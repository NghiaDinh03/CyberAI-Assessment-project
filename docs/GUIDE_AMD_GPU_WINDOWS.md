# Hướng Dẫn Tối Ưu Hóa & Sử Dụng GPU AMD Radeon Trên Windows (Lưu Trữ Kỹ Thuật)

Tài liệu này lưu trữ toàn bộ các bước cấu hình để kích hoạt card đồ họa tích hợp **AMD Radeon 860M (iGPU / APU)** hoặc card rời AMD với Ollama trên Windows khi cần kích hoạt lại trong tương lai.

---

## 1. Bản Chất Phần Cứng & Cơ Chế Hoạt Động

* **Phần cứng máy tính**: AMD Ryzen AI 7 350 (8 nhân vật lý / 16 luồng logic) + AMD Radeon 860M Graphics.
* **Mặc định**: BIOS của máy cấp phát cố định `512MB Dedicated VRAM` cho card đồ họa tích hợp.
* **Cơ chế Ollama**:
  * Ollama Windows hỗ trợ GPU AMD thông qua Vulkan và ROCm.
  * Mặc định Ollama tự động bỏ qua (drop) card tích hợp nếu không có cờ `OLLAMA_IGPU_ENABLE=1`.

---

## 2. Các Bước Kích Hoạt Lại GPU Windows (Khi Cần)

### Bước 1: Mở rộng VRAM trong BIOS (Khuyên Dùng)
Để GPU nhận trọn vẹn mô hình mà không tràn sang RAM chính:
1. Mở PowerShell (Admin) và chạy lệnh để vào thẳng BIOS:
   ```powershell
   shutdown /r /fw /t 0
   ```
2. Trong BIOS: Chọn tab **Configuration** (hoặc **Advanced**) $\rightarrow$ **UMA Frame Buffer Size** $\rightarrow$ Đổi từ `512MB` lên `4GB` hoặc `8GB` $\rightarrow$ Nhấn **F10** (Save & Exit).

### Bước 2: Cài đặt Biến Môi Trường cho Ollama Windows
Mở PowerShell và chạy các lệnh sau:
```powershell
[System.Environment]::SetEnvironmentVariable('OLLAMA_IGPU_ENABLE', '1', 'User')
[System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'User')
```

### Bước 3: Chuyển cấu hình kết nối trong dự án
Trong file `.env`:
```ini
OLLAMA_URL=http://host.docker.internal:11434
```
Trong `docker-compose.yml`:
- Tắt service `ollama` (`docker compose stop ollama`).
- Khởi động lại backend (`docker compose restart backend`).

---

## 3. Chế Độ Chạy Mặc Định Hiện Tại (100% Docker CPU - An Toàn & Tự Động)

Hệ thống đang chạy chế độ chuẩn hóa:
- **100% Tự Động Hóa trong Docker**: Không phụ thuộc bất kỳ phần mềm nào cài trên Windows.
- **Tối ưu 10 Luồng CPU (Threads)**: Tốc độ xử lý nhanh, CPU tải ~60%, máy mát và an toàn 100%.
- **Live SSE Streaming**: Truyền dữ liệu từng từ theo thời gian thực kèm tín hiệu Heartbeat mỗi 15 giây, chống timeout vĩnh viễn.
