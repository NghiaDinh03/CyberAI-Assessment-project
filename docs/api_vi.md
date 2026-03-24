# Tài Liệu API

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-API_Reference-blue?style=flat-square)](api.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Tài_liệu_API-red?style=flat-square)](api_vi.md)

</div>

---

## Mục Lục

1. [Base URL & Quy Ước](#1-base-url--quy-ước)
2. [Endpoint Chat](#2-endpoint-chat)
3. [Endpoint Tin Tức](#3-endpoint-tin-tức)
4. [Endpoint ISO 27001](#4-endpoint-iso-27001)
5. [Endpoint Hệ Thống](#5-endpoint-hệ-thống)
6. [Phản Hồi Lỗi](#6-phản-hồi-lỗi)
7. [Lớp Proxy Next.js](#7-lớp-proxy-nextjs)

---

## 1. Base URL & Quy Ước

| Môi trường | Base URL |
|------------|----------|
| Docker local | `http://localhost:8000` |
| Mạng nội bộ Docker | `http://backend:8000` |
| Proxy frontend (Next.js) | `/api` (chuyển tiếp tới backend) |

**Header thông dụng:**

```http
Content-Type: application/json
```

**Envelope phản hồi (thành công):**

```json
{ "field1": "...", "field2": "..." }
```

**Envelope phản hồi (lỗi):**

```json
{ "detail": "Thông báo lỗi dễ đọc" }
```

---

## 2. Endpoint Chat

### `POST /api/chat`

Phản hồi chat đồng bộ. Trả về toàn bộ câu trả lời AI.

**Request body:**

```json
{
  "message": "Yêu cầu kiểm soát truy cập ISO 27001 là gì?",
  "session_id": "user-abc123"
}
```

| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|------|----------|-------|
| `message` | string | ✅ | Tin nhắn người dùng (phải khác rỗng) |
| `session_id` | string | ❌ | ID session để duy trì hội thoại. Mặc định `"default"` |

**Phản hồi:**

```json
{
  "response": "ISO 27001 Annex A.9 Kiểm soát truy cập yêu cầu...",
  "session_id": "user-abc123",
  "route": "security",
  "model": "gemini-2.5-pro",
  "provider": "open_claude"
}
```

| Trường | Mô tả |
|--------|-------|
| `response` | Câu trả lời từ AI |
| `session_id` | Echo lại session ID đã dùng |
| `route` | Quyết định router: `security` / `search` / `general` |
| `model` | Tên model thực sự đã dùng |
| `provider` | `open_claude` hoặc `localai` |

---

### `POST /api/chat/stream`

Chat streaming qua **Server-Sent Events (SSE)**. Mỗi chunk đến dưới dạng sự kiện riêng biệt.

**Request body:** Giống `POST /api/chat`

**Phản hồi:** `text/event-stream`

```
data: {"chunk": "ISO 27001 "}
data: {"chunk": "Annex A.9 "}
data: {"chunk": "Kiểm soát truy cập..."}
data: {"done": true, "session_id": "user-abc123", "route": "security"}
```

**Loại sự kiện:**

| Trường | Mô tả |
|--------|-------|
| `chunk` | Đoạn text cần nối thêm vào UI |
| `done` | `true` báo hiệu kết thúc stream; kèm metadata |
| `error` | Chuỗi thông báo lỗi nếu tạo phản hồi thất bại |

---

### `GET /api/chat/history/{session_id}`

Lấy toàn bộ lịch sử hội thoại của một session.

**Path parameter:** `session_id` — chuỗi định danh session

**Phản hồi:**

```json
{
  "session_id": "user-abc123",
  "messages": [
    { "role": "user",      "content": "Xin chào" },
    { "role": "assistant", "content": "Chào bạn! Tôi có thể giúp gì?" }
  ],
  "count": 2
}
```

> **Lưu ý:** Tối đa 20 tin nhắn được lưu mỗi session (TTL: 24 giờ). Chỉ 10 tin nhắn gần nhất được gửi tới LLM mỗi yêu cầu.

---

## 3. Endpoint Tin Tức

### `GET /api/news`

Lấy bài báo theo danh mục (cache TTL 15 phút).

**Query parameters:**

| Tham số | Kiểu | Mặc định | Mô tả |
|---------|------|---------|-------|
| `category` | string | `cybersecurity` | Một trong: `cybersecurity`, `stocks_vietnam`, `stocks_international` |
| `limit` | int | `15` | Số bài tối đa (1–50) |

**Phản hồi:**

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

**Nguồn RSS theo danh mục:**

| Danh mục | Nguồn |
|----------|-------|
| `cybersecurity` | The Hacker News, Dark Reading, SecurityWeek |
| `stocks_international` | CNBC Markets, MarketWatch, Yahoo Finance |
| `stocks_vietnam` | Znews Kinh doanh, VnExpress Kinh doanh, VnEconomy |

---

### `GET /api/news/history`

Lấy toàn bộ lịch sử xử lý bài báo (lưu tại `/data/articles_history.json`).

---

### `GET /api/news/ai-status`

Trả về chuỗi trạng thái xử lý AI hiện tại.

**Phản hồi:**

```json
{ "status": "Đang dịch bài: Critical Zero-Day..." }
```

Các giá trị: `"Đang rảnh"` (nhàn rỗi) hoặc thông báo đang xử lý.

---

### `GET /api/news/search`

Tìm kiếm toàn văn trong tất cả bài báo đã cache.

**Query parameters:** `q` (string, bắt buộc), `limit` (int, mặc định 20)

---

### `GET /api/news/all`

Lấy bài báo từ cả ba danh mục kết hợp.

**Query parameter:** `limit` (int, 1–30, mặc định 10)

---

### `POST /api/news/summarize`

Kích hoạt tóm tắt bài báo theo yêu cầu: cào → dịch → TTS audio.

**Request body:**

```json
{
  "url": "https://thehackernews.com/2025/...",
  "lang": "en",
  "title": "Critical Zero-Day..."
}
```

| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|------|----------|-------|
| `url` | string | ✅ | URL bài báo |
| `lang` | string | ✅ | `"en"` (dịch) hoặc `"vi"` (biên tập lại) |
| `title` | string | ❌ | Tiêu đề gốc (dùng dự phòng nếu cào thất bại) |

**Phản hồi (thành công):**

```json
{
  "audio_url": "/api/news/audio/a7c3e259.mp3",
  "summary_vi": "Tóm tắt nội dung bài báo bằng tiếng Việt...",
  "title_vi": "Tiêu đề bài báo dạng tiếng Việt"
}
```

**Phản hồi (lỗi):**

```json
{
  "error": "❌ Trang thehackernews.com chặn truy cập bot. Sẽ tự động thử lại sau.",
  "retryable": true
}
```

**Pipeline nội bộ:**

```
Bước 1: scrape_article(url)
         requests+BeautifulSoup → trafilatura → newspaper3k
         (cắt bớt tại 30.000 ký tự)
Bước 2: CloudLLMService.chat_completion(task_type="news_translate")
         → gemini-2.5-pro (Open Claude chính)
         → dọn artifact AI
Bước 3: edge_tts.Communicate("vi-VN-HoaiMyNeural").save(mp3)
```

---

### `POST /api/news/reprocess`

Buộc xử lý lại một bài báo (xóa cache, chạy lại pipeline).

**Request body:** `{ "url": "https://..." }`

---

### `GET /api/news/audio/{filename}`

Stream file MP3 audio.

**Phản hồi:** `audio/mpeg` stream

---

### `POST /api/news/clear-cache`

Xóa cache tin tức in-memory (ép lấy RSS mới ở yêu cầu tiếp theo).

---

## 4. Endpoint ISO 27001

### `POST /api/iso27001/assess`

Gửi đánh giá ISO 27001. Trả về ngay lập tức với job ID dạng pending. Xử lý chạy trong **background task**.

**Request body:**

```json
{
  "company_name": "ACME Corp",
  "industry": "Tài chính",
  "system_description": "Hệ thống core banking...",
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

**Phản hồi ngay lập tức (HTTP 202):**

```json
{
  "id": "7e0b008d-34d9-4c5b-bf9a-f3de2d53658e",
  "status": "pending"
}
```

**Luồng background task:**

```
process_assessment_bg(assessment_id)
  → load JSON từ /data/assessments/{id}.json
  → ChatService.assess_system(system_data)
      → VectorStore.search(controls ISO liên quan, top_k=5)
      → CloudLLMService.chat_completion(task_type="iso_analysis")
         → gemini-2.5-pro (qua Open Claude)
  → lưu { status:"done", result:{...} } vào JSON
```

---

### `GET /api/iso27001/assessments/{assessment_id}`

Kiểm tra trạng thái của một job đánh giá.

**Phản hồi (đang xử lý):**

```json
{ "id": "7e0b008d-...", "status": "pending" }
```

**Phản hồi (hoàn thành):**

```json
{
  "id": "7e0b008d-...",
  "status": "done",
  "result": {
    "overall_score": 62,
    "compliance_level": "Partial",
    "gaps": ["Chưa có quy trình quản lý vá lỗi", "Chưa có kế hoạch ứng phó sự cố"],
    "recommendations": ["Triển khai quản lý vá lỗi tự động...", "..."]
  }
}
```

---

### `DELETE /api/iso27001/assessments/{assessment_id}`

Xóa một bản ghi đánh giá.

**Phản hồi:** `{ "deleted": true }`

---

### `POST /api/iso27001/reindex`

Re-index tài liệu ISO vào ChromaDB (xóa và xây dựng lại collection).

**Phản hồi:** `{ "status": "ok", "indexed": 42 }`

---

### `GET /api/iso27001/chromadb/stats`

Trả về thống kê ChromaDB collection.

**Phản hồi:**

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

Tìm kiếm ngữ nghĩa trong cơ sở kiến thức ISO.

**Request body:**

```json
{ "query": "chính sách kiểm soát truy cập", "top_k": 5 }
```

**Phản hồi:**

```json
{
  "results": [
    {
      "id": "iso27001_annex_a_chunk_42",
      "document": "[Context: # ISO 27001 > ## Annex A > ### A.9]\nA.9.1.1 Chính sách kiểm soát truy cập...",
      "metadata": { "source": "iso27001_annex_a.md", "chunk_index": 42 },
      "distance": 0.12
    }
  ]
}
```

---

## 5. Endpoint Hệ Thống

### `GET /api/system/stats`

Mức sử dụng tài nguyên hệ thống theo thời gian thực. Đọc trực tiếp từ `/host/proc/stat` và `/host/proc/meminfo` (filesystem host được mount chỉ đọc vào container).

**Phản hồi:**

```json
{
  "cpu": {
    "percent": 23.5,
    "model": "Intel(R) Core(TM) i7-10700K",
    "cores": 8
  },
  "memory": {
    "total": 16777216000,
    "used": 8234567000,
    "percent": 49.1
  },
  "disk": {
    "total": 512000000000,
    "used": 189000000000,
    "percent": 36.9
  },
  "uptime": 432000
}
```

**Phương pháp tính CPU %:**

```python
# Đọc /host/proc/stat hai lần (cách nhau 100ms)
# Tính delta: (ticks không idle / tổng ticks) × 100
```

---

### `GET /api/system/cache-stats`

Trả về kích thước thư mục cache và số lượng bản ghi.

**Phản hồi:**

```json
{
  "summaries": { "count": 54, "size_bytes": 2340000 },
  "audio":     { "count": 54, "size_bytes": 98000000 },
  "sessions":  { "count": 12, "size_bytes": 45000 },
  "assessments": { "count": 3, "size_bytes": 12000 }
}
```

---

## 6. Phản Hồi Lỗi

| HTTP Code | Ý nghĩa | Ví dụ |
|-----------|---------|-------|
| `400` | Request không hợp lệ | `{ "detail": "Message cannot be empty" }` |
| `404` | Không tìm thấy | `{ "detail": "Assessment not found" }` |
| `422` | Lỗi validation (Pydantic) | `{ "detail": [{ "loc": ["body","url"], "msg": "field required" }] }` |
| `500` | Lỗi server nội bộ | `{ "detail": "Internal server error" }` |

---

## 7. Lớp Proxy Next.js

Frontend bao gồm các file API route dưới `frontend-next/src/app/api/` để proxy yêu cầu tới backend. Cho phép trình duyệt gọi `/api/*` mà không lộ URL backend hay gặp vấn đề CORS.

| Route frontend | Proxy tới |
|----------------|----------|
| `POST /api/chat` | `POST http://backend:8000/api/chat` |
| `GET /api/news` | `GET http://backend:8000/api/news` |
| `GET /api/news/history` | `GET http://backend:8000/api/news/history` |
| `POST /api/news/summarize` | `POST http://backend:8000/api/news/summarize` |
| `POST /api/news/reprocess` | `POST http://backend:8000/api/news/reprocess` |
| `GET /api/news/search` | `GET http://backend:8000/api/news/search` |
| `POST /api/iso27001/assess` | `POST http://backend:8000/api/iso27001/assess` |
| `GET /api/iso27001/assessments/:id` | `GET http://backend:8000/api/iso27001/assessments/:id` |
| `POST /api/iso27001/chromadb/search` | `POST http://backend:8000/api/iso27001/chromadb/search` |

> **Lưu ý:** `/api/chat/stream` được gọi trực tiếp qua `fetch` với streaming reader; không có route proxy Next.js bao bọc.
