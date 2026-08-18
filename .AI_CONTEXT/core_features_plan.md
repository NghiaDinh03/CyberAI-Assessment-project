# Kế Hoạch 3 Tính Năng Core — CyberAI Assessment Platform

> **Ngày tạo:** 2026-05-06  
> **Vị trí:** `.AI_CONTEXT/` (plan nội bộ)  
> **Thay đổi lớn:** Bỏ SecurityLLM (quá yếu), bỏ ChromaDB RAG, dùng gemma4 + Cloud

---

## 📑 Mục Lục

1. [Tổng Quan & Model Stack](#1-tổng-quan--model-stack)
2. [Tính Năng 1: AI Chat](#2-tính-năng-1-ai-chat)
3. [Tính Năng 2: Đánh Giá Hệ Thống](#3-tính-năng-2-đánh-giá-hệ-thống)
4. [Tính Năng 3: Output Báo Cáo IT Audit](#4-tính-năng-3-output-báo-cáo-it-audit)
5. [Xử Lý Bằng Chứng (Evidence)](#5-xử-lý-bằng-chứng-evidence)
6. [Bảo Mật Thông Tin](#6-bảo-mật-thông-tin)
7. [Roadmap & Ước Tính](#7-roadmap--ước-tính)

---

## 1. Tổng Quan & Model Stack

### Model Stack mới (đơn giản hóa)

| Vai trò | Model | Nơi chạy | Ghi chú |
|---------|-------|----------|---------|
| **Local chính** | gemma4:latest | Ollama | Mạnh nhất, default cho mọi task |
| **Local nhẹ** | gemma3n:e4b | Ollama | Nhanh, phù hợp task đơn giản |
| **Local cực nhẹ** | gemma3n:e2b | Ollama | Cực nhanh, fallback khi RAM thấp |
| **Local nặng** | gemma3:27b | Ollama | Chất lượng cao, cần nhiều RAM |
| **Cloud chính** | deepseek-v4-flash | DeepSeek API | Báo cáo formatting, fallback |
| **Cloud tùy chọn** | gemini-3.1-pro-preview | Google AI Studio | Người dùng chọn trong UI |
| **Cloud tùy chọn** | gpt-4o-mini | OpenAI | Người dùng chọn trong UI |

### Tại sao bỏ SecurityLLM?

- SecurityLLM-7B yếu hơn gemma4 về mọi mặt: context window nhỏ, output JSON hay lỗi, hay hallucinate control IDs
- gemma4 xử lý được cả Phase 1 (GAP analysis) lẫn Phase 2 (report) nếu prompt tốt
- Giảm complexity: 1 local model thay vì 2

### Tại sao bỏ ChromaDB RAG?

- ChromaDB embedding search cho ISO documents không mang lại giá trị đủ lớn
- Tài liệu ISO/TCVN đã được nhúng sẵn vào prompt qua `controls_catalog.py`
- Evidence text được xử lý trực tiếp (OCR → chunk → inject vào prompt)
- Giảm dependency, giảm RAM, giảm complexity

### Luồng xử lý tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                    CYBERAI PLATFORM                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  1. AI CHAT  │  │  2. ASSESSMENT   │  │  3. REPORT   │  │
│  │              │  │                  │  │    OUTPUT     │  │
│  │ Hỏi đáp ATTT │  │ TCVN + ISO 27001 │  │ Markdown     │  │
│  │ Phân tích log│  │ Per-control      │  │ JSON         │  │
│  │ Web search   │  │ Evidence verdict  │  │ XLSX + PDF   │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────┬───────┘  │
│         │                   │                    │          │
│         └───────────────────┼────────────────────┘          │
│                             │                               │
│                    ┌────────▼─────────┐                     │
│                    │  MODEL ROUTER    │                     │
│                    │  gemma4 (local)  │                     │
│                    │  DeepSeek (cloud)│                     │
│                    │  + user selector │                     │
│                    └──────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### UI Model Selector cho Chatbot

Khi người dùng chọn chế độ **Cloud** hoặc **Hybrid**, UI hiển thị dropdown chọn model:

```
┌─────────────────────────────────────────────────┐
│  Chế độ AI: [Local ▼]  [Hybrid]  [Cloud]       │
│                                                 │
│  Nếu chọn Cloud/Hybrid:                        │
│  ┌─────────────────────────────────────────┐    │
│  │ Cloud Model: [deepseek-v4-flash    ▼]  │    │
│  │              ├─ deepseek-v4-flash       │    │
│  │              ├─ gemini-3.1-pro-preview  │    │
│  │              └─ gpt-4o-mini            │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  Nếu chọn Local:                               │
│  ┌─────────────────────────────────────────┐    │
│  │ Local Model: [gemma4:latest        ▼]  │    │
│  │              ├─ gemma4:latest (default) │    │
│  │              ├─ gemma3:27b (nặng, cần RAM)│   │
│  │              ├─ gemma3n:e4b (nhẹ, nhanh) │   │
│  │              └─ gemma3n:e2b (cực nhẹ)    │   │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

**Backend cần sửa:**
- `cloud_llm_service.py`: Thêm DeepSeek API provider
- `TASK_MODEL_MAP`: deepseek-v4-flash làm default cloud
- `FALLBACK_CHAIN`: deepseek-v4-flash → gemini → gpt-4o-mini
- API endpoint: thêm `cloud_model` param

**Frontend cần sửa:**
- `form-iso/page.js`: Thêm model selector dropdown
- `chatbot/page.js`: Thêm model selector dropdown
- `settings/page.js`: Thêm default model configuration
- `lib/api.js`: Gửi `cloud_model` param trong request

---

## 2. Tính Năng 1: AI Chat

### 2.1 Mô tả

Người dùng hỏi đáp về ATTT, gửi log để phân tích, tìm kiếm thông tin. AI trả lời bằng tiếng Việt, có trích nguồn.

### 2.2 Luồng xử lý (9 bước)

```
Bước 1: NHẬN INPUT
├── Tin nhắn text từ người dùng
├── File đính kèm (tùy chọn)
├── Session ID (lịch sử hội thoại)
└── Detect ngôn ngữ (VI/EN)

Bước 2: KIỂM TRA BẢO MẬT
├── Phát hiện prompt injection
│   ├── "ignore previous instructions"
│   ├── "you are now" / "act as"
│   └── "<|im_start|>" / "system:" prefix
├── Làm sạch input
└── Kiểm tra rate limit

Bước 3: PHÂN LOẠI Ý ĐỊNH (Intent)
├── Semantic: ChromaDB in-memory intent_classifier (threshold 0.6)
├── Keyword fallback (regex)
│   ├── ISO_KEYWORDS → route "security"
│   ├── SEARCH_KEYWORDS → route "search"
│   └── Mặc định → route "general"
└── Kết quả: {intent, confidence, route}

Bước 4: CHỌN MODEL
├── Route "security" → gemma4 (local), có context ISO/TCVN
├── Route "search" → gemma4 + web search
├── Route "general" → gemma4, không context
└── Fallback: gemma4 → DeepSeek (cloud) nếu local fail

Bước 5: TẠO CONTEXT
├── Nếu "security": lấy context từ controls_catalog + knowledge base
├── Nếu "search": gọi DuckDuckGo/SearXNG (timeout 3s)
├── Lịch sử hội thoại (2-10 tin nhắn gần nhất)
└── Phát hiện log analysis (JSON payload, Event ID, timestamp)

Bước 6: XÂY DỰNG PROMPT
├── Chọn system prompt theo route
│   ├── CHAT_SECURITY (ATTT + context)
│   ├── CHAT_SEARCH (tổng hợp web)
│   ├── CHAT_GENERAL (kiến thức chung)
│   └── CHAT_LOG_ANALYSIS (SOC analyst format)
├── Ghép: system prompt + context + history + user message
└── Kiểm tra token budget (max ~6000 cho gemma4)

Bước 7: GỌI MODEL
├── Ưu tiên: gemma4 (Ollama) → DeepSeek (Cloud)
├── Streaming: token-by-token qua SSE (Ollama)
├── Non-streaming: single response (Cloud)
└── Xử lý lỗi: timeout → retry → fallback model

Bước 8: XỬ LÝ KẾT QUẢ
├── Làm sạch special tokens (Llama/Gemma artifacts)
├── Log analysis: đảm bảo có "Nhận định:" + "Mức độ:"
├── Thêm trích nguồn [source:N] nếu có
└── Lưu vào session history

Bước 9: TRẢ KẾT QUẢ
├── Streaming: SSE events (routing → thinking → tokens → done)
└── Non-streaming: JSON {response, model, sources, tokens}
```

### 2.3 Files liên quan

| File | Vai trò |
|------|---------|
| [`backend/services/chat_service.py`](../backend/services/chat_service.py) | Điều phối chính — routing, streaming, session |
| [`backend/services/model_router.py`](../backend/services/model_router.py) | Phân loại ý định + chọn model |
| [`backend/services/cloud_llm_service.py`](../backend/services/cloud_llm_service.py) | Gọi LLM (Ollama, Cloud) |
| [`backend/prompts/defaults.py`](../backend/prompts/defaults.py) | System prompts theo route |
| [`backend/api/routes/chat.py`](../backend/api/routes/chat.py) | HTTP endpoints |

### 2.4 Cần sửa

| # | Vấn đề | Mức | Cách sửa |
|---|--------|-----|----------|
| C1 | SecurityLLM vẫn được gọi trong model router | 🔴 | Chuyển tất cả sang gemma4 |
| C2 | RAG context quá dài cho local model | 🟠 | Cắt RAG context theo token budget |
| C3 | Log analysis output vẫn có markdown headings | 🟡 | Post-processing strip `#` headers |
| C4 | Chưa có DeepSeek API provider | 🔴 | Thêm DeepSeek vào cloud_llm_service.py |
| C5 | UI chưa có model selector dropdown | 🟠 | Thêm dropdown chọn model ở chatbot + form-iso |

---

## 3. Tính Năng 2: Đánh Giá Hệ Thống

### 3.1 Mô tả

Đánh giá tuân thủ theo TCVN 11930:2017 (34 controls) và ISO 27001:2022 (93 controls). Người dùng điền form, upload bằng chứng → AI phân tích từng control → xuất báo cáo.

### 3.2 Luồng xử lý (4 Phases)

```
═══════════════════════════════════════════════════════════
PHASE 0: THU THẬP INPUT (Frontend Form)
═══════════════════════════════════════════════════════════

Bước 0.1: Thông tin tổ chức
├── Tên, ngành, quy mô, số nhân viên, IT staff
└── Chọn tiêu chuẩn: ISO 27001 / TCVN 11930 / Custom

Bước 0.2: Hạ tầng
├── Servers, Firewalls, VPN, Cloud, Antivirus
├── SIEM, Backup, sự cố 12 tháng
└── Mô tả chi tiết

Bước 0.3: Checklist controls
├── ISO 27001: 93 controls × 4 nhóm (A.5/A.6/A.7/A.8)
├── TCVN 11930: 34 controls × 5 nhóm
├── Tick: đã triển khai / chưa
└── Upload bằng chứng per control (max 10MB/file)

Bước 0.4: Chọn chế độ AI
├── Local: gemma4 cho cả 2 phase
├── Hybrid: gemma4 (Phase 1) + Cloud (Phase 2)
└── Cloud: Cloud cho cả 2 phase

Bước 0.5: Submit → POST /api/iso27001/assess
├── Tạo assessment_id (UUID)
├── Tính compliance% sơ bộ (weighted)
├── Build evidence_context
└── Trigger background task

═══════════════════════════════════════════════════════════
PHASE 1: XỬ LÝ BẰNG CHỨNG (Background)
═══════════════════════════════════════════════════════════

Bước 1.1: Nhận diện loại file
├── .txt, .log, .csv, .xml, .json → Đọc trực tiếp
├── .pdf → pypdf extract text
│   ├── Có text layer → extract
│   └── Scanned (< 50 chars) → OCR (Tesseract)
├── .docx → python-docx (paragraphs + tables)
├── .xlsx → openpyxl (rows + sheets)
└── .png, .jpg → OCR (Tesseract)

Bước 1.2: Chuẩn hóa text
├── Loại bỏ noise (header, footer, số trang)
├── Chuẩn hóa whitespace
└── Giữ nguyên cấu trúc (headings, lists, tables)

Bước 1.3: Lọc thông tin nhạy cảm (Privacy Filter)
├── SĐT VN: 0xxxxxxxxx → [SĐT]
├── Email → [EMAIL]
├── CMND/CCCD → [CMND]
├── IP nội bộ → [IP]
├── API key/token → [BI_MAT]
└── Hostname nội bộ → [TEN_MAY]

Bước 1.4: Chia nhỏ (Chunking)
├── 700 tokens/chunk (~2800 chars)
├── Overlap: 80 tokens (~320 chars)
├── Tách theo paragraph trước, rồi sentence
└── Giữ overlap từ chunk trước

Bước 1.5: Map bằng chứng → control
├── Ưu tiên: user gán (từ form)
├── Filename pattern: "policy" → A.5.1, "firewall" → A.8.20
└── Content keyword (500 chars đầu)

Bước 1.6: Chấm điểm chất lượng bằng chứng
├── Completeness: file có đủ thông tin? (0-1)
├── Freshness: file mới hay cũ? (>12 tháng = outdated)
├── Relevance: nội dung liên quan control? (0-1)
└── Overall: weighted average

═══════════════════════════════════════════════════════════
PHASE 2: PHÂN TÍCH AI (Background — 2 sub-phases)
═══════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────┐
│ Phase 2A: GAP Analysis (Per Control Group)          │
│ Model: gemma4 (local) hoặc DeepSeek (cloud)         │
└─────────────────────────────────────────────────────┘

Bước 2A.1: Chia controls thành nhóm nhỏ
├── Mỗi nhóm: 5-8 controls (cùng category)
├── ISO 27001: 93 controls → ~15 nhóm
├── TCVN 11930: 34 controls → ~6 nhóm
└── Mỗi nhóm = 1 prompt (fits context window gemma4)

Bước 2A.2: Xử lý từng nhóm
Với mỗi nhóm control:
├── Load definitions (5-8 control)
├── Load bằng chứng đã xử lý cho nhóm này
├── Tóm tắt bằng chứng (gemma4, max 256 tokens)
│   ├── Input: raw evidence (max 8KB, lấy cuối)
│   ├── Output: bullet list (controls/artifacts/gaps)
│   └── Fallback: rỗng nếu lỗi
├── Build prompt compact
│   ├── "Bạn là ISO Auditor chuyên nghiệp..."
│   ├── Fields: tiêu chuẩn, nhóm, % tuân thủ
│   ├── Tóm tắt hệ thống (max 400 chars)
│   ├── Tóm tắt bằng chứng (max 600 chars)
│   ├── Controls đã đạt / chưa đạt
│   └── Few-shot examples
├── Gọi model (temperature=0.1)
│   ├── Thử gemma4 trước (nếu hybrid/local)
│   ├── Fallback DeepSeek nếu gemma4 fail
│   └── Retry tối đa 3 lần nếu JSON lỗi
├── Validate output
│   ├── Parse JSON array
│   ├── Anti-hallucination: reject ID không hợp lệ
│   ├── Validate: severity, likelihood, impact, risk
│   ├── Verdict: satisfied/partial/missing/not_applicable
│   └── Clamp confidence [0.0, 1.0]
└── Fallback nếu tất cả fail
    └── Tạo gap từ metadata control

Bước 2A.3: Tổng hợp kết quả
├── Gộp tất cả gap items
├── Chuẩn hóa severity (>70% critical → phân bổ lại)
├── Tạo raw_analysis (Markdown table)
└── Log: tổng gaps, counts theo severity

┌─────────────────────────────────────────────────────┐
│ Phase 2B: Định dạng báo cáo                        │
│ Model: DeepSeek (cloud) hoặc gemma4 (local)         │
└─────────────────────────────────────────────────────┘

Bước 2B.1: Nén kết quả Phase 2A
├── Input: raw_analysis (có thể 10K+ chars)
├── Trích: table lines, severity counts, summary
└── Output: max 2500 chars

Bước 2B.2: Build prompt formatting
├── "Bạn là chuyên gia trình bày báo cáo..."
├── Thông tin tổ chức: tên, ngành, quy mô
├── Metrics: % tuân thủ, score, max_score
├── Weight breakdown: critical/high/medium/low
├── Risk register nén từ Phase 2A
└── Cấu trúc bắt buộc: 5 phần

Bước 2B.3: Gọi model
├── Temperature: 0.5 (sáng tạo hơn cho formatting)
├── Max tokens: 10000
└── Output: Markdown report

Bước 2B.4: Tạo Structured JSON
├── Parse severity counts từ raw_analysis
├── Tính compliance tier (high/medium/low/critical)
├── Trích top gaps theo severity
├── Build weight_breakdown
└── Package: assessment_date, standard, organization,
    compliance, risk_summary, top_gaps, controls[]

═══════════════════════════════════════════════════════════
PHASE 3: LƯU & TRẢ KẾT QUẢ
═══════════════════════════════════════════════════════════

Bước 3.1: Lưu assessment
├── status: "completed"
├── result: {report, json_data, model_used}
└── updated_at: timestamp

Bước 3.2: Frontend polling
├── GET /api/iso27001/assessments/{id}
├── Progress: {message, percent}
└── Khi status="completed" → render báo cáo

Bước 3.3: Export (tùy chọn)
├── SoA .xlsx → Statement of Applicability
├── Risk Register .xlsx → Bảng rủi ro
└── Report .md → Báo cáo đầy đủ
```

### 3.3 Files liên quan

| File | Vai trò |
|------|---------|
| [`backend/api/routes/iso27001.py`](../backend/api/routes/iso27001.py) | HTTP endpoints, upload evidence, background task |
| [`backend/services/chat_service.py`](../backend/services/chat_service.py:727) | `assess_system()` — điều phối chính |
| [`backend/services/assessment_helpers.py`](../backend/services/assessment_helpers.py) | Build prompt, validate, infer gap |
| [`backend/services/controls_catalog.py`](../backend/services/controls_catalog.py) | Định nghĩa controls, scoring, grouping |
| [`backend/services/soa_exporter.py`](../backend/services/soa_exporter.py) | Xuất SoA .xlsx |
| [`backend/services/document_service.py`](../backend/services/document_service.py) | Upload + parse documents |
| [`backend/prompts/defaults.py`](../backend/prompts/defaults.py) | Prompts đánh giá |

### 3.4 Cần sửa

| # | Vấn đề | Mức | Cách sửa |
|---|--------|-----|----------|
| A1 | Chunking theo category (37 controls A.5) → quá tải | 🔴 | `get_control_groups()` — chia 5-8 controls/nhóm |
| A2 | SecurityLLM được hardcode làm model Phase 1 | 🔴 | Chuyển sang gemma4 |
| A3 | Không có OCR cho scanned PDF / ảnh | 🔴 | Thêm Tesseract OCR |
| A4 | Evidence truncate 3000 chars/file | 🟠 | Bỏ limit, dùng chunking |
| A5 | Không có per-control evidence verdict | 🟠 | Wire `ControlVerdict` vào output |
| A6 | TCVN dùng chung scoring với ISO | 🟡 | `calc_tcvn_compliance()` riêng |
| A7 | Knowledge base JSONs rỗng | 🟡 | Populate data |
| A8 | Không có privacy filter | 🟠 | PII stripping trước cloud API |

---

## 4. Tính Năng 3: Output Báo Cáo IT Audit

### 4.1 Mục tiêu

Báo cáo phải đạt chuẩn IT Audit:
- **A4 format** — sạch đẹp, gọn gàng
- **Markdown** — dễ đọc, convert sang PDF/DOCX
- **Structured JSON** — cho dashboard
- **XLSX** — SoA + Risk Register

### 4.2 Cấu trúc báo cáo Markdown (5 phần bắt buộc)

```
═══════════════════════════════════════════════════════════
PHẦN 1: ĐÁNH GIÁ TỔNG QUAN
═══════════════════════════════════════════════════════════

Bảng metadata:
├── Tiêu chuẩn: ISO 27001:2022 / TCVN 11930:2017
├── Ngày đánh giá: DD/MM/YYYY
├── Tổ chức: Tên công ty
├── Ngành: Lĩnh vực
├── Phương pháp: Local/Hybrid/Cloud
└── Model: gemma4 + deepseek-v4-flash (user có thể chọn cloud model)

Compliance summary:
├── Overall: 62.4% (58/93 controls)
├── Tier: 🟡 Tuân thủ một phần
└── Bảng weight breakdown:
    | Trọng số  | Đạt | Tổng | Tỷ lệ |
    | Critical  | 12  | 20   | 60%   |
    | High      | 20  | 30   | 66.7% |
    | Medium    | 18  | 30   | 60%   |
    | Low       | 8   | 13   | 61.5% |

═══════════════════════════════════════════════════════════
PHẦN 2: RISK REGISTER
═══════════════════════════════════════════════════════════

Bảng rủi ro (sắp xếp Risk score giảm dần):
| # | Control | Nhóm | GAP | Mức độ | L | I | Risk | Khuyến nghị | Timeline |

Mỗi dòng:
├── Control ID: A.5.7
├── Nhóm: A.5 Tổ chức
├── GAP: "Không có threat intelligence"
├── Mức độ: 🔴 Critical / 🟠 High / 🟡 Medium / ⚪ Low
├── Likelihood: 1-5
├── Impact: 1-5
├── Risk: L × I (1-25)
├── Khuyến nghị: "Triển khai threat intel feed"
└── Timeline: "1-3 tháng"

Tóm tắt: 🔴=X 🟠=X 🟡=X ⚪=X

═══════════════════════════════════════════════════════════
PHẦN 3: GAP ANALYSIS (Chi tiết theo Category)
═══════════════════════════════════════════════════════════

### A.5 Tổ chức (Organization Controls)

#### Controls đã đạt (12/37)
✅ A.5.1 Chính sách ATTT — Đã ban hành v2.1
   Bằng chứng: policy_v2.1.pdf (chất lượng: 0.92)

#### Controls chưa đạt (25/37)
❌ A.5.7 Threat Intelligence
   Bằng chứng: Không có
   GAP: Không có quy trình thu thập threat intelligence
   Rủi ro: Không phát hiện sớm mối đe dọa
   Khuyến nghị: Đăng ký threat intel feed
   Confidence: 0.88

⚠️ A.5.9 Kiểm kê tài sản (Một phần)
   Bằng chứng: CMDB nhưng chưa đầy đủ (chất lượng: 0.65)
   GAP: CMDB chưa cover 100% tài sản

### A.6 Con người (People Controls) ...
### A.7 Vật lý (Physical Controls) ...
### A.8 Công nghệ (Technological Controls) ...

═══════════════════════════════════════════════════════════
PHẦN 4: ACTION PLAN
═══════════════════════════════════════════════════════════

### Ngắn hạn (0-30 ngày)
| # | Hành động | Control | Ưu tiên | Ước tính |
| 1 | Triển khai MFA | A.8.5 | 🔴 | 2 tuần |
| 2 | Cập nhật chính sách | A.5.1 | 🔴 | 1 tuần |

### Trung hạn (1-3 tháng)
| # | Hành động | Control | Ưu tiên | Ước tính |
| 1 | Triển khai SIEM/SOC | A.8.15 | 🟠 | 2 tháng |
| 2 | Đào tạo ATTT | A.6.3 | 🟠 | 1 tháng |

### Dài hạn (3-12 tháng)
| # | Hành động | Control | Ưu tiên | Ước tính |
| 1 | Chứng nhận ISO 27001 | All | 🟡 | 6-12 tháng |

═══════════════════════════════════════════════════════════
PHẦN 5: EXECUTIVE SUMMARY
═══════════════════════════════════════════════════════════

### Metrics
- Compliance: 62.4% (58/93 controls)
- Critical gaps: 8 controls
- High gaps: 10 controls
- Bằng chứng: 45/93 controls có bằng chứng

### Top 3 Rủi ro
1. Thiếu Threat Intelligence → Ước tính: 50-100tr VND
2. Chưa có SIEM/SOC → Ước tính: 200-500tr VND
3. MFA chưa đầy đủ → Ước tính: 20-50tr VND

### Next Steps (30 ngày)
1. Triển khai MFA cho admin
2. Ban hành chính sách ATTT mới
3. Lập kế hoạch SIEM/SOC

---
Phương pháp: Hybrid (gemma4 + DeepSeek)
Ngày tạo: DD/MM/YYYY
```

### 4.3 Structured JSON Output

```json
{
  "assessment_id": "uuid",
  "assessment_date": "2026-05-06",
  "standard": "iso27001",
  "standard_name": "ISO 27001:2022",
  "organization": {
    "name": "Công ty ABC",
    "industry": "Tài chính",
    "size": "large",
    "employees": 500
  },
  "compliance": {
    "score": 58,
    "max_score": 93,
    "percentage": 62.4,
    "tier": "medium",
    "tier_label": "Tuân thủ một phần"
  },
  "weight_breakdown": {
    "critical": {"total": 20, "implemented": 12, "percent": 60.0},
    "high": {"total": 30, "implemented": 20, "percent": 66.7},
    "medium": {"total": 30, "implemented": 18, "percent": 60.0},
    "low": {"total": 13, "implemented": 8, "percent": 61.5}
  },
  "controls": [
    {
      "id": "A.5.1",
      "label": "Chính sách ATTT",
      "category": "A.5 Tổ chức",
      "weight": "critical",
      "evidence_verdict": "satisfied",
      "confidence": 0.92,
      "missing_items": [],
      "evidence_files": ["policy_v2.1.pdf"],
      "notes": "Đã ban hành và phê duyệt"
    }
  ],
  "risk_register": [
    {
      "control_id": "A.5.7",
      "severity": "critical",
      "likelihood": 4,
      "impact": 4,
      "risk_score": 16,
      "gap": "Không có threat intelligence",
      "recommendation": "Triển khai threat intel feed",
      "timeline": "1-3 tháng"
    }
  ],
  "ai_mode": "hybrid",
  "model_used": {
    "phase1": "ollama:gemma4",
    "phase2": "deepseek:deepseek-v4-flash"
  }
}
```

### 4.4 XLSX Export

**SoA (Statement of Applicability):**
- Sheet: "Statement of Applicability"
- Columns: Control ID | Tên Control | Nhóm | Trọng số | Áp dụng | Lý do | Trạng thái | Điểm | Bằng chứng | Ghi chú
- Conditional formatting: đỏ (0) → cam (1-2) → vàng (3-4) → xanh (5)

**Risk Register:**
- Sheet: "Risk Register"
- Columns: # | Control ID | Nhóm | GAP | Mức độ | L | I | Risk | Khuyến nghị | Timeline | Chủ sở hữu | Trạng thái
- Sắp xếp theo Risk score giảm dần

### 4.5 PDF (Tương lai)

- Markdown → PDF qua WeasyPrint
- CSS: A4, font Times New Roman 12pt, margins 20mm
- Header: logo + tiêu đề báo cáo
- Footer: số trang + thông báo bảo mật

### 4.6 Cần sửa

| # | Vấn đề | Mức | Cách sửa |
|---|--------|-----|----------|
| R1 | Không có PDF export | 🟠 | Thêm WeasyPrint |
| R2 | Risk Register không export riêng | 🟡 | Thêm Risk Register .xlsx exporter |
| R3 | Report prompt quá dài cho local model | 🟠 | Nén input, dùng cloud cho Phase 2B |
| R4 | Không có evidence quality trong report | 🟡 | Thêm quality score per control |

---

## 5. Xử Lý Bằng Chứng (Evidence)

### 5.1 Pipeline hiện tại vs Mới

```
HIỆN TẠI:
Upload → Parse text → Truncate 3000 chars → Nhồi vào 1 prompt → AI phân tích
❌ Không OCR, không chunking, không quality scoring

MỚI:
Upload → Parse/OCR → Chuẩn hóa → Lọc PII → Chunk → Map → Quality Score → Inject vào prompt
✅ Đầy đủ, per-control, có chất lượng
```

### 5.2 OCR Implementation

**Thư viện:** Tesseract (nhẹ, chạy CPU)

**Docker dependencies:**
```dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng \
    poppler-utils && rm -rf /var/lib/apt/lists/*

RUN pip install pytesseract pdf2image Pillow
```

**Parser mới:** `backend/services/document_ingest/ocr_parser.py`
- `parse_image(data)` → OCR ảnh PNG/JPG
- `ocr_pdf(data)` → OCR PDF scanned (convert page → image → Tesseract)

**Nâng cấp PDF parser:** `backend/services/document_ingest/pdf_parser.py`
- Nếu pypdf extract < 50 chars → fallback OCR
- Nếu OCR cũng fail → warning

### 5.3 Privacy Filter

**File mới:** `backend/services/privacy_filter.py`

| Pattern | Thay thế |
|---------|----------|
| SĐT VN: 0[3-9]XXXXXXXX | [SĐT] |
| Email: user@domain | [EMAIL] |
| CMND/CCCD: 9-12 digits | [CMND] |
| IP nội bộ: 10.x/192.168.x | [IP] |
| API key/token | [BI_MAT] |
| Hostname *.local/corp | [TEN_MAY] |

**Quy tắc:**
- Local AI: lọc nhẹ (tùy chọn)
- Cloud AI: lọc mạnh (bắt buộc)
- Raw evidence: KHÔNG BAO GIỜ gửi lên cloud

### 5.4 Evidence → Control Mapping

**File mới:** `backend/services/evidence_mapper.py`

| Pattern filename | Control IDs |
|-----------------|-------------|
| policy, chính sách | A.5.1, A.5.2 |
| firewall, tường lửa | A.8.20, NW.02 |
| backup, sao lưu | A.8.13, DAT.01 |
| training, đào tạo | A.6.3 |
| encryption, mã hóa | A.8.24, DAT.04 |
| vulnerability, lỗ hổng | A.8.8 |
| logging, audit, siem | A.8.15, A.8.16, MNG.03 |
| vpn | NW.04 |
| patch, bản vá | SV.07 |
| mfa, xác thực | A.8.5, SV.06 |

---

## 6. Bảo Mật Thông Tin

### Nguyên tắc

| Nguyên tắc | Mô tả |
|-----------|-------|
| **Local-first** | Ưu tiên gemma4 cho phân tích chính |
| **PII stripping** | Loại bỏ thông tin cá nhân trước khi gửi AI |
| **Cloud = formatting only** | Cloud chỉ cho Phase 2B (báo cáo), KHÔNG cho Phase 2A (phân tích) |
| **No raw evidence to cloud** | Evidence text thô KHÔNG BAO GIỜ gửi lên cloud |
| **Audit trail** | Log mọi lần gọi AI: model, provider, input size, timestamp |

### Cloud AI được phép nhận

```
✅ CHO PHÉP:
├── Phase 2B: Định dạng báo cáo (Markdown output)
├── Input: Điểm số tổng hợp, control IDs, verdicts
├── Input: Weight breakdown, severity counts
└── Input: Tên tổ chức, ngành (không phải PII)

❌ KHÔNG BAO GIỜ:
├── Raw evidence text
├── Tên nhân viên, email, SĐT
├── IP nội bộ, hostname, sơ đồ mạng
├── API key, password, cấu hình
├── Chi tiết sự cố với ngày/tên cụ thể
└── Bất kỳ nội dung file nào từ evidence upload
```

---

## 7. Roadmap & Ước Tính

### Phase 10A: Evidence Pipeline (Tuần 1-2)

| # | Task | File | Ưu tiên | Thời gian |
|---|------|------|---------|-----------|
| A1 | OCR parser (Tesseract) | `document_ingest/ocr_parser.py` | 🔴 | 2 ngày |
| A2 | PDF parser OCR fallback | `document_ingest/pdf_parser.py` | 🔴 | 0.5 ngày |
| A3 | Image parser (PNG/JPG) | `document_ingest/ocr_parser.py` | 🔴 | 0.5 ngày |
| A4 | Privacy filter | `services/privacy_filter.py` | 🔴 | 1 ngày |
| A5 | Evidence → control mapper | `services/evidence_mapper.py` | 🟡 | 1 ngày |
| A6 | Evidence quality scorer | `services/evidence_mapper.py` | 🟡 | 0.5 ngày |
| A7 | Docker: Tesseract + poppler | `Dockerfile`, `requirements.txt` | 🔴 | 0.5 ngày |
| A8 | Tests | `tests/test_evidence_pipeline.py` | 🟡 | 1 ngày |

### Phase 10B: Per-Control Assessment + DeepSeek (Tuần 2-3)

| # | Task | File | Ưu tiên | Thời gian |
|---|------|------|---------|-----------|
| B0 | Thêm DeepSeek API provider | `cloud_llm_service.py` | 🔴 | 1 ngày |
| B0b | UI model selector (chatbot + form-iso) | `chatbot/page.js`, `form-iso/page.js` | 🔴 | 1 ngày |
| B1 | Bỏ SecurityLLM, chuyển sang gemma4 | `config.py`, `model_router.py` | 🔴 | 0.5 ngày |
| B2 | Control grouping (5-8 controls/nhóm) | `controls_catalog.py` | 🔴 | 0.5 ngày |
| B3 | Upgrade chunk prompt | `assessment_helpers.py` | 🔴 | 1 ngày |
| B4 | Per-control verdict validation | `assessment_helpers.py` | 🔴 | 1 ngày |
| B5 | Evidence summary per group | `assessment_helpers.py` | 🟡 | 0.5 ngày |
| B6 | Upgrade assess_system() | `chat_service.py` | 🔴 | 2 ngày |
| B7 | TCVN scoring logic riêng | `controls_catalog.py` | 🟡 | 1 ngày |
| B8 | Tests | `tests/test_assessment_v2.py` | 🟡 | 1 ngày |

### Phase 10C: Output & Export (Tuần 3-4)

| # | Task | File | Ưu tiên | Thời gian |
|---|------|------|---------|-----------|
| C1 | Structured JSON builder | `chat_service.py` | 🔴 | 1 ngày |
| C2 | Markdown report template | `prompts/defaults.py` | 🔴 | 1 ngày |
| C3 | Risk Register .xlsx export | `services/risk_register_exporter.py` | 🟡 | 1 ngày |
| C4 | SoA export cho TCVN | `services/soa_exporter.py` | 🟡 | 0.5 ngày |
| C5 | PDF generation (WeasyPrint) | `services/report_pdf_generator.py` | 🟡 | 1.5 ngày |
| C6 | Frontend: per-control verdicts | `form-iso/ControlRow.js` | 🟡 | 1 ngày |

### Phase 10D: Knowledge Base & Polish (Tuần 4)

| # | Task | File | Ưu tiên | Thời gian |
|---|------|------|---------|-----------|
| D1 | Populate knowledge base JSONs | `data/knowledge_base/` | 🟡 | 1 ngày |
| D2 | Privacy filter tests | `tests/test_privacy_filter.py` | 🟡 | 0.5 ngày |
| D3 | E2E integration test | `tests/test_e2e_assessment.py` | 🟡 | 1 ngày |
| D4 | Documentation update | `docs/vi/iso_assessment_form.md` | 🟢 | 0.5 ngày |

### Tổng kết

| Phase | Nội dung | Thời gian | Ưu tiên |
|-------|----------|-----------|---------|
| 10A | Evidence Pipeline (OCR + Privacy + Chunking) | 1 tuần | 🔴 P0 |
| 10B | Per-Control Assessment (gemma4 + grouping) | 1 tuần | 🔴 P0 |
| 10C | Output & Export (Markdown + JSON + XLSX + PDF) | 1 tuần | 🟡 P1 |
| 10D | Knowledge Base & Integration | 3 ngày | 🟡 P1 |
| **Tổng** | | **~18 ngày** | **1 developer** |

---

## Phụ lục: Files cần tạo/sửa

### Tạo mới

| File | Mục đích |
|------|----------|
| `backend/services/document_ingest/ocr_parser.py` | OCR parser (Tesseract) |
| `backend/services/privacy_filter.py` | Lọc PII |
| `backend/services/evidence_mapper.py` | Evidence → control mapping |
| `backend/services/report_pdf_generator.py` | Tạo PDF |
| `backend/services/risk_register_exporter.py` | Xuất Risk Register .xlsx |
| `backend/tests/test_evidence_pipeline.py` | Test evidence pipeline |
| `backend/tests/test_assessment_v2.py` | Test assessment v2 |
| `backend/tests/test_privacy_filter.py` | Test privacy filter |
| `backend/tests/test_e2e_assessment.py` | Test E2E |

### Sửa đổi

| File | Thay đổi |
|------|----------|
| `backend/services/controls_catalog.py` | Thêm `get_control_groups()`, `calc_tcvn_compliance()` |
| `backend/services/assessment_helpers.py` | Upgrade chunk prompt, verdict validation |
| `backend/services/chat_service.py` | Upgrade `assess_system()`, bỏ SecurityLLM |
| `backend/services/cloud_llm_service.py` | Thêm DeepSeek provider, cập nhật FALLBACK_CHAIN |
| `backend/services/document_ingest/pdf_parser.py` | OCR fallback |
| `backend/services/document_ingest/base.py` | Register OCR parser |
| `backend/core/config.py` | Bỏ SECURITY_MODEL_NAME, dùng MODEL_NAME, thêm DEEPSEEK_API_KEY |
| `backend/services/model_router.py` | Đơn giản hóa routing |
| `backend/api/routes/iso27001.py` | Tích hợp evidence processing |
| `backend/prompts/defaults.py` | Prompts mới |
| `backend/Dockerfile` | Thêm Tesseract + poppler |
| `backend/requirements.txt` | Thêm pytesseract, pdf2image, Pillow, weasyprint |
| `frontend-next/src/app/chatbot/page.js` | Thêm model selector dropdown |
| `frontend-next/src/app/form-iso/page.js` | Thêm model selector dropdown |
| `frontend-next/src/lib/api.js` | Gửi cloud_model param |
| `data/knowledge_base/iso27001.json` | Populate |
| `data/knowledge_base/tcvn14423.json` | Populate |
| `data/knowledge_base/controls.json` | Populate |

