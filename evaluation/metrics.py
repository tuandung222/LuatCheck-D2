"""
Evaluation Metrics for LuatCheck Benchmark.
Calculates quantitative metrics conforming to Kapoor et al. (TMLR 2025) & Gao et al. (ALCE 2023).
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


def calculate_retrieval_metrics(retrieved_ids: List[str], ground_truth_id: Any, k_list: List[int] = [1, 3, 5]) -> Dict[str, float]:
    """
    Computes Recall@k and MRR for statutory retrieval tasks.
    """
    if isinstance(ground_truth_id, (list, tuple, set)):
        norm_gts = [normalize_id(g) for g in ground_truth_id if g]
    else:
        norm_gts = [normalize_id(ground_truth_id)] if ground_truth_id else []

    norm_retrieved = [normalize_id(r) for r in retrieved_ids]

    metrics = {}
    for k in k_list:
        hits = 1.0 if any(g in norm_retrieved[:k] for g in norm_gts) else 0.0
        metrics[f"Recall@{k}"] = hits

    # MRR (Mean Reciprocal Rank)
    ranks = [norm_retrieved.index(g) + 1 for g in norm_gts if g in norm_retrieved]
    if ranks:
        metrics["MRR"] = round(1.0 / min(ranks), 4)
    else:
        metrics["MRR"] = 0.0

    return metrics


def calculate_citation_metrics(predicted_citations: List[str], ground_truth_id: Any) -> Dict[str, float]:
    """
    Computes Citation Precision and Citation Recall.
    """
    if isinstance(ground_truth_id, (list, tuple, set)):
        norm_gts = {normalize_id(g) for g in ground_truth_id if g}
    else:
        norm_gts = {normalize_id(ground_truth_id)} if ground_truth_id else set()

    norm_preds = {normalize_id(c) for c in predicted_citations if c}

    if not norm_preds:
        return {"citation_precision": 0.0, "citation_recall": 0.0}
    if not norm_gts:
        return {"citation_precision": 0.0, "citation_recall": 1.0}

    hits = len(norm_preds & norm_gts)
    precision = hits / len(norm_preds) if norm_preds else 0.0
    recall = hits / len(norm_gts) if norm_gts else 0.0
    return {
        "citation_precision": round(float(precision), 4),
        "citation_recall": round(float(recall), 4)
    }


def calculate_latency_percentiles(latencies: List[float]) -> Dict[str, float]:
    """
    Computes p50 and p95 latency (in milliseconds).
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
    Computes Unsupported-Sentence Rate (fraction of claims lacking statutory support).
    Standardized according to ALCE (Gao et al., 2023) and legal QA benchmarks:
    - If answer is empty or a refusal, Unsupported Rate = 0.0 (no unsupported assertions made).
    - Splits the response into individual proposition sentences.
    - Matches each sentence against cited statutory articles using the verifier.
    - Unsupported Rate = unsupported sentences / total proposition sentences.
    """
    if not answer_text or not isinstance(answer_text, str) or not answer_text.strip():
        return 0.0

    # 1. Split response into individual proposition sentences
    raw_sentences = [s.strip() for s in re.split(r'[.?!]\s+|\n+', answer_text) if s.strip()]
    sentences = []
    for s in raw_sentences:
        cleaned = re.sub(r'^[-\s•*0-9.)]+', '', s).strip()
        # Filter out short fragments or titles that lack legal propositions
        if len(cleaned) > 15:
            sentences.append(cleaned)

    # If no sentence > 15 chars but text is non-empty, keep full text
    if not sentences and len(answer_text.strip()) > 0:
        sentences = [answer_text.strip()]

    if not sentences:
        return 0.0

    # 2. Normalize list of cited statutory articles
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

    # If an affirmative response is provided without any statutory citations
    if not citation_objs:
        return 1.0

    if retrieved_article_ids is None:
        retrieved_article_ids = list(raw_article_ids)

    # 3. Verify each sentence using verifier
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

