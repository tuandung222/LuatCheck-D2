"""sqlite-vec store: a `vec0` virtual table (exact KNN, cosine) plus an items table for ids/metadata.

Metadata filtering is done after the KNN query (sqlite-vec caps `k` at 4096; a filtered search that would need
more candidates than that raises BackendError instead of returning a partial answer).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List

import numpy as np

from ..errors import BackendError, BackendUnavailableError, ConfigError
from ..types import Hit
from .base import VectorStore, lib_version

_MAX_K = 4096


class SqliteVecStore(VectorStore):
    backend = "sqlite_vec"
    exact = True
    native_filter = False

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        if self.metric != "cosine":
            raise ConfigError("sqlite_vec: only the cosine metric is supported (vec0 offers l2/cosine/hamming)")

    def _open(self, mode: str) -> None:
        try:
            import sqlite_vec
        except ImportError as exc:
            raise BackendUnavailableError("backend 'sqlite_vec' needs the 'sqlite-vec' package (uv pip install sqlite-vec)") from exc
        if self.path is None:
            raise BackendError("sqlite_vec: a local path is required")
        self.path.mkdir(parents=True, exist_ok=True)
        db_path = self.path / f"{self.collection}.sqlite"
        exists = db_path.exists()
        self._prepare_dir(mode, exists)
        if mode == "overwrite" and exists:
            for suffix in ("", "-wal", "-shm"):
                p = db_path.with_name(db_path.name + suffix)
                if p.exists():
                    p.unlink()
            exists = False
        self._db_path = db_path
        conn = sqlite3.connect(db_path, check_same_thread=False)
        if not hasattr(conn, "enable_load_extension"):
            raise BackendUnavailableError("sqlite_vec: this Python's sqlite3 was built without loadable-extension support")
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except (sqlite3.Error, OSError) as exc:
            raise BackendUnavailableError(f"sqlite_vec: cannot load the vec0 extension: {exc}") from exc
        self._conn = conn
        self._vec_version = conn.execute("SELECT vec_version()").fetchone()[0]
        try:
            if exists:
                row = dict(conn.execute("SELECT key, value FROM store_meta").fetchall())
                self._check_stored(int(row["dim"]), row["metric"])
            else:
                if not self.dim:
                    raise BackendError("sqlite_vec: dim is required to create a collection")
                conn.executescript(
                    "CREATE TABLE store_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
                    "CREATE TABLE items (rowid INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, metadata TEXT NOT NULL);"
                )
                conn.execute(f"CREATE VIRTUAL TABLE vec_items USING vec0(embedding float[{self.dim}] distance_metric=cosine)")
                conn.executemany("INSERT INTO store_meta VALUES (?, ?)",
                                 [("dim", str(self.dim)), ("metric", self.metric), ("backend", self.backend)])
                conn.commit()
        except sqlite3.Error as exc:
            raise BackendError(f"sqlite_vec: cannot open {db_path}: {exc}") from exc

    def _upsert(self, ids, vectors, metadata) -> None:
        import sqlite_vec
        c = self._conn
        try:
            for i, vec, meta in zip(ids, vectors, metadata):
                blob = sqlite_vec.serialize_float32(vec.tolist())
                row = c.execute("SELECT rowid FROM items WHERE id = ?", (i,)).fetchone()
                payload = json.dumps(meta, ensure_ascii=False)
                if row is None:
                    cur = c.execute("INSERT INTO items (id, metadata) VALUES (?, ?)", (i, payload))
                    rid = cur.lastrowid
                else:
                    rid = row[0]
                    c.execute("UPDATE items SET metadata = ? WHERE rowid = ?", (payload, rid))
                    c.execute("DELETE FROM vec_items WHERE rowid = ?", (rid,))
                c.execute("INSERT INTO vec_items (rowid, embedding) VALUES (?, ?)", (rid, blob))
            c.commit()
        except sqlite3.Error as exc:
            c.rollback()
            raise BackendError(f"sqlite_vec: upsert failed: {exc}") from exc

    def _search(self, vector, k, flt) -> List[Hit]:
        import sqlite_vec
        blob = sqlite_vec.serialize_float32(vector.tolist())

        def fetch(n: int) -> List[Hit]:
            try:
                rows = self._conn.execute(
                    "SELECT v.rowid, v.distance, i.id, i.metadata FROM vec_items v JOIN items i ON i.rowid = v.rowid "
                    "WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance", (blob, n)).fetchall()
            except sqlite3.Error as exc:
                raise BackendError(f"sqlite_vec: search failed: {exc}") from exc
            return [Hit(r[2], 1.0 - float(r[1]), json.loads(r[3])) for r in rows]

        return self._expanding_search(fetch, k, flt, max_fetch=_MAX_K)

    def _delete(self, ids) -> None:
        c = self._conn
        try:
            for i in ids:
                row = c.execute("SELECT rowid FROM items WHERE id = ?", (i,)).fetchone()
                if row:
                    c.execute("DELETE FROM vec_items WHERE rowid = ?", (row[0],))
                    c.execute("DELETE FROM items WHERE rowid = ?", (row[0],))
            c.commit()
        except sqlite3.Error as exc:
            c.rollback()
            raise BackendError(f"sqlite_vec: delete failed: {exc}") from exc

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM items").fetchone()[0])

    def persist(self) -> None:
        self._conn.commit()

    def _close(self) -> None:
        self._conn.commit()
        self._conn.close()

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "library": "sqlite-vec", "version": lib_version("sqlite-vec"),
                "extension_version": self._vec_version, "sqlite_version": sqlite3.sqlite_version, "exact": True,
                "metric": self.metric, "dim": self.dim, "count": self.count(), "native_filter": False,
                "filter": "post-filter with candidate growth (k <= 4096)", "persistence": "SQLite file", "path": str(self._db_path)}
