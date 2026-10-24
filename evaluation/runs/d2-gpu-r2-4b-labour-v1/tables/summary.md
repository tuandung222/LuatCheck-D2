# Results summary - run `d2-gpu-r2-4b-labour-v1` (main, gpu-accuracy)

report_eligible: **True** - Complete main run; every trial judged, an execution error, or judge-attempted (unknowns listed in coverage and counted as failures). Still LLM-judge estimates; human audit labels pending.

**Post-hoc revision evaluated on the same tasks** (protocol `r2-posthoc`): the revision was designed after the frozen v3 results on these tasks were seen; this is not a pre-planned result.

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | 150/150 | 62.0 [52-72] | 7 | 91.6 | 87.3 | 0.989 | 0.952 | 0.957 | 0.886 | 0.830 | 0.841 | 0.0 |
| labour_vi_v1 | l1 | 150/150 | 52.7 [43-63] | 6 | 75.7 | 86.3 | 0.989 | 0.952 | 0.957 | 0.759 | 0.719 | 0.728 | 2.7 |
| labour_vi_v1 | l1_rerank | 150/150 | 56.7 [47-67] | 4 | 76.7 | 85.6 | 0.993 | 0.959 | 0.964 | 0.726 | 0.678 | 0.691 | 2.7 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | 129/2/4/0 | 3/12/0/0 | 4.4 | 20.0 | 85.7 | 80.0 | 94.0 |
| labour_vi_v1 | l1 | 109/18/4/4 | 2/13/0/0 | 16.8 | 13.3 | 41.9 | 86.7 | 81.3 |
| labour_vi_v1 | l1_rerank | 106/24/1/4 | 2/13/0/0 | 19.1 | 13.3 | 35.1 | 86.7 | 79.3 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | False | PENDING/PENDING | PENDING/PENDING | PENDING | 9070/686 | 3.11 | 0.360 |
| labour_vi_v1 | l1 | False | PENDING/PENDING | PENDING/PENDING | PENDING | 11382/840 | 3.65 | 0.327 |
| labour_vi_v1 | l1_rerank | False | PENDING/PENDING | PENDING/PENDING | PENDING | 11477/865 | 3.69 | 0.269 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| labour_vi_v1 | off | 52.8 (n=12) | 63.6 (n=33) | 73.3 (n=5) |
| labour_vi_v1 | l1 | 38.9 (n=12) | 55.6 (n=33) | 66.7 (n=5) |
| labour_vi_v1 | l1_rerank | 52.8 (n=12) | 54.5 (n=33) | 80.0 (n=5) |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | labour_vi_v1 | 50 | -9.3 [-18.7,+0.0] | -12.7 [-20.7,-5.3] | +0.0 [+0.0,+0.0] | -11.2 [-19.8,-3.5] | +2.7 [+0.7,+5.3] |
| L1+rerank vs L1 | labour_vi_v1 | 50 | +4.0 [-6.0,+14.0] | -2.0 [-8.7,+5.3] | +0.4 [-2.2,+3.3] | -3.7 [-10.6,+3.2] | +0.0 [-2.7,+2.7] |
| L1+rerank vs OFF | labour_vi_v1 | 50 | -5.3 [-15.3,+4.0] | -14.7 [-24.0,-6.0] | +0.4 [-2.2,+3.3] | -14.9 [-25.3,-5.7] | +2.7 [+0.0,+6.0] |

## Diagnostic baselines (seed 42, no tools; NOT system variants; reference rows are the system variants on answerable tasks only)

| benchmark | row | trials | strict success % (all tasks run) | strict success % (answerable only) [95% CI] | answer rate % | cit P | cit R |
|---|---|---|---|---|---|---|---|
| labour_vi_v1 | closed_book (diagnostic baseline) | 50 | 24.0 | 24.4 [13-38] | 2.2 | -- | -- |
| labour_vi_v1 | oracle (diagnostic baseline) | 45 | 75.6 | 75.6 [62-87] | 97.8 | 0.967 | 0.944 |
| labour_vi_v1 | off (reference) | 135 | -- | 60.7 [50-71] | 95.6 | 0.886 | 0.830 |
| labour_vi_v1 | l1 (reference) | 135 | -- | 51.1 [40-62] | 80.7 | 0.759 | 0.719 |
| labour_vi_v1 | l1_rerank (reference) | 135 | -- | 54.1 [43-64] | 78.5 | 0.726 | 0.678 |

## Refusals and clarifications by source (counts: total / expected-answer / expected-refuse)

| benchmark | variant | source | refused | clarified |
|---|---|---|---|---|
| labour_vi_v1 | off | model | 14 / 2 / 12 | 0 / 0 / 0 |
| labour_vi_v1 | off | unrecorded | 0 / 0 / 0 | 4 / 4 / 0 |
| labour_vi_v1 | l1 | model | 17 / 4 / 13 | 0 / 0 / 0 |
| labour_vi_v1 | l1 | repair_exhausted | 14 / 14 / 0 | 0 / 0 / 0 |
| labour_vi_v1 | l1 | unrecorded | 0 / 0 / 0 | 4 / 4 / 0 |
| labour_vi_v1 | l1_rerank | model | 19 / 6 / 13 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | repair_exhausted | 18 / 18 / 0 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 1 / 1 / 0 |

## Judge reliability

Human audit: {"n": 30, "percent_agreement": 0.9, "kappa": 0.8, "kappa_scheme": "nominal", "chance_agreement": 0.5, "kappa_note": null, "bootstrap": {"agreement_ci95": [0.7666666666666667, 1.0], "kappa_ci95": [0.5374449339207048, 1.0], "kappa_defined_in_resamples": 2000, "draws": 2000}, "weighted_percent_agreement": 0.9747081712062257, "weighted_kappa": 0.9480783874928124}

