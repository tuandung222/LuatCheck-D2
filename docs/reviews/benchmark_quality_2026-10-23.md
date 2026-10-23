# Benchmark quality audit: hcmut_v1 and labour_vi_v1

Date and time: 2026-10-23 22:07 +07 (UTC+7). Reviewer: BENCHMARK-QA (read-only; no task, lock, corpus or config file was edited).
Status of this document: an independent review by one AI reviewer plus two LLM second opinions. It is not a human or legal-expert review.

## 1. Bottom line

| | hcmut_v1 | labour_vi_v1 |
|---|---|---|
| Automatic checks (section 4) | all pass | 2 of 14 deterministic checks report metadata inconsistencies only (3 `single` items with 2 gold records; 2 `doc_code` values that differ from the first gold record); no data-integrity failure |
| Gold answers wrong (BLOCKER) | 0 of 45 | 0 of 45 |
| Refusal items that the corpus actually answers | 0 of 5 | 0 of 5 |
| MAJOR item-level findings | 0 | 0 |
| MAJOR benchmark-level findings | 3 (B1 retrieval saturation, B2 guessable items, B3 decision-number pins) | 3 (B1 retrieval saturation, B2 guessable items, B4 invalid closed-book claim in README) |
| MINOR | 12 items/clusters | 13 items/clusters |
| Fit for the D2 run as-is | Yes, for correctness of gold. Report caveats B1 to B3. | Yes, for correctness of gold. Do not repeat the README closed-book claim (B4); report caveats B1 and B2. |

Every one of the 90 answerable gold answers follows from its cited record text, and every one of the 10 refusal items is genuinely unanswerable from the corpus (HCMUT-050 and LVN-025 have a partly related passage, see section 6). The two benchmarks are weak as discriminating instruments, not wrong as ground truth: BM25 alone already places the gold record first for 89% (hcmut) and 78% (labour) of questions, and about one third of the answerable questions can be answered without the corpus.

## 2. Method

1. Mechanical audit, `evaluation/benchmarks/qa/audit_benchmarks.py` (reads data only; raw output in `evaluation/benchmarks/qa/audit_output_2026-10-23.json`). Checks: lock hashes recomputed (sha256 of tasks, corpus, profile, benchmark.yaml and the 10 verification files), lock counts, required fields, unique ids and questions, category and behaviour values, gold ids exist in the corpus, evidence ids equal gold ids, every `exact_quote` is a verbatim substring of its record (NFC and whitespace normalised), `pdf_pages` equal the record `source_pages`, `doc_code` equals the first gold record, category and gold-count coherence, `review_status` of yaml equals lock. Descriptive checks: numbers of the expected answer vs quotes, question and answer token overlap, near-duplicate questions, shared gold records, quotes that also occur in non-gold records, evidence position inside long records, instrument numbers cited in questions that are absent from the gold text, an own BM25 baseline (syllable unigrams, question text only; it is not the system retriever), sanity-run signals.
2. Manual correctness review of all 100 items against the full text of the cited records (read in full, not only the quotes). Sufficiency was tested by looking for qualifying clauses, exceptions, dates and a second clause that the answer needs. For the table-dependent golds the PDF pages were rendered and read as images: HCMUT 1260 p.2 (HCMUT-001, 023), CTDT1862 p.2 and p.6 (HCMUT-034, 036), 2749 p.5 (HCMUT-006), ND135 p.4 (LVN-030). ND293 p.2 (LVN-009, 021, 047) was checked in a second extraction mode. Arithmetic re-done for LVN-040 (3 + 25 x 0.3 = 10.5) and LVN-047 (5 x 5,310,000 = 26,550,000).
3. Refusal items: every one of the 10 questions was searched over its whole corpus with several keyword and regex patterns (e.g. phúc khảo, đơn giá, học bổng, ký túc, mức phạt, phạt tiền, triệu đồng, bảo hiểm y tế next to %, lương hưu, thai sản next to %) and the closest records by IDF-weighted overlap were inspected; the same 8 closest records per question were also given to the two gateway models.
4. Gateway second opinion (LLM opinion only; every flag was re-checked against the corpus text before being reported): `deepseek/deepseek-v4-pro` (all 100 items, `evaluation/benchmarks/qa/gateway_second_opinion_deepseek-v4-pro_2026-10-23.json`) and `openrouter/google/gemini-3-flash-preview` (all 100 items, `..._gemini-3-flash_2026-10-23.json`). Prompts and code: `evaluation/benchmarks/qa/gateway_second_opinion.py`. The key was read through `evaluation.judge_gateway.local_environment` and never printed or stored.
5. Corrected closed-book probe for labour (`evaluation/benchmarks/qa/closed_book_neutral.py`, output `closed_book_neutral_labour_2026-10-23.json`): same answer model and judge as the sanity runs (Gemma-4-31B, DeepSeek Flash) with a neutral labour-law prompt instead of the HCMUT-scoped one. LLM estimates, not labels.
6. Gateway cost reported by the gateway: USD 0.384 (DeepSeek Pro, 100 calls) + 0.0035 (2-call probe) + 0.0985 (Gemini Flash, 100 calls) + 0.0113 (closed-book probe) = about USD 0.50.
7. Not done: no human or legal expert review; no check of Oct-2026 consolidated law outside the corpus (the corpus is a snapshot of 2026-10-22; later amendments were not checked, as the project README already states); no heavy local model was loaded.

Agreement of the LLM opinions with my own review: DeepSeek Pro rated 88 of 90 answer items "correct" and confirmed 10 of 10 refusals; its 2 "minor_issue" flags are HCMUT-026 (omitted exception, real, see MINOR) and LVN-005 (it wanted the words "hợp đồng làm việc hoặc chấm dứt làm việc" in the answer; not an issue). Gemini Flash rated 89 of 90 correct, flagged HCMUT-026 again, and called HCMUT-050 "partially answerable" (real, see MINOR). Neither model found a wrong value.

## 3. Counts

### 3.1 hcmut_v1 (50 tasks, corpus 143 records, 10 documents)

| | |
|---|---|
| category | single 40, multi 5 (021, 022, 023, 046, 047), out_of_scope 5 (024, 025, 048, 049, 050) |
| expected_behavior | answer 45, refuse 5 |
| gold_status | 49 `ai_verified_two_independent_reviewers_adjudicated`, 1 (HCMUT-021) `ai_verified_adjudicator_plus_independent_recheck` |
| answer has a digit | 26 of 45 |
| questions naming an instrument, article or document | 29 of 50; 22 of 45 cite a decision number (1259, 1260, 1862, 2282, 2749) |
| unique gold records | 35 of 143 (24%); 10 records are used by more than one task |

| document (task `doc_code`, refusals count their nearest document) | tasks | gold citations | corpus records |
|---|---|---|---|
| HVCHUNG1259 | 7 | 6 | 25 |
| GVCN2977 | 6 | 5 | 25 |
| NOIQUY1924 | 6 | 5 | 9 |
| HVDT1260 | 5 | 6 | 18 |
| HOCPHI2800 | 5 | 6 | 14 |
| VINHDANH658 | 5 | 4 | 19 |
| HVDT2749 | 4 | 4 | 4 |
| GIANGDAY2282 | 4 | 4 | 6 |
| CTDT1862 | 4 | 5 | 4 |
| UNGXU3408 | 4 | 5 | 19 |

### 3.2 labour_vi_v1 (50 tasks, corpus 458 records, 10 documents)

| | |
|---|---|
| category | single 40, multi 5 (021, 022, 023, 046, 047), out_of_scope 5 (024, 025, 048, 049, 050) |
| expected_behavior | answer 45, refuse 5 |
| gold_status | 49 `ai_verified_two_independent_reviewers_adjudicated`, 1 (LVN-047) `ai_verified_adjudicator_plus_independent_recheck` |
| answer has a digit | 37 of 45 |
| questions naming an instrument, article or document | 30 of 50; 21 of 45 cite a decree or circular number |
| unique gold records | 41 of 458 (9%); 9 records are used by more than one task |

| document | tasks | gold citations | corpus records |
|---|---|---|---|
| LVL2025 | 7 | 7 | 55 |
| BLLD2019 | 6 | 6 | 220 |
| ND274_2025 | 6 | 4 | 16 |
| ND219_2025 | 5 | 6 | 36 |
| ND135_2020 | 5 | 5 | 12 |
| TT26_2025 | 5 | 5 | 5 |
| ND293_2025 | 4 | 6 | 5 |
| ND318_2025 | 4 | 6 | 25 |
| LCD2024 | 4 | 4 | 37 |
| ND143_2024 | 4 | 4 | 47 |

## 4. Automatic check results

| check | hcmut_v1 | labour_vi_v1 |
|---|---|---|
| lock hashes recomputed match (tasks, corpus, profile, yaml, 10 verification files) | pass | pass |
| lock counts (50 tasks, categories, behaviours, records) match | pass | pass |
| ids unique; questions unique | pass | pass |
| required fields present | pass | pass |
| category and behaviour values valid | pass | pass |
| gold ids exist in corpus | pass | pass |
| evidence ids equal gold ids | pass | pass |
| every `exact_quote` verbatim in its cited record (68 quotes in hcmut, 77 in labour) | pass | pass |
| `pdf_pages` equal record `source_pages` | pass | pass |
| `doc_code` equals first gold record | pass | FAIL: LVN-023 (ND219_2025 vs first gold BLLD2019), LVN-046 (TT26_2025 vs first gold ND135_2020); explained in the notes as "first cited", metadata only |
| category and gold-count coherence (`single` has 1 gold) | pass | FAIL: LVN-014, LVN-016, LVN-019 are `single` with 2 gold records (the README says so; metadata only) |
| benchmark.yaml `review_status` equals lock | pass (`ai_verified_not_human_reviewed`) | pass, but both say `pending` while the README says "AI-verified, not human-reviewed" |

Descriptive results (raw in the JSON): near-duplicate questions, maximum pairwise token Jaccard 0.46 (hcmut) and 0.54 (labour), no pair above 0.7; question and expected-answer overlap is high only where the answer is a bare number or entity, so there is no sign of the answer wording being copied into questions beyond what the question needs; none of the quotes is missing a number that the expected answer states, except derived values (HCMUT-009 "0,01" from "0.01", LVN-040 and LVN-047 computed).

## 5. Findings

Severity rule: BLOCKER = gold is wrong, so a reported number would be wrong. MAJOR = ambiguous, insufficient evidence, time-sensitive, or a claim or design problem that changes what a D2 number means. MINOR = wording, balance, metadata. Nothing here is applied; each item carries a proposed fix for a future benchmark version.

### 5.1 BLOCKER

None found in either benchmark (0 of 90 answerable golds; 0 of 10 refusals).

### 5.2 MAJOR, benchmark-level

**B1 (both). Retrieval is nearly saturated, so the benchmark cannot separate retrieval variants.**
An own BM25 over title and content, using only the question text, puts a gold record at rank 1 for 40 of 45 hcmut and 35 of 45 labour questions, in the top 5 for 45 and 44 of 45. Worst ranks: hcmut 2 (HCMUT-021, 030, 034, 035, 039), labour 6 for LVN-016, 3 for LVN-002, 003, 018, 019. The cause is that 29 hcmut and 30 labour questions name the document or article, and ND293 and TT26 are only 5 records each yet supply 11 tasks. With the D2 variants (off, l1, l1_rerank) retrieval recall and MRR will be near the ceiling for all of them.
Fix or caveat: report retrieval metrics as saturated; add a harder v2 slice (questions that do not name the instrument, gold in large documents such as BLLD2019, paraphrased wording); do not claim reranker benefit from these items.

**B2 (both). About one third of the answerable items are answerable without the corpus.**
hcmut sanity run (correct HCMUT-scoped prompt, Gemma-4-31B, DeepSeek Flash judge): 15 of 45 closed-book correct and 12 partially correct: HCMUT-003, 006, 007, 013, 018, 022, 026, 027, 030, 032, 033, 035, 043, 044, 045. labour with a neutral prompt (my re-run): 12 of 45 correct, 10 partial: LVN-001, 006, 007, 008, 011, 016, 026, 027, 030, 031, 043, 046 (correct). The adjudication files already say guessable items were left unchanged by owner decision; the point here is that absolute accuracy is partly parametric knowledge.
Fix or caveat: report closed-book accuracy next to every variant, and give accuracy stratified by "closed-book solvable" vs "not solvable"; keep the lists above as the stratum definition (they are LLM estimates, not labels).

**B3 (hcmut). 22 of 45 answerable questions pin the document by a decision number that is not in any gold record text and not printed in the source PDFs.**
HCMUT-001 to 016, 022, 034 to 037, 047 say e.g. "Theo Quyết định 1260/QĐ-ĐHBK sửa đổi khoản 3.1 Điều 3". The PDFs print blank "Số" and "ngày" (ADJUDICATION limitation 5); the numbers come from the website listing and the file names, unverified against signed copies, and the README says "No task asks about them". Only HVDT2749 Điều 1 mentions "1260" in its text, the others (1259, 1862, 2282, 2749) occur only in record metadata (`source_name`, `document_number`) and in the doc_id suffix. BM25 indexes title and content only (`src/retrieval/bm25_engine.py` line 28), so the number cannot help lexical retrieval; and a wrong listing number would make 22 questions point to a wrong instrument. The gold content itself is not affected.
Fix: either verify the five numbers against signed copies, or re-pin by description ("Quy định học vụ đại học, phần sửa đổi khoản 3.1 Điều 3 tại văn bản tháng 3/2026") and keep the article numbers; at least record the unverified status in the D2 limitations. The same pattern exists in labour (21 questions cite "Nghị định 293/2025" etc.), but there the numbers are printed in the PDFs, so only the lexical-retrieval remark applies.

**B4 (labour). The README claim "Closed-book: no answerable item correct (all items require the corpus)" is not valid evidence.**
`evaluation/benchmark_sanity.py` uses one `CLOSED_SYSTEM` prompt for both benchmarks: "Trả lời ngắn gọn ... câu hỏi về quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM. Nếu bạn không chắc, nói rõ là không biết." In `labour-sanity-final-v1` 48 of 50 closed-book answers mention the HCMUT or học vụ scope (example LVN-001: "Câu hỏi của bạn thuộc lĩnh vực Luật Lao động, không phải quy định học vụ của Trường Đại học Bách khoa"); the "0 correct, 28 inappropriate refusals" is a scope-refusal artefact. The neutral re-run gives 12 correct and 10 partially correct of 45 (see B2). The oracle column is not affected (45 of 45 correct). A smaller related point: in the oracle condition the 5 refusal items receive only the list of all section titles (`benchmark_sanity.py` comment "the oracle context is the whole set of section titles"), so "5/5 appropriate refusals" shows only that the model refuses on titles, not that the corpus lacks the answer; section 6 supplies that evidence.
Fix: delete or correct the README sentence, and the closed-book counts quoted in the labour ADJUDICATION.md (draft run, same prompt; 47 of 50 answers mention the HCMUT scope); use a domain-neutral closed-book prompt and re-run if the number is cited.

### 5.3 MAJOR, item-level

None. The candidates that were examined and downgraded are listed under MINOR with the reason (LVN-031 and the ND135 cluster, HCMUT-014, HCMUT-030).

### 5.4 MINOR, hcmut_v1

| id | quoted evidence | issue | proposed fix |
|---|---|---|---|
| HCMUT-030 | Nội quy Điều 3: "sinh viên phải đeo thẻ sinh viên khi ở trong khuôn viên Trường"; Ứng xử Điều 9.6: "Người học đeo thẻ sinh viên/ học viên khi ở trong khuôn viên Trường" | The question does not name the document and a second record states the same rule (BM25 even ranks `HCMUT_UNGXU3408_Dieu_9` first). A correct citation of it scores as a citation miss. | Add `HCMUT_UNGXU3408_Dieu_9` as an accepted alternative id, or name the Nội quy in the question. |
| HCMUT-005, 006, 007, 008 | `HCMUT_HVDT1260_PhuLuc_1` has the same Phụ lục 1 text (diff: only table headers and extraction spacing) | The question pins 2749 (the 2749 appendix replaces the 1260 one, so the 1260 record is a superseded duplicate). Retrieval of the 1260 record is a distractor, not an alternative gold. | Keep gold; document the 1260 appendix as a known superseded distractor. |
| HCMUT-010 | gold id `HCMUT_HVCHUNG1259_Dieu_1_S9_1` titled "9.1 Phân công quản lý các học phần" but the answer "điểm đạt là từ điểm C." sits in the 14.2 text appended to that record | Chunking artefact: the question cites khoản 14.2 Điều 14, which no record title carries. | Keep; note it, or re-chunk the corpus in a new version. |
| HCMUT-014 | "đăng ký trước 16g00 của ngày làm việc cách trước ngày dạy bù tối thiểu 01 ngày và trước tối đa 07 ngày" | The source does not say whether the 1 and 7 days are calendar or working days. The expected answer says "01 ngày ... 07 ngày"; the oracle judge rated "01 ngày làm việc ... 07 ngày" as partially_correct. | Accept both unit readings; add "đơn vị ngày theo văn bản không nêu rõ". |
| HCMUT-021 | "Bước 1 ... nộp đơn ... về Phòng Công tác sinh viên"; "Trưởng Phòng ... là Phó Chủ tịch Hội đồng"; "Phó Trưởng phòng Công tác sinh viên là thư ký" | Correct and a true two-record chain, but reviewed only by the adjudicator and one recheck. In the smoke run all three variants "clarified" instead of answering (Recall@1 0.5: only Điều 7 retrieved at first). | None for gold; expect this item to be hard for retrieval depth. |
| HCMUT-022 | "Sinh viên phải có điểm trung bình tích lũy (GPA) từ 2.0 trở lên"; "Từ 2,00 đến cận 2,50: Trung bình" | Three questions in one (threshold, hypothetical GPA 2,35, rank); answer correct. Scoring needs partial credit per sub-question. | Split or define sub-scores. |
| HCMUT-026 | "Mỗi GVCN chủ nhiệm tối đa 02 lớp (áp dụng với tất cả các hệ đào tạo, trường hợp đặc biệt do Hiệu trưởng quyết định)" | Expected answer "Tối đa 02 lớp" omits the exception; both LLM reviewers flagged it. A fuller answer is not wrong. | Add the exception to `expected_answer`, or tell graders not to penalise it. |
| HCMUT-046 | duplicates the Nội quy Điều 6.3 half of HCMUT-033 | Half-duplicate of 033 (known). | Replace or keep as a documented overlap. |
| HCMUT-047 | "có tối thiểu 9 tín chỉ tự chọn tự do (đối với khóa 2025 về trước)" | Two independent facts joined by "và"; the number 9 also occurs in Điều 12 khoản 4 (tự chọn ngành/chuyên ngành), a plausible wrong pick. Gold is right. | Documented in the task notes; keep. |
| HCMUT-050 | Nội quy Điều 5.3: "Đi xe máy, xe đạp trong khuôn viên Trường" | The question has a false-premise element: riding a motorbike onto campus is itself banned, the fine amount is absent. Gemini rated it "partially answerable". Refusal is still the right behaviour, and the expected answer says so. | Graders should accept "no fine stated, but the ban exists". |
| HCMUT-005, 006, 007, 015, 034, 037, 047 | gold quote starts after char 3,000 of its record (HVDT2749_PhuLuc_1: 6,402 / 5,756 / 3,791; GIANGDAY2282_PhuLuc_1: 5,056; CTDT1862_Dieu_1 (19,613 chars): 4,698 / 8,055 / 7,106) | In the `l1_rerank` variant the reranker has `max_length` 1024 tokens (about 3,000 characters of Vietnamese; approximate, not tokenised), so for these items the reranker may not see the answer span. Five tasks (034, 035, 036, 037, 047) share one 19.6k-character record, four (005 to 008) share an 8k record. | Treat results on these items as partly a truncation test; consider splitting the records in a v2 corpus. |
| HCMUT-001 to 016, 022, 034 to 037, 047 | see B3 | decision-number pin | see B3 |

### 5.5 MINOR, labour_vi_v1

| id | quoted evidence | issue | proposed fix |
|---|---|---|---|
| LVN-014, 016, 019 | gold lists 2 records (ND318 Điều 6 and 25; ND318 Điều 4 and 8; ND219 Điều 30 and 31) | Category `single` with 2 gold ids; breaks the "single = one record" rule used by any per-category retrieval metric. The README says the choice was deliberate (to keep the 40/5/5 mix). | Relabel as `multi` in a new version (mix becomes 37/8/5) or accept and state it. |
| LVN-023, 046 | `doc_code` ND219_2025 / TT26_2025 vs first gold BLLD2019 / ND135_2020 | Metadata inconsistency (explained in notes). | Order gold ids to match `doc_code`. |
| LVN-008 | "Tiền lương làm căn cứ đóng bảo hiểm thất nghiệp cao nhất bằng 20 lần mức lương tối thiểu tháng theo vùng" | The question names neither a law nor a date (the rule is in Luật Việc làm 2025, effective 01-01-2026; the answer happens to be the same under the 2013 law). Also closed-book solvable. | Add "theo Luật Việc làm 2025". |
| LVN-003 | question: "gây thiệt hại trực tiếp đến tài sản"; source: "hành vi vi phạm liên quan trực tiếp đến tài chính, tài sản, tiết lộ bí mật ..." | The question paraphrases "liên quan trực tiếp đến" as "gây thiệt hại trực tiếp đến"; the answer 12 tháng is still right. | Reword to "liên quan trực tiếp đến tài sản". |
| LVN-002 | answer lists the sectors of khoản 3 points a to d and đ | Long reference answer; hard to grade by overlap, easy to over-penalise a correct shorter answer. | Provide a rubric (200 giờ; 300 giờ; list is ngành a-d, đ by Government). |
| LVN-031 and the ND135 cluster (030, 031, 032, 033, 046) | ND135 Điều 5.1: "không quá 05 tuổi ... trừ trường hợp pháp luật có quy định khác"; BLLĐ Điều 219 (in corpus): up to 05 years for 61% to under 81%, up to 10 years for 81% and above | The question pins khoản 1 Điều 5, so 05 is right for the cited text; but a second in-corpus rule (and the replacement of the 2014 BHXH law by Luật 41/2024/QH15, which ND318 cites by number and ND274 applies article by article) gives a defensible "up to 10" for incapacity of 81% or more. All five items quote ND135 as promulgated; whether ND135 Điều 3, 4, 5, 7 is unchanged in Oct 2026 cannot be settled from the corpus. | Accept "05 (and up to 10 if 81% or more under BLLĐ Điều 219)" for LVN-031; keep the "texts as promulgated" caveat in D2 for the five items. |
| LVN-036 | ND274 Điều 4 (not treated as trốn đóng) and Điều 5 khoản 1 điểm c, d (the unpaid amount is still counted as chậm đóng) | Expected answer states only "không bị coi là trốn đóng"; a fuller answer that adds "vẫn là chậm đóng" is not wrong. | Add the remark to the reference or tell graders. |
| LVN-040, 047 | "3 lần ... cộng 0,3 lần cho mỗi 1%" (10,5 lần); "05 lần" x "5.310.000" (26.550.000 đồng) | Derived values (arithmetic verified). Format tolerance needed: 10,5 or 10.5; 26.550.000 or 26,55 triệu. LVN-047 has the weaker review chain (adjudicator plus one recheck). | State accepted numeric forms. |
| LVN-042 | "được xác định theo thời gian làm việc ở vùng ... tại tháng 6 năm 2025" | The source sentence is itself convoluted (it refers to the vùng list as of June 2025); the reference copies it and the question asks "theo thời điểm nào". | Reword the reference as "theo danh mục/vùng tại tháng 6/2025". |
| LVN-037 | "đã được cơ quan có thẩm quyền đôn đốc trong thời hạn 45 ngày kể từ hạn đóng chậm nhất ... số ngày trốn đóng được tính từ khi nào" | Correct (60 days) but heavily nested; Vietnamese clarity low, easy to misread the 45 vs 60 days. | Reword; keep the answer. |
| LVN-043, 044, 045 | TT26 Điều 5 and Điều 2 | Administrative-responsibility lookups ("which body", "which khoản"), little reasoning; with LVN-042 and 046 five tasks come from a 5-record document. | Replace some with Code-based items in a v2. |
| LVN-025 | BLLĐ Điều 97 khoản 4: "đền bù ... một khoản tiền ít nhất bằng số tiền lãi" | Refusal is correct (no fine amount in the corpus); the compensation clause is a near-miss and the reference answer already names it. | None. |
| README and yaml | README: `gold_status` of LVN-047 "ai_replacement_adjudicator_only_not_reviewed_by_independent_verifiers"; tasks.json: `ai_verified_adjudicator_plus_independent_recheck`; yaml and lock: `review_status: pending` | Documents out of sync. | Align the README and the yaml `review_status` in the next version. |

### 5.6 Benchmark-level MINOR (both)

- Topic balance, labour: BLLD2019 is 48% of the records (220 of 458) but 6 of 50 tasks (12%): annual leave, overtime, disciplinary time limit, maternity leave, minimum-wage definition, foreign worker exemption. No item covers contract types and termination, probation, severance, dismissal, labour disputes or strikes. About 20 items (40%) concern unemployment or social insurance and 11 concern ND293 or TT26 (10 records). "Vietnamese Labour Code" cannot be claimed as tested.
- Multi-hop: only HCMUT-021 and LVN-047 are real dependent chains; the other `multi` items are parallel lookups (HCMUT-022, 023, 046, 047; LVN-021, 022, 023, 046). Expect "multi" results to measure two lookups, not reasoning.
- Clustering: 35 and 41 unique gold records for 45 answerable items each; five hcmut items share `HCMUT_CTDT1862_Dieu_1`, four share `HCMUT_HVDT2749_PhuLuc_1`; four labour items share ND293 Điều 3 (009, 010, 021, 047). Effective sample size is smaller than 45.
- Statistical power: with n = 45 answerable items the 95% Wilson interval for an observed accuracy of 50% is 36% to 64% (80%: 66% to 89%), so differences below about 15 percentage points between variants will not be resolvable without paired tests.
- No `clarify` behaviour exists in the schema, although the runner records `clarified` (smoke run: 4 of 18 trials, HCMUT-021 in all three variants and LVN-024 in one). Questions without a pinned instrument (HCMUT-030, 038; LVN-008, 043) can legitimately attract a clarification. Scoring of `clarified` must be defined before the main run.
- Refusal items: 4 of 5 labour refusals ask for a percentage or amount that lives in a law outside the corpus (BHYT, BHXH pension, maternity, fines), which are good near-misses; the hcmut refusals are weaker (049, ký túc xá, has no hit at all). The sanity oracle only checks refusals against titles (B4).
- The smoke run `bench-smoke-both-20261023` has 3 tasks per benchmark (001, 021, 024) with `report_eligible: false`; it is a pipeline check and gives no quality signal about the gold.

## 6. Refusal items: evidence of absence

| id | question topic | search result | verdict |
|---|---|---|---|
| HCMUT-024 | học phí per credit 2026-27 | `đơn giá` only in HVCHUNG1259 Điều 23.1 ("Trường thông báo đơn giá ... theo từng năm"), no amount | unanswerable, confirmed |
| HCMUT-025 | phúc khảo deadline | `phúc khảo`, `chấm lại`, `xem lại`, `công bố điểm`: 0 hits; `khiếu nại` only VINHDANH658 awards | confirmed |
| HCMUT-048 | học bổng khuyến khích học tập thresholds | `học bổng` once (GVCN2977 Điều 9, no criteria) | confirmed |
| HCMUT-049 | ký túc xá registration | `ký túc`, `nội trú`: 0 hits | confirmed |
| HCMUT-050 | traffic-law fine | `phạt`, `mũ bảo hiểm`: 0 hits; Nội quy bans motorbikes and bicycles | confirmed (partly related ban, see MINOR) |
| LVN-024 | BHYT contribution % | no `bảo hiểm y tế` next to a percentage (the 30% is a wage-deduction cap, the 1% is unemployment insurance) | confirmed |
| LVN-025 | fine for late wage payment | `xử phạt` only BLLĐ Điều 217, LVL2025 Điều 41, LCD2024 Điều 36 without amounts; `phạt tiền`, `triệu đồng`, `mức phạt`: none; Điều 97.4 is compensation | confirmed |
| LVN-048 | pension % at 20 years | `tỷ lệ hưởng lương hưu` only ND135 Điều 7.3 without a number; BLLĐ Điều 219 gives eligibility conditions only | confirmed |
| LVN-049 | maternity benefit % | BLLĐ Điều 139 refers to the BHXH law; no % next to `thai sản` | confirmed |
| LVN-050 | BHXH evasion fine | ND274's 0,03%/ngày is a payment, not a fine; no administrative fine amount | confirmed |

## 7. Per-item verdicts (spot-check table)

"OK" means the expected answer follows from the cited text and the question is answerable as stated; "CB" marks an LLM-estimated closed-book solvable item (section 5.2, B2); "alt" marks another record with the same text.

### hcmut_v1

| id | verdict | note |
|---|---|---|
| 001 | OK | table checked on PDF image |
| 002 | OK | |
| 003 | OK, CB | |
| 004 | OK | |
| 005 | OK | alt (superseded 1260 appendix); deep evidence |
| 006 | OK, CB | alt; table checked on PDF image |
| 007 | OK, CB | alt; deep evidence |
| 008 | OK | alt |
| 009 | OK | |
| 010 | OK | MINOR chunk label |
| 011 | OK | |
| 012 | OK | |
| 013 | OK, CB | |
| 014 | OK | MINOR unit |
| 015 | OK | deep evidence |
| 016 | OK | |
| 017 | OK | |
| 018 | OK, CB | |
| 019 | OK | |
| 020 | OK | |
| 021 | OK | MINOR review chain |
| 022 | OK, CB | MINOR compound |
| 023 | OK | table checked on PDF image |
| 024 | refusal confirmed | |
| 025 | refusal confirmed | |
| 026 | OK, CB | MINOR omitted exception |
| 027 | OK, CB | |
| 028 | OK | |
| 029 | OK | |
| 030 | OK, CB | MINOR alt gold |
| 031 | OK | |
| 032 | OK, CB | pinned to the Nội quy, so the Ứng xử mention is not an alternative |
| 033 | OK, CB | |
| 034 | OK | table checked on PDF image; deep evidence |
| 035 | OK, CB | |
| 036 | OK | table checked on PDF image |
| 037 | OK | deep evidence |
| 038 | OK | |
| 039 | OK | |
| 040 | OK | |
| 041 | OK | |
| 042 | OK | |
| 043 | OK, CB | |
| 044 | OK, CB | |
| 045 | OK, CB | |
| 046 | OK, CB | MINOR half-duplicate of 033 |
| 047 | OK | MINOR conjunction; deep evidence |
| 048 | refusal confirmed | |
| 049 | refusal confirmed | |
| 050 | refusal confirmed | MINOR false premise |

### labour_vi_v1

| id | verdict | note |
|---|---|---|
| 001 | OK, CB | |
| 002 | OK | MINOR long reference |
| 003 | OK | MINOR wording |
| 004 | OK | |
| 005 | OK | |
| 006 | OK, CB | |
| 007 | OK, CB | |
| 008 | OK, CB | MINOR no law pinned |
| 009 | OK | table checked (second extraction) |
| 010 | OK | |
| 011 | OK, CB | |
| 012 | OK | |
| 013 | OK | |
| 014 | OK | MINOR `single` with 2 gold; effective date 01/01/2027 in the question, correct |
| 015 | OK | |
| 016 | OK, CB | MINOR `single` with 2 gold |
| 017 | OK | |
| 018 | OK | |
| 019 | OK | MINOR `single` with 2 gold |
| 020 | OK | |
| 021 | OK | |
| 022 | OK | |
| 023 | OK | MINOR doc_code |
| 024 | refusal confirmed | |
| 025 | refusal confirmed | |
| 026 | OK, CB | |
| 027 | OK, CB | |
| 028 | OK | |
| 029 | OK | |
| 030 | OK, CB | table checked on PDF image |
| 031 | OK, CB | MINOR second rule |
| 032 | OK | ND135 cluster caveat |
| 033 | OK | ND135 cluster caveat |
| 034 | OK | |
| 035 | OK | |
| 036 | OK | MINOR completeness |
| 037 | OK | MINOR wording; deep evidence |
| 038 | OK | |
| 039 | OK | |
| 040 | OK | arithmetic verified |
| 041 | OK | |
| 042 | OK | MINOR wording |
| 043 | OK, CB | |
| 044 | OK | |
| 045 | OK | |
| 046 | OK, CB | MINOR doc_code |
| 047 | OK | arithmetic verified |
| 048 | refusal confirmed | |
| 049 | refusal confirmed | |
| 050 | refusal confirmed | |

## 8. What to do before the D2 numbers are written

1. Keep both benchmarks and their locks unchanged for the main run (the gold is correct; changing tasks after the freeze would break the freeze rule).
2. In the D2 text: remove or correct the labour README closed-book sentence (B4); show a closed-book baseline and the CB-stratified accuracy (B2); describe retrieval metrics as saturated by lexical matching (B1); list the HCMUT decision-number pin as an unverified limitation (B3); state that all labour answers follow the corpus text as promulgated and that later amendments (notably for the ND135 items) were not checked.
3. A future v2 slice, only after the user approves: unpinned and paraphrased questions, gold in large documents (BLLD2019 contract, termination, severance; HCMUT amendment records split by clause), genuine dependent multi-hop items, acceptable alternative ids (HCMUT-030), explicit numeric-format and unit tolerances, and a defined scoring rule for `clarified`.

## 9. Reproduce

```
python3 evaluation/benchmarks/qa/audit_benchmarks.py --out evaluation/benchmarks/qa/audit_output_2026-10-23.json
python3 evaluation/benchmarks/qa/gateway_second_opinion.py --model deepseek/deepseek-v4-pro --out <json>   # needs the gateway key via evaluation.judge_gateway.local_environment
python3 evaluation/benchmarks/qa/closed_book_neutral.py --out <json>                                      # same
```

Files: `evaluation/benchmarks/qa/audit_benchmarks.py`, `audit_output_2026-10-23.json`, `gateway_second_opinion.py`, `gateway_second_opinion_deepseek-v4-pro_2026-10-23.json`, `gateway_second_opinion_gemini-3-flash_2026-10-23.json`, `closed_book_neutral.py`, `closed_book_neutral_labour_2026-10-23.json`.
