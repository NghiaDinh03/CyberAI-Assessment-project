<div align="center">
  <h1>PhoBERT AI Platform v2.0</h1>
  <p>Hệ thống RAG, Đánh giá ISO 27001 & Tóm tắt Tin Tức Đa Tầng</p>
  <p>
    <a href="README.md">🇬🇧 English</a> | <a href="README_vi.md">🇻🇳 Tiếng Việt</a>
  </p>
</div>

Nền tảng AI on-premise kết hợp đánh giá tuân thủ **ISO 27001:2022**, Tra cứu thông tin (RAG), và Tổng hợp Tin tức Tự động. Hệ thống được triển khai bằng Docker Compose, thiết kế đặc biệt với kiến trúc Fallback đa điểm để đảm bảo tính sẵn sàng (High Availability) lớn nhất.

---

## 🆕 Tính năng Mới trong v2.0

### 🔄 Unified Cloud LLM Service (Open Claude + Fallback Đa Tầng)
- **API Chính mới**: Thay thế các API rời rạc bằng `CloudLLMService` thống nhất, sử dụng **Open Claude** (`gemini-3-pro-preview`).
- **Chuỗi Fallback 3 Tầng**: Open Claude → OpenRouter → LocalAI (on-premise). Khi bất kỳ provider nào lỗi, hệ thống tự động chuyển sang tầng tiếp theo.
- **Multi-Key Round-Robin**: Hỗ trợ nhiều API key mỗi provider, tự động xoay vòng. Khi key bị Rate Limit (HTTP 429), key đó bị chặn 60 giây và hệ thống chuyển sang key kế tiếp.
- **Exponential Backoff Retry**: Logic retry thông minh qua tất cả providers.

### 🧠 Bộ nhớ Hội thoại (Conversation Memory)
- **Trước đây**: Mỗi tin nhắn chat là request độc lập — AI không nhớ gì từ tin nhắn trước.
- **Bây giờ**: Bộ nhớ hội thoại theo session, lưu tối đa **20 tin nhắn gần nhất/session**.
- **Lưu trữ bền vững**: File JSON sessions tồn tại khi container restart.
- **Auto-Cleanup**: Sessions tự hết hạn sau **24 giờ** (TTL có thể cấu hình).
- **API Endpoints mới**: `GET /api/chat/history/{session_id}` và `DELETE /api/chat/history/{session_id}`.

### 🔍 Nâng cấp RAG Pipeline
- **Semantic Chunking**: Tôn trọng cấu trúc Markdown (headers, tables, lists) thay vì cắt ký tự đơn giản.
- **Header Hierarchy Tracking**: Gắn ngữ cảnh header cha vào mỗi chunk để tăng độ chính xác.
- **Tăng Overlap**: 150 ký tự overlap giữa các chunk để bảo toàn ngữ cảnh tốt hơn.
- **Multi-Query Search**: Tạo các biến thể câu hỏi tiếng Việt để tăng recall từ vector store.
- **Cosine Similarity Scoring**: Kết quả được sắp xếp theo điểm liên quan.
- **Source Attribution**: Câu trả lời RAG giờ bao gồm danh sách tài liệu tham khảo đã sử dụng.

### ⚡ Tối ưu Hiệu suất CPU
| Kỹ thuật | Mô tả |
|----------|-------|
| PyTorch Thread Control | `torch.set_num_threads()` cấu hình qua biến `TORCH_THREADS` |
| JIT Optimization | `torch.jit.optimize_for_inference()` cho inference CPU nhanh hơn |
| Semaphore Throttling | Giới hạn request đồng thời tránh CPU overload |
| Cloud-First Strategy | Ưu tiên Cloud API → giảm tải CPU cho local model |
| Batch Chunking | Dịch theo batch 8 tiêu đề/lần, tránh OOM |
| Aggressive Caching | Cache file-based bền vững với quản lý TTL |
| Request Size Limit | Middleware giới hạn body request 2MB |
| Docker Memory Limits | Backend: 4GB, LocalAI: 8GB, Frontend: 1GB |

### 🛡️ Bảo mật & Ổn định
| Tính năng | Chi tiết |
|-----------|----------|
| CORS Whitelist | Cấu hình qua `CORS_ORIGINS` (không còn wildcard `*`) |
| Rate Limiting | Giới hạn tốc độ per-endpoint qua `slowapi` (VD: `10/minute` cho chat) |
| Request Size Limit | Middleware 2MB chống lạm dụng |
| Input Validation | Pydantic schemas với `min_length=1, max_length=2000` |
| Error Boundaries | Custom handlers 404/500, graceful degradation |
| Config Validation | `settings.validate()` chạy khi khởi động để phát hiện lỗi cấu hình |
| Docker Health Checks | Giám sát sức khỏe tự động cho Backend & LocalAI containers |

### 🏗️ Model Router Thông minh
- **Trước đây**: Phân loại câu hỏi bằng regex đơn giản.
- **Bây giờ**: Phân loại semantic theo keyword-weighted qua **7 loại route**: `iso`, `security`, `legal`, `technical`, `news`, `general`, `greeting`.
- Mỗi route kích hoạt system prompt riêng và ngữ cảnh RAG chuyên biệt để tăng độ chính xác.

### 🔧 RAG Service v2.0
- Module `rag_service.py` mới cung cấp interface rõ ràng cho Retrieval-Augmented Generation.
- Sử dụng `CloudLLMService` thay vì gọi trực tiếp LocalAI để phản hồi nhanh hơn.
- Hỗ trợ `retrieve_with_sources()` để trích dẫn nguồn tài liệu trong câu trả lời.
- Kiểm tra ngưỡng liên quan qua phương thức `is_relevant()`.

### 🧹 Code Cleanup — Codebase Chuẩn Production
- **Xóa toàn bộ** decorative section separators và inline comments thừa trên toàn bộ backend.
- **Rút gọn** docstring chỉ giữ 1 dòng mô tả ngắn gọn ở đầu file.
- **Loại bỏ** các comments giải thích hiển nhiên (VD: `# Check cooldown`, `# Build messages array`).
- **Giữ lại** chỉ comments thực sự hữu ích giải thích business logic và edge cases.
- **Kết quả**: Giảm ~25-40% số dòng code trên 10+ file core mà vẫn giữ nguyên chức năng. Codebase giờ đọc như dự án production chuyên nghiệp.

### 🦙 Nâng cấp LocalAI Model — Llama 3.1 70B
- **Trước đây**: Llama 3.1 8B Instruct (Q4_K_M) — suy luận hạn chế cho ISO assessment phức tạp.
- **Bây giờ**: **Llama 3.1 70B Instruct (Q4_K_M)** — thông minh hơn đáng kể cho chatbot, phân tích ISO gap, và kiểm toán bảo mật.
- Docker memory limits nâng lên: Backend **6GB**, LocalAI **12GB**, Frontend **2GB**.
- Inference timeout tăng lên **180s** để phù hợp model lớn hơn.
- Fallback: Nếu máy <16GB RAM, đổi sang model 8B trong `.env`.

### 📰 Nâng cấp Pipeline Tin tức — Dịch & Biên tập Toàn bộ Nội dung
- **Trước đây**: Bài báo bị cắt 6000 ký tự và tóm tắt. Cloud API và VinAI xử lý dịch riêng.
- **Bây giờ**: Cloud API xử lý **dịch + biên tập toàn bộ** trong 1 lần gọi (tối đa 12000 ký tự, không cắt nội dung).
- **Prompt nâng cấp** yêu cầu giữ 100% dữ kiện: tên người, số liệu, mã CVE, ngày tháng, thông số kỹ thuật phải giữ nguyên.
- **Không tóm tắt** — bài báo được dịch/biên tập đầy đủ bằng tiếng Việt chuẩn phát thanh, sẵn sàng cho Text-to-Speech.
- Thêm nhiều từ phiên âm cho TTS: DDoS, VPN, SSL, TLS, ransomware, blockchain, crypto.
- `max_tokens` nâng lên **16000** để không bị cắt output trên bài dài.

---

## 🏗️ Kiến trúc Công nghệ & Các Thành phần Chính

Dự án này sử dụng mô hình Client-Server với sự hỗ trợ của đa dạng AI Models, được phân bổ vào các container trong Docker.

### 1. 🖥️ Frontend (Next.js 15)
- **Giao diện người dùng (UI):** Thiết kế dạng Single Page Application (SPA) siêu tốc, không cần tải lại trang. Các Module được chia thành các Tab chức năng (Analytics, Chat, Form ISO, Tin tức).
- **Client-Side Caching:** Tích hợp bộ nhớ đệm (cache) phía client (React state/ref) cho ứng dụng Tin tức, giúp lưu trữ tạm thời các tab (An ninh mạng, Chứng khoán...) giảm tải băng thông và độ trễ khi chuyển qua lại.
- **Audio Control:** Giao diện điều khiển audio hiện đại, cho phép nghe ngay tin tức tóm tắt trên từng bài báo hoặc thông qua Panel Lịch sử (có logic tắt chéo chống âm thanh đè lên nhau).

### 2. ⚙️ Backend (FastAPI - Python)
Hệ thống API thần tốc đáp ứng mọi request từ Frontend thông qua kiến trúc đa luồng và bảo mật:
- **`cloud_llm_service.py`** 🆕: Client Cloud LLM thống nhất hỗ trợ Open Claude (primary), OpenRouter (fallback), và LocalAI (last resort) với multi-key round-robin và auto-cooldown.
- **`chat_service.py`**: Quản lý trò chuyện với **bộ nhớ hội thoại theo session**, gọi Cloud LLM trước, sau đó truy vấn CSDL Vector qua RAG.
- **`model_router.py`**: Phân loại semantic theo keyword-weighted, điều phối tasks qua 7 loại tới AI model và system prompt phù hợp.
- **`rag_service.py`** 🆕: Pipeline RAG nâng cao với multi-query search, trích dẫn nguồn, và tích hợp Cloud LLM.
- **`summary_service.py`**: Trái tim của hệ thống tóm tắt tin tức. Tích hợp cơ chế **Fallback 3 Tầng & Round-Robin**:
  1. **Open Claude (gemini-3-pro-preview)**: API cloud chính với multi-key rotation và cooldown 60s khi bị rate limit.
  2. **OpenRouter**: Nếu toàn bộ mảng Open Claude Keys bị lỗi, tự chuyển sang pool OpenRouter.
  3. **LocalAI (On-premise)**: Nếu mất mạng hoặc tất cả Cloud API đều sập/hết quota, tự động dùng AI Local làm phương án cuối cùng.
- **`news_service.py`**: Quản lý việc kéo RSS từ các nguồn lớn (The Hacker News, Dark Reading, MarketWatch...). Tích hợp cơ sở dữ liệu `articles_history.json` dọn dẹp (cleanup) vòng đời tuổi thọ 7 ngày.
- **`translation_service.py`**: Dùng Model `VinAI Translate` (135M parameters) dịch tiêu đề trực tiếp bằng CPU, tối ưu với PyTorch JIT và configurable thread control.
- **`session_store.py`** 🆕: Lưu trữ session file-based bền vững cho bộ nhớ hội thoại với TTL 24h và auto-cleanup.

### 3. 💾 Data & Logic Lưu trữ (Folder `data/`)
Đây là bộ não lưu trữ persistent (bền vững) được mount vào Docker:
- **`data/iso_documents/`**: Thư mục bạn vứt file `.md` vào, và ChromaDB sẽ đọc nó để tạo Knowledge Base cho bot ISO.
- **`data/vector_store/`**: Chứa CSDL SQLite Vector của ChromaDB.
- **`data/summaries/`**: Nơi lưu Cache JSON cho chữ và đặc biệt là folder `data/summaries/audio/`.
  - **Cơ chế Audio Caching:** Url của bài báo được băm thành **MD5 Hash**. Hệ thống dùng Edge-TTS chuyển văn bản thành giọng nói tiếng Việt và lưu thành file tĩnh bằng `hash.mp3`. Các url đã có Audio sẽ không bao giờ phải gọi TTS lại lần thứ 2, giúp lướt nhanh cho người sau. Cùng với text history, nó bị xóa sau 7 ngày để giải phóng RAM/Ổ cứng.
- **`data/sessions/`** 🆕: File session hội thoại bền vững (JSON) với auto-expiry.
- **`data/assessments/`**: Lưu lịch sử báo cáo ISO được sinh ra.

---

## 📑 Các Tính năng Chia theo Giao diện (Tabs)

### 🏠 Trang chủ (Dashboard)
- Đồng hồ 4 Múi giờ Thế giới trực tiếp.
- Các nút dẫn hướng nhanh giới thiệu tính năng hệ thống.

### 💬 AI Chat (ISO RAG) — *Nâng cấp trong v2.0*
👉 **[Xem chi tiết Hướng dẫn Cơ chế Hoạt động RAG](./docs/chatbot_rag.md)**
👉 *Dành cho việc train data: [Tiêu chuẩn Format Markdown RAG & PICO](./docs/markdown_rag_standard.md)*
- Ứng dụng Retrieval-Augmented Generation (RAG) với **semantic chunking** và **multi-query search**.
- **Bộ nhớ Hội thoại** 🆕: AI nhớ các tin nhắn trước đó trong session (tối đa 20 tin nhắn).
- **Cloud-First Strategy** 🆕: Ưu tiên Cloud AI (Open Claude) nhanh, fallback sang LocalAI khi cần.
- **Trích dẫn Nguồn** 🆕: Câu trả lời chỉ rõ tài liệu nào đã được sử dụng làm tham khảo.
- **Quản lý Session** 🆕: Xem lịch sử chat hoặc xóa session qua API.

### 📊 Analytics (Monitor) — *Nâng cấp trong v2.0*
👉 **[Xem chi tiết Hướng dẫn Quản trị và Analytics](./docs/analytics_monitoring.md)**
- Dashboard tối thượng theo dõi sức khỏe phần cứng (CPU, RAM).
- Theo dõi các Container và trạng thái Model AI rảnh hay đang bận.
- Quản lý kho ChromaDB (Clear, Reload), Lịch sử hệ thống.
- **Cloud LLM Health Check** 🆕: Giám sát trạng thái Open Claude, OpenRouter, và LocalAI.
👉 *Tham khảo thêm: [Hướng dẫn nạp dữ liệu ChromaDB](./docs/chromadb_guide.md)*

### 📝 Form ISO
👉 **[Xem chi tiết Luồng Data Form Đánh giá ISO](./docs/iso_assessment_form.md)**
- Khảo sát nhanh 20+ câu hỏi về hạ tầng Mạng doanh nghiệp.
- Sinh báo cáo Action Plan bằng AI Llama 3.1 & SecurityLLM.

### 📰 Tin tức (AI News Aggregator)
👉 **[Xem chi tiết Cơ chế Crawl Tin & Sinh Audio TTS Nội bộ](./docs/news_aggregator.md)**
- 3 Chuyên mục tin tức chính. Bài đăng được fetch liên tục.
- Hiển thị bài viết, ấn **🔊 Nghe** hệ thống sẽ tóm tắt -> sinh MP3 -> và phát (Phát từ Cache nếu nghe lần 2).
- **Panel Lịch Sử 7 Ngày Sidebar:** Hiển thị bài báo cũ của tuần, cho phép người dùng click Nghe lại Audio tĩnh đã được tạo trong lịch sử mà không tốn token.

---

## 📚 Hệ thống Tài liệu Kỹ thuật (Docs)
Dự án đi kèm bộ tài liệu phân tích kỹ thuật rất sâu, nằm trong thư mục `docs/`. Bạn có thể đọc chúng để hiểu rõ hơn cách hệ thống hoạt động:
- 📖 **[Kiến trúc Tổng thể (Architecture)](./docs/architecture.md):** Giải thích mô hình Client-Server và luồng dữ liệu.
- 📖 **[Tài liệu API Dữ liệu (API References)](./docs/api.md):** Danh sách các Endpoint API Backend đang hỗ trợ.
- 📖 **[Hướng dẫn Triển khai (Deployment)](./docs/deployment.md):** Các bước để triển khai lên server thật bằng Docker.
- 📖 **[Hướng dẫn Nạp ChromaDB (ChromaDB Guide)](./docs/chromadb_guide.md):** Cơ chế Embed file `.md` thành vector nội bộ.
- 📖 **[Tiêu chuẩn Format Markdown RAG & PICO](./docs/markdown_rag_standard.md):** Định dạng file `.md` chuẩn nhất để giúp Llama 3 hiểu và truy xuất chính xác thông tin.
- 📖 **[Analytics & Monitoring Guide](./docs/analytics_monitoring.md):** Hướng dẫn giám sát và quản trị hệ thống.
- 📖 **[News Aggregator Architecture](./docs/news_aggregator.md):** Cơ chế crawl tin và sinh audio TTS.
- 📖 **[ISO Assessment Form Flow](./docs/iso_assessment_form.md):** Luồng dữ liệu form đánh giá ISO.

---

## 🤖 Hệ thống Mô hình AI (Trí tuệ Nhân tạo)

| # | Model | Provider | Vai trò |
|---|-------|----------|---------|
| 1 | **gemini-3-pro-preview** 🆕 | Open Claude (Cloud) | Bộ não chính cho chat, RAG, và tóm tắt qua Cloud LLM thống nhất |
| 2 | **Llama 3.1 Instruct (70B)** 🆕 | LocalAI (On-premise) | Bộ não fallback nâng cấp: thông minh hơn cho chatbot, ISO assessment, inference local |
| 3 | **SecurityLLM (7B)** | LocalAI (On-premise) | Chuyên gia bảo mật dò lỗi mạng nội bộ |
| 4 | **Gemini 2.5 Flash / OpenRouter** | Cloud API | Provider cloud fallback cho tóm tắt tốc độ cao |
| 5 | **VinAI Translate (135M)** | HuggingFace Transformers | Biên dịch viên tiếng Việt 100% On-server (tối ưu CPU với JIT) |
| 6 | **all-MiniLM-L6-v2** | ChromaDB | Phân mảnh text thành Vector toán học |
| 7 | **Edge-TTS** | Microsoft Service | Text-to-Speech tự nhiên, mượt mà |

---

## 🚀 Cài đặt và Khởi chạy

Kiến trúc chuẩn bị vô cùng đơn giản, tất cả được đóng gói qua `docker-compose`. Mọi vấn đề về DNS hoặc Network Docker đã được tuỳ biến dọn dẹp.

### 1. Clone project và thiết lập biến môi trường
```bash
git clone https://github.com/NghiaDinh03/phobert-chatbot-project.git
cd phobert-chatbot-project
cp .env.example .env
```

### 2. Cấu hình API Keys
Mở file `.env` và cấu hình:

```env
# Cloud LLM chính (Open Claude)
CLOUD_API_KEYS=your_key_1,your_key_2,your_key_3
CLOUD_LLM_API_URL=https://open-claude.com/v1
CLOUD_MODEL_NAME=gemini-3-pro-preview

# (Tùy chọn) OpenRouter làm fallback
OPENROUTER_API_KEYS=your_openrouter_key

# (Tùy chọn) Legacy Gemini keys
GEMINI_API_KEYS=key1,key2,key3
```

> ⚠️ **Lưu ý:** Hệ thống cần ít nhất **1** Cloud API key (Open Claude HOẶC OpenRouter) để chat hoạt động. Hỗ trợ nhiều key phân cách bằng dấu phẩy, hệ thống tự động Round-Robin cân bằng tải!

### 3. Chạy Project bằng 1 lệnh
```bash
docker-compose up --build -d
```
*Lệnh này sẽ tự kéo các image, tải GGUF model vào `/models`, nạp thư viện và chạy 3 container `phobert-frontend`, `phobert-backend`, `phobert-localai` với memory limits và health checks.*

### 4. Truy cập
Mở trình duyệt và vào **http://localhost:3000**

### 5. (Tùy chọn) Tinh chỉnh Hiệu suất
Đối với môi trường hạn chế CPU, điều chỉnh trong `.env`:
```env
TORCH_THREADS=4          # Số threads PyTorch cho dịch thuật
MAX_CONCURRENT_REQUESTS=3 # Số request AI đồng thời tối đa
INFERENCE_TIMEOUT=120     # Timeout LocalAI (giây)
CLOUD_TIMEOUT=60          # Timeout Cloud API (giây)
```

---

## 📊 So sánh Hiệu suất v1.0 vs v2.0

| Chỉ số | v1.0 | v2.0 | Cải thiện |
|--------|------|------|-----------|
| Chat Response (Cloud) | N/A | ~2-5s | 🆕 Mới |
| Chat Response (LocalAI) | 15-30s | 15-30s (chỉ fallback) | Cloud-first strategy |
| Translation Batch | Không chunking | 8 titles/batch | Ổn định hơn |
| Session Persistence | In-memory (mất khi restart) | File-based (bền vững) | ✅ Persistent |
| Conversation Context | Không có | 20 messages/session | ✅ Mới |
| RAG Chunk Quality | Basic split | Semantic + headers | Chính xác hơn |
| API Security | CORS `*` | Whitelist + rate limit | ✅ Bảo mật |
| Error Recovery | Crash | Graceful fallback chain | ✅ Ổn định |

---

*Dự án tập trung vào trải nghiệm Người dùng cuối (End-User) cao cấp, an toàn dữ liệu, chống tràn bộ nhớ, và Backup lỗi hệ thống nhiều tầng vững chắc.*
