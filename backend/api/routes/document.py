from fastapi import APIRouter, UploadFile, File, Request
from services.document_service import DocumentService
from core.config import settings

router = APIRouter()
doc_service = DocumentService()

try:
    from main import limiter, _has_rate_limit
except ImportError:
    limiter = None
    _has_rate_limit = False


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    result = await doc_service.process_upload(file)
    return result
