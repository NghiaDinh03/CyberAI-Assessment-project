# Phản Hồi & Cập Nhật Plan — CyberAI Core Features

> **Ngày:** 2026-05-06  
> **Vị trí:** `.AI_CONTEXT/` (plan nội bộ)

---

## 1. Chunking — Vấn đề lẫn controls

### Vấn đề
Chia chunk theo char (700 tokens) → bằng chứng control A.5.1 có thể bị cắt giữa chừng, phần sau lẫn vào chunk của A.5.2.

### Giải pháp: Control-Aware Chunking

```
THAY VÌ:
  File.pdf → chunk 700 tokens → chunk1, chunk2, chunk3...
  (chunk2 có thể chứa nửa A.5.1 + nửa A.5.2 → lẫn)

THÀNH:
  File.pdf → Parse sections → Map section → control ID → Chunk per control
  
  Ví dụ:
  ├── Section "Chính sách ATTT" → map A.5.1 → chunk riêng
  ├── Section "Phân quyền truy cập" → map A.5.15, A.5.16 → chunk riêng  
  ├── Section "Firewall" → map A.8.20 → chunk riêng
  └── Section không map được → chunk chung + gán "unmapped"
```

**Implementation:**
```python
def control_aware_chunk(text: str, control_map: dict) -> dict:
    """Chia text thành chunks, mỗi chunk gắn với control ID cụ thể.
    
    1. Tách text thành sections (theo heading hoặc paragraph lớn)
    2. Map mỗi section → control ID (dựa trên keyword + heading)
    3. Chunk mỗi section riêng (700 tokens, 80 overlap)
    4. Gắn metadata: {control_id, section_heading, chunk_index}
    
    Kết quả: {control_id: [chunk1, chunk2, ...]}
    """
```

**Nguyên tắc:** KHÔNG bao giờ 1 chunk chứa thông tin của 2 control khác nhau.

---

## 2. Upload file báo cáo tổng → Match với controls

### Vấn đề
Người dùng không nhập tay từng control. Họ upload 1 file báo cáo tổng (VD: "Báo cáo đánh giá ATTT 2025.pdf" 50 trang). Cần tự động match thông tin trong file → controls.

### Giải pháp: Smart Evidence Matching Pipeline

```
Bước 1: Upload file báo cáo tổng
  → Parse toàn bộ text (PDF/DOCX/XLSX)
  → Tách thành sections theo heading

Bước 2: Section-Level Matching
  Với mỗi section:
  ├── Extract heading + body text
  ├── So sánh với control labels trong controls_catalog.py
  │   ├── Exact match: "Chính sách ATTT" → A.5.1
  │   ├── Fuzzy match: "policy" / "chính sách" → A.5.1, A.5.2
  │   ├── Keyword match: "firewall" / "tường lửa" → A.8.20, NW.02
  │   └── Semantic match: dùng model embedding (nếu có)
  └── Gán control_id cho section

Bước 3: Content-Level Matching (cho sections không match được)
  ├── Chia section thành paragraphs
  ├── Với mỗi paragraph, tìm keyword liên quan controls
  ├── Nếu keyword density > threshold → gán control
  └── Nếu không match → gán "unmapped" (user review sau)

Bước 4: User Review (Optional)
  ├── Hiển thị kết quả matching cho user
  ├── User confirm / sửa lại mapping
  └── Lưu mapping vào evidence_map

Bước 5: Inject vào Assessment
  ├── Với mỗi control đã match:
  │   ├── Lấy chunks tương ứng
  │   ├── Tóm tắt (gemma4, max 256 tokens)
  │   └── Inject vào chunk prompt
  └── Với controls không match:
      └── Đánh dấu "Không có bằng chứng"
```

**Ví dụ thực tế:**
```
Input: "Bao_cao_danh_gia_ATTT_2025.pdf" (50 trang)

Parse → Sections:
├── "1. Giới thiệu" → unmapped
├── "2. Chính sách an toàn thông tin" → A.5.1 ✅
├── "3. Phân quyền và quản lý truy cập" → A.5.15, A.5.16, A.5.17, A.5.18 ✅
├── "4. Bảo vệ mạng" → A.8.20, A.8.21, A.8.22, NW.01, NW.02 ✅
├── "5. Sao lưu và phục hồi" → A.8.13, DAT.01, DAT.03 ✅
├── "6. Đào tạo nhân viên" → A.6.3 ✅
├── "7. Quản lý sự cố" → A.5.24, A.5.25, A.5.26, MNG.04 ✅
└── "8. Kết luận" → unmapped

Kết quả: 25/93 controls có bằng chứng từ 1 file
```

---

## 3. Nâng token cho Local Model

### Hiện tại
- gemma4:latest → context window 8192 tokens (default Ollama)
- Max output: ~4096 tokens

### Nâng cấp

**Ollama Modelfile custom:**
```dockerfile
# Tạo custom gemma4 với context window lớn hơn
FROM gemma4:latest

# Nâng context window lên 16384 tokens
PARAMETER num_ctx 16384

# Nâng max output tokens
PARAMETER num_predict 8192

# Temperature thấp cho assessment (chính xác)
PARAMETER temperature 0.1
```

**Docker compose cập nhật:**
```yaml
ollama:
  entrypoint: ["/bin/sh", "-c", "
    ollama serve & sleep 5 && 
    ollama pull gemma4:latest && 
    ollama create gemma4:16k -f /models/Modelfile.gemma4-16k &&
    ollama pull gemma3:27b && 
    ollama pull gemma3n:e4b && 
    ollama pull gemma3n:e2b; 
    wait"]
```

**Lưu ý hiệu suất:**
| Config | Context | RAM cần | Tốc độ | Chất lượng |
|--------|---------|---------|--------|------------|
| gemma4:latest (default) | 8192 | ~8GB | Nhanh | Tốt |
| gemma4:16k (custom) | 16384 | ~12GB | Chậm hơn ~30% | Tốt hơn (nhiều context) |
| gemma3:27b | 8192 | ~20GB | Chậm | Rất tốt |

**Khuyến nghị:** Dùng `gemma4:16k` cho assessment (cần nhiều context), `gemma4:latest` cho chat (nhanh).

---

## 4. Streaming Log cho User quan sát

### Vấn đề
User submit assessment → chờ 5-10 phút → không biết hệ thống đang làm gì.

### Giải pháp: Real-time Progress Log

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Tiến trình đánh giá                                     │
│                                                             │
│  ✅ Bước 1: Thu thập input (2s)                             │
│  ✅ Bước 2: Xử lý bằng chứng (15s)                         │
│     ├── ✅ Parse PDF: bao_cao_ATTT.pdf (8s)                 │
│     ├── ✅ Parse DOCX: chinh_sach.docx (3s)                 │
│     ├── ✅ OCR: scan_001.png (2s)                           │
│     ├── ✅ Privacy filter: 5 PII items stripped              │
│     └── ✅ Map: 25/93 controls có bằng chứng                │
│  ✅ Bước 3: Tóm tắt bằng chứng (10s)                       │
│  🔄 Bước 4: Phân tích GAP [3/15 groups] ████░░░░░░ 20%     │
│     ├── ✅ A.5 Tổ chức (1/4) — 6 gaps found                 │
│     ├── ✅ A.5 Tổ chức (2/4) — 4 gaps found                 │
│     ├── 🔄 A.5 Tổ chức (3/4) — đang phân tích...            │
│     ├── ⏳ A.5 Tổ chức (4/4) — chờ                          │
│     ├── ⏳ A.6 Con người — chờ                              │
│     └── ⏳ ...                                               │
│  ⏳ Bước 5: Định dạng báo cáo — chờ                        │
│  ⏳ Bước 6: Export — chờ                                    │
│                                                             │
│  [Chi tiết] [Tóm tắt]                                       │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
- Backend: SSE (Server-Sent Events) endpoint `/api/iso27001/assess/{id}/stream`
- Mỗi bước: emit event `{step, status, message, progress_percent, details}`
- Frontend: EventSource listener, render real-time

**Backend code pattern:**
```python
async def assessment_stream(assessment_id: str):
    """SSE stream cho assessment progress."""
    yield f"data: {json.dumps({'step': 'init', 'status': 'running', 'message': 'Bắt đầu...'})}\n\n"
    
    # Step 1: Parse evidence
    yield f"data: {json.dumps({'step': 'evidence', 'status': 'running', 'message': 'Xử lý bằng chứng...'})}\n\n"
    for file in evidence_files:
        result = parse_file(file)
        yield f"data: {json.dumps({'step': 'evidence', 'file': file.name, 'status': 'done', 'result': result})}\n\n"
    
    # Step 2: Chunked assessment
    for i, group in enumerate(control_groups):
        yield f"data: {json.dumps({'step': 'analysis', 'group': group.name, 'progress': i/len(groups), 'status': 'running'})}\n\n"
        gaps = analyze_group(group)
        yield f"data: {json.dumps({'step': 'analysis', 'group': group.name, 'gaps': len(gaps), 'status': 'done'})}\n\n"
    
    # Step 3: Report
    yield f"data: {json.dumps({'step': 'report', 'status': 'running', 'message': 'Định dạng báo cáo...'})}\n\n"
    report = format_report(all_gaps)
    yield f"data: {json.dumps({'step': 'report', 'status': 'done'})}\n\n"
    
    yield f"data: {json.dumps({'step': 'complete', 'status': 'done', 'message': 'Hoàn thành!'})}\n\n"
```

---

## 5. Nâng max tokens Phase 2B (Report Formatting)

### Vấn đề
Max tokens 10000 → báo cáo bị cắt ngắn, thiếu chi tiết.

### Giải pháp

| Model | Max tokens cũ | Max tokens mới | Ghi chú |
|-------|--------------|----------------|---------|
| gemma4:latest | 4096 | 8192 | Nâng num_predict trong Modelfile |
| gemma4:16k (custom) | 8192 | 12288 | Đủ cho báo cáo đầy đủ |
| deepseek-v4-flash | 10000 | 32000 | Cloud model, không giới hạn |
| gemini-3.1-pro-preview | 8192 | 32000 | Cloud model |

**Chiến lược:**
- Nếu báo cáo < 8192 tokens → dùng local (gemma4:16k)
- Nếu báo cáo > 8192 tokens → dùng cloud (deepseek-v4-flash, 32000 tokens)
- Nếu dùng cloud → privacy filter bắt buộc (không gửi raw evidence)

**Prompt optimization:**
```
Thay vì gửi TOÀN BỘ raw analysis vào Phase 2B:
├── Compress: chỉ gửi summary + top 20 gaps quan trọng
├── Structured: gửi dạng JSON thay vì Markdown (tiết kiệm token)
└── Phân tách: nếu quá dài → chia thành 2 calls
    ├── Call 1: Sections 1-3 (Overview, Risk Register, GAP Analysis)
    └── Call 2: Sections 4-5 (Action Plan, Executive Summary)
```

---

## 6. Export File Docs Hoàn Chỉnh

### Yêu cầu
- File .docx có thể edit được
- Giấy A4
- Font Times New Roman
- Định dạng sạch đẹp, đúng chuẩn IT Audit quốc tế
- Có header/footer chuyên nghiệp

### Giải pháp: python-docx Template Engine

```
┌─────────────────────────────────────────────────────────────┐
│                EXPORT PIPELINE                               │
│                                                             │
│  Input: Assessment JSON (structured data)                   │
│                                                             │
│  Step 1: Load template .docx                                │
│  ├── Template có sẵn styles: Heading1, Heading2, Body,      │
│  │   TableHeader, TableCell, Footer                         │
│  ├── Page setup: A4, margins 25mm top/bottom, 20mm L/R     │
│  └── Font: Times New Roman 12pt                             │
│                                                             │
│  Step 2: Fill content                                       │
│  ├── Title page: tên tổ chức, tiêu chuẩn, ngày             │
│  ├── Section 1: Tổng quan (bảng compliance)                 │
│  ├── Section 2: Risk Register (bảng rủi ro)                 │
│  ├── Section 3: GAP Analysis (chi tiết per category)        │
│  ├── Section 4: Action Plan (3 bảng ngắn/trung/dài hạn)     │
│  └── Section 5: Executive Summary                           │
│                                                             │
│  Step 3: Format                                             │
│  ├── Tables: border, alternating row colors                 │
│  ├── Headers: numbering (1., 1.1, 1.1.1)                   │
│  ├── Page breaks between major sections                     │
│  ├── Header: "BÁO CÁO ĐÁNH GIÁ ATTT — [Tổ chức]"          │
│  ├── Footer: "Trang X/Y — Bảo mật nội bộ"                 │
│  └── Table of Contents (auto-generated)                     │
│                                                             │
│  Step 4: Output                                             │
│  ├── .docx (editable)                                       │
│  └── .pdf (via LibreOffice headless hoặc WeasyPrint)       │
└─────────────────────────────────────────────────────────────┘
```

**Template structure (IT Audit standard):**
```
TRANG BÌA
├── Logo tổ chức (placeholder)
├── "BÁO CÁO ĐÁNH GIÁ AN TOÀN THÔNG TIN"
├── Tiêu chuẩn: ISO 27001:2022 / TCVN 11930:2017
├── Tổ chức: [Tên]
├── Ngày đánh giá: [DD/MM/YYYY]
├── Phiên bản: 1.0
├── Mức bảo mật: NỘI BỘ — CHỈ DÀNH CHO BAN LÃNH ĐẠO
└── Người lập: CyberAI Assessment Platform

MỤC LỤC (auto)

PHẦN 1: ĐÁNH GIÁ TỔNG QUAN
├── 1.1 Phạm vi đánh giá
├── 1.2 Phương pháp đánh giá
├── 1.3 Kết quả tổng hợp (bảng)
└── 1.4 Phân bổ trọng số (bảng)

PHẦN 2: SỔ ĐĂNG KÝ RỦI RO (RISK REGISTER)
├── 2.1 Bảng rủi ro (sắp xếp theo Risk score)
└── 2.2 Tóm tắt rủi ro

PHẦN 3: PHÂN TÍCH KHOẢNG CÁCH (GAP ANALYSIS)
├── 3.1 A.5 Tổ chức
│   ├── Controls đã đạt
│   └── Controls chưa đạt (chi tiết per control)
├── 3.2 A.6 Con người
├── 3.3 A.7 Vật lý
└── 3.4 A.8 Công nghệ

PHẦN 4: KẾ HOẠCH HÀNH ĐỘNG
├── 4.1 Ngắn hạn (0-30 ngày)
├── 4.2 Trung hạn (1-3 tháng)
└── 4.3 Dài hạn (3-12 tháng)

PHẦN 5: TÓM TẮT DÀNH CHO LÃNH ĐẠO
├── 5.1 Chỉ số chính
├── 5.2 Top 3 rủi ro
└── 5.3 Hành động ưu tiên

PHỤ LỤC
├── A. Danh sách controls đầy đủ
├── B. Bằng chứng đã thu thập
└── C. Glossary thuật ngữ
```

---

## 7. UI Preview trước khi Export

### Yêu cầu
- Preview toàn bộ thông tin trên UI
- Options chọn preview từng loại file (Markdown/JSON/XLSX/DOCX/PDF)
- Chính xác 100% định dạng, cỡ chữ
- User xem trước → nếu phù hợp → mới tải về

### Giải pháp: Multi-Format Preview Panel

```
┌─────────────────────────────────────────────────────────────┐
│  📄 Preview Báo Cáo                                         │
│                                                             │
│  [Markdown] [JSON] [DOCX] [PDF] [XLSX SoA] [XLSX Risk]    │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─────────────────────────────────────────────────────┐ ││
│  │ │ BÁO CÁO ĐÁNH GIÁ AN TOÀN THÔNG TIN                │ ││
│  │ │ Công ty ABC — ISO 27001:2022 — 06/05/2026          │ ││
│  │ │                                                     │ ││
│  │ │ 1. ĐÁNH GIÁ TỔNG QUAN                              │ ││
│  │ │ ┌──────────┬──────┬──────┬──────┐                  │ ││
│  │ │ │Trọng số  │ Đạt  │ Tổng │ Tỷ lệ│                  │ ││
│  │ │ ├──────────┼──────┼──────┼──────┤                  │ ││
│  │ │ │Critical  │ 12   │ 20   │ 60%  │                  │ ││
│  │ │ │High      │ 20   │ 30   │ 66.7%│                  │ ││
│  │ │ │Medium    │ 18   │ 30   │ 60%  │                  │ ││
│  │ │ │Low       │ 8    │ 13   │ 61.5%│                  │ ││
│  │ │ └──────────┴──────┴──────┴──────┘                  │ ││
│  │ │                                                     │ ││
│  │ │ 2. RISK REGISTER                                    │ ││
│  │ │ ...                                                 │ ││
│  │ └─────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  Format: A4 (210×297mm) | Font: Times New Roman 12pt        │
│  Trang: 1/12 | Kích thước: ~245KB                           │
│                                                             │
│  [⬇ Tải .docx] [⬇ Tải .pdf] [⬇ Tải .xlsx SoA]            │
│  [✏️ Chỉnh sửa] [🔄 Tạo lại]                               │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**
- Frontend: Render Markdown preview với CSS mô phỏng A4
- CSS: `width: 210mm; min-height: 297mm; font-family: 'Times New Roman'; font-size: 12pt;`
- Tabs: mỗi tab render format khác nhau
- Pagination: chia thành "trang" A4 trên UI
- Download: chỉ export khi user ấn nút

---

## 8. Karpathy Guidelines — Áp dụng

### Repo: https://github.com/forrestchang/andrej-karpathy-skills

**Nội dung chính (4 quy tắc):**

1. **Think Before Coding** — Nêu giả định, không assume, hỏi khi không rõ
2. **Simplicity First** — Code tối thiểu, không thêm feature ngoài yêu cầu
3. **Surgical Changes** — Chỉ sửa code liên quan, không refactor code chưa hỏng
4. **Goal-Driven Execution** — Verify sau mỗi bước, có acceptance criteria

### Áp dụng cho CyberAI

| Quy tắc | Áp dụng cụ thể |
|---------|-----------------|
| Simplicity | Không thêm model mới nếu gemma4 đủ. Không thêm feature nếu chưa có yêu cầu. |
| Surgical | Khi sửa `chat_service.py` → chỉ sửa `assess_system()`, không đụng `stream_chat()`. |
| No speculative | Không viết code cho "tương lai có thể cần". Chỉ code cái user yêu cầu. |
| Verify | Mỗi task trong roadmap phải có acceptance criteria. |

### Cách sử dụng

```bash
# Copy vào project root
cp CLAUDE.md /path/to/CyberAI-Assessment-project/CLAUDE.md

# Merge với .clinerules hiện tại
# Thêm vào cuối .clinerules:
# - Simplicity first
# - Surgical changes  
# - Verify after each step
# - No speculative code
```

**File đã tạo:** [`.AI_CONTEXT/karpathy_guidelines.md`](karpathy_guidelines.md)

---

## 9. Cập nhật Plan chính

### Thay đổi trong [`core_features_plan.md`](core_features_plan.md)

| Section | Thay đổi |
|---------|----------|
| Bước 1.4 Chunking | Chuyển sang **Control-Aware Chunking** — không lẫn controls |
| Bước 1.5 Mapping | Nâng cấp thành **Smart Evidence Matching** — tự match file báo cáo tổng |
| Token budget | Nâng gemma4 lên 16k context (custom Modelfile) |
| Phase 2B | Nâng max tokens lên 32000 (cloud) / 12288 (local custom) |
| Streaming log | Thêm SSE endpoint cho real-time progress |
| Export | Thêm .docx export (python-docx template, A4, Times New Roman) |
| Preview | Thêm multi-format preview panel trên UI |
| Karpathy | Thêm guidelines vào `.clinerules` |

### Files cần tạo mới (bổ sung)

| File | Mục đích |
|------|----------|
| `backend/services/document_ingest/control_aware_chunker.py` | Chunking không lẫn controls |
| `backend/services/evidence_matcher.py` | Smart matching file → controls |
| `backend/services/report_docx_generator.py` | Tạo .docx IT Audit format |
| `backend/api/routes/assessment_stream.py` | SSE endpoint cho progress |
| `frontend-next/src/components/AssessmentProgress.js` | UI streaming log |
| `frontend-next/src/components/ReportPreview.js` | Multi-format preview |
| `ollama/Modelfile.gemma4-16k` | Custom gemma4 với 16k context |
| `CLAUDE.md` | Karpathy guidelines |

