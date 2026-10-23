# Kế hoạch thực nghiệm D2 — cập nhật 22/10/2026

Yêu cầu mới nhất cho phép chạy thật trên Mac, thay thế kế hoạch hoãn cũ. Không mock, HTTP doubles, monkeypatch hoặc component thay thế, kể cả trong tests.

## Dữ liệu chốt

Corpus gồm toàn bộ 220 điều nguyên bản Bộ luật Lao động 45/2019/QH14 từ PDF Công báo Chính phủ. Đây không phải luật hợp nhất hiện hành 2026. PDF, extractor, page text và SHA ở docs/materials/benchmark-sources/.

Task/gold tại evaluation/benchmarks/bll2019_v1/tasks.json: 10 task local, gồm 7 single-provision, 2 synthesis, 1 ngoài phạm vi; 9 answerable. Các gold excerpts được đối chiếu nguồn bằng AI; chưa được chuyên gia chứng nhận. Không gọi là split VLQA hay held-out benchmark. Không sửa gold theo model output. Draft cũ không chắc chắn đã loại khỏi đường chạy.

## Cấu hình và workload

Apple M4, 10 CPU cores, 16 GiB unified memory; Ollama 0.34.4, Qwen2.5:3B Q4_K_M đã cache, Metal. Context 8192; output cap 768/generation; temperature 0.1; timeout tối đa 60 s/call và phần còn lại của deadline. Budget 5 tools, 2 repairs, 8 steps, 180 s/task. Một model, chạy tuần tự.

OFF và L1 ON cùng model/prompt/corpus/retriever; OFF bỏ verification. BM25 + TF-IDF/RRF trên 220 điều. Memory read/write tắt bằng config thật. Backend prefix cache không phải answer cache.

- Pilot v1: 8 lượt thật; pilot interface v2: 4 lượt thật. Giữ mọi output, không gộp main.
- Main: 10 tasks × 2 modes × seeds 42, 123, 2026 = 60 lượt; luân phiên thứ tự mode.
- bll2019-main-v1 dừng sau 10 lượt, incomplete. Khi tiếp tục không còn collector/server; nguyên nhân gián đoạn chưa xác định. Giữ artifacts.
- bll2019-main-v2 chạy lại toàn bộ cùng frozen source/config. Log: docs/reviews/native-benchmark-2026-10-22/logs/main-v2.log.
- Chưa mở rộng 120 lượt: ưu tiên hoàn thành 60 và chấm có căn cứ.

Trần deadline lý thuyết khoảng 3 giờ/60 task cộng setup/review; đây không phải latency đã đo. Không sửa runtime/data trong lúc main chạy.

## Lệnh tái lập

Không chạy đồng thời collection khác hoặc native tests. Output phải là thư mục mới.

~~~sh
.venv/bin/python -m evaluation.run_eval --execute --phase main --config config/d2_native.yaml --tasks evaluation/benchmarks/bll2019_v1/tasks.json --task-review evaluation/benchmarks/bll2019_v1/review.json --seeds 42 123 2026 --ablation both --output evaluation/runs/NEW-UNUSED-DIRECTORY
~~~

Sau khi manifest là collected_pending_human_scoring:

~~~sh
.venv/bin/python -m evaluation.analyze_native --run-dir evaluation/runs/bll2019-main-v2 --tasks evaluation/benchmarks/bll2019_v1/tasks.json --output evaluation/runs/bll2019-main-v2/operational-summary.json
.venv/bin/python -m evaluation.export_blind_review --run-dir evaluation/runs/bll2019-main-v2 --output evaluation/runs/bll2019-main-v2/blind-review
~~~

Analyzer/exporter từ chối batch thiếu hoặc sai hash, không ghi đè output. Không rerun riêng câu sai để đổi điểm.

## Chấm bằng gì

| Đối tượng | Cách chấm | Giới hạn |
| --- | --- | --- |
| Trajectory Recall/Hit/MRR | Recall/Hit@5: 5 unique ID đầu tiên; MRR: toàn bộ ordered unique trace | Không phải held-out IR benchmark |
| Citation-ID precision/recall | Tập ID gold so với citation | Không chứng minh entailment; có thể bỏ sót alternative đúng |
| Exact quote | Containment trong source | Không chứng minh lập luận đúng |
| Latency, tokens, calls, errors | Ledger/native usage thật | Thiếu giữ null |
| Model service-hours | Tổng backend total_duration | Không gọi là hardware GPU-active hours |
| Reference EM/F1, lexical unsupported | Code lexical | Proxy/diagnostic, không phải correctness |
| Correctness, completeness, faithfulness, hành vi phù hợp | Judge độc lập mạnh hơn, nguồn/rubric, ẩn mode | LLM estimate, cần kiểm tra bằng người |
| Độ tin cậy judge | Nhãn người thật, agreement/kappa | Chưa có nhãn, không điền điểm |

Protocol: evaluation/benchmarks/bll2019_v1/SEMANTIC_JUDGING.md. Không dùng Qwen3B tự chấm rồi gọi là judge độc lập. Credential gateway đã được cấu hình cục bộ (không lưu trong tài liệu); judge API đã chạy theo lựa chọn người dùng. Không tải judge local lớn hơn.

Exporter tạo judge_packets.json và private_mapping.json; chỉ đưa packet và protocol cho reviewer. Exporter không tạo nhãn. Mẫu human audit tối thiểu 12/60 theo protocol; không bịa người chấm. Nếu chưa có judge/human evidence trước hạn thì giữ ô semantic đỏ.

## Hoàn thiện

1. Complete main, phân tích mọi lỗi và actual failure cases.
2. Điền operational metrics thật; semantic còn thiếu giữ đỏ.
3. Chạy judge khi có cấu hình thật và human audit khi có người chấm.
4. Chạy real tests sau main, build/render/verify PDF; tối đa 10 trang nội dung.
5. Nhóm xác nhận pitch, HR walkthrough, contributions, AI-use, commit/access; slide PDF, video dự phòng và rehearsal.

Owner trong report là đề xuất, không tự gán đóng góp đã hoàn tất.

## Cập nhật sau collection

Main v2 đã hoàn tất 60 trial/264 calls, gồm 12 model-output errors; mọi usage được lưu. Independent artifact verification và 11 real-system tests đạt. Bảng operational đã tính; chưa có semantic judge/human labels, không gọi answer coverage là accuracy.

## Cập nhật judge theo lựa chọn của người dùng

Đã dùng gateway Qualgo với model deepseek/deepseek-v4-flash (alias upstream được tài liệu DeepSeek ánh xạ sang V4.1-Flash-1017, không pin revision). Có 57 phán quyết accepted / 60; 3 OFF unknown. Giữ nguyên main+recovery và mọi lỗi. Tiếp theo là human audit 12 mẫu thật; không tạo nhãn người bằng model. Xem analysis-final trong evaluation/runs/deepseek-judge-main-v1/ để lấy summary và human-audit/.
