# Documentation

Project documentation of LuatCheck. Course deliverables (reports, slides, demo) live in [`../deliverables/`](../deliverables/README.md); recorded experiment runs live in `../evaluation/runs/`.

## Layout

| Folder | What goes here | Start with |
|---|---|---|
| [`reference/`](reference/) | Stable specifications of the current system: architecture, rule-based L1 citation verifier, benchmarks and metrics (with formulas), and the Web UI API | [CITATION_VERIFIER_L1.md](reference/CITATION_VERIFIER_L1.md) |
| [`guides/`](guides/) | How-to documents: set up machines, run the benchmarks, reproduce the reported numbers, do the human audit | [REPRODUCE_D2.md](guides/REPRODUCE_D2.md) |
| [`design/`](design/) | Component design notes with the measurements behind each choice (ingestion, indexing, reranker, model components, wiring, benchmarking, span citations) | [wiring.md](design/wiring.md) |
| [`images/`](images/) | Figures and demo GIFs used by the README and the report (`demo/`, `architecture.png`) | |
| [`materials/`](materials/) | Source documents with provenance: HCMUT and labour-law PDFs, benchmark sources | [materials/d2/README.md](materials/d2/README.md) |
| [`historical/`](historical/) | Archived historical development plans, internal session handoffs, dated review notes, and retired pre-D2 status records | [historical/README.md](historical/README.md) |

## Reference

- [CITATION_VERIFIER_L1.md](reference/CITATION_VERIFIER_L1.md): full specification, rules, failure examples, and empirical audit of the rule-based L1 citation verifier (`src/verifier/lexical_grounding_v2.py`).
- [architecture.md](reference/architecture.md): modules and data flow.
- [BENCHMARKS_AND_METRICS.md](reference/BENCHMARKS_AND_METRICS.md): the two frozen benchmarks and every metric with its formula and limits.
- [web-ui-api.md](reference/web-ui-api.md): the FastAPI backend used by the demo UI.

## Guides

- [REPRODUCE_D2.md](guides/REPRODUCE_D2.md): every reported number, step by step, with the run inventory and judge costs.
- [RUNBOOK_D2.md](guides/RUNBOOK_D2.md): machine setup (Mac and GPU server) and the run matrix.
- [HUMAN_AUDIT_GUIDE.md](guides/HUMAN_AUDIT_GUIDE.md): how the team labels judge packets to measure judge–human agreement.
