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
    Khử khuẩn dữ liệu cá nhân (PII Sanitization) tuân thủ Nghị định 13/2023/NĐ-CP & PDPL 2025:
    - Số căn cước công dân (CCCD 12 chữ số) và định dạng có dấu cách/dấu gạch
    - Số điện thoại di động Việt Nam (các đầu số 03, 05, 07, 08, 09 hoặc +84)
    - Địa chỉ email
    Thay thế toàn bộ bằng nhãn chuẩn [REDACTED_PII].
    """
    if not text:
        return ""

    sanitized = text

    # 1. Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    sanitized = re.sub(email_pattern, '[REDACTED_PII]', sanitized)

    # 2. Số điện thoại di động Việt Nam (+84 hoặc 0, theo sau bởi 3/5/7/8/9 và 8 chữ số, hỗ trợ dấu phân cách)
    phone_pattern = r'(?:\+84|84|0)(?:3|5|7|8|9)(?:[.\-\s]?\d){8}\b'
    sanitized = re.sub(phone_pattern, '[REDACTED_PII]', sanitized)

    # 3. Số Căn cước công dân 12 chữ số (CCCD) và phân cách định dạng chuẩn
    cccd_pattern = r'\b\d{12}\b|\b\d{3}[.\-\s]\d{3}[.\-\s]\d{3}[.\-\s]\d{3}\b'
    sanitized = re.sub(cccd_pattern, '[REDACTED_PII]', sanitized)

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
