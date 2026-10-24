r"""Side-by-side comparison of runs of DIFFERENT systems on the SAME tasks (v3 vs the post-hoc revision r2, 2B vs 4B).

  python evaluation/run_d2.py compare \
      --arm "v3-2B=d2-gpu-main-hcmut-v3,d2-gpu-main-labour-v3" \
      --arm "r2-2B=d2-gpu-r2-2b-hcmut-v1,d2-gpu-r2-2b-labour-v1" \
      --arm "r2-4B=d2-gpu-r2-4b-hcmut-v1,d2-gpu-r2-4b-labour-v1"

An ARM is one system (label = comma-separated run directories under evaluation/runs/, one run per benchmark). Per benchmark and variant the
tool computes, for every arm, strict success (lower bound over all planned trials: error / unknown / missing = failure), structural behaviour
match, Recall@5 over the agent's own trace, answer rate and execution-error rate, each averaged over seeds per task. A CONTRAST `LABEL=B-A`
(default for three arms: `system effect=<arm2>-<arm1>`, `model effect=<arm3>-<arm2>`; for two arms one contrast) is the paired task-level
bootstrap difference B - A (evaluation/stats.py, same unit and draws as the run analyses). Nothing is estimated: the numbers come from the
runs' trials.jsonl and analysis/private-trial-details.json; a missing analysis is an error, not a blank.

Guards: the arms must have run the same tasks (tasks_sha256 equal per benchmark) with the same seeds; the judge model of every arm is printed.
Arms whose manifest carries `protocol: r2-posthoc` are labelled "post-hoc revision evaluated on the same tasks" in every table. Strict success
is an LLM-judge estimate (not human labels); R@5 / answer rate / behaviour match / error rate are structural.

Outputs (default evaluation/comparisons/<name>/): comparison.md, comparison.tex (every table has a `LUATCHECK-COMPARE-PROVENANCE v1` comment block listing
each arm's run, commit, harness, freshness, protocol and trials hash, plus the generator command), comparison.json (all numbers).
`make report-check` validates those blocks (each run must be main, report-eligible and `current` or `pinned`).
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation import metrics as bm_metrics
from evaluation import provenance, registry, stats
from evaluation import run_benchmark as rb

RUNS_DIR = Path("evaluation/runs")
COMPARE_MARK, COMPARE_END = "% === LUATCHECK-COMPARE-PROVENANCE v1 ===", "% === END COMPARE PROVENANCE ==="
PENDING = r"\textcolor{red}{\textbf{[PENDING]}}"
BENCH_NAMES = {"hcmut_v1": "HCMUT-v1", "labour_vi_v1": "Labour-VI-v1"}
VARIANT_NAMES = {"off": "OFF", "l1": "L1", "l1_rerank": r"L1{+}rerank"}
# metric -> (label, scale for display, decimals, unit of differences)
METRICS = {
    "strict_success": ("Strict success", 100.0, 1, "pp"),
    "behaviour_match": ("Behaviour match", 100.0, 1, "pp"),
    "recall_at_5": ("Recall@5", 1.0, 3, ""),
    "answer_rate": ("Answer rate", 100.0, 1, "pp"),
    "error_rate": ("Execution-error rate", 100.0, 1, "pp"),
}
SECONDARY = ("behaviour_match", "recall_at_5", "answer_rate", "error_rate")


class CompareError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- loading

def parse_arm(spec: str) -> Tuple[str, List[str]]:
    if "=" not in spec:
        raise CompareError(f"--arm must look like LABEL=RUN[,RUN...], got {spec!r}")
    label, runs = spec.split("=", 1)
    names = [r.strip() for r in runs.split(",") if r.strip()]
    if not label.strip() or not names:
        raise CompareError(f"--arm {spec!r}: empty label or run list")
    return label.strip(), names


def _trial_value(metric: str, row: Dict[str, Any], success: Optional[bool]) -> Optional[float]:
    if metric == "strict_success":
        return 1.0 if success is True else 0.0
    if row is None:
        return None
    if metric == "behaviour_match":
        return 1.0 if (row["expected_behavior"], row["terminal_status"]) in (("answer", "answered"), ("refuse", "refused")) else 0.0
    if metric == "answer_rate":
        return 1.0 if row["terminal_status"] == "answered" else 0.0
    if metric == "error_rate":
        return 1.0 if row["system_error"] else 0.0
    if metric == "recall_at_5":
        return bm_metrics.trial_retrieval_metrics(row["ledger"], row["gold_article_ids"])["Recall@5"] if row["gold_article_ids"] else None
    raise KeyError(metric)


def load_run(run_id: str, runs_dir: Path) -> Dict[str, Any]:
    run_dir = Path(runs_dir) / run_id
    manifest_path = run_dir / "manifest.json"
    details_path = run_dir / "analysis" / "private-trial-details.json"
    summary_path = run_dir / "analysis" / "summary.json"
    for path in (manifest_path, details_path, summary_path):
        if not path.is_file():
            raise CompareError(f"{run_id}: {path} is missing (collect, judge and analyse the run first)")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = rb.latest_by_key(rb.read_rows(rb.trials_path(run_dir)))
    details = {(d["benchmark"], d["variant"], d["seed"], d["task_id"]): d for d in json.loads(details_path.read_text(encoding="utf-8"))}
    row_info = registry.describe(run_dir)
    judge = summary.get("judge_model") or {}
    git = (manifest.get("provenance") or {}).get("git") or manifest.get("git") or {}
    return {"run_id": run_id, "run_dir": run_dir, "manifest": manifest, "rows": rows, "details": details,
            "benchmarks": {b["name"]: b for b in manifest["benchmarks"]},
            "meta": {"run": run_id, "commit": git.get("commit"), "harness_version": manifest.get("harness_version"), "freshness": row_info["freshness"],
                     "kind": row_info["kind"], "report_eligible": row_info["report_eligible"], "protocol": manifest.get("protocol"),
                     "protocol_label": manifest.get("protocol_label") or rb.protocol_label(manifest.get("protocol")),
                     "trials_sha256": summary.get("runs_sha256"), "judge": judge.get("requested"),
                     "controller": (manifest.get("server") or {}).get("model_alias") or (manifest.get("model_config") or {}).get("path"),
                     "seeds": manifest.get("seeds"), "profile": (manifest.get("run_profile") or {}).get("name")}}


def per_task(run: Dict[str, Any], benchmark: str, variant: str, metric: str) -> Dict[str, float]:
    """task_id -> mean over the run's seeds of the per-trial value (tasks that do not contribute are absent)."""
    values: Dict[str, List[float]] = defaultdict(list)
    for key, detail in run["details"].items():
        if key[0] != benchmark or key[1] != variant:
            continue
        row = run["rows"].get(key)
        if metric != "strict_success" and row is None:
            continue
        value = _trial_value(metric, row, detail.get("success"))
        if value is not None:
            values[key[3]].append(value)
    return {t: float(np.mean(v)) for t, v in values.items()}


def build(arms: List[Tuple[str, List[str]]], contrasts: List[Tuple[str, str, str]], variants: List[str], runs_dir: Path = RUNS_DIR,
          benchmarks: Optional[List[str]] = None) -> Dict[str, Any]:
    if len(arms) < 2:
        raise CompareError("a comparison needs at least two --arm")
    labels = [a[0] for a in arms]
    if len(set(labels)) != len(labels):
        raise CompareError(f"arm labels must be unique: {labels}")
    loaded: Dict[str, Dict[str, Dict[str, Any]]] = {}   # arm -> benchmark -> run
    for label, names in arms:
        loaded[label] = {}
        for name in names:
            run = load_run(name, runs_dir)
            for bm in run["benchmarks"]:
                if benchmarks and bm not in benchmarks:
                    continue
                if bm in loaded[label]:
                    raise CompareError(f"arm {label}: benchmark {bm} appears in two runs ({loaded[label][bm]['run_id']}, {name})")
                loaded[label][bm] = run
    bm_names = sorted(set.intersection(*[set(v) for v in loaded.values()]))
    if not bm_names:
        raise CompareError("the arms share no benchmark")
    problems: List[str] = []
    for bm in bm_names:
        shas = {label: loaded[label][bm]["benchmarks"][bm]["tasks_sha256"] for label in labels}
        if len(set(shas.values())) != 1:
            raise CompareError(f"{bm}: the arms did not run the same tasks (tasks_sha256 differs: {shas})")
        seeds = {label: tuple(loaded[label][bm]["manifest"].get("seeds") or ()) for label in labels}
        if len(set(seeds.values())) != 1:
            problems.append(f"{bm}: seeds differ between arms {seeds}; per-task means use each arm's own seeds")
    for _, a, b in contrasts:
        if a not in labels or b not in labels:
            raise CompareError(f"contrast refers to unknown arm(s): {a}, {b} (arms: {labels})")
    table: Dict[str, Any] = {}
    for bm in bm_names:
        table[bm] = {}
        for variant in variants:
            cell: Dict[str, Any] = {"arms": {}, "contrasts": {}}
            sides: Dict[str, Dict[str, Dict[str, float]]] = {}
            for label in labels:
                run = loaded[label][bm]
                if not any(k[0] == bm and k[1] == variant for k in run["details"]):
                    cell["arms"][label] = None
                    continue
                sides[label] = {m: per_task(run, bm, variant, m) for m in METRICS}
                strict = list(sides[label]["strict_success"].values())
                cell["arms"][label] = {m: (float(np.mean(list(v.values()))) if v else None) for m, v in sides[label].items()}
                cell["arms"][label]["strict_success_ci95"] = (stats.bootstrap_mean_ci(strict) or {}).get("ci95")
                cell["arms"][label]["tasks"] = len(strict)
            for name, a, b in contrasts:
                if a in sides and b in sides:
                    cell["contrasts"][name] = {m: stats.paired_bootstrap(sides[a][m], sides[b][m]) for m in METRICS}
                else:
                    cell["contrasts"][name] = None
            table[bm][variant] = cell
    return {"arms": {label: {bm: loaded[label][bm]["meta"] for bm in bm_names} for label in labels},
            "contrasts": [{"label": n, "a": a, "b": b, "definition": f"{b} - {a}"} for n, a, b in contrasts],
            "variants": variants, "benchmarks": bm_names, "table": table, "problems": problems,
            "unit": "task (seeds averaged)", "draws": stats.BOOTSTRAP_DRAWS, "bootstrap_seed": stats.BOOTSTRAP_SEED,
            "metric_notes": {"strict_success": "LLM-judge estimate, lower bound over all planned trials (error / unknown / missing = failure); not human labels",
                             "behaviour_match": "structural: expected answer -> answered, expected refuse -> refused (clarified counts as a miss); no judge",
                             "recall_at_5": "gold-id retrieval over the agent's search+read trace, answerable tasks; not answer correctness",
                             "answer_rate": "share of trials whose terminal status is answered", "error_rate": "share of trials that are execution errors"}}


def default_contrasts(labels: List[str]) -> List[Tuple[str, str, str]]:
    if len(labels) == 2:
        return [(f"{labels[1]} - {labels[0]}", labels[0], labels[1])]
    out = [("system effect", labels[0], labels[1]), ("model effect", labels[1], labels[2])]
    return out + [(f"{labels[i]} - {labels[0]}", labels[0], labels[i]) for i in range(3, len(labels))]


def parse_contrast(spec: str) -> Tuple[str, str, str]:
    """`LABEL=B minus A` -> (label, A, B): the difference B - A. Arm labels may contain '-', hence the spelled-out separator."""
    if "=" not in spec or " minus " not in spec.split("=", 1)[1]:
        raise CompareError(f"--contrast must look like 'LABEL=ARM_B minus ARM_A', got {spec!r}")
    label, rest = spec.split("=", 1)
    b, a = rest.split(" minus ", 1)
    return label.strip(), a.strip(), b.strip()


# ----------------------------------------------------------------------------- rendering

def _fmt(metric: str, value: Optional[float]) -> str:
    _, scale, digits, _ = METRICS[metric]
    return "n/a" if value is None else f"{scale * value:.{digits}f}"


def _delta(metric: str, result: Optional[Dict[str, Any]], with_ci: bool = True) -> str:
    if not result:
        return "n/a"
    _, scale, digits, _ = METRICS[metric]
    out = f"{scale * result['diff_b_minus_a']:+.{digits}f}"
    if with_ci:
        lo, hi = result["ci95"]
        out += f" [{scale * lo:+.{digits}f}, {scale * hi:+.{digits}f}]"
    return out


def _excludes_zero(result: Optional[Dict[str, Any]]) -> bool:
    return bool(result) and (result["ci95"][0] > 0 or result["ci95"][1] < 0)


def posthoc_sentence(data: Dict[str, Any]) -> str:
    labelled = {}
    for label, per_bm in data["arms"].items():
        for meta in per_bm.values():
            if meta.get("protocol_label"):
                labelled[label] = meta["protocol_label"]
    if not labelled:
        return ""
    names = ", ".join(sorted(labelled))
    frozen = [l for l in data["arms"] if l not in labelled]
    return (f"Arm(s) {names}: {sorted(set(labelled.values()))[0]} (the revision was designed after the {', '.join(frozen) if frozen else 'earlier'} results "
            "were seen; it is not a pre-planned result)")


def render_markdown(data: Dict[str, Any], command: str) -> str:
    labels = list(data["arms"])
    lines = ["# Comparison of systems on the same tasks", "",
             f"Generated {provenance.local_now()} by `{command}` (harness `{provenance.HARNESS_VERSION}`). Paired task-level bootstrap "
             f"({data['draws']} draws, seed {data['bootstrap_seed']}, unit: {data['unit']}); differences are B - A as defined below; intervals are descriptive, "
             "no multiple-comparison correction.", ""]
    ph = posthoc_sentence(data)
    if ph:
        lines += [f"**{ph[0].upper() + ph[1:]}.**", ""]
    lines += ["## Arms", "", "| arm | benchmark | run | controller | commit | harness | freshness | protocol | judge |", "|---|---|---|---|---|---|---|---|---|"]
    for label, per_bm in data["arms"].items():
        for bm, m in per_bm.items():
            lines.append(f"| {label} | {bm} | {m['run']} | {m['controller']} | {str(m['commit'])[:7]} | {m['harness_version']} | {m['freshness']} | "
                         f"{m['protocol'] or 'frozen v3 protocol'} | {m['judge']} |")
    lines += ["", "## Contrasts", ""] + [f"- **{c['label']}** = {c['definition']}" for c in data["contrasts"]] + [""]
    for p in data["problems"]:
        lines.append(f"- WARNING: {p}")
    lines += ["", "Metrics: " + "; ".join(f"{METRICS[k][0]}: {v}" for k, v in data["metric_notes"].items()), ""]
    for metric, (name, scale, digits, unit) in METRICS.items():
        lines += [f"## {name}" + (" (%, differences in pp)" if unit == "pp" else " (differences absolute)"), "",
                  "| benchmark | variant | tasks | " + " | ".join(labels) + " | " + " | ".join(c["label"] for c in data["contrasts"]) + " |",
                  "|---|---|---|" + "---|" * (len(labels) + len(data["contrasts"]))]
        for bm in data["benchmarks"]:
            for variant in data["variants"]:
                cell = data["table"][bm][variant]
                vals = []
                for label in labels:
                    a = cell["arms"].get(label)
                    if not a:
                        vals.append("n/a")
                        continue
                    text = _fmt(metric, a[metric])
                    if metric == "strict_success" and a.get("strict_success_ci95"):
                        lo, hi = a["strict_success_ci95"]
                        text += f" [{100 * lo:.0f}-{100 * hi:.0f}]"
                    vals.append(text)
                diffs = [_delta(metric, (cell["contrasts"].get(c["label"]) or {}).get(metric)) for c in data["contrasts"]]
                n = next((a["tasks"] for a in cell["arms"].values() if a), "n/a")
                lines.append(f"| {bm} | {variant} | {n} | " + " | ".join(vals) + " | " + " | ".join(diffs) + " |")
        lines.append("")
    return "\n".join(lines) + "\n"


def _provenance_block(table: str, data: Dict[str, Any], command: str) -> str:
    out = [COMPARE_MARK, f"% table: {table}", f"% generator: {command}", f"% generated_local: {provenance.local_now()}",
           f"% unit: {data['unit']}; draws {data['draws']}; bootstrap_seed {data['bootstrap_seed']}"]
    for c in data["contrasts"]:
        out.append(f"% contrast: {c['label']} = {c['definition']}")
    for label, per_bm in data["arms"].items():
        for bm, m in per_bm.items():
            out.append(f"% arm: {label} | benchmark: {bm} | run: {m['run']} | commit: {m['commit']} | harness_version: {m['harness_version']} | "
                       f"freshness: {m['freshness']} | protocol: {m['protocol'] or 'frozen'} | trials_sha256: {m['trials_sha256']}")
    out.append(COMPARE_END)
    return "\n".join(out)


def _esc(text: Any) -> str:
    return str(text).replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("%", r"\%").replace("&", r"\&").replace("#", r"\#")


def render_latex(data: Dict[str, Any], command: str) -> str:
    labels = list(data["arms"])
    contrasts = data["contrasts"]
    ph = posthoc_sentence(data)
    ph_tex = (r"\textbf{" + _esc(ph[0].upper() + ph[1:]) + r".} ") if ph else ""
    judges = sorted({m["judge"] or "unknown" for per_bm in data["arms"].values() for m in per_bm.values()})
    sources = "; ".join(f"{_esc(label)}: " + ", ".join(f"{_esc(m['run'])} @ {_esc(str(m['commit'])[:7])} ({_esc(m['freshness'])})" for m in per_bm.values())
                        for label, per_bm in data["arms"].items())
    tail = (rf"\par\vspace{{2pt}}{{\tiny\textit{{Source: {sources}. Harness {_esc(provenance.HARNESS_VERSION)} comparison; differences are paired task-level "
            rf"bootstrap (B$-$A, {data['draws']} draws), intervals descriptive.}}}}")
    contrast_text = "; ".join(f"{_esc(c['label'])} = {_esc(c['b'])} $-$ {_esc(c['a'])}" for c in contrasts)
    # table 1: strict success
    head = ("Benchmark & Variant & " + " & ".join(_esc(l) + r" Succ.\ (\%)" for l in labels) + " & " + " & ".join(_esc(c["label"]) + r" (pp)" for c in contrasts) + r"\\")
    rows: List[str] = []
    for bm in data["benchmarks"]:
        for i, variant in enumerate(data["variants"]):
            cell = data["table"][bm][variant]
            lead = rf"\multirow{{{len(data['variants'])}}}{{*}}{{{_esc(BENCH_NAMES.get(bm, bm))}}}" if i == 0 else ""
            vals = []
            for label in labels:
                a = cell["arms"].get(label)
                if not a:
                    vals.append(PENDING)
                    continue
                text = _fmt("strict_success", a["strict_success"])
                if a.get("strict_success_ci95"):
                    text += rf"\,{{\scriptsize[{100 * a['strict_success_ci95'][0]:.0f}--{100 * a['strict_success_ci95'][1]:.0f}]}}"
                vals.append(text)
            diffs = []
            for c in contrasts:
                r = (cell["contrasts"].get(c["label"]) or {}).get("strict_success")
                if not r:
                    diffs.append(PENDING)
                    continue
                lo, hi = r["ci95"]
                diffs.append(f"{100 * r['diff_b_minus_a']:+.1f}\\,{{\\scriptsize[{100 * lo:+.1f},{100 * hi:+.1f}]}}" + ("$^{*}$" if _excludes_zero(r) else ""))
            rows.append(" & ".join([lead, VARIANT_NAMES.get(variant, _esc(variant))] + vals + diffs) + r"\\")
        rows.append(r"\midrule")
    rows.pop()
    cols = "@{}ll" + "r" * (len(labels) + len(contrasts)) + "@{}"
    caption1 = (ph_tex + "Strict success per variant (LLM-judge estimate, \\textbf{not human labels}; lower bound over all planned trials, errors and judge-unknown count as failures; "
                f"seeds averaged per task; judge: {_esc(', '.join(judges))}), with the paired task-level bootstrap differences {contrast_text}. "
                "$^{*}$: the 95\\% interval excludes 0 (descriptive, no multiple-comparison correction). Same tasks in every arm.")
    t1 = "\n".join([_provenance_block("tab:compare-success", data, command), r"\begin{table}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{3pt}",
                    r"\resizebox{\textwidth}{!}{%", rf"\begin{{tabular}}{{{cols}}}", r"\toprule", head, r"\midrule", *rows, r"\bottomrule", r"\end{tabular}}",
                    r"\caption{" + caption1 + "}", r"\label{tab:compare-success}", tail, r"\end{table}"])
    # table 2: secondary metrics, compact cells "a / b / c" and "d1 / d2"
    head2 = "Benchmark & Variant & " + " & ".join(rf"{METRICS[m][0]} ({' / '.join(_esc(l) for l in labels)}) & $\Delta$ ({' / '.join(_esc(c['label']) for c in contrasts)})" for m in SECONDARY) + r"\\"
    rows2: List[str] = []
    for bm in data["benchmarks"]:
        for i, variant in enumerate(data["variants"]):
            cell = data["table"][bm][variant]
            lead = rf"\multirow{{{len(data['variants'])}}}{{*}}{{{_esc(BENCH_NAMES.get(bm, bm))}}}" if i == 0 else ""
            parts = [lead, VARIANT_NAMES.get(variant, _esc(variant))]
            for m in SECONDARY:
                parts.append(" / ".join(_fmt(m, (cell["arms"].get(l) or {}).get(m)) for l in labels))
                ds = []
                for c in contrasts:
                    r = (cell["contrasts"].get(c["label"]) or {}).get(m)
                    ds.append(_delta(m, r, with_ci=False) + ("$^{*}$" if _excludes_zero(r) else ""))
                parts.append(" / ".join(ds))
            rows2.append(" & ".join(parts) + r"\\")
        rows2.append(r"\midrule")
    rows2.pop()
    caption2 = (ph_tex + "Structural metrics per variant (no judge): behaviour match (expected answer $\\to$ answered, expected refuse $\\to$ refused), Recall@5 of gold ids over the agent's "
                "trace (answerable tasks, a retrieval proxy, not answer correctness), answer rate and execution-error rate; percentages except Recall@5. Each cell lists the arms in the order "
                f"{_esc(' / '.join(labels))}; $\\Delta$ lists {contrast_text} in pp (Recall@5 absolute). $^{{*}}$: the paired 95\\% bootstrap interval excludes 0 (descriptive).")
    t2 = "\n".join([_provenance_block("tab:compare-structural", data, command), r"\begin{table}[t]", r"\centering", r"\scriptsize", r"\setlength{\tabcolsep}{2pt}",
                    r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{@{}ll" + "rr" * len(SECONDARY) + "@{}}", r"\toprule", head2, r"\midrule", *rows2, r"\bottomrule", r"\end{tabular}}",
                    r"\caption{" + caption2 + "}", r"\label{tab:compare-structural}", tail, r"\end{table}"])
    return ("% Generated by evaluation/compare_runs.py. Do not edit by hand. Requires: booktabs, multirow, graphicx, xcolor.\n" + t1 + "\n\n" + t2 + "\n")


def write_outputs(data: Dict[str, Any], out_dir: Path, command: str) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {"markdown": out_dir / "comparison.md", "latex": out_dir / "comparison.tex", "json": out_dir / "comparison.json"}
    paths["markdown"].write_text(render_markdown(data, command), encoding="utf-8")
    paths["latex"].write_text(render_latex(data, command), encoding="utf-8")
    paths["json"].write_text(json.dumps({**data, "generated_local": provenance.local_now(), "generator": command, "harness_version": provenance.HARNESS_VERSION},
                                        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def run(arm_specs: List[str], contrast_specs: Optional[List[str]], variants: List[str], out_dir: Optional[str], benchmarks: Optional[List[str]],
        command: str, runs_dir: Path = RUNS_DIR) -> Dict[str, Any]:
    arms = [parse_arm(s) for s in arm_specs]
    contrasts = [parse_contrast(s) for s in contrast_specs] if contrast_specs else default_contrasts([a[0] for a in arms])
    data = build(arms, contrasts, variants, runs_dir, benchmarks)
    target = Path(out_dir) if out_dir else Path("evaluation/comparisons") / re.sub(r"[^A-Za-z0-9_.-]+", "_", "_vs_".join(a[0] for a in arms))
    data["output_dir"] = str(target)
    data["files"] = {k: str(v) for k, v in write_outputs(data, target, command).items()}
    return data


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", action="append", required=True, help="LABEL=RUN[,RUN...] (repeat; the first arm is the reference)")
    parser.add_argument("--contrast", action="append", help="'LABEL=ARM_B minus ARM_A' (difference B - A); default: system effect / model effect for three arms")
    parser.add_argument("--variants", default="off,l1,l1_rerank")
    parser.add_argument("--benchmarks", nargs="+")
    parser.add_argument("--out-dir")
    args = parser.parse_args(argv)
    import os
    os.chdir(REPO_ROOT)
    try:
        data = run(args.arm, args.contrast, [v for v in args.variants.split(",") if v], args.out_dir, args.benchmarks,
                   "python evaluation/run_d2.py compare " + " ".join(f"--arm {a!r}" for a in args.arm))
    except CompareError as exc:
        print(f"CompareError: {exc}", file=sys.stderr)
        return 1
    print(Path(data["files"]["markdown"]).read_text(encoding="utf-8"))
    print(f"wrote {data['output_dir']}/ (comparison.md, comparison.tex, comparison.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
