"""Embedding providers: local sentence-transformers, OpenAI-compatible HTTP, Ollama native.

All providers return float32 matrices of shape (n, dim), L2-normalised when `normalize` is true.
A failure (model cannot load, HTTP error, malformed response, NaN/zero vector, text longer than
the model supports) raises EmbeddingError; no provider ever returns placeholder vectors.
"""
from __future__ import annotations

import gc
import importlib.metadata
import ipaddress
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import numpy as np

from .errors import BackendUnavailableError, ConfigError, EmbeddingError, MemoryLimitError, TextTooLongError
from .resources import current_rss_mb, wait_for_quiet_machine


def _version(pkg: str) -> Optional[str]:
    try:
        return importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        return None


def _is_loopback(host: str) -> bool:
    if host in ("localhost",) or host.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class EmbeddingProvider(ABC):
    """Base class. Subclasses implement `_embed_raw`; this class validates and normalises."""

    kind: str = "abstract"

    def __init__(
        self,
        model: str,
        normalize: bool = True,
        batch_size: int = 8,
        document_prefix: str = "",
        query_prefix: str = "",
        max_tokens: Optional[int] = None,
        truncate_dim: Optional[int] = None,
    ):
        if batch_size < 1:
            raise ConfigError("embedding batch_size must be >= 1")
        if truncate_dim is not None and int(truncate_dim) < 1:
            raise ConfigError("embedding truncate_dim must be >= 1")
        self.model = model
        self.normalize = bool(normalize)
        self.batch_size = int(batch_size)
        self.document_prefix = document_prefix
        self.query_prefix = query_prefix
        self.max_tokens = max_tokens          # None = unknown (HTTP providers); chunk by characters then
        self.truncate_dim: Optional[int] = int(truncate_dim) if truncate_dim is not None else None
        self._dimension: Optional[int] = None
        self.stats: Dict[str, Any] = {"texts": 0, "seconds": 0.0, "calls": 0}

    # -- interface --------------------------------------------------------------------------
    @abstractmethod
    def _embed_raw(self, texts: List[str]) -> np.ndarray:
        """Embed one already-prefixed batch; return a (len(texts), dim) float array."""

    def token_offsets(self, text: str) -> Optional[List[Tuple[int, int]]]:
        """Character offsets of each token, or None when this provider has no tokenizer."""
        return None

    @property
    def has_tokenizer(self) -> bool:
        return False

    def close(self) -> None:
        """Release model memory / connections."""

    def load(self) -> None:
        """Eagerly load resources (no-op for HTTP providers)."""

    # -- public embedding API -----------------------------------------------------------------
    @property
    def dimension(self) -> Optional[int]:
        """Embedding dimension; None until known (after the first call or `probe_dimension`)."""
        return self._dimension

    def probe_dimension(self) -> int:
        vec = self.embed_documents(["dimension probe"])
        return int(vec.shape[1])

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed_many([self.document_prefix + t for t in texts])

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        return self._embed_many([self.query_prefix + t for t in texts])

    def _embed_many(self, texts: List[str]) -> np.ndarray:
        if not texts:
            raise EmbeddingError("no texts to embed")
        for i, t in enumerate(texts):
            if not isinstance(t, str) or not t.strip():
                raise EmbeddingError(f"text #{i} is empty; refusing to embed an empty string")
        t0 = time.perf_counter()
        parts: List[np.ndarray] = []
        for s in range(0, len(texts), self.batch_size):
            parts.append(self._validate(self._embed_raw(texts[s:s + self.batch_size]), len(texts[s:s + self.batch_size])))
        mat = np.concatenate(parts, axis=0).astype(np.float32, copy=False)
        self.stats["texts"] += len(texts)
        self.stats["calls"] += 1
        self.stats["seconds"] += time.perf_counter() - t0
        return mat

    def _validate(self, arr: Any, n: int) -> np.ndarray:
        try:
            mat = np.asarray(arr, dtype=np.float32)
        except (TypeError, ValueError) as exc:
            raise EmbeddingError(f"{self.kind}/{self.model}: malformed embedding payload: {exc}") from exc
        if mat.ndim != 2 or mat.shape[0] != n or mat.shape[1] < 1:
            raise EmbeddingError(f"{self.kind}/{self.model}: expected ({n}, dim) embeddings, got shape {mat.shape}")
        if not np.isfinite(mat).all():
            raise EmbeddingError(f"{self.kind}/{self.model}: embeddings contain NaN/Inf")
        if self.truncate_dim is not None:
            if mat.shape[1] < self.truncate_dim:
                raise EmbeddingError(
                    f"{self.kind}/{self.model}: cannot truncate {mat.shape[1]}-d embeddings to truncate_dim={self.truncate_dim}"
                )
            mat = mat[:, :self.truncate_dim]
        norms = np.linalg.norm(mat, axis=1)
        if (norms < 1e-12).any():
            raise EmbeddingError(f"{self.kind}/{self.model}: a zero-norm embedding was returned (refusing to use it)")
        if self._dimension is None:
            self._dimension = int(mat.shape[1])
        elif mat.shape[1] != self._dimension:
            raise EmbeddingError(f"{self.kind}/{self.model}: dimension changed from {self._dimension} to {mat.shape[1]}")
        if self.normalize:
            mat = mat / norms[:, None]
        return mat

    # -- description -----------------------------------------------------------------------------
    def info(self) -> Dict[str, Any]:
        d = {
            "provider": self.kind,
            "model": self.model,
            "dimension": self._dimension,
            "normalized": self.normalize,
            "max_tokens": self.max_tokens,
            "batch_size": self.batch_size,
            "document_prefix": self.document_prefix,
            "query_prefix": self.query_prefix,
        }
        if self.truncate_dim is not None:
            d["truncate_dim"] = self.truncate_dim
        return d

    def identity(self) -> Dict[str, Any]:
        """The fields that must match between an index build and later queries."""
        d = {
            "provider": self.kind,
            "model": self.model,
            "normalized": self.normalize,
            "document_prefix": self.document_prefix,
            "query_prefix": self.query_prefix,
        }
        if self.truncate_dim is not None:
            d["truncate_dim"] = self.truncate_dim
        return d

    @property
    def throughput(self) -> Optional[float]:
        s = self.stats["seconds"]
        return self.stats["texts"] / s if s > 0 else None


# =============================================================================================
# (a) local sentence-transformers
# =============================================================================================
class SentenceTransformerProvider(EmbeddingProvider):
    """Local sentence-transformers model on `mps` (Apple GPU) or `cpu`.

    The model is loaded once (explicitly or on first use), batches are small, text longer than
    `max_seq_length` raises TextTooLongError (chunk first), and RSS is checked after loading and
    after every batch against `max_rss_gb`.
    """

    kind = "sentence_transformers"

    def __init__(
        self,
        model: str = "AITeamVN/Vietnamese_Embedding",
        device: str = "auto",
        batch_size: int = 4,
        max_seq_length: Optional[int] = None,
        dtype: str = "float32",
        normalize: bool = True,
        document_prefix: str = "",
        query_prefix: str = "",
        max_rss_gb: Optional[float] = 4.0,
        local_files_only: bool = False,
        wait_for_quiet_machine_gb: Optional[float] = None,
        trust_remote_code: bool = False,
        truncate_dim: Optional[int] = None,
        config_kwargs: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            model, normalize, batch_size, document_prefix, query_prefix, max_tokens=None, truncate_dim=truncate_dim
        )
        if "embeddinggemma" in str(model).lower() and dtype == "float16":
            raise ConfigError(
                f"model {model!r} overflows float16 dynamic range (producing NaN); use dtype 'bfloat16' or 'float32'"
            )
        self.requested_device = device
        self.requested_max_seq_length = max_seq_length
        self.dtype = dtype
        self.max_rss_gb = max_rss_gb
        self.local_files_only = local_files_only
        self.wait_gb = wait_for_quiet_machine_gb
        self.trust_remote_code = trust_remote_code
        self.config_kwargs: Optional[Dict[str, Any]] = dict(config_kwargs) if config_kwargs is not None else None
        self._st: Any = None
        self._tok: Any = None
        self.device: Optional[str] = None
        self.load_seconds: Optional[float] = None
        self.memory_after_load_mb: Optional[float] = None
        self.memory_peak_seen_mb: float = 0.0
        self.model_revision: Optional[str] = None
        self.native_max_seq_length: Optional[int] = None

    # -- loading ---------------------------------------------------------------------------------
    def load(self) -> None:
        if self._st is not None:
            return
        import sys
        if "faiss" in sys.modules:
            from .vector_stores.faiss_store import FAISS_TORCH_CONFLICT
            raise BackendUnavailableError(FAISS_TORCH_CONFLICT)
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise BackendUnavailableError(
                "local embeddings need the 'sentence-transformers' and 'torch' packages "
                "(uv pip install --python .venv/bin/python -r requirements-indexing.txt)"
            ) from exc
        if self.wait_gb:
            wait_for_quiet_machine(self.wait_gb)
        device = self.requested_device
        if device == "auto":
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        if device not in ("mps", "cpu"):
            raise ConfigError(f"embedding device must be 'auto', 'mps' or 'cpu', got {device!r}")
        dtype_map = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}
        if self.dtype not in dtype_map:
            raise ConfigError(f"embedding dtype must be one of {sorted(dtype_map)}, got {self.dtype!r}")
        t0 = time.perf_counter()
        st_kwargs: Dict[str, Any] = {
            "device": device,
            "model_kwargs": {"dtype": dtype_map[self.dtype]},
            "local_files_only": self.local_files_only,
            "trust_remote_code": self.trust_remote_code,
        }
        if self.config_kwargs is not None:
            st_kwargs["config_kwargs"] = self.config_kwargs
        try:
            import transformers
            import sentence_transformers.base.modules.transformer as _st_tr

            _orig_proc_from_pretrained = _st_tr.AutoProcessor.from_pretrained

            def _safe_proc_from_pretrained(*args: Any, **kwargs: Any) -> Any:
                try:
                    return _orig_proc_from_pretrained(*args, **kwargs)
                except ImportError:
                    return transformers.AutoTokenizer.from_pretrained(*args, **kwargs)

            _st_tr.AutoProcessor.from_pretrained = _safe_proc_from_pretrained
            try:
                st = SentenceTransformer(self.model, **st_kwargs)
            finally:
                _st_tr.AutoProcessor.from_pretrained = _orig_proc_from_pretrained
        except Exception as exc:  # network, missing model, bad config: all surface as an embedding error
            raise EmbeddingError(f"cannot load embedding model {self.model!r} on {device}: {exc}") from exc
        cfg_obj = getattr(getattr(st[0], "auto_model", None) or getattr(st[0], "model", None), "config", None)
        positions = getattr(cfg_obj, "max_position_embeddings", None)
        if positions is None and hasattr(cfg_obj, "get_text_config"):
            positions = getattr(cfg_obj.get_text_config(), "max_position_embeddings", None)
        raw_max = st.max_seq_length
        native_max = int(raw_max) if (raw_max is not None and int(raw_max) <= 1_000_000) else int(positions or 8192)
        if self.requested_max_seq_length:
            if positions is not None and self.requested_max_seq_length > int(positions) - 2:
                raise ConfigError(
                    f"max_seq_length {self.requested_max_seq_length} exceeds the model's {positions} position embeddings"
                )
            st.max_seq_length = int(self.requested_max_seq_length)
        elif raw_max is None or int(raw_max) > 1_000_000:
            st.max_seq_length = native_max
        self.native_max_seq_length = native_max
        self._st = st
        tok = st.tokenizer
        self._tok = getattr(tok, "tokenizer", tok)
        self.max_tokens = int(st.max_seq_length)
        self.device = device
        self.load_seconds = time.perf_counter() - t0
        dim_fn = getattr(st, "get_embedding_dimension", None) or st.get_sentence_embedding_dimension
        raw_dim = int(dim_fn())
        if self.truncate_dim is not None:
            if self.truncate_dim > raw_dim:
                raise ConfigError(f"truncate_dim {self.truncate_dim} exceeds model's native dimension {raw_dim}")
            st.truncate_dim = self.truncate_dim
            self._dimension = int(self.truncate_dim)
        else:
            self._dimension = raw_dim
        self.model_revision = self._resolve_revision()
        self.memory_after_load_mb = self._check_memory("after model load")
        self.memory_peak_seen_mb = max(self.memory_peak_seen_mb, self.memory_after_load_mb)

    def _resolve_revision(self) -> Optional[str]:
        """Commit hash of the cached snapshot (last path component), when the model came from the HF cache."""
        try:
            from huggingface_hub import try_to_load_from_cache
            cached = try_to_load_from_cache(self.model, "config.json")
            return os.path.basename(os.path.dirname(cached)) if isinstance(cached, str) else None
        except Exception:
            return None

    def memory_mb(self) -> float:
        """Process RSS plus Metal-allocated memory. On `mps` the weights live in unified memory that
        RSS does not show (measured: ~0.5 GB RSS vs ~2.2 GB MPS allocation for this model)."""
        total = current_rss_mb()
        if self.device == "mps":
            import torch
            total += torch.mps.current_allocated_memory() / 2**20
        return total

    def _check_memory(self, where: str) -> float:
        used = self.memory_mb()
        if self.max_rss_gb is not None and used > self.max_rss_gb * 1024.0:
            raise MemoryLimitError(
                f"RSS + MPS memory {used / 1024.0:.2f} GB exceeds the limit of {self.max_rss_gb:.2f} GB ({where}); "
                "reduce batch_size / chunking.max_tokens or free memory"
            )
        return used

    @property
    def has_tokenizer(self) -> bool:
        return True

    def token_offsets(self, text: str) -> List[Tuple[int, int]]:
        self.load()
        enc = self._tok(text, add_special_tokens=False, return_offsets_mapping=True, truncation=False, verbose=False)
        return [(int(s), int(e)) for s, e in enc["offset_mapping"]]

    def token_count(self, text: str) -> int:
        """Token count including special tokens (what the model actually sees)."""
        self.load()
        return len(self._tok(text, add_special_tokens=True, truncation=False, verbose=False)["input_ids"])

    # -- embedding -------------------------------------------------------------------------------
    def _embed_raw(self, texts: List[str]) -> np.ndarray:
        self.load()
        lengths = [self.token_count(t) for t in texts]
        for t, n in zip(texts, lengths):
            if n > self.max_tokens:
                raise TextTooLongError(
                    f"text of {n} tokens exceeds the model limit of {self.max_tokens}; "
                    f"chunk it (src.indexing.chunking) instead of truncating: {t[:60]!r}..."
                )
        try:
            out = self._st.encode(
                texts, batch_size=len(texts), convert_to_numpy=True, normalize_embeddings=False, show_progress_bar=False
            )
            if self.device == "mps":
                import torch
                torch.mps.empty_cache()
        except Exception as exc:
            raise EmbeddingError(f"{self.model} inference failed on {self.device}: {exc}") from exc
        self.memory_peak_seen_mb = max(self.memory_peak_seen_mb, self._check_memory("during embedding"))
        return out

    def _embed_many(self, texts: List[str]) -> np.ndarray:
        # sort by length so batches pad little, then restore the caller's order
        self.load()
        if len(texts) > 1:
            order = np.argsort([len(t) for t in texts], kind="stable")
            mat = super()._embed_many([texts[i] for i in order])
            out = np.empty_like(mat)
            out[order] = mat
            return out
        return super()._embed_many(texts)

    def close(self) -> None:
        st, self._st, self._tok = self._st, None, None
        del st
        gc.collect()
        try:
            import torch
            if self.device == "mps":
                torch.mps.empty_cache()
        except Exception:
            pass

    def info(self) -> Dict[str, Any]:
        d = super().info()
        d.update(
            {
                "device": self.device or self.requested_device,
                "dtype": self.dtype,
                "model_revision": self.model_revision,
                "sentence_transformers": _version("sentence-transformers"),
                "torch": _version("torch"),
                "transformers": _version("transformers"),
                "native_max_seq_length": self.native_max_seq_length,
                "load_seconds": self.load_seconds,
                "memory_rss_plus_mps_after_load_mb": self.memory_after_load_mb,
                "max_rss_gb": self.max_rss_gb,
            }
        )
        if self.device == "mps":
            try:
                import torch
                d["mps_allocated_mb"] = torch.mps.current_allocated_memory() / 2**20
                d["mps_driver_allocated_mb"] = torch.mps.driver_allocated_memory() / 2**20
            except Exception:
                pass
        return d

    def identity(self) -> Dict[str, Any]:
        d = super().identity()
        d["dtype"] = self.dtype
        return d


# =============================================================================================
# (b)/(c) HTTP providers
# =============================================================================================
class _HttpProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str,
        endpoint: str,
        timeout_seconds: float = 60.0,
        allow_remote: bool = False,
        api_key_env: Optional[str] = None,
        dimension: Optional[int] = None,
        **kwargs: Any,
    ):
        super().__init__(model, **kwargs)
        parsed = urlparse(endpoint)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ConfigError(f"embedding endpoint must be an http(s) URL, got {endpoint!r}")
        if not _is_loopback(parsed.hostname) and not allow_remote:
            raise ConfigError(
                f"embedding endpoint host {parsed.hostname!r} is not loopback; set allow_remote: true to send text off this machine"
            )
        self.endpoint = endpoint.rstrip("/")
        self.timeout = float(timeout_seconds)
        self.api_key_env = api_key_env
        if dimension:
            self._expected_dimension = int(dimension)
        else:
            self._expected_dimension = None

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key_env:
            key = os.environ.get(self.api_key_env)
            if not key:
                raise ConfigError(f"environment variable {self.api_key_env} (embedding api key) is not set")
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _post(self, url: str, payload: Dict[str, Any]) -> Any:
        try:
            import requests
        except ImportError as exc:
            raise BackendUnavailableError("HTTP embedding providers need the 'requests' package") from exc
        try:
            resp = requests.post(url, data=json.dumps(payload), headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise EmbeddingError(f"embedding request to {url} failed: {exc}") from exc
        if resp.status_code != 200:
            raise EmbeddingError(f"embedding endpoint {url} returned HTTP {resp.status_code}: {resp.text[:300]}")
        try:
            return resp.json()
        except ValueError as exc:
            raise EmbeddingError(f"embedding endpoint {url} returned non-JSON: {resp.text[:200]!r}") from exc

    def _check_expected(self, mat: np.ndarray) -> np.ndarray:
        if self._expected_dimension and mat.shape[1] != self._expected_dimension:
            raise EmbeddingError(f"{self.model}: endpoint returned dimension {mat.shape[1]}, configured {self._expected_dimension}")
        return mat

    def info(self) -> Dict[str, Any]:
        d = super().info()
        d["endpoint"] = self.endpoint
        return d

    def identity(self) -> Dict[str, Any]:
        return super().identity()


class OpenAICompatibleProvider(_HttpProvider):
    """POST {endpoint}/embeddings (OpenAI schema): llama.cpp `--embeddings`, Ollama `/v1`, vLLM, gateways."""

    kind = "openai_compatible"

    def __init__(self, model: str, endpoint: str = "http://127.0.0.1:8081/v1", batch_size: int = 16, **kwargs: Any):
        super().__init__(model, endpoint, batch_size=batch_size, **kwargs)

    def _embed_raw(self, texts: List[str]) -> np.ndarray:
        body = self._post(f"{self.endpoint}/embeddings", {"model": self.model, "input": texts})
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbeddingError(f"{self.endpoint}/embeddings: expected {len(texts)} items in 'data', got {str(body)[:200]}")
        try:
            ordered = sorted(data, key=lambda item: item.get("index", 0))
            vectors = [item["embedding"] for item in ordered]
        except (KeyError, AttributeError, TypeError) as exc:
            raise EmbeddingError(f"{self.endpoint}/embeddings: malformed item in 'data': {exc}") from exc
        return self._check_expected(self._validate(vectors, len(texts)))


class OllamaProvider(_HttpProvider):
    """POST {host}/api/embed (Ollama native). `truncate` is sent as false: over-long input is an error."""

    kind = "ollama"

    def __init__(self, model: str, endpoint: str = "http://127.0.0.1:11434", batch_size: int = 16, **kwargs: Any):
        super().__init__(model, endpoint, batch_size=batch_size, **kwargs)

    def _embed_raw(self, texts: List[str]) -> np.ndarray:
        body = self._post(f"{self.endpoint}/api/embed", {"model": self.model, "input": texts, "truncate": False})
        vectors = body.get("embeddings") if isinstance(body, dict) else None
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise EmbeddingError(f"{self.endpoint}/api/embed: expected {len(texts)} embeddings, got {str(body)[:200]}")
        return self._check_expected(self._validate(vectors, len(texts)))


# =============================================================================================
# factory
# =============================================================================================
_ALIASES = {
    "sentence_transformers": "sentence_transformers", "sentence-transformers": "sentence_transformers",
    "local": "sentence_transformers", "st": "sentence_transformers", "transformers": "sentence_transformers",
    "openai": "openai_compatible", "openai_compatible": "openai_compatible", "openai-compatible": "openai_compatible",
    "llamacpp": "openai_compatible", "llama.cpp": "openai_compatible", "gateway": "openai_compatible",
    "ollama": "ollama",
}
_CLASSES = {"sentence_transformers": SentenceTransformerProvider, "openai_compatible": OpenAICompatibleProvider, "ollama": OllamaProvider}


def make_provider(cfg: Dict[str, Any]) -> EmbeddingProvider:
    """Build a provider from a `retrieval.embedding` config block."""
    cfg = dict(cfg or {})
    name = cfg.pop("provider", None)
    if name not in _ALIASES:
        raise ConfigError(f"embedding.provider must be one of {sorted(set(_ALIASES))}, got {name!r}")
    cls = _CLASSES[_ALIASES[name]]
    if "model" not in cfg:
        raise ConfigError("embedding.model is required")
    try:
        return cls(**cfg)
    except TypeError as exc:
        raise ConfigError(f"invalid embedding config for provider {name!r}: {exc}") from exc
