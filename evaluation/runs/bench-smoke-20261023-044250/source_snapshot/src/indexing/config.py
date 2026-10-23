"""Index build configuration (YAML) and project paths."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .chunking import ChunkingConfig
from .errors import ConfigError
from .vector_stores import canonical_backend

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = "data/index"


def resolve_path(p: str | Path, base: Path = PROJECT_ROOT) -> Path:
    p = Path(p)
    return p if p.is_absolute() else base / p


@dataclass
class CorpusSpec:
    path: str
    collection_id: Optional[str] = None  # default for records that carry no collection_id


@dataclass
class StoreSpec:
    backend: str
    collection: str = "chunks"
    metric: str = "cosine"
    path: Optional[str] = None           # relative paths are inside the index directory
    name: Optional[str] = None           # label used to pick this store at query time (default: the backend name)
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = self.name or self.backend

    @property
    def label(self) -> str:
        return self.name


@dataclass
class IndexConfig:
    name: str
    corpora: List[CorpusSpec]
    embedding: Dict[str, Any]
    keyword_index: Dict[str, Any]
    vector_stores: List[StoreSpec]
    chunking: ChunkingConfig
    output_dir: str = DEFAULT_OUTPUT_DIR
    rrf_k: int = 60
    candidates: int = 50
    vector_metadata_fields: Optional[List[str]] = None
    default_store: Optional[str] = None
    source_path: Optional[str] = None

    @property
    def index_dir(self) -> Path:
        return resolve_path(self.output_dir) / self.name

    def to_dict(self) -> Dict[str, Any]:
        emb = {k: v for k, v in self.embedding.items()}
        return {
            "name": self.name,
            "corpora": [{"path": c.path, "collection_id": c.collection_id} for c in self.corpora],
            "chunking": self.chunking.as_dict(),
            "retrieval": {
                "embedding": emb,
                "keyword_index": self.keyword_index,
                "vector_stores": [{"backend": s.backend, "name": s.name, "collection": s.collection, "metric": s.metric, "path": s.path, **s.params}
                                  for s in self.vector_stores],
                "rrf_k": self.rrf_k,
                "candidates": self.candidates,
            },
            "vector_metadata_fields": self.vector_metadata_fields,
            "default_store": self.default_store,
        }


_TOP_KEYS = {"name", "corpus", "corpora", "chunking", "retrieval", "output_dir", "vector_metadata_fields"}
_RETRIEVAL_KEYS = {"embedding", "keyword_index", "vector_store", "vector_stores", "rrf_k", "candidates", "default_store"}


def parse_store(raw: Dict[str, Any]) -> StoreSpec:
    raw = dict(raw)
    if "backend" not in raw:
        raise ConfigError("vector store entry needs a `backend`")
    backend = canonical_backend(raw.pop("backend"))
    return StoreSpec(backend=backend, collection=raw.pop("collection", "chunks"), metric=raw.pop("metric", "cosine"),
                     path=raw.pop("path", None), name=raw.pop("name", None), params=raw)


def load_config(path: str | Path) -> IndexConfig:
    p = resolve_path(path) if not Path(path).is_file() else Path(path)
    if not p.is_file():
        raise ConfigError(f"index config not found: {path}")
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ConfigError(f"{p}: expected a mapping")
    unknown = set(raw) - _TOP_KEYS
    if unknown:
        raise ConfigError(f"{p}: unknown keys {sorted(unknown)}")
    name = raw.get("name")
    if not name or not isinstance(name, str) or "/" in name:
        raise ConfigError(f"{p}: `name` (a simple string) is required")
    if "corpora" in raw:
        corpora = [CorpusSpec(**c) if isinstance(c, dict) else CorpusSpec(path=str(c)) for c in raw["corpora"]]
    elif "corpus" in raw:
        corpora = [CorpusSpec(path=str(raw["corpus"]))]
    else:
        raise ConfigError(f"{p}: `corpus` or `corpora` is required")
    r = raw.get("retrieval") or {}
    extra = set(r) - _RETRIEVAL_KEYS
    if extra:
        raise ConfigError(f"{p}: unknown retrieval keys {sorted(extra)}")
    if "embedding" not in r:
        raise ConfigError(f"{p}: retrieval.embedding is required")
    stores_raw = r.get("vector_stores") or ([r["vector_store"]] if "vector_store" in r else [])
    if not stores_raw:
        raise ConfigError(f"{p}: retrieval.vector_store (or vector_stores) is required")
    stores = [parse_store(s) for s in stores_raw]
    labels = [s.label for s in stores]
    if len(set(labels)) != len(labels):
        raise ConfigError(f"{p}: store names must be unique (give repeated backends a `name`); got {labels}")
    default_store = r.get("default_store")
    if default_store is not None:
        if default_store not in labels:
            raise ConfigError(f"{p}: default_store {default_store!r} is not among {labels}")
    return IndexConfig(
        name=name, corpora=corpora, embedding=dict(r["embedding"]), keyword_index=dict(r.get("keyword_index") or {"backend": "sqlite_fts5"}),
        vector_stores=stores, chunking=ChunkingConfig.from_dict(raw.get("chunking")), output_dir=raw.get("output_dir", DEFAULT_OUTPUT_DIR),
        rrf_k=int(r.get("rrf_k", 60)), candidates=int(r.get("candidates", 50)),
        vector_metadata_fields=raw.get("vector_metadata_fields"), default_store=default_store, source_path=str(p),
    )
