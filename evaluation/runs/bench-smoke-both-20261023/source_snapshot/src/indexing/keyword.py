"""Keyword indexes behind one interface: persisted SQLite FTS5 and the existing in-memory BM25.

Scores are lexical proxies (BM25-style term statistics); they say nothing about answer correctness.
"""
from __future__ import annotations

import json
import re
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .errors import BackendError, BackendUnavailableError, ConfigError
from .records import nfc
from .types import Hit, Metadata, MetadataFilter, matches_filter, validate_filter

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def query_tokens(text: str) -> List[str]:
    """NFC + lowercase + Unicode word tokens (Vietnamese syllables are whitespace-delimited)."""
    return _TOKEN_RE.findall(nfc(text).lower())


@dataclass
class KeywordDoc:
    doc_id: str
    title: str
    content: str
    metadata: Metadata


class KeywordIndex(ABC):
    backend: str = "abstract"
    persistent: bool = False

    @abstractmethod
    def build(self, docs: Sequence[KeywordDoc]) -> None:
        """(Re)create the index from `docs`."""

    @abstractmethod
    def search(self, query: str, k: int = 10, filter: Optional[MetadataFilter] = None) -> List[Hit]:
        """Top-k documents by lexical score (higher is better); metadata is the doc metadata."""

    @abstractmethod
    def count(self) -> int: ...

    def persist(self) -> None:
        """Flush to disk (no-op for indexes that are rebuilt from the record store)."""

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def info(self) -> Dict[str, Any]: ...


class SqliteFts5Index(KeywordIndex):
    """FTS5 index in a SQLite file. Tokenizer `unicode61 remove_diacritics 0` keeps Vietnamese diacritics
    significant (thử != thu); text and queries are NFC-normalised first. Ranking is FTS5 `bm25()` with a
    configurable title weight. Queries are OR-ed unigrams plus (default on, `bigrams`) adjacent-pair phrases, since
    most Vietnamese words are two syllables."""

    backend = "sqlite_fts5"
    persistent = True

    def __init__(self, path: str | Path, tokenizer: str = "unicode61 remove_diacritics 0", title_weight: float = 2.0,
                 bigrams: bool = True, mode: str = "open_or_create"):
        self.path = Path(path)
        if not re.fullmatch(r"[\w .=-]+", tokenizer):
            raise ConfigError(f"fts5 tokenizer spec has unsupported characters: {tokenizer!r}")
        self.tokenizer = tokenizer
        self.title_weight = float(title_weight)
        self.bigrams = bool(bigrams)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "open" and not self.path.is_file():
            raise BackendError(f"fts5 index not found: {self.path}")
        try:
            self._conn = sqlite3.connect(self.path)
            self._conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _probe USING fts5(x)")
            self._conn.execute("DROP TABLE _probe")
        except sqlite3.Error as exc:
            raise BackendUnavailableError(f"this Python's SQLite lacks FTS5: {exc}") from exc
        row = self._conn.execute("SELECT name FROM sqlite_master WHERE name = 'fts'").fetchone()
        if row:
            stored = dict(self._conn.execute("SELECT key, value FROM kw_meta").fetchall())
            if stored.get("tokenizer") != self.tokenizer:
                raise BackendError(f"fts5: stored tokenizer {stored.get('tokenizer')!r} != configured {self.tokenizer!r}; rebuild the index")
            self.title_weight = float(stored.get("title_weight", self.title_weight))

    def build(self, docs: Sequence[KeywordDoc]) -> None:
        c = self._conn
        try:
            c.executescript("DROP TABLE IF EXISTS fts; DROP TABLE IF EXISTS kw_docs; DROP TABLE IF EXISTS kw_meta;")
            c.execute(f"CREATE VIRTUAL TABLE fts USING fts5(title, content, tokenize = '{self.tokenizer}')")
            c.execute("CREATE TABLE kw_docs (rowid INTEGER PRIMARY KEY, doc_id TEXT UNIQUE NOT NULL, metadata TEXT NOT NULL)")
            c.execute("CREATE TABLE kw_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            for n, d in enumerate(docs, start=1):
                c.execute("INSERT INTO fts (rowid, title, content) VALUES (?, ?, ?)", (n, nfc(d.title), nfc(d.content)))
                c.execute("INSERT INTO kw_docs VALUES (?, ?, ?)", (n, d.doc_id, json.dumps(d.metadata, ensure_ascii=False)))
            c.executemany("INSERT INTO kw_meta VALUES (?, ?)", [("tokenizer", self.tokenizer), ("title_weight", str(self.title_weight))])
            c.execute("INSERT INTO fts(fts) VALUES ('optimize')")
            c.commit()
        except sqlite3.Error as exc:
            c.rollback()
            raise BackendError(f"fts5 build failed: {exc}") from exc

    def _match_expr(self, query: str) -> Optional[str]:
        toks = query_tokens(query)
        if not toks:
            return None
        terms = [f'"{t}"' for t in dict.fromkeys(toks)]
        if self.bigrams:
            terms += [f'"{a} {b}"' for a, b in dict.fromkeys(zip(toks, toks[1:]))]
        return " OR ".join(terms)

    def search(self, query: str, k: int = 10, filter: Optional[MetadataFilter] = None) -> List[Hit]:
        expr = self._match_expr(query)
        if expr is None:
            return []
        try:
            flt = validate_filter(filter)
        except ValueError as exc:
            raise BackendError(f"fts5: {exc}") from exc
        total = self.count()
        n = k if not flt else min(total, max(4 * k, 64))
        while True:
            try:
                rows = self._conn.execute(
                    "SELECT d.doc_id, bm25(fts, ?, 1.0), d.metadata FROM fts JOIN kw_docs d ON d.rowid = fts.rowid "
                    "WHERE fts MATCH ? ORDER BY bm25(fts, ?, 1.0), d.doc_id LIMIT ?",
                    (self.title_weight, expr, self.title_weight, n)).fetchall()
            except sqlite3.Error as exc:
                raise BackendError(f"fts5 search failed for {expr[:80]!r}: {exc}") from exc
            hits = [Hit(r[0], -float(r[1]), json.loads(r[2])) for r in rows]  # bm25() is negative: lower is better
            kept = [h for h in hits if matches_filter(h.metadata, flt)]
            if len(kept) >= k or len(rows) < n or n >= total:
                return kept[:k]
            n = min(total, n * 4)

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM kw_docs").fetchone()[0]) if self._has_tables() else 0

    def _has_tables(self) -> bool:
        return self._conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'kw_docs'").fetchone() is not None

    def persist(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    def info(self) -> Dict[str, Any]:
        return {"backend": self.backend, "library": "sqlite3", "version": sqlite3.sqlite_version, "persistent": True,
                "tokenizer": self.tokenizer, "title_weight": self.title_weight, "bigrams": self.bigrams,
                "score": "FTS5 bm25() sign-flipped (lexical proxy)", "count": self.count(), "path": str(self.path)}


class Bm25MemoryIndex(KeywordIndex):
    """The repository's in-memory BM25 (`src.retrieval.bm25_engine.BM25Retriever`, rank_bm25 Okapi) behind the
    KeywordIndex interface. Nothing is persisted: it is rebuilt from the record store in milliseconds at load."""

    backend = "bm25_memory"
    persistent = False

    def __init__(self) -> None:
        self._engine = None
        self._meta: Dict[str, Metadata] = {}

    def build(self, docs: Sequence[KeywordDoc]) -> None:
        try:
            from src.retrieval.bm25_engine import BM25Retriever
        except ImportError as exc:
            raise BackendUnavailableError("bm25_memory needs the 'rank-bm25' package and src.retrieval.bm25_engine") from exc
        corpus = [{"doc_id": d.doc_id, "title": d.title, "content": d.content} for d in docs]
        self._engine = BM25Retriever(corpus)
        self._meta = {d.doc_id: d.metadata for d in docs}

    def search(self, query: str, k: int = 10, filter: Optional[MetadataFilter] = None) -> List[Hit]:
        if self._engine is None:
            raise BackendError("bm25_memory: index not built")
        try:
            flt = validate_filter(filter)
        except ValueError as exc:
            raise BackendError(f"bm25_memory: {exc}") from exc
        top = self._engine.search(nfc(query), top_k=len(self._meta) if flt else k)
        hits = [Hit(doc_id, score, dict(self._meta[doc_id])) for doc_id, score in top]
        return [h for h in hits if matches_filter(h.metadata, flt)][:k]

    def count(self) -> int:
        return len(self._meta)

    def close(self) -> None:
        self._engine = None

    def info(self) -> Dict[str, Any]:
        import importlib.metadata
        try:
            version = importlib.metadata.version("rank-bm25")
        except importlib.metadata.PackageNotFoundError:
            version = None
        return {"backend": self.backend, "library": "rank-bm25", "version": version, "persistent": False,
                "tokenizer": "src.retrieval.bm25_engine.tokenize_vietnamese", "score": "BM25Okapi (lexical proxy)",
                "count": self.count()}


def open_keyword_index(cfg: Dict[str, Any], index_dir: Path, mode: str = "open_or_create") -> KeywordIndex:
    backend = cfg.get("backend", "sqlite_fts5")
    if backend in ("sqlite_fts5", "fts5"):
        known = {"backend", "tokenizer", "title_weight", "bigrams", "path"}
        extra = set(cfg) - known
        if extra:
            raise ConfigError(f"keyword_index: unknown keys {sorted(extra)}")
        path = Path(cfg.get("path", "keyword/fts5.sqlite"))
        path = path if path.is_absolute() else index_dir / path
        return SqliteFts5Index(path, tokenizer=cfg.get("tokenizer", "unicode61 remove_diacritics 0"),
                               title_weight=cfg.get("title_weight", 2.0), bigrams=cfg.get("bigrams", True), mode=mode)
    if backend in ("bm25_memory", "bm25"):
        return Bm25MemoryIndex()
    raise ConfigError(f"keyword_index.backend must be 'sqlite_fts5' or 'bm25_memory', got {backend!r}")
