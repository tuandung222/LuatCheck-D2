# Web UI native inference smoke

This folder preserves one real diagnostic run through the new browser UI. It is
not a benchmark trial and is not included in D2 report tables or aggregates.

- Run ID: `801e9177-188d-420e-be58-fed1405d6f35`
- Query: a generic Labour Code question about the maximum probation period
- Configured backend: Ollama, `qwen2.5:3b`
- Result: `job_status=finished`, `terminal_status=error`, `error_kind=backend_error`
- The core attempted one native call. Input and output token counts were absent;
  the UI displayed “Không có dữ liệu” rather than zero.
- The model endpoint was unreachable. No answer, refusal, legal score, or
  benchmark outcome was substituted.
- The run was executed with temporary web DB, audit and outbox paths under
  `/tmp`; its persisted snapshot and event sequence were exported to `run.json`.
  `health.json` records the backend status observed after the smoke run.

The browser layout was inspected at 1440, 1024 and 390 CSS pixel widths. The
frontend TypeScript check and production build passed. Python modules compiled
and the FastAPI app imported. No automated pytest suite or outbox write was run.
The successful native-answer gate remains open, so `make demo` stays on the
legacy Streamlit entry point; start the independent interface with `make web`
after building the frontend.
