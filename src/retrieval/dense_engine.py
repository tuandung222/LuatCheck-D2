"""
True Dense Semantic Retrieval Engine for Legal Documents using Deep Learning Embeddings.

Features:
1. NeuralDenseRetriever: True Deep Learning Neural Embedding Retriever executing on CPU.
   - Supports compact open-source embedding models:
     * 'all-minilm' (45 MB, 384-dim, ultra-fast CPU inference ~30ms)
     * 'bge-m3' (1024-dim multilingual SOTA)
     * 'nomic-embed-text' (768-dim)
   - Pre-computes normalized dense vector representations and performs matrix cosine similarity.
   - Built-in graceful fallback when offline.
2. TfidfDenseRetriever: Statistical n-gram fallback retriever for offline baseline comparisons.
3. DenseSemanticRetriever: Alias to NeuralDenseRetriever.
"""
import os
import requests
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.interfaces.base import BaseDenseRetriever


class TfidfDenseRetriever(BaseDenseRetriever):
    """Statistical n-gram vectorizer baseline retriever for offline unit tests and ablation benchmarks."""

    def __init__(self, corpus: List[Dict[str, Any]]):
        self.corpus = corpus
        self.doc_ids = [
            str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or "")
            for doc in corpus
        ]
        self.raw_texts = [
            f"{doc.get('title') or doc.get('section_title', '')} {doc.get('content', '')}"
            for doc in corpus
        ]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            min_df=1
        )
        self.doc_vectors = self.vectorizer.fit_transform(self.raw_texts)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search articles using statistical n-gram TF-IDF cosine similarity."""
        if not query.strip():
            return []
        query_vec = self.vectorizer.transform([query])
        sim_scores = cosine_similarity(query_vec, self.doc_vectors).flatten()
        ranked_indices = np.argsort(sim_scores)[::-1][:top_k]
        results = []
        for idx in ranked_indices:
            score = float(sim_scores[idx])
            if score > 0.01:
                results.append((self.doc_ids[idx], score))
        return results


class NeuralDenseRetriever(BaseDenseRetriever):
    """
    True Deep Learning Neural Dense Embedding Retriever for Legal Text.
    Executes 100% on CPU using lightweight quantized/compact embedding models.
    """

    def __init__(
        self,
        corpus: Optional[List[Dict[str, Any]]] = None,
        corpus_path: Optional[str] = None,
        model_name: str = "all-minilm",
        endpoint: Optional[str] = None,
        ollama_url: Optional[str] = None,
        timeout_seconds: float = 5.0
    ):
        if corpus is not None:
            self.corpus = corpus
        elif corpus_path:
            import json
            with open(corpus_path, "r", encoding="utf-8") as f:
                self.corpus = json.load(f)
        else:
            self.corpus = []

        self.doc_ids = [
            str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or "")
            for doc in self.corpus
        ]
        self.raw_texts = [
            f"{doc.get('title') or doc.get('section_title', '')} {doc.get('content', '')}".strip()
            for doc in self.corpus
        ]
        self.model_name = model_name
        self.endpoint = (
            endpoint
            or ollama_url
            or os.getenv("EMBEDDING_ENDPOINT")
            or os.getenv("MODEL_ENDPOINT")
            or os.getenv("OLLAMA_ENDPOINT")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds

        # Fallback offline statistical retriever
        self._offline_fallback = TfidfDenseRetriever(self.corpus)
        self.doc_matrix: Optional[np.ndarray] = None
        self._is_online: bool = False

        # Attempt to pre-compute and cache corpus dense embeddings
        self._initialize_corpus_embeddings()

    def _embed_single(self, text: str) -> Optional[np.ndarray]:
        """Query local Ollama / OpenAI-compatible embedding API for a single text."""
        if not text.strip():
            return None

        # Truncate text to fit model context window (minilm ~1500 chars, bge-m3 ~3000 chars)
        max_chars = 1500 if "minilm" in self.model_name.lower() else 3000
        clean_text = text[:max_chars]

        # 1. Try Ollama native embedding endpoint: /api/embeddings
        try:
            url = f"{self.endpoint}/api/embeddings"
            payload = {"model": self.model_name, "prompt": clean_text}
            resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
            if resp.status_code == 200:
                vec = resp.json().get("embedding")
                if vec and isinstance(vec, list):
                    return np.array(vec, dtype=np.float32)
        except Exception:
            pass

        # 2. Try OpenAI-compatible embedding endpoint: /v1/embeddings
        try:
            url = f"{self.endpoint}/v1/embeddings"
            payload = {"model": self.model_name, "input": clean_text}
            resp = requests.post(url, json=payload, timeout=self.timeout_seconds)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data and isinstance(data, list):
                    vec = data[0].get("embedding")
                    if vec:
                        return np.array(vec, dtype=np.float32)
        except Exception:
            pass

        return None

    def _initialize_corpus_embeddings(self):
        """Pre-compute and normalize dense embeddings for the entire corpus."""
        if not self.raw_texts:
            return

        # Probe with first document to test endpoint connectivity
        first_vec = self._embed_single(self.raw_texts[0])
        if first_vec is None:
            self._is_online = False
            return

        dim = len(first_vec)
        vectors = [first_vec]

        # Embed remaining documents
        for text in self.raw_texts[1:]:
            vec = self._embed_single(text)
            if vec is None or len(vec) != dim:
                # If any document fails, abort neural mode and fallback
                self._is_online = False
                self.doc_matrix = None
                return
            vectors.append(vec)

        # Assemble and L2-normalize document matrix (N x D)
        matrix = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self.doc_matrix = matrix / np.maximum(norms, 1e-9)
        self._is_online = True

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Search articles using neural dense vector cosine similarity.
        Falls back gracefully to statistical retriever if embedding server is offline.
        """
        if not query.strip():
            return []

        # If online neural matrix is available, execute dense search
        if self._is_online and self.doc_matrix is not None:
            q_vec = self._embed_single(query)
            if q_vec is not None:
                # L2-normalize query vector
                q_norm = np.linalg.norm(q_vec)
                if q_norm > 1e-9:
                    q_vec_norm = q_vec / q_norm
                    # Compute cosine similarity via dot product
                    sim_scores = np.dot(self.doc_matrix, q_vec_norm)
                    ranked_indices = np.argsort(sim_scores)[::-1][:top_k]
                    results = []
                    for idx in ranked_indices:
                        score = float(sim_scores[idx])
                        if score > 0.05:
                            results.append((self.doc_ids[idx], score))
                    return results

        # Graceful fallback for offline test environments
        return self._offline_fallback.search(query, top_k=top_k)


DenseSemanticRetriever = NeuralDenseRetriever
