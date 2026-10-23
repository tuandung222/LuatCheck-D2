"""Process-memory helpers (macOS/Linux, no third-party dependency)."""
from __future__ import annotations

import os
import resource
import subprocess
import sys
import time
from typing import List, Tuple

from .errors import MemoryLimitError


def current_rss_mb(pid: int | None = None) -> float:
    """Resident set size of a process in MB (current, not peak), via `ps`."""
    pid = os.getpid() if pid is None else pid
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True, check=False)
    text = out.stdout.strip()
    if not text:
        raise OSError(f"cannot read RSS of pid {pid}: {out.stderr.strip()!r}")
    return int(text) / 1024.0


def peak_rss_mb() -> float:
    """Peak RSS of this process in MB (ru_maxrss: bytes on macOS, kilobytes on Linux)."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024.0 * 1024.0) if sys.platform == "darwin" else raw / 1024.0


def check_rss_limit(limit_gb: float | None, where: str = "") -> float:
    """Raise MemoryLimitError if current RSS exceeds `limit_gb`; return current RSS in MB."""
    rss = current_rss_mb()
    if limit_gb is not None and rss > limit_gb * 1024.0:
        raise MemoryLimitError(
            f"process RSS {rss / 1024.0:.2f} GB exceeds the configured limit of {limit_gb:.2f} GB"
            f"{' (' + where + ')' if where else ''}; reduce batch_size/chunk size or free memory"
        )
    return rss


def other_python_processes(min_rss_gb: float) -> List[Tuple[int, float, str]]:
    """Other python processes (not this one) whose RSS is above `min_rss_gb`."""
    out = subprocess.run(["ps", "-axo", "pid=,rss=,command="], capture_output=True, text=True, check=True)
    me = os.getpid()
    heavy: List[Tuple[int, float, str]] = []
    for line in out.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid, rss_kb, cmd = int(parts[0]), int(parts[1]), parts[2]
        if pid == me or "python" not in cmd.lower():
            continue
        if rss_kb / (1024.0 * 1024.0) > min_rss_gb:
            heavy.append((pid, rss_kb / 1024.0, cmd[:160]))
    return heavy


def wait_for_quiet_machine(min_rss_gb: float = 2.0, poll_seconds: float = 30.0, timeout_seconds: float = 600.0) -> None:
    """Block while another python process uses more than `min_rss_gb`; raise MemoryLimitError on timeout."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        heavy = other_python_processes(min_rss_gb)
        if not heavy:
            return
        if time.monotonic() >= deadline:
            desc = "; ".join(f"pid {p} {rss:.0f} MB {cmd}" for p, rss, cmd in heavy)
            raise MemoryLimitError(
                f"another python process held more than {min_rss_gb} GB for {timeout_seconds:.0f}s: {desc}"
            )
        time.sleep(poll_seconds)
