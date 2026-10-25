#!/bin/bash
set -e

UI_MODE="${LUATCHECK_UI_MODE:-web}"
WEB_PORT="${LUATCHECK_WEB_PORT:-8000}"

echo "=========================================================="
echo " Starting LuatCheck-D2 Container (${UI_MODE})"
echo "=========================================================="

mkdir -p /app/data/db /app/data/outbox

# Auto-discover Controller LLM Server (port 8081 on macOS host or local network)
if [ -z "${LUATCHECK_CONTROLLER_ENDPOINT:-}" ]; then
    for candidate in "http://host.docker.internal:8081" "http://127.0.0.1:8081" "http://172.17.0.1:8081"; do
        if curl -sf --connect-timeout 1 "$candidate/health" > /dev/null 2>&1 || curl -sf --connect-timeout 1 "$candidate/v1/models" > /dev/null 2>&1; then
            export LUATCHECK_CONTROLLER_ENDPOINT="${candidate}/v1"
            echo "[LuatCheck-D2] Connected to Controller LLM at: ${LUATCHECK_CONTROLLER_ENDPOINT}"
            break
        fi
    done
fi

# Auto-discover Reranker Server (port 8082 on macOS host or local network)
if [ -z "${LUATCHECK_RERANKER_BASE_URL:-}" ]; then
    for candidate in "http://host.docker.internal:8082" "http://127.0.0.1:8082" "http://172.17.0.1:8082"; do
        if curl -sf --connect-timeout 1 "$candidate/health" > /dev/null 2>&1; then
            export LUATCHECK_RERANKER_BASE_URL="${candidate}"
            echo "[LuatCheck-D2] Connected to Reranker Server at: ${LUATCHECK_RERANKER_BASE_URL}"
            break
        fi
    done
fi

echo " Web Port:      ${WEB_PORT}"
echo " Configs:       ${LUATCHECK_WEB_CONFIGS:-default}"
echo " Controller:    ${LUATCHECK_CONTROLLER_ENDPOINT:-from profile config}"
echo " Reranker:      ${LUATCHECK_RERANKER_BASE_URL:-from profile config}"
echo "=========================================================="

if [ "${UI_MODE}" = "streamlit" ]; then
    exec streamlit run src/ui/app.py \
        --server.port="${STREAMLIT_SERVER_PORT:-8501}" \
        --server.address="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}" \
        --server.headless=true \
        --browser.gatherUsageStats=false
else
    export LUATCHECK_WEB_ALLOW_CONTAINER_BIND=1
    export LUATCHECK_WEB_HOST="${LUATCHECK_WEB_HOST:-0.0.0.0}"
    export LUATCHECK_WEB_PORT="${WEB_PORT}"
    exec python -m src.api.app
fi
