# Chatbot RAG — Phân Tích Kỹ Thuật

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-Chatbot_RAG-blue?style=flat-square)](chatbot_rag.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Chatbot_RAG-red?style=flat-square)](chatbot_rag_vi.md)

</div>

---

## Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Sơ Đồ Luồng Đầu Cuối](#2-sơ-đồ-luồng-đầu-cuối)
3. [Model Router — Phân Loại Intent Hybrid](#3-model-router--phân-loại-intent-hybrid)
4. [Route Security — Pipeline RAG](#4-route-security--pipeline-rag)
5. [Route Search — Tìm Kiếm DuckDuckGo](#5-route-search--tìm-kiếm-duckduckgo)
6. [Route General — LLM Trực Tiếp](#6-route-general--llm-trực-tiếp)
7. [Session Memory](#7-session-memory)
8. [Cloud LLM Service](#8-cloud-llm-service)
9. [Streaming Chat](#9-streaming-chat)
10. [Triển Khai Frontend](#10-triển-khai-frontend)

---

## 1. Tổng Quan

Chatbot là **trợ lý AI nhận biết ngữ cảnh** chuyên về bảo mật thông tin và ISO 27001. Mỗi tin nhắn người dùng đi qua **hybrid intent router** để quyết định cách trả lời:

| Route | Điều kiện kích hoạt | Cơ chế |
|-------|---------------------|--------|
| `security` | Câu hỏi về ISO / tuân thủ / lỗ hổng | RAG: Tìm kiếm ngữ nghĩa ChromaDB trên `iso_documents` |
| `search` | Câu hỏi về tin tức / sự kiện hiện tại / xu hướng | Tìm web: DuckDuckGo qua thư viện `ddgs` |
| `general` | Hội thoại / kiến thức tổng quát | Gọi LLM trực tiếp, không truy xuất |

Backbone AI sử dụng **Open Claude làm chính** với **LocalAI làm dự phòng** — không có OpenRouter.

---

## 2. Sơ Đồ Luồng Đầu Cuối

```
Người dùng gửi tin nhắn
          │
          ▼
┌─────────────────────────────────────────────────┐
│  POST /api/chat  hoặc  /api/chat/stream          │
│  { message, session_id }                         │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│              ChatService.generate_response()              │
│                                                           │
│  1. SessionStore.get_context_messages(max=10)             │
│     → 10 tin nhắn gần nhất từ /data/sessions/{id}.json   │
│                                                           │
│  2. ModelRouter.route_model(message)                      │
│     → Phân loại hybrid → route: security/search/general  │
│                                                           │
│  3. Rẽ nhánh theo route:                                  │
│     security  → VectorStore.search(top_k=5)               │
│                 xây dựng RAG prompt với context ISO        │
│     search    → WebSearch.search(max=5)                   │
│                 xây dựng search prompt với kết quả web    │
│     general   → build_general_prompt()                    │
│                                                           │
│  4. CloudLLMService.chat_completion(messages, task_type)  │
│     → Open Claude chính → LocalAI dự phòng               │
│                                                           │
│  5. SessionStore.add_message(user + assistant)            │
│                                                           │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
          { response, route, model, provider }
```

---

## 3. Model Router — Phân Loại Intent Hybrid

File: [`backend/services/model_router.py`](../backend/services/model_router.py)

### Bước 1 — Phân Loại Ngữ Nghĩa (ChromaDB in-memory)

Collection ChromaDB in-memory tên `intent_classifier` lưu các tin nhắn mẫu đã được gán nhãn cho mỗi route. Router nhúng tin nhắn đến và tìm ví dụ gần nhất:

```python
collection = client.get_or_create_collection(
    name="intent_classifier",
    metadata={"hnsw:space": "cosine"}
)

result = collection.query(
    query_texts=[message],
    n_results=1
)
distance   = result["distances"][0][0]
confidence = 1 - distance    # cosine → 0=giống hệt, 1=trực giao
```

Nếu `confidence > 0.6` → dùng nhãn route khớp.

### Bước 2 — Keyword Fallback (khi confidence ≤ 0.6)

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

Logic phân loại:

```
message_lower = message.lower().split()
if any(w in security_keywords for w in message_lower):
    route = "security"
elif any(w in search_keywords for w in message_lower):
    route = "search"
else:
    route = "general"
```

### Bảng Quyết Định Route

```
Input: "ISO 27001 Annex A.9 nói gì về kiểm soát truy cập?"
  → confidence ngữ nghĩa: 0.91  →  route: security  ✅

Input: "Tin tức ransomware mới nhất hôm nay"
  → confidence ngữ nghĩa: 0.44  →  keyword fallback
  → "latest", "today" khớp search_keywords  →  route: search  ✅

Input: "Làm thế nào để viết hàm Python?"
  → confidence ngữ nghĩa: 0.28  →  keyword fallback
  → không khớp  →  route: general  ✅
```

---

## 4. Route Security — Pipeline RAG

File: [`backend/repositories/vector_store.py`](../backend/repositories/vector_store.py)

### Tìm Kiếm Vector

```python
results = vector_store.search(query=message, top_k=5)
# Trả về: [{id, document, metadata, distance}, ...]
```

Mỗi kết quả có tiền tố context header:

```
[Context: # ISO 27001:2022 > ## Annex A > ### A.9 Access Control]
A.9.1.1 Chính sách kiểm soát truy cập — Cần thiết lập, lập tài liệu,
được phê duyệt bởi ban quản lý, công bố và truyền đạt tới nhân viên
và các bên liên quan bên ngoài...
```

### Xây Dựng Prompt

```python
context = "\n\n---\n\n".join([r["document"] for r in results])

messages = [
    {
        "role": "system",
        "content": (
            "Bạn là chuyên gia bảo mật thông tin chuyên về ISO 27001. "
            "Chỉ trả lời dựa trên context được cung cấp. "
            "Nếu context không có câu trả lời, hãy nói rõ điều đó.\n\n"
            f"CONTEXT:\n{context}"
        )
    },
    *history_messages,   # 10 lượt gần nhất
    {
        "role": "user",
        "content": message
    }
]
```

### Tìm Kiếm Đa Query (tùy chọn)

Với các câu hỏi phức tạp, `multi_query_search` tạo 3 biến thể query, lấy kết quả cho mỗi query rồi loại trùng theo distance:

```python
queries = [
    message,
    f"ISO 27001 {message}",
    f"security control {message}"
]
all_results = []
for q in queries:
    all_results.extend(vector_store.search(q, top_k=3))
# loại trùng theo id, giữ distance thấp nhất
```

---

## 5. Route Search — Tìm Kiếm DuckDuckGo

File: [`backend/services/web_search.py`](../backend/services/web_search.py)

### Thực Thi Tìm Kiếm

```python
from duckduckgo_search import DDGS

with DDGS() as ddgs:
    raw = list(ddgs.text(query, max_results=max_results))
```

### Logic Retry

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

### Định Dạng Context

```python
@staticmethod
def format_context(results):
    if not results:
        return "Không có kết quả tìm kiếm web."
    lines = ["## Kết Quả Tìm Kiếm Web\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**[{i}] {r['title']}**")
        lines.append(r['body'])
        lines.append(f"Nguồn: {r['href']}\n")
    return "\n".join(lines)
```

### Prompt Cho Route Search

```python
messages = [
    {
        "role": "system",
        "content": (
            "Bạn là trợ lý AI hữu ích. Dùng kết quả tìm kiếm web sau "
            "để trả lời câu hỏi người dùng. Trích dẫn nguồn khi phù hợp.\n\n"
            f"{WebSearch.format_context(results)}"
        )
    },
    *history_messages,
    { "role": "user", "content": message }
]
```

---

## 6. Route General — LLM Trực Tiếp

Với câu hỏi chung, không thực hiện truy xuất. System prompt thiết lập persona:

```python
messages = [
    {
        "role": "system",
        "content": (
            "Bạn là trợ lý AI am hiểu về bảo mật thông tin, "
            "ISO 27001 và CNTT doanh nghiệp. "
            "Trả lời rõ ràng và súc tích."
        )
    },
    *history_messages,
    { "role": "user", "content": message }
]
```

---

## 7. Session Memory

File: [`backend/repositories/session_store.py`](../backend/repositories/session_store.py)

### Cấu Trúc Lưu Trữ

```
/data/sessions/
└── {session_id}.json
```

Mỗi file chứa:

```json
{
  "session_id": "user-abc123",
  "created_at": 1711270000.0,
  "updated_at": 1711270400.0,
  "messages": [
    { "role": "user",      "content": "ISO 27001 là gì?" },
    { "role": "assistant", "content": "ISO 27001 là tiêu chuẩn quốc tế..." }
  ]
}
```

### Tham Số

| Tham số | Giá trị | Ghi chú |
|---------|---------|---------|
| Số tin nhắn lưu tối đa | 20 | Tin nhắn cũ hơn bị xóa khi đạt giới hạn |
| Tin nhắn gửi tới LLM | 10 | Luôn là `history[-10:]` |
| TTL session | 86400 s (24 h) | Session hết hạn được dọn khi khởi động |
| Lưu trữ | File-based | An toàn luồng với `threading.Lock()` |

### Quản Lý Cửa Sổ Context

```python
def get_context_messages(self, session_id: str, max_messages: int = 10):
    history = self.load(session_id).get("messages", [])
    return history[-max_messages:]   # cửa sổ trượt, gần nhất nhất trước
```

### An Toàn Luồng

Mọi thao tác đọc/ghi đều dùng `self._lock = threading.Lock()` để tránh race condition khi nhiều request đồng thời sửa cùng một file session.

---

## 8. Cloud LLM Service

File: [`backend/services/cloud_llm_service.py`](../backend/services/cloud_llm_service.py)

### Chuỗi Dự Phòng

```
CloudLLMService.chat_completion(messages, task_type="chat")
        │
        ▼
  Tầng 1: Open Claude (OPEN_CLAUDE_API_BASE)
  ┌────────────────────────────────────────┐
  │ model = TASK_MODEL_MAP[task_type]      │
  │ keys = OPEN_CLAUDE_API_KEY.split(",")  │
  │ key  = keys[_key_index % len(keys)]    │
  │ _key_index += 1  (round-robin)         │
  └──────────────┬─────────────────────────┘
                 │ timeout / 5xx / không có key
                 ▼
  Tầng 2: LocalAI (LOCAL_AI_BASE_URL)
  ┌────────────────────────────────────────┐
  │ model = LOCAL_AI_MODEL                 │
  │ OpenAI-compatible /v1/chat/completions │
  └────────────────────────────────────────┘
```

### Model Cho Chat

```python
TASK_MODEL_MAP = {
    "chat":    "gemini-3-pro-preview",   # tin nhắn chat thông thường
    "complex": "gemini-2.5-pro",         # khi phát hiện độ phức tạp cao
    "default": "gemini-3-pro-preview",
}
```

### Định Dạng Phản Hồi

```python
{
    "content": "ISO 27001 Annex A.9 bao gồm kiểm soát truy cập...",
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

### Sự Kiện Stream

```
data: {"chunk": "ISO "}
data: {"chunk": "27001 "}
data: {"chunk": "Annex A.9..."}
data: {"done": true, "session_id": "abc", "route": "security", "model": "gemini-2.5-pro"}
```

> Frontend (`chatbot/page.js`) hiện dùng endpoint đồng bộ `/api/chat`. Endpoint streaming có sẵn để tích hợp trong tương lai.

---

## 10. Triển Khai Frontend

File: [`frontend-next/src/app/chatbot/page.js`](../frontend-next/src/app/chatbot/page.js)

### State

```js
const [messages, setMessages] = useState([])   // hiển thị chat
const [sessions, setSessions] = useState([])   // danh sách session sidebar
const [sessionId, setSessionId] = useState(null)
const [pending, setPending] = useState(false)
```

### Lưu Session (localStorage)

```js
// Key: "chatbot_sessions"
// Value: [{ id, preview, messages, ts }, ...]
function directSaveSession(sessionId, messages) {
    const entry = { id: sessionId, preview: messages[0]?.content, messages, ts: Date.now() }
    const sessions = lsGet("chatbot_sessions", [])
    // upsert theo id, giữ tối đa 20 sessions
}
```

### Luồng Gửi Tin Nhắn

```
Người dùng nhập + nhấn Enter
  → send(text)
      → thêm tin nhắn người dùng vào UI
      → POST /api/chat { message: text, session_id }
      → chờ phản hồi
      → thêm tin nhắn bot vào UI
      → directSaveSession(sessionId, updatedMessages)
```

### Gợi Ý Câu Hỏi

```js
const SUGGESTIONS = [
  "Tổng quan các controls Annex A của ISO 27001",
  "Cách triển khai chính sách kiểm soát truy cập?",
  "Tin tức mới nhất về các mối đe dọa an ninh mạng",
  "Quy trình đánh giá rủi ro là gì?",
  "Tổng quan Luật An ninh Mạng Việt Nam 2018"
]
```
