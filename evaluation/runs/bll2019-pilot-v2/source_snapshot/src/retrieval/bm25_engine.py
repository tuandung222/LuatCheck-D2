"""
BM25 Retrieval Engine for Vietnamese Legal Documents
"""
import re
import json
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi


def tokenize_vietnamese(text: str) -> List[str]:
    """
    Basic tokenization and normalization for Vietnamese legal documents.
    """
    text = text.lower()
    # Remove punctuation, retain alphanumeric and Vietnamese characters
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = text.split()
    return tokens


class BM25Retriever:
    def __init__(self, corpus: List[Dict[str, Any]]):
        self.corpus = corpus
        self.doc_ids = [
            str(doc.get("doc_id") or doc.get("article_id") or doc.get("id") or "")
            for doc in corpus
        ]
        self.tokenized_corpus = [
            tokenize_vietnamese(f"{doc.get('title') or doc.get('section_title', '')} {doc.get('content', '')}")
            for doc in corpus
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Return a list of (article_id, score) tuples sorted in descending order of BM25 score.
        """
        tokenized_query = tokenize_vietnamese(query)
        if not tokenized_query:
            return []
        scores = self.bm25.get_scores(tokenized_query)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in ranked_indices:
            if scores[idx] > 0:
                results.append((self.doc_ids[idx], float(scores[idx])))
        return results
