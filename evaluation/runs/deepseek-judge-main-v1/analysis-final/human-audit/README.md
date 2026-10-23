# Human audit — 12 mẫu, chưa có nhãn người

Chỉ đọc packets.json và SEMANTIC_JUDGING.md trong thư mục này trước khi chấm.
Không xem private-judge-details.json, mapping mode/seed hay điểm DeepSeek.

Điền labels.csv bằng đánh giá thực tế:
- reviewer: tên người thực sự chấm.
- judgeable: true/false; nếu false, ghi lý do trong notes và để các điểm trống.
- behaviour_appropriate: true/false theo nội dung câu trả lời, không chỉ action.
- correctness, completeness: 0, 1 hoặc 2 theo rubric.
- total_claims, unsupported_claims: số claim thực tế đã kiểm tra; ghi rõ bất đồng.
- notes: giải thích lỗi/nguồn hoặc câu hỏi/gold có vấn đề.

Không tự điền tên, điểm hoặc xác nhận chuyên gia khi chưa chấm. Không sửa câu trả
lời model hoặc nguồn. Ba output OFF chưa có phán quyết LLM hợp lệ cũng được
giữ nguyên; bất kỳ kết luận nào của người cần được lưu như nhãn người riêng.

Mẫu được chọn bằng hash cố định, phân tầng theo mode/category/kết quả judge và
ẩn các nhãn đó khi xuất packet. Agreement trên mẫu này chỉ là diagnostic của
mẫu, không chứng nhận toàn bộ population. Hiện chưa có agreement hoặc kappa.

Mẫu reliability hiện tại gồm 12 output có phán quyết LLM hợp lệ, để có thể tính agreement/kappa trên 12 cặp nhãn thực tế. Ba output còn thiếu phán quyết LLM được tách ở unresolved-packets.json để review có mục tiêu; không gộp chúng vào mẫu reliability cố định. Mẫu được chốt trước khi nhận bất kỳ nhãn người nào.
