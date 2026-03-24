# Chatbot RAG — Technical Deep Dive

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-Chatbot_RAG-blue?style=flat-square)](chatbot_rag.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Chatbot_RAG-red?style=flat-square)](chatbot_rag_vi.md)

</div>

---

## Table of Contents

1. [Overview](#1-overview)
2. [End-to-End Flow Diagram](#2-end-to-end-flow-diagram)
3. [Model Router — Hybrid Intent Classification](#3-model-router--hybrid-intent-classification)
4. [Route: Security — RAG Pipeline](#4-route-security--rag-pipeline)
5. [Route: Search — DuckDuckGo Web Search](#5-route-search--duckduckgo-web-search)
6. [Route: General — Direct LLM](#6-route-general--direct-llm)
7. [Session Memory](#7-session-memory)
8. [Cloud LLM Service](#8-cloud-llm-service)
9. [Streaming Chat](#9-streaming-chat)
10. [Frontend Implementation](#10-frontend-implementation)

---

## 1. Overview

The chatbot is a **context-aware AI assistant** specialized in cybersecurity and ISO 27001. Every user message passes through a **hybrid intent router** that decides how to answer:

| Route | Trigger | Mechanism |
|-------|---------|-----------|
| `security` | ISO / compliance / vulnerability questions | RAG: ChromaDB semantic search on `iso_documents` |
| `search` | News / current events / trend questions | Web search: DuckDuckGo via `ddgs` library |
| `general` | Conversation / general knowledge | Direct LLM call, no retrieval |

The AI backbone uses **Open Claude as primary** with **LocalAI as fallback** — no OpenRouter.

---

## 2. End-to-End Flow Diagram

```
User sends message
        │
        ▼
┌───────────────────────────────────────┐
│  POST /api/chat  or  /api/chat/stream │
│  { message, session_id }              │
└─────────────────┬─────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              ChatService.generate_response()             │
│                                                          │
│  1. SessionStore.get_context_messages(max=10)            │
│     → last 10 messages from /data/sessions/{id}.json     │
│                                                          │
│  2. ModelRouter.route_model(message)                     │
│     → Hybrid classify → route: security/search/general   │
│                                                          │
│  3. Branch on route:                                     │
│     security  → VectorStore.search(top_k=5)              │
│                 build RAG prompt with ISO context         │
│     search    → WebSearch.search(max=5)                  │
│                 build search prompt with web snippets     │
│     general   → build_general_prompt()                   │
│                                                          │
│  4. CloudLLMService.chat_completion(messages, task_type) │
│     → Open Claude primary → LocalAI fallback             │
│                                                          │
│  5. SessionStore.add_message(user + assistant)           │
│                                                          │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
           { response, route, model, provider }
```

---

## 3. Model Router — Hybrid Intent Classification

File: [`backend/services/model_router.py`](../backend/services/model_router.py)

### Step 1 — Semantic Classification (ChromaDB in-memory)

An in-memory ChromaDB collection called `intent_classifier` stores labelled example messages for each route. The router embeds the incoming message and finds the nearest example:

```python
collection = client.get_or_create_collection(
    name="intent_classifier",
    metadata={"hnsw:space": "cosine"}
)

result = collection.query(
    query_texts=[message],
    n_results=1
)
distance = result["distances"][0][0]
confidence = 1 - distance          # cosine → 0=identical, 1=orthogonal
```

If `confidence > 0.6` → use the matched route label.

### Step 2 — Keyword Fallback (when confidence ≤ 0.6)

```python
security_keywords = {
    "iso", "27001", "annex", "control", "compliance",
    "vulnerability", "patch", "firewall", "encryption",
    "audit", "risk", "threat", "incident", "policy"
}

search_keywords = {
    "news", "latest", "today", "recent", "current",
    "trend", "event", "announce", "release", "update"
}
```

Classification logic:

```
message_lower = message.lower().split()
if any(w in security_keywords for w in message_lower):
    route = "security"
elif any(w in search_keywords for w in message_lower):
    route = "search"
else:
    route = "general"
```

### Route Decision Table

```
Input: "What does ISO 27001 Annex A.9 say about access control?"
  → semantic confidence: 0.91  →  route: security  ✅

Input: "Latest news on ransomware attacks today"
  → semantic confidence: 0.44  →  keyword fallback
  → "latest", "today" match search_keywords  →  route: search  ✅

Input: "How do I write a Python function?"
  → semantic confidence: 0.28  →  keyword fallback
  → no matches  →  route: general  ✅
```

---

## 4. Route: Security — RAG Pipeline

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py)

### Vector Search

```python
results = vector_store.search(query=message, top_k=5)
# Returns: [{id, document, metadata, distance}, ...]
```

Each result's `document` field contains a header-context prefix:

```
[Context: # ISO 27001 > ## Annex A > ### A.9 Access Control]
A.9.1.1 Access control policy — An access control policy shall be
established, documented, approved by management, published and
communicated to employees and relevant external parties...
```

### Prompt Construction

```python
context = "\n\n---\n\n".join([r["document"] for r in results])

messages = [
    {
        "role": "system",
        "content": (
            "You are a cybersecurity expert specializing in ISO 27001. "
            "Answer using ONLY the provided context. "
            "If the context does not contain the answer, say so clearly.\n\n"
            f"CONTEXT:\n{context}"
        )
    },
    *history_messages,   # last 10 turns
    {
        "role": "user",
        "content": message
    }
]
```

### Multi-Query Search (optional)

For complex queries, `multi_query_search` generates 3 query variations, fetches results for each, then deduplicates by distance:

```python
queries = [
    message,
    f"ISO 27001 {message}",
    f"security control {message}"
]
all_results = []
for q in queries:
    all_results.extend(vector_store.search(q, top_k=3))
# deduplicate by id, keep lowest distance
```

---

## 5. Route: Search — DuckDuckGo Web Search

File: [`backend/services/web_search.py`](../backend/services/web_search.py)

### Search Execution

```python
from duckduckgo_search import DDGS

with DDGS() as ddgs:
    raw = list(ddgs.text(query, max_results=max_results))
```

### Retry Logic

```python
def search(query, max_results=5, retries=2):
    for attempt in range(retries):
        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
            if raw:
                return [{"title": r["title"], "body": r["body"], "href": r["href"]}
                        for r in raw]
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
    return []
```

### Context Formatting

```python
@staticmethod
def format_context(results):
    if not results:
        return "No web search results available."
    lines = ["## Web Search Results\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**[{i}] {r['title']}**")
        lines.append(r['body'])
        lines.append(f"Source: {r['href']}\n")
    return "\n".join(lines)
```

### Prompt for Search Route

```python
messages = [
    {
        "role": "system",
        "content": (
            "You are a helpful assistant. Use the following web search results "
            "to answer the user's question. Cite sources when relevant.\n\n"
            f"{WebSearch.format_context(results)}"
        )
    },
    *history_messages,
    { "role": "user", "content": message }
]
```

---

## 6. Route: General — Direct LLM

For general questions, no retrieval is done. The system prompt sets persona:

```python
messages = [
    {
        "role": "system",
        "content": (
            "You are a knowledgeable AI assistant specializing in "
            "cybersecurity, ISO 27001, and enterprise IT. "
            "Answer clearly and concisely."
        )
    },
    *history_messages,
    { "role": "user", "content": message }
]
```

---

## 7. Session Memory

File: [`backend/repositories/session_store.py`](../backend/repositories/session_store.py)

### Storage Structure

```
/data/sessions/
└── {session_id}.json
```

Each file contains:

```json
{
  "session_id": "user-abc123",
  "created_at": 1711270000.0,
  "updated_at": 1711270400.0,
  "messages": [
    { "role": "user",      "content": "What is ISO 27001?" },
    { "role": "assistant", "content": "ISO 27001 is an international standard..." }
  ]
}
```

### Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Max stored messages | 20 | Older messages are dropped when limit reached |
| Messages sent to LLM | 10 | Always `history[-10:]` |
| Session TTL | 86400 s (24 h) | Expired sessions cleaned on startup |
| Storage | File-based | Thread-safe with `threading.Lock()` |

### Context Window Management

```python
def get_context_messages(self, session_id: str, max_messages: int = 10):
    history = self.load(session_id).get("messages", [])
    return history[-max_messages:]   # sliding window, most recent first
```

### Thread Safety

All read/write operations use `self._lock = threading.Lock()` to prevent race conditions from concurrent requests modifying the same session file.

---

## 8. Cloud LLM Service

File: [`backend/services/cloud_llm_service.py`](../backend/services/cloud_llm_service.py)

### Fallback Chain

```
CloudLLMService.chat_completion(messages, task_type="chat")
        │
        ▼
  Tier 1: Open Claude (OPEN_CLAUDE_API_BASE)
  ┌────────────────────────────────────────┐
  │ model = TASK_MODEL_MAP[task_type]      │
  │ keys = OPEN_CLAUDE_API_KEY.split(",")  │
  │ key  = keys[_key_index % len(keys)]    │
  │ _key_index += 1  (round-robin)         │
  └──────────────┬─────────────────────────┘
                 │ timeout / 5xx / no keys
                 ▼
  Tier 2: LocalAI (LOCAL_AI_BASE_URL)
  ┌────────────────────────────────────────┐
  │ model = LOCAL_AI_MODEL                 │
  │ OpenAI-compatible /v1/chat/completions │
  └────────────────────────────────────────┘
```

### Chat-Specific Models

```python
TASK_MODEL_MAP = {
    "chat":    "gemini-3-pro-preview",   # standard chat messages
    "complex": "gemini-2.5-pro",         # routed when high-complexity detected
    "default": "gemini-3-pro-preview",
}
```

### Response Format

```python
{
    "content": "ISO 27001 Annex A.9 covers access control...",
    "model": "gemini-3-pro-preview",
    "provider": "open_claude",
    "usage": {
        "prompt_tokens": 842,
        "completion_tokens": 215,
        "total_tokens": 1057
    }
}
```

---

## 9. Streaming Chat

File: [`backend/api/routes/chat.py`](../backend/api/routes/chat.py)

### Endpoint

```
POST /api/chat/stream
Content-Type: application/json
→ text/event-stream
```

### Generator

```python
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(400, "Message cannot be empty")

    def event_generator():
        for chunk in ChatService.generate_response_stream(
            request.message, request.session_id
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Stream Events

```
data: {"chunk": "ISO "}
data: {"chunk": "27001 "}
data: {"chunk": "Annex A.9..."}
data: {"done": true, "session_id": "abc", "route": "security", "model": "gemini-2.5-pro"}
```

### Frontend Reader (chatbot/page.js)

```js
const res = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: text, session_id: sessionId })
})
const data = await res.json()
// full response arrives at once (non-streaming frontend path)
```

> The frontend (`chatbot/page.js`) currently uses the synchronous `/api/chat` endpoint. The streaming endpoint is available for future integration.

---

## 10. Frontend Implementation

File: [`frontend-next/src/app/chatbot/page.js`](../frontend-next/src/app/chatbot/page.js)

### State

```js
const [messages, setMessages] = useState([])   // chat display
const [sessions, setSessions] = useState([])   // sidebar session list
const [sessionId, setSessionId] = useState(null)
const [pending, setPending] = useState(false)
```

### Session Persistence (localStorage)

```js
// Key: "chatbot_sessions"
// Value: [{ id, preview, messages, ts }, ...]
function directSaveSession(sessionId, messages) {
    const entry = { id: sessionId, preview: messages[0]?.content, messages, ts: Date.now() }
    const sessions = lsGet("chatbot_sessions", [])
    // upsert by id, keep max 20 sessions
}
```

### Send Flow

```
user types + presses Enter
  → send(text)
      → append user message to UI
      → POST /api/chat { message: text, session_id }
      → await response
      → append bot message to UI
      → directSaveSession(sessionId, updatedMessages)
```

### Suggested Prompts

```js
const SUGGESTIONS = [
  "ISO 27001 Annex A controls overview",
  "How to implement access control policy?",
  "Latest cybersecurity threats",
  "What is a risk assessment process?",
  "Vietnam Cybersecurity Law 2018 overview"
]
```
