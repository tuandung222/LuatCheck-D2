# Proposal: harder benchmarks v2 (hcmut_v2, labour_vi_v2)

> Written: 2026-10-23 22:15 +07. Status: **proposal only, not started.** Nothing in this file has been built or run.
> Owner decision needed before work starts (section 9).

## 1. Why

The v1 benchmarks (`evaluation/benchmarks/hcmut_v1`, `labour_vi_v1`, frozen) are correct but too easy. The audit
in `docs/reviews/benchmark_quality_2026-10-23.md` found no wrong gold answers, but:

| Evidence (v1, 45 answerable items each) | hcmut_v1 | labour_vi_v1 |
|---|---|---|
| Plain BM25 on the raw question puts a gold record at **rank 1** | 40 / 45 | 35 / 45 |
| Plain BM25 puts a gold record in the top 5 | 45 / 45 | 44 / 45 |
| Answered correctly **without any document** (Gemma-4-31B, DeepSeek Flash judge; LLM estimate) | 15 / 45 (+12 partial) | 12 / 45 (+10 partial) |
| Category mix | 40 single, 5 multi, 5 out_of_scope | 40 single, 5 multi, 5 out_of_scope |

As a result, the benchmark measures keyword matching and parametric knowledge more than grounded retrieval and reading.
The reranker, the multi-step search/read loop and the verifier are not really exercised, and retrieval metrics
(Recall@k, MRR) cannot separate the D2 variants.

**Goal of v2:** most items can only be answered by finding and reading the right passages. Finding them must be
non-trivial, and the answer must still be unambiguous and verifiable.

## 2. Scope and principles

- Same corpora as v1: `data/corpus/hcmut_academic_v1.json` (10 HCMUT documents) and `data/corpus/labour_vi_v1.json`
  (10 labour documents). There is no new ingestion, and corpus hashes stay as locked.
- v1 stays frozen and is kept as the "easy / lexical" reference set. v2 is a new version with its own lock. v1 files
  are not edited.
- 50 items per benchmark, as in v1.
- AGENTS.md applies:
  - Gold must be source-backed and contain verbatim quotes.
  - LLM checks are labelled as LLM estimates.
  - No fabricated labels.
  - Items are frozen before main collection.
- Domain specifics live in the benchmark data and config only (AGENTS.md "Direction" section).

## 3. Item types (target mix per benchmark)

| Type | Share | What makes it hard | Example shape |
|---|---|---|---|
| **Scenario / case application** | ~30% | The question describes a situation, not a clause; the solver must identify the applicable rule. | "Chị A ký HĐLĐ xác định thời hạn 24 tháng, đang mang thai tháng thứ 5; công ty muốn chấm dứt vì hết hạn. Công ty phải làm gì?" |
| **Multi-hop, cross-record / cross-document** | ~25% | Needs ≥2 records, often in 2 documents (Code + implementing decree; academic regulation + tuition rule). | "Sinh viên bị cảnh báo học vụ lần 2 thì học phí học lại tính thế nào?" |
| **Conditions, exceptions, temporal validity** | ~15% | Answer depends on a condition/exception or on which instrument is in force at a stated date. | "Tính đến 01/03/2026, mức đóng BHTN tối đa là bao nhiêu?" |
| **Numeric computation** | ~10% | Requires a value from the text plus arithmetic; gold includes the derivation. | Severance, credit counts, deadlines in days. |
| **Hard negatives (refuse)** | ~10% | Close to a covered topic but truly absent from the corpus, or a false premise. | Asks for a procedure the regulation does not define. |
| **Clarify** | ~5–10% | Missing a fact that changes the answer (e.g. contract type, cohort year). | |

Writing rules:
- **Paraphrase:** do not reuse the distinctive wording or the title of the gold record in the question.
- **Pin the frame:** pin the time and the instrument when the answer depends on them.
- **No leakage:** do not include the answer number or the condition in the question.
- **One correct answer:** each item has exactly one correct answer that can be stated in a few sentences.

## 4. Gold format (extends the v1 schema)

Fields:
- `task_id`, `question`, `expected_behavior` (answer / clarify / refuse), `category` (new values: `scenario`,
  `multi_hop`, `conditional_temporal`, `numeric`, `hard_negative`, `clarify`)
- `difficulty` (`easy` / `medium` / `hard`, set from the gates in section 5, not by the writer)
- `ground_truth_article_ids` (all records needed)
- `reference_evidence` (one verbatim quote per hop)
- `expected_answer`
- `reasoning_steps` (short derivation, for multi-hop and numeric items)
- `as_of_date` (when time matters)
- `distractor_ids` (similar-looking but wrong records, optional)
- `source_doc_codes`

## 5. Acceptance gates (measured per item, reproducible script)

An item enters v2 only if it passes all the gates below. The gate results are stored per item.

| Gate | How it is measured | Pass condition |
|---|---|---|
| G1 Verbatim evidence | Script: each quote is found in its cited record (whitespace-normalised). | 100% |
| G2 Solvable with gold | 2 strong gateway models answer with only the gold records as context; DeepSeek Flash judge. | Both correct (target ≥90% of items overall; failures are rewritten or dropped) |
| G3 Not guessable | 3 strong models (e.g. GPT-5.5, DeepSeek-v4-pro, Gemini) answer with **no context** and a domain-neutral prompt. | Benchmark-level target: ≤15% of answerable items closed-book correct by majority. An item answered correctly by ≥2 models is rewritten or dropped. |
| G4 Retrieval non-trivial | BM25 and dense retrieval on the raw question over the full corpus. | Benchmark-level target: gold at rank 1 for ≤50% of items. Multi-hop: all gold records in the top 5 for ≤40%. |
| G5 Refusal validity | Corpus text search plus a gateway check with the full relevant document as context. | The information is absent (refuse) or genuinely underdetermined (clarify). |
| G6 Independent verification | A second agent, which did not write the item, re-derives the answer from the corpus; a human spot-check sample follows. | Agreement; disagreements are adjudicated, with the decision recorded in ADJUDICATION.md. |

**Difficulty tiers (anti floor effect).** The D2 controller is Bonsai 2B. If every item is hard, all variants may score
near 0 and the off / l1 / l1_rerank comparison becomes uninformative. Each item gets a tier from the gates, roughly:

- **easy:** retrievable at rank 1, single record.
- **medium:** rank 2–5, or 2 records.
- **hard:** gold not in the top 5, or multi-document / scenario / computation.

Target mix: ~20% easy / 40% medium / 40% hard. Results are reported per tier.

## 6. Process

1. **Seed from v1.** Keep the v1 items that already pass G3 and G4 (not closed-book solvable, and not trivially retrieved). Mark them `origin: v1:<task_id>`.
2. **Write.** Sonnet writer agents, one per document cluster (about 2–3 documents each). They follow the type mix in section 3, and each writes about 1.5× the needed items.
3. **Gate.** One script (`evaluation/benchmarks/qa/gate_items.py`) runs G1–G5 on all drafts and writes a per-item JSON. Expected gateway cost: USD 1–3.
4. **Select.** Pick 50 per benchmark that satisfy the type mix and tier mix, and balance across the 10 documents (no document over 15%).
5. **Verify.** Independent verifier agent (G6). The supervisor spot-checks at least 20 items per benchmark against the source PDFs.
6. **Freeze.** Write `tasks.json`, README (method, gate statistics, limitations), ADJUDICATION.md, `benchmark.yaml`, and `benchmark.lock.json` via `make benchmark-freeze`.
7. **Smoke.** Run the D2 runner for a few items per variant to confirm the schema works end to end. No new runner features should be needed beyond reading the new optional fields.

## 7. Schedule and cost (estimate)

- **Effort:** about 4–6 hours of agent work, plus about 1 hour of supervisor verification.
- **Gateway cost:** about USD 2–4 in total.
- **D2 data collection:** moves from the night of Fri 23 Oct to the morning of Sat 24 Oct, on v2. That still leaves time for:
  - the human audit on Sat 24 Oct evening;
  - the report deadline at 23:59 on Sun 25 Oct.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Harder items have wrong or ambiguous gold | G2 with two models, the G6 independent re-derivation, and a supervisor spot-check; drop rather than patch doubtful items. |
| Floor effect with Bonsai 2B | Difficulty tiers; report per tier; keep a v1 run as the easy reference. |
| "Not guessable" measured only by LLMs | State that G3 is an LLM estimate; report the closed-book baseline next to every variant. |
| Paraphrasing makes questions unnatural | Native-Vietnamese review of wording in G6; scenario style keeps questions realistic. |
| Time overrun delays data collection | Hard stop: if v2 is not frozen by Sat 24 Oct 10:00 +07, run D2 on v1 and report v2 as follow-up. |
| Labour amendments after the corpus snapshot | Pin `as_of_date` and the instrument; state that later amendments were not checked. |

## 9. Decisions needed from the owner

1. Approve v2 (keep v1 frozen) and whether D2 main numbers use v2 only, or v2 as main with v1 as the easy reference.
2. Approve the timeline change (data collection Saturday morning) and the hard-stop rule in section 8.
3. Type mix and tier mix in sections 3 and 5: keep, or adjust.
4. Size: 50 items per benchmark, or more (for example 80), to narrow the confidence intervals.
