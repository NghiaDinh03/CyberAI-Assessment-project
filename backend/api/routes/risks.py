"""HTTP routes for the Risk Register module (Phase 2).

Endpoints (mounted under ``/api`` and ``/api/v1`` in :mod:`main`):
    GET    /risks              — list all risks
    POST   /risks              — create a new risk
    GET    /risks/{risk_id}    — get a single risk
    PATCH  /risks/{risk_id}    — partial update
    DELETE /risks/{risk_id}    — delete a risk
    GET    /risks/heatmap      — 5×5 likelihood×impact summary
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas.risk import (
    Risk,
    RiskCreate,
    RiskListResponse,
    RiskUpdate,
)
from services import risk_register_service as svc

router = APIRouter()


@router.get("/risks/heatmap")
async def risk_heatmap() -> dict:
    """Return a 5×5 matrix counting risks per (likelihood, impact) cell.

    Response shape::

        {
          "matrix": [[0,0,0,0,0], ...],   # matrix[likelihood-1][impact-1]
          "total": 12
        }
    """
    risks = svc.list_all()
    matrix = [[0] * 5 for _ in range(5)]
    for r in risks:
        matrix[r.likelihood - 1][r.impact - 1] += 1
    return {"matrix": matrix, "total": len(risks)}


@router.get("/risks", response_model=RiskListResponse)
async def list_risks() -> RiskListResponse:
    """Return all risks sorted by creation date (newest first)."""
    risks = svc.list_all()
    return RiskListResponse(risks=risks, total=len(risks))


@router.post("/risks", response_model=Risk, status_code=201)
async def create_risk(payload: RiskCreate) -> Risk:
    """Create a new risk entry. ``inherent_score`` is auto-calculated."""
    return svc.create(payload)


@router.get("/risks/{risk_id}", response_model=Risk)
async def get_risk(risk_id: str) -> Risk:
    risk = svc.get(risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found.")
    return risk


@router.patch("/risks/{risk_id}", response_model=Risk)
async def update_risk(risk_id: str, payload: RiskUpdate) -> Risk:
    """Partial update — only supplied fields are merged."""
    risk = svc.update(risk_id, payload)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found.")
    return risk


@router.delete("/risks/{risk_id}", status_code=204)
async def delete_risk(risk_id: str) -> None:
    if not svc.delete(risk_id):
        raise HTTPException(status_code=404, detail="Risk not found.")
