# CyberAI Platform — ISO Assessment Feature

---

## 1. Overview

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

## 5. Structured JSON Output

[`_build_structured_json`](backend/services/assessment_helpers.py) produces a machine-readable summary:

```json
{
  "compliance_tier": "medium",
  "compliance_score": 62.5,
  "weight_breakdown": {
    "critical": {"implemented": 3, "total": 5, "weight": 4},
    "high": {"implemented": 10, "total": 15, "weight": 3},
    "medium": {"implemented": 8, "total": 10, "weight": 2},
    "low": {"implemented": 4, "total": 5, "weight": 1}
  },
  "risk_summary": {
    "critical": 2,
    "high": 5,
    "medium": 2,
    "low": 1
  },
  "top_gaps": [
    {"id": "A.8.7", "severity": "critical", "gap": "..."},
    {"id": "A.5.23", "severity": "critical", "gap": "..."}
  ]
}
```

---

## 6. Supported Standards

### Built-in Standards

| Standard | ID | Controls | Categories |
|----------|-----|----------|------------|
| ISO 27001:2022 | `iso27001` | 93 | 4 — A.5 Organizational, A.6 People, A.7 Physical, A.8 Technological |
| TCVN 11930:2017 | `tcvn11930` | 34 | 5 — Network, Server, Application, Data, Management |
| Custom uploaded | `{custom_id}` | Up to 500 | Variable |

Control catalogs defined in [`controls_catalog.py`](backend/services/controls_catalog.py).

### Additional Standards for RAG Domain Mapping

These standards are indexed into ChromaDB collections and available for RAG context, but do not have dedicated control checklists:

`nd13`, `nist_csf`, `pci_dss`, `hipaa`, `gdpr`, `soc2`

---

## 7. Evidence System

| Feature | Description |
|---------|-------------|
| Upload | Per-control file upload via `/api/iso27001/evidence/{control_id}` (max 10 MB) |
| Storage | `data/evidence/{control_id}/` directory |
| Content extraction | File contents extracted and injected as AI context during assessment |
| Summary | `/api/iso27001/evidence-summary` aggregates evidence across all controls |
| Preview | `/api/iso27001/evidence/{control_id}/{filename}/preview` returns text content for supported types |
| Management | List, download, delete per control per file |

---

## 8. Export

| Method | Implementation | Details |
|--------|---------------|---------|
| **PDF** (server) | weasyprint | HTML → PDF with professional styling, via `/api/iso27001/assessments/{id}/export-pdf` |
| **HTML fallback** (server) | Jinja2 | Returns styled HTML if weasyprint is unavailable |
| **HTML** (client) | Browser | Client-side HTML export with browser print-to-PDF |

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

### Processing UX

- Submit triggers background task
- **Polling interval**: every 8 seconds until completion
- Compliance gauge visualization on result
- Structured JSON dashboard for machine-readable output
