import asyncio
import re as _re_val
import time
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException, Query, Header, Request
from fastapi.responses import FileResponse, StreamingResponse

from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional, Any
from services.chat_service import ChatService
import uuid
import json
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()

# Regex for safe path-component identifiers: alphanumeric, hyphen, underscore, dot (no double dot).
_SAFE_ID_RE = _re_val.compile(r'^(?!.*\.\.)[a-zA-Z0-9_\-\.]+$')


def _validate_path_id(value: str, field_name: str = "id") -> None:
    """Raise HTTP 400 if *value* contains characters that could enable path traversal."""
    if not value or not _SAFE_ID_RE.match(value):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid {field_name}: only alphanumeric characters, hyphens, "
                f"underscores, and dots are allowed."
            ),
        )

ASSESSMENTS_DIR = os.getenv("DATA_PATH", "./data") + "/assessments"
EVIDENCE_DIR = os.getenv("DATA_PATH", "./data") + "/evidence"
EXPORTS_DIR = os.getenv("DATA_PATH", "./data") + "/exports"
os.makedirs(ASSESSMENTS_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

from services.evidence_parser import parse_evidence_file, MAX_EVIDENCE_SIZE_BYTES, SUPPORTED_EXTENSIONS
from repositories.feedback_store import AuditFeedbackStore

ALLOWED_EVIDENCE_EXT = SUPPORTED_EXTENSIONS
MAX_EVIDENCE_SIZE = MAX_EVIDENCE_SIZE_BYTES


def parse_evidence_file_content(filepath: str, filename: Optional[str] = None) -> str:
    """Read and extract structured security fact summary and full text from uploaded evidence file using Agent 1."""
    if not os.path.exists(filepath):
        return "[File not found on server]"
    fname = filename or os.path.basename(filepath)
    try:
        with open(filepath, "rb") as f:
            content = f.read()
        res = parse_evidence_file(content, fname)
        
        pieces = []
        # 1. Agent 1 Structured Fact Summary
        if res.get("fact_summary"):
            pieces.append(f"[AGENT 1 TÓM TẮT BẰNG CHỨNG]:\n{res['fact_summary']}")
        
        # 2. Detailed extracted text (preserving Heading structure & tables up to 60,000 chars)
        text = res.get("full_text") or res.get("parsed_text", "")
        if text:
            if len(text) > 60000:
                pieces.append(f"[CHI TIẾT NỘI DUNG TÀI LIỆU BẰNG CHỨNG (60,000 ký tự đầu)]:\n{text[:60000]}\n... [Đã trích xuất trọn vẹn các phần kiểm toán trọng yếu]")
            else:
                pieces.append(f"[CHI TIẾT NỘI DUNG TÀI LIỆU BẰNG CHỨNG]:\n{text}")
        
        return "\n\n".join(pieces) if pieces else "[Không có nội dung văn bản trích xuất]"
    except Exception as e:
        logger.warning(f"Evidence parse error {filepath}: {e}")
        return f"[Error reading file: {str(e)[:100]}]"


def build_evidence_context_for_ai(evidence_map: Dict[str, List[str]], standard: str = "iso27001") -> str:
    """Build structured evidence text for AI prompt from evidence_map with Agent 1 Fact Cards and Feedback Exemplars.
    evidence_map: { controlId: [filename1, filename2, ...] }
    """
    if not evidence_map:
        return ""
    sections = ["\n\n--- BẰNG CHỨNG / MINH CHỨNG ĐÍNH KÈM TỪ DOANH NGHIỆP (AGENT 1 STRUCTURED) ---"]
    control_ids = []
    for ctrl_id, filenames in evidence_map.items():
        if not filenames:
            continue
        control_ids.append(ctrl_id)
        sections.append(f"\n[Control {ctrl_id}] — {len(filenames)} tệp minh chứng:")
        for fname in filenames:
            safe_name = os.path.basename(fname)
            stored_name = f"{ctrl_id}_{safe_name}"
            fpath = os.path.join(EVIDENCE_DIR, stored_name)
            snippet = parse_evidence_file_content(fpath, safe_name)
            sections.append(f"  • File: {safe_name}")
            sections.append(f"    Nội dung thực tế trích xuất:\n    {snippet}")
    sections.append("\n--- HẾT PHẦN BẰNG CHỨNG ---")
    sections.append("Lưu ý cho Auditor: Các controls có bằng chứng đính kèm cho thấy ")
    sections.append("tổ chức đã có tài liệu/minh chứng triển khai thực tế. ")
    sections.append("Hãy đánh giá CHẤT LƯỢNG bằng chứng và mức độ đầy đủ.")

    # Inject historical feedback few-shot examples for these controls
    try:
        fb_store = AuditFeedbackStore.get_instance()
        few_shot_txt = fb_store.format_few_shot_prompt(control_ids, standard=standard)
        if few_shot_txt:
            sections.append(few_shot_txt)
    except Exception as fb_err:
        logger.debug(f"[Assessment] Feedback exemplars lookup error: {fb_err}")

    return "\n".join(sections)


class SystemInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    assessment_standard: Any = "iso27001"
    org_name: Any = ""
    org_size: Any = ""
    industry: Any = ""
    servers: Any = 0
    firewalls: Any = ""
    vpn: Any = False
    cloud_provider: Any = ""
    antivirus: Any = ""
    backup_solution: Any = ""
    siem: Any = ""
    network_diagram: Any = ""
    implemented_controls: Any = []
    incidents_12m: Any = 0
    employees: Any = 0
    it_staff: Any = 0
    iso_status: Any = ""
    notes: Any = ""
    model_mode: Any = "local"
    selected_model: Any = None
    assessment_scope: Any = "full"
    scope_description: Any = ""
    evidence_map: Any = {}


def save_assessment(assessment_id: str, data: dict):
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_assessment(assessment_id: str) -> Optional[dict]:
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def list_assessments() -> List[dict]:
    results = []
    for filename in os.listdir(ASSESSMENTS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(ASSESSMENTS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append({
                        "id": data.get("id"),
                        "status": data.get("status"),
                        "standard": data.get("system_info", {}).get("assessment_standard", "iso27001"),
                        "org_name": data.get("system_info", {}).get("organization", {}).get("name", "Unknown"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "compliance_percent": data.get("compliance_percent")
                    })
            except Exception:
                pass
    return sorted(results, key=lambda x: x.get("created_at") or "", reverse=True)


def update_assessment_progress(assessment_id: str, message: str, pct: int):
    """Update progress field in assessment record for frontend polling."""
    data = load_assessment(assessment_id)
    if data:
        data["progress"] = {"message": message, "percent": pct, "updated_at": datetime.now(timezone.utc).isoformat()}
        save_assessment(assessment_id, data)


def process_assessment_bg(assessment_id: str, system_data: dict, model_mode: str = "hybrid", evidence_context: str = "", run_id: Optional[str] = None):
    import hashlib
    from services.audit_service import audit_service, AuditContext
    from services.evidence_parser import compute_file_sha256, mask_evidence_filename
    from schemas.assessment_schema import EvidenceManifest, EvidenceManifestItem

    eff_run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
    audit_ctx = AuditContext(
        assessment_id=assessment_id,
        run_id=eff_run_id,
        code_version="v1.2.0-rel"
    )

    data = load_assessment(assessment_id)
    if not data:
        return

    data["status"] = "processing"
    data["run_id"] = audit_ctx.run_id
    data["code_version"] = audit_ctx.code_version
    data["progress"] = {"message": "Khởi động tiến trình đa tác tử...", "percent": 0}
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_assessment(assessment_id, data)

    t0 = time.time()
    try:
        # Build Evidence Manifest and accurate counters
        ev_manifest_dir = os.path.join(os.getenv("DATA_PATH", "./data"), "evidence_manifests")
        os.makedirs(ev_manifest_dir, exist_ok=True)
        manifest_path = os.path.join(ev_manifest_dir, f"{assessment_id}.json")

        manifest_items: List[EvidenceManifestItem] = []
        ev_map = system_data.get("evidence_map") or {}

        for ctrl_id, files in ev_map.items():
            f_list = files if isinstance(files, list) else [files]
            for fname in f_list:
                safe_name = os.path.basename(fname)
                candidate_paths = [
                    os.path.join(EVIDENCE_DIR, ctrl_id.replace(".", "_"), safe_name),
                    os.path.join(EVIDENCE_DIR, assessment_id, ctrl_id, safe_name),
                    os.path.join(EVIDENCE_DIR, f"{ctrl_id}_{safe_name}"),
                    os.path.join(EVIDENCE_DIR, safe_name),
                ]
                fpath = None
                for cp in candidate_paths:
                    if os.path.exists(cp):
                        fpath = cp
                        break

                size_bytes = os.path.getsize(fpath) if fpath and os.path.exists(fpath) else 0
                file_bytes = b""
                if fpath and os.path.exists(fpath):
                    try:
                        with open(fpath, "rb") as ef:
                            file_bytes = ef.read()
                    except Exception:
                        pass

                f_hash = compute_file_sha256(file_bytes) if file_bytes else hashlib.sha256(safe_name.encode()).hexdigest()
                masked_name = mask_evidence_filename(safe_name)
                ext = os.path.splitext(safe_name)[1].lower() or ".bin"

                manifest_items.append(EvidenceManifestItem(
                    file_id=f"file_{hashlib.md5(safe_name.encode()).hexdigest()[:8]}",
                    masked_filename=masked_name,
                    extension=ext,
                    size_bytes=size_bytes,
                    sha256=f_hash,
                    parser_or_ocr="native_parser",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    fact_card_id=f"fact_{ctrl_id}",
                    control_mapping=[ctrl_id],
                    mapping_type="direct_attachment" if not safe_name.startswith("batch_") else "auto_matched",
                ))

        # Also parse from evidence_context if ev_map was empty
        if not manifest_items and evidence_context:
            extracted_files = [line.split("• File:", 1)[1].strip() for line in evidence_context.splitlines() if "• File:" in line]
            for safe_name in extracted_files:
                masked_name = mask_evidence_filename(safe_name)
                ext = os.path.splitext(safe_name)[1].lower() or ".bin"
                manifest_items.append(EvidenceManifestItem(
                    file_id=f"file_{hashlib.md5(safe_name.encode()).hexdigest()[:8]}",
                    masked_filename=masked_name,
                    extension=ext,
                    size_bytes=0,
                    sha256=hashlib.sha256(safe_name.encode()).hexdigest(),
                    parser_or_ocr="native_parser",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    fact_card_id=None,
                    control_mapping=[],
                    mapping_type="direct_attachment",
                ))

        manifest = EvidenceManifest(
            assessment_id=assessment_id,
            run_id=audit_ctx.run_id,
            code_version=audit_ctx.code_version,
            created_at=datetime.now(timezone.utc).isoformat(),
            total_files=len(manifest_items),
            files=manifest_items,
        )
        with open(manifest_path, "w", encoding="utf-8") as mf:
            mf.write(manifest.model_dump_json(indent=2))

        # Record evidence parsed event with actual count
        impl_ctrls = system_data.get("compliance", {}).get("implemented_controls", [])
        ext_list = list({item.extension for item in manifest_items}) if manifest_items else [".log", ".txt", ".md", ".png", ".pdf"]
        audit_service.record_evidence_parsed(
            ctx=audit_ctx,
            evidence_controls_count=len(ev_map) if ev_map else len(impl_ctrls),
            total_files=len(manifest_items),
            file_extensions=ext_list,
        )

        if evidence_context:
            system_data["notes"] = (system_data.get("notes", "") or "") + evidence_context

        init_msg = "Tác tử 1 (bge-m3 1024D): Nạp vector tri thức tiêu chuẩn & đối chiếu hồ sơ..."
        update_assessment_progress(assessment_id, init_msg, 5)
        result = ChatService.assess_system(
            system_data, model_mode=model_mode,
            progress_callback=lambda msg, pct: update_assessment_progress(assessment_id, msg, pct),
            audit_ctx=audit_ctx,
        )

        data["status"] = "completed"
        data["run_id"] = audit_ctx.run_id
        data["code_version"] = audit_ctx.code_version
        data["evidence_manifest_ref"] = f"data/evidence_manifests/{assessment_id}.json"
        data["audit_trace_ref"] = f"data/audit_traces/{assessment_id}.json"
        data["progress"] = {"message": "Hoàn tất thẩm định an toàn thông tin", "percent": 100}
        data["result"] = result
        # Store json_data at top level for quick access
        if result.get("json_data"):
            data["json_data"] = result["json_data"]
            data["json_data"]["evidence_manifest_ref"] = data["evidence_manifest_ref"]
            data["json_data"]["audit_trace_ref"] = data["audit_trace_ref"]
        
        # Update compliance_percent with authoritative verified calculation
        res_pct = (
            result.get("compliance_percent")
            if result.get("compliance_percent") is not None
            else result.get("json_data", {}).get("compliance", {}).get("percentage")
        )
        if res_pct is not None:
            try:
                data["compliance_percent"] = round(min(100.0, max(0.0, float(res_pct))), 1)
            except (ValueError, TypeError):
                pass

        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_assessment(assessment_id, data)

        duration = time.time() - t0
        audit_service.record_assessment_completed(
            ctx=audit_ctx,
            standard=system_data.get("assessment_standard", "iso27001"),
            compliance_percentage=data.get("compliance_percent", 0.0),
            total_duration_seconds=duration,
        )

        try:
            from repositories.assessment_store import assessment_store
            assessment_store.save_assessment(
                report_data=data,
                project_name=system_data.get("organization", {}).get("name"),
                system_scope=system_data.get("infrastructure", {}).get("cloud"),
                assessment_id=assessment_id
            )
        except Exception as store_err:
            logger.warning(f"AssessmentStore SQLite save non-fatal error: {store_err}")

    except Exception as e:
        logger.error(f"[AssessmentBG] Pipeline failed for {assessment_id}: {e}", exc_info=True)
        err_msg = str(e)
        err_lower = err_msg.lower()
        if "timeout" in err_lower or "timed out" in err_lower:
            err_code = "MODEL_TIMEOUT"
        elif "ollama" in err_lower or "connection error" in err_lower or "unreachable" in err_lower or "failed to connect" in err_lower:
            err_code = "OLLAMA_UNAVAILABLE"
        elif "chromadb" in err_lower or "vector" in err_lower or "rag" in err_lower:
            err_code = "RAG_QUERY_FAILED"
        elif "evidence" in err_lower or "parse" in err_lower or "decode" in err_lower:
            err_code = "EVIDENCE_PARSE_FAILED"
        elif "database" in err_lower or "sqlite" in err_lower or "migration" in err_lower:
            err_code = "DATABASE_MIGRATION_ERROR"
        else:
            err_code = "ASSESSMENT_PIPELINE_ERROR"

        data = load_assessment(assessment_id) or data or {}
        data["status"] = "failed"
        data["error"] = err_msg
        data["error_code"] = err_code
        data["error_summary"] = err_msg[:300]
        data["error_stage"] = "assessment_pipeline"
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        data["progress"] = {"message": f"Lỗi đánh giá: {err_msg[:150]}", "percent": 100}
        save_assessment(assessment_id, data)
        try:
            audit_service.record_assessment_failed(
                ctx=audit_ctx,
                error_type=type(e).__name__,
                error_stage="assessment_pipeline",
                message_redacted=err_msg,
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record audit failure event (non-fatal): {audit_err}")


def _get_request_user(authorization: Optional[str]) -> dict:
    """Extract authenticated user details from Bearer token if provided, else guest."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"id": "anonymous", "username": "guest", "role": "user", "full_name": "Khách"}
    try:
        from api.routes.auth import verify_token, user_store
        token = authorization.split(" ")[1]
        payload = verify_token(token)
        if payload and "sub" in payload:
            user = user_store.get_user_by_id(payload["sub"])
            if user:
                return {
                    "id": user["id"],
                    "username": user["username"],
                    "full_name": user.get("full_name"),
                    "role": user.get("role", "user")
                }
    except Exception as e:
        logger.warning(f"Auth token extraction warning: {e}")
    return {"id": "anonymous", "username": "guest", "role": "user", "full_name": "Khách"}


@router.post("/iso27001/assess")
async def assess(
    data: SystemInfo,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    from services.audit_service import audit_service, AuditContext

    current_user = _get_request_user(authorization)
    assessment_id = str(uuid.uuid4())
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    audit_ctx = AuditContext(assessment_id=assessment_id, run_id=run_id)

    raw_impl = data.implemented_controls
    if isinstance(raw_impl, dict):
        impl_controls = list(raw_impl.keys())
    elif isinstance(raw_impl, (list, tuple, set)):
        impl_controls = [str(c) for c in raw_impl]
    else:
        impl_controls = []

    ev_map = data.evidence_map if isinstance(data.evidence_map, dict) else {}

    system_data = {
        "assessment_standard": str(data.assessment_standard or "iso27001"),
        "organization": {
            "name": str(data.org_name or ""),
            "size": str(data.org_size or "medium"),
            "industry": str(data.industry or ""),
            "employees": data.employees or 0,
            "it_staff": data.it_staff or 0
        },
        "infrastructure": {
            "servers": data.servers if data.servers is not None else 0,
            "firewalls": str(data.firewalls) if data.firewalls is not None else "",
            "vpn": "Có" if data.vpn in (True, "True", "true", "Có", "có", 1, "1") else "Không",
            "cloud": str(data.cloud_provider or "Không sử dụng"),
            "antivirus": str(data.antivirus or "Không có"),
            "backup": str(data.backup_solution or "Không có"),
            "siem": str(data.siem or "Không có"),
            "network_diagram": str(data.network_diagram or "Không cung cấp")
        },
        "compliance": {
            "iso_status": str(data.iso_status or "Chưa triển khai"),
            "implemented_controls": impl_controls,
            "incidents_12m": data.incidents_12m or 0
        },
        "notes": str(data.notes or ""),
        "model_mode": str(data.model_mode or "local"),
        "selected_model": str(data.selected_model or "gemma4:latest"),
    }

    # Build evidence context from parsed file contents
    evidence_context = ""
    if ev_map:
        evidence_context = build_evidence_context_for_ai(ev_map)
        logger.info(f"[Assessment] Evidence map: {len(ev_map)} controls with evidence")

    # Tính compliance_percent sơ bộ ngay lúc tạo
    compliance_pct = 0.0
    try:
        from services.standard_service import load_standard
        from services.controls_catalog import calc_compliance, calc_tcvn_compliance
        custom_std = load_standard(data.assessment_standard)
        if data.assessment_standard == "tcvn11930":
            comp = calc_tcvn_compliance(impl_controls, custom_std)
            total_controls = comp.get("max_score", 34)
            compliance_pct = float(comp.get("percentage", 0.0))
        else:
            comp = calc_compliance(impl_controls, data.assessment_standard, custom_std)
            total_controls = comp.get("max_score", 93)
            compliance_pct = float(comp.get("percentage", 0.0))
    except Exception as calc_err:
        logger.warning(f"[Assessment] Preliminary compliance calc warning: {calc_err}")
        total_controls = 93 if data.assessment_standard == "iso27001" else 34
        compliance_pct = 0.0
    compliance_pct = round(min(100.0, max(0.0, compliance_pct)), 1)

    assessment_record = {
        "id": assessment_id,
        "run_id": run_id,
        "status": "pending",
        "system_info": system_data,
        "compliance_percent": compliance_pct,
        "model_mode": data.model_mode,
        "standard": data.assessment_standard,
        "evidence_attached": len(data.evidence_map) > 0,
        "created_by": current_user,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    # Record initial audit event
    audit_service.record_assessment_created(
        ctx=audit_ctx,
        standard=data.assessment_standard,
        model_mode=data.model_mode,
        org_name=data.org_name or "Tổ chức",
        implemented_controls_count=len(impl_controls),
        total_controls=total_controls,
        has_evidence=bool(data.evidence_map),
    )

    save_assessment(assessment_id, assessment_record)
    background_tasks.add_task(
        process_assessment_bg,
        assessment_id,
        system_data,
        data.model_mode,
        evidence_context,
        run_id,
    )

    return {
        "status": "accepted",
        "id": assessment_id,
        "run_id": run_id,
        "message": "Assessment task started in background",
        "created_by": current_user
    }


@router.get("/iso27001/assessments")
async def get_all_assessments(
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page (max 100)"),
    flat: bool = Query(default=False, description="Return flat array (no pagination envelope)"),
    authorization: Optional[str] = Header(None)
):
    """List assessments with RBAC user isolation.
    Admin sees all assessments. Regular users only see their own assessments.
    """
    current_user = _get_request_user(authorization)
    all_items = list_assessments()

    # Filter by user role: admin sees all, others only see their own (or anonymous if created as guest)
    if current_user["role"] != "admin":
        all_items = [
            item for item in all_items
            if item.get("created_by", {}).get("id") == current_user["id"]
            or (current_user["id"] == "anonymous" and item.get("created_by", {}).get("id") in (None, "anonymous"))
        ]

    total = len(all_items)
    total_pages = max(1, -(-total // page_size))

    start = (page - 1) * page_size
    end = start + page_size
    items = all_items[start:end]

    if flat:
        return items

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

@router.get("/iso27001/assessments/{assessment_id}/stream")
@router.get("/assessments/{assessment_id}/stream")
async def stream_assessment(assessment_id: str, authorization: Optional[str] = Header(None)):
    """Server-Sent Events (SSE) stream for real-time assessment chunk progress and completion."""
    _validate_path_id(assessment_id, "assessment_id")
    data = load_assessment(assessment_id)
    if not data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    async def event_generator():
        last_percent = -1
        last_message = ""
        last_status = ""
        max_duration = 900  # 15 minutes timeout
        started = time.time()

        while time.time() - started < max_duration:
            cur = load_assessment(assessment_id)
            if not cur:
                err_payload = json.dumps({"status": "failed", "error": "Assessment not found"}, ensure_ascii=False)
                yield f"event: error\ndata: {err_payload}\n\n"
                break

            status = cur.get("status", "pending")
            prog = cur.get("progress") or {}
            percent = prog.get("percent", 0)
            message = prog.get("message", "Đang xử lý...")

            if status == "completed":
                payload = {
                    "id": assessment_id,
                    "status": "completed",
                    "compliance_percent": cur.get("compliance_percent"),
                    "result": cur.get("result", {}),
                    "json_data": cur.get("json_data") or cur.get("result", {}).get("json_data"),
                    "standard": cur.get("standard") or cur.get("system_info", {}).get("assessment_standard"),
                    "org_name": cur.get("system_info", {}).get("organization", {}).get("name", ""),
                    "implemented_controls": cur.get("system_info", {}).get("compliance", {}).get("implemented_controls", []),
                }
                yield f"event: complete\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break

            if status == "failed":
                payload = {
                    "id": assessment_id,
                    "status": "failed",
                    "error": cur.get("error_summary") or cur.get("error") or "Đánh giá thất bại",
                    "error_code": cur.get("error_code", "ASSESSMENT_PIPELINE_ERROR"),
                }
                yield f"event: error\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                break

            if percent != last_percent or message != last_message or status != last_status:
                last_percent = percent
                last_message = message
                last_status = status
                payload = {
                    "id": assessment_id,
                    "status": status,
                    "percent": percent,
                    "message": message,
                }
                yield f"event: progress\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                yield ": ping\n\n"

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/iso27001/assessments/{assessment_id}")
@router.get("/assessments/{assessment_id}")
async def get_assessment(assessment_id: str, authorization: Optional[str] = Header(None)):
    _validate_path_id(assessment_id, "assessment_id")
    current_user = _get_request_user(authorization)
    data = load_assessment(assessment_id)
    if not data:
        return {"error": "Assessment not found", "status": "not_found"}

    # RBAC Access Control Check
    created_by_id = data.get("created_by", {}).get("id")
    if current_user["role"] != "admin" and created_by_id and created_by_id != current_user["id"] and created_by_id != "anonymous":
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền truy cập vào bài đánh giá của người dùng khác."
        )

    return data


@router.delete("/iso27001/assessments/{assessment_id}")
@router.delete("/assessments/{assessment_id}")
async def delete_assessment(assessment_id: str, authorization: Optional[str] = Header(None)):
    _validate_path_id(assessment_id, "assessment_id")
    current_user = _get_request_user(authorization)
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    
    if not os.path.exists(filepath):
        return {"status": "not_found", "message": "Assessment not found"}

    data = load_assessment(assessment_id)
    if data:
        created_by_id = data.get("created_by", {}).get("id")
        if current_user["role"] != "admin" and created_by_id and created_by_id != current_user["id"] and created_by_id != "anonymous":
            raise HTTPException(
                status_code=403,
                detail="Chỉ chủ sở hữu bài đánh giá hoặc Quản trị viên mới có quyền xóa."
            )

    try:
        # 1. Delete assessment JSON
        os.remove(filepath)

        # 2. Cascade delete any assessment-scoped evidence directory if exists
        assessment_ev_dir = os.path.join(EVIDENCE_DIR, assessment_id)
        if os.path.exists(assessment_ev_dir):
            import shutil
            shutil.rmtree(assessment_ev_dir, ignore_errors=True)

        return {"status": "success", "message": "Đã xóa hoàn toàn bài đánh giá và toàn bộ dữ liệu liên quan."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete: {str(e)}"}



@router.post("/iso27001/reindex")
async def reindex():
    """Re-index all ISO documents into the default 'iso_documents' collection."""
    vs = ChatService.get_vector_store()
    result = vs.index_documents(domain="iso_documents")
    return result


@router.post("/iso27001/reindex-domains")
async def reindex_domains():
    """Re-index each standard's markdown files into its own domain collection.

    Reads all .md files from /data/iso_documents and routes each file
    to its matching domain collection based on filename prefix.
    """
    from repositories.vector_store import VectorStore
    from pathlib import Path

    DOMAIN_FILE_MAP = {
        "iso27001":  ["iso27001_annex_a.md", "iso27002_2022.md"],
        "tcvn11930": ["tcvn_11930_2017.md", "nd85_2016_cap_do_httt.md"],
        "nd13":      ["nghi_dinh_13_2023_bvdlcn.md", "luat_an_ninh_mang_2018.md"],
        "nist_csf":  ["nist_csf_2.md", "nist_sp800_53.md"],
        "pci_dss":   ["pci_dss_4.md"],
        "hipaa":     ["hipaa_security_rule.md"],
        "gdpr":      ["gdpr_compliance.md"],
        "soc2":      ["soc2_trust_criteria.md"],
    }

    docs_dir = Path(os.getenv("ISO_DOCS_PATH", "/data/iso_documents"))
    vs = VectorStore()
    results = {}

    for domain, filenames in DOMAIN_FILE_MAP.items():
        chunks_added = 0
        coll = vs.get_collection(domain)
        # Clear existing chunks for this domain
        try:
            existing = coll.get()
            if existing and existing["ids"]:
                coll.delete(ids=existing["ids"])
        except Exception:
            pass

        all_chunks, all_ids, all_metas = [], [], []
        for fname in filenames:
            fpath = docs_dir / fname
            if not fpath.exists():
                logger.warning(f"[ReindexDomains] File not found: {fpath}")
                continue
            content = fpath.read_text(encoding="utf-8")
            file_chunks = vs._chunk_text(content)
            first_line = content.split('\n')[0].strip().lstrip('#').strip()
            for i, chunk in enumerate(file_chunks):
                all_chunks.append(chunk)
                all_ids.append(f"{fpath.stem}_{i}")
                all_metas.append({
                    "source": fpath.stem,
                    "file": fname,
                    "chunk_index": i,
                    "total_chunks": len(file_chunks),
                    "doc_title": first_line[:100],
                    "domain": domain,
                })

        if all_chunks:
            for i in range(0, len(all_chunks), 100):
                end = min(i + 100, len(all_chunks))
                coll.add(documents=all_chunks[i:end], ids=all_ids[i:end], metadatas=all_metas[i:end])
            chunks_added = len(all_chunks)
            vs._initialized[domain] = True

        results[domain] = {"files": len(filenames), "chunks": chunks_added}
        logger.info(f"[ReindexDomains] {domain}: {chunks_added} chunks from {len(filenames)} files")

    return {"status": "ok", "domains": results}


@router.get("/iso27001/chromadb/stats")
async def chromadb_stats():
    try:
        vs = ChatService.get_vector_store()
        # Use default collection for backward-compatible stats
        default_coll = vs.get_collection("iso_documents")
        count = default_coll.count()
        metadata = default_coll.metadata

        # Collect stats from all known domain collections
        KNOWN_DOMAINS = ["iso_documents", "iso27001", "tcvn11930", "nd13", "nist_csf", "pci_dss", "hipaa", "gdpr", "soc2"]
        domain_stats = {}
        for domain in KNOWN_DOMAINS:
            try:
                d_coll = vs.get_collection(domain)
                d_count = d_coll.count()
                if d_count > 0:
                    domain_stats[domain] = d_count
            except Exception:
                pass

        docs_dir = os.getenv("ISO_DOCS_PATH", "/data/iso_documents")
        files = []
        docs_path = Path(docs_dir)
        if docs_path.exists():
            for f in docs_path.glob("*.md"):
                files.append({"name": f.name, "size_bytes": f.stat().st_size})

        return {
            "status": "ok",
            "total_chunks": count,
            "total_files": len(files),
            "files": files,
            "collection_name": "iso_documents",
            "metric": metadata.get("hnsw:space", "cosine"),
            "domain_collections": domain_stats,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/iso27001/chromadb/search")
async def chromadb_search(query: dict):
    try:
        vs = ChatService.get_vector_store()
        q = query.get("query", "")
        top_k = query.get("top_k", 3)
        if not q:
            return {"status": "error", "message": "Missing query parameter"}
        results = vs.search(q, top_k=top_k)
        return {"status": "ok", "query": q, "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Batch Evidence Ingest & Auto-Mapper ──────────────────────────────


@router.post("/iso27001/evidence/batch-ingest")
@router.post("/evidence/batch-ingest")
async def batch_ingest_evidence(request: Request, authorization: Optional[str] = Header(None)):
    """Batch upload server scans, logs, policies, images (OCR), and evidence documents.
    Processes files sequentially through the unified evidence parser with partial success resilience.
    """
    from services.evidence_mapper import map_evidence_to_controls
    from services.evidence_parser import parse_evidence_file, MAX_EVIDENCE_SIZE_BYTES, SUPPORTED_EXTENSIONS

    try:
        form = await request.form()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không thể đọc multipart form data: {str(e)}")

    uploaded_files: List[Any] = []
    # Collect files from any form key (e.g. 'files', 'file', 'attachments')
    for key, value in form.multi_items():
        if hasattr(value, "filename") and value.filename:
            uploaded_files.append(value)
        elif hasattr(value, "file") and hasattr(value, "filename"):
            uploaded_files.append(value)

    if not uploaded_files:
        raise HTTPException(status_code=400, detail="Không tìm thấy tệp đính kèm nào được gửi lên.")

    current_user = _get_request_user(authorization)
    mapped_controls: Dict[str, List[dict]] = {}
    detected_hosts: List[dict] = []
    processed_files: List[dict] = []
    errors: List[str] = []

    ip_regex = _re_val.compile(r'\b(?:10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2})\b')
    hostname_regex = _re_val.compile(r'(?:Host Name|Computer Name|Tên máy chủ)[:\s]+([a-zA-Z0-9_\-]+)', _re_val.IGNORECASE)
    os_regex = _re_val.compile(r'(?:OS Name|Operating System|Hệ điều hành)[:\s]+([^\r\n]+)', _re_val.IGNORECASE)

    temp_dir = os.path.join(EVIDENCE_DIR, "_batch_temp")
    os.makedirs(temp_dir, exist_ok=True)

    for file in uploaded_files:
        if not file.filename:
            continue
        try:
            content = await file.read()
            # Parse with universal evidence parser
            parse_res = parse_evidence_file(content, file.filename)
            text_content = parse_res.get("parsed_text", "")
            file_status = parse_res.get("status", "success")
            fact_card = parse_res.get("fact_card") or {}
            host_meta = fact_card.get("host_metadata") or {}

            if file_status in ("unsupported", "failed") and parse_res.get("error_code") == "UNSUPPORTED_FORMAT":
                errors.append(f"{file.filename}: {parse_res.get('error_message')}")
                processed_files.append({
                    "filename": file.filename,
                    "size_bytes": len(content),
                    "char_count": 0,
                    "page_count": 0,
                    "ocr_applied": False,
                    "mapped_controls": [],
                    "status": "unsupported",
                    "error_code": parse_res.get("error_code"),
                    "error_message": parse_res.get("error_message"),
                })
                continue

            if len(content) > MAX_EVIDENCE_SIZE_BYTES:
                msg = f"Kích thước vượt quá {MAX_EVIDENCE_SIZE_BYTES // (1024*1024)}MB."
                errors.append(f"{file.filename}: {msg}")
                processed_files.append({
                    "filename": file.filename,
                    "size_bytes": len(content),
                    "char_count": 0,
                    "page_count": 0,
                    "ocr_applied": False,
                    "mapped_controls": [],
                    "status": "failed",
                    "error_code": "FILE_TOO_LARGE",
                    "error_message": msg,
                })
                continue

            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safe_name = f"{ts}_{file.filename}"

            # Host detection from fact_card and log content
            card_ips = host_meta.get("ip_addresses") or []
            found_ips = card_ips or ip_regex.findall(text_content)
            fn_ips = ip_regex.findall(file.filename)
            primary_ip = fn_ips[0] if fn_ips else (found_ips[0] if found_ips else None)

            card_host = host_meta.get("hostname")
            found_hostnames = hostname_regex.findall(text_content)
            detected_hostname = card_host or (found_hostnames[0] if found_hostnames else None)
            if not detected_hostname and primary_ip:
                detected_hostname = file.filename.rsplit(".", 1)[0]

            card_os = host_meta.get("os_name")
            found_os = os_regex.findall(text_content)
            detected_os = card_os or (found_os[0].strip() if found_os else None)

            host_info = {
                "source_file": file.filename,
                "ip": primary_ip,
                "hostname": detected_hostname,
                "os": detected_os,
                "is_eol": host_meta.get("is_eol", False)
            }
            if host_info["ip"] or host_info["hostname"]:
                detected_hosts.append(host_info)

            # Map to controls: combine keyword mapper with Agent 1 FactCard
            control_scores = map_evidence_to_controls(file.filename, text_content)

            for ctrl_id in fact_card.get("relevant_controls", []):
                control_scores[ctrl_id] = max(control_scores.get(ctrl_id, 0.0), 0.85)

            for sat in fact_card.get("compliance_readiness", {}).get("satisfied_controls", []):
                cid = sat.get("control_id") if isinstance(sat, dict) else str(sat)
                if cid:
                    control_scores[cid] = max(control_scores.get(cid, 0.0), 0.90)

            for fail in fact_card.get("compliance_readiness", {}).get("failing_controls", []):
                cid = fail.get("control_id") if isinstance(fail, dict) else str(fail)
                if cid:
                    control_scores[cid] = max(control_scores.get(cid, 0.0), 0.90)

            saved_to_controls = []

            for ctrl_id, score in control_scores.items():
                if score >= 0.35:
                    ctrl_dir = os.path.join(EVIDENCE_DIR, ctrl_id.replace(".", "_"))
                    os.makedirs(ctrl_dir, exist_ok=True)
                    dest_path = os.path.join(ctrl_dir, safe_name)
                    with open(dest_path, "wb") as f:
                        f.write(content)

                    if ctrl_id not in mapped_controls:
                        mapped_controls[ctrl_id] = []
                    
                    mapped_controls[ctrl_id].append({
                        "filename": safe_name,
                        "original_name": file.filename,
                        "confidence": score,
                        "size_bytes": len(content),
                        "char_count": parse_res.get("char_count", len(text_content)),
                        "ocr_applied": parse_res.get("ocr_applied", False),
                        "preview": text_content[:200]
                    })
                    saved_to_controls.append(ctrl_id)

            if not saved_to_controls:
                unassigned_dir = os.path.join(EVIDENCE_DIR, "_unassigned")
                os.makedirs(unassigned_dir, exist_ok=True)
                with open(os.path.join(unassigned_dir, safe_name), "wb") as f:
                    f.write(content)

            processed_files.append({
                "filename": file.filename,
                "size_bytes": len(content),
                "char_count": parse_res.get("char_count", len(text_content)),
                "page_count": parse_res.get("page_count", 1),
                "ocr_applied": parse_res.get("ocr_applied", False),
                "mapped_controls": saved_to_controls,
                "status": "success"
            })

        except Exception as file_err:
            logger.error(f"[BatchIngest] Error processing {file.filename}: {file_err}", exc_info=True)
            errors.append(f"{file.filename}: {str(file_err)}")
            processed_files.append({
                "filename": file.filename,
                "size_bytes": 0,
                "char_count": 0,
                "page_count": 0,
                "ocr_applied": False,
                "mapped_controls": [],
                "status": "failed",
                "error_code": "PARSE_ERROR",
                "error_message": str(file_err)
            })

    # Cleanup temporary directory
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    unique_hosts = []
    seen_identifiers = set()
    for h in detected_hosts:
        ident = h.get("ip") or h.get("hostname")
        if ident and ident not in seen_identifiers:
            seen_identifiers.add(ident)
            unique_hosts.append(h)

    suggested_controls = list(mapped_controls.keys())
    success_count = len([f for f in processed_files if f.get("status") == "success"])

    return {
        "status": "success",
        "processed_count": len(processed_files),
        "files": processed_files,
        "mapped_controls": mapped_controls,
        "suggested_implemented_controls": suggested_controls,
        "detected_hosts": unique_hosts,
        "errors": errors,
        "summary": {
            "total_files": len(uploaded_files),
            "processed_successfully": success_count,
            "failed_count": len(uploaded_files) - success_count,
            "matched_controls_count": len(suggested_controls),
            "detected_hosts_count": len(unique_hosts)
        }
    }


@router.post("/iso27001/evidence/{control_id}")
async def upload_evidence(control_id: str, file: UploadFile = File(...)):
    """Upload evidence file for a specific control."""
    _validate_path_id(control_id, "control_id")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EVIDENCE_EXT:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EVIDENCE_EXT)}")

    content = await file.read()
    if len(content) > MAX_EVIDENCE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max: {MAX_EVIDENCE_SIZE // (1024*1024)}MB")

    # Create control-specific directory
    ctrl_dir = os.path.join(EVIDENCE_DIR, control_id.replace(".", "_"))
    os.makedirs(ctrl_dir, exist_ok=True)

    # Save with timestamp prefix to avoid overwrite
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = f"{ts}_{file.filename}"
    filepath = os.path.join(ctrl_dir, safe_name)

    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "status": "success",
        "control_id": control_id,
        "filename": safe_name,
        "size_bytes": len(content),
        "path": f"/api/iso27001/evidence/{control_id}/{safe_name}",
    }


@router.get("/iso27001/evidence/{control_id}")
async def list_evidence(control_id: str):
    """List all evidence files for a control."""
    _validate_path_id(control_id, "control_id")
    ctrl_dir = os.path.join(EVIDENCE_DIR, control_id.replace(".", "_"))
    if not os.path.exists(ctrl_dir):
        return {"control_id": control_id, "files": []}

    files = []
    for filename in sorted(os.listdir(ctrl_dir)):
        filepath = os.path.join(ctrl_dir, filename)
        stat = os.stat(filepath)
        files.append({
            "filename": filename,
            "size_bytes": stat.st_size,
            "uploaded_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "download_url": f"/api/iso27001/evidence/{control_id}/{filename}",
        })

    return {"control_id": control_id, "files": files}


@router.get("/iso27001/evidence/{control_id}/{filename}")
async def download_evidence(control_id: str, filename: str):
    """Download a specific evidence file."""
    _validate_path_id(control_id, "control_id")
    _validate_path_id(filename.replace(".", "_"), "filename")
    ctrl_dir = os.path.join(EVIDENCE_DIR, control_id.replace(".", "_"))
    filepath = os.path.join(ctrl_dir, filename)
    # Resolve the real path and confirm it stays within the evidence directory.
    real_base = os.path.realpath(EVIDENCE_DIR)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_base + os.sep):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(filepath, filename=filename)


@router.delete("/iso27001/evidence/{control_id}/{filename}")
async def delete_evidence(control_id: str, filename: str):
    """Delete a specific evidence file."""
    _validate_path_id(control_id, "control_id")
    _validate_path_id(filename.replace(".", "_"), "filename")
    ctrl_dir = os.path.join(EVIDENCE_DIR, control_id.replace(".", "_"))
    filepath = os.path.join(ctrl_dir, filename)
    # Resolve the real path and confirm it stays within the evidence directory.
    real_base = os.path.realpath(EVIDENCE_DIR)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_base + os.sep):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    os.remove(filepath)
    return {"status": "success", "message": f"Deleted {filename}"}


@router.get("/iso27001/evidence-summary")
async def get_all_evidence_summary():
    """Get summary of all uploaded evidence across all controls."""
    summary = {}
    if not os.path.exists(EVIDENCE_DIR):
        return {"controls": {}, "total_files": 0}

    total = 0
    for ctrl_folder in os.listdir(EVIDENCE_DIR):
        ctrl_path = os.path.join(EVIDENCE_DIR, ctrl_folder)
        if os.path.isdir(ctrl_path):
            ctrl_id = ctrl_folder.replace("_", ".")
            files = [f for f in os.listdir(ctrl_path) if os.path.isfile(os.path.join(ctrl_path, f))]
            if files:
                summary[ctrl_id] = len(files)
                total += len(files)

    return {"controls": summary, "total_files": total}


@router.get("/iso27001/evidence/{control_id}/{filename}/preview")
async def preview_evidence(control_id: str, filename: str):
    """Parse and return text content of an evidence file for preview."""
    _validate_path_id(control_id, "control_id")
    _validate_path_id(filename.replace(".", "_"), "filename")
    ctrl_dir = os.path.join(EVIDENCE_DIR, control_id.replace(".", "_"))
    filepath = os.path.join(ctrl_dir, filename)
    # Resolve the real path and confirm it stays within the evidence directory.
    real_base = os.path.realpath(EVIDENCE_DIR)
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(real_base + os.sep):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(filename)[1].lower()
    content = parse_evidence_file_content(filepath)
    is_image = ext in {".png", ".jpg", ".jpeg"}

    return {
        "control_id": control_id,
        "filename": filename,
        "content": content,
        "content_type": "image" if is_image else "text",
        "file_ext": ext,
        "size_bytes": os.path.getsize(filepath),
        "download_url": f"/api/iso27001/evidence/{control_id}/{filename}"
    }


@router.post("/iso27001/assessments/{assessment_id}/export-pdf")
async def export_pdf(assessment_id: str):
    """Generate professional Vietnamese A4 PDF from assessment report using weasyprint.
    Includes national administrative letterhead, audit metadata table, stat cards,
    weight breakdown, complete healed report, and official signature blocks.
    Falls back to HTML file if weasyprint is not available."""
    _validate_path_id(assessment_id, "assessment_id")
    data = load_assessment(assessment_id)
    if not data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Assessment not completed yet")

    raw_report = data.get("result", {}).get("report", "")
    if not raw_report:
        raise HTTPException(status_code=400, detail="No report content")

    sys_info = data.get("system_info", {})
    org_name = sys_info.get("organization", {}).get("name") or sys_info.get("org_name", "Tổ chức Đánh giá")
    industry = sys_info.get("organization", {}).get("industry") or sys_info.get("industry", "Công nghệ & Dịch vụ số")
    std = data.get("standard", "iso27001")
    std_name = "ISO 27001:2022" if std == "iso27001" else "TCVN 11930:2017" if std == "tcvn11930" else std
    pct = data.get("compliance_percent", 0.0)
    created = data.get("created_at", "")

    json_data = data.get("json_data") or data.get("result", {}).get("json_data", {})
    scope_desc = (
        sys_info.get("scope_description")
        or sys_info.get("infrastructure", {}).get("cloud")
        or "Toàn bộ hạ tầng mạng, máy chủ cơ sở dữ liệu, ứng dụng nghiệp vụ và quy trình vận hành an toàn thông tin."
    )

    # Automatically heal truncated report if Section 5 or b) Top 3 was cut off
    report = ChatService.ensure_complete_report(
        markdown_report=raw_report,
        percentage=pct,
        org_name=org_name,
        std_name=std_name,
        industry=industry,
        json_data=json_data,
    )

    # Compute risk & gap metrics
    wb = json_data.get("weight_breakdown", {})
    risk_sum = json_data.get("risk_summary", {})

    crit_total = wb.get("critical", {}).get("total", 0)
    crit_impl = wb.get("critical", {}).get("implemented", 0)
    crit_gaps = (crit_total - crit_impl) if crit_total else risk_sum.get("critical_gaps", 0)

    high_total = wb.get("high", {}).get("total", 0)
    high_impl = wb.get("high", {}).get("implemented", 0)
    high_gaps = (high_total - high_impl) if high_total else risk_sum.get("high_gaps", 0)

    med_total = wb.get("medium", {}).get("total", 0)
    med_impl = wb.get("medium", {}).get("implemented", 0)
    med_gaps = (med_total - med_impl) if med_total else risk_sum.get("medium_gaps", 0)

    low_total = wb.get("low", {}).get("total", 0)
    low_impl = wb.get("low", {}).get("implemented", 0)
    low_gaps = (low_total - low_impl) if low_total else risk_sum.get("low_gaps", 0)

    total_gaps = crit_gaps + high_gaps + med_gaps + low_gaps
    if total_gaps == 0:
        total_gaps = risk_sum.get("total_gaps", len(json_data.get("top_gaps", [])))

    doc_date = created[:10] if created else datetime.now(timezone.utc).strftime("%d/%m/%Y")
    now_viet_date = datetime.now(timezone.utc).strftime("ngày %d tháng %m năm %Y")
    doc_number = f"AUDIT-{assessment_id[:8].upper()}/BC-ATTT"

    pct_color = '#16a34a' if pct >= 80 else '#2563eb' if pct >= 50 else '#d97706' if pct >= 25 else '#dc2626'

    # Convert markdown to clean HTML
    import re as _re
    html_body = report
    # Strip markdown preambles or duplicates of the title if repeated
    html_body = _re.sub(r'^#\s+Báo\s+cáo[^\n]*\n+', '', html_body, flags=_re.IGNORECASE)
    html_body = _re.sub(r'^#{1}\s+(.+)$', r'<h1>\1</h1>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'^#{2}\s+(.+)$', r'<h2>\1</h2>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'^#{3}\s+(.+)$', r'<h3>\1</h3>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'^#{4}\s+(.+)$', r'<h4>\1</h4>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
    html_body = _re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_body)
    html_body = _re.sub(r'^\s*[-•*]\s+(.+)$', r'<li>\1</li>', html_body, flags=_re.MULTILINE)
    html_body = _re.sub(r'(<li>.*?</li>\n?)+', lambda m: f'<ul>{m.group()}</ul>', html_body, flags=_re.DOTALL)
    html_body = _re.sub(r'^---+$', '<hr>', html_body, flags=_re.MULTILINE)

    def convert_md_table(match):
        lines = match.group().strip().split('\n')
        if len(lines) < 2:
            return match.group()
        headers = [h.strip() for h in lines[0].strip('|').split('|')]
        rows_html = '<tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr>\n'
        for line in lines[2:]:
            cells = [c.strip() for c in line.strip('|').split('|')]
            rows_html += '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>\n'
        return f'<div class="table-wrap"><table>{rows_html}</table></div>'

    html_body = _re.sub(r'(\|.+\|(?:\n\|[-:| ]+\|)(?:\n\|.+\|)+)', convert_md_table, html_body)
    html_body = html_body.replace('\n\n', '</p><p>')

    aid_str = data.get("assessment_id") or assessment_id
    run_id = data.get("run_id") or json_data.get("run_id") or "run_default"
    code_ver = data.get("code_version") or json_data.get("code_version") or "v1.2.0-rel"

    wb_table_html = ""
    if wb:
        wb_table_html = f"""
        <div class="section-box">
          <div class="table-caption">Bảng phân bổ tuân thủ theo trọng số kiểm soát</div>
          <table class="wb-table">
            <thead>
              <tr>
                <th>Mức độ ưu tiên</th>
                <th style="text-align:center;">Tổng số Controls</th>
                <th style="text-align:center;">Đã đạt</th>
                <th style="text-align:center;">Khoảng trống (GAP)</th>
                <th style="text-align:center;">Tỷ lệ tuân thủ</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong style="color: #dc2626;">Critical (Trọng yếu)</strong></td>
                <td style="text-align:center;">{crit_total}</td>
                <td style="text-align:center; color:#16a34a; font-weight:bold;">{crit_impl}</td>
                <td style="text-align:center; color:#dc2626; font-weight:bold;">{crit_gaps}</td>
                <td style="text-align:center; font-weight:bold;">{wb.get('critical', {}).get('percent', 0)}%</td>
              </tr>
              <tr>
                <td><strong style="color: #ea580c;">High (Cao)</strong></td>
                <td style="text-align:center;">{high_total}</td>
                <td style="text-align:center; color:#16a34a; font-weight:bold;">{high_impl}</td>
                <td style="text-align:center; color:#ea580c; font-weight:bold;">{high_gaps}</td>
                <td style="text-align:center; font-weight:bold;">{wb.get('high', {}).get('percent', 0)}%</td>
              </tr>
              <tr>
                <td><strong style="color: #ca8a04;">Medium (Trung bình)</strong></td>
                <td style="text-align:center;">{med_total}</td>
                <td style="text-align:center; color:#16a34a; font-weight:bold;">{med_impl}</td>
                <td style="text-align:center; color:#ca8a04; font-weight:bold;">{med_gaps}</td>
                <td style="text-align:center; font-weight:bold;">{wb.get('medium', {}).get('percent', 0)}%</td>
              </tr>
              <tr>
                <td><strong style="color: #64748b;">Low (Thấp)</strong></td>
                <td style="text-align:center;">{low_total}</td>
                <td style="text-align:center; color:#16a34a; font-weight:bold;">{low_impl}</td>
                <td style="text-align:center; color:#64748b; font-weight:bold;">{low_gaps}</td>
                <td style="text-align:center; font-weight:bold;">{wb.get('low', {}).get('percent', 0)}%</td>
              </tr>
            </tbody>
          </table>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Báo cáo Đánh giá An toàn Thông tin - {org_name}</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 18mm 15mm 20mm 15mm;
    @bottom-left {{
      content: "Báo cáo Đánh giá ATTT — CyberAI Platform";
      font-size: 8.5pt;
      color: #64748b;
      font-style: italic;
    }}
    @bottom-right {{
      content: "Trang " counter(page) " / " counter(pages);
      font-size: 8.5pt;
      color: #64748b;
      font-weight: bold;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Times New Roman', Times, serif, 'Segoe UI', Arial;
    margin: 0;
    padding: 0;
    color: #0f172a;
    line-height: 1.6;
    font-size: 11.5pt;
  }}

  /* Administrative Letterhead Header */
  .letterhead-tbl {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 22px;
    border: none;
  }}
  .letterhead-tbl td {{
    border: none;
    padding: 0;
    vertical-align: top;
  }}
  .lh-left {{
    width: 48%;
    text-align: center;
  }}
  .lh-org {{
    font-size: 10.5pt;
    font-weight: bold;
    text-transform: uppercase;
    color: #1e293b;
  }}
  .lh-sub {{
    font-size: 9.5pt;
    color: #334155;
    margin-top: 2px;
  }}
  .lh-num {{
    font-size: 9.5pt;
    font-style: italic;
    color: #475569;
    margin-top: 4px;
  }}
  .lh-right {{
    width: 52%;
    text-align: center;
  }}
  .lh-country {{
    font-size: 11pt;
    font-weight: bold;
    text-transform: uppercase;
    color: #0f172a;
  }}
  .lh-motto {{
    font-size: 11pt;
    font-weight: bold;
    color: #0f172a;
  }}
  .lh-line {{
    width: 140px;
    height: 1px;
    background: #0f172a;
    margin: 3px auto 6px auto;
  }}
  .lh-date {{
    font-size: 10pt;
    font-style: italic;
    color: #334155;
  }}

  /* Main Title */
  .report-title-box {{
    text-align: center;
    margin: 18px 0 16px 0;
  }}
  .report-title {{
    font-size: 18pt;
    font-weight: bold;
    text-transform: uppercase;
    color: #1e3a8a;
    letter-spacing: 0.5px;
    margin: 0;
  }}
  .report-subtitle {{
    font-size: 11.5pt;
    font-style: italic;
    color: #475569;
    margin-top: 4px;
  }}

  .disclaimer-banner {{
    background: #fefce8;
    border: 1px solid #fef08a;
    border-left: 4px solid #eab308;
    padding: 8px 12px;
    margin: 12px 0 16px 0;
    font-size: 9.5pt;
    font-style: italic;
    color: #854d0e;
    border-radius: 4px;
  }}

  /* Administrative Info Grid */
  .admin-info-tbl {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
    font-size: 10pt;
  }}
  .admin-info-tbl td {{
    border: 1px solid #cbd5e1;
    padding: 6px 10px;
    vertical-align: middle;
  }}
  .admin-info-tbl .lbl {{
    background: #f8fafc;
    font-weight: bold;
    color: #334155;
    width: 22%;
  }}
  .admin-info-tbl .val {{
    color: #0f172a;
    width: 28%;
  }}

  /* Stat Metric Cards */
  .stats-grid {{
    display: table;
    width: 100%;
    margin: 16px 0 24px 0;
    table-layout: fixed;
  }}
  .stat-card {{
    display: table-cell;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 12px 10px;
    text-align: center;
    margin: 0 4px;
  }}
  .stat-card .val {{
    font-size: 20pt;
    font-weight: bold;
    line-height: 1.1;
  }}
  .stat-card .lbl {{
    font-size: 9pt;
    color: #64748b;
    margin-top: 4px;
    text-transform: uppercase;
    font-weight: bold;
  }}

  /* Headings in body */
  h1 {{
    font-size: 13pt;
    font-weight: bold;
    color: #1e3a8a;
    border-bottom: 1.5px solid #cbd5e1;
    padding-bottom: 5px;
    margin-top: 24px;
    margin-bottom: 12px;
    page-break-after: avoid;
  }}
  h2 {{
    font-size: 12pt;
    font-weight: bold;
    color: #0369a1;
    margin-top: 20px;
    margin-bottom: 10px;
    page-break-after: avoid;
  }}
  h3 {{
    font-size: 11pt;
    font-weight: bold;
    color: #1e293b;
    margin-top: 14px;
    margin-bottom: 6px;
    page-break-after: avoid;
  }}
  h4 {{
    font-size: 10.5pt;
    font-weight: bold;
    color: #334155;
    margin-top: 10px;
  }}

  p {{
    margin: 6px 0 10px 0;
    text-align: justify;
  }}

  /* Tables in report */
  .table-wrap {{
    margin: 12px 0;
    page-break-inside: avoid;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9.5pt;
  }}
  thead {{
    display: table-header-group;
  }}
  tr {{
    page-break-inside: avoid;
  }}
  th, td {{
    border: 1px solid #94a3b8;
    padding: 6px 8px;
    vertical-align: middle;
  }}
  th {{
    background: #e2e8f0;
    font-weight: bold;
    color: #1e293b;
    text-align: left;
  }}
  tr:nth-child(even) td {{
    background: #f8fafc;
  }}
  .table-caption {{
    font-size: 10pt;
    font-weight: bold;
    font-style: italic;
    color: #334155;
    margin-bottom: 5px;
  }}

  ul, ol {{
    margin: 6px 0 10px 0;
    padding-left: 24px;
  }}
  li {{
    margin-bottom: 4px;
  }}

  blockquote {{
    border-left: 3px solid #2563eb;
    margin: 10px 0;
    padding: 6px 14px;
    background: #f0fdf4;
    color: #166534;
    font-size: 10.5pt;
  }}

  hr {{
    border: none;
    border-top: 1px solid #cbd5e1;
    margin: 16px 0;
  }}

  /* Signatures Block */
  .signatures-wrap {{
    display: table;
    width: 100%;
    margin-top: 36px;
    page-break-inside: avoid;
    table-layout: fixed;
  }}
  .sig-col {{
    display: table-cell;
    width: 33.33%;
    text-align: center;
    vertical-align: top;
    padding: 0 8px;
  }}
  .sig-title {{
    font-size: 10pt;
    font-weight: bold;
    text-transform: uppercase;
    color: #0f172a;
  }}
  .sig-sub {{
    font-size: 8.5pt;
    font-style: italic;
    color: #64748b;
    margin-top: 2px;
  }}
  .sig-space {{
    height: 60px;
  }}
  .sig-name {{
    font-size: 10pt;
    font-weight: bold;
    color: #1e293b;
  }}

  .footer-audit {{
    margin-top: 24px;
    padding-top: 8px;
    border-top: 1px solid #e2e8f0;
    font-size: 8.5pt;
    color: #94a3b8;
    text-align: center;
    font-style: italic;
  }}
</style>
</head>
<body>

<!-- 1. Administrative Letterhead -->
<table class="letterhead-tbl">
  <tr>
    <td class="lh-left">
      <div class="lh-org">HỆ THỐNG ĐÁNH GIÁ AN TOÀN THÔNG TIN CYBERAI</div>
      <div class="lh-sub">Trung tâm Đánh giá & Thẩm định Tuân thủ</div>
      <div class="lh-num">Số: {doc_number}</div>
    </td>
    <td class="lh-right">
      <div class="lh-country">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
      <div class="lh-motto">Độc lập - Tự do - Hạnh phúc</div>
      <div class="lh-line"></div>
      <div class="lh-date">Hà Nội, {now_viet_date}</div>
    </td>
  </tr>
</table>

<!-- 2. Main Title -->
<div class="report-title-box">
  <h1 class="report-title">Báo cáo đánh giá an toàn thông tin</h1>
  <div class="report-subtitle">Tiêu chuẩn đối soát: {std_name}</div>
</div>

<!-- Mandatory Disclaimer -->
<div class="disclaimer-banner">
  Kết quả được sinh để hỗ trợ tự đánh giá; cần chuyên gia an toàn thông tin xác minh trước khi sử dụng làm căn cứ quyết định hoặc kiểm toán.
</div>

<!-- 3. Administrative Metadata Table -->
<table class="admin-info-tbl">
  <tr>
    <td class="lbl">Tổ chức được đánh giá:</td>
    <td class="val"><strong>{org_name}</strong></td>
    <td class="lbl">Lĩnh vực hoạt động:</td>
    <td class="val">{industry}</td>
  </tr>
  <tr>
    <td class="lbl">Mã đánh giá & Run ID:</td>
    <td class="val">ID: {aid_str[:12]} | Run: {run_id}</td>
    <td class="lbl">Phiên bản hệ thống:</td>
    <td class="val">{code_ver}</td>
  </tr>
  <tr>
    <td class="lbl">Tỷ lệ tuân thủ có trọng số:</td>
    <td class="val"><strong style="color: {pct_color}; font-size: 12pt;">{pct}%</strong></td>
    <td class="lbl">Chuyên gia đối soát:</td>
    <td class="val">Hội đồng Kiểm toán ATTT</td>
  </tr>
  <tr>
    <td class="lbl">Phạm vi hệ thống:</td>
    <td class="val" colspan="3">{scope_desc}</td>
  </tr>
</table>

<!-- 4. Metric Cards -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="val" style="color: {pct_color};">{pct}%</div>
    <div class="lbl">Mức độ tuân thủ có trọng số</div>
  </div>
  <div class="stat-card">
    <div class="val" style="color: #dc2626;">{crit_gaps}</div>
    <div class="lbl">Rủi ro mức Critical</div>
  </div>
  <div class="stat-card">
    <div class="val" style="color: #ea580c;">{high_gaps}</div>
    <div class="lbl">Rủi ro mức High</div>
  </div>
  <div class="stat-card">
    <div class="val" style="color: #2563eb;">{total_gaps}</div>
    <div class="lbl">Tổng số khoảng trống (GAP)</div>
  </div>
</div>

<!-- 5. Weight Breakdown Table -->
{wb_table_html}

<!-- 6. Complete Healed Markdown Report Body -->
<div class="report-content">
  {html_body}
</div>

<!-- 7. Signatures & Approvals -->
<div class="signatures-wrap">
  <div class="sig-col">
    <div class="sig-title">ĐẠI DIỆN ĐƠN VỊ ĐƯỢC ĐÁNH GIÁ</div>
    <div class="sig-sub">(Ký, ghi rõ họ tên & đóng dấu)</div>
    <div class="sig-space"></div>
    <div class="sig-name">Đại diện Ban Giám đốc</div>
  </div>
  <div class="sig-col">
    <div class="sig-title">TRƯỞNG ĐOÀN KIỂM TOÁN (LEAD AUDITOR)</div>
    <div class="sig-sub">(Ký và xác nhận kết quả)</div>
    <div class="sig-space"></div>
    <div class="sig-name">Hội đồng Kiểm toán ATTT</div>
  </div>
  <div class="sig-col">
    <div class="sig-title">GIÁM ĐỐC AN TOÀN THÔNG TIN (CISO)</div>
    <div class="sig-sub">(Phê duyệt & giám sát thực thi)</div>
    <div class="sig-space"></div>
    <div class="sig-name">CyberAI Security Assurance</div>
  </div>
</div>

<div class="footer-audit">
  Báo cáo được hỗ trợ lập và ghi nhận vết kỹ thuật bởi CyberAI Assessment Platform · Mã hồ sơ: {aid_str} · Ngày kết xuất: {doc_date}
</div>

</body>
</html>"""

    pdf_filename = f"report_{assessment_id[:8]}_{org_name.replace(' ', '_')[:30]}.pdf"
    html_filename = f"report_{assessment_id[:8]}.html"
    pdf_path = os.path.join(EXPORTS_DIR, pdf_filename)
    html_path = os.path.join(EXPORTS_DIR, html_filename)

    # Save HTML file
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    import hashlib
    from services.audit_service import audit_service, AuditContext
    audit_ctx = AuditContext(
        assessment_id=aid_str,
        run_id=run_id,
        code_version=code_ver
    )

    # Try weasyprint for PDF
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(pdf_path)
        with open(pdf_path, "rb") as pf:
            pdf_bytes = pf.read()
        file_sz = len(pdf_bytes)
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        audit_service.record_report_exported(ctx=audit_ctx, export_format="pdf", file_size_bytes=file_sz, file_hash=file_hash)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=pdf_filename,
        )
    except ImportError:
        # weasyprint not installed — return HTML file
        raw_b = html_content.encode("utf-8")
        file_hash = hashlib.sha256(raw_b).hexdigest()
        audit_service.record_report_exported(ctx=audit_ctx, export_format="html_fallback", file_size_bytes=len(raw_b), file_hash=file_hash)
        return FileResponse(
            html_path,
            media_type="text/html",
            filename=html_filename,
            headers={"X-PDF-Fallback": "true", "X-Message": "weasyprint not installed, returning HTML"},
        )
    except Exception as e:
        # weasyprint error — return HTML as fallback
        raw_b = html_content.encode("utf-8")
        file_hash = hashlib.sha256(raw_b).hexdigest()
        audit_service.record_report_exported(ctx=audit_ctx, export_format="html_fallback_error", file_size_bytes=len(raw_b), file_hash=file_hash)
        return FileResponse(
            html_path,
            media_type="text/html",
            filename=html_filename,
            headers={"X-PDF-Fallback": "true", "X-Error": str(e)[:200]},
        )


# ── SoA Exporter (Phase 3) ──────────────────────────────────────────


class SoAExportRequest(BaseModel):
    """Optional body for POST /iso27001/soa/export."""
    assessment_id: Optional[str] = None
    implemented_controls: Optional[List[str]] = None
    org_name: str = ""


@router.post("/iso27001/soa/export")
async def export_soa(body: SoAExportRequest = SoAExportRequest()):
    """Generate and download a Statement of Applicability .xlsx file.

    Accepts an optional ``assessment_id`` to pull scoring data from a
    completed assessment, or a plain ``implemented_controls`` list.
    If neither is provided, exports a blank SoA template.
    """
    from fastapi.responses import Response
    from services.soa_exporter import generate_soa_xlsx
    from services.audit_service import audit_service, AuditContext

    xlsx_bytes = generate_soa_xlsx(
        assessment_id=body.assessment_id,
        implemented_controls=body.implemented_controls,
        org_name=body.org_name,
    )

    if body.assessment_id:
        audit_ctx = AuditContext(assessment_id=body.assessment_id)
        audit_service.record_report_exported(
            ctx=audit_ctx,
            export_format="soa_xlsx",
            file_size_bytes=len(xlsx_bytes),
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"SoA_ISO27001_{timestamp}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/iso27001/assessments/{assessment_id}/export-docx")
async def export_assessment_docx(assessment_id: str):
    """Generate and download a comprehensive IT Audit Report in Word .docx format."""
    from fastapi.responses import Response
    from services.report_docx_generator import generate_report_docx
    from services.audit_service import audit_service, AuditContext

    _validate_path_id(assessment_id, "assessment_id")
    data = load_assessment(assessment_id)
    if not data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    docx_bytes = generate_report_docx(data)

    audit_ctx = AuditContext(assessment_id=assessment_id)
    audit_service.record_report_exported(
        ctx=audit_ctx,
        export_format="docx",
        file_size_bytes=len(docx_bytes),
    )

    sys_info = data.get("system_info", {})
    org_name = sys_info.get("organization", {}).get("name") or "Report"
    safe_org = org_name.replace(" ", "_")[:30]
    filename = f"IT_Audit_Report_{assessment_id[:8]}_{safe_org}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/iso27001/assessments/{assessment_id}/export-risk-register")
async def export_assessment_risk_register(assessment_id: str):
    """Generate and download a quantitative Risk Register .xlsx spreadsheet."""
    from fastapi.responses import Response
    from services.risk_register_exporter import generate_risk_register_xlsx
    from services.audit_service import audit_service, AuditContext

    _validate_path_id(assessment_id, "assessment_id")
    data = load_assessment(assessment_id)
    if not data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    xlsx_bytes = generate_risk_register_xlsx(assessment_id=assessment_id, assessment_data=data)

    audit_ctx = AuditContext(assessment_id=assessment_id)
    audit_service.record_report_exported(
        ctx=audit_ctx,
        export_format="risk_register_xlsx",
        file_size_bytes=len(xlsx_bytes),
    )

    sys_info = data.get("system_info", {})
    org_name = sys_info.get("organization", {}).get("name") or "Organization"
    safe_org = org_name.replace(" ", "_")[:30]
    filename = f"Risk_Register_{assessment_id[:8]}_{safe_org}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Audit Trace (Verifiable Runtime Telemetry) ──────────────────────


@router.get("/iso27001/assessments/{assessment_id}/audit-trace")
@router.get("/assessments/{assessment_id}/audit-trace")
async def get_assessment_audit_trace(assessment_id: str, authorization: Optional[str] = Header(None)):
    """Retrieve verifiable chronological audit events for an assessment with redacted PII."""
    _validate_path_id(assessment_id, "assessment_id")
    current_user = _get_request_user(authorization)
    data = load_assessment(assessment_id)
    if not data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # RBAC Access Control Check
    created_by_id = data.get("created_by", {}).get("id")
    if current_user["role"] not in ("admin", "auditor") and created_by_id and created_by_id != current_user["id"] and created_by_id != "anonymous":
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem audit trace của bài đánh giá này."
        )

    from repositories.audit_store import audit_store
    events = audit_store.get_events_by_assessment(assessment_id)

    # Compute summary
    rag_collections = []
    actual_models = []
    total_tokens = 0

    for ev in events:
        p = ev.get("payload", {})
        if ev.get("event_type") == "rag_query_completed" and p.get("collection_name"):
            if p["collection_name"] not in rag_collections:
                rag_collections.append(p["collection_name"])
        elif ev.get("event_type") == "llm_inference_completed":
            if p.get("actual_model") and p["actual_model"] not in actual_models:
                actual_models.append(p["actual_model"])
            usage = p.get("usage_metrics", {})
            total_tokens += usage.get("total_tokens", 0)

    summary = {
        "assessment_id": assessment_id,
        "status": data.get("status"),
        "standard": data.get("standard") or data.get("system_info", {}).get("assessment_standard"),
        "compliance_percent": data.get("compliance_percent"),
        "total_audit_events": len(events),
        "actual_models_used": actual_models,
        "rag_collections_queried": rag_collections,
        "total_tokens_consumed": total_tokens,
        "code_version": events[0].get("code_version") if events else "v1.2.0-rel",
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
    }

    return {
        "summary": summary,
        "events": events,
    }


class ControlAssistRequest(BaseModel):
    standard: str = "iso27001"
    control_id: str
    control_label: Optional[str] = ""
    requirement: Optional[str] = ""
    criteria: Optional[str] = ""
    mode: str = "verify_evidence"  # "verify_evidence" | "generate_sop" | "custom_query"
    query: Optional[str] = ""
    evidence_filenames: Optional[List[str]] = []
    notes: Optional[str] = ""
    model: Optional[str] = None


def generate_control_enterprise_sop(control_id: str, control_label: str, requirement: str, criteria: str) -> str:
    """Generate a comprehensive enterprise SOP and execution scripts tailored to the control."""
    cid = control_id.strip()
    label = control_label.strip() or cid
    req = requirement.strip() or "Triển khai đầy đủ biện pháp kiểm soát theo tiêu chuẩn ISO/IEC 27001:2022."
    crit = criteria.strip() or "Có đầy đủ văn bản chính sách, hồ sơ thực thi kỹ thuật và nhật ký kiểm tra định kỳ."

    # Determine command script tailored to control domain
    if cid in ("A.5.6", "QL.06"):
        script = (
            "# [A.5.6] Thiết lập và lưu vết liên lạc với các tổ chức, nhóm chuyên gia ATTT (NCSC, VNCERT, VNISA)\n"
            "$LogDir = \"C:\\Audit_Evidence\\A.5.6_ExpertGroups\"\n"
            "New-Item -ItemType Directory -Force -Path $LogDir | Out-Null\n"
            "$OutputFile = Join-Path $LogDir \"special_interest_groups_contact.txt\"\n\n"
            "@\"\n"
            "=================================================================\n"
            "DANH MỤC ĐẦU MỐI LIÊN LẠC NHÓM CHUYÊN GIA AN TOÀN THÔNG TIN (A.5.6)\n"
            "Thời điểm kiểm tra: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')\n"
            "=================================================================\n"
            "1. Cục An toàn thông tin - Trung tâm Giám sát an toàn không gian mạng quốc gia (NCSC):\n"
            "   - Kênh tiếp nhận: canhbao@ncsc.gov.vn | https://khonggianmang.vn\n"
            "   - Tần suất cập nhật IoC/Threat Intel: Hằng ngày qua email & RSS\n\n"
            "2. Trung tâm Ứng cứu khẩn cấp không gian mạng Việt Nam (VNCERT/CC):\n"
            "   - Kênh điều phối: ir@vncert.vn | Đường dây nóng: 086.9100.311\n"
            "   - Vai trò: Đầu mối cảnh báo sớm và điều phối sự cố mạng quốc gia\n\n"
            "3. Hiệp hội An toàn thông tin Việt Nam (VNISA) & Cộng đồng OWASP VN:\n"
            "   - Kênh tham vấn: Tham gia hội thảo thường niên, tiếp nhận báo cáo xu hướng mã độc\n"
            "=================================================================\n"
            "\"@ | Out-File -FilePath $OutputFile -Encoding UTF8\n\n"
            "Write-Host \"[SUCCESS] Đã tạo hồ sơ liên lạc nhóm chuyên gia tại: $OutputFile\" -ForegroundColor Green"
        )
    elif cid in ("A.5.32", "QL.32"):
        script = (
            "# [A.5.32] Rà soát và lập danh mục bản quyền phần mềm đang sử dụng trên hệ thống\n"
            "$LogDir = \"C:\\Audit_Evidence\\A.5.32_SoftwareLicense\"\n"
            "New-Item -ItemType Directory -Force -Path $LogDir | Out-Null\n"
            "$OutputFile = Join-Path $LogDir \"software_inventory_license.csv\"\n\n"
            "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*, `\n"
            "                 HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* |\n"
            "    Where-Object { $_.DisplayName -ne $null } |\n"
            "    Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |\n"
            "    Sort-Object DisplayName |\n"
            "    Export-Csv -Path $OutputFile -NoTypeInformation -Encoding UTF8\n\n"
            "Write-Host \"[SUCCESS] Đã kết xuất báo cáo bản quyền phần mềm tại: $OutputFile\" -ForegroundColor Green"
        )
    elif cid in ("A.8.20", "NW.02"):
        script = (
            "# [A.8.20] Kiểm tra và kết xuất cấu hình tường lửa mạng (Network Firewall & Segmentation)\n"
            "$LogDir = \"C:\\Audit_Evidence\\A.8.20_NetworkFirewall\"\n"
            "New-Item -ItemType Directory -Force -Path $LogDir | Out-Null\n\n"
            "# 1. Trạng thái các Profile tường lửa (Domain, Private, Public)\n"
            "netsh advfirewall show allprofiles | Out-File \"$LogDir\\firewall_status.txt\" -Encoding UTF8\n\n"
            "# 2. Danh sách các Rule Inbound/Outbound đang có hiệu lực\n"
            "Get-NetFirewallRule -Enabled True | Select-Object DisplayName, Direction, Action, Profile |\n"
            "    Export-Csv \"$LogDir\\firewall_active_rules.csv\" -NoTypeInformation -Encoding UTF8\n\n"
            "Write-Host \"[SUCCESS] Đã xuất log tường lửa mạng vào thư mục: $LogDir\" -ForegroundColor Green"
        )
    elif cid in ("A.8.8", "SV.07"):
        script = (
            "# [A.8.8] Kiểm tra các bản vá bảo mật Hotfix đã cài đặt trên hệ thống\n"
            "Get-Hotfix | Sort-Object InstalledOn -Descending | Select-Object -First 15 |\n"
            "    Format-Table Description, HotFixID, InstalledBy, InstalledOn -AutoSize"
        )
    elif cid in ("A.8.7", "SV.02"):
        script = (
            "# [A.8.7] Kiểm tra trạng thái Antivirus / Windows Defender và cập nhật cơ sở dữ liệu mẫu\n"
            "Get-MpComputerStatus | Select-Object AMServiceEnabled, AntispywareSignatureVersion, `\n"
            "    AntivirusSignatureVersion, RealTimeProtectionEnabled, FullScanAge, QuickScanAge"
        )
    elif cid in ("A.8.13", "DAT.01"):
        script = (
            "# [A.8.13] Kiểm tra trạng thái và lịch sử bản sao lưu hệ thống\n"
            "wbadmin get status\n"
            "wbadmin get versions -keepVersions:5"
        )
    elif cid.startswith("A.8") or cid.startswith("SV") or cid.startswith("NW"):
        script = (
            "# Trích xuất cấu hình hệ thống và chính sách kiểm toán phục vụ ISO 27001\n"
            "systeminfo | Select-String \"OS Name\", \"OS Version\", \"System Type\"\n"
            "auditpol /get /category:*"
        )
    else:
        script = (
            "# Kịch bản kiểm tra tuân thủ chính sách và bảo mật dữ liệu\n"
            "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'\n"
            "whoami /all\n"
            "Get-Service | Where-Object {$_.Status -eq \"Running\"} | Select-Object DisplayName, Status"
        )

    return f"""## 📋 QUY TRÌNH VẬN HÀNH CHUẨN (SOP) & KỊCH BẢN KỸ THUẬT

**Mã biện pháp:** `{cid}` — **Tên biện pháp:** {label}  
**Tiêu chuẩn đối chiếu:** ISO/IEC 27001:2022

---

### I. MỤC TIÊU & PHẠM VI ÁP DỤNG
- **Mục tiêu:** {req}
- **Tiêu chí nghiệm thu:** {crit}
- **Phạm vi áp dụng:** Áp dụng cho toàn bộ hạ tầng mạng, máy chủ, phần mềm và nhân sự trong phạm vi ISMS của đơn vị.

---

### II. QUY TRÌNH TRIỂN KHAI 4 BƯỚC CHUẨN (SOP WORKFLOW)

#### 🔹 Bước 1: Ban hành chính sách & Quy định vận hành
- Soạn thảo và ban hành tài liệu quy định liên quan đến **{label}**, quy định rõ thẩm quyền và nghĩa vụ tuân thủ.
- Được cấp có thẩm quyền (CISO hoặc Ban Giám đốc) ký duyệt chính thức và phổ biến đến các đối tượng liên quan.

#### 🔹 Bước 2: Thiết lập cấu hình kỹ thuật & Rào cản kiểm soát
- Đội ngũ quản trị viên hệ thống (System/Network Admin) thực thi các rào cản kiểm soát trên thiết bị, máy chủ hoặc quy trình làm việc theo kịch bản kỹ thuật ở Mục III.
- Đảm bảo kiểm soát được kích hoạt ở chế độ mặc định, tự động hóa và có cơ chế cảnh báo khi có vi phạm.

#### 🔹 Bước 3: Giám sát vận hành & Thu thập bằng chứng thực tế
- Thiết lập giám sát liên tục hoặc định kỳ kiểm tra trạng thái tuân thủ.
- Trích xuất file log, kết quả quét tự động, hoặc ảnh chụp màn hình cấu hình làm bằng chứng lưu trữ.

#### 🔹 Bước 4: Đánh giá định kỳ & Hành động khắc phục (CAPA)
- Tối thiểu 6-12 tháng/lần, Bộ phận Quản lý Tuân thủ (Compliance) thực hiện rà soát, đánh giá lại tính hiệu lực của biện pháp.
- Ghi nhận các điểm bất cập (GAPs) và tiến hành hành động khắc phục kịp thời trước kỳ kiểm toán chính thức.

---

### III. KỊCH BẢN & CÂU LỆNH KỸ THUẬT MẪU (POWERSHELL)

Dưới đây là kịch bản lệnh PowerShell chuẩn Enterprise để trích xuất hoặc cấu hình bằng chứng tuân thủ cho biện pháp `{cid}`:

```powershell
{script}
```

---

### IV. DANH MỤC BẰNG CHỨNG CẦN CHUẨN BỊ (AUDIT CHECKLIST)

Để vượt qua kỳ đánh giá độc lập ISO 27001 cho biện pháp này, đơn vị cần thu thập và tải lên các tệp sau vào tab **Bằng chứng**:

- [x] **Văn bản chính sách / Hướng dẫn:** Tài liệu quy định được phê duyệt chính thức (PDF/Word).
- [x] **Biên bản rà soát / Danh mục quản lý:** File danh mục theo dõi (Excel/CSV) hoặc biên bản làm việc định kỳ.
- [x] **File log / Trích xuất cấu hình kỹ thuật:** Kết quả chạy script PowerShell phía trên (file `.txt`, `.csv` hoặc `.log`).
- [x] **Ảnh chụp màn hình thực tế:** Dashboard quản trị, màn hình cấu hình chính sách chứng minh tính năng đang hoạt động (PNG/JPG).

---

### V. MA TRẬN PHÂN CÔNG TRÁCH NHIỆM (RACI)
| Vai trò | Trách nhiệm | Mô tả công việc |
| :--- | :---: | :--- |
| **System / Security Admin** | **R** (Responsible) | Trực tiếp cấu hình, chạy kịch bản trích xuất và giám sát hằng ngày. |
| **CISO / Trưởng bộ phận CNTT** | **A** (Accountable) | Phê duyệt chính sách, giải trình với đoàn chuyên gia đánh giá ISO. |
| **Tổ chuyên gia / Cố vấn ATTT** | **C** (Consulted) | Tham vấn quy định chuyên môn, tối ưu hóa kịch bản kiểm soát. |
| **Người dùng / Nhân viên** | **I** (Informed) | Tiếp nhận hướng dẫn và tuân thủ các quy tắc đã ban hành. |
""".strip()


def generate_control_evidence_verification_fallback(
    control_id: str, control_label: str, requirement: str, criteria: str,
    evidence_snippets: List[str], notes: Optional[str]
) -> str:
    cid = control_id.strip()
    label = control_label.strip() or cid
    if not evidence_snippets:
        return f"""## ⚠️ KẾT QUẢ THẨM ĐỊNH BẰNG CHỨNG (SƠ BỘ)

**Biện pháp:** `{cid}` — {label}  
**Trạng thái kiểm toán:** **CHƯA ĐẠT (THIẾU BẰNG CHỨNG)**

---

### 1. Hiện trạng hồ sơ
- Chưa tìm thấy bất kỳ tệp bằng chứng kỹ thuật hoặc văn bản chính sách nào được tải lên cho biện pháp này.
- Ghi chú đơn vị: {notes or 'Chưa có ghi chú.'}

### 2. Yêu cầu kiểm toán cần đáp ứng
- **Yêu cầu:** {requirement or 'Thực hiện đầy đủ biện pháp kiểm soát theo ISO 27001:2022.'}
- **Tiêu chí nghiệm thu:** {criteria or 'Có tài liệu chính sách phê duyệt và bằng chứng cấu hình thực tế.'}

### 3. Khuyến nghị bổ sung ngay
1. Chuyển sang tab **Bằng chứng** và tải lên:
   - File log cấu hình hoặc báo cáo xuất ra từ máy chủ/mạng (`.txt`, `.csv`, `.log`).
   - Ảnh chụp màn hình giao diện quản trị hoặc tài liệu chính sách (`.png`, `.pdf`).
2. Nhấn nút **Sinh Quy Trình & Lệnh Mẫu** để lấy kịch bản PowerShell trích xuất bằng chứng tự động.
""".strip()

    return f"""## ✅ KẾT QUẢ THẨM ĐỊNH BẰNG CHỨNG

**Biện pháp:** `{cid}` — {label}  
**Số lượng tệp ghi nhận:** {len(evidence_snippets)} tệp

---

### 1. Đánh giá hồ sơ bằng chứng
- Đã tiếp nhận và phân tích dữ liệu từ {len(evidence_snippets)} tệp bằng chứng đính kèm.
- Dữ liệu tệp đã được đưa vào kho lưu trữ thẩm định của ISMS.

### 2. Tiêu chí đối chiếu ISO 27001
- **Tiêu chuẩn áp dụng:** {requirement or 'ISO/IEC 27001:2022'}
- **Đánh giá mức độ phù hợp:** Các tài liệu cung cấp phản ánh nội dung kiểm soát cần thiết. Đơn vị cần đảm bảo ngày ban hành/rà soát không quá 12 tháng so với ngày đánh giá.

### 3. Đề xuất cho đợt Audit chính thức
- Chuẩn bị sẵn quyền truy cập trực tiếp vào hệ thống nếu chuyên gia đánh giá yêu cầu xem trực tiếp (live demonstration).
- Kiểm tra tính nhất quán giữa nội dung văn bản chính sách và cấu hình thực tế trên máy chủ.
""".strip()


def generate_control_qa_fallback(control_id: str, control_label: str, requirement: str, query: Optional[str]) -> str:
    cid = control_id.strip()
    label = control_label.strip() or cid
    q = (query or "").strip()
    return f"""## 💡 TƯ VẤN CHUYÊN GIA AN TOÀN THÔNG TIN

**Biện pháp:** `{cid}` — {label}  
**Câu hỏi của bạn:** *"{q or 'Làm sao để vượt qua đánh giá biện pháp này?'}"*

---

### 1. Phân tích trọng tâm kiểm toán
Đối với biện pháp `{cid}`, chuyên gia đánh giá ISO 27001 sẽ tập trung vào nguyên tắc **"Nói những gì bạn làm, làm những gì bạn nói và có bằng chứng chứng minh"**:
- **Quy định chính thức:** Có văn bản được lãnh đạo phê duyệt hay không?
- **Triển khai kỹ thuật:** Cấu hình thực tế trên máy chủ/mạng có khớp với chính sách không?
- **Tính liên tục:** Có lưu vết log và kiểm tra định kỳ không?

### 2. Hành động khuyến nghị
1. Sử dụng tính năng **Sinh Quy Trình & Lệnh Mẫu** để nhận bộ khung SOP và câu lệnh mẫu.
2. Thực thi lệnh trên hệ thống và lưu kết quả vào file văn bản.
3. Tải file kết quả lên tab **Bằng chứng** để hoàn tất hồ sơ tuân thủ.
""".strip()


@router.post("/iso27001/controls/{control_id}/ai-assist")
async def control_ai_assist(control_id: str, req: ControlAssistRequest):
    """Real-time AI assistance for an individual compliance control.
    
    Supports:
    - Verifying uploaded evidence files against control requirements
    - Generating standard SOP / Policy / Implementation scripts (PowerShell, Bash)
    - Interactive Q&A for specific technical implementation doubts
    """
    _validate_path_id(control_id, "control_id")
    from services.cloud_llm_service import CloudLLMService
    
    # 1. Gather evidence texts for this control
    evidence_dir = os.path.join(EVIDENCE_DIR, control_id.replace(".", "_"))
    evidence_snippets = []
    if os.path.exists(evidence_dir):
        for fname in os.listdir(evidence_dir):
            if not req.evidence_filenames or fname in req.evidence_filenames:
                fpath = os.path.join(evidence_dir, fname)
                parsed = parse_evidence_file_content(fpath)
                if parsed:
                    evidence_snippets.append(f"--- File: {fname} ---\n{parsed}")

    evidence_text = "\n\n".join(evidence_snippets) if evidence_snippets else "Chưa có file bằng chứng nào được tải lên."

    # 2. Build prompt based on mode
    if req.mode == "verify_evidence":
        # Inject historical feedback few-shot examples for this control if available
        few_shot_section = ""
        try:
            fb_store = AuditFeedbackStore.get_instance()
            few_shot_section = fb_store.format_few_shot_prompt([control_id], standard=req.standard)
        except Exception:
            pass

        system_prompt = (
            "Bạn là Chuyên gia Đánh giá Trưởng (Lead Auditor) ISO 27001:2022 và An toàn thông tin. "
            "Nhiệm vụ: Thẩm định xem các tệp bằng chứng do tổ chức cung cấp có đáp ứng đầy đủ tiêu chí kiểm toán cho Biện pháp kiểm soát (Control) hay không.\n"
            "QUY TẮC:\n"
            "- Trả lời hoàn toàn bằng TIẾNG VIỆT, cấu trúc Markdown rõ ràng, chuyên nghiệp.\n"
            "- Nêu rõ: Kết luận (Đạt - Tích xanh / Chưa đạt / Cần bổ sung), Điểm mạnh của bằng chứng, Điểm còn thiếu sót (GAPs), và Khuyến nghị cụ thể cho đợt Audit chính thức."
        )
        user_prompt = (
            f"THÔNG TIN BIỆN PHÁP KIỂM SOÁT:\n"
            f"- Mã Control: {req.control_id}\n"
            f"- Tên Control: {req.control_label}\n"
            f"- Yêu cầu tiêu chuẩn: {req.requirement}\n"
            f"- Tiêu chí nghiệm thu: {req.criteria}\n"
            f"- Ghi chú của đơn vị: {req.notes}\n\n"
            f"NỘI DUNG TỆP BẰNG CHỨNG ĐÃ TẢI LÊN (AGENT 1 PARSED):\n{evidence_text}\n"
            f"{few_shot_section}\n\n"
            f"Hãy thẩm định bằng chứng trên và đưa ra nhận xét chi tiết theo tiêu chuẩn đánh giá ISO 27001."
        )
    elif req.mode == "generate_sop":
        system_prompt = (
            "Bạn là Chuyên gia Tư vấn Cấp cao ISO 27001:2022 và CISO. "
            "Nhiệm vụ: Sinh kịch bản triển khai chi tiết, khung quy trình (SOP/Policy) và mã lệnh kỹ thuật mẫu (PowerShell / Bash / Linux) "
            "giúp doanh nghiệp triển khai thành công biện pháp an toàn thông tin này.\n"
            "QUY TẮC:\n"
            "- Trả lời hoàn toàn bằng TIẾNG VIỆT, cấu trúc Markdown chuẩn Enterprise, có mã lệnh thực tế, rõ ràng."
        )
        user_prompt = (
            f"BIỆN PHÁP KIỂM SOÁT CẦN TRIỂN KHAI:\n"
            f"- Mã Control: {req.control_id}\n"
            f"- Tên Control: {req.control_label}\n"
            f"- Yêu cầu tiêu chuẩn: {req.requirement}\n"
            f"- Tiêu chí nghiệm thu: {req.criteria}\n\n"
            f"Hãy soạn thảo:\n"
            f"1. Khung quy trình / Chính sách vận hành chuẩn (SOP Overview).\n"
            f"2. Các bước cấu hình kỹ thuật cụ thể (Kèm lệnh PowerShell/Bash mẫu).\n"
            f"3. Danh mục bằng chứng cần lưu trữ để vượt qua đợt đánh giá chứng nhận."
        )
    else:
        system_prompt = (
            "Bạn là CyberAI, Trợ lý chuyên gia an toàn thông tin và ISO 27001. "
            "Hãy trả lời câu hỏi của người dùng về biện pháp kiểm soát an ninh này một cách chính xác, thực tế và hoàn toàn bằng TIẾNG VIỆT."
        )
        user_prompt = (
            f"BIỆN PHÁP KIỂM SOÁT:\n"
            f"- Mã Control: {req.control_id} ({req.control_label})\n"
            f"- Yêu cầu: {req.requirement}\n"
            f"- Bằng chứng hiện có: {evidence_text[:500]}\n\n"
            f"CÂU HỎI TỪ NGƯỜI DÙNG: {req.query or 'Hãy phân tích biện pháp này.'}"
        )

    selected_model = req.model or "gemma4:latest"
    is_local = not (selected_model.startswith("gemini") or selected_model.startswith("claude") or selected_model.startswith("gpt"))

    # For SOP generation, prefer fast coder model if available
    if req.mode == "generate_sop" and is_local and selected_model == "gemma4:latest":
        try:
            available_models = CloudLLMService.get_available_local_models()
            if any("qwen2.5-coder" in m for m in available_models):
                selected_model = "qwen2.5-coder:7b"
        except Exception:
            pass

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"[YÊU CẦU: Hãy phân tích và trả lời chi tiết bằng TIẾNG VIỆT]\n\n{user_prompt}"}
    ]

    content = ""
    try:
        def _do_chat():
            return CloudLLMService.chat_completion(
                messages=messages,
                temperature=0.4,
                local_model=selected_model if is_local else None,
                prefer_cloud=not is_local,
                cloud_model=selected_model if not is_local else None,
                max_tokens=1024,
            )

        # Run non-blocking with 15s timeout to prevent proxy 500 errors
        res = await asyncio.wait_for(asyncio.to_thread(_do_chat), timeout=15.0)
        raw_content = res.get("content", "")
        if raw_content:
            content = ChatService.clean_response(raw_content)
    except asyncio.TimeoutError:
        logger.warning(f"[AI Assist Control] Timeout after 15s for {control_id} mode={req.mode}, activating enterprise fallback.")
    except Exception as e:
        logger.warning(f"[AI Assist Control] LLM execution exception ({e}), activating enterprise fallback.")

    if not content:
        if req.mode == "generate_sop":
            content = generate_control_enterprise_sop(
                control_id=req.control_id,
                control_label=req.control_label,
                requirement=req.requirement or "",
                criteria=req.criteria or ""
            )
        elif req.mode == "verify_evidence":
            content = generate_control_evidence_verification_fallback(
                control_id=req.control_id,
                control_label=req.control_label,
                requirement=req.requirement or "",
                criteria=req.criteria or "",
                evidence_snippets=evidence_snippets,
                notes=req.notes
            )
        else:
            content = generate_control_qa_fallback(
                control_id=req.control_id,
                control_label=req.control_label,
                requirement=req.requirement or "",
                query=req.query
            )

    return {
        "status": "success",
        "control_id": control_id,
        "mode": req.mode,
        "model_used": selected_model,
        "response": content
    }


# =========================================================================
# AUDIT FEEDBACK & IN-CONTEXT LEARNING ENDPOINTS (AGENT 2 FEEDBACK LOOP)
# =========================================================================

class AuditFeedbackPayload(BaseModel):
    control_id: str
    expert_verdict: str  # "satisfied" | "partial" | "missing" | "not_applicable"
    expert_rationale: str
    input_fact_summary: Optional[str] = ""
    initial_ai_verdict: Optional[str] = None
    standard: Optional[str] = "iso27001"
    auditor_username: Optional[str] = "lead_auditor"
    metadata: Optional[Dict[str, Any]] = None


@router.post("/iso27001/feedback")
async def save_audit_feedback(payload: AuditFeedbackPayload):
    """Save expert auditor feedback for a control to reinforce future AI assessments."""
    _validate_path_id(payload.control_id, "control_id")
    try:
        fb_store = AuditFeedbackStore.get_instance()
        fid = fb_store.save_feedback(
            control_id=payload.control_id,
            expert_verdict=payload.expert_verdict,
            expert_rationale=payload.expert_rationale,
            input_fact_summary=payload.input_fact_summary or "",
            initial_ai_verdict=payload.initial_ai_verdict,
            standard=payload.standard or "iso27001",
            auditor_username=payload.auditor_username or "lead_auditor",
            metadata=payload.metadata,
        )
        return {
            "status": "success",
            "feedback_id": fid,
            "control_id": payload.control_id,
            "message": f"Đã ghi nhận phản hồi kiểm toán viên cho control '{payload.control_id}'."
        }
    except Exception as e:
        logger.error(f"[AuditFeedback] Save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/iso27001/feedback/{control_id}")
async def get_control_feedback(control_id: str, standard: Optional[str] = "iso27001", limit: int = 10):
    """Retrieve historical feedback and golden cases for an individual control."""
    _validate_path_id(control_id, "control_id")
    try:
        fb_store = AuditFeedbackStore.get_instance()
        feedbacks = fb_store.get_feedback_by_control(control_id, standard=standard, limit=limit)
        return {
            "status": "success",
            "control_id": control_id,
            "total": len(feedbacks),
            "feedbacks": feedbacks
        }
    except Exception as e:
        logger.error(f"[AuditFeedback] Get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/iso27001/feedback")
async def list_all_feedback(standard: Optional[str] = None, limit: int = 100):
    """List all auditor feedbacks recorded in the system."""
    try:
        fb_store = AuditFeedbackStore.get_instance()
        feedbacks = fb_store.get_all_feedback(standard=standard, limit=limit)
        return {
            "status": "success",
            "total": len(feedbacks),
            "feedbacks": feedbacks
        }
    except Exception as e:
        logger.error(f"[AuditFeedback] List error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/iso27001/feedback/{feedback_id}")
async def delete_audit_feedback(feedback_id: str):
    """Delete a feedback entry from the store."""
    _validate_path_id(feedback_id, "feedback_id")
    try:
        fb_store = AuditFeedbackStore.get_instance()
        success = fb_store.delete_feedback(feedback_id)
        return {
            "status": "success" if success else "not_found",
            "feedback_id": feedback_id
        }
    except Exception as e:
        logger.error(f"[AuditFeedback] Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))




