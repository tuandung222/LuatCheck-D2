# Results summary - run `mac-check-2task-20261024` (smoke, mac-latency)

report_eligible: **False** - Not eligible: smoke/unfrozen run, incomplete collection, trials the judge never attempted, or collection sources changed during a session ([]).

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 2/2 | 50.0 [0-100] | 0 | 100.0 | 100.0 | 1.000 | 1.000 | 1.000 | 1.000 | 0.750 | 0.833 | 0.0 |
| hcmut_v1 | l1 | 2/2 | 0.0 [0-0] | 0 | 50.0 | 100.0 | 0.750 | 0.750 | 0.693 | 0.250 | 0.250 | 0.250 | 0.0 |
| hcmut_v1 | l1_rerank | 2/2 | 0.0 [0-0] | 0 | 0.0 | 0.0 | 0.750 | 0.375 | 0.409 | 0.000 | 0.000 | 0.000 | 0.0 |
| labour_vi_v1 | off | 2/2 | 0.0 [0-0] | 0 | 100.0 | 40.0 | 1.000 | 1.000 | 0.960 | 0.583 | 1.000 | 0.733 | 0.0 |
| labour_vi_v1 | l1 | 2/2 | 0.0 [0-0] | 0 | 50.0 | 100.0 | 1.000 | 1.000 | 0.960 | 0.500 | 0.500 | 0.500 | 0.0 |
| labour_vi_v1 | l1_rerank | 2/2 | 0.0 [0-0] | 0 | 0.0 | PENDING | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.0 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 2/0/0/0 | 0/0/0/0 | 0.0 | PENDING | PENDING | PENDING | 100.0 |
| hcmut_v1 | l1 | 1/0/1/0 | 0/0/0/0 | 50.0 | PENDING | PENDING | PENDING | 50.0 |
| hcmut_v1 | l1_rerank | 0/1/1/0 | 0/0/0/0 | 100.0 | PENDING | 0.0 | PENDING | 0.0 |
| labour_vi_v1 | off | 2/0/0/0 | 0/0/0/0 | 0.0 | PENDING | PENDING | PENDING | 100.0 |
| labour_vi_v1 | l1 | 1/1/0/0 | 0/0/0/0 | 50.0 | PENDING | 0.0 | PENDING | 50.0 |
| labour_vi_v1 | l1_rerank | 0/2/0/0 | 0/0/0/0 | 100.0 | PENDING | 0.0 | PENDING | 0.0 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | True | 24.8/25.6 | 12.65/20.73 | 37 | 3642/743 | 2.00 | 0.001 |
| hcmut_v1 | l1 | True | 17.6/20.3 | 8.09/15.17 | 34 | 3630/494 | 2.00 | 0.001 |
| hcmut_v1 | l1_rerank | True | 49.1/74.1 | 6.34/15.00 | 37 | 15355/1003 | 4.50 | 0.001 |
| labour_vi_v1 | off | True | 16.7/24.2 | 6.01/17.38 | 59 | 3547/612 | 2.00 | 0.008 |
| labour_vi_v1 | l1 | True | 9.6/11.9 | 3.98/6.06 | 89 | 4944/663 | 2.50 | 0.001 |
| labour_vi_v1 | l1_rerank | True | 14.7/16.0 | 3.08/7.92 | 90 | 6313/839 | 3.00 | 0.000 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| hcmut_v1 | off | PENDING | 50.0 (n=2) | PENDING |
| hcmut_v1 | l1 | PENDING | 0.0 (n=2) | PENDING |
| hcmut_v1 | l1_rerank | PENDING | 0.0 (n=2) | PENDING |
| labour_vi_v1 | off | 0.0 (n=1) | 0.0 (n=1) | PENDING |
| labour_vi_v1 | l1 | 0.0 (n=1) | 0.0 (n=1) | PENDING |
| labour_vi_v1 | l1_rerank | 0.0 (n=1) | 0.0 (n=1) | PENDING |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | hcmut_v1 | 2 | -50.0 [-100.0,+0.0] | -50.0 [-100.0,+0.0] | -25.0 [-50.0,+0.0] | -58.3 [-100.0,-16.7] | +0.0 [+0.0,+0.0] |
| L1 vs OFF | labour_vi_v1 | 2 | +0.0 [+0.0,+0.0] | -50.0 [-100.0,+0.0] | +0.0 [+0.0,+0.0] | -23.3 [-80.0,+33.3] | +0.0 [+0.0,+0.0] |
| L1 vs OFF | pooled | 4 | -25.0 [-75.0,+0.0] | -50.0 [-100.0,+0.0] | -12.5 [-37.5,+0.0] | -40.8 [-90.0,+8.3] | +0.0 [+0.0,+0.0] |
| L1+rerank vs L1 | hcmut_v1 | 2 | +0.0 [+0.0,+0.0] | -50.0 [-100.0,+0.0] | +0.0 [+0.0,+0.0] | -25.0 [-50.0,+0.0] | +0.0 [+0.0,+0.0] |
| L1+rerank vs L1 | labour_vi_v1 | 2 | +0.0 [+0.0,+0.0] | -50.0 [-100.0,+0.0] | +0.0 [+0.0,+0.0] | -50.0 [-100.0,+0.0] | +0.0 [+0.0,+0.0] |
| L1+rerank vs L1 | pooled | 4 | +0.0 [+0.0,+0.0] | -50.0 [-100.0,+0.0] | +0.0 [+0.0,+0.0] | -37.5 [-75.0,+0.0] | +0.0 [+0.0,+0.0] |
| L1+rerank vs OFF | hcmut_v1 | 2 | -50.0 [-100.0,+0.0] | -100.0 [-100.0,-100.0] | -25.0 [-50.0,+0.0] | -83.3 [-100.0,-66.7] | +0.0 [+0.0,+0.0] |
| L1+rerank vs OFF | labour_vi_v1 | 2 | +0.0 [+0.0,+0.0] | -100.0 [-100.0,-100.0] | +0.0 [+0.0,+0.0] | -73.3 [-80.0,-66.7] | +0.0 [+0.0,+0.0] |
| L1+rerank vs OFF | pooled | 4 | -25.0 [-75.0,+0.0] | -100.0 [-100.0,-100.0] | -12.5 [-37.5,+0.0] | -78.3 [-91.7,-66.7] | +0.0 [+0.0,+0.0] |

## Diagnostic baselines (seed 42, no tools; NOT system variants; reference rows are the system variants on answerable tasks only)

| benchmark | row | trials | strict success % (all tasks run) | strict success % (answerable only) [95% CI] | answer rate % | cit P | cit R |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | closed_book (diagnostic baseline) | 2 | 0.0 | 0.0 [0-0] | 0.0 | -- | -- |
| hcmut_v1 | oracle (diagnostic baseline) | 2 | 50.0 | 50.0 [0-100] | 100.0 | 1.000 | 1.000 |
| hcmut_v1 | off (reference) | 2 | -- | 50.0 [0-100] | 100.0 | 1.000 | 0.750 |
| hcmut_v1 | l1 (reference) | 2 | -- | 0.0 [0-0] | 50.0 | 0.250 | 0.250 |
| hcmut_v1 | l1_rerank (reference) | 2 | -- | 0.0 [0-0] | 0.0 | 0.000 | 0.000 |
| labour_vi_v1 | closed_book (diagnostic baseline) | 2 | 0.0 | 0.0 [0-0] | 100.0 | -- | -- |
| labour_vi_v1 | oracle (diagnostic baseline) | 2 | 100.0 | 100.0 [100-100] | 100.0 | 1.000 | 1.000 |
| labour_vi_v1 | off (reference) | 2 | -- | 0.0 [0-0] | 100.0 | 0.583 | 1.000 |
| labour_vi_v1 | l1 (reference) | 2 | -- | 0.0 [0-0] | 50.0 | 0.500 | 0.500 |
| labour_vi_v1 | l1_rerank (reference) | 2 | -- | 0.0 [0-0] | 0.0 | 0.000 | 0.000 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

