"""
Semantic NLI Entailment Verifier (Natural Language Inference Layer).

Checks the directional semantic entailment relation between generated claim sentences
and their cited knowledge provisions.
Implements a hierarchical dual-engine architecture:
1. Local SLM NLI Caller (Qwen2.5-3B via Ollama).
2. Fast Offline Semantic Comparator:
   - Robust sentence segmentation and anti-vacuous approval
   - Dynamic numerical duration & quantifier clash detection
   - Negation / polarity contradiction detection
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


class SemanticNLIVerifier:
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
            self._normalize_id(str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or "")): (
                f"{doc.get('title', '')}. {doc.get('content', '')}" if doc.get("title") else doc.get("content", "")
            )
            for doc in legal_corpus
        }
        self.entailment_threshold = entailment_threshold
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.use_slm = use_slm
        self.slm_timeout = slm_timeout

        # Fit TF-IDF vectorizer over the statutory corpus text
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        all_texts = list(self.corpus_lookup.values())
        if all_texts:
            self.vectorizer.fit(all_texts)

    def _normalize_id(self, article_id: str) -> str:
        """
        Normalize article identifier across variations:
        'Dieu_25', 'dieu_25', 'Điều 25', 'điều_25', 'Điều_25' (NFC/NFD).
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
        Extract temporal durations and normalize relatively to days:
        Returns list of tuples: (days: float, unit_type: str, raw_expression: str)
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
        Extract percentage values from text.
        """
        matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*%", text)
        return [float(m.replace(",", ".")) for m in matches]

    def _call_slm_nli(self, premise: str, hypothesis: str) -> Optional[Tuple[str, float]]:
        """
        Engine 1: Local SLM (Qwen2.5-3B) NLI Caller with default 10.0s timeout.
        Returns (verdict, confidence) or None if SLM is unreachable (offline fallback).
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
            # 1. Support llama.cpp / OpenAI-compatible endpoint (/v1/chat/completions)
            if self.ollama_url and ("/v1" in self.ollama_url or ":8080" in self.ollama_url):
                url = self.ollama_url.rstrip("/")
                endpoint = f"{url}/chat/completions" if not url.endswith("/chat/completions") else url
                openai_payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                }
                resp = requests.post(endpoint, json=openai_payload, timeout=self.slm_timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                    raw_json = json.loads(raw_content)
                    verdict = raw_json.get("verdict", "").strip().upper()
                    confidence = float(raw_json.get("confidence", 0.8))
                    if verdict in ["ENTAILMENT", "CONTRADICTION", "NEUTRAL"]:
                        return verdict, confidence
            else:
                # 2. Support native Ollama endpoint (/api/chat)
                resp = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=self.slm_timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_json = json.loads(data.get("message", {}).get("content", "{}"))
                    verdict = raw_json.get("verdict", "").strip().upper()
                    confidence = float(raw_json.get("confidence", 0.8))
                    if verdict in ["ENTAILMENT", "CONTRADICTION", "NEUTRAL"]:
                        return verdict, confidence
        except Exception:
            # Graceful fallback to Fast Offline Semantic Comparator when server is offline or times out
            pass

        return None

    def _extract_clause_bounds(self, premise: str) -> List[Dict[str, Any]]:
        """
        Dynamically extract quantitative bounds (MAX, MIN, PROHIBITED_UNDER, ONCE_ONLY, PCT_MIN, PCT_MAX)
        directly from the clauses of any statutory/SOP premise text without hardcoding article IDs.
        """
        clauses = [c.strip() for c in re.split(r"[\n;]+", premise) if c.strip()]
        bounds: List[Dict[str, Any]] = []

        unit_pat = r"(ngày\s+làm\s+việc|ngày|tháng|năm|tuần|giờ|phút)"

        def _to_days(val: float, unit: str) -> float:
            u = unit.strip().lower()
            if "ngày" in u:
                return val
            if "tháng" in u:
                return val * 30.0
            if "năm" in u:
                return val * 365.0
            if "tuần" in u:
                return val * 7.0
            if "giờ" in u:
                return val / 24.0
            if "phút" in u:
                return val / 1440.0
            return val

        for clause in clauses:
            c_low = clause.lower()

            # 1. Single-occurrence constraint: "chỉ được <action> một lần"
            m_once = re.search(r"chỉ\s+được\s+([^,.;\n]{3,30}?)\s+(?:một|01|1)\s+lần", c_low)
            if m_once:
                bounds.append({
                    "type": "ONCE_ONLY",
                    "topic": m_once.group(1).strip(),
                    "clause": c_low
                })

            # 2. Scope exclusion under duration threshold: "không áp dụng <topic> đối với ... dưới X <unit>"
            m_prohib = re.search(
                rf"(?:không\s+áp\s+dụng|không\s+được(?:\s+áp\s+dụng)?|nghiêm\s+cấm)\s+([^,.;\n]{{3,30}}?)\s+đối\s+với\s+[^.;\n]*?\b(?:dưới|ít\s+hơn)\s+(\d+(?:[.,]\d+)?)\s*{unit_pat}",
                c_low
            )
            if m_prohib:
                val = float(m_prohib.group(2).replace(",", "."))
                bounds.append({
                    "type": "PROHIBITED_UNDER",
                    "topic": m_prohib.group(1).strip(),
                    "days": _to_days(val, m_prohib.group(3)),
                    "raw": f"{m_prohib.group(2)} {m_prohib.group(3)}",
                    "clause": c_low
                })

            # 3. Percentage lower bounds: "ít nhất (phải bằng)? X%" or "tối thiểu X%"
            for m_pmin in re.finditer(r"(?:ít\s+nhất(?:\s+phải\s+bằng)?|tối\s+thiểu)\s+(\d+(?:[.,]\d+)?)\s*%", c_low):
                bounds.append({
                    "type": "PCT_MIN",
                    "pct": float(m_pmin.group(1).replace(",", ".")),
                    "clause": c_low
                })

            # 4. Percentage upper bounds: "không quá X%" or "tối đa X%"
            for m_pmax in re.finditer(r"(?:không\s+quá|tối\s+đa)\s+(\d+(?:[.,]\d+)?)\s*%", c_low):
                bounds.append({
                    "type": "PCT_MAX",
                    "pct": float(m_pmax.group(1).replace(",", ".")),
                    "clause": c_low
                })

            # 5. Duration upper bounds: "không quá X <unit>" or "tối đa X <unit>"
            for m_max in re.finditer(rf"(?:không\s+quá|tối\s+đa)\s+(\d+(?:[.,]\d+)?)\s*{unit_pat}", c_low):
                val = float(m_max.group(1).replace(",", "."))
                bounds.append({
                    "type": "DURATION_MAX",
                    "days": _to_days(val, m_max.group(2)),
                    "raw": f"{m_max.group(1)} {m_max.group(2)}",
                    "clause": c_low
                })

            # 6. Duration lower bounds: "ít nhất X <unit>" or "tối thiểu X <unit>"
            for m_min in re.finditer(rf"(?:ít\s+nhất|tối\s+thiểu)\s+(\d+(?:[.,]\d+)?)\s*{unit_pat}", c_low):
                val = float(m_min.group(1).replace(",", "."))
                bounds.append({
                    "type": "DURATION_MIN",
                    "days": _to_days(val, m_min.group(2)),
                    "raw": f"{m_min.group(1)} {m_min.group(2)}",
                    "clause": c_low
                })

        return bounds

    @staticmethod
    def _match_clause_qualifier(claim_lower: str, clause_lower: str) -> Tuple[bool, int]:
        """
        Determines whether a premise clause's qualification/condition matches the claim's subject,
        returning (matched: bool, priority: int) based on lexical and domain qualification alignment.
        """
        is_manager_claim = any(w in claim_lower for w in [
            "công việc của người quản lý", "chức danh quản lý", "vị trí quản lý",
            "người quản lý doanh nghiệp", "người quản lý", "vị trí giám đốc", "làm giám đốc", "giám đốc điều hành"
        ])
        is_vocational_claim = any(w in claim_lower for w in [
            "công nhân kỹ thuật", "trung cấp", "sơ cấp", "công nhân", "nghiệp vụ"
        ])
        is_college_claim = any(w in claim_lower for w in [
            "đại học", "cao đẳng", "chuyên môn", "kỹ thuật", "văn phòng", "nhân viên", "cử nhân", "kỹ sư", "chuyên viên"
        ])
        is_simple_claim = any(w in claim_lower for w in [
            "công việc khác", "lao động phổ thông", "giản đơn"
        ])

        # Qualification tier matching against premise clause text
        if "quản lý doanh nghiệp" in clause_lower:
            return (is_manager_claim, 4 if is_manager_claim else 0)
        if "trung cấp" in clause_lower or "công nhân kỹ thuật" in clause_lower:
            matched = is_vocational_claim and not is_manager_claim
            return (matched, 3 if matched else 0)
        if "cao đẳng trở lên" in clause_lower:
            matched = is_college_claim and not is_vocational_claim and not is_manager_claim
            return (matched, 2 if matched else 0)
        if "công việc khác" in clause_lower:
            matched = is_simple_claim and not is_manager_claim
            return (matched, 3 if matched else 0)

        # Contract term type matching against premise clause text
        if "không xác định thời hạn" in clause_lower:
            matched = "không xác định thời hạn" in claim_lower
            return (matched, 3 if matched else 0)
        if "từ 12 tháng đến 36 tháng" in clause_lower:
            matched = (
                ("từ 12 tháng đến 36 tháng" in claim_lower or "xác định thời hạn" in claim_lower)
                and "không xác định" not in claim_lower
                and "dưới 12 tháng" not in claim_lower
            )
            return (matched, 2 if matched else 0)
        if "xác định thời hạn" in clause_lower and "không xác định" not in clause_lower:
            matched = "xác định thời hạn" in claim_lower and "không xác định" not in claim_lower
            return (matched, 2 if matched else 0)

        # General lexical overlap fallback for single-clause or arbitrary domain bounds
        clause_tokens = set(re.findall(r"\w+", clause_lower))
        claim_tokens = set(re.findall(r"\w+", claim_lower))
        overlap = len(clause_tokens & claim_tokens)
        return (overlap >= 3, 1 if overlap >= 3 else 0)

    def _check_quantifier_and_polarity_contradiction(
        self,
        claim: str,
        premise: str,
        norm_id: str
    ) -> Optional[str]:
        """
        Check for quantifier clash, numerical boundaries, and polarity contradiction
        dynamically against the extracted constraints of `premise` (no hardcoded article IDs).
        """
        claim_lower = claim.lower()
        premise_lower = premise.lower()
        durations = self._extract_durations(claim)
        percentages = self._extract_percentages(claim)
        bounds = self._extract_clause_bounds(premise)

        # 1. Check ONCE_ONLY constraints extracted from premise
        for b in bounds:
            if b["type"] == "ONCE_ONLY":
                topic = b["topic"]
                if topic in claim_lower and re.search(
                    rf"\b{re.escape(topic)}\b.{{0,25}}\b(nhiều\s+lần|2\s+lần|hai\s+lần|lần\s+hai|từ\s+2\s+lần)\b",
                    claim_lower
                ):
                    return f"CONTRADICTION: Văn bản gốc quy định chỉ được {topic} một lần."

        # 2. Check PROHIBITED_UNDER scope exclusions extracted from premise
        for b in bounds:
            if b["type"] == "PROHIBITED_UNDER":
                topic = b["topic"]
                thresh_days = b["days"]
                if topic in claim_lower:
                    has_under_phrase = any(
                        w in claim_lower
                        for w in ["dưới 01 tháng", "dưới 1 tháng", "dưới 30 ngày", "dưới một tháng"]
                    )
                    has_short_contract = False
                    short_dur_desc = ""
                    for days, unit_type, raw_str in durations:
                        if 0 < days < thresh_days:
                            pat1 = rf"\b(hợp\s+đồng|hđlđ|hđ|giao\s+kết)\b(?:(?!\b{re.escape(topic)}\b).){{0,25}}\b{re.escape(raw_str)}"
                            pat2 = rf"{re.escape(raw_str)}\s+(?:hợp\s+đồng|hđlđ|hđ)"
                            if re.search(pat1, claim_lower) or re.search(pat2, claim_lower):
                                has_short_contract = True
                                short_dur_desc = raw_str
                                break

                    if has_under_phrase or has_short_contract:
                        neg_before = rf"\b(không\s+áp\s+dụng|không\s+được|nghiêm\s+cấm|cấm|không\s+thể)\b.{{0,30}}\b{re.escape(topic)}\b"
                        neg_after = rf"\b{re.escape(topic)}\b.{{0,30}}\b(không\s+áp\s+dụng|không\s+được|bị\s+cấm)\b"
                        if not re.search(neg_before, claim_lower) and not re.search(neg_after, claim_lower):
                            desc_str = f" ({short_dur_desc})" if short_dur_desc else ""
                            return f"CONTRADICTION: Văn bản gốc quy định không áp dụng {topic} đối với thời hạn dưới {b['raw']}{desc_str}."

        # 3. Check PCT_MIN and PCT_MAX bounds extracted from premise
        for b in bounds:
            if b["type"] == "PCT_MIN":
                min_pct = b["pct"]
                for pct in percentages:
                    if pct < min_pct:
                        return f"CONTRADICTION: Văn bản gốc quy định mức tối thiểu {min_pct}%, không thể là {pct}%."
                if any(w in claim_lower for w in [
                    "0 đồng", "không lương", "miễn phí", "không được trả lương",
                    "không trả lương", "không có lương", "không cần trả lương", "làm việc không công"
                ]):
                    return f"CONTRADICTION: Văn bản gốc quy định mức hưởng tối thiểu {min_pct}%, không cho phép không trả lương."
            elif b["type"] == "PCT_MAX":
                max_pct = b["pct"]
                for pct in percentages:
                    if pct > max_pct:
                        return f"CONTRADICTION: Văn bản gốc quy định mức tối đa {max_pct}%, không thể là {pct}%."

        # 4. Check DURATION_MAX bounds extracted from premise
        max_bounds = [b for b in bounds if b["type"] == "DURATION_MAX"]
        if max_bounds and durations:
            # Check if premise is about probation ("thử việc") and ensure claim also discusses the same topic
            premise_is_probation = "thời gian thử việc" in premise_lower and len(max_bounds) > 1
            if not premise_is_probation or "thử việc" in claim_lower:
                global_max_days = max(b["days"] for b in max_bounds)
                # Find best-matching clause bound for the claim's subject
                matched_candidates = []
                for b in max_bounds:
                    is_match, prio = self._match_clause_qualifier(claim_lower, b["clause"])
                    if is_match:
                        matched_candidates.append((prio, b["days"], b))

                for days, unit_type, raw_str in durations:
                    if days <= 0:
                        return f"CONTRADICTION: Thời hạn {raw_str} không hợp lệ so với quy định."
                    if days > global_max_days:
                        return f"CONTRADICTION: Thời hạn {raw_str} vượt quá mức tối đa tuyệt đối ({global_max_days:.0f} ngày) trong điều luật."
                    if matched_candidates:
                        # Sort by highest specificity priority, then tightest bound
                        matched_candidates.sort(key=lambda x: (-x[0], x[1]))
                        best_bound = matched_candidates[0][2]
                        if days > best_bound["days"]:
                            return f"CONTRADICTION: Thời hạn {raw_str} vượt quá giới hạn không quá {best_bound['raw']} của khoản tương ứng."
                    elif premise_is_probation:
                        # Non-managerial default probation cap (second highest cap in probation schedule, e.g. 60 days)
                        non_mgr_bounds = [b["days"] for b in max_bounds if "quản lý doanh nghiệp" not in b["clause"]]
                        if non_mgr_bounds and days > max(non_mgr_bounds):
                            return f"CONTRADICTION: Thời hạn {raw_str} vượt quá giới hạn thử việc thông thường ({max(non_mgr_bounds):.0f} ngày)."

        # 5. Check DURATION_MIN bounds extracted from premise
        min_bounds = [b for b in bounds if b["type"] == "DURATION_MIN"]
        if min_bounds and durations:
            has_no_notice_exception = any(w in claim_lower for w in ["không cần báo trước", "không phải báo trước", "khoản 2"])
            if not has_no_notice_exception and "thử việc" not in claim_lower:
                for b in min_bounds:
                    is_match, prio = self._match_clause_qualifier(claim_lower, b["clause"])
                    if is_match and prio >= 2:
                        for days, unit_type, raw_str in durations:
                            if days < b["days"]:
                                return f"CONTRADICTION: Thời hạn {raw_str} thấp hơn mức tối thiểu ít nhất {b['raw']} trong điều luật."

        # 6. Statutory prohibitions and fundamental rights polarity inversion
        illegal_patterns = [
            (r"\b(được|có\s+quyền|cho\s+phép)\b.{0,30}\b(phạt\s+tiền|cắt\s+lương|trừ\s+lương|khấu\s+trừ\s+lương\s+thay\s+kỷ\s+luật)\b", "Pháp luật lao động nghiêm cấm người sử dụng lao động phạt tiền hoặc cắt lương người lao động thay cho việc xử lý kỷ luật"),
            (r"\b(được|có\s+quyền|cho\s+phép|yêu\s+cầu)\b.{0,30}\b(giữ|thu\s+giữ|tạm\s+giữ)\b.{0,30}\b(bằng\s+cấp|văn\s+bằng|chứng\s+chỉ|giấy\s+tờ\s+tùy\s+thân|cccd|cmnd|hộ\s+chiếu)\b", "Bộ luật Lao động nghiêm cấm giữ bản chính giấy tờ tùy thân, văn bằng, chứng chỉ của người lao động"),
            (r"\b(đuổi\s+việc|sa\s+thải|xử\s+lý\s+kỷ\s+luật|chấm\s+dứt)\b.{0,30}\b(mang\s+thai|thai\s+sản|nuôi\s+con\s+(?:dưới\s+12\s+tháng|nhỏ))\b", "Nghiêm cấm sa thải hoặc xử lý kỷ luật lao động đối với lao động nữ mang thai, nghỉ thai sản, nuôi con dưới 12 tháng tuổi"),
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
        Evaluate directional semantic entailment between a claim sentence and cited article.
        Returns: (is_entailed: bool, score: float, verdict: str)
        """
        if not claim_sentence or not claim_sentence.strip():
            return False, 0.0, "NEUTRAL_OR_UNSUPPORTED: Claim sentence is empty."

        norm_id = self._normalize_id(cited_article_id)
        premise_text = self.corpus_lookup.get(norm_id)
        if not premise_text:
            return False, 0.0, f"Mã điều luật '{cited_article_id}' không tồn tại để kiểm tra ngữ nghĩa."

        # 1. Contradiction check: Quantifiers, boundary conditions, and prohibitions
        contradiction_reason = self._check_quantifier_and_polarity_contradiction(
            claim_sentence, premise_text, norm_id
        )
        if contradiction_reason:
            return False, 0.15, "CONTRADICTION"

        # 2. Engine 1: Local SLM NLI evaluation if available
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

        # Composite semantic score combining TF-IDF similarity and asymmetric keyword coverage
        if not claim_words or asymmetric_recall == 0.0:
            score = 0.0
        else:
            score = 0.6 * tfidf_score + 0.4 * asymmetric_recall

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
        Verify directional semantic entailment for all clauses in the answer text against cited articles.
        Guarantees protection against short clause bypass (<= 15 chars) and vacuous approvals.
        """
        # If answer text is empty or whitespace-only
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

        # Normalize citation_ids list
        norm_cit_ids = []
        for c in citation_ids:
            if isinstance(c, str):
                norm_cit_ids.append(c)
            elif hasattr(c, "article_id"):
                norm_cit_ids.append(c.article_id)
            elif isinstance(c, dict) and "article_id" in c:
                norm_cit_ids.append(c["article_id"])

        # Segment legal claim sentences: protect decimals (85.5%), thousands separators (100.000), and clause numbers (1. )
        raw_segments = re.split(r"(?:(?<=[?!;])\s*|(?<!\b\d[.])(?<=[.])\s+|\n+)", answer_text)
        sentences = []
        for p in raw_segments:
            # Strip bullet points and leading enumeration markers
            s = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", p).strip().rstrip(".?!;")
            # Retain clauses with length >= 3 containing alphanumeric characters
            if len(s) >= 3 and re.search(r"[\w\d]", s):
                sentences.append(s)

        # If text has content but produces no valid sentences
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

        # If no statutory citations were provided
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

            # A sentence is considered valid if at least one cited article entails it
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


# Compatibility aliases
SemanticEntailmentVerifier = SemanticNLIVerifier
L2SemanticEntailmentVerifier = SemanticNLIVerifier


