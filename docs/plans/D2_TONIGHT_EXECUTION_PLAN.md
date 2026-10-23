# D2 execution plan: night of Fri 23 → Sat 24 Oct 2026

> Written 2026-10-24 00:45 +07 by the supervising agent. Owner: Võ Phạm Tuấn Dũng. Implementation is delegated to
> Sonnet agents with strict file ownership; the supervisor reviews and verifies every step before it is committed.

## Scope (decided by the owner)

- Benchmarks: only the frozen `hcmut_v1` and `labour_vi_v1`. Zalo, ViLegalExperts and benchmark v2 are later work.
- Accuracy numbers come from server 82 (H100) tonight. Mac latency is measured later, only when the owner says so;
  tonight the Mac command is only checked on 2 tasks.
- The web UI must be polished and demo-ready on the Mac, with recorded GIFs and an MP4 backup.
- Every run must be traceable (harness version, commit, script, models), and the report must never mix stale and
  current results.

## Phases

| # | Phase | Who | Done when | Status |
|---|---|---|---|---|
| 0 | Full test suite on the current tree | supervisor (background) | suite finishes; failures explained | running |
| 1 | Experiment tracking layer: provenance in manifests, run registry with freshness (`make runs`), table provenance headers, `make report-check`, backfill of old runs | Sonnet (evaluation owner) | registry lists every run with kind/status/freshness; report-check fails on stale tables; tests green | running |
| 2 | Web UI demo polish, live run of every demo query, GIFs + MP4 | Sonnet (frontend owner) | UI builds, every demo query verified live, GIFs in `docs/presentation/gifs/` | running |
| 3 | Review phase 1; re-run evaluation, pipeline and reranker tests; commit the benchmark code (UI files excluded while in flight) as the owner, push | supervisor | clean commit on origin; working tree clean in collection paths | pending |
| 4 | Server 82 setup: pull; Python venv on top of the CUDA-12 torch env; prism llama.cpp CUDA build; Bonsai GGUF + reranker weights pinned; free GPU; port 28081; preflight | Sonnet (82 runner) | `make benchmark-preflight` passes on 82 with recorded GPU/driver/model identities | pending |
| 5 | Gate trial then full GPU matrix: OFF/L1/L1+rerank × seeds 42/123/2026 + closed-book and oracle baselines (seed 42), ~1,090 trials, judge skipped on 82, tmux/job with resume | Sonnet (82 runner), supervisor monitors | `status` shows complete, 0 unexplained errors, registry `current` | pending |
| 6 | Mac command check on 2 tasks (`scripts/run_d2_benchmarks.sh mac` with `--limit 2`) | supervisor | run completes end to end; marked smoke | pending |
| 7 | Copy the run back to the Mac, judge (gateway), analyze, tables, registry, report-check; independent recomputation of headline numbers | Sonnet + supervisor verification | tables reproducible from the run; report-check passes | pending |
| 8 | Review UI work (watch GIFs, try the UI), commit | supervisor | demo works from a clean start | pending |
| 9 | Insert tables into the report, write results text without overclaiming, compile, page check, report-check, commit and push | Sonnet (report owner) + supervisor review | report has no red result placeholders except human audit / team items | pending |
| 10 | Export the human-audit package for the team (Sat 24 evening) | Sonnet (evaluation owner) | blank label sheet + instructions; scorer refuses without labels | pending |

## Rules for every phase

- Real inference only; failures are results; nothing fabricated (AGENTS.md).
- Main runs start only from a clean commit that exists on origin. Smoke runs are never report-eligible.
- One heavy model at a time on the Mac; on 82 only free GPUs, loopback ports owned by us, no sudo, NFS storage.
- Commits are authored by the owner, without AI co-author trailers.
- Nothing in the report cites a run that `make runs` does not list as `current` and report-eligible.

## Risks and fallbacks

| Risk | Fallback |
|---|---|
| Python deps conflict in the shared conda env on 82 | separate venv with `--system-site-packages` on the CUDA-12 env; never modify shared envs |
| Throughput on 82 lower than expected | run seed 42 first for all cells, then 123 and 2026, so a partial run still gives one complete seed |
| Judge gateway rate limits | resumable judge with spend guard (USD 6); judge can run later from the Mac |
| UI agent cannot make a query reliable on the 2B model | replace the query with a stable one from the same corpus; document it |
