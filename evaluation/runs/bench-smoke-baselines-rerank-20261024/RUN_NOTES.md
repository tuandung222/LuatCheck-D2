# Run notes - `bench-smoke-baselines-rerank-20261024`

Generated 2026-10-24 00:23 +07 by evaluation/run_d2.py from the run's own files (manifest, trials, judge, analysis). Facts below are copied from artifacts; nothing is estimated. The operator section at the end is for human remarks.

## Run

- profile: `mac-latency` (workers 1, latency reportable: True), phase `smoke`
- matrix: benchmarks ['hcmut_v1', 'labour_vi_v1'], variants ['off', 'l1_rerank'], diagnostic baselines ['closed_book', 'oracle'], seeds [42], limit 2
- collection: status `collected`, planned 16, recorded 16, execution errors 0 {}, resumes 0, wall time in this/all sessions 477.65 / 477.65 s
- sources changed while a session ran: [] (non-empty = run not report-eligible)
- request-level rejections by a healthy dependency (not outages, not retried): 0
- created 2026-10-23T17:12:58.218263+00:00, last finished 2026-10-23T17:21:46.784883+00:00
- git: commit `67a48ece642fd61d19db8374773ef26baa038d2f`, dirty True (36 tracked changes, 43 untracked); the exact code is in `source_snapshot/`

## Systems

- machine: macOS-27.0.1-arm64-arm-64bit-Mach-O / Apple M4 / python 3.14.4; GPUs: None
- controller server: alias `prism-ml/Ternary-Bonsai-2-2B-gguf`, GGUF sha256 `d5f01a4ecaf49239653308ee732ad1a0c5f802c0ddb997549fc7b694c8b45928`, ftype PQ2_0 - 2.13 bpw (group 128), build `b1-73bfe6c`, slots 4, n_ctx 32768, chat-template sha256 `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715`
- server command line (local only): `/Users/admin/src/prism-llama.cpp/build/bin/llama-server -m /Users/admin/.cache/huggingface/hub/models--prism-ml--Ternary-Bonsai-2-2B-gguf/snapshots/683f7be2629342a50987627b40881e54761a2430/Ternary-Bonsai-2-2B-PQ2_0.gguf -ngl 99 -fa on -c 32768 --host 127.0.0.1 --port 8081 --alias prism-ml/Ternary-Bonsai-2-2B-gguf --jinja --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64`
- operator note on the server: None
- reranker runtime (variants that rerank): {"backend": "llama_cpp", "model": "Vietnamese_Reranker-f16", "device": "server", "dtype": null, "max_length": 1024, "base_url": "http://127.0.0.1:8082", "top_k_in": 20, "top_k_out": 5, "server_model_file_sha256": "939b3f301ec6ccb524fdb6dc940ed1be33664a13038d93e3b841570005a41793", "torch": null, "cuda_devices": null}
- seed canary: {"prompt": "Vi\u1ebft m\u1ed9t c\u00e2u ng\u1eafn v\u1ec1 m\u00f9a thu \u1edf H\u00e0 N\u1ed9i.", "same_seed_identical": true, "different_seed_differs": true}
- preflight warnings: ['machine_idle']; failed checks: []

## Judge and analysis

- judge: {"requested": "deepseek/deepseek-v4-flash", "thinking": {"type": "enabled"}, "reasoning_effort": "high", "max_tokens": 24000, "revision_pinned": false, "returned_model_ids": {"deepseek/deepseek-v4-flash": 16}}
- attempts 16 (valid 16, invalid share 0.0), reasons {}, gateway-reported cost $0.0209 (not an invoice), median attempt 32.8205 s
- coverage {'planned': 16, 'recorded': 16, 'judged_or_error': 16, 'judge_attempted_but_invalid': 0, 'judge_never_attempted': 0}; unknown trials 0; report_eligible **False** (Not eligible: smoke/unfrozen run, incomplete collection, trials the judge never attempted, or collection sources changed during a session ([]).)
- human audit: `analysis/human-audit/` (labels blank until people label them); agreement/kappa: PENDING

## Independent recomputation of the headline counts

Counts of answered/refused/clarified/errors and strict successes per benchmark x variant recomputed from trials.jsonl and judge/judgments.jsonl without the analysis code: **ALL MATCH**

- hcmut_v1/closed_book: match {'trials': 2, 'answered': 0, 'refused': 2, 'clarified': 0, 'errors': 0, 'strict_successes': 0}
- hcmut_v1/l1_rerank: match {'trials': 2, 'answered': 0, 'refused': 1, 'clarified': 1, 'errors': 0, 'strict_successes': 0}
- hcmut_v1/off: match {'trials': 2, 'answered': 1, 'refused': 0, 'clarified': 1, 'errors': 0, 'strict_successes': 0}
- hcmut_v1/oracle: match {'trials': 2, 'answered': 2, 'refused': 0, 'clarified': 0, 'errors': 0, 'strict_successes': 1}
- labour_vi_v1/closed_book: match {'trials': 2, 'answered': 1, 'refused': 0, 'clarified': 1, 'errors': 0, 'strict_successes': 0}
- labour_vi_v1/l1_rerank: match {'trials': 2, 'answered': 1, 'refused': 1, 'clarified': 0, 'errors': 0, 'strict_successes': 1}
- labour_vi_v1/off: match {'trials': 2, 'answered': 2, 'refused': 0, 'clarified': 0, 'errors': 0, 'strict_successes': 0}
- labour_vi_v1/oracle: match {'trials': 2, 'answered': 2, 'refused': 0, 'clarified': 0, 'errors': 0, 'strict_successes': 1}

## Operator notes

PENDING: anomalies, manual steps, retries and who ran this must be written here by the operator; the tool does not guess them.
