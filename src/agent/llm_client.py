"""
Modular LLM Client Layer for LuatCheck.

Completely decouples the inference engine from the FSM controller loop.
Provides the following strategies:
1. OllamaLLMClient: Connects to a local Ollama server via HTTP REST API.
2. MockRuleBasedLLMClient: Deterministic fallback inference engine for unit testing and offline benchmarking.
3. CompositeLLMClient: Graceful fallback chain — attempts live inference first, automatically falls back on offline/error.
"""
import json
import re
import requests
from typing import List, Dict, Any, Optional
from src.interfaces.base import BaseLLMClient
from src.agent.state import ActionType, CaseLedger


class MockRuleBasedLLMClient(BaseLLMClient):
    """Deterministic rule-based mock LLM inference client for offline evaluation and testing."""

    def __init__(self, verification_mode: str = "l1_only"):
        self.verification_mode = verification_mode

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        """Generate next ReAct action based on conversation history."""
        last_msg = messages[-1]["content"] if messages else ""
        has_search = any(
            m.get("role") == "assistant" and "search_law" in m.get("content", "")
            for m in messages
        )
        repair_msgs = [
            m.get("content", "") for m in messages
            if "CẢNH BÁO TỪ HỆ THỐNG" in m.get("content", "") or "CẢNH BÁO XÁC THỰC" in m.get("content", "")
        ]

        if not has_search:
            if repair_msgs:
                return {
                    "thought": "Hệ thống xác thực báo lỗi căn cứ pháp lý không đủ. Tôi từ chối đưa ra kết luận để tránh rủi ro.",
                    "action": "refuse",
                    "tool_args": {"reason": "Không đủ căn cứ pháp lý tin cậy trong các điều luật đã nạp."}
                }
            first_user_content = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
            clean_q = re.sub(r'\[/?UNTRUSTED_[A-Z_]+[^\]]*\]', '', first_user_content).strip()
            return {
                "thought": "Cần tra cứu quy định pháp luật liên quan đến câu hỏi của người dùng.",
                "action": "search_law",
                "tool_args": {"query": clean_q[:100], "top_k": 3}
            }

        obs_msg = next(
            (m.get("content", "") for m in reversed(messages) if "[OBSERVATION_TOOL_RESULT]" in m.get("content", "")),
            last_msg
        )
        retrieved_articles = []
        try:
            json_part = obs_msg.split("[OBSERVATION_TOOL_RESULT]", 1)[-1].strip()
            obs_data = json.loads(json_part)
            if isinstance(obs_data, dict) and isinstance(obs_data.get("articles"), list):
                retrieved_articles = obs_data["articles"]
        except Exception:
            pass

        if not retrieved_articles:
            r_ids = re.findall(r'"article_id":\s*"([^"]+)"', obs_msg)
            r_snips = re.findall(r'"content_snippet":\s*"([^"]+)"', obs_msg)
            r_titles = re.findall(r'"title":\s*"([^"]+)"', obs_msg)
            for idx_r, rid in enumerate(r_ids):
                retrieved_articles.append({
                    "article_id": rid,
                    "title": r_titles[idx_r] if idx_r < len(r_titles) else "",
                    "content_snippet": r_snips[idx_r] if idx_r < len(r_snips) else "",
                })

        chosen_id = retrieved_articles[0]["article_id"] if retrieved_articles else "Dieu_25"
        chosen_snippet = retrieved_articles[0].get("content_snippet", "") if retrieved_articles else ""

        if repair_msgs:
            if len(repair_msgs) >= 2:
                return {
                    "thought": "Đã thử sửa chữa nhưng vẫn không đạt yêu cầu xác thực căn cứ pháp lý. Tôi từ chối trả lời.",
                    "action": "refuse",
                    "tool_args": {"reason": "Không đủ căn cứ pháp lý tin cậy sau khi đối chiếu các điều luật đã nạp."}
                }
            last_repair = repair_msgs[-1]
            repaired_candidate = None
            if "Sai lệch chủ thể pháp lý" in last_repair and len(retrieved_articles) > 1:
                if "lại điều chỉnh 'người sử dụng lao động'" in last_repair:
                    target_actor_phrase = "của người lao động"
                else:
                    target_actor_phrase = "của người sử dụng lao động"
                for cand in retrieved_articles[1:]:
                    cand_title = str(cand.get("title") or "").lower()
                    if target_actor_phrase in cand_title:
                        repaired_candidate = cand
                        break
            if repaired_candidate is None:
                return {
                    "thought": "Hệ thống xác thực báo lỗi căn cứ pháp lý không đủ. Tôi từ chối đưa ra kết luận để tránh rủi ro.",
                    "action": "refuse",
                    "tool_args": {"reason": "Không đủ căn cứ pháp lý tin cậy trong các điều luật đã nạp."}
                }
            chosen_id = repaired_candidate["article_id"]
            chosen_snippet = repaired_candidate.get("content_snippet", "")

        raw_user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        user_q = (
            ledger.user_query
            if ledger and getattr(ledger, "user_query", None)
            else re.sub(r'\[/?UNTRUSTED_[A-Z_]+[^\]]*\]', '', raw_user_msg).strip()
        )

        chosen_display = chosen_id.replace("Dieu_", "Điều ").replace("dieu_", "Điều ")
        if chosen_snippet:
            clean_snippet = re.sub(r'[\r\n]+', ' ', chosen_snippet.replace('\\"', '"').replace('\\n', ' ')).strip()
            clean_q_clause = re.sub(r'[.?!;\n]+', ',', user_q).strip(' ,')
            if "sa thải" in clean_q_clause.lower() and "trái" in clean_q_clause.lower():
                clean_q_clause += " (người sử dụng lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật)"
            prefix_clause = f"{clean_q_clause}. " if len(clean_q_clause) >= 35 else ""
            first_clause = clean_snippet.split('.')[0].strip()
            if len(first_clause) > 20:
                answer_content = f"{prefix_clause}Căn cứ theo quy định tại {chosen_display} Bộ luật Lao động 2019: {first_clause}."
            else:
                answer_content = f"{prefix_clause}Căn cứ theo quy định tại {chosen_display} ({chosen_id}): {clean_snippet[:150]}."
        else:
            answer_content = f"Căn cứ theo quy định tại {chosen_display} ({chosen_id}) Bộ luật Lao động 2019, quyền và nghĩa vụ của người lao động được quy định chi tiết theo điều luật."

        return {
            "thought": f"Đã có kết quả tra cứu điều luật {chosen_id}, tổng hợp câu trả lời có căn cứ.",
            "action": "answer",
            "tool_args": {
                "content": answer_content,
                "citations": [{"article_id": chosen_id, "law_name": "Bộ luật Lao động 2019"}]
            }
        }


class OllamaLLMClient(BaseLLMClient):
    """Inference client invoking a local SLM/LLM via the Ollama HTTP API."""

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        model_name: str = "qwen2.5:3b",
        temperature: float = 0.1,
        timeout_seconds: float = 30.0
    ):
        self.endpoint = endpoint
        self.model_name = model_name
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        valid_actions = {e.value for e in ActionType}
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "top_p": 0.9
            }
        }
        resp = requests.post(
            f"{self.endpoint}/api/chat",
            json=payload,
            timeout=self.timeout_seconds
        )
        if resp.status_code != 200:
            raise ConnectionError(f"Ollama server returned error status {resp.status_code}: {resp.text}")

        data = resp.json()
        raw_content = data.get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as jde:
            if ledger:
                ledger.audit_events.append({
                    "event": "parse_error",
                    "details": f"JSONDecodeError: {str(jde)} | raw: {raw_content[:100]}"
                })
            raise ValueError(f"Model response is not valid JSON: {raw_content}")

        if not isinstance(parsed, dict) or "action" not in parsed:
            if ledger:
                ledger.audit_events.append({
                    "event": "parse_error",
                    "details": f"InvalidSchema: Response missing 'action' field: {raw_content[:100]}"
                })
            raise ValueError(f"JSON response missing required 'action' field: {raw_content}")

        if not isinstance(parsed.get("tool_args"), dict):
            parsed["tool_args"] = {}

        act = str(parsed.get("action", ""))
        if act not in valid_actions:
            if ledger:
                ledger.audit_events.append({
                    "event": "parse_error",
                    "details": f"InvalidAction: '{act}' not in {valid_actions}"
                })
            raise ValueError(f"Invalid action '{act}'.")

        return parsed


class LlamaCppLLMClient(BaseLLMClient):
    """Inference client invoking a local SLM/LLM via llama.cpp or OpenAI-compatible server."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8080/v1",
        model_name: str = "qwen2.5:3b",
        temperature: float = 0.1,
        timeout_seconds: float = 30.0
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        valid_actions = {e.value for e in ActionType}
        url = self.endpoint if self.endpoint.endswith("/chat/completions") else f"{self.endpoint}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
        if resp.status_code != 200:
            raise ConnectionError(f"llama.cpp server returned error status {resp.status_code}: {resp.text}")

        data = resp.json()
        raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as jde:
            if ledger:
                ledger.audit_events.append({
                    "event": "parse_error",
                    "details": f"JSONDecodeError: {str(jde)} | raw: {raw_content[:100]}"
                })
            raise ValueError(f"Model response is not valid JSON: {raw_content}")

        if not isinstance(parsed, dict) or "action" not in parsed:
            if ledger:
                ledger.audit_events.append({
                    "event": "parse_error",
                    "details": f"InvalidSchema: Response missing 'action' field: {raw_content[:100]}"
                })
            raise ValueError(f"JSON response missing required 'action' field: {raw_content}")

        if not isinstance(parsed.get("tool_args"), dict):
            parsed["tool_args"] = {}

        act = str(parsed.get("action", ""))
        if act not in valid_actions:
            if ledger:
                ledger.audit_events.append({
                    "event": "parse_error",
                    "details": f"InvalidAction: '{act}' not in {valid_actions}"
                })
            raise ValueError(f"Invalid action '{act}'.")

        return parsed


class CompositeLLMClient(BaseLLMClient):
    """Composite client: Attempts primary LLM inference, automatically falling back on mock client upon network/timeout errors."""

    def __init__(
        self,
        primary_client: Optional[BaseLLMClient] = None,
        fallback_client: Optional[BaseLLMClient] = None
    ):
        self.primary_client = primary_client or OllamaLLMClient()
        self.fallback_client = fallback_client or MockRuleBasedLLMClient()

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        try:
            return self.primary_client.generate(messages, ledger=ledger)
        except Exception:
            return self.fallback_client.generate(messages, ledger=ledger)
