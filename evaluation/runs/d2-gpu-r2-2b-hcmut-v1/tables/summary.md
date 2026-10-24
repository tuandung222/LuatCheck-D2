# Results summary - run `d2-gpu-r2-2b-hcmut-v1` (main, gpu-accuracy)

report_eligible: **True** - Complete main run; every trial judged, an execution error, or judge-attempted (unknowns listed in coverage and counted as failures). Still LLM-judge estimates; human audit labels pending.

**Post-hoc revision evaluated on the same tasks** (protocol `r2-posthoc`): the revision was designed after the frozen v3 results on these tasks were seen; this is not a pre-planned result.

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 150/150 | 31.3 [22-41] | 13 | 58.4 | 67.2 | 0.856 | 0.822 | 0.820 | 0.522 | 0.496 | 0.504 | 0.0 |
| hcmut_v1 | l1 | 150/150 | 24.0 [15-33] | 7 | 43.4 | 71.2 | 0.859 | 0.819 | 0.819 | 0.381 | 0.356 | 0.363 | 0.0 |
| hcmut_v1 | l1_rerank | 150/150 | 28.7 [20-37] | 11 | 46.8 | 71.3 | 0.844 | 0.789 | 0.797 | 0.381 | 0.370 | 0.373 | 0.7 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 79/45/11/0 | 4/8/3/0 | 41.5 | 26.7 | 15.1 | 53.3 | 58.0 |
| hcmut_v1 | l1 | 59/66/10/0 | 3/9/3/0 | 56.3 | 20.0 | 12.0 | 60.0 | 45.3 |
| hcmut_v1 | l1_rerank | 60/67/7/1 | 3/10/2/0 | 55.2 | 20.0 | 13.0 | 66.7 | 46.7 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | False | PENDING/PENDING | PENDING/PENDING | PENDING | 11298/602 | 3.27 | 0.297 |
| hcmut_v1 | l1 | False | PENDING/PENDING | PENDING/PENDING | PENDING | 13396/710 | 3.55 | 0.296 |
| hcmut_v1 | l1_rerank | False | PENDING/PENDING | PENDING/PENDING | PENDING | 13780/708 | 3.63 | 0.264 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| hcmut_v1 | off | 33.3 (n=15) | 26.7 (n=30) | 53.3 (n=5) |
| hcmut_v1 | l1 | 24.4 (n=15) | 20.0 (n=30) | 46.7 (n=5) |
| hcmut_v1 | l1_rerank | 31.1 (n=15) | 23.3 (n=30) | 53.3 (n=5) |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | hcmut_v1 | 50 | -7.3 [-17.3,+2.7] | -12.7 [-22.7,-2.7] | +0.4 [-4.8,+5.9] | -14.1 [-24.2,-4.0] | +0.0 [+0.0,+0.0] |
| L1+rerank vs L1 | hcmut_v1 | 50 | +4.7 [-3.3,+12.0] | +1.3 [-9.3,+12.0] | -1.5 [-8.2,+5.2] | +1.0 [-9.4,+11.1] | +0.7 [+0.0,+2.0] |
| L1+rerank vs OFF | hcmut_v1 | 50 | -2.7 [-12.0,+6.0] | -11.3 [-22.0,-0.0] | -1.1 [-8.2,+5.9] | -13.1 [-23.5,-3.0] | +0.7 [+0.0,+2.0] |

## Diagnostic baselines (seed 42, no tools; NOT system variants; reference rows are the system variants on answerable tasks only)

| benchmark | row | trials | strict success % (all tasks run) | strict success % (answerable only) [95% CI] | answer rate % | cit P | cit R |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | closed_book (diagnostic baseline) | 50 | 12.0 | 2.2 [0-7] | 8.9 | -- | -- |
| hcmut_v1 | oracle (diagnostic baseline) | 45 | 48.9 | 48.9 [33-62] | 91.1 | 0.911 | 0.878 |
| hcmut_v1 | off (reference) | 135 | -- | 28.9 [19-39] | 58.5 | 0.522 | 0.496 |
| hcmut_v1 | l1 (reference) | 135 | -- | 21.5 [13-31] | 43.7 | 0.381 | 0.356 |
| hcmut_v1 | l1_rerank (reference) | 135 | -- | 25.9 [17-35] | 44.4 | 0.381 | 0.370 |

## Refusals and clarifications by source (counts: total / expected-answer / expected-refuse)

| benchmark | variant | source | refused | clarified |
|---|---|---|---|---|
| hcmut_v1 | off | budget | 5 / 5 / 0 | 0 / 0 / 0 |
| hcmut_v1 | off | model | 48 / 40 / 8 | 0 / 0 / 0 |
| hcmut_v1 | off | unrecorded | 0 / 0 / 0 | 14 / 11 / 3 |
| hcmut_v1 | l1 | budget | 5 / 5 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1 | model | 52 / 43 / 9 | 0 / 0 / 0 |
| hcmut_v1 | l1 | repair_exhausted | 18 / 18 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1 | unrecorded | 0 / 0 / 0 | 13 / 10 / 3 |
| hcmut_v1 | l1_rerank | budget | 5 / 5 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | model | 56 / 46 / 10 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | repair_exhausted | 16 / 16 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 9 / 7 / 2 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

