from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from src.services.web_contract import normalize_snapshot
from src.services.web_store import WebStore


def _run(store: WebStore, session_id: str, run_id: str) -> None:
    store.create_run(
        run_id=run_id,
        session_id=session_id,
        request_key=f"request-{run_id}",
        request_sha256="a" * 64,
        query_text="Câu hỏi kiểm tra khả năng phục hồi.",
        pasted_document="",
        verification_mode="lexical_grounding",
        config={"test_fixture": "persisted run record; no model output"},
    )


def _proposal(proposal_id: str, run_id: str, session_id: str, idempotency_key: str) -> dict:
    return {
        "proposal_id": proposal_id,
        "run_id": run_id,
        "session_id": session_id,
        "recipient": "review@example.invalid",
        "content": "Nội dung proposal kiểm thử storage.",
        "idempotency_key": idempotency_key,
        "payload_hash": "b" * 64,
    }


def test_restart_persists_full_error_snapshot_and_keeps_unknown_usage_null(tmp_path: Path) -> None:
    path = tmp_path / "restart.sqlite3"
    initial = WebStore(str(path))
    session_id = "local-test-session"
    initial.get_or_create_session(session_id, "local-test-csrf")
    run_id = str(uuid4())
    _run(initial, session_id, run_id)

    restarted = WebStore(str(path))
    row = restarted.get_run(session_id, run_id)

    assert row is not None
    assert row["job_status"] == "finished"
    assert row["terminal_status"] == "error"
    snapshot = row["snapshot"]
    assert snapshot["terminal_status"] == "error"
    assert snapshot["verification_mode"] == "lexical_grounding"
    assert snapshot["final_output"]["error_kind"] == "api_restart"
    assert snapshot["retrieved_article_ids"] == []
    assert snapshot["budgets"] is None
    assert snapshot["grounding"] is None
    assert snapshot["usage"] == {
        "model_call_count": None,
        "input_tokens": None,
        "output_tokens": None,
        "model_wall_ms": None,
    }
    assert snapshot["elapsed_ms"] is None


def test_old_sparse_error_snapshot_normalizes_without_fabricated_measurements() -> None:
    snapshot = normalize_snapshot(
        {
            "terminal_status": "error",
            "final_output": {
                "action": "error",
                "reason": "API khởi động lại khi tác vụ chưa hoàn tất.",
                "error_kind": "api_restart",
                "citations": [],
            },
        },
        persisted_mode="lexical_grounding",
        persisted_terminal="error",
    )

    assert snapshot is not None
    assert snapshot["retrieved_article_ids"] == []
    assert snapshot["verification_mode"] == "lexical_grounding"
    assert snapshot["usage"] is None
    assert snapshot["budgets"] is None
    assert snapshot["elapsed_ms"] is None


def test_concurrent_create_or_get_proposal_is_atomic_across_store_instances(tmp_path: Path) -> None:
    path = tmp_path / "proposal-race.sqlite3"
    bootstrap = WebStore(str(path))
    session_id = "local-test-session"
    bootstrap.get_or_create_session(session_id, "local-test-csrf")
    run_id = str(uuid4())
    _run(bootstrap, session_id, run_id)
    stores = [WebStore(str(path)) for _ in range(12)]
    idempotency_key = "c" * 64

    def create(index: int):
        return stores[index].create_or_get_proposal(
            _proposal(f"prop_{uuid4().hex}", run_id, session_id, idempotency_key)
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(create, range(12)))

    returned_ids = {proposal["proposal_id"] for proposal, _created, _event in results}
    created_count = sum(1 for _proposal_row, created, _event in results if created)
    event_count = sum(1 for _proposal_row, _created, event in results if event is not None)
    with sqlite3.connect(path) as conn:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM summary_proposals WHERE session_id=? AND idempotency_key=?",
            (session_id, idempotency_key),
        ).fetchone()[0]

    assert len(returned_ids) == 1
    assert created_count == 1
    assert event_count == 1
    assert row_count == 1


def test_expired_attempt_can_be_replaced_without_changing_logical_outbox_key(tmp_path: Path) -> None:
    path = tmp_path / "proposal-renew.sqlite3"
    store = WebStore(str(path))
    session_id = "local-test-session"
    store.get_or_create_session(session_id, "local-test-csrf")
    run_id = str(uuid4())
    _run(store, session_id, run_id)
    idempotency_key = "d" * 64
    first, first_created, _ = store.create_or_get_proposal(
        _proposal(f"prop_{uuid4().hex}", run_id, session_id, idempotency_key)
    )
    store.update_proposal(first["proposal_id"], "expired")

    second, second_created, _ = store.create_or_get_proposal(
        _proposal(f"prop_{uuid4().hex}", run_id, session_id, idempotency_key)
    )

    assert first_created is True
    assert second_created is True
    assert second["proposal_id"] != first["proposal_id"]
    assert second["idempotency_key"] == first["idempotency_key"]
    assert second["status"] == "pending"
