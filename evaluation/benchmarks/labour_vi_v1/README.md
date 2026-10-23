# labour_vi_v1: Vietnamese labour-law benchmark (50 tasks)

Status: **AI-verified, not human-reviewed.** Final task file: `tasks.json`. `benchmark.yaml` still has `review_status: pending` and is not changed by this step.

## Purpose

Questions an employee or an SME HR officer might ask about Vietnamese labour and employment law, each with source-backed gold evidence, for testing grounded answering and refusal in LuatCheck. 40 questions have one gold record (two in LVN-016 and LVN-019, both records from the same decree), 5 need two records, and 5 have no answer in the corpus and expect a refusal.

## Corpus

`data/corpus/labour_vi_v1.json`: 10 official documents, 458 records (446 articles, 12 appendix sections). Provenance, hashes, amendment relationships and caveats: `docs/materials/labour-sources/README.md` and `manifest.json`. Gold IDs are corpus `doc_id`s. Texts are as printed (BLLD2019 is the original 2019 Gazette text); later amendments were not checked. Not in the corpus: NĐ 145/2020 and other implementing decrees over the 40-page limit, unnumbered annexes of ND293_2025 and TT26_2025 (see ADJUDICATION.md).

## Schema (per task)

| Field | Meaning |
|---|---|
| `task_id` | `LVN-001` to `LVN-050` |
| `category` | `single`, `multi` (two records), `out_of_scope` |
| `question` | Vietnamese question |
| `expected_behavior` | `answer` or `refuse` |
| `ground_truth_article_ids` | gold corpus record IDs (`[]` for out_of_scope) |
| `expected_answer` | short reference answer fully determined by the quoted text (for refuse: why the corpus cannot answer) |
| `reference_evidence` | list of `{article_id, exact_quote, pdf_pages}`; each quote is a verbatim substring of the record content; `pdf_pages` equal the record's `source_pages` |
| `doc_code` | document code of the first cited document |
| `author` | who wrote the item (draft: Claude Haiku (AI); LVN-047: Claude Sonnet (AI) adjudicator) |
| `revised_by` | present only on changed items: `Claude Sonnet (AI) adjudicator` |
| `gold_status` | `ai_verified_two_independent_reviewers_adjudicated` (49 items) or `ai_replacement_adjudicator_only_not_reviewed_by_independent_verifiers` (LVN-047) |
| `verification` | `{verify_A, verify_B, adjudication: kept/fixed/replaced, note}`: the two verifiers' verdicts, the decision and the reason |
| `notes` | writer notes for verifiers (amendment context, search terms for out_of_scope) |

## Counts

50 tasks: 40 single, 5 multi (021, 022, 023, 046, 047), 5 out_of_scope (024, 025, 048, 049, 050). By `doc_code`: LVL2025 7, BLLD2019 6, ND274_2025 6, ND219_2025 5, ND135_2020 5, TT26_2025 5, ND293_2025 4, ND318_2025 4, LCD2024 4, ND143_2024 4 (for out_of_scope items `doc_code` is the document nearest the topic, not a gold record). Adjudication: 39 kept unchanged, 10 fixed (002, 010, 014, 016, 019, 023, 024, 025, 031, 044), 1 replaced (047).

## Provenance chain

1. Draft: Claude Haiku (AI) wrote 50 tasks under `WRITER_BRIEF.md` (`draft_all.json`; parts in `draft_part1.json`, `draft_part2.json`).
2. Independent verification: two Claude Sonnet (AI) verifiers worked separately under `VERIFIER_BRIEF.md` (`verify_A.json`, `verify_B.json`).
3. Adjudication: Claude Sonnet (AI) read every flagged task against the corpus, decided each, and replaced LVN-047 (`ADJUDICATION.md`).
4. Mechanical checks run before `tasks.json` was written: 50 unique IDs (LVN-001 to 050); every quote (76) a verbatim substring of its record; gold IDs exist and equal the cited records; no `_MAU_` ids; mix 40/5/5; no duplicate questions (max pairwise similarity 0.59); unflagged items identical to the draft apart from `gold_status` and `verification`; the five out_of_scope items re-searched over all 458 records.
5. A sanity run on the draft (`evaluation/runs/labour-sanity-draft-v1/`: Gemma-4-31B with gold context, 45/45 answerable correct and 5/5 refusals appropriate, LLM judge) was used only as a pointer. These are LLM estimates, not labels.

## Limitations

AI-only verification, no human or expert review; LVN-047 reviewed by the adjudicator only; NĐ 145/2020 and some annexes absent; TT26_2025 number and date come from vanban.chinhphu.vn metadata, not from the printed PDF; texts as promulgated, later amendments not checked. Details in `ADJUDICATION.md`. Lexical overlap with `expected_answer` is a lexical proxy, not answer correctness; correctness claims need separate reviewed evidence.

## Final checks (23 Oct 2026)
- Independent recheck of the 11 changed items (`recheck_C.json`, a fresh Sonnet verifier that did not read the adjudication): 10 accept, 1 fix (LVN-014: the registration procedure of ND318 Điều 6 applies from 01/01/2027 per Điều 25 khoản 3) — applied by the orchestrator, quotes re-verified.
- Oracle-context check on the final file (`evaluation/runs/labour-sanity-final-v1/`, Gemma-4-31B with the gold records, DeepSeek Flash judge; LLM estimates, not labels): 45/45 answerable correct, 5/5 appropriate refusals. Closed-book: no answerable item correct (all items require the corpus).
