"""Benchmark runner tests on real components: the real hcmut_v1 files, the real agent and the running llama-server.

No mocks, stand-ins or canned model output. Temporary directories hold copies of the real benchmark files and run
outputs. The paid judge is never called here. Tests that need native inference FAIL (never skip, never fake) when the
llama-server on 127.0.0.1:8081 is not reachable. Failure paths are provoked with real failures: a closed port, an
oversized prompt the real server rejects, a trial timeout shorter than a real request.
"""
import hashlib
import json
import shutil
import sys
import subprocess
import os
from pathlib import Path

import pytest
import requests

from evaluation import judge_benchmark as jb
from evaluation import render_benchmark_tables as render
from evaluation import run_benchmark as rb

REPO = Path(__file__).resolve().parents[1]
BENCH = REPO / "evaluation" / "benchmarks" / "hcmut_v1"
ENDPOINT = "http://127.0.0.1:8081/v1"
RUN_ROW_KEYS = {"warmup", "trial_timeout_seconds", "task_id", "seed", "mode", "expected_behavior", "terminal_status", "gold_article_ids", "system_error",
                "error_kind", "pre_model_policy_refusal", "native_calls", "successful_native_calls", "wall_ms",
                "token_usage_complete", "input_tokens", "output_tokens", "retrieval", "citation",
                "lexical_unsupported_proxy", "human_task_correct", "human_unsupported_claims", "ledger"}


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def server_up() -> bool:
    try:
        return requests.get(ENDPOINT + "/models", timeout=3).status_code == 200
    except requests.RequestException:
        return False


SERVER_DOWN = "llama-server not reachable on 127.0.0.1:8081: start it with `make prism-server` (tests never start it)"


def needs_server(test):
    """Real-inference tests fail (never skip) when the model server is down."""
    def wrapper(*args, **kwargs):
        assert server_up(), SERVER_DOWN
        return test(*args, **kwargs)
    wrapper.__name__, wrapper.__doc__ = test.__name__, test.__doc__
    import inspect
    wrapper.__signature__ = inspect.signature(test)
    return wrapper


@pytest.fixture()
def bench_copy(tmp_path):
    """A temp copy of the real hcmut_v1 benchmark directory (same corpus and profile paths)."""
    target = tmp_path / "hcmut_v1"
    shutil.copytree(BENCH, target, ignore=shutil.ignore_patterns("benchmark.lock*"))
    return target


# ----------------------------------------------------------------------------- freeze / lock

def test_real_hcmut_benchmark_passes_mechanical_checks():
    bm = rb.Benchmark(BENCH)
    errors, warnings, info = rb.check_benchmark(bm)
    assert errors == []
    assert info["tasks"] == 50 and info["categories"] == {"single": 40, "multi": 5, "out_of_scope": 5}
    assert info["expected_behaviors"] == {"answer": 45, "refuse": 5}


def test_freeze_writes_lock_with_real_hashes_and_is_idempotent(bench_copy):
    assert rb.main(["freeze", "--benchmark", str(bench_copy)]) == 0
    lock = json.loads((bench_copy / "benchmark.lock.json").read_text())
    assert lock["tasks"]["sha256"] == sha(BENCH / "tasks.json")
    assert lock["corpus"]["sha256"] == sha(REPO / "data/corpus/hcmut_academic_v1.json")
    assert lock["profile"]["sha256"] == sha(REPO / "config/domains/hcmut_academic.yaml")
    assert any(name.endswith("verify_A.json") for name in lock["verification_files"])
    assert lock["tasks"]["count"] == 50
    before = (bench_copy / "benchmark.lock.json").read_text()
    assert rb.main(["freeze", "--benchmark", str(bench_copy)]) == 0
    assert (bench_copy / "benchmark.lock.json").read_text() == before  # unchanged benchmark: lock untouched
    assert rb.lock_status(rb.Benchmark(bench_copy))[0] == "ok"


def test_freeze_refuses_when_a_quote_is_not_verbatim(bench_copy):
    tasks = json.loads((bench_copy / "tasks.json").read_text())
    tasks[0]["reference_evidence"][0]["exact_quote"] += " (altered)"
    (bench_copy / "tasks.json").write_text(json.dumps(tasks, ensure_ascii=False))
    assert rb.main(["freeze", "--benchmark", str(bench_copy)]) == 1
    assert not (bench_copy / "benchmark.lock.json").exists()


def test_freeze_refuses_duplicate_ids_and_missing_gold(bench_copy):
    tasks = json.loads((bench_copy / "tasks.json").read_text())
    tasks[1]["task_id"] = tasks[0]["task_id"]
    tasks[2]["ground_truth_article_ids"] = ["HCMUT_NOT_A_RECORD"]
    (bench_copy / "tasks.json").write_text(json.dumps(tasks, ensure_ascii=False))
    errors, _, _ = rb.check_benchmark(rb.Benchmark(bench_copy))
    assert any("not unique" in e for e in errors)
    assert any("gold ids not in corpus" in e for e in errors)
    assert rb.main(["freeze", "--benchmark", str(bench_copy)]) == 1


def test_refreeze_requires_explicit_flag(bench_copy):
    assert rb.main(["freeze", "--benchmark", str(bench_copy)]) == 0
    tasks = json.loads((bench_copy / "tasks.json").read_text())
    tasks[0]["notes"] = "edited after freeze"
    (bench_copy / "tasks.json").write_text(json.dumps(tasks, ensure_ascii=False))
    assert rb.main(["freeze", "--benchmark", str(bench_copy)]) == 1  # differs from the lock: refused
    assert rb.main(["freeze", "--benchmark", str(bench_copy), "--refreeze"]) == 0
    assert list(bench_copy.glob("benchmark.lock.superseded-*.json"))  # the old lock is archived, not lost


def test_run_refuses_lock_mismatch_and_missing_lock_without_inference(bench_copy, tmp_path):
    out = tmp_path / "refused-run"
    base = ["run", "--benchmark", str(bench_copy), "--variants", "off", "--seeds", "42", "--output", str(out), "--execute"]
    assert rb.main(base) == 1 and not out.exists()  # no lock yet
    assert rb.main(["freeze", "--benchmark", str(bench_copy)]) == 0
    tasks = json.loads((bench_copy / "tasks.json").read_text())
    tasks[0]["question"] += " (changed after freeze)"
    (bench_copy / "tasks.json").write_text(json.dumps(tasks, ensure_ascii=False))
    assert rb.lock_status(rb.Benchmark(bench_copy))[0] == "mismatch"
    assert rb.main(base) == 1 and not out.exists()  # lock hash mismatch: refused before any directory or request
    assert rb.main(base[:-1] + ["--allow-unfrozen", "--execute"]) == 1 and not out.exists()  # unfrozen needs --limit (smoke) too


def test_run_requires_execute_flag(bench_copy, tmp_path):
    args = rb.build_parser().parse_args(["run", "--benchmark", str(bench_copy), "--output", str(tmp_path / "x")])
    with pytest.raises(rb.BenchmarkError, match="--execute"):
        rb.cmd_run(args)
    assert not (tmp_path / "x").exists()


def test_limit_selection_is_deterministic_and_covers_categories():
    tasks = json.loads((BENCH / "tasks.json").read_text())
    chosen = rb.select_tasks(tasks, 3)
    assert [t["category"] for t in chosen] == ["single", "multi", "out_of_scope"]
    assert chosen == rb.select_tasks(tasks, 3)
    assert len(rb.select_tasks(tasks, 500)) == 50


# ----------------------------------------------------------------------------- variants / profiles / config

def test_variant_configs_are_set_by_config_only():
    bm = rb.Benchmark(BENCH)
    variants = rb.load_variants(["off", "l1"])
    off = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "off", variants["off"])
    l1 = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1", variants["l1"])
    assert off.verifier.mode == "off" and l1.verifier.mode == "l1_on"
    assert off.domain.profile == "hcmut_academic" and off.retrieval.corpus_path == "data/corpus/hcmut_academic_v1.json"
    assert off.model.provider == "llamacpp" and off.memory.enabled is False
    assert off.retrieval.reranker.enabled is False


def test_run_profiles_are_discovered_from_config_and_define_parallelism_and_reranker_runtime():
    profiles = rb.discover_profiles()
    assert {"mac-latency", "gpu-accuracy"} <= set(profiles)
    mac, gpu = rb.load_run_profile("mac-latency"), rb.load_run_profile("gpu-accuracy")
    assert mac["workers"] == 1 and mac["sequential"] is True and mac["latency_reportable"] is True and mac["warmup_trials"] >= 1
    assert gpu["workers"] == "auto" and gpu["latency_reportable"] is False and gpu["max_workers"] >= 1
    assert mac["reranker"]["backend"] == "llamacpp_http" and mac["reranker"]["base_url"] == "http://127.0.0.1:8082"
    assert (gpu["reranker"]["backend"], gpu["reranker"]["device"], gpu["reranker"]["dtype"]) == ("cross_encoder", "cuda", "float16")


def test_l1_rerank_takes_its_reranker_runtime_from_the_run_profile():
    bm = rb.Benchmark(BENCH)
    spec = rb.load_variants(["l1_rerank"])["l1_rerank"]
    assert rb.variant_needs_reranker(spec) and "backend" not in spec["overrides"]["retrieval"]["reranker"]  # the variant does not pick a runtime
    mac = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1_rerank", spec, profile=rb.load_run_profile("mac-latency")).retrieval.reranker
    gpu = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1_rerank", spec, profile=rb.load_run_profile("gpu-accuracy")).retrieval.reranker
    assert (mac.enabled, mac.backend, mac.base_url, mac.top_k_in, mac.top_k_out, mac.max_length) == (True, "llamacpp_http", "http://127.0.0.1:8082", 20, 5, 1024)
    expected_model = os.environ.get("RERANKER_MODEL_DIR") or "AITeamVN/Vietnamese_Reranker"   # profile: ${RERANKER_MODEL_DIR:-AITeamVN/Vietnamese_Reranker}
    assert (gpu.enabled, gpu.backend, gpu.model, gpu.device, gpu.dtype, gpu.local_files_only, gpu.top_k_in, gpu.top_k_out) == (
        True, "cross_encoder", expected_model, "cuda", "float16", True, 20, 5)


def test_reranking_variant_without_a_profile_runtime_or_with_a_conflict_is_refused(tmp_path):
    bm = rb.Benchmark(BENCH)
    spec = rb.load_variants(["l1_rerank"])["l1_rerank"]
    with pytest.raises(rb.ConfigError, match="no `reranker:` runtime"):
        rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1_rerank", spec, profile=None)
    bare = {**rb.load_run_profile("mac-latency")}
    bare.pop("reranker")
    with pytest.raises(rb.ConfigError, match="no `reranker:` runtime"):
        rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1_rerank", spec, profile=bare)
    conflicting = {**rb.load_run_profile("mac-latency"), "reranker": {"backend": "llamacpp_http", "base_url": "http://127.0.0.1:8082", "top_k_in": 10}}
    with pytest.raises(rb.ConfigError, match="top_k_in"):
        rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1_rerank", spec, profile=conflicting)
    # off / l1 never need a reranker runtime
    rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1", rb.load_variants(["l1"])["l1"], profile=bare)


def test_unsupported_override_key_is_a_config_error_not_silently_dropped():
    bm = rb.Benchmark(BENCH)
    spec = {"verification_mode": "l1_on", "overrides": {"retrieval": {"definitely_not_a_key": True}}}
    with pytest.raises(rb.ConfigError, match="not supported"):
        rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "x", spec)


def test_model_env_overrides_are_refused():
    # A real child process with the override in its environment; nothing in this process is patched.
    code = ("from evaluation import run_benchmark as rb; from pathlib import Path; import sys\n"
            "bm = rb.Benchmark(Path(sys.argv[1]))\n"
            "try:\n"
            "    rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, 'off', rb.load_variants(['off'])['off'])\n"
            "except rb.ConfigError as exc:\n"
            "    print('REFUSED', exc); sys.exit(0)\n"
            "sys.exit(3)\n")
    env = {**os.environ, "MODEL_NAME": "some-other-model", "PYTHONPATH": str(REPO)}
    result = subprocess.run([sys.executable, "-c", code, str(BENCH)], cwd=REPO, env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and "Environment overrides" in result.stdout, result.stdout + result.stderr


def test_warmup_questions_cover_both_benchmarks_and_are_never_benchmark_tasks():
    warm = rb.load_warmup_questions()
    profile = rb.load_run_profile("mac-latency")
    for name in ("hcmut_v1", "labour_vi_v1"):
        tasks = {t["question"] for t in json.loads((REPO / "evaluation" / "benchmarks" / name / "tasks.json").read_text())}
        assert len(warm[name]) >= profile["warmup_trials"] and not (set(warm[name]) & tasks)


def test_matrix_config_is_the_900_trial_d2_plan():
    import yaml
    matrix = yaml.safe_load((REPO / "config" / "benchmark" / "d2_matrix.yaml").read_text())
    assert matrix["benchmarks"] == ["hcmut_v1", "labour_vi_v1"] and matrix["variants"] == ["off", "l1", "l1_rerank"]  # "off" is the string, not False
    assert matrix["seeds"] == [42, 123, 2026]
    trials = sum(len(json.loads((REPO / "evaluation" / "benchmarks" / b / "tasks.json").read_text())) for b in matrix["benchmarks"])
    assert trials * len(matrix["variants"]) * len(matrix["seeds"]) == 900


# ----------------------------------------------------------------------------- rows, preflight, failure handling (real failures)

def test_read_rows_ignores_a_truncated_last_line_but_never_a_corrupt_middle_line(tmp_path):
    source = rb.trials_path(REPO / "evaluation" / "runs" / "bench-smoke-both-20261023")
    lines = source.read_text().splitlines(keepends=True)
    truncated = tmp_path / "trials.jsonl"
    truncated.write_text("".join(lines[:3]) + lines[3][: len(lines[3]) // 2])
    assert len(rb.read_rows(truncated)) == 3
    fragment = rb.repair_partial_tail(truncated)
    assert fragment and Path(fragment).read_text() == lines[3][: len(lines[3]) // 2]  # the fragment is kept, not deleted
    assert truncated.read_text() == "".join(lines[:3]) and rb.repair_partial_tail(truncated) is None
    corrupt = tmp_path / "corrupt.jsonl"
    corrupt.write_text(lines[0] + "{not json}\n" + lines[1])
    with pytest.raises(rb.BenchmarkError, match="not the last line"):
        rb.read_rows(corrupt)


@needs_server
def test_preflight_exercises_the_real_controller_and_records_its_identity(tmp_path):
    code = rb.main(["preflight", "--benchmark", str(BENCH), "--variants", "off,l1", "--limit", "3", "--allow-unfrozen", "--allow-busy"])
    assert code == 0
    from evaluation import bench_preflight
    plan = rb.resolve_plan(rb.build_parser().parse_args(
        ["preflight", "--benchmark", str(BENCH), "--variants", "off,l1", "--limit", "3", "--allow-unfrozen", "--allow-busy"]))
    report = bench_preflight.run(plan)
    names = {c["name"]: c for c in report["checks"]}
    assert report["ok"] and names["controller_gguf_sha256"]["ok"] and names["controller_llama_cpp_build"]["ok"]
    assert report["server"]["model_file_sha256"] == bench_preflight.expected_server()["gguf_sha256"]
    assert report["seed_canary"]["different_seed_differs"] is True  # the server honours the per-request seed
    assert report["git"]["commit"] and isinstance(report["git"]["dirty"], bool)
    assert not any(n.startswith("reranker") for n in names)  # no reranking variant selected: no reranker dependency


@needs_server
def test_preflight_refuses_when_the_reranker_server_is_unreachable(tmp_path):
    import yaml
    profile = rb.load_run_profile("mac-latency")
    profile.pop("_path")
    profile["name"] = "mac-latency-unreachable-reranker"
    profile["reranker"] = {"backend": "llamacpp_http", "base_url": "http://127.0.0.1:1"}  # nothing listens on port 1: a real refusal
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump(profile))
    argv = ["preflight", "--benchmark", str(BENCH), "--variants", "l1_rerank", "--limit", "3", "--allow-unfrozen", "--allow-busy", "--run-profile", str(path), "--skip-canary"]
    assert rb.main(argv) == 1
    from evaluation import bench_preflight
    report = bench_preflight.run(rb.resolve_plan(rb.build_parser().parse_args(argv)))
    assert not report["ok"] and "reranker_server_health" in report["failed"]
    # and the run itself refuses before writing anything
    out = tmp_path / "never"
    assert rb.main(["run", "--benchmark", str(BENCH), "--variants", "l1_rerank", "--limit", "3", "--allow-unfrozen", "--allow-busy", "--run-profile", str(path),
                    "--skip-canary", "--execute", "--output", str(out)]) == 1 and not out.exists()


def agent_for(variant="off", endpoint=None):
    from src.agent.loop import LuatCheckAgent
    bm = rb.Benchmark(BENCH)
    spec = rb.load_variants([variant])[variant]
    cfg = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, variant, spec, endpoint=endpoint, profile=rb.load_run_profile("mac-latency"))
    return LuatCheckAgent(config=cfg, verification_mode=spec["verification_mode"], l2_use_slm=False)


def trial(agent, question, timeout=120.0):
    task = {"task_id": "T-REAL", "category": "single", "question": question, "expected_behavior": "answer", "ground_truth_article_ids": []}
    return rb.execute_trial(agent, "hcmut_v1", "off", "off", task, 42, run_profile="mac-latency", latency_reportable=True, worker=0, attempt=1,
                            sampler=None, provider="llamacpp", timeout_seconds=timeout)


def test_a_dead_backend_is_an_outage_that_is_retried_and_counts_toward_the_stop_rule():
    agent = agent_for(endpoint="http://127.0.0.1:1/v1")  # connection refused: a real backend failure, no model involved
    row = trial(agent, "Sinh viên được đăng ký tối đa bao nhiêu tín chỉ?")
    assert row["system_error"] and row["terminal_status"] == "error" and row["error_kind"] == "backend_error"
    assert row["native_calls"] >= 1 and row["successful_native_calls"] == 0  # an error, never an answer or refusal
    row["error_diagnosis"] = rb.diagnose_error(row, "http://127.0.0.1:1", None)
    assert row["error_diagnosis"]["dependency_healthy_after_error"] is False and rb.is_outage(row)


@needs_server
def test_a_request_rejected_by_a_healthy_server_is_not_an_outage():
    """A prompt far beyond the context makes the real llama-server answer HTTP 400 while staying healthy (context overflow)."""
    agent = agent_for()
    row = trial(agent, "tín chỉ " * 60000)
    assert row["system_error"] and row["error_kind"] == "backend_error", row["terminal_status"]
    row["error_diagnosis"] = rb.diagnose_error(row, "http://127.0.0.1:8081", None)
    assert row["error_diagnosis"]["dependency_healthy_after_error"] is True and row["error_diagnosis"]["http_status"] == 400
    assert not rb.is_outage(row)  # not retried, does not trip the consecutive-outage stop


@needs_server
def test_trial_watchdog_records_a_timeout_error_row_and_marks_the_agent_for_disposal():
    agent = agent_for()
    row = trial(agent, "Sinh viên bị buộc thôi học trong những trường hợp nào?", timeout=0.05)
    assert row["system_error"] and row["error_kind"] == "runner_trial_timeout" and "TrialTimeout" in row["runner_exception"]
    assert row["terminal_status"] == "error" and not rb.is_outage(row)  # a hang is a result, not an outage to retry


# ----------------------------------------------------------------------------- real smoke run

@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory):
    if not server_up():
        pytest.fail(SERVER_DOWN)
    out = tmp_path_factory.mktemp("bench") / "smoke"
    code = rb.main(["run", "--benchmark", str(BENCH), "--variants", "off,l1", "--seeds", "42", "--limit", "2",
                    "--allow-unfrozen", "--allow-busy", "--execute", "--output", str(out)])
    assert code == 0
    return out


@needs_server
def test_smoke_run_produces_rows_in_the_run_eval_schema(smoke_run):
    manifest = json.loads((smoke_run / "manifest.json").read_text())
    rows = rb.read_rows(smoke_run / "trials.jsonl")
    assert len(rows) == 4 and manifest["planned_trials"] == 4 and manifest["status"] == "collected"
    assert {(r["variant"], r["task_id"]) for r in rows} == {(v, t) for v in ("off", "l1") for t in ("HCMUT-001", "HCMUT-021")}
    for row in rows:
        assert RUN_ROW_KEYS <= set(row)
        assert row["benchmark"] == "hcmut_v1" and row["mode"] == row["variant"] and row["seed"] == 42
        assert row["terminal_status"] in {"answered", "refused", "clarified", "error"}
        assert row["wall_ms"] > 0 and row["native_calls"] == len(row["calls"]) == len(row["ledger"]["llm_calls"])
        assert all(c["backend"] == "llamacpp" for c in row["ledger"]["llm_calls"])
        assert row["system_error"] is False, row["error_message"]  # a failure here means the live server is unhealthy
        assert row["latency_reportable"] is True and row["run_profile"] == "mac-latency"
        assert row["token_usage_complete"] and row["input_tokens"] > 0
        assert set(row["retrieval"]) >= {"Recall@1", "Recall@5", "MRR"} and "citation_precision" in row["citation"]
    assert manifest["phase"] == "smoke" and manifest["report_eligible"] is False
    assert manifest["server"]["model_alias"] == "prism-ml/Ternary-Bonsai-2-2B-gguf"
    assert manifest["git"]["commit"] and isinstance(manifest["git"]["dirty"], bool)
    assert manifest["hardware"]["machine"] and manifest["run_profile"]["name"] == "mac-latency"
    assert manifest["peak_memory_mb"]["runner_ru_maxrss"] > 0
    # D2 batch-runner evidence: identity of what served the run, fingerprint, warm-up kept apart, progress file
    assert manifest["preflight"]["ok"] and manifest["server"]["model_file_sha256"] and manifest["trial_timeout_seconds"] == 300
    assert manifest["fingerprint"]["must_match"]["controller_model_file_sha256"] == manifest["server"]["model_file_sha256"]
    assert manifest["sources"]["collection_sha256"] and "src/agent/loop.py" in manifest["sources"]["collection_files"]
    warm = rb.read_rows(smoke_run / "warmup.jsonl")
    assert len(warm) == 4 and all(w["warmup"] is True and w["seed"] == 0 and w["task_id"].startswith("WARMUP") for w in warm)  # 2 per agent x 2 agents
    assert not any(r["warmup"] for r in rows)  # warm-up never enters the trials file
    progress = json.loads((smoke_run / "progress.json").read_text())
    assert progress["completed_this_session"] == 4 == progress["to_run_this_session"]
    for relative, digest in manifest["sources"]["files_sha256"].items():
        assert sha(smoke_run / "source_snapshot" / relative) == digest
    assert manifest["runs_sha256"] == sha(smoke_run / "trials.jsonl")


@needs_server
def test_resume_skips_completed_rows_and_never_overwrites(smoke_run, tmp_path):
    work = tmp_path / "resume"
    shutil.copytree(smoke_run, work)
    lines = (work / "trials.jsonl").read_text().splitlines(keepends=True)
    (work / "trials.jsonl").write_text("".join(lines[:2]) + lines[2][:200])  # a crash: 2 complete rows and a half-written third
    args = ["run", "--benchmark", str(BENCH), "--variants", "off,l1", "--seeds", "42", "--limit", "2", "--allow-unfrozen",
            "--allow-busy", "--execute", "--output", str(work)]
    assert rb.main(args) == 1  # existing directory without --resume is refused
    assert (work / "trials.jsonl").read_text() == "".join(lines[:2]) + lines[2][:200]
    assert rb.main(args + ["--resume"]) == 0
    assert list(work.glob("trials.jsonl.partial-*"))  # the half-written row was set aside, not deleted
    resumed = (work / "trials.jsonl").read_text().splitlines(keepends=True)
    assert len(resumed) == 4 and resumed[:2] == lines[:2]  # first rows are byte-identical, only missing ones were added
    assert len({rb.trial_key(json.loads(line)) for line in resumed}) == 4
    manifest = json.loads((work / "manifest.json").read_text())
    assert len(manifest["resumes"]) == 1 and manifest["status"] == "collected"
    before = (work / "trials.jsonl").read_text()
    assert rb.main(args + ["--resume"]) == 0  # nothing left to do
    assert (work / "trials.jsonl").read_text() == before
    assert rb.main(args + ["--resume", "--seeds", "7"]) == 1  # different protocol (seeds): refused
    manifest["sources"]["files_sha256"]["src/agent/loop.py"] = "0" * 64  # simulate code drift since the run started
    (work / "manifest.json").write_text(json.dumps(manifest))
    assert rb.main(args + ["--resume"]) == 1  # drifted sources: refused
    assert (work / "trials.jsonl").read_text() == before


@needs_server
def test_judge_packets_are_blinded_and_source_complete(smoke_run, tmp_path):
    work = tmp_path / "judge-run"
    shutil.copytree(smoke_run, work)
    info = jb.build_packets(work)
    assert info["packets"] == 4 and info["execution_errors_not_judged"] == 0
    packets = json.loads((work / "judge" / "judge_packets.json").read_text())
    mapping = {m["review_id"]: m for m in json.loads((work / "judge" / "private_mapping.json").read_text())}
    assert len({p["review_id"] for p in packets}) == 4 and set(mapping) == {p["review_id"] for p in packets}
    corpus = {rb.record_id(r): r for r in json.loads((REPO / "data/corpus/hcmut_academic_v1.json").read_text())}
    tasks = {t["task_id"]: t for t in json.loads((BENCH / "tasks.json").read_text())}
    allowed = {"review_id", "question", "scope", "expected_behavior", "reference_answer", "reference_evidence",
               "candidate_behavior", "candidate_answer", "candidate_citations", "source_articles", "unknown_citation_ids"}
    for packet in packets:
        assert set(packet) == allowed  # no variant, seed, benchmark, mode, repair or timing fields
        meta = mapping[packet["review_id"]]
        task = tasks[meta["task_id"]]
        assert packet["question"] == task["question"] and packet["reference_answer"] == task["expected_answer"]
        shipped = {a["article_id"]: a for a in packet["source_articles"]}
        for gold in task["ground_truth_article_ids"]:
            assert shipped[gold]["content"] == corpus[gold]["content"]  # full record text, not a snippet
        for cited in packet["candidate_citations"]:
            assert cited["article_id"] in shipped or cited["article_id"] in packet["unknown_citation_ids"]
    assert {m["variant"] for m in mapping.values()} == {"off", "l1"}
    # packets are immutable: rebuilding yields identical packets
    first = (work / "judge" / "judge_packets.json").read_text()
    jb.build_packets(work)
    assert (work / "judge" / "judge_packets.json").read_text() == first


@needs_server
def test_judge_requires_execute_and_analysis_does_not_invent_judgments(smoke_run, tmp_path):
    work = tmp_path / "analyze-run"
    shutil.copytree(smoke_run, work)
    with pytest.raises(ValueError, match="--execute"):
        jb.run_judge(work, REPO / jb.DEFAULT_JUDGE_CONFIG, execute=False)
    jb.build_packets(work)
    summary = jb.analyze(work, audit_size=3)  # no judge was called: nothing may look judged
    assert summary["report_eligible"] is False and summary["human_labels_received"] is False
    assert summary["judge_cost_total"]["attempts"] == 0
    for cell in summary["cells"].values():
        assert cell["trials_recorded"] == 2 and cell["strict_success"]["unknown"] == 2
        assert cell["strict_success"]["successes"] == 0 and cell["claim_faithfulness"]["rate"] is None
        assert cell["judging"]["judged_valid"] == 0
        assert cell["latency"]["reportable"] is True and cell["latency"]["trial_p50_s"] > 0
        assert cell["retrieval"]["Recall@5"] is not None and cell["tokens"]["input_per_trial"] > 0
    labels = (work / "analysis" / "human-audit" / "labels.csv").read_text().splitlines()
    assert labels[0].startswith("review_id,reviewer") and len(labels) == 1  # nothing eligible to audit yet; no labels invented


@needs_server
def test_render_marks_non_eligible_runs_and_shows_missing_cells_as_red(smoke_run, tmp_path):
    work = tmp_path / "render-run"
    shutil.copytree(smoke_run, work)
    jb.build_packets(work)
    jb.analyze(work, audit_size=3)
    with pytest.raises(SystemExit):  # a smoke run must never reach the report file
        render.main(["--run-dir", str(work)])
    report_file = REPO / "report_d2" / "benchmark_results.tex"
    report_before = report_file.read_bytes() if report_file.exists() else None
    out = tmp_path / "tables.tex"
    assert render.main(["--run-dir", str(work), "--output", str(out), "--allow-non-eligible"]) == 0
    tex = out.read_text()
    assert "NON-ELIGIBLE RUN" in tex and "not human labels" in tex
    assert tex.count(r"\textcolor{red}{\textbf{[PENDING]}}") > 8  # unjudged cells, l1_rerank and labour_vi_v1 are red placeholders
    assert "tab:benchmark-main" in tex and "Labour-VI-v1" in tex
    assert (report_file.read_bytes() if report_file.exists() else None) == report_before  # report file untouched

# ----------------------------------------------------------------------------- strata, gold counts, sanity prompts (benchmark QA findings)

def test_strata_lists_equal_the_verdicts_of_the_recorded_closed_book_probes():
    import yaml
    cfg = yaml.safe_load((REPO / "config" / "benchmark" / "strata.yaml").read_text())
    for name, source in cfg["sources"].items():
        path = REPO / source["path"]
        assert sha(path) == source["sha256"], f"{source['path']} changed since the strata were derived"
        data = json.loads(path.read_text())
        if source["layout"] == "sanity_rows":
            verdict = {r["task_id"]: (r["closed_book"]["judgment"] or {}).get("verdict") for r in data["rows"] if r["expected_behavior"] == "answer"}
        else:
            verdict = {r["task_id"]: (r["judgment"] or {}).get("verdict") for r in data["rows"]}
        assert set(cfg["strata"][name]["closed_book_guessable"]) == {t for t, v in verdict.items() if v == "correct"}
        assert set(cfg["strata"][name]["closed_book_partial"]) == {t for t, v in verdict.items() if v == "partially_correct"}
        tasks = {t["task_id"]: t for t in json.loads((REPO / "evaluation" / "benchmarks" / name / "tasks.json").read_text())}
        assert all(tasks[t]["expected_behavior"] == "answer" for ids in cfg["strata"][name].values() for t in ids)  # refusal tasks have no closed-book stratum


def test_stratum_assignment_never_assumes_category_implies_one_gold_id():
    from evaluation import judge_benchmark as jb
    strata = jb.load_strata(REPO)
    tasks = {t["task_id"]: t for t in json.loads((REPO / "evaluation" / "benchmarks" / "labour_vi_v1" / "tasks.json").read_text())}
    for tid in ("LVN-014", "LVN-016", "LVN-019"):   # `single` tasks with two gold records (benchmark QA review)
        assert tasks[tid]["category"] == "single" and len(tasks[tid]["ground_truth_article_ids"]) == 2
    assert jb.stratum_of(strata, "labour_vi_v1", tasks["LVN-016"]) == "closed_book_guessable"
    assert jb.stratum_of(strata, "labour_vi_v1", tasks["LVN-019"]) == "closed_book_partial"
    assert jb.stratum_of(strata, "labour_vi_v1", tasks["LVN-014"]) == "closed_book_unsolved"
    assert jb.stratum_of(strata, "labour_vi_v1", tasks["LVN-024"]) == "refusal_task"
    assert jb.stratum_group(strata, "closed_book_partial") == "not_guessable" and jb.stratum_group(strata, "closed_book_guessable") == "guessable"
    # recall of a 2-gold `single` task is out of 2, not out of 1
    from evaluation import metrics
    assert metrics.calculate_retrieval_metrics(["a"], ["a", "b"])["Recall@5"] == 0.5


def test_sanity_prompts_come_from_the_domain_profile_not_from_hcmut():
    from evaluation import benchmark_sanity as sanity
    labour = sanity.build_prompts(sanity.domain_display_name(REPO / "evaluation" / "benchmarks" / "labour_vi_v1"))
    hcmut = sanity.build_prompts(sanity.domain_display_name(REPO / "evaluation" / "benchmarks" / "hcmut_v1"))
    for text in labour.values():
        assert "Bách khoa" not in text and "học vụ" not in text and "Pháp luật lao động" in text
    for text in hcmut.values():
        assert "Bách khoa" in text and "Pháp luật lao động" not in text
    assert "Pháp luật lao động" in sanity.build_prompts("Pháp luật lao động Việt Nam")["judge_system"] and '"verdict"' in labour["judge_system"]


# ----------------------------------------------------------------------------- diagnostic baselines (closed-book, oracle)

def test_baselines_are_configured_separately_with_the_agreed_trial_counts():
    import yaml
    baselines = rb.load_baselines(["closed_book", "oracle"])
    assert baselines["closed_book"]["tasks"] == "all" and baselines["oracle"]["tasks"] == "answerable"
    assert baselines["closed_book"]["seeds"] == baselines["oracle"]["seeds"] == [42]
    assert set(rb.load_variants(["off", "l1", "l1_rerank"])).isdisjoint(baselines)   # never a system variant
    assert yaml.safe_load((REPO / "config" / "benchmark" / "d2_matrix.yaml").read_text())["baselines"] == ["closed_book", "oracle"]
    counts = {}
    for name in ("hcmut_v1", "labour_vi_v1"):
        bm = rb.Benchmark(REPO / "evaluation" / "benchmarks" / name)
        counts[name] = {b: len(rb.baseline_tasks(bm, spec, None)) for b, spec in baselines.items()}
        answerable = [t for t in bm.load_tasks() if t["expected_behavior"] == "answer"]
        assert all(t["ground_truth_article_ids"] for t in rb.baseline_tasks(bm, baselines["oracle"], None))   # refuse tasks (no gold context) excluded
        assert len(answerable) == counts[name]["oracle"] == 45 and counts[name]["closed_book"] == 50
    with pytest.raises(rb.BenchmarkError, match="collide|Unknown"):
        rb.load_baselines(["off"])


def test_restricted_action_schema_and_validation_have_no_tool_branch():
    from src.agent.llm_client import LlamaCppLLMClient, InferenceError
    from src.domains import load_profile
    client = LlamaCppLLMClient(endpoint="http://127.0.0.1:1/v1", profile=load_profile("hcmut_academic"))
    assert len(client.action_schema["anyOf"]) == 5   # default unchanged
    client.restrict_actions(["answer", "clarify", "refuse"])
    assert [b["properties"]["action"]["const"] for b in client.action_schema["anyOf"]] == ["answer", "clarify", "refuse"]
    client.validate_action({"thought": "t", "action": "refuse", "tool_args": {"reason": "r"}})
    with pytest.raises(InferenceError) as excinfo:
        client.validate_action({"thought": "t", "action": "search", "tool_args": {"query": "q"}})
    assert excinfo.value.kind == "model_output_error"


def baseline_agent(kind, benchmark="hcmut_v1"):
    from evaluation.baselines import build_baseline_agent
    bm = rb.Benchmark(REPO / "evaluation" / "benchmarks" / benchmark)
    spec = rb.load_baselines([kind])[kind]
    cfg = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, kind, spec, profile=rb.load_run_profile("mac-latency"))
    return build_baseline_agent(cfg, spec), bm


def test_oracle_context_is_the_real_read_observation_and_closed_book_has_no_documents():
    corpus = {rb.record_id(r): r for r in json.loads((REPO / "data/corpus/hcmut_academic_v1.json").read_text())}
    task = next(t for t in json.loads((BENCH / "tasks.json").read_text()) if len(t["ground_truth_article_ids"]) == 2)   # a multi-gold task
    from src.agent.state import CaseLedger
    oracle, _ = baseline_agent("oracle")
    oracle.prepare_trial(task)
    ledger = CaseLedger(session_id="t", original_query=task["question"])
    messages = oracle._initial_messages(task["question"], None, ledger)
    assert [m["role"] for m in messages] == ["system", "user"] and "KHÔNG có công cụ" in messages[0]["content"]
    assert messages[0]["content"].startswith(oracle.profile.system_prompt.rstrip())   # the domain prompt, plus the disclosed note
    blocks = [b for b in messages[1]["content"].split("[OBSERVATION_TOOL_RESULT]\n")[1:]]
    assert len(blocks) == 2
    for gold_id, block in zip(task["ground_truth_article_ids"], blocks):
        observation = json.loads(block.strip())
        assert observation["status"] == "success" and observation["full_content"] == corpus[gold_id]["content"]   # full text, read-tool format
    assert ledger.retrieved_article_ids == task["ground_truth_article_ids"] and ledger.tool_calls_count == 0
    assert ledger.audit_events[-1]["event"] == "oracle_context"   # recorded as given context, not as a tool call
    closed, _ = baseline_agent("closed_book")
    assert not hasattr(closed, "prepare_trial") and closed.uses_gold is False and oracle.uses_gold is True   # closed-book has no gold entry point at all
    ledger = CaseLedger(session_id="t2", original_query=task["question"])
    messages = closed._initial_messages(task["question"], None, ledger)
    joined = "\n".join(m["content"] for m in messages)
    assert all(corpus[g]["content"][:80] not in joined for g in task["ground_truth_article_ids"]) and ledger.retrieved_article_ids == []


@needs_server
def test_baselines_run_on_real_inference_without_tools():
    tasks = {t["task_id"]: t for t in json.loads((BENCH / "tasks.json").read_text())}
    task = tasks["HCMUT-003"]
    for kind in ("closed_book", "oracle"):
        agent, bm = baseline_agent(kind)
        row = rb.execute_trial(agent, "hcmut_v1", kind, "off", task, 42, run_profile="mac-latency", latency_reportable=True, worker=0,
                               attempt=1, sampler=None, provider="llamacpp", kind=kind)
        assert row["system_error"] is False, row["error_message"]
        assert row["kind"] == kind and row["variant"] == kind and row["native_calls"] >= 1
        assert row["terminal_status"] in {"answered", "refused", "clarified"}
        assert not [e for e in row["ledger"]["audit_events"] if e.get("event") == "tool_call"]   # no search / read happened
        assert all(c["backend"] == "llamacpp" for c in row["ledger"]["llm_calls"])
        assert row["ledger"]["retrieved_article_ids"] == (task["ground_truth_article_ids"] if kind == "oracle" else [])
