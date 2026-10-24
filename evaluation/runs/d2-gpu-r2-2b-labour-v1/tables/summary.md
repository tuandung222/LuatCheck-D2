# Results summary - run `d2-gpu-r2-2b-labour-v1` (main, gpu-accuracy)

report_eligible: **True** - Complete main run; every trial judged, an execution error, or judge-attempted (unknowns listed in coverage and counted as failures). Still LLM-judge estimates; human audit labels pending.

**Post-hoc revision evaluated on the same tasks** (protocol `r2-posthoc`): the revision was designed after the frozen v3 results on these tasks were seen; this is not a pre-planned result.

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | 150/150 | 31.3 [22-41] | 7 | 80.4 | 63.0 | 0.967 | 0.930 | 0.935 | 0.552 | 0.504 | 0.519 | 0.0 |
| labour_vi_v1 | l1 | 150/150 | 28.0 [19-38] | 3 | 62.6 | 69.4 | 0.989 | 0.952 | 0.957 | 0.496 | 0.459 | 0.472 | 0.0 |
| labour_vi_v1 | l1_rerank | 150/150 | 28.0 [19-37] | 6 | 61.8 | 72.5 | 0.993 | 0.958 | 0.963 | 0.559 | 0.515 | 0.528 | 0.7 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | 107/20/8/0 | 4/11/0/0 | 20.7 | 26.7 | 35.5 | 73.3 | 78.7 |
| labour_vi_v1 | l1 | 83/42/10/0 | 1/12/2/0 | 38.5 | 6.7 | 22.2 | 80.0 | 63.3 |
| labour_vi_v1 | l1_rerank | 85/40/9/1 | 1/13/1/0 | 36.6 | 6.7 | 24.5 | 86.7 | 65.3 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | False | PENDING/PENDING | PENDING/PENDING | PENDING | 11403/672 | 3.58 | 0.274 |
| labour_vi_v1 | l1 | False | PENDING/PENDING | PENDING/PENDING | PENDING | 14393/824 | 4.15 | 0.253 |
| labour_vi_v1 | l1_rerank | False | PENDING/PENDING | PENDING/PENDING | PENDING | 13602/834 | 3.98 | 0.235 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| labour_vi_v1 | off | 19.4 (n=12) | 30.3 (n=33) | 66.7 (n=5) |
| labour_vi_v1 | l1 | 27.8 (n=12) | 22.2 (n=33) | 66.7 (n=5) |
| labour_vi_v1 | l1_rerank | 25.0 (n=12) | 26.3 (n=33) | 46.7 (n=5) |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | labour_vi_v1 | 50 | -3.3 [-11.3,+4.7] | -15.3 [-24.7,-6.0] | +2.2 [+0.0,+5.9] | -4.7 [-14.1,+4.7] | +0.0 [+0.0,+0.0] |
| L1+rerank vs L1 | labour_vi_v1 | 50 | -0.0 [-6.0,+6.0] | +2.0 [-6.7,+10.7] | +0.4 [-2.2,+3.3] | +5.7 [-4.9,+15.8] | +0.7 [+0.0,+2.0] |
| L1+rerank vs OFF | labour_vi_v1 | 50 | -3.3 [-12.0,+5.3] | -13.3 [-23.3,-3.3] | +2.6 [+0.0,+5.9] | +1.0 [-11.1,+12.1] | +0.7 [+0.0,+2.0] |

## Diagnostic baselines (seed 42, no tools; NOT system variants; reference rows are the system variants on answerable tasks only)

| benchmark | row | trials | strict success % (all tasks run) | strict success % (answerable only) [95% CI] | answer rate % | cit P | cit R |
|---|---|---|---|---|---|---|---|
| labour_vi_v1 | closed_book (diagnostic baseline) | 50 | 26.0 | 22.2 [11-36] | 33.3 | -- | -- |
| labour_vi_v1 | oracle (diagnostic baseline) | 45 | 48.9 | 48.9 [33-64] | 93.3 | 0.933 | 0.889 |
| labour_vi_v1 | off (reference) | 135 | -- | 27.4 [19-37] | 79.3 | 0.552 | 0.504 |
| labour_vi_v1 | l1 (reference) | 135 | -- | 23.7 [15-33] | 61.5 | 0.496 | 0.459 |
| labour_vi_v1 | l1_rerank (reference) | 135 | -- | 25.9 [16-36] | 63.0 | 0.559 | 0.515 |

## Refusals and clarifications by source (counts: total / expected-answer / expected-refuse)

| benchmark | variant | source | refused | clarified |
|---|---|---|---|---|
| labour_vi_v1 | off | budget | 5 / 4 / 1 | 0 / 0 / 0 |
| labour_vi_v1 | off | model | 26 / 16 / 10 | 0 / 0 / 0 |
| labour_vi_v1 | off | unrecorded | 0 / 0 / 0 | 8 / 8 / 0 |
| labour_vi_v1 | l1 | budget | 12 / 10 / 2 | 0 / 0 / 0 |
| labour_vi_v1 | l1 | model | 25 / 15 / 10 | 0 / 0 / 0 |
| labour_vi_v1 | l1 | repair_exhausted | 17 / 17 / 0 | 0 / 0 / 0 |
| labour_vi_v1 | l1 | unrecorded | 0 / 0 / 0 | 12 / 10 / 2 |
| labour_vi_v1 | l1_rerank | budget | 6 / 3 / 3 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | model | 26 / 17 / 9 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | repair_exhausted | 21 / 20 / 1 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 10 / 9 / 1 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

