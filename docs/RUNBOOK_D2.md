# RUNBOOK D2 - benchmark collection on server 82 (accuracy) and on the Mac (latency)

Written 2026-10-23 22:30 +07 (UTC+7). For the agent that runs the D2 benchmarks tonight. Read `AGENTS.md` first: real inference only, a backend failure is an execution
error (never an answer or refusal), nothing is filled in, failed runs are preserved, no commit/push, never print or read `.env` (the judge key is read by
`evaluation.judge_gateway.local_environment()` only). Background: `docs/plans/D2_COMPLETION_PLAN.md`, `docs/plans/benchmarking.md`, `docs/reviews/metrics_review_2026-10-23.md`.

What is being run: 2 benchmarks (`hcmut_v1`, `labour_vi_v1`, frozen, 50 tasks each) x 3 variants (`off`, `l1`, `l1_rerank`) x 3 seeds (42, 123, 2026) = **900 system trials per machine** plus **190 diagnostic-baseline trials** (`closed_book` on all 50 tasks and `oracle` on the 45 answerable tasks of each benchmark, seed 42, no tools; reported in their own table, never pooled; they run automatically in `all`, disable with `--baselines none`), controller
Ternary Bonsai 2 2B GGUF (PQ2_0) on the PrismML llama.cpp fork **commit 73bfe6c**, judge DeepSeek Flash through the gateway. Everything is config
(`config/benchmark/{d2_matrix,variants,profile_gpu_accuracy,profile_mac_latency,expected_server,warmup,strata}.yaml`); one command runs it:
`evaluation/run_d2.py all` (preflight -> collect -> judge -> analyze -> tables -> `RUN_NOTES.md`), wrapped by `scripts/run_d2_benchmarks.sh`.

**Hands off while a run is in progress:** do not edit `src/`, `config/`, `evaluation/run_benchmark.py|metrics.py|bench_preflight.py`, benchmark files or corpora. The runner snapshots them, refuses to resume on
drift and stops before building a new agent if one changed. If a fix is unavoidable, start a NEW run directory and say so in `RUN_NOTES.md`.

Do not run the full pytest suite or other model processes on the Mac while the latency run is in progress.

---------------------------------------------------------------------------------------------------

## A. Server 82 (GPU accuracy run)

Rules of the shared server (gpu-bridge `agent_docs`): no sudo, pick a FREE GPU, keep files on the NFS path (`/home/dungvpt/...`), touch only your own processes. Use the gpu-bridge tools
(`agent_docs`, `gpu_status`, `disk_status`, `run`, `job_start`, `job_wait`, `sync_push`, `sync_pull`, `tmux_sessions`, `tmux_peek`); the commands below are what to run inside them.

### A0. Ports and ownership on the shared server (read before starting anything)
Other users run services on 82 (seen at 22:50 +07: 8000, 8002, 8016, 8018, 8067, 8080, 18001, 18004; 8081/8082 free but could be taken any time). Therefore in GPU mode:
* the controller server uses an **uncommon high port, `PRISM_PORT=28081`** (default of `scripts/run_d2_benchmarks.sh gpu` and `make prism-server-gpu GPU_PORT=28081`), bound to `127.0.0.1` only; the runner is told with `--endpoint http://127.0.0.1:28081/v1` (the script and `make benchmark-d2-gpu` add it). Use the SAME port for the whole run and for every resume (the endpoint is part of the resume check). No reranker server is needed on 82 (torch reranker inside the runner). Mac mode keeps 8081 / 8082.
* **before reusing** a healthy server on the port, the script checks that the listening process belongs to your user and is a `llama-server` (lsof/ss); otherwise it aborts with exit 4 and a message. It never uses someone else's server.
* **before starting** a server it aborts (exit 4) if anything at all listens on the port. If 28081 is taken: `PRISM_PORT=28091 ...` (any free high port).
* it only ever stops the server **it started** (pid in `logs/d2/<RUN_ID>/server.pid`, and only if that pid is still a llama-server); a server you started by hand, or anyone else's, is never touched. Check yourself: `ss -ltnp | grep 28081`.

### A1. Pick a GPU and look around
```
gpu_status                      # choose a GPU with ~0 MiB used and no other users' processes. At 22:50 +07 GPUs 2 and 3 were free, 0 and 1 were in use by others - re-check, it changes.
                                # remember its index as $GPU (the script refuses a GPU with > 4000 MiB in use; FORCE_GPU=1 overrides - do not)
disk_status                     # NFS has space? (a run is ~250 MB; weights ~3 GB; llama.cpp build ~1 GB)
env_list                        # find a conda env with torch+CUDA, or plan a venv (A3)
```

### A2. Sync the repository (code, benchmarks, corpora, configs) to 82
`sync_push` the repo to `/home/dungvpt/luatcheck-d2` **excluding**: `.venv*`, `node_modules`, `frontend`, `evaluation/runs` (old runs are not needed), `report_d1`, `report_d2`, `report_d3`, `output`, `tmp`, `.git` (optional).
The benchmark locks (`evaluation/benchmarks/*/benchmark.lock.json`), `data/corpus/*.json`, `config/` and `evaluation/benchmarks/*/` MUST be included. On 82:
```
cd /home/dungvpt/luatcheck-d2
sha256sum evaluation/benchmarks/hcmut_v1/tasks.json evaluation/benchmarks/labour_vi_v1/tasks.json   # expect 591513d0f8fc... and f6bfe0efb471... (see locks)
```
(The runner re-checks every lock hash anyway and refuses on drift. Without `.git` the manifest records `commit: null`; the source snapshot and the hashes identify the code - note the Mac commit hash in `RUN_NOTES.md`.)

### A3. Python environment on 82
```
cd /home/dungvpt/luatcheck-d2
python3 -m venv /home/dungvpt/envs/luatcheck-d2 && source /home/dungvpt/envs/luatcheck-d2/bin/activate     # or activate the conda env from env_list
pip install -r requirements.txt -r requirements-model-backends.txt     # torch must be a CUDA build
python - <<'EOF'
import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())
EOF
```
`torch.cuda.is_available()` must be True. (`CUDA_VISIBLE_DEVICES=$GPU` selects the GPU for the server AND for the torch reranker inside the runner.)

### A4. Build the PrismML llama.cpp with CUDA (same commit as the Mac)
```
mkdir -p /home/dungvpt/src && cd /home/dungvpt/src
git clone https://github.com/PrismML-Eng/llama.cpp prism-llama.cpp          # full clone, NOT --depth 1: we need an exact commit
cd prism-llama.cpp && git checkout 73bfe6cc485554822f80c473a3c0c4f25e80f41b
nvcc --version                                                              # a CUDA toolkit must exist; if not, ask the user (no sudo)
cmake -S . -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DCMAKE_CUDA_ARCHITECTURES=90
cmake --build build -j 16 --target llama-server
build/bin/llama-server --version 2>&1 | head -3                             # expect build b1-73bfe6c
```
If GitHub is blocked on 82: on the Mac `tar czf /tmp/prism-llama.cpp.tgz --exclude=build -C ~/src prism-llama.cpp`, `sync_push` it, untar, then the cmake lines above.
`export PRISM_DIR=/home/dungvpt/src/prism-llama.cpp`. Preflight will refuse a server whose `/props build_info` does not contain `73bfe6c`.

### A5. Get the GGUF and the reranker weights (and verify them)
```
mkdir -p /home/dungvpt/models/bonsai /home/dungvpt/models/reranker
hf download prism-ml/Ternary-Bonsai-2-2B-gguf Ternary-Bonsai-2-2B-PQ2_0.gguf --local-dir /home/dungvpt/models/bonsai
sha256sum /home/dungvpt/models/bonsai/Ternary-Bonsai-2-2B-PQ2_0.gguf        # MUST be d5f01a4ecaf49239653308ee732ad1a0c5f802c0ddb997549fc7b694c8b45928
hf download AITeamVN/Vietnamese_Reranker --revision f536976248403314225d7fdfdbc87f0e9516a54e --local-dir /home/dungvpt/models/reranker/AITeamVN_Vietnamese_Reranker
sha256sum /home/dungvpt/models/reranker/AITeamVN_Vietnamese_Reranker/model.safetensors   # MUST be 1cecccab406ec6d3f13da8ccdc5e853a1372e51845322163655ab530d3730071
export GGUF_PATH=/home/dungvpt/models/bonsai/Ternary-Bonsai-2-2B-PQ2_0.gguf
export RERANKER_MODEL_DIR=/home/dungvpt/models/reranker/AITeamVN_Vietnamese_Reranker
```
If Hugging Face is blocked on 82: `sync_push` the files from the Mac (`~/.cache/huggingface/hub/models--prism-ml--Ternary-Bonsai-2-2B-gguf/snapshots/*/Ternary-Bonsai-2-2B-PQ2_0.gguf`, `~/models/reranker/AITeamVN_Vietnamese_Reranker/`) and verify both sha256 values on 82.
**Never** substitute another quantisation: a different file is a different model (ask the user first and label it). Preflight enforces both hashes.

### A6. Gate: does PQ2_0 run on CUDA? (3 questions, ~2 minutes)
In tmux session `d2` window 1:
```
tmux new -s d2
cd /home/dungvpt/luatcheck-d2 && source /home/dungvpt/envs/luatcheck-d2/bin/activate
export CUDA_VISIBLE_DEVICES=$GPU PRISM_DIR GGUF_PATH RERANKER_MODEL_DIR     # e.g. GPU=2; PRISM_PORT defaults to 28081
RUN_ID=d2-gpu-gate SKIP_JUDGE=1 EXTRA="--benchmarks hcmut_v1 --variants off,l1,l1_rerank --seeds 42 --limit 3 --allow-unfrozen" scripts/run_d2_benchmarks.sh gpu
```
This starts the server (`-np 8 -c 131072` on 127.0.0.1:28081, log `logs/d2/d2-gpu-gate/server.log`), runs preflight (identity, seed canary, a real reranker search on CUDA), 9 trials and the tables, then stops the server it started.
**Pass criteria:** preflight all green (warnings allowed but read them), `evaluation/runs/d2-gpu-gate/manifest.json` has `execution_errors: 0` and sensible terminal statuses (answered / refused / clarified), `tables/summary.md` readable.
**If the server crashes or prints errors for PQ2_0 on CUDA: STOP** (do not switch quantisation) and report to the user; fallback is the Mac overnight run (section C).

### A7. Launch the main run (tmux or nohup)
```
tmux new -s d2-main      # (or: nohup env ... scripts/run_d2_benchmarks.sh gpu > logs/d2/main.out 2>&1 &)
cd /home/dungvpt/luatcheck-d2 && source /home/dungvpt/envs/luatcheck-d2/bin/activate
export CUDA_VISIBLE_DEVICES=$GPU PRISM_DIR GGUF_PATH RERANKER_MODEL_DIR
RUN_ID=d2-gpu-main-v1 SKIP_JUDGE=1 scripts/run_d2_benchmarks.sh gpu            # SKIP_JUDGE: the gateway key is not on 82 (omit it if 82 has the key)
```
Via gpu-bridge instead: `job_start` with the same command line, `resume=true` (the script is resumable).
Defaults: 8 workers = 8 slots (`-np 8`, 16384 context per slot), trial timeout 300 s, 900 system + 190 baseline trials. Output: `evaluation/runs/d2-gpu-main-v1/`.

### A8. Monitor
```
python evaluation/run_d2.py status --run-dir evaluation/runs/d2-gpu-main-v1     # counts per cell, error kinds, ETA
cat evaluation/runs/d2-gpu-main-v1/progress.json                                 # trials/min, ETA
tail -f logs/d2/d2-gpu-main-v1/run.log                                          # one line per finished trial
nvidia-smi -i $GPU                                                              # utilisation / memory of the GPU in use
tmux_peek (gpu-bridge)                                                          # read the tmux pane without attaching
```
Healthy: `execution errors` close to 0; any `wall_timeout` / `model_output_error` rows are results (investigate the share, do not hide them). A growing count of `backend_error` means the server or reranker is unhealthy.

### A9. Resume after a crash / stop
The run stops by itself after 5 consecutive "dependency down" failures, on SIGTERM/Ctrl-C (it finishes in-flight trials), or if the process is killed. Rows are kept (fsync per trial).
1. Find the cause (`tail logs/d2/d2-gpu-main-v1/server.log`, `nvidia-smi`, `dmesg` is not available - read the log).
2. Run **exactly the same command** as in A7. The script restarts the server if it is down, `run_d2.py` detects the existing run directory and resumes it (`--resume --retry-errors`: outage rows get a new attempt, old rows stay; a half-written last line is moved to `trials.jsonl.partial-*`).
3. The resume REFUSES if code/config/benchmark files, the GGUF, the llama.cpp build, the chat template or the sampler changed since the run started. Do not work around it: start `RUN_ID=d2-gpu-main-v2` and explain in `RUN_NOTES.md`; keep v1 as it is.
Never delete or edit `trials.jsonl`.

### A10. Finish, judge, copy back
When the log says `DONE` (or `COLLECTED, JUDGE NOT RUN`): `evaluation/runs/d2-gpu-main-v1/{manifest.json,trials.jsonl,warmup.jsonl,progress.json,source_snapshot,state,pipeline.log}` exist and `manifest.json` has `"status": "collected"`.
Copy back with `sync_pull` the whole directory `evaluation/runs/d2-gpu-main-v1` (about 150-250 MB) and `logs/d2/d2-gpu-main-v1/` to the Mac (same relative paths).
Then on the Mac (the gateway key is there; add `--judge-concurrency 12` only if the gateway accepts it):
```
cd /Users/admin/Desktop/Recents/LuatCheck-D2
make judge RUN=evaluation/runs/d2-gpu-main-v1 D2_EXTRA="--judge-concurrency 12"       # ~1,090 packets, ~$2.9, ~1.3-2.7 h; resumable (judged packets are never re-judged)
make tables RUN=evaluation/runs/d2-gpu-main-v1                                         # analysis, tables/, RUN_NOTES.md
```
The judge refuses an estimate above `max_judge_usd` (6.0 in `config/benchmark/d2_matrix.yaml`) and tells you to raise `--max-judge-usd` deliberately.
Check `evaluation/runs/d2-gpu-main-v1/RUN_NOTES.md`: "ALL MATCH" in the independent recomputation, `report_eligible`, unknown trials, invalid-judge share. Add the operator remarks (anomalies, retries, who ran what) in its last section by hand.
`report_d2/benchmark_results.tex` is written only on explicit request and only for an eligible run: `.venv/bin/python evaluation/render_benchmark_tables.py --run-dir evaluation/runs/d2-gpu-main-v1 --publish`. Ask the user/Opus before publishing; `report_d2/**` belongs to the report owner.

---------------------------------------------------------------------------------------------------

## B. Preflight by hand (any machine)

```
.venv/bin/python evaluation/run_d2.py preflight --profile gpu-accuracy --endpoint http://127.0.0.1:28081/v1   # or: --profile mac-latency (default 8081); prints every check
```
| Check | Fails when | Fix |
|---|---|---|
| `lock:*` | a frozen file changed | restore the file; never re-freeze for D2 |
| `controller` / `controller_health` | no server on `PRISM_PORT` or alias not served | start it (`make prism-server` / `make prism-server-gpu GPU=2`) |
| `controller_gguf_sha256`, `_quantisation`, `_llama_cpp_build` | other GGUF / build | fetch the right file / checkout 73bfe6c (`--allow-build-drift` exists for debugging only; the run is then not comparable) |
| `controller_slots`, `controller_context` | `-np` < workers or `-c` < 8192 x workers | restart the server with `-np 8 -c 131072` |
| `seed_honoured` (warn) | different seeds gave identical text | server ignores seeds: do not start |
| `seed_reproducible` (warn) | same seed gave different text | normal under load or on another GPU; make sure nothing else uses the server |
| `reranker_server_health` (mac) | reranker server down | `make rerank-server-mac` (section C) |
| `reranker_gguf` (mac) | the reranker server runs a GGUF that is not pinned / whose sha256 differs | serve f16 via `make rerank-server-mac` |
| `reranker_weights`, `reranker_revision` (gpu) | weights not at the pinned revision / safetensors sha256 differs | A5 |
| `reranker_cuda` / `reranker_canary` | CUDA unavailable / real rerank search failed | A3, check `CUDA_VISIBLE_DEVICES` |
| `machine_idle` (error for mac-latency) | load > 0.5 x CPUs | stop other work; `--allow-busy` only for non-reportable tries |
| `git` (warn) | uncommitted changes | recorded; the snapshot holds the exact bytes; `--require-clean` makes it an error |

---------------------------------------------------------------------------------------------------

## C. Mac (latency run, profile `mac-latency`)

Reportable latency/memory comes ONLY from this run. Preconditions: the Mac is plugged in, idle (quit browsers/IDEs/agents; no tests, no other model servers, no reranker-parity probe), nothing else using port 8081/8082. Prevent sleep with `caffeinate`.
Reranker GGUF: `scripts/reranker/build_gguf.sh` (once; produces `~/models/reranker/gguf/Vietnamese_Reranker-{f16,Q8_0,f32}.gguf` and `SHA256SUMS` from the pinned revision). The D2 Mac profile serves **f16**; preflight checks its sha256 against `config/benchmark/expected_server.yaml` and `SHA256SUMS` and refuses another file.

### C1. Servers (two terminals, or let the script start them)
```
make prism-server PRISM_CTX=65536        # Bonsai on 127.0.0.1:8081 (same GGUF sha256 as the GPU run)
make rerank-server-mac                   # llama.cpp reranker (GGUF f16) on 127.0.0.1:8082 (scripts/reranker/serve_mac.sh f16); refuses a port already in use
curl -s 127.0.0.1:8081/health; curl -s 127.0.0.1:8082/health          # both {"status":"ok"}
```
### C2. Preflight and a smoke run (10 minutes)
```
.venv/bin/python evaluation/run_d2.py preflight --profile mac-latency
make benchmark-smoke SMOKE_VARIANTS=off,l1,l1_rerank RUN_PROFILE=mac-latency        # both benchmarks, 3 tasks, 1 seed, judge included (~$0.05)
```
### C3. The latency run
Option 1 (preferred when the GPU accuracy run succeeded): one seed, all variants, 300 trials, about 1-1.5 h idle:
```
caffeinate -dimsu env RUN_ID=d2-mac-latency-main-v1 EXTRA="--seeds 42" scripts/run_d2_benchmarks.sh mac
```
Option 2 (if the GPU run failed): the whole matrix on the Mac (900 system + 190 baseline trials, about 2.8 h idle, up to 4.5 h if the machine is not idle), then accuracy AND latency come from this run:
```
caffeinate -dimsu env RUN_ID=d2-mac-latency-full-v1 scripts/run_d2_benchmarks.sh mac
```
The script starts any missing server, runs `run_d2.py all` (includes judge and tables; add `SKIP_JUDGE=1` to skip), and stops only the servers it started. Resume = the same command again.
Per trial: 2 un-scored warm-up trials per agent (kept in `warmup.jsonl`), then strictly sequential trials; p50/p95 per trial and per LLM call, tokens/s, peak RSS of runner and llama-server are in `analysis/summary.json` (`latency.reportable: true`).
### C4. Compare the two machines honestly
```
make benchmark-compare RUN_A=evaluation/runs/d2-gpu-main-v1 RUN_B=evaluation/runs/d2-mac-latency-main-v1
```
Expect `comparable: false` only through `may_differ`-type differences being listed separately; any `must_match` difference (GGUF, llama.cpp build, chat template, sampling, collection sources, variants/seeds) means the runs are different systems. The reranker runtime differs by design (GGUF Q8_0 on llama.cpp vs torch fp16): do not pool `l1_rerank` accuracy across machines; take accuracy from the GPU run and latency from the Mac run and say so in the report.

---------------------------------------------------------------------------------------------------

## D. After collection

1. `make tables RUN=<run>`; read `tables/summary.md` and `RUN_NOTES.md`.
2. Human audit (Sat 24 Oct): give the team `analysis/human-audit/packets.json`, `SEMANTIC_JUDGING.md` and `labels.csv` (fill WITHOUT looking at judge verdicts; one row per item and reviewer, reviewer name required). Score: `make audit-score RUN=<run> LABELS="path/to/filled.csv [more.csv]"`. Without valid labels the scorer prints no number (`no_labels`); partial/invalid files are reported line by line. The result lands in `analysis/human-audit/agreement.json` and the next `make tables` shows it in the table caption; otherwise the caption keeps the red placeholder.
3. Report numbers: strict success is an LLM-judge estimate (not human labels), lower bound over all trials with errors as failures; retrieval Recall/MRR are saturated and cannot separate variants; read success also by closed-book stratum (`tables/benchmark_diagnostics.tex`).
4. Smoke runs and runs with `report_eligible: false` are never report evidence.

## D2. Provenance: main runs, registry, report check (do this before and after every run)

* **Before a MAIN run**: commit everything in `src/ config/ evaluation/ data/corpus requirements*.txt` and **push** (`git push origin main`). A main run is refused (before any server is touched) on a dirty collection path or a commit that is not on origin; smoke / `--allow-unfrozen` / `--kind diagnostic` runs may be dirty but are marked and never report-eligible. Server 82 has no `.git`: on the clean, pushed Mac checkout run `make stamp-provenance` (writes `PROVENANCE.json`, valid only while the collection sources are unchanged), then sync the repository including that file.
* Every run records in `manifest.json`: `kind`, `harness_version` (`evaluation/provenance.py`, bumped by hand on any metric / collection / judge-rule / table change), commit + branch + remote + on-origin, exact `argv` and the environment variables that matter (`RUN_ID`, `CUDA_VISIBLE_DEVICES`, ports ...), host (hostname, OS, GPU/driver/CUDA, Python and package versions), model identities (GGUF sha, llama.cpp commit, reranker sha/revision), benchmark lock hashes, config hashes, `run_state` (running|complete|incomplete|failed) and local start/end time. Judge and analysis stages write `stage_provenance` (harness version, judge prompt hash, the run and trials hash they consumed); tables write `tables/PROVENANCE.json`.
* **`make runs`** (= `python evaluation/run_d2.py registry`) rewrites `evaluation/runs/REGISTRY.md` + `registry.jsonl`: one row per run with kind, state, commit, harness, `report_eligible` and **freshness** against HEAD: `current`, `pinned@<commit>` (a result frozen on purpose, listed under `pinned:` in `registry_overrides.yaml`; holds only while the run's recorded fingerprint equals that commit's sources, checked with `git show`), `stale: <what differs>` (re-run, never quote), `historical: <reason>`, `superseded_by: <run>`, `remote/not synced` (listed under `remote:`, lives only on server 82), `incomplete`, `n/a`. Marks live in `evaluation/runs/registry_overrides.yaml` and an optional `<run>/RUN_STATUS.json` (`{"superseded_by": "<run>"}` when a re-run replaces a run); runs are never deleted.
* Every table the renderer writes has a `% === LUATCHECK-PROVENANCE v1 ===` comment block (run id, commit, harness, generator command) and a visible "Source: run ... @ commit, harness ..." line.
* **Final steps, always**: `make runs` then **`make report-check`**. It fails if any result table in `report_d2/main_d2.tex` comes from a run that is not `main`, not report-eligible or not `current`, if the tables of one file mix commits / harness versions, if trials changed after a table was rendered, or if a table with measured numbers is written inline without `% PROVENANCE: run=<id>` / `% PROVENANCE: historical <reason>` (`n/a` only for design / plan tables). It writes `report_d2/RESULTS_PROVENANCE.md` (table -> run -> commit -> command). Do not send the report while it says FAILED. If a run is `stale` because you changed code after the run, either re-run it or (analysis-only change) re-run `make tables`, bump nothing, and re-check; if it is stale because the harness version moved, the run must be repeated.

## F. Post-hoc revision r2 on server 82 (2B on GPU 2, 4B on GPU 3) and the v3-vs-r2 comparison

Written 2026-10-24 (UTC+7). The frozen v3 runs (`d2-gpu-main-{hcmut,labour}-v3`, commit 957579b, harness 1.1.2) stay the pre-planned result and are **pinned** in the registry (`pinned@957579b`).
The revision r2 (ten opt-in switches, see the comment header of `config/benchmark/model_prism_gguf2b_r2.yaml` and `docs/reviews/v3_failure_analysis_2026-10-24.md`) was designed AFTER
the v3 results of `hcmut_v1` / `labour_vi_v1` were seen. Its runs are `kind: main` but carry `protocol: r2-posthoc`; every table and `RUN_NOTES.md` prints **"post-hoc revision evaluated on the same tasks"**.
Same matrix as v3 (2 benchmarks x 3 variants x 3 seeds + closed_book/oracle) for two controllers: 2B (isolates the system fix) and 4B (isolates model size on the revised system).
Run ids: `d2-gpu-r2-{2b,4b}-{hcmut,labour}-v1` (one run per benchmark, as for v3, so a resume stays small).

What the runner enforces: `config/benchmark/d2_matrix_r2.yaml` sets `protocol`; the runner refuses a model config whose keys the installed `src/` would drop, a revised config without the protocol tag, a tagged run without all ten switches, and a resume across a different system. The manifest records
`protocol`, `protocol_label` and `system_revision` (`requested_in_model_config` and `effective`, the values `src/` resolved) and the same in `fingerprint.must_match` (`protocol`, `system_revision_effective`); each `effective_configs[...]` entry shows `domain.profile` (set per benchmark) together with `domain.profile_variant: r2`.
Check before launching: `jq '.system_revision.effective, .protocol' evaluation/runs/<run>/manifest.json`.

### F1. Before launching (Mac): commit and push, stamp, sync
```
git push origin main && make stamp-provenance          # a main run needs a clean, pushed tree; sync PROVENANCE.json with the repo (server 82 has no .git)
```
Ports: 2B uses 28081 (GPU 2), 4B uses 28082 (GPU 3). 4B uses about 11 GB VRAM (check `nvidia-smi -i 3`; the script refuses a GPU with > 4000 MiB used by others). Both GGUFs:
`/home/dungvpt/workspace/dungvpt/models/bonsai/Ternary-Bonsai-2-2B-PQ2_0.gguf` (sha256 d5f01a4e...) and `/home/dungvpt/workspace/dungvpt/models/bonsai/4b/Ternary-Bonsai-2-4B-PQ2_0.gguf` (sha256 d406b1e9..., pinned in `expected_server.yaml` under `controllers:`; preflight pins the controller by alias with `expected_controller(alias)`).

### F2. Launch (tmux on 82; resume = run the same command again)
Common environment (the script starts `llama-server -np 16 -c 262144 --kv-unified` itself when nothing healthy answers on the port; `--workers 16` = the slots, as in v3):
```
cd /home/dungvpt/luatcheck-d2
export PYTHON=/home/dungvpt/workspace/dungvpt/d2-setup/py.sh SKIP_JUDGE=1 NP=16 CTX_PER_SLOT=16384
export PRISM_DIR=/home/dungvpt/workspace/dungvpt/src/prism-llama.cpp
export RERANKER_MODEL_DIR=/home/dungvpt/workspace/dungvpt/models/reranker/AITeamVN_Vietnamese_Reranker
export MATRIX=config/benchmark/d2_matrix_r2.yaml
```
2B on GPU 2, port 28081 (tmux session `r2-2b`):
```
export CUDA_VISIBLE_DEVICES=2 PRISM_PORT=28081 MODEL_CONFIG=config/benchmark/model_prism_gguf2b_r2.yaml MODEL_ALIAS=prism-ml/Ternary-Bonsai-2-2B-gguf
export GGUF_PATH=/home/dungvpt/workspace/dungvpt/models/bonsai/Ternary-Bonsai-2-2B-PQ2_0.gguf
RUN_ID=d2-gpu-r2-2b-hcmut-v1  EXTRA="--benchmarks hcmut_v1 --workers 16"      scripts/run_d2_benchmarks.sh gpu
RUN_ID=d2-gpu-r2-2b-labour-v1 EXTRA="--benchmarks labour_vi_v1 --workers 16"   scripts/run_d2_benchmarks.sh gpu
```
4B on GPU 3, port 28082 (second tmux session `r2-4b`):
```
export CUDA_VISIBLE_DEVICES=3 PRISM_PORT=28082 MODEL_CONFIG=config/benchmark/model_prism_gguf4b_r2.yaml MODEL_ALIAS=prism-ml/Ternary-Bonsai-2-4B-gguf
export GGUF_PATH=/home/dungvpt/workspace/dungvpt/models/bonsai/4b/Ternary-Bonsai-2-4B-PQ2_0.gguf
RUN_ID=d2-gpu-r2-4b-hcmut-v1  EXTRA="--benchmarks hcmut_v1 --workers 16"      scripts/run_d2_benchmarks.sh gpu
RUN_ID=d2-gpu-r2-4b-labour-v1 EXTRA="--benchmarks labour_vi_v1 --workers 16"   scripts/run_d2_benchmarks.sh gpu
```
(`MODEL_ALIAS` is optional: the script reads `model.name` from `MODEL_CONFIG` and refuses a contradicting value. The two shells use different GPUs and ports, so they may run at the same time. The script stops only a server it started, so the second benchmark of a controller starts a fresh server; set `KEEP_SERVERS=1` to keep it.)
A dry run prints the plan and the judge estimate: `.venv/bin/python evaluation/run_d2.py all --profile gpu-accuracy --matrix config/benchmark/d2_matrix_r2.yaml --model-config config/benchmark/model_prism_gguf4b_r2.yaml`.
A preflight by hand (needs the server): `$PYTHON evaluation/run_d2.py preflight --profile gpu-accuracy --matrix $MATRIX --model-config $MODEL_CONFIG --endpoint http://127.0.0.1:$PRISM_PORT/v1`.

### F3. Copy back, judge, tables (Mac), registry
`sync_pull` each `evaluation/runs/d2-gpu-r2-*` and `logs/d2/d2-gpu-r2-*`; then per run `make judge RUN=evaluation/runs/<run> D2_EXTRA="--judge-concurrency 12"` and `make tables RUN=evaluation/runs/<run>`; `make runs`.
`RUN_NOTES.md` and `tables/summary.md` show the protocol line, the revision switches (requested -> effective) and the refusals/clarifications by source (`refusal_source`; `unrecorded` for the frozen v3 runs).

### F4. v3 vs r2 comparison (same tasks, paired task-level bootstrap, seeds averaged)
```
make benchmark-compare-systems ARMS="v3-2B=d2-gpu-main-hcmut-v3,d2-gpu-main-labour-v3 r2-2B=d2-gpu-r2-2b-hcmut-v1,d2-gpu-r2-2b-labour-v1 r2-4B=d2-gpu-r2-4b-hcmut-v1,d2-gpu-r2-4b-labour-v1"
# = .venv/bin/python evaluation/run_d2.py compare --arm "v3-2B=..." --arm "r2-2B=..." --arm "r2-4B=..."
```
Contrasts (default for three arms): **system effect** = r2-2B - v3-2B, **model effect** = r2-4B - r2-2B; pass `--contrast "LABEL=ARM_B minus ARM_A"` for others. Output `evaluation/comparisons/<arms>/comparison.{md,tex,json}`:
strict success per variant for every arm with the differences, plus behaviour match, Recall@5, answer rate and error rate. Every table has a `LUATCHECK-COMPARE-PROVENANCE v1` header (run, commit, harness, freshness, protocol, trials hash per arm) and prints the post-hoc sentence; `make report-check` validates it (each arm run `main`, report-eligible and `current` or `pinned`; a table FILE of ordinary result tables must not mix pinned and current runs - only comparison tables show them side by side).
Self-test on the recorded v3 runs (all differences must be exactly 0 and the cells equal each run's own `analysis/summary.json`): `compare --arm "a=d2-gpu-main-hcmut-v3,d2-gpu-main-labour-v3" --arm "b=d2-gpu-main-hcmut-v3,d2-gpu-main-labour-v3"`.

---------------------------------------------------------------------------------------------------

## E. Quick reference

| Task | Command |
|---|---|
| everything on 82 | `RUN_ID=d2-gpu-main-v1 SKIP_JUDGE=1 scripts/run_d2_benchmarks.sh gpu` |
| everything on the Mac | `caffeinate -dimsu env RUN_ID=d2-mac-latency-main-v1 EXTRA="--seeds 42" scripts/run_d2_benchmarks.sh mac` |
| dry run (what would run, judge estimate) | `.venv/bin/python evaluation/run_d2.py all --profile gpu-accuracy` |
| status | `.venv/bin/python evaluation/run_d2.py status --run-dir <run>` |
| judge / tables alone | `make judge RUN=<run>` / `make tables RUN=<run>` |
| human-audit agreement | `make audit-score RUN=<run> LABELS=<csv>` |
| which runs exist / are they current? | `make runs` (REGISTRY.md) |
| may the report be sent? | `make report-check` (RESULTS_PROVENANCE.md) |
| certify a checkout for a host without .git | `make stamp-provenance` |
| are two runs comparable? | `make benchmark-compare RUN_A=<a> RUN_B=<b>` |
| v3 vs r2 / 2B vs 4B tables | `make benchmark-compare-systems ARMS="label=run,run label=run,run ..."` (section F4) |
| r2 on 82 | section F2: `MATRIX=config/benchmark/d2_matrix_r2.yaml MODEL_CONFIG=config/benchmark/model_prism_gguf{2b,4b}_r2.yaml RUN_ID=d2-gpu-r2-{2b,4b}-{hcmut,labour}-v1 ...` |
| servers | `make prism-server`, `make prism-server-gpu GPU=2 GPU_PORT=28081 GGUF_PATH=...`, `make rerank-server-mac` |
