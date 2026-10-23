#!/usr/bin/env bash
# Build GGUF files of AITeamVN/Vietnamese_Reranker (bge-reranker-v2-m3 fine-tune, XLM-RoBERTa cross-encoder).
#
# Weights are kept OUTSIDE git (default ~/models/reranker). Pinned source revision:
#   AITeamVN/Vietnamese_Reranker @ f536976248403314225d7fdfdbc87f0e9516a54e (2025-05-06)
# Steps: (1) hf download of the pinned revision, (2) convert_hf_to_gguf.py -> raw/*.gguf (f32, f16),
# (3) gguf_fix_pair_template.py -> patched f32/f16 (the converter omits add_bos_token and the </s></s> pair separator,
# without which llama-server scores differ from the HF model, see that script), (4) llama-quantize from the
# patched f16 (Q8_0 by default). Run from the repo root.
#
# Conversion uses convert_hf_to_gguf.py + gguf-py of a llama.cpp checkout that has the XLMRobertaForSequenceClassification
# converter (default ~/src/prism-llama.cpp, commit 73bfe6c). Quantisation uses llama-quantize (Homebrew llama.cpp b9760).
set -euo pipefail

REVISION="${RERANKER_REVISION:-f536976248403314225d7fdfdbc87f0e9516a54e}"
MODEL_ROOT="${RERANKER_MODEL_ROOT:-$HOME/models/reranker}"
LLAMA_SRC="${LLAMA_CPP_SRC:-$HOME/src/prism-llama.cpp}"
PY="${PYTHON:-.venv/bin/python}"
HF_DIR="$MODEL_ROOT/AITeamVN_Vietnamese_Reranker"
OUT_DIR="$MODEL_ROOT/gguf"
QUANTS="${RERANKER_QUANTS:-Q8_0}"      # extra quantisations made from the patched f16 file (space separated)

mkdir -p "$HF_DIR" "$OUT_DIR/raw"
.venv/bin/hf download AITeamVN/Vietnamese_Reranker --revision "$REVISION" --local-dir "$HF_DIR"

for TYPE in f32 f16; do
  RAW="$OUT_DIR/raw/Vietnamese_Reranker-$TYPE.gguf"
  OUT="$OUT_DIR/Vietnamese_Reranker-$TYPE.gguf"
  [ -f "$RAW" ] || PYTHONPATH="$LLAMA_SRC/gguf-py" "$PY" "$LLAMA_SRC/convert_hf_to_gguf.py" "$HF_DIR" \
      --outtype "$TYPE" --outfile "$RAW"
  [ -f "$OUT" ] || "$PY" scripts/reranker/gguf_fix_pair_template.py "$RAW" "$OUT" --gguf-py "$LLAMA_SRC/gguf-py"
done
for Q in $QUANTS; do
  OUT="$OUT_DIR/Vietnamese_Reranker-$Q.gguf"
  [ -f "$OUT" ] || llama-quantize "$OUT_DIR/Vietnamese_Reranker-f16.gguf" "$OUT" "$Q"
done
( cd "$OUT_DIR" && shasum -a 256 Vietnamese_Reranker-*.gguf | tee SHA256SUMS )
