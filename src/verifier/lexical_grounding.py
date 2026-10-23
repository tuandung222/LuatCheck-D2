"""
Lexical Grounding and Citation Provenance Verifier.

Checks that citations exist and were retrieved in the current session (provenance),
and lexically support the claims made in the generated answer.
"""
import re
from decimal import Decimal
from typing import List, Dict, Any, Optional
from src.agent.state import GroundingVerificationResult, Citation
from src.domains import DomainProfile, load_profile


SENTENCE_SPLIT = re.compile(r'(?:(?<=[?!;])\s*|(?<!\b\d[.])(?<=[.])\s+|\n+)')


def _squash(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]


def _quantity_key(value: str) -> str:
    """'3,5 tháng' -> '3.5:tháng': number normalised, unit without inner whitespace."""
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(.+)", value.strip().lower())
    return str(Decimal(match.group(1).replace(",", ".")).normalize()) + ":" + re.sub(r"\s+", "", match.group(2))


class LexicalGroundingVerifier:
    """
    Deterministic evidence grounding verifier.
    Performs 3-stage validation:
    1. Existence Check: Document ID exists in knowledge corpus.
    2. Provenance Check: Document was actually retrieved in the current session.
    3. Span Support Check: Answer sentences have token overlap with cited source text.
    """

    def __init__(self, corpus: List[Dict[str, Any]], similarity_threshold: float = 0.65, overlap_threshold: float = 0.25,
                 profile: Optional[DomainProfile] = None):
        # ID convention, quantity units, stopwords and feedback wording come from the domain profile
        # (default: labour, the behaviour before profiles existed).
        self.profile = profile or load_profile()
        self.valid_article_ids = {
            str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or "").lower(): doc
            for doc in corpus
        }
        self.similarity_threshold = similarity_threshold
        self.overlap_threshold = overlap_threshold

    def _normalize_id(self, doc_id: str) -> str:
        return self.profile.normalize_id(doc_id)

    def verify(
        self,
        answer_text: str,
        citations: List[Citation],
        retrieved_article_ids: List[str]
    ) -> GroundingVerificationResult:
        """
        Evaluate 3-stage lexical grounding verification.
        """
        messages = self.profile.messages
        if not answer_text or not answer_text.strip():
            return self._reject(unsupported=[messages.l1_empty_answer_claim], feedback=messages.l1_empty_answer_feedback)
        if not citations:
            return self._reject(unsupported=[answer_text.strip()], invalid=["MISSING_CITATION"],
                                feedback=messages.l1_missing_citation_feedback)

        invalid_citations = self._invalid_citations(citations, retrieved_article_ids)
        if invalid_citations:
            return self._reject(invalid=invalid_citations, feedback="\n".join(invalid_citations))

        unsupported_claims = self._unsupported_sentences(answer_text, citations)
        if unsupported_claims:
            feedback = messages.l1_unsupported_claims.format(
                count=len(unsupported_claims), claims="\n".join(f'- "{c}"' for c in unsupported_claims[:2]))
            return self._reject(unsupported=unsupported_claims, feedback=feedback)

        return GroundingVerificationResult(is_valid=True, unsupported_claims=[], invalid_citations=[], repair_feedback=None)

    @staticmethod
    def _reject(feedback: str, unsupported: Optional[List[str]] = None,
                invalid: Optional[List[str]] = None) -> GroundingVerificationResult:
        return GroundingVerificationResult(is_valid=False, unsupported_claims=unsupported or [],
                                           invalid_citations=invalid or [], repair_feedback=feedback)

    def _invalid_citations(self, citations: List[Citation], retrieved_article_ids: List[str]) -> List[str]:
        """Existence, provenance (retrieved in this session) and exact-quote checks, in citation order."""
        messages = self.profile.messages
        retrieved_normalized = {self._normalize_id(aid) for aid in retrieved_article_ids}
        problems: List[str] = []
        for c in citations:
            norm_id = self._normalize_id(c.article_id)
            if norm_id not in self.valid_article_ids:
                problems.append(messages.l1_unknown_citation.format(doc_id=c.article_id))
            elif norm_id not in retrieved_normalized:
                problems.append(messages.unretrieved_citation.format(doc_id=c.article_id))
            if norm_id in self.valid_article_ids and c.exact_quote:
                source = self.valid_article_ids[norm_id].get("content", "")
                if _squash(c.exact_quote) not in _squash(source):
                    problems.append(messages.l1_quote_mismatch.format(doc_id=c.article_id))
        return problems

    def _unsupported_sentences(self, answer_text: str, citations: List[Citation]) -> List[str]:
        """Answer sentences whose quantities are absent from, or whose tokens barely overlap, the cited text.

        Exact quantity checks catch simple numeric mutations. This is still a lexical heuristic, not a calibrated
        semantic/legal correctness oracle.
        """
        cited_texts = []
        for c in citations:
            doc = self.valid_article_ids.get(self._normalize_id(c.article_id))
            if doc:
                title = doc.get("title") or ""
                content = doc.get("content") or doc.get("full_content") or ""
                cited_texts.append((f"{title}. {content}" if title else content).lower())
        source_text = " ".join(cited_texts)
        quantity_pattern = self.profile.quantity_pattern
        source_quantities = {_quantity_key(q) for q in re.findall(quantity_pattern, source_text)}
        source_tokens = set(re.findall(r'\w+', source_text))
        stop_words = self.profile.stopword_set

        unsupported = []
        for sentence in split_sentences(answer_text):
            quantities = {_quantity_key(q) for q in re.findall(quantity_pattern, sentence.lower())}
            if quantities - source_quantities:
                unsupported.append(sentence)
                continue
            words = set(re.findall(r'\w+', sentence.lower()))
            if not words:
                continue
            meaningful = (words - stop_words) or words
            overlap = sum(1 for w in meaningful if w in source_tokens) / len(meaningful)
            if overlap < self.overlap_threshold:
                unsupported.append(sentence)
        return unsupported


CitationGroundingVerifier = LexicalGroundingVerifier
L1EvidenceVerifier = LexicalGroundingVerifier

__all__ = ["LexicalGroundingVerifier", "split_sentences", "CitationGroundingVerifier", "L1EvidenceVerifier"]
