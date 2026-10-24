# Results summary - run `d2-mac-latency-r2-2b-l1rr-v1` (main, mac-latency)

report_eligible: **False** - Not eligible: smoke/unfrozen run, incomplete collection, trials the judge never attempted, or collection sources changed during a session ([]).

**Post-hoc revision evaluated on the same tasks** (protocol `r2-posthoc`): the revision was designed after the frozen v3 results on these tasks were seen; this is not a pre-planned result.

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | l1_rerank | 50/50 | 0.0 [0-0] | 50 | PENDING | PENDING | 0.744 | 0.706 | 0.710 | 0.400 | 0.367 | 0.378 | 0.0 |
| labour_vi_v1 | l1_rerank | 50/50 | 0.0 [0-0] | 50 | PENDING | PENDING | 0.978 | 0.956 | 0.957 | 0.578 | 0.533 | 0.548 | 0.0 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | l1_rerank | 20/18/7/0 | 0/3/2/0 | 55.6 | 0.0 | 14.3 | 60.0 | 46.0 |
| labour_vi_v1 | l1_rerank | 28/14/3/0 | 1/4/0/0 | 37.8 | 20.0 | 22.2 | 80.0 | 64.0 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | l1_rerank | True | 13.3/30.1 | 3.24/6.84 | 92 | 10477/607 | 2.94 | 0.000 |
| labour_vi_v1 | l1_rerank | True | 14.6/27.6 | 3.07/5.74 | 92 | 12932/802 | 3.92 | 0.000 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| hcmut_v1 | l1_rerank | 0.0 (n=15) | 0.0 (n=30) | 0.0 (n=5) |
| labour_vi_v1 | l1_rerank | 0.0 (n=12) | 0.0 (n=33) | 0.0 (n=5) |

## Refusals and clarifications by source (counts: total / expected-answer / expected-refuse)

| benchmark | variant | source | refused | clarified |
|---|---|---|---|---|
| hcmut_v1 | l1_rerank | model | 19 / 16 / 3 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | repair_exhausted | 2 / 2 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 9 / 7 / 2 |
| labour_vi_v1 | l1_rerank | budget | 1 / 0 / 1 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | model | 8 / 6 / 2 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | repair_exhausted | 9 / 8 / 1 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 3 / 3 / 0 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

