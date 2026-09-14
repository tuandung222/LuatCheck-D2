"""
Evaluation Metrics for LuatCheck Benchmark
Tính toán các chỉ số định lượng theo chuẩn bài báo Kapoor et al. (TMLR 2025) & Gao et al. (ALCE 2023)
"""
import re
import numpy as np
from typing import List, Dict, Any, Set, Optional

try:
    from src.agent.state import Citation
except ImportError:
    class Citation:
        def __init__(self, article_id: str, **kwargs):
            self.article_id = article_id


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


def calculate_unsupported_rate(
    answer_text: Optional[str],
    cited_articles: Optional[List[Any]],
    verifier: Any,
    retrieved_article_ids: Optional[List[str]] = None
) -> float:
    """
    Tính Unsupported-Sentence Rate (tỷ lệ câu khẳng định không có căn cứ pháp lý hỗ trợ).
    Chuẩn hóa theo ALCE (Gao et al., 2023) và benchmark pháp lý:
    - Nếu câu trả lời rỗng hoặc từ chối (refusal), Unsupported Rate = 0.0 (không phát biểu sai).
    - Tách câu trả lời thành từng câu khẳng định đơn lập.
    - Với mỗi câu, đối chiếu với các điều luật được trích dẫn thông qua verifier.
    - Unsupported Rate = số câu không có căn cứ / tổng số câu khẳng định.
    """
    if not answer_text or not isinstance(answer_text, str) or not answer_text.strip():
        return 0.0

    # 1. Tách câu trả lời thành danh sách các câu phát biểu độc lập
    raw_sentences = [s.strip() for s in re.split(r'[.?!]\s+|\n+', answer_text) if s.strip()]
    sentences = []
    for s in raw_sentences:
        cleaned = re.sub(r'^[-\s•*0-9.)]+', '', s).strip()
        # Loại bỏ các đoạn quá ngắn hoặc tiêu đề không chứa mệnh đề pháp lý
        if len(cleaned) > 15:
            sentences.append(cleaned)

    # Nếu không có câu nào > 15 ký tự nhưng answer_text có nội dung, giữ nguyên answer_text
    if not sentences and len(answer_text.strip()) > 0:
        sentences = [answer_text.strip()]

    if not sentences:
        return 0.0

    # 2. Chuẩn hóa danh sách điều luật trích dẫn
    citation_objs = []
    raw_article_ids = []
    if cited_articles:
        for c in cited_articles:
            if isinstance(c, Citation):
                citation_objs.append(c)
                raw_article_ids.append(c.article_id)
            elif isinstance(c, dict) and "article_id" in c:
                citation_objs.append(Citation(article_id=str(c["article_id"])))
                raw_article_ids.append(str(c["article_id"]))
            elif isinstance(c, str) and c.strip():
                citation_objs.append(Citation(article_id=c.strip()))
                raw_article_ids.append(c.strip())

    # Nếu đưa ra câu trả lời khẳng định nhưng không có bất kỳ trích dẫn điều luật nào
    if not citation_objs:
        return 1.0

    if retrieved_article_ids is None:
        retrieved_article_ids = list(raw_article_ids)

    # 3. Đánh giá từng câu bằng verifier
    unsupported_count = 0
    for s in sentences:
        is_supported = False
        if hasattr(verifier, "verify"):
            res = verifier.verify(
                answer_text=s,
                citations=citation_objs,
                retrieved_article_ids=retrieved_article_ids
            )
            is_supported = getattr(res, "is_valid", False)
        elif hasattr(verifier, "verify_all_claims"):
            res = verifier.verify_all_claims(s, raw_article_ids)
            is_supported = res.get("is_entailed", False)
        elif hasattr(verifier, "verify_entailment"):
            for aid in raw_article_ids:
                is_ent, _, _ = verifier.verify_entailment(s, aid)
                if is_ent:
                    is_supported = True
                    break
        else:
            is_supported = True

        if not is_supported:
            unsupported_count += 1

    return round(float(unsupported_count / len(sentences)), 4)

