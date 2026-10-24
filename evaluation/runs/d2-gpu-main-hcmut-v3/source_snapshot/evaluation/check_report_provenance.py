r"""Fail the build when the report can mix outdated and current results.

  python evaluation/check_report_provenance.py [--report report_d2/main_d2.tex]      (make report-check)

Rules (every violation is listed; exit code 1 if any)
  1. Every result table file the report \\input s (a file that contains a table float) carries one `LUATCHECK-PROVENANCE v1` comment
     block per table (written by evaluation/render_benchmark_tables.py): run id, commit, harness version, generator command.
  2. The run named in each block exists, is a harness run of kind `main`, is report_eligible, and its registry freshness is `current`
     (same collection sources / harness major.minor / locks / models as HEAD): a stale, superseded, historical, smoke or incomplete run
     cannot feed the report. The block's commit, harness version and trials hash must equal the run's own records (no hand-edited headers
     and no trials changed after rendering).
  3. All blocks of one file agree on commit and harness version.
  4. A table written inline in main_d2.tex that contains numbers must carry `% PROVENANCE: run=<run-id> ...` (checked like rule 2) or
     `% PROVENANCE: historical <reason>`, or `% PROVENANCE: n/a <reason>` which is accepted for design / plan / definition / placeholder tables but refused on tables labelled like result tables (tab:benchmark-*, tab:result*, tab:latency*, tab:accuracy*, tab:baseline*...) (listed in the output). "Results table" = label matching result/metric/error/bench/latency/accuracy/... with numbers, or any table with 3+ decimal/percent/ratio numbers; otherwise it is a hard-coded number without provenance.
  5. A table file that the report references through \\IfFileExists but that does not exist yet is a red placeholder in the report: allowed, reported.
Writes report_d2/RESULTS_PROVENANCE.md: table -> source file -> run -> commit -> harness -> status -> command.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

MARK_START, MARK_END = "% === LUATCHECK-PROVENANCE v1 ===", "% === END PROVENANCE ==="
NUMBER = re.compile(r"(?<![\\\w])\d+[.,]\d+|\b\d+\s*/\s*\d+\b|\b\d+\s*\\?%")
RESULT_LABEL = re.compile(r"result|metric|error|bench|latency|accura|eval|success|score|baseline|ablation|perf", re.I)
EXEMPT = ("historical", "n/a")
# `% PROVENANCE: n/a` (design / plan / definition / placeholder tables) is refused on tables labelled like the benchmark result tables.
N_A_BANNED = re.compile(r"^tab:(benchmark|results?|bench|latency|accuracy|baseline|ablation|perf)", re.I)


def strip_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def parse_blocks(text: str) -> List[Dict[str, str]]:
    blocks, current = [], None
    for line in text.splitlines():
        line = line.strip()
        if line == MARK_START:
            current = {}
        elif line == MARK_END and current is not None:
            blocks.append(current)
            current = None
        elif current is not None and line.startswith("% ") and ": " in line:
            key, value = line[2:].split(": ", 1)
            current[key.strip()] = value.strip()
    return blocks


def referenced_files(tex: str, base: Path) -> List[Dict[str, Any]]:
    """\\input{x} and \\IfFileExists{x}{...} targets (relative to the report directory), with whether the reference is optional."""
    def stem(name: str) -> str:
        return name[:-4] if name.endswith(".tex") else name
    found = []
    for match in re.finditer(r"\\IfFileExists\{([^}]+)\}", tex):
        found.append({"name": match.group(1), "optional": True})
    for match in re.finditer(r"\\input\{([^}]+)\}", tex):
        found.append({"name": match.group(1), "optional": any(stem(f["name"]) == stem(match.group(1)) for f in found)})
    out, seen = [], set()
    for f in found:
        if stem(f["name"]) in seen:
            continue
        seen.add(stem(f["name"]))
        if "#" in f["name"]:
            continue   # a macro argument, not a file
        direct = base / f["name"]
        f["path"] = direct if direct.is_file() else base / (f["name"] if f["name"].endswith(".tex") else f["name"] + ".tex")
        out.append(f)
    return out


def check_run(run_id: Optional[str], block: Dict[str, str], problems: List[str], where: str, runs_dir: Path = Path("evaluation/runs")) -> Dict[str, Any]:
    from evaluation import registry
    info: Dict[str, Any] = {"run": run_id, "freshness": None}
    run_dir = Path(runs_dir) / str(run_id)
    if not run_id or not (run_dir / "manifest.json").is_file():
        problems.append(f"{where}: run {run_id!r} not found under evaluation/runs")
        return info
    row = registry.describe(run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    info.update(freshness=row["freshness"], kind=row["kind"], eligible=row["report_eligible"])
    if row["kind"] != "main":
        problems.append(f"{where}: run {run_id} is kind {row['kind']!r}, only `main` runs may feed the report")
    if not row["report_eligible"]:
        problems.append(f"{where}: run {run_id} is not report_eligible (incomplete, unjudged, or source drift during the run)")
    if row["freshness"] != "current":
        problems.append(f"{where}: run {run_id} is not current: {row['freshness']}")
    git = (manifest.get("provenance") or {}).get("git") or {}
    if block:
        if block.get("commit") and git.get("commit") and block["commit"] != git["commit"]:
            problems.append(f"{where}: header commit {block['commit'][:12]} differs from the run's commit {git['commit'][:12]}")
        if block.get("harness_version") != manifest.get("harness_version"):
            problems.append(f"{where}: header harness {block.get('harness_version')} differs from the run's {manifest.get('harness_version')}")
        summary_path = run_dir / "analysis" / "summary.json"
        if block.get("trials_sha256") and summary_path.is_file():
            current = json.loads(summary_path.read_text(encoding="utf-8")).get("runs_sha256")
            if current != block["trials_sha256"]:
                problems.append(f"{where}: trials of run {run_id} changed after the table was rendered (re-render)")
    info.update(commit=git.get("commit"), harness=manifest.get("harness_version"))
    return info


def check(report: Path, runs_dir: Path = Path("evaluation/runs")) -> Dict[str, Any]:
    tex = report.read_text(encoding="utf-8")
    base = report.parent
    problems: List[str] = []
    notes: List[str] = []
    rows: List[Dict[str, Any]] = []
    for ref in referenced_files(tex, base):
        path = ref["path"]
        if not path.is_file():
            notes.append(f"{path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path}: not present ({'optional: red placeholder in the report' if ref['optional'] else 'REQUIRED input missing'})")
            if not ref["optional"]:
                problems.append(f"{path.name}: \\input file does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        tables = len(re.findall(r"\\begin\{table\*?\}", text))
        if not tables:
            continue   # prose / section file
        blocks = parse_blocks(text)
        if len(blocks) != tables:
            problems.append(f"{path.name}: {tables} tables but {len(blocks)} provenance blocks (table not produced by the renderer, or header removed)")
        for key in ("commit", "harness_version"):
            if len({b.get(key) for b in blocks}) > 1:
                problems.append(f"{path.name}: its tables come from different {key}s {sorted({str(b.get(key)) for b in blocks})}")
        for block in blocks:
            info = check_run(block.get("run_id"), block, problems, f"{path.name} [{block.get('table')}]", runs_dir)
            rows.append({"table": block.get("table"), "source": path.name, "run": block.get("run_id"), "commit": block.get("commit"),
                         "harness": block.get("harness_version"), "freshness": info.get("freshness"), "command": block.get("generator"),
                         "generated": block.get("generated_local")})
    # inline tables of main_d2.tex
    body = tex
    for match in re.finditer(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", body, re.S):
        chunk = match.group(0)
        label = re.search(r"\\label\{([^}]+)\}", chunk)
        label = label.group(1) if label else f"(inline table at char {match.start()})"
        numbers = NUMBER.findall(strip_comments(chunk))
        marker = re.search(r"(?<!\\)% PROVENANCE: (.+)$", chunk, re.M)
        if not (RESULT_LABEL.search(label) and numbers) and len(numbers) < 3 and not marker:
            continue   # a descriptive table (tools, plan, contributions...) without measured numbers
        if not marker:
            problems.append(f"main_d2.tex [{label}]: hard-coded numbers without provenance (add `% PROVENANCE: run=<run-id>` or `% PROVENANCE: historical <reason>`, or, for a design / plan table only, `% PROVENANCE: n/a <why it is not a result>`)")
            rows.append({"table": label, "source": "main_d2.tex (inline)", "run": None, "commit": None, "harness": None, "freshness": "NO PROVENANCE",
                         "command": None, "generated": None})
        elif marker.group(1).startswith("n/a") and N_A_BANNED.search(label):
            problems.append(f"main_d2.tex [{label}]: `% PROVENANCE: n/a` is only allowed on design / plan tables, not on a results table (use run=<run-id> or historical <reason>)")
            rows.append({"table": label, "source": "main_d2.tex (inline)", "run": None, "commit": None, "harness": None,
                         "freshness": "n/a NOT ALLOWED on a results table", "command": None, "generated": None})
        elif marker.group(1).startswith(EXEMPT):
            rows.append({"table": label, "source": "main_d2.tex (inline)", "run": None, "commit": None, "harness": None,
                         "freshness": marker.group(1), "command": None, "generated": None})
        else:
            run = re.search(r"run=(\S+)", marker.group(1))
            info = check_run(run.group(1) if run else None, {}, problems, f"main_d2.tex [{label}]", runs_dir)
            rows.append({"table": label, "source": "main_d2.tex (inline)", "run": info["run"], "commit": info.get("commit"), "harness": info.get("harness"),
                         "freshness": info.get("freshness"), "command": "(hand-maintained)", "generated": None})
    return {"problems": problems, "notes": notes, "rows": rows}


def write_markdown(report: Path, result: Dict[str, Any]) -> Path:
    from evaluation import provenance
    lines = ["# Results provenance of the report", "",
             f"Generated {provenance.local_now()} by `python evaluation/check_report_provenance.py` for `{report.name}` (harness `{provenance.HARNESS_VERSION}`). "
             "Every result table must come from a `main`, report-eligible, `current` run; this file is regenerated by `make report-check`.", "",
             f"Status: **{'FAILED' if result['problems'] else 'OK'}**", ""]
    lines += ["| table | source file | run | commit | harness | freshness | generated | command |", "|---|---|---|---|---|---|---|---|"]
    for r in result["rows"]:
        lines.append(f"| {r['table']} | {r['source']} | {r['run'] or '-'} | {str(r['commit'] or '-')[:12]} | {r['harness'] or '-'} | {r['freshness']} | {r['generated'] or '-'} | `{r['command'] or '-'}` |")
    if not result["rows"]:
        lines.append("| (no result tables in the report yet) | | | | | | | |")
    if result["notes"]:
        lines += ["", "Notes:", *[f"- {n}" for n in result["notes"]]]
    if result["problems"]:
        lines += ["", "Problems:", *[f"- {p}" for p in result["problems"]]]
    path = report.parent / "RESULTS_PROVENANCE.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", default="report_d2/main_d2.tex")
    parser.add_argument("--runs-dir", default="evaluation/runs")
    parser.add_argument("--no-write", action="store_true", help="do not write RESULTS_PROVENANCE.md next to the report")
    args = parser.parse_args(argv)
    import os
    os.chdir(REPO_ROOT)
    report = Path(args.report).resolve()
    result = check(report, Path(args.runs_dir))
    out = write_markdown(report, result) if not args.no_write else "(not written)"
    for note in result["notes"]:
        print(f"note: {note}")
    for problem in result["problems"]:
        print(f"FAIL: {problem}")
    print(f"{'FAILED' if result['problems'] else 'OK'}: {len(result['rows'])} result tables checked; wrote {out}")
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
