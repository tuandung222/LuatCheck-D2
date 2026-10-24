"""Verified-answer memory around the SQLite episodic store.

Two jobs, both switched by `memory.*` in the app config:

* `recall`:   reuse a stored answer to a similar earlier question (`memory.enabled` and `memory.reuse_answers`).
              A stored answer is used only if it carries native-inference evidence, no optional NLI step would be
              skipped by reusing it, and it passes the current verification pipeline again against the current
              retriever. Otherwise the normal ReAct loop runs.
* `remember`: persist an answer that passed verification (`memory.enabled`).

With `memory.enabled: false` no store exists and both calls do nothing.
"""
import time
from typing import Any, Callable, Dict, List, Optional

from src.agent.citations import build_citation, dump_citations
from src.agent.state import CaseLedger, Citation
from src.domains import DomainProfile
from src.memory.ledger import CaseLedgerManager
from src.memory.sqlite_store import SQLiteEpisodicStore
from src.security.audit_logger import AuditLogger


def _article_ids(raw: Any) -> List[str]:
    if isinstance(raw, str):
        return [aid.strip() for aid in raw.split(",") if aid.strip()]
    if isinstance(raw, (list, tuple, set)):
        return [str(aid).strip() for aid in raw if str(aid).strip()]
    return []


class AnswerMemory:
    def __init__(self, store: Optional[SQLiteEpisodicStore], audit: AuditLogger, profile: DomainProfile, *,
                 enabled: bool, reuse_answers: bool, similarity_threshold: float):
        self.store = store
        self.audit = audit
        self.profile = profile
        self.enabled = enabled and store is not None
        self.reuse_answers = reuse_answers
        self.similarity_threshold = similarity_threshold

    # ------------------------------------------------------------------ reuse
    def recall(self, ledger: CaseLedger, session_id: str, query: str, *, pipeline: Any,
               lookup: Callable[[str], Optional[Dict[str, Any]]], verified: bool, started: float) -> bool:
        """Fill `ledger` with a re-verified stored answer and return True; return False to run the ReAct loop."""
        case = self._candidate(session_id, query, pipeline)
        if case is None:
            return False
        citations = [build_citation(self.profile, c) if isinstance(c, dict)
                     else Citation(article_id=str(c), law_name=self.profile.source_name)
                     for c in case.get("citations", [])]
        article_ids = _article_ids(case.get("article_ids", ""))
        for citation in citations:
            if citation.article_id and citation.article_id not in article_ids:
                article_ids.append(citation.article_id)
        for article_id in article_ids:
            record = lookup(article_id)
            CaseLedgerManager.add_retrieved_article(ledger, article_id, record.get("content", "") if record else "")

        result = pipeline.verify(answer_text=case["answer"], citations=citations,
                                 retrieved_article_ids=ledger.retrieved_article_ids)
        if result.is_valid:
            ledger.is_terminal = True
            ledger.terminal_status = "answered"
            ledger.final_output = {"action": "answer", "content": case["answer"],
                                   "citations": dump_citations(citations), "from_cache": True, "verified": verified}
            self.audit.log_event(session_id, "cache_hit",
                                 {"case_id": case.get("case_id"), "verified": True,
                                  "article_ids": ledger.retrieved_article_ids, "citations_count": len(citations)},
                                 latency_ms=(time.time() - started) * 1000)
            return True
        self.audit.log_event(session_id, "cache_verification_failed",
                             {"case_id": case.get("case_id"), "feedback": self._rejection_feedback(result)})
        # The ReAct loop starts from an empty working memory.
        ledger.retrieved_article_ids = []
        ledger.retrieved_articles_cache = {}
        return False

    def _candidate(self, session_id: str, query: str, pipeline: Any) -> Optional[Dict[str, Any]]:
        if not (self.enabled and self.reuse_answers):
            return None
        case = self.store.retrieve_similar_case(query, threshold=self.similarity_threshold)
        if case and not self.store.has_native_evidence(case):
            self.audit.log_event(session_id, "cache_untrusted_origin", {"case_id": case.get("case_id")})
            return None
        if case and getattr(pipeline, "nli_step", None) is not None:
            # A stored answer would skip the configured NLI step (and its ledger record): do not reuse it.
            self.audit.log_event(session_id, "cache_skipped_nli_enabled", {"case_id": case.get("case_id")})
            return None
        return case

    def _rejection_feedback(self, result: Any) -> Optional[str]:
        semantic = getattr(result, "semantic_result", None)
        if semantic is not None:
            failed = [f["sentence"] for f in semantic.get("failed_claims", [])]
            return self.profile.messages.cache_l2_rejection.format(
                count=len(failed), claims="\n".join(f'- "{s}"' for s in failed[:2]))
        return result.repair_feedback

    # ---------------------------------------------------------------- persist
    def remember(self, ledger: CaseLedger, session_id: str, query: str, answer: str,
                 citations: List[Dict[str, Any]], *, verified: bool, native_inference: bool) -> None:
        """Store a verified answer together with the native model calls that produced it."""
        if not (self.enabled and verified and native_inference and ledger.llm_calls):
            return
        evidence = [{"backend": call.get("backend"), "outcome": call.get("outcome"),
                     "requested_model": call.get("requested_model"), "request_sha256": call.get("request_sha256"),
                     "action": call.get("response", {}).get("action")}
                    for call in ledger.llm_calls]
        self.store.write_if_verified(case_id=session_id, query=query, answer=answer, citations=citations,
                                     is_l1_verified=True, native_evidence=evidence)
