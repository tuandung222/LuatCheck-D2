# Configuration

One YAML file configures a run. It is validated by pydantic (`src/config/app_config.py`) when it is loaded, and
`src/pipeline/builder.py` turns it into running components. Every key, default and allowed value is listed, with
comments, in [`reference.yaml`](reference.yaml) (it loads, and means "all defaults").

```sh
.venv/bin/python -m src.pipeline config/profiles/local-full.yaml   # validate a config, print what it switches on; loads no model
LUATCHECK_CONFIG_PATH=config/profiles/lite.yaml make web            # use a config (an explicit path that is missing is an error)
```

A file only needs the keys you change. Unknown keys are ignored with a warning (`unknown config key '...'`);
a wrong value for a known key fails at load with the key named.

## Switching components

| Component | Switch | Values |
|---|---|---|
| Controller LLM | `model.provider` | `ollama`, `mlx`, `llamacpp` (aliases `llama.cpp`, `openai`, `prism`, `prism_llamacpp`, `prism-llamacpp`, `prismml`), `gateway` |
| First-stage retriever | `retrieval.mode` | `bm25_tfidf` (default), `hybrid_index` (needs `retrieval.index.path`) |
| Fused second retriever | `retrieval.dense_model_type` | `tfidf` (default), `bm25` (BM25 alone), or an embedding model name served at `model.endpoint` |
| Reranker | `retrieval.reranker.enabled` + `backend` | `cross_encoder`, `qwen3`, `qev_http`, `llamacpp_http`; `max_length`, `chunk_chars` (1500, MaxP over windows, null = off) and `chunk_overlap_chars` (200) apply to `cross_encoder` and `llamacpp_http` (docs/plans/reranker.md) |
| Verification | `verifier.mode` | `off`, `l1` (lexical grounding), `l1_l2` (adds native-model entailment, needs `verifier.l2_use_slm: true`) |
| L1 implementation | `verifier.l1_version` | `v1` (default; original, reproduces the frozen D2 v3 runs), `v2` |
| NLI step | `verifier.nli.enabled` + `backend` | `cross_encoder`, `llm`, `decision_model`, `qev_http`; `action: flag` or `repair` |
| Answer memory | `memory.enabled`, `memory.reuse_answers`, `memory.backend` | `sqlite`; `enabled: false` creates no store |
| Input guardrails | `security.guardrails.enabled` | `true` (default) / `false` |
| Domain | `domain.profile`, `domain.profile_variant` | a file name in `config/domains/`; variant `""` or `r2` (below) |

Rules that apply to all of them:

* Nothing is built or loaded unless its section enables it. The default config loads no model in this process.
* A backend that is unavailable or malformed is an execution error (`terminal_status: error`), never a substitute
  answer, score or ranking. This includes a neural retriever whose embedding service is down.
* A caller that already has a component can pass it to `LuatCheckAgent(...)` (retriever, tool registry, LLM client,
  verifiers, pipeline, store, audit logger) or hand over a whole `AgentComponents`; that wins over the config.

## R2 revision switches

A post-hoc revision of the frozen D2 v3 protocol (fixes F1-F8, F11 of `docs/reviews/v3_failure_analysis_2026-10-24.md`; the plan is
`docs/plans/D2_REVISION_L1_BONSAI4B.md`). Every switch is opt-in and **defaults to the v3 behaviour**: a config that does not name a switch
behaves byte-identically to harness 1.1.2 (`tests/test_r2_switches.py` rebuilds the requests of recorded v3 trials and compares their
`request_sha256`). The v3 runs stay the pre-planned result; a run that sets any of these is a post-hoc revision and must be labelled so.

| Fix | Key | Default (v3) | r2 value | Effect |
|---|---|---|---|---|
| F1 | `retrieval.first_search_anchor` | `none` | `question_plus_query` | first search of a run = user question + the model-query words the question lacks; observation shows `search_note` with the model's query; ledger `query_anchor` records both |
| F2 | `retrieval.default_top_k` | `3` | `5` | `top_k` when the model omits it, capped by `final_top_k` |
| F3 | `tools.search_hints` | `false` | `true` | search observation gains `tool_calls_remaining` and a `hint` (truncated count, read before concluding) |
| F4, F6, F9 | `domain.profile_variant` | `""` | `r2` | loads `<profile>_r2` (`hcmut_academic_r2`, `labour_vi_multi_r2`, `labour_vi_2019_r2`): refuse when the text lacks the answer, clarify only for missing user facts, query guidance, neutral repair prompt |
| F5 | `agent.require_search_before_answer` | `false` | `true` | answer/clarify before any search becomes a "search first" observation (a step, not a tool call); refuse allowed; inactive for closed-book/oracle baselines |
| F6 | `verifier.repair_feedback_style` | `v1` | `verifier_report` | rejection delivered as a labelled `[VERIFIER_REPORT]` observation without the "choose refuse" instruction |
| F7 | `model.thought_max_chars` | `null` | `800` | `maxLength` on `thought` in the action grammar (honoured by the PrismML llama-server); a longer thought from a backend without grammar support is a `model_output_error` |
| F8 | `agent.free_duplicate_notices` | `false` | `true` | `duplicate_query` / `already_read` notices cost a step, not a tool call (ledger event `free_notice`) |
| L1 lite | `verifier.l1_sentence_support` | `block` | `warn` | L1 v2 only: unsupported-sentence findings become warnings (`verification_warnings`, `l1_warning` event); quote and quantity failures still block |
| F11 | (none) | always on | | `ledger.refusal_source` on every refused run: `model`, `repair_exhausted`, `budget`, `guardrail`, `controller` |

Values are validated when the config loads (wrong enum value, `thought_max_chars < 20`, an unknown profile variant fail with the key named);
`profile_variant` needs a profile id, not a path. New wording lives in the language pack (`config/domains/messages/vi.yaml`, keys
`search_hint_*`, `first_search_anchor_note`, `search_first_required`, `repair_report`). `python -m src.pipeline <config>` lists the switches and
whether each is on. The `*_r2.yaml` profiles differ from their originals only in `id`, `system_prompt` and `repair_prompt`.

## Files in this directory

| Path | Purpose |
|---|---|
| `config.yaml` | App default: Ternary Bonsai 2B GGUF on llama.cpp (`make prism-server`), BM25 + TF-IDF/RRF, L1 verification, no reranker, no NLI |
| `profiles/lite.yaml` | Same as `config.yaml` (a test pins them equal) |
| `profiles/local-full.yaml` | `lite` + local reranker and local NLI model (needs `requirements-model-backends.txt` and the cached weights) |
| `profiles/remote.yaml` | `lite` + local reranker + NLI through a Qev server on a forwarded loopback port |
| `d2_*.yaml` | **Frozen** D2 experiment and diagnostic configs. Do not edit; run snapshots refer to them |
| `benchmark/` | **Frozen** inputs of `evaluation/run_benchmark.py` (model blocks, variants, run profiles) |
| `domains/<id>.yaml` | Domain profiles (below). The benchmark locks hash these files: editing one invalidates a frozen benchmark |
| `domains/messages/<language>.yaml` | Controller, tool and verifier wording per language (below) |
| `indexing/`, `ingestion/` | Inputs of `python -m src.indexing` and `python -m src.ingestion` (not app configs) |
| `reference.yaml` | Every app-config key with default and allowed values |

## Domain profiles

Everything specific to one document domain is data in `config/domains/<id>.yaml`: system and repair prompts,
model-facing tool names and descriptions, the document-ID convention, domain guardrail patterns, the L1 quantity
units and stopwords, and the wording of observations and repair feedback. Shared code reads these through
`DomainProfile` (`src/domains/profile.py`) and has no domain constants.

The messages a profile does not set (budget notices, "not found" results, L1/NLI/L2 feedback) come from the pack of
its `language`, `config/domains/messages/<language>.yaml`. A profile can override any of them in its own `messages:`
block. A new language needs a new pack; a profile whose language has no pack must set every message itself.

To add a domain: write its corpus with provenance, add `config/domains/<id>.yaml`, point `retrieval.corpus_path` at
the corpus, and write reviewed tasks before making any claim about it (AGENTS.md).

## Compatibility notes

* Keys kept for older run configs but read by no component: `retrieval.bm25_top_k`, `retrieval.dense_top_k`,
  `verifier.similarity_threshold`, `security.egress_requires_confirmation`.
* `verifier.l1_version` (`v1` | `v2`, default `v1`) selects the L1 implementation. `v1` is the original verifier and
  is kept byte-for-byte so the frozen D2 v3 runs can be repeated; the default keeps every config that predates the key
  (the frozen `d2_*.yaml`, `config/benchmark/`) meaning exactly what it meant. A revised run sets `l1_version: v2` explicitly. `l1_overlap_threshold` applies to
  v1 only, `l1_support_threshold` to v2 only.
* `verifier.mode` accepts the aliases of `src/verifier/modes.py` (`l1_on`, `lexical`, `full`, ...). An invalid value
  now fails when the config is loaded; before, it failed when the agent was built.
* `retrieval.dense_model_type` other than `tfidf`/`bm25` is now also the embedding model name sent to the server
  (it used to be ignored in favour of `all-minilm`).
