# ISO 27001 Assessment Form — Technical Deep Dive

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-ISO_Assessment-blue?style=flat-square)](iso_assessment_form.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Đánh_giá_ISO-red?style=flat-square)](iso_assessment_form_vi.md)

</div>

---

## Table of Contents

1. [Overview](#1-overview)
2. [End-to-End Flow Diagram](#2-end-to-end-flow-diagram)
3. [Form Structure — 4-Step Wizard](#3-form-structure--4-step-wizard)
4. [Async Assessment — BackgroundTasks](#4-async-assessment--backgroundtasks)
5. [AI Analysis Pipeline](#5-ai-analysis-pipeline)
6. [Knowledge Base — ISO Documents](#6-knowledge-base--iso-documents)
7. [Assessment Result Format](#7-assessment-result-format)
8. [Polling Mechanism](#8-polling-mechanism)
9. [Multi-Standard Support](#9-multi-standard-support)
10. [Data Persistence](#10-data-persistence)

---

## 1. Overview

The ISO 27001 Assessment module evaluates an organization's information security posture against ISO 27001:2022 (and TCVN 14423) controls. It works **asynchronously** — the user submits a form and immediately gets a job ID back; the AI analysis runs in a background thread and results are polled.

| Feature | Detail |
|---------|--------|
| Standard | ISO 27001:2022 (default), TCVN 14423 (optional) |
| AI model | `gemini-2.5-pro` via Open Claude (task_type=`iso_analysis`) |
| Execution | FastAPI `BackgroundTasks` (async, non-blocking) |
| Storage | JSON files: `/data/assessments/{uuid4}.json` |
| Polling | Frontend polls `GET /api/iso27001/assessments/{id}` every 3s |
| Knowledge | ChromaDB `iso_documents` collection — 7 ISO/legal documents |

---

## 2. End-to-End Flow Diagram

```
User fills 4-step form
         │
         ▼
POST /api/iso27001/assess  { system_info, controls[], standard_id }
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  iso27001.py — assess()                                    │
│                                                            │
│  1. assessment_id = str(uuid4())                           │
│  2. Save JSON { id, status:"pending", data:{...} }         │
│     → /data/assessments/{id}.json                          │
│  3. background_tasks.add_task(process_assessment_bg, id)   │
│  4. Return HTTP 202 { id, status:"pending" }               │
└──────────────────────────┬─────────────────────────────────┘
                           │ immediate response to frontend
                           │
         ┌─────────────────┘
         │  [Background Thread — FastAPI BackgroundTasks]
         ▼
┌────────────────────────────────────────────────────────────┐
│  process_assessment_bg(assessment_id)                      │
│                                                            │
│  1. Load JSON from /data/assessments/{id}.json             │
│  2. ChatService.assess_system(system_data)                 │
│     a. VectorStore.search(query, top_k=5)                  │
│        → Retrieve relevant ISO controls from ChromaDB      │
│     b. Build detailed system_prompt + user_prompt          │
│     c. CloudLLMService.chat_completion(                    │
│           task_type="iso_analysis"                         │
│        )  → gemini-2.5-pro via Open Claude                 │
│           → LocalAI fallback if Open Claude fails          │
│  3. Update JSON { status:"done", result:{...} }            │
└────────────────────────────────────────────────────────────┘
         │
         │  [Frontend polls every 3 seconds]
         ▼
GET /api/iso27001/assessments/{id}
→ { id, status:"pending" }   (while processing)
→ { id, status:"done", result:{...} }  (when complete)
```

---

## 3. Form Structure — 4-Step Wizard

File: [`frontend-next/src/app/form-iso/page.js`](../frontend-next/src/app/form-iso/page.js)

### Step 1 — Standard & Company Info

```
┌────────────────────────────────────────────────┐
│  Select Standard:  [ISO 27001:2022] [TCVN 14423]│
│                                                 │
│  Company Name:     [____________________]       │
│  Industry:         [____________________]       │
│  System Description: [__________________]       │
└────────────────────────────────────────────────┘
```

### Step 2 — Security Controls Selection

Organized by control category (Annex A domains):

```
┌──────────────────────────────────────────────────────┐
│  A.5 Information Security Policies      [Select All] │
│  ☑ A.5.1 Policies for information security           │
│  ☑ A.5.2 Information security roles                  │
│                                                      │
│  A.9 Access Control                     [Select All] │
│  ☑ A.9.1 Business requirements for access control    │
│  ☐ A.9.2 User access management                      │
└──────────────────────────────────────────────────────┘
```

### Step 3 — Current Security Status

Binary/ternary questions about existing controls:

| Field | Options |
|-------|---------|
| `firewall` | yes / no |
| `antivirus` | yes / no |
| `backup` | yes / partial / no |
| `patch_management` | yes / no |
| `incident_response` | yes / no |
| `access_control` | yes / partial / no |
| `encryption` | yes / partial / no |
| `employee_training` | yes / no |
| `physical_security` | yes / no |
| `risk_assessment` | yes / partial / no |

### Step 4 — Review & Submit

Shows a summary of all selected controls and system info before submission.

---

## 4. Async Assessment — BackgroundTasks

File: [`backend/api/routes/iso27001.py`](../backend/api/routes/iso27001.py)

### Route Handler

```python
@router.post("/iso27001/assess")
async def assess(data: SystemInfo, background_tasks: BackgroundTasks):
    assessment_id = str(uuid4())

    assessment_data = {
        "id": assessment_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "data": data.dict()
    }
    save_assessment(assessment_id, assessment_data)

    background_tasks.add_task(process_assessment_bg, assessment_id, data.dict())

    return {"id": assessment_id, "status": "pending"}
```

### Background Processor

```python
def process_assessment_bg(assessment_id: str, system_data: dict):
    data = load_assessment(assessment_id)
    try:
        result = ChatService.assess_system(system_data)
        data["status"] = "done"
        data["result"] = result
    except Exception as e:
        data["status"] = "error"
        data["error"] = str(e)
    finally:
        save_assessment(assessment_id, data)
```

### File Storage

```python
ASSESSMENTS_DIR = "/data/assessments"

def save_assessment(assessment_id, data):
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_assessment(assessment_id):
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
```

---

## 5. AI Analysis Pipeline

File: [`backend/services/chat_service.py`](../backend/services/chat_service.py)

### `ChatService.assess_system(system_data)`

```python
@staticmethod
def assess_system(system_data: Dict) -> Dict:
    vs = ChatService.get_vector_store()

    # 1. Build search query from system data
    query = (
        f"{system_data.get('standard_id', 'ISO 27001')} "
        f"{system_data.get('industry', '')} "
        f"{' '.join(system_data.get('controls', []))}"
    )

    # 2. Retrieve relevant ISO context
    context_docs = vs.search(query, top_k=5)
    context = "\n\n---\n\n".join([d["document"] for d in context_docs])

    # 3. Build AI prompt
    system_prompt = f"""You are an expert ISO 27001 auditor.
Analyze the provided system information against ISO 27001:2022 controls.
Reference the following knowledge base context in your analysis:

{context}

Provide:
1. Overall compliance score (0-100)
2. Compliance level (Non-compliant / Partial / Mostly Compliant / Fully Compliant)
3. Critical gaps found
4. Specific recommendations for each gap
5. Per-control analysis for selected controls"""

    user_prompt = f"""System Information:
Company: {system_data['company_name']}
Industry: {system_data['industry']}
Description: {system_data['system_description']}

Current Security Posture:
- Firewall: {system_data.get('firewall')}
- Antivirus: {system_data.get('antivirus')}
- Backup: {system_data.get('backup')}
- Patch Management: {system_data.get('patch_management')}
- Incident Response: {system_data.get('incident_response')}
- Access Control: {system_data.get('access_control')}
- Encryption: {system_data.get('encryption')}
- Employee Training: {system_data.get('employee_training')}
- Physical Security: {system_data.get('physical_security')}
- Risk Assessment: {system_data.get('risk_assessment')}

Selected Controls for Assessment: {', '.join(system_data.get('controls', []))}"""

    # 4. Call AI
    result = CloudLLMService.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.2,
        task_type="iso_analysis"    # → gemini-2.5-pro
    )

    return {"analysis": result["content"], "model": result["model"], "provider": result["provider"]}
```

---

## 6. Knowledge Base — ISO Documents

Stored in `data/iso_documents/` and indexed into ChromaDB (`iso_documents` collection):

| File | Content | Chunks (approx) |
|------|---------|-----------------|
| `iso27001_annex_a.md` | Full Annex A — all 93 controls with descriptions | ~120 |
| `assessment_criteria.md` | Scoring and compliance criteria | ~25 |
| `checklist_danh_gia_he_thong.md` | Vietnamese system evaluation checklist | ~30 |
| `luat_an_ninh_mang_2018.md` | Vietnam Cybersecurity Law 2018 | ~40 |
| `network_infrastructure.md` | Network security guidelines and best practices | ~35 |
| `nghi_dinh_13_2023_bvdlcn.md` | Decree 13/2023 on personal data protection | ~30 |
| `tcvn_11930_2017.md` | TCVN 11930:2017 IT security standard | ~35 |

**Total: ~315 chunks** indexed with cosine similarity, chunk_size=600, overlap=150.

---

## 7. Assessment Result Format

```json
{
  "id": "7e0b008d-34d9-4c5b-bf9a-f3de2d53658e",
  "status": "done",
  "created_at": "2025-03-24T09:00:00",
  "data": {
    "company_name": "ACME Corp",
    "industry": "Finance",
    "controls": ["A.5.1", "A.9.1", "A.9.2"],
    "firewall": "yes",
    "patch_management": "no"
  },
  "result": {
    "analysis": "## ISO 27001:2022 Compliance Assessment\n\n**Overall Score: 62/100**\n\n**Compliance Level: Partial**\n\n### Critical Gaps Found:\n1. No patch management process in place...\n2. No incident response plan documented...\n\n### Recommendations:\n1. **Patch Management (A.12.6.1)**: Implement automated patch management...\n\n### Control Analysis:\n- **A.5.1** Information security policies: ✅ Compliant\n- **A.9.1** Access control policy: ⚠️ Partial\n- **A.9.2** User access management: ❌ Non-compliant",
    "model": "gemini-2.5-pro",
    "provider": "open_claude"
  }
}
```

---

## 8. Polling Mechanism

### Frontend Polling (form-iso/page.js)

```js
const submit = async () => {
  const res = await fetch('/api/iso27001/assess', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(form)
  })
  const { id } = await res.json()

  // Start polling
  setResult({ status: 'pending', id })
  const interval = setInterval(async () => {
    const poll = await fetch(`/api/iso27001/assessments/${id}`)
    const data = await poll.json()
    if (data.status !== 'pending') {
      clearInterval(interval)
      setResult(data)
    }
  }, 3000)   // Poll every 3 seconds
}
```

### Status Flow

```
submit()   → status: "pending"  → show spinner
poll()×n   → status: "pending"  → keep spinner
poll()     → status: "done"     → show result
poll()     → status: "error"    → show error message
```

### List All Assessments

```python
def list_assessments():
    for filename in os.listdir(ASSESSMENTS_DIR):
        if filename.endswith(".json"):
            data = json.load(open(filepath))
            summaries.append({
                "id": data["id"],
                "status": data["status"],
                "created_at": data.get("created_at"),
                "company_name": data["data"].get("company_name")
            })
    return sorted(summaries, key=lambda x: x["created_at"], reverse=True)
```

---

## 9. Multi-Standard Support

File: [`frontend-next/src/data/standards.js`](../frontend-next/src/data/standards.js)

The form supports multiple standards. Each standard defines its own control set:

```js
export const STANDARDS = [
  {
    id: "iso27001_2022",
    name: "ISO 27001:2022",
    categories: [
      {
        name: "A.5 Information Security Policies",
        controls: [
          { id: "A.5.1", name: "Policies for information security" },
          { id: "A.5.2", name: "Information security roles and responsibilities" },
          ...
        ]
      },
      ...  // 4 categories, 93 total controls
    ]
  },
  {
    id: "tcvn14423",
    name: "TCVN 14423",
    categories: [...]
  }
]
```

### Standard Change Handler

When user switches standard mid-form, selected controls are cleared:

```js
const handleStandardChange = (newStandardId) => {
  setForm(prev => ({
    ...prev,
    standard_id: newStandardId,
    controls: []           // reset control selection
  }))
}
```

---

## 10. Data Persistence

### Assessment Storage

```
/data/assessments/
├── 7e0b008d-34d9-4c5b-bf9a-f3de2d53658e.json   ← status: done
├── 71789587-a7cd-4de2-94ed-09a540de90f7.json   ← status: done
└── {uuid4}.json                                  ← status: pending|done|error
```

### History Loading (Analytics page)

The analytics page (`/analytics`) loads all assessment summaries via:

```
GET /api/iso27001/assessments  (list endpoint)
→ [{ id, status, created_at, company_name }, ...]
```

Clicking an entry loads the full result:

```
GET /api/iso27001/assessments/{id}
→ { id, status, data, result }
```

### Reuse Assessment

The "Reuse" button on the analytics page pre-fills the form with the original submission data:

```js
const handleReuse = () => {
  router.push(`/form-iso?prefill=${encodeURIComponent(JSON.stringify(selectedDetail.data))}`)
}
```
