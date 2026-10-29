#!/usr/bin/env bash
# ==============================================================================
# LuatCheck-D2 — One-Click Docker on macOS Launcher
# Runs on branch: fix/ui-markdown-and-search-before-refuse
# Starts:
#   1. Docker Desktop (if not already running)
#   2. Host Metal Inference Servers (:8081 Bonsai 4B & :8082 Vietnamese Reranker)
#   3. Docker Container `luatcheck-web` on http://127.0.0.1:8000
# Includes an automatic health watchdog so :8081 and :8082 stay online.
# ==============================================================================
set -euo pipefail

REPO_DIR="/Users/admin/Desktop/Recents/LuatCheck-D2"
TARGET_BRANCH="fix/ui-markdown-and-search-before-refuse"
PRISM_DIR="${HOME}/src/prism-llama.cpp"
LLAMA_SERVER="${PRISM_DIR}/build/bin/llama-server"
GGUF_REPO="prism-ml/Ternary-Bonsai-2-4B-gguf"
GGUF_FILE="Ternary-Bonsai-2-4B-PQ2_0.gguf"
WEB_URL="http://127.0.0.1:8000"
PIDFILE="/tmp/luatcheck_launcher.pid"

cd "$REPO_DIR"

echo "=================================================================="
echo "  LuatCheck-D2 — Khởi chạy qua Docker Container trên macOS"
echo "=================================================================="

# 0. Stop any previous launcher instance first
if [ -f "$PIDFILE" ]; then
  OLD_LAUNCHER_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$OLD_LAUNCHER_PID" ] && [ "$OLD_LAUNCHER_PID" != "$$" ] && kill -0 "$OLD_LAUNCHER_PID" >/dev/null 2>&1; then
    echo "-> Đang đóng phiên launcher cũ (PID: $OLD_LAUNCHER_PID)..."
    kill "$OLD_LAUNCHER_PID" >/dev/null 2>&1 || true
    sleep 1
  fi
fi
echo "$$" > "$PIDFILE"

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

# 2. Ensure Docker Desktop is running
if ! docker info >/dev/null 2>&1; then
  echo "-> Đang bật Docker Desktop..."
  open -a Docker
  echo -n "   Đang chờ Docker Engine khởi động"
  for _ in $(seq 1 90); do
    if docker info >/dev/null 2>&1; then
      echo " [XONG]"
      break
    fi
    echo -n "."
    sleep 1
  done
fi

MODEL_PATH="$(.venv-mlx/bin/python -c "
from huggingface_hub import hf_hub_download
try:
    print(hf_hub_download('$GGUF_REPO', '$GGUF_FILE', local_files_only=True))
except Exception:
    print(hf_hub_download('$GGUF_REPO', '$GGUF_FILE'))
")"

start_controller_8081() {
  if curl -sf -m 2 http://127.0.0.1:8081/health >/dev/null 2>&1; then
    return 0
  fi
  local stale
  stale="$(lsof -nP -iTCP:8081 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$stale" ]; then
    for spid in $stale; do kill "$spid" >/dev/null 2>&1 || true; done
    sleep 1
  fi
  echo "-> Đang khởi động Host Metal Controller (Bonsai 4B) trên cổng 8081..."
  nohup "$LLAMA_SERVER" \
    -m "$MODEL_PATH" \
    -ngl 99 -fa on -c 65536 --host 0.0.0.0 --port 8081 \
    --alias "$GGUF_REPO" --jinja \
    --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 \
    --presence-penalty 1.5 --repeat-penalty 1.0 --repeat-last-n 64 \
    >/tmp/luatcheck_controller_8081.log 2>&1 &
  disown || true

  echo -n "   Đang nạp mô hình 4B vào GPU Metal"
  for _ in $(seq 1 60); do
    if curl -sf -m 1 http://127.0.0.1:8081/health >/dev/null 2>&1; then
      echo " [XONG]"
      return 0
    fi
    echo -n "."
    sleep 1
  done
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
  echo "-> Đang khởi động Host Metal Reranker trên cổng 8082..."
  nohup env LLAMA_SERVER="$LLAMA_SERVER" RERANKER_HOST="0.0.0.0" RERANKER_PORT=8082 \
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
}

# 3. Ensure Controller (:8081) and Reranker (:8082) are running
if curl -sf -m 2 http://127.0.0.1:8081/health >/dev/null 2>&1; then
  echo "-> [OK] Host Metal Controller (Bonsai 4B) đã sẵn sàng trên cổng 8081."
else
  start_controller_8081
fi

if curl -sf -m 2 http://127.0.0.1:8082/health >/dev/null 2>&1; then
  echo "-> [OK] Host Metal Reranker (f16) đã sẵn sàng trên cổng 8082."
else
  start_reranker_8082
fi

# 4. Stop any local non-Docker process on port 8000 before starting container
touch /tmp/luatcheck_docker_starting
if ! docker ps --format '{{.Names}}' | grep -q '^luatcheck-web$'; then
  OLD_WEB_PID="$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$OLD_WEB_PID" ]; then
    echo "-> Đang giải phóng cổng 8000 từ tiến trình local (PID: $OLD_WEB_PID)..."
    for wpid in $OLD_WEB_PID; do kill "$wpid" >/dev/null 2>&1 || true; done
    sleep 1
    for wpid in $OLD_WEB_PID; do
      if kill -0 "$wpid" >/dev/null 2>&1; then kill -9 "$wpid" >/dev/null 2>&1 || true; fi
    done
  fi
fi

# 5. Build & start Docker container
echo "-> Đang khởi chạy container luatcheck-web bằng Docker Compose..."
docker compose up -d --build
rm -f /tmp/luatcheck_docker_starting

shutdown_docker_session() {
  echo ""
  echo "=================================================================="
  echo "-> Đang dừng Docker container luatcheck-web..."
  docker compose stop >/dev/null 2>&1 || true
  rm -f "$PIDFILE"
  echo "-> Đã dừng container."
  echo "=================================================================="
  exit 0
}
trap shutdown_docker_session INT TERM HUP

echo -n "   Đang chờ Container Web UI phản hồi tại $WEB_URL"
for _ in $(seq 1 60); do
  if curl -sf -m 1 "$WEB_URL/api/v1/health" >/dev/null 2>&1; then
    echo " [XONG]"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo "=================================================================="
echo "  [SẴN SÀNG] LuatCheck-D2 (Docker Container) đang chạy tại:"
echo "  👉 $WEB_URL"
echo "  Nhánh: $TARGET_BRANCH"
echo "  (Nhấn Ctrl+C hoặc đóng cửa sổ này để dừng Docker container)"
echo "=================================================================="
open "$WEB_URL"

docker compose logs -f
