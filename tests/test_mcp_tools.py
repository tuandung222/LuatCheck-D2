"""
Unit tests for MCP Tools and Permissions
"""
import pytest
from src.tools.legal_tools import LegalToolRegistry


@pytest.fixture
def registry():
    return LegalToolRegistry()


def test_search_law(registry):
    res = registry.search_law("thời gian thử việc", top_k=3)
    assert res["status"] == "success"
    assert len(res["articles"]) > 0
    article_ids = [a["article_id"] for a in res["articles"]]
    assert "Dieu_25" in article_ids or "Dieu_24" in article_ids


def test_get_article(registry):
    res = registry.get_article("Dieu_35")
    assert res["status"] == "success"
    assert "đơn phương chấm dứt hợp đồng" in res["title"].lower()


def test_send_summary_requires_confirmation(registry):
    # Unconfirmed -> must be blocked
    res = registry.send_summary(
        recipient="test@example.com",
        content="Tóm tắt pháp lý",
        idempotency_key="key1",
        user_confirmed=False
    )
    assert res["status"] == "blocked_by_permission_gate"
    assert res["requires_confirmation"] is True

    # Confirmed -> success
    res_ok = registry.send_summary(
        recipient="test@example.com",
        content="Tóm tắt pháp lý",
        idempotency_key="key2",
        user_confirmed=True
    )
    assert res_ok["status"] == "success"


def test_idempotency_suppression(registry):
    # First send
    res1 = registry.send_summary(
        recipient="user@domain.com",
        content="Nội dung cần gửi",
        idempotency_key="unique_key_123",
        user_confirmed=True
    )
    assert res1["status"] == "success"

    # Resend with identical key -> must be suppressed as duplicate
    res2 = registry.send_summary(
        recipient="user@domain.com",
        content="Nội dung cần gửi",
        idempotency_key="unique_key_123",
        user_confirmed=True
    )
    assert res2["status"] == "duplicate_suppressed"
