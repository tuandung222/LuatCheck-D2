# Comparison of systems on the same tasks

Generated 2026-10-24T19:19:18.032445+07:00 by `python evaluation/run_d2.py compare --arm 'v3-2B=d2-gpu-main-hcmut-v3,d2-gpu-main-labour-v3' --arm 'r2-2B=d2-gpu-r2-2b-hcmut-v1,d2-gpu-r2-2b-labour-v1' --arm 'r2-4B=d2-gpu-r2-4b-hcmut-v1,d2-gpu-r2-4b-labour-v1'` (harness `1.2.0`). Paired task-level bootstrap (5000 draws, seed 20261023, unit: task (seeds averaged)); differences are B - A as defined below; intervals are descriptive, no multiple-comparison correction.

**Arm(s) r2-2B, r2-4B: post-hoc revision evaluated on the same tasks (the revision was designed after the v3-2B results were seen; it is not a pre-planned result).**

## Arms

| arm | benchmark | run | controller | commit | harness | freshness | protocol | judge |
|---|---|---|---|---|---|---|---|---|
| v3-2B | hcmut_v1 | d2-gpu-main-hcmut-v3 | prism-ml/Ternary-Bonsai-2-2B-gguf | 957579b | 1.1.2 | pinned@957579b | frozen v3 protocol | deepseek/deepseek-v4-flash |
| v3-2B | labour_vi_v1 | d2-gpu-main-labour-v3 | prism-ml/Ternary-Bonsai-2-2B-gguf | 957579b | 1.1.2 | pinned@957579b | frozen v3 protocol | deepseek/deepseek-v4-flash |
| r2-2B | hcmut_v1 | d2-gpu-r2-2b-hcmut-v1 | prism-ml/Ternary-Bonsai-2-2B-gguf | cdb6b24 | 1.2.0 | current | r2-posthoc | deepseek/deepseek-v4-flash |
| r2-2B | labour_vi_v1 | d2-gpu-r2-2b-labour-v1 | prism-ml/Ternary-Bonsai-2-2B-gguf | cdb6b24 | 1.2.0 | current | r2-posthoc | deepseek/deepseek-v4-flash |
| r2-4B | hcmut_v1 | d2-gpu-r2-4b-hcmut-v1 | prism-ml/Ternary-Bonsai-2-4B-gguf | cdb6b24 | 1.2.0 | current | r2-posthoc | deepseek/deepseek-v4-flash |
| r2-4B | labour_vi_v1 | d2-gpu-r2-4b-labour-v1 | prism-ml/Ternary-Bonsai-2-4B-gguf | cdb6b24 | 1.2.0 | current | r2-posthoc | deepseek/deepseek-v4-flash |

## Contrasts

- **system effect** = r2-2B - v3-2B
- **model effect** = r2-4B - r2-2B


Metrics: Strict success: LLM-judge estimate, lower bound over all planned trials (error / unknown / missing = failure); not human labels; Behaviour match: structural: expected answer -> answered, expected refuse -> refused (clarified counts as a miss); no judge; Recall@5: gold-id retrieval over the agent's search+read trace, answerable tasks; not answer correctness; Answer rate: share of trials whose terminal status is answered; Execution-error rate: share of trials that are execution errors

## Strict success (%, differences in pp)

| benchmark | variant | tasks | v3-2B | r2-2B | r2-4B | system effect | model effect |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 50 | 18.0 [11-26] | 31.3 [22-41] | 70.0 [61-79] | +13.3 [+4.0, +22.7] | +38.7 [+27.3, +50.0] |
| hcmut_v1 | l1 | 50 | 12.0 [7-18] | 24.0 [15-33] | 64.0 [53-75] | +12.0 [+4.0, +20.7] | +40.0 [+28.7, +51.3] |
| hcmut_v1 | l1_rerank | 50 | 14.0 [8-21] | 28.7 [20-37] | 60.7 [50-71] | +14.7 [+6.0, +23.3] | +32.0 [+21.3, +42.0] |
| labour_vi_v1 | off | 50 | 14.7 [7-23] | 31.3 [22-41] | 62.0 [52-72] | +16.7 [+7.3, +25.3] | +30.7 [+20.7, +40.7] |
| labour_vi_v1 | l1 | 50 | 14.7 [7-23] | 28.0 [19-38] | 52.7 [43-63] | +13.3 [+4.0, +22.7] | +24.7 [+12.0, +37.3] |
| labour_vi_v1 | l1_rerank | 50 | 18.7 [11-27] | 28.0 [19-37] | 56.7 [47-67] | +9.3 [+0.7, +18.0] | +28.7 [+18.0, +39.3] |

## Behaviour match (%, differences in pp)

| benchmark | variant | tasks | v3-2B | r2-2B | r2-4B | system effect | model effect |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 50 | 44.0 | 58.0 | 88.0 | +14.0 [+2.0, +26.0] | +30.0 [+18.7, +42.0] |
| hcmut_v1 | l1 | 50 | 23.3 | 45.3 | 82.7 | +22.0 [+12.7, +32.0] | +37.3 [+27.3, +47.3] |
| hcmut_v1 | l1_rerank | 50 | 27.3 | 46.7 | 80.0 | +19.3 [+8.0, +30.7] | +33.3 [+22.0, +44.7] |
| labour_vi_v1 | off | 50 | 60.7 | 78.7 | 94.0 | +18.0 [+8.0, +27.3] | +15.3 [+7.3, +23.3] |
| labour_vi_v1 | l1 | 50 | 38.0 | 63.3 | 81.3 | +25.3 [+15.3, +35.3] | +18.0 [+9.3, +26.0] |
| labour_vi_v1 | l1_rerank | 50 | 36.0 | 65.3 | 79.3 | +29.3 [+20.7, +38.7] | +14.0 [+4.7, +23.3] |

## Recall@5 (differences absolute)

| benchmark | variant | tasks | v3-2B | r2-2B | r2-4B | system effect | model effect |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 50 | 0.674 | 0.856 | 0.989 | +0.181 [+0.085, +0.278] | +0.133 [+0.063, +0.207] |
| hcmut_v1 | l1 | 50 | 0.659 | 0.859 | 0.989 | +0.200 [+0.122, +0.278] | +0.130 [+0.067, +0.200] |
| hcmut_v1 | l1_rerank | 50 | 0.756 | 0.844 | 0.978 | +0.089 [-0.022, +0.200] | +0.133 [+0.063, +0.211] |
| labour_vi_v1 | off | 50 | 0.607 | 0.967 | 0.989 | +0.359 [+0.237, +0.481] | +0.022 [+0.000, +0.059] |
| labour_vi_v1 | l1 | 50 | 0.659 | 0.989 | 0.989 | +0.330 [+0.222, +0.444] | +0.000 [+0.000, +0.000] |
| labour_vi_v1 | l1_rerank | 50 | 0.815 | 0.993 | 0.993 | +0.178 [+0.093, +0.270] | +0.000 [-0.022, +0.022] |

## Answer rate (%, differences in pp)

| benchmark | variant | tasks | v3-2B | r2-2B | r2-4B | system effect | model effect |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 50 | 44.0 | 55.3 | 80.7 | +11.3 [-0.7, +23.3] | +25.3 [+13.3, +38.0] |
| hcmut_v1 | l1 | 50 | 22.0 | 41.3 | 72.7 | +19.3 [+9.3, +28.7] | +31.3 [+20.7, +42.0] |
| hcmut_v1 | l1_rerank | 50 | 25.3 | 42.0 | 72.7 | +16.7 [+6.0, +27.3] | +30.7 [+19.3, +42.0] |
| labour_vi_v1 | off | 50 | 60.7 | 74.0 | 88.0 | +13.3 [+4.7, +22.0] | +14.0 [+5.3, +22.0] |
| labour_vi_v1 | l1 | 50 | 34.7 | 56.0 | 74.0 | +21.3 [+11.3, +31.3] | +18.0 [+9.3, +26.0] |
| labour_vi_v1 | l1_rerank | 50 | 32.7 | 57.3 | 72.0 | +24.7 [+16.0, +34.0] | +14.7 [+5.3, +24.0] |

## Execution-error rate (%, differences in pp)

| benchmark | variant | tasks | v3-2B | r2-2B | r2-4B | system effect | model effect |
|---|---|---|---|---|---|---|---|
| hcmut_v1 | off | 50 | 0.0 | 0.0 | 2.0 | +0.0 [+0.0, +0.0] | +2.0 [+0.0, +5.3] |
| hcmut_v1 | l1 | 50 | 0.0 | 0.0 | 2.0 | +0.0 [+0.0, +0.0] | +2.0 [+0.0, +4.7] |
| hcmut_v1 | l1_rerank | 50 | 1.3 | 0.7 | 2.0 | -0.7 [-2.7, +1.3] | +1.3 [+0.0, +3.3] |
| labour_vi_v1 | off | 50 | 0.7 | 0.0 | 0.0 | -0.7 [-2.0, +0.0] | +0.0 [+0.0, +0.0] |
| labour_vi_v1 | l1 | 50 | 0.0 | 0.0 | 2.7 | +0.0 [+0.0, +0.0] | +2.7 [+0.7, +5.3] |
| labour_vi_v1 | l1_rerank | 50 | 0.7 | 0.7 | 2.7 | +0.0 [-2.0, +2.0] | +2.0 [+0.0, +4.7] |

