"""
L1 Deterministic Evidence Verifier.

Guarantees 100% statutory citations exist, were retrieved in the current session (provenance),
and lexically support the claims made in the generated answer.
"""
import re
from typing import List, Dict, Any, Tuple
from src.agent.state import L1VerificationResult, Citation


class L1EvidenceVerifier:
    def __init__(self, legal_corpus: List[Dict[str, Any]], similarity_threshold: float = 0.65):
        self.valid_article_ids = {doc["article_id"].lower(): doc for doc in legal_corpus}
        self.similarity_threshold = similarity_threshold

    def _normalize_id(self, article_id: str) -> str:
        aid = article_id.strip().replace(" ", "_").lower()
        if aid.startswith("điều_"):
            aid = "dieu_" + aid[5:]
        return aid

    def verify(
        self,
        answer_text: str,
        citations: List[Citation],
        retrieved_article_ids: List[str]
    ) -> L1VerificationResult:
        """
        Evaluate 3-tier L1 verification:
        1. Existence Check: Article ID exists in statutory corpus.
        2. Provenance Check: Article was retrieved during the current session.
        3. Span Support Check: Answer sentences are supported by statutory text.
        """
        invalid_citations = []
        unsupported_claims = []
        retrieved_normalized = {self._normalize_id(aid) for aid in retrieved_article_ids}

        # 0. Check for empty answer
        if not answer_text or not answer_text.strip():
            return L1VerificationResult(
                is_valid=False,
                unsupported_claims=["Câu trả lời rỗng hoặc không có nội dung."],
                invalid_citations=[],
                repair_feedback="Câu trả lời rỗng không cung cấp nội dung tư vấn pháp lý."
            )

        # 1 & 2. Check citation identifiers
        if not citations:
            # If an affirmative answer is given without any citations
            return L1VerificationResult(
                is_valid=False,
                unsupported_claims=[answer_text.strip()],
                invalid_citations=["MISSING_CITATION"],
                repair_feedback="Bạn đưa ra câu trả lời khẳng định nhưng không cung cấp bất kỳ mã điều luật trích dẫn (citation) nào làm căn cứ!"
            )

        for c in citations:
            norm_id = self._normalize_id(c.article_id)
            # Existence check
            if norm_id not in self.valid_article_ids:
                invalid_citations.append(f"Mã điều luật '{c.article_id}' không tồn tại trong Bộ luật Lao động 2019.")
            # Provenance check
            elif norm_id not in retrieved_normalized:
                invalid_citations.append(
                    f"Mã điều luật '{c.article_id}' tồn tại nhưng chưa từng được bạn tra cứu trong phiên làm việc này. Bị nghi ngờ là hallucination!"
                )

        if invalid_citations:
            return L1VerificationResult(
                is_valid=False,
                unsupported_claims=[],
                invalid_citations=invalid_citations,
                repair_feedback="\n".join(invalid_citations)
            )

        # 3. Span support check (Lexical token overlap between answer clauses and cited statutory text)
        # Aggregate cited statutory texts
        cited_texts = []
        for c in citations:
            norm_id = self._normalize_id(c.article_id)
            doc = self.valid_article_ids.get(norm_id)
            if doc:
                cited_texts.append(doc["content"].lower())
        combined_law_text = " ".join(cited_texts)
        law_token_set = set(re.findall(r'\w+', combined_law_text))
        # Segment answer into clauses/sentences (do not ignore short clauses)
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
            matches = sum(1 for w in meaningful_words if w in law_token_set)
            overlap_ratio = matches / len(meaningful_words)

            if overlap_ratio < 0.25: # If token overlap is below 25% threshold
                unsupported_claims.append(sent)

        if unsupported_claims:
            feedback = (
                f"Phát hiện {len(unsupported_claims)} câu khẳng định chưa tìm thấy căn cứ đối ứng trong điều luật trích dẫn:\n"
                + "\n".join(f"- \"{c}\"" for c in unsupported_claims[:2])
            )
            return L1VerificationResult(
                is_valid=False,
                unsupported_claims=unsupported_claims,
                invalid_citations=[],
                repair_feedback=feedback
            )

        return L1VerificationResult(
            is_valid=True,
            unsupported_claims=[],
            invalid_citations=[],
            repair_feedback=None
        )
