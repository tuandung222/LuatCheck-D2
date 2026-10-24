"""FAISS store: exact `IndexFlatIP` (default) or approximate `IndexHNSWFlat`, persisted as `.faiss` + JSON sidecar.

Metadata filtering is done after the vector search (FAISS has no metadata); the candidate list is grown
until `k` rows survive. HNSW cannot delete in place, so deletes/overwrites rebuild that index from the
stored vectors.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

import numpy as np

from ..errors import BackendError, BackendUnavailableError, ConfigError
from ..types import Hit, Metadata
from .base import VectorStore, atomic_write_json, lib_version


FAISS_TORCH_CONFLICT = (
    "faiss-cpu and torch each bundle their own libomp on macOS; one process that loads both aborts "
    "('OMP: Error #15') or segfaults (reproduced on this Mac with faiss-cpu 1.15.1 + torch 2.14.1, in both import orders, "
    "also with KMP_DUPLICATE_LIB_OK=TRUE). FAISS therefore refuses to load in a process where torch is imported, and the "
    "local sentence-transformers provider refuses to load in a process where faiss is imported. Use HTTP embeddings "
    "(ollama / openai_compatible) with FAISS, or write the FAISS store in a separate process with "
    "`python -m src.indexing add-store`."
)


def _faiss():
    import sys
    if "torch" in sys.modules:
        raise BackendUnavailableError(FAISS_TORCH_CONFLICT)
    try:
        import faiss
    except ImportError as exc:
        raise BackendUnavailableError("backend 'faiss' needs the 'faiss-cpu' package (uv pip install faiss-cpu)") from exc
    return faiss


class FaissStore(VectorStore):
    backend = "faiss"
    native_filter = False

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.index_type = str(self.params.get("index_type", "flat")).lower()
        if self.index_type not in ("flat", "hnsw"):
            raise ConfigError(f"faiss: index_type must be 'flat' or 'hnsw', got {self.index_type!r}")
        self.hnsw_m = int(self.params.get("hnsw_m", 32))
        self.ef_construction = int(self.params.get("ef_construction", 200))
        self.ef_search = int(self.params.get("ef_search", 128))
        self.exact = self.index_type == "flat"

    def _paths(self):
        return self.path / f"{self.collection}.faiss", self.path / f"{self.collection}.faiss.json"

    def _new_index(self, dim: int):
        faiss = _faiss()
        if self.index_type == "flat":
            sub = faiss.IndexFlatIP(dim)
        else:
            sub = faiss.IndexHNSWFlat(dim, self.hnsw_m, faiss.METRIC_INNER_PRODUCT)
            sub.hnsw.efConstruction = self.ef_construction
            sub.hnsw.efSearch = self.ef_search
        return faiss.IndexIDMap2(sub)

    def _open(self, mode: str) -> None:
        faiss = _faiss()
        if self.path is None:
            raise BackendError("faiss: a local path is required")
        idx_path, js_path = self._paths()
        exists = idx_path.exists() and js_path.exists()
        self._prepare_dir(mode, exists)
        self.path.mkdir(parents=True, exist_ok=True)
        self._dirty = False
        if exists and mode != "overwrite":
            try:
                with open(js_path, "r", encoding="utf-8") as f:
                    side = json.load(f)
                self._index = faiss.read_index(str(idx_path))
            except (OSError, RuntimeError, ValueError) as exc:
                raise BackendError(f"faiss: cannot read {idx_path}: {exc}") from exc
            self._check_stored(int(side["dim"]), side["metric"])
            if side["index_type"] != self.index_type:
                raise BackendError(f"faiss: stored index_type {side['index_type']!r} != requested {self.index_type!r}")
            self._int_of: Dict[str, int] = {k: int(v) for k, v in side["int_ids"].items()}
            self._meta: Dict[str, Metadata] = side["metadata"]
            self._next = int(side["next_int"])
            if self._index.ntotal != len(self._int_of):
                raise BackendError("faiss: index and sidecar disagree on the vector count (interrupted write?)")
            self._set_ef()
        else:
            self._index = None
            self._int_of, self._meta, self._next = {}, {}, 0
            self._dirty = True
            if self.dim:
                self._index = self._new_index(self.dim)
        self._id_of = {v: k for k, v in self._int_of.items()}

    def _set_ef(self) -> None:
        if self.index_type == "hnsw" and self._index is not None:
            _faiss().downcast_index(self._index.index).hnsw.efSearch = self.ef_search

    def _remove(self, ids: List[str]) -> None:
        faiss = _faiss()
        ints = np.array([self._int_of[i] for i in ids if i in self._int_of], dtype=np.int64)
        if ints.size == 0:
            return
        if self.index_type == "flat":
            self._index.remove_ids(ints)
        else:  # HNSW has no in-place removal: rebuild from the surviving vectors
            sub = faiss.downcast_index(self._index.index)
            all_ids = faiss.vector_to_array(self._index.id_map)
            vecs = sub.reconstruct_n(0, sub.ntotal)
            keep = ~np.isin(all_ids, ints)
            self._index = self._new_index(self.dim)
            if keep.any():
                self._index.add_with_ids(vecs[keep], all_ids[keep])
        for i in ids:
            n = self._int_of.pop(i, None)
            if n is not None:
                self._id_of.pop(n, None)
                self._meta.pop(i, None)

    def _upsert(self, ids, vectors, metadata) -> None:
        if self._index is None:
            self._index = self._new_index(self.dim)
        vectors = np.ascontiguousarray(self._normalise(vectors), dtype=np.float32)
        self._remove([i for i in ids if i in self._int_of])
        ints = np.arange(self._next, self._next + len(ids), dtype=np.int64)
        self._next += len(ids)
        self._index.add_with_ids(vectors, ints)
        for i, n, m in zip(ids, ints.tolist(), metadata):
            self._int_of[i], self._id_of[n], self._meta[i] = n, i, m
        self._set_ef()
        self._dirty = True

    def _search(self, vector, k, flt) -> List[Hit]:
        q = np.ascontiguousarray(self._normalise(vector[None, :]), dtype=np.float32)
        faiss = _faiss()

        def fetch(n: int) -> List[Hit]:
            if self.index_type == "hnsw":
                params = faiss.SearchParametersHNSW()
                params.efSearch = max(self.ef_search, n)
                D, I = self._index.search(q, n, params=params)
            else:
                D, I = self._index.search(q, n)
            return [Hit(self._id_of[int(j)], float(s), dict(self._meta[self._id_of[int(j)]]))
                    for s, j in zip(D[0], I[0]) if j != -1]

        return self._expanding_search(fetch, k, flt)

    def _delete(self, ids) -> None:
        if self._index is not None:
            self._remove(ids)
            self._dirty = True

    def count(self) -> int:
        return len(self._int_of)

    def persist(self) -> None:
        if not self._dirty:
            return
        faiss = _faiss()
        idx_path, js_path = self._paths()
        if self._index is None:
            self._index = self._new_index(self.dim or 1)
        tmp = idx_path.with_suffix(".faiss.tmp")
        faiss.write_index(self._index, str(tmp))
        tmp.replace(idx_path)
        atomic_write_json(js_path, {"format": 1, "backend": self.backend, "dim": self.dim, "metric": self.metric,
                                    "index_type": self.index_type, "next_int": self._next,
                                    "int_ids": self._int_of, "metadata": self._meta})
        self._dirty = False

    def _close(self) -> None:
        self.persist()
        self._index = None

    def info(self) -> Dict[str, Any]:
        d = {"backend": self.backend, "library": "faiss-cpu", "version": lib_version("faiss-cpu"),
             "exact": self.exact, "index_type": self.index_type, "metric": self.metric, "dim": self.dim,
             "count": self.count(), "native_filter": False, "filter": "post-filter with candidate growth",
             "persistence": ".faiss index + JSON id/metadata sidecar", "path": str(self.path)}
        if self.index_type == "hnsw":
            d.update({"hnsw_m": self.hnsw_m, "ef_construction": self.ef_construction, "ef_search": self.ef_search})
        return d
