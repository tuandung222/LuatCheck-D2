"""Provenance of benchmark runs: harness version, git state, host, environment, and the rules for MAIN runs.

Why: results in a report must always be traceable to the code that produced them, and stale results must be detectable. A MAIN run
must start from a clean tree in all collection paths and from a commit that exists on origin; smoke / unfrozen / diagnostic runs may be
dirty but are marked and never report-eligible. Where there is no .git (a synced copy on the GPU server) the run needs a
PROVENANCE.json written by `run_d2.py stamp` on a clean, pushed checkout; it is valid only while the collection sources still hash to
the value recorded in it.

HARNESS_VERSION is bumped by hand on ANY change that can alter what a trial records or how a metric is computed (collection code,
metric definitions, judge rule/prompt, analysis, table content). Semantics: MAJOR/MINOR change -> older runs are `stale` (must be
re-run or re-analysed); PATCH = documentation/behaviour-neutral. History below.
"""
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

# 1.0.0  first D2 matrix harness (runner, judge, analysis, tables)
# 1.1.0  strict-success rule for refusals (judge_rules), baselines (closed_book / oracle), reranker chunk policy wiring, provenance + registry
# 1.2.0  protocol field (`r2-posthoc`) + recorded revision switches in the manifest and fingerprint, config/domains/** in the collection fingerprint,
#        `pinned` registry state, v3-vs-r2 comparison tables, refusal source on trial rows. Runs of 1.1.x stay valid only as `pinned` (v3) or are stale.
HARNESS_VERSION = "1.2.0"

STAMP_FILE = REPO_ROOT / "PROVENANCE.json"
# Paths whose uncommitted state invalidates a main run (everything that can change a trial or its scoring), relative to the repo root.
CLEAN_PATHS = ["src", "config", "evaluation", "data/corpus", "requirements.txt", "requirements-model-backends.txt"]
# Web/Streamlit front ends: never imported by the harness, so UI work must not invalidate or stale a benchmark run.
UI_ONLY_SOURCE_DIRS = ["src/api", "src/services", "src/ui"]
CLEAN_EXCLUDES = ["evaluation/runs", "evaluation/benchmarks/qa", *UI_ONLY_SOURCE_DIRS]   # run outputs, QA scratch and UI are not harness code
ENV_KEYS = ["RUN_ID", "RUN_PROFILE", "KIND", "MODEL_ALIAS", "MODEL_CONFIG", "MATRIX", "CUDA_VISIBLE_DEVICES", "PRISM_PORT", "PRISM_DIR", "RERANKER_PORT", "RERANKER_MODEL_DIR",
            "RERANKER_QUANT", "NP", "CTX_PER_SLOT", "MAC_CTX", "GGUF_PATH", "SKIP_JUDGE", "MAX_JUDGE_USD", "EXTRA", "KEEP_SERVERS"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def local_now() -> str:
    return datetime.now().astimezone().isoformat()


def _git(*args: str, timeout: float = 15) -> Optional[str]:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def major_minor(version: Optional[str]) -> Optional[str]:
    if not version:
        return None
    parts = str(version).split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else None


def git_info(fetch: bool = False) -> Dict[str, Any]:
    """Live git facts. `on_origin`: the commit is contained in a remote-tracking branch of origin (fetch=True refreshes them first)."""
    if _git("rev-parse", "--is-inside-work-tree") != "true":
        return {"available": False, "commit": None, "branch": None, "remote": None, "dirty_collection_paths": None, "on_origin": None}
    if fetch:
        _git("fetch", "--quiet", "origin", timeout=60)
    commit = _git("rev-parse", "HEAD")
    pathspec = [*CLEAN_PATHS, *[f":(exclude){p}" for p in CLEAN_EXCLUDES]]
    status = _git("status", "--porcelain", "--untracked-files=all", "--", *pathspec) or ""
    containing = _git("branch", "-r", "--contains", commit) if commit else None
    return {"available": True, "commit": commit, "branch": _git("rev-parse", "--abbrev-ref", "HEAD"), "remote": _git("remote", "get-url", "origin"),
            "dirty_collection_paths": [line for line in status.splitlines() if line],
            "dirty_other_tracked_changes": sum(1 for line in (_git("status", "--porcelain") or "").splitlines() if line and not line.startswith("??")),
            "on_origin": bool(containing and any(l.strip().startswith("origin/") for l in containing.splitlines())),
            "describe": _git("describe", "--always", "--abbrev=12")}


def read_stamp() -> Optional[Dict[str, Any]]:
    return json.loads(STAMP_FILE.read_text(encoding="utf-8")) if STAMP_FILE.is_file() else None


def write_stamp(collection_sha256: str, fetch: bool = True) -> Dict[str, Any]:
    """On a clean, pushed checkout: write PROVENANCE.json so a copy without .git (server 82) can start a main run."""
    git = git_info(fetch=fetch)
    problems = main_run_problems(git, collection_sha256, None)
    if problems:
        raise ValueError("cannot stamp: " + "; ".join(problems))
    stamp = {"commit": git["commit"], "branch": git["branch"], "remote": git["remote"], "on_origin": git["on_origin"], "clean_collection_paths": True,
             "collection_sha256": collection_sha256, "harness_version": HARNESS_VERSION, "stamped_at": local_now(), "stamped_on": socket.gethostname()}
    STAMP_FILE.write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
    return stamp


def main_run_problems(git: Dict[str, Any], collection_sha256: str, stamp: Optional[Dict[str, Any]]) -> List[str]:
    """Why a MAIN run may not start here (empty = fine)."""
    if git.get("available"):
        problems = []
        if git["dirty_collection_paths"]:
            problems.append(f"{len(git['dirty_collection_paths'])} uncommitted paths in collection code/config (e.g. {git['dirty_collection_paths'][0].strip()}): commit them")
        if not git["on_origin"]:
            problems.append(f"commit {str(git['commit'])[:12]} is not on origin: push it (git push origin {git['branch']})")
        return problems
    if stamp is None:
        return ["no .git here and no PROVENANCE.json: run `python evaluation/run_d2.py stamp` on the clean, pushed checkout and sync that file"]
    problems = []
    if stamp.get("collection_sha256") != collection_sha256:
        problems.append("PROVENANCE.json was stamped for different collection sources (code/config changed after stamping): re-stamp on the pushed checkout and re-sync")
    if not stamp.get("on_origin") or not stamp.get("clean_collection_paths"):
        problems.append("PROVENANCE.json does not certify a clean, pushed commit")
    if major_minor(stamp.get("harness_version")) != major_minor(HARNESS_VERSION):
        problems.append(f"PROVENANCE.json is for harness {stamp.get('harness_version')}, current {HARNESS_VERSION}")
    return problems


def run_git_record(git: Dict[str, Any], stamp: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if git.get("available"):
        return {"source": "git", "commit": git["commit"], "branch": git["branch"], "remote": git["remote"], "describe": git.get("describe"),
                "dirty": bool(git["dirty_collection_paths"]) or bool(git.get("dirty_other_tracked_changes")),
                "dirty_collection_paths": git["dirty_collection_paths"], "on_origin": git["on_origin"]}
    if stamp:
        return {"source": "PROVENANCE.json", "commit": stamp.get("commit"), "branch": stamp.get("branch"), "remote": stamp.get("remote"),
                "dirty": None, "dirty_collection_paths": None, "on_origin": stamp.get("on_origin"), "stamped_at": stamp.get("stamped_at"),
                "stamped_on": stamp.get("stamped_on"), "note": "no .git on this host; certified by PROVENANCE.json (valid only while collection sources hash to its value)"}
    return {"source": None, "commit": None, "branch": None, "remote": None, "dirty": None, "dirty_collection_paths": None, "on_origin": None}


def host_record() -> Dict[str, Any]:
    info: Dict[str, Any] = {"hostname": socket.gethostname(), "os": platform.platform(), "machine": platform.machine(), "python": sys.version.split()[0],
                            "python_executable": sys.executable}
    smi = _run(["nvidia-smi", "--query-gpu=index,name,driver_version,memory.total", "--format=csv,noheader"])
    if smi:
        info["gpus"] = smi.splitlines()
        info["cuda_visible_devices"] = os.environ.get("CUDA_VISIBLE_DEVICES")
    packages = {}
    for module in ("torch", "transformers", "sentence_transformers", "numpy", "pydantic", "requests", "yaml", "huggingface_hub"):
        try:
            packages[module] = __import__(module).__version__
        except Exception:
            pass
    try:
        import torch
        packages["torch_cuda"] = torch.version.cuda
    except Exception:
        pass
    info["packages"] = packages
    return info


def _run(cmd: List[str], timeout: float = 10) -> Optional[str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def invocation_record() -> Dict[str, Any]:
    return {"argv": list(sys.argv), "entry_script": sys.argv[0] if sys.argv else None, "cwd": os.getcwd(),
            "env": {k: os.environ[k] for k in ENV_KEYS if k in os.environ}}
