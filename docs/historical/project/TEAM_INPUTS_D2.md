# Phần nhóm cần điền cho D2 (trước 23:59 Chủ nhật 25/10/2026)

> Cập nhật 2026-10-25 03:05 +07. Các mục phân công đóng góp, người thuyết trình, tự kiểm chứng và kế hoạch tuần đã được cập nhật vào Report và Slide. Chỉ còn mục 1 (Audit người cho LLM judge).

## 1. Audit người cho LLM judge (còn lại)

Làm theo `docs/guides/HUMAN_AUDIT_GUIDE.md`; điền hai file:
- `evaluation/runs/d2-gpu-r2-4b-hcmut-v1/analysis/human-audit/labels.csv` (30 câu)
- `evaluation/runs/d2-gpu-r2-4b-labour-v1/analysis/human-audit/labels.csv` (30 câu)

| Thành viên | Benchmark | Số câu đã gán | Xong lúc |
|---|---|---|---|
| | | | |

## 2. Bằng chứng đóng góp (report mục 8, bảng đóng góp — ĐÃ ĐIỀN)

| Thành viên | Đã làm gì (bằng chứng) |
|---|---|
| Lê Trí Quyền (Leader) | Retrieval & serving: luồng nạp văn bản (`src/ingestion/`), chỉ mục BM25 + TF-IDF & vector index với RRF (`src/indexing/`), tích hợp cross-encoder reranker (`src/retrieval/`), `llama.cpp`/Prism local serving và triển khai đa nền tảng (`555919a`, `8fed7c5`, `15fd823`, `ad0881b`, `bdb5d69`, `415efda`). |
| Võ Phạm Tuấn Dũng (Technical Lead) | Phụ trách kỹ thuật chính, kiểm chứng ý tưởng và review toàn bộ commit; vòng lặp ReAct có giới hạn ngân sách & config-driven pipeline (`src/agent/`, `src/pipeline/`), bộ kiểm tra trích dẫn L1 & sửa chữa (`src/verifier/`), xây dựng và rà soát thủ công 100 câu benchmark (`evaluation/benchmarks/`), evaluation harness, chạy thực nghiệm GPU/Mac, phân tích thống kê và biên soạn báo cáo/slide D2 (`386ca40`, `8eb63f4`, `cdb6b24`, `40323a6`, `7b94407`, `afaee8f`, `d741440`). |
| Nguyễn Hoàng Phong | System & security: tầng công cụ & kiểm soát phân quyền (`src/tools/`), bộ lọc guardrails regex & PII (`src/security/`), giao diện Web/Streamlit & hộp thư duyệt cục bộ (`frontend/`, `src/api/`, `src/ui/`), lưu trữ SQLite & nhật ký kiểm toán (`src/memory/`), kiểm thử lỗi và an ninh (`6dc1dbc`, `78bb069`, `2c1f3d0`, `d117349`, `7ce7e45`, `1272dc7`, `e0b4a05`, `edc9bfa`). |

## 3. Nhóm đã tự kiểm chứng những gì (report mục 8 — ĐÃ ĐIỀN)

| Thành viên | Đã tự kiểm chứng |
|---|---|
| Lê Trí Quyền | Kiểm chứng trích xuất corpus, chỉ mục BM25/TF-IDF và dịch vụ `llama.cpp`/reranker local |
| Võ Phạm Tuấn Dũng | Review toàn bộ 100 câu hỏi benchmark đối chiếu PDF nguồn (23/10), kiểm chứng kiến trúc, review toàn bộ mã nguồn/commit của nhóm và kiểm tra các lượt chạy live demo trên Mac |
| Nguyễn Hoàng Phong | Kiểm chứng ranh giới phân quyền công cụ, chặn guardrail và các trạng thái giao diện Web UI |

## 4. Người trình bày (slide, 10 phút — ĐÃ ĐIỀN)

| Slide | Nội dung | Người trình bày |
|---|---|---|
| 1–2 | Đề tài, thay đổi so với proposal | Lê Trí Quyền |
| 3–4 | Kiến trúc, trace | Võ Phạm Tuấn Dũng |
| 5 | Live demo (chạy bằng controller 4B) | Nguyễn Hoàng Phong thuyết minh; Võ Phạm Tuấn Dũng điều khiển bàn phím |
| 6–8 | Đánh giá, kết quả, phân tích verifier & reranker | Võ Phạm Tuấn Dũng |
| 9 | Chi phí, độ trễ Mac và reranker parity | Lê Trí Quyền |
| 10 | Threat model | Nguyễn Hoàng Phong |
| 11–12 | Kế hoạch, rủi ro, tổng kết | Lê Trí Quyền |
| Hỏi đáp | Retrieval/serving: Quyền · Agent/verifier/evaluation: Dũng · Tools/security/UI: Phong | Cả nhóm |

## 5. Kế hoạch tới báo cáo cuối kỳ (report mục 7 — ĐÃ ĐIỀN)

| Tuần | Việc | Người phụ trách |
|---|---|---|
| 45 (2–8/11) | HR walkthrough; thiết kế và khóa bộ câu hỏi mới khó hơn (tình huống, nhiều bước) | Quyền, Phong |
| 46 (9–15/11) | Chạy hệ thống hiện tại và ablation (dense embedding) trên bộ câu hỏi mới; phân tích lỗi | Dũng, Quyền |
| 47 (16–22/11) | Thử tấn công prompt injection theo điểm vào; kiểm tra phân quyền và lỗi | Phong, Dũng |
| 48 (23–29/11) | Tái lập từ các lượt chạy đã ghi, hoàn thiện demo và báo cáo cuối kỳ | Cả nhóm |
| 49 (30/11–2/12) | Phát hành bản gắn thẻ (tagged release) và báo cáo vòng 1 ngày 2/12 | Cả nhóm |

## 6. Trước khi nộp

- [x] Video demo dự phòng bằng controller 4B (`deliverables/d2/demo/gifs/demo_backup_4b.mp4`)
- [ ] Trưởng nhóm (Lê Trí Quyền) gửi email `[CO5151][G8] D2 Interim report` tới lexuanbach@hcmut.edu.vn, CC các thành viên, đính kèm `deliverables/d2/report/main_d2.pdf` và `deliverables/d2/slides/main.pdf`
