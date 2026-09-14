# LuatCheck: A Local, Evidence-Grounded Vietnamese Legal Assistant (Deliverable 2 - D2)

**Khóa học:** CO5151 · Advanced Agentic Artificial Intelligence (GV: TS. Lê Xuân Bách, ĐHBK ĐHQG-HCM)  
**Nhóm 8 (Theme 9 - Agentic RAG for Vietnamese Documents - Application Track):**
- **Lê Trí Quyền (Leader)**: Retrieval & Serving (Corpus Ingestion, BM25, Qdrant Dense Index, RRF Hybrid).
- **Nguyễn Hoàng Phong**: System & Security (MCP Toolset, Streamlit UI, Audit Logger, SQLite Episodic Store, Injection Harness).
- **Võ Phạm Tuấn Dũng**: Agent & Evaluation (Budgeted ReAct Loop, Pydantic Structured Output, L1/L2 Evidence Verifier, Evaluation Benchmark).

---

## 1. Tổng Quan Mục Tiêu Cột Mốc D2
- **Interim Progress Report (4–6 trang LaTeX)**: Báo cáo tiến độ chạy thực tế, phân tích Delta so với D1, thiết kế công cụ chuẩn MCP và bộ nhớ kép, kết quả thực nghiệm ban đầu trên 10 tasks VLQA (so sánh Ablation Verification ON vs OFF), Threat Model v1 kèm kết quả kiểm thử bộ 10 ca prompt injection.
- **8-Minute Live Demo**: Trình diễn luồng suy luận thật với giao diện Streamlit, cơ chế L1 Verification bắt lỗi bịa luật, cơ chế từ chối dứt khoát (Refusal Path), và Human-in-the-loop confirmation cho hành động không khả hồi (`send_summary`).

---

## 2. Cấu Trúc Thư Mục Dự Án

```
LuatCheck-D2/
├── config/                  # Cấu hình hệ thống (YAML, model endpoints, thresholds)
├── data/                    # Corpus luật (VLQA), index lưu trữ, sqlite database
├── docs/                    # Tài liệu kiến trúc, threat model, checklist rubric
├── evaluation/              # Benchmark dataset (10-20 tasks), eval runner, metrics
├── redteam/                 # Bộ 10+ ca kiểm thử prompt injection (direct, indirect, poisoned)
├── report_d2/               # Mã nguồn LaTeX báo cáo tiến độ D2 (4-6 trang)
├── src/                     # Mã nguồn chính của hệ thống
│   ├── agent/               # ReAct control loop, state machine, prompt templates
│   ├── tools/               # FastMCP server, legal tools, permission gates
│   ├── retrieval/           # Hybrid retriever: BM25 + Qdrant Dense + RRF
│   ├── verifier/            # L1 deterministic verifier (ID, provenance, span) & L2 NLI
│   ├── memory/              # Short-term ledger & SQLite episodic store
│   ├── security/            # Guardrails, untrusted tagging, JSONL audit logger
│   └── ui/                  # Giao diện tương tác Streamlit cho Live Demo 8'
├── tests/                   # Bộ unit tests cho Agent, Verifier, Security, MCP
└── README.md
```

---

## 3. Khởi Chạy Nhanh (Quick Start)

### Cài đặt môi trường
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Khởi chạy giao diện Demo
```bash
streamlit run src/ui/app.py
```

### Chạy kiểm thử đánh giá định lượng (Evaluation Harness)
```bash
python evaluation/run_eval.py --tasks evaluation/tasks/vlqa_sample_10.json --seeds 42 123 2026
```

### Chạy bộ kiểm thử an toàn (Red Teaming Suite)
```bash
python redteam/run_redteam.py --cases redteam/test_cases.json
```
