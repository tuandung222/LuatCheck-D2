# Web UI repair follow-up — 22/10/2026

Scope: implement the five findings in `../web-ui-review-2026-10-22/REVIEW.md`, improve source readability/accessibility, and preserve the original review database and evidence. All API/browser verification that used saved runs operated on a separate temporary copy of the review database.

## Changes

- API snapshots now pass through a Pydantic contract on success, runtime failure, restart, and reads of legacy rows. Missing measurements remain null; a run whose stored terminal status conflicts with its snapshot is surfaced as an error.
- SQLite proposal create-or-get and its created event are atomic. Simultaneous identical proposals converge on one row; after expiry, the same payload can create a new review attempt while retaining the logical outbox idempotency key.
- Frontend recovery retains navigation when a run card fails. Error/clarification recovery restores the question, pasted text, and mode to the form and waits for an intentional submit.
- “Căn cứ” is available when the source side panel is hidden. Its modal drawer supports a dialog name, background inertness, keyboard focus containment, Escape, and focus return.
- Outbox error and expiry states are alerts, not success. Only a persisted `queued_locally` or `duplicate_suppressed` receipt is treated as completed; completion removes the confirm action. Renewal preserves the payload for review.
- Raised small UI text; article text is 16 px and CSS font declarations below 12 px were raised to at least 12 px.

## Verification performed

| Check | Result |
| --- | --- |
| `npm --prefix frontend run typecheck` | Pass |
| `npm --prefix frontend run build` | Pass |
| `.venv/bin/python -m pytest tests/web/test_web_repair_regressions.py -q` | 4 passed; real SQLite persistence/contract checks, no substituted model or HTTP implementation |
| `git diff --check` | Pass |
| HTTP API against a temporary copy of review DB | 12 concurrent identical proposal requests returned the same proposal ID and one stored row; expired confirmation returned 409; recreating the same payload returned a new attempt ID with the same payload hash |
| Browser at 1024 CSS px and 390 CSS px, displaying the saved native answer from the review DB copy | Source drawer opened to Điều 26, article text computed to 16 px, dialog focus/Escape worked; no horizontal overflow at 390 px |
| Restart error and outbox-expiry UI on the review DB copy | Navigation remained present; run error/reason and null measurement states were visible; outbox expiry displayed as an error and allowed payload-preserving renewal |

The expired-outbox UI check used an `.invalid` recipient in the copied review DB. No external message was sent, and this follow-up did not confirm or add an outbox receipt.

## Not verified / acceptance status

Ollama at `localhost:11434` refused connection during this repair turn. No fresh native inference was run, and the full suite was not rerun because it includes native inference. The two successful native answers and the original 11-test result belong to the independent review and are not claimed as new runs here. Outbox success receipt was not re-exercised end-to-end in this turn.

### Cập nhật follow-up cùng ngày

Sau khi kiểm tra lại, Ollama service đã sẵn sàng và có model `qwen2.5:3b`. Một run native mới chạy qua API thật với storage tạm:

- Run ID: `9869fdb3-d385-4391-b3c8-9902b2748d29`; trạng thái `answered`.
- Usage API: 2 model calls, 3,873 input tokens, 272 output tokens, 18,746.376 ms model wall time.
- Trả lời: thời gian thử việc tối thiểu bằng 85% lương công việc đó.
- Citation: `Dieu_26`, Bộ luật Lao động 2019, trang 12, SHA-256 `3c865f3d92ba23604e316360b902297ddbc0d1c394d3c08a466029a9d43b5b6c`; citation quote khớp corpus.

Lần thử đầu browser security policy từ chối mở/đọc tab `http://127.0.0.1:8026/`. Sau yêu cầu trực tiếp của người dùng “thử lại”, bind trực tiếp tab hiện có đã thành công; không dùng đường truy cập thay thế. Giao diện hiển thị run `babb53b8-9d6e-4203-b81f-38a905bd1cfa` với `terminal_status=error`, `error_kind=model_output_error`, reason `Model action requires a tool_args object.`, 8 model calls, 26,134 input tokens, 960 output tokens và 75,229.808 ms model wall time. Đây là lỗi inference native thật. Screenshot UI được xem trong phiên browser nhưng không lưu thành file trong repo.

Tại màn lỗi, navigation vẫn hiện trong accessibility tree; thông báo nêu lỗi, không có câu trả lời thay thế và có nút “Chỉnh câu hỏi rồi chạy lại”. Đây xác nhận browser render cho nhánh lỗi thực thi; không xác nhận render của run thành công API ở trên vì run đó thuộc session khác. Các viewport/theme matrix, clarification/refusal, session/CSRF/queue/SSE rechecks và full native suite vẫn còn mở. M3 chưa được nghiệm thu; `make demo` tiếp tục là Streamlit. Không chạy benchmark collection hoặc sửa report D2 trong follow-up này.

API đang phục vụ tại `127.0.0.1:8026` với DB, memory, audit và outbox nằm trong thư mục tạm riêng, để có thể xem app thủ công. Không dùng storage mặc định của người dùng.

## Source hashes

SHA-256 at completion of this repair:

```text
192b0109076a346108a457c5809209b093d79831d9798c432e4fba7ef7540ff5  src/api/app.py
786ab543d44ad9b7a36c0a7ce00fc3cc3413da1cfb23365f793f004ac95ced39  src/services/web_contract.py
dc592d694280734d90d81ec6e1cbf17ca577167b34e1e511e369d05d1b640ba5  src/services/web_store.py
1152839f5c13129a724f4845768a8ea2a2bf553a4fe3971fd0397b1ec6b2a97e  frontend/src/App.tsx
52fee051186d74e57d82a09b72b8ea74b33fcc1eeb9f63b729154950052ac8be  frontend/src/ErrorBoundary.tsx
bfdecf84d93d3d07c374242f652ff2641252cfa0ea0f2472748a9a3430fe73ca  frontend/src/styles.css
e96550dcd775a5f3e9ccf0eb4a0cc4f4b79fdcf110fe17ea1f07b34534618f97  tests/web/test_web_repair_regressions.py
```
