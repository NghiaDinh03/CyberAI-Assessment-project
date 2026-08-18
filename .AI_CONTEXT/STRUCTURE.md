# STRUCTURE.md — Cấu Trúc Project CyberAI

> **Cập nhật:** 2026-07-08  
> **Quy tắc:** Luôn update file này khi thay đổi cấu trúc project.

---

## Root

```
CyberAI-Assessment-project/
├── .env.example             # Template biến môi trường
├── .gitignore
├── docker-compose.yml       # Dev environment
├── docker-compose.prod.yml  # Production environment
├── README.md                # Docs tiếng Anh
├── README_vi.md             # Docs tiếng Việt
│
├── .AI_CONTEXT/             # Quy tắc, tài liệu, cấu hình và bộ nhớ cho AI (Centralized)
│   ├── MEMORY.md            # Append-only memory (KHÔNG XÓA)
│   ├── STRUCTURE.md         # File này
│   ├── CODING_GUIDELINES.md # Quy tắc coding + tự tranh luận
│   ├── MASTER_PROMPT.md     # Prompt mẫu cho AI session
│   ├── core_features_plan.md
│   ├── feedback_update.md
│   ├── karpathy_guidelines.md
│   ├── subtask.md
│   ├── context.md           # Context phân tích tích hợp toolkit (historical)
│   ├── .clinerules          # Quy tắc RTK của Cline (di chuyển từ gốc)
│   ├── .agents/             # Cấu hình quy tắc của Roo Code/Claude Code (di chuyển từ gốc)
│   ├── .roo/                # Cấu hình và kỹ năng của Roo Code (di chuyển từ gốc)
│   ├── .claude/             # Cấu hình của Claude Code (di chuyển từ gốc)
│   ├── logs/                # Thư mục chứa các file log thu gom được
│   └── temp-karpathy-skills/ # Thư mục kỹ năng tham khảo Karpathy (không dùng trực tiếp)
│
├── backend/                 # FastAPI backend (Python 3.11)
│   ├── Dockerfile
│   ├── main.py              # Entry point
│   ├── requirements.txt
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py          # Chat AI endpoints
│   │   │   ├── document.py      # Document upload/parse
│   │   │   ├── iso27001.py      # Assessment endpoints
│   │   │   ├── health.py        # Health check
│   │   │   ├── metrics.py       # Prometheus metrics
│   │   │   ├── ollama.py        # Ollama management
│   │   │   ├── prompts.py       # Prompt management
│   │   │   ├── risks.py         # Risk register
│   │   │   ├── standards.py     # Custom standards
│   │   │   ├── system.py        # System info
│   │   │   ├── templates.py     # Templates
│   │   │   └── web_search.py    # Web search
│   │   └── schemas/
│   │       ├── chat.py
│   │       ├── document.py
│   │       └── risk.py
│   │
│   ├── core/
│   │   ├── config.py        # Settings + env validation
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── limiter.py       # Rate limiting
│   │
│   ├── prompts/
│   │   ├── defaults.py      # Default system prompts
│   │   └── store.py         # Prompt storage
│   │
│   ├── repositories/
│   │   ├── session_store.py # Session management
│   │   └── vector_store.py  # ChromaDB (legacy, đang bỏ)
│   │
│   ├── services/
│   │   ├── assessment_helpers.py    # Assessment pipeline helpers
│   │   ├── chat_service.py          # Chat orchestrator
│   │   ├── cloud_llm_service.py     # LLM calls (Ollama, Cloud)
│   │   ├── controls_catalog.py      # ISO/TCVN control definitions
│   │   ├── document_service.py      # Document processing
│   │   ├── model_guard.py           # Model health checks
│   │   ├── model_router.py          # Intent classification + routing
│   │   ├── rag_service.py           # RAG (legacy, đang bỏ)
│   │   ├── ram_guard.py             # RAM monitoring
│   │   ├── risk_register_service.py # Risk register CRUD
│   │   ├── soa_exporter.py          # SoA .xlsx export
│   │   ├── standard_service.py      # Custom standards
│   │   ├── template_evidence_store.py
│   │   ├── web_search.py            # DuckDuckGo/SearXNG
│   │   ├── privacy_filter.py        # PII stripping (Phase 10A)
│   │   ├── evidence_mapper.py       # Evidence → control mapping (Phase 10A)
│   │   │
│   │   └── document_ingest/
│   │       ├── base.py          # Parser registry
│   │       ├── chunker.py       # Text chunking
│   │       ├── docx_parser.py   # DOCX parser
│   │       ├── indexer.py       # ChromaDB indexing
│   │       ├── ocr_parser.py    # OCR parser — Tesseract (Phase 10A)
│   │       ├── pdf_parser.py    # PDF parser + OCR fallback
│   │       ├── storage.py       # File storage
│   │       ├── text_parser.py   # Text parser
│   │       └── xlsx_parser.py   # XLSX parser
│   │
│   ├── tests/
│   │   ├── test_assessment_helpers.py
│   │   ├── test_chat_service.py
│   │   ├── test_document_ingest.py
│   │   ├── test_e2e_assessment.py   # E2E integration (Phase 10D)
│   │   ├── test_iso27001_routes.py
│   │   ├── test_prompts.py
│   │   ├── test_rag_service.py
│   │   ├── test_risk_register.py
│   │   ├── test_soa_exporter.py
│   │   └── test_template_evidence.py
│   │
│   └── utils/
│       ├── helpers.py
│       └── logger.py
│
├── data/
│   ├── assessments/         # Assessment JSON files
│   ├── evidence/            # Uploaded evidence files
│   ├── exports/             # Generated reports
│   ├── iso_documents/       # ISO/TCVN reference docs (.md)
│   ├── knowledge_base/      # Control data JSONs
│   │   ├── benchmark_iso27001.json
│   │   ├── controls.json
│   │   ├── iso27001.json
│   │   ├── sample_training_pairs.jsonl
│   │   └── tcvn14423.json
│   ├── risks/               # Risk register data
│   ├── sessions/            # Chat sessions
│   ├── standards/           # Custom standards
│   ├── template_evidence/
│   ├── translations/
│   ├── uploads/
│   └── vector_store/        # ChromaDB data
│
├── docs/
│   ├── en/                  # English docs
│   ├── vi/                  # Vietnamese docs
│   └── archive/             # Old plans
│
├── frontend-next/           # Next.js frontend
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   │
│   ├── public/
│   │   └── sampleEvidence/  # Sample evidence files
│   │
│   └── src/
│       ├── app/
│       │   ├── layout.js
│       │   ├── page.js          # Home page
│       │   ├── analytics/       # Analytics page
│       │   ├── chatbot/         # Chatbot page
│       │   ├── form-iso/        # Assessment form
│       │   │   └── _components/
│       │   │       ├── ControlRow.js
│       │   │       ├── DetailDrawer.js
│       │   │       ├── EvidencePreviewModal.js
│       │   │       └── EvidenceThumb.js
│       │   ├── landing/         # Landing page
│       │   ├── settings/        # Settings
│       │   └── standards/       # Standards page
│       │
│       ├── components/
│       │   ├── EvidenceLibrary.js
│       │   ├── LanguageProvider.js
│       │   ├── MarkdownRenderer.js
│       │   ├── Navbar.js
│       │   ├── PromptManager.js
│       │   ├── StepProgress.js
│       │   ├── SystemStats.js
│       │   ├── ThemeProvider.js
│       │   └── Toast.js
│       │
│       ├── data/
│       │   ├── controlDescriptions.js
│       │   ├── controlDescriptions.en.js
│       │   ├── controlDescriptions.vi.js
│       │   ├── sampleEvidence.js
│       │   ├── standards.js
│       │   ├── templates.js
│       │   ├── templates.en.js
│       │   └── templates.vi.js
│       │
│       ├── i18n/
│       │   ├── en.json
│       │   ├── vi.json
│       │   └── index.js
│       │
│       └── lib/
│           └── api.js       # API client
│
├── nginx/
│   └── nginx.conf
│
└── scripts/
```

---

## Key Dependencies

### Backend (Python)
- **Framework:** FastAPI
- **LLM:** Ollama (local), DeepSeek/Google AI/OpenAI (cloud)
- **Document parsing:** pypdf, python-docx, openpyxl
- **OCR:** pytesseract + pdf2image (planned)
- **Export:** openpyxl (XLSX), python-docx (DOCX), weasyprint (PDF)

### Frontend (JavaScript)
- **Framework:** Next.js 16
- **UI:** CSS Modules
- **State:** React hooks
- **API:** fetch + SSE for streaming

### Infrastructure
- **Container:** Docker + docker-compose
- **Reverse proxy:** Nginx
- **Monitoring:** Prometheus metrics, Sentry
