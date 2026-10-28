# LuatCheck — Kịch Bản Thuyết Trình Đề Xuất D1 (Proposal Pitch · 3 Phút)

- **Người trình bày:** Võ Phạm Tuấn Dũng (đại diện Nhóm 8)
- **Thời lượng mục tiêu:** Tổng ~745 âm tiết $\approx$ 173 giây trên ngân sách 180 giây (3 phút).
- **Quy ước:** Đoạn trong ngoặc kép là lời nói; dòng nghiêng là chỉ dẫn thao tác (không đọc).

---

## PHẦN 1: 6 SLIDE CHÍNH (3 PHÚT)

### SLIDE 1 — Chưa tính giờ, nói trong lúc bước lên
> "Chào thầy và các bạn. Em là Dũng, nhóm 8. Đề tài của nhóm là LuatCheck — trợ lý pháp luật tiếng Việt chạy nội bộ, trả lời kèm bằng chứng và biết từ chối."

*$\rightarrow$ Bấm sang Slide 2 NGAY. Không đọc tên từng thành viên, không đọc mục lục. Bắt đầu bấm giờ từ Slide 2.*

---

### SLIDE 2 — `[0:00 → 0:30]` (~124 âm tiết $\approx$ 29 giây)
> "Người dùng là người không rành luật: nhân viên, chủ doanh nghiệp nhỏ, HR. Câu hỏi thật: sắp bị cho thôi việc, được báo trước bao nhiêu ngày?
>
> Hôm nay có hai lựa chọn, cả hai đều hỏng. Chatbot công cộng thì câu hỏi rời khỏi tổ chức, và điều luật nó trích có thể không đỡ nổi câu trả lời. Cổng pháp luật có văn bản gốc, nhưng phải biết trước mở cái nào.
>
> Vì sao là agent chứ không phải script? Vì quyết định trả lời, hỏi lại, hay từ chối phụ thuộc vào bằng chứng chỉ có sau khi truy hồi và kiểm chứng. Script phải cam kết trả lời trước khi biết điều đó — và đó chính là lỗi tụi em nhắm tới."

*$\rightarrow$ Câu cuối là câu quan trọng nhất slide này. Nói chậm lại, rồi chuyển slide.*

---

### SLIDE 3 — `[0:30 → 1:30]` (~229 âm tiết $\approx$ 53 giây — Slide quan trọng nhất)
*Chỉ tay theo mũi tên, TUYỆT ĐỐI không đọc hết chữ trên hình.*

> "Em đi theo mũi tên.
> Câu hỏi và tài liệu dán vào đi qua Input Guard: mọi văn bản dán vào và truy hồi được đều gắn nhãn không tin cậy, không bao giờ được đổi control policy hay quyền tool.
>
> Giữa là control loop. Mỗi bước model chọn đúng một trong năm hành động: `search_law`, `get_article`, `answer`, `clarify`, `refuse`. Ngân sách cứng: tối đa năm lời gọi tool, hai vòng sửa.
>
> Bên phải là tool layer, schema JSON tương thích MCP. Hai tool tra cứu chỉ đọc; `save_case` hoàn tác được; `send_summary` thì không, nên bắt buộc người xác nhận.
>
> Dưới là truy hồi lai BM25 cộng dense, RRF — trục một.
>
> Rồi tới kiểm chứng bằng chứng, trục hai. L1 luôn chạy: điều luật được trích có tồn tại không, có nằm trong kết quả truy hồi không, và câu khẳng định có được đoạn văn đó đỡ không. Fail thì quay lại loop sửa — mũi tên cam bên trái. Fail lặp lại thì từ chối.
>
> Khối tím là memory, yêu cầu R3. Ngắn hạn là case ledger: facts, truy vấn đã chạy, ID điều luật, ngân sách còn lại. Dài hạn là SQLite, chỉ ghi khi đã qua kiểm chứng — không ghi ca từ chối, không ghi dữ liệu cá nhân thô.
>
> Trục ba là guardrails: ở Input Guard, ở quyền tool, và ở egress duy nhất."

*$\rightarrow$ Nếu cháy giờ: bỏ đoạn tool layer. Nhưng PHẢI chỉ đủ ba chỗ thầy cần thấy — vòng lặp, memory, và ba nhãn A1/A2/A3.*

---

### SLIDE 4 — `[1:30 → 2:15]` (~182 âm tiết $\approx$ 42 giây)
> "Đánh giá có ba phần.
> Task set: hai trăm cặp câu hỏi–điều luật từ VLQA để đo truy hồi, và hai mươi task end-to-end — mười câu một điều luật, năm câu tổng hợp, ba câu không trả lời được, hai câu đối kháng. Cộng ít nhất mười ca tấn công.
>
> Metric: Recall và MRR cho truy hồi; đầu ra đo tỉ lệ câu không có bằng chứng đỡ, citation precision và recall, và tỉ lệ tấn công thành công.
>
> Phần thứ ba là phần tụi em quan tâm nhất: làm sao biết chính cái thước đo là đúng. Tụi em gán nhãn tay ba mươi cặp claim–điều luật để audit bộ verifier, đo độ chính xác và tỉ lệ từ chối sai. Utility và attack-success báo riêng, nên từ chối hết mọi thứ không được điểm cao hơn.
>
> Số lần chạy: ba cấu hình nhân ba seed nhân hai mươi task, là một trăm tám mươi lần chạy. A với B tách đúng cơ chế tụi em claim; C cho biết ràng buộc chạy nội bộ tốn bao nhiêu chất lượng."

*$\rightarrow$ Nếu thầy hỏi "sao chỉ 20 task": vì mỗi task chạy 9 lần và có verifier audit gán nhãn tay. Ưu tiên đo được sai số hơn là số lượng task.*

---

### SLIDE 5 — `[2:15 → 2:45]` (~126 âm tiết $\approx$ 29 giây)
> "Threat model v0. Tài sản cần bảo vệ: tính đúng của câu trả lời, dữ liệu người dùng, nhật ký audit, và các điểm đi ra ngoài.
>
> Dữ liệu không tin cậy vào ở năm chỗ: câu hỏi, tài liệu dán vào, văn bản truy hồi được, output của tool, và payload của `send_summary` — cũng là đường ra duy nhất.
>
> Biện pháp chính: mọi văn bản dán vào và truy hồi được đều gắn nhãn không tin cậy, không được đổi control policy hay quyền tool. Mặc định chỉ đọc; đường ra duy nhất bắt buộc người xác nhận và ghi log trước khi gửi.
>
> Kiểm bằng bộ tấn công ít nhất mười ca, trong đó hai ca cài ngay vào chính index của tụi em."

*$\rightarrow$ Nhấn câu cuối. Cài tấn công vào chính index của mình là indirect injection thật, không phải chỉ test prompt người dùng — chỗ này ăn điểm R6.*

---

### SLIDE 6 — `[2:45 → 3:00]` (~62 âm tiết $\approx$ 15 giây — Nói gọn rồi DỪNG)
> "Giả định rủi ro nhất: một model 4 tới 8 tỉ tham số chạy nội bộ có thể ở trong vòng lặp năm hành động và hồi phục sau khi kiểm chứng fail, đủ thường xuyên để đo được.
> Nếu sai, tụi em lên 8B rồi 32B, giữ nguyên schema và ngân sách cứng. Kiểm tra trích dẫn L1 thì không bao giờ bỏ.
> Em xin hết ạ."

*$\rightarrow$ DỪNG Ở ĐÂY. Không bấm tiếp — các slide sau là backup, chỉ mở khi thầy hỏi. Còn dư giây nào thì im lặng, đừng nói thêm.*

---

## PHẦN 2: SLIDE BACKUP D1 (CHỈ BẬT KHI THẦY HỎI)

- **Thứ tự backup phía sau:**
  - Slide 7: Slide chắn (nếu lỡ bấm quá Slide 6 thì dừng ở đây)
  - Slide 8: MỚI (bảng so sánh với cái đã có)
  - Slide 9: KHÔNG TẦM THƯỜNG (quyết định thiết kế khó nhất)
  - Slide 10: CÓ Ý NGHĨA (ai chịu ảnh hưởng, bằng chứng)
  - Slide 11: KHẢ THI (kế hoạch theo tuần + phân công)
  - Slide 12: Bản đồ R2/R3/R4/R5/R6
  - Slide 13: References

### 1. Câu hỏi: "MỚI ở chỗ nào?"
- **Trả lời ngắn:** "Không có cái nào trong bốn cái này vừa chạy nội bộ, vừa kiểm chứng từng claim, vừa có đường từ chối tường minh. Cái mới là tổ hợp, không phải model mới hay retriever mới — tụi em nói rõ là không đề xuất hai thứ đó."
- **Nếu thầy hỏi "ví dụ gần nhất đã có là gì":** Commercial legal AI (Lexis+ AI, Westlaw AI) — Magesh 2025 đo và vẫn thấy mis-citation; và các công cụ đó đều là cloud.

### 2. Câu hỏi: "Quyết định thiết kế khó nhất là gì? Sao AI assistant không tự làm được?"
- **Trả lời theo 3 nhịp:**
  1. "Quyết định khó nhất là: khi kiểm chứng fail thì làm gì. Có bốn lựa chọn hợp lệ và lựa chọn đúng phụ thuộc vào lý do fail."
  2. "Sai hướng nào cũng chết: từ chối quá tay thì sản phẩm vô dụng; trả lời quá tay thì đúng lại cái lỗi mình định sửa. Ngưỡng chấp nhận quyết định mình chết hướng nào."
  3. "Coding assistant dựng được cái loop trong một buổi chiều — tụi em có ghi rõ là có dùng. Cái nó không làm được là chỉ ra ngưỡng đó nằm ở đâu trên văn bản pháp luật tiếng Việt, và trả cái giá đo đạc đánh đổi đó. Phần đo đạc mới là đồ án."

### 3. Câu hỏi: "Nếu chạy hoàn hảo thì ai dùng? Hoặc trả lời câu hỏi nghiên cứu nào?"
- **Trả lời ứng dụng:** "Người dùng là SME không có phòng pháp chế. Hiện tại HR của họ hoặc đoán, hoặc dán hợp đồng vào chatbot công cộng — mà từ 1/1/2026 thì việc đó vướng Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15."
- **Nếu thầy đẩy sang hướng nghiên cứu:** "Câu hỏi nghiên cứu là kiểm chứng bằng chứng ở mức claim mua được bao nhiêu grounding, và trả giá bao nhiêu bằng coverage và latency, trên một SLM chạy nội bộ."

### 4. Câu hỏi: "Kế hoạch theo tuần so với 10 tuần thực có, có khả thi không?"
- **Trả lời:** "Hai trong ba thành viên là software engineer chưa làm agentic AI, mỗi người khoảng bốn tiếng một tuần. Nên tụi em chốt interface contract ở tuần 3 để ba nhánh chạy độc lập, và chỉ một nhánh là agent-specific. Retrieval, UI, storage, fault harness đều là kỹ thuật phần mềm bình thường."
- **Nếu thầy hỏi "không có GPU thì sao":** Fallback là 4B quantize trên máy cá nhân, rồi tới GPU của trường hoặc tổ chức. Chỉ số latency đổi, còn claim về privacy không đổi.

### 5. Câu hỏi về R2/R3/R4/R5/R6
- Mở đúng Slide 12 và chỉ đúng dòng requirement được hỏi.
- **Nếu thầy hỏi "MCP đã dựng chưa":** "Chưa. D1 tụi em giữ schema JSON tương thích MCP; phơi thành MCP server là việc của D2, và không phải sửa agent."
