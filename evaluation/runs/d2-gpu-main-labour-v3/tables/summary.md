# Results summary - run `d2-gpu-main-labour-v3` (main, gpu-accuracy)

report_eligible: **True** - Complete main run; every trial judged, an execution error, or judge-attempted (unknowns listed in coverage and counted as failures). Still LLM-judge estimates; human audit labels pending.

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | 150/150 | 14.7 [7-23] | 2 | 56.1 | 53.9 | 0.607 | 0.547 | 0.543 | 0.358 | 0.374 | 0.358 | 0.7 |
| labour_vi_v1 | l1 | 150/150 | 14.7 [7-23] | 8 | 40.1 | 62.6 | 0.659 | 0.581 | 0.584 | 0.277 | 0.256 | 0.258 | 0.0 |
| labour_vi_v1 | l1_rerank | 150/150 | 18.7 [11-27] | 12 | 39.1 | 61.4 | 0.815 | 0.685 | 0.704 | 0.296 | 0.289 | 0.289 | 0.7 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | 88/6/40/1 | 3/3/9/0 | 34.3 | 20.0 | 33.3 | 20.0 | 60.7 |
| labour_vi_v1 | l1 | 51/39/45/0 | 1/6/8/0 | 62.2 | 6.7 | 13.3 | 40.0 | 38.0 |
| labour_vi_v1 | l1_rerank | 49/51/34/1 | 0/5/10/0 | 63.4 | 0.0 | 8.9 | 33.3 | 36.0 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| labour_vi_v1 | off | False | PENDING/PENDING | PENDING/PENDING | PENDING | 5945/545 | 2.67 | 0.215 |
| labour_vi_v1 | l1 | False | PENDING/PENDING | PENDING/PENDING | PENDING | 7539/667 | 3.13 | 0.142 |
| labour_vi_v1 | l1_rerank | False | PENDING/PENDING | PENDING/PENDING | PENDING | 7542/735 | 3.17 | 0.143 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| labour_vi_v1 | off | 16.7 (n=12) | 13.1 (n=33) | 20.0 (n=5) |
| labour_vi_v1 | l1 | 5.6 (n=12) | 14.1 (n=33) | 40.0 (n=5) |
| labour_vi_v1 | l1_rerank | 16.7 (n=12) | 16.2 (n=33) | 40.0 (n=5) |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | labour_vi_v1 | 50 | -0.0 [-6.7,+6.7] | -22.7 [-33.3,-12.0] | +5.2 [-0.7,+11.9] | -10.0 [-17.7,-2.6] | -0.7 [-2.0,+0.0] |
| L1 vs OFF | pooled | 50 | -0.0 [-6.7,+6.7] | -22.7 [-33.3,-12.0] | +5.2 [-0.7,+11.9] | -10.0 [-17.7,-2.6] | -0.7 [-2.0,+0.0] |
| L1+rerank vs L1 | labour_vi_v1 | 50 | +4.0 [-5.3,+13.3] | -2.0 [-12.7,+8.7] | +15.6 [+3.0,+28.9] | +3.1 [-6.5,+13.3] | +0.7 [+0.0,+2.0] |
| L1+rerank vs L1 | pooled | 50 | +4.0 [-5.3,+13.3] | -2.0 [-12.7,+8.7] | +15.6 [+3.0,+28.9] | +3.1 [-6.5,+13.3] | +0.7 [+0.0,+2.0] |
| L1+rerank vs OFF | labour_vi_v1 | 50 | +4.0 [-4.0,+12.0] | -24.7 [-36.0,-14.0] | +20.7 [+6.7,+35.2] | -6.9 [-19.9,+5.7] | +0.0 [-2.0,+2.0] |
| L1+rerank vs OFF | pooled | 50 | +4.0 [-4.0,+12.0] | -24.7 [-36.0,-14.0] | +20.7 [+6.7,+35.2] | -6.9 [-19.9,+5.7] | +0.0 [-2.0,+2.0] |

## Diagnostic baselines (seed 42, no tools; NOT system variants; reference rows are the system variants on answerable tasks only)

| benchmark | row | trials | strict success % (all tasks run) | strict success % (answerable only) [95% CI] | answer rate % | cit P | cit R |
|---|---|---|---|---|---|---|---|
| labour_vi_v1 | closed_book (diagnostic baseline) | 50 | 14.0 | 13.3 [4-24] | 48.9 | -- | -- |
| labour_vi_v1 | oracle (diagnostic baseline) | 45 | 44.4 | 44.4 [31-58] | 84.4 | 0.844 | 0.811 |
| labour_vi_v1 | off (reference) | 135 | -- | 14.1 [7-23] | 65.2 | 0.358 | 0.374 |
| labour_vi_v1 | l1 (reference) | 135 | -- | 11.9 [5-20] | 37.8 | 0.277 | 0.256 |
| labour_vi_v1 | l1_rerank (reference) | 135 | -- | 16.3 [9-24] | 36.3 | 0.296 | 0.289 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

