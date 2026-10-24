"""Pluggable, persistent indexing layer: embedding providers, vector stores, keyword indexes, builder, hybrid search.

Typical use::

    from src.indexing import load_index
    with load_index("labor_code_2019_vi") as idx:
        results = idx.searcher().search("thời gian thử việc tối đa", top_k=5)

Build with ``python -m src.indexing build --config config/indexing/labor_code_2019.yaml``.
Every failure raises an `IndexingError` subclass; nothing falls back to another backend.
"""
from .builder import LoadedIndex, add_store, build_index, load_index
from .chunking import Chunk, ChunkingConfig, chunk_record
from .config import IndexConfig, load_config
from .embeddings import (EmbeddingProvider, OllamaProvider, OpenAICompatibleProvider, SentenceTransformerProvider,
                         make_provider)
from .errors import (BackendError, BackendUnavailableError, ConfigError, EmbeddingError, IndexingError, ManifestError,
                     MemoryLimitError, StaleIndexError, TextTooLongError)
from .hybrid import HybridSearcher
from .keyword import Bm25MemoryIndex, KeywordDoc, KeywordIndex, SqliteFts5Index, open_keyword_index
from .records import RecordStore, load_corpus
from .types import Hit
from .vector_stores import VectorStore, backend_status, open_store

__all__ = [
    "LoadedIndex", "add_store", "build_index", "load_index", "Chunk", "ChunkingConfig", "chunk_record", "IndexConfig", "load_config",
    "EmbeddingProvider", "OllamaProvider", "OpenAICompatibleProvider", "SentenceTransformerProvider", "make_provider",
    "BackendError", "BackendUnavailableError", "ConfigError", "EmbeddingError", "IndexingError", "ManifestError",
    "MemoryLimitError", "StaleIndexError", "TextTooLongError", "HybridSearcher", "Bm25MemoryIndex", "KeywordDoc",
    "KeywordIndex", "SqliteFts5Index", "open_keyword_index", "RecordStore", "load_corpus", "Hit", "VectorStore",
    "backend_status", "open_store",
]
