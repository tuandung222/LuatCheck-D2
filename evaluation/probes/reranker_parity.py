#!/usr/bin/env python3
"""Reranker runtime parity + latency probe (real inference only; no stand-ins).

Question answered: does a serving runtime (llama.cpp GGUF, torch fp16 on CUDA, ...) of
AITeamVN/Vietnamese_Reranker rank the *benchmark's own* candidate sets like the reference runtime
(torch fp32 on CPU), and how fast is it?

Workflow (one run directory, e.g. evaluation/runs/reranker-parity-2026-10-23/):

  1. candidates   first-stage top-k_in candidates per benchmark question from the real retriever
                  (HybridDomainRetriever, BM25 + TF-IDF RRF, the benchmark configuration) -> candidates.json
  2. score        one runtime scores every (question, candidate) pair through the production
                  `src.retrieval.rerankers` classes -> scores_<label>.json   (repeat per runtime)
  3. tokcheck     (llama.cpp only) per-pair prompt-token count of the server vs the HF tokenizer
  4. report       parity vs the reference runtime, MRR/Recall vs gold ids, latency, RSS -> report.json, report.md

Queries are the benchmark *questions* (not the agent's own tool-call queries, which need the agent loop).
Candidate text is `title` + `content` exactly as the search tool passes it to the reranker (full article, no
snippet).  `max_length` is the same for every runtime (default 1024 tokens, longest_first).  Metrics against gold ids
are rank metrics on article ids only; they are not answer-correctness evidence.

Examples (repo root):
  python evaluation/probes/reranker_parity.py candidates --out RUN
  python evaluation/probes/reranker_parity.py score --out RUN --label torch_fp32_cpu --backend cross_encoder \\
      --model ~/models/reranker/AITeamVN_Vietnamese_Reranker --device cpu --dtype float32
  python evaluation/probes/reranker_parity.py score --out RUN --label gguf_q8_0 --backend llama_cpp \\
      --endpoint http://127.0.0.1:8082 --model Vietnamese_Reranker-Q8_0 --server-port 8082
  python evaluation/probes/reranker_parity.py report --out RUN --reference torch_fp32_cpu
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(os.environ.get("LUATCHECK_REPO_ROOT") or SCRIPT_DIR.parents[1]).resolve()
BENCHMARKS = {
    "hcmut_v1": ("evaluation/benchmarks/hcmut_v1/tasks.json", "data/corpus/hcmut_academic_v1.json"),
    "labour_vi_v1": ("evaluation/benchmarks/labour_vi_v1/tasks.json", "data/corpus/labour_vi_v1.json"),
}
RRF_K = 60            # config/benchmark/model_prism_gguf2b.yaml retrieval.rrf_k
MODEL_REVISION = "f536976248403314225d7fdfdbc87f0e9516a54e"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z (UTC%z)")


def percentile(values: List[float], q: float) -> float:
    """Linear-interpolation percentile (numpy default)."""
    xs = sorted(values)
    if not xs:
        return float("nan")
    pos = (len(xs) - 1) * q / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def rank_average(values: List[float]) -> List[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(a: List[float], b: List[float]) -> Optional[float]:
    ra, rb = rank_average(a), rank_average(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va, vb = sum((x - ma) ** 2 for x in ra), sum((y - mb) ** 2 for y in rb)
    if va == 0 or vb == 0:
        return None
    return cov / math.sqrt(va * vb)


def order_of(scores: List[float]) -> List[int]:
    """Same ordering rule as BaseReranker.rerank: best first, ties keep retrieval order."""
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))


# --------------------------------------------------------------------------- #
# 1. candidates
# --------------------------------------------------------------------------- #

def load_tasks(bench: str) -> List[Dict[str, Any]]:
    return json.loads((REPO_ROOT / BENCHMARKS[bench][0]).read_text(encoding="utf-8"))


def make_retriever(bench: str):
    sys.path.insert(0, str(REPO_ROOT))
    from src.retrieval.hybrid_domain import HybridDomainRetriever
    return HybridDomainRetriever(corpus_path=str(REPO_ROOT / BENCHMARKS[bench][1]), retrieval_mode="tfidf",
                                 rrf_k=RRF_K)


class CorpusLookup:
    """Doc-id -> record straight from the benchmark corpus JSON (no retriever dependencies; used by score/tokcheck)."""

    def __init__(self, bench: str):
        records = json.loads((REPO_ROOT / BENCHMARKS[bench][1]).read_text(encoding="utf-8"))
        self.by_id = {str(r.get("doc_id") or r.get("article_id") or r.get("id")): r for r in records}

    def get_document_by_id(self, doc_id: str) -> Dict[str, Any]:
        return self.by_id[doc_id]


def cmd_candidates(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / "candidates.json"
    if target.exists():
        print(f"{target} exists; refusing to overwrite", file=sys.stderr)
        return 1
    doc: Dict[str, Any] = {"created": now_stamp(), "top_k_in": args.top_k_in, "retrieval": "HybridDomainRetriever tfidf rrf_k=60",
                           "query_source": "benchmark task question", "benchmarks": {}}
    for bench, (tasks_rel, corpus_rel) in BENCHMARKS.items():
        retriever = make_retriever(bench)
        entries = []
        for task in load_tasks(bench):
            hits = retriever.search(task["question"], top_k=args.top_k_in)
            entries.append({
                "task_id": task["task_id"], "category": task["category"], "expected_behavior": task["expected_behavior"],
                "query": task["question"], "gold": task["ground_truth_article_ids"],
                "candidates": [{"doc_id": h["doc_id"], "rrf_score": h["rrf_score"],
                                "text_sha256": sha256_text((h["title"] or "") + "\n" + (h["content"] or ""))}
                               for h in hits],
            })
        doc["benchmarks"][bench] = {
            "tasks": tasks_rel, "tasks_sha256": sha256_file(REPO_ROOT / tasks_rel),
            "corpus": corpus_rel, "corpus_sha256": sha256_file(REPO_ROOT / corpus_rel), "entries": entries}
        print(f"{bench}: {len(entries)} tasks, candidates per task "
              f"{sorted({len(e['candidates']) for e in entries})}")
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {target}")
    return 0


def load_candidates(out: Path) -> Dict[str, Any]:
    return json.loads((out / "candidates.json").read_text(encoding="utf-8"))


def docs_for(bench: str, entry: Dict[str, Any], retriever, cand_doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Candidate dicts exactly as the retriever returns them (title/content), verified against the recorded hash."""
    docs = []
    for c in entry["candidates"]:
        d = retriever.get_document_by_id(c["doc_id"])
        doc = {"doc_id": c["doc_id"], "title": d.get("title") or d.get("section_title", ""), "content": d.get("content", "")}
        if sha256_text((doc["title"] or "") + "\n" + (doc["content"] or "")) != c["text_sha256"]:
            raise SystemExit(f"{bench}/{entry['task_id']}/{c['doc_id']}: corpus text differs from candidates.json")
        docs.append(doc)
    return docs


# --------------------------------------------------------------------------- #
# 2. score
# --------------------------------------------------------------------------- #

def rss_mb_of_pid(pid: int) -> Optional[float]:
    try:
        out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, check=True).stdout
        return int(out.strip()) / 1024.0
    except (subprocess.CalledProcessError, ValueError):
        return None


def pid_listening_on(port: int) -> Optional[int]:
    try:
        out = subprocess.run(["lsof", "-tiTCP:%d" % port, "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
        return int(out[0]) if out else None
    except (OSError, ValueError):
        return None


def own_rss_mb() -> float:
    try:
        out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True).stdout
        return int(out.strip()) / 1024.0
    except (OSError, ValueError):
        return float("nan")


def peak_rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1024.0 * 1024.0) if sys.platform == "darwin" else peak / 1024.0


def cmd_score(args) -> int:
    sys.path.insert(0, str(REPO_ROOT))
    from src.retrieval.rerankers import build_reranker
    out = Path(args.out)
    target = out / f"scores_{args.label}.json"
    if target.exists():
        print(f"{target} exists; refusing to overwrite (use another --label)", file=sys.stderr)
        return 1
    cands = load_candidates(out)
    cfg: Dict[str, Any] = {"backend": args.backend, "max_length": args.max_length,
                           "chunk_chars": args.chunk_chars or None}
    if args.backend == "cross_encoder":
        cfg.update({"model": args.model, "device": args.device, "dtype": args.dtype, "batch_size": args.batch_size,
                    "local_files_only": args.local_files_only})
    elif args.backend == "llama_cpp":
        cfg.update({"endpoint": args.endpoint, "model": args.model, "timeout_seconds": args.timeout})
    else:
        raise SystemExit("backend must be cross_encoder or llama_cpp")
    reranker = build_reranker(cfg)

    server_pid = pid_listening_on(args.server_port) if args.server_port else None
    if args.backend == "llama_cpp" and server_pid is None:
        raise SystemExit(f"nothing is listening on 127.0.0.1:{args.server_port}: start scripts/reranker/serve_mac.sh")
    env: Dict[str, Any] = {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine()}
    if args.backend == "cross_encoder":
        import torch
        import transformers
        env.update({"torch": torch.__version__, "transformers": transformers.__version__})
        if args.device.startswith("cuda") and torch.cuda.is_available():
            idx = torch.device(args.device).index or 0
            env["gpu"] = torch.cuda.get_device_name(idx)
            env["cuda_visible_devices"] = os.environ.get("CUDA_VISIBLE_DEVICES")
    else:
        try:
            ver = subprocess.run([args.llama_server, "--version"], capture_output=True, text=True)
            env["llama_server_version"] = (ver.stdout + ver.stderr).strip().splitlines()[0:2]
        except OSError:
            env["llama_server_version"] = "unknown"
        env["server_pid"] = server_pid
    started = time.perf_counter()
    reranker.load() if hasattr(reranker, "load") else None
    load_s = time.perf_counter() - started

    retrievers = {b: CorpusLookup(b) for b in cands["benchmarks"]}
    result: Dict[str, Any] = {
        "label": args.label, "created": now_stamp(), "config": cfg, "reranker_info": reranker.info(), "env": env,
        "model_revision": MODEL_REVISION, "load_seconds": load_s, "candidates_sha256": sha256_file(out / "candidates.json"),
        "max_length": args.max_length, "benchmarks": {}}
    if args.model_file:
        mf = Path(args.model_file).expanduser()
        result["model_file"] = {"path": str(mf), "bytes": mf.stat().st_size, "sha256": sha256_file(mf)}

    # warm-up (two queries, results discarded; first-call kernels / allocator / server prompt cache)
    first_bench = next(iter(cands["benchmarks"]))
    for entry in cands["benchmarks"][first_bench]["entries"][: args.warmup]:
        reranker.score(entry["query"], docs_for(first_bench, entry, retrievers[first_bench], cands))

    peak_server = rss_mb_of_pid(server_pid) if server_pid else None
    rss_after_warmup = own_rss_mb() if args.backend == "cross_encoder" else peak_server
    total_pairs = 0
    for bench, block in cands["benchmarks"].items():
        rows = []
        for entry in block["entries"]:
            docs = docs_for(bench, entry, retrievers[bench], cands)
            scores = reranker.score(entry["query"], docs)
            run = dict(reranker.last_run)
            row = {"task_id": entry["task_id"], "doc_ids": [d["doc_id"] for d in docs], "scores": scores,
                   "wall_ms": run["wall_ms"], "ms_per_pair": run["ms_per_pair"], "n_scored": run["n_scored"],
                   "n_truncated": run.get("n_truncated"), "n_chunks": run.get("n_chunks"),
                   "best_chunk": run.get("best_chunk")}
            if server_pid:
                rss = rss_mb_of_pid(server_pid)
                peak_server = max(peak_server or 0.0, rss or 0.0)
            rows.append(row)
            total_pairs += len(docs)
        result["benchmarks"][bench] = rows
        print(f"{args.label} {bench}: {len(rows)} queries scored")
    if args.backend == "cross_encoder":
        result["memory"] = {"process_peak_rss_mb": peak_rss_mb(), "process_rss_after_warmup_mb": rss_after_warmup,
                            "process_rss_end_mb": own_rss_mb(),
                            "note": "peak RSS of the whole python process including the model and the corpus/retrievers"}
    else:
        result["memory"] = {"server_rss_after_warmup_mb": rss_after_warmup, "server_peak_rss_sampled_mb": peak_server,
                            "server_rss_end_mb": rss_mb_of_pid(server_pid), "client_python_rss_mb": own_rss_mb(),
                            "note": "RSS of the llama-server process (weights are memory-mapped; GPU/Metal buffers are "
                                    "not counted by ps RSS)"}
    result["total_pairs"] = total_pairs
    target.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {target}")
    return 0


# --------------------------------------------------------------------------- #
# 3. tokcheck: server prompt tokens vs the HF tokenizer (llama.cpp prompt template check)
# --------------------------------------------------------------------------- #

def cmd_tokcheck(args) -> int:
    sys.path.insert(0, str(REPO_ROOT))
    import requests
    from transformers import AutoTokenizer
    from src.retrieval.rerankers import LlamaCppReranker
    out = Path(args.out)
    cands = load_candidates(out)
    tok = AutoTokenizer.from_pretrained(args.hf_model, local_files_only=True)
    reranker = LlamaCppReranker(args.endpoint, model=args.model, max_length=args.max_length)
    reranker._check_server()
    checked = mismatches = 0
    examples = []
    for bench, block in cands["benchmarks"].items():
        retriever = CorpusLookup(bench)
        for entry in block["entries"][: args.tasks]:
            docs = docs_for(bench, entry, retriever, cands)
            for doc in docs:
                from src.model_runtime import doc_text
                text = doc_text(doc)
                q2, t2 = reranker._fit(entry["query"], [text])
                resp = requests.post(f"{reranker.endpoint}/v1/rerank", json={"query": q2, "documents": t2}, timeout=60)
                resp.raise_for_status()
                server_tokens = resp.json()["usage"]["prompt_tokens"]
                hf_tokens = len(tok(entry["query"], text, truncation="longest_first", max_length=args.max_length)["input_ids"])
                checked += 1
                if server_tokens != hf_tokens:
                    mismatches += 1
                    if len(examples) < 10:
                        examples.append({"bench": bench, "task_id": entry["task_id"], "doc_id": doc["doc_id"],
                                         "server": server_tokens, "hf": hf_tokens})
    res = {"created": now_stamp(), "endpoint": args.endpoint, "max_length": args.max_length, "pairs_checked": checked,
           "token_count_mismatches": mismatches, "mismatch_examples": examples,
           "meaning": "server usage.prompt_tokens (one pair per request, after client-side longest_first fit) vs "
                      "len(HF tokenizer(query, text, truncation=longest_first, max_length))"}
    (out / f"tokcheck_{args.label}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0 if mismatches == 0 else 2


# --------------------------------------------------------------------------- #
# 4. report
# --------------------------------------------------------------------------- #

def gold_metrics(order_by_task: Dict[str, List[str]], gold_by_task: Dict[str, List[str]], ks=(1, 3, 5)) -> Dict[str, Any]:
    rr, recall, hit, absent, n = [], {k: [] for k in ks}, {k: [] for k in ks}, 0, 0
    for tid, ranked_ids in order_by_task.items():
        gold = gold_by_task[tid]
        if not gold:
            continue
        n += 1
        ranks = [ranked_ids.index(g) + 1 for g in gold if g in ranked_ids]
        absent += sum(1 for g in gold if g not in ranked_ids)
        rr.append(1.0 / min(ranks) if ranks else 0.0)
        for k in ks:
            top = set(ranked_ids[:k])
            recall[k].append(sum(1 for g in gold if g in top) / len(gold))
            hit[k].append(1.0 if any(g in top for g in gold) else 0.0)
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    return {"n_answerable": n, "MRR": mean(rr), **{f"Recall@{k}": mean(recall[k]) for k in ks},
            **{f"Hit@{k}": mean(hit[k]) for k in ks}, "gold_ids_absent_from_candidates": absent}


LONG_EVIDENCE_CHARS = 3000


def long_evidence_tasks() -> Dict[str, Dict[str, Any]]:
    """Tasks whose reference quote starts beyond the first LONG_EVIDENCE_CHARS characters of its record."""
    found: Dict[str, Dict[str, Any]] = {}
    for bench, (tasks_rel, corpus_rel) in BENCHMARKS.items():
        corpus = CorpusLookup(bench).by_id
        for task in load_tasks(bench):
            pos = []
            for ev in task.get("reference_evidence", []):
                rec = corpus.get(ev["article_id"])
                at = rec["content"].find(ev["exact_quote"]) if rec else -1
                if at >= LONG_EVIDENCE_CHARS:
                    pos.append((ev["article_id"], at, len(rec["content"])))
            if pos:
                found[f"{bench}/{task['task_id']}"] = {"evidence_beyond_chars": pos}
    return found


def policy_of(run: Dict[str, Any]) -> str:
    """Input policy of a scored run: `chunk` (windows, max over windows) or `nochunk` (prefix truncation only)."""
    return "chunk" if (run.get("config") or {}).get("chunk_chars") else "nochunk"


def cmd_report(args) -> int:
    out = Path(args.out)
    cands = load_candidates(out)
    runs: Dict[str, Dict[str, Any]] = {}
    for p in sorted(out.glob("scores_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d["candidates_sha256"] != sha256_file(out / "candidates.json"):
            raise SystemExit(f"{p.name}: scored a different candidates.json")
        runs[d["label"]] = d
    refs = {"nochunk": args.reference, "chunk": args.reference_chunk}
    for policy, name in refs.items():
        if name not in runs:
            raise SystemExit(f"{policy} reference {name!r} not found among {sorted(runs)}")
        if policy_of(runs[name]) != policy:
            raise SystemExit(f"reference {name!r} does not use the {policy} input policy")
    gold = {b: {e["task_id"]: e["gold"] for e in blk["entries"]} for b, blk in cands["benchmarks"].items()}
    behaviour = {b: {e["task_id"]: e["expected_behavior"] for e in blk["entries"]} for b, blk in cands["benchmarks"].items()}

    def by_task(run, bench):
        return {r["task_id"]: r for r in run["benchmarks"][bench]}

    report: Dict[str, Any] = {"created": now_stamp(), "reference": args.reference, "reference_chunk": args.reference_chunk, "candidates": "candidates.json",
                              "top_k_in": cands["top_k_in"], "runtimes": {}, "first_stage": {}}
    for bench, blk in cands["benchmarks"].items():
        first = {e["task_id"]: [c["doc_id"] for c in e["candidates"]] for e in blk["entries"]}
        report["first_stage"][bench] = gold_metrics(first, gold[bench])
    for label, run in runs.items():
        ref = runs[refs[policy_of(run)]]
        entry: Dict[str, Any] = {"policy": policy_of(run), "reference": ref["label"], "info": run["reranker_info"], "env": run["env"], "model_file": run.get("model_file"),
                                 "memory": run.get("memory"), "load_seconds": run["load_seconds"], "per_benchmark": {}}
        all_wall, all_pair, sp_all, t1_all, t3s_all, t3o_all, diffs, qmax = [], [], [], [], [], [], [], []
        for bench in cands["benchmarks"]:
            r_rows, x_rows = by_task(ref, bench), by_task(run, bench)
            sp, t1, t3s, t3o, bdiff, bmax = [], [], [], [], [], []
            order_ids = {}
            for tid, xr in x_rows.items():
                rr = r_rows[tid]
                if rr["doc_ids"] != xr["doc_ids"]:
                    raise SystemExit(f"{label}/{bench}/{tid}: candidate order differs from reference")
                s = spearman(rr["scores"], xr["scores"])
                if s is not None:
                    sp.append(s)
                ro, xo = order_of(rr["scores"]), order_of(xr["scores"])
                t1.append(1.0 if ro[0] == xo[0] else 0.0)
                t3s.append(1.0 if set(ro[:3]) == set(xo[:3]) else 0.0)
                t3o.append(1.0 if ro[:3] == xo[:3] else 0.0)
                d = [abs(a - b) for a, b in zip(rr["scores"], xr["scores"])]
                bdiff.extend(d)
                bmax.append(max(d))
                order_ids[tid] = [xr["doc_ids"][i] for i in xo]
            gm_all = gold_metrics(order_ids, gold[bench])
            mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
            walls = [r["wall_ms"] for r in x_rows.values()]
            pairs = [r["ms_per_pair"] for r in x_rows.values()]
            entry["per_benchmark"][bench] = {
                "n_queries": len(x_rows), "spearman_mean": mean(sp), "spearman_min": min(sp) if sp else None,
                "spearman_n_undefined": len(x_rows) - len(sp),
                "top1_agreement": mean(t1), "top3_set_agreement": mean(t3s), "top3_ordered_agreement": mean(t3o),
                "max_abs_score_diff": max(bdiff), "mean_abs_score_diff": mean(bdiff),
                "gold": gm_all,
                "latency_ms_per_query": {"p50": percentile(walls, 50), "p95": percentile(walls, 95),
                                         "mean": mean(walls), "max": max(walls), "n": len(walls)},
                "ms_per_pair": {"p50": percentile(pairs, 50), "p95": percentile(pairs, 95)},
                "n_truncated_pairs": sum((r["n_truncated"] or 0) for r in x_rows.values()),
                "n_chunks": sum((r.get("n_chunks") or 0) for r in x_rows.values()),
                "n_pairs": sum(r["n_scored"] for r in x_rows.values())}
            all_wall += walls; all_pair += pairs; sp_all += sp; t1_all += t1; t3s_all += t3s; t3o_all += t3o
            diffs += bdiff; qmax += bmax
        mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
        merged_order, merged_gold = {}, {}
        for bench in cands["benchmarks"]:
            x_rows = by_task(run, bench)
            for tid, xr in x_rows.items():
                merged_order[f"{bench}/{tid}"] = [xr["doc_ids"][i] for i in order_of(xr["scores"])]
                merged_gold[f"{bench}/{tid}"] = gold[bench][tid]
        entry["overall"] = {
            "n_queries": len(t1_all), "spearman_mean": mean(sp_all), "spearman_min": min(sp_all),
            "top1_agreement": mean(t1_all), "top3_set_agreement": mean(t3s_all), "top3_ordered_agreement": mean(t3o_all),
            "max_abs_score_diff": max(diffs), "mean_abs_score_diff": mean(diffs), "gold": gold_metrics(merged_order, merged_gold),
            "latency_ms_per_query": {"p50": percentile(all_wall, 50), "p95": percentile(all_wall, 95), "mean": mean(all_wall)},
            "ms_per_pair": {"p50": percentile(all_pair, 50), "p95": percentile(all_pair, 95)}}
        report["runtimes"][label] = entry
    report["cross_runtime"] = {}
    for spec in args.compare:
        a_label, b_label = spec.split(":")
        a, b = runs[a_label], runs[b_label]
        sp, t1, t3s, t3o, dif, per_query_max = [], [], [], [], [], []
        for bench in cands["benchmarks"]:
            a_rows, b_rows = by_task(a, bench), by_task(b, bench)
            for tid, ar in a_rows.items():
                br = b_rows[tid]
                if ar["doc_ids"] != br["doc_ids"]:
                    raise SystemExit(f"{spec}/{bench}/{tid}: candidate order differs")
                s_ = spearman(ar["scores"], br["scores"])
                if s_ is not None:
                    sp.append(s_)
                ao, bo = order_of(ar["scores"]), order_of(br["scores"])
                t1.append(1.0 if ao[0] == bo[0] else 0.0)
                t3s.append(1.0 if set(ao[:3]) == set(bo[:3]) else 0.0)
                t3o.append(1.0 if ao[:3] == bo[:3] else 0.0)
                d = [abs(x - y) for x, y in zip(ar["scores"], br["scores"])]
                dif.extend(d)
                per_query_max.append(max(d))
        mean_ = lambda xs: sum(xs) / len(xs)
        report["cross_runtime"][spec] = {
            "n_queries": len(t1), "spearman_mean": mean_(sp), "spearman_min": min(sp), "top1_agreement": mean_(t1),
            "top3_set_agreement": mean_(t3s), "top3_ordered_agreement": mean_(t3o),
            "max_abs_score_diff": max(dif), "mean_abs_score_diff": mean_(dif),
            "policies": [policy_of(a), policy_of(b)]}
    long_tasks = long_evidence_tasks()
    report["long_evidence_tasks"] = {}
    for key, info in long_tasks.items():
        bench, tid = key.split("/")
        row = {"evidence": info["evidence_beyond_chars"], "gold": gold[bench][tid], "gold_rank_by_runtime": {}}
        first_ids = next(e for e in cands["benchmarks"][bench]["entries"] if e["task_id"] == tid)["candidates"]
        first_ids = [c["doc_id"] for c in first_ids]
        row["gold_rank_by_runtime"]["first_stage"] = {g: (first_ids.index(g) + 1 if g in first_ids else None) for g in gold[bench][tid]}
        for label, run in runs.items():
            xr = by_task(run, bench)[tid]
            ids = [xr["doc_ids"][i] for i in order_of(xr["scores"])]
            row["gold_rank_by_runtime"][label] = {g: (ids.index(g) + 1 if g in ids else None) for g in gold[bench][tid]}
        report["long_evidence_tasks"][key] = row
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print((out / "report.md").read_text(encoding="utf-8"))
    return 0


def render_markdown(rep: Dict[str, Any]) -> str:
    f = lambda x, n=4: "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"
    L = [f"# Reranker runtime parity report", "", f"Generated {rep['created']}; reference runtimes: `{rep['reference']}` (no chunking) and "
         f"`{rep['reference_chunk']}` (chunking); each run is compared with the reference of its own input policy; "
         f"top_k_in = {rep['top_k_in']} candidates per question.", ""]
    L += ["## Parity vs reference (per-query statistics over both benchmarks)", "",
          "| runtime | policy | queries | Spearman mean | Spearman min | top-1 agree | top-3 set agree | top-3 ordered agree | max abs diff | mean abs diff |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for label, e in rep["runtimes"].items():
        o = e["overall"]
        L.append(f"| {label} | {e['policy']} | {o['n_queries']} | {f(o['spearman_mean'], 5)} | {f(o['spearman_min'], 5)} | {f(o['top1_agreement'], 3)} | "
                 f"{f(o['top3_set_agreement'], 3)} | {f(o['top3_ordered_agreement'], 3)} | {f(o['max_abs_score_diff'], 4)} | {f(o['mean_abs_score_diff'], 5)} |")
    L += ["", "## Rank metrics vs gold article ids (answerable questions only; not answer correctness)", "",
          "| benchmark | system | n | MRR | Recall@1 | Recall@3 | Recall@5 | Hit@1 | Hit@3 | gold absent from candidates |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    benches = list(rep["first_stage"])
    for b in benches:
        g = rep["first_stage"][b]
        L.append(f"| {b} | first stage (retrieval order) | {g['n_answerable']} | {f(g['MRR'], 3)} | {f(g['Recall@1'], 3)} | {f(g['Recall@3'], 3)} | {f(g['Recall@5'], 3)} | {f(g['Hit@1'], 3)} | {f(g['Hit@3'], 3)} | {g['gold_ids_absent_from_candidates']} |")
        for label, e in rep["runtimes"].items():
            g = e["per_benchmark"][b]["gold"]
            L.append(f"| {b} | {label} | {g['n_answerable']} | {f(g['MRR'], 3)} | {f(g['Recall@1'], 3)} | {f(g['Recall@3'], 3)} | {f(g['Recall@5'], 3)} | {f(g['Hit@1'], 3)} | {f(g['Hit@3'], 3)} | {g['gold_ids_absent_from_candidates']} |")
    if rep.get("cross_runtime"):
        L += ["", "## Runtime vs runtime (no reference involved)", "",
              "| A : B | policies | queries | Spearman mean | Spearman min | top-1 agree | top-3 set agree | top-3 ordered agree | max abs diff | mean abs diff |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for spec, o in rep["cross_runtime"].items():
            L.append(f"| {spec} | {'/'.join(o['policies'])} | {o['n_queries']} | {f(o['spearman_mean'], 5)} | {f(o['spearman_min'], 5)} | "
                     f"{f(o['top1_agreement'], 3)} | {f(o['top3_set_agreement'], 3)} | {f(o['top3_ordered_agreement'], 3)} | "
                     f"{f(o['max_abs_score_diff'], 4)} | {f(o['mean_abs_score_diff'], 5)} |")
    if rep.get("long_evidence_tasks"):
        labels = list(next(iter(rep["long_evidence_tasks"].values()))["gold_rank_by_runtime"])
        L += ["", f"## Tasks whose gold evidence starts beyond the first {LONG_EVIDENCE_CHARS} characters of its record",
              "", "Gold article rank among the candidates (1 = best; `-` = not in the candidate set). Multi-gold tasks list ranks in gold order.", "",
              "| task | evidence (record, char offset, record length) | " + " | ".join(labels) + " |",
              "|---|---|" + "---|" * len(labels)]
        for key, row in rep["long_evidence_tasks"].items():
            ev = "; ".join(f"{a} @{p}/{n}" for a, p, n in row["evidence"])
            cells = [", ".join(str(r) if r else "-" for r in row["gold_rank_by_runtime"][lb].values()) for lb in labels]
            L.append(f"| {key} | {ev} | " + " | ".join(cells) + " |")
    L += ["", "## Latency per query (one batch of all candidates) and memory", "",
          "| runtime | device | p50 ms/query | p95 ms/query | p50 ms/doc | p95 ms/doc | scored chunks (docs) | truncated | RSS MB (see note) |", "|---|---|---|---|---|---|---|---|---|"]
    for label, e in rep["runtimes"].items():
        lat = e["overall"]["latency_ms_per_query"]; mp = e["overall"]["ms_per_pair"]
        trunc = sum(pb["n_truncated_pairs"] for pb in e["per_benchmark"].values())
        total = sum(pb["n_pairs"] for pb in e["per_benchmark"].values())
        mem = e.get("memory") or {}
        rss = mem.get("server_peak_rss_sampled_mb") or mem.get("process_peak_rss_mb")
        chunks = sum(pb.get("n_chunks") or pb["n_pairs"] for pb in e["per_benchmark"].values())
        L.append(f"| {label} | {e['info'].get('device')} | {f(lat['p50'], 0)} | {f(lat['p95'], 0)} | {f(mp['p50'], 1)} | {f(mp['p95'], 1)} | {chunks} ({total}) | {trunc} | {f(rss, 0)} |")
    L += ["", "RSS: llama-server runtimes = sampled peak RSS of the server process (mapped weights count once touched; Metal buffers are not in ps RSS); "
          "torch runtimes = peak RSS of the whole Python process (model + corpus + retrievers).", ""]
    return "\n".join(L)


# --------------------------------------------------------------------------- #

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates"); c.add_argument("--out", required=True); c.add_argument("--top-k-in", type=int, default=20)
    s = sub.add_parser("score")
    s.add_argument("--out", required=True); s.add_argument("--label", required=True)
    s.add_argument("--backend", required=True, choices=["cross_encoder", "llama_cpp"])
    s.add_argument("--model", required=True, help="cross_encoder: HF id / local dir; llama_cpp: served alias")
    s.add_argument("--device", default="cpu"); s.add_argument("--dtype", default="float32")
    s.add_argument("--batch-size", type=int, default=1); s.add_argument("--max-length", type=int, default=1024)
    s.add_argument("--chunk-chars", type=int, default=1500,
                   help="long candidates are split into windows of this many characters, document score = max over "
                        "windows; 0 = off (prefix truncation to --max-length tokens only)")
    s.add_argument("--local-files-only", action="store_true")
    s.add_argument("--endpoint", default="http://127.0.0.1:8082"); s.add_argument("--timeout", type=float, default=120.0)
    s.add_argument("--server-port", type=int, default=None, help="llama.cpp: port of the server whose RSS is sampled")
    s.add_argument("--llama-server", default="llama-server"); s.add_argument("--model-file", default=None,
                   help="GGUF path, recorded with its sha256")
    s.add_argument("--warmup", type=int, default=2)
    t = sub.add_parser("tokcheck")
    t.add_argument("--out", required=True); t.add_argument("--label", required=True)
    t.add_argument("--hf-model", required=True); t.add_argument("--endpoint", default="http://127.0.0.1:8082")
    t.add_argument("--model", default=None); t.add_argument("--max-length", type=int, default=1024)
    t.add_argument("--tasks", type=int, default=10, help="tasks per benchmark")
    r = sub.add_parser("report"); r.add_argument("--out", required=True); r.add_argument("--reference", default="torch_fp32_cpu",
                   help="reference run for runs WITHOUT chunking (prefix truncation only)")
    r.add_argument("--compare", action="append", default=[], metavar="A:B",
                   help="also report parity of run A against run B (e.g. gguf_f16_chunk:h100_fp16_bs1_chunk)")
    r.add_argument("--reference-chunk", default="torch_fp32_cpu_chunk", help="reference run for runs WITH chunking")
    args = ap.parse_args(argv)
    return {"candidates": cmd_candidates, "score": cmd_score, "tokcheck": cmd_tokcheck, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
