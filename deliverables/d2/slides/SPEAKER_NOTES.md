# LuatCheck: speaker notes (10-minute talk, then about 5 minutes of Q&A)

Slides: `main.pdf` (12 presented slides, backup slides A to D that are not presented). Build: `make` in this folder.
Vocabulary used on the slides and here: "initial system" (2B controller), "current system" (4B controller; "current system, 2B controller" when the smaller model is meant), configurations "no verifier" / "verifier" / "verifier + reranker (full system)", "citation verifier", "semantic check (not used yet)", benchmarks "HCMUT regulations" and "Labour law" (50 questions each).
Presenter assignment is not decided: every "Speaker" cell is a placeholder for the team. Rubric: live demo 20%, presentation 15%, Q&A 15%. Total time is exactly 10:00; if running long, shorten slide 6 first, then slide 9.

## Timing

| # | Slide | Time | Cumulative | Speaker |
|---|---|---|---|---|
| 1 | Title and problem | 0:20 | 0:20 | Lê Trí Quyền |
| 2 | What changed since the proposal | 0:45 | 1:05 | Lê Trí Quyền |
| 3 | Architecture | 0:55 | 2:00 | Võ Phạm Tuấn Dũng |
| 4 | Trace of one real question | 0:45 | 2:45 | Võ Phạm Tuấn Dũng |
| 5 | Live demo | 2:30 | 5:15 | Nguyễn Hoàng Phong (Võ Phạm Tuấn Dũng drives keyboard) |
| 6 | Evaluation design and judge | 0:45 | 6:00 | Võ Phạm Tuấn Dũng |
| 7 | First numbers (chart) | 0:55 | 6:55 | Võ Phạm Tuấn Dũng |
| 8 | Current system in detail (verifier, reranker) | 0:35 | 7:30 | Võ Phạm Tuấn Dũng |
| 9 | Cost, latency, parity | 0:40 | 8:10 | Lê Trí Quyền |
| 10 | Threat model | 0:50 | 9:00 | Nguyễn Hoàng Phong |
| 11 | Plan, risks, status | 0:35 | 9:35 | Lê Trí Quyền |
| 12 | Team and takeaways | 0:25 | 10:00 | Lê Trí Quyền |

## Per-slide talking points

**1. Title and problem (0:20)**
- LuatCheck answers only from the loaded regulations, cites sections, checks the citations in code, and refuses or asks when the sources do not answer.
- Two collections: HCMUT academic regulations and Vietnamese labour law. Not legal advice; not tried by real users.
- Everything runs locally; only the offline benchmark judge uses an online API.

**2. What changed since the proposal (0:45)**
- Done: agent loop and citation check; two fixed 50-question benchmarks; reranker evaluated as a configuration.
- Dropped: Qwen3 controllers (Bonsai 2B and 4B instead, so one set of weights runs on a 16 GiB Mac and a GPU); dense retrieval with Qdrant (BM25 + TF-IDF instead; a vector index is built but not evaluated).
- Changed & Done: the verifier audit became a 60-item blind human audit of the LLM judge (96.7% agreement, $\kappa=0.93$ on HCMUT; 90.0%, $\kappa=0.80$ on labour law). HR walkthrough and attack tests are scheduled for W45 and W47.
- Say the evolution once, in plain words: the initial system reached 12 to 19% strict success; we analysed its failures and built the current system with a 4B controller. The revision was designed after analysing the initial system's failures on these same questions, so gains may be optimistic; we confirm them on new questions for the final report. No feedback on the proposal pitch was received.

**3. Architecture (0:55)**
- One agent, one JSON action per step; budget 8 steps, 5 tool calls, 2 repairs, 180 seconds.
- Path: guardrails (regex, before any model call), controller, read-only tools (search, read), BM25 + TF-IDF with rank fusion to the top 20, optional reranker down to the top 5, then the citation verifier (ids, quotes, numbers) with at most two repairs.
- End states: answer with verified citations; refused or clarified; error. A backend failure is an error, never an answer or a refusal.
- Orange boxes are the optional parts we switch on and off in the evaluation. The dashed box is implemented but not used yet (semantic check, vector index, memory).
- Why one agent: permissions and budgets stay inspectable.

**4. Trace (0:45)**
- One question on the HCMUT regulations (student code of conduct). Say it was picked because the judge rated it correct with no repair, not because it is typical.
- Step 1 search (the first search uses the user's own question plus the model's query; 20 candidates, reranked, top 5 kept, the right article first). Step 2 reads the full article. Step 3 answers with one exact quote; the citation verifier accepts with 0 repairs (two soft warnings on one sentence, not rejections).
- 3 model calls, 7,812 tokens in, 598 out. Judge (not a human): correctness 2/2, completeness 2/2.

**5. Live demo (2:30)**
- 0:00 What you will see: local controller, search/read tools, reranker, citation verifier; the strip at the top of the UI shows the active configuration.
- Query 1 (HCMUT) answer: follow the timeline, open the cited section, compare the highlighted quote. Query 2 (labour) same flow on the second collection. Query 3 refusal; mention that a red "execution error" state exists for backend failures. Query 4 injection: guardrail block, no model call.
- Close with one sentence: the demo illustrates; the tables are the evidence; the verifier is a word-overlap check and can pass a wrong answer.
- If something fails: show it as it is (read the cited section, point at the failed check). Backup video: say aloud that it is a recording and explain the trace. If short on time, skip the optional clarification query, then query 2.
- Backup video with the current system (4B controller): `deliverables/d2/demo/gifs/demo_backup_4b.mp4` (recorded 25 October on the Mac, 2 min 37 s: Q1, Q2, a verifier repair, refusal, guardrail). The older clips (initial system, 2B) are secondary backup. Optional: re-record on the presenting laptop.

**6. Evaluation design and judge (0:45)**
- 2 benchmarks of 50 questions (45 answerable, 5 to refuse), 3 configurations, 3 runs with different seeds; two diagnostic baselines (closed-book and oracle) on one run each.
- Strict success is a lower bound: valid judgment, appropriate behaviour, correctness and completeness 2/2, every claim supported; errors and unknowns count as failures; 95% intervals from a paired bootstrap over questions.
- Judge: DeepSeek V4 Flash, blind to the configuration, offline. Reliability check against a 60-item blind human-labelled sample (30 answers per benchmark): strict-success agreement is 96.7% ($\kappa=0.93$, weighted 98.8%) on HCMUT and 90.0% ($\kappa=0.80$, weighted 97.5%) on labour law.
- Limits: questions are AI-drafted and AI-verified; retrieval is near-saturated; 15/45 HCMUT and 12/45 labour answerable questions are estimated to be guessable without the documents; with 50 questions, differences under about 10 points are not detectable.

**7. First numbers (0:55)**
- Chart: full system (verifier + reranker) strict success: initial 14.0 (HCMUT) and 18.7 (labour); current with 2B 28.7 and 28.0; current with 4B 60.7 and 56.7; with 95% intervals.
- System change (current 2B minus initial): +14.7 points [+6.0, +23.3] HCMUT, +9.3 [+0.7, +18.0] labour. Model change (4B minus 2B): +32.0 and +28.7 points.
- Repeat the caveat in one phrase: gains may be optimistic (slide 2), judge lower bounds not human labels, small benchmarks.

**8. Current system in detail (0:35)**
- With no verifier the current system scores highest on strict success (70.0 and 62.0); the verifier and the full system are lower (not significant), and citation F1 drops about 11 points (intervals exclude zero). Faithfulness is unchanged.
- Mechanism: after rejections the model refuses; answerable questions refused after the repair budget ran out: 10 and 13 of 150 HCMUT trials (verifier, full system), 14 and 18 on labour.
- Reranker: Recall@5 is already 0.98 to 0.99 without it, so no effect is detectable. We measured no correctness gain from the verifier; its value is auditable, checked citations.
- Oracle (correct section given) 82.2 and 75.6, closed-book 2.0 and 24.0 bracket the system.

**9. Cost, latency, parity (0:40)**
- Controller tokens per trial for no verifier and full system (about 9,000 to 12,000 in, 700 to 900 out, 3.1 to 3.7 calls); local, no API cost; GPU-active hours not measured.
- Judge cost: USD 1.06 plus 1.10 equals USD 2.17 as reported by the gateway, a lower bound (some attempts report no cost); 36% and 45% of judge attempts were invalid or timed out and retried.
- Reranker parity: the GGUF f16 runtime on the Mac against the torch fp32 CPU reference, Spearman 0.9994, same top-1 in 99 of 100; H100 fp16, 0.9943, 100 of 100. Rank agreement only.
- Mac latency (Apple M4, one question at a time, median / p95): 4B controller 33 s / 86 s (HCMUT) and 30 s / 72 s (labour), about 43 tokens/s; 2B controller 13 s / 30 s and 15 s / 28 s, about 92 tokens/s. GPU wall times are not reported.

**10. Threat model (0:50)**
- Assets: faithful answers, user data, document collections and model weights, the tool boundary, availability. The attacker can send any text; cannot change code, documents, weights, audit log or approval state.
- Per entry point: regex guardrails and untrusted-content tags (questions); tagged tool output and the citation verifier (retrieved text); hashes and offline ingestion (documents, weights); memory off, outbox needs approval bound to the payload hash; the judge is offline and blind.
- Residual risks: paraphrase bypass, an injected instruction inside a source still reaches the model, no signatures.
- No attack results yet; tests are planned for week W47.

**11. Plan, risks, status (0:35)**
- W45 HR walkthrough and a new benchmark of unseen questions; W46 failure analysis; W47 attack tests; W48 reproduction and final report; W49 release and the 2 December presentation.
- Riskiest assumptions: a 2 to 4B controller answers correctly within budget; gains hold on new questions; benchmarks separate the configurations. Fallback: keep the loop, benchmarks, configurations and pipeline; cut the vector index, semantic check and extra domains.
- Owners: Quyền and Phong (W45), Dũng and Quyền (W46), Phong and Dũng (W47), all members (W48–W49). Self-assessment: on track, with one main risk (unconfirmed gain on unseen tasks, to be tested in W45–W46).

**12. Team and takeaways (0:25)**
- Takeaways: 12 to 19% became 57 to 61% for the full system (judge lower bound, may be optimistic); the weak link was the controller's behaviour, not retrieval; the citation verifier gives auditable citations without a measured correctness gain.
- Ask the audience to challenge judge reliability, benchmark difficulty, and gains measured on the same questions. Repository link and commit hash `d74144099016` are on the slide.

## Likely questions and answers

1. **Why no dense (embedding) retrieval?** Retrieval was not the bottleneck: Recall@5 is 0.98 to 0.99 for the current system with or without the reranker, and plain BM25 on the raw question is near the ceiling in an offline check. A dense vector index is built but was not evaluated, and we dropped Qdrant. Caveat: about half the questions name their source document, which helps lexical search; the new benchmark will include a harder slice.
2. **Why do you say the gains may be optimistic? Is the current system overfit?** We designed the revision after analysing the initial system's failures on these same 100 questions. Our plan limited changes to generic design fixes (for example, searching with the user's own question) and ruled out tuning thresholds on the benchmark labels, but we cannot prove there is no leakage. We therefore confirm on new questions for the final report.
3. **How reliable is the judge?** On our 60-item blind human audit (30 items per benchmark), strict-success agreement is 96.7% ($\kappa=0.93$, design-weighted 98.8%) on HCMUT and 90.0% ($\kappa=0.80$, design-weighted 97.5%) on labour law (4 disagreements out of 60 items, documented in `AUDIT_NOTES.md`). Answers are judged blind to the configuration, the judge's quotes are validated against the source and the answer, and 36% and 45% of attempts were rejected as invalid or timed out and retried; invalid or unjudged trials count as failures.
4. **What is the latency on the Mac?** On an Apple M4 (16 GiB, one question at a time, 50 questions per benchmark), the full system takes a median of 33.0 s (HCMUT, p95 86 s) and 29.8 s (labour, p95 72 s) with the 4B controller (about 43 tokens/s), and 13.3 s (p95 30 s) and 14.6 s (p95 28 s) with the 2B controller (about 92 tokens/s). GPU timings came from a shared server and are not reported as latency.
5. **Why does the verifier lower strict success?** After a rejection the model tends to refuse instead of repairing: answerable questions refused after the repair budget ran out were 10 (verifier) and 13 (full system) of 150 HCMUT trials, 14 and 18 on labour. The strict-success differences are not significant (-6.0 [-16.0, +4.0] and -9.3 [-18.7, 0.0] points) but there is no gain, and citation F1 drops about 11 points. We keep the verifier for auditability, not for a measured accuracy gain.
6. **Can the verifier pass a wrong answer?** Yes. It checks ids, quotes and numbers by word overlap. In an earlier demo with the initial system, a labour answer of "60 days" (reference: 10 working days) passed the check. The semantic check exists but is not used yet.
7. **How good are the guardrails?** They are regex patterns for Vietnamese and English, run before the model. A paraphrase can bypass them, there are some false positives, and there are no red-team numbers yet. Defence in depth: the model has no write action and its tools are read-only.
8. **Are the benchmarks hard enough?** Probably not fully. Questions are AI-drafted and AI-verified; 15/45 HCMUT and 12/45 labour answerable questions are estimated to be guessable without the documents (closed-book strict success is 2.0% on HCMUT but 24.0% on labour for the current system); retrieval is saturated; and with 50 questions, differences under about 10 points are not detectable. A harder benchmark of unseen questions is planned.
9. **Privacy: does data leave the machine?** The controller, reranker and retrieval run locally; the demo sends nothing out. Only the offline evaluation sends benchmark questions and answers (no user data) to the judge gateway, with the key taken from the environment. Memory is off in all runs.
10. **What did it cost?** Controller runs are local with no API cost; GPU-active hours were not measured. The judge cost USD 2.17 as reported by the gateway across both benchmarks (a lower bound, not an invoice), about USD 0.002 per valid judgment.
11. **Why does the 4B controller help so much (+32 and +29 points)?** We measured the effect (paired interval [+21.3, +42.0] on HCMUT) but did not test why, so we do not claim a mechanism. The failure analysis shows the initial system's errors were mostly about the controller's behaviour (asking for clarification or refusing instead of answering).
12. **Is the system better than the simplest configuration?** Not on strict success: with no verifier the current system scores highest (70.0 and 62.0). The honest finding is that the verifier and the reranker did not improve correctness on these benchmarks.
13. **Why one agent instead of several?** Permissions, budgets and traces stay inspectable, and the failures we found are in the single controller's behaviour. More agents would add surface without evidence that they help.
14. **Does it work for other domains?** Two collections are evaluated (HCMUT regulations and labour law). Domain specifics (prompt, tool names, id rules, guardrail patterns) sit in configuration. We make no claim beyond these two; a new domain needs its own documents, questions and evaluation.
15. **What if the live demo fails?** We show the failure state (error, refusal) and read the evidence on screen. The backup video of real runs is used only if needed, and we say so. The video was recorded with the current system (4B controller) from real runs, nothing edited; older clips come from the initial system (2B).
16. **What does the reranker parity check show?** The Mac runtime (GGUF f16) against a torch fp32 CPU reference: mean Spearman 0.9994, same top-1 in 99 of 100 questions; H100 fp16: 0.9943, 100 of 100. It shows the runtimes rank alike, not that answers are correct.

## Red placeholders still open on the slides

- None (all presenter roles, weekly plan owners, and the 60-item human audit agreement/$\kappa$ have been filled).

The mapping from every number to its source file is in `SOURCES_INTERNAL.md` (for the team, not for the lecturer).
