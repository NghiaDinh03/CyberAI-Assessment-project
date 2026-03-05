# PhoBERT AI Platform — Hệ thống Đánh giá An toàn Thông tin

Nền tảng AI on-premise cho **đánh giá tuân thủ ISO 27001:2022**, **TCVN 11930:2017** và **pháp luật ATTT Việt Nam**.
Tích hợp Multi-Model RAG (Retrieval-Augmented Generation) với **PhoBERT**, **Llama 3.1 8B** và **SecurityLLM 7B**, toàn bộ chạy cục bộ bằng Docker — không gửi dữ liệu ra bên ngoài.

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| **AI Chatbot** | Trò chuyện với AI bằng tiếng Việt, hỏi đáp về ATTT, ISO 27001 |
| **Form ISO 27001** | Nhập thông tin hệ thống của tổ chức, AI tự động phân tích compliance |
| **Analytics Dashboard** | Xem tài nguyên hệ thống (CPU, RAM, Disk), trạng thái dịch vụ, lịch sử đánh giá |
| **ChromaDB Monitor** | Giám sát Vector Database, xem danh sách tài liệu đã nạp, test tìm kiếm trực tiếp |
| **Multi-Model RAG** | SecurityLLM phân tích → Llama 3.1 sinh báo cáo, ChromaDB tra cứu tài liệu chuẩn |
| **Live Clock** | Đồng hồ thời gian thực, chuyển đổi 4 múi giờ (VN, UTC, US, JP) |
| **Xóa lịch sử** | Xóa assessment cũ với popup xác nhận, chặn cảnh báo 24h |
| **Tái sử dụng form** | Click vào lịch sử đánh giá → xem chi tiết hoặc nạp lại form cũ |

---

## Công nghệ sử dụng

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| **Frontend** | Next.js 15, React 19, CSS Modules | Giao diện web SPA |
| **Backend** | FastAPI, Python 3.10, Uvicorn | API server, AI pipeline |
| **LLM chính** | Llama 3.1 8B (Q4_K_M) | Sinh báo cáo tiếng Việt |
| **LLM bảo mật** | SecurityLLM 7B (Q4_K_M) | Phân tích compliance ISO |
| **NLP** | PhoBERT (VinAI) | Xử lý ngôn ngữ tự nhiên tiếng Việt |
| **Vector DB** | ChromaDB 0.4.24 | Lưu trữ/Tìm kiếm tài liệu tiêu chuẩn |
| **LLM Runtime** | LocalAI | Chạy GGUF models trên CPU |
| **Container** | Docker Compose | Triển khai 1 lệnh duy nhất |

---

## Cấu trúc thư mục

```text
phobert-chatbot-project/
│
├── frontend-next/                          # Next.js Frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.js                   # Root layout (Navbar + Footer)
│   │   │   ├── globals.css                 # Design system toàn cục
│   │   │   ├── page.js                     # Trang chủ Dashboard
│   │   │   ├── chatbot/page.js             # Chatbot AI tiếng Việt
│   │   │   ├── analytics/page.js           # Analytics + ChromaDB Monitor
│   │   │   └── form-iso/page.js            # Form đánh giá ISO 27001
│   │   └── components/
│   │       ├── Navbar.js                   # Thanh điều hướng + Đồng hồ Live
│   │       └── SystemStats.js              # Card tài nguyên CPU/RAM/Disk
│   ├── Dockerfile                          # Build production image
│   ├── package.json
│   └── next.config.js                      # Proxy API → Backend
│
├── backend/                                # FastAPI Backend
│   ├── api/routes/
│   │   ├── chat.py                         # POST /api/chat — Chatbot endpoint
│   │   ├── iso27001.py                     # CRUD đánh giá + ChromaDB API
│   │   ├── health.py                       # GET /api/health — Health check
│   │   ├── system.py                       # GET /api/system/stats — CPU/RAM/Disk
│   │   └── document.py                     # Upload tài liệu
│   ├── services/
│   │   ├── chat_service.py                 # Gọi LocalAI, quản lý VectorStore
│   │   ├── mcp_server.py                   # MCP Server (semantic search tool)
│   │   └── model_router.py                 # Điều phối SecurityLLM ↔ Llama 3.1
│   ├── repositories/
│   │   └── vector_store.py                 # ChromaDB wrapper (chunk, index, search)
│   ├── core/config.py                      # Biến cấu hình tập trung
│   ├── utils/logger.py                     # Logging
│   ├── main.py                             # Điểm khởi chạy FastAPI
│   ├── Dockerfile
│   └── requirements.txt
│
├── data/
│   ├── iso_documents/                      # Tài liệu tiêu chuẩn cho RAG
│   │   ├── iso27001_annex_a.md             # ISO 27001:2022 Phụ lục A (93 controls)
│   │   ├── tcvn_11930_2017.md              # TCVN 11930:2017 (5 cấp HTTT)
│   │   ├── nghi_dinh_13_2023_bvdlcn.md     # NĐ 13/2023 Bảo vệ DLCN
│   │   ├── luat_an_ninh_mang_2018.md       # Luật An ninh mạng 2018
│   │   ├── checklist_danh_gia_he_thong.md  # Checklist đánh giá hệ thống IT
│   │   ├── assessment_criteria.md          # Tiêu chí chấm điểm đánh giá
│   │   └── network_infrastructure.md       # Hạ tầng mạng tham chiếu
│   ├── assessments/                        # Kết quả đánh giá (JSON files)
│   ├── knowledge_base/                     # Knowledge base JSON
│   ├── sessions/                           # Phiên chat
│   ├── uploads/                            # File upload (tài liệu, ảnh)
│   └── vector_store/                       # ChromaDB persistent data
│
├── models/                                 # GGUF model files (tải tự động)
├── docker-compose.yml                      # Orchestration toàn bộ services
├── .env.example                            # Mẫu biến môi trường
└── README.md
```

---

## Cài đặt và Triển khai

### Yêu cầu hệ thống
- **Docker** và **Docker Compose** (phiên bản mới nhất)
- **RAM**: Tối thiểu 16GB (khuyến nghị 32GB)
- **Disk**: Tối thiểu 20GB trống (cho models ~10GB)
- **CPU**: 4 cores trở lên (models chạy trên CPU)

### Bước 1 — Clone và cấu hình

```bash
git clone https://github.com/NghiaDinh03/phobert-chatbot-project.git
cd phobert-chatbot-project

cp .env.example .env
```

### Bước 2 — Khởi chạy toàn bộ (1 lệnh duy nhất)

```bash
docker-compose up --build -d
```

Lệnh trên sẽ:
1. Build 2 Docker images (Frontend + Backend)
2. Tự động kéo image LocalAI từ Docker Hub
3. Tải model Llama 3.1 8B và SecurityLLM 7B (~10GB, chỉ lần đầu)
4. Khởi động 3 containers: `phobert-frontend`, `phobert-backend`, `phobert-localai`

### Bước 3 — Truy cập

| Dịch vụ | URL | Mô tả |
|---|---|---|
| **Giao diện web** | http://localhost:3000 | Trang chính (Dashboard, Chatbot, Form, Analytics) |
| **Backend API** | http://localhost:8000 | FastAPI endpoints |
| **API Docs (Swagger)** | http://localhost:8000/docs | Tài liệu API tương tác |
| **LocalAI** | http://localhost:8080 | LLM inference server |

---

## Hướng dẫn sử dụng

### 1. Chatbot AI
- Truy cập tab **"AI Chat"** trên thanh điều hướng
- Nhập câu hỏi bằng tiếng Việt về an toàn thông tin, ISO 27001
- AI sẽ trả lời dựa trên tài liệu chuẩn đã được nạp vào ChromaDB

### 2. Đánh giá ISO 27001
- Truy cập tab **"Form ISO"**
- Nhập thông tin tổ chức: tên, quy mô, ngành nghề
- Nhập thông tin hạ tầng: số server, firewall, VPN, cloud
- Chọn các chính sách ATTT đã có (checkbox)
- Nhấn **"🤖 Đánh giá bằng AI"** → AI phân tích và trả về báo cáo
- Xem kết quả tại tab **"Analytics"** → click vào lịch sử để xem chi tiết

### 3. Quản lý tài liệu ChromaDB
- Thả file `.md` (Markdown) vào thư mục `data/iso_documents/`
- Truy cập Analytics Dashboard → phần **"ChromaDB Monitor"**
- Nhấn **"🔄 Reindex tài liệu"** để nạp file mới vào Vector Database
- Dùng ô **"Test tìm kiếm"** để kiểm tra ChromaDB đã đọc được tài liệu

### 4. Xem Analytics
- Tab **"Analytics"** hiển thị:
  - Tài nguyên hệ thống (CPU, RAM, Disk, Uptime)
  - Trạng thái tất cả dịch vụ (Backend, LocalAI, ChromaDB, Models)
  - ChromaDB Monitor (số chunks, files, metric, search test)
  - Lịch sử đánh giá ISO 27001 (click xem chi tiết / tái sử dụng / xóa)

---

## Cấu hình biến môi trường

| Biến | Mô tả | Mặc định |
|---|---|---|
| `MODEL_NAME` | Tên file GGUF model chính | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` |
| `SECURITY_MODEL_NAME` | Tên model phân tích bảo mật | `SecurityLLM-7B-v0.1-Q4_K_M.gguf` |
| `LOCALAI_URL` | URL nội bộ của LocalAI | `http://localai:8080` |
| `MAX_TOKENS` | Giới hạn output tokens | `-1` (không giới hạn) |
| `ISO_DOCS_PATH` | Thư mục tài liệu ISO | `/data/iso_documents` |
| `VECTOR_STORE_PATH` | Thư mục lưu ChromaDB | `/data/vector_store` |
| `DATA_PATH` | Thư mục dữ liệu chung | `/data` |
| `LOG_LEVEL` | Mức ghi log | `INFO` |

---

## Kiến trúc hệ thống

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│   Next.js 15    │──────▶│    FastAPI Backend   │──────▶│    LocalAI      │
│   (Port 3000)   │  API  │    (Port 8000)       │  HTTP │    (Port 8080)  │
│                 │       │                     │       │                 │
│  - Dashboard    │       │  - Model Router     │       │  - Llama 3.1 8B │
│  - Chatbot      │       │  - Vector Store     │       │  - SecurityLLM  │
│  - Form ISO     │       │  - MCP Server       │       │  - PhoBERT      │
│  - Analytics    │       │  - Assessment CRUD  │       │                 │
└─────────────────┘       └────────┬────────────┘       └─────────────────┘
                                   │
                          ┌────────▼────────────┐
                          │     ChromaDB         │
                          │  (Vector Database)   │
                          │                     │
                          │  - ISO 27001 Annex A │
                          │  - TCVN 11930:2017   │
                          │  - NĐ 13/2023 BVDLCN │
                          │  - Luật ANM 2018     │
                          └─────────────────────┘
```

---

## API Endpoints

### Chat
| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/chat` | Gửi tin nhắn tới AI Chatbot |

### ISO 27001
| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/iso27001/assess` | Submit đánh giá ISO 27001 |
| GET | `/api/iso27001/assessments` | Lấy danh sách lịch sử đánh giá |
| GET | `/api/iso27001/assessments/{id}` | Xem chi tiết 1 đánh giá |
| DELETE | `/api/iso27001/assessments/{id}` | Xóa 1 đánh giá |
| POST | `/api/iso27001/reindex` | Nạp lại tài liệu vào ChromaDB |
| GET | `/api/iso27001/chromadb/stats` | Thống kê ChromaDB |
| POST | `/api/iso27001/chromadb/search` | Test tìm kiếm ChromaDB |

### Hệ thống
| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/health` | Kiểm tra trạng thái Backend |
| GET | `/api/system/stats` | Lấy thông tin CPU, RAM, Disk |

---

## Tài liệu tiêu chuẩn đã tích hợp

| File | Nội dung | Nguồn |
|---|---|---|
| `iso27001_annex_a.md` | Phụ lục A — 93 biện pháp kiểm soát (4 nhóm) | ISO/IEC 27001:2022 |
| `tcvn_11930_2017.md` | Phân cấp 5 cấp HTTT, yêu cầu kỹ thuật 5 lớp bảo vệ | TCVN 11930:2017 |
| `nghi_dinh_13_2023_bvdlcn.md` | Bảo vệ dữ liệu cá nhân, quyền chủ thể, DPIA | NĐ 13/2023/NĐ-CP |
| `luat_an_ninh_mang_2018.md` | Luật An ninh mạng, nghĩa vụ doanh nghiệp | Luật số 24/2018/QH14 |
| `checklist_danh_gia_he_thong.md` | Checklist đánh giá toàn diện hạ tầng IT | Tổng hợp ISO + TCVN |
| `assessment_criteria.md` | Thang điểm và tiêu chí đánh giá | ISO 27001:2022 |
| `network_infrastructure.md` | Kiến trúc mạng tham chiếu, checklist thiết bị | Best practices |

---

## Khắc phục sự cố

| Vấn đề | Giải pháp |
|---|---|
| ChromaDB lỗi `duplicate column bool_value` | Xóa `data/vector_store/`, restart backend |
| Model tải quá lâu | Lần đầu tải ~10GB, kiểm tra mạng và dung lượng disk |
| AI timeout khi đánh giá | Request timeout đã được tăng lên 15 phút cho CPU |
| Frontend bị Hydration error | Dùng `suppressHydrationWarning` hoặc `mounted` state |
| RAM không đủ | Cần tối thiểu 16GB, khuyến nghị 32GB |
