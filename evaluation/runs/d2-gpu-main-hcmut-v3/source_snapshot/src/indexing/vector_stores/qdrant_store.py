"""Qdrant store via qdrant-client: embedded local mode (`path`) or a remote server (`url`).

Local mode scores by brute force (exact). On a remote server `exact: true` (default) asks Qdrant for an
exhaustive search; set `exact: false` for the HNSW index. Metadata filtering is native (payload filter on
`meta.<field>`); string/int values use MatchAny, other types are filtered after the search.
Remote mode is implemented against the same client API but is NOT exercised by the local test-suite
(no Qdrant server is run on this machine); connection failures raise BackendError.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

import numpy as np

from ..errors import BackendError, BackendUnavailableError, ConfigError
from ..types import Hit
from .base import VectorStore, lib_version

_NS = uuid.UUID("5f0a3b1e-8d2c-4c8e-9d57-3a0b1f6e7c11")


class QdrantStore(VectorStore):
    backend = "qdrant"
    native_filter = True

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.url: Optional[str] = self.params.get("url")
        self.api_key_env: Optional[str] = self.params.get("api_key_env")
        self.search_exact = bool(self.params.get("exact", True))
        self.exact = self.url is None or self.search_exact
        if self.url is None and self.path is None:
            raise ConfigError("qdrant: set `path` (embedded) or `url` (server)")

    @staticmethod
    def _pid(i: str) -> str:
        return str(uuid.uuid5(_NS, i))

    def _open(self, mode: str) -> None:
        try:
            from qdrant_client import QdrantClient, models
        except ImportError as exc:
            raise BackendUnavailableError("backend 'qdrant' needs the 'qdrant-client' package (uv pip install qdrant-client)") from exc
        self._models = models
        try:
            if self.url:
                key = os.environ.get(self.api_key_env) if self.api_key_env else None
                if self.api_key_env and not key:
                    raise ConfigError(f"qdrant: environment variable {self.api_key_env} is not set")
                self._client = QdrantClient(url=self.url, api_key=key, timeout=float(self.params.get("timeout_seconds", 30)))
            else:
                self.path.mkdir(parents=True, exist_ok=True)
                self._client = QdrantClient(path=str(self.path))
            exists = self._client.collection_exists(self.collection)
            self._prepare_dir(mode, exists)
            distance = models.Distance.COSINE if self.metric == "cosine" else models.Distance.DOT
            if exists and mode != "overwrite":
                params = self._client.get_collection(self.collection).config.params.vectors
                stored_metric = "cosine" if params.distance == models.Distance.COSINE else "ip"
                self._check_stored(int(params.size), stored_metric)
            else:
                if not self.dim:
                    raise BackendError("qdrant: dim is required to create a collection")
                if exists:
                    self._client.delete_collection(self.collection)
                self._client.create_collection(self.collection,
                                               vectors_config=models.VectorParams(size=self.dim, distance=distance))
        except (BackendError, ConfigError):
            raise
        except Exception as exc:
            raise BackendError(f"qdrant: cannot open {self.url or self.path}: {exc}") from exc

    def _upsert(self, ids, vectors, metadata) -> None:
        for m in metadata:
            if any("." in k for k in m):
                raise BackendError("qdrant: metadata field names must not contain '.'")
        points = [self._models.PointStruct(id=self._pid(i), vector=v.tolist(), payload={"__id": i, "meta": m})
                  for i, v, m in zip(ids, vectors, metadata)]
        try:
            for s in range(0, len(points), 256):
                self._client.upsert(self.collection, points=points[s:s + 256], wait=True)
        except Exception as exc:
            raise BackendError(f"qdrant: upsert failed: {exc}") from exc

    def _native_filter(self, flt):
        if not flt:
            return None
        must = []
        for field, values in flt.items():
            if all(isinstance(v, (str, int)) and not isinstance(v, bool) for v in values):
                must.append(self._models.FieldCondition(key=f"meta.{field}", match=self._models.MatchAny(any=values)))
            # other value types (float/bool): handled by the post-filter in VectorStore.search
        return self._models.Filter(must=must) if must else None

    def _search(self, vector, k, flt) -> List[Hit]:
        kwargs: Dict[str, Any] = {}
        if self.url:
            kwargs["search_params"] = self._models.SearchParams(exact=self.search_exact)
        native = self._native_filter(flt)

        def fetch(n: int) -> List[Hit]:
            try:
                res = self._client.query_points(self.collection, query=vector.tolist(), limit=n, query_filter=native,
                                                with_payload=True, **kwargs)
            except Exception as exc:
                raise BackendError(f"qdrant: search failed: {exc}") from exc
            return [Hit(p.payload["__id"], float(p.score), dict(p.payload.get("meta", {}))) for p in res.points]

        # values Qdrant cannot match natively (float/bool) need the candidate-growth post-filter
        needs_post = bool(flt) and any(not (isinstance(v, (str, int)) and not isinstance(v, bool))
                                       for vals in flt.values() for v in vals)
        return self._expanding_search(fetch, k, flt) if needs_post else fetch(k)

    def _delete(self, ids) -> None:
        try:
            self._client.delete(self.collection, points_selector=self._models.PointIdsList(points=[self._pid(i) for i in ids]), wait=True)
        except Exception as exc:
            raise BackendError(f"qdrant: delete failed: {exc}") from exc

    def count(self) -> int:
        try:
            return int(self._client.count(self.collection, exact=True).count)
        except Exception as exc:
            raise BackendError(f"qdrant: count failed: {exc}") from exc

    def persist(self) -> None:
        """Local mode writes through to its SQLite storage on every call; server mode is durable via `wait=True`."""

    def _close(self) -> None:
        self._client.close()

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "library": "qdrant-client", "version": lib_version("qdrant-client"),
                "mode": "remote" if self.url else "embedded-local", "url": self.url, "exact": self.exact,
                "metric": self.metric, "dim": self.dim, "count": self.count(), "native_filter": True,
                "filter": "payload filter on meta.<field>", "persistence": "qdrant local storage dir" if not self.url else "server",
                "path": str(self.path) if self.path else None}
