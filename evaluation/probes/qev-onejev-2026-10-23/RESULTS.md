# Official Qev / OneJev servers: re-ranking and NLI probe (23 Oct 2026)

## Caveats (read first)

- **Tiny sample**: 9 answerable queries x 20 stored first-stage candidates; 29 NLI pairs. One query moves Recall/MRR by 0.11, one pair by 0.034. This is a probe, not a benchmark.
- **NLI labels are constructed from source text by the earlier probe author, not human labels** (27 constructed + 2 real model outputs, same pairs as `evaluation/probes/rerank-nli-2026-10-23`).
- **Remote shared GPU**: both models run on GPU server 82 (shared, other users' load unknown) behind an SSH tunnel; latencies include the network and queueing and are NOT comparable with the local MPS timings. The model runs remotely, not on this Mac.
- **Probabilities are rounded to 6 decimals by the server**, so near-certain candidates tie; ties are reported (stable tie-break = first-stage order, as the backend does; pessimistic/optimistic bounds below).
- **Not report evidence.** Rank metrics on gold article IDs only; nothing here is a reviewed answer-correctness result. Do not copy into D2 report tables.
- Option/candidate order bias (the model reads letters A/B/C in a fixed order) was not tested.
- The `/v1/models` listing of each server answers to every OneJev alias; the `/health` `model` field is the only reliable identity (checked by the client).

## Servers

| server | base_url (SSH tunnel) | /health | Qev version |
|---|---|---|---|
| 0.8B | http://127.0.0.1:18001 | {"status": "ok", "model": "OmniJev/OneJev1.6-0.8B", "fork_mode": "batched", "prompt_version": "qev-labels-v2"} | 0.1.4 (OpenAPI info.version of qev_openapi_18001.json) |
| 4B | http://127.0.0.1:18004 | {"status": "ok", "model": "OmniJev/OneJev1.6-4B", "fork_mode": "batched", "prompt_version": "qev-labels-v2"} | 0.1.4 (OpenAPI info.version of qev_openapi_18001.json) |

## Experiment A: re-ranking the stored first-stage top-20 (9 tasks)

Per-candidate `noul` yes/no question, state `{query, document}` (full article text, nothing truncated); score = P(yes). Stable tie-break; `[pess., opt.]` = bounds if ties are resolved against/for the gold article.

| System | Recall@1 | Recall@3 | Recall@5 | MRR | MRR [pess., opt.] | median ms/req (client) | p95 ms | server-side median ms | status |
|---|---|---|---|---|---|---|---|---|---|
| first stage (HybridDomainRetriever tfidf) | 0.778 | 0.944 | 1.000 | 0.944 | - | - | - | - | stored |
| local AITeamVN/Vietnamese_Reranker (mps float16) | 0.889 | 0.944 | 1.000 | 1.000 | - | 116 (local) | 262 | - | earlier probe |
| local Qwen/Qwen3-Reranker-0.6B (mps float16) | 0.889 | 1.000 | 1.000 | 1.000 | - | 296 (local) | 622 | - | earlier probe |
| Qev OneJev1.6-0.8B [en] | 0.667 | 1.000 | 1.000 | 0.889 | [0.889, 0.889] | 462 | 876 | 51 | ok, 0 errors |
| Qev OneJev1.6-0.8B [vi] | 0.667 | 0.944 | 1.000 | 0.889 | [0.889, 0.889] | 470 | 824 | 51 | ok, 0 errors |
| Qev OneJev1.6-4B [en] | 0.667 | 0.889 | 0.889 | 0.840 | [0.840, 0.840] | 516 | 918 | 85 | ok, 0 errors |
| Qev OneJev1.6-4B [vi] | 0.611 | 0.889 | 0.889 | 0.785 | [0.785, 0.785] | 508 | 866 | 82 | ok, 0 errors |

Wording: `en` = "The document contains information that directly answers the query"; `vi` = "Tài liệu chứa thông tin trả lời trực tiếp cho câu hỏi truy vấn".

### Per-task gold ranks (stable tie-break; `absent` = not in top-20)

| Task | first-stage | 0.8B en | 0.8B vi | 4B en | 4B vi | Vietnamese_Reranker | Qwen3-Reranker-0.6B |
|---|---|---|---|---|---|---|---|
| BLL19-01-PROBATION | Dieu_25:1 | Dieu_25:1 | Dieu_25:1 | Dieu_25:1 | Dieu_25:1 | Dieu_25:1 | Dieu_25:1 |
| BLL19-02-PROBATION_WAGE | Dieu_26:1 | Dieu_26:1 | Dieu_26:1 | Dieu_26:1 | Dieu_26:1 | Dieu_26:1 | Dieu_26:1 |
| BLL19-03-NOTICE | Dieu_35:1 | Dieu_35:2 | Dieu_35:2 | Dieu_35:1 | Dieu_35:1 | Dieu_35:1 | Dieu_35:1 |
| BLL19-04-ABSENCE | Dieu_36:1 | Dieu_36:1 | Dieu_36:1 | Dieu_36:1 | Dieu_36:1 | Dieu_36:1 | Dieu_36:1 |
| BLL19-05-PREGNANCY | Dieu_37:2 | Dieu_37:1 | Dieu_37:1 | Dieu_37:16 | Dieu_37:15 | Dieu_37:1 | Dieu_37:1 |
| BLL19-06-UNLAWFUL_RESIGNATION | Dieu_40:1 | Dieu_40:2 | Dieu_40:2 | Dieu_40:1 | Dieu_40:1 | Dieu_40:1 | Dieu_40:1 |
| BLL19-07-NOTICE_AND_SEVERANCE | Dieu_35:5, Dieu_46:1 | Dieu_35:3, Dieu_46:1 | Dieu_35:4, Dieu_46:1 | Dieu_35:3, Dieu_46:1 | Dieu_35:3, Dieu_46:2 | Dieu_35:4, Dieu_46:1 | Dieu_35:3, Dieu_46:1 |
| BLL19-08-UNLAWFUL_TERMINATION | Dieu_41:1, Dieu_46:3 | Dieu_41:1, Dieu_46:3 | Dieu_41:1, Dieu_46:2 | Dieu_41:1, Dieu_46:3 | Dieu_41:1, Dieu_46:3 | Dieu_41:1, Dieu_46:3 | Dieu_41:1, Dieu_46:3 |
| BLL19-09-DEPOSIT | Dieu_17:1 | Dieu_17:1 | Dieu_17:1 | Dieu_17:2 | Dieu_17:2 | Dieu_17:1 | Dieu_17:1 |

- Qev 0.8B [en]: 0/180 scores are 0 or 1 after rounding; 0 gold articles tie with another candidate; 0 request errors.
- Qev 0.8B [vi]: 0/180 scores are 0 or 1 after rounding; 0 gold articles tie with another candidate; 0 request errors.
- Qev 4B [en]: 0/180 scores are 0 or 1 after rounding; 0 gold articles tie with another candidate; 0 request errors.
- Qev 4B [vi]: 0/180 scores are 0 or 1 after rounding; 0 gold articles tie with another candidate; 0 request errors.

## Experiment B: 29 NLI pairs as a 3-option `choice` question

State `{premise, hypothesis}`; options entailment / neutral / contradiction (option order = that order). Accuracy per constructed class (n=9 each); real = 2 real model outputs.

| System | entailment | neutral | contradiction | all constructed (27) | real outputs (2) | median ms/req | p95 ms | status |
|---|---|---|---|---|---|---|---|---|
| local MoritzLaurer/mDeBERTa-v3-base-mnli-xnli (mps float32) | 6/9 | 7/9 | 6/9 | 19/27 = 0.704 | 2/2 | 213 (local) | 614 | earlier probe |
| Qev OneJev1.6-0.8B [vi] | 5/9 | 9/9 | 6/9 | 20/27 = 0.741 | 1/2 | 460 | 607 | ok, 0 errors |
| Qev OneJev1.6-0.8B [en] | 5/9 | 9/9 | 6/9 | 20/27 = 0.741 | 1/2 | 455 | 522 | ok, 0 errors |
| Qev OneJev1.6-4B [vi] | 6/9 | 8/9 | 8/9 | 22/27 = 0.815 | 2/2 | 470 | 551 | ok, 0 errors |
| Qev OneJev1.6-4B [en] | 6/9 | 8/9 | 8/9 | 22/27 = 0.815 | 2/2 | 464 | 841 | ok, 0 errors |

Wording `vi`: question "Căn cứ pháp lý (premise) có suy ra giả thuyết (hypothesis), mâu thuẫn với giả thuyết, hay không liên quan đến giả thuyết?" with Vietnamese option descriptions; `en`: the English wording used by `DecisionModelNLI`/`QevHttpNLI` by default.

### Predicted-label distribution per true class (rows = true class; columns = predicted E / N / C)

| System | true entailment | true neutral | true contradiction |
|---|---|---|---|
| local mDeBERTa | 6/2/1 | 0/7/2 | 0/3/6 |
| Qev 0.8B [vi] | 5/2/2 | 0/9/0 | 1/2/6 |
| Qev 0.8B [en] | 5/2/2 | 0/9/0 | 1/2/6 |
| Qev 4B [vi] | 6/2/1 | 0/8/1 | 1/0/8 |
| Qev 4B [en] | 6/2/1 | 0/8/1 | 1/0/8 |

### Calibration notes (descriptive; n=29, not a calibration study)

| System | mean top-1 prob (correct) | mean top-1 prob (wrong) | predictions with top-1 >= 0.9 | of which wrong |
|---|---|---|---|---|
| Qev 0.8B [vi] | 0.860 | 0.745 | 13 | 2 |
| Qev 0.8B [en] | 0.872 | 0.762 | 14 | 2 |
| Qev 4B [vi] | 0.833 | 0.807 | 11 | 1 |
| Qev 4B [en] | 0.836 | 0.797 | 12 | 1 |
| local mDeBERTa | 0.994 | 0.953 | 28 | 7 |

### Per-pair predictions (predicted label, P(predicted); `*` = wrong)

| Pair | expected | mDeBERTa | 0.8B vi | 0.8B en | 4B vi | 4B en |
|---|---|---|---|---|---|---|
| BLL19-01-PROBATION::entailment | enta | enta 1.00 | enta 0.70 | enta 0.73 | enta 0.74 | enta 0.78 |
| BLL19-01-PROBATION::contradiction | cont | neut 0.91* | cont 0.86 | cont 0.87 | cont 0.95 | cont 0.95 |
| BLL19-01-PROBATION::neutral | neut | neut 1.00 | neut 0.92 | neut 0.95 | neut 0.96 | neut 0.95 |
| BLL19-02-PROBATION_WAGE::entailment | enta | enta 1.00 | enta 0.93 | enta 0.93 | enta 0.96 | enta 0.97 |
| BLL19-02-PROBATION_WAGE::contradiction | cont | cont 0.98 | cont 0.92 | cont 0.94 | cont 0.96 | cont 0.98 |
| BLL19-02-PROBATION_WAGE::neutral | neut | cont 0.99* | neut 0.93 | neut 0.94 | neut 0.98 | neut 0.96 |
| BLL19-03-NOTICE::entailment | enta | enta 1.00 | enta 0.77 | enta 0.81 | enta 0.68 | enta 0.72 |
| BLL19-03-NOTICE::contradiction | cont | cont 0.99 | cont 0.78 | cont 0.76 | cont 0.89 | cont 0.88 |
| BLL19-03-NOTICE::neutral | neut | neut 1.00 | neut 0.97 | neut 0.99 | neut 0.85 | neut 0.86 |
| BLL19-04-ABSENCE::entailment | enta | enta 1.00 | enta 0.91 | enta 0.90 | enta 0.99 | enta 0.99 |
| BLL19-04-ABSENCE::contradiction | cont | cont 1.00 | cont 0.98 | cont 0.98 | cont 0.99 | cont 0.99 |
| BLL19-04-ABSENCE::neutral | neut | neut 1.00 | neut 0.97 | neut 0.98 | neut 0.94 | neut 0.92 |
| BLL19-05-PREGNANCY::entailment | enta | neut 1.00* | neut 0.87* | neut 0.88* | neut 0.85* | neut 0.81* |
| BLL19-05-PREGNANCY::contradiction | cont | neut 1.00* | neut 0.94* | neut 0.95* | cont 0.68 | cont 0.72 |
| BLL19-05-PREGNANCY::neutral | neut | neut 1.00 | neut 0.96 | neut 0.96 | neut 0.81 | neut 0.80 |
| BLL19-06-UNLAWFUL_RESIGNATION::entailment | enta | neut 1.00* | neut 0.66* | neut 0.63* | neut 0.85* | neut 0.83* |
| BLL19-06-UNLAWFUL_RESIGNATION::contradiction | cont | cont 0.99 | cont 0.84 | cont 0.83 | cont 0.63 | cont 0.70 |
| BLL19-06-UNLAWFUL_RESIGNATION::neutral | neut | neut 1.00 | neut 0.98 | neut 0.99 | neut 0.92 | neut 0.91 |
| BLL19-07-NOTICE_AND_SEVERANCE::entailment | enta | enta 0.99 | enta 0.59 | enta 0.62 | enta 0.63 | enta 0.64 |
| BLL19-07-NOTICE_AND_SEVERANCE::contradiction | cont | cont 0.99 | neut 0.76* | neut 0.82* | cont 0.92 | cont 0.96 |
| BLL19-07-NOTICE_AND_SEVERANCE::neutral | neut | neut 1.00 | neut 0.79 | neut 0.80 | neut 0.79 | neut 0.71 |
| BLL19-08-UNLAWFUL_TERMINATION::entailment | enta | enta 0.95 | cont 0.51* | cont 0.51* | enta 0.50 | enta 0.53 |
| BLL19-08-UNLAWFUL_TERMINATION::contradiction | cont | cont 1.00 | cont 0.61 | cont 0.61 | cont 0.87 | cont 0.86 |
| BLL19-08-UNLAWFUL_TERMINATION::neutral | neut | neut 1.00 | neut 0.85 | neut 0.84 | cont 0.51* | cont 0.50* |
| BLL19-09-DEPOSIT::entailment | enta | cont 1.00* | cont 0.97* | cont 0.98* | cont 0.96* | cont 0.98* |
| BLL19-09-DEPOSIT::contradiction | cont | neut 0.73* | enta 0.49* | enta 0.58* | enta 0.86* | enta 0.87* |
| BLL19-09-DEPOSIT::neutral | neut | cont 1.00* | neut 0.92 | neut 0.94 | neut 0.70 | neut 0.59 |
| real-output-dieu17-deposit | cont | cont 1.00 | enta 0.76* | enta 0.75* | cont 0.89 | cont 0.91 |
| real-output-dieu107-california | neut | neut 1.00 | neut 0.88 | neut 0.93 | neut 0.76 | neut 0.79 |

## Local re-implementation (`SystemOneRunner`) vs the official 0.8B server

Status: **ok**. Wording `en`; local device mps bfloat16; peak RSS+MPS driver 2.71 GiB (limit 4 GiB); load 19.1 s.

Items: 10 (5 NLI pairs + 5 rerank candidates). Decision agreement (argmax / P(yes)>=0.5): **10/10**. Prompt token counts equal: 10/10. Mean max |dP|: 0.0019; max |dP|: 0.0092; items with |dP| > 0.05: 0.

| Item | local | official | agree | max abs dP | local tokens | official tokens |
|---|---|---|---|---|---|---|
| BLL19-01-PROBATION::entailment | 0.736 / 0.220 / 0.045 | 0.726 / 0.227 / 0.046 | yes | 0.0092 | 186 | 186 |
| BLL19-04-ABSENCE::contradiction | 0.004 / 0.017 / 0.979 | 0.005 / 0.017 / 0.978 | yes | 0.0011 | 222 | 222 |
| BLL19-03-NOTICE::neutral | 0.002 / 0.986 / 0.012 | 0.002 / 0.985 / 0.012 | yes | 0.0004 | 185 | 185 |
| BLL19-05-PREGNANCY::entailment | 0.075 / 0.877 / 0.048 | 0.075 / 0.877 / 0.048 | yes | 0.0004 | 188 | 188 |
| real-output-dieu17-deposit | 0.752 / 0.164 / 0.083 | 0.754 / 0.162 / 0.084 | yes | 0.0028 | 273 | 273 |
| BLL19-01-PROBATION::Dieu_25 | 0.779 | 0.776 | yes | 0.0029 | 365 | 365 |
| BLL19-01-PROBATION::Dieu_53 | 0.093 | 0.091 | yes | 0.0015 | 481 | 481 |
| BLL19-05-PREGNANCY::Dieu_37 | 0.768 | 0.768 | yes | 0.0001 | 323 | 323 |
| BLL19-05-PREGNANCY::Dieu_36 | 0.302 | 0.302 | yes | 0.0003 | 873 | 873 |
| BLL19-09-DEPOSIT::Dieu_17 | 0.432 | 0.433 | yes | 0.0007 | 278 | 278 |

(NLI columns are P(E) / P(N) / P(C).)

## Observations on the recorded run (23 Oct 2026; re-check after any re-run)

- **Re-ranking**: on these 9 queries neither Qev model improved on the stored first stage (MRR 0.944) nor on the two local rerankers (MRR 1.000 each); 0.8B reached MRR 0.889, 4B 0.840 (en) / 0.785 (vi). The 4B model put the pregnancy article (Dieu_37) at rank 15-16 of 20, and the deposit article (Dieu_17) at rank 2. Differences are 1-2 queries; no ranking of the models is justified by this sample. The English statement was not worse than the Vietnamese one.
- **NLI**: constructed-label accuracy 20/27 (0.8B) and 22/27 (4B) vs 19/27 for mDeBERTa; the wording language (vi/en) made no difference to the 0.8B predictions and none to the 4B ones. The same pairs fail for every model (pregnancy and unlawful-resignation entailments predicted neutral; the deposit entailment predicted contradiction) which points at the constructed pairs/hypothesis phrasing as much as at the models. The 0.8B model called the real deposit output ("employer may require a deposit") entailment (wrong), the 4B model and mDeBERTa called it contradiction.
- **Calibration**: Qev top-1 probabilities are moderate (mean 0.83-0.87 when correct, 0.75-0.81 when wrong), so they separate right from wrong only weakly; mDeBERTa is near-certain (0.99) even when wrong. Probabilities are model outputs of unverified calibration, not evidence of correctness.
- **Latency**: ~0.45-0.52 s per request seen from this Mac, of which the server reports only ~0.05 s (0.8B) / ~0.08 s (4B); the remaining ~0.41-0.43 s is tunnel/network and HTTP overhead. Sequential rerank of 20 candidates therefore costs ~9-10 s regardless of model size here. Timings are for a shared GPU and a single tunnel and may vary.
- **Local vs official**: the local re-implementation matched the official 0.8B server on prompt token count and decision for all 10 items; remaining differences (<= 0.01) are consistent with bf16 on MPS vs the server and 6-decimal rounding. This supports, but with n=10 does not prove, that `SystemOneRunner` reproduces the official prompt.

## Failures and errors

None recorded in results.json.
