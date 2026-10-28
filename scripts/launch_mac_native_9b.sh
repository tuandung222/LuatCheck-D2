#!/usr/bin/env bash
# ==============================================================================
# LuatCheck-D2 — One-Click macOS Native Launcher (Bonsai 9B Controller)
# Runs on branch: fix/ui-markdown-and-search-before-refuse
# Starts & Supervises:
#   1. Bonsai 9B Controller (Metal llama-server on :8084)
#   2. Vietnamese Reranker f16 (Metal llama-server on :8082, shared)
#   3. LuatCheck FastAPI + React Web UI (:8002) for 9B profiles
#   4. macOS caffeinate (prevents sleep/App Nap) + 3-second auto-heal watchdog
# ==============================================================================
set -euo pipefail

REPO_DIR="/Users/admin/Desktop/Recents/LuatCheck-D2"
TARGET_BRANCH="fix/ui-markdown-and-search-before-refuse"
PRISM_DIR="${HOME}/src/prism-llama.cpp"
LLAMA_SERVER="${PRISM_DIR}/build/bin/llama-server"
GGUF_REPO="prism-ml/Ternary-Bonsai-2-9B-gguf"
GGUF_FILE="Ternary-Bonsai-2-9B-PQ2_0.gguf"
WEB_URL="http://127.0.0.1:8002"
PIDFILE="/tmp/luatcheck_launcher_9b.pid"

cd "$REPO_DIR"

echo "=================================================================="
echo "  LuatCheck-D2 (Bonsai 9B) — Khởi chạy trực tiếp trên macOS"
echo "  Chế độ: Duy trì liên tục (Auto-Heal Watchdog + Chống Sleep)"
echo "=================================================================="

# 0. Stop any previous 9B launcher instance first
if [ -f "$PIDFILE" ]; then
  OLD_LAUNCHER_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$OLD_LAUNCHER_PID" ] && [ "$OLD_LAUNCHER_PID" != "$$" ] && kill -0 "$OLD_LAUNCHER_PID" >/dev/null 2>&1; then
    echo "-> Đang đóng phiên launcher 9B cũ (PID: $OLD_LAUNCHER_PID)..."
    kill "$OLD_LAUNCHER_PID" >/dev/null 2>&1 || true
    sleep 1
  fi
fi
echo "$$" > "$PIDFILE"

# Keep macOS awake while running
caffeinate -dimsu -w "$$" >/dev/null 2>&1 &

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

# 2. Ensure frontend bundle is built
if [ ! -f "frontend/dist/index.html" ]; then
  echo "-> Đang build giao diện Frontend..."
  npm --prefix frontend run build
fi

# Resolve 9B GGUF path (offline-first, download if not yet cached)
echo "-> Kiểm tra mô hình $GGUF_REPO ($GGUF_FILE)..."
MODEL_PATH="$(.venv-mlx/bin/python -c "
from huggingface_hub import hf_hub_download
try:
    print(hf_hub_download('$GGUF_REPO', '$GGUF_FILE', local_files_only=True))
except Exception:
    print(hf_hub_download('$GGUF_REPO', '$GGUF_FILE'))
")"

start_controller_8084() {
  if curl -sf -m 2 http://127.0.0.1:8084/health >/dev/null 2>&1; then
    return 0
  fi
  local stale
  stale="$(lsof -nP -iTCP:8084 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$stale" ]; then
    for spid in $stale; do kill "$spid" >/dev/null 2>&1 || true; done
    sleep 1
  fi
  echo "-> Đang khởi động Model Controller (Bonsai 9B Metal) trên cổng 8084..."
  nohup caffeinate -isu "$LLAMA_SERVER" \
    -m "$MODEL_PATH" \
    -ngl 99 -fa on -c 65536 --host 0.0.0.0 --port 8084 \
    --alias "$GGUF_REPO" --jinja \
    --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 \
    --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64 \
    >/tmp/luatcheck_controller_8084.log 2>&1 &
  disown || true

  echo -n "   Đang nạp mô hình 9B vào GPU Metal"
  for _ in $(seq 1 60); do
    if curl -sf -m 1 http://127.0.0.1:8084/health >/dev/null 2>&1; then
      echo " [XONG]"
      return 0
    fi
    echo -n "."
    sleep 1
  done
  echo " [CẢNH BÁO: Quá thời gian chờ cổng 8084]"
}

start_reranker_8082() {
  if curl -sf -m 2 http://127.0.0.1:8082/health >/dev/null 2>&1; then
    return 0
  fi
  local stale
  stale="$(lsof -nP -iTCP:8082 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$stale" ]; then
    for spid in $stale; do kill "$spid" >/dev/null 2>&1 || true; done
    sleep 1
  fi
  echo "-> Đang khởi động Vietnamese Reranker (Metal) trên cổng 8082..."
  nohup caffeinate -isu env LLAMA_SERVER="$LLAMA_SERVER" RERANKER_HOST="0.0.0.0" RERANKER_PORT=8082 \
    ./scripts/reranker/serve_mac.sh f16 >/tmp/luatcheck_reranker_8082.log 2>&1 &
  disown || true

  echo -n "   Đang nạp Reranker vào GPU Metal"
  for _ in $(seq 1 45); do
    if curl -sf -m 1 http://127.0.0.1:8082/health >/dev/null 2>&1; then
      echo " [XONG]"
      return 0
    fi
    echo -n "."
    sleep 1
  done
  echo " [CẢNH BÁO: Quá thời gian chờ cổng 8082]"
}

start_web_8002() {
  if curl -sf -m 2 "$WEB_URL/api/v1/health" >/dev/null 2>&1; then
    return 0
  fi
  local stale
  stale="$(lsof -nP -iTCP:8002 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$stale" ]; then
    for wpid in $stale; do kill "$wpid" >/dev/null 2>&1 || true; done
    sleep 1
  fi
  echo "-> Đang khởi động LuatCheck Web App (9B) trên $WEB_URL ..."
  nohup caffeinate -isu env \
    LUATCHECK_WEB_CONFIGS="config/profiles/demo-hcmut-9b.yaml,config/profiles/demo-labour-9b.yaml" \
    LUATCHECK_WEB_DB="data/db/web_demo_9b.sqlite3" \
    LUATCHECK_WEB_PORT=8002 \
    PYTHONPATH=. \
    .venv/bin/python -m src.api.app >/tmp/luatcheck_web_8002.txt 2>&1 &
  disown || true

  echo -n "   Đang chờ Web UI (9B) phản hồi"
  for _ in $(seq 1 45); do
    if curl -sf -m 1 "$WEB_URL/api/v1/health" >/dev/null 2>&1; then
      echo " [XONG]"
      return 0
    fi
    echo -n "."
    sleep 1
  done
  echo " [CẢNH BÁO: Quá thời gian chờ cổng 8002]"
}

# 3. Ensure all 3 services (:8084, :8082, :8002) are running and healthy
if curl -sf -m 2 http://127.0.0.1:8084/health >/dev/null 2>&1; then
  echo "-> [OK] Model Controller (Bonsai 9B) đã sẵn sàng trên cổng 8084."
else
  start_controller_8084
fi

if curl -sf -m 2 http://127.0.0.1:8082/health >/dev/null 2>&1; then
  echo "-> [OK] Vietnamese Reranker (f16) đã sẵn sàng trên cổng 8082."
else
  start_reranker_8082
fi

if curl -sf -m 2 "$WEB_URL/api/v1/health" >/dev/null 2>&1; then
  echo "-> [OK] LuatCheck Web App (9B) đã sẵn sàng trên cổng 8002."
else
  start_web_8002
fi

shutdown_user_session() {
  echo ""
  echo "=================================================================="
  echo "-> Đã đóng cửa sổ giám sát 9B. Các dịch vụ nền (8002, 8084, 8082) vẫn được giữ hoạt động."
  echo "=================================================================="
  rm -f "$PIDFILE"
  exit 0
}
trap shutdown_user_session INT TERM HUP

echo ""
echo "=================================================================="
echo "  [SẴN SÀNG] LuatCheck-D2 (Bonsai 9B - Mac Native) đang chạy tại:"
echo "  👉 $WEB_URL"
echo "  - Model Controller (9B): http://127.0.0.1:8084/health [OK]"
echo "  - Reranker (f16):        http://127.0.0.1:8082/health [OK]"
echo "  - Web App (9B UI):       http://127.0.0.1:8002/api/v1/health [OK]"
echo "  - Nhánh:                 $TARGET_BRANCH"
echo "  - Chế độ: Tự động kiểm tra & phục hồi mỗi 3 giây (Chống Sleep)"
echo "=================================================================="
open "$WEB_URL"

# 4. Continuous Watchdog Loop (checks every 3s and auto-restarts any dropped service)
while true; do
  if ! curl -sf -m 3 http://127.0.0.1:8084/health >/dev/null 2>&1; then
    echo "[$(date '+%H:%M:%S')] ⚠️ Watchdog: Cổng 8084 ngắt kết nối -> Đang tự động bật lại Model 9B..."
    start_controller_8084
  fi
  if ! curl -sf -m 3 http://127.0.0.1:8082/health >/dev/null 2>&1; then
    echo "[$(date '+%H:%M:%S')] ⚠️ Watchdog: Cổng 8082 ngắt kết nối -> Đang tự động bật lại Reranker..."
    start_reranker_8082
  fi
  if ! curl -sf -m 3 "$WEB_URL/api/v1/health" >/dev/null 2>&1; then
    echo "[$(date '+%H:%M:%S')] ⚠️ Watchdog: Cổng 8002 ngắt kết nối -> Đang tự động bật lại Web App 9B..."
    start_web_8002
  fi
  sleep 3
done
