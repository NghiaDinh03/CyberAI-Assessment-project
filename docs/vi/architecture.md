# Kiến Trúc Hệ Thống

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-Architecture-blue?style=flat-square)](architecture.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Kiến_trúc-red?style=flat-square)](architecture_vi.md)

</div>

---

## Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Sơ Đồ Kiến Trúc Tổng Thể](#2-sơ-đồ-kiến-trúc-tổng-thể)
3. [Cấu Hình Container (Docker Compose)](#3-cấu-hình-container-docker-compose)
4. [Frontend — Next.js 14](#4-frontend--nextjs-14)
5. [Backend — FastAPI](#5-backend--fastapi)
6. [Tầng AI — Cloud LLM Service](#6-tầng-ai--cloud-llm-service)
7. [Model Router — Phân Loại Intent Hybrid](#7-model-router--phân-loại-intent-hybrid)
8. [Vector Store — ChromaDB](#8-vector-store--chromadb)
9. [Session Store](#9-session-store)
10. [Tóm Tắt Luồng Dữ Liệu](#10-tóm-tắt-luồng-dữ-liệu)

---

## 1. Tổng Quan

Nền tảng này là ứng dụng AI doanh nghiệp đa tính năng với ba module chính:

| Module | Mô tả |
|--------|-------|
| **AI News Aggregator** | Thu thập RSS → cào bài → Cloud LLM dịch → Edge-TTS audio |
| **RAG Chatbot** | Định tuyến hybrid → RAG ChromaDB / tìm kiếm DuckDuckGo / LLM tổng quát |
| **ISO 27001 Assessor** | Form nhập thông tin → BackgroundTask async → AI phân tích gap |

Ba module đều chia sẻ:
- Một backend **FastAPI** duy nhất (Python 3.11)
- Một frontend **Next.js 14** duy nhất (React, App Router)
- Cùng một **Cloud LLM Service** (`CloudLLMService`) cho mọi lệnh gọi AI
- Cùng một **ChromaDB** vector store để truy xuất kiến thức ISO

---

## 2. Sơ Đồ Kiến Trúc Tổng Thể

```
┌─────────────────────────────────────────────────────────────┐
│                   TRÌNH DUYỆT / CLIENT                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / HTTP
┌──────────────────────────▼──────────────────────────────────┐
│              NEXT.JS 14  (Cổng 3000)                        │
│  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ /chatbot │ │ /news  │ │/form-iso │ │  /analytics      │ │
│  └──────────┘ └────────┘ └──────────┘ └──────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │    Next.js API Routes  (/app/api/*)  — lớp proxy       │ │
│  └────────────────────────┬───────────────────────────────┘ │
└─────────────────────────  │  ──────────────────────────────-┘
                           │ HTTP (mạng nội bộ Docker)
┌──────────────────────────▼──────────────────────────────────┐
│              FASTAPI BACKEND  (Cổng 8000)                   │
│                                                              │
│  Routers:  /api/chat  /api/news  /api/iso27001  /api/system │
│                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │ ChatService  │  │  NewsService  │  │  ISO27001 Route │  │
│  │ (RAG/Search/ │  │  (RSS+Cache)  │  │ (BackgroundTask)│  │
│  │  General LLM)│  └───────┬───────┘  └────────┬────────┘  │
│  └──────┬───────┘          │                   │           │
│         │           ┌──────▼──────┐    ┌───────▼────────┐  │
│  ┌──────▼───────┐   │SummaryService│   │  ChatService   │  │
│  │ ModelRouter  │   │(Scrape+TTS) │    │  assess_system │  │
│  │ (3 routes)   │   └──────┬──────┘    └───────┬────────┘  │
│  └──────┬───────┘          │                   │           │
│         │                  └─────────┬─────────┘           │
│  ┌──────▼──────────────────▼─────────▼───────────────────┐ │
│  │              Cloud LLM Service                        │ │
│  │   Open Claude (chính) → LocalAI (dự phòng)            │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────┐   ┌───────────────────────────────┐  │
│  │  ChromaDB        │   │  SessionStore (file-based)    │  │
│  │  (iso_documents) │   │  /data/sessions/              │  │
│  └──────────────────┘   └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│         /host/proc   (bind mount chỉ đọc)                   │
│   /host/proc/stat · /host/proc/meminfo · /proc/uptime        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Cấu Hình Container (Docker Compose)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./data:/data                      # dữ liệu bền vững
      - /proc:/host/proc:ro               # thống kê hệ thống

  frontend:
    build: ./frontend-next
    ports: ["3000:3000"]
    depends_on: [backend]
    environment:
      - BACKEND_URL=http://backend:8000   # DNS nội bộ Docker
```

**Volumes quan trọng:**

| Host path | Container path | Mục đích |
|-----------|----------------|---------|
| `./data` | `/data` | Bài viết, sessions, summaries, audio, assessments, vector_store |
| `/proc` | `/host/proc` (chỉ đọc) | Thống kê CPU/bộ nhớ cho giám sát hệ thống |

---

## 4. Frontend — Next.js 14

```
frontend-next/src/
├── app/
│   ├── layout.js              # Root layout (ThemeProvider, Navbar)
│   ├── page.js                # Trang chủ dashboard
│   ├── chatbot/page.js        # Giao diện RAG Chatbot
│   ├── news/page.js           # Giao diện News Aggregator
│   ├── form-iso/page.js       # Form Đánh Giá ISO 27001
│   ├── analytics/page.js      # Lịch sử đánh giá + ChromaDB explorer
│   ├── templates/page.js      # Chọn template tiêu chuẩn
│   └── api/                   # Next.js proxy routes → backend
│       ├── chat/route.js
│       ├── news/route.js
│       ├── news/history/route.js
│       ├── news/reprocess/route.js
│       └── news/search/route.js
├── components/
│   ├── Navbar.js              # Đồng hồ (3 múi giờ), chuyển theme, nav
│   ├── SystemStats.js         # Widget CPU / RAM / Disk / Uptime
│   └── ThemeProvider.js       # Chuyển đổi biến CSS dark/light
```

### Proxy API Next.js

Lớp proxy frontend (`/app/api/`) ghi lại tất cả yêu cầu `/api/*` tới backend FastAPI bằng biến môi trường `BACKEND_URL`. Điều này tránh vấn đề CORS khi triển khai production:

```js
// next.config.js — quy tắc rewrite
{ source: '/api/:path*', destination: `${BACKEND_URL}/api/:path*` }
```

---

## 5. Backend — FastAPI

```
backend/
├── main.py                    # App factory, CORS, middleware, startup
├── core/config.py             # Cấu hình (biến môi trường, API keys)
├── api/routes/
│   ├── chat.py                # POST /api/chat, POST /api/chat/stream, GET /api/chat/history/:id
│   ├── news.py                # GET /api/news, POST /api/news/summarize, ...
│   ├── iso27001.py            # POST /api/iso27001/assess (async), GET kết quả
│   └── system.py             # GET /api/system/stats, GET /api/system/cache-stats
├── services/
│   ├── chat_service.py        # Điều phối hội thoại
│   ├── cloud_llm_service.py   # Open Claude + LocalAI
│   ├── model_router.py        # Định tuyến intent hybrid (3 routes)
│   ├── news_service.py        # RSS + cache in-memory + worker queues
│   ├── summary_service.py     # Pipeline cào + dịch + TTS
│   ├── web_search.py          # Tìm kiếm DuckDuckGo (ddgs)
│   ├── translation_service.py # Cache dịch tiêu đề hàng loạt
│   └── rag_service.py        # Query builder RAG
├── repositories/
│   ├── vector_store.py        # ChromaDB wrapper (iso_documents)
│   └── session_store.py      # Lưu trữ session bền vững theo file
└── utils/
    ├── helpers.py
    └── logger.py
```

### Trình Tự Khởi Động (`main.py`)

```python
@app.on_event("startup")
def on_startup():
    settings.validate()            # Kiểm tra biến môi trường bắt buộc
    VectorStore().ensure_indexed() # Index tài liệu ISO → ChromaDB nếu cần
    SessionStore().cleanup_expired()
```

### Middleware

| Middleware | Chi tiết |
|-----------|---------|
| CORS | Origins: `*` (có thể cấu hình) |
| Giới hạn kích thước request | Tối đa 10 MB body |
| Xử lý 404 / 500 | Phản hồi JSON lỗi |

---

## 6. Tầng AI — Cloud LLM Service

File: [`backend/services/cloud_llm_service.py`](../backend/services/cloud_llm_service.py)

### Chuỗi Dự Phòng 2 Tầng

```
Yêu cầu
   │
   ▼
┌──────────────────────────────────────────┐
│  Tầng 1 — Open Claude (chính)            │
│  Endpoint: OPEN_CLAUDE_API_BASE          │
│  Auth: OPEN_CLAUDE_API_KEY (round-robin) │
└──────────────────────┬───────────────────┘
                       │ THẤT BẠI (timeout / 5xx / không có key)
                       ▼
┌──────────────────────────────────────────┐
│  Tầng 2 — LocalAI (dự phòng)             │
│  Endpoint: LOCAL_AI_BASE_URL             │
│  Model: LOCAL_AI_MODEL                   │
└──────────────────────────────────────────┘
```

> ⚠️ **Không có OpenRouter.** Dự án chỉ sử dụng hai tầng này.

### Bảng Model Theo Task

```python
TASK_MODEL_MAP = {
    "news_translate": "gemini-2.5-pro",          # Dịch toàn bộ bài báo
    "news_summary":   "gemini-3-flash-preview",  # Tóm tắt nhanh
    "iso_analysis":   "gemini-2.5-pro",          # Phân tích gap ISO
    "complex":        "gemini-2.5-pro",           # Truy vấn chat phức tạp
    "chat":           "gemini-3-pro-preview",     # Chat thông thường
    "default":        "gemini-3-pro-preview",     # Mặc định dự phòng
}

LOCAL_ONLY_TASKS = {"iso_local"}  # Chỉ gửi tới LocalAI
```

### Round-Robin Key Rotation

```python
OPEN_CLAUDE_API_KEY=key1,key2,key3,...   # phân cách bằng dấu phẩy trong .env
# Mỗi yêu cầu dùng: keys[_key_index % len(keys)]
# _key_index tăng theo mỗi lần gọi → cân bằng tải tự động
```

### Dọn Dẹp Special Token

Sau mỗi phản hồi LLM, các artifact định dạng Llama bị loại bỏ:

```python
summary_vi = summary_vi.replace("<|eot_id|>", "")
summary_vi = summary_vi.replace("<|end_header_id|>", "")
if summary_vi.lower().startswith("assistant"):
    summary_vi = summary_vi[len("assistant"):].strip()
```

---

## 7. Model Router — Phân Loại Intent Hybrid

File: [`backend/services/model_router.py`](../backend/services/model_router.py)

### Các Route

| Route | Điều kiện kích hoạt | Hành động |
|-------|---------------------|----------|
| `security` | Từ khóa ISO/bảo mật hoặc khớp ngữ nghĩa | Load context ISO từ ChromaDB → phản hồi RAG |
| `search` | Từ khóa tìm kiếm/tin tức/xu hướng | Tìm kiếm web DuckDuckGo → inject kết quả làm context |
| `general` | Mọi thứ còn lại | Phản hồi LLM trực tiếp (không truy xuất) |

### Luồng Phân Loại

```
Tin nhắn người dùng
        │
        ▼
┌────────────────────────────────────────────────┐
│  Bước 1: Phân loại ngữ nghĩa                   │
│  Collection ChromaDB in-memory: intent_classifier│
│  Model: sentence-transformers (cosine distance) │
│  Ngưỡng confidence: 0.6                         │
└──────────────────┬─────────────────────────────┘
                   │
          confidence > 0.6?
         /               \
       CÓ                 KHÔNG
        │                   │
        ▼                   ▼
   Dùng route          Bước 2: Keyword fallback
   ngữ nghĩa           ┌────────────────────────┐
                       │ security_keywords set  │
                       │ search_keywords set    │
                       │ → khớp → gán route     │
                       └────────────────────────┘
                                 │
                       không khớp → "general"
```

---

## 8. Vector Store — ChromaDB

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py)

### Cấu Hình

| Tham số | Giá trị |
|---------|---------|
| Tên collection | `iso_documents` |
| Metric khoảng cách | cosine |
| Kích thước chunk | 600 ký tự |
| Overlap chunk | 150 ký tự |
| Thư mục lưu trữ | `/data/vector_store` |

### Chunking Nhận Biết Header

Tài liệu được chia nhỏ với phân cấp markdown được bảo tồn:

```python
# Mỗi chunk nhận tiền tố context:
"[Context: # ISO 27001 > ## Annex A > ### A.9 Access Control]"

# Ví dụ chunk:
"[Context: # ISO 27001 > ## Annex A > ### A.9]\n"
"A.9.1.1 Chính sách kiểm soát truy cập — Cần thiết lập chính sách..."
```

### Tài Liệu Được Index

Nguồn: `data/iso_documents/`

| File | Nội dung |
|------|---------|
| `iso27001_annex_a.md` | Toàn bộ Annex A controls |
| `assessment_criteria.md` | Tiêu chí đánh giá điểm số |
| `checklist_danh_gia_he_thong.md` | Checklist đánh giá hệ thống |
| `luat_an_ninh_mang_2018.md` | Luật An ninh Mạng Việt Nam 2018 |
| `network_infrastructure.md` | Hướng dẫn bảo mật mạng |
| `nghi_dinh_13_2023_bvdlcn.md` | Nghị định 13/2023 bảo vệ dữ liệu cá nhân |
| `tcvn_11930_2017.md` | Tiêu chuẩn TCVN 11930:2017 |

### API Tìm Kiếm

```python
results = vector_store.search(query, top_k=5)
# Trả về: [{id, document, metadata, distance}, ...]

results = vector_store.multi_query_search(query, top_k=5)
# Tạo 3 biến thể query → gộp → loại trùng theo distance
```

---

## 9. Session Store

File: [`backend/repositories/session_store.py`](../backend/repositories/session_store.py)

```
/data/sessions/
└── {session_id}.json    ← một file mỗi cuộc hội thoại
```

| Tham số | Giá trị |
|---------|---------|
| Định dạng lưu trữ | JSON file theo session |
| TTL | 86400 giây (24 giờ) |
| Số tin nhắn lưu tối đa | 20 mỗi session |
| Tin nhắn gửi tới LLM | 10 cuối (`history[-10:]`) |
| Dọn dẹp | Khi khởi động + định kỳ |

```python
def get_context_messages(self, session_id: str, max_messages: int = 10):
    history = self.load(session_id).get("messages", [])
    return history[-max_messages:]   # Luôn lấy 10 tin nhắn gần nhất
```

---

## 10. Tóm Tắt Luồng Dữ Liệu

### Yêu Cầu Chat

```
POST /api/chat  { message, session_id }
  → ChatService.generate_response()
      → ModelRouter.route_model(message)        # phân loại hybrid
          ├─ route=security  → VectorStore.search() → build_rag_prompt()
          ├─ route=search    → WebSearch.search()   → build_search_prompt()
          └─ route=general   → build_general_prompt()
      → SessionStore.get_context_messages()     # 10 tin nhắn gần nhất
      → CloudLLMService.chat_completion()       # Open Claude → LocalAI
      → SessionStore.add_message()              # lưu trữ cuộc trao đổi
  ← { response, session_id, route, model, provider }
```

### Pipeline Bài Báo Tin Tức

```
GET /api/news?category=cybersecurity
  → NewsService.get_news()
      → _parse_rss() × 3 nguồn         # TheHackerNews, DarkReading, SecurityWeek
      → SummaryService._get_cache()    # kiểm tra audio/summary đã có
      → _apply_translations()          # load title_vi từ cache dịch
      → _update_history()              # lưu vào /data/articles_history.json
      → _llama_queue.put()             # đưa vào hàng đợi xử lý nền

POST /api/news/summarize  { url, lang, title }
  → SummaryService.process_article()   # khóa theo URL
      Bước 1: scrape_article()          # requests-bs4 → trafilatura → newspaper3k
      Bước 2: CloudLLMService.chat_completion(task_type="news_translate")
              → gemini-2.5-pro (qua Open Claude)
              → dọn artifact AI (*, #, <|eot_id|>, ...)
      Bước 3: edge_tts.Communicate("vi-VN-HoaiMyNeural").save(audio_path)
  ← { audio_url, summary_vi, title_vi }
```

### Đánh Giá ISO 27001

```
POST /api/iso27001/assess  { system_info, controls, standard_id }
  → tạo assessment_id = uuid4()
  → lưu JSON { id, status:"pending", data }
  → BackgroundTasks.add_task(process_assessment_bg, assessment_id)
  ← 202 { id, status:"pending" }   ← phản hồi ngay lập tức

[Luồng Nền]
  → ChatService.assess_system()
      → VectorStore.search(query, top_k=5)  # controls ISO liên quan
      → CloudLLMService.chat_completion(task_type="iso_analysis")
         → gemini-2.5-pro (qua Open Claude)
  → lưu JSON { id, status:"done", result }

GET /api/iso27001/assessments/{id}
  ← { id, status:"pending"|"done", result? }
```
