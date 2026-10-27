# =========================================================================
# LuatCheck-D2 Containerfile (macOS Apple Silicon / Intel & Linux)
# Stage 1: Build React + Vite Frontend bundle (`frontend/dist`)
# Stage 2: Python 3.12 Runtime serving FastAPI + React UI + Hybrid Index
# =========================================================================
FROM node:22-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# =========================================================================
# Stage 2: Application Runtime
# =========================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    LUATCHECK_UI_MODE=web \
    LUATCHECK_WEB_HOST=0.0.0.0 \
    LUATCHECK_WEB_PORT=8000 \
    LUATCHECK_WEB_ALLOW_CONTAINER_BIND=1 \
    LUATCHECK_WEB_CONFIGS=config/profiles/demo-hcmut-gemma2-768d.yaml,config/profiles/demo-labour-gemma2-768d.yaml \
    LUATCHECK_WEB_DB=data/db/web_demo_gemma2_768d.sqlite3

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install CPU PyTorch + requirements + sentence-transformers for EmbeddingGemma-2 768-d
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "sentence-transformers>=4.1.0" "qdrant-client>=1.14.0"

# Copy built React UI from Stage 1
COPY --from=frontend-build /frontend/dist /app/frontend/dist

# Copy application source, configs, corpora, and pre-built indexes
COPY src/ /app/src/
COPY config/ /app/config/
COPY data/ /app/data/
COPY tests/ /app/tests/
COPY conftest.py pytest.ini /app/
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh && \
    mkdir -p /app/data/db /app/data/outbox

EXPOSE 8000 8501

ENTRYPOINT ["/app/entrypoint.sh"]
