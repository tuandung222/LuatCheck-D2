# Human audit packets — labour (30 items, blind)

Read with SEMANTIC_JUDGING.md. Fill labels.csv (one row per review_id). Variant, seed and the LLM judgement are hidden on purpose.


---

## 1. `0ce19a8e159c499606fe8f92`

**Question:** Theo Bộ luật Lao động 2019, người lao động thông thường được làm thêm giờ tối đa bao nhiêu giờ trong một năm, và giới hạn này được nâng lên trong trường hợp nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Thông thường người sử dụng lao động chỉ được cho làm thêm không quá 200 giờ trong 01 năm (khoản 2 điểm c Điều 107). Giới hạn được nâng lên không quá 300 giờ trong 01 năm đối với các ngành, nghề, công việc hoặc trường hợp sau (khoản 3 Điều 107): (a) sản xuất, gia công xuất khẩu sản phẩm hàng dệt, may, da, giày, điện, điện tử, chế biến nông, lâm, diêm nghiệp, thủy sản; (b) sản xuất, cung cấp điện, viễn thông, lọc dầu; cấp, thoát nước; (c) giải quyết công việc đòi hỏi lao động có trình độ chuyên môn, kỹ thuật cao mà thị trường lao động không cung ứng đầy đủ, kịp thời; (d) giải quyết công việc cấp bách, không thể trì hoãn do tính chất thời vụ, thời điểm của nguyên liệu, sản phẩm hoặc công việc phát sinh do yếu tố khách quan không dự liệu trước, do hậu quả thời tiết, thiên tai, hỏa hoạn, địch họa, thiếu điện, thiếu nguyên liệu, sự cố kỹ thuật của dây chuyền sản xuất; (đ) trường hợp khác do Chính phủ quy định.

**Reference evidence:**
- `BLLD2019_Dieu_107`: không quá 200 giờ trong 01 năm, trừ trường hợp quy định tại khoản 3 Điều này
- `BLLD2019_Dieu_107`: không quá 300 giờ trong 01 năm trong một số ngành, nghề, công việc hoặc trường hợp sau đây
- `BLLD2019_Dieu_107`: Sản xuất, gia công xuất khẩu sản phẩm hàng dệt, may, da, giày, điện, điện tử, chế biến nông, lâm, diêm nghiệp, thủy sản
- `BLLD2019_Dieu_107`: Sản xuất, cung cấp điện, viễn thông, lọc dầu; cấp, thoát nước
- `BLLD2019_Dieu_107`: Trường hợp giải quyết công việc đòi hỏi lao động có trình độ chuyên môn, kỹ thuật cao mà thị trường lao động không cung ứng đầy đủ, kịp thời
- `BLLD2019_Dieu_107`: Trường hợp phải giải quyết công việc cấp bách, không thể trì hoãn do tính chất thời vụ, thời điểm của nguyên liệu, sản phẩm hoặc để giải quyết công việc phát sinh do yếu tố khách quan không dự liệu trước, do hậu quả thời tiết, thiên tai, hỏa hoạn, địch họa, thiếu điện, thiếu nguyên liệu, sự cố kỹ thuật của dây chuyền sản xuất
- `BLLD2019_Dieu_107`: Trường hợp khác do Chính phủ quy định

**Candidate behaviour:** refused

**Candidate answer:**

> Không có tài liệu trong bộ văn bản đã tra cứu chứng minh chính xác các quy định về thời gian làm việc tối đa năm, chỉ có phần trích dẫn ngắn. Cần kiểm tra lại nội dung source.

<details><summary>Source `BLLD2019_Dieu_107` — Điều 107. Làm thêm giờ</summary>

Điều 107. Làm thêm giờ 1. Thời gian làm thêm giờ là khoảng thời gian làm việc ngoài thời giờ làm việc bình thường theo quy định của pháp luật, thỏa ước lao động tập thể hoặc nội quy lao động. 2. Người sử dụng lao động được sử dụng người lao động làm thêm giờ khi đáp ứng đầy đủ các yêu cầu sau đây: a) Phải được sự đồng ý của người lao động; b) Bảo đảm số giờ làm thêm của người lao động không quá 50% số giờ làm việc bình thường trong 01 ngày; trường hợp áp dụng quy định thời giờ làm việc bình thường theo tuần thì tổng số giờ làm việc bình thường và số giờ làm thêm không quá 12 giờ trong 01 ngày; không quá 40 giờ trong 01 tháng; c) Bảo đảm số giờ làm thêm của người lao động không quá 200 giờ trong 01 năm, trừ trường hợp quy định tại khoản 3 Điều này. 3. Người sử dụng lao động được sử dụng người lao động làm thêm không quá 300 giờ trong 01 năm trong một số ngành, nghề, công việc hoặc trường hợp sau đây: a) Sản xuất, gia công xuất khẩu sản phẩm hàng dệt, may, da, giày, điện, điện tử, chế biến nông, lâm, diêm nghiệp, thủy sản; b) Sản xuất, cung cấp điện, viễn thông, lọc dầu; cấp, thoát nước; c) Trường hợp giải quyết công việc đòi hỏi lao động có trình độ chuyên môn, kỹ thuật cao mà thị trường lao động không cung ứng đầy đủ, kịp thời; d) Trường hợp phải giải quyết công việc cấp bách, không thể trì hoãn do tính chất thời vụ, thời điểm của nguyên liệu, sản phẩm hoặc để giải quyết công việc phát sinh do yếu tố khách quan không dự liệu trước, do hậu quả thời tiết, thiên tai, hỏa hoạn, địch họa, thiếu điện, thiếu nguyên liệu, sự cố kỹ thuật của dây chuyền sản xuất; đ) Trường hợp khác do Chính phủ quy định. 4. Khi tổ chức làm thêm giờ theo quy định tại khoản 3 Điều này, người sử dụng lao động phải thông báo bằng văn bản cho cơ quan chuyên môn về lao động thuộc Ủy ban nhân dân cấp tỉnh. 5. Chính phủ quy định chi tiết Điều này.

</details>


---

## 2. `0d0bca29f23f4e858de9ad93`

**Question:** Lao động nữ nghỉ thai sản thì được trợ cấp thai sản từ bảo hiểm xã hội bằng bao nhiêu phần trăm tiền lương?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Corpus không trả lời: Bộ luật Lao động Điều 139 chỉ nói lao động nữ được hưởng chế độ thai sản theo pháp luật về bảo hiểm xã hội; mức trợ cấp thai sản không có trong corpus.

**Candidate behaviour:** refused

**Candidate answer:**

> Không tìm thấy nội dung chi tiết về mức trợ cấp cụ thể (phần trăm) trong các văn bản tra cứu. Điều này dẫn đến không có căn cứ pháp lý đủ chắc chắn từ file dữ liệu đã nạp.


---

## 3. `1bc2b72832c9bc280aed857b`

**Question:** Lao động nữ nghỉ thai sản thì được trợ cấp thai sản từ bảo hiểm xã hội bằng bao nhiêu phần trăm tiền lương?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Corpus không trả lời: Bộ luật Lao động Điều 139 chỉ nói lao động nữ được hưởng chế độ thai sản theo pháp luật về bảo hiểm xã hội; mức trợ cấp thai sản không có trong corpus.

**Candidate behaviour:** clarified

**Candidate answer:**

> Cần có thông tin cụ thể hơn về mức trợ cấp từ BHXH khi nghỉ thai sản, có có thể cung cấp thêm thông tin như tên con số (ví dụ: 10%, 25%) hay cần tra cứu lại điều khoản liên quan?


---

## 4. `21fba8c2957527641bf19139`

**Question:** Theo Bộ luật Lao động 2019, mức lương tối thiểu được xác lập và ấn định theo những đơn vị nào, và theo Nghị định 293/2025 mức lương tối thiểu tháng và giờ của Vùng I là bao nhiêu?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Bộ luật Lao động 2019 quy định mức lương tối thiểu được xác lập theo vùng và ấn định theo tháng, giờ. Nghị định 293/2025 quy định Vùng I là 5.310.000 đồng/tháng và 25.500 đồng/giờ.

**Reference evidence:**
- `BLLD2019_Dieu_91`: Mức lương tối thiểu được xác lập theo vùng, ấn định theo tháng, giờ
- `ND293_2025_Dieu_3`: Vùng I 5.310.000 25.500

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Nghị định 293/2025/NĐ-CP (mức lương tối thiểu), mức lương tối thiểu tháng cho Vùng I là 5.310.000 đồng, và mức lương tối thiểu giờ là 25.500 đồng.

**Candidate citations:** `ND293_2025_Dieu_3`

<details><summary>Source `BLLD2019_Dieu_91` — Điều 91. Mức lương tối thiểu</summary>

Điều 91. Mức lương tối thiểu 1. Mức lương tối thiểu là mức lương thấp nhất được trả cho người lao động làm công việc giản đơn nhất trong điều kiện lao động bình thường nhằm bảo đảm mức sống tối thiểu của người lao động và gia đình họ, phù hợp với điều kiện phát triển kinh tế - xã hội. 2. Mức lương tối thiểu được xác lập theo vùng, ấn định theo tháng, giờ. 3. Mức lương tối thiểu được điều chỉnh dựa trên mức sống tối thiểu của người lao động và gia đình họ; tương quan giữa mức lương tối thiểu và mức lương trên thị trường; chỉ số giá tiêu dùng, tốc độ tăng trưởng kinh tế; quan hệ cung, cầu lao động; việc làm và thất nghiệp; năng suất lao động; khả năng chi trả của doanh nghiệp. 4. Chính phủ quy định chi tiết Điều này; quyết định và công bố mức lương tối thiểu trên cơ sở khuyến nghị của Hội đồng tiền lương quốc gia.

</details>

<details><summary>Source `ND293_2025_Dieu_3` — Điều 3. Mức lương tối thiểu</summary>

Điều 3. Mức lương tối thiểu 1. Quy định mức lương tối thiểu tháng và mức lương tối thiểu giờ đối với người lao động làm việc cho người sử dụng lao động theo vùng như sau: Vùng Mức lương tối thiểu tháng Mức lương tối thiểu giờ (Đơn vị: đồng/tháng) (Đơn vị: đồng/giờ) Vùng I 5.310.000 25.500 Vùng II 4.730.000 22.700 Vùng III 4.140.000 20.000 Vùng IV 3.700.000 17.800 2. Danh mục địa bàn vùng I, vùng II, vùng III, vùng IV được quy định tại Phụ lục ban hành kèm theo Nghị định này. 3. Việc áp dụng địa bàn vùng được xác định theo nơi hoạt động của người sử dụng lao động như sau: a) Người sử dụng lao động hoạt động trên địa bàn thuộc vùng nào thì áp dụng mức lương tối thiểu quy định đối với địa bàn đó. b) Người sử dụng lao động có đơn vị, chi nhánh hoạt động trên các địa bàn có mức lương tối thiểu khác nhau thì đơn vị, chi nhánh hoạt động ở địa bàn nào, áp dụng mức lương tối thiểu quy định đối với địa bàn đó. c) Người sử dụng lao động hoạt động trong khu công nghiệp, khu chế xuất, khu công nghệ cao, khu công nghệ số tập trung nằm trên các địa bàn có mức lương tối thiểu khác nhau thì áp dụng theo địa bàn có mức lương tối thiểu cao nhất. d) Người sử dụng lao động hoạt động trên địa bàn có sự thay đổi tên hoặc chia thì tạm thời áp dụng mức lương tối thiểu quy định đối với địa bàn trước khi thay đổi tên hoặc chia cho đến khi Chính phủ có quy định mới. đ) Người sử dụng lao động hoạt động trên địa bàn được thành lập mới từ một địa bàn hoặc nhiều địa bàn có mức lương tối thiểu khác nhau thì áp dụng mức lương tối thiểu theo địa bàn có mức lương tối thiểu cao nhất cho đến khi Chính phủ có quy định mới.

</details>


---

## 5. `2751671a3e571d0eba74758d`

**Question:** Doanh nghiệp đã được cơ quan có thẩm quyền đôn đốc trong thời hạn 45 ngày kể từ hạn đóng chậm nhất. Trong trường hợp trốn đóng theo điểm đ, e khoản 1 Điều 39 Luật Bảo hiểm xã hội, số ngày trốn đóng được tính từ khi nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Số ngày trốn đóng được tính bắt đầu từ sau 60 ngày kể từ sau thời hạn đóng bảo hiểm xã hội chậm nhất quy định tại khoản 4 Điều 34 Luật Bảo hiểm xã hội (hoặc sau thời hạn đóng bảo hiểm thất nghiệp chậm nhất theo pháp luật về bảo hiểm thất nghiệp).

**Reference evidence:**
- `ND274_2025_Dieu_6`: đã được cơ quan có thẩm quyền đôn đốc theo quy định trong thời hạn 45 ngày kể từ sau thời hạn đóng bảo hiểm xã hội chậm nhất quy định tại khoản 4 Điều 34 Luật Bảo hiểm xã hội
- `ND274_2025_Dieu_6`: Số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp được xác định bắt đầu từ sau 60 ngày kể từ sau thời hạn đóng bảo hiểm xã hội chậm nhất quy định tại khoản 4 Điều 34 Luật Bảo hiểm xã hội

**Candidate behaviour:** refused

**Candidate answer:**

> Không tìm thấy thông tin chi tiết trong văn bản 'Nghị định 274/2025/NĐ-CP' hoặc 'Luật Bảo hiểm xã hội' xác định rõ số ngày cụ thể được tính từ khi nào cho trường hợp trốn đóng theo điểm a Điều 39, chỉ có quy định về thời hạn 60 ngày.

<details><summary>Source `ND274_2025_Dieu_6` — Điều 6. Số tiền, số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp</summary>

Điều 6. Số tiền, số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp Số tiền, số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp theo quy định tại khoản 1 Điều 41 Luật Bảo hiểm xã hội được quy định như sau: 1. Số tiền trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp. a) Trốn đóng theo điểm a, b khoản 1 Điều 39 Luật Bảo hiểm xã hội: số tiền bảo hiểm xã hội bắt buộc trốn đóng là số tiền thuộc trách nhiệm của người sử dụng lao động theo quy định tại khoản 4 Điều 13 Luật Bảo hiểm xã hội phải đóng cho người lao động chưa được đăng ký tham gia bảo hiểm xã hội sau thời hạn 60 ngày kể từ ngày hết thời hạn quy định tại khoản 1 Điều 28 Luật Bảo hiểm xã hội; số tiền bảo hiểm thất nghiệp trốn đóng là số tiền thuộc trách nhiệm của người sử dụng lao động phải đóng cho người lao động chưa được đăng ký tham gia bảo hiểm thất nghiệp sau thời hạn 60 ngày kể từ ngày hết thời hạn phải tham gia bảo hiểm thất nghiệp theo quy định của pháp luật về bảo hiểm thất nghiệp. b) Trốn đóng theo điểm c, d khoản 1 Điều 39 Luật Bảo hiểm xã hội: số tiền bảo hiểm xã hội bắt buộc trốn đóng là số tiền thuộc trách nhiệm của người sử dụng lao động theo quy định tại khoản 4 Điều 13 Luật Bảo hiểm xã hội còn phải đóng vào quỹ bảo hiểm xã hội do đã đăng ký tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc thấp hơn quy định tại khoản 1 Điều 31 Luật Bảo hiểm xã hội; số tiền bảo hiểm thất nghiệp trốn đóng là số tiền thuộc trách nhiệm của người sử dụng lao động còn phải đóng vào quỹ bảo hiểm thất nghiệp do đã đăng ký tiền lương làm căn cứ đóng bảo hiểm thất nghiệp bắt buộc thấp hơn quy định của pháp luật về bảo hiểm thất nghiệp. c) Trốn đóng theo điểm đ, e khoản 1 Điều 39 Luật Bảo hiểm xã hội: số tiền bảo hiểm xã hội bắt buộc trốn đóng là số tiền thuộc trách nhiệm của người sử dụng lao động theo quy định tại khoản 4 Điều 13 Luật Bảo hiểm xã hội còn phải đóng theo đăng ký sau 60 ngày kể từ ngày đóng bảo hiểm xã hội bắt buộc chậm nhất quy định tại khoản 4 Điều 34 Luật Bảo hiểm xã hội và đã được cơ quan có thẩm quyền đôn đốc theo quy định tại Điều 35 của Luật Bảo hiểm xã hội, Điều 3 Nghị định này; số tiền bảo hiểm thất nghiệp trốn đóng là số tiền thuộc trách nhiệm của người sử dụng lao động còn phải đóng theo đăng ký sau 60 ngày kể từ ngày đóng bảo hiểm thất nghiệp chậm nhất theo quy định của pháp luật về bảo hiểm thất nghiệp và đã được cơ quan có thẩm quyền đôn đốc theo quy định tại Điều 35 của Luật Bảo hiểm xã hội, Điều 3 Nghị định này. 2. Số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp. a) Số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp được xác định bắt đầu từ ngày sau thời hạn đóng bảo hiểm xã hội chậm nhất quy định tại khoản 1, khoản 2 Điều 28 và khoản 4 Điều 34 Luật Bảo hiểm xã hội hoặc sau thời hạn đóng bảo hiểm thất nghiệp chậm nhất theo quy định của pháp luật về bảo hiểm thất nghiệp. b) Trốn đóng theo điểm c, d khoản 1 Điều 39 Luật Bảo hiểm xã hội. Đối với các phương thức đóng hàng tháng: số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp được xác định bắt đầu từ sau ngày cuối cùng của tháng tiếp theo tháng phát sinh tiền lương đã đăng ký làm căn cứ đóng bảo hiểm xã hội bắt buộc thấp hơn quy định tại khoản 1 Điều 31 của Luật Bảo hiểm xã hội. Đối với phương thức đóng 03 tháng một lần hoặc 06 tháng một lần: số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp được xác định bắt đầu từ sau ngày cuối cùng của tháng tiếp theo ngay sau chu kỳ đóng đã đăng ký làm căn cứ đóng bảo hiểm xã hội bắt buộc thấp hơn quy định tại khoản 1 Điều 31 của Luật Bảo hiểm xã hội. c) Trốn đóng theo điểm đ, e khoản 1 Điều 39 Luật Bảo hiểm xã hội: Đối với đơn vị sử dụng lao động đã được cơ quan có thẩm quyền đôn đốc theo quy định trong thời hạn 45 ngày kể từ sau thời hạn đóng bảo hiểm xã hội chậm nhất quy định tại khoản 4 Điều 34 Luật Bảo hiểm xã hội: Số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp được xác định bắt đầu từ sau 60 ngày kể từ sau thời hạn đóng bảo hiểm xã hội chậm nhất quy định tại khoản 4 Điều 34 Luật Bảo hiểm xã hội hoặc sau thời hạn đóng bảo hiểm thất nghiệp chậm nhất theo quy định của pháp luật về bảo hiểm thất nghiệp. Đối với đơn vị sử dụng lao động đã được cơ quan có thẩm quyền đôn đốc theo quy định sau 45 ngày kể từ sau thời hạn đóng bảo hiểm xã hội chậm nhất quy định tại khoản 4 Điều 34 Luật Bảo hiểm xã hội: Số ngày trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp được xác định từ ngày thứ 15 kể từ ngày ban hành văn bản đôn đốc của cơ quan có thẩm quyền.

</details>


---

## 6. `2e645f5f6d8966001eda4498`

**Question:** Theo Nghị định 219/2025/NĐ-CP, người nước ngoài là chủ sở hữu công ty trách nhiệm hữu hạn muốn không phải xin giấy phép lao động khi làm việc tại Việt Nam thì giá trị góp vốn tối thiểu là bao nhiêu? Bộ luật Lao động 2019 quy định mức này như thế nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Theo Bộ luật Lao động 2019 (Điều 154 khoản 1), giá trị góp vốn do Chính phủ quy định; Nghị định 219/2025 (Điều 7 khoản 2) quy định từ 3 tỷ đồng trở lên.

**Reference evidence:**
- `BLLD2019_Dieu_154`: Là chủ sở hữu hoặc thành viên góp vốn của công ty trách nhiệm hữu hạn có giá trị góp vốn theo quy định của Chính phủ
- `ND219_2025_Dieu_7`: Là chủ sở hữu hoặc thành viên góp vốn có giá trị góp vốn từ 3 tỷ đồng trở lên của công ty trách nhiệm hữu hạn

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Luật Lao động 2019, điều 154 quy định người lao động nước ngoài không thuộc diện cấp giấy phép lao động nếu là chủ sở hữu hoặc thành viên góp vốn của công ty trách nhiệm hữu hạn có giá trị góp vốn theo quy định của Chính phủ. Tuy nhiên, Nghị định 219/2025/NĐ-CP (Điều 7) bổ sung quy định về mức giá trị góp vốn tối thiểu để không bị xem là chủ sở hữu hoặc thành viên góp vốn với mức thấp hơn. Theo Nghị định này, người lao động nước ngoài có giá trị góp vốn từ **3 tỷ đồng trở lên** của công ty trách nhiệm hữu hạn (Điều 2) hoặc 3 tỷ đồng trở lên của công ty cổ phần (Điều 3). Do đó, để không phải xin giấy phép lao động, mức giá trị góp vốn tối thiểu là **3 tỷ đồng**.

**Candidate citations:** `BLLD2019_Dieu_154`, `ND219_2025_Dieu_7`

<details><summary>Source `BLLD2019_Dieu_154` — Điều 154. Người lao động nước ngoài làm việc tại Việt Nam không thuộc diện cấp giấy phép lao động</summary>

Điều 154. Người lao động nước ngoài làm việc tại Việt Nam không thuộc diện cấp giấy phép lao động 1. Là chủ sở hữu hoặc thành viên góp vốn của công ty trách nhiệm hữu hạn có giá trị góp vốn theo quy định của Chính phủ. 2. Là Chủ tịch Hội đồng quản trị hoặc thành viên Hội đồng quản trị của công ty cổ phần có giá trị góp vốn theo quy định của Chính phủ. 3. Là Trưởng văn phòng đại diện, dự án hoặc chịu trách nhiệm chính về hoạt động của tổ chức quốc tế, tổ chức phi chính phủ nước ngoài tại Việt Nam. 4. Vào Việt Nam với thời hạn dưới 03 tháng để thực hiện chào bán dịch vụ. 5. Vào Việt Nam với thời hạn dưới 03 tháng để xử lý sự cố, tình huống kỹ thuật, công nghệ phức tạp nảy sinh làm ảnh hưởng hoặc có nguy cơ ảnh hưởng tới sản xuất, kinh doanh mà các chuyên gia Việt Nam và các chuyên gia nước ngoài hiện đang ở Việt Nam không xử lý được. 6. Là luật sư nước ngoài đã được cấp Giấy phép hành nghề luật sư tại Việt Nam theo quy định của Luật Luật sư. 7. Trường hợp theo quy định của điều ước quốc tế mà nước Cộng hòa xã hội chủ nghĩa Việt Nam là thành viên. 8. Người nước ngoài kết hôn với người Việt Nam và sinh sống trên lãnh thổ Việt Nam. 9. Trường hợp khác theo quy định của Chính phủ.

</details>

<details><summary>Source `ND219_2025_Dieu_7` — Điều 7. Người lao động nước ngoài không thu ộc diện cấp giấy phép lao đ ộng</summary>

Điều 7. Người lao động nước ngoài không thu ộc diện cấp giấy phép lao đ ộng 1. Thuộc một trong các trường hợp quy định tại các khoản 3, 4, 5, 6, 7 và 8 Điều 154 của Bộ luật Lao động. 2. Là chủ sở hữu hoặc thành viên góp vốn có giá trị góp vốn từ 3 tỷ đồng trở lên của công ty trách nhiệm hữu hạn. 3. Là Chủ tịch Hội đồng quản trị hoặc thành viên Hội đồng quản trị có giá trị góp vốn từ 3 tỷ đồng trở lên của công ty cổ phần. 4. Vào Việt Nam để cung cấp dịch vụ tư vấn về chuyên môn và kỹ thuật hoặc thực hiện các nhiệm vụ khác phục vụ cho công tác nghiên cứu, xây dựng, thẩm định, theo dõi đánh giá, quản lý và thực hiện chương trình, dự án sử dụng nguồn hỗ trợ phát triển chính thức theo quy định hay thỏa thuận trong các điều ước quốc tế về nguồn hỗ trợ phát triển chính thức đã ký kết giữa cơ quan có thẩm quyền của Việt Nam và nước ngoài. 5. Phóng viên nước ngoài hoạt động thông tin báo chí đư ợc Bộ Ngoại giao xác nh ận. 6. Được cơ quan, tổ chức có thẩm quyền của nước ngoài cử sang Việt Nam giảng dạy, làm nhà quản lý, giám đốc điều hành tại cơ sở giáo dục do cơ quan đại diện ngoại giao nước ngoài, tổ chức liên chính phủ đề nghị thành lập tại Việt Nam hoặc các cơ sở, tổ chức được thành lập theo các đi ều ước quốc tế mà Việt Nam đã ký kết, tham gia. 7. Học sinh, sinh viên , học viên nước ngoài đang học tập tại các trường, cơ sở đào tạo ở Việt Nam hoặc nước ngoài có thỏa thuận thực tập hoặc thư mời làm việc cho người sử dụng lao động tại Việt Nam; học viên thực tập, tập sự trên tàu biển Việt Nam. 8. Thân nhân thành viên cơ quan đại diện nước ngoài tại Việt Nam được phép làm việc tại Việt Nam theo quy định tại điều ước quốc tế mà nước Cộng hòa xã hội chủ nghĩa Việt Nam là thành viên. 9. Có hộ chiếu công vụ vào làm việc cho cơ quan nhà nước, tổ chức chính trị, tổ chức chính trị - xã hội. 10. Người chịu trách nhiệm thành lập hiện diện thương mại. 11. Tình nguyện viên làm việc tại Việt Nam theo hình thức tự nguyện và không hưởng lương để thực hiện điều ước quốc tế mà nước Cộng hòa xã hội chủ nghĩa Việt Nam là thành viên và có xác nh ận của cơ quan đại diện ngoại giao nước ngoài hoặc tổ chức quốc tế tại Việt Nam. 12. Vào Việt Nam thực hiện thỏa thuận quốc tế mà cơ quan, tổ chức ở Trung ương, cấp tỉnh ký kết theo quy định của pháp luật. 13. Người lao động nước ngoài là nhà quản lý, giám đốc điều hành, chuyên gia, lao động kỹ thuật thuộc một trong các trường hợp sau: a) Vào Việt Nam làm việc có tổng thời gian dư ới 90 ngày trong 01 năm , tính từ 01 tháng 01 đ ến ngày cuối cùng c ủa năm; b) Di chuyển trong nội bộ doanh nghi ệp: Di chuyển có thời hạn trong nội bộ doanh nghiệp nước ngoài đã thành lập hiện diện thương mại trên lãnh thổ Việt Nam thuộc phạm vi 11 ngành dịch vụ theo biểu cam kết dịch vụ của Việt Nam với tổ chức thương mại thế giới và đã được doanh nghiệp nước ngoài tuyển dụng trước đó ít nhất 12 tháng liên tục. Hiện diện thương mại bao gồm tổ chức kinh tế có vốn đầu tư nước ngoài; văn phòng đ ại diện, chi nhánh của thương nhân nước ngoài tại Việt Nam; văn phòng điều hành của nhà đầu tư nước ngoài trong h ợp đồng hợp tác kinh doanh. 14. Được Bộ Giáo dục và Đào tạo xác nhận vào Việt Nam để thực hiện các công việc sau: a) Giảng dạy, nghiên cứu, chuyển giao chương trình giáo dục quốc tế; b) Làm nhà quản lý, giám đốc điều hành, hiệu trưởng, phó hiệu trưởng cơ sở giáo dục do cơ quan đại diện ngoại giao nước ngoài hoặc tổ chức liên chính ph ủ đề nghị thành lập tại Việt Nam. 15. Được các bộ, cơ quan ngang bộ hoặc Ủy ban nhân dân cấp tỉnh xác nhận vào Việt Nam làm việc trong các lĩnh vực: tài chính, khoa học, công nghệ, đổi mới sáng tạo, chuyển đổi số quốc gia, các lĩnh vực ưu tiên phát triển kinh tế - xã hội.

</details>


---

## 7. `3c4c9ff9458f614d0ab4f222`

**Question:** Nếu trong quá trình thực hiện có thay đổi tên gọi hoặc điều kiện kinh tế - xã hội của các vùng trong danh mục, các Bộ, ngành và Ủy ban nhân dân tỉnh, thành phố phải phản ánh về cơ quan nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Bộ Nội vụ.

**Reference evidence:**
- `TT26_2025_Dieu_5`: đề nghị các Bộ, ngành và Ủy ban nhân dân các tỉnh, thành phố trực thuộc Trung ương phản ánh về Bộ Nội vụ để kịp thời nghiên cứu, giải quyết

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Điều 5 của Thông tư 26/2025/TT-BNV (vùng KT-XH đặc biệt khó khăn, nghỉ hưu sớm), việc phản ánh về thay đổi tên gọi hoặc điều kiện kinh tế-xã hội của các vùng được quy định bởi Ủy ban nhân dân các tỉnh, thành phố trực thuộc Trung ương.

**Candidate citations:** `TT26_2025_Dieu_5`

<details><summary>Source `TT26_2025_Dieu_5` — Điều 5. Tổ chức thực hiện</summary>

Điều 5. Tổ chức thực hiện 1. Ủy ban nhân dân các tỉnh, thành phố trực thuộc Trung ương có trách nhiệm chỉ đạo Sở Nội vụ và các cơ quan có liên quan kiểm tra, đôn đốc việc thực hiện Thông tư này. 2. Cơ quan bảo hiểm xã hội có trách nhiệm triển khai thực hiện Thông tư này. 3. Trong quá trình thực hiện nếu có thay đổi về tên gọi, điều kiện kinh tế - xã hội của các vùng được quy định tại Điều 1 Thông tư này, đề nghị các Bộ, ngành và Ủy ban nhân dân các tỉnh, thành phố trực thuộc Trung ương phản ánh về Bộ Nội vụ để kịp thời nghiên cứu, giải quyết./.

</details>


---

## 8. `46a4b3d63560d23e43e01938`

**Question:** Theo Bộ luật Lao động 2019, mức lương tối thiểu được xác lập và ấn định theo những đơn vị nào, và theo Nghị định 293/2025 mức lương tối thiểu tháng và giờ của Vùng I là bao nhiêu?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Bộ luật Lao động 2019 quy định mức lương tối thiểu được xác lập theo vùng và ấn định theo tháng, giờ. Nghị định 293/2025 quy định Vùng I là 5.310.000 đồng/tháng và 25.500 đồng/giờ.

**Reference evidence:**
- `BLLD2019_Dieu_91`: Mức lương tối thiểu được xác lập theo vùng, ấn định theo tháng, giờ
- `ND293_2025_Dieu_3`: Vùng I 5.310.000 25.500

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Bộ luật Lao động 2019, mức lương tối thiểu được xác lập theo vùng, tháng và giờ. Theo Nghị định 293/2025/NĐ-CP (Điều 3), Vùng I có mức lương tối thiểu tháng là **5.310.000 đồng** và mức lương tối thiểu giờ là **25.500 đồng**.

**Candidate citations:** `BLLD2019_Dieu_91`, `ND293_2025_Dieu_3`

<details><summary>Source `BLLD2019_Dieu_91` — Điều 91. Mức lương tối thiểu</summary>

Điều 91. Mức lương tối thiểu 1. Mức lương tối thiểu là mức lương thấp nhất được trả cho người lao động làm công việc giản đơn nhất trong điều kiện lao động bình thường nhằm bảo đảm mức sống tối thiểu của người lao động và gia đình họ, phù hợp với điều kiện phát triển kinh tế - xã hội. 2. Mức lương tối thiểu được xác lập theo vùng, ấn định theo tháng, giờ. 3. Mức lương tối thiểu được điều chỉnh dựa trên mức sống tối thiểu của người lao động và gia đình họ; tương quan giữa mức lương tối thiểu và mức lương trên thị trường; chỉ số giá tiêu dùng, tốc độ tăng trưởng kinh tế; quan hệ cung, cầu lao động; việc làm và thất nghiệp; năng suất lao động; khả năng chi trả của doanh nghiệp. 4. Chính phủ quy định chi tiết Điều này; quyết định và công bố mức lương tối thiểu trên cơ sở khuyến nghị của Hội đồng tiền lương quốc gia.

</details>

<details><summary>Source `ND293_2025_Dieu_3` — Điều 3. Mức lương tối thiểu</summary>

Điều 3. Mức lương tối thiểu 1. Quy định mức lương tối thiểu tháng và mức lương tối thiểu giờ đối với người lao động làm việc cho người sử dụng lao động theo vùng như sau: Vùng Mức lương tối thiểu tháng Mức lương tối thiểu giờ (Đơn vị: đồng/tháng) (Đơn vị: đồng/giờ) Vùng I 5.310.000 25.500 Vùng II 4.730.000 22.700 Vùng III 4.140.000 20.000 Vùng IV 3.700.000 17.800 2. Danh mục địa bàn vùng I, vùng II, vùng III, vùng IV được quy định tại Phụ lục ban hành kèm theo Nghị định này. 3. Việc áp dụng địa bàn vùng được xác định theo nơi hoạt động của người sử dụng lao động như sau: a) Người sử dụng lao động hoạt động trên địa bàn thuộc vùng nào thì áp dụng mức lương tối thiểu quy định đối với địa bàn đó. b) Người sử dụng lao động có đơn vị, chi nhánh hoạt động trên các địa bàn có mức lương tối thiểu khác nhau thì đơn vị, chi nhánh hoạt động ở địa bàn nào, áp dụng mức lương tối thiểu quy định đối với địa bàn đó. c) Người sử dụng lao động hoạt động trong khu công nghiệp, khu chế xuất, khu công nghệ cao, khu công nghệ số tập trung nằm trên các địa bàn có mức lương tối thiểu khác nhau thì áp dụng theo địa bàn có mức lương tối thiểu cao nhất. d) Người sử dụng lao động hoạt động trên địa bàn có sự thay đổi tên hoặc chia thì tạm thời áp dụng mức lương tối thiểu quy định đối với địa bàn trước khi thay đổi tên hoặc chia cho đến khi Chính phủ có quy định mới. đ) Người sử dụng lao động hoạt động trên địa bàn được thành lập mới từ một địa bàn hoặc nhiều địa bàn có mức lương tối thiểu khác nhau thì áp dụng mức lương tối thiểu theo địa bàn có mức lương tối thiểu cao nhất cho đến khi Chính phủ có quy định mới.

</details>


---

## 9. `5c351d75a13af5da8071f2e0`

**Question:** Luật Công đoàn 2024 có hiệu lực thi hành từ ngày nào, và Luật Công đoàn 2012 hết hiệu lực vào thời điểm nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Luật có hiệu lực từ ngày 01/7/2025. Luật Công đoàn số 12/2012/QH13 hết hiệu lực từ ngày Luật Công đoàn 2024 có hiệu lực.

**Reference evidence:**
- `LCD2024_Dieu_37`: Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2025
- `LCD2024_Dieu_37`: Luật Công đoàn số 12/2012/QH13 hết hiệu lực từ ngày Luật này có hiệu lực thi hành

**Candidate behaviour:** refused

**Candidate answer:**

> Không có thông tin trong cơ sở dữ liệu về hiệu lực pháp luật công ty hay Luật Công đoàn. Không thể xác định chính xác ngày bắt đầu và thời điểm hết hiệu lực.

<details><summary>Source `LCD2024_Dieu_37` — Điều 37. Hiệu lực thi hành</summary>

Điều 37. Hiệu lực thi hành Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2025. Luật Công đoàn số 12/2012/QH13 hết hiệu lực từ ngày Luật này có hiệu lực thi hành./. Luật này được Quốc hội nước Cộng hòa xã hội chủ nghĩa Việt Nam khóa XV, kỳ họp thứ 8 thông qua ngày 27 tháng 11 năm 2024.

</details>


---

## 10. `61264862dec1492ea4b729c2`

**Question:** Theo Nghị định 318/2025, khi người lao động tự kê khai hồ sơ đăng ký lao động thì ai chịu trách nhiệm trước pháp luật về tính trung thực và chính xác của thông tin?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Người lao động tự kê khai chịu trách nhiệm trước pháp luật về tính trung thực, chính xác của các thông tin đã kê khai; người sử dụng lao động có trách nhiệm kê khai và cung cấp đầy đủ, chính xác, kịp thời thông tin về người lao động khi tuyển dụng, thay đổi hoặc chấm dứt quan hệ lao động.

**Reference evidence:**
- `ND318_2025_Dieu_3`: Người lao động tự kê khai hồ sơ đăng ký lao động và chịu trách nhiệm trước pháp luật về tính trung thực, chính xác của các thông tin đã kê khai

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Nghị định 318/2025 (Nghị định 318/2025/NĐ-CP), người lao động tự kê khai hồ sơ đăng ký lao động phải chịu trách nhiệm trước pháp luật về tính trung thực và chính xác của thông tin đã kê khai. Người sử dụng lao động có trách nhiệm thu thập, kê khai và cung cấp đầy đủ, chính xác, kịp thời các thông tin liên quan đến người lao động.

**Candidate citations:** `ND318_2025_Dieu_3`

<details><summary>Source `ND318_2025_Dieu_3` — Điều 3. Đối tượng đăng ký lao động</summary>

Điều 3. Đối tượng đăng ký lao động 1. Người lao động thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc theo quy định tại khoản 1 Điều 2 Luật Bảo hiểm xã hội số 41/2024/QH15. 2. Người lao động đang có việc làm và không thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc. 3. Người thất nghiệp là người đang không có việc làm, đang tìm kiếm việc làm và sẵn sàng làm việc. 4. Cán bộ, công chức, viên chức, lực lượng vũ trang nhân dân không thực hiện việc đăng ký, điều chỉnh thông tin đăng ký lao động theo quy định tại Nghị định này. 5. Người lao động tự kê khai hồ sơ đăng ký lao động và chịu trách nhiệm trước pháp luật về tính trung thực, chính xác của các thông tin đã kê khai; người sử dụng lao động có trách nhiệm thu thập, kê khai và cung cấp đầy đủ, chính xác, kịp thời thông tin về người lao động khi tuyển dụng, thay đổi hoặc chấm dứt quan hệ lao động theo quy định của Nghị định này; bảo đảm tính trung thực chính xác của thông tin cung cấp.

</details>


---

## 11. `673f8d6e33f6eb0a740dd305`

**Question:** Người sử dụng lao động và người lao động phải đóng bảo hiểm y tế với tỷ lệ bao nhiêu phần trăm tiền lương hiện hành?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Kho dữ liệu không nêu tỷ lệ đóng bảo hiểm y tế. Các văn bản trong kho chỉ nhắc đến bảo hiểm y tế mà không có tỷ lệ phần trăm đóng (ví dụ Điều 168 Bộ luật Lao động 2019 chỉ viện dẫn pháp luật về bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp); luật về bảo hiểm y tế không thuộc 10 văn bản đã thu thập. Các tỷ lệ phần trăm có trong kho không phải tỷ lệ đóng bảo hiểm y tế: mức đóng tối đa 1% là của bảo hiểm thất nghiệp (Điều 33 Luật Việc làm 2025) và 30% là mức khấu trừ tiền lương tối đa hằng tháng (Điều 102 Bộ luật Lao động 2019).

**Candidate behaviour:** refused

**Candidate answer:**

> Không có thông tin về tỷ lệ bảo hiểm y tế trong cơ sở dữ liệu đã nạp. Cần truy vấn các văn bản pháp luật liên quan.


---

## 12. `78c07d79f79521bde390554a`

**Question:** Người tham gia bảo hiểm tai nạn lao động tự nguyện không đóng đúng thời điểm theo quy định thì được coi là ở trạng thái nào? Nếu muốn đóng tiếp thì phải làm thủ tục gì?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Được coi là tạm dừng đóng. Nếu tiếp tục đóng, người lao động phải đăng ký lại phương thức đóng theo Điều 17 của Nghị định 143/2024/NĐ-CP.

**Reference evidence:**
- `ND143_2024_Dieu_13`: Khi quá thời điểm đóng bảo hiểm tai nạn lao động tự nguyện theo quy định tại điểm b khoản 4 Điều 11 của Nghị định này mà người lao động tham gia bảo hiểm tai nạn lao động tự nguyện không đóng bảo hiểm thì được coi là tạm dừng đóng bảo hiểm tai nạn lao động tự nguyện
- `ND143_2024_Dieu_13`: phải đăng ký lại phương thức đóng theo quy định tại Điều 17 của Nghị định này

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Nghị định 143/2024/NĐ-CP (BHTNLĐ tự nguyện), người lao động tham gia bảo hiểm tai nạn lao động tự nguyện không đóng theo thời điểm quy định sẽ bị coi là 'tạm dừng' đóng. Để tiếp tục đóng, họ phải đăng ký lại phương thức đóng theo quy định tại Điều 17 của Nghị định này.

**Candidate citations:** `ND143_2024_Dieu_13`

<details><summary>Source `ND143_2024_Dieu_13` — Điều 13. Tạm dừng đóng bảo hiểm tai nạn lao động tự nguyện</summary>

Điều 13. Tạm dừng đóng bảo hiểm tai nạn lao động tự nguyện 1. Khi quá thời điểm đóng bảo hiểm tai nạn lao động tự nguyện theo quy định tại điểm b khoản 4 Điều 11 của Nghị định này mà người lao động tham gia bảo hiểm tai nạn lao động tự nguyện không đóng bảo hiểm thì được coi là tạm dừng đóng bảo hiểm tai nạn lao động tự nguyện. 2. Người đang tạm dừng đóng bảo hiểm tai nạn lao động tự nguyện, nếu tiếp tục đóng thì phải đăng ký lại phương thức đóng theo quy định tại Điều 17 của Nghị định này.

</details>


---

## 13. `7b52fc5cacd6ee1f277813f1`

**Question:** Người lao động đủ điều kiện hưởng trợ cấp thất nghiệp, có tháng cuối cùng đóng bảo hiểm thất nghiệp là tháng 4 năm 2026, làm việc cho người sử dụng lao động hoạt động trên địa bàn thuộc vùng I. Theo Luật Việc làm 2025 và mức lương tối thiểu tháng theo vùng quy định tại Nghị định 293/2025/NĐ-CP, mức trợ cấp thất nghiệp hằng tháng tối đa người này có thể được hưởng là bao nhiêu đồng?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Tối đa 26.550.000 đồng/tháng. Khoản 1 Điều 39 Luật Việc làm 2025 giới hạn mức hưởng hằng tháng tối đa không quá 05 lần mức lương tối thiểu tháng theo vùng áp dụng tại tháng cuối cùng đóng bảo hiểm thất nghiệp; khoản 1 Điều 3 Nghị định 293/2025/NĐ-CP quy định mức lương tối thiểu tháng vùng I là 5.310.000 đồng; 05 x 5.310.000 = 26.550.000 đồng.

**Reference evidence:**
- `LVL2025_Dieu_39`: tối đa không quá 05 lần mức lương tối thiểu tháng theo vùng do Chính phủ công bố được áp dụng tại tháng cuối cùng đóng bảo hiểm thất nghiệp
- `ND293_2025_Dieu_3`: Vùng I 5.310.000 25.500
- `ND293_2025_Dieu_3`: Người sử dụng lao động hoạt động trên địa bàn thuộc vùng nào thì áp dụng mức lương tối thiểu quy định đối với địa bàn đó

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Luật Việc làm 2025 và Nghị định 293/2025/NĐ-CP, mức trợ cấp thất nghiệp được tính theo vùng. Đối với người lao động thuộc vùng I, mức lương tối thiểu tháng theo vùng quy định là X đồng/tháng (dựa trên nội dung văn bản). Tuy nhiên, mức trợ cấp thất nghiệp thường là 50% - 70% của mức lương tối thiểu trong các trường hợp cụ thể (cần xác định chi tiết về tỷ lệ này trong Luật Việc làm 2025).
> 
> Lưu ý: Thông tin chính xác về con số tiền trợ cấp cụ thể cần dựa vào văn bản pháp luật hiện hành. Nếu có điều chỉnh sau khi tra cứu, thông tin này có thể thay đổi.

<details><summary>Source `LVL2025_Dieu_39` — Điều 39. Mức hưởng, thời gian hưởng, thời điểm hưởng và hồ sơ, trình tự, thủ tục hưởng trợ cấp thất nghiệp</summary>

Điều 39. Mức hưởng, thời gian hưởng, thời điểm hưởng và hồ sơ, trình tự, thủ tục hưởng trợ cấp thất nghiệp 1. Mức hưởng trợ cấp thất nghiệp hằng tháng bằng 60% mức bình quân tiền lương tháng đóng bảo hiểm thất nghiệp của 06 tháng đã đóng bảo hiểm thất nghiệp gần nhất trước khi chấm dứt hợp đồng lao động, hợp đồng làm việc hoặc chấm dứt làm việc nhưng tối đa không quá 05 lần mức lương tối thiểu tháng theo vùng do Chính phủ công bố được áp dụng tại tháng cuối cùng đóng bảo hiểm thất nghiệp. 2. Thời gian hưởng trợ cấp thất nghiệp được tính theo số tháng đóng bảo hiểm thất nghiệp, cứ đóng đủ 12 tháng đến đủ 36 tháng thì được hưởng 03 tháng trợ cấp thất nghiệp, sau đó, cứ đóng đủ thêm 12 tháng thì được hưởng thêm 01 tháng trợ cấp thất nghiệp nhưng thời gian hưởng trợ cấp thất nghiệp tối đa 12 tháng. 3. Thời điểm hưởng trợ cấp thất nghiệp là ngày làm việc thứ 11 kể từ ngày nộp đủ hồ sơ hưởng trợ cấp thất nghiệp. 4. Người lao động đang hưởng trợ cấp thất nghiệp được hưởng chế độ bảo hiểm y tế theo quy định của pháp luật về bảo hiểm y tế, bao gồm thời gian tạm dừng hưởng trợ cấp thất nghiệp theo quy định tại khoản 2 Điều 41 của Luật này. Người đang hưởng trợ cấp thất nghiệp được cơ quan bảo hiểm xã hội đóng bảo hiểm y tế từ Quỹ bảo hiểm thất nghiệp. 5. Chính phủ quy định chi tiết khoản 1 và khoản 2 Điều này; quy định hồ sơ, trình tự, thủ tục hưởng trợ cấp thất nghiệp.

</details>

<details><summary>Source `ND293_2025_Dieu_3` — Điều 3. Mức lương tối thiểu</summary>

Điều 3. Mức lương tối thiểu 1. Quy định mức lương tối thiểu tháng và mức lương tối thiểu giờ đối với người lao động làm việc cho người sử dụng lao động theo vùng như sau: Vùng Mức lương tối thiểu tháng Mức lương tối thiểu giờ (Đơn vị: đồng/tháng) (Đơn vị: đồng/giờ) Vùng I 5.310.000 25.500 Vùng II 4.730.000 22.700 Vùng III 4.140.000 20.000 Vùng IV 3.700.000 17.800 2. Danh mục địa bàn vùng I, vùng II, vùng III, vùng IV được quy định tại Phụ lục ban hành kèm theo Nghị định này. 3. Việc áp dụng địa bàn vùng được xác định theo nơi hoạt động của người sử dụng lao động như sau: a) Người sử dụng lao động hoạt động trên địa bàn thuộc vùng nào thì áp dụng mức lương tối thiểu quy định đối với địa bàn đó. b) Người sử dụng lao động có đơn vị, chi nhánh hoạt động trên các địa bàn có mức lương tối thiểu khác nhau thì đơn vị, chi nhánh hoạt động ở địa bàn nào, áp dụng mức lương tối thiểu quy định đối với địa bàn đó. c) Người sử dụng lao động hoạt động trong khu công nghiệp, khu chế xuất, khu công nghệ cao, khu công nghệ số tập trung nằm trên các địa bàn có mức lương tối thiểu khác nhau thì áp dụng theo địa bàn có mức lương tối thiểu cao nhất. d) Người sử dụng lao động hoạt động trên địa bàn có sự thay đổi tên hoặc chia thì tạm thời áp dụng mức lương tối thiểu quy định đối với địa bàn trước khi thay đổi tên hoặc chia cho đến khi Chính phủ có quy định mới. đ) Người sử dụng lao động hoạt động trên địa bàn được thành lập mới từ một địa bàn hoặc nhiều địa bàn có mức lương tối thiểu khác nhau thì áp dụng mức lương tối thiểu theo địa bàn có mức lương tối thiểu cao nhất cho đến khi Chính phủ có quy định mới.

</details>


---

## 14. `8e129c37cc250c619c8bf2f3`

**Question:** Công ty trả lương chậm cho nhân viên thì bị cơ quan nhà nước xử phạt vi phạm hành chính bao nhiêu tiền?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Kho dữ liệu không nêu mức tiền xử phạt vi phạm hành chính. Điều 217 Bộ luật Lao động 2019 chỉ dẫn chung việc xử phạt vi phạm hành chính theo pháp luật, không có số tiền; nghị định xử phạt không nằm trong kho. Khoản 4 Điều 97 chỉ quy định việc đền bù cho người lao động (ít nhất bằng số tiền lãi theo lãi suất huy động tiền gửi có kỳ hạn 01 tháng) khi chậm trả lương từ 15 ngày trở lên trong trường hợp bất khả kháng; đó là khoản đền bù, không phải tiền phạt hành chính.

**Candidate behaviour:** refused

**Candidate answer:**

> Không có thông tin chi tiết về mức phạt hành chính cụ thể trong văn bản đã tra cứu.


---

## 15. `910043dbcc5fc50a3d9e19f9`

**Question:** Doanh nghiệp trốn đóng bảo hiểm xã hội sẽ bị phạt hành chính bao nhiêu tiền (tính bằng đồng) cho mỗi lần vi phạm?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Corpus không trả lời: không có mức tiền phạt hành chính bằng đồng đối với trốn đóng bảo hiểm xã hội. Nghị định 274/2025 chỉ quy định khoản tiền phải nộp 0,03%/ngày và thời điểm tính trốn đóng; mức xử phạt hành chính không được nêu trong corpus.

**Candidate behaviour:** refused

**Candidate answer:**

> Không tìm thấy trong tài liệu đã nạp các con số cụ thể (tổng cộng) cho phạt hành chính, chỉ có quy định tỷ lệ. Cần hỏi thêm về khoảng thời gian chậm đóng hoặc tổng tiền để đưa ra kết luận chính xác.


---

## 16. `939d14cc5d0fbea89c30f187`

**Question:** Thời gian làm việc trước ngày 01/01/2021 ở nơi có phụ cấp khu vực hệ số 0,7 trở lên có được tính vào 15 năm làm việc ở vùng khó khăn để nghỉ hưu sớm theo Nghị định 135/2020 không? Thông tư về danh mục vùng xác định thời gian đó như thế nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Có. Theo Điều 5 khoản 1 điểm b Nghị định 135/2020, 15 năm làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn bao gồm cả thời gian làm việc ở nơi có phụ cấp khu vực hệ số 0,7 trở lên trước ngày 01/01/2021. Thông tư (Điều 4 khoản 2 điểm a) quy định thời gian làm việc trước ngày 01/01/2021 ở nơi có phụ cấp khu vực hệ số 0,7 trở lên hoặc từ 25% trở lên được xác định là thời gian làm việc ở vùng này.

**Reference evidence:**
- `ND135_2020_Dieu_5`: Người lao động có từ đủ 15 năm trở lên làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn, bao gồm cả thời gian làm việc ở nơi có phụ cấp khu vực hệ số 0,7 trở lên trước ngày 01 tháng 01 năm 2021
- `TT26_2025_Dieu_4`: Thời gian người lao động làm việc trước ngày 01 tháng 01 năm 2021 ở nơi có phụ cấp khu vực hệ số 0,7 trở lên hoặc nơi có phụ cấp khu vực từ mức 25% trở lên được xác định là thời gian làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn

**Candidate behaviour:** answered

**Candidate answer:**

> Nghị định 135/2020/NĐ-CP (tuổi nghỉ hưu) quy định: Người lao động có từ đủ 15 năm làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn (bao gồm thời gian làm việc ở nơi có phụ cấp khu vực hệ số 0,7 trở lên trước ngày 01/01/2021) và không được nghỉ hưu sớm hơn 05 tuổi so với tuổi nghỉ hưu quy định tại Điều 4. Bộ trưởng Bộ Lao động - Thương binh và Xã hội ban hành danh mục vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn.

**Candidate citations:** `ND135_2020_Dieu_5`

<details><summary>Source `ND135_2020_Dieu_5` — Điều 5. Nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường</summary>

Điều 5. Nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường Nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường của người lao động theo khoản 3 Điều 169 của Bộ luật Lao động được quy định cụ thể như sau: 1. Người lao động thuộc các trường hợp dưới đây có thể nghỉ hưu ở tuổi thấp hơn nhưng không quá 05 tuổi so với tuổi nghỉ hưu quy định tại Điều 4 của Nghị định này tại thời điểm nghỉ hưu, trừ trường hợp pháp luật có quy định khác: a) Người lao động có từ đủ 15 năm trở lên làm nghề, công việc nặng nhọc, độc hại, nguy hiểm hoặc đặc biệt nặng nhọc, độc hại, nguy hiểm thuộc danh mục do Bộ Lao động - Thương binh và Xã hội ban hành. b) Người lao động có từ đủ 15 năm trở lên làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn, bao gồm cả thời gian làm việc ở nơi có phụ cấp khu vực hệ số 0,7 trở lên trước ngày 01 tháng 01 năm 2021. Bộ trưởng Bộ Lao động - Thương binh và Xã hội ban hành danh mục vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn. c) Người lao động bị suy giảm khả năng lao động từ 61% trở lên. d) Người lao động có tổng thời gian làm nghề, công việc quy định tại điểm a và thời gian làm việc ở vùng quy định tại điểm b khoản này từ đủ 15 năm trở lên. 2. Tuổi nghỉ hưu thấp nhất của người lao động quy định tại khoản 1 Điều này được thực hiện theo bảng dưới đây: Lao động nam Lao động nữ Năm nghỉ hưu Tuổi nghỉ hưu thấp nhất Năm nghỉ hưu Tuổi nghỉ hưu thấp nhất 2021 55 tuổi 3 tháng 2021 50 tuổi 4 tháng 2022 55 tuổi 6 tháng 2022 50 tuổi 8 tháng 2023 55 tuổi 9 tháng 2023 51 tuổi 2024 56 tuổi 2024 51 tuổi 4 tháng 2025 56 tuổi 3 tháng 2025 51 tuổi 8 tháng 2026 56 tuổi 6 tháng 2026 52 tuổi 2027 56 tuổi 9 tháng 2027 52 tuổi 4 tháng Từ năm 2028 trở đi 57 tuổi 2028 52 tuổi 8 tháng 2029 53 tuổi 2030 53 tuổi 4 tháng 2031 53 tuổi 8 tháng 2032 54 tuổi 2033 54 tuổi 4 tháng 2034 54 tuổi 8 tháng Từ năm 2035 trở đi 55 tuổi Việc đối chiếu tháng, năm sinh của người lao động tương ứng với tuổi nghỉ hưu quy định tại khoản này theo Phụ lục II ban hành kèm theo Nghị định này.

</details>

<details><summary>Source `TT26_2025_Dieu_4` — Điều 4. Hiệu lực thi hành</summary>

Điều 4. Hiệu lực thi hành 1. Thông tư này có hiệu lực thi hành kể từ ngày 01 tháng 01 năm 2026. 2. Các quy định tại Thông tư này được áp dụng từ ngày 01 tháng 01 năm 2026. a) Thời gian người lao động làm việc trước ngày 01 tháng 01 năm 2021 ở nơi có phụ cấp khu vực hệ số 0,7 trở lên hoặc nơi có phụ cấp khu vực từ mức 25% trở lên được xác định là thời gian làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn để làm căn cứ xác định các trường hợp có thể nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường. b) Thời gian người lao động làm việc từ ngày 01 tháng 01 năm 2021 đến trước ngày 01 tháng 01 năm 2026 ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn để làm căn cứ xác định các trường hợp có thể nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường được áp dụng theo Danh mục vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn để làm căn cứ xác định các trường hợp có thể nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường ban hành kèm theo Thông tư số 19/2021/TT-BLĐTBXH ngày 15 tháng 12 năm 2021 của Bộ trưởng Bộ Lao động - Thương binh và Xã hội. Trong đó, thời gian người lao động làm việc từ ngày 01 tháng 7 năm 2025 đến trước ngày 01 tháng 01 năm 2026 ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn để làm căn cứ xác định các trường hợp có thể nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường được xác định theo thời gian làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn tại tháng 6 năm 2025. 2. Thông tư số 19/2021/TT-BLĐTBXH ngày 15 tháng 12 năm 2021 của Bộ trưởng Bộ Lao động - Thương binh và Xã hội ban hành Danh mục vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn để làm căn cứ xác định các trường hợp có thể nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường hết hiệu lực thi hành kể từ ngày Thông tư này có hiệu lực thi hành.

</details>


---

## 17. `9425d4195a08245cd9e516d7`

**Question:** Người sử dụng lao động cần nộp hồ sơ đề nghị cấp giấy phép lao động cho người lao động nước ngoài trong khoảng thời gian nào trước ngày người đó dự kiến làm việc theo Nghị định 219/2025?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Trong khoảng từ 60 ngày đến không ít hơn 10 ngày trước ngày người lao động nước ngoài dự kiến làm việc.

**Reference evidence:**
- `ND219_2025_Dieu_22`: Trong thời hạn 60 ngày nhưng không ít hơn 10 ngày tính đến ngày người lao động nước ngoài dự kiến làm việc

**Candidate behaviour:** clarified

**Candidate answer:**

> Trong Nghị định 219/2025/NĐ-CP, liệu điều kiện nào liên quan đến việc nộp hồ sơ trước ngày dự kiến làm việc mà vẫn chưa được chi tiết? Có cần tôi cung cấp thêm thông tin cụ thể về thời gian bắt đầu hoặc kết thúc của quá trình này không?

<details><summary>Source `ND219_2025_Dieu_22` — Điều 22. Trình tự cấp giấy phép lao động</summary>

Điều 22. Trình tự cấp giấy phép lao động 1. Trong thời hạn 60 ngày nhưng không ít hơn 10 ngày tính đến ngày người lao động nước ngoài dự kiến làm việc, người sử dụng lao động nộp hồ sơ đề nghị cấp giấy phép lao động trực tiếp hoặc thông qua dịch vụ bưu chính công ích hoặc qua thuê dịch vụ của doanh nghiệp, cá nhân hoặc qua uỷ quyền đến Trung tâm Phục vụ hành chính công tại địa phương nơi người lao động nước ngoài dự kiến làm việc. 2. Trung tâm Phục vụ hành chính công tại địa phương chuyển hồ sơ theo quy định của pháp luật về thực hiện thủ tục hành chính theo cơ chế một cửa, một cửa liên thông tại bộ phận một cửa và Cổng Dịch vụ công quốc gia đến cơ quan có thẩm quyền cấp giấy phép lao động. 3. Trong thời hạn 10 ngày làm việc, kể từ ngày nhận đủ hồ sơ đề nghị cấp giấy phép lao động, cơ quan có thẩm quyền xem xét chấp thuận nhu cầu và thực hiện cấp giấy phép lao động cho người lao động nước ngoài theo Mẫu số 04 Phụ lục ban hành kèm theo Ngh ị định này. Trường hợp không chấp thuận nhu cầu sử dụng người lao động nước ngoài hoặc không cấp giấy phép lao động cho người lao động nước ngoài phải có văn bản trả lời và nêu rõ lý do trong th ời hạn 03 ngày làm việc kể từ ngày nhận đủ hồ sơ. 4. Đối với người lao động nước ngoài theo quy định tại các điểm a và m khoản 1 Điều 2 Nghị định này, sau khi người lao động nước ngoài được cấp giấy phép lao động thì người sử dụng lao động và người lao động nước ngoài phải ký kết hợp đồng lao động bằng văn bản theo quy định của pháp luật lao động Việt Nam trước ngày dự kiến làm việc. Khi được yêu cầu, người sử dụng lao động phải gửi bản sao hợp đồng lao động đã ký kết tới cơ quan có thẩm quyền đã cấp giấy phép lao động. 5. Trường hợp người lao động nước ngoài đã được cấp giấy phép lao động có nhu cầu làm việc cho người sử dụng lao động đó tại nhiều tỉnh, thành phố trực thuộc trung ương, trước ít nhất 3 ngày dự kiến làm việc, người sử dụng lao động phải thông báo cho cơ quan có thẩm quyền nơi người lao động nước ngoài dự kiến làm việc thông tin: họ và tên, tuổi, quốc tịch, số hộ chiếu, số giấy phép lao động, tên người sử dụng lao động nước ngoài, ngày bắt đầu và ngày kết thúc làm việc không vượt quá thời hạn của giấy phép lao động đã được cấp.

</details>


---

## 18. `9bad756f7c5a1e35ae59d79d`

**Question:** Theo Nghị định 293/2025, mức lương tối thiểu tháng là mức lương thấp nhất với điều kiện người lao động phải làm việc và hoàn thành công việc như thế nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Người lao động phải làm việc đủ thời giờ làm việc bình thường trong tháng và hoàn thành định mức lao động hoặc công việc đã thỏa thuận.

**Reference evidence:**
- `ND293_2025_Dieu_4`: làm việc đủ thời giờ làm việc bình thường trong tháng và hoàn thành định mức lao động hoặc công việc đã thỏa thuận không được thấp hơn mức lương tối thiểu tháng

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Nghị định 293/2025/NĐ-CP (mức lương tối thiểu), mức lương tối thiểu tháng là mức lương thấp nhất. Người lao động phải tuân thủ yêu cầu về giờ làm việc và hoàn thành công việc để đảm bảo mức lương không thấp hơn mức lương tối thiểu tháng.

**Candidate citations:** `ND293_2025_Dieu_4`

<details><summary>Source `ND293_2025_Dieu_4` — Điều 4. Áp dụng mức lương tối thiểu</summary>

Điều 4. Áp dụng mức lương tối thiểu 1. Mức lương tối thiểu tháng là mức lương thấp nhất làm cơ sở để thỏa thuận và trả lương đối với người lao động áp dụng hình thức trả lương theo tháng, bảo đảm mức lương theo công việc hoặc chức danh của người lao động làm việc đủ thời giờ làm việc bình thường trong tháng và hoàn thành định mức lao động hoặc công việc đã thỏa thuận không được thấp hơn mức lương tối thiểu tháng. 2. Mức lương tối thiểu giờ là mức lương thấp nhất làm cơ sở để thỏa thuận và trả lương đối với người lao động áp dụng hình thức trả lương theo giờ, bảo đảm mức lương theo công việc hoặc chức danh của người lao động làm việc trong một giờ và hoàn thành định mức lao động hoặc công việc đã thỏa thuận không được thấp hơn mức lương tối thiểu giờ. 3. Đối với người lao động áp dụng hình thức trả lương theo tuần hoặc theo ngày hoặc theo sản phẩm hoặc lương khoán thì mức lương của các hình thức trả lương này nếu quy đổi theo tháng hoặc theo giờ không được thấp hơn mức lương tối thiểu tháng hoặc mức lương tối thiểu giờ. Mức lương quy đổi theo tháng hoặc theo giờ trên cơ sở thời giờ làm việc bình thường do người sử dụng lao động lựa chọn theo quy định của pháp luật lao động như sau: a) Mức lương quy đổi theo tháng bằng mức lương theo tuần nhân với 52 tuần chia cho 12 tháng; hoặc mức lương theo ngày nhân với số ngày làm việc bình thường trong tháng; hoặc mức lương theo sản phẩm, lương khoán thực hiện trong thời giờ làm việc bình thường trong tháng. b) Mức lương quy đổi theo giờ bằng mức lương theo tuần, theo ngày chia cho số giờ làm việc bình thường trong tuần, trong ngày; hoặc mức lương theo sản phẩm, lương khoán chia cho số giờ làm việc trong thời giờ làm việc bình thường để sản xuất sản phẩm, thực hiện nhiệm vụ khoán.

</details>


---

## 19. `aab057b191bc75134db8a9d5`

**Question:** Theo Luật Công đoàn 2024, kinh phí công đoàn do doanh nghiệp đóng bằng bao nhiêu phần trăm quỹ tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** 2% quỹ tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc cho người lao động.

**Reference evidence:**
- `LCD2024_Dieu_29`: Kinh phí công đoàn do cơ quan, tổ chức, đơn vị, doanh nghiệp, hợp tác xã, liên hiệp hợp tác xã đóng bằng 2% quỹ tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc cho người lao động

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Luật Công đoàn 2024, kinh phí công đoàn do doanh nghiệp đóng bằng 2% quỹ tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc.

**Candidate citations:** `LCD2024_Dieu_29`

<details><summary>Source `LCD2024_Dieu_29` — Điều 29. Tài chính công đoàn</summary>

Điều 29. Tài chính công đoàn 1. Nguồn tài chính công đoàn bao gồm: a) Đoàn phí công đoàn do đoàn viên công đoàn đóng theo quy định của Điều lệ Công đoàn Việt Nam; b) Kinh phí công đoàn do cơ quan, tổ chức, đơn vị, doanh nghiệp, hợp tác xã, liên hiệp hợp tác xã đóng bằng 2% quỹ tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc cho người lao động; c) Ngân sách nhà nước cấp hỗ trợ; d) Nguồn thu khác từ hoạt động văn hóa, thể thao, hoạt động kinh tế của Công đoàn; từ đề án, dự án do Nhà nước giao; từ viện trợ, tài trợ hợp pháp của tổ chức, cá nhân trong nước và nước ngoài theo quy định của pháp luật. 2. Chính phủ quy định phương thức, thời hạn và nguồn đóng kinh phí công đoàn; trường hợp không đóng hoặc chậm đóng kinh phí công đoàn; nội dung ngân sách nhà nước cấp hỗ trợ quy định tại điểm c khoản 1 Điều này.

</details>


---

## 20. `b9c1ddfae734d53cdae7c7c8`

**Question:** Người sử dụng lao động phát hiện người lao động gây thiệt hại trực tiếp đến tài sản của công ty và muốn xử lý kỷ luật. Thời hiệu xử lý kỷ luật lao động trong trường hợp này là bao lâu theo Bộ luật Lao động 2019?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** 12 tháng kể từ ngày xảy ra hành vi vi phạm (trường hợp hành vi liên quan trực tiếp đến tài chính, tài sản, bí mật công nghệ hoặc bí mật kinh doanh); các trường hợp khác là 06 tháng.

**Reference evidence:**
- `BLLD2019_Dieu_123`: Thời hiệu xử lý kỷ luật lao động là 06 tháng kể từ ngày xảy ra hành vi vi phạm
- `BLLD2019_Dieu_123`: trường hợp hành vi vi phạm liên quan trực tiếp đến tài chính, tài sản, tiết lộ bí mật công nghệ, bí mật kinh doanh của người sử dụng lao động thì thời hiệu xử lý kỷ luật lao động là 12 tháng

**Candidate behaviour:** refused

**Candidate answer:**

> Không thể xác thực căn cứ pháp lý sau 2 lần thử sửa chữa. Chi tiết vi phạm: Trích nguyên văn của 'BLLD2019_Dieu_123' không nằm trong văn bản nguồn. Đọc lại nguồn hoặc bỏ trường exact_quote nếu chỉ diễn giải.

<details><summary>Source `BLLD2019_Dieu_123` — Điều 123. Thời hiệu xử lý kỷ luật lao động</summary>

Điều 123. Thời hiệu xử lý kỷ luật lao động 1. Thời hiệu xử lý kỷ luật lao động là 06 tháng kể từ ngày xảy ra hành vi vi phạm; trường hợp hành vi vi phạm liên quan trực tiếp đến tài chính, tài sản, tiết lộ bí mật công nghệ, bí mật kinh doanh của người sử dụng lao động thì thời hiệu xử lý kỷ luật lao động là 12 tháng. 2. Khi hết thời gian quy định tại khoản 4 Điều 122 của Bộ luật này, nếu hết thời hiệu hoặc còn thời hiệu nhưng không đủ 60 ngày thì được kéo dài thời hiệu để xử lý kỷ luật lao động nhưng không quá 60 ngày kể từ ngày hết thời gian nêu trên. 3. Người sử dụng lao động phải ban hành quyết định xử lý kỷ luật lao động trong thời hạn quy định tại khoản 1 và khoản 2 Điều này.

</details>


---

## 21. `c07829457a899dc76bbe372f`

**Question:** Theo Nghị định 219/2025/NĐ-CP, người nước ngoài là chủ sở hữu công ty trách nhiệm hữu hạn muốn không phải xin giấy phép lao động khi làm việc tại Việt Nam thì giá trị góp vốn tối thiểu là bao nhiêu? Bộ luật Lao động 2019 quy định mức này như thế nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Theo Bộ luật Lao động 2019 (Điều 154 khoản 1), giá trị góp vốn do Chính phủ quy định; Nghị định 219/2025 (Điều 7 khoản 2) quy định từ 3 tỷ đồng trở lên.

**Reference evidence:**
- `BLLD2019_Dieu_154`: Là chủ sở hữu hoặc thành viên góp vốn của công ty trách nhiệm hữu hạn có giá trị góp vốn theo quy định của Chính phủ
- `ND219_2025_Dieu_7`: Là chủ sở hữu hoặc thành viên góp vốn có giá trị góp vốn từ 3 tỷ đồng trở lên của công ty trách nhiệm hữu hạn

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Nghị định 219/2025/NĐ-CP (Điều 7), giá trị góp vốn tối thiểu cho chủ sở hữu hoặc thành viên góp vốn của công ty trách nhiệm hữu hạn là **3 tỷ đồng**. Tuy nhiên, theo Luật Lao động 2019 (Điều 154), quy định chung rằng người lao động nước ngoài có giá trị góp vốn theo quy định của Chính phủ. Để chính xác hóa mức giá trị này, cần tham chiếu các văn bản liên quan cụ thể hơn.

**Candidate citations:** `ND219_2025_Dieu_7`

<details><summary>Source `BLLD2019_Dieu_154` — Điều 154. Người lao động nước ngoài làm việc tại Việt Nam không thuộc diện cấp giấy phép lao động</summary>

Điều 154. Người lao động nước ngoài làm việc tại Việt Nam không thuộc diện cấp giấy phép lao động 1. Là chủ sở hữu hoặc thành viên góp vốn của công ty trách nhiệm hữu hạn có giá trị góp vốn theo quy định của Chính phủ. 2. Là Chủ tịch Hội đồng quản trị hoặc thành viên Hội đồng quản trị của công ty cổ phần có giá trị góp vốn theo quy định của Chính phủ. 3. Là Trưởng văn phòng đại diện, dự án hoặc chịu trách nhiệm chính về hoạt động của tổ chức quốc tế, tổ chức phi chính phủ nước ngoài tại Việt Nam. 4. Vào Việt Nam với thời hạn dưới 03 tháng để thực hiện chào bán dịch vụ. 5. Vào Việt Nam với thời hạn dưới 03 tháng để xử lý sự cố, tình huống kỹ thuật, công nghệ phức tạp nảy sinh làm ảnh hưởng hoặc có nguy cơ ảnh hưởng tới sản xuất, kinh doanh mà các chuyên gia Việt Nam và các chuyên gia nước ngoài hiện đang ở Việt Nam không xử lý được. 6. Là luật sư nước ngoài đã được cấp Giấy phép hành nghề luật sư tại Việt Nam theo quy định của Luật Luật sư. 7. Trường hợp theo quy định của điều ước quốc tế mà nước Cộng hòa xã hội chủ nghĩa Việt Nam là thành viên. 8. Người nước ngoài kết hôn với người Việt Nam và sinh sống trên lãnh thổ Việt Nam. 9. Trường hợp khác theo quy định của Chính phủ.

</details>

<details><summary>Source `ND219_2025_Dieu_7` — Điều 7. Người lao động nước ngoài không thu ộc diện cấp giấy phép lao đ ộng</summary>

Điều 7. Người lao động nước ngoài không thu ộc diện cấp giấy phép lao đ ộng 1. Thuộc một trong các trường hợp quy định tại các khoản 3, 4, 5, 6, 7 và 8 Điều 154 của Bộ luật Lao động. 2. Là chủ sở hữu hoặc thành viên góp vốn có giá trị góp vốn từ 3 tỷ đồng trở lên của công ty trách nhiệm hữu hạn. 3. Là Chủ tịch Hội đồng quản trị hoặc thành viên Hội đồng quản trị có giá trị góp vốn từ 3 tỷ đồng trở lên của công ty cổ phần. 4. Vào Việt Nam để cung cấp dịch vụ tư vấn về chuyên môn và kỹ thuật hoặc thực hiện các nhiệm vụ khác phục vụ cho công tác nghiên cứu, xây dựng, thẩm định, theo dõi đánh giá, quản lý và thực hiện chương trình, dự án sử dụng nguồn hỗ trợ phát triển chính thức theo quy định hay thỏa thuận trong các điều ước quốc tế về nguồn hỗ trợ phát triển chính thức đã ký kết giữa cơ quan có thẩm quyền của Việt Nam và nước ngoài. 5. Phóng viên nước ngoài hoạt động thông tin báo chí đư ợc Bộ Ngoại giao xác nh ận. 6. Được cơ quan, tổ chức có thẩm quyền của nước ngoài cử sang Việt Nam giảng dạy, làm nhà quản lý, giám đốc điều hành tại cơ sở giáo dục do cơ quan đại diện ngoại giao nước ngoài, tổ chức liên chính phủ đề nghị thành lập tại Việt Nam hoặc các cơ sở, tổ chức được thành lập theo các đi ều ước quốc tế mà Việt Nam đã ký kết, tham gia. 7. Học sinh, sinh viên , học viên nước ngoài đang học tập tại các trường, cơ sở đào tạo ở Việt Nam hoặc nước ngoài có thỏa thuận thực tập hoặc thư mời làm việc cho người sử dụng lao động tại Việt Nam; học viên thực tập, tập sự trên tàu biển Việt Nam. 8. Thân nhân thành viên cơ quan đại diện nước ngoài tại Việt Nam được phép làm việc tại Việt Nam theo quy định tại điều ước quốc tế mà nước Cộng hòa xã hội chủ nghĩa Việt Nam là thành viên. 9. Có hộ chiếu công vụ vào làm việc cho cơ quan nhà nước, tổ chức chính trị, tổ chức chính trị - xã hội. 10. Người chịu trách nhiệm thành lập hiện diện thương mại. 11. Tình nguyện viên làm việc tại Việt Nam theo hình thức tự nguyện và không hưởng lương để thực hiện điều ước quốc tế mà nước Cộng hòa xã hội chủ nghĩa Việt Nam là thành viên và có xác nh ận của cơ quan đại diện ngoại giao nước ngoài hoặc tổ chức quốc tế tại Việt Nam. 12. Vào Việt Nam thực hiện thỏa thuận quốc tế mà cơ quan, tổ chức ở Trung ương, cấp tỉnh ký kết theo quy định của pháp luật. 13. Người lao động nước ngoài là nhà quản lý, giám đốc điều hành, chuyên gia, lao động kỹ thuật thuộc một trong các trường hợp sau: a) Vào Việt Nam làm việc có tổng thời gian dư ới 90 ngày trong 01 năm , tính từ 01 tháng 01 đ ến ngày cuối cùng c ủa năm; b) Di chuyển trong nội bộ doanh nghi ệp: Di chuyển có thời hạn trong nội bộ doanh nghiệp nước ngoài đã thành lập hiện diện thương mại trên lãnh thổ Việt Nam thuộc phạm vi 11 ngành dịch vụ theo biểu cam kết dịch vụ của Việt Nam với tổ chức thương mại thế giới và đã được doanh nghiệp nước ngoài tuyển dụng trước đó ít nhất 12 tháng liên tục. Hiện diện thương mại bao gồm tổ chức kinh tế có vốn đầu tư nước ngoài; văn phòng đ ại diện, chi nhánh của thương nhân nước ngoài tại Việt Nam; văn phòng điều hành của nhà đầu tư nước ngoài trong h ợp đồng hợp tác kinh doanh. 14. Được Bộ Giáo dục và Đào tạo xác nhận vào Việt Nam để thực hiện các công việc sau: a) Giảng dạy, nghiên cứu, chuyển giao chương trình giáo dục quốc tế; b) Làm nhà quản lý, giám đốc điều hành, hiệu trưởng, phó hiệu trưởng cơ sở giáo dục do cơ quan đại diện ngoại giao nước ngoài hoặc tổ chức liên chính ph ủ đề nghị thành lập tại Việt Nam. 15. Được các bộ, cơ quan ngang bộ hoặc Ủy ban nhân dân cấp tỉnh xác nhận vào Việt Nam làm việc trong các lĩnh vực: tài chính, khoa học, công nghệ, đổi mới sáng tạo, chuyển đổi số quốc gia, các lĩnh vực ưu tiên phát triển kinh tế - xã hội.

</details>


---

## 22. `c92f424da4b853885d007838`

**Question:** Lao động nữ nghỉ thai sản thì được trợ cấp thai sản từ bảo hiểm xã hội bằng bao nhiêu phần trăm tiền lương?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Corpus không trả lời: Bộ luật Lao động Điều 139 chỉ nói lao động nữ được hưởng chế độ thai sản theo pháp luật về bảo hiểm xã hội; mức trợ cấp thai sản không có trong corpus.

**Candidate behaviour:** clarified

**Candidate answer:**

> Trong các văn bản tra cứu (Bộ luật Lao động 2019), có câu nhắc đến mức trợ cấp theo tỷ lệ lương cho thời gian nghỉ thai sản không? Nếu vậy, con số cụ thể là bao nhiêu phần trăm?


---

## 23. `ce1bc87ce016b02a401ba812`

**Question:** Theo khoản 1 Điều 5 Nghị định 135/2020/NĐ-CP, người lao động bị suy giảm khả năng lao động từ 61% trở lên có thể nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường không, và thấp hơn tối đa bao nhiêu tuổi?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Có. Theo khoản 1 Điều 5 Nghị định 135/2020/NĐ-CP (điểm c), người lao động bị suy giảm khả năng lao động từ 61% trở lên có thể nghỉ hưu ở tuổi thấp hơn nhưng không quá 05 tuổi so với tuổi nghỉ hưu quy định tại Điều 4 của Nghị định tại thời điểm nghỉ hưu, trừ trường hợp pháp luật có quy định khác.

**Reference evidence:**
- `ND135_2020_Dieu_5`: c) Người lao động bị suy giảm khả năng lao động từ 61% trở lên.
- `ND135_2020_Dieu_5`: nhưng không quá 05 tuổi so với tuổi nghỉ hưu quy định tại Điều 4 của Nghị định này tại thời điểm nghỉ hưu

**Candidate behaviour:** clarified

**Candidate answer:**

> Theo Điều 5 Nghị định 135/2020/NĐ-CP quy định về việc điều chỉnh tuổi nghỉ hưu trong điều kiện lao động bình thường, có thông tin chi tiết về con số tuổi nghỉ hưu thấp nhất hay không?

<details><summary>Source `ND135_2020_Dieu_5` — Điều 5. Nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường</summary>

Điều 5. Nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường Nghỉ hưu ở tuổi thấp hơn tuổi nghỉ hưu trong điều kiện lao động bình thường của người lao động theo khoản 3 Điều 169 của Bộ luật Lao động được quy định cụ thể như sau: 1. Người lao động thuộc các trường hợp dưới đây có thể nghỉ hưu ở tuổi thấp hơn nhưng không quá 05 tuổi so với tuổi nghỉ hưu quy định tại Điều 4 của Nghị định này tại thời điểm nghỉ hưu, trừ trường hợp pháp luật có quy định khác: a) Người lao động có từ đủ 15 năm trở lên làm nghề, công việc nặng nhọc, độc hại, nguy hiểm hoặc đặc biệt nặng nhọc, độc hại, nguy hiểm thuộc danh mục do Bộ Lao động - Thương binh và Xã hội ban hành. b) Người lao động có từ đủ 15 năm trở lên làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn, bao gồm cả thời gian làm việc ở nơi có phụ cấp khu vực hệ số 0,7 trở lên trước ngày 01 tháng 01 năm 2021. Bộ trưởng Bộ Lao động - Thương binh và Xã hội ban hành danh mục vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn. c) Người lao động bị suy giảm khả năng lao động từ 61% trở lên. d) Người lao động có tổng thời gian làm nghề, công việc quy định tại điểm a và thời gian làm việc ở vùng quy định tại điểm b khoản này từ đủ 15 năm trở lên. 2. Tuổi nghỉ hưu thấp nhất của người lao động quy định tại khoản 1 Điều này được thực hiện theo bảng dưới đây: Lao động nam Lao động nữ Năm nghỉ hưu Tuổi nghỉ hưu thấp nhất Năm nghỉ hưu Tuổi nghỉ hưu thấp nhất 2021 55 tuổi 3 tháng 2021 50 tuổi 4 tháng 2022 55 tuổi 6 tháng 2022 50 tuổi 8 tháng 2023 55 tuổi 9 tháng 2023 51 tuổi 2024 56 tuổi 2024 51 tuổi 4 tháng 2025 56 tuổi 3 tháng 2025 51 tuổi 8 tháng 2026 56 tuổi 6 tháng 2026 52 tuổi 2027 56 tuổi 9 tháng 2027 52 tuổi 4 tháng Từ năm 2028 trở đi 57 tuổi 2028 52 tuổi 8 tháng 2029 53 tuổi 2030 53 tuổi 4 tháng 2031 53 tuổi 8 tháng 2032 54 tuổi 2033 54 tuổi 4 tháng 2034 54 tuổi 8 tháng Từ năm 2035 trở đi 55 tuổi Việc đối chiếu tháng, năm sinh của người lao động tương ứng với tuổi nghỉ hưu quy định tại khoản này theo Phụ lục II ban hành kèm theo Nghị định này.

</details>


---

## 24. `ce27ece052b60a8d72688f95`

**Question:** Người sử dụng lao động và người lao động phải đóng bảo hiểm y tế với tỷ lệ bao nhiêu phần trăm tiền lương hiện hành?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Kho dữ liệu không nêu tỷ lệ đóng bảo hiểm y tế. Các văn bản trong kho chỉ nhắc đến bảo hiểm y tế mà không có tỷ lệ phần trăm đóng (ví dụ Điều 168 Bộ luật Lao động 2019 chỉ viện dẫn pháp luật về bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp); luật về bảo hiểm y tế không thuộc 10 văn bản đã thu thập. Các tỷ lệ phần trăm có trong kho không phải tỷ lệ đóng bảo hiểm y tế: mức đóng tối đa 1% là của bảo hiểm thất nghiệp (Điều 33 Luật Việc làm 2025) và 30% là mức khấu trừ tiền lương tối đa hằng tháng (Điều 102 Bộ luật Lao động 2019).

**Candidate behaviour:** answered

**Candidate answer:**

> Cần tra cứu lại để tìm quy định cụ thể về tỷ lệ bảo hiểm y tế. Tuy nhiên, trong Bộ luật Lao động 2019 hiện hành (Điều 168: Người lao động phải tham gia bảo hiểm xã hội, bảo hiểm y tế và thất nghiệp nhưng không quy định tỷ lệ chi trả lương; Điều 102: Khấu trừ tiền lương chỉ cho 30% lương. Nếu chưa có văn bản chính thức quy định tỷ lệ cụ thể, đây là thông tin dựa trên quy định chung.


---

## 25. `d9031b3db784bdcf17c5f807`

**Question:** Người đóng đủ 20 năm bảo hiểm xã hội khi nghỉ hưu thì được hưởng lương hưu bằng bao nhiêu phần trăm mức bình quân tiền lương đóng bảo hiểm?

**Expected behaviour:** refuse  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Corpus không trả lời: tỷ lệ hưởng lương hưu theo số năm đóng nằm trong Luật Bảo hiểm xã hội, không có trong corpus. Điều 7 khoản 3 của Nghị định 135/2020 chỉ viện dẫn 'tỷ lệ hưởng lương hưu' mà không nêu tỷ lệ.

**Candidate behaviour:** clarified

**Candidate answer:**

> Người hỏi cần biết chính xác con số cụ thể (tỷ lệ %) hay thông tin khác về quy định lương hưu?


---

## 26. `e7c2b1749bbc679df1f2874e`

**Question:** Theo Nghị định 293/2025/NĐ-CP, mức lương tối thiểu giờ áp dụng cho vùng IV là bao nhiêu đồng một giờ?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** 17.800 đồng/giờ (mức lương tối thiểu tháng của vùng IV là 3.700.000 đồng/tháng).

**Reference evidence:**
- `ND293_2025_Dieu_3`: Vùng IV 3.700.000 17.800

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Nghị định 293/2025/NĐ-CP, mức lương tối thiểu giờ áp dụng cho vùng IV là 17.800 đồng một giờ.

**Candidate citations:** `ND293_2025_Dieu_3`

<details><summary>Source `ND293_2025_Dieu_3` — Điều 3. Mức lương tối thiểu</summary>

Điều 3. Mức lương tối thiểu 1. Quy định mức lương tối thiểu tháng và mức lương tối thiểu giờ đối với người lao động làm việc cho người sử dụng lao động theo vùng như sau: Vùng Mức lương tối thiểu tháng Mức lương tối thiểu giờ (Đơn vị: đồng/tháng) (Đơn vị: đồng/giờ) Vùng I 5.310.000 25.500 Vùng II 4.730.000 22.700 Vùng III 4.140.000 20.000 Vùng IV 3.700.000 17.800 2. Danh mục địa bàn vùng I, vùng II, vùng III, vùng IV được quy định tại Phụ lục ban hành kèm theo Nghị định này. 3. Việc áp dụng địa bàn vùng được xác định theo nơi hoạt động của người sử dụng lao động như sau: a) Người sử dụng lao động hoạt động trên địa bàn thuộc vùng nào thì áp dụng mức lương tối thiểu quy định đối với địa bàn đó. b) Người sử dụng lao động có đơn vị, chi nhánh hoạt động trên các địa bàn có mức lương tối thiểu khác nhau thì đơn vị, chi nhánh hoạt động ở địa bàn nào, áp dụng mức lương tối thiểu quy định đối với địa bàn đó. c) Người sử dụng lao động hoạt động trong khu công nghiệp, khu chế xuất, khu công nghệ cao, khu công nghệ số tập trung nằm trên các địa bàn có mức lương tối thiểu khác nhau thì áp dụng theo địa bàn có mức lương tối thiểu cao nhất. d) Người sử dụng lao động hoạt động trên địa bàn có sự thay đổi tên hoặc chia thì tạm thời áp dụng mức lương tối thiểu quy định đối với địa bàn trước khi thay đổi tên hoặc chia cho đến khi Chính phủ có quy định mới. đ) Người sử dụng lao động hoạt động trên địa bàn được thành lập mới từ một địa bàn hoặc nhiều địa bàn có mức lương tối thiểu khác nhau thì áp dụng mức lương tối thiểu theo địa bàn có mức lương tối thiểu cao nhất cho đến khi Chính phủ có quy định mới.

</details>


---

## 27. `eaf299e0be0b54ca8ad5e1e9`

**Question:** Luật Công đoàn 2024 có hiệu lực thi hành từ ngày nào, và Luật Công đoàn 2012 hết hiệu lực vào thời điểm nào?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Luật có hiệu lực từ ngày 01/7/2025. Luật Công đoàn số 12/2012/QH13 hết hiệu lực từ ngày Luật Công đoàn 2024 có hiệu lực.

**Reference evidence:**
- `LCD2024_Dieu_37`: Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2025
- `LCD2024_Dieu_37`: Luật Công đoàn số 12/2012/QH13 hết hiệu lực từ ngày Luật này có hiệu lực thi hành

**Candidate behaviour:** answered

**Candidate answer:**

> Dựa trên các văn bản pháp luật đã tra cứu: Điều 37 của Luật Công đoàn 2024 quy định hiệu lực thi hành từ ngày 01 tháng 7 năm 2025. Tuy nhiên, thông tin về hiệu lực cụ thể của Luật Công đoàn 2012 (thường được xác minh qua các văn bản hướng dẫn hoặc Điều 19) chưa rõ ràng trong kết quả search_law hiện tại. Vui lòng cung cấp thêm thông tin nếu cần.

<details><summary>Source `LCD2024_Dieu_37` — Điều 37. Hiệu lực thi hành</summary>

Điều 37. Hiệu lực thi hành Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2025. Luật Công đoàn số 12/2012/QH13 hết hiệu lực từ ngày Luật này có hiệu lực thi hành./. Luật này được Quốc hội nước Cộng hòa xã hội chủ nghĩa Việt Nam khóa XV, kỳ họp thứ 8 thông qua ngày 27 tháng 11 năm 2024.

</details>


---

## 28. `eb3c9a7bb1c095e46284a058`

**Question:** Người lao động đủ tuổi nghỉ hưu vào giữa tháng thì thời điểm nghỉ hưu được xác định thế nào theo Nghị định 135/2020/NĐ-CP? Nếu họ tiếp tục làm việc sau khi đủ tuổi thì sao?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Thời điểm nghỉ hưu là kết thúc ngày cuối cùng của tháng đủ tuổi nghỉ hưu. Nếu người lao động tiếp tục làm việc sau khi đủ tuổi nghỉ hưu, thời điểm nghỉ hưu là thời điểm chấm dứt hợp đồng lao động.

**Reference evidence:**
- `ND135_2020_Dieu_3`: Thời điểm nghỉ hưu là kết thúc ngày cuối cùng của tháng đủ tuổi nghỉ hưu theo quy định
- `ND135_2020_Dieu_3`: thời điểm nghỉ hưu là thời điểm chấm dứt hợp đồng lao động

**Candidate behaviour:** clarified

**Candidate answer:**

> Cần cung cấp thêm thông tin cụ thể hơn về điều kiện 'tiếp tục làm việc' sau khi đủ tuổi nghỉ hưu theo Nghị định 135/2020/NĐ-CP, hay có phải cần dựa vào quy định khác?

<details><summary>Source `ND135_2020_Dieu_3` — Điều 3. Thời điểm nghỉ hưu và thời điểm hưởng chế độ hưu trí</summary>

Điều 3. Thời điểm nghỉ hưu và thời điểm hưởng chế độ hưu trí 1. Thời điểm nghỉ hưu là kết thúc ngày cuối cùng của tháng đủ tuổi nghỉ hưu theo quy định. Đối với trường hợp người lao động tiếp tục làm việc sau khi đã đủ tuổi nghỉ hưu theo quy định thì thời điểm nghỉ hưu là thời điểm chấm dứt hợp đồng lao động. 2. Thời điểm hưởng chế độ hưu trí là bắt đầu ngày đầu tiên của tháng liền kề sau thời điểm nghỉ hưu. 3. Trường hợp hồ sơ của người lao động không xác định được ngày, tháng sinh mà chỉ có năm sinh thì lấy ngày 01 tháng 01 của năm sinh để làm căn cứ xác định thời điểm nghỉ hưu và thời điểm hưởng chế độ hưu trí.

</details>


---

## 29. `ee72c2611785852f97979c43`

**Question:** Người lao động ký hợp đồng có thời hạn 6 tháng muốn hưởng trợ cấp thất nghiệp theo Luật Việc làm 2025 thì phải đóng bảo hiểm thất nghiệp đủ bao nhiêu tháng trong bao nhiêu tháng trước khi chấm dứt hợp đồng, và nếu đóng đủ 12 tháng thì được hưởng bao nhiêu tháng trợ cấp?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Phải đóng đủ 12 tháng trở lên trong thời gian 36 tháng trước khi chấm dứt hợp đồng (Điều 38 khoản 1 điểm b); đóng đủ 12 tháng thì được hưởng 03 tháng trợ cấp thất nghiệp (Điều 39 khoản 2).

**Reference evidence:**
- `LVL2025_Dieu_38`: Trường hợp người lao động làm việc theo hợp đồng lao động có thời hạn từ đủ 01 tháng đến dưới 12 tháng thì phải đóng đủ 12 tháng trở lên trong thời gian 36 tháng trước khi chấm dứt hợp đồng lao động
- `LVL2025_Dieu_39`: cứ đóng đủ 12 tháng đến đủ 36 tháng thì được hưởng 03 tháng trợ cấp thất nghiệp

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Luật Việc làm 2025 (Điều 39):
> - Mức hưởng trợ cấp thất nghiệp hằng tháng bằng 60% mức bình quân tiền lương tháng đóng bảo hiểm thất nghiệp của 06 tháng đã đóng bảo hiểm thất nghiệp gần nhất trước khi chấm dứt hợp đồng lao động, hợp đồng làm việc hoặc chấm dứt làm việc. Thời gian này không quá 5 lần mức lương tối thiểu tháng theo vùng.

**Candidate citations:** `LVL2025_Dieu_39`

<details><summary>Source `LVL2025_Dieu_38` — Điều 38. Điều kiện hưởng</summary>

Điều 38. Điều kiện hưởng 1. Người lao động quy định tại khoản 1 Điều 31 của Luật này đang đóng bảo hiểm thất nghiệp được hưởng trợ cấp thất nghiệp khi có đủ các điều kiện sau đây: a) Chấm dứt hợp đồng lao động, hợp đồng làm việc hoặc chấm dứt làm việc theo quy định của pháp luật mà không thuộc một trong các trường hợp người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật theo quy định của Bộ luật Lao động hoặc người lao động nghỉ việc khi đủ điều kiện hưởng lương hưu. b) Đã đóng bảo hiểm thất nghiệp từ đủ 12 tháng trở lên trong thời gian 24 tháng trước khi chấm dứt hợp đồng lao động, hợp đồng làm việc hoặc chấm dứt làm việc theo quy định của pháp luật. Trường hợp người lao động làm việc theo hợp đồng lao động có thời hạn từ đủ 01 tháng đến dưới 12 tháng thì phải đóng đủ 12 tháng trở lên trong thời gian 36 tháng trước khi chấm dứt hợp đồng lao động. c) Đã nộp đủ hồ sơ hưởng trợ cấp thất nghiệp trong thời hạn 03 tháng kể từ ngày chấm dứt hợp đồng lao động, hợp đồng làm việc hoặc chấm dứt làm việc. d) Trong thời hạn 10 ngày làm việc kể từ ngày nộp đủ hồ sơ hưởng trợ cấp thất nghiệp mà người lao động không thuộc một trong các trường hợp có việc làm và thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc theo quy định tại Luật Bảo hiểm xã hội hoặc thực hiện nghĩa vụ quân sự, nghĩa vụ tham gia Công an nhân dân, dân quân thường trực hoặc đi học tập có thời hạn trên 12 tháng hoặc chấp hành quyết định áp dụng biện pháp đưa vào cơ sở giáo dục bắt buộc, cơ sở cai nghiện bắt buộc hoặc bị tạm giam, chấp hành hình phạt tù hoặc ra nước ngoài định cư hoặc chết. 2. Chính phủ quy định chi tiết Điều này.

</details>

<details><summary>Source `LVL2025_Dieu_39` — Điều 39. Mức hưởng, thời gian hưởng, thời điểm hưởng và hồ sơ, trình tự, thủ tục hưởng trợ cấp thất nghiệp</summary>

Điều 39. Mức hưởng, thời gian hưởng, thời điểm hưởng và hồ sơ, trình tự, thủ tục hưởng trợ cấp thất nghiệp 1. Mức hưởng trợ cấp thất nghiệp hằng tháng bằng 60% mức bình quân tiền lương tháng đóng bảo hiểm thất nghiệp của 06 tháng đã đóng bảo hiểm thất nghiệp gần nhất trước khi chấm dứt hợp đồng lao động, hợp đồng làm việc hoặc chấm dứt làm việc nhưng tối đa không quá 05 lần mức lương tối thiểu tháng theo vùng do Chính phủ công bố được áp dụng tại tháng cuối cùng đóng bảo hiểm thất nghiệp. 2. Thời gian hưởng trợ cấp thất nghiệp được tính theo số tháng đóng bảo hiểm thất nghiệp, cứ đóng đủ 12 tháng đến đủ 36 tháng thì được hưởng 03 tháng trợ cấp thất nghiệp, sau đó, cứ đóng đủ thêm 12 tháng thì được hưởng thêm 01 tháng trợ cấp thất nghiệp nhưng thời gian hưởng trợ cấp thất nghiệp tối đa 12 tháng. 3. Thời điểm hưởng trợ cấp thất nghiệp là ngày làm việc thứ 11 kể từ ngày nộp đủ hồ sơ hưởng trợ cấp thất nghiệp. 4. Người lao động đang hưởng trợ cấp thất nghiệp được hưởng chế độ bảo hiểm y tế theo quy định của pháp luật về bảo hiểm y tế, bao gồm thời gian tạm dừng hưởng trợ cấp thất nghiệp theo quy định tại khoản 2 Điều 41 của Luật này. Người đang hưởng trợ cấp thất nghiệp được cơ quan bảo hiểm xã hội đóng bảo hiểm y tế từ Quỹ bảo hiểm thất nghiệp. 5. Chính phủ quy định chi tiết khoản 1 và khoản 2 Điều này; quy định hồ sơ, trình tự, thủ tục hưởng trợ cấp thất nghiệp.

</details>


---

## 30. `f3a9d0ff39d7dd730e293abc`

**Question:** Khi phát hiện người sử dụng lao động chậm đóng hoặc trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp ngoài các trường hợp thuộc khoản 1 Điều 3 Nghị định 274/2025, cơ quan bảo hiểm xã hội phải đôn đốc bằng văn bản trong thời hạn bao lâu?

**Expected behaviour:** answer  
**Scope:** Knowledge base: Pháp luật lao động Việt Nam (Bộ luật Lao động 2019 và văn bản hướng dẫn). Câu hỏi nằm ngoài phạm vi các văn bản pháp luật lao động trong cơ sở dữ liệu đã nạp (Bộ luật Lao động 2019 và các văn bản liên quan).

**Reference answer:** Trong thời hạn 05 ngày làm việc, cơ quan bảo hiểm xã hội có trách nhiệm đôn đốc bằng văn bản.

**Reference evidence:**
- `ND274_2025_Dieu_3`: thì trong thời hạn 05 ngày làm việc, cơ quan bảo hiểm xã hội có trách nhiệm đôn đốc bằng văn bản

**Candidate behaviour:** answered

**Candidate answer:**

> Theo Luật Lao động 2019, Điều 3 Nghị định 274/2025 quy định cho cơ quan bảo hiểm xã hội phải đôn đốc việc đóng bảo hiểm thất nghiệp trong thời hạn **60 ngày** sau khi có báo cáo hoặc yêu cầu từ người lao động.

<details><summary>Source `ND274_2025_Dieu_3` — Điều 3. Đôn đốc thực hiện trách nhiệm đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp</summary>

Điều 3. Đôn đốc thực hiện trách nhiệm đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp Việc đôn đốc thực hiện trách nhiệm đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp theo quy định tại khoản 4 Điều 35 của Luật Bảo hiểm xã hội được quy định như sau: 1. Chậm đóng theo khoản 1 Điều 38 Luật Bảo hiểm xã hội: Hằng tháng, Giám đốc cơ quan bảo hiểm xã hội quản lý trực tiếp đối tượng tham gia bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp có trách nhiệm rà soát, xác định người sử dụng lao động chậm đóng theo khoản 1 Điều 38 Luật Bảo hiểm xã hội; trong thời hạn 10 ngày đầu tháng gửi văn bản yêu cầu người sử dụng lao động thực hiện trách nhiệm đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp theo hướng dẫn tại Phụ lục I ban hành kèm theo Nghị định này, trong đó có những nội dung chủ yếu: a) Căn cứ Điều 35, 38, 39, 40, 41 Luật Bảo hiểm xã hội và quy định của Nghị định quy định một số điều của Luật Bảo hiểm xã hội về chậm đóng, trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp; khiếu nại, tố cáo về bảo hiểm xã hội. b) Số tiền chậm đóng, trốn đóng: chi tiết từng khoản chậm đóng, trốn đóng. c) Số ngày chậm đóng, trốn đóng: chi tiết từng khoản chậm đóng, trốn đóng tính trên số ngày chậm đóng, trốn đóng. d) Số tiền phải nộp bằng 0,03%/ngày tính trên số tiền, số ngày chậm đóng, trốn đóng. đ) Quy định của pháp luật về các biện pháp xử lý hành vi chậm đóng, trốn đóng. e) Thời hạn chuyển từ hành vi chậm đóng sang hành vi trốn đóng và các biện pháp xử lý hành vi trốn đóng. g) Yêu cầu người sử dụng lao động báo cáo nguyên nhân chậm đóng (trường hợp vì lý do bất khả kháng, xảy ra khách quan không thể lường trước được và khắc phục được mặc dù đã áp dụng mọi biện pháp cần thiết và khả năng cho phép thì gửi kèm hồ sơ trước ngày 25 của tháng có văn bản đôn đốc). 2. Khi phát hiện người sử dụng lao động chậm đóng, trốn đóng không bao gồm các trường hợp quy định tại khoản 1 Điều này thì trong thời hạn 05 ngày làm việc, cơ quan bảo hiểm xã hội có trách nhiệm đôn đốc bằng văn bản những nội dung quy định tại khoản 1 Điều này yêu cầu người sử dụng lao động thực hiện trách nhiệm đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp và nêu căn cứ phát hiện, tiếp nhận thông tin hành vi chậm đóng, trốn đóng bảo hiểm xã hội bắt buộc, bảo hiểm thất nghiệp. 3. Thông tin về người sử dụng lao động chậm đóng, trốn đóng bảo hiểm xã hội bắt buộc. a) Trước ngày 15 của tháng đầu quý tiếp theo, cơ quan bảo hiểm xã hội cấp tỉnh gửi thông tin về người sử dụng lao động chậm đóng, trốn đóng tính đến hết ngày cuối quý đến cơ quan quản lý nhà nước về bảo hiểm xã hội, bảo hiểm thất nghiệp và cơ quan thanh tra có liên quan để xem xét xử lý theo thẩm quyền. b) Cơ quan bảo hiểm xã hội báo cáo về người sử dụng lao động chậm đóng, trốn đóng đột xuất với cơ quan có thẩm quyền khi có yêu cầu.

</details>
