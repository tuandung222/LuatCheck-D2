# Design analysis: span-referenced answers so L1 can verify exactly

> Written 2026-10-24 16:10 +07 by the supervising agent. Status: analysis and recommendation; not implemented.

## 1. The real problem

L1 checks attribution, but the controller's output format decides how checkable an answer is. Today the model writes
free text plus optional `exact_quote` strings, so L1 has to re-discover the alignment between answer and source with
heuristics (verbatim quote search, a whole-record bag of words, document-level number lookup). Every heuristic error is
a false rejection or a false pass.

The v3 ledgers show the cost:
- 175 of 237 L1 repairs are quote mismatches.
- 98 failed quotes contain `...` or `[...]`. Our own search snippet joins clauses with `" [...] "` and truncates with `"..."`
  (`src/tools/domain_tools.py::_snippet`), so the model copies those markers and L1 then rejects them. Part of the
  problem is created by the system, not the model.
- Document-level number checks let wrong numbers pass (LVN-017, "60 ngày").
- After a rejection the 2B model usually refuses instead of repairing.

Principle: a small model is bad at copying text verbatim and good at choosing a short identifier. Let it **point to**
evidence instead of **copying** it, and let L1 verify the declared alignment instead of guessing it.

## 2. Options

| Option | Model output | L1 work | Refactor | Small-model risk |
|---|---|---|---|---|
| A. L1 v2 heuristics (in progress) | unchanged free text + quotes | fuzzy quotes, sentence-level support | small (verifier only) | none new; alignment still guessed |
| B. Inline span markers | free text with `[S3]` markers | split by marker, check each sentence vs its spans | medium | markers misplaced or missing |
| C. **Claims array with span ids** | `claims: [{text, evidence: [span_id]}]`, answer rendered from claims | per-claim checks against exactly the cited spans | medium (feature-flagged, additive) | more complex JSON; constrained decoding enforces shape |
| D. Evidence-then-answer (two actions) | `select_evidence` then `answer` from the selected spans | trivial alignment | larger (new action, loop change) | one more step, more latency |

## 3. Recommended design (option C)

**Spans computed on the fly, corpus untouched.**
- A span is a clause, point or sentence of a record. Reuse the existing clause splitter (`_CLAUSE_SPLIT`), and fall back
  to sentence splitting.
- Span ids are `<doc_id>#S<n>`, deterministic from the stored record text.
- No corpus rebuild, so corpora, benchmark locks and the frozen v3 runs stay valid.

**Tool observations.**
- `read` returns the record as numbered spans.
- `search` snippets carry span ids instead of `[...]` joins.
- The ledger records which spans were shown, giving a stronger provenance check: "this evidence was shown to the model"
  instead of only "this document was retrieved".

**Answer schema** (`model.answer_format: free_text | claims`; `free_text` reproduces v3):
- `{"action": "answer", "claims": [{"text": str, "evidence": [span_id, ...]}], ...}`, with 1–5 claims.
- The user-facing answer is the claims joined in order.
- `citations` (article ids) is derived from the spans, so existing metrics and the judge still work unchanged.

**L1 v3, per claim:**
1. Every span id exists and was shown in this session (hard check).
2. Every number+unit in the claim appears in its cited spans (claim-local, normalised; the newline-unit fix stays).
3. Lexical support of the claim against its cited spans only (threshold set on the bll2019 dev set, not on v1).
4. Optional L2: an NLI pair (premise = cited spans, hypothesis = claim). It now fits NLI exactly: short premise, one
   claim.

**Repair feedback (actionable):**
- Name the failing claim and check.
- Quote the cited span verbatim, e.g. *"Claim 1 says '60 ngày' but #S3 says: «… 10 ngày …»"*.
- List valid span ids when an id is unknown.

**Prompt.** Answer-format instructions go in a new config file referenced by the app config, not in
`config/domains/*.yaml`, because those profile files are hashed by the benchmark locks.

## 4. Trade-offs

| Dimension | Gain | Cost / risk |
|---|---|---|
| Verifiability | exact claim→evidence alignment; quote-copy failures disappear | none |
| Number errors | claim-local check catches LVN-017-type errors | a correct number paraphrased in words ("mười ngày") fails; rare in this corpus |
| Small-model compliance | short ids instead of long quotes; shorter outputs, fewer truncations | richer schema: wrong or missing span ids → caught by L1 with a list of valid ids |
| Tokens | answer JSON shrinks (no copied quotes) | span markers add about 5–8 tokens per span to observations (+≈40 per read of a median record) |
| UI | highlight the exact source span per claim | renderer must show claims (the joined text works meanwhile) |
| Evaluation | span-level citation precision becomes possible; L2 NLI gets clean pairs | the judge stays on the joined text for comparability with v3 |
| Reproducibility | feature flag; v3 stays byte-identical with `free_text` + L1 v1 | two code paths to maintain |
| Scientific validity | principled, not task-tuned | still a post-hoc revision on the same tasks: report it as such; confirm on benchmark v2 |

## 5. Refactor size (feature-flagged, additive)

| Area | Change | Size |
|---|---|---|
| new `src/evidence/spans.py` | domain-agnostic span segmentation + ids (profile may override the splitter) | ~120 lines |
| `src/tools/domain_tools.py` | numbered spans in `read`, span-tagged snippets in `search`, shown-span set | ~80 lines |
| `src/agent/llm_client.py`, `state.py` | `claims` answer branch behind the flag; `Claim` model; `Citation.span_ids` | ~60 lines |
| `src/agent/loop.py` | record shown spans; render answer from claims; pass spans to L1 | ~60 lines |
| `src/verifier/` | L1 v3 claim checks + feedback (reuses v2 normalisation) | ~200 lines |
| config + prompt addendum | `answer_format`, `l1_version`, answer instructions file | ~40 lines |
| evaluation | judge packet from joined claims; citation metrics via span→doc mapping; replay tool | ~60 lines |
| UI (optional for tonight) | per-claim span highlight | ~100 lines |
| tests (real data) | spans, schema, L1 v3, compatibility of v3 path | ~200 lines |

**Estimate:** about 3–4 hours of agent work plus verification. It is not a rewrite: the loop, tools and verifier keep
their structure, and every change sits behind `answer_format` / `l1_version`.

## 6. Execution plan with a safety gate

1. Implement behind the flags; the v3 path must stay byte-identical (tests replay recorded v3 drafts).
2. **Compliance gate on 82** (≈10 minutes): 20 tasks × {2B, 4B} with `claims` + L1 v3. Measure:
   - valid JSON rate;
   - valid span-id rate;
   - claims per answer;
   - repair success rate.

   Proceed if span-id validity is ≥90% and JSON validity is ≥98%. Otherwise fall back to option A (L1 v2) for the rerun.
3. Full matrix on GPUs 2 and 3:
   - revised system × {2B, 4B};
   - variants OFF / L1v3 / L1v3+rerank × 3 seeds, plus the closed-book and oracle baselines;
   - about 17 minutes per run.
4. Judge, compare v3 against the revised system, and replay L1 against the judge labels.
