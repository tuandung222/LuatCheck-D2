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

# Optional health check for local SLM server
ENDPOINT="${MODEL_ENDPOINT:-http://127.0.0.1:11434}"
echo "[Local SLM CPU] Probing model endpoint at $ENDPOINT..."
if curl -s --connect-timeout 2 "$ENDPOINT/api/tags" > /dev/null 2>&1; then
    echo "[Local SLM CPU] Connected successfully to Ollama endpoint: $ENDPOINT"
elif curl -s --connect-timeout 2 "$ENDPOINT/v1/models" > /dev/null 2>&1; then
    echo "[Local SLM CPU] Connected successfully to llama.cpp/OpenAI endpoint: $ENDPOINT"
else
    echo "[Local SLM CPU] Warning: Endpoint $ENDPOINT not responding immediately."
    echo "[Local SLM CPU] Fallback mock inference and rule-based verification will be available if offline."
fi

# Run Streamlit application
exec streamlit run src/ui/app.py \
    --server.port="${STREAMLIT_SERVER_PORT:-8501}" \
    --server.address="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}" \
    --server.headless=true \
    --browser.gatherUsageStats=false
