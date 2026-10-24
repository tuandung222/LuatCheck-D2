# Human audit packets — hcmut (30 items, blind)

Read with SEMANTIC_JUDGING.md. Fill labels.csv (one row per review_id). Variant, seed and the LLM judgement are hidden on purpose.


---

## 1. `1a15126b11c2e867b027649b`

**Question:** Theo khoản 5.5 Điều 5 được sửa đổi bởi Quyết định 1260/QĐ-ĐHBK (áp dụng từ học kỳ 1 năm học 2025-2026), điểm trung bình tích lũy tối thiểu (thang 4) để sinh viên được đăng ký các học phần tốt nghiệp là bao nhiêu? Một sinh viên có điểm trung bình tích lũy 2,35 có đạt ngưỡng điểm này không, và học lực được xếp loại gì theo khoản 15.2 do Quyết định 1259/QĐ-ĐHBK sửa đổi?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Ngưỡng tối thiểu là điểm trung bình tích lũy (GPA) từ 2.0 trở lên theo thang điểm 4 (áp dụng từ học kỳ 1 năm học 2025-2026). GPA 2,35 đạt ngưỡng GPA này (việc đăng ký học phần tốt nghiệp còn các điều kiện khác trong khoản 5.5, không được hỏi ở đây), và học lực xếp loại Trung bình (từ 2,00 đến cận 2,50).

**Reference evidence:**
- `HCMUT_HVDT1260_Dieu_1_S5_5`: Sinh viên phải có điểm trung bình tích lũy (GPA) từ 2.0 trở lên (theo thang điểm 4)
- `HCMUT_HVCHUNG1259_Dieu_1_S15_2`: Từ 2,00 đến cận 2,50: Trung bình

**Candidate behaviour:** answered

**Candidate answer:**

> Theo nội dung văn bản [HCMUT_HVDT1260_Dieu_1_S5_5]:
> - Điểm trung bình tích lũy 2.35 nằm trong khoảng 'Trung bình' theo Điều 15.2.
> - Để đăng ký tốt nghiệp, GPA cần >= 2.0 (Điều 5.5).
> 
> Dựa trên quy định 15.2: Điểm trung bình 2.35 thuộc nhóm 'Trung bình'.

**Candidate citations:** `HCMUT_HVDT1260_Dieu_1_S5_5`

<details><summary>Source `HCMUT_HVCHUNG1259_Dieu_1_S15_2` — “15.2 Xếp loại học lực</summary>

“15.2 Xếp loại học lực
Người học được xếp loại học lực theo điểm trung bình học kỳ, điểm trung bình
năm học hoặc điểm trung bình tích lũy như sau:
Từ 3,60 đến 4,00: Xuất sắc;
Từ 3,20 đến cận 3,60: Giỏi;
Từ 2,50 đến cận 3,20: Khá;
Từ 2,00 đến cận 2,50: Trung bình;
Từ 1,00 đến cận 2,00: Yếu;
Dưới 1,00: Kém.”
6. Sửa đổi, bổ sung khoản 16.2 Điều 16 như sau:

</details>

<details><summary>Source `HCMUT_HVDT1260_Dieu_1_S5_5` — “5.5 Đăng ký các học phần tốt nghiệp</summary>

“5.5 Đăng ký các học phần tốt nghiệp
Các học phần tốt nghiệp (Thực tập ngoài trường, Đồ án chuyên ngành, Khóa luận
tốt nghiệp) được thiết kế vào cuối chương trình đào tạo. Sinh viên phải hoàn thành điều
kiện về chuẩn ngoại ngữ và số tín chỉ tích luỹ ngành trước khi được phép đăng ký các học
phần này.
Riêng học phần Thực tập ngoài trường/Thực tập kỹ sư chỉ mở trong học kỳ Hè, đăng
ký theo lịch học vụ học kỳ hè, dự kiến bắt đầu đăng ký từ giữa học kỳ 2. Sinh viên có nhu
cầu đăng ký các học phần thực tập trong học kỳ chính phải đăng ký với Khoa quản lý để
được đồng ý tổ chức học phần thực tập trong học kỳ chính.
Học phần đang học được xem là tạm đạt và tạm tính vào số tín chỉ tích lũy khi xét
đăng ký học phần cho sinh viên.
Sinh viên phải tích luỹ đủ ít nhất 65% (chương trình song ngành là 52%) số tín chỉ
của chương trình đào tạo để đăng ký học phần Thực tập ngoài trường.
Sinh viên phải tích luỹ đủ ít nhất 70% (chương trình song ngành là 76%) số tín chỉ
của chương trình đào tạo để đăng ký học phần Đồ án chuyên ngành.
Sinh viên phải tích luỹ số đủ ít nhất 82.5% (chương trình song ngành là 86%) số tín
chỉ của chương trình đào tạo, hoàn thành tối thiểu 80% chương trình rèn luyện sinh viên
theo quy định của trường và đạt Chuẩn ngoại ngữ tốt nghiệp để đăng ký học phần Khoá
luận tốt nghiệp.
Sinh viên phải có điểm trung bình tích lũy (GPA) từ 2.0 trở lên (theo thang điểm 4)
để được đăng ký các học phần tốt nghiệp (áp dụng từ học kỳ 1 năm học 2025-2026).”
3. Sửa đổi, bổ sung khoản 7.1 Điều 7 như sau:

</details>


---

## 2. `1ccadfbdc769b22d43b25605`

**Question:** Sinh viên vi phạm Nội quy học đường sẽ được xử lý theo căn cứ nào, và mức xử lý phụ thuộc vào yếu tố nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Theo Quy chế Công tác sinh viên của Trường và quy định của pháp luật; tùy theo mức độ vi phạm.

**Reference evidence:**
- `HCMUT_NOIQUY1924_Dieu_6`: sẽ bị xử lý theo Quy chế Công tác sinh viên Trường và quy định của pháp luật
- `HCMUT_NOIQUY1924_Dieu_6`: tùy theo mức độ vi phạm

**Candidate behaviour:** refused

**Candidate answer:**

> Không tìm thấy nội dung quy định chi tiết về mức xử lý vi phạm trong tài liệu đã tra cứu.

<details><summary>Source `HCMUT_NOIQUY1924_Dieu_6` — Điều 6. Tổ chức thực hiện</summary>

Điều 6. Tổ chức thực hiện
1. Lãnh đạo các đơn vị, Ban cán sự lớp có trách nhiệm triển khai Nội quy học đường
này; Trưởng các đơn vị chịu trách nhiệm trước Hiệu trưởng về việc thực hiện Nội
quy học đường của sinh viên thuộc đơn vị quản lý.
2. Phòng Công tác sinh viên, Phòng Thanh tra - Pháp chế, Tổ Bảo vệ có trách nhiệm
kiểm tra giám sát việc thực hiện Nội quy của các đơn vị và cá nhân liên quan.
3. Trong trường hợp sinh viên vi phạm Nội quy, tùy theo mức độ vi phạm, sinh viên
sẽ bị xử lý theo Quy chế Công tác sinh viên Trường và quy định của pháp luật.
4. Định kỳ hằng năm hoặc khi có đề xuất của các đơn vị, Phòng Công tác sinh viên
kiến nghị Hiệu trưởng xem xét, sửa đổi, cập nhật, bổ sung Nội quy cho phù hợp
với tình hình thực tế và các quy định hiện hành.
HIỆU TRƯỞNG
Mai Thanh Phong

</details>


---

## 3. `1e8b0b3139d2c1866d0847ed`

**Question:** Theo Nội quy học đường, quy định cấm hút thuốc lá trong khuôn viên Trường nêu rõ bao gồm cả loại thuốc lá nào ngoài thuốc lá thông thường?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Bao gồm cả thuốc lá điện tử.

**Reference evidence:**
- `HCMUT_NOIQUY1924_Dieu_5`: hút thuốc lá trong khuôn viên Trường (bao gồm thuốc lá
điện tử)

**Candidate behaviour:** answered

**Candidate answer:**

> Dựa trên các thông tin tra cứu, quy định của Trường Đại học Bách khoa - ĐHQG-HCM (thực hiện trong Nội quy học đường) chỉ cấm 'hút thuốc lá' chung, không phân biệt cụ thể loại thuốc lá khác. Các văn bản đã cung cấp chi tiết là: 'kể cả thuốc lá điện tử'.

**Candidate citations:** `HCMUT_UNGXU3408_Dieu_4`

<details><summary>Source `HCMUT_NOIQUY1924_Dieu_5` — Điều 5. Những hành vi sinh viên KHÔNG được phép thực hiện</summary>

Điều 5. Những hành vi sinh viên KHÔNG được phép thực hiện
1. Gian lận trong học tập, kiểm tra, thi cử.
2. Cho người khác mượn thẻ sinh viên hoặc mượn thẻ sinh viên của người khác để
sử dụng, sử dụng thẻ sinh viên sai mục đích.
3. Đi xe máy, xe đạp trong khuôn viên Trường.
4. Dẫm, nằm, ngồi lên cỏ ở các khu vực có biển cấm trong khuôn viên Trường; hái
hoa, bẻ cành cây trong khuôn viên Trường; chơi thể thao tại những địa điểm ngoài
khu vực sân thể dục thể thao theo quy định của Trường.
5. Tổ chức hoặc tham gia cờ bạc dưới mọi hình thức trong khuôn viên Trường.
6. Mang theo hoặc sử dụng các chất cháy, chất gây nổ; các loại vũ khí, hung khí vào
Trường.
7. Mang đồ ăn vào lớp học, gi ảng đường và hội trường. Mang theo động vật, thú
nuôi vào Trường.
8. Sử dụng, mua bán, tàng trữ các chất ma túy, các chất kích thích dưới mọi hình
thức; uống rượu, bia và hút thuốc lá trong khuôn viên Trường (bao gồm thuốc lá
điện tử); say rượu bia khi đến Trường.
9. Tự ý viết, dán quảng cáo, thông báo trong khuôn viên Trường; viết, vẽ, sơn bậy,
bôi xóa, làm bẩn, làm mất vệ sinh và làm hư hỏng các trang thiết bị học tập, máy
móc, dụng cụ thực hành thí nghiệm, cơ sở vật chất … của Trường.
10. Tự ý sử dụng tài sản của Nhà trường; tự ý di chuyển các trang thiết bị, tài sản ra
khỏi vị trí đã sắp xếp, lắp đặt trong phòng và trong khuôn viên Trường. Đứng lên
bàn ghế, leo trèo hoặc ngồi trên lan can, khung cửa sổ và trên bàn học, bàn giáo
viên.
11. Lưu hành, tuyên truyền các ấn phẩm, tài liệu, thông tin phản động, phim ảnh
không lành mạnh và các tài liệu cấm khác theo quy định của Nhà nước.
12. Gây bè phái, gây mất đoàn kết nội bộ trong tập thể lớp và trong Trường. Gây gổ,
đánh nhau hoặc kích động đánh nhau, tổ chức băng nhóm, tụ tập gây mất an ninh,
trật tự dưới mọi hình thức.
13. Không lợi dụng mạng xã hội nhằm mục đích xâm phạm đời tư, công việc và học
tập của cá nhân, cơ quan, tổ chức, đoàn thể; có ý thức bảo vệ, xây dựng hình ảnh,
thương hiệu của Nhà trường trên không gian mạng.
14. Không sử dụng từ ngữ gây thù hận, kích động bạo lực, phân biệt vùng miền, giới
tính, tôn giáo, dân tộc.
15. Tổ chức, tham gia, truyền bá các hoạt động mê tín dị đoan, các hoạt động tôn
giáo và các hành vi vi phạm đạo đức khác trong và ngoài khuôn viên Trường.
16. Tổ chức, tham gia các hoạt động chính trị trái pháp luật trong và ngoài khuôn
viên Trường.
17. Tham gia các hoạt động tập thể mang danh nghĩa Nhà trường khi chưa được Nhà
trường cho phép.
18. Có hành vi xúc phạm nhân phẩm, danh dự, xâm phạm tới thân thể, sức khỏe và
tài sản của cán bộ, giảng viên, người lao động và sinh viên khác của Nhà trường.
19. Tổ chức hoặc tham gia các hoạt động vi phạm pháp luật khác.

</details>

<details><summary>Source `HCMUT_UNGXU3408_Dieu_4` — Điều 4. Quy tắc chung</summary>

Điều 4. Quy tắc chung
1. Có trách nhiệm xây dựng và bảo vệ hình ảnh, thương hiệu của Trường Đại học Bách
khoa – ĐHQG-HCM.
2. Trang phục lịch sự, gọn gàng phù hợp với văn hóa học đường, khuyến khích VC –
NLĐ sử dụng trang phục thương hiệu của Trường. VC – NLĐ mặc lễ phục trang
trọng, lịch sự theo quy định của sự kiện.
3. Chấp hành nghiêm chủ trương, đường lối của Đảng, chính sách pháp luật của Nhà
nước và quy định của Nhà trường; kiên quyết đấu tranh, ngăn chặn những hành vi
vi phạm pháp luật, vi phạm quy định của Nhà trường.
4. Có tác phong làm việc nghiêm túc, chuyên nghiệp; chấp hành nghiêm quy định về
thời gian làm việc của Nhà trường, sử dụng hiệu quả thời gian làm việc; sử dụng
ngôn ngữ chuẩn mực, rõ ràng; sẵn sàng lắng nghe, chia sẻ và giú p đỡ người học,
đồng nghiệp.
5. Tôn trọng danh dự, uy tín của cơ quan, tổ chức, cá nhân có quan hệ công tác; chân
thành, thiện chí, sẵn sàng hỗ trợ lẫn nhau để hoàn thành nhiệm vụ.
6. Thực hiện đúng nhiệm vụ, quyền hạn được giao; giữ gìn đoàn kết nội bộ; phát h uy
trách nhiệm nêu gương và xây dựng môi trường làm việc, học tập chuyên nghiệp,
thân thiện.
7. Tích cực xây dựng không gian làm việc xanh, sạch, đẹp và môi trường công sở văn
minh, thân thiện; không lưu trữ và phát tán các hình ảnh, nội dung văn hóa phẩm
đồi trụy, tài liệu chống phá Đảng, Nhà nước, Nhà trường.
8. Không sử dụng, mua bán, tàng trữ trái phép các chất ma túy, các chất kích thích
dưới mọi hình thức; không hút thuốc lá trong khuôn viên Trường (kể cả thuốc lá
điện tử).

</details>


---

## 4. `3ebabe19265ceff0a86ee6f2`

**Question:** Theo Phụ lục 1 được thay thế bởi Quyết định 2749/QĐ-ĐHBK, kết quả kiểm tra tiếng Anh theo định dạng TOEIC vào cuối học kỳ 1 năm nhất được dùng để làm gì, và có được dùng nhiều lần không?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Được dùng để xét miễn các học phần Anh văn 1, 2, 3, 4 tương ứng theo thang điểm quy đổi tại tiểu mục 3.1 mục 3 của Phụ lục; việc xét miễn này chỉ thực hiện một lần duy nhất (không dùng lại nhiều lần).

**Reference evidence:**
- `HCMUT_HVDT2749_PhuLuc_1`: Vào cuối học kỳ 1 năm nhất, Nhà trường tổ chức thêm một kỳ kiểm tra trình độ tiếng Anh
đầu vào theo định dạng TOEIC
- `HCMUT_HVDT2749_PhuLuc_1`: Kết quả kiểm tra này được sử dụng để xét miễn một lần duy nhất các học phần Anh văn 1,
2, 3, 4 tương ứng theo thang điểm quy đổi tại bảng quy đổi tại tiểu mục 3.1 mục 3 của Phụ

**Candidate behaviour:** answered

**Candidate answer:**

> Chào bạn, dựa trên cơ sở dữ liệu và văn bản quy định đã tra cứu (Quy định Quy tắc ứng xử tại Trường Đại học Bách khoa – Thành phố Hồ Chí Minh - Số 3408/QĐ-ĐHBK), **không có thông tin nào** xác nhận TOEIC (Thái độ tiếng Anh) là một mục tiêu cụ thể hoặc quy định trong văn bản này.
> 
> Quy định 3408/QĐ-ĐHBK liên quan đến các nội dung: Quy tắc ứng xử, Hiệu lực thi hành và Khen thưởng/Kỷ luật. Các quyết định trước đây của Nhà trường (nếu có) về nội dung quy tắc ứng xử có hiệu lực nhưng không đề cập đến TOEIC.

**Candidate citations:** `HCMUT_UNGXU3408_QD_Dieu_1`

<details><summary>Source `HCMUT_HVDT2749_PhuLuc_1` — PHỤ LỤC 1. QUY ĐỊNH VỀ CHUẨN NGOẠI NGỮ</summary>

PHỤ LỤC 1. QUY ĐỊNH VỀ CHUẨN NGOẠI NGỮ
(Ban hành kèm theo Quyết định số: /QĐ-ĐHBK, ngày tháng năm 2026
của Hiệu trưởng trường Đại học Bách khoa – ĐHQG-HCM)
A. DÀNH CHO CHƯƠNG TRÌNH GIẢNG DẠY BẰNG TIẾNG VIỆT
Các quy định chuẩn ngoại ngữ sau đây dành cho các sinh viên chương trình đào tạo giảng
dạy bằng tiếng Việt. Các sinh viên tiêu chuẩn chương trình giảng dạy bằng tiếng Việt là lưu
học sinh Lào, Campuchia được miễn các chuẩn ngoại ngữ từng năm và chuẩn ngoại ngữ
tốt nghiệp, nhưng không được miễn các học phần tiếng Anh trong chương trình đào tạo.
1. Chuẩn ngoại ngữ từng năm học
Sinh viên phải đạt chuẩn ngoại ngữ từng năm theo quy định để đăng ký môn học cho năm
tiếp theo. Chuẩn ngoại ngữ từng năm được quy định cụ thể như sau:
a) Chuẩn ngoại ngữ tiếng Anh từng năm dành cho sinh viên chương trình tiêu chuẩn, vừa
làm vừa học, Bằng 2
- Từ Khóa 2023 về trước
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất Anh văn cơ bản 2 Học phần ngoài chương trình đào tạo
Năm thứ hai Anh văn 1 Hết năm nhất
Năm thứ ba Anh văn 1, 2, 3 Hết năm hai
Năm thứ tư Anh văn 1, 2, 3, 4 Hết năm ba
- Từ Khóa 2024 về sau (áp dụng từ học kỳ 1 năm học 2026-2027)
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất Anh văn cơ bản 2 Học phần ngoài chương trình đào tạo
Năm thứ hai Anh văn 1 Hết năm nhất
Năm thứ ba, tư Anh văn 1, 2, 3, 4 Hết năm hai
Lưu ý: Điều kiện tiên quyết của các học phần Anh văn 1, 2, 3 và 4 tương ứng là Anh văn
cơ bản 2, Anh văn 1, 2 và 3.
Chuẩn ngoại ngữ tiếng Anh từng năm không áp dụng đối với sinh viên chương trình định
hướng Nhật Bản, chương trình đào tạo kỹ sư chất lượng cao tại Việt Nam (PFIEV).
b) Chuẩn ngoại ngữ tiếng Pháp từng năm dành cho sinh viên Chương trình đào tạo kỹ sư
chất lượng cao tại Việt Nam (PFIEV) từ khóa 2024 về sau, áp dụng từ học kỳ 1 năm học
2026-2027.
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất
Năm thứ hai Pháp văn 1 Hết năm nhất
Năm thứ ba Pháp văn 1, 2, 3, 4 Hết năm hai
Năm thứ tư Pháp văn 1, 2, 3, 4, 5, 6 Hết năm ba
c) Chuẩn ngoại ngữ tiếng Nhật từng năm dành cho sinh viên Chương trình định hướng
Nhật Bản từ khóa 2026 về sau:
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất
Năm thứ hai Tiếng Nhật 1, 2 Hết năm nhất
Năm thứ ba Tiếng Nhật 1, 2, 3, 4 Hết năm hai
Năm thứ tư Tiếng Nhật 1, 2, 3, 4, 5, 6 Hết năm ba
2. Chuẩn ngoại ngữ tốt nghiệp
Chuẩn ngoại ngữ tốt nghiệp được quy định theo chứng chỉ ngoại ngữ quốc tế như sau:
Chương trình,
hình thức đào tạo
Chuẩn ngoại ngữ tốt nghiệp
Tiếng Anh (tương đương
TOEIC) Khác
Nghe-Đọc Nói-Viết
Chương trình tiêu chuẩn 500 (khoá 2018 v ề
trước)
550 (khoá 2019)
600 (từ khoá 2020)
200
Chương trình Định hướng Nhật
Bản Không áp dụng JLPT N3 (tiếng Nhật)
Chương trình tài năng 600 (khoá 2018 v ề
trước)
650 (khoá 2019)
700 (từ khoá 2020)
245
Chương trình đào tạo kỹ sư chất
lượng cao t ại Vi ệt Nam
(PFIEV)
600 (khoá 2018 v ề
trước)
650 (khoá 2019)
700 (từ khoá 2020)
245
DELF B1
TCF B1
(tiếng Pháp)
Vừa làm vừa học,
Đào tạo từ xa
400 (khoá 2017 v ề
trước)
450 (khoá 2018)
500 (khoá 2019)
600 (từ khoá 2020)
200
(từ khoá
2021)
Chính quy Bằng thứ hai Học chương trình đào tạo chính quy của khóa nào thì áp
dụng chuẩn của khóa đó.
Các chứng chỉ tiếng Anh bao gồm đầy đủ các kỹ năng Nghe – Đọc – Nói – Viết để xét
chuẩn tốt nghi ệp g ồm: IELTS, TOEFL iBT (không s ử dụng ch ứng ch ỉ TOEFL iBT
Home Edition), PET, FCE, CAE, PTE Academic, Linguaskill, APTIS ESOL. Khi đ ạt
mức điểm tương đương TOEIC theo bảng quy đ ổi tại mục 3.1 của Phụ lục này, sinh
viên được xét đạt chuẩn ngoại ngữ tốt nghiệp cho tất cả các kỹ năng.
Tạm thời cho phép sinh viên s ử dụng kết quả các kỳ kiểm tra k ỹ năng Nói – Viết do
Trung tâm Ngoại ngữ Trường Đại học Bách khoa tổ chức để xét tốt nghiệp.
Khi xét điều kiện đăng ký học phần Khóa luận tốt nghiệp, cho phép áp dụng chuẩn ngoại
ngữ tốt nghiệp tiếng Anh ch ỉ đối với kỹ năng Nghe – Đọc, Chương trình Định hướng
Nhật Bản là JLPT N3 (tiếng Nhật).
3. Quy đổi các bằng cấp và chứng chỉ ngoại ngữ
3.1. Các chứng chỉ tiếng Anh quốc tế được quy đổi tương đương như sau:
Các chứng chỉ tiếng Anh Quốc tế Các học phần Anh văn
TOEIC
Listening
&
Reading
TOEFL
iBT
TOEFL
iBT 2026
(Overall
Score)
IELTS PET FCE CAE PTE Academic Lingua -skill APTIS ESOL VSTEP VEPT Cơ bản 1 2 3 4
400 40 2.5 - - - - - - - - Đạt - - - -
450 49 3 - - - - - 140 - 4.0 43 Đạt Đạt - - -
500 54 3 4.0 Grade C - - - 143 - 4.5 51 Đạt Đạt Đạt - -
550 59 3.5 4.5 Grade B - - - 146 - 5.0 59 Đạt Đạt Đạt Đạt -
600 64 3.5 5.0 Grade B - - 41 149 B1 5.5 67 Đạt Đạt Đạt Đạt Đạt
650 70 3.5 5.0 Grade A - - 43 152 - X X Đạt Đạt Đạt Đạt Đạt
700 79 4 5.5 Grade A - - 45 155 B1 X X Đạt Đạt Đạt Đạt Đạt
785 85 4 5.5 X
Grade
C,
Grade
B,
Grade
A
Level
B2
Grade
C,
Grade
B,
Grade
A
48 160 B2 X X Đạt Đạt Đạt Đạt Đạt
Lưu ý: Không sử dụng chứng chỉ ngoại ngữ TOEFL iBT Home Edition
Thời hạn công nhận chứng chỉ: trong thời hạn 2 năm tính từ ngày cấp cho đến ngày đăng
ký xét đạt chuẩn.
Bằng tốt nghiệp bậc đại học trở lên ngành/chuyên ngành tiếng Anh được xét miễn các học
phần Anh văn 1, 2, 3, 4.
3.2. Các chứng chỉ tiếng Pháp được quy đổi tương đương như sau:
Các chứng chỉ tiếng Pháp Các học phần tiếng Pháp
Tú tài
Pháp
Tốt nghiệp phổ thông
chương trình Song ngữ và
tăng cường tiếng Pháp
DELF TCF 1 2 3 4 5 6 7*
X X A1 100-199 Đạt
X X A2 200-299 Đạt Đạt
B1,
B2
300-399 Đạt Đạt Đạt Đạt Đạt Đạt Đạt
*Pháp văn 7: áp dụng cho sinh viên Khoá 2018 về trước.
3.3. Các chứng chỉ tiếng Nhật được quy đổi tương đương như sau:
Sinh viên đã có chứng chỉ tiếng Nhật JLPT trong vòng 12 tháng, được xem xét miễn một
số học phần tiếng Nhật như sau:
a) Đối với Khóa 2023 về trước:
Chứng chỉ Được xét miễn Ghi chú
JLPT N1 Tiếng Nhật 1, 2, 3, 4, 5, 6
JLPT N2 Tiếng Nhật 1, 2, 3
JLPT N3 Tiếng Nhật 1, 2
b) Đối với Khóa 2024 về sau:
Chứng chỉ Được xét miễn Ghi chú
JLPT N1 Tiếng Nhật 1, 2, 3, 4, 5, 6
JLPT N2 Tiếng Nhật 1, 2, 3, 4
JLPT N3 Tiếng Nhật 1, 2, 3
4. Nguyên tắc xét miễn các học phần tiếng Anh và các chuẩn ngoại ngữ
4.1. Ngay khi nhập học
Sau khi nhập học, Nhà trường tổ chức một kỳ thi xếp trình độ tiếng Anh dành cho sinh viên
chương trình giảng dạy bằng tiếng Việt vừa trúng tuyển. Căn cứ vào kết quả kỳ thi, sinh
viên được phân lớp hoặc đăng ký các học phần Anh văn 1, 2, 3, 4 tương ứng. Kết quả thi
xếp trình độ tiếng Anh chỉ được sử dụng để xét tạm đạt điều kiện tiên quyết khi đăng ký
các học phần Anh văn trong học kỳ 1 và học kỳ 2 của năm nhất; không có giá trị xét miễn
bất kỳ học phần Anh văn nào trong chương trình đào tạo.
Vào cuối học kỳ 1 năm nhất, Nhà trường tổ chức thêm một kỳ kiểm tra trình độ tiếng Anh
đầu vào theo định dạng TOEIC dành cho sinh viên chương trình giảng dạy bằng tiếng Việt.
Kết quả kiểm tra này được sử dụng để xét miễn một lần duy nhất các học phần Anh văn 1,
2, 3, 4 tương ứng theo thang điểm quy đổi tại bảng quy đổi tại tiểu mục 3.1 mục 3 của Phụ
lục này. Đối với các học phần không được miễn, sinh viên phải đăng ký học theo quy định.
Sinh viên vừa trúng tuyển, đã có bằng tốt nghiệp từ bậc đại học ngành/chuyên ngành tiếng
Anh, trong học kỳ đầu tiên tính từ lúc trúng tuyển, được đăng ký xét miễn các học phần
Anh văn 1, 2, 3 và 4.
4.2. Trong quá trình học
Trong quá trình học, sinh viên có thể sử dụng chứng chỉ tiếng Anh quốc tế còn thời hạn phù
hợp để được xét miễn các học phần Anh văn 1, 2, 3, 4 (theo quy định tại mục 3.1 của Phụ
lục này) và đồng thời được xét đạt chuẩn ngoại ngữ tốt nghiệp (theo quy định tại mục 2 của
Phụ lục này).
B. DÀNH CHO CHƯƠNG TRÌNH GIẢNG DẠY BẰNG TIẾNG ANH
Quy định chuẩn ngoại ngữ này bao gồm chuẩn ngoại ngữ tiếng Anh dành cho các sinh viên
chương trình Dạy và học bằng tiếng Anh, Tiên tiến.
Chuẩn ngoại ngữ tiếng Anh của cả chương trình, là điều kiện trúng tuyển vào trường và là
chuẩn ngoại ngữ tốt nghiệp. Cụ thể như sau:
IELTS
Academic
PTE
Academic
TOEFL iBT
TOEFL iBT 2026
(Overall Score)
TOEIC (*)
Nghe-Đọc Nói-Viết
6,0 52 79 4 730 280
(*) Áp dụng từ khoá 2021 về sau.
Lưu ý: Không sử dụng chứng chỉ ngoại ngữ TOEFL iBT Home Edition.
Sinh viên phải có chứng chỉ ngoại ngữ quốc tế phù hợp và còn trong thời hạn hợp lệ để
được xét đạt chuẩn. Hạn của chứng chỉ tính đến thời điểm xét.

</details>

<details><summary>Source `HCMUT_UNGXU3408_QD_Dieu_1` — Điều 1. Ban hành kèm theo Quyết định này “Quy định Quy tắc ứng xử tại Trường</summary>

Điều 1. Ban hành kèm theo Quyết định này “Quy định Quy tắc ứng xử tại Trường
Đại học Bách khoa – Đại học Quốc gia Thành phố Hồ Chí Minh”.

</details>


---

## 5. `5107af110e10d9fa201742c0`

**Question:** Theo Quy định gia hạn học phí của Trường Đại học Bách khoa, người học phải nộp đơn đăng ký gia hạn trước thời điểm kết thúc thời gian nộp học phí ít nhất bao nhiêu ngày làm việc?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Ít nhất 05 ngày làm việc.

**Reference evidence:**
- `HCMUT_HOCPHI2800_Dieu_7`: điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc.

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Quy định gia hạn học phí, người học phải nộp đơn đăng ký gia hạn trước thời điểm kết thúc học phí ít nhất 05 ngày làm việc.

**Candidate citations:** `HCMUT_HOCPHI2800_Dieu_7`

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_7` — Điều 7. Quy trình gia hạn thời gian nộp học phí</summary>

Điều 7. Quy trình gia hạn thời gian nộp học phí
Người học và các đơn vị liên quan thực hiện quy trình gồm các bước sau:
Bước 1: Người học nộp đơn đăng ký gia hạn thời gian nộp học phí về Phòng Công
tác sinh viên, kèm các minh chứng cần thiết. Thời gian đăng ký gia hạn phải trước thời
điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc. (Phụ lục 1)
Bước 2: Phòng Công tác sinh viên tổng hợp, tổ chức hội đồng xét duyệt và trình
Ban Giám hiệu phê duyệt.
Bước 3: Phòng Công tác sinh viên thông báo kết quả cho người học , thực hiện gia
hạn thời gian nộp học phí, đồng thời thông báo kết quả cho Phòng Kế hoạch - Tài chính để
theo dõi công nợ của người học.
Bước 4: Người học thực hiện nộp học phí sau khi hết thời gian gia hạn.
Bước 5: Phòng Kế hoạch - Tài chính gửi kết quả theo dõi công nợ của người học
được xét gia hạn về Phòng Công tác sinh viên sau khi kết thúc thời gian nộp học phí ở học
kỳ kế tiếp.
Bước 6: Phòng Công tác sinh viên ra quyết định liên quan đến nợ học phí, xử lý học
vụ (đối với người học không hoàn thành nộp học phí).

</details>


---

## 6. `530b165068a670f7d575355a`

**Question:** Người học muốn xin gia hạn thời gian nộp học phí thì nộp đơn đăng ký về phòng nào, và phòng đó giữ những chức danh nào trong Hội đồng xét hồ sơ xin gia hạn?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Nộp về Phòng Công tác sinh viên (Điều 7, Bước 1). Trong Hội đồng xét hồ sơ (Điều 8 khoản 1), Trưởng Phòng Công tác sinh viên là Phó Chủ tịch Hội đồng và Phó Trưởng phòng Công tác sinh viên là thư ký.

**Reference evidence:**
- `HCMUT_HOCPHI2800_Dieu_7`: Bước 1: Người học nộp đơn đăng ký gia hạn thời gian nộp học phí về Phòng Công
tác sinh viên
- `HCMUT_HOCPHI2800_Dieu_8`: Trưởng Phòng
Công tác sinh viên là Phó Chủ tịch Hội đồng
- `HCMUT_HOCPHI2800_Dieu_8`: Phó Trưởng phòng Công tác sinh viên là thư ký

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Điều 7 của Quy định gia hạn thời gian nộp học phí, người học phải nộp đơn về Phòng Công tác sinh viên. Về việc giữ các chức danh trong Hội đồng xét hồ sơ, theo Điều 8:
> - Phó Hiệu trưởng là Chủ tịch Hội đồng.
> - Trưởng Phòng Công tác sinh viên là Phó Chủ tịch Hội đồng.
> - Trưởng Phòng Kế hoạch - Tài chính là ủy viên.
> - Trưởng Phòng Đào tạo là ủy viên.
> - Phó Trưởng phòng Công tác sinh viên là thư ký.

**Candidate citations:** `HCMUT_HOCPHI2800_Dieu_7`, `HCMUT_HOCPHI2800_Dieu_8`

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_7` — Điều 7. Quy trình gia hạn thời gian nộp học phí</summary>

Điều 7. Quy trình gia hạn thời gian nộp học phí
Người học và các đơn vị liên quan thực hiện quy trình gồm các bước sau:
Bước 1: Người học nộp đơn đăng ký gia hạn thời gian nộp học phí về Phòng Công
tác sinh viên, kèm các minh chứng cần thiết. Thời gian đăng ký gia hạn phải trước thời
điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc. (Phụ lục 1)
Bước 2: Phòng Công tác sinh viên tổng hợp, tổ chức hội đồng xét duyệt và trình
Ban Giám hiệu phê duyệt.
Bước 3: Phòng Công tác sinh viên thông báo kết quả cho người học , thực hiện gia
hạn thời gian nộp học phí, đồng thời thông báo kết quả cho Phòng Kế hoạch - Tài chính để
theo dõi công nợ của người học.
Bước 4: Người học thực hiện nộp học phí sau khi hết thời gian gia hạn.
Bước 5: Phòng Kế hoạch - Tài chính gửi kết quả theo dõi công nợ của người học
được xét gia hạn về Phòng Công tác sinh viên sau khi kết thúc thời gian nộp học phí ở học
kỳ kế tiếp.
Bước 6: Phòng Công tác sinh viên ra quyết định liên quan đến nợ học phí, xử lý học
vụ (đối với người học không hoàn thành nộp học phí).

</details>

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_8` — Điều 8. Quy trình xét hồ sơ</summary>

Điều 8. Quy trình xét hồ sơ
1. Trường ban hành quyết định thành lập Hội đồng xét hồ sơ xin gia hạn thời gian
nộp học phí, bao gồm 5 thành viên: Phó Hiệu trưởng là Chủ tịch Hội đồng; Trưởng Phòng
Công tác sinh viên là Phó Chủ tịch Hội đồng; Trưởng Phòng Kế hoạch – Tài chính là ủy
viên; Trưởng Phòng Đào tạo là ủy viên; Phó Trưởng phòng Công tác sinh viên là thư ký.
2. Hội đồng thực hiện xét hồ sơ dựa trên các tiêu chuẩn xét gia hạn thời gian nộp
học phí quy định tại Điều 4.
Chương V
TỔ CHỨC THỰC HIỆN

</details>


---

## 7. `5586c9fbf0771ea0e2a91860`

**Question:** Theo Phụ lục 1 được thay thế bởi Quyết định 2749/QĐ-ĐHBK, kết quả kiểm tra tiếng Anh theo định dạng TOEIC vào cuối học kỳ 1 năm nhất được dùng để làm gì, và có được dùng nhiều lần không?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Được dùng để xét miễn các học phần Anh văn 1, 2, 3, 4 tương ứng theo thang điểm quy đổi tại tiểu mục 3.1 mục 3 của Phụ lục; việc xét miễn này chỉ thực hiện một lần duy nhất (không dùng lại nhiều lần).

**Reference evidence:**
- `HCMUT_HVDT2749_PhuLuc_1`: Vào cuối học kỳ 1 năm nhất, Nhà trường tổ chức thêm một kỳ kiểm tra trình độ tiếng Anh
đầu vào theo định dạng TOEIC
- `HCMUT_HVDT2749_PhuLuc_1`: Kết quả kiểm tra này được sử dụng để xét miễn một lần duy nhất các học phần Anh văn 1,
2, 3, 4 tương ứng theo thang điểm quy đổi tại bảng quy đổi tại tiểu mục 3.1 mục 3 của Phụ

**Candidate behaviour:** clarified

**Candidate answer:**

> Theo Quyết định 2749/QĐ-ĐHBK, có quy định cụ thể nào về việc sử dụng kết quả kiểm tra tiếng Anh TOEIC cho mục đích gì trong chương trình học?

<details><summary>Source `HCMUT_HVDT2749_PhuLuc_1` — PHỤ LỤC 1. QUY ĐỊNH VỀ CHUẨN NGOẠI NGỮ</summary>

PHỤ LỤC 1. QUY ĐỊNH VỀ CHUẨN NGOẠI NGỮ
(Ban hành kèm theo Quyết định số: /QĐ-ĐHBK, ngày tháng năm 2026
của Hiệu trưởng trường Đại học Bách khoa – ĐHQG-HCM)
A. DÀNH CHO CHƯƠNG TRÌNH GIẢNG DẠY BẰNG TIẾNG VIỆT
Các quy định chuẩn ngoại ngữ sau đây dành cho các sinh viên chương trình đào tạo giảng
dạy bằng tiếng Việt. Các sinh viên tiêu chuẩn chương trình giảng dạy bằng tiếng Việt là lưu
học sinh Lào, Campuchia được miễn các chuẩn ngoại ngữ từng năm và chuẩn ngoại ngữ
tốt nghiệp, nhưng không được miễn các học phần tiếng Anh trong chương trình đào tạo.
1. Chuẩn ngoại ngữ từng năm học
Sinh viên phải đạt chuẩn ngoại ngữ từng năm theo quy định để đăng ký môn học cho năm
tiếp theo. Chuẩn ngoại ngữ từng năm được quy định cụ thể như sau:
a) Chuẩn ngoại ngữ tiếng Anh từng năm dành cho sinh viên chương trình tiêu chuẩn, vừa
làm vừa học, Bằng 2
- Từ Khóa 2023 về trước
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất Anh văn cơ bản 2 Học phần ngoài chương trình đào tạo
Năm thứ hai Anh văn 1 Hết năm nhất
Năm thứ ba Anh văn 1, 2, 3 Hết năm hai
Năm thứ tư Anh văn 1, 2, 3, 4 Hết năm ba
- Từ Khóa 2024 về sau (áp dụng từ học kỳ 1 năm học 2026-2027)
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất Anh văn cơ bản 2 Học phần ngoài chương trình đào tạo
Năm thứ hai Anh văn 1 Hết năm nhất
Năm thứ ba, tư Anh văn 1, 2, 3, 4 Hết năm hai
Lưu ý: Điều kiện tiên quyết của các học phần Anh văn 1, 2, 3 và 4 tương ứng là Anh văn
cơ bản 2, Anh văn 1, 2 và 3.
Chuẩn ngoại ngữ tiếng Anh từng năm không áp dụng đối với sinh viên chương trình định
hướng Nhật Bản, chương trình đào tạo kỹ sư chất lượng cao tại Việt Nam (PFIEV).
b) Chuẩn ngoại ngữ tiếng Pháp từng năm dành cho sinh viên Chương trình đào tạo kỹ sư
chất lượng cao tại Việt Nam (PFIEV) từ khóa 2024 về sau, áp dụng từ học kỳ 1 năm học
2026-2027.
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất
Năm thứ hai Pháp văn 1 Hết năm nhất
Năm thứ ba Pháp văn 1, 2, 3, 4 Hết năm hai
Năm thứ tư Pháp văn 1, 2, 3, 4, 5, 6 Hết năm ba
c) Chuẩn ngoại ngữ tiếng Nhật từng năm dành cho sinh viên Chương trình định hướng
Nhật Bản từ khóa 2026 về sau:
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất
Năm thứ hai Tiếng Nhật 1, 2 Hết năm nhất
Năm thứ ba Tiếng Nhật 1, 2, 3, 4 Hết năm hai
Năm thứ tư Tiếng Nhật 1, 2, 3, 4, 5, 6 Hết năm ba
2. Chuẩn ngoại ngữ tốt nghiệp
Chuẩn ngoại ngữ tốt nghiệp được quy định theo chứng chỉ ngoại ngữ quốc tế như sau:
Chương trình,
hình thức đào tạo
Chuẩn ngoại ngữ tốt nghiệp
Tiếng Anh (tương đương
TOEIC) Khác
Nghe-Đọc Nói-Viết
Chương trình tiêu chuẩn 500 (khoá 2018 v ề
trước)
550 (khoá 2019)
600 (từ khoá 2020)
200
Chương trình Định hướng Nhật
Bản Không áp dụng JLPT N3 (tiếng Nhật)
Chương trình tài năng 600 (khoá 2018 v ề
trước)
650 (khoá 2019)
700 (từ khoá 2020)
245
Chương trình đào tạo kỹ sư chất
lượng cao t ại Vi ệt Nam
(PFIEV)
600 (khoá 2018 v ề
trước)
650 (khoá 2019)
700 (từ khoá 2020)
245
DELF B1
TCF B1
(tiếng Pháp)
Vừa làm vừa học,
Đào tạo từ xa
400 (khoá 2017 v ề
trước)
450 (khoá 2018)
500 (khoá 2019)
600 (từ khoá 2020)
200
(từ khoá
2021)
Chính quy Bằng thứ hai Học chương trình đào tạo chính quy của khóa nào thì áp
dụng chuẩn của khóa đó.
Các chứng chỉ tiếng Anh bao gồm đầy đủ các kỹ năng Nghe – Đọc – Nói – Viết để xét
chuẩn tốt nghi ệp g ồm: IELTS, TOEFL iBT (không s ử dụng ch ứng ch ỉ TOEFL iBT
Home Edition), PET, FCE, CAE, PTE Academic, Linguaskill, APTIS ESOL. Khi đ ạt
mức điểm tương đương TOEIC theo bảng quy đ ổi tại mục 3.1 của Phụ lục này, sinh
viên được xét đạt chuẩn ngoại ngữ tốt nghiệp cho tất cả các kỹ năng.
Tạm thời cho phép sinh viên s ử dụng kết quả các kỳ kiểm tra k ỹ năng Nói – Viết do
Trung tâm Ngoại ngữ Trường Đại học Bách khoa tổ chức để xét tốt nghiệp.
Khi xét điều kiện đăng ký học phần Khóa luận tốt nghiệp, cho phép áp dụng chuẩn ngoại
ngữ tốt nghiệp tiếng Anh ch ỉ đối với kỹ năng Nghe – Đọc, Chương trình Định hướng
Nhật Bản là JLPT N3 (tiếng Nhật).
3. Quy đổi các bằng cấp và chứng chỉ ngoại ngữ
3.1. Các chứng chỉ tiếng Anh quốc tế được quy đổi tương đương như sau:
Các chứng chỉ tiếng Anh Quốc tế Các học phần Anh văn
TOEIC
Listening
&
Reading
TOEFL
iBT
TOEFL
iBT 2026
(Overall
Score)
IELTS PET FCE CAE PTE Academic Lingua -skill APTIS ESOL VSTEP VEPT Cơ bản 1 2 3 4
400 40 2.5 - - - - - - - - Đạt - - - -
450 49 3 - - - - - 140 - 4.0 43 Đạt Đạt - - -
500 54 3 4.0 Grade C - - - 143 - 4.5 51 Đạt Đạt Đạt - -
550 59 3.5 4.5 Grade B - - - 146 - 5.0 59 Đạt Đạt Đạt Đạt -
600 64 3.5 5.0 Grade B - - 41 149 B1 5.5 67 Đạt Đạt Đạt Đạt Đạt
650 70 3.5 5.0 Grade A - - 43 152 - X X Đạt Đạt Đạt Đạt Đạt
700 79 4 5.5 Grade A - - 45 155 B1 X X Đạt Đạt Đạt Đạt Đạt
785 85 4 5.5 X
Grade
C,
Grade
B,
Grade
A
Level
B2
Grade
C,
Grade
B,
Grade
A
48 160 B2 X X Đạt Đạt Đạt Đạt Đạt
Lưu ý: Không sử dụng chứng chỉ ngoại ngữ TOEFL iBT Home Edition
Thời hạn công nhận chứng chỉ: trong thời hạn 2 năm tính từ ngày cấp cho đến ngày đăng
ký xét đạt chuẩn.
Bằng tốt nghiệp bậc đại học trở lên ngành/chuyên ngành tiếng Anh được xét miễn các học
phần Anh văn 1, 2, 3, 4.
3.2. Các chứng chỉ tiếng Pháp được quy đổi tương đương như sau:
Các chứng chỉ tiếng Pháp Các học phần tiếng Pháp
Tú tài
Pháp
Tốt nghiệp phổ thông
chương trình Song ngữ và
tăng cường tiếng Pháp
DELF TCF 1 2 3 4 5 6 7*
X X A1 100-199 Đạt
X X A2 200-299 Đạt Đạt
B1,
B2
300-399 Đạt Đạt Đạt Đạt Đạt Đạt Đạt
*Pháp văn 7: áp dụng cho sinh viên Khoá 2018 về trước.
3.3. Các chứng chỉ tiếng Nhật được quy đổi tương đương như sau:
Sinh viên đã có chứng chỉ tiếng Nhật JLPT trong vòng 12 tháng, được xem xét miễn một
số học phần tiếng Nhật như sau:
a) Đối với Khóa 2023 về trước:
Chứng chỉ Được xét miễn Ghi chú
JLPT N1 Tiếng Nhật 1, 2, 3, 4, 5, 6
JLPT N2 Tiếng Nhật 1, 2, 3
JLPT N3 Tiếng Nhật 1, 2
b) Đối với Khóa 2024 về sau:
Chứng chỉ Được xét miễn Ghi chú
JLPT N1 Tiếng Nhật 1, 2, 3, 4, 5, 6
JLPT N2 Tiếng Nhật 1, 2, 3, 4
JLPT N3 Tiếng Nhật 1, 2, 3
4. Nguyên tắc xét miễn các học phần tiếng Anh và các chuẩn ngoại ngữ
4.1. Ngay khi nhập học
Sau khi nhập học, Nhà trường tổ chức một kỳ thi xếp trình độ tiếng Anh dành cho sinh viên
chương trình giảng dạy bằng tiếng Việt vừa trúng tuyển. Căn cứ vào kết quả kỳ thi, sinh
viên được phân lớp hoặc đăng ký các học phần Anh văn 1, 2, 3, 4 tương ứng. Kết quả thi
xếp trình độ tiếng Anh chỉ được sử dụng để xét tạm đạt điều kiện tiên quyết khi đăng ký
các học phần Anh văn trong học kỳ 1 và học kỳ 2 của năm nhất; không có giá trị xét miễn
bất kỳ học phần Anh văn nào trong chương trình đào tạo.
Vào cuối học kỳ 1 năm nhất, Nhà trường tổ chức thêm một kỳ kiểm tra trình độ tiếng Anh
đầu vào theo định dạng TOEIC dành cho sinh viên chương trình giảng dạy bằng tiếng Việt.
Kết quả kiểm tra này được sử dụng để xét miễn một lần duy nhất các học phần Anh văn 1,
2, 3, 4 tương ứng theo thang điểm quy đổi tại bảng quy đổi tại tiểu mục 3.1 mục 3 của Phụ
lục này. Đối với các học phần không được miễn, sinh viên phải đăng ký học theo quy định.
Sinh viên vừa trúng tuyển, đã có bằng tốt nghiệp từ bậc đại học ngành/chuyên ngành tiếng
Anh, trong học kỳ đầu tiên tính từ lúc trúng tuyển, được đăng ký xét miễn các học phần
Anh văn 1, 2, 3 và 4.
4.2. Trong quá trình học
Trong quá trình học, sinh viên có thể sử dụng chứng chỉ tiếng Anh quốc tế còn thời hạn phù
hợp để được xét miễn các học phần Anh văn 1, 2, 3, 4 (theo quy định tại mục 3.1 của Phụ
lục này) và đồng thời được xét đạt chuẩn ngoại ngữ tốt nghiệp (theo quy định tại mục 2 của
Phụ lục này).
B. DÀNH CHO CHƯƠNG TRÌNH GIẢNG DẠY BẰNG TIẾNG ANH
Quy định chuẩn ngoại ngữ này bao gồm chuẩn ngoại ngữ tiếng Anh dành cho các sinh viên
chương trình Dạy và học bằng tiếng Anh, Tiên tiến.
Chuẩn ngoại ngữ tiếng Anh của cả chương trình, là điều kiện trúng tuyển vào trường và là
chuẩn ngoại ngữ tốt nghiệp. Cụ thể như sau:
IELTS
Academic
PTE
Academic
TOEFL iBT
TOEFL iBT 2026
(Overall Score)
TOEIC (*)
Nghe-Đọc Nói-Viết
6,0 52 79 4 730 280
(*) Áp dụng từ khoá 2021 về sau.
Lưu ý: Không sử dụng chứng chỉ ngoại ngữ TOEFL iBT Home Edition.
Sinh viên phải có chứng chỉ ngoại ngữ quốc tế phù hợp và còn trong thời hạn hợp lệ để
được xét đạt chuẩn. Hạn của chứng chỉ tính đến thời điểm xét.

</details>


---

## 8. `5d30469e8d0c14bf4e353095`

**Question:** Việc gia hạn thời gian nộp học phí theo quy định của Trường Đại học Bách khoa áp dụng cho những loại học kỳ nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Chỉ học kỳ chính; không áp dụng cho học kỳ dự thính và học kỳ hè.

**Reference evidence:**
- `HCMUT_HOCPHI2800_Dieu_5`: không áp dụng cho học kỳ dự thính, học kỳ hè

**Candidate behaviour:** answered

**Candidate answer:**

> Theo quy định của Trường Đại học Bách khoa - ĐHQG-HCM, việc gia hạn thời gian nộp học phí được áp dụng cho các kỳ học theo lịch trình cố định (thường là semester-based) của trường, không có sự thay đổi tùy theo nhu cầu cá nhân. Người học sẽ phải tuân thủ thời hạn quy định trong từng khóa học.

**Candidate citations:** `HCMUT_QCDT_01_Dieu_01`

**Unknown citation ids:** ['HCMUT_QCDT_01_Dieu_01']

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_5` — Điều 5. Quyền lợi của người học khi được gia hạn thời gian nộp học phí</summary>

Điều 5. Quyền lợi của người học khi được gia hạn thời gian nộp học phí
1. Người học được xét đơn xin gia hạn thời gian nộp học phí trong các học kỳ chính
(không áp dụng cho học kỳ dự thính, học kỳ hè).
2. Người học không được gia hạn thời gian nộp học phí trong 02 học kỳ chính liên
tiếp nếu chưa hoàn thành nộp học phí của học kỳ được xét gia hạn trong thời gian quy định.
3. Người học được tiếp tục hoàn thành chương trình đào tạo trong học kỳ được xét
gia hạn thời gian nộp học phí sau khi Trường ban hành quyết định gia hạn thời gian nộp
học phí.

</details>


---

## 9. `632ff2b2da56d54a87514910`

**Question:** Sinh viên bắt buộc phải đeo thẻ sinh viên trong phạm vi nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Khi ở trong khuôn viên Trường.

**Reference evidence:**
- `HCMUT_NOIQUY1924_Dieu_3`: sinh viên phải đeo thẻ sinh viên khi ở trong khuôn viên Trường

**Candidate behaviour:** answered

**Candidate answer:**

> Theo các văn bản quy chế đã tra cứu, người học phải đeo thẻ sinh viên khi ở trong khuôn viên trường. Điều 9 của Quy tắc chung và Điều 3 của Nội quy học đường đều khẳng định: 'Đeo thẻ sinh viên: sinh viên phải đeo thẻ sinh viên khi ở trong khuôn viên Trường.'

**Candidate citations:** `HCMUT_UNGXU3408_Dieu_9`, `HCMUT_NOIQUY1924_Dieu_5`

<details><summary>Source `HCMUT_NOIQUY1924_Dieu_3` — Điều 3. Quy định về tác phong, ý thức, cách thức giao tiếp và thái độ ứng xử của</summary>

Điều 3. Quy định về tác phong, ý thức, cách thức giao tiếp và thái độ ứng xử của
sinh viên
1. Đeo thẻ sinh viên: sinh viên phải đeo thẻ sinh viên khi ở trong khuôn viên Trường.
2. Trang phục: Trang phục lịch sự, gọn gàng phù hợp với văn hóa học đường khi
vào khuôn viên trường. Khi tham gia các ngày lễ (khai giảng, tốt nghiệp, …), hội
nghị, hội thảo … sinh vi ên phải mặc lễ phục trang trọng, lịch sự theo quy định
của sự kiện.
3. Đầu tóc gọn gàng, nghiêm túc, phù hợp với môi trường giáo dục; không xăm hình
gây phản cảm, không phù hợp với thuần phong, mỹ tục và văn hóa dân tộc.
4. Lễ phép, tôn trọng cán bộ viên chức và người lao động của Nhà trường; lịch sự,
hoà nhã và thân thiện với mọi người.
5. Sinh viên phải đi học đúng giờ quy định, có thái độ nghiêm túc trong học tập và
thi cử; tuân thủ, chấp hành đầy đủ nội quy, quy định về an toàn và hướng dẫn của
giảng viên trong các giờ học thực hành, thí nghiệm.
6. Thực hiện nếp sống văn minh, xếp hàng ngay ngắn, trật tự khi đi thang máy, liên
hệ công việc và sử dụng các dịch vụ của Nhà trường.

</details>

<details><summary>Source `HCMUT_NOIQUY1924_Dieu_5` — Điều 5. Những hành vi sinh viên KHÔNG được phép thực hiện</summary>

Điều 5. Những hành vi sinh viên KHÔNG được phép thực hiện
1. Gian lận trong học tập, kiểm tra, thi cử.
2. Cho người khác mượn thẻ sinh viên hoặc mượn thẻ sinh viên của người khác để
sử dụng, sử dụng thẻ sinh viên sai mục đích.
3. Đi xe máy, xe đạp trong khuôn viên Trường.
4. Dẫm, nằm, ngồi lên cỏ ở các khu vực có biển cấm trong khuôn viên Trường; hái
hoa, bẻ cành cây trong khuôn viên Trường; chơi thể thao tại những địa điểm ngoài
khu vực sân thể dục thể thao theo quy định của Trường.
5. Tổ chức hoặc tham gia cờ bạc dưới mọi hình thức trong khuôn viên Trường.
6. Mang theo hoặc sử dụng các chất cháy, chất gây nổ; các loại vũ khí, hung khí vào
Trường.
7. Mang đồ ăn vào lớp học, gi ảng đường và hội trường. Mang theo động vật, thú
nuôi vào Trường.
8. Sử dụng, mua bán, tàng trữ các chất ma túy, các chất kích thích dưới mọi hình
thức; uống rượu, bia và hút thuốc lá trong khuôn viên Trường (bao gồm thuốc lá
điện tử); say rượu bia khi đến Trường.
9. Tự ý viết, dán quảng cáo, thông báo trong khuôn viên Trường; viết, vẽ, sơn bậy,
bôi xóa, làm bẩn, làm mất vệ sinh và làm hư hỏng các trang thiết bị học tập, máy
móc, dụng cụ thực hành thí nghiệm, cơ sở vật chất … của Trường.
10. Tự ý sử dụng tài sản của Nhà trường; tự ý di chuyển các trang thiết bị, tài sản ra
khỏi vị trí đã sắp xếp, lắp đặt trong phòng và trong khuôn viên Trường. Đứng lên
bàn ghế, leo trèo hoặc ngồi trên lan can, khung cửa sổ và trên bàn học, bàn giáo
viên.
11. Lưu hành, tuyên truyền các ấn phẩm, tài liệu, thông tin phản động, phim ảnh
không lành mạnh và các tài liệu cấm khác theo quy định của Nhà nước.
12. Gây bè phái, gây mất đoàn kết nội bộ trong tập thể lớp và trong Trường. Gây gổ,
đánh nhau hoặc kích động đánh nhau, tổ chức băng nhóm, tụ tập gây mất an ninh,
trật tự dưới mọi hình thức.
13. Không lợi dụng mạng xã hội nhằm mục đích xâm phạm đời tư, công việc và học
tập của cá nhân, cơ quan, tổ chức, đoàn thể; có ý thức bảo vệ, xây dựng hình ảnh,
thương hiệu của Nhà trường trên không gian mạng.
14. Không sử dụng từ ngữ gây thù hận, kích động bạo lực, phân biệt vùng miền, giới
tính, tôn giáo, dân tộc.
15. Tổ chức, tham gia, truyền bá các hoạt động mê tín dị đoan, các hoạt động tôn
giáo và các hành vi vi phạm đạo đức khác trong và ngoài khuôn viên Trường.
16. Tổ chức, tham gia các hoạt động chính trị trái pháp luật trong và ngoài khuôn
viên Trường.
17. Tham gia các hoạt động tập thể mang danh nghĩa Nhà trường khi chưa được Nhà
trường cho phép.
18. Có hành vi xúc phạm nhân phẩm, danh dự, xâm phạm tới thân thể, sức khỏe và
tài sản của cán bộ, giảng viên, người lao động và sinh viên khác của Nhà trường.
19. Tổ chức hoặc tham gia các hoạt động vi phạm pháp luật khác.

</details>

<details><summary>Source `HCMUT_UNGXU3408_Dieu_9` — Điều 9. Quy tắc chung</summary>

Điều 9. Quy tắc chung
1. Chấp hành nhiệm vụ của người học tại các quy chế , quy định của Bộ Giáo dục và
Đào tạo, Nội quy học đường Trường Đại học Bách khoa – ĐHQG-HCM.
2. Tích cực rèn luyện phẩm chất đạo đức, có lối sống lành mạnh, giản dị, khiêm tốn;
trung thực, nghiêm túc trong học tập, nghiên cứu khoa học và rèn luyện, không gian
lận trong học tập và thi cử với mọi hình thức, tránh những việc gây ảnh hưởng xấu
hình ảnh, uy tín của Nhà trường.
3. Tự giác, chủ động trong quá trình học tập, nghiên cứu khoa học, tích cực tham gia
các hoạt động giáo dục, đào tạo và các chương trình do Nhà trường tổ chức để nâng
cao kiến thức chuyên môn; các hoạt động xã hội, các hoạt động phục vụ cộng đồng
để rèn luyện các kỹ năng mềm, khả năng thích ứng với môi trường làm việc, rèn
luyện kỹ năng sống, học tập và hội nhập quốc tế.
4. Khi tham gia các hoạt động, sự kiện, hội nghị,… người học phải đến trước giờ khai
mạc ít nhất 5 phút. Nếu không thể tham gia hoạt động, sự kiện hoặc đến muộn,
người học phải báo cáo sớm với Ban Tổ chức hay người phụ trách (trưởng nhóm,
lớp trưởng, v.v.).
5. Người học đến trường phải mặc trang phục giản dị, kín đáo, gọn gàng, lịch sự, phù
hợp với môi trường học đường.
6. Người học đeo thẻ sinh viên/ học viên khi ở trong khuôn viên Trường. Tuyệt đối
không cho người khác mượn hoặc mượn thẻ sinh viên/ học viên của người khác để
sử dụng; không được cầm cố thẻ sinh viên/ học viên.
7. Việc ghi âm, ghi hình, chụp ảnh trong quá trình học tập, làm việc phải tuân thủ quy
định của Nhà trường, bảo đảm tôn trọng quyền riêng tư và không làm ảnh hưởng
đến hoạt động giảng dạy, học tập; không phát tán, sử d ụng trái phép các nội dung
đã ghi nhận.
8. Có trách nhiệm phản ánh, tố giác các hành vi vi phạm quy định, vi phạm đạo đức
trong Nhà trường thông qua các kênh tiếp nhận thông tin theo quy định.

</details>


---

## 10. `6ba3c86cf40e8bfd70d1f77f`

**Question:** Theo luật giao thông đường bộ, sinh viên đi xe máy vào khuôn viên trường mà không đội mũ bảo hiểm thì bị phạt bao nhiêu tiền?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Corpus chỉ cấm đi xe máy trong khuôn viên Trường (Nội quy học đường) và không nêu mức phạt tiền theo pháp luật giao thông đường bộ.

**Candidate behaviour:** refused

**Candidate answer:**

> Lý do: Câu hỏi liên quan đến luật giao thông đường bộ nhưng nội dung không nằm trong cơ sở dữ liệu quy chế học vụ và văn bản đã tra cứu. Không có quy định cụ thể về khoản phạt vi phạm này cho sinh viên tại trường.


---

## 11. `750a9c12ce29787f3845bd4d`

**Question:** Hiện kim khen thưởng cho một nhóm SV từ hai người trở lên được tính so với khen thưởng dành cho cá nhân như thế nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Bằng 2 lần khen thưởng dành cho cá nhân.

**Reference evidence:**
- `HCMUT_VINHDANH658_Dieu_11`: Đối với nhóm SV (từ 02 SV trở lên) thì hiện kim khen thưởng cho nhóm SV có
- `HCMUT_VINHDANH658_Dieu_11`: giá trị bằng 02 lần so với hiện kim khen thưởng dành cho cá nhân

**Candidate behaviour:** answered

**Candidate answer:**

> Hiện kim khen thưởng cho một nhóm SV từ hai người trở lên được tính là 02 lần so với hiện kim khen thưởng dành cho cá nhân. Điều này quy định trong clause 4c của Điều 11, quy định rằng đối với các nhóm SV (từ 02 SV trở lên), giá trị khen thưởng cho nhóm SV có giá trị bằng 02 lần so với hiện kim khen thưởng dành cho cá nhân.

**Candidate citations:** `HCMUT_VINHDANH658_Dieu_11`

<details><summary>Source `HCMUT_VINHDANH658_Dieu_11` — Điều 11. Định mức hỗ trợ và vinh danh</summary>

Điều 11. Định mức hỗ trợ và vinh danh
1. Định mức hỗ trợ
a. Mức hỗ trợ được căn cứ theo qui định hiện hành về hỗ trợ phụ cấp, công tác phí,
phụ cấp lưu trú theo quy định của nhà trường.
b. Mức hỗ trợ này không bao gồm chi phí thực hiện đề tài; hoặc không áp dụng cho
các đề tài đã được duyệt kinh phí thực hiện đề tài trong đó bao gồm chi phí tham gia, chi
phí di chuyển và chi phí triển khai đề tài.
c. Đối với đề tài/ sản phẩm dự thi có từ 02 GV hướng d ẫn: chỉ xem xét hỗ trợ 01
GV đại diện tham gia.
d. Đối với đề tài/ sản phẩm dự thi có từ 03 SV thực hiện trở lên: chỉ xem xét hỗ trợ
tối đa 02 SV đại diện tham gia.
2. Đối với GV đạt chuẩn vinh danh
a. Được nhận Giấy khen Hiệu trưởng.
b. Thành tích được quy đổi giờ Nghiên cứu khoa học và chuyển giao công nghệ căn
cứ trên nguyên tắc: chỉ quy đổi một lần và lấy kết quả cao nhất để quy đổi.
3. Định mức khen thưởng vinh danh cho SV, nhóm SV
a. Tất cả SV được nhận giấy khen Hiệu trưởng và khen thưởng hiện kim.
b. Hiện kim (HK) được căn cứ vào phân loại mức độ cuộc thi / giải thưởng (Kpl)
quy định tại Điều 5 của Quy chế này và hệ số khen thưởng (Khs) do Hiệu trưởng quyết
định mỗi năm: HK = Kpl x Khs.
c. Bảng định mức hệ số khen thưởng (dành cho cá nhân):
TT Phân loại mức độ cuộc thi, giải thưởng
Hệ số khen thưởng (Kpl)
Giải nhất
/ TOP3
Giải nhì /
TOP5
Giải ba /
TOP10
Giải KK /
TOP20
1 Loại I 30 23 19 15
2 Loại II 22 15 11 7
3 Loại III 16 9 5 1
4 Loại IV 6 3 1 0
Lưu ý: Đối với các giải thưởng không có cơ cấu Nhất – Nhì – Ba – KK thì sẽ dùng
cơ cấu TOP 3 – TOP 5 – TOP 10 – TOP 20 để ghi nhận thành tích.
d. Đối với nhóm SV (từ 02 SV trở lên) thì hiện kim khen thưởng cho nhóm SV có
giá trị bằng 02 lần so với hiện kim khen thưởng dành cho cá nhân.
e. Đối với các cuộc thi có giải thưởng đồng đội thì hiện kim khen thưởng cho tập
thể đạt giải có giá trị bằng 03 lần so với hiện kim khen thưởng dành cho cá nhân.
f. Đối với các đơn vị t ổ chức khen thưởng riêng cho các SV, nhóm SV (ngoài lễ
vinh danh của trường tổ chức), hiện kim khen thưởng quy định như sau:
+ Nếu kinh phí khen thưởng từ nguồn kinh phí của trường thì phải đề xuất và
được Hiệu trưởng phê duyệt: HKriêng = k x HK (với hệ số k do đơn vị đề xuất).
+ Nếu kinh phí khen thưởng từ nguồn vận động tài trợ t hì đơn vị toàn quyền
quyết định.
4. Đối với các trường hợp đặc biệt : sẽ do Hội đồng cố vấn xem xét và đề xuất
Hiệu trưởng quyết định mức khen thưởng.

</details>


---

## 12. `757c67132b8641fbfae43cf5`

**Question:** Khi có quyết định xử lý biến động người học như đình chỉ học tập hoặc buộc thôi học, Phòng Đào tạo phải gửi quyết định đi đâu?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Gửi đến Khoa.

**Reference evidence:**
- `HCMUT_GVCN2977_Dieu_8`: Gửi quyết định mỗi khi có xử lý biến động người học
- `HCMUT_GVCN2977_Dieu_8`: nghỉ học tạm thời đến Khoa

**Candidate behaviour:** answered

**Candidate answer:**

> Phòng Đào tạo phải gửi quyết định đi Khoa. Điều 8 của văn bản quy định yêu cầu: "Gửi quyết định mỗi khi có xử lý biến động người học như đình chỉ học tập, buộc thôi học".

**Candidate citations:** `HCMUT_GVCN2977_Dieu_8`

<details><summary>Source `HCMUT_GVCN2977_Dieu_8` — Điều 8. Nhiệm vụ của Phòng Đào tạo</summary>

Điều 8. Nhiệm vụ của Phòng Đào tạo
1. Tham mưu xây dựng các quy định, quy trình hoạt động của GVCN & CVHT.
2. Cung cấp tài khoản cho GVCN & CVHT, Ban Chủ nhiệm Khoa để truy cập vào
hệ thống theo dõi kết quả học tập của người học.
3. Giải đáp, cung cấp thông tin liên quan đến chương trình đào tạo , đăng ký học tập
và kết quả học tập của người học theo đề nghị cụ thể của Ban Chủ nhiệm Khoa.
4. Gửi quyết định mỗi khi có xử lý biến động người học như đình chỉ học tập, buộc
thôi học, nghỉ học tạm thời đến Khoa.
5. Phối hợp với P. TC-NS và P. CTSV tính định mức giảm giờ cho các nhiệm vụ theo
Quy định chế độ làm việc của VC&NLĐ.

</details>


---

## 13. `7a5d1a62df20b571cc8e712f`

**Question:** Đơn giá học phí mỗi tín chỉ năm học 2026–2027 cho sinh viên đại học chính quy là bao nhiêu?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Corpus không có đơn giá học phí. Điều 23.1 (Quyết định 1259) chỉ nói Trường thông báo đơn giá, cách tính và thời điểm thu học phí theo từng năm hoặc theo học kỳ; thông báo đó không nằm trong corpus.

**Candidate behaviour:** refused

**Candidate answer:**

> Không tìm thấy thông tin chi tiết về đơn giá học phí trong các văn bản tra cứu. Các snippet chỉ cung cấp quy định về chuẩn kỹ năng, đánh giá học tập và ngoại ngữ.


---

## 14. `9010c0eb30c8dc5d06c1cfda`

**Question:** Sinh viên muốn phúc khảo điểm một học phần thì phải nộp đơn trong thời hạn bao nhiêu ngày kể từ ngày công bố điểm?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Corpus không quy định thủ tục hay thời hạn phúc khảo điểm học phần. Các điều khoản về đánh giá, hoãn thi và xét kết quả trong corpus không trả lời câu hỏi này; cần tra quy định riêng của nhà trường.

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Điều 7 của Quy định gia hạn thời gian nộp học phí, người học phải nộp đơn trước thời điểm kết thúc ít nhất 05 ngày làm việc. Thời gian đăng ký gia hạn là khoảng 05 ngày làm việc.

**Candidate citations:** `HCMUT_HOCPHI2800_Dieu_7`

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_7` — Điều 7. Quy trình gia hạn thời gian nộp học phí</summary>

Điều 7. Quy trình gia hạn thời gian nộp học phí
Người học và các đơn vị liên quan thực hiện quy trình gồm các bước sau:
Bước 1: Người học nộp đơn đăng ký gia hạn thời gian nộp học phí về Phòng Công
tác sinh viên, kèm các minh chứng cần thiết. Thời gian đăng ký gia hạn phải trước thời
điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc. (Phụ lục 1)
Bước 2: Phòng Công tác sinh viên tổng hợp, tổ chức hội đồng xét duyệt và trình
Ban Giám hiệu phê duyệt.
Bước 3: Phòng Công tác sinh viên thông báo kết quả cho người học , thực hiện gia
hạn thời gian nộp học phí, đồng thời thông báo kết quả cho Phòng Kế hoạch - Tài chính để
theo dõi công nợ của người học.
Bước 4: Người học thực hiện nộp học phí sau khi hết thời gian gia hạn.
Bước 5: Phòng Kế hoạch - Tài chính gửi kết quả theo dõi công nợ của người học
được xét gia hạn về Phòng Công tác sinh viên sau khi kết thúc thời gian nộp học phí ở học
kỳ kế tiếp.
Bước 6: Phòng Công tác sinh viên ra quyết định liên quan đến nợ học phí, xử lý học
vụ (đối với người học không hoàn thành nộp học phí).

</details>


---

## 15. `91fc03c4341c48a78621c095`

**Question:** Đơn giá học phí mỗi tín chỉ năm học 2026–2027 cho sinh viên đại học chính quy là bao nhiêu?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Corpus không có đơn giá học phí. Điều 23.1 (Quyết định 1259) chỉ nói Trường thông báo đơn giá, cách tính và thời điểm thu học phí theo từng năm hoặc theo học kỳ; thông báo đó không nằm trong corpus.

**Candidate behaviour:** answered

**Candidate answer:**

> Dựa trên nội dung các văn bản tra cứu, trường Đại học Bách khoa - ĐHQG-HCM quy định về chuẩn kỹ năng ứng dụng Công nghệ thông tin, đánh giá kết quả học tập và chuẩn ngoại ngữ. Tuy nhiên, thông tin cụ thể về đơn giá học phí (tiền gửi) theo từng tín chỉ mỗi năm học 2026–2027 chưa được ghi rõ trong các văn bản đã truy vấn.

**Candidate citations:** `HCMUT_HVDT1260_PhuLuc_3`

<details><summary>Source `HCMUT_HVDT1260_PhuLuc_3` — PHỤ LỤC 3. QUY ĐỊNH VỀ CÁC CHUẨN KHÁC</summary>

PHỤ LỤC 3. QUY ĐỊNH VỀ CÁC CHUẨN KHÁC
của Hiệu trưởng trường Đại học Bách khoa – ĐHQG-HCM)
A. QUY ĐỊNH VỀ CHUẨN KỸ NĂNG CÔNG NGHỆ THÔNG TIN
1. Chuẩn kỹ năng ứng dụng Công nghệ thông tin và các điều kiện ràng buộc
Từ khóa tuyển sinh năm 2021, sinh viên phải đạt chuẩn kỹ năng ứng dụng Công nghệ thông
tin cơ bản. Sinh viên phải hoàn tất chuẩn này sau năm thứ nhất để được xếp trình độ năm
thứ hai.
Đối với chứng chỉ MOS, sinh viên cần đạt yêu cầu 01 bài thi Excel trong bộ chứng chỉ
MOS. Quy định này bắt buộc đối với sinh viên chương trình Dạy và học bằng tiếng Anh,
chương trình Tiên tiến (áp dụng từ khóa 2023) và sinh viên chương trình Định hướng Nhật
Bản (áp dụng từ khóa 2024) để được đăng ký học phần Khóa luận tốt nghiệp/Đồ án tốt
nghiệp.
2. Cách thức đạt chuẩn
Nhà trường tổ chức các kỳ kiểm tra kỹ năng ứng dụng Công nghệ thông tin nội bộ, không
cấp chứng chỉ, miễn phí một lần cho toàn bộ các sinh viên chính quy trong năm thứ nhất.
Sinh viên có thể nộp các chứng chỉ Ứng dụng Công nghệ thông tin cơ bản hợp lệ hoặc
chứng chỉ quốc tế IC3 để hoàn tất chuẩn này.
Trường phối hợp với các đơn vị có trách nhiệm tổ chức các kỳ thi lấy chứng chỉ MOS cho
sinh viên. Mỗi sinh viên chính quy được miễn phí một lần thi. Sinh viên có thể nộp các
chứng chỉ MOS tương ứng để hoàn tất chuẩn này.
Sinh viên đã hoàn tất chuẩn nội bộ, trong đối đa 05 năm, được bảo lưu kết quả khi trúng
tuyển đầu vào của nhà trường hoặc chuyển sang hình thức vừa làm vừa học, đào tạo từ xa.
B. QUY ĐỊNH VỀ CHUẨN CÁC MÔN ĐẠI CƯƠNG
Chuẩn các môn đại cương từng năm áp dụng từ học kỳ 1 năm học 2026-2027 cho sinh viên
từ khóa 2024. Sinh viên phải đạt điều kiện về chuẩn các môn học đại cương theo từng năm
để được đăng ký học phần cho năm tiếp theo, cụ thể như sau:
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ hai
Hoàn thành các môn Giới thiệu ngành/Nhập môn
về kỹ thuật/Nhập môn điện toán/Nhập môn kiến
trúc để đủ điều kiện đăng ký các môn học năm 2.
Hết năm nhất
Năm thứ tư
Sinh viên trình độ năm 4 (hết năm 3): Hoàn thành
các môn trong khối kiến thức Toán và Khoa học tự
nhiên, Kiến thức quản lý/Khởi nghiệp hoặc Kiến
Hết năm ba
thức kỹ thuật ngoài ngành đối với các ngành quản
lý.
C. QUY ĐỊNH VỀ CHUẨN NGÀY CÔNG TÁC XÃ HỘI
Chuẩn ngày công tác xã hội từng năm áp dụng từ học kỳ 1 năm học 2026-2027 cho sinh
viên chính quy Bằng thứ nhất của các khóa đào tạo. Sinh viên phải đạt điều kiện về chuẩn
ngày công tác xã hội theo từng năm để được đăng ký học phần cho năm tiếp theo, cụ thể
như sau:
Chuẩn từng năm Đạt ngày CTXH (tối thiểu) Ghi chú
Năm nhất 00 ngày
Năm hai 04 ngày Hết năm nhất
Năm ba 08 ngày Hết năm hai
Năm tư / Đồ án tốt nghiệp 12 ngày Hết năm ba
Tốt nghiệp 15 ngày
D. QUY ĐỊNH CHUẨN KỸ NĂNG, ĐỀ ÁN KỸ NĂNG VÀ THỂ CHẤT
Chuẩn kỹ năng, Đề án Kỹ năng và thể chất cho sinh viên từ khóa 2025 về sau cho chương
trình Dạy và Học bằng tiếng Anh/Tiên tiến/Định hướng Nhật Bản/Chuyển tiếp quốc tế.
Sinh viên phải hoàn thành chuẩn kỹ năng theo từng năm để được đăng ký học phần cho
năm tiếp theo, cụ thể như sau:
Chuẩn từng năm Đạt tương đương Ghi chú
Năm thứ nhất
Năm thứ hai Hoàn thành 2 chuyên đề Hết năm nhất
Năm thứ ba Hoàn thành 3 chuyên đề Hết năm hai
Năm thứ tư Hoàn thành 4 chuyên đề Hết năm ba
Sinh viên các chương trình Dạy và Học bằng tiếng Anh/Tiên tiến/Định hướng Nhật
Bản từ khóa 2025 về sau phải tích lũy tối thiểu 04/08 chuyên đề kỹ năng để được đăng
ký Thực tập ngoài trường và tốt nghiệp.

</details>


---

## 16. `990c1b5ec407af462ea48550`

**Question:** Sinh viên muốn phúc khảo điểm một học phần thì phải nộp đơn trong thời hạn bao nhiêu ngày kể từ ngày công bố điểm?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Corpus không quy định thủ tục hay thời hạn phúc khảo điểm học phần. Các điều khoản về đánh giá, hoãn thi và xét kết quả trong corpus không trả lời câu hỏi này; cần tra quy định riêng của nhà trường.

**Candidate behaviour:** answered

**Candidate answer:**

> Trong quy định học vụ Trường Đại học Bách khoa - ĐHQG-HCM, sinh viên phải nộp đơn phúc khảo điểm theo thời hạn xác định trong từng chương trình đào tạo cụ thể. Đối với các khóa tuyển sinh hoặc khóa đào tạo chuyên ngành, thời gian nộp đơn thường là từ ngày công bố điểm đến ngày kết thúc kỳ thi hoặc vòng xét duyệt, cụ thể là **10 ngày** (hoặc nhiều năm tùy loại khóa) tùy theo quy định của từng khoa học.


---

## 17. `99497d2aab78f517d0c90a6d`

**Question:** Theo khoản 5.5 Điều 5 được sửa đổi bởi Quyết định 1260/QĐ-ĐHBK (áp dụng từ học kỳ 1 năm học 2025-2026), điểm trung bình tích lũy tối thiểu (thang 4) để sinh viên được đăng ký các học phần tốt nghiệp là bao nhiêu? Một sinh viên có điểm trung bình tích lũy 2,35 có đạt ngưỡng điểm này không, và học lực được xếp loại gì theo khoản 15.2 do Quyết định 1259/QĐ-ĐHBK sửa đổi?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Ngưỡng tối thiểu là điểm trung bình tích lũy (GPA) từ 2.0 trở lên theo thang điểm 4 (áp dụng từ học kỳ 1 năm học 2025-2026). GPA 2,35 đạt ngưỡng GPA này (việc đăng ký học phần tốt nghiệp còn các điều kiện khác trong khoản 5.5, không được hỏi ở đây), và học lực xếp loại Trung bình (từ 2,00 đến cận 2,50).

**Reference evidence:**
- `HCMUT_HVDT1260_Dieu_1_S5_5`: Sinh viên phải có điểm trung bình tích lũy (GPA) từ 2.0 trở lên (theo thang điểm 4)
- `HCMUT_HVCHUNG1259_Dieu_1_S15_2`: Từ 2,00 đến cận 2,50: Trung bình

**Candidate behaviour:** clarified

**Candidate answer:**

> Trong văn bản trả về, có thông tin chi tiết về con số điểm trung bình tích lũy để đăng ký học phần tốt nghiệp (Điều 5) hay quy định xếp loại học lực theo Điều 15.2 không? Nếu không, tôi cần biết thêm các thông tin liên quan để xác định đáp án chính xác.

<details><summary>Source `HCMUT_HVCHUNG1259_Dieu_1_S15_2` — “15.2 Xếp loại học lực</summary>

“15.2 Xếp loại học lực
Người học được xếp loại học lực theo điểm trung bình học kỳ, điểm trung bình
năm học hoặc điểm trung bình tích lũy như sau:
Từ 3,60 đến 4,00: Xuất sắc;
Từ 3,20 đến cận 3,60: Giỏi;
Từ 2,50 đến cận 3,20: Khá;
Từ 2,00 đến cận 2,50: Trung bình;
Từ 1,00 đến cận 2,00: Yếu;
Dưới 1,00: Kém.”
6. Sửa đổi, bổ sung khoản 16.2 Điều 16 như sau:

</details>

<details><summary>Source `HCMUT_HVDT1260_Dieu_1_S5_5` — “5.5 Đăng ký các học phần tốt nghiệp</summary>

“5.5 Đăng ký các học phần tốt nghiệp
Các học phần tốt nghiệp (Thực tập ngoài trường, Đồ án chuyên ngành, Khóa luận
tốt nghiệp) được thiết kế vào cuối chương trình đào tạo. Sinh viên phải hoàn thành điều
kiện về chuẩn ngoại ngữ và số tín chỉ tích luỹ ngành trước khi được phép đăng ký các học
phần này.
Riêng học phần Thực tập ngoài trường/Thực tập kỹ sư chỉ mở trong học kỳ Hè, đăng
ký theo lịch học vụ học kỳ hè, dự kiến bắt đầu đăng ký từ giữa học kỳ 2. Sinh viên có nhu
cầu đăng ký các học phần thực tập trong học kỳ chính phải đăng ký với Khoa quản lý để
được đồng ý tổ chức học phần thực tập trong học kỳ chính.
Học phần đang học được xem là tạm đạt và tạm tính vào số tín chỉ tích lũy khi xét
đăng ký học phần cho sinh viên.
Sinh viên phải tích luỹ đủ ít nhất 65% (chương trình song ngành là 52%) số tín chỉ
của chương trình đào tạo để đăng ký học phần Thực tập ngoài trường.
Sinh viên phải tích luỹ đủ ít nhất 70% (chương trình song ngành là 76%) số tín chỉ
của chương trình đào tạo để đăng ký học phần Đồ án chuyên ngành.
Sinh viên phải tích luỹ số đủ ít nhất 82.5% (chương trình song ngành là 86%) số tín
chỉ của chương trình đào tạo, hoàn thành tối thiểu 80% chương trình rèn luyện sinh viên
theo quy định của trường và đạt Chuẩn ngoại ngữ tốt nghiệp để đăng ký học phần Khoá
luận tốt nghiệp.
Sinh viên phải có điểm trung bình tích lũy (GPA) từ 2.0 trở lên (theo thang điểm 4)
để được đăng ký các học phần tốt nghiệp (áp dụng từ học kỳ 1 năm học 2025-2026).”
3. Sửa đổi, bổ sung khoản 7.1 Điều 7 như sau:

</details>


---

## 18. `a293a4cb99980e759e28d1e1`

**Question:** Việc gia hạn thời gian nộp học phí theo quy định của Trường Đại học Bách khoa áp dụng cho những loại học kỳ nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Chỉ học kỳ chính; không áp dụng cho học kỳ dự thính và học kỳ hè.

**Reference evidence:**
- `HCMUT_HOCPHI2800_Dieu_5`: không áp dụng cho học kỳ dự thính, học kỳ hè

**Candidate behaviour:** answered

**Candidate answer:**

> Theo các văn bản quy định (HCMUT_HOCPHI2800_Dieu_1, HCMUT_HOCPHI2800_Dieu_5), việc gia hạn học phí có thể áp dụng cho các học kỳ: 1. Học kỳ chính (không áp dụng cho học kỳ dự thính hoặc hè). 2. Sau khi kết thúc thời gian gia hạn nộp học phí của học kỳ kế tiếp, người học không hoàn thành nghĩa vụ sẽ bị xử lý.

**Candidate citations:** `HCMUT_HOCPHI2800_Dieu_6`

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_5` — Điều 5. Quyền lợi của người học khi được gia hạn thời gian nộp học phí</summary>

Điều 5. Quyền lợi của người học khi được gia hạn thời gian nộp học phí
1. Người học được xét đơn xin gia hạn thời gian nộp học phí trong các học kỳ chính
(không áp dụng cho học kỳ dự thính, học kỳ hè).
2. Người học không được gia hạn thời gian nộp học phí trong 02 học kỳ chính liên
tiếp nếu chưa hoàn thành nộp học phí của học kỳ được xét gia hạn trong thời gian quy định.
3. Người học được tiếp tục hoàn thành chương trình đào tạo trong học kỳ được xét
gia hạn thời gian nộp học phí sau khi Trường ban hành quyết định gia hạn thời gian nộp
học phí.

</details>

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_6` — Điều 6. Nghĩa vụ của người học khi được gia hạn thời gian nộp học phí</summary>

Điều 6. Nghĩa vụ của người học khi được gia hạn thời gian nộp học phí
1. Sau khi kết thúc thời gian gia hạn nộp học phí, người học phải nộp đủ học phí cả
02 học kỳ đúng thời hạn theo thông báo nộp học phí ở học kỳ kế tiếp để đảm bảo quyền
lợi học tập và các quyền lợi khác của người học.
2. Sau khi kết thúc thời gian nộp học phí của học kỳ kế tiếp, người học không hoàn
thành nghĩa vụ nộp học phí sau thời gian gia hạn sẽ bị xử lý học vụ theo quy định của
trường.
Chương IV
QUY TRÌNH XÉT GIA HẠN THỜI GIAN NỘP HỌC PHÍ

</details>


---

## 19. `ae51faddbb3555e5fc6e92e1`

**Question:** Theo luật giao thông đường bộ, sinh viên đi xe máy vào khuôn viên trường mà không đội mũ bảo hiểm thì bị phạt bao nhiêu tiền?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Corpus chỉ cấm đi xe máy trong khuôn viên Trường (Nội quy học đường) và không nêu mức phạt tiền theo pháp luật giao thông đường bộ.

**Candidate behaviour:** refused

**Candidate answer:**

> Không có thông tin cụ thể trong văn bản quy chế đã tra cứu về khoản phạt tiền khi sinh viên đi xe máy không đeo mũ bảo hiểm. Đây thuộc phạm vi luật giao thông đường bộ chứ không nằm trong nội dung nội quy học trường của Trường Đại học Bách khoa - ĐHQG-HCM.


---

## 20. `b34f10e2d5c0bf1d480c325c`

**Question:** Một đội thi được hỗ trợ hoặc vinh danh tối đa bao nhiêu lần ở cùng một mức?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** 01 lần.

**Reference evidence:**
- `HCMUT_VINHDANH658_Dieu_5`: Mỗi đội thi chỉ được hỗ trợ/vinh danh 01 lần ở mỗi mức

**Candidate behaviour:** answered

**Candidate answer:**

> Dựa trên quy định trong văn bản quy chế (Điều 5), mỗi đội thi chỉ được hỗ trợ hoặc vinh danh **01 lần** ở mỗi mức.

**Candidate citations:** `HCMUT_VINHDANH658_Dieu_5`

<details><summary>Source `HCMUT_VINHDANH658_Dieu_5` — Điều 5. Tiêu chí xét hỗ trợ và vinh danh</summary>

Điều 5. Tiêu chí xét hỗ trợ và vinh danh
Các đối tượng tại Điều 1 tham gia hoặc đạt giải thưởng cao tại các cuộc thi, giải
thưởng đáp ứng các tiêu chí được quy định tại Điều 5 sẽ được phân loại mức độ, Tổ cố
vấn sẽ xem xét và đề xuất mức hỗ trợ, Hội đồng cố vấn sẽ xem xét và đề xuất mức vinh
danh.
Mỗi đội thi chỉ được hỗ trợ/vinh danh 01 lần ở mỗi mức và không vinh danh mức
thấp hơn nếu đã được vinh danh mức cao trước đó.
Giảng viên hướng dẫn SV, nhóm SV đạt giải thưởng trong các cuộc thi được xếp
loại III trở lên và có hệ số khen thưởng (Kpl) từ 9 trở lên (đối với cá nhân) , từ 18 trở lên
(đối với nhóm SV), từ 27 trở lên (đối với giải đồng đội) sẽ được Hội đồng cố vấn xem xét
và đề xuất mức vinh danh.
Các mức độ phân loại cuộc thi, giải thưởng cụ thể như sau:
1. Loại I
Thoả mãn ít nhất 02 tiêu chí sau:
a. Được tổ chức/ đồng tổ chức/ chỉ đạo/ bảo trợ bởi các t ập đoàn đa quốc gia, các
trường đại học ngoài nước có trong bảng xếp hạng Quacquarelli Symonds
World University Rankings (QS Rankings) / Times Higher Education Worl d University
Rankings (THE Rankings) hoặc các tổ chức/ tập đoàn quốc tế uy tín.
b. Có sự tham gia của các đội thi đến từ các quốc gia phát triển theo danh sách của
Quỹ Tiền tệ quốc tế (IMF).
c. Giải thưởng cho giải cao nhất có giá trị tối thiểu 5.000 USD.
2. Loại II
Thoả mãn ít nhất 02 tiêu chí sau:
a. Được tổ chức/ đồng tổ chức/ chỉ đạo/ bảo trợ bởi các Bộ/ Ngành, các cơ quan
thuộc các tổ chức Chính phủ/ Phi chính phủ hoặc các tập đoàn có thương hiệu quốc gia /
quốc tế.
b. Có sự tham gia của ít nhất 03 trường thành viên trong khối Đại học quốc gia Hà
Nội/ Đại học quốc gia Thành phố Hồ Chí Minh hoặc trong nhóm 07 trường Đại học Kỹ
thuật.
c. Có sự tham gia của các đội thi đến từ các doanh nghiệp.
d. Giải thưởng cho giải cao nhất có giá trị tối thiểu 30.000.000 đồng.
3. Loại III
Thoả mãn ít nhất 02 tiêu chí sau:
a. Được tổ chức/ đồng tổ chức/ chỉ đạo/ bảo trợ bởi các Sở/ Ban/ Ngành của các
Tỉnh/ Thành phố trực thuộc Trung ương.
b. Có sự tham gia của ít nhất 02 tr ường thành viên trong khối Đại học quốc gia Hà
Nội/ Đại học quốc gia Thành phố Hồ Chí Minh hoặc trong nhóm 07 trường Đại học Kỹ
thuật.
c. Giải thưởng cho giải cao nhất có giá trị tối thiểu 20.000.000 đồng.
4. Loại IV
Thoả mãn 02 tiêu chí sau:
a. Cuộc thi do một trường Đại học tổ chức.
b. Có sự tham gia của các đội thi đến từ ít nhất 03 trường Đại học/ Cao Đẳng/
Trung học phổ thông.

</details>


---

## 21. `b53a9f0a19aaa998ce5f1271`

**Question:** Theo luật giao thông đường bộ, sinh viên đi xe máy vào khuôn viên trường mà không đội mũ bảo hiểm thì bị phạt bao nhiêu tiền?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Corpus chỉ cấm đi xe máy trong khuôn viên Trường (Nội quy học đường) và không nêu mức phạt tiền theo pháp luật giao thông đường bộ.

**Candidate behaviour:** refused

**Candidate answer:**

> Không tìm thấy quy định trong văn bản đã tra cứu về mức phạt sinh viên đi xe máy vào campus.


---

## 22. `c8b3365b91699033c0bcb6d7`

**Question:** Người học muốn xin gia hạn thời gian nộp học phí thì nộp đơn đăng ký về phòng nào, và phòng đó giữ những chức danh nào trong Hội đồng xét hồ sơ xin gia hạn?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Nộp về Phòng Công tác sinh viên (Điều 7, Bước 1). Trong Hội đồng xét hồ sơ (Điều 8 khoản 1), Trưởng Phòng Công tác sinh viên là Phó Chủ tịch Hội đồng và Phó Trưởng phòng Công tác sinh viên là thư ký.

**Reference evidence:**
- `HCMUT_HOCPHI2800_Dieu_7`: Bước 1: Người học nộp đơn đăng ký gia hạn thời gian nộp học phí về Phòng Công
tác sinh viên
- `HCMUT_HOCPHI2800_Dieu_8`: Trưởng Phòng
Công tác sinh viên là Phó Chủ tịch Hội đồng
- `HCMUT_HOCPHI2800_Dieu_8`: Phó Trưởng phòng Công tác sinh viên là thư ký

**Candidate behaviour:** answered

**Candidate answer:**

> Để xin gia hạn thời gian nộp học phí, người học phải nộp đơn đăng ký về phòng Công tác sinh viên. Về các chức danh trong Hội đồng xét hồ sơ, theo Điều 8 của Quy định gia hạn học phí (số 2800/QĐ-ĐHBK), thành viên hội đồng gồm: Chủ tịch Hội đồng là Phó Hiệu trưởng; Trưởng Phòng Công tác sinh viên là Phó Chủ tịch Hội đồng; Trưởng Phòng Kế hoạch – Tài chính là ủy viên; Trưởng Phòng Đào tạo là ủy viên; Phó Trưởng phòng Công tác sinh viên là thư ký. Các chức danh này được quy định trong Điều 8 của quy định.

**Candidate citations:** `HCMUT_HOCPHI2800_Dieu_8`

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_7` — Điều 7. Quy trình gia hạn thời gian nộp học phí</summary>

Điều 7. Quy trình gia hạn thời gian nộp học phí
Người học và các đơn vị liên quan thực hiện quy trình gồm các bước sau:
Bước 1: Người học nộp đơn đăng ký gia hạn thời gian nộp học phí về Phòng Công
tác sinh viên, kèm các minh chứng cần thiết. Thời gian đăng ký gia hạn phải trước thời
điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc. (Phụ lục 1)
Bước 2: Phòng Công tác sinh viên tổng hợp, tổ chức hội đồng xét duyệt và trình
Ban Giám hiệu phê duyệt.
Bước 3: Phòng Công tác sinh viên thông báo kết quả cho người học , thực hiện gia
hạn thời gian nộp học phí, đồng thời thông báo kết quả cho Phòng Kế hoạch - Tài chính để
theo dõi công nợ của người học.
Bước 4: Người học thực hiện nộp học phí sau khi hết thời gian gia hạn.
Bước 5: Phòng Kế hoạch - Tài chính gửi kết quả theo dõi công nợ của người học
được xét gia hạn về Phòng Công tác sinh viên sau khi kết thúc thời gian nộp học phí ở học
kỳ kế tiếp.
Bước 6: Phòng Công tác sinh viên ra quyết định liên quan đến nợ học phí, xử lý học
vụ (đối với người học không hoàn thành nộp học phí).

</details>

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_8` — Điều 8. Quy trình xét hồ sơ</summary>

Điều 8. Quy trình xét hồ sơ
1. Trường ban hành quyết định thành lập Hội đồng xét hồ sơ xin gia hạn thời gian
nộp học phí, bao gồm 5 thành viên: Phó Hiệu trưởng là Chủ tịch Hội đồng; Trưởng Phòng
Công tác sinh viên là Phó Chủ tịch Hội đồng; Trưởng Phòng Kế hoạch – Tài chính là ủy
viên; Trưởng Phòng Đào tạo là ủy viên; Phó Trưởng phòng Công tác sinh viên là thư ký.
2. Hội đồng thực hiện xét hồ sơ dựa trên các tiêu chuẩn xét gia hạn thời gian nộp
học phí quy định tại Điều 4.
Chương V
TỔ CHỨC THỰC HIỆN

</details>


---

## 23. `d7d9aaad7ec62afa58df5213`

**Question:** Theo Quy định gia hạn học phí của Trường Đại học Bách khoa, người học phải nộp đơn đăng ký gia hạn trước thời điểm kết thúc thời gian nộp học phí ít nhất bao nhiêu ngày làm việc?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Ít nhất 05 ngày làm việc.

**Reference evidence:**
- `HCMUT_HOCPHI2800_Dieu_7`: điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc.

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Quy định gia hạn học phí Trường Đại học Bách khoa – Đại học Quốc gia TP. HCM (Số 2800/QĐ-ĐHBK), người học phải nộp đơn đăng ký gia hạn trước thời điểm kết thúc thời gian nộp học phí ít nhất **05 ngày** làm việc.

**Candidate citations:** `HCMUT_HOCPHI2800_Dieu_7`

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_7` — Điều 7. Quy trình gia hạn thời gian nộp học phí</summary>

Điều 7. Quy trình gia hạn thời gian nộp học phí
Người học và các đơn vị liên quan thực hiện quy trình gồm các bước sau:
Bước 1: Người học nộp đơn đăng ký gia hạn thời gian nộp học phí về Phòng Công
tác sinh viên, kèm các minh chứng cần thiết. Thời gian đăng ký gia hạn phải trước thời
điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc. (Phụ lục 1)
Bước 2: Phòng Công tác sinh viên tổng hợp, tổ chức hội đồng xét duyệt và trình
Ban Giám hiệu phê duyệt.
Bước 3: Phòng Công tác sinh viên thông báo kết quả cho người học , thực hiện gia
hạn thời gian nộp học phí, đồng thời thông báo kết quả cho Phòng Kế hoạch - Tài chính để
theo dõi công nợ của người học.
Bước 4: Người học thực hiện nộp học phí sau khi hết thời gian gia hạn.
Bước 5: Phòng Kế hoạch - Tài chính gửi kết quả theo dõi công nợ của người học
được xét gia hạn về Phòng Công tác sinh viên sau khi kết thúc thời gian nộp học phí ở học
kỳ kế tiếp.
Bước 6: Phòng Công tác sinh viên ra quyết định liên quan đến nợ học phí, xử lý học
vụ (đối với người học không hoàn thành nộp học phí).

</details>


---

## 24. `dd4f2cb123df5116d86593f3`

**Question:** Sinh viên muốn phúc khảo điểm một học phần thì phải nộp đơn trong thời hạn bao nhiêu ngày kể từ ngày công bố điểm?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Corpus không quy định thủ tục hay thời hạn phúc khảo điểm học phần. Các điều khoản về đánh giá, hoãn thi và xét kết quả trong corpus không trả lời câu hỏi này; cần tra quy định riêng của nhà trường.

**Candidate behaviour:** answered

**Candidate answer:**

> Dựa trên các tài liệu tra cứu, quy định nộp đơn gia hạn học phí (thay vì phúc khảo điểm) cho sinh viên là phải hoàn thành trong thời gian nhất thiết. Tuy nhiên, thông tin cụ thể về 'thời hạn' cho việc phúc khảo điểm (điểm) chưa được nêu rõ trong các văn bản chính thức. Từ Article 7, quy trình gia hạn cần thực hiện trước khi điểm expires. Nếu hiểu 'nộp đơn' là thủ tục chuẩn xác, thời gian làm việc tối thiểu là 5 ngày. Tuy nhiên, 'phúc khảo' thường diễn ra sau khi kết thúc kỳ học hoặc theo quy định riêng.

**Candidate citations:** `HCMUT_HOCPHI2800_Dieu_7`

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_7` — Điều 7. Quy trình gia hạn thời gian nộp học phí</summary>

Điều 7. Quy trình gia hạn thời gian nộp học phí
Người học và các đơn vị liên quan thực hiện quy trình gồm các bước sau:
Bước 1: Người học nộp đơn đăng ký gia hạn thời gian nộp học phí về Phòng Công
tác sinh viên, kèm các minh chứng cần thiết. Thời gian đăng ký gia hạn phải trước thời
điểm kết thúc thời gian nộp học phí ít nhất 05 ngày làm việc. (Phụ lục 1)
Bước 2: Phòng Công tác sinh viên tổng hợp, tổ chức hội đồng xét duyệt và trình
Ban Giám hiệu phê duyệt.
Bước 3: Phòng Công tác sinh viên thông báo kết quả cho người học , thực hiện gia
hạn thời gian nộp học phí, đồng thời thông báo kết quả cho Phòng Kế hoạch - Tài chính để
theo dõi công nợ của người học.
Bước 4: Người học thực hiện nộp học phí sau khi hết thời gian gia hạn.
Bước 5: Phòng Kế hoạch - Tài chính gửi kết quả theo dõi công nợ của người học
được xét gia hạn về Phòng Công tác sinh viên sau khi kết thúc thời gian nộp học phí ở học
kỳ kế tiếp.
Bước 6: Phòng Công tác sinh viên ra quyết định liên quan đến nợ học phí, xử lý học
vụ (đối với người học không hoàn thành nộp học phí).

</details>


---

## 25. `e4fa2df5a8e80119df3f9c68`

**Question:** Việc gia hạn thời gian nộp học phí theo quy định của Trường Đại học Bách khoa áp dụng cho những loại học kỳ nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Chỉ học kỳ chính; không áp dụng cho học kỳ dự thính và học kỳ hè.

**Reference evidence:**
- `HCMUT_HOCPHI2800_Dieu_5`: không áp dụng cho học kỳ dự thính, học kỳ hè

**Candidate behaviour:** answered

**Candidate answer:**

> Theo các điều khoản trong văn bản quy định học vụ của Trường Đại học Bách khoa:
> 
> 1. **Phạm vi điều chỉnh**: Các điều kiện được xét gia hạn thời gian nộp học phí bao gồm việc xác định cụ thể những học kỳ (học kỳ chính, học kỳ dự thính, học kỳ hè) mà trường có quyền áp dụng quy định gia hạn.
> 2. **Nghĩa vụ khi gia hạn**: Người học phải nộp đủ học phí trong thời hạn quy định của từng học kỳ sau khi được gia hạn, nhằm đảm bảo quyền lợi học tập và các quyền lợi khác.

**Candidate citations:** `HCMUT_HOCPHI2800_Dieu_1`

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_1` — Điều 1. Phạm vi điều chỉnh</summary>

Điều 1. Phạm vi điều chỉnh
Văn bản này quy định về việc gia hạn thời gian nộp học phí đối với người học, bao
gồm: điều kiện được xét gia hạn thời gian nộp học phí; nhiệm vụ và quyền của người học
khi được gia hạn thời gian nộp học phí; quy trình và thủ tục gia hạn thời gian nộp học phí;
tổ chức thực hiện.

</details>

<details><summary>Source `HCMUT_HOCPHI2800_Dieu_5` — Điều 5. Quyền lợi của người học khi được gia hạn thời gian nộp học phí</summary>

Điều 5. Quyền lợi của người học khi được gia hạn thời gian nộp học phí
1. Người học được xét đơn xin gia hạn thời gian nộp học phí trong các học kỳ chính
(không áp dụng cho học kỳ dự thính, học kỳ hè).
2. Người học không được gia hạn thời gian nộp học phí trong 02 học kỳ chính liên
tiếp nếu chưa hoàn thành nộp học phí của học kỳ được xét gia hạn trong thời gian quy định.
3. Người học được tiếp tục hoàn thành chương trình đào tạo trong học kỳ được xét
gia hạn thời gian nộp học phí sau khi Trường ban hành quyết định gia hạn thời gian nộp
học phí.

</details>


---

## 26. `e5dea64294bbad7e32d7dcf0`

**Question:** Theo Quyết định 2282/QĐ-ĐHBK sửa đổi khoản 3.2 Điều 3 của Quy định giảng dạy, số phiên học bố trí dạy thay của một lớp không được vượt quá bao nhiêu phần trăm tổng số phiên học?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** 20% tổng số phiên học của lớp (và không quá 03 phiên học đã được phân công của giảng viên cho một lớp).

**Reference evidence:**
- `HCMUT_GIANGDAY2282_Dieu_1`: Số phiên học bố trí dạy thay của một lớp không được vượt quá 20% tổng số
- `HCMUT_GIANGDAY2282_Dieu_1`: không quá 03 phiên học đã được phân công giảng dạy của giảng viên cho một

**Candidate behaviour:** clarified

**Candidate answer:**

> Cần biết rõ quy định sửa đổi Điều 3.2 của Quy định giảng dạy (Quyết định 2282/QĐ-ĐHBK) có bao nhiêu phần trăm tổng số phiên học không?

<details><summary>Source `HCMUT_GIANGDAY2282_Dieu_1` — Điều 1. Sửa đổi, bổ sung một số điều của Quy định giảng dạy ban hành kèm theo</summary>

Điều 1. Sửa đổi, bổ sung một số điều của Quy định giảng dạy ban hành kèm theo
Quyết định số 2929/QĐ-ĐHBK ngày 10 tháng 09 năm 2021 của Hiệu trưởng trường Đại
học Bách khoa, Đại học Quốc Gia Tp.HCM, như sau:
1. Sửa đổi, bổ sung Điều 2 như sau:
“Điều 2. Các khái niệm
Các khái niệm có dùng trong quy định này mà không được định nghĩa rõ ràng trong
quy định sẽ căn cứ trên các quy định khác hiện hành (các văn bản, quy định, quy chế, thông
tư, nghị định, luật, hướng dẫn của nhà trường, của Đại học Quốc gia thành phố Hồ Chí
Minh, của các Bộ ngành và Chính phủ).
Một số khái niệm dùng riêng trong quy định này:
- Khoa: chỉ chung cho các Khoa và Trung tâm Ngoại ngữ.
- Giảng viên: chỉ chung cho tất cả người giảng dạy là giảng viên hay người hỗ trợ giảng
dạy, người hướng dẫn đồ án, bài tập lớn, thí nghiệm, …”
2. Sửa đổi, bổ sung khoản 3.2 Điều 3 như sau:
“3.2 Nghỉ dạy, dạy bù và dạy thay
Một số phiên học có thể có giảng viên khác dạy thay cho giảng viên được phân công
ban đầu. Người dạy thay phải có trình độ và năng lực phù hợp với yêu cầu của phần nội
dung dạy thay và phải được sự đồng ý của Khoa phân công giảng dạy. Các trường hợp dạy
thay nhưng không được sự đồng ý của Khoa phân công giảng dạy được tính như là nghỉ
dạy có báo. Số phiên học bố trí dạy thay của một lớp không được vượt quá 20% tổng số
phiên học và không quá 03 phiên học đã được phân công giảng dạy của giảng viên cho một
lớp.
Trong trường hợp bất khả kháng, giảng viên có thể nghỉ dạy và phải báo nghỉ dạy
cho nhà trường, và cho tất cả người học bị ảnh hưởng. Thời hạn báo cho người học trễ nhất
là trước giờ lên lớp của phiên học. Thời hạn báo cho nhà trường trễ nhất là trước 21g00 của
cùng ngày nghỉ. Khuyến khích báo trước cho nhà trường và người học trước 16g00 của
ngày làm việc trước ngày nghỉ 02 ngày.
Giảng viên không được nghỉ dạy ở phiên đầu tiên của lớp học theo thời khóa biểu.
Giảng viên không được đăng ký nghỉ dạy tiếp theo đối với cùng một nhóm lớp nếu phiên
học đã nghỉ trước đó nhóm lớp này chưa được dạy bù.
Giảng viên phải đảm bảo giảng dạy đủ giờ theo quy định của học phần. Khi không
giảng dạy đủ giờ, giảng viên cần phải dạy bù trong các tuần học theo biểu đồ học tập và
trước khi thi cuối kỳ của học phần. Một lần dạy bù, chỉ được dạy bù cho một phiên học của
lớp và không quá 04 tiết một ngày hoặc không quá số tiết của phiên học đã được phân công
trên thời khoá biểu. Ngoài ra, tổng số tiết học của một lớp và số giờ dạy bù của lớp trong
một tuần không được quá 15 tiết.
Khi đăng ký dạy bù, giảng viên phải đăng ký trước 16g00 của ngày làm việc cách
trước ngày dạy bù tối thiểu 01 ngày và trước tối đa 07 ngày. Giảng viên có trách nhiệm
thông báo cho toàn bộ người học bị ảnh hưởng bởi việc dạy bù. Khi dạy bù, cho phép tối
đa 10% số người học bị trùng giờ. Giảng viên phải đảm bảo quyền lợi học tập của người
học khi tổ chức dạy bù, có trách nhiệm hỗ trợ người học bị trùng giờ không tham gia lớp
học bù được.
Giảng viên không được phép nghỉ dạy, dạy bù quá 20% số tiết và không quá 03
phiên học đã được phân công giảng dạy của một lớp.
Việc báo nghỉ dạy, dạy bù, dạy thay được thực hiện qua hệ thống Hỗ trợ giảng dạy
trên cổng thông tin và dịch vụ trực tuyến nhà trường (myBK - mybk.hcmut.edu.vn). Trong
trường hợp đặc biệt, cần liên hệ Phòng Thanh tra Pháp chế để được hỗ trợ.”

</details>


---

## 27. `edbb567440fefb44b1a57437`

**Question:** Theo Nội quy học đường, quy định cấm hút thuốc lá trong khuôn viên Trường nêu rõ bao gồm cả loại thuốc lá nào ngoài thuốc lá thông thường?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** Bao gồm cả thuốc lá điện tử.

**Reference evidence:**
- `HCMUT_NOIQUY1924_Dieu_5`: hút thuốc lá trong khuôn viên Trường (bao gồm thuốc lá
điện tử)

**Candidate behaviour:** answered

**Candidate answer:**

> Theo nội quy học đường Trường Đại học Bách khoa - ĐHQG-HCM, quy định cấm hút thuốc lá bao gồm cả các loại thuốc lá điện tử. Điều 8 của Quy tắc ứng xử tại Trường (số 3408/QĐ-ĐHBK) và Điều 5 (sử dụng, mua bán, tàng trữ...) đều ghi rõ: 'Hút thuốc lá trong khuôn viên Trường (bao gồm thuốc lá điện tử)'.

**Candidate citations:** `HCMUT_UNGXU3408_Dieu_4`

<details><summary>Source `HCMUT_NOIQUY1924_Dieu_5` — Điều 5. Những hành vi sinh viên KHÔNG được phép thực hiện</summary>

Điều 5. Những hành vi sinh viên KHÔNG được phép thực hiện
1. Gian lận trong học tập, kiểm tra, thi cử.
2. Cho người khác mượn thẻ sinh viên hoặc mượn thẻ sinh viên của người khác để
sử dụng, sử dụng thẻ sinh viên sai mục đích.
3. Đi xe máy, xe đạp trong khuôn viên Trường.
4. Dẫm, nằm, ngồi lên cỏ ở các khu vực có biển cấm trong khuôn viên Trường; hái
hoa, bẻ cành cây trong khuôn viên Trường; chơi thể thao tại những địa điểm ngoài
khu vực sân thể dục thể thao theo quy định của Trường.
5. Tổ chức hoặc tham gia cờ bạc dưới mọi hình thức trong khuôn viên Trường.
6. Mang theo hoặc sử dụng các chất cháy, chất gây nổ; các loại vũ khí, hung khí vào
Trường.
7. Mang đồ ăn vào lớp học, gi ảng đường và hội trường. Mang theo động vật, thú
nuôi vào Trường.
8. Sử dụng, mua bán, tàng trữ các chất ma túy, các chất kích thích dưới mọi hình
thức; uống rượu, bia và hút thuốc lá trong khuôn viên Trường (bao gồm thuốc lá
điện tử); say rượu bia khi đến Trường.
9. Tự ý viết, dán quảng cáo, thông báo trong khuôn viên Trường; viết, vẽ, sơn bậy,
bôi xóa, làm bẩn, làm mất vệ sinh và làm hư hỏng các trang thiết bị học tập, máy
móc, dụng cụ thực hành thí nghiệm, cơ sở vật chất … của Trường.
10. Tự ý sử dụng tài sản của Nhà trường; tự ý di chuyển các trang thiết bị, tài sản ra
khỏi vị trí đã sắp xếp, lắp đặt trong phòng và trong khuôn viên Trường. Đứng lên
bàn ghế, leo trèo hoặc ngồi trên lan can, khung cửa sổ và trên bàn học, bàn giáo
viên.
11. Lưu hành, tuyên truyền các ấn phẩm, tài liệu, thông tin phản động, phim ảnh
không lành mạnh và các tài liệu cấm khác theo quy định của Nhà nước.
12. Gây bè phái, gây mất đoàn kết nội bộ trong tập thể lớp và trong Trường. Gây gổ,
đánh nhau hoặc kích động đánh nhau, tổ chức băng nhóm, tụ tập gây mất an ninh,
trật tự dưới mọi hình thức.
13. Không lợi dụng mạng xã hội nhằm mục đích xâm phạm đời tư, công việc và học
tập của cá nhân, cơ quan, tổ chức, đoàn thể; có ý thức bảo vệ, xây dựng hình ảnh,
thương hiệu của Nhà trường trên không gian mạng.
14. Không sử dụng từ ngữ gây thù hận, kích động bạo lực, phân biệt vùng miền, giới
tính, tôn giáo, dân tộc.
15. Tổ chức, tham gia, truyền bá các hoạt động mê tín dị đoan, các hoạt động tôn
giáo và các hành vi vi phạm đạo đức khác trong và ngoài khuôn viên Trường.
16. Tổ chức, tham gia các hoạt động chính trị trái pháp luật trong và ngoài khuôn
viên Trường.
17. Tham gia các hoạt động tập thể mang danh nghĩa Nhà trường khi chưa được Nhà
trường cho phép.
18. Có hành vi xúc phạm nhân phẩm, danh dự, xâm phạm tới thân thể, sức khỏe và
tài sản của cán bộ, giảng viên, người lao động và sinh viên khác của Nhà trường.
19. Tổ chức hoặc tham gia các hoạt động vi phạm pháp luật khác.

</details>

<details><summary>Source `HCMUT_UNGXU3408_Dieu_4` — Điều 4. Quy tắc chung</summary>

Điều 4. Quy tắc chung
1. Có trách nhiệm xây dựng và bảo vệ hình ảnh, thương hiệu của Trường Đại học Bách
khoa – ĐHQG-HCM.
2. Trang phục lịch sự, gọn gàng phù hợp với văn hóa học đường, khuyến khích VC –
NLĐ sử dụng trang phục thương hiệu của Trường. VC – NLĐ mặc lễ phục trang
trọng, lịch sự theo quy định của sự kiện.
3. Chấp hành nghiêm chủ trương, đường lối của Đảng, chính sách pháp luật của Nhà
nước và quy định của Nhà trường; kiên quyết đấu tranh, ngăn chặn những hành vi
vi phạm pháp luật, vi phạm quy định của Nhà trường.
4. Có tác phong làm việc nghiêm túc, chuyên nghiệp; chấp hành nghiêm quy định về
thời gian làm việc của Nhà trường, sử dụng hiệu quả thời gian làm việc; sử dụng
ngôn ngữ chuẩn mực, rõ ràng; sẵn sàng lắng nghe, chia sẻ và giú p đỡ người học,
đồng nghiệp.
5. Tôn trọng danh dự, uy tín của cơ quan, tổ chức, cá nhân có quan hệ công tác; chân
thành, thiện chí, sẵn sàng hỗ trợ lẫn nhau để hoàn thành nhiệm vụ.
6. Thực hiện đúng nhiệm vụ, quyền hạn được giao; giữ gìn đoàn kết nội bộ; phát h uy
trách nhiệm nêu gương và xây dựng môi trường làm việc, học tập chuyên nghiệp,
thân thiện.
7. Tích cực xây dựng không gian làm việc xanh, sạch, đẹp và môi trường công sở văn
minh, thân thiện; không lưu trữ và phát tán các hình ảnh, nội dung văn hóa phẩm
đồi trụy, tài liệu chống phá Đảng, Nhà nước, Nhà trường.
8. Không sử dụng, mua bán, tàng trữ trái phép các chất ma túy, các chất kích thích
dưới mọi hình thức; không hút thuốc lá trong khuôn viên Trường (kể cả thuốc lá
điện tử).

</details>


---

## 28. `edd937b91f307a3c263e8af7`

**Question:** Theo Quy định về công tác GVCN và CVHT, cố vấn học tập có nhiệm vụ gì liên quan đến tín chỉ tự chọn tự do, và theo Quyết định 1862/QĐ-ĐHBK sửa đổi, chương trình đào tạo trình độ đại học khóa 2025 về trước cần có tối thiểu bao nhiêu tín chỉ tự chọn tự do?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** CVHT tư vấn cho người học về các tín chỉ tự chọn tự do (Điều 15 khoản 4 Quy định GVCN và CVHT); chương trình đào tạo trình độ đại học khóa 2025 về trước cần có tối thiểu 9 tín chỉ tự chọn tự do (khoản 5 Điều 12 được sửa đổi).

**Reference evidence:**
- `HCMUT_GVCN2977_Dieu_15`: Tư vấn cho người học về các tín chỉ tự chọn tự do.
- `HCMUT_CTDT1862_Dieu_1`: có tối thiểu 9 tín chỉ tự chọn tự do (đối với khóa 2025 về trước)

**Candidate behaviour:** refused

**Candidate answer:**

> Không thể xác thực căn cứ sau 2 lần thử sửa chữa. Chi tiết vi phạm: Trích nguyên văn của 'HCMUT_CTDT1862_Dieu_1' không nằm trong văn bản nguồn. Đọc lại nguồn hoặc bỏ trường exact_quote nếu chỉ diễn giải.

<details><summary>Source `HCMUT_CTDT1862_Dieu_1` — Điều 1. Sửa đổi, bổ sung một số điều của Quy định cấu trúc và quy trình xây dựng,</summary>

Điều 1. Sửa đổi, bổ sung một số điều của Quy định cấu trúc và quy trình xây dựng,
thẩm định, điều chỉnh chương trình đào tạo; quy trình mở ngành đào tạo trình độ đại học,
thạc sĩ, tiến sĩ ban hành kèm theo Quyết định số 3538/QĐ-ĐHBK ngày 11 tháng 9 năm 2025
của Hiệu trưởng trường Đại học Bách khoa, Đại học Quốc gia Thành phố Hồ Chí Minh
1. Sửa đổi, bổ sung Điều 2 như sau:
a) Sửa đổi, bổ sung điểm b khoản 2 Điều 2:
“b) Học phần được tổ chức dưới dạng lý thuyết bao gồm giảng dạy lý thuyết và thực
hành (thảo luận, thực hành tại lớp, thí nghiệm, bài tập lớn, kiến tập), trong đó phần thực
hành chiếm tối thiểu 20% khối lượng tín chỉ học phần; hoặc dưới dạng thực hành (thí
nghiệm, thực hành, thực tập, thực tập ngoài trường/doanh nghiệp); hoặc dưới dạng đồ án
(đồ án, đồ án chuyên ngành, đồ án/khóa luận tốt nghiệp, chuyên đề/đề án/luận văn thạc sĩ,
tiểu luận/chuyên đề/luận án tiến sĩ.”.
b) Sửa đổi, bổ sung điểm e khoản 3 Điều 2:
“e) Cấp độ năm là các học phần ở chương trình chuyên sâu đặc thù, bao gồm cả giai
đoạn chuyên sâu kỹ sư của chương trình đào tạo Kỹ sư Chất lượng cao tại Việt Nam (viết
tắt là PFIEV) (người học từ năm thứ năm), trình độ thạc sĩ và tiến sĩ, ngoại trừ các học
phần nêu trong điểm f và g trong khoản này;”.
2. Bổ sung khoản 5 Điều 3 như sau:
“5. Chương trình tích hợp: Đại học – Thạc sĩ, Thạc sĩ – Tiến sĩ là các chương trình
đào tạo liên tục giữa hai trình độ học tập , nhằm rút ngắn thời gian học hoặc kết hợp khung
kiến thức, tín chỉ của hai trình độ liên tiếp. Người học được cấp bằng tương ứng với trình
độ đã hoàn thành.”.
3. Thay thế Điều 6 như sau:
“Điều 6. Cấu trúc của chương trình đào tạo đại học
1. Các ngành kỹ thuật và kiến trúc theo khung của tiêu chuẩn kiểm định ABET và
của một số tổ chức kiểm định quốc tế:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 30
1. Toán tối thiểu 11
2. Khoa học tự nhiên tối thiểu 5
Giáo dục chung 30
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 8
Cơ sở ngành/ Ngành/ Chuyên ngành 68–72
1. Cơ sở ngành 18–34
2. Ngành/ Chuyên ngành
34–54
3. Tốt nghiệp trình độ đại học
Tổng tín chỉ 128–132
2. Các ngành quản lý theo khung của tiêu chuẩn kiểm định FIBAA:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 12
1. Toán quản lý 9
2. Khoa học tự nhiên 3
Giáo dục chung 30
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 8
Cơ sở ngành/ Ngành/ Chuyên ngành 86–90
1. Cơ sở ngành 18–34
2. Ngành/ Chuyên ngành
52–72
3. Tốt nghiệp trình độ đại học
Tổng tín chỉ 128–132
”.
4. Thay thế Điều 7 như sau:
“ Điều 7. Cấu trúc của chương trình đào tạo PFIEV
1. Xét theo giai đoạn:
Giai đoạn Số tín chỉ
Tổng tín chỉ 158–163
1.
Giai đoạn 1
(bao gồm 8 tín chỉ tiếng Anh và 8 tín chỉ tiếng Pháp)
66
2.
Giai đoạn 2
(bao gồm 4 tín chỉ tiếng Pháp)
92–97
2. Xét theo khối kiến thức:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 36
1. Toán 21
2. Khoa học tự nhiên 15
Giáo dục chung 42
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 20
Cơ sở ngành/ Ngành/ Chuyên ngành 80–85
1. Cơ sở ngành 16–32
2. Ngành/ Chuyên ngành
48–69
3. Tốt nghiệp chương trình PFIEV
Tổng tín chỉ 158–163
”.
5. Thay thế Điều 9 như sau:
“ Điều 9. Cấu trúc của chương trình đào tạo thạc sĩ
Khối kiến thức Thạc sĩ ứng dụng Thạc sĩ nghiên cứu Thạc sĩ nghiên cứu chuyên sâu
Đa ngành, tổng quát
1. Triết học 3 3 3
2. Tự chọn đa ngành, tổng quát 6 - -
3. Phương pháp nghiên cứu khoa học - 3 3
Cơ sở ngành/ Ngành
1. Cơ sở ngành 12 12 -
2. Ngành/ Chuyên ngành 24 12 -
Tốt nghiệp trình độ thạc sĩ
1. Thực tập 6 - -
2. Chuyên đề nghiên cứu trước luận văn - 15
3. Đề án tốt nghiệp/ Luận văn thạc sĩ 9
15
+ Báo cáo
khoa học
54
1×9
3×15
+ Báo cáo
khoa học
Tổng số tín chỉ 60 60 60
”.
6. Thay thế Điều 11 như sau:
“ Điều 11. Quy định thêm về khối kiến thức
Quy định tại Điều này áp dụng đối với các khối kiến thức quy định từ Điều 6
đến Điều 10.
Khối kiến thức Số tín chỉ Ghi chú
a) Giáo dục chung khác
1. Nhập môn 3 Kỹ thuật/ Điện toán/ Kiến trúc/ Quản lý
2.
Kiến thức quản lý/ Khởi nghiệp
Hoặc
Kiến thức kỹ thuật ngoài ngành đối
với các ngành quản lý
3
3.
Kiến thức về con người và môi
trường/ Kỹ năng nghề nghiệp
chuyên nghiệp
3
Các kiến thức về tác động của
ngành với con người, xã hội và
môi trường
b) Ngoại ngữ
1. Tiếng Anh 8
2. Tiếng Pháp 12 Chương trình PFIEV
c) Chuyên sâu đặc thù
Có thể dùng xét công nhận đạt các khối kiến thức chuyên ngành bắt buộc, khối kiến
thức chuyên ngành tự chọn và khối kiến thức thực tập trong chương trình thạc sĩ.
1. Học kỳ doanh nghiệp 15
d) Tốt nghiệp trình độ đại học từ khóa 2025 về trước
1. Thực tập ngoài trường 2 Học kỳ 6, có thể vận hành trong hè của năm 3
2. Đồ án chuyên ngành 2 Học kỳ 7
3. Đồ án/ Khóa luận tốt nghiệp 4 Học kỳ 8
e) Tốt nghiệp trình độ đại học từ khóa 2026
1. Học kỳ thực tập doanh nghiệp 11 Học kỳ 7
2. Đồ án/ Khóa luận tốt nghiệp 6 Học kỳ 8
f) Tốt nghiệp chương trình PFIEV
1. Thực tập công nhân 2 Học kỳ 4, có thể vận hành trong hè của năm 2
2. Thực tập ngoài trường 2 Học kỳ 6, có thể vận hành trong hè của năm 3
3. Học kỳ thực tập doanh nghiệp 13 Học kỳ 8 (có thể vận hành trong hè của năm 4) và học kỳ 9
4. Đồ án tốt nghiệp kỹ sư 9 Học kỳ 10
g) Tốt nghiệp trình độ thạc sĩ ứng dụng
1. Thực tập ngoài trường 6 Học kỳ 3
2. Đề án tốt nghiệp 9 Học kỳ 4
h) Tốt nghiệp trình độ thạc sĩ nghiên cứu
1. Chuyên đề nghiên cứu trước luận văn 15 Học kỳ 3
2. Luận văn thạc sĩ 15 Học kỳ 4
i) Tốt nghiệp trình độ thạc sĩ nghiên cứu chuyên sâu
1.
Luận văn thạc sĩ nghiên cứu
chuyên sâu
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 1
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 2
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 3
54
9
15
15
15
Học kỳ 1
Học kỳ 2
Học kỳ 3
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 4 Học kỳ 4
j) Tốt nghiệp trình độ tiến sĩ – Phương thức 1
1.
Luận án tiến sĩ
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận án tiến sĩ – chuẩn bị
Luận án tiến sĩ – phần 1
Luận án tiến sĩ – phần 2
Luận án tiến sĩ – phần 3
Luận án tiến sĩ – phần 4
Luận án tiến sĩ – phần 5
87
12
15
15
15
15
15
Học kỳ 1
Học kỳ 2
Học kỳ 3
Học kỳ 4
Học kỳ 5
Học kỳ 6
k) Tốt nghiệp trình độ tiến sĩ – Phương thức 2
1.
Luận án tiến sĩ
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận án tiến sĩ – phần 1
Luận án tiến sĩ – phần 2
Luận án tiến sĩ – phần 3
Luận án tiến sĩ – phần 4
Luận án tiến sĩ – phần 5
75
15
15
15
15
15
Học kỳ 2
Học kỳ 3
Học kỳ 4
Học kỳ 5
Học kỳ 6
Ghi chú:
(†): Các phần học thành phần dùng để bố trí đăng ký học phần trên thời khóa biểu, tính học
phí và tính khối lượng giảng dạy, không in vào Phụ lục bằng tốt nghiệp.”.
7. Sửa đổi, bổ sung Điều 12 như sau:
a) Sửa đổi, bổ sung khoản 4 Điều 12:
“4. Các tín chỉ tự chọn trong chương trình đào tạo trình độ đại học phải có tối thiểu
9 tín chỉ (3 học phần tự chọn ngành/chuyên ngành), được phân bố vào tất cả các học kỳ,
tối thiểu bắt đầu từ học kỳ 6.”.
b) Sửa đổi, bổ sung khoản 5 Điều 12:
“5. Chương trình đào tạo trình độ đại học cần có tối thiểu 7 tín chỉ các học phần
thực hành (bao gồm thí nghiệm và đồ án, không bao gồm khối kiến thức tốt nghiệp) là các
học phần bắt buộc, có tối thiểu 9 tín chỉ tự chọn tự do (đối với khóa 2025 về trước) và học
kỳ thực tập doanh nghiệp (đối với khóa 2026 về sau); Đối với chương trình PFIEV , cần
thiết kế thêm tối thiểu 6 tín chỉ ở học phần bắt buộc dưới dạng đồ án định hướng công
nghiệp.”.
8. Sửa đổi, bổ sung Điều 16 như sau:
a) Sửa đổi, bổ sung khoản 1 Điều 16:
“1. Hội đồng ngành là tổ chức chuyên môn tập hợp các giảng viên, chuyên gia trong
ngành có học hàm học vị cao, uy tín, có nhiều kinh nghiệm giảng dạy và quản lý giảng dạy
với chức năng tổ chức xây dựng, rà soát và cập nhật chương trình đào tạo của ngành theo
chuẩn mực chất lượng của văn bằng được cấp. Hội đồng ngành được thành lập cho từng
ngành đào tạo , bao gồm tất cả các trình độ đào tạo . Trong trường hợp có các ngành gần
cùng trình độ đào tạo; hoặc các ngành gần nhưng có sự khác nhau về tên giữa các trình độ
đào tạo thì chỉ thành lập một hội đồng ngành chung và đặt tên ghép hoặc tên chung mang
tính bao hàm. Hội đồng ngành có tối thiểu 07 thành viên và tối đa 15 thành viên (không
bao gồm thư ký hành ch ính), có số thành viên là số lẻ , trong đó phải có sự tham gia của
các Chủ trì ngành đại diện cho các trình độ đào tạo có liên quan. Hội đồng ngành do Trưởng
khoa quản lý ngành đề cử, Hiệu trưởng quyết định thành lập và chịu sự quản lý trực tiếp
của khoa quản lý ngành. Đối với các ngành liên ngành, Hội đồng ngành liên ngành do
Trưởng các khoa quản lý các ngành liên quan đề cử, Hiệu trưởng quyết định thành lập và
chịu sự quản lý trực tiếp của các khoa quản lý ngành.”.
b) Sửa đổi, bổ sung khoản 4 Điều 16:
“4. Nhiệm vụ của Chủ nhiệm Hội đồng ngành:
a) Chủ trì chuẩn bị hồ sơ, tài liệu, văn bản cần thiết và tổ chức các cuộc họp của
Hội đồng ngành; báo cáo Hội đồng khoa học và đào tạo của khoa về công tác xây dựng, rà
soát và cập nhật chương trình đào tạo của ngành, chuyên ngành;
b) Trao đổi với Trưởng khoa (hoặc Trưởng các khoa liên quan đối với ngành liên
ngành, sau đây gọi tắt là Trưởng khoa) hoặc giảng viên phụ trách học phần (nếu có) trong
việc phân bổ nội dung học phần trong chương trình đào tạo, tổ chức thảo luận, thống nhất
trong Hội đồng ngành để trình cấp có thẩm quyền phê duyệt;
c) Tham mưu cho Trưởng khoa trong việc phân công giảng viên giảng dạy các học
phần trong chương trình đào tạo, tham mưu việc xét duyệt đề tài và phân công khối lượng
hướng dẫn khóa luận tốt nghiệp hay luận văn thạc sĩ theo quy định;
d) Báo cáo định kỳ Hội đồng khoa học và đào tạo của khoa về tình hình tổ chức,
vận hành chương trình đào tạo của ngành, chuyên ngành;
e) Tổng hợp báo cáo của các Chủ trì ngành theo từng trình độ đào tạo và báo cáo
Trưởng khoa để xem xét, chỉ đạo;
f) Tham mưu cho Trưởng khoa trong việc mời giảng viên thỉnh giảng.”.
9. Bổ sung Điều 16a sau Điều 16 như sau:
“ Điều 16a. Chủ trì ngành
a) Chủ trì xây dựng và tổ chức triển khai chương trình đào tạo của ngành, chuyên
ngành;
b) Rà soát định kỳ chương trình đào tạo; báo cáo Hội đồng ngành để xem xét quyết
định việc điều chỉnh hoặc xây dựng mới chương trình đào tạo;
c) Tham mưu cho Hội đồng ngành trong việc phân công giảng viên giảng dạy các học
phần thuộc chương trình đào tạo, tham mưu việc xét duyệt đề tài và phân công khối lượng
hướng dẫn khóa luận tốt nghiệp hoặc luận văn thạc sĩ theo quy định;
d) Tham mưu cho Trưởng khoa trong việc phân công giảng viên làm Trưởng nhóm
môn học để chịu trách nhiệm chủ trì việc thống nhất nội dung giảng dạy của môn học theo
từng học kỳ, tổ chức ra đề thi và thực hiện thẩm định đề thi theo quy định;
e) Đề xuất danh sách thành viên các hội đồng chấm đồ án, khóa luận , luận văn,
luận án… để Hội đồng ngành tham mưu Trưởng khoa xem xét, quyết định;
f) Báo cáo định kỳ Hội đồng ngành về tình hình triển khai và vận hành chương trình
đào tạo của ngành, chuyên ngành; đề xuất các giải pháp điều chỉnh, cải tiến khi cần thiết.”.
10. Thay thế Phụ lục III như sau:
“ PHỤ LỤC III
PHÂN BỐ CÁC HỌC PHẦN TRÌNH ĐỘ THẠC SĨ:
Học
kỳ
Học phần
Thạc sĩ ứng dụng Thạc sĩ nghiên cứu
Thạc sĩ nghiên cứu
chuyên sâu
1.
Triết học (3 TC) Triết học (3 TC) Triết học (3 TC)
Cơ sở ngành (12 TC) Cơ sở ngành (12 TC)
Phương pháp nghiên cứu
khoa học (3 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 1
+ Báo cáo khoa học
(9 TC)
2.
Tự chọn đa ngành, tổng
quát (3 TC)
Phương pháp nghiên cứu
khoa học (3 TC) Luận văn thạc sĩ nghiên cứu chuyên sâu – phần 2
+ Báo cáo khoa học
(15 TC) Ngành/ Chuyên ngành
bắt buộc (12 TC)
Ngành/ Chuyên ngành
(12 TC)
3.
Ngành/ Chuyên ngành tự
chọn (9 TC)
Chuyên đề nghiên cứu
trước luận văn (15 TC)
Thực tập (6 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 3
+ Báo cáo khoa học
(15 TC)
4.
Ngành/ Chuyên ngành tự
chọn (3 TC) Luận văn thạc sĩ nghiên
cứu + Báo cáo khoa học
(15 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 4
+ Báo cáo khoa học
(15 TC)
Tự chọn đa ngành, tổng
quát (3 TC)
Đề án tốt nghiệp (9 TC)
”.
11. Sửa đổi mục 2.2 Thạc sĩ nghiên cứu của Phụ lục V – Cấu trúc chi tiết chương
trình đào tạo các trình độ như sau:
“ 2.2 Thạc sĩ nghiên cứu
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ NGHIÊN CỨU
Khối kiến thức Số môn Số tín chỉ
A. Đa ngành, tổng quát (General Multidisciplinary Courses) 6
Triết học (Philosophy) 3
Phương pháp nghiên cứu khoa học (Scientific Research Methodology) 3
Anh văn 1 (English 1) 0
Anh văn 2 (English 2) 0
B. Cơ sở ngành (Foundation Courses) 12
B.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
B.2 Tự chọn cơ sở ngành (Elective Foundation Courses)
…
C. Ngành/ Chuyên ngành (Major/ Speciality Courses) 12
C.1 Ngành/ Chuyên ngành bắt buộc (Compulsory Major/ Speciality Courses)
…
C.2 Ngành/ Chuyên ngành tự chọn (Elective Major/ Speciality Courses)
…
D. Học phần tốt nghiệp (Graduation Module) 30
Chuyên đề nghiên cứu trước luận văn
(Pre – Thesis Research Project)
15
Luận văn thạc sĩ (Master’s Thesis) 15
E. Điều kiện tốt nghiệp (Other Graduation Requirements)
ENG_B2
Tổng tín chỉ 60
”.
12. Bổ sung vào bước 6, khoản 1.1, mục 1 (Xây dựng chương trình đào tạo mới)
của Phụ lục VI: Quy trình xây dựng, thẩm định, cập nhật và ban hành chương trình đào tạo
trình độ đại học, thạc sĩ, tiến sĩ như sau:
“Bước 6: Tổ chức hội thảo lấy ý kiến của giảng viên, đội ngũ quản lý trong và ngoài
trường, các nhà khoa học, đại diện đơn vị sử dụng lao động liên quan và người đã tốt nghiệp
(nếu có) về CTĐT. Yêu cầu có Biên bản họp của Hội đồng ngành và Hội đồng Khoa học
và đào tạo của khoa về việc thông qua nội dung chương trình đào tạo là căn cứ để hoàn
thiện hồ sơ và trình phê duyệt chương trình đào tạo.”.
13. Bổ sung Phụ lục XI như sau:
“ PHỤ LỤC XI:
Cấu trúc chi tiết chương trình đào tạo các trình độ từ khóa 2026
1. Trình độ đại học
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC
CÁC NGÀNH KỸ THUẬT VÀ KIẾN TRÚC
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and Basic
Sciences) 30
A.1 Toán (Mathematics) Tối thiểu 11
…
A.2. Khoa học tự nhiên (Basic Sciences) Tối thiểu 5
…
B. Giáo dục chung (General Education) 30
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Quản lý / Khởi nghiệp (Management/ Entrepreneurship Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 8
Anh văn 1 (English 1)
Anh văn 2 (English 2)
Anh văn 3 (English 3)
Anh văn 4 (English 4)
B.6
Kiến thức và kỹ năng bổ trợ (Supplementary
Knowledge and Skills) Dành cho các môn kỹ
năng mềm, tiếng Nhật, văn hoá Nhật ...
B.6.1 Kỹ năng bổ trợ (Supplementary Skills) : áp dụng từ khóa 2025 chương trình tiêu chuẩn 1 0
…
B.6.2
Kỹ năng bổ trợ (Supplementary Skills) : áp
dụng từ khóa 2025 cho các chương trình: Dạy
và học bằng tiếng Anh; Tiên tiến; Định hướng
Nhật bản; Chuyển tiếp quốc tế; Liên kết cử
nhân kỹ thuật quốc tế
4 0
…
B.6.3
Tiếng Nhật (Japaneses) áp dụng cho các
chương trình: Định hướng Nhật Bản và
Chuyển tiếp quốc tế Nhật Bản
8 0
…
B.6.4 Văn hóa Nhật (Japanese Culture) áp dụng cho Chương trình Định hướng Nhật Bản 1 0
…
C. Cơ sở ngành (Foundation Courses) 18–34
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành ( Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality Courses) 17–37
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses)
D2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc c huyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 17
…
…
F. Giáo dục Quốc phòng – An ninh (National Defense
and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GC
…
Tổng tín chỉ 128–132
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC
CÁC NGÀNH QUẢN LÝ
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and Basic
Sciences) 12
A.1 Toán (Mathematics) 9
…
A.2. Khoa học tự nhiên (Basic Sciences) 3
…
B. Giáo dục chung (General Education) 30
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Kỹ thuật ngoài ngành ( Non – management Technical Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 8
Anh văn 1 (English 1)
Anh văn 2 (English 2)
Anh văn 3 (English 3)
Anh văn 4 (English 4)
B.6 Kiến thức và kỹ năng bổ trợ (Supplementary Knowledge and Skills) 0
B.6.1 Kỹ năng bổ trợ (Supplementary Skills) : áp dụng từ khóa 2025 chương trình tiêu chuẩn 1 0
…
B.6.2
Kỹ năng bổ trợ (Supplementary Skills) : áp
dụng từ khóa 2025 cho các chương trình: Dạy
và học bằng tiếng Anh; Chuyển tiếp quốc tế
4 0
…
C. Cơ sở ngành (Foundation Courses) 18–34
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành ( Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality Courses) 35–55
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses)
D.2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc c huyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 17
…
…
F. Giáo dục Quốc phòng – An ninh (National Defense
and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục Thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GC
…
Tổng tín chỉ 128–132
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO PFIEV
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and
Basic Sciences) 36
A.1 Toán (Mathematics) 21
…
A.2. Khoa học tự nhiên (Basic Sciences) 15
…
B. Giáo dục chung (General Education) 42
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Quản lý/ Khởi nghiệp (Management/ Entrepreneurship Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 20
B5.1 Anh văn (English) 8
B5.2 Pháp văn (French) 12
B.6 Kiến thức và kỹ năng bổ trợ (Supplementary Knowledge and Skills) áp dụng từ khóa 2025 1 0
…
C. Cơ sở ngành (Foundation Courses) 16–32
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành (Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality
Courses) 22–43
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses )
D.2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc chuyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 26
…
…
…
…
F. Giáo dục Quốc phòng – An ninh (National
Defense and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục Thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GT_700
FRA_GC
Tổng tín chỉ 158–163
”.

</details>

<details><summary>Source `HCMUT_GVCN2977_Dieu_15` — Điều 15. Vai trò và nhiệm vụ</summary>

Điều 15. Vai trò và nhiệm vụ
1. Giải thích cho người học về chương trình đào tạo, kế hoạch giảng dạy của ngành.
2. Cố vấn cho người học khi học có nhu cầu học vượt, học chậm tiến độ.
3. Tư vấn cho người học định hướng về ngành, ngành chính - phụ, ngành thứ hai, các
vấn đề có thể xảy ra khi chuyển khóa, chuyển ngành.
4. Tư vấn cho người học về các tín chỉ tự chọn tự do.
5. Tư vấn cho người học về các học phần tương đương, thay thế, các học phần của
chương trình liên thông Đại học - Thạc sĩ, Cử nhân - Kỹ sư.
6. Tư vấn cho người học về các nội dung khác liên quan đến chương trình đào tạo.

</details>


---

## 29. `f205bbbc5cd4bfa17653ae41`

**Question:** Theo Quy định về công tác GVCN và CVHT, cố vấn học tập có nhiệm vụ gì liên quan đến tín chỉ tự chọn tự do, và theo Quyết định 1862/QĐ-ĐHBK sửa đổi, chương trình đào tạo trình độ đại học khóa 2025 về trước cần có tối thiểu bao nhiêu tín chỉ tự chọn tự do?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** CVHT tư vấn cho người học về các tín chỉ tự chọn tự do (Điều 15 khoản 4 Quy định GVCN và CVHT); chương trình đào tạo trình độ đại học khóa 2025 về trước cần có tối thiểu 9 tín chỉ tự chọn tự do (khoản 5 Điều 12 được sửa đổi).

**Reference evidence:**
- `HCMUT_GVCN2977_Dieu_15`: Tư vấn cho người học về các tín chỉ tự chọn tự do.
- `HCMUT_CTDT1862_Dieu_1`: có tối thiểu 9 tín chỉ tự chọn tự do (đối với khóa 2025 về trước)

**Candidate behaviour:** refused

**Candidate answer:**

> Không có tài liệu trong cơ sở dữ liệu đã nạp (HCMUT_QCDT_*) liên quan đến Quy định GVCN và CVHT, Quyết định 1862/QĐ-ĐHBK hoặc yêu cầu tín chỉ tự chọn tự do cho khóa 2025. Các thông tin này nằm ngoài phạm vi quy định học vụ theo dữ liệu đã nạp.

<details><summary>Source `HCMUT_CTDT1862_Dieu_1` — Điều 1. Sửa đổi, bổ sung một số điều của Quy định cấu trúc và quy trình xây dựng,</summary>

Điều 1. Sửa đổi, bổ sung một số điều của Quy định cấu trúc và quy trình xây dựng,
thẩm định, điều chỉnh chương trình đào tạo; quy trình mở ngành đào tạo trình độ đại học,
thạc sĩ, tiến sĩ ban hành kèm theo Quyết định số 3538/QĐ-ĐHBK ngày 11 tháng 9 năm 2025
của Hiệu trưởng trường Đại học Bách khoa, Đại học Quốc gia Thành phố Hồ Chí Minh
1. Sửa đổi, bổ sung Điều 2 như sau:
a) Sửa đổi, bổ sung điểm b khoản 2 Điều 2:
“b) Học phần được tổ chức dưới dạng lý thuyết bao gồm giảng dạy lý thuyết và thực
hành (thảo luận, thực hành tại lớp, thí nghiệm, bài tập lớn, kiến tập), trong đó phần thực
hành chiếm tối thiểu 20% khối lượng tín chỉ học phần; hoặc dưới dạng thực hành (thí
nghiệm, thực hành, thực tập, thực tập ngoài trường/doanh nghiệp); hoặc dưới dạng đồ án
(đồ án, đồ án chuyên ngành, đồ án/khóa luận tốt nghiệp, chuyên đề/đề án/luận văn thạc sĩ,
tiểu luận/chuyên đề/luận án tiến sĩ.”.
b) Sửa đổi, bổ sung điểm e khoản 3 Điều 2:
“e) Cấp độ năm là các học phần ở chương trình chuyên sâu đặc thù, bao gồm cả giai
đoạn chuyên sâu kỹ sư của chương trình đào tạo Kỹ sư Chất lượng cao tại Việt Nam (viết
tắt là PFIEV) (người học từ năm thứ năm), trình độ thạc sĩ và tiến sĩ, ngoại trừ các học
phần nêu trong điểm f và g trong khoản này;”.
2. Bổ sung khoản 5 Điều 3 như sau:
“5. Chương trình tích hợp: Đại học – Thạc sĩ, Thạc sĩ – Tiến sĩ là các chương trình
đào tạo liên tục giữa hai trình độ học tập , nhằm rút ngắn thời gian học hoặc kết hợp khung
kiến thức, tín chỉ của hai trình độ liên tiếp. Người học được cấp bằng tương ứng với trình
độ đã hoàn thành.”.
3. Thay thế Điều 6 như sau:
“Điều 6. Cấu trúc của chương trình đào tạo đại học
1. Các ngành kỹ thuật và kiến trúc theo khung của tiêu chuẩn kiểm định ABET và
của một số tổ chức kiểm định quốc tế:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 30
1. Toán tối thiểu 11
2. Khoa học tự nhiên tối thiểu 5
Giáo dục chung 30
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 8
Cơ sở ngành/ Ngành/ Chuyên ngành 68–72
1. Cơ sở ngành 18–34
2. Ngành/ Chuyên ngành
34–54
3. Tốt nghiệp trình độ đại học
Tổng tín chỉ 128–132
2. Các ngành quản lý theo khung của tiêu chuẩn kiểm định FIBAA:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 12
1. Toán quản lý 9
2. Khoa học tự nhiên 3
Giáo dục chung 30
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 8
Cơ sở ngành/ Ngành/ Chuyên ngành 86–90
1. Cơ sở ngành 18–34
2. Ngành/ Chuyên ngành
52–72
3. Tốt nghiệp trình độ đại học
Tổng tín chỉ 128–132
”.
4. Thay thế Điều 7 như sau:
“ Điều 7. Cấu trúc của chương trình đào tạo PFIEV
1. Xét theo giai đoạn:
Giai đoạn Số tín chỉ
Tổng tín chỉ 158–163
1.
Giai đoạn 1
(bao gồm 8 tín chỉ tiếng Anh và 8 tín chỉ tiếng Pháp)
66
2.
Giai đoạn 2
(bao gồm 4 tín chỉ tiếng Pháp)
92–97
2. Xét theo khối kiến thức:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 36
1. Toán 21
2. Khoa học tự nhiên 15
Giáo dục chung 42
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 20
Cơ sở ngành/ Ngành/ Chuyên ngành 80–85
1. Cơ sở ngành 16–32
2. Ngành/ Chuyên ngành
48–69
3. Tốt nghiệp chương trình PFIEV
Tổng tín chỉ 158–163
”.
5. Thay thế Điều 9 như sau:
“ Điều 9. Cấu trúc của chương trình đào tạo thạc sĩ
Khối kiến thức Thạc sĩ ứng dụng Thạc sĩ nghiên cứu Thạc sĩ nghiên cứu chuyên sâu
Đa ngành, tổng quát
1. Triết học 3 3 3
2. Tự chọn đa ngành, tổng quát 6 - -
3. Phương pháp nghiên cứu khoa học - 3 3
Cơ sở ngành/ Ngành
1. Cơ sở ngành 12 12 -
2. Ngành/ Chuyên ngành 24 12 -
Tốt nghiệp trình độ thạc sĩ
1. Thực tập 6 - -
2. Chuyên đề nghiên cứu trước luận văn - 15
3. Đề án tốt nghiệp/ Luận văn thạc sĩ 9
15
+ Báo cáo
khoa học
54
1×9
3×15
+ Báo cáo
khoa học
Tổng số tín chỉ 60 60 60
”.
6. Thay thế Điều 11 như sau:
“ Điều 11. Quy định thêm về khối kiến thức
Quy định tại Điều này áp dụng đối với các khối kiến thức quy định từ Điều 6
đến Điều 10.
Khối kiến thức Số tín chỉ Ghi chú
a) Giáo dục chung khác
1. Nhập môn 3 Kỹ thuật/ Điện toán/ Kiến trúc/ Quản lý
2.
Kiến thức quản lý/ Khởi nghiệp
Hoặc
Kiến thức kỹ thuật ngoài ngành đối
với các ngành quản lý
3
3.
Kiến thức về con người và môi
trường/ Kỹ năng nghề nghiệp
chuyên nghiệp
3
Các kiến thức về tác động của
ngành với con người, xã hội và
môi trường
b) Ngoại ngữ
1. Tiếng Anh 8
2. Tiếng Pháp 12 Chương trình PFIEV
c) Chuyên sâu đặc thù
Có thể dùng xét công nhận đạt các khối kiến thức chuyên ngành bắt buộc, khối kiến
thức chuyên ngành tự chọn và khối kiến thức thực tập trong chương trình thạc sĩ.
1. Học kỳ doanh nghiệp 15
d) Tốt nghiệp trình độ đại học từ khóa 2025 về trước
1. Thực tập ngoài trường 2 Học kỳ 6, có thể vận hành trong hè của năm 3
2. Đồ án chuyên ngành 2 Học kỳ 7
3. Đồ án/ Khóa luận tốt nghiệp 4 Học kỳ 8
e) Tốt nghiệp trình độ đại học từ khóa 2026
1. Học kỳ thực tập doanh nghiệp 11 Học kỳ 7
2. Đồ án/ Khóa luận tốt nghiệp 6 Học kỳ 8
f) Tốt nghiệp chương trình PFIEV
1. Thực tập công nhân 2 Học kỳ 4, có thể vận hành trong hè của năm 2
2. Thực tập ngoài trường 2 Học kỳ 6, có thể vận hành trong hè của năm 3
3. Học kỳ thực tập doanh nghiệp 13 Học kỳ 8 (có thể vận hành trong hè của năm 4) và học kỳ 9
4. Đồ án tốt nghiệp kỹ sư 9 Học kỳ 10
g) Tốt nghiệp trình độ thạc sĩ ứng dụng
1. Thực tập ngoài trường 6 Học kỳ 3
2. Đề án tốt nghiệp 9 Học kỳ 4
h) Tốt nghiệp trình độ thạc sĩ nghiên cứu
1. Chuyên đề nghiên cứu trước luận văn 15 Học kỳ 3
2. Luận văn thạc sĩ 15 Học kỳ 4
i) Tốt nghiệp trình độ thạc sĩ nghiên cứu chuyên sâu
1.
Luận văn thạc sĩ nghiên cứu
chuyên sâu
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 1
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 2
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 3
54
9
15
15
15
Học kỳ 1
Học kỳ 2
Học kỳ 3
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 4 Học kỳ 4
j) Tốt nghiệp trình độ tiến sĩ – Phương thức 1
1.
Luận án tiến sĩ
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận án tiến sĩ – chuẩn bị
Luận án tiến sĩ – phần 1
Luận án tiến sĩ – phần 2
Luận án tiến sĩ – phần 3
Luận án tiến sĩ – phần 4
Luận án tiến sĩ – phần 5
87
12
15
15
15
15
15
Học kỳ 1
Học kỳ 2
Học kỳ 3
Học kỳ 4
Học kỳ 5
Học kỳ 6
k) Tốt nghiệp trình độ tiến sĩ – Phương thức 2
1.
Luận án tiến sĩ
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận án tiến sĩ – phần 1
Luận án tiến sĩ – phần 2
Luận án tiến sĩ – phần 3
Luận án tiến sĩ – phần 4
Luận án tiến sĩ – phần 5
75
15
15
15
15
15
Học kỳ 2
Học kỳ 3
Học kỳ 4
Học kỳ 5
Học kỳ 6
Ghi chú:
(†): Các phần học thành phần dùng để bố trí đăng ký học phần trên thời khóa biểu, tính học
phí và tính khối lượng giảng dạy, không in vào Phụ lục bằng tốt nghiệp.”.
7. Sửa đổi, bổ sung Điều 12 như sau:
a) Sửa đổi, bổ sung khoản 4 Điều 12:
“4. Các tín chỉ tự chọn trong chương trình đào tạo trình độ đại học phải có tối thiểu
9 tín chỉ (3 học phần tự chọn ngành/chuyên ngành), được phân bố vào tất cả các học kỳ,
tối thiểu bắt đầu từ học kỳ 6.”.
b) Sửa đổi, bổ sung khoản 5 Điều 12:
“5. Chương trình đào tạo trình độ đại học cần có tối thiểu 7 tín chỉ các học phần
thực hành (bao gồm thí nghiệm và đồ án, không bao gồm khối kiến thức tốt nghiệp) là các
học phần bắt buộc, có tối thiểu 9 tín chỉ tự chọn tự do (đối với khóa 2025 về trước) và học
kỳ thực tập doanh nghiệp (đối với khóa 2026 về sau); Đối với chương trình PFIEV , cần
thiết kế thêm tối thiểu 6 tín chỉ ở học phần bắt buộc dưới dạng đồ án định hướng công
nghiệp.”.
8. Sửa đổi, bổ sung Điều 16 như sau:
a) Sửa đổi, bổ sung khoản 1 Điều 16:
“1. Hội đồng ngành là tổ chức chuyên môn tập hợp các giảng viên, chuyên gia trong
ngành có học hàm học vị cao, uy tín, có nhiều kinh nghiệm giảng dạy và quản lý giảng dạy
với chức năng tổ chức xây dựng, rà soát và cập nhật chương trình đào tạo của ngành theo
chuẩn mực chất lượng của văn bằng được cấp. Hội đồng ngành được thành lập cho từng
ngành đào tạo , bao gồm tất cả các trình độ đào tạo . Trong trường hợp có các ngành gần
cùng trình độ đào tạo; hoặc các ngành gần nhưng có sự khác nhau về tên giữa các trình độ
đào tạo thì chỉ thành lập một hội đồng ngành chung và đặt tên ghép hoặc tên chung mang
tính bao hàm. Hội đồng ngành có tối thiểu 07 thành viên và tối đa 15 thành viên (không
bao gồm thư ký hành ch ính), có số thành viên là số lẻ , trong đó phải có sự tham gia của
các Chủ trì ngành đại diện cho các trình độ đào tạo có liên quan. Hội đồng ngành do Trưởng
khoa quản lý ngành đề cử, Hiệu trưởng quyết định thành lập và chịu sự quản lý trực tiếp
của khoa quản lý ngành. Đối với các ngành liên ngành, Hội đồng ngành liên ngành do
Trưởng các khoa quản lý các ngành liên quan đề cử, Hiệu trưởng quyết định thành lập và
chịu sự quản lý trực tiếp của các khoa quản lý ngành.”.
b) Sửa đổi, bổ sung khoản 4 Điều 16:
“4. Nhiệm vụ của Chủ nhiệm Hội đồng ngành:
a) Chủ trì chuẩn bị hồ sơ, tài liệu, văn bản cần thiết và tổ chức các cuộc họp của
Hội đồng ngành; báo cáo Hội đồng khoa học và đào tạo của khoa về công tác xây dựng, rà
soát và cập nhật chương trình đào tạo của ngành, chuyên ngành;
b) Trao đổi với Trưởng khoa (hoặc Trưởng các khoa liên quan đối với ngành liên
ngành, sau đây gọi tắt là Trưởng khoa) hoặc giảng viên phụ trách học phần (nếu có) trong
việc phân bổ nội dung học phần trong chương trình đào tạo, tổ chức thảo luận, thống nhất
trong Hội đồng ngành để trình cấp có thẩm quyền phê duyệt;
c) Tham mưu cho Trưởng khoa trong việc phân công giảng viên giảng dạy các học
phần trong chương trình đào tạo, tham mưu việc xét duyệt đề tài và phân công khối lượng
hướng dẫn khóa luận tốt nghiệp hay luận văn thạc sĩ theo quy định;
d) Báo cáo định kỳ Hội đồng khoa học và đào tạo của khoa về tình hình tổ chức,
vận hành chương trình đào tạo của ngành, chuyên ngành;
e) Tổng hợp báo cáo của các Chủ trì ngành theo từng trình độ đào tạo và báo cáo
Trưởng khoa để xem xét, chỉ đạo;
f) Tham mưu cho Trưởng khoa trong việc mời giảng viên thỉnh giảng.”.
9. Bổ sung Điều 16a sau Điều 16 như sau:
“ Điều 16a. Chủ trì ngành
a) Chủ trì xây dựng và tổ chức triển khai chương trình đào tạo của ngành, chuyên
ngành;
b) Rà soát định kỳ chương trình đào tạo; báo cáo Hội đồng ngành để xem xét quyết
định việc điều chỉnh hoặc xây dựng mới chương trình đào tạo;
c) Tham mưu cho Hội đồng ngành trong việc phân công giảng viên giảng dạy các học
phần thuộc chương trình đào tạo, tham mưu việc xét duyệt đề tài và phân công khối lượng
hướng dẫn khóa luận tốt nghiệp hoặc luận văn thạc sĩ theo quy định;
d) Tham mưu cho Trưởng khoa trong việc phân công giảng viên làm Trưởng nhóm
môn học để chịu trách nhiệm chủ trì việc thống nhất nội dung giảng dạy của môn học theo
từng học kỳ, tổ chức ra đề thi và thực hiện thẩm định đề thi theo quy định;
e) Đề xuất danh sách thành viên các hội đồng chấm đồ án, khóa luận , luận văn,
luận án… để Hội đồng ngành tham mưu Trưởng khoa xem xét, quyết định;
f) Báo cáo định kỳ Hội đồng ngành về tình hình triển khai và vận hành chương trình
đào tạo của ngành, chuyên ngành; đề xuất các giải pháp điều chỉnh, cải tiến khi cần thiết.”.
10. Thay thế Phụ lục III như sau:
“ PHỤ LỤC III
PHÂN BỐ CÁC HỌC PHẦN TRÌNH ĐỘ THẠC SĨ:
Học
kỳ
Học phần
Thạc sĩ ứng dụng Thạc sĩ nghiên cứu
Thạc sĩ nghiên cứu
chuyên sâu
1.
Triết học (3 TC) Triết học (3 TC) Triết học (3 TC)
Cơ sở ngành (12 TC) Cơ sở ngành (12 TC)
Phương pháp nghiên cứu
khoa học (3 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 1
+ Báo cáo khoa học
(9 TC)
2.
Tự chọn đa ngành, tổng
quát (3 TC)
Phương pháp nghiên cứu
khoa học (3 TC) Luận văn thạc sĩ nghiên cứu chuyên sâu – phần 2
+ Báo cáo khoa học
(15 TC) Ngành/ Chuyên ngành
bắt buộc (12 TC)
Ngành/ Chuyên ngành
(12 TC)
3.
Ngành/ Chuyên ngành tự
chọn (9 TC)
Chuyên đề nghiên cứu
trước luận văn (15 TC)
Thực tập (6 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 3
+ Báo cáo khoa học
(15 TC)
4.
Ngành/ Chuyên ngành tự
chọn (3 TC) Luận văn thạc sĩ nghiên
cứu + Báo cáo khoa học
(15 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 4
+ Báo cáo khoa học
(15 TC)
Tự chọn đa ngành, tổng
quát (3 TC)
Đề án tốt nghiệp (9 TC)
”.
11. Sửa đổi mục 2.2 Thạc sĩ nghiên cứu của Phụ lục V – Cấu trúc chi tiết chương
trình đào tạo các trình độ như sau:
“ 2.2 Thạc sĩ nghiên cứu
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ NGHIÊN CỨU
Khối kiến thức Số môn Số tín chỉ
A. Đa ngành, tổng quát (General Multidisciplinary Courses) 6
Triết học (Philosophy) 3
Phương pháp nghiên cứu khoa học (Scientific Research Methodology) 3
Anh văn 1 (English 1) 0
Anh văn 2 (English 2) 0
B. Cơ sở ngành (Foundation Courses) 12
B.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
B.2 Tự chọn cơ sở ngành (Elective Foundation Courses)
…
C. Ngành/ Chuyên ngành (Major/ Speciality Courses) 12
C.1 Ngành/ Chuyên ngành bắt buộc (Compulsory Major/ Speciality Courses)
…
C.2 Ngành/ Chuyên ngành tự chọn (Elective Major/ Speciality Courses)
…
D. Học phần tốt nghiệp (Graduation Module) 30
Chuyên đề nghiên cứu trước luận văn
(Pre – Thesis Research Project)
15
Luận văn thạc sĩ (Master’s Thesis) 15
E. Điều kiện tốt nghiệp (Other Graduation Requirements)
ENG_B2
Tổng tín chỉ 60
”.
12. Bổ sung vào bước 6, khoản 1.1, mục 1 (Xây dựng chương trình đào tạo mới)
của Phụ lục VI: Quy trình xây dựng, thẩm định, cập nhật và ban hành chương trình đào tạo
trình độ đại học, thạc sĩ, tiến sĩ như sau:
“Bước 6: Tổ chức hội thảo lấy ý kiến của giảng viên, đội ngũ quản lý trong và ngoài
trường, các nhà khoa học, đại diện đơn vị sử dụng lao động liên quan và người đã tốt nghiệp
(nếu có) về CTĐT. Yêu cầu có Biên bản họp của Hội đồng ngành và Hội đồng Khoa học
và đào tạo của khoa về việc thông qua nội dung chương trình đào tạo là căn cứ để hoàn
thiện hồ sơ và trình phê duyệt chương trình đào tạo.”.
13. Bổ sung Phụ lục XI như sau:
“ PHỤ LỤC XI:
Cấu trúc chi tiết chương trình đào tạo các trình độ từ khóa 2026
1. Trình độ đại học
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC
CÁC NGÀNH KỸ THUẬT VÀ KIẾN TRÚC
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and Basic
Sciences) 30
A.1 Toán (Mathematics) Tối thiểu 11
…
A.2. Khoa học tự nhiên (Basic Sciences) Tối thiểu 5
…
B. Giáo dục chung (General Education) 30
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Quản lý / Khởi nghiệp (Management/ Entrepreneurship Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 8
Anh văn 1 (English 1)
Anh văn 2 (English 2)
Anh văn 3 (English 3)
Anh văn 4 (English 4)
B.6
Kiến thức và kỹ năng bổ trợ (Supplementary
Knowledge and Skills) Dành cho các môn kỹ
năng mềm, tiếng Nhật, văn hoá Nhật ...
B.6.1 Kỹ năng bổ trợ (Supplementary Skills) : áp dụng từ khóa 2025 chương trình tiêu chuẩn 1 0
…
B.6.2
Kỹ năng bổ trợ (Supplementary Skills) : áp
dụng từ khóa 2025 cho các chương trình: Dạy
và học bằng tiếng Anh; Tiên tiến; Định hướng
Nhật bản; Chuyển tiếp quốc tế; Liên kết cử
nhân kỹ thuật quốc tế
4 0
…
B.6.3
Tiếng Nhật (Japaneses) áp dụng cho các
chương trình: Định hướng Nhật Bản và
Chuyển tiếp quốc tế Nhật Bản
8 0
…
B.6.4 Văn hóa Nhật (Japanese Culture) áp dụng cho Chương trình Định hướng Nhật Bản 1 0
…
C. Cơ sở ngành (Foundation Courses) 18–34
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành ( Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality Courses) 17–37
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses)
D2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc c huyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 17
…
…
F. Giáo dục Quốc phòng – An ninh (National Defense
and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GC
…
Tổng tín chỉ 128–132
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC
CÁC NGÀNH QUẢN LÝ
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and Basic
Sciences) 12
A.1 Toán (Mathematics) 9
…
A.2. Khoa học tự nhiên (Basic Sciences) 3
…
B. Giáo dục chung (General Education) 30
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Kỹ thuật ngoài ngành ( Non – management Technical Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 8
Anh văn 1 (English 1)
Anh văn 2 (English 2)
Anh văn 3 (English 3)
Anh văn 4 (English 4)
B.6 Kiến thức và kỹ năng bổ trợ (Supplementary Knowledge and Skills) 0
B.6.1 Kỹ năng bổ trợ (Supplementary Skills) : áp dụng từ khóa 2025 chương trình tiêu chuẩn 1 0
…
B.6.2
Kỹ năng bổ trợ (Supplementary Skills) : áp
dụng từ khóa 2025 cho các chương trình: Dạy
và học bằng tiếng Anh; Chuyển tiếp quốc tế
4 0
…
C. Cơ sở ngành (Foundation Courses) 18–34
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành ( Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality Courses) 35–55
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses)
D.2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc c huyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 17
…
…
F. Giáo dục Quốc phòng – An ninh (National Defense
and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục Thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GC
…
Tổng tín chỉ 128–132
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO PFIEV
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and
Basic Sciences) 36
A.1 Toán (Mathematics) 21
…
A.2. Khoa học tự nhiên (Basic Sciences) 15
…
B. Giáo dục chung (General Education) 42
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Quản lý/ Khởi nghiệp (Management/ Entrepreneurship Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 20
B5.1 Anh văn (English) 8
B5.2 Pháp văn (French) 12
B.6 Kiến thức và kỹ năng bổ trợ (Supplementary Knowledge and Skills) áp dụng từ khóa 2025 1 0
…
C. Cơ sở ngành (Foundation Courses) 16–32
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành (Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality
Courses) 22–43
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses )
D.2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc chuyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 26
…
…
…
…
F. Giáo dục Quốc phòng – An ninh (National
Defense and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục Thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GT_700
FRA_GC
Tổng tín chỉ 158–163
”.

</details>

<details><summary>Source `HCMUT_GVCN2977_Dieu_15` — Điều 15. Vai trò và nhiệm vụ</summary>

Điều 15. Vai trò và nhiệm vụ
1. Giải thích cho người học về chương trình đào tạo, kế hoạch giảng dạy của ngành.
2. Cố vấn cho người học khi học có nhu cầu học vượt, học chậm tiến độ.
3. Tư vấn cho người học định hướng về ngành, ngành chính - phụ, ngành thứ hai, các
vấn đề có thể xảy ra khi chuyển khóa, chuyển ngành.
4. Tư vấn cho người học về các tín chỉ tự chọn tự do.
5. Tư vấn cho người học về các học phần tương đương, thay thế, các học phần của
chương trình liên thông Đại học - Thạc sĩ, Cử nhân - Kỹ sư.
6. Tư vấn cho người học về các nội dung khác liên quan đến chương trình đào tạo.

</details>


---

## 30. `fe3d26aa28221f816af26634`

**Question:** Theo Quy định về công tác GVCN và CVHT, cố vấn học tập có nhiệm vụ gì liên quan đến tín chỉ tự chọn tự do, và theo Quyết định 1862/QĐ-ĐHBK sửa đổi, chương trình đào tạo trình độ đại học khóa 2025 về trước cần có tối thiểu bao nhiêu tín chỉ tự chọn tự do?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Quy chế và quy định học vụ - Trường Đại học Bách khoa, ĐHQG-HCM. Câu hỏi nằm ngoài phạm vi các văn bản quy chế, quy định học vụ của Trường Đại học Bách khoa - ĐHQG-HCM trong cơ sở dữ liệu đã nạp; không suy đoán, nêu rõ giới hạn và gợi ý người dùng liên hệ đơn vị phụ trách đào tạo của trường để được xác nhận chính thức.

**Reference answer:** CVHT tư vấn cho người học về các tín chỉ tự chọn tự do (Điều 15 khoản 4 Quy định GVCN và CVHT); chương trình đào tạo trình độ đại học khóa 2025 về trước cần có tối thiểu 9 tín chỉ tự chọn tự do (khoản 5 Điều 12 được sửa đổi).

**Reference evidence:**
- `HCMUT_GVCN2977_Dieu_15`: Tư vấn cho người học về các tín chỉ tự chọn tự do.
- `HCMUT_CTDT1862_Dieu_1`: có tối thiểu 9 tín chỉ tự chọn tự do (đối với khóa 2025 về trước)

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Quyết định 1862/QĐ-ĐHBK (Điều 12), chương trình đào tạo trình độ đại học khóa 2025 cần có tối thiểu 9 tín chỉ tự chọn tự do. Ngoài ra, điều này được quy định trong các khoản 4 và 5 của Điều 12.

**Candidate citations:** `HCMUT_CTDT1862_Dieu_1`, `HCMUT_GVCN2977_Dieu_15`

<details><summary>Source `HCMUT_CTDT1862_Dieu_1` — Điều 1. Sửa đổi, bổ sung một số điều của Quy định cấu trúc và quy trình xây dựng,</summary>

Điều 1. Sửa đổi, bổ sung một số điều của Quy định cấu trúc và quy trình xây dựng,
thẩm định, điều chỉnh chương trình đào tạo; quy trình mở ngành đào tạo trình độ đại học,
thạc sĩ, tiến sĩ ban hành kèm theo Quyết định số 3538/QĐ-ĐHBK ngày 11 tháng 9 năm 2025
của Hiệu trưởng trường Đại học Bách khoa, Đại học Quốc gia Thành phố Hồ Chí Minh
1. Sửa đổi, bổ sung Điều 2 như sau:
a) Sửa đổi, bổ sung điểm b khoản 2 Điều 2:
“b) Học phần được tổ chức dưới dạng lý thuyết bao gồm giảng dạy lý thuyết và thực
hành (thảo luận, thực hành tại lớp, thí nghiệm, bài tập lớn, kiến tập), trong đó phần thực
hành chiếm tối thiểu 20% khối lượng tín chỉ học phần; hoặc dưới dạng thực hành (thí
nghiệm, thực hành, thực tập, thực tập ngoài trường/doanh nghiệp); hoặc dưới dạng đồ án
(đồ án, đồ án chuyên ngành, đồ án/khóa luận tốt nghiệp, chuyên đề/đề án/luận văn thạc sĩ,
tiểu luận/chuyên đề/luận án tiến sĩ.”.
b) Sửa đổi, bổ sung điểm e khoản 3 Điều 2:
“e) Cấp độ năm là các học phần ở chương trình chuyên sâu đặc thù, bao gồm cả giai
đoạn chuyên sâu kỹ sư của chương trình đào tạo Kỹ sư Chất lượng cao tại Việt Nam (viết
tắt là PFIEV) (người học từ năm thứ năm), trình độ thạc sĩ và tiến sĩ, ngoại trừ các học
phần nêu trong điểm f và g trong khoản này;”.
2. Bổ sung khoản 5 Điều 3 như sau:
“5. Chương trình tích hợp: Đại học – Thạc sĩ, Thạc sĩ – Tiến sĩ là các chương trình
đào tạo liên tục giữa hai trình độ học tập , nhằm rút ngắn thời gian học hoặc kết hợp khung
kiến thức, tín chỉ của hai trình độ liên tiếp. Người học được cấp bằng tương ứng với trình
độ đã hoàn thành.”.
3. Thay thế Điều 6 như sau:
“Điều 6. Cấu trúc của chương trình đào tạo đại học
1. Các ngành kỹ thuật và kiến trúc theo khung của tiêu chuẩn kiểm định ABET và
của một số tổ chức kiểm định quốc tế:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 30
1. Toán tối thiểu 11
2. Khoa học tự nhiên tối thiểu 5
Giáo dục chung 30
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 8
Cơ sở ngành/ Ngành/ Chuyên ngành 68–72
1. Cơ sở ngành 18–34
2. Ngành/ Chuyên ngành
34–54
3. Tốt nghiệp trình độ đại học
Tổng tín chỉ 128–132
2. Các ngành quản lý theo khung của tiêu chuẩn kiểm định FIBAA:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 12
1. Toán quản lý 9
2. Khoa học tự nhiên 3
Giáo dục chung 30
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 8
Cơ sở ngành/ Ngành/ Chuyên ngành 86–90
1. Cơ sở ngành 18–34
2. Ngành/ Chuyên ngành
52–72
3. Tốt nghiệp trình độ đại học
Tổng tín chỉ 128–132
”.
4. Thay thế Điều 7 như sau:
“ Điều 7. Cấu trúc của chương trình đào tạo PFIEV
1. Xét theo giai đoạn:
Giai đoạn Số tín chỉ
Tổng tín chỉ 158–163
1.
Giai đoạn 1
(bao gồm 8 tín chỉ tiếng Anh và 8 tín chỉ tiếng Pháp)
66
2.
Giai đoạn 2
(bao gồm 4 tín chỉ tiếng Pháp)
92–97
2. Xét theo khối kiến thức:
Khối kiến thức Số tín chỉ
Toán và Khoa học tự nhiên 36
1. Toán 21
2. Khoa học tự nhiên 15
Giáo dục chung 42
1. Kinh tế – Chính trị – Xã hội – Luật 13
2. Giáo dục chung khác 9
3. Ngoại ngữ 20
Cơ sở ngành/ Ngành/ Chuyên ngành 80–85
1. Cơ sở ngành 16–32
2. Ngành/ Chuyên ngành
48–69
3. Tốt nghiệp chương trình PFIEV
Tổng tín chỉ 158–163
”.
5. Thay thế Điều 9 như sau:
“ Điều 9. Cấu trúc của chương trình đào tạo thạc sĩ
Khối kiến thức Thạc sĩ ứng dụng Thạc sĩ nghiên cứu Thạc sĩ nghiên cứu chuyên sâu
Đa ngành, tổng quát
1. Triết học 3 3 3
2. Tự chọn đa ngành, tổng quát 6 - -
3. Phương pháp nghiên cứu khoa học - 3 3
Cơ sở ngành/ Ngành
1. Cơ sở ngành 12 12 -
2. Ngành/ Chuyên ngành 24 12 -
Tốt nghiệp trình độ thạc sĩ
1. Thực tập 6 - -
2. Chuyên đề nghiên cứu trước luận văn - 15
3. Đề án tốt nghiệp/ Luận văn thạc sĩ 9
15
+ Báo cáo
khoa học
54
1×9
3×15
+ Báo cáo
khoa học
Tổng số tín chỉ 60 60 60
”.
6. Thay thế Điều 11 như sau:
“ Điều 11. Quy định thêm về khối kiến thức
Quy định tại Điều này áp dụng đối với các khối kiến thức quy định từ Điều 6
đến Điều 10.
Khối kiến thức Số tín chỉ Ghi chú
a) Giáo dục chung khác
1. Nhập môn 3 Kỹ thuật/ Điện toán/ Kiến trúc/ Quản lý
2.
Kiến thức quản lý/ Khởi nghiệp
Hoặc
Kiến thức kỹ thuật ngoài ngành đối
với các ngành quản lý
3
3.
Kiến thức về con người và môi
trường/ Kỹ năng nghề nghiệp
chuyên nghiệp
3
Các kiến thức về tác động của
ngành với con người, xã hội và
môi trường
b) Ngoại ngữ
1. Tiếng Anh 8
2. Tiếng Pháp 12 Chương trình PFIEV
c) Chuyên sâu đặc thù
Có thể dùng xét công nhận đạt các khối kiến thức chuyên ngành bắt buộc, khối kiến
thức chuyên ngành tự chọn và khối kiến thức thực tập trong chương trình thạc sĩ.
1. Học kỳ doanh nghiệp 15
d) Tốt nghiệp trình độ đại học từ khóa 2025 về trước
1. Thực tập ngoài trường 2 Học kỳ 6, có thể vận hành trong hè của năm 3
2. Đồ án chuyên ngành 2 Học kỳ 7
3. Đồ án/ Khóa luận tốt nghiệp 4 Học kỳ 8
e) Tốt nghiệp trình độ đại học từ khóa 2026
1. Học kỳ thực tập doanh nghiệp 11 Học kỳ 7
2. Đồ án/ Khóa luận tốt nghiệp 6 Học kỳ 8
f) Tốt nghiệp chương trình PFIEV
1. Thực tập công nhân 2 Học kỳ 4, có thể vận hành trong hè của năm 2
2. Thực tập ngoài trường 2 Học kỳ 6, có thể vận hành trong hè của năm 3
3. Học kỳ thực tập doanh nghiệp 13 Học kỳ 8 (có thể vận hành trong hè của năm 4) và học kỳ 9
4. Đồ án tốt nghiệp kỹ sư 9 Học kỳ 10
g) Tốt nghiệp trình độ thạc sĩ ứng dụng
1. Thực tập ngoài trường 6 Học kỳ 3
2. Đề án tốt nghiệp 9 Học kỳ 4
h) Tốt nghiệp trình độ thạc sĩ nghiên cứu
1. Chuyên đề nghiên cứu trước luận văn 15 Học kỳ 3
2. Luận văn thạc sĩ 15 Học kỳ 4
i) Tốt nghiệp trình độ thạc sĩ nghiên cứu chuyên sâu
1.
Luận văn thạc sĩ nghiên cứu
chuyên sâu
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 1
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 2
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 3
54
9
15
15
15
Học kỳ 1
Học kỳ 2
Học kỳ 3
Luận văn thạc sĩ nghiên cứu chuyên
sâu – phần 4 Học kỳ 4
j) Tốt nghiệp trình độ tiến sĩ – Phương thức 1
1.
Luận án tiến sĩ
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận án tiến sĩ – chuẩn bị
Luận án tiến sĩ – phần 1
Luận án tiến sĩ – phần 2
Luận án tiến sĩ – phần 3
Luận án tiến sĩ – phần 4
Luận án tiến sĩ – phần 5
87
12
15
15
15
15
15
Học kỳ 1
Học kỳ 2
Học kỳ 3
Học kỳ 4
Học kỳ 5
Học kỳ 6
k) Tốt nghiệp trình độ tiến sĩ – Phương thức 2
1.
Luận án tiến sĩ
Trong đó, bố trí các phần học qua
từng học kỳ như sau (†):
Luận án tiến sĩ – phần 1
Luận án tiến sĩ – phần 2
Luận án tiến sĩ – phần 3
Luận án tiến sĩ – phần 4
Luận án tiến sĩ – phần 5
75
15
15
15
15
15
Học kỳ 2
Học kỳ 3
Học kỳ 4
Học kỳ 5
Học kỳ 6
Ghi chú:
(†): Các phần học thành phần dùng để bố trí đăng ký học phần trên thời khóa biểu, tính học
phí và tính khối lượng giảng dạy, không in vào Phụ lục bằng tốt nghiệp.”.
7. Sửa đổi, bổ sung Điều 12 như sau:
a) Sửa đổi, bổ sung khoản 4 Điều 12:
“4. Các tín chỉ tự chọn trong chương trình đào tạo trình độ đại học phải có tối thiểu
9 tín chỉ (3 học phần tự chọn ngành/chuyên ngành), được phân bố vào tất cả các học kỳ,
tối thiểu bắt đầu từ học kỳ 6.”.
b) Sửa đổi, bổ sung khoản 5 Điều 12:
“5. Chương trình đào tạo trình độ đại học cần có tối thiểu 7 tín chỉ các học phần
thực hành (bao gồm thí nghiệm và đồ án, không bao gồm khối kiến thức tốt nghiệp) là các
học phần bắt buộc, có tối thiểu 9 tín chỉ tự chọn tự do (đối với khóa 2025 về trước) và học
kỳ thực tập doanh nghiệp (đối với khóa 2026 về sau); Đối với chương trình PFIEV , cần
thiết kế thêm tối thiểu 6 tín chỉ ở học phần bắt buộc dưới dạng đồ án định hướng công
nghiệp.”.
8. Sửa đổi, bổ sung Điều 16 như sau:
a) Sửa đổi, bổ sung khoản 1 Điều 16:
“1. Hội đồng ngành là tổ chức chuyên môn tập hợp các giảng viên, chuyên gia trong
ngành có học hàm học vị cao, uy tín, có nhiều kinh nghiệm giảng dạy và quản lý giảng dạy
với chức năng tổ chức xây dựng, rà soát và cập nhật chương trình đào tạo của ngành theo
chuẩn mực chất lượng của văn bằng được cấp. Hội đồng ngành được thành lập cho từng
ngành đào tạo , bao gồm tất cả các trình độ đào tạo . Trong trường hợp có các ngành gần
cùng trình độ đào tạo; hoặc các ngành gần nhưng có sự khác nhau về tên giữa các trình độ
đào tạo thì chỉ thành lập một hội đồng ngành chung và đặt tên ghép hoặc tên chung mang
tính bao hàm. Hội đồng ngành có tối thiểu 07 thành viên và tối đa 15 thành viên (không
bao gồm thư ký hành ch ính), có số thành viên là số lẻ , trong đó phải có sự tham gia của
các Chủ trì ngành đại diện cho các trình độ đào tạo có liên quan. Hội đồng ngành do Trưởng
khoa quản lý ngành đề cử, Hiệu trưởng quyết định thành lập và chịu sự quản lý trực tiếp
của khoa quản lý ngành. Đối với các ngành liên ngành, Hội đồng ngành liên ngành do
Trưởng các khoa quản lý các ngành liên quan đề cử, Hiệu trưởng quyết định thành lập và
chịu sự quản lý trực tiếp của các khoa quản lý ngành.”.
b) Sửa đổi, bổ sung khoản 4 Điều 16:
“4. Nhiệm vụ của Chủ nhiệm Hội đồng ngành:
a) Chủ trì chuẩn bị hồ sơ, tài liệu, văn bản cần thiết và tổ chức các cuộc họp của
Hội đồng ngành; báo cáo Hội đồng khoa học và đào tạo của khoa về công tác xây dựng, rà
soát và cập nhật chương trình đào tạo của ngành, chuyên ngành;
b) Trao đổi với Trưởng khoa (hoặc Trưởng các khoa liên quan đối với ngành liên
ngành, sau đây gọi tắt là Trưởng khoa) hoặc giảng viên phụ trách học phần (nếu có) trong
việc phân bổ nội dung học phần trong chương trình đào tạo, tổ chức thảo luận, thống nhất
trong Hội đồng ngành để trình cấp có thẩm quyền phê duyệt;
c) Tham mưu cho Trưởng khoa trong việc phân công giảng viên giảng dạy các học
phần trong chương trình đào tạo, tham mưu việc xét duyệt đề tài và phân công khối lượng
hướng dẫn khóa luận tốt nghiệp hay luận văn thạc sĩ theo quy định;
d) Báo cáo định kỳ Hội đồng khoa học và đào tạo của khoa về tình hình tổ chức,
vận hành chương trình đào tạo của ngành, chuyên ngành;
e) Tổng hợp báo cáo của các Chủ trì ngành theo từng trình độ đào tạo và báo cáo
Trưởng khoa để xem xét, chỉ đạo;
f) Tham mưu cho Trưởng khoa trong việc mời giảng viên thỉnh giảng.”.
9. Bổ sung Điều 16a sau Điều 16 như sau:
“ Điều 16a. Chủ trì ngành
a) Chủ trì xây dựng và tổ chức triển khai chương trình đào tạo của ngành, chuyên
ngành;
b) Rà soát định kỳ chương trình đào tạo; báo cáo Hội đồng ngành để xem xét quyết
định việc điều chỉnh hoặc xây dựng mới chương trình đào tạo;
c) Tham mưu cho Hội đồng ngành trong việc phân công giảng viên giảng dạy các học
phần thuộc chương trình đào tạo, tham mưu việc xét duyệt đề tài và phân công khối lượng
hướng dẫn khóa luận tốt nghiệp hoặc luận văn thạc sĩ theo quy định;
d) Tham mưu cho Trưởng khoa trong việc phân công giảng viên làm Trưởng nhóm
môn học để chịu trách nhiệm chủ trì việc thống nhất nội dung giảng dạy của môn học theo
từng học kỳ, tổ chức ra đề thi và thực hiện thẩm định đề thi theo quy định;
e) Đề xuất danh sách thành viên các hội đồng chấm đồ án, khóa luận , luận văn,
luận án… để Hội đồng ngành tham mưu Trưởng khoa xem xét, quyết định;
f) Báo cáo định kỳ Hội đồng ngành về tình hình triển khai và vận hành chương trình
đào tạo của ngành, chuyên ngành; đề xuất các giải pháp điều chỉnh, cải tiến khi cần thiết.”.
10. Thay thế Phụ lục III như sau:
“ PHỤ LỤC III
PHÂN BỐ CÁC HỌC PHẦN TRÌNH ĐỘ THẠC SĨ:
Học
kỳ
Học phần
Thạc sĩ ứng dụng Thạc sĩ nghiên cứu
Thạc sĩ nghiên cứu
chuyên sâu
1.
Triết học (3 TC) Triết học (3 TC) Triết học (3 TC)
Cơ sở ngành (12 TC) Cơ sở ngành (12 TC)
Phương pháp nghiên cứu
khoa học (3 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 1
+ Báo cáo khoa học
(9 TC)
2.
Tự chọn đa ngành, tổng
quát (3 TC)
Phương pháp nghiên cứu
khoa học (3 TC) Luận văn thạc sĩ nghiên cứu chuyên sâu – phần 2
+ Báo cáo khoa học
(15 TC) Ngành/ Chuyên ngành
bắt buộc (12 TC)
Ngành/ Chuyên ngành
(12 TC)
3.
Ngành/ Chuyên ngành tự
chọn (9 TC)
Chuyên đề nghiên cứu
trước luận văn (15 TC)
Thực tập (6 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 3
+ Báo cáo khoa học
(15 TC)
4.
Ngành/ Chuyên ngành tự
chọn (3 TC) Luận văn thạc sĩ nghiên
cứu + Báo cáo khoa học
(15 TC)
Luận văn thạc sĩ nghiên
cứu chuyên sâu – phần 4
+ Báo cáo khoa học
(15 TC)
Tự chọn đa ngành, tổng
quát (3 TC)
Đề án tốt nghiệp (9 TC)
”.
11. Sửa đổi mục 2.2 Thạc sĩ nghiên cứu của Phụ lục V – Cấu trúc chi tiết chương
trình đào tạo các trình độ như sau:
“ 2.2 Thạc sĩ nghiên cứu
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO THẠC SĨ NGHIÊN CỨU
Khối kiến thức Số môn Số tín chỉ
A. Đa ngành, tổng quát (General Multidisciplinary Courses) 6
Triết học (Philosophy) 3
Phương pháp nghiên cứu khoa học (Scientific Research Methodology) 3
Anh văn 1 (English 1) 0
Anh văn 2 (English 2) 0
B. Cơ sở ngành (Foundation Courses) 12
B.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
B.2 Tự chọn cơ sở ngành (Elective Foundation Courses)
…
C. Ngành/ Chuyên ngành (Major/ Speciality Courses) 12
C.1 Ngành/ Chuyên ngành bắt buộc (Compulsory Major/ Speciality Courses)
…
C.2 Ngành/ Chuyên ngành tự chọn (Elective Major/ Speciality Courses)
…
D. Học phần tốt nghiệp (Graduation Module) 30
Chuyên đề nghiên cứu trước luận văn
(Pre – Thesis Research Project)
15
Luận văn thạc sĩ (Master’s Thesis) 15
E. Điều kiện tốt nghiệp (Other Graduation Requirements)
ENG_B2
Tổng tín chỉ 60
”.
12. Bổ sung vào bước 6, khoản 1.1, mục 1 (Xây dựng chương trình đào tạo mới)
của Phụ lục VI: Quy trình xây dựng, thẩm định, cập nhật và ban hành chương trình đào tạo
trình độ đại học, thạc sĩ, tiến sĩ như sau:
“Bước 6: Tổ chức hội thảo lấy ý kiến của giảng viên, đội ngũ quản lý trong và ngoài
trường, các nhà khoa học, đại diện đơn vị sử dụng lao động liên quan và người đã tốt nghiệp
(nếu có) về CTĐT. Yêu cầu có Biên bản họp của Hội đồng ngành và Hội đồng Khoa học
và đào tạo của khoa về việc thông qua nội dung chương trình đào tạo là căn cứ để hoàn
thiện hồ sơ và trình phê duyệt chương trình đào tạo.”.
13. Bổ sung Phụ lục XI như sau:
“ PHỤ LỤC XI:
Cấu trúc chi tiết chương trình đào tạo các trình độ từ khóa 2026
1. Trình độ đại học
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC
CÁC NGÀNH KỸ THUẬT VÀ KIẾN TRÚC
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and Basic
Sciences) 30
A.1 Toán (Mathematics) Tối thiểu 11
…
A.2. Khoa học tự nhiên (Basic Sciences) Tối thiểu 5
…
B. Giáo dục chung (General Education) 30
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Quản lý / Khởi nghiệp (Management/ Entrepreneurship Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 8
Anh văn 1 (English 1)
Anh văn 2 (English 2)
Anh văn 3 (English 3)
Anh văn 4 (English 4)
B.6
Kiến thức và kỹ năng bổ trợ (Supplementary
Knowledge and Skills) Dành cho các môn kỹ
năng mềm, tiếng Nhật, văn hoá Nhật ...
B.6.1 Kỹ năng bổ trợ (Supplementary Skills) : áp dụng từ khóa 2025 chương trình tiêu chuẩn 1 0
…
B.6.2
Kỹ năng bổ trợ (Supplementary Skills) : áp
dụng từ khóa 2025 cho các chương trình: Dạy
và học bằng tiếng Anh; Tiên tiến; Định hướng
Nhật bản; Chuyển tiếp quốc tế; Liên kết cử
nhân kỹ thuật quốc tế
4 0
…
B.6.3
Tiếng Nhật (Japaneses) áp dụng cho các
chương trình: Định hướng Nhật Bản và
Chuyển tiếp quốc tế Nhật Bản
8 0
…
B.6.4 Văn hóa Nhật (Japanese Culture) áp dụng cho Chương trình Định hướng Nhật Bản 1 0
…
C. Cơ sở ngành (Foundation Courses) 18–34
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành ( Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality Courses) 17–37
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses)
D2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc c huyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 17
…
…
F. Giáo dục Quốc phòng – An ninh (National Defense
and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GC
…
Tổng tín chỉ 128–132
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC
CÁC NGÀNH QUẢN LÝ
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and Basic
Sciences) 12
A.1 Toán (Mathematics) 9
…
A.2. Khoa học tự nhiên (Basic Sciences) 3
…
B. Giáo dục chung (General Education) 30
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Kỹ thuật ngoài ngành ( Non – management Technical Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 8
Anh văn 1 (English 1)
Anh văn 2 (English 2)
Anh văn 3 (English 3)
Anh văn 4 (English 4)
B.6 Kiến thức và kỹ năng bổ trợ (Supplementary Knowledge and Skills) 0
B.6.1 Kỹ năng bổ trợ (Supplementary Skills) : áp dụng từ khóa 2025 chương trình tiêu chuẩn 1 0
…
B.6.2
Kỹ năng bổ trợ (Supplementary Skills) : áp
dụng từ khóa 2025 cho các chương trình: Dạy
và học bằng tiếng Anh; Chuyển tiếp quốc tế
4 0
…
C. Cơ sở ngành (Foundation Courses) 18–34
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành ( Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality Courses) 35–55
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses)
D.2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc c huyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 17
…
…
F. Giáo dục Quốc phòng – An ninh (National Defense
and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục Thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GC
…
Tổng tín chỉ 128–132
CẤU TRÚC CHI TIẾT CHƯƠNG TRÌNH ĐÀO TẠO PFIEV
Khối kiến thức Số môn Số tín chỉ
A. Toán & Khoa học tự nhiên (Mathematics and
Basic Sciences) 36
A.1 Toán (Mathematics) 21
…
A.2. Khoa học tự nhiên (Basic Sciences) 15
…
B. Giáo dục chung (General Education) 42
B.1 Kinh tế – Chính trị – Xã hội – Luật (Socials and Economics) 13
…
B.2 Nhập môn (Introduction) 3
…
B.3 Quản lý/ Khởi nghiệp (Management/ Entrepreneurship Courses) 3
…
B.4
Kiến thức về con người và môi trường
(Knowledge of Humans and the
Environment)
Hoặc
Kỹ năng nghề nghiệp chuyên nghiệp
(Professional Career Skills)
3
…
B.5 Ngoại ngữ (Foreign Languages) 20
B5.1 Anh văn (English) 8
B5.2 Pháp văn (French) 12
B.6 Kiến thức và kỹ năng bổ trợ (Supplementary Knowledge and Skills) áp dụng từ khóa 2025 1 0
…
C. Cơ sở ngành (Foundation Courses) 16–32
C.1 Bắt buộc cơ sở ngành (Compulsory Foundation Courses)
…
C.2 Tự chọn cơ sở ngành (Elective Foundation Courses)
…
D. Ngành/ Chuyên ngành (Major/ Speciality
Courses) 22–43
D.1 Ngành (Major Courses)
D.1.1 Bắt buộc ngành (Compulsory Major Courses)
…
D.1.2 Tự chọn ngành (Elective Major Courses)
…
D.2 Chuyên ngành (Speciality Courses )
D.2.1 Chuyên ngành …(Speciality Courses …)
D.2.1.1 Bắt buộc chuyên ngành …(Compulsory Speciality Courses…)
…
D.2.1.2 Tự chọn Chuyên ngành …(Elective Speciality Courses …)
…
E. Học phần tốt nghiệp (Graduation Module) 26
…
…
…
…
F. Giáo dục Quốc phòng – An ninh (National
Defense and Security Education) 1 0
…
G. Giáo dục Thể chất (Physical Education) 0
G.1 Giáo dục Thể chất 1 (Physical Education 1) 1
G.2 Giáo dục Thể chất 2 (Physical Education 2) 1
H. Điều kiện tốt nghiệp (Other Graduation Requirements)
SA4001
ENG_GT_700
FRA_GC
Tổng tín chỉ 158–163
”.

</details>

<details><summary>Source `HCMUT_GVCN2977_Dieu_15` — Điều 15. Vai trò và nhiệm vụ</summary>

Điều 15. Vai trò và nhiệm vụ
1. Giải thích cho người học về chương trình đào tạo, kế hoạch giảng dạy của ngành.
2. Cố vấn cho người học khi học có nhu cầu học vượt, học chậm tiến độ.
3. Tư vấn cho người học định hướng về ngành, ngành chính - phụ, ngành thứ hai, các
vấn đề có thể xảy ra khi chuyển khóa, chuyển ngành.
4. Tư vấn cho người học về các tín chỉ tự chọn tự do.
5. Tư vấn cho người học về các học phần tương đương, thay thế, các học phần của
chương trình liên thông Đại học - Thạc sĩ, Cử nhân - Kỹ sư.
6. Tư vấn cho người học về các nội dung khác liên quan đến chương trình đào tạo.

</details>
