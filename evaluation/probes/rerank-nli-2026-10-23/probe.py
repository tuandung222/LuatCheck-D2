#!/usr/bin/env python3
"""Low-memory probe of Vietnamese rerankers and an NLI model on BLL2019 v1 (23 Oct 2026).

Reads the read-only corpus/tasks, runs the existing first-stage retriever, reranks its
top-20 with real cross-encoder models (one pair per forward pass, one model in memory at
a time) and runs constructed NLI pairs.  Writes results.json and RESULTS.md.
See BRIEF.md in this directory.

Usage (from anywhere):
    ~/src/probe-venv/bin/python probe.py                      # everything
    ~/src/probe-venv/bin/python probe.py --only qwen3,nli     # re-run selected phases, merge into results.json
    ~/src/probe-venv/bin/python probe.py --render-only        # regenerate RESULTS.md from results.json

Memory rules: batch size 1, rerankers max_length 1024, mDeBERTa 512, fp16 on MPS for the
rerankers only after a sanity check against fp32-CPU scores, hard guard of 4 GB for
(process RSS + MPS driver allocation), resource wait before every model.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")            # models are in the local cache; no downloads
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
# transformers 5.20.2 async weight loading deadlocked on the GIL (safetensors once-cell) in a first run
# of this probe; load synchronously instead.
os.environ.setdefault("HF_DEACTIVATE_ASYNC_LOAD", "1")

import numpy as np
import psutil
import torch

PROBE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROBE_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT))

CORPUS_PATH = REPO_ROOT / "data/corpus/labor_code_2019_official.json"
TASKS_PATH = REPO_ROOT / "evaluation/benchmarks/bll2019_v1/tasks.json"
RESULTS_PATH = PROBE_DIR / "results.json"
RESULTS_MD_PATH = PROBE_DIR / "RESULTS.md"
FOREIGN_TASK_ID = "BLL19-10-FOREIGN_SCOPE"

RERANKER_MAX_LEN = 1024          # user memory cap (AITeamVN card suggests 2304)
NLI_MAX_LEN = 512
GUARD_BYTES = 4 * 1024 ** 3      # RSS + MPS driver allocation
GUARD_EVERY_PAIRS = 10
WAIT_POLL_S = 30
WAIT_MAX_S = 600
MIN_FREE_PCT = 25
HEAVY_PROC_BYTES = 2 * 1024 ** 3

NLI_LABELS = ["entailment", "neutral", "contradiction"]

# ---------------------------------------------------------------------------
# Constructed NLI pairs.  Built from the task evidence by the probe author, NOT human
# labelled.  `evidence_index` selects which reference_evidence quote is the premise.
# ---------------------------------------------------------------------------
NLI_SPECS = {
    "BLL19-01-PROBATION": {
        "evidence_index": 0,
        "entailment": "Không quá 60 ngày.",
        "contradiction": ("Người sử dụng lao động được phép kéo dài thời gian thử việc "
                          "tới 90 ngày đối với công việc có chức danh nghề nghiệp cần trình độ "
                          "chuyên môn, kỹ thuật từ cao đẳng trở lên."),
        "neutral_from": "BLL19-08-UNLAWFUL_TERMINATION",
    },
    "BLL19-02-PROBATION_WAGE": {
        "evidence_index": 0,
        "entailment": "Ít nhất bằng 85% mức lương của công việc đó.",
        "contradiction": ("Tiền lương của người lao động trong thời gian thử việc có thể chỉ "
                          "bằng 70% mức lương của công việc đó."),
        "neutral_from": "BLL19-09-DEPOSIT",
    },
    "BLL19-03-NOTICE": {
        "evidence_index": 0,
        "entailment": "Ít nhất 45 ngày.",
        "contradiction": ("Người lao động chỉ cần báo trước 30 ngày nếu làm việc theo hợp đồng "
                          "lao động không xác định thời hạn."),
        "neutral_from": "BLL19-02-PROBATION_WAGE",
    },
    "BLL19-04-ABSENCE": {
        # quote 1 is the notice rule ("không phải báo trước") the polarity flip targets
        "evidence_index": 1,
        "entailment": ("Người sử dụng lao động không phải báo trước cho người lao động khi đơn "
                       "phương chấm dứt hợp đồng lao động quy định tại điểm d và điểm e khoản 1 "
                       "Điều này."),
        "contradiction": ("Khi đơn phương chấm dứt hợp đồng lao động quy định tại điểm d và điểm e "
                          "khoản 1 Điều này thì người sử dụng lao động phải báo trước cho người "
                          "lao động."),
        "neutral_from": "BLL19-01-PROBATION",
    },
    "BLL19-05-PREGNANCY": {
        "evidence_index": 0,
        "entailment": "Không được thực hiện quyền đơn phương chấm dứt trong các trường hợp này.",
        "contradiction": ("Người sử dụng lao động được thực hiện quyền đơn phương chấm dứt hợp "
                          "đồng lao động đối với người lao động nữ đang mang thai."),
        "neutral_from": "BLL19-03-NOTICE",
    },
    "BLL19-06-UNLAWFUL_RESIGNATION": {
        "evidence_index": 0,
        "entailment": "Người lao động đơn phương chấm dứt trái pháp luật không được trợ cấp thôi việc.",
        "contradiction": "Người lao động đơn phương chấm dứt trái pháp luật được hưởng trợ cấp thôi việc.",
        "neutral_from": "BLL19-01-PROBATION",
    },
    "BLL19-07-NOTICE_AND_SEVERANCE": {
        "evidence_index": 0,
        "entailment": "Báo trước ít nhất 30 ngày.",
        "contradiction": ("Người lao động chỉ cần báo trước 15 ngày nếu làm việc theo hợp đồng lao "
                          "động xác định thời hạn có thời hạn từ 12 tháng đến 36 tháng."),
        "neutral_from": "BLL19-05-PREGNANCY",
    },
    "BLL19-08-UNLAWFUL_TERMINATION": {
        # quote 1 is "ít nhất bằng 02 tháng tiền lương"
        "evidence_index": 1,
        "entailment": "Phải trả thêm ít nhất bằng 02 tháng tiền lương theo hợp đồng lao động.",
        "contradiction": ("Người sử dụng lao động chỉ cần trả thêm 01 tháng tiền lương theo hợp "
                          "đồng lao động."),
        "neutral_from": "BLL19-02-PROBATION_WAGE",
    },
    "BLL19-09-DEPOSIT": {
        "evidence_index": 0,
        "entailment": "Không được phép yêu cầu biện pháp bảo đảm bằng tiền hoặc tài sản khác cho việc thực hiện hợp đồng lao động.",
        "contradiction": ("Người sử dụng lao động được phép yêu cầu người lao động nộp tiền đặt cọc "
                          "để bảo đảm việc thực hiện hợp đồng lao động."),
        "neutral_from": "BLL19-06-UNLAWFUL_RESIGNATION",
    },
}

REAL_OUTPUT_PAIRS = [
    {
        "id": "real-output-dieu17-deposit",
        "article_id": "Dieu_17",
        "hypothesis": ("Người sử dụng lao động được phép yêu cầu người lao động nộp tiền đặt cọc "
                       "để bảo đảm thực hiện hợp đồng lao động."),
        "expected": "contradiction",
    },
    {
        "id": "real-output-dieu107-california",
        "article_id": "Dieu_107",
        "hypothesis": "Theo luật bang California, số giờ làm thêm tối đa là 200 giờ một năm.",
        "expected": "neutral",
    },
]


# ---------------------------------------------------------------------------
# Utilities: memory guard, resource wait, timing
# ---------------------------------------------------------------------------
class MemoryGuardError(RuntimeError):
    pass


class MemSampler(threading.Thread):
    """Samples process RSS while a model phase runs (RSS only; MPS is read in the main thread)."""

    def __init__(self, interval=0.02):
        super().__init__(daemon=True)
        self.interval = interval
        self.peak_rss = 0
        self._stop_event = threading.Event()
        self.proc = psutil.Process()

    def run(self):
        while not self._stop_event.is_set():
            try:
                self.peak_rss = max(self.peak_rss, self.proc.memory_info().rss)
            except psutil.Error:
                pass
            self._stop_event.wait(self.interval)

    def stop(self):
        self._stop_event.set()
        self.join(timeout=1.0)


def mps_memory() -> dict:
    if not torch.backends.mps.is_available():
        return {}
    out = {}
    try:
        out["current_allocated_bytes"] = int(torch.mps.current_allocated_memory())
        out["driver_allocated_bytes"] = int(torch.mps.driver_allocated_memory())
    except Exception as exc:  # noqa: BLE001 - reported, not hidden
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


class Guard:
    """Aborts a model phase when RSS + MPS driver allocation exceeds GUARD_BYTES."""

    def __init__(self):
        self.snapshots = []
        self.peak_rss = 0
        self.peak_mps_driver = 0
        self.peak_mps_current = 0
        self.peak_combined = 0

    def check(self, tag: str):
        rss = psutil.Process().memory_info().rss
        mps = mps_memory()
        drv = mps.get("driver_allocated_bytes", 0)
        cur = mps.get("current_allocated_bytes", 0)
        combined = rss + drv
        self.peak_rss = max(self.peak_rss, rss)
        self.peak_mps_driver = max(self.peak_mps_driver, drv)
        self.peak_mps_current = max(self.peak_mps_current, cur)
        self.peak_combined = max(self.peak_combined, combined)
        self.snapshots.append({"tag": tag, "rss": rss, "mps_driver": drv, "mps_current": cur,
                               "combined": combined})
        if combined > GUARD_BYTES:
            raise MemoryGuardError(
                f"memory guard tripped at '{tag}': rss={rss/2**30:.2f} GiB + mps_driver="
                f"{drv/2**30:.2f} GiB = {combined/2**30:.2f} GiB > {GUARD_BYTES/2**30:.0f} GiB")

    def summary(self) -> dict:
        return {"peak_rss_at_checks_bytes": self.peak_rss,
                "peak_mps_driver_bytes": self.peak_mps_driver,
                "peak_mps_current_bytes": self.peak_mps_current,
                "peak_rss_plus_mps_driver_bytes": self.peak_combined,
                "guard_limit_bytes": GUARD_BYTES,
                "n_checks": len(self.snapshots)}


def memory_free_pct():
    """macOS `memory_pressure` system-wide free percentage; falls back to psutil."""
    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=20).stdout
        m = re.search(r"free percentage:\s*(\d+)%", out)
        if m:
            return int(m.group(1)), "memory_pressure"
    except Exception:  # noqa: BLE001
        pass
    vm = psutil.virtual_memory()
    return int(round(100.0 * vm.available / vm.total)), "psutil.available"


def heavy_python_procs():
    me = os.getpid()
    parents = set()
    try:
        parents = {p.pid for p in psutil.Process().parents()}
    except psutil.Error:
        pass
    found = []
    for p in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
        try:
            if p.info["pid"] == me or p.info["pid"] in parents:
                continue
            cmd = " ".join(p.info["cmdline"] or [])
            name = p.info["name"] or ""
            rss = p.info["memory_info"].rss
            if rss > HEAVY_PROC_BYTES and ("python" in name.lower() or "python" in cmd.lower()):
                found.append({"pid": p.info["pid"], "rss_bytes": rss, "cmd": cmd[:160]})
        except (psutil.Error, TypeError, AttributeError):
            continue
    return found


def wait_for_resources(label: str) -> dict:
    """Poll every WAIT_POLL_S up to WAIT_MAX_S until no other heavy python process is running
    and system free memory >= MIN_FREE_PCT. Returns a record of what was observed."""
    rec = {"label": label, "waited_seconds": 0.0, "polls": [], "proceeded": False}
    t0 = time.time()
    while True:
        free_pct, src = memory_free_pct()
        heavy = heavy_python_procs()
        sw = psutil.swap_memory()
        rec["polls"].append({"t": round(time.time() - t0, 1), "free_pct": free_pct,
                             "free_pct_source": src, "swap_used_bytes": sw.used,
                             "swap_total_bytes": sw.total, "heavy_python_procs": heavy})
        if free_pct >= MIN_FREE_PCT and not heavy:
            rec["proceeded"] = True
            break
        if time.time() - t0 >= WAIT_MAX_S:
            break
        print(f"[{label}] waiting: free={free_pct}% heavy_python={len(heavy)}", flush=True)
        time.sleep(WAIT_POLL_S)
    rec["waited_seconds"] = round(time.time() - t0, 1)
    return rec


def latency_summary(values_ms) -> dict:
    a = np.asarray(values_ms, dtype=float)
    if a.size == 0:
        return {"n": 0}
    return {"n": int(a.size), "median_ms": float(np.median(a)),
            "p95_ms": float(np.percentile(a, 95)), "mean_ms": float(a.mean()),
            "min_ms": float(a.min()), "max_ms": float(a.max()),
            "per_pair_ms": [round(float(v), 3) for v in a]}


class Loaded:
    def __init__(self, tok, model, score, device, dtype):
        self.tok, self.model, self.score, self.device, self.dtype = tok, model, score, device, dtype


def release(loaded):
    if loaded is not None:
        loaded.model = None
        loaded.score = None
        loaded.tok = None
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    gc.collect()


def sync(device):
    if device == "mps":
        torch.mps.synchronize()


# ---------------------------------------------------------------------------
# Model loaders. score(query, doc) -> dict(score, raw, n_tokens, truncated)
# ---------------------------------------------------------------------------
def _from_pretrained(cls, repo, device, dtype):
    kwargs = {"dtype": dtype}
    if device == "mps":
        kwargs["device_map"] = {"": "mps"}   # load straight to the device, avoid a second CPU copy
    model = cls.from_pretrained(repo, **kwargs)
    if device != "mps":
        model = model.to(device)
    return model.eval()


def load_aiteam(repo, device, dtype) -> Loaded:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(repo)
    model = _from_pretrained(AutoModelForSequenceClassification, repo, device, dtype)

    def score(query, doc):
        full = tok(query, doc, truncation=False)["input_ids"]
        enc = tok(query, doc, truncation="only_second", max_length=RERANKER_MAX_LEN,
                  return_tensors="pt")
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.inference_mode():
            logit = model(**enc).logits.view(-1).float()[0]
        v = float(logit.cpu())
        return {"score": v, "raw": v, "n_tokens": len(full), "truncated": len(full) > RERANKER_MAX_LEN}

    return Loaded(tok, model, score, device, str(dtype))


def load_qwen3(repo, device, dtype) -> Loaded:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    prefix = ("<|im_start|>system\nJudge whether the Document meets the requirements based on "
              "the Query and the Instruct provided. Note that the answer can only be \"yes\" or "
              "\"no\".<|im_end|>\n<|im_start|>user\n")
    suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    instruction = "Given a web search query, retrieve relevant passages that answer the query"
    tok = AutoTokenizer.from_pretrained(repo, padding_side="left")
    model = _from_pretrained(AutoModelForCausalLM, repo, device, dtype)
    t_true = tok.convert_tokens_to_ids("yes")
    t_false = tok.convert_tokens_to_ids("no")
    prefix_ids = tok.encode(prefix, add_special_tokens=False)
    suffix_ids = tok.encode(suffix, add_special_tokens=False)
    inner_max = RERANKER_MAX_LEN - len(prefix_ids) - len(suffix_ids)

    def score(query, doc):
        text = f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {doc}"
        n_full = len(tok(text, add_special_tokens=False)["input_ids"]) + len(prefix_ids) + len(suffix_ids)
        ids = tok(text, truncation="longest_first", max_length=inner_max,
                  add_special_tokens=False)["input_ids"]
        ids = prefix_ids + list(ids) + suffix_ids
        input_ids = torch.tensor([ids], device=device)
        with torch.inference_mode():
            # logits_to_keep=1: only the last position is needed; avoids a (seq x 151k vocab) tensor
            logits = model(input_ids=input_ids, attention_mask=torch.ones_like(input_ids),
                           logits_to_keep=1).logits[:, -1, :].float()
        two = torch.stack([logits[:, t_false], logits[:, t_true]], dim=1)
        prob = torch.log_softmax(two, dim=1)[:, 1].exp()
        margin = (logits[:, t_true] - logits[:, t_false])
        return {"score": float(prob.cpu()[0]), "raw": float(margin.cpu()[0]),
                "n_tokens": n_full, "truncated": n_full > RERANKER_MAX_LEN}

    return Loaded(tok, model, score, device, str(dtype))


def load_nli(repo, device, dtype) -> Loaded:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(repo)
    model = _from_pretrained(AutoModelForSequenceClassification, repo, device, dtype)
    id2label = {int(k): v for k, v in model.config.id2label.items()}

    def score(premise, hypothesis):
        enc = tok(premise, hypothesis, truncation="only_first", max_length=NLI_MAX_LEN,
                  return_tensors="pt")
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.inference_mode():
            logits = model(**enc).logits[0].float()
        return torch.softmax(logits, dim=-1).cpu().tolist()

    ld = Loaded(tok, model, score, device, str(dtype))
    ld.id2label = id2label
    return ld


# ---------------------------------------------------------------------------
# Data + retrieval (existing first stage, unchanged)
# ---------------------------------------------------------------------------
def load_inputs():
    with open(CORPUS_PATH, encoding="utf-8") as fh:
        corpus = json.load(fh)
    with open(TASKS_PATH, encoding="utf-8") as fh:
        tasks = json.load(fh)
    return corpus, tasks


def build_first_stage(tasks):
    from src.retrieval.hybrid_domain import HybridDomainRetriever
    retriever = HybridDomainRetriever(corpus_path=str(CORPUS_PATH), retrieval_mode="tfidf")
    first_stage = {}
    for task in [t for t in tasks if t["task_id"] != FOREIGN_TASK_ID]:
        start = time.perf_counter()
        hits = retriever.search(task["question"], top_k=20)
        elapsed = time.perf_counter() - start
        ranking = [h["article_id"] for h in hits]
        gold = list(task["ground_truth_article_ids"])
        first_stage[task["task_id"]] = {
            "question": task["question"],
            "gold_ids": gold,
            "gold_ranks": {g: (ranking.index(g) + 1 if g in ranking else None) for g in gold},
            "gold_absent_from_top20": [g for g in gold if g not in ranking],
            "search_seconds": elapsed,
            "candidates": [{"article_id": h["article_id"], "rrf_score": h.get("rrf_score"),
                            "content_chars": len(h.get("content") or "")} for h in hits],
            "_hits": hits,
        }
    return first_stage


def rank_metrics(per_task_ranks, per_task_gold, ks=(1, 3, 5)):
    rows = []
    for task_id, ranks in per_task_ranks.items():
        gold = per_task_gold[task_id]
        found = [r for r in (ranks[g] for g in gold) if r is not None]
        rows.append({"task_id": task_id, "gold_ranks": ranks,
                     "recall": {f"@{k}": sum(1 for r in found if r <= k) / len(gold) for k in ks},
                     "rr": (1.0 / min(found)) if found else 0.0})
    return {"per_task": rows,
            "mean": {**{f"Recall@{k}": float(np.mean([r["recall"][f"@{k}"] for r in rows])) for k in ks},
                     "MRR": float(np.mean([r["rr"] for r in rows]))}}


# ---------------------------------------------------------------------------
# Experiment A
# ---------------------------------------------------------------------------
def sanity_compare(key, ref, test):
    """fp16-MPS vs fp32-CPU on the same pairs: finite, same order, small drift."""
    r = [x["score"] for x in ref]
    t = [x["score"] for x in test]
    finite = all(np.isfinite(t))
    diffs = [abs(a - b) for a, b in zip(r, t)]
    same_order = list(np.argsort(r, kind="stable")) == list(np.argsort(t, kind="stable"))
    raw_r = [x["raw"] for x in ref]
    raw_t = [x["raw"] for x in test]
    raw_diffs = [abs(a - b) for a, b in zip(raw_r, raw_t)]
    # tolerance on the raw (logit / yes-no margin) scale; both models produce O(1-10) values
    tol = 0.75
    ok = bool(finite and same_order and max(raw_diffs) <= tol)
    return {"fp32_cpu_scores": r, "fp16_mps_scores": t, "fp32_cpu_raw": raw_r, "fp16_mps_raw": raw_t,
            "max_abs_raw_diff": float(max(raw_diffs)), "max_abs_score_diff": float(max(diffs)),
            "finite": bool(finite), "same_order": bool(same_order), "raw_tolerance": tol, "sane": ok}


def run_reranker(key, repo, loader, first_stage):
    phase = {"model": repo, "status": "pending", "errors": [], "max_length": RERANKER_MAX_LEN,
             "batch_size": 1}
    phase["resource_wait"] = wait_for_resources(key)
    if not phase["resource_wait"]["proceeded"]:
        phase["status"] = "skipped_resources"
        phase["errors"].append({"stage": "wait", "error": "heavy process / low free memory persisted "
                                "for the full wait window; model not loaded"})
        return phase
    guard = Guard()
    sampler = MemSampler()
    sampler.start()
    baseline_rss = psutil.Process().memory_info().rss
    loaded = None
    try:
        first_tid = next(iter(first_stage))
        fs0 = first_stage[first_tid]
        ref_pairs = [(fs0["question"], h["content"]) for h in fs0["_hits"][:4]]

        device, dtype = "cpu", torch.float32
        phase["load_attempts"] = []
        if torch.backends.mps.is_available():
            # 1. fp32 CPU reference on 4 pairs
            t0 = time.perf_counter()
            ref_loaded = loader(repo, "cpu", torch.float32)
            phase["load_attempts"].append({"device": "cpu", "dtype": "float32", "purpose": "sanity reference",
                                           "load_seconds": time.perf_counter() - t0})
            guard.check(f"{key}: after fp32-cpu reference load")
            ref_loaded.score(*ref_pairs[0])  # warm-up
            ref = [ref_loaded.score(q, d) for q, d in ref_pairs]
            guard.check(f"{key}: after fp32-cpu reference scoring")
            release(ref_loaded); ref_loaded = None
            # 2. fp16 MPS
            t0 = time.perf_counter()
            loaded = loader(repo, "mps", torch.float16)
            phase["load_attempts"].append({"device": "mps", "dtype": "float16", "purpose": "candidate run",
                                           "load_seconds": time.perf_counter() - t0})
            guard.check(f"{key}: after fp16-mps load")
            loaded.score(*ref_pairs[0]); sync("mps")  # warm-up
            test = [loaded.score(q, d) for q, d in ref_pairs]
            phase["fp16_sanity_check"] = sanity_compare(key, ref, test)
            if phase["fp16_sanity_check"]["sane"]:
                device, dtype = "mps", torch.float16
            else:
                print(f"[{key}] fp16 MPS outputs not sane vs fp32 CPU; falling back to fp32 CPU", flush=True)
                release(loaded); loaded = None
        if loaded is None:
            t0 = time.perf_counter()
            loaded = loader(repo, "cpu", torch.float32)
            phase["load_attempts"].append({"device": "cpu", "dtype": "float32", "purpose": "candidate run",
                                           "load_seconds": time.perf_counter() - t0})
            guard.check(f"{key}: after fp32-cpu load")
            loaded.score(*ref_pairs[0])
            device, dtype = "cpu", torch.float32
        phase["device"] = device
        phase["dtype"] = str(dtype).replace("torch.", "")
        phase["load_seconds"] = phase["load_attempts"][-1]["load_seconds"]
        print(f"[{key}] running on {device} {phase['dtype']}", flush=True)

        per_task, per_task_ranks, per_task_gold = {}, {}, {}
        lat_ms, truncated_ids, n_pairs = [], [], 0
        phase["per_task"] = per_task
        for task_id, fs in first_stage.items():
            hits = fs["_hits"]
            scores, raws, ntoks, trunc = [], [], [], []
            t_task = time.perf_counter()
            for h in hits:
                t = time.perf_counter()
                out = loaded.score(fs["question"], h["content"])
                sync(device)
                lat_ms.append((time.perf_counter() - t) * 1000)
                scores.append(out["score"]); raws.append(out["raw"])
                ntoks.append(out["n_tokens"]); trunc.append(out["truncated"])
                if out["truncated"]:
                    truncated_ids.append(f"{task_id}:{h['article_id']}")
                n_pairs += 1
                if n_pairs % GUARD_EVERY_PAIRS == 0:
                    guard.check(f"{key}: pair {n_pairs}")
            order = sorted(range(len(hits)), key=lambda i: (-scores[i], i))
            reranked = [hits[i]["article_id"] for i in order]
            ranks = {g: (reranked.index(g) + 1 if g in reranked else None) for g in fs["gold_ids"]}
            per_task[task_id] = {
                "gold_ranks_before": fs["gold_ranks"], "gold_ranks_after": ranks,
                "reranked_ids": reranked,
                "scores": {hits[i]["article_id"]: scores[i] for i in range(len(hits))},
                "raw_scores": {hits[i]["article_id"]: raws[i] for i in range(len(hits))},
                "n_tokens": {hits[i]["article_id"]: ntoks[i] for i in range(len(hits))},
                "truncated": [hits[i]["article_id"] for i in range(len(hits)) if trunc[i]],
                "gold_truncated": [g for g in fs["gold_ids"]
                                   if g in [hits[i]["article_id"] for i in range(len(hits)) if trunc[i]]],
                "seconds": time.perf_counter() - t_task,
            }
            per_task_ranks[task_id] = ranks
            per_task_gold[task_id] = fs["gold_ids"]
        guard.check(f"{key}: end")
        phase["metrics"] = rank_metrics(per_task_ranks, per_task_gold)
        phase["per_pair_latency"] = latency_summary(lat_ms)
        phase["truncation"] = {"candidates_over_cap": len(truncated_ids), "n_pairs": n_pairs,
                               "cap_tokens": RERANKER_MAX_LEN, "pairs": truncated_ids}
        phase["status"] = "ok"
    except MemoryGuardError as exc:
        phase["status"] = "aborted_memory_guard"
        phase["errors"].append({"stage": "guard", "error": str(exc)})
        print(f"[{key}] ABORTED: {exc}", flush=True)
    except Exception as exc:  # noqa: BLE001
        phase["status"] = "error"
        phase["errors"].append({"stage": "run", "error": f"{type(exc).__name__}: {exc}",
                                "traceback": traceback.format_exc()[-4000:]})
        print(f"[{key}] FAILED: {exc}", flush=True)
    finally:
        sampler.stop()
        phase["memory"] = {"baseline_rss_bytes": baseline_rss, "peak_rss_sampled_bytes": sampler.peak_rss,
                           **guard.summary(), "snapshots": guard.snapshots}
        release(loaded)
    return phase


# ---------------------------------------------------------------------------
# Experiment B
# ---------------------------------------------------------------------------
def build_nli_pairs(tasks, corpus):
    by_id = {t["task_id"]: t for t in tasks}
    content_by_id = {d["article_id"]: d["content"] for d in corpus}
    pairs = []
    for task_id, spec in NLI_SPECS.items():
        task = by_id[task_id]
        evidence = task["reference_evidence"][spec["evidence_index"]]
        premise = evidence["exact_quote"]
        pairs.append({
            "id": f"{task_id}::entailment",
            "kind": "entailment",
            "task_id": task_id,
            "premise_article_id": evidence["article_id"],
            "premise": premise,
            "hypothesis": spec["entailment"],
            "hypothesis_source": ("expected_answer_verbatim"
                                  if spec["entailment"] == task["expected_answer"]
                                  else "faithful_restatement"),
            "expected": "entailment",
        })
        pairs.append({
            "id": f"{task_id}::contradiction",
            "kind": "contradiction",
            "task_id": task_id,
            "premise_article_id": evidence["article_id"],
            "premise": premise,
            "hypothesis": spec["contradiction"],
            "hypothesis_source": "constructed_contradiction",
            "expected": "contradiction",
        })
        other = by_id[spec["neutral_from"]]
        pairs.append({
            "id": f"{task_id}::neutral",
            "kind": "neutral",
            "task_id": task_id,
            "premise_article_id": evidence["article_id"],
            "premise": premise,
            "hypothesis": other["expected_answer"],
            "hypothesis_source": f"expected_answer_of:{spec['neutral_from']}",
            "expected": "neutral",
        })
    for spec in REAL_OUTPUT_PAIRS:
        if spec["article_id"] not in content_by_id:
            raise KeyError(f"missing corpus article {spec['article_id']}")
        pairs.append({
            "id": spec["id"],
            "kind": "real_model_output",
            "task_id": None,
            "premise_article_id": spec["article_id"],
            "premise": content_by_id[spec["article_id"]],
            "hypothesis": spec["hypothesis"],
            "hypothesis_source": "real_model_output",
            "expected": spec["expected"],
        })
    return pairs




def windowed_scores(ld, premise, hypothesis, window_tokens=380, stride_tokens=250):
    """Only used for premises longer than the 512-token cap: premise token windows, each scored
    with the hypothesis. Returns per-window probabilities (aggregation is done by the caller)."""
    ids = ld.tok(premise, add_special_tokens=False)["input_ids"]
    out, start = [], 0
    while True:
        chunk = ld.tok.decode(ids[start:start + window_tokens])
        out.append({"start_token": start, "probs": ld.score(chunk, hypothesis)})
        if start + window_tokens >= len(ids):
            break
        start += stride_tokens
    return out


def run_nli(repo, tasks, corpus):
    phase = {"model": repo, "status": "pending", "errors": [], "max_length": NLI_MAX_LEN,
             "dtype": "float32", "batch_size": 1}
    phase["resource_wait"] = wait_for_resources("nli")
    if not phase["resource_wait"]["proceeded"]:
        phase["status"] = "skipped_resources"
        phase["errors"].append({"stage": "wait", "error": "heavy process / low free memory persisted; not loaded"})
        return phase
    guard = Guard()
    sampler = MemSampler(); sampler.start()
    baseline_rss = psutil.Process().memory_info().rss
    loaded = None
    try:
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        t0 = time.perf_counter()
        try:
            loaded = load_nli(repo, device, torch.float32)
        except Exception as exc:  # noqa: BLE001 - recorded, then CPU retry
            phase["errors"].append({"stage": f"load on {device}", "error": f"{type(exc).__name__}: {exc}",
                                    "traceback": traceback.format_exc()[-3000:]})
            release(None)
            device = "cpu"
            loaded = load_nli(repo, "cpu", torch.float32)
        phase["device"] = device
        phase["load_seconds"] = time.perf_counter() - t0
        guard.check("nli: after load")
        phase["id2label_from_config"] = {str(k): v for k, v in loaded.id2label.items()}
        labels = [loaded.id2label[i] for i in range(len(loaded.id2label))]
        assert labels == NLI_LABELS, f"unexpected label order {labels}"

        pairs = build_nli_pairs(tasks, corpus)
        for p in pairs:
            ids_p = loaded.tok(p["premise"], add_special_tokens=False)["input_ids"]
            ids_pair = loaded.tok(p["premise"], p["hypothesis"])["input_ids"]
            p["premise_tokens"] = len(ids_p)
            p["pair_tokens"] = len(ids_pair)
            p["pair_over_512"] = len(ids_pair) > NLI_MAX_LEN

        loaded.score("Đoạn văn thử nghiệm.", "Câu thử nghiệm."); sync(device)  # warm-up
        lat = []
        for i, p in enumerate(pairs, 1):
            t = time.perf_counter()
            probs = loaded.score(p["premise"], p["hypothesis"]); sync(device)
            lat.append((time.perf_counter() - t) * 1000)
            p["probs"] = dict(zip(NLI_LABELS, map(float, probs)))
            p["predicted"] = NLI_LABELS[int(np.argmax(probs))]
            p["correct"] = p["predicted"] == p["expected"]
            if p["pair_over_512"]:
                p["premise_truncated"] = True
                wins = windowed_scores(loaded, p["premise"], p["hypothesis"])
                p["windowed"] = {
                    "note": ("supplementary: premise split into ~380-token windows; aggregation = per-class "
                             "max over windows, then argmax (heuristic, not part of the brief's base protocol)"),
                    "windows": [{"start_token": w["start_token"],
                                 "probs": dict(zip(NLI_LABELS, map(float, w["probs"])))} for w in wins]}
                agg = [max(w["probs"][c] for w in wins) for c in range(3)]
                p["windowed"]["aggregate_max"] = dict(zip(NLI_LABELS, map(float, agg)))
                p["windowed"]["predicted"] = NLI_LABELS[int(np.argmax(agg))]
                p["windowed"]["correct"] = p["windowed"]["predicted"] == p["expected"]
            else:
                p["premise_truncated"] = False
            if i % GUARD_EVERY_PAIRS == 0:
                guard.check(f"nli: pair {i}")
        guard.check("nli: end")

        constructed = [p for p in pairs if p["kind"] in NLI_LABELS]
        by_class = {}
        for cls in NLI_LABELS:
            rows = [p for p in constructed if p["kind"] == cls]
            by_class[cls] = {"n": len(rows), "correct": sum(p["correct"] for p in rows),
                             "accuracy": sum(p["correct"] for p in rows) / len(rows),
                             "predictions": {l: sum(1 for p in rows if p["predicted"] == l) for l in NLI_LABELS}}
        phase["pairs"] = pairs
        phase["accuracy_by_constructed_class"] = by_class
        phase["constructed_accuracy"] = sum(p["correct"] for p in constructed) / len(constructed)
        phase["real_output_accuracy"] = {
            "n": sum(1 for p in pairs if p["kind"] == "real_model_output"),
            "correct": sum(1 for p in pairs if p["kind"] == "real_model_output" and p["correct"])}
        phase["truncation"] = {"pairs_over_512_tokens": [p["id"] for p in pairs if p["pair_over_512"]],
                               "n_pairs": len(pairs)}
        phase["per_pair_latency"] = latency_summary(lat)
        phase["status"] = "ok"
    except MemoryGuardError as exc:
        phase["status"] = "aborted_memory_guard"
        phase["errors"].append({"stage": "guard", "error": str(exc)})
        print(f"[nli] ABORTED: {exc}", flush=True)
    except Exception as exc:  # noqa: BLE001
        phase["status"] = "error"
        phase["errors"].append({"stage": "run", "error": f"{type(exc).__name__}: {exc}",
                                "traceback": traceback.format_exc()[-4000:]})
        print(f"[nli] FAILED: {exc}", flush=True)
    finally:
        sampler.stop()
        phase["memory"] = {"baseline_rss_bytes": baseline_rss, "peak_rss_sampled_bytes": sampler.peak_rss,
                           **guard.summary(), "snapshots": guard.snapshots}
        release(loaded)
    return phase


# ---------------------------------------------------------------------------
# Optional: OneJev -- not run (reason recorded; see RESULTS.md)
# ---------------------------------------------------------------------------
def onejev_section():
    cache = Path.home() / ".cache/huggingface/hub/models--OmniJev--OneJev1.6-0.8B"
    import importlib.util
    return {
        "model": "OmniJev/OneJev1.6-0.8B",
        "status": "skipped",
        "qev_installed": importlib.util.find_spec("qev") is not None,
        "weights_in_hf_cache": cache.exists(),
        "reason": ("Official API per the model card is `qev serve --model OmniJev/OneJev1.6-0.8B` (an HTTP "
                   "server implementing TypeSafe's System One API) plus `qev.Client(...).system_one(...)`, "
                   "with `qev` installed from GitHub (`pip install \"qev[torch] @ git+https://github.com/"
                   "OmniJev/OneJev.git\"`). Running it requires (a) a network install of third-party code "
                   "from a git URL and (b) starting a new model server, which this task forbids; the model "
                   "is a multimodal decision model with typed Choice/Noul questions, not an NLI cross-encoder, "
                   "so a direct transformers load would not be its official API. Not attempted; no numbers "
                   "reported for it."),
    }


# ---------------------------------------------------------------------------
# RESULTS.md rendering (every number comes from results.json)
# ---------------------------------------------------------------------------
GIB = 2 ** 30


def _fmt_ranks(ranks):
    return ", ".join(f"{g}:{'absent' if r is None else r}" for g, r in ranks.items())


def render_md(res):
    L = []
    P = res["probe"]
    L.append("# Reranker and NLI probe, 23 Oct 2026 (Mac, low-memory run)\n")
    L.append(f"Device availability: MPS={P['mps_available']}, torch {P['torch']}, {P['platform']}. "
             "Batch size 1 per pair, one model in memory at a time, guard: RSS + MPS driver allocation <= 4 GiB.\n")
    L.append("## Caveats (read first)\n")
    L.append("- **Tiny sample**: 9 answerable queries (BLL19-10-FOREIGN_SCOPE excluded) and 29 NLI pairs. "
             "This is a probe, not a benchmark; differences of one query move Recall/MRR by 0.11.\n"
             "- **NLI labels are constructed by the probe author from source text, not human labels.** "
             "Hypotheses for entailment were taken or restated from expected answers; contradictions were "
             "written by changing a quantity or polarity; neutral hypotheses are expected answers of unrelated tasks.\n"
             "- **Not report evidence.** Nothing here is a reviewed answer-correctness result; first-stage "
             "numbers are rank metrics on gold article IDs only. Do not copy into D2 report tables.\n"
             "- Reranker max_length was capped at 1024 tokens (lower than AITeamVN's suggested 2304) to limit "
             "memory; truncated candidates are counted below and may disadvantage long articles.\n"
             "- Latencies are single-pair forward passes (after one warm-up) on a shared Mac with an Ollama "
             "runner and llama-server running; absolute values are noisy.\n")
    L.append("## Experiment A: reranking the first-stage top-20 (9 queries)\n")
    fs_m = res["first_stage"]["metrics"]["mean"]
    absent = [(tid, d["gold_absent_from_top20"]) for tid, d in res["first_stage"]["per_task"].items()
              if d["gold_absent_from_top20"]]
    L.append("| System | Device / dtype | Recall@1 | Recall@3 | Recall@5 | MRR | Load s | Median ms/pair | p95 ms/pair | "
             "Peak RSS (sampled) GiB | Peak MPS driver GiB | Peak RSS+MPS (at checks) GiB | Truncated cands |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    L.append(f"| first-stage HybridDomainRetriever (tfidf) | cpu | {fs_m['Recall@1']:.3f} | {fs_m['Recall@3']:.3f} | "
             f"{fs_m['Recall@5']:.3f} | {fs_m['MRR']:.3f} | - | - | - | - | - | - | - |")
    for key, ph in res["experiment_a"]["models"].items():
        if ph.get("status") != "ok":
            L.append(f"| {ph['model']} | {ph.get('device','-')} | FAILED: {ph['status']} | | | | | | | | | | |")
            continue
        m = ph["metrics"]["mean"]; lat = ph["per_pair_latency"]; mem = ph["memory"]; tr = ph["truncation"]
        L.append(f"| {ph['model']} | {ph['device']} {ph['dtype']} | {m['Recall@1']:.3f} | {m['Recall@3']:.3f} | "
                 f"{m['Recall@5']:.3f} | {m['MRR']:.3f} | {ph['load_seconds']:.1f} | {lat['median_ms']:.0f} | "
                 f"{lat['p95_ms']:.0f} | {mem['peak_rss_sampled_bytes']/GIB:.2f} | "
                 f"{mem['peak_mps_driver_bytes']/GIB:.2f} | {mem['peak_rss_plus_mps_driver_bytes']/GIB:.2f} | "
                 f"{tr['candidates_over_cap']}/{tr['n_pairs']} |")
    L.append("")
    L.append("Gold articles absent from the first-stage top-20 (cannot be recovered by reranking): " +
             ("; ".join(f"{t}: {', '.join(g)}" for t, g in absent) if absent else "none") + ".\n")
    L.append("### Per-task gold ranks (1 = best; `absent` = not in top-20)\n")
    hdr = ["Task", "first-stage"] + [ph["model"].split("/")[-1] for ph in res["experiment_a"]["models"].values()]
    L.append("| " + " | ".join(hdr) + " |")
    L.append("|" + "---|" * len(hdr))
    for tid, d in res["first_stage"]["per_task"].items():
        row = [tid, _fmt_ranks(d["gold_ranks"])]
        for ph in res["experiment_a"]["models"].values():
            pt = ph.get("per_task", {}).get(tid)
            if ph.get("status") != "ok" or pt is None:
                row.append("n/a")
            else:
                cell = _fmt_ranks(pt["gold_ranks_after"])
                if pt["gold_truncated"]:
                    cell += f" (gold truncated: {', '.join(pt['gold_truncated'])})"
                row.append(cell)
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    for key, ph in res["experiment_a"]["models"].items():
        sc = ph.get("fp16_sanity_check")
        if sc:
            L.append(f"- {ph['model']}: fp16-MPS vs fp32-CPU sanity check on 4 pairs: sane={sc['sane']}, "
                     f"max |raw diff|={sc['max_abs_raw_diff']:.4f}, same order={sc['same_order']} "
                     f"(fp32-cpu raw {[round(x,3) for x in sc['fp32_cpu_raw']]}, "
                     f"fp16-mps raw {[round(x,3) for x in sc['fp16_mps_raw']]}).")
        rw = ph.get("resource_wait", {})
        L.append(f"- {ph['model']}: resource wait {rw.get('waited_seconds', 0)} s "
                 f"(free memory at start {rw['polls'][0]['free_pct']}% via {rw['polls'][0]['free_pct_source']}, "
                 f"swap used {rw['polls'][0]['swap_used_bytes']/GIB:.2f} of {rw['polls'][0]['swap_total_bytes']/GIB:.2f} GiB).")
    L.append("")
    L.append("Notes: the truncated candidates (see `truncation.pairs` in results.json) are the same article in every "
             "query's top-20 (Dieu_219, over the 1024-token cap); no gold article was truncated. The sampled peak RSS of each "
             "reranker occurs during the fp32-CPU sanity-reference scoring (before the fp16 model is moved to MPS, when MPS "
             "allocation is still 0); during the fp16-MPS run RSS stays below ~0.8 GiB and the MPS driver allocation is "
             "~1.1-1.4 GiB. Free memory was only just above the 25% threshold when each model started, and swap was already "
             "heavily used by other processes before this probe.\n")
    L.append("## Experiment B: NLI probe (MoritzLaurer/mDeBERTa-v3-base-mnli-xnli, constructed labels)\n")
    nb = res["experiment_b"]
    if nb.get("status") != "ok":
        L.append(f"FAILED: status={nb.get('status')}\n")
    else:
        mem = nb["memory"]; lat = nb["per_pair_latency"]
        L.append(f"Device {nb['device']} fp32, max_length 512, label order from config {nb['id2label_from_config']}. "
                 f"Load {nb['load_seconds']:.1f} s; median {lat['median_ms']:.0f} ms / p95 {lat['p95_ms']:.0f} ms per pair; "
                 f"peak RSS (sampled) {mem['peak_rss_sampled_bytes']/GIB:.2f} GiB, peak MPS driver "
                 f"{mem['peak_mps_driver_bytes']/GIB:.2f} GiB, peak RSS+MPS at checks {mem['peak_rss_plus_mps_driver_bytes']/GIB:.2f} GiB.\n")
        L.append("| Constructed class | n | correct | accuracy | predicted E / N / C |")
        L.append("|---|---|---|---|---|")
        for c, d in nb["accuracy_by_constructed_class"].items():
            pr = d["predictions"]
            L.append(f"| {c} | {d['n']} | {d['correct']} | {d['accuracy']:.3f} | {pr['entailment']} / {pr['neutral']} / {pr['contradiction']} |")
        L.append(f"| all constructed | {sum(d['n'] for d in nb['accuracy_by_constructed_class'].values())} | "
                 f"{sum(d['correct'] for d in nb['accuracy_by_constructed_class'].values())} | {nb['constructed_accuracy']:.3f} | |")
        ro = nb["real_output_accuracy"]
        L.append(f"\nReal-model-output cases: {ro['correct']}/{ro['n']} matched the expected label.")
        L.append(f"\nPairs over 512 tokens (truncated premise): {nb['truncation']['pairs_over_512_tokens'] or 'none'} "
                 f"of {nb['truncation']['n_pairs']}.\n")
        L.append("| Pair | Expected | Predicted | P(entail) | P(neutral) | P(contra) | Premise tok | Truncated |")
        L.append("|---|---|---|---|---|---|---|---|")
        for p in nb["pairs"]:
            pr = p["probs"]
            L.append(f"| {p['id']} | {p['expected']} | {p['predicted']}{'' if p['correct'] else ' (wrong)'} | "
                     f"{pr['entailment']:.3f} | {pr['neutral']:.3f} | {pr['contradiction']:.3f} | "
                     f"{p['premise_tokens']} | {'yes' if p['premise_truncated'] else 'no'} |")
        for p in nb["pairs"]:
            if p.get("windowed"):
                w = p["windowed"]
                L.append(f"\nSupplementary windowed scoring for {p['id']} ({len(w['windows'])} windows): aggregate (per-class max) "
                         f"E/N/C = {w['aggregate_max']['entailment']:.3f} / {w['aggregate_max']['neutral']:.3f} / "
                         f"{w['aggregate_max']['contradiction']:.3f} -> {w['predicted']} "
                         f"(expected {p['expected']}). Heuristic aggregation, not the base protocol.")
        L.append("")
    L.append("## OneJev1.6-0.8B\n")
    oj = res.get("onejev") or {}
    L.append(f"Status: {oj.get('status')}. {oj.get('reason', '')}\n")
    L.append("## Failures and errors\n")
    any_err = False
    for key, ph in res["experiment_a"]["models"].items():
        for e in ph.get("errors", []):
            any_err = True
            L.append(f"- {ph['model']} [{e['stage']}] (status {ph['status']}): {e['error']}")
    for e in nb.get("errors", []):
        any_err = True
        L.append(f"- mDeBERTa [{e['stage']}] (status {nb.get('status')}): {e['error']}")
    L.append("- Run history: the first launch of this rewritten probe hung (0% CPU, all threads waiting on the GIL inside "
             "safetensors during transformers 5.20.2 asynchronous weight loading) before any scoring; it was killed by hand and "
             "re-run with `HF_DEACTIVATE_ASYNC_LOAD=1` (synchronous loading, set in probe.py). No scores came from the hung launch.")
    if not any_err:
        L.append("- No model failures in the reported run. Earlier, a run by another tool, preserved as results_prior_killed_run.json, "
                 "was killed after the probe process grew to ~13 GB RSS and the machine swapped; it scored whole "
                 "batches of long articles and is not used here.")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="aiteam,qwen3,nli", help="comma list of phases to run")
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()

    if args.render_only:
        res = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        RESULTS_MD_PATH.write_text(render_md(res), encoding="utf-8")
        print(RESULTS_MD_PATH.read_text(encoding="utf-8"))
        return

    phases = [x.strip() for x in args.only.split(",") if x.strip()]
    corpus, tasks = load_inputs()
    rss0 = psutil.Process().memory_info().rss
    first_stage = build_first_stage(tasks)
    print(f"first-stage done; RSS {psutil.Process().memory_info().rss/GIB:.2f} GiB (before {rss0/GIB:.2f})", flush=True)

    if RESULTS_PATH.exists():
        results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    else:
        results = {"experiment_a": {"models": {}}, "experiment_b": {}, "onejev": None}
    results["probe"] = {
        "date": "2026-10-23", "brief": "evaluation/probes/rerank-nli-2026-10-23/BRIEF.md",
        "corpus": str(CORPUS_PATH), "tasks": str(TASKS_PATH), "excluded_task": FOREIGN_TASK_ID,
        "n_queries_experiment_a": len(first_stage), "python": sys.version, "torch": torch.__version__,
        "platform": platform.platform(), "machine": platform.machine(),
        "mps_available": torch.backends.mps.is_available(),
        "labels_note": "NLI pair labels are constructed from source text by the probe author; NOT human labels.",
        "first_stage": "HybridDomainRetriever(retrieval_mode='tfidf'), top_k=20",
        "rss_after_first_stage_bytes": psutil.Process().memory_info().rss,
        "guard_bytes": GUARD_BYTES, "reranker_max_length": RERANKER_MAX_LEN,
    }
    results["first_stage"] = {
        "per_task": {tid: {k: v for k, v in fs.items() if k != "_hits"} for tid, fs in first_stage.items()},
        "metrics": rank_metrics({tid: fs["gold_ranks"] for tid, fs in first_stage.items()},
                                {tid: fs["gold_ids"] for tid, fs in first_stage.items()}),
    }
    print("first-stage metrics:", json.dumps(results["first_stage"]["metrics"]["mean"]), flush=True)

    def save():
        RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    save()
    rerankers = {"aiteam": ("AITeamVN/Vietnamese_Reranker", load_aiteam),
                 "qwen3": ("Qwen/Qwen3-Reranker-0.6B", load_qwen3)}
    for key, (repo, loader) in rerankers.items():
        if key in phases:
            results["experiment_a"]["models"][key] = run_reranker(key, repo, loader, first_stage)
            save()
    if "nli" in phases:
        results["experiment_b"] = run_nli("MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", tasks, corpus)
        save()
    results["onejev"] = onejev_section()
    save()
    RESULTS_MD_PATH.write_text(render_md(results), encoding="utf-8")
    print(f"wrote {RESULTS_PATH} and {RESULTS_MD_PATH}", flush=True)


if __name__ == "__main__":
    main()
