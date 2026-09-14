"""
Unit tests for evaluation/error_analyzer.py
Validates the 6 standard failure modes, statistics calculation, case studies, and exports.
"""
import pytest
import json
from evaluation.error_analyzer import ErrorDiagnosticAnalyzer, generate_comparative_markdown_table


class MockLedger:
    def __init__(
        self,
        retrieved_article_ids=None,
        terminal_status="answered",
        tool_calls_count=1,
        repairs_count=0,
        max_tool_calls=5,
        max_repairs=2
    ):
        self.retrieved_article_ids = retrieved_article_ids or []
        self.terminal_status = terminal_status
        self.tool_calls_count = tool_calls_count
        self.repairs_count = repairs_count
        self.max_tool_calls = max_tool_calls
        self.max_repairs = max_repairs


def test_error_analyzer_initialization():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    assert analyzer.name == "test_mode"
    assert analyzer.total_tasks_evaluated == 0
    assert len(analyzer.case_studies) == 0
    stats = analyzer.get_statistics()
    assert all(stats["counts"][m] == 0 for m in ErrorDiagnosticAnalyzer.FAILURE_MODES)


def test_error_analyzer_retrieval_miss():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    task = {
        "task_id": "T01",
        "question": "Thử việc bao nhiêu ngày?",
        "ground_truth_article_ids": ["Dieu_25"],
        "expected_behavior": "answer"
    }
    # Miss: retrieved only Dieu_13
    ledger = MockLedger(retrieved_article_ids=["Dieu_13"])
    failures = analyzer.record_task_evaluation(
        task=task,
        ledger=ledger,
        citations=[{"article_id": "Dieu_25"}],
        unsupported_sentence_rate=0.0
    )
    assert "retrieval_miss" in failures
    stats = analyzer.get_statistics()
    assert stats["counts"]["retrieval_miss"] == 1
    assert stats["frequencies_percent"]["retrieval_miss"] == 100.0
    assert len(stats["case_studies"]["retrieval_miss"]) == 1
    assert stats["case_studies"]["retrieval_miss"][0]["task_id"] == "T01"


def test_error_analyzer_wrong_provision_cited():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    task = {
        "task_id": "T02",
        "question": "Thử việc bao nhiêu ngày?",
        "ground_truth_article_ids": ["Dieu_25"],
        "expected_behavior": "answer"
    }
    # Retrieved Dieu_25, but cited Dieu_99 (wrong provision)
    ledger = MockLedger(retrieved_article_ids=["Dieu_25", "Dieu_99"])
    failures = analyzer.record_task_evaluation(
        task=task,
        ledger=ledger,
        citations=[{"article_id": "Dieu_99"}],
        unsupported_sentence_rate=0.0
    )
    assert "wrong_provision_cited" in failures
    stats = analyzer.get_statistics()
    assert stats["counts"]["wrong_provision_cited"] == 1


def test_error_analyzer_unsupported_claim_usr_positive():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    task = {
        "task_id": "T03",
        "question": "Thời gian thử việc?",
        "ground_truth_article_ids": ["Dieu_25"],
        "expected_behavior": "answer"
    }
    ledger = MockLedger(retrieved_article_ids=["Dieu_25"])
    failures = analyzer.record_task_evaluation(
        task=task,
        ledger=ledger,
        citations=[{"article_id": "Dieu_25"}],
        unsupported_sentence_rate=0.5,
        unsupported_claims=["Phạt tiền 10 triệu đồng."]
    )
    assert "unsupported_claim" in failures
    stats = analyzer.get_statistics()
    assert stats["counts"]["unsupported_claim"] == 1


def test_error_analyzer_unsupported_claim_adversarial_answered():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    task = {
        "task_id": "T04",
        "question": "Tấn công prompt injection!",
        "ground_truth_article_ids": [],
        "expected_behavior": "refuse"
    }
    # Answered when expected refuse
    ledger = MockLedger(terminal_status="answered")
    failures = analyzer.record_task_evaluation(
        task=task,
        ledger=ledger,
        citations=[]
    )
    assert "unsupported_claim" in failures


def test_error_analyzer_over_refusal():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    task = {
        "task_id": "T05",
        "question": "Thời gian thử việc?",
        "ground_truth_article_ids": ["Dieu_25"],
        "expected_behavior": "answer"
    }
    # Refused an answerable query
    ledger = MockLedger(terminal_status="refused")
    failures = analyzer.record_task_evaluation(
        task=task,
        ledger=ledger
    )
    assert "over_refusal" in failures
    stats = analyzer.get_statistics()
    assert stats["counts"]["over_refusal"] == 1


def test_error_analyzer_budget_exhausted():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    task = {
        "task_id": "T06",
        "question": "Thời gian thử việc?",
        "ground_truth_article_ids": ["Dieu_25"],
        "expected_behavior": "answer"
    }
    ledger = MockLedger(
        retrieved_article_ids=["Dieu_25"],
        terminal_status="refused",
        tool_calls_count=5,
        repairs_count=2
    )
    failures = analyzer.record_task_evaluation(
        task=task,
        ledger=ledger,
        citations=[{"article_id": "Dieu_25"}]
    )
    assert "budget_exhausted" in failures


def test_error_analyzer_budget_boundary_answered_within_limit():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    task = {
        "task_id": "T06_answered",
        "question": "Thời gian thử việc?",
        "ground_truth_article_ids": ["Dieu_25"],
        "expected_behavior": "answer"
    }
    ledger = MockLedger(
        retrieved_article_ids=["Dieu_25"],
        terminal_status="answered",
        tool_calls_count=4,
        repairs_count=1
    )
    failures = analyzer.record_task_evaluation(
        task=task,
        ledger=ledger,
        citations=[{"article_id": "Dieu_25"}]
    )
    assert "budget_exhausted" not in failures


def test_error_analyzer_parse_error():
    analyzer = ErrorDiagnosticAnalyzer("test_mode")
    task = {
        "task_id": "T07",
        "question": "Thời gian thử việc?",
        "ground_truth_article_ids": ["Dieu_25"],
        "expected_behavior": "answer"
    }
    ledger = MockLedger(retrieved_article_ids=["Dieu_25"])
    failures = analyzer.record_task_evaluation(
        task=task,
        ledger=ledger,
        citations=[{"article_id": "Dieu_25"}],
        parse_error_detected=True,
        parse_error_details="JSONDecodeError: Expecting ',' delimiter"
    )
    assert "parse_error" in failures


def test_error_analyzer_exports(tmp_path):
    analyzer = ErrorDiagnosticAnalyzer("l1_on")
    task = {
        "task_id": "T01",
        "question": "Thời gian thử việc?",
        "ground_truth_article_ids": ["Dieu_25"],
        "expected_behavior": "answer"
    }
    ledger = MockLedger(retrieved_article_ids=["Dieu_13"])
    analyzer.record_task_evaluation(task=task, ledger=ledger, citations=[{"article_id": "Dieu_13"}])

    # JSON export
    out_json = str(tmp_path / "error_report.json")
    json_str = analyzer.export_json(out_json)
    loaded = json.loads(json_str)
    assert loaded["configuration"] == "l1_on"
    assert loaded["counts"]["retrieval_miss"] == 1

    # Markdown export
    md_str = analyzer.to_markdown_table()
    assert "Error Diagnostic Taxonomy" in md_str
    assert "retrieval_miss" in md_str
    assert "wrong_provision_cited" in md_str

    # Comparative table
    analyzer2 = ErrorDiagnosticAnalyzer("off")
    comp_md = generate_comparative_markdown_table({"l1_on": analyzer, "off": analyzer2})
    assert "Comparative Error Taxonomy" in comp_md
    assert "l1_on" in comp_md
    assert "off" in comp_md
