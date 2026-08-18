# Repository Cleanup & Docs Consolidation Plan

> **Status**: DRAFT for user review. **No files have been deleted.** Everything below is analysis only.
> **Last updated**: 2026-04-20
> **Scope**: (1) clarify the misunderstanding about `.gitignore` and `.log` files; (2) audit every `.md` file for repo value; (3) propose a clean EN/VI docs structure.

---

## 0. Clarifications (in response to your questions)

### Q1: "Why delete `.gitignore`?"
**I never proposed deleting it.** The proposal was the **opposite** — *add entries* to it so logs and local IDE config stay on disk for debugging but are **not pushed to GitHub**. `.gitignore` is the file that makes that work. Apologies for the unclear wording last round.

### Q2: "Logs are useful for debug — keep them?"
Yes — logs **stay on the filesystem** for debugging. The only change is **never commit them to Git** (current behavior accidentally tracks `_bk.log`, `_fe.log`, `backend.log`, `ollama.log`). Your local copies remain untouched; only the tracked-in-Git copies are removed (`git rm --cached <file>`). Concrete plan in §1 below.

### Q3: "Other files — what's their purpose?"
Per-file utility table in §2 below; nothing is deleted unless its function is replaced or its purpose has expired.

---

## 1. Root-level files — utility analysis

| File | Purpose | Action |
|---|---|---|
| `.clinerules` | Cline IDE rule (RTK token-killer prefix). Active. | **KEEP**. Already tracked. |
| `🛡️ .clinerules` | Emoji-prefixed duplicate. Likely a Windows editor artifact (path with emoji). | **NEEDS REVIEW** — diff vs canonical first; if identical → delete the emoji copy. |
| `.env` | Local secrets. Already gitignored. | **KEEP locally; do nothing.** |
| `.env.example` | Template for new contributors. | **KEEP**. |
| `.gitignore` | Source of truth for exclusions. | **KEEP and EXTEND** with: `*.log`, `.claude/`, `backend/data/`, `__pycache__/`, `.pytest_cache/`. |
| `_bk.log`, `_fe.log`, `backend.log`, `ollama.log` | Runtime logs from local dev runs. | **`git rm --cached` only** (file stays on disk). Add `*.log` to `.gitignore`. |
| `README.md` | Project entry point (EN). 136 lines — concise, OK. | **KEEP**. |
| `README_vi.md` | Project entry point (VI). 204 lines — slightly long but acceptable. | **KEEP**. |
| `context.md` | Active living plan (you are reviewing it). | **KEEP**. |
| `docker-compose.yml` / `docker-compose.prod.yml` | Container orchestration. | **KEEP**. |

---

## 2. Docs folder — `.md` audit (38 files total)

### Methodology
1. Inventory every `.md` outside `node_modules`, `.next`, `__pycache__`, `.pytest_cache`.
2. Cross-reference each doc against [`README.md`](../../README.md:151), [`README_vi.md`](../../README_vi.md:228), source code links, and other docs.
3. Verdict scale:
   - **KEEP** — referenced by code/README/another doc, or contains unique reference info.
   - **MERGE** — overlaps with another doc; consolidate.
   - **PARK** — historical/planning doc; move to `docs/archive/` instead of deletion (recoverable).
   - **DELETE** — duplicate, generated, or no value.

### 2.1 Top-level (root) and shared
| File | Lines | Verdict | Reason |
|---|---:|---|---|
| `README.md` | 136 | KEEP | EN entry point, links to `docs/en/*`. |
| `README_vi.md` | 204 | KEEP | VI entry point, links to `docs/vi/*`. |
| `context.md` | 213 | KEEP | Active implementation plan. |
| `docs/en/cleanup-plan.md` | (this) | KEEP until cleanup is executed, then PARK to `docs/archive/2026-04-cleanup.md`. |

### 2.2 `data/iso_documents/*.md` — RAG knowledge base (18 files)
These are **NOT documentation**; they are **input corpus** for ChromaDB indexing (`reindex_domains` route).
**All KEEP — DO NOT TOUCH.** Removing any breaks RAG retrieval for the corresponding standard.

| File | Used by |
|---|---|
| `assessment_criteria.md`, `author_profile.md`, `checklist_danh_gia_he_thong.md`, `gap_analysis_patterns.md`, `infrastructure_description_guide.md`, `network_infrastructure.md` | RAG general assessment context |
| `iso27001_annex_a.md`, `iso27002_2022.md` | ChromaDB `iso27001` collection |
| `tcvn_11930_2017.md`, `nd85_2016_cap_do_httt.md`, `nghi_dinh_13_2023_bvdlcn.md`, `luat_an_ninh_mang_2018.md` | ChromaDB Vietnam-law collections |
| `cis_controls_v8.md`, `nist_csf_2.md`, `nist_sp800_53.md` | ChromaDB NIST collections |
| `nis2_directive.md`, `gdpr_compliance.md`, `hipaa_security_rule.md`, `pci_dss_4.md`, `soc2_trust_criteria.md`, `owasp_top10_2021.md` | Multi-standard support |

### 2.3 `data/knowledge_base/dataset_schema.md`
| Lines | Verdict | Reason |
|---:|---|---|
| 108 | **KEEP** | Schema spec referenced by [`backend/services/dataset_generator.py`](../../backend/services/dataset_generator.py:1). |

### 2.4 `docs/en/` — English documentation (18 files)

| File | Lines | Verdict | Reason |
|---|---:|---|---|
| `architecture.md` | 326 | **KEEP** | Top-level system map, linked from README. |
| `api.md` | 172 | **KEEP** | Endpoint reference, linked from README. |
| `deployment.md` | 380+ | **KEEP** | Production guide, linked from README. |
| `chatbot_rag.md` | 176 | **KEEP** | Linked from README + cross-linked. |
| `chromadb_guide.md` | 240+ | **KEEP** | Vector store ops guide, linked. |
| `analytics_monitoring.md` | 381 | **KEEP** | Prometheus dashboard, linked. |
| `backup_strategy.md` | 231 | **KEEP** | DR procedure, linked. |
| `iso_assessment_form.md` | 200+ | **KEEP** | Wizard reference, linked. |
| `algorithms.md` | 592 | **KEEP** | Scoring/intent/RAG algorithms, linked + cross-linked. |
| `benchmark.md` | 442 | **KEEP** | Benchmark reference, linked. |
| `case_studies.md` | 351 | **KEEP** | Linked from README. |
| `dataset_generator.md` | 174+ | **KEEP** | Cross-linked from algorithms + benchmark. |
| `model_guard.md` | 152 | **KEEP** | Cross-linked from architecture/deployment/scripts. |
| `scripts.md` | 159 | **KEEP** | Operations guide. |
| `web_search.md` | 153 | **KEEP** | Service guide, cross-linked. |
| `markdown_rag_standard.md` | ~65 | **KEEP** | Format spec for `data/iso_documents/`. |
| `multi_standard_assessment_plan_v2.md` | 33 | **PARKED** → [`docs/archive/en/multi_standard_assessment_plan_v2.md`](../archive/en/multi_standard_assessment_plan_v2.md) | Historical planning doc, superseded by current code. |
| `cleanup-plan.md` | (this) | **KEEP-then-PARK** | This plan — archive after execution. |

### 2.5 `docs/vi/` — Vietnamese documentation (19 files)

EN/VI mirror status:
- ✅ Mirrored: `algorithms`, `analytics_monitoring`, `api`, `architecture`, `backup_strategy`, `benchmark`, `case_studies`, `chatbot_rag`, `chromadb_guide`, `dataset_generator`, `deployment`, `iso_assessment_form`, `markdown_rag_standard`, `model_guard`, `multi_standard_assessment_plan_v2`, `scripts`, `web_search`.
- ⚠️ **VI-only (no EN mirror)**: `context.md`, `local_models_api.md`.
- ⚠️ **EN-only**: `cleanup-plan.md` (intentional — internal doc).

| File | Verdict | Reason |
|---|---|---|
| All mirrored VI docs | **KEEP** | One-to-one with EN; user-requested bilingual structure. |
| `docs/vi/context.md` | **DELETED** | Was a stale fork of root [`context.md`](../../context.md:1). Root file is the source of truth. |
| `docs/vi/local_models_api.md` | **KEEP** + EN stub at [`docs/en/local_models_api.md`](local_models_api.md) | Useful reference (Ollama OpenAI compatibility); EN stub links back to full VI doc. |
| `docs/vi/multi_standard_assessment_plan_v2.md` | **PARKED** → [`docs/archive/vi/multi_standard_assessment_plan_v2.md`](../archive/vi/multi_standard_assessment_plan_v2.md) | Same archive treatment as EN counterpart. |

### 2.6 `frontend-next/public/sampleEvidence/README.md`
| Lines | Verdict | Reason |
|---:|---|---|
| 17 | **KEEP** | Explains the synthetic fixtures shipped in [`sampleEvidence.js`](../../frontend-next/src/data/sampleEvidence.js:1). |

### 2.7 `.roo/skills/**/*.md` — Roo IDE skill definitions
**ENTIRELY OFF-LIMITS per user directive.** All files under `.roo/` contain AI model skill definitions and are **never touched** by this cleanup. No audit, no rename, no deletion.

| File group | Verdict |
|---|---|
| Everything under `.roo/` | **DO NOT TOUCH** |
| `.pytest_cache/README.md` | **DELETE** — auto-generated by pytest, should be gitignored. |

---

## 3. Proposed final docs tree

```
README.md                      ← EN entry, ≤140 lines (current)
README_vi.md                   ← VI entry, ≤210 lines (current)
context.md                     ← active plan
docs/
  en/
    architecture.md
    api.md
    deployment.md
    chatbot_rag.md
    chromadb_guide.md
    analytics_monitoring.md
    backup_strategy.md
    iso_assessment_form.md
    algorithms.md
    benchmark.md
    case_studies.md
    dataset_generator.md
    model_guard.md
    scripts.md
    web_search.md
    markdown_rag_standard.md
    local_models_api.md        ← NEW: translate from VI
  vi/
    (mirror of en/, same filenames)
  archive/
    en/multi_standard_assessment_plan_v2.md
    vi/multi_standard_assessment_plan_v2.md
    2026-04-cleanup.md         ← this file moves here when done
data/iso_documents/*.md        ← UNCHANGED (RAG corpus)
data/knowledge_base/dataset_schema.md  ← UNCHANGED
frontend-next/public/sampleEvidence/README.md  ← UNCHANGED
.roo/skills/<active-only>/SKILL.md
```

**Net change**: 0 user-facing docs deleted. 2 stale docs moved to `archive/`. 1 duplicate (`docs/vi/context.md`) deleted. 1 doc translated to EN. Logs untracked from Git (kept on disk).

---

## 4. Execution checklist (waiting for approval)

- [ ] **Step 2 — Git hygiene** (no file deletion on disk):
  - `git rm --cached _bk.log _fe.log backend.log ollama.log`
  - Append to `.gitignore`: `*.log`, `.claude/`, `backend/data/`, `__pycache__/`, `.pytest_cache/`.
  - Decide on `🛡️ .clinerules` (diff first).
- [ ] **Step 3 — Move runtime artifacts**: `git rm --cached backend/data/assessments/*.json` (files stay on disk; future writes go to root `data/assessments/` per existing volume mount).
- [ ] **Step 4 — Code cleanup**:
  - Delete unused [`backend/utils/helpers.py`](../../backend/utils/helpers.py:1) (0 importers).
  - Decide on [`backend/services/document_service.py`](../../backend/services/document_service.py:1) stub (keep, or remove with [`routes/document.py`](../../backend/api/routes/document.py:1) and any frontend caller).
- [ ] **Step 5 — Comment trim**: 2 confirmed targets — [`test_iso27001_routes.py`](../../backend/tests/test_iso27001_routes.py:1) header, [`smoke-detail-drawer.mjs`](../../frontend-next/scripts/smoke-detail-drawer.mjs:1) header. (Other files audited — comments are not bloated.)
- [ ] **Step 6 — Docs consolidation** (per §3):
  - Create `docs/archive/{en,vi}/` and move historical docs.
  - Delete `docs/vi/context.md` (duplicate).
  - Translate `docs/vi/local_models_api.md` → `docs/en/local_models_api.md`. Update README links.
- [ ] **Step 7 — Validation**: pytest + smoke-test must stay green; README links must not 404.

---

## 5. What will NOT be touched

- `data/iso_documents/*.md` (RAG corpus).
- `data/knowledge_base/*` (training data).
- Source `.py` / `.js` / `.css` business logic.
- **Anything under `.roo/`** (skills, settings — entirely off-limits).
- Local `.env`, local `.log` files (only their **Git-tracked status** changes).

---

*End of cleanup plan. Awaiting your sign-off before any `git rm` or file move.*
