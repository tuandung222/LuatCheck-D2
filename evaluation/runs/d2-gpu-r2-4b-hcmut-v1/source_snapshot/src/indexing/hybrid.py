"""HybridSearcher: keyword index + vector store fused with reciprocal-rank fusion (RRF)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .embeddings import EmbeddingProvider
from .errors import BackendError, ConfigError
from .keyword import KeywordIndex
from .records import RecordStore
from .types import Hit, MetadataFilter
from .vector_stores.base import VectorStore

MODES = ("hybrid", "keyword", "vector")


class HybridSearcher:
    """Returns records shaped like `HybridDomainRetriever.search()` results
    (doc_id, article_id, source_name, law_name, law_id, title, content, rrf_score) plus per-source ranks/scores.

    Vector hits are chunk-level; they are collapsed to documents (best chunk per document, in rank order)
    before fusion. A failure in either component raises: hybrid never degrades to a single source silently.
    Keyword scores are lexical proxies (BM25-style); vector scores are cosine/inner-product similarities.
    """

    def __init__(self, keyword_index: KeywordIndex, vector_store: VectorStore, embedding_provider: EmbeddingProvider,
                 records: RecordStore, rrf_k: int = 60, candidates: int = 50,
                 keyword_weight: float = 1.0, vector_weight: float = 1.0):
        if rrf_k < 1 or candidates < 1:
            raise ConfigError("rrf_k and candidates must be >= 1")
        self.keyword = keyword_index
        self.vector = vector_store
        self.provider = embedding_provider
        self.records = records
        self.rrf_k = int(rrf_k)
        self.candidates = int(candidates)
        self.keyword_weight = float(keyword_weight)
        self.vector_weight = float(vector_weight)

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self.records.get_normalised(doc_id)

    get_article_by_id = get_document_by_id

    def _vector_docs(self, query: str, flt: Optional[MetadataFilter], depth: int) -> List[Dict[str, Any]]:
        qvec = self.provider.embed_queries([query])[0]
        hits: List[Hit] = self.vector.search(qvec, k=depth, filter=flt)
        docs: Dict[str, Dict[str, Any]] = {}
        for h in hits:  # hits are score-descending: first chunk seen per document is its best
            doc_id = h.metadata.get("doc_id")
            if doc_id is None:
                raise BackendError(f"vector hit {h.id!r} has no doc_id metadata; the index is malformed")
            docs.setdefault(doc_id, {"doc_id": doc_id, "score": h.score, "chunk_id": h.id,
                                     "chunk_index": h.metadata.get("chunk_index"), "char_start": h.metadata.get("char_start"),
                                     "char_end": h.metadata.get("char_end")})
        return list(docs.values())

    def search(self, query: str, top_k: int = 5, filter: Optional[MetadataFilter] = None, mode: str = "hybrid") -> List[Dict[str, Any]]:
        if mode not in MODES:
            raise ConfigError(f"mode must be one of {MODES}")
        if not query or not query.strip():
            return []
        depth = max(self.candidates, top_k)
        kw_ranked: List[Hit] = self.keyword.search(query, k=depth, filter=filter) if mode in ("hybrid", "keyword") else []
        vec_ranked = self._vector_docs(query, filter, depth) if mode in ("hybrid", "vector") else []

        fused: Dict[str, Dict[str, Any]] = {}
        for rank, h in enumerate(kw_ranked, start=1):
            e = fused.setdefault(h.id, {})
            e.update(keyword_rank=rank, keyword_score=h.score)
            e["rrf_score"] = e.get("rrf_score", 0.0) + self.keyword_weight / (self.rrf_k + rank)
        for rank, d in enumerate(vec_ranked, start=1):
            e = fused.setdefault(d["doc_id"], {})
            e.update(vector_rank=rank, vector_score=d["score"],
                     matched_chunk={k: d[k] for k in ("chunk_id", "chunk_index", "char_start", "char_end")})
            e["rrf_score"] = e.get("rrf_score", 0.0) + self.vector_weight / (self.rrf_k + rank)

        ordered = sorted(fused.items(), key=lambda kv: (-kv[1]["rrf_score"], kv[0]))[:top_k]
        results: List[Dict[str, Any]] = []
        for doc_id, e in ordered:
            rec = self.records.get(doc_id)
            if rec is None:
                raise BackendError(f"index hit {doc_id!r} is missing from the record store; the index is inconsistent")
            results.append({
                "doc_id": doc_id,
                "article_id": doc_id,
                "source_name": rec.get("source_name") or rec.get("law_name") or "Knowledge Base",
                "law_name": rec.get("law_name") or rec.get("source_name") or "Knowledge Base",
                "law_id": rec.get("law_id") or rec.get("collection_id") or "default",
                "collection_id": rec.get("collection_id"),
                "title": rec.get("title", ""),
                "content": rec["content"],
                "rrf_score": float(e["rrf_score"]),
                "keyword_rank": e.get("keyword_rank"),
                "keyword_score": e.get("keyword_score"),      # lexical proxy
                "vector_rank": e.get("vector_rank"),
                "vector_score": e.get("vector_score"),
                "matched_chunk": e.get("matched_chunk"),
                "retrieval_mode": mode,
            })
        return results
