"""Render LaTeX (and Markdown) tables for the D2 report from <run-dir>/analysis/summary.json.

Outputs (all inside the run directory unless --output/--publish says otherwise)
  tables/benchmark_results.tex      \\input-able: tab:benchmark-main, tab:benchmark-ops, tab:benchmark-paired
  tables/benchmark_diagnostics.tex  behaviour confusion / abstention table (tab:benchmark-behaviour)
  tables/summary.md                 the same numbers as plain Markdown (for RUN_NOTES and review)
  report_d2/benchmark_results.tex   only with --publish, and only for a report-eligible run

Values come only from the analysis summary; anything missing is a visible red [PENDING], never a filled-in number.
Smoke or otherwise non-eligible runs are labelled with a red banner and can never be published to the report path.
main_d2.tex itself is never edited here. Needs booktabs, multirow, graphicx, xcolor in the report preamble.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_TABLES = REPO_ROOT / "report_d2" / "benchmark_results.tex"
PENDING = r"\textcolor{red}{\textbf{[PENDING]}}"
NOT_REPORTABLE = r"\textit{n/r}"
BENCH_NAMES = {"hcmut_v1": "HCMUT-v1", "labour_vi_v1": "Labour-VI-v1"}
VARIANT_NAMES = {"off": "OFF", "l1": "L1", "l1_rerank": r"L1+rerank"}
MD_PENDING = "PENDING"


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


def pair_cell(lat: Dict[str, Any], key50: str, key95: str, digits: int = 1) -> str:
    if not lat["reportable"]:
        return NOT_REPORTABLE
    if lat.get(key50) is None:
        return PENDING
    return f"{lat[key50]:.{digits}f}/{lat[key95]:.{digits}f}"


def delta_cell(result: Optional[Dict[str, Any]], scale: float = 100.0, digits: int = 1) -> str:
    if not result:
        return PENDING
    lo, hi = result["ci95"]
    return f"{scale * result['diff_b_minus_a']:+.{digits}f}\\,{{\\scriptsize[{scale * lo:+.{digits}f},{scale * hi:+.{digits}f}]}}"


def audit_sentence(agreement: Optional[Dict[str, Any]]) -> str:
    if not agreement or agreement.get("status") != "ok":
        return r"The human audit of the judge is " + PENDING + "."
    s = agreement["judge_vs_human"]["strict_success"]
    pooled = agreement.get("reviewers", {})
    return (f"Judge--human agreement on strict success over {s['n']} human-labelled items: {100 * s['percent_agreement']:.0f}\\% agreement"
            + (f", $\\kappa$ = {s['kappa']:.2f}" if s.get("kappa") is not None else ", $\\kappa$ undefined")
            + (f" ({len(pooled)} reviewer(s))" if pooled else "") + ".")


def render(summary: Dict[str, Any], expect_benchmarks: List[str], expect_variants: List[str],
           agreement: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    cells = summary["cells"]
    run_label = f"{summary['run_id']} ({summary['phase']}, {summary['run_profile']})"
    non_eligible = not summary["report_eligible"]
    seeds = sorted({s for c in cells.values() for s in c["seeds"]})
    total_trials = sum(c["trials_recorded"] for c in cells.values())
    judge = summary.get("judge_model") or {}
    judge_text = (f"{esc(judge['requested'])} (gateway-routed, thinking {esc(judge['thinking'].get('type'))}, effort "
                  f"{esc(judge['reasoning_effort'])}; model revision not pinned)") if judge else "an LLM judge (not yet run)"
    banner = ""
    if non_eligible:
        banner = (r"\textcolor{red}{\textbf{NON-ELIGIBLE RUN (" + esc(summary["phase"]) + r"): pipeline check only, not report evidence.}} ")
    cost = summary["judge_cost_total"]

    main_rows: List[str] = []
    ops_rows: List[str] = []
    beh_rows: List[str] = []
    for bm in expect_benchmarks:
        bm_cells = [(v, cells.get(f"{bm}/{v}")) for v in expect_variants]
        for i, (variant, cell) in enumerate(bm_cells):
            lead = (rf"\multirow{{{len(bm_cells)}}}{{*}}{{{esc(BENCH_NAMES.get(bm, bm))}}}" if i == 0 else "")
            name = esc(VARIANT_NAMES.get(variant, variant)).replace("+", "{+}")
            if cell is None:
                main_rows.append(f"{lead} & {name} & " + " & ".join([PENDING] * 9) + r"\\")
                ops_rows.append(f"{lead} & {name} & " + " & ".join([PENDING] * 9) + r"\\")
                beh_rows.append(f"{lead} & {name} & " + " & ".join([PENDING] * 7) + r"\\")
                continue
            r, ci = cell["retrieval"], cell["citation_id"]
            main_rows.append(" & ".join([
                lead, name, str(cell["trials_recorded"]) + (rf"/{cell['trials_planned']}" if cell["trials_missing"] else ""),
                success_cell(cell), pct(cell["behaviour_appropriate"]["rate"]), faith_cell(cell),
                num(r["Recall@5"]), num(r["MRR"]), num(ci["precision"]), num(ci["recall"]), num(ci["f1"])]) + r"\\")
            c = cell["counts"]
            tok, lat, err = cell["tokens"], cell["latency"], cell["errors"]
            ops_rows.append(" & ".join([
                lead, name, f"{c['answered']}/{c['refused']}/{c['clarified']}/{c['execution_errors']}",
                pct(err["error_rate"]),
                pair_cell(lat, "trial_p50_s", "trial_p95_s"), pair_cell(lat, "model_call_p50_s", "model_call_p95_s", 2),
                (NOT_REPORTABLE if not lat["reportable"] else num(lat.get("decode_tokens_per_s_p50"), 0)),
                PENDING if tok["input_per_trial"] is None else f"{tok['input_per_trial']:.0f}/{tok['output_per_trial']:.0f}",
                f"{tok['native_calls_per_trial']:.2f}" if tok["native_calls_per_trial"] is not None else PENDING,
                str(cell["strict_success"]["unknown"]),
                f"{cell['judge_cost']['gateway_reported_usd_body']:.3f}"]) + r"\\")
            b = cell["behaviour_confusion"]
            m = b["matrix_expected_by_actual"]
            beh_rows.append(" & ".join([
                lead, name,
                "/".join(str(m["answer"][s]) for s in ("answered", "refused", "clarified", "error")),
                "/".join(str(m["refuse"][s]) for s in ("answered", "refused", "clarified", "error")),
                pct(b["over_refusal_rate"]), pct(b["unsafe_answer_rate"]), pct(b["refusal_precision"]), pct(b["refusal_recall"]),
                pct(b["strict_match_rate_all"])]) + r"\\")
        main_rows.append(r"\midrule")
        ops_rows.append(r"\midrule")
        beh_rows.append(r"\midrule")
    for rows_ in (main_rows, ops_rows, beh_rows):
        rows_.pop()

    latency_note = ("Latency is sequential single-request wall time on the recorded machine, warm-up excluded; trial p50/p95 are over non-error trials."
                    if summary["latency_reportable"] else
                    "n/r: latency was recorded under concurrent workers and is not reportable.")
    caption_main = (banner + f"Benchmark results per variant ({total_trials} real native trials; seeds {', '.join(map(str, seeds))}; run "
                    f"{esc(summary['run_id'])}). \\emph{{Succ.}} is the strict-success rate (behaviour appropriate, correctness and "
                    f"completeness 2, all claims supported) as a lower bound over all trials, with a task-level bootstrap 95\\% interval; "
                    f"execution errors count as failures and $\\dagger k$ marks $k$ judge-unknown trials counted as failures. "
                    f"Succ., Beh., Faith. are LLM-judge estimates by {judge_text}, \\textbf{{not human labels}}. {audit_sentence(agreement)} "
                    f"Recall@5 and MRR are retrieval of gold ids over the agent's search+read trace (answerable trials); Cit. P/R/F1 are macro "
                    f"cited-id set matches to gold ids (nothing cited = 0; source-ID proxies, not answer correctness). Red entries are not measured.")
    caption_ops = (banner + "Operational measurements and judge cost per variant. Counts are answered/refused/clarified/execution-error trials; "
                   "Err.\\ is the execution-error rate. "
                   + latency_note + f" Call = one controller LLM call; tok/s = decode tokens per second from the server timings. Tokens are controller "
                   f"input/output per trial (complete usage only). Judge cost is the gateway-reported usage cost over all retained attempts "
                   f"(all variants: {cost['gateway_reported_usd_body']:.3f} USD; not an invoice).")
    main = "\n".join([
        r"\begin{table}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{@{}llrrrrrrrrr@{}}", r"\toprule",
        r"Benchmark & Variant & Trials & Succ.\ (\%) & Beh.\ (\%) & Faith.\ (\%) & Recall@5 & MRR & Cit.\ P & Cit.\ R & Cit.\ F1\\",
        r"\midrule", *main_rows, r"\bottomrule", r"\end{tabular}}",
        r"\caption{" + caption_main + "}", r"\label{tab:benchmark-main}", r"\end{table}"])
    ops = "\n".join([
        r"\begin{table}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{@{}llrrrrrrrrr@{}}", r"\toprule",
        r"Benchmark & Variant & Ans/Ref/Clar/Err & Err.\ (\%) & Trial p50/p95 (s) & Call p50/p95 (s) & tok/s & Tok.\ in/out & Calls/trial & Unknown & Judge USD\\",
        r"\midrule", *ops_rows, r"\bottomrule", r"\end{tabular}}",
        r"\caption{" + caption_ops + "}", r"\label{tab:benchmark-ops}", r"\end{table}"])
    paired = render_paired(summary, expect_benchmarks, banner)
    beh = "\n".join([
        r"\begin{table}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{@{}llrrrrrrr@{}}", r"\toprule",
        r"Benchmark & Variant & E=answer: A/R/C/Err & E=refuse: A/R/C/Err & Over-refusal (\%) & Unsafe answer (\%) & Refusal P (\%) & Refusal R (\%) & Strict match (\%)\\",
        r"\midrule", *beh_rows, r"\bottomrule", r"\end{tabular}}",
        r"\caption{" + banner + "Structural behaviour (terminal status vs the frozen expected behaviour, no judge): rows E=answer / E=refuse give counts of "
        "answered/refused/clarified/error. Over-refusal = refused or clarified when an answer exists; unsafe answer = answered when the task should be refused; "
        "refusal P/R treat \\emph{refused} as the positive class (non-error trials); strict match counts errors as mismatches.}",
        r"\label{tab:benchmark-behaviour}", r"\end{table}"])
    header = (f"% Generated by evaluation/render_benchmark_tables.py from {run_label}. Do not edit by hand.\n"
              f"% Requires: booktabs, multirow, graphicx, xcolor. report_eligible={summary['report_eligible']}.\n")
    return {"results": header + main + "\n\n" + ops + "\n\n" + paired + "\n", "diagnostics": header + beh + "\n",
            "markdown": render_markdown(summary, expect_benchmarks, expect_variants, agreement)}


def render_paired(summary: Dict[str, Any], expect_benchmarks: List[str], banner: str) -> str:
    comparisons = (summary.get("paired_differences") or {}).get("comparisons") or {}
    rows: List[str] = []
    for label, entry in comparisons.items():
        scopes = [(bm, entry["by_benchmark"].get(bm)) for bm in expect_benchmarks] + [("pooled", entry["pooled"])]
        for i, (scope, metrics) in enumerate(scopes):
            lead = rf"\multirow{{{len(scopes)}}}{{*}}{{{esc(label).replace('+', '{+}')}}}" if i == 0 else ""
            name = "pooled" if scope == "pooled" else esc(BENCH_NAMES.get(scope, scope))
            if not metrics:
                rows.append(f"{lead} & {name} & " + " & ".join([PENDING] * 6) + r"\\")
                continue
            n = (metrics.get("strict_success_lower") or {}).get("n_units")
            rows.append(" & ".join([lead, name, str(n) if n else PENDING,
                                    delta_cell(metrics.get("strict_success_lower")), delta_cell(metrics.get("behaviour_strict_match")),
                                    delta_cell(metrics.get("recall_at_5"), 100.0), delta_cell(metrics.get("citation_f1"), 100.0),
                                    delta_cell(metrics.get("execution_error"))]) + r"\\")
        rows.append(r"\midrule")
    if rows:
        rows.pop()
    else:
        rows = [r"\multicolumn{8}{c}{" + PENDING + r"}\\"]
    caption = (banner + "Paired variant differences (treatment minus baseline, percentage points) with 95\\% paired bootstrap intervals over tasks "
               f"(seeds averaged per task; {(summary.get('paired_differences') or {}).get('draws', '--')} resamples; pooled = both benchmarks' tasks together). "
               "Succ.\\ is the strict-success lower bound (LLM-judge estimate), Beh.\\ the structural behaviour match, Rec.@5 the trace retrieval, Cit.\\ F1 the "
               "cited-id F1, Err.\\ the execution-error rate. No multiple-comparison correction; intervals that include 0 show no detectable difference at this sample size.")
    return "\n".join([
        r"\begin{table}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}", r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{@{}llrrrrrr@{}}", r"\toprule",
        r"Comparison & Scope & Tasks & $\Delta$ Succ.\ (pp) & $\Delta$ Beh.\ match (pp) & $\Delta$ Rec.@5 (pp) & $\Delta$ Cit.\ F1 (pp) & $\Delta$ Err.\ (pp)\\",
        r"\midrule", *rows, r"\bottomrule", r"\end{tabular}}", r"\caption{" + caption + "}", r"\label{tab:benchmark-paired}", r"\end{table}"])


def render_markdown(summary: Dict[str, Any], expect_benchmarks: List[str], expect_variants: List[str], agreement: Optional[Dict[str, Any]]) -> str:
    def f(v, scale=1.0, d=1):
        return MD_PENDING if v is None else f"{scale * v:.{d}f}"
    lines = [f"# Results summary - run `{summary['run_id']}` ({summary['phase']}, {summary['run_profile']})", "",
             f"report_eligible: **{summary['report_eligible']}** - {summary['report_eligible_note']}", "",
             "LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. "
             "Execution errors count as failures in strict success and are reported separately.", ""]
    lines += ["| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for bm in expect_benchmarks:
        for v in expect_variants:
            c = summary["cells"].get(f"{bm}/{v}")
            if c is None:
                lines.append(f"| {bm} | {v} | " + " | ".join([MD_PENDING] * 12) + " |")
                continue
            s, ci = c["strict_success"], c["strict_success"].get("ci95_task_bootstrap_lower_bound")
            lines.append(f"| {bm} | {v} | {c['trials_recorded']}/{c['trials_planned']} | {f(s['rate_lower_bound'], 100)}"
                         + (f" [{100 * ci[0]:.0f}-{100 * ci[1]:.0f}]" if ci else "") + f" | {s['unknown']} | {f(c['behaviour_appropriate']['rate'], 100)} | "
                         f"{f(c['claim_faithfulness']['rate'], 100)} | {f(c['retrieval']['Recall@5'], 1, 3)} | {f(c['retrieval']['MRR'], 1, 3)} | "
                         f"{f(c['retrieval']['nDCG@5'], 1, 3)} | {f(c['citation_id']['precision'], 1, 3)} | {f(c['citation_id']['recall'], 1, 3)} | "
                         f"{f(c['citation_id']['f1'], 1, 3)} | {f(c['errors']['error_rate'], 100)} |")
    lines += ["", "## Behaviour (structural, no judge)", "",
              "| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |",
              "|---|---|---|---|---|---|---|---|---|"]
    for bm in expect_benchmarks:
        for v in expect_variants:
            c = summary["cells"].get(f"{bm}/{v}")
            if c is None:
                continue
            b = c["behaviour_confusion"]
            m = b["matrix_expected_by_actual"]
            lines.append(f"| {bm} | {v} | {'/'.join(str(m['answer'][k]) for k in ('answered', 'refused', 'clarified', 'error'))} | "
                         f"{'/'.join(str(m['refuse'][k]) for k in ('answered', 'refused', 'clarified', 'error'))} | {f(b['over_refusal_rate'], 100)} | "
                         f"{f(b['unsafe_answer_rate'], 100)} | {f(b['refusal_precision'], 100)} | {f(b['refusal_recall'], 100)} | {f(b['strict_match_rate_all'], 100)} |")
    lines += ["", "## Operations", "", "| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |",
              "|---|---|---|---|---|---|---|---|---|"]
    for bm in expect_benchmarks:
        for v in expect_variants:
            c = summary["cells"].get(f"{bm}/{v}")
            if c is None:
                continue
            lat, tok = c["latency"], c["tokens"]
            lines.append(f"| {bm} | {v} | {lat['reportable']} | {f(lat['trial_p50_s'], 1, 1)}/{f(lat['trial_p95_s'], 1, 1)} | "
                         f"{f(lat['model_call_p50_s'], 1, 2)}/{f(lat['model_call_p95_s'], 1, 2)} | {f(lat.get('decode_tokens_per_s_p50'), 1, 0)} | "
                         f"{f(tok['input_per_trial'], 1, 0)}/{f(tok['output_per_trial'], 1, 0)} | {f(tok['native_calls_per_trial'], 1, 2)} | "
                         f"{c['judge_cost']['gateway_reported_usd_body']:.3f} |")
    paired = (summary.get("paired_differences") or {}).get("comparisons") or {}
    if paired:
        lines += ["", "## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)", "",
                  "| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |", "|---|---|---|---|---|---|---|---|"]
        for label, entry in paired.items():
            for scope, metrics in list(entry["by_benchmark"].items()) + [("pooled", entry["pooled"])]:
                def cell(key):
                    r = (metrics or {}).get(key)
                    return MD_PENDING if not r else f"{100 * r['diff_b_minus_a']:+.1f} [{100 * r['ci95'][0]:+.1f},{100 * r['ci95'][1]:+.1f}]"
                n = ((metrics or {}).get("strict_success_lower") or {}).get("n_units")
                lines.append(f"| {label} | {scope} | {n if n else MD_PENDING} | {cell('strict_success_lower')} | {cell('behaviour_strict_match')} | "
                             f"{cell('recall_at_5')} | {cell('citation_f1')} | {cell('execution_error')} |")
    lines += ["", "## Judge reliability", "",
              ("Human audit: " + json.dumps(agreement["judge_vs_human"].get("strict_success"), default=str)) if agreement and agreement.get("status") == "ok"
              else "Human audit labels: PENDING (agreement and kappa are not computed without real labels).", ""]
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", help="results .tex path (default <run>/tables/benchmark_results.tex)")
    parser.add_argument("--publish", action="store_true", help="also write report_d2/benchmark_results.tex (report-eligible runs only)")
    parser.add_argument("--expect-benchmarks", default="hcmut_v1,labour_vi_v1")
    parser.add_argument("--expect-variants", default="off,l1,l1_rerank")
    parser.add_argument("--allow-non-eligible", action="store_true",
                        help="render a smoke/incomplete run (labelled in the captions); never publishable")
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    summary = json.loads((run_dir / "analysis" / "summary.json").read_text(encoding="utf-8"))
    agreement_path = run_dir / "analysis" / "human-audit" / "agreement.json"
    agreement = json.loads(agreement_path.read_text(encoding="utf-8")) if agreement_path.is_file() else None
    output = Path(args.output).resolve() if args.output else (run_dir / "tables" / "benchmark_results.tex").resolve()
    if not summary["report_eligible"]:
        if args.publish or output == REPORT_TABLES.resolve():
            raise SystemExit("Refusing to write a non-eligible (smoke/incomplete/unjudged) run to report_d2/benchmark_results.tex. "
                             f"Reason: {summary.get('report_eligible_note')}")
        if not args.allow_non_eligible:
            raise SystemExit("Run is not report-eligible; pass --allow-non-eligible to render it with a visible banner.")
    texts = render(summary, [b for b in args.expect_benchmarks.split(",") if b], [v for v in args.expect_variants.split(",") if v], agreement)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(texts["results"], encoding="utf-8")
    (output.parent / "benchmark_diagnostics.tex").write_text(texts["diagnostics"], encoding="utf-8")
    (output.parent / "summary.md").write_text(texts["markdown"], encoding="utf-8")
    print(f"wrote {output} (+ benchmark_diagnostics.tex, summary.md)")
    if args.publish:
        REPORT_TABLES.parent.mkdir(parents=True, exist_ok=True)
        REPORT_TABLES.write_text(texts["results"], encoding="utf-8")
        print(f"published {REPORT_TABLES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
