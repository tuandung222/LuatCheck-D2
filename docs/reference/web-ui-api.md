# Local web UI API contract

The API is served from the same origin as the production build. In development,
Vite proxies `/api` to the loopback FastAPI process. Interactive docs are
available at `/docs`; the machine-readable OpenAPI document is `/openapi.json`.

## Session and request protection

- `GET /api/v1/session` creates or resumes an opaque HttpOnly browser-session
  cookie and returns the CSRF token for that browser tab.
- Reads of runs, events, and articles require that cookie and are filtered by
  its session ID. Unknown or foreign run/proposal IDs return `404`.
- `POST` mutations require a loopback `Origin` and `X-CSRF-Token` matching the
  browser session. The production UI and Vite development origin are allowed.
- Query, pasted text and summary sizes are bounded. The default server binds to
  `127.0.0.1` and refuses a non-loopback `LUATCHECK_WEB_HOST`.

## Domain profiles (corpus switch)

One API process can serve several domain profiles. `LUATCHECK_WEB_CONFIGS` is a
comma-separated list of config files (for the D2 demo `make demo-web` sets it to
`config/profiles/demo-hcmut.yaml,config/profiles/demo-labour.yaml`); without it the single
default config (`LUATCHECK_CONFIG_PATH`) is served. Each profile has its own corpus, tool
registry, reranker settings and budgets; they share the controller and reranker servers
named in their configs. A profile that fails to load (missing corpus, bad config) is listed
with `available=false` and its error, and the others keep working.
`GET /api/v1/capabilities` returns `profiles[]` (id, display and short name, tool names, ID
example, corpus record/document counts, retrieval and reranker settings, verifier mode,
budgets, example questions from `src/api/ui_hints.json`), `default_profile` and
`default_verification_mode`. `GET /api/v1/health` also reports whether the configured
reranker server answers its `/health`. Domain wording (short names, scope notes, example
questions) lives in `src/api/ui_hints.json`, keyed by profile id, not in the frontend.

## Runs

`POST /api/v1/runs` accepts `query`, optional `pasted_document`, optional `profile` (a
profile id from `capabilities`; default: the first available; unknown id: `422`), and one
`verification_mode` (`off`, `lexical_grounding`, or `semantic_entailment` only
when native semantic verification is configured). It requires an
`Idempotency-Key`, returns `202` with the server-created `run_id`, and rejects
an overloaded waiting queue with `429` and `Retry-After`. Reusing the key with
the same payload returns the original run; a changed payload returns `409`.

`GET /api/v1/runs` lists only the current browser session's records. A run
snapshot separates `job_status` (`queued`, `running`, `finished`) from the core
`terminal_status` (`answered`, `clarified`, `refused`, `error`). Only selected
output, citations/provenance, budgets, lexical proxy details, and measured
usage are returned. Prompts, model call records, credentials and full audit
logs are not exposed.

`GET /api/v1/runs/{run_id}` also returns `pasted_document` for restoring the
user's own input in that same browser session. The paginated list omits it.
Persisted snapshots are validated and normalized on read: missing collection
fields become empty collections, missing measurement fields remain `null`,
and the verification mode comes from the stored run configuration. An
inconsistent legacy terminal status is surfaced as an execution error instead
of being presented as a successful answer. Restarted jobs keep
`terminal_status=error` and `error_kind=api_restart`.

A finished snapshot also carries `profile` (id and display name), `refusal_kind`
(`guardrail` = blocked before any model call, `verification_failed` = the L1 check kept
failing until the repair budget ran out, `model` = the controller chose to refuse) and
`final_output.pre_model_policy_refusal`. The run summary has `profile_id`.

`GET /api/v1/runs/{run_id}/events` streams persisted SSE records. It uses SSE
event IDs and accepts `Last-Event-ID` to resume the same run. Event names are:
`run_queued`, `run_started`, `model_call_started`, `tool_completed`,
`verification_completed`, `repair_started`, `run_finished`, `run_persisted`,
`run_failed`, `run_interrupted`, `summary_proposal_created`, and
`summary_proposal_completed`. Activity events contain operational metadata,
never model thoughts or token-by-token output. Each event carries `t_ms` (milliseconds since
`run_started`). `tool_completed` also carries the search `query` or the requested id, the
returned ids with titles, and for a reranked search the first-stage and reranked ids, the
reranker model and its measured wall time; `tool_completed`, `verification_completed` and
`run_finished` carry `model` (wall time, input/output tokens and chosen action of the model
call that preceded them, as recorded by the client); `repair_started` carries the verifier
feedback; `run_finished` carries `failed_tool` when a search failed (for example the
reranker server is down). These values are copied from the case ledger; nothing is estimated.
The UI timeline is built only from these events.

`GET /api/v1/runs/{run_id}/articles/{article_id}` returns the corpus text and
the recorded source URL, pages, SHA-256, extraction note and scope.

## Summary outbox

`POST /api/v1/runs/{run_id}/summary-proposals` stores the exact recipient and
content for a review step. `POST /api/v1/summary-proposals/{proposal_id}/confirm`
checks browser ownership and the bound payload hash; the server alone obtains
and uses the internal approval token. A changed payload needs a new proposal.
Confirmation appends to the configured local outbox, which is a queue only and
does not send email or webhooks. Confirm retries return the persisted result.
Pending approvals expire after an API restart because approval tokens are
memory-only. Concurrent create requests for the same run/session/recipient/
content resolve to the same persisted proposal. If an attempt expired, creating
the same payload again opens a new review attempt while retaining the stable
logical outbox idempotency key; the user must review and confirm that attempt.
The stored confirmation receipt must have status `queued_locally` or
`duplicate_suppressed` before the API reports completion. A missing or invalid
receipt is an HTTP 503, not a successful zero-effect confirmation.

## Persistence and failures

The web-session database defaults to `data/db/web_ui.sqlite3` and a 30-day
retention period. Set `LUATCHECK_WEB_DB` or `LUATCHECK_WEB_RETENTION_DAYS` to
change those settings. A restart marks queued/running records as `error` with
`error_kind=api_restart`; the server does not resume model work. Native model,
retrieval, configuration and response-format failures remain execution errors;
the API never makes a rule-based answer or a successful zero-usage result.
