# Kế hoạch thay Streamlit bằng web UI độc lập

Ngày lập: 22/10/2026. Đây là kế hoạch bàn giao ban đầu; tình trạng triển khai được ghi ở mục 9.

## 1. Mục tiêu và quyết định kiến trúc

Xây giao diện LuatCheck dễ đọc, có bản sắc, dễ thay đổi bố cục và theme, chạy độc lập với Streamlit. Tái sử dụng backend inference, retrieval, verification và outbox hiện có.

Stack đề xuất:

- Frontend: React + TypeScript + Vite.
- Giao diện: Tailwind CSS + các component shadcn/ui được tùy biến bằng design tokens; Lucide cho icon.
- Backend HTTP: FastAPI + Pydantic, gọi trực tiếp Python core.
- Cập nhật tiến trình: Server-Sent Events (SSE) cho sự kiện thực thi thật.
- Lưu phiên web: SQLite với bảng/schema riêng, tách khỏi episodic cache hiện có.
- Bản đầu: một tiến trình API, một worker inference, phục vụ một tác vụ model tại một thời điểm. Hàng đợi có giới hạn; không để request chờ vô hạn.
- Development: Vite proxy `/api` tới FastAPI. Bản build: FastAPI phục vụ static frontend và API cùng origin, chạy trên loopback.

Đây là lựa chọn thiết kế cho app local hiện tại. Đội triển khai phải kiểm tra phiên bản Python/Node sẵn có, chọn phiên bản tương thích và lưu lockfile trước khi tích hợp.

Tài liệu chính thức đã đối chiếu:

- Vite: https://vite.dev/guide/
- shadcn/ui cho Vite: https://ui.shadcn.com/docs/installation/vite
- FastAPI SSE: https://fastapi.tiangolo.com/tutorial/server-sent-events/

## 2. Hiện trạng đã khảo sát

- `src/ui/app.py`: UI Streamlit, bố cục ba cột, form tình huống/văn bản, mode verifier, ledger, câu trả lời, citations, grounding, HITL và audit inspector.
- `src/agent/loop.py`: `LuatCheckAgent.run(...)` đồng bộ và lưu `self.ledger`; không chia sẻ một agent mutable cho nhiều run.
- `src/agent/state.py`: `CaseLedger` chứa trạng thái cuối `answered`, `clarified`, `refused`, `error`, tool events, budgets và native call records.
- `src/agent/llm_client.py`: inference hiện không stream token. UI Streamlit cũng chỉ render ledger sau khi `run()` trả về.
- `src/tools/domain_tools.py`: proposal, approval token gắn payload và ghi outbox bền vững; approval hiện nằm trong bộ nhớ tiến trình, khóa dispatch là khóa trên từng registry instance.
- `src/config/app_config.py`: cấu hình Pydantic/YAML, có model, budgets, retrieval, verifier, memory, security.
- `src/verifier/grounding_analyzer.py`: có thể tái sử dụng phân tích grounding; đây là lexical proxy.
- `src/ui/app.py` vẫn có nút “Gửi Tóm Tắt Này Qua Email” dù thao tác chỉ ghi local outbox. UI mới phải dùng nhãn đúng hành vi.
- Working tree đang có nhiều thay đổi chưa commit. Không reset, clean hoặc ghi đè để tạo baseline cho công việc UI.

Điểm cần lưu ý: corpus là văn bản gốc Bộ luật Lao động 2019, không phải bản hợp nhất luật hiện hành năm 2026. Không biến nhãn “verified” thành khẳng định tư vấn đúng pháp lý.

## 3. Định hướng thiết kế

Phong cách: không gian làm việc pháp lý, sáng, điềm tĩnh; nền xám ấm, bề mặt trắng, chữ slate đậm, màu nhấn xanh navy/teal. Amber dùng cho phần cần xem xét; đỏ cho lỗi hoặc trạng thái bị chặn. Ưu tiên typography và khoảng trắng.

- Font Be Vietnam Pro, được phục vụ local cùng app; nội dung tư vấn 16–17 px, line-height khoảng 1.65.
- Spacing theo thang 4/8 px; border mảnh; bo góc và elevation nhất quán.
- Theme điều khiển qua CSS variables cho màu, font, spacing, radius và độ rộng panel.
- Desktop: sidebar khoảng 240 px cho phiên/tạo tình huống; vùng chính cho nội dung; panel căn cứ khoảng 340 px có thể thu gọn.
- Dưới khoảng 1100 px: panel căn cứ chuyển thành drawer. Mobile khoảng 390 px: một cột, căn cứ và hoạt động mở qua tab/drawer.
- Nội dung tư vấn là trọng tâm. Tool calls, budgets và audit mở theo nhu cầu trong tab “Hoạt động”.
- Hiển thị phạm vi nguồn ở vị trí dễ thấy: “Bộ luật Lao động 2019 — văn bản gốc”.
- Bản đầu hoàn thiện light theme. Dark theme là phần bổ sung sau khi luồng chính đạt nghiệm thu.

Các khu vực cần có:

1. Màn hình đầu với ô nhập tình huống và vài câu hỏi gợi ý. Gợi ý chỉ điền input, không chứa kết quả tư vấn sẵn.
2. Vùng dán văn bản/hợp đồng, có nhãn rõ là dữ liệu người dùng cung cấp.
3. Kết quả với trích dẫn có thể bấm để mở đúng điều luật, đoạn trích, trang nguồn và provenance thực có.
4. Panel căn cứ hiển thị văn bản nguồn và lexical checks, không dùng “độ chính xác pháp lý”.
5. Timeline “Hoạt động” hiển thị các bước thực thi quan sát được, không trình bày chain-of-thought nội bộ.
6. Dialog xem lại chính xác nội dung trước khi ghi local outbox.
7. Trang cài đặt: theme/layout và các tùy chọn chạy được backend cho phép. Cấu hình dùng cho mỗi run được chụp lại, không tự ghi đè YAML hay cấu hình benchmark.

Đầy đủ trạng thái: trống, đang xếp hàng, đang chạy, có câu trả lời, cần làm rõ, từ chối, lỗi thực thi, mất kết nối sự kiện, nguồn không có, proposal hết hiệu lực và thao tác trùng.

## 4. Hợp đồng backend cần chốt trước khi chia việc

Đặt API dưới `/api/v1`. Điều phối viên và agent API chốt schema request/response, tên event và lỗi trong OpenAPI cùng tài liệu contract.

| Endpoint dự kiến | Trách nhiệm |
| --- | --- |
| `GET /health` | Trạng thái API/model dependency; không coi API sống là model đã sẵn sàng |
| `GET /capabilities` | Model được cấu hình, mode verifier thực sự dùng được, budgets và metadata corpus an toàn để hiển thị |
| `POST /runs` | Nhận query, pasted document, mode; trả `202` và run ID do server tạo |
| `GET /runs` | Liệt kê phiên thuộc browser session hiện tại, có phân trang |
| `GET /runs/{id}` | Snapshot trạng thái/kết quả và căn cứ đã được lọc cho UI |
| `GET /runs/{id}/events` | SSE của run, có sequence ID và hỗ trợ nối lại |
| `GET /runs/{id}/articles/{article_id}` | Văn bản và provenance của điều luật liên quan đến run |
| `POST /runs/{id}/summary-proposals` | Tạo proposal cho đúng payload người dùng chuẩn bị duyệt |
| `POST /summary-proposals/{id}/confirm` | Kiểm tra quyền sở hữu, payload hash và xác nhận từ UI; server approve rồi dispatch |

Quy tắc xử lý:

- Tách trạng thái job `queued/running/finished` khỏi `terminal_status` của agent. Không tự thêm trạng thái vào kết luận của core để trang trí UI.
- Inference lỗi phải giữ `terminal_status=error`; API có thể trả snapshot HTTP 200 nhưng nội dung snapshot vẫn phải thể hiện lỗi rõ ràng.
- Dùng một agent mới cho mỗi run; tạo và sử dụng các tài nguyên có ràng buộc thread trong đúng worker. Không đưa `run()` đồng bộ vào event loop HTTP.
- Outbox đi qua một service/registry có quyền sở hữu rõ ràng trong tiến trình API, tuần tự hóa thao tác. Không tạo nhiều registry với tập idempotency riêng rồi tuyên bố chống trùng giữa chúng.
- Cấu hình mỗi run là snapshot; mode semantic chỉ bật khi native verifier đã được cấu hình dùng được.
- API chỉ trả DTO được chọn lọc. Không trả nguyên `llm_calls`, system prompts, endpoint credentials hay toàn bộ audit log cho browser.
- Kiểm tra browser session sở hữu run/proposal. Bind loopback, cùng origin ở bản build, kiểm tra Origin/CSRF cho mutations và giới hạn kích thước input.
- Approval token nội bộ không trả cho frontend hay model. Payload đổi thì proposal cần được tạo và duyệt lại. Restart làm mất approval chưa lưu phải được báo rõ.
- HTTP retry tạo run dùng request key để tránh vô tình chạy inference lần hai; retry sự kiện SSE chỉ nối lại run cũ.
- Persist snapshot và sự kiện cần thiết vào schema web riêng. Khi restart, các run đang dang dở được ghi nhận interrupted/error, không tự chạy lại.
- Cấu hình retention và đường dẫn lưu hồ sơ/văn bản rõ ràng; không tuyên bố dữ liệu nhạy cảm đã được ẩn hoàn toàn.

SSE phải dựa trên sự kiện thật tại các ranh giới start/tool/verification/repair/finish/error. Thêm một kênh sự kiện production vào runtime với thay đổi tối thiểu, bảo toàn hành vi khi không có subscriber. Event được đánh số và lưu để reconnect không tạo lại tool call. Không đọc ledger đang mutate thiếu đồng bộ. Không dựng token streaming hay phần trăm tiến độ giả; spinner vô định và thời gian đã trôi qua là đủ khi đang đợi model.

Audit lưu trữ và luồng sự kiện UI có mục đích khác nhau. Luồng UI phải lọc nội dung và giới hạn theo phiên; giữ audit provenance hiện có.

## 5. Phân công đội bốn agent

Không agent nào được dùng mock, stub, HTTP response giả, monkeypatch hay component thay thế. Trong lúc API chưa sẵn sàng, frontend dùng empty/loading/disconnected states thực, không dùng câu trả lời mẫu.

| Agent | Phạm vi sở hữu | Kết quả bàn giao |
| --- | --- | --- |
| A — Điều phối và tích hợp | Contract, scope, `Makefile`, `README.md`, tài liệu chạy app | Contract được chốt; phân chia file; lệnh dev/build/run; kiểm tra tích hợp cuối |
| B — API và runtime | `src/api/`, `src/services/`, persistence web, Python dependencies, thay đổi core tối thiểu cho events | API thật, hàng đợi, session isolation, SSE, capabilities, outbox service |
| C — Thiết kế và frontend | `frontend/`, tokens, components, screens, TypeScript client, lockfile | UI hoàn chỉnh, responsive, keyboard accessibility, tích hợp API thật |
| D — QA và kiểm chứng | `tests/web/`, browser E2E, artifacts nghiệm thu và review integrity | Kiểm thử hệ thống thật, ảnh màn hình, log, checklist lỗi và báo cáo giới hạn |

Ranh giới sửa file: B sở hữu Python core/API; C sở hữu frontend; D sở hữu các test web mới; A sở hữu tài liệu và lệnh tích hợp. Nếu phải sửa chéo phạm vi, agent gửi yêu cầu cho người sở hữu trước để tránh đè thay đổi.

Các thư mục đề xuất là nơi triển khai tương lai, không phải những phần đã có sẵn.

## 6. Thứ tự thực hiện và cổng nghiệm thu

**M0 — Chốt nền tảng.** A ghi nhận trạng thái working tree, các luồng phải bảo toàn và schema API. B kiểm tra runtime/phiên bản; C chốt layout, tokens và cách dùng panel. D lập ma trận nghiệm thu. Chốt contract trước khi B/C viết phần tích hợp.

**M1 — Một luồng thật xuyên suốt.** B có `POST /runs` và snapshot; C có form → gọi backend → hiện kết quả/lỗi thật. Giai đoạn này dùng trạng thái chờ và kết quả cuối trung thực; chưa cần timeline đầy đủ. D chạy một tình huống có nguồn với native inference và lưu run ID, log, cấu hình cùng ảnh UI.

**M2 — Trải nghiệm hoàn chỉnh.** B/C bổ sung SSE thực, citations, panel căn cứ, lịch sử phiên, capability gating, lexical labels và dialog outbox. D kiểm tra refresh/reconnect, isolation và ghi outbox thật trong thư mục tạm.

**M3 — Hoàn thiện giao diện và đóng gói.** C kiểm tra typography, responsive và keyboard; B kiểm tra session, error handling và persistence; A thêm lệnh chạy app mới. D chạy regression phù hợp và bàn giao artifacts.

Chỉ chuyển entry point demo mặc định sang web UI sau khi M3 đạt. Streamlit có thể giữ như entry point legacy trong quá trình chuyển đổi. App mới phải khởi động và sử dụng được mà không import/chạy Streamlit. Việc tách dependency Streamlit sang nhóm optional thuộc giai đoạn đóng gói.

## 7. Tiêu chí nghiệm thu bắt buộc

1. Người dùng khởi động web app bằng một lệnh được tài liệu hóa, hỏi và nhận kết quả từ backend native thật. Lệnh build frontend, kiểm tra TypeScript và các kiểm tra Python liên quan đều thành công.
2. Backend không khả dụng phải hiện lỗi thực thi; không có câu tư vấn thay thế, refusal giả hoặc token/cost bằng 0 để che dữ liệu thiếu.
3. Câu trả lời, citations, budgets, trạng thái cuối và metadata UI khớp snapshot/artifacts của run. Chỉ hiện số token/latency model nếu có nguồn đo; dữ liệu thiếu hiện “không có dữ liệu”.
4. Citation mở đúng văn bản nguồn; tỷ lệ từ vựng được ghi là lexical proxy. Không có nhãn khẳng định luật đã cập nhật đến 2026 hoặc tư vấn đã được chứng nhận đúng.
5. Loading và sự kiện hiển thị đúng thời điểm thật; reconnect không tạo run/tool action mới. Refresh vẫn xem được snapshot. API restart không biến run dở dang thành thành công.
6. Hai browser session không đọc/chỉnh run và proposal của nhau. Nhiều lượt gửi không làm ledger bị lẫn; native jobs chạy tuần tự theo giới hạn bản đầu.
7. Outbox thật: không duyệt thì không ghi, payload bị đổi không dùng lại approval cũ, duyệt đúng ghi bền vững, retry không ghi lặp. Nhãn kết quả là “Đã lưu hàng đợi cục bộ; chưa gửi email/webhook”.
8. Semantic mode không sẵn sàng được giải thích bằng capability/error thật; không hạ xuống heuristic mà vẫn giữ nhãn semantic.
9. UI được kiểm tra ở viewport khoảng 1440, 1024 và 390 px; không tràn ngang, tab order hợp lý, dialog có focus management, màu có nhãn chữ đi kèm.
10. Browser/API integration tests gọi server thật, corpus có nguồn và model thật khi cần inference. Có thể dùng file/DB/outbox tạm; tuyệt đối không thay implementation. Thử mất kết nối bằng cấu hình endpoint không hoạt động trong môi trường test riêng, không tắt model server người dùng đang dùng.
11. Không chạy native regression đồng thời với benchmark collection. Không thay corpus, frozen benchmark, historical run artifacts hoặc điền placeholder báo cáo D2 trong công việc UI.
12. Handoff cuối có ảnh UI, lệnh tái hiện, logs/artifacts test, các lỗi còn lại và phân biệt rõ phần đã chạy với phần chưa kiểm chứng. Nếu model không sinh một nhánh trạng thái cần quan sát, ghi nhánh đó chưa kiểm chứng thay vì dựng kết quả.

Không bổ sung dashboard benchmark, email delivery, OCR/upload tài liệu, SaaS authentication hay multi-user deployment vào bản đầu. Các phần đó cần phạm vi và bằng chứng riêng.

## 8. Prompt điều phối có thể chuyển cho đội agent

> Triển khai web UI LuatCheck theo `docs/plans/WEB_UI_HANDOFF_PLAN.md` và toàn bộ `AGENTS.md`. Phân vai A/B/C/D như kế hoạch, chốt contract trước, sau đó chạy song song API và frontend trong phạm vi file riêng. Bắt đầu bằng một luồng form → native agent → kết quả/lỗi thật. Bảo toàn working tree hiện có, inference core, provenance và trạng thái lịch sử. Mọi test dùng implementation thật; không mock hoặc dựng output. Tiến tới M3, lưu artifacts nghiệm thu, rồi bàn giao lệnh chạy, ảnh giao diện và các giới hạn còn lại. Không tuyên bố hoàn thành khi UI chưa chạy với backend thật.

## 9. Tình trạng triển khai — 22/10/2026

Đã thêm API FastAPI dưới `/api/v1`, web-session SQLite riêng, browser-session ownership, CSRF/Origin checks, queue có giới hạn với một native inference worker, run idempotency, SSE lưu bền, snapshot đã lọc, article/provenance endpoint và outbox proposal/confirm. `src/agent/loop.py` phát các sự kiện runtime tùy chọn mà không gửi model thoughts; registry outbox được dùng một lần trong process. Frontend React/Vite có giao diện tiếng Việt, light/dark theme, composer, lịch sử, kết quả/ lỗi thật, lexical proxy, citations, article reader, activity timeline và hộp xem lại local outbox. Contract và lệnh chạy nằm trong `docs/reference/web-ui-api.md` và `README.md`.

Đã kiểm tra TypeScript, production build, Python compile/import và bố cục ở 1440, 1024, 390 CSS px. Một smoke run dùng model endpoint native đã cấu hình thật; endpoint Ollama không kết nối được. Run giữ `terminal_status=error`, `error_kind=backend_error`, một lần gọi model và token counts không có dữ liệu. Snapshot/event đã lưu tại `docs/reviews/web-ui-smoke-2026-10-22/`; không có answer thay thế và run này không phải benchmark hay D2 evidence.

Phần chặn cổng M3: chưa có lượt hỏi thành công với model native nên chưa chuyển `make demo` khỏi Streamlit. Browser/API automated integration suite, kiểm tra isolation bằng hai session, queue saturation, API-restart trên run đang chạy và thao tác ghi outbox thật chưa được kiểm chứng. Outbox, proposal expiry, semantic capability gating và citation matching đã được triển khai nhưng các nhánh đó chưa được nghiệm thu end-to-end. Không sửa benchmark, report D2 hay historical artifacts trong lượt triển khai UI này.

## 10. Follow-up sau review — 22/10/2026

Các lỗi R1–R5 và typography/drawer keyboard được sửa trong lượt follow-up; chi tiết implementation, lệnh và bằng chứng nằm tại `docs/plans/WEB_UI_REPAIR_PLAN.md` mục 7. TypeScript, production build, bốn regression test storage/contract, API concurrency/expiry trên process thật và browser checks tại 1024/390 CSS px đã pass trên bản sao DB review. Review artifacts ban đầu được giữ nguyên.

M3 vẫn **chưa đạt**: lượt sửa không chạy được Ollama native (`localhost:11434` từ chối kết nối), vì vậy không có inference mới hoặc lượt kiểm tra outbox success native mới. Full native suite và các viewport/theme/nhánh còn lại chưa được chạy lại. `make demo` tiếp tục dùng Streamlit; không suy diễn từ build/API checks thành nghiệm thu M3.

**Cập nhật follow-up cùng ngày:** Ollama sau đó đã sẵn sàng với `qwen2.5:3b`; API thật trả một câu hỏi mới ở trạng thái `answered`, có citation `Dieu_26` trang 12 và token usage đo được. Theo yêu cầu thử lại của người dùng, tab localhost sau đó mở được; UI xác nhận một run native lỗi `model_output_error` được hiển thị đúng với reason, usage, navigation và nút khôi phục. Chi tiết hai run nằm trong `docs/reviews/web-ui-repair-2026-10-22/REPAIR.md`. Screenshot được quan sát trong browser nhưng không lưu thành file. Ma trận viewport/theme và full native suite vẫn còn thiếu; M3 chưa đạt và `make demo` vẫn giữ Streamlit.
