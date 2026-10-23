# Results summary - run `bench-smoke-evalimpl-20261023` (smoke, mac-latency)

report_eligible: **False** - Not eligible: smoke/unfrozen run, incomplete collection, trials the judge never attempted, or collection sources changed during a session ([]).

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 3/3 | 0.0 [0-0] | 1 | 50.0 | 50.0 | 0.750 | 1.000 | 0.807 | 0.500 | 0.500 | 0.500 | 0.0 |
| hcmut_v1 | l1 | 3/3 | 33.3 [0-100] | 0 | 33.3 | 0.0 | 0.750 | 1.000 | 0.807 | 0.000 | 0.000 | 0.000 | 0.0 |
| labour_vi_v1 | off | 3/3 | 33.3 [0-100] | 0 | 100.0 | 80.0 | 1.000 | 1.000 | 0.960 | 0.833 | 1.000 | 0.900 | 0.0 |
| labour_vi_v1 | l1 | 3/3 | 33.3 [0-100] | 0 | 66.7 | 50.0 | 1.000 | 1.000 | 0.960 | 0.500 | 0.500 | 0.500 | 0.0 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 1/0/1/0 | 1/0/0/0 | 50.0 | 100.0 | PENDING | 0.0 | 33.3 |
| hcmut_v1 | l1 | 0/1/1/0 | 0/1/0/0 | 100.0 | 0.0 | 50.0 | 100.0 | 33.3 |
| labour_vi_v1 | off | 2/0/0/0 | 0/1/0/0 | 0.0 | 0.0 | 100.0 | 100.0 | 100.0 |
| labour_vi_v1 | l1 | 1/1/0/0 | 0/1/0/0 | 50.0 | 0.0 | 50.0 | 100.0 | 66.7 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | True | 10.9/22.1 | 5.50/15.93 | 40 | 3670/481 | 2.00 | 0.003 |
| hcmut_v1 | l1 | True | 13.2/36.0 | 5.43/18.19 | 37 | 5755/648 | 2.67 | 0.005 |
| labour_vi_v1 | off | True | 12.8/13.7 | 3.42/9.85 | 62 | 5910/525 | 2.67 | 0.009 |
| labour_vi_v1 | l1 | True | 14.5/15.8 | 3.97/7.19 | 59 | 6841/617 | 3.00 | 0.015 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| hcmut_v1 | off | PENDING | 0.0 (n=2) | 0.0 (n=1) |
| hcmut_v1 | l1 | PENDING | 0.0 (n=2) | 100.0 (n=1) |
| labour_vi_v1 | off | 0.0 (n=1) | 0.0 (n=1) | 100.0 (n=1) |
| labour_vi_v1 | l1 | 0.0 (n=1) | 0.0 (n=1) | 100.0 (n=1) |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | hcmut_v1 | 3 | +33.3 [+0.0,+100.0] | +0.0 [-100.0,+100.0] | +0.0 [+0.0,+0.0] | -50.0 [-100.0,+0.0] | +0.0 [+0.0,+0.0] |
| L1 vs OFF | labour_vi_v1 | 3 | +0.0 [+0.0,+0.0] | -33.3 [-100.0,+0.0] | +0.0 [+0.0,+0.0] | -40.0 [-80.0,+0.0] | +0.0 [+0.0,+0.0] |
| L1 vs OFF | pooled | 6 | +16.7 [+0.0,+50.0] | -16.7 [-66.7,+33.3] | +0.0 [+0.0,+0.0] | -45.0 [-90.0,+0.0] | +0.0 [+0.0,+0.0] |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

