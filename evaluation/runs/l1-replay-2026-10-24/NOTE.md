# L1 v1 vs v2: offline replay on recorded answer drafts

Written 2026-10-24 15:55 +07 (Asia/Ho_Chi_Minh, UTC+7) by the W1 implementer (Sonnet). No inference, no model server, no
mocks: the real `LexicalGroundingVerifier` (v1, unchanged) and `LexicalGroundingVerifierV2` run on the real corpus
files with the answers and citations the controller actually produced (ledgers of the frozen runs, citations parsed by
the production `parse_model_citations`). L1 results here are lexical proxies, not answer correctness.

## Commands

```sh
python evaluation/probes/l1_replay.py dev    --out evaluation/runs/l1-replay-2026-10-24   # -> dev_bll2019.json
python evaluation/probes/l1_replay.py replay --out evaluation/runs/l1-replay-2026-10-24   # -> replay_summary.json, drafts.jsonl, feedback_examples.jsonl
.venv/bin/python -m pytest tests/test_l1_v2.py tests/test_domain_profiles.py tests/test_pipeline_builder.py
```

`replay` re-reads `<run>/judge/judgments.jsonl` when it exists, so re-running it after the HCMUT judge finishes fills the
confusion table for HCMUT (it is empty for HCMUT at the time of writing). Both commands are deterministic.

## What was compared

- `l1_and_l1_rerank_all_drafts`: every `answer` draft in the L1 and L1+rerank trials of `d2-gpu-main-hcmut-v3` and
  `d2-gpu-main-labour-v3` (429 drafts: 237 were repaired, 172 accepted, 20 refused after the repair budget).
- `off_final_answers`: the final answer of every OFF trial that answered (157 drafts; OFF never verifies).
- v1 = frozen original (`l1_overlap_threshold` 0.25, the value of the frozen configs). v2 = `l1_support_threshold` 0.50.
- Retrieved ids = the ledger's final `retrieved_article_ids` (an earlier draft may have been verified with a shorter list;
  see the first check below, which shows it did not matter).

## Check 0: the v1 replay is exactly what the runs recorded

For all 429 L1 / L1+rerank drafts the v1 replay reproduces the recorded outcome: the 237 repair events (feedback text
identical, byte for byte), the 172 accepted drafts (pass), the 20 drafts refused after repairs (feedback contained in the
refusal reason). 0 mismatches (`replay_summary.json: v1_replay_vs_recorded`). This is also pinned by
`tests/test_l1_v2.py::test_v1_reproduces_every_recorded_l1_decision_of_the_frozen_runs` and by the sha256 of
`src/verifier/lexical_grounding.py` (unchanged since commit 0bc3108).

## Development set (bll2019, used to choose the support threshold)

`bll2019-main-v2` final answers (qwen2.5:3b, original Labour Code) with labels from `deepseek-judge-main-v1` (analysis-final,
merged with the recovery runs). Label = judge strict success (judgeable, appropriate behaviour, correctness 2, completeness 2,
every claim supported), the definition of `evaluation/analyze_judge.py`. 29 answers: 19 strictly correct, 10 not
(15 from OFF, unselected; 14 from L1-on, which had already passed v1).

Selection rule fixed before any v3 label was read: the largest value of {0.2, 0.3, 0.4, 0.5, 0.6} for which v2 rejects no
strictly-correct answer. Result: 0.5 (at 0.6 one correct answer is rejected).

| support threshold | rejects correct (of 19) | rejects incorrect (of 10) | precision of pass |
|---|---|---|---|
| v1 (0.25 whole-record bag) | 0 | 4 | 0.76 |
| v2 0.2 / 0.3 / 0.4 | 0 | 3 | 0.73 |
| **v2 0.5 (chosen)** | **0** | **4** | **0.76** |
| v2 0.6 | 1 | 5 | 0.78 |

OFF only (15 answers: 8 correct, 7 not): v1 rejects 4 of 7 incorrect and 0 of 8 correct; v2 at 0.5 the same. So on the
development set v2 is not better than v1 at separating correct from incorrect answers, and not worse; the differences are in
*why* an answer is rejected (e.g. an answer judged correctness 2 that v1 rejected for an elided quote now passes; one
unsupported answer that v1 passed is now rejected). The set is tiny, from one 3B model, and the selection is coarse; treat
0.5 as an a-priori operating point, not a calibrated optimum. `support_threshold: 0` switches the sentence check off.

## Replay: failure reasons, drafts failing for each reason

v1 stops at the first failing stage (citations before sentences); v2 reports citation and sentence problems together, so the
v2 columns for `claim_unsupported` and `quantity` are not like-for-like with v1 on drafts that v1 already rejected for a quote.
A draft can have several reasons.

| group | verifier | drafts | failing | missing_citation | unknown/unretrieved id | quote_mismatch | quantity | claim_unsupported |
|---|---|---|---|---|---|---|---|---|
| L1 + L1+rerank, all drafts | v1 | 429 | 257 | 27 | 3 / 3 | 195 | 8 | 25 |
| | v2 | 429 | 283 | 27 | 3 / 3 | 104 | 42 (23 absent, 24 not local) | 188 |
| OFF final answers | v1 | 157 | 89 | 12 | 0 / 1 | 64 | 3 | 11 |
| | v2 | 157 | 96 | 12 | 0 / 1 | 34 | 15 (10 absent, 8 not local) | 63 |

(per-benchmark rows are in `replay_summary.json`). Paired view on the 172 drafts that v1 accepted during the runs: v2 rejects
74 (63 on `claim_unsupported` only, 8 on `quantity_not_local` only, 3 on both). Of the 237 drafts v1 sent back for repair, v2 would have accepted 42; all 42 are drafts that v1 rejected only for the
quote (172 of the 237 were quote-only rejections).

Where v2 remains strict on quotes (104 drafts): paraphrased text, text mixed from two clauses, a number or word changed, or a
real quote cited under another record's id (v2 detects that last case and names the right id in the feedback).

Repair feedback size (failing drafts, characters of the model-visible text): v1 median 135 / p90 263 / max 427; v2 median 383 /
p90 721 / max 777 (at most two findings, clipped source span 170 chars).

## Judge confusion snapshot (LABOUR ONLY; HCMUT judgments did not exist at writing)

Read for the first time in the final replay run, after the code, the parameters and the threshold were frozen; nothing was tuned
on it. `d2-gpu-main-labour-v3/judge/judgments.jsonl` had 542 rows at 2026-10-24 15:51 +07 (LLM judge, not human labels).
Correct = judge strict success. Rows = final answers of trials that answered.

| set | verifier | n | pass: correct / incorrect | precision of pass | rejects incorrect | rejects correct |
|---|---|---|---|---|---|---|
| OFF final answers (unselected) | v1 | 83 | 16 / 21 | 0.43 | 43 of 64 (67%) | 3 of 19 (16%) |
| | v2 | 83 | 15 / 18 | 0.45 | 46 of 64 (72%) | 4 of 19 (21%) |
| L1 / L1+rerank final answers (all passed v1 in the run, so selected) | v1 | 95 | 32 / 63 | 0.34 | 0 | 0 |
| | v2 | 95 | 29 / 29 | 0.50 | 34 of 63 (54%) | 3 of 32 (9%) |

Reading: on unselected OFF answers the two verifiers are close (v2 rejects 3 more incorrect and 1 more correct answer). The
informative number is the second block: among answers v1 let through, v2 would additionally have rejected about half of the
incorrect ones for about one in ten correct ones. Caveats: one benchmark; LLM-judge labels with no human validation; small n;
v2 rejections in the L1 variants would also have triggered repairs and changed the later trajectory, which an offline replay
cannot simulate (a rejected draft might have been repaired into a correct answer or into a refusal).

## Caveats

- Design and the one calibrated threshold used only: the v3 L1 / L1+rerank / OFF *answer texts and ledgers* (to find bugs and
  look at examples; no label), the source corpora, and the bll2019 development set with its judge labels. No v1 or v3 label
  decided a rule or a number. Examples read for bug-finding included v3 drafts; the fixes that came out of that (spacing before
  punctuation, dropped list numbering, per-number context, list lead-ins) are generic.
- The retrieved-id list is the final one of each trial.
- Lexical proxies only: a v2 pass means the quotes are verbatim, the numbers sit in the matching clause and the sentences
  share enough content words with one source window. It does not mean the answer is correct (the dev set contains incorrect
  answers that pass).
- Known weaknesses: filler/hedging sentences ("Tuy nhiên, cần xác định từ văn bản cụ thể") are rejected as unsupported (they
  cost a repair round); coverage by common words is lenient (a sentence assembled from words of one long clause passes);
  a number in a sentence that mixes two clauses is judged by the words around that number, so very short context can
  accept or reject the wrong clause; multi-record answers are scored per window of any cited record.
- Frozen v3 runs stay reproducible only with `verifier.l1_version: v1`; configs that predate the key now default to v2.

## Files

| file | content |
|---|---|
| `dev_bll2019.json` | development set, sweep, selection rule, per-answer outcomes |
| `replay_summary.json` | reasons by group and benchmark, paired v1/v2 pass, v1 replay vs recorded, judge confusion (when judgments exist) |
| `drafts.jsonl` | one row per replayed draft: v1/v2 verdict and reasons, recorded outcome, feedback sizes |
| `feedback_examples.jsonl` | first failing draft per (benchmark, v2 finding kind): answer, v1 feedback, v2 feedback |
