"""Shared runtime helpers for the pluggable model components.

Used by ``src/retrieval/rerankers.py`` and ``src/verifier/nli_backends.py``.

Integrity rules (see AGENTS.md):

* Every failure is raised as :class:`ModelComponentError`.  No function in this
  module (or in the two component modules) ever returns a substitute score,
  label or probability when a model, runtime or server is unavailable.
* Device selection is explicit and recorded.  ``"auto"`` means "mps when torch
  reports it available *and* the component is marked MPS-safe, else cpu"; an
  explicit device that cannot be honoured raises instead of changing silently.
* Models are lazy: nothing is imported or downloaded until ``load()`` (or the
  first call), and a failed load is remembered and re-raised on every later
  call so the caller can inspect ``load_error``.
"""
from __future__ import annotations

import ipaddress
import json
import math
import threading
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "ModelComponentError",
    "require_loopback_url",
    "import_torch",
    "resolve_device",
    "resolve_dtype",
    "doc_id",
    "doc_text",
    "reject_unknown_keys",
    "LazyComponent",
    "SystemOneRunner",
    "QevHttpClient",
    "get_system_one_runner",
    "release_system_one_runners",
    "flush_accelerator_cache",
]


class ModelComponentError(RuntimeError):
    """A model/runtime/server failure.  Never convertible to a successful result.

    ``kind`` is one of: ``config_error``, ``missing_runtime``, ``load_error``,
    ``backend_error``, ``bad_response``, ``input_too_long``.
    """

    def __init__(self, message: str, kind: str = "backend_error"):
        super().__init__(message)
        self.kind = kind


# --------------------------------------------------------------------------- #
# Config / document helpers
# --------------------------------------------------------------------------- #

def reject_unknown_keys(cfg: Dict[str, Any], allowed: Sequence[str], what: str) -> None:
    unknown = sorted(set(cfg) - set(allowed))
    if unknown:
        raise ModelComponentError(
            f"{what}: unknown config key(s) {unknown}; allowed keys: {sorted(allowed)}",
            kind="config_error")


def doc_id(doc: Any, index: int = 0) -> str:
    """Generic document id (works for ``doc_id`` / ``article_id`` / ``id`` dicts)."""
    if isinstance(doc, dict):
        for key in ("doc_id", "article_id", "id"):
            if doc.get(key) not in (None, ""):
                return str(doc[key])
    return f"doc_{index}"


def doc_text(doc: Any, fields: Sequence[str] = ("title", "content")) -> str:
    """Text of a candidate document.

    Strings are used as-is.  For dicts the non-empty ``fields`` are joined with a
    blank line, except that a field already contained at the start of the
    previous one is not repeated (the official corpus stores ``content`` with its
    title as a prefix).
    """
    if isinstance(doc, str):
        text = doc
    elif isinstance(doc, dict):
        parts: List[str] = []
        for name in fields:
            value = doc.get(name)
            if value is None or not str(value).strip():
                continue
            value = str(value).strip()
            if parts and parts[-1].startswith(value):
                continue
            if parts and value.startswith(parts[-1]):
                parts[-1] = value
                continue
            parts.append(value)
        text = "\n\n".join(parts)
    else:
        raise ModelComponentError(
            f"Unsupported document type {type(doc).__name__}; expected str or dict", kind="config_error")
    if not text.strip():
        raise ModelComponentError("Candidate document has no text in fields " + str(list(fields)),
                                  kind="config_error")
    return text


def require_loopback_url(url: str, what: str) -> str:
    """Return ``url`` stripped of a trailing slash if its host is loopback, else raise."""
    parsed = urllib.parse.urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ModelComponentError(f"{what}: endpoint must be an http(s) URL, got {url!r}", kind="config_error")
    host = parsed.hostname
    loopback = host == "localhost"
    if not loopback:
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
    if not loopback:
        raise ModelComponentError(
            f"{what}: endpoint host {host!r} is not loopback (localhost/127.0.0.0/8/::1); "
            "remote endpoints are refused by default", kind="config_error")
    return url.rstrip("/")


# --------------------------------------------------------------------------- #
# torch / device / dtype
# --------------------------------------------------------------------------- #

_INSTALL_HINT = ("install the optional model backends: "
                 "uv pip install --python .venv/bin/python -r requirements-model-backends.txt")


def import_torch():
    try:
        import torch  # noqa: WPS433
    except ImportError as exc:
        raise ModelComponentError(f"torch is not installed; {_INSTALL_HINT}", kind="missing_runtime") from exc
    return torch


def resolve_device(requested: Optional[str], mps_supported: bool = True) -> str:
    """Resolve ``auto|cpu|mps|cuda[:n]`` to a concrete torch device string.

    ``auto`` -> ``mps`` when available and ``mps_supported`` else ``cpu``.
    Explicit values are validated, never silently replaced.
    """
    torch = import_torch()
    req = (requested or "auto").strip().lower()
    mps_ok = bool(getattr(torch.backends, "mps", None)) and torch.backends.mps.is_available()
    if req == "auto":
        return "mps" if (mps_supported and mps_ok) else "cpu"
    if req == "cpu":
        return "cpu"
    if req == "mps":
        if not mps_supported:
            raise ModelComponentError("device 'mps' is not supported for this component", kind="config_error")
        if not mps_ok:
            raise ModelComponentError("device 'mps' requested but torch reports MPS unavailable",
                                      kind="missing_runtime")
        return "mps"
    if req.startswith("cuda"):
        if not torch.cuda.is_available():
            raise ModelComponentError("device 'cuda' requested but CUDA is unavailable", kind="missing_runtime")
        return req
    raise ModelComponentError(f"unknown device {requested!r}; use auto|cpu|mps|cuda", kind="config_error")


def resolve_dtype(name: Optional[str], default: str = "float32"):
    torch = import_torch()
    key = (name or default).strip().lower()
    table = {"float32": torch.float32, "fp32": torch.float32, "float16": torch.float16, "fp16": torch.float16,
             "bfloat16": torch.bfloat16, "bf16": torch.bfloat16}
    if key not in table:
        raise ModelComponentError(f"unknown dtype {name!r}; use float32|float16|bfloat16", kind="config_error")
    canonical = {torch.float32: "float32", torch.float16: "float16", torch.bfloat16: "bfloat16"}[table[key]]
    return table[key], canonical


def flush_accelerator_cache() -> None:
    """Release cached accelerator memory (no-op when torch is not installed)."""
    try:
        import torch
    except ImportError:
        return
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        torch.mps.empty_cache()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def release_system_one_runners() -> None:
    """Unload and forget every shared decision-model runner."""
    with _RUNNERS_LOCK:
        runners = list(_RUNNERS.values())
        _RUNNERS.clear()
    for runner in runners:
        runner.unload()


# --------------------------------------------------------------------------- #
# Lazy loading base
# --------------------------------------------------------------------------- #

class LazyComponent:
    """Lazy, load-once component whose load failure is remembered and re-raised."""

    backend: str = "unknown"
    mps_supported: bool = True

    def __init__(self, model: str, device: str = "auto", dtype: Optional[str] = None,
                 local_files_only: bool = False):
        if not model or not isinstance(model, str):
            raise ModelComponentError(f"{type(self).__name__}: 'model' (HF repo id or local path) is required",
                                      kind="config_error")
        self.model_name = model
        self.requested_device = device or "auto"
        self.requested_dtype = dtype
        self.local_files_only = bool(local_files_only)
        self.device: Optional[str] = None      # concrete device, set at load time
        self.dtype_name: Optional[str] = None
        self.load_seconds: Optional[float] = None
        self.load_error: Optional[ModelComponentError] = None
        self._loaded = False
        self._lock = threading.RLock()

    # subclasses implement
    def _load(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    @property
    def loaded(self) -> bool:
        return self._loaded

    def load(self) -> "LazyComponent":
        with self._lock:
            if self._loaded:
                return self
            if self.load_error is not None:
                raise self.load_error
            started = time.perf_counter()
            try:
                self._load()
            except ModelComponentError as exc:
                self.load_error = exc
                raise
            except Exception as exc:  # noqa: BLE001 - wrapped, never swallowed
                hint = ""
                if isinstance(exc, OSError) or "local_files_only" in str(exc):
                    hint = f" (download with: hf download {self.model_name})"
                err = ModelComponentError(
                    f"{type(self).__name__} failed to load {self.model_name!r}: "
                    f"{type(exc).__name__}: {exc}{hint}", kind="load_error")
                err.__cause__ = exc
                self.load_error = err
                raise err from exc
            self.load_seconds = time.perf_counter() - started
            self._loaded = True
            return self

    _HEAVY_ATTRS = ("_model", "_tok", "_tokenizer", "_slot_w")

    def unload(self) -> None:
        """Free the weights (del + gc + accelerator cache flush).  A later call reloads."""
        import gc
        with self._lock:
            for name in self._HEAVY_ATTRS:
                if hasattr(self, name):
                    setattr(self, name, None)
            self._loaded = False
            gc.collect()
            flush_accelerator_cache()

    def info(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "model": self.model_name,
            "device": self.device,
            "dtype": self.dtype_name,
            "loaded": self._loaded,
            "load_seconds": self.load_seconds,
            "load_error": None if self.load_error is None else str(self.load_error),
            "local_files_only": self.local_files_only,
        }


# --------------------------------------------------------------------------- #
# System One / JEV decision-model runner
# --------------------------------------------------------------------------- #
#
# Real API of OmniJev/OneJev1.6-* (model card + github.com/OmniJev/OneJev, package
# ``qev``): a request is a ``state`` plus typed ``questions`` (Noul = yes/no,
# Choice = categorical, Score = ordinal).  The server renders each question to a
# chat prompt (system prompt "Apply the question to the state. Choose exactly one
# of the listed options. Respond with only its uppercase letter ..."; user turn
# ``<state>...</state>`` + ``Question: ... Options: A. ... Answer with one
# letter: A, B.``), runs ONE forward pass and reads the logits of the option
# letter tokens at the last position; the answer is the softmax over those slot
# logits (temperature 1.0 unless a calibration file is supplied; the LM head rows
# of the slots are computed in float32).  ``SystemOneRunner`` below is a faithful
# re-implementation of that single-question path with plain transformers
# (prompt version ``qev-labels-v2``).  It does NOT install or call the ``qev``
# package/server, and it has not been cross-checked against a qev server's
# output.  It supports text states only (no images/video).

SYSTEM_ONE_PROMPT_VERSION = "qev-labels-v2"
_SYSTEM_ONE_SYSTEM = ("Apply the question to the state. Choose exactly one of the listed options. "
                      "Respond with only its uppercase letter, with no explanation or reasoning.")
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_NOUL_TRUE = "the statement is true / the answer is yes"
_NOUL_FALSE = "the statement is false / the answer is no"


def _render_state(state: Any) -> str:
    if state is None:
        return ""
    if isinstance(state, str):
        return state
    return json.dumps(state, ensure_ascii=False, indent=2)


def _render_options(names: Sequence[str], descriptions: Sequence[str]) -> str:
    lines = []
    for letter, name, desc in zip(_LETTERS, names, descriptions):
        lines.append(f"{letter}. {name}: {desc}" if desc else f"{letter}. {name}")
    return "\n".join(lines)


class SystemOneRunner(LazyComponent):
    """Local single-pass decision-model runner (OneJev / System One style)."""

    backend = "system_one"
    # Qwen3.5 gated-delta-net layers use a torch fallback kernel here; MPS support is
    # established empirically (see docs/plans/model-components.md), not assumed.
    mps_supported = True

    def __init__(self, model: str, device: str = "auto", dtype: Optional[str] = None,
                 local_files_only: bool = False, max_prompt_tokens: int = 8192):
        super().__init__(model, device, dtype, local_files_only)
        self.max_prompt_tokens = int(max_prompt_tokens)
        self._model = None
        self._tokenizer = None
        self._slot_ids: List[int] = []
        self._slot_w = None
        self.last_details: Dict[str, Any] = {}

    def _load(self) -> None:
        torch = import_torch()
        try:
            import transformers
        except ImportError as exc:
            raise ModelComponentError(f"transformers is not installed; {_INSTALL_HINT}",
                                      kind="missing_runtime") from exc
        if not hasattr(transformers, "Qwen3_5ForCausalLM"):
            raise ModelComponentError(
                f"transformers {transformers.__version__} has no Qwen3_5ForCausalLM; need transformers>=5 "
                f"({_INSTALL_HINT})", kind="missing_runtime")
        self.device = resolve_device(self.requested_device, self.mps_supported)
        torch_dtype, self.dtype_name = resolve_dtype(
            self.requested_dtype, default="bfloat16" if self.device != "cpu" else "float32")
        common = {"local_files_only": self.local_files_only, "trust_remote_code": False}
        config = transformers.AutoConfig.from_pretrained(self.model_name, **common)
        if config.model_type not in ("qwen3_5", "qwen3_5_text"):
            raise ModelComponentError(
                f"SystemOneRunner supports OneJev 1.6 (qwen3_5) checkpoints; {self.model_name!r} has "
                f"model_type {config.model_type!r}", kind="config_error")
        tokenizer = transformers.AutoTokenizer.from_pretrained(self.model_name, **common)
        model, info = transformers.Qwen3_5ForCausalLM.from_pretrained(
            self.model_name, config=config.get_text_config(), dtype=torch_dtype,
            output_loading_info=True, **common)
        # A partially initialised model would yield numbers that look real but are not.
        missing = [k for k in info.get("missing_keys", [])]
        if missing:
            raise ModelComponentError(
                f"{self.model_name!r}: {len(missing)} weights missing after load (e.g. {missing[:3]})",
                kind="load_error")
        model.eval().to(self.device)
        slot_ids = []
        for label in _LETTERS:
            enc = tokenizer.encode(label, add_special_tokens=False)
            if len(enc) != 1 or tokenizer.decode(enc) != label:
                raise ModelComponentError(f"answer slot {label!r} is not a single round-trip token",
                                          kind="load_error")
            slot_ids.append(enc[0])
        head = model.get_output_embeddings()
        self._slot_w = head.weight.detach().index_select(
            0, torch.tensor(slot_ids, device=head.weight.device)).to(torch.float32)
        self._slot_ids = slot_ids
        self._model, self._tokenizer = model, tokenizer

    # -- public API ------------------------------------------------------- #

    def decide_choice(self, state: Any, instructions: str, options: Dict[str, str]) -> Dict[str, float]:
        """Probabilities over ``options`` (label -> description), summing to 1."""
        if not 2 <= len(options) <= len(_LETTERS):
            raise ModelComponentError(f"choice needs 2..{len(_LETTERS)} options, got {len(options)}",
                                      kind="config_error")
        labels = list(options)
        suffix = (f"Question: {instructions}\n\nOptions:\n"
                  f"{_render_options(labels, [options[k] for k in labels])}\n\n"
                  f"Answer with one letter: {', '.join(_LETTERS[:len(labels)])}.")
        probs = self._run(state, suffix, len(labels))
        return dict(zip(labels, probs))

    def decide_yes_no(self, state: Any, instructions: str, true_description: str = _NOUL_TRUE,
                      false_description: str = _NOUL_FALSE) -> float:
        """P(yes) for a Noul-style question."""
        suffix = (f"Question: {instructions}\n\nOptions:\n"
                  f"{_render_options(['yes', 'no'], [true_description, false_description])}\n\n"
                  "Answer with one letter: A, B.")
        return self._run(state, suffix, 2)[0]

    # -- internals -------------------------------------------------------- #

    def _run(self, state: Any, suffix: str, n_slots: int) -> List[float]:
        self.load()
        torch = import_torch()
        started = time.perf_counter()
        messages = [
            {"role": "system", "content": _SYSTEM_ONE_SYSTEM},
            {"role": "user", "content": f"<state>\n{_render_state(state)}\n</state>\n\n{suffix}"},
        ]
        prompt = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        ids = self._tokenizer.encode(prompt, add_special_tokens=False)
        if len(ids) > self.max_prompt_tokens:
            raise ModelComponentError(
                f"decision-model prompt has {len(ids)} tokens > max_prompt_tokens={self.max_prompt_tokens}; "
                "refusing to truncate the state silently", kind="input_too_long")
        with torch.inference_mode():
            inp = torch.tensor([ids], device=self.device)
            hidden = self._model.model(input_ids=inp, use_cache=False, return_dict=True).last_hidden_state[:, -1]
            slot_logits = (hidden.to(torch.float32) @ self._slot_w[:n_slots].T)[0]
            vocab_head = self._model.get_output_embeddings()
            # share of the full-vocabulary mass that sits on the option letters (diagnostic)
            full = vocab_head(hidden.to(vocab_head.weight.dtype))[0].float()
            mass = float((torch.logsumexp(slot_logits, -1) - torch.logsumexp(full, -1)).exp())
            probs = torch.softmax(slot_logits, -1).tolist()
        if not all(math.isfinite(p) for p in probs):
            raise ModelComponentError("decision model produced non-finite probabilities", kind="backend_error")
        self.last_details = {
            "prompt_version": SYSTEM_ONE_PROMPT_VERSION,
            "prompt_tokens": len(ids),
            "slot_logits": slot_logits.tolist(),
            "allowed_token_mass": mass,
            "wall_ms": (time.perf_counter() - started) * 1000.0,
        }
        return probs

    def info(self) -> Dict[str, Any]:
        out = super().info()
        out["prompt_version"] = SYSTEM_ONE_PROMPT_VERSION
        return out


# --------------------------------------------------------------------------- #
# Official Qev HTTP client (OmniJev/OneJev "System One" servers)
# --------------------------------------------------------------------------- #

class QevHttpClient:
    """Client for an official Qev server (``qev serve --model OmniJev/OneJev1.6-*``).

    Wire format (from github.com/OmniJev/OneJev ``examples/request.json`` and a
    live Qev 0.1.4 server)::

        POST {base_url}/v1/systemone
        {"model": ..., "state": {...},
         "questions": {"q": {"type": "noul", "instructions": "<statement>"},
                       "c": {"type": "choice", "instructions": "<question>",
                             "criteria": {"<option>": "<description>", ...}}}}
        -> {"model": ..., "answers": {"q": {"type": "noul", "noul": P(yes)},
                                      "c": {"type": "choice", "choice": "<option>",
                                            "probabilities": {"<option>": p, ...}, ...}},
            "usage": {...}, "qev": {"prompt_version": ..., "timing": {...}}}

    Differences to :class:`SystemOneRunner`: the model runs **remotely** (latency
    includes the network, the server may be a shared GPU), the server renders the
    prompt itself, and probabilities arrive rounded to 6 decimals.

    Safety rules:

    * ``base_url`` is mandatory and explicit.  Only loopback hosts (e.g. an SSH
      tunnel on ``127.0.0.1``) are accepted unless ``allow_remote=True``, which
      must be set deliberately for any other host.
    * The first call checks ``GET /health`` and requires ``status == "ok"`` and
      ``model`` equal to the configured ``model``.  (A Qev server answers to every
      alias of every model name, so without this check a wrong port would silently
      be served by a different model.)
    * HTTP errors, timeouts, non-JSON bodies, missing/extra options, wrong answer
      types and non-finite or out-of-range probabilities raise
      :class:`ModelComponentError`.  Nothing is retried and no substitute value is
      ever returned.  This client never starts or stops a server.
    """

    backend = "qev_http"

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 60.0, allow_remote: bool = False):
        if not base_url:
            raise ModelComponentError("QevHttpClient: 'base_url' must be configured explicitly", kind="config_error")
        if not model or not isinstance(model, str):
            raise ModelComponentError("QevHttpClient: 'model' (e.g. OmniJev/OneJev1.6-0.8B) is required",
                                      kind="config_error")
        if isinstance(allow_remote, str) or not isinstance(allow_remote, bool):
            raise ModelComponentError(f"allow_remote must be a boolean, got {allow_remote!r}", kind="config_error")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise ModelComponentError(f"timeout_seconds must be a positive number, got {timeout_seconds!r}",
                                      kind="config_error")
        if allow_remote:
            parsed = urllib.parse.urlparse(base_url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise ModelComponentError(f"QevHttpClient: base_url must be an http(s) URL, got {base_url!r}",
                                          kind="config_error")
            self.base_url = base_url.rstrip("/")
        else:
            self.base_url = require_loopback_url(base_url, "QevHttpClient (set allow_remote: true to use a "
                                                            "non-loopback host)")
        self.model_name = model
        self.timeout_seconds = float(timeout_seconds)
        self.allow_remote = allow_remote
        self.device = "server"
        self.last_details: Dict[str, Any] = {}
        self._verified = False
        self._lock = threading.Lock()

    # -- transport ---------------------------------------------------------- #

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        import requests
        url = f"{self.base_url}{path}"
        try:
            if method == "GET":
                resp = requests.get(url, timeout=self.timeout_seconds)
            else:
                resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise ModelComponentError(f"Qev request {method} {url} failed: {type(exc).__name__}: {exc}",
                                      kind="backend_error") from exc
        if resp.status_code != 200:
            raise ModelComponentError(f"Qev server returned HTTP {resp.status_code} from {method} {url}: "
                                      f"{resp.text[:300]!r}", kind="backend_error")
        try:
            body = resp.json()
        except ValueError as exc:
            raise ModelComponentError(f"Qev server returned non-JSON from {url}: {resp.text[:200]!r}",
                                      kind="bad_response") from exc
        if not isinstance(body, dict):
            raise ModelComponentError(f"Qev server returned {type(body).__name__}, expected an object, from {url}",
                                      kind="bad_response")
        return body

    def health(self) -> Dict[str, Any]:
        """``GET /health``; raises unless the server reports ``status == "ok"`` and a ``model``."""
        body = self._request("GET", "/health")
        if body.get("status") != "ok" or not isinstance(body.get("model"), str):
            raise ModelComponentError(f"Qev /health at {self.base_url} is not healthy: {body!r}", kind="backend_error")
        return body

    def _ensure_ready(self) -> None:
        with self._lock:
            if self._verified:
                return
            served = self.health()["model"]
            if served != self.model_name:
                raise ModelComponentError(
                    f"Qev server at {self.base_url} serves {served!r} but the configured model is "
                    f"{self.model_name!r}; fix the port or the model name", kind="config_error")
            self._verified = True

    # -- public API ----------------------------------------------------------- #

    def system_one(self, state: Any, questions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Raw ``POST /v1/systemone``; returns the ``answers`` mapping after structural checks."""
        if not questions:
            raise ModelComponentError("Qev request needs at least one question", kind="config_error")
        self._ensure_ready()
        started = time.perf_counter()
        body = self._request("POST", "/v1/systemone", {"model": self.model_name, "state": state,
                                                       "questions": questions})
        wall_ms = (time.perf_counter() - started) * 1000.0
        answers = body.get("answers")
        if not isinstance(answers, dict) or set(answers) != set(questions):
            raise ModelComponentError(
                f"Qev response has answers for {sorted(answers) if isinstance(answers, dict) else answers!r}, "
                f"expected {sorted(questions)}", kind="bad_response")
        qev_meta = body.get("qev") if isinstance(body.get("qev"), dict) else {}
        timing = qev_meta.get("timing") if isinstance(qev_meta.get("timing"), dict) else {}
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        self.last_details = {
            "server": self.base_url, "server_model": body.get("model"),
            "prompt_version": qev_meta.get("prompt_version"), "prompt_sha256": qev_meta.get("prompt_sha256"),
            "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
            "server_total_s": timing.get("total_s"), "server_forward_s": timing.get("forward_s"),
            "wall_ms": wall_ms, "remote_inference": True,
        }
        return answers

    @staticmethod
    def _probability(value: Any, what: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
                or not -1e-6 <= value <= 1 + 1e-6:
            raise ModelComponentError(f"Qev response: {what} is {value!r}, not a probability", kind="bad_response")
        return float(value)

    def decide_yes_no(self, state: Any, instructions: str) -> float:
        """P(yes) for a ``noul`` question; ``instructions`` is a statement to be judged true or false."""
        answers = self.system_one(state, {"q": {"type": "noul", "instructions": instructions}})
        ans = answers["q"]
        if not isinstance(ans, dict) or ans.get("type") != "noul" or "noul" not in ans:
            raise ModelComponentError(f"Qev response is not a noul answer: {ans!r}", kind="bad_response")
        p = self._probability(ans["noul"], "noul")
        self.last_details["answer_type"] = "noul"
        return p

    def decide_choice(self, state: Any, instructions: str, options: Dict[str, str]) -> Dict[str, float]:
        """Probabilities over ``options`` (label -> description) for a ``choice`` question (sum to 1)."""
        if not isinstance(options, dict) or len(options) < 2:
            raise ModelComponentError("choice needs at least 2 options", kind="config_error")
        answers = self.system_one(state, {"q": {"type": "choice", "instructions": instructions,
                                                "criteria": dict(options)}})
        ans = answers["q"]
        if not isinstance(ans, dict) or ans.get("type") != "choice" or not isinstance(ans.get("probabilities"), dict):
            raise ModelComponentError(f"Qev response is not a choice answer: {ans!r}", kind="bad_response")
        raw = ans["probabilities"]
        if set(raw) != set(options):
            raise ModelComponentError(
                f"Qev response has options {sorted(raw)}, expected {sorted(options)}", kind="bad_response")
        probs = {k: self._probability(raw[k], f"probability of {k!r}") for k in options}
        total = sum(probs.values())
        if abs(total - 1.0) > 1e-3:
            raise ModelComponentError(f"Qev option probabilities sum to {total}, not 1", kind="bad_response")
        self.last_details.update({"answer_type": "choice", "choice": ans.get("choice"),
                                  "confidence": ans.get("confidence")})
        return probs

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "base_url": self.base_url, "model": self.model_name,
                "device": self.device, "timeout_seconds": self.timeout_seconds,
                "allow_remote": self.allow_remote, "remote_inference": True}


_RUNNERS: Dict[Tuple[str, str, Optional[str], bool, int], SystemOneRunner] = {}
_RUNNERS_LOCK = threading.Lock()


def get_system_one_runner(model: str, device: str = "auto", dtype: Optional[str] = None,
                          local_files_only: bool = False, max_prompt_tokens: int = 8192) -> SystemOneRunner:
    """Process-wide shared runner so a reranker and an NLI backend using the same
    decision model do not load the weights twice (16 GB unified memory)."""
    key = (model, (device or "auto"), dtype, bool(local_files_only), int(max_prompt_tokens))
    with _RUNNERS_LOCK:
        if key not in _RUNNERS:
            _RUNNERS[key] = SystemOneRunner(model, device, dtype, local_files_only, max_prompt_tokens)
        return _RUNNERS[key]
