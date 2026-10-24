"""Corpus loading, record normalisation and the persisted RecordStore."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from .errors import ConfigError, IndexingError
from .types import Metadata, is_scalar

# Fields that never go into vector-store metadata (the full record lives in the RecordStore).
_TEXT_FIELDS = ("content", "text")
MAX_VECTOR_METADATA_STR = 256


def nfc(text: str) -> str:
    """Unicode NFC. Vietnamese text can arrive precomposed or decomposed; indexes use NFC only."""
    return unicodedata.normalize("NFC", text)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def record_id(record: Dict[str, Any]) -> str:
    rid = record.get("doc_id") or record.get("article_id") or record.get("id")
    return str(rid).strip() if rid not in (None, "") else ""


def load_corpus(path: str | Path, default_collection_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load a JSON list of records; every record needs doc_id/article_id/id and non-empty content."""
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"corpus file not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ConfigError(f"{p}: expected a JSON list of records, got {type(data).__name__}")
    out: List[Dict[str, Any]] = []
    for i, rec in enumerate(data):
        if not isinstance(rec, dict):
            raise ConfigError(f"{p}[{i}]: record is not an object")
        rid = record_id(rec)
        if not rid:
            raise ConfigError(f"{p}[{i}]: record has no doc_id/article_id/id")
        content = rec.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ConfigError(f"{p}[{i}] ({rid}): record has no content")
        norm = dict(rec)
        norm["doc_id"] = rid
        norm["content"] = nfc(content)
        if isinstance(norm.get("title"), str):
            norm["title"] = nfc(norm["title"])
        elif isinstance(norm.get("section_title"), str):
            norm["title"] = nfc(norm["section_title"])
        else:
            norm["title"] = ""
        if default_collection_id and not norm.get("collection_id"):
            norm["collection_id"] = default_collection_id
        out.append(norm)
    return out


def vector_metadata(record: Dict[str, Any], fields: Optional[Sequence[str]] = None) -> Metadata:
    """Scalar metadata carried next to each vector.

    `fields=None`: every scalar field except content/text and strings longer than
    MAX_VECTOR_METADATA_STR (long strings stay in the RecordStore). Explicit `fields`
    are taken as listed (missing ones skipped; non-scalar values are an error).
    """
    meta: Metadata = {}
    if fields is None:
        for k, v in record.items():
            if k in _TEXT_FIELDS or not is_scalar(v) or v is None:
                continue
            if isinstance(v, str) and len(v) > MAX_VECTOR_METADATA_STR:
                continue
            meta[k] = v
    else:
        for k in fields:
            if k not in record or record[k] is None:
                continue
            v = record[k]
            if not is_scalar(v):
                raise ConfigError(f"vector metadata field {k!r} of {record.get('doc_id')} is not a scalar")
            meta[k] = v
    meta["doc_id"] = record["doc_id"]
    return meta


class RecordStore:
    """Persisted full records (SQLite), keyed by doc_id, in corpus order."""

    FILENAME = "records.sqlite"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._conn: Optional[sqlite3.Connection] = None

    # -- lifecycle -------------------------------------------------------------------------
    def create(self, records: Sequence[Dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.path.unlink()
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.execute("CREATE TABLE records (doc_id TEXT PRIMARY KEY, ord INTEGER NOT NULL, data TEXT NOT NULL)")
        conn.executemany(
            "INSERT INTO records (doc_id, ord, data) VALUES (?, ?, ?)",
            [(r["doc_id"], i, json.dumps(r, ensure_ascii=False)) for i, r in enumerate(records)],
        )
        conn.commit()
        self._conn = conn

    def open(self) -> "RecordStore":
        if not self.path.is_file():
            raise IndexingError(f"record store not found: {self.path}")
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        return self

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- access -----------------------------------------------------------------------------
    def _c(self) -> sqlite3.Connection:
        if self._conn is None:
            raise IndexingError("record store is not open")
        return self._conn

    def count(self) -> int:
        return int(self._c().execute("SELECT COUNT(*) FROM records").fetchone()[0])

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        row = self._c().execute("SELECT data FROM records WHERE doc_id = ?", (doc_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def get_normalised(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Lookup tolerant to case and spaces-vs-underscores (generic; no domain aliases)."""
        if not doc_id:
            return None
        clean = str(doc_id).strip()
        for cand in (clean, clean.replace(" ", "_")):
            rec = self.get(cand)
            if rec:
                return rec
        low = clean.replace(" ", "_").lower()
        row = self._c().execute("SELECT data FROM records WHERE lower(doc_id) = ?", (low,)).fetchone()
        return json.loads(row[0]) if row else None

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        for (data,) in self._c().execute("SELECT data FROM records ORDER BY ord"):
            yield json.loads(data)
