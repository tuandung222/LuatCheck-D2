"""
Benchmark Evaluation Runner for LuatCheck D2 & D3
Chạy đánh giá tự động đa seeds, so sánh Ablation (Verification ON vs OFF)
Tính toán Unsupported Sentence Rate (USR) động thực sự qua L1EvidenceVerifier
"""
import argparse
import json
import time
import os
import sys
import re
import numpy as np
from typing import Dict, Any, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.loop import LuatCheckAgent
from src.agent.state import Citation
from evaluation.metrics import (
    calculate_retrieval_metrics,
    calculate_citation_metrics,
    calculate_latency_percentiles,
    normalize_id
)


def run_benchmark(tasks_file: str, seeds: List[int], mode: str = "l1_on") -> Dict[str, Any]:
    with open(tasks_file, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    print(f"\n==================================================")
    print(f"BẮT ĐẦU CHẠY BENCHMARK: {mode.upper()}")
    print(f"Số lượng tasks: {len(tasks)} | Seeds: {seeds}")
    print(f"==================================================")

    enable_verif = (mode != "off")
    agent = LuatCheckAgent(verification_mode=mode, enable_verification=enable_verif)

    all_seed_results = []
    latencies = []
    error_counts = {
        "retrieval_miss": 0,
        "wrong_provision": 0,
        "unsupported_claim": 0,
        "over_refusal": 0,
        "budget_exhausted": 0,
        "parse_error": 0
    }

    for seed in seeds:
        print(f"\n--- Đang chạy Seed: {seed} ---")
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
            gt_ids = task.get("ground_truth_article_ids", [task.get("ground_truth_article_id")])
            primary_gt = gt_ids[0] if gt_ids else "NONE"
            expected_behavior = task.get("expected_behavior", "answer")

            ledger = agent.run(query, session_id=f"eval_{mode}_s{seed}_t{idx}")
            t_elapsed = (time.time() - t_start) * 1000
            latencies.append(t_elapsed)

            # Đánh giá Retrieval
            if primary_gt != "NONE":
                ret_metrics = calculate_retrieval_metrics(ledger.retrieved_article_ids, primary_gt)
                seed_recalls_1.append(ret_metrics["Recall@1"])
                seed_recalls_5.append(ret_metrics["Recall@5"])
                seed_mrrs.append(ret_metrics["MRR"])
                if ret_metrics["Recall@5"] == 0.0:
                    error_counts["retrieval_miss"] += 1

            is_answered = (ledger.terminal_status == "answered")
            seed_coverage.append(1.0 if is_answered else 0.0)

            final_out = ledger.final_output or {}
            citations = final_out.get("citations", [])
            cit_ids = [c.get("article_id", "") for c in citations] if isinstance(citations, list) else []

            if primary_gt != "NONE":
                cit_metrics = calculate_citation_metrics(cit_ids, primary_gt)
                seed_citation_precisions.append(cit_metrics["citation_precision"])
                seed_citation_recalls.append(cit_metrics["citation_recall"])
                if cit_metrics["citation_precision"] < 1.0 and is_answered:
                    error_counts["wrong_provision"] += 1
            else:
                seed_citation_precisions.append(1.0)
                seed_citation_recalls.append(1.0)

            # Error diagnosis for refusal vs answer
            if expected_behavior == "refuse" and is_answered:
                error_counts["unsupported_claim"] += 1
            elif expected_behavior == "answer" and not is_answered:
                error_counts["over_refusal"] += 1

            # Tính toán Unsupported Sentence Rate (USR) động thực tế theo ALCE (Gao et al., 2023)
            if not is_answered:
                # Phản hồi từ chối hoặc làm rõ không chứa khẳng định pháp lý sai lệch
                usr = 0.0
            else:
                answer_text = final_out.get("content", "")
                sentences = [s.strip() for s in re.split(r'[.?!]\s+', answer_text) if len(s.strip()) > 15]
                total_sentences = len(sentences)

                if total_sentences == 0:
                    usr = 0.0
                elif not cit_ids or not citations:
                    # Đưa ra câu trả lời khẳng định nhưng không có trích dẫn điều luật nào -> 100% unsupported
                    usr = 1.0
                else:
                    citation_objs = []
                    for c in citations:
                        if isinstance(c, dict):
                            citation_objs.append(Citation(article_id=c.get("article_id", ""), span=c.get("span", "")))
                        elif hasattr(c, "article_id"):
                            citation_objs.append(c)

                    # Sử dụng L1EvidenceVerifier của agent để kiểm tra tính hợp lệ và span overlap
                    l1_res = agent.verifier.verify(
                        answer_text=answer_text,
                        citations=citation_objs,
                        retrieved_article_ids=ledger.retrieved_article_ids
                    )

                    if l1_res.invalid_citations:
                        # Điều luật trích dẫn không tồn tại hoặc hallucinated -> unsupported
                        usr = 1.0
                    else:
                        unsupported_count = len(l1_res.unsupported_claims)
                        usr = round(float(unsupported_count / total_sentences), 4)

            seed_unsupported_rates.append(usr)

            status_icon = "✅" if (is_answered and expected_behavior == "answer") or (not is_answered and expected_behavior == "refuse") else "⚠️"
            print(f" Task {idx+1:02d}: {status_icon} | Ret:{ledger.retrieved_article_ids[:2]} | GT:{primary_gt} | USR:{usr:.3f} | Latency: {t_elapsed:.1f}ms")

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

    aggregated = {
        "mode": mode,
        "seeds": seeds,
        "Recall@1_mean": round(float(np.mean([r["Recall@1"] for r in all_seed_results])), 4),
        "Recall@1_std": round(float(np.std([r["Recall@1"] for r in all_seed_results])), 4),
        "Recall@5_mean": round(float(np.mean([r["Recall@5"] for r in all_seed_results])), 4),
        "Recall@5_std": round(float(np.std([r["Recall@5"] for r in all_seed_results])), 4),
        "MRR_mean": round(float(np.mean([r["MRR"] for r in all_seed_results])), 4),
        "Citation_Precision_mean": round(float(np.mean([r["Citation_Precision"] for r in all_seed_results])), 4),
        "Citation_Precision_std": round(float(np.std([r["Citation_Precision"] for r in all_seed_results])), 4),
        "Citation_Recall_mean": round(float(np.mean([r["Citation_Recall"] for r in all_seed_results])), 4),
        "Citation_Recall_std": round(float(np.std([r["Citation_Recall"] for r in all_seed_results])), 4),
        "Coverage_mean": round(float(np.mean([r["Coverage"] for r in all_seed_results])), 4),
        "Unsupported_Rate_mean": round(float(np.mean([r["Unsupported_Rate"] for r in all_seed_results])), 4),
        "Error_Taxonomy": error_counts,
        "Latency": calculate_latency_percentiles(latencies),
        "Compute_Cost_USD": 0.0
    }
    return aggregated


def main():
    parser = argparse.ArgumentParser(description="Run LuatCheck Evaluation Benchmark")
    parser.add_argument("--tasks", default="evaluation/tasks/vlqa_full_20.json", help="Path to tasks file")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 2026], help="Random seeds")
    parser.add_argument("--ablation", choices=["on", "off", "both", "three_way"], default="three_way", help="Verification mode")
    args = parser.parse_args()

    results = {}
    if args.ablation in ["off", "both", "three_way"]:
        results["baseline_off"] = run_benchmark(args.tasks, args.seeds, mode="off")

    if args.ablation in ["on", "both", "three_way"]:
        results["luatcheck_l1_on"] = run_benchmark(args.tasks, args.seeds, mode="l1_on")

    if args.ablation == "three_way":
        results["luatcheck_l1_l2_on"] = run_benchmark(args.tasks, args.seeds, mode="l1_l2_on")

    # Lưu kết quả
    os.makedirs("evaluation", exist_ok=True)
    with open("evaluation/eval_results_d3.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(" BẢNG TỔNG HỢP KẾT QUẢ ĐÁNH GIÁ ĐỊNH LƯỢNG D3 (THREE-WAY ABLATION STUDY)")
    print("=" * 80)
    header = f"{'Metric':<24} | {'Baseline (OFF)':<16} | {'LuatCheck (L1 ON)':<17} | {'LuatCheck (L1+L2)':<17}"
    print(header)
    print("-" * 80)

    b = results.get("baseline_off", {})
    l1 = results.get("luatcheck_l1_on", {})
    l2 = results.get("luatcheck_l1_l2_on", {})

    metrics_map = [
        ("Recall@1", "Recall@1_mean"),
        ("Recall@5", "Recall@5_mean"),
        ("MRR", "MRR_mean"),
        ("Citation Precision", "Citation_Precision_mean"),
        ("Citation Recall", "Citation_Recall_mean"),
        ("Answer Coverage", "Coverage_mean"),
        ("Unsupported Rate (↓)", "Unsupported_Rate_mean"),
    ]

    for label, m_key in metrics_map:
        b_val = f"{b.get(m_key, 0):.3f}"
        l1_val = f"{l1.get(m_key, 0):.3f}"
        l2_val = f"{l2.get(m_key, 0):.3f}"
        print(f"{label:<24} | {b_val:<16} | {l1_val:<17} | {l2_val:<17}")

    print("-" * 80)
    print("\n--- BẢNG PHÂN LOẠI LỖI (ERROR TAXONOMY DIAGNOSIS) ---")
    err_b = b.get("Error_Taxonomy", {})
    err_l1 = l1.get("Error_Taxonomy", {})
    err_l2 = l2.get("Error_Taxonomy", {})
    for k in err_b:
        print(f" - {k:<20}: Baseline={err_b.get(k, 0):<3} | L1_ON={err_l1.get(k, 0):<3} | L1+L2={err_l2.get(k, 0):<3}")
    print("=" * 80)


if __name__ == "__main__":
    main()
