# LuatCheck

**A local, source-grounded assistant over Vietnamese regulations that answers only from a loaded document collection, cites the sections it used, verifies every citation against the source text in code, and refuses or asks for clarification when the sources do not answer.**

<p align="center">
  <img src="docs/images/demo/11_hcmut_answer_4b.gif" alt="LuatCheck (4B controller) answering an HCMUT regulation question with a verified citation" width="820">
</p>

---

## Demo Recordings (Bonsai 4B Controller)

| Labour law: verified answer with citation | Citation verifier rejects draft $\rightarrow$ repaired & verified |
|---|---|
| <img src="docs/images/demo/12_labour_answer_4b.gif" alt="Labour-law question answered with a verified citation" width="410"> | <img src="docs/images/demo/13_verifier_repair_4b.gif" alt="Citation verifier rejects first draft quote, controller repairs and passes" width="410"> |

<details>
<summary><strong>Safety & boundary recordings: out-of-scope refusal and prompt-injection guardrail block</strong></summary>
<br>

| Out-of-scope question refused | Prompt-injection attempt blocked before model call (3 ms) |
|---|---|
| <img src="docs/images/demo/14_hcmut_refuse_4b.gif" alt="Out-of-scope question refused" width="410"> | <img src="docs/images/demo/15_guardrail_4b.gif" alt="Prompt-injection attempt blocked by regex guardrail" width="410"> |

</details>

---

## What LuatCheck Does

- **Source-grounded answers over two corpora:**
  1. **HCMUT academic regulations** (10 official decisions/regulations, 143 sections; for students and academic advisers).
  2. **Vietnamese labour law** (10 legal documents: 2019 Labour Code + 2 laws, 6 decrees, 1 circular of 2020–2025, 458 articles; for employees and HR staff).
- **Rule-based L1 citation verifier (`src/verifier/lexical_grounding_v2.py` — deterministic Python heuristic, NOT an LLM, neural model, or second agent):** Every proposed `answer` runs through a $<2\text{ ms}$ rule-based gate with **3 hard checks** and **1 soft diagnostic check** (full specification in [`docs/reference/CITATION_VERIFIER_L1.md`](docs/reference/CITATION_VERIFIER_L1.md)):
  1. *Session retrieval provenance (hard gate):* every cited `article_id` must exist in the corpus and have been returned by `search` or `read_document` in the current run.
  2. *Normalised verbatim / elided quote match (hard gate):* after Unicode NFC, case, and whitespace/line-wrap folding, every non-trivial segment ($\ge 12$ chars or $\ge 3$ words) of a quote (supporting `...` elisions) must appear verbatim and in order inside the cited section, with digit-boundary guards (`5` cannot match inside `15` or `3,5`).
  3. *Claim-local numeric & unit verification (hard gate):* every number + unit in an answer sentence must occur inside the $\le 300$-character source window that best matches the surrounding $\pm 8$ context words of that claim.
  4. *Content-token overlap (soft warning, threshold $\ge 0.50$):* logs a diagnostic warning if fewer than $50\%$ of a sentence's non-stopword tokens appear in the best source window.
  If any hard gate fails, a structured tool report with the closest 170-character source passage is returned to the controller for at most **2 repairs**; if repairs are exhausted, the run terminates as a refusal.
- **Strict read-only tool boundary:** The controller's action schema only exposes `search`, `read_document`, `answer`, `clarify`, and `refuse`. Input regex guardrails (`src/security/`) run before any model call, user text is wrapped in untrusted tags, and the outbound summary queue requires explicit host-UI approval bound to the payload SHA-256 hash.
- **Runs 100% locally on a 16 GiB Mac:** Uses ternary-quantised **Bonsai 4B** (default) or **Bonsai 2B** (faster option) on `llama.cpp` (Apple Metal) together with a local Vietnamese cross-encoder reranker (`AITeamVN/Vietnamese_Reranker`, GGUF f16). A backend or budget failure terminates as an explicit `error` state—never a fabricated answer or silent fallback.

---

## Architecture

![Architecture and control flow of LuatCheck](docs/images/architecture.png)

- **Bounded ReAct loop (`src/agent/`):** At most 8 steps, 5 tool calls, 2 verifier repairs, and 180 s per question; constrained JSON decoding guarantees one valid action per step.
- **Hybrid lexical retrieval + neural reranking (`src/indexing/`, `src/retrieval/`):** First-stage BM25 + word 1–3-gram TF-IDF fused by Reciprocal Rank Fusion (RRF, top-20 candidates), rescored by the cross-encoder reranker to keep the top 5 sections. The first search of every run anchors on the user's original question plus the model's query.
- **Custom Python implementation (no external agent framework):** The control loop, tool registry, retrieval/RRF pipeline, citation verifier, and evaluation harness are written directly in Python (`FastAPI`, `SQLite`, `rank-bm25`, `scikit-learn`, `llama.cpp`), keeping permissions and token/step budgets directly inspectable.

---

## Evaluation & Benchmark Results

> **Evaluation Scope:** The current evaluation suite primarily validates that the end-to-end agentic pipeline and automated measurement harness run reliably and produce reproducible, auditable measurements across configurations. Further system improvements and broader empirical experiments—including harder unseen multi-hop/paraphrased benchmarks where lexical retrieval is not near ceiling, reducing verifier repair-budget over-refusals, dense embedding retrieval, and red-team prompt-injection evaluations—are part of ongoing development.

We evaluate **two self-built, hash-locked 50-question benchmarks** (100 questions total; each benchmark has 40 single-record questions, 5 two-record questions, and 5 out-of-scope refusal questions) across **3 configurations** (`No verifier`, `Verifier`, `Verifier + reranker`), **3 random seeds** (`42, 123, 2026`), and **2 diagnostic baselines** (`Closed-book` without documents, `Oracle` with gold sections given up front) — **1,090 recorded trials per controller**.

| Benchmark | Configuration | Bonsai 2B Judge-Strict (%) | Bonsai 4B Judge-Strict (%) | 4B Unverified Citation Leak (%) | 4B Citation-Audited Strict (%) | Controller scaling 4B − 2B (pp) |
|---|---|---:|---:|---:|---:|---:|
| **HCMUT regulations** | No verifier | 31.3 [22–41] | 70.0 [61–79] | 25.6% (31/121) | 55.3% (83/150) | +38.7 [+27.3, +50.0]* |
| | Verifier (with repair) | 24.0 [15–33] | 64.0 [53–75] | **0.0% (0/109)** | **64.0% (96/150)** | +40.0 [+28.7, +51.3]* |
| | **Verifier + reranker (full)** | 28.7 [20–37] | **60.7 [50–71]** | **0.0% (0/109)** | **60.7% (91/150)** | +32.0 [+21.3, +42.0]* |
| **Labour law** | No verifier | 31.3 [22–41] | 62.0 [52–72] | 28.0% (37/132) | 51.3% (77/150) | +30.7 [+20.7, +40.7]* |
| | Verifier (with repair) | 28.0 [19–38] | 52.7 [43–63] | **0.0% (0/111)** | 52.7% (79/150) | +24.7 [+12.0, +37.3]* |
| | **Verifier + reranker (full)** | 28.0 [19–37] | **56.7 [47–67]** | **0.0% (0/108)** | **56.7% (85/150)** | +28.7 [+18.0, +39.3]* |

*Notes on reading the results:*
1. **Why the rule-based L1 Citation Verifier matters (`Unverified Citation Leak` & `Citation-Audited Strict`):** Without the verifier (`No verifier`), **25.6% (31/121)** of HCMUT answers and **28.0% (37/132)** of labour-law answers emitted by the 4B controller (and **39.8%** / **45.9%** on the 2B controller) leak **unverifiable citations**—fabricated or altered quotes that do not exist verbatim in the PDF, unretrieved section IDs, or numbers borrowed from the wrong clause. Because the LLM judge evaluates answer prose without checking substring/window-number alignment against the full PDF corpus, it credits `No verifier` on 22 (HCMUT) and 16 (labour) answers that carry broken citations. When requiring both LLM-judge correctness and a verifiably authentic citation (**Citation-Audited Strict**), the L1 verifier + repair loop **eliminates unverified citation leakage to 0.0%**, rescues **17–20 flawed first drafts** via bounded repair, and **raises audited strict accuracy from 55.3% $\rightarrow$ 60.7–64.0% (+5.4 to +8.7 pp) on HCMUT and from 51.3% $\rightarrow$ 56.7% (+5.4 pp) on labour law**.
2. **Blind human audit of the LLM judge (`deepseek/deepseek-v4-flash`):** On a stratified blind sample of **60 outputs** (30 per benchmark), judge–human agreement on strict success is **96.7%** ($\kappa = 0.93$, design-weighted 98.8%) on HCMUT regulations and **90.0%** ($\kappa = 0.80$, design-weighted 97.5%) on labour law.
3. **Cost & Mac latency:** Local inference has **USD 0 API cost**; offline LLM judging across both 545-trial runs cost **USD 2.17** in total (`$1.06 + $1.10`). On an Apple M4 MacBook (16 GiB, sequential single-query runs), median / p95 latency for the full system is **33.0 s / 86 s** (HCMUT) and **29.8 s / 72 s** (labour law) with the **4B controller** ($\approx 43$ tok/s), and **13.3 s / 30 s** and **14.6 s / 28 s** with the **2B controller** ($\approx 92$ tok/s).

---

## Quickstart: Running the Live Demo (macOS, 16 GiB)

```sh
.venv/bin/pip install -r requirements.txt
make prism-setup                # once: build the llama.cpp fork and download GGUF weights
make demo-model-server          # terminal 1: Bonsai 4B controller on 127.0.0.1:8081
make rerank-server-mac          # terminal 2: Vietnamese cross-encoder reranker on 127.0.0.1:8082
make demo-web                   # terminal 3: FastAPI + React Web UI on http://127.0.0.1:8000
```

- **Lighter 2B controller option:** Run `make demo-model-server-2b` (port `8083`) and `make demo-web-2b` (port `8001`).
- **Python API usage:**

```python
from src.agent.loop import LuatCheckAgent

agent = LuatCheckAgent.from_config("config/profiles/demo-hcmut.yaml")
ledger = agent.run("Khi tham gia sự kiện của Nhà trường, người học phải có mặt trước giờ khai mạc ít nhất bao lâu?")
print(ledger.terminal_status, ledger.final_output)  # answered | clarified | refused | error
```

---

## Technical Documentation & Evaluation Artifacts

- **L1 Citation Verifier Specification:** [`docs/reference/CITATION_VERIFIER_L1.md`](docs/reference/CITATION_VERIFIER_L1.md)
- **Benchmarks & Metric Definitions:** [`docs/reference/BENCHMARKS_AND_METRICS.md`](docs/reference/BENCHMARKS_AND_METRICS.md)
- **Recorded Evaluation Run Registry:** [`evaluation/runs/REGISTRY.md`](evaluation/runs/REGISTRY.md)

---

## Repository Structure

| Path | Description |
|---|---|
| `src/ingestion/`, `src/indexing/`, `src/retrieval/` | PDF ingestion/normalisation, BM25 + TF-IDF + vector indexing with RRF fusion, cross-encoder reranker |
| `src/agent/`, `src/verifier/`, `src/pipeline/` | Bounded ReAct control loop, rule-based L1 citation verifier & repair, config-driven pipeline builder |
| `src/tools/`, `src/security/`, `src/memory/` | Read-only tool registry & permissions, regex guardrails & PII filter, SQLite memory & audit ledger |
| `src/api/`, `frontend/`, `src/ui/` | FastAPI backend, React/Vite Web UI (`frontend/`), Streamlit UI & trusted outbox |
| `config/` | Runtime profiles (`config/profiles/`), domain configurations (`config/domains/`), benchmark configs |
| `data/corpus/` | Normalized corpora with SHA-256 and page provenance (`hcmut_academic_v1.json`, `labour_vi_v1.json`) |
| `evaluation/` | Frozen 100-task benchmarks (`benchmarks/`), recorded runs (`runs/`), paired comparisons (`comparisons/`), human audit scorer |
| `tests/` | Automated test suite using real components and no mocks (`.venv/bin/pytest tests/ -q`) |
