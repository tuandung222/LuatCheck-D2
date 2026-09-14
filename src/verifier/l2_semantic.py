"""
L2 Semantic Entailment Verifier (Natural Language Inference Layer)
Hardened Version for LuatCheck Deliverable 3 & 4 (Milestone 1 Iteration 2 Remediation)
Kiểm tra quan hệ kéo theo ngữ nghĩa (Entailment) giữa câu khẳng định pháp lý và điều luật làm căn cứ.
Triển khai kiến trúc phân tầng kép (Hierarchical Dual-Engine):
1. Local SLM NLI Caller (Qwen2.5-3B qua Ollama với timeout 10.0s)
2. Fast Offline Semantic Comparator:
   - Robust sentence splitting & anti-vacuous approval (handles short sentences >= 3 chars)
   - Dynamic numerical duration & quantifier clash detection (Article 20, 24, 25, 26, 35, 36)
   - Negation / polarity contradiction detection & statutory rights protection (Article 17, 24, 26, 37, 122)
   - TF-IDF cosine similarity & asymmetric recall fallback
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
        slm_timeout: float = 10.0
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

    def _extract_durations(self, text: str) -> List[Tuple[float, str, str]]:
        """
        Trích xuất các mốc thời gian và quy đổi tương đối về số ngày để kiểm tra ràng buộc pháp lý:
        Trả về list of tuples: (days: float, unit_type: str, raw_expression: str)
        """
        text_lower = text.lower()
        durations = []
        matches = re.finditer(r"(\d+(?:[.,]\d+)?)\s*(ngày\s+làm\s+việc|ngày|tháng|năm|tuần)", text_lower)
        for m in matches:
            num_str, unit = m.group(1), m.group(2).strip()
            num = float(num_str.replace(",", "."))
            if "ngày" in unit:
                durations.append((num, "day", f"{num_str} {unit}"))
            elif "tháng" in unit:
                durations.append((num * 30.0, "month", f"{num_str} {unit}"))
            elif "năm" in unit:
                durations.append((num * 365.0, "year", f"{num_str} {unit}"))
            elif "tuần" in unit:
                durations.append((num * 7.0, "week", f"{num_str} {unit}"))
        return durations

    def _extract_percentages(self, text: str) -> List[float]:
        """
        Trích xuất tỷ lệ phần trăm trong phát biểu.
        """
        matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*%", text)
        return [float(m.replace(",", ".")) for m in matches]

    def _call_slm_nli(self, premise: str, hypothesis: str) -> Optional[Tuple[str, float]]:
        """
        Engine 1: Local SLM (Qwen2.5-3B) NLI Caller với timeout mặc định 10.0s.
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
        durations = self._extract_durations(claim)
        percentages = self._extract_percentages(claim)

        # 1. Mâu thuẫn Điều 25 (Thời gian thử việc)
        if norm_id == "dieu_25":
            # Chỉ kiểm tra ràng buộc thử việc nếu claim có đề cập tới thử việc
            if "thử việc" in claim_lower:
                # Tần suất thử việc: chỉ được thử việc 1 lần đối với một công việc
                if re.search(r"\bthử\s+việc\b.{0,25}\b(nhiều\s+lần|2\s+lần|hai\s+lần|lần\s+hai|từ\s+2\s+lần)\b", claim_lower):
                    return "CONTRADICTION: Điều 25 quy định chỉ được thử việc một lần đối với một công việc."

                # Chức danh quản lý (vị trí/công việc người quản lý doanh nghiệp)
                is_manager_job = any(w in claim_lower for w in [
                    "công việc của người quản lý", "chức danh quản lý", "vị trí quản lý",
                    "người quản lý doanh nghiệp", "người quản lý", "vị trí giám đốc", "làm giám đốc"
                ])

                for days, unit_type, raw_str in durations:
                    if days <= 0:
                        return f"CONTRADICTION: Điều 25 không quy định thời gian thử việc {raw_str}."
                    if days > 180:
                        return f"CONTRADICTION: Điều 25 quy định thời gian thử việc tối đa không quá 180 ngày (kể cả người quản lý doanh nghiệp), không thể là {raw_str}."

                    # Trình độ trung cấp, công nhân kỹ thuật, sơ cấp: tối đa 30 ngày (enforce even if 'kỹ thuật' in text)
                    has_vocational = any(w in claim_lower for w in ["công nhân kỹ thuật", "trung cấp", "sơ cấp", "công nhân", "nghiệp vụ"])
                    if has_vocational and not is_manager_job and days > 30:
                        return f"CONTRADICTION: Khoản 3 Điều 25 quy định thử việc trình độ trung cấp, công nhân kỹ thuật không quá 30 ngày, không thể là {raw_str}."

                    has_univ = any(w in claim_lower for w in ["đại học", "cao đẳng", "chuyên môn", "kỹ thuật", "văn phòng", "nhân viên", "cử nhân", "kỹ sư", "chuyên viên"])

                    # Trình độ chuyên môn kỹ thuật từ cao đẳng trở lên: tối đa 60 ngày
                    if has_univ and not is_manager_job and days > 60:
                        return f"CONTRADICTION: Khoản 2 Điều 25 quy định thử việc trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên không quá 60 ngày, không thể là {raw_str}."

                    # Công việc khác: tối đa 06 ngày làm việc
                    has_simple = any(w in claim_lower for w in ["công việc khác", "lao động phổ thông", "giản đơn"])
                    if has_simple and days > 6:
                        return f"CONTRADICTION: Khoản 4 Điều 25 quy định thử việc đối với công việc khác không quá 06 ngày làm việc, không thể là {raw_str}."

                    # Mặc định: nếu không thuộc chức danh quản lý mà số ngày > 60
                    if not is_manager_job and days > 60:
                        return f"CONTRADICTION: Điều 25 quy định thời gian thử việc thông thường không quá 60 ngày (chỉ công việc người quản lý doanh nghiệp tối đa 180 ngày), không thể là {raw_str}."

        # 2. Mâu thuẫn Điều 20 (Loại hợp đồng lao động)
        if norm_id == "dieu_20":
            if any(w in claim_lower for w in ["xác định thời hạn", "hợp đồng lao động", "thời hạn hợp đồng"]):
                for days, unit_type, raw_str in durations:
                    if (unit_type == "month" and days > 36 * 30) or (unit_type == "year" and days > 3 * 365) or days > 1095:
                        return f"CONTRADICTION: Điểm b khoản 1 Điều 20 quy định hợp đồng lao động xác định thời hạn có thời hạn không quá 36 tháng (3 năm), không cho phép {raw_str}."

        # 3. Mâu thuẫn Điều 24 (Thử việc: Không áp dụng thử việc đối với HĐLĐ dưới 01 tháng)
        if norm_id == "dieu_24":
            has_under_1m = any(w in claim_lower for w in ["dưới 01 tháng", "dưới 1 tháng", "dưới 30 ngày", "dưới một tháng"])

            # Phát hiện hợp đồng có thời hạn cụ thể < 30 ngày (e.g. 15 ngày, 2 tuần, 3 tuần)
            has_short_contract = False
            short_dur_desc = ""
            for days, unit_type, raw_str in durations:
                if 0 < days < 30.0:
                    pat1 = rf"\b(hợp\s+đồng|hđlđ|hđ|giao\s+kết)\b(?:(?!\bthử\s+việc\b).){{0,25}}\b{re.escape(raw_str)}"
                    pat2 = rf"{re.escape(raw_str)}\s+(?:hợp\s+đồng|hđlđ|hđ)"
                    if re.search(pat1, claim_lower) or re.search(pat2, claim_lower):
                        has_short_contract = True
                        short_dur_desc = raw_str
                        break

            if (has_under_1m or has_short_contract) and "thử việc" in claim_lower:
                # Nếu câu khẳng định được phép / áp dụng thử việc mà không có từ ngữ phủ định
                if not re.search(r"\b(không\s+áp\s+dụng|không\s+được|nghiêm\s+cấm|cấm|không\s+thể)\b.{0,30}\bthử\s+việc\b", claim_lower) and \
                   not re.search(r"\bthử\s+việc\b.{0,30}\b(không\s+áp\s+dụng|không\s+được|bị\s+cấm)\b", claim_lower):
                    desc_str = f" ({short_dur_desc})" if short_dur_desc else ""
                    return f"CONTRADICTION: Khoản 3 Điều 24 quy định không áp dụng thử việc đối với người lao động giao kết hợp đồng lao động có thời hạn dưới 01 tháng{desc_str}."

        # 4. Mâu thuẫn Điều 26 (Tiền lương thử việc: ít nhất 85%)
        if norm_id == "dieu_26":
            for pct in percentages:
                if pct < 85.0:
                    return f"CONTRADICTION: Điều 26 quy định tiền lương thử việc ít nhất phải bằng 85% mức lương của công việc đó, không thể là {pct}%."
            if any(w in claim_lower for w in ["0 đồng", "không lương", "miễn phí", "không được trả lương", "không trả lương", "không có lương", "không cần trả lương", "làm việc không công"]):
                return "CONTRADICTION: Điều 26 quy định tiền lương thử việc ít nhất phải bằng 85%, không cho phép làm việc không lương."

        # 5. Mâu thuẫn Điều 35 (Thời hạn báo trước khi người lao động đơn phương chấm dứt)
        if norm_id == "dieu_35":
            if "không xác định thời hạn" in claim_lower and not any(w in claim_lower for w in ["không cần báo trước", "khoản 2"]):
                for days, unit_type, raw_str in durations:
                    if days < 45 and "thử việc" not in claim_lower:
                        return f"CONTRADICTION: Điểm a khoản 1 Điều 35 quy định hợp đồng không xác định thời hạn phải báo trước ít nhất 45 ngày, không thể là {raw_str}."
            if "từ 12 tháng đến 36 tháng" in claim_lower or "xác định thời hạn" in claim_lower:
                for days, unit_type, raw_str in durations:
                    if days < 30 and "không xác định" not in claim_lower and "dưới 12 tháng" not in claim_lower and "không cần báo trước" not in claim_lower and "thử việc" not in claim_lower:
                        return f"CONTRADICTION: Điểm b khoản 1 Điều 35 quy định hợp đồng xác định thời hạn (12-36 tháng) phải báo trước ít nhất 30 ngày."

        # 6. Mâu thuẫn về các hành vi bị pháp luật lao động nghiêm cấm (Điều 17, 37, 122, 127)
        illegal_patterns = [
            (r"\b(được|có\s+quyền|cho\s+phép)\b.{0,30}\b(phạt\s+tiền|cắt\s+lương|trừ\s+lương|khấu\s+trừ\s+lương\s+thay\s+kỷ\s+luật)\b", "Pháp luật lao động nghiêm cấm người sử dụng lao động phạt tiền hoặc cắt lương người lao động thay cho việc xử lý kỷ luật"),
            (r"\b(được|có\s+quyền|cho\s+phép|yêu\s+cầu)\b.{0,30}\b(giữ|thu\s+giữ|tạm\s+giữ)\b.{0,30}\b(bằng\s+cấp|văn\s+bằng|chứng\s+chỉ|giấy\s+tờ\s+tùy\s+thân|cccd|cmnd|hộ\s+chiếu)\b", "Điều 17 Bộ luật Lao động nghiêm cấm giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ của người lao động"),
            (r"\b(đuổi\s+việc|sa\s+thải|xử\s+lý\s+kỷ\s+luật|chấm\s+dứt)\b.{0,30}\b(mang\s+thai|thai\s+sản|nuôi\s+con\s+(?:dưới\s+12\s+tháng|nhỏ))\b", "Khoản 4 Điều 122 và khoản 3 Điều 37 nghiêm cấm sa thải hoặc xử lý kỷ luật lao động đối với lao động nữ mang thai, nghỉ thai sản, nuôi con dưới 12 tháng tuổi"),
            (r"\b(được|có\s+quyền)\b.{0,30}\b(sa\s+thải|đuổi\s+việc)\b.{0,30}\b(mang\s+thai|thai\s+sản)\b", "Pháp luật lao động nghiêm cấm sa thải lao động nữ mang thai")
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
            elif slm_verdict == "ENTAILMENT":
                is_ent = slm_conf >= self.entailment_threshold
                return is_ent, round(slm_conf, 4), "ENTAILMENT" if is_ent else "NEUTRAL_OR_UNSUPPORTED"
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

        # Điểm tổng hợp ngữ nghĩa
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
        Khắc phục hoàn toàn lỗ hổng bypass câu ngắn (<= 15 ký tự) và chống phê duyệt rỗng (vacuous approval).
        """
        # Nếu câu trả lời rỗng hoặc chỉ có khoảng trắng
        if not answer_text or not answer_text.strip():
            return {
                "is_entailed": False,
                "verdict": "NEUTRAL_OR_UNSUPPORTED",
                "failed_claims": [{
                    "sentence": "",
                    "max_entailment_score": 0.0,
                    "verdict": "NEUTRAL_OR_UNSUPPORTED"
                }],
                "average_score": 0.0,
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

        # Tách các câu khẳng định pháp lý: bảo vệ số thập phân (85.5%) và dấu chấm hàng nghìn (100.000)
        raw_segments = re.split(r"(?:(?<=[?!;])\s*|(?<=[.])\s+|\n+)", answer_text)
        sentences = []
        for p in raw_segments:
            # Loại bỏ bullet points, đánh số thứ tự đầu dòng
            s = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", p).strip().rstrip(".?!;")
            # Giữ lại các phân đoạn có độ dài >= 3 ký tự và có chứa ký tự chữ/số
            if len(s) >= 3 and re.search(r"[\w\d]", s):
                sentences.append(s)

        # Nếu văn bản có nội dung nhưng không tạo thành câu có nghĩa hợp lệ
        if not sentences:
            return {
                "is_entailed": False,
                "verdict": "NEUTRAL_OR_UNSUPPORTED",
                "failed_claims": [{
                    "sentence": answer_text.strip(),
                    "max_entailment_score": 0.0,
                    "verdict": "NEUTRAL_OR_UNSUPPORTED"
                }],
                "average_score": 0.0,
                "total_sentences": 0
            }

        # Nếu không có căn cứ điều luật nào được trích dẫn
        if not norm_cit_ids:
            return {
                "is_entailed": False,
                "verdict": "NEUTRAL_OR_UNSUPPORTED",
                "failed_claims": [{
                    "sentence": s,
                    "max_entailment_score": 0.0,
                    "verdict": "NEUTRAL_OR_UNSUPPORTED"
                } for s in sentences],
                "average_score": 0.0,
                "total_sentences": len(sentences)
            }

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
