# CyberAI Assessment Platform

> Nền tảng đánh giá an ninh mạng tích hợp AI — hỗ trợ inference đa model, phân tích tăng cường bằng RAG, và đánh giá tuân thủ ISO 27001 / TCVN 11930.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**[🇬🇧 English version](README.md)**

---

## Mục lục

- [Tính năng](#tính-năng)
  - [Chatbot AI](#-chatbot-ai)
  - [Đánh giá ISO 27001 / TCVN 11930](#-đánh-giá-iso-27001--tcvn-11930)
  - [Pipeline RAG](#-pipeline-rag)
  - [Quản lý tiêu chuẩn](#-quản-lý-tiêu-chuẩn)
  - [Tìm kiếm web](#-tìm-kiếm-web)
  - [Inference cục bộ kép](#️-inference-cục-bộ-kép)
  - [Giám sát](#-giám-sát)
  - [Bảo mật](#-bảo-mật)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Bắt đầu nhanh](#bắt-đầu-nhanh)
- [So sánh model](#so-sánh-model)
  - [Thông số kỹ thuật model cục bộ](#bảng-1-thông-số-kỹ-thuật-model-cục-bộ)
  - [Model cloud dự phòng](#bảng-2-model-cloud-dự-phòng)
  - [Ma trận lựa chọn model theo tác vụ](#bảng-3-ma-trận-lựa-chọn-model-theo-tác-vụ)
  - [So sánh chế độ inference](#bảng-4-so-sánh-chế-độ-inference)
- [Hạ tầng model](#hạ-tầng-model)
  - [Chuỗi fallback cloud](#chuỗi-fallback-cloud)
  - [Yêu cầu tài nguyên](#yêu-cầu-tài-nguyên)
- [Biến môi trường](#biến-môi-trường)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Tổng quan API](#tổng-quan-api)
  - [Ví dụ request chat](#ví-dụ-request-chat)
  - [Ví dụ request đánh giá](#ví-dụ-request-đánh-giá)
- [Chi tiết pipeline AI](#chi-tiết-pipeline-ai)
  - [Pipeline đánh giá 2 phase](#pipeline-đánh-giá-2-phase)
  - [Chấm điểm tuân thủ có trọng số](#chấm-điểm-tuân-thủ-có-trọng-số)
  - [Chiến lược truy xuất RAG](#chiến-lược-truy-xuất-rag)
  - [Phát hiện prompt injection](#phát-hiện-prompt-injection)
- [Prometheus metrics](#prometheus-metrics)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
  - [AI Chat](#-ai-chat-chatbot)
  - [Đánh giá bảo mật](#-đánh-giá-bảo-mật-form-iso)
  - [Quản lý tiêu chuẩn](#-quản-lý-tiêu-chuẩn-standards)
  - [Analytics & giám sát](#-analytics--giám-sát-analytics)
  - [Template library](#-template-library-templates)
- [Tài liệu](#tài-liệu)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Đóng góp](#đóng-góp)
- [Giấy phép](#giấy-phép)

---

## Tính năng

### 🤖 Chatbot AI

Chat đa model với **18+ model** từ **5 provider** (OpenAI, Google, Anthropic, Ollama, LocalAI). Các tính năng chính:

- **SSE streaming** — phản hồi token-by-token real-time qua `POST /chat/stream`
- **Bộ nhớ phiên** — lưu ngữ cảnh hội thoại bền vững dưới dạng JSON tại `data/sessions/`
- **Định tuyến thông minh** — bộ phân loại intent kết hợp (ChromaDB semantic + keyword fallback) tự động chọn giữa SecurityLLM, Llama, hoặc cloud model
- **Render Markdown** — hỗ trợ đầy đủ GFM qua `react-markdown` + `remark-gfm`
- **Phát hiện prompt injection** — chặn bằng regex: `ignore previous instructions`, prefix `system:`, chèn special token

**Ví dụ luồng chat:**
```
Người dùng: "Đánh giá rủi ro cho hệ thống có 50 servers"
  → Phân loại intent: "security" (confidence 0.87)
  → Model được chọn: SecurityLLM-7B-Q4_K_M.gguf
  → RAG truy xuất: iso27001_annex_a.md, nist_csf_2.md (cosine ≥ 0.35)
  → Streaming phản hồi kèm trích dẫn nguồn
```

### 📋 Đánh giá ISO 27001 / TCVN 11930

Wizard 4 bước với **pipeline AI 2 phase**:

| Bước | Thành phần UI | Mô tả |
|------|--------------|-------|
| 1 | Thông tin hệ thống | Tên tổ chức, quy mô, ngành nghề, chi tiết hạ tầng |
| 2 | Checklist control | Chọn các control đã triển khai (93 cho ISO 27001, 34 cho TCVN 11930) |
| 3 | Upload bằng chứng | Đính kèm file theo từng control (PDF/PNG/DOCX/XLSX, tối đa 10 MB/file) |
| 4 | Phân tích AI | Pipeline 2 phase tạo phân tích GAP + báo cáo định dạng |

**Ví dụ chấm điểm (ISO 27001):**
```
Tổ chức: Acme Corp (200 nhân viên, 50 servers)
Đã triển khai: 62/93 controls → 66.7% tuân thủ
Điểm có trọng số: 148/268 điểm → 55.2% (lỗ hổng nghiêm trọng ở A.8 Technology)

Risk Register:
| # | Control | Mức độ      | L | I | Risk | Khuyến nghị                    |
|---|---------|-------------|---|---|------|--------------------------------|
| 1 | A.8.8   | 🔴 Critical | 4 | 5 | 20   | Triển khai quét lỗ hổng        |
| 2 | A.8.9   | 🔴 Critical | 4 | 4 | 16   | Áp dụng CIS hardening          |
| 3 | A.5.24  | 🟠 High     | 3 | 4 | 12   | Xây dựng kế hoạch ứng phó sự cố |
```

### 📚 Pipeline RAG

**21 tài liệu tiêu chuẩn bảo mật** làm knowledge base, truy xuất thông minh:

| Phân loại | Số lượng | Ví dụ |
|-----------|----------|-------|
| Quốc tế | 8 | ISO 27001 Annex A, ISO 27002:2022, NIST CSF 2.0, NIST SP 800-53 |
| Theo ngành | 4 | PCI DSS 4.0, HIPAA Security Rule, SOC 2, OWASP Top 10 |
| Khu vực | 2 | NIS2 Directive, GDPR Compliance |
| Việt Nam | 4 | TCVN 11930:2017, Luật An ninh mạng 2018, Nghị định 13/2023, Nghị định 85/2016 |
| Nội bộ | 3 | Tiêu chí đánh giá, mẫu phân tích GAP, hướng dẫn hạ tầng |

**Thông số kỹ thuật:**
- Chunking: 600 ký tự, overlap 150 ký tự, nhận biết heading (giữ nguyên hierarchy `# > ## > ###`)
- Embedding: ChromaDB mặc định (all-MiniLM-L6-v2), cosine similarity
- Ngưỡng confidence: `score ≥ 0.35` (distance ≤ 0.65)
- Mở rộng multi-query: tự động sinh từ đồng nghĩa tiếng Việt (`đánh giá` → `kiểm toán`)
- Index theo batch: 100 chunk/batch để tối ưu bộ nhớ

### 📁 Quản lý tiêu chuẩn

Upload tiêu chuẩn tùy chỉnh (JSON/YAML, tối đa 500 control), tự động index vào ChromaDB.

**Tiêu chuẩn tích hợp sẵn:**

| Tiêu chuẩn | Số control | Phân bổ trọng số |
|------------|-----------|-----------------|
| ISO 27001:2022 | 93 | 15 critical, 30 high, 28 medium, 20 low |
| TCVN 11930:2017 | 34 | 8 critical, 12 high, 10 medium, 4 low |

**Định dạng JSON cho tiêu chuẩn tùy chỉnh:**
```json
{
  "standard_name": "Chính sách bảo mật công ty v2",
  "categories": [
    {
      "category": "Kiểm soát truy cập",
      "controls": [
        { "id": "AC-01", "label": "MFA cho tất cả người dùng", "weight": "critical" },
        { "id": "AC-02", "label": "Chính sách xoay vòng mật khẩu", "weight": "high" }
      ]
    }
  ]
}
```

### 🔍 Tìm kiếm web

Tích hợp DuckDuckGo để truy vấn thông tin real-time khi knowledge base không cover được câu hỏi. Bộ phân loại intent tự động kích hoạt khi phát hiện từ khóa tìm kiếm (`latest`, `recent`, `news`, `tìm kiếm`, `tin tức`).

### 🖥️ Inference cục bộ kép

**LocalAI** (Llama 3.1 8B + SecurityLLM 7B) + **Ollama** (Gemma 3n E4B) với fallback cloud tự động.

```
Luồng xử lý request:
  1. PREFER_LOCAL=true → thử LocalAI trước
  2. LocalAI timeout/lỗi → thử Ollama (gemma3n:e4b)
  3. Ollama không khả dụng → chuỗi fallback cloud
  4. Tất cả cloud model thất bại → trả về lỗi thân thiện
```

### 📊 Giám sát

Metrics tương thích Prometheus tại `GET /metrics`:

| Metric | Loại | Mô tả |
|--------|------|-------|
| `cyberai_requests_total` | Counter | Request HTTP theo method, endpoint, status |
| `cyberai_request_duration_seconds` | Histogram | Phân bố latency (11 bucket: 5ms → 10s) |
| `cyberai_active_sessions` | Gauge | Số phiên chat đang hoạt động |
| `cyberai_rag_queries_total` | Counter | Truy vấn RAG theo kết quả (`hit` / `miss`) |
| `cyberai_assessments_total` | Gauge | Tổng số đánh giá đã lưu |

Thống kê hệ thống qua `GET /system/stats`: CPU, RAM, disk (dùng `psutil`).

### 🔒 Bảo mật

| Lớp | Cơ chế | Cấu hình |
|-----|--------|---------|
| Rate limiting | SlowAPI | `10/phút` chat, `3/phút` assess, `5/phút` benchmark |
| Authentication | JWT (HS256) | Secret ≥32 ký tự, hết hạn 60 phút, bắt buộc ở production |
| CORS | FastAPI middleware | Origin cấu hình được (mặc định: `localhost:3000`) |
| Validate input | Pydantic v2 | `max_length=2000` cho chat, path ID an toàn cho file |
| Prompt injection | Regex detection | Chặn `ignore previous`, `system:`, special token |
| Giới hạn request | Upload bằng chứng | 10 MB/file, whitelist extension |

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Network                          │
│                                                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐ │
│  │ Frontend   │  │ Backend   │  │ LocalAI   │  │ Ollama   │ │
│  │ Next.js 15 │  │ FastAPI   │  │ v2.24.2   │  │ latest   │ │
│  │ React 19   │  │ Pydantic  │  │ GGUF      │  │ Gemma 3n │ │
│  │ :3000      │→ │ :8000     │→ │ :8080     │  │ :11434   │ │
│  │ (2 GB)     │  │ (6 GB)    │  │ (12 GB)   │  │ (12 GB)  │ │
│  └───────────┘  └─────┬─────┘  └───────────┘  └──────────┘ │
│                       │                                      │
│              ┌────────┴────────┐                             │
│              │    ChromaDB     │                             │
│              │  (embedded)     │                             │
│              │  cosine HNSW    │                             │
│              │  21 docs →      │                             │
│              │  ~500 chunks    │                             │
│              └────────┬────────┘                             │
│                       │                                      │
│              ┌────────┴────────┐                             │
│              │   Cloud APIs    │                             │
│              │   Open Claude   │                             │
│              │   gateway       │                             │
│              │  (fallback)     │                             │
│              └─────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

**Luồng dữ liệu — pipeline đánh giá:**
```
Frontend (bước 1-3)           Backend                        Model AI
───────────────────           ───────                        ────────
SystemInfo + Controls  →  /iso27001/assess
                               │
                               ├─ Tính điểm có trọng số
                               ├─ Chunk control theo category
                               ├─ RAG: truy xuất tiêu chuẩn liên quan
                               │
                               ├─ Phase 1: SecurityLLM (phân tích GAP)
                               │    └─ JSON gap item theo từng category
                               │    └─ Validate + lọc anti-hallucination
                               │    └─ Chuẩn hóa severity (≤70% critical)
                               │
                               ├─ Phase 2: Llama 3.1 (định dạng báo cáo)
                               │    └─ Bảng Risk Register markdown
                               │    └─ Tóm tắt điều hành
                               │
                               └─ Response: { report, gaps, score, pdf_url }
```

---

## Bắt đầu nhanh

```bash
# Clone repo
git clone https://github.com/your-org/phobert-chatbot-project.git
cd phobert-chatbot-project

# Cấu hình
cp .env.example .env
# Sửa .env — đặt CLOUD_API_KEYS nếu dùng fallback cloud

# Tải model (tùy chọn — cho inference cục bộ)
pip install huggingface_hub hf_transfer
python scripts/download_models.py --model llama --model security

# Khởi chạy
docker compose up -d

# Truy cập
# Giao diện:     http://localhost:3000
# Backend API:   http://localhost:8000
# API docs:      http://localhost:8000/docs
# LocalAI:       http://localhost:8080
# Ollama:        http://localhost:11434
```

> **Lưu ý:** Ollama tự động pull `gemma3n:e4b` khi khởi động lần đầu — không cần tải thủ công.

**Kiểm tra mọi thứ đã chạy:**
```bash
# Xem trạng thái container
docker compose ps

# Health check
curl http://localhost:8000/health

# Kiểm tra LocalAI sẵn sàng chưa
curl http://localhost:8080/readyz

# Xem model đang có trên Ollama
curl http://localhost:11434/api/tags
```

---

## So sánh model

### Bảng 1: thông số kỹ thuật model cục bộ

| Thông số | Meta-Llama 3.1 8B | SecurityLLM 7B | Gemma 3n E4B |
|----------|-------------------|----------------|--------------|
| Provider | LocalAI | LocalAI | Ollama |
| Định dạng | GGUF (Q4_K_M) | GGUF (Q4_K_M) | Native |
| Kích thước file | ~4.9 GB | ~4.2 GB | ~2 GB |
| Context window | 8192 tokens | 8192 tokens | 8192 tokens |
| Port | 8080 | 8080 | 11434 |
| Vai trò chính | Định dạng báo cáo, chat tổng hợp | Phân tích GAP, audit bảo mật | Chat, đánh giá nhanh |
| Tốc độ (ước tính) | ~15-25 tokens/s (CPU) | ~18-28 tokens/s (CPU) | ~20-30 tokens/s (CPU) |
| RAM cần thiết | ~6 GB | ~5 GB | ~4 GB |

### Bảng 2: model cloud (dự phòng)

| Thông số | gemini-3-flash-preview | gemini-3-pro-preview | gpt-5-mini | claude-sonnet-4 | gpt-5 |
|----------|----------------------|---------------------|-----------|----------------|------|
| Ưu tiên | 1 (mặc định) | 2 (complex) | 3 | 4 | 5 |
| Loại tác vụ | iso_analysis, chat | complex | fallback | fallback | fallback |
| Tốc độ phản hồi | Nhanh | Trung bình | Nhanh | Trung bình | Chậm |
| Chất lượng | Cao | Rất cao | Cao | Rất cao | Rất cao |
| Chi phí | Thấp | Trung bình | Trung bình | Cao | Cao |

### Bảng 3: ma trận lựa chọn model theo tác vụ

| Tác vụ | Model ưu tiên | Model dự phòng | Dùng RAG? | Ghi chú |
|--------|--------------|----------------|-----------|---------|
| Chat thông thường | Llama 3.1 8B | gemini-3-flash | Không | Phân loại intent = "general" |
| Hỏi về bảo mật/ISO | SecurityLLM 7B | gemini-3-flash | Có | Phân loại intent = "security" |
| Tìm kiếm web | Llama 3.1 8B | gemini-3-flash | Không | DuckDuckGo tích hợp |
| GAP analysis (phase 1) | SecurityLLM 7B | Cloud chain | Có (top_k=2) | Phân tích theo từng category |
| Tạo báo cáo (phase 2) | Llama 3.1 8B | Cloud chain | Không | Input tối đa 2500 ký tự |

### Bảng 4: so sánh chế độ inference

| Chế độ | Cấu hình | Ưu điểm | Nhược điểm | Khi nào dùng |
|--------|----------|---------|-----------|-------------|
| Local only | `LOCAL_ONLY_MODE=true` | Bảo mật tuyệt đối, không phụ thuộc internet | Cần phần cứng mạnh (16GB+ RAM) | Môi trường air-gapped |
| Hybrid (mặc định) | `PREFER_LOCAL=true` | Cân bằng tốc độ/chất lượng, tự động fallback | Cần cả local + cloud API key | Phần lớn trường hợp |
| Cloud first | `PREFER_LOCAL=false` | Chất lượng cao nhất, không cần GPU | Phụ thuộc internet, tốn chi phí | Phần cứng yếu |

---

## Hạ tầng model

| Provider | Model | Quantization | Kích thước | Port | Vai trò |
|----------|-------|-------------|-----------|------|---------|
| LocalAI | Meta-Llama-3.1-8B-Instruct | Q4_K_M | ~4.9 GB | 8080 | Định dạng báo cáo, chat chung |
| LocalAI | SecurityLLM-7B | Q4_K_M | ~4.2 GB | 8080 | Phân tích GAP, audit bảo mật |
| Ollama | Gemma 3n E4B | native | ~2 GB | 11434 | Chat, đánh giá (tự động pull) |
| Cloud | gemini-3-flash-preview | — | — | — | Fallback cloud chính |
| Cloud | gpt-5-mini | — | — | — | Fallback thứ hai |
| Cloud | claude-sonnet-4 | — | — | — | Fallback thứ ba |

### Chuỗi fallback cloud

Khi model cục bộ không khả dụng hoặc gặp lỗi:

```
gemini-3-flash-preview → gemini-3-pro-preview → gpt-5-mini → claude-sonnet-4 → gpt-5
```

Mỗi model được thử với tất cả API key khả dụng (round-robin, cooldown 30s/key khi bị rate limit).

### Yêu cầu tài nguyên

| Thành phần | RAM (tối thiểu) | RAM (khuyến nghị) | CPU |
|-----------|----------------|-------------------|-----|
| Frontend | 512 MB | 2 GB | 1 core |
| Backend | 2 GB | 6 GB | 2 core |
| LocalAI | 4 GB | 12 GB | 6 thread (`THREADS=6`) |
| Ollama | 2 GB | 12 GB | 4 core |
| **Tổng** | **8.5 GB** | **32 GB** | **4+ core** |

**Tùy chọn tải model:**
```bash
# Kiểm tra trạng thái tất cả model
python scripts/download_models.py --status

# Tải từng model riêng
python scripts/download_models.py --model llama        # 4.9 GB
python scripts/download_models.py --model security     # 4.2 GB
python scripts/download_models.py --model gemma-3-4b   # 2.5 GB
python scripts/download_models.py --model gemma-3-12b  # 7.3 GB
python scripts/download_models.py --model gemma-4-31b  # 19 GB

# Tải tất cả cùng lúc
python scripts/download_models.py --model all
```

---

## Biến môi trường

Các biến chính — xem [`.env.example`](.env.example) để có danh sách đầy đủ kèm chú thích.

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `MODEL_NAME` | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | Model LocalAI chính (phase 2 — báo cáo) |
| `SECURITY_MODEL_NAME` | `SecurityLLM-7B-Q4_K_M.gguf` | Model bảo mật (phase 1 — phân tích GAP) |
| `LOCALAI_URL` | `http://localai:8080` | Endpoint LocalAI |
| `OLLAMA_URL` | `http://ollama:11434` | Endpoint Ollama |
| `PREFER_LOCAL` | `true` | Ưu tiên inference cục bộ thay vì cloud |
| `CLOUD_LLM_API_URL` | `https://open-claude.com/v1` | URL gateway LLM cloud |
| `CLOUD_MODEL_NAME` | `gemini-3-flash-preview` | Cloud model mặc định |
| `CLOUD_API_KEYS` | — | API key phân cách bằng dấu phẩy cho fallback |
| `JWT_SECRET` | — | Secret ký JWT (≥32 ký tự, bắt buộc ở prod) |
| `JWT_EXPIRE_MINUTES` | `60` | Thời gian hết hạn JWT (phút) |
| `CORS_ORIGINS` | `http://localhost:3000` | Origin CORS cho phép (phân cách bằng dấu phẩy) |
| `RATE_LIMIT_CHAT` | `10/minute` | Rate limit endpoint chat |
| `RATE_LIMIT_ASSESS` | `3/minute` | Rate limit endpoint đánh giá |
| `RATE_LIMIT_BENCHMARK` | `5/minute` | Rate limit endpoint benchmark |
| `INFERENCE_TIMEOUT` | `300` | Timeout request LocalAI (giây) |
| `CLOUD_TIMEOUT` | `60` | Timeout API cloud (giây) |
| `CONTEXT_SIZE` | `8192` | Context window LocalAI |
| `THREADS` | `6` | Số thread CPU cho LocalAI |
| `MAX_CONCURRENT_REQUESTS` | `3` | Giới hạn concurrent request backend |
| `ISO_DOCS_PATH` | `/data/iso_documents` | Thư mục knowledge base RAG |
| `VECTOR_STORE_PATH` | `/data/vector_store` | Thư mục lưu ChromaDB |
| `DATA_PATH` | `/data` | Thư mục data gốc |
| `LOG_LEVEL` | `INFO` | Mức log |
| `DEBUG` | `true` | Chế độ debug (nới lỏng validate JWT) |

---

## Cấu trúc dự án

```
phobert-chatbot-project/
├── backend/                        # Ứng dụng FastAPI
│   ├── main.py                     # Entry point, lifespan hook, middleware
│   ├── core/
│   │   ├── config.py               # Settings + validate JWT
│   │   ├── exceptions.py           # Custom exception class
│   │   └── limiter.py              # Cấu hình rate limiter SlowAPI
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py             # POST /chat, /chat/stream, /chat/history
│   │   │   ├── iso27001.py         # POST /iso27001/assess (794 dòng)
│   │   │   ├── standards.py        # GET/POST /standards/
│   │   │   ├── document.py         # POST /documents/upload
│   │   │   ├── health.py           # GET /health
│   │   │   ├── metrics.py          # GET /metrics (Prometheus)
│   │   │   ├── system.py           # GET /system/stats
│   │   │   └── benchmark.py        # GET /benchmark
│   │   └── schemas/
│   │       ├── chat.py             # ChatRequest, ChatResponse
│   │       └── document.py         # Schema tài liệu
│   ├── services/
│   │   ├── chat_service.py         # Routing hội thoại, SSE (820 dòng)
│   │   ├── cloud_llm_service.py    # Cloud/Local/Ollama + fallback (498 dòng)
│   │   ├── model_router.py         # Chọn model theo intent (214 dòng)
│   │   ├── model_guard.py          # Kiểm tra model khả dụng
│   │   ├── rag_service.py          # Pipeline RAG, bộ lọc confidence
│   │   ├── standard_service.py     # Upload & index tiêu chuẩn tùy chỉnh
│   │   ├── web_search.py           # Tích hợp DuckDuckGo
│   │   ├── assessment_helpers.py   # Pipeline 2 phase, scoring, prompt
│   │   ├── controls_catalog.py     # Định nghĩa ISO 27001 + TCVN 11930
│   │   ├── document_service.py     # Xử lý tài liệu
│   │   └── dataset_generator.py    # Sinh dữ liệu huấn luyện
│   ├── repositories/
│   │   ├── vector_store.py         # Wrapper ChromaDB, chunking, search
│   │   └── session_store.py        # Lưu phiên dạng JSON
│   └── tests/                      # Test suite pytest
│       ├── test_chat_service.py
│       ├── test_iso27001_routes.py
│       └── test_rag_service.py
├── frontend-next/                  # Frontend Next.js 15
│   └── src/
│       ├── app/
│       │   ├── chatbot/            # Giao diện chat AI
│       │   ├── form-iso/           # Wizard đánh giá 4 bước
│       │   ├── standards/          # UI quản lý tiêu chuẩn
│       │   ├── analytics/          # Dashboard giám sát
│       │   ├── landing/            # Trang chủ
│       │   └── templates/          # Mẫu báo cáo
│       ├── components/             # Navbar, StepProgress, SystemStats, Toast
│       ├── data/
│       │   ├── standards.js        # ISO 27001 (93) + TCVN 11930 (34) control
│       │   ├── controlDescriptions.js
│       │   └── templates.js
│       └── lib/api.js              # API client gọi backend
├── data/
│   ├── iso_documents/              # 21 tài liệu tiêu chuẩn bảo mật (markdown)
│   ├── knowledge_base/             # Catalog control, training pair (JSON)
│   ├── vector_store/               # ChromaDB persistence
│   ├── assessments/                # Kết quả đánh giá JSON
│   ├── evidence/                   # File bằng chứng đã upload
│   ├── exports/                    # Báo cáo PDF đã tạo
│   ├── sessions/                   # File phiên chat
│   ├── standards/                  # Tiêu chuẩn tùy chỉnh đã upload
│   └── uploads/                    # Upload chung
├── docs/
│   ├── en/                         # Tài liệu tiếng Anh
│   │   ├── architecture.md
│   │   ├── deployment.md
│   │   ├── api.md
│   │   ├── chatbot_rag.md
│   │   ├── iso_assessment_form.md
│   │   ├── chromadb_guide.md
│   │   ├── analytics_monitoring.md
│   │   ├── backup_strategy.md
│   │   └── markdown_rag_standard.md
│   └── vi/                         # Tài liệu tiếng Việt
│       ├── architecture.md
│       ├── deployment.md
│       ├── api.md
│       ├── chatbot_rag.md
│       ├── iso_assessment_form.md
│       ├── chromadb_guide.md
│       └── analytics_monitoring.md
├── scripts/
│   └── download_models.py          # Tool tải model HuggingFace (6 model)
├── nginx/nginx.conf                # Reverse proxy cho production
├── docker-compose.yml              # Stack dev (4 service)
├── docker-compose.prod.yml         # Stack production
└── .env.example                    # Tham chiếu biến môi trường
```

---

## Tổng quan API

Backend cung cấp RESTful API tại `http://localhost:8000`. Tài liệu tương tác có tại [`/docs`](http://localhost:8000/docs) (Swagger UI) và [`/redoc`](http://localhost:8000/redoc) (ReDoc).

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/chat` | POST | Chat AI (response đồng bộ) |
| `/chat/stream` | POST | Chat SSE streaming |
| `/chat/history/{session_id}` | GET | Lấy lịch sử phiên |
| `/iso27001/assess` | POST | Chạy đánh giá ISO 27001 / TCVN |
| `/iso27001/assessments` | GET | Liệt kê đánh giá đã lưu |
| `/iso27001/assessments/{id}` | GET | Lấy đánh giá cụ thể |
| `/iso27001/export/{id}` | GET | Xuất đánh giá PDF |
| `/iso27001/evidence/{id}` | POST | Upload bằng chứng |
| `/standards/` | GET | Liệt kê tiêu chuẩn khả dụng |
| `/standards/` | POST | Upload tiêu chuẩn tùy chỉnh |
| `/documents/upload` | POST | Upload tài liệu để index RAG |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/system/stats` | GET | Thống kê CPU, RAM, disk |

### Ví dụ request chat

**Gửi tin nhắn với model cục bộ:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Phân tích rủi ro cho hệ thống không có firewall", "model": "SecurityLLM-7B-Q4_K_M.gguf"}'
```

**Response:**
```json
{
  "response": "Hệ thống không có firewall đối mặt với các rủi ro nghiêm trọng...",
  "model_used": "SecurityLLM-7B-Q4_K_M.gguf",
  "source": "local",
  "rag_used": true,
  "processing_time": 3.2
}
```

**Gửi tin nhắn với cloud model:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Giải thích Annex A.8.8 về quản lý lỗ hổng kỹ thuật",
    "session_id": "user-001",
    "model": "gemini-3-flash-preview",
    "prefer_cloud": true
  }'
```

**Response:**
```json
{
  "response": "**A.8.8 — Quản lý lỗ hổng kỹ thuật**\n\nĐây là biện pháp kiểm soát ...",
  "model": "gemini-3-flash-preview",
  "session_id": "user-001",
  "provider": "cloud",
  "rag_used": true,
  "sources": [
    { "file": "iso27001_annex_a.md", "title": "ISO 27001:2022 Annex A", "score": 0.72 }
  ]
}
```

### Ví dụ request đánh giá

```bash
curl -X POST http://localhost:8000/iso27001/assess \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_standard": "iso27001",
    "org_name": "Acme Corp",
    "org_size": "medium",
    "industry": "fintech",
    "servers": 50,
    "employees": 200,
    "implemented_controls": ["A.5.1", "A.5.2", "A.5.15", "A.8.1"],
    "model_mode": "hybrid"
  }'
```

**Response (rút gọn):**
```json
{
  "id": "7e0b008d-34d9-4c5b-bf9a-f3de2d53658e",
  "status": "completed",
  "standard": "iso27001",
  "score": {
    "implemented": 4,
    "total": 93,
    "percentage": 4.3,
    "weighted_percentage": 5.6
  },
  "gaps": [
    {
      "id": "A.8.8",
      "severity": "critical",
      "likelihood": 4,
      "impact": 5,
      "risk": 20,
      "gap": "Không có quy trình quét và quản lý lỗ hổng",
      "recommendation": "Triển khai giải pháp quét lỗ hổng tự động"
    }
  ],
  "report": "# Báo cáo đánh giá ISO 27001\n\n## Tóm tắt điều hành\n..."
}
```

Tài liệu API đầy đủ: [`docs/vi/api.md`](docs/vi/api.md).

---

## Chi tiết pipeline AI

### Pipeline đánh giá 2 phase

Đánh giá ISO dùng phương pháp 2 phase chuyên biệt:

**Phase 1 — phân tích GAP (SecurityLLM 7B)**
- Input: control chunk theo category + ngữ cảnh RAG + bằng chứng
- Output: mảng JSON theo category với `{ id, severity, likelihood, impact, risk, gap, recommendation }`
- Anti-hallucination: validate control ID với catalog đã biết, loại bỏ ID không tồn tại
- Chuẩn hóa severity: nếu >70% bị đánh critical, phân phối lại thực tế (~25% critical, 25% high, 30% medium, 20% low)
- Nhúng few-shot example trong prompt để đảm bảo output JSON nhất quán

**Phase 2 — tạo báo cáo (Llama 3.1 8B)**
- Input: gap item tổng hợp + thông tin hệ thống + điểm có trọng số
- Output: báo cáo markdown với bảng Risk Register, tóm tắt điều hành
- Công thức rủi ro: `Risk = Likelihood × Impact` (thang 1–5 mỗi chiều, risk tối đa = 25)

### Chấm điểm tuân thủ có trọng số

Control được gán trọng số theo mức độ quan trọng:

| Trọng số | Điểm | Ví dụ |
|----------|------|-------|
| Critical | 4 điểm | A.5.1 Chính sách bảo mật, A.5.15 Kiểm soát truy cập, A.8.1 Endpoint security |
| High | 3 điểm | A.5.9 Kiểm kê tài sản, A.6.1 Sàng lọc nhân sự, A.7.1 Vành đai vật lý |
| Medium | 2 điểm | A.5.7 Threat intelligence, A.7.6 Khu vực an toàn, A.8.6 Capacity |
| Low | 1 điểm | A.5.6 Liên lạc chuyên gia, A.5.11 Hoàn trả tài sản, A.7.7 Bàn sạch |

**Công thức:** `Điểm trọng số = Σ(trọng số control đã triển khai) / Σ(trọng số tất cả control) × 100%`

**Ví dụ:** 62/93 control đã triển khai, nhưng chủ yếu ở mức low/medium → điểm trọng số có thể chỉ đạt 55.2% dù đếm đơn giản là 66.7%.

### Chiến lược truy xuất RAG

```
Truy vấn người dùng
    │
    ├─ Mở rộng multi-query
    │   "đánh giá iso 27001" → ["đánh giá iso 27001", "tiêu chuẩn đánh giá iso 27001"]
    │   "đánh giá rủi ro" → ["đánh giá rủi ro", "kiểm toán rủi ro"]
    │
    ├─ Tìm kiếm cosine ChromaDB (mỗi query mở rộng, top_k=5)
    │   └─ Loại trùng lặp theo (source, chunk_index)
    │
    ├─ Bộ lọc confidence (score ≥ 0.35)
    │   └─ Đếm hit/miss qua Prometheus counter
    │
    └─ Trả về context + trích dẫn nguồn
        └─ Sources: [{ file, title, score }]
```

### Phát hiện prompt injection

Chat service chặn tin nhắn khớp với các pattern sau:
- `ignore previous instructions`, `disregard all prior`
- `you are now`, `act as`, `forget everything`
- Special token: `<|im_start|>`, `<|im_end|>`, `<|eot_id|>`
- Prefix `system:` ở đầu tin nhắn

Request bị chặn trả về HTTP 400 với lỗi chung (không tiết lộ chi tiết pattern).

---

## Prometheus metrics

Cấu hình Prometheus để scrape backend:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: cyberai
    static_configs:
      - targets: ['backend:8000']
    scrape_interval: 30s
```

**Các metric khả dụng:**

| Metric | Loại | Label |
|--------|------|-------|
| `cyberai_requests_total` | Counter | `method`, `endpoint`, `status` |
| `cyberai_request_duration_seconds` | Histogram | `endpoint` |
| `cyberai_active_sessions` | Gauge | — |
| `cyberai_rag_queries_total` | Counter | `result` (`hit` / `miss`) |
| `cyberai_assessments_total` | Gauge | — |

**Histogram bucket:** 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s

---

## Hướng dẫn sử dụng

Nền tảng có 4 công cụ chính, truy cập qua giao diện web tại `http://localhost:3000`:

### 🤖 AI Chat (`/chatbot`)

Trợ lý AI chuyên bảo mật, hỗ trợ tra cứu ISO 27001, TCVN 11930, và các tiêu chuẩn bảo mật khác.

| Thao tác | Mô tả |
|----------|-------|
| **Input** | Gõ câu hỏi vào ô chat (tối đa 2000 ký tự) |
| **Chọn model** | Click dropdown phía trên để chọn model (18+ model từ 5 provider) |
| **Output** | Phản hồi streaming real-time, render Markdown với bảng và code block |
| **Phiên chat** | Tự động lưu — có thể tạo phiên mới, xóa, hoặc chuyển qua lại |

**Ví dụ câu hỏi:**
- `"Kiểm soát truy cập là gì?"` → phân loại intent "security", dùng SecurityLLM + RAG
- `"Giải thích Annex A ISO 27001"` → truy xuất tài liệu từ knowledge base
- `"ISO 27001 vs SOC 2 khác nhau thế nào?"` → so sánh tiêu chuẩn với nguồn trích dẫn

**Luồng xử lý bên trong:**
```
Tin nhắn → Phát hiện prompt injection → Phân loại intent
  → Chọn model (local/cloud) → Truy xuất RAG (nếu cần)
  → Sinh response → Streaming về client
```

### 📋 Đánh giá bảo mật (`/form-iso`)

Wizard 4 bước đánh giá tuân thủ đa tiêu chuẩn với AI phân tích tự động.

**Bước 1 — thông tin hệ thống:**

| Field | Kiểu | Ví dụ |
|-------|------|-------|
| Tên tổ chức | Text | "Công ty NGS" |
| Quy mô | Select | small / medium / large / enterprise |
| Ngành nghề | Text | "Công nghệ thông tin" |
| Số nhân viên | Number | 155 |
| Số nhân viên IT | Number | 100 |
| Số server | Number | 24 |
| Firewall | Text | "sophos, pfsense" |
| VPN | Checkbox | Có / Không |
| Cloud provider | Text | "AWS" hoặc "Không sử dụng" |
| Antivirus | Text | "kaspersky" |
| Backup | Text | "veeam" |
| SIEM | Text | "elk, qradar" |
| Mô tả hạ tầng mạng | Textarea | Mô tả sơ đồ mạng dạng text |

**Bước 2 — checklist control:**
- Chọn tiêu chuẩn: ISO 27001 (93 control), TCVN 11930 (34 control), hoặc tiêu chuẩn tùy chỉnh đã upload
- Tick các control đã triển khai trong tổ chức
- Mỗi control hiển thị trọng số (critical/high/medium/low) và mô tả chi tiết

**Bước 3 — upload bằng chứng (tùy chọn):**
- Đính kèm file theo từng control (PDF/PNG/DOCX/XLSX/CSV/TXT/LOG/CONF/XML/JSON)
- Tối đa 10 MB/file
- AI tự động extract nội dung text từ file để phân tích

**Bước 4 — phân tích AI:**
- Chọn chế độ model: `hybrid` (mặc định), `local`, hoặc `cloud`
- Bấm "Phân tích" → backend chạy pipeline 2 phase
- Kết quả hiển thị: điểm tuân thủ, Risk Register, tóm tắt điều hành, gap item chi tiết

**Output mẫu:**

| Thành phần | Nội dung |
|-----------|---------|
| Điểm tuân thủ | Gauge chart hiển thị % (đếm đơn giản + có trọng số) |
| Risk Register | Bảng với severity, likelihood, impact, risk score, khuyến nghị |
| Báo cáo | Markdown đầy đủ — có thể xuất PDF |
| Lịch sử | Tất cả đánh giá được lưu, xem lại bất kỳ lúc nào |

### 📁 Quản lý tiêu chuẩn (`/standards`)

Quản lý knowledge base tiêu chuẩn bảo mật.

| Thao tác | Input | Output |
|----------|-------|--------|
| Xem danh sách | — | Tất cả tiêu chuẩn có sẵn (built-in + custom) |
| Upload mới | File JSON/YAML theo schema | Tiêu chuẩn mới xuất hiện trong danh sách, tự động index vào ChromaDB |
| Xóa | Chọn tiêu chuẩn custom | Xóa khỏi hệ thống |
| Tìm kiếm | Gõ keyword | Lọc danh sách theo tên |

**Schema file upload:**
```json
{
  "id": "my_standard",
  "name": "Tên tiêu chuẩn",
  "version": "1.0",
  "controls": [
    {
      "category": "1. Tên nhóm",
      "controls": [
        { "id": "CTL.01", "label": "Tên control", "weight": "critical" }
      ]
    }
  ]
}
```

### 📊 Analytics & giám sát (`/analytics`)

Dashboard real-time hiển thị trạng thái hệ thống và lịch sử đánh giá.

| Panel | Nội dung | Nguồn dữ liệu |
|-------|---------|---------------|
| System stats | CPU, RAM, disk usage | `GET /system/stats` |
| Assessment history | Danh sách đánh giá đã chạy, trạng thái, điểm | `GET /iso27001/assessments` |
| Compliance heatmap | Bản đồ nhiệt theo domain Annex A | Từ đánh giá gần nhất |
| RAG stats | Hit/miss ratio, số document đã index | `GET /metrics` |

### 📝 Template library (`/templates`)

Thư viện mẫu hệ thống mạng thực tế để thử nghiệm đánh giá nhanh — không cần nhập liệu từ đầu. Chọn template → tự động điền thông tin hệ thống → chuyển sang bước 2.

---

## Tài liệu

| Tài liệu | Mô tả |
|-----------|-------|
| [Kiến trúc](docs/vi/architecture.md) | Thiết kế hệ thống, tương tác giữa các service, luồng dữ liệu |
| [Hướng dẫn triển khai](docs/vi/deployment.md) | Deploy production, Nginx, quy hoạch tài nguyên |
| [Tham chiếu API](docs/vi/api.md) | Tài liệu endpoint đầy đủ |
| [Chatbot & RAG](docs/vi/chatbot_rag.md) | Pipeline chat, chiến lược RAG, thiết kế prompt |
| [Đánh giá ISO](docs/vi/iso_assessment_form.md) | Wizard đánh giá, pipeline 2 phase, cách tính điểm |
| [Hướng dẫn ChromaDB](docs/vi/chromadb_guide.md) | Cài đặt vector store, quản lý collection |
| [Phân tích & giám sát](docs/vi/analytics_monitoring.md) | Prometheus metrics, cài đặt dashboard |

Phiên bản tiếng Anh: [`docs/en/`](docs/en/)

---

## Công nghệ sử dụng

| Tầng | Công nghệ | Chi tiết |
|------|-----------|---------|
| **Backend** | Python 3.10, FastAPI 0.115+, Pydantic v2 | Uvicorn ASGI, hỗ trợ async |
| **Vector store** | ChromaDB 0.5+ | Embedded PersistentClient, cosine HNSW |
| **Frontend** | Next.js 15.1, React 19 | CSS Modules, lucide-react, react-markdown |
| **AI cục bộ** | LocalAI v2.24.2 | Inference GGUF, MMAP enabled, context 8192 |
| **AI cục bộ** | Ollama (latest) | Kiến trúc Gemma 3n, tự động pull |
| **AI cloud** | Open Claude gateway | Routing đa model (Gemini, GPT, Claude) |
| **Tìm kiếm** | DuckDuckGo Search 6.2+ | Thông tin web real-time |
| **Metrics** | Prometheus Client 0.20+ | Counter, Gauge, Histogram |
| **Bảo mật** | SlowAPI, JWT (HS256) | Rate limiting, token auth |
| **Hạ tầng** | Docker Compose | 4 service, health check, resource limit |
| **Production** | Nginx reverse proxy | TLS termination, static caching |
| **Xuất PDF** | WeasyPrint 62+ | Chuyển đổi HTML → PDF |

---

## Đóng góp

1. Fork repository
2. Tạo nhánh feature (`git checkout -b feature/tinh-nang-cua-ban`)
3. Commit thay đổi (`git commit -m 'Thêm tính năng mới'`)
4. Push lên nhánh (`git push origin feature/tinh-nang-cua-ban`)
5. Mở Pull Request

Đảm bảo tất cả test pass trước khi gửi PR:

```bash
cd backend && python -m pytest tests/ -v
```

---

## Giấy phép

Dự án được cấp phép theo MIT License. Xem file [LICENSE](LICENSE) để biết chi tiết.
