#!/usr/bin/env bash
# ==============================================================================
# LuatCheck-D2 — One-Click macOS Native Launcher
# Runs on branch: fix/ui-markdown-and-search-before-refuse
# Starts:
#   1. Bonsai 4B Controller (Metal llama-server on :8081)
#   2. Vietnamese Reranker f16 (Metal llama-server on :8082)
#   3. LuatCheck FastAPI + React Web UI (:8000) with Weighted RRF 768-d
# Automatically opens http://127.0.0.1:8000 in the default browser.
# ==============================================================================
set -euo pipefail

REPO_DIR="/Users/admin/Desktop/Recents/LuatCheck-D2"
TARGET_BRANCH="fix/ui-markdown-and-search-before-refuse"
PRISM_DIR="${HOME}/src/prism-llama.cpp"
LLAMA_SERVER="${PRISM_DIR}/build/bin/llama-server"
GGUF_REPO="prism-ml/Ternary-Bonsai-2-4B-gguf"
GGUF_FILE="Ternary-Bonsai-2-4B-PQ2_0.gguf"
WEB_URL="http://127.0.0.1:8000"

cd "$REPO_DIR"

echo "=================================================================="
echo "  LuatCheck-D2 — Khởi chạy trực tiếp trên macOS (Native Metal)"
echo "=================================================================="

# 1. Ensure target branch
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$CURRENT_BRANCH" != "$TARGET_BRANCH" ]; then
  echo "-> Chuyển sang nhánh: $TARGET_BRANCH"
  if ! git checkout "$TARGET_BRANCH"; then
    echo "⚠️ [CẢNH BÁO] Không thể chuyển sang nhánh $TARGET_BRANCH (có thể do tệp chưa commit)."
    echo "   Vẫn tiếp tục chạy trên nhánh hiện tại: $CURRENT_BRANCH"
  fi
else
  echo "-> Đang ở nhánh: $TARGET_BRANCH ($(git rev-parse --short HEAD))"
fi

# 2. If Docker container is occupying port 8000, stop it cleanly
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -q '^luatcheck-web$'; then
    echo "-> Đang dừng container Docker luatcheck-web để giải phóng cổng 8000..."
    docker stop luatcheck-web >/dev/null 2>&1 || true
  fi
fi

# 3. Ensure frontend bundle is built
if [ ! -f "frontend/dist/index.html" ]; then
  echo "-> Đang build giao diện Frontend..."
  npm --prefix frontend run build
fi

STARTED_PIDS=()
cleanup() {
  echo ""
  echo "=================================================================="
  echo "-> Đang dừng các tiến trình LuatCheck do phiên này khởi tạo..."
  if [ ${#STARTED_PIDS[@]} -gt 0 ]; then
    for pid in "${STARTED_PIDS[@]}"; do
      if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
        kill "$pid" >/dev/null 2>&1 || true
      fi
    done
  fi
  echo "-> Đã dừng hoàn tất."
  echo "=================================================================="
}
trap cleanup EXIT INT TERM

# 4. Start Controller Model Server (:8081) if not already running
if curl -sf -m 2 http://127.0.0.1:8081/health >/dev/null 2>&1; then
  echo "-> [OK] Model Controller (Bonsai 4B) đã sẵn sàng trên cổng 8081."
else
  STALE_8081="$(lsof -nP -iTCP:8081 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$STALE_8081" ]; then
    echo "-> Đang giải phóng cổng 8081 từ tiến trình cũ không phản hồi (PID: $STALE_8081)..."
    for spid in $STALE_8081; do
      kill "$spid" >/dev/null 2>&1 || true
    done
    sleep 1
  fi
  echo "-> Đang khởi động Model Controller (Bonsai 4B Metal) trên cổng 8081..."
  MODEL_PATH="$(.venv-mlx/bin/python -c "
from huggingface_hub import hf_hub_download
try:
    print(hf_hub_download('$GGUF_REPO', '$GGUF_FILE', local_files_only=True))
except Exception:
    print(hf_hub_download('$GGUF_REPO', '$GGUF_FILE'))
")"
  "$LLAMA_SERVER" \
    -m "$MODEL_PATH" \
    -ngl 99 -fa on -c 65536 --host 0.0.0.0 --port 8081 \
    --alias "$GGUF_REPO,prism-ml/Ternary-Bonsai-2-2B-gguf" --jinja \
    --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 \
    --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64 \
    >/tmp/luatcheck_controller_8081.log 2>&1 &
  STARTED_PIDS+=("$!")

  echo -n "   Đang nạp mô hình 4B vào GPU Metal"
  for _ in $(seq 1 60); do
    if curl -sf -m 1 http://127.0.0.1:8081/health >/dev/null 2>&1; then
      echo " [XONG]"
      break
    fi
    echo -n "."
    sleep 1
  done
fi

# 5. Start Vietnamese Reranker Server (:8082) if not already running
if curl -sf -m 2 http://127.0.0.1:8082/health >/dev/null 2>&1; then
  echo "-> [OK] Vietnamese Reranker (f16) đã sẵn sàng trên cổng 8082."
else
  STALE_8082="$(lsof -nP -iTCP:8082 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$STALE_8082" ]; then
    echo "-> Đang giải phóng cổng 8082 từ tiến trình cũ không phản hồi (PID: $STALE_8082)..."
    for spid in $STALE_8082; do
      kill "$spid" >/dev/null 2>&1 || true
    done
    sleep 1
  fi
  echo "-> Đang khởi động Vietnamese Reranker (Metal) trên cổng 8082..."
  LLAMA_SERVER="$LLAMA_SERVER" RERANKER_HOST="0.0.0.0" RERANKER_PORT=8082 \
    ./scripts/reranker/serve_mac.sh f16 >/tmp/luatcheck_reranker_8082.log 2>&1 &
  STARTED_PIDS+=("$!")

  echo -n "   Đang nạp Reranker vào GPU Metal"
  for _ in $(seq 1 45); do
    if curl -sf -m 1 http://127.0.0.1:8082/health >/dev/null 2>&1; then
      echo " [XONG]"
      break
    fi
    echo -n "."
    sleep 1
  done
fi

# 6. Free port 8000 if an old uvicorn process is still hanging
OLD_WEB_PID="$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t 2>/dev/null || true)"
if [ -n "$OLD_WEB_PID" ]; then
  echo "-> Đang khởi động lại Web Server cũ trên cổng 8000 (PID: $OLD_WEB_PID)..."
  for wpid in $OLD_WEB_PID; do
    kill "$wpid" >/dev/null 2>&1 || true
  done
  sleep 1
  for wpid in $OLD_WEB_PID; do
    if kill -0 "$wpid" >/dev/null 2>&1; then
      kill -9 "$wpid" >/dev/null 2>&1 || true
    fi
  done
fi

# 7. Start FastAPI + React Web UI (:8000)
echo "-> Đang khởi động LuatCheck Web App trên $WEB_URL ..."
LUATCHECK_WEB_CONFIGS="config/profiles/demo-hcmut-gemma2-768d.yaml,config/profiles/demo-labour-gemma2-768d.yaml" \
LUATCHECK_WEB_DB="data/db/web_demo_gemma2_768d.sqlite3" \
LUATCHECK_WEB_PORT=8000 \
PYTHONPATH=. \
.venv/bin/python -m src.api.app >/tmp/luatcheck_web_8000.txt 2>&1 &
WEB_PID="$!"
STARTED_PIDS+=("$WEB_PID")

echo -n "   Đang chờ Web UI phản hồi"
for _ in $(seq 1 45); do
  if curl -sf -m 1 "$WEB_URL/api/v1/health" >/dev/null 2>&1; then
    echo " [XONG]"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo "=================================================================="
echo "  [SẴN SÀNG] LuatCheck-D2 (Mac Native) đang chạy tại:"
echo "  👉 $WEB_URL"
echo "  Nhánh: $TARGET_BRANCH"
echo "  (Nhấn Ctrl+C hoặc đóng cửa sổ này để tắt toàn bộ server)"
echo "=================================================================="
open "$WEB_URL"

wait "$WEB_PID"
