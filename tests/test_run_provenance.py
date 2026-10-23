"""Experiment tracking on REAL recorded runs: provenance, registry freshness, table provenance headers, report check.

No run is invented. Positive "current / eligible" cases use a temporary COPY of the recorded smoke run
evaluation/runs/bench-smoke-baselines-rerank-20261024 whose manifest/summary fields are re-pointed at the current checkout (that is the
mutation the test is about); negative cases mutate one field of such a copy. The real evaluation/runs directory is never written.
"""
import json
import shutil
from pathlib import Path

import pytest

from evaluation import check_report_provenance as check
from evaluation import provenance, registry
from evaluation import render_benchmark_tables as render
from evaluation import run_benchmark as rb

REPO = Path(__file__).resolve().parents[1]
REAL = REPO / "evaluation" / "runs"
SMOKE = REAL / "bench-smoke-baselines-rerank-20261024"
BENCH = REPO / "evaluation" / "benchmarks" / "hcmut_v1"


def current_looking_copy(tmp_path, name="d2-copy-main-v1") -> Path:
    """Copy of the recorded smoke run, re-pointed at HEAD so the registry sees a complete, eligible, main run of this checkout."""
    runs = tmp_path / "runs"
    runs.mkdir(exist_ok=True)
    run = runs / name
    shutil.copytree(SMOKE, run)
    manifest = json.loads((run / "manifest.json").read_text())
    benchmarks = [rb.Benchmark(Path(b["tasks_path"]).parent) for b in manifest["benchmarks"]]
    paths = rb.collection_paths(benchmarks, Path(manifest["model_config"]["path"]),
                                {"_path": manifest["run_profile"].get("_path") or str(rb.discover_profiles()[manifest["run_profile"]["name"]].relative_to(REPO))})
    manifest["sources"]["collection_files"] = paths
    manifest["sources"]["files_sha256"].update({p: rb.sha256_file(p) for p in paths})
    manifest.update(kind="main", phase="main", harness_version=provenance.HARNESS_VERSION, run_state="complete", run_id=name)
    manifest["provenance"] = {"git": {"commit": "a" * 40, "source": "git", "on_origin": True}}
    for entry in manifest["benchmarks"]:
        lock = Path("evaluation/benchmarks") / entry["name"] / "benchmark.lock.json"
        entry["lock_sha256"] = rb.sha256_file(lock) if lock.is_file() else None
    (run / "manifest.json").write_text(json.dumps(manifest))
    summary = json.loads((run / "analysis" / "summary.json").read_text())
    summary.update(report_eligible=True, run_id=name)
    (run / "analysis" / "summary.json").write_text(json.dumps(summary))
    return run


def rendered_report(tmp_path, run: Path, extra_tex: str = "") -> Path:
    out = tmp_path / "report"
    out.mkdir(exist_ok=True)
    assert render.main(["--run-dir", str(run), "--output", str(out / "benchmark_results.tex"), "--expect-variants", "off,l1_rerank"]) == 0
    (out / "main.tex").write_text("\\documentclass{article}\\begin{document}\\input{benchmark_results}\\input{benchmark_diagnostics}\n" + extra_tex + "\\end{document}\n")
    return out / "main.tex"


# ----------------------------------------------------------------------------- provenance gate

def test_harness_version_is_semver_and_git_facts_are_real():
    assert len(provenance.HARNESS_VERSION.split(".")) == 3 and provenance.major_minor(provenance.HARNESS_VERSION) == ".".join(provenance.HARNESS_VERSION.split(".")[:2])
    git = provenance.git_info()
    assert git["available"] and len(git["commit"]) == 40 and git["branch"] and "github.com" in (git["remote"] or "")
    assert isinstance(git["dirty_collection_paths"], list) and isinstance(git["on_origin"], bool)
    host = provenance.host_record()
    assert host["hostname"] and host["python"] and "numpy" in host["packages"]


def test_main_run_rules_on_real_and_altered_git_facts():
    git = provenance.git_info()
    sha = "0" * 64
    dirty = {**git, "dirty_collection_paths": [" M src/agent/loop.py"], "on_origin": True}
    unpushed = {**git, "dirty_collection_paths": [], "on_origin": False}
    clean = {**git, "dirty_collection_paths": [], "on_origin": True}
    assert any("uncommitted" in p for p in provenance.main_run_problems(dirty, sha, None))
    assert any("not on origin" in p for p in provenance.main_run_problems(unpushed, sha, None))
    assert provenance.main_run_problems(clean, sha, None) == []
    no_git = {"available": False}
    assert any("PROVENANCE.json" in p for p in provenance.main_run_problems(no_git, sha, None))
    stamp = {"collection_sha256": sha, "on_origin": True, "clean_collection_paths": True, "harness_version": provenance.HARNESS_VERSION}
    assert provenance.main_run_problems(no_git, sha, stamp) == []
    assert any("different collection sources" in p for p in provenance.main_run_problems(no_git, "1" * 64, stamp))   # edited after stamping
    assert any("harness" in p for p in provenance.main_run_problems(no_git, sha, {**stamp, "harness_version": "0.1.0"}))


def test_a_main_run_is_refused_before_any_inference_unless_the_tree_is_clean_and_pushed(tmp_path, capsys):
    out = tmp_path / "main-attempt"
    code = rb.main(["run", "--benchmark", str(BENCH), "--variants", "off", "--seeds", "42", "--kind", "main", "--output", str(out), "--execute"])
    assert code == 1 and not out.exists()          # nothing written, whatever the reason
    git = provenance.git_info()
    if git["dirty_collection_paths"] or not git["on_origin"]:
        assert "clean tree and a pushed commit" in capsys.readouterr().err
    smoke = rb.build_parser().parse_args(["run", "--benchmark", str(BENCH), "--limit", "2", "--allow-unfrozen", "--output", str(out), "--kind", "main", "--execute"])
    with pytest.raises(rb.BenchmarkError, match="incompatible"):
        rb.cmd_run(smoke)


# ----------------------------------------------------------------------------- registry

def test_registry_marks_recorded_runs_without_touching_them():
    smoke = registry.describe(REAL / "bench-smoke-both-20261023")
    assert smoke["kind"] == "smoke" and smoke["report_eligible"] is False and smoke["freshness"].startswith("stale") and "never report evidence" in smoke["note"]
    old = registry.describe(REAL / "bll2019-main-v1")
    assert old["kind"] == "historical" and old["freshness"].startswith("historical: old D2 protocol") and old["report_eligible"] is False
    assert registry.describe(REAL / "deepseek-judge-recovery-v2")["freshness"].startswith("historical")
    assert registry.describe(REAL / "hcmut-sanity-final-v1")["kind"] == "historical"
    assert registry.describe(REAL / "reranker-parity-2026-10-23")["freshness"].startswith("n/a")


def test_registry_scan_lists_every_run_dir_and_writes_markdown_and_jsonl(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    for name in ("bench-smoke-both-20261023", "bll2019-pilot-v1", "reranker-parity-2026-10-23"):
        (runs / name).symlink_to(REAL / name, target_is_directory=True)
    rows = registry.write_registry(runs)
    assert [r["run"] for r in rows] == sorted(p.name for p in runs.iterdir() if p.is_dir())
    text = (runs / "REGISTRY.md").read_text()
    assert "| bench-smoke-both-20261023 | smoke |" in text and "historical" in text and "Only `report_eligible = yes` AND `current`" in text
    assert len((runs / "registry.jsonl").read_text().splitlines()) == 3


def test_freshness_is_current_only_when_sources_harness_and_locks_match(tmp_path):
    run = current_looking_copy(tmp_path)
    row = registry.describe(run)
    assert row["freshness"] == "current" and row["kind"] == "main" and row["report_eligible"] is True and row["harness_version"] == provenance.HARNESS_VERSION
    manifest = json.loads((run / "manifest.json").read_text())

    changed = json.loads(json.dumps(manifest))
    victim = next(p for p in changed["sources"]["collection_files"] if p.startswith("src/") and p.endswith(".py"))
    changed["sources"]["files_sha256"][victim] = "0" * 64
    (run / "manifest.json").write_text(json.dumps(changed))
    assert registry.describe(run)["freshness"].startswith("stale: 1 collection files changed") and victim in registry.describe(run)["freshness"]

    old_harness = {**manifest, "harness_version": "0.9.0"}
    (run / "manifest.json").write_text(json.dumps(old_harness))
    assert "harness 0.9.0 vs current" in registry.describe(run)["freshness"]
    patch = {**manifest, "harness_version": provenance.major_minor(provenance.HARNESS_VERSION) + ".99"}
    (run / "manifest.json").write_text(json.dumps(patch))
    assert registry.describe(run)["freshness"] == "current"          # a PATCH difference does not invalidate

    bad_lock = json.loads(json.dumps(manifest))
    bad_lock["benchmarks"][0]["lock_sha256"] = "f" * 64
    (run / "manifest.json").write_text(json.dumps(bad_lock))
    assert "benchmark lock of" in registry.describe(run)["freshness"]

    (run / "manifest.json").write_text(json.dumps({**manifest, "run_state": "incomplete"}))
    assert registry.describe(run)["freshness"] == "incomplete (incomplete)"
    (run / "manifest.json").write_text(json.dumps(manifest))
    (run / "RUN_STATUS.json").write_text(json.dumps({"superseded_by": "d2-copy-main-v2"}))
    assert registry.describe(run)["freshness"] == "superseded_by: d2-copy-main-v2"
    (run / "RUN_STATUS.json").write_text(json.dumps({"kind": "historical", "historical": "protocol changed"}))
    assert registry.describe(run)["freshness"] == "historical: protocol changed" and registry.describe(run)["report_eligible"] is False


# ----------------------------------------------------------------------------- table provenance and the report check

def test_every_table_carries_a_provenance_block_and_a_visible_source_line(tmp_path):
    run = current_looking_copy(tmp_path)
    report = rendered_report(tmp_path, run)
    for name in ("benchmark_results.tex", "benchmark_diagnostics.tex"):
        text = (report.parent / name).read_text()
        tables = text.count("\\begin{table}")
        blocks = check.parse_blocks(text)
        assert tables >= 2 and len(blocks) == tables
        for block in blocks:
            assert block["run_id"] == run.name and block["harness_version"] == provenance.HARNESS_VERSION and block["commit"] == "a" * 40
            assert "evaluation/render_benchmark_tables.py" in block["generator"] and block["table"].startswith("tab:benchmark-")
        assert text.count("Source: run") == tables and "harness" in text
    meta = json.loads((report.parent / "PROVENANCE.json").read_text())
    assert meta["run_id"] == run.name and meta["renderer_harness_version"] == provenance.HARNESS_VERSION


def test_report_check_passes_only_for_main_eligible_current_runs(tmp_path):
    run = current_looking_copy(tmp_path)
    report = rendered_report(tmp_path, run)
    result = check.check(report, run.parent)
    assert result["problems"] == [] and {r["run"] for r in result["rows"]} == {run.name} and all(r["freshness"] == "current" for r in result["rows"])
    path = check.write_markdown(report, result)
    assert "Status: **OK**" in path.read_text() and run.name in path.read_text()
    assert check.main(["--report", str(report), "--runs-dir", str(run.parent)]) == 0


def test_report_check_rejects_stale_smoke_tampered_and_mixed_tables(tmp_path):
    run = current_looking_copy(tmp_path)
    report = rendered_report(tmp_path, run)
    good = (report.parent / "benchmark_results.tex").read_text()

    manifest = json.loads((run / "manifest.json").read_text())
    stale = json.loads(json.dumps(manifest))
    victim = next(p for p in stale["sources"]["collection_files"] if p.startswith("src/") and p.endswith(".py"))
    stale["sources"]["files_sha256"][victim] = "0" * 64
    (run / "manifest.json").write_text(json.dumps(stale))
    assert any("not current: stale" in p for p in check.check(report, run.parent)["problems"])      # source changed since the run
    (run / "manifest.json").write_text(json.dumps(manifest))

    (run / "manifest.json").write_text(json.dumps({**manifest, "kind": "smoke"}))
    assert any("only `main` runs" in p for p in check.check(report, run.parent)["problems"])
    (run / "manifest.json").write_text(json.dumps(manifest))

    summary = json.loads((run / "analysis" / "summary.json").read_text())
    (run / "analysis" / "summary.json").write_text(json.dumps({**summary, "report_eligible": False}))
    assert any("not report_eligible" in p for p in check.check(report, run.parent)["problems"])
    (run / "analysis" / "summary.json").write_text(json.dumps({**summary, "runs_sha256": "0" * 64}))
    assert any("changed after the table was rendered" in p for p in check.check(report, run.parent)["problems"])
    (run / "analysis" / "summary.json").write_text(json.dumps(summary))

    (report.parent / "benchmark_results.tex").write_text(good.replace("% commit: " + "a" * 40, "% commit: " + "b" * 40, 1))
    problems = check.check(report, run.parent)["problems"]
    assert any("different commits" in p or "different commits" in p.replace("commit", "commit") for p in problems) or any("header commit" in p for p in problems)
    (report.parent / "benchmark_results.tex").write_text(good.replace("% === LUATCHECK-PROVENANCE v1 ===", "% header removed", 1))
    assert any("provenance blocks" in p for p in check.check(report, run.parent)["problems"])
    (report.parent / "benchmark_results.tex").write_text(good)
    assert check.check(report, run.parent)["problems"] == []


def test_report_check_rejects_the_real_smoke_run_tables_and_unreferenced_numbers(tmp_path):
    smoke_tables = SMOKE / "tables" / "benchmark_results.tex"
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    shutil.copy(smoke_tables, report_dir / "benchmark_results.tex")     # produced before provenance headers existed: no block
    (report_dir / "main.tex").write_text("\\input{benchmark_results}\n")
    result = check.check(report_dir / "main.tex", REAL)
    assert any("provenance blocks" in p for p in result["problems"])
    # inline table with measured numbers and no marker
    inline = ("\\begin{table}\\label{tab:results-inline}\\begin{tabular}{ll}a & 61.5\\% \\\\ b & 0.83 \\\\\\end{tabular}\\end{table}\n")
    (report_dir / "main.tex").write_text(inline)
    assert any("hard-coded numbers without provenance" in p for p in check.check(report_dir / "main.tex", REAL)["problems"])
    (report_dir / "main.tex").write_text(inline.replace("\\begin{tabular}", "% PROVENANCE: historical old 10-task pilot\n\\begin{tabular}"))
    result = check.check(report_dir / "main.tex", REAL)
    assert result["problems"] == [] and result["rows"][0]["freshness"].startswith("historical")
    (report_dir / "main.tex").write_text(inline.replace("\\begin{tabular}", "% PROVENANCE: run=bench-smoke-both-20261023\n\\begin{tabular}"))
    problems = check.check(report_dir / "main.tex", REAL)["problems"]
    assert any("only `main` runs" in p for p in problems) and any("not current" in p for p in problems)   # a smoke run can never back a result
    (report_dir / "main.tex").write_text("\\IfFileExists{benchmark_missing.tex}{\\input{benchmark_missing}}{}\n")
    result = check.check(report_dir / "main.tex", REAL)
    assert result["problems"] == [] and any("red placeholder" in n for n in result["notes"])   # an absent optional table file is a placeholder, not a failure


def test_stage_records_name_the_run_and_harness_they_consumed():
    judge = json.loads((SMOKE / "judge" / "judge_manifest.json").read_text())
    assert "stage_provenance" not in judge or judge["stage_provenance"]["consumed_run"]["run_id"] == SMOKE.name   # recorded runs predate stage records
    from evaluation import judge_benchmark as jb
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "run"
        shutil.copytree(SMOKE, work)
        summary = jb.analyze(work, audit_size=3)
        stage = summary["stage_provenance"]
        assert stage["stage"] == "analyze" and stage["harness_version"] == provenance.HARNESS_VERSION and stage["consumed_run"]["run_id"] == SMOKE.name
        assert stage["consumed_run"]["trials_sha256"] == rb.sha256_file(rb.trials_path(work))


# ----------------------------------------------------------------------------- table column counts with missing cells

def _rows_have_header_width(tex: str):
    """Every data row of every tabular has as many cells as its header ('&' count), \\multicolumn rows excepted (they span the width)."""
    import re
    checked = 0
    for table in re.findall(r"\\begin\{tabular\}.*?\\end\{tabular\}", tex, re.S):
        lines = [l for l in table.splitlines() if l.rstrip().endswith("\\\\") and "&" in l]
        header = lines[0].count("&")
        for line in lines[1:]:
            assert line.count("&") == header, f"row has {line.count('&') + 1} cells, header {header + 1}: {line[:120]}"
            checked += 1
    return checked


def test_baseline_and_other_tables_keep_their_column_count_when_a_cell_is_missing():
    summary = json.loads((SMOKE / "analysis" / "summary.json").read_text())
    benchmarks, variants = ["hcmut_v1", "labour_vi_v1"], ["off", "l1_rerank"]
    full = render.render_baselines(summary, benchmarks, variants, "")
    assert _rows_have_header_width(full) >= 8
    for dropped in ("hcmut_v1/oracle", "labour_vi_v1/closed_book", "hcmut_v1/off", "labour_vi_v1/l1_rerank"):
        cut = json.loads(json.dumps(summary))
        del cut["cells"][dropped]
        tex = render.render_baselines(cut, benchmarks, variants, "")
        assert _rows_have_header_width(tex) >= 8 and tex.count(render.PENDING) >= 6   # the missing cell is a full row of red placeholders
        texts = render.render(cut, benchmarks, variants)
        assert _rows_have_header_width(texts["results"]) > 8 and _rows_have_header_width(texts["diagnostics"]) > 4
    # a benchmark that was never run at all
    assert _rows_have_header_width(render.render_baselines(summary, benchmarks + ["not_run_v1"], variants, "")) >= 8


def test_na_marker_is_only_allowed_on_design_tables_not_on_results_tables(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    body = "\\begin{{table}}\\label{{{label}}}% PROVENANCE: n/a design table, no measurement\n\\begin{{tabular}}{{ll}}W45 & 2.5 \\\\ W46 & 3.5 \\\\ W47 & 4.5 \\\\\\end{{tabular}}\\end{{table}}\n"
    (report_dir / "main.tex").write_text(body.format(label="tab:plan"))
    assert check.check(report_dir / "main.tex", REAL)["problems"] == []
    (report_dir / "main.tex").write_text(body.format(label="tab:benchmark-results"))
    problems = check.check(report_dir / "main.tex", REAL)["problems"]
    assert len(problems) == 1 and "only allowed on design / plan tables" in problems[0]
