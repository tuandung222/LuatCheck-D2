"""
Unit tests for Dual-Tier Memory System & PII Sanitization
Tests SQLiteEpisodicStore write/retrieval policies, index versioning,
and Vietnam PDPL 2025 PII sanitization (CCCD, phone, email).
"""
import pytest
import sqlite3
import json
import os
from src.memory.sqlite_store import SQLiteEpisodicStore, sanitize_pii
from src.memory.ledger import CaseLedgerManager


def test_sanitize_pii_email():
    raw_text = "Vui lòng liên hệ với tôi qua email nguyen.van.a@example.com hoặc hr_legal@company.vn."
    cleaned = sanitize_pii(raw_text)
    assert "[REDACTED_PII]" in cleaned
    assert "nguyen.van.a@example.com" not in cleaned
    assert "hr_legal@company.vn" not in cleaned


def test_sanitize_pii_phone():
    raw_text = "Số điện thoại của tôi là 0912345678, hoặc gọi +84987654321 nếu bận."
    cleaned = sanitize_pii(raw_text)
    assert "[REDACTED_PII]" in cleaned
    assert "0912345678" not in cleaned
    assert "+84987654321" not in cleaned


def test_sanitize_pii_formatted_phone():
    raw_text = "Hotline nhân sự: 0901.234.567 hoặc 0901 234 567."
    cleaned = sanitize_pii(raw_text)
    assert "0901.234.567" not in cleaned
    assert "0901 234 567" not in cleaned
    assert "[REDACTED_PII]" in cleaned


def test_sanitize_pii_cccd():
    raw_text = "Số Căn cước công dân của người lao động là 001234567890 theo hợp đồng."
    cleaned = sanitize_pii(raw_text)
    assert "001234567890" not in cleaned
    assert "[REDACTED_PII]" in cleaned


def test_sanitize_pii_clean_text_unchanged():
    legal_text = "Thời hạn báo trước khi đơn phương chấm dứt hợp đồng lao động không xác định thời hạn là 45 ngày."
    cleaned = sanitize_pii(legal_text)
    assert cleaned == legal_text


def test_sqlite_write_policy_unverified_rejected(tmp_path):
    db_file = str(tmp_path / "test_unverified.db")
    store = SQLiteEpisodicStore(db_path=db_file)

    saved = store.write_if_verified(
        case_id="case_unverified",
        query="Công ty có được giữ bằng không?",
        answer="Công ty không được giữ bằng.",
        citations=[{"article_id": "Dieu_17"}],
        is_l1_verified=False
    )
    assert saved is False

    match = store.retrieve_similar_case("Công ty có được giữ bằng không?")
    assert match is None


def test_sqlite_write_and_retrieve_with_pii_sanitization(tmp_path):
    db_file = str(tmp_path / "test_pii.db")
    store = SQLiteEpisodicStore(db_path=db_file)

    raw_query = "Tôi là Nguyễn Văn A, SĐT 0912345678, CCCD 001234567890, hỏi về thời gian thử việc đại học?"
    raw_answer = "Căn cứ Điều 25, thời gian thử việc tối đa 60 ngày. Mọi chi tiết gửi về hr@legal.vn."
    citations = [{"article_id": "Dieu_25", "law_name": "Bộ luật Lao động 2019"}]

    saved = store.write_if_verified(
        case_id="case_pii_01",
        query=raw_query,
        answer=raw_answer,
        citations=citations,
        is_l1_verified=True
    )
    assert saved is True

    # Check directly in SQLite to ensure PII was scrubbed prior to storage
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT normalized_query, answer, article_ids FROM episodic_memory WHERE case_id = 'case_pii_01'")
        row = cursor.fetchone()
        assert row is not None
        stored_q, stored_a, stored_aids = row
        assert "0912345678" not in stored_q
        assert "001234567890" not in stored_q
        assert "[redacted_pii]" in stored_q or "[REDACTED_PII]" in stored_q.upper()
        assert "hr@legal.vn" not in stored_a
        assert "[REDACTED_PII]" in stored_a

    # Retrieve using query from same user but different contact details (different phone, different CCCD)
    query_lookup = "Tôi là Nguyễn Văn A, SĐT 0987654321, CCCD 012345678901, hỏi về thời gian thử việc đại học?"
    match = store.retrieve_similar_case(query_lookup)

    assert match is not None
    assert isinstance(match["article_ids"], list)
    assert "Dieu_25" in match["article_ids"]
    assert "[REDACTED_PII]" in match["answer"]


def test_sqlite_version_matching(tmp_path):
    db_file = str(tmp_path / "test_version.db")
    store_v1 = SQLiteEpisodicStore(db_path=db_file, index_version="v2026.1")
    store_v2 = SQLiteEpisodicStore(db_path=db_file, index_version="v2026.2")

    query = "Quy định về thời giờ làm việc ban đêm?"
    answer = "Thời giờ làm việc ban đêm từ 22h đến 6h."
    citations = [{"article_id": "Dieu_106"}]

    store_v1.write_if_verified("case_v1", query, answer, citations, is_l1_verified=True)

    # v1 retrieval succeeds
    match_v1 = store_v1.retrieve_similar_case(query)
    assert match_v1 is not None

    # v2 retrieval fails due to mismatched index_version
    match_v2 = store_v2.retrieve_similar_case(query)
    assert match_v2 is None


def test_case_ledger_helper_methods():
    ledger = CaseLedgerManager.create_session("sess_01", "Hỏi về thử việc")
    
    CaseLedgerManager.add_query(ledger, "search_law: thử việc")
    assert len(ledger.queries_issued) == 1
    assert ledger.queries_issued[0] == "search_law: thử việc"

    CaseLedgerManager.add_fact(ledger, "Người lao động tốt nghiệp đại học")
    assert len(ledger.extracted_facts) == 1
    # Do not add duplicate fact
    CaseLedgerManager.add_fact(ledger, "Người lao động tốt nghiệp đại học")
    assert len(ledger.extracted_facts) == 1

    CaseLedgerManager.record_cache_hit(
        ledger,
        case_id="case_cached_99",
        article_ids=["Dieu_25"],
        articles_cache={"Dieu_25": "Nội dung Điều 25"}
    )
    assert "Dieu_25" in ledger.retrieved_article_ids
    assert ledger.retrieved_articles_cache["Dieu_25"] == "Nội dung Điều 25"
    assert any(ev["event"] == "cache_hit" for ev in ledger.audit_events)
