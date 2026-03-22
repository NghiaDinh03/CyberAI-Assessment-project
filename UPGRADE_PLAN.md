# 🚀 UPGRADE PLAN v2.0 — PhoBERT AI Platform

## ✅ TRẠNG THÁI: ĐÃ HOÀN THÀNH

---

## 📋 Tổng quan các nâng cấp đã thực hiện

### 1. 🔄 Thay thế API: Open Claude → gemini-3-pro-preview
**Trước:** Dùng nhiều API rời rạc (Gemini, OpenRouter) không thống nhất
**Sau:** Unified `CloudLLMService` với:
- **Primary**: Open Claude API (`https://open-claude.com/v1`) — model `gemini-3-pro-preview`
- **Fallback 1**: OpenRouter API
- **Fallback 2**: LocalAI (local GGUF models)
- Multi-key round-robin với auto-cooldown khi bị rate limit
- Retry logic thông minh với exponential backoff

**Files changed:**
- `backend/services/cloud_llm_service.py` — **MỚI** (thay thế gemini_service.py)
- `backend/services/gemini_service.py` — Backward-compatible wrapper
- `backend/core/config.py` — Centralized config với CLOUD_LLM_API_URL, CLOUD_MODEL_NAME, CLOUD_API_KEYS

---

### 2. ⚡ Tối ưu hiệu suất CPU
**Vấn đề:** Project chạy AI model bằng CPU, cần tối ưu hóa
**Giải pháp đã áp dụng:**

| Kỹ thuật | File | Mô tả |
|----------|------|-------|
| PyTorch thread control | `translation_service.py` | `torch.set_num_threads()` configurable via `TORCH_THREADS` |
| JIT optimization | `translation_service.py` | `torch.jit.optimize_for_inference()` cho CPU inference |
| Semaphore throttling | `chat_service.py`, `summary_service.py` | Giới hạn concurrent requests tránh CPU overload |
| Cloud-first strategy | `chat_service.py` | Ưu tiên Cloud API → giảm tải CPU cho local model |
| Batch chunking | `translation_service.py` | Chunk size 8 titles/batch, tránh OOM |
| Aggressive caching | `session_store.py`, `summary_service.py` | File-based persistent cache, TTL management |
| Request size limit | `main.py` | Middleware giới hạn body 2MB |
| Docker memory limits | `docker-compose.yml` | Backend 6GB, LocalAI 12GB, Frontend 2GB |

---

### 3. 🧠 Conversation Memory (Bộ nhớ hội thoại)
**Trước:** Mỗi câu hỏi là 1 request độc lập, không nhớ context
**Sau:** Session-based conversation memory:
- Lưu 20 tin nhắn gần nhất/session
- Persistent storage (file-based JSON)
- Auto-cleanup sessions hết hạn (24h TTL)
- API endpoints: `GET /api/chat/history/{session_id}`, `DELETE /api/chat/history/{session_id}`

**Files changed:**
- `backend/repositories/session_store.py` — File-based persistent sessions
- `backend/services/chat_service.py` — Conversation context injection
- `backend/api/routes/chat.py` — History & clear endpoints

---

### 4. 🔍 Nâng cấp RAG Pipeline
**Trước:** Chunking đơn giản, không metadata
**Sau:**
- Semantic chunking tôn trọng markdown structure (headers, tables, lists)
- Tăng overlap (150 chars) cho context preservation tốt hơn
- Header hierarchy tracking → prepend context cho mỗi chunk
- Multi-query search (query variations cho Vietnamese)
- Cosine similarity scoring & sorting

**Files changed:**
- `backend/repositories/vector_store.py` — Enhanced chunking, multi-query search

---

### 5. 🛡️ Bảo mật & Stability
**Thêm mới:**

| Feature | Implementation |
|---------|---------------|
| CORS whitelist | Configurable via `CORS_ORIGINS` env var |
| Rate limiting | `slowapi` — configurable per endpoint |
| Request size limit | 2MB middleware |
| Input validation | Pydantic `min_length=1, max_length=2000` |
| Error boundaries | Custom 404/500 handlers, graceful degradation |
| Config validation | `settings.validate()` on startup |
| Health checks | Docker healthcheck for backend & localai |

**Files changed:**
- `backend/main.py` — CORS, rate limiting, error handlers
- `backend/core/config.py` — Validation, security settings
- `backend/api/routes/chat.py` — Input validation

---

### 6. 🏗️ Model Router Intelligence
**Trước:** Regex đơn giản phân loại câu hỏi
**Sau:** Keyword-weighted semantic classification:
- 7 route categories: `iso`, `security`, `legal`, `technical`, `news`, `general`, `greeting`
- Keyword scoring với weighted matching
- Mỗi route → custom system prompt + RAG context riêng

**Files changed:**
- `backend/services/model_router.py` — Semantic keyword classification
- `backend/services/chat_service.py` — Route-aware response generation

---

## 📁 Danh sách files đã thay đổi

### Backend Services
| File | Status | Mô tả |
|------|--------|-------|
| `services/cloud_llm_service.py` | 🆕 NEW | Unified Cloud LLM client (Open Claude + fallbacks) |
| `services/chat_service.py` | ♻️ REWRITE | Conversation memory, Cloud-first, RAG integration |
| `services/model_router.py` | ♻️ REWRITE | Semantic keyword classification |
| `services/summary_service.py` | 🔄 UPGRADE | CloudLLMService integration |
| `services/news_service.py` | 🔄 UPGRADE | CloudLLMService for tagging |
| `services/translation_service.py` | 🔄 UPGRADE | CPU optimization (torch threads, JIT) |
| `services/gemini_service.py` | ⚠️ DEPRECATED | Backward-compatible wrapper → CloudLLMService |

### Backend Core
| File | Status | Mô tả |
|------|--------|-------|
| `core/config.py` | ♻️ REWRITE | Centralized settings, validation, multi-key support |
| `main.py` | ♻️ REWRITE | CORS whitelist, rate limiting, error handlers |
| `repositories/session_store.py` | ♻️ REWRITE | File-based persistent sessions |
| `repositories/vector_store.py` | 🔄 UPGRADE | Semantic chunking, multi-query search |

### API Routes
| File | Status | Mô tả |
|------|--------|-------|
| `api/routes/chat.py` | 🔄 UPGRADE | History/clear endpoints, streaming, validation |

### Infrastructure
| File | Status | Mô tả |
|------|--------|-------|
| `requirements.txt` | 🔄 UPGRADE | Added slowapi, httpx, newspaper4k |
| `.env.example` | ♻️ REWRITE | Full documentation, new env vars |
| `docker-compose.yml` | 🔄 UPGRADE | Cloud LLM env vars, memory limits, healthchecks |
| `backend/Dockerfile` | 🔄 UPGRADE | Multi-worker production config |

---

## 🔧 Cách cấu hình

### 1. Tạo file `.env` từ template:
```bash
cp .env.example .env
```

### 2. Điền API key Open Claude:
```env
CLOUD_API_KEYS=your_key_1,your_key_2
CLOUD_LLM_API_URL=https://open-claude.com/v1
CLOUD_MODEL_NAME=gemini-3-pro-preview
```

### 3. (Optional) Thêm OpenRouter làm fallback:
```env
OPENROUTER_API_KEYS=your_openrouter_key
```

### 4. Chạy Docker:
```bash
docker-compose up --build -d
```

---

## 📊 So sánh hiệu suất (Trước vs Sau)

| Metric | v1.0 | v2.0 | Cải thiện |
|--------|------|------|-----------|
| Chat response (Cloud) | N/A | ~2-5s | Mới |
| Chat response (LocalAI) | 15-30s | 15-30s (fallback) | Cloud-first strategy |
| Translation batch | Không chunking | 8 titles/batch | Ổn định hơn |
| Session persistence | In-memory (mất khi restart) | File-based (persistent) | ✅ Persist |
| Conversation context | Không có | 20 messages/session | ✅ Mới |
| RAG chunk quality | Basic split | Semantic + headers | Chính xác hơn |
| API security | CORS * | Whitelist + rate limit | ✅ Bảo mật |
| Error recovery | Crash | Graceful fallback chain | ✅ Ổn định |

---

---

### 7. 🧹 Code Cleanup — Production-Ready Codebase
**Vấn đề:** Code chứa quá nhiều comment rườm rà, decorative separators (`# ========================`), docstring trùng lặp, gây khó đọc và không chuyên nghiệp.

**Giải pháp đã áp dụng:**
- Xóa tất cả decorative section separators (`# ========================`)
- Rút gọn docstring chỉ giữ 1 dòng mô tả ngắn gọn ở đầu file
- Loại bỏ inline comments giải thích hiển nhiên (VD: `# Check cooldown`, `# Build messages array`)
- Giữ lại comments thực sự hữu ích (business logic, edge cases)
- Code formatting gọn gàng, professional như production codebase

**Files cleaned:**

| File | Trước | Sau | Giảm |
|------|-------|-----|------|
| `services/cloud_llm_service.py` | ~280 lines | ~170 lines | ~40% |
| `services/chat_service.py` | ~310 lines | ~230 lines | ~26% |
| `services/model_router.py` | ~220 lines | ~140 lines | ~36% |
| `services/rag_service.py` | ~90 lines | ~65 lines | ~28% |
| `services/gemini_service.py` | ~25 lines | ~18 lines | ~28% |
| `repositories/session_store.py` | ~130 lines | ~95 lines | ~27% |
| `repositories/vector_store.py` | ~190 lines | ~130 lines | ~32% |
| `core/config.py` | ~85 lines | ~70 lines | ~18% |
| `main.py` | ~110 lines | ~85 lines | ~23% |
| `api/routes/chat.py` | ~95 lines | ~75 lines | ~21% |

---

### 8. 🦙 Nâng cấp LocalAI Model — Llama 3.1 70B
**Trước:** Llama 3.1 8B Instruct (Q4_K_M) — suy luận hạn chế cho ISO assessment phức tạp.
**Sau:** **Llama 3.1 70B Instruct (Q4_K_M)** — thông minh hơn đáng kể cho chatbot, phân tích ISO gap, kiểm toán bảo mật.

**Thay đổi:**
- Docker memory limits nâng: Backend **6GB**, LocalAI **12GB**, Frontend **2GB**
- LocalAI threads tăng lên **6** (từ 4)
- Inference timeout tăng **180s** (từ 120s) cho model lớn hơn
- LocalAI `start_period` healthcheck tăng **120s** (model 70B load lâu hơn)
- Fallback: Máy <16GB RAM → đổi sang model 8B trong `.env`

**Files changed:**
- `docker-compose.yml` — Memory limits, threads, timeouts
- `.env.example` — Default model → 70B
- `core/config.py` — Default MODEL_NAME → 70B

---

### 9. 📰 Nâng cấp News Pipeline — Dịch & Biên tập Toàn bộ Nội dung
**Trước:** Bài báo bị cắt 6000 ký tự, Cloud API tóm tắt, VinAI dịch tiêu đề riêng.
**Sau:** Cloud API xử lý **dịch + biên tập toàn bộ** trong 1 lần gọi duy nhất.

**Chi tiết thay đổi:**
- Soft limit nâng lên **12000 ký tự** (từ 6000) — không hard truncation
- `max_tokens` output nâng **16000** (từ 8000) — tránh cắt bài dài
- Prompt mới yêu cầu giữ **100% dữ kiện**: tên người, số liệu, mã CVE, ngày tháng, thông số kỹ thuật
- **Không tóm tắt** — dịch/biên tập đầy đủ nội dung chuẩn phát thanh
- Thêm system message role để AI tuân thủ quy tắc chặt hơn
- Thêm phiên âm TTS mới: DDoS, VPN, SSL, TLS, ransomware, blockchain, crypto, HTTPS
- Tách `_fix_pronunciation()` thành static method riêng, dễ mở rộng

**Files changed:**
- `services/summary_service.py` — Prompt rewrite, no truncation, expanded TTS pronunciation

---

## ⚠️ Lưu ý quan trọng

1. **API Key cần thiết**: Cần ít nhất 1 key Open Claude HOẶC OpenRouter để chat hoạt động
2. **CPU Performance**: Nếu dùng máy yếu, tăng `TORCH_THREADS` lên 4-8 và giảm `MAX_CONCURRENT_REQUESTS`
3. **Memory**: Backend cần tối thiểu 2GB RAM, LocalAI cần **8-12GB** cho model 70B GGUF (hoặc 2-4GB cho 8B)
4. **LocalAI là fallback**: Khi cả Cloud APIs đều fail, hệ thống sẽ dùng LocalAI local
5. **Model 70B**: Cần máy ≥16GB RAM. Nếu không đủ, đổi `MODEL_NAME=Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` trong `.env`
