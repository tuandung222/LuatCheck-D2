# L1 verifier: cơ chế và số liệu

> Soạn 2026-10-24 20:10 +07. Số liệu sinh bởi `evaluation/probes/l1_effect.py` →
> `evaluation/runs/l1-effect-2026-10-24/results.json` (đọc từ các run đã chấm, không chạy model, không chấm judge mới).
> Nhãn đúng/sai lấy từ LLM judge (ước lượng, chưa phải nhãn người).

## 1. L1 là gì

L1 là **bộ kiểm trích dẫn bằng luật, chạy trong code**, nằm giữa câu trả lời của controller và người dùng. Không dùng
model, không hiểu nghĩa: chỉ so chữ, so số, so mã tài liệu giữa câu trả lời và **văn bản nguồn mà câu trả lời trích**.
Chạy trong vài mili giây, kết quả xác định (cùng đầu vào → cùng kết luận).

Mục tiêu: **chặn trước khi tới người dùng** những câu trả lời trích dẫn bịa, trích tài liệu chưa đọc, trích sai nguyên
văn hoặc đưa con số không có trong nguồn.

## 2. Luồng xử lý

```
controller chọn action "answer" (nội dung + citations[{article_id, exact_quote?}])
        │
        ▼
   L1 kiểm (mục 3) ──đạt──► trả lời người dùng (kèm trích dẫn đã kiểm)
        │
     không đạt
        ▼
   phản hồi sửa (repair feedback) gửi lại controller ──► controller viết lại câu trả lời
        │                                                     │
        └──────────── tối đa 2 lần sửa ◄─────────────────────┘
        │
   hết 2 lần mà vẫn không đạt ──► hệ thống TỪ CHỐI (refusal_source = repair_exhausted)
```

Ở biến thể **"no verifier" (OFF)** bước kiểm bị bỏ qua: câu trả lời đi thẳng tới người dùng (vẫn bắt buộc có citation).

## 3. Các luật kiểm

### 3.1 Phiên bản dùng trong hệ thống đã chốt: L1 v2 (`l1_version: v2`, `l1_sentence_support: warn`)

| # | Luật | Không đạt khi | Chặn hay cảnh báo |
|---|---|---|---|
| 1 | Có nội dung | câu trả lời rỗng | chặn |
| 2 | Có trích dẫn | không có citation nào | chặn |
| 3 | Mã tài liệu tồn tại | `article_id` không có trong corpus (bịa mã) | chặn |
| 4 | Nguồn gốc | tài liệu được trích **chưa từng được search/đọc trong phiên** (trích theo trí nhớ) | chặn |
| 5 | Trích nguyên văn (nếu có `exact_quote`) | đoạn trích không có trong văn bản được trích. Trước khi so: chuẩn hoá Unicode (NFC), chữ thường, khoảng trắng, dấu nháy/gạch; bỏ dấu ngoặc kép bao ngoài; chấp nhận dấu lược `...`, `…`, `[...]` nếu **mọi đoạn ≥ 12 ký tự hoặc ≥ 3 từ khớp nguyên văn, đúng thứ tự**; con số trong đoạn trích phải khớp chính xác. Nếu đoạn trích nằm ở tài liệu khác đã tra, phản hồi chỉ ra tài liệu đó | chặn |
| 6 | Con số theo đúng chỗ | một cặp *số + đơn vị* (ngày, tháng, %, tín chỉ, học kỳ…; danh sách đơn vị theo domain) trong câu trả lời **không xuất hiện trong câu nguồn khớp nhất với câu đó** (cửa sổ 1–2 câu hoặc 1 mục liệt kê kèm câu dẫn). "3,5 tháng" = "3.5 tháng"; đơn vị bị xuống dòng vẫn nhận ra | chặn |
| 7 | Câu có căn cứ | với từng câu trả lời: tỉ lệ từ có nghĩa (bỏ stopword) tìm thấy trong **câu nguồn khớp nhất** < 0,5 | **chỉ cảnh báo** (ghi `l1_warning`, không bác câu trả lời) |

Phản hồi sửa (v2, dạng "báo cáo của verifier", không phải lời người dùng): nêu tối đa 2 lỗi, mỗi lỗi kèm **đoạn nguồn
gần nhất (≤ 170 ký tự) chép nguyên văn**, để model chép đúng hoặc sửa con số; không còn câu yêu cầu chọn `refuse`.

Ngưỡng 0,5 của luật 7 được chọn trên tập phát triển cũ (`bll2019`), **không** chỉnh theo nhãn của hai benchmark D2.

### 3.2 Phiên bản cũ: L1 v1 (hệ thống ban đầu)

Cùng luật 1–4. Khác ở: luật 5 so nguyên văn **cứng** (không chấp nhận dấu lược hay dấu nháy bao ngoài); luật 6 kiểm con
số **ở bất kỳ đâu trong cả văn bản được trích** (nên số sai vẫn lọt nếu văn bản có số đó ở chỗ khác); luật 7 tính trùng từ
trên **cả văn bản như một túi từ**, ngưỡng 0,25, và **chặn** câu trả lời. Phản hồi sửa ngắn, gửi dưới vai người dùng, kết
thúc bằng câu yêu cầu chọn `refuse` nếu không sửa được.

### 3.3 Những gì L1 KHÔNG làm

- Không hiểu nghĩa: không bắt được câu phủ định ngược nghĩa ("được" / "không được") khi từ ngữ trùng nguồn.
- Không kiểm điều kiện, ngoại lệ, thời điểm hiệu lực.
- Không biết câu trả lời có trả lời đúng câu hỏi hay không.
- Phần kiểm theo nghĩa thuộc về L2 (NLI) — đã cài đặt, **chưa dùng trong D2**.

## 4. Số liệu

Cột: 3 cấu hình OFF / có L1 / L1 + reranker. "Đúng hoàn toàn" = judge chấm correctness 2 và completeness 2, tính **trên
các câu hệ thống chịu trả lời** (câu có đáp án). "Có nhận định sai" = số câu trả lời có ≥ 1 nhận định judge gắn nhãn
*contradicted* (trái với nguồn). Mỗi ô: 2 benchmark × 45 câu có đáp án × 3 seed = 135 trial câu có đáp án (strict success
tính trên cả 150 trial).

### 4.1 Hệ thống hiện tại, controller 4B (hệ thống đã chốt)

| Benchmark | Cấu hình | Strict success | Số câu trả lời / 135 | Đúng hoàn toàn (trong số câu trả lời) | Câu trả lời có nhận định sai | Từ chối sau 2 lần sửa | Lượt sửa |
|---|---|---|---|---|---|---|---|
| HCMUT | OFF | 70,0% | 119 | 81% | 9 | — | — |
| | L1 | 64,0% | 109 | 78% | 7 | 10 | 47 |
| | L1 + reranker | 60,7% | 107 | 82% | **5** | 13 | 39 |
| Lao động | OFF | 62,0% | 129 | 67% | 16 | — | — |
| | L1 | 52,7% | 109 | 66% | **7** | 14 | 52 |
| | L1 + reranker | 56,7% | 106 | 68% | 12 | 18 | 67 |

### 4.2 Hệ thống hiện tại, controller 2B

| Benchmark | Cấu hình | Strict success | Số câu trả lời / 135 | Đúng hoàn toàn | Có nhận định sai | Từ chối sau 2 lần sửa | Lượt sửa |
|---|---|---|---|---|---|---|---|
| HCMUT | OFF | 31,3% | 79 | 51% | 22 | — | — |
| | L1 | 24,0% | 59 | 53% | 13 | 18 | 50 |
| | L1 + reranker | 28,7% | 60 | **63%** | **11** | 16 | 49 |
| Lao động | OFF | 31,3% | 107 | 35% | 38 | — | — |
| | L1 | 28,0% | 83 | 38% | 26 | 17 | 69 |
| | L1 + reranker | 28,0% | 85 | 40% | **19** | 20 | 77 |

### 4.3 Hệ thống ban đầu, controller 2B (L1 v1)

| Benchmark | Cấu hình | Strict success | Số câu trả lời / 135 | Đúng hoàn toàn | Có nhận định sai | Lượt sửa |
|---|---|---|---|---|---|---|
| HCMUT | OFF | 18,0% | 63 | 38% | 16 | — |
| | L1 | 12,0% | 31 | 48% | 9 | 56 |
| | L1 + reranker | 14,0% | 37 | **56%** | **5** | 53 |
| Lao động | OFF | 14,7% | 88 | 22% | 36 | — |
| | L1 | 14,7% | 51 | 28% | **13** | 54 |
| | L1 + reranker | 18,7% | 49 | **40%** | 16 | 74 |

(Hệ thống ban đầu chưa ghi nguồn gốc của mỗi lần từ chối, nên không có cột "từ chối sau 2 lần sửa".)

### 4.4 L1 bác vì lý do gì (theo nội dung phản hồi sửa)

| Run | Cấu hình | Trích không nguyên văn | Con số không có trong câu nguồn | Thiếu trích dẫn | Câu không có căn cứ (chặn) | Mã không tồn tại | Cảnh báo câu (không chặn) | Câu trả lời được sau khi sửa |
|---|---|---|---|---|---|---|---|---|
| hiện tại 4B, HCMUT | L1 | 19 | 28 | — | — | — | 49 | 11 |
| hiện tại 4B, HCMUT | L1 + reranker | 18 | 21 | — | — | — | 30 | 6 |
| hiện tại 2B, Lao động | L1 | 21 | 23 | 25 | — | — | 46 | 20 |
| hiện tại 2B, Lao động | L1 + reranker | 27 | 28 | 22 | — | — | 39 | 18 |
| ban đầu 2B, Lao động (v1) | L1 | 38 | — | 8 | 7 | 1 | — | 2 |
| ban đầu 2B, Lao động (v1) | L1 + reranker | 53 | — | 10 | 11 | — | — | 6 |

Bảng đầy đủ cho cả 6 run trong `results.json`.

## 5. Đọc số liệu

1. **L1 không làm tăng strict success ở cấu hình nào.** Strict success đo *độ bao phủ* (đúng trên tổng số câu). L1 bác
   một số câu đúng → thành từ chối → số câu trả lời giảm (ví dụ 4B Lao động: 129 → 109 câu trả lời).
2. **L1 làm giảm số câu trả lời có nhận định sai lọt tới người dùng**, rõ nhất với controller yếu: 2B Lao động 38 → 19,
   2B HCMUT 22 → 11, hệ thống ban đầu Lao động 36 → 13–16; với 4B Lao động 16 → 7.
3. **Với 2B, L1 làm tăng tỉ lệ đúng trong số câu được trả lời** (ví dụ 51% → 63%, 22% → 40%). Với 4B gần như không đổi
   (81/78/82%, 67/66/68%): model mạnh vốn ít bịa, nên lợi ích của L1 nhỏ.
4. **Cái giá:** 10–20 trong 150 trial mỗi cấu hình (4B, 2B hiện tại) kết thúc bằng từ chối sau 2 lần sửa, trên câu đáng
   lẽ phải trả lời. Lý do bác chủ yếu là **con số không có trong câu nguồn khớp nhất** và **trích không nguyên văn**.
5. **v2 so với v1:** ở hệ thống ban đầu, phần lớn lần bác là trích không nguyên văn (38/54 và 53/74 ở Lao động) và rất ít
   câu trả lời được sau khi sửa (2–6). Ở hệ thống hiện tại, lý do bác chia đều hơn và nhiều câu sửa thành công hơn (6–20).

**Tóm lại:** L1 là một **đánh đổi độ bao phủ lấy độ tin cậy**: trả lời ít hơn nhưng những gì nói ra ít sai hơn. Với
tra cứu luật — nơi trả lời sai nguy hiểm hơn từ chối — đây là lựa chọn có lý, đặc biệt khi dùng model nhỏ chạy trên máy.

## 6. Giới hạn của số liệu

- Nhãn đúng/sai và "nhận định sai" là của **LLM judge**; audit người đang làm.
- Các tỉ lệ ở mục 4 là **đếm thô, chưa có khoảng tin cậy**; số câu trả lời khác nhau giữa các cấu hình (so sánh độ chính
  xác trên các tập câu khác nhau). Mỗi ô chỉ 45 câu × 3 seed.
- Phân loại lý do bác dựa trên nội dung phản hồi sửa; một lượt sửa có thể nêu tới 2 lỗi, bảng 4.4 đếm theo lỗi đầu tiên
  khớp mẫu.
- Hệ thống hiện tại được thiết kế sau khi xem lỗi của hệ thống ban đầu trên cùng bộ câu hỏi (post-hoc).
