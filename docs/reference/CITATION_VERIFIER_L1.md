# L1 Citation Verifier: Rule-Based Heuristic Design & Specification

**Module:** [`src/verifier/lexical_grounding_v2.py`](../../src/verifier/lexical_grounding_v2.py) · **Orchestrator:** [`src/verifier/pipeline.py`](../../src/verifier/pipeline.py)

---

## 1. What the Citation Verifier Is (and What It Is Not)

To avoid any ambiguity about the system architecture:

| Question | Answer in LuatCheck |
|---|---|
| **Is the Citation Verifier an LLM or a second agent?** | **No.** LuatCheck has only **one** agent controller (Bonsai 4B or 2B). There is no multi-agent critic and no LLM self-critique call inside the verifier. |
| **Is the L1 Citation Verifier a neural network / deep-learning model?** | **No.** The L1 verifier (`lexical_grounding`, v2) evaluated in the D2 report is **100% deterministic, rule-based Python code** (string normalisation, regular expressions, token overlap, and window-bounded numeric matching). |
| **How fast does it run?** | **Under 2 ms per answer** on CPU, with zero GPU/RAM overhead and zero stochasticity. |
| **What about the NLI check (`src/verifier/nli_backends.py`)?** | A separate, optional neural NLI step is implemented in code (`verifier.nli`), but it is **switched off in all D2 benchmark runs** so that the D2 ablation isolates the deterministic rule-based L1 verifier. |

---

## 2. Where the Verifier Sits in the Agent Loop

When the controller emits an `answer` JSON action containing `answer` (Vietnamese prose) and `citations: [{article_id, quote}, ...]`, the control loop (`src/agent/loop.py`) intercepts the draft before returning it to the user and runs the deterministic L1 verifier:

1. **Pass (`is_valid = True`):** All hard checks succeed $\rightarrow$ the answer and its verified citations are returned to the user.
2. **Fail (`is_valid = False`) with repair budget remaining ($\text{repairs\_used} < 2$):** The verifier generates a deterministic structured tool message naming the exact failed check and quoting the closest 170-character passage from the retrieved source document. This report is appended to the conversation as an observation so the controller can revise its answer or quote.
3. **Fail with repair budget exhausted ($\text{repairs\_used} = 2$):** The loop terminates deterministically as a **refusal** (`verifier-exhaustion refusal`) rather than emitting an unverified answer.

---

## 3. The Four Heuristic Checks in Detail

The L1 verifier (`LexicalGroundingVerifierV2` in [`src/verifier/lexical_grounding_v2.py`](../../src/verifier/lexical_grounding_v2.py)) executes **three hard gates** (any failure rejects the draft) and **one soft diagnostic check**:

### Check 1 — Record Existence & Session Retrieval Provenance (Hard Gate)
- **Rule:**
  1. Every cited `article_id` must exist in the loaded corpus (`data/corpus/hcmut_academic_v1.json` or `labour_vi_v1.json`).
  2. Every cited `article_id` must belong to `retrieved_ids` — the set of section IDs actually returned by `search` or `read_document` during the current trial.
- **Why it matters:** Blocks hallucinated document IDs and prevents the model from citing a real article ID from parametric memory without having inspected its text in the current session.

### Check 2 — Normalised Verbatim / Elided Quote Matching (Hard Gate)
- **Text folding (`fold_with_map`):** Both the cited `quote` and the source record are normalised with Unicode NFC, lowercased, stripped of zero-width characters, and unified across typographic quotes (`“ ” « »` $\rightarrow$ `"`), dashes (`– —` $\rightarrow$ `-`), and whitespace (including PDF line wraps).
- **Elision support (`...`, `[...]`, `(...)`):** Legal and academic articles often have long introductory clauses. If the model uses an ellipsis in its quote, the quote is split into segments:
  - Every non-trivial segment ($\ge 12$ characters or $\ge 3$ words) must appear **verbatim and in increasing character order** inside the cited record (tolerating omitted list markers such as `a)`, `1.` after punctuation).
  - **Digit-boundary guard (`_find_bounded`):** A segment starting or ending with a digit cannot match inside a longer number (e.g., `"5 tháng"` is rejected if the source text says `"15 tháng"` or `"3,5 tháng"`).
  - Any numbers inside a short skipped segment must also appear in the cited record.

### Check 3 — Claim-Local Numeric & Unit Verification (Hard Gate)
- **Segmentation into source windows:** Each cited record is split into sentence/clause units ($\le 400$ chars). A *window* is either a single unit, two adjacent units, or a list-introductory sentence paired with one of its bullet items (capped at `MAX_WINDOW_CHARS = 300` characters).
- **Quantity extraction:** For each sentence in the model's answer, the verifier extracts all numeric quantities and domain units (e.g., `28 tín chỉ`, `17.800 đồng/giờ`, `5 phút`, `3,5` normalised to `3.5`).
- **Claim-local matching (`QUANTITY_CONTEXT_TOKENS = 8`):** A quantity in an answer sentence does **not** pass merely because the number appears somewhere in the same article. It must appear inside a source window ($\le 300$ chars) that matches the surrounding $\pm 8$ content words of the claim at least as well as any other window in the cited documents.
- **Why it matters:** Prevents "wrong-clause number borrowing" (e.g., citing the Region III minimum wage when the question asked for Region IV in the same table of Article 3).

### Check 4 — Sentence-Level Content-Token Overlap (Soft Warning, Threshold = 0.50)
- **Rule:** For each sentence in the answer, Vietnamese stopwords and numeric quantities are removed, and the verifier computes the fraction of remaining content words that appear in the best-matching source window:
  $$\text{overlap}(s, w) = \frac{|\text{content\_tokens}(s) \cap \text{tokens}(w)|}{|\text{content\_tokens}(s)|}$$
- **Behaviour:** If $\text{overlap} < 0.50$ (`DEFAULT_SUPPORT_THRESHOLD`), the verifier records a sentence-level warning in the case ledger (`grounding_result.warnings`), while hard rejection is reserved for Checks 1–3. This avoids false rejections when the model paraphrases Vietnamese legal prose while quoting the exact source clause and numbers accurately.

---

## 4. Actionable Repair Feedback Format

When any of Checks 1–3 fails, the verifier constructs a neutral tool report (at most `MAX_FEEDBACK_ITEMS = 2` findings per turn to fit the context budget of small 2B/4B controllers) that includes:
1. Which check failed (`unretrieved_id`, `quote_not_verbatim`, or `unverified_quantity`).
2. For near-miss quotes or wrong numbers, the **closest 170-character verbatim span** (`SPAN_CHARS = 170`) located in the cited record so the controller can copy the exact wording or correct the number on its repair turn.

---

## 5. Known Limitations of the Rule-Based Heuristic (Why Ablations Show Over-Refusal)

In Section 5 of the D2 report, enabling the L1 verifier on top of `no verifier` changes strict success from `70.0%` $\rightarrow$ `64.0%` on HCMUT regulations and `62.0%` $\rightarrow$ `52.7%` on labour law. Our trace analysis shows why:

1. **Verifier-exhaustion refusals on answerable questions:** In `10–13 / 150` HCMUT trials and `14–18 / 150` labour-law trials, the 4B controller found the right article, but its quote formatting or multi-clause number synthesis failed Check 2 or Check 3 twice in a row, forcing the loop to refuse.
2. **Lexical overlap $\neq$ logical entailment:** Because L1 is a lexical/numeric heuristic, it guarantees that every cited section was read, every quote is verbatim in the source, and every number matches the local clause—but it cannot detect a semantic negation or an omitted exception clause if all words and numbers come from the cited sentence.
