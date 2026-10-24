"""LanceDB store (embedded, columnar files on disk). Exact flat search (no ANN index is created).

Metadata is stored as a JSON column and filtered after the vector search (candidate growth).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

import numpy as np

from ..errors import BackendError, BackendUnavailableError
from ..types import Hit
from .base import VectorStore, atomic_write_json, lib_version


def _sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


class LanceDBStore(VectorStore):
    backend = "lancedb"
    exact = True
    native_filter = False

    def _open(self, mode: str) -> None:
        try:
            import lancedb
            import pyarrow as pa
        except ImportError as exc:
            raise BackendUnavailableError("backend 'lancedb' needs the 'lancedb' package (uv pip install lancedb)") from exc
        if self.path is None:
            raise BackendError("lancedb: a local path is required")
        self.path.mkdir(parents=True, exist_ok=True)
        side = self.path / f"{self.collection}.store.json"
        try:
            self._db = lancedb.connect(str(self.path))
            exists = self.collection in self._table_names() and side.exists()
            self._prepare_dir(mode, exists)
            if exists and mode != "overwrite":
                stored = json.loads(side.read_text(encoding="utf-8"))
                self._check_stored(int(stored["dim"]), stored["metric"])
                self._table = self._db.open_table(self.collection)
            else:
                if not self.dim:
                    raise BackendError("lancedb: dim is required to create a collection")
                schema = pa.schema([
                    pa.field("id", pa.string()),
                    pa.field("vector", pa.list_(pa.float32(), self.dim)),
                    pa.field("metadata", pa.string()),
                ])
                self._table = self._db.create_table(self.collection, schema=schema, mode="overwrite")
                atomic_write_json(side, {"backend": self.backend, "dim": self.dim, "metric": self.metric})
        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(f"lancedb: cannot open {self.path}: {exc}") from exc

    def _table_names(self) -> List[str]:
        if hasattr(self._db, "list_tables"):  # lancedb >= 0.3x; table_names() is deprecated
            res = self._db.list_tables()
            return list(getattr(res, "tables", res))
        return list(self._db.table_names())

    def _upsert(self, ids, vectors, metadata) -> None:
        rows = [{"id": i, "vector": v.tolist(), "metadata": json.dumps(m, ensure_ascii=False)}
                for i, v, m in zip(ids, vectors, metadata)]
        try:
            (self._table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(rows))
        except Exception as exc:
            raise BackendError(f"lancedb: upsert failed: {exc}") from exc

    def _search(self, vector, k, flt) -> List[Hit]:
        metric = "cosine" if self.metric == "cosine" else "dot"

        def fetch(n: int) -> List[Hit]:
            try:
                rows = self._table.search(vector.tolist()).metric(metric).limit(n).to_list()
            except Exception as exc:
                raise BackendError(f"lancedb: search failed: {exc}") from exc
            # both lance distances are "1 - similarity"
            return [Hit(r["id"], 1.0 - float(r["_distance"]), json.loads(r["metadata"])) for r in rows]

        return self._expanding_search(fetch, k, flt)

    def _delete(self, ids) -> None:
        try:
            self._table.delete("id IN (" + ", ".join(_sql_quote(i) for i in ids) + ")")
        except Exception as exc:
            raise BackendError(f"lancedb: delete failed: {exc}") from exc

    def count(self) -> int:
        return int(self._table.count_rows())

    def persist(self) -> None:
        """LanceDB commits every write as a new table version; nothing to flush."""

    def _close(self) -> None:
        self._table = None
        self._db = None

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "library": "lancedb", "version": lib_version("lancedb"),
                "pylance": lib_version("pylance"), "exact": True, "metric": self.metric, "dim": self.dim,
                "count": self.count(), "native_filter": False, "filter": "post-filter with candidate growth",
                "persistence": "Lance columnar dataset (versioned)", "path": str(self.path)}
