"""
Evaluation Metrics for LuatCheck Benchmark
Tính toán các chỉ số định lượng theo chuẩn bài báo Kapoor et al. (TMLR 2025) & Gao et al. (ALCE 2023)
"""
import numpy as np
from typing import List, Dict, Any, Set


def normalize_id(aid: str) -> str:
    aid = aid.strip().lower().replace(" ", "_")
    if aid.startswith("điều_"):
        aid = "dieu_" + aid[5:]
    return aid


def calculate_retrieval_metrics(retrieved_ids: List[str], ground_truth_id: str, k_list: List[int] = [1, 3, 5]) -> Dict[str, float]:
    """
    Tính Recall@k và MRR cho tác vụ truy xuất điều luật
    """
    norm_gt = normalize_id(ground_truth_id)
    norm_retrieved = [normalize_id(r) for r in retrieved_ids]

    metrics = {}
    for k in k_list:
        hits = 1.0 if norm_gt in norm_retrieved[:k] else 0.0
        metrics[f"Recall@{k}"] = hits

    # MRR (Mean Reciprocal Rank)
    if norm_gt in norm_retrieved:
        rank = norm_retrieved.index(norm_gt) + 1
        metrics["MRR"] = 1.0 / rank
    else:
        metrics["MRR"] = 0.0

    return metrics


def calculate_citation_metrics(predicted_citations: List[str], ground_truth_id: str) -> Dict[str, float]:
    """
    Tính Citation Precision và Citation Recall
    """
    norm_gt = normalize_id(ground_truth_id)
    norm_preds = {normalize_id(c) for c in predicted_citations}

    if not norm_preds:
        return {"citation_precision": 0.0, "citation_recall": 0.0}

    precision = 1.0 if norm_gt in norm_preds else 0.0
    recall = 1.0 if norm_gt in norm_preds else 0.0
    return {
        "citation_precision": precision,
        "citation_recall": recall
    }


def calculate_latency_percentiles(latencies: List[float]) -> Dict[str, float]:
    """
    Tính latency p50 và p95 (mili-giây)
    """
    if not latencies:
        return {"p50_ms": 0.0, "p95_ms": 0.0}
    return {
        "p50_ms": round(float(np.percentile(latencies, 50)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2)
    }
