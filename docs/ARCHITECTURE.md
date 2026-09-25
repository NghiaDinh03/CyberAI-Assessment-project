# System Architecture Specification

## 1. Overview & Architectural Philosophy

The **CyberAI Assessment Platform** is designed as a secure, on-premise-first pre-audit assessment system. It automates technical gap analysis, evidence correlation, and risk profiling against **ISO/IEC 27001:2022** and **TCVN 11930:2017**.

The architecture adheres to three core design principles:
1. **Data Sovereignty & Air-Gap Compatibility**: Technical evidence (network configurations, firewall rules, server logs, user lists) can be processed 100% locally via on-premise language models (Ollama).
2. **Clear Boundary Separation**:
   - The **Assessment Pipeline** relies strictly on standard catalogues, parsed technical evidence, Fact Cards, and deterministic schema validators.
   - The **Vector Database (ChromaDB)** stores *only* standard definitions, regulatory decrees, and control clauses. Enterprise evidence is **never** vectorized or stored in the vector database.
   - **Web Search** is strictly isolated to the interactive AI Chatbot and is **never** used during assessment scoring.
3. **Audit Reproducibility**: All compliance scores, gap classifications, and export artifacts are derived from an immutable, validated `UnifiedAssessmentResult` object linked to a verifiable Evidence Manifest with SHA-256 integrity hashes.

---

## 2. Multi-Tier Service Topology

```mermaid
flowchart TB
    Client(["👨‍💻 Client Browser<br/>(Desktop / Tablet)"])

    subgraph ReverseProxy["🌐 Ingress Tier"]
        NGINX["Nginx Alpine (:80)<br/>• Reverse Proxy<br/>• Static Asset Caching<br/>• SSE Buffering Disabled"]
    end

    subgraph FrontendApp["🎨 Presentation Tier"]
        NEXT["cyberai-frontend (:3081)<br/>• Next.js 15 (App Router)<br/>• React 18 & CSS Modules<br/>• Client-Side State & Drafts<br/>• Bilingual i18n (EN / VI)"]
    end

    subgraph BackendCore["⚙️ Application Tier"]
        FASTAPI["cyberai-backend (:8000)<br/>• FastAPI (Python 3.11)<br/>• Multi-Agent Pipeline Coordinator<br/>• Evidence Parser & Tesseract OCR<br/>• Fact Extractor & Evidence Mapper<br/>• Artifact Validator & Audit Service"]
    end

    subgraph LocalInference["🦙 Local Inference Tier (Ollama)"]
        EXTRACTOR["Agent 2: Fact Extractor<br/>qwen2.5-coder:7b"]
        AUDITOR["Agent 3: Compliance Auditor<br/>gemma4:latest"]
        EMBED["Agent 1: Embedding Model<br/>bge-m3 (1024-dim)"]
    end

    subgraph SearchTier["🔍 Search Tier"]
        SEARXNG["cyberai-searxng (:8888 / :8080)<br/>Private Meta-Search Engine<br/>(CHATBOT ONLY)"]
    end

    subgraph DataStorage["📁 Persistence & Storage Tier"]
        CHROMA[("ChromaDB Vector Store<br/>/data/vector_store<br/>Standard Clauses & Catalogs")]
        SQL_ASSESS[("SQLite: assessments.db<br/>/data/assessments")]
        SQL_SESS[("SQLite: sessions.db<br/>/data/sessions")]
        SQL_USER[("SQLite: users.db<br/>/data/users")]
        EVID_VOL[("Evidence & Uploads<br/>/data/evidence, /data/uploads")]
        EXP_VOL[("Exported Artifacts<br/>/data/exports (DOCX/XLSX/PDF)")]
    end

    subgraph CloudFallbackTier["☁️ Optional Cloud Gateway"]
        CLOUD_API["Google AI Studio / Gemini 2.0 / OpenClaude<br/>(Secondary fallback if Ollama unavailable)"]
    end

    Client -->|"HTTP :80"| NGINX
    Client -.->|"Direct Dev :3081"| NEXT
    NGINX -->|"Route /"| NEXT
    NGINX -->|"Route /api/*"| FASTAPI
    NEXT -->|"API Calls (/api/*)"| FASTAPI

    FASTAPI -->|"RAG Retrieval (Standard text only)"| CHROMA
    CHROMA -->|"Generate Embeddings"| EMBED
    FASTAPI -->|"Extract Technical Facts"| EXTRACTOR
    FASTAPI -->|"Evaluate Controls & Gaps"| AUDITOR
    FASTAPI -->|"Optional Web Queries"| SEARXNG
    FASTAPI -.->|"API Fallback"| CLOUD_API

    FASTAPI -->|"Save Assessment State"| SQL_ASSESS
    FASTAPI -->|"Session History"| SQL_SESS
    FASTAPI -->|"Authentication & RBAC"| SQL_USER
    FASTAPI -->|"Store Raw Files & Manifest"| EVID_VOL
    FASTAPI -->|"Generate Reports"| EXP_VOL
```

---

## 3. Data Isolation & Privacy Boundaries

### 3.1. Standard Text vs. Enterprise Evidence
| Dimension | Standard Knowledge Base | Uploaded Enterprise Evidence |
|:---|:---|:---|
| **Content** | ISO/IEC 27001:2022 clauses, Annex A descriptions, TCVN 11930:2017 decree requirements | Server configs (`systeminfo`, `sshd_config`), firewall dumps, password policy screenshots, audit logs |
| **Storage Engine** | **ChromaDB Vector Store** (`/data/vector_store`) | **Local Encrypted/Protected Filesystem** (`/data/evidence/`) |
| **Indexing** | Vectorized into semantic chunks via `bge-m3` embedding model | **Never vectorized**. Stored as raw files with SHA-256 hashes |
| **Access in Pipeline** | Retrieved via Cosine similarity to provide regulatory context | Extracted by native parsers / OCR into structured **Security Fact Cards** |

### 3.2. Web Search Strict Isolation
- **SearXNG** is exposed only to the `ChatService` when the user explicitly enables the Web Search toggle in the Chatbot interface.
- Web search query results are annotated with `[Web Search: URL]` citations in the chat stream.
- **The Assessment Pipeline has zero dependency on Web Search**. Neither Agent 2 (Fact Extractor) nor Agent 3 (Compliance Auditor) can trigger external web requests.

---

## 4. Multi-Agent Orchestration Model

The assessment pipeline coordinates 4 specialized functional roles:

```mermaid
sequenceDiagram
    autonumber
    actor User as Security Officer
    participant UI as Next.js Frontend
    participant API as FastAPI Backend
    participant Parser as Native / OCR Parser
    participant Chroma as ChromaDB (Standards)
    participant A1 as Agent 1: bge-m3
    participant A2 as Agent 2: qwen2.5-coder:7b
    participant A3 as Agent 3: gemma4:latest
    participant Val as Unified Validator
    participant Exp as Report Exporters

    User->>UI: Submit Assessment (Scope, Answers, Evidence Files)
    UI->>API: POST /api/iso27001/assess
    API->>API: Initialize Assessment Record (status: processing)
    API-->>UI: Return assessment_id

    loop For each uploaded file
        API->>Parser: Parse text / run Tesseract OCR
        Parser-->>API: Extracted raw text + SHA-256 hash
        API->>A2: Extract structured technical facts
        A2-->>API: Security Fact Cards (OS, Patch, MFA, Firewall...)
    end

    API->>API: Build Evidence Manifest with SHA-256 & Control Mappings

    loop For each Control Group (5-8 controls)
        API->>Chroma: Query standard clauses
        Chroma->>A1: Compute query embedding
        A1-->>Chroma: Dense 1024D vector
        Chroma-->>API: Regulatory standard context
        API->>A3: Prompt with Standard Context + Fact Cards + User Declaration
        A3-->>API: Raw JSON Control Verdicts & Rationales
    end

    API->>Val: Normalize verdicts & validate UnifiedAssessmentResult
    Val->>Val: Enforce 5 Authoritative Verdicts & 10-5-3-1 Math
    Val-->>API: Validated Unified Result

    API->>Exp: Generate DOCX, SoA XLSX, Risk Register XLSX, PDF
    Exp-->>API: Persisted Artifacts
    API->>API: Save to SQLite (status: completed)
    UI->>API: Poll / stream status
    API-->>UI: Complete Assessment Result & Audit Trace
```

---

## 5. Persistence Architecture

### 5.1. Relational & Key-Value Storage (SQLite in WAL Mode)
- **`assessments.db`**: Stores assessment metadata, progress percentage, execution logs, and complete serialized `UnifiedAssessmentResult` JSON bodies.
- **`sessions.db`**: Stores chatbot conversation sessions and message histories.
- **`users.db`**: Stores credentials hashed with salted PBKDF2/SHA-256 and RBAC role assignments (`ADMIN`, `AUDITOR`).

### 5.2. File-Based Storage
- `/data/evidence/`: Ingested technical evidence files organized by assessment ID.
- `/data/exports/`: Generated DOCX reports, Statement of Applicability Excel files, Risk Register workbooks, and PDF documents.
- `/data/vector_store/`: Persistent ChromaDB index for standard regulatory texts.

---

## 6. Security & Hardening Architecture

1. **Authentication**: JWT tokens signed using HMAC-SHA256 with mandatory minimum 32-character secret length (`JWT_SECRET`).
2. **CORS Enforcement**: Whitelist restricts requests to configured local and internal host origins.
3. **Rate Limiting**: In-memory token bucket rate limiters prevent API abuse on chat, assessment, and benchmark endpoints.
4. **Prompt Injection Defense**: Input sanitization blocks prompt-injection patterns (`ignore previous instructions`, `act as`, system prompt overrides).
5. **Conflict Resolution Fallback**: When an irreconcilable conflict between self-declaration and evidence is detected, the pipeline automatically forces the control to `needs_expert_review` (factor 0.0), logging a safety fallback event in the Audit Trace.
