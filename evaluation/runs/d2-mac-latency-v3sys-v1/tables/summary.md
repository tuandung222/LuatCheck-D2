# Results summary - run `d2-mac-latency-v3sys-v1` (main, mac-latency)

report_eligible: **False** - Not eligible: smoke/unfrozen run, incomplete collection, trials the judge never attempted, or collection sources changed during a session ([]).

LLM-judge estimates (success, behaviour, faithfulness) are not human labels. Retrieval and citation numbers are source-ID proxies. Execution errors count as failures in strict success and are reported separately.

| benchmark | variant | trials | strict success % [95% CI] | unknown | judge behav % | faithfulness % | R@5 | MRR | nDCG@5 | cit P | cit R | cit F1 | err % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 50/50 | 0.0 [0-0] | 50 | PENDING | PENDING | 0.700 | 0.648 | 0.647 | 0.393 | 0.389 | 0.388 | 0.0 |
| hcmut_v1 | l1 | 50/50 | 0.0 [0-0] | 50 | PENDING | PENDING | 0.700 | 0.648 | 0.647 | 0.244 | 0.233 | 0.237 | 0.0 |
| hcmut_v1 | l1_rerank | 50/50 | 0.0 [0-0] | 50 | PENDING | PENDING | 0.744 | 0.669 | 0.677 | 0.133 | 0.122 | 0.126 | 0.0 |
| labour_vi_v1 | off | 50/50 | 0.0 [0-0] | 49 | 0.0 | PENDING | 0.633 | 0.556 | 0.561 | 0.359 | 0.367 | 0.359 | 2.0 |
| labour_vi_v1 | l1 | 50/50 | 0.0 [0-0] | 49 | 0.0 | PENDING | 0.656 | 0.561 | 0.571 | 0.178 | 0.178 | 0.178 | 2.0 |
| labour_vi_v1 | l1_rerank | 50/50 | 0.0 [0-0] | 50 | PENDING | PENDING | 0.800 | 0.635 | 0.674 | 0.289 | 0.233 | 0.252 | 0.0 |

## Behaviour (structural, no judge)

| benchmark | variant | E=answer A/R/C/Err | E=refuse A/R/C/Err | over-refusal % | unsafe answer % | refusal P % | refusal R % | strict match % |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 24/6/15/0 | 3/1/1/0 | 46.7 | 60.0 | 14.3 | 20.0 | 50.0 |
| hcmut_v1 | l1 | 11/18/16/0 | 1/2/2/0 | 75.6 | 20.0 | 10.0 | 40.0 | 26.0 |
| hcmut_v1 | l1_rerank | 8/20/17/0 | 0/4/1/0 | 82.2 | 0.0 | 16.7 | 80.0 | 24.0 |
| labour_vi_v1 | off | 27/4/13/1 | 2/2/1/0 | 38.6 | 40.0 | 33.3 | 40.0 | 58.0 |
| labour_vi_v1 | l1 | 10/16/18/1 | 1/3/1/0 | 77.3 | 20.0 | 15.8 | 60.0 | 26.0 |
| labour_vi_v1 | l1_rerank | 14/16/15/0 | 0/2/3/0 | 68.9 | 0.0 | 11.1 | 40.0 | 32.0 |

## Operations

| benchmark | variant | reportable latency | trial p50/p95 s | call p50/p95 s | decode tok/s | tokens in/out per trial | calls/trial | judge USD |
|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | True | 7.1/16.0 | 2.52/8.79 | 94 | 5336/490 | 2.36 | 0.000 |
| hcmut_v1 | l1 | True | 8.1/19.6 | 3.00/8.65 | 94 | 7118/661 | 2.82 | 0.000 |
| hcmut_v1 | l1_rerank | True | 12.0/28.6 | 2.95/8.61 | 94 | 6938/646 | 2.78 | 0.000 |
| labour_vi_v1 | off | True | 7.8/15.1 | 2.68/6.05 | 95 | 5880/550 | 2.64 | 0.000 |
| labour_vi_v1 | l1 | True | 9.5/19.2 | 2.79/6.19 | 94 | 7585/706 | 3.16 | 0.000 |
| labour_vi_v1 | l1_rerank | True | 12.8/22.5 | 2.81/7.22 | 95 | 6915/705 | 3.02 | 0.000 |

## Strict success by closed-book stratum (LLM-estimated strata; lower bound)

| benchmark | variant | guessable (n tasks) | not guessable (n tasks) | refusal tasks (n tasks) |
|---|---|---|---|---|
| hcmut_v1 | off | 0.0 (n=15) | 0.0 (n=30) | 0.0 (n=5) |
| hcmut_v1 | l1 | 0.0 (n=15) | 0.0 (n=30) | 0.0 (n=5) |
| hcmut_v1 | l1_rerank | 0.0 (n=15) | 0.0 (n=30) | 0.0 (n=5) |
| labour_vi_v1 | off | 0.0 (n=12) | 0.0 (n=33) | 0.0 (n=5) |
| labour_vi_v1 | l1 | 0.0 (n=12) | 0.0 (n=33) | 0.0 (n=5) |
| labour_vi_v1 | l1_rerank | 0.0 (n=12) | 0.0 (n=33) | 0.0 (n=5) |

## Paired differences (treatment - baseline, pp; 95% paired bootstrap over tasks)

| comparison | scope | tasks | d strict success | d behaviour match | d R@5 | d cit F1 | d error rate |
|---|---|---|---|---|---|---|---|
| L1 vs OFF | hcmut_v1 | 50 | +0.0 [+0.0,+0.0] | -24.0 [-38.0,-12.0] | +0.0 [+0.0,+0.0] | -15.1 [-26.2,-6.2] | +0.0 [+0.0,+0.0] |
| L1 vs OFF | labour_vi_v1 | 50 | +0.0 [+0.0,+0.0] | -32.0 [-46.0,-18.0] | +2.2 [+0.0,+6.7] | -18.1 [-29.2,-8.0] | +0.0 [+0.0,+0.0] |
| L1 vs OFF | pooled | 100 | +0.0 [+0.0,+0.0] | -28.0 [-38.0,-18.0] | +1.1 [+0.0,+3.3] | -16.6 [-24.4,-9.4] | +0.0 [+0.0,+0.0] |
| L1+rerank vs L1 | hcmut_v1 | 50 | +0.0 [+0.0,+0.0] | -2.0 [-16.0,+12.0] | +4.4 [-6.7,+15.6] | -11.1 [-24.4,+2.2] | +0.0 [+0.0,+0.0] |
| L1+rerank vs L1 | labour_vi_v1 | 50 | +0.0 [+0.0,+0.0] | +6.0 [-10.0,+22.0] | +14.4 [+0.0,+30.0] | +7.4 [-5.2,+20.0] | -2.0 [-6.0,+0.0] |
| L1+rerank vs L1 | pooled | 100 | +0.0 [+0.0,+0.0] | +2.0 [-9.0,+13.0] | +9.4 [+0.0,+18.9] | -1.9 [-11.9,+7.4] | -1.0 [-3.0,+0.0] |
| L1+rerank vs OFF | hcmut_v1 | 50 | +0.0 [+0.0,+0.0] | -26.0 [-44.0,-6.0] | +4.4 [-6.7,+15.6] | -26.2 [-42.2,-10.7] | +0.0 [+0.0,+0.0] |
| L1+rerank vs OFF | labour_vi_v1 | 50 | +0.0 [+0.0,+0.0] | -26.0 [-44.0,-8.0] | +16.7 [+3.3,+31.1] | -10.7 [-26.7,+4.6] | -2.0 [-6.0,+0.0] |
| L1+rerank vs OFF | pooled | 100 | +0.0 [+0.0,+0.0] | -26.0 [-39.0,-13.0] | +10.6 [+1.7,+19.4] | -18.4 [-30.2,-7.0] | -1.0 [-3.0,+0.0] |

## Refusals and clarifications by source (counts: total / expected-answer / expected-refuse)

| benchmark | variant | source | refused | clarified |
|---|---|---|---|---|
| hcmut_v1 | off | model | 7 / 6 / 1 | 0 / 0 / 0 |
| hcmut_v1 | off | unrecorded | 0 / 0 / 0 | 16 / 15 / 1 |
| hcmut_v1 | l1 | model | 16 / 14 / 2 | 0 / 0 / 0 |
| hcmut_v1 | l1 | repair_exhausted | 4 / 4 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1 | unrecorded | 0 / 0 / 0 | 18 / 16 / 2 |
| hcmut_v1 | l1_rerank | model | 22 / 18 / 4 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | repair_exhausted | 2 / 2 / 0 | 0 / 0 / 0 |
| hcmut_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 18 / 17 / 1 |
| labour_vi_v1 | off | model | 6 / 4 / 2 | 0 / 0 / 0 |
| labour_vi_v1 | off | unrecorded | 0 / 0 / 0 | 14 / 13 / 1 |
| labour_vi_v1 | l1 | budget | 1 / 1 / 0 | 0 / 0 / 0 |
| labour_vi_v1 | l1 | model | 17 / 14 / 3 | 0 / 0 / 0 |
| labour_vi_v1 | l1 | repair_exhausted | 1 / 1 / 0 | 0 / 0 / 0 |
| labour_vi_v1 | l1 | unrecorded | 0 / 0 / 0 | 19 / 18 / 1 |
| labour_vi_v1 | l1_rerank | model | 17 / 15 / 2 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | repair_exhausted | 1 / 1 / 0 | 0 / 0 / 0 |
| labour_vi_v1 | l1_rerank | unrecorded | 0 / 0 / 0 | 18 / 15 / 3 |

## Judge reliability

Human audit labels: PENDING (agreement and kappa are not computed without real labels).

