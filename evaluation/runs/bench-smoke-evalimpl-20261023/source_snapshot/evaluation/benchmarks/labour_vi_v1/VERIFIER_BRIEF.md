# Verifier brief: labour_vi_v1 draft (50 tasks), 23 Oct 2026

You are an independent verifier. Another verifier checks the same items separately; do not look for or read
any other verification file in this directory. Read AGENTS.md, WRITER_BRIEF.md, the corpus
data/corpus/labour_vi_v1.json, and docs/materials/labour-sources/manifest.json + README.md
(amendment relationships between documents; original vs amended texts; table layouts).

Input: evaluation/benchmarks/labour_vi_v1/draft_all.json (50 tasks, drafted by Claude Haiku).
Mechanical checks already pass (quote containment, IDs). Your job is semantic verification.

For EVERY task, read the cited records in full (and neighbouring records of the same document when the
question could depend on them) and decide:
1. Answerability: is the question answered by the corpus with a single correct answer? Is anything else in the
   corpus (other sections/documents) that changes or conflicts with the answer? Search the corpus text
   (Python keyword search over all records) — do not rely only on the cited records.
2. Gold correctness: is expected_answer correct and complete for what the question asks, without adding facts
   that are not in the text? Are ground_truth_article_ids the right and sufficient records? Do the quotes
   actually support the answer (not just contain related words)? Tables: check that the row/column reading is right.
3. Question quality: unambiguous, natural Vietnamese, not trivially copied from the source, not dependent on the
   laws or amendments outside the corpus, or on assumed current practice, not a near-duplicate of another task.
4. Out-of-scope items: confirm by your own keyword searches that the corpus does not answer them (list terms).
   If the corpus partly answers, the item must be rejected or rewritten.
5. Behaviour label: expected_behavior answer/refuse is appropriate.

Verdict per task: "accept" | "fix" | "reject".
- "fix": give the exact corrected fields (question / expected_answer / ground_truth_article_ids /
  reference_evidence with verbatim exact_quote) — verify containment of any new quote with Python.
- "reject": the item cannot be repaired without changing its intent; explain.

Write a JSON list to your assigned output file, one object per task:
{"task_id", "verdict", "issues": [..], "fix": {..} or null, "searched_terms": [..] (for out_of_scope and
conflict checks), "confidence": "high"|"medium"|"low"}
Then a short summary: counts per verdict and the most serious problems. Do not edit any other file.
