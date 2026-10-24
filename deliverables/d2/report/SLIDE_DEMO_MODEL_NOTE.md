# Slide and demo model note (replaces the outdated Qwen2.5-3B note)

Written 2026-10-23 (UTC+7). The earlier version of this file said that the demo model differed from the reported numbers.
That is no longer true.

**Correct statement for slides and Q&A:** the live demo and every reported number use the same controller, Ternary Bonsai 2 2B
(`prism-ml/Ternary-Bonsai-2-2B-gguf`, PQ2_0, PrismML `llama.cpp` commit 73bfe6c), the same sampler, budgets, prompts and L1 verifier,
and the same two corpora (`hcmut_academic_v1`, `labour_vi_v1`). Demo behaviour illustrates the tables; it is not evidence for them.
The Qwen2.5-3B / `bll2019_v1` pilot is superseded and must not appear on a results slide.

Where to look:

- `deliverables/d2/demo/D2_SLIDES_OUTLINE.md`: 10-minute talk, slide by slide, mapped to the rubric.
- `deliverables/d2/demo/DEMO_SCRIPT.md`: server start-up, demo queries, fallback plan, backup-video checklist.
- `deliverables/d2/report/main_d2.tex`: the report the slides must agree with (Section 1 "Models and framework").
