#!/bin/bash
set -e

echo "=========================================================="
echo " Starting Local SLM CPU Container: local-slm-cpu"
echo "=========================================================="
echo " Model Provider: ${MODEL_PROVIDER:-ollama}"
echo " Model Name:     ${MODEL_NAME:-qwen2.5:3b}"
echo " Model Endpoint: ${MODEL_ENDPOINT:-http://127.0.0.1:11434}"
echo " Streamlit Port: ${STREAMLIT_SERVER_PORT:-8501}"
echo " Execution Mode: 100% Local CPU"
echo "=========================================================="

# Ensure persistent directories exist
mkdir -p /app/data/db /app/data/outbox

# Intelligent multi-platform endpoint discovery (Mac, Windows, Linux, and Docker Compose networks)
TARGET_ENDPOINT="${MODEL_ENDPOINT}"

if [ -z "$TARGET_ENDPOINT" ] || ! curl -s --connect-timeout 1 "$TARGET_ENDPOINT/api/tags" > /dev/null 2>&1; then
    echo "[Local SLM CPU] Searching for active model endpoints across platforms..."
    for candidate in "$MODEL_ENDPOINT" "http://host.docker.internal:11434" "http://ollama:11434" "http://127.0.0.1:11434" "http://localhost:11434" "http://172.17.0.1:11434"; do
        if [ -n "$candidate" ] && curl -s --connect-timeout 1 "$candidate/api/tags" > /dev/null 2>&1; then
            TARGET_ENDPOINT="$candidate"
            echo "[Local SLM CPU] ✅ Auto-discovered active Ollama endpoint at: $TARGET_ENDPOINT"
            break
        elif [ -n "$candidate" ] && curl -s --connect-timeout 1 "$candidate/v1/models" > /dev/null 2>&1; then
            TARGET_ENDPOINT="$candidate"
            echo "[Local SLM CPU] ✅ Auto-discovered active llama.cpp/OpenAI endpoint at: $TARGET_ENDPOINT"
            break
        fi
    done
fi

if [ -n "$TARGET_ENDPOINT" ]; then
    export MODEL_ENDPOINT="$TARGET_ENDPOINT"
    echo "[Local SLM CPU] Active model endpoint set to: $MODEL_ENDPOINT"
else
    export MODEL_ENDPOINT="${MODEL_ENDPOINT:-http://127.0.0.1:11434}"
    echo "[Local SLM CPU] Warning: No active endpoint detected. Using default $MODEL_ENDPOINT (offline fallback ready)."
fi

# Run Streamlit application
exec streamlit run src/ui/app.py \
    --server.port="${STREAMLIT_SERVER_PORT:-8501}" \
    --server.address="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}" \
    --server.headless=true \
    --browser.gatherUsageStats=false
