# Diagnostic run: Ternary Bonsai 2 2B, MLX runtime — not report evidence

Collected 23 October 2026 with `config/d2_mlx2b_diagnostic.yaml` on the Apple M4 (16 GB): MLX 2-bit on mlx_vlm 0.7.10 (HF revision 1c6cbae2).
Same frozen tasks, corpus, retrieval, budgets and L1 checks as the D2 main run, with the post-collection prompt
revision **and the compacted tool outputs** (query-aware snippets, duplicate notices). 10 tasks x OFF/ON x seed 42.
Status: `report_eligible: false`.

Paired with the other 2B runtime run (same weights): `gguf2b-bonsai-diag-v1` and `mlx2b-bonsai-diag-v1` were
collected back to back with the same source. Sampling differs between runtimes, so their answers differ; compare
speed and execution errors, not correctness. Totals: GGUF 197 s (median 7.6 s/trial, 0 errors); MLX 427 s
(median 13.7 s/trial, 2 output-cap errors). Server memory: GGUF ~0.7 GB; MLX up to 6.6 GB.
