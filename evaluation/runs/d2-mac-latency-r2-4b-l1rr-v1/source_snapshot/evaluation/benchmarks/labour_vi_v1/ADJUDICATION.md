# Adjudication of the labour_vi_v1 draft (50 tasks), 23 Oct 2026

Adjudicator: Claude Sonnet (AI). Inputs: `draft_all.json` (Claude Haiku draft), `verify_A.json` and `verify_B.json` (two independent Claude Sonnet verifiers), the corpus `data/corpus/labour_vi_v1.json` (458 records), and `docs/materials/labour-sources/manifest.json` + `README.md`. Output: `tasks.json`. The draft, verification files and `benchmark.yaml` were not modified.

Method: for every task flagged by either verifier I read the cited records in full (and neighbouring records where the question could depend on them), decided independently, and applied the best-supported fix, merging the verifiers' fixes where useful. Scope rule from the project owner: ground-truth correctness only (wrong or incomplete answer, insufficient gold, a quote that does not support the answer, an ambiguous question with more than one defensible answer, an out-of-scope item the corpus answers). Nothing was rewritten for style or guessability.

Verdict totals: verify_A accept 43 / fix 6 / reject 1; verify_B accept 45 / fix 5 / reject 0. Final: 39 kept unchanged (of which 036, 048, 049, 050 carry a note), 10 fixed, 1 replaced. Category mix 40 single / 5 multi / 5 out_of_scope, as drafted.

## Flagged tasks

| Task | verify_A | verify_B | Decision | Reason |
|---|---|---|---|---|
| 002 | fix | accept | fixed (answer, evidence) | The question asks in which cases the 200-hour cap rises, but the answer only said "các trường hợp liệt kê tại khoản 3" and the quotes did not contain them, so the gold was not self-contained. Answer now lists points a-đ of khoản 3 Điều 107 (checked against the full record); evidence has one verbatim quote per point. |
| 010 | fix | accept | fixed (evidence) | Answer correct (khoản 3 điểm c Điều 3 ND293). The old quote started at "thì áp dụng theo địa bàn ..." and omitted the subject (industrial zones spanning localities with different minimum wages). Replaced by the full clause. |
| 014 | fix | accept | fixed (evidence) | Answer correct. Platform/VNeID (khoản 3 điểm a) and the failure-reason clause were not covered by the two quotes. Three verbatim quotes now. B's "optional" note adopted. |
| 016 | fix | fix | fixed (gold, answer, evidence); kept single | Both: Điều 8 only says "thông tin quy định tại khoản 1 Điều 4"; the field list the question names is in ND318 Điều 4 khoản 1, so both records are needed. Both proposed multi; I kept it single (both records come from the same decree) to preserve the 40/5/5 mix, with both records cited. Answer extended as in B. Question unchanged. |
| 019 | fix | accept | fixed (question, gold, answer, evidence) | Điều 31 khoản 1 (15 days) applies only to the cases of Điều 30 khoản 1, i.e. permits that cease under khoản 2-7 Điều 156 BLLĐ. A permit that simply expires by term (khoản 1 Điều 156) is outside it, so "đã hết hiệu lực theo quy định" was too broad. Question names khoản 2-7 Điều 156, Điều 30 added to the gold, answer adds the report requirement. 15 days unchanged. A caught the premise gap; B accepted. |
| 024 | fix | accept | fixed (answer) | Out of scope confirmed. The old answer said the rate is in "pháp luật về bảo hiểm xã hội", which is an outside-law claim and the wrong law. Rewritten: it only states that the law on health insurance is not in the corpus, and lists the look-alike percentages (1% unemployment insurance, LVL2025 Điều 33; 30% wage-deduction cap, BLLĐ Điều 102). |
| 025 | accept | fix | fixed (question, answer) | Out of scope confirmed. BLLĐ Điều 97 khoản 4 requires compensation (at least the interest) for pay late 15 days or more in the force-majeure case. A model citing it should not be marked wrong, so the answer names it as compensation, not an administrative fine. "một tháng" dropped from the question (it implied a specific delay). |
| 031 | accept | fix | fixed (question, answer) | BLLĐ Điều 219 (amending Luật BHXH) is a second rule in the corpus on 61%+ incapacity (reduced-rate pension, up to 5 years lower for 61% to under 81%, up to 10 years lower for 81% and above). It is a pension-rate rule, not the early-retirement age of ND135 Điều 5, but the old "tối đa bao nhiêu tuổi" could be answered from either. Question and answer now cite khoản 1 Điều 5 ND135. Gold value (05 tuổi) unchanged. |
| 044 | accept | fix | fixed (question) | Gold and quote correct. "Thông tư về danh mục vùng này" had no antecedent. It now names the content of the Thông tư. |
| 047 | reject | fix | replaced | I side with A. B's rewrite still joins two unrelated rules (union-fee arrears as a prohibited act in LCD2024 Điều 10 khoản 5; 0,03%/ngày on late BHXH in ND274 Điều 7 khoản 2) by a made-up scenario. The two answer halves do not depend on each other, so the item is two lookups side by side. Replacement below. |
| 023 | accept | accept (note) | fixed (question wording) | B's non-blocking note adopted: the first sentence had no legal basis (rule 4 of the writer brief), so another decree's threshold could be argued. Now names ND 219/2025/NĐ-CP. Answer and evidence unchanged. |
| 036 | accept | accept (note) | kept | The nuance is real (ND274 Điều 5 khoản 1 still treats the amount as chậm đóng, so it remains due) but is not asked; the gold answers the question asked. Not added to the answer because it would need a second record. |

014: A's and B's notes on quote coverage are the same point, handled above.

## Replacement for LVN-047

- Question: a worker eligible for unemployment benefit, last contribution month April 2026, employer in vùng I; under Luật Việc làm 2025 and the regional minimum wage in Nghị định 293/2025/NĐ-CP, what is the maximum monthly unemployment benefit?
- Gold records: `LVL2025_Dieu_39` (khoản 1: not more than 05 times the regional monthly minimum wage applying in the last contribution month) and `ND293_2025_Dieu_3` (khoản 1: vùng I monthly minimum wage 5.310.000 đồng, hourly 25.500; khoản 3 điểm a: the region is the one where the employer operates).
- Answer: 05 x 5.310.000 = 26.550.000 đồng/tháng.
- Dates checked in the text: `LVL2025_Dieu_54` khoản 1 and `ND293_2025_Dieu_5` khoản 1 both print effective 01-01-2026, and ND293 Điều 5 khoản 2 repeals ND 74/2024 from that date, so April 2026 falls under both documents. These two records support the date but are not gold because the answer does not need them.
- Ambiguity removed: the question names ND293 as the source of the regional minimum wage ("do Chính phủ công bố" in Điều 39 is otherwise unspecific) and states the vùng, because the Phụ lục listing which localities are vùng I is not in the corpus. The 60% average-salary branch is not asked. ND293 Điều 5 khoản 5 (transitional protection for employers in re-zoned localities) concerns the employer's wage floor, not this cap. Overlap check: LVN-005 asks the rule (60%, cap of 05 lần) and LVN-009 / LVN-021 ask minimum wage values, but neither asks the combined figure.
- Status: authored and mechanically checked by the adjudicator only. It was not reviewed by the two independent verifiers (A only proposed the idea), so its `gold_status` is `ai_replacement_adjudicator_only_not_reviewed_by_independent_verifiers`, not the two-reviewer status.

## Kept as-is (39 tasks)

001, 003, 004, 005, 006, 007, 008, 009, 011, 012, 013, 015, 017, 018, 020, 021, 022, 026, 027, 028, 029, 030, 032, 033, 034, 035, 036, 037, 038, 039, 040, 041, 042, 043, 045, 046, 048, 049, 050. Both verifiers accepted each. Content fields are byte-identical to the draft; only `gold_status` and `verification` were added.

The five out_of_scope items (024, 025, 048, 049, 050) were re-searched over all 458 records at adjudication time with my own patterns; none is answered:

- 024: `tỷ lệ đóng`, `mức đóng bảo hiểm y tế`, `4,5 %`, `1,5 %`, `17,5` (0 hits each); `bảo hiểm y tế` next to a percentage only in BLLĐ Điều 102 (30% wage deduction cap); 1% in LVL2025 Điều 33 is unemployment insurance.
- 025 and 050: `triệu đồng`, `mức phạt`, `tiền phạt`, `nghìn đồng` (0 hits); `xử phạt` / `vi phạm hành chính` only in BLLĐ Điều 217, LVL2025 Điều 41, LCD2024 Điều 36, none with an amount; `tỷ đồng` only the 3 tỷ capital threshold (ND219 Điều 2, 7). ND274's 0,03%/ngày is a payment, not a fine.
- 048: `tỷ lệ hưởng` (ND135 Điều 7 khoản 3, no figure); `45 %` (0); `75 %` (BLLĐ Điều 84, collective agreements); `20 năm đóng` only BLLĐ Điều 219, which gives conditions for a reduced pension but no rate.
- 049: `thai sản` next to a percentage (0 hits); `trợ cấp thai sản` only BLLĐ Điều 139, which defers to the social-insurance law; `100 %` only capital shares and ND143 Điều 7 incapacity range.

## Information only: oracle signal on the draft

`evaluation/runs/labour-sanity-draft-v1/results.json` (Gemma-4-31B with the gold records as context, judged by DeepSeek Flash; LLM estimates, not labels) judged all 45 answerable draft items correct and all 5 refusals appropriate; closed-book 17 incorrect, 29 inappropriate refusals, 4 appropriate refusals. That run was on the draft, so it does not cover the changed items in their final wording (002, 010, 014, 016, 019, 023, 024, 025, 031, 044, 047). It was a pointer, not evidence for any decision. Lexical overlap with `expected_answer` is a lexical proxy, not answer correctness.

## Known limitations

1. AI-only verification. Drafting (Haiku), two verifications and the adjudication (Sonnet) are all model work. No human or legal expert reviewed any task. Status is "AI-verified, not human-reviewed". The two verifiers are independent of each other but share a model family with the adjudicator, so correlated misreadings of Vietnamese legal text are possible.
2. LVN-047 was written by the adjudicator and had no independent review.
3. NĐ 145/2020/NĐ-CP, the core implementing decree of the Labour Code, is not in the corpus (95 pages, over the 40-page limit). Questions on Labour Code procedure that need it are out of reach; an out_of_scope item that relies on that absence could be answerable with a different corpus.
4. Unnumbered annexes are not extracted: the Phụ lục of ND293_2025 (locality lists by wage region; 22.2% coverage) and the Danh mục of TT26_2025 (31.9% coverage), plus form annexes of ND318 and ND219. No task asks which locality belongs to which vùng or region; LVN-047 gives the vùng in the question for this reason.
5. TT26_2025: the PDF prints "Số: /2025/TT-BNV" with no date. Its number, issue date and signatory come from metadata on vanban.chinhphu.vn (docid 216367); the file hash matches the official attachment. The text in the corpus was not compared with a signed copy. No task asks for the number or date (LVN-044 was made self-contained without them).
6. Texts are as promulgated or printed in the PDFs, retrieved 2026-10-22. Later amendments or replacement were not checked for any document. Answers follow the corpus text, not a consolidated current text. BLLD2019 is the original Gazette text.
7. Table readings (ND293 Điều 3 minimum wage table, ND135 Điều 5 retirement-age table) come from extracted text; layout was inferred. The ND293 table reading ("Vùng I 5.310.000 25.500" is tháng, giờ) is relied on by LVN-009, 021 and 047.
8. A few items carry an in-corpus second rule that a model may cite (LVN-031 with BLLĐ Điều 219; LVN-025 with BLLĐ Điều 97). The questions and answers now say which rule is meant.
9. `expected_answer` is a short reference, not an exhaustive rubric.
