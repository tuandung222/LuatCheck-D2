# D2 completion plan (for the next agent)

Written 23 Oct 2026 (local time ~05:30, UTC+7). Deadline: report PDF + slide PDF emailed by the group leader before
**23:59 Sun 25 Oct 2026** (late = −10%/day). Presentation and live demo: Wed 28 Oct 2026, 18:00, room B4-305.
Teacher requirements: `report_d2/D2_REQUIREMENTS.md` (8 sections in fixed order, ≤10 content pages, repo URL + commit
hash, LLM-judge reliability checked on a human-labelled sample, one-command reproducibility).

Read first, in this order: `AGENTS.md` (integrity rules — they override convenience), this file,
`docs/plans/benchmarking.md`, `docs/plans/wiring.md`, `evaluation/benchmarks/*/README.md` and `ADJUDICATION.md`.

## 0. Ground rules (non-negotiable)

- Real inference only. A backend/model failure is an execution error, never an answer, refusal or zero cost.
- No mocks, stubs, monkeypatching or canned outputs anywhere, including tests (`tests/test_real_system.py` enforces part of this).
- Never fabricate scores, token counts, latency, costs, human labels, provenance or member contributions. Missing evidence stays a
  red `\pending{...}` placeholder in `report_d2/main_d2.tex`.
- Preserve every run directory, including failed/interrupted ones. Never overwrite a run; start a new output directory.
- The two benchmarks are frozen (`evaluation/benchmarks/*/benchmark.lock.json`). Do not edit `tasks.json`, corpora or domain
  profiles; if a defect is found, record it, fix it in a new versioned benchmark, re-freeze, and say so in the report.
- Do not commit, push, reset or stash unless the user explicitly asks. The working tree is intentionally uncommitted.
- Do not read `.env` except through `evaluation/judge_gateway.local_environment()`; never print the key.
- RAM on the Mac is 16 GB: one heavy model process at a time; do not run the full test suite concurrently with a benchmark.
- Server 82 is shared (see gpu-bridge rules): no sudo, pick a free GPU, keep files on NFS, only touch your own processes.
- Label LLM-judge numbers as LLM estimates, lexical metrics as lexical proxies; all benchmarks are AI-verified, not human-reviewed.

## 1. Verified current state

| Area | State | Evidence |
|---|---|---|
| Benchmark `hcmut_v1` | 50 tasks (40 single / 5 multi / 5 out_of_scope), corpus `data/corpus/hcmut_academic_v1.json` (143 records, 10 official HCMUT docs ≤21 pages), profile `hcmut_academic`. Haiku drafts → 2 independent Sonnet verifiers → Sonnet adjudication → independent recheck (9/9 accept). Gemma-4-31B oracle check 49/50. Frozen, tasks sha256 `591513d0f8fc…` | `evaluation/benchmarks/hcmut_v1/{tasks.json,ADJUDICATION.md,README.md,verify_*.json,recheck_C.json,benchmark.lock.json}`, `evaluation/runs/hcmut-sanity-final-v1/` |
| Benchmark `labour_vi_v1` | 50 tasks (40/5/5), corpus `data/corpus/labour_vi_v1.json` (458 records: BLLĐ 2019 + 9 labour documents ≤36 pages from congbao/chinhphu), profile `labour_vi_multi`. Same verification chain (recheck 10/11 accept; LVN-014 fix applied). Gemma oracle 50/50. Frozen, tasks sha256 `f6bfe0efb471…` | `evaluation/benchmarks/labour_vi_v1/…`, `docs/materials/labour-sources/`, `evaluation/runs/labour-sanity-final-v1/` |
| Known corpus limits | `labour_vi_v1`: NĐ 145/2020 excluded (95 pages); unnumbered annexes of ND293_2025 and TT26_2025 not extracted; TT26 number/date not printed (metadata from vanban.chinhphu.vn, file hash = official attachment). `hcmut_v1`: base regulations 2933/2931/2929 are image-only and absent; several documents are amendment-only; CTDT1862_Dieu_1 is one 19.6k-char record; HVDT2749_PhuLuc_1 duplicates HVDT1260_PhuLuc_1 text | benchmark READMEs |
| Benchmark tooling | `evaluation/run_benchmark.py` (freeze/run/status, profiles mac-latency/gpu-accuracy, resumable, refuses lock/source drift), `evaluation/judge_benchmark.py` (blinded packets, DeepSeek Flash gateway judge, analysis, stratified human-audit export with blank labels), `evaluation/render_benchmark_tables.py` (→ `report_d2/benchmark_results.tex`), Makefile targets `benchmark-freeze`, `benchmark-d2`, `benchmark-smoke` | `docs/plans/benchmarking.md` |
| Smoke run | Both benchmarks × off/l1/l1_rerank × 3 tasks × seed 42: 18/18 trials, 0 execution errors, rerank metadata present, judge ≈ $0.046 (1 unknown judgment). NOT report evidence | `evaluation/runs/bench-smoke-both-20261023/` |
| Wiring | `retrieval.reranker`, `verifier.nli` (default off), `retrieval.mode: hybrid_index`, `models.*` ModelManager, profiles `config/profiles/{lite,local-full,remote}.yaml`; frozen `config/d2_native.yaml` behaviour unchanged (pinned digests) | `docs/plans/wiring.md`, `tests/test_wiring.py` |
| Tests | Full suite run alone: 192 passed, 1 skipped (HTTP embedding success path: no embedding server), peak RSS 4.5 GB | `PYTHONPATH=. .venv/bin/python -m pytest -q tests/` |
| Model servers | Default app model: Ternary Bonsai 2 2B GGUF PQ2_0 on the PrismML llama.cpp fork (built at `~/src/prism-llama.cpp`, commit 73bfe6c), `make prism-server` → 127.0.0.1:8081. **Currently NOT running** (the session that started it ended). Ollama (Qwen2.5-3B, frozen old D2 run) on 11434. Qev OneJev servers on GPU 82 forwarded to 127.0.0.1:18001 (0.8B) / 18004 (4B) by an existing ssh tunnel (not used in D2 main runs) | `make prism-server`, `curl 127.0.0.1:8081/health` |
| Report | `report_d2/main_d2.tex` still reports the OLD frozen Qwen2.5-3B run on the 10-task `bll2019_v1` benchmark as the main result, plus diagnostics. `report_d2/benchmark_results.tex` does not exist yet. PDF currently 11 pages total (cover + 10 numbered, references on the last page) | `make report_d2` |
| Human labels | None yet. The group scheduled human labelling for **Sat 24 Oct evening**. The new judge exports an audit sample but there is **no script yet that computes human–judge agreement / Cohen's kappa for the new runs** | `evaluation/judge_benchmark.py` (export only) |
| Git | Nothing committed for D2; ~75 untracked, 33 modified, 25 deleted paths | `git status` |

## 2. Decisions already made by the user (do not re-ask)

- D2 main results = the **two official benchmarks** (`hcmut_v1`, `labour_vi_v1`), 50 tasks each.
- Controller model for D2 results = **Ternary Bonsai 2 2B GGUF** (same as the live demo).
- Variants = `off` (no verification), `l1` (L1 checks), `l1_rerank` (L1 + AITeamVN/Vietnamese_Reranker, top-20 → top-5, 1024-token cap). Seeds 42, 123, 2026.
- Accuracy is collected on GPU server 82 (`gpu-accuracy`); latency/memory are measured on the Mac (`mac-latency`).
- Vector index, L2 NLI, Qev and other components stay OUT of the D2 main experiment (final-report work).
- Human audit of the judge: Sat 24 Oct evening by the group, on the sample exported from the new main run.
- Long-term direction: domain-general assistant (see `AGENTS.md`), but D2 claims stay within the evaluated domains.

## 3. Workstreams

Dependencies: A → (B ∥ C) → D → (E ∥ F) → G → H. B and C must not run on the same machine at the same time.

### A. Pre-flight (Mac, ~15 min)
1. `curl -s 127.0.0.1:8081/health || make prism-server` (background). Wait for `{"status":"ok"}`; check `/props` model path = PQ2_0 GGUF.
2. `.venv/bin/python evaluation/run_benchmark.py status` (or `freeze --check` equivalent) — locks must match; if not, STOP and report what changed.
3. `git status --short src/ evaluation/ config/` and record the output in the run notes; do not edit `src/` from now until all main runs finish (the runner refuses resume on source drift).
4. Optional sanity: `make benchmark-smoke SMOKE_BENCHMARKS="hcmut_v1 labour_vi_v1" SMOKE_VARIANTS=off,l1,l1_rerank SMOKE_OUT=evaluation/runs/bench-smoke-preflight-<stamp>` (≈10 min, ≈$0.05).
Acceptance: server healthy, locks valid, smoke 18/18 without execution errors.

### B. Accuracy run on GPU server 82 (gpu-accuracy, ~1–2 h including setup)
Use gpu-bridge tools (`gpu_status`, `run`, `job_start`, `job_wait`, `port_forward`); read `agent_docs` first.
1. Choose a free GPU (`gpu_status`). Work under the NFS path (`/home/dungvpt/...` on 82).
2. Build the PrismML fork with CUDA (see `docs/plans/benchmarking.md` §6): `git clone --depth 1 -b prism https://github.com/PrismML-Eng/llama.cpp`, `cmake -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF`, target `llama-server`. Record the commit.
3. Get the same GGUF (`prism-ml/Ternary-Bonsai-2-2B-gguf`, file `Ternary-Bonsai-2-2B-PQ2_0.gguf`, sha256 `d5f01a4ecaf49239653308ee732ad1a0c5f802c0ddb997549fc7b694c8b45928`). 82 may block huggingface.co (proxy allowlist): if so, copy the file from the Mac HF cache via gpu-bridge `sync_push`. Verify the sha256.
4. **Gate:** confirm PQ2_0 runs on CUDA. Start a test server, send 3 benchmark questions with the model config of `config/benchmark/model_prism_gguf2b.yaml` (same sampler, `enable_thinking: false`, JSON schema), compare that outputs are valid actions. If PQ2_0 is unsupported on CUDA, STOP: a different quantisation (e.g. Q2_0) is a different model; ask the user before using it and label it.
5. Start the real server with `job_start`: `-ngl 99 -fa on -np 8 -c 65536 --jinja --alias prism-ml/Ternary-Bonsai-2-2B-gguf` and the same sampler flags as `make prism-server`.
6. Preferred: run the runner ON 82 (8 workers each load the reranker for `l1_rerank`, too much for the Mac). Sync the repo (code + benchmarks + corpora + `config/`), create a Python env there with `requirements.txt` + `requirements-model-backends.txt`, copy the AITeamVN reranker weights, then:
   `make benchmark-d2 RUN_PROFILE=gpu-accuracy BENCH_EXTRA="--endpoint http://127.0.0.1:<port>/v1 --workers 8 --server-note '<GPU model>, prism llama.cpp <commit>, -np 8 -c 65536'"`.
   Fallback: run from the Mac via `port_forward` with `--workers 2` for `l1_rerank` (memory) or run `off,l1` with 8 workers and `l1_rerank` with 2.
   The judge needs the gateway: if 82 cannot reach it (proxy allowlist allows ai-gateway01.qualgo.ai), run the judge step on the Mac against the synced run directory.
7. Expected size: 2 benchmarks × 3 variants × 3 seeds × 50 = **900 trials**. Keep the run directory even if it fails; resume with the same command.
Acceptance: run `status` reports all 900 rows (answered/refused/clarified/error all count), manifest `report_eligible` true after judging, server note recorded.

### C. Latency run on the Mac (mac-latency, sequential)
Latency in the report must come only from this profile.
- Option C1 (preferred if B succeeds): 1 seed (42) × 3 variants × 100 tasks = 300 trials ≈ 1.5–2.5 h:
  `make benchmark-d2 RUN_PROFILE=mac-latency BENCH_SEEDS=42 BENCH_OUT=evaluation/runs/d2-mac-latency-<stamp>`
  (the judge step also runs; that is fine, the accuracy table still comes from B unless B failed).
- Option C2 (if B fails): full 900 trials on the Mac overnight (≈4.5–6.5 h), then accuracy AND latency come from this run.
- Close other heavy apps; do not run tests concurrently; record llama-server RSS (runner does it).
Acceptance: latency p50/p95, tokens/trial, peak memory per variant present in `analysis/summary.json` with `latency_reportable: true`.

### D. Judging, analysis, tables (~1.5 h, ≈$1.5–3 for 900 trials)
1. `make benchmark-d2` already chains judge + analyze + render. If run separately:
   `.venv/bin/python evaluation/judge_benchmark.py all --run-dir <run> --execute`, then
   `.venv/bin/python evaluation/render_benchmark_tables.py --run-dir <accuracy run> --output report_d2/benchmark_results.tex`.
2. Check: every trial judged or an execution error; unknown judgments listed (not counted as success); gateway-reported cost recorded (not an invoice).
3. Write a short `evaluation/runs/<run>/RUN_NOTES.md`: hardware, server note, start/end, anomalies, retries, any manual step.
4. Independently recompute 3–4 headline numbers from `runs.jsonl` / `judge/` with a few lines of Python (same practice as earlier: counts per status, strict success per variant) and record the check in RUN_NOTES.
Acceptance: `report_d2/benchmark_results.tex` exists and is regenerated only from a report-eligible, frozen, non-smoke run.

### E. Human audit of the judge (Sat 24 Oct evening, group members)
1. The audit sample is exported under `<accuracy run>/analysis/human-audit/` (blank labels). Give the team clear instructions: label each item without looking at the judge verdict; fields = correctness 0/1/2, behaviour appropriate yes/no, unsupported claims count (mirror the judge rubric in `evaluation/judge_prompt.txt` / `judge_benchmark.py`). Record labeller names per item (member contribution evidence).
2. **Missing code (implement before Saturday):** a scorer that reads the filled CSV(s), validates them (no blank required fields, ids match the frozen sample, labeller recorded), and computes judge–human agreement and Cohen's kappa on the strict-success label (and on behaviour), with the sample's stratification weights stated. Put it in a new `evaluation/score_benchmark_audit.py` (pattern: `evaluation/analyze_judge.py` human-audit functions); real data only, no synthetic labels in tests (test with a CSV the test writes from existing judge rows? NO — tests must not invent labels; test validation errors only, and the agreement math on labels the team actually provides).
3. If the team does not label, the report keeps the red placeholders for agreement/kappa. Never fill them.
Acceptance: agreement + kappa computed from real labels, or placeholders retained.

### F. Report D2 rewrite (`report_d2/main_d2.tex`, ≤10 numbered content pages)
Keep the 8 required sections and their order (`tests/test_real_system.py::test_actual_report_has_eight_ordered_sections`). Keep all remaining `\pending{}` for evidence that does not exist. Section by section:
1. **Changes from the proposal:** the evaluation moved from the 10-task `bll2019_v1` set to two frozen 50-task benchmarks (why: too small, one corpus); controller for results and demo = Bonsai 2B GGUF (why: local speed/memory measurements: GGUF ≈2× faster per task than MLX, ~0.7 GB server RSS); reranker added; status table updated (done / in progress / not started / dropped). Keep pitch feedback / HR walkthrough statuses as reported by the team (no invented events).
2. **Architecture:** update Figure 1 (reranker now wired as an optional step after first-stage retrieval; Bonsai controller; NLI/vector index implemented but outside D2 runs). Replace the native trace with a real trace from the new main run (pick one trial id; quote ledger facts only).
3. **Tools/permissions:** add the reranker (read-only, local model, failure = execution error); unchanged gates otherwise.
4. **Memory/knowledge:** two corpora with provenance, sizes (143 / 458 records), ingestion pipeline (`src/ingestion`), limits listed in §1 of this plan; answer reuse disabled in the demo config and memory disabled in experiments.
5. **Evaluation (main change):** benchmark construction and verification chain (AI-only, no human/expert review — say so), counts, freezing; metrics definitions (strict success with errors as failures, behaviour-appropriate, claim faithfulness, retrieval Recall@k/MRR and citation-ID P/R as source-ID metrics, latency from mac-latency only, tokens, judge cost); `\input{benchmark_results.tex}`; judge reliability = human audit (agreement/kappa or red placeholder); error analysis: classify the execution errors and 3–4 concrete failures from the new run (same style as the current error table); reproduction = the one command `make benchmark-d2` + lock hashes. Move the old Qwen/bll2019 results to a short "earlier pilot (historical, superseded)" paragraph or drop them; keep the GPT-5.5/4B diagnostics only if space allows (they are not on the new benchmarks).
6. **Threat model:** unchanged unless new entry points (reranker adds none); keep "no attack evaluation in D2".
7. **Plan:** W45–W49 with owners (still `\pending` until the team confirms), riskiest assumption (small local controller quality — now measured), cut-scope (keep loop + reranker + two benchmarks; defer NLI/vector).
8. **Contributions + AI-use:** list AI tools actually used (Claude Code orchestrator with Sonnet/Haiku subagents, OpenAI Codex earlier, Codex Astra review, Qoder/DeepSeek Flash research, DeepSeek Flash judge, Gemma-4-31B benchmark sanity check) and what humans verified; member evidence stays `\pending` until provided.
Then `make report_d2`; check page count (`gs -q -dNODISPLAY -dNOSAFER -c "(report_d2/main_d2.pdf) (r) file runpdfbegin pdfpagecount = quit"` and where References start); fix overflow by tightening text, not by shrinking fonts below the template.
Acceptance: compiles without errors, ≤10 numbered content pages, every number traceable to a run artifact, placeholders only for genuinely missing evidence.

### G. Slides and demo prep
- `report_d2/SLIDE_DEMO_MODEL_NOTE.md` is now OUTDATED (it says main numbers come from Qwen2.5-3B). Update it: main numbers and demo both use Bonsai 2B GGUF; keep the honest caveats (AI-verified benchmarks, LLM-judge estimates).
- Demo script: `make prism-server`, UI (`make web` + frontend or `make demo`), 2–3 pre-chosen tasks that work reliably (pick from the run where Bonsai succeeded), one refusal case; record a backup video (rubric B1).
- Slides (10 minutes): changes, running architecture, demo, results table, cost/latency, threat model, plan/risks.

### H. Freeze and hand-off
- Ask the user before committing. When asked: commit on a branch, put the full commit hash and repo URL into the report title page (currently `\pending`), confirm instructor read access.
- Update `README.md` status section (benchmarks, commands, results run directory).
- Keep `evaluation/RESULTS_STATUS.md` current: list main runs, diagnostics, smoke runs and which are report-eligible.

## 4. Risks and fallbacks

| Risk | Fallback |
|---|---|
| PrismML fork cannot run PQ2_0 on CUDA | Ask the user; options: run accuracy on the Mac overnight (C2), or a labelled different quantisation on GPU |
| 82 cannot download weights/packages (proxy allowlist) | `sync_push` from the Mac (GGUF, reranker weights, wheels) |
| Judge gateway errors / cost spikes | Judge retries only invalid judgments; keep attempts; if the budget is a concern ask the user before judging 900 trials |
| Runner refuses due to source drift | Do not edit `src/` during runs; if a fix is essential, start a new run directory and disclose |
| Report over 10 pages | Shorten Sections 1/5 prose, drop diagnostics paragraph, keep tables |
| Team gives no human labels | Keep red placeholders for agreement/kappa; say "pending" honestly |
| Bonsai accuracy is low | Report it as measured; the controller-capacity diagnostic (GPT-5.5 on the old set) is the explanation only as a hypothesis |

## 5. Timeline (UTC+7)

| When | What |
|---|---|
| Fri 23 Oct (today, daytime) | A, then B on server 82 (or start C2 on the Mac if B is blocked) |
| Fri 23 Oct (evening/night) | C1 latency run on the Mac; D judging + tables; implement the audit scorer (E step 2) |
| Sat 24 Oct (daytime) | Draft F with the real tables; G slides/demo; backup video |
| Sat 24 Oct (evening) | Team human audit (E); compute agreement/kappa; insert into the report |
| Sun 25 Oct | Final F pass, page check, H commit + hash (with user approval); group leader sends before 23:59 |
