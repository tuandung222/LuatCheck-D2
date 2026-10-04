# =========================================================================
# Local SLM CPU - Containerfile
# Designed for lightweight, 100% offline CPU execution on Linux & Apple Silicon
# =========================================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    MODEL_PROVIDER=ollama \
    MODEL_NAME=qwen2.5:3b \
    MODEL_ENDPOINT=http://127.0.0.1:11434

WORKDIR /app

# Install lightweight system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-optimized PyTorch first to avoid massive CUDA overhead
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code, evaluation suite, tests, and configurations
COPY src/ /app/src/
COPY evaluation/ /app/evaluation/
COPY redteam/ /app/redteam/
COPY config/ /app/config/
COPY data/ /app/data/
COPY tests/ /app/tests/
COPY conftest.py pytest.ini /app/
COPY entrypoint.sh /app/entrypoint.sh

# Ensure script is executable and data subdirectories exist
RUN chmod +x /app/entrypoint.sh && \
    mkdir -p /app/data/db /app/data/outbox

EXPOSE 8501

ENTRYPOINT ["/app/entrypoint.sh"]
