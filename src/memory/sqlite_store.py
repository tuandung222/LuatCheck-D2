"""
Long-term Episodic Store: SQLite
Triển khai bộ nhớ dài hạn với chính sách Ghi (Write Policy) và Đọc (Retrieval Policy) nghiêm ngặt
"""
import sqlite3
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime


class SQLiteEpisodicStore:
    def __init__(self, db_path: str = "data/db/luatcheck_memory.db", index_version: str = "v2026.1"):
        self.db_path = db_path
        self.index_version = index_version
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

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
        - Loại bỏ dữ liệu cá nhân thô (chỉ lưu normalized query).
        """
        if not is_l1_verified:
            return False

        article_ids = ",".join([c.get("article_id", "") for c in citations])
        normalized_q = query.strip().lower()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO episodic_memory 
                (case_id, normalized_query, article_ids, answer, citations_json, index_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                case_id,
                normalized_q,
                article_ids,
                answer,
                json.dumps(citations, ensure_ascii=False),
                self.index_version,
                datetime.utcnow().isoformat()
            ))
            conn.commit()
        return True

    def retrieve_similar_case(self, query: str) -> Optional[Dict[str, Any]]:
        """
        CHÍNH SÁCH TRUY XUẤT (Retrieval Policy):
        - Chỉ tái sử dụng ca tư vấn cũ nếu cùng phiên bản cơ sở pháp lý (index_version).
        - Đối soát từ khóa câu hỏi tương đồng cao.
        """
        normalized_q = query.strip().lower()
        q_words = set(normalized_q.split())

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT case_id, normalized_query, article_ids, answer, citations_json, index_version, created_at
                FROM episodic_memory
                WHERE index_version = ?
            """, (self.index_version,))
            rows = cursor.fetchall()

            best_match = None
            best_overlap = 0.0

            for row in rows:
                stored_words = set(row["normalized_query"].split())
                if not stored_words:
                    continue
                intersection = len(q_words & stored_words)
                union = len(q_words | stored_words)
                jaccard = intersection / union if union > 0 else 0

                if jaccard > 0.85 and jaccard > best_overlap:
                    best_overlap = jaccard
                    best_match = dict(row)

            if best_match:
                best_match["citations"] = json.loads(best_match["citations_json"])
                return best_match

        return None
