# Biên bản đối chiếu note yêu cầu D2

Ngày đối chiếu: 21/10/2026, múi giờ Việt Nam. Đối tượng: [D2_REQUIREMENTS.md](../../../report_d2/D2_REQUIREMENTS.md) và ba nguồn trong [thư mục tài liệu](README.md).

**Kết quả đọc và đối chiếu:** không phát hiện yêu cầu D2 bị bỏ sót hoặc bị diễn giải trái nguồn trong phạm vi ba tài liệu được cung cấp sau các chỉnh sửa dưới đây. Bảng 80 nhóm nội dung bên dưới ghi nơi kiểm tra và nơi thể hiện trong note. Đây là đối chiếu yêu cầu; chưa đánh giá report, demo, số liệu hay mã nguồn của nhóm có đáp ứng chúng hay không.

## 1. Phương pháp và phạm vi kiểm tra

- PDF: xác nhận có 3 trang; trích xuất bằng cả `pypdf` và `pdfplumber`; xem ảnh render của cả 3 trang. `pypdf` có lỗi ánh xạ một số dấu tiếng Việt, nên dùng bản đọc `pdfplumber` và ảnh trang để đối chiếu chữ. PDF gốc được giữ nguyên.
- Excel: đọc các giá trị, công thức, dropdown và ghi chú ở cả G1-G8; đối chiếu thêm XML trong file XLSX. So sánh nội dung các sheet sau khi loại ô tiêu đề nhóm `B2`.
- Công thức: kiểm tra biểu thức được lưu, các hàng tính điểm, tổng trọng số và điểm tối đa; tính số học độc lập để đối chiếu công thức trong note. Không thực thi công thức bằng Excel và không thay đổi workbook.
- Thông báo: đọc toàn bộ văn bản được cung cấp; kiểm tra mục 3-6 về D2, phân biệt với công việc Seminar 1/2. Bản TXT và MD giống hệt byte nguồn; không suy ra metadata email không được cung cấp.
- Sao chép: so sánh byte và SHA-256 của Excel, PDF, TXT, MD với các file nguồn bên ngoài repo.
- Note: kiểm tra tám phần đúng thứ tự, các con số/ngày tháng, nguồn trích, điều kiện áp dụng và liên kết tới file trong repo. Kiểm tra tự động hỗ trợ xác minh cấu trúc và số liệu; bảng đối chiếu nội dung là kết quả đọc, không phải kết luận từ tìm từ khóa.
- Website được dẫn trong tài liệu chỉ được giữ làm liên kết tham chiếu; không lấy nội dung website làm nguồn yêu cầu thứ tư.

Kết quả kiểm tra bằng chương trình, hash và thời điểm thực hiện được lưu tại [verification.json](verification.json). Hash của note trong JSON gắn với phiên bản được kiểm tra; nếu sửa note sau đó thì cần kiểm tra lại.

## 2. Bảng đối chiếu 80 nhóm nội dung

Quy ước: **P** = PDF; **E** = email/thông báo; **X** = Excel, địa chỉ ô áp dụng cho cả tám sheet. **N2** = mục 2 của note; **N3.1** = phần 1 trong mục 3 của note, tương tự cho các phần khác.

### Hồ sơ, thời hạn và tỷ trọng

| ID | Nội dung đã đối chiếu | Nguồn | Vị trí trong note |
| --- | --- | --- | --- |
| D01 | 23:59 Chủ nhật 25/10/2026 cho cả report và slide | P tr. 1, mục 1; E mục 3 | N2 |
| D02 | Một report PDF, tối đa 10 trang nội dung, Việt hoặc Anh | P tr. 1, mục 1 | N2 |
| D03 | Bìa/tiêu đề, mục lục, tham khảo, phụ lục không tính vào giới hạn | P tr. 1; E mục 3 | N2 |
| D04 | Nội dung sau trang 10 không được đọc, không được chấm | P tr. 1, mục 1; E mục 3 | N2 |
| D05 | URL repo, commit hash đúng phiên bản báo cáo, giảng viên có quyền đọc | P tr. 1, mục 1 | N2 |
| D06 | Nhóm trưởng gửi một email, hai PDF, CC mọi thành viên; đúng email và tiêu đề | P tr. 1, mục 1; E mục 3 | N2 |
| D07 | Trừ 10% mỗi ngày, tối đa 3 ngày; sau đó 0 điểm | P tr. 1, mục 1 | N2, N9 |
| D08 | D2 bằng 30% điểm đồ án và 15% điểm môn | P tr. 1; X B24; E mục 3 | N2 |

### Tám phần nội dung report

| ID | Nội dung đã đối chiếu | Nguồn | Vị trí trong note |
| --- | --- | --- | --- |
| C01 | Tám phần bắt buộc theo đúng thứ tự | P mục 2; E mục 3 | N3 |
| C02 | Thay đổi phạm vi, kiến trúc, đánh giá kể từ D1 và lý do | P tr. 1, mục 2, phần 1 | N3.1 |
| C03 | Cách xử lý góp ý pitch | P tr. 1, mục 2, phần 1; X B15 | N3.1 |
| C04 | Bảng cam kết trước giữa kỳ; xong/đang làm/chưa bắt đầu/đã bỏ | P tr. 1, mục 2, phần 1 | N3.1 |
| C05 | Sơ đồ cập nhật và vòng điều khiển | P tr. 2, mục 2, phần 2 | N3.2 |
| C06 | Đang chạy end-to-end so với kế hoạch; sơ đồ khớp code | P tr. 2, phần 2; X B12 | N3.2, N1 |
| C07 | Một trace thật khi hoàn thành task | P tr. 2, phần 2; X B12 | N3.2 |
| C08 | Agent nào hoạt động, trao đổi ra sao; nói rõ nếu hiện chỉ một agent | P tr. 2, phần 2 | N3.2 |
| C09 | Chọn kiến trúc/pattern nào và vì sao, bằng hệ thống của nhóm | E mục 3, đoạn liên hệ Seminar 1 | N3.2 |
| C10 | Bảng từng công cụ MCP hoặc function calling tương đương | P tr. 2, phần 3 | N3.3 |
| C11 | Trạng thái từng công cụ: cài đặt hoặc kế hoạch | P tr. 2, phần 3 | N3.3 |
| C12 | Bốn mức quyền: đọc, ghi hoàn tác, ghi không hoàn tác, thực thi mã | P tr. 2, phần 3 | N3.3 |
| C13 | Cơ chế chặn cho mọi tool không chỉ đọc | P tr. 2, phần 3 | N3.3 |
| C14 | Nếu chỉ đọc: bảo đảm trong code, không chỉ prompt | P tr. 2, phần 3 | N3.3 |
| C15 | Quản lý ngữ cảnh ngắn hạn | P tr. 2, phần 4 | N3.4 |
| C16 | Bộ nhớ dài hạn/episodic: ghi và truy xuất | P tr. 2, phần 4 | N3.4 |
| C17 | Retrieval: dữ liệu, quy mô, cách chia/lập chỉ mục, trạng thái đã chạy | P tr. 2, phần 4 | N3.4 |
| C18 | Không áp dụng theo thiết kế đã duyệt: ghi rõ và giải thích | P mở đầu và tr. 2, phần 4 | N1, N3.4 |
| C19 | Nguồn task công khai/tự xây/kết hợp | P tr. 2, phần 5 | N3.5 |
| C20 | Số task hiện có và mục tiêu cuối kỳ | P tr. 2, phần 5 | N3.5 |
| C21 | Task tự xây: ai viết, cách xác định đáp án chuẩn | P tr. 2, phần 5 | N3.5 |
| C22 | Cách chấm đúng/sai rõ ràng | P tr. 2, phần 5; X B13 | N3.5 |
| C23 | Nếu dùng LLM judge: kiểm tra tin cậy trên mẫu có nhãn người | P tr. 2, phần 5 | N3.5 |
| C24 | “Ít nhất 5-10 task” thực chạy, có độ đo chính | P tr. 2, phần 5; E mục 3, phần 5; X B13 | N3.5, N9 |
| C25 | So với ít nhất một cấu hình đơn giản hơn | P tr. 2, phần 5; X B13 | N3.5 |
| C26 | Chi phí mỗi task và độ trễ | P tr. 2, phần 5 | N3.5 |
| C27 | API: token và tiền | P tr. 2, phần 5 | N3.5 |
| C28 | Mô hình cục bộ: giờ GPU và cấu hình máy | P tr. 2, phần 5 | N3.5 |
| C29 | Task thất bại và nguyên nhân dự đoán | P tr. 2, phần 5 | N3.5 |
| C30 | Số liệu sơ bộ được mong đợi; không rõ cách chấm hoặc không tái lập thì không tính | P tr. 2, phần 5 | N3.5 |
| C31 | Cách đánh giá giúp biết hệ thống tốt đến đâu, dùng số liệu nhóm | E mục 3, đoạn liên hệ Seminar 1 | N3.5 |
| C32 | Mọi đề tài có threat model ở D2 | P tr. 2, phần 6 | N3.6 |
| C33 | Có threat model trong proposal: cập nhật theo hệ thống và nêu thay đổi | P tr. 2, phần 6 | N3.6 |
| C34 | Chưa có: bổ sung bản đầu; không trừ vì proposal thiếu, chấm nội dung D2 | P tr. 2, phần 6 | N3.6 |
| C35 | Tài sản cần bảo vệ | P tr. 2, phần 6; X B14 | N3.6 |
| C36 | Điểm vào nội dung không tin cậy theo hệ thống thực tế | P tr. 2, phần 6 | N3.6 |
| C37 | Năng lực giả định của kẻ tấn công | P tr. 2, phần 6; X B14 | N3.6 |
| C38 | Mỗi điểm vào có biện pháp dự kiến; bảng nửa trang đủ | P tr. 2, phần 6; X B14 | N3.6 |
| C39 | Chưa cần chạy prompt injection ở D2; thuộc báo cáo cuối kỳ | P tr. 2, phần 6; X G40; E mục 3 | N3.6 |
| C40 | Theo tuần 45 tới vòng báo cáo thứ nhất, tuần 49, 02/12/2026 | P tr. 3, phần 7 | N3.7 |
| C41 | Ai phụ trách việc gì | P tr. 3, phần 7 | N3.7 |
| C42 | Giả định rủi ro nhất còn lại | P tr. 3, phần 7 | N3.7 |
| C43 | Nếu giả định sai: phạm vi thu hẹp và phần lõi giữ lại | P tr. 3, phần 7 | N3.7 |
| C44 | Tự đánh giá: đúng tiến độ/có rủi ro/cần thu hẹp | P tr. 3, phần 7 | N3.7 |
| C45 | Đóng góp mỗi thành viên khớp lịch sử commit | P tr. 3, phần 8; X B16 | N3.8 |
| C46 | AI-use: công cụ, mục đích, phần nhóm tự kiểm chứng | P tr. 3, phần 8; X B16 | N3.8 |

### Mục proposal còn thiếu phải hoàn thiện

| ID | Nội dung đã đối chiếu | Nguồn | Vị trí trong note |
| --- | --- | --- | --- |
| P01 | D2 là hạn cuối bổ sung; đã đầy đủ thì nhắc ngắn | P tr. 3, mục 3 | N4 |
| P02 | Ghi rõ Research/Application Track | P tr. 3, mục 3 | N4 |
| P03 | Research: giả thuyết có thể bác bỏ RT1, baseline bên ngoài RT2 | P tr. 3, mục 3 | N4, N9 |
| P04 | Application: nhóm người dùng, ít nhất 3 kịch bản, có bất cẩn/ý đồ xấu | P tr. 3, mục 3 | N4 |
| P05 | Mô hình phát triển và mô hình tạo số liệu, API/cục bộ, framework, phần tự viết | P tr. 3, mục 3 | N4 |
| P06 | Bảng tools/quyền và thiết kế bộ nhớ nếu còn thiếu | P tr. 3, mục 3 | N4 |
| P07 | Quy mô task, độ đo, baseline, số lần chạy nếu mới nêu chung | P tr. 3, mục 3 | N4, N3.5 |
| P08 | Threat model, kế hoạch theo tuần, phạm vi thu hẹp nếu thiếu | P tr. 3, mục 3 | N4 |
| P09 | Dữ liệu giả lập/tổng hợp: nói rõ và so với dữ liệu thật | P tr. 3, mục 3 | N4 |
| P10 | Nếu hứa dùng thử người thật: trạng thái thực hiện và điều học được | P tr. 3, mục 3 | N4 |

### Rubric và cách tính

| ID | Nội dung đã đối chiếu | Nguồn | Vị trí trong note |
| --- | --- | --- | --- |
| R01 | Đủ A1-A5/B1-B3, trọng số 15/15/10/5/5/20/15/15% và bằng chứng từng tiêu chí | X A12:C16, A18:C20; ghi chú B12:B16, B18:B20; E mục 4 | N5 |
| R02 | Năm khung 9-10/7-8/5-6/3-4/0-2 và mô tả | X B34:G38; E mục 4 | N5 |
| R03 | Mốc chấm là mức hoàn thành so proposal và chất lượng bằng chứng | X B32; E mục 4 | N5 |
| R04 | Kỳ vọng điểm cao A2: tái lập từ repo bằng một lệnh | X ghi chú B13 | N3.5, N5 |
| R05 | Công thức tổng, report/demo mỗi phần tối đa 5, tổng chỉ hiện đủ 8 | X F5:F8 và các công thức E/F tại hàng tiêu chí | N5 |
| R06 | Sheet nhóm, ô dropdown và ghi chú tiêu chí; không tự thêm yêu cầu nộp rubric | X G1-G8, D12:D16, D18:D20; danh sách hồ sơ P mục 1/E mục 3 | N1, N5 |

### Trình bày và giới hạn phạm vi

| ID | Nội dung đã đối chiếu | Nguồn | Vị trí trong note |
| --- | --- | --- | --- |
| L01 | 28/10/2026, 18:00-20:29, B4-305, G1-G8 | P tr. 1; E mục 5 | N6 |
| L02 | Tổng 15 phút; khoảng 10 phút trình bày có demo và 5 phút Q&A; B2 ghi “Đúng 10 phút” | P tr. 1; E mục 5; X ghi chú B19 | N5, N6, N9 |
| L03 | Ít nhất một task end-to-end, dữ liệu đề tài, ngay tại lớp, khớp report | E mục 5; X ghi chú B18 | N6, N5 |
| L04 | Video dự phòng sự cố mạng/API/máy, giải thích trace | E mục 5; X ghi chú B18 | N6 |
| L05 | Video-only khi không có sự cố không đạt Rất tốt B1 | E mục 5; X ghi chú B18 | N6 |
| L06 | Mọi thành viên có mặt, trả lời phần mình; Q&A chính xác/có chứng cứ/thừa nhận hạn chế | E mục 5; X ghi chú B20 | N6, N5 |
| L07 | Có mặt từ đầu, kiểm tra trình chiếu, mở sẵn demo/tài liệu | E mục 5 | N6 |
| L08 | Nội dung trình bày: thay đổi, kiến trúc, demo, số liệu/chi phí, threat model, kế hoạch/rủi ro | E mục 5; X ghi chú B19 | N6 |
| X01 | Không đưa công việc/điểm giám khảo Seminar thành yêu cầu D2 | E mục 1-2, 5-6 so với mục 3-4 | N9 |
| X02 | Hướng dẫn chung là liên kết tham chiếu từ PDF/email, chưa mở rộng nguồn website | P tr. 1; E mục 3 | N9 |

Checklist chính thức ở P mục 4 được bao phủ bởi các nhóm trên và được tổng hợp tại N7. N8 là gợi ý tổ chức bằng chứng, đã ghi rõ không phải định dạng bắt buộc.

## 3. Các chỉnh sửa sau đối chiếu sâu

1. Chép tài liệu nguồn vào repo, đổi các liên kết nguồn trong note từ đường dẫn Downloads/attachment sang đường dẫn tương đối trong repo.
2. Viết rõ vị trí trích dẫn “mục 2, phần 1”, “mục 3, phần 1” thay cho cách viết có thể bị hiểu là số tiểu mục chính thức.
3. Đưa quy mô task, độ đo, baseline và số lần chạy vào ngay phần đánh giá; vẫn giữ điều kiện bổ sung nếu proposal mới nêu chung chung.
4. Đổi “số liệu sơ bộ được chấp nhận” thành “số liệu sơ bộ là điều được mong đợi”, sát nguyên văn PDF hơn.
5. Bỏ câu đối chiếu với “số lượng tính năng được hứa”, vì nguồn chỉ quy định mức hoàn thành so với proposal và chất lượng bằng chứng.
6. Ghi riêng bốn điểm cần đọc đúng: số task 5-10; khoảng/đúng 10 phút; không tự suy ra cách tính phạt ngày lẻ; baseline ngoài cho Research và cấu hình đơn giản hơn cho đánh giá D2.

## 4. Những điểm giữ nguyên theo nguồn

- **“Ít nhất 5-10 task”**: PDF và Excel dùng dấu khoảng 5–10, email dùng 5-10. Không tự rút thành một ngưỡng duy nhất hoặc thành giới hạn tối đa 10.
- **Thời lượng**: cả hai cách viết “khoảng 10 phút” và “Đúng 10 phút” đều có trong nguồn; giữ tổng 15 phút có Q&A.
- **Nộp trễ**: không tự thêm cách làm tròn ngày lẻ hoặc xác định 10% tính trên cơ sở nào.
- **Baseline**: không tự gộp baseline bên ngoài RT2 với cấu hình đơn giản hơn; cũng không tự bắt buộc hai cấu hình riêng khi nguồn chưa nói vậy.
- **Threat model**: bắt buộc ở D2, nhưng thử prompt injection chưa bắt buộc; “giảm thiểu dự kiến” không được đổi thành tuyên bố đã kiểm chứng phòng thủ.
- **Tính tái lập**: bắt buộc có khả năng tái lập; “bằng một lệnh” là kỳ vọng điểm cao ghi trong comment A2. Kiểm tra công thức rubric không chứng minh số liệu thí nghiệm của nhóm tái lập được.

Kết luận trên chỉ áp dụng cho nội dung ba nguồn được lưu và phiên bản note đã đối chiếu, không phải cam kết tuyệt đối rằng tài liệu nguồn không có điểm chưa rõ hoặc rằng đồ án đã đáp ứng rubric.
