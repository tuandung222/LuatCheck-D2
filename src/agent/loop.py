"""
LuatCheck Budgeted ReAct Agent Loop
Vòng lặp suy luận - hành động có giới hạn ngân sách và xác thực căn cứ pháp lý L1 & L2
"""
import json
import time
import requests
import re
from typing import Dict, Any, Optional, List, Tuple, Literal

from src.agent.state import ActionType, AgentAction, CaseLedger, Citation
from src.agent.prompts import SYSTEM_PROMPT, REPAIR_PROMPT_TEMPLATE
from src.tools.legal_tools import LegalToolRegistry
from src.verifier.l1_deterministic import L1EvidenceVerifier
from src.verifier.l2_semantic import L2SemanticEntailmentVerifier
from src.memory.ledger import CaseLedgerManager
from src.memory.sqlite_store import SQLiteEpisodicStore
from src.security.guardrails import SecurityGuardrails
from src.security.audit_logger import AuditLogger
from src.config.app_config import AppConfig, load_config
from src.interfaces.base import BaseRetriever, BaseLLMClient, BaseVerifier
from src.agent.llm_client import OllamaLLMClient, MockRuleBasedLLMClient, CompositeLLMClient


class LuatCheckAgent:
    VALID_MODES = {"off", "l1", "l1_only", "l1_on", "l1_l2", "l1_l2_on"}

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
        sqlite_store: Optional[SQLiteEpisodicStore] = None,
        audit_logger: Optional[AuditLogger] = None,
        outbox_path: Optional[str] = None
    ):
        # 1. Nạp cấu hình tập trung từ AppConfig hoặc config.yaml
        self.config = config or load_config()
        self.model_name = model_name or self.config.model.name
        self.ollama_url = ollama_url or self.config.model.endpoint
        self.corpus_path = corpus_path or self.config.retrieval.corpus_path
        self.l2_use_slm = l2_use_slm if l2_use_slm is not None else self.config.verifier.l2_use_slm

        # 2. Ngân sách thực thi (Budgets)
        self.max_tool_calls = max_tool_calls if max_tool_calls is not None else self.config.budgets.max_tool_calls
        self.max_repairs = max_repairs if max_repairs is not None else self.config.budgets.max_repairs
        self.max_steps = max_steps if max_steps is not None else self.config.budgets.max_steps
        self.outbox_path = outbox_path or self.config.security.outbox_path

        # 3. Xử lý tương thích ngược giữa enable_verification và verification_mode
        chosen_mode = verification_mode if verification_mode is not None else self.config.verifier.mode
        if enable_verification is False:
            self.verification_mode = "off"
        elif enable_verification is True and chosen_mode == "off":
            self.verification_mode = "l1_only"
        else:
            self.verification_mode = chosen_mode

        if self.verification_mode not in self.VALID_MODES:
            raise ValueError(
                f"Chế độ verification_mode '{self.verification_mode}' không hợp lệ. "
                f"Bắt buộc phải là một trong các giá trị: {sorted(list(self.VALID_MODES))}"
            )

        self.enable_verification = (self.verification_mode != "off")

        # 4. Dependency Injection cho Tool Registry & Retriever
        if retriever:
            self.tool_registry = LegalToolRegistry(
                corpus_path=self.corpus_path,
                outbox_path=self.outbox_path,
                retriever=retriever
            )
        else:
            self.tool_registry = LegalToolRegistry(
                corpus_path=self.corpus_path,
                outbox_path=self.outbox_path
            )

        # 5. Dependency Injection cho Verifiers
        corpus_data = getattr(self.tool_registry.retriever, "corpus", [])
        self.verifier = verifier or L1EvidenceVerifier(corpus_data)
        self.l2_verifier = l2_verifier or L2SemanticEntailmentVerifier(
            corpus_data,
            entailment_threshold=self.config.verifier.l2_entailment_threshold,
            ollama_url=self.ollama_url,
            model_name=self.model_name,
            use_slm=self.l2_use_slm
        )

        # 6. Dependency Injection cho Memory & Logger
        self.sqlite_store = sqlite_store or SQLiteEpisodicStore(
            db_path=self.config.memory.sqlite_path,
            index_version=self.config.memory.index_version
        )
        self.audit_logger = audit_logger or AuditLogger(log_path=self.config.security.audit_log_path)
        self.ledger: Optional[CaseLedger] = None

        # 7. Dependency Injection cho LLM Client (Tách rời LLM Engine)
        self.mock_client = MockRuleBasedLLMClient(verification_mode=self.verification_mode)
        if llm_client:
            self.llm_client = llm_client
        else:
            self.llm_client = CompositeLLMClient(
                primary_client=OllamaLLMClient(
                    endpoint=self.ollama_url,
                    model_name=self.model_name,
                    temperature=self.config.model.temperature,
                    timeout_seconds=self.config.model.timeout_seconds
                ),
                fallback_client=self.mock_client
            )

    @classmethod
    def from_config(cls, config_path_or_obj: Any = "config/config.yaml", **kwargs) -> "LuatCheckAgent":
        """Factory method: Khởi tạo LuatCheckAgent trực tiếp từ cấu hình YAML hoặc AppConfig object."""
        if isinstance(config_path_or_obj, str):
            cfg = load_config(config_path_or_obj)
        elif isinstance(config_path_or_obj, AppConfig):
            cfg = config_path_or_obj
        else:
            cfg = load_config()
        return cls(config=cfg, **kwargs)

    @classmethod
    def default(cls) -> "LuatCheckAgent":
        """Factory method: Khởi tạo LuatCheckAgent với cấu hình mặc định chuẩn."""
        return cls.from_config()

    def _call_llm(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        """Ủy quyền sinh phản hồi cho LLM Client đã được mô-đun hóa."""
        return self.llm_client.generate(messages, ledger=ledger)

    def step(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        """Thực hiện một bước gọi mô hình suy luận và chuyển tiếp trạng thái ledger."""
        return self._call_llm(messages, ledger=ledger or self.ledger)

    def _rule_based_fallback(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Duy trì tương thích ngược cho các bài test hoặc caller gọi trực tiếp rule-based fallback."""
        return self.mock_client.generate(messages, ledger=self.ledger)


    def run(self, user_query: str, pasted_doc: Optional[str] = None, session_id: Optional[str] = None) -> CaseLedger:
        start_time = time.time()
        sid = session_id or f"session_{int(time.time() * 1000)}"
        ledger = CaseLedgerManager.create_session(sid, user_query, [pasted_doc] if pasted_doc else [])
        ledger.max_tool_calls = self.max_tool_calls
        ledger.max_repairs = self.max_repairs
        self.ledger = ledger

        # 1. Gác cổng an ninh (Security Guardrails Check)
        is_safe, safety_msg = SecurityGuardrails.check_input_safety(user_query, pasted_doc)
        if not is_safe:
            ledger.is_terminal = True
            ledger.terminal_status = "refused"
            ledger.final_output = {
                "action": "refuse",
                "reason": safety_msg,
                "citations": []
            }
            self.audit_logger.log_event(sid, "security_refusal", {"query": user_query, "reason": safety_msg})
            return ledger

        # 2. Kiểm tra bộ nhớ dài hạn (Episodic Store Check) & Tái xác thực Cache
        cached_case = self.sqlite_store.retrieve_similar_case(user_query)
        if cached_case:
            # 2.1 Phục hồi danh sách điều luật đã truy xuất
            raw_article_ids = cached_case.get("article_ids", "")
            if isinstance(raw_article_ids, str):
                cached_article_ids = [aid.strip() for aid in raw_article_ids.split(",") if aid.strip()]
            elif isinstance(raw_article_ids, (list, tuple, set)):
                cached_article_ids = [str(aid).strip() for aid in raw_article_ids if str(aid).strip()]
            else:
                cached_article_ids = []

            # Chuẩn hóa trích dẫn thành đối tượng Citation để L1 verifier có thể đọc
            raw_citations = cached_case.get("citations", [])
            cached_citations = [
                Citation(**c) if isinstance(c, dict) else Citation(article_id=str(c))
                for c in raw_citations
            ]

            # Bổ sung các article_id từ citations vào danh sách retrieved nếu chưa có
            for c in cached_citations:
                if c.article_id and c.article_id not in cached_article_ids:
                    cached_article_ids.append(c.article_id)

            # Nạp vào ledger short-term memory
            for aid in cached_article_ids:
                art = self.tool_registry.retriever.get_article_by_id(aid)
                content = art.get("content", "") if art else ""
                CaseLedgerManager.add_retrieved_article(ledger, aid, content)

            # 2.2 Tái xác thực căn cứ pháp lý L1 & L2 trước khi tái sử dụng (Cache Re-Verification)
            is_cache_valid = True
            cache_feedback = None

            if self.verification_mode in ["l1", "l1_only", "l1_on"]:
                l1_res = self.verifier.verify(
                    answer_text=cached_case["answer"],
                    citations=cached_citations,
                    retrieved_article_ids=ledger.retrieved_article_ids
                )
                if not l1_res.is_valid:
                    is_cache_valid = False
                    cache_feedback = l1_res.repair_feedback

            elif self.verification_mode in ["l1_l2", "l1_l2_on"]:
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

            # 2.3 Xử lý kết quả tái xác thực cache
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
                # Nếu xác thực thất bại: ghi log cảnh báo và Fallback sang vòng lặp ReAct bình thường
                self.audit_logger.log_event(
                    sid,
                    "cache_verification_failed",
                    {
                        "case_id": cached_case.get("case_id"),
                        "feedback": cache_feedback
                    }
                )
                # Dọn sạch danh sách retrieved tạm thời để ReAct loop bắt đầu truy xuất mới
                ledger.retrieved_article_ids = []
                ledger.retrieved_articles_cache = {}

        # 3. Chuẩn bị ngữ cảnh cho LLM
        wrapped_input = SecurityGuardrails.wrap_untrusted_input(user_query, pasted_doc)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": wrapped_input}
        ]

        # 4. Vòng lặp ReAct có ngân sách (Budgeted ReAct Loop)
        while not ledger.is_terminal:
            # 1. Kiểm tra giới hạn tổng số bước suy luận (Step Budget Invariant)
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

            agent_resp = self._call_llm(messages, ledger=self.ledger)
            if not isinstance(agent_resp, dict):
                agent_resp = {"action": "refuse", "tool_args": {"reason": "Phản hồi từ mô hình không đúng định dạng JSON."}}

            action = str(agent_resp.get("action", "refuse"))
            thought = str(agent_resp.get("thought", ""))
            tool_args = agent_resp.get("tool_args")
            if not isinstance(tool_args, dict):
                tool_args = {}

            # Xử lý các hành động
            if action == ActionType.SEARCH_LAW.value:
                if not ledger.can_call_tool():
                    # Đã hết ngân sách gọi tool -> nhắc nhở model chuyển sang answer hoặc refuse
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

                tool_res = self.tool_registry.search_law(q, top_k=top_k)
                
                # Lưu vào cache ledger
                for art in tool_res.get("articles", []):
                    CaseLedgerManager.add_retrieved_article(ledger, art["article_id"], art["content_snippet"])
                CaseLedgerManager.add_query(ledger, q)

                ledger.record_tool_call("search_law", tool_args, f"Tìm thấy {len(tool_res.get('articles', []))} điều luật")
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

                # BƯỚC XÁC THỰC CĂN CỨ PHÁP LÝ (3-WAY ABLATION CONTRACT)
                verif_valid = True
                repair_feedback = None

                if self.verification_mode == "off":
                    verif_valid = True
                    repair_feedback = None
                elif self.verification_mode in ["l1", "l1_only", "l1_on"]:
                    l1_res = self.verifier.verify(
                        answer_text=answer_content,
                        citations=citations,
                        retrieved_article_ids=ledger.retrieved_article_ids
                    )
                    verif_valid = l1_res.is_valid
                    repair_feedback = l1_res.repair_feedback
                elif self.verification_mode in ["l1_l2", "l1_l2_on"]:
                    l1_res = self.verifier.verify(
                        answer_text=answer_content,
                        citations=citations,
                        retrieved_article_ids=ledger.retrieved_article_ids
                    )
                    if not l1_res.is_valid:
                        verif_valid = False
                        repair_feedback = l1_res.repair_feedback
                    else:
                        cit_ids = [c.article_id for c in citations]
                        l2_res = self.l2_verifier.verify_all_claims(answer_content, cit_ids)
                        if not l2_res.get("is_entailed", False):
                            verif_valid = False
                            failed_claims = l2_res.get("failed_claims", [])
                            failed_sentences = [f["sentence"] for f in failed_claims]
                            repair_feedback = (
                                f"CẢNH BÁO XÁC THỰC L2 (Ngữ nghĩa): Phát hiện {len(failed_sentences)} câu khẳng định "
                                f"chưa đạt căn cứ kéo theo ngữ nghĩa (entailment score < {self.l2_verifier.entailment_threshold}):\n"
                                + "\n".join(f"- \"{s}\"" for s in failed_sentences[:2])
                            )
                        else:
                            verif_valid = True
                            repair_feedback = None

                if verif_valid:
                    ledger.is_terminal = True
                    ledger.terminal_status = "answered"
                    # Giữ nguyên thứ tự truy xuất khách quan, không xáo trộn danh sách retrieval
                    citations_dicts = [c.model_dump() if hasattr(c, "model_dump") else c.dict() for c in citations]
                    ledger.final_output = {
                        "action": "answer",
                        "content": answer_content,
                        "citations": citations_dicts,
                        "verified": (self.verification_mode != "off")
                    }
                    # Lưu vào SQLite Episodic Store (chỉ ghi khi kết quả được xác thực)
                    if self.verification_mode != "off":
                        self.sqlite_store.write_if_verified(
                            case_id=sid,
                            query=user_query,
                            answer=answer_content,
                            citations=citations_dicts,
                            is_l1_verified=True
                        )
                else:
                    # Xử lý khi xác thực L1/L2 thất bại -> Kích hoạt Targeted Repair
                    if ledger.can_repair():
                        ledger.record_repair(repair_feedback)
                        repair_prompt = REPAIR_PROMPT_TEMPLATE.format(repair_feedback=repair_feedback)
                        messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                        messages.append({"role": "user", "content": repair_prompt})
                    else:
                        # Đã hết ngân sách tự sửa chữa -> Fallback dứt khoát sang Refuse
                        ledger.is_terminal = True
                        ledger.terminal_status = "refused"
                        ledger.final_output = {
                            "action": "refuse",
                            "reason": f"Không thể xác thực căn cứ pháp lý sau {self.max_repairs} lần thử sửa chữa. Chi tiết vi phạm: {repair_feedback}",
                            "citations": []
                        }

            elif action == ActionType.CLARIFY.value:
                ledger.is_terminal = True
                ledger.terminal_status = "clarified"
                ledger.final_output = {
                    "action": "clarify",
                    "question": str(tool_args.get("question") or "Vui lòng làm rõ thêm chi tiết về tình huống của bạn."),
                    "citations": []
                }

            elif action == ActionType.REFUSE.value:
                ledger.is_terminal = True
                ledger.terminal_status = "refused"
                ledger.final_output = {
                    "action": "refuse",
                    "reason": str(tool_args.get("reason") or "Hệ thống từ chối trả lời vì không có căn cứ pháp luật rõ ràng."),
                    "citations": []
                }

            else:
                # Xử lý các action lạ/không hợp lệ (như {"action": "bogus"})
                ledger.audit_events.append({
                    "event": "invalid_action",
                    "action": action,
                    "step": ledger.step_count
                })
                if ledger.can_repair():
                    ledger.record_repair(f"Hành động '{action}' không hợp lệ.")
                    messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                    messages.append({"role": "user", "content": f"[LỖI_HÀNH_ĐỘNG] Hành động '{action}' không được hỗ trợ. Hãy chỉ chọn một trong các hành động: search_law, get_article, answer, clarify, refuse."})
                else:
                    ledger.is_terminal = True
                    ledger.terminal_status = "refused"
                    ledger.final_output = {
                        "action": "refuse",
                        "reason": f"Mô hình sinh hành động không hợp lệ '{action}' vượt quá giới hạn sửa chữa.",
                        "citations": []
                    }

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
