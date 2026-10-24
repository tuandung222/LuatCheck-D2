# Documentation

Project documentation of LuatCheck (CO5151, Group 8). Course deliverables (reports, slides, demo) live in
[`../deliverables/`](../deliverables/README.md); recorded experiment runs live in `../evaluation/runs/`.

## Layout

| Folder | What goes here | Start with |
|---|---|---|
| [`guides/`](guides/) | How-to documents: set up machines, run the benchmarks, reproduce the reported numbers, do the human audit | [REPRODUCE_D2.md](guides/REPRODUCE_D2.md) |
| [`reference/`](reference/) | Stable descriptions of the current system: architecture, benchmarks and metrics (with formulas), the L1 verifier, the web UI API | [architecture.md](reference/architecture.md) |
| [`design/`](design/) | Component design notes with the measurements behind each choice (ingestion, indexing, reranker, model components, wiring, benchmarking, span citations) | [wiring.md](design/wiring.md) |
| [`plans/`](plans/) | Plans and proposals: the D2 revision, the benchmark v2 proposal, completed execution plans | [D2_REVISION_L1_BONSAI4B.md](plans/D2_REVISION_L1_BONSAI4B.md) |
| [`reviews/`](reviews/) | Dated review records (benchmark quality, metrics, failure analysis, requirement gaps, UI reviews); historical, never rewritten | [v3_failure_analysis_2026-10-24.md](reviews/v3_failure_analysis_2026-10-24.md) |
| [`project/`](project/) | Project management: D2 work items, team inputs, and [`handoffs/`](project/handoffs/) between work sessions | [HANDOFF_FINAL_2026-10-25.md](project/handoffs/HANDOFF_FINAL_2026-10-25.md) |
| [`images/`](images/) | Figures used by the README and the report (architecture drawing, LaTeX source included) | |
| `materials/` | Source documents with provenance: HCMUT and labour-law PDFs, benchmark sources, the D2 course requirements | [materials/d2/README.md](materials/d2/README.md) |

## Guides

- [REPRODUCE_D2.md](guides/REPRODUCE_D2.md): every reported number, step by step, with the run inventory and judge costs.
- [RUNBOOK_D2.md](guides/RUNBOOK_D2.md): machine setup (Mac and GPU server) and the D2 run matrix.
- [HUMAN_AUDIT_GUIDE.md](guides/HUMAN_AUDIT_GUIDE.md): how the team labels judge packets to measure judge–human agreement.

## Reference

- [architecture.md](reference/architecture.md): modules and data flow.
- [BENCHMARKS_AND_METRICS.md](reference/BENCHMARKS_AND_METRICS.md): the two frozen benchmarks and every metric with its formula and limits.
- [L1_VERIFIER.md](reference/L1_VERIFIER.md): how the lexical citation verifier works and what it changes, with numbers.
- [web-ui-api.md](reference/web-ui-api.md): the FastAPI backend used by the demo UI.

## Project

- [D2_WORK_ITEMS.md](project/D2_WORK_ITEMS.md): work done for D2, without owners.
- [TEAM_INPUTS_D2.md](project/TEAM_INPUTS_D2.md): the form for team-owned inputs (audit labels, contributions, presenters).
- [handoffs/](project/handoffs/): session handoffs; the latest supersedes earlier ones where they differ.

## Conventions

- One topic per file; a file's folder says what kind of document it is (how-to, reference, design, plan, review, project).
- Dated records (reviews, handoffs) carry the date in the file name (`_YYYY-MM-DD`) and are not rewritten later; corrections go in a newer record.
- Numbers in any document must come from a recorded run in `evaluation/runs/`; name the run or the comparison file they come from.
- `materials/` is referenced by the hash-locked corpora in `data/corpus/`: do not move or rename anything in it.
- Link with relative paths from the linking file, so links work on GitHub and in a local checkout.
