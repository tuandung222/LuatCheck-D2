# D2 slide outline (10-minute talk, then about 5 minutes of Q&A)

Written 2026-10-23 (UTC+7) for the presentation on Wed 28 Oct 2026, 18:00, room B4-305. Slide PDF is due with the report (before 23:59 Sun 25 Oct).
Status: outline only; no slide file exists yet. Everything marked `[PENDING ...]` is filled from the main-run tables or by the team, never invented.

Ground rules for every slide (AGENTS.md, rubric B2/B3):
- The current system runs the same model for the reported numbers and the demo: Ternary Bonsai 2 4B (GGUF PQ2_0); a 2B controller is the lighter option. Put that on the architecture slide once. The built deck is deliverables/d2/slides/main.pdf.
- Strict success, behaviour and faithfulness are LLM-judge estimates (not human labels) until the human-audit agreement is known; retrieval and citation numbers are source-ID proxies.
- Benchmarks are AI-written and AI-verified (no human review); retrieval is near-saturated, about one third of tasks are closed-book guessable. Say this on the evaluation slide.
- Show red `[PENDING]` on a slide rather than a number we do not have. The old Qwen2.5-3B / ten-task results never appear.
- Time is exactly 10:00 (rubric B2 says "exactly 10 minutes"): rehearse twice with a timer; cut slide 4 first if running long.

## Time plan and speakers

| # | Slide | Min | Cumulative | Speaker |
|---|---|---|---|---|
| 1 | Title and problem | 0:30 | 0:30 | [PENDING: member] |
| 2 | What changed since the proposal | 0:50 | 1:20 | [PENDING: member] |
| 3 | Architecture that runs end to end | 1:10 | 2:30 | [PENDING: member] |
| 4 | Tools, permissions, memory, knowledge | 0:40 | 3:10 | [PENDING: member] |
| 5 | Live demo | 2:30 | 5:40 | [PENDING: member] (second member drives the keyboard) |
| 6 | Evaluation design and judge | 1:00 | 6:40 | [PENDING: member] |
| 7 | First numbers, cost, latency, failures | 1:10 | 7:50 | [PENDING: member] |
| 8 | Threat model | 0:50 | 8:40 | [PENDING: member] |
| 9 | Plan, riskiest assumption, honest status | 0:50 | 9:30 | [PENDING: member] |
| 10 | Close and what we ask the audience to challenge | 0:30 | 10:00 | [PENDING: member] |

Every member should speak at least once and be able to answer on their part (announcement section 5): [PENDING: ownership map retrieval/reranker, loop/verifier/evaluation, tools/security/UI, from the team].

## Slides

### 1. Title and problem (rubric B2)
- LuatCheck: a local assistant that answers only from loaded regulations, cites sections, checks citations, refuses when the sources do not answer.
- Two evaluated corpora: HCMUT academic regulations (10 documents) and Vietnamese labour law (10 documents). Not legal advice.
- Everything runs locally except the offline judge.
- Visual: logo, one-line scenario. Group 8, members.

### 2. What changed since the proposal (rubric A4/B2; report Section 1)
- Done / in progress / dropped / not started (the commitments table): loop and L1 done; Qwen3 and Qdrant dropped; reranker and benchmark in progress.
- Why: the controller is a small ternary model (4B, with a 2B option) so the same weights run on a 16 GiB Mac and on a GPU; benchmark moved from 10 tasks to two frozen 50-task benchmarks, one of them a second domain.
- Honest items: no pitch feedback received, HR walkthrough not started.
- Figure/table: report Table 1 (shortened to 6 rows). Do not show the old Qwen pilot.

### 3. Architecture that runs end to end (rubric A1/B2; report Section 2)
- One bounded agent: 8 steps, 5 tool calls, 2 repairs, 180 s; one JSON action per step.
- Pipeline from one YAML: guardrails, controller, search/read, BM25 + TF-IDF/RRF, optional reranker, L1 verifier, ledger. Dashed: L2/NLI, vector index, memory (implemented, outside D2).
- Backend failure is an error, never a refusal or an answer.
- Figure: report Figure 1 (full slide). One-sentence why single agent, not multi-agent.
- Trace: show one real trial (report Table 2) [PENDING: trial id from main run]. If no trace exists by 28 Oct, say so and show the live demo's timeline instead.

### 4. Tools, permissions, memory and knowledge (rubric A1; report Sections 3-4)
- Read-only tools only reach the model; writes are proposal-only and gated by a trusted UI approval bound to the payload hash.
- Reranker is a read-only model component; failure is an execution error.
- Memory exists but is off in all D2 runs; corpora: 143 and 458 records with source URL, SHA-256, pages.
- Figure/table: report Table 3 (tool permissions) as a compact version. First slide to cut if over time.

### 5. Live demo (rubric B1, 20%; see DEMO_SCRIPT.md)
- Four queries: HCMUT answer with citations; labour answer with citations; a refusal; an injection blocked before the model.
- What to point at: action timeline, retrieved ids, cited section text, L1 verdict, tokens and seconds.
- Backup: video of the same flow plus screenshots (checklist in DEMO_SCRIPT.md; draft recordings of real runs are in `deliverables/d2/demo/gifs/`, including the execution-error state). Say aloud if a fallback is used.
- Start the demo with `make demo-web` (corpus switch in the UI); the final query set and live outcomes are in DEMO_SCRIPT.md section 3.
- Same model and config as the tables.

### 6. Evaluation design and the judge (rubric A2/B2; report Section 5)
- 2 benchmarks x 3 variants (OFF / L1 / L1+rerank) x 3 seeds x 50 tasks = 900 trials; accuracy on server 82, latency on the Mac.
- Strict success = lower bound over all trials, errors count as failures; paired bootstrap over tasks; closed-book strata.
- How correctness is decided: DeepSeek Flash judge, blind to variant; reliability checked against a human-labelled sample (about 30 items per benchmark, Sat 24 Oct): agreement and kappa [PENDING: human audit].
- Honest limits: tasks are AI-drafted and AI-verified; retrieval saturated; about one third guessable.
- Figure/table: report Table 5 (metric definitions), trimmed to four rows.

### 7. First numbers, cost, latency and failures (rubric A2/B2; report Section 5)
- Main table: strict success, behaviour, retrieval, citation F1 per variant [PENDING: report Table "benchmark-main" from the main run].
- Paired differences with 95% intervals [PENDING]; say that differences under about 10 pp are not detectable with 50 tasks per benchmark.
- Cost and latency: judge USD, tokens per trial, p50/p95 on the Mac [PENDING: ops and Mac latency tables]; GPU-active hours are not measured, only device wall time.
- Failures: error kinds and two or three concrete failed tasks [PENDING: failure analysis].
- Say plainly if variants do not differ; that is a finding about the benchmark as much as about the system.

### 8. Threat model (rubric A3/B2; report Section 6)
- Assets: answer faithfulness, user data, corpora/config/weights, tool boundary, availability, judge credential.
- Untrusted entry points: question, pasted document, retrieved text, ingested PDFs, memory, config/weights, judge-gateway egress (offline); web browsing N/A.
- Attacker can send text; cannot change code, corpora, weights, or approval state.
- Mitigations with file pointers; residual risks stated (observations tagged but not filtered; paraphrase bypass). No attack results in D2.
- Figure/table: report threat-model table, shortened to 5 rows.

### 9. Plan, riskiest assumption and honest status (rubric A4/B2; report Section 7)
- Weeks W45-W49: HR walkthrough, harder benchmark slice, failure analysis, attack tests, reproduction, release 2 Dec. Owners [PENDING: team confirmation].
- Riskiest assumption: a 2B controller must answer correctly within budget and the benchmarks must be hard enough to separate variants; fallback keeps loop, benchmarks, variants, pipeline.
- Self-assessment: at risk (provisional) [PENDING: re-assess after main run and audit].
- What is done vs measured vs planned, in one line each.

### 10. Close (rubric B2/B3)
- Three takeaways drawn from the numbers [PENDING: from main run].
- What we want challenged: judge reliability, benchmark difficulty, Bonsai capacity.
- Repo URL and commit hash [PENDING: final commit hash].

## Backup slides (not presented, used in Q&A)
- B1: benchmark provenance chain and QA findings B1-B4 (report Section 5).
- B2: metric definitions and strict-success rule (`evaluation/judge_rules.py`).
- B3: reranker parity (MaxP input policy, torch fp16 vs GGUF) [PENDING: parity numbers].
- B4: per-member ownership and what each member verified [PENDING: team].
- B5: error taxonomy and the trace table.

## Rubric coverage check

| Criterion | Weight | Slides |
|---|---|---|
| B1 Live demo | 20% | 5 (+ backup video) |
| B2 Presentation (changes, running architecture, demo, numbers and cost, threat model, plan and risks, honest completion) | 15% | 2, 3, 5, 7, 8, 9, 10 |
| B3 Q&A (evidence-based, each member, limits admitted) | 15% | 6, 7 limits; backup slides; ownership map |
| A1-A5 (report) | 50% | slides mirror report Sections 1-8 |
