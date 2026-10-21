"""
Unit tests for L2 Semantic Entailment Verifier (Natural Language Inference Layer)
Validates entailment, contradiction, neutral, and fallback behaviors.
"""
import pytest
import json
from unittest.mock import patch
from src.verifier.semantic_nli import SemanticNLIVerifier, SemanticNLIVerifier as L2SemanticEntailmentVerifier


@pytest.fixture
def sample_corpus():
    with open("data/corpus/labor_code_2019.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def verifier(sample_corpus):
    # Uses threshold 0.30 for TF-IDF semantic comparator
    return L2SemanticEntailmentVerifier(sample_corpus, entailment_threshold=0.30, use_slm=False)


# =========================================================================
# 1. ENTAILMENT TEST CASES
# =========================================================================

def test_l2_entailment_probation_period(verifier):
    """
    Claim trực tiếp phản ánh nội dung Điều 25 khoản 2 (thời gian thử việc không quá 60 ngày).
    Kỳ vọng: is_entailed is True, score >= 0.30, status == 'ENTAILMENT'.
    """
    claim = "Thời gian thử việc đối với người làm công việc có chức danh nghề nghiệp cần trình độ chuyên môn, kỹ thuật từ cao đẳng trở lên không quá 60 ngày."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_25")
    assert is_entailed is True
    assert score >= 0.30
    assert msg == "ENTAILMENT"


def test_l2_entailment_probation_wage(verifier):
    """
    Claim phản ánh Điều 26 (tiền lương thử việc ít nhất bằng 85% lương công việc).
    Kỳ vọng: is_entailed is True, score >= 0.30, status == 'ENTAILMENT'.
    """
    claim = "Tiền lương của người lao động trong thời gian thử việc ít nhất phải bằng 85% mức lương của công việc đó."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_26")
    assert is_entailed is True
    assert score >= 0.30
    assert msg == "ENTAILMENT"


def test_l2_entailment_resignation_notice(verifier):
    """
    Claim phản ánh Điều 35 (báo trước ít nhất 45 ngày với hợp đồng không xác định thời hạn).
    Kỳ vọng: is_entailed is True, score >= 0.30, status == 'ENTAILMENT'.
    """
    claim = "Người lao động làm việc theo hợp đồng lao động không xác định thời hạn có quyền đơn phương chấm dứt hợp đồng nhưng phải báo trước ít nhất 45 ngày."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_35")
    assert is_entailed is True
    assert score >= 0.30
    assert msg == "ENTAILMENT"


# =========================================================================
# 2. NEUTRAL & OUT-OF-DOMAIN TEST CASES
# =========================================================================

def test_l2_neutral_unrelated_domain(verifier):
    """
    Claim về chế độ thai sản/nghĩa vụ quân sự nhưng lại trích dẫn Điều 25 (Thời gian thử việc).
    Kỳ vọng: is_entailed is False, score < 0.30, status == 'NEUTRAL_OR_UNSUPPORTED'.
    """
    claim = "Lao động nữ được nghỉ thai sản trước và sau khi sinh con là 06 tháng."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_25")
    assert is_entailed is False
    assert score < 0.30
    assert "NEUTRAL" in msg or "UNSUPPORTED" in msg


def test_l2_neutral_unrelated_labor_topic(verifier):
    """
    Claim về xử lý kỷ luật sa thải nhưng trích dẫn Điều 13 (Hợp đồng lao động).
    Kỳ vọng: is_entailed is False, score < 0.30.
    """
    claim = "Người sử dụng lao động được áp dụng hình thức kỷ luật sa thải khi người lao động có hành vi trộm cắp."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_13")
    assert is_entailed is False
    assert score < 0.30


# =========================================================================
# 3. CONTRADICTION & OVERCLAIM TEST CASES
# =========================================================================

def test_l2_contradiction_probation_duration(verifier):
    """
    Claim mâu thuẫn: khẳng định thời gian thử việc trình độ đại học có thể lên tới 180 ngày hoặc 1 năm.
    Điều 25 quy định tối đa 60 ngày đối với cao đẳng trở lên (180 ngày chỉ dành cho người quản lý doanh nghiệp).
    Kỳ vọng: is_entailed is False, status == 'CONTRADICTION'.
    """
    claim = "Người lao động có trình độ đại học làm nhân viên văn phòng có thể bị áp dụng thời gian thử việc tối đa 180 ngày theo quyết định của giám đốc."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_25")
    assert is_entailed is False
    assert msg == "CONTRADICTION"


def test_l2_contradiction_illegal_penalty(verifier):
    """
    Claim mâu thuẫn quy định cấm: khẳng định công ty có quyền phạt tiền người lao động.
    """
    claim = "Người sử dụng lao động có quyền phạt tiền nhân viên vi phạm kỷ luật nội bộ."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_122")
    assert is_entailed is False
    assert msg == "CONTRADICTION"


def test_l2_contradiction_probation_zero_wage(verifier):
    """
    Claim mâu thuẫn: thời gian thử việc 0 đồng hoặc không trả lương.
    """
    claim = "Thời gian thử việc 0 đồng cho sinh viên mới ra trường theo chính sách công ty."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_26")
    assert is_entailed is False
    assert msg == "CONTRADICTION"


# =========================================================================
# 4. FALLBACK & ERROR RESILIENCE TEST CASES
# =========================================================================

def test_l2_fallback_missing_article_id(verifier):
    """
    Mã điều luật không tồn tại trong corpus (ví dụ: Dieu_999).
    Kỳ vọng: không gây crash/exception, trả về (False, 0.0, error_message).
    """
    claim = "Theo Điều 999, công ty có quyền phạt tiền nhân viên."
    is_entailed, score, msg = verifier.verify_entailment(claim, "Dieu_999")
    assert is_entailed is False
    assert score == 0.0
    assert "không tồn tại" in msg


def test_l2_fallback_empty_claim(verifier):
    """
    Chuỗi claim rỗng hoặc chỉ có khoảng trắng.
    Kỳ vọng: xử lý an toàn không văng lỗi.
    """
    is_entailed, score, msg = verifier.verify_entailment("", "Dieu_25")
    assert is_entailed is False
    assert score == 0.0


def test_l2_article_id_normalization(verifier):
    """
    Kiểm tra tính chịu lỗi của việc chuẩn hóa mã điều luật:
    'Điều 25', 'dieu_25', 'Điều_25', 'Dieu 25' đều phải được map chính xác.
    """
    claim = "Thời gian thử việc đối với người có trình độ cao đẳng trở lên không quá 60 ngày."
    for variant in ["Dieu_25", "dieu_25", "Điều 25", "điều_25"]:
        is_ent, score, _ = verifier.verify_entailment(claim, variant)
        assert is_ent is True, f"Failed for variant: {variant}"
        assert score >= 0.30


# =========================================================================
# 5. BATCH ANSWER VERIFICATION (verify_all_claims)
# =========================================================================

def test_l2_verify_all_claims_fully_supported(verifier):
    """
    Đoạn văn bản trả lời gồm 2 câu, cả 2 đều có căn cứ vững chắc tại Điều 25 và Điều 26.
    Kỳ vọng: result['is_entailed'] is True, failed_claims rỗng.
    """
    answer = (
        "Thời gian thử việc đối với người có trình độ cao đẳng trở lên không quá 60 ngày. "
        "Tiền lương của người lao động trong thời gian thử việc ít nhất phải bằng 85% mức lương của công việc đó."
    )
    citations = ["Dieu_25", "Dieu_26"]
    res = verifier.verify_all_claims(answer, citations)

    assert res["is_entailed"] is True
    assert len(res["failed_claims"]) == 0
    assert res["average_score"] >= 0.30
    assert res["total_sentences"] == 2


def test_l2_verify_all_claims_partial_unsupported_fails(verifier):
    """
    Đoạn văn bản có 1 câu hợp lệ và 1 câu hoàn toàn không có căn cứ (bịa đặt quy định xử phạt).
    Kỳ vọng: result['is_entailed'] is False, failed_claims ghi nhận đúng câu vi phạm.
    """
    answer = (
        "Thời gian thử việc đối với người có trình độ cao đẳng trở lên không quá 60 ngày. "
        "Người sử dụng lao động có quyền xử phạt tiền lên tới 50 triệu đồng nếu nhân viên vi phạm quy chế."
    )
    citations = ["Dieu_25"]
    res = verifier.verify_all_claims(answer, citations)

    assert res["is_entailed"] is False
    assert len(res["failed_claims"]) >= 1
    assert any("phạt tiền" in f["sentence"] for f in res["failed_claims"])


def test_l2_threshold_sensitivity(sample_corpus):
    """
    Kiểm tra tính nhạy cảm của ngưỡng entailment_threshold:
    Khi đặt ngưỡng khắt khe (0.80), câu trùng khớp một phần sẽ bị từ chối.
    Khi đặt ngưỡng lỏng (0.20), câu đó sẽ được chấp nhận.
    """
    v_strict = L2SemanticEntailmentVerifier(sample_corpus, entailment_threshold=0.80, use_slm=False)
    v_relaxed = L2SemanticEntailmentVerifier(sample_corpus, entailment_threshold=0.20, use_slm=False)

    claim = "Thời gian thử việc đối với công việc có chức danh nghề nghiệp cần trình độ cao đẳng trở lên không quá 60 ngày."
    is_ent_strict, score_strict, _ = v_strict.verify_entailment(claim, "Dieu_25")
    is_ent_relaxed, score_relaxed, _ = v_relaxed.verify_entailment(claim, "Dieu_25")

    assert is_ent_relaxed is True
    assert score_strict == score_relaxed
    assert is_ent_strict is False


def test_l2_slm_nli_integration_mocked(sample_corpus):
    """
    Kiểm tra Engine 1 SLM caller được kích hoạt và phân tích đúng định dạng JSON từ Ollama.
    """
    v_slm = L2SemanticEntailmentVerifier(sample_corpus, entailment_threshold=0.50, use_slm=True)
    
    mock_resp = {
        "message": {
            "content": json.dumps({"verdict": "ENTAILMENT", "confidence": 0.95})
        }
    }
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_resp

        is_ent, score, msg = v_slm.verify_entailment("Thời gian thử việc không quá 60 ngày.", "Dieu_25")
        assert is_ent is True
        assert score == 0.95
        assert msg == "ENTAILMENT"


# =========================================================================
# 6. REMEDIATION: SHORT SENTENCE BYPASS & ANTI-VACUOUS APPROVAL
# =========================================================================

def test_short_sentence_bypass_illegal_termination(verifier):
    answer = "Được sa thải."
    res = verifier.verify_all_claims(answer, ["Dieu_37"])
    assert res["is_entailed"] is False
    assert res["total_sentences"] == 1
    assert res["failed_claims"][0]["sentence"] == "Được sa thải"


def test_short_sentence_bypass_holding_degrees(verifier):
    answer = "Giữ bằng cấp."
    res = verifier.verify_all_claims(answer, ["Dieu_13"])
    assert res["is_entailed"] is False
    assert res["total_sentences"] == 1


def test_short_sentences_combined(verifier):
    answer = "Được sa thải. Giữ bằng cấp."
    res = verifier.verify_all_claims(answer, ["Dieu_37", "Dieu_122"])
    assert res["is_entailed"] is False
    assert res["total_sentences"] == 2
    assert len(res["failed_claims"]) == 2


def test_vacuous_approval_empty_answer(verifier):
    res = verifier.verify_all_claims("", ["Dieu_25"])
    assert res["is_entailed"] is False
    assert res["total_sentences"] == 0


def test_vacuous_approval_whitespace_or_punctuation(verifier):
    res = verifier.verify_all_claims("...", ["Dieu_25"])
    assert res["is_entailed"] is False
    assert res["total_sentences"] == 0


def test_no_citations_provided(verifier):
    res = verifier.verify_all_claims("Thời gian thử việc tối đa 60 ngày.", [])
    assert res["is_entailed"] is False


# =========================================================================
# 7. REMEDIATION: QUANTIFIER & NUMERICAL CLASH
# =========================================================================

def test_article_25_probation_100_days_clash(verifier):
    claim = "Thời gian thử việc đối với người làm công việc có chức danh nghề nghiệp cần trình độ chuyên môn kỹ thuật là 100 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_25")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_article_25_probation_90_days_office_clash(verifier):
    claim = "Thời gian thử việc đối với nhân viên văn phòng là 90 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_25")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_article_25_probation_exceeding_180_days(verifier):
    claim = "Thời gian thử việc cho giám đốc điều hành là 200 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_25")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_article_25_probation_multiple_times(verifier):
    claim = "Công ty có quyền áp dụng thời gian thử việc 2 lần đối với một vị trí công việc."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_25")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_article_20_fixed_term_contract_years_clash(verifier):
    claim = "Hợp đồng lao động xác định thời hạn có thời hạn 5 năm."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_20")
    assert is_ent is False
    assert msg == "CONTRADICTION"

    claim_10y = "Hợp đồng lao động xác định thời hạn kéo dài 10 năm."
    is_ent, score, msg = verifier.verify_entailment(claim_10y, "Dieu_20")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_article_26_probation_wage_percentage_clash(verifier):
    claim = "Tiền lương thử việc của người lao động bằng 70% mức lương của công việc."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_26")
    assert is_ent is False
    assert msg == "CONTRADICTION"


# =========================================================================
# 8. REMEDIATION: NEGATION & POLARITY CONTRADICTIONS
# =========================================================================

def test_article_24_probation_under_1_month_prohibition(verifier):
    claim = "Được phép thử việc đối với hợp đồng lao động có thời hạn dưới 1 tháng."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_24")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_article_26_unpaid_probation_prohibition(verifier):
    claim = "Người lao động không được trả lương trong thời gian thử việc."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_26")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_article_37_illegal_dismissal_pregnancy(verifier):
    claim = "Doanh nghiệp có quyền sa thải nhân viên nữ mang thai."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_37")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_article_122_illegal_financial_penalty(verifier):
    claim = "Người sử dụng lao động được phạt tiền nhân viên vi phạm quy chế."
    is_ent, score, msg = verifier.verify_entailment(claim, "Dieu_122")
    assert is_ent is False
    assert msg == "CONTRADICTION"


def test_timeout_setting_default(sample_corpus):
    v = L2SemanticEntailmentVerifier(sample_corpus, use_slm=True)
    assert v.slm_timeout == 10.0


# =========================================================================
# 9. CHALLENGER M1-R2-1 REFINEMENTS
# =========================================================================

def test_article_25_probation_cong_nhan_ky_thuat_cap_30_days(verifier):
    """
    Article 25 Khoản 3: Enforce 30-day cap for 'công nhân kỹ thuật', 'trung cấp', 'sơ cấp'
    even if 'kỹ thuật' is matched in the text.
    """
    # 45 days for technical worker ('công nhân kỹ thuật') -> CONTRADICTION (> 30 days)
    claim1 = "Thời gian thử việc đối với công nhân kỹ thuật là 45 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim1, "Dieu_25")
    assert is_ent is False
    assert msg == "CONTRADICTION"

    # 40 days for intermediate degree ('trình độ trung cấp') -> CONTRADICTION (> 30 days)
    claim2 = "Thời gian thử việc đối với người có trình độ kỹ thuật trung cấp là 40 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim2, "Dieu_25")
    assert is_ent is False
    assert msg == "CONTRADICTION"

    # 35 days for elementary vocational ('sơ cấp') -> CONTRADICTION (> 30 days)
    claim3 = "Thời gian thử việc cho lao động có chứng chỉ sơ cấp là 35 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim3, "Dieu_25")
    assert is_ent is False
    assert msg == "CONTRADICTION"

    # 25 days for technical worker ('công nhân kỹ thuật') -> NOT a contradiction (<= 30 days)
    claim4 = "Thời gian thử việc đối với công nhân kỹ thuật là 25 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim4, "Dieu_25")
    assert msg != "CONTRADICTION"


def test_article_24_explicit_short_contract_durations(verifier):
    """
    Article 24 Khoản 3: Detect explicit contract durations < 30 days
    (e.g. '15 ngày', '2 tuần', '3 tuần') asserting probation and flag as contradiction.
    """
    # 15 days contract asserting probation -> CONTRADICTION
    claim1 = "Hợp đồng lao động 15 ngày có áp dụng thời gian thử việc 3 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim1, "Dieu_24")
    assert is_ent is False
    assert msg == "CONTRADICTION"

    # 2 weeks contract asserting probation -> CONTRADICTION
    claim2 = "Người lao động ký hợp đồng 2 tuần vẫn phải thử việc theo yêu cầu của công ty."
    is_ent, score, msg = verifier.verify_entailment(claim2, "Dieu_24")
    assert is_ent is False
    assert msg == "CONTRADICTION"

    # 3 weeks contract asserting probation -> CONTRADICTION
    claim3 = "Hợp đồng thời hạn 3 tuần được áp dụng thử việc."
    is_ent, score, msg = verifier.verify_entailment(claim3, "Dieu_24")
    assert is_ent is False
    assert msg == "CONTRADICTION"

    # Explicit prohibition for 15 days contract -> NOT a contradiction (entails statutory prohibition)
    claim4 = "Không áp dụng thử việc đối với hợp đồng lao động 15 ngày."
    is_ent, score, msg = verifier.verify_entailment(claim4, "Dieu_24")
    assert msg != "CONTRADICTION"


def test_corpus_driven_dynamic_bound_extraction_unseen_articles():
    """
    Verify that SemanticNLIVerifier dynamically extracts quantitative bounds
    directly from any statutory/SOP premise text without hardcoded article IDs.
    """
    synthetic_corpus = [
        {
            "article_id": "SOP_SEC_901",
            "title": "Quy định thời gian xử lý sự cố và mức đền bù SLA",
            "content": (
                "1. Thời gian phản hồi sự cố khẩn cấp chỉ được gia hạn một lần đối với một sự cố. "
                "2. Không quá 15 ngày đối với quy trình rà soát an ninh định kỳ. "
                "3. Mức bồi hoàn dịch vụ ít nhất phải bằng 90% giá trị gói cước tháng đó."
            ),
        }
    ]
    custom_verifier = L2SemanticEntailmentVerifier(synthetic_corpus, entailment_threshold=0.30)

    # 1. Violates "chỉ được ... một lần" -> CONTRADICTION
    is_ent_1, _, msg_1 = custom_verifier.verify_entailment(
        "Thời gian phản hồi sự cố khẩn cấp được gia hạn 2 lần đối với một sự cố.",
        "SOP_SEC_901",
    )
    assert is_ent_1 is False
    assert msg_1 == "CONTRADICTION"

    # 2. Violates "Không quá 15 ngày" -> CONTRADICTION
    is_ent_2, _, msg_2 = custom_verifier.verify_entailment(
        "Thời hạn tối đa là 30 ngày đối với quy trình rà soát an ninh định kỳ.",
        "SOP_SEC_901",
    )
    assert is_ent_2 is False
    assert msg_2 == "CONTRADICTION"

    # 3. Violates "ít nhất phải bằng 90%" -> CONTRADICTION
    is_ent_3, _, msg_3 = custom_verifier.verify_entailment(
        "Mức bồi hoàn dịch vụ bằng 75% giá trị gói cước tháng đó.",
        "SOP_SEC_901",
    )
    assert is_ent_3 is False
    assert msg_3 == "CONTRADICTION"

