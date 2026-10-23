#!/usr/bin/env bash
# GPU (server 82, H100) reranker: AITeamVN/Vietnamese_Reranker as an in-process torch fp16 CrossEncoderReranker
# (config/reranker/gpu_cuda.yaml). There is NO server to start: each benchmark worker loads the model itself.
# This script only (a) downloads the pinned revision to a local dir and (b) smoke-tests it on a free GPU.
#
#   scripts/reranker/serve_gpu.sh prepare [DIR]     download revision f536976 into DIR (default $RERANKER_MODEL_DIR or
#                                                   $HOME/models/reranker/AITeamVN_Vietnamese_Reranker); print the export line
#   scripts/reranker/serve_gpu.sh check  [DIR]      load it with CrossEncoderReranker (cuda, fp16) and score 2 pairs
#
# Shared machine rules: choose a free GPU with gpu_status and export CUDA_VISIBLE_DEVICES; never touch other users' work.
set -euo pipefail
REVISION="${RERANKER_REVISION:-f536976248403314225d7fdfdbc87f0e9516a54e}"
ACTION="${1:-check}"
DIR="${2:-${RERANKER_MODEL_DIR:-$HOME/models/reranker/AITeamVN_Vietnamese_Reranker}}"
PY="${PYTHON:-python}"

case "$ACTION" in
  prepare)
    mkdir -p "$DIR"
    "$PY" - "$DIR" "$REVISION" <<'PYEOF'
import sys
from huggingface_hub import snapshot_download
print(snapshot_download("AITeamVN/Vietnamese_Reranker", revision=sys.argv[2], local_dir=sys.argv[1]))
PYEOF
    echo "export RERANKER_MODEL_DIR=$DIR" ;;
  check)
    "$PY" - "$DIR" <<'PYEOF'
import sys
from src.retrieval.rerankers import build_reranker
r = build_reranker({"backend": "cross_encoder", "model": sys.argv[1], "device": "cuda", "dtype": "float16",
                    "local_files_only": True, "max_length": 1024})
scores = r.score("thời gian thử việc tối đa", ["Thời gian thử việc không quá 60 ngày", "Nghỉ phép năm 12 ngày"])
print({"device": r.device, "dtype": r.dtype_name, "scores": scores})
assert scores[0] > scores[1], "relevant passage must outscore the irrelevant one"
PYEOF
    ;;
  *) echo "usage: $0 prepare|check [DIR]" >&2; exit 2 ;;
esac
