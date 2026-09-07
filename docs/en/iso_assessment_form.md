# CyberAI Platform — ISO Assessment Feature

---

## 1. Overview

> 💡 **What does this feature do?** The ISO Assessment system helps you check **how compliant** your organization is with international security standards (ISO 27001, NIST, PCI DSS...). AI will automatically:
> 1. **Find gaps** — Compare "what you've done" vs "what the standard requires" → show what's missing
> 2. **Assess risks** — Each gap is analyzed by AI: "If this control is missing, what's the risk? How severe?"
> 3. **Generate report** — Automatically produce a professional report: compliance score, risk register, action plan
>
> **Real-world example:** ACME Corp wants to know "How compliant are we with ISO 27001?". They fill in a 4-step form → AI analyzes → Result: "62.5% compliant, missing 2 critical controls for encryption and malware management."

### What is GAP Analysis? — Simple Explanation

> 🎯 **GAP = the distance between where you are and where you should be.** Imagine:
> - **ISO 27001** requires 93 security controls (e.g., must have firewall, must encrypt data, must train staff...)
> - **Your company** has implemented 50 controls
> - **GAP** = 43 controls not yet done → That's the "gap" to improve
>
> AI analyzes each GAP: "Missing control A.8.7 (malware management) → Risk: hackers can install malware → Severity: Critical → Recommendation: deploy antivirus within 30 days"

4-step wizard for comprehensive cybersecurity compliance assessment. Supports **ISO 27001:2022**, **TCVN 11930:2017**, and **custom uploaded standards**.

Frontend: [`/form-iso`](frontend-next/src/app/form-iso/page.js) with [`StepProgress`](frontend-next/src/components/StepProgress.js) navigation.

Backend: [`/api/iso27001/assess`](backend/api/routes/iso27001.py) triggers a background task processed by [`assessment_helpers.py`](backend/services/assessment_helpers.py).

---

## 2. Assessment Workflow (4 Steps)

### Step 1 — Organization & Scope

| Field | Description |
|-------|-------------|
| Organization name | Company or entity name |
| Industry | Industry sector |
| Organization size | Employee/asset scale |
| Standard | ISO 27001 (93 controls, 4 categories) / TCVN 11930 (34 controls, 5 categories) / Custom |
| Scope | `full` / `department` / `system` |

### Step 2 — Infrastructure Details

| Field | Description |
|-------|-------------|
| Servers | Server inventory and configuration |
| Firewalls | Firewall deployment details |
| VPN | VPN services in use |
| Cloud services | Cloud provider and services |
| Antivirus | Endpoint protection solutions |
| SIEM | Security monitoring systems |
| Backup systems | Backup infrastructure |
| Recent incidents | Any recent security incidents |

### Step 3 — Controls Checklist

- **Toggle per control**: implemented / not implemented
- **Per-category select-all** for bulk toggling
- **Evidence upload** per control (drag-drop, max 10 MB)
- Allowed file types: `PDF`, `PNG`, `JPG`, `DOC`, `DOCX`, `XLSX`, `CSV`, `TXT`, `LOG`, `CONF`, `XML`, `JSON`

**Evidence content extraction for AI context:**

| File Type | Extraction Method |
|-----------|-------------------|
| TXT, LOG, CONF, CSV, XML, JSON | Read directly as text |
| PDF | `pypdf` |
| DOCX | `python-docx` |
| XLSX | `openpyxl` |

### Step 4 — System Description & AI Mode

| Field | Description |
|-------|-------------|
| Network topology | Description of network architecture |
| Additional notes | Free-form supplementary information |
| AI mode | `Local` / `Hybrid` / `Cloud` |

---

## 3. 2-Phase AI Pipeline

### Phase 1 — GAP Analysis

**Model:** SecurityLLM 7B (local) or cloud provider.

```
For each standard category:
  1. RAG lookup (top_k=2, domain-scoped collection)
  2. Build compact prompt:
     ├── Missing (unimplemented) controls for the category
     ├── System summary from infrastructure details
     └── RAG context chunks
  3. LLM returns JSON array per category
  4. Validate output → retry up to 3 times on failure
```

**Per-control output schema:**

```json
[
  {
    "id": "A.5.1",
    "severity": "critical|high|medium|low",
    "likelihood": "high|medium|low",
    "impact": "high|medium|low",
    "risk": "Description of risk",
    "gap": "Description of gap",
    "recommendation": "Remediation action"
  }
]
```

**Validation & anti-hallucination:**

- JSON extraction from LLM output (handles markdown fences, partial JSON)
- **Anti-hallucination**: reject any control IDs not in the valid control set for the selected standard
- Retry up to 3 times on validation failure
- **Fallback**: [`infer_gap_from_control()`](backend/services/assessment_helpers.py) generates gap analysis from control metadata when LLM fails
- **Severity normalization**: if >70% of gaps are `critical`, redistribute proportionally across severity levels

### Phase 2 — Report Formatting

**Model:** Meta-Llama 8B (local) or cloud provider.

**Input:** Compressed Phase 1 Risk Register (max 2500 chars) + weight breakdown.

**Output:** 5-section Markdown report:

| Section | Content |
|---------|---------|
| 1. ĐÁNH GIÁ TỔNG QUAN | Compliance %, weight breakdown by severity |
| 2. RISK REGISTER | Table: Control \| GAP \| Severity \| Likelihood \| Impact \| Risk \| Recommendation \| Timeline |
| 3. GAP ANALYSIS | Gaps grouped by severity |
| 4. ACTION PLAN | 0–30 days / 1–3 months / 3–12 months |
| 5. EXECUTIVE SUMMARY | Key metrics, top 3 risks, budget estimates in VND |

---

## 4. Compliance Scoring

### Weighted Formula

```
W = Σ(implemented_weight) / Σ(all_weights) × 100%
```

**Severity weights:**

## 4. Compliance Scoring

The platform strictly distinguishes two complementary measurement sets:

### 1. Control Coverage (Raw Quantity Metric)
- **Formula:** `(Implemented Controls / Total Controls) × 100%`
- Reflects literal control completion (e.g., `47/93 controls` ~ `50.54%`).
- Itemized into: `self_declared_implemented`, `evidence_supported_implemented`, `not_evidenced_or_missing`.

### 2. Weighted Compliance (Security Depth Metric)
- **Formula:** `W = Σ(achieved_weight) / Σ(max_weight) × 100%`
- Critical controls carry weight **4**, High **3**, Medium **2**, and Low **1**.
- Accurately captures prioritized security posture (e.g., `237.5 / 430.0` ~ `55.23%`).

| Severity | Weight |
|----------|--------|
| Critical | 4 |
| High | 3 |
| Medium | 2 |
| Low | 1 |

### Compliance Tiers

| Score | Tier |
|-------|------|
| ≥ 80% | High compliance |
| ≥ 50% | Medium compliance |
| ≥ 25% | Low compliance |
| < 25% | Critical |

---

## 5. Unified Assessment Result Schema

All APIs, UI views, and exporters share a single standardized data contract [`UnifiedAssessmentResult`](backend/schemas/assessment_schema.py):

<details>
<summary>📄 View Unified Assessment Result JSON Schema</summary>

```json
{
  "assessment_id": "assess-7c81a29f-3d18-4f51-b841-8664b58e76a0",
  "run_id": "run_43bce82f1092",
  "code_version": "6a15651c9d0f",
  "created_at": "2026-09-07T09:20:10.104Z",
  "completed_at": "2026-09-07T09:20:16.120Z",
  "status": "completed",
  "standard": {
    "id": "iso27001",
    "name": "ISO/IEC 27001:2022"
  },
  "control_coverage": {
    "self_declared_implemented": 47,
    "evidence_supported_implemented": 15,
    "not_evidenced_or_missing": 46,
    "total_controls": 93,
    "raw_percentage": 50.54
  },
  "weighted_compliance": {
    "weighted_score": 237.5,
    "weighted_max_score": 430.0,
    "percentage": 55.23,
    "algorithm": "iso27001_domain_weighted_v1"
  },
  "controls": [
    {
      "control_id": "A.8.8",
      "user_declaration": "implemented",
      "evidence_status": "direct_attachment",
      "evidence_file_ids": ["patch_report_masked.pdf"],
      "fact_card_ids": ["fc_patch_01"],
      "auto_match_confidence": null,
      "assessment_verdict": "satisfied",
      "verdict_basis": ["user_declaration", "direct_evidence"],
      "expert_review_status": "pending"
    }
  ],
  "evidence_manifest_ref": "data/evidence_manifests/assess-7c81a29f.json",
  "audit_trace_ref": "data/audit_traces/assess-7c81a29f.json"
}
```

</details>

**Standardized Control Statuses:**
- `user_declaration`: `implemented` | `not_implemented` | `unknown`
- `evidence_status`: `direct_attachment` | `auto_matched` | `no_evidence` | `not_reviewed`
- `assessment_verdict`: `satisfied` | `not_evidenced` | `missing` | `needs_expert_review`
- `verdict_basis`: `user_declaration`, `direct_evidence`, `auto_match`, `ai_inference`
- `expert_review_status`: `pending` | `approved` | `modified` | `rejected`

---

## 6. Supported Standards

### Built-in Standards

| Standard | ID | Controls | Categories |
|----------|-----|----------|------------|
| ISO 27001:2022 | `iso27001` | 93 | 4 — A.5 Organizational, A.6 People, A.7 Physical, A.8 Technological |
| TCVN 11930:2017 | `tcvn11930` | 34 | 5 — Network, Server, Application, Data, Management |
| Custom uploaded | `{custom_id}` | Up to 500 | Variable |

Control catalogs defined in [`controls_catalog.py`](backend/services/controls_catalog.py).

---

## 7. Evidence Manifest & Privacy Sanitization

The evidence subsystem automatically builds a cryptographic manifest for each assessment run:
- **Masked Filenames**: Private IP patterns (`192.168.***.***`) and credentials in filenames are sanitized prior to reporting.
- **SHA-256 Hashing**: Generates SHA-256 digests for all uploaded artifacts without embedding raw configs or logs.
- **Fact Card Linkage**: Links Fact Card IDs to targeted control codes.
- **Objective Reporting**: Explicitly states *"chưa ghi nhận đủ minh chứng trong phạm vi dữ liệu đánh giá; cần chuyên gia xác minh"* instead of presuming unevidenced controls are completely absent.

---

## 8. Export Specifications

All export routines consume the unified `UnifiedAssessmentResult` model:

| Format | Target Standards | Features & Guarantees |
|--------|------------------|-----------------------|
| **SoA XLSX** | ISO 27001 (93 rows) / TCVN 11930 (34 rows) | Metadata header banner, `Score (0-5)` at column index 7, Verdict, Verdict Basis, and masked evidence list. |
| **Risk Register XLSX** | ISO 27001 / TCVN 11930 | Structured $L \times I$ matrix with transparent `risk_assessment_basis` and metadata banner. |
| **DOCX** | A4 Professional Layout | `<w:tblHeader/>` repeats on page breaks, `<w:cantSplit/>` prevents row fragmentation, zero raw markdown (`#`, `*`), zero emoji font failures, mandatory audit disclaimer. |
| **PDF** | WeasyPrint / Paged Media | Clean pagination, repeated table headers, no orphan titles, automated `report_exported` audit trace event with SHA-256 digest. |

---

## 9. Frontend UI

Implemented in [`/form-iso`](frontend-next/src/app/form-iso/page.js).

### Navigation

4-step wizard using [`StepProgress`](frontend-next/src/components/StepProgress.js) component.

### Tabs

| Tab | Purpose |
|-----|---------|
| Form | Assessment wizard (Steps 1–4) |
| Result | Rendered Markdown report + compliance gauge + JSON dashboard |
| History | Paginated list of past assessments |
| Templates | Pre-filled assessment templates |

---

## 10. Per-Control Detail Drawer & CyberAI Assistant

Each control card provides a **Detail Drawer** with 3 dedicated workspaces:

1. **Criteria Tab:**
   - Detailed control description, audit criteria, and common pitfalls.
   - Recommended technical commands (PowerShell / Linux Bash).
2. **Evidence Tab:**
   - Dedicated drag & drop / browse file uploader for the specific control.
   - Live synchronization with `/api/iso27001/evidence/{control_id}` and instant status updates.
3. **CyberAI Assistant Tab:**
   - Asynchronous execution via `asyncio.to_thread` with 15s timeout protection against proxy dropouts.
   - **"Generate SOP & Scripts" (`generate_sop`):** Produces 4-step enterprise SOPs, practical PowerShell/Bash scripts, audit checklists, and RACI matrices.
   - **"Verify Evidence" (`verify_evidence`):** Audits uploaded files against control acceptance criteria.
   - **"Ask Question" (`custom_query`):** Interactive technical Q&A with context awareness.
   - **Enterprise SOP Fallback Generator:** Guarantees deterministic, domain-specific guidance even during 100% background GPU/CPU saturation.
