"""Pydantic schemas for the Risk Register module (Phase 2).

Schema mirrors context.md §C1:
    {id, asset_ref, threat, vulnerability, likelihood (1-4), impact (1-4),
     inherent_score, treatment, residual_score, owner, review_date,
     linked_controls[]}

``inherent_score`` is auto-calculated as ``likelihood × impact`` (1-16) on creation
and update — callers never set it directly.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class RiskBase(BaseModel):
    """Fields shared by create and update payloads."""

    asset_ref: str = Field(
        ..., min_length=1, max_length=300,
        description="Asset name or reference (e.g. 'ERP Server', 'Customer DB').",
    )
    threat: str = Field(
        ..., min_length=1, max_length=500,
        description="Threat description (e.g. 'Ransomware attack').",
    )
    vulnerability: str = Field(
        ..., min_length=1, max_length=500,
        description="Vulnerability exploited (e.g. 'Unpatched OS').",
    )
    likelihood: int = Field(
        ..., ge=1, le=4,
        description="Likelihood score 1-4 (1=Rare, 4=Almost Certain).",
    )
    impact: int = Field(
        ..., ge=1, le=4,
        description="Impact score 1-4 (1=Negligible, 4=Catastrophic).",
    )
    treatment: Literal[
        "mitigate", "accept", "transfer", "avoid",
    ] = Field(
        ...,
        description="Risk treatment strategy per ISO 27005.",
    )
    residual_score: int = Field(
        ..., ge=1, le=16,
        description="Residual risk score after treatment (1-16).",
    )
    owner: str = Field(
        ..., min_length=1, max_length=200,
        description="Risk owner (person or role).",
    )
    review_date: date = Field(
        ...,
        description="Next review date (ISO 8601 date).",
    )
    linked_controls: List[str] = Field(
        default_factory=list,
        description="ISO 27001 Annex A control IDs (e.g. ['A.5.1', 'A.8.3']).",
    )

    @field_validator("linked_controls", mode="before")
    @classmethod
    def _dedupe_controls(cls, v: list) -> list:
        """Remove duplicates while preserving order."""
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            s = str(item).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out


class RiskCreate(RiskBase):
    """Payload for POST /api/risks — ``id`` and ``inherent_score`` are
    server-generated."""
    pass


class RiskUpdate(BaseModel):
    """Partial update payload for PATCH /api/risks/{risk_id}.

    Every field is optional; only supplied fields are merged.
    """

    asset_ref: Optional[str] = Field(None, min_length=1, max_length=300)
    threat: Optional[str] = Field(None, min_length=1, max_length=500)
    vulnerability: Optional[str] = Field(None, min_length=1, max_length=500)
    likelihood: Optional[int] = Field(None, ge=1, le=4)
    impact: Optional[int] = Field(None, ge=1, le=4)
    treatment: Optional[Literal["mitigate", "accept", "transfer", "avoid"]] = None
    residual_score: Optional[int] = Field(None, ge=1, le=16)
    owner: Optional[str] = Field(None, min_length=1, max_length=200)
    review_date: Optional[date] = None
    linked_controls: Optional[List[str]] = None

    @field_validator("linked_controls", mode="before")
    @classmethod
    def _dedupe_controls(cls, v: list | None) -> list | None:
        if v is None:
            return v
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            s = str(item).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out


class Risk(BaseModel):
    """Full risk record as stored on disk and returned by the API."""

    id: str = Field(..., description="Server-generated UUID.")
    asset_ref: str = Field(..., min_length=1, max_length=300)
    threat: str = Field(..., min_length=1, max_length=500)
    vulnerability: str = Field(..., min_length=1, max_length=500)
    likelihood: int = Field(..., description="Likelihood score 1-4 (or legacy).")
    impact: int = Field(..., description="Impact score 1-4 (or legacy).")
    treatment: Literal["mitigate", "accept", "transfer", "avoid"]
    residual_score: int = Field(..., description="Residual risk score (1-16, or legacy).")
    owner: str = Field(..., min_length=1, max_length=200)
    review_date: date
    linked_controls: List[str] = Field(default_factory=list)
    inherent_score: int = Field(
        ...,
        description="Auto-calculated: likelihood × impact.",
    )
    created_at: datetime
    updated_at: datetime
    is_legacy: bool = False

    @model_validator(mode="before")
    @classmethod
    def _calc_inherent(cls, values: dict) -> dict:
        """Ensure inherent_score is always likelihood × impact, and identify legacy records."""
        if isinstance(values, dict):
            lk = values.get("likelihood")
            imp = values.get("impact")
            res = values.get("residual_score")
            inh = values.get("inherent_score")
            # If reading historical records with 5x5 metrics (>4 or >16), mark as legacy
            if (
                (lk is not None and lk > 4)
                or (imp is not None and imp > 4)
                or (res is not None and res > 16)
                or (inh is not None and inh > 16)
            ):
                values["is_legacy"] = True

            if lk is not None and imp is not None:
                values["inherent_score"] = lk * imp
        return values

    @model_validator(mode="after")
    def _validate_risk_bounds(self) -> "Risk":
        """Strictly validate current records against 4x4 matrix constraints."""
        if not self.is_legacy:
            if not (1 <= self.likelihood <= 4):
                raise ValueError(f"Likelihood must be between 1 and 4, got {self.likelihood}")
            if not (1 <= self.impact <= 4):
                raise ValueError(f"Impact must be between 1 and 4, got {self.impact}")
            expected = self.likelihood * self.impact
            if self.inherent_score != expected:
                raise ValueError(f"inherent_score must equal likelihood * impact ({expected}), got {self.inherent_score}")
            if self.inherent_score > 16:
                raise ValueError(f"inherent_score cannot exceed 16, got {self.inherent_score}")
            if not (1 <= self.residual_score <= 16):
                raise ValueError(f"residual_score must be between 1 and 16, got {self.residual_score}")
        return self


class RiskListResponse(BaseModel):
    """Paginated list wrapper."""

    risks: List[Risk]
    total: int

