"""
Domain-Agnostic Hybrid Retrieval with Reciprocal Rank Fusion (RRF).

Combines BM25 with an explicitly selected statistical or neural retriever
across any knowledge corpus (Legal, Medical, Technical, SOPs, Documentation).
"""
import json
import os
from typing import List, Dict, Any, Optional, Union
from collections import defaultdict

from src.interfaces.base import BaseRetriever, BaseDenseRetriever
from src.retrieval.bm25_engine import BM25Retriever
from src.retrieval.dense_engine import NeuralDenseRetriever, TfidfDenseRetriever
from src.contracts.universal_document import UniversalDocument


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
        retrieval_mode: str = "tfidf"
    ):
        self.corpus_path = corpus_path or "data/corpus/labor_code_2019.json"
        self.rrf_k = rrf_k
        if corpus is not None:
            self.corpus = corpus
        else:
            self.corpus = self._load_corpus(self.corpus_path)

        # Build multi-key index for fast lookups
        self.doc_lookup: Dict[str, Dict[str, Any]] = {}
        for doc in self.corpus:
            doc_id = str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or "").strip()
            if doc_id:
                norm_doc = dict(doc)
                if "title" not in norm_doc and "section_title" in norm_doc:
                    norm_doc["title"] = norm_doc["section_title"]
                if "section_title" not in norm_doc and "title" in norm_doc:
                    norm_doc["section_title"] = norm_doc["title"]
                if "doc_id" not in norm_doc and "article_id" in norm_doc:
                    norm_doc["doc_id"] = norm_doc["article_id"]
                if "article_id" not in norm_doc and "doc_id" in norm_doc:
                    norm_doc["article_id"] = norm_doc["doc_id"]
                if "law_name" not in norm_doc and "source_name" in norm_doc:
                    norm_doc["law_name"] = norm_doc["source_name"]
                if "source_name" not in norm_doc and "law_name" in norm_doc:
                    norm_doc["source_name"] = norm_doc["law_name"]

                self.doc_lookup[doc_id] = norm_doc
                self.doc_lookup[doc_id.lower()] = norm_doc
                norm = doc_id.replace(" ", "_").lower()
                self.doc_lookup[norm] = norm_doc

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

        # Domain alias normalization (e.g. Điều 35 <-> Dieu_35)
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
