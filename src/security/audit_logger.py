"""
Structured Audit Logger for LuatCheck
Ghi nhận toàn bộ vết kiểm toán (Audit Trail) định dạng JSON Lines
"""
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class AuditLogger:
    def __init__(self, log_path: str = "data/audit_log.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def log_event(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
        latency_ms: Optional[float] = None,
        token_count: Optional[int] = None
    ):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "epoch": time.time(),
            "session_id": session_id,
            "event_type": event_type,
            "latency_ms": latency_ms,
            "token_count": token_count,
            "payload": payload
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_recent_logs(self, limit: int = 50) -> list:
        if not os.path.exists(self.log_path):
            return []
        logs = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        return logs[-limit:]
