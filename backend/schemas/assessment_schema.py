"""Unified Assessment Schema — Standardized contract across JSON, Audit Trace, SoA, Risk Register, DOCX, and PDF."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ControlItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    control_id: str
    label: str = ""
    category: str = ""
    weight: str = "medium"  # critical, high, medium, low
    user_declaration: str = "not_implemented"  # implemented, not_implemented, unknown
    evidence_status: str = "no_evidence"  # direct_attachment, auto_matched, no_evidence, not_reviewed
    evidence_file_ids: List[str] = Field(default_factory=list)
    fact_card_ids: List[str] = Field(default_factory=list)
    auto_match_confidence: Optional[float] = None
    assessment_verdict: str = "missing"  # satisfied, not_evidenced, missing, needs_expert_review
    verdict_basis: List[str] = Field(default_factory=list)  # user_declaration, direct_evidence, auto_match, ai_inference
    expert_review_status: str = "pending"  # pending, approved, modified, rejected

    # Risk metrics
    risk_severity: str = "medium"  # critical, high, medium, low
    likelihood: int = 3  # 1-5
    impact: int = 3  # 1-5
    risk_score: int = 9  # likelihood * impact
    risk_assessment_basis: str = "ai_provisional"  # evidence_based, rule_based, ai_provisional, expert_validated
    gap: str = ""
    recommendation: str = ""
    timeline: str = "30-90 ngày"


class ControlCoverage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    self_declared_implemented: int = 0
    evidence_supported_implemented: int = 0
    not_evidenced_or_missing: int = 0
    total_controls: int = 0
    raw_percentage: float = 0.0


class WeightedCompliance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    weighted_score: float = 0.0
    weighted_max_score: float = 0.0
    percentage: float = 0.0
    algorithm: str = "weight_score_v1"


class EvidenceManifestItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_id: str
    masked_filename: str
    extension: str
    size_bytes: int
    sha256: str
    parser_or_ocr: str = "native_parser"
    timestamp: str = ""
    fact_card_id: Optional[str] = None
    control_mapping: List[str] = Field(default_factory=list)
    mapping_type: str = "auto_matched"  # direct_attachment, auto_matched


class EvidenceManifest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assessment_id: str
    run_id: str
    code_version: str = "v1.2.0-rel"
    created_at: str = ""
    total_files: int = 0
    files: List[EvidenceManifestItem] = Field(default_factory=list)


class UnifiedAssessmentResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assessment_id: str
    run_id: str
    code_version: str = "v1.2.0-rel"
    created_at: str = ""
    completed_at: str = ""
    status: str = "completed"  # processing, completed, failed
    standard: Dict[str, str] = Field(default_factory=lambda: {"id": "iso27001", "name": "ISO/IEC 27001:2022"})
    organization: Dict[str, Any] = Field(default_factory=dict)

    control_coverage: ControlCoverage = Field(default_factory=ControlCoverage)
    weighted_compliance: WeightedCompliance = Field(default_factory=WeightedCompliance)

    controls: List[ControlItem] = Field(default_factory=list)
    evidence_manifest_ref: str = ""
    audit_trace_ref: str = ""

    # Legacy & export compatibility views
    weight_breakdown: Dict[str, Any] = Field(default_factory=dict)
    risk_summary: Dict[str, Any] = Field(default_factory=dict)
    top_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    risk_register: List[Dict[str, Any]] = Field(default_factory=list)
    report: str = ""
