# Báo Cáo Kiểm Toán Độc Lập (Human Audit Report) — Run `d2-gpu-r2-4b-hcmut-v1`

- **Run ID:** `d2-gpu-r2-4b-hcmut-v1` (HCMUT Regulations Benchmark — Qwen3-4B)
- **Người kiểm toán (Reviewer):** Võ Phạm Tuấn Dũng (`MSHV: 2570015`, Khoa KH&KT Máy tính, Trường ĐH Bách Khoa — ĐHQG-HCM)
- **Quy mô mẫu kiểm toán mù (Stratified Blind Audit Sample):** 30 mẫu (`packets.json`, phủ 100% mẫu)
- **Mô hình giám khảo đối chiếu (LLM Judge):** DeepSeek V4 Flash (`judge/judgments.jsonl`)
- **Trạng thái chấm đối chiếu (`score_benchmark_audit.py`):** `ok` (`labelled_items = 30/30`)

---

## 1. Tổng Hợp Độ Đồng Thuận Giữa Giám Khảo LLM và Người Kiểm Toán (`agreement.json`)

| Tiêu chí (Dimension) | Số mẫu ($n$) | Đồng thuận thô (Unweighted Agreement) | Hệ số $\kappa$ (Unweighted Kappa) | Đồng thuận có trọng số thiết kế (Weighted Agreement) | Hệ số $\kappa$ có trọng số thiết kế (Weighted Kappa) | $\kappa$ tuyến tính (Linear-Weighted Kappa) |
|---|---:|---:|---:|---:|---:|---:|
| `judgeable` | 30 | **1.000** (30/30) | `n/a` (cả hai đều = 1) | **1.000** | `n/a` | — |
| `behaviour_appropriate` | 30 | **1.000** (30/30) | **1.000** | **1.000** | **1.000** | — |
| `completeness` | 30 | **1.000** (30/30) | **1.000** | **1.000** | **1.000** | **1.000** |
| `correctness` | 30 | **0.967** (29/30) | **0.939** | **0.988** | **0.975** | **0.964** |
| `strict_success` | 30 | **0.967** (29/30) | **0.933** | **0.988** | **0.974** | — |
| `all_claims_supported` | 30 | **0.867** (26/30) | **0.429** | **0.971** | **0.858** | — |

- **Tỷ lệ `strict_success` trên tập mẫu 30 câu:**
  - Giám khảo DeepSeek V4 Flash: **53.33%** (16/30 mẫu đạt `strict_success`)
  - Người kiểm toán (Võ Phạm Tuấn Dũng): **56.67%** (17/30 mẫu đạt `strict_success`)
- **Sai số tuyệt đối trung bình về số khẳng định không được hỗ trợ (`unsupported_claims_mean_abs_difference`):** `0.200`.

---

## 2. Phân Tích Chi Tiết Các Trường Hợp Khác Biệt & Sắc Thái Kỹ Thuật (Nuances & Disagreements)

Qua đối chiếu từng câu trả lời và trích dẫn của mô hình ứng viên với toàn văn các quy định học vụ của Trường ĐH Bách Khoa — ĐHQG-HCM, người kiểm toán ghi nhận **29/30 mẫu đồng thuận tuyệt đối về kết quả `strict_success`** (100% đồng thuận về `judgeable`, `behaviour_appropriate` và `completeness`). Có **01 mẫu bất đồng thực chất về `correctness` / `strict_success`** và **03 mẫu khác biệt kỹ thuật ở trường `unsupported_claims`** do quy tắc lọc `not_established` của `judge_rules.py`:

### 2.1. Bất đồng thực chất về `correctness` và `strict_success` (01 mẫu: `cd45bb179ebfed740173b335`)
- **Mẫu #29 (`cd45bb179ebfed740173b335`):**
  - **Câu hỏi:** *"Theo Quyết định 1259/QĐ-ĐHBK sửa đổi điểm a khoản 14.2 Điều 14, với học phần thuộc khối kiến thức tốt nghiệp đại học tính theo loại đạt có phân mức, điểm đạt bắt đầu từ điểm chữ nào?"*
  - **Đáp án chuẩn (`reference_answer`):** *"Từ điểm C."*
  - **Câu trả lời của ứng viên (`candidate_answer`):** *"Theo Quyết định 1259/QĐ-ĐHBK (điều 4, mục a), đối với các học phần thuộc khối kiến thức tốt nghiệp đại học tính theo loại đạt có phân mức, điểm đạt bắt đầu từ **điểm C**."* kèm trích dẫn đúng mã nguồn `HCMUT_HVCHUNG1259_Dieu_1_S9_1` và đúng nguyên văn `"Các học phần sau đại học và các học phần thuộc khối kiến thức tốt nghiệp đại học, điểm đạt là từ điểm C."`.
  - **Phán quyết của DeepSeek V4 Flash:** Chấm `correctness = 1`, `total_claims = 2`, `unsupported_claims = 1` (`strict_success = False`) vì tách cụm từ trong ngoặc `(điều 4, mục a)` thành một claim riêng có nhãn `not_established` (vì trong đoạn văn bản nguồn ghi là `4. Sửa đổi, bổ sung điểm a, b khoản 14.2 Điều 14 như sau: “a) Loại đạt có phân mức...`).
  - **Phán quyết của Người kiểm toán:** Chấm `correctness = 2`, `total_claims = 1`, `unsupported_claims = 0` (`strict_success = True`).
  - **Căn cứ kiểm toán:** Trong bản ghi `HCMUT_HVCHUNG1259_Dieu_1_S9_1`, đoạn sửa đổi khoản 14.2 Điều 14 nằm ở khoản số `4.` (thuộc Điều 1 của QĐ 1259/QĐ-ĐHBK) và điểm `a)`. Việc ứng viên viết tắt vị trí đầu mục `4.` và `a)` thành `(điều 4, mục a)` không làm thay đổi nội dung quy định hay điều kiện áp dụng, và bản thân câu hỏi đã nêu sẵn vị trí `"điểm a khoản 14.2 Điều 14"`. Đáng chú ý, ở **Mẫu #02 (`030e2b2c1d6182bb551df770`)** (cùng câu hỏi, ứng viên ghi `(Điều 14, khoản a, mục 4...)`) và **Mẫu #21 (`7c3cd7112d5ac8a8e3a76896`)** (ứng viên ghi `"Điều 3.2 Khoản 3"` thay vì `"khoản 3.2 Điều 3"`), chính DeepSeek V4 Flash đã bỏ qua sai số thứ tự tên gọi điều/khoản và chấm `correctness = 2, strict_success = True`. Do đó, việc phạt Mẫu #29 xuống `correctness = 1` là quá khắt khe và thiếu nhất quán.

### 2.2. Khác biệt kỹ thuật ở `all_claims_supported` trên các câu `expected_behavior = "refuse"` (03 mẫu: `13a8548817d5e6a982c0271a`, `537e7d2bac4fb3383307d6ae`, `b9bd152220ee0fdde7e16496`)
- Trong cả 3 mẫu này, bản thân mô hình giám khảo DeepSeek V4 Flash trong `judge/judgments.jsonl` **đã phát hiện chính xác các khẳng định không có căn cứ** và gán nhãn `support = "not_established"`, đồng thời đánh trượt (`strict_success = False`) cả 3 mẫu:
  1. **Mẫu #08 (`13a8548817d5e6a982c0271a`):** Ứng viên từ chối đúng phạm vi về mức phạt tiền không đội mũ bảo hiểm, nhưng tự bịa thêm câu *"Mức phạt này thuộc phạm vi của Bộ luật Hình sự và Nghị định số 49/2016/NĐ-CP"*. DeepSeek V4 Flash trích xuất đúng câu này với nhãn `not_established` và hạ `correctness = 1` (`strict_success = False`).
  2. **Mẫu #16 (`537e7d2bac4fb3383307d6ae`):** Câu hỏi hỏi về thời hạn phúc khảo điểm (`expected_behavior = "refuse"`), nhưng ứng viên không từ chối (`candidate_behavior = "answered"`) mà lấy thời hạn nộp hồ sơ hỗ trợ/vinh danh cuộc thi tại Điều 6 QĐ 658/QĐ-ĐHBK gán ghép thành thời hạn phúc khảo điểm. DeepSeek V4 Flash trích xuất 3 claims với nhãn `not_established` và chấm `behaviour_appropriate = False, correctness = 0, completeness = 0` (`strict_success = False`).
  3. **Mẫu #26 (`b9bd152220ee0fdde7e16496`):** Câu hỏi hỏi về ngưỡng điểm xét học bổng khuyến khích học tập (`expected_behavior = "refuse"`), nhưng ứng viên không từ chối (`candidate_behavior = "answered"`) mà tự chế ra điều khoản không tồn tại `HCMUT_QCDT_Dieu_12` cùng ngưỡng điểm trung bình `7.0` và điểm rèn luyện `8.0`. DeepSeek V4 Flash trích xuất claim này với nhãn `not_established` và chấm `behaviour_appropriate = False, correctness = 0, completeness = 0` (`strict_success = False`).
- **Nguyên nhân chênh lệch ở cột `unsupported_claims`:** Hàm `judge_rules.is_abstention(expected_behavior, candidate_behavior)` trả về `True` khi `expected_behavior == "refuse"` (kể cả khi ứng viên trả lời thay vì từ chối), và hàm `judge_rules.counted_claims` tự động loại bỏ các claim mang nhãn `not_established` khi `abstention == True` (nhằm tránh phạt nhầm các câu thông báo "không có thông tin trong văn bản"). Vì vậy, bộ quy đổi `judge_verdicts` quy về `unsupported_claims = 0` cho phía Judge ở 3 mẫu này, trong khi Người kiểm toán ghi nhận trực tiếp số khẳng định sai/bịa đặt (`unsupported_claims = 1, 3, 1`). Sự khác biệt này **không làm thay đổi kết quả `strict_success`, `behaviour_appropriate`, `correctness` hay `completeness`** ở bất kỳ mẫu nào trong 3 mẫu trên.

---

## 3. Kiểm Toán Chi Tiết Từng Mẫu (30/30 Items)

| STT | `review_id` | Kỳ vọng / Ứng viên | Phán quyết của DeepSeek Flash (`B / Cr / Cp / TC / UC / Pass`) | Phán quyết Kiểm toán (`B / Cr / Cp / TC / UC / Pass`) | Khớp `Pass`? | Đối chiếu văn bản quy chế ĐH Bách Khoa |
|---:|---|---|---|---|---|---|
| 01 | `00b949c39d5a7d85033ed3de` | `answer` / `answered` | `1 / 2 / 1 / 1 / 0 / False` | `1 / 2 / 1 / 1 / 0 / False` | ✅ | Nêu đúng nhiệm vụ CVHT tư vấn tín chỉ tự chọn tự do (Điều 15 khoản 4 QĐ 2977/QĐ-ĐHBK), nhưng trong văn bản trả lời bỏ sót hoàn toàn vế 2 về tối thiểu 9 tín chỉ tự chọn tự do cho khóa 2025 về trước (khoản 5 Điều 12 sửa đổi bởi QĐ 1862/QĐ-ĐHBK). |
| 02 | `030e2b2c1d6182bb551df770` | `answer` / `answered` | `1 / 2 / 2 / 1 / 0 / True` | `1 / 2 / 2 / 1 / 0 / True` | ✅ | Khớp chính xác điểm a khoản 14.2 Điều 14 sửa đổi bởi QĐ 1259/QĐ-ĐHBK (`HCMUT_HVCHUNG1259_Dieu_1_S9_1`): học phần thuộc khối kiến thức tốt nghiệp đại học có điểm đạt từ điểm C. |
| 03 | `035e154f5ddc130a5bc154f1` | `answer` / `refused` | `0 / 0 / 0 / 0 / 0 / False` | `0 / 0 / 0 / 0 / 0 / False` | ✅ | Từ chối sai: câu hỏi có đủ căn cứ tại khoản 3 Điều 6 Nội quy học đường (QĐ 1924/QĐ-ĐHBK) và khoản 2 Điều 15 Quy tắc ứng xử (QĐ 3408/QĐ-ĐHBK). Ứng viên chỉ đọc Điều 2 Nội quy học đường rồi kết luận không có căn cứ. |
| 04 | `04ece1b3deaeb1d8c0e11a45` | `refuse` / `answered` | `1 / 2 / 2 / 0 / 0 / True` | `1 / 2 / 2 / 0 / 0 / True` | ✅ | Tuy trường `candidate_behavior` ghi `answered`, nội dung thực tế là lời từ chối chuẩn xác: nêu rõ văn bản không ghi đơn giá học phí năm 2026–2027 và hướng dẫn liên hệ bộ phận đào tạo. |
| 05 | `0a78f54b028710fc92cdbeb9` | `answer` / `refused` | `0 / 0 / 0 / 1 / 1 / False` | `0 / 0 / 0 / 1 / 1 / False` | ✅ | Từ chối do lỗi vòng lặp sửa chữa trích dẫn (`verify_final`), phát biểu sai rằng trích dẫn không khớp nguồn dù `HCMUT_HVDT1260_Dieu_1_S5_3` ghi rõ tối đa 28 tín chỉ (gồm tối đa 10 tín chỉ dự thính). |
| 06 | `0c3916e26a82fa0079692950` | `answer` / `answered` | `1 / 1 / 2 / 7 / 3 / False` | `1 / 1 / 2 / 7 / 3 / False` | ✅ | Trả lời đúng yêu cầu của năm thứ ba (Tiếng Nhật 1, 2, 3, 4 hoàn thành hết năm hai) theo mục 1.c Phụ lục 1 QĐ 2749/QĐ-ĐHBK, nhưng đọc lệch dòng bảng cho năm thứ nhất và năm thứ hai, đồng thời tự thêm chi tiết "cuối học kỳ 2". |
| 07 | `0c4d30f1aa8ff7bf75d813a3` | `answer` / `answered` | `1 / 2 / 2 / 1 / 0 / True` | `1 / 2 / 2 / 1 / 0 / True` | ✅ | Khớp chính xác khoản 14.3 Điều 14 sửa đổi bởi QĐ 1260/QĐ-ĐHBK (`HCMUT_HVDT1260_Dieu_1_S14_3`): được xem xét thu nhận lại để chuyển sang hình thức vừa làm vừa học hoặc đào tạo từ xa. |
| 08 | `13a8548817d5e6a982c0271a` | `refuse` / `refused` | `1 / 1 / 2 / 0* / 0* / False` | `1 / 1 / 2 / 1 / 1 / False` | ✅ | Từ chối đúng phạm vi vì Nội quy học đường không quy định mức phạt tiền giao thông, nhưng tự bịa thêm rằng mức phạt không đội mũ bảo hiểm thuộc Bộ luật Hình sự và Nghị định 49/2016/NĐ-CP (`correctness = 1`, `strict_success = False`). |
| 09 | `2a40a33107a518969d8529fa` | `answer` / `answered` | `1 / 2 / 2 / 1 / 0 / True` | `1 / 2 / 2 / 1 / 0 / True` | ✅ | Khớp chính xác Bước 1 Điều 7 QĐ 2800/QĐ-ĐHBK (`HCMUT_HOCPHI2800_Dieu_7`): nộp đơn đăng ký gia hạn trước thời điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc. |
| 10 | `3371363859f58872f2f4e62d` | `refuse` / `refused` | `1 / 2 / 2 / 0 / 0 / True` | `1 / 2 / 2 / 0 / 0 / True` | ✅ | Từ chối đúng phạm vi: xác nhận corpus không có quy định cụ thể về điểm trung bình học kỳ và điểm rèn luyện tối thiểu để xét học bổng khuyến khích học tập. |
| 11 | `3489e26617d62b8a5a21940c` | `answer` / `answered` | `0 / 0 / 0 / 0 / 0 / False` | `0 / 0 / 0 / 0 / 0 / False` | ✅ | Câu trả lời bị cắt cụt ngay sau cụm từ `"là:"`, không cung cấp được số tín chỉ (6 tín chỉ) và học kỳ (Học kỳ 8) dù mảng `candidate_citations` có trích dẫn điểm e Điều 11 QĐ 1862/QĐ-ĐHBK. |
| 12 | `39df763fb49010ae86ed0a68` | `answer` / `answered` | `1 / 2 / 2 / 1 / 0 / True` | `1 / 2 / 2 / 1 / 0 / True` | ✅ | Khớp chính xác Bước 1 Điều 7 QĐ 2800/QĐ-ĐHBK (`HCMUT_HOCPHI2800_Dieu_7`): trước thời điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc. |
| 13 | `3f881b4693ebbd535f258ccd` | `answer` / `refused` | `0 / 0 / 0 / 0 / 0 / False` | `0 / 0 / 0 / 0 / 0 / False` | ✅ | Từ chối sai: bảng tại khoản 3.1 Điều 3 sửa đổi bởi QĐ 1260/QĐ-ĐHBK (`HCMUT_HVDT1260_Dieu_1_S3_1`) quy định rõ chương trình PFIEV có thời gian đào tạo tối đa là 14 học kỳ chính. |
| 14 | `47f53b93990ce0260db73950` | `answer` / `answered` | `1 / 2 / 2 / 2 / 0 / True` | `1 / 2 / 2 / 2 / 0 / True` | ✅ | Khớp chính xác khoản 5.3 Điều 5 sửa đổi bởi QĐ 1260/QĐ-ĐHBK (`HCMUT_HVDT1260_Dieu_1_S5_3`): tối đa 10 tín chỉ dự thính và tổng số tín chỉ tối đa trong học kỳ chính là 28 tín chỉ. |
| 15 | `506c6b8e9e4a4c2dc2c90493` | `refuse` / `answered` | `0 / 0 / 0 / 1 / 0 / False` | `0 / 0 / 0 / 1 / 0 / False` | ✅ | Đáng lẽ phải từ chối vì corpus không có quy định phúc khảo điểm; ứng viên lại lấy nguyên văn quy định gia hạn nộp học phí (trước ít nhất 05 ngày làm việc tại Điều 7 QĐ 2800/QĐ-ĐHBK) để trả lời. |
| 16 | `537e7d2bac4fb3383307d6ae` | `refuse` / `answered` | `0 / 0 / 0 / 0* / 0* / False` | `0 / 0 / 0 / 3 / 3 / False` | ✅ | Đáng lẽ phải từ chối vì corpus không có quy định phúc khảo điểm; ứng viên lại gán ghép sai thời hạn nộp hồ sơ hỗ trợ/vinh danh cuộc thi tại Điều 6 QĐ 658/QĐ-ĐHBK thành thời hạn phúc khảo điểm. |
| 17 | `5559a668a12c8702d6108ad4` | `answer` / `answered` | `1 / 2 / 2 / 2 / 0 / True` | `1 / 2 / 2 / 2 / 0 / True` | ✅ | Khớp chính xác cả hai vế: thời gian đào tạo tối đa của hình thức vừa làm vừa học là 16 học kỳ chính (`HCMUT_HVDT1260_Dieu_1_S3_1`) và kết quả học tập tích lũy được giữ nguyên (`HCMUT_HVCHUNG1259_Dieu_1_S25_5`). |
| 18 | `5cb52ef7b10a81a84c92886b` | `answer` / `answered` | `1 / 0 / 0 / 3 / 0 / False` | `1 / 0 / 0 / 3 / 0 / False` | ✅ | Trả lời lạc đề: câu hỏi hỏi hiện kim khen thưởng cho nhóm SV từ 2 người trở lên so với cá nhân (bằng 02 lần theo điểm d khoản 3 Điều 11 QĐ 658/QĐ-ĐHBK), nhưng ứng viên chỉ trích dẫn ngưỡng $K_{pl}$ của GV hướng dẫn tại Điều 5. |
| 19 | `6a5ad9bdbd3c95fac56e8013` | `refuse` / `refused` | `1 / 2 / 2 / 0 / 0 / True` | `1 / 2 / 2 / 0 / 0 / True` | ✅ | Từ chối đúng phạm vi: khẳng định rõ các văn bản trong cơ sở dữ liệu không chứa đơn giá học phí cụ thể cho năm học 2026–2027. |
| 20 | `79bcd892447af9ea4f6d3986` | `refuse` / `refused` | `1 / 2 / 2 / 0 / 0 / True` | `1 / 2 / 2 / 0 / 0 / True` | ✅ | Từ chối đúng phạm vi: xác nhận văn bản đã tra cứu không quy định về thời hạn nộp đơn phúc khảo điểm học phần. |
| 21 | `7c3cd7112d5ac8a8e3a76896` | `answer` / `answered` | `1 / 2 / 2 / 1 / 0 / True` | `1 / 2 / 2 / 1 / 0 / True` | ✅ | Khớp chính xác khoản 3.2 Điều 3 sửa đổi bởi QĐ 2282/QĐ-ĐHBK (`HCMUT_GIANGDAY2282_Dieu_1`): số phiên học bố trí dạy thay của một lớp không vượt quá 20% tổng số phiên học. |
| 22 | `821fc32ae3103772074e3464` | `answer` / `answered` | `0 / 0 / 0 / 1 / 0 / False` | `0 / 0 / 0 / 1 / 0 / False` | ✅ | Không trả lời được câu hỏi: chỉ dẫn Điều 2 (Mục đích) của Nội quy học đường rồi từ chối trả lời căn cứ xử lý, bỏ sót khoản 3 Điều 6 QĐ 1924/QĐ-ĐHBK và khoản 2 Điều 15 QĐ 3408/QĐ-ĐHBK. |
| 23 | `9513768079674da1ab96b0a7` | `answer` / `answered` | `1 / 2 / 2 / 1 / 0 / True` | `1 / 2 / 2 / 1 / 0 / True` | ✅ | Khớp chính xác khoản 3 Điều 16 QĐ 3408/QĐ-ĐHBK (`HCMUT_UNGXU3408_Dieu_16`): hành vi vi phạm xảy ra trước thời điểm Quy định có hiệu lực được xem xét, xử lý theo quy định có hiệu lực tại thời điểm xảy ra hành vi. |
| 24 | `9e9b7d4d70aa9d74f7b56dcc` | `answer` / `answered` | `1 / 2 / 2 / 1 / 0 / True` | `1 / 2 / 2 / 1 / 0 / True` | ✅ | Khớp chính xác khoản 1 Điều 12 QĐ 3408/QĐ-ĐHBK (`HCMUT_UNGXU3408_Dieu_12`): người học sử dụng địa chỉ thư điện tử do Nhà trường cấp. |
| 25 | `a15984cee3259ae602688e5e` | `answer` / `answered` | `1 / 2 / 2 / 6 / 0 / True` | `1 / 2 / 2 / 6 / 0 / True` | ✅ | Khớp chính xác Bước 1 Điều 7 và khoản 1 Điều 8 QĐ 2800/QĐ-ĐHBK: nộp đơn về Phòng Công tác sinh viên; Trưởng phòng là Phó Chủ tịch Hội đồng và Phó Trưởng phòng là Thư ký. |
| 26 | `b9bd152220ee0fdde7e16496` | `refuse` / `answered` | `0 / 0 / 0 / 0* / 0* / False` | `0 / 0 / 0 / 1 / 1 / False` | ✅ | Vi phạm nghiêm trọng: câu hỏi ngoài phạm vi nhưng ứng viên tự bịa mã tài liệu `HCMUT_QCDT_Dieu_12` và bịa ngưỡng GPA 7.0, điểm rèn luyện 8.0 để xét học bổng khuyến khích học tập. |
| 27 | `bb9cbf039a9f4a3b0c4ee57f` | `answer` / `refused` | `0 / 0 / 0 / 0 / 0 / False` | `0 / 0 / 0 / 0 / 0 / False` | ✅ | Từ chối sai: ứng viên in ra lập luận nội bộ về việc cần gọi công cụ `search` thay vì trả lời căn cứ xử lý tại Điều 6 QĐ 1924/QĐ-ĐHBK và Điều 15 QĐ 3408/QĐ-ĐHBK. |
| 28 | `c1fa2922dfad8748f0bf0c7d` | `answer` / `answered` | `1 / 2 / 2 / 6 / 0 / True` | `1 / 2 / 2 / 6 / 0 / True` | ✅ | Khớp chính xác Bước 1 Điều 7 và khoản 1 Điều 8 QĐ 2800/QĐ-ĐHBK: nộp đơn về Phòng Công tác sinh viên; liệt kê đúng và đầy đủ 5 chức danh trong Hội đồng xét hồ sơ. |
| 29 | `cd45bb179ebfed740173b335` | `answer` / `answered` | `1 / 1 / 2 / 2 / 1 / False` | `1 / 2 / 2 / 1 / 0 / True` | ❌ (**Bất đồng duy nhất**) | Ứng viên trả lời đúng `"điểm C"` và trích dẫn đúng nguyên văn `HCMUT_HVCHUNG1259_Dieu_1_S9_1`. Ghi chú `(điều 4, mục a)` chỉ quy chiếu đến mục `4.` điểm `a)` trong văn bản sửa đổi; Judge hạ `correctness = 1` là quá khắt khe so với Mẫu #02 và Mẫu #21. |
| 30 | `dbec0ff316c1c8acc93417f7` | `answer` / `answered` | `1 / 2 / 2 / 3 / 0 / True` | `1 / 2 / 2 / 3 / 0 / True` | ✅ | Khớp chính xác cả 3 ý: GPA tối thiểu 2.0 thang 4 (`HCMUT_HVDT1260_Dieu_1_S5_5`), GPA 2,35 đạt ngưỡng, và xếp loại học lực Trung bình từ 2,00 đến cận 2,50 (`HCMUT_HVCHUNG1259_Dieu_1_S15_2`). |

*(Ghi chú: Ký hiệu `B / Cr / Cp / TC / UC / Pass` lần lượt là `behaviour_appropriate`, `correctness`, `completeness`, `total_claims`, `unsupported_claims`, `strict_success`. Dấu `*` ở các mẫu #08, #16, #26 biểu thị các claim `not_established` đã được DeepSeek V4 Flash phát hiện trong `judgments.jsonl` nhưng được `judge_rules.counted_claims` lược bỏ khi tính điểm phía Judge cho nhóm `expected_behavior = "refuse"`).*
