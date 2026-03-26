# Context — CyberAI Assessment Chatbot (cập nhật 25/03/2026)

## Tech Stack
- **Frontend**: Next.js 14 App Router, CSS Modules, ReactMarkdown + remark-gfm
- **Backend**: FastAPI, Python 3.11
- **AI**: LocalAI (SecurityLLM 7B, Llama 3.1 8B), Open Claude API (cloud fallback)
- **Vector DB**: ChromaDB (cosine similarity), index từ `/data/iso_documents/*.md`
- **Docker Compose**: `frontend-next`, `backend`, `localai`, `chromadb`
- **Proxy**: `next.config.js` rewrites `/api/*` → `http://backend:8000/api/*`

---

## AI Routing (cloud_llm_service.py)
| task_type | Model | Mô tả |
|---|---|---|
| `iso_local` | SecurityLLM (LocalAI) | Phase 1 phân tích hạ tầng — BẮT BUỘC local, không fallback cloud |
| `iso_analysis` | Cloud (Open Claude) | Phase 2 format markdown report |
| `security` | SecurityLLM | Câu hỏi bảo mật general |
| `translation` | Cloud | Dịch thuật |
| `summarization` | Cloud | Tóm tắt bài viết |
| `general` | Llama 3.1 8B | Chat general |

**LOCAL_ONLY_TASKS**: `iso_local` → smart fallback cloud nếu model load fail. `security` → không fallback.

### Model RAM Requirements (LocalAI container limit: 12GB)
| Model | RAM cần | Có chạy được? | Vai trò |
|-------|---------|---------------|---------|
| `SecurityLLM-7B-Q4_K_M.gguf` | ~4GB | ✅ OK | Phase 1 — GAP analysis |
| `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | ~5GB | ✅ OK (khuyên dùng) | Phase 2 — report formatting |
| `Meta-Llama-3.2-3B-Instruct-Q4_K_M.gguf` | ~2GB | ✅ OK (nhanh nhất) | Phase 2 fallback |
| `Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf` | ~40GB | ❌ OOM (cần 48GB+) | KHÔNG dùng được |

**Kết luận:** Đổi `MODEL_NAME` từ 70B → 8B trong `.env`. Cả SecurityLM 7B + Llama 8B = ~9GB tổng → vừa trong 12GB container.

---

## ISO Assessment — 2-Phase AI Report

### Model Routing (cập nhật 26/03/2026)

| Mode | Phase 1 | Phase 2 |
|------|---------|---------|
| **Local Only** | `SECURITY_MODEL_NAME` (SecurityLM) — GAP analysis | `MODEL_NAME` (Meta-Llama) — report formatting |
| **Hybrid** | `SECURITY_MODEL_NAME` (SecurityLM) — local | Cloud (OpenClaude) — report |
| **Cloud Only** | Cloud (OpenClaude) | Cloud (OpenClaude) |

```
Phase 1: SecurityLM (iso_local) — domain-specific GAP analysis per category
  Input: chunked per-category (~1000 tokens/chunk), system summary compact
  Output: raw GAP tables per category (markdown bảng Risk Register)

Phase 2: Meta-Llama (local) / OpenClaude (cloud|hybrid) — report formatting
  Input: aggregated raw_analysis + scoring data
  Output: Full Markdown report (Tổng quan / Risk Register / GAP / Action Plan / Executive Summary)
```

### Health Check + Auto-Fallback (26/03/2026)
```
localai_health_check(model=SECURITY_MODEL_NAME, timeout=15s)
  OK  → dùng local như bình thường
  FAIL (OOM/RPC Canceled) →
    local mode:  fallback → hybrid (nếu có cloud key)
    hybrid mode: fallback → cloud
    local + no cloud key: raise Exception + hướng dẫn
```

**LOCAL_ONLY_TASKS** đã update: `iso_local` giờ có smart fallback thay vì hard fail.

**Bugs đã fix (26/03/2026):**
- `HTTP 500 rpc error: Canceled` (70B model OOM) → health check + auto-fallback mode
- Phase 2 local dùng nhầm model → giờ dùng `MODEL_NAME` (Meta-Llama) đúng role
- `[Ngày hiện tại]` placeholder → inject `today = datetime.now().strftime("%d/%m/%Y")`
- Phase 1 gửi infra data lên cloud → `task_type="iso_local"`

---

## Weighted Scoring (standards.js)
```js
WEIGHT_SCORE = { critical: 4, high: 3, medium: 2, low: 1 }

calcWeightedScore(implementedIds, allControls) → { achieved, maxScore, percent }
// percent = (sum of weight of implemented controls) / (sum of all weights) × 100
```

Mỗi control trong `ISO_27001_CONTROLS` và `TCVN_11930_CONTROLS` có field `weight: 'critical'|'high'|'medium'|'low'`.

**Trong page.js (form-iso):**
```js
const weightedScore = useMemo(() => calcWeightedScore(form.implemented_controls, currentStandard.controls), [...])
const compliancePercent = weightedScore.percent  // weighted %, không phải count đơn giản
```

---

## Form Đánh giá ISO (form-iso/page.js)

### 4 Bước:
1. **Tổ chức** — tên, quy mô, ngành nghề, số nhân sự, tiêu chuẩn
2. **Hạ tầng** — server, firewall, VPN, cloud, AV, backup, SIEM, sự cố
3. **Controls** — accordion theo category, weighted badge, tooltip detail panel
4. **Mô tả + Tổng kết** — network_diagram, notes, summary trước khi submit

### Result Tab:
- **Score Hero Card** — SVG gauge tròn thực (`SvgGauge` component), hiển thị % weighted
- **Processing Card** — animated spinner, 3-step progress indicator
- **Action Bar** — 📋 Sao chép | 📄 Xem/Xuất PDF | 🖨️ In | ← Đánh giá mới
- **Report Body** — `ReactMarkdown` với enhanced `.md` CSS styles

### Export PDF:
Button "📄 Xem / Xuất PDF" → mở new tab với HTML styled (light theme, print-ready)
→ Có banner hướng dẫn "Ctrl+P → Lưu thành PDF"
→ Hero card + report content đầy đủ
→ Không auto-download, user tự chọn lưu/print

### History Tab (form-iso):
Hiển thị: Org name | Ngày | Tiêu chuẩn | **% Tuân thủ** (màu theo mức) | Status badge | Xem/Kiểm tra

---

## Analytics Dashboard (analytics/page.js)

### Lịch sử Đánh giá ISO:
Bảng 6 cột: Thời gian | Tổ chức | **% Tuân thủ** | Trạng thái | ID Giao dịch | Xóa
- `pctBadge` — badge màu theo mức (red/amber/blue/green)

### Modal "Chi tiết Đánh giá" (đã redesign hoàn toàn):
1. **Header** — "Chi tiết Đánh giá" + ID + timestamp
2. **Score Hero mini** — SVG gauge 96px + %, org name, standard, compliance badge, meta (NV/Server/ISO status)
3. **Action Bar** — 📋 Sao chép | 📄 Xem/Xuất PDF | ♻️ Tái sử dụng
4. **Failed note** (nếu có lỗi)
5. **Report** — `ReactMarkdown` với `.md` CSS styles

---

## Backend — iso27001.py

### Lưu compliance_percent khi tạo assessment:
```python
impl_controls = data.implemented_controls or []
total_controls = 93 if data.assessment_standard == "iso27001" else 34
compliance_pct = round((len(impl_controls) / total_controls) * 100, 1)

assessment_record = {
    "id": assessment_id,
    "status": "pending",
    "system_info": system_data,
    "compliance_percent": compliance_pct,   # ← Lưu sẵn
    "standard": data.assessment_standard,
    "created_at": ...,
    "updated_at": ...
}
```

### list_assessments() trả về thêm:
```python
"compliance_percent": data.get("compliance_percent"),
```

---

## CSS Classes Mới (form-iso/page.module.css)

| Class | Mô tả |
|---|---|
| `.svgGaugeWrap` | Container 120×120 cho SVG gauge, `position: relative` |
| `.svgGaugeOverlay` | Overlay tuyệt đối chứa số % và label "Tuân thủ" |
| `.scoreNumLow/Partial/Mostly/Full` | Màu số % theo mức (red/amber/blue/green) |
| `.weightBadge` | Badge nhỏ hiện mức weight (critical/high/medium/low) trên mỗi control |
| `.ctrlTopRow` | Flex row chứa `ctrlId` + `weightBadge` |
| `.histPercent` | Column % tuân thủ trong history list |
| `.histPercentNum` | Số % lớn có màu |
| `.histPercentLabel` | Label "tuân thủ" nhỏ bên dưới |

## CSS Classes Mới (analytics/page.module.css)

| Class | Mô tả |
|---|---|
| `.pctBadge` | Badge % trong bảng lịch sử analytics |
| `.modalScoreHero` | Flex card mini trong modal |
| `.modalGaugeWrap/Overlay` | SVG gauge wrap cho analytics modal |
| `.modalGaugePct/Label` | Số % và label |
| `.modalOrgName/StdName` | Tên tổ chức và tiêu chuẩn |
| `.modalBadge` + variants | Compliance badge (Neutral/Low/Partial/Mostly/Full) |
| `.modalMetaRow` | Meta tags (NV, server, ISO status) |
| `.modalActionBar/Btn/BtnSecondary` | Action bar bên trong modal |
| `.failedNote` | Thông báo lỗi với border-left đỏ |
| `.loadingSpinner` | Spinner animation khi tải modal |
| `.md` + h1/h2/h3/strong/ul/blockquote/hr/code | Markdown styles cho modal |

---

---

## 3 Tính năng — ĐÃ IMPLEMENT ✅

### 1. Weighted Scoring trong Phase 1 Prompt ✅
**Phase 1 prompt** bây giờ gửi weight breakdown chi tiết:
```
PHÂN BỔ TRỌNG SỐ CONTROLS:
- Tối quan trọng (4 điểm): 5/15 đạt (33.3%)
- Quan trọng (3 điểm): 10/28 đạt (35.7%)
⚠️ CONTROLS TỐI QUAN TRỌNG CHƯA ĐẠT (10):
  🔴 A.5.17 (Xác thực MFA)
  🔴 A.8.8 (Quản lý lỗ hổng)
```
- AI Auditor phân loại GAP theo severity: 🔴 Critical, 🟠 High, 🟡 Medium, ⚪ Low
- Phase 1 yêu cầu tạo Risk Register dạng bảng markdown
- Missing critical/high controls được liệt kê để AI focus

### 2. Risk Register ✅
**Phase 2 prompt** bắt buộc tạo cấu trúc 5 section:
1. ĐÁNH GIÁ TỔNG QUAN (bảng phân bổ trọng số)
2. **RISK REGISTER** — bảng markdown BẮT BUỘC:

| # | Control ID | Mô tả GAP | Severity | Likelihood | Impact | Risk Score | Khuyến nghị | Timeline |

3. PHÂN TÍCH LỖ HỔNG CHI TIẾT (nhóm theo severity)
4. KHUYẾN NGHỊ ƯU TIÊN (lộ trình Ngắn/Trung/Dài hạn)
5. TÓM TẮT ĐIỀU HÀNH (Executive Summary cho C-level)

### 3. Scoring Breakdown Panel ✅
Frontend hiển thị per-category bar chart trong result view:
- Mỗi category có progress bar + weighted % + control count + điểm
- Màu sắc theo mức: ≥80% green, ≥50% blue, ≥25% amber, <25% red
- `calcCategoryBreakdown()` trong standards.js tính: total, implemented, percent, weightScore, maxWeightScore, weightPercent

---

## Dynamic Standard Loading — ĐÃ IMPLEMENT ✅

### Luồng hoạt động:
```
Upload JSON/YAML ──→ Backend parse + validate ──→ Lưu data/standards/{id}.json
                                                  ↓
                                          ChromaDB auto-index (RAG)
                                                  ↓
Frontend /standards page ←── GET /api/standards ←── List builtin + custom
         ↓
Form ISO /form-iso ←── GET /api/standards/{id} ←── Load controls + descriptions
         ↓
Dropdown render custom standard ──→ User tick controls ──→ AI assess_system()
```

### Backend Files:
- `services/standard_service.py` — parse, validate, save, index, CRUD
- `api/routes/standards.py` — REST API: upload, validate, list, get, delete, reindex
- `main.py` — registered `/api/standards/*` router

### Frontend Files:
- `app/standards/page.js` — Upload UI, drag-drop, validate, standard list, detail panel
- `app/standards/page.module.css` — Full CSS cho standards management page
- `data/standards.js` — `mergeCustomStandard()`, `removeCustomStandard()`, `calcCategoryBreakdown()`
- `app/form-iso/page.js` — Dynamic loading custom standards on mount, `allDescriptions` merged
- `components/Navbar.js` — Added "📚 Tiêu chuẩn" nav item

### API Endpoints:
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/standards` | List all (builtin + custom) |
| GET | `/api/standards/sample` | Download sample JSON template |
| GET | `/api/standards/{id}` | Get full standard for frontend |
| POST | `/api/standards/upload` | Upload + validate + save + ChromaDB index |
| POST | `/api/standards/validate` | Validate file without saving |
| POST | `/api/standards/{id}/index` | Re-index to ChromaDB |
| DELETE | `/api/standards/{id}` | Delete custom standard |

---

## TODO Đề xuất Tiếp theo

### Tính năng chưa implement (ưu tiên cao):
- [ ] **Weighted scoring trong Phase 1 prompt** — truyền weight breakdown vào AI để báo cáo phân loại GAP theo Critical/High/Medium/Low
- [ ] **Risk Register** — bảng phân loại GAP theo mức độ rủi ro trong output report
- [ ] **Scoring Breakdown Panel** — chart/bar thể hiện từng category đạt bao nhiêu % (calcCategoryBreakdown đã sẵn)
- [x] **Dynamic Standard Loading** — upload JSON/YAML tiêu chuẩn mới → backend parse + ChromaDB index → frontend render form tự động ✅
- [ ] **Thêm tiêu chuẩn**: PCI-DSS 4.0, HIPAA, NIS2, ISO 22301, NIST CSF (có thể upload qua /standards page)

### Cải thiện kỹ thuật:
- [x] **Weighted scoring cả ở backend** — iso27001.py + chat_service.py đã dùng weighted formula ✅
- [x] **Export PDF server-side** — weasyprint (fallback HTML) tại `/api/iso27001/assessments/{id}/export-pdf` ✅
- [ ] **Re-assessment diff** — so sánh 2 lần đánh giá để xem cải thiện/tụt lùi
- [ ] **Assessment scheduling** — lên lịch đánh giá định kỳ (quarterly/annually)
- [x] **Evidence upload** — per-control upload, list, delete, download tại `/api/iso27001/evidence/{control_id}` ✅
- [ ] **Multi-org support** — quản lý nhiều tổ chức, so sánh compliance across orgs

---

## IT Audit Workflow — Đề xuất Áp dụng cho Platform

IT Audit thực tế thường trải qua các bước sau. Dưới đây là mapping vào hệ thống CyberAI:

### Phase 1: Planning & Scoping (Lập kế hoạch)
- [ ] **Scope Definition** — cho phép chọn scope audit (toàn bộ hệ thống / chỉ network / chỉ app) → filter controls theo scope
- [ ] **Risk-Based Audit Planning** — dựa trên industry + org_size tự gợi ý controls ưu tiên cao (ngân hàng ≠ bệnh viện ≠ startup)
- [ ] **Audit Universe** — quản lý "bản đồ audit" (inventory toàn bộ hệ thống, apps, databases, network segments)

### Phase 2: Evidence Collection (Thu thập bằng chứng)
- [x] **Evidence Upload per Control** — mỗi control có slot upload file (PDF policy, screenshot config, log export) ✅
- [ ] **Automated Evidence Collection** — API integration với cloud providers (AWS/Azure) để tự pull config snapshots
- [ ] **Interview & Walkthrough Notes** — form ghi chú phỏng vấn, observation cho từng control domain
- [ ] **Configuration Audit Checklist** — checklist cấu hình server/network tự sinh từ system_info (VD: SSH config, firewall rules)

### Phase 3: Testing & Analysis (Kiểm tra & Phân tích)
- [ ] **Vulnerability Scan Import** — import results từ Nessus/Qualys/OpenVAS → tự map vào controls tương ứng
- [ ] **Compliance Gap Heatmap** — visualize GAP trên heatmap 2D (Severity × Category)
- [ ] **Control Effectiveness Rating** — ngoài "đạt/không đạt", thêm mức: Fully Effective / Partially Effective / Ineffective / Not Tested
- [ ] **Automated Technical Checks** — scan ports, check SSL certs, DNS config qua API (lightweight pentest)

### Phase 4: Reporting & Communication (Báo cáo)
- [ ] **Executive Summary Auto-Gen** — AI tạo bản tóm tắt cho C-level (1 trang, key metrics, top 5 risks)
- [x] **Risk Register với Remediation Timeline** — mỗi GAP kèm deadline, Severity, Likelihood × Impact scoring ✅
- [ ] **Benchmark Comparison** — so sánh kết quả đánh giá với industry average (nếu có data)
- [x] **PDF Export server-side** — weasyprint (fallback HTML) tại `/api/iso27001/assessments/{id}/export-pdf` ✅

### Phase 5: Follow-up & Monitoring (Theo dõi)
- [ ] **Remediation Tracker** — dashboard tracking progress fix GAP theo thời gian
- [ ] **Re-assessment Diff** — so sánh 2 lần đánh giá, highlight cải thiện/tụt lùi
- [ ] **Continuous Monitoring Dashboard** — real-time compliance score, alert khi score giảm
- [ ] **Assessment Scheduling** — lên lịch đánh giá quarterly/annually, email reminder

### Phase 6: Input/Output Improvement cho Model
- [ ] **Structured System Info** — parse network_diagram text thành structured JSON (VLAN list, firewall rules, server inventory)
- [x] **Weight Breakdown in AI Prompt** — gửi phân bổ weight (Critical: X, High: Y...) để AI đánh giá GAP có severity ✅
- [ ] **Custom Prompt Templates** — cho phép auditor tùy chỉnh Phase 1/Phase 2 prompt theo methodology riêng
- [ ] **RAG Enhancement** — index thêm best practices documents, CIS Benchmarks, NIST SP 800 series
- [ ] **AI Confidence Score** — model trả về confidence level cho mỗi finding (High/Medium/Low confidence)
- [ ] **Multi-language Report** — tạo báo cáo song ngữ Việt-Anh cho tổ chức quốc tế

---

## Map File Quan trọng

```
frontend-next/src/
├── app/form-iso/
│   ├── page.js          ← Form 4 bước, SvgGauge, Scoring Breakdown, Evidence Upload,
│   │                       Dynamic Standards, compact AI Mode Selector, server PDF export
│   └── page.module.css  ← CSS: Score Hero, weight badges, gauge, breakdown bars,
│                           compact model selector, flow diagram, evidence upload
├── app/standards/
│   ├── page.js          ← Upload UI, validate, standard list, detail panel
│   └── page.module.css  ← Standards management CSS
├── app/analytics/
│   ├── page.js          ← Dashboard, modal redesign, SVG gauge, PDF export
│   └── page.module.css  ← Modal CSS, pctBadge, md styles
├── data/
│   ├── standards.js     ← ISO_27001 + TCVN_11930 + mergeCustomStandard + calcCategoryBreakdown
│   └── controlDescriptions.js  ← Mô tả chi tiết từng control (requirement, criteria, hint)
├── components/
│   └── Navbar.js        ← Added "📚 Tiêu chuẩn" nav item

backend/
├── services/
│   ├── chat_service.py       ← assess_system(): weighted breakdown, risk register prompt,
│   │                           dynamic standard, missing critical controls list
│   ├── cloud_llm_service.py  ← LOCAL_ONLY_TASKS, routing, fallback logic
│   └── standard_service.py   ← Dynamic Standard CRUD, parse, validate, ChromaDB index
├── api/routes/
│   ├── iso27001.py           ← CRUD assessments, weighted compliance_percent,
│   │                           evidence upload/list/download/delete, PDF export (weasyprint)
│   └── standards.py          ← Standards REST API: upload, validate, list, get, delete, reindex

data/
├── standards/                ← Custom standard JSON files
├── evidence/                 ← Per-control evidence files ({control_id}/{filename})
├── exports/                  ← Server-generated PDF/HTML reports
│   └── .gitkeep
```

## New API Endpoints

### Evidence
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/iso27001/evidence/{control_id}` | Upload evidence file |
| GET | `/api/iso27001/evidence/{control_id}` | List evidence files |
| GET | `/api/iso27001/evidence/{control_id}/{filename}` | Download evidence |
| DELETE | `/api/iso27001/evidence/{control_id}/{filename}` | Delete evidence |
| GET | `/api/iso27001/evidence-summary` | Summary of all evidence |

### PDF Export
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/iso27001/assessments/{id}/export-pdf` | Generate PDF (weasyprint) or HTML fallback |

## New CSS Classes

### Compact Model Selector
| Class | Mô tả |
|---|---|
| `.modelCompactRow` | Flex row chứa 3 compact buttons |
| `.modelCompactBtn` | Button cho mỗi mode |
| `.modelCompactActive` | Active state cho button |
| `.modelDetailPanel` | Expandable detail panel khi nhấn ⓘ |
| `.modelDetailFlow` | Data flow visualization (📋→🖥️→☁️→📄) |
| `.flowStep` / `.flowLocal` / `.flowCloud` | Tags trong flow diagram |

### Scoring Breakdown
| Class | Mô tả |
|---|---|
| `.breakdownPanel` | Container cho category breakdown |
| `.breakdownGrid` | Grid layout cho cards |
| `.breakdownItem` | Card cho từng category |
| `.breakdownBarTrack` / `.breakdownBarFill` | Progress bar (weighted %) |
| `.breakdownMeta` | Controls count + điểm |

### Evidence Upload
| Class | Mô tả |
|---|---|
| `.panelUploadArea` | Container |
| `.panelUploadBtn` | Upload button (dashed border) |
| `.evidenceFileList` | List of uploaded files |
| `.evidenceFile` | Individual file row |
| `.evidenceDeleteBtn` | Delete button per file |

---

## CSS Variables Quan trọng
```css
--accent-blue, --accent-green, --accent-red, --accent-amber
--bg-card, --bg-subtle, --bg-muted, --bg-secondary
--border, --border-active, --border-light
--text-primary, --text-secondary, --text-muted, --text-dim
--blue-subtle, --green-subtle, --red-subtle, --amber-subtle
--shadow-sm, --shadow-md, --shadow-lg
```

---

## UI/UX Consolidation (24/03/2026)

### Navbar giảm từ 7 → 5 items
- Xóa `/standards` (đã có sẵn trong Analytics tab "📋 Tiêu chuẩn")
- Xóa `/templates` (đã tích hợp vào form-iso tab "📂 Mẫu")
- Remaining: Trang chủ, AI Chat, Đánh giá, Tin tức, Analytics

### Templates tích hợp vào form-iso
- Tab thứ 4: `📂 Mẫu` — hiển thị template cards với filter bar (ISO/TCVN)
- Template cards: org info, stats, compliance bar, "Phân tích hệ thống này →" button
- `ℹ` info button: hiển thị hướng dẫn sử dụng kho mẫu
- Navigation links: `← Quay lại Nhập liệu` và `📊 Analytics & Tiêu chuẩn →`

### Evidence Upload — Luôn hiển thị
- ℹ icon ở mỗi control **luôn clickable** (không cần `desc` tồn tại)
- Panel detail **luôn có** section "📎 Upload bằng chứng triển khai"
- Tooltip help text: hướng dẫn upload + list format support
- `evidenceFormats`: hiển thị danh sách extension hỗ trợ

### Evidence → AI Model Format
```js
buildEvidenceSummary() → string
// Output format:
// BẰNG CHỨNG ĐÃ CUNG CẤP CHO CÁC CONTROLS:
//   A.5.1: [2 file] — policy.pdf, access_control.docx
//   A.8.7: [1 file] — antivirus_config.log
//
// evidence_map: { "A.5.1": ["policy.pdf", "access_control.docx"] }
```
Dữ liệu evidence được nối vào `notes` field + gửi `evidence_map` object → Phase 1 AI nhận biết controls nào có minh chứng.

### New CSS Classes
| Class | Mô tả |
|---|---|
| `.headerNav` / `.headerNavLink` | Navigation links ở header page |
| `.evidenceHelpText` | Help text cho evidence upload section |
| `.evidenceFormats` | Danh sách extension hỗ trợ (monospace) |
| `.templatesWrap` | Container tab Mẫu |
| `.tplHeaderRow` / `.tplInfoBtn` / `.tplInfoPanel` | Header + ℹ info panel |
| `.tplFilterBar` / `.tplFilterBtn` / `.tplFilterActive` | Filter bar (Tất cả / ISO / TCVN) |
| `.tplGrid` / `.tplCard` / `.tplCardHeader` / `.tplCardBody` | Template card grid |
| `.tplStdBadge` / `.tplStdIso` / `.tplStdTcvn` | Standard badges |
| `.tplStatsRow` / `.tplStatBox` / `.tplStatNum` / `.tplStatLabel` | Stats row |
| `.tplComplianceSection` / `.tplComplianceTrack` / `.tplComplianceFill` | Compliance bar |
| `.tplCardFooter` / `.tplUseBtn` | Footer + "Phân tích →" button |
| `.tplNavRow` | Bottom navigation row |
| `.dropZone` / `.dropZoneActive` / `.dropZoneInner` | Drag-and-drop upload zone |
| `.evidencePreview` / `.evidencePreviewCode` / `.evidencePreviewBtn` | File content preview |
| `.evidenceFileWrap` | Evidence file wrapper với preview |

### Phase 2 — Evidence Upgrade (24/03/2026)

**Backend Evidence Parsing** (`iso27001.py`):
- `parse_evidence_file_content()` — Trích xuất nội dung file: txt/csv/json/xml/conf/log (raw text), PDF (pypdf), DOCX (python-docx), XLSX (openpyxl), image (metadata)
- `build_evidence_context_for_ai()` — Tạo structured text cho AI prompt từ evidence_map
- API preview: `GET /api/iso27001/evidence/{control_id}/{filename}/preview`
- Evidence content tự động inject vào `notes` trước khi gửi tới Phase 1 AI

**Frontend Evidence UX**:
- Drag-and-drop: `handleDragOver`, `handleDragLeave`, `handleDrop` → upload nhiều file cùng lúc
- `<input multiple>` — cho phép chọn nhiều file qua file dialog
- Preview nội dung: nút 👁️ → gọi API preview → hiện nội dung trong `<pre>` (text) hoặc link tải (image)

**Mobile Responsive** (`page.module.css`):
- `@media (max-width: 768px)` — tablet: step wizard dọc, form grid 1 cột, panel full-width từ bottom
- `@media (max-width: 480px)` — phone: tabs nhỏ hơn, template cards 1 cột, step wizard compact

---

## TODO — Đề xuất nâng cấp tiếp theo

### ✅ Đã hoàn thành
- [x] Backend parse evidence files (PDF/text/docx/xlsx → text)
- [x] Real-time evidence preview trong panel
- [x] Batch evidence upload (drag-and-drop + multi-file)
- [x] Mobile responsive (768px + 480px breakpoints)

### 🔴 IT Audit Workflow — Giai đoạn Lập kế hoạch (Audit Planning)
- [ ] **Scope definition**: Cho phép chọn phạm vi đánh giá (toàn bộ / theo phòng ban / theo hệ thống cụ thể)
- [ ] **Audit checklist generator**: Tự động tạo checklist kiểm tra dựa trên tiêu chuẩn đã chọn + industry context
- [ ] **Risk-based audit prioritization**: AI phân tích risk profile tổ chức → đề xuất thứ tự đánh giá controls ưu tiên
- [ ] **Pre-audit questionnaire**: Bảng câu hỏi sơ bộ gửi cho tổ chức trước khi audit (thu thập thông tin hạ tầng, policy, nhân sự)

### 🟠 IT Audit Workflow — Giai đoạn Thực hiện (Fieldwork)
- [ ] **Control testing matrix**: Bảng ma trận test cho từng control: mục tiêu test / phương pháp / sample size / kết quả
- [ ] **Finding classification**: Phân loại finding theo ISACA/IIA: Control Deficiency / Significant Deficiency / Material Weakness
- [ ] **Evidence quality scoring**: AI tự đánh giá chất lượng evidence đính kèm (đầy đủ / thiếu / không liên quan)
- [ ] **Interview notes**: Cho phép ghi chú phỏng vấn cho từng control (người phỏng vấn, thời gian, kết quả)

### 🟡 IT Audit Workflow — Giai đoạn Báo cáo (Reporting)
- [ ] **Assessment comparison**: So sánh 2 đánh giá side-by-side (trước/sau remediation)
- [ ] **Executive summary generator**: AI tạo Executive Summary riêng cho C-level (metrics, top risks, budget impact)
- [ ] **Remediation tracking**: Theo dõi tiến độ khắc phục từng finding (owner, deadline, status, re-test date)
- [ ] **PDF report branding**: Chèn logo tổ chức, tên auditor, thông tin pháp lý vào báo cáo

### 🟢 AI Model — Input/Output Improvements
- [ ] **Evidence content analysis prompt**: Cải thiện prompt Phase 1 để AI đánh giá CHẤT LƯỢNG evidence (không chỉ có/không có)
- [ ] **Multi-phase assessment**: Thêm Phase 0 (Pre-screening) → AI đánh giá sơ bộ trước khi deep analysis
- [ ] **Structured JSON output**: AI trả về structured data (JSON) thay vì chỉ Markdown → dễ parse cho dashboard
- [ ] **Historical trend analysis**: AI so sánh kết quả assessment hiện tại vs lịch sử → phát hiện xu hướng cải thiện/xấu đi
- [ ] **Control-level AI commentary**: Mỗi control có nhận xét riêng từ AI (không chỉ overall report)
- [ ] **Compliance roadmap**: AI tạo lộ trình chi tiết để đạt mục tiêu compliance % mong muốn (ví dụ: từ 45% → 80% trong 6 tháng)

### 🔵 Hạ tầng & DevOps
- [ ] **Auto-save form data**: Lưu draft vào localStorage tránh mất dữ liệu
- [ ] **Template builder**: User tạo và export template riêng từ assessment đã hoàn thành
- [ ] **Webhook notifications**: Gửi thông báo khi assessment hoàn thành (email / Slack / Telegram)
- [ ] **Role-based access**: Phân quyền Auditor / Manager / Viewer

---

## UI/UX Consolidation — 25/03/2026

### Bug Fixes
- **Bug:** Analytics page `Unexpected eof` — thừa `<div>` khi thêm Standards tab → fixed bằng đúng closing `</div>)}` ở cuối dashboard section
- **Bug:** `BUILTIN_STANDARDS` import unused trong form-iso (tree-shaking OK, không gây lỗi)

### Tính năng đã merge/consolidate:

#### 1. Analytics Page — Thêm tab "Tiêu chuẩn" ✅
- **Trước:** `/standards` là page riêng trong navbar → rườm rà
- **Sau:** Analytics có 2 main tabs: `📊 Dashboard` | `📋 Tiêu chuẩn`
- Standards tab: upload JSON/YAML, list built-in + custom, schema guide, drag-drop, detail side panel
- CSS mới trong `analytics/page.module.css`: `.mainTabNav`, `.mainTab`, `.stdSection`, `.stdDropZone`, `.stdCard`, `.stdDetailPanel`

#### 2. Form ISO — Templates đã là tab riêng `📂 Mẫu` ✅
- **Trước:** `/templates` page riêng, link từ subtitle
- **Sau:** Tab `📂 Mẫu` inline trong form-iso → chọn → auto-fill form → chuyển về Nhập liệu
- Header nav có link `📊 Analytics & Tiêu chuẩn` và `💬 AI Chat`

#### 3. Step 3 Controls — ⓘ cho TẤT CẢ controls ✅
- Mọi control đều có ⓘ button (không chỉ controls có description)
- Click ⓘ → detail panel bên phải slide in
- Panel có: Status badge, weight badge, requirement, criteria, hint, evidence list
- Controls không có desc vẫn show: "Chưa có thông tin chi tiết... đính kèm bằng chứng bên dưới"
- **Evidence upload luôn ở trong ⓘ panel** (không tách ra ngoài)

#### 4. Evidence Upload — Drag & Drop + Multi-file + Preview ✅
- Drop Zone với kéo-thả nhiều file cùng lúc
- Preview endpoint: `/api/iso27001/evidence/{control_id}/{filename}/preview`
- Content types: text/log/conf/json → hiện code preview; image → link download + size
- Evidence data được format và gửi vào AI prompt (Phase 1): `buildEvidenceSummary()`

#### 5. Navbar — Đã bỏ "Tiêu chuẩn" và "Mẫu" ✅
- Navbar chỉ còn: Trang chủ | AI Chat | Đánh giá | Tin tức | Analytics

### Map File Đã Thay đổi

```
frontend-next/src/
├── components/Navbar.js          ← Bỏ /standards và /templates nav items
├── app/analytics/
│   ├── page.js                   ← Thêm Standards management tab (2 main tabs)
│   └── page.module.css           ← Thêm mainTabNav, stdSection, stdCard, stdGrid CSS
├── app/form-iso/
│   ├── page.js                   ← Templates tab, evidence drag-drop, all controls có ⓘ
│   └── page.module.css           ← dropZone, evidenceFile, tplGrid, headerNav CSS
```

### TODO Còn lại (Ưu tiên):
- [x] **Auto-save draft** — `FORM_DRAFT_KEY` localStorage, restore on mount (ưu tiên reuse > draft)
- [x] **Structured JSON output** — `_build_structured_json()` → `json_data` stored, dashboard panel in result tab
- [x] **Scope definition** — radio UI (full/by_department/by_system) + scope_description freetext
- [x] **Standards format guide** — `FormatGuidePanel` modal: JSON/YAML/Built-in/ChromaDB tabs
- [ ] **Re-assessment diff** — So sánh 2 lần đánh giá (controls tăng/giảm, risk score thay đổi)
- [ ] **Mobile layout** — detail panel on mobile: scroll-lock, swipe-to-close
- [ ] **Template search** — filter by industry + search by name trong tab Mẫu

---

## LocalAI / SecurityLM — Cải tiến Phân tích Đánh giá (25/03/2026)

### Root Cause: LocalAI Busy khi News đang chạy

**Vấn đề:** `_call_localai()` kiểm tra `get_ai_status()` — nếu News summarizer đang chạy thì assessment Phase 1 bị block ngay lập tức với lỗi `[LocalAI] Busy: AI tóm tắt & dịch bài (3/6)...`

**Giải pháp đã áp dụng:**
- `_call_localai(priority=True)` — assessment có priority cao hơn news: pause news status → call LocalAI → restore status
- `iso_local` task_type tự động được gọi với `priority=True`
- News worker kiểm tra `get_ai_status()` → nếu thấy "Tạm dừng" thì skip iteration hiện tại

### Chunked Analysis — Giảm tải context window

**Vấn đề:** 93 controls ISO 27001 + system_info + RAG context → ~6000-8000 tokens → vượt context window SecurityLM 4096

**Giải pháp:** Phân tích theo category (chunk):
- LocalAI mode: mỗi category (A.5/A.6/A.7/A.8) được gửi thành 1 request riêng
- Mỗi chunk chỉ ~800-1200 tokens (compact prompt + 1 category controls)
- Kết quả 4 chunks được ghép lại thành `raw_analysis` tổng hợp
- Cloud mode: vẫn dùng single full prompt (context window lớn hơn)

```python
# chat_service.py — assess_system()
if p1_task_type == "iso_local" and all_controls_flat:
    for category in std_categories:
        chunk_prompt = _build_category_chunk_prompt(...)  # compact, ~800 tokens
        chunk_result = CloudLLMService.chat_completion(..., task_type="iso_local")
        chunk_results.append(f"### {cat_name}\n{chunk_content}")
    raw_analysis = "\n\n".join(chunk_results)
else:
    # Cloud: single full prompt
    result_p1 = CloudLLMService.chat_completion(messages_p1, ...)
    raw_analysis = result_p1.get("content", "")
```

### TODO Cải tiến LocalAI (Đề xuất)

| # | Cải tiến | Tác dụng | Output mong đợi |
|---|----------|----------|-----------------|
| 1 | **Per-control scoring** — Gửi từng control riêng lẻ để LocalAI chấm điểm (0/1 + risk reason) | Độ chính xác cao nhất, tránh hallucination về control ID | JSON array: `[{id, implemented, risk_level, reason}]` cho tất cả 93 controls |
| 2 | **Streaming chunk results** — WebSocket/SSE để frontend thấy từng category khi phân tích xong | UX tốt hơn, user thấy tiến trình real-time thay vì chờ 2-3 phút | Progress bar theo category, từng bảng Risk Register hiện dần |
| 3 | **LocalAI model quantization** — Dùng Q4_K_M thay Q8 nếu RAM < 16GB | Tốc độ inference tăng 40-60%, latency giảm từ 90s xuống ~40s | Response time Phase 1 < 45s/category |
| 4 | **Control embedding cache** — Pre-embed tất cả control labels vào ChromaDB → semantic match với hạ tầng user nhập | AI không cần "nhớ" toàn bộ controls, tìm kiếm ngữ nghĩa chính xác hơn | Tăng accuracy, giảm false negative khi user mô tả khác terminology chuẩn |
| 5 | **Fine-tuning SecurityLM** — Fine-tune model với dataset đánh giá ISO 27001 thực tế | Model hiểu domain-specific, không cần RAG context dài | Giảm prompt length 50%, tăng accuracy controls identification lên 85%+ |
| 6 | **Parallel category chunks** — Nếu LocalAI hỗ trợ concurrent requests, gửi 4 chunks song song | Thời gian Phase 1 giảm từ 4×45s → 45s (parallel) | Report hoàn chỉnh trong < 60s thay vì 3-4 phút |
| 7 | **GAP confidence score** — Mỗi GAP có confidence (0-1) từ model | Lọc bỏ GAP hallucination, chỉ hiển thị GAP có confidence > 0.7 | Risk Register chính xác hơn, ít false positive |
| 8 | **Assessment queue với priority** — Background queue có priority levels: assessment > chat > news | Không bao giờ block assessment khi news chạy | Isolated resource management, zero conflict |

---

## Bilingual Terminology trong UI (25/03/2026)

Tất cả tooltip ℹ trong form-iso hiển thị thuật ngữ kỹ thuật theo format:
```
English Term (Nghĩa tiếng Việt)
```

**Ví dụ:**
- `DMZ Zone (Vùng mạng biên)`
- `VLAN (Virtual LAN - Mạng LAN ảo)`
- `EDR/XDR (Endpoint Detection & Response)`
- `SIEM (Security Information & Event Management)`
- `WAF (Web Application Firewall - Tường lửa ứng dụng web)`
- `HA (High Availability - Tính sẵn sàng cao)`
- `Phishing (Lừa đảo qua email)`, `Ransomware (Mã độc tống tiền)`, `Data Leak (Rò rỉ dữ liệu)`
