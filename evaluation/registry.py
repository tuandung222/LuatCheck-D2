"""Run registry: one row per directory of evaluation/runs/, with FRESHNESS computed against the current checkout.

  python evaluation/run_d2.py registry        (or `make runs`)   ->  evaluation/runs/REGISTRY.md and registry.jsonl

Freshness answers "may a report use this run?":
  current                 same collection-source fingerprint, same harness major.minor, same benchmark locks, same pinned model identities as HEAD
  stale: <reasons>        something that can change a trial or its scoring differs -> re-run (or re-analyse for analysis-only changes); never quote it
  incomplete (<state>)    collection did not finish
  superseded_by: <run>    replaced by a newer run (metadata only; the old run stays)
  historical: <reason>    deliberately kept for the record (old benchmark / model / protocol); never in current report tables
  n/a                     not a D2-harness run (reranker parity probe etc.)
Runs are never deleted or edited by the registry. Curated marks live in evaluation/runs/registry_overrides.yaml (patterns) and in an optional
<run>/RUN_STATUS.json ({"kind": ..., "historical": "reason", "superseded_by": "run-id", "note": "..."}), which wins over the patterns.
"""
import fnmatch
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from evaluation import provenance
from evaluation import run_benchmark as rb

RUNS_DIR = Path("evaluation/runs")
OVERRIDES = RUNS_DIR / "registry_overrides.yaml"


def load_overrides() -> List[Dict[str, Any]]:
    return (yaml.safe_load(OVERRIDES.read_text(encoding="utf-8")) or {}).get("overrides", []) if OVERRIDES.is_file() else []


def override_for(name: str, run_dir: Path) -> Dict[str, Any]:
    mark: Dict[str, Any] = {}
    for item in load_overrides():
        if fnmatch.fnmatch(name, item["match"]):
            mark = {**mark, **item}
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
        if mark.get("superseded_by"):
            row["freshness"] = f"superseded_by: {mark['superseded_by']}"
        elif mark.get("kind") == "historical" or mark.get("historical"):
            row["freshness"] = f"historical: {mark.get('historical') or mark.get('reason')}"
        elif row["state"] not in ("complete", "collected"):
            row["freshness"] = f"incomplete ({row['state']})"
        else:
            reasons = stale_reasons(manifest)
            row["freshness"] = "current" if not reasons else "stale: " + "; ".join(reasons)
        if row["kind"] in ("smoke", "diagnostic"):
            row["report_eligible"] = False
            row["note"] = f"{row['kind']}: never report evidence"
        elif row["freshness"].startswith(("historical", "superseded")):
            row["note"] = ""
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


def scan(runs_dir: Path = RUNS_DIR) -> List[Dict[str, Any]]:
    return [describe(p) for p in sorted(runs_dir.iterdir()) if p.is_dir()]


def render_markdown(rows: List[Dict[str, Any]], git: Dict[str, Any]) -> str:
    counts: Dict[str, int] = {}
    for r in rows:
        key = r["freshness"].split(":")[0].split(" (")[0]
        counts[key] = counts.get(key, 0) + 1
    lines = ["# Run registry", "",
             f"Generated {provenance.local_now()} by `python evaluation/run_d2.py registry` against HEAD `{str(git.get('commit'))[:12]}` "
             f"({'dirty' if git.get('dirty_collection_paths') else 'clean'} collection paths), harness `{provenance.HARNESS_VERSION}`. Do not edit by hand: "
             "marks live in `evaluation/runs/registry_overrides.yaml` and `<run>/RUN_STATUS.json`.", "",
             "Freshness: **current** = same collection sources / harness / locks / models as HEAD; **stale** = differs, re-run before quoting; "
             "**historical** / **superseded_by** = kept for the record, never in current report tables; **incomplete**; **n/a**. "
             "Only `report_eligible = yes` AND `current` runs may feed the report (`make report-check` enforces this).", "",
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
