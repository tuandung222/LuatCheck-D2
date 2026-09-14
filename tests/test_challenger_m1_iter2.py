"""
Empirical Stress Test Harness: Challenger 1 Iteration 2
Assigned Scope:
1. PII Sanitization Stress:
   - Complex formatting variations of phone numbers (+84 9..., (+84)..., (0912)...).
   - CCCD 12-digit patterns (dot, hyphen, space, 4-4-4).
   - Extreme currency figures (500.000.000.000 VNĐ, 1.000.000.000.000 đồng, 123.456.789.000 đ)
     to confirm ZERO false positive redacting.
2. Dynamic Metric Stress:
   - Test calculate_unsupported_rate with:
     - Pure refusal / empty text -> 0.0
     - Uncited declarative advice -> 1.0
     - Properly cited grounded advice against labor_code_2019.json -> genuine evaluation
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.memory.sqlite_store import sanitize_pii
from evaluation.metrics import calculate_unsupported_rate
from src.verifier.l1_deterministic import L1EvidenceVerifier
from src.agent.state import Citation


@pytest.fixture(scope="module")
def legal_corpus():
    corpus_path = os.path.join(os.path.dirname(__file__), "..", "data", "corpus", "labor_code_2019.json")
    with open(corpus_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def verifier(legal_corpus):
    return L1EvidenceVerifier(legal_corpus)


# ============================================================================
# 1. PII SANITIZATION STRESS: PHONE NUMBERS
# ============================================================================

class TestPhoneSanitizationStress:
    @pytest.mark.parametrize("phone_input,phone_label", [
        ("Số điện thoại +84 912 345 678", "intl_+84_space"),
        ("Số điện thoại +84-912-345-678", "intl_+84_dash"),
        ("Số điện thoại +84.912.345.678", "intl_+84_dot"),
        ("Số điện thoại (+84) 912 345 678", "intl_paren_+84_space"),
        ("Số điện thoại (+84)912345678", "intl_paren_+84_nospace"),
        ("Số điện thoại (+84)-912-345-678", "intl_paren_+84_dash"),
        ("Số điện thoại (+84).912.345.678", "intl_paren_+84_dot"),
        ("Số điện thoại (0912) 345 678", "paren_4digit_space"),
        ("Số điện thoại (0912)-345-678", "paren_4digit_dash"),
        ("Số điện thoại (0912).345.678", "paren_4digit_dot"),
        ("Số điện thoại (0912)345678", "paren_4digit_nospace"),
        ("Số điện thoại (091) 234-5678", "paren_3digit_dash"),
        ("Số điện thoại (091) 234 5678", "paren_3digit_space"),
        ("Số điện thoại (091).234.5678", "paren_3digit_dot"),
        ("Số điện thoại (098) 765 4321", "paren_098_space"),
        ("Liên hệ (+84) 38 123 4567 khẩn cấp", "intl_paren_038"),
        ("Hotline 84 912 345 678 tư vấn", "intl_84_space"),
        ("Di động 090 123 4567 chính chủ", "090_spaces"),
        ("Di động 090-123-4567 chính chủ", "090_dashes"),
        ("Di động 090.123.4567 chính chủ", "090_dots"),
    ])
    def test_phone_formatting_variations_redacted(self, phone_input, phone_label):
        cleaned = sanitize_pii(phone_input)
        assert "[REDACTED_PII]" in cleaned, f"Failed to redact phone {phone_label}: {phone_input} -> {cleaned}"
        # Ensure raw phone components do not leak
        for component in ["912 345 678", "912-345-678", "912.345.678", "912345678",
                          "234-5678", "234 5678", "234.5678", "765 4321", "123 4567"]:
            assert component not in cleaned, f"Phone component {component} leaked in {cleaned}"

    def test_complex_phone_surrounding_tokens(self):
        text = "Liên hệ [ +84 912 345 678 ] hoặc Zalo {(0912) 345-678} hay (+84).912.345.678!"
        cleaned = sanitize_pii(text)
        assert cleaned.count("[REDACTED_PII]") == 3
        assert "912" not in cleaned
        assert "345" not in cleaned


# ============================================================================
# 2. PII SANITIZATION STRESS: CCCD 12-DIGIT PATTERNS
# ============================================================================

class TestCCCDSanitizationStress:
    @pytest.mark.parametrize("cccd_input,cccd_label", [
        ("Số CCCD 001234567890 cấp tại Hà Nội", "plain_12_digits"),
        ("Số định danh 001.234.567.890 công dân", "dots_3_3_3_3"),
        ("Số định danh 001-234-567-890 công dân", "dashes_3_3_3_3"),
        ("Số định danh 001 234 567 890 công dân", "spaces_3_3_3_3"),
        ("Số định danh cá nhân 0012 3456 7890 mới", "spaces_4_4_4"),
        ("Số định danh cá nhân 0012-3456-7890 mới", "dashes_4_4_4"),
        ("Số định danh cá nhân 0012.3456.7890 mới", "dots_4_4_4"),
        ("Mã thẻ CCCD: 001234567890 đính kèm", "prefix_cccd_colon"),
        ("Căn cước (001234567890) người lao động", "paren_enclosed"),
        ("Số thẻ [001234567890] hợp lệ", "bracket_enclosed"),
    ])
    def test_cccd_patterns_redacted(self, cccd_input, cccd_label):
        cleaned = sanitize_pii(cccd_input)
        assert "[REDACTED_PII]" in cleaned, f"Failed to redact CCCD {cccd_label}: {cccd_input} -> {cleaned}"
        assert "001234567890" not in cleaned
        assert "3456 7890" not in cleaned
        assert "3456-7890" not in cleaned
        assert "3456.7890" not in cleaned


# ============================================================================
# 3. EXTREME CURRENCY FIGURES: ZERO FALSE POSITIVE INVARIANCE
# ============================================================================

class TestCurrencyInvarianceStress:
    @pytest.mark.parametrize("currency_text", [
        "500.000.000.000 VNĐ",
        "1.000.000.000.000 đồng",
        "123.456.789.000 đ",
        "100.000.000.000 VND",
        "100.000.000.000 Đồng",
        "100.000.000.000 vnđ",
        "100.000.000.000 vnd",
        "123.456.789.000đ",
        "500.000.000.000VNĐ",
        "1.000.000.000.000đồng",
        "500.000.000.000 USD",
        "1.000.000.000.000 EUR",
        "100.000.000.000 tỷ",
        "84.500.000.000 VNĐ",
    ])
    def test_extreme_currency_figures_never_redacted(self, currency_text):
        cleaned = sanitize_pii(currency_text)
        assert "[REDACTED_PII]" not in cleaned, f"Currency figure falsely redacted: {currency_text} -> {cleaned}"
        assert cleaned == currency_text, f"Currency figure modified: expected '{currency_text}', got '{cleaned}'"

    @pytest.mark.parametrize("contract_sentence,expected_amount", [
        ("Bên B có trách nhiệm bồi thường thiệt hại số tiền là 500.000.000.000 VNĐ cho Bên A.", "500.000.000.000 VNĐ"),
        ("Vốn điều lệ của doanh nghiệp đăng ký là 1.000.000.000.000 đồng theo giấy phép đầu tư.", "1.000.000.000.000 đồng"),
        ("Tổng giá trị hợp đồng dịch vụ tư vấn pháp lý trị giá 123.456.789.000 đ thanh toán theo 3 đợt.", "123.456.789.000 đ"),
        ("Mức bồi thường vi phạm hợp đồng tối đa không vượt quá 84.500.000.000 VNĐ.", "84.500.000.000 VNĐ"),
        ("Cam kết góp vốn đầu tư 500.000.000.000VNĐ vào doanh nghiệp.", "500.000.000.000VNĐ"),
    ])
    def test_embedded_contract_currency_preservation(self, contract_sentence, expected_amount):
        cleaned = sanitize_pii(contract_sentence)
        assert "[REDACTED_PII]" not in cleaned, f"Contract sentence falsely redacted: {contract_sentence} -> {cleaned}"
        assert expected_amount in cleaned, f"Expected amount {expected_amount} missing from {cleaned}"

    def test_mixed_pii_and_currency_in_single_paragraph(self):
        mixed_text = (
            "Người đại diện là ông Nguyễn Văn A, số CCCD 0012 3456 7890, "
            "số điện thoại liên hệ (+84) 912 345 678. "
            "Công ty có vốn điều lệ 1.000.000.000.000 đồng và cam kết bồi thường 500.000.000.000 VNĐ."
        )
        cleaned = sanitize_pii(mixed_text)
        # CCCD and Phone must be redacted
        assert "0012 3456 7890" not in cleaned
        assert "912 345 678" not in cleaned
        assert cleaned.count("[REDACTED_PII]") == 2
        # Currencies must be preserved exactly
        assert "1.000.000.000.000 đồng" in cleaned
        assert "500.000.000.000 VNĐ" in cleaned


# ============================================================================
# 4. DYNAMIC METRIC STRESS: CALCULATE_UNSUPPORTED_RATE
# ============================================================================

class TestDynamicUnsupportedRateMetricStress:
    def test_pure_refusal_and_empty_inputs(self, verifier):
        """Pure refusal or empty text must return exactly 0.0 unsupported rate."""
        assert calculate_unsupported_rate("", [], verifier) == 0.0
        assert calculate_unsupported_rate("   \n\t  ", [], verifier) == 0.0
        assert calculate_unsupported_rate(None, [], verifier) == 0.0
        assert calculate_unsupported_rate("", ["Dieu_25"], verifier) == 0.0

    def test_uncited_declarative_advice(self, verifier):
        """Declarative affirmative legal advice without citations must return 1.0."""
        text_single = "Thời gian thử việc không quá 60 ngày đối với công việc có trình độ chuyên môn cao đẳng trở lên."
        assert calculate_unsupported_rate(text_single, [], verifier) == 1.0
        assert calculate_unsupported_rate(text_single, None, verifier) == 1.0

        text_multi = (
            "Hợp đồng lao động phải được giao kết bằng văn bản thành 02 bản. "
            "Thời gian thử việc tối đa là 180 ngày đối với người quản lý doanh nghiệp."
        )
        assert calculate_unsupported_rate(text_multi, [], verifier) == 1.0

    def test_grounded_advice_against_labor_code(self, verifier):
        """Fully supported advice citing correct statutory articles must return 0.0."""
        # Grounded against Dieu_25 (Thời gian thử việc)
        dieu_25_text = (
            "Thời gian thử việc không quá 60 ngày đối với công việc có chức danh nghề nghiệp "
            "cần trình độ chuyên môn kỹ thuật từ cao đẳng trở lên."
        )
        usr_25 = calculate_unsupported_rate(
            answer_text=dieu_25_text,
            cited_articles=["Dieu_25"],
            verifier=verifier,
            retrieved_article_ids=["Dieu_25"]
        )
        assert usr_25 == 0.0, f"Expected 0.0 for grounded Dieu_25, got {usr_25}"

        # Grounded against Dieu_26 (Tiền lương thử việc)
        dieu_26_text = (
            "Tiền lương của người lao động trong thời gian thử việc do hai bên thỏa thuận "
            "nhưng ít nhất phải bằng 85% mức lương của công việc đó."
        )
        usr_26 = calculate_unsupported_rate(
            answer_text=dieu_26_text,
            cited_articles=["Dieu_26"],
            verifier=verifier,
            retrieved_article_ids=["Dieu_26"]
        )
        assert usr_26 == 0.0, f"Expected 0.0 for grounded Dieu_26, got {usr_26}"

        # Grounded against Dieu_46 (Trợ cấp thôi việc)
        dieu_46_text = (
            "Khi hợp đồng lao động chấm dứt theo quy định, người sử dụng lao động có trách nhiệm "
            "trả trợ cấp thôi việc cho người lao động đã làm việc thường xuyên từ đủ 12 tháng trở lên."
        )
        usr_46 = calculate_unsupported_rate(
            answer_text=dieu_46_text,
            cited_articles=["Dieu_46"],
            verifier=verifier,
            retrieved_article_ids=["Dieu_46"]
        )
        assert usr_46 == 0.0, f"Expected 0.0 for grounded Dieu_46, got {usr_46}"

    def test_hallucinated_unsupported_claims_citing_statute(self, verifier):
        """Completely unsupported legal claims citing an article must return 1.0."""
        hallucinated_text = (
            "Thuế thu nhập cá nhân được khấu trừ trực tiếp tại nguồn "
            "theo biểu thuế lũy tiến từng phần mười phần trăm."
        )
        usr = calculate_unsupported_rate(
            answer_text=hallucinated_text,
            cited_articles=["Dieu_25"],
            verifier=verifier,
            retrieved_article_ids=["Dieu_25"]
        )
        assert usr == 1.0, f"Expected 1.0 for completely unsupported claim, got {usr}"

    def test_invalid_and_unretrieved_citations_penalized(self, verifier):
        """Citing non-existent or unretrieved provisions must be marked unsupported."""
        grounded_content = (
            "Thời gian thử việc không quá 60 ngày đối với công việc có chức danh nghề nghiệp "
            "cần trình độ chuyên môn kỹ thuật từ cao đẳng trở lên."
        )
        # Non-existent article ID
        usr_fake = calculate_unsupported_rate(
            answer_text=grounded_content,
            cited_articles=["Dieu_9999_Fake"],
            verifier=verifier,
            retrieved_article_ids=["Dieu_9999_Fake"]
        )
        assert usr_fake == 1.0, f"Expected 1.0 for fake article citation, got {usr_fake}"

        # Unretrieved article ID (retrieval provenance failure)
        usr_unretrieved = calculate_unsupported_rate(
            answer_text=grounded_content,
            cited_articles=["Dieu_25"],
            verifier=verifier,
            retrieved_article_ids=["Dieu_13"]  # Dieu_25 was not retrieved in session!
        )
        assert usr_unretrieved == 1.0, f"Expected 1.0 for unretrieved citation, got {usr_unretrieved}"

    def test_proportional_multi_sentence_metric_accuracy(self, verifier):
        """Calculates exact unsupported fraction across multi-sentence answers."""
        sent_grounded_1 = (
            "Thời gian thử việc không quá 60 ngày đối với công việc có chức danh nghề nghiệp "
            "cần trình độ chuyên môn kỹ thuật từ cao đẳng trở lên."
        )
        sent_grounded_2 = (
            "Không quá 30 ngày đối với công việc có chức danh nghề nghiệp cần trình độ "
            "chuyên môn kỹ thuật trung cấp, công nhân kỹ thuật, nhân viên nghiệp vụ."
        )
        sent_unsupported_1 = (
            "Thuế thu nhập cá nhân được khấu trừ trực tiếp tại nguồn theo biểu thuế lũy tiến từng phần."
        )
        sent_unsupported_2 = (
            "Hành vi vi phạm bị phạt tù từ hai năm đến bảy năm tù giam theo luật hình sự."
        )

        # 1 grounded + 1 unsupported = 0.5
        two_sentences = f"{sent_grounded_1}. {sent_unsupported_1}."
        usr_half = calculate_unsupported_rate(two_sentences, ["Dieu_25"], verifier, ["Dieu_25"])
        assert usr_half == 0.5, f"Expected 0.5 for 1/2 unsupported, got {usr_half}"

        # 2 grounded + 1 unsupported = 1/3 (0.3333)
        three_sentences_one_bad = f"{sent_grounded_1}. {sent_grounded_2}. {sent_unsupported_1}."
        usr_third = calculate_unsupported_rate(three_sentences_one_bad, ["Dieu_25"], verifier, ["Dieu_25"])
        assert usr_third == 0.3333, f"Expected 0.3333 for 1/3 unsupported, got {usr_third}"

        # 1 grounded + 2 unsupported = 2/3 (0.6667)
        three_sentences_two_bad = f"{sent_grounded_1}. {sent_unsupported_1}. {sent_unsupported_2}."
        usr_two_thirds = calculate_unsupported_rate(three_sentences_two_bad, ["Dieu_25"], verifier, ["Dieu_25"])
        assert usr_two_thirds == 0.6667, f"Expected 0.6667 for 2/3 unsupported, got {usr_two_thirds}"
