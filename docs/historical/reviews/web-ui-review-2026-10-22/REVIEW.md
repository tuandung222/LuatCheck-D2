# Review độc lập web UI — 22/10/2026

Kết luận: giao diện có bố cục và màu sắc nhất quán, inference thật hoạt động, nhưng **chưa đạt cổng M3**. Có lỗi làm trắng toàn bộ trang sau restart và các lỗi ở vòng đời proposal. Giữ stack hiện tại và sửa theo `docs/plans/WEB_UI_REPAIR_PLAN.md`.

Review này không sửa source ứng dụng. Có build lại frontend, chạy test có sẵn, chạy hai API process riêng cho review, khởi động Ollama đã cài trên máy và kiểm tra bằng trình duyệt thật. Storage DB/cache/audit/outbox của các API review nằm riêng trong `output/playwright/web-ui-review-2026-10-22/`. Corpus, benchmark, kết quả lịch sử và báo cáo D2 không bị sửa. Lần restart có chủ ý chỉ tác động API process do reviewer tạo.

## Phát hiện cần sửa

### R1 — P1: API restart làm trắng toàn bộ frontend

- `src/services/web_store.py:86–101` ghi snapshot của run bị ngắt chỉ có `terminal_status` và `final_output`.
- `frontend/src/App.tsx:515` đọc `snapshot.retrieved_article_ids.length` như trường bắt buộc. TypeScript type tuyên bố đầy đủ nhưng API không enforce response schema đó. Không có error boundary để giữ phần ứng dụng còn lại.
- Đã tạo một native run thật cùng hai run xếp hàng, nhận queue-full 429 ở request thứ tư, rồi restart riêng API.
- Backend đánh dấu cả ba run là `error/api_restart`, đúng về trạng thái. Khi refresh UI, bootstrap chọn run mới nhất và render `RunDetails`, gây `TypeError: Cannot read properties of undefined (reading 'length')`. Trang không còn nội dung hoặc cách phục hồi từ UI.
- Bằng chứng: `restart-checks.json`, `runs-after-restart.json`, `browser-errors.json`, `restart-blank-page.png` trong thư mục artifacts.
- Cần một snapshot schema thống nhất cho mọi nhánh, normalize bản ghi cũ và frontend defensive rendering/error boundary. Không chuyển run lỗi thành thành công.

### R2 — P2: Căn cứ không có đường mở ở 761–1240 CSS px

- `frontend/src/styles.css:351` ẩn `.reference-panel` khi width <=1240.
- `frontend/src/styles.css:253` ẩn `.mobile-source-tab !important`; chỉ bật lại ở width <=760 tại dòng 398.
- Các citation buttons nằm trong panel bị ẩn; nội dung answer không có nút citation tương đương. Vì vậy dải 761–1240 không có điều khiển UI để mở căn cứ.
- Đây là kết luận từ source/CSS, **chưa được tái hiện ở viewport 1024 trong trình duyệt review**. Các viewport thực đã quan sát là 460×773 và 1280×720 CSS px.
- Cần cùng một điều kiện breakpoint cho việc ẩn panel và hiện nút drawer, cùng test khả năng mở điều luật tại 1024.

### R3 — P2: Tạo proposal đồng thời gây HTTP 500

- `src/api/app.py:576–589`: khóa chỉ bao quanh tạo proposal trong registry; thao tác đọc bản ghi đã tồn tại rồi insert SQLite diễn ra ngoài transaction chung.
- `src/services/web_store.py:233` dùng INSERT với unique `proposal_id`.
- Đã gửi 12 HTTP request thật đồng thời với cùng browser session/run/recipient/content: **2 trả 200, 10 trả 500**. Trace chỉ tới `sqlite3.IntegrityError: UNIQUE constraint failed: summary_proposals.proposal_id`.
- Không ghi thêm outbox vì các request này mới tạo proposal.
- Bằng chứng: mục `concurrent_identical_proposal` trong `api-checks.json`; script `probe_api.py`.
- Lặp lại với payload mới sau restart để lưu log ASGI: 11/12 request trả 500; trace nguyên bản được giữ trong `api-restarted.log`, statuses ở `proposal-race-repeat.json`.
- Cần thao tác create-or-get nguyên tử, trả cùng proposal hợp lệ cho duplicate requests. Không chỉ bắt exception để che race.

### R4 — P2: Proposal hết hạn không thể được duyệt lại với cùng payload

- Restart đánh dấu pending proposals là `expired`, đúng với việc approval state không tồn tại qua process restart.
- Nhưng idempotency key tạo từ run/session/recipient/content là cố định; `src/api/app.py:578–586` luôn trả bản ghi expired cũ khi người dùng tạo lại đúng nội dung.
- Đã giữ một proposal chưa duyệt qua restart: confirm trả 409. Tạo lại cùng payload trả 200 nhưng cùng `proposal_id` và `status=expired`. UI không có đường tạo một vòng duyệt mới cho đúng nội dung đó.
- Bằng chứng: mục `renew_expired_proposal` trong `restart-checks.json`; recipient thử nghiệm `restart-review@example.invalid` chỉ nằm trong storage review, không gửi email.
- Cần tách logical operation identity khỏi proposal attempt/generation; cho phép xem lại và duyệt một proposal mới sau khi expiry, vẫn bảo toàn chống ghi trùng.

### R5 — P2: Lỗi xác nhận outbox được render như thành công

- `frontend/src/App.tsx:298–299` đưa exception vào `outboxMessage`; dòng 453 render mọi message bằng `success-alert` và icon Check.
- Đã bấm confirm proposal sau restart: response là lỗi hết hiệu lực, nhưng UI hiển thị chữ xanh `rgb(49,117,91)` trong `inline-alert success-alert` với dấu check. Chưa có receipt ghi outbox cho proposal đó.
- Sau confirm thành công, `proposal.status` cũng không cập nhật nên nút confirm vẫn còn.
- Bằng chứng: `outbox-expired-green-error.png`, đối chiếu với `outbox-confirmed.png`.
- Cần state riêng cho success/error/pending/expired, và chỉ thông báo đã lưu khi receipt server xác nhận.

## Đánh giá giao diện và các điểm bổ sung

- Hướng màu slate/teal, sidebar, result card và source panel phù hợp. Không cần đổi framework hoặc làm lại toàn bộ giao diện.
- Typography nhỏ hơn yêu cầu ban đầu: answer desktop 15 px, mobile 13 px; title citation và source banner 10 px; panel label 8 px; văn bản điều luật 10 px theo CSS. Đây là nhận xét usability có số đo, không phải điểm benchmark.
- Drawer căn cứ là `<aside>` được đặt fixed, không chuyển focus và không làm nền inert. Khi mở drawer trên viewport hẹp, focus vẫn nằm ở nút mở phía sau. Cần kiểm chứng đầy đủ Tab/Escape/focus return; các dialog dùng `<dialog>` đã có hành vi focus tốt hơn nhưng chưa có ma trận keyboard hoàn chỉnh.
- Giao diện trộn thuật ngữ vận hành như run/core/native/proxy vào nhiều vị trí. Có thể chuyển metadata kỹ thuật vào phần chi tiết và dùng nhãn Việt dễ hiểu ở luồng chính.
- Bộ test hiện có chỉ có `tests/test_real_system.py`; chưa có automated web regression suite. Việc 11 test cũ pass không kiểm tra được R1–R5.
- Lịch sử frontend chỉ lấy 30 bản ghi dù API có phân trang; không có điều khiển tải thêm. Đây là phần cần hoàn thiện sau các lỗi chính.

## Những gì đã thực sự chạy

| Kiểm tra | Kết quả quan sát |
| --- | --- |
| `npm --prefix frontend run build` | TypeScript và Vite build thành công |
| `.venv/bin/python -m pytest tests/ -q` | 11 passed trong 63.47 s; có native inference |
| Browser query về lương thử việc | Answered thật, cache tắt; 2 model calls, 3766 input tokens, 293 output tokens; citation Điều 26, trang Công báo 12 |
| Native rerun sau restart | Answered thật, cache tắt; 2 model calls, 3766 input tokens, 291 output tokens |
| Endpoint native không hoạt động, cấu hình ở port 9 | `error/backend_error`, 1 attempt; input/output tokens null; UI hiện lỗi thực thi |
| Session B đọc run/events/article của A | 404 ở cả ba endpoint |
| Session B confirm proposal của A | 404 |
| Mutation thiếu CSRF / Origin ngoài loopback | 403 |
| Run idempotency cùng payload / đổi payload | Replay cùng run ID / 409 |
| Semantic mode đang tắt | 422 |
| Quote của citation so với article text | Khớp nội dung nguồn sau chuẩn hóa whitespace |
| SSE `Last-Event-ID` sau event cuối | Không có event lặp, không tạo native run mới |
| Approval hash sai | 409, không ghi outbox |
| Tạo proposal trước confirmation | Outbox chưa được tạo |
| Confirm đúng rồi retry | Mỗi logical summary chỉ ghi một dòng, receipt `delivered=false` |
| Queue có một run thật đang chạy | Hai run chờ được nhận; request tiếp theo 429 với Retry-After 2 |
| API restart | DB đánh dấu interrupted/error; frontend crash như R1 |
| 12 request tạo proposal giống nhau | 10 HTTP 500 như R3 |

Không cộng các kiểm tra này thành điểm chất lượng tư vấn. Không xác nhận legal correctness hoặc chứng nhận toàn bộ tính an toàn. Hai lượt hỏi thành công dùng cùng một câu hỏi nhằm kiểm tra UI, không phải hai task benchmark độc lập.

## Artifacts và giới hạn

Toàn bộ bằng chứng nằm tại `output/playwright/web-ui-review-2026-10-22/`:

- `source-manifest.json`: hash source được review và phạm vi kiểm chứng.
- `native-answer.json`, `native-rerun-after-restart.json`, `native-unavailable-run.json`, `events.sse`, `article.json`.
- `api-checks.json`, `queue-before-restart.json`, `runs-after-restart.json`, `restart-checks.json`, `browser-errors.json`, `pytest.log`.
- Screenshots `desktop-answer.png`, `mobile-answer.png`, `article-reader.png`, `backend-error-desktop.png`, `outbox-confirmed.png`, `outbox-expired-green-error.png`, `restart-blank-page.png`.
- Script probes gọi implementation/HTTP thật. Chúng dùng storage review, không thay component, không seed câu trả lời hay sửa ledger để dựng trạng thái.

Review dùng CUA browser sau khi wrapper Playwright CLI cài sẵn không tìm thấy executable `playwright-cli`. Không tạo mock browser backend. Chưa kiểm chứng trực tiếp mọi viewport theo plan cũ, dark theme, mọi nhánh clarification/refusal, semantic inference hoặc bảo đảm đa tiến trình. Những phần đó vẫn cần bằng chứng riêng trước khi nhận M3.
