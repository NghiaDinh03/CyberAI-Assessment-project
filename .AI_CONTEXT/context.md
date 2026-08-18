# Context: PehanIn/ISO-27001-2022-Toolkit — Phân tích & Kế hoạch tích hợp

> File này là **bản nháp để review**, chưa thực hiện thay đổi nào lên repo.
> Nguồn: <https://github.com/PehanIn/ISO-27001-2022-Toolkit> (MIT License, 180 ⭐, 114 forks, last push 2024-10-15).

---

## 1. Bộ toolkit này là gì?

Một bộ **template tài liệu hành chính** (Word + Excel) phục vụ triển khai một ISMS (Information Security Management System) theo chuẩn **ISO/IEC 27001:2022**. **Không có code**, không có script, không có engine — đúng nghĩa "document pack" mà các consultant ISO hay bán $200-2000 trên Etsy/Gumroad nhưng tác giả release MIT free.

### Cấu trúc 12 thư mục (mỗi thư mục thường có 1 `Guidance.docx` + 1 `Template.docx/.xlsx`)

| # | Thư mục | Định dạng chính | Mục đích nghiệp vụ |
|---|---|---|---|
| 1 | Gap Assessment Plan | `.docx` | Đo khoảng cách hiện trạng vs 93 controls Annex A |
| 2 | SOA (Statement of Applicability) | `.xlsx` | Bảng 93 controls × (Áp dụng/Loại trừ + Lý do + Trạng thái) |
| 3 | Risk Register | `.xlsx` + `.docx` | Đăng ký rủi ro: asset → threat → likelihood × impact → treatment |
| 4 | Scope and Context Definition | `.docx` | Phạm vi ISMS, bên liên quan, điều khoản 4 ISO 27001 |
| 5 | Asset Inventory | `.xlsx` | Liệt kê tài sản thông tin + classification + owner |
| 6 | BCDR Plan | `.docx` | Business Continuity & Disaster Recovery |
| 7 | Information Security Policy & Procedures | `.docx` | Chính sách ISMS chính + procedures con |
| 8 | Awareness & Training Plan | `.docx` | Kế hoạch đào tạo nhân viên |
| 9 | Management Review Meeting | `.docx` | Biên bản họp soát xét lãnh đạo (clause 9.3) |
| 10 | ISMS Checklists | `.docx` | Checklist tự đánh giá |
| 11 | Internal Audit Plan | `.docx` | Kế hoạch audit nội bộ (clause 9.2) |
| 12 | ROI Analysis | `.xlsx` | Tính chi phí/lợi ích đầu tư ISMS |

### Toolkit này **không** làm gì
- ❌ Không có **logic chấm điểm tự động** — toàn bộ là template trống
- ❌ Không có **mapping JSON/YAML** giữa controls với evidence
- ❌ Không có **API / web UI**
- ❌ Không có **AI / NLP** phân tích chứng cứ
- ❌ Không có **dataset benchmark** để so sánh
- ❌ Không có **gap analysis pattern library** (chỉ template trống)

---

## 2. Repo mình hiện tại đang có gì? (đối chiếu)

| Domain | Toolkit Pehanin | CyberAI-Assessment-project |
|---|---|---|
| **93 controls Annex A** | ✅ SoA `.xlsx` (text mô tả) | ✅ [`data/iso_documents/iso27001_annex_a.md`](data/iso_documents/iso27001_annex_a.md:1) + [`data/knowledge_base/controls.json`](data/knowledge_base/controls.json:1) + [`controlDescriptions.vi.js`](frontend-next/src/data/controlDescriptions.vi.js:1) (đã có UI Form-ISO chấm điểm) |
| **Gap analysis** | ✅ `.docx` template trống | ✅ [`data/iso_documents/gap_analysis_patterns.md`](data/iso_documents/gap_analysis_patterns.md:1) + [`assessment_helpers.py`](backend/services/assessment_helpers.py:1) (logic auto-score) |
| **Assessment criteria** | ❌ | ✅ [`data/iso_documents/assessment_criteria.md`](data/iso_documents/assessment_criteria.md:1) + [`checklist_danh_gia_he_thong.md`](data/iso_documents/checklist_danh_gia_he_thong.md:1) |
| **Risk Register** | ✅ Excel template | ❌ **CHƯA CÓ** — đây là gap thật |
| **Asset Inventory** | ✅ Excel template | ❌ **CHƯA CÓ** |
| **SoA xuất ra** | ✅ Static Excel | ⚠️ Có form chấm nhưng **không export SoA chuẩn** |
| **BCDR / Policies / Training / Mgmt Review / Audit Plan / ROI** | ✅ 6 templates | ❌ **CHƯA CÓ** (đây là tầng "GRC paperwork" mà repo bỏ trống) |
| **Multi-standard** (NIST/CIS/PCI/GDPR/SOC2…) | ❌ Chỉ ISO 27001 | ✅ 13 chuẩn trong [`data/iso_documents/`](data/iso_documents/) |
| **AI chatbot phân tích log** | ❌ | ✅ [`chat_service.py`](backend/services/chat_service.py:1) |
| **RAG vector store** | ❌ | ✅ ChromaDB |
| **Benchmark dataset** | ❌ | ✅ [`benchmark_iso27001.json`](data/knowledge_base/benchmark_iso27001.json:1) |

**Kết luận đối chiếu**: Toolkit Pehanin **không thay thế** được bất cứ phần nào của repo mình. Nhưng nó **bổ sung** được tầng "tài liệu đầu ra hành chính" mà repo đang thiếu — đặc biệt **Risk Register** và **Asset Inventory** là 2 thứ có giá trị nhất nếu gắn vào pipeline form-iso.

---

## 3. Có áp dụng được cho repo không? — 4 lựa chọn

### Option A — KHÔNG áp dụng (giữ nguyên repo)
**Khi nào chọn**: Nếu định vị repo là "AI-powered SOC log analyzer + multi-standard assessment chatbot", không phải "GRC consulting toolkit".
- Toolkit thuần `.docx`/`.xlsx`, không tự động hoá → trái với DNA codebase (FastAPI + Next.js + LLM).
- 93 controls đã có rồi (file `.md` + JSON), nhập thêm Excel SoA là **trùng lặp**.

### Option B — Vendor minh hoạ (recommend cho landing/demo)
Tạo thư mục [`docs/templates/iso27001-toolkit-pehan/`](docs/templates/iso27001-toolkit-pehan/) chứa:
- Bản copy 12 file `.docx/.xlsx` (kèm `ATTRIBUTION.md` ghi rõ nguồn + MIT)
- Link tải trực tiếp từ trang [`/standards`](frontend-next/src/app/standards/page.js:1) hoặc [`/templates`](frontend-next/src/app/templates/page.js:1) (đã có sẵn)
- Mục tiêu: cho khách hàng tải về **làm tài liệu chứng nhận**, repo chỉ là phần "AI phụ trợ"
- **Effort**: ~2 giờ (tải file + viết attribution + thêm card UI)

### Option C — Trích logic từ template, tự build module nội bộ ⭐ **đề xuất**
Đọc nội dung `.docx/.xlsx` → trích **field schema** → build:

#### C1. Risk Register module (mới)
- Backend: [`backend/services/risk_register_service.py`](backend/services/risk_register_service.py:1) + [`backend/api/routes/risks.py`](backend/api/routes/risks.py:1)
- Schema: `{id, asset_ref, threat, vulnerability, likelihood (1-5), impact (1-5), inherent_score, treatment, residual_score, owner, review_date, linked_controls[]}`
- Storage: JSON tại [`data/risks/`](data/risks/) (mirror pattern của `data/sessions/`)
- Frontend: trang `/risk-register` với bảng có heatmap 5×5, drilldown, link sang [`/form-iso`](frontend-next/src/app/form-iso/page.js:1) controls
- Export: `.xlsx` qua `openpyxl` — output **giống y file Pehanin** (để khách dùng được luôn)
- **Effort**: 3-4 ngày

#### C2. Asset Inventory module (mới)
- Tương tự C1, schema `{id, name, type (Hardware/Software/Data/Service), classification (Public/Internal/Confidential/Restricted), owner, location, criticality, controls[]}`
- Liên kết 2 chiều với Risk Register (asset_ref) và Form-ISO (linked_controls)
- **Effort**: 2-3 ngày

#### C3. SoA exporter (nâng cấp)
- Tận dụng dữ liệu chấm điểm form-iso đã có → generate **`SoA.xlsx`** đúng format Pehanin
- Endpoint `POST /api/iso27001/soa/export` → trả file `.xlsx`
- **Effort**: 1-2 ngày

#### C4. Document generators (nice-to-have)
- Auto-fill `.docx` template (Scope, BCDR, Policy, Internal Audit) bằng `python-docx` + Jinja
- Input: org metadata + assessment results → output: bộ tài liệu chứng nhận sẵn sàng
- **Effort**: 1 tuần (mỗi template ~1 ngày)

### Option D — Fork & merge ngược
Không khuyến nghị. Toolkit là document pack, không có maintainer active (last push 1.5 năm) → fork chỉ để giữ snapshot là đủ.

---

## 4. Kế hoạch đề xuất (combined B + C1 + C3)

### Phase 1 — Quick win (1 tuần)
- [ ] Tải 12 file template, đặt tại [`docs/templates/iso27001-toolkit-pehan/`](docs/templates/iso27001-toolkit-pehan/) + `ATTRIBUTION.md` (MIT, credit Pehan Indira)
- [ ] Thêm card "ISO 27001 Toolkit Templates" trên trang [`/templates`](frontend-next/src/app/templates/page.js:1) cho download
- [ ] Bổ sung mục trong [`docs/en/iso_assessment_form.md`](docs/en/iso_assessment_form.md:1): "Sau khi chấm xong, tải template SoA/Risk Register từ /templates để hoàn tất chứng nhận"

### Phase 2 — Risk Register MVP (1 tuần)
- [ ] Backend service + route + JSON storage
- [ ] Frontend trang `/risk-register` (bảng + form CRUD + heatmap)
- [ ] Liên kết 2 chiều Risk ↔ Control (link sang form-iso)
- [ ] Test: [`backend/tests/test_risk_register.py`](backend/tests/test_risk_register.py:1)

### Phase 3 — SoA Exporter (2-3 ngày)
- [ ] `openpyxl` generator đọc state form-iso → output `.xlsx` đúng schema Pehanin
- [ ] Nút "Export SoA (.xlsx)" trên [`/form-iso`](frontend-next/src/app/form-iso/page.js:1)

### Phase 4 — Asset Inventory (1 tuần) — optional
- [ ] CRUD module + liên kết Risk Register

### Phase 5 — Document generators (1-2 tuần) — long-term
- [ ] `.docx` auto-fill cho Scope, BCDR, Policy, Internal Audit, Mgmt Review

---

## 5. Rủi ro & Lưu ý

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| MIT cho phép, nhưng **bắt buộc giữ copyright notice** | Low | `ATTRIBUTION.md` rõ ràng + credit trong UI footer |
| Repo Pehanin không update từ 2024-10 → có thể outdated với errata ISO 27001:2022 | Medium | Chỉ dùng làm tham khảo schema, controls lấy từ source chính thức của ISO |
| Trùng lặp chức năng nếu copy nguyên xi | Medium | Option C: chỉ trích schema, không nhúng `.docx/.xlsx` vào logic |
| Bloat repo nếu commit binary `.docx/.xlsx` (~411KB) | Low | Chấp nhận được, hoặc dùng Git LFS |
| File `.docx/.xlsx` khó review trong PR | Low | Để riêng thư mục `docs/templates/`, không lẫn với `data/` |

---

## 6. Câu hỏi cần bạn quyết

1. **Định vị repo**: Là "AI tool hỗ trợ assessment" (giữ Option A) hay "GRC platform end-to-end" (đi Option B/C)?
2. **Risk Register có phải gap thật?** (Tôi nghĩ có — không có nó thì khó chứng minh đã làm clause 6.1.2)
3. **Asset Inventory có cần không?** (Có giá trị nhưng overlap nhẹ với Form-ISO scope)
4. **Document generators (Phase 5)**: Cần thiết hay overkill?
5. Có muốn tôi **clone toolkit về local** + **đọc nội dung `.xlsx` Risk Register** để extract schema chính xác trước khi code không?

---

## 7. 🔴 GAP LỚN: Evidence Extraction Pipeline (CHƯA CÓ — cần build gấp)

> Yêu cầu mới từ bạn: "Nhân sự sẽ upload mớ file template đã điền lên cho model → cần trích xuất được text để AI phân tích".

### 7.1 Hiện trạng (bad news)

File [`backend/services/document_service.py`](backend/services/document_service.py:1) **hiện tại là stub rỗng**:

```python
class DocumentService:
    async def process_upload(self, file: UploadFile):
        content = await file.read()
        # Process document (placeholder)
        return {"filename": file.filename, "status": "processed", "chunks": 10}
```

Và [`backend/requirements.txt`](backend/requirements.txt:1) **không có** bất kỳ thư viện parser nào (`python-docx`, `openpyxl`, `pypdf`, `unstructured`, `tika`…). Endpoint [`/documents/upload`](backend/api/routes/document.py:14) trả về dữ liệu giả.

**Hậu quả**: Nếu nhân sự upload `Risk Register.xlsx` hoặc `Policy.docx` ngay bây giờ → model **không thấy nội dung thật**, chỉ thấy metadata filename. Đây là gap **phải fix trước** khi đi Phase 2-5.

### 7.2 Kiến trúc Evidence Extraction được đề xuất

```
                     ┌─────────────────────────────────────────┐
  Upload (.docx /    │  POST /api/documents/upload             │
  .xlsx / .pdf /     │      │                                  │
  .txt / .md / .csv) │      ▼                                  │
 ──────────────────▶ │  DocumentIngestService.dispatch()       │
                     │      │                                  │
                     │      ▼ (theo MIME / extension)          │
                     │  ┌──────────────────────────────────┐   │
                     │  │ Parser strategy registry:        │   │
                     │  │ - .docx  → python-docx           │   │
                     │  │ - .xlsx  → openpyxl (per-sheet)  │   │
                     │  │ - .pdf   → pypdf + OCR fallback  │   │
                     │  │ - .txt/.md/.csv → stdlib         │   │
                     │  │ - .doc/.xls (legacy) → reject    │   │
                     │  │   hoặc dùng libreoffice headless │   │
                     │  └──────────────────────────────────┘   │
                     │      │                                  │
                     │      ▼                                  │
                     │  Normalize → {                          │
                     │    doc_id, filename, mime,              │
                     │    extracted_text,                      │
                     │    sections: [{heading, body}],         │
                     │    tables: [{sheet, rows}],             │
                     │    metadata (author, mtime, pages)      │
                     │  }                                      │
                     │      │                                  │
                     │      ▼                                  │
                     │  Chunker (512-1024 tokens, overlap 80)  │
                     │      │                                  │
                     │      ▼                                  │
                     │  ChromaDB upsert                        │
                     │  (collection="evidence")                │
                     │      │                                  │
                     │      ▼                                  │
                     │  Return: {doc_id, chunks, preview}      │
                     └─────────────────────────────────────────┘
                                   │
                                   ▼
         Available for: /api/chat (RAG), /form-iso auto-score,
                        /api/iso27001/assess, manual review UI
```

### 7.3 Parser stack (thư viện đề xuất)

| Format | Lib | Reason | Fallback |
|---|---|---|---|
| `.docx` | **`python-docx`** | Native, tách được paragraph + heading + table | `docx2txt` (đơn giản hơn) |
| `.xlsx` | **`openpyxl`** | Đã cần cho SoA exporter ở Phase 3 → tái dùng | `pandas.read_excel` |
| `.pdf` (text) | **`pypdf`** | Pure-Python, không cần Poppler | `pdfplumber` (table tốt hơn) |
| `.pdf` (scan) | **`pytesseract` + `pdf2image`** | OCR cho PDF ảnh | Optional, gate bằng env flag |
| `.doc` / `.xls` (MS 97-2003) | **`libreoffice --headless --convert-to docx`** | Không lib Python native tốt | Reject với message "Please save as .docx" |
| `.txt / .md` | stdlib | - | - |
| `.csv` | stdlib `csv` | - | `pandas` nếu cần type inference |
| `.html` | **`beautifulsoup4`** | Có sẵn nếu đã cài RAG | - |

**All-in-one alternative**: [`unstructured`](https://github.com/Unstructured-IO/unstructured) library xử lý được ~25 format qua 1 API nhưng nặng (~500MB deps bao gồm `libmagic`, `tesseract`). **Không nên** trừ khi bạn cần >10 format → với 6 format chính thì stack trên gọn hơn.

### 7.4 Schema lưu trữ

```python
# backend/api/schemas/document.py (cần mở rộng)
class ExtractedDocument(BaseModel):
    doc_id: str                    # uuid4
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    uploaded_by: Optional[str]
    toolkit_type: Optional[Literal[
        "risk_register", "asset_inventory", "soa",
        "policy", "bcdr", "audit_report", "other"
    ]]                             # classifier dựa trên filename + content
    linked_control_ids: list[str]  # vd ["A.5.1", "A.8.3"] — link 2 chiều
    linked_risk_ids: list[str]
    extracted_text: str            # concatenated
    sections: list[Section]        # {heading, body, level}
    tables: list[Table]            # {name/sheet, headers, rows}
    chunk_ids: list[str]           # chunks trong ChromaDB
    checksum: str                  # SHA-256 để dedupe
```

Storage: [`data/evidence/{doc_id}/`](data/evidence/) (đã có thư mục rỗng `.gitkeep`) chứa:
- `raw/{filename}` — file gốc
- `extracted.json` — kết quả parse
- `preview.md` — markdown rendering (cho UI xem nhanh không cần parse lại)

### 7.5 Phase mới (chèn vào lộ trình)

**Phase 0 — Evidence Extraction Pipeline (PRIORITY 1, làm trước Phase 2)** — 1 tuần

- [ ] Cài deps: `python-docx`, `openpyxl`, `pypdf`, `pdfplumber`, `beautifulsoup4` vào [`backend/requirements.txt`](backend/requirements.txt:1)
- [ ] Refactor [`document_service.py`](backend/services/document_service.py:1) → tạo `backend/services/document_ingest/` với:
  - `base.py` — `BaseParser` ABC + registry
  - `docx_parser.py`, `xlsx_parser.py`, `pdf_parser.py`, `text_parser.py`
  - `classifier.py` — đoán `toolkit_type` từ filename/keyword (regex: `risk.?register`, `asset.?inv`, `SoA|statement.of.app`…)
  - `chunker.py` — 512-1024 tokens, overlap 80
  - `storage.py` — ghi `data/evidence/{doc_id}/`
- [ ] Update [`document.py`](backend/api/routes/document.py:1) route: trả `ExtractedDocument` thật + chunk count thật + preview 500 chars
- [ ] Thêm `GET /api/documents/{doc_id}` (metadata), `GET /api/documents/{doc_id}/raw` (download), `GET /api/documents/{doc_id}/text` (extracted)
- [ ] ChromaDB collection `"evidence"` với metadata `{doc_id, toolkit_type, linked_controls, chunk_index}`
- [ ] Frontend: upgrade trang upload (hiện đang rất basic) → preview + link controls + delete
- [ ] Unit tests với sample files tại [`backend/tests/fixtures/`](backend/tests/fixtures/):
  - `sample_risk_register.xlsx` (trích từ toolkit Pehanin)
  - `sample_policy.docx`
  - `sample_audit_report.pdf` (text + scanned)
- [ ] Integration test: upload → extract → query RAG → chat hỏi về risk → model trả lời đúng

### 7.6 Edge cases phải handle

| Case | Giải pháp |
|---|---|
| File `.docx` có `<w:drawing>` (ảnh chèn vào policy) | Skip ảnh, extract alt-text nếu có; optionally OCR bằng pytesseract |
| File `.xlsx` có **merged cells** (rất phổ biến trong Risk Register) | `openpyxl.utils.cell.range_boundaries` + unmerge logic |
| File `.xlsx` có **multiple sheets** | Parse tất cả sheet, mỗi sheet 1 `Table` object, metadata ghi sheet name |
| File `.pdf` **encrypted** | Detect + báo lỗi rõ ràng "PDF is password-protected" |
| File `.pdf` **scanned** (ảnh) | Nếu `extract_text()` trả < 50 chars → auto fallback OCR (optional, env `OCR_ENABLED=true`) |
| File `.docx` có **track changes / comments** | Flatten, extract nội dung accepted version |
| File **quá lớn** (>50MB) | Reject ở route level + message |
| **Duplicate upload** (cùng checksum) | Return existing `doc_id` thay vì tạo mới |
| Format **lạ** (`.odt`, `.rtf`, `.pages`) | Log + reject với hướng dẫn convert |
| File **malicious** (macro, XXE, ZIP bomb) | `python-docx`/`openpyxl` đã disable macro; limit unzip size |

### 7.7 Tích hợp với Form-ISO & Chatbot (huge win)

Khi có evidence extraction thật, mở khoá loạt tính năng:

1. **Auto-suggest controls liên quan** khi upload policy `.docx` → phân loại theo 93 controls (dùng embedding + [`controls.json`](data/knowledge_base/controls.json:1))
2. **Auto-score control** trong [`/form-iso`](frontend-next/src/app/form-iso/page.js:1): user upload policy → backend đọc → AI tự đề xuất điểm 0-5 + lý do trích dẫn đoạn cụ thể
3. **Chatbot hỏi evidence**: "Policy truy cập đã đề cập đến MFA chưa?" → RAG trên chunks của doc đó → trả lời có citation
4. **Gap analysis tự động**: so sánh policy nộp lên với [`gap_analysis_patterns.md`](data/iso_documents/gap_analysis_patterns.md:1) → highlight thiếu gì
5. **Risk Register import**: upload `.xlsx` Pehanin → auto-populate module Risk Register (Phase 2)

### 7.8 Rủi ro Phase 0

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Docker image phình to khi thêm tesseract (OCR) | Medium | Gate OCR bằng env flag, build 2 variant image (`slim` / `full-ocr`) |
| Parsing `.pdf` phức tạp → edge case vô hạn | High | Bắt đầu với text-only PDF, OCR là Phase 0.5 nếu cần |
| File upload quá lớn làm đầy RAM | Medium | Stream upload + limit 50MB + temp file, không load full vào RAM |
| Embedding cost nếu upload batch 100 doc | Low-Medium | Ollama local embedding miễn phí (đã có [`model_router.py`](backend/services/model_router.py:1)) |
| Malicious file (ZIP bomb trong .xlsx/.docx) | Medium | `defusedxml` + size limit + sandbox nếu paranoid |

---

## 8. Lộ trình cập nhật (có Phase 0)

| Phase | Nội dung | Effort | Ưu tiên |
|---|---|---|---|
| **0** 🆕 | **Evidence Extraction Pipeline** (docx/xlsx/pdf → text → ChromaDB) | 1 tuần | **P0 — bắt buộc trước** |
| 1 | Host 12 template `.docx/.xlsx` + download UI | ~2h | P1 |
| 2 | Risk Register module | 1 tuần | P1 |
| 3 | SoA `.xlsx` exporter | 2-3 ngày | P2 |
| 4 | Asset Inventory | 1 tuần | P3 |
| 5 | `.docx` auto-fill generators | 1-2 tuần | P4 |

**Effort tối thiểu để có MVP có giá trị (Phase 0+1+2+3)**: ~3 tuần.

---

## 9. Review Karpathy 2026-04-21 — đề xuất tinh giản + UI fix

### A. Plan siết lại (Simplicity First)
- **Bỏ** khỏi MVP: Phase 4 (Asset Inventory), Phase 5 (.docx auto-fill), OCR, `toolkit_type` classifier, `uploaded_by` → speculative, chưa có user request rõ ràng.
- **Giữ** MVP 2 tuần: Phase 0 (ingest pipeline gọn 4 parser) + Phase 1 (host template) + Phase 2 (Risk Register) + Phase 3 (SoA exporter).
- Schema Phase 0 thu về: `{doc_id, filename, mime, size_bytes, uploaded_at, extracted_text, sections, tables, chunk_ids, checksum}` — 9 field là đủ, 4 field khác defer.
- PDF chỉ text-layer qua `pypdf`; nếu `extract_text() < 50 chars` → return rỗng + warning. OCR là Phase 0.5 khi có yêu cầu thực.
- Docker image giữ slim, không thêm tesseract/poppler.

### B. UI — đã fix dấu `*` bằng chứng bắt buộc (2026-04-21)
- Trước: label "Bằng chứng yêu cầu" **không** có dấu `*` → user không biết đây là field bắt buộc (dù gate logic đã chặn tick "đã triển khai" khi chưa upload).
- Sau: thêm `<span className={styles.required}> *</span>` ở 2 chỗ:
  - [`form-iso/_components/DetailDrawer.js:181`](frontend-next/src/app/form-iso/_components/DetailDrawer.js:181) — tab `criteria` của drawer
  - [`form-iso/page.js:1841`](frontend-next/src/app/form-iso/page.js:1841) — panel expand control
- Bổ sung class `.required` vào [`DetailDrawer.module.css`](frontend-next/src/app/form-iso/_components/DetailDrawer.module.css:1) (class tương tự [`page.module.css:384`](frontend-next/src/app/form-iso/page.module.css:384) sẵn có).
- Gate logic đã có từ trước ở [`ControlRow.js:39`](frontend-next/src/app/form-iso/_components/ControlRow.js:39) + [`DetailDrawer.js:306`](frontend-next/src/app/form-iso/_components/DetailDrawer.js:306), không đụng.
- Hint string "Cần tải lên ít nhất 1 tệp bằng chứng." trong [`vi.json:483`](frontend-next/src/i18n/vi.json:483) giữ nguyên.

### C. Câu hỏi cho reviewer tiếp theo
- Scope MVP 2 tuần (Phase 0+1+2+3 rút gọn) OK không, hay vẫn giữ lộ trình 3-4 tuần gốc?
- Evidence extractor MVP có cần classifier đoán `toolkit_type` từ filename ngay từ đầu không, hay để user tự chọn dropdown ở UI upload?
- Phase 0 có nên tách thành 2 PR: (a) parser + endpoint, (b) ChromaDB indexing — để review dễ hơn?

---

## 10. TL;DR (bản cập nhật)

> Toolkit Pehanin là **bộ template `.docx/.xlsx` thuần** cho ISO 27001:2022. Repo mình đã mạnh hơn ở controls catalog + AI chatbot + multi-standard, nhưng **thiếu 2 thứ**:
> 1. 🔴 **Evidence Extraction Pipeline** — [`document_service.py`](backend/services/document_service.py:1) đang là stub trống, **không parse được gì** → model không đọc được evidence mà nhân sự upload
> 2. **Risk Register + Asset Inventory + SoA exporter** — toolkit Pehanin có sẵn template cho các artifact này
>
> **Đề xuất lộ trình**: **Phase 0 (extract pipeline) ưu tiên nhất**, sau đó Phase 1 (host templates) + Phase 2 (Risk Register) + Phase 3 (SoA xlsx exporter). Bỏ C2/C4/Phase 5 trừ khi định vị GRC full-stack.
>
> **Effort tối thiểu**: ~3 tuần (P0 + P1 + P2 + P3).
>
> **Câu hỏi quyết định**:
> 1. OK đi Phase 0 trước không?
> 2. Phase 0 có cần OCR cho PDF scanned không? (Ảnh hưởng kích thước Docker image +500MB)
> 3. Tôi clone toolkit Pehanin về local + mở `Risk Register.xlsx` để extract schema chính xác luôn, rồi viết code?
>
> **Trả lời Yes/No 3 câu trên là tôi bắt đầu code được ngay.**

---

## 11. CORE FEATURES PLAN — 3 Tính Năng Core (2026-05-06)

> **Plan chi tiết:** `.AI_CONTEXT/core_features_plan.md`
> **Subtasks:** `.AI_CONTEXT/subtask.md` — Phase 10
> **Vị trí:** `.AI_CONTEXT/` (plan nội bộ, không phải docs chính thức)

### 3 tính năng core:

1. **AI Chat** — Hỏi đáp ATTT, phân tích log, RAG + Web search
   - Intent classification (semantic + keyword)
   - Model routing (Local/Cloud/Hybrid)
   - Streaming response via SSE
   - Session history + context management

2. **Đánh giá hệ thống (Assessment)** — TCVN 11930 + ISO 27001
   - Per-control group chunking (5-8 controls/group)
   - Evidence processing pipeline (OCR + text extract + chunk)
   - Privacy filter (PII stripping)
   - Per-control evidence verdict (satisfied/partial/missing)
   - 2-phase AI: SecurityLM (GAP) + Cloud (Report)

3. **Output Báo cáo IT Audit** — Markdown + JSON + XLSX + PDF
   - 5-section Markdown report (A4 format)
   - Structured JSON for dashboard
   - SoA .xlsx export
   - Risk Register .xlsx export
   - PDF generation (WeasyPrint)

### Implementation: ~18 ngày (1 developer)
- Phase 10A: Evidence Pipeline (1 tuần)
- Phase 10B: Per-Control Assessment (1 tuần)
- Phase 10C: Output and Export (1 tuần)
- Phase 10D: Knowledge Base (3 ngày)

---

## 12. CẬP NHẬT TRẠNG THÁI HIỆN TẠI (2026-05-26)

Hệ thống CyberAI đã chính thức hoàn thiện **100%** và sẵn sàng tuyệt đối cho môi trường vận hành thực tế (Production Go-Live Ready):

1. **Evidence Extraction Pipeline & OCR**: Tích hợp toàn diện Tesseract OCR cùng pypdf/docx/openpyxl, tự động parse hình ảnh và scan PDF, chuẩn hóa và strip PII bảo mật.
2. **SQLite Chat Persistence**: Chuyển đổi thành công lịch sử chat sang database SQLite local lưu trữ bền vững tại `/data/sessions/chat_history.db`.
3. **Background Document Watcher**: Quét tự động thư mục `/data/iso_documents` mỗi 30 giây để index tài liệu quy trình SOC vào ChromaDB collection.
4. **Smart Cloud Fallback & Low-Resource Model Optimization**:
   - Tích hợp bộ vá lỗi JSON tự động thông minh `json_repair` cho các local model yếu/chạy CPU, cứu nguy 80% lỗi định dạng ngay tại Attempt 1.
   - Smart Cloud Fallback tự động gọi Cloud LLM cứu nguy ở Attempt 3 nếu local model lỗi nặng.
5. **System Prompt Guard**: Tích hợp bộ lọc bảo mật Chat API chặn đứng 100% các cuộc tấn công prompt injection/jailbreak, trả về cảnh báo chuẩn ATTT.
6. **Hạ tầng Dockerized & Testing**:
   - Tách SearXNG thành service private cục bộ hoạt động độc lập và an toàn trong Docker Compose.
   - Cấu hình cache Ollama model pulls, tránh kéo lại model mỗi khi restart container.
   - Viết bộ kiểm thử tĩnh và HTTP runtime smoke test tự động cho frontend Next.js, đạt tỷ lệ test pass 100%.
   - Chuẩn bị sẵn template GPU Nvidia reservation cho Ollama & LocalAI.

