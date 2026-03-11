# Hướng dẫn Cài đặt & Triển khai (Deployment Guide)

PhoBERT AI Platform được đóng gói toàn bộ với kiến trúc Microservices trong Docker. Mặc dù sở hữu tới 6 hệ thống mô hình AI và phần cứng khác nhau, việc cài đặt lại cực kỳ dễ dàng. Bạn không cần thiết lập Python hay môi trường ảo trên Host, chỉ cần Docker!

## 1. Yêu cầu Hệ thống (System Requirements)
- **Môi trường Server/Máy tính:** Ưu tiên Linux (Ubuntu 22.04+) hoặc Windows WSL2.
- **Phần mềm:** Docker và Docker Compose.
- **Phần cứng Tối thiểu:** 16GB RAM + Ổ cứng 30GB trống (để tải GGUF Models).
- **Phần cứng Đề nghị:** 32GB RAM + GPU (Nvidia/CUDA) tuỳ chọn để chạy LocalAI nhanh hơn.

## 2. Bước 1: Chuẩn bị Source Code và `.env`
Clone dự án từ GitHub:
```bash
git clone https://github.com/NghiaDinh03/phobert-chatbot-project.git
cd phobert-chatbot-project
```

Tiến hành thiết lập file biến số môi trường:
```bash
cp .env.example .env
```

Mở file `.env` lên, bạn sẽ thấy 2 trường nhập mảng API (ngăn cách bằng dấu phẩy `,`) là `GEMINI_API_KEYS` và `OPENROUTER_API_KEYS`. Hãy nhập càng nhiều key càng tốt, hệ thống Tóm tắt Tin tức sẽ luân phiên (Round-Robin) đổi API nhằm không bao giờ đứt đoạn do hết Quota hay giới hạn Rate Limit. Nếu có key bị lỗi, nó sẽ khóa lại trong 60s và chuyển tự động sang key khác.

## 3. Bước 2: Build Hệ Tự tự động bằng Docker
Chạy một lệnh duy nhất:
```bash
docker-compose up --build -d
```
Lệnh này sẽ tự động tải các tệp tin `Llama-3.1` và `SecurityLLM` dưới chuẩn GGUF vào ổ, tự động tải Image, biên dịch Frontend, và nối chúng lại vào chung network lưới `phobert-network`. Tuỳ cấu hình mạng, quá trình kéo Model và Build image có thể mất 15-30 phút lần đầu!

## 4. Kiểm tra sức khỏe (Health Check)
Thống kê Log của Backend:
```bash
docker logs phobert-backend -f
```

Giao diện hệ thống hiện thân tại cổng `:3000`. Bạn mở trình duyệt lên truy cập: `http://localhost:3000`.

## 5. Cấu trúc Volume Dữ Liệu Persistent (An Toàn Dữ Liệu)
Mọi lịch sử AI sinh ra, thư mục ghi âm `audio/`, và thư viện tải model HuggingFace `transformers` đều được lưu lại an toàn ở ổ vật lý của bạn bên trong thư mục `/data`:
- Khi update lại Docker (chạy `down` / `up` liên tục), cache tải Model VinAI 135M và Vector DB (ChromaDB) không bao giờ bị mất, tiết kiệm tối đa RAM và Băng thông internet ngoài.
- Tin tức quá 7 ngày được tự dọn rác bởi CRON Job tích hợp trong Python để tránh tràn ổ C:/.
