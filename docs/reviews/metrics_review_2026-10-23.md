# Metrics and D2-scenario review

Written 2026-10-23 22:25 +07 (UTC+7). Author: EVALUATION implementer. Scope: `evaluation/` metric code as it is after this change, the D2 collection plan
(`docs/plans/D2_COMPLETION_PLAN.md`), and the benchmark QA findings of `docs/reviews/benchmark_quality_2026-10-23.md` that change how numbers must be read.
Everything below was checked against the code and against recorded runs (`evaluation/runs/bench-smoke-both-20261023`, `evaluation/runs/bench-smoke-evalimpl-20261023`);
statements that are estimates or assumptions say so. Nothing here is a result of the D2 main runs, which do not exist yet.

## 0. Summary

* The headline quantity is **strict success** (LLM-judge estimate: behaviour appropriate, correctness 2, completeness 2, every claim supported), reported as a **lower bound over all planned
  trials** (execution errors, judge-unknown and missing trials count as failures) with a task-level bootstrap 95% interval. That definition was already sound; what was missing or wrong is listed in section 3.
* Retrieval Recall@k / MRR are **near ceiling by benchmark construction** (the QA review found the gold record in BM25's top 5 for 45/45 hcmut and 44/45 labour questions). They will barely separate
  `off`, `l1` and `l1_rerank`; do not use them to claim a reranker benefit. A gold-free saturation indicator (`share_full_recall_at_5`) is now in every cell.
* About one third of answerable tasks are answerable closed-book (QA finding B2). Strict success is now also reported stratified by closed-book guessability
  (`config/benchmark/strata.yaml`, LLM-estimated strata, not labels).
* Paired differences between variants (`l1` vs `off`, `l1_rerank` vs `l1`) use a **paired bootstrap over tasks** (seeds averaged per task); with 50 tasks per benchmark only differences of roughly 10 percentage points
  or more can be detected (section 5.2).
* The Mac and the GPU server do **not** run the same `l1_rerank` system (GGUF Q8_0 over llama.cpp vs torch fp16 cross-encoder, different truncation); accuracy tables must say which run each number
  comes from and the two machines' `l1_rerank` rows must not be pooled (section 5.4).

## 1. Metric catalogue: definition, validity, comparison with practice

Notation: a **trial** is one (benchmark, variant, seed, task) row of `trials.jsonl`; a **cell** is (benchmark, variant). "Answerable" = the frozen task has gold ids. `category` is task metadata:
**`single` does not imply one gold id** (LVN-014/016/019 are `single` with two gold records), and no metric here derives the number of gold ids from the category.

### 1.1 Answer quality (LLM judge) - `evaluation/judge_benchmark.py`, rubric `evaluation/judge_prompt.txt`

| Metric | Exact definition (code) | Valid here? | Research / production practice |
|---|---|---|---|
| **Strict success** (`strict_success`, rule in `evaluation/judge_rules.py`) | per trial: execution error -> False; judge invalid or `judgeable=false` -> unknown (None); else `behaviour_appropriate and correctness==2 and completeness==2` and the claim condition: for **answer outputs** every claim is `supported`; for **abstention outputs** (expected_behavior refuse, or the candidate refused / asked to clarify) claims labelled `not_established` are ignored and no claim may be `contradicted`. Cell rate = successes / **planned** trials (lower bound); upper bound adds unknowns; `rate_known_only` = successes / known. | Yes. Conservative (a single unsupported claim fails the trial). Zero claims is vacuously "all supported", which is right for a justified refusal and relies on correctness==2 for an answer. | Answer correctness by an LLM judge against a reference (Zheng et al. 2023, "Judging LLM-as-a-Judge") is standard; counting failures/timeouts as failures is the production notion of **task success**. The strict all-claims-supported conjunction is stricter than usual (most RAG papers report correctness and faithfulness separately). |
| **Behaviour appropriate (judge)** | `judgment.behaviour_appropriate` rate over `{execution errors (counted inappropriate)} + {judgeable outputs}`; unjudged/invalid trials are outside the denominator. | Yes, but the denominator excludes unknowns, so read it with the `unknown` count. | Answer / refuse correctness as in answerability work (SQuAD 2.0 no-answer; over-refusal in XSTest, Rottger et al.). The structural counterpart is in 1.3. |
| **Claim faithfulness** | micro: supported claims / all claims over judgeable outputs (`claims` = atomic factual claims extracted by the judge, refusals included). New `rate_macro_over_trials`: mean over trials of supported/claims (trials with claims). | Yes. Micro is dominated by long answers; macro is the per-answer view. Not defined when an output has no claims. | RAGAS "faithfulness" = supported claims / claims; ALCE (Gao et al. 2023) measures citation quality by NLI entailment of the cited passage instead. Ours is judge-assigned support against the full gold + cited records, which is closer to RAGAS. |
| **Judge reliability** | `evaluation/score_benchmark_audit.py` (new): percent agreement and Cohen's kappa (judgeable, behaviour, correctness/completeness nominal and linear-weighted, all-claims-supported, strict success) judge vs human, per reviewer and pooled, design-weighted variants for the stratified sample, bootstrap CIs. No numbers without valid labels. | Yes. The audit sample is stratified on judge outcome, so unweighted agreement describes the sample, not the population; weighted figures are given when stratum sizes are available. | Human calibration of the judge (kappa, Cohen 1960) is the accepted check; sample size matters more than the statistic (30 per benchmark gives wide intervals, reported). |

**Historical numbers.** `evaluation/analyze_judge.py` (the old 10-task `bll2019` D2 analysis, OFF 10/30 and ON 11/30 strict success in `evaluation/runs/deepseek-judge-main-v1/analysis-retry-v2`) used the same all-claims-supported rule. It is left unmodified on purpose (its hash is recorded in those frozen summaries). Re-scoring those 60 recorded judgments offline with the new rule changes 0 of them, so the reported old numbers stand; `report_d2` was not touched.

**Judge limitations that no metric can remove** (stated, not fixed): one judge model (`deepseek/deepseek-v4-flash`, gateway-routed, revision not pinned), single judgment per packet (no repeated-judge variance), validation failures in about 30% of attempts (see 5.3).

### 1.2 Retrieval and citation (ID-based proxies; gold ids read after the trial, never shown to the agent) - `evaluation/metrics.py`

| Metric | Exact definition | Valid here? | Practice |
|---|---|---|---|
| **Recall@k, Hit@k, MRR, nDCG@5, trace_recall, read_recall** (`trial_retrieval_metrics`) | The agent's **trace** = distinct ids in first-appearance order: search hits in the order the tool returned them (successive searches concatenated), then ids added by reads. Recall@k = share of gold ids among the first k distinct ids; MRR = 1/rank of the first gold id; nDCG@5 binary relevance; `trace_recall` = Recall@infinity; `read_recall` = gold ids the agent explicitly read. Over answerable trials; execution errors stay in (a failure to retrieve); `non_error_*` repeats the key values without them. | Valid as "did the agent surface the evidence". **k is across the whole trajectory, not the rank inside one search result**, and with 1.0 searches per trial (smoke) it is nearly a single-search ranking. **Saturated**: see `share_full_recall_at_5`. Not the retriever's quality in isolation (the agent chooses queries). Reads are rare (about 0.1 per trial in the smoke runs), so `read_recall` is low. | BEIR-style Recall@k / nDCG@10 / MRR are computed per query on a fixed query set; an agent trace is a different object. For `l1_rerank` the ledger also stores first-stage candidates, giving `rerank_first_stage_gold_recall` (upper bound) vs `rerank_returned_gold_recall`. |
| **Citation precision / recall / F1** (`trial_citation_metrics`, `aggregate_citation`) | cited = distinct ids in the final answer's citations. precision = cited-and-gold / cited (**undefined, not 0, when nothing is cited**); recall = cited-and-gold / gold; F1 = harmonic mean, 0 when nothing matches. Cell level: `macro_*` (nothing cited = 0, so refusing/erroring is penalised), `precision_when_cited`, `micro_*`, plus gold-free `cited_not_retrieved_rate` (cited an id the agent never surfaced) and `spurious_citation_rate_on_refuse`. | Valid as a **source-ID proxy**. It under-credits valid alternative sources (the judge accepts them, the ID metric does not; QA note HCMUT-030) and says nothing about whether the answer is right. Labelled "ID proxy" in every table caption. | ALCE defines citation recall/precision by entailment, not by id match; id match is the cheap, reproducible proxy. |
| **Lexical unsupported proxy** (`lexical_unsupported_proxy`) | fraction of answer sentences (>15 chars) for which the agent's own L1 verifier says "not supported by the cited records"; 1.0 when an answer has no citation. | Only a proxy for the verifier's own signal. **Never** shown as correctness; reported only inside `lexical_proxy` and labelled. | n/a |

### 1.3 Behaviour and abstention - `behaviour_confusion`

Structural confusion matrix, expected (`answer` | `refuse`, from the frozen task) x actual terminal status (`answered | refused | clarified | error`), no judge involved. Derived rates (errors excluded from rates, reported separately):
`answer_coverage`, `over_refusal_rate` = (refused+clarified)/non-error answerable, `unsafe_answer_rate` = answered/non-error refuse tasks, `refusal_recall` (strict: clarification is not a refusal), `abstention_recall` (lenient),
`refusal_precision`, `refusal_f1`, `strict_match_rate_all` (errors count as mismatches). The benchmarks have no expected "clarify", so `clarified` is always abstention and never a match.
Practice: answerability/abstention is reported as precision/recall of the refusal class plus over-refusal on answerable inputs (XSTest). A risk-coverage curve (selective prediction) would need a confidence score, which the controller does not produce; not computed.

### 1.4 Operations - `latency_metrics`, `error_profile`

| Metric | Definition | Notes |
|---|---|---|
| Trial latency p50/p95 | wall time of `agent.run` (retrieval + reranker + controller calls + verifier). Headline over **non-error** trials; `trial_all_*` over every trial incl. timeouts. | Percentiles are numpy linear interpolation; with n < 100 per cell p95 is near the maximum (n is printed). Reportable only for `mac-latency` (sequential); the GPU run's latency is recorded under concurrency and printed `n/r`. Warm-up trials are executed before each agent's first recorded trial and are kept in `warmup.jsonl`, outside every metric. |
| Per-LLM-call latency p50/p95 | wall time of each successful controller request. | Server-side `prompt_ms`/`predicted_ms` also give decode and prefill tokens/s (excluding cached prompt tokens) and the cached-prompt share. |
| Non-model time | trial wall minus controller-call wall (retrieval, rerank, verifier). Reranker call p50/p95 from the ledger. | |
| Tokens | controller input/output tokens per trial from the server's usage (trials with complete usage only), calls per trial, tool calls, repairs. | |
| Cost per query | **Controller: not an API cost** (local; energy and device-hours not measured, never reported as zero). Judge: gateway-reported usage cost per attempt (not an invoice), also per valid packet. | Production practice would add energy / GPU-hours; unmeasured here and said so. |
| Error rate | execution errors / trials with Wilson 95% interval, by `error_kind`, timeouts counted separately. Errors **fail** strict success but are never hidden inside it. | |
| Task consistency | per task: all seeds succeed / all fail / mixed; seed mean +- sd of the cell rate. `all_seeds_success` is the tau-bench-style pass^k reliability measure (k = number of seeds). | |

### 1.5 Intervals and comparisons - `evaluation/stats.py`

* Cell CI: percentile bootstrap (5000 draws, fixed seed 20261023) over **tasks**, each task's value = mean over seeds. Seeds of one task are not independent samples of the task population, so resampling trials would give intervals that are too narrow.
* Variant differences (`config/benchmark/variants.yaml: comparisons`): paired bootstrap of treatment - baseline over the tasks present in both variants, per benchmark and pooled; reports difference, 95% CI, units better/worse/tied, and a bootstrap two-sided p-value (resampling approximation; no multiple-comparison correction, stated in the table caption).
* Error rates: Wilson interval.

## 1.6 Diagnostic baselines (closed-book and oracle)

Two no-tool baselines run in the same run, with the same Bonsai controller file, sampler, domain system prompt, constrained JSON decoding (action schema restricted to answer / clarify / refuse), verification off, **one seed (42)**, judged by the same judge (`evaluation/baselines.py`, definitions in `config/benchmark/variants.yaml: baselines`, which also holds the disclosed one-paragraph note appended to the domain prompt: no tools, only answer/clarify/refuse):

| Baseline | Gets | Tasks | Trials | What it measures |
|---|---|---|---|---|
| `closed_book` | the question only | all 50 per benchmark | 100 | share of the score that is parametric knowledge (a floor any retrieval system must beat; also over-refusal / unsafe-answer behaviour without evidence) |
| `oracle` | the question plus the **full text of the gold records**, rendered by the real read tool and put in the user turn as `[OBSERVATION_TOOL_RESULT]` blocks (passive data, like every observation) | answerable tasks only, 45 per benchmark (**refuse tasks have no gold context and are excluded**) | 90 | the reading / reasoning ceiling of a 2B controller with perfect retrieval and no tool-use burden |

Rules: baselines are separate cells (`arm: baseline`), have their own table (`tab:benchmark-baselines`), are **never pooled** with the system variants and never enter the paired comparisons; the baseline table carries the system variants as *reference rows* restricted to answerable tasks (`answerable_only`) so the comparison is like for like. Retrieval metrics are not applicable (the oracle is given gold; closed-book gets none) and are reported as null. Citation P/R vs gold ids is meaningful for the oracle (it must cite the ids it was given); for closed-book it is not shown. The oracle uses gold by design: `OracleBaselineAgent.uses_gold` is the single entry point of gold ids into an agent call, and a test whitelists exactly that class. 190 extra trials per machine profile; judge about $0.5; negligible GPU time, about 20 min on the Mac.

**Reading them (error decomposition).** For the answerable tasks, with S = strict success of a system variant, O = oracle strict success, C = closed-book strict success:
* `C` is the parametric floor; combined with the closed-book strata (section 2) it shows how much of a system's score on guessable tasks is not grounding.
* `O` is an upper bound for the same reader: `O - S` is what retrieval, tool use and verification cost the system relative to perfect evidence (a 2B model cannot beat its own reading ceiling by retrieving better).
* Inside a system variant, `answerable_by_gold_surfaced` splits answerable trials by whether the agent surfaced all gold ids: success given surfaced is the reading+tool-use part, trials where gold was missed are retrieval/search failures. Because retrieval is near ceiling (section 2), most of `O - S` will then be reading under longer, noisier context and tool-use errors, not retrieval.
* Caveats: one seed (sampling noise is not averaged, interval is over tasks only); the baselines see a different prompt (disclosed addendum) than the system variants, so `O - S` mixes evidence access with that prompt difference; the oracle prompt contains full records (longer context than a search snippet), which is also what a read action would give; LLM-judge estimates throughout.

## 2. What the benchmark QA review changes about reading the numbers

1. **Saturated retrieval (B1).** Do not claim a retrieval or reranker benefit from Recall/MRR/nDCG. The honest statements these data can support are about answer-level metrics, behaviour, errors and latency. `share_full_recall_at_5` is printed so the ceiling is visible.
2. **Closed-book guessable items (B2).** `strict_success` is also split into `guessable` (a strong model answered correctly without the corpus), `not_guessable` (partially correct or unsolved closed-book) and `refusal_task`. The strata are LLM estimates from the closed-book probes named in `config/benchmark/strata.yaml`; a test checks the lists against the verdicts in those files and their sha256. Success on guessable items measures parametric knowledge as much as grounding.
3. **Invalid labour closed-book column (B4).** `evaluation/benchmark_sanity.py` no longer hard-codes the HCMUT prompt; prompts are templates in `config/benchmark/sanity_prompts.yaml` filled with the benchmark's domain-profile `display_name`. The old labour `labour-sanity-final-v1` closed-book numbers must not be quoted; the labour strata come from the QA agent's neutral-prompt probe. The hcmut strata come from the old run whose prompt was correct for that domain. The new default closed-book prompt is the neutral one (no "say you do not know if unsure"), so a re-run is not byte-comparable with the old hcmut column; the strata do not depend on a re-run.
4. **Truncation test inside `l1_rerank` (QA MINOR).** Seven hcmut tasks have the answer span beyond the first ~3,000 characters of a long record; a 1024-token reranker cap can hide it (see 5.4 for the Mac/GPU difference).
5. **Decision-number pins (B3)** and metadata (`doc_code`, `review_status`) do not affect any metric but belong in the report's limitations.

## 3. Bugs and gaps found in the previous metric/runner code, and what was done

| # | Finding | Action |
|---|---|---|
| 1 | Citation precision was 0.0 when nothing was cited and was then averaged, so abstaining looked like imprecision; no F1; legacy function returns recall 1.0 for "no gold id". | New `trial_citation_metrics` (precision undefined when nothing cited), macro/conditional/micro aggregates, F1; legacy function kept for `run_eval.py`, documented. |
| 2 | Latency percentiles were computed over non-error trials only (survivorship bias: timeouts vanish from p95). | Both views reported (`trial_all_*`), per-call and non-model times, decode/prefill tokens/s. |
| 3 | `report_eligible` was false whenever a single judge packet stayed invalid after 3 attempts (about 3% of packets expected), so the run could never feed the report. | Extra judge rounds (`judge_extra_rounds`); remaining unknowns are explicit (`unknown_trials`, dagger in tables, counted as failures) and no longer block eligibility; never-attempted packets, incomplete collection and source drift during a session still do. |
| 4 | Collection stopped after 5 consecutive `backend_error` rows and `--retry-errors` retried them all, but a **healthy server answering HTTP 400/500 for one oversized prompt** is not an outage: five such trials in a row would have killed the run, and retrying is pointless. | Each error row gets `error_diagnosis` (failing component, `/health` of that component right after the failure, HTTP status). Only dependency-down rows count toward the stop and are retried. Row `error_kind`/message are never altered. |
| 5 | A killed process leaves a truncated last JSONL line; `read_rows` crashed and resume was impossible. | Truncated tail is ignored for reading and moved to `trials.jsonl.partial-<time>` on resume; a corrupt middle line raises. |
| 6 | Resume drift detection hashed every `evaluation/*.py`, `Makefile` and `config/**`: editing analysis code or an unrelated config file blocked a resume, while an edit of a file read lazily at agent construction (domain profile, prompts) during an uninterrupted run went unnoticed. | Drift set = `src/**`, the run's profile/variants/model/expected-server/warm-up configs, collection modules, benchmark files, corpus and domain profile. Checked on resume, and **before every agent construction** (a changed file stops the run); changes during a session make the run non-eligible. |
| 7 | Reranker backend was fixed in `variants.yaml` (`cross_encoder`) for every machine. | Runtime comes from the run profile (`llamacpp_http` on the Mac, torch fp16 `cross_encoder` on CUDA); the variant keeps `enabled/top_k_in/top_k_out/max_length`; conflicts and a missing runtime are config errors. |
| 8 | No identity checks: nothing recorded or enforced which llama.cpp build / GGUF / reranker weights served a run. | `config/benchmark/expected_server.yaml` (GGUF sha256, quantisation, llama.cpp commit 73bfe6c, reranker revision and weights sha256); preflight refuses a mismatch; manifest `fingerprint` (must-match vs may-differ) and `run_d2.py compare`. |
| 9 | Seeds: the request payload does carry `seed` (set per trial), but nothing showed that the server honours it. | Preflight seed canary (4 real completions): see 5.1. |
| 10 | YAML trap: an unquoted `off` is `False`, which silently broke any matrix written as a list. | `d2_matrix.yaml` quotes it; a test asserts the strings. |
| 11 | No time-boxing of a hung trial beyond the agent's wall budget; no warm-up exclusion. | Per-trial watchdog thread (`trial_timeout_seconds`, discards the agent), warm-up trials outside every metric. |
| 12 | Bootstrap was 2000 draws with the unit mean of the lower bound only; no paired comparison. | `stats.py`: 5000 draws, fixed seed, paired bootstrap, Wilson, kappa. |
| 13 | Closed-book sanity prompt hard-coded to HCMUT (QA B4). | Prompts from config + domain profile (above). |
| 15 | **Correct refusals counted as failures.** The judge listed the refusal sentence ("Không có thông tin ... trong các văn bản đã tra cứu") as a claim labelled `not_established`, and strict success required all claims supported: 3 of 12 smoke trials (behaviour appropriate, correctness 2, completeness 2) failed only for that reason; the same distortion hit claim faithfulness (refusals pulled it down). | (a) `judge_prompt.txt` and the protocol: a refusal / abstention / absence-of-information statement is not a factual claim and is not listed. (b) `judge_rules.py`: for abstention outputs `not_established` claims are ignored (also in faithfulness) and `contradicted` still fails; behaviour, correctness 2 and completeness 2 are still required. Known limit: an invented assertion inside a refusal that the judge labels `not_established` is not penalised by the claim check, correctness==2 is then the only guard. The human audit follows the same counting rule (reviewers leave the refusal sentence out of total/unsupported claims) and the audit scorer applies the rule to the judge side. Re-scoring the recorded smoke judgments offline (no new judge call): strict successes 0 -> 3 of 12 (`labour_vi_v1/off` 0->1, `labour_vi_v1/l1` 0->1, `hcmut_v1/l1` 0->1, `hcmut_v1/off` 0->0 with 1 unknown); nothing that is not an abstention changed. The smoke judgments themselves were produced under the old prompt; a run judged under the new prompt is expected to list fewer such claims, the rule makes the score independent of that. |
| 14 | Retrieval metric on the trace ranks only the first k distinct ids of a concatenation of searches. | Documented as a trajectory metric (above); per-search ranking is unavailable for non-reranking variants because the ledger stores only counts for them (a `src` change would be needed: record returned ids per search in the audit event). |

## 4. Added (all cheap, all recomputed from the recorded ledgers so old runs gain them too)

Retrieval trace metrics (Recall@k, Hit@k, MRR, nDCG@5, trace/read recall, rerank first-stage vs returned recall, saturation share, gold-count distribution); citation P/R/F1 and groundedness checks; behaviour confusion matrix with abstention rates;
error profile with Wilson intervals and timeouts; latency per trial and per call, decode/prefill tokens/s, cached-prompt share; seed spread, task consistency (pass^k style); strata (closed-book) success and stratified paired differences;
paired bootstrap for the configured comparisons; judge-vs-human agreement scorer; independent recomputation of the headline counts (`RUN_NOTES.md`); `progress.json` with ETA.

## 5. D2 collection scenario

### 5.1 Trial count and what the three seeds mean

2 benchmarks x 50 tasks x 3 variants x 3 seeds = **900 system trials** per machine profile plus **190 diagnostic-baseline trials** (closed-book 2 x 50, oracle 2 x 45, seed 42; section 1.6) = 1,090 (`config/benchmark/d2_matrix.yaml`; a test asserts the 900).

**Is sampling seeded?** Yes: `LlamaCppLLMClient.generate` adds `"seed": <int>` to the `/v1/chat/completions` payload when `llm_client.seed` is set, and the runner sets it per trial (`execute_trial`); the same seed is used for every controller call of a trial, together with temperature 0.7, top_p 0.8, top_k 20, min_p 0, presence_penalty 1.5. Evidence from real runs:
* preflight canary (4 real completions, seeds 42, 42, 123, 42): different seeds produced different text in every canary I ran (4 runs); the same seed gave identical text on an idle server and **different text once, while other processes were using the server's slots** (the run is flagged by a `seed_reproducible` warning). So: the seed selects a sampling stream, results are reproducible when the server is not shared, not bit-reproducible under concurrent load or across hardware.
* two independent smoke runs (seed 42, same 12 tasks x `off`/`l1`, different machine load): the `off` variant produced identical token totals in both (4790 in / 503 out per trial, mean of 6); `l1` differed slightly (6289/621 vs 6298/632).
* `off` and `l1` produce the **same output until the first L1 repair** (identical token counts on tasks where L1 never fires): common random numbers, which makes the paired comparison efficient. `l1_rerank` changes the retrieved order, hence the prompts, hence its random stream decouples after the first search.

**Are 3 seeds meaningful?** They measure and average the controller's sampling variance (temperature 0.7 is large for a 2B model, so one seed is a noisy draw per task). They do **not** add independent tasks, so the confidence interval is task-based. Rule of thumb (planning estimate, assumes about 30% of tasks differ between two variants): a paired difference of strict success over 50 tasks has a standard error near 8 pp (95% CI about +-15 pp), over the 100 pooled tasks about 5.5 pp (+-11 pp). Differences under roughly 10 pp are not detectable; report them as such.

### 5.2 Cost and time (extrapolations from recorded smoke runs; not measurements of the full run)

| Item | Basis | Estimate |
|---|---|---|
| Judge spend (900 system + 190 baseline packets) | $0.0464 for 26 attempts / 18 valid packets (`bench-smoke-both`), $0.0326 for 17 attempts / 12 valid packets (`bench-smoke-evalimpl`) = $0.0026-0.0027 per valid packet incl. failed attempts | 1,090 packets about **$2.8-2.9** (baselines about $0.5; guard: `max_judge_usd` 6.0) |
| Judge time | median attempt 45-49 s (max 119 s), 1.45 attempts per valid packet, 8 concurrent | about **2.7 h**; 1.3 h with `--judge-concurrency 16` (not tested against gateway rate limits) |
| Mac collection (idle machine) | `bench-smoke-both`: mean trial 7.4 s (`off`), 8.8 s (`l1`), 12.2 s (`l1_rerank` with the former CPU/MPS reranker) | 900 system trials about **2.4 h** idle plus about 20 min for the 190 baseline trials (one call each, no search; estimate); the shared-machine smoke averaged 15 s/trial (about 3.8 h): the machine must be idle, preflight now refuses a busy machine for `mac-latency` |
| GPU collection | not measured; assumes a 2B model decodes several hundred tokens/s per slot on an H100 and 8 slots | order of **15-40 min** (labelled guess; the real figure comes from `progress.json`) |

### 5.3 Failure modes and how the runner handles them

| Failure | Handling |
|---|---|
| Controller server down / crash | Row = execution error (`backend_error`), never an answer or refusal; health probe marks it an outage; after 5 consecutive outage rows the run stops with rows kept; resume with the same command retries outage rows (new `attempt`, old row kept). |
| Reranker server down (Mac) | `ModelComponentError` -> execution error row, component diagnosed as `model_component`; preflight refuses to start when `8082` is down. |
| Per-request timeout (60 s) / task wall budget (180 s) | agent returns `wall_timeout` error row (a result, not retried). |
| Hang the agent cannot see | watchdog (`trial_timeout_seconds` 300): `runner_trial_timeout` row, agent discarded, run continues. |
| Prompt too long for the server | HTTP 400/500 from a healthy server: error row with diagnosis `dependency_healthy_after_error: true`, not an outage, not retried. Largest controller input seen: 3,944 tokens per call; the 19.6k-character record (HCMUT-034..037, 047) is the likely maximum. Both servers use unified KV (default), so one sequence may use the whole `-c`: runbook uses 131072 on the GPU (`-np 8`, 16384 per slot) and 65536 on the Mac. |
| Model returns invalid action JSON / truncated | `model_output_error` row (counted as failure). The 768-token cap produced such errors in an earlier smoke; `max_output_tokens` is 1024. |
| Process killed (OOM, tmux closed, SIGKILL) | rows are fsync'd per trial; truncated tail repaired on resume; SIGTERM/SIGINT finish in-flight trials and stop cleanly. |
| Code/config edited during the run | stop before the next agent is built; resume refuses; run not eligible. |
| Server swapped between sessions (different GGUF/build/sampler) | resume refuses (fingerprint). |
| Judge: invalid JSON/quote validation (about 30% of attempts, mostly "quote absent from supplied source") | 3 attempts, then `judge_extra_rounds` more rounds of 3; residual packets are `unknown` (failure in the lower bound, listed). Retries add a disclosed line because the gateway returns identical completions for byte-identical requests. |
| Judge gateway unreachable / key missing on the machine | stage reports `judge_unavailable` (exit 6), collection and tables still complete; run `make judge RUN=...` where the key exists. Cost guard refuses above `max_judge_usd`. |
| Judge model identity drift | returned model id recorded per attempt, mismatch with the allowed list is fatal for that packet; the revision is not pinned (disclosed). Judge all runs in one sitting. |
| Disk full | preflight requires 2 GB; a run is about 150-250 MB of ledgers. |

### 5.4 What would make numbers incomparable (and what is done about it)

1. **Different reranker runtime on the two machines (now the same input policy).** Mac: GGUF f16 of the pinned `AITeamVN/Vietnamese_Reranker` revision served by llama.cpp (`llamacpp_http`); GPU: torch fp16 cross-encoder, batch size 1. Both apply the same policy in the client (1500-character windows with 200 overlap, document score = max over windows, `max_length` 1024 tokens cut with the runtime's own tokenizer; `docs/plans/reranker.md`), so long records (QA: answer span beyond ~3,000 characters in 8 tasks) are reachable on both. Measured parity of the two runtimes on the benchmark candidate sets: Spearman mean 0.994 (min 0.960), top-1 agreement 0.99, max |score difference| 0.126 logit. They are the same system up to that numerical noise, not bit-identical; the identity of each runtime (GGUF sha256 pinned in `expected_server.yaml`, or weights revision + safetensors sha256) is checked by preflight and recorded in the fingerprint (`may_differ`: runtime; `must_match`: policy). Still report accuracy from one run (GPU) and latency from the Mac run.
2. **Different llama.cpp builds / kernels.** Same commit enforced by preflight (73bfe6c), but CUDA and Metal kernels for PQ2_0 differ numerically; seeds therefore do not give identical text across machines. The two accuracy/latency runs are statistical replicas, not twins.
3. **Parallelism.** Eight slots batch requests; batch composition perturbs floating-point results (see the canary). Per-trial latency under concurrency is not a latency measurement (`n/r`).
4. **Context capacity** (`-c`): Mac `PRISM_CTX` default 32768 vs 131072 on the GPU: only matters for pathological prompts (>32k tokens); runbook raises the Mac to 65536 for the latency run and the error profile lists any rejection.
5. **Prompt drift.** System prompt, tool descriptions and messages live in the domain-profile YAML, hashed in the benchmark lock and in the collection set; chat template sha256 and sampler defaults are compared in the fingerprint; no date or clock is injected into prompts (checked).
6. **Software versions.** torch/transformers/sentence-transformers versions are recorded in `manifest.hardware.packages` and compared by `run_d2.py compare`; they can change reranker numerics.
7. **Judge drift between sessions.** One judge, unpinned revision; judge all runs of a table together.
8. **Prompt cache.** Sequential Mac runs reuse cached prompt prefixes (about 66% of prompt tokens in the smoke); this is part of the measured latency and is identical across variants, but trial order matters (variants alternate per task) and warm-up is excluded.
9. **Machine load on the Mac.** The shared-machine smoke measured 37-62 decode tokens/s vs 97-99 idle. `mac-latency` now has `require_idle`: preflight refuses a busy machine unless `--allow-busy` (recorded), and the run notes carry start and end load.

### 5.5 Recommendations (implemented unless stated)

Implemented: profile-driven reranker runtime; identity pinning and refusal on drift; fingerprint + `compare`; seed canary; per-trial watchdog; outage-aware error handling; warm-up; idle-machine guard; narrower drift set with in-run protection; extra judge rounds and spend guard; paired comparisons with bootstrap; strata and saturation reporting; independent recomputation in `RUN_NOTES.md`.
Not implemented (needs a decision or a `src/` change):
1. (done by the reranker agent and wired here) `max_length` and chunking parity between the Mac and GPU rerankers.
2. Record the ids returned by every search in the audit event (also for non-reranking variants) so Recall@k can be computed per search rather than over the concatenated trace - `src/` change.
3. A shared reranker instance across the 8 GPU workers (now one copy per worker, about 1.1 GB each in fp16) - `src/` change, optional.
4. Repeat-judging a random 5% of packets to measure the judge's own variance (about $0.12) - not run; easy to add.
5. Pin the judge model revision if the gateway offers it.

## 6. Smoke evidence for this change (pipeline check, not report evidence)

`make benchmark-smoke` (hcmut_v1 + labour_vi_v1, variants off and l1, 3 tasks, seed 42, mac-latency, shared machine, load average about 7): 12 trials, 0 execution errors, 2 warm-up trials per agent kept apart, judge 17 attempts for 12 packets (one packet needed an extra round), gateway-reported cost $0.0326, total wall 10 min 24 s; independent recomputation of the headline counts matched. Details: `evaluation/runs/bench-smoke-evalimpl-20261023/RUN_NOTES.md`.
