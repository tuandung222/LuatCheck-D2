# Reranker and NLI probe, 23 Oct 2026 (Mac, low-memory run)

Device availability: MPS=True, torch 2.14.1, macOS-27.0.1-arm64-arm-64bit. Batch size 1 per pair, one model in memory at a time, guard: RSS + MPS driver allocation <= 4 GiB.

## Caveats (read first)

- **Tiny sample**: 9 answerable queries (BLL19-10-FOREIGN_SCOPE excluded) and 29 NLI pairs. This is a probe, not a benchmark; differences of one query move Recall/MRR by 0.11.
- **NLI labels are constructed by the probe author from source text, not human labels.** Hypotheses for entailment were taken or restated from expected answers; contradictions were written by changing a quantity or polarity; neutral hypotheses are expected answers of unrelated tasks.
- **Not report evidence.** Nothing here is a reviewed answer-correctness result; first-stage numbers are rank metrics on gold article IDs only. Do not copy into D2 report tables.
- Reranker max_length was capped at 1024 tokens (lower than AITeamVN's suggested 2304) to limit memory; truncated candidates are counted below and may disadvantage long articles.
- Latencies are single-pair forward passes (after one warm-up) on a shared Mac with an Ollama runner and llama-server running; absolute values are noisy.

## Experiment A: reranking the first-stage top-20 (9 queries)

| System | Device / dtype | Recall@1 | Recall@3 | Recall@5 | MRR | Load s | Median ms/pair | p95 ms/pair | Peak RSS (sampled) GiB | Peak MPS driver GiB | Peak RSS+MPS (at checks) GiB | Truncated cands |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| first-stage HybridDomainRetriever (tfidf) | cpu | 0.778 | 0.944 | 1.000 | 0.944 | - | - | - | - | - | - | - |
| AITeamVN/Vietnamese_Reranker | mps float16 | 0.889 | 0.944 | 1.000 | 1.000 | 3.1 | 116 | 262 | 1.44 | 1.14 | 1.31 | 9/180 |
| Qwen/Qwen3-Reranker-0.6B | mps float16 | 0.889 | 1.000 | 1.000 | 1.000 | 1.0 | 296 | 622 | 3.10 | 1.39 | 2.87 | 9/180 |

Gold articles absent from the first-stage top-20 (cannot be recovered by reranking): none.

### Per-task gold ranks (1 = best; `absent` = not in top-20)

| Task | first-stage | Vietnamese_Reranker | Qwen3-Reranker-0.6B |
|---|---|---|---|
| BLL19-01-PROBATION | Dieu_25:1 | Dieu_25:1 | Dieu_25:1 |
| BLL19-02-PROBATION_WAGE | Dieu_26:1 | Dieu_26:1 | Dieu_26:1 |
| BLL19-03-NOTICE | Dieu_35:1 | Dieu_35:1 | Dieu_35:1 |
| BLL19-04-ABSENCE | Dieu_36:1 | Dieu_36:1 | Dieu_36:1 |
| BLL19-05-PREGNANCY | Dieu_37:2 | Dieu_37:1 | Dieu_37:1 |
| BLL19-06-UNLAWFUL_RESIGNATION | Dieu_40:1 | Dieu_40:1 | Dieu_40:1 |
| BLL19-07-NOTICE_AND_SEVERANCE | Dieu_35:5, Dieu_46:1 | Dieu_35:4, Dieu_46:1 | Dieu_35:3, Dieu_46:1 |
| BLL19-08-UNLAWFUL_TERMINATION | Dieu_41:1, Dieu_46:3 | Dieu_41:1, Dieu_46:3 | Dieu_41:1, Dieu_46:3 |
| BLL19-09-DEPOSIT | Dieu_17:1 | Dieu_17:1 | Dieu_17:1 |

- AITeamVN/Vietnamese_Reranker: fp16-MPS vs fp32-CPU sanity check on 4 pairs: sane=True, max |raw diff|=0.0055, same order=True (fp32-cpu raw [9.651, -7.169, -7.297, -7.123], fp16-mps raw [9.656, -7.172, -7.301, -7.129]).
- AITeamVN/Vietnamese_Reranker: resource wait 0.0 s (free memory at start 27% via memory_pressure, swap used 6.22 of 7.00 GiB).
- Qwen/Qwen3-Reranker-0.6B: fp16-MPS vs fp32-CPU sanity check on 4 pairs: sane=True, max |raw diff|=0.0218, same order=True (fp32-cpu raw [6.963, -1.477, -7.266, -5.326], fp16-mps raw [6.953, -1.469, -7.254, -5.305]).
- Qwen/Qwen3-Reranker-0.6B: resource wait 0.1 s (free memory at start 33% via memory_pressure, swap used 6.38 of 8.00 GiB).

Notes: the truncated candidates (see `truncation.pairs` in results.json) are the same article in every query's top-20 (Dieu_219, over the 1024-token cap); no gold article was truncated. The sampled peak RSS of each reranker occurs during the fp32-CPU sanity-reference scoring (before the fp16 model is moved to MPS, when MPS allocation is still 0); during the fp16-MPS run RSS stays below ~0.8 GiB and the MPS driver allocation is ~1.1-1.4 GiB. Free memory was only just above the 25% threshold when each model started, and swap was already heavily used by other processes before this probe.

## Experiment B: NLI probe (MoritzLaurer/mDeBERTa-v3-base-mnli-xnli, constructed labels)

Device mps fp32, max_length 512, label order from config {'0': 'entailment', '1': 'neutral', '2': 'contradiction'}. Load 3.0 s; median 213 ms / p95 614 ms per pair; peak RSS (sampled) 0.61 GiB, peak MPS driver 2.12 GiB, peak RSS+MPS at checks 2.21 GiB.

| Constructed class | n | correct | accuracy | predicted E / N / C |
|---|---|---|---|---|
| entailment | 9 | 6 | 0.667 | 6 / 2 / 1 |
| neutral | 9 | 7 | 0.778 | 0 / 7 / 2 |
| contradiction | 9 | 6 | 0.667 | 0 / 3 / 6 |
| all constructed | 27 | 19 | 0.704 | |

Real-model-output cases: 2/2 matched the expected label.

Pairs over 512 tokens (truncated premise): ['real-output-dieu107-california'] of 29.

| Pair | Expected | Predicted | P(entail) | P(neutral) | P(contra) | Premise tok | Truncated |
|---|---|---|---|---|---|---|---|
| BLL19-01-PROBATION::entailment | entailment | entailment | 0.998 | 0.001 | 0.000 | 51 | no |
| BLL19-01-PROBATION::contradiction | contradiction | neutral (wrong) | 0.004 | 0.910 | 0.086 | 51 | no |
| BLL19-01-PROBATION::neutral | neutral | neutral | 0.001 | 0.998 | 0.001 | 51 | no |
| BLL19-02-PROBATION_WAGE::entailment | entailment | entailment | 0.997 | 0.003 | 0.000 | 61 | no |
| BLL19-02-PROBATION_WAGE::contradiction | contradiction | contradiction | 0.001 | 0.017 | 0.982 | 61 | no |
| BLL19-02-PROBATION_WAGE::neutral | neutral | contradiction (wrong) | 0.001 | 0.006 | 0.994 | 61 | no |
| BLL19-03-NOTICE::entailment | entailment | entailment | 0.998 | 0.002 | 0.000 | 37 | no |
| BLL19-03-NOTICE::contradiction | contradiction | contradiction | 0.002 | 0.013 | 0.986 | 37 | no |
| BLL19-03-NOTICE::neutral | neutral | neutral | 0.001 | 0.996 | 0.003 | 37 | no |
| BLL19-04-ABSENCE::entailment | entailment | entailment | 0.998 | 0.002 | 0.000 | 69 | no |
| BLL19-04-ABSENCE::contradiction | contradiction | contradiction | 0.001 | 0.001 | 0.998 | 69 | no |
| BLL19-04-ABSENCE::neutral | neutral | neutral | 0.000 | 0.999 | 0.001 | 69 | no |
| BLL19-05-PREGNANCY::entailment | entailment | neutral (wrong) | 0.001 | 0.998 | 0.001 | 42 | no |
| BLL19-05-PREGNANCY::contradiction | contradiction | neutral (wrong) | 0.004 | 0.996 | 0.000 | 42 | no |
| BLL19-05-PREGNANCY::neutral | neutral | neutral | 0.003 | 0.996 | 0.001 | 42 | no |
| BLL19-06-UNLAWFUL_RESIGNATION::entailment | entailment | neutral (wrong) | 0.001 | 0.999 | 0.000 | 16 | no |
| BLL19-06-UNLAWFUL_RESIGNATION::contradiction | contradiction | contradiction | 0.000 | 0.005 | 0.994 | 16 | no |
| BLL19-06-UNLAWFUL_RESIGNATION::neutral | neutral | neutral | 0.000 | 0.999 | 0.000 | 16 | no |
| BLL19-07-NOTICE_AND_SEVERANCE::entailment | entailment | entailment | 0.994 | 0.006 | 0.000 | 51 | no |
| BLL19-07-NOTICE_AND_SEVERANCE::contradiction | contradiction | contradiction | 0.001 | 0.004 | 0.994 | 51 | no |
| BLL19-07-NOTICE_AND_SEVERANCE::neutral | neutral | neutral | 0.001 | 0.996 | 0.003 | 51 | no |
| BLL19-08-UNLAWFUL_TERMINATION::entailment | entailment | entailment | 0.955 | 0.042 | 0.003 | 25 | no |
| BLL19-08-UNLAWFUL_TERMINATION::contradiction | contradiction | contradiction | 0.001 | 0.001 | 0.998 | 25 | no |
| BLL19-08-UNLAWFUL_TERMINATION::neutral | neutral | neutral | 0.002 | 0.996 | 0.003 | 25 | no |
| BLL19-09-DEPOSIT::entailment | entailment | contradiction (wrong) | 0.000 | 0.000 | 1.000 | 58 | no |
| BLL19-09-DEPOSIT::contradiction | contradiction | neutral (wrong) | 0.271 | 0.729 | 0.000 | 58 | no |
| BLL19-09-DEPOSIT::neutral | neutral | contradiction (wrong) | 0.000 | 0.003 | 0.997 | 58 | no |
| real-output-dieu17-deposit | contradiction | contradiction | 0.003 | 0.001 | 0.996 | 178 | no |
| real-output-dieu107-california | neutral | neutral | 0.000 | 0.999 | 0.001 | 856 | yes |

Supplementary windowed scoring for real-output-dieu107-california (3 windows): aggregate (per-class max) E/N/C = 0.000 / 0.999 / 0.001 -> neutral (expected neutral). Heuristic aggregation, not the base protocol.

## OneJev1.6-0.8B

Status: skipped. Official API per the model card is `qev serve --model OmniJev/OneJev1.6-0.8B` (an HTTP server implementing TypeSafe's System One API) plus `qev.Client(...).system_one(...)`, with `qev` installed from GitHub (`pip install "qev[torch] @ git+https://github.com/OmniJev/OneJev.git"`). Running it requires (a) a network install of third-party code from a git URL and (b) starting a new model server, which this task forbids; the model is a multimodal decision model with typed Choice/Noul questions, not an NLI cross-encoder, so a direct transformers load would not be its official API. Not attempted; no numbers reported for it.

## Failures and errors

- Run history: the first launch of this rewritten probe hung (0% CPU, all threads waiting on the GIL inside safetensors during transformers 5.20.2 asynchronous weight loading) before any scoring; it was killed by hand and re-run with `HF_DEACTIVATE_ASYNC_LOAD=1` (synchronous loading, set in probe.py). No scores came from the hung launch.
- No model failures in the reported run. Earlier, a run by another tool, preserved as results_prior_killed_run.json, was killed after the probe process grew to ~13 GB RSS and the machine swapped; it scored whole batches of long articles and is not used here.
