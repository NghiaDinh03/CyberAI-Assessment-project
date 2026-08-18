"""API Routes — Custom Standards CRUD + Upload + ChromaDB indexing."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import logging

from services.standard_service import (
    parse_uploaded_standard,
    save_standard,
    list_custom_standards,
    delete_standard,
    index_standard_to_chromadb,
    get_standard_for_frontend,
    generate_sample_standard,
    validate_standard,
    StandardValidationError,
)

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB


@router.get("/standards")
async def get_all_standards():
    """List all available standards (built-in + custom uploaded).

    Returns built-in standards metadata alongside custom-uploaded ones.
    """
    # Built-in standards metadata
    builtin = [
        {
            "id": "iso27001",
            "name": "ISO 27001:2022 (93 Biện pháp kiểm soát)",
            "version": "2022",
            "description": "International standard for information security management systems (ISMS)",
            "total_controls": 93,
            "categories": 4,
            "source": "builtin",
        },
        {
            "id": "tcvn11930",
            "name": "TCVN 11930:2017 (34 Yêu cầu kỹ thuật/quản lý)",
            "version": "2017",
            "description": "Tiêu chuẩn Việt Nam về yêu cầu cơ bản đảm bảo ATTT hệ thống thông tin theo cấp độ",
            "total_controls": 34,
            "categories": 5,
            "source": "builtin",
        },
    ]

    custom = list_custom_standards()

    return {
        "builtin": builtin,
        "custom": custom,
        "total": len(builtin) + len(custom),
    }


@router.get("/standards/sample")
async def get_sample_standard():
    """Download a sample standard JSON template for reference."""
    sample = generate_sample_standard()
    return JSONResponse(
        content=sample,
        headers={
            "Content-Disposition": "attachment; filename=sample_standard.json",
            "Content-Type": "application/json; charset=utf-8",
        },
    )


@router.get("/standards/{standard_id}")
async def get_standard(standard_id: str):
    """Get a specific standard (full data for frontend rendering)."""
    # Check built-in first — return None to let frontend use its own data
    if standard_id in ("iso27001", "tcvn11930"):
        return {
            "id": standard_id,
            "source": "builtin",
            "message": "Built-in standard. Frontend uses local data from standards.js",
        }

    result = get_standard_for_frontend(standard_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Standard '{standard_id}' not found")
    return result


@router.post("/standards/upload")
async def upload_standard(file: UploadFile = File(...)):
    """Upload a JSON/YAML standard file, validate, save, and optionally index to ChromaDB.

    Accepts: .json, .yaml, .yml files up to 2MB.
    Returns: Standard metadata + validation results.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed_ext = (".json", ".yaml", ".yml")
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_ext)}"
        )

    # Read content
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE // 1024}KB")

    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    # Parse
    try:
        data = parse_uploaded_standard(content_str, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate before saving
    errors = validate_standard(data)
    if errors:
        return JSONResponse(
            status_code=422,
            content={
                "status": "validation_error",
                "errors": errors,
                "hint": "Download the sample template at GET /api/standards/sample for reference.",
            },
        )

    # Save
    try:
        result = save_standard(data)
    except StandardValidationError as e:
        return JSONResponse(
            status_code=422,
            content={"status": "validation_error", "errors": e.errors},
        )
    except Exception as e:
        logger.error(f"Failed to save standard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save standard: {str(e)}")

    # Auto-index to ChromaDB
    index_result = index_standard_to_chromadb(result["id"])

    return {
        "status": "success",
        "message": f"Standard '{result['name']}' uploaded successfully",
        "standard": result,
        "chromadb_index": index_result,
    }


@router.post("/standards/{standard_id}/index")
async def reindex_standard(standard_id: str):
    """Re-index a specific standard into ChromaDB for RAG."""
    if standard_id in ("iso27001", "tcvn11930"):
        # Built-in standards use the main reindex endpoint
        return {
            "status": "info",
            "message": "Built-in standards are indexed via /api/iso27001/reindex",
        }

    result = index_standard_to_chromadb(standard_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Indexing failed"))
    return result


@router.delete("/standards/{standard_id}")
async def remove_standard(standard_id: str):
    """Delete a custom standard and its ChromaDB index."""
    try:
        deleted = delete_standard(standard_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Standard '{standard_id}' not found")

        # Try to remove from ChromaDB (domain-scoped collection)
        try:
            from repositories.vector_store import VectorStore
            vs = VectorStore()
            coll = vs.get_collection(standard_id)
            existing = coll.get()
            if existing and existing["ids"]:
                coll.delete(ids=existing["ids"])
        except Exception as e:
            logger.warning(f"Could not remove ChromaDB collection for '{standard_id}': {e}")

        return {"status": "success", "message": f"Standard '{standard_id}' deleted"}

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/standards/validate")
async def validate_standard_endpoint(file: UploadFile = File(...)):
    """Validate a standard file without saving it. Useful for pre-upload checks."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        content_str = content.decode("utf-8")
        data = parse_uploaded_standard(content_str, file.filename)
    except (ValueError, UnicodeDecodeError) as e:
        return {"valid": False, "errors": [str(e)]}

    errors = validate_standard(data)

    # Calculate stats even if there are errors
    total_controls = 0
    categories = 0
    if isinstance(data.get("controls"), list):
        categories = len(data["controls"])
        for cat in data["controls"]:
            if isinstance(cat.get("controls"), list):
                total_controls += len(cat["controls"])

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "preview": {
            "id": data.get("id", ""),
            "name": data.get("name", ""),
            "version": data.get("version", ""),
            "total_controls": total_controls,
            "categories": categories,
        },
    }
