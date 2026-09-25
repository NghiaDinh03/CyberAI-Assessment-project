# Assessment Workflow Specification

## 1. End-to-End Pipeline Overview

The assessment workflow transforms raw organizational inputs and technical evidence into an authoritative, verifiable compliance evaluation.

```mermaid
flowchart TD
    S1["1. User Input & Self-Declaration<br/>(Scope, Infrastructure, Controls Checklist)"]
    S2["2. Technical Evidence Upload<br/>(PDF, PNG/JPG, TXT, LOG, CONF)"]
    S3["3. Text Extraction & OCR<br/>(Native file parser + Tesseract OCR)"]
    S4["4. Fact Extraction & Manifest<br/>(Agent 2 qwen2.5-coder:7b -> Fact Cards & SHA-256 Manifest)"]
    S5["5. Evidence-to-Control Mapping<br/>(Filename pattern + content keyword mapping)"]
    S6["6. Standards RAG Context<br/>(ChromaDB bge-m3 retrieval of Standard Clauses)"]
    S7["7. Chunked Compliance Assessment<br/>(Agent 3 gemma4:latest per 5-8 control group)"]
    S8["8. Verdict Normalization & Validation<br/>(UnifiedAssessmentResult Pydantic schema validation)"]
    S9["9. Dual Metric Computation<br/>(Raw Coverage vs Weighted Compliance)"]
    S10["10. Audit Trace & Artefact Generation<br/>(Audit Trace, SoA XLSX, Risk Register XLSX, DOCX, PDF)"]
    S11["11. Expert Post-Review<br/>(Manual review for controls marked needs_expert_review)"]

    S1 Quad --> S2
    S1 --> S5
    S2 --> S3
    S3 --> S4
    S4 --> S5
    S5 --> S7
    S6 --> S7
    S7 --> S8
    S8 --> S9
    S9 --> S10
    S10 --> S11
```

---

## 2. Detailed Stage Breakdown

### Stage 1: User Input & Self-Declaration
- **Step 1 — Scope & Organization**: The user selects the standard (`iso27001` or `tcvn11930`), organization name, industry, size, and assessment boundary (Organization-wide, Specific Department, or Targeted System).
- **Step 2 — Infrastructure Profile**: Information regarding servers, firewalls, AV/EDR, SIEM, backup solutions, cloud environments, and historical incidents is recorded.
- **Step 3 — Controls Checklist**: The user ticks controls they declare are implemented within their organization. This count forms the basis for the **Raw Coverage** index.
- **Step 4 — Review & Execution Mode**: The user reviews their draft, optionally provides topology notes, and selects the inference execution mode (`local`, `hybrid`, or `cloud`).

### Stage 2 & 3: Evidence Ingestion, Parsing & OCR
When technical files are uploaded:
1. **File Type Detection**: Files are categorized by extension (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.txt`, `.log`, `.conf`, `.ini`, `.json`, `.csv`).
2. **Text Parsing**:
   - Native plain text parsers handle `.txt`, `.log`, `.conf`, and `.ini`.
   - Native PDF parsers extract embedded text streams.
   - For image files or scanned PDFs, **Tesseract OCR** (`tesseract-ocr`, `tesseract-ocr-vie`, `tesseract-ocr-eng`) extracts Vietnamese and English text.
3. **Integrity Hashing**: A cryptographic **SHA-256** checksum is computed immediately upon receipt.
   > [!NOTE]
   > The SHA-256 hash guarantees **file integrity** (the file has not been altered or corrupted). It does **not** certify the factual correctness or security adequacy of the file's contents.

### Stage 4: Fact Extraction & Evidence Manifest
1. **Agent 2 (`qwen2.5-coder:7b`)** analyzes extracted text and structures technical parameters into standardized **Security Fact Cards**:
   - Operating system and patch levels
   - Firewall rule baselines and network zoning
   - Identity and Access Management (MFA, PAM policies)
   - Antivirus / EDR deployment status
   - Backup schedules and retention policies
2. An **Evidence Manifest** item is created containing:
   - `file_id`: Unique identifier
   - `sha256`: Cryptographic checksum
   - `parser_or_ocr`: Parser method used (`native_parser`, `tesseract_ocr`)
   - `mapped_controls`: Associated control candidate IDs
   - `ingestion_status`: `ingested` or `excluded` (with `exclusion_reason`)

### Stage 5: Evidence-to-Control Mapping
The `evidence_mapper` module inspects file naming patterns and content keywords to map evidence to applicable controls in ISO 27001:2022 (e.g., `A.5.15`, `A.8.20`) or TCVN 11930:2017 (e.g., `NW.02`, `SV.02`).
- A single physical evidence file may map to multiple control IDs (e.g., a firewall configuration maps to both `A.8.20 Network Security` and `A.8.22 Network Segregation`).
- No physical duplication of the file occurs; only references are mapped.

### Stage 6: Regulatory Standards RAG Retrieval
- ChromaDB is queried using cosine similarity via the `bge-m3` embedding model.
- **What is retrieved**: Official requirements, implementation guidance, and audit objectives from the standard catalogue for the target control group.
- **What is NOT in ChromaDB**: Enterprise evidence is **never** vectorized or stored in ChromaDB.

### Stage 7: Chunked Compliance Assessment
Because assessing 93 controls simultaneously would exceed the model's context window, controls are divided into chunks of **5 to 8 controls** per prompt (`build_chunk_prompt`):
- **Agent 3 (`gemma4:latest`)** receives:
  - Standard reference text (from ChromaDB)
  - Extracted Security Fact Cards / Evidence snippets
  - User self-declaration status (`implemented` / `not_implemented`)
- The model outputs structured JSON evaluating each control with:
  - `evidence_verdict`
  - `confidence` (clamped to $[0.0, 1.0]$, metadata only)
  - `missing_items`
  - `verdict_rationale`
  - `evidence_citations`

### Stage 8: Normalization & Pydantic Validation
The raw LLM output is passed to `normalize_verdict` and the Pydantic model `UnifiedAssessmentResult`:
1. **Verdict Normalization**: Aliases (`compliant`, `pass`, `fail`) are strictly converted into one of the **5 Authoritative Verdicts**:
   - `satisfied`
   - `partial`
   - `not_evidenced`
   - `missing`
   - `needs_expert_review`
2. **Conflict Enforcement**: If a user declared a control implemented but the evidence directly contradicts it, the control is automatically forced to:
   - `assessment_verdict`: `needs_expert_review`
   - `verdict_source`: `safe_fallback_conflict`
   - `verdict_factor`: `0.0`
3. **Safety Fallback**: If an LLM fails or produces unparseable JSON, deterministic rule-based fallbacks assign `needs_expert_review` or `missing`, guaranteeing 100% pipeline completion.

### Stage 9: Dual Metric Computation
The validated result computes two completely separated indices:
1. **Raw Coverage**:
   $$\text{Raw Coverage} = \frac{\text{self\_declared\_implemented}}{\text{total\_applicable\_controls}} \times 100\%$$
   *(Purely self-declared; does not imply verified compliance).*
2. **Weighted Compliance**:
   $$\text{Weighted Compliance} = \frac{\sum (w_i \times \text{verdict\_factor}_i)}{\sum w_{\text{catalogue}}} \times 100\%$$
   *(Driven strictly by final technical verdicts; 495.0 max for ISO, 271.0 max for TCVN).*

### Stage 10: Audit Trace & Artefact Generation
A single validated `UnifiedAssessmentResult` generates:
- **`audit_trace.json`**: Machine-readable log containing step-by-step evidence mapping, prompts, raw model responses, fallbacks, and citation chains.
- **Statement of Applicability (SoA)**: Excel workbook (`.xlsx`) documenting applicability, justification, and verified status for all controls.
- **Risk Register**: Excel workbook (`.xlsx`) detailing identified gaps mapped to a $4 \times 4$ Risk Matrix ($L \times I \in [1, 16]$) and prioritized into P0, P1, P2 remediation plans.
- **Executive Summary DOCX**: A4 formatted Word document ready for stakeholder presentation.
- **Audit Report PDF**: Rendered printable report.

### Stage 11: Human Expert Review
Controls assigned the `needs_expert_review` verdict are surfaced in the UI with a dedicated warning badge. An accredited auditor or senior security analyst reviews the audit trace, inspects the attached evidence, and makes the final determination before official audit filing.

---

## 3. Strict Assessment Invariants Summary

| Item | Architectural Guarantee |
|:---|:---|
| **Authoritative Verdicts** | Exactly 5: `satisfied`, `partial`, `not_evidenced`, `missing`, `needs_expert_review`. |
| **No Denominator Reduction** | All 93 ISO controls (495 pts) and all 34 TCVN controls (271 pts) remain in the denominator. N/A is never excluded. |
| **Web Search** | Strictly isolated to Chatbot. Never called in assessment. |
| **Evidence Privacy** | Parsed in local container memory / disk. Never placed into shared vector stores. |
| **Advisory Nature** | Tool provides pre-audit gap analysis; it does not replace accredited third-party certification bodies. |
