"""
Long-term Episodic Store: SQLite
Implements episodic policies and supported-pattern PII filtering.
Filtering alone does not establish privacy or legal compliance.
"""
import sqlite3
import json
import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def sanitize_pii(text: str) -> str:
    """
    Sanitizes personally identifiable information (PII) complying with Decree 13/2023/ND-CP & PDPL 2025:
    - Preserves 10-digit enterprise tax codes (and 13-digit branch codes) when preceded by tax code markers.
    - Redacts 12-digit Citizen Identity Card numbers (CCCD with spaces, dots, dashes)
      and 9-digit ID cards (CMND), preventing currency suffix spoofing bypasses.
    - Redacts Vietnamese mobile and landline telephone numbers (03, 05, 07, 08, 09 mobile, 02x landline, +84, (+84)).
    - Redacts standard RFC 5322 email addresses.
    Replaces all detected sensitive personal data with the standardized tag [REDACTED_PII].
    """
    if not text:
        return ""

    sanitized = text

    # 0. Preserve Enterprise Tax Codes
    tax_placeholders = {}
    tax_pattern = r"(?i)\b(?:mã\s+số\s+thuế|mst|mã\s+số\s+doanh\s+nghiệp|msdn|tax\s+code)\b[\s:._-]*([0-9]{10}(?:-[0-9]{3})?)\b"

    def _mask_tax(match: re.Match) -> str:
        key = f"__PRESERVED_TAX_CODE_{len(tax_placeholders)}__"
        full = match.group(0)
        num = match.group(1)
        tax_placeholders[key] = num
        prefix = full[:match.start(1) - match.start(0)]
        return f"{prefix}{key}"

    sanitized = re.sub(tax_pattern, _mask_tax, sanitized)

    # 0.1 Preserve legitimate currency amounts and financial figures
    # Do not preserve numbers starting with 0 (e.g., 001203456789 đồng is a CCCD bypass attempt)
    currency_placeholders = {}
    currency_pattern = (
        r"(?<!\d)(?:[1-9]\d{0,2}(?:[.,]\d{3})+|[1-9]\d+)\s*"
        r"(?i:(?:đồng|đ|vnđ|vnd|usd|eur|tỷ|tỉ|triệu))\b"
    )

    def _mask_currency(match: re.Match) -> str:
        key = f"__PRESERVED_CURRENCY_{len(currency_placeholders)}__"
        currency_placeholders[key] = match.group(0)
        return key

    sanitized = re.sub(currency_pattern, _mask_currency, sanitized)

    # 1. Email addresses (basic RFC 5322 standard)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    sanitized = re.sub(email_pattern, '[REDACTED_PII]', sanitized)

    # 2. Inspect explicit CCCD/CMND identity labels (regardless of separators and currency suffixes)
    explicit_id_pattern = r'(?i)\b(?:cccd|căn\s+cước(?:\s+công\s+dân)?|cmnd|chứng\s+minh\s+nhân\s+dân|số\s+định\s+danh)[\s:._-]*([0-9\s.\-]{9,22})\b'
    def _redact_explicit_id(match: re.Match) -> str:
        digits = re.sub(r'\D', '', match.group(1))
        if len(digits) in (9, 12):
            prefix = match.group(0)[:match.start(1) - match.start(0)]
            return f"{prefix}[REDACTED_PII]"
        return match.group(0)
    sanitized = re.sub(explicit_id_pattern, _redact_explicit_id, sanitized)

    # 3. 12-digit Citizen Identity Card (CCCD) numbers with flexible separators
    def _redact_12_digits(match: re.Match) -> str:
        matched_str = match.group(0)
        digits = re.sub(r'\D', '', matched_str)
        if len(digits) == 12:
            return '[REDACTED_PII]'
        return matched_str

    sanitized = re.sub(r'(?<![\d])(?:\d[\s.\-]?){11}\d(?![\d])', _redact_12_digits, sanitized)

    # 4. 9-digit National ID Card (CMND) numbers
    def _redact_9_digits(match: re.Match) -> str:
        matched_str = match.group(0)
        digits = re.sub(r'\D', '', matched_str)
        if len(digits) == 9:
            return '[REDACTED_PII]'
        return matched_str

    sanitized = re.sub(r'(?<![\d])(?:\d[\s.\-]?){8}\d(?![\d])', _redact_9_digits, sanitized)

    # 5. Vietnamese mobile and landline telephone numbers (prefixes 03, 05, 07, 08, 09 and landline 02x)
    phone_pattern = (
        r'(?<![\d])(?:'
        r'(?:(?:\+84|84|0|\(\+84\))[\s.\-]*(?:\(?0?(?:3|5|7|8|9)\)?))[\s.\-]*(?:[\s.\-]?\d){7,8}'
        r'|'
        r'(?:(?:\+84|84|0)[\s.\-]*2\d{1,2})[\s.\-]*(?:[\s.\-]?\d){7,8}'
        r'|'
        r'(?:\(0[235789]\d{1,2}\))[\s.\-]*(?:[\s.\-]?\d){6,8}'
        r')(?![\s.\-]?\d)'
    )
    sanitized = re.sub(phone_pattern, '[REDACTED_PII]', sanitized)

    # 6. Restore preserved currency and enterprise tax codes
    for key, original_curr in currency_placeholders.items():
        sanitized = sanitized.replace(key, original_curr)
    for key, original_tax in tax_placeholders.items():
        sanitized = sanitized.replace(key, original_tax)

    return sanitized


class SQLiteEpisodicStore:
    def __init__(self, db_path: str = "data/db/luatcheck_memory.db", index_version: str = "v2026.1"):
        self.db_path = db_path
        self.index_version = index_version
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self._init_db()

    @staticmethod
    def sanitize_pii(text: str) -> str:
        return sanitize_pii(text)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    case_id TEXT PRIMARY KEY,
                    normalized_query TEXT NOT NULL,
                    article_ids TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    index_version TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            columns = {row[1] for row in cursor.execute("PRAGMA table_info(episodic_memory)")}
            if "native_evidence_json" not in columns:
                cursor.execute("ALTER TABLE episodic_memory ADD COLUMN native_evidence_json TEXT NOT NULL DEFAULT '[]'")
            conn.commit()

    @staticmethod
    def has_native_evidence(case: Dict[str, Any]) -> bool:
        evidence = case.get("native_evidence", [])
        return bool(isinstance(evidence, list) and evidence and all(
            isinstance(call, dict) and call.get("backend") in {"ollama", "llamacpp"}
            and call.get("outcome") == "success" and bool(call.get("requested_model"))
            and re.fullmatch(r"[a-f0-9]{64}", str(call.get("request_sha256", "")))
            for call in evidence) and evidence[-1].get("action") == "answer")

    def write_if_verified(
        self,
        case_id: str,
        query: str,
        answer: str,
        citations: List[Dict[str, Any]],
        is_l1_verified: bool,
        native_evidence: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        WRITE POLICY:
        - Only writes when the case has passed 100% of L1 Verification checks.
        - Strictly drops rejected or unverified inquiries/responses.
        - Sanitizes all PII (CCCD, phone, email) in query, answer, and citations_json.
        """
        if not is_l1_verified:
            return False

        # Sanitize PII adhering to PDPL 2025
        clean_query = sanitize_pii(query).strip().lower()
        clean_answer = sanitize_pii(answer)

        # Extract and sanitize citations structure
        citations_sanitized = []
        if isinstance(citations, list):
            article_ids = ",".join([
                c.get("article_id", "") if isinstance(c, dict) else getattr(c, "article_id", str(c))
                for c in citations
            ])
            for c in citations:
                c_dict = c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else (c.dict() if hasattr(c, "dict") else {"article_id": str(c)}))
                clean_c = {}
                for k, v in c_dict.items():
                    if isinstance(v, str):
                        clean_c[k] = sanitize_pii(v)
                    else:
                        clean_c[k] = v
                citations_sanitized.append(clean_c)
        else:
            article_ids = ""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO episodic_memory 
                (case_id, normalized_query, article_ids, answer, citations_json, index_version, created_at, native_evidence_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_id,
                clean_query,
                article_ids,
                clean_answer,
                json.dumps(citations_sanitized, ensure_ascii=False),
                self.index_version,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(native_evidence or [], ensure_ascii=False)
            ))
            conn.commit()
        return True

    def retrieve_similar_case(
        self,
        query: str,
        index_version: Optional[str] = None,
        threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """
        RETRIEVAL POLICY:
        - Reuses past advisory cases only if index_version strictly matches.
        - Sanitizes PII and normalizes punctuation before computing hybrid TF-IDF cosine + Jaccard similarity.
        - Returns parsed article_ids as List[str].
        - Only accepts cases with similarity >= threshold.
        """
        target_version = index_version or self.index_version
        clean_q = sanitize_pii(query).strip().lower()
        q_words = set(re.findall(r'\w+', clean_q))

        if not q_words:
            return None

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT case_id, normalized_query, article_ids, answer, citations_json, index_version, created_at, native_evidence_json
                FROM episodic_memory
                WHERE index_version = ?
            """, (target_version,))
            rows = cursor.fetchall()

            if not rows:
                return None

            stored_queries = [row["normalized_query"] for row in rows]
            try:
                vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
                mat = vec.fit_transform([clean_q] + stored_queries)
                cosine_scores = cosine_similarity(mat[0:1], mat[1:])[0]
            except Exception:
                cosine_scores = [0.0] * len(rows)

            best_match = None
            best_score = 0.0

            for idx, row in enumerate(rows):
                stored_words = set(re.findall(r'\w+', row["normalized_query"]))
                if not stored_words:
                    continue
                intersection = len(q_words & stored_words)
                union = len(q_words | stored_words)
                jaccard = intersection / union if union > 0 else 0.0
                tfidf_cos = float(cosine_scores[idx]) if idx < len(cosine_scores) else 0.0
                hybrid_sim = max(jaccard, 0.5 * jaccard + 0.5 * tfidf_cos)

                if hybrid_sim >= threshold and hybrid_sim > best_score:
                    best_score = hybrid_sim
                    best_match = dict(row)

            if best_match:
                # Parse article_ids list
                raw_aids = best_match.get("article_ids", "")
                if isinstance(raw_aids, str):
                    parsed_aids = [aid.strip() for aid in raw_aids.split(",") if aid.strip()]
                elif isinstance(raw_aids, (list, tuple, set)):
                    parsed_aids = [str(aid).strip() for aid in raw_aids if str(aid).strip()]
                else:
                    parsed_aids = []

                best_match["article_ids"] = parsed_aids
                try:
                    best_match["citations"] = json.loads(best_match["citations_json"])
                except (ValueError, TypeError):
                    return None
                try:
                    best_match["native_evidence"] = json.loads(best_match["native_evidence_json"])
                except (ValueError, TypeError):
                    best_match["native_evidence"] = []
                best_match["similarity_score"] = round(best_score, 4)
                return best_match

        return None
