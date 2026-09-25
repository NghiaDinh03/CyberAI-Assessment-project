"""Unified Assessment Schema — Standardized contract across JSON, Audit Trace, SoA, Risk Register, DOCX, and PDF."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VALID_VERDICTS = {
    "satisfied",
    "partial",
    "partially_satisfied",
    "not_satisfied",
    "not_evidenced",
    "missing",
    "needs_expert_review",
    "pending",
}

WEIGHT_NAME_TO_POINTS = {
    "critical": 10.0,
    "high": 5.0,
    "medium": 3.0,
    "low": 1.0,
}

WEIGHT_POINTS_TO_NAME = {
    10.0: "critical",
    5.0: "high",
    3.0: "medium",
    1.0: "low",
    10: "critical",
    5: "high",
    3: "medium",
    1: "low",
}

VERDICT_FACTOR = {
    "satisfied": 1.0,
    "partial": 0.5,
    "partially_satisfied": 0.5,
    "not_evidenced": 0.0,
    "missing": 0.0,
    "needs_expert_review": 0.0,
}


class ControlItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    control_id: str = Field(default="", min_length=0)
    label: str = ""
    category: str = ""
    weight: Union[float, str] = 3.0  # 10.0, 5.0, 3.0, 1.0 or 'critical', 'high', 'medium', 'low'
    weight_points: float = 3.0       # Explicit numeric weight (10, 5, 3, 1)
    weight_level: str = "medium"     # 'critical', 'high', 'medium', 'low'
    user_declaration: str = "not_implemented"  # implemented, not_implemented, unknown
    evidence_status: str = "no_evidence"  # direct_attachment, auto_matched, no_evidence, not_reviewed
    evidence_file_ids: List[str] = Field(default_factory=list)
    fact_card_ids: List[str] = Field(default_factory=list)
    auto_match_confidence: Optional[float] = None
    assessment_verdict: str = "missing"  # satisfied, not_evidenced, missing, needs_expert_review
    verdict: Optional[str] = None
    verdict_factor: float = 0.0          # 1.0 (satisfied), 0.5 (partial), 0.0 (others)
    weighted_score_contribution: float = 0.0  # weight * verdict_factor
    verdict_basis: List[str] = Field(default_factory=list)  # user_declaration, direct_evidence, auto_match, ai_inference
    expert_review_status: str = "pending"  # pending, approved, modified, rejected

    # Conflict detection attributes
    conflict_detected: bool = False
    conflict_reason: Optional[str] = None
    conflicting_evidence_ids: List[str] = Field(default_factory=list)

    # Risk metrics (4x4 Heatmap: Likelihood 1-4, Impact 1-4, Risk Score 1-16)
    risk_severity: str = "medium"  # critical, high, medium, low
    likelihood: int = 3  # 1-4
    impact: int = 3  # 1-4
    risk_score: int = 9  # likelihood * impact (1-16)
    risk_assessment_basis: str = "ai_provisional"  # evidence_based, rule_based, ai_provisional, expert_validated
    gap: str = ""
    recommendation: str = ""
    timeline: str = "30-90 ngày"
    is_legacy: bool = False

    # Detailed Verdict Provenance & Trace
    ai_verdict_raw: Optional[str] = None
    normalized_ai_verdict: Optional[str] = None
    verdict_source: str = "safe_fallback_no_evidence"
    fallback_reason: Optional[str] = None
    verdict_rationale: Optional[str] = None
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list)

    score: Optional[int] = None

    # Compatibility aliases
    id: Optional[str] = None
    evidence_verdict: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def map_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            c_id = data.get("control_id") or data.get("id") or ""
            data["control_id"] = str(c_id)
            
            # Map weight
            raw_w = data.get("weight")
            if isinstance(raw_w, str):
                w_lower = raw_w.lower().strip()
                if w_lower in WEIGHT_NAME_TO_POINTS:
                    data["weight_points"] = WEIGHT_NAME_TO_POINTS[w_lower]
                    data["weight_level"] = w_lower
                    data["weight"] = WEIGHT_NAME_TO_POINTS[w_lower]
                else:
                    try:
                        num_w = float(raw_w)
                        data["weight"] = num_w
                        data["weight_points"] = num_w
                        data["weight_level"] = WEIGHT_POINTS_TO_NAME.get(num_w, "medium")
                    except ValueError:
                        data["weight"] = 3.0
                        data["weight_points"] = 3.0
                        data["weight_level"] = "medium"
            elif isinstance(raw_w, (int, float)):
                num_w = float(raw_w)
                data["weight"] = num_w
                data["weight_points"] = num_w
                data["weight_level"] = WEIGHT_POINTS_TO_NAME.get(num_w, "medium")
            elif raw_w is None:
                data["weight"] = 3.0
                data["weight_points"] = 3.0
                data["weight_level"] = "medium"

            verdict = data.get("assessment_verdict") or data.get("verdict") or data.get("evidence_verdict")
            if not verdict:
                sc = data.get("score")
                if sc is not None and sc >= 4:
                    verdict = "satisfied"
                elif sc is not None and sc > 0:
                    verdict = "partial"
                else:
                    verdict = "missing"
            data["assessment_verdict"] = str(verdict)
            data["verdict"] = str(verdict)
        return data

    @field_validator("assessment_verdict")
    @classmethod
    def validate_verdict(cls, v: str) -> str:
        if not isinstance(v, str) or v.lower() not in VALID_VERDICTS:
            raise ValueError(f"Invalid assessment verdict '{v}'. Valid verdicts: {sorted(VALID_VERDICTS)}")
        return v.lower()

    @model_validator(mode="after")
    def enforce_conflict_safe_branch(self) -> "ControlItem":
        if self.conflict_detected:
            self.assessment_verdict = "needs_expert_review"
            self.verdict_source = "safe_fallback_conflict"
            if not self.conflict_reason:
                self.conflict_reason = "Mâu thuẫn giữa thông tin tự kê khai và bằng chứng kỹ thuật."
            if not self.fallback_reason:
                self.fallback_reason = self.conflict_reason
        
        self.verdict = self.assessment_verdict
        if not self.id:
            self.id = self.control_id
        if not self.evidence_verdict:
            self.evidence_verdict = self.assessment_verdict

        # Calculate authoritative verdict_factor and weighted_score_contribution
        self.verdict_factor = VERDICT_FACTOR.get(self.assessment_verdict, 0.0)
        self.weighted_score_contribution = round(float(self.weight_points) * float(self.verdict_factor), 1)

        # Retain score field for legacy compatibility: semantic equals weighted_score_contribution
        self.score = int(round(self.weighted_score_contribution))

        # Validate 4x4 Risk Heatmap constraints
        if not self.is_legacy:
            if not (1 <= self.likelihood <= 4):
                raise ValueError(f"Likelihood must be between 1 and 4, got {self.likelihood}")
            if not (1 <= self.impact <= 4):
                raise ValueError(f"Impact must be between 1 and 4, got {self.impact}")
            expected_risk = self.likelihood * self.impact
            if self.risk_score != expected_risk:
                raise ValueError(
                    f"Risk score must equal likelihood * impact ({expected_risk}), got {self.risk_score}"
                )
            if self.risk_score > 16:
                raise ValueError(f"Risk score cannot exceed 16, got {self.risk_score}")

        return self


class ControlCoverage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    self_declared_implemented: int = 0
    evidence_supported_implemented: int = 0
    not_evidenced_or_missing: int = 0
    not_applicable_count: int = 0
    total_applicable_controls: int = 0
    total_controls: int = 0
    raw_percentage: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def sync_total_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            tot_ctrls = data.get("total_controls")
            tot_app = data.get("total_applicable_controls")
            if tot_ctrls is None and tot_app is not None:
                data["total_controls"] = tot_app
            elif tot_app is None and tot_ctrls is not None:
                data["total_applicable_controls"] = tot_ctrls
            data["not_applicable_count"] = 0
        return data


class WeightedCompliance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    weighted_score: float = 0.0
    weighted_max_score: float = 0.0
    percentage: float = 0.0
    algorithm: str = "verdict_weighted_v2"
    weight_scheme: Optional[str] = "critical_10_high_5_medium_3_low_1"


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
    ingestion_status: str = "ingested"  # ingested, excluded
    exclusion_reason: Optional[str] = None


class EvidenceManifest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assessment_id: str
    run_id: str
    code_version: str = "v1.2.0-verdict"
    created_at: str = ""
    total_files: int = 0
    mapped_control_count: int = 0
    files: List[EvidenceManifestItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def enforce_manifest_invariants(cls, data: Any) -> Any:
        if isinstance(data, dict):
            files = data.get("files", [])
            unique_keys = set()
            for it in files:
                if isinstance(it, dict):
                    k = it.get("sha256") or it.get("file_id") or it.get("masked_filename")
                else:
                    k = getattr(it, "sha256", None) or getattr(it, "file_id", None) or getattr(it, "masked_filename", None)
                if k:
                    unique_keys.add(k)
            if unique_keys:
                data["total_files"] = len(unique_keys)
            mapped_ctrls = set()
            for it in files:
                st = it.get("ingestion_status") if isinstance(it, dict) else getattr(it, "ingestion_status", None)
                if st == "ingested" or st is None:
                    cmap = it.get("control_mapping") or it.get("controls_covered") if isinstance(it, dict) else getattr(it, "control_mapping", None) or getattr(it, "controls_covered", None)
                    if cmap:
                        for c in cmap:
                            if c:
                                mapped_ctrls.add(str(c))
            if mapped_ctrls:
                data["mapped_control_count"] = len(mapped_ctrls)
        return data


class UnifiedAssessmentResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    assessment_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    code_version: str = "v1.2.0-verdict"
    created_at: str = ""
    completed_at: str = ""
    status: str = "completed"  # processing, completed, failed
    standard: Dict[str, str] = Field(default_factory=lambda: {"id": "iso27001", "name": "ISO/IEC 27001:2022"})
    organization: Dict[str, Any] = Field(default_factory=dict)

    control_coverage: ControlCoverage = Field(default_factory=ControlCoverage)
    weighted_compliance: WeightedCompliance = Field(default_factory=WeightedCompliance)

    controls: List[ControlItem] = Field(default_factory=list)
    evidence_manifest_ref: str = ""
    evidence_manifest_id: Optional[str] = ""
    evidence_manifest: Optional[Dict[str, Any]] = None
    audit_trace_ref: str = ""
    runtime_summary: Dict[str, Any] = Field(default_factory=dict)
    chunk_telemetries: List[Dict[str, Any]] = Field(default_factory=list)

    # Legacy & export compatibility views
    compliance: Dict[str, Any] = Field(default_factory=dict)
    weighted_coverage: Dict[str, Any] = Field(default_factory=dict)
    weight_breakdown: Dict[str, Any] = Field(default_factory=dict)
    risk_summary: Dict[str, Any] = Field(default_factory=dict)
    top_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    risk_register: List[Dict[str, Any]] = Field(default_factory=list)
    report: str = ""

    @field_validator("assessment_id", "run_id")
    @classmethod
    def validate_required_string(cls, v: str, info) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"Trường bắt buộc '{info.field_name}' không được để trống.")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def extract_wrapped_assessment_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "assessment_id" not in data and "id" in data and data["id"]:
                data["assessment_id"] = str(data["id"])

            # Normalize standard if passed as plain string
            if "standard" in data and isinstance(data["standard"], str):
                s_id = data["standard"]
                s_name = "ISO/IEC 27001:2022" if "27001" in s_id else "TCVN 11930:2017" if "11930" in s_id else s_id.upper()
                data["standard"] = {"id": s_id, "name": s_name}

            # If wrapped under 'json_data', merge top-level properties into a flattened dictionary
            if "json_data" in data and isinstance(data["json_data"], dict):
                merged = dict(data["json_data"])
                for key in (
                    "assessment_id", "run_id", "code_version", "created_at",
                    "completed_at", "status", "organization", "evidence_manifest_ref", "audit_trace_ref",
                    "standard", "compliance_percent"
                ):
                    if key in data and (key not in merged or not merged[key]):
                        merged[key] = data[key]
                if "assessment_id" not in merged and "assessment_id" in data:
                    merged["assessment_id"] = data["assessment_id"]
                elif "assessment_id" not in merged and "id" in data:
                    merged["assessment_id"] = str(data["id"])
                if "run_id" not in merged and "run_id" in data:
                    merged["run_id"] = data["run_id"]
                if "compliance" in data and "compliance" not in merged:
                    merged["compliance"] = data["compliance"]
                if "weighted_coverage" in data and "weighted_coverage" not in merged:
                    merged["weighted_coverage"] = data["weighted_coverage"]
                if "system_info" in data and isinstance(data["system_info"], dict):
                    sys_info = data["system_info"]
                    if "organization" not in merged:
                        org = sys_info.get("organization") or {"name": sys_info.get("org_name", "")}
                        merged["organization"] = org
                    ev_map = sys_info.get("evidence_map") or {}
                    impl = sys_info.get("compliance", {}).get("implemented_controls", [])
                    if "controls" in merged and isinstance(merged["controls"], list):
                        for ctrl in merged["controls"]:
                            if isinstance(ctrl, dict):
                                cid = ctrl.get("control_id") or ctrl.get("id")
                                if cid in ev_map and not ctrl.get("evidence_file_ids"):
                                    raw = ev_map[cid]
                                    ctrl["evidence_file_ids"] = raw if isinstance(raw, list) else [raw]
                                if cid in impl and not ctrl.get("user_declaration"):
                                    ctrl["user_declaration"] = "implemented"
                                # Check for legacy 5x5 metrics to preserve backwards-compatibility
                                lk = ctrl.get("likelihood")
                                imp = ctrl.get("impact")
                                sc = ctrl.get("risk_score")
                                if (lk is not None and lk > 4) or (imp is not None and imp > 4) or (sc is not None and sc > 16):
                                    ctrl["is_legacy"] = True
                return merged
        return data

    @model_validator(mode="after")
    def populate_coverage_and_invariants(self) -> "UnifiedAssessmentResult":
        applicable = self.controls
        tot_app = len(applicable)
        tot_ctrls = tot_app

        # Only overwrite coverage from controls if controls represent full assessment or coverage was not pre-populated
        has_full_controls = (
            tot_app > 0 and (
                self.control_coverage.total_controls == 0 or
                self.control_coverage.total_controls <= tot_app or
                tot_app >= 30
            )
        )

        if has_full_controls:
            satisfied_cnt = sum(1 for c in applicable if (c.assessment_verdict or "").lower() == "satisfied")
            not_ev_missing_cnt = sum(
                1 for c in applicable
                if (c.assessment_verdict or "").lower() in ("not_evidenced", "missing", "needs_expert_review", "not_satisfied")
            )
            decl_cnt = sum(1 for c in applicable if c.user_declaration == "implemented")
            raw_pct = round((decl_cnt / tot_app * 100), 1) if tot_app > 0 else 0.0

            # 1. Authoritative ControlCoverage
            self.control_coverage = ControlCoverage(
                self_declared_implemented=decl_cnt,
                evidence_supported_implemented=satisfied_cnt,
                not_evidenced_or_missing=not_ev_missing_cnt,
                not_applicable_count=0,
                total_applicable_controls=tot_app,
                total_controls=tot_ctrls,
                raw_percentage=raw_pct,
            )

            # 2. Strict verdict_weighted_v2 calculation & invariant guarantee:
            # sum(c.weighted_score_contribution) == weighted_compliance.weighted_score
            contrib_sum = round(sum(c.weighted_score_contribution for c in applicable), 1)
            tot_max_w = round(sum(c.weight_points for c in applicable), 1)
            verdict_pct = round((contrib_sum / tot_max_w * 100), 1) if tot_max_w > 0 else 0.0

            self.weighted_compliance.weighted_score = contrib_sum
            self.weighted_compliance.weighted_max_score = tot_max_w
            self.weighted_compliance.percentage = verdict_pct
            self.weighted_compliance.algorithm = "verdict_weighted_v2"
            self.weighted_compliance.weight_scheme = "critical_10_high_5_medium_3_low_1"

            # 3. Preliminary Weighted Coverage (from self-declaration only)
            w_decl_score = round(sum(c.weight_points for c in applicable if c.user_declaration == "implemented"), 1)
            w_decl_pct = round(w_decl_score / tot_max_w * 100, 1) if tot_max_w > 0 else 0.0
            self.weighted_coverage = {
                "score": w_decl_score,
                "max_score": tot_max_w,
                "percentage": w_decl_pct,
            }

            # 4. Sync legacy compliance dict with verified stats
            ev_supp_pct = round((satisfied_cnt / tot_app * 100), 1) if tot_app > 0 else 0.0
            self.compliance = {
                "score": satisfied_cnt,
                "max_score": tot_app,
                "percentage": ev_supp_pct,
                "satisfied_count": satisfied_cnt,
            }

        # 5. Harmonize risk_summary directly from risk_register
        if self.risk_register:
            # Enforce no satisfied controls in risk_register
            self.risk_register = [
                r for r in self.risk_register
                if (r.get("verdict") or "").lower() != "satisfied"
            ]
            crit = sum(1 for r in self.risk_register if str(r.get("severity", "")).lower() == "critical")
            high = sum(1 for r in self.risk_register if str(r.get("severity", "")).lower() == "high")
            med = sum(1 for r in self.risk_register if str(r.get("severity", "")).lower() == "medium")
            low = sum(1 for r in self.risk_register if str(r.get("severity", "")).lower() == "low")
            tot_gaps = len(self.risk_register)
            self.risk_summary = {
                "critical_gaps": crit,
                "high_gaps": high,
                "medium_gaps": med,
                "low_gaps": low,
                "total_gaps": tot_gaps,
            }

        return self

