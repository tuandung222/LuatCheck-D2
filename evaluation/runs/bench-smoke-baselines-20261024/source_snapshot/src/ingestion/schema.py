"""Unified chunk schema.

A `Chunk` serialises (`to_record`) to a flat JSON object that is a superset of the records the current
consumers read (`doc_id` or `article_id`, `title`, `content`, `source_url`, `source_sha256`, `source_pages`).
`content` is always the heading plus the verbatim text of the span it covers; `char_start`/`char_end` are
offsets into the *normalised* document text (the same text the manifest hashes), so every chunk can be
re-located and re-verified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

LEVELS = ("document", "chapter", "article", "clause", "point", "section", "paragraph")

# Field order of a serialised record. `article_id` (alias of doc_id) is emitted first when enabled so records
# stay readable next to the legacy corpus; extras (e.g. law_id, law_name, scope) come last.
RECORD_FIELDS = (
    "doc_id", "collection_id", "source_name", "title", "content", "level", "parent_id", "section_path",
    "lead_in", "source_url", "source_sha256", "source_pages", "document_number", "issued_date", "version",
    "char_start", "char_end", "doc_code", "extraction",
)


@dataclass
class Chunk:
    doc_id: str
    collection_id: str
    source_name: str
    title: str
    content: str
    level: str
    parent_id: Optional[str]
    section_path: List[str]
    source_sha256: str
    source_pages: List[int]
    char_start: int
    char_end: int
    lead_in: Optional[str] = None
    source_url: Optional[str] = None
    document_number: Optional[str] = None
    issued_date: Optional[str] = None
    version: Optional[str] = None
    doc_code: Optional[str] = None
    extraction: Optional[str] = None
    article_id: Optional[str] = None  # alias of doc_id; set only when the profile asks for it
    extra: Dict[str, Any] = field(default_factory=dict)  # source-level metadata copied verbatim into the record

    def to_record(self) -> Dict[str, Any]:
        rec: Dict[str, Any] = {}
        if self.article_id is not None:
            rec["article_id"] = self.article_id
        for name in RECORD_FIELDS:
            rec[name] = getattr(self, name)
        for key, value in self.extra.items():
            if key in rec:
                raise ValueError(f"metadata key {key!r} collides with a schema field")
            rec[key] = value
        return rec
