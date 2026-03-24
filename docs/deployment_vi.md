# Hướng Dẫn Triển Khai

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-Deployment-blue?style=flat-square)](deployment.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Triển_khai-red?style=flat-square)](deployment_vi.md)

</div>

---

## Mục Lục

1. [Yêu Cầu Hệ Thống](#1-yêu-cầu-hệ-thống)
2. [Biến Môi Trường](#2-biến-môi-trường)
3. [Khởi Động Nhanh (Docker Compose)](#3-khởi-động-nhanh-docker-compose)
4. [Tham Chiếu Docker Compose](#4-tham-chiếu-docker-compose)
5. [Dockerfile Backend](#5-dockerfile-backend)
6. [Dockerfile Frontend](#6-dockerfile-frontend)
7. [Cài Đặt Thư Mục Dữ Liệu](#7-cài-đặt-thư-mục-dữ-liệu)
8. [Cài Đặt LocalAI (Tùy Chọn)](#8-cài-đặt-localai-tùy-chọn)
9. [Checklist Production](#9-checklist-production)
10. [Sự Cố Thường Gặp](#10-sự-cố-thường-gặp)

---

## 1. Yêu Cầu Hệ Thống

| Yêu cầu | Phiên bản | Ghi chú |
|---------|---------|---------|
| Docker | ≥ 24.0 | Bắt buộc |
| Docker Compose | ≥ 2.20 | Bắt buộc (cú pháp v2) |
| API key Open Claude | — | Nhà cung cấp AI chính |
| LocalAI (tùy chọn) | — | AI dự phòng, tự host |
| Dung lượng đĩa | ≥ 5 GB | Cho cache audio + models |
| RAM | ≥ 4 GB | Khuyến nghị 8 GB |

**Không cần cài Python hay Node.js** — mọi thứ chạy trong Docker container.

---

## 2. Biến Môi Trường

Tạo file `.env` ở thư mục gốc dự án:

```bash
# ── Open Claude (AI Chính) ────────────────────────────────────
# Nhiều key cách nhau dấu phẩy để round-robin
OPEN_CLAUDE_API_KEY=sk-xxx1,sk-xxx2,sk-xxx3
OPEN_CLAUDE_API_BASE=https://api.openai.com/v1   # hoặc endpoint tương thích

# ── LocalAI (AI Dự Phòng) ────────────────────────────────────
LOCAL_AI_BASE_URL=http://localai:8080             # DNS nội bộ Docker
LOCAL_AI_MODEL=llama3                             # tên model LocalAI phục vụ

# ── Backend ──────────────────────────────────────────────────
BACKEND_URL=http://backend:8000                   # Next.js proxy dùng
LOG_LEVEL=INFO

# ── Frontend ─────────────────────────────────────────────────
NEXT_PUBLIC_APP_NAME=CyberAI Platform
```

### Xoay Vòng Key

Cung cấp nhiều API key dưới dạng danh sách cách nhau dấu phẩy. Backend dùng round-robin:

```
OPEN_CLAUDE_API_KEY=key1,key2,key3
# Yêu cầu 1 → key1
# Yêu cầu 2 → key2
# Yêu cầu 3 → key3
# Yêu cầu 4 → key1 (quay lại)
```

---

## 3. Khởi Động Nhanh (Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/your-org/phobert-chatbot-project.git
cd phobert-chatbot-project

# 2. Tạo file môi trường
cp .env.example .env
# Chỉnh sửa .env — tối thiểu điền OPEN_CLAUDE_API_KEY

# 3. Tạo các thư mục dữ liệu cần thiết
mkdir -p data/sessions data/summaries/audio data/assessments \
         data/vector_store data/translations data/uploads

# 4. Build và khởi động tất cả services
docker compose up --build -d

# 5. Kiểm tra services đang chạy
docker compose ps

# 6. Xem logs
docker compose logs -f backend
docker compose logs -f frontend
```

**Truy cập:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

---

## 4. Tham Chiếu Docker Compose

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPEN_CLAUDE_API_KEY=${OPEN_CLAUDE_API_KEY}
      - OPEN_CLAUDE_API_BASE=${OPEN_CLAUDE_API_BASE}
      - LOCAL_AI_BASE_URL=${LOCAL_AI_BASE_URL}
      - LOCAL_AI_MODEL=${LOCAL_AI_MODEL}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - ./data:/data                  # dữ liệu bền vững
      - /proc:/host/proc:ro           # thống kê hệ thống host (chỉ đọc)
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend-next
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - BACKEND_URL=http://backend:8000
      - NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME:-CyberAI Platform}
    depends_on:
      - backend
    restart: unless-stopped
```

---

## 5. Dockerfile Backend

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Deps hệ thống cho tạo audio và cào web
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Tạo thư mục dữ liệu
RUN mkdir -p /data/sessions /data/summaries/audio \
    /data/assessments /data/vector_store \
    /data/translations /data/uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### Các Dependency Python Quan Trọng

```
# requirements.txt (các package chính)
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.0

chromadb>=0.4.22           # vector store
sentence-transformers       # embeddings

requests>=2.31
beautifulsoup4>=4.12
trafilatura>=1.8
newspaper3k>=0.2            # cào bài báo

edge-tts>=6.1               # Microsoft Neural TTS

duckduckgo-search>=5.0      # tìm kiếm web (ddgs)

httpx>=0.26
python-dotenv>=1.0
```

---

## 6. Dockerfile Frontend

```dockerfile
# frontend-next/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Giai đoạn production
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

### Chế Độ Development

Để hot-reload khi phát triển:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

```yaml
# docker-compose.dev.yml (override)
services:
  frontend:
    build:
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend-next:/app
      - /app/node_modules
      - /app/.next
    environment:
      - WATCHPACK_POLLING=true
```

---

## 7. Cài Đặt Thư Mục Dữ Liệu

Tất cả dữ liệu bền vững nằm dưới `./data/` trên host, được mount vào container backend tại `/data/`:

```
data/
├── iso_documents/          ← File markdown cơ sở kiến thức ISO (đi kèm repo)
│   ├── iso27001_annex_a.md
│   ├── assessment_criteria.md
│   └── ...
├── knowledge_base/         ← Kiến thức JSON có cấu trúc (đi kèm repo)
│   ├── controls.json
│   ├── iso27001.json
│   └── tcvn14423.json
├── vector_store/           ← Index ChromaDB (tự tạo khi khởi động)
│   ├── chroma.sqlite3
│   └── {uuid}/
├── sessions/               ← File chat session (tự tạo)
├── summaries/              ← Cache JSON tóm tắt bài (tự tạo)
│   └── audio/              ← File audio MP3 (tự tạo)
├── assessments/            ← File JSON đánh giá ISO (tự tạo)
├── translations/           ← Cache dịch tiêu đề (tự tạo)
├── articles_history.json   ← Lịch sử bài báo (tự tạo)
└── uploads/                ← Placeholder upload file
```

### Sao Lưu Thư Mục Quan Trọng

```bash
# Sao lưu tất cả dữ liệu người dùng
tar czf backup-$(date +%Y%m%d).tar.gz data/

# Khôi phục
tar xzf backup-20250324.tar.gz
```

---

## 8. Cài Đặt LocalAI (Tùy Chọn)

LocalAI là **AI dự phòng** khi Open Claude không khả dụng. Tự host và phục vụ model GGUF/GGML với API tương thích OpenAI.

### Thêm vào docker-compose.yml

```yaml
services:
  localai:
    image: localai/localai:latest-aio-cpu
    ports:
      - "8080:8080"
    volumes:
      - ./localai-models:/models
    environment:
      - MODELS_PATH=/models
    restart: unless-stopped
```

### Tải Model

```bash
# Ví dụ: LLaMA-3 8B Q4
mkdir -p localai-models
cd localai-models
wget https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf
```

### Tạo Config Model

```yaml
# localai-models/llama3.yaml
name: llama3
parameters:
  model: Meta-Llama-3-8B-Instruct-Q4_K_M.gguf
  context_size: 8192
template:
  chat: llama3-instruct
```

### Cấu Hình Backend

```bash
LOCAL_AI_BASE_URL=http://localai:8080
LOCAL_AI_MODEL=llama3
```

---

## 9. Checklist Production

### Bảo Mật

- [ ] Đặt `OPEN_CLAUDE_API_KEY` từ environment secrets (không commit vào git)
- [ ] Cấu hình CORS trong `backend/main.py` để giới hạn origins:
  ```python
  app.add_middleware(CORSMiddleware, allow_origins=["https://yourdomain.com"])
  ```
- [ ] Thêm HTTPS qua reverse proxy (Nginx/Caddy/Traefik)
- [ ] Đặt `LOG_LEVEL=WARNING` trong production
- [ ] Giới hạn mount `/proc` ở chỉ đọc (đã cấu hình trong compose)

### Reverse Proxy (ví dụ Nginx)

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_read_timeout 120s;        # dài cho tạo AI
        proxy_set_header Host $host;
    }
}
```

### Hiệu Suất

- [ ] Đặt `--workers 1` cho Uvicorn (ChromaDB không an toàn với fork)
- [ ] Pre-warm ChromaDB khi khởi động (tự xử lý bởi `ensure_indexed()`)
- [ ] Theo dõi dung lượng đĩa — file audio tích lũy (~1.5–2 MB mỗi bài)

### Giám Sát

```bash
# Health check
curl http://localhost:8000/

# Thống kê hệ thống
curl http://localhost:8000/api/system/stats

# Thống kê cache
curl http://localhost:8000/api/system/cache-stats
```

---

## 10. Sự Cố Thường Gặp

### Backend không khởi động — thiếu API key

```
ValueError: OPEN_CLAUDE_API_KEY is not set
```

**Cách sửa:** Đặt biến môi trường trong `.env` hoặc phần environment Docker Compose.

### ChromaDB index không tìm thấy / kết quả rỗng

```bash
# Re-index qua API
curl -X POST http://localhost:8000/api/iso27001/reindex
```

### File audio không phát

Kiểm tra thư mục audio có thể truy cập và MP3 đã được tạo:

```bash
docker exec <backend> ls /data/summaries/audio/
curl http://localhost:8000/api/news/audio/<hash>.mp3 -I
```

### Thống kê `/host/proc` hiển thị số 0

Volume mount `/proc:/host/proc:ro` bị thiếu hoặc host không hỗ trợ.

```bash
# Xác minh mount
docker exec <backend> ls /host/proc/stat
```

### Edge-TTS timeout / lỗi kết nối

Edge-TTS cần truy cập internet tới server TTS của Microsoft. Kiểm tra:

```bash
docker exec <backend> curl -I https://speech.microsoft.com
```

### DuckDuckGo search trả về rỗng

DuckDuckGo giới hạn tốc độ các scraper tích cực. Service retry 2 lần với delay 1s. Nếu vẫn xảy ra:

```bash
# Kiểm tra từ trong container
docker exec <backend> python3 -c "
from duckduckgo_search import DDGS
with DDGS() as d:
    print(list(d.text('test', max_results=1)))
"
```

### Frontend không thể kết nối backend

Kiểm tra biến môi trường `BACKEND_URL` được đặt là tên DNS nội bộ Docker:

```bash
# Phải là http://backend:8000 (không phải localhost!)
docker exec <frontend> env | grep BACKEND_URL
```
