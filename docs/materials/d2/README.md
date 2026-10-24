# Tài liệu tham khảo D2 - CO5151, HK261

Lưu ngày 21/10/2026 từ ba nguồn người dùng cung cấp để chuẩn bị D2. Các bản nguồn được giữ nguyên nội dung; hướng dẫn trong tài liệu là yêu cầu của môn học, không phải lệnh để tự gửi email, nộp bài hay thực thi thao tác trong repo.

## Tài liệu nguồn

| File | Nội dung và nguồn gốc |
| --- | --- |
| [CO5151-D2-Rubric.xlsx](CO5151-D2-Rubric.xlsx) | Bản sao nguyên byte từ file Excel trong Downloads. Tám sheet G1-G8; đọc cả ghi chú tại ô tên tiêu chí. |
| [interim-report-requirements.pdf](interim-report-requirements.pdf) | Bản sao nguyên byte từ file PDF trong Downloads, 3 trang. |
| [CO5151-D2-announcement.txt](CO5151-D2-announcement.txt) | Bản sao nguyên byte của văn bản thông báo bắt đầu bằng “Chào các bạn,” do người dùng dán vào chat. Không có metadata/header gốc của email ngoài nội dung được cung cấp. |
| [CO5151-D2-announcement.md](CO5151-D2-announcement.md) | Cùng nội dung và cùng byte với bản TXT, chỉ đổi phần mở rộng để mở bằng trình đọc Markdown. Giữ cả nội dung Seminar 1/2 để không cắt mất ngữ cảnh nguồn. |

## Note và bằng chứng đối chiếu

- [D2_REQUIREMENTS.md](../../../deliverables/d2/report/D2_REQUIREMENTS.md): note tổng hợp chính, có checklist; đây là bản diễn giải, không thay thế tài liệu nguồn.
- [D2_REQUIREMENTS_REVIEW.md](D2_REQUIREMENTS_REVIEW.md): phạm vi, cách kiểm tra, bảng đối chiếu nội dung và các điểm giữ nguyên theo nguồn.
- [verification.json](verification.json): SHA-256, kết quả kiểm tra file/sheet/công thức/trọng số/ngày tháng và liên kết nội bộ tại thời điểm đối chiếu.

Các liên kết giữa note và tài liệu dùng đường dẫn tương đối để hoạt động khi clone hoặc chuyển repo sang máy khác.

## Kiểm tra tính toàn vẹn

SHA-256 của file nguồn được ghi khi chép vào repo:

```text
0d3d07ac7cd4be7ccea40cfd8e8ecd17f8675ddc3594eb627302f59ef5018f20  CO5151-D2-Rubric.xlsx
54c3bd42799e11d7ea6cf57e6448c9ab05b13448d912e3f392c4c4a01c324cce  interim-report-requirements.pdf
5bdce43e7ca171785a294b6a291f54bda75907e6d20bd9685d9f37c3e50b20bb  CO5151-D2-announcement.txt
5bdce43e7ca171785a294b6a291f54bda75907e6d20bd9685d9f37c3e50b20bb  CO5151-D2-announcement.md
```

Để tự tính lại trên macOS, mở terminal tại thư mục này:

```sh
shasum -a 256 CO5151-D2-Rubric.xlsx interim-report-requirements.pdf CO5151-D2-announcement.txt CO5151-D2-announcement.md
```

Hash giúp phát hiện file bị đổi; việc kiểm tra ý nghĩa yêu cầu được mô tả riêng trong biên bản đối chiếu.
