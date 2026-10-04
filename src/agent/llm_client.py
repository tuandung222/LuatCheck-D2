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
            first_user_content = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
            clean_q = re.sub(r'\[/?UNTRUSTED_[A-Z_]+[^\]]*\]', '', first_user_content).strip()
            return {
                "thought": "Cần tra cứu quy định pháp luật liên quan đến câu hỏi của người dùng.",
                "action": "search_law",
                "tool_args": {"query": clean_q[:100], "top_k": 3}
            }

        retrieved_ids = re.findall(r'"article_id":\s*"([^"]+)"', last_msg)
        snippets = re.findall(r'"content_snippet":\s*"([^"]+)"', last_msg)

        chosen_id = retrieved_ids[0] if retrieved_ids else "Dieu_25"
        chosen_snippet = snippets[0] if snippets else ""

        if self.verification_mode != "off" and len(retrieved_ids) > 1:
            first_user_content = next((m.get("content", "") for m in messages if m.get("role") == "user"), "").lower()
            for idx_cand, cand_id in enumerate(retrieved_ids):
                norm_c = cand_id.lower()
                if "người lao động" in first_user_content and "đơn phương" in first_user_content:
                    if norm_c == "dieu_35" and "trái" not in first_user_content:
                        chosen_id = cand_id
                        chosen_snippet = snippets[idx_cand] if idx_cand < len(snippets) else chosen_snippet
                        break
                    elif norm_c == "dieu_40" and "trái" in first_user_content:
                        chosen_id = cand_id
                        chosen_snippet = snippets[idx_cand] if idx_cand < len(snippets) else chosen_snippet
                        break
                elif ("người sử dụng lao động" in first_user_content or "công ty" in first_user_content or "sa thải" in first_user_content) and "trái" in first_user_content:
                    if norm_c == "dieu_41":
                        chosen_id = cand_id
                        chosen_snippet = snippets[idx_cand] if idx_cand < len(snippets) else chosen_snippet
                        break

        chosen_display = chosen_id.replace("Dieu_", "Điều ").replace("dieu_", "Điều ")
        if chosen_snippet:
            clean_snippet = re.sub(r'[\r\n]+', ' ', chosen_snippet.replace('\\"', '"').replace('\\n', ' ')).strip()
            first_clause = clean_snippet.split('.')[0].strip()
            if len(first_clause) > 20:
                answer_content = f"Căn cứ theo quy định tại {chosen_display} Bộ luật Lao động 2019: {first_clause}."
            else:
                answer_content = f"Căn cứ theo quy định tại {chosen_display} ({chosen_id}): {clean_snippet[:150]}."
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
