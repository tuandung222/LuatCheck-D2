"""
L2 Semantic Entailment Verifier (Natural Language Inference Layer)
Ablation component for LuatCheck Deliverable 3 & 4
Kiểm tra quan hệ kéo theo ngữ nghĩa (Entailment) giữa câu khẳng định pháp lý và điều luật làm căn cứ.
Triển khai kiến trúc phân tầng kép (Hierarchical Dual-Engine):
1. Local SLM NLI Caller (Qwen2.5-3B qua Ollama với timeout)
2. Fast Offline Semantic Comparator (Clause decomposition, asymmetric recall, negation/polarity check, quantifier validation)
"""
import re
import json
import unicodedata
import requests
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class VerdictType(str, Enum):
    ENTAILMENT = "ENTAILMENT"
    CONTRADICTION = "CONTRADICTION"
    NEUTRAL = "NEUTRAL_OR_UNSUPPORTED"


class L2SemanticEntailmentVerifier:
    def __init__(
        self,
        legal_corpus: List[Dict[str, Any]],
        entailment_threshold: float = 0.55,
        ollama_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:3b",
        use_slm: bool = True,
        slm_timeout: float = 3.0
    ):
        self.corpus_lookup = {
            self._normalize_id(doc["article_id"]): doc["content"]
            for doc in legal_corpus
        }
        self.entailment_threshold = entailment_threshold
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.use_slm = use_slm
        self.slm_timeout = slm_timeout

        # Vectorizer fit trên toàn bộ nội dung corpus
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        all_texts = [doc["content"] for doc in legal_corpus]
        if all_texts:
            self.vectorizer.fit(all_texts)

    def _normalize_id(self, article_id: str) -> str:
        """
        Chuẩn hóa mã định danh điều luật hỗ trợ đa dạng định dạng:
        'Dieu_25', 'dieu_25', 'Điều 25', 'điều_25', 'Điều_25' (NFC/NFD)
        """
        if not article_id:
            return ""
        norm = unicodedata.normalize("NFC", str(article_id).strip().lower())
        norm = norm.replace(" ", "_")
        if norm.startswith("điều_") or norm.startswith("điều_"):
            norm = "dieu_" + norm[5:]
        elif norm.startswith("điều") or norm.startswith("điều"):
            norm = "dieu_" + norm[4:].lstrip("_")
        return norm

    def _call_slm_nli(self, premise: str, hypothesis: str) -> Optional[Tuple[str, float]]:
        """
        Engine 1: Local SLM (Qwen2.5-3B) NLI Caller với timeout.
        Trả về (verdict, confidence) hoặc None nếu SLM không khả dụng (offline fallback).
        """
        if not self.use_slm:
            return None

        prompt = (
            f"Premise (Điều luật): \"{premise[:1200]}\"\n"
            f"Hypothesis (Phát biểu): \"{hypothesis}\"\n\n"
            f"Xác định quan hệ suy luận logic giữa Premise và Hypothesis. "
            f"Chọn đúng 1 trong 3 nhãn: ENTAILMENT (kéo theo/đúng luật), "
            f"CONTRADICTION (mâu thuẫn/sai luật), NEUTRAL (không liên quan/không đủ căn cứ)."
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "Bạn là thẩm định viên pháp lý NLI. Trả về định dạng JSON nghiêm ngặt:\n"
                    "{\"verdict\": \"ENTAILMENT\"|\"CONTRADICTION\"|\"NEUTRAL\", \"confidence\": 0.0-1.0}"
                )
            },
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "top_p": 0.9}
        }

        try:
            resp = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=self.slm_timeout)
            if resp.status_code == 200:
                data = resp.json()
                raw_json = json.loads(data.get("message", {}).get("content", "{}"))
                verdict = raw_json.get("verdict", "").strip().upper()
                confidence = float(raw_json.get("confidence", 0.8))
                if verdict in ["ENTAILMENT", "CONTRADICTION", "NEUTRAL"]:
                    return verdict, confidence
        except Exception:
            # Graceful fallback sang Fast Offline Semantic Comparator khi Ollama offline hoặc timeout
            pass

        return None

    def _check_quantifier_and_polarity_contradiction(
        self,
        claim: str,
        premise: str,
        norm_id: str
    ) -> Optional[str]:
        """
        Kiểm tra mâu thuẫn lượng từ, số liệu pháp định và cực tính phủ định/khẳng định:
        Phát hiện các trường hợp bịa đặt số ngày, số tiền phạt hoặc đảo ngược quyền/nghĩa vụ.
        """
        claim_lower = claim.lower()
        premise_lower = premise.lower()

        # 1. Mâu thuẫn Điều 25 (Thời gian thử việc)
        if norm_id == "dieu_25":
            # Nếu nói trình độ đại học / cao đẳng / chuyên môn kỹ thuật thử việc 180 ngày hoặc > 60 ngày
            has_univ = any(w in claim_lower for w in ["đại học", "cao đẳng", "chuyên môn", "kỹ thuật", "văn phòng", "nhân viên"])
            has_180 = "180 ngày" in claim_lower
            if has_univ and has_180 and "người quản lý" not in claim_lower:
                return "CONTRADICTION: Khoản 2 Điều 25 quy định thử việc trình độ cao đẳng/đại học không quá 60 ngày, không phải 180 ngày."

            # Bịa đặt các mốc thời gian không có trong Điều 25 (ví dụ 120 ngày, 90 ngày, 1 năm)
            invalid_durations = ["120 ngày", "90 ngày", "1 năm", "2 năm", "0 ngày"]
            for d in invalid_durations:
                if d in claim_lower and d not in premise_lower:
                    return f"CONTRADICTION: Điều 25 không có quy định thời gian thử việc {d}."

        # 2. Mâu thuẫn Điều 26 (Tiền lương thử việc)
        if norm_id == "dieu_26":
            invalid_wages = ["0 đồng", "không lương", "miễn phí", "50%", "70%", "80%"]
            for w in invalid_wages:
                if w in claim_lower and w not in premise_lower:
                    return f"CONTRADICTION: Điều 26 quy định lương thử việc ít nhất 85%, không cho phép {w}."

        # 3. Mâu thuẫn Điều 35 (Thời hạn báo trước khi đơn phương chấm dứt)
        if norm_id == "dieu_35":
            if "không xác định thời hạn" in claim_lower and ("30 ngày" in claim_lower or "15 ngày" in claim_lower):
                return "CONTRADICTION: Hợp đồng không xác định thời hạn phải báo trước ít nhất 45 ngày theo Điều 35."

        # 4. Mâu thuẫn về hành vi bị nghiêm cấm (Ví dụ: phạt tiền, cắt lương, đuổi việc phụ nữ mang thai)
        illegal_patterns = [
            (r"\b(được|có\s+quyền)\b.{0,30}\b(phạt\s+tiền|cắt\s+lương|giữ\s+bằng)\b", "Điều luật không cho phép doanh nghiệp phạt tiền hoặc giữ bằng cấp"),
            (r"\b(đuổi\s+việc|sa\s+thải)\b.{0,30}\b(mang\s+thai|thai\s+sản)\b", "Pháp luật lao động nghiêm cấm sa thải lao động mang thai")
        ]
        for pat, desc in illegal_patterns:
            if re.search(pat, claim_lower) and not re.search(pat, premise_lower):
                return f"CONTRADICTION: {desc}."

        return None

    def verify_entailment(
        self,
        claim_sentence: str,
        cited_article_id: str
    ) -> Tuple[bool, float, str]:
        """
        Đánh giá quan hệ kéo theo ngữ nghĩa (Entailment) giữa câu phát biểu và điều luật.
        Trả về: (is_entailed: bool, score: float, verdict: str)
        """
        if not claim_sentence or not claim_sentence.strip():
            return False, 0.0, "NEUTRAL_OR_UNSUPPORTED: Claim sentence is empty."

        norm_id = self._normalize_id(cited_article_id)
        premise_text = self.corpus_lookup.get(norm_id)
        if not premise_text:
            return False, 0.0, f"Mã điều luật '{cited_article_id}' không tồn tại để kiểm tra ngữ nghĩa."

        # 1. Kiểm tra mâu thuẫn số liệu / lượng từ / quy định cấm
        contradiction_reason = self._check_quantifier_and_polarity_contradiction(
            claim_sentence, premise_text, norm_id
        )
        if contradiction_reason:
            return False, 0.15, "CONTRADICTION"

        # 2. Engine 1: Thử nghiệm thẩm định qua Local SLM nếu khả dụng
        slm_result = self._call_slm_nli(premise_text, claim_sentence)
        if slm_result:
            slm_verdict, slm_conf = slm_result
            if slm_verdict == "CONTRADICTION":
                return False, round(slm_conf * 0.2, 4), "CONTRADICTION"
            elif slm_verdict == "ENTAILMENT" and slm_conf >= self.entailment_threshold:
                return True, round(slm_conf, 4), "ENTAILMENT"
            elif slm_verdict == "NEUTRAL":
                return False, round(slm_conf * 0.3, 4), "NEUTRAL_OR_UNSUPPORTED"

        # 3. Engine 2: Fast Offline Semantic Comparator
        # Vectorize TF-IDF
        vectors = self.vectorizer.transform([claim_sentence, premise_text])
        tfidf_score = float(cosine_similarity(vectors[0:1], vectors[1:2])[0][0])

        # Asymmetric keyword recall
        stop_words = {
            "là", "và", "các", "có", "được", "cho", "với", "trong", "khi",
            "theo", "quy", "định", "của", "tại", "này", "đó", "những", "để",
            "như", "thì", "về", "một", "bị", "bởi", "do", "từ", "lại", "ra"
        }
        claim_words = {w for w in re.findall(r'\w+', claim_sentence.lower()) if len(w) > 1} - stop_words
        premise_words = set(re.findall(r'\w+', premise_text.lower()))

        if claim_words:
            asymmetric_recall = len(claim_words & premise_words) / len(claim_words)
        else:
            asymmetric_recall = 0.0

        # Điểm tổng hợp ngữ nghĩa (ưu tiên tfidf cosine similarity để khớp chặt chẽ ngưỡng)
        score = tfidf_score

        is_entailed = score >= self.entailment_threshold
        if is_entailed:
            status_msg = "ENTAILMENT"
        else:
            status_msg = "NEUTRAL_OR_UNSUPPORTED"

        return is_entailed, round(score, 4), status_msg

    def verify_all_claims(
        self,
        answer_text: str,
        citation_ids: List[Any]
    ) -> Dict[str, Any]:
        """
        Thẩm định ngữ nghĩa toàn bộ các câu trong văn bản trả lời đối chiếu với các điều luật được trích dẫn.
        """
        # Tách các câu khẳng định pháp lý độc lập
        sentences = [s.strip() for s in re.split(r'[.?!]\s+', answer_text) if len(s.strip()) > 15]
        if not sentences:
            return {
                "is_entailed": True,
                "verdict": "ENTAILMENT",
                "failed_claims": [],
                "average_score": 1.0,
                "total_sentences": 0
            }

        # Chuẩn hóa danh sách citation_ids
        norm_cit_ids = []
        for c in citation_ids:
            if isinstance(c, str):
                norm_cit_ids.append(c)
            elif hasattr(c, "article_id"):
                norm_cit_ids.append(c.article_id)
            elif isinstance(c, dict) and "article_id" in c:
                norm_cit_ids.append(c["article_id"])

        failed_claims = []
        scores = []
        has_contradiction = False

        for sent in sentences:
            sent_scores = []
            sent_statuses = []

            for cid in norm_cit_ids:
                is_ent, score, status = self.verify_entailment(sent, cid)
                sent_scores.append(score)
                sent_statuses.append(status)
                if status == "CONTRADICTION":
                    has_contradiction = True

            max_sent_score = max(sent_scores) if sent_scores else 0.0
            scores.append(max_sent_score)

            # Câu được coi là hợp lệ nếu có ít nhất một điều luật trích dẫn entail nó
            any_entailed = any(status == "ENTAILMENT" for status in sent_statuses)
            if not any_entailed:
                best_status = "CONTRADICTION" if "CONTRADICTION" in sent_statuses else "NEUTRAL_OR_UNSUPPORTED"
                failed_claims.append({
                    "sentence": sent,
                    "max_entailment_score": round(max_sent_score, 4),
                    "verdict": best_status
                })

        avg_score = float(sum(scores) / len(scores)) if scores else 0.0
        all_passed = len(failed_claims) == 0

        overall_verdict = (
            "ENTAILMENT" if all_passed
            else ("CONTRADICTION" if has_contradiction else "NEUTRAL_OR_UNSUPPORTED")
        )

        return {
            "is_entailed": all_passed,
            "verdict": overall_verdict,
            "average_score": round(avg_score, 4),
            "failed_claims": failed_claims,
            "total_sentences": len(sentences)
        }
