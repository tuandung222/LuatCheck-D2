"""
Grounding and Attribution Analysis Module.

Decouples sentence-level statutory attribution and token overlap verification
from UI rendering logic, enabling clean unit testing, headless benchmarking,
and modular integration.
"""
import re
from typing import Dict, Any, List, Optional
from src.agent.state import Citation


def analyze_grounding(
    answer_text: str,
    citations: List[Any],
    agent_or_verifier: Any
) -> Dict[str, Any]:
    """
    Analyzes sentence-level span support conforming to statutory evidence verification:
    Splits sentences, computes token overlap against cited statutory articles, and assigns attribution.
    
    Args:
        answer_text: The generated legal advice text.
        citations: List of Citation objects or dicts with article_id.
        agent_or_verifier: Either a LuatCheckAgent instance (with .verifier) or an L1EvidenceVerifier instance.
        
    Returns:
        Dict containing is_valid, unsupported_claims, invalid_citations, sentences_data, and grounded_ratio.
    """
    if not answer_text or not answer_text.strip():
        return {"is_valid": False, "sentences_data": [], "grounded_ratio": 0.0}

    # Extract L1 verifier instance
    if hasattr(agent_or_verifier, "verifier"):
        verifier = agent_or_verifier.verifier
    else:
        verifier = agent_or_verifier

    # Normalize citations
    norm_citations = []
    for c in citations:
        if isinstance(c, dict):
            norm_citations.append(Citation(**c))
        elif isinstance(c, Citation):
            norm_citations.append(c)

    retrieved_ids = [c.article_id for c in norm_citations]

    # 1. Invoke L1 Verifier for comprehensive statutory check
    l1_res = verifier.verify(
        answer_text=answer_text,
        citations=norm_citations,
        retrieved_article_ids=retrieved_ids
    )

    # 2. Split sentences and analyze detailed token overlap per sentence
    raw_sentences = [s.strip() for s in re.split(r'[.?!]\s+', answer_text) if len(s.strip()) > 15]
    sentences_data = []

    # Collect tokens per statutory article for accurate attribution assignment
    article_tokens: Dict[str, set] = {}
    for c in norm_citations:
        norm_id = verifier._normalize_id(c.article_id)
        doc = verifier.valid_article_ids.get(norm_id)
        if doc:
            article_tokens[c.article_id] = set(re.findall(r'\w+', doc.get("content", "").lower()))

    combined_law_text = " ".join(
        [
            verifier.valid_article_ids.get(verifier._normalize_id(c.article_id), {}).get("content", "").lower()
            for c in norm_citations
            if verifier.valid_article_ids.get(verifier._normalize_id(c.article_id))
        ]
    )
    all_law_tokens = set(re.findall(r'\w+', combined_law_text))
    stop_words = {"là", "và", "các", "có", "được", "cho", "với", "trong", "khi", "theo", "quy", "định", "của", "tại"}

    supported_count = 0
    for sent in raw_sentences:
        sent_words = set(re.findall(r'\w+', sent.lower()))
        meaningful_words = sent_words - stop_words
        if not meaningful_words:
            continue

        matches_total = sum(1 for w in meaningful_words if w in all_law_tokens)
        overlap_ratio = matches_total / len(meaningful_words) if meaningful_words else 0.0

        # Identify statutory article with highest overlap (Attribution mapping)
        best_aid = None
        best_overlap = 0.0
        for aid, tokens in article_tokens.items():
            m = sum(1 for w in meaningful_words if w in tokens)
            r = m / len(meaningful_words) if meaningful_words else 0.0
            if r > best_overlap:
                best_overlap = r
                best_aid = aid

        is_supported = (overlap_ratio >= 0.25)
        if is_supported:
            supported_count += 1

        sentences_data.append({
            "sentence": sent,
            "overlap_ratio": overlap_ratio,
            "is_supported": is_supported,
            "best_article_id": best_aid or (norm_citations[0].article_id if norm_citations else "N/A"),
            "best_overlap": best_overlap
        })

    ratio = (supported_count / len(sentences_data)) if sentences_data else (1.0 if l1_res.is_valid else 0.0)

    return {
        "is_valid": l1_res.is_valid,
        "unsupported_claims": l1_res.unsupported_claims,
        "invalid_citations": l1_res.invalid_citations,
        "sentences_data": sentences_data,
        "grounded_ratio": ratio
    }
