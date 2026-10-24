"""NumPy flat store: exact brute-force scoring, persisted as `<collection>.npy` + `<collection>.json`."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np

from ..errors import BackendError
from ..types import Hit, Metadata, matches_filter
from .base import VectorStore, atomic_write_json, lib_version


class NumpyFlatStore(VectorStore):
    backend = "numpy"
    exact = True
    native_filter = True  # boolean mask over the metadata list before scoring

    def _paths(self):
        return self.path / f"{self.collection}.npy", self.path / f"{self.collection}.json"

    def _open(self, mode: str) -> None:
        if self.path is None:
            raise BackendError("numpy: a local path is required")
        npy, js = self._paths()
        exists = npy.exists() and js.exists()
        self._prepare_dir(mode, exists)
        self.path.mkdir(parents=True, exist_ok=True)
        self._dirty = False
        if exists and mode != "overwrite":
            import json
            try:
                with open(js, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self._matrix = np.load(npy, allow_pickle=False)
            except (OSError, ValueError) as exc:
                raise BackendError(f"numpy: cannot read {npy}: {exc}") from exc
            ids = state["ids"]
            if self._matrix.shape[0] != len(ids) or len(state["metadata"]) != len(ids):
                raise BackendError(f"numpy: {npy} and {js} disagree on the row count (interrupted write?)")
            self._check_stored(int(state["dim"]), state["metric"])
            self._ids: List[str] = list(ids)
            self._meta: List[Metadata] = list(state["metadata"])
        else:
            self._matrix = np.zeros((0, self.dim or 0), dtype=np.float32)
            self._ids, self._meta = [], []
            self._dirty = True
        self._row: Dict[str, int] = {i: n for n, i in enumerate(self._ids)}

    def _upsert(self, ids, vectors, metadata) -> None:
        vectors = self._normalise(vectors)
        if self._matrix.shape[1] == 0:
            self._matrix = np.zeros((0, vectors.shape[1]), dtype=np.float32)
        new_rows = []
        for i, vec, meta in zip(ids, vectors, metadata):
            r = self._row.get(i)
            if r is None:
                self._row[i] = len(self._ids) + len(new_rows)
                new_rows.append((i, vec, meta))
            else:
                self._matrix[r] = vec
                self._meta[r] = meta
        if new_rows:
            self._matrix = np.concatenate([self._matrix, np.stack([v for _, v, _ in new_rows])], axis=0)
            self._ids.extend(i for i, _, _ in new_rows)
            self._meta.extend(m for _, _, m in new_rows)
        self._dirty = True

    def _search(self, vector, k, flt) -> List[Hit]:
        q = self._normalise(vector[None, :])[0]
        scores = self._matrix @ q
        if flt:
            allowed = np.fromiter((matches_filter(m, flt) for m in self._meta), dtype=bool, count=len(self._meta))
            idx = np.flatnonzero(allowed)
            scores_f = scores[idx]
        else:
            idx, scores_f = np.arange(len(scores)), scores
        if idx.size == 0:
            return []
        take = min(k, idx.size)
        if take < idx.size // 4:  # partial selection first, then exact ordering of the survivors
            part = np.argpartition(-scores_f, take - 1)[:take]
            cutoff = scores_f[part].min()
            cand = np.flatnonzero(scores_f >= cutoff)  # keep ties at the cutoff so tie-breaking by id is exact
        else:
            cand = np.arange(idx.size)
        order = sorted(cand.tolist(), key=lambda j: (-float(scores_f[j]), self._ids[idx[j]]))[:take]
        return [Hit(self._ids[idx[j]], float(scores_f[j]), dict(self._meta[idx[j]])) for j in order]

    def _delete(self, ids) -> None:
        drop = {self._row[i] for i in ids if i in self._row}
        if not drop:
            return
        keep = [n for n in range(len(self._ids)) if n not in drop]
        self._matrix = self._matrix[keep]
        self._ids = [self._ids[n] for n in keep]
        self._meta = [self._meta[n] for n in keep]
        self._row = {i: n for n, i in enumerate(self._ids)}
        self._dirty = True

    def export(self):
        """All rows as (ids, float32 matrix, metadata list); used to copy vectors into another backend without re-embedding."""
        return list(self._ids), self._matrix.copy(), [dict(m) for m in self._meta]

    def count(self) -> int:
        return len(self._ids)

    def persist(self) -> None:
        if not self._dirty:
            return
        npy, js = self._paths()
        tmp = npy.with_suffix(".npy.tmp")
        with open(tmp, "wb") as f:
            np.save(f, self._matrix, allow_pickle=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, npy)
        atomic_write_json(js, {"format": 1, "backend": self.backend, "dim": self.dim, "metric": self.metric,
                               "count": len(self._ids), "ids": self._ids, "metadata": self._meta})
        self._dirty = False

    def _close(self) -> None:
        self.persist()

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "library": "numpy", "version": np.__version__, "exact": True,
                "metric": self.metric, "dim": self.dim, "count": self.count(), "native_filter": True,
                "persistence": ".npy matrix + JSON ids/metadata", "path": str(self.path)}
