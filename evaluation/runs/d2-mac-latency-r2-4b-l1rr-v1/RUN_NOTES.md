# Run notes - `d2-mac-latency-r2-4b-l1rr-v1`

Generated 2026-10-24 20:39 +07 by evaluation/run_d2.py from the run's own files (manifest, trials, judge, analysis). Facts below are copied from artifacts; nothing is estimated. The operator section at the end is for human remarks.

## Run

- profile: `mac-latency` (workers 1, latency reportable: True), phase `main`
- protocol: `r2-posthoc` - **post-hoc revision evaluated on the same tasks** (the system was revised after the frozen v3 results on these tasks were seen; this is not a pre-planned result). Revision switches (requested -> effective): {"retrieval.first_search_anchor": "question_plus_query", "retrieval.default_top_k": 5, "tools.search_hints": true, "domain.profile_variant": "r2", "agent.require_search_before_answer": true, "verifier.repair_feedback_style": "verifier_report", "model.thought_max_chars": 800, "agent.free_duplicate_notices": true, "verifier.l1_version": "v2", "verifier.l1_sentence_support": "warn"} -> {"retrieval.first_search_anchor": "question_plus_query", "retrieval.default_top_k": 5, "tools.search_hints": true, "domain.profile_variant": "r2", "agent.require_search_before_answer": true, "verifier.repair_feedback_style": "verifier_report", "model.thought_max_chars": 800, "agent.free_duplicate_notices": true, "verifier.l1_version": "v2", "verifier.l1_sentence_support": "warn"}
- controller model config: `config/benchmark/model_prism_gguf4b_r2.yaml`
- matrix: benchmarks ['hcmut_v1', 'labour_vi_v1'], variants ['l1_rerank'], diagnostic baselines [], seeds [42], limit None
- collection: status `collected`, planned 100, recorded 100, execution errors 0 {}, resumes 0, wall time in this/all sessions 4057.25 / 4057.25 s
- sources changed while a session ran: [] (non-empty = run not report-eligible)
- request-level rejections by a healthy dependency (not outages, not retried): 0
- created 2026-10-24T12:31:17.326677+00:00, last finished 2026-10-24T13:38:59.532576+00:00
- git: commit `8cdd28d80296d0f042010d0a06bf4bb86fdbe819`, dirty True (6 tracked changes, 2 untracked); the exact code is in `source_snapshot/`

## Systems

- machine: macOS-27.0.1-arm64-arm-64bit-Mach-O / Apple M4 / python 3.14.4; GPUs: None
- controller server: alias `prism-ml/Ternary-Bonsai-2-4B-gguf`, GGUF sha256 `d406b1e912c0d2a4c124ad10bf38a76ae662fdc4d24b176451403dc7b7f30409`, ftype PQ2_0 - 2.13 bpw (group 128), build `b1-73bfe6c`, slots 4, n_ctx 65536, chat-template sha256 `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715`
- server command line (local only): `/Users/admin/src/prism-llama.cpp/build/bin/llama-server -m /Users/admin/.cache/huggingface/hub/models--prism-ml--Ternary-Bonsai-2-4B-gguf/snapshots/8d6557168168f91ea6697a4a49ed2ef622b53adb/Ternary-Bonsai-2-4B-PQ2_0.gguf -ngl 99 -fa on -c 65536 --host 127.0.0.1 --port 8081 --alias prism-ml/Ternary-Bonsai-2-4B-gguf --jinja --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64`
- operator note on the server: None
- reranker runtime (variants that rerank): {"backend": "llama_cpp", "model": "Vietnamese_Reranker-f16", "device": "server", "dtype": null, "max_length": 1024, "base_url": "http://127.0.0.1:8082", "top_k_in": 20, "top_k_out": 5, "server_model_file_sha256": "939b3f301ec6ccb524fdb6dc940ed1be33664a13038d93e3b841570005a41793", "torch": null, "cuda_devices": null}
- seed canary: {"prompt": "Vi\u1ebft m\u1ed9t c\u00e2u ng\u1eafn v\u1ec1 m\u00f9a thu \u1edf H\u00e0 N\u1ed9i.", "same_seed_identical": true, "different_seed_differs": true}
- preflight warnings: []; failed checks: []

## Judge and analysis

- judge: null
- attempts 0 (valid 0, invalid share None), reasons {}, gateway-reported cost $0.0000 (not an invoice), median attempt None s
- coverage {'planned': 100, 'recorded': 100, 'judged_or_error': 0, 'judge_attempted_but_invalid': 0, 'judge_never_attempted': 100}; unknown trials 0; report_eligible **False** (Not eligible: smoke/unfrozen run, incomplete collection, trials the judge never attempted, or collection sources changed during a session ([]).)
- human audit: `analysis/human-audit/` (labels blank until people label them); agreement/kappa: PENDING

## Operator notes

PENDING: anomalies, manual steps, retries and who ran this must be written here by the operator; the tool does not guess them.
