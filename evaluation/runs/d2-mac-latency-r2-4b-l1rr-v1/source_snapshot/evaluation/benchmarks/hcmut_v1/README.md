# hcmut_v1: HCMUT academic-affairs benchmark (50 tasks)

Status: **AI-verified, not human-reviewed.** Final task file: `tasks.json`.

## Purpose

Questions a student or academic advisor might ask about public HCMUT (Trường Đại học Bách khoa – ĐHQG-HCM) academic-affairs regulations, each with source-backed gold evidence, for testing grounded answering and refusal in LuatCheck. 40 questions have one gold record, 5 need two records, and 5 have no answer in the corpus and expect a refusal.

## Corpus

`data/corpus/hcmut_academic_v1.json` (10 documents, 143 sections). Provenance, caveats and extraction checks are in `docs/materials/hcmut-sources/README.md` and `manifest.json`. Gold IDs are corpus `doc_id`s. Amendment documents contain only changed clauses; their base regulations are not in the corpus (see ADJUDICATION.md).

## Schema (per task)

| Field | Meaning |
|---|---|
| `task_id` | `HCMUT-001` to `HCMUT-050` |
| `category` | `single`, `multi` (two records), `out_of_scope` |
| `question` | Vietnamese question |
| `expected_behavior` | `answer` or `refuse` |
| `ground_truth_article_ids` | gold corpus record IDs (`[]` for out_of_scope) |
| `expected_answer` | short reference answer fully determined by the quoted text (for refuse: why the corpus cannot answer) |
| `reference_evidence` | list of `{article_id, exact_quote, pdf_pages}`; each quote is a verbatim substring of the record content (line breaks as in the corpus) |
| `doc_code` | document code of the first cited document |
| `author` | who wrote the item (draft: Claude Haiku (AI)) |
| `revised_by` | present only on changed items: `Claude Sonnet (AI) adjudicator` |
| `gold_status` | `ai_verified_two_independent_reviewers_adjudicated` (49 items) or `ai_verified_adjudicator_plus_independent_recheck` (HCMUT-021, accepted by the independent recheck in `recheck_C.json`) |
| `verification` | `{verify_A, verify_B, adjudication: kept/fixed/replaced, note}` |
| `notes` | writer notes for verifiers (amendment context, distractors) |

## Counts

50 tasks: 40 single, 5 multi (021, 022, 023, 046, 047), 5 out_of_scope (024, 025, 048, 049, 050). Adjudication: 38 kept unchanged, 3 kept with a note (038, 039, 046), 8 fixed (005, 014, 016, 022, 023, 032, 036, 047), 1 replaced (021).

## Provenance chain

1. Draft: Claude Haiku (AI) wrote 50 tasks under `WRITER_BRIEF.md` (`draft_all.json`; parts in `draft_part1.json`, `draft_part2.json`).
2. Independent verification: two Claude Sonnet (AI) verifiers worked separately under `VERIFIER_BRIEF.md` (`verify_A.json`, `verify_B.json`).
3. Adjudication: Claude Sonnet (AI) read every flagged task against the corpus, decided each, and replaced HCMUT-021 (`ADJUDICATION.md`).
4. Recheck: mechanical checks run on `tasks.json` before writing: 50 unique IDs, every quote verbatim in its record, gold IDs exist and equal the cited records, category mix 40/5/5, no duplicate or near-duplicate questions (max pairwise similarity 0.67), unflagged items unchanged from the draft apart from status and verification. A keyword re-search confirmed the five out_of_scope items.
5. A sanity run (`evaluation/runs/hcmut-sanity-draft-v2/`) answered the draft with Gemma-4-31B under oracle and closed-book conditions, judged by DeepSeek Flash. These are LLM estimates, not labels, and were used only as a pointer for review.

## Limitations

AI-only verification, no human or expert review; amendment-only documents with missing base regulations; printed numbers and dates unverified; some items guessable without the corpus; HCMUT-021 was written by the adjudicator and accepted by one independent recheck (not by the two original verifiers). Details in `ADJUDICATION.md`. Lexical overlap with `expected_answer` is a lexical proxy, not answer correctness; correctness claims need separate reviewed evidence.

## Final checks (23 Oct 2026)
- Independent recheck of the 9 changed items (`recheck_C.json`, a fresh Sonnet verifier that did not read the adjudication): 9/9 accept.
- Oracle-context check on the final file (`evaluation/runs/hcmut-sanity-final-v1/`, Gemma-4-31B answers with the gold records, DeepSeek Flash judge; LLM estimates, not labels): 44 correct + 5 appropriate refusals, 1 partially correct (HCMUT-014). The source states the full condition "trước 16g00 của ngày làm việc cách trước ngày dạy bù tối thiểu 01 ngày và trước tối đa 07 ngày"; the reference answer and quote were completed with the 16g00 condition (asked numbers unchanged).
