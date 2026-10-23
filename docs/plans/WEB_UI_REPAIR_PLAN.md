# Kế hoạch sửa sau review web UI

Ngày: 22/10/2026. Đầu vào: `docs/reviews/web-ui-review-2026-10-22/REVIEW.md` và artifacts tại `output/playwright/web-ui-review-2026-10-22/`.

Mục tiêu: hoàn thành M3 bằng cách sửa bản React/FastAPI hiện tại. Giữ design direction, core inference và quy tắc integrity. Đây là tài liệu bàn giao; reviewer chưa triển khai các bản sửa.

## 1. Phân công và thứ tự

| Agent | Sở hữu file/phần việc | Đầu ra |
| --- | --- | --- |
| A — Contract/API/persistence | `src/api/`, `src/services/`, contract API | Snapshot schema thống nhất, normalization dữ liệu cũ, proposal atomicity và renewal |
| B — Frontend/UX | `frontend/` | Không crash theo error/restart; outbox state đúng; drawer, typography và keyboard được sửa |
| C — QA hệ thống thật | Các test mới trong `tests/web/`, browser checks, artifacts review vòng sau | Regression tests gọi process/API thật; native runs và ảnh UI ở viewport yêu cầu |
| D — Điều phối/tích hợp | README, Makefile, tài liệu nghiệm thu | Chốt interface trước, kiểm tra các cổng, quyết định chuyển demo entry point dựa trên bằng chứng |

D chốt contract với A/B trước. Sau đó A và B làm song song ở phạm vi file riêng; C chuẩn bị reproducer từ artifacts rồi kiểm tra tuần tự khi cần native inference. Không chạy nhiều job model hoặc benchmark collection đồng thời.

## 2. Cổng F1: phục hồi lỗi và restart

Ưu tiên R1 trước mọi polish.

Agent A:

1. Định nghĩa snapshot response model chung với đầy đủ defaults trung thực: `retrieved_article_ids=[]`, budgets/usage/grounding có thể null; mode lấy từ run config đã lưu. Không tạo token count hoặc thời gian đo chưa có.
2. Tất cả đường native finish, runtime exception và API restart dùng cùng serializer/model. API response thực sự được validate, không chỉ thêm TypeScript interface.
3. Chuẩn hóa các snapshot cũ khi đọc hoặc migrate có version; giữ error kind/reason gốc. Không yêu cầu xóa database hay session người dùng để tránh crash.

Agent B:

1. Parse/validate payload API ở boundary và render trường optional an toàn.
2. Thêm error boundary phù hợp để lỗi một card không làm mất navigation/hồ sơ; hiển thị thông báo có cách quay lại/tải lại.
3. Có thao tác phục hồi từ error và clarification; giữ câu hỏi/văn bản đã nhập để người dùng có thể chỉnh, gửi một run mới có chủ ý. Không tự retry inference.

Nghiệm thu F1:

- Start API thật, submit native task, thêm hai queued tasks, restart riêng API process trước khi hoàn tất, rồi refresh UI.
- Cả ba run vẫn là interrupted/error; UI còn sidebar, đọc được reason và không có unhandled exception.
- Mở lại DB chứa snapshot thiếu trường đã phát sinh thật trong vòng review; UI không crash. Dùng bản sao storage review để kiểm tra migration, không sửa bằng chứng gốc.
- Một lần reload hoặc nối lại SSE không tạo lại inference/job đã bị ngắt.

## 3. Cổng F2: vòng đời proposal và receipt

Agent A:

1. Thực hiện create-or-get proposal trong transaction/critical section có ownership rõ ràng; giải quyết unique conflicts bằng việc đọc đúng bản ghi đã tạo và trả response nhất quán.
2. Tách identity chống ghi trùng của summary khỏi identity của từng lần duyệt. Sau expiry, người dùng có thể tạo một attempt mới cho cùng run/recipient/content, đọc lại payload và duyệt lại.
3. Giữ payload hash binding và approval token server-only. Không phục hồi phê duyệt cũ thành approved sau restart.
4. Outbox write và proposal receipt phải có đường recovery khi process chết giữa hai bước. Trạng thái không chắc phải được biểu diễn là chưa xác nhận; dùng durable dedup để tránh ghi lặp.
5. Trả schema trạng thái rõ ràng, phân biệt pending/completed/expired và lỗi ghi; không dùng HTTP 200 như receipt thành công khi chưa ghi.

Agent B:

1. Tách `outboxResult`/`outboxError` và state của proposal; màu/icon/thông báo dựa trên status.
2. Sau receipt queued/duplicate, cập nhật state completed và thay confirm bằng nút đóng/xem receipt.
3. Proposal hết hạn có nút “Tạo bản duyệt mới”, buộc xem lại payload. Nếu nội dung đổi, luôn tạo proposal mới.
4. Error được thể hiện bằng alert tương ứng và giữ payload người dùng đang xem.

Nghiệm thu F2:

- 12 request thật đồng thời tạo cùng proposal đều nhận response hợp lệ, cùng logical proposal; không có 500 hay duplicate DB record.
- Trước confirm, outbox chưa có thêm dòng. Hash sai/session khác bị chặn. Confirm và retry chỉ tạo một receipt ghi bền vững.
- Pending proposal qua restart hết hiệu lực; người dùng tạo lại cùng nội dung được attempt mới, xem lại và duyệt được; không ghi lặp logical summary đã được lưu.
- HTTP 409/503 hiển thị lỗi, không dấu check xanh hoặc chữ “đã lưu”. Thành công chỉ có khi receipt đúng.

## 4. Cổng F3: căn cứ có thể đọc và sử dụng

Agent B:

1. Dùng cùng breakpoint cho ẩn panel và hiện nút “Căn cứ”. Nút luôn xuất hiện ở mọi kích thước mà panel không hiển thị.
2. Drawer có accessible name, chuyển/trap focus phù hợp, Escape đóng, trả focus về trigger; nền không nhận tương tác khi drawer modal mở. Kiểm tra cả menu sidebar mobile.
3. Typography qua tokens: body/answer/văn bản nguồn khoảng 16–17 px; control/body phụ khoảng 14 px; metadata khoảng 12–13 px. Tránh nhãn quan trọng 8–10 px. Kiểm tra bằng computed style và đọc trực tiếp, không chỉ ảnh thu nhỏ.
4. Cải thiện tương phản chữ phụ, kích thước vùng bấm và tách metadata kỹ thuật ra khỏi nội dung tư vấn.
5. Thêm tải thêm/phân trang lịch sử; giữ active run ngay cả khi ngoài trang đầu.

Nghiệm thu F3:

- Native answer thật có citation. Tại 390, 460, 768, 1024, 1240, 1280 và 1440 CSS px, có đường mở Điều 26, đọc nội dung, provenance và quay lại.
- Ở 1024, drawer phải được mở bằng nút hiển thị trên UI; không gọi API hoặc sửa DOM để giả lập thao tác người dùng.
- Không tràn ngang, drawer không che mất nút đóng, keyboard không đi vào nền bị che. Ghi lại viewport dimensions thực cùng ảnh chụp.
- Light theme đạt trước; dark theme đã có cũng phải qua các màn answer, error, source và outbox.

## 5. Cổng F4: bộ kiểm thử và quyết định nghiệm thu

Agent C/D:

1. Giữ 11 test core hiện có, bổ sung automated regression cho F1/F2/F3. Kiểm tra session ownership, CSRF, queue saturation, idempotency, restart/reconnect và outbox trên server thật.
2. Native success dùng model đã cấu hình và corpus có nguồn. Failure branch dùng cấu hình native endpoint thực sự không hoạt động trong một process/storage riêng; không tắt server model đang dùng, không chèn HTTP response giả.
3. Không ép model sinh một terminal state để test UI. Nếu nhánh chưa gặp bằng inference thật hoặc chưa có artifact native tương ứng, ghi chưa kiểm chứng; không dựng câu trả lời/refusal.
4. Lưu commands, source hashes, screenshots, HTTP statuses, run IDs, actual model usage nếu có, và các lỗi còn lại. Phân biệt regression tests với benchmark/legal-correctness evaluation.
5. Chỉ chuyển `make demo` sang web UI khi không còn P1/P2 ở R1–R5 và có bằng chứng cho các cổng. Đảm bảo lệnh chạy production phục vụ static build/API cùng origin; Streamlit giữ entry point legacy có tên riêng nếu cần.

Không đổi framework, corpus, frozen benchmark, bảng kết quả D2 hay historical artifacts để hoàn tất kế hoạch này.

## 6. Prompt giao đội agent

> Sửa bản web UI LuatCheck theo `docs/plans/WEB_UI_REPAIR_PLAN.md`, review `docs/reviews/web-ui-review-2026-10-22/REVIEW.md` và AGENTS.md. Chia bốn vai A/B/C/D, chốt snapshot/proposal contract trước, rồi làm song song API và frontend theo ownership. Ưu tiên lỗi restart làm trắng trang, race tạo proposal, proposal expiry không tạo lại được và error bị tô thành success; sau đó sửa breakpoint căn cứ, typography và keyboard. Tái hiện bằng implementation/API/browser và inference thật, không mock hoặc seed output. Giữ các run lỗi và artifacts review gốc. Bàn giao source hashes, commands, screenshots và kết quả từng cổng; không nhận M3 chỉ vì build và 11 core tests pass.

## 7. Kết quả sửa chữa — 22/10/2026

Đã sửa source cho cả năm finding R1–R5 trong review:

- **R1:** API restart lưu snapshot đầy đủ theo contract; snapshot cũ được normalize khi đọc mà không bịa token, budget, grounding hoặc thời gian. API response được validate bằng Pydantic. Lỗi trong một vùng giao diện được ErrorBoundary chặn ở cấp vùng, giữ navigation và có hành động khôi phục.
- **R2:** nút “Căn cứ” hiển thị từ breakpoint mobile tới 1240 px khi panel bị ẩn. Drawer có dialog semantics, làm nền inert, giữ focus trong drawer, đóng bằng Escape và trả focus về nút mở.
- **R3/R4:** SQLite `BEGIN IMMEDIATE` bao trọn thao tác create-or-get và event tạo proposal. Concurrent request dùng cùng logical payload nhận cùng proposal. Proposal hết hạn có attempt ID mới khi tạo lại; idempotency key của logical outbox operation vẫn giữ ổn định.
- **R5:** receipt thành công chỉ nhận `queued_locally`/`duplicate_suppressed`; lỗi/expiry dùng trạng thái cảnh báo, không dấu check xanh. Thành công cập nhật proposal để bỏ nút confirm; renewal giữ payload để người dùng xem lại.
- **Typography:** chữ điều luật và nội dung chính 16 px; các khai báo CSS nhỏ hơn 12 px được nâng tối thiểu 12 px.

### Kiểm tra đã chạy

- `npm --prefix frontend run typecheck` — pass.
- `npm --prefix frontend run build` — pass.
- `.venv/bin/python -m pytest tests/web/test_web_repair_regressions.py -q` — 4 passed; kiểm tra contract/storage và concurrency trên SQLite thật, không thay model/API implementation.
- HTTP/API trên process thật dùng bản sao DB review: legacy run/detail/article đọc được; 12 POST đồng thời nhận cùng proposal ID và tạo một hàng proposal; proposal expired trả 409, tạo lại cùng payload trả attempt ID mới với payload hash ổn định.
- Browser kiểm tra trên answer native đã lưu trong review DB copy: 1024 CSS px và 390 CSS px mở được Điều 26; không tràn ngang ở 390; article text 16 px; dialog keyboard Escape/focus hoạt động. Run restart vẫn hiện lý do lỗi, navigation còn dùng được; thao tác khôi phục chỉ đưa input về form, không tự gọi inference.
- Nhánh outbox expired được kiểm tra bằng HTTP và UI trên DB copy: lỗi hiển thị đỏ, không receipt xanh, có hành động tạo attempt mới và giữ payload. Không xác nhận/ghi outbox trong kiểm tra này.

### Cổng còn mở

- Build/typecheck/regression storage/browser repair pass không hoàn tất M3. Chưa chạy native inference mới trong lượt sửa: Ollama tại `localhost:11434` hiện từ chối kết nối. Không chạy full `tests/` vì suite có native inference; kết quả 11 test và hai native answer trong review gốc là bằng chứng lịch sử của reviewer, không phải lượt chạy lại.
- Chưa kiểm tra lại native outbox success receipt end-to-end ở lượt sửa; review gốc đã có kiểm tra đó. Chưa có screenshot/artifact browser mới được lưu thành bộ nghiệm thu độc lập; các browser assertions ở trên chạy trực tiếp trên UI và API process thật với bản sao review DB.
- Chưa kiểm tra toàn bộ viewport 460, 768, 1240, 1280, 1440; dark theme; mọi clarification/refusal; session isolation/CSRF/queue/SSE; hay toàn bộ native suite trong lượt sửa.
- Vì vậy vẫn giữ `make demo` trên Streamlit và chưa đánh dấu M3 đạt. Benchmark, corpus, report D2, historical runs và review artifacts gốc không được sửa trong lượt này.

## 8. Cập nhật follow-up — 22/10/2026

Sau thời điểm ghi mục 7, Ollama service được khởi chạy tự động bởi ứng dụng đã cài; model `qwen2.5:3b` khả dụng. Một native run mới qua API thật đã `answered`, có citation `Dieu_26` (trang 12), 2 model calls, 3,873 input tokens, 272 output tokens và 18,746.376 ms model wall time. Run ID và provenance được ghi tại `docs/reviews/web-ui-repair-2026-10-22/REPAIR.md`.

Lần browser đầu bị policy từ chối; sau yêu cầu trực tiếp của người dùng, lần thử lại bind tab hiện có thành công. UI hiển thị run `babb53b8-9d6e-4203-b81f-38a905bd1cfa` với lỗi native `model_output_error`, reason nguyên gốc, token usage thật và nút khôi phục; navigation còn dùng được, không có câu trả lời thay thế. Screenshot được quan sát trong browser nhưng không lưu thành file. API vẫn chạy ở cổng này với storage tạm để người dùng xem. Ma trận viewport/theme và full native suite còn thiếu, nên M3 vẫn chưa đạt; `make demo` tiếp tục là Streamlit.
