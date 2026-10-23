# Wiring of the model components into the application

Status: implemented and tested (`tests/test_wiring.py`, real components only; see "Tests"). The stand-alone components are described in
`docs/plans/model-components.md` (rerankers, NLI), `docs/plans/indexing.md` (hybrid index) and `docs/plans/ingestion.md`.
Everything is off by default: `config/config.yaml` and the frozen `config/d2_native.yaml` behave exactly as before (pinned by digests of the search-tool output).

## Config keys (all optional; defaults = previous behaviour)

```yaml
retrieval:
  mode: bm25_tfidf            # bm25_tfidf (default) | hybrid_index
  index:                      # only for mode: hybrid_index
    path: labor_code_2019_vi  # index name under data/index, or a directory
    store: numpy              # vector store inside the index (default: the manifest's default store); faiss stores are rejected
    search_mode: hybrid       # hybrid | keyword | vector
    verify_corpus: true       # refuse an index whose corpus hash changed
  reranker:
    enabled: false
    backend: cross_encoder    # cross_encoder | qwen3 | qev_http | llamacpp_http
    model: AITeamVN/Vietnamese_Reranker
    top_k_in: 20              # first-stage candidates handed to the reranker
    top_k_out: 5              # at most this many returned
    device: auto
    max_length: 1024          # tokens per (query, document) pair; longer pairs are truncated and counted (n_truncated)
    dtype: null               # float32 | float16 | bfloat16
    base_url: null            # qev_http / llamacpp_http; loopback unless allow_remote (qev_http only)
    allow_remote: false
    # extras beyond the shared contract (optional): local_files_only: false, batch_size: 1, timeout_seconds: 60
verifier:
  nli:
    enabled: false
    backend: cross_encoder    # cross_encoder | llm | decision_model | qev_http
    model: MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
    threshold: 0.9            # P(contradiction) at which `repair` fires (also passed to the backend)
    action: flag              # flag | repair
    # any other key (device, max_length, base_url, timeout_seconds, ...) goes to build_nli_backend, which rejects unknown ones
models:                       # ModelManager policy
  idle_unload_seconds: 600
  max_resident_gb: 4.0
  min_free_gb: 1.0            # refuse to load below this much available system memory
  default_estimate_gb: 2.5    # only when a model's weights cannot be sized from the local cache
  wait_for_quiet_machine_gb: null   # optional: wait while another python process holds more than this
domain:
  profile: labour_vi_2019     # existing; new: labour_vi_multi
```

Validation errors (pydantic `ValueError`) name the key: reranker enabled without `model`, `top_k_out > top_k_in`, unknown backend or key, `qev_http`/`llamacpp_http`
without `base_url`, `allow_remote` with `llamacpp_http`, NLI enabled without `model`, `action` not `flag|repair`, `retrieval.mode` other than the two values,
`hybrid_index` without `index.path`. `llamacpp_http` maps to the `llama_cpp` backend of `build_reranker` (`base_url` -> `endpoint`).

## Search tool with a reranker (`src/tools/domain_tools.py`)

`DomainKnowledgeRegistry.search_with_metadata(query, top_k) -> (result, metadata)` (`search_knowledge`/`search_law` return only `result`).
Without a reranker: `retriever.search(query, top_k)` as before. With one:

1. first stage: `retriever.search(query, top_k=top_k_in)`;
2. every candidate is scored against the search query by the reranker (all `top_k_in` scores are kept);
3. the best `min(top_k, top_k_out)` are returned in reranked order; snippets are computed exactly as without a reranker.

The model-visible result is unchanged in shape (no scores, no timings). The metadata goes to the ledger only: the agent loop stores it in the
`tool_call` audit event as `metadata.rerank`:

```
rerank: {requested_top_k, top_k_in, top_k_out, n_candidates, first_stage_ids[], first_stage_ms,
         backend, model, device, dtype, max_length, n_scored, n_truncated, wall_ms, ms_per_pair,
         ranking[{rank, doc_id, input_index, score}]   # all scored candidates, best first; scores are backend-specific
         reranked_ids[], score_note}
```

**Failure.** A reranker/model failure (`ModelComponentError`: `load_error`, `backend_error`, `memory_budget`, ...) is not caught by the tool. The loop records the
search call in the ledger with `error: {kind, type, message}` (no `metadata`, nothing from the first stage is added to the ledger), ends the run with
`terminal_status: error`, `final_output = {action: error, error_kind, verified: false}` and logs `inference_error`. There is no fallback to first-stage order.

When `retrieval.reranker.enabled` and the caller injects its own `tool_registry`, the registry is configured with `configure_reranker(...)`; a registry without that
method raises `ValueError` at construction.

## NLI step (`src/verifier/pipeline.py`, class `NLIStep`)

Optional, after L1, for every non-`off` verification mode (the D2 "ON" mode is `l1`). For each answer sentence (same sentence splitter as L1) and each cited record,
`premise` = the full text of that one record (`title` + `content`, title not repeated), `hypothesis` = the sentence; n sentences x m citations pairs, never a
concatenation of records. Result in `PipelineVerificationResult.nli_result`; the loop writes it to the ledger as an `nli_check` event
(`metadata.nli`: component info, per pair `{sentence, premise_id, premise_chars, label, probabilities, contradiction, contradicted, details}`).

* `action: flag` - records only; the verdict is unchanged.
* `action: repair` - when any pair has `P(contradiction) >= threshold` the verification fails and the existing repair loop runs with an NLI feedback message (budget `max_repairs` applies).
* Not run when L1 failed (the answer is repaired for L1 first) or the mode is `off`. A backend failure raises and ends the run as an execution error; it is never a pass/flag/repair.
* While an NLI step is configured, a cached episodic answer is not reused (it would skip the step); logged as `cache_skipped_nli_enabled`.
* Probabilities are model outputs, not answer correctness. Observed with mDeBERTa on `Dieu_25`: a wrong duration for another job category was scored "entailment" 0.98 and a correct paraphrase 0.89-0.99, while a reversal of "chỉ được thử việc một lần" scored contradiction 0.997 (a few probes, not an evaluation).

## ModelManager (`src/model_manager.py`)

* One shared handle per `(kind, backend, model, device, dtype, base_url, max_length)` (`manager.reranker(cfg)`, `manager.nli(cfg)`); building a handle loads nothing. `ModelManager.shared(models_cfg)` is the process-wide instance used by `LuatCheckAgent` unless `model_manager=` is passed (a later config updates its limits).
* Run a component with `with handle.use() as component:`; the first use loads it. Components are built without `top_k_in/out`; the search tool applies them.
* `sweep()` unloads models idle for >= `idle_unload_seconds`; it runs at every `use()` ("next access check") and optionally from `start_idle_timer(interval)`, a daemon thread that only calls `sweep()` (never inference, never a load). A model in use is never unloaded.
* Budget: cost = max(estimate, measured). The estimate is the parameter count in the cached safetensors headers x the requested dtype width (AITeamVN reranker fp16: 1.06 GB; mDeBERTa fp32: 1.04 GB; `default_estimate_gb` when not cached); `measured` is the RSS + MPS allocation delta of the load (reranker ~1.8 GB, mDeBERTa up to ~1.9 GB on a first load in a fresh process, because it includes one-off runtime/allocator overhead; this makes the budget conservative). Before a load, least-recently-used idle models are unloaded until `resident + cost <= max_resident_gb`; a model larger than the budget, or one that cannot fit because the rest is in use, raises `ModelBudgetError` (`kind: memory_budget`). Available memory (macOS: free + inactive + speculative + purgeable pages via `vm_stat`) below `min_free_gb` also raises. Remote backends (`qev_http`, `llamacpp_http`) hold no local weights and are never counted or unloaded.
* With the default 4.0 GB budget the `local-full` pair (reranker ~1.8 GB + mDeBERTa up to ~1.9 GB as measured in separate fresh processes) just fits; adding the hybrid index's embedding model makes the manager evict the least-recently-used model between calls. Raise `max_resident_gb` only after checking free memory.
* Failures are `ModelComponentError`s; a failed local load is remembered by the component and re-raised on every later use (no silent retry or fallback).

## `retrieval.mode: hybrid_index`

`IndexedRetriever` (`src/retrieval/hybrid_domain.py`) wraps `src/indexing` `load_index(...).searcher(store)`; same interface as `HybridDomainRetriever` (`search`, `get_document_by_id`, `corpus`), so the tool, L1 and NLI step are unchanged. The index's embedding model is a ModelManager component (lazy, budgeted, unloaded when idle). `faiss` stores are rejected with a clear `ConfigError` before anything is opened (faiss and torch cannot share a process on this Mac); numpy, sqlite_vec, lancedb, qdrant-local and chroma are usable. A missing/stale index or failing embedding model raises; there is no fallback to BM25/TF-IDF or keyword-only search. Verified on `data/index/labor_code_2019_vi` (store `numpy`).

## Multi-source answers

When one search returns articles from more than one source (`law_name`/`source_name`), each article carries its own `law_name` and the single top-level `law_name` is omitted; single-source results are byte-identical to before (D2 digests).

## Profiles

* Domain profile `config/domains/labour_vi_multi.yaml` (corpus `data/corpus/labour_vi_v1.json`, not built by this change): same prompt style, tool names (`search_law`/`get_article`), units and labour guardrails as `labour_vi_2019`; source name "Bộ luật Lao động 2019 và các văn bản pháp luật lao động liên quan"; ID pattern `^[A-Za-z][A-Za-z0-9]*(?:_\w+)+$` (`BLLD2019_Dieu_25`, `ND145_2020_Dieu_3`); the "Điều > 220" guardrail applies only when the article number is directly followed by "Bộ luật Lao động"/"BLLĐ" (a decree's own article numbers are not blocked). `labour_vi_2019` and `hcmut_academic` are untouched.
* App profiles (`LUATCHECK_CONFIG_PATH=config/profiles/<name>.yaml` or `--config`): `lite.yaml` = the current `config/config.yaml` (pinned equal by a test); `local-full.yaml` = lite + reranker AITeamVN/Vietnamese_Reranker (MPS fp16, top_k_in 20, top_k_out 5, max_length 1024) + NLI mDeBERTa (fp32, flag); `remote.yaml` = lite + the same reranker + NLI `qev_http` OneJev1.6-4B at `http://127.0.0.1:18004` (flag; needs the SSH tunnel; the app never starts or stops it; premise and answer text leave the process through the tunnel).

## Tests (`tests/test_wiring.py`)

Real corpora, real AITeamVN reranker and mDeBERTa weights (local HF cache, `local_files_only`), the real index and embedding model, the running llama-server (Bonsai, `127.0.0.1:8081`) for the end-to-end runs; a missing model or server fails naming it. Covered: config defaults/parsing/validation and the three profiles; frozen D2 agent (components absent, three search outputs equal their pre-wiring sha256); reranked search (candidates, order, all scores and timing in metadata only, snippets equal to the plain tool, top_k cap, missing weights and dead HTTP reranker raise, mixed sources); ModelManager (cached-size estimate, shared lazy handles, reuse, idle unload on sweep and on the next access, in-use protection, timer that never loads, LRU eviction under a budget that holds one model, over-budget and free-memory-floor refusals before loading, remembered load failure); NLI step (flag vs repair, premise = the whole cited record and one premise per citation, off/L1-failure skip, dead backend raises); `labour_vi_multi` profile; hybrid-index mode (faiss and missing index/store rejected, real search through the managed embedding model); agent construction (lazy, shared handles across agents, injected registry configured); two real agent runs on Bonsai: with a reranker (ledger holds `metadata.rerank`) and with a nonexistent reranker (run ends `error/load_error`, error in the ledger, no first-stage results leaked). The end-to-end tests make no claim about answer correctness. Because a 2B model sometimes clarifies without searching, they try up to three questions and assert on the first run that searched.

## Not done / limitations

* No end-to-end agent run exercises the NLI step (it needs the model to produce a grounded answer); the step is tested directly through the pipeline with real mDeBERTa, and wired into the agent construction (`TestAgentConstruction`). The `llm`, `decision_model`, `qev_http` NLI backends are only checked through the shared code path (`qev_http` against a closed port).
* `retrieval.reranker` with `qev_http`/`llamacpp_http` was exercised only against a closed port (error path); the success paths belong to `tests/test_model_components.py` (Qev servers) and are unverified for llama.cpp rerank (see model-components.md).
* The cached-answer path of the loop does not run the NLI step; it is bypassed instead (see above). The reranker applies to the search tool only; `get_article` is unchanged.
* The shared `ModelManager.shared()` is per process; separate processes (parallel benchmark workers) each load their own copy and do not see each other's budgets.
* The hybrid index loads its embedding model (about 2.1-2.5 GB) on the first query; together with the reranker this exceeds the default 4 GB budget only if both are measured high, in which case the manager evicts the least-recently-used one between calls (reloading costs seconds).
