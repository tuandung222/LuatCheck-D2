# D2 work items (to assign)

> Listed 2026-10-24 19:05 +07. Owners are blank on purpose: the group fills the **Owner** column. "Evidence" points to
> the files, runs or commits that show the work. Status: ✅ done · ⏳ in progress · ☐ not started.

## 1. Planning and requirements

| # | Item | Evidence | Status | Owner |
|---|---|---|---|---|
| 1.1 | Map the lecturer's D2 requirements and rubric to the project (traceability matrix, gaps ranked by rubric weight) | `docs/reviews/d2_requirements_gap_2026-10-23.md` | ✅ | |
| 1.2 | D2 completion plan, tonight's execution plan, handoff note | `docs/plans/D2_COMPLETION_PLAN.md`, `D2_TONIGHT_EXECUTION_PLAN.md`, `docs/HANDOFF_2026-10-24.md` | ✅ | |
| 1.3 | Decide the D2 design: Bonsai 2B controller, two benchmarks, variants OFF / L1 / L1+rerank, GPU accuracy + Mac latency | plans above | ✅ | |
| 1.4 | Gap analysis vs a production legal assistant (positioning and limitations) | chat summary; report limitations | ✅ | |

## 2. Benchmarks and data

| # | Item | Evidence | Status | Owner |
|---|---|---|---|---|
| 2.1 | Build the HCMUT academic-regulations benchmark (10 documents, 50 tasks) | `evaluation/benchmarks/hcmut_v1/` | ✅ | |
| 2.2 | Build the labour-law benchmark (10 documents, 50 tasks) | `evaluation/benchmarks/labour_vi_v1/` | ✅ | |
| 2.3 | Collect and ingest the source documents (PDF/DOCX → records with provenance) | `data/corpus/*_v1.json`, `docs/materials/*-sources/` | ✅ | |
| 2.4 | Freeze both benchmarks with hash locks | `benchmark.lock.json` in each benchmark | ✅ | |
| 2.5 | Benchmark quality audit (gold correctness, verbatim evidence, difficulty, closed-book guessability) | `docs/reviews/benchmark_quality_2026-10-23.md`, `evaluation/benchmarks/qa/` | ✅ | |
| 2.6 | Human review of all 100 tasks | `docs/reviews/benchmark_human_review_2026-10-23.md` | ✅ | |
| 2.7 | Proposal for a harder benchmark v2 (scenario, multi-hop, temporal; measurable gates) | `docs/plans/BENCHMARK_V2_PROPOSAL.md` | ✅ (proposal; build in D3) | |
| 2.8 | Survey of public Vietnamese legal datasets (ViLegalExperts, Zalo, VLSP, VLegal-Bench) | `docs/reviews/public_vn_legal_benchmarks_2026-10-23.md` | ✅ | |

## 3. System implementation

| # | Item | Evidence | Status | Owner |
|---|---|---|---|---|
| 3.1 | Refactor the core into a config-driven pipeline (components on/off from YAML, builder, reference config) | `src/pipeline/`, `config/reference.yaml`, `docs/architecture.md` | ✅ | |
| 3.2 | Bounded agent loop split into action handlers; behaviour preserved (replay-identical) | `src/agent/loop.py` | ✅ | |
| 3.3 | Domain profiles (HCMUT, labour) keeping domain specifics out of shared code | `config/domains/` | ✅ | |
| 3.4 | Ingestion pipeline and multi-backend vector indexing | `src/ingestion/`, `src/indexing/` | ✅ | |
| 3.5 | Bonsai 2B controller on llama.cpp (Mac) and CUDA (server 82); constrained JSON decoding | `config/benchmark/model_prism_gguf2b.yaml`, `Makefile` | ✅ | |
| 3.6 | Reranker: AITeamVN Vietnamese reranker as GGUF (Mac) and torch fp16 (GPU), shared chunk policy, GGUF conversion fix | `src/retrieval/rerankers.py`, `scripts/reranker/`, `docs/plans/reranker.md` | ✅ | |
| 3.7 | Reranker parity measurement Mac vs GPU vs fp32 reference | `evaluation/runs/reranker-parity-2026-10-23/` | ✅ | |
| 3.8 | Thread-safe shared reranker for parallel benchmark workers | commit `f8a14b4` | ✅ | |
| 3.9 | L1 verifier fixes (line-broken units crash) and L1 v2 (fair quote matching, claim-local quantities, sentence support, actionable feedback) | `src/verifier/lexical_grounding*.py` | ✅ | |
| 3.10 | Revision r2 switches F1–F8, F11 (question-anchored first search, top_k 5, search hints, clarify/refuse prompt contract, search-first gate, verifier-report feedback, thought length cap, free duplicate notices, refusal source) | `src/agent/`, `config/domains/*_r2.yaml` | ✅ | |
| 3.11 | Bonsai 4B controller: download, pin, CUDA gate | `config/benchmark/model_prism_gguf4b*.yaml`, `expected_server.yaml` | ✅ | |
| 3.12 | Design study: span-referenced answers (claims + evidence span ids) | `docs/plans/SPAN_CITATION_DESIGN.md` | ✅ (design; build in D3) | |

## 4. Evaluation harness and metrics

| # | Item | Evidence | Status | Owner |
|---|---|---|---|---|
| 4.1 | Metrics review vs research/production practice; fixes (citation precision, latency over all trials, abstention-aware strict success) | `docs/reviews/metrics_review_2026-10-23.md`, `evaluation/judge_rules.py` | ✅ | |
| 4.2 | New metrics: retrieval R@k/MRR/nDCG, citation P/R/F1, behaviour confusion matrix, paired bootstrap CIs, closed-book strata | `evaluation/metrics.py`, `evaluation/stats.py` | ✅ | |
| 4.3 | One-command batch runner with preflight (model/sha/port checks), resume, judge, tables | `evaluation/run_d2.py`, `scripts/run_d2_benchmarks.sh`, `docs/RUNBOOK_D2.md` | ✅ | |
| 4.4 | Diagnostic baselines: closed-book and oracle | `evaluation/baselines.py` | ✅ | |
| 4.5 | Experiment tracking: harness version, manifest provenance, run registry with freshness/pinning, table provenance, report-check | `evaluation/provenance.py`, `registry.py`, `check_report_provenance.py`, `evaluation/runs/REGISTRY.md` | ✅ | |
| 4.6 | v3-vs-r2 comparison tables | `evaluation/compare_runs.py` | ✅ (tables pending r2 judge) | |
| 4.7 | Offline L1 replay against recorded answers and judge labels | `evaluation/probes/l1_replay.py`, `evaluation/runs/l1-replay-2026-10-24/` | ✅ | |
| 4.8 | Failure analysis of v3 (clarify overuse, query construction, repair behaviour, truncation) | `docs/reviews/v3_failure_analysis_2026-10-24.md` | ✅ | |
| 4.9 | Human-audit kit for the judge (blind packets, guide, kappa scorer) | `docs/HUMAN_AUDIT_GUIDE.md`, `evaluation/score_benchmark_audit.py` | ✅ | |
| 4.10 | Human audit labelling (30 items per benchmark) and κ | `evaluation/runs/d2-gpu-main-*-v3/analysis/human-audit/labels.csv` | ☐ (tonight) | |

## 5. Experiments

| # | Item | Evidence | Status | Owner |
|---|---|---|---|---|
| 5.1 | Server 82 setup (venv, CUDA llama.cpp build, models, gates) | `/home/dungvpt/workspace/dungvpt/` on server 82 | ✅ | |
| 5.2 | Main runs v3 (Bonsai 2B, 1,090 trials) + judge + independent recomputation | `evaluation/runs/d2-gpu-main-{hcmut,labour}-v3` | ✅ | |
| 5.3 | Revised runs r2 with Bonsai 2B and 4B (4 × 545 trials) | `evaluation/runs/d2-gpu-r2-{2b,4b}-{hcmut,labour}-v1` | ⏳ (judge finishing) | |
| 5.4 | Mac latency run (v3 system, 300 trials) | `evaluation/runs/d2-mac-latency-v3sys-v1` | ✅ | |
| 5.5 | Full test-suite run with live servers (425 passed) | `evaluation/runs/test-suite-2026-10-24/` | ✅ | |
| 5.6 | Smoke and gate runs (Mac 2-task check, GPU gates) | `evaluation/runs/bench-smoke-*`, `mac-check-*` | ✅ | |

## 6. Demo and frontend

| # | Item | Evidence | Status | Owner |
|---|---|---|---|---|
| 6.1 | Web UI update: corpus switch, agent timeline, cited source spans, outcome states | `frontend/`, `src/api/` | ✅ | |
| 6.2 | Demo configs identical to the benchmark L1+rerank system | `config/profiles/demo-*.yaml` | ✅ | |
| 6.3 | Demo script with live-verified queries | `docs/presentation/DEMO_SCRIPT.md` | ✅ | |
| 6.4 | Recorded GIFs and MP4 backup video | `docs/presentation/gifs/` | ✅ | |
| 6.5 | Demo rehearsal on the presenting laptop; re-record backup there | — | ☐ | |
| 6.6 | `make demo-preflight` (server check + warm-up) | — | ☐ (optional) | |

## 7. Report and presentation

| # | Item | Evidence | Status | Owner |
|---|---|---|---|---|
| 7.1 | Rewrite the D2 report for the current system (sections 1–8, threat model, metric definitions) | `report_d2/main_d2.tex` | ✅ | |
| 7.2 | New architecture figure (Figure 1) | `report_d2/images/architecture.tikz` | ✅ | |
| 7.3 | Editorial and AI-slop passes | report history | ✅ | |
| 7.4 | v3 result tables with provenance; latency, reranker parity and trace | `report_d2/tables_*_v3/`, `benchmark_latency_mac.tex` | ✅ | |
| 7.5 | r2 results section, AI-use statement, benchmark-review statement, final professional pass | `report_d2/main_d2.tex` | ⏳ (tonight) | |
| 7.6 | Reproduction guide for every reported result | `docs/REPRODUCE_D2.md` | ☐ (tonight) | |
| 7.7 | Member contribution evidence and "verified by the group" statements | report Section 8 | ☐ (group) | |
| 7.8 | Final freeze: commit hash, report-check, lecturer repository access | — | ☐ | |
| 7.9 | Slide outline | `docs/presentation/D2_SLIDES_OUTLINE.md` | ✅ | |
| 7.10 | Slide deck (from the outline, with final numbers) | — | ☐ | |
| 7.11 | Q&A preparation (limitations, who answers what) | — | ☐ | |

## 8. Engineering hygiene

| # | Item | Evidence | Status | Owner |
|---|---|---|---|---|
| 8.1 | Repository on GitHub kept in sync with server 82 | `origin/main` | ✅ | |
| 8.2 | Fixes found by running: GGUF reranker template, reranker lock, L1 newline crash, port ownership on the shared server, `--kv-unified` | commits `f8a14b4`, `957579b`, `227df08` | ✅ | |
| 8.3 | Integrity rules (no mocks, no fabricated numbers, red placeholders) applied throughout | `AGENTS.md` | ✅ | |
