"""Native inference clients. Backend failures never produce substitute answers."""
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

import requests
from src.agent.state import ActionType, CaseLedger
from src.domains import DomainProfile, load_profile


class InferenceError(RuntimeError):
    """A failed invocation must not be scored as a safety refusal."""
    def __init__(self, message: str, kind: str = "backend_error"):
        super().__init__(message)
        self.kind = kind


class NativeLLMClient:
    backend = "native"

    def __init__(self, endpoint: str, model_name: str = "qwen2.5:3b",
                 temperature: float = 0.1, timeout_seconds: float = 30,
                 seed: Optional[int] = None, max_output_tokens: int = 512,
                 context_tokens: int = 4096, sampling: Optional[Dict[str, Any]] = None,
                 profile: Optional[DomainProfile] = None):
        self.endpoint = endpoint.rstrip("/")
        # The profile names the model-facing tools; it defaults to the labour profile used before profiles existed.
        self.profile = profile or load_profile()
        self.action_schema = build_action_schema(self.profile)
        self.model_name = model_name
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.seed = seed
        self.max_output_tokens = max_output_tokens
        self.context_tokens = context_tokens
        self.sampling = dict(sampling or {})

    def validate_action(self, action: Any) -> Dict[str, Any]:
        """Check a parsed model response against the action contract of this client's domain profile.

        Raises InferenceError("model_output_error") for anything else: an invalid response is an
        execution error, never a substitute answer.
        """
        canonical = self.profile.canonical_action(action.get("action")) if isinstance(action, dict) else None
        if canonical is None:
            raise InferenceError("Model returned an invalid or missing action.", "model_output_error")
        if not isinstance(action.get("tool_args"), dict):
            raise InferenceError("Model action requires a tool_args object.", "model_output_error")
        args = action["tool_args"]
        required = REQUIRED_ARGUMENT[canonical]
        if not isinstance(args.get(required), str) or not args[required].strip():
            raise InferenceError(f"Action requires a nonempty {required}.", "model_output_error")
        if canonical is ActionType.ANSWER:
            citations = args.get("citations")
            if not isinstance(citations, list) or any(
                not isinstance(c, dict) or not isinstance(c.get("article_id"), str) or not c["article_id"].strip()
                for c in citations
            ):
                raise InferenceError("Answer requires a citation list with valid article IDs.", "model_output_error")
        return action

    def _request(self, url: str, payload: dict, ledger: Optional[CaseLedger],
                 headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        started = time.monotonic()
        event = {
            "backend": self.backend, "endpoint": self.endpoint,
            "requested_model": self.model_name, "seed": self.seed,
            "request_sha256": hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            "request_messages": json.loads(json.dumps(payload.get("messages", []), ensure_ascii=False)),
            "input_tokens": None, "output_tokens": None, "outcome": "error",
        }
        try:
            timeout = self.timeout_seconds
            if ledger and ledger.deadline_monotonic is not None:
                remaining = ledger.deadline_monotonic - time.monotonic()
                if remaining <= 0:
                    raise InferenceError("Task wall-clock budget exhausted before inference.", "wall_timeout")
                timeout = min(timeout, remaining)
            response = requests.post(url, json=payload, timeout=timeout, headers=headers)
            if response.status_code != 200:
                raise InferenceError(f"{self.backend} returned HTTP {response.status_code}.")
            data = response.json()
            if not isinstance(data, dict):
                raise InferenceError("Backend response must be a JSON object.")
            event["native_response"] = data
            if self.backend == "ollama":
                raw = data.get("message", {}).get("content", "")
                event.update(input_tokens=data.get("prompt_eval_count"), output_tokens=data.get("eval_count"),
                             returned_model=data.get("model"), total_duration_ns=data.get("total_duration"),
                             load_duration_ns=data.get("load_duration"), eval_duration_ns=data.get("eval_duration"))
                if data.get("done_reason") == "length":
                    raise InferenceError("Model output truncated by token limit.", "model_output_error")
            else:
                raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage") or {}
                event.update(input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"),
                             returned_model=data.get("model"))
                if data.get("choices", [{}])[0].get("finish_reason") == "length":
                    raise InferenceError("Model output truncated by token limit.", "model_output_error")
            try:
                action = json.loads(raw)
            except (TypeError, json.JSONDecodeError) as exc:
                raise InferenceError("Model response is not valid JSON.", "model_output_error") from exc
            self.validate_action(action)
            event.update(outcome="success", response=action)
            return action
        except InferenceError as exc:
            event["error"] = str(exc)
            event["error_kind"] = exc.kind
            raise
        except requests.Timeout as exc:
            event.update(error=str(exc), error_kind="wall_timeout")
            raise InferenceError("Native inference timed out.", "wall_timeout") from exc
        except (requests.RequestException, ValueError, TypeError, IndexError, AttributeError) as exc:
            event["error"] = f"{type(exc).__name__}: {exc}"
            raise InferenceError(f"{self.backend} inference failed: {type(exc).__name__}") from exc
        finally:
            event["wall_ms"] = round((time.monotonic() - started) * 1000, 3)
            if ledger is not None:
                ledger.llm_calls.append(event)


class OllamaLLMClient(NativeLLMClient):
    backend = "ollama"

    def __init__(self, endpoint: str = "http://localhost:11434", **kwargs):
        super().__init__(endpoint, **kwargs)

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        options = {"temperature": self.temperature, "top_p": 0.9,
                   "num_predict": self.max_output_tokens, "num_ctx": self.context_tokens}
        if self.seed is not None:
            options["seed"] = self.seed
        payload = {"model": self.model_name, "messages": messages, "stream": False,
                   "format": "json", "options": options, "keep_alive": "10m"}
        return self._request(f"{self.endpoint}/api/chat", payload, ledger)


class LlamaCppLLMClient(NativeLLMClient):
    backend = "llamacpp"

    def __init__(self, endpoint: str = "http://localhost:8080/v1", constrained_json: bool = False,
                 enable_thinking: Optional[bool] = None, **kwargs):
        super().__init__(endpoint, **kwargs)
        self.constrained_json = constrained_json
        self.enable_thinking = enable_thinking

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        url = self.endpoint if self.endpoint.endswith("/chat/completions") else f"{self.endpoint}/chat/completions"
        payload = {"model": self.model_name, "messages": messages, "temperature": self.temperature,
                   "max_tokens": self.max_output_tokens, "response_format": {"type": "json_object"}}
        if self.constrained_json:
            payload["response_format"] = {"type": "json_schema",
                                          "json_schema": {"name": "luatcheck_action", "schema": self.action_schema}}
        if self.enable_thinking is not None:
            payload["chat_template_kwargs"] = {"enable_thinking": self.enable_thinking}
        payload.update(self.sampling)
        if self.seed is not None:
            payload["seed"] = self.seed
        return self._request(url, payload, ledger)


def _action_branch(action: str, args: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {"type": "object",
            "properties": {"thought": {"type": "string"}, "action": {"const": action},
                           "tool_args": {"type": "object", "properties": args, "required": required}},
            "required": ["thought", "action", "tool_args"]}


# The one required, nonempty string argument of each canonical action. Argument names are canonical
# across domains; only the SEARCH and READ action names come from the domain profile.
REQUIRED_ARGUMENT = {ActionType.SEARCH: "query", ActionType.READ: "article_id", ActionType.ANSWER: "content",
                     ActionType.CLARIFY: "question", ActionType.REFUSE: "reason"}


def build_action_schema(profile: DomainProfile) -> Dict[str, Any]:
    """JSON schema of the controller's action contract for a domain profile, used for grammar-constrained decoding.

    The client still validates every response; the schema only restricts what can be sampled.
    """
    return {"anyOf": [
        _action_branch(profile.model_action_name(ActionType.SEARCH),
                       {"query": {"type": "string"}, "top_k": {"type": "integer"}}, ["query"]),
        _action_branch(profile.model_action_name(ActionType.READ), {"article_id": {"type": "string"}}, ["article_id"]),
        _action_branch("answer", {"content": {"type": "string"},
                                  "citations": {"type": "array", "items": {
                                      "type": "object",
                                      "properties": {"article_id": {"type": "string"}, "law_name": {"type": "string"},
                                                     "exact_quote": {"type": "string"}},
                                      "required": ["article_id"]}}},
                       ["content", "citations"]),
        _action_branch("clarify", {"question": {"type": "string"}}, ["question"]),
        _action_branch("refuse", {"reason": {"type": "string"}}, ["reason"]),
    ]}


# Schema of the default (labour) profile, kept for callers that import the constant.
ACTION_SCHEMA = build_action_schema(load_profile())


class MlxVlmLLMClient(NativeLLMClient):
    """OpenAI-compatible mlx_vlm.server on Apple Silicon (e.g. Ternary Bonsai MLX packs)."""
    backend = "mlx"

    def __init__(self, endpoint: str = "http://127.0.0.1:8080/v1", constrained_json: bool = True, **kwargs):
        super().__init__(endpoint, **kwargs)
        self.constrained_json = constrained_json

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        url = self.endpoint if self.endpoint.endswith("/chat/completions") else f"{self.endpoint}/chat/completions"
        payload = {"model": self.model_name, "messages": messages, "stream": False,
                   "temperature": self.temperature, "max_tokens": self.max_output_tokens,
                   "enable_thinking": False}
        if self.constrained_json:
            # A full action schema: mlx-vlm's generic json_object grammar corrupted Bonsai's first key.
            payload["response_format"] = {"type": "json_schema",
                                          "json_schema": {"name": "luatcheck_action", "schema": self.action_schema}}
        payload.update(self.sampling)
        if self.seed is not None:
            payload["seed"] = self.seed
        return self._request(url, payload, ledger)


class GatewayLLMClient(NativeLLMClient):
    """Remote OpenAI-compatible API gateway, for diagnostic comparison runs only.

    The credential is read from the named environment variable (or the local .env)
    at request time and is never stored on the client, in the ledger or in a manifest.
    """
    backend = "gateway"

    def __init__(self, endpoint: str, api_key_env: str, reasoning_effort: Optional[str] = None, **kwargs):
        super().__init__(endpoint, **kwargs)
        self.api_key_env = api_key_env
        self.reasoning_effort = reasoning_effort

    def _api_key(self) -> str:
        import os
        from pathlib import Path
        key = os.environ.get(self.api_key_env)
        if not key and Path(".env").exists():
            for line in Path(".env").read_text().splitlines():
                name, _, value = line.partition("=")
                if name.strip() == self.api_key_env:
                    key = value.strip().strip("\"'")
        if not key:
            raise InferenceError(f"Gateway credential {self.api_key_env} is not set.")
        return key

    def generate(self, messages: List[Dict[str, str]], ledger: Optional[CaseLedger] = None) -> Dict[str, Any]:
        url = self.endpoint if self.endpoint.endswith("/chat/completions") else f"{self.endpoint}/chat/completions"
        payload = {"model": self.model_name, "messages": messages, "temperature": self.temperature,
                   "max_tokens": self.max_output_tokens, "response_format": {"type": "json_object"}}
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        if self.seed is not None:
            payload["seed"] = self.seed
        return self._request(url, payload, ledger, headers={"Authorization": f"Bearer {self._api_key()}"})
