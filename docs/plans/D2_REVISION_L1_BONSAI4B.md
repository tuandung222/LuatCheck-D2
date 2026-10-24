# D2 revision: L1 verifier v2 and Bonsai 4B rerun

> Written 2026-10-24 15:40 +07 by the supervising agent, on the owner's request. Status: in progress.

## Why

The frozen main runs `d2-gpu-main-hcmut-v3` and `d2-gpu-main-labour-v3` (Bonsai 2B, commit 957579b, harness 1.1.2)
are complete and are kept unchanged as the backup result set. Their judge-free numbers exposed problems in L1 and in
how the system drives a small controller. The owner wants a rerun with Bonsai 4B after fixing them.

## Verified L1 problems (from the v3 ledgers, before any change)

| # | Finding | Evidence |
|---|---|---|
| L1-a | Most L1 rejections are exact-quote mismatches, not unsupported claims | 175 of 237 repair events in L1 / L1+rerank are "quote not in source" |
| L1-b | Many "mismatched" quotes are legitimate elisions or wrapper characters | Of 223 failed quotes: 98 contain an ellipsis (`...`, `…`, `[...]`), 51 match ≥80% of their length verbatim (often only surrounding quotation marks or punctuation differ), 54 match 40–80%, 20 are paraphrases |
| L1-c | Quantity check is document-level, so a wrong number passes if it appears anywhere in the cited record | LVN-017 answered "60 ngày" (gold: 10 ngày) and passed L1 |
| L1-d | Repair feedback is not actionable for a 2B model; after a rejection the model usually refuses instead of fixing | HCMUT L1: 34 of 55 refusals on answerable tasks came after 1–2 repairs |
| L1-e | Lexical overlap is a whole-record bag of words with threshold 0.25: lenient for wrong claims that reuse source words, harsh for faithful paraphrases | design review |

## Other observations to investigate (system, not only model)

- Clarify on 30–35% of answerable tasks, mostly right after one search; also 8–10 of 15 refuse tasks end in clarify.
- Model-written search queries retrieve worse than the original question (agent R@5 0.60–0.67 vs ≈1.0 for BM25 on
  the raw question); the reranker recovers part of it (R@5 +0.08 to +0.16).
- Five truncated outputs (`model_output_error`, 1024-token cap).
- Closed-book baseline answers 2–3 of 5 out-of-scope tasks.

## Methodology guard (test-set reuse)

All fixes are decided after seeing results on the same two benchmarks. To limit overfitting:
1. Fixes must be principled bug fixes or generic design changes, justified without reference to individual task ids.
2. No threshold is tuned on `hcmut_v1` / `labour_vi_v1` labels. If a threshold needs data, use the historical
   `bll2019_v1` judged runs as the development set.
3. The report keeps v3 (2B, frozen protocol) as the pre-planned result and labels every revised run as a post-hoc
   revision evaluated on the same tasks. Clean confirmation of the revisions belongs to benchmark v2 (D3).
4. To separate the two changes, run the revised system with BOTH controllers: 2B (isolates the system fix) and 4B
   (isolates model size on the revised system).

## Workstreams

| ID | Work | Owner | Output |
|---|---|---|---|
| W1 | L1 v2: fair quote matching (normalisation, wrapper stripping, ellipsis segments in order), claim-local quantity check, sentence-level support, actionable repair feedback that shows the closest source span; offline replay old vs new L1 on recorded v3 answers; dev-set check on bll2019 | Sonnet | code + tests + `evaluation/probes/l1_replay.py` + report |
| W2 | Results review for other system defects (clarify policy, query construction, truncation, snippets, refusal behaviour) with evidence and ranked, principled fixes; analysis only | Sonnet | `docs/reviews/v3_failure_analysis_2026-10-24.md` |
| W3 | Bonsai 4B on server 82: download pinned GGUF, sha256, CUDA gate, throughput and VRAM | Sonnet (82) | identities for `expected_server.yaml`, model config values |
| W4 | Apply the approved W2 fixes, harness version bump, commit | supervisor + Sonnet | commit on origin |
| W5 | Rerun on 82: revised system × {2B, 4B}, full matrix + baselines, GPUs 2 and 3 | Sonnet (82) | runs `d2-gpu-r2-*` |
| W6 | Judge, analysis, tables; v3 vs revised comparison; L1 offline replay against judge labels | supervisor + Sonnet | tables, registry, report update |
