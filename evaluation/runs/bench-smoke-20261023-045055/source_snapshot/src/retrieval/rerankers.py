"""Pluggable re-rankers for retrieved candidates.

All backends score every (query, candidate) pair with a *real* model and return
the candidates sorted by that score.  If a model, runtime or server is
unavailable the call raises :class:`ModelComponentError`; there is no lexical or
rule-based fallback score (see AGENTS.md).

Score semantics differ by backend and are **not comparable across backends**:

==================  =========================================================
backend             score
==================  =========================================================
``cross_encoder``   raw relevance logit (higher = more relevant); optional
                    ``activation: sigmoid``
``qwen3``           P("yes") in [0, 1] from the yes/no next-token logits
                    (Qwen3-Reranker model-card formula)
``llama_cpp``       ``relevance_score`` returned by the server's /v1/rerank
``decision_model``  P(yes) in [0, 1] from a one-pass System-One yes/no decision
``qev_http``        P(yes) in [0, 1] of an official Qev server's ``noul`` answer
                    (remote inference; network latency included)
==================  =========================================================

Usage::

    reranker = build_reranker({"backend": "cross_encoder",
                               "model": "AITeamVN/Vietnamese_Reranker",
                               "top_k_in": 30, "top_k_out": 5})
    ranked = reranker.rerank(query, candidates)       # [(doc, score), ...]
    reranker.last_run                                   # timing / device / counts

``documents`` are the dicts produced by ``HybridDomainRetriever`` (``title`` and
``content`` are used by default) or plain strings.
"""
from __future__ import annotations

import abc
import math
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.model_runtime import (
    LazyComponent,
    ModelComponentError,
    QevHttpClient,
    doc_id,
    doc_text,
    get_system_one_runner,
    import_torch,
    reject_unknown_keys,
    require_loopback_url,
    resolve_device,
    resolve_dtype,
)

__all__ = [
    "BaseReranker",
    "CrossEncoderReranker",
    "Qwen3Reranker",
    "LlamaCppReranker",
    "DecisionModelReranker",
    "QevHttpReranker",
    "build_reranker",
    "ModelComponentError",
]

RankedDoc = Tuple[Any, float]


class BaseReranker(abc.ABC):
    """Interface: ``rerank(query, documents, top_k) -> [(doc, score), ...]`` (best first)."""

    backend = "base"

    def __init__(self, top_k_in: Optional[int] = None, top_k_out: Optional[int] = None,
                 text_fields: Sequence[str] = ("title", "content")):
        for name, value in (("top_k_in", top_k_in), ("top_k_out", top_k_out)):
            if value is not None and (not isinstance(value, int) or value < 1):
                raise ModelComponentError(f"{name} must be a positive integer or null, got {value!r}",
                                          kind="config_error")
        self.top_k_in = top_k_in
        self.top_k_out = top_k_out
        self.text_fields = tuple(text_fields)
        self.last_run: Dict[str, Any] = {}

    # ---- to implement -------------------------------------------------- #
    @abc.abstractmethod
    def _score_texts(self, query: str, texts: List[str]) -> List[float]:
        """Return one finite float per text, same order.  Raise on any failure."""

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "top_k_in": self.top_k_in, "top_k_out": self.top_k_out}

    # ---- public API ---------------------------------------------------- #
    def score(self, query: str, documents: Sequence[Any]) -> List[float]:
        """Scores in input order (no sorting, no ``top_k_in`` cut)."""
        texts = self._prepare(query, documents)
        return self._timed_score(query, texts, n_input=len(documents), n_dropped=0)

    def rerank(self, query: str, documents: Sequence[Any], top_k: Optional[int] = None) -> List[RankedDoc]:
        """Score and sort ``documents`` (best first, ties keep retrieval order).

        Only the first ``top_k_in`` candidates (retrieval order) are scored; the rest
        are dropped from the output and counted in ``last_run['n_dropped_unscored']``.
        The input list and its dicts are never mutated.  ``top_k`` overrides
        ``top_k_out``.
        """
        documents = list(documents)
        if not documents:
            self.last_run = {"backend": self.backend, "n_input": 0, "n_scored": 0, "n_returned": 0}
            return []
        n_dropped = 0
        if self.top_k_in is not None and len(documents) > self.top_k_in:
            n_dropped = len(documents) - self.top_k_in
            documents = documents[: self.top_k_in]
        texts = self._prepare(query, documents)
        scores = self._timed_score(query, texts, n_input=len(documents) + n_dropped, n_dropped=n_dropped)
        order = sorted(range(len(documents)), key=lambda i: (-scores[i], i))
        k = top_k if top_k is not None else self.top_k_out
        if k is not None:
            if not isinstance(k, int) or k < 1:
                raise ModelComponentError(f"top_k must be a positive integer, got {k!r}", kind="config_error")
            order = order[:k]
        ranked = [(documents[i], scores[i]) for i in order]
        self.last_run["n_returned"] = len(ranked)
        self.last_run["ranking"] = [
            {"rank": r + 1, "doc_id": doc_id(documents[i], i), "input_index": i, "score": scores[i]}
            for r, i in enumerate(order)
        ]
        return ranked

    # ---- internals ----------------------------------------------------- #
    def _prepare(self, query: str, documents: Sequence[Any]) -> List[str]:
        if not isinstance(query, str) or not query.strip():
            raise ModelComponentError("rerank query must be a non-empty string", kind="config_error")
        return [doc_text(d, self.text_fields) for d in documents]

    def _timed_score(self, query: str, texts: List[str], n_input: int, n_dropped: int) -> List[float]:
        if not texts:
            return []
        started = time.perf_counter()
        scores = self._score_texts(query, texts)
        wall_ms = (time.perf_counter() - started) * 1000.0
        if len(scores) != len(texts):
            raise ModelComponentError(
                f"{self.backend}: returned {len(scores)} scores for {len(texts)} documents", kind="bad_response")
        for s in scores:
            if not isinstance(s, (int, float)) or not math.isfinite(s):
                raise ModelComponentError(f"{self.backend}: non-finite score {s!r}", kind="bad_response")
        self.last_run = {
            "backend": self.backend, "n_input": n_input, "n_scored": len(texts), "n_dropped_unscored": n_dropped,
            "wall_ms": wall_ms, "ms_per_pair": wall_ms / len(texts), **self.info(),
        }
        return [float(s) for s in scores]


# --------------------------------------------------------------------------- #
# (a) Cross-encoder (XLM-R / BGE-reranker / AITeamVN Vietnamese_Reranker)
# --------------------------------------------------------------------------- #

class CrossEncoderReranker(LazyComponent, BaseReranker):
    """``AutoModelForSequenceClassification`` with a single relevance logit.

    Query and candidate are encoded as a pair and truncated ``longest_first`` to
    ``max_length`` (default 1024 to bound RAM on a 16 GB Mac; AITeamVN supports up
    to 2304 = 256 query + 2048 passage).  ``batch_size`` defaults to 1.
    ``last_run['n_truncated']`` counts candidates that exceeded ``max_length``.
    """

    backend = "cross_encoder"
    mps_supported = True

    def __init__(self, model: str, device: str = "auto", dtype: Optional[str] = None,
                 local_files_only: bool = False, max_length: int = 1024, batch_size: int = 1,
                 activation: str = "none", top_k_in: Optional[int] = None, top_k_out: Optional[int] = None,
                 text_fields: Sequence[str] = ("title", "content")):
        LazyComponent.__init__(self, model, device, dtype, local_files_only)
        BaseReranker.__init__(self, top_k_in, top_k_out, text_fields)
        if activation not in ("none", "sigmoid"):
            raise ModelComponentError("activation must be 'none' or 'sigmoid'", kind="config_error")
        self.max_length, self.batch_size, self.activation = int(max_length), int(batch_size), activation
        self._tok = self._model = None

    def _load(self) -> None:
        torch = import_torch()
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        self.device = resolve_device(self.requested_device, self.mps_supported)
        torch_dtype, self.dtype_name = resolve_dtype(self.requested_dtype, default="float32")
        common = {"local_files_only": self.local_files_only}
        self._tok = AutoTokenizer.from_pretrained(self.model_name, **common)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_name, dtype=torch_dtype, **common)
        if model.config.num_labels != 1:
            raise ModelComponentError(
                f"{self.model_name!r} has num_labels={model.config.num_labels}; a reranker needs 1",
                kind="config_error")
        self._model = model.eval().to(self.device)

    def info(self) -> Dict[str, Any]:
        return {**LazyComponent.info(self), "top_k_in": self.top_k_in, "top_k_out": self.top_k_out,
                "max_length": self.max_length, "activation": self.activation}

    def _score_texts(self, query: str, texts: List[str]) -> List[float]:
        self.load()
        torch = import_torch()
        out: List[float] = []
        n_truncated = 0
        with torch.inference_mode():
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start:start + self.batch_size]
                pairs = [[query, t] for t in batch]
                full = self._tok(pairs, truncation=False, padding=False)["input_ids"]
                n_truncated += sum(1 for ids in full if len(ids) > self.max_length)
                enc = self._tok(pairs, padding=True, truncation=True, max_length=self.max_length,
                                return_tensors="pt").to(self.device)
                logits = self._model(**enc, return_dict=True).logits.view(-1).float()
                if self.activation == "sigmoid":
                    logits = torch.sigmoid(logits)
                out.extend(logits.cpu().tolist())
        self._truncated = n_truncated
        return out

    def _timed_score(self, query, texts, n_input, n_dropped):
        scores = super()._timed_score(query, texts, n_input, n_dropped)
        if texts:
            self.last_run["n_truncated"] = getattr(self, "_truncated", 0)
        return scores


# --------------------------------------------------------------------------- #
# (b) Qwen3-Reranker (causal LM, yes/no scoring)
# --------------------------------------------------------------------------- #

_QWEN3_PREFIX = ("<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and "
                 "the Instruct provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n"
                 "<|im_start|>user\n")
_QWEN3_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
_QWEN3_DEFAULT_INSTRUCTION = "Given a web search query, retrieve relevant passages that answer the query"


class Qwen3Reranker(LazyComponent, BaseReranker):
    """Qwen3-Reranker via transformers, exactly the model-card procedure.

    Input: ``<Instruct>: ...\\n<Query>: ...\\n<Document>: ...`` wrapped in the
    model-card chat prefix/suffix; score = softmax over the ``no``/``yes`` logits of
    the final position, returning P(yes).  Left padding; ``max_length`` (the
    model card allows 8192; default here is 1024 to bound RAM), long pairs are truncated ``longest_first``.
    """

    backend = "qwen3"
    mps_supported = True

    def __init__(self, model: str, device: str = "auto", dtype: Optional[str] = None,
                 local_files_only: bool = False, max_length: int = 1024, batch_size: int = 1,
                 instruction: Optional[str] = None, top_k_in: Optional[int] = None,
                 top_k_out: Optional[int] = None, text_fields: Sequence[str] = ("title", "content")):
        LazyComponent.__init__(self, model, device, dtype, local_files_only)
        BaseReranker.__init__(self, top_k_in, top_k_out, text_fields)
        self.max_length, self.batch_size = int(max_length), int(batch_size)
        self.instruction = instruction or _QWEN3_DEFAULT_INSTRUCTION
        self._tok = self._model = None
        self._true_id = self._false_id = None
        self._prefix: List[int] = []
        self._suffix: List[int] = []

    def _load(self) -> None:
        import_torch()
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.device = resolve_device(self.requested_device, self.mps_supported)
        torch_dtype, self.dtype_name = resolve_dtype(self.requested_dtype, default="float32")
        common = {"local_files_only": self.local_files_only}
        tok = AutoTokenizer.from_pretrained(self.model_name, padding_side="left", **common)
        self._true_id = tok.convert_tokens_to_ids("yes")
        self._false_id = tok.convert_tokens_to_ids("no")
        if self._true_id is None or self._false_id is None or self._true_id == self._false_id:
            raise ModelComponentError(f"{self.model_name!r}: tokenizer has no distinct 'yes'/'no' tokens",
                                      kind="config_error")
        self._prefix = tok.encode(_QWEN3_PREFIX, add_special_tokens=False)
        self._suffix = tok.encode(_QWEN3_SUFFIX, add_special_tokens=False)
        model = AutoModelForCausalLM.from_pretrained(self.model_name, dtype=torch_dtype, **common)
        self._tok, self._model = tok, model.eval().to(self.device)

    def info(self) -> Dict[str, Any]:
        return {**LazyComponent.info(self), "top_k_in": self.top_k_in, "top_k_out": self.top_k_out,
                "max_length": self.max_length, "instruction": self.instruction}

    def _score_texts(self, query: str, texts: List[str]) -> List[float]:
        self.load()
        torch = import_torch()
        budget = self.max_length - len(self._prefix) - len(self._suffix)
        scores: List[float] = []
        with torch.inference_mode():
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start:start + self.batch_size]
                pairs = [f"<Instruct>: {self.instruction}\n<Query>: {query}\n<Document>: {t}" for t in batch]
                enc = self._tok(pairs, padding=False, truncation="longest_first",
                                return_attention_mask=False, max_length=budget)
                enc["input_ids"] = [self._prefix + ids + self._suffix for ids in enc["input_ids"]]
                enc = self._tok.pad(enc, padding=True, return_tensors="pt").to(self.device)
                logits = self._model(**enc, logits_to_keep=1).logits[:, -1, :].float()
                two = torch.stack([logits[:, self._false_id], logits[:, self._true_id]], dim=1)
                scores.extend(torch.log_softmax(two, dim=1)[:, 1].exp().cpu().tolist())
        return scores


# --------------------------------------------------------------------------- #
# (c) llama.cpp /v1/rerank client (loopback only)
# --------------------------------------------------------------------------- #

class LlamaCppReranker(BaseReranker):
    """Client for llama-server's reranking endpoint (``--reranking``, e.g. a
    Qwen3-Reranker or bge-reranker GGUF).

    Request: ``POST {endpoint}/v1/rerank`` with ``{"model", "query", "documents",
    "top_n"}``.  Response: ``{"results": [{"index": i, "relevance_score": s}, ...]}``.
    Every input index must appear exactly once or the call fails.  The endpoint
    host must be loopback.  A server started without ``--reranking`` answers with
    an HTTP error, which is raised (never converted to a score).
    This module never starts or stops a server.
    """

    backend = "llama_cpp"

    def __init__(self, endpoint: str, model: Optional[str] = None, timeout_seconds: float = 60.0,
                 top_k_in: Optional[int] = None, top_k_out: Optional[int] = None,
                 text_fields: Sequence[str] = ("title", "content")):
        super().__init__(top_k_in, top_k_out, text_fields)
        base = require_loopback_url(endpoint, "LlamaCppReranker")
        self.endpoint = base[:-3] if base.endswith("/v1") else base
        self.model_name = model
        self.timeout_seconds = float(timeout_seconds)
        self.device = "server"

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "endpoint": self.endpoint, "model": self.model_name,
                "device": self.device, "timeout_seconds": self.timeout_seconds,
                "top_k_in": self.top_k_in, "top_k_out": self.top_k_out}

    def _score_texts(self, query: str, texts: List[str]) -> List[float]:
        import requests
        payload: Dict[str, Any] = {"query": query, "documents": texts, "top_n": len(texts)}
        if self.model_name:
            payload["model"] = self.model_name
        url = f"{self.endpoint}/v1/rerank"
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise ModelComponentError(f"llama.cpp rerank request to {url} failed: {type(exc).__name__}: {exc}",
                                      kind="backend_error") from exc
        if resp.status_code != 200:
            raise ModelComponentError(
                f"llama.cpp rerank returned HTTP {resp.status_code} from {url}: {resp.text[:300]!r}",
                kind="backend_error")
        try:
            results = resp.json()["results"]
            scores: List[Optional[float]] = [None] * len(texts)
            for item in results:
                idx, val = item["index"], item["relevance_score"]
                if not isinstance(idx, int) or not 0 <= idx < len(texts) or scores[idx] is not None:
                    raise ValueError(f"bad or duplicate index {idx!r}")
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise ValueError(f"relevance_score for index {idx} is {val!r}")
                scores[idx] = float(val)
            if any(s is None for s in scores):
                raise ValueError("response is missing some document indices")
        except (ValueError, KeyError, TypeError) as exc:
            raise ModelComponentError(f"malformed llama.cpp rerank response: {type(exc).__name__}: {exc}",
                                      kind="bad_response") from exc
        return scores  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# (d) Decision-model (JEV / System One) reranker
# --------------------------------------------------------------------------- #

class DecisionModelReranker(BaseReranker):
    """Per-candidate yes/no question answered by a System-One decision model.

    State ``{"query": ..., "document": ...}``; question "Does the document contain
    information that answers the query?"; score = P(yes) from one forward pass per
    candidate (see ``SystemOneRunner`` for the exact protocol).  Candidates are
    scored sequentially.
    """

    backend = "decision_model"

    DEFAULT_QUESTION = "Does the document contain information that directly answers the query?"

    def __init__(self, model: str, device: str = "auto", dtype: Optional[str] = None,
                 local_files_only: bool = False, max_prompt_tokens: int = 1024,
                 question: Optional[str] = None, top_k_in: Optional[int] = None,
                 top_k_out: Optional[int] = None, text_fields: Sequence[str] = ("title", "content")):
        super().__init__(top_k_in, top_k_out, text_fields)
        self.runner = get_system_one_runner(model, device, dtype, local_files_only, max_prompt_tokens)
        self.question = question or self.DEFAULT_QUESTION

    @property
    def device(self) -> Optional[str]:
        return self.runner.device

    @property
    def load_error(self):
        return self.runner.load_error

    def load(self) -> "DecisionModelReranker":
        self.runner.load()
        return self

    def unload(self) -> None:
        self.runner.unload()

    def info(self) -> Dict[str, Any]:
        return {**self.runner.info(), "backend": self.backend, "question": self.question,
                "top_k_in": self.top_k_in, "top_k_out": self.top_k_out}

    def _score_texts(self, query: str, texts: List[str]) -> List[float]:
        return [
            self.runner.decide_yes_no(
                {"query": query, "document": text}, self.question,
                "the document contains information that answers the query",
                "the document does not answer the query")
            for text in texts
        ]


# --------------------------------------------------------------------------- #
# (e) Official Qev HTTP server (OneJev) reranker
# --------------------------------------------------------------------------- #

class QevHttpReranker(BaseReranker):
    """Per-candidate ``noul`` (yes/no) question sent to an official Qev server.

    State ``{"query": ..., "document": ...}``; statement "The document contains
    information that directly answers the query"; score = ``noul`` = P(yes) as
    returned by the server (rounded to 6 decimals, so near-certain candidates can
    tie; ties keep retrieval order).  One HTTP request per candidate, sequential.
    The model runs on the server (remote, possibly shared), not on this machine.
    ``base_url`` is mandatory and must be loopback (e.g. an SSH tunnel) unless
    ``allow_remote: true``.  Any HTTP/timeout/format error raises.
    """

    backend = "qev_http"

    DEFAULT_QUESTION = "The document contains information that directly answers the query"

    def __init__(self, base_url: str = "", model: str = "", timeout_seconds: float = 60.0,
                 allow_remote: bool = False, question: Optional[str] = None, top_k_in: Optional[int] = None,
                 top_k_out: Optional[int] = None, text_fields: Sequence[str] = ("title", "content")):
        super().__init__(top_k_in, top_k_out, text_fields)
        self.client = QevHttpClient(base_url, model, timeout_seconds, allow_remote)
        self.question = question or self.DEFAULT_QUESTION
        self.device = "server"

    def info(self) -> Dict[str, Any]:
        return {**self.client.info(), "backend": self.backend, "question": self.question,
                "top_k_in": self.top_k_in, "top_k_out": self.top_k_out}

    def _score_texts(self, query: str, texts: List[str]) -> List[float]:
        return [self.client.decide_yes_no({"query": query, "document": text}, self.question) for text in texts]


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #

_COMMON = ("backend", "top_k_in", "top_k_out", "text_fields")
_BACKENDS = {
    "cross_encoder": (CrossEncoderReranker,
                      _COMMON + ("model", "device", "dtype", "local_files_only", "max_length", "batch_size",
                                 "activation")),
    "qwen3": (Qwen3Reranker,
              _COMMON + ("model", "device", "dtype", "local_files_only", "max_length", "batch_size",
                         "instruction")),
    "llama_cpp": (LlamaCppReranker, _COMMON + ("endpoint", "model", "timeout_seconds")),
    "decision_model": (DecisionModelReranker,
                       _COMMON + ("model", "device", "dtype", "local_files_only", "max_prompt_tokens",
                                  "question")),
    "qev_http": (QevHttpReranker,
                 _COMMON + ("base_url", "model", "timeout_seconds", "allow_remote", "question")),
}
_ALIASES = {
    "cross-encoder": "cross_encoder", "crossencoder": "cross_encoder", "bge": "cross_encoder",
    "qwen3_reranker": "qwen3", "qwen3-reranker": "qwen3",
    "llamacpp": "llama_cpp", "llama.cpp": "llama_cpp", "llama-cpp": "llama_cpp",
    "jev": "decision_model", "system_one": "decision_model", "onejev": "decision_model",
    "qev": "qev_http", "qev-http": "qev_http",
}


def build_reranker(config: Optional[Dict[str, Any]]) -> Optional[BaseReranker]:
    """Build a reranker from ``retrieval.reranker`` config.

    Returns ``None`` only when the config is empty/``None`` or ``backend`` is
    ``"none"`` (re-ranking explicitly disabled by configuration).  Any other
    problem raises :class:`ModelComponentError`; unknown keys are rejected.
    """
    if not config:
        return None
    if not isinstance(config, dict):
        raise ModelComponentError("reranker config must be a mapping", kind="config_error")
    backend = str(config.get("backend", "")).strip().lower()
    if backend in ("none", "off", "disabled"):
        return None
    backend = _ALIASES.get(backend, backend)
    if backend not in _BACKENDS:
        raise ModelComponentError(
            f"unknown reranker backend {config.get('backend')!r}; use one of {sorted(_BACKENDS)}",
            kind="config_error")
    cls, allowed = _BACKENDS[backend]
    reject_unknown_keys(config, allowed, f"reranker[{backend}]")
    kwargs = {k: v for k, v in config.items() if k != "backend"}
    return cls(**kwargs)
