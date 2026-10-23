# Run notes - `bench-smoke-evalimpl-20261023`

Generated 2026-10-23 22:29 +07 by evaluation/run_d2.py from the run's own files (manifest, trials, judge, analysis). Facts below are copied from artifacts; nothing is estimated. The operator section at the end is for human remarks.

## Run

- profile: `mac-latency` (workers 1, latency reportable: True), phase `smoke`
- matrix: benchmarks ['hcmut_v1', 'labour_vi_v1'], variants ['off', 'l1'], seeds [42], limit 3
- collection: status `collected`, planned 12, recorded 12, execution errors 0 {}, resumes 0, wall time in this/all sessions 367.45 / 367.45 s
- sources changed while a session ran: None (non-empty = run not report-eligible)
- request-level rejections by a healthy dependency (not outages, not retried): 0
- created 2026-10-23T15:06:56.109073+00:00, last finished 2026-10-23T15:13:30.874448+00:00
- git: commit `9ee48da01af736418de1ddb7b70251b5789686e9`, dirty True (24 tracked changes, 19 untracked); the exact code is in `source_snapshot/`

## Systems

- machine: macOS-27.0.1-arm64-arm-64bit-Mach-O / Apple M4 / python 3.14.4; GPUs: None
- controller server: alias `prism-ml/Ternary-Bonsai-2-2B-gguf`, GGUF sha256 `d5f01a4ecaf49239653308ee732ad1a0c5f802c0ddb997549fc7b694c8b45928`, ftype PQ2_0 - 2.13 bpw (group 128), build `b1-73bfe6c`, slots 4, n_ctx 32768, chat-template sha256 `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715`
- server command line (local only): `/Users/admin/src/prism-llama.cpp/build/bin/llama-server -m /Users/admin/.cache/huggingface/hub/models--prism-ml--Ternary-Bonsai-2-2B-gguf/snapshots/683f7be2629342a50987627b40881e54761a2430/Ternary-Bonsai-2-2B-PQ2_0.gguf -ngl 99 -fa on -c 32768 --host 127.0.0.1 --port 8081 --alias prism-ml/Ternary-Bonsai-2-2B-gguf --jinja --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64`
- operator note on the server: None
- reranker runtime (variants that rerank): {}
- seed canary: {"prompt": "Vi\u1ebft m\u1ed9t c\u00e2u ng\u1eafn v\u1ec1 m\u00f9a thu \u1edf H\u00e0 N\u1ed9i.", "same_seed_identical": false, "different_seed_differs": true}
- preflight warnings: ['seed_reproducible', 'machine_idle']; failed checks: []

## Judge and analysis

- judge: {"requested": "deepseek/deepseek-v4-flash", "thinking": {"type": "enabled"}, "reasoning_effort": "high", "max_tokens": 24000, "revision_pinned": false, "returned_model_ids": {"deepseek/deepseek-v4-flash": 17}}
- attempts 17 (valid 12, invalid share 0.29411764705882354), reasons {'ValueError: Supporting/contradicting quote is absent from supplied source': 4, 'ValueError: Claim quote is absent from actual candidate answer': 1}, gateway-reported cost $0.0326 (not an invoice), median attempt 45.492 s
- coverage {'planned': 12, 'recorded': 12, 'judged_or_error': 12, 'judge_attempted_but_invalid': 0, 'judge_never_attempted': 0}; unknown trials 0; report_eligible **False** (Not eligible: smoke/unfrozen run, incomplete collection, trials the judge never attempted, or collection sources changed during a session ([]).)
- human audit: `analysis/human-audit/` (labels blank until people label them); agreement/kappa: PENDING

## Independent recomputation of the headline counts

Counts of answered/refused/clarified/errors and strict successes per benchmark x variant recomputed from trials.jsonl and judge/judgments.jsonl without the analysis code: **ALL MATCH**

- hcmut_v1/l1: match {'trials': 3, 'answered': 0, 'refused': 2, 'clarified': 1, 'errors': 0, 'strict_successes': 1}
- hcmut_v1/off: match {'trials': 3, 'answered': 2, 'refused': 0, 'clarified': 1, 'errors': 0, 'strict_successes': 0}
- labour_vi_v1/l1: match {'trials': 3, 'answered': 1, 'refused': 2, 'clarified': 0, 'errors': 0, 'strict_successes': 1}
- labour_vi_v1/off: match {'trials': 3, 'answered': 2, 'refused': 1, 'clarified': 0, 'errors': 0, 'strict_successes': 1}

## Operator notes

PENDING: anomalies, manual steps, retries and who ran this must be written here by the operator; the tool does not guess them.
