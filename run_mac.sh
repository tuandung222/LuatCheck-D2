#!/usr/bin/env bash
# ==============================================================================
# One-Click Launch Script for macOS (Apple Silicon M1-M4 & Intel)
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================================="
echo " Starting LuatCheck - Local SLM CPU Assistant on macOS"
echo "=================================================================="

# 1. Check Python installation
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python 3 is not installed."
    echo "👉 Please install Python 3.11+ using Homebrew: 'brew install python@3.11'"
    exit 1
fi

PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Detected Python version: $PY_VERSION"

# 2. Check the default model server (Ternary Bonsai 2 2B GGUF on the PrismML llama.cpp fork)
if curl -s --connect-timeout 2 http://127.0.0.1:8081/health > /dev/null 2>&1; then
    echo "✅ Model server (prism llama.cpp) is running on http://127.0.0.1:8081"
else
    echo "⚠️ Warning: the model server is not running on http://127.0.0.1:8081."
    echo "👉 First time: 'make mlx-setup' (hf CLI) and 'make prism-setup'. Then run 'make prism-server' in another terminal."
    echo "👉 Without a model server the app reports an error; it never answers without the model."
fi

# 3. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Initializing virtual environment in ./venv..."
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    echo "📥 Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 4. Launch Streamlit Application
echo "🚀 Launching LuatCheck Web UI on http://localhost:8501..."
echo "💡 Press Ctrl+C to terminate."
echo "=================================================================="

exec streamlit run src/ui/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --browser.gatherUsageStats=false
