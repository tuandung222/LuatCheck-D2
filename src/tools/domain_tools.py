"""
Domain-Agnostic Knowledge Tool Registry.

Provides decoupled, standardized tools for searching, retrieving, persisting,
and executing Human-In-The-Loop actions across arbitrary domain corpora
(Legal, Medical, Finance, Enterprise IT SOPs).
"""
import os
import json
import math
import re
import time
import hashlib
import hmac
import secrets
import threading
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple

from src.retrieval.hybrid_domain import HybridDomainRetriever
from src.tools.permissions import PermissionManager, PermissionError


class DomainKnowledgeRegistry:
    """
    Standard registry for knowledge search, retrieval, episodic persistence,
    and reversible/irreversible tool execution.
    """

    def __init__(
        self,
        corpus_path: str = "data/corpus/labor_code_2019_official.json",
        outbox_path: Optional[str] = None,
        retriever: Optional[Any] = None,
        dense_endpoint: Optional[str] = None,
        dense_model_name: str = "all-minilm",
        retrieval_mode: str = "tfidf",
        rrf_k: int = 60,
        reranker: Optional[Any] = None,
        rerank_top_k_in: int = 20,
        rerank_top_k_out: int = 5
    ):
        self.retriever = retriever or HybridDomainRetriever(
            corpus_path=corpus_path,
            dense_endpoint=dense_endpoint,
            dense_model_name=dense_model_name,
            retrieval_mode=retrieval_mode,
            rrf_k=rrf_k
        )
        self.reranker = None
        self.rerank_top_k_in = self.rerank_top_k_out = 0
        if reranker is not None:
            self.configure_reranker(reranker, rerank_top_k_in, rerank_top_k_out)
        self.saved_cases: Dict[str, Dict[str, Any]] = {}
        self.sent_summaries_log: List[Dict[str, Any]] = []
        self.executed_idempotency_keys: set = set()
        self.pending_proposals: Dict[str, Dict[str, Any]] = {}
        self.outbox_path = outbox_path
        self._dispatch_lock = threading.RLock()

        # Reload executed idempotency keys from durable outbox if path is specified
        self._load_outbox()

        # Syllable document frequencies for query-aware snippets.
        corpus = getattr(self.retriever, "corpus", None) or []
        self._df = Counter(tok for doc in corpus for tok in set(self._tokens(doc.get("content", ""))))
        self._n_docs = max(len(corpus), 1)

    SNIPPET_CHARS = 600
    SNIPPET_CLAUSES = 2
    _CLAUSE_SPLIT = re.compile(r"(?<=[.;:])\s+(?=(?:\d{1,2}\.|[a-zđ]\))\s)")

    @staticmethod
    def _tokens(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _snippet(self, query: str, title: str, content: str) -> Dict[str, Any]:
        """Return the clauses/points that best match the query, in article order, not the article opening.

        Short articles are returned whole. Scoring is IDF-weighted syllable and bigram overlap.
        """
        if len(content) <= self.SNIPPET_CHARS:
            return {"content_snippet": content, "snippet_truncated": False}
        if title and content.startswith(title) and content[len(title):len(title) + 2].strip()[:1].islower():
            # The stored title of some articles stops mid-heading; extend it up to clause 1.
            match = re.match(re.escape(title) + r"(.{0,200}?)(?=\s1\.\s)", content)
            if match:
                title = title + match.group(1)
        body = content[len(title):].strip() if title and content.startswith(title) else content
        q = self._tokens(query)
        q_bigrams = set(zip(q, q[1:]))
        idf = lambda t: math.log((self._n_docs + 1) / (self._df.get(t, 0) + 1))
        segments = self._CLAUSE_SPLIT.split(body)
        scored = []
        for index, segment in enumerate(segments):
            toks = self._tokens(segment)
            tokset, bigrams = set(toks), set(zip(toks, toks[1:]))
            score = sum(idf(t) for t in set(q) if t in tokset) + sum(2 * idf(b[1]) for b in q_bigrams if b in bigrams)
            scored.append((score, -index))
        keep = sorted(-i for _, i in sorted(scored, reverse=True)[:self.SNIPPET_CLAUSES])
        parts, used = [], 0
        for index in keep:
            room = self.SNIPPET_CHARS - used
            if room <= 40:
                break
            segment = segments[index]
            if re.match(r"[a-zđ]\)\s", segment):
                # A point ("b) ...") is meaningless without its clause's lead-in ("... trong trường hợp sau đây:").
                lead = next((segments[j] for j in range(index - 1, -1, -1) if segments[j].rstrip().endswith(":")), "")
                if lead:
                    lead = re.split(r"(?<=[.;])\s+", lead.rstrip())[-1]
                    segment = f"{lead} ... {segment}"
            parts.append(segment if len(segment) <= room else segment[:room] + "...")
            used += len(parts[-1])
        excerpt = " [...] ".join(parts)
        return {"content_snippet": f"{title} [...] {excerpt}" if title else excerpt, "snippet_truncated": True}

    def _load_outbox(self):
        if self.outbox_path and os.path.exists(self.outbox_path):
            try:
                with open(self.outbox_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            canonical = self.summary_hash(record["recipient"], record["content"], record["idempotency_key"])
                            legacy = hashlib.sha256(f"{record['recipient']}:{record['content']}:{record['idempotency_key']}".encode()).hexdigest()
                            if record.get("hash") not in {canonical, legacy}:
                                raise ValueError("Outbox record hash does not match its payload.")
                            self.executed_idempotency_keys.add(canonical)
                            self.sent_summaries_log.append(record)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise ValueError("Cannot safely reload the durable outbox; inspect existing records before retrying.") from exc

    def configure_reranker(self, reranker: Any, top_k_in: int, top_k_out: int) -> None:
        """Enable second-stage reranking. `reranker` is a `src.model_manager.ManagedModel` (or None to disable)."""
        if reranker is not None and (top_k_in < 1 or top_k_out < 1 or top_k_out > top_k_in):
            raise ValueError("rerank top_k_out must be between 1 and top_k_in")
        self.reranker, self.rerank_top_k_in, self.rerank_top_k_out = reranker, top_k_in, top_k_out

    def search_knowledge(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Searches the corpus. Each hit carries its best-matching clause, not the article opening;
        the law name is given once, and no field is duplicated.
        """
        return self.search_with_metadata(query, top_k)[0]

    def search_with_metadata(self, query: str, top_k: int = 5) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """(model-visible result, audit metadata). The metadata is for the ledger only and is None without a reranker.

        With a reranker the first stage returns `top_k_in` candidates, which are scored against `query`; the best
        min(top_k, top_k_out) are returned in reranked order. A reranker failure raises (ModelComponentError):
        there is no fallback to first-stage order.
        """
        metadata: Optional[Dict[str, Any]] = None
        if self.reranker is None:
            results = self.retriever.search(query, top_k=top_k)
        else:
            started = time.perf_counter()
            candidates = self.retriever.search(query, top_k=self.rerank_top_k_in)
            retrieval_ms = (time.perf_counter() - started) * 1000.0
            results = []
            metadata = {"rerank": {"requested_top_k": top_k, "top_k_in": self.rerank_top_k_in, "top_k_out": self.rerank_top_k_out,
                                   "n_candidates": len(candidates), "first_stage_ms": retrieval_ms,
                                   "first_stage_ids": [str(c.get("doc_id") or c.get("article_id") or "") for c in candidates],
                                   "score_note": "backend-specific relevance scores; not comparable across backends, not answer correctness"}}
            if candidates:
                with self.reranker.use() as component:
                    # Every candidate is scored and its score recorded; only the best min(top_k, top_k_out) are returned.
                    ranked = component.rerank(query, candidates, top_k=len(candidates))
                    run = dict(component.last_run)
                results = [doc for doc, _ in ranked][:min(top_k, self.rerank_top_k_out)]
                metadata["rerank"].update({
                    "backend": run.get("backend"), "model": run.get("model"), "device": run.get("device"),
                    "dtype": run.get("dtype"), "max_length": run.get("max_length"), "n_scored": run.get("n_scored"),
                    "n_truncated": run.get("n_truncated"), "wall_ms": run.get("wall_ms"), "ms_per_pair": run.get("ms_per_pair"),
                    "ranking": run.get("ranking"), "reranked_ids": [str(d.get("doc_id") or d.get("article_id") or "") for d in results]})
        if not results:
            return ({"status": "not_found", "message": f"Không tìm thấy tài liệu phù hợp cho truy vấn '{query}'",
                     "articles": []}, metadata)
        articles = []
        for r in results:
            content = r.get("content") or r.get("text") or ""
            title = r.get("title") or r.get("section_title", "")
            articles.append({"article_id": str(r.get("doc_id") or r.get("article_id") or ""), "title": title,
                             **self._snippet(query, title, content), "full_content_chars": len(content)})
        sources = [str(r.get("law_name") or r.get("source_name") or "") for r in results]
        if len(set(sources)) > 1:
            # Several documents in one answer set: every article names its own source instead of one shared law_name.
            for article, source in zip(articles, sources):
                article["law_name"] = source
            return ({"status": "success", "count": len(articles), "articles": articles}, metadata)
        return ({"status": "success", "law_name": sources[0], "count": len(articles), "articles": articles}, metadata)

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

        return {"status": "success", "article_id": canonical_id, "law_name": source_name,
                "title": title, "full_content": content}

    def get_article(self, article_id: str) -> Dict[str, Any]:
        return self.get_document(article_id)

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

    @staticmethod
    def summary_hash(recipient: str, content: str, idempotency_key: str) -> str:
        payload = json.dumps([recipient, content, idempotency_key], ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def create_summary_proposal(
        self,
        recipient: str,
        content: str,
        idempotency_key: str,
        proposal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates server-validated proposal for dispatching advisory summary."""
        with self._dispatch_lock:
            payload_hash = self.summary_hash(recipient, content, idempotency_key)
            proposal_id = proposal_id or f"prop_{payload_hash[:16]}"
            existing = self.pending_proposals.get(proposal_id)
            if existing is not None:
                return {k: v for k, v in existing.items() if k != "approval_token"}
            proposal = {
                "proposal_id": proposal_id,
                "approval_token": None,
                "recipient": recipient,
                "content": content,
                "idempotency_key": idempotency_key,
                "payload_hash": payload_hash,
                "approved": False,
                "created_at": time.time()
            }
            self.pending_proposals[proposal_id] = proposal
            return {k: v for k, v in proposal.items() if k != "approval_token"}

    def discard_unapproved_proposal(self, proposal_id: str) -> None:
        """Drop a proposal attempt that lost an atomic persistence race."""
        with self._dispatch_lock:
            proposal = self.pending_proposals.get(proposal_id)
            if proposal is not None and not proposal.get("approved"):
                self.pending_proposals.pop(proposal_id, None)

    def approve_proposal(self, proposal_id: str) -> Optional[str]:
        """Trusted host/UI only. This method must never be exposed as a model tool."""
        with self._dispatch_lock:
            if proposal_id in self.pending_proposals:
                self.pending_proposals[proposal_id]["approved"] = True
                token = secrets.token_urlsafe(32)
                self.pending_proposals[proposal_id]["approval_token"] = token
                return token
            return None

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
        content_hash = self.summary_hash(recipient, content, idempotency_key)

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
                "message": err_msg,
                "proposed_payload": {
                    "recipient": recipient,
                    "content": content,
                    "idempotency_key": idempotency_key
                }
            }

        proposal = self.pending_proposals.get(proposal_id or "")
        valid_approval = bool(proposal and proposal.get("approved")
                              and proposal.get("payload_hash") == content_hash
                              and isinstance(approval_token, str)
                              and hmac.compare_digest(approval_token, proposal.get("approval_token") or ""))
        if not valid_approval:
            return {"status": "blocked_by_permission_gate", "requires_confirmation": True,
                    "message": "Caller confirmation is insufficient; trusted approval bound to this payload is required."}

        with self._dispatch_lock:
            try:
                return self._append_outbox(recipient, content, idempotency_key, content_hash)
            except OSError as exc:
                return {"status": "error", "delivered": False,
                        "message": f"Không thể xác nhận ghi bền vững vào outbox ({type(exc).__name__}); cần kiểm tra trước khi thử lại."}

    def _append_outbox(self, recipient: str, content: str, idempotency_key: str, content_hash: str) -> Dict[str, Any]:
        # Local queue only: this is not a network-delivery receipt.
        if content_hash in self.executed_idempotency_keys:
            return {
                "status": "duplicate_suppressed",
                "message": f"Yêu cầu gửi với idempotency_key '{idempotency_key}' đã được thực thi trước đó. Tránh gửi lặp."
            }

        entry = {
            "recipient": recipient,
            "content": content,
            "idempotency_key": idempotency_key,
            "hash": content_hash,
            "created_at": time.time()
        }
        # Persist to durable outbox queue if outbox path is configured
        if self.outbox_path:
            out_dir = os.path.dirname(self.outbox_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(self.outbox_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
        else:
            return {"status": "error", "message": "No durable local outbox configured; nothing was delivered."}
        self.executed_idempotency_keys.add(content_hash)
        self.sent_summaries_log.append(entry)

        return {
            "status": "queued_locally",
            "delivered": False,
            "message": "Đã lưu vào hàng đợi cục bộ; chưa gửi email/webhook.",
            "hash": content_hash
        }

    send_summary = dispatch_external_action
    create_proposal = create_summary_proposal
