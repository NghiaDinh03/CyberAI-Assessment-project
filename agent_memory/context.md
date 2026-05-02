# CyberAI Assessment Platform — Context & Technology

> **Date:** 2026-05-02  
> **Purpose:** Full context for the Vane → CyberAI frontend migration.

---

## 1. Project Overview

### 1.1 CyberAI Assessment (Current)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | ISO 27001 compliance assessment chatbot with RAG, AI support |
| **Frontend** | Next.js 15 (React 19), CSS Modules, `lucide-react`, `react-markdown` |
| **Backend** | FastAPI (Python 3.11+), Uvicorn |
| **Vector Store** | ChromaDB (PersistentClient, cosine similarity) |
| **LLM Providers** | Open Claude (cloud), LocalAI (local GGUF), Ollama (local) |
| **Database** | ChromaDB (vector), JSON files (sessions, risks, standards) |
| **Web Search** | DuckDuckGo (`duckduckgo-search`) |
| **Auth** | JWT (basic, optional) |
| **Rate Limit** | slowapi |
| **Metrics** | Prometheus client |
| **Container** | Docker Compose (5 services: backend, frontend, localai, ollama, nginx) |
| **Languages** | Vietnamese + English (i18n) |

### 1.2 Vane (Source for Frontend Merge)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | AI-powered answering engine with web search, media, widgets |
| **Frontend** | Next.js 16 (React 18), Tailwind CSS, TypeScript |
| **Chat Engine** | Streaming SSE, multi-model providers, file uploads, web search |
| **Features** | Chat history, discover/news, library, settings, weather, stocks |
| **Container** | Docker Compose (1 service: vane + SearXNG) |

---

## 2. Migration Status

### ✅ Phase 1: Rebrand Vane → CyberAI (DONE)
- [x] Updated `layout.tsx`: title → "CyberAI Assessment Platform", font → Inter
- [x] Updated `Sidebar.tsx`: added all CyberAI nav items (AI Chat, Assessment, Standards, Templates, Analytics)
- [x] Updated `globals.css`: added CyberAI page-container, card, grid utilities
- [x] Updated `tsconfig.json`: added `.js`/`.jsx` support
- [x] Created `LanguageProvider.js`: i18n support for CyberAI pages
- [x] Created `chatbot/page.tsx`: wraps Vane's ChatWindow

### ✅ Phase 2: Port CyberAI Pages (DONE)
- [x] `/assessment` — ISO 27001 assessment form (ported from `form-iso`)
- [x] `/standards` — Standards library with upload/validate
- [x] `/analytics` — Dashboard, service status, benchmark, ChromaDB
- [x] `/templates` — Assessment templates with evidence
- [x] `/settings` — Language, assessment mode, docs library
- [x] `/settings/guide` — Full assessment guide
- [x] `/settings/prompts/chat` — Chat prompt manager
- [x] `/settings/prompts/assessment` — Assessment prompt manager

### ✅ Data Layer Ported
- [x] `src/data/standards.js` — Assessment standards + scoring
- [x] `src/data/controlDescriptions.js` — Control descriptions (en/vi)
- [x] `src/data/templates.js` — Assessment templates (en/vi)
- [x] `src/data/sampleEvidence.js` — Sample evidence files
- [x] `src/data/index.js` — Data hooks
- [x] `src/i18n/en.json` + `vi.json` — Translation files
- [x] `src/lib/api.js` — API client functions

### ✅ Components Ported
- [x] Toast.js — Toast notifications
- [x] Skeleton.js — Loading skeletons
- [x] SystemStats.js — System statistics display
- [x] MarkdownRenderer.js — Markdown rendering
- [x] StepProgress.js — Step progress indicator
- [x] EvidenceLibrary.js — Evidence library component
- [x] PromptManager.js — Prompt management

### 🔄 Phase 3: Remaining (PENDING)
- [ ] Install `react-markdown` + `remark-gfm` in Vane
- [ ] Build test & fix any import errors
- [ ] Update `package.json` name → "cyberai-assessment"

### 🔄 Phase 4: Final Branding (PENDING)
- [ ] Rename `Vane/` folder → `cyberai-frontend/`
- [ ] Update all Docker references
- [ ] Update README

---

## 3. Architecture (Post-Merge)

```
cyberai-frontend/          # Formerly Vane/
├── src/
│   ├── app/
│   │   ├── page.tsx               # Home → ChatWindow (Vane's chat engine)
│   │   ├── chatbot/page.tsx       # AI Chat page
│   │   ├── assessment/            # ISO 27001 assessment (ported)
│   │   ├── standards/             # Standards library (ported)
│   │   ├── analytics/             # Dashboard + benchmark (ported)
│   │   ├── templates/             # Assessment templates (ported)
│   │   ├── settings/              # Settings + guide (ported)
│   │   ├── discover/              # News discover (Vane original)
│   │   ├── library/               # Chat library (Vane original)
│   │   ├── c/[chatId]/            # Chat sessions (Vane original)
│   │   └── api/                   # Vane's API routes
│   ├── components/
│   │   ├── ChatWindow.tsx         # Vane's chat engine
│   │   ├── Sidebar.tsx            # Merged sidebar
│   │   ├── LanguageProvider.js    # i18n (ported)
│   │   ├── Toast.js               # Toast (ported)
│   │   └── ...                    # Other ported components
│   ├── data/                      # CyberAI data layer (ported)
│   ├── i18n/                      # Translation files (ported)
│   └── lib/                       # Vane's lib + api.js (ported)
├── docker-compose.yaml
└── Dockerfile
```

---

## 4. Key Design Decisions

1. **Vane's chat engine is kept as-is** — it's superior to CyberAI's chatbot with streaming, multi-model, web search, file uploads
2. **CyberAI pages are ported as-is** — they use CSS Modules which coexist with Vane's Tailwind
3. **Sidebar is Vane's** — customized with CyberAI nav items, keeping Vane's clean vertical icon layout
4. **LanguageProvider is new** — needed for CyberAI's i18n; Vane uses its own config system
5. **Vane's Settings page is kept** — CyberAI's settings page is added as a separate route
