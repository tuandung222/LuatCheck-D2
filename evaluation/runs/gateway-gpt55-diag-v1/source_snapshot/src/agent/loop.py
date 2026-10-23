"""
LuatCheck Budgeted ReAct Agent Loop.

Finite-State Machine (FSM) control loop with strict execution budgets
and multi-tier evidence verification (Lexical Grounding & Semantic NLI).
"""
import json
import time
import requests
import re
from typing import Callable, Dict, Any, Optional, List, Tuple, Literal

from src.agent.state import ActionType, AgentAction, CaseLedger, Citation
from src.agent.prompts import SYSTEM_PROMPT, REPAIR_PROMPT_TEMPLATE
from src.tools.legal_tools import LegalToolRegistry
from src.verifier.lexical_grounding import LexicalGroundingVerifier
from src.verifier.semantic_nli import SemanticNLIVerifier
from src.verifier.pipeline import VerificationPipeline
from src.memory.ledger import CaseLedgerManager
from src.memory.sqlite_store import SQLiteEpisodicStore
from src.security.guardrails import SecurityGuardrails
from src.security.audit_logger import AuditLogger
from src.config.app_config import AppConfig, load_config
from src.interfaces.base import BaseRetriever, BaseLLMClient, BaseVerifier
from src.agent.llm_client import (
    OllamaLLMClient,
    LlamaCppLLMClient,
    MlxVlmLLMClient,
    GatewayLLMClient,
    NativeLLMClient,
    InferenceError
)


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
        # DATA SCIENTIST EXTENSION HOOKS (Dependency Injection)
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
        event_sink: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        # 1. Load centralized configuration from AppConfig or config.yaml
        self.config = config or load_config()
        self.model_name = model_name or self.config.model.name
        self.ollama_url = ollama_url or self.config.model.endpoint
        self.corpus_path = corpus_path or self.config.retrieval.corpus_path
        self.l2_use_slm = l2_use_slm if l2_use_slm is not None else self.config.verifier.l2_use_slm

        # 2. Execution budgets
        self.max_tool_calls = max_tool_calls if max_tool_calls is not None else self.config.budgets.max_tool_calls
        self.max_repairs = max_repairs if max_repairs is not None else self.config.budgets.max_repairs
        self.max_steps = max_steps if max_steps is not None else self.config.budgets.max_steps
        self.outbox_path = outbox_path or self.config.security.outbox_path
        self.event_sink = event_sink

        # 3. Verification mode configuration
        chosen_mode = verification_mode if verification_mode is not None else self.config.verifier.mode
        if enable_verification is False:
            self.verification_mode = "off"
        elif enable_verification is True and chosen_mode == "off":
            self.verification_mode = "lexical_grounding"
        else:
            self.verification_mode = chosen_mode

        if self.verification_mode not in self.VALID_MODES:
            raise ValueError(
                f"Chế độ verification_mode '{self.verification_mode}' không hợp lệ. "
                f"Bắt buộc phải là một trong các giá trị: {sorted(list(self.VALID_MODES))}"
            )

        self.enable_verification = (self.verification_mode != "off")

        # 4. Dependency Injection for Tool Registry & Retriever
        if tool_registry is not None:
            self.tool_registry = tool_registry
        elif retriever:
            self.tool_registry = LegalToolRegistry(
                corpus_path=self.corpus_path,
                outbox_path=self.outbox_path,
                retriever=retriever
            )
        else:
            self.tool_registry = LegalToolRegistry(
                corpus_path=self.corpus_path,
                outbox_path=self.outbox_path,
                dense_endpoint=self.ollama_url,
                retrieval_mode=self.config.retrieval.dense_model_type,
                rrf_k=self.config.retrieval.rrf_k
            )

        # 5. Dependency Injection for Verification Pipeline & Verifiers
        corpus_data = getattr(self.tool_registry.retriever, "corpus", [])
        if verification_pipeline:
            self.verification_pipeline = verification_pipeline
            self.lexical_verifier = getattr(verification_pipeline, "lexical_verifier", verification_pipeline.verifier)
            self.semantic_verifier = getattr(verification_pipeline, "semantic_verifier", verification_pipeline.l2_verifier)
        else:
            self.lexical_verifier = lexical_grounding_verifier or verifier or LexicalGroundingVerifier(
                corpus_data, overlap_threshold=self.config.verifier.l1_overlap_threshold)
            self.semantic_verifier = semantic_nli_verifier or l2_verifier or SemanticNLIVerifier(
                corpus_data,
                entailment_threshold=self.config.verifier.l2_entailment_threshold,
                ollama_url=self.ollama_url,
                model_name=self.model_name,
                use_slm=self.l2_use_slm
            )
            self.verification_pipeline = VerificationPipeline(
                lexical_verifier=self.lexical_verifier,
                semantic_verifier=self.semantic_verifier,
                mode=self.verification_mode
            )
        self.verifier = self.lexical_verifier
        self.l2_verifier = self.semantic_verifier

        # 6. Dependency Injection for Memory & Logger
        self.sqlite_store = sqlite_store or SQLiteEpisodicStore(
            db_path=self.config.memory.sqlite_path,
            index_version=self.config.memory.index_version
        )
        self.audit_logger = audit_logger or AuditLogger(log_path=self.config.security.audit_log_path)
        self.ledger: Optional[CaseLedger] = None

        # 7. Dependency Injection for LLM Client (Decoupled Inference Engine)
        native_options = dict(model_name=self.model_name, temperature=self.config.model.temperature,
                              timeout_seconds=self.config.model.timeout_seconds, seed=self.config.model.seed,
                              max_output_tokens=self.config.model.max_output_tokens,
                              context_tokens=self.config.model.context_tokens)
        if llm_client:
            self.llm_client = llm_client
        elif self.config.model.provider == "gateway":
            if not self.config.model.api_key_env:
                raise ValueError("Gateway provider requires model.api_key_env.")
            self.llm_client = GatewayLLMClient(endpoint=self.ollama_url, api_key_env=self.config.model.api_key_env,
                                               reasoning_effort=self.config.model.reasoning_effort, **native_options)
        elif self.config.model.provider == "mlx":
            sampling = {k: v for k, v in (("top_p", self.config.model.top_p), ("top_k", self.config.model.top_k),
                                          ("min_p", self.config.model.min_p),
                                          ("presence_penalty", self.config.model.presence_penalty)) if v is not None}
            self.llm_client = MlxVlmLLMClient(endpoint=self.ollama_url, sampling=sampling,
                                              constrained_json=self.config.model.constrained_json, **native_options)
        elif self.config.model.provider in ["llamacpp", "llama.cpp", "openai", "prism", "prism_llamacpp", "prism-llamacpp", "prismml"]:
            self.llm_client = LlamaCppLLMClient(endpoint=self.ollama_url, **native_options)
        elif self.config.model.provider == "ollama":
            self.llm_client = OllamaLLMClient(endpoint=self.ollama_url, **native_options)
        else:
            raise ValueError("Unsupported provider; native inference is required.")

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

    def run(self, user_query: str, pasted_doc: Optional[str] = None, session_id: Optional[str] = None) -> CaseLedger:
        try:
            ledger = self._run_inner(user_query, pasted_doc, session_id)
            self._emit_run_event("run_finished", terminal_status=ledger.terminal_status)
            return ledger
        except InferenceError as exc:
            # This also covers an explicitly enabled native verification judge.
            ledger = self.ledger
            if ledger is None:
                raise
            ledger.is_terminal = True
            ledger.terminal_status = "error"
            ledger.final_output = {"action": "error", "reason": str(exc), "error_kind": exc.kind,
                                   "citations": [], "verified": False}
            self.audit_logger.log_event(ledger.session_id, "inference_error", ledger.final_output)
            self._emit_run_event("run_finished", terminal_status="error", error_kind=exc.kind)
            return ledger

    def _run_inner(self, user_query: str, pasted_doc: Optional[str] = None, session_id: Optional[str] = None) -> CaseLedger:
        start_time = time.time()
        sid = session_id or f"session_{int(time.time() * 1000)}"
        ledger = CaseLedgerManager.create_session(sid, user_query, [pasted_doc] if pasted_doc else [])
        ledger.max_tool_calls = self.max_tool_calls
        ledger.max_repairs = self.max_repairs
        ledger.max_steps = self.max_steps
        ledger.deadline_monotonic = time.monotonic() + self.config.budgets.wall_seconds
        self.ledger = ledger
        self._emit_run_event("run_started")

        # 1. Security Guardrails Check
        is_safe, safety_msg = SecurityGuardrails.check_input_safety(user_query, pasted_doc)
        if not is_safe:
            ledger.is_terminal = True
            ledger.terminal_status = "refused"
            ledger.final_output = {
                "action": "refuse",
                "pre_model_policy_refusal": True,
                "reason": safety_msg,
                "citations": []
            }
            self.audit_logger.log_event(sid, "security_refusal", {"query": user_query, "reason": safety_msg})
            return ledger

        # 2. Episodic Store Check & Cache Re-Verification
        cached_case = (self.sqlite_store.retrieve_similar_case(user_query, threshold=self.config.memory.similarity_threshold)
                       if self.config.memory.enabled else None)
        if cached_case and not self.sqlite_store.has_native_evidence(cached_case):
            self.audit_logger.log_event(sid, "cache_untrusted_origin", {"case_id": cached_case.get("case_id")})
            cached_case = None
        if cached_case:
            # 2.1 Reconstruct retrieved articles list
            raw_article_ids = cached_case.get("article_ids", "")
            if isinstance(raw_article_ids, str):
                cached_article_ids = [aid.strip() for aid in raw_article_ids.split(",") if aid.strip()]
            elif isinstance(raw_article_ids, (list, tuple, set)):
                cached_article_ids = [str(aid).strip() for aid in raw_article_ids if str(aid).strip()]
            else:
                cached_article_ids = []

            # Normalize citations to Citation objects for L1 verifier
            raw_citations = cached_case.get("citations", [])
            cached_citations = [
                Citation(**c) if isinstance(c, dict) else Citation(article_id=str(c))
                for c in raw_citations
            ]

            # Append citation article_ids to retrieved list if missing
            for c in cached_citations:
                if c.article_id and c.article_id not in cached_article_ids:
                    cached_article_ids.append(c.article_id)

            # Populate ledger short-term working memory
            for aid in cached_article_ids:
                art = self.tool_registry.retriever.get_article_by_id(aid)
                content = art.get("content", "") if art else ""
                CaseLedgerManager.add_retrieved_article(ledger, aid, content)

            # 2.2 Re-verify L1 & L2 legal evidence before reuse (Cache Re-Verification)
            is_cache_valid = True
            cache_feedback = None
            norm_cache_mode = self.verification_pipeline._normalize_mode(self.verification_mode)

            if norm_cache_mode == "lexical_grounding":
                l1_res = self.verifier.verify(
                    answer_text=cached_case["answer"],
                    citations=cached_citations,
                    retrieved_article_ids=ledger.retrieved_article_ids
                )
                if not l1_res.is_valid:
                    is_cache_valid = False
                    cache_feedback = l1_res.repair_feedback

            elif norm_cache_mode == "semantic_entailment":
                l1_res = self.verifier.verify(
                    answer_text=cached_case["answer"],
                    citations=cached_citations,
                    retrieved_article_ids=ledger.retrieved_article_ids
                )
                if not l1_res.is_valid:
                    is_cache_valid = False
                    cache_feedback = l1_res.repair_feedback
                else:
                    cit_ids = [c.article_id for c in cached_citations]
                    l2_res = self.l2_verifier.verify_all_claims(cached_case["answer"], cit_ids)
                    if not l2_res.get("is_entailed", False):
                        is_cache_valid = False
                        failed_claims = l2_res.get("failed_claims", [])
                        failed_sentences = [f["sentence"] for f in failed_claims]
                        cache_feedback = (
                            f"L2 SEMANTIC VERIFIER REJECTED (Cache): Phát hiện {len(failed_sentences)} câu khẳng định "
                            f"chưa đạt căn cứ kéo theo ngữ nghĩa:\n"
                            + "\n".join(f"- \"{s}\"" for s in failed_sentences[:2])
                        )

            # 2.3 Process cache re-verification result
            if is_cache_valid:
                ledger.is_terminal = True
                ledger.terminal_status = "answered"
                ledger.final_output = {
                    "action": "answer",
                    "content": cached_case["answer"],
                    "citations": [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in cached_citations],
                    "from_cache": True,
                    "verified": (self.verification_mode != "off")
                }
                elapsed_ms = (time.time() - start_time) * 1000
                self.audit_logger.log_event(
                    sid,
                    "cache_hit",
                    {
                        "case_id": cached_case.get("case_id"),
                        "verified": True,
                        "article_ids": ledger.retrieved_article_ids,
                        "citations_count": len(cached_citations)
                    },
                    latency_ms=elapsed_ms
                )
                return ledger
            else:
                # If cache re-verification fails: log warning and fall back to regular ReAct loop
                self.audit_logger.log_event(
                    sid,
                    "cache_verification_failed",
                    {
                        "case_id": cached_case.get("case_id"),
                        "feedback": cache_feedback
                    }
                )
                # Clear temporary retrieved state so ReAct loop starts fresh
                ledger.retrieved_article_ids = []
                ledger.retrieved_articles_cache = {}

        # 3. Prepare context for LLM
        wrapped_input = SecurityGuardrails.wrap_untrusted_input(user_query, pasted_doc)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": wrapped_input}
        ]

        # 4. Budgeted ReAct Loop
        while not ledger.is_terminal:
            if time.monotonic() >= ledger.deadline_monotonic:
                ledger.is_terminal = True
                ledger.terminal_status = "error"
                ledger.final_output = {"action": "error", "reason": "Task wall-clock budget exhausted.", "error_kind": "wall_timeout", "citations": []}
                break
            # 1. Step Budget Invariant Check
            if not ledger.can_step():
                ledger.is_terminal = True
                ledger.terminal_status = "refused"
                ledger.final_output = {
                    "action": "refuse",
                    "reason": f"Hệ thống đã sử dụng hết giới hạn tối đa {self.max_steps} bước suy luận mà chưa có kết luận.",
                    "citations": []
                }
                break

            ledger.record_step()
            self._emit_run_event("model_call_started", step=ledger.step_count)

            try:
                agent_resp = self._call_llm(messages, ledger=ledger)
                if time.monotonic() >= ledger.deadline_monotonic:
                    raise InferenceError("Task wall-clock budget exhausted during inference.", "wall_timeout")
            except InferenceError as exc:
                ledger.is_terminal = True
                ledger.terminal_status = "error"
                ledger.final_output = {"action": "error", "reason": str(exc), "error_kind": exc.kind, "citations": [], "verified": False}
                break
            # Native clients validate the action contract; any other response is an
            # execution error, never a substitute refusal.
            valid_actions = {a.value for a in ActionType}
            if (not isinstance(agent_resp, dict) or agent_resp.get("action") not in valid_actions
                    or not isinstance(agent_resp.get("tool_args"), dict)):
                ledger.is_terminal = True
                ledger.terminal_status = "error"
                ledger.final_output = {"action": "error", "reason": "Model returned an invalid or missing action.",
                                       "error_kind": "model_output_error", "citations": [], "verified": False}
                break

            action = agent_resp["action"]
            tool_args = agent_resp["tool_args"]

            # Dispatch action
            if action == ActionType.SEARCH_LAW.value:
                if not ledger.can_call_tool():
                    # Tool budget exhausted -> prompt model to switch to answer or refuse
                    messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                    messages.append({"role": "user", "content": f"[LỖI_NGÂN_SÁCH] Đã sử dụng tối đa {self.max_tool_calls} lượt gọi công cụ. Bạn KHÔNG ĐƯỢC gọi thêm công cụ nữa. Hãy chuyển sang hành động 'answer' nếu đã đủ tài liệu, hoặc 'refuse' nếu chưa đủ căn cứ."})
                    if ledger.step_count >= self.max_steps - 1:
                        ledger.is_terminal = True
                        ledger.terminal_status = "refused"
                        ledger.final_output = {
                            "action": "refuse",
                            "reason": f"Hệ thống đã sử dụng hết ngân sách {self.max_tool_calls} lượt gọi công cụ.",
                            "citations": []
                        }
                    continue

                q = str(tool_args.get("query") or user_query)
                raw_top_k = tool_args.get("top_k", 3)
                try:
                    top_k = int(raw_top_k)
                except (ValueError, TypeError):
                    top_k = 3
                top_k = max(1, min(top_k, self.config.retrieval.final_top_k))

                tool_res = self.tool_registry.search_law(q, top_k=top_k)
                
                # Cache into ledger working memory
                for art in tool_res.get("articles", []):
                    CaseLedgerManager.add_retrieved_article(ledger, art["article_id"], art["content_snippet"])
                CaseLedgerManager.add_query(ledger, q)

                ledger.record_tool_call("search_law", tool_args, f"Tìm thấy {len(tool_res.get('articles', []))} điều luật")
                self._emit_run_event(
                    "tool_completed",
                    tool="search_law",
                    article_ids=[str(article.get("article_id", "")) for article in tool_res.get("articles", []) if article.get("article_id")],
                    result_count=len(tool_res.get("articles", [])),
                )
                messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                messages.append({"role": "user", "content": f"[OBSERVATION_TOOL_RESULT]\n{json.dumps(tool_res, ensure_ascii=False)}"})

            elif action == ActionType.GET_ARTICLE.value:
                if not ledger.can_call_tool():
                    messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                    messages.append({"role": "user", "content": f"[LỖI_NGÂN_SÁCH] Đã sử dụng tối đa {self.max_tool_calls} lượt gọi công cụ. Bạn KHÔNG ĐƯỢC gọi thêm công cụ nữa. Hãy chuyển sang hành động 'answer' hoặc 'refuse'."})
                    if ledger.step_count >= self.max_steps - 1:
                        ledger.is_terminal = True
                        ledger.terminal_status = "refused"
                        ledger.final_output = {
                            "action": "refuse",
                            "reason": f"Hệ thống đã sử dụng hết ngân sách {self.max_tool_calls} lượt gọi công cụ.",
                            "citations": []
                        }
                    continue

                aid = str(tool_args.get("article_id") or "")
                tool_res = self.tool_registry.get_article(aid)
                if tool_res.get("status") == "success":
                    CaseLedgerManager.add_retrieved_article(ledger, aid, tool_res.get("full_content", ""))
                
                ledger.record_tool_call("get_article", tool_args, f"Trạng thái: {tool_res.get('status')}")
                self._emit_run_event("tool_completed", tool="get_article", article_ids=[aid] if tool_res.get("status") == "success" else [], result_count=1 if tool_res.get("status") == "success" else 0)
                messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                messages.append({"role": "user", "content": f"[OBSERVATION_TOOL_RESULT]\n{json.dumps(tool_res, ensure_ascii=False)}"})

            elif action == ActionType.ANSWER.value:
                answer_content = str(tool_args.get("content") or "")
                raw_citations = tool_args.get("citations", [])
                if not isinstance(raw_citations, list):
                    raw_citations = []
                citations = []
                for c in raw_citations:
                    if isinstance(c, dict):
                        try:
                            citations.append(Citation(**c))
                        except Exception:
                            aid = str(c.get("article_id") or "")
                            if aid:
                                citations.append(Citation(article_id=aid))
                    elif isinstance(c, str) and c.strip():
                        citations.append(Citation(article_id=c.strip()))

                # STATUTORY EVIDENCE VERIFICATION STEP (DECOUPLED VERIFICATION PIPELINE)
                v_res = self.verification_pipeline.verify(
                    answer_text=answer_content,
                    citations=citations,
                    retrieved_article_ids=ledger.retrieved_article_ids
                )
                verif_valid = v_res.is_valid
                repair_feedback = v_res.repair_feedback
                self._emit_run_event("verification_completed", mode=v_res.mode, passed=bool(verif_valid))

                if verif_valid:
                    ledger.is_terminal = True
                    ledger.terminal_status = "answered"
                    # Preserve objective retrieval order without scrambling list
                    citations_dicts = [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in citations]
                    ledger.final_output = {
                        "action": "answer",
                        "content": answer_content,
                        "citations": citations_dicts,
                        "verified": (self.verification_mode != "off")
                    }
                    # Save to SQLite Episodic Store (persisted only when verified)
                    if self.config.memory.enabled and self.verification_mode != "off" and isinstance(self.llm_client, NativeLLMClient) and ledger.llm_calls:
                        evidence = [{"backend": call.get("backend"), "outcome": call.get("outcome"),
                                     "requested_model": call.get("requested_model"), "request_sha256": call.get("request_sha256"),
                                     "action": call.get("response", {}).get("action")}
                                    for call in ledger.llm_calls]
                        self.sqlite_store.write_if_verified(
                            case_id=sid,
                            query=user_query,
                            answer=answer_content,
                            citations=citations_dicts,
                            is_l1_verified=True,
                            native_evidence=evidence
                        )
                else:
                    # Handle verification failure -> Trigger Targeted Self-Repair
                    if ledger.can_repair():
                        ledger.record_repair(repair_feedback)
                        self._emit_run_event("repair_started", attempt=ledger.repairs_count)
                        repair_prompt = REPAIR_PROMPT_TEMPLATE.format(repair_feedback=repair_feedback)
                        messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                        messages.append({"role": "user", "content": repair_prompt})
                    else:
                        # Self-repair budget exhausted -> Fallback decisively to Refuse
                        ledger.is_terminal = True
                        ledger.terminal_status = "refused"
                        ledger.final_output = {
                            "action": "refuse",
                            "reason": f"Không thể xác thực căn cứ pháp lý sau {self.max_repairs} lần thử sửa chữa. Chi tiết vi phạm: {repair_feedback}",
                            "citations": []
                        }

            else:
                # clarify / refuse: the model's own text is required, never a default message.
                field = "question" if action == ActionType.CLARIFY.value else "reason"
                text = tool_args.get(field)
                ledger.is_terminal = True
                if not isinstance(text, str) or not text.strip():
                    ledger.terminal_status = "error"
                    ledger.final_output = {"action": "error", "reason": f"Action requires a nonempty {field}.",
                                           "error_kind": "model_output_error", "citations": [], "verified": False}
                else:
                    ledger.terminal_status = "clarified" if action == ActionType.CLARIFY.value else "refused"
                    ledger.final_output = {"action": action, field: text, "citations": []}

        elapsed_ms = (time.time() - start_time) * 1000
        self.audit_logger.log_event(
            sid,
            "session_completed",
            {
                "query": user_query,
                "terminal_status": ledger.terminal_status,
                "tool_calls": ledger.tool_calls_count,
                "repairs": ledger.repairs_count,
                "output": ledger.final_output
            },
            latency_ms=elapsed_ms
        )
        return ledger


LocalSLMAgent = LuatCheckAgent
