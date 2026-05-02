# CyberAI Assessment Platform — Migration Plan

> **Updated:** 2026-05-02  
> **Goal:** Merge CyberAI's features into Vane's UI framework, rebrand as "CyberAI Assessment Platform"

---

## ✅ Completed

### Phase 1: Rebrand Vane → CyberAI
- [x] `layout.tsx`: title → "CyberAI Assessment Platform", font → Inter
- [x] `Sidebar.tsx`: added all CyberAI nav items (AI Chat, Assessment, Standards, Templates, Analytics, Discover, Library)
- [x] `globals.css`: added CyberAI page-container, card, grid, status-badge utilities
- [x] `tsconfig.json`: added `.js`/`.jsx` support
- [x] `LanguageProvider.js`: i18n support for CyberAI pages
- [x] `chatbot/page.tsx`: wraps Vane's ChatWindow

### Phase 2: Port CyberAI Pages
- [x] `/assessment` — ISO 27001 assessment form (ported from `form-iso`)
- [x] `/standards` — Standards library with upload/validate
- [x] `/analytics` — Dashboard, service status, benchmark, ChromaDB
- [x] `/templates` — Assessment templates with evidence
- [x] `/settings` — Language, assessment mode, docs library
- [x] `/settings/guide` — Full assessment guide
- [x] `/settings/prompts/chat` — Chat prompt manager
- [x] `/settings/prompts/assessment` — Assessment prompt manager

### Phase 3: Data Layer & Components
- [x] `src/data/` — standards, controlDescriptions, templates, sampleEvidence
- [x] `src/i18n/` — en.json, vi.json
- [x] `src/lib/api.js` — API client
- [x] Components: Toast, Skeleton, SystemStats, MarkdownRenderer, StepProgress, EvidenceLibrary, PromptManager

### Phase 4: Docker Integration
- [x] `docker-compose.yaml`: integrated full CyberAI stack (frontend, backend, localai, ollama)
- [x] `next.config.mjs`: API proxy rewrites for CyberAI backend
- [x] `package.json`: name → "cyberai-assessment"

---

## 🔄 In Progress

### Phase 5: Final Branding
- [ ] Rename `Vane/` folder → `cyberai-frontend/`
- [ ] Update all Docker references
- [ ] Update README

### Phase 6: Verification
- [ ] Build test: `docker compose up -d --build`
- [ ] Verify all pages load correctly
- [ ] Verify API proxy works

---

## Architecture (Post-Merge)

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
│   │   └── ...                    # Other ported components
│   ├── data/                      # CyberAI data layer (ported)
│   ├── i18n/                      # Translation files (ported)
│   └── lib/                       # Vane's lib + api.js (ported)
├── docker-compose.yaml
└── Dockerfile
```

## Docker Services

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| cyberai-frontend | cyberai-frontend | 3001 | Next.js frontend (formerly Vane) |
| cyberai-backend | cyberai-backend | 8000 | FastAPI backend |
| cyberai-localai | cyberai-localai | 8080 | Local LLM engine |
| cyberai-ollama | cyberai-ollama | 11434 | Ollama LLM runner |

## Key Design Decisions

1. **Vane's chat engine kept as-is** — superior streaming, multi-model, web search
2. **CyberAI pages ported as-is** — CSS Modules coexist with Tailwind
3. **Sidebar is Vane's** — customized with CyberAI nav items
4. **LanguageProvider is new** — needed for CyberAI's i18n
5. **API proxy in next.config.mjs** — routes CyberAI API calls to backend
