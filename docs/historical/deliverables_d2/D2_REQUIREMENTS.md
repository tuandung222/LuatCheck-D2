# D2 Interim Report - Note yêu cầu quan trọng

Môn CO5151 - Advanced Agentic Artificial Intelligence, HK261. Tổng hợp ngày 21/10/2026 từ ba nguồn bên dưới; dùng để chuẩn bị report, slide và buổi báo cáo D2.

## 1. Nguồn và cách đọc note

| Ký hiệu | Nguồn | Nội dung đã đối chiếu |
| --- | --- | --- |
| **[PDF]** | [interim-report-requirements.pdf](../../../docs/materials/d2/interim-report-requirements.pdf) | Toàn bộ 3 trang: cách nộp, tám phần bắt buộc, phần proposal cần bổ sung và checklist. |
| **[XLSX]** | [CO5151-D2-Rubric.xlsx](../../../docs/materials/d2/CO5151-D2-Rubric.xlsx) | Cả tám sheet G1-G8, gồm trọng số, công thức và **ghi chú tại ô tên tiêu chí**. Nội dung tiêu chí và ghi chú giống nhau giữa các sheet, chỉ khác tên nhóm. |
| **[Email]** | [Thông báo của giảng viên](../../../docs/materials/d2/CO5151-D2-announcement.md) | Toàn bộ nội dung được giữ nguyên từ văn bản người dùng gửi; mục 3: nộp D2, mục 4: rubric, mục 5: trình bày/demo, mục 6: lịch. Có cả [bản TXT](../../../docs/materials/d2/CO5151-D2-announcement.txt). |

Các mục yêu cầu dưới đây là nội dung tổng hợp từ giảng viên và rubric. Phần ghi **“Gợi ý”** là cách tổ chức công việc, không phải yêu cầu bổ sung của môn học. Checklist chưa đánh dấu không có nghĩa nhóm đang thiếu mục đó; note này chưa đánh giá report hoặc mã nguồn hiện tại.

**Nguyên tắc xuyên suốt report:** phân biệt rõ phần **đã cài đặt, đã chạy, đã đo** với phần **còn trong kế hoạch**; nhận định phải khớp bằng chứng. Mục không áp dụng theo thiết kế đã duyệt phải ghi rõ và giải thích lý do. Nguồn: [PDF] tr. 1, phần mở đầu; [Email] mục 3; [XLSX] ghi chú A1, A5.

## 2. Mốc thời gian, hồ sơ và cách nộp

| Hạng mục | Yêu cầu |
| --- | --- |
| **Hạn nộp** | **23:59 Chủ nhật 25/10/2026**, áp dụng cho cả report và slide. |
| Report | **Một file PDF, tối đa 10 trang nội dung**, tiếng Việt hoặc tiếng Anh. |
| Không tính vào 10 trang | Trang bìa/tiêu đề, mục lục, tài liệu tham khảo và phụ lục. |
| Vượt giới hạn | **Phần nội dung sau trang 10 không được đọc và không được chấm.** |
| Slide | Một file PDF cho buổi trình bày của nhóm. |
| Mã nguồn | Trong report phải có **repository URL và commit hash của phiên bản được báo cáo**; giảng viên phải có quyền đọc repository. |
| Người gửi | **Nhóm trưởng** gửi một email, đính kèm hai file PDF, **CC tất cả thành viên**. |
| Người nhận | `lexuanbach@hcmut.edu.vn` |
| Tiêu đề email | `[CO5151][Gx] D2 Interim report` - thay `Gx` bằng nhóm thực tế. |
| **Nộp trễ** | **Trừ 10% mỗi ngày, tối đa 3 ngày; sau đó bài nộp nhận 0 điểm.** |
| Tỷ trọng | D2 = **30% điểm đồ án**, tương đương **15% điểm tổng kết môn**. |

Nguồn: [PDF] tr. 1, mục 1; [Email] mục 3. Quy định nộp trễ nằm trong PDF.

## 3. Tám phần bắt buộc của report - giữ đúng thứ tự

### 1) Thay đổi so với proposal

- Nêu phạm vi, kiến trúc hoặc kế hoạch đánh giá đã thay đổi so với D1 và **lý do**.
- Nêu cách xử lý các góp ý nhận được ở buổi pitch.
- Có **bảng đối chiếu các cam kết hoàn thành trước mốc giữa kỳ trong proposal với trạng thái hiện tại**.
- Dùng các trạng thái: **xong / đang làm / chưa bắt đầu / đã bỏ**.

Nguồn: [PDF] tr. 1, mục 2, phần 1; [Email] mục 3, phần 1; [XLSX] ghi chú `B15` (A4).

### 2) Kiến trúc đã cài đặt (R1)

- Sơ đồ kiến trúc cập nhật và mô tả **vòng điều khiển**.
- Nêu **nhóm chọn kiến trúc/pattern nào và vì sao**, thể hiện quyết định đó bằng hệ thống của chính nhóm, theo nhấn mạnh trong email sau danh sách tám phần.
- Đánh dấu rõ phần **đang chạy end-to-end** và phần **còn là kế hoạch**; sơ đồ phải khớp mã nguồn.
- Kèm **một trace thật khi hệ thống hoàn thành một task**.
- Nếu nhiều agent: nêu agent nào đã hoạt động, cách trao đổi và phối hợp. Nếu hiện mới chạy một agent thì ghi đúng như vậy.

Nguồn: [PDF] tr. 2, mục 2, phần 2; [Email] mục 3, phần 2 và đoạn liên hệ Seminar 1 với D2; [XLSX] ghi chú `B12` (A1).

### 3) Công cụ và phân quyền (R2)

- Có bảng liệt kê **từng công cụ**: MCP server hoặc function calling tương đương.
- Với mỗi công cụ, ghi trạng thái **đã cài đặt / còn kế hoạch** và mức quyền:
  - Chỉ đọc.
  - Ghi có thể hoàn tác.
  - Ghi không thể hoàn tác.
  - Thực thi mã.
- Với **mọi công cụ không phải chỉ đọc**, mô tả cơ chế chặn, chẳng hạn xác nhận của người dùng, kiểm tra quyền hoặc sandbox.
- Nếu hệ thống chỉ có công cụ chỉ đọc: giải thích điều gì **bảo đảm giới hạn ở mức mã nguồn**, không chỉ dựa vào prompt.

Nguồn: [PDF] tr. 2, mục 2, phần 3; [Email] mục 3, phần 3; [XLSX] ghi chú `B12` (A1).

### 4) Bộ nhớ và nguồn tri thức (R3)

- Cách quản lý **ngữ cảnh ngắn hạn**.
- Bộ nhớ dài hạn hoặc episodic: **chính sách ghi và chính sách truy xuất**.
- Nếu có retrieval: dữ liệu đã nạp, **quy mô**, cách chia và lập chỉ mục. Bao gồm nguồn văn bản, bảng biểu, đồ thị tri thức hoặc lược đồ cơ sở dữ liệu nếu có.
- Ghi rõ phần nào đã chạy.
- Nếu proposal đã được duyệt với thiết kế không có bộ nhớ dài hạn hoặc không có retrieval: ghi **“không áp dụng” và lý do theo thiết kế đã duyệt**.

Nguồn: [PDF] tr. 2, mục 2, phần 4; [Email] mục 3, phần 4; [XLSX] ghi chú `B12` (A1).

### 5) Bộ đánh giá và số liệu đầu tiên (R5)

| Nội dung | Phải thể hiện |
| --- | --- |
| Nguồn task | Benchmark công khai, tự xây dựng hoặc kết hợp; **số task hiện có và mục tiêu cuối kỳ**. Nếu tự xây dựng: ai viết task, đáp án chuẩn được xác định thế nào. |
| Cách chấm | Định nghĩa đúng/sai: kiểm tra tự động, nhãn người hay LLM-as-judge. |
| LLM-as-judge, nếu dùng | Nêu cách kiểm tra độ tin cậy trên **một mẫu có nhãn người**. |
| Kết quả | Kết quả trên **“ít nhất 5-10 task” đã thực sự chạy** theo cách diễn đạt của tài liệu, với các độ đo chính của đề tài. |
| So sánh | **Ít nhất một cấu hình đơn giản hơn**, ví dụ gọi mô hình trực tiếp, RAG cố định hoặc bỏ một thành phần. |
| Thiết kế đánh giá | Rà soát **quy mô tập task, độ đo, baseline và số lần chạy**; nếu proposal mới nêu chung chung thì D2 phải bổ sung (xem [PDF] tr. 3, mục 3). |
| Chi phí và độ trễ | Báo cáo chi phí mỗi task và độ trễ. Dùng API: **token và tiền**. Chạy mô hình cục bộ: **giờ GPU và cấu hình máy**. |
| Phân tích lỗi | Một số task thất bại và nguyên nhân dự đoán. |
| Tái lập | Số liệu phải tái lập được từ repository. **Ghi chú rubric A2 nhấn mạnh tái lập bằng một lệnh.** |

Ngoài mô tả quy trình chấm, cần giải thích **cách đánh giá được chọn giúp biết hệ thống chạy tốt đến đâu**, bằng số liệu của chính nhóm. Đây là nhấn mạnh trong [Email] mục 3, đoạn liên hệ hai chủ đề Seminar 1 với D2.

**Số liệu sơ bộ là điều được mong đợi. Số liệu không có cách chấm rõ ràng hoặc không tái lập được từ repository thì không được tính.**

Nguồn: [PDF] tr. 2, mục 2, phần 5 và tr. 3, mục 3; [Email] mục 3, phần 5 và đoạn liên hệ Seminar 1 với D2; [XLSX] ghi chú `B13` (A2).

### 6) Threat model (R6)

- **Mọi đề tài đều bắt buộc có**, kể cả proposal chưa có threat model.
- Đã có trong proposal: cập nhật theo hệ thống hiện tại và nêu thay đổi.
- Chưa có trong proposal: bổ sung bản đầu tiên ở D2. Việc thiếu trong proposal không bị trừ điểm ở D2; chấm theo nội dung trình bày tại D2.
- Threat model phải cụ thể cho hệ thống của nhóm, gồm:
  - **Tài sản cần bảo vệ**.
  - **Điểm nội dung không tin cậy đi vào ngữ cảnh mô hình**: chẳng hạn PDF tải lên, tài liệu retrieval, trường văn bản trong database, tool output, trang web hoặc câu hỏi người dùng, tùy hệ thống thực tế.
  - **Năng lực giả định của kẻ tấn công**.
  - **Biện pháp giảm thiểu dự kiến cho từng điểm vào**.
- Tài liệu cho biết **một bảng khoảng nửa trang là đủ** nếu trả lời được các nội dung trên.
- **D2 chưa yêu cầu chạy thử prompt injection. Phần thử tấn công thuộc báo cáo cuối kỳ.**

Nguồn: [PDF] tr. 2, mục 2, phần 6; [Email] mục 3, phần 6; [XLSX] ghi chú `B14` (A3), ô `G40`.

### 7) Kế hoạch tới buổi báo cáo cuối kỳ

- Kế hoạch **theo tuần từ tuần 45 tới vòng báo cáo thứ nhất, ngày 02/12/2026**; tài liệu gọi mốc này là tuần 49.
- Ai phụ trách việc gì.
- **Giả định rủi ro nhất còn lại**.
- Nếu giả định đó sai: **phạm vi thu hẹp và phần lõi sẽ giữ lại**.
- Kết thúc bằng tự đánh giá: **đúng tiến độ / có rủi ro / cần thu hẹp phạm vi**.

Nguồn: [PDF] tr. 3, mục 2, phần 7; [Email] mục 3, phần 7; [XLSX] ghi chú `B15` (A4).

### 8) Đóng góp thành viên và AI-use statement

- Bảng ngắn nêu mỗi thành viên đã làm phần nào, **khớp lịch sử commit**.
- AI-use statement: **công cụ AI nào, dùng vào việc gì và nhóm đã tự kiểm chứng những gì**.

Nguồn: [PDF] tr. 3, mục 2, phần 8; [Email] mục 3, phần 8; [XLSX] ghi chú `B16` (A5).

## 4. Những mục phải bổ sung nếu proposal còn thiếu

**D2 là hạn cuối để bổ sung các thông tin dưới đây.** Nếu proposal đã đầy đủ thì nhắc lại ngắn gọn. Nguồn: [PDF] tr. 3, mục 3.

| Nội dung cần rà soát | Yêu cầu |
| --- | --- |
| **Track** | Ghi rõ **Research Track** hoặc **Application Track**. |
| Research Track | Nêu **giả thuyết có thể bác bỏ (RT1)** và **baseline bên ngoài (RT2)**. |
| Application Track | Nêu **nhóm người dùng và ít nhất ba kịch bản sử dụng (AT1)**, trong đó có một kịch bản người dùng bất cẩn hoặc có ý đồ xấu. |
| Mô hình và framework | Mô hình dùng khi phát triển và mô hình dùng để tạo số liệu trong report; API hay cục bộ; framework nào; nhóm tự viết phần nào. |
| Tools và quyền | Bảng công cụ và mức quyền cụ thể. |
| Bộ nhớ | Thiết kế, chính sách ghi và truy xuất. |
| Đánh giá | Quy mô tập task, độ đo, baseline và **số lần chạy**. |
| Threat model | Đủ tài sản, điểm vào và năng lực kẻ tấn công; xem phần 6 của report. |
| Kế hoạch | Theo tuần và có phạm vi thu hẹp. |
| Dữ liệu | Nếu dùng dữ liệu giả lập/tổng hợp: ghi rõ và nêu khác dữ liệu thật ở đâu. |
| Người dùng thật | Nếu proposal đã hứa một buổi dùng thử: báo cáo đã thực hiện hay chưa và học được gì. |

## 5. Rubric D2 và bằng chứng để đạt điểm cao

Điểm D2 trên **thang 10**, gồm **report 50% + trình bày/live demo/hỏi đáp 50%**. Các trọng số sau tính trên **toàn bộ D2**.

| Mã | Tiêu chí | Trọng số | Tối đa trên điểm D2 /10 | Trọng tâm trong ghi chú rubric |
| --- | --- | --- | --- | --- |
| A1 | Kiến trúc, công cụ, bộ nhớ và nguồn tri thức | 15% | 1,5 | Sơ đồ khớp code; trace thật; tools/quyền/cơ chế chặn; chính sách bộ nhớ và retrieval; giải thích mục không áp dụng. |
| A2 | Bộ đánh giá và số liệu đầu tiên | 15% | 1,5 | Task đã chạy; cách chấm rõ; baseline đơn giản; chi phí, độ trễ, lỗi; tái lập bằng một lệnh. |
| A3 | Threat model | 10% | 1,0 | Cụ thể cho hệ thống; đủ tài sản, điểm vào, năng lực attacker; mỗi điểm vào có biện pháp dự kiến. |
| A4 | Thay đổi, kế hoạch và rủi ro | 5% | 0,5 | Đối chiếu proposal, lý do thay đổi, xử lý góp ý pitch, bổ sung mục thiếu, kế hoạch khả thi và phạm vi thu hẹp. |
| A5 | Chất lượng báo cáo | 5% | 0,5 | Đúng giới hạn trang, đủ tám phần; nhận định khớp bằng chứng; repo/commit; đóng góp và AI-use statement. |
| B1 | Live demo | 20% | 2,0 | Ít nhất một task end-to-end ngay tại lớp trên dữ liệu đề tài; khớp report; video dự phòng và giải thích trace. |
| B2 | Trình bày | 15% | 1,5 | Ghi chú rubric ghi “đúng 10 phút”; đủ thay đổi, kiến trúc đang chạy, số liệu/chi phí, threat model, kế hoạch/rủi ro; không nói quá. |
| B3 | Hỏi đáp | 15% | 1,5 | Trả lời chính xác, có bằng chứng; từng thành viên hiểu phần mình; thừa nhận hạn chế thật. |

Nguồn: [XLSX] các sheet G1-G8, hàng `12:16` và `18:20`, trọng số cột `C`, ghi chú cột `B`; [Email] mục 4.

### Khung điểm cho mỗi tiêu chí

| Khung | Điểm /10 | Ý nghĩa theo rubric |
| --- | --- | --- |
| Rất tốt | 9-10 | Đã cài đặt, đã demo, đã đo; bằng chứng có trong report và thấy được trong demo. |
| Tốt | 7-8 | Đã cài đặt và chạy được; thiếu sót nhỏ về bằng chứng hoặc giải thích. |
| Khá | 5-6 | Cài đặt một phần; một số yêu cầu chưa chạy hoặc chưa đo. |
| Trung bình | 3-4 | Chủ yếu là kế hoạch; ít thứ chạy được hoặc số liệu thiếu cách chấm rõ ràng. |
| Không tốt | 0-2 | Thiếu hoặc mâu thuẫn với demo/repository. |

Nguồn: [XLSX] `B34:G38`. Mốc đánh giá là **mức độ hoàn thành so với proposal của chính nhóm và chất lượng bằng chứng** (`B32`; [Email] mục 4).

**Cách tính:** `D2 = 0.15*A1 + 0.15*A2 + 0.10*A3 + 0.05*A4 + 0.05*A5 + 0.20*B1 + 0.15*B2 + 0.15*B3`, với từng tiêu chí trên thang 10.

Excel có sheet G1-G8; ô `D12:D16` và `D18:D20` chọn điểm/khung 0-10 qua dropdown, ghi chú rubric nằm ở ô tên tiêu chí tương ứng. Công thức ô `F5` chỉ hiện tổng khi đã đủ tám điểm; `F6` và `F7` là tổng từng phần. Đây là thông tin đọc từ file, không phải yêu cầu phải nộp thêm phiếu rubric cùng D2.

## 6. Trình bày, live demo và hỏi đáp

- **Thứ Tư 28/10/2026, 18:00-20:29, phòng B4-305**; thứ tự **G1 đến G8**.
- Mỗi nhóm **tổng cộng 15 phút**: khoảng **10 phút trình bày có live demo + 5 phút hỏi đáp**. Nên tập để phần trình bày đạt mốc 10 phút mà ghi chú rubric B2 nhấn mạnh.
- Trình bày: thay đổi so với proposal, kiến trúc đang chạy, demo, số liệu đầu tiên và chi phí, threat model, kế hoạch và rủi ro còn lại.
- Live demo phải cho thấy **ít nhất một task chạy từ đầu đến cuối trên dữ liệu đề tài**; kết quả khớp report.
- **Quay sẵn video dự phòng** cho sự cố mạng, API hoặc máy; khi dùng video phải giải thích được trace.
- **Chỉ chiếu video khi không có sự cố thì B1 không đạt khung Rất tốt.**
- **Mọi thành viên phải có mặt và trả lời được về phần mình làm.**
- Có mặt từ đầu buổi, kiểm tra trình chiếu, mở sẵn tài liệu/demo khi gần đến lượt.

Nguồn: [Email] mục 5; [PDF] tr. 1; [XLSX] ghi chú `B18:B20` (B1-B3).

## 7. Checklist trước khi nộp

Checklist tổng hợp từ [PDF] mục 4 và các yêu cầu chi tiết phía trên:

- [ ] Report PDF tối đa 10 trang nội dung; đủ tám phần, đúng thứ tự.
- [ ] Có bảng cam kết proposal và trạng thái hiện tại; giải thích thay đổi và xử lý góp ý pitch.
- [ ] Ghi rõ track; bổ sung các mục proposal còn thiếu, gồm mô hình/framework và thiết kế đánh giá.
- [ ] Research Track: giả thuyết có thể bác bỏ và baseline bên ngoài. Application Track: nhóm người dùng, ít nhất ba kịch bản, gồm một kịch bản bất cẩn hoặc có ý đồ xấu.
- [ ] Sơ đồ khớp code, tách phần đã chạy với phần dự kiến; có trace thật hoàn thành một task.
- [ ] Giải thích lựa chọn kiến trúc/pattern và cách đánh giá, có bằng chứng từ hệ thống và số liệu của nhóm.
- [ ] Bảng tools có trạng thái, mức quyền và cơ chế chặn; nếu chỉ đọc, giải thích bảo đảm trong code.
- [ ] Mô tả ngữ cảnh, bộ nhớ, retrieval; mục không áp dụng có lý do theo thiết kế đã duyệt.
- [ ] Đã chạy số task theo yêu cầu “ít nhất 5-10 task”; có cách chấm và ít nhất một cấu hình đơn giản hơn để so sánh.
- [ ] Nêu số task hiện có/mục tiêu, độ đo, baseline và số lần chạy; nếu tự xây tập task, nêu người viết và cách xác định đáp án chuẩn.
- [ ] Có chi phí, độ trễ, phân tích lỗi; nếu dùng LLM-as-judge, nêu kiểm tra trên mẫu nhãn người.
- [ ] Số liệu tái lập được từ repo; để bám tiêu chí điểm cao A2, chuẩn bị một lệnh tái lập.
- [ ] Threat model cụ thể, mỗi điểm vào có biện pháp giảm thiểu dự kiến.
- [ ] Kế hoạch theo tuần tới 02/12; người phụ trách, giả định rủi ro, phạm vi thu hẹp và tự đánh giá tiến độ.
- [ ] Bảng đóng góp khớp commit; AI-use statement nêu cả phần nhóm tự kiểm chứng.
- [ ] Nếu dùng dữ liệu giả lập/tổng hợp, nêu khác biệt với dữ liệu thật; nếu proposal hứa dùng thử với người dùng thật, báo cáo trạng thái và điều học được.
- [ ] Report có repo URL và commit hash; giảng viên có quyền đọc.
- [ ] Slide PDF hoàn tất; demo đã chạy thử; video dự phòng đã quay; thành viên đã chuẩn bị Q&A.
- [ ] Nhóm trưởng gửi đủ hai PDF, đúng người nhận/tiêu đề, CC tất cả thành viên, trước **23:59 ngày 25/10/2026**.

## 8. Gợi ý tổ chức bằng chứng khi viết

Đây là gợi ý thực hiện, không phải định dạng bắt buộc từ giảng viên:

- Bảng đối chiếu proposal: `Cam kết giữa kỳ | Trạng thái | Bằng chứng | Lý do thay đổi`.
- Bảng tools: `Tool/MCP | Trạng thái | Quyền | Cơ chế chặn hoặc bảo đảm chỉ đọc`.
- Bảng đánh giá: `Cấu hình | Số task đã chạy | Độ đo chính | Chi phí/task | Độ trễ | Lệnh tái lập`.
- Bảng threat model: `Tài sản | Điểm vào | Năng lực attacker | Biện pháp giảm thiểu dự kiến`.
- Bảng kế hoạch: `Tuần | Công việc | Người phụ trách | Kết quả dự kiến | Rủi ro/phạm vi thu hẹp`.
- Bảng đóng góp: `Thành viên | Phần đã làm | Commit/bằng chứng`.

## 9. Phạm vi của note và liên kết tham chiếu

- Cụm **“ít nhất 5-10 task”** được giữ theo nguồn; note không tự chuyển thành một ngưỡng duy nhất là 5 hoặc 10, cũng không coi 10 là giới hạn tối đa.
- Về thời lượng: PDF/email ghi **khoảng 10 phút trình bày có live demo** trong tổng 15 phút; ghi chú rubric B2 ghi **“Đúng 10 phút”**. Note giữ cả hai cách diễn đạt, không biến toàn bộ 15 phút thành thời gian thuyết trình.
- Quy định trễ hạn được giữ nguyên **“Trừ 10% mỗi ngày, tối đa 3 ngày; sau đó bài nộp nhận 0 điểm”**. Nguồn không giải thích chi tiết cách tính ngày lẻ hoặc cơ sở tính 10%; note không tự bổ sung công thức phạt.
- **Baseline bên ngoài (Research Track, RT2)** và **ít nhất một cấu hình đơn giản hơn (đánh giá D2)** là hai yêu cầu được nêu ở các đoạn khác nhau. Nguồn không nói chúng bắt buộc phải là hai cấu hình riêng biệt; cần mô tả cấu hình nào đáp ứng yêu cầu nào.
- Nội dung Seminar 1 (trả lời bổ sung, phiếu chấm G6/G2) và Seminar 2 trong email là việc riêng, không phải hồ sơ nộp D2.
- Quy tắc chia điểm giám khảo **30% G6 + 30% G2 + 40% thầy** trong mục 2 email áp dụng cho Seminar 1, không phải công thức D2.
- Ba nguồn được gửi thống nhất về yêu cầu chính. PDF bổ sung quy định nộp trễ và các mục proposal cần hoàn thiện; ghi chú Excel bổ sung mức kỳ vọng chi tiết, đặc biệt **tái lập bằng một lệnh** ở A2.
- [Hướng dẫn đồ án chung](https://lexuanbach.github.io/5151/project.html) được PDF và email dẫn chiếu; PDF nêu đây là nơi giải thích các mã yêu cầu R1-R9, RT1-RT4 và AT1-AT4. Note này chỉ tổng hợp ba nguồn được gửi, chưa mở rộng sang nội dung trên website đó.

Đối chiếu sâu ngày 21/10/2026: đọc toàn bộ PDF và xem ảnh cả ba trang, kiểm tra nội dung/ghi chú/công thức/dropdown trên tám sheet, đọc toàn bộ email. Đã đưa bản nguồn vào repo và kiểm tra bản sao khớp từng byte bằng SHA-256; xem [thư mục tài liệu](../../../docs/materials/d2/README.md), [biên bản đối chiếu](../../../docs/materials/d2/D2_REQUIREMENTS_REVIEW.md) và [kết quả kiểm tra](../../../docs/materials/d2/verification.json).
