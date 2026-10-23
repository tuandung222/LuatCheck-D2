> HISTORICAL ONLY: các diagnostic/mock artifacts dưới đây không phải kết quả native hiện tại. Script dùng substitutions đã được bỏ khỏi các Python entry point theo quy định mới.

# Bằng chứng review gap D2

Kết luận và danh sách hành động nằm trong [D2_GAP_REVIEW.md](../../../report_d2/D2_GAP_REVIEW.md).

- `pytest-output.txt`, `pytest.xml`: 487 tests pass trong bản sao tạm. Đây là kết quả tests hiện có, không chứng nhận đủ yêu cầu môn học hoặc đúng số liệu report.
- `diagnostics.json`: các kiểm tra tổng hợp, lỗi import MCP và số lần primary/fallback.
- `offline-diagnostic-results.json`, `offline-trajectories.json`, `offline-diagnostic-output.txt`: một lượt chạy 10 task x 3 seeds x 2 mode, dùng fallback, không phải Qwen native.
- `cli-offline-results.json`, `cli-offline-output.txt`: chạy CLI gốc riêng với cùng tập task/config offline. Các độ đo nội dung đã được đối chiếu với diagnostic; latency thay đổi giữa các lần chạy.
- `benchmark-audit.jsonl`: audit events của lượt instrumented diagnostic cuối cùng, 60 sessions.
- `synthetic-audit.jsonl`: audit event dùng câu hỏi có email giả để kiểm tra phạm vi lưu dữ liệu; không chứa thông tin khách hàng thật từ hệ thống hiện hữu.
- `source-manifest.json`: SHA-256 nguồn, commit và môi trường kiểm tra.
- `review_checks.historical-source.txt`: bản nguồn lịch sử đã ngừng dùng (không phải Python entry point hiện tại); script dành cho bản sao repo tạm, có ghi file vào thư mục output. Không dùng dữ liệu production.

Đã kiểm tra 36 file code/config/task/corpus giữa bản sao dùng chạy diagnostic và repo gốc, không có sai khác tại lúc kiểm tra. Bộ tests có tạo PDF/cache/log trong bản sao đó; các kết quả gốc ở `evaluation/`, `redteam/` và report gốc không bị ghi đè.

Lệnh CLI đã chạy trong bản sao tạm, dùng Python của `.venv` hiện tại:

```sh
EMBEDDING_ENDPOINT=http://127.0.0.1:1 /path/to/project/.venv/bin/python evaluation/run_eval.py \
  --tasks evaluation/tasks/vlqa_sample_10.json \
  --seeds 42 123 2026 --ablation both --offline \
  --output /path/to/review-evidence/cli-offline-results.json
```

Endpoint cố ý không phục vụ inference trong diagnostic này. Mục đích là kiểm tra đường offline/fallback, không đo chất lượng hoặc tốc độ Qwen. Cổng mặc định Ollama `11434` và llama.cpp `8080` không truy cập được lúc review; chưa khảo sát mọi cổng hoặc máy khác.
