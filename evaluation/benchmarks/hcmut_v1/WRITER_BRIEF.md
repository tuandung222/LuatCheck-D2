# Writer brief: HCMUT academic-affairs benchmark (hcmut_v1), 23 Oct 2026

Corpus (read-only): data/corpus/hcmut_academic_v1.json — 143 sections from 10 official HCMUT documents
(records: doc_id `HCMUT_<DOCCODE>_<SECTION>`, source_name, title, content, source_url, source_pages ...).
Provenance and caveats: docs/materials/hcmut-sources/manifest.json and README.md (read both first).
Rules: AGENTS.md of the repository (never invent content; anything not in the corpus is not a fact).

## Your output
Write a JSON list of task objects to the file named in your assignment. Every task:
{
  "task_id": "HCMUT-<NNN>",            // number range given in your assignment
  "category": "single" | "multi" | "out_of_scope",
  "question": "<natural Vietnamese, as a student or academic advisor would ask>",
  "ground_truth_article_ids": ["HCMUT_..."],      // [] for out_of_scope
  "expected_behavior": "answer" | "refuse",
  "expected_answer": "<short Vietnamese answer fully determined by the quoted text; for refuse: why the corpus cannot answer>",
  "reference_evidence": [{"article_id": "HCMUT_...", "exact_quote": "<verbatim substring of that record's content>", "pdf_pages": [..]}],
  "doc_code": "<DOCCODE>",
  "author": "Claude Haiku (AI), draft — not human-reviewed",
  "gold_status": "draft_ai_unverified",
  "notes": "<anything a verifier should know: amendment context, ambiguity you avoided, date caveats>"
}

## Rules for questions
1. Each answerable question must be answerable ONLY from the quoted text, with a single correct answer. No outside knowledge, no current-events assumptions.
2. exact_quote must be copied character-for-character from the record's `content` (same Unicode, same spacing). Keep quotes short (one clause/sentence) but sufficient. Run a containment check with a script before finishing (load the corpus with Python and assert `quote in content` for every evidence item); fix any failure.
3. Paraphrase the question; do not copy a whole sentence of the source into the question. Keep the domain terms (tín chỉ, học kỳ, cảnh báo học vụ, GVCN, CVHT...).
4. Amendment documents (HVDT1260, HVDT2749, HVCHUNG1259, GIANGDAY2282, CTDT1862) only contain changed clauses; their base regulations are NOT in the corpus. Ask only about what the amendment text itself states. Do not ask questions whose answer depends on the base regulation. Mention the amending decision in the question when the rule could differ from older versions (e.g. "theo Quyết định 1260/QĐ-ĐHBK sửa đổi ...").
5. Do not ask about printed decision numbers/dates (they are blank in the PDFs and come from the website listing).
6. Prefer questions with checkable specifics: numbers (tín chỉ, %, số ngày, điểm), conditions, who is responsible, deadlines, permitted/not permitted. Avoid yes/no questions whose answer is trivially in the title.
7. "multi" questions need two sections (same or different documents) combined; cite both.
8. "out_of_scope" questions must be realistic HCMUT student questions whose answer is NOT in this corpus (e.g. rules only in the unavailable base regulation 2933 such as conditions for "buộc thôi học", or other universities, or national law). Before writing one, search the corpus text (Python substring/keyword search over all contents) to confirm the answer is absent, and record the search terms you checked in notes. expected_behavior = "refuse".
9. Vary difficulty; avoid near-duplicate questions; no question about a single word's definition only.
10. Do not modify the corpus or any other file except your output file.

Finish with: count by category, the containment-check result, and any question you were unsure about.
