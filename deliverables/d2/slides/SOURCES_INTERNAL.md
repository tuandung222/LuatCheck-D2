# Internal: where each number on the slides comes from (for the team and the supervisor, not for the lecturer)

Internal names: "initial system" = v3 (Bonsai 2B); "current system" = r2 (Bonsai 4B), "current system, 2B" = r2-2B; "no verifier / verifier / verifier + reranker" = OFF / L1 / L1+rerank; "final report" = D3.

| Slide | Number(s) | Source |
|---|---|---|
| 2, 7, 12, backup B | strict success with intervals, paired differences | `evaluation/comparisons/v3-2B_vs_r2-2B_vs_r2-4B/comparison.md` |
| 4 | trace, tokens, judge 2/2 | `evaluation/runs/d2-gpu-r2-4b-hcmut-v1/trials.jsonl` (ledger of HCMUT-033, l1_rerank, seed 42); `judge/judgments.jsonl` joined through `judge/private_mapping.json` |
| 8 | faithfulness, citation F1, baselines, errors, refusal sources, paired L1 vs OFF | `evaluation/runs/d2-gpu-r2-4b-{hcmut,labour}-v1/tables/summary.md` |
| 6, backup C | guessable-question counts (15/45, 12/45), 545 trials per run | same `summary.md` (strata table) and `trials.jsonl` |
| 9 | tokens per trial and calls per trial | same `summary.md` (Operations table) |
| 9, backup C | judge USD 1.0635 and 1.1031 (sum 2.17), invalid-attempt shares 0.357 and 0.450 | `evaluation/runs/d2-gpu-r2-4b-*-v1/analysis/summary.json` (`judge_cost_total`) |
| 9, Q&A 16 | reranker parity | `evaluation/runs/reranker-parity-2026-10-23/report.md` |
| 12, backup A | initial-system oracle 28.9 / 44.4, failure findings, what the current system changes | `docs/HANDOFF_2026-10-24.md`, `docs/reviews/v3_failure_analysis_2026-10-24.md`, `docs/plans/D2_REVISION_L1_BONSAI4B.md`, `config/benchmark/model_prism_gguf4b_r2.yaml` |
| 2, 3, 10 | commitments, architecture, threat model | `deliverables/d2/report/main_d2.tex`, `deliverables/d2/report/images/architecture.tikz` |
| 5, backup D | demo plan, frames | `deliverables/d2/demo/DEMO_SCRIPT.md`; frames extracted from `deliverables/d2/demo/gifs/{11_hcmut_answer_4b,13_verifier_repair_4b,15_guardrail_4b}.gif` (current system, 4B, recorded 25 Oct 2026; slide 5 and backup D) and, for the reranker-down frame, `06_error_reranker_down.gif` (initial system, 2B, 24 Oct) |
