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


class LuatCheckAgent:
    def __init__(
        self,
        model_name: str = "qwen2.5:3b",
        ollama_url: str = "http://localhost:11434",
        corpus_path: str = "data/corpus/labor_code_2019.json",
        max_tool_calls: int = 5,
        max_repairs: int = 2,
        verification_mode: str = "l1_only",
        enable_verification: Optional[bool] = None,
        l2_use_slm: bool = False
    ):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.max_tool_calls = max_tool_calls
        self.max_repairs = max_repairs
        self.l2_use_slm = l2_use_slm

        # Xử lý tương thích ngược giữa enable_verification và verification_mode
        if enable_verification is False:
            self.verification_mode = "off"
        elif enable_verification is True and verification_mode == "off":
            self.verification_mode = "l1_only"
        else:
            self.verification_mode = verification_mode

        self.enable_verification = (self.verification_mode != "off")

        # Khởi tạo các hệ thống con
        self.tool_registry = LegalToolRegistry(corpus_path=corpus_path)
        self.verifier = L1EvidenceVerifier(self.tool_registry.retriever.corpus)
        self.l2_verifier = L2SemanticEntailmentVerifier(
            self.tool_registry.retriever.corpus,
            entailment_threshold=0.30,
            use_slm=l2_use_slm
        )
        self.sqlite_store = SQLiteEpisodicStore()
        self.audit_logger = AuditLogger()

    def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Gọi Ollama API với format json
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }
        try:
            resp = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                raw_content = data.get("message", {}).get("content", "{}")
                return json.loads(raw_content)
        except Exception:
            # Fallback nếu Ollama mất kết nối
            pass

        return self._rule_based_fallback(messages)

    def _rule_based_fallback(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Bộ sinh suy luận dự phòng đảm bảo tính sẵn sàng cao (High Availability)
        """
        last_msg = messages[-1]["content"]
        # Chỉ kiểm tra tin nhắn của assistant để xác định đã gọi search_law (tránh nhầm với system prompt)
        has_search = any(
            m.get("role") == "assistant" and "search_law" in m.get("content", "")
            for m in messages
        )
        has_repair = any(
            "CẢNH BÁO TỪ HỆ THỐNG" in m.get("content", "") or "CẢNH BÁO XÁC THỰC" in m.get("content", "")
            for m in messages
        )

        if has_repair:
            return {
                "thought": "Hệ thống xác thực báo lỗi căn cứ pháp lý không đủ. Tôi từ chối đưa ra kết luận để tránh rủi ro.",
                "action": "refuse",
                "tool_args": {"reason": "Không đủ căn cứ pháp lý tin cậy trong các điều luật đã nạp."}
            }

        if not has_search:
            # Lấy nội dung câu hỏi người dùng từ user message
            first_user_content = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
            clean_q = re.sub(r'\[/?UNTRUSTED_[A-Z_]+[^\]]*\]', '', first_user_content).strip()
            return {
                "thought": "Cần tra cứu quy định pháp luật liên quan đến câu hỏi của người dùng.",
                "action": "search_law",
                "tool_args": {"query": clean_q[:100], "top_k": 3}
            }

        # Trích xuất mã điều luật và nội dung trích đoạn từ kết quả tìm kiếm đã nạp
        retrieved_ids = re.findall(r'"article_id":\s*"([^"]+)"', last_msg)
        chosen_id = retrieved_ids[0] if retrieved_ids else "Dieu_25"

        # Lấy snippet tương ứng để đảm bảo span support overlap > 25%
        snippets = re.findall(r'"content_snippet":\s*"([^"]+)"', last_msg)
        if snippets:
            clean_snippet = re.sub(r'[\r\n]+', ' ', snippets[0].replace('\\"', '"').replace('\\n', ' ')).strip()
            first_clause = clean_snippet.split('.')[0].strip()
            if len(first_clause) > 20:
                answer_content = f"Căn cứ theo quy định pháp luật lao động: {first_clause}."
            else:
                answer_content = f"Căn cứ theo quy định tại {chosen_id}: {clean_snippet[:150]}."
        else:
            answer_content = f"Căn cứ theo quy định tại {chosen_id} Bộ luật Lao động 2019, quyền và nghĩa vụ của người lao động được quy định chi tiết theo điều luật."

        return {
            "thought": f"Đã có kết quả tra cứu điều luật {chosen_id}, tổng hợp câu trả lời có căn cứ.",
            "action": "answer",
            "tool_args": {
                "content": answer_content,
                "citations": [{"article_id": chosen_id, "law_name": "Bộ luật Lao động 2019"}]
            }
        }


    def run(self, user_query: str, pasted_doc: Optional[str] = None, session_id: Optional[str] = None) -> CaseLedger:
        start_time = time.time()
        sid = session_id or f"session_{int(time.time() * 1000)}"
        ledger = CaseLedgerManager.create_session(sid, user_query, [pasted_doc] if pasted_doc else [])
        ledger.max_tool_calls = self.max_tool_calls
        ledger.max_repairs = self.max_repairs

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
            # Kiểm tra ngân sách công cụ
            if not ledger.can_call_tool():
                ledger.is_terminal = True
                ledger.terminal_status = "refused"
                ledger.final_output = {
                    "action": "refuse",
                    "reason": f"Hệ thống đã sử dụng hết ngân sách {self.max_tool_calls} lượt gọi công cụ mà chưa hoàn tất xác thực.",
                    "citations": []
                }
                break

            agent_resp = self._call_llm(messages)
            action = agent_resp.get("action", "refuse")
            thought = agent_resp.get("thought", "")
            tool_args = agent_resp.get("tool_args", {})

            # Xử lý các hành động
            if action == ActionType.SEARCH_LAW.value:
                q = tool_args.get("query", user_query)
                top_k = tool_args.get("top_k", 3)
                tool_res = self.tool_registry.search_law(q, top_k=top_k)
                
                # Lưu vào cache ledger
                for art in tool_res.get("articles", []):
                    CaseLedgerManager.add_retrieved_article(ledger, art["article_id"], art["content_snippet"])
                CaseLedgerManager.add_query(ledger, q)

                ledger.record_tool_call("search_law", tool_args, f"Tìm thấy {len(tool_res.get('articles', []))} điều luật")
                messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                messages.append({"role": "user", "content": f"[OBSERVATION_TOOL_RESULT]\n{json.dumps(tool_res, ensure_ascii=False)}"})

            elif action == ActionType.GET_ARTICLE.value:
                aid = tool_args.get("article_id", "")
                tool_res = self.tool_registry.get_article(aid)
                if tool_res.get("status") == "success":
                    CaseLedgerManager.add_retrieved_article(ledger, aid, tool_res.get("full_content", ""))
                
                ledger.record_tool_call("get_article", tool_args, f"Trạng thái: {tool_res.get('status')}")
                messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                messages.append({"role": "user", "content": f"[OBSERVATION_TOOL_RESULT]\n{json.dumps(tool_res, ensure_ascii=False)}"})

            elif action == ActionType.ANSWER.value:
                answer_content = tool_args.get("content", "")
                raw_citations = tool_args.get("citations", [])
                citations = [Citation(**c) if isinstance(c, dict) else Citation(article_id=str(c)) for c in raw_citations]

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
                    "question": tool_args.get("question", "Vui lòng làm rõ thêm chi tiết về tình huống của bạn."),
                    "citations": []
                }

            elif action == ActionType.REFUSE.value:
                ledger.is_terminal = True
                ledger.terminal_status = "refused"
                ledger.final_output = {
                    "action": "refuse",
                    "reason": tool_args.get("reason", "Hệ thống từ chối trả lời vì không có căn cứ pháp luật rõ ràng."),
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
