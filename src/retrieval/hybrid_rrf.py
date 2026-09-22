"""
Hybrid Retrieval with Reciprocal Rank Fusion (RRF).

Combines BM25 (lexical matching for legal citations) and Dense Semantic Search
(semantic matching for situational queries) using Reciprocal Rank Fusion.
"""
import json
import os
from typing import List, Dict, Any, Optional
from collections import defaultdict

from src.retrieval.bm25_engine import BM25Retriever
from src.retrieval.dense_engine import DenseSemanticRetriever


class HybridLegalRetriever:
    def __init__(self, corpus_path: str = "data/corpus/labor_code_2019.json", rrf_k: int = 60):
        self.corpus_path = corpus_path
        self.rrf_k = rrf_k
        self.corpus = self._load_corpus(corpus_path)
        self.article_lookup: Dict[str, Dict[str, Any]] = {
            doc["article_id"]: doc for doc in self.corpus
        }
        self.bm25 = BM25Retriever(self.corpus)
        self.dense = DenseSemanticRetriever(self.corpus)

    def _load_corpus(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Corpus file not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        # Normalize in case user passes "Điều 35" or "dieu_35"
        normalized_id = article_id.strip().replace(" ", "_")
        if normalized_id.lower().startswith("điều_"):
            normalized_id = "Dieu_" + normalized_id[5:]
        elif normalized_id.lower().startswith("dieu_"):
            normalized_id = "Dieu_" + normalized_id[5:]
            
        for key in self.article_lookup:
            if key.lower() == normalized_id.lower() or key.lower() == article_id.lower():
                return self.article_lookup[key]
        return None

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid search combining BM25 and Dense semantics via Reciprocal Rank Fusion (RRF).
        """
        bm25_results = self.bm25.search(query, top_k=top_k * 2)
        dense_results = self.dense.search(query, top_k=top_k * 2)

        rrf_scores = defaultdict(float)

        # RRF for BM25
        for rank, (doc_id, _) in enumerate(bm25_results):
            rrf_scores[doc_id] += 1.0 / (self.rrf_k + (rank + 1))

        # RRF for Dense
        for rank, (doc_id, _) in enumerate(dense_results):
            rrf_scores[doc_id] += 1.0 / (self.rrf_k + (rank + 1))

        # Sort descending by RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)[:top_k]

        enriched_results = []
        for doc_id in sorted_doc_ids:
            doc = self.article_lookup.get(doc_id)
            if doc:
                enriched_results.append({
                    "article_id": doc["article_id"],
                    "law_id": doc["law_id"],
                    "law_name": doc["law_name"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "rrf_score": float(rrf_scores[doc_id])
                })

        return enriched_results
