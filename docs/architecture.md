# Architecture

LuatCheck answers questions about a document collection: a bounded controller loop asks a native language model
for one action per step, runs the search or read tool the model chose, and accepts an `answer` only after the
configured verification passes. The current release covers one domain, the original 2019 Vietnamese Labour Code.
The code is domain-agnostic; domain wording and rules are data (`config/domains`).

## Data flow of one run

```
question (+ pasted document)
   |
   v
SecurityGuardrails.check_input_safety  --- unsafe --> terminal "refused" (no model call)      [security.guardrails.enabled]
   |
   v
AnswerMemory.recall  --- similar verified answer, re-verified now --> terminal "answered"   [memory.enabled + reuse_answers]
   |
   v
ReAct loop, at most budgets.max_steps model calls, budgets.max_tool_calls tool calls, budgets.wall_seconds
   |   messages = domain system prompt + wrapped untrusted input + earlier turns
   |   LLM client -> one JSON action, validated against the profile's action schema
   |
   +-- search  -> tool registry -> retriever (BM25 + TF-IDF/RRF | index) -> optional reranker -> snippets
   +-- read    -> tool registry -> verbatim record
   +-- answer  -> VerificationPipeline: L1 lexical grounding [-> NLI step] [-> L2 entailment]
   |                 pass -> terminal "answered"  (+ AnswerMemory.remember)
   |                 fail -> repair prompt with the verifier's feedback (budgets.max_repairs), then "refused"
   +-- clarify / refuse -> terminal "clarified" / "refused" (the model's own text is required)
   |
   v
CaseLedger (tool calls, LLM calls with request hashes, repairs, NLI/rerank metadata) + audit log (JSONL)
```

Any failure of the model or of a model component (unreachable server, malformed action, reranker or NLI backend
error, wall-clock budget) ends the run with `terminal_status: error` and an `error_kind`. It is never converted into
an answer, a refusal or a default ranking. L1 scores are lexical proxies, not correctness.

## Wiring

`LuatCheckAgent` (`src/agent/loop.py`) orchestrates; it does not decide which implementation backs a component.
`src/pipeline/builder.py` does, from the validated `AppConfig`:

```
config.yaml --load_config--> AppConfig --build_components(config, Overrides)--> AgentComponents --> LuatCheckAgent
                                  |                                                  (or pass components= yourself)
                                  +-- python -m src.pipeline <config>  prints which components are on
```

`Overrides` carries anything the caller already owns (retriever, tool registry, LLM client, verifiers, pipeline,
store, audit logger, model manager) plus per-agent settings (model name, endpoint, verification mode). The
protocols the controller relies on are in `src/interfaces/base.py`.

## Module map

| Module | Role |
|---|---|
| `src/config/app_config.py` | pydantic config models, `load_config`, unknown-key detection. Keys: `config/reference.yaml` |
| `src/pipeline/` | `builder.py` (config -> components), `describe.py` and `__main__.py` (print the switches) |
| `src/agent/loop.py` | `LuatCheckAgent`: the run loop and its action handlers |
| `src/agent/llm_client.py` | Native clients (`ollama`, `mlx`, `llamacpp`, `gateway`), action schema and validation, `InferenceError` |
| `src/agent/state.py`, `citations.py` | `CaseLedger`, `ActionType`, `Citation`; citation parsing |
| `src/domains/profile.py` | `DomainProfile`: prompts, tool names, ID rules, guardrail patterns, L1 units, messages (+ language packs) |
| `src/tools/domain_tools.py` | `DomainKnowledgeRegistry` (`LegalToolRegistry` alias): search with snippets and optional reranking, read, summary proposals / local outbox. `mcp_server.py` exposes the same tools over MCP (not used by the loop) |
| `src/retrieval/` | `hybrid_domain.py` (BM25 + TF-IDF/neural RRF; `IndexedRetriever` over a built index), `bm25_engine.py`, `dense_engine.py`, `rerankers.py` (cross-encoder, Qwen3, llama.cpp, Qev backends) |
| `src/verifier/` | `modes.py` (mode vocabulary), `lexical_grounding.py` (L1), `semantic_nli.py` (L2, native judge), `nli_backends.py` (optional NLI backends), `pipeline.py` (stage orchestration, `NLIStep`), `grounding_analyzer.py` (UI/metrics helper) |
| `src/memory/` | `sqlite_store.py` (store, PII filter), `answer_memory.py` (reuse and persist verified answers), `ledger.py` |
| `src/security/` | `guardrails.py` (shared injection patterns + the profile's), `audit_logger.py` (JSONL, PII-filtered) |
| `src/model_manager.py`, `model_runtime.py` | Shared lazy loading, idle unload and memory budget for local reranker / NLI / embedding models; `ModelComponentError` |
| `src/indexing/`, `src/ingestion/` | Offline: source documents -> normalized records -> persisted hybrid index (`python -m src.ingestion`, `python -m src.indexing`) |
| `src/api/`, `src/services/`, `src/ui/` | FastAPI backend + React client support, web run store; legacy Streamlit UI |
| `src/contracts/universal_document.py` | Domain-agnostic document/citation contract |

Compatibility aliases kept for existing callers: `src/tools/legal_tools.py`, `src/retrieval/hybrid_rrf.py`,
`LocalSLMAgent`, `src/agent/prompts.py` (the default profile's prompts).

## Where domain specifics live

| Concern | Location |
|---|---|
| System / repair prompts, tool names and descriptions, ID pattern and aliases, guardrail patterns, L1 units, stopwords | `config/domains/<id>.yaml` |
| Observation, budget and feedback wording | the profile's `messages:`, defaulting to `config/domains/messages/<language>.yaml` |
| Corpus | `retrieval.corpus_path` (data with provenance), or an index |
| Benchmark tasks and rubrics | `evaluation/benchmarks/` |

## Extending

* **A new backend of an existing component**: add the class next to its siblings, add its name to the `Literal` in
  `app_config.py` and to the dispatch in `src/pipeline/builder.py`, and document it in `config/reference.yaml`
  (a test compares the reference with the config models).
* **A new domain**: see `config/README.md`. Do not reuse results of another domain as evidence.
* **Tests** use real implementations only (AGENTS.md): real corpora, real model servers or cached weights, temporary
  storage; no mocks, stubs or monkeypatching.
