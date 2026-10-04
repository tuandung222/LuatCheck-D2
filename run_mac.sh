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

# 2. Check Ollama status
if curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running locally on http://localhost:11434"
else
    echo "⚠️ Warning: Ollama does not appear to be running on http://localhost:11434."
    echo "👉 If you have Ollama installed, please run 'ollama serve' in another terminal."
    echo "👉 Offline mock mode will be used if Ollama is unavailable."
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
