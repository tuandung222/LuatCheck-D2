# Diagnostic run: local controller Ternary Bonsai 2 4B (MLX) — not report evidence

Collected 23 October 2026 with `config/d2_mlx4b_diagnostic.yaml` on the Apple M4 (16 GB): same frozen tasks,
corpus, retrieval, budgets and L1 checks as the D2 main run, with the post-collection prompt revision.
Model `prism-ml/Ternary-Bonsai-2-4B-mlx-2bit`, HF revision dff2caaa23fa8706164c44c10f1b58feb405f76a, served by
mlx_vlm 0.7.10; model-card non-thinking sampler, decoding constrained to the action JSON schema, 768-token cap.
10 tasks x OFF/ON x seed 42 = 20 trials. Status: `report_eligible: false`.

Caveats
- mlx_vlm.server does not apply the configured 8,192-token context window; one recorded call had 9,606 input
  tokens, and the two-provision notice/severance task timed out (60 s per call) at about 10,000 tokens.
- Decoding is deterministic for a fixed seed and identical request, so OFF/ON pairs with identical requests
  produce identical outputs (no cache involved).
- One seed only. Correctness notes are an AI assistant's comparison with frozen references, not human labels.

Observed (AI inspection): 12/20 trials consistent with the reference (tasks 01, 02, 03, 05, 06, 10 in both modes).
Wrong provision or refusal on 04 (both), 08 (both, cited Article 40 instead of 41/46), 09 OFF (right conclusion,
wrong citation) and 09 ON (L1 rejection, then refusal); 07 timed out in both modes.
