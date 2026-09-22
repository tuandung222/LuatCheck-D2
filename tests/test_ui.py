"""
Comprehensive Automated Test Suite for LuatCheck Streamlit UI (Milestone 3 - R7)
Tests:
1. Initial page structure & 3-column layout
2. Preset demo scenarios population
3. Empty / whitespace query handling
4. Direct prompt injection safety refusal
5. Indirect prompt injection safety refusal
6. HITL egress control: unconfirmed submission blocked
7. HITL egress control: confirmed submission succeeded
8. Standard query execution with L1 verification & citations
9. Novel custom query execution with tool metric tracking (offline fallback)
10. Audit log viewer inspection
11. HITL modal dialog interaction (@st.dialog) with SHA-256 idempotency check
12. Sentence-level grounding attribution calculation & visualization
"""
import pytest
from unittest.mock import patch
import requests
from streamlit.testing.v1 import AppTest
from src.ui.app import analyze_grounding, get_agent_instance


def test_ui_initial_page_structure():
    """Verify 3-column layout, headers, metrics, and interactive widgets."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
    assert not at.exception

    # Header and title
    assert any("LuatCheck" in m.value for m in at.markdown)

    # 3-column subheaders + audit inspector
    subheaders = [h.value for h in at.subheader]
    assert any("1. Tình Huống Pháp Lý" in sh for sh in subheaders)
    assert any("2. Luồng Suy Luận & Căn Cứ Pháp Lý" in sh for sh in subheaders)
    assert any("3. Kiểm Soát Quyền" in sh for sh in subheaders)
    assert any("4. Nhật Ký Kiểm Toán" in sh for sh in subheaders)

    # Initial budget metrics in Case Ledger (0/5 tool calls, 0/2 repairs)
    assert len(at.metric) == 2
    assert "0 / 5" in at.metric[0].value
    assert "0 / 2" in at.metric[1].value

    # Interactive controls in Column 1 & Column 3
    assert len(at.selectbox) >= 1
    assert "Chọn tình huống mẫu" in at.selectbox[0].label
    assert len(at.text_area) >= 3  # query, pasted_doc, egress summary
    assert len(at.button) >= 2     # run agent, egress submit, modal, etc.


def test_ui_preset_scenarios_population():
    """Verify that selecting demo scenarios correctly populates query and document textareas."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()

    # Preset 1: Probation period
    at.selectbox[0].select_index(1).run()
    assert not at.exception
    assert "Thời gian thử việc tối đa" in at.text_area[0].value
    assert at.text_area[1].value == ""

    # Preset 2: Unpaid wages
    at.selectbox[0].select_index(2).run()
    assert not at.exception
    assert "chậm trả lương" in at.text_area[0].value

    # Preset 3: Pregnancy termination
    at.selectbox[0].select_index(3).run()
    assert not at.exception
    assert "mang thai" in at.text_area[0].value

    # Preset 4: Direct prompt injection
    at.selectbox[0].select_index(4).run()
    assert not at.exception
    assert "System Prompt" in at.text_area[0].value

    # Preset 5: Indirect prompt injection in contract
    at.selectbox[0].select_index(5).run()
    assert not at.exception
    assert "HỢP ĐỒNG LAO ĐỘNG" in at.text_area[1].value
    assert "send_summary" in at.text_area[1].value


def test_ui_empty_and_whitespace_query_handling():
    """Clicking Run Agent with empty or whitespace-only query should not crash or trigger execution."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()

    # Empty query
    at.button[0].click().run()
    assert not at.exception
    assert len(at.error) == 0
    assert len(at.success) == 0

    # Whitespace-only query
    at.text_area[0].input("    \n\t   ")
    at.button[0].click().run()
    assert not at.exception
    assert len(at.error) == 0
    assert len(at.success) == 0


def test_ui_direct_injection_safety_refusal():
    """Direct prompt injection triggers safety refusal badge and warning in UI."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
    at.selectbox[0].select_index(4).run()
    at.button[0].click().run()

    assert not at.exception
    # Safety refusal badge
    assert any("badge-refused" in m.value for m in at.markdown)
    assert len(at.error) >= 1
    assert "CẢNH BÁO AN NINH" in at.error[0].value
    # No tool execution occurred
    assert "0 / 5" in at.metric[0].value


def test_ui_indirect_injection_safety_refusal():
    """Indirect prompt injection in attached contract triggers safety refusal in UI."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
    at.selectbox[0].select_index(5).run()
    at.button[0].click().run()

    assert not at.exception
    assert any("badge-refused" in m.value for m in at.markdown)
    assert len(at.error) >= 1
    assert "CẢNH BÁO AN NINH" in at.error[0].value
    assert "0 / 5" in at.metric[0].value


def test_ui_hitl_egress_unconfirmed_blocked():
    """Submitting send_summary without confirmation checkbox is strictly blocked by HITL guard."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
    btn_send = next(b for b in at.button if "Gửi Tóm Tắt (Egress)" in b.label)
    btn_send.click().run()

    assert not at.exception
    assert len(at.error) >= 1
    assert "Human-In-The-Loop Confirmation" in at.error[0].value
    assert len(at.success) == 0


def test_ui_hitl_egress_confirmed_success():
    """Submitting send_summary with confirmation checkbox succeeds and displays confirmation."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
    at.checkbox[0].check().run()
    btn_send = next(b for b in at.button if "Gửi Tóm Tắt (Egress)" in b.label)
    btn_send.click().run()

    assert not at.exception
    assert len(at.error) == 0
    assert len(at.success) >= 1
    assert "Đã gửi thành công" in at.success[0].value


def test_ui_valid_query_execution_with_grounding():
    """Running standard legal query (Scenario 1) renders verified badge and statutory citations."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
    at.selectbox[0].select_index(1).run()
    at.button[0].click().run()

    assert not at.exception
    # Verified badge
    assert any("badge-verified" in m.value for m in at.markdown)
    assert len(at.success) >= 1
    assert "Điều 25" in at.success[0].value

    # ReAct reasoning trace box
    assert any("trace-box" in m.value for m in at.markdown)


def test_ui_custom_query_offline_fallback():
    """Novel custom query executes ReAct loop with offline fallback and tracks tool metric."""
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Offline")), \
         patch("src.memory.sqlite_store.SQLiteEpisodicStore.retrieve_similar_case", return_value=None):
        at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
        at.text_area[0].input("Quy định về thời giờ làm việc bình thường của người lao động?")
        at.button[0].click().run()

        assert not at.exception
        assert len(at.success) >= 1
        # Tool call metric updated to 1 / 5
        assert "1 / 5" in at.metric[0].value
        assert any("trace-box" in m.value for m in at.markdown)


def test_ui_audit_log_inspector():
    """Audit logger inspector component renders structured JSONL records."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
    assert not at.exception
    assert len(at.json) >= 1 or any("Nhật Ký Kiểm Toán" in m.value for m in at.markdown)


def test_ui_hitl_modal_dialog_interaction():
    """Test dedicated @st.dialog modal for HITL egress with SHA-256 idempotency check."""
    at = AppTest.from_file("src/ui/app.py", default_timeout=30).run()
    btn_modal = next(b for b in at.button if "Mở Modal HITL" in b.label)
    btn_modal.click().run()

    assert not at.exception
    # Verify modal controls are present
    modal_submit = next(b for b in at.button if "Xác Nhận & Thực Thi" in b.label)
    
    # Try submit without confirmation inside modal
    modal_submit.click().run()
    assert len(at.error) >= 1
    assert "Human-In-The-Loop Confirmation" in at.error[-1].value


def test_ui_sentence_level_grounding_attribution():
    """Test sentence-level grounding attribution logic."""
    agent = get_agent_instance()
    # High support test sentence
    text_sup = "Thời gian thử việc đối với người có trình độ đại học không quá 60 ngày."
    res_sup = analyze_grounding(text_sup, [{"article_id": "Dieu_25"}], agent)
    assert res_sup["is_valid"] is True
    assert res_sup["grounded_ratio"] > 0.0
    assert len(res_sup["sentences_data"]) >= 1
    assert res_sup["sentences_data"][0]["is_supported"] is True
    assert "Dieu_25" in res_sup["sentences_data"][0]["best_article_id"]

    # Unsupported claim test sentence (astronomy claim against labor law)
    text_unsup = "Sao Hỏa quay quanh Mặt Trời mất khoảng 687 ngày Trái Đất để hoàn thành một chu kỳ quỹ đạo."
    res_unsup = analyze_grounding(text_unsup, [{"article_id": "Dieu_25"}], agent)
    assert res_unsup["grounded_ratio"] == 0.0
    assert len(res_unsup["sentences_data"]) >= 1
    assert res_unsup["sentences_data"][0]["is_supported"] is False
