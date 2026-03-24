# API Reference

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-API_Reference-blue?style=flat-square)](api.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Tài_liệu_API-red?style=flat-square)](api_vi.md)

</div>

---

## Table of Contents

1. [Base URL & Conventions](#1-base-url--conventions)
2. [Chat Endpoints](#2-chat-endpoints)
3. [News Endpoints](#3-news-endpoints)
4. [ISO 27001 Endpoints](#4-iso-27001-endpoints)
5. [System Endpoints](#5-system-endpoints)
6. [Error Responses](#6-error-responses)
7. [Next.js Proxy Layer](#7-nextjs-proxy-layer)

---

## 1. Base URL & Conventions

| Environment | Base URL |
|-------------|----------|
| Local Docker | `http://localhost:8000` |
| Internal Docker network | `http://backend:8000` |
| Frontend proxy (Next.js) | `/api` (forwarded to backend) |

**Common headers:**

```http
Content-Type: application/json
```

**Response envelope (success):**

```json
{ "field1": "...", "field2": "..." }
```

**Response envelope (error):**

```json
{ "detail": "Human-readable error message" }
```

---

## 2. Chat Endpoints

### `POST /api/chat`

Synchronous chat response. Returns complete AI reply.

**Request body:**

```json
{
  "message": "What are the ISO 27001 access control requirements?",
  "session_id": "user-abc123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ | User message (trimmed, must be non-empty) |
| `session_id` | string | ❌ | Session ID for conversation continuity. Defaults to `"default"` |

**Response:**

```json
{
  "response": "ISO 27001 Annex A.9 Access Control requires...",
  "session_id": "user-abc123",
  "route": "security",
  "model": "gemini-2.5-pro",
  "provider": "open_claude"
}
```

| Field | Description |
|-------|-------------|
| `response` | AI-generated reply |
| `session_id` | Echo of the session ID used |
| `route` | Router decision: `security` / `search` / `general` |
| `model` | Model name actually used |
| `provider` | `open_claude` or `localai` |

---

### `POST /api/chat/stream`

Streaming chat via **Server-Sent Events (SSE)**. Each chunk arrives as a separate event.

**Request body:** Same as `POST /api/chat`

**Response:** `text/event-stream`

```
data: {"chunk": "ISO 27001 "}
data: {"chunk": "Annex A.9 "}
data: {"chunk": "Access Control..."}
data: {"done": true, "session_id": "user-abc123", "route": "security"}
```

**Event types:**

| Field | Description |
|-------|-------------|
| `chunk` | Text fragment to append to UI |
| `done` | `true` signals end of stream; includes metadata |
| `error` | Error message string if generation failed |

**Usage example (JavaScript):**

```js
const res = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message, session_id })
})
const reader = res.body.getReader()
// read chunks in loop...
```

---

### `GET /api/chat/history/{session_id}`

Retrieve full conversation history for a session.

**Path parameter:** `session_id` — session identifier string

**Response:**

```json
{
  "session_id": "user-abc123",
  "messages": [
    { "role": "user",      "content": "Hello" },
    { "role": "assistant", "content": "Hi! How can I help?" }
  ],
  "count": 2
}
```

> **Note:** Up to 20 messages are stored per session (TTL: 24 hours). Only the most recent 10 are sent to the LLM on each request.

---

## 3. News Endpoints

### `GET /api/news`

Fetch categorized news articles (with cache TTL of 15 minutes).

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `category` | string | `cybersecurity` | One of: `cybersecurity`, `stocks_vietnam`, `stocks_international` |
| `limit` | int | `15` | Max articles to return (1–50) |

**Response:**

```json
{
  "articles": [
    {
      "url": "https://thehackernews.com/2025/...",
      "title": "Critical Zero-Day in...",
      "title_vi": "Lỗ hổng Zero-Day nghiêm trọng trong...",
      "date": "2025-03-24T08:00:00",
      "source": "The Hacker News",
      "icon": "🔓",
      "lang": "en",
      "category": "cybersecurity",
      "audio_cached": true,
      "summary_text": "Tóm tắt: Nhóm hacker APT..."
    }
  ],
  "category": "cybersecurity",
  "count": 15,
  "sources": ["The Hacker News", "Dark Reading", "SecurityWeek"],
  "cached_at": "09:30:00 24/03/2025"
}
```

**RSS Sources per category:**

| Category | Sources |
|----------|---------|
| `cybersecurity` | The Hacker News, Dark Reading, SecurityWeek |
| `stocks_international` | CNBC Markets, MarketWatch, Yahoo Finance |
| `stocks_vietnam` | Znews Kinh doanh, VnExpress Kinh doanh, VnEconomy |

---

### `GET /api/news/history`

Retrieve the full article processing history (persisted in `/data/articles_history.json`).

**Response:**

```json
[
  {
    "url": "https://...",
    "title": "...",
    "title_vi": "...",
    "audio_cached": true,
    "summary_text": "...",
    "category": "cybersecurity",
    "added_at": "2025-03-24T08:00:00"
  }
]
```

---

### `GET /api/news/ai-status`

Returns the current AI processing status string.

**Response:**

```json
{ "status": "Đang dịch bài: Critical Zero-Day..." }
```

Possible values: `"Đang rảnh"` (idle) or a descriptive processing message.

---

### `GET /api/news/search`

Full-text search across all cached articles.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | — | Search query (required) |
| `limit` | int | `20` | Max results |

**Response:**

```json
{
  "results": [{ "url": "...", "title": "...", "title_vi": "..." }],
  "count": 3,
  "query": "ransomware"
}
```

---

### `GET /api/news/all`

Fetch articles from all three categories combined.

**Query parameter:** `limit` (int, 1–30, default 10)

---

### `POST /api/news/summarize`

Trigger on-demand article summarization: scrape → translate → TTS audio.

**Request body:**

```json
{
  "url": "https://thehackernews.com/2025/...",
  "lang": "en",
  "title": "Critical Zero-Day..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | ✅ | Article URL |
| `lang` | string | ✅ | `"en"` (translate) or `"vi"` (editorial rewrite) |
| `title` | string | ❌ | Original title (used as fallback if scraping fails) |

**Response (success):**

```json
{
  "audio_url": "/api/news/audio/a7c3e259.mp3",
  "summary_vi": "Tóm tắt nội dung bài báo bằng tiếng Việt...",
  "title_vi": "Tiêu đề bài báo dạng tiếng Việt"
}
```

**Response (error):**

```json
{
  "error": "❌ Trang thehackernews.com chặn truy cập bot. Sẽ tự động thử lại sau.",
  "retryable": true
}
```

**Internal pipeline:**

```
Step 1: scrape_article(url)
         requests+BeautifulSoup → trafilatura → newspaper3k
         (truncated at 30,000 chars)
Step 2: CloudLLMService.chat_completion(task_type="news_translate")
         → gemini-2.5-pro (Open Claude primary)
         → strip AI artifacts
Step 3: edge_tts.Communicate("vi-VN-HoaiMyNeural").save(mp3)
```

---

### `POST /api/news/reprocess`

Force reprocessing of an article (clears cache entry, re-runs pipeline).

**Request body:**

```json
{ "url": "https://..." }
```

---

### `GET /api/news/audio/{filename}`

Stream MP3 audio file.

**Path parameter:** `filename` — hash-based `.mp3` filename

**Response:** `audio/mpeg` stream

---

### `POST /api/news/clear-cache`

Clears the in-memory news cache (forces fresh RSS fetch on next request).

---

## 4. ISO 27001 Endpoints

### `POST /api/iso27001/assess`

Submit an ISO 27001 system assessment. Returns immediately with a pending job ID. Processing runs in a **background task**.

**Request body:**

```json
{
  "company_name": "ACME Corp",
  "industry": "Finance",
  "system_description": "Core banking application...",
  "controls": ["A.5.1", "A.6.1", "A.9.1"],
  "standard_id": "iso27001_2022",
  "firewall": "yes",
  "antivirus": "yes",
  "backup": "partial",
  "patch_management": "no",
  "incident_response": "no",
  "access_control": "yes",
  "encryption": "partial",
  "employee_training": "no",
  "physical_security": "yes",
  "risk_assessment": "no"
}
```

**Response (immediate — HTTP 202):**

```json
{
  "id": "7e0b008d-34d9-4c5b-bf9a-f3de2d53658e",
  "status": "pending"
}
```

**Background task execution:**

```
process_assessment_bg(assessment_id)
  → load JSON from /data/assessments/{id}.json
  → ChatService.assess_system(system_data)
      → VectorStore.search(relevant ISO controls, top_k=5)
      → CloudLLMService.chat_completion(task_type="iso_analysis")
         → gemini-2.5-pro (via Open Claude)
  → save { status:"done", result:{...} } to JSON
```

---

### `GET /api/iso27001/assessments/{assessment_id}`

Poll the status of an assessment job.

**Response (pending):**

```json
{ "id": "7e0b008d-...", "status": "pending" }
```

**Response (done):**

```json
{
  "id": "7e0b008d-...",
  "status": "done",
  "result": {
    "overall_score": 62,
    "compliance_level": "Partial",
    "gaps": ["No patch management process", "No incident response plan"],
    "recommendations": ["Implement automated patch management...", "..."],
    "control_analysis": { "A.9.1": { "status": "compliant", "notes": "..." } }
  }
}
```

---

### `DELETE /api/iso27001/assessments/{assessment_id}`

Delete an assessment record.

**Response:** `{ "deleted": true }`

---

### `POST /api/iso27001/reindex`

Re-index ISO documents into ChromaDB (drops and rebuilds collection).

**Response:** `{ "status": "ok", "indexed": 42 }`

---

### `GET /api/iso27001/chromadb/stats`

Return ChromaDB collection statistics.

**Response:**

```json
{
  "collection": "iso_documents",
  "count": 312,
  "persist_dir": "/data/vector_store",
  "metadata": { "hnsw:space": "cosine" }
}
```

---

### `POST /api/iso27001/chromadb/search`

Semantic search against the ISO knowledge base.

**Request body:**

```json
{ "query": "access control policy", "top_k": 5 }
```

**Response:**

```json
{
  "results": [
    {
      "id": "iso27001_annex_a_chunk_42",
      "document": "[Context: # ISO 27001 > ## Annex A > ### A.9]\nA.9.1.1 Access control policy...",
      "metadata": { "source": "iso27001_annex_a.md", "chunk_index": 42 },
      "distance": 0.12
    }
  ]
}
```

---

## 5. System Endpoints

### `GET /api/system/stats`

Real-time system resource usage. Reads directly from `/host/proc/stat` and `/host/proc/meminfo` (host filesystem mounted read-only into container).

**Response:**

```json
{
  "cpu": {
    "percent": 23.5,
    "model": "Intel(R) Core(TM) i7-10700K",
    "cores": 8
  },
  "memory": {
    "total": 16777216,
    "used": 8234567,
    "percent": 49.1
  },
  "disk": {
    "total": 512000000,
    "used": 189000000,
    "percent": 36.9
  },
  "uptime": 432000
}
```

**CPU % calculation method:**

```python
# Reads /host/proc/stat twice (100ms apart)
# Computes delta: (non-idle ticks / total ticks) × 100
```

---

### `GET /api/system/cache-stats`

Returns cache directory sizes and summary counts.

**Response:**

```json
{
  "summaries": { "count": 54, "size_bytes": 2340000 },
  "audio": { "count": 54, "size_bytes": 98000000 },
  "sessions": { "count": 12, "size_bytes": 45000 },
  "assessments": { "count": 3, "size_bytes": 12000 }
}
```

---

## 6. Error Responses

| HTTP Code | Meaning | Example |
|-----------|---------|---------|
| `400` | Bad request / validation error | `{ "detail": "Message cannot be empty" }` |
| `404` | Not found | `{ "detail": "Assessment not found" }` |
| `422` | Unprocessable entity (Pydantic) | `{ "detail": [{ "loc": ["body","url"], "msg": "field required" }] }` |
| `500` | Internal server error | `{ "detail": "Internal server error" }` |

---

## 7. Next.js Proxy Layer

The frontend includes API route files under `frontend-next/src/app/api/` that proxy requests to the backend. This allows the browser to call `/api/*` without exposing the backend URL or hitting CORS restrictions.

| Frontend route | Proxies to |
|----------------|-----------|
| `POST /api/chat` | `POST http://backend:8000/api/chat` |
| `GET /api/news` | `GET http://backend:8000/api/news` |
| `GET /api/news/history` | `GET http://backend:8000/api/news/history` |
| `POST /api/news/summarize` | `POST http://backend:8000/api/news/summarize` |
| `POST /api/news/reprocess` | `POST http://backend:8000/api/news/reprocess` |
| `GET /api/news/search` | `GET http://backend:8000/api/news/search` |
| `POST /api/iso27001/assess` | `POST http://backend:8000/api/iso27001/assess` |
| `GET /api/iso27001/assessments/:id` | `GET http://backend:8000/api/iso27001/assessments/:id` |
| `POST /api/iso27001/chromadb/search` | `POST http://backend:8000/api/iso27001/chromadb/search` |

> **Note:** `/api/chat/stream` is called directly via `fetch` with a streaming reader; no Next.js proxy route wraps it.
