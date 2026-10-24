# Reranker for D2: one model, one input policy, two runtimes

Written 2026-10-24 (+07). Data: `evaluation/runs/reranker-parity-2026-10-23/` (NOTE.md, report.md, raw scores). Everything below is
measured there unless marked otherwise. Rank metrics against gold ids are **not** answer-correctness evidence; latency was taken on
shared machines and is diagnostic only.

## Decision

The D2 system includes reranking with **`AITeamVN/Vietnamese_Reranker` @ `f536976248403314225d7fdfdbc87f0e9516a54e`**
(XLM-RoBERTa cross-encoder fine-tune of BAAI/bge-reranker-v2-m3, Apache-2.0, 568M parameters, raw relevance logit as score).

| machine | runtime | why |
|---|---|---|
| Mac (demo, latency) | llama.cpp `llama-server --reranking` on 127.0.0.1:8082, **GGUF f16** (client `LlamaCppReranker`, config alias `llamacpp_http`) | faithful to torch fp32 (max abs score diff 0.094), no torch/transformers in the serving path, not slower than torch/MPS fp16 on the same queries, ~1.7 GB RSS. Q8_0 (636 MB, ~1.0 GB RSS) is available but less faithful (max diff 0.31, top-3 ordered agreement 0.96 vs 0.99) and only ~15 % faster. |
| Server 82 (accuracy) | in-process torch **fp16 on CUDA** (`CrossEncoderReranker`, `batch_size: 1`), no server | simplest faithful option on a GPU box: no conversion step, same weights, max abs diff 0.034 vs the fp32 reference. llama.cpp CUDA serving would also work but adds a build and a server per worker for no accuracy benefit. |

No third-party GGUF/ONNX was used. Hugging Face has community GGUF uploads of these weights (for example `tieubaoca/Vietnamese_Reranker-GGUF`,
`ledinhthanh/Vietnamese_Reranker-Q8_0-GGUF`) and ONNX exports of bge-reranker-v2-m3, but none is published by the model's authors and
their provenance, revision and tokenizer metadata cannot be checked. We converted the pinned revision ourselves (ONNX fallback was not
needed because the GGUF is faithful).

## The same system on both machines (input policy)

Both `LlamaCppReranker` and `CrossEncoderReranker` apply the identical policy in the client (defaults of the classes, so any wiring
gets it; `null` switches a part off):

1. Candidate text = `title` + `content` of the full retrieved record (the search tool passes full records, not snippets).
2. `chunk_chars: 1500` (overlap `200`): a longer text is split into windows at clause boundaries (the section's first line is repeated
   in each later window); every (query, window) pair is scored; **document score = max over windows**
   (`last_run['n_chunks']`, `['best_chunk']`).
3. `max_length: 1024` tokens per pair, `longest_first`, 4 special tokens included. `CrossEncoderReranker` does this with the HF
   tokenizer; `LlamaCppReranker` with the server's own `/tokenize` + `/detokenize` (llama-server itself never truncates). With 1500-character
   windows no pair reaches the cap (largest chunk in both corpora: 481 tokens), so the cap only guards pathological inputs.

Why chunking: 8 benchmark tasks have their gold evidence beyond the first 3000 characters of its record (HCMUT-005, 006, 007, 015,
034, 037, 047; LVN-037). With prefix truncation (188 of 2000 scored pairs were truncated) the reranker never sees it: gold ranks with
the torch fp32 reference went HCMUT-005 5 to 2, 007 3 to 2, 015 7 to 1, 037 3 to 1, 047 [1,5] to [2,1] (HCMUT-006, 034, LVN-037 were already 1). Chunking costs
~2x pairs (3984 windows for 2000 documents) and therefore latency.

## Faithfulness of the GGUF (what had to be fixed)

`convert_hf_to_gguf.py` (llama.cpp mainline-derived converter, prism fork 73bfe6c; the Homebrew b9760 server runs the result) writes no
`add_bos_token` and no pair separator for XLM-R. The server then builds `query </s> passage </s>` instead of
`<s> query </s></s> passage </s>`, and scores are wrong although the encoder is identical (cos >= 0.9999998 for HF token ids):
logit 1.448 (torch) vs -3.91 (GGUF). `scripts/reranker/gguf_fix_pair_template.py` sets `tokenizer.ggml.add_bos_token`,
`tokenizer.ggml.seperator_token_id` = EOS and `tokenizer.ggml.add_sep_token`; `build_gguf.sh` does this for every build. Afterwards the
server's `usage.prompt_tokens` equals the HF pair length on 399/400 checked pairs per file (the exception is a pair cut by the token
cap, 1023 vs 1024). `tests/test_reranker_backends.py` guards this. Community GGUFs very likely lack the same metadata.

## Parity vs torch fp32 CPU reference (policy `chunk`, 100 questions x 20 candidates)

| runtime | Spearman mean / min | top-1 agree | top-3 set / ordered | max abs diff | mean abs diff |
|---|---|---|---|---|---|
| GGUF f16 | 0.9994 / 0.9955 | 0.99 | 1.00 / 0.99 | 0.094 | 0.0077 |
| GGUF f32 | 0.9993 / 0.9951 | 0.99 | 0.99 / 0.98 | 0.097 | 0.0078 |
| GGUF Q8_0 | 0.9981 / 0.9744 | 0.99 | 0.98 / 0.96 | 0.309 | 0.0306 |
| H100 torch fp32 (bs1) | 1.0000 / 0.9996 | 1.00 | 1.00 / 1.00 | 0.0004 | 0.0000 |
| H100 torch fp16 bs1 | 0.9943 / 0.9601 | 1.00 | 0.99 / 0.99 | 0.034 | 0.0033 |
| H100 torch fp16 bs16 | 0.9907 / 0.8860 | 1.00 | 0.99 / 0.99 | 0.036 | 0.0035 |

Low per-query Spearman minima in the fp16 rows come from near-ties among irrelevant candidates (score differences <= 0.04); the
decisions that matter (top-1/top-3) agree. Policy `nochunk` gives the same picture (report.md).

**GPU runtime vs Mac GGUF under the shared policy** (A:B, no reference): GGUF f16 : H100 fp16 bs1 = Spearman 0.9941 mean / 0.9601 min,
top-1 0.99, top-3 set 0.99, ordered 0.98, max abs diff 0.126, mean 0.0078. GGUF Q8_0 : H100 fp16 bs1 = 0.9935 / 0.9601, top-1 0.99,
ordered 0.97, max 0.308. So the two machines run the same system up to ~0.1 logit of numerical noise, with one top-1 flip in 100
questions.

## Rank metrics vs gold ids (policy `chunk`; 45 answerable questions per benchmark; not answer correctness)

| system | HCMUT MRR / R@1 / R@3 | labour_vi MRR / R@1 / R@3 |
|---|---|---|
| first stage (BM25 + TF-IDF RRF), gold always inside the 20 candidates | 0.952 / 0.856 / 0.967 | 0.952 / 0.844 / 0.978 |
| torch fp32 CPU (reference) | 0.933 / 0.811 / 0.978 | 0.967 / 0.856 / 0.978 |
| GGUF f16 | 0.944 / 0.833 / 0.978 | 0.967 / 0.856 / 0.978 |
| GGUF Q8_0 | 0.933 / 0.811 / 0.978 | 0.967 / 0.856 / 0.978 |
| H100 fp16 bs1 | 0.933 / 0.811 / 0.978 | 0.967 / 0.856 / 0.978 |

On these question-as-query sets the reranker does **not** improve MRR over the first stage (differences are one or two questions;
n = 45). Do not claim a retrieval gain from it; what the data supports is that the two runtimes behave alike and that long records are
reachable. Whether it improves end-to-end answers needs the l1_rerank variant with reviewed labels.

## Latency and memory (Mac M4 16 GB, diagnostic; 20 candidates = one batch)

| runtime | p50 / p95 ms per query | windows scored | RSS |
|---|---|---|---|
| GGUF f16, chunk | 4595 / 9940 | 3984 | server 1.74 GB |
| GGUF f16, nochunk | 2950 / 5010 | 2000 | 1.6 GB |
| GGUF Q8_0, chunk | 3938 / 10192 | 3984 | 1.03 GB |
| torch fp32 CPU, chunk | 8668 / 25087 | 3984 | python 1.7 GB |
| H100 fp16 bs1 / bs16, chunk | 1171 / 447 (p95 2501 / 612) | 3984 | python 4.3 GB (peak) |

Reranking 20 candidates costs seconds per search call on the Mac (the cost is the ~400-token pairs through a 24-layer encoder, which
is compute-bound). Levers, none applied: `top_k_in` 10 halves it; `chunk_chars: null` removes the chunk factor but reintroduces the
blind spot above. Server flags (`-ub`, `-fa`, `-np`) made no consistent difference (adhoc/ in the run directory). The GPU numbers are
a shared H100 PCIe with a CPU-bound tokenisation path and are not the accuracy-run latency.

## How to run

```
scripts/reranker/build_gguf.sh                 # download pinned revision, convert, fix pair template, quantise (~/models/reranker/gguf)
scripts/reranker/serve_mac.sh f16              # llama-server --reranking on 127.0.0.1:8082 (alias Vietnamese_Reranker-f16); Q8_0 / f32 also possible
scripts/reranker/serve_gpu.sh prepare|check    # server 82: pinned weights + CUDA smoke test (no server)
.venv/bin/python -m pytest -q tests/test_reranker_backends.py     # needs the server on 8082; FAILS (not skips) when it is down
```

Config snippets: `config/reranker/mac_gguf.yaml`, `config/reranker/gpu_cuda.yaml` (both are valid `retrieval.reranker` blocks of
`RerankerConfig`). Failures are loud: a stopped server, a wrong alias, an HTTP error, a malformed response or a CUDA request without
CUDA raises `ModelComponentError` (execution error); no backend returns a score it did not compute and none silently disables reranking.

## Wiring still to do (other owners)

* `RerankerConfig.component_config()` for `llamacpp_http` does not forward `max_length` (class default 1024 applies) and no backend
  forwards `chunk_chars` / `chunk_overlap_chars`; add both keys to `RerankerConfig` (and to the `ModelManager.reranker` cache key) so
  the policy is configurable and recorded. Until then both machines use the identical class defaults.
* Benchmark profiles: Mac `llamacpp_http` base_url 8082 should set `model: Vietnamese_Reranker-f16` (the client verifies the alias
  against `/v1/models`); GPU profile keeps `cross_encoder`, `dtype: float16`, `batch_size: 1`.
* Makefile target for `scripts/reranker/serve_mac.sh` (`rerank-server-mac` is referenced by `profile_mac_latency.yaml`).
* Preflight should record the GGUF sha256 (`~/models/reranker/gguf/SHA256SUMS`) and `usage.prompt_tokens` sanity (pair template).

## Limits

Queries are benchmark questions, not the agent's tool-call queries; one corpus per benchmark; n = 100 questions; latency on a shared
machine; Q8_0/f32 GGUF and fp16 batch>1 are secondary configurations; no human relevance labels were produced.
