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
``llama_cpp``       ``relevance_score`` returned by the server's /v1/rerank (raw
                    logit for a cross-encoder GGUF)
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

Long documents: ``cross_encoder`` and ``llama_cpp`` split a candidate longer than ``chunk_chars`` (default 1500
characters, ``null`` = off) into overlapping windows, score every (query, window) pair and use the **maximum** window
score as the document score (``last_run['n_chunks']``, ``['best_chunk']``).  Without this a long record is cut to its
first ``max_length`` tokens and evidence later in the record is never seen.

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

DEFAULT_CHUNK_CHARS = 1500
DEFAULT_CHUNK_OVERLAP = 200


def split_chunks(text: str, chunk_chars: int, overlap: int = DEFAULT_CHUNK_OVERLAP,
                 title_chars: int = 200) -> List[str]:
    """Split ``text`` into windows of about ``chunk_chars`` characters (deterministic, no model involved).

    A text that fits is returned unchanged.  Windows end at the last clause boundary (newline, ``. ``, ``; ``,
    ``: ``) in the final 30 % of the window, else at the last space; consecutive windows overlap by ``overlap``
    characters.  The first line of the text (the section title, when it is at most ``title_chars`` characters)
    is repeated in front of every later window so each chunk stays attributable to its section.
    """
    if len(text) <= chunk_chars:
        return [text]
    first_line = text.split("\n", 1)[0].strip()
    prefix = first_line + "\n" if 0 < len(first_line) <= title_chars and len(first_line) < chunk_chars // 3 else ""
    body_room = chunk_chars - len(prefix)
    n = len(text)

    def cut(lo: int, hi: int) -> int:
        if hi >= n:
            return n
        floor = lo + int((hi - lo) * 0.7)
        for sep in ("\n", ". ", "; ", ": ", " "):
            idx = text.rfind(sep, floor, hi)
            if idx != -1:
                return idx + len(sep)
        return hi
    chunks = []
    end = cut(0, chunk_chars)
    chunks.append(text[:end])
    while end < n:
        start = max(end - overlap, 0)
        nxt = text.find(" ", start, end)
        start = nxt + 1 if nxt != -1 else start
        end = cut(start, min(start + body_room, n))
        chunks.append(prefix + text[start:end].lstrip())
    return chunks


class BaseReranker(abc.ABC):
    """Interface: ``rerank(query, documents, top_k) -> [(doc, score), ...]`` (best first)."""

    backend = "base"

    def __init__(self, top_k_in: Optional[int] = None, top_k_out: Optional[int] = None,
                 text_fields: Sequence[str] = ("title", "content"), chunk_chars: Optional[int] = None,
                 chunk_overlap_chars: int = DEFAULT_CHUNK_OVERLAP):
        if chunk_chars is not None and (isinstance(chunk_chars, bool) or not isinstance(chunk_chars, int)
                                        or chunk_chars < 200):
            raise ModelComponentError(f"chunk_chars must be an integer >= 200 or null, got {chunk_chars!r}",
                                      kind="config_error")
        if (isinstance(chunk_overlap_chars, bool) or not isinstance(chunk_overlap_chars, int)
                or chunk_overlap_chars < 0 or (chunk_chars is not None and chunk_overlap_chars >= chunk_chars // 2)):
            raise ModelComponentError(
                f"chunk_overlap_chars must be an integer in [0, chunk_chars/2), got {chunk_overlap_chars!r}",
                kind="config_error")
        self.chunk_chars, self.chunk_overlap_chars = chunk_chars, chunk_overlap_chars
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
        n_chunks = best_chunks = None
        if self.chunk_chars:
            flat: List[str] = []
            owner: List[int] = []
            for i, text in enumerate(texts):
                parts = split_chunks(text, self.chunk_chars, self.chunk_overlap_chars)
                flat.extend(parts)
                owner.extend([i] * len(parts))
            flat_scores = self._score_texts(query, flat)
            if len(flat_scores) != len(flat):
                raise ModelComponentError(
                    f"{self.backend}: returned {len(flat_scores)} scores for {len(flat)} chunks", kind="bad_response")
            scores, best_chunks, n_chunks = [], [], len(flat)
            for i in range(len(texts)):
                idxs = [j for j, o in enumerate(owner) if o == i]
                best = max(idxs, key=lambda j: (flat_scores[j], -j))     # max over chunks, earliest chunk on ties
                scores.append(flat_scores[best])
                best_chunks.append(best - idxs[0])
        else:
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
        if n_chunks is not None:     # score of a document = max over its chunks; ms_per_pair is per document
            self.last_run.update({"n_chunks": n_chunks, "best_chunk": best_chunks})
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
                 text_fields: Sequence[str] = ("title", "content"), chunk_chars: Optional[int] = DEFAULT_CHUNK_CHARS,
                 chunk_overlap_chars: int = DEFAULT_CHUNK_OVERLAP):
        LazyComponent.__init__(self, model, device, dtype, local_files_only)
        BaseReranker.__init__(self, top_k_in, top_k_out, text_fields, chunk_chars, chunk_overlap_chars)
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
                "max_length": self.max_length, "activation": self.activation, "chunk_chars": self.chunk_chars,
                "chunk_overlap_chars": self.chunk_overlap_chars}

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
    """Client for llama-server's reranking endpoint (``llama-server --reranking``),
    e.g. a GGUF of ``AITeamVN/Vietnamese_Reranker`` / bge-reranker-v2-m3 or a
    Qwen3-Reranker (see ``scripts/reranker/serve_mac.sh``).

    Request: ``POST {endpoint}/v1/rerank`` with ``{"model", "query", "documents",
    "top_n"}``.  Response: ``{"results": [{"index": i, "relevance_score": s}, ...]}``.
    For a cross-encoder GGUF the score is the raw relevance logit of the model head
    (same scale as :class:`CrossEncoderReranker` with ``activation: none``).
    Every input index must appear exactly once or the call fails.  The endpoint
    host must be loopback.  A server started without ``--reranking`` answers with
    an HTTP error, which is raised (never converted to a score).
    This module never starts or stops a server.

    ``max_length`` (default 1024, ``None`` = no client-side limit) mirrors
    :class:`CrossEncoderReranker`: llama-server does not truncate, so a (query,
    passage) pair longer than ``max_length`` tokens (4 special tokens included) is
    cut ``longest_first`` here, using the *server's own* tokenizer (``/tokenize`` +
    ``/detokenize``, only called for passages that can exceed the limit).  Cut pairs
    are counted in ``last_run['n_truncated']``.  A pair that still exceeds the
    server's physical batch (``-ub``/``-c``) is rejected by the server and raised.

    The first call checks ``GET /v1/models`` (the server must answer and, when
    ``model`` is configured, serve a model/alias with that name) so that a wrong
    process on the port is an error rather than a silent answer.
    """

    backend = "llama_cpp"
    N_SPECIAL_TOKENS = 4          # <s> query </s></s> passage </s>  (XLM-RoBERTa pair template)

    def __init__(self, endpoint: str, model: Optional[str] = None, timeout_seconds: float = 60.0,
                 max_length: Optional[int] = 1024,
                 top_k_in: Optional[int] = None, top_k_out: Optional[int] = None,
                 text_fields: Sequence[str] = ("title", "content"), chunk_chars: Optional[int] = DEFAULT_CHUNK_CHARS,
                 chunk_overlap_chars: int = DEFAULT_CHUNK_OVERLAP):
        super().__init__(top_k_in, top_k_out, text_fields, chunk_chars, chunk_overlap_chars)
        base = require_loopback_url(endpoint, "LlamaCppReranker")
        self.endpoint = base[:-3] if base.endswith("/v1") else base
        self.model_name = model
        self.timeout_seconds = float(timeout_seconds)
        if max_length is not None and (isinstance(max_length, bool) or not isinstance(max_length, int)
                                       or max_length < 16):
            raise ModelComponentError(f"max_length must be an integer >= 16 or null, got {max_length!r}",
                                      kind="config_error")
        self.max_length = max_length
        self.device = "server"
        self._checked = False
        self._truncated = 0
        self._prompt_tokens: Optional[int] = None

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "endpoint": self.endpoint, "model": self.model_name,
                "device": self.device, "timeout_seconds": self.timeout_seconds, "max_length": self.max_length,
                "chunk_chars": self.chunk_chars, "chunk_overlap_chars": self.chunk_overlap_chars,
                "top_k_in": self.top_k_in, "top_k_out": self.top_k_out}

    # ---- HTTP helpers --------------------------------------------------- #
    _START_HINT = "start it with scripts/reranker/serve_mac.sh (this module never starts a server)"

    def _call(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        import requests
        url = f"{self.endpoint}{path}"
        try:
            resp = requests.request(method, url, json=payload, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise ModelComponentError(
                f"llama.cpp reranker server request to {url} failed: {type(exc).__name__}: {exc}; "
                f"{self._START_HINT}", kind="backend_error") from exc
        if resp.status_code != 200:
            raise ModelComponentError(
                f"llama.cpp reranker server returned HTTP {resp.status_code} from {url}: {resp.text[:300]!r}",
                kind="backend_error")
        try:
            return resp.json()
        except ValueError as exc:
            raise ModelComponentError(f"llama.cpp reranker server returned non-JSON from {url}: {resp.text[:200]!r}",
                                      kind="bad_response") from exc

    def _check_server(self) -> None:
        body = self._call("GET", "/v1/models")
        try:
            names = set()
            for item in body["data"]:
                names.add(str(item.get("id")))
                names.update(str(a) for a in (item.get("aliases") or []))
                names.add(str(item.get("name")))
        except (KeyError, TypeError, AttributeError) as exc:
            raise ModelComponentError(f"malformed llama.cpp /v1/models response: {body!r:.200}",
                                      kind="bad_response") from exc
        if self.model_name and self.model_name not in names:
            raise ModelComponentError(
                f"llama.cpp server at {self.endpoint} serves {sorted(names)}, not the configured model "
                f"{self.model_name!r}", kind="config_error")
        self._checked = True

    def _tokenize(self, text: str) -> List[int]:
        body = self._call("POST", "/tokenize", {"content": text, "add_special": False})
        try:
            return [int(t) for t in body["tokens"]]
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelComponentError(f"malformed llama.cpp /tokenize response: {str(body)[:200]}",
                                      kind="bad_response") from exc

    def _detokenize(self, tokens: List[int]) -> str:
        body = self._call("POST", "/detokenize", {"tokens": tokens})
        if not isinstance(body, dict) or not isinstance(body.get("content"), str):
            raise ModelComponentError(f"malformed llama.cpp /detokenize response: {str(body)[:200]}",
                                      kind="bad_response")
        return body["content"]

    @staticmethod
    def _longest_first(len_a: int, len_b: int, budget: int) -> Tuple[int, int]:
        """Token counts kept by HF ``truncation='longest_first'`` (ties trim the passage first)."""
        over = len_a + len_b - budget
        if over <= 0:
            return len_a, len_b
        trim = min(over, abs(len_a - len_b))
        if len_a > len_b:
            len_a -= trim
        else:
            len_b -= trim
        over -= trim
        return len_a - over // 2, len_b - (over - over // 2)

    def _fit(self, query: str, texts: List[str]) -> Tuple[str, List[str]]:
        """Apply ``max_length`` to (query, passage) pairs; returns the query and passages to send."""
        self._truncated = 0
        if self.max_length is None:
            return query, texts
        budget = self.max_length - self.N_SPECIAL_TOKENS
        # A SentencePiece token covers at least one character, so short texts cannot exceed the budget.
        if len(query) + max(len(t) for t in texts) <= budget:
            return query, texts
        q_tok = self._tokenize(query)
        new_q_tok, out = q_tok, []
        for text in texts:
            if len(query) + len(text) <= budget:
                out.append(text)
                continue
            t_tok = self._tokenize(text)
            keep_q, keep_t = self._longest_first(len(q_tok), len(t_tok), budget)
            if keep_t < len(t_tok) or keep_q < len(q_tok):
                self._truncated += 1
            if keep_q < len(q_tok):
                new_q_tok = q_tok[:keep_q]
            out.append(self._detokenize(t_tok[:keep_t]) if keep_t < len(t_tok) else text)
        if new_q_tok is not q_tok:     # query itself cut (pathologically long query): same cut for every passage
            query = self._detokenize(new_q_tok)
        return query, out

    def _timed_score(self, query, texts, n_input, n_dropped):
        scores = super()._timed_score(query, texts, n_input, n_dropped)
        if texts:
            self.last_run["n_truncated"] = self._truncated
            self.last_run["server_prompt_tokens"] = self._prompt_tokens
        return scores

    def _score_texts(self, query: str, texts: List[str]) -> List[float]:
        if not self._checked:
            self._check_server()
        query, texts = self._fit(query, texts)
        payload: Dict[str, Any] = {"query": query, "documents": texts, "top_n": len(texts)}
        if self.model_name:
            payload["model"] = self.model_name
        url = f"{self.endpoint}/v1/rerank"
        body = self._call("POST", "/v1/rerank", payload)
        try:
            results = body["results"]
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
            self._prompt_tokens = (body.get("usage") or {}).get("prompt_tokens")
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ModelComponentError(f"malformed llama.cpp rerank response from {url}: {type(exc).__name__}: {exc}",
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
                                 "activation", "chunk_chars", "chunk_overlap_chars")),
    "qwen3": (Qwen3Reranker,
              _COMMON + ("model", "device", "dtype", "local_files_only", "max_length", "batch_size",
                         "instruction")),
    "llama_cpp": (LlamaCppReranker, _COMMON + ("endpoint", "model", "timeout_seconds", "max_length",
                                               "chunk_chars", "chunk_overlap_chars")),
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
