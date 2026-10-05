"""
Unit tests for LlamaCppLLMClient and llama.cpp OpenAI-compatible inference support.
Validates:
1. Successful JSON generation from OpenAI/llama.cpp /chat/completions endpoint.
2. Connection error handling on server error status.
3. Parse error handling on malformed JSON outputs.
4. Schema validation for required 'action' fields and valid ActionTypes.
5. Seamless CompositeLLMClient fallback to MockRuleBasedLLMClient.
6. LuatCheckAgent initialization using provider="llamacpp" or "llama.cpp".
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.agent.llm_client import LlamaCppLLMClient, CompositeLLMClient, MockRuleBasedLLMClient
from src.agent.state import CaseLedger
from src.agent.loop import LuatCheckAgent
from src.config.app_config import AppConfig, ModelConfig


def test_llamacpp_generate_success():
    """Verify that LlamaCppLLMClient sends correct payload and parses OpenAI-compatible response."""
    client = LlamaCppLLMClient(endpoint="http://localhost:8080/v1", model_name="qwen2.5:3b")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "action": "answer",
                        "content": "Thời gian thử việc tối đa là 60 ngày theo Điều 25.",
                        "citations": [{"article_id": "Dieu_25", "span": "thời gian thử việc"}]
                    })
                }
            }
        ]
    }
    
    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = client.generate([{"role": "user", "content": "Thử việc bao lâu?"}])
        
        assert mock_post.called
        call_url = mock_post.call_args[0][0]
        call_json = mock_post.call_args[1]["json"]
        
        assert call_url == "http://localhost:8080/v1/chat/completions"
        assert call_json["model"] == "qwen2.5:3b"
        assert call_json["response_format"] == {"type": "json_object"}
        assert result["action"] == "answer"
        assert "60 ngày" in result["content"]


def test_llamacpp_connection_error():
    """Verify ConnectionError is raised when llama.cpp server returns non-200 status."""
    client = LlamaCppLLMClient(endpoint="http://localhost:8080/v1")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_resp.text = "Bad Gateway"
    
    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(ConnectionError) as exc_info:
            client.generate([{"role": "user", "content": "Test"}])
        assert "llama.cpp server returned error status 502" in str(exc_info.value)


def test_llamacpp_malformed_json_handling():
    """Verify ValueError and parse_error audit event when model returns invalid JSON."""
    client = LlamaCppLLMClient(endpoint="http://localhost:8080/v1")
    ledger = CaseLedger(session_id="test_session", original_query="Test query")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "This is raw unformatted text without JSON"}}]
    }
    
    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(ValueError) as exc_info:
            client.generate([{"role": "user", "content": "Test"}], ledger=ledger)
        assert "Model response is not valid JSON" in str(exc_info.value)
        assert any(ev.get("event") == "parse_error" for ev in ledger.audit_events)


def test_llamacpp_missing_or_invalid_action():
    """Verify ValueError when required 'action' field is missing or invalid."""
    client = LlamaCppLLMClient(endpoint="http://localhost:8080/v1")
    
    # Missing action
    mock_resp_1 = MagicMock()
    mock_resp_1.status_code = 200
    mock_resp_1.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"content": "Missing action"})}}]
    }
    
    with patch("requests.post", return_value=mock_resp_1):
        with pytest.raises(ValueError) as exc:
            client.generate([{"role": "user", "content": "Test"}])
        assert "missing required 'action' field" in str(exc.value)

    # Invalid action name
    mock_resp_2 = MagicMock()
    mock_resp_2.status_code = 200
    mock_resp_2.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"action": "unknown_action_type"})}}]
    }
    
    with patch("requests.post", return_value=mock_resp_2):
        with pytest.raises(ValueError) as exc:
            client.generate([{"role": "user", "content": "Test"}])
        assert "Invalid action 'unknown_action_type'" in str(exc.value)


def test_composite_client_automatic_fallback():
    """CompositeLLMClient must automatically fall back to mock client when llama.cpp is offline."""
    primary = LlamaCppLLMClient(endpoint="http://127.0.0.1:9999/v1") # Unreachable port
    fallback = MockRuleBasedLLMClient()
    composite = CompositeLLMClient(primary_client=primary, fallback_client=fallback)
    
    # Mock network connection error from requests.post
    with patch("requests.post", side_effect=Exception("Connection refused")):
        # Mock client should handle the query and return a valid action dict
        res = composite.generate([{"role": "user", "content": "Thời gian thử việc tối đa là bao lâu?"}])
        assert isinstance(res, dict)
        assert "action" in res


def test_agent_initialization_with_llamacpp_config():
    """LuatCheckAgent must properly instantiate LlamaCppLLMClient when config.model.provider='llamacpp'."""
    cfg = AppConfig()
    cfg.model = ModelConfig(
        provider="llamacpp",
        endpoint="http://localhost:8080/v1",
        name="qwen3.5:4b"
    )
    
    agent = LuatCheckAgent(config=cfg)
    assert isinstance(agent.llm_client, CompositeLLMClient)
    assert isinstance(agent.llm_client.primary_client, LlamaCppLLMClient)
    assert agent.llm_client.primary_client.endpoint == "http://localhost:8080/v1"
    assert agent.llm_client.primary_client.model_name == "qwen3.5:4b"
