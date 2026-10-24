# D2 benchmarking: matrix runner, judge, analysis, tables

Updated 2026-10-23 22:35 +07. Step-by-step operation: `docs/guides/RUNBOOK_D2.md`. Metric definitions and the review of the D2 scenario: `docs/reviews/metrics_review_2026-10-23.md`.
Benchmark quality caveats (saturated retrieval, closed-book guessable items): `docs/reviews/benchmark_quality_2026-10-23.md`.

One command runs the whole matrix (benchmark x variant x seed) on real native inference, judges it and renders the tables:

```
make benchmark-d2-gpu                    # server 82, profile gpu-accuracy (workers = server slots, latency not reportable)
make benchmark-d2-mac                    # the Mac, profile mac-latency (sequential, reportable latency)
make benchmark-smoke                     # 3 tasks, 1 seed, both benchmarks, off+l1: pipeline check, never report evidence
make benchmark-d2-gpu RUN_ID=<existing>  # RESUME: the same RUN_ID is the same run directory (append only)
scripts/run_d2_benchmarks.sh gpu|mac     # same, plus starts/stops the llama-servers it needs; for tmux/nohup on 82
```

`AGENTS.md` applies: no mocks, no rule-based fallback, a backend failure is an execution-error row (never a refusal or a zero-cost success), failed runs are preserved, nothing is ever filled in.
Nothing starts a model server except `scripts/run_d2_benchmarks.sh` (and only ones it started are stopped).

## Files

| File | Role |
|---|---|
| `evaluation/benchmarks/<name>/benchmark.yaml` | `tasks`, `corpus`, `profile`, `review_status` (frozen: `benchmark.lock.json`) |
| `config/benchmark/d2_matrix.yaml` | the matrix (benchmarks, variants, seeds), model config, judge config, judge spend guard and extra judge rounds |
| `config/benchmark/variants.yaml` | `off`, `l1`, `l1_rerank` (what is compared) and `comparisons` (paired pairs). The reranker RUNTIME is not here. |
| `config/benchmark/profile_{gpu_accuracy,mac_latency}.yaml` | run profiles: workers (`auto` = server slots), `sequential`, `latency_reportable`, `require_idle`, `trial_timeout_seconds`, `warmup_trials`, and the `reranker:` runtime (mac: `llamacpp_http` at 127.0.0.1:8082; gpu: `cross_encoder`, CUDA, fp16, `${RERANKER_MODEL_DIR}`). Any `profile_*.yaml` is discovered; `--run-profile` also takes a YAML path. |
| `config/benchmark/model_prism_gguf2b.yaml` | controller model block (Bonsai 2B GGUF, sampler, budgets) |
| `config/benchmark/expected_server.yaml` | identity every run must have: GGUF sha256, PQ2_0, llama.cpp commit 73bfe6c, reranker revision + weights sha256 |
| `config/benchmark/warmup.yaml` | un-scored warm-up questions (never benchmark tasks) |
| `config/benchmark/strata.yaml` | closed-book strata (LLM estimates) for stratified reporting |
| `config/benchmark/sanity_prompts.yaml` | prompts of `evaluation/benchmark_sanity.py`, filled from the benchmark's domain profile |
| `config/benchmark/judge_gateway.json` | judge: `deepseek/deepseek-v4-flash`, thinking enabled, effort high, 24 000 max tokens, 3 attempts, 8 concurrent |
| `evaluation/run_d2.py` | the pipeline: `all`, `preflight`, `collect`, `judge`, `tables`, `notes`, `status`, `compare`, `registry`, `stamp` |
| `evaluation/provenance.py`, `registry.py`, `check_report_provenance.py` | harness version + main-run gate; run registry with freshness; report provenance check |
| `evaluation/baselines.py` | diagnostic baselines `closed_book` / `oracle` (no tools; `variants.yaml: baselines`; own table, never pooled) |
| `evaluation/run_benchmark.py` | collection engine: `freeze`, `preflight`, `run`, `status` |
| `evaluation/bench_preflight.py` | preflight checks (real server canaries) |
| `evaluation/judge_benchmark.py` | blinded packets, gateway judge, `analyze` (metrics, paired differences, strata, human-audit export) |
| `evaluation/metrics.py`, `evaluation/stats.py` | per-trial metrics; bootstrap / Wilson / kappa |
| `evaluation/render_benchmark_tables.py` | LaTeX + Markdown tables |
| `evaluation/score_benchmark_audit.py` | judge-vs-human agreement and kappa from filled `labels.csv` (no labels, no numbers) |
| `tests/test_benchmark_runner.py`, `tests/test_benchmark_metrics.py` | real-component tests (the first needs the llama-server on 8081) |

## Run directory layout (`evaluation/runs/<run-id>/`)

`manifest.json` (git commit + dirty, hardware, packages, server identity from `/props` + GGUF sha256, preflight report, fingerprint, profile, effective configs, source hashes, planned / recorded / missing trials, wall time, memory),
`trials.jsonl` (one row per benchmark / variant / seed / task / attempt incl. error rows, full ledger; legacy runs call it `runs.jsonl` and are still read), `warmup.jsonl` (un-scored warm-up trials), `progress.json` (trials/min, ETA),
`source_snapshot/` (byte copies of code, configs, benchmark files, corpus, domain profile), `state/`, `judge/` (packets, every attempt, judgments), `analysis/` (`summary.json`, `trial_details.csv`, `human-audit/`),
`tables/` (`benchmark_results.tex`, `benchmark_diagnostics.tex`, `summary.md`), `RUN_NOTES.md` (facts copied from artifacts + independent recomputation of the headline counts + an operator section), `pipeline.log`.

## 1. Freeze (before any main collection)

`make benchmark-freeze` (`run_benchmark.py freeze --benchmark all`). Mechanical checks: unique ids and questions, required fields, `expected_behavior` in {answer, refuse}, gold ids exist, evidence ids equal gold ids, every `exact_quote` verbatim in its record, the domain profile loads and its corpus equals the benchmark corpus.
`benchmark.lock.json` stores sha256 of tasks, corpus, profile, `benchmark.yaml` and the verification files. `freeze` on an unchanged benchmark is a no-op; a changed one needs `--refreeze` (the old lock is archived). `run` refuses a main run when any hash differs. `--allow-unfrozen` is for `--limit` smoke runs only.
The checks do not certify the gold answers; both benchmarks are AI-verified, not human-reviewed.

## 1b. Diagnostic baselines

`d2_matrix.yaml: baselines` adds `closed_book` (all tasks) and `oracle` (answerable tasks, gold records given up front in the read-tool observation format) at seed 42, same controller / sampler / domain prompt / constrained decoding, answer-clarify-refuse only, verification off (190 extra trials). `--baselines closed_book,oracle|none` overrides. They are separate cells (`arm: baseline`), judged by the same judge, shown in `tab:benchmark-baselines` with system rows as answerable-only reference rows, and excluded from the system tables and paired comparisons. See `docs/reviews/metrics_review_2026-10-23.md` section 1.6.

## 2. Preflight (every run, also `run_d2.py preflight`)

Nothing is run or written when a check fails. Checks: git state, lock hashes, controller reachable / alias / `/health` / GGUF sha256 / PQ2_0 / llama.cpp commit / slots and context for the workers, a 4-request **seed canary** (do different seeds differ? is the same seed reproducible?),
reranker (HTTP server health and props, or CUDA + weights sha256 against the pinned revision, then a **real first-stage + rerank search**), free disk, machine load (an error for profiles with `require_idle`). The report is stored in the manifest.

## 3. Run

`run_d2.py all --profile <p> --run-dir <dir> --execute` (or the make targets). Behaviour:
* Matrix from `d2_matrix.yaml`; `--limit/--benchmarks/--variants/--seeds` override it for smoke runs. Without `--execute` it only prints the plan and the judge estimate.
* `mac-latency`: one worker, one request in flight, one agent per benchmark x variant, 2 un-scored warm-up trials per agent (from `warmup.yaml`), per-trial and per-call latency and peak RSS of runner and llama-server. `gpu-accuracy`: `workers: auto` = the server's slots (cap 8), one agent per worker; the runner refuses unless `/props total_slots >= workers` and `-c >= 8192 x workers`; latency is recorded but flagged not reportable.
* Per-trial watchdog (`trial_timeout_seconds`, 300 s, above the agent's 180 s task budget and 60 s request timeout): a hung trial becomes a `runner_trial_timeout` error row and its agent is discarded.
* Errors: every failure is a row (`system_error`, `error_kind`, `error_message`) counted as a failed trial and reported separately. Each error row gets `error_diagnosis` (failing component, `/health` right after, HTTP status). Only dependency-down rows count toward the "5 consecutive" stop and are retried by `--resume --retry-errors` (new `attempt`, old rows kept); a healthy server rejecting one request (e.g. oversized prompt) or a `wall_timeout` / `model_output_error` is a result, not retried.
* Resume: same command. Refused on any change of variants / seeds / limit / profile content / worker count / model config / endpoint / tasks / corpus / collection sources, or of the controller identity (GGUF, build, chat template, sampler). A truncated last line is moved to `trials.jsonl.partial-*`. Sources are re-checked before every agent construction; a change stops the run and makes it non-eligible.
* SIGTERM / SIGINT: in-flight trials finish, rows are kept, exit code 2.
* The manifest `fingerprint` splits `must_match` (controller identity, sampler, code, configs, locks, seeds) from `may_differ` (hardware, parallelism, reranker runtime, packages). `run_d2.py compare A B` lists the differences.

## 4. Judge and analysis

Strict success rule (`evaluation/judge_rules.py`): behaviour appropriate, correctness 2, completeness 2, and every claim supported; for abstention outputs (expected refuse, or the candidate refused / asked to clarify) "no information in the sources" statements are not claims, `not_established` claims are ignored and only a `contradicted` claim fails. The human audit counts the same way.

Packets are blinded (no variant, seed, benchmark, timing); the judge sees the question, scope, expected behaviour, reference, full gold and cited records, and the candidate. Execution errors are not sent to the judge (strict success = failure).
Judge attempts are stored one file each and never overwritten; invalid / unparseable / unfinished judgments are retried (3 attempts, then `judge_extra_rounds` more rounds); packets still invalid are `unknown` (failure in the lower bound, listed, dagger in the tables).
The judge stage is refused when `packets_to_judge x planning_usd_per_packet` exceeds `max_judge_usd`. Key from `evaluation.judge_gateway.local_environment()` only; without it the stage reports `judge_unavailable` (exit 6) and collection / tables still complete.

`analysis/summary.json` per benchmark x variant (details and definitions: `docs/reviews/metrics_review_2026-10-23.md`): strict success (lower / upper bound, task-level bootstrap CI, seed spread, pass^k-style consistency), judge behaviour, claim faithfulness (micro, macro),
retrieval trace metrics (Recall@k, Hit@k, MRR, nDCG@5, trace/read recall, saturation share, rerank first-stage vs returned), citation-ID precision / recall / F1 (macro, conditional, micro) and groundedness checks, behaviour confusion matrix with abstention rates,
error profile (rate, Wilson CI, kinds, timeouts), latency (trial p50/p95 non-error and all, per call, non-model, rerank, decode / prefill tokens/s; mac-latency only), tokens, calls, lexical proxy (labelled), judge cost (gateway-reported; not an invoice),
strict success by closed-book stratum, and `paired_differences` (paired task-level bootstrap for the comparisons in `variants.yaml`, per benchmark and pooled, also by stratum).
`report_eligible` = frozen main run, complete collection, no packet the judge never attempted, no source change during a session. Everything judged is an LLM estimate until `analysis/human-audit/agreement.json` exists.

## 5. Tables

`run_d2.py tables --run-dir <run>` (or `make tables RUN=...`) writes `<run>/tables/`: `benchmark_results.tex` (`tab:benchmark-main`, `tab:benchmark-ops`, `tab:benchmark-paired`), `benchmark_diagnostics.tex` (`tab:benchmark-behaviour`, `tab:benchmark-strata`) and `summary.md`.
Needs `booktabs`, `multirow`, `graphicx`, `xcolor`. Missing cells, variants or benchmarks are red `[PENDING]`; non-eligible runs carry a red banner and cannot be published. `render_benchmark_tables.py --publish` copies `benchmark_results.tex` to `deliverables/d2/report/` (eligible runs only, explicit).
The main caption names the judge, says "not human labels", and shows the human-audit agreement or a red placeholder.

## 6. Human audit

`analysis/human-audit/` holds a stratified blinded sample (benchmark x variant x category x judge outcome, hash-selected, about 30 per benchmark), `packets.json` and a blank `labels.csv`. After people fill it: `make audit-score RUN=<run> LABELS=<csv...>`
(percent agreement and Cohen's kappa per dimension, per reviewer, design-weighted variants). Blank, partial or malformed labels yield `no_labels` / `invalid_labels` and no numbers.

## 6b. Experiment tracking (provenance, registry, report check)

`evaluation/provenance.py` holds `HARNESS_VERSION` (bump MAJOR/MINOR on any change to collection, metrics, judge rule/prompt, analysis or table content; PATCH for neutral edits) and the main-run gate: a main run needs a clean tree in all collection paths and a commit on origin (or a valid `PROVENANCE.json` on a host without `.git`, written by `run_d2.py stamp`). The manifest records kind, harness version + collection-source hash, git commit / branch / remote, argv + environment, host and package versions, model and reranker identities, lock and config hashes, run state and local times; judge / analysis / table stages record the harness version and the run they consumed.
`run_d2.py registry` (`make runs`) writes `evaluation/runs/REGISTRY.md`: kind, state, commit, harness, `report_eligible` and freshness (`current` / `stale: <reason>` / `historical` / `superseded_by` / `incomplete` / `n/a`) against HEAD; curated marks in `evaluation/runs/registry_overrides.yaml` and `<run>/RUN_STATUS.json`.
Every rendered table carries a provenance comment block and a visible source line; `make report-check` (`evaluation/check_report_provenance.py`) fails when the report would mix outdated and current results and writes `deliverables/d2/report/RESULTS_PROVENANCE.md`.

## 7. Cost and time (extrapolations from recorded smoke runs; the real totals are in the manifest and `RUN_NOTES.md`)

900 system + 190 baseline trials per machine profile. Judge about $2.8-2.9 gateway-reported ($0.0026-0.0027 per valid packet incl. failed attempts), about 2.2 h at 8 concurrent / 1.1 h at 16 (about 30% of attempts fail validation and are retried, 1.45 attempts per valid packet).
Mac collection about 2.4 h on an idle machine, up to 4 h on a shared one. GPU collection: unmeasured, order of 15-40 minutes. Local model cost is not an API charge; energy and device hours are not measured.

## Post-hoc revision r2 and system comparison (2026-10-24, harness 1.2.0)

The frozen v3 runs (Bonsai 2B, commit 957579b) are the pre-planned result and are `pinned@957579b` in the registry. The revision r2 (ten opt-in switches in
`config/benchmark/model_prism_gguf{2b,4b}_r2.yaml`) was designed after those results were seen on the same tasks, so its runs (`d2-gpu-r2-{2b,4b}-{hcmut,labour}-v1`,
matrix `config/benchmark/d2_matrix_r2.yaml`) are `kind: main` with `protocol: r2-posthoc`, and every table and RUN_NOTES prints "post-hoc revision evaluated on the same tasks".
Comparison (`run_d2.py compare --arm ...`, `evaluation/compare_runs.py`): system effect = r2-2B - v3-2B, model effect = r2-4B - r2-2B, paired task-level bootstrap with seeds averaged.
Clean confirmation of the revision belongs to benchmark v2 (D3). Launch commands: `docs/guides/RUNBOOK_D2.md` section F.
