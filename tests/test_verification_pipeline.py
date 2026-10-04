"""
Unit tests for unified VerificationPipeline and modular grounding analyzer.
Validates mode transitions ('off', 'l1_only', 'l1_l2'), result structures, and DI integration.
"""
import pytest
from src.agent.state import Citation
from src.verifier.pipeline import VerificationPipeline, PipelineVerificationResult
from src.verifier.lexical_grounding import LexicalGroundingVerifier, LexicalGroundingVerifier as L1EvidenceVerifier
from src.verifier.semantic_nli import SemanticNLIVerifier, SemanticNLIVerifier as L2SemanticEntailmentVerifier
from src.verifier.grounding_analyzer import analyze_grounding


@pytest.fixture
def test_corpus():
    return [
        {
            "article_id": "Dieu_25",
            "law_id": "bllđ_2019",
            "law_name": "Bộ luật Lao động 2019",
            "title": "Điều 25. Thời gian thử việc",
            "content": "Thời gian thử việc do hai bên thỏa thuận căn cứ vào tính chất và mức độ phức tạp của công việc nhưng chỉ được thử việc một lần đối với một công việc và bảo đảm điều kiện sau đây: Không quá 60 ngày đối với công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên."
        }
    ]


def test_verification_pipeline_off_mode(test_corpus):
    pipeline = VerificationPipeline(corpus=test_corpus, mode="off")
    res = pipeline.verify(
        answer_text="Đây là câu trả lời không có căn cứ.",
        citations=[],
        retrieved_article_ids=[]
    )
    assert res.is_valid is True
    assert res.repair_feedback is None
    assert res.mode == "off"


def test_verification_pipeline_l1_only_valid(test_corpus):
    pipeline = VerificationPipeline(corpus=test_corpus, mode="l1_only")
    valid_text = "Thời gian thử việc do hai bên thỏa thuận không quá 60 ngày đối với công việc có chức danh trình độ chuyên môn kỹ thuật từ cao đẳng trở lên."
    citations = [Citation(article_id="Dieu_25")]

    res = pipeline.verify(
        answer_text=valid_text,
        citations=citations,
        retrieved_article_ids=["Dieu_25"]
    )
    assert res.is_valid is True
    assert res.repair_feedback is None
    assert res.l1_result is not None
    assert res.l1_result.is_valid is True


def test_verification_pipeline_l1_only_unsupported_rejection(test_corpus):
    pipeline = VerificationPipeline(corpus=test_corpus, mode="l1_only")
    unsupported_text = "Người lao động được quyền tự ý bỏ việc bất kỳ khi nào mà không bị bất kỳ chế tài nào."
    citations = [Citation(article_id="Dieu_25")]

    res = pipeline.verify(
        answer_text=unsupported_text,
        citations=citations,
        retrieved_article_ids=["Dieu_25"]
    )
    assert res.is_valid is False
    assert res.repair_feedback is not None
    assert "chưa tìm thấy căn cứ đối ứng" in res.repair_feedback


def test_grounding_analyzer_isolated(test_corpus):
    verifier = L1EvidenceVerifier(test_corpus)
    valid_text = "Thời gian thử việc do hai bên thỏa thuận không quá 60 ngày đối với công việc có chức danh trình độ chuyên môn kỹ thuật từ cao đẳng trở lên."
    res = analyze_grounding(valid_text, [{"article_id": "Dieu_25"}], verifier)

    assert "is_valid" in res
    assert res["is_valid"] is True
    assert res["grounded_ratio"] > 0.0
    assert len(res["sentences_data"]) >= 1


def test_explicit_naming_and_verification_mode_enum(test_corpus):
    """Test self-documenting LexicalGroundingVerifier, SemanticNLIVerifier, and VerificationMode enum."""
    from src.verifier.lexical_grounding import LexicalGroundingVerifier
    from src.verifier.semantic_nli import SemanticNLIVerifier
    from src.verifier.pipeline import VerificationMode

    lexical_v = LexicalGroundingVerifier(test_corpus)
    semantic_v = SemanticNLIVerifier(test_corpus)

    pipeline = VerificationPipeline(
        lexical_verifier=lexical_v,
        semantic_verifier=semantic_v,
        mode=VerificationMode.LEXICAL_GROUNDING
    )

    valid_text = "Thời gian thử việc do hai bên thỏa thuận không quá 60 ngày đối với công việc có chức danh trình độ chuyên môn kỹ thuật từ cao đẳng trở lên."
    citations = [Citation(article_id="Dieu_25")]

    res = pipeline.verify(
        answer_text=valid_text,
        citations=citations,
        retrieved_article_ids=["Dieu_25"]
    )
    assert res.is_valid is True
    assert res.grounding_result is not None
    assert res.l1_result is res.grounding_result

