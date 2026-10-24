"""SQLite persistence for the local web UI's sessions, runs, events, and proposals."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.web_contract import make_restart_snapshot


class WebStore:
    def __init__(self, path: str, retention_days: int = 30):
        self.path = str(Path(path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        self._initialize(max(1, int(retention_days)))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def _initialize(self, retention_days: int) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS browser_sessions (
                    session_id TEXT PRIMARY KEY,
                    csrf_token TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_seen REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES browser_sessions(session_id),
                    request_key TEXT NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    pasted_document TEXT,
                    verification_mode TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    job_status TEXT NOT NULL,
                    terminal_status TEXT,
                    snapshot_json TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(session_id, request_key)
                );
                CREATE INDEX IF NOT EXISTS runs_by_session_created
                    ON runs(session_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS run_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS run_events_by_run
                    ON run_events(run_id, event_id);
                CREATE TABLE IF NOT EXISTS summary_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    session_id TEXT NOT NULL REFERENCES browser_sessions(session_id),
                    recipient TEXT NOT NULL,
                    content TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS proposals_by_logical_key
                    ON summary_proposals(session_id, idempotency_key, created_at DESC);
                """
            )
            cutoff = time.time() - retention_days * 86400
            conn.execute("DELETE FROM runs WHERE created_at < ?", (cutoff,))
            now = time.time()
            interrupted = conn.execute(
                "SELECT run_id, verification_mode FROM runs WHERE job_status IN ('queued','running')"
            ).fetchall()
            for row in interrupted:
                snapshot = make_restart_snapshot(row["verification_mode"])
                conn.execute(
                    "UPDATE runs SET job_status='finished', terminal_status='error', "
                    "snapshot_json=?, updated_at=? WHERE run_id=?",
                    (self._json(snapshot), now, row["run_id"]),
                )
            # Restarted jobs cannot resume inference. Preserve an explicit persisted event.
            for row in interrupted:
                conn.execute(
                    "INSERT INTO run_events(run_id,event_type,data_json,created_at) VALUES(?,?,?,?)",
                    (row["run_id"], "run_interrupted", "{}", time.time()),
                )
            conn.execute(
                "UPDATE summary_proposals SET status='expired', updated_at=? WHERE status IN ('pending','approved')",
                (time.time(),),
            )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def get_or_create_session(self, session_id: str, csrf_token: str) -> Dict[str, str]:
        now = time.time()
        with self._write_lock, self._connect() as conn:
            row = conn.execute(
                "SELECT session_id, csrf_token FROM browser_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO browser_sessions(session_id,csrf_token,created_at,last_seen) VALUES(?,?,?,?)",
                    (session_id, csrf_token, now, now),
                )
                return {"session_id": session_id, "csrf_token": csrf_token}
            conn.execute("UPDATE browser_sessions SET last_seen=? WHERE session_id=?", (now, session_id))
            return {"session_id": row["session_id"], "csrf_token": row["csrf_token"]}

    def create_run(
        self,
        run_id: str,
        session_id: str,
        request_key: str,
        request_sha256: str,
        query_text: str,
        pasted_document: Optional[str],
        verification_mode: str,
        config: Dict[str, Any],
    ) -> None:
        now = time.time()
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO runs(run_id,session_id,request_key,request_sha256,query_text,pasted_document,"
                "verification_mode,config_json,job_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, session_id, request_key, request_sha256, query_text, pasted_document,
                 verification_mode, self._json(config), "queued", now, now),
            )

    def find_run_by_key(self, session_id: str, request_key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE session_id=? AND request_key=?", (session_id, request_key)
            ).fetchone()
        return self._decode_run(row) if row else None

    @staticmethod
    def _decode_run(row: sqlite3.Row) -> Dict[str, Any]:
        value = dict(row)
        for key in ("config_json", "snapshot_json"):
            if value.get(key) is not None:
                value[key.removesuffix("_json")] = json.loads(value[key])
        return value

    def get_run(self, session_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE session_id=? AND run_id=?", (session_id, run_id)
            ).fetchone()
        return self._decode_run(row) if row else None

    def list_runs(self, session_id: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs WHERE session_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (session_id, limit, offset),
            ).fetchall()
        return [self._decode_run(row) for row in rows]

    def count_runs(self, session_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM runs WHERE session_id=?", (session_id,)).fetchone()
        return int(row[0])

    def update_run_status(
        self,
        run_id: str,
        job_status: str,
        terminal_status: Optional[str] = None,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "UPDATE runs SET job_status=?, terminal_status=COALESCE(?,terminal_status), "
                "snapshot_json=COALESCE(?,snapshot_json), updated_at=? WHERE run_id=?",
                (job_status, terminal_status, self._json(snapshot) if snapshot is not None else None, time.time(), run_id),
            )

    def delete_run(self, run_id: str, session_id: str) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute("DELETE FROM runs WHERE run_id=? AND session_id=?", (run_id, session_id))

    def append_event(self, run_id: str, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        created_at = time.time()
        with self._write_lock, self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO run_events(run_id,event_type,data_json,created_at) VALUES(?,?,?,?)",
                (run_id, event_type, self._json(data), created_at),
            )
            return {"id": int(cursor.lastrowid), "created_at": created_at}

    def list_events(self, run_id: str, after_event_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_id,event_type,data_json,created_at FROM run_events "
                "WHERE run_id=? AND event_id>? ORDER BY event_id LIMIT ?",
                (run_id, after_event_id, limit),
            ).fetchall()
        return [
            {"id": int(row["event_id"]), "event": row["event_type"], "data": json.loads(row["data_json"]), "created_at": row["created_at"]}
            for row in rows
        ]

    def create_proposal(self, proposal: Dict[str, Any]) -> None:
        now = time.time()
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO summary_proposals(proposal_id,run_id,session_id,recipient,content,idempotency_key,"
                "payload_hash,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (proposal["proposal_id"], proposal["run_id"], proposal["session_id"], proposal["recipient"],
                 proposal["content"], proposal["idempotency_key"], proposal["payload_hash"], "pending", now, now),
            )

    def create_or_get_proposal(
        self, proposal: Dict[str, Any],
    ) -> tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
        """Atomically return an active/completed logical proposal or insert a new attempt.

        Expired attempts are deliberately excluded so the same logical summary can be
        reviewed and approved again. The stable idempotency key still protects outbox
        writes from duplication across attempts.
        """
        now = time.time()
        with self._write_lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM summary_proposals WHERE session_id=? AND idempotency_key=? "
                "AND status IN ('pending','completed') ORDER BY created_at DESC LIMIT 1",
                (proposal["session_id"], proposal["idempotency_key"]),
            ).fetchone()
            if row is not None:
                conn.commit()
                return self._decode_proposal(row), False, None
            conn.execute(
                "INSERT INTO summary_proposals(proposal_id,run_id,session_id,recipient,content,idempotency_key,"
                "payload_hash,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (proposal["proposal_id"], proposal["run_id"], proposal["session_id"], proposal["recipient"],
                 proposal["content"], proposal["idempotency_key"], proposal["payload_hash"], "pending", now, now),
            )
            row = conn.execute(
                "SELECT * FROM summary_proposals WHERE proposal_id=?", (proposal["proposal_id"],)
            ).fetchone()
            event_created_at = time.time()
            event_cursor = conn.execute(
                "INSERT INTO run_events(run_id,event_type,data_json,created_at) VALUES(?,?,?,?)",
                (proposal["run_id"], "summary_proposal_created",
                 self._json({"proposal_id": proposal["proposal_id"]}), event_created_at),
            )
            conn.commit()
            event = {"id": int(event_cursor.lastrowid), "created_at": event_created_at}
            return self._decode_proposal(row), True, event

    def get_proposal(self, session_id: str, proposal_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM summary_proposals WHERE session_id=? AND proposal_id=?",
                (session_id, proposal_id),
            ).fetchone()
        if row is None:
            return None
        return self._decode_proposal(row)

    @staticmethod
    def _decode_proposal(row: sqlite3.Row) -> Dict[str, Any]:
        value = dict(row)
        value["result"] = json.loads(value["result_json"]) if value.get("result_json") else None
        return value

    def update_proposal(self, proposal_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> None:
        with self._write_lock, self._connect() as conn:
            conn.execute(
                "UPDATE summary_proposals SET status=?, result_json=?, updated_at=? WHERE proposal_id=?",
                (status, self._json(result) if result is not None else None, time.time(), proposal_id),
            )
