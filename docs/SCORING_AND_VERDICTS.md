# Scoring and Verdicts Specification

## 1. Authoritative Verdict Framework

The CyberAI Assessment Platform strictly adheres to **5 standardized verdicts**. No other verdicts are permitted in the calculation engine or output reporting.

| Verdict | Factor ($v_f$) | Mathematical Definition | Compliance Contribution |
|:---|:---:|:---|:---:|
| `satisfied` | **1.0** | Technical evidence comprehensively verifies all control requirements. | $w_i \times 1.0$ (100% of control weight) |
| `partial` | **0.5** | Evidence demonstrates substantial but incomplete implementation. | $w_i \times 0.5$ (50% of control weight) |
| `not_evidenced` | **0.0** | Control declared implemented, but technical evidence is absent or unverified. | $w_i \times 0.0 = 0.0$ |
| `missing` | **0.0** | Control is not implemented and no evidence is attached. | $w_i \times 0.0 = 0.0$ |
| `needs_expert_review` | **0.0** | A conflict is detected between declaration and evidence, or file is unparseable. | $w_i \times 0.0 = 0.0$ (Pending manual auditor review) |

### 1.1. Elimination of `not_applicable` (N/A)
> [!IMPORTANT]
> The `not_applicable` (N/A) verdict is **completely eliminated** from the active scoring engine.
> - No control can be excluded from the compliance denominator.
> - The denominator remains fixed at the full catalogue weight ($495.0$ for ISO 27001; $271.0$ for TCVN 11930).
> - **Historical Data Handling**: If an imported legacy record contains a `not_applicable` verdict, the normalization layer automatically maps it to `needs_expert_review` ($v_f = 0.0$). The control remains in the scoring scope and denominator.

---

## 2. Weighted Compliance Specification (10-5-3-1 Scheme)

### 2.1. Weight Level Values
Each control is assigned a server-side weight corresponding to its operational risk criticality:

| Weight Level | Numeric Weight ($w_i$) | Architectural Significance |
|:---|:---:|:---|
| **Critical** | **10.0** | Core foundational security controls (IAM, Access Control, Anti-Malware, Encryption, Incident Response, Backup). Absence creates immediate catastrophic risk. |
| **High** | **5.0** | Key operational and structural controls (Network Segregation, Asset Inventory, Patch Management, Change Management). |
| **Medium** | **3.0** | Standard security practices (Threat Intelligence, Capacity Planning, Secure Coding). |
| **Low** | **1.0** | Good-to-have auxiliary controls (NTP clock synchronization, clean desk/clean screen). |

### 2.2. Weighted Compliance Formula
$$\text{Weighted Compliance (\%)} = \frac{\sum_{i=1}^{N} (w_i \times v_{f, i})}{\sum_{i=1}^{N} w_i} \times 100\%$$

Where:
- $N$ is the total number of controls defined in the catalogue.
- $w_i \in \{10.0, 5.0, 3.0, 1.0\}$.
- $v_{f, i} \in \{1.0, 0.5, 0.0\}$.
- AI model confidence scores are **purely informational metadata** and are **never** multiplied into the score.
- Per-control score contributions are computed as:
  $$\text{contribution}_i = \text{round}(w_i \times v_{f, i}, 1)$$
- The final percentage is clamped to $[0.0, 100.0]$ and rounded to 1 decimal place.

### 2.3. Mathematical Invariants

| Standard | Total Controls ($N$) | Denominator ($\sum w_{\text{catalogue}}$) | Invariant Status |
|:---|:---:|:---:|:---|
| **ISO/IEC 27001:2022** | **93 controls** | **495.0 points** | **Strict Invariant** — Never 494, 490, or 92 controls |
| **TCVN 11930:2017** | **34 controls** | **271.0 points** | **Strict Invariant** — Never reduced |

#### Verification Proof for ISO/IEC 27001:2022 (93 controls):
- **A.5 Organizational** (37 controls):
  - 10 Critical ($10 \times 10 = 100$)
  - 13 High ($13 \times 5 = 65$)
  - 12 Medium ($12 \times 3 = 36$)
  - 2 Low ($2 \times 1 = 2$)
  - *Subtotal A.5*: $100 + 65 + 36 + 2 = \mathbf{203.0}$
- **A.6 People** (8 controls):
  - 1 Critical ($1 \times 10 = 10$)
  - 5 High ($5 \times 5 = 25$)
  - 2 Medium ($2 \times 3 = 6$)
  - 0 Low
  - *Subtotal A.6*: $10 + 25 + 6 = \mathbf{41.0}$
- **A.7 Physical** (14 controls):
  - 0 Critical
  - 6 High ($6 \times 5 = 30$)
  - 6 Medium ($6 \times 3 = 18$)
  - 2 Low ($2 \times 1 = 2$)
  - *Subtotal A.7*: $30 + 18 + 2 = \mathbf{50.0}$
- **A.8 Technological** (34 controls):
  - 12 Critical ($12 \times 10 = 120$)
  - 12 High ($12 \times 5 = 60$)
  - 9 Medium ($9 \times 3 = 27$)
  - 1 Low ($1 \times 1 = 1$)
  - *Subtotal A.8*: $120 + 60 + 27 + 1 = \mathbf{208.0}$

$$\text{Total ISO Max Score} = 203.0 + 41.0 + 50.0 + 208.0 = \mathbf{495.0}$$

#### Verification Proof for TCVN 11930:2017 (34 controls):
- **1. Mạng (NW)** (8 controls): 4 Critical (40), 3 High (15), 1 Medium (3) = **58.0**
- **2. Máy chủ (SV)** (8 controls): 7 Critical (70), 1 High (5) = **75.0**
- **3. Ứng dụng (APP)** (7 controls): 4 Critical (40), 3 High (15) = **55.0**
- **4. Dữ liệu (DAT)** (6 controls): 4 Critical (40), 1 High (5), 1 Medium (3) = **48.0**
- **5. Quản lý Vận hành (MNG)** (5 controls): 3 Critical (30), 2 High (10) = **40.0**

$$\text{Total TCVN Max Score} = 58.0 + 75.0 + 55.0 + 48.0 + 40.0 = \mathbf{271.0}$$

---

## 3. Raw Coverage vs. Weighted Compliance

The platform strictly separates the **Self-Declared Metric** from the **Audited Compliance Metric**:

| Property | Raw Coverage | Weighted Compliance |
|:---|:---|:---|
| **Formula** | $\frac{\text{self\_declared\_implemented}}{\text{total\_controls}} \times 100\%$ | $\frac{\sum (w_i \times v_{f, i})}{\sum w_{\text{catalogue}}} \times 100\%$ |
| **Basis** | User checklist declarations in Step 3 | Technical evidence verified by AI Auditor & Fact Cards |
| **Meaning** | Initial organizational self-assessment estimate | Objective, audit-traceable technical readiness |
| **Effect of Uploading a File** | None (does not alter self-declaration count) | Enables technical analysis to assign `satisfied` or `partial` |
| **Zero Evidence State** | Can be high (e.g. 50% if user ticks half the checklist) | **Strictly 0.0%** (all unverified controls get factor 0.0) |
| **Audit Status** | Preliminary self-declaration | Authoritative pre-audit result |

---

## 4. 4×4 Risk Matrix Specification

For identified gaps (controls with verdicts `missing`, `not_evidenced`, or `needs_expert_review`), the platform computes risk metrics on a **$4 \times 4$ Risk Heatmap**:

### 4.1. Scales
- **Likelihood ($L$)**: $1$ (Unlikely), $2$ (Possible), $3$ (Likely), $4$ (Almost Certain).
- **Impact ($I$)**: $1$ (Low), $2$ (Medium), $3$ (High), $4$ (Critical).
- **Risk Score ($R$)**:
  $$R = L \times I \quad (1 \le R \le 16)$$

### 4.2. Risk Severity Categorization
| Risk Score ($R$) | Severity Level | Priority Band | Target Remediation Timeline |
|:---:|:---:|:---:|:---|
| **$12 - 16$** | **Critical** (🔴) | **P0** | Immediate (within 14 days) |
| **$8 - 11$** | **High** (🟠) | **P1** | High priority (within 30 days) |
| **$4 - 7$** | **Medium** (🟡) | **P2** | Medium priority (within 60 days) |
| **$1 - 3$** | **Low** (⚪) | **P3** | Low priority (within 90 days) |

### 4.3. Schema Invariants
- Pydantic models in `assessment_schema.py` strictly validate that $1 \le L \le 4$, $1 \le I \le 4$, and $R = L \times I \le 16$.
- Any legacy $5 \times 5$ payloads ($R > 16$) are flagged with `is_legacy = True` and surfaced with a legacy warning banner in the UI.
