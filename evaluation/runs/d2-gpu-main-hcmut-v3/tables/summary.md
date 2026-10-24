# Results summary - run `d2-gpu-main-hcmut-v3` (main, gpu-accuracy)

report_eligible: **True** - Complete main run; every trial judged, an execution error, or judge-attempted (unknowns listed in coverage and counted as failures). Still LLM-judge estimates; human audit labels pending.

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 150/150 | 18.0 [11-26] | 8 | 45.1 | 70.0 | 0.674 | 0.554 | 0.582 | 0.317 | 0.337 | 0.317 | 0.0 |
| hcmut_v1 | l1 | 150/150 | 12.0 [7-18] | 9 | 22.7 | 64.9 | 0.659 | 0.520 | 0.547 | 0.167 | 0.167 | 0.165 | 0.0 |
| hcmut_v1 | l1_rerank | 150/150 | 14.0 [8-21] | 11 | 25.2 | 54.9 | 0.756 | 0.630 | 0.653 | 0.237 | 0.237 | 0.235 | 1.3 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 63/22/50/0 | 3/3/9/0 | 53.3 | 20.0 | 12.0 | 20.0 | 44.0 |
| hcmut_v1 | l1 | 31/55/49/0 | 2/4/9/0 | 77.0 | 13.3 | 6.8 | 26.7 | 23.3 |
| hcmut_v1 | l1_rerank | 37/51/45/2 | 1/4/10/0 | 72.2 | 6.7 | 7.3 | 26.7 | 27.3 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | False | PENDING/PENDING | PENDING/PENDING | PENDING | 5794/472 | 2.52 | 0.197 |
| hcmut_v1 | l1 | False | PENDING/PENDING | PENDING/PENDING | PENDING | 6751/593 | 2.80 | 0.144 |
| hcmut_v1 | l1_rerank | False | PENDING/PENDING | PENDING/PENDING | PENDING | 6351/615 | 2.65 | 0.158 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| hcmut_v1 | off | 17.8 (n=15) | 17.8 (n=30) | 20.0 (n=5) |
| hcmut_v1 | l1 | 8.9 (n=15) | 11.1 (n=30) | 26.7 (n=5) |
| hcmut_v1 | l1_rerank | 22.2 (n=15) | 10.0 (n=30) | 13.3 (n=5) |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | hcmut_v1 | 50 | -6.0 [-13.3,+0.7] | -20.7 [-30.7,-10.7] | -1.5 [-9.6,+7.0] | -15.2 [-24.2,-6.5] | +0.0 [+0.0,+0.0] |
| L1+rerank vs L1 | hcmut_v1 | 50 | +2.0 [-5.3,+9.3] | +4.0 [-4.7,+12.7] | +9.6 [-0.7,+20.7] | +6.9 [-1.7,+15.8] | +1.3 [+0.0,+3.3] |
| L1+rerank vs OFF | hcmut_v1 | 50 | -4.0 [-11.3,+3.3] | -16.7 [-26.7,-6.7] | +8.1 [-2.6,+18.5] | -8.3 [-18.1,+1.1] | +1.3 [+0.0,+3.3] |

## Diagnostic baselines (seed 42, no tools; NOT system variants; reference rows are the system variants on answerable tasks only)

| benchmark | row | trials | strict success % (all tasks run) | strict success % (answerable only) [95% CI] | answer rate % | cit P | cit R |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | closed_book (diagnostic baseline) | 50 | 6.0 | 0.0 [0-0] | 11.1 | -- | -- |
| hcmut_v1 | oracle (diagnostic baseline) | 45 | 28.9 | 28.9 [16-42] | 84.4 | 0.822 | 0.811 |
| hcmut_v1 | off (reference) | 135 | -- | 17.8 [10-26] | 46.7 | 0.317 | 0.337 |
| hcmut_v1 | l1 (reference) | 135 | -- | 10.4 [5-16] | 23.0 | 0.167 | 0.167 |
| hcmut_v1 | l1_rerank (reference) | 135 | -- | 14.1 [7-21] | 27.4 | 0.237 | 0.237 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

