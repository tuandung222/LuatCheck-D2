"""VectorStore interface shared by every backend."""
from __future__ import annotations

import json
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from ..errors import BackendError, ConfigError
from ..types import Hit, Metadata, MetadataFilter, matches_filter, validate_filter

METRICS = ("cosine", "ip")
MODES = ("create", "overwrite", "open", "open_or_create")


class VectorStore(ABC):
    """Persistent vector index over (id, vector, metadata) rows.

    Contract shared by all backends:
      * `metric`: "cosine" or "ip" (inner product). Scores are similarities, higher is better:
        cosine -> cosine similarity in [-1, 1]; ip -> dot product. Ties are ordered by id.
      * `upsert` replaces rows with the same id. Metadata is a flat dict of JSON-serialisable values.
      * `search(vector, k, filter)`: `filter` is {field: value | [values]} (AND across fields, any-of
        within a list, strict equality). Where a backend has no native metadata filter the filter is
        applied after the vector search with the candidate list grown until `k` rows survive or the
        whole collection was examined (exact result, higher cost).
      * Failures raise BackendError (never an empty result, never another backend).
    """

    backend: str = "abstract"
    exact: bool = True          # exhaustive scoring (True) vs approximate index (False)
    native_filter: bool = False  # metadata filter evaluated inside the backend

    def __init__(self, path: Optional[str | Path], collection: str, dim: Optional[int], metric: str = "cosine", **params: Any):
        if metric not in METRICS:
            raise ConfigError(f"{self.backend}: metric must be one of {METRICS}, got {metric!r}")
        if not collection or not isinstance(collection, str):
            raise ConfigError(f"{self.backend}: collection name is required")
        self.path = Path(path) if path is not None else None
        self.collection = collection
        self.dim = int(dim) if dim else None
        self.metric = metric
        self.params = params
        self._closed = False

    # -- construction --------------------------------------------------------------------------
    @classmethod
    def open(cls, path: Optional[str | Path], collection: str, dim: Optional[int] = None, metric: str = "cosine",
             mode: str = "open_or_create", **params: Any) -> "VectorStore":
        """Create or open a collection. `mode`: create (error if present) | overwrite | open (error if absent)
        | open_or_create. When opening an existing collection `dim`/`metric` must match what is stored."""
        if mode not in MODES:
            raise ConfigError(f"mode must be one of {MODES}, got {mode!r}")
        store = cls(path, collection, dim, metric, **params)
        store._open(mode)
        return store

    @abstractmethod
    def _open(self, mode: str) -> None: ...

    @abstractmethod
    def _upsert(self, ids: List[str], vectors: np.ndarray, metadata: List[Metadata]) -> None: ...

    @abstractmethod
    def _search(self, vector: np.ndarray, k: int, flt: Optional[Dict[str, List[Any]]]) -> List[Hit]: ...

    @abstractmethod
    def _delete(self, ids: List[str]) -> None: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def persist(self) -> None: ...

    @abstractmethod
    def _close(self) -> None: ...

    @abstractmethod
    def info(self) -> Dict[str, Any]: ...

    # -- public API (validation, then delegate) ------------------------------------------------
    def upsert(self, ids: Sequence[str], vectors: Any, metadata: Optional[Sequence[Metadata]] = None) -> None:
        self._ensure_open()
        ids = [str(i) for i in ids]
        mat = np.asarray(vectors, dtype=np.float32)
        if mat.ndim != 2 or mat.shape[0] != len(ids):
            raise BackendError(f"{self.backend}: vectors must have shape ({len(ids)}, dim), got {mat.shape}")
        if self.dim is None:
            self.dim = int(mat.shape[1])
        if mat.shape[1] != self.dim:
            raise BackendError(f"{self.backend}: vector dimension {mat.shape[1]} != collection dimension {self.dim}")
        if not np.isfinite(mat).all():
            raise BackendError(f"{self.backend}: vectors contain NaN/Inf")
        if len(set(ids)) != len(ids):
            raise BackendError(f"{self.backend}: duplicate ids within one upsert call")
        if any(not i for i in ids):
            raise BackendError(f"{self.backend}: empty id")
        meta = [dict(m) for m in metadata] if metadata is not None else [{} for _ in ids]
        if len(meta) != len(ids):
            raise BackendError(f"{self.backend}: metadata length {len(meta)} != ids length {len(ids)}")
        if not ids:
            return
        self._upsert(ids, mat, meta)

    def search(self, vector: Any, k: int = 10, filter: Optional[MetadataFilter] = None) -> List[Hit]:
        self._ensure_open()
        if k < 1:
            raise BackendError("k must be >= 1")
        q = np.asarray(vector, dtype=np.float32).reshape(-1)
        if self.dim is not None and q.shape[0] != self.dim:
            raise BackendError(f"{self.backend}: query dimension {q.shape[0]} != collection dimension {self.dim}")
        if not np.isfinite(q).all():
            raise BackendError(f"{self.backend}: query contains NaN/Inf")
        try:
            flt = validate_filter(filter)
        except ValueError as exc:
            raise BackendError(f"{self.backend}: {exc}") from exc
        if self.count() == 0:
            return []
        hits = self._search(q, int(k), flt)
        hits = [h for h in hits if matches_filter(h.metadata, flt)]  # safety net; also the post-filter for non-native backends
        hits.sort(key=lambda h: (-h.score, h.id))
        return hits[:k]

    def delete(self, ids: Sequence[str]) -> None:
        self._ensure_open()
        ids = [str(i) for i in ids]
        if ids:
            self._delete(ids)

    def close(self) -> None:
        if not self._closed:
            self._close()
            self._closed = True

    def __enter__(self) -> "VectorStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- helpers -------------------------------------------------------------------------------
    def _ensure_open(self) -> None:
        if self._closed:
            raise BackendError(f"{self.backend}: store is closed")

    def _normalise(self, mat: np.ndarray) -> np.ndarray:
        """Unit-normalise rows when the metric is cosine (for backends that score by dot product)."""
        if self.metric != "cosine":
            return mat
        norms = np.linalg.norm(mat, axis=-1, keepdims=True)
        if (norms < 1e-12).any():
            raise BackendError(f"{self.backend}: zero-norm vector cannot be used with the cosine metric")
        return mat / norms

    def _expanding_search(self, fetch: Callable[[int], List[Hit]], k: int, flt: Optional[Dict[str, List[Any]]],
                          max_fetch: Optional[int] = None) -> List[Hit]:
        """Post-filtering with candidate growth: fetch(n) must return up to n best hits (unfiltered)."""
        total = self.count()
        cap = total if max_fetch is None else min(total, max_fetch)
        n = k if not flt else min(cap, max(4 * k, 64))
        n = max(1, min(n, cap))
        while True:
            hits = fetch(n)
            kept = [h for h in hits if matches_filter(h.metadata, flt)]
            if len(kept) >= k or len(hits) < n or n >= total:
                return kept
            if n >= cap:
                raise BackendError(
                    f"{self.backend}: filtered search needs more than {cap} candidates (backend limit); "
                    "use a backend with native metadata filtering"
                )
            n = min(cap, n * 4)

    def _prepare_dir(self, mode: str, existing: bool) -> None:
        if mode == "create" and existing:
            raise BackendError(f"{self.backend}: collection {self.collection!r} already exists at {self.path} (use mode='overwrite')")
        if mode == "open" and not existing:
            raise BackendError(f"{self.backend}: no collection {self.collection!r} at {self.path}")

    def _check_stored(self, stored_dim: int, stored_metric: str) -> None:
        if self.dim is not None and self.dim != stored_dim:
            raise BackendError(f"{self.backend}: stored dimension {stored_dim} != requested {self.dim}")
        if stored_metric != self.metric:
            raise BackendError(f"{self.backend}: stored metric {stored_metric!r} != requested {self.metric!r}")
        self.dim = stored_dim

    def size_on_disk(self) -> Optional[int]:
        """Bytes used by this collection's files (best effort; None for remote)."""
        if self.path is None:
            return None
        total = 0
        files = [self.path] if self.path.is_file() else [p for p in self.path.rglob("*") if p.is_file()]
        for f in files:
            total += f.stat().st_size
        return total


def atomic_write_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def lib_version(pkg: str) -> Optional[str]:
    import importlib.metadata
    try:
        return importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        return None
