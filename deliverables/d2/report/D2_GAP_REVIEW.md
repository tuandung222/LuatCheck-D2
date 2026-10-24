> **Historical (superseded 24 October 2026).** This note describes the Qwen2.5-3B / `bll2019_v1` pilot. Current D2 status: README.md and docs/guides/RUNBOOK_D2.md; requirements gap: docs/reviews/d2_requirements_gap_2026-10-23.md.

# LuatCheck - Review gap giữa project, report D2 và yêu cầu môn học

Ngày review: 21/10/2026. Commit được đọc: `3996f1f84d0dbd1356744b51758f96e829d3c1de`. Đối tượng: source hiện tại, D1, [D2 LaTeX](main_d2.tex), [D2 PDF](main_d2.pdf), các task/kết quả trong repo và [ba nguồn yêu cầu](../../../docs/materials/d2/README.md).

**Kết luận:** chưa nên nộp report D2 hiện tại nguyên trạng. Nhóm đã có nền tảng chạy được bằng fallback: loop có ngân sách, retrieval, verifier, memory, UI và test suite. Gap lớn nhất là **report mô tả kết quả/đường chạy mạnh hơn bằng chứng đang lưu**, đồng thời thiếu một số phần bắt buộc. Cần ưu tiên xác minh số liệu và đồng bộ mô tả với code, sau đó hoàn thiện cấu trúc/nội dung và hồ sơ demo.

## 1. Review này đã kiểm tra đến đâu

- Đọc D1 để xác định cam kết thực tế, không chỉ so D2 với yêu cầu chung.
- Đọc D2 source, trích xuất PDF và xem ảnh cả 6 trang: 1 bìa + 5 trang sau bìa, trong đó có tài liệu tham khảo. Bản đang có không vi phạm giới hạn 10 trang nội dung.
- Đọc các module agent, LLM client, retrieval, tools/MCP, memory, guardrails, verifier, evaluation, red team và UI.
- Chạy toàn bộ tests trong bản sao tạm của repo: **487 passed, 4 warnings, 0 skipped**, thời gian khoảng 20 giây. Tests có cả build LaTeX trong sandbox; không ghi đè report gốc.
- Chạy mới 10 task x 3 seeds x 2 mode = **60 lượt fallback diagnostic**, có đo số lần gọi primary/fallback và lưu ledger. Đây là thực thi mô phỏng theo code hiện tại, **không phải benchmark Qwen native**.
- Thử các ca tổng hợp riêng: sai con số so với corpus nhưng được L1 chấp nhận; cờ xác nhận do caller tự truyền; lỗi chữ ký `get_article`; email giả trong audit log; import MCP.
- Kiểm tra cổng local mặc định: `11434/api/tags` và `8080/health` đều `ConnectionError` tại lúc review. Điều này không chứng minh nhóm chưa từng chạy LLM ở máy/cổng khác.
- Không sửa implementation hoặc report D2. Chỉ thêm tài liệu review và bằng chứng. Chưa kiểm tra quyền đọc repository của Thầy, trình bày trực tiếp, file ngoài repo, tính đúng pháp luật của toàn bộ corpus hoặc mọi nguồn thư mục tham khảo.

Bằng chứng: [diagnostics.json](../../../docs/reviews/d2-gap-review-2026-10-21/diagnostics.json), [pytest-output.txt](../../../docs/reviews/d2-gap-review-2026-10-21/pytest-output.txt), [source-manifest.json](../../../docs/reviews/d2-gap-review-2026-10-21/source-manifest.json).

## 2. Những gap cần ưu tiên cao nhất

### G01. Số liệu trong report chưa có bộ artifact khớp và tái lập được

**Loại:** bằng chứng thực nghiệm + report. **Ảnh hưởng:** A2, A5, B2, B3.

Report `main_d2.tex:309-344` khẳng định 30 lượt/cấu hình chạy Qwen2.5-3B qua Ollama trên Metal. Tuy nhiên:

- [Runner](../../../evaluation/run_eval.py) dòng 38, 49 và 239 mặc định `offline=True`, chuyển endpoint tới `http://127.0.0.1:1`.
- [CompositeLLMClient](../../../src/agent/llm_client.py) dòng 282-286 bắt mọi exception và chuyển sang `MockRuleBasedLLMClient`; không gắn nhãn fallback vào kết quả benchmark.
- Kiểm tra mới ghi nhận **129 primary calls, 0 primary success, 129 primary errors, 129 fallback calls** trên 60 lượt. Neural embedding cũng không hoạt động trong cả hai agent; retrieval dùng nhánh TF-IDF fallback.
- Bảng report khác JSON đang lưu và khác lượt chạy diagnostic mới. Không tìm thấy bộ artifact trong repo chứng minh các số như Recall@1 `0.9333`, coverage `0.8333`, p95 `51,324.55 ms` đúng với phiên bản đang báo cáo.

| Độ đo OFF / L1 ON | Report D2 | JSON lưu `evaluation/eval_results.json` | Diagnostic mới, fallback |
| --- | --- | --- | --- |
| Retrieval Recall@1 | 0.8000 / 0.9333 | 0.7000 / 0.9000 | 0.7000 / 0.7000 |
| Retrieval Recall@5 | 0.8000 / 1.0000 | 0.7000 / 0.9000 | 1.0000 / 1.0000 |
| Citation precision | 0.8000 / 0.8167 | 0.7000 / 0.9000 | 0.7000 / 1.0000 |
| Answer coverage | 1.0000 / 0.8333 | 1.0000 / 1.0000 | 1.0000 / 1.0000 |
| USR theo scorer hiện tại | 0.2000 / 0.0000 | 0.0000 / 0.0000 | 0.0000 / 0.0000 |

Ba cột không phải ba benchmark tương đương: cột JSON lưu không có đầy đủ provenance để xác định chính xác backend/config lúc tạo; cột diagnostic được xác nhận là mock. Không thể dùng việc chạy được mock để xác nhận số liệu Qwen trong report, cũng không thể kết luận các số report chưa bao giờ xuất hiện ở ngoài repo.

**Cần làm:** chọn một commit/config/task set; chạy inference thật với ít nhất số task D2 yêu cầu và một cấu hình đơn giản hơn; cấm fallback âm thầm trong chế độ thu số liệu. Lưu command, model/version/quantization, phần cứng, mode retrieval thực tế, output/trace mỗi task và kết quả chấm. Bảng report phải được sinh/đối chiếu từ đúng bộ artifact đó. Nếu chỉ có mock thì phải ghi rõ mock và giới hạn kết luận; nó chưa xác nhận tuyên bố đã đo Qwen native.

### G02. “USR = 0” không xác nhận không còn phát biểu sai

**Loại:** giới hạn scorer + tuyên bố quá bằng chứng. **Ảnh hưởng:** A2, A5, B3.

[L1 verifier](../../../src/verifier/lexical_grounding.py) dòng 150-164 kiểm tra tỷ lệ giao tập token, ngưỡng 0.25. [Scorer USR](../../../evaluation/metrics.py) dòng 142-152 gọi lại chính verifier này. Kiểm tra tổng hợp thay **85% trong corpus Điều 26 thành 50%** trong một câu có nhiều từ trùng nguồn: L1 vẫn `is_valid=True`, scorer vẫn trả `USR=0.0`.

Vì vậy câu “100% elimination of ungrounded legal claims” tại `main_d2.tex:343` vượt quá điều đã đo. Chỉ số hiện tại là lỗi theo tiêu chí lexical/provenance của code, không phải nhãn độc lập về đúng/sai nội dung tư vấn. Trường `expected_answer` có trong task nhưng runner không dùng để chấm đúng toàn bộ câu trả lời. Với task nhiều gold article, `calculate_retrieval_metrics` còn dùng “có bất kỳ gold nào trong top-k”, nên tên Recall@k cần giải thích hoặc đổi thành hit@k.

**Cần làm:** định nghĩa rõ câu trả lời đúng/sai cho task, kiểm tra độc lập một mẫu output bằng gold/nhãn người, báo cáo lỗi số liệu/phủ định/chủ thể. Không bắt buộc xây ngay L2 mới: có thể giới hạn claim đúng với phép đo và dùng audit thủ công rõ ràng. Nếu dùng LLM-as-judge thì phải thêm kiểm tra độ tin cậy trên mẫu nhãn người theo yêu cầu Thầy.

### G03. MCP và permission boundary chưa khớp report

**Loại:** implementation + mô tả kiến trúc. **Ảnh hưởng:** A1, A3, B1, B3.

1. [MCP server](../../../src/tools/mcp_server.py) dòng 6 import `mcp.server.fastmcp.FastMCP`. Môi trường `.venv` hiện có `mcp==2.3.0`; import thực tế bị `ModuleNotFoundError`. [requirements.txt](../../../requirements.txt) dòng 8 chỉ đặt `mcp>=1.0.0`, không khóa compatibility.
2. MCP `get_article` dòng 29 gọi `registry.get_article(article_id=...)`, nhưng alias trong [domain_tools.py](../../../src/tools/domain_tools.py) dòng 97, 128 trỏ tới `get_document(doc_id)`. Gọi keyword tương ứng đã tái hiện `TypeError`. MCP wrapper chưa chạy qua lỗi này vì lỗi import xảy ra trước.
3. Runtime agent gọi trực tiếp `self.tool_registry` ở [loop.py](../../../src/agent/loop.py) dòng 372, 398; không đi qua MCP client/transport. Vì vậy có code server không đồng nghĩa trace chính đã chạy qua FastMCP như hình dễ làm người đọc hiểu.
4. `dispatch_external_action` nhận `proposal_id`/`approval_token` nhưng không kiểm tra chúng. Test tổng hợp truyền `user_confirmed=True`, proposal không tồn tại, token sai vẫn tạo record thành công dù không có approval server-side. UI có checkbox thật; lỗ hổng nằm ở callable/MCP-facing boundary tin cờ do caller cung cấp.
5. `save_case` trong registry chỉ ghi dictionary trong RAM (`domain_tools.py:130-146`), khác `SQLiteEpisodicStore` được agent tự ghi sau verification. Bảng tools report gán `save_case` cho SQLite/audit chưa đúng đường cài đặt.
6. `send_summary` hiện ghi in-memory/local outbox; không có vận chuyển email/webhook thật trong implementation được đọc. Kiểm tra không gửi thông điệp ra ngoài.

**Cần làm:** hoặc sửa và test MCP thật, hoặc ghi đúng là tool calls trực tiếp và đánh dấu MCP chưa hoàn tất. Cổng ghi phải dựa vào trạng thái phê duyệt do phía tin cậy quản lý, ràng buộc payload/session; caller không tự cấp quyền bằng boolean. Mô tả rõ từng đường ghi và trạng thái triển khai. Thầy cho phép function calling tương đương MCP; không cần ép thêm MCP vào runtime chỉ để giữ một claim.

### G04. Chưa có trace hoàn thành task bằng đường chạy được báo cáo

**Loại:** thiếu bằng chứng bắt buộc. **Ảnh hưởng:** A1, B1.

Report có sơ đồ và đoạn case study, nhưng không có trace task thật thể hiện input, từng tool/action/observation, verification/repair và output cuối. Trace trong UI là khả năng của sản phẩm, chưa thay thế trace cần kèm report. Các trace mới lưu trong review này là fallback diagnostic, không được đưa vào như trace Qwen native.

**Cần làm:** thu một task native hoàn thành thật, đưa trace rút gọn dễ đọc vào report, dẫn full trace trong repo. Ghi model/backend và mode retrieval để phân biệt live inference với fallback/cache.

### G05. Tests xanh đang che khuất một số gap quan trọng

**Loại:** thiếu kiểm chứng phù hợp, không phải thiếu số lượng tests.

[test_challenger_m5.py](../../../tests/test_challenger_m5.py) dòng 196-227 mang tên kiểm tra fidelity nhưng chỉ assert các literal trong LaTeX; tham số `eval_data` không được dùng để so số trong hai bảng. Dòng 97-100 còn giả định D2 bắt buộc 4-6 trang, trong khi tài liệu hiện tại quy định tối đa 10 trang nội dung. Vì vậy **487 tests pass không xác nhận report đúng số liệu hoặc đủ requirements**. Bộ tests chạy cũng chưa bắt lỗi import MCP nêu trên.

**Cần làm:** đối chiếu bảng với kết quả thật, bổ sung integration check cho đường demo/MCP được tuyên bố, kiểm tra schema/provenance artifact. Sửa các điều kiện report theo requirements mới. Không cần tăng số test chỉ để tăng con số pass.

## 3. Đối chiếu từng phần yêu cầu của Thầy

Nguồn quy định: PDF mục 1-4, email mục 3-5 và ghi chú rubric A1-A5/B1-B3. Trạng thái “chưa thấy” chỉ áp dụng cho repo/report được cung cấp.

| Phần/yêu cầu | Hiện trạng | Gap cần xử lý |
| --- | --- | --- |
| PDF, ngôn ngữ, giới hạn trang | Có PDF tiếng Anh; 1 bìa + 5 trang sau bìa | Đạt giới hạn trang; không cần ép còn 4-6 trang theo test cũ. |
| Đúng tám phần và thứ tự | D2 có 6 section; có Related Work riêng; tools/memory gộp vào Architecture; contribution gộp Roadmap | Tổ chức lại đúng tám phần. Có thể rút related work để dành chỗ cho bằng chứng còn thiếu. |
| 1. Thay đổi so proposal | Có hai bullet điều chỉnh | Thiếu bảng cam kết giữa kỳ xong/đang làm/chưa bắt đầu/đã bỏ; thiếu mục xử lý góp ý pitch. Nếu không có góp ý, ghi rõ thông tin thực tế. |
| D1-D2 delta đầy đủ | D1 Qwen3-4B/8B, Qdrant, sentence-embedding support; D2 Qwen2.5-3B, implementation retrieval/verifier khác | Ghi model/retrieval/verifier đã thay đổi gì, vì sao, tác động; không chỉ nêu hoãn L2/FastMCP. |
| 2. Kiến trúc đã cài đặt | Có FSM, sơ đồ, budgets và code loop | Thiếu trace thật; chưa đánh dấu phần native/mock/fallback/pending; đường FastMCP chưa khớp runtime. |
| 3. Tools và quyền | Có bảng bốn tools và phân quyền | Thiếu cột trạng thái triển khai; permission/save_case/egress sai khác như G03. Không phải bổ sung tool thực thi mã nếu hệ thống không có tool đó. |
| 4. Ngữ cảnh và bộ nhớ | Có ledger, SQLite, write/read policy, version match và re-verification | Bổ sung trạng thái chạy; sửa mô tả memory similarity: code dùng hybrid TF-IDF/Jaccard, không chỉ cosine. YAML đặt 0.88 nhưng đường gọi không truyền vào, dùng default 0.85. |
| Nguồn tri thức/retrieval | Corpus lao động đang có 15 article; còn corpus SOP 3 mục | D2 chưa nêu quy mô 15 article, nguồn/phiên bản, cách tạo/kiểm tra corpus, đơn vị chia, embedding/index thực tế và fallback. Không bắt buộc mở rộng corpus ngay để đạt D2, nhưng phải khai đúng phạm vi. |
| 5. Tập task | Có sample 10 và full 20 (15 answer, 5 refuse) | Chưa đủ mapping tới record/split/version gốc VLQA hoặc mô tả ai tự viết/gán gold. Có tên VLQA không tự chứng minh đây là benchmark nguyên bản. |
| Số liệu trên task thật | Có bảng nhưng artifact không khớp | Chốt lại G01: inference thật, ledger, kết quả chấm, config/commit và command tái lập. Code có 20 task không làm số liệu của 10 task tự hợp lệ. |
| Cấu hình đơn giản hơn | Runner có verification OFF | Có thể dùng OFF làm ablation bỏ thành phần theo yêu cầu; sửa nhãn “single-pass RAG” vì code vẫn dùng cùng agent loop. Không nhất thiết phải xây baseline hoàn toàn mới. |
| Cách chấm đúng/sai | Có citation/retrieval/lexical-USR và error taxonomy | Cần định nghĩa correctness nội dung và giới hạn proxy. Với LLM judge, điều kiện nhãn người chỉ áp dụng khi thực sự dùng judge đó. |
| Chi phí/độ trễ | Có bảng token, p50/p95, $0 | Tokens trong runner là ước lượng `len(words)*1.3`, không phải usage backend; $0 được hard-code. Chưa có giờ GPU và cấu hình máy theo nhánh chạy local mà PDF yêu cầu. API fee 0 không có nghĩa compute cost 0. |
| Phân tích lỗi | Có bảng/case study | Phải tái sinh từ đúng runs mới, dẫn task/output lỗi cụ thể; không giữ counts cũ không khớp JSON. |
| 6. Threat model | Có assets và ba attack surface; có paragraphs về defense | Thiếu giả định attacker rõ ràng và bảng mỗi điểm vào -> năng lực -> tài sản -> mitigation dự kiến; tool output/memory/audit cần đưa vào theo implementation. |
| 7. Kế hoạch tới 02/12/2026 | Chỉ có nhóm Weeks 8-9, 10-11, 12 | Thiếu kế hoạch theo tuần 45-49, người phụ trách, giả định rủi ro nhất, phạm vi thu hẹp/phần lõi giữ lại. “ON TRACK” chưa có đối chiếu cam kết để hỗ trợ. |
| 8. Đóng góp thành viên | Có đoạn văn phân việc | Thầy yêu cầu bảng; cần bằng chứng khớp commit/PR/artifact. Git local chỉ thấy hai tên hiển thị dùng cùng tài khoản/email; điều này chưa chứng minh đóng góp từng người, cũng không chứng minh người khác không làm. |
| AI-use statement | Có Claude/Copilot và mục đích | Cần nói cụ thể nhóm tự kiểm chứng gì, bằng artifact nào; câu đã kiểm chứng toàn bộ số liệu/security chưa được artifact hiện tại hỗ trợ. |
| Application Track/AT1 | Track được ghi ở bìa, có nhóm người dùng trong intro | D2 thiếu ít nhất ba kịch bản sử dụng rõ ràng, gồm careless/malicious. D1 đã có ba kịch bản ở `chap1.tex:41-44`, có thể tóm lại thay vì sáng tác mới. |
| Cam kết người dùng thật | D1 `chap1.tex:45` hứa walkthrough HR W5 và báo cáo ở D2 | D2 chỉ đẩy HR walkthrough sang tương lai. Phải nêu đã làm/chưa làm; nếu làm thì ai/thời điểm/bài học, nếu chưa thì ghi lý do và kế hoạch điều chỉnh. Đây là gap so chính proposal. |
| Dữ liệu giả lập/tổng hợp | Không có mô tả rõ phân loại nguồn của task/corpus | Nếu tự biên soạn/tổng hợp phải ghi rõ, nêu khác dữ liệu thật; không tự gắn nhãn “benchmark gold” khi chưa có mapping. |
| Repo URL và commit hash | `git remote` có GitHub URL, nhưng report không ghi URL/hash | Đưa vào report và xác nhận quyền đọc của Thầy. Có remote trong máy không thay thế yêu cầu in trong report. |
| Slide PDF | Chưa thấy slide D2 trong repo; chỉ thấy pitch PPTX D1 | Cần slide D2 PDF; xác nhận nếu đang ở ngoài repo. |
| Video dự phòng | Chưa thấy MP4/MOV/WebM trong repo | Chuẩn bị video cho demo; lưu vị trí truy cập được. Không kết luận nhóm chưa quay nếu file ở ngoài repo. |
| Live demo/Q&A | Có code Streamlit và tests UI | Chưa xác nhận native LLM demo, đường tools thực tế và rehearsed 10+5 phút. Mọi thành viên cần nắm phần mình. |

## 4. Phần security đã làm thêm chưa chứng minh những gì

Thầy **chưa yêu cầu injection tests ở D2**. Đây không phải lý do phải mở thêm nghiên cứu trước deadline; vấn đề là report hiện đang đưa kết luận mạnh từ suite hạn chế.

- Hai ca tên `POISONED_SHARD_*` trong [test_cases.json](../../../redteam/test_cases.json) được truyền qua `pasted_doc`; [runner](../../../redteam/run_redteam.py) dòng 35-40 không cấy payload vào retrieval index/tool observation. Vì vậy chưa chứng minh đã kiểm thử poisoned retrieved shard như nhãn bảng.
- Oracle tại `run_redteam.py:49-61` dựa vào terminal refusal và tìm một vài từ/ID. Không kiểm tra từng attacker objective bằng receipt của tool/outbox hoặc secret canary; mọi non-refusal bị xem exploited, kể cả một câu trả lời an toàn.
- Clean utility tại dòng 89-96 chỉ đếm trạng thái `answered`, không chấm câu trả lời đúng. **100% answered không đồng nghĩa 100% giải đúng task.**
- Report gán việc chặn từng attack cho L1/MCP/SQLite nhưng không có trace quy trách nhiệm. Nếu input regex đã trả refused ngay đầu loop thì run đó chưa thực sự đi tới L1 hoặc cổng egress.
- Audit logger ghi raw query/output. Kiểm tra bằng email giả cho thấy email vẫn nằm trong audit JSONL dù SQLite có sanitizer. Vì vậy phải mô tả phạm vi PII filtering chính xác và đưa log vào threat model; không suy ra tuân thủ pháp luật từ regex.
- Không thấy artifact hậu thuẫn đo “cross-encoder NLI +1.8 s/claim” ở `main_d2.tex:193`. Semantic verifier hiện có local SLM/heuristic comparator, không phải bằng chứng chạy cross-encoder đó.

**Cách xử lý gọn cho D2:** giữ một threat model cụ thể, chuyển kết quả security chưa đủ chứng cứ thành “diagnostic trên bộ input tổng hợp”, bỏ/giảm các kết luận về miễn nhiễm hoặc hiệu quả pháp lý. Nếu giữ bảng attacks, đặt tên đúng đường payload và báo riêng coverage, correctness và attacker success.

## 5. Thứ tự hoàn thiện trước khi nộp

Các owner dưới đây là **gợi ý theo vai trò đã ghi trong report**, không phải xác nhận phân công thực tế.

| Ưu tiên | Việc cần chốt | Bằng chứng hoàn thành | Owner gợi ý |
| --- | --- | --- | --- |
| P1 | Chạy native model + OFF/ON, vô hiệu hóa fallback trong mode thu số liệu | Task outputs/traces + backend metadata + metrics cùng commit, chạy lại được bằng một lệnh | Dũng |
| P1 | Định nghĩa correctness, audit output và sửa claim USR/security | Rubric task/gold; mẫu output đã kiểm; kết luận giới hạn đúng phép đo | Dũng + cả nhóm |
| P1 | Chốt tool path để demo: direct calls hay MCP; sửa permission/write boundary | Smoke/integration evidence cho đúng đường được report; không tự cấp approval bằng tool args | Phong |
| P1 | Đưa repo/hash và một trace thật vào report | URL đọc được, commit tái lập, trace một task native hoàn thành | Cả nhóm |
| P2 | Viết lại đúng tám phần, thêm delta/pitch-feedback/triển khai-pending | Bảng đối chiếu D1 + report theo thứ tự Thầy yêu cầu | Cả nhóm |
| P2 | Chốt corpus/task provenance và AT1; báo trạng thái HR walkthrough | Bảng dữ liệu/index; mapping hoặc nhãn tự biên soạn; ba scenarios; walkthrough status | Quyền + Phong |
| P2 | Threat model + kế hoạch từng tuần tới 02/12 + fallback scope | Bảng entry/attacker/mitigation; tuần/owner/risk/core; tự đánh giá có căn cứ | Cả nhóm |
| P2 | Bảng đóng góp và AI-use theo chứng cứ | Commit/PR/artifact và mô tả kiểm chứng thực tế | Cả nhóm |
| P1 trước buổi báo cáo | Slide PDF, live task, video dự phòng, tập Q&A | Hai PDF sẵn nộp; demo đúng backend; video mở được; tập khoảng 10 phút + 5 phút hỏi đáp | Cả nhóm |

Hồ sơ cần nộp: report PDF và slide PDF, nhóm trưởng email Thầy, CC mọi thành viên, tiêu đề `[CO5151][G8] D2 Interim report`, trước **23:59 Chủ nhật 25/10/2026**. Demo: **18:00 thứ Tư 28/10/2026**, B4-305, thứ tự G1-G8.

## 6. Những thứ không cần xây thêm chỉ để đạt D2

- Không bắt buộc thêm nhiều agent; một agent có control loop rõ ràng vẫn có thể đáp ứng.
- Không bắt buộc cross-encoder/L2 NLI hoặc mô hình 32B; cần ghi rõ thay đổi so proposal và phần nào còn kế hoạch.
- Không bắt buộc hoàn thành tất cả 20 task/200 retrieval pairs của mục tiêu cuối kỳ ngay bây giờ; yêu cầu D2 dùng nguyên văn “ít nhất 5-10 task” đã chạy, có baseline, correctness, chi phí/độ trễ và khả năng tái lập.
- Không bắt buộc mở rộng red team trước khi sửa số liệu, trace và các phần report còn thiếu.
- Không cần thay toàn bộ kiến trúc hoặc làm lại UI. Ưu tiên làm cho phần đang có chạy thật, báo cáo đúng trạng thái và có bằng chứng kiểm tra được.

## 7. Danh mục bằng chứng

- [diagnostics.json](../../../docs/reviews/d2-gap-review-2026-10-21/diagnostics.json): các ca xác minh tổng hợp và thống kê primary/fallback.
- [offline-diagnostic-results.json](../../../docs/reviews/d2-gap-review-2026-10-21/offline-diagnostic-results.json): 60 lượt diagnostic mới, hai mode; chỉ dùng để kiểm tra fallback hiện tại.
- [offline-trajectories.json](../../../docs/reviews/d2-gap-review-2026-10-21/offline-trajectories.json): ledger của các lượt đó; không phải trace native Qwen.
- [offline-diagnostic-output.txt](../../../docs/reviews/d2-gap-review-2026-10-21/offline-diagnostic-output.txt): stdout diagnostic.
- [cli-offline-results.json](../../../docs/reviews/d2-gap-review-2026-10-21/cli-offline-results.json) và [stdout CLI](../../../docs/reviews/d2-gap-review-2026-10-21/cli-offline-output.txt): kiểm tra riêng CLI gốc, vẫn là fallback; không thay kết quả gốc trong `evaluation/`.
- [pytest-output.txt](../../../docs/reviews/d2-gap-review-2026-10-21/pytest-output.txt), [pytest.xml](../../../docs/reviews/d2-gap-review-2026-10-21/pytest.xml): kết quả tests trong bản sao tạm.
- [source-manifest.json](../../../docs/reviews/d2-gap-review-2026-10-21/source-manifest.json): commit và SHA-256 nguồn lúc review.
- [review_checks.py](../../../docs/reviews/d2-gap-review-2026-10-21/review_checks.py): mã kiểm tra để chạy trên một bản sao tạm, không chạy trên dữ liệu production.
