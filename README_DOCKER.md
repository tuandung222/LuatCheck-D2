# Hướng Dẫn Vận Hành: Local SLM CPU (Docker & Desktop)

Hệ thống đã được đóng gói thành container Docker chuẩn hóa mang tên **`local-slm-cpu`**, tối ưu hóa cho môi trường thực thi **100% CPU Offline**, hoàn toàn không phụ thuộc GPU hay các Cloud API bên ngoài.

---

## 1. Kiến Trúc & Đặc Tính Kỹ Thuật

- **Tên Container**: `local-slm-cpu`
- **Mô hình SLM**: Khuyến khích sử dụng các dòng Small Language Model 4-bit lượng tử hóa nhẹ:
  - `qwen2.5:3b` (Q4_K_M ~1.9GB RAM)
  - `qwen3.5:4b` (4-bit)
- **Inference Engines hỗ trợ**:
  - **Ollama** (mặc định: `http://localhost:11434` hoặc `http://127.0.0.1:11434`)
  - **llama.cpp** (`llama-server` theo chuẩn OpenAI REST API `http://localhost:8080/v1`)
  - **Mock / Fallback**: Tự động dự phòng nếu endpoint tạm thời offline, không bao giờ crash hệ thống.
- **Embedding & Retrieval**:
  - BM25 (`rank-bm25`) + TF-IDF n-grams Cosine Similarity (`scikit-learn`), chạy 100% trên CPU.
- **Xác thực căn cứ hai tầng**: L1 Deterministic + L2 Semantic Entailment NLI.
- **Port giao diện**: `8501` (Streamlit SPA).

---

## 2. Vận Hành Trên Server Hiện Tại (Linux)

Container hiện đang chạy và phục vụ trực tiếp trên server:

```bash
# Kiểm tra trạng thái container
docker ps --filter "name=local-slm-cpu"

# Xem log thời gian thực
docker logs -f local-slm-cpu

# Kiểm tra sức khỏe HTTP
curl -s http://localhost:8501/_stcore/health
```

### Cách Khởi Động Lại Hoặc Tùy Biến

#### Cách 1: Sử dụng Docker CLI
```bash
docker run -d \
  --name local-slm-cpu \
  --net=host \
  -e MODEL_PROVIDER=ollama \
  -e MODEL_NAME=qwen2.5:3b \
  -e MODEL_ENDPOINT=http://127.0.0.1:11434 \
  -v $(pwd)/data:/app/data \
  local-slm-cpu:latest
```

#### Cách 2: Sử dụng Docker Compose
```bash
docker compose up -d
```

---

## 3. Hướng Dẫn Triển Khai Trên Desktop (MacBook Apple Silicon)

Trong tương lai khi chuyển sang chạy trên MacBook (M1/M2/M3/M4):

### Lựa chọn A: Chạy qua Docker Desktop trên Mac

1. **Khởi chạy Ollama hoặc llama.cpp trên Mac**:
   ```bash
   # Nếu dùng Ollama:
   brew install ollama
   ollama serve
   ollama pull qwen2.5:3b
   
   # Hoặc nếu dùng llama.cpp (chạy GGUF Qwen 3.5 4B 4-bit):
   brew install llama.cpp
   llama-server -m ./qwen3.5-4b-q4_k_m.gguf --port 8080
   ```

2. **Chạy Container `local-slm-cpu`**:
   - Nếu dùng Ollama:
     ```bash
     docker run -d \
       --name local-slm-cpu \
       -p 8501:8501 \
       -e MODEL_PROVIDER=ollama \
       -e MODEL_NAME=qwen2.5:3b \
       -e MODEL_ENDPOINT=http://host.docker.internal:11434 \
       -v $(pwd)/data:/app/data \
       local-slm-cpu:latest
     ```
   - Nếu dùng llama.cpp:
     ```bash
     docker run -d \
       --name local-slm-cpu \
       -p 8501:8501 \
       -e MODEL_PROVIDER=llamacpp \
       -e MODEL_NAME=qwen3.5:4b \
       -e MODEL_ENDPOINT=http://host.docker.internal:8080/v1 \
       -v $(pwd)/data:/app/data \
       local-slm-cpu:latest
     ```

### Lựa chọn B: Chạy Native trực tiếp trên MacBook (không cần Docker)

```bash
# Tạo môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt

# Khởi chạy UI
streamlit run src/ui/app.py --server.port 8501
```

---

## 4. Kiểm Thử Chất Lượng Bên Trong Container

Bộ kiểm thử gồm 452 ca kiểm nghiệm tự động đã được chạy và xác nhận 100% thành công:

```bash
docker exec local-slm-cpu pytest -q
# Kết quả: 452 passed, 13 skipped in ~34s
```
