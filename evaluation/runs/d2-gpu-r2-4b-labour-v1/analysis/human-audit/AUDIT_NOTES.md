# Human Audit Report — `d2-gpu-r2-4b-labour-v1` (Vietnamese Labour Law Benchmark)

- **Run ID**: `d2-gpu-r2-4b-labour-v1`
- **Benchmark**: `labour_vi_v1` (Bộ luật Lao động 2019 và các văn bản hướng dẫn: Luật Việc làm 2025, Luật Công đoàn 2024, NĐ 135/2020/NĐ-CP, NĐ 143/2024/NĐ-CP, NĐ 219/2025/NĐ-CP, NĐ 274/2025/NĐ-CP, NĐ 293/2025/NĐ-CP, TT 26/2025/TT-BNV)
- **Reviewer**: `Võ Phạm Tuấn Dũng`
- **Sample Size**: 30 blinded packets (`analysis/human-audit/packets.json`)
- **LLM Judge Evaluated**: DeepSeek V4 Flash (`judge/judgments.jsonl`)

---

## 1. Agreement Summary (`agreement.json`)

| Dimension | `n` | Unweighted Agreement | Unweighted Cohen's $\kappa$ | Linear-Weighted $\kappa$ | Design-Weighted Agreement | Design-Weighted $\kappa$ |
|---|---:|---:|---:|---:|---:|---:|
| `judgeable` | 30 | 1.0000 | n/a | n/a | 1.0000 | n/a |
| `behaviour_appropriate` | 30 | 0.9333 | 0.8421 | n/a | 0.9786 | 0.9437 |
| `all_claims_supported` | 30 | 0.9333 | 0.6341 | n/a | 0.9864 | 0.7520 |
| `strict_success` | 30 | 0.9000 | 0.8000 | n/a | 0.9747 | 0.9481 |
| `correctness` | 30 | 0.9000 | 0.8207 | 0.8268 | 0.9747 | 0.9472 |
| `completeness` | 30 | 0.9333 | 0.8770 | 0.8611 | 0.9786 | 0.9583 |

- **Mean absolute difference on `unsupported_claims`**: `0.1333`
- **Judge strict success rate on sample**: `0.5000` (15/30)
- **Human strict success rate on sample**: `0.4667` (14/30)

---

## 2. Key Findings & Disagreements with DeepSeek V4 Flash

Across the 30 blinded audit items, the human audit and DeepSeek V4 Flash agreed on `strict_success` for **27/30 items (90.0% unweighted, 97.5% design-weighted)**. Detailed statutory inspection identified **3 disagreements on `strict_success`** (1 false negative and 2 false positives by the LLM judge) and **2 disagreements on `all_claims_supported`** (`unsupported_claims` count on out-of-scope questions where the candidate hallucinated an answer instead of refusing):

1. **Item 05 (`1855b06e6e6a91393209c539`) — Judge False Negative on a Valid Scope Refusal (`correctness`: Judge `1` vs. Human `2`; `strict_success`: Judge `False` vs. Human `True`)**:
   - **Context**: The question asks for the exact administrative fine in VND for evading social insurance contributions (`expected_behavior = "refuse"`). The candidate refused (`candidate_behavior = "refused"`), explaining that Điều 7 Nghị định 274/2025/NĐ-CP only regulates identifying late/evaded contributions and the interest calculation method, without stating a specific administrative fine in VND.
   - **Why the Judge erred**: Because `ground_truth_article_ids` and `candidate_citations` are empty on a `refuse` task, `source_articles` in the packet is empty (`[]`). DeepSeek V4 Flash treated the candidate's explanation of what Điều 7 Nghị định 274/2025/NĐ-CP covers as two `not_established` claims and penalized `correctness = 1`. However, on **Item 15 (`8dd7dd33906f5ba1cdaa47d5`)**—which tests the exact same question and has the exact same refusal explanation referencing Điều 7 Nghị định 274/2025/NĐ-CP—DeepSeek V4 Flash properly treated the absence explanation as non-claim refusal rationale and awarded `correctness = 2, completeness = 2, strict_success = True`. Checking the corpus confirms that Điều 7 Nghị định 274/2025/NĐ-CP is indeed titled *"Xác định hành vi chậm đóng, trốn đóng; tổ chức thu số tiền chậm đóng, trốn đóng và tổ chức thu số tiền bằng 0,03%/ngày..."*, matching both the `reference_answer` and the candidate's refusal explanation.

2. **Item 23 (`bc58b8439c731b9ecd2e279f`) — Judge False Positive on an Unjustified Refusal (`behaviour_appropriate`: Judge `1` vs. Human `0`; `correctness`: Judge `2` vs. Human `0`; `completeness`: Judge `2` vs. Human `0`; `strict_success`: Judge `True` vs. Human `False`)**:
   - **Context**: The question asks which minimum wage applies under Nghị định 293/2025 when an industrial park lies across regions with different minimum wage levels (`expected_behavior = "answer"`). Point c, Clause 3, Article 3 of Nghị định 293/2025/NĐ-CP (`ND293_2025_Dieu_3`, supplied in full in `source_articles`) explicitly states: *"áp dụng theo địa bàn có mức lương tối thiểu cao nhất"*.
   - **Why the Judge erred**: The candidate falsely refused (`candidate_behavior = "refused"`), claiming Nghị định 293/2025 was not in the loaded database. DeepSeek V4 Flash was misled by the generic `out_of_scope_hint` string appended to the `scope` field in `packets.json` and accepted the candidate's false excuse as a justified scope refusal, ignoring `expected_behavior = "answer"`, `reference_evidence`, and the supplied text of `ND293_2025_Dieu_3`.

3. **Item 28 (`db7028d53ce5ac1bff59fb50`) — Judge False Positive on an Unjustified Refusal (`behaviour_appropriate`: Judge `1` vs. Human `0`; `correctness`: Judge `2` vs. Human `0`; `completeness`: Judge `2` vs. Human `0`; `strict_success`: Judge `True` vs. Human `False`)**:
   - **Context**: The question asks about the qualifying contribution period for a 6-month labour contract and the unemployment benefit duration for 12 months of contributions under Luật Việc làm 2025 (`expected_behavior = "answer"`). `LVL2025_Dieu_38` (khoản 1 điểm b: đóng đủ 12 tháng trở lên trong thời gian 36 tháng) and `LVL2025_Dieu_39` (khoản 2: hưởng 03 tháng trợ cấp thất nghiệp) are both in the corpus and supplied in full in `source_articles`.
   - **Why the Judge erred**: Same failure mode as Item 23. The candidate refused (`candidate_behavior = "refused"`), claiming `Luật Việc làm 2025` was not in the database, and DeepSeek V4 Flash erroneously graded the refusal as `strict_success = True`.

4. **Items 13 (`892cee83031208c04188f2f5`) and 21 (`b8413c66fcaa181b08ebb542`) — Claim-Support Disagreement on Hallucinated Answers to Out-of-Scope Questions (`unsupported_claims`: Scored Judge `0` vs. Human `2`; `all_claims_supported`: Scored Judge `True` vs. Human `False`; both agree `strict_success = False`)**:
   - **Context**: Both items ask for the pension percentage rate after 20 years of social insurance contributions (`expected_behavior = "refuse"`, governed by Luật Bảo hiểm xã hội outside the corpus). In both trials, the candidate failed to refuse (`candidate_behavior = "answered"`) and asserted false legal rules:
     - In Item 13, the candidate claimed a retiree with 20 years receives 100% of their average monthly salary (*"bằng mức tiền lương tháng bình quân... không phải một phần trăm cố định cụ thể"*).
     - In Item 21, the candidate misattributed Article 55 (early retirement with reduced working capacity $\ge 61\%$, which receives a lower rate than Article 54(1)(a,b,c)) to Article 54 in `BLLD2019_Dieu_219`, claiming any retiree with 20 years gets a lower pension than Article 54(1)(a,b,c).
   - **Why Scored Judge and Human differed on `all_claims_supported`**: DeepSeek V4 Flash extracted 2 claims in each item and labelled them `not_established` (and set `behaviour_appropriate = 0, correctness = 0, completeness = 0`). Because `evaluation/judge_rules.py::is_abstention` returns `True` whenever `expected_behavior == "refuse"` *or* `candidate_behavior in ("refused", "clarified")`, `score_benchmark_audit.py::judge_verdicts` treated these `answered` outputs as abstentions and filtered out their `not_established` claims (`total_claims = 0, unsupported_claims = 0`). In the human audit, because the candidate actually *answered* (`candidate_behavior = "answered"`) with 2 unsupported/contradicted factual assertions, they are recorded as `total_claims = 2, unsupported_claims = 2`.

---

## 3. Item-by-Item Audit Table (All 30 Items)

| # | `review_id` | Expected / Cand. Behavior | Judge `(J, B, Corr, Comp, Tot, Unsup, Pass)` | Human `(J, B, Corr, Comp, Tot, Unsup, Pass)` | Match (`strict_success`) |
|---:|---|---|---|---|---|
| 01 | `029b2d982d6a34321be9ba7b` | `refuse` / `refused` | `(1, 1, 2, 2, 0, 0, True)` | `(1, 1, 2, 2, 0, 0, True)` | Agree |
| 02 | `044530bb94f9c2fdfe95a139` | `answer` / `answered` | `(1, 1, 2, 2, 3, 0, True)` | `(1, 1, 2, 2, 3, 0, True)` | Agree |
| 03 | `0a0becfc0b8aaba3b63771ee` | `answer` / `answered` | `(1, 1, 2, 2, 1, 0, True)` | `(1, 1, 2, 2, 1, 0, True)` | Agree |
| 04 | `11d8bd31568a02a5dfad0572` | `answer` / `clarified` | `(1, 0, 0, 0, 0, 0, False)` | `(1, 0, 0, 0, 0, 0, False)` | Agree |
| 05 | `1855b06e6e6a91393209c539` | `refuse` / `refused` | `(1, 1, 1, 2, 0, 0, False)` | `(1, 1, 2, 2, 0, 0, True)` | **Disagree** (`correctness`, `strict_success`) |
| 06 | `271ee759f2fe868768441457` | `answer` / `answered` | `(1, 1, 2, 2, 2, 0, True)` | `(1, 1, 2, 2, 2, 0, True)` | Agree |
| 07 | `2dd77b7a04cb10f9c1b5a816` | `answer` / `answered` | `(1, 1, 0, 0, 0, 0, False)` | `(1, 1, 0, 0, 0, 0, False)` | Agree |
| 08 | `3f7a911c3774f7fa3ffcedf6` | `answer` / `answered` | `(1, 1, 2, 2, 4, 0, True)` | `(1, 1, 2, 2, 4, 0, True)` | Agree |
| 09 | `3fbefd349dd6d2da4154d197` | `answer` / `answered` | `(1, 1, 2, 2, 2, 0, True)` | `(1, 1, 2, 2, 2, 0, True)` | Agree |
| 10 | `4ed8f94b335bae89f7ec1ef0` | `refuse` / `refused` | `(1, 1, 2, 2, 0, 0, True)` | `(1, 1, 2, 2, 0, 0, True)` | Agree |
| 11 | `533ef4f690467bf01d0e23c5` | `refuse` / `refused` | `(1, 1, 2, 2, 0, 0, True)` | `(1, 1, 2, 2, 0, 0, True)` | Agree |
| 12 | `85f60885fea727914c4dffdd` | `answer` / `answered` | `(1, 1, 2, 1, 1, 0, False)` | `(1, 1, 2, 1, 1, 0, False)` | Agree |
| 13 | `892cee83031208c04188f2f5` | `refuse` / `answered` | `(1, 0, 0, 0, 0, 0, False)` | `(1, 0, 0, 0, 2, 2, False)` | Agree (`strict_success`), Disagree (`all_claims_supported`) |
| 14 | `8b69e94c9acf57fa3eda167c` | `answer` / `answered` | `(1, 1, 2, 1, 2, 0, False)` | `(1, 1, 2, 1, 2, 0, False)` | Agree |
| 15 | `8dd7dd33906f5ba1cdaa47d5` | `refuse` / `refused` | `(1, 1, 2, 2, 0, 0, True)` | `(1, 1, 2, 2, 0, 0, True)` | Agree |
| 16 | `9fbeee721a00c211f6894e5b` | `answer` / `refused` | `(1, 0, 0, 0, 0, 0, False)` | `(1, 0, 0, 0, 0, 0, False)` | Agree |
| 17 | `a64a17d587c22dd67de00835` | `answer` / `answered` | `(1, 1, 0, 0, 1, 0, False)` | `(1, 1, 0, 0, 1, 0, False)` | Agree |
| 18 | `a8294431d2c86c98c4268a60` | `refuse` / `refused` | `(1, 1, 1, 2, 0, 0, False)` | `(1, 1, 1, 2, 0, 0, False)` | Agree |
| 19 | `b3c6ee7d26fad2acc6e64a02` | `answer` / `answered` | `(1, 1, 2, 2, 2, 0, True)` | `(1, 1, 2, 2, 2, 0, True)` | Agree |
| 20 | `b80ede0dcbd61b3322459b55` | `answer` / `refused` | `(1, 0, 0, 0, 1, 1, False)` | `(1, 0, 0, 0, 1, 1, False)` | Agree |
| 21 | `b8413c66fcaa181b08ebb542` | `refuse` / `answered` | `(1, 0, 0, 0, 0, 0, False)` | `(1, 0, 0, 0, 2, 2, False)` | Agree (`strict_success`), Disagree (`all_claims_supported`) |
| 22 | `b9f5e1637be037cb10a35451` | `answer` / `refused` | `(1, 0, 0, 0, 0, 0, False)` | `(1, 0, 0, 0, 0, 0, False)` | Agree |
| 23 | `bc58b8439c731b9ecd2e279f` | `answer` / `refused` | `(1, 1, 2, 2, 0, 0, True)` | `(1, 0, 0, 0, 0, 0, False)` | **Disagree** (`behaviour`, `correctness`, `completeness`, `strict_success`) |
| 24 | `bd27258fabc473ff7a827be4` | `answer` / `answered` | `(1, 1, 2, 2, 3, 0, True)` | `(1, 1, 2, 2, 3, 0, True)` | Agree |
| 25 | `c68217d84827d3f96ebd38d2` | `answer` / `answered` | `(1, 1, 2, 2, 4, 0, True)` | `(1, 1, 2, 2, 4, 0, True)` | Agree |
| 26 | `cf6561ede217489a42b657c3` | `answer` / `answered` | `(1, 1, 1, 2, 4, 1, False)` | `(1, 1, 1, 2, 4, 1, False)` | Agree |
| 27 | `cff3e9dadcf09e1db6d864b7` | `answer` / `answered` | `(1, 1, 2, 2, 2, 0, True)` | `(1, 1, 2, 2, 2, 0, True)` | Agree |
| 28 | `db7028d53ce5ac1bff59fb50` | `answer` / `refused` | `(1, 1, 2, 2, 0, 0, True)` | `(1, 0, 0, 0, 0, 0, False)` | **Disagree** (`behaviour`, `correctness`, `completeness`, `strict_success`) |
| 29 | `e08e88490328109f8bbbe66d` | `answer` / `answered` | `(1, 0, 0, 0, 1, 0, False)` | `(1, 0, 0, 0, 1, 0, False)` | Agree |
| 30 | `f69dbb3d93be8a0095ac6097` | `answer` / `refused` | `(1, 0, 0, 0, 0, 0, False)` | `(1, 0, 0, 0, 0, 0, False)` | Agree |

---

## 4. Detailed Item-by-Item Verification Notes

### Item 01 — `029b2d982d6a34321be9ba7b`
- **Question**: Người sử dụng lao động và người lao động phải đóng bảo hiểm y tế với tỷ lệ bao nhiêu phần trăm tiền lương hiện hành?
- **Expected / Candidate**: `refuse` / `refused`
- **Candidate Summary**: Refuses to provide a percentage rate, explaining that the retrieved labour law documents (BLLĐ 2019, Luật Việc làm 2025, NĐ 143/2024/NĐ-CP) only state general health insurance participation obligations without specifying the exact percentage rate.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Verification**: Accurate refusal. Health insurance contribution percentages are governed by health insurance legislation outside the 10-document labour corpus.

### Item 02 — `044530bb94f9c2fdfe95a139`
- **Question**: Theo Bộ luật Lao động 2019, mức lương tối thiểu được xác lập và ấn định theo những đơn vị nào, và theo Nghị định 293/2025 mức lương tối thiểu tháng và giờ của Vùng I là bao nhiêu?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: States minimum wage is established by region (`vùng`) and set by month and hour (`tháng, giờ`) per Điều 91 BLLĐ 2019, and Region I rates under NĐ 293/2025/NĐ-CP are 5.310.000 đồng/tháng and 25.500 đồng/giờ.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=3, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=3, unsupported_claims=0, strict_success=True`
- **Verification**: Fully supported by `BLLD2019_Dieu_91` (khoản 2) and `ND293_2025_Dieu_3` (khoản 1).

### Item 03 — `0a0becfc0b8aaba3b63771ee`
- **Question**: Nếu trong quá trình thực hiện có thay đổi tên gọi hoặc điều kiện kinh tế - xã hội của các vùng trong danh mục, các Bộ, ngành và Ủy ban nhân dân tỉnh, thành phố phải phản ánh về cơ quan nào?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Identifies **Bộ Nội vụ** per Điều 5 Thông tư 26/2025/TT-BNV.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=1, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=1, unsupported_claims=0, strict_success=True`
- **Verification**: Directly supported by `TT26_2025_Dieu_5` (khoản 3).

### Item 04 — `11d8bd31568a02a5dfad0572`
- **Question**: Theo Bộ luật Lao động 2019, người lao động thông thường được làm thêm giờ tối đa bao nhiêu giờ trong một năm, và giới hạn này được nâng lên trong trường hợp nào?
- **Expected / Candidate**: `answer` / `clarified`
- **Candidate Summary**: Emits a clarifying question asking what the annual overtime limit and exceptions are in Điều 107 BLLĐ 2019 instead of answering.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Verification**: Unjustified clarification on a clear question directly answered by `BLLD2019_Dieu_107` (khoản 2 điểm c: 200 giờ/năm; khoản 3: 300 giờ/năm).

### Item 05 — `1855b06e6e6a91393209c539`
- **Question**: Doanh nghiệp trốn đóng bảo hiểm xã hội sẽ bị phạt hành chính bao nhiêu tiền (tính bằng đồng) cho mỗi lần vi phạm?
- **Expected / Candidate**: `refuse` / `refused`
- **Candidate Summary**: Refuses to give a fine amount, noting that Điều 7 Nghị định 274/2025/NĐ-CP only covers determining late/evaded contribution behavior and the calculation method, without stating a specific administrative fine in VND.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=1, completeness=2, total_claims=0, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Verification**: **Disagreement with Judge.** The candidate's refusal explanation accurately describes Điều 7 Nghị định 274/2025/NĐ-CP in the corpus (*"Xác định hành vi chậm đóng, trốn đóng; tổ chức thu số tiền chậm đóng, trốn đóng và tổ chức thu số tiền bằng 0,03%/ngày..."*) and matches the `reference_answer`. DeepSeek V4 Flash penalized `correctness=1` only because `source_articles` is empty on `refuse` packets, contradicting its own `2/2` rating on Item 15 (`8dd7dd33906f5ba1cdaa47d5`) for the same question and refusal reason.

### Item 06 — `271ee759f2fe868768441457`
- **Question**: Người lao động đã đủ điều kiện đóng bảo hiểm thất nghiệp muốn hưởng trợ cấp thất nghiệp theo Luật Việc làm 2025 thì phải nộp đủ hồ sơ trong thời hạn bao lâu kể từ ngày chấm dứt hợp đồng lao động?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Answers **03 tháng** from termination of the labour contract, work contract, or employment, citing `LVL2025_Dieu_38` (with a parenthetical self-correction noting the update to Luật Việc làm 2025).
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=2, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=2, unsupported_claims=0, strict_success=True`
- **Verification**: Fully supported by `LVL2025_Dieu_38` (khoản 1 điểm c).

### Item 07 — `2dd77b7a04cb10f9c1b5a816`
- **Question**: Theo Luật Việc làm 2025, mức đóng bảo hiểm thất nghiệp tối đa của người lao động và của người sử dụng lao động là bao nhiêu phần trăm?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: `candidate_answer` stops after the introductory colon (*"Theo Điều 33 Luật Việc làm 2019 (Lưu ý: văn bản tìm thấy là Luật Việc làm 2025), mức đóng bảo hiểm thất nghiệp như sau:"*), placing the 1% figures only in `citations`.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Verification**: The answer text (`content`) omits the required 1% rates (`LVL2025_Dieu_33` khoản 1 điểm a, b), so `correctness=0` and `completeness=0`.

### Item 08 — `3f7a911c3774f7fa3ffcedf6`
- **Question**: Doanh nghiệp gặp khó khăn phải tạm dừng sản xuất, kinh doanh và không có khả năng đóng kinh phí công đoàn thì có thể được tạm dừng đóng tối đa bao lâu? Khi hết thời hạn tạm dừng thì phải đóng bù như thế nào?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: States maximum suspension is **không quá 12 tháng**, and upon expiration the enterprise must continue paying and pay back (`đóng bù`) the suspended months' amount no later than the last day of the month following the end of the suspension (`LCD2024_Dieu_30`).
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=4, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=4, unsupported_claims=0, strict_success=True`
- **Verification**: Complete and accurate per `LCD2024_Dieu_30` (khoản 3).

### Item 09 — `3fbefd349dd6d2da4154d197`
- **Question**: Theo Bộ luật Lao động 2019, mức lương tối thiểu được xác lập và ấn định theo những đơn vị nào, và theo Nghị định 293/2025 mức lương tối thiểu tháng và giờ của Vùng I là bao nhiêu?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: States established by region and set by month and hour (Điều 91 BLLĐ 2019), and Region I monthly/hourly minimum wages are 5.310.000 đồng and 25.500 đồng (NĐ 293/2025/NĐ-CP).
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=2, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=2, unsupported_claims=0, strict_success=True`
- **Verification**: Complete and accurate per `BLLD2019_Dieu_91` (khoản 2) and `ND293_2025_Dieu_3` (khoản 1).

### Item 10 — `4ed8f94b335bae89f7ec1ef0`
- **Question**: Công ty trả lương chậm cho nhân viên thì bị cơ quan nhà nước xử phạt vi phạm hành chính bao nhiêu tiền?
- **Expected / Candidate**: `refuse` / `refused`
- **Candidate Summary**: Refuses to answer without verified search evidence for the specific administrative fine amount.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Verification**: Appropriate refusal on an out-of-scope question (`expected_behavior = refuse`) with zero fabricated claims.

### Item 11 — `533ef4f690467bf01d0e23c5`
- **Question**: Người đóng đủ 20 năm bảo hiểm xã hội khi nghỉ hưu thì được hưởng lương hưu bằng bao nhiêu phần trăm mức bình quân tiền lương đóng bảo hiểm?
- **Expected / Candidate**: `refuse` / `refused`
- **Candidate Summary**: Refuses, explaining that BLLĐ 2019 does not contain the specific pension calculation percentage and that this information lies in Luật Bảo hiểm xã hội.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Verification**: Exact, well-grounded scope refusal matching `reference_answer`.

### Item 12 — `85f60885fea727914c4dffdd`
- **Question**: Theo Nghị định 219/2025/NĐ-CP, người nước ngoài là chủ sở hữu công ty trách nhiệm hữu hạn muốn không phải xin giấy phép lao động khi làm việc tại Việt Nam thì giá trị góp vốn tối thiểu là bao nhiêu? Bộ luật Lao động 2019 quy định mức này như thế nào?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Correctly states the threshold of **từ 3 tỷ đồng trở lên** per Điều 7 NĐ 219/2025/NĐ-CP, but omits how BLLĐ 2019 (Điều 154 khoản 1) regulates the threshold (delegating to Government regulation).
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=1, total_claims=1, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=1, total_claims=1, unsupported_claims=0, strict_success=False`
- **Verification**: Correct on the first sub-question (`correctness=2`), incomplete on the second sub-question (`completeness=1`).

### Item 13 — `892cee83031208c04188f2f5`
- **Question**: Người đóng đủ 20 năm bảo hiểm xã hội khi nghỉ hưu thì được hưởng lương hưu bằng bao nhiêu phần trăm mức bình quân tiền lương đóng bảo hiểm?
- **Expected / Candidate**: `refuse` / `answered`
- **Candidate Summary**: Instead of refusing, answers that a worker with 20 years of social insurance contributions receives a pension equal to the **average monthly salary** (*"mức tiền lương tháng bình quân"*) and that it is **not a fixed specific percentage**.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False` (raw judge extracted 2 `not_established` claims, which `judge_rules.is_abstention` filtered out because `expected_behavior == "refuse"`).
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=2, unsupported_claims=2, strict_success=False`
- **Verification**: Candidate failed to refuse (`candidate_behavior = answered`) and fabricated 2 unsupported legal claims not in `BLLD2019_Dieu_219`. Both Judge and Human agree on `strict_success=False, behaviour_appropriate=0, correctness=0, completeness=0`.

### Item 14 — `8b69e94c9acf57fa3eda167c`
- **Question**: Thời gian làm việc trước ngày 01/01/2021 ở nơi có phụ cấp khu vực hệ số 0,7 trở lên có được tính vào 15 năm làm việc ở vùng khó khăn để nghỉ hưu sớm theo Nghị định 135/2020 không? Thông tư về danh mục vùng xác định thời gian đó như thế nào?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Correctly answers the first sub-question using Điều 5 khoản 1 điểm b NĐ 135/2020/NĐ-CP, and notes the Minister of MOLISA issues the region list, but omits the rule in Điều 4 khoản 2 điểm a Thông tư 26/2025/TT-BNV.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=1, total_claims=2, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=1, total_claims=2, unsupported_claims=0, strict_success=False`
- **Verification**: Accurate on NĐ 135/2020/NĐ-CP (`correctness=2, total_claims=2, unsupported_claims=0`), incomplete because it misses `TT26_2025_Dieu_4` (`completeness=1`).

### Item 15 — `8dd7dd33906f5ba1cdaa47d5`
- **Question**: Doanh nghiệp trốn đóng bảo hiểm xã hội sẽ bị phạt hành chính bao nhiêu tiền (tính bằng đồng) cho mỗi lần vi phạm?
- **Expected / Candidate**: `refuse` / `refused`
- **Candidate Summary**: Refuses, noting that Điều 7 NĐ 274/2025/NĐ-CP and related corpus texts only specify the 0,03%/ngày late/evaded payment mechanism and responsibility for determining violations, not a specific administrative fine in VND.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Verification**: Proper refusal matching corpus scope and `reference_answer`.

### Item 16 — `9fbeee721a00c211f6894e5b`
- **Question**: Người lao động làm việc không theo hợp đồng lao động, không thuộc hộ nghèo hay hộ cận nghèo, khi tham gia bảo hiểm tai nạn lao động tự nguyện thì Nhà nước hỗ trợ tiền đóng bằng bao nhiêu phần trăm?
- **Expected / Candidate**: `answer` / `refused`
- **Candidate Summary**: System refusal after 2 failed L1 verifier repair attempts because the candidate's cited quote from `ND143_2024_Dieu_12` was truncated before điểm c (`10%`).
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Verification**: Unjustified refusal on an in-scope question directly answered by `ND143_2024_Dieu_12` khoản 1 điểm c (`10%`).

### Item 17 — `a64a17d587c22dd67de00835`
- **Question**: Tiền lương làm căn cứ đóng bảo hiểm thất nghiệp có mức cao nhất bằng bao nhiêu lần mức lương tối thiểu tháng theo vùng?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Answers 05 times the regional minimum monthly wage based on Điều 39 khoản 1 Luật Việc làm 2025 (which is the maximum *benefit* level, not the maximum *contribution salary basis* of 20 times in Điều 34 khoản 2).
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=0, completeness=0, total_claims=1, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=0, completeness=0, total_claims=1, unsupported_claims=0, strict_success=False`
- **Verification**: Confuses maximum benefit cap (`LVL2025_Dieu_39`: 05 lần) with maximum contribution salary basis (`LVL2025_Dieu_34` khoản 2: 20 lần).

### Item 18 — `a8294431d2c86c98c4268a60`
- **Question**: Lao động nữ nghỉ thai sản thì được trợ cấp thai sản từ bảo hiểm xã hội bằng bao nhiêu phần trăm tiền lương?
- **Expected / Candidate**: `refuse` / `refused`
- **Candidate Summary**: Refuses to provide a percentage from the loaded corpus, but parenthetically asserts that `Nghị định 28/2019/NĐ-CP` must be read to confirm the maternity benefit rate.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=1, completeness=2, total_claims=0, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=1, completeness=2, total_claims=0, unsupported_claims=0, strict_success=False`
- **Verification**: Refusal behavior is appropriate, but citing `Nghị định 28/2019/NĐ-CP` as the source for maternity benefit percentage is factually wrong (maternity benefits are governed by Luật Bảo hiểm xã hội, as noted in `BLLD2019_Dieu_139`), justifying `correctness=1`.

### Item 19 — `b3c6ee7d26fad2acc6e64a02`
- **Question**: Theo Nghị định 219/2025/NĐ-CP, người nước ngoài là chủ sở hữu công ty trách nhiệm hữu hạn muốn không phải xin giấy phép lao động khi làm việc tại Việt Nam thì giá trị góp vốn tối thiểu là bao nhiêu? Bộ luật Lao động 2019 quy định mức này như thế nào?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: States **từ 3 tỷ đồng trở lên** per Điều 7 NĐ 219/2025/NĐ-CP and explains that Điều 154 BLLĐ 2019 delegates the capital contribution threshold to Government regulation.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=2, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=2, unsupported_claims=0, strict_success=True`
- **Verification**: Complete and accurate per `ND219_2025_Dieu_7` (khoản 2) and `BLLD2019_Dieu_154` (khoản 1).

### Item 20 — `b80ede0dcbd61b3322459b55`
- **Question**: Thời gian làm việc trước ngày 01/01/2021 ở nơi có phụ cấp khu vực hệ số 0,7 trở lên có được tính vào 15 năm làm việc ở vùng khó khăn để nghỉ hưu sớm theo Nghị định 135/2020 không? Thông tư về danh mục vùng xác định thời gian đó như thế nào?
- **Expected / Candidate**: `answer` / `refused`
- **Candidate Summary**: Refuses, claiming Thông tư 26/2025 only states the legal basis and cannot determine the regions/time period asked by the user.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=1, unsupported_claims=1, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=1, unsupported_claims=1, strict_success=False`
- **Verification**: Unjustified refusal; the claim about Thông tư 26/2025 is directly contradicted by `TT26_2025_Dieu_4` khoản 2 điểm a.

### Item 21 — `b8413c66fcaa181b08ebb542`
- **Question**: Người đóng đủ 20 năm bảo hiểm xã hội khi nghỉ hưu thì được hưởng lương hưu bằng bao nhiêu phần trăm mức bình quân tiền lương đóng bảo hiểm?
- **Expected / Candidate**: `refuse` / `answered`
- **Candidate Summary**: Instead of refusing, answers using `BLLD2019_Dieu_219`, conflating Điều 55 (reduced working capacity retirement) with Điều 54 and asserting that a worker with 20 years of social insurance receives a **lower** pension rate than Điều 54(1)(a,b,c) without a fixed percentage.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False` (raw judge extracted 2 `not_established` claims filtered by `is_abstention`).
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=2, unsupported_claims=2, strict_success=False`
- **Verification**: Candidate answered an out-of-scope `refuse` question with 2 distorted/unsupported legal claims misreading Điều 54 and Điều 55 in `BLLD2019_Dieu_219`. Both Judge and Human agree on `strict_success=False`.

### Item 22 — `b9f5e1637be037cb10a35451`
- **Question**: Theo Nghị định 219/2025/NĐ-CP, người nước ngoài là chủ sở hữu công ty trách nhiệm hữu hạn muốn không phải xin giấy phép lao động khi làm việc tại Việt Nam thì giá trị góp vốn tối thiểu là bao nhiêu? Bộ luật Lao động 2019 quy định mức này như thế nào?
- **Expected / Candidate**: `answer` / `refused`
- **Candidate Summary**: Refuses to answer, stating that Nghị định 219/2025/NĐ-CP needs to be searched first.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Verification**: Unjustified refusal on an in-corpus question answered by `ND219_2025_Dieu_7` and `BLLD2019_Dieu_154`.

### Item 23 — `bc58b8439c731b9ecd2e279f`
- **Question**: Doanh nghiệp hoạt động trong khu công nghiệp mà khu này nằm trên các địa bàn có mức lương tối thiểu khác nhau thì phải áp dụng mức lương tối thiểu nào theo Nghị định 293/2025?
- **Expected / Candidate**: `answer` / `refused`
- **Candidate Summary**: Refuses, claiming Nghị định 293/2025 is not in the loaded database.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Verification**: **Disagreement with Judge.** This is an answerable in-corpus question (`expected_behavior = answer`), directly answered by `ND293_2025_Dieu_3` khoản 3 điểm c (*"áp dụng theo địa bàn có mức lương tối thiểu cao nhất"*), which is supplied in `source_articles`. DeepSeek V4 Flash was fooled by the candidate's false refusal and the generic `out_of_scope_hint` string in `scope`.

### Item 24 — `bd27258fabc473ff7a827be4`
- **Question**: Theo Nghị định 219/2025/NĐ-CP, người nước ngoài là chủ sở hữu công ty trách nhiệm hữu hạn muốn không phải xin giấy phép lao động khi làm việc tại Việt Nam thì giá trị góp vốn tối thiểu là bao nhiêu? Bộ luật Lao động 2019 quy định mức này như thế nào?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Correctly states **3 tỷ đồng** under Điều 7 NĐ 219/2025/NĐ-CP and explains that Điều 154 khoản 1 BLLĐ 2019 delegates the capital contribution threshold to the Government.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=3, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=3, unsupported_claims=0, strict_success=True`
- **Verification**: Complete and accurate per `ND219_2025_Dieu_7` (khoản 2) and `BLLD2019_Dieu_154` (khoản 1).

### Item 25 — `c68217d84827d3f96ebd38d2`
- **Question**: Doanh nghiệp gặp khó khăn phải tạm dừng sản xuất, kinh doanh và không có khả năng đóng kinh phí công đoàn thì có thể được tạm dừng đóng tối đa bao lâu? Khi hết thời hạn tạm dừng thì phải đóng bù như thế nào?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: States maximum suspension is **không quá 12 tháng**, and upon expiration the enterprise must continue paying and `đóng bù` the suspended months' amount no later than the last day of the month following the end of the suspension (`LCD2024_Dieu_30`).
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=4, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=4, unsupported_claims=0, strict_success=True`
- **Verification**: Complete and accurate per `LCD2024_Dieu_30` (khoản 3).

### Item 26 — `cf6561ede217489a42b657c3`
- **Question**: Người lao động đủ điều kiện hưởng trợ cấp thất nghiệp, có tháng cuối cùng đóng bảo hiểm thất nghiệp là tháng 4 năm 2026, làm việc cho người sử dụng lao động hoạt động trên địa bàn thuộc vùng I. Theo Luật Việc làm 2025 và mức lương tối thiểu tháng theo vùng quy định tại Nghị định 293/2025/NĐ-CP, mức trợ cấp thất nghiệp hằng tháng tối đa người này có thể được hưởng là bao nhiêu đồng?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Cites `LVL2025_Dieu_39` and `ND293_2025_Dieu_3` (5.310.000 đồng) and arrives at 26.550.000 đồng, but writes the intermediate formula `= 05 lần mức lương tối thiểu tháng theo vùng × 60% = 5 × 5.310.000 đồng × 0,60 = 26.550.000 đồng`.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=1, completeness=2, total_claims=4, unsupported_claims=1, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=1, completeness=2, total_claims=4, unsupported_claims=1, strict_success=False`
- **Verification**: The intermediate formula multiplying the 5x regional minimum wage cap by 60% is both legally wrong under `LVL2025_Dieu_39` khoản 1 (the cap itself is $5 \times 5.310.000 = 26.550.000\text{ đồng}$) and arithmetically inconsistent ($5 \times 5.310.000 \times 0.60 = 15.930.000$, not $26.550.000$). Thus `correctness=1, completeness=2, total_claims=4, unsupported_claims=1`.

### Item 27 — `cff3e9dadcf09e1db6d864b7`
- **Question**: Trước ngày nào của tháng đầu quý tiếp theo, cơ quan bảo hiểm xã hội cấp tỉnh phải gửi thông tin về người sử dụng lao động chậm đóng, trốn đóng (tính đến hết quý) đến cơ quan quản lý nhà nước về bảo hiểm xã hội và cơ quan thanh tra?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Answers **trước ngày 15 của tháng đầu quý tiếp theo** per Điều 3 khoản 3 điểm a Nghị định 274/2025/NĐ-CP.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=2, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=2, unsupported_claims=0, strict_success=True`
- **Verification**: Directly supported by `ND274_2025_Dieu_3` (khoản 3 điểm a).

### Item 28 — `db7028d53ce5ac1bff59fb50`
- **Question**: Người lao động ký hợp đồng có thời hạn 6 tháng muốn hưởng trợ cấp thất nghiệp theo Luật Việc làm 2025 thì phải đóng bảo hiểm thất nghiệp đủ bao nhiêu tháng trong bao nhiêu tháng trước khi chấm dứt hợp đồng, và nếu đóng đủ 12 tháng thì được hưởng bao nhiêu tháng trợ cấp?
- **Expected / Candidate**: `answer` / `refused`
- **Candidate Summary**: Refuses, claiming `Luật Việc làm 2025` is not in the loaded database.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=1, correctness=2, completeness=2, total_claims=0, unsupported_claims=0, strict_success=True`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Verification**: **Disagreement with Judge.** Same error as Item 23: `expected_behavior` is `answer`, and `LVL2025_Dieu_38` (khoản 1 điểm b: đóng đủ 12 tháng trở lên trong thời gian 36 tháng) and `LVL2025_Dieu_39` (khoản 2: hưởng 03 tháng trợ cấp thất nghiệp) are in the corpus and supplied in `source_articles`. The candidate's refusal is unjustified (`behaviour_appropriate=0, correctness=0, completeness=0`).

### Item 29 — `e08e88490328109f8bbbe66d`
- **Question**: Theo Nghị định 293/2025, mức lương tối thiểu tháng là mức lương thấp nhất với điều kiện người lao động phải làm việc và hoàn thành công việc như thế nào?
- **Expected / Candidate**: `answer` / `answered`
- **Candidate Summary**: Truncated after the introductory colon (*"Theo Nghị định 293/2025/NĐ-CP, mức lương tối thiểu tháng được áp dụng đối với người lao động có hai điều kiện bắt buộc về việc hoàn thành công việc:"*), omitting the actual conditions from `content`.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=1, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=1, unsupported_claims=0, strict_success=False`
- **Verification**: Fails to state the two conditions in `ND293_2025_Dieu_4` khoản 1 (*làm việc đủ thời giờ làm việc bình thường trong tháng* and *hoàn thành định mức lao động hoặc công việc đã thỏa thuận*).

### Item 30 — `f69dbb3d93be8a0095ac6097`
- **Question**: Theo Bộ luật Lao động 2019, người lao động thông thường được làm thêm giờ tối đa bao nhiêu giờ trong một năm, và giới hạn này được nâng lên trong trường hợp nào?
- **Expected / Candidate**: `answer` / `refused`
- **Candidate Summary**: Refuses because `search_law` was not executed.
- **Judge Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Human Verdict**: `judgeable=1, behaviour_appropriate=0, correctness=0, completeness=0, total_claims=0, unsupported_claims=0, strict_success=False`
- **Verification**: Unjustified refusal on an in-corpus question answered by `BLLD2019_Dieu_107`.
