"""D2 benchmark runner: freeze a benchmark, then run benchmark x variant x seed trials on real native inference.

Subcommands
  freeze   mechanical checks + benchmark.lock.json (sha256 of tasks, corpus, profile, verification files)
  run      collect trials (requires --execute); refuses when the benchmark lock does not match the files
  status   show lock state and, with --run-dir, the progress of a collection

Rules (AGENTS.md): real inference only, a backend failure is an execution error row (never a substitute answer),
failed runs and rows are preserved, nothing is overwritten. Latency is reportable only for the mac-latency profile.
Run from anywhere: the working directory is switched to the repository root.

Run profiles (config/benchmark/profile_*.yaml) and variants (config/benchmark/variants.yaml) are pure configuration; the
reranker runtime of the l1_rerank variant comes from the run profile. Whole-matrix orchestration (preflight, collect,
judge, tables, notes) is evaluation/run_d2.py; this module is the collection engine.
"""
import argparse
import copy
import gc
import hashlib
import json
import os
import platform
import queue
import resource
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import requests
import yaml

if __name__ == "__main__":  # `python evaluation/run_benchmark.py`: make `import evaluation.run_benchmark` resolve to this module
    sys.modules.setdefault("evaluation.run_benchmark", sys.modules["__main__"])

BENCHMARKS_DIR = Path("evaluation/benchmarks")
VARIANTS_CONFIG = Path("config/benchmark/variants.yaml")
PROFILE_GLOB = "config/benchmark/profile_*.yaml"
EXPECTED_SERVER_CONFIG = Path("config/benchmark/expected_server.yaml")
WARMUP_CONFIG = Path("config/benchmark/warmup.yaml")
TRIALS_FILE = "trials.jsonl"
LEGACY_TRIALS_FILE = "runs.jsonl"   # runs written before the D2 batch runner used this name; still readable
DEFAULT_MODEL_CONFIG = Path("config/benchmark/model_prism_gguf2b.yaml")
DEFAULT_TRIAL_TIMEOUT_SECONDS = 300
DEFAULT_SEEDS = [42, 123, 2026]
LOCK_SCHEMA = "luatcheck.benchmark.lock.v1"
RUN_SCHEMA = "luatcheck.benchmark.run.v1"
VALID_BEHAVIORS = {"answer", "refuse"}
MODEL_ENV_OVERRIDES = ("MODEL_ENDPOINT", "OLLAMA_ENDPOINT", "MODEL_NAME", "MODEL_PROVIDER")
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
RETRYABLE_ERROR_KINDS = {"backend_error"}


def discover_profiles() -> Dict[str, Path]:
    """name -> path of every run profile (config/benchmark/profile_*.yaml). Adding a file adds a profile."""
    found: Dict[str, Path] = {}
    for path in sorted((REPO_ROOT / "config" / "benchmark").glob("profile_*.yaml")):
        name = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("name")
        if name:
            found[str(name)] = path
    return found


RUN_PROFILES = discover_profiles()


_ENV_REF = __import__("re").compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def expand_env(value: Any) -> Any:
    """`${VAR}` / `${VAR:-default}` in string values of a run profile (e.g. the local reranker weights directory). The EXPANDED profile is
    what the manifest records and what a resume compares, so a changed environment cannot silently change a run."""
    if isinstance(value, str):
        def sub(match):
            found = os.environ.get(match.group(1))
            if found:
                return found
            if match.group(2) is not None:
                return match.group(2)
            raise BenchmarkError(f"Run profile refers to ${{{match.group(1)}}} which is not set and has no default.")
        return _ENV_REF.sub(sub, value)
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    return value


def load_run_profile(name: str) -> Dict[str, Any]:
    """A registered profile name (config/benchmark/profile_*.yaml) or the path of a profile YAML file (same schema)."""
    profiles = discover_profiles()
    if name in profiles:
        path = profiles[name]
    elif Path(name).is_file():
        path = Path(name).resolve()
    else:
        raise BenchmarkError(f"Unknown run profile {name!r}; defined: {sorted(profiles)} (or give the path of a profile YAML)")
    profile = expand_env(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    for key in ("name", "latency_reportable"):
        if key not in profile:
            raise BenchmarkError(f"Run profile {path} lacks `{key}`.")
    try:
        profile["_path"] = str(path.relative_to(REPO_ROOT))
    except ValueError:
        profile["_path"] = str(path)
    return profile


def trials_path(run_dir) -> Path:
    """<run>/trials.jsonl, or the legacy <run>/runs.jsonl of runs recorded before the rename."""
    root = Path(run_dir)
    return root / TRIALS_FILE if (root / TRIALS_FILE).exists() or not (root / LEGACY_TRIALS_FILE).exists() else root / LEGACY_TRIALS_FILE


class BenchmarkError(RuntimeError):
    """Refusal to freeze or run: an integrity or configuration problem, never worked around."""


class ConfigError(BenchmarkError):
    """A variant/config cannot be honoured by the installed src/ configuration."""


# ----------------------------------------------------------------------------- helpers

def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def write_json(path, value) -> None:
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def deep_merge(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def record_id(record: Dict[str, Any]) -> str:
    return str(record.get("doc_id") or record.get("article_id") or "")


def load_corpus(corpus_path) -> Dict[str, Dict[str, Any]]:
    data = json.loads(Path(corpus_path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise BenchmarkError(f"Corpus {corpus_path} must be a JSON list of records.")
    records: Dict[str, Dict[str, Any]] = {}
    for record in data:
        rid = record_id(record)
        if not rid:
            raise BenchmarkError(f"Corpus {corpus_path} has a record without doc_id/article_id.")
        if rid in records:
            raise BenchmarkError(f"Corpus {corpus_path} has duplicate record id {rid}.")
        records[rid] = record
    return records


# ----------------------------------------------------------------------------- benchmark definition

class Benchmark:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        spec_path = self.directory / "benchmark.yaml"
        if not spec_path.is_file():
            raise BenchmarkError(f"{spec_path} not found (a benchmark directory needs benchmark.yaml).")
        self.spec_path = spec_path
        self.spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        for key in ("name", "tasks", "corpus", "profile"):
            if not self.spec.get(key):
                raise BenchmarkError(f"{spec_path}: missing '{key}'.")
        self.name = str(self.spec["name"])
        self.tasks_path = self.directory / self.spec["tasks"]
        self.corpus_path = str(self.spec["corpus"])
        self.profile_ref = str(self.spec["profile"])
        self.lock_path = self.directory / "benchmark.lock.json"

    @property
    def profile_path(self) -> Path:
        ref = self.profile_ref
        if "/" in ref or ref.endswith((".yaml", ".yml")):
            return Path(ref)
        return Path("config/domains") / f"{ref}.yaml"

    def load_tasks(self) -> List[Dict[str, Any]]:
        if not self.tasks_path.is_file():
            raise BenchmarkError(f"{self.name}: {self.tasks_path} does not exist yet; the benchmark is not ready.")
        return json.loads(self.tasks_path.read_text(encoding="utf-8"))

    def verification_files(self) -> List[Path]:
        patterns = ["verify_*.json", "recheck_*.json", "review*.json", "provenance.json", "ADJUDICATION.md",
                    "README.md", "*_BRIEF.md", "SEMANTIC_JUDGING.md", "draft_*.json"]
        found = {p for pattern in patterns for p in self.directory.glob(pattern) if p.is_file()}
        return sorted(found)


def resolve_benchmarks(refs: List[str]) -> List[Benchmark]:
    if not refs:
        raise BenchmarkError("Give --benchmark <dir> (repeatable) or 'all'.")
    directories: List[Path] = []
    for ref in refs:
        if ref == "all":
            directories += sorted(p.parent for p in BENCHMARKS_DIR.glob("*/benchmark.yaml"))
        elif Path(ref).is_dir():
            directories.append(Path(ref))
        elif (BENCHMARKS_DIR / ref).is_dir():
            directories.append(BENCHMARKS_DIR / ref)
        else:
            raise BenchmarkError(f"Benchmark {ref!r} not found (looked for a directory and {BENCHMARKS_DIR}/{ref}).")
    unique, seen = [], set()
    for directory in directories:
        key = directory.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(directory)
    return [Benchmark(d) for d in unique]


# ----------------------------------------------------------------------------- mechanical checks and lock

def check_benchmark(bm: Benchmark) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """Mechanical checks only. They do not establish that gold answers are correct (see review_status)."""
    errors: List[str] = []
    warnings: List[str] = []
    info: Dict[str, Any] = {}
    if not bm.tasks_path.is_file():
        return [f"{bm.tasks_path} does not exist"], warnings, info
    if not Path(bm.corpus_path).is_file():
        errors.append(f"corpus {bm.corpus_path} does not exist")
        return errors, warnings, info
    if not bm.profile_path.is_file():
        errors.append(f"domain profile {bm.profile_path} does not exist")
    try:
        tasks = bm.load_tasks()
        corpus = load_corpus(bm.corpus_path)
    except (BenchmarkError, json.JSONDecodeError) as exc:
        return [str(exc)], warnings, info
    if not isinstance(tasks, list) or not tasks:
        return ["tasks.json must be a nonempty JSON list"], warnings, info
    ids = [t.get("task_id") for t in tasks]
    if any(not isinstance(i, str) or not i for i in ids):
        errors.append("every task needs a nonempty string task_id")
    if len(ids) != len(set(ids)):
        errors.append("task_id values are not unique: " + ", ".join(sorted({i for i in ids if ids.count(i) > 1})))
    questions = [(t.get("question") or "").strip() for t in tasks]
    if len(questions) != len(set(questions)):
        errors.append("duplicate questions")
    categories: Dict[str, int] = {}
    behaviors: Dict[str, int] = {}
    for task in tasks:
        tid = task.get("task_id")
        for field in ("category", "question", "expected_behavior", "expected_answer", "ground_truth_article_ids"):
            if field not in task:
                errors.append(f"{tid}: missing field {field}")
        if not (task.get("question") or "").strip():
            errors.append(f"{tid}: empty question")
        behavior = task.get("expected_behavior")
        if behavior not in VALID_BEHAVIORS:
            errors.append(f"{tid}: expected_behavior must be one of {sorted(VALID_BEHAVIORS)}, got {behavior!r}")
        categories[str(task.get("category"))] = categories.get(str(task.get("category")), 0) + 1
        behaviors[str(behavior)] = behaviors.get(str(behavior), 0) + 1
        if not (task.get("expected_answer") or "").strip():
            errors.append(f"{tid}: empty expected_answer")
        gold = task.get("ground_truth_article_ids")
        if not isinstance(gold, list):
            errors.append(f"{tid}: ground_truth_article_ids must be a list")
            continue
        missing = [g for g in gold if g not in corpus]
        if missing:
            errors.append(f"{tid}: gold ids not in corpus: {missing}")
        evidence = task.get("reference_evidence") or []
        if behavior == "answer":
            if not gold:
                errors.append(f"{tid}: answer task without gold ids")
            if not evidence:
                errors.append(f"{tid}: answer task without reference_evidence")
        elif behavior == "refuse":
            if gold:
                warnings.append(f"{tid}: refuse task lists gold ids {gold}")
        quoted_ids = set()
        for item in evidence:
            aid, quote = item.get("article_id"), item.get("exact_quote")
            quoted_ids.add(aid)
            if aid not in corpus:
                errors.append(f"{tid}: evidence article {aid} not in corpus")
            elif not isinstance(quote, str) or not quote.strip():
                errors.append(f"{tid}: empty exact_quote for {aid}")
            elif quote not in corpus[aid].get("content", ""):
                errors.append(f"{tid}: exact_quote for {aid} is not a verbatim substring of the record")
        if evidence and quoted_ids != set(gold):
            errors.append(f"{tid}: reference_evidence ids {sorted(quoted_ids)} differ from gold ids {sorted(gold)}")
    # Domain profile consistency (corpus the agent will load must be the corpus the tasks were written against).
    if bm.profile_path.is_file():
        try:
            from src.domains import load_profile
            load_profile(bm.profile_ref)
            profile_raw = yaml.safe_load(bm.profile_path.read_text(encoding="utf-8")) or {}
            profile_corpus = profile_raw.get("corpus_path")
            if profile_corpus and Path(profile_corpus) != Path(bm.corpus_path):
                errors.append(f"profile corpus_path {profile_corpus} differs from benchmark corpus {bm.corpus_path}")
        except Exception as exc:  # profile failed to load: a hard error
            errors.append(f"domain profile {bm.profile_ref} does not load: {type(exc).__name__}: {exc}")
    info.update(tasks=len(tasks), corpus_records=len(corpus), categories=categories, expected_behaviors=behaviors)
    return errors, warnings, info


def compute_lock(bm: Benchmark, info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema": LOCK_SCHEMA, "benchmark": bm.name, "frozen_at": utcnow(),
        "review_status": bm.spec.get("review_status"),
        "tasks": {"path": rel(bm.tasks_path), "sha256": sha256_file(bm.tasks_path), "count": info["tasks"],
                  "categories": info["categories"], "expected_behaviors": info["expected_behaviors"]},
        "corpus": {"path": bm.corpus_path, "sha256": sha256_file(bm.corpus_path), "records": info["corpus_records"]},
        "profile": {"ref": bm.profile_ref, "path": str(bm.profile_path), "sha256": sha256_file(bm.profile_path)},
        "benchmark_yaml": {"path": rel(bm.spec_path), "sha256": sha256_file(bm.spec_path)},
        "verification_files": {rel(p): sha256_file(p) for p in bm.verification_files()},
        "mechanical_checks": "passed: unique ids, required fields, quotes verbatim in records, gold ids exist, evidence ids equal gold ids",
        "note": "Mechanical checks only; they do not certify gold answers. See review_status and the benchmark README.",
    }


def lock_hashes(lock: Dict[str, Any]) -> Dict[str, str]:
    flat = {"tasks": lock["tasks"]["sha256"], "corpus": lock["corpus"]["sha256"],
            "profile": lock["profile"]["sha256"], "benchmark_yaml": lock["benchmark_yaml"]["sha256"]}
    flat.update({f"verification:{k}": v for k, v in lock["verification_files"].items()})
    return flat


def lock_status(bm: Benchmark) -> Tuple[str, List[str]]:
    """('missing'|'ok'|'mismatch', details). Compares the stored lock with the files as they are now."""
    if not bm.lock_path.is_file():
        return "missing", [f"{rel(bm.lock_path)} does not exist; run `freeze` first"]
    lock = json.loads(bm.lock_path.read_text(encoding="utf-8"))
    problems: List[str] = []
    current = {"tasks": (bm.tasks_path, lock["tasks"]["sha256"]), "corpus": (Path(bm.corpus_path), lock["corpus"]["sha256"]),
               "profile": (bm.profile_path, lock["profile"]["sha256"]),
               "benchmark_yaml": (bm.spec_path, lock["benchmark_yaml"]["sha256"])}
    for name, (path, expected) in current.items():
        if not Path(path).is_file():
            problems.append(f"{name}: {path} is missing")
        elif sha256_file(path) != expected:
            problems.append(f"{name}: {rel(path)} changed since freeze")
    for path, expected in lock["verification_files"].items():
        if not Path(path).is_file():
            problems.append(f"verification file {path} is missing")
        elif sha256_file(path) != expected:
            problems.append(f"verification file {path} changed since freeze")
    present = {rel(p) for p in bm.verification_files()}
    for extra in sorted(present - set(lock["verification_files"])):
        problems.append(f"verification file {extra} was added after freeze")
    return ("ok" if not problems else "mismatch"), problems


def cmd_freeze(args) -> int:
    code = 0
    for bm in resolve_benchmarks(args.benchmark):
        errors, warnings, info = check_benchmark(bm)
        for warning in warnings:
            print(f"[{bm.name}] warning: {warning}")
        if errors:
            print(f"[{bm.name}] REFUSED: mechanical checks failed ({len(errors)}):")
            for error in errors:
                print(f"  - {error}")
            code = 1
            continue
        lock = compute_lock(bm, info)
        if bm.lock_path.is_file():
            old = json.loads(bm.lock_path.read_text(encoding="utf-8"))
            if lock_hashes(old) == lock_hashes(lock):
                print(f"[{bm.name}] already frozen and unchanged ({rel(bm.lock_path)})")
                continue
            if not args.refreeze:
                print(f"[{bm.name}] REFUSED: files differ from the existing lock. Re-freezing replaces the frozen "
                      "benchmark; pass --refreeze to archive the old lock and write a new one.")
                _, problems = lock_status(bm)
                for problem in problems:
                    print(f"  - {problem}")
                code = 1
                continue
            archive = bm.directory / f"benchmark.lock.superseded-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
            shutil.move(str(bm.lock_path), str(archive))
            print(f"[{bm.name}] archived previous lock to {rel(archive)}")
        write_json(bm.lock_path, lock)
        print(f"[{bm.name}] frozen: {info['tasks']} tasks, {info['corpus_records']} corpus records "
              f"-> {rel(bm.lock_path)} (tasks sha256 {lock['tasks']['sha256'][:12]})")
    return code


# ----------------------------------------------------------------------------- configuration per benchmark x variant

def load_variants(names: List[str]) -> Dict[str, Dict[str, Any]]:
    spec = yaml.safe_load(VARIANTS_CONFIG.read_text(encoding="utf-8"))["variants"]
    unknown = [n for n in names if n not in spec]
    if unknown:
        raise BenchmarkError(f"Unknown variants {unknown}; defined in {VARIANTS_CONFIG}: {sorted(spec)}")
    return {n: spec[n] for n in names}


def load_baselines(names: List[str]) -> Dict[str, Dict[str, Any]]:
    """Diagnostic baselines (evaluation/baselines.py) from variants.yaml `baselines:`; never part of the system variants."""
    spec = yaml.safe_load(VARIANTS_CONFIG.read_text(encoding="utf-8")).get("baselines") or {}
    unknown = [n for n in names if n not in spec]
    if unknown:
        raise BenchmarkError(f"Unknown baselines {unknown}; defined in {VARIANTS_CONFIG}: {sorted(spec)}")
    clash = [n for n in names if n in (yaml.safe_load(VARIANTS_CONFIG.read_text(encoding="utf-8")).get("variants") or {})]
    if clash:
        raise BenchmarkError(f"Baseline names {clash} collide with system variant names.")
    return {n: spec[n] for n in names}


def baseline_tasks(bm: "Benchmark", spec: Dict[str, Any], limit: Optional[int]) -> List[Dict[str, Any]]:
    """Tasks a baseline runs on: `all`, or `answerable` (gold ids present; refuse tasks have no gold context). --limit applies after."""
    tasks = bm.load_tasks()
    if spec.get("tasks") == "answerable":
        tasks = [t for t in tasks if t.get("expected_behavior") == "answer" and t.get("ground_truth_article_ids")]
    elif spec.get("tasks") != "all":
        raise BenchmarkError(f"baseline tasks must be 'all' or 'answerable', got {spec.get('tasks')!r}")
    return select_tasks(tasks, limit)


def variant_needs_reranker(variant_spec: Dict[str, Any]) -> bool:
    return bool((((variant_spec.get("overrides") or {}).get("retrieval") or {}).get("reranker") or {}).get("enabled"))


def effective_overrides(variant: str, variant_spec: Dict[str, Any], profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Variant overrides plus, for a reranking variant, the reranker RUNTIME (backend/model/device/dtype/base_url) taken
    from the run profile. The variant states what is compared (enabled, top_k_in/out, max_length); the profile states
    where it runs. A key given by both must agree. A reranking variant without a profile reranker block is refused."""
    overrides = copy.deepcopy(variant_spec.get("overrides") or {})
    if not variant_needs_reranker(variant_spec):
        return overrides
    runtime = (profile or {}).get("reranker")
    if not isinstance(runtime, dict) or not runtime.get("backend"):
        raise ConfigError(f"Variant {variant!r} reranks but run profile {(profile or {}).get('name')!r} defines no "
                          "`reranker:` runtime (backend/model/...); there is no default and no fallback.")
    block = overrides["retrieval"]["reranker"]
    for key, value in runtime.items():
        if value is None:
            continue
        if key in block and block[key] != value:
            raise ConfigError(f"Variant {variant!r} sets retrieval.reranker.{key}={block[key]!r} but run profile "
                              f"{profile.get('name')!r} sets {value!r}.")
        block[key] = value
    return overrides


def build_variant_config(model_config: Path, bm: Benchmark, variant: str, variant_spec: Dict[str, Any],
                         *, endpoint: Optional[str] = None, state_dir: Optional[Path] = None, tag: str = "w0",
                         profile: Optional[Dict[str, Any]] = None):
    """AppConfig for one benchmark x variant (x run profile). Raises ConfigError when src/ does not honour a requested key."""
    from src.config.app_config import AppConfig, load_config
    present = [name for name in MODEL_ENV_OVERRIDES if os.getenv(name)]
    if present:
        raise ConfigError(f"Environment overrides {present} would silently change the model; unset them for benchmark runs.")
    data = load_config(str(model_config)).model_dump()
    if endpoint:
        data["model"]["endpoint"] = endpoint
    if not isinstance(data.get("domain"), dict):
        raise ConfigError("Installed src/ has no domain.profile config key.")
    data["domain"]["profile"] = bm.profile_ref
    data["retrieval"]["corpus_path"] = bm.corpus_path
    data["verifier"]["mode"] = variant_spec["verification_mode"]
    data["memory"]["enabled"] = False
    data["memory"]["reuse_answers"] = False
    if state_dir is not None:
        state_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{bm.name}-{variant}-{tag}"
        data["memory"]["sqlite_path"] = str(state_dir / f"state-{stem}.db")
        data["security"]["audit_log_path"] = str(state_dir / f"audit-{stem}.jsonl")
        data["security"]["outbox_path"] = str(state_dir / f"outbox-{stem}.jsonl")
    overrides = effective_overrides(variant, variant_spec, profile)
    deep_merge(data, overrides)
    try:
        cfg = AppConfig.model_validate(data)
    except Exception as exc:
        raise ConfigError(f"Variant {variant!r} is not a valid configuration for the installed src/: {exc}") from exc
    _assert_honoured(cfg, overrides, path="")
    if cfg.domain.profile != bm.profile_ref:
        raise ConfigError(f"domain.profile was not applied ({cfg.domain.profile!r} != {bm.profile_ref!r}).")
    if cfg.retrieval.corpus_path != bm.corpus_path:
        raise ConfigError("retrieval.corpus_path was not applied.")
    return cfg


def _assert_honoured(obj: Any, overrides: Dict[str, Any], path: str) -> None:
    """Every requested override must be a real field with the requested value after validation (pydantic drops
    unknown keys silently; this turns that into a clear error)."""
    for key, wanted in overrides.items():
        here = f"{path}{key}"
        if not hasattr(obj, key):
            raise ConfigError(f"Config key {here} is not supported by the installed src/ yet; refusing to run this variant "
                              "(no runner-side emulation).")
        actual = getattr(obj, key)
        if isinstance(wanted, dict):
            _assert_honoured(actual, wanted, here + ".")
        elif actual != wanted:
            raise ConfigError(f"Config key {here} resolved to {actual!r}, not the requested {wanted!r}.")


# ----------------------------------------------------------------------------- environment records

def _run(cmd: List[str], timeout: float = 10) -> Optional[str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def git_state() -> Dict[str, Any]:
    status = _run(["git", "status", "--porcelain"]) or ""
    lines = [line for line in status.splitlines() if line]
    return {"commit": _run(["git", "rev-parse", "HEAD"]),
            "dirty": bool(lines),
            "tracked_changes": sum(1 for line in lines if not line.startswith("??")),
            "untracked_files": sum(1 for line in lines if line.startswith("??")),
            "note": "The sources actually used are preserved byte-for-byte in source_snapshot/; the commit alone does not describe them when dirty."}


def hardware_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {"platform": platform.platform(), "machine": platform.machine(),
                            "python": platform.python_version(), "cpu_count": os.cpu_count()}
    if sys.platform == "darwin":
        info["cpu_brand"] = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        mem = _run(["sysctl", "-n", "hw.memsize"])
        info["memory_bytes"] = int(mem) if mem and mem.isdigit() else None
        info["macos"] = _run(["sw_vers", "-productVersion"])
        info["gpu_note"] = "Apple silicon unified memory; GPU-active hours are not measured."
    else:
        cpuinfo = Path("/proc/cpuinfo")
        model = next((line.split(":", 1)[1].strip() for line in cpuinfo.read_text(errors="ignore").splitlines()
                      if line.startswith("model name")), None) if cpuinfo.is_file() else None
        info["cpu_brand"] = model or platform.processor() or None
        meminfo = Path("/proc/meminfo")
        if meminfo.is_file():
            kb = next((line.split()[1] for line in meminfo.read_text().splitlines() if line.startswith("MemTotal")), None)
            info["memory_bytes"] = int(kb) * 1024 if kb and kb.isdigit() else None
        if shutil.which("nvidia-smi"):
            info["nvidia_smi"] = _run(["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,driver_version", "--format=csv,noheader"])
        info["cuda_visible_devices"] = os.environ.get("CUDA_VISIBLE_DEVICES")
    versions = {}
    for module in ("requests", "pydantic", "numpy", "yaml", "torch", "transformers", "sentence_transformers"):
        try:
            versions[module] = __import__(module).__version__
        except Exception:
            pass
    info["packages"] = versions
    return info


def server_pid(endpoint: str) -> Optional[int]:
    """PID of a local process listening on the endpoint port, only if it is a llama-server (not an ssh forward)."""
    port = urlparse(endpoint).port
    if not port:
        return None
    out = _run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"])
    for token in (out or "").split():
        if token.isdigit():
            command = _run(["ps", "-o", "command=", "-p", token]) or ""
            if "llama-server" in command or "llama.cpp" in command:
                return int(token)
    return None


def rss_mb(pid: int) -> Optional[float]:
    out = _run(["ps", "-o", "rss=", "-p", str(pid)], timeout=3)
    return round(int(out) / 1024, 2) if out and out.strip().isdigit() else None


class MemorySampler(threading.Thread):
    """Samples RSS of this process and (if local) the llama-server every `interval` seconds."""

    def __init__(self, server_pid_value: Optional[int], interval: float = 0.5):
        super().__init__(daemon=True)
        self.pid_runner, self.pid_server, self.interval = os.getpid(), server_pid_value, interval
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self.peak = {"runner_mb": None, "server_mb": None}
        self.run_peak = {"runner_mb": None, "server_mb": None}

    @staticmethod
    def _max(a, b):
        return b if a is None else (a if b is None else max(a, b))

    def sample_once(self):
        runner = rss_mb(self.pid_runner)
        server = rss_mb(self.pid_server) if self.pid_server else None
        with self._lock:
            for target in (self.peak, self.run_peak):
                target["runner_mb"] = self._max(target["runner_mb"], runner)
                target["server_mb"] = self._max(target["server_mb"], server)

    def run(self):
        while not self._stop_event.is_set():
            self.sample_once()
            self._stop_event.wait(self.interval)

    def snapshot_and_reset(self) -> Dict[str, Optional[float]]:
        self.sample_once()
        with self._lock:
            snap = dict(self.peak)
            self.peak = {"runner_mb": None, "server_mb": None}
        return snap

    def stop(self):
        self.sample_once()
        self._stop_event.set()


def server_info(cfg, *, sha_model: bool = True) -> Dict[str, Any]:
    """Preflight: the configured llama.cpp alias is served on a loopback endpoint. No substitute is ever tried."""
    endpoint = cfg.model.endpoint.rstrip("/")
    if cfg.model.provider not in {"llamacpp", "llama.cpp", "prism", "prism_llamacpp", "prism-llamacpp", "prismml"}:
        raise BenchmarkError(f"Benchmark runs use the llamacpp provider, got {cfg.model.provider!r}.")
    if urlparse(endpoint).hostname not in LOOPBACK:
        raise BenchmarkError("The model endpoint must be loopback (use a port forward for a remote GPU server).")
    try:
        listed = requests.get(endpoint + "/models", timeout=10)
        listed.raise_for_status()
    except requests.RequestException as exc:
        raise BenchmarkError(f"Model server not reachable at {endpoint}: {type(exc).__name__}. Not started by this tool.") from exc
    body = listed.json()
    ids = {m.get("id") for m in body.get("data", [])}
    if cfg.model.name not in ids:
        raise BenchmarkError(f"Configured model {cfg.model.name!r} is not served (served: {sorted(i for i in ids if i)}). No substitute.")
    base = endpoint[:-3] if endpoint.endswith("/v1") else endpoint
    props: Dict[str, Any] = {}
    try:
        response = requests.get(base + "/props", timeout=10)
        if response.status_code == 200:
            props = response.json()
    except (requests.RequestException, ValueError):
        pass
    template = props.get("chat_template")
    path = props.get("model_path")
    digest = None
    if sha_model and path and Path(path).is_file():
        digest = sha256_file(path)
    pid = server_pid(endpoint)
    info = {
        "endpoint": endpoint, "model_alias": cfg.model.name, "models_listing": body.get("data"),
        "model_path": path, "model_file_sha256": digest,
        "model_file_sha256_note": None if digest else "GGUF file not readable from this machine (remote or unknown path); digest not recorded.",
        "build_info": props.get("build_info"), "model_ftype": props.get("model_ftype"),
        "total_slots": props.get("total_slots"),
        "n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx"),
        "server_default_sampling": (props.get("default_generation_settings") or {}).get("params"),
        "chat_template_sha256": sha256_text(template) if isinstance(template, str) else None,
        "local_server_pid": pid,
        "local_server_command": (_run(["ps", "-o", "command=", "-p", str(pid)]) if pid else None),
        "props_available": bool(props),
    }
    return info


# ----------------------------------------------------------------------------- source snapshot

SNAPSHOT_GLOBS = ("src/**/*.py", "src/**/*.yaml", "src/**/*.json", "evaluation/*.py", "evaluation/judge_prompt.txt",
                  "config/**/*.yaml", "config/**/*.yml", "config/**/*.json")
# Files that can change what a trial records. Analysis/judge/table code is snapshotted too but may be improved after
# collection without invalidating a resume.
COLLECTION_EVALUATION_FILES = ("evaluation/run_benchmark.py", "evaluation/metrics.py", "evaluation/bench_preflight.py", "evaluation/baselines.py")
COLLECTION_CONFIG_FILES = (VARIANTS_CONFIG, EXPECTED_SERVER_CONFIG, WARMUP_CONFIG)


def source_paths(benchmarks: List[Benchmark], model_config: Path) -> List[Path]:
    paths: List[Path] = []
    for pattern in SNAPSHOT_GLOBS:
        paths += [p for p in Path(".").glob(pattern) if "__pycache__" not in p.parts and p.is_file()]
    paths += [Path("requirements.txt"), Path("Makefile"), model_config]
    for bm in benchmarks:
        paths += [p for p in bm.directory.iterdir() if p.is_file() and p.stat().st_size < 8_000_000]
        paths += [Path(bm.corpus_path), bm.profile_path]
    unique = {}
    for p in paths:
        if p.is_file():
            unique[rel(p)] = p
    return [unique[k] for k in sorted(unique)]


def collection_paths(benchmarks: List[Benchmark], model_config: Path, run_profile: Dict[str, Any]) -> List[str]:
    """Relative paths whose bytes must be identical across a run and its resumes."""
    chosen: Dict[str, Path] = {}
    for pattern in ("src/**/*.py", "src/**/*.yaml", "src/**/*.json"):
        for p in Path(".").glob(pattern):
            if "__pycache__" not in p.parts and p.is_file():
                chosen[rel(p)] = p
    extra = [Path(f) for f in COLLECTION_EVALUATION_FILES] + [Path(f) for f in COLLECTION_CONFIG_FILES] + [
        Path("requirements.txt"), model_config, Path(run_profile["_path"])]
    for bm in benchmarks:
        extra += [p for p in bm.directory.iterdir() if p.is_file() and p.stat().st_size < 8_000_000]
        extra += [Path(bm.corpus_path), bm.profile_path]
    for p in extra:
        if p.is_file():
            chosen[rel(p)] = p
    return sorted(chosen)


def snapshot_sources(paths: List[Path], target: Path) -> Dict[str, str]:
    hashes = {}
    for path in paths:
        relative = rel(path)
        destination = target / "source_snapshot" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        hashes[relative] = sha256_file(destination)
        if hashes[relative] != sha256_file(path):
            raise BenchmarkError(f"Source {relative} changed while it was being snapshotted.")
    return hashes


# ----------------------------------------------------------------------------- trials

def select_tasks(tasks: List[Dict[str, Any]], limit: Optional[int]) -> List[Dict[str, Any]]:
    """--limit N: deterministic round-robin over categories (file order inside a category), so a smoke run
    covers single, multi and out-of-scope tasks instead of only the first N rows."""
    if limit is None or limit >= len(tasks):
        return list(tasks)
    order: List[str] = []
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for task in tasks:
        cat = str(task.get("category"))
        if cat not in buckets:
            buckets[cat] = []
            order.append(cat)
        buckets[cat].append(task)
    chosen: List[Dict[str, Any]] = []
    while len(chosen) < limit and any(buckets.values()):
        for cat in order:
            if buckets[cat] and len(chosen) < limit:
                chosen.append(buckets[cat].pop(0))
    keep = {t["task_id"] for t in chosen}
    return [t for t in tasks if t["task_id"] in keep]


def trial_key(row: Dict[str, Any]) -> Tuple[str, str, int, str]:
    return (row["benchmark"], row["variant"], row["seed"], row["task_id"])


def read_rows(path: Path) -> List[Dict[str, Any]]:
    """All rows of a JSONL trials file. A truncated FINAL line (the process was killed mid-write) is ignored; a malformed
    line anywhere else is corruption and raises instead of being guessed around."""
    path = Path(path)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").split("\n")
    last_content = max((i for i, line in enumerate(lines) if line.strip()), default=-1)
    rows = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            if i == last_content:
                break
            raise BenchmarkError(f"{path}: line {i + 1} is not valid JSON and is not the last line (corruption; refusing to guess): {exc}") from exc
    return rows


def repair_partial_tail(path: Path) -> Optional[str]:
    """Before appending to an existing trials file: if the last line is incomplete (killed mid-write), move that fragment to
    `<name>.partial-<time>` (kept, never deleted) and cut the file back to the last complete row. Returns the fragment path."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        return None
    data = path.read_bytes()
    if data.endswith(b"\n"):
        return None
    cut = data.rfind(b"\n") + 1
    tail = data[cut:]
    try:
        json.loads(tail.decode("utf-8"))
        with path.open("ab") as stream:   # a complete row that only lacks its newline
            stream.write(b"\n")
        return None
    except (UnicodeDecodeError, json.JSONDecodeError):
        fragment = path.with_name(path.name + f".partial-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}")
        fragment.write_bytes(tail)
        with path.open("r+b") as stream:
            stream.truncate(cut)
        return str(fragment)


def latest_by_key(rows: List[Dict[str, Any]]) -> Dict[Tuple, Dict[str, Any]]:
    latest: Dict[Tuple, Dict[str, Any]] = {}
    for row in rows:
        key = trial_key(row)
        if key not in latest or row.get("attempt", 1) >= latest[key].get("attempt", 1):
            latest[key] = row
    return latest


class RowWriter:
    def __init__(self, path: Path):
        self.path, self._lock = path, threading.Lock()

    def append(self, row: Dict[str, Any]) -> None:
        line = json.dumps(row, ensure_ascii=False) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line)
                stream.flush()
                os.fsync(stream.fileno())


def per_call_summary(calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = []
    for call in calls:
        response = call.get("native_response") or {}
        timings = response.get("timings") or {}
        summary.append({"wall_ms": call.get("wall_ms"), "outcome": call.get("outcome"), "error_kind": call.get("error_kind"),
                        "input_tokens": call.get("input_tokens"), "output_tokens": call.get("output_tokens"),
                        "server_prompt_ms": timings.get("prompt_ms"), "server_predicted_ms": timings.get("predicted_ms"),
                        "server_prompt_n": timings.get("prompt_n"), "server_cache_n": timings.get("cache_n"),
                        "server_predicted_n": timings.get("predicted_n")})
    return summary


def execute_trial(agent, bm_name: str, variant: str, verification_mode: str, task: Dict[str, Any], seed: int,
                  *, run_profile: str, latency_reportable: bool, worker: int, attempt: int,
                  sampler: Optional[MemorySampler], provider: str,
                  timeout_seconds: float = DEFAULT_TRIAL_TIMEOUT_SECONDS, warmup: bool = False, kind: str = "system") -> Dict[str, Any]:
    from evaluation.metrics import calculate_citation_metrics, calculate_retrieval_metrics, calculate_unsupported_rate
    from src.agent.state import CaseLedger
    session = f"{bm_name}-{variant}-s{seed}-{task['task_id']}-a{attempt}"
    agent.llm_client.seed = seed
    started_at = utcnow()
    if sampler:
        sampler.snapshot_and_reset()
    before = time.monotonic()
    runner_exception = None
    runner_error_kind = None
    box: Dict[str, Any] = {}

    def target():
        try:
            if getattr(agent, "uses_gold", False):   # ONLY the oracle baseline (evaluation/baselines.py) is given gold, by design
                agent.prepare_trial(task)
            box["ledger"] = agent.run(task["question"], pasted_doc=task.get("pasted_doc"), session_id=session)
        except BaseException as exc:  # preserved as an execution error row; never replaced by an answer
            box["exc"] = exc

    # The agent enforces its own wall-clock budget; this watchdog only guards a hang the agent cannot see (a stuck
    # reranker call, a blocked socket). The abandoned thread is a daemon and the caller discards the agent.
    thread = threading.Thread(target=target, daemon=True, name=f"trial-{session}")
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        runner_exception = f"TrialTimeout: no result after {timeout_seconds:.0f}s (agent thread abandoned)"
        runner_error_kind = "runner_trial_timeout"
    elif "exc" in box:
        runner_exception = f"{type(box['exc']).__name__}: {box['exc']}"
        runner_error_kind = "runner_exception"
    if runner_exception:
        try:
            ledger = agent.ledger.model_copy(deep=True) if agent.ledger else CaseLedger(session_id=session, original_query=task["question"])
        except Exception:
            ledger = CaseLedger(session_id=session, original_query=task["question"])
        ledger.is_terminal, ledger.terminal_status = True, "error"
        ledger.final_output = {"action": "error", "reason": runner_exception, "error_kind": runner_error_kind,
                               "citations": [], "verified": False}
    else:
        ledger = box["ledger"]
    wall_ms = round((time.monotonic() - before) * 1000, 3)
    memory = sampler.snapshot_and_reset() if sampler else {"runner_mb": None, "server_mb": None}
    calls = ledger.llm_calls
    final = ledger.final_output or {}
    success_calls = sum(c.get("outcome") == "success" for c in calls)
    genuine = bool(calls) and all(c.get("backend") == "llamacpp" for c in calls)
    policy_refusal = (not calls and ledger.terminal_status == "refused" and final.get("pre_model_policy_refusal") is True)
    status = ledger.terminal_status
    error_kind = final.get("error_kind")
    integrity = None
    if status == "answered" and (not genuine or not success_calls):
        integrity = "answer without successful native inference is ineligible"
        status, error_kind = "error", "integrity_no_native_inference"
    if status is None:
        status, error_kind = "error", error_kind or "no_terminal_status"
    system_error = status == "error"
    tokens_complete = policy_refusal or (bool(calls) and all(
        isinstance(c.get(k), int) and not isinstance(c.get(k), bool) for c in calls for k in ("input_tokens", "output_tokens")))
    citations = final.get("citations", [])
    ids = [c["article_id"] for c in citations if isinstance(c, dict) and "article_id" in c]
    gold = task.get("ground_truth_article_ids", [])
    model_ms = sum(c.get("wall_ms") or 0 for c in calls)
    unsupported = (calculate_unsupported_rate(final.get("content", ""), citations, agent.verifier, ledger.retrieved_article_ids)
                   if status == "answered" else None)
    return {
        "benchmark": bm_name, "variant": variant, "kind": kind, "verification_mode": verification_mode, "mode": variant,
        "task_id": task["task_id"], "category": task.get("category"), "seed": seed, "attempt": attempt, "warmup": warmup,
        "expected_behavior": task["expected_behavior"], "terminal_status": status, "gold_article_ids": gold,
        "system_error": system_error, "error_kind": error_kind if system_error else None,
        "error_message": (final.get("reason") if system_error else None), "runner_exception": runner_exception,
        "integrity_violation": integrity, "pre_model_policy_refusal": policy_refusal,
        "native_calls": len(calls), "successful_native_calls": success_calls,
        "started_at": started_at, "wall_ms": wall_ms, "model_call_wall_ms": round(model_ms, 3),
        "non_model_wall_ms": round(wall_ms - model_ms, 3), "calls": per_call_summary(calls),
        "token_usage_complete": tokens_complete,
        "input_tokens": sum(c["input_tokens"] for c in calls) if tokens_complete and calls else (0 if tokens_complete else None),
        "output_tokens": sum(c["output_tokens"] for c in calls) if tokens_complete and calls else (0 if tokens_complete else None),
        "retrieval": calculate_retrieval_metrics(ledger.retrieved_article_ids, gold),
        "citation": calculate_citation_metrics(ids, gold),
        "lexical_unsupported_proxy": unsupported,
        "lexical_unsupported_proxy_note": "Lexical proxy from the agent's L1 verifier; not answer correctness.",
        "run_profile": run_profile, "latency_reportable": latency_reportable, "worker": worker,
        "trial_timeout_seconds": timeout_seconds,
        "peak_memory_mb": memory if sampler else None, "provider": provider,
        "human_task_correct": None, "human_unsupported_claims": None,
        "ledger": ledger.model_dump(),
    }


def _probe_health(base: Optional[str], timeout: float = 3.0) -> Optional[bool]:
    if not base:
        return None
    try:
        return requests.get(base.rstrip("/") + "/health", timeout=timeout).status_code == 200
    except requests.RequestException:
        return False


def diagnose_error(row: Dict[str, Any], controller_base: Optional[str], reranker_base: Optional[str]) -> Dict[str, Any]:
    """Which dependency failed, and was it still healthy right after the failure? Recorded on the row (the row's own
    error_kind/message are never altered). An HTTP-level rejection while the server is healthy (e.g. HTTP 400 for a prompt
    that exceeds the per-slot context) is a property of that trial, not an outage: it is neither retried nor counted
    toward the consecutive-outage stop."""
    import re
    component = "controller"
    for event in (row["ledger"].get("audit_events") or []):
        if (event.get("error") or {}).get("type") == "ModelComponentError":
            component = "model_component"
    if row.get("error_kind") == "runner_trial_timeout":
        component = "runner"
    base = reranker_base if component == "model_component" else controller_base
    match = re.search(r"HTTP (\d{3})", str(row.get("error_message") or ""))
    return {"component": component, "dependency_healthy_after_error": _probe_health(base),
            "probed": (base.rstrip("/") + "/health") if base else None, "http_status": int(match.group(1)) if match else None}


def is_outage(row: Dict[str, Any]) -> bool:
    """A backend_error that looks like the dependency being down (or a legacy row without a diagnosis)."""
    if not (row["system_error"] and row.get("error_kind") in RETRYABLE_ERROR_KINDS):
        return False
    diagnosis = row.get("error_diagnosis")
    return diagnosis is None or diagnosis.get("dependency_healthy_after_error") is False


class RunContext:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.abort = threading.Event()
        self.failure: Optional[BaseException] = None
        self.consecutive_outages = 0
        self.counter_lock = threading.Lock()
        self.completed = 0
        self.errors = 0
        self.started = time.monotonic()
        self.signal_received: Optional[int] = None


def write_progress(ctx: RunContext, last: str) -> None:
    elapsed = time.monotonic() - ctx.started
    rate = ctx.completed / elapsed if elapsed > 0 and ctx.completed else None
    data = {"updated_at": utcnow(), "completed_this_session": ctx.completed, "to_run_this_session": ctx.total,
            "execution_errors_this_session": ctx.errors, "elapsed_s": round(elapsed, 1),
            "eta_s": round((ctx.total - ctx.completed) / rate, 0) if rate else None,
            "trials_per_minute": round(rate * 60, 2) if rate else None, "workers": ctx.workers, "last": last}
    tmp = ctx.output / "progress.json.tmp"
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, ctx.output / "progress.json")


def load_warmup_questions() -> Dict[str, List[str]]:
    if not WARMUP_CONFIG.is_file():
        return {}
    return (yaml.safe_load(WARMUP_CONFIG.read_text(encoding="utf-8")) or {}).get("questions") or {}


def warm_up(agent, bm: Benchmark, variant: str, wid: int, ctx: RunContext) -> None:
    """Un-scored trials on questions that are NOT benchmark tasks (config/benchmark/warmup.yaml), run once per new agent
    before its first recorded trial: loads the retrieval index, the reranker weights and the server's compute/prompt cache.
    Rows go to warmup.jsonl (kept, flagged warmup=true) and never into the trials file or any metric."""
    count = int(ctx.profile.get("warmup_trials") or 0)
    if count <= 0:
        return
    questions = (ctx.warmup_questions.get(bm.name) or [])[:count]
    if len(questions) < count:
        raise BenchmarkError(f"Run profile asks for {count} warm-up trials but {WARMUP_CONFIG} has {len(questions)} for {bm.name}.")
    for index, question in enumerate(questions):
        task = {"task_id": f"WARMUP-{index + 1}", "category": "warmup", "question": question, "expected_behavior": "answer",
                "ground_truth_article_ids": []}
        row = execute_trial(agent, bm.name, variant, ctx.variants[variant]["verification_mode"], task, 0,
                            run_profile=ctx.profile["name"], latency_reportable=False, worker=wid, attempt=1, sampler=None,
                            provider="llamacpp", timeout_seconds=ctx.trial_timeout, warmup=True, kind=ctx.variants[variant].get("kind", "system"))
        ctx.warmup_writer.append(row)


def worker_loop(wid: int, work: "queue.Queue", ctx: RunContext) -> None:
    from src.agent.llm_client import LlamaCppLLMClient
    from src.agent.loop import LuatCheckAgent
    agents: Dict[Tuple[str, str], Any] = {}
    try:
        while not ctx.abort.is_set():
            try:
                bm, variant, seed, task, attempt = work.get_nowait()
            except queue.Empty:
                return
            key = (bm.name, variant)
            if key not in agents:
                # Work is ordered benchmark-major: drop agents (and their reranker weights) of finished benchmarks.
                for stale in [k for k in agents if k[0] != bm.name]:
                    del agents[stale]
                gc.collect()
                changed = [p for p, h in ctx.collection_hashes.items() if sha256_file(p) != h]
                if changed:   # config files (domain profile, prompts, corpus) are read when an agent is built: never mix two versions in one run
                    raise BenchmarkError(f"Collection sources changed while the run was in progress ({len(changed)} files, e.g. {changed[0]}); "
                                         "stopping before building a new agent. Start a new run directory (rows so far are kept).")
                cfg = build_variant_config(ctx.model_config, bm, variant, ctx.variants[variant], endpoint=ctx.endpoint,
                                           state_dir=ctx.output / "state", tag=f"w{wid}", profile=ctx.profile)
                spec = ctx.variants[variant]
                if spec.get("kind") in ("closed_book", "oracle"):
                    from evaluation.baselines import build_baseline_agent
                    agent = build_baseline_agent(cfg, spec)
                else:
                    agent = LuatCheckAgent(config=cfg, verification_mode=spec["verification_mode"], l2_use_slm=False)
                if type(agent.llm_client) is not LlamaCppLLMClient:
                    raise TypeError("The configured real llama.cpp inference client is required for collection.")
                agents[key] = agent
                warm_up(agent, bm, variant, wid, ctx)
            row = execute_trial(agents[key], bm.name, variant, ctx.variants[variant]["verification_mode"], task, seed,
                                run_profile=ctx.profile["name"], latency_reportable=ctx.profile["latency_reportable"],
                                worker=wid, attempt=attempt, sampler=ctx.sampler if ctx.workers == 1 else None,
                                provider="llamacpp", timeout_seconds=ctx.trial_timeout, kind=ctx.variants[variant].get("kind", "system"))
            if row["system_error"]:
                row["error_diagnosis"] = diagnose_error(row, ctx.controller_base, ctx.reranker_base)
            if row.get("error_kind") == "runner_trial_timeout":
                agents.pop(key, None)  # its thread may still be running inside this agent: never reuse it
            ctx.writer.append(row)
            with ctx.counter_lock:
                ctx.completed += 1
                ctx.errors += bool(row["system_error"])
                if is_outage(row):
                    ctx.consecutive_outages += 1
                elif not row["system_error"]:
                    ctx.consecutive_outages = 0
                too_many = ctx.consecutive_outages >= ctx.max_backend_errors
                print(f"[{ctx.completed}/{ctx.total}] {bm.name} {variant} s{seed} {task['task_id']} -> {row['terminal_status']}"
                      f"{' (' + str(row['error_kind']) + ')' if row['system_error'] else ''} {row['wall_ms'] / 1000:.1f}s w{wid}",
                      flush=True)
                write_progress(ctx, f"{bm.name}/{variant}/s{seed}/{task['task_id']}")
            if too_many:
                raise BenchmarkError(f"{ctx.max_backend_errors} consecutive trials failed while their dependency was down "
                                     "(controller or reranker server not answering /health): collection stopped. "
                                     "Rows are retained; restart the server and resume with the same command (--resume --retry-errors).")
    except BaseException as exc:
        ctx.failure = ctx.failure or exc
        ctx.abort.set()


def plan_work(benchmarks: List[Benchmark], variants: List[str], seeds: List[int], limit: Optional[int],
              existing: Dict[Tuple, Dict[str, Any]], retry_errors: bool, baselines: Optional[Dict[str, Dict[str, Any]]] = None):
    """Deterministic order: benchmark, seed, task, with the variant order alternating per task (as run_eval does)."""
    items = []
    planned = 0
    task_ids: Dict[str, List[str]] = {}
    baseline_ids: Dict[str, Dict[str, List[str]]] = {name: {} for name in (baselines or {})}
    for bm in benchmarks:
        tasks = select_tasks(bm.load_tasks(), limit)
        task_ids[bm.name] = [t["task_id"] for t in tasks]
        for seed in seeds:
            for index, task in enumerate(tasks):
                order = variants if index % 2 == 0 else list(reversed(variants))
                for variant in order:
                    planned += 1
                    key = (bm.name, variant, seed, task["task_id"])
                    prior = existing.get(key)
                    if prior is None:
                        items.append((bm, variant, seed, task, 1))
                    elif retry_errors and is_outage(prior):
                        items.append((bm, variant, seed, task, prior.get("attempt", 1) + 1))
        # Diagnostic baselines after the system matrix of this benchmark: their own seeds and task subset.
        for name, spec in (baselines or {}).items():
            chosen = baseline_tasks(bm, spec, limit)
            baseline_ids[name][bm.name] = [t["task_id"] for t in chosen]
            for seed in spec["seeds"]:
                for task in chosen:
                    planned += 1
                    key = (bm.name, name, seed, task["task_id"])
                    prior = existing.get(key)
                    if prior is None:
                        items.append((bm, name, seed, task, 1))
                    elif retry_errors and is_outage(prior):
                        items.append((bm, name, seed, task, prior.get("attempt", 1) + 1))
    return items, planned, task_ids, baseline_ids


# ----------------------------------------------------------------------------- plan resolution, fingerprint

def parse_workers(value) -> Optional[Any]:
    if value is None:
        return None
    if str(value).lower() == "auto":
        return "auto"
    if not str(value).isdigit() or int(value) < 1:
        raise BenchmarkError("--workers must be a positive integer or 'auto'.")
    return int(value)


def resolve_plan(args) -> Dict[str, Any]:
    """Everything a run needs, validated, before any server is contacted (except `workers: auto`, which reads /props)."""
    os.chdir(REPO_ROOT)
    benchmarks = resolve_benchmarks(args.benchmark)
    variant_names = [v.strip() for v in args.variants.split(",") if v.strip()]
    if not variant_names or len(variant_names) != len(set(variant_names)):
        raise BenchmarkError("--variants must be a nonempty list of unique names.")
    variants = load_variants(variant_names)
    baseline_names = [b.strip() for b in (getattr(args, "baselines", "") or "").split(",") if b.strip() and b.strip() != "none"]
    baselines = load_baselines(baseline_names)
    seeds = args.seeds
    if not seeds or len(seeds) != len(set(seeds)):
        raise BenchmarkError("--seeds must be nonempty and unique.")
    profile = load_run_profile(args.run_profile)
    requested = parse_workers(args.workers) or profile.get("workers", 1)
    if profile.get("sequential") and requested not in (1,):
        if parse_workers(args.workers) is not None:
            raise BenchmarkError(f"{profile['name']} is strictly sequential; --workers does not apply.")
        requested = 1
    smoke = args.limit is not None or args.allow_unfrozen
    for bm in benchmarks:
        errors, _, _ = check_benchmark(bm)
        if errors:
            raise BenchmarkError(f"{bm.name}: mechanical checks fail ({len(errors)} problems, e.g. {errors[0]}). Run `freeze` after fixing.")
        state, problems = lock_status(bm)
        if state != "ok" and not args.allow_unfrozen:
            raise BenchmarkError(f"{bm.name}: benchmark lock {state}: {'; '.join(problems)}. "
                                 "Run `freeze` (or `freeze --refreeze` after an intended change). "
                                 "Use --allow-unfrozen only for smoke runs (--limit); it marks the run non-eligible.")
        if state != "ok" and args.limit is None:
            raise BenchmarkError("--allow-unfrozen is for --limit smoke runs only; a main run must match the benchmark lock.")
    model_config = Path(args.model_config)
    effective_configs: Dict[str, Any] = {}
    first_cfg = None
    for bm in benchmarks:
        for variant in variant_names:
            cfg = build_variant_config(model_config, bm, variant, variants[variant], endpoint=args.endpoint, profile=profile)
            first_cfg = first_cfg or cfg
            effective_configs[f"{bm.name}/{variant}"] = cfg.model_dump()
        for name, spec in baselines.items():
            effective_configs[f"{bm.name}/{name}"] = build_variant_config(model_config, bm, name, spec, endpoint=args.endpoint, profile=profile).model_dump()
    workers = requested
    if workers == "auto":
        slots = server_info(first_cfg, sha_model=False).get("total_slots")
        if not slots:
            raise BenchmarkError("workers: auto needs the server's /props total_slots, which it does not report.")
        workers = max(1, min(int(slots), int(profile.get("max_workers", 8))))
    workers = int(workers)
    return {"benchmarks": benchmarks, "variant_names": variant_names, "variants": variants, "baselines": baselines, "seeds": seeds, "profile": profile,
            "workers": workers, "model_config": model_config, "endpoint": args.endpoint, "smoke": smoke,
            "first_cfg": first_cfg, "effective_configs": effective_configs, "output": Path(args.output),
            "require_clean": getattr(args, "require_clean", False), "allow_build_drift": getattr(args, "allow_build_drift", False),
            "skip_model_hash": getattr(args, "skip_model_hash", False), "skip_canary": getattr(args, "skip_canary", False),
            "allow_slot_mismatch": getattr(args, "allow_slot_mismatch", False), "allow_busy": getattr(args, "allow_busy", False)}


def build_fingerprint(plan: Dict[str, Any], preflight_report: Dict[str, Any], collection_sha256: str) -> Dict[str, Any]:
    """What must match for two runs (e.g. Mac and GPU) to be comparable, and what may legitimately differ."""
    server = preflight_report.get("server") or {}
    cfg = plan["first_cfg"]
    reranker = {}
    for check in preflight_report.get("checks", []):
        if check["name"] == "reranker_canary":
            reranker = {k: check["data"].get(k) for k in ("backend", "model", "device", "dtype", "max_length", "base_url", "top_k_in",
                                                         "top_k_out", "server_model_file_sha256", "torch", "cuda_devices")}
    return {
        "must_match": {
            "controller_model_file_sha256": server.get("model_file_sha256"), "controller_ftype": server.get("model_ftype"),
            "llama_cpp_build": server.get("build_info"), "chat_template_sha256": server.get("chat_template_sha256"),
            "request_sampling": {"temperature": cfg.model.temperature, "top_p": cfg.model.top_p, "top_k": cfg.model.top_k,
                                 "min_p": cfg.model.min_p, "presence_penalty": cfg.model.presence_penalty,
                                 "constrained_json": cfg.model.constrained_json, "enable_thinking": cfg.model.enable_thinking,
                                 "max_output_tokens": cfg.model.max_output_tokens, "context_tokens": cfg.model.context_tokens},
            "server_default_sampling": server.get("server_default_sampling"),
            "collection_sources_sha256": collection_sha256,
            "model_config_sha256": sha256_file(plan["model_config"]), "variants_sha256": sha256_file(VARIANTS_CONFIG),
            "benchmark_locks": {bm.name: (sha256_file(bm.lock_path) if bm.lock_path.is_file() else None) for bm in plan["benchmarks"]},
            "seeds": plan["seeds"], "variants": plan["variant_names"], "baselines": {n: s_ for n, s_ in plan["baselines"].items()},
        },
        "may_differ": {
            "run_profile": plan["profile"]["name"], "workers": plan["workers"], "platform": platform.platform(),
            "machine": platform.machine(), "reranker_runtime": reranker, "controller_slots": server.get("total_slots"),
            "controller_n_ctx": server.get("n_ctx"), "git_commit": preflight_report.get("git", {}).get("commit"),
        },
        "note": "Two runs are directly comparable only if every must_match entry is equal. may_differ entries (hardware, reranker "
                "runtime, parallelism) must be named wherever numbers from different runs are put side by side.",
    }


def compare_fingerprints(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    def diff(x, y):
        keys = sorted(set(x) | set(y))
        return {k: {"a": x.get(k), "b": y.get(k)} for k in keys if x.get(k) != y.get(k)}
    must = diff(a.get("must_match", {}), b.get("must_match", {}))
    return {"comparable": not must, "must_match_differences": must, "may_differ_differences": diff(a.get("may_differ", {}), b.get("may_differ", {}))}


# ----------------------------------------------------------------------------- run

def _install_signal_handlers(ctx: RunContext):
    import signal
    if threading.current_thread() is not threading.main_thread():
        return

    def handler(signum, _frame):
        if ctx.abort.is_set():  # second signal: stop waiting for in-flight trials
            raise KeyboardInterrupt(f"signal {signum} (second)")
        ctx.signal_received = signum
        ctx.failure = ctx.failure or KeyboardInterrupt(f"signal {signum}")
        ctx.abort.set()
        print(f"signal {signum}: finishing in-flight trials, then stopping (rows are kept; resume with --resume).", flush=True)

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def cmd_preflight(args) -> int:
    from evaluation import bench_preflight
    plan = resolve_plan(args)
    report = bench_preflight.run(plan)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    for check in report["checks"]:
        mark = "ok  " if check["ok"] else ("WARN" if check["severity"] == "warn" else "FAIL")
        print(f"[{mark}] {check['name']}: {check['detail']}", file=sys.stderr)
    return 0 if report["ok"] else 1


def cmd_run(args) -> int:
    os.chdir(REPO_ROOT)
    if not args.execute:
        raise BenchmarkError("No inference without --execute.")
    from evaluation import bench_preflight
    plan = resolve_plan(args)
    benchmarks, variant_names, variants, seeds = plan["benchmarks"], plan["variant_names"], plan["variants"], plan["seeds"]
    profile, workers, model_config, output, smoke = plan["profile"], plan["workers"], plan["model_config"], plan["output"], plan["smoke"]
    first_cfg = plan["first_cfg"]
    trial_timeout = float(args.trial_timeout or profile.get("trial_timeout_seconds") or DEFAULT_TRIAL_TIMEOUT_SECONDS)

    resuming = output.exists()
    if resuming and not args.resume:
        raise BenchmarkError(f"{output} exists. Use a new --output directory (results are never overwritten) or --resume.")
    report = bench_preflight.run(plan)
    for check in report["checks"]:
        if not check["ok"]:
            print(f"preflight {'FAIL' if check['severity'] == 'error' else 'warn'}: {check['name']}: {check['detail']}", file=sys.stderr, flush=True)
    if not report["ok"]:
        raise BenchmarkError("Preflight failed (" + ", ".join(report["failed"]) + "); nothing was run or written. "
                             "Fix the dependency and start again; see `run_benchmark.py preflight` for the full report.")
    server = report["server"]
    reranker_base = (profile.get("reranker") or {}).get("base_url")   # HTTP rerankers only; local ones have no server to probe
    controller_base = server["endpoint"][:-3] if server["endpoint"].endswith("/v1") else server["endpoint"]

    manifest_path = output / "manifest.json"
    collection = collection_paths(benchmarks, model_config, profile)
    current_collection_hashes = {p: sha256_file(p) for p in collection}
    collection_sha = sha256_text(json.dumps(current_collection_hashes, sort_keys=True))
    if resuming:
        if not manifest_path.is_file():
            raise BenchmarkError(f"{output} exists but has no manifest.json; refusing to resume into it.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _check_resume_compat(manifest, benchmarks, variant_names, variants, seeds, args, model_config, workers, profile, plan['baselines'])
        recorded_files = manifest["sources"].get("collection_files")
        if recorded_files is None:   # run written before the narrower drift set existed: compare everything snapshotted
            current_sources = {rel(p): sha256_file(p) for p in source_paths(benchmarks, model_config)}
            changed = [k for k, v in manifest["sources"]["files_sha256"].items() if current_sources.get(k) != v]
        else:
            changed = [k for k in recorded_files if current_collection_hashes.get(k) != manifest["sources"]["files_sha256"].get(k)]
            changed += [k for k in collection if k not in recorded_files]
        if changed:
            raise BenchmarkError(f"Sources changed since the run started ({len(changed)} files, e.g. {changed[0]}); "
                                 "a resumed run must use identical code/config. Start a new run directory.")
        old_fp = (manifest.get("fingerprint") or {}).get("must_match") or {}
        new_fp = build_fingerprint(plan, report, collection_sha)["must_match"]
        drifted = [k for k in ("controller_model_file_sha256", "llama_cpp_build", "chat_template_sha256", "request_sampling",
                               "controller_ftype") if old_fp.get(k) is not None and old_fp.get(k) != new_fp.get(k)]
        if drifted:
            raise BenchmarkError(f"The controller server changed since this run started ({', '.join(drifted)}); resuming would mix "
                                 "two different systems in one run. Start a new run directory.")
        fragment = repair_partial_tail(output / TRIALS_FILE)
        if fragment:
            print(f"resume: an incomplete last line was moved to {fragment}", flush=True)
        else:
            fragment = None
    else:
        output.mkdir(parents=True)
        (output / "state").mkdir()
        paths = source_paths(benchmarks, model_config)
        sources_sha = snapshot_sources(paths, output)
        fingerprint = build_fingerprint(plan, report, collection_sha)
        manifest = {
            "schema": RUN_SCHEMA, "run_id": output.name, "created_at": utcnow(),
            "phase": "smoke" if smoke else "main", "limit": args.limit, "allow_unfrozen": args.allow_unfrozen,
            "report_eligible": False,
            "report_eligible_note": ("Eligible only as input to the D2 report after the judge/analysis; "
                                     "smoke and unfrozen runs are never eligible." if not smoke else
                                     "Smoke/unfrozen run: pipeline check only, not report evidence."),
            "benchmarks": [{"name": bm.name, "tasks_path": rel(bm.tasks_path), "tasks_sha256": sha256_file(bm.tasks_path), "corpus": bm.corpus_path,
                            "corpus_sha256": sha256_file(bm.corpus_path), "profile": bm.profile_ref,
                            "profile_sha256": sha256_file(bm.profile_path),
                            "lock_sha256": sha256_file(bm.lock_path) if bm.lock_path.is_file() else None,
                            "lock_status": lock_status(bm)[0], "review_status": bm.spec.get("review_status")} for bm in benchmarks],
            "variants": {n: variants[n] for n in variant_names}, "seeds": seeds,
            "run_profile": {**profile, "workers_effective": workers},
            "trial_timeout_seconds": trial_timeout,
            "model_config": {"path": rel(model_config), "sha256": sha256_file(model_config)},
            "endpoint_override": args.endpoint, "effective_configs": plan["effective_configs"],
            "git": report["git"], "hardware": hardware_info(), "server": server, "preflight": report,
            "fingerprint": fingerprint,
            "server_operator_note": args.server_note,
            "server_hardware_note": ("Operator-provided text, not measured by this tool." if args.server_note else
                                     "Not recorded; runner-machine hardware above is the machine that issues requests."),
            "sources": {"files_sha256": sources_sha, "collection_files": collection, "collection_sha256": collection_sha},
            "latency_reportable": profile["latency_reportable"],
            "scoring": "Retrieval/citation-ID metrics and lexical proxies only; semantic judging is a separate step (judge_benchmark.py).",
            "status": "collecting", "resumes": [], "API_charge_USD": None,
            "API_charge_note": "Local endpoint; this is not a claim of zero compute cost.",
        }
        write_json(manifest_path, manifest)

    runs_path = output / TRIALS_FILE
    existing = latest_by_key(read_rows(runs_path))
    baselines = plan["baselines"]
    items, planned, task_ids, baseline_ids = plan_work(benchmarks, variant_names, seeds, args.limit, existing, args.retry_errors, baselines)
    manifest["planned_trials"] = planned
    manifest["task_ids"] = task_ids
    manifest["baselines"] = baselines
    manifest["baseline_task_ids"] = baseline_ids
    if resuming:
        manifest["resumes"].append({"at": utcnow(), "rows_before": len(existing), "retry_errors": args.retry_errors,
                                    "partial_tail_moved_to": fragment, "machine_state": report["checks"][-1]["data"] if report["checks"] else None})
        manifest["status"] = "collecting"
    write_json(manifest_path, manifest)
    print(f"run {output.name}: planned {planned}, already recorded {len(existing)}, to run now {len(items)} "
          f"({profile['name']}, workers={workers}, trial timeout {trial_timeout:.0f}s, latency_reportable={profile['latency_reportable']})", flush=True)

    sampler = None
    if profile.get("record_memory") and workers == 1:
        sampler = MemorySampler(server.get("local_server_pid"))
        sampler.start()
    work: "queue.Queue" = queue.Queue()
    for item in items:
        work.put(item)
    ctx = RunContext(model_config=model_config, variants={**variants, **baselines}, endpoint=args.endpoint, output=output,
                     profile=profile, workers=workers, writer=RowWriter(runs_path), warmup_writer=RowWriter(output / "warmup.jsonl"),
                     sampler=sampler, total=len(items), max_backend_errors=args.max_backend_errors, trial_timeout=trial_timeout,
                     controller_base=controller_base, reranker_base=reranker_base, warmup_questions=load_warmup_questions(),
                     collection_hashes=current_collection_hashes)
    _install_signal_handlers(ctx)
    started = time.monotonic()
    try:
        if workers == 1:
            worker_loop(0, work, ctx)
        else:
            threads = [threading.Thread(target=worker_loop, args=(i, work, ctx), name=f"worker-{i}") for i in range(workers)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
    except KeyboardInterrupt:
        ctx.failure = ctx.failure or KeyboardInterrupt("interrupted")
        ctx.abort.set()
    finally:
        if sampler:
            sampler.stop()
        rows = read_rows(runs_path)
        latest = latest_by_key(rows)
        remaining = planned - len(latest)
        manifest["rows_recorded"] = len(rows)
        manifest["trials_recorded"] = len(latest)
        manifest["trials_missing"] = remaining
        manifest["execution_errors"] = sum(r["system_error"] for r in latest.values())
        manifest["error_kinds"] = _count(r["error_kind"] for r in latest.values() if r["system_error"])
        manifest["wall_seconds_this_session"] = round(time.monotonic() - started, 2)
        manifest["wall_seconds_total"] = round(manifest.get("wall_seconds_total", 0) + manifest["wall_seconds_this_session"], 2)
        manifest["finished_at"] = utcnow()
        manifest["sources_changed_during_session"] = [p for p, h in current_collection_hashes.items() if sha256_file(p) != h]
        manifest["machine_state_end"] = bench_preflight.machine_state()
        manifest["peak_memory_mb"] = {
            "runner_rss_sampled": sampler.run_peak["runner_mb"] if sampler else None,
            "runner_ru_maxrss": _maxrss_mb(),
            "llama_server_rss_sampled": sampler.run_peak["server_mb"] if sampler else None,
            "note": "Sampled with `ps` every 0.5 s on this machine (mac-latency, local server only); null = not measured.",
        }
        if ctx.failure is not None:
            manifest["status"] = "incomplete"
            manifest["failure"] = f"{type(ctx.failure).__name__}: {ctx.failure}"
        else:
            manifest["status"] = "collected" if remaining == 0 else "incomplete"
            manifest.pop("failure", None)
        if runs_path.is_file():
            manifest["runs_sha256"] = sha256_file(runs_path)
        write_json(manifest_path, manifest)
    if ctx.failure is not None:
        print(f"STOPPED: {type(ctx.failure).__name__}: {ctx.failure}", file=sys.stderr)
        return 2
    print(json.dumps({"run_dir": str(output), "status": manifest["status"], "trials_recorded": manifest["trials_recorded"],
                      "execution_errors": manifest["execution_errors"], "phase": manifest["phase"]}))
    return 0


def _maxrss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss  # bytes on macOS, KiB on Linux
    return round(peak / 1048576 if sys.platform == "darwin" else peak / 1024, 2)


def _count(values) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for v in values:
        out[str(v)] = out.get(str(v), 0) + 1
    return out


def _check_resume_compat(manifest, benchmarks, variant_names, variants, seeds, args, model_config, workers, profile, baselines=None) -> None:
    problems = []
    if (manifest.get("baselines") or {}) != (baselines or {}):
        problems.append("baselines differ")
    if manifest.get("schema") != RUN_SCHEMA:
        problems.append("not a run_benchmark run")
    if sorted(manifest.get("variants", {})) != sorted(variant_names):
        problems.append("variants differ")
    elif any(manifest["variants"][n] != variants[n] for n in variant_names):
        problems.append("variant definitions changed")
    if manifest.get("seeds") != seeds:
        problems.append("seeds differ")
    if manifest.get("limit") != args.limit:
        problems.append("--limit differs")
    recorded_profile = {k: v for k, v in (manifest.get("run_profile") or {}).items() if k != "workers_effective"}
    if recorded_profile.get("name") != profile["name"]:
        problems.append("run profile differs")
    elif recorded_profile != profile:
        problems.append("run profile content changed")
    if manifest.get("run_profile", {}).get("workers_effective") != workers:
        problems.append("worker count differs")
    if manifest.get("model_config", {}).get("sha256") != sha256_file(model_config):
        problems.append("model config changed")
    if manifest.get("endpoint_override") != args.endpoint:
        problems.append("endpoint override differs")
    recorded = {b["name"]: b for b in manifest.get("benchmarks", [])}
    if sorted(recorded) != sorted(b.name for b in benchmarks):
        problems.append("benchmarks differ")
    for bm in benchmarks:
        entry = recorded.get(bm.name)
        if entry and (entry["tasks_sha256"] != sha256_file(bm.tasks_path) or entry["corpus_sha256"] != sha256_file(bm.corpus_path)):
            problems.append(f"{bm.name}: tasks/corpus changed")
    if problems:
        raise BenchmarkError("Cannot resume this run: " + "; ".join(problems))


# ----------------------------------------------------------------------------- status

def cmd_status(args) -> int:
    os.chdir(REPO_ROOT)
    refs = args.benchmark or ["all"]
    for bm in resolve_benchmarks(refs):
        state, problems = lock_status(bm)
        ready = bm.tasks_path.is_file()
        print(f"{bm.name}: tasks.json {'present' if ready else 'MISSING'}; lock {state}" + (f" ({'; '.join(problems)})" if problems else ""))
    if args.run_dir:
        root = Path(args.run_dir)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        rows = read_rows(trials_path(root))
        latest = latest_by_key(rows)
        print(f"run {manifest['run_id']}: phase={manifest['phase']} status={manifest['status']} "
              f"profile={manifest['run_profile']['name']} planned={manifest.get('planned_trials')} recorded={len(latest)} rows={len(rows)}")
        groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for row in latest.values():
            groups.setdefault((row["benchmark"], row["variant"]), []).append(row)
        for (bm, variant), group in sorted(groups.items()):
            statuses = _count(r["terminal_status"] for r in group)
            print(f"  {bm:14s} {variant:10s} n={len(group):4d} errors={sum(r['system_error'] for r in group)} {statuses}")
        errors = _count(r["error_kind"] for r in latest.values() if r["system_error"])
        if errors:
            print(f"  error kinds: {errors}")
        retried = sum(1 for r in rows if r.get("attempt", 1) > 1)
        if retried:
            print(f"  retry attempts recorded: {retried}")
        progress = root / "progress.json"
        if progress.is_file():
            p = json.loads(progress.read_text(encoding="utf-8"))
            print(f"  progress ({p['updated_at']}): {p['completed_this_session']}/{p['to_run_this_session']} this session, "
                  f"{p.get('trials_per_minute')} trials/min, ETA {p.get('eta_s')} s, errors {p['execution_errors_this_session']}")
        if manifest.get("failure"):
            print(f"  last failure: {manifest['failure']}")
    return 0


# ----------------------------------------------------------------------------- CLI

def _selection_arguments(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--benchmark", action="append", required=True, help="benchmark dir or name (repeatable) or 'all'")
    sub.add_argument("--variants", default="off,l1,l1_rerank")
    sub.add_argument("--baselines", default="", help="diagnostic baselines to add (comma list from variants.yaml `baselines`, e.g. closed_book,oracle); default none")
    sub.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    sub.add_argument("--run-profile", default="mac-latency", help=f"one of {sorted(discover_profiles())} or the path of a profile YAML")
    sub.add_argument("--workers", help="positive integer or 'auto' (= the server's slots, capped by the profile's max_workers); default from the run profile")
    sub.add_argument("--model-config", default=str(DEFAULT_MODEL_CONFIG))
    sub.add_argument("--endpoint", help="override model.endpoint (loopback only, e.g. a forwarded port)")
    sub.add_argument("--limit", type=int, help="smoke: N tasks per benchmark, round-robin over categories")
    sub.add_argument("--allow-unfrozen", action="store_true", help="smoke only: run without a matching lock (run is marked non-eligible)")
    sub.add_argument("--allow-slot-mismatch", action="store_true")
    sub.add_argument("--allow-busy", action="store_true", help="profiles with require_idle: run although the machine is busy (the load is recorded)")
    sub.add_argument("--allow-build-drift", action="store_true", help="accept a llama.cpp build different from config/benchmark/expected_server.yaml (recorded)")
    sub.add_argument("--require-clean", action="store_true", help="refuse when src/ or config/ or the collection code has uncommitted changes")
    sub.add_argument("--skip-model-hash", action="store_true", help="do not sha256 the local GGUF (identity then unverified)")
    sub.add_argument("--skip-canary", action="store_true", help="skip the 4-request seed canary")
    sub.add_argument("--output", default="evaluation/runs/_preflight", help="a new run directory (existing paths are refused unless --resume)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze", help="mechanical checks and benchmark.lock.json")
    freeze.add_argument("--benchmark", action="append", required=True, help="benchmark dir or name (repeatable) or 'all'")
    freeze.add_argument("--refreeze", action="store_true", help="archive an existing, different lock and write a new one")
    freeze.set_defaults(func=cmd_freeze)
    run = sub.add_parser("run", help="collect trials (needs --execute)")
    _selection_arguments(run)
    run.set_defaults(output=None)
    run.add_argument("--resume", action="store_true", help="continue an existing run directory (append only)")
    run.add_argument("--retry-errors", action="store_true",
                     help="with --resume: add a new attempt for backend_error rows whose server was down (old rows kept)")
    run.add_argument("--max-backend-errors", type=int, default=5, help="stop after N consecutive trials that failed while their dependency was down")
    run.add_argument("--trial-timeout", type=float, help="hard per-trial watchdog in seconds (default: run profile)")
    run.add_argument("--server-note", help="operator-provided description of the server hardware/flags (recorded verbatim)")
    run.add_argument("--execute", action="store_true", help="explicit permission to run real inference")
    run.set_defaults(func=cmd_run)
    pre = sub.add_parser("preflight", help="exercise every dependency once; nothing is run or written")
    _selection_arguments(pre)
    pre.set_defaults(func=cmd_preflight)
    status = sub.add_parser("status", help="lock state and run progress")
    status.add_argument("--benchmark", action="append")
    status.add_argument("--run-dir")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    os.chdir(REPO_ROOT)
    args = build_parser().parse_args(argv)
    if args.command == "run" and not args.output:
        print("BenchmarkError: --output is required for `run`.", file=sys.stderr)
        return 1
    try:
        return args.func(args)
    except BenchmarkError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
