"""
Adversarial Memory Subsystem & Cache Re-Verification Stress Testing Suite
Challenger 1 — Milestone 1: Memory & Cache Stress Testing

Tests 5 core challenge dimensions:
1. PII Sanitization Adversarial Variations:
   - Weird formatting of Vietnamese mobile phone numbers (spaces, dots, dashes, parentheses, +84).
   - CCCD variations (12 digits, 3-3-3-3, 4-4-4, embedded punctuation).
   - Email variations (subdomains, plus tags, brackets, special characters).
2. False Positive Invariance on Legal & Financial Text:
   - Statutes, decrees, circulars, decision codes, dates, money amounts, percentages.
3. Cache Re-Verification with Corrupted / Invalid Article ID:
   - Ensures L1 verifier catches fake citations on cache retrieval and safely falls back to ReAct.
4. Cache Index Version Mismatch:
   - Stored under 'v2025.1', queried under 'v2026.1' -> zero cache contamination.
5. Cache Re-Verification under L2 Semantic Contradiction:
   - Valid statutory code with fabricated/contradictory content rejected by L2 verifier.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import sqlite3
import json
import re
import requests
from unittest.mock import patch

from src.memory.sqlite_store import SQLiteEpisodicStore, sanitize_pii
from src.agent.loop import LuatCheckAgent
from src.agent.state import ActionType, Citation


# ============================================================================
# 1. ADVERSARIAL PII TEST FIXTURES
# ============================================================================

ADVERSARIAL_PHONES = [
    # (id, raw_input, expected_contain_pii, description)
    ("phone_standard_09", "SĐT liên hệ: 0912345678 khi cần", True, "Standard 10-digit 09x"),
    ("phone_standard_03", "Gọi cho tôi số 0387654321 ngay", True, "Standard 10-digit 03x"),
    ("phone_standard_07", "Hotline tư vấn: 0771234567", True, "Standard 10-digit 07x"),
    ("phone_standard_08", "Số di động 0868888888", True, "Standard 10-digit 08x"),
    ("phone_standard_05", "Liên lạc qua 0523456789", True, "Standard 10-digit 05x"),
    ("phone_intl_plus84_nospace", "Số quốc tế +84912345678", True, "International +84 without space"),
    ("phone_intl_84_nospace", "Số quốc tế 84912345678", True, "International 84 without space"),
    ("phone_dots_3_3_4", "Số điện thoại 090.123.4567", True, "Phone formatted with dots (3-3-4)"),
    ("phone_dots_4_3_3", "Số điện thoại 0901.234.567", True, "Phone formatted with dots (4-3-3)"),
    ("phone_dashes_3_3_4", "Số điện thoại 090-123-4567", True, "Phone formatted with dashes (3-3-4)"),
    ("phone_dashes_4_3_3", "Số điện thoại 0901-234-567", True, "Phone formatted with dashes (4-3-3)"),
    ("phone_spaces_3_3_4", "Số điện thoại 091 234 5678", True, "Phone formatted with spaces (3-3-4)"),
    ("phone_spaces_4_3_3", "Số điện thoại 0912 345 678", True, "Phone formatted with spaces (4-3-3)"),
    # Tricky adversarial formats with spaces / punctuation after country code:
    ("phone_intl_plus84_space", "Số điện thoại +84 912 345 678", True, "International +84 with space after country code"),
    ("phone_intl_plus84_dash", "Số điện thoại +84-912-345-678", True, "International +84 with dash after country code"),
    ("phone_intl_plus84_dots", "Số điện thoại +84.912.345.678", True, "International +84 with dots after country code"),
    ("phone_intl_84_space", "Số điện thoại 84 912 345 678", True, "Prefix 84 with space"),
    ("phone_paren_area_dash", "Số điện thoại (091) 234-5678", True, "Parentheses around area code with dash"),
    ("phone_paren_area_space", "Số điện thoại (0912) 345 678", True, "Parentheses around 4 digits with space"),
    ("phone_paren_country_code", "Số điện thoại (+84) 912 345 678", True, "Parentheses around country code (+84)"),
]

ADVERSARIAL_CCCD = [
    # (id, raw_input, expected_contain_pii, description)
    ("cccd_12_plain", "Số CCCD của tôi là 001234567890 ghi trên hợp đồng", True, "Standard 12 digits plain"),
    ("cccd_dots_3_3_3_3", "Số định danh cá nhân 001.234.567.890", True, "CCCD grouped 3-3-3-3 with dots"),
    ("cccd_dashes_3_3_3_3", "Số định danh cá nhân 001-234-567-890", True, "CCCD grouped 3-3-3-3 with dashes"),
    ("cccd_spaces_3_3_3_3", "Số định danh cá nhân 001 234 567 890", True, "CCCD grouped 3-3-3-3 with spaces"),
    ("cccd_spaces_4_4_4", "Số định danh cá nhân 0012 3456 7890", True, "CCCD grouped 4-4-4 with spaces"),
    ("cccd_dashes_4_4_4", "Số định danh cá nhân 0012-3456-7890", True, "CCCD grouped 4-4-4 with dashes"),
    ("cccd_prefix_colon", "CCCD:001234567890", True, "CCCD glued with prefix and colon"),
    ("cccd_parentheses", "Số căn cước (001234567890) đính kèm", True, "CCCD inside parentheses"),
    ("cccd_bracket", "Số thẻ [001234567890] đã photo", True, "CCCD inside brackets"),
]

ADVERSARIAL_EMAILS = [
    # (id, raw_input, expected_contain_pii, description)
    ("email_standard", "Gửi phản hồi về email legal@company.vn", True, "Standard email"),
    ("email_subdomain_4_tiers", "Liên hệ qua email contact@hr.legal.corp.vn", True, "Email with 4 subdomain tiers"),
    ("email_plus_tag", "Email nhân sự: recruitment+legal.2026@domain.com", True, "Email with plus tagging"),
    ("email_angle_bracket", "Người nhận: <lawyer.nguyen@vietnam-law.org.vn>", True, "Email enclosed in angle brackets"),
    ("email_uppercase", "GỬI TÀI LIỆU VỀ HR_DIRECTOR@CORPORATION.VN", True, "Uppercase email"),
    ("email_hyphen_domain", "Hòm thư trợ giúp: helpdesk@my-company-domain.vn", True, "Email with hyphenated domain"),
]

LEGAL_AND_FINANCIAL_TEXTS = [
    # (id, raw_input, description)
    ("legal_decree_145", "Căn cứ Nghị định 145/2020/NĐ-CP hướng dẫn Bộ luật Lao động", "Decree 145/2020/NĐ-CP"),
    ("legal_decree_08", "Theo quy định tại Nghị định 08/2020/NĐ-CP về hòa giải viên", "Decree 08/2020/NĐ-CP"),
    ("legal_decree_12", "Áp dụng xử phạt theo Nghị định 12/2022/NĐ-CP", "Decree 12/2022/NĐ-CP"),
    ("legal_circular_05", "Xem hướng dẫn tại Thông tư 05/2023/TT-BLĐTBXH", "Circular 05/2023/TT-BLĐTBXH"),
    ("legal_decision_595", "Căn cứ Quyết định 595/QĐ-BHXH quy định về bảo hiểm xã hội", "Decision 595/QĐ-BHXH"),
    ("legal_law_45", "Bộ luật Lao động được ban hành theo Luật số 45/2019/QH14", "Law 45/2019/QH14"),
    ("legal_article_168", "Quy định tại Điều 168 Bộ luật Lao động 2019 về tham gia bảo hiểm", "Statute article reference"),
    ("legal_date_slash", "Bộ luật có hiệu lực thi hành từ ngày 01/01/2021", "Date formatted with slashes"),
    ("legal_date_dash", "Hợp đồng ký ngày 15-09-2026 giữa hai bên", "Date formatted with dashes"),
    ("legal_date_dot", "Kỷ niệm ngày 30.04.1975 giải phóng", "Date formatted with dots"),
    ("legal_money_million", "Mức lương tối thiểu vùng là 4.680.000 đồng/tháng", "Money: millions with dots"),
    ("legal_money_billion", "Tổng tiền bồi thường thiệt hại là 5.000.000.000 đồng", "Money: billions with dots"),
    ("legal_money_hundred_billion", "Dự án có tổng vốn đầu tư là 100.000.000.000 đồng", "Money: 100 billion with dots (12 digits)"),
    ("legal_money_plain_12_digits", "Bồi thường số tiền 100000000000 đồng cho đối tác", "Money: 100 billion plain 12 digits"),
    ("legal_percentage_overtime", "Tiền lương làm thêm giờ ít nhất bằng 150%, 200% hoặc 300%", "Overtime salary percentage"),
    ("legal_notice_period_days", "Thời hạn báo trước là 45 ngày đối với HĐLĐ không xác định thời hạn", "Notice period in days"),
]


# ============================================================================
# 2. EMPIRICAL BENCHMARK FIXTURE & EVALUATION LOGIC
# ============================================================================

def evaluate_pii_sanitization_corpus():
    """
    Evaluates sanitize_pii on all adversarial variations and returns structured statistics:
    - true_positives (redacted when should redact)
    - false_negatives (leaked when should redact - SECURITY / PRIVACY BUG)
    - false_positives (redacted when legitimate legal text - CORRUPTION BUG)
    """
    results = {
        "phones": {"passed": [], "failed": []},
        "cccd": {"passed": [], "failed": []},
        "emails": {"passed": [], "failed": []},
        "legal_invariance": {"passed": [], "failed": []}
    }

    # 1. Phone numbers
    for cid, raw, should_redact, desc in ADVERSARIAL_PHONES:
        cleaned = sanitize_pii(raw)
        has_redacted = "[REDACTED_PII]" in cleaned
        # Extract digits to check if original phone leaked
        leaked = any(c in cleaned for c in ["0912345678", "0387654321", "0771234567", "0868888888", "0523456789", "912 345 678", "234-5678", "234 5678", "345 678"])
        if has_redacted and not leaked:
            results["phones"]["passed"].append((cid, raw, cleaned, desc))
        else:
            results["phones"]["failed"].append((cid, raw, cleaned, desc))

    # 2. CCCD
    for cid, raw, should_redact, desc in ADVERSARIAL_CCCD:
        cleaned = sanitize_pii(raw)
        has_redacted = "[REDACTED_PII]" in cleaned
        leaked = any(c in cleaned for c in ["001234567890", "001.234.567.890", "001-234-567-890", "001 234 567 890", "0012 3456 7890", "0012-3456-7890"])
        if has_redacted and not leaked:
            results["cccd"]["passed"].append((cid, raw, cleaned, desc))
        else:
            results["cccd"]["failed"].append((cid, raw, cleaned, desc))

    # 3. Emails
    for cid, raw, should_redact, desc in ADVERSARIAL_EMAILS:
        cleaned = sanitize_pii(raw)
        has_redacted = "[REDACTED_PII]" in cleaned
        leaked = "@" in cleaned
        if has_redacted and not leaked:
            results["emails"]["passed"].append((cid, raw, cleaned, desc))
        else:
            results["emails"]["failed"].append((cid, raw, cleaned, desc))

    # 4. Legal text invariance
    for cid, raw, desc in LEGAL_AND_FINANCIAL_TEXTS:
        cleaned = sanitize_pii(raw)
        if "[REDACTED_PII]" in cleaned or cleaned != raw:
            results["legal_invariance"]["failed"].append((cid, raw, cleaned, desc))
        else:
            results["legal_invariance"]["passed"].append((cid, raw, cleaned, desc))

    return results


# ============================================================================
# 3. PYTEST TESTS: PII SANITIZATION
# ============================================================================

@pytest.mark.parametrize("cid,raw,should_redact,desc", ADVERSARIAL_EMAILS)
def test_adversarial_email_sanitization(cid, raw, should_redact, desc):
    """
    Emails must always be sanitized regardless of subdomains, tags, or formatting.
    """
    cleaned = sanitize_pii(raw)
    assert "[REDACTED_PII]" in cleaned, f"Email not redacted in: {raw}"
    assert "@" not in cleaned, f"Email character '@' still present in: {cleaned}"


@pytest.mark.parametrize("cid,raw,should_redact,desc", ADVERSARIAL_PHONES)
def test_all_phone_sanitization_passes(cid, raw, should_redact, desc):
    """
    All Vietnamese mobile phone variations must be successfully redacted.
    """
    cleaned = sanitize_pii(raw)
    assert "[REDACTED_PII]" in cleaned, f"Phone not redacted in: {raw}"
    assert not any(c in cleaned for c in ["0912345678", "0387654321", "0771234567", "0868888888", "0523456789", "912 345 678", "234-5678", "234 5678", "345 678"])


def test_adversarial_phone_leakage_edge_cases():
    """Verify that all tricky phone formats are cleanly redacted."""
    test_cases = ["+84 912 345 678", "+84-912-345-678", "+84.912.345.678", "(091) 234-5678", "(0912) 345 678"]
    for s in test_cases:
        cleaned = sanitize_pii(s)
        assert "[REDACTED_PII]" in cleaned
        assert not any(c in cleaned for c in ["912", "345", "678", "234", "5678"])


def test_adversarial_cccd_grouping_edge_cases():
    r"""
    VERIFIED RESOLUTION:
    CCCD grouped as 4-4-4 (common in ID cards/documents) is correctly captured.
    """
    cccd_444 = "0012 3456 7890"
    cleaned_444 = sanitize_pii(cccd_444)
    assert "[REDACTED_PII]" in cleaned_444, "CCCD 4-4-4 must be redacted"
    assert "0012 3456 7890" not in cleaned_444


def test_legal_text_false_positive_financial_hundred_billion():
    """
    VERIFIED RESOLUTION:
    Zero False Positive Mandate:
    Money amounts >= 100 billion VND (100.000.000.000 đồng) are preserved and NOT redacted.
    """
    hundred_billion = "100.000.000.000 đồng"
    cleaned = sanitize_pii(hundred_billion)
    assert "[REDACTED_PII]" not in cleaned, "100 billion VND must NOT be redacted"
    assert cleaned == hundred_billion


@pytest.mark.parametrize("cid,raw,desc", LEGAL_AND_FINANCIAL_TEXTS)
def test_legal_text_invariance_passes(cid, raw, desc):
    """
    Legal decrees, articles, dates, and typical monetary amounts
    must NEVER be altered or redacted.
    """
    cleaned = sanitize_pii(raw)
    assert cleaned == raw, f"Legal text wrongly modified in {cid}: {raw!r} -> {cleaned!r}"


# ============================================================================
# 4. PYTEST TESTS: EPISODIC CACHE RE-VERIFICATION
# ============================================================================

def test_cache_reverification_catches_fake_article_id_and_falls_back(tmp_path):
    """
    STRESS TEST 1: Cache re-verification with fake/invalid article ID.
    - An attacker or corrupt process poisons SQLite cache with 'Dieu_9999_Fake'.
    - When retrieved, L1 verifier detects non-existent article in corpus.
    - System MUST:
      1. Reject cache hit (from_cache=False)
      2. Record 'cache_verification_failed' event in audit logger
      3. Clear temporary retrieved ledger cache
      4. Fall back to live ReAct loop
    """
    db_file = str(tmp_path / "corrupt_cache.db")
    store = SQLiteEpisodicStore(db_path=db_file, index_version="v2026.1")

    query = "Thời gian thử việc của người lao động trình độ đại học?"
    fake_answer = "Thời gian thử việc tối đa là 180 ngày theo Điều 9999 Bộ luật Lao động."
    fake_citations = [{"article_id": "Dieu_9999_Fake", "law_name": "Bộ luật Lao động 2019"}]

    # Manually insert corrupted record bypassing write_if_verified
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO episodic_memory 
            (case_id, normalized_query, article_ids, answer, citations_json, index_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "corrupt_case_001",
            store.sanitize_pii(query).strip().lower(),
            "Dieu_9999_Fake",
            fake_answer,
            json.dumps(fake_citations),
            "v2026.1",
            "2026-09-15T00:00:00Z"
        ))
        conn.commit()

    agent = LuatCheckAgent(corpus_path="data/corpus/labor_code_2019.json", verification_mode="l1")
    agent.sqlite_store = store

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Offline fallback")):
        ledger = agent.run(query, session_id="test_cache_fake_article")

    # Assertions on defense behavior
    assert ledger.is_terminal is True
    # Must NOT have served answer from corrupted cache
    assert ledger.final_output.get("from_cache") is not True
    assert "Dieu_9999_Fake" not in ledger.retrieved_article_ids
    assert "Dieu_9999_Fake" not in [c.get("article_id") for c in ledger.final_output.get("citations", [])]

    # Must have fallen back to ReAct loop and executed live tools
    assert ledger.tool_calls_count >= 1
    # Check that cache verification failure was logged in audit trail
    recent_logs = agent.audit_logger.get_recent_logs(limit=50)
    has_cache_fail_log = any(
        rec.get("session_id") == "test_cache_fake_article" and rec.get("event_type") == "cache_verification_failed"
        for rec in recent_logs
    )
    assert has_cache_fail_log is True, "AuditLogger must record cache_verification_failed event"


def test_cache_version_mismatch_isolation(tmp_path):
    """
    STRESS TEST 2: Index version mismatch isolation.
    - Case stored under index_version='v2025.1'.
    - Agent running under index_version='v2026.1'.
    - Must NOT hit cache and must perform fresh ReAct query.
    """
    db_file = str(tmp_path / "version_mismatch.db")
    store_old = SQLiteEpisodicStore(db_path=db_file, index_version="v2025.1")
    store_new = SQLiteEpisodicStore(db_path=db_file, index_version="v2026.1")

    query = "Thời gian nghỉ giữa ca làm việc ban ngày?"
    answer = "Căn cứ theo Điều 109, người lao động được nghỉ ít nhất 30 phút liên tục."
    citations = [{"article_id": "Dieu_109", "law_name": "Bộ luật Lao động 2019"}]

    # Store under old version
    saved = store_old.write_if_verified("case_old_v2025", query, answer, citations, is_l1_verified=True)
    assert saved is True

    # Attempt retrieve under new version
    retrieved_new = store_new.retrieve_similar_case(query)
    assert retrieved_new is None, "Store must return None when index_version does not match"

    # Agent with new store must execute ReAct loop from scratch
    agent = LuatCheckAgent(corpus_path="data/corpus/labor_code_2019.json", verification_mode="l1")
    agent.sqlite_store = store_new

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Offline fallback")):
        ledger = agent.run(query, session_id="test_version_mismatch_exec")

    assert ledger.is_terminal is True
    assert ledger.final_output.get("from_cache") is not True
    assert ledger.tool_calls_count >= 1


def test_cache_reverification_under_l2_semantic_contradiction(tmp_path):
    """
    STRESS TEST 3: L2 semantic contradiction in cache.
    - Article ID exists (Dieu_25), passes L1 existence and provenance.
    - BUT answer content contradicts statutory law (claims 180 days probation for university graduates).
    - Under verification_mode='l1_l2', L2 semantic verifier MUST reject the cached answer.
    """
    db_file = str(tmp_path / "l2_cache_test.db")
    store = SQLiteEpisodicStore(db_path=db_file, index_version="v2026.1")

    query = "Thời gian thử việc tối đa đối với lao động chuyên môn kỹ thuật cao đẳng đại học là bao lâu?"
    contradictory_answer = (
        "Thời gian thử việc của người lao động có trình độ đại học cao đẳng "
        "kéo dài tối đa 180 ngày theo quyết định của người sử dụng lao động."
    )
    citations = [{"article_id": "Dieu_25", "law_name": "Bộ luật Lao động 2019"}]

    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO episodic_memory 
            (case_id, normalized_query, article_ids, answer, citations_json, index_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "case_l2_contradict",
            store.sanitize_pii(query).strip().lower(),
            "Dieu_25",
            contradictory_answer,
            json.dumps(citations),
            "v2026.1",
            "2026-09-15T00:00:00Z"
        ))
        conn.commit()

    agent = LuatCheckAgent(corpus_path="data/corpus/labor_code_2019.json", verification_mode="l1_l2")
    agent.sqlite_store = store

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Offline fallback")):
        ledger = agent.run(query, session_id="test_l2_cache_contradict")

    assert ledger.is_terminal is True
    # Cache hit must have been rejected because 180 days contradicts Dieu 25 (max 60 days)
    assert ledger.final_output.get("from_cache") is not True
    recent_logs = agent.audit_logger.get_recent_logs(limit=50)
    has_cache_fail = any(
        rec.get("session_id") == "test_l2_cache_contradict" and rec.get("event_type") == "cache_verification_failed"
        for rec in recent_logs
    )
    assert has_cache_fail is True, "AuditLogger must record cache_verification_failed when L2 rejects cache"


if __name__ == "__main__":
    report = evaluate_pii_sanitization_corpus()
    print("=" * 60)
    print("CHALLENGER 1 EMPIRICAL PII SANITIZATION AUDIT REPORT")
    print("=" * 60)
    for cat, data in report.items():
        pass_cnt = len(data["passed"])
        fail_cnt = len(data["failed"])
        total = pass_cnt + fail_cnt
        rate = (pass_cnt / total * 100) if total > 0 else 100.0
        print(f"{cat.upper():<20} | Passed: {pass_cnt:2d}/{total:2d} ({rate:5.1f}%) | Failed: {fail_cnt:2d}")
        for item in data["failed"]:
            print(f"   [FAIL] {item[0]}: {item[1]!r} -> {item[2]!r} ({item[3]})")
    print("=" * 60)
