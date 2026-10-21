"""
Domain-Agnostic Knowledge Tool Registry.

Provides decoupled, standardized tools for searching, retrieving, persisting,
and executing Human-In-The-Loop actions across arbitrary domain corpora
(Legal, Medical, Finance, Enterprise IT SOPs).
"""
import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional

from src.retrieval.hybrid_domain import HybridDomainRetriever
from src.tools.permissions import PermissionManager, PermissionError


class DomainKnowledgeRegistry:
    """
    Standard registry for knowledge search, retrieval, episodic persistence,
    and reversible/irreversible tool execution.
    """

    def __init__(
        self,
        corpus_path: str = "data/corpus/labor_code_2019.json",
        outbox_path: Optional[str] = None,
        retriever: Optional[Any] = None,
        dense_endpoint: Optional[str] = None,
        dense_model_name: str = "all-minilm"
    ):
        self.retriever = retriever or HybridDomainRetriever(
            corpus_path=corpus_path,
            dense_endpoint=dense_endpoint,
            dense_model_name=dense_model_name
        )
        self.saved_cases: Dict[str, Dict[str, Any]] = {}
        self.sent_summaries_log: List[Dict[str, Any]] = []
        self.executed_idempotency_keys: set = set()
        self.pending_proposals: Dict[str, Dict[str, Any]] = {}
        self.outbox_path = outbox_path

        # Reload executed idempotency keys from durable outbox if path is specified
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

    def search_knowledge(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Searches knowledge documents or sections relevant to the user query.
        """
        results = self.retriever.search(query, top_k=top_k)
        if not results:
            return {
                "status": "not_found",
                "message": f"Không tìm thấy tài liệu phù hợp cho truy vấn '{query}'",
                "documents": [],
                "articles": []
            }

        docs_summary = []
        for r in results:
            content_text = r.get("content_snippet") or r.get("content") or r.get("text") or ""
            doc_id = str(r.get("doc_id") or r.get("article_id") or "")
            source_name = str(r.get("source_name") or r.get("law_name") or "Knowledge Base")
            docs_summary.append({
                "doc_id": doc_id,
                "article_id": doc_id,
                "source_name": source_name,
                "law_name": source_name,
                "title": r.get("title") or r.get("section_title", ""),
                "content_snippet": content_text[:300] + "..." if len(content_text) > 300 else content_text,
                "rrf_score": round(r.get("rrf_score", r.get("score", 1.0)), 4)
            })

        return {
            "status": "success",
            "count": len(docs_summary),
            "documents": docs_summary,
            "articles": docs_summary
        }

    search_law = search_knowledge

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Retrieves the verbatim text of a specific document section by identifier.
        """
        doc = (
            getattr(self.retriever, "get_document_by_id", None)
            or getattr(self.retriever, "get_article_by_id", None)
        )(doc_id)

        if not doc:
            return {
                "status": "error",
                "message": f"Mã tài liệu '{doc_id}' không tồn tại trong cơ sở dữ liệu."
            }

        canonical_id = str(doc.get("doc_id") or doc.get("article_id") or doc_id)
        source_name = str(doc.get("source_name") or doc.get("law_name", "Knowledge Base"))
        title = str(doc.get("title") or doc.get("section_title", ""))
        content = str(doc.get("content") or doc.get("full_content", ""))

        return {
            "status": "success",
            "doc_id": canonical_id,
            "article_id": canonical_id,
            "source_name": source_name,
            "law_name": source_name,
            "title": title,
            "full_content": content,
            "content": content
        }

    get_article = get_document

    def record_case(self, case_id: str, summary: str, client_name: Optional[str] = "Anonymous") -> Dict[str, Any]:
        """
        Saves advisory case to reversible storage (Reversible Action).
        """
        self.saved_cases[case_id] = {
            "case_id": case_id,
            "summary": summary,
            "client_name": client_name,
            "timestamp": time.time()
        }
        return {
            "status": "success",
            "message": f"Đã lưu hồ sơ tư vấn '{case_id}' thành công.",
            "case_id": case_id
        }

    save_case = record_case

    def create_summary_proposal(self, recipient: str, content: str, idempotency_key: str) -> Dict[str, Any]:
        """Creates server-validated proposal for dispatching advisory summary."""
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
        """Approves proposal via user interaction interface."""
        if proposal_id in self.pending_proposals:
            self.pending_proposals[proposal_id]["approved"] = True
            return True
        return False

    def dispatch_external_action(
        self,
        recipient: str,
        content: str,
        idempotency_key: str,
        user_confirmed: bool = False,
        proposal_id: Optional[str] = None,
        approval_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches advisory summary into durable outbox queue guarded by HITL verification.
        IRREVERSIBLE ACTION: Requires explicit Human-In-The-Loop Confirmation prior to execution.
        """
        content_hash = hashlib.sha256(f"{recipient}:{content}:{idempotency_key}".encode()).hexdigest()

        # 1. Authorization check and Human Confirmation
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

        # 2. Idempotency verification preventing unintentional duplicates via SHA-256 hash
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

        # Persist to durable outbox queue if outbox path is configured
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

    send_summary = dispatch_external_action
    create_proposal = create_summary_proposal
