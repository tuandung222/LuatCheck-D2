# Writer brief: Vietnamese labour-law benchmark (labour_vi_v1), 23 Oct 2026

Corpus (read-only): data/corpus/labour_vi_v1.json — articles/sections from 10 official Vietnamese labour-law documents
(records: doc_id `<DOCCODE>_Dieu_<n>` or `<DOCCODE>_<section>`, source_name, title, content, source_url, source_pages ...).
Provenance and caveats: docs/materials/labour-sources/manifest.json and README.md (read both first).
Rules: AGENTS.md of the repository (never invent content; anything not in the corpus is not a fact).

## Your output
Write a JSON list of task objects to the file named in your assignment. Every task:
{
  "task_id": "LVN-<NNN>",            // number range given in your assignment
  "category": "single" | "multi" | "out_of_scope",
  "question": "<natural Vietnamese, as an employee or SME HR officer would ask>",
  "ground_truth_article_ids": ["<DOCCODE>_Dieu_..."],      // [] for out_of_scope
  "expected_behavior": "answer" | "refuse",
  "expected_answer": "<short Vietnamese answer fully determined by the quoted text; for refuse: why the corpus cannot answer>",
  "reference_evidence": [{"article_id": "<DOCCODE>_...", "exact_quote": "<verbatim substring of that record's content>", "pdf_pages": [..]}],
  "doc_code": "<DOCCODE>",
  "author": "Claude Haiku (AI), draft — not human-reviewed",
  "gold_status": "draft_ai_unverified",
  "notes": "<anything a verifier should know: amendment context, ambiguity you avoided, date caveats>"
}

## Rules for questions
1. Each answerable question must be answerable ONLY from the quoted text, with a single correct answer. No outside knowledge, no current-events assumptions.
2. exact_quote must be copied character-for-character from the record's `content` (same Unicode, same spacing). Keep quotes short (one clause/sentence) but sufficient. Run a containment check with a script before finishing (load the corpus with Python and assert `quote in content` for every evidence item); fix any failure.
3. Paraphrase the question; do not copy a whole sentence of the source into the question. Keep legal terms (hợp đồng lao động, trợ cấp thôi việc, lương tối thiểu vùng, xử phạt, BHXH ...).
4. State the legal basis scope when versions could differ: name the document (e.g. "theo Nghị định 145/2020/NĐ-CP"). Answers must follow the text as promulgated in this corpus; never assume later amendments or current practice. If a document in the corpus amends another, ask only what the text in the corpus itself states. The Labour Code 2019 records are the original Gazette text (BLLD2019).
5. Do not ask about decision numbers/dates beyond what is printed in the record text.
6. Prefer questions with checkable specifics: numbers (tín chỉ, %, số ngày, điểm), conditions, who is responsible, deadlines, permitted/not permitted. Avoid yes/no questions whose answer is trivially in the title.
7. "multi" questions need two sections (same or different documents) combined; cite both.
8. "out_of_scope" questions must be realistic employee or HR questions whose answer is NOT in this corpus (e.g. rules from laws not in this corpus, other jurisdictions, or tax/civil matters) — but first search the whole corpus to confirm the answer is truly absent. Before writing one, search the corpus text (Python substring/keyword search over all contents) to confirm the answer is absent, and record the search terms you checked in notes. expected_behavior = "refuse".
9. Vary difficulty; avoid near-duplicate questions; no question about a single word's definition only.
10. Do not modify the corpus or any other file except your output file.

Finish with: count by category, the containment-check result, and any question you were unsure about.
