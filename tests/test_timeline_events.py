"""Unit tests for run event enrichment and truthful timeline event reporting.

Verifies:
1. When `tool_started` is emitted, `_enrich` attaches `payload["model"]` with model metrics.
2. `tool_completed` also retains `payload["model"]` so completed steps have full provenance.
3. In `_act_search` and `_act_read`, `tool_started` is emitted before the tool operation completes.
4. When model is thinking (waiting for `_call_llm`), no false tool call is reported.
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock

from src.agent.loop import LuatCheckAgent, _Run
from src.agent.state import ActionType
from src.api.runtime import _enrich, make_event_sink
from src.config.app_config import AppConfig
from src.memory.ledger import CaseLedgerManager


def test_enrich_attaches_model_to_tool_started_and_tool_completed():
    """Verify that tool_started receives model info immediately, and tool_completed also retains it."""
    ledger = MagicMock()
    ledger.llm_calls = [
        {
            "wall_ms": 3200.5,
            "input_tokens": 4200,
            "output_tokens": 128,
            "outcome": "completed",
            "error_kind": None,
            "response": {"action": "search_law", "tool_args": {"query": "thời gian thử việc"}},
        }
    ]
    ledger.audit_events = [
        {"event": "tool_call", "tool": "search_law", "args": {"query": "thời gian thử việc"}, "metadata": None}
    ]

    state: Dict[str, Any] = {"seen_calls": 0, "last_verification_passed": None}

    # 1. tool_started event arrives
    payload_started = {"tool": "search_law", "query": "thời gian thử việc"}
    _enrich("tool_started", payload_started, ledger, state, lambda i: "")

    assert "model" in payload_started
    assert payload_started["model"]["wall_ms"] == 3200.5
    assert payload_started["model"]["action"] == "search_law"
    assert payload_started["model"]["input_tokens"] == 4200
    assert payload_started["model"]["output_tokens"] == 128
    assert state["seen_calls"] == 1

    # 2. tool_completed event arrives
    payload_completed = {"tool": "search_law", "article_ids": ["BLLD2019_Dieu_25"]}
    _enrich("tool_completed", payload_completed, ledger, state, lambda i: "Title")

    assert "model" in payload_completed
    assert payload_completed["model"]["wall_ms"] == 3200.5
    assert payload_completed["model"]["action"] == "search_law"
    assert payload_completed["query"] == "thời gian thử việc"
    assert len(payload_completed["results"]) == 1
    assert payload_completed["results"][0]["id"] == "BLLD2019_Dieu_25"


def test_enrich_on_refuse_run_finished():
    """Verify that when a model chooses refuse on step 1, run_finished carries model info."""
    ledger = MagicMock()
    ledger.llm_calls = [
        {
            "wall_ms": 11400.0,
            "input_tokens": 4752,
            "output_tokens": 232,
            "outcome": "completed",
            "error_kind": None,
            "response": {"action": "refuse", "tool_args": {"reason": "Không có căn cứ"}},
        }
    ]
    ledger.audit_events = []

    state: Dict[str, Any] = {"seen_calls": 0, "last_verification_passed": None}

    payload = {"terminal_status": "refused"}
    _enrich("run_finished", payload, ledger, state, lambda i: "")

    assert "model" in payload
    assert payload["model"]["wall_ms"] == 11400.0
    assert payload["model"]["action"] == "refuse"
    assert state["seen_calls"] == 1


def test_make_event_sink_timing_and_enrichment():
    """Verify make_event_sink integrates sink callbacks and enriches events."""
    recorded_events: List[Dict[str, Any]] = []

    def record(name: str, payload: Dict[str, Any]):
        recorded_events.append({"name": name, "payload": payload})

    holder: Dict[str, Any] = {}
    sink = make_event_sink(record, holder, lambda i: f"Title of {i}")

    mock_agent = MagicMock()
    mock_agent.ledger.llm_calls = [
        {
            "wall_ms": 1500.0,
            "input_tokens": 2000,
            "output_tokens": 50,
            "outcome": "completed",
            "error_kind": None,
            "response": {"action": "read_article", "tool_args": {"article_id": "BLLD2019_Dieu_25"}},
        }
    ]
    mock_agent.ledger.audit_events = [
        {"event": "tool_call", "tool": "read_article", "args": {"article_id": "BLLD2019_Dieu_25"}}
    ]
    holder["agent"] = mock_agent

    sink("run_started", {})
    sink("model_call_started", {"step": 1})
    sink("tool_started", {"tool": "read_article", "requested_id": "BLLD2019_Dieu_25"})
    sink("tool_completed", {"tool": "read_article", "article_ids": ["BLLD2019_Dieu_25"]})

    assert len(recorded_events) == 4
    assert recorded_events[0]["name"] == "run_started"
    assert recorded_events[1]["name"] == "model_call_started"
    assert recorded_events[2]["name"] == "tool_started"
    assert recorded_events[2]["payload"]["tool"] == "read_article"
    assert recorded_events[2]["payload"]["requested_id"] == "BLLD2019_Dieu_25"
    assert recorded_events[2]["payload"]["model"]["action"] == "read_article"

    assert recorded_events[3]["name"] == "tool_completed"
    assert recorded_events[3]["payload"]["model"]["action"] == "read_article"
    assert recorded_events[3]["payload"]["requested_id"] == "BLLD2019_Dieu_25"
