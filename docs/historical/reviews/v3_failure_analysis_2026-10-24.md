2026-10-24 15:46 +07

# v3 failure analysis (W2): controller, query construction, observations

Scope: frozen main runs `d2-gpu-main-hcmut-v3` and `d2-gpu-main-labour-v3` (Bonsai 2B, harness 1.1.2, 545 trials each: 3 system variants x 150, closed-book 50, oracle 45). Analysis only; no code, config or data was changed. Every number below is produced by `evaluation/probes/v3_failure_analysis.py` (run with `.venv/bin/python`; the Anaconda python on this Mac has a broken scipy). Retrieval is recomputed with the real `HybridDomainRetriever` (tfidf/BM25+RRF, k=60); it reproduces the ids shown to the model in 374 of 377 re-checked `off` searches (3 HCMUT tie-order differences).

Caveats that apply to everything:
- Judge labels were still arriving (about 410 of 545 per run at 15:44). Where a judged number is quoted it is labelled "provisional" and comes from valid per-attempt files in `judge/attempts/` joined through `private_mapping.json`. Everything else is structural (statuses, actions, ids, lexical coverage of the reference quote) and is a proxy, not correctness.
- "Evidence in view" = at least 80% of the tokens of a task's `reference_evidence.exact_quote` occur in a snippet or full read the model saw. It uses benchmark reference quotes, so it is a diagnostic only; do not tune constants on it (methodology guard 2). The projections marked "projection" are offline simulations with stated assumptions, not measurements.
- Roughly half of the benchmark questions name their source ("Theo Quyết định 1260/QĐ-ĐHBK sửa đổi khoản 3.1 Điều 3": 23/45 HCMUT, 30/45 labour). That inflates the raw-question baseline for retrieval. I report the split with and without such references below; the conclusion holds on both halves.

## 0. Headline

1. The model's clarify is not "asking the user for missing facts". It is the exit taken when the needed text is not in view. With the reference evidence in view, clarify is 17% (HCMUT) / 13% (labour); with it absent (not retrieved, or retrieved but not in the 600-char snippet) it is 57% / 43%. The oracle floor (gold given at step 0) is 16% / 13%. Evidence is in view in only 49% / 51% of single-evidence answerable `off` trials.
2. The cause is upstream of the model: model-written first queries keep 31-32% of the question's IDF mass; the loop silently searches with top_k=3 (the model sets top_k in only 7 of 1,246 searches); the model almost never reads (gold read in full in 17% / 0% of trials) although 65-72% of displayed hits are truncated. Query = original question would raise first-search R@3 from 0.71 to 0.95 (HCMUT) and 0.62 to 0.98 (labour).
3. Under L1 the repair loop converts rejections into refusals: after a feedback message the model refuses in 56% / 53% of cases; only 8-11% of trials with a repair end answered. The repair prompt itself ends with a capitalised instruction to refuse.
4. The five truncated outputs are runaway `thought` strings (2,000-4,600 chars, partly English), not legitimately long answers. 1024 tokens is adequate; the `thought` field is unbounded in the grammar.
5. Prompt/controller contract gaps: "search first" is not enforced (33/450 HCMUT system trials never search); the prompt allows `refuse` only when search finds nothing, but BM25 almost never returns nothing (2 `not_found` in 1,246 searches), so clarify becomes the only exit and 60% of out-of-scope trials end in clarify.

## 1. Clarify overuse

Rates (answerable tasks, per variant; `off` has no L1, so it isolates the controller):

| | HCMUT | labour |
|---|---|---|
| off / l1 / l1_rerank | 37% / 36% / 33% | 30% / 33% / 25% |
| oracle (gold at step 0) | 7/45 = 16% | 6/45 = 13% |
| refuse tasks, system variants | 28/45 = 62% clarify (11 refused, 6 answered) | 27/45 = 60% (14 refused, 4 answered) |

The benchmark contains no task whose expected behaviour is clarify (answer/refuse only), and the questions are fully specified, so every clarify on an answerable task is a miss. Provisional judge labels agree: 116 of 117 judged system clarifies on answerable HCMUT tasks and 89 of 90 on labour got correctness 0; all 16 (HCMUT) and 22 of 23 (labour) judged clarifies on out-of-scope tasks were scored behaviour-inappropriate, while all 6 and 11 judged refusals were appropriate.

When: 72% (36/50, HCMUT `off`) and 70% (28/40, labour) of clarifies come right after the first search; 18% (9/50) of HCMUT clarifies happen before any search. Searches before clarify (HCMUT off): 0:9, 1:36, 2:3, 3:1, 5:1; labour: 0:1, 1:28, 2:6, 4:5. 86% (HCMUT) / 92% (labour) clarify without any read.

What the question says (keyword heuristic over all system variants): of 144 (HCMUT) / 119 (labour) clarifies on answerable tasks, 130 / 97 either ask for "more details" or repeat the user's own question. I read about 70 of them; none requested a situational fact the task lacked. Examples: HCMUT-001 s42 off: "Is this information available in the documents we have access to?" (asks the user whether the corpus has it); LVN-006 s42 off just re-asks "mức đóng bảo hiểm thất nghiệp cụ thể là bao nhiêu phần trăm?"; HCMUT-015 s42 off, gold retrieved, no read: "Vui lòng cung cấp thêm chi tiết về tiêu chuẩn này."

Why: it tracks evidence in view (single-evidence tasks, `off`, n=120 per benchmark):

| state | HCMUT n / clarify | labour n / clarify |
|---|---|---|
| gold not retrieved | 38 / 58% | 44 / 45% |
| retrieved, evidence not in snippet | 23 / 57% | 15 / 40% |
| evidence in view | 59 / 17% | 61 / 13% |

Where answered with evidence in view, provisional judge correctness >=1 is 34/38 (HCMUT) and 26/32 (labour); answered with gold not retrieved is wrong in 3/3 and 13/13 judged. The excess over the oracle (about +21 and +17 points) is therefore mostly the evidence-in-view gap; the remaining 13-17% is the model's own hedging (oracle shows the same).

Nudges in prompt, schema and observations (system defect, partly):
- Principle 1 allows `refuse` only "khi đã tra cứu ... mà không tìm thấy bất kỳ tài liệu liên quan nào". BM25 returns hits for any query (status `not_found`: 1 HCMUT, 1 labour of 1,246 searches), so refuse is almost never licensed; "found something but it does not contain the answer" has no sanctioned action except clarify. Out-of-scope tasks end in clarify 60% of the time.
- Budget rule 5: "Nếu tra cứu 2-3 lần không tìm thấy ... chọn `refuse` hoặc `clarify`" lists clarify as a not-found exit. Labour only: "Nếu thiếu dữ kiện quyết định câu trả lời, chọn clarify" (unrestricted to user facts; HCMUT restricts to student facts yet clarifies more, so wording is not the main driver).
- The action example for clarify is generic ("yêu cầu người dùng cung cấp thêm thông tin cần thiết"); nothing says "never to ask whether the corpus contains X".
- The prompt says truncated snippets must be read before concluding, but the observation only carries `"snippet_truncated": true`; the instruction sits ~2k tokens earlier and is ignored (reads: 33/135 HCMUT, 10/135 labour answerable `off` trials; the duplicate-query notice, which does say "dùng read", is followed by a read 15 of 35 times in HCMUT).
- Observations never show the remaining tool budget. The budget notice appears only after the budget is spent and lists answer/refuse only.
- Not a nudge: the "answer must cite" rule (empty-citation answers are 3-10 per variant and are routed to repair, not clarify).

Fixes: F1, F2, F3, F4, F5 below.

## 2. Query construction

First model query vs BM25 on the raw question (answerable, variants off+l1, trials with >=1 search; HCMUT n=245, labour n=267):

| | R@1 | R@3 | R@5 |
|---|---|---|---|
| HCMUT model query | 0.48 | 0.71 | 0.80 |
| HCMUT raw question | 0.86 | 0.95 | 0.99 |
| HCMUT question+model query concatenated | 0.81 | 0.98 | 1.00 |
| HCMUT RRF(question, model) | 0.68 | 0.88 | 0.96 |
| labour model query | 0.46 | 0.62 | 0.78 |
| labour raw question | 0.81 | 0.98 | 0.99 |
| labour concatenated | 0.77 | 0.98 | 0.99 |
| labour RRF | 0.68 | 0.90 | 0.96 |

The controller effectively sees @3, not @5: the model almost never sets top_k (it is absent in 521 of 526 HCMUT and 718 of 720 labour searches; the rest set 3) and the loop defaults to 3 (`loop.py`: `tool_args.get("top_k", 3)`) although `final_top_k` is 5 and the prompt example shows 3.

Split by whether the question names its source: HCMUT with references (n=128) R@3 model 0.68 vs question 1.00; without (n=117) 0.74 vs 0.89. Labour with (n=178) 0.49 vs 0.97; without (n=89) 0.88 vs 1.00. So the raw question wins on both halves.

How queries differ: 10.2 / 11.0 tokens vs 30.7 / 35.3 for the question; IDF-weighted share of question terms kept 0.31 / 0.32 (median 0.29 / 0.30); of questions containing numbers, the first query drops at least one in 114/125 (HCMUT) and 112/214 (labour); a decision/clause reference survives in 62/125 (HCMUT) and 127/148 (labour) of the questions that have one, so labour queries keep the identifier but lose the content words (R@3 0.49 on those questions). HCMUT: 48/245 first queries copy the institution name from the prompt's `source_name` ("quy chế", "bách khoa", "ĐHQG"); their R@3 is 0.52 vs 0.75 for the others (0.63 after stripping the name). Examples: HCMUT-004's query "Quyết định 1260/QĐ-ĐHBK điều 14.3" keeps the identifiers and loses every content term of a 40-word question; labour: "Nghị định 318/2025 lao động đăng ký bảo hiểm xã hội" retrieves Điều 1-3 of the decree instead of the specific article.

Recovery is weak: after a first-search miss the model searches again in 24% (HCMUT) / 34% (labour) of cases and the gold appears later in 6/66 and 7/89 (9% / 8%). The first query decides.

Projection (offline, real retriever and snippet function, single-evidence tasks, first search only): P(evidence >=80% in the first result) 0.43 (HCMUT) / 0.46 (labour) as run; 0.49 / 0.61 with top_k=5; 0.62 / 0.85 with the question as the query (top 3); 0.73 / 0.90 with 1000-char/3-clause snippets. Applying the two-state clarify rates above (in view 17%/13%, not in view 57%/44%) gives clarify of roughly 32% / 18% (question as query) and 28% / 16% (plus larger snippets), versus 37% / 28% observed on those tasks, i.e. a drop of about 5-10 (HCMUT) and 10-12 (labour) points. This is a rough model, not a measurement.

Fix: F1 (+F2, F9).

## 3. Repair behaviour under L1

Reaction to a repair message (l1 + l1_rerank, all feedback types): HCMUT 109 events: refuse 61 (56%), answer 34, search 8, clarify 4, read 1, none 1; labour 128 events: refuse 68 (53%), answer 39, clarify 12, search 8, none 1. By feedback type the refuse share is similar (quote mismatch 56% / 52%; unsupported claims 57% / 56%), so type is not what drives it. Outcome: trials with >=1 repair end answered 10/90 (HCMUT) and 8/106 (labour); refused 74 and 84. Controller-made "repair exhausted" refusals: 10 per benchmark.

Why the controller invites refusal:
- The repair prompt's last bullet is "bạn HÃY CHỌN HÀNH ĐỘNG `refuse` thay vì đưa ra thông tin chưa được kiểm chứng!" (both profiles); it is the only concrete action offered.
- The feedback is a `user`-role message headed "CẢNH BÁO TỪ HỆ THỐNG ...". The model reads it as the user complaining: 49/85 (58%, HCMUT) and 18/91 (labour) post-quote-feedback thoughts begin "Người dùng ..." (e.g. "Người dùng chỉ trích lại câu trả lời trước").
- The suggested fix ("bỏ trường exact_quote nếu chỉ diễn giải") is rarely taken: of 56 re-answers after quote feedback only 7 dropped quotes; only 6 passed (2/25 HCMUT, 4/31 labour).
- Rejected answers were often on-target: of 70 (HCMUT) / 78 (labour) refusals that followed a rejected first answer, 51 / 50 cited a gold article, and 31 / 16 also contained every number of the expected answer (structural proxy; the judge sees only the final output). Worked example: HCMUT-001 s42 l1 answered the correct "14 học kỳ" with a quote that elided a line break, was told the quote is not in the source, then refused ("Chi tiết '10 10 14' trong snippet không phải là văn bản chính thức").
- Snippets use "[...]" and "..." as joiners, which teaches the model to elide in quotes; the elision is then what L1 rejects (W1 owns the matcher).

Fix: F6 (controller wording only; L1 internals are W1).

## 4. Truncation and `thought` length

Output tokens per call (system variants; HCMUT / labour): mean 211 / 217, p50 161 / 166, p90 395 / 410, p99 683 / 688, max 1024. By action (mean): search 123 / 133, read 162 / 155, clarify 209 / 246, refuse 228 / 271, answer 400 / 378. `thought` is 59-60% of the response characters (mean 405-418 chars, p90 647-682, p99 1,541-2,096, max 2,947-3,643).

Truncations: 5 `model_output_error` (HCMUT l1_rerank 2; labour off 1, l1_rerank 1, oracle 1), 0.2% of calls. All five have 3,000-4,700 raw characters, four are still inside an unterminated `thought` and run into free English reasoning ("... the instruction says 'only one JSON'. I must prioritize accuracy"); the fifth (LVN-004 s42 off) spent a 2,274-char thought before an answer. So 1024 is not too low; raising it would only let runaway thoughts run longer. About 2-3% of thoughts (25 HCMUT, 40 labour) switch to English and 16 contain CJK characters; the sampler (presence_penalty 1.5) is a plausible but untested cause.

Fix: F7 (bound `thought` in the grammar). A cap of 800 chars touches 6-7% of calls and saves about 4-5% of response characters; the gain is robustness, not speed. Dropping `thought` altogether would remove about 60% of generated characters but is a larger protocol change and is not recommended here.

## 5. Search and read observations

- 65% (HCMUT) / 72% (labour) of displayed hits are truncated (`snippet_truncated: true`). With the question as the snippet query, the 600-char/2-clause snippet contains >=80% of the reference quote for 66% / 82% of evidence items; 1000/3 gives 81% / 87%; 1500/3 gives 91% / 91% (offline, benchmark labels, diagnostic only). With the model's real queries it is lower (retrieved but evidence not in the snippet: 23 HCMUT and 15 labour single-evidence `off` trials).
- Tables are not the problem: only 5/143 HCMUT and 0/458 labour records contain numeric-row lines, and 3 tasks per benchmark have digit-heavy evidence (`off` outcomes HCMUT 3 answered / 5 clarified / 1 refused, labour 5 / 3 / 1; small n). HCMUT-001's "10 10 14" snippet kept the column header and was answered correctly (14); the failure was the quote check.
- Titles are the first line of the record: some stop mid-heading (`Điều 5. Nghỉ hưu ở tuổi thấp`), 22 HCMUT titles begin with an opening quote. The snippet code already compensates; harmless.
- HCMUT hits carry the full decision title as `law_name` (mean 507 chars, 18% of an observation). It does carry the decision number, so it is useful, but it costs context.
- Read results are complete: 42/42 HCMUT and 11/11 labour successful reads equal the corpus text. Failed reads are model-typed ids (4 in total: HCMUT_HOCPHI280_Dieu_8, LBL2019_Hoang_25, BLLD2019_2019_Dieu_154, ND293_2025_Dieu_7); the error message gives no candidate id.
- Reading is the real gap: the model reads at all in 24% (HCMUT) / 7% (labour) of answerable `off` trials; 67% / 94% of answered `off` trials never read.

Fix: F3 (visible nudge in the observation), F10 (snippet size, needs dev-set choice).

## 6. Refuse (out-of-scope) tasks and closed-book

Outcomes over 15 trials per variant group: HCMUT system variants: clarified 28, refused 11, answered 6 of 45; labour: clarified 27, refused 14, answered 4. Answered cases are topic substitutions that L1 passes: HCMUT-025 (off) answers a post-grade-appeal deadline question with the fee-extension article ("Theo Điều 7 của Quy định gia hạn thời gian nộp học phí"), LVN-049 answers a maternity benefit rate from the Labour Code Điều 140. L1 verified 3 of 6 and 1 of 4 of these answers. Provisional labels: 3 of 4 judged answered refuse-task trials in HCMUT and 1 of 1 in labour were behaviour-inappropriate.

Clarify questions on these tasks ask the user for the missing content ("Cần cung cấp thêm thông tin nào để giải đáp câu hỏi về mức phạt hành chính ..." LVN-050), 24 of 28 (HCMUT) after exactly one search.

Closed-book (no tools, diagnostic) answers 2/5 (HCMUT) and 3/5 (labour) out-of-scope tasks with invented specifics (an invented URL in HCMUT-049, "Điều 253" in LVN-050); both judged HCMUT closed-book answers on out-of-scope tasks were behaviour-inappropriate. The `refuse` branch is therefore the correct target for out-of-scope tasks, and the controller prompt makes it hard to reach (section 1).

Guardrails: 0 pre-model refusals in all 1,090 trials, so no guardrail false positives (and no evidence about recall; no adversarial tasks here).

Fix: F4; any relevance/support threshold needs calibration on the bll2019 dev set (methodology guard 2) and is not recommended before that.

## 7. Other system defects

- Search-first is not enforced. 33/450 HCMUT system trials (7%) end without any search (16 refused, 15 clarified, 1 answered), labour 3/450. All are failures on answerable tasks.
- Duplicate queries: 35/526 (7%) HCMUT and 71/720 (10%) labour searches repeat a query already issued. The model often repeats it again after the notice (labour: 28 of 67 notices are followed by another search). LVN-005 l1 issued the same query 5 times and then refused; LVN-006 l1 five times. Each notice consumes a tool call and a step; labour: 25 trials spent all 5 tool calls, 13 saw the budget notice, 9 of those ended refused. The duplicate observation returns only `article_ids`, not the earlier hits.
- Budget visibility: the model is never told the remaining tool calls; `[LỖI_NGÂN_SÁCH]` arrives only after exhaustion.
- Mixed refusal sources (no `refusal_source` field exists in `src/` or the runner): "refused" aggregates model refusals (HCMUT 128, labour 98 in system variants), controller repair-exhausted refusals (10 + 10) and controller budget refusals (1 + 2). Reports that read refusal as a model decision should not pool them; the ledger has no `refusal_source`.
- Citation ids and normalisation are fine: 154/154 (HCMUT) and 209/210 (labour) cited ids are ids that were retrieved; no read used a non-canonical id; the single non-retrieved citation was in an `off` trial. Prompt placeholders leak rarely (query "...": 1, "từ khóa tìm kiếm": 1 per benchmark).
- Context: mean input 2.3-2.4k tokens, max 11,088 against `context_tokens: 8192` in the model config; harmless on the 16-slot server (n_ctx 262,144/16 per slot) but any larger snippets or top_k need that checked.
- Corpus note: a few HCMUT hits are chunks that contain another document's letterhead (3% of displayed hits); minor, corpus-side.

## 8. Ranked fixes

Impact per effort, highest first. Every item below changes behaviour that the frozen v3 protocol fixed (prompt text, action grammar, tool observations, retrieval inputs or budgets) and must be labelled a post-hoc revision, except F11. None needs a threshold tuned on hcmut_v1/labour_vi_v1; F10 and any score threshold must be set on bll2019_v1.

| # | Fix | Evidence | Expected impact | Risk | Files | Effort |
|---|---|---|---|---|---|---|
| F1 | On the first search of a run, retrieve with the user's original question concatenated with the model's query (record both in the ledger metadata); later searches stay model-driven. Domain-agnostic. | R@3 0.71 to 0.98 (HCMUT), 0.62 to 0.98 (labour); evidence-in-view after first search 0.43 to 0.62 / 0.46 to 0.85; recovery after a miss only 8-9% | Largest. Projected clarify -5 to -12 points; also removes the wrong-evidence answers (13/13 judged wrong when gold not retrieved) | Less "agentic" search; benchmark questions often cite sources, so the gain is partly lexical (it holds on the no-reference half); shrinks the reranker gain | `src/agent/loop.py` (`_act_search`), `src/tools/domain_tools.py` (`search_with_metadata`), `src/config/app_config.py` (flag in `RetrievalConfig`) | S |
| F2 | Default `top_k` to `retrieval.final_top_k` (5), not 3 | model never sets it; R@3 to R@5 +0.09 / +0.16 on model queries | Moderate alone, small on top of F1 | About +600 tokens per search | `src/agent/loop.py` line 325-328 | XS |
| F3 | Put the action cue next to the data: each search observation states how many hits are truncated and tells the model to `read` before concluding, and carries `tool_calls_remaining`. New generic message keys (not edited existing ones) | reads in 17% / 0% of trials for gold; 65-72% hits truncated; 43% of duplicate notices (which say "read") were followed by a read | High on the "retrieved, evidence not in view" bucket (23 + 15 trials, clarify 40-57%); full read gives 100% evidence | More reads use budget (5 calls); acceptable | `src/tools/domain_tools.py`, `src/domains/profile.py` (`PACK_MESSAGES`), `config/domains/messages/vi.yaml` | S |
| F4 | Fix the clarify/refuse contract in the prompts: refuse also when the retrieved text does not contain the answer; clarify only for facts about the user's situation, never to ask whether the corpus has something or to restate the question; drop clarify from the "2-3 searches" rule. Optional one-time controller gate: first clarify with no read and budget left returns a notice and does not end the run | 90% / 82% of clarifies are generic or echo; refuse unreachable (2 `not_found` in 1,246); 60% of out-of-scope trials clarify | Moderate to high on out-of-scope (refuse correct, clarify never credited) and on residual clarify; may move some to wrongful refusals | Wording-sensitive for a 2B model; check on dev set | `config/domains/hcmut_academic.yaml`, `config/domains/labour_vi_multi.yaml` (do not edit the frozen `labour_vi_2019.yaml`), `src/agent/loop.py` (`_act_clarify_or_refuse`) | S |
| F5 | Enforce search-first: reject a first-step answer/clarify/refuse with a notice, or restrict step 0 to the search action (existing `restrict_actions` grammar) | 33/450 HCMUT trials never search, all misses | Up to 7% of HCMUT trials; labour about 1% | Low | `src/agent/loop.py`, `src/agent/llm_client.py` | S |
| F6 | Repair framing: deliver verifier feedback with a tool/verifier prefix rather than as a user complaint; drop the capitalised "HÃY CHỌN refuse" line or pair it with "đọc lại nguồn bằng read / bỏ exact_quote" | refuse 56% / 53% after feedback; 58% HCMUT thoughts begin "Người dùng"; 8-11% of repaired trials answered | Moderate under L1; independent of W1's matcher | May let wrong answers survive if L1 stays lenient; judge before/after | `config/domains/*.yaml` (`repair_prompt`), `src/agent/loop.py` (`_act_answer`) | XS |
| F7 | Bound `thought` in the action grammar (about 800 chars, near p90; verify the PrismML llama-server honours `maxLength`); keep `max_output_tokens` at 1024 | 5 truncations all runaway thoughts; p90 of thought is 650-680 chars | Removes the 5 execution errors (0.2% of calls); saves only about 4-5% of response characters (6-7% of calls are affected at 800) | Grammar support in the fork unverified; slightly less room for reasoning | `src/agent/llm_client.py` (`_action_branch`) | XS |
| F8 | Do not charge `duplicate_query` and `already_read` to the tool budget; on duplicate return the earlier hits compactly | 71 labour duplicates, up to 5 repeats; 9 budget refusals | Small (about 3% of labour trials) | Needs a loop guard (steps already bounded at 8) | `src/agent/loop.py` (`_act_search`, `_act_read`) | S |
| F9 | Query guidance in the prompt: keep the question's own identifiers, numbers and terms; do not add the institution or code name | HCMUT 48/245 queries with the name: R@3 0.52 vs 0.75; 114/125 numeric refs dropped | Small once F1 is in; useful for later searches | Prompt sensitivity | the two profile YAMLs | XS |
| F10 | Larger query-aware snippet (for example 1000 chars / 3 clauses), as a profile setting rather than class constants | evidence coverage 66-82% to 81-87% (diagnostic) | Moderate for in-view rate, costs about 400 tokens per hit | Context growth; choose size on bll2019_v1 | `src/tools/domain_tools.py` (`SNIPPET_CHARS`, `SNIPPET_CLAUSES`) | S |
| F11 | Record `refusal_source` (model, repair_exhausted, tool_budget, step_budget, guardrail) and the first-search hit in trial rows. Not benchmark-visible | 20 + 3 controller refusals pooled with model refusals | Cleaner reporting only | None | `src/agent/loop.py` (`_refuse`), `evaluation/run_benchmark.py` | XS |

Suggested bundle for the revised run: F1+F2+F3+F5+F4+F6+F7 first (they act on different failure buckets), then F8/F9, with F10 only if the dev-set check supports it. To attribute effects honestly under the plan's "2B isolates the system fix", run the 2B ablation as at least {baseline v3, F1+F2+F3, all of them}. Edit copies of the two profiles under new ids rather than in place, so v3 stays reproducible by id (the runs also keep `source_snapshot/`). `config/domains/messages/vi.yaml` is shared with the frozen `labour_vi_2019` profile: add new keys, do not reword existing ones.

## 9. Not verified

- Final judge labels (the numbers above are provisional and partial); the judge sees only the final output, so L1-rejected first answers are assessed only by the structural proxy.
- Whether the PrismML llama-server enforces `maxLength`/`minItems` in the JSON-schema grammar.
- The sampler (presence_penalty 1.5, temperature 0.7) as a cause of English/CJK drift and repeated queries.
- The effect sizes in the projection; they assume the conditional clarify rates stay fixed when evidence is made visible.
- Whether the 4B controller shares these failure modes; nothing here was run on 4B.

## 10. Reproduce

`.venv/bin/python evaluation/probes/v3_failure_analysis.py all` (sections: overview, clarify, queries, repair, tokens, snippets, refuse, defects, evidence, judged, extras). It reads the two run directories and benchmark tasks only.
