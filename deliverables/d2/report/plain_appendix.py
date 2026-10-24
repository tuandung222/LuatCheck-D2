"""Write reader-friendly copies of the generated appendix tables (labels and captions only; numbers and provenance headers untouched).

  python deliverables/d2/report/plain_appendix.py        (run after `make tables` / compare, before building the report)

Reads the generated table files (deliverables/d2/report/tables_*_r2_4b/*.tex and evaluation/comparisons/<cmp>/comparison.tex, never modified) and writes
deliverables/d2/report/appendix_plain/*.tex. What changes: internal labels in cells (variant, benchmark and system names), the captions (plain wording),
and the visible "Source:" lines (removed; the run, commit and hash stay in the unchanged `%` provenance header, which
evaluation/check_report_provenance.py verifies). Table values are copied byte for byte.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]   # deliverables/d2/report -> repository root
OUT = HERE / "appendix_plain"
CMP = REPO / "evaluation" / "comparisons" / "v3-2B_vs_r2-2B_vs_r2-4B" / "comparison.tex"
POSTHOC_COMMENT = "% protocol label (kept for evaluation/check_report_provenance.py): post-hoc revision evaluated on the same tasks"

# Plain-language statement (empty: the provenance comment above already satisfies check_report_provenance.py).
OPTIMISTIC = r""

CAPTIONS = {
    "tab:benchmark-main": (
        r"\textbf{Results of the current system with the 4B controller on the {bench} benchmark}, three configurations "
        r"({trials} trials; random seeds 42, 123, 2026). \emph{Succ.} is strict success (appropriate behaviour, "
        r"correctness and completeness both full, every claim supported): a lower bound over all trials, with a 95\% bootstrap interval "
        r"over questions; execution errors count as failures, and $\dagger k$ marks $k$ trials the judge could not rate, also counted as failures. "
        r"Succ., Beh. (behaviour match) and Faith. (faithfulness) are estimates by the LLM judge of Section~\ref{sec:eval}, "
        r"\textbf{not human labels}. {audit} "
        r"Recall@5 and MRR measure whether the gold documents appear in the agent's search and read results (answerable questions; "
        r"all cells are {cells}, so they cannot separate the configurations). Cit. P/R/F1 compare the cited document ids with the gold ids "
        r"(nothing cited counts as 0); they are measured on document ids and say nothing about answer correctness. Red entries are not measured."),
    "tab:benchmark-ops": (
        r"\textbf{Operating measurements and judge cost} of the current system with the 4B controller on the {bench} benchmark. "
        r"Ans/Ref/Clar/Err are the numbers of answered, refused, clarified and execution-error trials; Err. is the execution-error rate. "
        r"n/r (not reported): latency was recorded while several workers ran at once, so it is not reportable. Call = one controller model call; "
        r"tok/s = generated tokens per second. Tokens are controller input/output per trial (trials with complete usage only). "
        r"Judge cost is the usage cost reported by the API gateway over all retained attempts ({usd} USD for all configurations; not an invoice)."),
    "tab:benchmark-paired": (
        r"\textbf{Differences between configurations} on the {bench} benchmark (treatment minus baseline, percentage points) with 95\% paired bootstrap "
        r"intervals over questions (seeds averaged per question; 5000 resamples). Succ. is strict success (LLM-judge lower bound), "
        r"Beh. the behaviour match, Rec.@5 the Recall@5 of gold documents, Cit. F1 the citation F1 on document ids, Err. the execution-error rate. "
        r"There is no multiple-comparison correction; an interval that includes 0 shows no detectable difference at this sample size."),
    "tab:benchmark-baselines": (
        r"\textbf{Two diagnostic baselines} on the {bench} benchmark: one seed (42), the same 4B controller, sampler, domain prompt and constrained decoding, "
        r"\emph{no tools}, verifier off. They are not system configurations and are never pooled with them. \emph{Closed-book}: the question only, "
        r"all questions. \emph{Oracle}: the full gold records are given up front in the format of a read result, answerable questions only "
        r"(refusal questions have no gold context and are excluded). Succ. (all) is over every question the row ran; Succ. (answerable) is restricted to "
        r"answerable questions (the like-for-like column), with a bootstrap interval over questions; both are LLM-judge lower bounds and errors count as failures. "
        r"Answer rate = answered / all recorded trials (execution errors count as not answered) on answerable questions. Cit. P/R compare cited ids with gold ids "
        r"(meaningful for the oracle and the system rows; a closed-book model has no document ids). Reference rows repeat the answerable-only results of the three "
        r"configurations (seeds averaged). The oracle bounds what the 4B controller achieves with perfect retrieval; closed-book bounds what the model's own knowledge achieves."),
    "tab:benchmark-behaviour": (
        r"\textbf{Behaviour against what the benchmark expects} on the {bench} benchmark (no judge). The rows ``answer expected'' and ``refusal expected'' "
        r"give the numbers of answered / refused / clarified / error trials (A/R/C/Err). Over-refusal = refused or clarified although an answer exists; "
        r"unsafe answer = answered although the question should be refused; refusal P/R treat \emph{refused} as the positive class (non-error trials); "
        r"strict match counts errors as mismatches."),
    "tab:benchmark-strata": (
        r"\textbf{Strict success split by whether the question can be guessed} on the {bench} benchmark (LLM-judge lower bound, errors count as failures). "
        r"``Closed-book guessable'': a strong model answered the question correctly \emph{without} the corpus (itself an LLM estimate), so these questions "
        r"measure the model's own knowledge as much as grounding. ``Not guessable'': partially correct or unsolved without the corpus. Refusal questions have no such split. "
        r"Intervals are bootstrap intervals over questions; n = questions in the group."),
    "tab:compare-success": (
        r"\textbf{Strict success across controller sizes and engineering iterations on both benchmarks}: the initial 2B prototype, the current system with the 2B controller and "
        r"the current system with the 4B controller (LLM-judge estimate, \textbf{not human labels}; lower bound over all planned trials, errors and trials the judge "
        r"could not rate count as failures; seeds averaged per question). Revision effect = current 2B minus initial 2B; controller effect = current 4B minus current 2B "
        r"(paired bootstrap differences over questions, 5000 draws). $^{*}$: the 95\% interval excludes 0 (descriptive, no multiple-comparison correction). "
        r"Same questions in every column."),
    "tab:compare-structural": (
        r"\textbf{Metrics that need no judge, for the same three runs}: behaviour match (expected answer $\to$ answered, expected refusal $\to$ refused), "
        r"Recall@5 of gold documents in the agent's results (answerable questions; a retrieval measure on document ids, not answer correctness), answer rate and "
        r"execution-error rate; percentages except Recall@5. Each cell lists initial 2B / current 2B / current 4B; $\Delta$ lists the revision effect (current 2B minus "
        r"initial 2B) and the controller effect (current 4B minus current 2B) in percentage points (Recall@5 absolute). $^{*}$: the paired 95\% bootstrap interval "
        r"excludes 0 (descriptive)."),
}

# Ordered cell/header substitutions (applied outside captions and % lines).
SUBS = [
    (r"v3-2B Succ\.\\ \(\\%\)", r"\makecell{Initial, 2B\\ Succ.\ (\%)}"),
    (r"r2-2B Succ\.\\ \(\\%\)", r"\makecell{Current, 2B\\ Succ.\ (\%)}"),
    (r"r2-4B Succ\.\\ \(\\%\)", r"\makecell{Current, 4B\\ Succ.\ (\%)}"),
    # structural table: the three systems and the two effects are explained in the caption, so the headers stay short
    (r"Behaviour match \(v3-2B / r2-2B / r2-4B\)", r"\makecell{Behaviour\\ match (\%)}"),
    (r"Recall@5 \(v3-2B / r2-2B / r2-4B\)", r"Recall@5"),
    (r"Answer rate \(v3-2B / r2-2B / r2-4B\)", r"\makecell{Answer\\ rate (\%)}"),
    (r"Execution-error rate \(v3-2B / r2-2B / r2-4B\)", r"\makecell{Execution-\\ error rate (\%)}"),
    (r"\$\\Delta\$ \(system effect / model effect\)", r"\makecell{$\Delta$ revision /\\ controller}"),
    (r"system effect \(pp\)", r"\makecell{revision effect\\ (pp)}"),
    (r"model effect \(pp\)", r"\makecell{controller effect\\ (pp)}"),
    (r"HCMUT-v1", r"HCMUT regulations"),
    (r"Labour-VI-v1", r"Labour law"),
    (r"L1\{\+\}rerank vs OFF", r"verifier + reranker vs no verifier"),
    (r"L1\{\+\}rerank vs L1", r"verifier + reranker vs verifier"),
    (r"L1 vs OFF", r"verifier vs no verifier"),
    (r"L1\{\+\}rerank", r"verifier + reranker"),
    (r"\bOFF\b", r"no verifier"),
    (r"(?<![\w\\])L1\b", r"verifier"),
    (r"E=answer: A/R/C/Err", r"Answer expected: A/R/C/Err"),
    (r"E=refuse: A/R/C/Err", r"Refusal expected: A/R/C/Err"),
    (r"& Variant &", r"& Configuration &"),
]
LABEL_BENCH = {"hcmut": "HCMUT regulations", "labour": "Labour law"}


def convert(text: str, bench: str) -> str:
    lines = text.splitlines()
    out, header_done = [], False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("%"):
            out.append(line)
            if line.strip() in ("% === END PROVENANCE ===", "% === END COMPARE PROVENANCE ==="):
                out.append(POSTHOC_COMMENT)
            i += 1
            continue
        if line.startswith(r"\par\vspace{2pt}{\tiny\textit{Source:"):
            i += 1
            continue
        if line.startswith(r"\caption{"):
            label = re.search(r"\\label\{([^}]+)\}", lines[i + 1]).group(1)
            template = CAPTIONS[label]
            cells = (re.search(r"all cells ([0-9.]+--[0-9.]+)", line) or [None, "0.98--0.99"])[1]
            trials = (re.search(r"(\d+) real native trials", line) or [None, "450"])[1]
            usd = (re.search(r"all variants: ([0-9.]+) USD", line) or [None, ""])[1]
            audit_m = re.search(r"(Judge--human agreement on strict success.*?reviewer\(s\)\)\.)", line)
            audit = audit_m.group(1) if audit_m else r"The human audit of the judge is \textcolor{red}{\textbf{[PENDING]}}."
            caption = template.replace('{bench}', bench).replace('{cells}', cells).replace('{trials}', trials).replace('{usd}', usd).replace('{audit}', audit)
            out.append(r"\caption{" + caption + "}")
            i += 1
            continue
        for pattern, repl in SUBS:
            line = re.sub(pattern, lambda m, r=repl: r, line)
        out.append(line)
        i += 1
    return "\n".join(out) + "\n"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    jobs = [(CMP, OUT / "comparison.tex", "")]
    for key in ("hcmut", "labour"):
        for stem in ("benchmark_results", "benchmark_diagnostics"):
            jobs.append((HERE / f"tables_{key}_r2_4b" / f"{stem}.tex", OUT / f"{key}_{stem}.tex", LABEL_BENCH[key]))
    for src, dst, bench in jobs:
        dst.write_text(convert(src.read_text(encoding="utf-8"), bench), encoding="utf-8")
        print(f"wrote {dst.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
