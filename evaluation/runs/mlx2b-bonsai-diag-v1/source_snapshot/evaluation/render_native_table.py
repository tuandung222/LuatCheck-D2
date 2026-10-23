"""Render measured D2 operational results; semantic evidence remains pending."""
import argparse
from pathlib import Path

from evaluation.analyze_native import analyze


def render(run_dir, tasks):
    result = analyze(run_dir, tasks)
    modes = [result["modes"][m] for m in ("off", "l1_on")]

    def values(key, fmt):
        return [r"\textcolor{red}{Not measured}" if m[key] is None else fmt(m[key]) for m in modes]

    rows = []
    for label, key, fmt in [
        ("Recorded trials (errors included)", "trials", str),
        ("Answered / refused / clarified", None, None),
        ("Execution errors (included)", "execution_errors", str),
        ("Answer coverage (all trials)", "answer_coverage", lambda v: f"{100*v:.1f}\\%"),
        ("Trajectory Recall@5", "trajectory_recall5", lambda v: f"{v:.3f}"),
        ("Trajectory Hit@5", "trajectory_hit5", lambda v: f"{v:.3f}"),
        ("Trajectory MRR", "trajectory_mrr", lambda v: f"{v:.3f}"),
        ("Citation-ID precision", "citation_id_precision", lambda v: f"{v:.3f}"),
        ("Citation-ID recall", "citation_id_recall", lambda v: f"{v:.3f}"),
        ("Latency p50 / p95 (s)", None, None),
        ("Input tokens (all calls)", "input_tokens", lambda v: f"{v:,}"),
        ("Output tokens (all calls)", "output_tokens", lambda v: f"{v:,}"),
        ("Native calls", "native_calls", str),
        ("Repairs", "repairs_total", str),
        ("Model service-hours", "native_service_hours", lambda v: f"{v:.4f}"),
    ]:
        if label.startswith("Answered"):
            cells = [f'{m["answered"]} / {m["refused"]} / {m["clarified"]}' for m in modes]
        elif label.startswith("Latency"):
            cells = [f'{m["latency_p50_seconds"]:.2f} / {m["latency_p95_seconds"]:.2f}' for m in modes]
        else:
            cells = values(key, fmt)
        rows.append(label + " & " + " & ".join(cells) + r"\\")
    rows += [r"Semantic task success & \pending{judge / human audit} & \pending{judge / human audit}\\",
             r"Claim support / unsupported rate & \pending{judge / human audit} & \pending{judge / human audit}\\",
             r"Hardware GPU-active hours & \pending{not measured} & \pending{not measured}\\"]
    header = (r"\begin{table}[H]\centering\footnotesize" "\n"
              r"\begin{tabularx}{\textwidth}{@{}L{5.0cm}XX@{}}\toprule Metric & OFF & L1 ON\\\midrule" "\n")
    counts = " / ".join(str(m["answerable_trials"]) for m in modes)
    phase = "Main collection" if result["phase"] == "main" else "Pilot diagnostic only; excluded from main results"
    caption = (phase + f": {result['trials']} real native trials. Retrieval and citation-ID metrics average "
               + counts + " answerable trials (OFF / ON), with non-answers included. These are "
               "operational/source-ID measurements, not semantic correctness. Model service-hours "
               "are backend durations, not GPU-active hours.")
    footer = ("\n" r"\bottomrule\end{tabularx}" "\n"
              + r"\caption{" + caption + "}\n" + r"\end{table}" "\n")
    return header + "\n".join(rows) + footer


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    Path(args.output).write_text(render(args.run_dir, args.tasks))
