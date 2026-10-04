"""
Unit and integration tests for NeuralDenseRetriever and Deep Learning Embeddings.
Validates CPU performance, matrix cosine similarity, fallback handling, and Dependency Injection.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from src.retrieval.dense_engine import NeuralDenseRetriever, TfidfDenseRetriever
from src.retrieval.hybrid_rrf import HybridLegalRetriever
from src.interfaces.base import BaseDenseRetriever


@pytest.fixture
def sample_corpus():
    return [
        {
            "article_id": "Dieu_25",
            "law_id": "bllđ_2019",
            "law_name": "Bộ luật Lao động 2019",
            "title": "Điều 25. Thời gian thử việc",
            "content": "Thời gian thử việc do hai bên thỏa thuận căn cứ vào tính chất và mức độ phức tạp của công việc nhưng chỉ được thử việc một lần đối với một công việc và bảo đảm điều kiện: Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên."
        },
        {
            "article_id": "Dieu_35",
            "law_id": "bllđ_2019",
            "law_name": "Bộ luật Lao động 2019",
            "title": "Điều 35. Quyền đơn phương chấm dứt hợp đồng lao động của người lao động",
            "content": "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động nhưng phải báo trước cho người sử dụng lao động ít nhất 30 ngày nếu làm việc theo hợp đồng lao động xác định thời hạn có thời hạn từ 12 tháng đến 36 tháng."
        },
        {
            "article_id": "Dieu_105",
            "law_id": "bllđ_2019",
            "law_name": "Bộ luật Lao động 2019",
            "title": "Điều 105. Thời giờ làm việc bình thường",
            "content": "Thời giờ làm việc bình thường không quá 08 giờ trong 01 ngày và không quá 48 giờ trong 01 tuần. Người sử dụng lao động có quyền quy định thời giờ làm việc theo ngày hoặc tuần."
        }
    ]


def test_tfidf_dense_retriever_protocol(sample_corpus):
    retriever = TfidfDenseRetriever(sample_corpus)
    assert isinstance(retriever, BaseDenseRetriever)
    
    results = retriever.search("thời gian thử việc cao đẳng", top_k=2)
    assert len(results) >= 1
    assert results[0][0] == "Dieu_25"
    assert isinstance(results[0][1], float)


def test_neural_dense_retriever_offline_fallback(sample_corpus):
    """When embedding endpoint is unreachable, retriever falls back gracefully without crash."""
    with patch("requests.post", side_effect=Exception("Connection refused")):
        retriever = NeuralDenseRetriever(
            sample_corpus,
            model_name="all-minilm",
            endpoint="http://invalid-host:11434"
        )
        assert retriever._is_online is False
        results = retriever.search("thử việc bao nhiêu ngày", top_k=2)
        assert len(results) >= 1
        assert results[0][0] == "Dieu_25"


def test_neural_dense_retriever_simulated_neural_mode(sample_corpus):
    """Test normalized dot product matrix similarity when online embeddings are returned."""
    # Deterministic 4-dimensional mock embeddings
    mock_embeddings = {
        "thử việc": [1.0, 0.0, 0.0, 0.0],
        "Dieu_25": [0.95, 0.1, 0.0, 0.0],
        "Dieu_35": [0.0, 0.9, 0.1, 0.0],
        "Dieu_105": [0.0, 0.0, 0.1, 0.95]
    }

    def fake_post(url, json=None, timeout=None):
        prompt = json.get("prompt", "")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "thử việc do hai bên" in prompt:
            mock_resp.json.return_value = {"embedding": mock_embeddings["Dieu_25"]}
        elif "đơn phương chấm dứt" in prompt:
            mock_resp.json.return_value = {"embedding": mock_embeddings["Dieu_35"]}
        elif "thời giờ làm việc" in prompt:
            mock_resp.json.return_value = {"embedding": mock_embeddings["Dieu_105"]}
        else:
            mock_resp.json.return_value = {"embedding": mock_embeddings["thử việc"]}
        return mock_resp

    with patch("requests.post", side_effect=fake_post):
        retriever = NeuralDenseRetriever(
            sample_corpus,
            model_name="all-minilm",
            endpoint="http://127.0.0.1:11434"
        )
        assert retriever._is_online is True
        assert retriever.doc_matrix is not None
        assert retriever.doc_matrix.shape == (3, 4)

        # Search with query
        results = retriever.search("thử việc", top_k=2)
        assert len(results) >= 1
        assert results[0][0] == "Dieu_25"
        assert results[0][1] > 0.8


def test_hybrid_retriever_dependency_injection(sample_corpus, tmp_path):
    import json
    corpus_file = tmp_path / "test_corpus.json"
    corpus_file.write_text(json.dumps(sample_corpus, ensure_ascii=False), encoding="utf-8")

    class CustomMockDense(BaseDenseRetriever):
        def search(self, query: str, top_k: int = 5):
            return [("Dieu_105", 0.99)]

    custom_dense = CustomMockDense()
    hybrid = HybridLegalRetriever(corpus_path=str(corpus_file), dense_retriever=custom_dense)
    assert hybrid.dense is custom_dense

    results = hybrid.search("quy định làm việc", top_k=1)
    assert len(results) == 1
    assert results[0]["article_id"] == "Dieu_105"
