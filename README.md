# LuatCheck — D2 working draft

CO5151, Group 8. A local, grounded question-answering agent for Vietnamese regulations: a bounded
action loop searches and reads a document corpus, answers with citations, checks them (L1), and
refuses or asks for clarification when the sources do not answer.

**Current status (24 October 2026):** the D2 system and evaluation are frozen and ready to run; the
main results have **not** been collected yet.

- Controller: Ternary Bonsai 2B (GGUF PQ2_0, prism llama.cpp) for both the reported numbers and the demo.
- Reranker: AITeamVN/Vietnamese_Reranker, GGUF f16 on the Mac and torch fp16 on CUDA, one shared input
  policy; parity in `evaluation/runs/reranker-parity-2026-10-23/report.md`.
- Benchmarks: `hcmut_v1` and `labour_vi_v1` (50 tasks each, frozen and hash-locked; quality audit in
  `docs/reviews/benchmark_quality_2026-10-23.md`).
- Matrix: variants OFF / L1 / L1+rerank x seeds 42, 123, 2026, plus closed-book and oracle diagnostic
  baselines (seed 42). Accuracy on a CUDA server, latency on the Mac. How to run: `docs/RUNBOOK_D2.md`.
- The earlier Qwen2.5-3B pilot on `bll2019_v1` (`evaluation/runs/bll2019-main-v2`) is historical and is
  not used in the D2 report.

## Report and reference materials

- [Revised D2 PDF](report_d2/main_d2.pdf) and [LaTeX source](report_d2/main_d2.tex)
- [Teacher requirements](report_d2/D2_REQUIREMENTS.md)
- [D2 runbook](docs/RUNBOOK_D2.md), [completion plan](docs/plans/D2_COMPLETION_PLAN.md), [requirements gap review](docs/reviews/d2_requirements_gap_2026-10-23.md)
- Reviews: [benchmark quality](docs/reviews/benchmark_quality_2026-10-23.md), [metrics](docs/reviews/metrics_review_2026-10-23.md), [reranker](docs/plans/reranker.md), [public Vietnamese legal benchmarks](docs/reviews/public_vn_legal_benchmarks_2026-10-23.md)
- Presentation: [slide outline](docs/presentation/D2_SLIDES_OUTLINE.md), [demo script](docs/presentation/DEMO_SCRIPT.md)
- [Historical experiment plan (Qwen pilot)](report_d2/D2_EXPERIMENT_PLAN.md)
- [Original teacher materials](docs/materials/d2/README.md)
- [Architecture and module map](docs/architecture.md), [configuration guide](config/README.md)
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

## Quickstart

~~~sh
.venv/bin/pip install -r requirements.txt
make prism-setup                 # once: build the llama.cpp fork and download the 2B GGUF (see "Development commands")
make prism-server                # model server on 127.0.0.1:8081 (leave running)
.venv/bin/python -m src.pipeline # show which components the default config switches on; loads nothing
make rerank-server-mac         # reranker server on 127.0.0.1:8082 (leave running; needed by the demo profiles)
make demo-web                    # D2 demo UI on 127.0.0.1:8000 with a HCMUT / labour corpus switch (or: make web for one default config, make demo for Streamlit)
~~~

From Python:

~~~python
from src.agent.loop import LuatCheckAgent

agent = LuatCheckAgent.from_config("config/config.yaml")     # builds every component the config enables
ledger = agent.run("Thời gian thử việc tối đa là bao lâu?")
print(ledger.terminal_status, ledger.final_output)           # answered | clarified | refused | error
~~~

## Architecture and configuration

One controller loop, five optional parts, each switched in YAML (full list: [config/reference.yaml](config/reference.yaml),
guide: [config/README.md](config/README.md), module map and data flow: [docs/architecture.md](docs/architecture.md)):

| Part | Key | Default in `config/config.yaml` |
|---|---|---|
| Controller model | `model.provider` (`ollama`, `mlx`, `llamacpp`, `gateway`) | `llamacpp` |
| Retrieval | `retrieval.mode` (`bm25_tfidf`, `hybrid_index`), `retrieval.dense_model_type` | BM25 + TF-IDF/RRF |
| Reranker | `retrieval.reranker.enabled`, `.backend` | off |
| Verification | `verifier.mode` (`off`, `l1`, `l1_l2`), `verifier.nli.enabled`, `.backend` | `l1`, NLI off |
| Memory | `memory.enabled`, `memory.reuse_answers` | store on, reuse off |
| Guardrails | `security.guardrails.enabled` | on |
| Domain | `domain.profile` (`config/domains/<id>.yaml`) | `labour_vi_2019` |

`src/pipeline/builder.py` is the single place that turns these keys into components; `LuatCheckAgent` only orchestrates.
A config is validated when loaded and a wrong value names its key. Example, a reranked run with the NLI step:
`LUATCHECK_CONFIG_PATH=config/profiles/local-full.yaml` (check with `python -m src.pipeline config/profiles/local-full.yaml`).
The frozen `config/d2_*.yaml` and `config/benchmark/` files keep their meaning.

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
`LUATCHECK_CONFIG_PATH=config/d2_mlx2b_diagnostic.yaml`. D2 demo (same system as the L1+rerank
variant, reranker server via `make rerank-server-mac`): `make demo-web` serves both profiles (`config/profiles/demo-hcmut.yaml`,
`config/profiles/demo-labour.yaml`) in one web UI with a corpus switch; one profile only: `LUATCHECK_CONFIG_PATH=<profile> make web`. The historical Qwen2.5-3B pilot config is `config/d2_native.yaml`.

The UI needs a real configured model server to answer. An unavailable server is
an error. Configure config/config.yaml or LUATCHECK_CONFIG_PATH; an explicit
missing/malformed config is rejected. Invalid providers, including mock, are
rejected. Neural retrieval must be explicitly configured and fails when its
embedding service is unavailable.

## Native experiments

All D2 numbers come from `evaluation/run_d2.py` (one command per machine, resumable, with preflight
checks of benchmark locks, model files and servers):

~~~sh
make benchmark-preflight          # checks only
make benchmark-smoke              # a few tasks per variant, judge included
make benchmark-d2-gpu             # accuracy matrix on a CUDA server (see docs/RUNBOOK_D2.md)
make benchmark-d2-mac             # latency on the Mac
~~~

Execution errors are results and count as failures. Judge scores are LLM estimates until checked
against the team's human audit (`evaluation/score_benchmark_audit.py`). Metric definitions and their
limits are in `docs/reviews/metrics_review_2026-10-23.md`. Earlier notebooks, JSON results and the
`bll2019_v1` pilot are historical material and are not D2 evidence.
