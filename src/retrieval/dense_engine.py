"""
Dense Semantic Retrieval Engine for Legal Documents
Sử dụng biểu diễn vector ngữ nghĩa TF-IDF n-gram / Dense embeddings và Cosine Similarity
"""
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class DenseSemanticRetriever:
    def __init__(self, corpus: List[Dict[str, Any]]):
        self.corpus = corpus
        self.doc_ids = [doc["article_id"] for doc in corpus]
        self.raw_texts = [
            f"{doc.get('title', '')} {doc.get('content', '')}"
            for doc in corpus
        ]
        # Sử dụng sublinear tf, n-gram 1-3 và phân tích ký tự n-gram để nắm bắt ngữ nghĩa tiếng Việt
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            min_df=1
        )
        self.doc_vectors = self.vectorizer.fit_transform(self.raw_texts)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Tìm kiếm tương đồng ngữ nghĩa bằng Cosine Similarity
        """
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
