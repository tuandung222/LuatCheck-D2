# LuatCheck: Speaker Notes (10-Minute Presentation + ~5 Minutes Q&A)

Slides: `main.pdf` (12 main slides, plus Backup Slides A to D). Build: `make` in this folder.
Terminology used across the slides: **Bonsai 4B controller (default)**, **Bonsai 2B controller (lightweight)**, configurations **No verifier** / **Verifier** / **Verifier + reranker (full system)**, **rule-based L1 citation verifier** (deterministic Python heuristic, not a model or second agent), and benchmarks **HCMUT regulations** and **Labour law** (50 questions each).
Rubric weights: live demo 20%, presentation 15%, Q&A 15%. Total target time is 10:00; if running long, shorten Slide 6 first, then Slide 9.

## Timing

| # | Slide | Time | Cumulative | Speaker |
|---|---|---|---|---|
| 1 | Title and System Overview | 0:20 | 0:20 | Lê Trí Quyền |
| 2 | Changes Since the D1 Proposal | 0:45 | 1:05 | Lê Trí Quyền |
| 3 | System Architecture: Offline Indexing and Bounded Agent Loop | 0:55 | 2:00 | Võ Phạm Tuấn Dũng |
| 4 | Execution Trace on a Sample HCMUT Query | 0:45 | 2:45 | Võ Phạm Tuấn Dũng |
| 5 | Live Demo: LuatCheck on a 16 GiB Mac | 2:30 | 5:15 | Nguyễn Hoàng Phong (Võ Phạm Tuấn Dũng drives keyboard) |
| 6 | Evaluation Protocol and Metrics | 0:45 | 6:00 | Võ Phạm Tuấn Dũng |
| 7 | Controller Scaling: Bonsai 2B vs. Bonsai 4B | 0:55 | 6:55 | Võ Phạm Tuấn Dũng |
| 8 | Component Ablation: Impact of the Citation Verifier | 0:35 | 7:30 | Võ Phạm Tuấn Dũng |
| 9 | Cost, Latency, and Runtime Environment | 0:40 | 8:10 | Lê Trí Quyền |
| 10 | Threat Model | 0:50 | 9:00 | Nguyễn Hoàng Phong |
| 11 | D3 Roadmap, Key Risks, and Project Status | 0:35 | 9:35 | Lê Trí Quyền |
| 12 | Key Takeaways and Team Contributions | 0:25 | 10:00 | Lê Trí Quyền |

## Per-Slide Talking Points

**1. Title and System Overview (0:20)**
- LuatCheck answers regulatory questions strictly from loaded local documents, cites the supporting provisions, verifies every citation in Python before returning an answer, and refuses or asks for clarification when the corpus does not support a conclusion.
- Evaluated on two corpora: HCMUT academic regulations (10 documents, 143 sections) and Vietnamese labour law (10 documents, 458 sections). Research prototype, not legal advice.
- All inference runs locally on a 16 GiB laptop; only the offline benchmark judge uses an external API.

**2. Changes Since the D1 Proposal (0:45)**
- Completed: bounded agent loop with rule-based citation check; two fixed 50-question benchmarks; Vietnamese cross-encoder reranker evaluated in the ablation matrix.
- Adjusted: replaced Qwen3 4B/8B and 32B models with ternary-quantised Bonsai 4B (default) and Bonsai 2B (lightweight) served via `llama.cpp`, so the exact same weights run on a 16 GiB Mac and on our evaluation GPU.
- Retrieval uses BM25 + 1–3-gram TF-IDF fused by RRF plus the cross-encoder reranker; the dense vector index is implemented and scheduled for ablation in Week 46.
- Verifier calibration was conducted as a 60-item blind human audit of our offline LLM judge: 96.7% agreement ($\kappa=0.93$) on HCMUT and 90.0% ($\kappa=0.80$) on labour law. HR walkthrough and attack tests follow in Weeks 45 and 47.

**3. System Architecture: Offline Indexing and Bounded Agent Loop (0:55)**
- Two-phase architecture:
  - **Phase 1 (Offline Ingestion & Indexing):** Official PDFs are extracted, normalised to Unicode NFC, segmented into 143 HCMUT and 458 labour sections with SHA-256 and page provenance (`data/corpus/`), and indexed into an in-memory BM25 + TF-IDF index.
  - **Phase 2 (Online Bounded ReAct Loop):** Budgeted to at most 8 steps, 5 tool calls, 2 repairs, and 180 seconds. Input guardrails screen requests before any model call; the controller selects one constrained JSON action (`search`, `read`, `answer`, `clarify`, `refuse`) per step; `search` runs BM25 + TF-IDF RRF (top-20) and cross-encoder reranking (top-5), while `read_document` loads the full section from the normalized corpus.
- Every proposed `answer` is checked by the **rule-based L1 citation verifier** (`<2 ms` Python heuristic checking session retrieval provenance, normalised verbatim/elided quotes, and claim-local numbers) with up to 2 repairs.
- Terminal states: verified answer, refusal/clarification, or explicit execution error (a backend or budget failure never produces a fallback answer).

**4. Execution Trace on a Sample HCMUT Query (0:45)**
- Real recorded trial on HCMUT regulations (student code of conduct, Decision 1924/QĐ-ĐHBK).
- Step 1 (`search`): combines the user's question with the model's query; 20 candidates are reranked to the top 5, placing Article 6 first. Step 2 (`read_document`): loads the full text of Article 6. Step 3 (`answer`): cites Article 6 with an exact quote; the L1 verifier accepts on the first pass (0 repairs).
- Total: 3 model calls, 2 tool calls, 7,812 input tokens, 598 output tokens; offline LLM judge scores 2/2 correctness and 2/2 completeness.

**5. Live Demo: LuatCheck on a 16 GiB Mac (2:30)**
- Show the active status strip at the top of the Web UI: corpus selector, Bonsai 4B controller (`:8081`), BM25 + TF-IDF + reranker (`:8082`), and L1 citation verifier.
- Query 1 (HCMUT): follow the live step timeline, expand the cited section (`Điều 9`), and inspect the highlighted verbatim quote.
- Query 2 (Labour law): switch corpus and run the minimum-wage query (`Nghị định 293/2025/NĐ-CP`, `Điều 3`).
- Query 3 (Out-of-scope): weather question triggers an explicit refusal (`Từ chối: nguồn không đủ căn cứ`).
- Query 4 (Prompt injection): pre-model regex guardrail blocks the input in ~3 ms with zero model calls.
- Backup recording (`deliverables/d2/demo/gifs/demo_backup_4b.mp4`, recorded 25 October on the 4B controller) is available if a local service fails.

**6. Evaluation Protocol and Metrics (0:45)**
- Primary D2 evaluation goal: verify that the end-to-end agentic pipeline and evaluation harness run reliably and produce reproducible baseline measurements across configurations; broader improvements and experiments are scheduled for D3.
- 2 benchmarks of 50 questions each (45 answerable, 5 out-of-scope refusals) $\times$ 3 configurations (`No verifier`, `Verifier`, `Verifier + reranker`) $\times$ 3 random seeds, plus `Closed-book` and `Oracle` diagnostic baselines (1,090 recorded trials per controller).
- Strict success is a conservative lower bound (execution errors and invalid judge outputs count as failures). Blind 60-item human audit confirms 96.7% ($\kappa=0.93$) and 90.0% ($\kappa=0.80$) agreement with the DeepSeek V4 Flash judge.

**7. Controller Scaling: Bonsai 2B vs. Bonsai 4B (0:55)**
- Comparing the lightweight 2B controller and default 4B controller on the full system (`Verifier + reranker`): strict success increases from 28.7% to 60.7% (+32.0 pp) on HCMUT regulations and from 28.0% to 56.7% (+28.7 pp) on labour law.
- Across all three configurations, scaling from 2B to 4B adds +24.7 to +40.0 percentage points, and all six 95% paired bootstrap confidence intervals exclude zero.

**8. Component Ablation: Impact of the Citation Verifier (0:35)**
- Looking only at the prose-only LLM judge (`judge %`), `No verifier` appears higher (70.0% and 62.0%) because the LLM judge does not verify whether cited quotes or numbers exist verbatim in the PDF.
- When we audit every emitted answer with deterministic L1 checks (`leak %` and `audited %`), **25.6% (31/121) of HCMUT answers and 28.0% (37/132) of labour answers under `No verifier` leak unverifiable citations** (non-verbatim quotes, unretrieved IDs, or wrong-clause numbers), and the LLM judge mistakenly credits 22 (HCMUT) and 16 (labour) of them.
- Enabling the rule-based L1 verifier **reduces unverified citation leakage to 0.0%**, corrects 17–20 rejected first drafts via bounded 2-turn repair, and **raises citation-audited strict success from 55.3% to 60.7–64.0% (+5.4 to +8.7 pp) on HCMUT and from 51.3% to 56.7% (+5.4 pp) on labour law**.
- Oracle (82.2% and 75.6% on the 45 answerable questions) and closed-book (2.0% and 24.0%) bracket the system.

**9. Cost, Latency, and Runtime Environment (0:40)**
- Local inference incurs USD 0 API cost (about 9,000–12,000 input tokens and 670–865 output tokens over 3.1–3.7 model calls per trial).
- Offline LLM judging across both 545-trial runs cost USD 2.17 total (USD 1.06 HCMUT and USD 1.10 labour).
- Sequential single-query latency on an Apple M4 MacBook (16 GiB): median 33 s (p95 86 s) on HCMUT and 30 s (p95 72 s) on labour law with the 4B controller (~43 tok/s); 13 s (p95 30 s) and 15 s (p95 28 s) with the 2B controller (~92 tok/s).

**10. Threat Model (0:50)**
- Five protected assets: faithful answers/citations, user data, corpus/weights/config integrity, read-only tool boundary, and local availability.
- Code-enforced boundaries per entry point: pre-model regex guardrails and untrusted tags on inputs; tagged tool outputs and L1 provenance/quote verification on retrieved text; SHA-256 provenance on corpora and weights; long-term memory disabled and outbox gated by host UI approval bound to payload SHA-256.
- Residual risks are stated transparently; systematic red-team attack evaluation is scheduled for Week 47 (D3).

**11. D3 Roadmap, Key Risks, and Project Status (0:35)**
- W45: HR walkthrough and freezing the harder unseen multi-hop/paraphrased benchmark.
- W46: Running full ablations + dense vector retrieval ablation on the unseen benchmark, plus verifier false-reject analysis.
- W47: Entry-point red-team prompt-injection and fault tests.
- W48–W49: Reproduction verification, final report, tagged release, and Round 1 presentation on 2 December.

**12. Key Takeaways and Team Contributions (0:25)**
- Three takeaways: (1) Scaling from 2B to 4B lifts full-system strict success from ~28% to 57–61%; (2) controller synthesis and citation discipline, rather than lexical retrieval (Recall@5 $\approx 0.99$), is the main bottleneck; (3) the rule-based L1 citation verifier eliminates unverified citation leakage (26–28% $\to$ 0.0%) and improves citation-audited strict success by +5.4 to +8.7 pp.
- Equal 33% contribution across all three members, with responsibilities mapped to repository modules and Q&A topics.

## Likely Questions and Answers

1. **Why is dense (embedding) retrieval not enabled in the main D2 table?** Lexical retrieval (BM25 + 1–3-gram TF-IDF with RRF) already achieves Recall@5 of 0.98–0.99 on these 100 questions, so retrieval was not the bottleneck at D2. The dense vector index is implemented in `src/indexing/` and will be ablated on the harder unseen paraphrased benchmark in Week 46 (D3).
2. **Why does `No verifier` have a higher judge-only strict success score (70.0% / 62.0%) than the full system (60.7% / 56.7%)?** Because the offline LLM judge grades answer prose without checking whether the cited quote or number actually appears verbatim in the PDF. Under `No verifier`, 25.6% (31/121) of HCMUT answers and 28.0% (37/132) of labour answers contain broken citations (fabricated/altered quotes, unretrieved IDs, or wrong-clause numbers), and 22 (HCMUT) and 16 (labour) of those broken-citation answers were still marked correct by the LLM judge. When we require both LLM-judge correctness and a valid citation (`Citation-Audited Strict Success`), the L1 verifier reduces unverified citation leakage to 0.0%, repairs 17–20 flawed drafts, and increases accuracy from 55.3% to 60.7–64.0% on HCMUT and from 51.3% to 56.7% on labour law.
3. **What is the main limitation of the L1 citation verifier?** Two trade-offs: (i) after two failed repair turns on an answerable question, the loop conservatively refuses (13/150 HCMUT and 18/150 labour trials in the 4B full system), and (ii) because L1 is a deterministic lexical/numeric heuristic rather than a semantic entailment model, it cannot catch a wrong interpretation if the quote and numbers are copied verbatim from the cited clause. Reducing repair-budget over-refusals and testing L2 NLI are part of our D3 work.
4. **How reliable is the offline LLM judge?** On a stratified blind sample of 60 outputs (30 per benchmark), human–judge agreement on strict success is 96.7% ($\kappa=0.93$, weighted 98.8%) on HCMUT and 90.0% ($\kappa=0.80$, weighted 97.5%) on labour law. All 4 disagreements out of 60 items are documented item-by-item on Backup Slide A.
5. **What is the interactive latency on a laptop?** On an Apple M4 MacBook (16 GiB, single-query sequential execution), median / p95 latency for the full system is 33.0 s / 86 s (HCMUT) and 29.8 s / 72 s (labour law) with the 4B controller (~43 tokens/s), and 13.3 s / 30 s and 14.6 s / 28 s with the 2B controller (~92 tokens/s).

Provenance mapping from every reported table to its recorded run is in `deliverables/d2/report/RESULTS_PROVENANCE.md` (verified by `make report-check`).
