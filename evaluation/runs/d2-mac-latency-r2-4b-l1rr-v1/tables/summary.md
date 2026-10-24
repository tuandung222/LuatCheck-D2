# Results summary - run `d2-mac-latency-r2-4b-l1rr-v1` (main, mac-latency)

report_eligible: **False** - Not eligible: smoke/unfrozen run, incomplete collection, trials the judge never attempted, or collection sources changed during a session ([]).

**Post-hoc revision evaluated on the same tasks** (protocol `r2-posthoc`): the revision was designed after the frozen v3 results on these tasks were seen; this is not a pre-planned result.

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | l1_rerank | 50/50 | 0.0 [0-0] | 50 | PENDING | PENDING | 0.978 | 0.944 | 0.942 | 0.733 | 0.711 | 0.719 | 0.0 |
| labour_vi_v1 | l1_rerank | 50/50 | 0.0 [0-0] | 50 | PENDING | PENDING | 1.000 | 0.967 | 0.971 | 0.744 | 0.711 | 0.719 | 0.0 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | l1_rerank | 35/10/0/0 | 0/5/0/0 | 22.2 | 0.0 | 33.3 | 100.0 | 80.0 |
| labour_vi_v1 | l1_rerank | 36/7/2/0 | 0/5/0/0 | 20.0 | 0.0 | 41.7 | 100.0 | 82.0 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | l1_rerank | True | 33.0/86.0 | 9.02/19.87 | 42 | 12976/836 | 3.48 | 0.000 |
| labour_vi_v1 | l1_rerank | True | 29.8/71.9 | 7.80/17.97 | 43 | 12086/922 | 3.72 | 0.000 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| hcmut_v1 | l1_rerank | 0.0 (n=15) | 0.0 (n=30) | 0.0 (n=5) |
| labour_vi_v1 | l1_rerank | 0.0 (n=12) | 0.0 (n=33) | 0.0 (n=5) |

## Refusals and clarifications by source (counts: total / expected-answer / expected-refuse)

| benchmark | variant | source | refused | clarified |
|---|---|---|---|---|
| hcmut_v1 | l1_rerank | model | 8 / 3 / 5 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | repair_exhausted | 7 / 7 / 0 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | model | 7 / 2 / 5 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | repair_exhausted | 5 / 5 / 0 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 2 / 2 / 0 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

