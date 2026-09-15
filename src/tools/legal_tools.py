import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from src.retrieval.hybrid_rrf import HybridLegalRetriever
from src.tools.permissions import PermissionManager, PermissionError


class LegalToolRegistry:
    def __init__(
        self,
        corpus_path: str = "data/corpus/labor_code_2019.json",
        outbox_path: Optional[str] = None
    ):
        self.retriever = HybridLegalRetriever(corpus_path=corpus_path)
        self.saved_cases: Dict[str, Dict[str, Any]] = {}
        self.sent_summaries_log: List[Dict[str, Any]] = []
        self.executed_idempotency_keys: set = set()
        self.pending_proposals: Dict[str, Dict[str, Any]] = {}
        self.outbox_path = outbox_path

        # Tải lại các khóa idempotency đã thực thi từ outbox bền vững nếu có chỉ định đường dẫn
        self._load_outbox()

    def _load_outbox(self):
        if self.outbox_path and os.path.exists(self.outbox_path):
            try:
                with open(self.outbox_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            h = record.get("hash")
                            if h:
                                self.executed_idempotency_keys.add(h)
                            self.sent_summaries_log.append(record)
            except Exception:
                pass

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

    def create_summary_proposal(self, recipient: str, content: str, idempotency_key: str) -> Dict[str, Any]:
        """Tạo proposal xác thực cấp server cho hành động gửi tóm tắt."""
        payload_hash = hashlib.sha256(f"{recipient}:{content}:{idempotency_key}".encode()).hexdigest()
        proposal_id = f"prop_{payload_hash[:16]}"
        token = f"tok_{hashlib.sha256(f'{proposal_id}:APPROVED_HITL'.encode()).hexdigest()[:16]}"
        proposal = {
            "proposal_id": proposal_id,
            "approval_token": token,
            "recipient": recipient,
            "content": content,
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
            "approved": False,
            "created_at": time.time()
        }
        self.pending_proposals[proposal_id] = proposal
        return proposal

    def approve_proposal(self, proposal_id: str) -> bool:
        """Phê duyệt proposal qua giao diện người dùng."""
        if proposal_id in self.pending_proposals:
            self.pending_proposals[proposal_id]["approved"] = True
            return True
        return False

    def send_summary(
        self,
        recipient: str,
        content: str,
        idempotency_key: str,
        user_confirmed: bool = False,
        proposal_id: Optional[str] = None,
        approval_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gửi tóm tắt tư vấn pháp lý vào hàng đợi Outbox bền vững có kiểm soát HITL.
        TÁC VỤ KHÔNG KHẢ HỒI: Bắt buộc phải có phê duyệt từ người dùng (Human-In-The-Loop Confirmation).
        """
        current_payload = f"{recipient}:{content}"
        content_hash = hashlib.sha256(f"{recipient}:{content}:{idempotency_key}".encode()).hexdigest()

        # 1. Kiểm tra quyền và Human Confirmation
        if not user_confirmed:
            prop = self.create_summary_proposal(recipient, content, idempotency_key)
            is_auth, err_msg = PermissionManager.check_permission(
                "send_summary",
                {"recipient": recipient, "content": content},
                user_confirmed=False
            )
            return {
                "status": "blocked_by_permission_gate",
                "requires_confirmation": True,
                "proposal_id": prop["proposal_id"],
                "approval_token": prop["approval_token"],
                "message": err_msg,
                "proposed_payload": {
                    "recipient": recipient,
                    "content": content,
                    "idempotency_key": idempotency_key
                }
            }

        # 2. Kiểm tra Idempotency chống lặp lại ngoài ý muốn qua mã SHA-256 hash
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
            "hash": content_hash,
            "created_at": time.time()
        }
        self.sent_summaries_log.append(entry)

        # Lưu bền vững vào hàng đợi outbox nếu cấu hình đường dẫn outbox
        if self.outbox_path:
            try:
                out_dir = os.path.dirname(self.outbox_path)
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)
                with open(self.outbox_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass

        return {
            "status": "success",
            "message": f"Đã gửi thành công bản tóm tắt pháp lý tới '{recipient}'.",
            "hash": content_hash
        }
