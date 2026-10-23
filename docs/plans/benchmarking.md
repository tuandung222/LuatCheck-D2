# D2 benchmarking: runner, judge, tables

One command runs the two official benchmarks on real native inference and produces the report tables:

```
make benchmark-d2                        # RUN_PROFILE=mac-latency (default)
make benchmark-d2 RUN_PROFILE=gpu-accuracy BENCH_EXTRA="--endpoint http://127.0.0.1:18081/v1 --workers 8"
make benchmark-smoke                     # 3 tasks, 1 seed, off+l1, pipeline check only
```

Nothing here starts or stops a model server. `AGENTS.md` applies: no mocks, no rule-based fallback, a backend failure is an
execution-error row (never a refusal or a zero-cost success), failed runs are preserved, and no score, token count, label
or cost is ever filled in.

## Files

| File | Role |
|---|---|
| `evaluation/benchmarks/<name>/benchmark.yaml` | `tasks` (relative to the dir), `corpus`, `profile`, `review_status` |
| `evaluation/run_benchmark.py` | `freeze`, `run`, `status` |
| `evaluation/judge_benchmark.py` | `packets`, `judge`, `analyze`, `all` (blinded packets, gateway judge, metrics, human-audit export) |
| `evaluation/render_benchmark_tables.py` | LaTeX tables -> `report_d2/benchmark_results.tex` (`main_d2.tex` is never edited) |
| `config/benchmark/model_prism_gguf2b.yaml` | controller model block, budgets, retrieval/verifier defaults |
| `config/benchmark/variants.yaml` | `off`, `l1`, `l1_rerank` (selected through config only) |
| `config/benchmark/profile_{mac_latency,gpu_accuracy}.yaml` | run profiles |
| `config/benchmark/judge_gateway.json` | judge: `deepseek/deepseek-v4-flash`, thinking enabled, effort high, 24 000 max tokens, 3 attempts, 8 concurrent |
| `tests/test_benchmark_runner.py` | real-component tests (needs the llama-server on 8081 for the inference tests) |

Benchmarks: `hcmut_v1` (50 tasks, ready) and `labour_vi_v1` (50 tasks over 10 documents; `tasks.json`, `data/corpus/labour_vi_v1.json`
and the `labour_vi_multi` profile are being built elsewhere). `run`/`freeze` refuse a benchmark until all three exist and pass the
mechanical checks; they do not silently drop it. Task schema: `task_id, category, question, expected_behavior (answer|refuse),
expected_answer, ground_truth_article_ids, reference_evidence[{article_id, exact_quote}]`. Corpus records are keyed by `doc_id` or `article_id`.

## 1. Freeze (before any main collection)

```
make benchmark-freeze                    # or: .venv/bin/python evaluation/run_benchmark.py freeze --benchmark hcmut_v1
```

Mechanical checks (the lock is refused if any fails): unique `task_id`s and questions, required fields, `expected_behavior` in
{answer, refuse}, gold ids exist in the corpus, `reference_evidence` ids equal the gold ids, every `exact_quote` is a verbatim substring
of its record, the domain profile loads and its `corpus_path` equals the benchmark corpus. `benchmark.lock.json` stores sha256 of
`tasks.json`, the corpus, the profile YAML, `benchmark.yaml` and every verification file present (`verify_*.json`, `recheck_*.json`,
`review*.json`, `provenance.json`, `ADJUDICATION.md`, `README.md`, `*_BRIEF.md`, `draft_*.json`). These checks do not certify the gold
answers; `hcmut_v1` is AI-verified, not human-reviewed, and the report must say so.

`freeze` on an unchanged benchmark is a no-op; on a changed one it refuses unless `--refreeze`, which archives the old lock as
`benchmark.lock.superseded-<time>.json`. `run` refuses a main run when any hash differs from the lock, or when there is no lock.
`--allow-unfrozen` exists for `--limit` smoke runs only and marks the run non-eligible.

## 2. Run

```
.venv/bin/python evaluation/run_benchmark.py run --benchmark all --variants off,l1,l1_rerank --seeds 42 123 2026 \
    --run-profile mac-latency --model-config config/benchmark/model_prism_gguf2b.yaml --output evaluation/runs/<new-dir> --execute
```

* `--benchmark` is repeatable (`hcmut_v1`, a directory, or `all`). `--output` must be new; `--resume` continues the same directory.
* `--limit N` (smoke): N tasks per benchmark, round-robin over categories (`single`, `multi`, `out_of_scope`), file order inside a category.
* `--endpoint URL` overrides `model.endpoint` (loopback only, e.g. a forwarded port). `MODEL_ENDPOINT`/`MODEL_NAME`/`MODEL_PROVIDER`
  environment overrides are refused so the model cannot change silently.
* Variants: `off` (verification off), `l1` (`l1_on`), `l1_rerank` (`l1_on` + `retrieval.reranker` {enabled, cross_encoder,
  `AITeamVN/Vietnamese_Reranker`, top_k_in 20, top_k_out 5, max_length 1024}). The runner builds every benchmark x variant config before the first
  request and raises `ConfigError` if `src/` does not honour a key (pydantic would otherwise drop it silently). There is no runner-side reranking.
* `mac-latency`: one worker, one request in flight, one agent per benchmark x variant. Per-trial and per-model-call latency (also the server's
  `timings`: prompt/decode ms, cached prompt tokens), plus peak RSS of the runner and of the local `llama-server` (sampled with `ps` every 0.5 s;
  Metal/unified-memory buffers that are not resident in the process are not captured). Latency is reportable.
* `gpu-accuracy`: `--workers N` (default 8), one agent per worker. The runner refuses unless `/props` reports `total_slots >= N` and `-c` is at least
  `context_tokens x N`. Latency is recorded but flagged `latency_reportable: false`; the tables print "n/r".
* Budgets (`max_tool_calls 5`, `max_repairs 2`, `max_steps 8`, `wall_seconds 180`, `timeout_seconds 60`) come from the model config and are enforced by the agent loop.
  Model output cap: `max_output_tokens 1024` (the app default; the 768 of `d2_gguf2b_diagnostic.yaml` produced "truncated by token limit" execution errors in a smoke run).
* Errors: each failure is a row (`system_error: true`, `error_kind`, `error_message`) and counts as a failed trial. A run stops after 5 consecutive `backend_error`
  rows (server down) with the rows kept. `--resume --retry-errors` appends a new `attempt` only for `backend_error` rows; earlier rows stay and
  analysis uses the latest attempt but counts the superseded ones. `model_output_error`, `wall_timeout` and similar are never retried.
* Resume refuses if variants, seeds, limit, profile, model config, endpoint, tasks/corpus or any snapshotted source file changed (the run's sources are
  byte-snapshotted in `source_snapshot/`; edits to `src/` while a run is in progress make a resume impossible, so freeze the checkout first).

Run directory: `manifest.json` (git commit + dirty counts, hardware, server `/props` + GGUF sha256 + llama-server command line when local, run profile, effective configs per
benchmark/variant, source sha256s, planned/recorded/missing trials, peak memory, `runs_sha256`), `runs.jsonl` (one row per benchmark/variant/seed/task/attempt, the
`evaluation/run_eval.py` row schema plus `benchmark`, `variant`, `category`, `attempt`, per-call `calls`, `model_call_wall_ms`, `non_model_wall_ms`, `peak_memory_mb`,
full `ledger`), `source_snapshot/`, `state/` (per-worker SQLite/audit files; memory is disabled and answer reuse off).

Check progress: `.venv/bin/python evaluation/run_benchmark.py status --run-dir <dir>`.

### Latency caveats (Mac)

* `llama-server` keeps prompt-cache slots, so repeated prompt prefixes make later trials faster than a cold start; all variants share this effect, but trial order matters
  (variants alternate per task). The first trial of each agent includes warm-up (and, for `l1_rerank`, the first reranker call), which shows in p95.
* The Mac must be otherwise idle and on power. Other agents running tests on the same machine perturb latency; the manifest cannot detect that.
* `l1_rerank` adds reranker time to `non_model_wall_ms` and typically longer prompts.

## 3. Judge and analysis

```
.venv/bin/python evaluation/judge_benchmark.py all --run-dir <run-dir> --execute   # packets -> judge -> analyze
```

* Packets (`<run>/judge/judge_packets.json`): question, scope, expected behaviour, reference answer, reference evidence, **full text** of the gold records and of every record the
  candidate cited, candidate behaviour/answer/citations. No variant, seed, benchmark, mode or timing. `private_mapping.json` maps `review_id` back (the id is a hash of the run id and trial key).
  Execution-error trials are not sent to the judge (strict success = failure; listed in `unjudged_execution_errors.json`).
* Judge: the gateway model `deepseek/deepseek-v4-flash` (same thinking/effort settings as `config/d2_judge_gateway.json`; `max_tokens` 24 000 because observed completions reach about 10 000
  tokens), prompt `evaluation/judge_prompt.txt` + the generalised protocol embedded in `judge_benchmark.py`, validation by `evaluation/judge_gateway.validate`. Only invalid/unparseable/unfinished
  judgments are retried (up to 3 attempts; `--retry-invalid` adds more). Retries add one disclosed line to the user message because the gateway appears to serve identical completions for byte-identical
  requests. Every attempt is stored as `judge/attempts/<review_id>-a<N>.json` with request, raw body, returned model id, usage and cost; attempts are never overwritten and a rerun skips packets that already have a valid judgment.
* Metrics (`<run>/analysis/summary.json`, per benchmark x variant): strict success (behaviour appropriate, correctness 2, completeness 2, all claims supported; errors count as failures;
  the headline rate is the lower bound over all planned trials with unknown/invalid counted as failures, with the unknown count, an upper bound, and a task-level bootstrap 95% interval),
  behaviour-appropriate rate, claim faithfulness (micro over claims), Recall@1/3/5, Hit@5, MRR over answerable tasks, citation-ID precision/recall (`evaluation/metrics.py`), latency p50/p95
  (mac-latency only), tokens per trial, answered/refused/clarified/error counts, tool calls/repairs, lexical unsupported proxy (labelled as a proxy), per-seed and per-category success, judge cost
  (gateway-reported `usage.cost` and `x-litellm-response-cost`; not an invoice).
* `analysis/human-audit/`: stratified (benchmark x variant x category x judge outcome, one hash-selected item per stratum, filled to 30 per benchmark) blinded packets + `labels.csv` with blank labels.
  These are LLM-judge estimates until people label the sample; `human_judge_agreement` stays null.
* `report_eligible` is true only for a complete, frozen, non-smoke run in which every trial is judged or an execution error.

## 4. Tables

```
.venv/bin/python evaluation/render_benchmark_tables.py --run-dir <run-dir>      # -> report_d2/benchmark_results.tex
```

Two tables to `\input` (needs `booktabs`, `multirow`, `graphicx`, `xcolor`): `tab:benchmark-main` (benchmark x variant: success with interval, behaviour, faithfulness, Recall@5, MRR, citation P/R; caption says
LLM-judge estimates, not human labels) and `tab:benchmark-ops` (counts, latency, tokens, calls, unknown judgments, judge cost). Missing cells, missing variants and missing benchmarks are red `[PENDING]`.
A smoke/non-eligible run is refused for the report path.

## 5. Mac (latency) procedure

1. `make prism-server` in its own terminal (loopback 8081, alias `prism-ml/Ternary-Bonsai-2-2B-gguf`).
2. Idle machine, plugged in, no other model servers competing (the Ollama runner on this machine also holds memory).
3. `make benchmark-smoke` (a few minutes), then `make benchmark-d2`.

## 6. GPU server 82 (accuracy) procedure

Requires the PrismML fork built with CUDA and PQ2_0 support on CUDA. Confirm this first (load the GGUF, check a short completion matches the Mac output in kind); if the fork cannot run PQ2_0 on CUDA,
a different quantization is a different model and its results must be labelled as such. Server 82 is shared: no sudo, pick a free GPU (`gpu_status`), keep files on the NFS path.

1. Build once (on 82, under `/home/dungvpt/...`): `git clone --depth 1 -b prism https://github.com/PrismML-Eng/llama.cpp && cmake -S llama.cpp -B llama.cpp/build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF && cmake --build llama.cpp/build -j --target llama-server`.
   Download the same GGUF (`prism-ml/Ternary-Bonsai-2-2B-gguf`, `Ternary-Bonsai-2-2B-PQ2_0.gguf`) and compare its sha256 with the Mac manifest's `server.model_file_sha256`.
2. Start the server with `-np N` and `-c = 8192 x N` (gpu-bridge `job_start`, so the log and git/env metadata are kept):
   `CUDA_VISIBLE_DEVICES=<free> llama-server -m <gguf> -ngl 99 -fa on -c 65536 -np 8 --host 127.0.0.1 --port 8081 --alias prism-ml/Ternary-Bonsai-2-2B-gguf --jinja --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64`.
3. Forward the port to the Mac on a free local port (gpu-bridge `port_forward`, 82:8081 -> 127.0.0.1:18081).
4. `make benchmark-d2 RUN_PROFILE=gpu-accuracy BENCH_EXTRA="--endpoint http://127.0.0.1:18081/v1 --workers 8 --server-note 'H100 <n>, llama.cpp prism <build>, -np 8 -c 65536'"`.
   The runner records the server `/props` and your note (operator text, not measured).
5. `l1_rerank` loads one reranker copy per worker. With 8 workers on a 16 GB Mac that is too much memory; either lower `--workers`, or run the runner itself on 82 (sync the repo, create the environment, use the server on
   loopback, then `sync_pull` the run directory and run `judge_benchmark.py all` / the renderer locally). The runner warns about this on macOS.
6. Latency from this profile is not reportable. Report mac-latency latency from a separate sequential Mac run, and say which run each number comes from.

## Reproducibility

A run directory holds everything needed to audit it: byte copies of the code, configs, benchmark files, corpus and profile (`source_snapshot/`, hashes in the manifest), the model server identity, every row with its full
ledger (all prompts and raw native responses), and, after judging, every judge attempt. `analyze` recomputes all numbers from those files and verifies the snapshot hashes. The model sampling seed is set per trial
(`--seeds`), but llama.cpp output is not guaranteed bit-reproducible across runs or hardware; the frozen quantity is the recorded run, not a promise of identical regeneration.

## Cost and time estimates (extrapolations)

Basis: 2 benchmarks x 3 variants x 3 seeds x 50 tasks = 900 trials. Per-trial wall times observed on the Apple M4 (16 GB) in smoke runs of 3-6 trials: `off` roughly 7-26 s, `l1` roughly 8-41 s, `l1_rerank` 29-61 s
(first trials include warm-up). Judge: about $0.0016 and 40 s per packet in 11 packets (about 1.6-2.8 k prompt tokens, 2-11 k completion tokens each).

| Item | Estimate |
|---|---|
| mac-latency collection, 900 trials | about 4.5-6.5 h wall (about 60 s per task-seed across the three variants; dominated by `l1_rerank`) |
| gpu-accuracy collection, 8 workers on one H100 | about 20-60 min if the GPU server is not contended; unmeasured here |
| Judge, about 850-900 packets at 8 concurrent | about 1.2-1.5 h wall, about $1.5-3 gateway-reported (more if many retries) |
| Local model cost | not an API charge; energy and device time are not measured |

These are planning figures from a handful of trials, not measurements of the full run; the real totals are in the run manifest and `analysis/summary.json`.

## Blocked on other work

* `labour_vi_v1`: `tasks.json`, `data/corpus/labour_vi_v1.json`, profile `labour_vi_multi` (and its `corpus_path`) must exist; then `make benchmark-freeze`.
* Gold review: both benchmarks are AI-verified; human review/audit labels are not part of this tooling's output.
