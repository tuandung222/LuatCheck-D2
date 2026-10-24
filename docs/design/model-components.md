# Pluggable re-ranking and NLI components

Status: implemented as stand-alone modules, **not yet wired** into `AppConfig`, the agent loop or `src/verifier/pipeline.py` (the orchestrator does that). All backends run real models; failures raise `ModelComponentError` and never produce a substitute score (AGENTS.md).

Files

| file | purpose |
|---|---|
| `src/model_runtime.py` | shared: `ModelComponentError`, device/dtype resolution, loopback check, lazy-load base (`load()`, `unload()`, `load_error`, `info()`), `SystemOneRunner` (decision model, local), `QevHttpClient` (official Qev server over HTTP) |
| `src/retrieval/rerankers.py` | `BaseReranker`, `CrossEncoderReranker`, `Qwen3Reranker`, `LlamaCppReranker`, `DecisionModelReranker`, `QevHttpReranker`, `build_reranker` |
| `src/verifier/nli_backends.py` | `BaseNLIBackend`, `CrossEncoderNLI`, `LLMPromptNLI`, `DecisionModelNLI`, `QevHttpNLI`, `build_nli_backend`, `NLIVerdict` |
| `requirements-model-backends.txt` | optional deps (torch, transformers>=5, sentencepiece, ...) |
| `tests/test_model_components.py` | real-model tests (no mocks) |

## Interfaces

```python
reranker.rerank(query, documents, top_k=None) -> [(doc, score), ...]   # best first, input not mutated
reranker.score(query, documents)              -> [score, ...]          # input order
reranker.last_run   # backend, n_input, n_scored, n_dropped_unscored, wall_ms, ms_per_pair, device, model, ranking[]
reranker.info() / .load() / .unload() / .load_error / .device

nli.classify(premise, hypothesis) -> {"entailment": p, "neutral": p, "contradiction": p}   # sums to 1
nli.verify(premise, hypothesis)   -> NLIVerdict(label, entailed, probabilities, threshold, details)
nli.last_details    # backend, device, wall_ms, backend-specific (n_windows, window_probabilities, ...)
```

`documents` are the dicts returned by `HybridDomainRetriever` (text = `title` + `content`, the title is not repeated when `content` already starts with it; override with `text_fields`) or plain strings. Document IDs are read from `doc_id`/`article_id`/`id`. Nothing in the modules is legal-specific.

`entailed` in `NLIVerdict` = argmax label is `entailment` **and** `P(entailment) >= threshold`.

### Scores are backend-specific (do not compare across backends)

| backend | score |
|---|---|
| `cross_encoder` | raw relevance logit (optional `activation: sigmoid`) |
| `qwen3` | P("yes") from the yes/no logits (Qwen model-card formula) |
| `llama_cpp` | server's `relevance_score` |
| `decision_model` | P(yes) of a one-pass System-One yes/no question |
| `qev_http` | P(yes) (`noul`) returned by an official Qev server, 6-decimal rounding (ties possible) |

NLI probabilities are model outputs. `llm` backend: P(verdict) is the model's self-reported confidence, the rest split equally (`probability_source = self_reported_confidence`, uncalibrated). None of this is evidence of answer correctness; that needs reviewed labels.

## Proposed config keys

```yaml
retrieval:
  reranker:                    # omit / backend: none  -> no re-ranking
    backend: cross_encoder     # cross_encoder | qwen3 | llama_cpp | decision_model | qev_http
    model: AITeamVN/Vietnamese_Reranker
    top_k_in: 30               # candidates taken from the first-stage retriever (retrieval order)
    top_k_out: 5               # candidates returned
    device: auto               # auto (mps if available, else cpu) | cpu | mps
    dtype: float32             # float32 | float16 | bfloat16
    max_length: 1024           # tokens per (query, doc) pair; longer pairs are truncated (counted in last_run.n_truncated)
    batch_size: 1
    local_files_only: false    # true = never touch the network
    # llama_cpp only:  endpoint: http://127.0.0.1:8082   model: <alias>   timeout_seconds: 60
    # qwen3 only:      instruction: "Given a ... query, retrieve ..."
    # decision_model:  max_prompt_tokens: 1024   question: "..."
    # qev_http:        base_url: http://127.0.0.1:18001   model: OmniJev/OneJev1.6-0.8B   timeout_seconds: 60
    #                  allow_remote: false   question: "<statement judged true/false>"   (see "Official Qev HTTP backend")
verifier:
  nli:                         # omit / backend: none -> no NLI
    backend: cross_encoder     # cross_encoder | llm | decision_model | qev_http
    model: MoritzLaurer/mDeBERTa-v3-base-mnli-xnli
    threshold: 0.7             # P(entailment) needed for verify().entailed
    label_map: {0: entailment, 1: neutral, 2: contradiction}   # default: model config id2label
    device: auto
    max_length: 512
    window_overlap: 64
    aggregate: max_evidence    # max_evidence | max_entailment | mean
    max_windows: 64
    batch_size: 1
    # llm only: endpoint: http://127.0.0.1:8081/v1  model: <name>  timeout_seconds  max_tokens  require_loopback: true
    # qev_http only: base_url  model  timeout_seconds  allow_remote  question  options {entailment|neutral|contradiction: description}
```

Unknown keys raise `config_error` (typo protection). Endpoints are loopback-only by default. `build_*` returns `None` only for an empty config or `backend: none`.

## Integration sketch

```python
from src.retrieval.rerankers import build_reranker
from src.verifier.nli_backends import build_nli_backend, ModelComponentError

reranker = build_reranker(cfg.retrieval.reranker)      # None if disabled
nli = build_nli_backend(cfg.verifier.nli)

candidates = retriever.search(query, top_k=cfg.retrieval.reranker["top_k_in"])
if reranker:
    ranked = reranker.rerank(query, candidates)          # raises ModelComponentError on failure -> report as execution error
    candidates = [d for d, _ in ranked]
    log["rerank"] = reranker.last_run                    # keep scores/device/latency in the audit log

verdict = nli.verify(source_article_text, claim)         # premise = the *cited* article, hypothesis = one claim
log["nli"] = {"label": verdict.label, "probs": verdict.probabilities, **verdict.details}
```

Rules for callers: catch `ModelComponentError` only to record an execution error (`.kind`: `config_error`, `missing_runtime`, `load_error`, `backend_error`, `bad_response`, `input_too_long`); do not turn it into a pass/fail verdict or a default ranking. Call `load()` at start-up if you want load errors early; models are otherwise loaded on first use. Call `unload()` (and `release_system_one_runners()` for decision models) to free memory before loading another model.

## Device / memory

* `device: auto` → `mps` when `torch.backends.mps.is_available()`, else `cpu`; an explicit device that is not usable raises. The device actually used is `component.device` and appears in `info()` / `last_run`.
* MPS verified for all four local backends on Apple M4 (see measurements); mDeBERTa is forced fp32 (`require_fp32`, default true; a half-precision dtype is rejected at construction).
* 16 GB machine: defaults are batch size 1, 1024-token cap for rerankers, one model at a time. A reranker and a decision-model NLI configured with the same model share one loaded copy (`get_system_one_runner`).

## Windowing rule of `CrossEncoderNLI` (premises over the model context)

The premise is split into windows of `room = max_length − len(hypothesis_tokens) − 3` premise tokens, consecutive windows overlapping by `window_overlap` tokens (start advances by `room − overlap`); each window is paired with the whole hypothesis. A hypothesis that leaves ≤ `overlap + 1` tokens of room, or a premise needing more than `max_windows` windows, raises `input_too_long` (never silent truncation). Aggregation (`aggregate`):

* `max_evidence` (default): the distribution of the window with the largest `1 − P(neutral)` (earliest on ties);
* `max_entailment`: the window with the largest `P(entailment)` (support-only);
* `mean`: mean of window distributions.

`last_details` keeps every window's distribution and the selected index.
**Measured caveat:** with mDeBERTa, an unrelated window can give a spurious confident contradiction. On a concatenation of Dieu_113/35/24/25/1 with the salary clause (Dieu_26) at the start, the entailed paraphrase scored contradiction 0.71 under `max_evidence` (window with the clause only reached entailment 0.16 when diluted by the following text). With the clause late in the premise it scored entailment 0.97. Pass the cited article/clause as the premise, not a concatenation, and treat windowed verdicts as weaker evidence.

## Decision models (JEV / System One)

Real API (OmniJev/OneJev1.6 model card and github.com/OmniJev/OneJev, package `qev`): a request is a `state` plus typed questions (`Noul` yes/no, `Choice`, `Score`); the model returns a probability per option from **one forward pass** (logits of the option-letter tokens at the last position, softmax, temperature 1 unless a calibration file is given). `SystemOneRunner` re-implements that single-question text path with plain transformers using the published prompt (`qev-labels-v2`, `enable_thinking=False`, float32 head rows). It does **not** install or call `qev`. A cross-check against the official Qev 0.1.4 server (0.8B, 10 items, see `evaluation/probes/qev-onejev-2026-10-23/RESULTS.md`) gave identical prompt token counts on 10/10 items, the same decision on 10/10 and a max probability difference of 0.009 (local MPS bf16 vs the server's 6-decimal output); this is a small sample, not a proof of equivalence. vllm-sr/d3-lite was not examined or run. Observations: the probability mass the model puts on the option letters out of the full vocabulary is small (≈2–5 %, `last_details.allowed_token_mass`) yet the slot softmax is stable and identical (to 3 decimals) between CPU fp32, MPS fp32 and MPS bf16 and ranks/classifies sensibly in the tests; treat the probabilities as model outputs of unverified calibration for this domain. Text states only (no images/video). Cost: ~1.2 s/candidate on MPS because transformers falls back to PyTorch kernels for Qwen3.5 linear attention (`flash-linear-attention` / `causal_conv1d` not installed), so a 30-candidate rerank takes ~40 s.

## Official Qev HTTP backend (`qev_http`)

`QevHttpClient` (`src/model_runtime.py`) talks to an official Qev server (`qev serve --model OmniJev/OneJev1.6-*`, tested against Qev 0.1.4) with `POST /v1/systemone`; `QevHttpReranker` and `QevHttpNLI` are the `qev_http` backends of `build_reranker` / `build_nli_backend`.

* Reranker: one **`noul`** question per candidate, state `{"query", "document"}`, statement "The document contains information that directly answers the query"; score = `answers.q.noul` = P(yes).
* NLI: one 3-option **`choice`** question, state `{"premise", "hypothesis"}`, options `entailment` / `neutral` / `contradiction` (this order = letters A/B/C; override `question` / `options` in the config); distribution = `answers.q.probabilities`.
* The model runs **remotely** (GPU server 82, shared); `last_details` / `last_run` record `remote_inference: true`, client `wall_ms`, the server's `total_s`/`forward_s`, `input_tokens`, `prompt_version`, `prompt_sha256`. Measured through the SSH tunnel: ~0.4-0.5 s per request, of which only ~0.05-0.09 s is server time (`evaluation/probes/qev-onejev-2026-10-23`).
* `base_url` is mandatory (no default). Loopback hosts only (an SSH tunnel on `127.0.0.1`/`localhost`/`::1`); any other host is refused with `config_error` unless `allow_remote: true` is set explicitly. That flag sends premise/query/document text off this machine, so set it only for a server you are entitled to send the data to.
* The first request calls `GET /health` and requires `status: ok` and `model` equal to the configured `model` (a Qev server answers to every OneJev alias, so a wrong port would otherwise be served silently by another model). A mismatch is a `config_error`.
* Errors raise `ModelComponentError`: connection/timeouts and HTTP errors (`backend_error`), non-JSON or structurally wrong bodies, missing/extra options, non-finite or out-of-range probabilities (`bad_response`). No retry, no fallback score. The client never starts/stops a server or tunnel.
* Probabilities come rounded to 6 decimals; reranker ties are broken by retrieval order. Text states only (the client does not send `media`).

```yaml
retrieval:
  reranker:
    backend: qev_http
    base_url: http://127.0.0.1:18001       # SSH tunnel to the server; required
    model: OmniJev/OneJev1.6-0.8B          # must equal the server's /health model (4B: port 18004 + OmniJev/OneJev1.6-4B)
    timeout_seconds: 60
    allow_remote: false                    # true only for a non-loopback host
    top_k_in: 20
    top_k_out: 5
verifier:
  nli:
    backend: qev_http
    base_url: http://127.0.0.1:18004
    model: OmniJev/OneJev1.6-4B
    threshold: 0.7
```

Probe numbers (9 queries / 29 constructed NLI pairs, not human labels, not report evidence): see `evaluation/probes/qev-onejev-2026-10-23/RESULTS.md`. Tests (`TestQevHttpConfig`, `TestQevHttpServers`) run against the real forwarded servers and FAIL naming the port when a tunnel is down.

## Not implemented / not verified

* llama.cpp `/v1/rerank` success path: no reranker server exists on this machine and servers must not be started; the client was only exercised against a running non-reranking llama-server (HTTP 501 raised correctly) and against closed ports. The request/response shape follows llama.cpp's documented OpenAI/Jina-style rerank API and is unverified against a real reranker GGUF.
* `LLMPromptNLI` success path: the only chat server running (llama-server on 8081, a thinking model) spent the whole token budget on reasoning and returned empty content, so the call correctly raised `bad_response`; a successful parse has not been observed.
* `qev_http`: the malformed-response and missing-option branches are not exercised by tests (a real server does not produce them; fakes are not allowed). Images/video (`media`) are not supported by the client.
* `BAAI/bge-reranker-v2-m3` is supported by `CrossEncoderReranker` by construction (same architecture as AITeamVN) but was not run.
