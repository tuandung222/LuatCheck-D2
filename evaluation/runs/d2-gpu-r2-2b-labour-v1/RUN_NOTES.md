# Run notes - `d2-gpu-r2-2b-labour-v1`

Generated 2026-10-24 19:18 +07 by evaluation/run_d2.py from the run's own files (manifest, trials, judge, analysis). Facts below are copied from artifacts; nothing is estimated. The operator section at the end is for human remarks.

## Run

- profile: `gpu-accuracy` (workers 16, latency reportable: False), phase `main`
- protocol: `r2-posthoc` - **post-hoc revision evaluated on the same tasks** (the system was revised after the frozen v3 results on these tasks were seen; this is not a pre-planned result). Revision switches (requested -> effective): {"retrieval.first_search_anchor": "question_plus_query", "retrieval.default_top_k": 5, "tools.search_hints": true, "domain.profile_variant": "r2", "agent.require_search_before_answer": true, "verifier.repair_feedback_style": "verifier_report", "model.thought_max_chars": 800, "agent.free_duplicate_notices": true, "verifier.l1_version": "v2", "verifier.l1_sentence_support": "warn"} -> {"retrieval.first_search_anchor": "question_plus_query", "retrieval.default_top_k": 5, "tools.search_hints": true, "domain.profile_variant": "r2", "agent.require_search_before_answer": true, "verifier.repair_feedback_style": "verifier_report", "model.thought_max_chars": 800, "agent.free_duplicate_notices": true, "verifier.l1_version": "v2", "verifier.l1_sentence_support": "warn"}
- controller model config: `config/benchmark/model_prism_gguf2b_r2.yaml`
- matrix: benchmarks ['labour_vi_v1'], variants ['off', 'l1', 'l1_rerank'], diagnostic baselines ['closed_book', 'oracle'], seeds [42, 123, 2026], limit None
- collection: status `collected`, planned 545, recorded 545, execution errors 1 {'model_output_error': 1}, resumes 0, wall time in this/all sessions 1386.57 / 1386.57 s
- sources changed while a session ran: [] (non-empty = run not report-eligible)
- request-level rejections by a healthy dependency (not outages, not retried): 1
- created 2026-10-24T09:59:58.334629+00:00, last finished 2026-10-24T10:23:05.892294+00:00
- git: commit `cdb6b243aac536dcfdec6fe137dc8c08f4b988f1`, dirty True (0 tracked changes, 9 untracked); the exact code is in `source_snapshot/`

## Systems

- machine: Linux-5.15.0-190-generic-x86_64-with-glibc2.35 / AMD EPYC 9754 128-Core Processor / python 3.11.14; GPUs: 0, NVIDIA H100 PCIe, 81559 MiB, 71895 MiB, 575.57.08
1, NVIDIA H100 PCIe, 81559 MiB, 4987 MiB, 575.57.08
2, NVIDIA H100 PCIe, 81559 MiB, 6557 MiB, 575.57.08
3, NVIDIA H100 PCIe, 81559 MiB, 13545 MiB, 575.57.08
- controller server: alias `prism-ml/Ternary-Bonsai-2-2B-gguf`, GGUF sha256 `d5f01a4ecaf49239653308ee732ad1a0c5f802c0ddb997549fc7b694c8b45928`, ftype PQ2_0 - 2.13 bpw (group 128), build `b10787-73bfe6cc4`, slots 16, n_ctx 262144, chat-template sha256 `a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715`
- server command line (local only): `/home/dungvpt/workspace/dungvpt/src/prism-llama.cpp/build/bin/llama-server -m /home/dungvpt/workspace/dungvpt/models/bonsai/Ternary-Bonsai-2-2B-PQ2_0.gguf -ngl 99 -fa on -np 16 -c 262144 --kv-unified --host 127.0.0.1 --port 28081 --alias prism-ml/Ternary-Bonsai-2-2B-gguf --jinja --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64`
- operator note on the server: gpu 2, NVIDIA H100 PCIe, llama.cpp prism, -np 16 -c 262144
- reranker runtime (variants that rerank): {"backend": "cross_encoder", "model": "/home/dungvpt/workspace/dungvpt/models/reranker/AITeamVN_Vietnamese_Reranker", "device": "cuda", "dtype": "float16", "max_length": 1024, "base_url": null, "top_k_in": 20, "top_k_out": 5, "server_model_file_sha256": null, "torch": "2.10.0+cu128", "cuda_devices": ["NVIDIA H100 PCIe"]}
- seed canary: {"prompt": "Vi\u1ebft m\u1ed9t c\u00e2u ng\u1eafn v\u1ec1 m\u00f9a thu \u1edf H\u00e0 N\u1ed9i.", "same_seed_identical": true, "different_seed_differs": true}
- preflight warnings: []; failed checks: []

## Judge and analysis

- judge: {"requested": "deepseek/deepseek-v4-flash", "thinking": {"type": "enabled"}, "reasoning_effort": "high", "max_tokens": 24000, "revision_pinned": false, "returned_model_ids": {"None": 66, "deepseek/deepseek-v4-flash": 668}}
- attempts 734 (valid 539, invalid share 0.2656675749318801), reasons {'ValueError: Gateway returned HTTP 524': 64, 'ValueError: Judgment fields do not match required schema': 38, 'ValueError: Claim quote is absent from actual candidate answer': 30, 'JSONDecodeError: Expecting property name enclosed in double quotes: line 2 colum': 11, 'ValueError: Supporting/contradicting quote is absent from supplied source': 48, 'ValueError: Judgeable results require a resolved reference and behaviour label': 1, 'ValueError: Gateway returned HTTP 429': 2, 'TypeError: the JSON object must be str, bytes or bytearray, not NoneType': 1}, gateway-reported cost $0.9709 (not an invoice), median attempt 41.197 s
- coverage {'planned': 545, 'recorded': 545, 'judged_or_error': 540, 'judge_attempted_but_invalid': 5, 'judge_never_attempted': 0}; unknown trials 5; report_eligible **True** (Complete main run; every trial judged, an execution error, or judge-attempted (unknowns listed in coverage and counted as failures). Still LLM-judge estimates; human audit labels pending.)
- human audit: `analysis/human-audit/` (labels blank until people label them); agreement/kappa: PENDING

## Independent recomputation of the headline counts

Counts of answered/refused/clarified/errors and strict successes per benchmark x variant recomputed from trials.jsonl and judge/judgments.jsonl without the analysis code: **ALL MATCH**

- labour_vi_v1/closed_book: match {'trials': 50, 'answered': 17, 'refused': 33, 'clarified': 0, 'errors': 0, 'strict_successes': 13}
- labour_vi_v1/l1: match {'trials': 150, 'answered': 84, 'refused': 54, 'clarified': 12, 'errors': 0, 'strict_successes': 42}
- labour_vi_v1/l1_rerank: match {'trials': 150, 'answered': 86, 'refused': 53, 'clarified': 10, 'errors': 1, 'strict_successes': 42}
- labour_vi_v1/off: match {'trials': 150, 'answered': 111, 'refused': 31, 'clarified': 8, 'errors': 0, 'strict_successes': 47}
- labour_vi_v1/oracle: match {'trials': 45, 'answered': 42, 'refused': 3, 'clarified': 0, 'errors': 0, 'strict_successes': 22}

## Operator notes

PENDING: anomalies, manual steps, retries and who ran this must be written here by the operator; the tool does not guess them.
