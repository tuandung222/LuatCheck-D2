"""Run registry: one row per directory of evaluation/runs/, with FRESHNESS computed against the current checkout.

  python evaluation/run_d2.py registry        (or `make runs`)   ->  evaluation/runs/REGISTRY.md and registry.jsonl

Freshness answers "may a report use this run?":
  current                 same collection-source fingerprint, same harness major.minor, same benchmark locks, same pinned model identities as HEAD
  pinned@<commit>         a deliberately FROZEN result (listed under `pinned:` in registry_overrides.yaml): the run's recorded collection fingerprint equals the
                          fingerprint of that commit's sources (hashes taken with `git show <commit>:<path>`, never from the working tree), so the result stays
                          reportable after the code moved on. Unpinned old runs keep showing `stale`. Tables must not mix pinned and current runs.
  stale: <reasons>        something that can change a trial or its scoring differs -> re-run (or re-analyse for analysis-only changes); never quote it
  incomplete (<state>)    collection did not finish
  superseded_by: <run>    replaced by a newer run (metadata only; the old run stays)
  remote/not synced       listed in registry_overrides.yaml `remote:` but its directory is not in this checkout (it lives only on server 82)
  historical: <reason>    deliberately kept for the record (old benchmark / model / protocol); never in current report tables
  n/a                     not a D2-harness run (reranker parity probe etc.)
Runs are never deleted or edited by the registry. Curated marks live in evaluation/runs/registry_overrides.yaml (patterns) and in an optional
<run>/RUN_STATUS.json ({"kind": ..., "historical": "reason", "superseded_by": "run-id", "note": "..."}), which wins over the patterns.
"""
import fnmatch
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from evaluation import provenance
from evaluation import run_benchmark as rb

RUNS_DIR = Path("evaluation/runs")
OVERRIDES = RUNS_DIR / "registry_overrides.yaml"


def _overrides_file() -> Dict[str, Any]:
    return (yaml.safe_load(OVERRIDES.read_text(encoding="utf-8")) or {}) if OVERRIDES.is_file() else {}


def load_overrides() -> List[Dict[str, Any]]:
    return _overrides_file().get("overrides", [])


def load_pins() -> Dict[str, Dict[str, Any]]:
    """run id -> {commit, reason} of the runs frozen on purpose."""
    return {item["run"]: item for item in _overrides_file().get("pinned", []) or []}


def load_remote() -> List[Dict[str, Any]]:
    """Runs that exist only on another machine (server 82): {run, superseded_by?, kind?, reason}. `run` may be a glob."""
    return _overrides_file().get("remote", []) or []


def _git_bytes(*args: str) -> Optional[bytes]:
    try:
        out = subprocess.run(["git", *args], capture_output=True, cwd=provenance.REPO_ROOT, timeout=60)
        return out.stdout if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


_BLOB_HASHES: Dict[Any, Optional[str]] = {}   # (full commit, path) -> sha256; a committed blob never changes, so caching within a process is safe


def commit_collection_hashes(commit: str, files: List[str]) -> Dict[str, Optional[str]]:
    """sha256 of every listed path AS COMMITTED at `commit` (None when the path does not exist there)."""
    out: Dict[str, Optional[str]] = {}
    for path in files:
        if (commit, path) not in _BLOB_HASHES:
            blob = _git_bytes("show", f"{commit}:{path}")
            _BLOB_HASHES[(commit, path)] = hashlib.sha256(blob).hexdigest() if blob is not None else None
        out[path] = _BLOB_HASHES[(commit, path)]
    return out


def _is_collection_source(path: str) -> bool:
    if not path.startswith("src/") or not path.endswith((".py", ".yaml", ".json")) or "__pycache__" in path:
        return False
    return not any(path.startswith(ui + "/") for ui in provenance.UI_ONLY_SOURCE_DIRS)


def pin_problems(manifest: Dict[str, Any], pin: Dict[str, Any]) -> List[str]:
    """Why a run is NOT a faithful frozen result of `pin['commit']` (empty = the recorded fingerprint equals that commit's sources)."""
    commit = str(pin["commit"])
    resolved = _git_bytes("rev-parse", "--verify", f"{commit}^{{commit}}")
    if not resolved:
        return [f"pinned commit {commit} is not available in this repository (fetch it)"]
    full = resolved.decode().strip()
    git = (manifest.get("provenance") or {}).get("git") or manifest.get("git") or {}
    recorded = str(git.get("commit") or "")
    problems: List[str] = []
    if not recorded or not (full.startswith(recorded) or recorded.startswith(full)):
        problems.append(f"the run recorded commit {recorded[:12] or 'none'}, not the pinned {full[:12]}")
    sources = manifest.get("sources") or {}
    files, recorded_hashes = sources.get("collection_files"), sources.get("files_sha256") or {}
    if not files:
        return problems + ["the run has no collection fingerprint to pin"]
    at_commit = commit_collection_hashes(full, files)
    differing = sorted(p for p in files if at_commit[p] != recorded_hashes.get(p))
    if differing:
        problems.append(f"{len(differing)} recorded collection files differ from commit {full[:7]} (e.g. {', '.join(differing[:3])})")
    tree = _git_bytes("ls-tree", "-r", "--name-only", full)
    if tree is not None:
        extra = sorted(p for p in tree.decode().splitlines() if _is_collection_source(p) and p not in set(files))
        if extra:
            problems.append(f"{len(extra)} collection sources exist at commit {full[:7]} but are not in the run's fingerprint (e.g. {', '.join(extra[:3])})")
    if not differing and sources.get("collection_sha256"):
        recomputed = hashlib.sha256(json.dumps({p: at_commit[p] for p in files}, sort_keys=True).encode("utf-8")).hexdigest()
        if recomputed != sources["collection_sha256"]:
            problems.append("the collection fingerprint recomputed from the commit differs from the recorded collection_sha256")
    return problems


def override_for(name: str, run_dir: Path) -> Dict[str, Any]:
    mark: Dict[str, Any] = {}
    for item in load_overrides():
        if fnmatch.fnmatch(name, item["match"]):
            mark = {**mark, **item}
    for item in load_remote():   # marks of runs that may also exist locally (e.g. after a sync_pull)
        if fnmatch.fnmatch(name, item["run"]):
            mark = {**mark, **{k: v for k, v in item.items() if k != "run"}}
    status = run_dir / "RUN_STATUS.json"
    if status.is_file():
        mark = {**mark, **json.loads(status.read_text(encoding="utf-8"))}
    return mark


def stale_reasons(manifest: Dict[str, Any]) -> List[str]:
    """Why a harness run no longer matches the current checkout (empty = current)."""
    reasons: List[str] = []
    recorded = manifest.get("harness_version")
    if not recorded:
        reasons.append(f"harness version not recorded (run predates {provenance.HARNESS_VERSION}; current harness is {provenance.HARNESS_VERSION})")
    elif provenance.major_minor(recorded) != provenance.major_minor(provenance.HARNESS_VERSION):
        reasons.append(f"harness {recorded} vs current {provenance.HARNESS_VERSION}")
    try:
        benchmarks = [rb.Benchmark(Path(b["tasks_path"]).parent) for b in manifest["benchmarks"]]
        model_config = Path(manifest["model_config"]["path"])
        profile_path = manifest["run_profile"].get("_path") or str(rb.discover_profiles()[manifest["run_profile"]["name"]].relative_to(rb.REPO_ROOT))
        profile = {"_path": profile_path}
        paths = rb.collection_paths(benchmarks, model_config, profile)
        now = {p: rb.sha256_file(p) for p in paths}
        sources = manifest.get("sources") or {}
        files = sources.get("files_sha256") or {}
        recorded_files = sources.get("collection_files")
        if recorded_files is None:
            reasons.append("run predates collection-source fingerprints")
        else:
            changed = sorted(p for p in recorded_files if now.get(p) != files.get(p))
            added = sorted(p for p in paths if p not in recorded_files)
            if changed or added:
                shown = (changed + added)[:4]
                reasons.append(f"{len(changed)} collection files changed, {len(added)} added since the run (e.g. {', '.join(shown)})")
        for entry in manifest["benchmarks"]:
            lock = Path("evaluation/benchmarks") / entry["name"] / "benchmark.lock.json"
            if entry.get("lock_sha256") and (not lock.is_file() or rb.sha256_file(lock) != entry["lock_sha256"]):
                reasons.append(f"benchmark lock of {entry['name']} changed")
    except Exception as exc:   # a run whose inputs can no longer be located cannot be shown to be current
        reasons.append(f"cannot recompute the collection fingerprint ({type(exc).__name__}: {exc})")
    expected = rb.EXPECTED_SERVER_CONFIG
    if expected.is_file():
        want = yaml.safe_load(expected.read_text(encoding="utf-8")) or {}
        got = ((manifest.get("fingerprint") or {}).get("must_match") or {}).get("controller_model_file_sha256")
        if got and want.get("gguf_sha256") and got != want["gguf_sha256"]:
            reasons.append("controller GGUF differs from the pinned model")
    return reasons


def describe(run_dir: Path) -> Dict[str, Any]:
    name = run_dir.name
    mark = override_for(name, run_dir)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
    harness_run = bool(manifest and manifest.get("schema") == rb.RUN_SCHEMA)
    row: Dict[str, Any] = {"run": name, "kind": mark.get("kind"), "state": None, "commit": None, "harness_version": None, "created": None,
                           "report_eligible": False, "freshness": None, "note": mark.get("reason") or mark.get("note") or ""}
    if harness_run:
        git = (manifest.get("provenance") or {}).get("git") or manifest.get("git") or {}
        summary_path = run_dir / "analysis" / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else None
        row.update(kind=mark.get("kind") or manifest.get("kind") or ("smoke" if manifest.get("phase") == "smoke" else "main"),
                   state=manifest.get("run_state") or manifest.get("status"), commit=(git.get("commit") or "")[:12] or None,
                   harness_version=manifest.get("harness_version") or "unversioned", created=manifest.get("created_at"),
                   report_eligible=bool(summary and summary.get("report_eligible") and row["kind"] != "historical"))
        row["analysed"] = bool(summary)
        row["protocol"] = manifest.get("protocol")
        if mark.get("superseded_by"):
            row["freshness"] = f"superseded_by: {mark['superseded_by']}"
        elif mark.get("kind") == "historical" or mark.get("historical"):
            row["freshness"] = f"historical: {mark.get('historical') or mark.get('reason')}"
        elif row["state"] not in ("complete", "collected"):
            row["freshness"] = f"incomplete ({row['state']})"
        elif name in load_pins():
            pin = load_pins()[name]
            problems = pin_problems(manifest, pin)
            row["freshness"] = f"pinned@{str(pin['commit'])[:7]}" if not problems else f"stale: pin {str(pin['commit'])[:7]} does not hold: " + "; ".join(problems)
            row["pinned_reason"] = pin.get("reason")
            row["note"] = row["note"] or str(pin.get("reason") or "")
        else:
            reasons = stale_reasons(manifest)
            row["freshness"] = "current" if not reasons else "stale: " + "; ".join(reasons)
        if row["kind"] in ("smoke", "diagnostic"):
            row["report_eligible"] = False
            row["note"] = f"{row['kind']}: never report evidence"
        elif row["freshness"].startswith(("historical", "superseded")):
            row["note"] = ""
        if row.get("protocol") and not row["freshness"].startswith(("historical", "superseded")):
            label = rb.protocol_label(row["protocol"])
            row["note"] = (f"protocol {row['protocol']}: {label}. " + row["note"]).strip()
    else:
        row.update(kind=mark.get("kind") or "historical", state="legacy" if manifest else "n/a")
        if mark.get("superseded_by"):
            row["freshness"] = f"superseded_by: {mark['superseded_by']}"
        elif mark.get("kind") in ("diagnostic",):
            row["freshness"] = f"n/a: {mark.get('reason', 'diagnostic outside the D2 harness')}"
        else:
            row["freshness"] = f"historical: {mark.get('reason') or 'not produced by the D2 harness (legacy run, provenance unknown)'}"
        row["note"] = ""
    return row


def remote_rows(local_names: List[str]) -> List[Dict[str, Any]]:
    """One row per `remote:` entry that has no local directory (an entry with a glob is listed once under its pattern when nothing matches it)."""
    rows = []
    for item in load_remote():
        if any(fnmatch.fnmatch(n, item["run"]) for n in local_names):
            continue
        sup = item.get("superseded_by")
        rows.append({"run": item["run"], "kind": item.get("kind") or "main", "state": "remote", "commit": None, "harness_version": None, "created": None,
                     "report_eligible": False, "analysed": False, "superseded_by": sup,
                     "freshness": "remote/not synced" + (f" (superseded_by: {sup})" if sup else ""), "note": item.get("reason") or "lives only on server 82"})
    return rows


def scan(runs_dir: Path = RUNS_DIR) -> List[Dict[str, Any]]:
    local = [p for p in sorted(runs_dir.iterdir()) if p.is_dir()]
    rows = [describe(p) for p in local] + remote_rows([p.name for p in local])
    return sorted(rows, key=lambda r: r["run"])


def render_markdown(rows: List[Dict[str, Any]], git: Dict[str, Any]) -> str:
    counts: Dict[str, int] = {}
    for r in rows:
        key = r["freshness"].split(":")[0].split(" (")[0].split("@")[0]
        counts[key] = counts.get(key, 0) + 1
    lines = ["# Run registry", "",
             f"Generated {provenance.local_now()} by `python evaluation/run_d2.py registry` against HEAD `{str(git.get('commit'))[:12]}` "
             f"({'dirty' if git.get('dirty_collection_paths') else 'clean'} collection paths), harness `{provenance.HARNESS_VERSION}`. Do not edit by hand: "
             "marks live in `evaluation/runs/registry_overrides.yaml` and `<run>/RUN_STATUS.json`.", "",
             "Freshness: **current** = same collection sources / harness / locks / models as HEAD; **stale** = differs, re-run before quoting; "
             "**pinned@commit** = a deliberately frozen result whose recorded fingerprint equals that commit's sources (reportable, but never in one table with current runs); "
             "**historical** / **superseded_by** = kept for the record, never in current report tables; **remote/not synced** = lives only on server 82; **incomplete**; **n/a**. "
             "Only `report_eligible = yes` AND `current` (or `pinned`) runs may feed the report (`make report-check` enforces this).", "",
             "Counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), "",
             "| run | kind | state | commit | harness | created | report_eligible | freshness | note |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['run']} | {r['kind']} | {r['state']} | {r['commit'] or '-'} | {r['harness_version'] or '-'} | {(r['created'] or '-')[:19]} | "
                     f"{'yes' if r['report_eligible'] else 'no'} | {r['freshness']} | {r['note']} |")
    return "\n".join(lines) + "\n"


def write_registry(runs_dir: Path = RUNS_DIR) -> List[Dict[str, Any]]:
    rows = scan(runs_dir)
    git = provenance.git_info()
    (runs_dir / "REGISTRY.md").write_text(render_markdown(rows, git), encoding="utf-8")
    with (runs_dir / "registry.jsonl").open("w", encoding="utf-8") as stream:
        for r in rows:
            stream.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def freshness_of(run_dir: Path) -> Dict[str, Any]:
    return describe(Path(run_dir))
