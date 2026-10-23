#!/usr/bin/env python3
"""Probe of the official Qev "System One" servers (OmniJev/OneJev1.6-0.8B and -4B), 23 Oct 2026.

Re-uses the inputs of the earlier local probe (evaluation/probes/rerank-nli-2026-10-23/results.json:
stored first-stage top-20 per task and the 29 constructed/real NLI pairs) and sends them to the
servers through ``src.model_runtime.QevHttpClient`` (the same client the ``qev_http`` backends use).

  * Experiment A: per-candidate ``noul`` yes/no relevance question, re-rank the stored top-20.
  * Experiment B: the 29 NLI pairs as a 3-option ``choice`` question, Vietnamese and English wording.
  * Local vs official: <=10 items run through the local re-implementation (SystemOneRunner, 0.8B)
    and compared with the official server's answers for the same items (RSS guard 4 GB).

The servers are SHARED remote GPUs reached through an existing SSH tunnel; this script is strictly
sequential (concurrency 1), never starts/stops a server and never touches the tunnels.  A failed
request is recorded as an error and is never replaced by a score.

Usage (from the repo root; needs only the standard library + requests for A/B, torch/transformers for `local`):
    PYTHONPATH=. .venv/bin/python evaluation/probes/qev-onejev-2026-10-23/probe_qev.py            # everything
    ... probe_qev.py --only A,B            # remote phases only (merged into results.json)
    ... probe_qev.py --only local          # local-vs-official agreement only
    ... probe_qev.py --render-only         # regenerate RESULTS.md from results.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

PROBE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROBE_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.model_runtime import ModelComponentError, QevHttpClient, doc_text  # noqa: E402

EARLIER_RESULTS = REPO_ROOT / "evaluation/probes/rerank-nli-2026-10-23/results.json"
CORPUS_PATH = REPO_ROOT / "data/corpus/labor_code_2019_official.json"
TASKS_PATH = REPO_ROOT / "evaluation/benchmarks/bll2019_v1/tasks.json"
RESULTS_PATH = PROBE_DIR / "results.json"
RESULTS_MD_PATH = PROBE_DIR / "RESULTS.md"
FOREIGN_TASK_ID = "BLL19-10-FOREIGN_SCOPE"

SERVERS = {
    "0.8B": {"base_url": "http://127.0.0.1:18001", "model": "OmniJev/OneJev1.6-0.8B"},
    "4B": {"base_url": "http://127.0.0.1:18004", "model": "OmniJev/OneJev1.6-4B"},
}
TIMEOUT_S = 120.0
MAX_CONSECUTIVE_ERRORS = 5
LABELS = ["entailment", "neutral", "contradiction"]
LOCAL_RSS_LIMIT = 4 * 1024 ** 3

# Experiment A statements (a noul question is a statement judged true/false).
A_WORDINGS = {
    "en": "The document contains information that directly answers the query",
    "vi": "Tài liệu chứa thông tin trả lời trực tiếp cho câu hỏi truy vấn",
}
# Experiment B: question + option descriptions. Option keys stay the English labels (they are what
# the response is keyed by and what QevHttpNLI supports); only the wording the model reads differs.
B_WORDINGS = {
    "vi": {
        "question": ("Căn cứ pháp lý (premise) có suy ra giả thuyết (hypothesis), mâu thuẫn với giả thuyết, "
                     "hay không liên quan đến giả thuyết?"),
        "options": {
            "entailment": "căn cứ nêu rõ hoặc suy ra được giả thuyết",
            "neutral": "căn cứ không khẳng định cũng không phủ định giả thuyết; thiếu thông tin",
            "contradiction": "căn cứ nêu điều không thể đồng thời đúng với giả thuyết",
        },
    },
    "en": {
        "question": "Does the premise entail the hypothesis, contradict it, or neither?",
        "options": {
            "entailment": "the premise states or logically implies the hypothesis",
            "neutral": "the premise neither supports nor contradicts the hypothesis; information is missing",
            "contradiction": "the premise states something incompatible with the hypothesis",
        },
    },
}
# Local-vs-official subset (<=10 items): NLI pair ids, and (task, article) rerank items.
LOCAL_NLI_IDS = [
    "BLL19-01-PROBATION::entailment",
    "BLL19-04-ABSENCE::contradiction",
    "BLL19-03-NOTICE::neutral",
    "BLL19-05-PREGNANCY::entailment",
    "real-output-dieu17-deposit",
]
LOCAL_RERANK_ITEMS = [
    ("BLL19-01-PROBATION", "Dieu_25"),
    ("BLL19-01-PROBATION", "Dieu_53"),
    ("BLL19-05-PREGNANCY", "Dieu_37"),
    ("BLL19-05-PREGNANCY", "Dieu_36"),
    ("BLL19-09-DEPOSIT", "Dieu_17"),
]
LOCAL_WORDING = "en"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_results():
    return load_json(RESULTS_PATH) if RESULTS_PATH.exists() else {}


def save_results(res):
    tmp = RESULTS_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    tmp.replace(RESULTS_PATH)


def pct(values, q):
    s = sorted(values)
    if not s:
        return None
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def latency_summary(wall_ms, server_s):
    out = {"n": len(wall_ms)}
    if wall_ms:
        out.update({"wall_median_ms": statistics.median(wall_ms), "wall_p95_ms": pct(wall_ms, 0.95),
                    "wall_mean_ms": statistics.fmean(wall_ms), "wall_min_ms": min(wall_ms),
                    "wall_max_ms": max(wall_ms)})
    srv = [s * 1000.0 for s in server_s if isinstance(s, (int, float))]
    if srv:
        out.update({"server_total_median_ms": statistics.median(srv), "server_total_p95_ms": pct(srv, 0.95)})
        net = [w - s for w, s in zip(wall_ms, [x * 1000.0 if isinstance(x, (int, float)) else None
                                                for x in server_s]) if s is not None]
        if net:
            out["client_minus_server_median_ms"] = statistics.median(net)
    return out


def new_client(name):
    cfg = SERVERS[name]
    return QevHttpClient(cfg["base_url"], cfg["model"], timeout_seconds=TIMEOUT_S, allow_remote=False)


def server_info(name):
    """Health + model listing of one server (read-only GETs)."""
    import requests
    cfg = SERVERS[name]
    out = {"base_url": cfg["base_url"], "configured_model": cfg["model"]}
    try:
        out["health"] = requests.get(cfg["base_url"] + "/health", timeout=15).json()
        models = requests.get(cfg["base_url"] + "/v1/models", timeout=15).json()["models"]
        out["models_listing_first_entry"] = models[0]
        out["models_listing_n"] = len(models)
    except Exception as exc:  # noqa: BLE001 - recorded
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


# --------------------------------------------------------------------------- #
# inputs (re-used from the earlier local probe)
# --------------------------------------------------------------------------- #

def load_inputs():
    earlier = load_json(EARLIER_RESULTS)
    corpus = {d["article_id"]: d for d in load_json(CORPUS_PATH)}
    tasks = {t["task_id"]: t for t in load_json(TASKS_PATH)}
    first = earlier["first_stage"]["per_task"]
    per_task = {}
    for tid, rec in first.items():
        per_task[tid] = {
            "question": rec["question"],
            "gold_ids": rec["gold_ids"],
            "candidate_ids": [c["article_id"] for c in rec["candidates"]],
        }
        assert tasks[tid]["question"] == rec["question"], tid
    return earlier, corpus, per_task


# --------------------------------------------------------------------------- #
# Experiment A
# --------------------------------------------------------------------------- #

def gold_ranks(scores, candidate_ids, gold_ids, mode):
    """Rank (1-based) of each gold id given per-candidate scores (None = unscored = ranked last).

    mode: 'stable' = ties keep first-stage order (what BaseReranker.rerank does);
          'pessimistic' = gold placed after every tied candidate; 'optimistic' = before.
    """
    ranks = {}
    for g in gold_ids:
        if g not in candidate_ids:
            ranks[g] = None
            continue
        gi = candidate_ids.index(g)
        gs = scores[gi] if scores[gi] is not None else -math.inf
        better = ties_before = ties_after = 0
        for i, s in enumerate(scores):
            if i == gi:
                continue
            s = s if s is not None else -math.inf
            if s > gs:
                better += 1
            elif s == gs:
                if i < gi:
                    ties_before += 1
                else:
                    ties_after += 1
        if mode == "stable":
            ranks[g] = better + ties_before + 1
        elif mode == "pessimistic":
            ranks[g] = better + ties_before + ties_after + 1
        else:
            ranks[g] = better + 1
    return ranks


def rank_metrics(per_task_ranks, per_task_gold, ks=(1, 3, 5)):
    rows = []
    for tid, ranks in per_task_ranks.items():
        gold = per_task_gold[tid]
        found = [r for r in (ranks[g] for g in gold) if r is not None]
        rows.append({"recall": {k: sum(1 for r in found if r <= k) / len(gold) for k in ks},
                     "rr": (1.0 / min(found)) if found else 0.0})
    mean = {f"Recall@{k}": statistics.fmean(r["recall"][k] for r in rows) for k in ks}
    mean["MRR"] = statistics.fmean(r["rr"] for r in rows)
    return mean


def run_experiment_a(name, wording, per_task, corpus):
    client = new_client(name)
    question = A_WORDINGS[wording]
    rec = {"server": name, "model": SERVERS[name]["model"], "wording": wording, "question": question,
           "status": "ok", "errors": [], "per_task": {}}
    wall, srv = [], []
    consecutive = 0
    try:
        # one unrecorded warm-up request (first request pays connection/cache costs)
        first_tid = next(iter(per_task))
        first_doc = corpus[per_task[first_tid]["candidate_ids"][0]]
        t0 = time.perf_counter()
        client.decide_yes_no({"query": per_task[first_tid]["question"], "document": doc_text(first_doc)}, question)
        rec["warmup_ms"] = (time.perf_counter() - t0) * 1000.0
    except ModelComponentError as exc:
        rec["status"] = "aborted"
        rec["errors"].append({"where": "warmup", "kind": exc.kind, "error": str(exc)})
        return rec
    for tid, task in per_task.items():
        cands = []
        for idx, aid in enumerate(task["candidate_ids"]):
            item = {"article_id": aid, "input_index": idx, "score": None}
            try:
                item["score"] = client.decide_yes_no(
                    {"query": task["question"], "document": doc_text(corpus[aid])}, question)
                d = client.last_details
                item.update({"wall_ms": d["wall_ms"], "server_total_s": d["server_total_s"],
                             "server_forward_s": d["server_forward_s"], "input_tokens": d["input_tokens"],
                             "prompt_sha256": d["prompt_sha256"]})
                wall.append(d["wall_ms"])
                srv.append(d["server_total_s"])
                consecutive = 0
            except ModelComponentError as exc:
                item["error"] = {"kind": exc.kind, "message": str(exc)[:400]}
                rec["errors"].append({"task_id": tid, "article_id": aid, "kind": exc.kind, "error": str(exc)[:400]})
                consecutive += 1
            cands.append(item)
            if consecutive >= MAX_CONSECUTIVE_ERRORS:
                rec["status"] = "aborted"
                rec["errors"].append({"where": "abort", "error": f"{MAX_CONSECUTIVE_ERRORS} consecutive errors"})
                break
        rec["per_task"][tid] = {"candidates": cands}
        if rec["status"] == "aborted":
            break
        print(f"[A {name}/{wording}] {tid} done ({sum(1 for c in cands if c.get('score') is not None)}/{len(cands)} scored)",
              flush=True)
    rec["latency"] = latency_summary(wall, srv)
    if rec["status"] == "ok":
        score_metrics(rec, per_task)
    return rec


def score_metrics(rec, per_task):
    rec["metrics"] = {}
    rec["gold_ranks"] = {}
    gold = {tid: per_task[tid]["gold_ids"] for tid in rec["per_task"]}
    for mode in ("stable", "pessimistic", "optimistic"):
        ranks = {}
        for tid, t in rec["per_task"].items():
            scores = [c["score"] for c in t["candidates"]]
            ranks[tid] = gold_ranks(scores, per_task[tid]["candidate_ids"], gold[tid], mode)
        rec["gold_ranks"][mode] = ranks
        rec["metrics"][mode] = rank_metrics(ranks, gold)
    # score diagnostics: ties and saturation
    n_gold_ties = 0
    saturated = 0
    total = 0
    for tid, t in rec["per_task"].items():
        scores = [c["score"] for c in t["candidates"]]
        for g in gold[tid]:
            if g in per_task[tid]["candidate_ids"]:
                gs = scores[per_task[tid]["candidate_ids"].index(g)]
                if sum(1 for s in scores if s == gs) > 1:
                    n_gold_ties += 1
        for s in scores:
            total += 1
            saturated += s is not None and (s >= 0.999999 or s <= 0.000001)
    rec["score_diagnostics"] = {"gold_articles_tied_with_another_candidate": n_gold_ties,
                                "scores_at_0_or_1_after_6dp_rounding": saturated, "n_scores": total}


# --------------------------------------------------------------------------- #
# Experiment B
# --------------------------------------------------------------------------- #

def run_experiment_b(name, wording, pairs):
    client = new_client(name)
    w = B_WORDINGS[wording]
    rec = {"server": name, "model": SERVERS[name]["model"], "wording": wording, "question": w["question"],
           "options": w["options"], "status": "ok", "errors": [], "pairs": []}
    try:
        client.decide_choice({"premise": pairs[0]["premise"], "hypothesis": pairs[0]["hypothesis"]},
                             w["question"], w["options"])
    except ModelComponentError as exc:
        rec["status"] = "aborted"
        rec["errors"].append({"where": "warmup", "kind": exc.kind, "error": str(exc)})
        return rec
    wall, srv = [], []
    consecutive = 0
    for p in pairs:
        item = {"id": p["id"], "kind": p["kind"], "expected": p["expected"]}
        try:
            probs = client.decide_choice({"premise": p["premise"], "hypothesis": p["hypothesis"]},
                                         w["question"], w["options"])
            d = client.last_details
            item.update({"probs": probs, "predicted": max(LABELS, key=lambda k: (probs[k], -LABELS.index(k))),
                         "server_choice": d.get("choice"), "server_confidence": d.get("confidence"),
                         "wall_ms": d["wall_ms"], "server_total_s": d["server_total_s"],
                         "input_tokens": d["input_tokens"], "prompt_sha256": d["prompt_sha256"]})
            item["correct"] = item["predicted"] == p["expected"]
            wall.append(d["wall_ms"])
            srv.append(d["server_total_s"])
            consecutive = 0
        except ModelComponentError as exc:
            item["error"] = {"kind": exc.kind, "message": str(exc)[:400]}
            rec["errors"].append({"id": p["id"], "kind": exc.kind, "error": str(exc)[:400]})
            consecutive += 1
        rec["pairs"].append(item)
        if consecutive >= MAX_CONSECUTIVE_ERRORS:
            rec["status"] = "aborted"
            break
    rec["latency"] = latency_summary(wall, srv)
    rec["summary"] = summarise_nli(rec["pairs"])
    print(f"[B {name}/{wording}] constructed accuracy {rec['summary']['constructed_accuracy']}", flush=True)
    return rec


def summarise_nli(items):
    scored = [i for i in items if "probs" in i]
    out = {"n_pairs": len(items), "n_scored": len(scored), "n_errors": len(items) - len(scored), "by_class": {}}
    for cls in LABELS:
        rows = [i for i in scored if i["kind"] == cls]
        preds = {l: sum(1 for i in rows if i["predicted"] == l) for l in LABELS}
        out["by_class"][cls] = {"n": len([i for i in items if i["kind"] == cls]), "scored": len(rows),
                                "correct": sum(i["correct"] for i in rows), "predicted": preds,
                                "accuracy": (sum(i["correct"] for i in rows) / len(rows)) if rows else None}
    cons = [i for i in scored if i["kind"] in LABELS]
    out["constructed_accuracy"] = (sum(i["correct"] for i in cons) / len(cons)) if cons else None
    out["constructed_correct"] = sum(i["correct"] for i in cons)
    out["constructed_n"] = len(cons)
    real = [i for i in scored if i["kind"] == "real_model_output"]
    out["real_output"] = {"n": len(real), "correct": sum(i["correct"] for i in real)}
    # calibration notes (top-1 probability vs correctness; tiny sample, descriptive only)
    top = lambda i: max(i["probs"].values())  # noqa: E731
    right = [top(i) for i in scored if i["correct"]]
    wrong = [top(i) for i in scored if not i["correct"]]
    hi = [i for i in scored if top(i) >= 0.9]
    out["calibration"] = {
        "mean_top1_prob_correct": statistics.fmean(right) if right else None,
        "mean_top1_prob_wrong": statistics.fmean(wrong) if wrong else None,
        "n_top1_ge_0.9": len(hi), "n_top1_ge_0.9_correct": sum(i["correct"] for i in hi),
        "n_wrong_with_top1_ge_0.9": sum(1 for i in hi if not i["correct"]),
    }
    return out


# --------------------------------------------------------------------------- #
# Local re-implementation vs official server
# --------------------------------------------------------------------------- #

def rss_bytes():
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True).stdout
    return int(out.strip() or 0) * 1024


def memory_free_pct():
    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=20).stdout
        for line in out.splitlines():
            if "free percentage" in line:
                return int(line.split(":")[1].strip().rstrip("%"))
    except Exception:  # noqa: BLE001
        pass
    return None


def heavy_python_procs(min_rss_kb=2 * 1024 * 1024):
    out = subprocess.run(["ps", "-axo", "pid=,rss=,command="], capture_output=True, text=True).stdout
    found = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and int(parts[0]) != os.getpid() and parts[1].isdigit() \
                and int(parts[1]) > min_rss_kb and "python" in parts[2].lower():
            found.append({"pid": int(parts[0]), "rss_kb": int(parts[1]), "cmd": parts[2][:140]})
    return found


class RssWatchdog(threading.Thread):
    """Hard-aborts the process (os._exit(3)) if RSS (+ MPS driver allocation) exceeds the limit."""

    def __init__(self, limit):
        super().__init__(daemon=True)
        self.limit, self.peak, self.stop_flag = limit, 0, threading.Event()

    def run(self):
        while not self.stop_flag.is_set():
            total = rss_bytes()
            try:
                import torch
                if torch.backends.mps.is_available():
                    total += int(torch.mps.driver_allocated_memory())
            except Exception:  # noqa: BLE001
                pass
            self.peak = max(self.peak, total)
            if total > self.limit:
                sys.stderr.write(f"RSS GUARD: {total / 2**30:.2f} GiB > {self.limit / 2**30:.0f} GiB; aborting\n")
                sys.stderr.flush()
                os._exit(3)
            self.stop_flag.wait(0.2)


def run_local_vs_official(res, per_task, corpus, earlier):
    """Local SystemOneRunner (0.8B) vs the official 0.8B server on <=10 items, same wording."""
    out = {"model": SERVERS["0.8B"]["model"], "wording": LOCAL_WORDING, "limit_bytes": LOCAL_RSS_LIMIT,
           "status": "ok", "items": []}
    # official answers come from the recorded experiments (same client, same wording)
    try:
        a_rec = res["experiment_a"]["0.8B"][LOCAL_WORDING]
        b_rec = res["experiment_b"]["0.8B"][LOCAL_WORDING]
    except KeyError:
        out["status"] = "error"
        out["error"] = "run experiments A and B for the 0.8B server first (--only A,B)"
        return out
    pair_by_id = {p["id"]: p for p in earlier["experiment_b"]["pairs"]}
    b_by_id = {p["id"]: p for p in b_rec["pairs"]}
    items = []
    for pid in LOCAL_NLI_IDS:
        items.append({"kind": "nli", "id": pid, "premise": pair_by_id[pid]["premise"],
                      "hypothesis": pair_by_id[pid]["hypothesis"], "official": b_by_id[pid]})
    for tid, aid in LOCAL_RERANK_ITEMS:
        cand = next(c for c in a_rec["per_task"][tid]["candidates"] if c["article_id"] == aid)
        items.append({"kind": "rerank", "id": f"{tid}::{aid}", "query": per_task[tid]["question"],
                      "document": doc_text(corpus[aid]), "official": cand})
    assert len(items) <= 10

    # resource gate: wait (<=10 min) for a quiet machine, otherwise do not run
    waited = 0
    while True:
        free, heavy = memory_free_pct(), heavy_python_procs()
        if (free is None or free >= 25) and not heavy:
            break
        if waited >= 600:
            out["status"] = "skipped"
            out["error"] = f"machine busy for 600 s (free={free}%, heavy python procs={heavy}); not run"
            return out
        print(f"[local] waiting: free={free}% heavy={len(heavy)}", flush=True)
        time.sleep(30)
        waited += 30
    out["waited_s"] = waited

    watchdog = RssWatchdog(LOCAL_RSS_LIMIT)
    watchdog.start()
    try:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("HF_DEACTIVATE_ASYNC_LOAD", "1")
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        from src.model_runtime import SystemOneRunner
        runner = SystemOneRunner(SERVERS["0.8B"]["model"], device="auto", local_files_only=True)
        t0 = time.perf_counter()
        runner.load()
        out["load_seconds"] = time.perf_counter() - t0
        out["device"], out["dtype"] = runner.device, runner.dtype_name
        for it in items:
            rec = {"kind": it["kind"], "id": it["id"]}
            off = it["official"]
            if it["kind"] == "nli":
                w = B_WORDINGS[LOCAL_WORDING]
                probs = runner.decide_choice({"premise": it["premise"], "hypothesis": it["hypothesis"]},
                                             w["question"], w["options"])
                rec["local"] = probs
                rec["official"] = off["probs"]
                rec["local_argmax"] = max(LABELS, key=lambda k: probs[k])
                rec["official_argmax"] = off["predicted"]
                rec["argmax_agree"] = rec["local_argmax"] == rec["official_argmax"]
                rec["max_abs_diff"] = max(abs(probs[k] - off["probs"][k]) for k in LABELS)
            else:
                p_yes = runner.decide_yes_no({"query": it["query"], "document": it["document"]},
                                             A_WORDINGS[LOCAL_WORDING])
                rec["local"] = p_yes
                rec["official"] = off["score"]
                rec["argmax_agree"] = (p_yes >= 0.5) == (off["score"] >= 0.5)
                rec["max_abs_diff"] = abs(p_yes - off["score"])
            rec["local_prompt_tokens"] = runner.last_details["prompt_tokens"]
            rec["official_input_tokens"] = off["input_tokens"]
            rec["local_allowed_token_mass"] = runner.last_details["allowed_token_mass"]
            rec["local_wall_ms"] = runner.last_details["wall_ms"]
            out["items"].append(rec)
            print(f"[local] {it['id']}: diff={rec['max_abs_diff']:.4f} tokens {rec['local_prompt_tokens']} vs "
                  f"{rec['official_input_tokens']}", flush=True)
        runner.unload()
    except Exception as exc:  # noqa: BLE001 - recorded, never replaced by numbers
        out["status"] = "error"
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["traceback"] = traceback.format_exc()[-1500:]
    finally:
        watchdog.stop_flag.set()
        out["peak_rss_plus_mps_bytes"] = watchdog.peak
    its = out["items"]
    if its:
        out["summary"] = {
            "n": len(its),
            "argmax_agree": sum(1 for i in its if i["argmax_agree"]),
            "token_count_equal": sum(1 for i in its if i["local_prompt_tokens"] == i["official_input_tokens"]),
            "mean_abs_diff": statistics.fmean(i["max_abs_diff"] for i in its),
            "max_abs_diff": max(i["max_abs_diff"] for i in its),
            "n_diff_gt_0.05": sum(1 for i in its if i["max_abs_diff"] > 0.05),
        }
    return out


# --------------------------------------------------------------------------- #
# main / rendering
# --------------------------------------------------------------------------- #

def fmt(x, nd=3):
    return "-" if x is None else f"{x:.{nd}f}"


def render_md(res):
    from textwrap import dedent
    earlier = load_json(EARLIER_RESULTS)
    L = []
    w = L.append
    w("# Official Qev / OneJev servers: re-ranking and NLI probe (23 Oct 2026)\n")
    w(dedent("""\
    ## Caveats (read first)

    - **Tiny sample**: 9 answerable queries x 20 stored first-stage candidates; 29 NLI pairs. One query moves Recall/MRR by 0.11, one pair by 0.034. This is a probe, not a benchmark.
    - **NLI labels are constructed from source text by the earlier probe author, not human labels** (27 constructed + 2 real model outputs, same pairs as `evaluation/probes/rerank-nli-2026-10-23`).
    - **Remote shared GPU**: both models run on GPU server 82 (shared, other users' load unknown) behind an SSH tunnel; latencies include the network and queueing and are NOT comparable with the local MPS timings. The model runs remotely, not on this Mac.
    - **Probabilities are rounded to 6 decimals by the server**, so near-certain candidates tie; ties are reported (stable tie-break = first-stage order, as the backend does; pessimistic/optimistic bounds below).
    - **Not report evidence.** Rank metrics on gold article IDs only; nothing here is a reviewed answer-correctness result. Do not copy into D2 report tables.
    - Option/candidate order bias (the model reads letters A/B/C in a fixed order) was not tested.
    - The `/v1/models` listing of each server answers to every OneJev alias; the `/health` `model` field is the only reliable identity (checked by the client).
    """))
    srv = res.get("servers", {})
    w("## Servers\n")
    w("| server | base_url (SSH tunnel) | /health | Qev version |\n|---|---|---|---|")
    for n, s in srv.items():
        w(f"| {n} | {s.get('base_url')} | {json.dumps(s.get('health'))} | {res.get('probe', {}).get('qev_version', '0.1.4 (OpenAPI info)')} |")
    w("")
    # ---------------- Experiment A
    ea = res.get("experiment_a", {})
    fs = earlier["first_stage"]["metrics"]["mean"]
    w("## Experiment A: re-ranking the stored first-stage top-20 (9 tasks)\n")
    w("Per-candidate `noul` yes/no question, state `{query, document}` (full article text, nothing truncated); score = P(yes). Stable tie-break; `[pess., opt.]` = bounds if ties are resolved against/for the gold article.\n")
    w("| System | Recall@1 | Recall@3 | Recall@5 | MRR | MRR [pess., opt.] | median ms/req (client) | p95 ms | server-side median ms | status |\n|---|---|---|---|---|---|---|---|---|---|")
    w(f"| first stage (HybridDomainRetriever tfidf) | {fmt(fs['Recall@1'])} | {fmt(fs['Recall@3'])} | {fmt(fs['Recall@5'])} | {fmt(fs['MRR'])} | - | - | - | - | stored |")
    for mname in ("aiteam", "qwen3"):
        m = earlier["experiment_a"]["models"][mname]
        mm = m["metrics"]["mean"]
        lat = m["per_pair_latency"]
        w(f"| local {m['model']} ({m['device']} {m['dtype']}) | {fmt(mm['Recall@1'])} | {fmt(mm['Recall@3'])} | {fmt(mm['Recall@5'])} | {fmt(mm['MRR'])} | - | {lat['median_ms']:.0f} (local) | {lat['p95_ms']:.0f} | - | earlier probe |")
    for sname in ("0.8B", "4B"):
        for wording in ("en", "vi"):
            r = ea.get(sname, {}).get(wording)
            if not r:
                continue
            if "metrics" not in r:
                w(f"| Qev {sname} [{wording}] | - | - | - | - | - | - | - | - | {r['status']}: {len(r['errors'])} errors |")
                continue
            st, pe, op = r["metrics"]["stable"], r["metrics"]["pessimistic"], r["metrics"]["optimistic"]
            lat = r["latency"]
            w(f"| Qev OneJev1.6-{sname} [{wording}] | {fmt(st['Recall@1'])} | {fmt(st['Recall@3'])} | {fmt(st['Recall@5'])} | {fmt(st['MRR'])} | [{fmt(pe['MRR'])}, {fmt(op['MRR'])}] | {lat.get('wall_median_ms', 0):.0f} | {lat.get('wall_p95_ms', 0):.0f} | {lat.get('server_total_median_ms', 0):.0f} | ok, {len(r['errors'])} errors |")
    w("\nWording: `en` = \"%s\"; `vi` = \"%s\".\n" % (A_WORDINGS["en"], A_WORDINGS["vi"]))
    # per-task gold ranks
    w("### Per-task gold ranks (stable tie-break; `absent` = not in top-20)\n")
    cols = [("first-stage", None)]
    for sname in ("0.8B", "4B"):
        for wording in ("en", "vi"):
            if ea.get(sname, {}).get(wording, {}).get("gold_ranks"):
                cols.append((f"{sname} {wording}", (sname, wording)))
    cols_local = [("Vietnamese_Reranker", "aiteam"), ("Qwen3-Reranker-0.6B", "qwen3")]
    w("| Task | " + " | ".join(c[0] for c in cols) + " | " + " | ".join(c[0] for c in cols_local) + " |")
    w("|---|" + "---|" * (len(cols) + len(cols_local)))
    tids = list(earlier["first_stage"]["per_task"])
    def fmt_ranks(d):
        return ", ".join(f"{g}:{r if r is not None else 'absent'}" for g, r in d.items())
    for tid in tids:
        row = [fmt_ranks(earlier["first_stage"]["per_task"][tid]["gold_ranks"])]
        for _, key in cols[1:]:
            row.append(fmt_ranks(ea[key[0]][key[1]]["gold_ranks"]["stable"][tid]))
        for _, mname in cols_local:
            row.append(fmt_ranks(earlier["experiment_a"]["models"][mname]["per_task"][tid]["gold_ranks_after"]))
        w(f"| {tid} | " + " | ".join(row) + " |")
    w("")
    for sname in ("0.8B", "4B"):
        for wording in ("en", "vi"):
            r = ea.get(sname, {}).get(wording)
            if r and "score_diagnostics" in r:
                d = r["score_diagnostics"]
                w(f"- Qev {sname} [{wording}]: {d['scores_at_0_or_1_after_6dp_rounding']}/{d['n_scores']} scores are 0 or 1 after rounding; "
                  f"{d['gold_articles_tied_with_another_candidate']} gold articles tie with another candidate; "
                  f"{len(r['errors'])} request errors.")
    w("")
    # ---------------- Experiment B
    eb = res.get("experiment_b", {})
    mb = earlier["experiment_b"]
    w("## Experiment B: 29 NLI pairs as a 3-option `choice` question\n")
    w("State `{premise, hypothesis}`; options entailment / neutral / contradiction (option order = that order). Accuracy per constructed class (n=9 each); real = 2 real model outputs.\n")
    w("| System | entailment | neutral | contradiction | all constructed (27) | real outputs (2) | median ms/req | p95 ms | status |\n|---|---|---|---|---|---|---|---|---|")
    ab = mb["accuracy_by_constructed_class"]
    w(f"| local {mb['model']} ({mb['device']} {mb['dtype']}) | {ab['entailment']['correct']}/9 | {ab['neutral']['correct']}/9 | {ab['contradiction']['correct']}/9 | {mb['constructed_accuracy']*27:.0f}/27 = {fmt(mb['constructed_accuracy'])} | {mb['real_output_accuracy']['correct']}/2 | {mb['per_pair_latency']['median_ms']:.0f} (local) | {mb['per_pair_latency']['p95_ms']:.0f} | earlier probe |")
    for sname in ("0.8B", "4B"):
        for wording in ("vi", "en"):
            r = eb.get(sname, {}).get(wording)
            if not r:
                continue
            s = r["summary"]
            bc = s["by_class"]
            lat = r["latency"]
            w(f"| Qev OneJev1.6-{sname} [{wording}] | {bc['entailment']['correct']}/9 | {bc['neutral']['correct']}/9 | {bc['contradiction']['correct']}/9 | {s['constructed_correct']}/{s['constructed_n']} = {fmt(s['constructed_accuracy'])} | {s['real_output']['correct']}/{s['real_output']['n']} | {lat.get('wall_median_ms', 0):.0f} | {lat.get('wall_p95_ms', 0):.0f} | {r['status']}, {s['n_errors']} errors |")
    w("\nWording `vi`: question \"%s\" with Vietnamese option descriptions; `en`: the English wording used by `DecisionModelNLI`/`QevHttpNLI` by default.\n" % B_WORDINGS["vi"]["question"])
    w("### Predicted-label distribution per true class (rows = true class; columns = predicted E / N / C)\n")
    w("| System | true entailment | true neutral | true contradiction |\n|---|---|---|---|")
    w("| local mDeBERTa | " + " | ".join("/".join(str(ab[c]["predictions"][l]) for l in LABELS) for c in LABELS) + " |")
    for sname in ("0.8B", "4B"):
        for wording in ("vi", "en"):
            r = eb.get(sname, {}).get(wording)
            if r:
                bc = r["summary"]["by_class"]
                w(f"| Qev {sname} [{wording}] | " + " | ".join("/".join(str(bc[c]["predicted"][l]) for l in LABELS) for c in LABELS) + " |")
    w("\n### Calibration notes (descriptive; n=29, not a calibration study)\n")
    w("| System | mean top-1 prob (correct) | mean top-1 prob (wrong) | predictions with top-1 >= 0.9 | of which wrong |\n|---|---|---|---|---|")
    for sname in ("0.8B", "4B"):
        for wording in ("vi", "en"):
            r = eb.get(sname, {}).get(wording)
            if r:
                c = r["summary"]["calibration"]
                w(f"| Qev {sname} [{wording}] | {fmt(c['mean_top1_prob_correct'])} | {fmt(c['mean_top1_prob_wrong'])} | {c['n_top1_ge_0.9']} | {c['n_wrong_with_top1_ge_0.9']} |")
    mp = mb["pairs"]
    right = [max(p['probs'].values()) for p in mp if p['correct']]
    wrong = [max(p['probs'].values()) for p in mp if not p['correct']]
    hi = [p for p in mp if max(p['probs'].values()) >= 0.9]
    w(f"| local mDeBERTa | {fmt(statistics.fmean(right))} | {fmt(statistics.fmean(wrong))} | {len(hi)} | {sum(1 for p in hi if not p['correct'])} |")
    w("")
    # per-pair table
    w("### Per-pair predictions (predicted label, P(predicted); `*` = wrong)\n")
    keys = [(s, wd) for s in ("0.8B", "4B") for wd in ("vi", "en") if eb.get(s, {}).get(wd)]
    w("| Pair | expected | mDeBERTa | " + " | ".join(f"{s} {wd}" for s, wd in keys) + " |")
    w("|---|---|---|" + "---|" * len(keys))
    by = {(s, wd): {p["id"]: p for p in eb[s][wd]["pairs"]} for s, wd in keys}
    for p in mb["pairs"]:
        row = [f"{p['predicted'][:4]} {max(p['probs'].values()):.2f}{'' if p['correct'] else '*'}"]
        for k in keys:
            q = by[k][p["id"]]
            if "probs" not in q:
                row.append("ERROR")
            else:
                row.append(f"{q['predicted'][:4]} {max(q['probs'].values()):.2f}{'' if q['correct'] else '*'}")
        w(f"| {p['id']} | {p['expected'][:4]} | " + " | ".join(row) + " |")
    w("")
    # ---------------- local vs official
    lv = res.get("local_vs_official")
    w("## Local re-implementation (`SystemOneRunner`) vs the official 0.8B server\n")
    if not lv:
        w("Not run.\n")
    else:
        w(f"Status: **{lv['status']}**" + (f" ({lv.get('error')})" if lv.get("error") else "") + f". Wording `{lv['wording']}`; local device {lv.get('device')} {lv.get('dtype')}; peak RSS+MPS driver {lv.get('peak_rss_plus_mps_bytes', 0) / 2**30:.2f} GiB (limit {lv['limit_bytes'] / 2**30:.0f} GiB); load {fmt(lv.get('load_seconds'), 1)} s.\n")
        if lv.get("summary"):
            s = lv["summary"]
            w(f"Items: {s['n']} (5 NLI pairs + 5 rerank candidates). Decision agreement (argmax / P(yes)>=0.5): **{s['argmax_agree']}/{s['n']}**. Prompt token counts equal: {s['token_count_equal']}/{s['n']}. Mean max |dP|: {s['mean_abs_diff']:.4f}; max |dP|: {s['max_abs_diff']:.4f}; items with |dP| > 0.05: {s['n_diff_gt_0.05']}.\n")
            w("| Item | local | official | agree | max abs dP | local tokens | official tokens |\n|---|---|---|---|---|---|---|")
            for i in lv["items"]:
                if i["kind"] == "nli":
                    loc = " / ".join(f"{i['local'][k]:.3f}" for k in LABELS)
                    off = " / ".join(f"{i['official'][k]:.3f}" for k in LABELS)
                else:
                    loc, off = f"{i['local']:.3f}", f"{i['official']:.3f}"
                w(f"| {i['id']} | {loc} | {off} | {'yes' if i['argmax_agree'] else 'NO'} | {i['max_abs_diff']:.4f} | {i['local_prompt_tokens']} | {i['official_input_tokens']} |")
            w("\n(NLI columns are P(E) / P(N) / P(C).)\n")
    # ---------------- observations (specific to the recorded run)
    w("## Observations on the recorded run (23 Oct 2026; re-check after any re-run)\n")
    w(dedent("""\
    - **Re-ranking**: on these 9 queries neither Qev model improved on the stored first stage (MRR 0.944) nor on the two local rerankers (MRR 1.000 each); 0.8B reached MRR 0.889, 4B 0.840 (en) / 0.785 (vi). The 4B model put the pregnancy article (Dieu_37) at rank 15-16 of 20, and the deposit article (Dieu_17) at rank 2. Differences are 1-2 queries; no ranking of the models is justified by this sample. The English statement was not worse than the Vietnamese one.
    - **NLI**: constructed-label accuracy 20/27 (0.8B) and 22/27 (4B) vs 19/27 for mDeBERTa; the wording language (vi/en) made no difference to the 0.8B predictions and none to the 4B ones. The same pairs fail for every model (pregnancy and unlawful-resignation entailments predicted neutral; the deposit entailment predicted contradiction) which points at the constructed pairs/hypothesis phrasing as much as at the models. The 0.8B model called the real deposit output ("employer may require a deposit") entailment (wrong), the 4B model and mDeBERTa called it contradiction.
    - **Calibration**: Qev top-1 probabilities are moderate (mean 0.83-0.87 when correct, 0.75-0.81 when wrong), so they separate right from wrong only weakly; mDeBERTa is near-certain (0.99) even when wrong. Probabilities are model outputs of unverified calibration, not evidence of correctness.
    - **Latency**: ~0.45-0.52 s per request seen from this Mac, of which the server reports only ~0.05 s (0.8B) / ~0.08 s (4B); the remaining ~0.41-0.43 s is tunnel/network and HTTP overhead. Sequential rerank of 20 candidates therefore costs ~9-10 s regardless of model size here. Timings are for a shared GPU and a single tunnel and may vary.
    - **Local vs official**: the local re-implementation matched the official 0.8B server on prompt token count and decision for all 10 items; remaining differences (<= 0.01) are consistent with bf16 on MPS vs the server and 6-decimal rounding. This supports, but with n=10 does not prove, that `SystemOneRunner` reproduces the official prompt.
    """))
    # ---------------- failures
    w("## Failures and errors\n")
    any_err = False
    for sname, d in ea.items():
        for wording, r in d.items():
            for e in r.get("errors", []):
                any_err = True
                w(f"- A {sname}/{wording}: {json.dumps(e, ensure_ascii=False)}")
    for sname, d in eb.items():
        for wording, r in d.items():
            for e in r.get("errors", []):
                any_err = True
                w(f"- B {sname}/{wording}: {json.dumps(e, ensure_ascii=False)}")
    for e in res.get("failures", []):
        any_err = True
        w(f"- {json.dumps(e, ensure_ascii=False)}")
    if not any_err:
        w("None recorded in results.json.")
    w("")
    RESULTS_MD_PATH.write_text("\n".join(L), encoding="utf-8")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="A,B,local", help="comma list of phases: A,B,local")
    ap.add_argument("--servers", default="0.8B,4B")
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args()
    if args.render_only:
        print(render_md(load_results()))
        return
    phases = {p.strip() for p in args.only.split(",")}
    names = [s.strip() for s in args.servers.split(",")]
    res = load_results()
    earlier, corpus, per_task = load_inputs()
    res["probe"] = {
        "date": "2026-10-23", "python": sys.version.split()[0], "platform": platform.platform(),
        "client": "src.model_runtime.QevHttpClient", "timeout_seconds": TIMEOUT_S, "concurrency": 1,
        "earlier_probe": "evaluation/probes/rerank-nli-2026-10-23/results.json",
        "n_tasks": len(per_task), "candidates_per_task": 20,
        "labels_note": "NLI pair labels are constructed from source text, not human labels.",
        "qev_version": "0.1.4 (OpenAPI info.version of qev_openapi_18001.json)",
        "a_wordings": A_WORDINGS, "b_wordings": B_WORDINGS,
    }
    res.setdefault("servers", {}).update({n: server_info(n) for n in names})
    save_results(res)
    pairs = earlier["experiment_b"]["pairs"]
    if "A" in phases:
        for n in names:
            for wording in ("en", "vi"):
                res.setdefault("experiment_a", {}).setdefault(n, {})[wording] = run_experiment_a(n, wording, per_task, corpus)
                save_results(res)
    if "B" in phases:
        for n in names:
            for wording in ("vi", "en"):
                res.setdefault("experiment_b", {}).setdefault(n, {})[wording] = run_experiment_b(n, wording, pairs)
                save_results(res)
    if "local" in phases:
        res["local_vs_official"] = run_local_vs_official(res, per_task, corpus, earlier)
        save_results(res)
    print(render_md(res))


if __name__ == "__main__":
    main()
