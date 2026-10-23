# LuatCheck — D2 working draft

CO5151, Group 8. Local Vietnamese labour-law assistant with a bounded action loop,
source lookup and optional evidence checks.

**Current status (22 October 2026):** main collection completed with 60 real
native trials and 264 model calls in `evaluation/runs/bll2019-main-v2`.
All 12 model-output errors are retained and counted. The interrupted 10-trial
batch in `bll2019-main-v1` remains excluded from main aggregates.
Independent artifact arithmetic/hash checks passed; the current real-system
suite passed 11 tests after fail-fast cleanup. DeepSeek Flash gateway judging
accepted 60/60 judgments after retained retries/revalidation; no outcomes remain
unknown. Strict-success estimates are OFF 10/30 and ON 11/30. These are uncalibrated LLM estimates. A 12-output human audit
package is prepared with blank labels. The D2 PDF is still a draft.

## Report and reference materials

- [Revised D2 PDF](report_d2/main_d2.pdf) and [LaTeX source](report_d2/main_d2.tex)
- [Teacher requirements](report_d2/D2_REQUIREMENTS.md)
- [Experiment and report completion plan](report_d2/D2_EXPERIMENT_PLAN.md)
- [Original teacher materials](docs/materials/d2/README.md)
- [Historical gap review](report_d2/D2_GAP_REVIEW.md)
- [Historical results status](evaluation/RESULTS_STATUS.md)
- Historical, not current evidence: [redteam/](redteam/README.md), [report_d3/](report_d3/README.md), `TEST_READY.md`, `TEST_INFRA.md`

The report follows the eight required sections. On 22 October the group reported
no pitch feedback yet, no completed HR walkthrough and no confirmed member
contribution evidence yet. The report records those statuses; the revised
walkthrough date, contribution evidence and final commit/access remain pending.

## Implemented path and limits

- One controller calls the Python registry directly. A separate MCP server is
  available; the main loop does not use MCP transport.
- Native llama.cpp (default on the Mac: Ternary Bonsai 2 2B GGUF on the PrismML fork), MLX or Ollama inference only. Connection, protocol and
  model-format failures produce errors; they never generate substitute answers.
- Default retrieval is explicit **BM25 + TF-IDF with RRF**, over all 220 articles
  of the original 2019 Labour Code, extracted from the official Gazette PDF.
  This is not a consolidated representation of current 2026 law.
- L1 checks IDs, retrieval provenance, lexical overlap and exact quantities.
  These are proxies and cannot certify legal correctness. Optional native NLI
  is outside the frozen D2 core experiment; heuristic NLI substitution was removed.
- SQLite stores answers through the configured verification path; cache reuse
  also requires native-origin metadata and is rechecked. Legacy rows without
  that metadata are skipped. Default index version is native-v2026.10.22;
  existing data are retained. The experiment protocol disables cache reads and writes.
- Model-facing summary tools propose a write. A trusted UI approves the exact
  payload with a random token; a caller boolean cannot self-authorize.
  An approved action writes a durable **local queue**. Email/webhook delivery
  is not implemented. Multi-user and cross-process guarantees are not certified.
- Supported PII patterns are filtered in episodic memory and audit payloads.
  This is incomplete minimisation, not a privacy/compliance guarantee.
- Tests exercise real implementations and native inference. Mock models, HTTP
  doubles, injected stand-ins and monkeypatching are forbidden, including in tests.

See [AGENTS.md](AGENTS.md) for repository integrity rules.

## Development commands

Use Python and dependencies from the existing virtual environment:

~~~sh
.venv/bin/python -m pytest tests/ -q
make report_d2
.venv/bin/python -m src.tools.mcp_server
.venv/bin/streamlit run src/ui/app.py --server.port 8501
~~~

### Local web UI

The independent React interface and FastAPI backend are available alongside the
legacy Streamlit entry point while the native web handoff is being verified.
Install the Python dependencies and frontend packages once, then start the API
and Vite development server in two terminals:

~~~sh
.venv/bin/pip install -r requirements.txt
npm --prefix frontend ci
make web
npm --prefix frontend run dev
~~~

Open `http://localhost:5173`. For the same-origin production build, run
`npm --prefix frontend run build`, then `make web`; FastAPI serves the generated
frontend at `http://127.0.0.1:8000`. The backend binds to loopback by default.
Its local web-session database is `data/db/web_ui.sqlite3`; set
`LUATCHECK_WEB_DB` to choose a different path and `LUATCHECK_WEB_RETENTION_DAYS`
to change the 30-day default retention. Run inputs and snapshots are stored in
that database. User-approved summaries go only to the configured local outbox;
the app does not send email or webhooks.

The API uses one native inference worker and a bounded waiting queue. Run status,
selected snapshots and UI events survive refresh. If the API restarts while a
run is queued or active, the persisted run is marked as an execution error and
is not resumed. `make demo` remains the Streamlit legacy entry point until the
web UI has passed its native end-to-end handoff checks.

The replacement suite uses temporary storage and the actual MCP transport,
retriever and native model. It includes a real inference test: do not run it
concurrently with benchmark collection. The old 509-test suite was retired
because it contained substitutions. MCP uses SDK v2 (mcp >=2.3,<3).

The default app model on the Mac is Ternary Bonsai 2 2B as GGUF PQ2_0
(`prism-ml/Ternary-Bonsai-2-2B-gguf`, ternary weights, ~0.5 GB) on the PrismML llama.cpp fork
(`llama-server`, Metal). On the ten benchmark tasks it ran about 2x faster per task than the MLX build of
the same weights and used ~0.7 GB instead of up to 6.6 GB (`evaluation/runs/gguf2b-bonsai-diag-v1`,
`mlx2b-bonsai-diag-v1`).

~~~sh
make mlx-setup     # once: .venv-mlx with the hf CLI (also enables the MLX alternative)
make prism-setup   # once: clone and build the prism branch, download the GGUF
make prism-server  # OpenAI-compatible server on 127.0.0.1:8081
~~~

Decoding is constrained to the action JSON schema and responses are still validated;
thinking is disabled per request. MLX alternative: `make mlx-server` with
`LUATCHECK_CONFIG_PATH=config/d2_mlx2b_diagnostic.yaml`. Frozen D2 model:
`LUATCHECK_CONFIG_PATH=config/d2_native.yaml` (Qwen2.5-3B via Ollama).

The UI needs a real configured model server to answer. An unavailable server is
an error. Configure config/config.yaml or LUATCHECK_CONFIG_PATH; an explicit
missing/malformed config is rejected. Invalid providers, including mock, are
rejected. Neural retrieval must be explicitly configured and fails when its
embedding service is unavailable.

## Native experiments

`make all` includes the real inference test; it does not start the main benchmark.
`make eval` and `make redteam` do not collect results. The historical
red-team scorer is disabled because refusal/keyword matching does not establish
attack success.

The frozen Mac configuration is cached Qwen2.5:3B Q4_K_M on an Apple M4 with
16 GiB unified memory, Metal, context 8192, output cap 768, one task at a time.
The main workload is 60 trials (10 tasks × 2 modes × 3 seeds), excluding the
8-trial first pilot and 4-trial interface pilot. All model errors are retained.

Follow the [full plan](report_d2/D2_EXPERIMENT_PLAN.md) before collecting data.
The main runner requires explicit --execute, a fresh output directory and an
source-review manifest matching the frozen task and corpus hashes. The current
source reviewer is AI, explicitly not a legal expert. Native usage, errors, full
ledgers and artifact hashes are recorded. Correctness requires independent
semantic review; judge reliability requires actual human labels. Missing
token/compute data stay unknown.

See `evaluation/benchmarks/bll2019_v1/SEMANTIC_JUDGING.md` for the frozen
pre-judging protocol snapshot. Current estimates, retry provenance and the
human audit package are in `evaluation/runs/deepseek-judge-main-v1/analysis-retry-v2/`.
The gateway's legacy Flash alias is documented upstream as V4.1-Flash-1017;
an immutable upstream revision is not independently attested.
Raw usage/cost anomalies are retained; gateway-reported subtotals are not invoices.

Changes to old interfaces are intentional: offline=True and injected unit
agents cannot produce empirical results. Old notebooks/JSONs and the D3 draft
are historical material until reviewed and regenerated under a native protocol.
