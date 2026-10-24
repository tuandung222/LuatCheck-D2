"""Chroma store via chromadb.PersistentClient. Approximate (HNSW index inside Chroma; no exact mode).

Scalar metadata fields are stored natively so `where` filtering is native; the full metadata dict is also kept
as JSON in `_meta_json` so values round-trip exactly.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import numpy as np

from ..errors import BackendError, BackendUnavailableError, ConfigError
from ..types import Hit, is_scalar
from .base import VectorStore, lib_version

_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]$")


class ChromaStore(VectorStore):
    backend = "chroma"
    exact = False
    native_filter = True

    def _open(self, mode: str) -> None:
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise BackendUnavailableError("backend 'chroma' needs the 'chromadb' package (uv pip install chromadb)") from exc
        if self.path is None:
            raise BackendError("chroma: a local path is required")
        if not _NAME_RE.match(self.collection):
            raise ConfigError("chroma: collection names are 3-512 chars of [a-zA-Z0-9._-], starting/ending alphanumeric")
        self.path.mkdir(parents=True, exist_ok=True)
        space = "cosine" if self.metric == "cosine" else "ip"
        hnsw = {
            "space": space,
            "ef_construction": int(self.params.get("ef_construction", 200)),
            "ef_search": int(self.params.get("ef_search", 128)),
            "max_neighbors": int(self.params.get("hnsw_m", 32)),
        }
        try:
            self._client = chromadb.PersistentClient(path=str(self.path), settings=Settings(anonymized_telemetry=False))
            names = [c if isinstance(c, str) else c.name for c in self._client.list_collections()]
            exists = self.collection in names
            self._prepare_dir(mode, exists)
            if exists and mode == "overwrite":
                self._client.delete_collection(self.collection)
                exists = False
            if exists:
                self._col = self._client.get_collection(self.collection, embedding_function=None)
                stored_space = (self._col.configuration or {}).get("hnsw", {}).get("space")
                if self._col.count() > 0:
                    emb = self._col.peek(1)["embeddings"]
                    self._check_stored(len(emb[0]), stored_space)
                else:
                    if stored_space != self.metric:
                        raise BackendError(f"chroma: stored metric {stored_space!r} != requested {self.metric!r}")
            else:
                self._col = self._client.create_collection(self.collection, embedding_function=None, configuration={"hnsw": hnsw})
            self._hnsw = hnsw
            self._batch = int(self._client.get_max_batch_size())
        except (BackendError, ConfigError):
            raise
        except Exception as exc:
            raise BackendError(f"chroma: cannot open {self.path}: {exc}") from exc

    @staticmethod
    def _native_meta(i: str, m: Dict[str, Any]) -> Dict[str, Any]:
        out = {k: v for k, v in m.items() if is_scalar(v) and v is not None}
        out["__id"] = i
        out["_meta_json"] = json.dumps(m, ensure_ascii=False)
        return out

    def _upsert(self, ids, vectors, metadata) -> None:
        try:
            for s in range(0, len(ids), self._batch):
                self._col.upsert(ids=ids[s:s + self._batch], embeddings=vectors[s:s + self._batch].tolist(),
                                 metadatas=[self._native_meta(i, m) for i, m in zip(ids[s:s + self._batch], metadata[s:s + self._batch])])
        except Exception as exc:
            raise BackendError(f"chroma: upsert failed: {exc}") from exc

    def _where(self, flt):
        if not flt:
            return None
        clauses = [{f: {"$in": values}} if len(values) > 1 else {f: {"$eq": values[0]}} for f, values in flt.items()]
        return clauses[0] if len(clauses) == 1 else {"$and": clauses}

    def _search(self, vector, k, flt) -> List[Hit]:
        try:
            res = self._col.query(query_embeddings=[vector.tolist()], n_results=min(k, self.count()), where=self._where(flt),
                                  include=["metadatas", "distances"])
        except Exception as exc:
            raise BackendError(f"chroma: search failed: {exc}") from exc
        hits = []
        for i, m, d in zip(res["ids"][0], res["metadatas"][0], res["distances"][0]):
            hits.append(Hit(i, 1.0 - float(d), json.loads(m["_meta_json"])))
        return hits

    def _delete(self, ids) -> None:
        try:
            self._col.delete(ids=ids)
        except Exception as exc:
            raise BackendError(f"chroma: delete failed: {exc}") from exc

    def count(self) -> int:
        return int(self._col.count())

    def persist(self) -> None:
        """PersistentClient writes through to its SQLite + HNSW segment files."""

    def _close(self) -> None:
        try:
            self._client.close()
        except AttributeError:
            pass
        self._col = None

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "library": "chromadb", "version": lib_version("chromadb"), "exact": False,
                "index": "HNSW", "hnsw": self._hnsw, "metric": self.metric, "dim": self.dim, "count": self.count(),
                "native_filter": True, "filter": "where on stored scalar fields", "persistence": "chroma PersistentClient dir",
                "path": str(self.path)}
