# Adjudication of the hcmut_v1 draft (50 tasks), 23 Oct 2026

Adjudicator: Claude Sonnet (AI). Inputs: `draft_all.json` (Claude Haiku draft), `verify_A.json` and `verify_B.json` (two independent Claude Sonnet verifiers), the corpus `data/corpus/hcmut_academic_v1.json`, and `docs/materials/hcmut-sources/manifest.json` + `README.md`. Output: `tasks.json`.

Method: for every task flagged by either verifier I read the cited records in full, decided independently, and applied the best-supported fix (merging the verifiers' fixes where useful). Scope rule from the project owner: edit only for correctness (wrong or incomplete answer, insufficient gold, a quote that does not support the answer, an ambiguous question with more than one defensible answer, an out-of-scope item the corpus answers) and replace HCMUT-021. Closed-book guessability was not used as a reason to rewrite anything.

Verdict totals: verify_A accept 41 / fix 8 / reject 1; verify_B accept 46 / fix 3 / reject 1. Final: 38 kept unchanged, 3 kept after a flag or note (038, 039, 046), 8 fixed, 1 replaced.

## Changed or flagged tasks

| Task | verify_A | verify_B | Decision | Reason |
|---|---|---|---|---|
| 005 | fix | accept | fixed (evidence + answer wording) | Old quote ended at "Anh văn 1", so "2, 3, 4", the table 3.1 reference and the TOEIC-format test were not supported by evidence. The answer was right against the full text. Two verbatim quotes now cover the TOEIC test and the exemption sentence. |
| 014 | fix | accept | fixed (answer) | Answer added "(đăng ký trước 16g00 của ngày làm việc đó)", an inexact paraphrase not asked for. Answer is now "tối thiểu 01 ngày và tối đa 07 ngày trước ngày dạy bù". |
| 016 | fix | accept | fixed (question, answer, quote) | "Điều kiện gì" is ambiguous: Phụ lục 2 mục 2 lists further requirements (research/teaching experience, foreign language). Question narrowed to the degree route (Thạc sĩ: trường đại học nước ngoài, đúng ngành hoặc ngành gần). Two split quotes merged. |
| 021 | reject | reject | replaced (new multi task) | Artificial conjunction of two unrelated questions. The first half rested on a purpose clause (HOCPHI2800 Điều 3) and equated "tạm dừng học tập" with the different "tạm dừng quá 02 học kỳ chính" of HVDT1260 14.3; the second half duplicated HCMUT-004. Replacement below. |
| 022 | fix | fix | fixed (question, answer) | "Đủ điều kiện đăng ký học phần tốt nghiệp" was overclaimed: khoản 5.5 also needs foreign-language standard, cumulative-credit percentages, etc. Question now asks only for the GPA threshold (2.0, thang 4, from HK1 2025-2026), whether 2,35 reaches it, and the 15.2 rank (Trung bình). |
| 023 | fix | accept | fixed (evidence, answer wording) | Old quote "tập của người học được giữ nguyên" began mid-sentence and did not support the stated conditions. Replaced by the full 25.5 sentence. Table 3.1 reading verified (Kế hoạch / Chuẩn / Tối đa, so 16). The conditions are now marked as a qualification, because the oracle run scored the item partially correct for omitting them although the question does not ask for them. |
| 032 | fix | accept | fixed (question, answer, quote) | "Loại sản phẩm nào khác cũng bị cấm hút" has a second defensible answer (drugs and stimulants in the same khoản). Question now targets the parenthetical "(bao gồm thuốc lá điện tử)". Split quotes merged. |
| 036 | accept | fix | fixed (evidence only) | "Tổng tín chỉ 128–132" occurs several times (ABET table, FIBAA table, appendix) and did not pin the ABET table. New quote ends in the ABET block row (68–72, unique) and the Toán quote includes its heading. Answer unchanged. |
| 038 | fix | accept | kept | A: question lacks regulation context. Not a correctness problem: no other document in the corpus concerns đội thi, so the answer (01 lần ở mỗi mức) is determinate. |
| 039 | accept | accept | kept (information) | Oracle run answered 27 (confused "nhóm SV" with "giải đồng đội"). Gold 18 is correct per VINHDANH658 Điều 5. The source does not define the difference between the two labels, so the item is hard; the question uses the source's label "nhóm SV". |
| 046 | accept | accept | kept (information) | Gold correct. B notes the Nội quy half repeats HCMUT-033. Kept as instructed because it is not incorrect; recorded as a near-duplicate in part. |
| 047 | fix | fix | fixed (question, answer, quote) | The 9 credits is a requirement on the training programme, not on the student, and the GVCN2977 record did not contribute to the number. Question now asks for the CVHT duty and the programme minimum separately so both records are needed. Limitation: two independent facts joined by a conjunction. |

## Replacement for HCMUT-021

- Question: "Người học muốn xin gia hạn thời gian nộp học phí thì nộp đơn đăng ký về phòng nào, và phòng đó giữ những chức danh nào trong Hội đồng xét hồ sơ xin gia hạn?"
- Gold records: `HCMUT_HOCPHI2800_Dieu_7` (Bước 1: nộp về Phòng Công tác sinh viên), `HCMUT_HOCPHI2800_Dieu_8` (Trưởng Phòng CTSV là Phó Chủ tịch; Phó Trưởng phòng CTSV là thư ký).
- Answer: Phòng Công tác sinh viên; Trưởng Phòng là Phó Chủ tịch Hội đồng, Phó Trưởng phòng là thư ký.
- The second part depends on the first (the unit found in Điều 7 is looked up in the Điều 8 member list). It does not use base regulations or printed numbers and dates. HCMUT-020 asks about the Chủ tịch only, so there is no overlap.
- Status: authored and mechanically checked by the adjudicator only. It was not reviewed by the two independent verifiers, so its `gold_status` is `ai_replacement_adjudicator_only_not_reviewed_by_independent_verifiers`, not the two-reviewer status.

## Kept as-is (38 tasks)

001, 002, 003, 004, 006, 007, 008, 009, 010, 011, 012, 013, 015, 017, 018, 019, 020, 024, 025, 026, 027, 028, 029, 030, 031, 033, 034, 035, 037, 040, 041, 042, 043, 044, 045, 048, 049, 050. Both verifiers accepted each of these. Content fields are byte-identical to the draft; only `gold_status` and `verification` were added.

The five out_of_scope items (024, 025, 048, 049, 050) were re-checked by keyword search over all 143 records at adjudication time: no record answers them (024: only the generic tuition notice clause in HVCHUNG1259 Điều 23.1; 048: one passing mention of "học bổng" in GVCN2977 Điều 9 with no criteria; 025, 049: zero hits for phúc khảo/chấm lại/công bố điểm and ký túc/nội trú; 050: no fines, only the Nội quy ban on motorbikes).

## Information only: closed-book signal

In the sanity run (`evaluation/runs/hcmut-sanity-draft-v2/results.json`; Gemma-4-31B answers judged by DeepSeek Flash; LLM estimates, not labels) the closed-book condition was judged "correct" on 003, 006, 007, 010, 013, 018, 027, 030, 032, 035, 043, 045, 046. Several are guessable from common knowledge (030 đeo thẻ trong khuôn viên; 043 email do Trường cấp; 045 quy định tại thời điểm hành vi; 032 thuốc lá điện tử; 027 từ cảnh cáo) and others are round-number guesses (003 5%, 013 20%, 035 20%). They were left unchanged by decision of the project owner. Results on these items measure parametric knowledge as much as retrieval, so a retrieval benefit should be read from the other items or from the closed-book vs. oracle gap. Oracle failures: 039 (gold re-checked, correct), 023 (partial; answer text revised as above).

## Known limitations

1. AI-only verification. Drafting (Haiku), two verifications and the adjudication (Sonnet) are all model work. No human or domain expert reviewed any task. Labels are "AI-verified, not human-reviewed".
2. The two Sonnet verifiers are independent of each other but share a model family with the adjudicator, so correlated misreadings of Vietnamese legal text are possible.
3. Amendment-only documents. HVDT1260, HVDT2749, HVCHUNG1259, GIANGDAY2282 and CTDT1862 contain only changed clauses; their base regulations (2933, 2931, 2929, 3538) are not in the corpus. Questions are limited to what the amendment text states, and a rule in an amendment may be incomplete without its base.
4. Base regulations are missing, so core undergraduate rules (cảnh báo học vụ, buộc thôi học conditions, bảo lưu, chuyển ngành, điểm rèn luyện) are absent. Some out_of_scope items rely on this absence; a different corpus version could answer them.
5. Printed decision numbers and dates are blank in all 10 PDFs and come from the website listing (unverified against signed copies). No task asks about them. The date conflict for 1260 (15/03 vs 16/03/2026) is unresolved.
6. Versions and supersession of the documents were not verified; the corpus is a snapshot retrieved on 2026-10-22.
7. Table readings (HVDT1260 3.1, CTDT1862 Điều 6, HVDT2749 Phụ lục 1) come from text extracted with pypdf; layout was inferred. Cell reading was checked by the verifiers and again here for 023 and 036 only.
8. Closed-book guessable items remain (see above); 046 partly duplicates 033; 047 and 022 are conjunctions of independent facts rather than reasoning chains; 021 has had no independent verification.
9. `expected_answer` is a short reference, not an exhaustive rubric. Lexical overlap with it is a lexical proxy, not evidence of correctness.
