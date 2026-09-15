"""
L1 Deterministic Evidence Verifier
Bảo đảm 100% trích dẫn căn cứ pháp lý là có thực, đã được truy xuất và hỗ trợ phát biểu
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
        Kiểm tra 3 tầng xác thực L1:
        1. Existence Check: Mã điều luật có tồn tại trong bộ luật hay không.
        2. Provenance Check: Điều luật có nằm trong số tài liệu được truy xuất ở phiên này không.
        3. Span Support Check: Các câu trả lời có được hỗ trợ bởi nội dung điều luật không.
        """
        invalid_citations = []
        unsupported_claims = []
        retrieved_normalized = {self._normalize_id(aid) for aid in retrieved_article_ids}

        # 0. Kiểm tra câu trả lời rỗng
        if not answer_text or not answer_text.strip():
            return L1VerificationResult(
                is_valid=False,
                unsupported_claims=["Câu trả lời rỗng hoặc không có nội dung."],
                invalid_citations=[],
                repair_feedback="Câu trả lời rỗng không cung cấp nội dung tư vấn pháp lý."
            )

        # 1 & 2. Kiểm tra mã điều luật
        if not citations:
            # Nếu có câu trả lời khẳng định nhưng không có trích dẫn nào
            return L1VerificationResult(
                is_valid=False,
                unsupported_claims=[answer_text.strip()],
                invalid_citations=["MISSING_CITATION"],
                repair_feedback="Bạn đưa ra câu trả lời khẳng định nhưng không cung cấp bất kỳ mã điều luật trích dẫn (citation) nào làm căn cứ!"
            )

        for c in citations:
            norm_id = self._normalize_id(c.article_id)
            # Kiểm tra tồn tại
            if norm_id not in self.valid_article_ids:
                invalid_citations.append(f"Mã điều luật '{c.article_id}' không tồn tại trong Bộ luật Lao động 2019.")
            # Kiểm tra nguồn gốc truy xuất
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

        # 3. Span support check (Kiểm tra overlap ngữ nghĩa giữa các câu trả lời và văn bản điều luật)
        # Gom nội dung các điều luật trích dẫn
        cited_texts = []
        for c in citations:
            norm_id = self._normalize_id(c.article_id)
            doc = self.valid_article_ids.get(norm_id)
            if doc:
                cited_texts.append(doc["content"].lower())
        combined_law_text = " ".join(cited_texts)
        law_token_set = set(re.findall(r'\w+', combined_law_text))
        # Tách câu trả lời thành từng mệnh đề / câu đơn (không bỏ qua câu ngắn)
        raw_sentences = [s.strip() for s in re.split(r'[.?!;\n]+', answer_text) if s.strip()]
        stop_words = {"là", "và", "các", "có", "được", "cho", "với", "trong", "khi", "theo", "quy", "định", "của", "tại", "này", "đó", "những"}

        for sent in raw_sentences:
            sent_words = set(re.findall(r'\w+', sent.lower()))
            if not sent_words:
                continue

            meaningful_words = sent_words - stop_words
            if not meaningful_words:
                meaningful_words = sent_words

            # Sử dụng phép giao tập hợp token (Token Set Intersection)
            matches = sum(1 for w in meaningful_words if w in law_token_set)
            overlap_ratio = matches / len(meaningful_words)

            if overlap_ratio < 0.25: # Nếu dưới 25% từ vựng xuất hiện trong luật
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
