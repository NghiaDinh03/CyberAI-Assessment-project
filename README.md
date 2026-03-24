<div align="center">
  <h1>🛡️ CyberAI Assessment Platform v2.0</h1>
  <p>Enterprise ISO 27001 Assessment · RAG Chatbot · AI News Aggregator · Text-to-Speech</p>
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

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Feature Mechanism Flows](#feature-mechanism-flows)
  - [AI Chatbot (RAG + Web Search)](#1-ai-chatbot--rag--web-search)
  - [ISO 27001 / TCVN Assessment](#2-iso-27001--tcvn-assessment)
  - [News Aggregator + TTS](#3-news-aggregator--text-to-speech)
  - [Analytics Dashboard](#4-analytics-dashboard)
- [Tech Stack](#tech-stack)
- [AI Models & Task Routing](#ai-models--task-routing)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Documentation](#documentation)

---

## Overview

**CyberAI Assessment Platform** is a fully containerized, on-premise AI system for Vietnamese enterprises. It provides:

- **ISO 27001:2022 & TCVN 11930:2017 compliance assessment** — automated two-phase AI gap analysis with async background processing
- **RAG-powered AI Chatbot** — hybrid semantic + keyword routing with ChromaDB retrieval and optional DuckDuckGo web search
- **AI News Aggregator with TTS** — RSS aggregation, VinAI Vietnamese translation, and Edge-TTS audio generation with 2-tier AI fallback
- **Analytics Dashboard** — real-time system monitoring via `/host/proc/` filesystem, ChromaDB management, assessment history

All services run via `docker-compose up --build -d` with zero manual dependency setup.

---

## System Architecture

### Container Topology

```
Host Machine
│
├── :3000  ──► phobert-frontend  (Next.js 15)
│                  next.config.js rewrite:
│                  /api/:path* → http://backend:8000/api/:path*
│
├── :8000  ──► phobert-backend   (FastAPI / Python 3.11)
│                  ├── services/
│                  │   ├── cloud_llm_service.py  ← Open Claude primary
│                  │   ├── chat_service.py        ← RAG + web search + session
│                  │   ├── model_router.py        ← hybrid semantic+keyword router
│                  │   ├── summary_service.py     ← scrape + translate + TTS
│                  │   ├── news_service.py        ← RSS + background workers
│                  │   ├── translation_service.py ← VinAI EN→VI (CPU)
│                  │   └── web_search.py          ← DuckDuckGo search
│                  └── repositories/
│                      ├── vector_store.py        ← ChromaDB wrapper
│                      └── session_store.py       ← file-based sessions
│
└── :8080  ──► phobert-localai   (LocalAI GGUF server)
                   /models/Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf
                   /models/SecurityLLM-7B-Q4_K_M.gguf

Shared Volume:  ./data:/data
  data/
  ├── iso_documents/   ← .md knowledge base for ChromaDB
  ├── vector_store/    ← ChromaDB SQLite (collection: iso_documents)
  ├── summaries/       ← Article JSON cache (7-day TTL)
  │   └── audio/       ← Edge-TTS MP3 files
  ├── sessions/        ← Chat session JSON (24h TTL)
  ├── translations/    ← VinAI title translation cache
  ├── assessments/     ← ISO assessment reports (permanent)
  └── knowledge_base/  ← Static ISO/TCVN control definitions
```

### AI Fallback Chain

```
Task arrives → CloudLLMService.chat_completion()
    │
    ├── task_type == "iso_local"?
    │     └── LocalAI ONLY (SecurityLLM) → raise if fails
    │
    └── Cloud path:
          Open Claude (CLOUD_API_KEYS, round-robin)
            │ 429 → key cooldown 60s, try next key
            │ 401 → skip key (config issue, no cooldown)
            │ 404 → retry with CLOUD_MODEL_NAME default
            │ All keys exhausted?
            ▼
          LocalAI (http://localai:8080/v1/chat/completions)
            │ Timeout: INFERENCE_TIMEOUT (default 120s)
            │ Busy check: get_ai_status() ≠ "Đang rảnh" → raise
            ▼
          raise Exception("All AI providers failed")
```

### Task-Specific Model Routing

| Task type | Cloud model | Fallback |
|-----------|-------------|---------|
| `news_translate` | `gemini-2.5-pro` | LocalAI 70B |
| `news_summary` | `gemini-3-flash-preview` | LocalAI 70B |
| `iso_analysis` | `gemini-2.5-pro` | LocalAI SecurityLLM |
| `complex` | `gemini-2.5-pro` | LocalAI 70B |
| `chat` | `gemini-3-pro-preview` | LocalAI 70B |
| `iso_local` | — | LocalAI SecurityLLM only |
| `default` | `gemini-3-pro-preview` | LocalAI 70B |

---

## Feature Mechanism Flows

### 1. AI Chatbot — RAG + Web Search

```
User sends message → POST /api/chat  (or /api/chat/stream for SSE)
        │
        ▼
[model_router.py: route_model(message)]
  Hybrid classification:
  ┌─────────────────────────────────────────────────────────┐
  │ Step 1: Semantic (ChromaDB intent classifier)           │
  │   in-memory collection "intent_classifier"              │
  │   INTENT_TEMPLATES: security / search / general        │
  │   confidence > 0.6 → use semantic result               │
  │                                                         │
  │ Step 2: Keyword fallback (confidence ≤ 0.6)            │
  │   ISO_KEYWORDS → route=security, use_rag=True           │
  │   SEARCH_KEYWORDS → route=search, use_search=True       │
  │   else → route=general                                  │
  └─────────────────────────────────────────────────────────┘
        │
        ├── route=security → RAG retrieval
        │   VectorStore.search(message, top_k=5)
        │   Collection: "iso_documents" (ChromaDB)
        │   Returns chunks sorted by cosine similarity score
        │
        ├── route=search → DuckDuckGo web search
        │   WebSearch.search(query, max_results=5, region="vn-vi")
        │   Returns [{title, url, snippet}]
        │
        └── route=general → no external retrieval
        │
        ▼
[SessionStore: get_context_messages(session_id, max_messages=10)]
  Load last 10 messages from data/sessions/<session_id>.json
  TTL: 24h (SESSION_TTL = 86400s)
  MAX_HISTORY_PER_SESSION = 20 stored, 10 sent to LLM
        │
        ▼
[_build_messages(): system prompt + RAG/search context + history + user msg]
        │
        ▼
[CloudLLMService.chat_completion()]
  Open Claude → LocalAI fallback
  Returns: {content, model, provider, usage}
        │
        ▼
[Save to session + return response]
  {response, model, provider, route, rag_used, search_used,
   sources, web_sources, tokens}
```

**Streaming endpoint** (`POST /api/chat/stream`): SSE events in order:
`routing` → `rag` (if ISO) → `searching` (if search) → `thinking` → `done`

---

### 2. ISO 27001 / TCVN Assessment

```
User fills multi-step form → POST /api/iso27001/assess
  SystemInfo payload:
  { assessment_standard, org_name, servers, firewalls, vpn,
    cloud_provider, antivirus, siem, implemented_controls[],
    incidents_12m, employees, iso_status, notes }
        │
        ▼
[BackgroundTasks] — async, non-blocking
  assessment_id = uuid4()
  Saved to data/assessments/<id>.json with status="pending"
  Returns immediately: { id, status: "pending" }
        │
        ▼ (background)
[chat_service.py: assess_system(system_data)]
        │
        ▼
Phase 1: RAG Context
  VectorStore.search(standard-specific query, top_k=6)
  ISO 27001 → "A.5 Tổ chức, A.6 Nhân sự, A.7 Vật lý, A.8 Công nghệ"
  TCVN 11930 → "TCVN 11930 hệ thống thông tin cấp độ bảo đảm an toàn"
        │
        ▼
Phase 2: Security Audit (task_type="iso_local" → LocalAI SecurityLLM)
  Prompt: "Chuyên gia Auditor về {std}. Chỉ trả về danh sách phát hiện kỹ thuật thô."
  Input: RAG context + system_info_txt
  Compliance score: len(implemented_controls) / 93 (ISO) or /34 (TCVN)
        │
        ▼
Phase 3: Report Formatting (task_type="iso_analysis" → gemini-2.5-pro)
  Prompt: Format raw analysis into Vietnamese Markdown:
    1. ĐÁNH GIÁ TỔNG QUAN
    2. PHÂN TÍCH LỖ HỔNG (GAP ANALYSIS)
    3. KHUYẾN NGHỊ ƯU TIÊN (ACTION PLAN)
        │
        ▼
Saved to data/assessments/<id>.json with status="completed"
Frontend polls GET /api/iso27001/history to see result
```

**Supported standards:**

| Standard | Max score | Scoring |
|---------|----------|---------|
| ISO 27001:2022 | 93 controls | `len(implemented) / 93 × 100%` |
| TCVN 11930:2017 | 34 requirements | `len(implemented) / 34 × 100%` |

---

### 3. News Aggregator + Text-to-Speech

```
[Background worker: start_bg_worker()]
  feedparser.parse(rss_url) → 15 articles/category
  Categories:
  • cybersecurity         → The Hacker News, BleepingComputer, Dark Reading
  • stocks_international  → CNBC, Yahoo Finance, MarketWatch
  • stocks_vietnam        → CafeF, VnEconomy, VnExpress Finance

  ┌── Thread: _translation_worker()
  │   Queue: _translate_queue
  │   VinAI envit5-translation (135M, local CPU)
  │   Batch: 8 titles, torch.jit.optimize_for_inference()
  │   Cache: data/translations/<category>.json
  │
  └── Thread: _llama_worker()
      Queue: _llama_queue
      CloudLLMService.quick_completion() → article tagging
      Prompt: "Tag 1-2 keywords. No explanation."

User clicks ▶ Play → POST /api/news/summarize
        │
        ▼
[SummaryService._process_article_internal()]
  Cache check: MD5(url) → data/summaries/<hash>.json
        │ Cache hit → return {audio_url, summary_vi} immediately
        │ Cache miss ↓
        ▼
Scraping (3-method fallback):
  1. requests + BeautifulSoup4
  2. trafilatura
  3. newspaper3k
  Cap: 12,000 chars, noise filter, dedup
        │
        ▼
AI Translation (2-tier fallback):
  1. Open Claude (task_type="news_translate" → gemini-2.5-pro)
     OR (task_type="news_summary" → gemini-3-flash-preview)
     Round-robin CLOUD_API_KEYS, 60s cooldown on 429
  2. LocalAI Llama 3.1 70B (offline fallback)
  Prompt: full editorial rewrite in Vietnamese
  Preserves: CVEs, dates, names, statistics verbatim
  max_tokens: 16000
        │
        ▼
_fix_pronunciation(): DDoS→"Đi Đốt", VPN, SSL/TLS, ransomware...
        │
        ▼
Edge-TTS: voice="vi-VN-HoaiMyNeural" → data/summaries/audio/<hash>.mp3
Persist: data/summaries/<hash>.json (TTL: 7 days)
```

---

### 4. Analytics Dashboard

```
/analytics page
  │
  ├── GET /api/system/stats (every 5s)
  │     Reads /host/proc/stat, /host/proc/meminfo (host filesystem)
  │     CPU%, RAM used/total/%, disk%, uptime
  │
  ├── GET /api/system/ai-status
  │     CloudLLMService.health_check()
  │     → open_claude: {configured, url, model, task_routing, keys_count, status}
  │     → localai: {url, model, status}
  │
  ├── GET /api/iso27001/history
  │     Lists data/assessments/*.json
  │     Columns: id, status, standard, org_name, created_at
  │
  ├── GET /api/iso27001/chromadb/stats
  │     Collection "iso_documents": doc count, chunk count
  │
  ├── POST /api/iso27001/chromadb/search { query, n_results }
  │     VectorStore.search() → top-N chunks with score
  │
  └── POST /api/iso27001/chromadb/reload
        Drops collection → re-indexes all data/iso_documents/*.md
        Chunk size: 600 chars, overlap: 150 chars
        Header-aware: [Context: # > ## > ###] prepended to chunks
```

---

## Tech Stack

### Frontend

| Technology | Version | Role |
|-----------|---------|------|
| Next.js | 15.1 | App Router, SSR, `/api/*` rewrite proxy to backend |
| React | 19.0 | UI components, `useState` / `useEffect` / `useRef` |
| CSS Modules | — | Scoped styles with CSS custom properties (dark/light theme) |
| react-markdown | 9.0 | Render AI-generated markdown reports |
| remark-gfm | 4.0 | GitHub-flavored markdown (tables, task lists) |

### Backend

| Technology | Role |
|-----------|------|
| FastAPI 0.115 | Async REST API, StreamingResponse for chat SSE |
| Python 3.11 | Runtime |
| Pydantic v2 | Request/response validation schemas |
| slowapi | Per-endpoint rate limiting (chat: 10/min, assess: 3/min, news: 5/min) |
| httpx | Async HTTP client for Open Claude API calls |
| requests | Sync HTTP for LocalAI + article scraping |
| chromadb | Local vector database (SQLite backend) |
| sentence-transformers | `all-MiniLM-L6-v2` embedding model (384-dim) |
| transformers + torch | VinAI `envit5-translation` (135M params, CPU) |
| feedparser | RSS feed parsing |
| BeautifulSoup4 | Primary HTML scraper |
| trafilatura | Fallback article content extractor |
| newspaper3k | Last-resort article extractor |
| edge-tts | Microsoft Edge Text-to-Speech (async) |
| ddgs / duckduckgo-search | DuckDuckGo web search for chatbot |

### Infrastructure

| Component | Role |
|-----------|------|
| Docker + Docker Compose | Container orchestration |
| LocalAI | OpenAI-compatible local GGUF inference server |
| ChromaDB (SQLite) | On-disk vector database |
| Docker bridge network | Isolated inter-container networking (`phobert-network`) |
| Docker Volumes | `./data:/data` persistent storage |

---

## AI Models & Task Routing

| # | Model | Provider | Params | Tasks |
|---|-------|----------|--------|-------|
| 1 | `gemini-2.5-pro` | Open Claude | — | Translation, ISO analysis, complex tasks |
| 2 | `gemini-3-pro-preview` | Open Claude | — | Chat, default tasks |
| 3 | `gemini-3-flash-preview` | Open Claude | — | News summary (fast, cheap) |
| 4 | `Llama 3.1 70B Instruct Q4_K_M` | LocalAI | 70B | Cloud fallback for all tasks |
| 5 | `SecurityLLM 7B Q4_K_M` | LocalAI | 7B | ISO security audit (Phase 1, `iso_local`) |
| 6 | `envit5-translation` (VinAI) | HuggingFace / CPU | 135M | EN→VI title translation (fully offline) |
| 7 | `all-MiniLM-L6-v2` | sentence-transformers | 22M | Text embedding for ChromaDB + intent classifier |
| 8 | `vi-VN-HoaiMyNeural` (Edge-TTS) | Microsoft | — | Vietnamese Text-to-Speech |

---

## Quick Start

### Prerequisites
- Docker Engine + Docker Compose v2
- 16 GB RAM minimum (32 GB recommended for 70B model)
- 40 GB free disk space

### 1. Clone & Setup
```bash
git clone https://github.com/NghiaDinh03/phobert-chatbot-project.git
cd phobert-chatbot-project
cp .env.example .env
```

### 2. Configure `.env`
```env
# Primary Cloud LLM — Open Claude (required)
CLOUD_API_KEYS=your_key_1,your_key_2,your_key_3
CLOUD_LLM_API_URL=https://open-claude.com/v1
CLOUD_MODEL_NAME=gemini-3-pro-preview

# Security (change in production)
JWT_SECRET=your-random-secret-here
CORS_ORIGINS=http://localhost:3000
```

### 3. Build & Launch
```bash
docker-compose up --build -d
```

First run: downloads GGUF models (~25–40 GB) and builds images — allow 20–45 minutes.

### 4. Access
Open **http://localhost:3000**

### 5. Performance Tuning (optional)
```env
TORCH_THREADS=4           # PyTorch threads for VinAI translation
MAX_CONCURRENT_REQUESTS=3 # Semaphore limit for concurrent AI calls
INFERENCE_TIMEOUT=120     # LocalAI timeout in seconds
CLOUD_TIMEOUT=60          # Open Claude timeout in seconds
```

---

## Environment Variables

| Variable | Default | Description |
|---------|---------|-------------|
| `CLOUD_API_KEYS` | `` | Comma-separated Open Claude API keys (round-robin) |
| `CLOUD_LLM_API_URL` | `https://open-claude.com/v1` | Open Claude base URL |
| `CLOUD_MODEL_NAME` | `gemini-3-pro-preview` | Default cloud model (overridden by task routing) |
| `LOCALAI_URL` | `http://localai:8080` | LocalAI server URL |
| `MODEL_NAME` | `Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf` | LocalAI general model |
| `SECURITY_MODEL_NAME` | same as MODEL_NAME | LocalAI security audit model |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed CORS origins |
| `TORCH_THREADS` | `cpu_count()` | PyTorch thread count for translation |
| `MAX_CONCURRENT_REQUESTS` | `3` | Semaphore for concurrent AI requests |
| `INFERENCE_TIMEOUT` | `120` | LocalAI call timeout (seconds) |
| `CLOUD_TIMEOUT` | `60` | Open Claude call timeout (seconds) |
| `RATE_LIMIT_CHAT` | `10/minute` | Chat endpoint rate limit |
| `RATE_LIMIT_ASSESS` | `3/minute` | Assessment endpoint rate limit |
| `RATE_LIMIT_NEWS` | `5/minute` | News summarize rate limit |
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret |
| `DEBUG` | `false` | Enable DEBUG-level logging |

---

## Documentation

| Document | Language | Description |
|---------|----------|-------------|
| [Architecture](./docs/architecture.md) | 🇬🇧 EN | Container topology, routing, AI orchestration |
| [Kiến trúc Hệ thống](./docs/architecture_vi.md) | 🇻🇳 VI | Container topology, routing, AI orchestration |
| [API Reference](./docs/api.md) | 🇬🇧 EN | All endpoints with schemas |
| [Tài liệu API](./docs/api_vi.md) | 🇻🇳 VI | All endpoints with schemas |
| [News Aggregator](./docs/news_aggregator.md) | 🇬🇧 EN | RSS, translation, TTS flow |
| [Tổng hợp Tin tức](./docs/news_aggregator_vi.md) | 🇻🇳 VI | RSS, translation, TTS flow |
| [Chatbot RAG](./docs/chatbot_rag.md) | 🇬🇧 EN | Hybrid routing, ChromaDB, web search |
| [Chatbot RAG](./docs/chatbot_rag_vi.md) | 🇻🇳 VI | Hybrid routing, ChromaDB, web search |
| [ISO Assessment](./docs/iso_assessment_form.md) | 🇬🇧 EN | Async assessment pipeline |
| [Form Đánh giá ISO](./docs/iso_assessment_form_vi.md) | 🇻🇳 VI | Async assessment pipeline |
| [Analytics](./docs/analytics_monitoring.md) | 🇬🇧 EN | Dashboard, system stats |
| [Analytics](./docs/analytics_monitoring_vi.md) | 🇻🇳 VI | Dashboard, system stats |
| [ChromaDB Guide](./docs/chromadb_guide.md) | 🇬🇧 EN | Vector store, add documents |
| [Hướng dẫn ChromaDB](./docs/chromadb_guide_vi.md) | 🇻🇳 VI | Vector store, add documents |
| [Deployment Guide](./docs/deployment.md) | 🇬🇧 EN | Setup, Docker, production |
| [Hướng dẫn Triển khai](./docs/deployment_vi.md) | 🇻🇳 VI | Setup, Docker, production |
| [Markdown RAG Standard](./docs/markdown_rag_standard.md) | 🇻🇳 VI | Format .md files for optimal RAG |

---

## Performance Reference

| Metric | Value |
|--------|-------|
| Chat response (Open Claude) | ~2–5 seconds |
| Chat response (LocalAI 70B, fallback) | ~30–90 seconds |
| News title translation (batch 8) | ~3–8 seconds |
| Article scrape + translate + TTS (cold) | ~15–40 seconds |
| Audio playback (cached) | ~0 ms instant |
| ChromaDB vector search (top-5) | < 100 ms |
| Session context window | 10 messages sent to LLM, 20 stored |
| Session TTL | 24 hours |
| Audio/summary cache TTL | 7 days auto-cleanup |
| Docker memory limits | Backend: 6 GB, LocalAI: 12 GB, Frontend: 2 GB |

---

## License

Proprietary — built for enterprise cybersecurity assessment.
