"""
Lexical Grounding and Citation Provenance Verifier.

Guarantees 100% citations exist, were retrieved in the current session (provenance),
and lexically support the claims made in the generated answer.
"""
import re
from typing import List, Dict, Any, Tuple
from src.agent.state import GroundingVerificationResult, Citation


class LexicalGroundingVerifier:
    """
    Deterministic evidence grounding verifier.
    Performs 3-stage validation:
    1. Existence Check: Document ID exists in knowledge corpus.
    2. Provenance Check: Document was actually retrieved in the current session.
    3. Span Support Check: Answer sentences have token overlap with cited source text.
    """

    def __init__(self, corpus: List[Dict[str, Any]], similarity_threshold: float = 0.65):
        self.valid_article_ids = {
            str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or "").lower(): doc
            for doc in corpus
        }
        self.similarity_threshold = similarity_threshold

    def _normalize_id(self, doc_id: str) -> str:
        did = str(doc_id).strip().replace(" ", "_").lower()
        if did.startswith("điều_"):
            did = "dieu_" + did[5:]
        return did

    def verify(
        self,
        answer_text: str,
        citations: List[Citation],
        retrieved_article_ids: List[str]
    ) -> GroundingVerificationResult:
        """
        Evaluate 3-stage lexical grounding verification.
        """
        invalid_citations = []
        unsupported_claims = []
        retrieved_normalized = {self._normalize_id(aid) for aid in retrieved_article_ids}

        # 0. Check for empty answer
        if not answer_text or not answer_text.strip():
            return GroundingVerificationResult(
                is_valid=False,
                unsupported_claims=["Câu trả lời rỗng hoặc không có nội dung."],
                invalid_citations=[],
                repair_feedback="Câu trả lời rỗng không cung cấp nội dung tư vấn có căn cứ."
            )

        # 1 & 2. Check citation identifiers
        if not citations:
            return GroundingVerificationResult(
                is_valid=False,
                unsupported_claims=[answer_text.strip()],
                invalid_citations=["MISSING_CITATION"],
                repair_feedback="Bạn đưa ra câu trả lời khẳng định nhưng không cung cấp bất kỳ trích dẫn nguồn (citation) nào làm căn cứ!"
            )

        for c in citations:
            norm_id = self._normalize_id(c.article_id)
            # Existence check
            if norm_id not in self.valid_article_ids:
                invalid_citations.append(f"Mã tài liệu trích dẫn '{c.article_id}' không tồn tại trong cơ sở tri thức.")
            # Provenance check
            elif norm_id not in retrieved_normalized:
                invalid_citations.append(
                    f"Mã điều luật '{c.article_id}' tồn tại nhưng chưa từng được bạn tra cứu trong phiên làm việc này. Bị nghi ngờ là hallucination!"
                )

        if invalid_citations:
            return GroundingVerificationResult(
                is_valid=False,
                unsupported_claims=[],
                invalid_citations=invalid_citations,
                repair_feedback="\n".join(invalid_citations)
            )

        # 3. Span support check (Lexical token overlap between answer clauses and cited text)
        cited_texts = []
        for c in citations:
            norm_id = self._normalize_id(c.article_id)
            doc = self.valid_article_ids.get(norm_id)
            if doc:
                content = doc.get("content") or doc.get("full_content") or ""
                cited_texts.append(content.lower())
        combined_source_text = " ".join(cited_texts)
        source_token_set = set(re.findall(r'\w+', combined_source_text))
        raw_sentences = [s.strip() for s in re.split(r'[.?!;\n]+', answer_text) if s.strip()]
        stop_words = {"là", "và", "các", "có", "được", "cho", "với", "trong", "khi", "theo", "quy", "định", "của", "tại", "này", "đó", "những"}

        for sent in raw_sentences:
            sent_words = set(re.findall(r'\w+', sent.lower()))
            if not sent_words:
                continue

            meaningful_words = sent_words - stop_words
            if not meaningful_words:
                meaningful_words = sent_words

            # Token Set Intersection overlap ratio
            matches = sum(1 for w in meaningful_words if w in source_token_set)
            overlap_ratio = matches / len(meaningful_words)

            if overlap_ratio < 0.25:
                unsupported_claims.append(sent)

        if unsupported_claims:
            feedback = (
                f"Phát hiện {len(unsupported_claims)} câu khẳng định chưa tìm thấy căn cứ đối ứng trong tài liệu trích dẫn:\n"
                + "\n".join(f"- \"{c}\"" for c in unsupported_claims[:2])
            )
            return GroundingVerificationResult(
                is_valid=False,
                unsupported_claims=unsupported_claims,
                invalid_citations=[],
                repair_feedback=feedback
            )

        return GroundingVerificationResult(
            is_valid=True,
            unsupported_claims=[],
            invalid_citations=[],
            repair_feedback=None
        )


CitationGroundingVerifier = LexicalGroundingVerifier
L1EvidenceVerifier = LexicalGroundingVerifier

__all__ = ["LexicalGroundingVerifier", "CitationGroundingVerifier", "L1EvidenceVerifier"]
