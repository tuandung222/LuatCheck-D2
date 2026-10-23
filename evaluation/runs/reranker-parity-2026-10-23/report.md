# Reranker runtime parity report

Generated 2026-10-24 00:01:52 +07 (UTC+0700); reference runtimes: `torch_fp32_cpu` (no chunking) and `torch_fp32_cpu_chunk` (chunking); each run is compared with the reference of its own input policy; top_k_in = 20 candidates per question.

## Parity vs reference (per-query statistics over both benchmarks)

| runtime | policy | queries | Spearman mean | Spearman min | top-1 agree | top-3 set agree | top-3 ordered agree | max abs diff | mean abs diff |
|---|---|---|---|---|---|---|---|---|---|
| gguf_f16_chunk | chunk | 100 | 0.99940 | 0.99549 | 0.990 | 1.000 | 0.990 | 0.0944 | 0.00769 |
| gguf_f16_nochunk | nochunk | 100 | 0.99856 | 0.92632 | 1.000 | 0.990 | 0.990 | 0.0944 | 0.00741 |
| gguf_f32_chunk | chunk | 100 | 0.99932 | 0.99511 | 0.990 | 0.990 | 0.980 | 0.0972 | 0.00778 |
| gguf_f32_nochunk | nochunk | 100 | 0.99854 | 0.92632 | 1.000 | 0.990 | 0.990 | 0.0972 | 0.00745 |
| gguf_q8_0_chunk | chunk | 100 | 0.99806 | 0.97444 | 0.990 | 0.980 | 0.960 | 0.3088 | 0.03062 |
| gguf_q8_0_nochunk | nochunk | 100 | 0.99776 | 0.96090 | 1.000 | 0.960 | 0.940 | 0.2652 | 0.02910 |
| h100_fp16_bs16_chunk | chunk | 100 | 0.99073 | 0.88598 | 1.000 | 0.990 | 0.990 | 0.0364 | 0.00348 |
| h100_fp16_bs16_nochunk | nochunk | 100 | 0.98621 | 0.87033 | 1.000 | 0.990 | 0.990 | 0.0364 | 0.00329 |
| h100_fp16_bs1_chunk | chunk | 100 | 0.99427 | 0.96011 | 1.000 | 0.990 | 0.990 | 0.0340 | 0.00325 |
| h100_fp32_bs1_chunk | chunk | 100 | 1.00000 | 0.99962 | 1.000 | 1.000 | 1.000 | 0.0004 | 0.00000 |
| h100_fp32_bs1_nochunk | nochunk | 100 | 1.00000 | 1.00000 | 1.000 | 1.000 | 1.000 | 0.0004 | 0.00000 |
| torch_fp32_cpu | nochunk | 100 | 1.00000 | 1.00000 | 1.000 | 1.000 | 1.000 | 0.0000 | 0.00000 |
| torch_fp32_cpu_chunk | chunk | 100 | 1.00000 | 1.00000 | 1.000 | 1.000 | 1.000 | 0.0000 | 0.00000 |

## Rank metrics vs gold article ids (answerable questions only; not answer correctness)

| benchmark | system | n | MRR | Recall@1 | Recall@3 | Recall@5 | Hit@1 | Hit@3 | gold absent from candidates |
|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1 | first stage (retrieval order) | 45 | 0.952 | 0.856 | 0.967 | 0.989 | 0.911 | 1.000 | 0 |
| hcmut_v1 | gguf_f16_chunk | 45 | 0.944 | 0.833 | 0.978 | 0.978 | 0.889 | 1.000 | 0 |
| hcmut_v1 | gguf_f16_nochunk | 45 | 0.889 | 0.778 | 0.922 | 0.956 | 0.822 | 0.956 | 0 |
| hcmut_v1 | gguf_f32_chunk | 45 | 0.944 | 0.833 | 0.978 | 0.978 | 0.889 | 1.000 | 0 |
| hcmut_v1 | gguf_f32_nochunk | 45 | 0.889 | 0.778 | 0.922 | 0.956 | 0.822 | 0.956 | 0 |
| hcmut_v1 | gguf_q8_0_chunk | 45 | 0.933 | 0.811 | 0.978 | 0.978 | 0.867 | 1.000 | 0 |
| hcmut_v1 | gguf_q8_0_nochunk | 45 | 0.887 | 0.778 | 0.900 | 0.956 | 0.822 | 0.933 | 0 |
| hcmut_v1 | h100_fp16_bs16_chunk | 45 | 0.933 | 0.811 | 0.978 | 0.978 | 0.867 | 1.000 | 0 |
| hcmut_v1 | h100_fp16_bs16_nochunk | 45 | 0.889 | 0.778 | 0.922 | 0.956 | 0.822 | 0.956 | 0 |
| hcmut_v1 | h100_fp16_bs1_chunk | 45 | 0.933 | 0.811 | 0.978 | 0.978 | 0.867 | 1.000 | 0 |
| hcmut_v1 | h100_fp32_bs1_chunk | 45 | 0.933 | 0.811 | 0.978 | 0.978 | 0.867 | 1.000 | 0 |
| hcmut_v1 | h100_fp32_bs1_nochunk | 45 | 0.889 | 0.778 | 0.922 | 0.956 | 0.822 | 0.956 | 0 |
| hcmut_v1 | torch_fp32_cpu | 45 | 0.889 | 0.778 | 0.922 | 0.956 | 0.822 | 0.956 | 0 |
| hcmut_v1 | torch_fp32_cpu_chunk | 45 | 0.933 | 0.811 | 0.978 | 0.978 | 0.867 | 1.000 | 0 |
| labour_vi_v1 | first stage (retrieval order) | 45 | 0.952 | 0.844 | 0.978 | 0.989 | 0.911 | 1.000 | 0 |
| labour_vi_v1 | gguf_f16_chunk | 45 | 0.967 | 0.856 | 0.978 | 1.000 | 0.933 | 1.000 | 0 |
| labour_vi_v1 | gguf_f16_nochunk | 45 | 0.978 | 0.878 | 0.978 | 1.000 | 0.956 | 1.000 | 0 |
| labour_vi_v1 | gguf_f32_chunk | 45 | 0.967 | 0.856 | 0.978 | 1.000 | 0.933 | 1.000 | 0 |
| labour_vi_v1 | gguf_f32_nochunk | 45 | 0.978 | 0.878 | 0.978 | 1.000 | 0.956 | 1.000 | 0 |
| labour_vi_v1 | gguf_q8_0_chunk | 45 | 0.967 | 0.856 | 0.978 | 1.000 | 0.933 | 1.000 | 0 |
| labour_vi_v1 | gguf_q8_0_nochunk | 45 | 0.978 | 0.878 | 0.978 | 1.000 | 0.956 | 1.000 | 0 |
| labour_vi_v1 | h100_fp16_bs16_chunk | 45 | 0.967 | 0.856 | 0.978 | 1.000 | 0.933 | 1.000 | 0 |
| labour_vi_v1 | h100_fp16_bs16_nochunk | 45 | 0.978 | 0.878 | 0.978 | 1.000 | 0.956 | 1.000 | 0 |
| labour_vi_v1 | h100_fp16_bs1_chunk | 45 | 0.967 | 0.856 | 0.978 | 1.000 | 0.933 | 1.000 | 0 |
| labour_vi_v1 | h100_fp32_bs1_chunk | 45 | 0.967 | 0.856 | 0.978 | 1.000 | 0.933 | 1.000 | 0 |
| labour_vi_v1 | h100_fp32_bs1_nochunk | 45 | 0.978 | 0.878 | 0.978 | 1.000 | 0.956 | 1.000 | 0 |
| labour_vi_v1 | torch_fp32_cpu | 45 | 0.978 | 0.878 | 0.978 | 1.000 | 0.956 | 1.000 | 0 |
| labour_vi_v1 | torch_fp32_cpu_chunk | 45 | 0.967 | 0.856 | 0.978 | 1.000 | 0.933 | 1.000 | 0 |

## Runtime vs runtime (no reference involved)

| A : B | policies | queries | Spearman mean | Spearman min | top-1 agree | top-3 set agree | top-3 ordered agree | max abs diff | mean abs diff |
|---|---|---|---|---|---|---|---|---|---|
| gguf_f16_chunk:h100_fp16_bs1_chunk | chunk/chunk | 100 | 0.99409 | 0.96011 | 0.990 | 0.990 | 0.980 | 0.1264 | 0.00777 |
| gguf_q8_0_chunk:h100_fp16_bs1_chunk | chunk/chunk | 100 | 0.99349 | 0.96011 | 0.990 | 0.990 | 0.970 | 0.3078 | 0.03006 |
| gguf_f16_chunk:h100_fp16_bs16_chunk | chunk/chunk | 100 | 0.99059 | 0.88598 | 0.990 | 0.990 | 0.980 | 0.1186 | 0.00845 |
| gguf_f16_chunk:gguf_q8_0_chunk | chunk/chunk | 100 | 0.99835 | 0.98195 | 0.980 | 0.980 | 0.950 | 0.2849 | 0.02768 |

## Tasks whose gold evidence starts beyond the first 3000 characters of its record

Gold article rank among the candidates (1 = best; `-` = not in the candidate set). Multi-gold tasks list ranks in gold order.

| task | evidence (record, char offset, record length) | first_stage | gguf_f16_chunk | gguf_f16_nochunk | gguf_f32_chunk | gguf_f32_nochunk | gguf_q8_0_chunk | gguf_q8_0_nochunk | h100_fp16_bs16_chunk | h100_fp16_bs16_nochunk | h100_fp16_bs1_chunk | h100_fp32_bs1_chunk | h100_fp32_bs1_nochunk | torch_fp32_cpu | torch_fp32_cpu_chunk |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hcmut_v1/HCMUT-005 | HCMUT_HVDT2749_PhuLuc_1 @6402/8032; HCMUT_HVDT2749_PhuLuc_1 @6577/8032 | 1 | 2 | 5 | 2 | 5 | 2 | 5 | 2 | 5 | 2 | 2 | 5 | 5 | 2 |
| hcmut_v1/HCMUT-006 | HCMUT_HVDT2749_PhuLuc_1 @5756/8032 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| hcmut_v1/HCMUT-007 | HCMUT_HVDT2749_PhuLuc_1 @3791/8032 | 1 | 2 | 3 | 2 | 3 | 2 | 3 | 2 | 3 | 2 | 2 | 3 | 3 | 2 |
| hcmut_v1/HCMUT-015 | HCMUT_GIANGDAY2282_PhuLuc_1 @5056/7709 | 1 | 1 | 7 | 1 | 7 | 1 | 7 | 1 | 7 | 1 | 1 | 7 | 7 | 1 |
| hcmut_v1/HCMUT-034 | HCMUT_CTDT1862_Dieu_1 @4698/19613; HCMUT_CTDT1862_Dieu_1 @4786/19613 | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| hcmut_v1/HCMUT-037 | HCMUT_CTDT1862_Dieu_1 @8055/19613 | 1 | 1 | 3 | 1 | 3 | 1 | 4 | 1 | 3 | 1 | 1 | 3 | 3 | 1 |
| hcmut_v1/HCMUT-047 | HCMUT_CTDT1862_Dieu_1 @7106/19613 | 1, 2 | 2, 1 | 1, 5 | 2, 1 | 1, 5 | 2, 1 | 1, 5 | 2, 1 | 1, 5 | 2, 1 | 2, 1 | 1, 5 | 1, 5 | 2, 1 |
| labour_vi_v1/LVN-037 | ND274_2025_Dieu_6 @3673/4511; ND274_2025_Dieu_6 @3849/4511 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

## Latency per query (one batch of all candidates) and memory

| runtime | device | p50 ms/query | p95 ms/query | p50 ms/doc | p95 ms/doc | scored chunks (docs) | truncated | RSS MB (see note) |
|---|---|---|---|---|---|---|---|---|
| gguf_f16_chunk | server | 4595 | 9940 | 229.7 | 497.0 | 3984 (2000) | 0 | 1738 |
| gguf_f16_nochunk | server | 2950 | 5010 | 147.5 | 250.5 | 2000 (2000) | 188 | 1615 |
| gguf_f32_chunk | server | 4883 | 17049 | 244.2 | 852.4 | 3984 (2000) | 0 | 2205 |
| gguf_f32_nochunk | server | 4090 | 5551 | 204.5 | 277.5 | 2000 (2000) | 188 | 1875 |
| gguf_q8_0_chunk | server | 3938 | 10192 | 196.9 | 509.6 | 3984 (2000) | 0 | 1028 |
| gguf_q8_0_nochunk | server | 3092 | 4241 | 154.6 | 212.1 | 2000 (2000) | 188 | 685 |
| h100_fp16_bs16_chunk | cuda | 447 | 612 | 22.4 | 30.6 | 3984 (2000) | 0 | 4285 |
| h100_fp16_bs16_nochunk | cuda | 425 | 537 | 21.2 | 26.8 | 2000 (2000) | 188 | 4448 |
| h100_fp16_bs1_chunk | cuda | 1171 | 2501 | 58.6 | 125.1 | 3984 (2000) | 0 | 4343 |
| h100_fp32_bs1_chunk | cuda | 1637 | 3634 | 81.9 | 181.7 | 3984 (2000) | 0 | 3457 |
| h100_fp32_bs1_nochunk | cuda | 1170 | 1637 | 58.5 | 81.9 | 2000 (2000) | 188 | 3456 |
| torch_fp32_cpu | cpu | 8434 | 26319 | 421.7 | 1316.0 | 2000 (2000) | 188 | 2221 |
| torch_fp32_cpu_chunk | cpu | 8668 | 25087 | 433.4 | 1254.3 | 3984 (2000) | 0 | 1690 |

RSS: llama-server runtimes = sampled peak RSS of the server process (mapped weights count once touched; Metal buffers are not in ps RSS); torch runtimes = peak RSS of the whole Python process (model + corpus + retrievers).
