# Hướng dẫn audit người cho LLM judge (D2)

> Soạn lúc 2026-10-24 16:45 +07. Dành cho các thành viên nhóm, buổi audit tối thứ Bảy 24/10/2026.

## Mục đích

Số liệu D2 của hệ thống đã chốt (r2, Bonsai 4B) được chấm bằng một LLM judge (DeepSeek Flash). Giảng viên yêu cầu kiểm tra xem judge đáng tin đến đâu,
bằng cách so nhãn của judge với nhãn do **người thật** gán trên một mẫu nhỏ. Kết quả là tỉ lệ đồng thuận và Cohen's
kappa, đưa vào report.

**Nguyên tắc bắt buộc:** mỗi nhãn phải do chính bạn đọc và quyết định. Không dùng AI để gán nhãn thay, không chép kết
quả của judge, không sửa nhãn của người khác. Không gán được thì để trống ô đó. Nhãn bịa còn tệ hơn không có nhãn.

## Tài liệu

Mỗi benchmark có 30 câu, chọn ngẫu nhiên theo tầng. Bạn không biết câu trả lời đến từ biến thể nào và judge đã chấm gì;
việc ẩn này là cố ý.

| Benchmark | Đọc câu hỏi và câu trả lời | Điền nhãn |
|---|---|---|
| HCMUT | `evaluation/runs/d2-gpu-r2-4b-hcmut-v1/analysis/human-audit/packets.md` | `.../human-audit/labels.csv` (cùng thư mục) |
| Lao động | `evaluation/runs/d2-gpu-r2-4b-labour-v1/analysis/human-audit/packets.md` | `.../human-audit/labels.csv` (cùng thư mục) |

Mỗi câu trong `packets.md` gồm: câu hỏi, hành vi mong đợi (trả lời hay từ chối), đáp án tham chiếu kèm bằng chứng,
câu trả lời của hệ thống, các trích dẫn, và nguyên văn các văn bản nguồn (bấm vào "Source" để mở).

Quy tắc chấm đầy đủ nằm trong `evaluation/runs/d2-gpu-r2-4b-hcmut-v1/judge/SEMANTIC_JUDGING.md`. Các cột cần điền trong
`labels.csv`:

| Cột | Giá trị | Ý nghĩa |
|---|---|---|
| `reviewer` | họ tên của bạn | bắt buộc |
| `judgeable` | `true` / `false` | `false` nếu đáp án tham chiếu sai hoặc câu hỏi mơ hồ đến mức không chấm được (ghi lý do vào `notes`) |
| `behaviour_appropriate` | `true` / `false` | hành vi có đúng không: cần trả lời thì trả lời; câu ngoài phạm vi thì từ chối |
| `correctness` | `0` / `1` / `2` | 2 = mọi khẳng định đều đúng theo nguồn; 1 = đúng một phần; 0 = sai hoặc lạc đề |
| `completeness` | `0` / `1` / `2` | 2 = đủ ý so với đáp án tham chiếu; 1 = thiếu ý quan trọng; 0 = không trả lời được câu hỏi |
| `total_claims` | số nguyên | số khẳng định sự thật trong câu trả lời. **Không tính** câu "không có thông tin trong văn bản" hay lời từ chối |
| `unsupported_claims` | số nguyên | số khẳng định mà văn bản nguồn **không** chứng minh được hoặc mâu thuẫn |
| `notes` | tự do | lý do, nhất là khi ghi `judgeable=false` hoặc khi phân vân |

Gợi ý:
- Chấm theo **ý nghĩa**, không chấm theo câu chữ.
- Kiểm tra điều kiện, ngoại lệ, con số và mốc thời gian.
- Nếu câu trả lời trích một văn bản khác với đáp án tham chiếu nhưng văn bản đó cũng đúng, vẫn tính là đúng.

## Chia việc (gợi ý)

Mỗi người 20 câu, khoảng 1,5–2 giờ. Nếu đủ người, nên có 10 câu do hai người chấm độc lập để đo mức đồng thuận giữa
người với người. Ghi rõ ai chấm câu nào trong cột `reviewer`. Nếu hai người chấm cùng một câu, dùng hai file CSV riêng.

## Sau khi điền xong

```bash
make audit-score RUN=evaluation/runs/d2-gpu-r2-4b-hcmut-v1 LABELS=evaluation/runs/d2-gpu-r2-4b-hcmut-v1/analysis/human-audit/labels.csv
```

```bash
make audit-score RUN=evaluation/runs/d2-gpu-r2-4b-labour-v1 LABELS=evaluation/runs/d2-gpu-r2-4b-labour-v1/analysis/human-audit/labels.csv
```

Script từ chối tính số nếu có dưới 10 câu đã gán nhãn hoặc nhãn không hợp lệ. Nếu đủ, nó tính tỉ lệ đồng thuận và
Cohen's kappa giữa người và judge, theo strict success và theo từng tiêu chí. Gửi lại file CSV đã điền để đưa kết quả
vào report.
