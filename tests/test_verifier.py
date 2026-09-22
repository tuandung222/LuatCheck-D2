"""
Unit tests for L1 Evidence Verifier
"""
import pytest
import json
from src.verifier.l1_deterministic import L1EvidenceVerifier
from src.agent.state import Citation


@pytest.fixture
def sample_corpus():
    with open("data/corpus/labor_code_2019.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def verifier(sample_corpus):
    return L1EvidenceVerifier(sample_corpus)


def test_valid_citation_pass(verifier):
    answer = "Thời gian thử việc đối với người có trình độ cao đẳng trở lên không quá 60 ngày theo quy định."
    citations = [Citation(article_id="Dieu_25")]
    retrieved = ["Dieu_25", "Dieu_24"]

    res = verifier.verify(answer, citations, retrieved)
    assert res.is_valid is True
    assert len(res.invalid_citations) == 0


def test_fake_article_id_fails(verifier):
    answer = "Theo Điều 999 Bộ luật Lao động, công ty được quyền phạt tiền nhân viên nghỉ việc."
    citations = [Citation(article_id="Dieu_999")]
    retrieved = ["Dieu_999"]

    res = verifier.verify(answer, citations, retrieved)
    assert res.is_valid is False
    assert any("không tồn tại" in s for s in res.invalid_citations)


def test_unretrieved_article_fails(verifier):
    answer = "Người lao động có quyền đơn phương chấm dứt hợp đồng theo Điều 35."
    citations = [Citation(article_id="Dieu_35")]
    retrieved = ["Dieu_13"]  # Dieu_35 was never retrieved in session

    res = verifier.verify(answer, citations, retrieved)
    assert res.is_valid is False
    assert any("chưa từng được bạn tra cứu" in s for s in res.invalid_citations)


def test_l2_semantic_entailment(sample_corpus):
    from src.verifier.l2_semantic import L2SemanticEntailmentVerifier
    l2_ver = L2SemanticEntailmentVerifier(sample_corpus, entailment_threshold=0.30)

    # Entailed statement (matching Dieu_25 probation rules)
    claim = "Thời gian thử việc đối với người làm công việc có chức danh nghề nghiệp cần trình độ cao đẳng trở lên không quá 60 ngày."
    is_entailed, score, msg = l2_ver.verify_entailment(claim, "Dieu_25")
    assert is_entailed is True
    assert score >= 0.30
    assert msg == "ENTAILMENT"

    # Non-entailed claim (unrelated topic compared to Dieu_25)
    unrelated = "Người sử dụng lao động có quyền xử lý kỷ luật sa thải đối với hành vi trộm cắp tài sản."
    is_entailed_unrelated, score_unrelated, msg_unrelated = l2_ver.verify_entailment(unrelated, "Dieu_25")
    assert score_unrelated < 0.50
