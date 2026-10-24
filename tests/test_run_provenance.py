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
    local = sorted(p.name for p in runs.iterdir() if p.is_dir())
    assert [r["run"] for r in rows if r["state"] != "remote"] == local            # every directory is listed ...
    assert {r["run"] for r in rows if r["state"] == "remote"} == {i["run"] for i in registry.load_remote()}     # ... plus the runs that live only on server 82
    text = (runs / "REGISTRY.md").read_text()
    assert "| bench-smoke-both-20261023 | smoke |" in text and "historical" in text and "Only `report_eligible = yes` AND `current`" in text
    assert len((runs / "registry.jsonl").read_text().splitlines()) == len(rows)


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


# ----------------------------------------------------------------------------- pinned runs, remote runs, comparison tables

import os

V3_HCMUT, V3_LABOUR = "d2-gpu-main-hcmut-v3", "d2-gpu-main-labour-v3"


def light_copy(tmp_path, name, source_name=V3_HCMUT, **manifest_changes) -> Path:
    """A run directory that is a COPY of a recorded run's manifest and summary (all the registry reads) with symlinks to the big recorded files,
    so the copy can also feed the comparison. Manifest fields can be changed to provoke one failure."""
    runs = tmp_path / "runs"
    runs.mkdir(exist_ok=True)
    run = runs / name
    source = REAL / source_name
    (run / "analysis").mkdir(parents=True)
    manifest = json.loads((source / "manifest.json").read_text())
    manifest.update(run_id=name, **manifest_changes)
    (run / "manifest.json").write_text(json.dumps(manifest))
    shutil.copy(source / "analysis" / "summary.json", run / "analysis" / "summary.json")
    os.symlink(source / "analysis" / "private-trial-details.json", run / "analysis" / "private-trial-details.json")
    os.symlink(source / "trials.jsonl", run / "trials.jsonl")
    return run


def test_the_frozen_v3_runs_are_pinned_to_their_commit_and_stay_reportable():
    pins = registry.load_pins()
    assert {r: pins[r]["commit"] for r in (V3_HCMUT, V3_LABOUR)} == {V3_HCMUT: "957579b", V3_LABOUR: "957579b"}
    for name in (V3_HCMUT, V3_LABOUR):
        row = registry.describe(REAL / name)
        assert row["freshness"] == "pinned@957579b" and row["kind"] == "main" and row["report_eligible"] is True and row["harness_version"] == "1.1.2"
        manifest = json.loads((REAL / name / "manifest.json").read_text())
        assert registry.pin_problems(manifest, pins[name]) == []
        # the working tree has moved on (so an unpinned run with the same fingerprint is stale), the pin does not look at it
        assert registry.stale_reasons(manifest)


def test_a_pin_holds_only_while_the_recorded_fingerprint_equals_the_commits_sources(tmp_path):
    ok = light_copy(tmp_path, V3_HCMUT)
    assert registry.describe(ok)["freshness"] == "pinned@957579b"
    manifest = json.loads((ok / "manifest.json").read_text())
    victim = next(p for p in manifest["sources"]["collection_files"] if p.startswith("src/") and p.endswith(".py"))

    edited = json.loads(json.dumps(manifest))
    edited["sources"]["files_sha256"][victim] = "0" * 64
    (ok / "manifest.json").write_text(json.dumps(edited))
    fresh = registry.describe(ok)["freshness"]
    assert fresh.startswith("stale: pin 957579b does not hold") and victim in fresh

    edited = json.loads(json.dumps(manifest))
    edited["sources"]["collection_sha256"] = "1" * 64
    (ok / "manifest.json").write_text(json.dumps(edited))
    assert "collection_sha256" in registry.describe(ok)["freshness"]

    edited = json.loads(json.dumps(manifest))
    edited["provenance"]["git"]["commit"] = "a" * 40
    (ok / "manifest.json").write_text(json.dumps(edited))
    assert "recorded commit aaaaaaaaaaaa, not the pinned" in registry.describe(ok)["freshness"]

    edited = json.loads(json.dumps(manifest))
    edited["sources"]["collection_files"] = edited["sources"]["collection_files"][:-3]
    (ok / "manifest.json").write_text(json.dumps(edited))
    assert "not in the run's fingerprint" in registry.describe(ok)["freshness"] or "stale" in registry.describe(ok)["freshness"]

    unavailable = {"run": "x", "commit": "0123456789abcdef0123456789abcdef01234567"}
    assert "not available in this repository" in registry.pin_problems(manifest, unavailable)[0]


def test_an_old_run_that_is_not_pinned_still_shows_stale(tmp_path):
    other = light_copy(tmp_path, "d2-gpu-main-hcmut-v9")                  # same recorded fingerprint, but nobody pinned this run
    assert registry.describe(other)["freshness"].startswith("stale:")
    marked = light_copy(tmp_path, "d2-gpu-main-hcmut-v8")
    (marked / "RUN_STATUS.json").write_text(json.dumps({"superseded_by": V3_HCMUT}))
    assert registry.describe(marked)["freshness"] == f"superseded_by: {V3_HCMUT}"


def test_runs_that_live_only_on_server_82_are_listed_as_remote_and_superseded(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / V3_HCMUT).symlink_to(REAL / V3_HCMUT, target_is_directory=True)
    rows = {r["run"]: r for r in registry.scan(runs)}
    for name in ("d2-gpu-main-hcmut-v1", "d2-gpu-main-hcmut-v2", "d2-gpu-main-labour-v1", "d2-gpu-main-labour-v2"):
        assert rows[name]["freshness"] == f"remote/not synced (superseded_by: {name.rsplit('-', 1)[0]}-v3)" and rows[name]["state"] == "remote"
        assert rows[name]["report_eligible"] is False
    assert rows["d2-gpu-gate-*"]["freshness"].startswith("remote/not synced") and rows["d2-gpu-gate-*"]["kind"] == "smoke"
    assert rows[V3_HCMUT]["freshness"] == "pinned@957579b"
    registry.write_registry(runs)
    text = (runs / "REGISTRY.md").read_text()
    assert "remote/not synced" in text and "pinned@957579b" in text and "pinned 1" in text
    # a directory that is synced back later is described by its own manifest and keeps the supersession mark
    synced = light_copy(tmp_path, "d2-gpu-main-hcmut-v2")
    assert registry.describe(synced)["freshness"] == f"superseded_by: {V3_HCMUT}"
    assert "d2-gpu-main-hcmut-v2" in {r["run"] for r in registry.scan(synced.parent)} and registry.scan(synced.parent)


def comparison_report(tmp_path, runs_dir, arms):
    from evaluation import compare_runs as cmp
    data = cmp.build([cmp.parse_arm(a) for a in arms], cmp.default_contrasts([cmp.parse_arm(a)[0] for a in arms]), ["off", "l1", "l1_rerank"], runs_dir)
    out = tmp_path / "report"
    out.mkdir(exist_ok=True)
    cmp.write_outputs(data, out, "python evaluation/run_d2.py compare (test)")
    (out / "main.tex").write_text("\\documentclass{article}\\begin{document}\\input{comparison}\n\\end{document}\n")
    return out / "main.tex", out / "comparison.tex"


def test_report_check_accepts_pinned_runs_and_their_own_tables():
    report_dir = Path(__import__("tempfile").mkdtemp())
    try:
        (report_dir / "benchmark_results.tex").write_text((REAL / V3_HCMUT / "tables" / "benchmark_results.tex").read_text())
        (report_dir / "benchmark_diagnostics.tex").write_text((REAL / V3_HCMUT / "tables" / "benchmark_diagnostics.tex").read_text())
        (report_dir / "main.tex").write_text("\\input{benchmark_results}\\input{benchmark_diagnostics}\n")
        result = check.check(report_dir / "main.tex", REAL)
        assert result["problems"] == [] and {r["freshness"] for r in result["rows"]} == {"pinned@957579b"} and len(result["rows"]) >= 4
        # an inline table can name a pinned run too
        (report_dir / "main.tex").write_text(f"\\begin{{table}}\\label{{tab:results-x}}% PROVENANCE: run={V3_HCMUT}\n\\begin{{tabular}}{{ll}}a & 61.5\\% \\\\ b & 0.83 \\\\\\end{{tabular}}\\end{{table}}\n")
        assert check.check(report_dir / "main.tex", REAL)["problems"] == []
    finally:
        shutil.rmtree(report_dir, ignore_errors=True)


def test_a_table_file_mixing_a_pinned_and_a_current_run_fails(tmp_path):
    current = current_looking_copy(tmp_path)
    (current.parent / V3_HCMUT).symlink_to(REAL / V3_HCMUT, target_is_directory=True)
    report = rendered_report(tmp_path, current)
    own = (report.parent / "benchmark_results.tex").read_text()
    assert check.check(report, current.parent)["problems"] == []
    (report.parent / "benchmark_results.tex").write_text(own + (REAL / V3_HCMUT / "tables" / "benchmark_results.tex").read_text())
    problems = check.check(report, current.parent)["problems"]
    assert any("mix pinned and current runs" in p for p in problems) and any("different commits" in p for p in problems)
    # the same holds for an inline table that names both
    inline = ("\\begin{table}\\label{tab:results-inline}% PROVENANCE: run=" + f"{V3_HCMUT},{current.name}" +
              "\n\\begin{tabular}{ll}a & 61.5\\% \\\\ b & 0.83 \\\\\\end{tabular}\\end{table}\n")
    (report.parent / "benchmark_results.tex").write_text(own)
    (report.parent / "main.tex").write_text(inline)
    assert any("mixes pinned and current runs" in p for p in check.check(report.parent / "main.tex", current.parent)["problems"])


def test_comparison_tables_may_put_a_pinned_and_a_current_run_side_by_side_but_every_arm_is_checked(tmp_path):
    current = current_looking_copy(tmp_path)
    runs = current.parent
    (runs / V3_HCMUT).symlink_to(REAL / V3_HCMUT, target_is_directory=True)
    (runs / V3_LABOUR).symlink_to(REAL / V3_LABOUR, target_is_directory=True)
    # (the "current" arm is the re-pointed smoke copy: other tasks, so use v3 as both arms for the accepted case and check the mix by the registry rows)
    report, table = comparison_report(tmp_path, runs, [f"v3={V3_HCMUT},{V3_LABOUR}", f"v3-again={V3_HCMUT},{V3_LABOUR}"])
    result = check.check(report, runs)
    assert result["problems"] == [] and {r["freshness"] for r in result["rows"]} == {"pinned@957579b"} and len(result["rows"]) == 2 * 2 * 2
    good = table.read_text()
    table.write_text(good.replace("harness_version: 1.1.2", "harness_version: 1.1.3", 1))
    assert any("header harness" in p for p in check.check(report, runs)["problems"])
    table.write_text(good.replace("% arm: v3 | benchmark: hcmut_v1 | run: " + V3_HCMUT, "% arm: v3 | benchmark: hcmut_v1 | run: " + current.name, 1))
    assert any("header commit" in p or "trials of run" in p or "differs" in p for p in check.check(report, runs)["problems"])
    table.write_text(good.replace(check.CMP_START, "% header removed", 1))
    assert any("comparison blocks" in p for p in check.check(report, runs)["problems"])
    table.write_text(good.replace("trials_sha256: ", "trials_sha256: 00", 1))
    assert any("changed after the table was rendered" in p for p in check.check(report, runs)["problems"])
    table.write_text(good)
    # an arm run that is not main / eligible / current-or-pinned fails the whole table
    smoke_like = light_copy(tmp_path, "d2-gpu-main-hcmut-v7")           # unpinned copy of v3: stale
    report2, _ = comparison_report(tmp_path, smoke_like.parent, [f"a=d2-gpu-main-hcmut-v7", "b=d2-gpu-main-hcmut-v7"])
    assert any("is not current: stale" in p for p in check.check(report2, smoke_like.parent)["problems"])


def test_a_post_hoc_arm_requires_the_label_in_every_table_that_shows_it(tmp_path):
    # a COPY of the real v3 run's records whose manifest carries the r2 protocol tag (it is still pinned to the same commit by its name)
    revised = light_copy(tmp_path, V3_LABOUR, source_name=V3_LABOUR, protocol="r2-posthoc", protocol_label="post-hoc revision evaluated on the same tasks")
    (revised.parent / V3_HCMUT).symlink_to(REAL / V3_HCMUT, target_is_directory=True)
    # arms must cover the same benchmark: build the comparison from the labour copy against the real labour run
    (revised.parent.parent / "runs2").mkdir(exist_ok=True)
    runs2 = revised.parent.parent / "runs2"
    (runs2 / V3_LABOUR).symlink_to(REAL / V3_LABOUR, target_is_directory=True)
    (runs2 / "d2-gpu-main-labour-v3-copy").symlink_to(revised, target_is_directory=True)
    assert V3_LABOUR in registry.load_pins()
    from evaluation import compare_runs as cmp
    data = cmp.build([cmp.parse_arm(f"frozen={V3_LABOUR}"), cmp.parse_arm("revised=d2-gpu-main-labour-v3-copy")], [("system effect", "frozen", "revised")], ["off"], runs2)
    assert data["arms"]["revised"]["labour_vi_v1"]["protocol_label"] == "post-hoc revision evaluated on the same tasks"
    out = tmp_path / "rep"
    out.mkdir()
    cmp.write_outputs(data, out, "python evaluation/run_d2.py compare (test)")
    tex = (out / "comparison.tex").read_text()
    assert tex.lower().count("post-hoc revision evaluated on the same tasks") >= 2 and "post-hoc revision evaluated on the same tasks" in (out / "comparison.md").read_text().lower()
    (out / "main.tex").write_text("\\input{comparison}\n")
    problems = check.check(out / "main.tex", runs2)["problems"]
    assert not any("does not print" in p for p in problems)
    (out / "comparison.tex").write_text(tex.replace("ost-hoc revision evaluated on the same tasks", "ost-hoc"))
    assert any("does not print" in p for p in check.check(out / "main.tex", runs2)["problems"])
