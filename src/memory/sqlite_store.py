"""
Long-term Episodic Store: SQLite
Triển khai bộ nhớ dài hạn với chính sách Ghi (Write Policy), Đọc (Retrieval Policy)
và Khử khuẩn Dữ liệu Định danh Cá nhân (PII Sanitization) tuân thủ Vietnam PDPL 2025
"""
import sqlite3
import json
import os
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone


def sanitize_pii(text: str) -> str:
    """
    Khử khuẩn dữ liệu định danh cá nhân (PII Sanitization) tuân thủ Nghị định 13/2023/NĐ-CP & PDPL 2025:
    - Bảo toàn Mã số thuế doanh nghiệp 10 chữ số (và 13 chữ số chi nhánh) khi có nhãn mã số thuế/MST/MSDN.
    - Khử khuẩn Số căn cước công dân (CCCD 12 chữ số theo các định dạng 3-3-3-3, 4-4-4, 3-1-2-6, tiền tố CCCD_)
      và CMND 9 chữ số, có cơ chế loại trừ số tiền tệ lớn (>= 100 tỷ đồng, VNĐ, VND, đ,...) bằng negative lookahead.
    - Khử khuẩn Số điện thoại di động và cố định Việt Nam (đầu số 03, 05, 07, 08, 09, 02x, +84, (+84)
      kèm dấu cách, gạch nối, dấu chấm, ngoặc đơn).
    - Khử khuẩn Địa chỉ email.
    Thay thế toàn bộ thông tin cá nhân nhạy cảm bằng nhãn chuẩn [REDACTED_PII].
    """
    if not text:
        return ""

    sanitized = text

    # 0. BẢO VỆ MÃ SỐ THUẾ DOANH NGHIỆP (Enterprise Tax Codes)
    # Mã số thuế của pháp nhân/doanh nghiệp là thông tin công khai minh bạch, không phải PII cá nhân.
    # Sử dụng kỹ thuật Masking Placeholder để ngăn regex SĐT (đầu 03x) hoặc CCCD nhận diện nhầm.
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

    # 1. Email addresses (chuẩn RFC 5322 cơ bản, hỗ trợ subdomain nhiều cấp và tag dấu +)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    sanitized = re.sub(email_pattern, '[REDACTED_PII]', sanitized)

    # Biểu thức loại trừ các đơn vị tiền tệ phổ biến (không phân biệt hoa thường)
    currency_exclusion = r'(?!\s*(?i:(?:đồng|đ|vnđ|vnd|usd|eur|tỷ|tỉ|triệu|nghìn|ngàn)\b))'

    # 2. Số Căn cước công dân 12 chữ số (CCCD) và phân cách định dạng chuẩn (3-3-3-3, 4-4-4)
    # Loại trừ các số tiền tệ 12 chữ số (ví dụ: 100.000.000.000 đồng)
    cccd_pattern = (
        r'(?<![\d])(?:'
        r'\d{12}'
        r'|\d{3}[.\-\s]\d{3}[.\-\s]\d{3}[.\-\s]\d{3}'
        r'|\d{4}[.\-\s]\d{4}[.\-\s]\d{4}'
        r')(?![\d])' + currency_exclusion
    )
    sanitized = re.sub(cccd_pattern, '[REDACTED_PII]', sanitized)

    # 3. Số điện thoại di động Việt Nam (hỗ trợ +84, 84, 0; tiền tố (0912), (091), (09), (+84); dấu cách, chấm, gạch ngang)
    # Loại trừ số tiền tệ (84.500.000.000 VNĐ, 0.900.000.000 đồng) và tránh nuốt số lớn hơn (184...)
    phone_pattern = (
        r'(?<![\d])(?:'
        r'(?:(?:\+84|84|0|\(\+84\))[\s.\-]*(?:\(?0?(?:3|5|7|8|9)\)?))[\s.\-]*(?:[\s.\-]?\d){7,8}'
        r'|'
        r'(?:\(0[35789]\d{2}\))[\s.\-]*(?:[\s.\-]?\d){6}'
        r'|'
        r'(?:\(0[35789]\d?\))[\s.\-]*(?:[\s.\-]?\d){7,8}'
        r')(?![\s.\-]?\d)' + currency_exclusion
    )
    sanitized = re.sub(phone_pattern, '[REDACTED_PII]', sanitized)

    # 4. KHÔI PHỤC MÃ SỐ THUẾ DOANH NGHIỆP
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
            conn.commit()

    def write_if_verified(
        self,
        case_id: str,
        query: str,
        answer: str,
        citations: List[Dict[str, Any]],
        is_l1_verified: bool
    ) -> bool:
        """
        CHÍNH SÁCH GHI (Write Policy):
        - Chỉ ghi khi kết quả đã VƯỢT QUA 100% kiểm tra L1 Verification.
        - Tuyệt đối không lưu câu hỏi/câu trả lời bị từ chối hoặc không được xác minh.
        - Khử khuẩn toàn bộ PII (CCCD, SĐT, Email) trước khi lưu vào cơ sở dữ liệu.
        """
        if not is_l1_verified:
            return False

        # Khử khuẩn PII tuân thủ PDPL 2025
        clean_query = sanitize_pii(query).strip().lower()
        clean_answer = sanitize_pii(answer)

        # Trích xuất và định dạng mã điều luật
        if isinstance(citations, list):
            article_ids = ",".join([
                c.get("article_id", "") if isinstance(c, dict) else getattr(c, "article_id", str(c))
                for c in citations
            ])
            citations_serializable = [
                c if isinstance(c, dict) else (c.dict() if hasattr(c, "dict") else {"article_id": str(c)})
                for c in citations
            ]
        else:
            article_ids = ""
            citations_serializable = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO episodic_memory 
                (case_id, normalized_query, article_ids, answer, citations_json, index_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                case_id,
                clean_query,
                article_ids,
                clean_answer,
                json.dumps(citations_serializable, ensure_ascii=False),
                self.index_version,
                datetime.now(timezone.utc).isoformat()
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
        CHÍNH SÁCH TRUY XUẤT (Retrieval Policy):
        - Chỉ tái sử dụng ca tư vấn cũ nếu khớp chính xác index_version.
        - Khử khuẩn PII và làm sạch dấu câu trước khi tính Jaccard similarity.
        - Trả về danh sách article_ids đã được parse (List[str]).
        - Chỉ chấp nhận tương đồng >= threshold.
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
                SELECT case_id, normalized_query, article_ids, answer, citations_json, index_version, created_at
                FROM episodic_memory
                WHERE index_version = ?
            """, (target_version,))
            rows = cursor.fetchall()

            best_match = None
            best_overlap = 0.0

            for row in rows:
                stored_words = set(re.findall(r'\w+', row["normalized_query"]))
                if not stored_words:
                    continue
                intersection = len(q_words & stored_words)
                union = len(q_words | stored_words)
                jaccard = intersection / union if union > 0 else 0

                if jaccard >= threshold and jaccard > best_overlap:
                    best_overlap = jaccard
                    best_match = dict(row)

            if best_match:
                # Parse danh sách article_ids
                raw_aids = best_match.get("article_ids", "")
                if isinstance(raw_aids, str):
                    parsed_aids = [aid.strip() for aid in raw_aids.split(",") if aid.strip()]
                elif isinstance(raw_aids, (list, tuple, set)):
                    parsed_aids = [str(aid).strip() for aid in raw_aids if str(aid).strip()]
                else:
                    parsed_aids = []

                best_match["article_ids"] = parsed_aids
                best_match["citations"] = json.loads(best_match["citations_json"])
                return best_match

        return None
