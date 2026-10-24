# Bounded judge recovery — 22 October 2026

The initial collection already allowed two attempts per output. A first streamed recovery retried all 11 initially invalid outputs once with 16,384 output tokens. After the rubric-aligned parser correction, 57/60 judgments were accepted. Three OFF outputs remained invalid: two reached the output length limit, and one repeated an identical candidate claim quote.

The user explicitly requested additional retries. Recovery v2 covers exactly these three still-invalid outputs; it preserves all 57 accepted judgments. It uses the same model, semantic prompt, blinded task packet, high reasoning setting and schema validator. It raises only the output budget to 32,768 tokens and runs one task at a time, with at most three attempts per task and 5/10 second delays between failed attempts. The first valid judgment is accepted regardless of score. Valid judgments are never retried to improve the result. A semantically unjudgeable but schema-valid result is retained as such; retry is not used to hide a reference problem.

All request bodies, raw SSE chunks, actual model identifiers, errors and available usage/cost fields are saved in a new versioned run directory. Older results and accounting discrepancies are preserved. API errors with missing usage are not counted as zero cost. This recovery policy was added after observing errors and was not preregistered.

Runner: `evaluation/recover_judge.py`. `--previous-recovery` is repeatable, in chronological order. The runner checks historical hashes and reconstructs accepted outputs using the actual raw responses and the current frozen rubric validator. A fresh output directory is required. The analyzer accepts repeatable `--recovery-dir` arguments, validates the ordered parent chain and includes all attempts in accounting.

Human reliability uses the already frozen 12-output sample; no human label is generated or imputed. A later API response cannot retrospectively repair a native application execution error.
