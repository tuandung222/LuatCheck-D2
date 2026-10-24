"""
Domain-Agnostic Hybrid Retrieval with Reciprocal Rank Fusion (RRF).

Combines BM25 with an explicitly selected statistical or neural retriever
across any knowledge corpus (Legal, Medical, Technical, SOPs, Documentation).
"""
import json
import os
from typing import Callable, List, Dict, Any, Optional
from collections import defaultdict

from src.interfaces.base import BaseRetriever, BaseDenseRetriever
from src.retrieval.bm25_engine import BM25Retriever
from src.retrieval.dense_engine import NeuralDenseRetriever, TfidfDenseRetriever

# Field pairs that are mirrored so that records using either spelling can be read through both.
_FIELD_ALIASES = (("section_title", "title"), ("article_id", "doc_id"), ("source_name", "law_name"))


def _normalized_record(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Copy of a corpus record in which each alias pair (title/section_title, doc_id/article_id, law_name/source_name)
    is present under both names when either is."""
    record = dict(doc)
    for first, second in _FIELD_ALIASES:
        if first not in record and second in record:
            record[first] = record[second]
        if second not in record and first in record:
            record[second] = record[first]
    return record


class HybridDomainRetriever(BaseRetriever):
    """
    Hybrid BM25 retrieval with explicit TF-IDF or native embedding configuration.
    """

    def __init__(
        self,
        corpus_path: Optional[str] = None,
        corpus: Optional[List[Dict[str, Any]]] = None,
        rrf_k: int = 60,
        dense_retriever: Optional[BaseDenseRetriever] = None,
        dense_model_name: str = "all-minilm",
        dense_endpoint: Optional[str] = None,
        retrieval_mode: str = "tfidf",
        id_normalizer: Optional[Callable[[str], str]] = None
    ):
        self.corpus_path = corpus_path or "data/corpus/labor_code_2019_official.json"
        self.rrf_k = rrf_k
        if corpus is not None:
            self.corpus = corpus
        else:
            self.corpus = self._load_corpus(self.corpus_path)

        # `id_normalizer` (the domain profile's ID convention) maps a cited ID to its canonical lower-case form.
        # Without one, the labour-style "Điều_N" <-> "Dieu_N" alias is tried (kept for callers built before profiles).
        self.id_normalizer = id_normalizer

        # Build multi-key index for fast lookups
        self.doc_lookup: Dict[str, Dict[str, Any]] = {}
        for doc in self.corpus:
            doc_id = str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or "").strip()
            if doc_id:
                norm_doc = _normalized_record(doc)
                self.doc_lookup[doc_id] = norm_doc
                self.doc_lookup[doc_id.lower()] = norm_doc
                self.doc_lookup[doc_id.replace(" ", "_").lower()] = norm_doc

        # Lexical and Dense engines
        self.bm25 = BM25Retriever(self.corpus)
        if dense_retriever is not None:
            self.dense = dense_retriever
            self.retrieval_mode = "injected"
        elif retrieval_mode == "tfidf":
            self.dense = TfidfDenseRetriever(self.corpus)
            self.retrieval_mode = "bm25_tfidf_rrf"
        elif retrieval_mode == "bm25":
            self.dense = None
            self.retrieval_mode = "bm25"
        else:
            self.dense = NeuralDenseRetriever(
                self.corpus,
                model_name=dense_model_name,
                endpoint=dense_endpoint
            )
            self.retrieval_mode = "bm25_neural_rrf"

    def _load_corpus(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Knowledge corpus not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Fetch document chunk by canonical or case-insensitive identifier."""
        if not doc_id:
            return None
        clean_id = str(doc_id).strip()
        # Direct lookup
        if clean_id in self.doc_lookup:
            return self.doc_lookup[clean_id]
        if clean_id.lower() in self.doc_lookup:
            return self.doc_lookup[clean_id.lower()]

        # Normalized lookup
        norm = clean_id.replace(" ", "_").lower()
        if norm in self.doc_lookup:
            return self.doc_lookup[norm]

        # Domain alias normalization (e.g. Điều 35 -> Dieu_35)
        if self.id_normalizer is not None:
            return self.doc_lookup.get(self.id_normalizer(clean_id))
        if norm.startswith("điều_"):
            alt = "dieu_" + norm[5:]
            if alt in self.doc_lookup:
                return self.doc_lookup[alt]
        elif norm.startswith("dieu_"):
            alt = "điều_" + norm[5:]
            if alt in self.doc_lookup:
                return self.doc_lookup[alt]

        return None

    get_article_by_id = get_document_by_id

    @property
    def article_lookup(self) -> Dict[str, Dict[str, Any]]:
        return self.doc_lookup

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Executes the configured statistical/neural retrieval combination via RRF.
        """
        bm25_results = self.bm25.search(query, top_k=top_k * 2)
        dense_results = self.dense.search(query, top_k=top_k * 2) if self.dense else []

        rrf_scores = defaultdict(float)

        # RRF for BM25
        for rank, (doc_id, _) in enumerate(bm25_results):
            rrf_scores[doc_id] += 1.0 / (self.rrf_k + (rank + 1))

        # RRF for Dense
        for rank, (doc_id, _) in enumerate(dense_results):
            rrf_scores[doc_id] += 1.0 / (self.rrf_k + (rank + 1))

        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)[:top_k]

        enriched_results = []
        for doc_id in sorted_doc_ids:
            doc = self.get_document_by_id(doc_id)
            if doc:
                canonical_id = str(doc.get("doc_id") or doc.get("article_id") or doc_id)
                enriched_results.append({
                    "doc_id": canonical_id,
                    "article_id": canonical_id,
                    "source_name": doc.get("source_name") or doc.get("law_name", "Knowledge Base"),
                    "law_name": doc.get("law_name") or doc.get("source_name", "Knowledge Base"),
                    "law_id": doc.get("law_id") or doc.get("collection_id", "default"),
                    "title": doc.get("title") or doc.get("section_title", ""),
                    "content": doc.get("content", ""),
                    "rrf_score": float(rrf_scores[doc_id])
                })

        return enriched_results


class IndexedRetriever(BaseRetriever):
    """`retrieval.mode: hybrid_index`: `src/indexing` HybridSearcher over a built, persisted index.

    Same interface and result shape as `HybridDomainRetriever` (`search`, `get_document_by_id`, `corpus`). The
    embedding model (the index's own, from its manifest) is a ModelManager component: loaded on the first query,
    counted in the resident budget, unloaded when idle. Any failure of the index or of the embedding model raises;
    there is no fallback to keyword-only search or to the in-memory BM25/TF-IDF retriever.

    FAISS stores are rejected: faiss and torch cannot share a process on macOS (duplicate libomp aborts or
    segfaults), and the application loads torch for rerankers, NLI and the embedding model.
    """

    def __init__(self, index_cfg: Any, manager: Any = None, id_normalizer: Optional[Callable[[str], str]] = None):
        from src.indexing import ConfigError, load_index
        from src.indexing.builder import resolve_index_dir
        from src.indexing.manifest import read_manifest
        from src.model_manager import ModelManager, estimate_weights_gb

        if not index_cfg.path:
            raise ConfigError("retrieval.mode 'hybrid_index' requires retrieval.index.path")
        index_dir = resolve_index_dir(index_cfg.path)
        manifest = read_manifest(index_dir)
        store = index_cfg.store or manifest["default_store"]
        entries = {e["name"]: e for e in manifest["vector_stores"]}
        if store not in entries:
            raise ConfigError(f"index {manifest['name']!r} has no vector store {store!r}; built with {sorted(entries)}")
        if entries[store]["backend"] == "faiss":
            raise ConfigError(
                f"vector store {store!r} is a FAISS store; FAISS cannot be used inside the application because it cannot "
                "share a process with torch (duplicate libomp: abort or segfault). Choose another store of the index "
                f"({sorted(n for n, e in entries.items() if e['backend'] != 'faiss')}) with retrieval.index.store")
        self.index_cfg = index_cfg
        self.id_normalizer = id_normalizer
        self._loaded = load_index(index_dir, stores=[store], verify_corpus=index_cfg.verify_corpus)
        self.searcher = self._loaded.searcher(store)
        self.corpus: List[Dict[str, Any]] = [_normalized_record(r) for r in self._loaded.records]
        self.retrieval_mode = f"hybrid_index:{index_cfg.search_mode}"
        provider = self._loaded.provider
        self.manager = manager or ModelManager.shared()
        local = hasattr(provider, "close") and provider.kind == "sentence_transformers"
        if local:
            gb, source = estimate_weights_gb(provider.model, getattr(provider, "dtype", "float32"),
                                             self.manager.default_estimate_gb)
            self.handle = self.manager.register(("embedding", provider.kind, provider.model, str(index_dir)), "embedding",
                                                provider, provider.load, provider.close, gb)
            self.handle.estimate_source = source
        else:
            self.handle = None   # HTTP embedding provider: nothing resident in this process

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.handle is None:
            return self.searcher.search(query, top_k=top_k, mode=self.index_cfg.search_mode)
        with self.handle.use():
            return self.searcher.search(query, top_k=top_k, mode=self.index_cfg.search_mode)

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        if not doc_id:
            return None
        clean_id = str(doc_id).strip()
        rec = self.searcher.get_document_by_id(clean_id)
        if rec is not None:
            return _normalized_record(rec)
        if self.id_normalizer is not None:
            rec = self.searcher.get_document_by_id(self.id_normalizer(clean_id))
            if rec is not None:
                return _normalized_record(rec)
        norm = clean_id.replace(" ", "_").lower()
        if norm.startswith("điều_"):
            rec = self.searcher.get_document_by_id("dieu_" + norm[5:])
        elif norm.startswith("dieu_"):
            rec = self.searcher.get_document_by_id("điều_" + norm[5:])
        return _normalized_record(rec) if rec is not None else None

    get_article_by_id = get_document_by_id

    def close(self) -> None:
        if self.handle is not None:
            self.manager.unload(self.handle)
        self._loaded.close()
