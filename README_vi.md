<div align="center">
  <h1>🛡️ CyberAI Assessment Platform v2.0</h1>
  <p>Đánh giá ISO 27001 Doanh nghiệp · Chatbot RAG · Tổng hợp Tin tức AI · Text-to-Speech</p>
  <p>
    <a href="README.md"><img src="https://img.shields.io/badge/English-README-blue?logo=googletranslate&logoColor=white" /></a>
    <a href="README_vi.md"><img src="https://img.shields.io/badge/Tiếng Việt-README-red?logo=googletranslate&logoColor=white" /></a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Next.js-15.1-black?logo=next.js" />
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" />
    <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python" />
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker" />
    <img src="https://img.shields.io/badge/ChromaDB-Vector_Store-orange" />
    <img src="https://img.shields.io/badge/Open_Claude-Primary_LLM-green" />
  </p>
</div>

---

## Mục lục
- [Tổng quan](#tổng-quan)
- [Kiến trúc Hệ thống](#kiến-trúc-hệ-thống)
- [Cơ chế Hoạt động Từng Tính năng](#cơ-chế-hoạt-động-từng-tính-năng)
  - [AI Chatbot (RAG + Web Search)](#1-ai-chatbot--rag--web-search)
  - [Đánh giá ISO 27001 / TCVN](#2-đánh-giá-iso-27001--tcvn)
  - [Tổng hợp Tin tức + TTS](#3-tổng-hợp-tin-tức--text-to-speech)
  - [Analytics Dashboard](#4-analytics-dashboard)
- [Công nghệ Sử dụng](#công-nghệ-sử-dụng)
- [AI Models & Định tuyến Tác vụ](#ai-models--định-tuyến-tác-vụ)
- [Cài đặt Nhanh](#cài-đặt-nhanh)
- [Biến Môi trường](#biến-môi-trường)
- [Tài liệu](#tài-liệu)

---

## Tổng quan

**CyberAI Assessment Platform** là hệ thống AI on-premise (tại chỗ) toàn diện, đóng gói bằng Docker, dành cho doanh nghiệp Việt Nam. Hệ thống cung cấp:

- **Đánh giá tuân thủ ISO 27001:2022 & TCVN 11930:2017** — phân tích GAP tự động bằng pipeline AI 2 pha, xử lý bất đồng bộ (async background task)
- **Chatbot RAG thông minh** — định tuyến hybrid (semantic + từ khóa) với ChromaDB retrieval và tùy chọn tìm kiếm DuckDuckGo trực tiếp
- **Tổng hợp Tin tức AI + TTS** — RSS aggregation, dịch sang tiếng Việt bằng VinAI, tạo audio bằng Edge-TTS với fallback AI 2 tầng
- **Analytics Dashboard** — giám sát hệ thống realtime qua `/host/proc/`, quản lý ChromaDB, lịch sử đánh giá

Toàn bộ hệ thống khởi động bằng một lệnh: `docker-compose up --build -d`

---

## Kiến trúc Hệ thống

### Sơ đồ Container

```
Máy chủ Host
│
├── :3000  ──► phobert-frontend  (Next.js 15)
│                  next.config.js rewrite:
│                  /api/:path* → http://backend:8000/api/:path*
│
├── :8000  ──► phobert-backend   (FastAPI / Python 3.11)
│                  ├── services/
│                  │   ├── cloud_llm_service.py  ← Open Claude (chính)
│                  │   ├── chat_service.py        ← RAG + web search + session
│                  │   ├── model_router.py        ← router hybrid semantic+từ khóa
│                  │   ├── summary_service.py     ← cào bài + dịch + TTS
│                  │   ├── news_service.py        ← RSS + background workers
│                  │   ├── translation_service.py ← VinAI EN→VI (CPU)
│                  │   └── web_search.py          ← DuckDuckGo search
│                  └── repositories/
│                      ├── vector_store.py        ← ChromaDB wrapper
│                      └── session_store.py       ← lưu session dạng file
│
└── :8080  ──► phobert-localai   (LocalAI GGUF server)
                   /models/Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf
                   /models/SecurityLLM-7B-Q4_K_M.gguf

Volume dùng chung:  ./data:/data
  data/
  ├── iso_documents/   ← file .md làm knowledge base cho ChromaDB
  ├── vector_store/    ← ChromaDB SQLite (collection: iso_documents)
  ├── summaries/       ← cache JSON bài báo (TTL 7 ngày)
  │   └── audio/       ← file MP3 Edge-TTS
  ├── sessions/        ← session chat JSON (TTL 24h)
  ├── translations/    ← cache dịch tiêu đề VinAI
  ├── assessments/     ← báo cáo đánh giá ISO (vĩnh viễn)
  └── knowledge_base/  ← định nghĩa controls ISO/TCVN tĩnh
```

### Chuỗi Fallback AI

```
Tác vụ đến → CloudLLMService.chat_completion()
    │
    ├── task_type == "iso_local"?
    │     └── CHỈ LocalAI (SecurityLLM) → raise nếu lỗi
    │
    └── Cloud path:
          Open Claude (CLOUD_API_KEYS, round-robin)
            │ 429 → khóa key 60s, thử key tiếp theo
            │ 401 → bỏ qua key (lỗi cấu hình, không cooldown)
            │ 404 → retry với CLOUD_MODEL_NAME mặc định
            │ Tất cả key hết?
            ▼
          LocalAI (http://localai:8080/v1/chat/completions)
            │ Timeout: INFERENCE_TIMEOUT (mặc định 120s)
            │ Kiểm tra bận: get_ai_status() ≠ "Đang rảnh" → raise
            ▼
          raise Exception("All AI providers failed")
```

### Định tuyến Model Theo Tác vụ

| Task type | Cloud model | Fallback |
|-----------|-------------|---------|
| `news_translate` | `gemini-2.5-pro` | LocalAI 70B |
| `news_summary` | `gemini-3-flash-preview` | LocalAI 70B |
| `iso_analysis` | `gemini-2.5-pro` | LocalAI SecurityLLM |
| `complex` | `gemini-2.5-pro` | LocalAI 70B |
| `chat` | `gemini-3-pro-preview` | LocalAI 70B |
| `iso_local` | — | CHỈ LocalAI SecurityLLM |
| `default` | `gemini-3-pro-preview` | LocalAI 70B |

---

## Cơ chế Hoạt động Từng Tính năng

### 1. AI Chatbot — RAG + Web Search

```
Người dùng gửi tin nhắn → POST /api/chat  (hoặc /api/chat/stream cho SSE)
        │
        ▼
[model_router.py: route_model(message)]
  Phân loại Hybrid:
  ┌─────────────────────────────────────────────────────────┐
  │ Bước 1: Semantic (ChromaDB intent classifier in-memory) │
  │   Templates: security / search / general               │
  │   confidence > 0.6 → dùng kết quả semantic             │
  │                                                         │
  │ Bước 2: Keyword fallback (confidence ≤ 0.6)            │
  │   ISO_KEYWORDS → route=security, use_rag=True           │
  │   SEARCH_KEYWORDS → route=search, use_search=True       │
  │   else → route=general                                  │
  └─────────────────────────────────────────────────────────┘
        │
        ├── route=security → Tra cứu ChromaDB
        │   VectorStore.search(câu hỏi, top_k=5)
        │   Collection: "iso_documents"
        │   Kết quả xếp hạng theo cosine similarity
        │
        ├── route=search → DuckDuckGo Web Search
        │   WebSearch.search(query, max_results=5, region="vn-vi")
        │   Trả về [{title, url, snippet}]
        │
        └── route=general → không tra cứu bên ngoài
        │
        ▼
[SessionStore: get_context_messages(session_id, max_messages=10)]
  Load 10 tin nhắn gần nhất từ data/sessions/<session_id>.json
  TTL: 24h | MAX_HISTORY_PER_SESSION = 20 lưu, 10 gửi LLM
        │
        ▼
[_build_messages(): system prompt + context RAG/search + lịch sử + câu hỏi]
        │
        ▼
[CloudLLMService.chat_completion()]
  Open Claude → LocalAI fallback
  Trả về: {content, model, provider, usage}
        │
        ▼
[Lưu session + trả response]
  {response, model, provider, route, rag_used, search_used,
   sources, web_sources, tokens}
```

**Streaming** (`POST /api/chat/stream`): Sự kiện SSE theo thứ tự:
`routing` → `rag` (nếu ISO) → `searching` (nếu search) → `thinking` → `done`

---

### 2. Đánh giá ISO 27001 / TCVN

```
Người dùng điền form nhiều bước → POST /api/iso27001/assess
  Payload SystemInfo:
  { assessment_standard, org_name, servers, firewalls, vpn,
    cloud_provider, antivirus, siem, implemented_controls[],
    incidents_12m, employees, iso_status, notes }
        │
        ▼
[BackgroundTasks] — bất đồng bộ, không block UI
  assessment_id = uuid4()
  Lưu vào data/assessments/<id>.json với status="pending"
  Trả về ngay: { id, status: "pending" }
        │
        ▼ (chạy nền)
[chat_service.py: assess_system(system_data)]
        │
        ▼
Pha 1: RAG Context
  VectorStore.search(query theo tiêu chuẩn, top_k=6)
  ISO 27001 → "A.5 Tổ chức, A.6 Nhân sự, A.7 Vật lý, A.8 Công nghệ"
  TCVN 11930 → "TCVN 11930 hệ thống thông tin cấp độ bảo đảm an toàn"
        │
        ▼
Pha 2: Security Audit (task_type="iso_local" → LocalAI SecurityLLM)
  Prompt: "Chuyên gia Auditor về {std}. Chỉ trả về danh sách phát hiện kỹ thuật thô."
  Đầu vào: RAG context + thông tin hệ thống
  Điểm tuân thủ: len(implemented_controls) / 93 (ISO) hoặc /34 (TCVN)
        │
        ▼
Pha 3: Định dạng Báo cáo (task_type="iso_analysis" → gemini-2.5-pro)
  Prompt: Format phân tích thô thành Markdown tiếng Việt:
    1. ĐÁNH GIÁ TỔNG QUAN
    2. PHÂN TÍCH LỖ HỔNG (GAP ANALYSIS)
    3. KHUYẾN NGHỊ ƯU TIÊN (ACTION PLAN)
        │
        ▼
Lưu vào data/assessments/<id>.json với status="completed"
Frontend polling GET /api/iso27001/history để xem kết quả
```

**Tiêu chuẩn được hỗ trợ:**

| Tiêu chuẩn | Điểm tối đa | Cách tính |
|------------|------------|----------|
| ISO 27001:2022 | 93 controls | `len(implemented) / 93 × 100%` |
| TCVN 11930:2017 | 34 yêu cầu | `len(implemented) / 34 × 100%` |

---

### 3. Tổng hợp Tin tức + Text-to-Speech

```
[Background worker: start_bg_worker()]
  feedparser.parse(rss_url) → 15 bài/danh mục
  Danh mục:
  • cybersecurity         → The Hacker News, BleepingComputer, Dark Reading
  • stocks_international  → CNBC, Yahoo Finance, MarketWatch
  • stocks_vietnam        → CafeF, VnEconomy, VnExpress Finance

  ┌── Thread: _translation_worker()
  │   Hàng đợi: _translate_queue
  │   VinAI envit5-translation (135M, local CPU)
  │   Batch: 8 tiêu đề, torch.jit.optimize_for_inference()
  │   Cache: data/translations/<category>.json
  │
  └── Thread: _llama_worker()
      Hàng đợi: _llama_queue
      CloudLLMService.quick_completion() → gán tag cho bài báo
      Prompt: "Tag 1-2 keywords. No explanation."

Người dùng click ▶ Nghe → POST /api/news/summarize
        │
        ▼
[SummaryService._process_article_internal()]
  Kiểm tra cache: MD5(url) → data/summaries/<hash>.json
        │ Cache hit → trả về {audio_url, summary_vi} ngay
        │ Cache miss ↓
        ▼
Cào nội dung (3 phương pháp fallback):
  1. requests + BeautifulSoup4
  2. trafilatura
  3. newspaper3k
  Giới hạn 12.000 ký tự, lọc nhiễu, khử trùng
        │
        ▼
Dịch AI (fallback 2 tầng):
  1. Open Claude
     news_translate → gemini-2.5-pro (chất lượng cao)
     news_summary   → gemini-3-flash-preview (nhanh, rẻ)
     Round-robin CLOUD_API_KEYS, cooldown 60s khi 429
  2. LocalAI Llama 3.1 70B (fallback offline)
  Prompt: viết lại hoàn toàn theo phong cách báo chí tiếng Việt
  Giữ nguyên: CVE, ngày tháng, tên, thống kê
  max_tokens: 16000
        │
        ▼
_fix_pronunciation(): DDoS→"Đi Đốt", VPN, SSL/TLS, ransomware...
        │
        ▼
Edge-TTS: giọng "vi-VN-HoaiMyNeural" → data/summaries/audio/<hash>.mp3
Lưu cache: data/summaries/<hash>.json (TTL: 7 ngày)
```

---

### 4. Analytics Dashboard

```
Trang /analytics
  │
  ├── GET /api/system/stats (mỗi 5 giây)
  │     Đọc /host/proc/stat, /host/proc/meminfo (filesystem host)
  │     CPU%, RAM đã dùng/tổng/%, disk%, uptime
  │
  ├── GET /api/system/ai-status
  │     CloudLLMService.health_check()
  │     → open_claude: {configured, url, model, task_routing, keys_count, status}
  │     → localai: {url, model, status}
  │
  ├── GET /api/iso27001/history
  │     Liệt kê data/assessments/*.json
  │     Cột: id, status, standard, org_name, created_at
  │
  ├── GET /api/iso27001/chromadb/stats
  │     Collection "iso_documents": số doc, số chunk
  │
  ├── POST /api/iso27001/chromadb/search { query, n_results }
  │     VectorStore.search() → top-N chunks kèm điểm cosine
  │
  └── POST /api/iso27001/chromadb/reload
        Xóa collection → index lại toàn bộ data/iso_documents/*.md
        chunk_size: 600 ký tự, overlap: 150 ký tự
        Header-aware: [Context: # > ## > ###] gắn đầu mỗi chunk
```

---

## Công nghệ Sử dụng

### Frontend

| Công nghệ | Phiên bản | Vai trò |
|-----------|----------|--------|
| Next.js | 15.1 | App Router, SSR, proxy `/api/*` đến backend |
| React | 19.0 | Components, `useState` / `useEffect` / `useRef` |
| CSS Modules | — | Style có phạm vi, CSS custom properties (dark/light theme) |
| react-markdown | 9.0 | Render báo cáo markdown từ AI |
| remark-gfm | 4.0 | GitHub-flavored markdown (bảng, task lists) |

### Backend

| Công nghệ | Vai trò |
|-----------|--------|
| FastAPI 0.115 | Async REST API, StreamingResponse cho chat SSE |
| Python 3.11 | Runtime |
| Pydantic v2 | Validate request/response |
| slowapi | Rate limiting (chat: 10/phút, assess: 3/phút, news: 5/phút) |
| httpx | Async HTTP cho Open Claude API |
| requests | Sync HTTP cho LocalAI + cào bài báo |
| chromadb | Vector database cục bộ (SQLite) |
| sentence-transformers | `all-MiniLM-L6-v2` embedding (384-dim) |
| transformers + torch | VinAI `envit5-translation` (135M, CPU) |
| feedparser | Phân tích RSS feed |
| BeautifulSoup4 | Cào HTML chính |
| trafilatura | Trích xuất nội dung bài báo (phương án 2) |
| newspaper3k | Trích xuất bài báo (phương án 3) |
| edge-tts | Microsoft Edge Text-to-Speech (async) |
| ddgs / duckduckgo-search | DuckDuckGo web search cho chatbot |

---

## AI Models & Định tuyến Tác vụ

| # | Model | Provider | Tham số | Tác vụ |
|---|-------|----------|---------|--------|
| 1 | `gemini-2.5-pro` | Open Claude | — | Dịch bài báo, phân tích ISO, tác vụ phức tạp |
| 2 | `gemini-3-pro-preview` | Open Claude | — | Chat, tác vụ mặc định |
| 3 | `gemini-3-flash-preview` | Open Claude | — | Tóm tắt tin tức (nhanh, tiết kiệm) |
| 4 | `Llama 3.1 70B Instruct Q4_K_M` | LocalAI | 70B | Fallback offline cho tất cả tác vụ |
| 5 | `SecurityLLM 7B Q4_K_M` | LocalAI | 7B | Audit bảo mật ISO (Pha 1, `iso_local`) |
| 6 | `envit5-translation` (VinAI) | HuggingFace / CPU | 135M | Dịch tiêu đề EN→VI (hoàn toàn offline) |
| 7 | `all-MiniLM-L6-v2` | sentence-transformers | 22M | Embedding cho ChromaDB + intent classifier |
| 8 | `vi-VN-HoaiMyNeural` (Edge-TTS) | Microsoft | — | Text-to-Speech tiếng Việt |

---

## Cài đặt Nhanh

### Yêu cầu
- Docker Engine + Docker Compose v2
- Tối thiểu 16 GB RAM (khuyến nghị 32 GB cho model 70B)
- 40 GB dung lượng đĩa trống

### 1. Clone & Setup
```bash
git clone https://github.com/NghiaDinh03/phobert-chatbot-project.git
cd phobert-chatbot-project
cp .env.example .env
```

### 2. Cấu hình `.env`
```env
# Cloud LLM chính — Open Claude (bắt buộc)
CLOUD_API_KEYS=your_key_1,your_key_2,your_key_3
CLOUD_LLM_API_URL=https://open-claude.com/v1
CLOUD_MODEL_NAME=gemini-3-pro-preview

# Bảo mật (thay đổi trong production)
JWT_SECRET=your-random-secret-here
CORS_ORIGINS=http://localhost:3000
```

### 3. Build & Chạy
```bash
docker-compose up --build -d
```

Lần đầu: tải GGUF models (~25–40 GB) và build images — khoảng 20–45 phút.

### 4. Truy cập
Mở **http://localhost:3000**

### 5. Tinh chỉnh Hiệu năng (tùy chọn)
```env
TORCH_THREADS=4           # Số luồng PyTorch cho dịch VinAI
MAX_CONCURRENT_REQUESTS=3 # Giới hạn AI chạy song song
INFERENCE_TIMEOUT=120     # Timeout LocalAI (giây)
CLOUD_TIMEOUT=60          # Timeout Open Claude (giây)
```

---

## Biến Môi trường

| Biến | Mặc định | Mô tả |
|------|---------|-------|
| `CLOUD_API_KEYS` | `` | Danh sách API key Open Claude (phân cách bằng dấu phẩy) |
| `CLOUD_LLM_API_URL` | `https://open-claude.com/v1` | URL Open Claude |
| `CLOUD_MODEL_NAME` | `gemini-3-pro-preview` | Model mặc định (định tuyến task có thể ghi đè) |
| `LOCALAI_URL` | `http://localai:8080` | URL LocalAI server |
| `MODEL_NAME` | `Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf` | Model LocalAI chính |
| `SECURITY_MODEL_NAME` | same as MODEL_NAME | Model security audit LocalAI |
| `CORS_ORIGINS` | `http://localhost:3000` | Origins CORS cho phép |
| `TORCH_THREADS` | `cpu_count()` | Số luồng PyTorch |
| `MAX_CONCURRENT_REQUESTS` | `3` | Giới hạn đồng thời |
| `INFERENCE_TIMEOUT` | `120` | Timeout LocalAI (giây) |
| `CLOUD_TIMEOUT` | `60` | Timeout Open Claude (giây) |
| `RATE_LIMIT_CHAT` | `10/minute` | Rate limit chat |
| `RATE_LIMIT_ASSESS` | `3/minute` | Rate limit đánh giá |
| `RATE_LIMIT_NEWS` | `5/minute` | Rate limit tóm tắt tin |
| `JWT_SECRET` | `change-me-in-production` | Khóa ký JWT |
| `DEBUG` | `false` | Bật logging DEBUG |

---

## Tài liệu

| Tài liệu | Ngôn ngữ | Mô tả |
|---------|----------|-------|
| [Architecture](./docs/architecture.md) | 🇬🇧 EN | Container, routing, AI orchestration |
| [Kiến trúc Hệ thống](./docs/architecture_vi.md) | 🇻🇳 VI | Container, routing, AI orchestration |
| [API Reference](./docs/api.md) | 🇬🇧 EN | Tất cả endpoints với schema |
| [Tài liệu API](./docs/api_vi.md) | 🇻🇳 VI | Tất cả endpoints với schema |
| [News Aggregator](./docs/news_aggregator.md) | 🇬🇧 EN | RSS, dịch, TTS flow |
| [Tổng hợp Tin tức](./docs/news_aggregator_vi.md) | 🇻🇳 VI | RSS, dịch, TTS flow |
| [Chatbot RAG](./docs/chatbot_rag.md) | 🇬🇧 EN | Hybrid routing, ChromaDB, web search |
| [Chatbot RAG](./docs/chatbot_rag_vi.md) | 🇻🇳 VI | Hybrid routing, ChromaDB, web search |
| [ISO Assessment](./docs/iso_assessment_form.md) | 🇬🇧 EN | Async pipeline đánh giá |
| [Form Đánh giá ISO](./docs/iso_assessment_form_vi.md) | 🇻🇳 VI | Async pipeline đánh giá |
| [Analytics](./docs/analytics_monitoring.md) | 🇬🇧 EN | Dashboard, system stats |
| [Analytics](./docs/analytics_monitoring_vi.md) | 🇻🇳 VI | Dashboard, system stats |
| [ChromaDB Guide](./docs/chromadb_guide.md) | 🇬🇧 EN | Vector store, thêm tài liệu |
| [Hướng dẫn ChromaDB](./docs/chromadb_guide_vi.md) | 🇻🇳 VI | Vector store, thêm tài liệu |
| [Deployment Guide](./docs/deployment.md) | 🇬🇧 EN | Setup, Docker, production |
| [Hướng dẫn Triển khai](./docs/deployment_vi.md) | 🇻🇳 VI | Setup, Docker, production |
| [Tiêu chuẩn Markdown RAG](./docs/markdown_rag_standard.md) | 🇻🇳 VI | Format .md tối ưu cho RAG |

---

## Hiệu năng Tham khảo

| Metric | Giá trị |
|--------|--------|
| Phản hồi chat (Open Claude) | ~2–5 giây |
| Phản hồi chat (LocalAI 70B, fallback) | ~30–90 giây |
| Dịch tiêu đề tin tức (batch 8) | ~3–8 giây |
| Cào bài + dịch + TTS (lần đầu) | ~15–40 giây |
| Phát audio (đã cache) | ~0 ms tức thì |
| Tìm kiếm vector ChromaDB (top-5) | < 100 ms |
| Context hội thoại | 10 tin nhắn gửi LLM, 20 lưu |
| TTL session | 24 giờ |
| TTL cache audio/summary | 7 ngày, tự xóa |
| Giới hạn bộ nhớ Docker | Backend: 6 GB, LocalAI: 12 GB, Frontend: 2 GB |

---

## License

Phần mềm độc quyền — xây dựng cho mục đích đánh giá an ninh mạng doanh nghiệp.
