> **Historical (superseded 24 October 2026).** This note describes the Qwen2.5-3B / `bll2019_v1` pilot. Current D2 status: README.md and docs/RUNBOOK_D2.md; requirements gap: docs/reviews/d2_requirements_gap_2026-10-23.md.

# Trạng thái D2 — 22/10/2026

Trạng thái này thay thế ghi chú chuẩn bị trước khi chạy native. PDF vẫn là draft; đã có ước lượng LLM judge; chưa có nhãn người hoặc chứng nhận chuyên gia.

## Đã thực hiện

- Bỏ response fallback và heuristic NLI thay thế; backend lỗi là execution error.
- Thay dữ liệu cũ bằng corpus 220 điều nguyên bản Công báo, có PDF, pages và SHA; chốt 10 task local có gold excerpts. Reviewer nguồn là AI, chưa phải chuyên gia.
- Bỏ tests dùng substitutions. Replacement suite kiểm tra implementation thật, MCP thật và model thật. Kiểm tra sau collection: 11 passed/43.31 s. Không chạy native test đồng thời với main.
- Pilot 8 + 4 lượt native được giữ riêng, bao gồm lỗi chất lượng.
- Main v1 có 10 lượt rồi gián đoạn; manifest incomplete. Main v2 đã hoàn tất toàn bộ 60 lượt cùng source/config, không gộp dữ liệu cũ.
- Report theo tám phần của Thầy; placeholder đỏ giữ nguyên phần thiếu.
- Đã chạy DeepSeek Flash gateway judge; nhãn người vẫn trống.

## Còn phải làm

- Hoàn tất human audit 12 output (nhóm hẹn làm tối thứ Bảy 24/10/2026, ghi nhận 23/10); toàn bộ 60 phán quyết LLM đã hợp lệ.
- Chốt lịch HR walkthrough mới, cung cấp bằng chứng đóng góp và xác nhận AI-use; pitch/HR hiện trạng đã được nhóm xác nhận.
- Chốt commit/access, slide PDF, backup video và rehearsal.

Nguồn tiến độ: evaluation/runs/bll2019-main-v2/manifest.json và runs.jsonl. Không coi manifest collecting hay log khởi động là batch hoàn tất.

## Xác nhận nhóm ngày 22/10/2026

Người dùng trả lời “chưa” cho câu hỏi tổng hợp: chưa có pitch feedback, chưa làm HR walkthrough, chưa cung cấp xác nhận/bằng chứng đóng góp từng thành viên. Không suy ra các thành viên chưa từng làm việc. Report đã ghi đúng tình trạng; lịch walkthrough mới và bằng chứng đóng góp vẫn thiếu.

## Kết quả thu thập hoàn tất

- Main v2: 60 trial, 264 native calls; 12 model-output errors được giữ lại.
- OFF: 18 answered, 3 refused, 4 clarified, 5 errors. ON: 14 answered, 5 refused, 4 clarified, 7 errors. Đây là nhãn action/status, không phải correctness.
- Đủ token usage; kiểm tra độc lập coverage, snapshot/hash, ID arithmetic và raw native usage đạt.
- Tests sau collection: 11 passed trong 43.31 s, có native inference thật.
- Operational summary và bộ chấm ẩn nhãn có trong evaluation/runs/bll2019-main-v2/.
- Đã chạy independent LLM judge; human validation vẫn chưa có. Các ô đã kiểm tra bằng người vẫn đỏ.

PDF hiện có 9 trang tổng cộng. Bản này vẫn là draft vì thiếu human audit và các xác nhận cuối trước nộp.

## DeepSeek judge — lịch sử trước retry bổ sung

- Main: 60 output, 72 API attempts; 49 phán quyết hợp lệ ban đầu.
- Recovery: đúng 11 output không hợp lệ, 1 streamed attempt/output; sau correction parser theo rubric có 8 phán quyết được chấp nhận. Không sửa điểm/nhãn/quote do model trả về.
- Tổng: 57/60 accepted, 3 OFF unknown; 83 attempts main+recovery, chưa tính 2 pilot.
- Strict success estimate: ON 11/30; OFF 8 thành công đã xác định, 3 unknown, nên bounds toàn bộ mẫu 26.7–36.7%. Không kết luận ON tốt hơn.
- Có 12 mẫu human audit, CSV trống. Agreement/kappa chưa tính.
- API token/cost fields có bất nhất upstream; giữ raw và báo riêng các subtotal, không chứng nhận hóa đơn.
- Summary tại thời điểm này: evaluation/runs/deepseek-judge-main-v1/analysis-final/summary.json. analysis/ là bản trước khi bổ sung phân biệt hai nguồn cost metadata, không phải bộ nhãn mới.
- Test real-system mới nhất: 11 passed / 26.09 s. PDF có bảng LLM estimates, human validation vẫn đỏ.

## Retry bổ sung đã hoàn tất

- Nguyên nhân ba mẫu còn thiếu: hai response hết ngân sách đầu ra, một response lặp claim quote.
- Chỉ retry ba mẫu còn invalid, cùng model/prompt/task/rubric, nâng cap lên 32.768 token, concurrency 1, tối đa ba lần/mẫu và backoff. Cả ba hợp lệ ngay lần bổ sung đầu tiên.
- Tổng 60/60 accepted, 0 unknown; 86 API attempts main+hai recovery, hai pilot giữ riêng. 57 phán quyết hợp lệ trước đó giữ nguyên.
- Strict success LLM estimate: OFF 10/30 (33,3%), ON 11/30 (36,7%). Claim faithfulness: OFF 40/48 (83,3%), ON 28/35 (80,0%). Không có kết luận ON tốt hơn có ý nghĩa thống kê.
- Summary chuẩn: evaluation/runs/deepseek-judge-main-v1/analysis-retry-v2/summary.json. Các summary cũ giữ làm lịch sử.
- Phát lại raw SSE, hash, phép tính điểm, bảo toàn 57 phán quyết cũ và 12 mẫu human audit đều đạt. Nhãn người vẫn trống.
