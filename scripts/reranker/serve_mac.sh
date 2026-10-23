#!/usr/bin/env bash
# Serve the Vietnamese reranker GGUF with llama.cpp on the Mac (Metal) at 127.0.0.1:8082 (/v1/rerank, /rerank).
# Usage: scripts/reranker/serve_mac.sh [f16|Q8_0|f32]      (default: $RERANKER_QUANT, else f16 = the measured-faithful choice)
# Build the files first with scripts/reranker/build_gguf.sh. The server stays in the foreground (Ctrl-C stops it).
set -euo pipefail

QUANT="${1:-${RERANKER_QUANT:-f16}}"
MODEL_ROOT="${RERANKER_MODEL_ROOT:-$HOME/models/reranker}"
PORT="${RERANKER_PORT:-8082}"
CTX="${RERANKER_CTX:-8192}"          # per-slot context; (query + passage) tokens beyond it are rejected by the server
GGUF="$MODEL_ROOT/gguf/Vietnamese_Reranker-$QUANT.gguf"
[ -f "$GGUF" ] || { echo "missing $GGUF: run scripts/reranker/build_gguf.sh" >&2; exit 1; }

# --reranking: enable /v1/rerank. -ub/-b must be >= the longest (query+passage) sequence: a non-causal model has to
# process the whole sequence in one physical batch. -np 1: one request at a time (the agent loop is sequential).
exec "${LLAMA_SERVER:-llama-server}" -m "$GGUF" --reranking --host 127.0.0.1 --port "$PORT" \
  -c "$CTX" -b "$CTX" -ub "$CTX" -np 1 --alias "Vietnamese_Reranker-$QUANT" ${RERANKER_EXTRA_ARGS:-}
