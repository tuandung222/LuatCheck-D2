"""Benchmark runner tests on real components: the real hcmut_v1 files, the real agent and the running llama-server.

No mocks, stand-ins or canned model output. Temporary directories hold copies of the real benchmark files and run
outputs. The paid judge is never called here. Tests that need native inference skip (never fake) when the
llama-server on 127.0.0.1:8081 is not reachable.
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
RUN_ROW_KEYS = {"task_id", "seed", "mode", "expected_behavior", "terminal_status", "gold_article_ids", "system_error",
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


# ----------------------------------------------------------------------------- variants / config

def test_variant_configs_are_set_by_config_only():
    bm = rb.Benchmark(BENCH)
    variants = rb.load_variants(["off", "l1"])
    off = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "off", variants["off"])
    l1 = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1", variants["l1"])
    assert off.verifier.mode == "off" and l1.verifier.mode == "l1_on"
    assert off.domain.profile == "hcmut_academic" and off.retrieval.corpus_path == "data/corpus/hcmut_academic_v1.json"
    assert off.model.provider == "llamacpp" and off.memory.enabled is False
    assert off.retrieval.reranker.enabled is False


def test_l1_rerank_uses_the_reranker_keys_or_fails_with_a_config_error():
    bm = rb.Benchmark(BENCH)
    spec = rb.load_variants(["l1_rerank"])["l1_rerank"]
    from src.config.app_config import RetrievalConfig
    if "reranker" in RetrievalConfig.model_fields:
        cfg = rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1_rerank", spec)
        rr = cfg.retrieval.reranker
        assert (rr.enabled, rr.backend, rr.model, rr.top_k_in, rr.top_k_out, rr.max_length) == (
            True, "cross_encoder", "AITeamVN/Vietnamese_Reranker", 20, 5, 1024)
        assert cfg.verifier.mode == "l1_on"
    else:
        with pytest.raises(rb.ConfigError, match="not supported"):
            rb.build_variant_config(rb.DEFAULT_MODEL_CONFIG, bm, "l1_rerank", spec)


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


# ----------------------------------------------------------------------------- real smoke run

@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory):
    if not server_up():
        pytest.fail(SERVER_DOWN)
    out = tmp_path_factory.mktemp("bench") / "smoke"
    code = rb.main(["run", "--benchmark", str(BENCH), "--variants", "off,l1", "--seeds", "42", "--limit", "2",
                    "--allow-unfrozen", "--execute", "--output", str(out)])
    assert code == 0
    return out


@needs_server
def test_smoke_run_produces_rows_in_the_run_eval_schema(smoke_run):
    manifest = json.loads((smoke_run / "manifest.json").read_text())
    rows = rb.read_rows(smoke_run / "runs.jsonl")
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
    for relative, digest in manifest["sources"]["files_sha256"].items():
        assert sha(smoke_run / "source_snapshot" / relative) == digest
    assert manifest["runs_sha256"] == sha(smoke_run / "runs.jsonl")


@needs_server
def test_resume_skips_completed_rows_and_never_overwrites(smoke_run, tmp_path):
    work = tmp_path / "resume"
    shutil.copytree(smoke_run, work)
    lines = (work / "runs.jsonl").read_text().splitlines(keepends=True)
    (work / "runs.jsonl").write_text("".join(lines[:2]))  # simulate an interrupted collection (first 2 rows recorded)
    args = ["run", "--benchmark", str(BENCH), "--variants", "off,l1", "--seeds", "42", "--limit", "2", "--allow-unfrozen",
            "--execute", "--output", str(work)]
    assert rb.main(args) == 1  # existing directory without --resume is refused
    assert (work / "runs.jsonl").read_text() == "".join(lines[:2])
    assert rb.main(args + ["--resume"]) == 0
    resumed = (work / "runs.jsonl").read_text().splitlines(keepends=True)
    assert len(resumed) == 4 and resumed[:2] == lines[:2]  # first rows are byte-identical, only missing ones were added
    assert len({rb.trial_key(json.loads(line)) for line in resumed}) == 4
    manifest = json.loads((work / "manifest.json").read_text())
    assert len(manifest["resumes"]) == 1 and manifest["status"] == "collected"
    before = (work / "runs.jsonl").read_text()
    assert rb.main(args + ["--resume"]) == 0  # nothing left to do
    assert (work / "runs.jsonl").read_text() == before
    assert rb.main(args + ["--resume", "--seeds", "7"]) == 1  # different protocol (seeds): refused


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
