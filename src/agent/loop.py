"""
LuatCheck Budgeted ReAct Agent Loop.

Finite-State Machine (FSM) control loop with strict execution budgets
and multi-tier evidence verification (Lexical Grounding & Semantic NLI).

The controller does not decide which implementation backs each component: `src/pipeline/builder.py` builds them from
the app config (or the caller injects them), and this class only orchestrates one run:

    guardrails -> answer memory -> [model action -> search | read | answer | clarify | refuse]* -> audit log

Every failure of a model or model component ends the run as `terminal_status: error`; nothing is substituted.
"""
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, Optional, List, Tuple

from src.agent.citations import build_citation, dump_citations, parse_model_citations
from src.agent.llm_client import InferenceError, NativeLLMClient
from src.agent.query import anchor_query
from src.agent.state import ActionType, CaseLedger, Citation
from src.config.app_config import AppConfig, load_config
from src.domains import DomainProfile
from src.interfaces.base import BaseRetriever, BaseLLMClient, BaseVerifier
from src.memory.ledger import CaseLedgerManager
from src.memory.sqlite_store import SQLiteEpisodicStore
from src.model_manager import ModelManager
from src.model_runtime import ModelComponentError
from src.pipeline.builder import AgentComponents, Overrides, build_components
from src.security.audit_logger import AuditLogger
from src.security.guardrails import SecurityGuardrails
from src.tools.legal_tools import LegalToolRegistry
from src.verifier.modes import OFF
from src.verifier.pipeline import VerificationPipeline

OBSERVATION_PREFIX = "[OBSERVATION_TOOL_RESULT]\n"


@dataclass
class _Run:
    """State of one `run()` call that is not part of the audit ledger."""
    ledger: CaseLedger
    session_id: str
    query: str
    started: float
    messages: List[Dict[str, str]] = field(default_factory=list)
    # Observations already in the context are not resent: a repeated query or a re-read article gets a short
    # notice (still a tool call against the budget).
    search_history: Dict[str, List[str]] = field(default_factory=dict)
    fully_read: set = field(default_factory=set)
    searched: bool = False    # a search action has been executed in this run (agent.require_search_before_answer, retrieval.first_search_anchor)
    refuse_search_prompted: bool = False


class LuatCheckAgent:
    VALID_MODES = VerificationPipeline.VALID_MODES

    def __init__(
        self,
        model_name: Optional[str] = None,
        ollama_url: Optional[str] = None,
        corpus_path: Optional[str] = None,
        max_tool_calls: Optional[int] = None,
        max_repairs: Optional[int] = None,
        max_steps: Optional[int] = None,
        verification_mode: Optional[str] = None,
        enable_verification: Optional[bool] = None,
        l2_use_slm: Optional[bool] = None,
        # Components the caller supplies instead of having them built from the config (Dependency Injection)
        config: Optional[AppConfig] = None,
        retriever: Optional[BaseRetriever] = None,
        llm_client: Optional[BaseLLMClient] = None,
        verifier: Optional[BaseVerifier] = None,
        l2_verifier: Optional[BaseVerifier] = None,
        lexical_grounding_verifier: Optional[BaseVerifier] = None,
        semantic_nli_verifier: Optional[BaseVerifier] = None,
        verification_pipeline: Optional[VerificationPipeline] = None,
        sqlite_store: Optional[SQLiteEpisodicStore] = None,
        audit_logger: Optional[AuditLogger] = None,
        outbox_path: Optional[str] = None,
        tool_registry: Optional[LegalToolRegistry] = None,
        event_sink: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        profile: Optional[DomainProfile] = None,
        model_manager: Optional[ModelManager] = None,
        components: Optional[AgentComponents] = None
    ):
        self.config = config or (components.config if components is not None else load_config())
        if components is None:
            # Optional components (reranker, NLI, index embeddings) share one ModelManager: lazy load, idle unload,
            # resident budget. Nothing is built or loaded unless the config enables it.
            components = build_components(self.config, Overrides(
                model_name=model_name, endpoint=ollama_url, corpus_path=corpus_path, outbox_path=outbox_path,
                verification_mode=verification_mode, enable_verification=enable_verification, l2_use_slm=l2_use_slm,
                profile=profile, model_manager=model_manager, retriever=retriever, tool_registry=tool_registry,
                llm_client=llm_client, lexical_verifier=lexical_grounding_verifier or verifier,
                semantic_verifier=semantic_nli_verifier or l2_verifier, verification_pipeline=verification_pipeline,
                sqlite_store=sqlite_store, audit_logger=audit_logger))
        self.components = components
        self.profile = components.profile
        self.model_name = components.model_name
        self.ollama_url = components.endpoint
        self.corpus_path = components.corpus_path
        self.outbox_path = components.outbox_path
        self.l2_use_slm = components.l2_use_slm
        self.verification_mode = components.verification_mode
        self.enable_verification = (self.verification_mode != OFF)
        self.model_manager = components.model_manager
        self.tool_registry = components.tool_registry
        self.reranker_handle = components.reranker_handle
        self.verification_pipeline = components.verification_pipeline
        self.lexical_verifier = self.verifier = components.lexical_verifier
        self.semantic_verifier = self.l2_verifier = components.semantic_verifier
        self.answer_memory = components.answer_memory
        self.sqlite_store = components.sqlite_store
        self.audit_logger = components.audit_logger
        self.llm_client = components.llm_client

        # Execution budgets
        budgets = self.config.budgets
        self.max_tool_calls = max_tool_calls if max_tool_calls is not None else budgets.max_tool_calls
        self.max_repairs = max_repairs if max_repairs is not None else budgets.max_repairs
        self.max_steps = max_steps if max_steps is not None else budgets.max_steps
        self.event_sink = event_sink
        self.ledger: Optional[CaseLedger] = None

    @classmethod
    def from_config(cls, config_path_or_obj: Any = None, **kwargs) -> "LuatCheckAgent":
        """Factory method: Initialize LuatCheckAgent directly from YAML config path or AppConfig object."""
        if isinstance(config_path_or_obj, str):
            cfg = load_config(config_path_or_obj)
        elif isinstance(config_path_or_obj, AppConfig):
            cfg = config_path_or_obj
        else:
            cfg = load_config()
        return cls(config=cfg, **kwargs)

    @classmethod
    def default(cls) -> "LuatCheckAgent":
        """Factory method: Initialize LuatCheckAgent with standard default configuration."""
        return cls.from_config()

    # ------------------------------------------------------------------ tool access
    def _citation(self, data: Dict[str, Any]) -> Citation:
        return build_citation(self.profile, data)

    def _search(self, query: str, top_k: int) -> Dict[str, Any]:
        return self._search_with_metadata(query, top_k)[0]

    def _search_with_metadata(self, query: str, top_k: int) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """(model-visible result, audit metadata for the ledger). A reranker failure raises ModelComponentError."""
        with_meta = getattr(self.tool_registry, "search_with_metadata", None)
        if with_meta is not None:
            return with_meta(query, top_k=top_k)
        search = getattr(self.tool_registry, "search_knowledge", None) or self.tool_registry.search_law
        return search(query, top_k=top_k), None

    def _read(self, doc_id: str) -> Dict[str, Any]:
        read = getattr(self.tool_registry, "get_document", None) or self.tool_registry.get_article
        return read(doc_id)

    def _call_llm(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        """Delegate LLM response generation to modular LLM client."""
        return self.llm_client.generate(messages, ledger=ledger)

    def step(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        """Execute one step of LLM inference and advance ledger state."""
        return self._call_llm(messages, ledger=ledger or self.ledger)

    def _emit_run_event(self, name: str, **data: Any) -> None:
        """Publish a small, UI-safe event without exposing prompts or model thoughts."""
        if self.event_sink is None:
            return
        try:
            self.event_sink(name, data)
        except Exception:
            # Observability must never alter inference or the agent's result.
            return

    # ------------------------------------------------------------------ one run
    def run(self, user_query: str, pasted_doc: Optional[str] = None, session_id: Optional[str] = None) -> CaseLedger:
        try:
            ledger = self._run_inner(user_query, pasted_doc, session_id)
            self._emit_run_event("run_finished", terminal_status=ledger.terminal_status)
            return ledger
        except (InferenceError, ModelComponentError) as exc:
            # This also covers an explicitly enabled native verification judge and a failing model component
            # (reranker / NLI / index embeddings): an execution error, never a substitute result.
            ledger = self.ledger
            if ledger is None:
                raise
            self._finish(ledger, "error", self._error_output(str(exc), exc.kind))
            self.audit_logger.log_event(ledger.session_id, "inference_error", ledger.final_output)
            self._emit_run_event("run_finished", terminal_status="error", error_kind=exc.kind)
            return ledger

    def _run_inner(self, user_query: str, pasted_doc: Optional[str] = None, session_id: Optional[str] = None) -> CaseLedger:
        started = time.time()
        sid = session_id or f"session_{int(time.time() * 1000)}"
        ledger = CaseLedgerManager.create_session(sid, user_query, [pasted_doc] if pasted_doc else [])
        ledger.max_tool_calls = self.max_tool_calls
        ledger.max_repairs = self.max_repairs
        ledger.max_steps = self.max_steps
        ledger.deadline_monotonic = time.monotonic() + self.config.budgets.wall_seconds
        self.ledger = ledger
        self._emit_run_event("run_started")
        run = _Run(ledger=ledger, session_id=sid, query=user_query, started=started)

        if self._refused_by_guardrails(run, pasted_doc):
            return ledger
        if self.answer_memory.recall(ledger, sid, user_query, pipeline=self.verification_pipeline,
                                     lookup=self.tool_registry.retriever.get_article_by_id,
                                     verified=self.verification_mode != OFF, started=started):
            return ledger

        run.messages = self._initial_messages(user_query, pasted_doc, ledger)
        self._react_loop(run)
        self.audit_logger.log_event(
            sid, "session_completed",
            {"query": user_query, "terminal_status": ledger.terminal_status, "tool_calls": ledger.tool_calls_count,
             "repairs": ledger.repairs_count, "output": ledger.final_output},
            latency_ms=(time.time() - started) * 1000)
        return ledger

    def _initial_messages(self, user_query: str, pasted_doc: Optional[str], ledger: CaseLedger) -> List[Dict[str, str]]:
        """The conversation the controller starts from. Overridden by evaluation baselines (no tools / documents up front)."""
        return [
            {"role": "system", "content": self.profile.system_prompt},
            {"role": "user", "content": SecurityGuardrails.wrap_untrusted_input(user_query, pasted_doc)},
        ]

    # ------------------------------------------------------------------ ledger outcomes
    @staticmethod
    def _finish(ledger: CaseLedger, status: str, output: Dict[str, Any], refusal_source: Optional[str] = None) -> None:
        ledger.is_terminal = True
        ledger.terminal_status = status
        ledger.final_output = output
        # Who ended a refused run: model | repair_exhausted | budget | guardrail | controller (any other controller rule).
        ledger.refusal_source = (refusal_source or "controller") if status == "refused" else None

    @staticmethod
    def _error_output(reason: str, kind: str, verified_flag: bool = True) -> Dict[str, Any]:
        output = {"action": "error", "reason": reason, "error_kind": kind, "citations": []}
        if verified_flag:
            output["verified"] = False
        return output

    def _refuse(self, ledger: CaseLedger, reason: str, source: str = "controller") -> None:
        self._finish(ledger, "refused", {"action": "refuse", "reason": reason, "citations": []}, refusal_source=source)

    # ------------------------------------------------------------------ guardrails
    def _refused_by_guardrails(self, run: _Run, pasted_doc: Optional[str]) -> bool:
        if not self.config.security.guardrails.enabled:
            return False
        is_safe, safety_msg = SecurityGuardrails.check_input_safety(run.query, pasted_doc, profile=self.profile)
        if is_safe:
            return False
        self._finish(run.ledger, "refused", {"action": "refuse", "pre_model_policy_refusal": True,
                                             "reason": safety_msg, "citations": []}, refusal_source="guardrail")
        self.audit_logger.log_event(run.session_id, "security_refusal", {"query": run.query, "reason": safety_msg})
        return True

    # ------------------------------------------------------------------ ReAct loop
    def _react_loop(self, run: _Run) -> None:
        ledger = run.ledger
        while not ledger.is_terminal:
            if time.monotonic() >= ledger.deadline_monotonic:
                self._finish(ledger, "error", self._error_output("Task wall-clock budget exhausted.", "wall_timeout",
                                                                 verified_flag=False))
                return
            if not ledger.can_step():
                self._refuse(ledger, self.profile.messages.steps_exhausted.format(max_steps=self.max_steps), source="budget")
                return

            ledger.record_step()
            self._emit_run_event("model_call_started", step=ledger.step_count)
            try:
                agent_resp = self._call_llm(run.messages, ledger=ledger)
                if time.monotonic() >= ledger.deadline_monotonic:
                    raise InferenceError("Task wall-clock budget exhausted during inference.", "wall_timeout")
            except InferenceError as exc:
                self._finish(ledger, "error", self._error_output(str(exc), exc.kind))
                return
            # Native clients validate the action contract; any other response is an execution error, never a
            # substitute refusal. The model's action name is mapped to its canonical action by the domain profile.
            canonical = self.profile.canonical_action(agent_resp.get("action")) if isinstance(agent_resp, dict) else None
            if canonical is None or not isinstance(agent_resp.get("tool_args"), dict):
                self._finish(ledger, "error", self._error_output("Model returned an invalid or missing action.",
                                                                 "model_output_error"))
                return

            self._dispatch(run, agent_resp, canonical)

    def _dispatch(self, run: _Run, agent_resp: Dict[str, Any], canonical: ActionType) -> None:
        """Execute one validated model action."""
        tool_args = agent_resp["tool_args"]
        if self._search_required(run, canonical):
            self._act_search_required(run, agent_resp)
        elif self._refuse_search_required(run, canonical):
            self._act_refuse_search_required(run, agent_resp)
        elif canonical is ActionType.SEARCH:
            self._act_search(run, agent_resp, tool_args)
        elif canonical is ActionType.READ:
            self._act_read(run, agent_resp, tool_args)
        elif canonical is ActionType.ANSWER:
            self._act_answer(run, agent_resp, tool_args)
        else:
            self._act_clarify_or_refuse(run, agent_resp, canonical, tool_args)

    def _can_search(self) -> bool:
        """False for a client that cannot take the search action (closed-book / oracle baselines restrict the actions)."""
        allowed = getattr(self.llm_client, "allowed_actions", None)
        return allowed is None or ActionType.SEARCH in allowed

    def _search_required(self, run: _Run, canonical: ActionType) -> bool:
        """agent.require_search_before_answer (F5): an answer or clarify before any search."""
        return (self.config.agent.require_search_before_answer and canonical in (ActionType.ANSWER, ActionType.CLARIFY)
                and not run.searched and self._can_search())

    def _act_search_required(self, run: _Run, agent_resp: Dict[str, Any]) -> None:
        """The draft action becomes an observation; it costs a step but no tool call."""
        run.ledger.audit_events.append({"event": "search_required_notice", "action": agent_resp.get("action")})
        search_tool = self.profile.model_action_name(ActionType.SEARCH)
        self._observe(run, agent_resp, {"status": "search_required",
                                        "message": self.profile.messages.search_first_required.format(search_tool=search_tool)})

    def _refuse_search_required(self, run: _Run, canonical: ActionType) -> bool:
        """When require_search_before_answer is enabled, intercept premature refuse before any search/read tool call."""
        return (
            self.config.agent.require_search_before_answer
            and canonical is ActionType.REFUSE
            and not run.searched
            and len(run.ledger.retrieved_article_ids) == 0
            and not run.refuse_search_prompted
            and self._can_search()
            and run.ledger.can_call_tool()
            and run.ledger.can_step()
        )

    def _act_refuse_search_required(self, run: _Run, agent_resp: Dict[str, Any]) -> None:
        """The premature refuse draft becomes an observation telling the controller to search first."""
        run.refuse_search_prompted = True
        run.ledger.audit_events.append({"event": "search_required_notice", "action": agent_resp.get("action")})
        search_tool = self.profile.model_action_name(ActionType.SEARCH)
        message = (
            f"[YÊU_CẦU_TRA_CỨU] Bạn chưa thực hiện tra cứu cơ sở tri thức đã nạp. Hãy gọi `{search_tool}` "
            f"ít nhất một lần để tìm kiếm văn bản liên quan trước khi kết luận rằng không có căn cứ hoặc từ chối."
        )
        self._observe(run, agent_resp, {"status": "search_required", "message": message})

    @staticmethod
    def _assistant_turn(run: _Run, agent_resp: Dict[str, Any]) -> None:
        run.messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})

    def _observe(self, run: _Run, agent_resp: Dict[str, Any], observation: Dict[str, Any]) -> None:
        self._assistant_turn(run, agent_resp)
        run.messages.append({"role": "user", "content": OBSERVATION_PREFIX + json.dumps(observation, ensure_ascii=False)})

    def _tool_budget_spent(self, run: _Run, agent_resp: Dict[str, Any], template: str) -> bool:
        """When no tool call is left: tell the model to answer or refuse (and refuse for it on the last step)."""
        ledger = run.ledger
        if ledger.can_call_tool():
            return False
        self._assistant_turn(run, agent_resp)
        run.messages.append({"role": "user", "content": template.format(max_tool_calls=self.max_tool_calls)})
        if ledger.step_count >= self.max_steps - 1:
            self._refuse(ledger, self.profile.messages.tool_budget_exhausted.format(max_tool_calls=self.max_tool_calls),
                         source="budget")
        return True

    def _act_search(self, run: _Run, agent_resp: Dict[str, Any], tool_args: Dict[str, Any]) -> None:
        ledger, messages = run.ledger, self.profile.messages
        if self._tool_budget_spent(run, agent_resp, messages.tool_budget_search):
            return
        search_tool = self.profile.model_action_name(ActionType.SEARCH)
        read_tool = self.profile.model_action_name(ActionType.READ)

        retrieval = self.config.retrieval
        model_query = str(tool_args.get("query") or run.query)
        try:
            top_k = int(tool_args.get("top_k", retrieval.default_top_k))
        except (ValueError, TypeError):
            top_k = retrieval.default_top_k
        top_k = max(1, min(top_k, retrieval.final_top_k))

        # retrieval.first_search_anchor (F1): the first search of the run is the user's question plus the model's words.
        anchored = (not run.searched) and retrieval.first_search_anchor == "question_plus_query"
        run.searched = True
        query = anchor_query(run.query, model_query) if anchored else model_query
        self._emit_run_event("tool_started", tool=search_tool, query=query)

        query_key = " ".join(query.lower().split())
        if query_key in run.search_history:
            tool_res = {"status": "duplicate_query", "article_ids": run.search_history[query_key],
                        "message": messages.duplicate_query.format(read_tool=read_tool)}
            search_meta = None
            if self.config.agent.free_duplicate_notices:
                # F8: the notice repeats what is already in the context; it costs a step, not a tool call.
                ledger.audit_events.append({"event": "free_notice", "kind": "duplicate_query", "tool": search_tool,
                                            "args": tool_args})
                self._observe(run, agent_resp, self._search_hints(ledger, tool_res, read_tool))
                return
        else:
            try:
                tool_res, search_meta = self._search_with_metadata(query, top_k)
            except ModelComponentError as exc:
                # Reranker (or index embedding) failure: an execution error recorded in the ledger, never a
                # silent return of the first-stage order.
                ledger.record_tool_call(search_tool, tool_args, messages.component_error_summary.format(kind=exc.kind))
                ledger.audit_events[-1]["error"] = {"kind": exc.kind, "type": type(exc).__name__, "message": str(exc)}
                self._finish(ledger, "error", self._error_output(str(exc), exc.kind))
                return
            hit_ids = [a["article_id"] for a in tool_res.get("articles", [])]
            run.search_history[query_key] = hit_ids
            if anchored:
                # a later repeat of the model's own query is a repeat of what it already got
                run.search_history.setdefault(" ".join(model_query.lower().split()), hit_ids)
                tool_res = {**tool_res, "search_note": messages.first_search_anchor_note.format(model_query=model_query)}

        articles = tool_res.get("articles", [])
        for article in articles:
            CaseLedgerManager.add_retrieved_article(ledger, article["article_id"], article["content_snippet"])
        CaseLedgerManager.add_query(ledger, query)
        ledger.record_tool_call(search_tool, tool_args, messages.search_summary.format(count=len(articles)))
        if anchored:
            ledger.audit_events[-1]["query_anchor"] = {"mode": retrieval.first_search_anchor, "model_query": model_query,
                                                       "searched_query": query}
        if search_meta:
            ledger.audit_events[-1]["metadata"] = search_meta   # ledger only; not in the model-visible observation
        self._emit_run_event("tool_completed", tool=search_tool,
                             article_ids=[str(a.get("article_id", "")) for a in articles if a.get("article_id")],
                             result_count=len(articles))
        self._observe(run, agent_resp, self._search_hints(ledger, tool_res, read_tool))

    def _search_hints(self, ledger: CaseLedger, tool_res: Dict[str, Any], read_tool: str) -> Dict[str, Any]:
        """tools.search_hints (F3): `tool_calls_remaining` and, for a result with hits, how many are truncated and what to do about it.
        Off (default): the observation is returned unchanged."""
        if not self.config.tools.search_hints:
            return tool_res
        out = dict(tool_res)
        out["tool_calls_remaining"] = max(0, ledger.max_tool_calls - ledger.tool_calls_count)
        articles = tool_res.get("articles") or []
        if articles:
            truncated = sum(1 for a in articles if a.get("snippet_truncated"))
            messages = self.profile.messages
            out["hint"] = (messages.search_hint_truncated.format(truncated=truncated, count=len(articles), read_tool=read_tool)
                           if truncated else messages.search_hint_complete.format(count=len(articles)))
        return out

    def _act_read(self, run: _Run, agent_resp: Dict[str, Any], tool_args: Dict[str, Any]) -> None:
        ledger, messages = run.ledger, self.profile.messages
        if self._tool_budget_spent(run, agent_resp, messages.tool_budget_read):
            return
        read_tool = self.profile.model_action_name(ActionType.READ)

        doc_id = str(tool_args.get("article_id") or "")
        self._emit_run_event("tool_started", tool=read_tool, requested_id=doc_id)
        if doc_id.lower() in run.fully_read:
            tool_res = {"status": "already_read", "article_id": doc_id, "message": messages.already_read}
            if self.config.agent.free_duplicate_notices:
                # F8: a notice about text already in the context costs a step, not a tool call.
                ledger.audit_events.append({"event": "free_notice", "kind": "already_read", "tool": read_tool,
                                            "args": tool_args})
                self._observe(run, agent_resp, tool_res)
                return
        else:
            tool_res = self._read(doc_id)
            if tool_res.get("status") == "success":
                CaseLedgerManager.add_retrieved_article(ledger, doc_id, tool_res.get("full_content", ""))
                run.fully_read.add(doc_id.lower())

        found = tool_res.get("status") == "success"
        ledger.record_tool_call(read_tool, tool_args, messages.read_status.format(status=tool_res.get("status")))
        self._emit_run_event("tool_completed", tool=read_tool, article_ids=[doc_id] if found else [],
                             result_count=1 if found else 0)
        self._observe(run, agent_resp, tool_res)

    def _act_answer(self, run: _Run, agent_resp: Dict[str, Any], tool_args: Dict[str, Any]) -> None:
        ledger = run.ledger
        answer = str(tool_args.get("content") or "")
        citations = parse_model_citations(self.profile, tool_args.get("citations", []))

        # Evidence verification (decoupled pipeline: off | L1 | L1 + L2, plus the optional NLI step)
        result = self.verification_pipeline.verify(answer_text=answer, citations=citations,
                                                   retrieved_article_ids=ledger.retrieved_article_ids)
        if getattr(result, "nli_result", None) is not None:
            ledger.audit_events.append({"event": "nli_check", "metadata": {"nli": result.nli_result}})
        self._emit_run_event("verification_completed", mode=result.mode, passed=bool(result.is_valid))
        # verifier.l1_sentence_support: warn -> findings that did not reject the answer are kept in the ledger and the result
        warnings = list(getattr(getattr(result, "grounding_result", None), "warnings", None) or [])
        if warnings:
            ledger.audit_events.append({"event": "l1_warning", "metadata": {"warnings": warnings}})

        verified = self.verification_mode != OFF
        if result.is_valid:
            citations_out = dump_citations(citations)
            output = {"action": "answer", "content": answer, "citations": citations_out, "verified": verified}
            if warnings:
                output["verification_warnings"] = warnings
            self._finish(ledger, "answered", output)
            # Persisted only when verified without warnings, and only with the native model calls that produced the answer.
            if not warnings:
                self.answer_memory.remember(ledger, run.session_id, run.query, answer, citations_out, verified=verified,
                                            native_inference=isinstance(self.llm_client, NativeLLMClient))
        elif ledger.can_repair():
            # Targeted self-repair: the verifier's feedback goes back to the model.
            ledger.record_repair(result.repair_feedback)
            self._emit_run_event("repair_started", attempt=ledger.repairs_count)
            self._assistant_turn(run, agent_resp)
            run.messages.append({"role": "user", "content": self._repair_message(result.repair_feedback)})
        else:
            # Self-repair budget exhausted -> refuse decisively.
            self._refuse(ledger, self.profile.messages.repair_exhausted.format(
                max_repairs=self.max_repairs, repair_feedback=result.repair_feedback), source="repair_exhausted")

    def _repair_message(self, repair_feedback: Optional[str]) -> str:
        """verifier.repair_feedback_style: v1 = the profile's repair prompt (a user turn, as in the frozen v3 runs);
        verifier_report = a labelled automatic report that offers fixing the flagged item before refusing (F6)."""
        if self.config.verifier.repair_feedback_style == "verifier_report":
            return self.profile.messages.repair_report.format(
                repair_feedback=repair_feedback, read_tool=self.profile.model_action_name(ActionType.READ))
        return self.profile.repair_prompt.format(repair_feedback=repair_feedback)

    def _act_clarify_or_refuse(self, run: _Run, agent_resp: Dict[str, Any], canonical: ActionType,
                               tool_args: Dict[str, Any]) -> None:
        """The model's own text is required, never a default message."""
        field_name = "question" if canonical is ActionType.CLARIFY else "reason"
        text = tool_args.get(field_name)
        if not isinstance(text, str) or not text.strip():
            self._finish(run.ledger, "error", self._error_output(f"Action requires a nonempty {field_name}.",
                                                                 "model_output_error"))
            return
        self._finish(run.ledger, "clarified" if canonical is ActionType.CLARIFY else "refused",
                     {"action": agent_resp["action"], field_name: text, "citations": []}, refusal_source="model")


LocalSLMAgent = LuatCheckAgent
