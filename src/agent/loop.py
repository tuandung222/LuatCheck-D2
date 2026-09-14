"""
LuatCheck Budgeted ReAct Agent Loop
Vòng lặp suy luận - hành động có giới hạn ngân sách và xác thực căn cứ L1
"""
import json
import time
import requests
from typing import Dict, Any, Optional, List, Tuple

from src.agent.state import ActionType, AgentAction, CaseLedger, Citation
from src.agent.prompts import SYSTEM_PROMPT, REPAIR_PROMPT_TEMPLATE
from src.tools.legal_tools import LegalToolRegistry
from src.verifier.l1_deterministic import L1EvidenceVerifier
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
        enable_verification: bool = True
    ):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.max_tool_calls = max_tool_calls
        self.max_repairs = max_repairs
        self.enable_verification = enable_verification

        # Khởi tạo các hệ thống con
        self.tool_registry = LegalToolRegistry(corpus_path=corpus_path)
        self.verifier = L1EvidenceVerifier(self.tool_registry.retriever.corpus)
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
        except Exception as e:
            # Fallback nếu Ollama mất kết nối
            pass

        return self._rule_based_fallback(messages)

    def _rule_based_fallback(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Bộ sinh suy luận dự phòng đảm bảo tính sẵn sàng cao (High Availability)
        """
        last_msg = messages[-1]["content"]
        # Phân tích xem đã search chưa
        has_search = any("search_law" in m.get("content", "") for m in messages)
        has_repair = any("CẢNH BÁO TỪ HỆ THỐNG" in m.get("content", "") for m in messages)

        if has_repair:
            return {
                "thought": "Hệ thống xác thực báo lỗi căn cứ pháp lý không đủ. Tôi từ chối đưa ra kết luận để tránh rủi ro.",
                "action": "refuse",
                "tool_args": {"reason": "Không đủ căn cứ pháp lý tin cậy trong các điều luật đã nạp."}
            }

        if not has_search:
            return {
                "thought": "Cần tra cứu quy định pháp luật liên quan đến câu hỏi của người dùng.",
                "action": "search_law",
                "tool_args": {"query": last_msg[:100], "top_k": 3}
            }

        return {
            "thought": "Đã có kết quả tra cứu điều luật, tổng hợp câu trả lời.",
            "action": "answer",
            "tool_args": {
                "content": "Theo quy định pháp luật lao động, quyền và nghĩa vụ của các bên được quy định cụ thể tại điều khoản trích dẫn.",
                "citations": [{"article_id": "Dieu_35", "law_name": "Bộ luật Lao động 2019"}]
            }
        }

    def run(self, user_query: str, pasted_doc: Optional[str] = None, session_id: Optional[str] = None) -> CaseLedger:
        start_time = time.time()
        sid = session_id or f"session_{int(time.time() * 1000)}"
        ledger = CaseLedgerManager.create_session(sid, user_query, [pasted_doc] if pasted_doc else [])

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

        # 2. Kiểm tra bộ nhớ dài hạn (Episodic Store Check)
        cached_case = self.sqlite_store.retrieve_similar_case(user_query)
        if cached_case:
            ledger.is_terminal = True
            ledger.terminal_status = "answered"
            ledger.final_output = {
                "action": "answer",
                "content": cached_case["answer"],
                "citations": cached_case["citations"],
                "from_cache": True
            }
            self.audit_logger.log_event(sid, "cache_hit", {"case_id": cached_case["case_id"]})
            return ledger

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
                    "reason": "Hệ thống đã sử dụng hết ngân sách 5 lượt gọi công cụ mà chưa hoàn tất xác thực.",
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

                # BƯỚC XÁC THỰC CĂN CỨ PHÁP LÝ L1
                if self.enable_verification:
                    l1_res = self.verifier.verify(
                        answer_text=answer_content,
                        citations=citations,
                        retrieved_article_ids=ledger.retrieved_article_ids
                    )
                else:
                    # Ablation: Tắt verification
                    from src.agent.state import L1VerificationResult
                    l1_res = L1VerificationResult(is_valid=True)

                if l1_res.is_valid:
                    ledger.is_terminal = True
                    ledger.terminal_status = "answered"
                    ledger.final_output = {
                        "action": "answer",
                        "content": answer_content,
                        "citations": [c.dict() for c in citations],
                        "verified": True
                    }
                    # Lưu vào SQLite Episodic Store
                    self.sqlite_store.write_if_verified(
                        case_id=sid,
                        query=user_query,
                        answer=answer_content,
                        citations=[c.dict() for c in citations],
                        is_l1_verified=True
                    )
                else:
                    # Xử lý khi xác thực L1 thất bại -> Kích hoạt Targeted Repair
                    if ledger.can_repair():
                        ledger.record_repair(l1_res.repair_feedback)
                        repair_prompt = REPAIR_PROMPT_TEMPLATE.format(repair_feedback=l1_res.repair_feedback)
                        messages.append({"role": "assistant", "content": json.dumps(agent_resp, ensure_ascii=False)})
                        messages.append({"role": "user", "content": repair_prompt})
                    else:
                        # Đã hết ngân sách tự sửa chữa -> Fallback dứt khoát sang Refuse
                        ledger.is_terminal = True
                        ledger.terminal_status = "refused"
                        ledger.final_output = {
                            "action": "refuse",
                            "reason": f"Không thể xác thực căn cứ pháp lý sau {self.max_repairs} lần thử sửa chữa. Chi tiết vi phạm: {l1_res.repair_feedback}",
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
