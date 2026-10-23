"""Render the controller-diagnostic comparison table from stored run artifacts (no inference).

Compares the seed-42 trials of the main Qwen run with diagnostic runs that change only the
controller model. Operational/source-ID measurements only; no correctness score is computed.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from evaluation.score_reviewed_runs import read_runs


def summarize(run_dir, seed):
    manifest, rows = read_runs(run_dir)
    rows = [r for r in rows if r["seed"] == seed]
    answerable = [r for r in rows if r["gold_article_ids"]]
    agree = sum({"answered": "answer", "refused": "refuse", "clarified": "clarify"}.get(r["terminal_status"]) == r["expected_behavior"]
                for r in rows)
    costs = [((c.get("native_response") or {}).get("usage") or {}).get("cost")
             for r in rows for c in r["ledger"]["llm_calls"]]
    known = [c for c in costs if isinstance(c, (int, float))]
    return {"trials": len(rows),
            "status": "/".join(str(sum(r["terminal_status"] == s for r in rows)) for s in ["answered", "refused", "clarified", "error"]),
            "agree": f"{agree}/{len(rows)}",
            "recall5": float(np.mean([r["retrieval"]["Recall@5"] for r in answerable])),
            "cit_p": float(np.mean([r["citation"]["citation_precision"] for r in answerable])),
            "cit_r": float(np.mean([r["citation"]["citation_recall"] for r in answerable])),
            "p50": float(np.percentile([r["wall_ms"] / 1000 for r in rows], 50)),
            "repairs": sum(r["ledger"]["repairs_count"] for r in rows),
            "cost": (sum(known) if known and len(known) == len(costs) else None),
            "provider": manifest["model"]["provider"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", nargs=2, action="append", metavar=("LABEL", "RUN_DIR"), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    cols = [(label, summarize(d, args.seed)) for label, d in args.run]
    def row(name, fn):
        return name + " & " + " & ".join(fn(s) for _, s in cols) + r"\\"
    lines = [r"\begin{table}[H]\centering\footnotesize",
             r"\begin{tabularx}{\textwidth}{@{}L{5.2cm}" + "X" * len(cols) + "@{}}\\toprule",
             "Seed " + str(args.seed) + ", OFF + ON & " + " & ".join(label for label, _ in cols) + r"\\\midrule",
             row("Trials", lambda s: str(s["trials"])),
             row("Answered / refused / clarified / error", lambda s: s["status"]),
             row("Terminal action = expected action", lambda s: s["agree"]),
             row("Trajectory Recall@5", lambda s: f"{s['recall5']:.3f}"),
             row("Citation-ID precision / recall", lambda s: f"{s['cit_p']:.3f} / {s['cit_r']:.3f}"),
             row("L1 repairs", lambda s: str(s["repairs"])),
             row("Latency p50 (s)", lambda s: f"{s['p50']:.1f}"),
             row("Gateway-reported cost (USD)", lambda s: (f"{s['cost']:.2f}" if s["cost"] is not None
                                                          else ("local" if s["provider"] != "gateway" else "unknown"))),
             r"\bottomrule\end{tabularx}",
             r"\caption{Controller diagnostic on the same tasks, corpus, retrieval, budgets and L1 checks. The diagnostic runs use the "
             r"post-collection prompt revision; model-specific settings are given in the text. Operational and source-ID measurements, "
             r"not correctness. Diagnostic runs are not report-eligible main results.}\label{tab:diag}",
             r"\end{table}"]
    Path(args.output).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
