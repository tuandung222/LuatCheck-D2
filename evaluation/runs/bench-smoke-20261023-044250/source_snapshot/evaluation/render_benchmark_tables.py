"""Render LaTeX tables (benchmark x variant) for report_d2 from <run-dir>/analysis/summary.json.

The output is meant to be \\input into the report; main_d2.tex itself is never edited here. Values come only from the
analysis summary; anything missing is a visible red placeholder, never a filled-in number. Smoke or otherwise
non-eligible runs cannot be written to the report file unless --allow-non-eligible is given, and are then labelled.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "report_d2" / "benchmark_results.tex"
PENDING = r"\textcolor{red}{\textbf{[PENDING]}}"
NOT_REPORTABLE = r"\textit{n/r}"
BENCH_NAMES = {"hcmut_v1": "HCMUT-v1", "labour_vi_v1": "Labour-VI-v1"}
VARIANT_NAMES = {"off": "OFF", "l1": "L1", "l1_rerank": r"L1+rerank"}


def esc(text: str) -> str:
    return str(text).replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("%", r"\%").replace("&", r"\&").replace("#", r"\#")


def pct(value: Optional[float]) -> str:
    return PENDING if value is None else f"{100 * value:.1f}"


def num(value: Optional[float], digits: int = 3) -> str:
    return PENDING if value is None else f"{value:.{digits}f}"


def success_cell(cell: Dict[str, Any]) -> str:
    s = cell["strict_success"]
    if cell["judging"]["judged_valid"] == 0 and cell["counts"]["execution_errors"] < cell["trials_recorded"]:
        return PENDING
    out = f"{100 * s['rate_lower_bound']:.1f}"
    ci = s.get("ci95_task_bootstrap_lower_bound")
    if ci:
        out += rf"\,{{\scriptsize[{100 * ci[0]:.0f}--{100 * ci[1]:.0f}]}}"
    if s["unknown"]:
        out += rf"$^{{\dagger{s['unknown']}}}$"
    return out


def faith_cell(cell: Dict[str, Any]) -> str:
    c = cell["claim_faithfulness"]
    if c["rate"] is None:
        return PENDING if cell["judging"]["judgeable"] == 0 else "--"
    return f"{100 * c['rate']:.1f}"


def latency_cell(cell: Dict[str, Any]) -> str:
    lat = cell["latency"]
    if not lat["reportable"]:
        return NOT_REPORTABLE
    if lat["trial_p50_s"] is None:
        return PENDING
    return f"{lat['trial_p50_s']:.1f}/{lat['trial_p95_s']:.1f}"


def render(summary: Dict[str, Any], expect_benchmarks: List[str], expect_variants: List[str]) -> str:
    cells = summary["cells"]
    run_label = f"{summary['run_id']} ({summary['phase']}, {summary['run_profile']})"
    non_eligible = not summary["report_eligible"]
    seeds = sorted({s for c in cells.values() for s in c["seeds"]})
    total_trials = sum(c["trials_recorded"] for c in cells.values())
    unknown = sum(c["strict_success"]["unknown"] for c in cells.values())
    judge = summary.get("judge_model") or {}
    judge_text = (f"{esc(judge['requested'])} (gateway-routed, thinking {esc(judge['thinking'].get('type'))}, effort "
                  f"{esc(judge['reasoning_effort'])}; model revision not pinned)") if judge else "an LLM judge (not yet run)"
    banner = ""
    if non_eligible:
        banner = (r"\textcolor{red}{\textbf{NON-ELIGIBLE RUN (" + esc(summary["phase"]) + r"): pipeline check only, not report evidence.}} ")
    cost = summary["judge_cost_total"]

    main_rows: List[str] = []
    ops_rows: List[str] = []
    for bm in expect_benchmarks:
        bm_cells = [(v, cells.get(f"{bm}/{v}")) for v in expect_variants]
        for i, (variant, cell) in enumerate(bm_cells):
            lead = (rf"\multirow{{{len(bm_cells)}}}{{*}}{{{esc(BENCH_NAMES.get(bm, bm))}}}" if i == 0 else "")
            name = esc(VARIANT_NAMES.get(variant, variant)).replace("+", "{+}")
            if cell is None:
                main_rows.append(f"{lead} & {name} & " + " & ".join([PENDING] * 8) + r"\\")
                ops_rows.append(f"{lead} & {name} & " + " & ".join([PENDING] * 6) + r"\\")
                continue
            r, ci = cell["retrieval"], cell["citation_id"]
            main_rows.append(" & ".join([
                lead, name, str(cell["trials_recorded"]) + (rf"/{cell['trials_planned']}" if cell["trials_missing"] else ""),
                success_cell(cell), pct(cell["behaviour_appropriate"]["rate"]), faith_cell(cell),
                num(r["Recall@5"]), num(r["MRR"]), num(ci["precision"]), num(ci["recall"])]) + r"\\")
            c = cell["counts"]
            tok = cell["tokens"]
            ops_rows.append(" & ".join([
                lead, name, f"{c['answered']}/{c['refused']}/{c['clarified']}/{c['execution_errors']}",
                latency_cell(cell),
                PENDING if tok["input_per_trial"] is None else f"{tok['input_per_trial']:.0f}/{tok['output_per_trial']:.0f}",
                f"{tok['native_calls_per_trial']:.2f}" if tok["native_calls_per_trial"] is not None else PENDING,
                str(cell["strict_success"]["unknown"]),
                f"{cell['judge_cost']['gateway_reported_usd_body']:.3f}"]) + r"\\")
        main_rows.append(r"\midrule")
        ops_rows.append(r"\midrule")
    main_rows.pop()
    ops_rows.pop()

    latency_note = ("Latency is sequential single-request wall time on the recorded Mac, execution-error trials excluded."
                    if summary["latency_reportable"] else
                    "n/r: latency was recorded under concurrent workers and is not reportable.")
    caption_main = (banner + f"Benchmark results per variant ({total_trials} real native trials; seeds {', '.join(map(str, seeds))}; run "
                    f"{esc(summary['run_id'])}). \\emph{{Succ.}} is the strict-success rate (behaviour appropriate, correctness and "
                    f"completeness 2, all claims supported) as a lower bound over all trials, with a task-level bootstrap 95\\% interval; "
                    f"execution errors count as failures and $\\dagger k$ marks $k$ judge-unknown trials counted as failures. "
                    f"Succ., Beh., Faith. are LLM-judge estimates by {judge_text}, \\textbf{{not human labels}}; the human audit is pending. "
                    f"Recall@5 and MRR are trajectory retrieval over answerable trials; Cit. P/R are cited-ID set matches to gold IDs "
                    f"(not answer correctness). Red entries are not measured.")
    caption_ops = (banner + "Operational measurements and judge cost per variant. Counts are answered/refused/clarified/execution-error trials. "
                   + latency_note + f" Tokens are controller input/output per trial (complete usage only). Judge cost is the "
                   f"gateway-reported usage cost over all retained attempts (all variants: {cost['gateway_reported_usd_body']:.3f} USD; "
                   f"not an invoice).")
    main = "\n".join([
        r"\begin{table}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{@{}llrrrrrrrr@{}}", r"\toprule",
        r"Benchmark & Variant & Trials & Succ.\ (\%) & Beh.\ (\%) & Faith.\ (\%) & Recall@5 & MRR & Cit.\ P & Cit.\ R\\",
        r"\midrule", *main_rows, r"\bottomrule", r"\end{tabular}}",
        r"\caption{" + caption_main + "}", r"\label{tab:benchmark-main}", r"\end{table}"])
    ops = "\n".join([
        r"\begin{table}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{@{}llrrrrrr@{}}", r"\toprule",
        r"Benchmark & Variant & Ans/Ref/Clar/Err & p50/p95 (s) & Tok.\ in/out & Calls/trial & Unknown & Judge USD\\",
        r"\midrule", *ops_rows, r"\bottomrule", r"\end{tabular}}",
        r"\caption{" + caption_ops + "}", r"\label{tab:benchmark-ops}", r"\end{table}"])
    header = (f"% Generated by evaluation/render_benchmark_tables.py from {run_label}. Do not edit by hand.\n"
              f"% Requires: booktabs, multirow, graphicx, xcolor. report_eligible={summary['report_eligible']}.\n")
    return header + main + "\n\n" + ops + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--expect-benchmarks", default="hcmut_v1,labour_vi_v1")
    parser.add_argument("--expect-variants", default="off,l1,l1_rerank")
    parser.add_argument("--allow-non-eligible", action="store_true",
                        help="write a smoke/incomplete run (labelled in the captions); never use for the report file")
    args = parser.parse_args(argv)
    summary = json.loads((Path(args.run_dir) / "analysis" / "summary.json").read_text(encoding="utf-8"))
    output = Path(args.output).resolve()
    if not summary["report_eligible"]:
        if output == DEFAULT_OUTPUT.resolve():
            raise SystemExit("Refusing to write a non-eligible (smoke/incomplete/unjudged) run to report_d2/benchmark_results.tex. "
                             f"Write elsewhere with --output. Reason: {summary.get('report_eligible_note')}")
        if not args.allow_non_eligible:
            raise SystemExit("Run is not report-eligible; pass --allow-non-eligible to render it with a visible banner.")
    text = render(summary, [b for b in args.expect_benchmarks.split(",") if b], [v for v in args.expect_variants.split(",") if v])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
