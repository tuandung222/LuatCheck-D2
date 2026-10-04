# Hướng Dẫn Vận Hành: Docker Compose Đa Nền Tảng (macOS, Windows, Linux)

Hệ thống **LuatCheck (Local-SLM-CPU)** đã được chuẩn hóa để có thể khởi chạy bằng **Docker Compose** trên cả **macOS (Apple Silicon M1-M4 & Intel)**, **Windows 10/11 (Docker Desktop)** và **Linux Server** với đúng 1 câu lệnh duy nhất.

---

## 1. Cơ Chế Kết Nối Thông Minh (Smart Endpoint Discovery)

Khác với Linux server có thể dùng `--net=host`, Docker Desktop trên **macOS và Windows** chạy bên trong một máy ảo (VM). 

Hệ thống đã được thiết kế cơ chế tự động thích ứng:
- **Tự động chuyển tiếp cổng**: Port `8501:8501` ánh xạ thẳng vào máy Mac/Windows.
- **Tự động quét mạng (Auto-Discovery)**: File `entrypoint.sh` tự động dò tìm Ollama tại:
  1. `http://host.docker.internal:11434` (Ollama đang chạy trên máy Mac / Windows thật).
  2. `http://ollama:11434` (Ollama chạy trong cùng mạng Docker Compose).
  3. `http://127.0.0.1:11434` (Ollama chạy trên Linux host).
- Bạn **không cần phải chỉnh sửa thủ công IP hay cấu hình YAML** khi mang dự án từ máy này sang máy khác!

---

## 2. Cách Vận Hành Bằng Docker Compose

### Cách A: Kết Nối Với Ollama Có Sẵn Trên Máy Thật (Khuyên Dùng)

*Phù hợp khi bạn đã cài Ollama trên Mac/Windows để tận dụng tối đa GPU Metal / CUDA.*

1. **Khởi chạy Ollama trên Mac hoặc Windows**:
   ```bash
   ollama pull qwen2.5:3b
   ollama pull all-minilm:latest
   ollama serve
   ```

2. **Khởi động ứng dụng bằng Docker Compose**:
   ```bash
   docker compose up -d
   ```
   *(Hoặc trên Linux cũ: `docker-compose up -d`)*

3. **Mở trình duyệt truy cập:**
   `http://localhost:8501`

---

### Cách B: Chạy Trọn Gói 100% Trong Docker (Full-Stack All-In-One)

*Dành cho trường hợp bạn hoàn toàn KHÔNG muốn cài đặt bất kỳ thứ gì lên máy thật ngoài Docker Desktop.*

Chỉ cần chạy lệnh:
```bash
docker compose --profile fullstack up -d
```
Lệnh này sẽ tự động khởi tạo 2 containers liên kết với nhau:
- `local-slm-ollama`: Container chạy dịch vụ Ollama, lưu trữ model trong Docker volume `ollama_models`.
- `local-slm-cpu`: Container chạy ứng dụng LuatCheck + Streamlit.

Để tải model vào container Ollama lần đầu tiên:
```bash
docker exec -it local-slm-ollama ollama pull qwen2.5:3b
docker exec -it local-slm-ollama ollama pull all-minilm:latest
```

---

## 3. Các Lệnh Quản Trị Hữu Ích

```bash
# Xem nhật ký hoạt động thời gian thực
docker compose logs -f

# Kiểm tra trạng thái sức khỏe
curl -s http://localhost:8501/_stcore/health

# Dừng và hạ toàn bộ container
docker compose down

# Build lại container sau khi sửa mã nguồn
docker compose build --no-cache
```
