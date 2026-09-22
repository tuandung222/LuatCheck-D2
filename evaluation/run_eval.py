"""
Benchmark Evaluation Runner for LuatCheck D2 & D3.
Executes automated evaluations across multiple seeds [42, 123, 2026], evaluating a 3-Way Ablation Study:
1. baseline_off: Verification OFF (Standard RAG baseline)
2. luatcheck_l1_on: Verification ON (L1 Deterministic Verifier)
3. luatcheck_l1_l2_on: Verification ON + L2 Semantic Entailment Verifier
Integrates ErrorDiagnosticAnalyzer to classify errors across 6 standardized failure modes.
"""
import argparse
import json
import time
import os
import sys
import re
import random
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.loop import LuatCheckAgent
from src.agent.state import Citation
from evaluation.metrics import (
    calculate_retrieval_metrics,
    calculate_citation_metrics,
    calculate_latency_percentiles,
    calculate_unsupported_rate,
    normalize_id
)
from evaluation.error_analyzer import ErrorDiagnosticAnalyzer, generate_comparative_markdown_table


def run_benchmark(
    tasks_file: str,
    seeds: List[int],
    mode: str = "l1_on",
    l2_use_slm: bool = False,
    offline: bool = True
) -> Dict[str, Any]:
    with open(tasks_file, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    print(f"\n==================================================", flush=True)
    print(f"BẮT ĐẦU CHẠY BENCHMARK: {mode.upper()}", flush=True)
    print(f"Số lượng tasks: {len(tasks)} | Seeds: {seeds} | Offline: {offline} | L2 SLM: {l2_use_slm}", flush=True)
    print(f"==================================================", flush=True)

    enable_verif = (mode != "off")
    ollama_url = "http://127.0.0.1:1" if offline else "http://localhost:11434"
    agent = LuatCheckAgent(
        verification_mode=mode,
        enable_verification=enable_verif,
        l2_use_slm=l2_use_slm,
        ollama_url=ollama_url
    )
    # Isolate memory in benchmark: disable cache reads and write-backs to SQLite to ensure fair cold-start measurement
    agent.sqlite_store.retrieve_similar_case = lambda *args, **kwargs: None
    agent.sqlite_store.write_if_verified = lambda *args, **kwargs: False

    error_analyzer = ErrorDiagnosticAnalyzer(name=mode)
    all_seed_results = []
    latencies = []
    total_token_counts = []

    for seed in seeds:
        random.seed(seed)
        np.random.seed(seed)
        print(f"\n--- Đang chạy Seed: {seed} ---", flush=True)

        seed_recalls_1 = []
        seed_recalls_5 = []
        seed_mrrs = []
        seed_citation_precisions = []
        seed_citation_recalls = []
        seed_coverage = []
        seed_unsupported_rates = []

        for idx, task in enumerate(tasks):
            t_start = time.time()
            query = task["question"]
            gt_ids = task.get("ground_truth_article_ids", [])
            if not gt_ids and task.get("ground_truth_article_id"):
                gt_ids = [task.get("ground_truth_article_id")]
            expected_behavior = task.get("expected_behavior", "answer")

            ledger = agent.run(query, session_id=f"eval_{mode}_s{seed}_t{idx}")
            t_elapsed = (time.time() - t_start) * 1000
            latencies.append(t_elapsed)

            final_out = ledger.final_output or {}
            citations = final_out.get("citations", [])
            cit_ids = []
            if citations:
                for c in citations:
                    aid = c.get("article_id", "") if isinstance(c, dict) else getattr(c, "article_id", str(c))
                    if aid:
                        cit_ids.append(normalize_id(aid))

            # 1. Evaluate Retrieval (objectively assessed across all ledger.retrieved_article_ids)
            if gt_ids:
                ret_evaluated = ledger.retrieved_article_ids
                ret_metrics = calculate_retrieval_metrics(ret_evaluated, gt_ids)
                seed_recalls_1.append(ret_metrics["Recall@1"])
                seed_recalls_5.append(ret_metrics["Recall@5"])
                seed_mrrs.append(ret_metrics["MRR"])

            is_answered = (ledger.terminal_status == "answered")
            seed_coverage.append(1.0 if is_answered else 0.0)

            # 2. Evaluate Citation
            if gt_ids:
                cit_metrics = calculate_citation_metrics(cit_ids, gt_ids)
                seed_citation_precisions.append(cit_metrics["citation_precision"])
                seed_citation_recalls.append(cit_metrics["citation_recall"])
            else:
                cit_metrics = calculate_citation_metrics(cit_ids, [])
                seed_citation_precisions.append(cit_metrics["citation_precision"])
                seed_citation_recalls.append(cit_metrics["citation_recall"])

            # 3. Compute dynamic Unsupported Sentence Rate (USR) symmetrically adhering to ALCE standard
            unsupported_claims_list = []
            if not is_answered:
                usr = 0.0
            elif expected_behavior == "refuse":
                # Symmetrical across modes: Answering unanswerable queries yields USR = 1.0 penalty (zero statutory grounding)
                usr = 1.0
                unsupported_claims_list = [str(final_out.get("content", ""))]
            else:
                answer_text = final_out.get("content", "")
                if mode in ["l1_l2", "l1_l2_on"]:
                    usr = calculate_unsupported_rate(
                        answer_text=answer_text,
                        cited_articles=citations,
                        verifier=agent.verifier,
                        retrieved_article_ids=ledger.retrieved_article_ids
                    )
                    l2_res = agent.l2_verifier.verify_all_claims(answer_text, cit_ids)
                    unsupported_claims_list = [f["sentence"] for f in l2_res.get("failed_claims", [])]
                    if not l2_res.get("is_entailed", False) and usr == 0.0 and len(unsupported_claims_list) > 0:
                        total_sents = max(l2_res.get("total_sentences", 1), 1)
                        usr = round(float(len(unsupported_claims_list) / total_sents), 4)
                else:
                    usr = calculate_unsupported_rate(
                        answer_text=answer_text,
                        cited_articles=citations,
                        verifier=agent.verifier,
                        retrieved_article_ids=ledger.retrieved_article_ids
                    )
                    cit_objs = [
                        Citation(article_id=c.get("article_id", ""), span=c.get("span", ""))
                        if isinstance(c, dict) else c
                        for c in citations
                    ]
                    l1_res = agent.verifier.verify(
                        answer_text=answer_text,
                        citations=cit_objs,
                        retrieved_article_ids=ledger.retrieved_article_ids
                    )
                    if hasattr(l1_res, "unsupported_claims"):
                        unsupported_claims_list = list(l1_res.unsupported_claims)

            seed_unsupported_rates.append(usr)

            # Estimate tokens per task
            prompt_tokens = int(len(query.split()) * 1.3) + 120
            out_tokens = int(len(str(final_out.get("content", "")).split()) * 1.3) if is_answered else 35
            total_token_counts.append(prompt_tokens + out_tokens)

            # 4. Record into ErrorDiagnosticAnalyzer
            parse_error_detected = any(ev.get("event") == "parse_error" for ev in getattr(ledger, "audit_events", []))
            parse_error_details = None
            if parse_error_detected:
                for ev in getattr(ledger, "audit_events", []):
                    if ev.get("event") == "parse_error":
                        parse_error_details = ev.get("details")
                        break

            error_analyzer.record_task_evaluation(
                task=task,
                ledger=ledger,
                citations=citations,
                unsupported_sentence_rate=usr,
                unsupported_claims=unsupported_claims_list,
                parse_error_detected=parse_error_detected,
                parse_error_details=parse_error_details
            )

            status_icon = "✅" if (is_answered and expected_behavior == "answer") or (not is_answered and expected_behavior == "refuse") else "⚠️"
            print(f" Task {idx+1:02d} [{task.get('task_id', '')[:28]:<28}]: {status_icon} | Ret:{ledger.retrieved_article_ids[:2]} | GT:{gt_ids[:2]} | USR:{usr:.3f} | Latency:{t_elapsed:.1f}ms", flush=True)

        all_seed_results.append({
            "seed": seed,
            "Recall@1": np.mean(seed_recalls_1) if seed_recalls_1 else 0.0,
            "Recall@5": np.mean(seed_recalls_5) if seed_recalls_5 else 0.0,
            "MRR": np.mean(seed_mrrs) if seed_mrrs else 0.0,
            "Citation_Precision": np.mean(seed_citation_precisions),
            "Citation_Recall": np.mean(seed_citation_recalls),
            "Coverage": np.mean(seed_coverage),
            "Unsupported_Rate": np.mean(seed_unsupported_rates)
        })

    error_stats = error_analyzer.get_statistics()

    aggregated = {
        "mode": mode,
        "seeds": seeds,
        "Recall@1_mean": round(float(np.mean([r["Recall@1"] for r in all_seed_results])), 4),
        "Recall@1_std": round(float(np.std([r["Recall@1"] for r in all_seed_results])), 4),
        "Recall@5_mean": round(float(np.mean([r["Recall@5"] for r in all_seed_results])), 4),
        "Recall@5_std": round(float(np.std([r["Recall@5"] for r in all_seed_results])), 4),
        "MRR_mean": round(float(np.mean([r["MRR"] for r in all_seed_results])), 4),
        "MRR_std": round(float(np.std([r["MRR"] for r in all_seed_results])), 4),
        "Citation_Precision_mean": round(float(np.mean([r["Citation_Precision"] for r in all_seed_results])), 4),
        "Citation_Precision_std": round(float(np.std([r["Citation_Precision"] for r in all_seed_results])), 4),
        "Citation_Recall_mean": round(float(np.mean([r["Citation_Recall"] for r in all_seed_results])), 4),
        "Citation_Recall_std": round(float(np.std([r["Citation_Recall"] for r in all_seed_results])), 4),
        "Coverage_mean": round(float(np.mean([r["Coverage"] for r in all_seed_results])), 4),
        "Coverage_std": round(float(np.std([r["Coverage"] for r in all_seed_results])), 4),
        "Unsupported_Rate_mean": round(float(np.mean([r["Unsupported_Rate"] for r in all_seed_results])), 4),
        "Unsupported_Rate_std": round(float(np.std([r["Unsupported_Rate"] for r in all_seed_results])), 4),
        "Error_Taxonomy": error_stats["counts"],
        "Error_Taxonomy_Detailed": error_stats,
        "Markdown_Taxonomy": error_analyzer.to_markdown_table(),
        "Latency": calculate_latency_percentiles(latencies),
        "Tokens_Per_Task_mean": round(float(np.mean(total_token_counts)), 1) if total_token_counts else 0.0,
        "Total_Tokens": sum(total_token_counts),
        "Compute_Cost_USD": 0.0,
        "_analyzer": error_analyzer
    }
    return aggregated


def main():
    parser = argparse.ArgumentParser(description="Run LuatCheck Evaluation Benchmark")
    parser.add_argument("--tasks", default="evaluation/tasks/vlqa_full_20.json", help="Path to tasks file")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 2026], help="Random seeds")
    parser.add_argument("--ablation", choices=["on", "off", "both", "three_way"], default="three_way", help="Verification mode")
    parser.add_argument("--l2_use_slm", action="store_true", default=False, help="Use SLM NLI for L2 semantic verifier (default: False)")
    parser.add_argument("--offline", action="store_true", default=True, help="Force deterministic offline execution (default: True)")
    parser.add_argument("--online", dest="offline", action="store_false", help="Enable online Ollama inference calls")
    parser.add_argument("--output", default=None, help="Custom output JSON path")
    args = parser.parse_args()

    results = {}
    analyzers = {}

    if args.ablation in ["off", "both", "three_way"]:
        res_off = run_benchmark(args.tasks, args.seeds, mode="off", l2_use_slm=args.l2_use_slm, offline=args.offline)
        an_off = res_off.pop("_analyzer")
        results["baseline_off"] = res_off
        analyzers["Baseline (OFF)"] = an_off

    if args.ablation in ["on", "both", "three_way"]:
        res_l1 = run_benchmark(args.tasks, args.seeds, mode="l1_on", l2_use_slm=args.l2_use_slm, offline=args.offline)
        an_l1 = res_l1.pop("_analyzer")
        results["luatcheck_l1_on"] = res_l1
        analyzers["LuatCheck (L1 ON)"] = an_l1

    if args.ablation == "three_way":
        res_l2 = run_benchmark(args.tasks, args.seeds, mode="l1_l2_on", l2_use_slm=args.l2_use_slm, offline=args.offline)
        an_l2 = res_l2.pop("_analyzer")
        results["luatcheck_l1_l2_on"] = res_l2
        analyzers["LuatCheck (L1+L2)"] = an_l2

    # Save quantitative evaluation results
    os.makedirs("evaluation", exist_ok=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        saved_paths = [args.output]
    elif args.ablation == "three_way":
        with open("evaluation/eval_results_d3.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        with open("evaluation/eval_results_3way.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        saved_paths = ["evaluation/eval_results_d3.json", "evaluation/eval_results_3way.json"]
    else:
        with open("evaluation/eval_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        saved_paths = ["evaluation/eval_results.json"]

    print("\n" + "=" * 90, flush=True)
    print(" BẢNG TỔNG HỢP KẾT QUẢ ĐÁNH GIÁ ĐỊNH LƯỢNG D3 (THREE-WAY ABLATION STUDY)", flush=True)
    print("=" * 90, flush=True)
    header = f"{'Metric':<26} | {'Baseline (OFF)':<18} | {'LuatCheck (L1 ON)':<18} | {'LuatCheck (L1+L2)':<18}"
    print(header, flush=True)
    print("-" * 90, flush=True)

    b = results.get("baseline_off", {})
    l1 = results.get("luatcheck_l1_on", {})
    l2 = results.get("luatcheck_l1_l2_on", {})

    metrics_map = [
        ("Recall@1", "Recall@1_mean", "Recall@1_std"),
        ("Recall@5", "Recall@5_mean", "Recall@5_std"),
        ("MRR", "MRR_mean", "MRR_std"),
        ("Citation Precision", "Citation_Precision_mean", "Citation_Precision_std"),
        ("Citation Recall", "Citation_Recall_mean", "Citation_Recall_std"),
        ("Answer Coverage", "Coverage_mean", "Coverage_std"),
        ("Unsupported Rate (↓)", "Unsupported_Rate_mean", "Unsupported_Rate_std"),
        ("Tokens / Task (mean)", "Tokens_Per_Task_mean", None),
    ]

    for label, m_key, s_key in metrics_map:
        if s_key:
            b_val = f"{b.get(m_key, 0):.3f} ± {b.get(s_key, 0):.3f}"
            l1_val = f"{l1.get(m_key, 0):.3f} ± {l1.get(s_key, 0):.3f}"
            l2_val = f"{l2.get(m_key, 0):.3f} ± {l2.get(s_key, 0):.3f}"
        else:
            b_val = f"{b.get(m_key, 0)}"
            l1_val = f"{l1.get(m_key, 0)}"
            l2_val = f"{l2.get(m_key, 0)}"
        print(f"{label:<26} | {b_val:<18} | {l1_val:<18} | {l2_val:<18}", flush=True)

    print("-" * 90, flush=True)
    b_lat = f"{b.get('Latency', {}).get('p50_ms', 0):.1f}ms / {b.get('Latency', {}).get('p95_ms', 0):.1f}ms"
    l1_lat = f"{l1.get('Latency', {}).get('p50_ms', 0):.1f}ms / {l1.get('Latency', {}).get('p95_ms', 0):.1f}ms"
    l2_lat = f"{l2.get('Latency', {}).get('p50_ms', 0):.1f}ms / {l2.get('Latency', {}).get('p95_ms', 0):.1f}ms"
    print(f"{'Latency (p50 / p95)':<26} | {b_lat:<18} | {l1_lat:<18} | {l2_lat:<18}", flush=True)
    print(f"{'Compute Cost (USD)':<26} | {'$0.00 (Local)':<18} | {'$0.00 (Local)':<18} | {'$0.00 (Local)':<18}", flush=True)
    print("=" * 90, flush=True)

    print("\n" + generate_comparative_markdown_table(analyzers), flush=True)
    print("\nĐã lưu kết quả thành công vào:", flush=True)
    for p in saved_paths:
        print(f" - {p}", flush=True)


if __name__ == "__main__":
    main()
