"""API routes for Infrastructure & ISO 27001 Assessment History."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

try:
    from repositories.assessment_store import assessment_store
except ImportError:
    from backend.repositories.assessment_store import assessment_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assessment/history", tags=["Assessment History"])


class SaveAssessmentRequest(BaseModel):
    report_data: Dict[str, Any]
    project_name: Optional[str] = None
    system_scope: Optional[str] = None
    assessment_id: Optional[str] = None


@router.get("", response_model=List[Dict[str, Any]])
async def list_assessments(limit: int = Query(50, ge=1, le=200)):
    """Retrieve the historical list of completed infrastructure assessments."""
    return assessment_store.list_assessments(limit=limit)


@router.post("", response_model=Dict[str, Any])
async def save_assessment_record(req: SaveAssessmentRequest):
    """Save an assessment report to the database."""
    aid = assessment_store.save_assessment(
        report_data=req.report_data,
        project_name=req.project_name,
        system_scope=req.system_scope,
        assessment_id=req.assessment_id
    )
    return {"status": "saved", "assessment_id": aid}


@router.get("/{assessment_id}", response_model=Dict[str, Any])
async def get_assessment_details(assessment_id: str):
    """Retrieve full details and control reports for a past assessment."""
    record = assessment_store.get_assessment(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment record not found")
    return record


@router.delete("/{assessment_id}")
async def delete_assessment_record(assessment_id: str):
    """Delete a past assessment record."""
    deleted = assessment_store.delete_assessment(assessment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Assessment record not found or already deleted")
    return {"status": "deleted", "assessment_id": assessment_id}
