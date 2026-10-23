# Slide text: demo model differs from the reported numbers

Paste into the D2 slides. Put the short banner on the demo slide and on every results slide, and the full box
on the slide just before the live demo. Wording matches report Section 1 ("Models and framework").

## Banner (demo slide and every results slide)

> Live demo: Ternary Bonsai 2 2B (GGUF, prism llama.cpp). Main numbers: Qwen2.5-3B (Ollama). The demo does not reproduce these numbers.

## Box (slide before the live demo)

**Which model you are seeing**

| | Reported numbers (Section 5) | Live demo |
|---|---|---|
| Model | Qwen2.5-3B-Instruct, Q4_K_M | Ternary Bonsai 2 2B (`prism-ml/Ternary-Bonsai-2-2B-gguf`, PQ2_0) |
| Runtime | Ollama 0.34.4, Metal | PrismML llama.cpp fork (`llama-server`), Metal |
| Config | `config/d2_native.yaml` (frozen) | `config/config.yaml` (app default) |
| Benchmarked | Yes: 60 native trials | **No** (20 diagnostic trials only) |

- Same loop, corpus (220 articles, BLL 2019) and L1 checks in both.
- Bonsai output is constrained to the action JSON schema; thinking is off. Tool outputs were compacted after the main run.
- Demo behaviour is an illustration, not evidence for the results table.

## Speaker note (one sentence)

"The demo runs the lighter Bonsai model that is now the app default on the Mac; every main number we showed comes
from Qwen2.5-3B, and Bonsai has only a small diagnostic run, not a benchmark result."
