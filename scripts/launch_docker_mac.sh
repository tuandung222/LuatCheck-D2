#!/usr/bin/env bash
# ==============================================================================
# LuatCheck-D2 — One-Click Docker on macOS Launcher
# Runs on branch: fix/ui-markdown-and-search-before-refuse
# Starts:
#   1. Docker Desktop (if not already running)
#   2. Host Metal Inference Servers (:8081 Bonsai 4B & :8082 Vietnamese Reranker)
#   3. Docker Container `luatcheck-web` on http://127.0.0.1:8000
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
echo "  LuatCheck-D2 — Khởi chạy qua Docker Container trên macOS"
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

# 2. Ensure Docker Desktop is installed and running
if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Lỗi: Docker chưa được cài đặt trên máy này."
  exit 1
fi

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

if ! docker info >/dev/null 2>&1; then
  echo " ❌ Không thể kết nối với Docker Engine. Vui lòng bật Docker Desktop trước."
  exit 1
fi

STARTED_PIDS=()
cleanup() {
  echo ""
  echo "=================================================================="
  echo "-> Đang dừng Docker container luatcheck-web và tiến trình phụ trợ..."
  docker compose stop >/dev/null 2>&1 || true
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

# 3. Start Controller Model Server (:8081 bound to 0.0.0.0 for host.docker.internal)
if curl -sf -m 2 http://127.0.0.1:8081/health >/dev/null 2>&1; then
  echo "-> [OK] Host Metal Controller (Bonsai 4B) đã sẵn sàng trên cổng 8081."
else
  STALE_8081="$(lsof -nP -iTCP:8081 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$STALE_8081" ]; then
    echo "-> Đang giải phóng cổng 8081 từ tiến trình cũ không phản hồi (PID: $STALE_8081)..."
    for spid in $STALE_8081; do
      kill "$spid" >/dev/null 2>&1 || true
    done
    sleep 1
  fi
  echo "-> Đang khởi động Host Metal Controller (Bonsai 4B) trên cổng 8081..."
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

# 4. Start Vietnamese Reranker Server (:8082 bound to 0.0.0.0 for host.docker.internal)
if curl -sf -m 2 http://127.0.0.1:8082/health >/dev/null 2>&1; then
  echo "-> [OK] Host Metal Reranker (f16) đã sẵn sàng trên cổng 8082."
else
  STALE_8082="$(lsof -nP -iTCP:8082 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$STALE_8082" ]; then
    echo "-> Đang giải phóng cổng 8082 từ tiến trình cũ không phản hồi (PID: $STALE_8082)..."
    for spid in $STALE_8082; do
      kill "$spid" >/dev/null 2>&1 || true
    done
    sleep 1
  fi
  echo "-> Đang khởi động Host Metal Reranker trên cổng 8082..."
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

# 5. Stop any local non-Docker process on port 8000 before starting container
if ! docker ps --format '{{.Names}}' | grep -q '^luatcheck-web$'; then
  OLD_WEB_PID="$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$OLD_WEB_PID" ]; then
    echo "-> Đang giải phóng cổng 8000 từ tiến trình local (PID: $OLD_WEB_PID)..."
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
fi

# 6. Build & start Docker container
echo "-> Đang khởi chạy container luatcheck-web bằng Docker Compose..."
docker compose up -d --build

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
