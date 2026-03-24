# System Architecture

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-Architecture-blue?style=flat-square)](architecture.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Kiến_trúc-red?style=flat-square)](architecture_vi.md)

</div>

---

## Table of Contents

1. [Overview](#1-overview)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Container Layout (Docker Compose)](#3-container-layout-docker-compose)
4. [Frontend — Next.js 14](#4-frontend--nextjs-14)
5. [Backend — FastAPI](#5-backend--fastapi)
6. [AI Layer — Cloud LLM Service](#6-ai-layer--cloud-llm-service)
7. [Model Router — Hybrid Intent Classification](#7-model-router--hybrid-intent-classification)
8. [Vector Store — ChromaDB](#8-vector-store--chromadb)
9. [Session Store](#9-session-store)
10. [Data Flow Summary](#10-data-flow-summary)

---

## 1. Overview

This platform is a multi-feature AI enterprise application with three core modules:

| Module | Description |
|--------|-------------|
| **AI News Aggregator** | RSS ingestion → scrape → Cloud LLM translate → Edge-TTS audio |
| **RAG Chatbot** | Hybrid routing → ChromaDB RAG / DuckDuckGo search / general LLM |
| **ISO 27001 Assessor** | System info form → async BackgroundTask → AI gap analysis |

All three modules share:
- A single **FastAPI** backend (Python 3.11)
- A single **Next.js 14** frontend (React, App Router)
- The same **Cloud LLM Service** (`CloudLLMService`) for all AI calls
- The same **ChromaDB** vector store for ISO knowledge retrieval

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER BROWSER / CLIENT                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / HTTP
┌──────────────────────────▼──────────────────────────────────┐
│              NEXT.JS 14  (Port 3000)                        │
│  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ /chatbot │ │ /news  │ │/form-iso │ │  /analytics      │ │
│  └──────────┘ └────────┘ └──────────┘ └──────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │    Next.js API Routes  (/app/api/*)  — proxy layer     │ │
│  └────────────────────────┬───────────────────────────────┘ │
└─────────────────────────  │  ──────────────────────────────-┘
                           │ HTTP (internal Docker network)
┌──────────────────────────▼──────────────────────────────────┐
│              FASTAPI BACKEND  (Port 8000)                   │
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
│  │   Open Claude (primary) → LocalAI (fallback)          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────┐   ┌───────────────────────────────┐  │
│  │  ChromaDB        │   │  SessionStore (file-based)    │  │
│  │  (iso_documents) │   │  /data/sessions/              │  │
│  └──────────────────┘   └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│            /host/proc   (read-only bind mount)               │
│   /host/proc/stat · /host/proc/meminfo · /proc/uptime        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Container Layout (Docker Compose)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./data:/data                      # persistent data
      - /proc:/host/proc:ro               # system stats

  frontend:
    build: ./frontend-next
    ports: ["3000:3000"]
    depends_on: [backend]
    environment:
      - BACKEND_URL=http://backend:8000   # internal Docker DNS
```

**Key volumes:**

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `./data` | `/data` | Articles, sessions, summaries, audio, assessments, vector_store |
| `/proc` | `/host/proc` (read-only) | CPU/memory stats for system monitoring |

---

## 4. Frontend — Next.js 14

```
frontend-next/src/
├── app/
│   ├── layout.js              # Root layout (ThemeProvider, Navbar)
│   ├── page.js                # Landing dashboard
│   ├── chatbot/page.js        # RAG Chatbot UI
│   ├── news/page.js           # News Aggregator UI
│   ├── form-iso/page.js       # ISO 27001 Assessment Form
│   ├── analytics/page.js      # Assessment history + ChromaDB explorer
│   ├── templates/page.js      # Standard templates picker
│   └── api/                   # Next.js proxy routes → backend
│       ├── chat/route.js
│       ├── news/route.js
│       ├── news/history/route.js
│       ├── news/reprocess/route.js
│       └── news/search/route.js
├── components/
│   ├── Navbar.js              # Clock (3 timezones), theme toggle, nav
│   ├── SystemStats.js         # CPU / RAM / Disk / Uptime widget
│   └── ThemeProvider.js       # Dark/light CSS variable switcher
```

### Next.js API Proxy

The frontend proxy layer (`/app/api/`) rewrites all `/api/*` requests to the FastAPI backend using the `BACKEND_URL` environment variable. This prevents CORS issues in production:

```js
// next.config.js — rewrite rule
{ source: '/api/:path*', destination: `${BACKEND_URL}/api/:path*` }
```

---

## 5. Backend — FastAPI

```
backend/
├── main.py                    # App factory, CORS, middleware, startup
├── core/config.py             # Settings (env vars, API keys)
├── api/routes/
│   ├── chat.py                # POST /api/chat, POST /api/chat/stream, GET /api/chat/history/:id
│   ├── news.py                # GET /api/news, POST /api/news/summarize, ...
│   ├── iso27001.py            # POST /api/iso27001/assess (async), GET results
│   └── system.py             # GET /api/system/stats, GET /api/system/cache-stats
├── services/
│   ├── chat_service.py        # Conversation orchestrator
│   ├── cloud_llm_service.py   # Open Claude + LocalAI
│   ├── model_router.py        # Hybrid intent router (3 routes)
│   ├── news_service.py        # RSS + in-memory cache + worker queues
│   ├── summary_service.py     # Scrape + translate + TTS pipeline
│   ├── web_search.py          # DuckDuckGo search (ddgs)
│   ├── translation_service.py # Bulk title translation cache
│   └── rag_service.py        # RAG query builder
├── repositories/
│   ├── vector_store.py        # ChromaDB wrapper (iso_documents)
│   └── session_store.py      # File-based session persistence
└── utils/
    ├── helpers.py
    └── logger.py
```

### Startup Sequence (`main.py`)

```python
@app.on_event("startup")
def on_startup():
    settings.validate()           # Check required env vars
    VectorStore().ensure_indexed() # Index ISO docs → ChromaDB if needed
    SessionStore().cleanup_expired()
```

### Middleware

| Middleware | Detail |
|-----------|--------|
| CORS | Origins: `*` (configurable) |
| Request size limit | 10 MB max body |
| 404 / 500 handlers | JSON error responses |

---

## 6. AI Layer — Cloud LLM Service

File: [`backend/services/cloud_llm_service.py`](../backend/services/cloud_llm_service.py)

### 2-Tier Fallback Chain

```
Request
   │
   ▼
┌──────────────────────────────────────────┐
│  Tier 1 — Open Claude (primary)          │
│  Endpoint: OPEN_CLAUDE_API_BASE          │
│  Auth: OPEN_CLAUDE_API_KEY (round-robin) │
└──────────────────────┬───────────────────┘
                       │ FAIL (timeout / 5xx / no keys)
                       ▼
┌──────────────────────────────────────────┐
│  Tier 2 — LocalAI (fallback)             │
│  Endpoint: LOCAL_AI_BASE_URL             │
│  Model: LOCAL_AI_MODEL                   │
└──────────────────────────────────────────┘
```

> ⚠️ **No OpenRouter.** The project uses only these two tiers.

### Task-Specific Model Map

```python
TASK_MODEL_MAP = {
    "news_translate": "gemini-2.5-pro",          # Full article translation
    "news_summary":   "gemini-3-flash-preview",  # Quick summary generation
    "iso_analysis":   "gemini-2.5-pro",          # ISO gap analysis
    "complex":        "gemini-2.5-pro",           # Complex chat queries
    "chat":           "gemini-3-pro-preview",     # Standard chat
    "default":        "gemini-3-pro-preview",     # Fallback default
}

LOCAL_ONLY_TASKS = {"iso_local"}  # Routes exclusively to LocalAI
```

### Round-Robin Key Rotation

```python
OPEN_CLAUDE_API_KEY=key1,key2,key3,...   # comma-separated in .env
# Each request uses: keys[_key_index % len(keys)]
# _key_index increments on every call → automatic load balancing
```

### Special Token Cleanup

After every LLM response, Llama-format artifacts are stripped:

```python
summary_vi = summary_vi.replace("<|eot_id|>", "")
summary_vi = summary_vi.replace("<|end_header_id|>", "")
if summary_vi.lower().startswith("assistant"):
    summary_vi = summary_vi[len("assistant"):].strip()
```

---

## 7. Model Router — Hybrid Intent Classification

File: [`backend/services/model_router.py`](../backend/services/model_router.py)

### Routes

| Route | Trigger | Action |
|-------|---------|--------|
| `security` | ISO/security keywords or semantic match | Load ISO context from ChromaDB → RAG response |
| `search` | Search/news/trend keywords | DuckDuckGo web search → inject results as context |
| `general` | Everything else | Direct LLM response (no retrieval) |

### Classification Flow

```
User message
     │
     ▼
┌────────────────────────────────────────────────┐
│  Step 1: Semantic Classification               │
│  ChromaDB in-memory collection: intent_classifier│
│  Model: sentence-transformers (cosine distance)│
│  Confidence threshold: 0.6                     │
└──────────────────┬─────────────────────────────┘
                   │
         confidence > 0.6?
        /               \
      YES                NO
       │                  │
       ▼                  ▼
  Use semantic       Step 2: Keyword fallback
  route result       ┌────────────────────────┐
                     │ security_keywords set  │
                     │ search_keywords set    │
                     │ → match → assign route │
                     └────────────────────────┘
                              │
                     no match → "general"
```

---

## 8. Vector Store — ChromaDB

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py)

### Configuration

| Parameter | Value |
|-----------|-------|
| Collection name | `iso_documents` |
| Distance metric | cosine |
| Chunk size | 600 characters |
| Chunk overlap | 150 characters |
| Persist directory | `/data/vector_store` |

### Header-Aware Chunking

Documents are split with markdown hierarchy preserved:

```python
# Each chunk gets a context prefix:
"[Context: # ISO 27001 > ## Annex A > ### A.9 Access Control]"

# Example chunk:
"[Context: # ISO 27001 > ## Annex A > ### A.9]\n"
"A.9.1.1 Access control policy — An access control policy..."
```

### Indexed Documents

Source: `data/iso_documents/`

| File | Content |
|------|---------|
| `iso27001_annex_a.md` | Full Annex A controls |
| `assessment_criteria.md` | Assessment scoring criteria |
| `checklist_danh_gia_he_thong.md` | System evaluation checklist |
| `luat_an_ninh_mang_2018.md` | Vietnam Cybersecurity Law 2018 |
| `network_infrastructure.md` | Network security guidelines |
| `nghi_dinh_13_2023_bvdlcn.md` | Decree 13/2023 on personal data |
| `tcvn_11930_2017.md` | TCVN 11930:2017 standard |

### Search API

```python
results = vector_store.search(query, top_k=5)
# Returns: [{id, document, metadata, distance}, ...]

results = vector_store.multi_query_search(query, top_k=5)
# Generates 3 query variations → merges → deduplicates by distance
```

---

## 9. Session Store

File: [`backend/repositories/session_store.py`](../backend/repositories/session_store.py)

```
/data/sessions/
└── {session_id}.json    ← one file per conversation
```

| Parameter | Value |
|-----------|-------|
| Storage format | JSON file per session |
| TTL | 86400 seconds (24 hours) |
| Max messages stored | 20 per session |
| Messages sent to LLM | Last 10 (`history[-10:]`) |
| Cleanup | On startup + periodic |

```python
def get_context_messages(self, session_id: str, max_messages: int = 10):
    history = self.load(session_id).get("messages", [])
    return history[-max_messages:]   # Always last 10
```

---

## 10. Data Flow Summary

### Chat Request

```
POST /api/chat  { message, session_id }
  → ChatService.generate_response()
      → ModelRouter.route_model(message)        # hybrid classify
          ├─ route=security  → VectorStore.search() → build_rag_prompt()
          ├─ route=search    → WebSearch.search()   → build_search_prompt()
          └─ route=general   → build_general_prompt()
      → SessionStore.get_context_messages()     # last 10 messages
      → CloudLLMService.chat_completion()       # Open Claude → LocalAI
      → SessionStore.add_message()              # persist exchange
  ← { response, session_id, route, model, provider }
```

### News Article Pipeline

```
GET /api/news?category=cybersecurity
  → NewsService.get_news()
      → _parse_rss() × 3 sources         # TheHackerNews, DarkReading, SecurityWeek
      → SummaryService._get_cache()      # check existing audio/summary
      → _apply_translations()            # load title_vi from translation cache
      → _update_history()                # persist to /data/articles_history.json
      → _llama_queue.put()               # enqueue background processing

POST /api/news/summarize  { url, lang, title }
  → SummaryService.process_article()     # locked per-URL
      Step 1: scrape_article()           # requests-bs4 → trafilatura → newspaper3k
      Step 2: CloudLLMService.chat_completion(task_type="news_translate")
              → gemini-2.5-pro (via Open Claude)
              → strip AI artifacts (*, #, <|eot_id|>, ...)
      Step 3: edge_tts.Communicate("vi-VN-HoaiMyNeural").save(audio_path)
  ← { audio_url, summary_vi, title_vi }
```

### ISO 27001 Assessment

```
POST /api/iso27001/assess  { system_info, controls, standard_id }
  → generate assessment_id = uuid4()
  → save JSON { id, status:"pending", data }
  → BackgroundTasks.add_task(process_assessment_bg, assessment_id)
  ← 202 { id, status:"pending" }   ← immediate response

[Background Thread]
  → ChatService.assess_system()
      → VectorStore.search(query, top_k=5)  # relevant ISO controls
      → CloudLLMService.chat_completion(task_type="iso_analysis")
         → gemini-2.5-pro (via Open Claude)
  → save JSON { id, status:"done", result }

GET /api/iso27001/assessments/{id}
  ← { id, status:"pending"|"done", result? }
```
