"""D2 benchmark runner: freeze a benchmark, then run benchmark x variant x seed trials on real native inference.

Subcommands
  freeze   mechanical checks + benchmark.lock.json (sha256 of tasks, corpus, profile, verification files)
  run      collect trials (requires --execute); refuses when the benchmark lock does not match the files
  status   show lock state and, with --run-dir, the progress of a collection

Rules (AGENTS.md): real inference only, a backend failure is an execution error row (never a substitute answer),
failed runs and rows are preserved, nothing is overwritten. Latency is reportable only for the mac-latency profile.
Run from anywhere: the working directory is switched to the repository root.
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

BENCHMARKS_DIR = Path("evaluation/benchmarks")
VARIANTS_CONFIG = Path("config/benchmark/variants.yaml")
RUN_PROFILES = {"mac-latency": Path("config/benchmark/profile_mac_latency.yaml"),
                "gpu-accuracy": Path("config/benchmark/profile_gpu_accuracy.yaml")}
DEFAULT_MODEL_CONFIG = Path("config/benchmark/model_prism_gguf2b.yaml")
DEFAULT_SEEDS = [42, 123, 2026]
LOCK_SCHEMA = "luatcheck.benchmark.lock.v1"
RUN_SCHEMA = "luatcheck.benchmark.run.v1"
VALID_BEHAVIORS = {"answer", "refuse"}
MODEL_ENV_OVERRIDES = ("MODEL_ENDPOINT", "OLLAMA_ENDPOINT", "MODEL_NAME", "MODEL_PROVIDER")
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
RETRYABLE_ERROR_KINDS = {"backend_error"}


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


def build_variant_config(model_config: Path, bm: Benchmark, variant: str, variant_spec: Dict[str, Any],
                         *, endpoint: Optional[str] = None, state_dir: Optional[Path] = None, tag: str = "w0"):
    """AppConfig for one benchmark x variant. Raises ConfigError when src/ does not honour a requested key."""
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
    overrides = variant_spec.get("overrides") or {}
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
        info["cpu_brand"] = platform.processor() or None
        if shutil.which("nvidia-smi"):
            info["nvidia_smi"] = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
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

def source_paths(benchmarks: List[Benchmark], model_config: Path) -> List[Path]:
    paths: List[Path] = []
    for pattern in ("src/**/*.py", "src/**/*.yaml", "src/**/*.json", "evaluation/*.py", "evaluation/judge_prompt.txt",
                    "config/**/*.yaml", "config/**/*.yml", "config/**/*.json"):
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
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


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
                  sampler: Optional[MemorySampler], provider: str) -> Dict[str, Any]:
    from evaluation.metrics import calculate_citation_metrics, calculate_retrieval_metrics, calculate_unsupported_rate
    from src.agent.state import CaseLedger
    session = f"{bm_name}-{variant}-s{seed}-{task['task_id']}-a{attempt}"
    agent.llm_client.seed = seed
    started_at = utcnow()
    if sampler:
        sampler.snapshot_and_reset()
    before = time.monotonic()
    runner_exception = None
    try:
        ledger = agent.run(task["question"], pasted_doc=task.get("pasted_doc"), session_id=session)
    except Exception as exc:  # preserved as an execution error row; never replaced by an answer
        runner_exception = f"{type(exc).__name__}: {exc}"
        ledger = agent.ledger or CaseLedger(session_id=session, original_query=task["question"])
        ledger.is_terminal, ledger.terminal_status = True, "error"
        ledger.final_output = {"action": "error", "reason": runner_exception, "error_kind": "runner_exception",
                               "citations": [], "verified": False}
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
        "benchmark": bm_name, "variant": variant, "verification_mode": verification_mode, "mode": variant,
        "task_id": task["task_id"], "category": task.get("category"), "seed": seed, "attempt": attempt,
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
        "peak_memory_mb": memory if sampler else None, "provider": provider,
        "human_task_correct": None, "human_unsupported_claims": None,
        "ledger": ledger.model_dump(),
    }


class RunContext:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.abort = threading.Event()
        self.failure: Optional[BaseException] = None
        self.consecutive_backend_errors = 0
        self.counter_lock = threading.Lock()
        self.completed = 0


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
                cfg = build_variant_config(ctx.model_config, bm, variant, ctx.variants[variant], endpoint=ctx.endpoint,
                                           state_dir=ctx.output / "state", tag=f"w{wid}")
                agent = LuatCheckAgent(config=cfg, verification_mode=ctx.variants[variant]["verification_mode"], l2_use_slm=False)
                if type(agent.llm_client) is not LlamaCppLLMClient:
                    raise TypeError("The configured real llama.cpp inference client is required for collection.")
                agents[key] = agent
            row = execute_trial(agents[key], bm.name, variant, ctx.variants[variant]["verification_mode"], task, seed,
                                run_profile=ctx.profile["name"], latency_reportable=ctx.profile["latency_reportable"],
                                worker=wid, attempt=attempt, sampler=ctx.sampler if ctx.workers == 1 else None,
                                provider="llamacpp")
            ctx.writer.append(row)
            with ctx.counter_lock:
                ctx.completed += 1
                if row["system_error"] and row["error_kind"] == "backend_error":
                    ctx.consecutive_backend_errors += 1
                elif not row["system_error"]:
                    ctx.consecutive_backend_errors = 0
                too_many = ctx.consecutive_backend_errors >= ctx.max_backend_errors
                print(f"[{ctx.completed}/{ctx.total}] {bm.name} {variant} s{seed} {task['task_id']} -> {row['terminal_status']}"
                      f"{' (' + str(row['error_kind']) + ')' if row['system_error'] else ''} {row['wall_ms'] / 1000:.1f}s w{wid}",
                      flush=True)
            if too_many:
                raise BenchmarkError(f"{ctx.max_backend_errors} consecutive backend errors: collection stopped. "
                                     "Rows are retained; resume with --resume --retry-errors once the server is healthy.")
    except BaseException as exc:
        ctx.failure = ctx.failure or exc
        ctx.abort.set()


def plan_work(benchmarks: List[Benchmark], variants: List[str], seeds: List[int], limit: Optional[int],
              existing: Dict[Tuple, Dict[str, Any]], retry_errors: bool):
    """Deterministic order: benchmark, seed, task, with the variant order alternating per task (as run_eval does)."""
    items = []
    planned = 0
    task_ids: Dict[str, List[str]] = {}
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
                    elif retry_errors and prior["system_error"] and prior.get("error_kind") in RETRYABLE_ERROR_KINDS:
                        items.append((bm, variant, seed, task, prior.get("attempt", 1) + 1))
    return items, planned, task_ids


def cmd_run(args) -> int:
    os.chdir(REPO_ROOT)
    if not args.execute:
        raise BenchmarkError("No inference without --execute.")
    benchmarks = resolve_benchmarks(args.benchmark)
    variant_names = [v.strip() for v in args.variants.split(",") if v.strip()]
    if not variant_names or len(variant_names) != len(set(variant_names)):
        raise BenchmarkError("--variants must be a nonempty list of unique names.")
    variants = load_variants(variant_names)
    seeds = args.seeds
    if not seeds or len(seeds) != len(set(seeds)):
        raise BenchmarkError("--seeds must be nonempty and unique.")
    profile = yaml.safe_load(RUN_PROFILES[args.run_profile].read_text(encoding="utf-8"))
    workers = 1 if args.run_profile == "mac-latency" else (args.workers or profile["workers"])
    if args.run_profile == "mac-latency" and args.workers not in (None, 1):
        raise BenchmarkError("mac-latency is strictly sequential; --workers applies to gpu-accuracy only.")
    if workers < 1:
        raise BenchmarkError("--workers must be >= 1.")
    model_config = Path(args.model_config)
    output = Path(args.output)

    # Lock verification: main runs are bound to the frozen benchmark.
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
    # Validate every (benchmark, variant) configuration up front, before any inference.
    effective_configs: Dict[str, Any] = {}
    first_cfg = None
    for bm in benchmarks:
        for variant in variant_names:
            cfg = build_variant_config(model_config, bm, variant, variants[variant], endpoint=args.endpoint)
            first_cfg = first_cfg or cfg
            effective_configs[f"{bm.name}/{variant}"] = cfg.model_dump()
    if args.run_profile == "gpu-accuracy":
        pass  # slots are checked against workers below, after server preflight
    server = server_info(first_cfg, sha_model=not args.skip_model_hash)
    if workers > 1:
        slots = server.get("total_slots")
        if slots is None:
            raise BenchmarkError("Server /props does not report total_slots; cannot confirm -np >= workers.")
        if slots < workers and not args.allow_slot_mismatch:
            raise BenchmarkError(f"{workers} workers but llama-server has {slots} slots (-np). Start it with -np {workers} "
                                 f"and -c >= {first_cfg.model.context_tokens * workers}, or lower --workers.")
        n_ctx = server.get("n_ctx")
        if n_ctx and n_ctx < first_cfg.model.context_tokens * min(workers, slots):
            raise BenchmarkError(f"Server -c {n_ctx} gives less than context_tokens={first_cfg.model.context_tokens} per slot "
                                 f"for {workers} workers; restart llama-server with a larger -c.")

    if workers > 2 and sys.platform == "darwin" and any(variants[v].get("overrides", {}).get("retrieval", {}).get("reranker") for v in variant_names):
        print(f"WARNING: {workers} workers each load their own reranker copy on this Mac; this can exhaust unified memory. "
              "Run the runner on the GPU server or lower --workers.", file=sys.stderr, flush=True)

    resuming = output.exists()
    if resuming and not args.resume:
        raise BenchmarkError(f"{output} exists. Use a new --output directory (results are never overwritten) or --resume.")
    manifest_path = output / "manifest.json"
    if resuming:
        if not manifest_path.is_file():
            raise BenchmarkError(f"{output} exists but has no manifest.json; refusing to resume into it.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _check_resume_compat(manifest, benchmarks, variant_names, seeds, args, model_config, workers)
        current_sources = {rel(p): sha256_file(p) for p in source_paths(benchmarks, model_config)}
        changed = [k for k, v in manifest["sources"]["files_sha256"].items() if current_sources.get(k) != v]
        if changed:
            raise BenchmarkError(f"Sources changed since the run started ({len(changed)} files, e.g. {changed[0]}); "
                                 "a resumed run must use identical code/config. Start a new run directory.")
    else:
        output.mkdir(parents=True)
        (output / "state").mkdir()
        paths = source_paths(benchmarks, model_config)
        sources_sha = snapshot_sources(paths, output)
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
            "model_config": {"path": rel(model_config), "sha256": sha256_file(model_config)},
            "endpoint_override": args.endpoint, "effective_configs": effective_configs,
            "git": git_state(), "hardware": hardware_info(), "server": server,
            "server_operator_note": args.server_note,
            "server_hardware_note": ("Operator-provided text, not measured by this tool." if args.server_note else
                                     "Not recorded; runner-machine hardware above is the Mac that issues requests."),
            "sources": {"files_sha256": sources_sha},
            "latency_reportable": profile["latency_reportable"],
            "scoring": "Retrieval/citation-ID metrics and lexical proxies only; semantic judging is a separate step (judge_benchmark.py).",
            "status": "collecting", "resumes": [], "API_charge_USD": None,
            "API_charge_note": "Local endpoint; this is not a claim of zero compute cost.",
        }
        write_json(manifest_path, manifest)

    runs_path = output / "runs.jsonl"
    existing = latest_by_key(read_rows(runs_path))
    items, planned, task_ids = plan_work(benchmarks, variant_names, seeds, args.limit, existing, args.retry_errors)
    manifest["planned_trials"] = planned
    manifest["task_ids"] = task_ids
    if resuming:
        manifest["resumes"].append({"at": utcnow(), "rows_before": len(existing), "retry_errors": args.retry_errors})
        manifest["status"] = "collecting"
    write_json(manifest_path, manifest)
    print(f"run {output.name}: planned {planned}, already recorded {len(existing)}, to run now {len(items)} "
          f"({args.run_profile}, workers={workers}, latency_reportable={profile['latency_reportable']})", flush=True)

    sampler = None
    if profile.get("record_memory") and workers == 1:
        sampler = MemorySampler(server.get("local_server_pid"))
        sampler.start()
    work: "queue.Queue" = queue.Queue()
    for item in items:
        work.put(item)
    ctx = RunContext(model_config=model_config, variants=variants, endpoint=args.endpoint, output=output,
                     profile=profile, workers=workers, writer=RowWriter(runs_path), sampler=sampler, total=len(items),
                     max_backend_errors=args.max_backend_errors)
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
        manifest["finished_at"] = utcnow()
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


def _check_resume_compat(manifest, benchmarks, variant_names, seeds, args, model_config, workers) -> None:
    problems = []
    if manifest.get("schema") != RUN_SCHEMA:
        problems.append("not a run_benchmark run")
    if sorted(manifest.get("variants", {})) != sorted(variant_names):
        problems.append("variants differ")
    if manifest.get("seeds") != seeds:
        problems.append("seeds differ")
    if manifest.get("limit") != args.limit:
        problems.append("--limit differs")
    if manifest.get("run_profile", {}).get("name") != args.run_profile:
        problems.append("run profile differs")
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
        rows = read_rows(root / "runs.jsonl")
        latest = latest_by_key(rows)
        print(f"run {manifest['run_id']}: phase={manifest['phase']} status={manifest['status']} "
              f"profile={manifest['run_profile']['name']} planned={manifest.get('planned_trials')} recorded={len(latest)} rows={len(rows)}")
        groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for row in latest.values():
            groups.setdefault((row["benchmark"], row["variant"]), []).append(row)
        for (bm, variant), group in sorted(groups.items()):
            statuses = _count(r["terminal_status"] for r in group)
            print(f"  {bm:14s} {variant:10s} n={len(group):4d} errors={sum(r['system_error'] for r in group)} {statuses}")
        retried = sum(1 for r in rows if r.get("attempt", 1) > 1)
        if retried:
            print(f"  retry attempts recorded: {retried}")
    return 0


# ----------------------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze", help="mechanical checks and benchmark.lock.json")
    freeze.add_argument("--benchmark", action="append", required=True, help="benchmark dir or name (repeatable) or 'all'")
    freeze.add_argument("--refreeze", action="store_true", help="archive an existing, different lock and write a new one")
    freeze.set_defaults(func=cmd_freeze)
    run = sub.add_parser("run", help="collect trials (needs --execute)")
    run.add_argument("--benchmark", action="append", required=True, help="benchmark dir or name (repeatable) or 'all'")
    run.add_argument("--variants", default="off,l1,l1_rerank")
    run.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    run.add_argument("--run-profile", choices=sorted(RUN_PROFILES), default="mac-latency")
    run.add_argument("--workers", type=int, help="gpu-accuracy only (default from the run-profile config)")
    run.add_argument("--model-config", default=str(DEFAULT_MODEL_CONFIG))
    run.add_argument("--endpoint", help="override model.endpoint (loopback only, e.g. a forwarded port)")
    run.add_argument("--output", required=True, help="a new run directory (existing paths are refused unless --resume)")
    run.add_argument("--limit", type=int, help="smoke: N tasks per benchmark, round-robin over categories")
    run.add_argument("--allow-unfrozen", action="store_true", help="smoke only: run without a matching lock (run is marked non-eligible)")
    run.add_argument("--resume", action="store_true", help="continue an existing run directory (append only)")
    run.add_argument("--retry-errors", action="store_true", help="with --resume: add a new attempt for backend_error rows (old rows kept)")
    run.add_argument("--max-backend-errors", type=int, default=5, help="stop after N consecutive backend_error rows")
    run.add_argument("--allow-slot-mismatch", action="store_true")
    run.add_argument("--skip-model-hash", action="store_true", help="do not sha256 the local GGUF (recorded as null)")
    run.add_argument("--server-note", help="operator-provided description of the server hardware/flags (recorded verbatim)")
    run.add_argument("--execute", action="store_true", help="explicit permission to run real inference")
    run.set_defaults(func=cmd_run)
    status = sub.add_parser("status", help="lock state and run progress")
    status.add_argument("--benchmark", action="append")
    status.add_argument("--run-dir")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    os.chdir(REPO_ROOT)
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BenchmarkError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
