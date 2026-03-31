# CyberAI Assessment Platform — Đánh Giá Toàn Diện & Đề Xuất Cải Thiện

> **Ngày đánh giá:** 2026-03-31 | **Người đánh giá:** Roo (Senior Full-Stack AI & Cybersecurity Platform Engineer)
> **Phiên bản platform:** v2.0.0 | **Stack:** FastAPI · Next.js 15 · LocalAI · ChromaDB · Docker

---

## MỤC LỤC

1. [Tổng quan kiến trúc hệ thống](#1-tổng-quan-kiến-trúc)
2. [Đánh giá UI/UX](#2-đánh-giá-uiux)
3. [Đánh giá Chatbot & AI Pipeline](#3-đánh-giá-chatbot--ai-pipeline)
4. [Đánh giá Backend & API](#4-đánh-giá-backend--api)
5. [Đánh giá Hạ tầng & DevSecOps](#5-đánh-giá-hạ-tầng--devsecops)
6. [Đánh giá Data Layer](#6-đánh-giá-data-layer)
7. [Đề xuất cải thiện ưu tiên cao](#7-đề-xuất-cải-thiện-ưu-tiên-cao)
8. [Roadmap đề xuất](#8-roadmap-đề-xuất)

---

## 1. TỔNG QUAN KIẾN TRÚC

### Sơ đồ luồng hiện tại

```
[Browser]
   │
   ▼
[Next.js 15 Frontend :3000]
   ├─ /chatbot     → AI Chat (SSE stream)
   ├─ /form-iso    → Multi-standard Assessment
   ├─ /standards   → Standard Library
   ├─ /analytics   → Dashboard + Benchmark
   └─ /templates   → Network Templates
   │
   ▼ (API proxy via Next.js Route Handlers)
[FastAPI Backend :8000]
   ├─ /api/chat            → ChatService → CloudLLMService → model_router
   ├─ /api/chat/stream     → SSE streaming
   ├─ /api/iso27001/*      → Assessment + Evidence
   ├─ /api/standards/*     → Custom Standards CRUD
   ├─ /api/system/*        → CPU/RAM/Disk stats
   ├─ /api/benchmark/*     → LLM Benchmark runner
   ├─ /api/documents/*     → Document ingestion
   └─ /api/dataset/*       → Fine-tune data gen
   │
   ├──▶ [ChromaDB] (persistent vector store)
   ├──▶ [LocalAI :8080] (GGUF inference, on-prem)
   └──▶ [Open Claude API] (cloud, multi-model fallback)
```

### Nhận xét tổng quan

| Hạng mục | Điểm | Nhận xét |
|---|---|---|
| Kiến trúc tổng thể | 7.5/10 | Clean separation, nhưng thiếu message queue, cache layer |
| Chatbot & AI | 7/10 | Hybrid routing tốt, thiếu streaming thực sự end-to-end |
| UI/UX | 7/10 | Dark mode đẹp, nhưng nhiều trang quá nặng, thiếu accessibility |
| Backend API | 7.5/10 | RESTful đúng chuẩn, nhưng thiếu auth, input validation yếu |
| Hạ tầng | 6.5/10 | Docker compose đủ dùng, thiếu CI/CD, monitoring, secret mgmt |
| Data Layer | 7/10 | ChromaDB + file-based sessions ổn, thiếu backup strategy |
| Bảo mật | 5/10 | **Nhiều lỗ hổng nghiêm trọng cần fix ngay** |

---

## 2. ĐÁNH GIÁ UI/UX

### 2.1 Điểm mạnh

- **Dark/Light theme** hoàn chỉnh với CSS variables, transition mượt — thiết kế nhất quán
- **Responsive navbar** với hamburger menu mobile, clock multi-timezone — UX tốt
- **SVG Gauge component** tái sử dụng cho form-iso và analytics — DRY tốt
- **ReactMarkdown + remark-gfm** render response AI đúng chuẩn, hỗ trợ table, code block
- **Suggestion chips** trên chatbot giúp user onboard nhanh
- **Session sidebar** trong chatbot lưu history localStorage — offline-capable
- **Drag & drop evidence upload** trong form-iso — UX hiện đại
- **Progress indicator streaming** (`step: routing → rag → thinking → done`) — tốt
- **Form draft auto-save** vào localStorage — chống mất dữ liệu

### 2.2 Vấn đề UI/UX cần cải thiện

#### CRITICAL

**[UX-01] Form ISO quá dài, không có navigation rõ ràng**
- [`form-iso/page.js`](frontend-next/src/app/form-iso/page.js:52) — 1845 dòng trong 1 file, quá phức tạp
- Không có step indicator (step 1/4, step 2/4...) visible ở đầu trang
- User dễ bị lạc trong form dài
- **Fix:** Tách thành `StepIndicator`, `StepNavigation` components riêng. Thêm sticky progress bar.

**[UX-02] Không có loading skeleton**
- Khi fetch data, các trang chỉ show spinner/text đơn giản
- Analytics page load nặng mà không có skeleton UI
- **Fix:** Implement skeleton loaders cho cards, tables, assessment list.

**[UX-03] Không có error boundary**
- Nếu API fail, không có fallback UI rõ ràng ở component level
- **Fix:** Thêm React Error Boundary wrapper cho từng section.

#### HIGH

**[UX-04] Model selector dropdown trong chatbot không filter/search được**
- 13 models hardcoded trong [`chatbot/page.js`](frontend-next/src/app/chatbot/page.js:8), không có search box
- User khó tìm model cần dùng khi list dài
- **Fix:** Thêm input search trong dropdown, group by provider.

**[UX-05] `mdToHtml()` function tự viết trong analytics — nguy hiểm**
- [`analytics/page.js`](frontend-next/src/app/analytics/page.js:11) implement custom markdown-to-HTML thay vì dùng ReactMarkdown
- Regex replace không đủ an toàn, có thể bị XSS nếu AI trả về malicious content
- **Fix:** Thay bằng `<ReactMarkdown>` + `rehype-sanitize`.

**[UX-06] Không có empty state design**
- Khi chưa có assessments, analytics chỉ show blank
- Chatbot khi chưa có session không có welcome screen rõ ràng
- **Fix:** Thiết kế empty state với illustration và CTA button.

**[UX-07] Thiếu keyboard navigation & accessibility**
- Không có `aria-label` đầy đủ trên buttons, inputs
- Model dropdown không thể navigate bằng keyboard (↑↓ Enter)
- Focus management khi mở/đóng modal/dropdown chưa đúng
- **Fix:** Thêm ARIA roles, keyboard handlers, focus trap cho modals.

**[UX-08] Analytics page quá nhiều state variables (30+ useState)**
- [`analytics/page.js`](frontend-next/src/app/analytics/page.js:53) — 30+ useState, làm component re-render nhiều
- **Fix:** Consolidate với `useReducer`, tách thành sub-components.

#### MEDIUM

**[UX-09] Mobile UX cho chatbot chưa tốt**
- Sidebar session list overlap trên mobile
- Input box bị đẩy lên khi keyboard mobile xuất hiện
- **Fix:** Dùng CSS `dvh` (dynamic viewport height), fix sidebar z-index.

**[UX-10] Không có toast notification system**
- Thành công/lỗi hiện chỉ dùng `alert()` (`confirm()` trong analytics delete)
- **Fix:** Implement toast/snackbar system (có thể dùng react-hot-toast nhẹ).

**[UX-11] Chatbot không có "copy message" button**
- AI responses dài không có button copy nhanh
- **Fix:** Thêm copy-to-clipboard button trên mỗi assistant bubble.

**[UX-12] Không có character counter trên input**
- ChatRequest limit là 2000 chars nhưng không hiển thị counter cho user
- **Fix:** Thêm counter `{input.length}/2000` dưới textarea.

**[UX-13] Standards page thiếu search/filter**
- Danh sách standards không có search, không có filter by category
- **Fix:** Thêm live search input + tag filter.

**[UX-14] Templates page không preview được trước khi apply**
- User phải apply template rồi mới thấy nội dung
- **Fix:** Thêm modal preview với summary trước khi apply.

**[UX-15] Form-ISO không validate realtime**
- Chỉ validate khi submit, không báo lỗi inline trong khi gõ
- **Fix:** Debounced validation với inline error messages.

---

## 3. ĐÁNH GIÁ CHATBOT & AI PIPELINE

### 3.1 Điểm mạnh

- **Hybrid routing** (Semantic ChromaDB + Keyword fallback) — kiến trúc thông minh
- **Multi-model fallback chain**: `gemini-3-flash → gemini-3-pro → gpt-5-mini → claude-sonnet → gpt-5`
- **RAG với source attribution** — biết context lấy từ file nào
- **Web search integration** (DuckDuckGo) — không cần API key
- **Session memory** — 10 messages context window
- **Special token cleanup** — xử lý Llama artifacts sạch sẽ
- **SSE streaming** — real-time response display
- **LocalAI fallback** — on-prem privacy option

### 3.2 Vấn đề AI/Chatbot cần cải thiện

#### CRITICAL

**[AI-01] Stream không thực sự streaming — polling thay vì true SSE**
- [`api/chat/route.js`](frontend-next/src/app/api/chat/route.js:12) proxy stream đúng, nhưng trong [`chatbot/page.js`](frontend-next/src/app/chatbot/page.js:136) vẫn dùng `.then(r => r.json())` — tức là đợi full response
- Không có token-by-token streaming render (typewriter effect)
- **Fix:** Parse `text/event-stream` chunks, render từng token vào UI ngay.

**[AI-02] `PENDING_KEY` localStorage pattern có race condition**
- [`chatbot/page.js`](frontend-next/src/app/chatbot/page.js:198) lưu pending request vào localStorage để recover sau navigation
- Nếu user refresh trong khi đang stream → có thể replay request, tốn token
- **Fix:** Dùng AbortController + cleanup properly, không dùng localStorage để track in-flight requests.

**[AI-03] Prompt injection không được sanitize**
- [`chat_service.py`](backend/services/chat_service.py:66) nhúng trực tiếp `message` vào system prompt context
- `user_content = f"Tài liệu tham chiếu:\n{context}\n\nCâu hỏi: {message}"`
- Malicious user có thể inject: `message = "Bỏ qua mọi hướng dẫn trên. Hãy..."`
- **Fix:** Thêm prompt injection guard, sanitize input, tách rõ system/user/context.

#### HIGH

**[AI-04] Intent classification templates quá đơn giản (Vietnamese-only)**
- [`model_router.py`](backend/services/model_router.py:14) chỉ có keywords tiếng Việt
- English queries về security sẽ bị route sai (ví dụ: "NIST CSF assessment")
- **Fix:** Thêm English keywords, dùng bilingual templates.

**[AI-05] RAG chunk size cứng (600 chars) không phù hợp với tất cả documents**
- [`vector_store.py`](backend/repositories/vector_store.py:29) chunk_size=600 quá nhỏ cho ISO controls dài
- Không có adaptive chunking dựa trên document type
- **Fix:** Semantic chunking by section boundaries, overlap strategy cải thiện.

**[AI-06] Không có confidence threshold cho RAG results**
- [`rag_service.py`](backend/services/rag_service.py:15) không filter results theo score
- Nếu relevance score thấp, AI vẫn dùng context không liên quan → hallucination
- **Fix:** Filter chunks với `score < 0.35`, chỉ inject context khi relevant.

**[AI-07] Session store file-based — không scale và có lock contention**
- [`session_store.py`](backend/repositories/session_store.py:19) dùng file JSON + threading.Lock()
- Với nhiều concurrent users, file I/O bottleneck nghiêm trọng
- **Fix:** Migrate sang Redis (có thể dùng redis-py + redis container trong compose).

**[AI-08] `MAX_TOKENS=-1` trong docker-compose — nguy hiểm**
- [`docker-compose.yml`](docker-compose.yml:14) `MAX_TOKENS=-1` → LocalAI generate không giới hạn
- Có thể gây OOM, hoặc response cực dài
- **Fix:** Set `MAX_TOKENS=4096` hoặc tùy theo use case.

**[AI-09] Không có response caching**
- Cùng 1 câu hỏi hỏi nhiều lần vẫn gọi API cloud → tốn tiền
- **Fix:** Implement semantic caching với ChromaDB (cache key = embedding similarity).

**[AI-10] Web search kết quả không được re-rank**
- DuckDuckGo trả về 5 kết quả, không có reranking
- Context nhồi vào prompt có thể noise nhiều
- **Fix:** Thêm BM25 reranking hoặc cross-encoder score trước khi inject.

#### MEDIUM

**[AI-11] Hardcoded model list ở frontend không đồng bộ với backend**
- [`chatbot/page.js`](frontend-next/src/app/chatbot/page.js:8) có 13 models hardcoded
- Backend fallback chain trong [`cloud_llm_service.py`](backend/services/cloud_llm_service.py:36) khác
- **Fix:** Expose `/api/models` endpoint, frontend fetch dynamic.

**[AI-12] Không có conversation title generation**
- Session title chỉ lấy 50 chars đầu của message đầu tiên
- **Fix:** Dùng LLM để generate title ngắn gọn cho session (background task).

**[AI-13] `prefer_cloud=True` hardcoded khi user chọn non-localai model**
- Không thực sự để user kiểm soát được routing
- **Fix:** Expose `prefer_cloud` setting rõ ràng trong UI toggle.

---

## 4. ĐÁNH GIÁ BACKEND & API

### 4.1 Điểm mạnh

- **FastAPI** với proper Pydantic v2 schemas — type-safe
- **Layered architecture**: routes → services → repositories — clean
- **Rate limiting** với slowapi (optional import pattern — resilient)
- **Request size limit** middleware — chặn oversized body
- **Background tasks** cho dataset generation — non-blocking
- **Health checks** đầy đủ trên tất cả services
- **Startup validation** warnings — tốt cho ops awareness
- **Evidence file parsing** multi-format (PDF/DOCX/XLSX/images)

### 4.2 Vấn đề Backend cần cải thiện

#### CRITICAL

**[BE-01] Không có Authentication/Authorization**
- Tất cả API endpoints hoàn toàn PUBLIC — không có JWT, không có API key check
- Bất kỳ ai biết URL đều có thể: xóa assessments, upload evidence, trigger benchmark, generate dataset
- [`chat.py`](backend/api/routes/chat.py:41) `@router.post("/chat")` — không có auth
- [`iso27001.py`](backend/api/routes/iso27001.py:148) save/delete assessments — không có auth
- **Fix:** Implement JWT middleware, protect write endpoints tối thiểu với API key.

**[BE-02] Path traversal vulnerability trong evidence upload**
- [`iso27001.py`](backend/api/routes/iso27001.py:101) `ctrl_dir = os.path.join(EVIDENCE_DIR, ctrl_id.replace(".", "_"))`
- `ctrl_id` từ user input, chỉ replace dấu chấm — còn `../` và các ký tự nguy hiểm khác
- Attacker có thể upload file vào thư mục ngoài EVIDENCE_DIR
- **Fix:** Validate `ctrl_id` với whitelist regex `^[a-zA-Z0-9_-]{1,50}$`, dùng `Path.resolve()` + check prefix.

**[BE-03] JWT_SECRET default "change-me-in-production" hardcoded**
- [`config.py`](backend/core/config.py:31) `JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")`
- Có warning nhưng system vẫn chạy bình thường với secret yếu
- **Fix:** Nếu JWT_SECRET == default, refuse startup trong production (`DEBUG=false`).

**[BE-04] Import vòng tròn trong routes**
- [`chat.py`](backend/api/routes/chat.py:13) `from main import limiter, _has_rate_limit`
- Import từ `main` trong routes là anti-pattern, circular import risk
- **Fix:** Tách limiter sang `core/limiter.py`, import từ đó.

#### HIGH

**[BE-05] Dataset generation endpoint không có auth hoặc rate limit**
- `POST /api/dataset/generate` ai cũng gọi được → có thể trigger expensive background task liên tục
- **Fix:** Require admin API key, add cooldown (1 request/hour).

**[BE-06] `os.getenv()` thay vì `settings` object trong một số nơi**
- [`iso27001.py`](backend/api/routes/iso27001.py:17) `os.getenv("DATA_PATH", "./data")` — bypass settings object
- Inconsistent config management
- **Fix:** Dùng `settings.DATA_PATH` nhất quán.

**[BE-07] Không có request ID / correlation ID**
- Không có tracing header, debug production rất khó
- **Fix:** Thêm middleware inject `X-Request-ID`, log kèm request_id.

**[BE-08] Error responses expose internal details**
- [`chat.py`](backend/api/routes/chat.py:55) `detail=f"Internal server error: {str(e)}"` — leak stack trace
- **Fix:** Log error server-side, return generic message cho client.

**[BE-09] Rate limit config dùng string format, không validate**
- `RATE_LIMIT_CHAT = "10/minute"` — nếu env var sai format, slowapi crash runtime
- **Fix:** Validate format khi parse config.

**[BE-10] Không có API versioning**
- Tất cả routes `/api/*` không có version prefix
- Breaking changes sẽ ảnh hưởng tất cả clients
- **Fix:** Prefix với `/api/v1/*` ngay bây giờ.

#### MEDIUM

**[BE-11] `assessment_service.py` / `helpers.py` không được test**
- Không có file test nào trong cả project
- **Fix:** Thêm pytest unit tests cho services, đặc biệt `chat_service`, `model_router`, `rag_service`.

**[BE-12] Benchmark route thiếu documentation**
- `/api/benchmark` không có docstring, schema không rõ
- **Fix:** Thêm Pydantic schemas đầy đủ, docstrings.

**[BE-13] Không có pagination trên list endpoints**
- `GET /api/iso27001/assessments` trả về tất cả assessments — không giới hạn
- **Fix:** Thêm `?page=1&per_page=20` pagination.

---

## 5. ĐÁNH GIÁ HẠ TẦNG & DEVSECOPS

### 5.1 Điểm mạnh

- **Docker Compose** phân tách dev/prod (`docker-compose.yml` vs `docker-compose.prod.yml`)
- **Resource limits** trên tất cả containers (memory limits/reservations)
- **Nginx reverse proxy** trong prod với HTTPS support
- **Health checks** trên backend, localai với `start_period` để chờ warm-up
- **Named volumes** trong prod — data persistence
- **CUDA variant** trong prod localai (`v2.24.2-cublas-cuda12`)
- **Restart policies** `unless-stopped` — resilience
- **Backend health**: `/health` endpoint đơn giản và nhanh

### 5.2 Vấn đề Hạ tầng cần cải thiện

#### CRITICAL

**[INFRA-01] Không có CI/CD pipeline**
- Không có `.github/workflows/` files (thư mục `.github/` tồn tại nhưng trống)
- Deploy thủ công hoàn toàn — error-prone, không có automated tests before deploy
- **Fix:** Implement GitHub Actions workflow: lint → test → build → security scan → deploy.

**[INFRA-02] Secret management không đúng chuẩn**
- `.env.example` tồn tại nhưng secrets truyền qua environment variables trong compose
- `CLOUD_API_KEYS` plain text trong env
- **Fix:** Dùng Docker Secrets hoặc HashiCorp Vault / AWS Secrets Manager cho production.

**[INFRA-03] `/proc` mount vào container — security risk**
- [`docker-compose.yml`](docker-compose.yml:50) `- /proc:/host/proc:ro`
- Mount host proc filesystem vào container, ngay cả read-only là security concern nghiêm trọng
- **Fix:** Dùng `psutil` trong container (đọc `/proc` container-local), không mount host proc.

**[INFRA-04] Không có container image scanning**
- Không có Trivy, Grype, hay bất kỳ CVE scanner nào trong pipeline
- **Fix:** Add Trivy scan vào CI pipeline trước khi push image.

#### HIGH

**[INFRA-05] Dev compose dùng `Dockerfile.dev` với source code mount**
- [`docker-compose.yml`](docker-compose.yml:80) mount toàn bộ `./frontend-next/src` vào container
- Hot reload tốt cho dev, nhưng `package-lock.json` không được mount → node_modules stale
- **Fix:** Mount `package-lock.json` hoặc dùng volume cho node_modules.

**[INFRA-06] LocalAI không có authentication**
- LocalAI port 8080 exposed ra host (không chỉ internal network trong dev)
- Ai có thể reach host đều có thể call LocalAI trực tiếp
- **Fix:** Trong prod, remove port mapping cho localai, chỉ expose qua internal network.

**[INFRA-07] Không có centralized logging**
- Logs chỉ `docker logs`, không có ELK stack, Loki, hay CloudWatch
- Production debug rất khó
- **Fix:** Thêm Loki + Grafana vào compose, hoặc forward logs sang CloudWatch.

**[INFRA-08] Không có monitoring/alerting**
- Không có Prometheus metrics, không có Grafana dashboard
- Không biết khi nào system overload
- **Fix:** Expose `/metrics` endpoint (Prometheus format), thêm Grafana + alerting rules.

**[INFRA-09] Prod Nginx config không được cung cấp**
- [`docker-compose.prod.yml`](docker-compose.prod.yml:19) mount `./nginx/nginx.conf` nhưng file này không tồn tại trong repo
- Deploy prod sẽ fail ngay lập tức
- **Fix:** Commit nginx config vào repo, thêm SSL termination config mẫu.

**[INFRA-10] Backend container mount source code trong dev**
- [`docker-compose.yml`](docker-compose.yml:40) `- ./backend:/app` — source mounted
- Nếu developer có malicious file trong backend dir, chạy trong container luôn
- **Fix:** Chỉ mount `./data` volumes, không mount source code (dùng `--reload` uvicorn thay thế).

#### MEDIUM

**[INFRA-11] Không có backup strategy cho data volumes**
- Vector store, assessments, sessions không có backup automation
- **Fix:** Cron job backup ChromaDB + assessments lên S3/GCS daily.

**[INFRA-12] `PARALLEL_REQUESTS=false` trong LocalAI — giới hạn throughput**
- [`docker-compose.yml`](docker-compose.yml:104) — chỉ 1 request tại 1 thời điểm
- **Fix:** Enable với `PARALLEL_REQUESTS=true` + set `MAX_CONCURRENT_REQUESTS` phù hợp.

**[INFRA-13] Không có graceful shutdown handling**
- Nếu container stop trong khi đang generate, response bị cắt
- **Fix:** Handle SIGTERM trong FastAPI (`@app.on_event("shutdown")`).

---

## 6. ĐÁNH GIÁ DATA LAYER

### 6.1 Điểm mạnh

- **ChromaDB PersistentClient** — data survive restart
- **Hierarchical chunking** với header context (`[Context: # ISO > ## A.5 > ### A.5.1]`) — context-aware retrieval
- **Multi-domain collections** — tách ISO docs, custom standards, intent classifier
- **Multi-query search** — tăng recall
- **File-based session store** với TTL auto-cleanup (24h)
- **Rich knowledge base**: 20+ markdown documents (ISO27001, NIST, GDPR, PCI DSS, Vietnam laws...)
- **Assessment persistence** dưới dạng JSON files với UUID

### 6.2 Vấn đề Data Layer cần cải thiện

#### CRITICAL

**[DATA-01] ChromaDB không có authentication**
- PersistentClient không có access control
- Bất kỳ process nào trong container network đều có thể đọc/ghi vector store
- **Fix:** Dùng ChromaDB Server mode với auth token khi chạy production.

**[DATA-02] Assessment files không encrypt**
- [`data/assessments/`](data/assessments/) chứa JSON với thông tin tổ chức, controls — plain text
- **Fix:** Encrypt sensitive fields (org_name, notes) trước khi ghi file.

#### HIGH

**[DATA-03] Vector store re-index xóa toàn bộ data trước**
- [`vector_store.py`](backend/repositories/vector_store.py:108) xóa tất cả IDs rồi re-add
- Nếu crash giữa chừng → data loss
- **Fix:** Implement incremental indexing: chỉ update documents đã thay đổi (dùng content hash).

**[DATA-04] Không có data validation khi index documents**
- Bất kỳ `.md` file nào trong thư mục đều được index, không validate format
- **Fix:** Validate markdown structure, minimum content length trước khi index.

**[DATA-05] Session store không có max sessions per user limit**
- [`session_store.py`](backend/repositories/session_store.py:18) không giới hạn số sessions
- Disk đầy nếu nhiều users tạo nhiều sessions
- **Fix:** Giới hạn 100 sessions, cleanup oldest khi vượt quá.

**[DATA-06] `_chunk_text()` dùng character count thay vì token count**
- [`vector_store.py`](backend/repositories/vector_store.py:29) `chunk_size=600` là chars, không phải tokens
- Với Vietnamese text, 600 chars ≈ 800-900 tokens → có thể vượt embedding model limit
- **Fix:** Dùng tiktoken để count tokens, chunk theo token boundary.

**[DATA-07] Không có data lineage tracking**
- Không biết document nào được index khi nào, version nào
- **Fix:** Thêm `indexed_at`, `file_hash`, `version` vào ChromaDB metadata.

#### MEDIUM

**[DATA-08] Knowledge base files không có versioning**
- ISO 27001 tài liệu không có version tag trong metadata
- Khi update file, không biết được chunk nào đã outdated
- **Fix:** Thêm frontmatter version header vào mỗi markdown file.

**[DATA-09] Không có data retention policy cho exports**
- [`data/exports/`](data/exports/) tích lũy PDF/HTML exports không có cleanup
- **Fix:** Auto-delete exports sau 30 ngày.

**[DATA-10] `sample_training_pairs.jsonl` trong knowledge base**
- Training data lưu cùng với production data
- **Fix:** Tách training data sang thư mục riêng, thêm vào `.gitignore`.

---

## 7. ĐỀ XUẤT CẢI THIỆN ƯU TIÊN CAO

### Sprint 1 — Bảo mật khẩn cấp (1-2 tuần)

| # | Việc cần làm | File | Effort |
|---|---|---|---|
| S1 | Thêm API Key authentication cho tất cả write endpoints | `backend/core/auth.py` (new) | M |
| S2 | Fix path traversal trong evidence upload | `backend/api/routes/iso27001.py:101` | S |
| S3 | Remove `/proc` host mount, dùng container-local `/proc` | `docker-compose.yml:50` | S |
| S4 | Fix circular import limiter | `backend/core/limiter.py` (new) | S |
| S5 | Refuse startup nếu JWT_SECRET là default trong production | `backend/core/config.py:61` | S |
| S6 | Remove LocalAI port exposure trong production | `docker-compose.prod.yml` | S |
| S7 | Sanitize `ctrl_id` với whitelist regex | `iso27001.py:101` | S |

### Sprint 2 — Chatbot & AI (2-3 tuần)

| # | Việc cần làm | File | Effort |
|---|---|---|---|
| A1 | Implement true token streaming (typewriter effect) | `chatbot/page.js` | L |
| A2 | Fix PENDING_KEY race condition | `chatbot/page.js:198` | M |
| A3 | Thêm prompt injection guard | `chat_service.py:66` | M |
| A4 | RAG confidence threshold filtering | `rag_service.py:66` | S |
| A5 | Redis session store thay file-based | `repositories/session_store.py` | M |
| A6 | Bilingual intent keywords (EN+VI) | `model_router.py:14` | S |
| A7 | Expose `/api/models` dynamic endpoint | `backend/api/routes/system.py` | S |

### Sprint 3 — UI/UX (2-3 tuần)

| # | Việc cần làm | File | Effort |
|---|---|---|---|
| U1 | Replace `mdToHtml()` với ReactMarkdown + rehype-sanitize | `analytics/page.js:11` | S |
| U2 | Thêm Toast notification system | `components/Toast.js` (new) | M |
| U3 | Loading skeleton cho cards/tables | `components/Skeleton.js` (new) | M |
| U4 | Keyboard navigation cho model dropdown | `chatbot/page.js:83` | M |
| U5 | Empty state design cho chatbot và analytics | tất cả pages | M |
| U6 | Character counter trên chat input | `chatbot/page.js` | S |
| U7 | Copy button trên assistant messages | `chatbot/page.js` | S |
| U8 | Step indicator visible cho form-iso | `form-iso/page.js:52` | M |

### Sprint 4 — DevSecOps (2-3 tuần)

| # | Việc cần làm | File | Effort |
|---|---|---|---|
| D1 | GitHub Actions CI/CD pipeline | `.github/workflows/ci.yml` | L |
| D2 | Commit nginx config mẫu | `nginx/nginx.conf` (new) | M |
| D3 | Thêm Prometheus metrics endpoint | `backend/api/routes/metrics.py` | M |
| D4 | Incremental vector store indexing | `repositories/vector_store.py:108` | L |
| D5 | API versioning `/api/v1/` | toàn bộ routes | M |
| D6 | Request ID middleware | `backend/main.py` | S |
| D7 | Graceful shutdown handler | `backend/main.py` | S |
| D8 | Unit tests với pytest | `backend/tests/` (new) | L |

---

## 8. ROADMAP ĐỀ XUẤT

### Tính năng mới nên thêm

**[FEAT-01] Real-time Collaboration**
- Nhiều auditor cùng làm việc trên 1 assessment
- WebSocket updates, conflict resolution
- Phù hợp cho team assessment trong doanh nghiệp

**[FEAT-02] Assessment Workflow & Approval**
- Draft → In Review → Approved → Published
- Role-based: Auditor, Reviewer, Approver
- Email/Slack notification khi state change

**[FEAT-03] PDF Report Export cải tiến**
- Hiện tại dùng weasyprint nhưng không rõ template
- Branded report với logo, executive summary, risk heatmap
- Export sang DOCX cho editable report

**[FEAT-04] Automated Evidence Validation**
- Khi upload evidence, AI tự đánh giá chất lượng (policy document có đủ không, screenshot có relevant không)
- Score evidence quality 1-5

**[FEAT-05] Compliance Gap Heatmap**
- Visualize compliance gaps theo ISO Annex A categories
- Heat map màu đỏ/vàng/xanh theo mức độ compliance

**[FEAT-06] Scheduled Re-assessment Reminder**
- ISO 27001 yêu cầu review định kỳ
- Email reminder khi assessment sắp hết hạn (ví dụ: 11 tháng)

**[FEAT-07] Integration với SIEM/SOAR**
- API webhook khi phát hiện gaps nghiêm trọng
- Integration Splunk, Elastic SIEM alerts

**[FEAT-08] Multi-tenant Support**
- Organizations riêng biệt, data isolation
- Admin portal quản lý tenants

**[FEAT-09] Offline Mode PWA**
- Form ISO có thể fill offline
- Sync khi có internet

**[FEAT-10] AI-powered Remediation Suggestions**
- Khi phát hiện gap, AI đề xuất cụ thể remediation steps
- Link tới relevant NIST, ISO controls

---

## TỔNG KẾT

### Strengths Summary
- Kiến trúc hybrid local/cloud AI tốt, fallback chain thông minh
- UI dark/light theme nhất quán, component reuse hợp lý
- Knowledge base phong phú với nhiều standards (ISO, NIST, GDPR, Vietnam law)
- Multi-format evidence handling tốt
- Streaming response UX

### Critical Risks (phải fix trước khi production)
1. **Không có authentication** — toàn bộ API public
2. **Path traversal** trong evidence upload
3. **Host `/proc` mount** vào container
4. **No CI/CD** — deploy thủ công, không có automated tests
5. **No monitoring** — blind spot khi production incident

### Điểm số tổng thể: **6.8/10**
Platform có foundation tốt, domain knowledge phong phú, AI pipeline thú vị. Cần tập trung vào security hardening và DevSecOps trước khi production deploy.
