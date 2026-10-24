# Results summary - run `d2-gpu-r2-4b-hcmut-v1` (main, gpu-accuracy)

report_eligible: **True** - Complete main run; every trial judged, an execution error, or judge-attempted (unknowns listed in coverage and counted as failures). Still LLM-judge estimates; human audit labels pending.

**Post-hoc revision evaluated on the same tasks** (protocol `r2-posthoc`): the revision was designed after the frozen v3 results on these tasks were seen; this is not a pre-planned result.

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 150/150 | 70.0 [61-79] | 4 | 84.2 | 89.8 | 0.989 | 0.953 | 0.951 | 0.844 | 0.807 | 0.820 | 2.0 |
| hcmut_v1 | l1 | 150/150 | 64.0 [53-75] | 6 | 81.2 | 90.3 | 0.989 | 0.952 | 0.950 | 0.726 | 0.693 | 0.704 | 2.0 |
| hcmut_v1 | l1_rerank | 150/150 | 60.7 [50-71] | 10 | 77.1 | 89.3 | 0.978 | 0.937 | 0.936 | 0.733 | 0.704 | 0.714 | 2.0 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 119/10/3/3 | 2/13/0/0 | 9.8 | 13.3 | 56.5 | 86.7 | 88.0 |
| hcmut_v1 | l1 | 109/20/3/3 | 0/15/0/0 | 17.4 | 0.0 | 42.9 | 100.0 | 82.7 |
| hcmut_v1 | l1_rerank | 107/24/1/3 | 2/13/0/0 | 18.9 | 13.3 | 35.1 | 86.7 | 80.0 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | False | PENDING/PENDING | PENDING/PENDING | PENDING | 10233/666 | 3.13 | 0.270 |
| hcmut_v1 | l1 | False | PENDING/PENDING | PENDING/PENDING | PENDING | 12923/807 | 3.47 | 0.282 |
| hcmut_v1 | l1_rerank | False | PENDING/PENDING | PENDING/PENDING | PENDING | 12070/763 | 3.37 | 0.312 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| hcmut_v1 | off | 73.3 (n=15) | 67.8 (n=30) | 73.3 (n=5) |
| hcmut_v1 | l1 | 80.0 (n=15) | 52.2 (n=30) | 86.7 (n=5) |
| hcmut_v1 | l1_rerank | 71.1 (n=15) | 53.3 (n=30) | 73.3 (n=5) |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | hcmut_v1 | 50 | -6.0 [-16.0,+4.0] | -5.3 [-14.7,+3.3] | +0.0 [+0.0,+0.0] | -11.6 [-22.0,-1.7] | +0.0 [-3.3,+2.7] |
| L1+rerank vs L1 | hcmut_v1 | 50 | -3.3 [-13.3,+6.7] | -2.7 [-9.3,+3.3] | -1.1 [-3.3,+0.0] | +1.0 [-6.2,+7.7] | +0.0 [-2.7,+2.7] |
| L1+rerank vs OFF | hcmut_v1 | 50 | -9.3 [-18.7,+0.0] | -8.0 [-16.7,+0.0] | -1.1 [-3.3,+0.0] | -10.6 [-20.7,-0.5] | +0.0 [-4.0,+3.3] |

## Diagnostic baselines (seed 42, no tools; NOT system variants; reference rows are the system variants on answerable tasks only)

| benchmark | row | trials | strict success % (all tasks run) | strict success % (answerable only) [95% CI] | answer rate % | cit P | cit R |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | closed_book (diagnostic baseline) | 50 | 2.0 | 0.0 [0-0] | 2.2 | -- | -- |
| hcmut_v1 | oracle (diagnostic baseline) | 45 | 82.2 | 82.2 [71-93] | 100.0 | 1.000 | 1.000 |
| hcmut_v1 | off (reference) | 135 | -- | 69.6 [60-79] | 88.1 | 0.844 | 0.807 |
| hcmut_v1 | l1 (reference) | 135 | -- | 61.5 [50-73] | 80.7 | 0.726 | 0.693 |
| hcmut_v1 | l1_rerank (reference) | 135 | -- | 59.3 [49-70] | 79.3 | 0.733 | 0.704 |

## Refusals and clarifications by source (counts: total / expected-answer / expected-refuse)

| benchmark | variant | source | refused | clarified |
|---|---|---|---|---|
| hcmut_v1 | off | model | 23 / 10 / 13 | 0 / 0 / 0 |
| hcmut_v1 | off | unrecorded | 0 / 0 / 0 | 3 / 3 / 0 |
| hcmut_v1 | l1 | budget | 1 / 1 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1 | model | 24 / 9 / 15 | 0 / 0 / 0 |
| hcmut_v1 | l1 | repair_exhausted | 10 / 10 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1 | unrecorded | 0 / 0 / 0 | 3 / 3 / 0 |
| hcmut_v1 | l1_rerank | model | 24 / 11 / 13 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | repair_exhausted | 13 / 13 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 1 / 1 / 0 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

