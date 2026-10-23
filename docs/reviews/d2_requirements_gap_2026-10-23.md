2026-10-23 22:45 +07 (UTC+7), Friday. D2 requirements-gap review (read-only), Group 8, CO5151. Deadline Sun 25 Oct 2026 23:59 +07; presentation Wed 28 Oct 18:00.

# D2 requirements traceability and gap review

Reviewer: REQUIREMENTS-GAP agent. Scope: lecturer requirements vs. what the repository contains at the time of writing. Nothing outside this file was edited; no git operation, benchmark, model load or `.env` read. Statuses are strict: DONE needs a cited file/line/run; "valid but stale" content is PARTIAL. Ranking weights ("distance") are my own estimates for prioritisation, not predicted scores.

## 1. Sources read

| Source | What was read | Size |
|---|---|---|
| `docs/materials/d2/interim-report-requirements.pdf` (primary 1) | Full text via pypdf (diacritics partly garbled by font mapping; wording checked against the announcement, which repeats all points) | 3 pages: §1 submission, §2 eight report sections, §3 proposal gaps to fill, §4 checklist |
| `docs/materials/d2/CO5151-D2-Rubric.xlsx` (primary 2) | Every cell, formula and cell comment (openpyxl) | 8 sheets G1-G8; all identical except title cell B2; 8 criteria, weights 15/15/10/5/5/20/15/15 %, 5 bands (9-10, 7-8, 5-6, 3-4, 0-2), band descriptions B34:G38, note G40, per-criterion "high score when" comments on B12-B20 |
| `docs/materials/d2/CO5151-D2-announcement.md` (primary 3) | Full (mirrors the PDF; adds submission email, 15 min = ~10 + ~5, demo and backup-video rules, deadlines) | 6 sections |
| Report | `report_d2/main_d2.tex` (337 lines), `native_results.tex`, `semantic_results.tex`, `diagnostic_results.tex`, `refs.bib`, compiled `main_d2.pdf` (page count and text per page via pypdf; `sections/` is empty) | 11 PDF pages |
| Team notes (secondary, verified against primary) | `report_d2/D2_GAP_REVIEW.md` (21 Oct, stale), `D2_REVISION_STATUS.md` (22 Oct, stale: says PDF 9 pages), `SLIDE_DEMO_MODEL_NOTE.md` (stale), `docs/materials/d2/D2_REQUIREMENTS_REVIEW.md`, `docs/plans/D2_COMPLETION_PLAN.md`, `docs/RUNBOOK_D2.md`, `docs/plans/benchmarking.md`, `docs/plans/BENCHMARK_V2_PROPOSAL.md`, `docs/reviews/{benchmark_quality,metrics_review}_2026-10-23.md`, `evaluation/RESULTS_STATUS.md`, benchmark READMEs, `report_d1/chap1.tex` (D1 proposal) | |
| Code spot-checks | `src/tools/{domain_tools,permissions,mcp_server}.py`, `src/agent/state.py`, `src/security/guardrails.py`, `src/memory/`, `src/pipeline/`, `config/benchmark/*.yaml`, `Makefile`, `tests/test_real_system.py`, `frontend/src/App.tsx`, `.git/logs/HEAD` (read as a file) | |

Primary sources agree with each other on every point checked; I found no requirement in `report_d2/D2_REQUIREMENTS.md` that is absent from the primaries (it adds nothing mandatory about slide count, template or citation style).

Facts about the current state that drive everything below:
- `report_d2/main_d2.tex`/`main_d2.pdf` (both last modified 23 Oct 02:22/02:23) still report the OLD frozen run: Qwen2.5-3B on Ollama, 10-task `bll2019_v1`, 220-article corpus, OFF vs ON.
- Decided D2 design (D2_COMPLETION_PLAN §2): two frozen 50-task benchmarks (`hcmut_v1`, `labour_vi_v1`), controller Ternary Bonsai 2 2B GGUF, variants `off`/`l1`/`l1_rerank`, seeds 42/123/2026, accuracy on server 82, latency on the Mac.
- No main-run directory exists in `evaluation/runs/` (no `d2-*`); only smoke runs (`bench-smoke-*`, all `report_eligible: false`), sanity runs, the old `bll2019-*`, judge and diagnostic runs, and `reranker-parity-2026-10-23`.
- Nothing has been committed for D2 (HEAD `9ee48da` is a pre-cleanup baseline; the smoke manifest records `dirty: True`, 24 tracked changes, 19 untracked). All 40 `.git/logs/HEAD` entries are by one author (`tuandung222`).
- No D2 slides and no backup video exist anywhere in the repo (only `report_d1/LuatCheck_D1_Pitch.pptx|pdf`).

## 2. Traceability matrix

Status key: DONE / PARTIAL / MISSING / N/A. "H" = needs a human decision or action. Quotes are the lecturer's wording (Vietnamese, short). Line numbers refer to `report_d2/main_d2.tex`.

### 2.1 Form, submission and deadline (PDF §1, §4; announcement §3)

| ID | Requirement (weight where the rubric ties it) | Status | Evidence | What is missing |
|---|---|---|---|---|
| F1 | One report PDF, "tối đa 10 trang nội dung" (A5 5%) | DONE (draft) | `main_d2.pdf` = 11 pages: unnumbered cover + numbered pages 1-10; Section 8 and the references share numbered page 10; numbered page 9 is ~60 % empty (1.5k of ~4k chars) because of `\clearpage` at :319 | Zero real margin after the rewrite adds new tables. Re-count after every edit (numbered page of last section body, not of the references). Do not shrink fonts further: tables are already `\footnotesize`, section spacing negative (:44-52) |
| F2 | Cover/TOC/references/appendix excluded; text after page 10 not graded | DONE | Title page :123-144; no TOC; references only after Section 8; no appendix | Anything beyond numbered page 10 is lost: Section 8 is currently the last content and sits exactly on page 10 |
| F3 | Language Vietnamese or English | DONE | English text | none |
| F4 | "tám phần ... theo đúng thứ tự" (A5) | DONE | Eight `\section` at :147, 171, 206, 223, 232, 285, 302, 320, in the required order; `tests/test_real_system.py:160` asserts the count (8) | Test checks only the count, not titles/order; fine |
| F5 | Repository URL in the report | DONE | :139 `github.com/tuandung222/LuatCheck-D2`, equal to `origin` in `.git/config` | none |
| F6 | Commit hash "của phiên bản được báo cáo" (A5) | MISSING | :140 and :284 are red `\pending`; no D2 commit exists; runs record `commit 9ee48da`, dirty | A real commit/tag of the final code (user must approve), pushed; hash in :140. Note the hash cannot contain the report PDF's own commit (cite the code commit and say so) |
| F7 | Lecturer must be able to read the repo | MISSING (H) | :141 red `\pending`; visibility of the GitHub repo unknown | Make repo public or add lexuanbach (or the lecturer's GitHub account) as reader; test from a clean clone/anonymous browser |
| F8 | Slide PDF "cho bài trình bày 15 phút" (B2 15%) | MISSING | No D2 deck in repo; `report_d2/SLIDE_DEMO_MODEL_NOTE.md` is a text note and is outdated | Entire deck, exported to PDF |
| F9 | Email from group leader to lexuanbach@hcmut.edu.vn, CC all members, two PDFs, subject `[CO5151][G8] D2 Interim report`, before 23:59 Sun 25 Oct; late = -10 %/day, max 3 days | MISSING (H) | Nothing in repo (cannot be) | Leader action on Sun 25 Oct; subject must use the group number (Gx = G8; cover says Group 8) |
| F10 | Template / citation style / font | N/A | Neither PDF nor announcement mandates any | Keep `\footnotesize` tables readable; 5 works cited (:169-248) |
| F11 | Checklist (PDF §4): "video dự phòng đã quay", "demo đã chạy thử" | MISSING | see B1 | see B1 |

### 2.2 The eight mandatory report sections (PDF §2)

| ID | Requirement | Weight | Status | Evidence | What is missing |
|---|---|---|---|---|---|
| S1.1 | "Phạm vi, kiến trúc hoặc kế hoạch đánh giá đã đổi gì kể từ D1, và vì sao" | A4 5% | PARTIAL | §1 :147-169 explains Qwen3-4B/8B to Qwen2.5-3B, Qdrant dropped, mock removal, `send_summary` made reversible | Not updated for the current design: benchmark move 10 tasks to 2x50 over two corpora (one non-legal: HCMUT academic regulations), controller Bonsai 2B, reranker, variants `off/l1/l1_rerank`, GPU server 82 + Mac. Text still says scope = "frozen original-2019 labour-law corpus" (:148), contradicted by the planned main run |
| S1.2 | Handling of pitch feedback | A4 | PARTIAL (H) | :166 "no pitch feedback has yet been received" (team answer of 22 Oct recorded in `report_d2/D2_REVISION_STATUS.md`) | Team to confirm that no feedback at all was received after the D1 pitch (lecturer/peer Q&A, grading comments); if any exists, list it and the response. Otherwise the sentence stands |
| S1.3 | Table: proposal commitments due "trước mốc giữa kỳ" vs. status (xong / đang làm / chưa bắt đầu / đã bỏ) | A4 | PARTIAL | Table 1 :152-165, 8 rows, correct 4-state vocabulary | Rows stale (models, "$\geq$10 tasks Done: 60 trials on ten tasks", corpus); D1 W7 commitments not listed: retrieval metrics on 200 held-out pairs, offline full run, 32B comparator, 3 configs, verifier audit of 30 pairs (`report_d1/chap1.tex` evaluation plan); reranker (optional in D1) now exists |
| S2.1 | Updated architecture diagram, marking "đang chạy từ đầu đến cuối" vs. planned (R1) | A1 15% | PARTIAL | Fig. 1 :174-200 (TikZ), caption :199 marks solid = run, dashed = outside experiment; `docs/architecture.md` has the data-flow and module map | Diagram shows "Qwen2.5-3B (results) / Bonsai 2B (demo)" and no reranker step; must show reranker (optional after first stage), which parts ran in the new main run (off/l1/l1_rerank), NLI/L2 and vector index as implemented-but-not-in-D2 |
| S2.2 | Description of the control loop | A1 | DONE | :172-201 (ReAct-style, budgets 8 steps / 5 tools / 2 repairs / 180 s, terminal actions, error vs refusal); matches `src/agent/state.py` ActionType and `docs/architecture.md` | Re-read after rewrite so budgets quoted equal `config/benchmark/model_prism_gguf2b.yaml` (max_output_tokens there is 1024, report says 768) |
| S2.3 | Single vs. multi-agent stated honestly | A1 | DONE | :172 "uses one agent ... No multi-agent coordination is claimed"; MCP server noted as not used by the loop | none |
| S2.4 | "Kèm một trace thật" of a completed task | A1, B1 | PARTIAL | :203-204: `BLL19-01-PROBATION`, seed 42, ON, from `evaluation/runs/bll2019-main-v2/runs.jsonl` | Trace is prose, from the superseded Qwen/old-benchmark run. Need a readable step table (action, tool, observation ids, verifier verdict, tokens, seconds) from the new main run (or the Bonsai demo model); depends on main run |
| S2.5 | (Announcement §3) which pattern and why, shown "bằng hệ thống và số liệu của chính nhóm" | A1, B3 | PARTIAL | :173 one sentence, cites ReAct; benefit "remains an empirical question" | Link the choice to measured off vs l1 vs l1_rerank deltas once the main run exists |
| S3.1 | Table of each tool: implemented or planned, permission level (read-only / reversible write / irreversible write / code execution) (R2) | A1 | PARTIAL | Table 2 :207-219: `search_law`, `get_article`, agent memory write, MCP `save_case` (blocked), `send_summary` (proposal), trusted-UI outbox, external sender and code exec (not implemented). `src/tools/permissions.py` TOOL_PERMISSIONS | Add the reranker (read-only model component, failure = execution error), the generic tool names of the HCMUT profile (`search`, `read_document`, `config/domains/hcmut_academic.yaml`), and state that MCP is not used by the loop (already in :172) |
| S3.2 | Blocking mechanism for every non-read-only tool | A1 | DONE | :213-215, :218-221. Code: `src/tools/domain_tools.py` `dispatch_external_action` (:299-) requires proposal approved by the trusted host, payload-hash match and HMAC-compared token; model action space has no write tool (`ActionType`: search, read, answer, clarify, refuse); `src/tools/mcp_server.py` `save_case` returns blocked; tests `tests/test_real_system.py:90` (outbox needs host approval) and `:122` (real MCP stdio) | none for the claim itself; sentence at :221 still has a red "attach demo evidence" placeholder |
| S3.3 | If read-only only: code-level guarantee | A1 | N/A | System has non-read tools; handled in S3.2 | none |
| S4.1 | Short-term context management | A1 | PARTIAL | :224 describes the ledger as state; context policy (observation compaction, 8192 ctx per slot, tool-output truncation notices) appears only inside "Reproduction" (:284) and :263 | One short paragraph on how the prompt is built and bounded for Bonsai (ctx tokens per slot, compacted observations, budget notices) |
| S4.2 | Long-term/episodic memory: write policy and retrieval policy | A1 | DONE | :226; `src/memory/answer_memory.py`, `sqlite_store.py`; write only after verification gate, reuse needs index-version match, similarity 0.85, re-verification; "D2 experiments disable memory" matches `config/benchmark/model_prism_gguf2b.yaml` (`memory.enabled: false`) and `config/config.yaml` (reuse off) | State plainly that memory exists but is not exercised by any D2 number or by the demo reuse path |
| S4.3 | Retrieval: data loaded, scale, chunking, indexing, "Ghi rõ phần nào đã chạy" | A1 | PARTIAL | :228-230 describes 220-article BLL 2019 corpus, BM25 + TF-IDF/RRF k=60. New data: `data/corpus/labour_vi_v1.json` 458 records / 10 documents, `data/corpus/hcmut_academic_v1.json` 143 records / 10 documents, provenance in `docs/materials/{labour,hcmut}-sources/`, ingestion code `src/ingestion/`, benchmark READMEs list limits | Rewrite for the two corpora and their caveats (image-only base regulations absent, ND 145/2020 excluded, unnumbered annexes); say that the persisted index (`src/indexing`, `hybrid_index`) and dense retrieval are NOT used in D2 runs (`dense_model_type: tfidf`) |
| S5.1 | Task set: provenance, current and target counts | A2 15% | PARTIAL | Old: :234-236. New facts exist: `evaluation/benchmarks/{hcmut_v1,labour_vi_v1}/{README.md,ADJUDICATION.md,benchmark.lock.json}`: 50 tasks each (40 single / 5 multi / 5 out_of_scope), frozen | Report text not rewritten; end-of-term target count for the new sets not stated; D1 target "20 tasks + 200 retrieval pairs" must be reconciled (now 100 tasks; retrieval-pair test not done) |
| S5.2 | "Với tập tự xây dựng: ai viết task và đáp án chuẩn" | A2 | PARTIAL | READMEs: drafted by Claude Haiku, verified by two Claude Sonnet verifiers, adjudicated by Sonnet, mechanical checks, Gemma-4-31B oracle check; `docs/reviews/benchmark_quality_2026-10-23.md` (no wrong gold in 90 answerable items, LLM-assisted audit) | State in the report that no human wrote or reviewed tasks (AI-only; also required by AGENTS.md); no group member spot-check exists yet (H). Disclose the QA findings: BM25 puts gold at rank 1 for 89 % / 78 %, ~1/3 of answerable items solvable closed-book |
| S5.3 | Scoring method (automatic / human / LLM judge) | A2 | PARTIAL | `evaluation/judge_prompt.txt`, `judge_rules.py`, strict success definition in `docs/reviews/metrics_review_2026-10-23.md` §1 and `docs/plans/benchmarking.md` §4; old report :243-248 | Report must define the new metrics (strict success lower bound over planned trials, paired bootstrap, strata, lexical proxies labelled) in a few lines |
| S5.4 | LLM judge: reliability on a human-labelled sample | A2, B3 | MISSING (H) | Scorer exists: `evaluation/score_benchmark_audit.py`, `make audit-score` (Makefile:160); audit sample is exported by `judge_benchmark.py analyze` (~30 per benchmark). Old 12-item CSV is blank. No labels for any run | Needs a judged main run, then human labels (planned Sat 24 Oct evening), then agreement/kappa. Without labels the red placeholders stay and A2 cannot reach "Rất tốt" |
| S5.5 | Results on "ít nhất 5-10 task đã thực sự chạy" with the project's main metrics | A2 | PARTIAL | Old: `evaluation/runs/bll2019-main-v2` (10 tasks x 3 seeds x 2 modes = 60 real native trials, 12 errors kept) plus DeepSeek judgments; new design: only smoke `bench-smoke-evalimpl-20261023` (12 trials, 0 errors, not eligible). `evaluation/run_d2.py` + RUNBOOK ready | The 900-trial matrix per machine has not been run. Old results must not appear as current tables (AGENTS.md); at most a labelled historical paragraph |
| S5.6 | Comparison with at least one simpler configuration | A2 | PARTIAL | Old OFF vs L1 ON in `native_results.tex`; new `config/benchmark/variants.yaml` (off, l1, l1_rerank + paired comparisons) | New numbers pending. Note the PDF itself accepts "bỏ một thành phần" as a simpler config, so `off` qualifies |
| S5.7 | Cost per task and latency; API users in tokens and money; local users in GPU hours and machine config | A2 | PARTIAL | Old: tokens, p50/p95, "model service-hours", red "GPU-active hours not measured". New tooling: per-trial latency (Mac only), tokens, peak RSS, hardware block in the manifest, judge cost from gateway usage (`RUN_NOTES.md` format); no API for the controller (local) | No main-run numbers yet. "Giờ GPU": runner records wall time and hardware, not GPU-active hours (`evaluation/run_benchmark.py:537`); report device wall-hours and GPU model (H100 on 82, Apple M4) explicitly as such. Mac `l1_rerank` uses a different reranker runtime (GGUF Q8_0) than the GPU run (torch fp16): do not pool (RUNBOOK C4) |
| S5.8 | Interpretation of failed tasks and predicted causes | A2 | PARTIAL | Old: error table :265-281 (12 `model_output_error`, byte-identical request analysis); new tooling: error profile with Wilson CI, kinds, per-task consistency | Needs the new run; failure analysis on Bonsai 2B items |
| S5.9 | Numbers reproducible from the repository ("bằng một lệnh" in the A2 comment) | A2 | PARTIAL | One command: `make benchmark-d2` (`evaluation/run_d2.py all`); `make tables RUN=...`; locks in `evaluation/benchmarks/*/benchmark.lock.json`; `docs/RUNBOOK_D2.md` | Not yet run for the main collection; code not committed (a clean clone cannot reproduce the hash-locked sources); the report's Reproduction paragraph (:284) cites old commands (`evaluation.run_eval`, `render_native_table`); GPU run needs server 82 and pinned weights, so state the Mac-only reproduction path too |
| S5.10 | "Số liệu không có cách chấm rõ ràng ... không được tính" | A2 | DONE (rules) | LLM-judge numbers labelled "uncalibrated LLM estimates" (semantic_results.tex caption), lexical proxies labelled; `evaluation/RESULTS_STATUS.md` quarantines historical files | Keep the labelling when new tables are published |
| S6.1 | Threat model: (a) assets to protect | A3 10% | PARTIAL | Table 3 :287-299 first column "Entry / asset" mixes both; D1 had a list of assets (answer correctness, user data, audit trail, egress) | Add an explicit asset list (3-5 items) |
| S6.2 | (b) points where untrusted content enters model context | A3 | PARTIAL | Table 3 rows: question, pasted document, retrieval/tool text, memory, audit, outbox, resources | New entry points not covered: documents ingested from the web into corpora (`src/ingestion`), reranker/NLI model weights, external judge gateway receiving questions/answers/sources (egress, offline eval only), domain/config files; say explicitly "web pages: N/A, no browsing tool" |
| S6.3 | (c) what the attacker is assumed to do | A3 | DONE | :286 | Add: attacker cannot alter corpus/config/weights |
| S6.4 | Planned mitigation per entry point | A3 | DONE | Table 3 column 3; each row names mitigation and remaining risk; code anchors `src/security/guardrails.py`, `config/domains/*.yaml` patterns | none beyond new entry points |
| S6.5 | Injection tests not required in D2 | A3 | DONE | :300; `redteam/README.md` marks old results historical; `evaluation/RESULTS_STATUS.md` | none |
| S7.1 | Weekly plan from week 45 to Round 1 (week 49, 2 Dec) | A4 | PARTIAL | Table 4 :303-315 has W45-W49 plus 24/25 Oct rows | Stale content (e.g. "expand approved tasks", ten-task framing); owner column is "Proposed", red at :314 |
| S7.2 | Who is responsible for what | A4 | PARTIAL (H) | Owners named in Table 4 (Quyền / Phong / Dũng pairs) | Team must confirm; do not present as agreed until they do |
| S7.3 | Riskiest remaining assumption | A4 | DONE | :316 "native 3B controller answers correctly within budget" | Update model name (Bonsai 2B) and add "benchmarks too easy/saturated retrieval" if used |
| S7.4 | Narrowed scope if assumption fails + core kept | A4 | PARTIAL | :316 | Outdated (keeps "ten approved tasks", cuts reranking). Reranker is now part of D2 core; restate |
| S7.5 | Self-assessment: on track / at risk / narrow scope | A4 | DONE | :317 "Self-assessment: at risk", cover :142 | Re-evaluate after main run; cover :142 says "native collection is complete", which is outdated |
| S8.1 | Table: what each member did, "khớp với lịch sử commit" (A5) | A5 | MISSING (H) | Table 5 :321-329 has all three members with red "Evidence pending"; `.git/logs/HEAD`: 40 of 40 entries by `tuandung222`, so history cannot show three contributors | Real per-member evidence (commits under their own identity, PRs, review notes, annotated artifacts) or an honest statement of how work was done; nobody should be credited without evidence |
| S8.2 | AI tools used and for what | A5 | PARTIAL | :330-332 lists Claude, Copilot (D1 draft), OpenAI Codex, DeepSeek Flash judge | Incomplete (red :331): add Claude Code orchestration with Sonnet/Haiku sub-agents (benchmark writing, verification, adjudication, QA), Gemma-4-31B (oracle/closed-book checks), DeepSeek V4 Pro and Gemini 3 Flash (benchmark second opinion), GPT-5.5 (old diagnostic), Qwen/Bonsai (controllers); who ran what |
| S8.3 | What the group itself verified | A5, B3 | MISSING (H) | :333 red placeholder; all benchmark checking is AI-only; no human labels exist | Only claim what humans actually did (e.g. Sat 24 Oct audit labelling, spot-checks of N tasks against PDFs, code review). Stale test statement at :332 ("11 tests in 26.09 s"): the plan records 192 passed / 1 skipped; fix with the actual latest count |

### 2.3 Items D2 must add if the proposal lacked them (PDF §3)

| ID | Requirement | Status | Evidence | Missing |
|---|---|---|---|---|
| P1 | Track stated | DONE | Cover :131 "Application Track" | none |
| P2 | Research items (RT1 falsifiable hypothesis, RT2 external baseline) | N/A | Application Track | none |
| P3 | AT1: user groups and at least three scenarios, one careless/malicious | DONE | :148 users, :150 three scenarios, third is malicious/careless | Scenarios are untested (stated); no student/HCMUT scenario even though `hcmut_v1` is a second domain |
| P4 | Dev model vs. model for report numbers; API vs local; framework; self-written parts | PARTIAL | :169 is detailed and honest, but states Qwen2.5-3B as the source of all numbers and Bonsai as demo-only | Rewrite: controller = Bonsai 2B GGUF on PrismML llama.cpp commit 73bfe6c for numbers and demo; judge DeepSeek Flash (gateway, API); reranker AITeamVN/Vietnamese_Reranker at pinned revision; no agent framework (keep) |
| P5 | Tool/permission table if missing | DONE | see S3 | see S3 |
| P6 | Memory design if missing | DONE | see S4.2 | see S4 |
| P7 | Task scale, metrics, baseline and number of runs | PARTIAL | Matrix in `config/benchmark/d2_matrix.yaml` (2 x 3 x 3 x 50 = 900 trials per machine) | Not in report |
| P8 | Threat model, weekly plan, narrowed scope | PARTIAL | see S6, S7 | see S6, S7 |
| P9 | Simulated/synthetic data disclosure and difference from real data | PARTIAL | Old text :236 ("local curated tasks ... AI reviewer") | New benchmarks are AI-written questions over real public documents, no real user questions; real usage differs (long, vague, pasted contracts). Say so |
| P10 | Promised real-user session: done or not, what was learned | DONE (status) | :159 "Not started", reported by the team on 22 Oct; D1 promised an HR walkthrough in W5 (`report_d1/chap1.tex` AT1) | Red placeholder for new date/owner; nothing was learned yet and the report says so |

### 2.4 Presentation, live demo and Q&A (announcement §5; rubric B1-B3)

| ID | Requirement | Weight | Status | Evidence | What is missing |
|---|---|---|---|---|---|
| B1.1 | Live demo of at least one task end to end on project data, in class | B1 20% | PARTIAL | UIs exist: Streamlit (`make demo`, `src/ui/app.py`) and FastAPI + React (`make web`, `frontend/src/App.tsx`, activity timeline and budgets); Bonsai server `make prism-server` (answering on 127.0.0.1:8081 at review time); Web UI smoke run in `docs/reviews/web-ui-smoke-2026-10-22/` ended in a backend error and its README says the successful native-answer gate remained open; later repair log shows two native answers with Qwen (`docs/reviews/web-ui-repair-2026-10-22/REPAIR.md`) | No recorded successful end-to-end demo with Bonsai 2B on `hcmut_v1`/`labour_vi_v1` data; no demo script/pre-chosen tasks (completion plan §G); demo and report must show the same model/behaviour |
| B1.2 | Backup video ready, group can explain the trace; video-only without incident cannot reach "Rất tốt" | B1 | MISSING | No .mp4/.mov/.webm in the repo | Record a screen capture of the exact demo flow with visible trace; keep the live run as primary |
| B2.1 | ~10 minutes ("Đúng 10 phút" in rubric B19) covering changes, running architecture, first numbers and cost, threat model, plan and risks, honest completion level | B2 15% | MISSING | No deck; `SLIDE_DEMO_MODEL_NOTE.md` outdated (says numbers = Qwen2.5-3B) | Deck + timed rehearsal (H) |
| B3.1 | Q&A: accurate, evidence-based answers; each member answers on their part; admit real limits | B3 15% | MISSING (H) | No Q&A preparation in repo; honest-limitations material exists (benchmark QA review, metrics review) | Q&A rehearsal per member; ownership map (who explains retrieval/rerank, agent loop/verifier/eval, tools/security/UI). Depends on S8.1 evidence |
| B4 | All members present from the start, projection checked (announcement §5) | n/a | N/A (H) | | Logistics |

### 2.5 Rubric criteria (sheet G8; weights verbatim from C12:C20)

| Criterion | Weight | Rubric "high score when" (condensed) | Overall status | Main blocking items |
|---|---|---|---|---|
| A1 Kiến trúc, công cụ, bộ nhớ và nguồn tri thức | 15 % | honest run/plan split; diagram matches code; real trace; tool table with permissions and blocking; memory/retrieval policy; N/A explained | PARTIAL (content strong, stale) | S2.1, S2.4, S3.1, S4.1, S4.3 |
| A2 Bộ đánh giá và số liệu đầu tiên | 15 % | $\geq$5-10 tasks run; correct/incorrect defined; simpler-config comparison; cost and latency; failures interpreted; reproducible with one command | PARTIAL (tooling ready; main numbers and human calibration absent) | S5.4, S5.5-5.9 |
| A3 Threat model | 10 % | assets, entry points, attacker capability specific to this system; mitigation per entry point | PARTIAL (mostly present, needs new entry points and assets list) | S6.1, S6.2 |
| A4 Thay đổi, kế hoạch và rủi ro | 5 % | full commitment table; scope changes with reasons; pitch feedback; missing proposal items added; feasible weekly plan; narrowed scope | PARTIAL | S1.1-S1.3, S7.x, P7, P9 |
| A5 Chất lượng báo cáo | 5 % | $\leq$10 pages, eight sections, claims match evidence, repo + commit hash, contribution table and AI-use statement | PARTIAL | F6, F7, S8.1-S8.3 |
| B1 Live demo | 20 % | end-to-end in class on project data; matches report; backup video + trace explanation | PARTIAL / MISSING video | B1.1, B1.2 |
| B2 Trình bày | 15 % | exactly 10 min; all seven content points; honest completion | MISSING | F8, B2.1 |
| B3 Hỏi đáp | 15 % | accurate, evidence-based, every member answers, limits admitted | MISSING (H) | B3.1, S8.1 |

Counts over the 63 requirement rows in 2.1-2.4 (the eight rubric rows in 2.5 are rollups and not counted):

| Block | Rows | DONE | PARTIAL | MISSING | N/A |
|---|---|---|---|---|---|
| 2.1 Form and submission | 11 | 5 | 0 | 5 | 1 |
| 2.2 Eight report sections | 37 | 10 | 23 | 3 | 1 |
| 2.3 Proposal gaps (PDF §3) | 10 | 5 | 4 | 0 | 1 |
| 2.4 Presentation, demo, Q&A | 5 | 0 | 1 | 3 | 1 |
| Total | 63 | 20 | 28 | 11 | 4 |

Most PARTIAL rows are "content exists and was honest for the old Qwen/10-task run, but must be rewritten for the decided Bonsai / 2x50-task design"; they close by writing plus the main-run numbers, not by new engineering.

## 3. Ranked gaps (rubric weight x distance from "Rất tốt")

Distance is my estimate of how far the item currently is from the top band (0 = there, 1 = nothing). Priority = weight % x distance.

| Rank | Gap | Criterion (priority) | Smallest action to close | Depends on | Effort |
|---|---|---|---|---|---|
| 1 | No rehearsed live demo on the decided system (Bonsai 2B, project data) and no backup video | B1 20 % x 0.7 = 14 | Choose 3 tasks (one `hcmut_v1`, one `labour_vi_v1`, one refusal) that work in smoke/main trials; write a 6-step demo script; confirm `make prism-server` + `make web` (or `make demo`) cold-start on the presenting laptop; record a screen video with visible trace; two timed rehearsals | Bonsai server and UI (exist); best after the main run provides known-good tasks, but video can be recorded from smoke tasks tonight/Sat | 3-4 h plus rehearsals; humans must present |
| 2 | No slide PDF; presentation not timed | B2 15 % x 0.9 = 13.5 | 10-min deck with the seven mandated topics (changes, running architecture, demo, first numbers and cost, threat model, plan, risks); update/replace `SLIDE_DEMO_MODEL_NOTE.md`; export PDF; time it | Report numbers (Sat/Sun) | 3-4 h |
| 3 | No main-run numbers on the new benchmarks (accuracy, latency, cost, errors) | A2 15 % x 0.75 = 11.3 | Execute RUNBOOK_D2: PQ2_0 CUDA gate on server 82, 900-trial accuracy run, Mac latency run (1 seed), judge, `make tables`; keep failed runs | Server 82 CUDA build of PrismML llama.cpp 73bfe6c; gateway key; Mac idle for latency | Machine time ~3-8 h total (judge ~1-2 h, ~$2-3); agent attention ~2 h |
| 4 | Judge reliability not measured against humans | A2 + B3 (part of 11.3 and 9) | Group labels the exported audit sample (about 30 per benchmark) blind to the verdicts on Sat 24 Oct evening; run `make audit-score`; paste agreement/kappa into the table caption. If time is short, label a smaller sample and say so | Judged main run (rank 3) and 3 members' time (about 60 items; plan for 1-2 h each) | 1-2 h per member + 30 min scoring |
| 5 | Report text describes the superseded system (model, benchmark, corpus, architecture figure, trace, plan, tests count) | A1 15 % x 0.4 + A4 + A5 (6.0 + 2.5 + 2.8) | Rewrite sections 1, 2, 4, 5, 7 against `docs/plans/D2_COMPLETION_PLAN.md` §3F; replace Fig. 1; drop or shrink old Section 5 results to one labelled "historical, superseded" paragraph to free ~2 pages for the new tables; fix the numbers listed in section 4 of this file | Rank 3 tables for final numbers; text can be drafted now with placeholders | 6-8 h writing; page-budget check after each pass |
| 6 | Commit hash and lecturer access | A5 5 % x 0.7 (+ prerequisite for S5.9 reproducibility) | After the supervisor freezes the code and the user approves: commit/tag, push, put the hash on the cover, verify the repo from a clean clone or anonymous browser, add lecturer as reader | All agents stop editing `src/`, `config/`, `evaluation/`; user's explicit approval to commit (AGENTS plan §H) | 30 min |
| 7 | Contribution table cannot match commit history; AI-use list incomplete; no member verification statement | A5 + B3 (3.5 + 2) | Each member supplies what they did and what they verified; map to commits, PRs, files, reviews; if git history shows only one account, say how work was shared and attach other evidence; rewrite AI-use with the full tool list | Team (human only) | 1 h writing after input |
| 8 | Trace in the report is from the old run | A1 (part of 6) | Select one finished trial from the new main run (or a Bonsai demo run), render the step table from `trials.jsonl` | Rank 3 | 30-45 min |
| 9 | Threat model lacks explicit asset list and new entry points | A3 10 % x 0.3 = 3 | Add 3-5 assets; add rows for ingested documents, reranker/NLI weights, judge gateway egress, config/profile files; mark web pages N/A | Writing only | 1 h |
| 10 | Q&A readiness | B3 15 % x 0.6 (part of 9) | Ownership map per member and a one-page list of honest limitations (AI-only benchmark, saturated retrieval, judge uncalibrated, Bonsai accuracy) | Report and deck final; humans | 1-2 h |
| 11 | Commitment table and scope-change reasoning out of date | A4 5 % x 0.5 | Update Table 1: add rows for retrieval-pair test, 32B comparator, offline run, verifier audit, reranker, benchmark/domain extension; explain why 2 benchmarks and why HCMUT | Writing; team to confirm "no pitch feedback" | 1 h |
| 12 | Data/users disclosure and benchmark caveats | A2/A4 (P9) | Add 4-5 sentences: AI-written tasks over real documents, no real users yet, QA findings B1-B4 from `docs/reviews/benchmark_quality_2026-10-23.md` | Writing only | 30 min |
| 13 | Weekly plan owners and walkthrough date unconfirmed | A4 | Team confirms W45-W49 owners and the HR walkthrough date; remove "Proposed" wording and the red tag only if confirmed | Team (human) | 15 min |
| 14 | Stale repo docs the lecturer may read: `README.md` status (22 Oct, says main = `bll2019-main-v2`), `evaluation/RESULTS_STATUS.md` (no entry for new benchmarks/smoke/sanity runs), `report_d2/SLIDE_DEMO_MODEL_NOTE.md`, `report_d2/D2_REVISION_STATUS.md` (says 9 pages) | A5/B3 consistency | Update after the report is final; list each run and its eligibility | After report | 45 min |
| 15 | Submission email | F9 | Leader sends with both PDFs, CC all, subject `[CO5151][G8] D2 Interim report`, before 23:59 Sun | Everything | 10 min |

Open decision (not a requirement gap): `docs/plans/BENCHMARK_V2_PROPOSAL.md` (harder benchmarks) is "proposal only, not started" and would move collection to Sat 24 Oct morning with a hard stop at 10:00. The v1 benchmarks are valid ground truth but weak instruments (QA review: BM25 rank-1 gold for 89 % / 78 %, about one third closed-book solvable, retrieval metrics saturated), so the off / l1 / l1_rerank comparison may show no difference. The lecturer's rubric rewards evidence quality and honesty, not discriminating power; v1 with explicit caveats satisfies A2. Switching to v2 competes for the same Saturday window as the human audit.

## 4. Conflicts and outdated claims in the current report (`report_d2/main_d2.tex`, `main_d2.pdf` of 23 Oct 02:23)

| # | Location | Claim | Why it conflicts with requirements or current state |
|---|---|---|---|
| C1 | :148, :228 | Scope = "frozen original-2019 Vietnamese labour-law corpus", 220 articles | Planned main run covers two corpora: `labour_vi_v1` (458 records, 10 documents including decrees, circulars, law 2025) and `hcmut_academic_v1` (143 records, 10 HCMUT documents, not law); AGENTS.md requires claims limited to evaluated domains |
| C2 | :156, :169, :182, :199, :316 | Qwen2.5-3B (Ollama) is the model of "every main-result number"; Bonsai 2B is "demo only" | Decision: Bonsai 2B GGUF for numbers and demo (`D2_COMPLETION_PLAN.md` §2). The "demo differs from reported numbers" box would be false and also invites B1/B3 questions |
| C3 | :158, :232-236, Table 1 | Ten `bll2019_v1` tasks as the evaluation set and "$\geq$10 tasks Done" | Superseded by two frozen 50-task benchmarks; old benchmark remains historical |
| C4 | `native_results.tex`, `semantic_results.tex`, :250-252 | Current tables of the old Qwen run (OFF 10/30, ON 11/30 etc.) | AGENTS.md: unverified historical results stay out of current tables. These numbers are real native runs but a different system and benchmark; relabel as historical or drop |
| C5 | :255-258, `diagnostic_results.tex` | GPT-5.5, Bonsai 4B/2B diagnostics on the old tasks (about one page) | Not on the new benchmarks; costs page budget; keep only if space remains and label as pre-main diagnostics |
| C6 | :239 | Two configurations OFF/ON | New design has three variants including `l1_rerank` (AITeamVN reranker top-20 to top-5) |
| C7 | :241 | Apple M4 / Ollama 0.34.4 as the only environment | Planned: GPU accuracy run on server 82 (H100, CUDA llama.cpp 73bfe6c, torch fp16 reranker) plus Mac latency run (Metal, GGUF Q8_0 reranker); the report must say which machine produced which number and that `l1_rerank` differs across machines |
| C8 | :248, :306 | Human audit = "12-output stratified sample" | Current exporter targets about 30 items per benchmark (`judge_benchmark.py analyze --audit-size 30`); sample size claim must match what the team actually labels |
| C9 | :284 | Reproduction via `python -m evaluation.run_eval --execute`, `render_native_table` | New one-command path is `make benchmark-d2` / `evaluation/run_d2.py all`, tables via `make tables` |
| C10 | :142 | "native collection is complete" | Only for the old run; new main collection not started |
| C11 | :332 | "all 11 tests in 26.09 seconds" | Outdated (plan records 192 passed, 1 skipped; more tests were added since); `D2_REVISION_STATUS.md` says 43.31 s for the same suite, so the two team notes also disagree |
| C12 | :216, Table 2 | No reranker row | A reranker is a new read-only model component (`src/retrieval/rerankers.py`, `l1_rerank`) |
| C13 | :330-333 | AI-use list = Claude, Copilot, Codex, DeepSeek | Incomplete versus the work actually done (see S8.2) |
| C14 | :201 | 768-token output cap | `config/benchmark/model_prism_gguf2b.yaml` sets `max_output_tokens: 1024` for the new runs |
| C15 | :316 | Cut "task expansion, optional NLI/reranking" | Reranker is part of the D2 design now |
| C16 | `README.md` "Current status (22 October)", `evaluation/RESULTS_STATUS.md`, `report_d2/SLIDE_DEMO_MODEL_NOTE.md`, `report_d2/D2_REVISION_STATUS.md` | Treat `bll2019-main-v2` and Qwen2.5-3B as the current result; revision status says PDF is 9 pages | Contradict the decided design and the actual 11-page PDF; the lecturer reads the repository (rubric A5) |
| C17 | Title/cover `LuatCheck: A Local Vietnamese Legal Assistant` | Legal only | One of the two benchmarks is academic regulations; either retitle ("Local Vietnamese Regulation Assistant"?) or state clearly that HCMUT is a second evaluated domain. Team decision (H); AGENTS.md says keep claims within evaluated domains |

Compliant and worth keeping: the honest handling of errors as execution errors, no mocks, AI-only review disclosure, "no pitch feedback / no HR walkthrough" disclosure, red placeholders for missing evidence, and the explicit exclusion of historical 100 % red-team claims.

## 5. Items only the team (humans) can provide

1. Human audit labels (Sat 24 Oct evening): about 30 items per benchmark, labelled blind to the judge verdict, reviewer name on every row (export under the judged run's `analysis/human-audit/`, which exists only after the main run is judged).
2. Per-member contribution evidence and what each member verified (no invention; current git history shows one author).
3. Confirmation that no pitch feedback was received at D1, and the new date/owner of the HR walkthrough (or an explicit "not done").
4. Confirmation of W45-W49 owners.
5. Complete AI-tool list with actual uses per member.
6. Decision on the title/scope wording (legal vs regulation assistant; HCMUT as second domain).
7. Approval to commit/tag and push; GitHub access for the lecturer; verification that a clean clone works.
8. Slides, live-demo rehearsal (10 + 5 minutes), backup video, Q&A ownership; the leader's email on Sun 25 Oct before 23:59.
9. Decision on v1 vs v2 benchmarks if anyone still considers v2 (hard stop Sat 10:00 in the proposal).
10. Optional but valuable for A2: a member spot-check of a few gold answers against the source PDFs, so the benchmark is not AI-only.

## 6. Interpretation notes

- "Tối đa 10 trang nội dung": I count the cover as excluded and number pages after it; if the lecturer counts raw PDF pages, the current draft has 11 total with references on the last, still defensible. Keep Section 8 on or before the tenth page after the cover.
- "Ít nhất 5-10 task": ambiguous (range vs. threshold). 100 tasks x variants x seeds passes either reading.
- "Đúng 10 phút" (rubric B2) vs. "khoảng 10 phút" (PDF/announcement): plan for 10 minutes sharp.
- "Giờ GPU và cấu hình máy" for a Mac without a discrete GPU or for a shared H100: GPU-active hours are not measured anywhere; the honest options are device wall-hours plus hardware config, stated as such.
- Late penalty ("10 % mỗi ngày") for partial days is unspecified.
- "Cam kết trước mốc giữa kỳ" in S1.3 maps to the D1 W7 (D2) checkpoint row of the proposal, which `report_d2/main_d2.tex` already assumes.
- The PDF text extraction garbled some Vietnamese diacritics; every requirement used here is also present in the announcement or the rubric comments, so no requirement depends on a garbled word.
