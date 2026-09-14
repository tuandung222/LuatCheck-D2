"""
Implementation of Legal Tools for LuatCheck Agent
"""
import hashlib
from typing import Dict, Any, List, Optional
from src.retrieval.hybrid_rrf import HybridLegalRetriever
from src.tools.permissions import PermissionManager, PermissionError


class LegalToolRegistry:
    def __init__(self, corpus_path: str = "data/corpus/labor_code_2019.json"):
        self.retriever = HybridLegalRetriever(corpus_path=corpus_path)
        self.saved_cases: Dict[str, Dict[str, Any]] = {}
        self.sent_summaries_log: List[Dict[str, Any]] = []
        self.executed_idempotency_keys: set = set()

    def search_law(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Tìm kiếm điều khoản pháp luật có liên quan đến câu hỏi hoặc tình huống.
        """
        results = self.retriever.search(query, top_k=top_k)
        if not results:
            return {
                "status": "not_found",
                "message": f"Không tìm thấy điều luật phù hợp cho truy vấn '{query}'",
                "articles": []
            }
        
        articles_summary = []
        for r in results:
            articles_summary.append({
                "article_id": r["article_id"],
                "law_name": r["law_name"],
                "title": r["title"],
                "content_snippet": r["content"][:300] + "..." if len(r["content"]) > 300 else r["content"],
                "rrf_score": round(r["rrf_score"], 4)
            })

        return {
            "status": "success",
            "count": len(articles_summary),
            "articles": articles_summary
        }

    def get_article(self, article_id: str) -> Dict[str, Any]:
        """
        Lấy nguyên văn toàn bộ nội dung một điều luật theo mã định danh (ví dụ: 'Dieu_35').
        """
        article = self.retriever.get_article_by_id(article_id)
        if not article:
            return {
                "status": "error",
                "message": f"Mã điều luật '{article_id}' không tồn tại trong cơ sở dữ liệu."
            }
        return {
            "status": "success",
            "article_id": article["article_id"],
            "law_name": article["law_name"],
            "title": article["title"],
            "full_content": article["content"]
        }

    def save_case(self, case_id: str, summary: str, client_name: Optional[str] = "Anonymous") -> Dict[str, Any]:
        """
        Lưu hồ sơ tư vấn vào bộ nhớ có thể hoàn tác (Reversible Action).
        """
        self.saved_cases[case_id] = {
            "case_id": case_id,
            "summary": summary,
            "client_name": client_name
        }
        return {
            "status": "success",
            "message": f"Đã lưu hồ sơ vụ việc '{case_id}' thành công."
        }

    def send_summary(
        self,
        recipient: str,
        content: str,
        idempotency_key: str,
        user_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Gửi tóm tắt tư vấn pháp lý qua kênh liên lạc bên ngoài (Egress Point).
        TÁC VỤ KHÔNG KHẢ HỒI: Bắt buộc phải có user_confirmed = True!
        """
        # 1. Kiểm tra quyền và Human Confirmation
        is_auth, err_msg = PermissionManager.check_permission(
            "send_summary",
            {"recipient": recipient, "content": content},
            user_confirmed=user_confirmed
        )
        if not is_auth:
            return {
                "status": "blocked_by_permission_gate",
                "requires_confirmation": True,
                "message": err_msg,
                "proposed_payload": {
                    "recipient": recipient,
                    "content": content,
                    "idempotency_key": idempotency_key
                }
            }

        # 2. Kiểm tra Idempotency chống lặp lại ngoài ý muốn
        content_hash = hashlib.sha256(f"{recipient}:{content}:{idempotency_key}".encode()).hexdigest()
        if content_hash in self.executed_idempotency_keys:
            return {
                "status": "duplicate_suppressed",
                "message": f"Yêu cầu gửi với idempotency_key '{idempotency_key}' đã được thực thi trước đó. Tránh gửi lặp."
            }

        self.executed_idempotency_keys.add(content_hash)
        entry = {
            "recipient": recipient,
            "content": content,
            "idempotency_key": idempotency_key,
            "hash": content_hash
        }
        self.sent_summaries_log.append(entry)

        return {
            "status": "success",
            "message": f"Đã gửi thành công bản tóm tắt pháp lý tới '{recipient}'.",
            "hash": content_hash
        }
