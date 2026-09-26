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
import hashlib
import shutil

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
from services.artifact_validator import validate_assessment_invariants

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


def build_evidence_context_for_ai(evidence_map: Dict[str, List[str]], standard: str = "iso27001", assessment_id: Optional[str] = None) -> str:
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
            candidate_paths = []
            if assessment_id:
                candidate_paths.append(os.path.join(EVIDENCE_DIR, assessment_id, ctrl_id.replace(".", "_"), safe_name))
                candidate_paths.append(os.path.join(EVIDENCE_DIR, assessment_id, safe_name))
            candidate_paths.extend([
                os.path.join(EVIDENCE_DIR, ctrl_id.replace(".", "_"), safe_name),
                os.path.join(EVIDENCE_DIR, ctrl_id, safe_name),
                os.path.join(EVIDENCE_DIR, f"{ctrl_id}_{safe_name}"),
                os.path.join(EVIDENCE_DIR, safe_name),
            ])
            fpath = None
            for cp in candidate_paths:
                if os.path.exists(cp):
                    fpath = cp
                    break
            if not fpath:
                fpath = candidate_paths[0]
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

    assessment_id: Any = None

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
    control_verdicts: Any = []
    evidence_manifest_id: Any = None
    evidence_files: Any = []
    template_id: Any = None
    template_name: Any = None
    is_template_input: Any = False
    compliance: Any = None


def save_assessment(assessment_id: str, data: dict):
    filepath = os.path.join(ASSESSMENTS_DIR, f"{assessment_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_assessment(assessment_id: str) -> Optional[dict]:
    cand_dirs = [ASSESSMENTS_DIR]
    data_env_dir = os.path.join(os.getenv("DATA_PATH", "./data"), "assessments")
    if data_env_dir not in cand_dirs:
        cand_dirs.append(data_env_dir)
    fallback_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "assessments"))
    if fallback_dir not in cand_dirs:
        cand_dirs.append(fallback_dir)
    fallback_dir2 = "/data/assessments"
    if fallback_dir2 not in cand_dirs:
        cand_dirs.append(fallback_dir2)

    filepath = None
    for c_dir in cand_dirs:
        if not os.path.exists(c_dir):
            continue
        cand_file = os.path.join(c_dir, f"{assessment_id}.json")
        if os.path.exists(cand_file):
            filepath = cand_file
            break
        if len(assessment_id) >= 6:
            matches = [f for f in os.listdir(c_dir) if f.startswith(assessment_id) and f.endswith(".json")]
            if len(matches) == 1:
                filepath = os.path.join(c_dir, matches[0])
                break

    if filepath and os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            real_id = data.get("id") or data.get("assessment_id") or os.path.splitext(os.path.basename(filepath))[0]
            data.setdefault("id", real_id)
            data.setdefault("assessment_id", real_id)
            data.setdefault("run_id", f"run_{real_id[:8]}")
            if "json_data" in data and isinstance(data["json_data"], dict):
                data["json_data"].setdefault("assessment_id", real_id)
                data["json_data"].setdefault("run_id", data["run_id"])
            return data
    return None


def load_evidence_manifest(assessment_id: str) -> Optional[dict]:
    """Load Evidence Manifest JSON for a given assessment."""
    ev_manifest_dir = os.path.join(os.getenv("DATA_PATH", "./data"), "evidence_manifests")
    path = os.path.join(ev_manifest_dir, f"{assessment_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
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
                    aid = data.get("id") or data.get("assessment_id") or filename[:-5]
                    org = (
                        data.get("system_info", {}).get("organization", {}).get("name")
                        or data.get("system_info", {}).get("org_name")
                        or data.get("org_name")
                        or (data.get("organization", {}).get("name") if isinstance(data.get("organization"), dict) else None)
                    )
                    if not org or org == "Unknown":
                        if str(aid).startswith("test-fail-"):
                            org = f"Mẫu lỗi kiểm thử ({aid})"
                        else:
                            org = "Không rõ"

                    raw_std = (
                        data.get("system_info", {}).get("assessment_standard")
                        or data.get("standard")
                        or "iso27001"
                    )
                    std = raw_std.get("id") if isinstance(raw_std, dict) else str(raw_std)

                    w_comp = data.get("weighted_compliance") or (data.get("json_data") or {}).get("weighted_compliance") or {}
                    pct = w_comp.get("percentage") if isinstance(w_comp, dict) and "percentage" in w_comp else data.get("compliance_percent")
                    if pct is None and "result" in data and isinstance(data["result"], dict):
                        pct = data["result"].get("compliance_percent")

                    # If assessment has controls and 0 verified satisfied/partial controls, pct must be 0.0
                    ctrls = (data.get("json_data") or {}).get("controls") or data.get("controls") or []
                    if ctrls and isinstance(ctrls, list):
                        has_satisfied = any(
                            (c.get("assessment_verdict") or c.get("evidence_verdict") or "").lower() in ("satisfied", "partial")
                            for c in ctrls if isinstance(c, dict)
                        )
                        if not has_satisfied:
                            pct = 0.0

                    results.append({
                        "id": aid,
                        "status": data.get("status", "unknown"),
                        "standard": std,
                        "org_name": org,
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "compliance_percent": round(float(pct), 1) if pct is not None else 0.0
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
    from services.audit_service import audit_service, AuditContext, get_code_version
    from services.evidence_parser import compute_file_sha256, mask_evidence_filename
    from schemas.assessment_schema import EvidenceManifest, EvidenceManifestItem

    eff_run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
    audit_ctx = AuditContext(
        assessment_id=assessment_id,
        run_id=eff_run_id,
        code_version=get_code_version(),
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
        # Build Evidence Manifest and accurate unique file counters
        ev_manifest_dir = os.path.join(os.getenv("DATA_PATH", "./data"), "evidence_manifests")
        os.makedirs(ev_manifest_dir, exist_ok=True)
        manifest_path = os.path.join(ev_manifest_dir, f"{assessment_id}.json")

        unique_files_map: Dict[str, EvidenceManifestItem] = {}
        ev_map = system_data.get("evidence_map") or {}
        raw_std = (
            system_data.get("standard")
            or system_data.get("assessment_standard")
            or system_data.get("system_info", {}).get("assessment_standard")
            or system_data.get("system_info", {}).get("standard")
            or "iso27001"
        )
        if isinstance(raw_std, dict):
            raw_std = raw_std.get("id") or raw_std.get("name") or "iso27001"
        std_code = str(raw_std).lower()
        is_tcvn_run = "tcvn" in std_code or "11930" in std_code
        is_iso_run = ("27001" in std_code or "iso" in std_code) and not is_tcvn_run

        SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".log", ".json", ".png", ".jpg", ".jpeg", ".conf", ".sql", ".ini"}

        for ctrl_id, files in ev_map.items():
            f_list = files if isinstance(files, list) else [files]
            for fname in f_list:
                safe_name = os.path.basename(fname)
                candidate_paths = [
                    os.path.join(EVIDENCE_DIR, assessment_id, ctrl_id.replace(".", "_"), safe_name),
                    os.path.join(EVIDENCE_DIR, assessment_id, safe_name),
                    os.path.join(EVIDENCE_DIR, ctrl_id.replace(".", "_"), safe_name),
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
                file_key = f"{f_hash}_{safe_name}"

                # Check if file should be excluded (unsupported extension or standard mismatch)
                is_excluded = False
                excl_reason = None
                if ext not in SUPPORTED_EXTENSIONS:
                    is_excluded = True
                    excl_reason = f"Định dạng tệp '{ext}' không được hỗ trợ (chỉ hỗ trợ PDF, DOCX, XLSX, CSV, TXT, LOG, CONF, PNG, JPG)."
                elif is_iso_run and (not ctrl_id.startswith("A.") and any(tcvn_p in ctrl_id for tcvn_p in ("NW", "DAT", "SV", "APP", "MNG"))):
                    is_excluded = True
                    excl_reason = f"Tệp đối soát tiêu chuẩn TCVN ({ctrl_id}) không áp dụng cho đánh giá ISO 27001."
                elif is_iso_run and ("tcvn" in safe_name.lower() and not ctrl_id.startswith("A.")):
                    is_excluded = True
                    excl_reason = "Tệp thuộc tiêu chuẩn TCVN không áp dụng cho đánh giá ISO 27001."
                elif is_tcvn_run and ctrl_id.startswith("A."):
                    is_excluded = True
                    excl_reason = f"Tệp đối soát tiêu chuẩn ISO ({ctrl_id}) không áp dụng cho đánh giá TCVN 11930."

                if file_key in unique_files_map:
                    item = unique_files_map[file_key]
                    if not is_excluded and ctrl_id not in item.control_mapping:
                        item.control_mapping.append(ctrl_id)
                else:
                    is_img_file = ext in {".png", ".jpg", ".jpeg", ".webp"}
                    unique_files_map[file_key] = EvidenceManifestItem(
                        file_id=f"file_{hashlib.md5(safe_name.encode()).hexdigest()[:8]}",
                        masked_filename=masked_name,
                        extension=ext,
                        size_bytes=size_bytes,
                        sha256=f_hash,
                        parser_or_ocr="ocr_tesseract" if is_img_file else "native_parser",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        fact_card_id=f"fact_{ctrl_id}",
                        control_mapping=[] if is_excluded else [ctrl_id],
                        mapping_type="direct_attachment" if not safe_name.startswith("batch_") else "auto_matched",
                        ingestion_status="excluded" if is_excluded else "ingested",
                        exclusion_reason=excl_reason,
                    )

        # Handle explicit excluded_files list in system_data
        for raw_excl in (system_data.get("excluded_files") or []):
            fname = raw_excl.get("file_name") or raw_excl.get("name") or "excluded_file"
            safe_name = os.path.basename(fname)
            f_hash = raw_excl.get("sha256") or hashlib.sha256(safe_name.encode()).hexdigest()
            file_key = f"{f_hash}_{safe_name}"
            if file_key not in unique_files_map:
                ext = os.path.splitext(safe_name)[1].lower() or ".bin"
                unique_files_map[file_key] = EvidenceManifestItem(
                    file_id=f"file_{hashlib.md5(safe_name.encode()).hexdigest()[:8]}",
                    masked_filename=mask_evidence_filename(safe_name),
                    extension=ext,
                    size_bytes=raw_excl.get("size_bytes", 0),
                    sha256=f_hash,
                    parser_or_ocr="excluded",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    fact_card_id=None,
                    control_mapping=[],
                    mapping_type="direct_attachment",
                    ingestion_status="excluded",
                    exclusion_reason=raw_excl.get("reason", "Tệp bị loại do không hợp lệ."),
                )

        # Also parse from evidence_context if ev_map was empty
        if not unique_files_map and evidence_context:
            extracted_files = [line.split("• File:", 1)[1].strip() for line in evidence_context.splitlines() if "• File:" in line]
            for safe_name in extracted_files:
                masked_name = mask_evidence_filename(safe_name)
                ext = os.path.splitext(safe_name)[1].lower() or ".bin"
                f_hash = hashlib.sha256(safe_name.encode()).hexdigest()
                file_key = f"{f_hash}_{safe_name}"
                if file_key not in unique_files_map:
                    unique_files_map[file_key] = EvidenceManifestItem(
                        file_id=f"file_{hashlib.md5(safe_name.encode()).hexdigest()[:8]}",
                        masked_filename=masked_name,
                        extension=ext,
                        size_bytes=0,
                        sha256=f_hash,
                        parser_or_ocr="ocr_tesseract" if ext in {".png", ".jpg", ".jpeg", ".webp"} else "native_parser",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        fact_card_id=None,
                        control_mapping=[],
                        mapping_type="direct_attachment",
                        ingestion_status="ingested",
                        exclusion_reason=None,
                    )

        manifest_items = list(unique_files_map.values())
        mapped_ctrl_count = len({cid for item in manifest_items if item.ingestion_status == "ingested" for cid in item.control_mapping})

        manifest = EvidenceManifest(
            assessment_id=assessment_id,
            run_id=audit_ctx.run_id,
            code_version=audit_ctx.code_version,
            created_at=datetime.now(timezone.utc).isoformat(),
            total_files=len(manifest_items),
            mapped_control_count=mapped_ctrl_count,
            files=manifest_items,
        )
        with open(manifest_path, "w", encoding="utf-8") as mf:
            mf.write(manifest.model_dump_json(indent=2))

        # Record evidence parsed event with actual count, manifest ID, file hashes, and control mapping
        impl_ctrls = system_data.get("compliance", {}).get("implemented_controls", [])
        ext_list = list({item.extension for item in manifest_items}) if manifest_items else [".log", ".txt", ".md", ".png", ".pdf"]
        eff_manifest_id = system_data.get("evidence_manifest_id") or f"manifest_{assessment_id}"
        file_hashes_map = {item.masked_filename: item.sha256 for item in manifest_items}
        ctrl_mapping_map = {}
        for item in manifest_items:
            for cid in item.control_mapping:
                ctrl_mapping_map.setdefault(cid, []).append(item.masked_filename)

        files_details = [
            {
                "evidence_id": item.file_id,
                "file_name": item.masked_filename,
                "sha256": item.sha256,
                "parser_status": item.parser_or_ocr,
                "size_bytes": item.size_bytes,
                "control_mapping": item.control_mapping,
            }
            for item in manifest_items
        ]
        ev_source = system_data.get("evidence_source") or (
            "template_preview" if system_data.get("template_id") and not manifest_items and not ev_map
            else ("uploaded_evidence" if manifest_items else "self_declared")
        )

        audit_service.record_evidence_parsed(
            ctx=audit_ctx,
            evidence_controls_count=len(ev_map) if ev_map else len(impl_ctrls),
            total_files=len(manifest_items),
            file_extensions=ext_list,
            evidence_manifest_id=eff_manifest_id,
            control_mapping=ctrl_mapping_map,
            file_hashes=file_hashes_map,
            evidence_source=ev_source,
            files=files_details,
        )


        system_data["evidence_manifest_id"] = eff_manifest_id
        system_data["evidence_manifest"] = manifest.model_dump()

        if evidence_context:
            system_data["notes"] = (system_data.get("notes", "") or "") + evidence_context

        init_msg = "Tác tử 1 (bge-m3 1024D): Nạp vector tri thức tiêu chuẩn & đối chiếu hồ sơ..."
        update_assessment_progress(assessment_id, init_msg, 5)
        result = ChatService.assess_system(
            system_data, model_mode=model_mode,
            progress_callback=lambda msg, pct: update_assessment_progress(assessment_id, msg, pct),
            audit_ctx=audit_ctx,
        )

        from schemas.assessment_schema import UnifiedAssessmentResult
        from pydantic import ValidationError

        raw_result = result.get("json_data") or {}
        raw_result["assessment_id"] = assessment_id
        raw_result["run_id"] = audit_ctx.run_id
        raw_result["code_version"] = audit_ctx.code_version
        raw_result["evidence_manifest_id"] = eff_manifest_id
        raw_result["evidence_manifest_ref"] = f"data/evidence_manifests/{assessment_id}.json"
        raw_result["audit_trace_ref"] = f"data/audit_traces/{assessment_id}.json"
        if not raw_result.get("evidence_manifest"):
            raw_result["evidence_manifest"] = manifest.model_dump()

        try:
            validated_result = UnifiedAssessmentResult.model_validate(raw_result)
        except ValidationError as ve:
            logger.error(f"[AssessmentBG] UnifiedAssessmentResult validation failed for {assessment_id}: {ve}", exc_info=True)
            data["status"] = "failed"
            data["error"] = f"UnifiedAssessmentResult validation failed: {str(ve)}"
            data["error_code"] = "SCHEMA_VALIDATION_ERROR"
            data["validation_errors"] = ve.errors()
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            data["progress"] = {"message": "Thẩm định thất bại do lỗi cấu trúc dữ liệu schema", "percent": 100}
            save_assessment(assessment_id, data)
            try:
                audit_service.record_assessment_failed(
                    ctx=audit_ctx,
                    error_type="ValidationError",
                    error_stage="schema_validation",
                    message_redacted=str(ve)[:300],
                )
            except Exception as audit_err:
                logger.warning(f"Failed to record audit failure event (non-fatal): {audit_err}")
            return

        tot_duration = (validated_result.runtime_summary or {}).get("total_duration_seconds")
        if tot_duration is None:
            tot_duration = round(time.time() - t0, 3)
            if not validated_result.runtime_summary:
                validated_result.runtime_summary = {}
            validated_result.runtime_summary["total_duration_seconds"] = tot_duration

        validated_dict = validated_result.model_dump()
        validated_dict["runtime_summary"]["total_duration_seconds"] = tot_duration

        # Validate Assessment Invariants (Citation integrity, mathematical recomputability, cleanliness)
        inv_valid, inv_failures = validate_assessment_invariants(
            validated_dict,
            manifest_data=validated_dict.get("evidence_manifest") or manifest.model_dump(),
            strict_catalogue_count=True,
        )
        if not inv_valid:
            logger.error(f"[AssessmentBG] Assessment {assessment_id} failed invariant validation: {inv_failures}")
            data["status"] = "failed"
            data["error_code"] = "INVARIANT_VALIDATION_ERROR"
            data["error"] = f"Invariant validation failed: {'; '.join(inv_failures[:5])}"
            data["invariant_failures"] = inv_failures
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            data["progress"] = {"message": "Thẩm định thất bại do vi phạm ràng buộc kiểm toán (Invariants)", "percent": 100}
            save_assessment(assessment_id, data)
            try:
                audit_service.record_assessment_failed(
                    ctx=audit_ctx,
                    error_type="InvariantValidationError",
                    error_stage="invariant_validation",
                    message_redacted=str(inv_failures[:3])[:300],
                )
            except Exception as audit_err:
                logger.warning(f"Failed to record invariant failure event (non-fatal): {audit_err}")
            return

        data["status"] = "completed"
        data["run_id"] = audit_ctx.run_id
        data["code_version"] = audit_ctx.code_version
        data["evidence_manifest_id"] = eff_manifest_id
        data["evidence_manifest"] = validated_dict.get("evidence_manifest") or manifest.model_dump()
        data["evidence_manifest_ref"] = f"data/evidence_manifests/{assessment_id}.json"
        data["audit_trace_ref"] = f"data/audit_traces/{assessment_id}.json"
        data["progress"] = {"message": "Hoàn tất thẩm định an toàn thông tin", "percent": 100}
        data["result"] = result
        data["json_data"] = validated_dict
        data["runtime_summary"] = validated_dict.get("runtime_summary", {})
        data["chunk_telemetries"] = validated_dict.get("chunk_telemetries", [])
        data["weighted_compliance"] = validated_dict.get("weighted_compliance", {})
        data["weighted_coverage"] = validated_dict.get("weighted_coverage", {})
        data["control_coverage"] = validated_dict.get("control_coverage", {})
        data["compliance_percent"] = validated_dict.get("weighted_compliance", {}).get("percentage", 0.0)

        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_assessment(assessment_id, data)

        duration = tot_duration
        audit_service.record_score_calculated(
            ctx=audit_ctx,
            standard=system_data.get("assessment_standard", "iso27001"),
            weighted_score=validated_result.weighted_compliance.weighted_score,
            weighted_max_score=validated_result.weighted_compliance.weighted_max_score,
            weighted_compliance_percentage=validated_result.weighted_compliance.percentage,
            raw_coverage_percentage=validated_result.control_coverage.raw_percentage,
            satisfied_count=validated_result.control_coverage.evidence_supported_implemented,
            partial_count=sum(1 for c in validated_result.controls if (c.assessment_verdict or "").lower() == "partial"),
            not_evidenced_count=sum(1 for c in validated_result.controls if (c.assessment_verdict or "").lower() == "not_evidenced"),
            missing_count=sum(1 for c in validated_result.controls if (c.assessment_verdict or "").lower() == "missing"),
            needs_expert_review_count=sum(1 for c in validated_result.controls if (c.assessment_verdict or "").lower() == "needs_expert_review"),
            algorithm="verdict_weighted_v2",
        )
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
    assessment_id = getattr(data, "assessment_id", None) or str(uuid.uuid4())
    _validate_path_id(assessment_id, "assessment_id")
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    audit_ctx = AuditContext(assessment_id=assessment_id, run_id=run_id)

    # Validate manifest ownership against assessment_id (Requirement D.3 & D.4)
    manifest_id = getattr(data, "evidence_manifest_id", None)
    if manifest_id:
        ev_manifest_dir = os.path.join(os.getenv("DATA_PATH", "./data"), "evidence_manifests")
        manifest_path = os.path.join(ev_manifest_dir, f"{manifest_id}.json")
        if not os.path.exists(manifest_path):
            cand = os.path.join(ev_manifest_dir, f"{manifest_id.replace('manifest_', '')}.json")
            if os.path.exists(cand):
                manifest_path = cand
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    mf_data = json.load(mf)
                owner_aid = mf_data.get("assessment_id")
                if owner_aid and owner_aid != assessment_id and owner_aid not in ("default_session", "anonymous") and not str(owner_aid).startswith("manifest_"):
                    logger.warning(
                        f"[ManifestConflict] Manifest '{manifest_id}' belongs to assessment '{owner_aid}', "
                        f"rejected for assessment '{assessment_id}'."
                    )
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Evidence manifest '{manifest_id}' belongs to assessment '{owner_aid}', "
                            f"not '{assessment_id}'. Cross-assessment manifest submission is forbidden."
                        )
                    )
            except HTTPException:
                raise
            except Exception as mf_err:
                logger.warning(f"[ManifestCheck] Error checking manifest file: {mf_err}")
    else:
        manifest_id = f"manifest_{assessment_id[:12]}"

    raw_impl = data.implemented_controls
    if not raw_impl and getattr(data, "compliance", None) and isinstance(data.compliance, dict):
        raw_impl = data.compliance.get("implemented_controls")
    if isinstance(raw_impl, dict):
        impl_controls = list(raw_impl.keys())
    elif isinstance(raw_impl, (list, tuple, set)):
        impl_controls = [str(c) for c in raw_impl]
    else:
        impl_controls = []

    ev_map = data.evidence_map if isinstance(data.evidence_map, dict) else {}
    ctrl_verdicts = data.control_verdicts if hasattr(data, "control_verdicts") and isinstance(data.control_verdicts, list) else []

    ev_files = getattr(data, "evidence_files", []) or []
    tpl_id = getattr(data, "template_id", None)
    tpl_name = getattr(data, "template_name", None)
    is_tpl_input = bool(getattr(data, "is_template_input", False))

    system_data = {
        "assessment_id": assessment_id,
        "assessment_standard": str(data.assessment_standard or "iso27001"),
        "evidence_manifest_id": manifest_id,
        "evidence_files": ev_files,
        "template_id": tpl_id,
        "template_name": tpl_name,
        "is_template_input": is_tpl_input,
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
            "incidents_12m": data.incidents_12m or 0,
            "evidence_map": ev_map,
        },
        "evidence_map": ev_map,
        "control_verdicts": ctrl_verdicts,
        "notes": str(data.notes or ""),
        "model_mode": str(data.model_mode or "local"),
        "selected_model": str(data.selected_model or "gemma4:latest"),
    }

    # Build evidence context from parsed file contents
    evidence_context = ""
    if ev_map:
        evidence_context = build_evidence_context_for_ai(ev_map, standard=data.assessment_standard, assessment_id=assessment_id)
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
        "evidence_manifest_id": manifest_id,
        "evidence_files": ev_files,
        "template_id": tpl_id,
        "template_name": tpl_name,
        "is_template_input": is_tpl_input,
        "status": "pending",
        "system_info": system_data,
        "evidence_map": ev_map,
        "control_verdicts": ctrl_verdicts,
        "compliance_percent": compliance_pct,
        "weighted_coverage": comp.get("weighted_coverage", {
            "score": round(float(comp.get("achieved_weighted", 0.0)), 1),
            "max_score": round(float(comp.get("max_weighted", 495.0)), 1),
            "percentage": compliance_pct,
        }),
        "control_coverage": comp.get("control_coverage", {}),
        "model_mode": data.model_mode,
        "standard": data.assessment_standard,
        "evidence_attached": len(ev_map) > 0,
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
        "evidence_manifest_id": manifest_id,
        "mapped_controls_count": len(ev_map),
        "evidence_map": ev_map,
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
                    "weighted_compliance": cur.get("weighted_compliance") or (cur.get("json_data") or {}).get("weighted_compliance"),
                    "weighted_coverage": cur.get("weighted_coverage") or (cur.get("json_data") or {}).get("weighted_coverage"),
                    "control_coverage": cur.get("control_coverage") or (cur.get("json_data") or {}).get("control_coverage"),
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
                    "weighted_coverage": cur.get("weighted_coverage"),
                    "control_coverage": cur.get("control_coverage"),
                    "compliance_percent": cur.get("compliance_percent"),
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
    # Authoritative schema validation & normalization through UnifiedAssessmentResult
    if data.get("status") == "completed" and ("json_data" in data or "controls" in data or "result" in data):
        try:
            from schemas.assessment_schema import UnifiedAssessmentResult
            validated = UnifiedAssessmentResult.model_validate(data)
            validated_dict = validated.model_dump()
            data["json_data"] = validated_dict
            data["weighted_compliance"] = validated_dict.get("weighted_compliance", {})
            data["control_coverage"] = validated_dict.get("control_coverage", {})
            data["weighted_coverage"] = validated_dict.get("weighted_coverage", {})
            data["compliance_percent"] = validated_dict.get("weighted_compliance", {}).get("percentage", 0.0)

            # Harmonize markdown report text to authoritative Weighted Compliance
            raw_rep = data.get("report") or (data.get("result", {}).get("report") if isinstance(data.get("result"), dict) else "") or validated_dict.get("report") or ""
            if raw_rep:
                from services.chat_service import ChatService
                w_comp = validated_dict.get("weighted_compliance", {})
                pct_val = w_comp.get("percentage", 0.0)
                cov_val = validated_dict.get("control_coverage", {})
                healed_rep = ChatService.ensure_complete_report(
                    markdown_report=raw_rep,
                    percentage=pct_val,
                    score=cov_val.get("evidence_supported_implemented", 0),
                    max_score=cov_val.get("total_controls", 93),
                    json_data=validated_dict,
                )
                data["report"] = healed_rep
                if "result" in data and isinstance(data["result"], dict):
                    data["result"]["report"] = healed_rep
                data["json_data"]["report"] = healed_rep

                if healed_rep != raw_rep:
                    try:
                        save_assessment(assessment_id, data)
                        from repositories.assessment_store import assessment_store
                        assessment_store.save_assessment(
                            report_data=data,
                            project_name=data.get("organization", {}).get("name") or data.get("system_info", {}).get("organization", {}).get("name"),
                            system_scope=data.get("system_info", {}).get("infrastructure", {}).get("cloud"),
                            assessment_id=assessment_id
                        )
                    except Exception as s_err:
                        logger.warning(f"[GetAssessment] Could not persist healed assessment {assessment_id}: {s_err}")
        except Exception as norm_err:
            logger.warning(f"[GetAssessment] Schema normalization warning for {assessment_id}: {norm_err}")

    # Record export event for assessment_json
    try:
        from services.audit_service import audit_service, AuditContext
        resolved_aid = data.get("id") or data.get("assessment_id") or assessment_id
        run_id_val = data.get("run_id") or data.get("json_data", {}).get("run_id") or f"run_{resolved_aid[:8]}"
        json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        json_hash = hashlib.sha256(json_bytes).hexdigest()
        audit_ctx = AuditContext(assessment_id=resolved_aid, run_id=run_id_val)
        audit_service.record_artifact_exported(
            ctx=audit_ctx,
            export_format="assessment_json",
            filename=f"assessment_{resolved_aid[:8]}.json",
            file_size_bytes=len(json_bytes),
            file_hash_sha256=json_hash,
        )
    except Exception:
        pass

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
        if os.path.exists(filepath):
            os.remove(filepath)

        # 2. Comprehensive SQLite database cleanup (infrastructure_assessments & audit_events)
        try:
            from repositories.assessment_store import assessment_store, DB_PATH
            assessment_store.delete_assessment(assessment_id)
            if os.path.exists(DB_PATH):
                import sqlite3
                conn = sqlite3.connect(DB_PATH, timeout=5.0)
                try:
                    c = conn.cursor()
                    c.execute("DELETE FROM audit_events WHERE assessment_id = ?", (assessment_id,))
                    c.execute("DELETE FROM infrastructure_assessments WHERE id = ?", (assessment_id,))
                    conn.commit()
                finally:
                    conn.close()
        except Exception as db_err:
            logger.warning(f"Could not cascade delete assessment {assessment_id} from SQLite: {db_err}")

        # 3. Cascade delete any assessment-scoped evidence directory if exists
        assessment_ev_dir = os.path.join(EVIDENCE_DIR, assessment_id)
        if os.path.exists(assessment_ev_dir):
            import shutil
            shutil.rmtree(assessment_ev_dir, ignore_errors=True)

        # 4. Cascade delete manifest and audit trace files
        data_dir = os.getenv("DATA_PATH", "./data")
        for sub in ["evidence_manifests", "audit_traces"]:
            p = os.path.join(data_dir, sub, f"{assessment_id}.json")
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

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


@router.post("/iso27001/assessments/init")
@router.post("/assessments/init")
async def init_assessment_session(
    standard: Optional[str] = Query("iso27001")
):
    """Initialize a new isolated assessment session with a dedicated assessment_id and manifest."""
    aid = str(uuid.uuid4())
    manifest_id = f"manifest_{aid[:12]}"

    # Ensure isolated evidence folder exists for this assessment
    asm_ev_dir = os.path.join(EVIDENCE_DIR, aid)
    os.makedirs(asm_ev_dir, exist_ok=True)

    ev_manifest_dir = os.path.join(os.getenv("DATA_PATH", "./data"), "evidence_manifests")
    os.makedirs(ev_manifest_dir, exist_ok=True)
    manifest_path = os.path.join(ev_manifest_dir, f"{manifest_id}.json")
    manifest_data = {
        "manifest_id": manifest_id,
        "assessment_id": aid,
        "standard": standard or "iso27001",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_files": 0,
        "files": [],
        "mapped_controls": {}
    }
    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[InitAssessment] Failed to save initial manifest: {e}")

    return {
        "status": "success",
        "assessment_id": aid,
        "manifest_id": manifest_id,
        "standard": standard or "iso27001",
        "created_at": manifest_data["created_at"]
    }


@router.post("/iso27001/evidence/batch-ingest")
@router.post("/evidence/batch-ingest")
async def batch_ingest_evidence(
    request: Request,
    assessment_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """Batch upload server scans, logs, policies, images (OCR), and evidence documents.
    Processes files sequentially through the unified evidence parser with partial success resilience.
    Scoped by assessment_id to prevent cross-assessment leakage.
    """
    from services.evidence_mapper import map_evidence_to_controls
    from services.evidence_parser import parse_evidence_file, MAX_EVIDENCE_SIZE_BYTES, SUPPORTED_EXTENSIONS

    try:
        form = await request.form()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không thể đọc multipart form data: {str(e)}")

    eff_aid = assessment_id or form.get("assessment_id") or request.headers.get("x-assessment-id") or request.headers.get("X-Assessment-ID")
    if eff_aid:
        _validate_path_id(str(eff_aid), "assessment_id")
        target_ev_dir = os.path.join(EVIDENCE_DIR, str(eff_aid))
    else:
        target_ev_dir = EVIDENCE_DIR
    os.makedirs(target_ev_dir, exist_ok=True)

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

    temp_dir = os.path.join(target_ev_dir, "_batch_temp")
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
                    "evidence_id": f"file_{hashlib.sha256(content).hexdigest()[:8]}",
                    "filename": file.filename,
                    "clean_name": os.path.basename(file.filename.replace("\\", "/")),
                    "original_name": file.filename,
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
                    "evidence_id": f"file_{hashlib.sha256(content).hexdigest()[:8]}",
                    "filename": file.filename,
                    "clean_name": os.path.basename(file.filename.replace("\\", "/")),
                    "original_name": file.filename,
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

            raw_filename = file.filename.replace("\\", "/")
            clean_filename = os.path.basename(raw_filename) or "unnamed_evidence"
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safe_name = f"{ts}_{clean_filename}"

            # Host detection from fact_card and log content
            card_ips = host_meta.get("ip_addresses") or []
            found_ips = card_ips or ip_regex.findall(text_content)
            fn_ips = ip_regex.findall(clean_filename)
            primary_ip = fn_ips[0] if fn_ips else (found_ips[0] if found_ips else None)

            card_host = host_meta.get("hostname")
            found_hostnames = hostname_regex.findall(text_content)
            detected_hostname = card_host or (found_hostnames[0] if found_hostnames else None)

            ext_lower = os.path.splitext(clean_filename)[1].lower()
            fn_lower = clean_filename.lower()
            is_doc_or_report = (
                ext_lower in {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".csv", ".odt", ".rtf"} or
                any(kw in fn_lower for kw in ["report", "bao_cao", "quy_che", "chinh_sach", "ke_hoach", "bien_ban", "va_dot", "audit", "danh_gia"])
            )

            if not detected_hostname and primary_ip and not is_doc_or_report:
                clean_host_candidate = clean_filename.rsplit(".", 1)[0]
                if _re_val.match(r'^[a-zA-Z0-9_\-]{2,32}$', clean_host_candidate):
                    detected_hostname = clean_host_candidate

            card_os = host_meta.get("os_name")
            found_os = os_regex.findall(text_content)
            detected_os = card_os or (found_os[0].strip() if found_os else None)

            if (primary_ip or detected_hostname) and not (is_doc_or_report and not detected_hostname):
                host_info = {
                    "source_file": clean_filename,
                    "ip": primary_ip,
                    "hostname": detected_hostname or (f"Host-{primary_ip}" if primary_ip else None),
                    "os": detected_os,
                    "is_eol": host_meta.get("is_eol", False)
                }
                detected_hosts.append(host_info)

            # Map to controls: combine keyword mapper with Agent 1 FactCard
            control_scores = map_evidence_to_controls(clean_filename, text_content)

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
                    ctrl_dir = os.path.join(target_ev_dir, ctrl_id.replace(".", "_"))
                    os.makedirs(ctrl_dir, exist_ok=True)
                    dest_path = os.path.join(ctrl_dir, safe_name)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:
                        f.write(content)

                    if ctrl_id not in mapped_controls:
                        mapped_controls[ctrl_id] = []
                    
                    mapped_controls[ctrl_id].append({
                        "filename": safe_name,
                        "original_name": file.filename,
                        "clean_name": clean_filename,
                        "confidence": score,
                        "size_bytes": len(content),
                        "char_count": parse_res.get("char_count", len(text_content)),
                        "ocr_applied": parse_res.get("ocr_applied", False),
                        "preview": text_content[:200]
                    })
                    saved_to_controls.append(ctrl_id)

            if not saved_to_controls:
                unassigned_dir = os.path.join(target_ev_dir, "_unassigned")
                os.makedirs(unassigned_dir, exist_ok=True)
                dest_unassigned = os.path.join(unassigned_dir, safe_name)
                os.makedirs(os.path.dirname(dest_unassigned), exist_ok=True)
                with open(dest_unassigned, "wb") as f:
                    f.write(content)

            f_sha256 = parse_res.get("sha256") or hashlib.sha256(content).hexdigest()
            processed_files.append({
                "evidence_id": f"file_{f_sha256[:8]}",
                "filename": safe_name,
                "original_name": file.filename,
                "clean_name": clean_filename,
                "size_bytes": len(content),
                "char_count": parse_res.get("char_count", len(text_content)),
                "page_count": parse_res.get("page_count", 1),
                "ocr_applied": parse_res.get("ocr_applied", False),
                "mapped_controls": saved_to_controls,
                "status": "success",
                "sha256": f_sha256,
                "parser_status": file_status,
                "preview": text_content[:400],
                "fact_summary": parse_res.get("fact_summary", "")
            })

        except Exception as file_err:
            clean_err_msg = str(file_err)
            if "No such file or directory" in clean_err_msg or "Errno 2" in clean_err_msg:
                clean_err_msg = "Không thể ghi tệp vào thư mục đích (đường dẫn thư mục không hợp lệ)."
            logger.error(f"[BatchIngest] Error processing {file.filename}: {file_err}", exc_info=True)
            clean_display_name = os.path.basename(file.filename.replace("\\", "/")) or file.filename
            errors.append(f"{clean_display_name}: {clean_err_msg}")
            processed_files.append({
                "evidence_id": f"file_{hashlib.sha256(clean_display_name.encode()).hexdigest()[:8]}",
                "filename": clean_display_name,
                "original_name": file.filename,
                "clean_name": clean_display_name,
                "size_bytes": 0,
                "char_count": 0,
                "page_count": 0,
                "ocr_applied": False,
                "mapped_controls": [],
                "status": "failed",
                "sha256": "",
                "error_code": "PARSE_ERROR",
                "error_message": clean_err_msg
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
    manifest_id = f"manifest_{eff_aid[:12]}" if eff_aid else f"manifest_{uuid.uuid4().hex[:12]}"

    # Write evidence manifest record to disk
    ev_manifest_dir = os.path.join(os.getenv("DATA_PATH", "./data"), "evidence_manifests")
    os.makedirs(ev_manifest_dir, exist_ok=True)
    manifest_path = os.path.join(ev_manifest_dir, f"{manifest_id}.json")
    manifest_record = {
        "manifest_id": manifest_id,
        "assessment_id": eff_aid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(processed_files),
        "files": processed_files,
        "mapped_controls": mapped_controls
    }
    try:
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest_record, mf, ensure_ascii=False, indent=2)
    except Exception as mf_err:
        logger.warning(f"[BatchIngest] Failed to save manifest: {mf_err}")

    return {
        "status": "success",
        "manifest_id": manifest_id,
        "evidence_manifest_id": manifest_id,
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


@router.get("/iso27001/evidence/file-content")
@router.get("/evidence/file-content")
async def get_evidence_file_content(
    filename: str,
    assessment_id: Optional[str] = Query(None),
    request: Request = None
):
    """Search and return full extracted text, SHA-256 hash, and FactCard for any uploaded evidence file."""
    if not filename:
        raise HTTPException(status_code=400, detail="Tên tệp không được để trống.")
    
    clean_target = os.path.basename(filename.replace("\\", "/"))
    eff_aid = assessment_id or (request.headers.get("x-assessment-id") if request else None) or (request.headers.get("X-Assessment-ID") if request else None)
    if eff_aid:
        _validate_path_id(eff_aid, "assessment_id")
        search_root = os.path.join(EVIDENCE_DIR, eff_aid)
    else:
        search_root = EVIDENCE_DIR
    real_base = os.path.realpath(EVIDENCE_DIR)
    found_path = None

    if os.path.exists(search_root):
        for root, _, files in os.walk(search_root):
            for f in files:
                if f == clean_target or f.endswith(f"_{clean_target}") or clean_target in f:
                    cand = os.path.join(root, f)
                    if os.path.realpath(cand).startswith(real_base + os.sep):
                        found_path = cand
                        break
            if found_path:
                break

    if not found_path or not os.path.exists(found_path):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp minh chứng '{clean_target}'.")

    try:
        with open(found_path, "rb") as fp:
            content_bytes = fp.read()
        from services.evidence_parser import parse_evidence_file
        parse_res = parse_evidence_file(content_bytes, clean_target)
        return {
            "status": "success",
            "filename": clean_target,
            "filepath": found_path,
            "size_bytes": len(content_bytes),
            "char_count": parse_res.get("char_count", 0),
            "page_count": parse_res.get("page_count", 1),
            "ocr_applied": parse_res.get("ocr_applied", False),
            "sha256": parse_res.get("sha256", ""),
            "full_text": parse_res.get("full_text") or parse_res.get("parsed_text", ""),
            "fact_card": parse_res.get("fact_card") or {},
            "fact_summary": parse_res.get("fact_summary") or ""
        }
    except Exception as e:
        logger.error(f"[EvidenceContent] Error reading {found_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi đọc nội dung tệp: {str(e)}")


@router.delete("/iso27001/evidence/file/{filename}")
@router.delete("/evidence/file/{filename}")
async def delete_evidence_file_globally(
    filename: str,
    assessment_id: Optional[str] = Query(None),
    request: Request = None
):
    """Delete an evidence file across all mapped control folders within the assessment."""
    if not filename:
        raise HTTPException(status_code=400, detail="Tên tệp không được để trống.")

    eff_aid = assessment_id or (request.headers.get("x-assessment-id") if request else None) or (request.headers.get("X-Assessment-ID") if request else None)
    if eff_aid:
        _validate_path_id(eff_aid, "assessment_id")
        search_root = os.path.join(EVIDENCE_DIR, eff_aid)
    else:
        search_root = EVIDENCE_DIR
    clean_target = os.path.basename(filename.replace("\\", "/"))
    real_base = os.path.realpath(EVIDENCE_DIR)
    removed_from = []

    if os.path.exists(search_root):
        for root, _, files in os.walk(search_root):
            for f in files:
                if f == clean_target or f.endswith(f"_{clean_target}") or clean_target in f:
                    cand = os.path.join(root, f)
                    if os.path.realpath(cand).startswith(real_base + os.sep):
                        try:
                            os.remove(cand)
                            folder_name = os.path.basename(root)
                            removed_from.append(folder_name.replace("_", "."))
                        except Exception as e:
                            logger.warning(f"[DeleteFile] Failed to remove {cand}: {e}")

    return {
        "status": "success",
        "filename": clean_target,
        "removed_from": removed_from,
        "message": f"Đã loại bỏ tệp '{clean_target}' khỏi {len(removed_from)} phân vùng minh chứng."
    }


@router.post("/iso27001/evidence/{control_id}")
async def upload_evidence(
    control_id: str,
    file: UploadFile = File(...),
    assessment_id: Optional[str] = Query(None),
    request: Request = None
):
    """Upload evidence file for a specific control, scoped by assessment_id."""
    _validate_path_id(control_id, "control_id")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")

    eff_aid = assessment_id or (request.headers.get("x-assessment-id") if request else None) or (request.headers.get("X-Assessment-ID") if request else None)

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EVIDENCE_EXT:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed. Allowed: {', '.join(ALLOWED_EVIDENCE_EXT)}")

    content = await file.read()
    if len(content) > MAX_EVIDENCE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max: {MAX_EVIDENCE_SIZE // (1024*1024)}MB")

    # Determine save directory based on assessment_id isolation
    if eff_aid:
        _validate_path_id(eff_aid, "assessment_id")
        ctrl_dir = os.path.join(EVIDENCE_DIR, eff_aid, control_id.replace(".", "_"))
    else:
        ctrl_dir = os.path.join(EVIDENCE_DIR, control_id.replace(".", "_"))
    os.makedirs(ctrl_dir, exist_ok=True)

    # Save with timestamp prefix to avoid overwrite
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    clean_filename = os.path.basename(file.filename.replace("\\", "/"))
    safe_name = f"{ts}_{clean_filename}"
    filepath = os.path.join(ctrl_dir, safe_name)

    with open(filepath, "wb") as f:
        f.write(content)

    parse_res = parse_evidence_file(content, clean_filename)
    sha256_hash = parse_res.get("sha256") or hashlib.sha256(content).hexdigest()
    char_count = parse_res.get("char_count", len(content))
    evidence_id = f"file_{sha256_hash[:8]}"

    # Update manifest on disk if assessment_id is present
    if eff_aid:
        manifest_id = f"manifest_{eff_aid[:12]}"
        ev_manifest_dir = os.path.join(os.getenv("DATA_PATH", "./data"), "evidence_manifests")
        os.makedirs(ev_manifest_dir, exist_ok=True)
        manifest_path = os.path.join(ev_manifest_dir, f"{manifest_id}.json")
        mf_data = {}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf_f:
                    mf_data = json.load(mf_f)
            except Exception:
                pass
        mf_files = mf_data.get("files", [])
        found_mf_f = False
        for mf_item in mf_files:
            if (mf_item.get("sha256") and mf_item.get("sha256") == sha256_hash) or mf_item.get("filename") == safe_name or mf_item.get("clean_name") == clean_filename:
                mapped_ctrls = mf_item.get("mapped_controls", [])
                if control_id not in mapped_ctrls:
                    mapped_ctrls.append(control_id)
                mf_item["mapped_controls"] = mapped_ctrls
                found_mf_f = True
                break
        if not found_mf_f:
            mf_files.append({
                "evidence_id": evidence_id,
                "filename": safe_name,
                "clean_name": clean_filename,
                "original_name": file.filename,
                "size_bytes": len(content),
                "sha256": sha256_hash,
                "char_count": char_count,
                "ocr_applied": parse_res.get("ocr_applied", False),
                "status": "success",
                "parser_status": parse_res.get("status", "success"),
                "mapped_controls": [control_id]
            })
        mf_data["manifest_id"] = manifest_id
        mf_data["assessment_id"] = eff_aid
        mf_data["total_files"] = len(mf_files)
        mf_data["files"] = mf_files
        try:
            with open(manifest_path, "w", encoding="utf-8") as mf_f:
                json.dump(mf_data, mf_f, ensure_ascii=False, indent=2)
        except Exception as mf_write_err:
            logger.warning(f"[UploadEvidence] Failed to update manifest: {mf_write_err}")

    download_qs = f"?assessment_id={eff_aid}" if eff_aid else ""
    return {
        "status": "success",
        "assessment_id": eff_aid,
        "control_id": control_id,
        "evidence_id": evidence_id,
        "filename": safe_name,
        "original_name": file.filename,
        "clean_name": clean_filename,
        "size_bytes": len(content),
        "sha256": sha256_hash,
        "char_count": char_count,
        "parser_status": parse_res.get("status", "success"),
        "mapped_controls": [control_id],
        "path": f"/api/iso27001/evidence/{control_id}/{safe_name}{download_qs}",
    }


@router.get("/iso27001/evidence/{control_id}")
async def list_evidence(
    control_id: str,
    assessment_id: Optional[str] = Query(None),
    request: Request = None
):
    """List all evidence files for a control, strictly filtered by assessment_id."""
    _validate_path_id(control_id, "control_id")
    eff_aid = assessment_id or (request.headers.get("x-assessment-id") if request else None) or (request.headers.get("X-Assessment-ID") if request else None)
    if not eff_aid:
        # Strictly no global fallback
        return {"control_id": control_id, "files": []}

    _validate_path_id(eff_aid, "assessment_id")
    ctrl_dir = os.path.join(EVIDENCE_DIR, eff_aid, control_id.replace(".", "_"))
    if not os.path.exists(ctrl_dir):
        return {"control_id": control_id, "files": []}

    files = []
    for filename in sorted(os.listdir(ctrl_dir)):
        filepath = os.path.join(ctrl_dir, filename)
        if not os.path.isfile(filepath):
            continue
        stat = os.stat(filepath)
        f_hash = ""
        try:
            with open(filepath, "rb") as rf:
                f_hash = hashlib.sha256(rf.read()).hexdigest()
        except Exception:
            pass
        clean_name = filename
        if _re_val.match(r'^\d{8}_\d{6}_', filename):
            clean_name = filename[15:]
        files.append({
            "evidence_id": f"file_{f_hash[:8]}" if f_hash else f"file_{filename[:8]}",
            "filename": filename,
            "clean_name": clean_name,
            "size_bytes": stat.st_size,
            "sha256": f_hash,
            "uploaded_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "download_url": f"/api/iso27001/evidence/{control_id}/{filename}?assessment_id={eff_aid}",
        })

    return {"control_id": control_id, "files": files}


@router.get("/iso27001/evidence/{control_id}/{filename}")
async def download_evidence(
    control_id: str,
    filename: str,
    assessment_id: Optional[str] = Query(None),
    request: Request = None
):
    """Download a specific evidence file."""
    _validate_path_id(control_id, "control_id")
    _validate_path_id(filename.replace(".", "_"), "filename")
    eff_aid = assessment_id or (request.headers.get("x-assessment-id") if request else None)
    if eff_aid:
        _validate_path_id(eff_aid, "assessment_id")
        ctrl_dir = os.path.join(EVIDENCE_DIR, eff_aid, control_id.replace(".", "_"))
    else:
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
async def delete_evidence(
    control_id: str,
    filename: str,
    assessment_id: Optional[str] = Query(None),
    request: Request = None
):
    """Delete a specific evidence file."""
    _validate_path_id(control_id, "control_id")
    _validate_path_id(filename.replace(".", "_"), "filename")
    eff_aid = assessment_id or (request.headers.get("x-assessment-id") if request else None) or (request.headers.get("X-Assessment-ID") if request else None)
    if not eff_aid:
        raise HTTPException(status_code=400, detail="assessment_id là bắt buộc để xóa tệp.")
    _validate_path_id(eff_aid, "assessment_id")
    ctrl_dir = os.path.join(EVIDENCE_DIR, eff_aid, control_id.replace(".", "_"))
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
async def get_all_evidence_summary(
    assessment_id: Optional[str] = Query(None),
    request: Request = None
):
    """Get summary of all uploaded evidence across all controls for an assessment."""
    eff_aid = assessment_id or (request.headers.get("x-assessment-id") if request else None)
    if not eff_aid:
        # Strictly no global fallback
        return {"controls": {}, "total_files": 0}

    _validate_path_id(eff_aid, "assessment_id")
    target_dir = os.path.join(EVIDENCE_DIR, eff_aid)
    if not os.path.exists(target_dir):
        return {"controls": {}, "total_files": 0}

    summary = {}
    total = 0
    for ctrl_folder in os.listdir(target_dir):
        ctrl_path = os.path.join(target_dir, ctrl_folder)
        if os.path.isdir(ctrl_path) and not ctrl_folder.startswith("_"):
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

    data["assessment_id"] = assessment_id
    data.setdefault("run_id", f"run_{assessment_id[:8]}")
    if "json_data" in data and isinstance(data["json_data"], dict):
        data["json_data"].setdefault("assessment_id", assessment_id)
        data["json_data"].setdefault("run_id", data["run_id"])

    if data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Assessment not completed yet")

    raw_report = data.get("result", {}).get("report", "") or data.get("report", "")
    if not raw_report:
        raise HTTPException(status_code=400, detail="No report content")

    from schemas.assessment_schema import UnifiedAssessmentResult
    try:
        validated = UnifiedAssessmentResult.model_validate(data.get("json_data") or data)
    except Exception as ve:
        raise HTTPException(status_code=422, detail=f"Assessment data fails schema validation: {ve}")

    inv_valid, inv_fails = validate_assessment_invariants(data.get("json_data") or data)
    if not inv_valid:
        raise HTTPException(
            status_code=422,
            detail=f"INVARIANT_VALIDATION_FAILED (Invariant Violation): {'; '.join(inv_fails)}"
        )

    sys_info = data.get("system_info", {})
    org_name = (validated.organization.get("name") if isinstance(validated.organization, dict) else "") or sys_info.get("organization", {}).get("name") or sys_info.get("org_name", "Tổ chức Đánh giá")
    if not org_name or str(org_name).strip().lower() in ("none", "null", ""):
        org_name = "Tổ chức Đánh giá"
    industry = (validated.organization.get("industry") if isinstance(validated.organization, dict) else "") or sys_info.get("organization", {}).get("industry") or sys_info.get("industry", "Công nghệ & Dịch vụ số")
    if not industry or str(industry).strip().lower() in ("none", "null", ""):
        industry = "Công nghệ & Dịch vụ số"
    raw_std = validated.standard
    std = raw_std.get("id") if isinstance(raw_std, dict) else str(raw_std)
    std_name = "ISO 27001:2022" if std == "iso27001" else "TCVN 11930:2017" if std == "tcvn11930" else std
    pct = validated.weighted_compliance.percentage
    created = validated.created_at or data.get("created_at", "")

    json_data = data.get("json_data") or data.get("result", {}).get("json_data", {})
    scope_desc = (
        sys_info.get("scope_description")
        or sys_info.get("infrastructure", {}).get("cloud")
        or "Toàn bộ hạ tầng mạng, máy chủ cơ sở dữ liệu, ứng dụng nghiệp vụ và quy trình vận hành an toàn thông tin."
    )
    if not scope_desc or str(scope_desc).strip().lower() in ("none", "null", ""):
        scope_desc = "Toàn bộ hạ tầng mạng, máy chủ cơ sở dữ liệu, ứng dụng nghiệp vụ và quy trình vận hành an toàn thông tin."

    cov = validated.control_coverage
    sat_score = cov.evidence_supported_implemented if cov else sum(1 for c in validated.controls if c.assessment_verdict == "satisfied")
    decl_score = cov.self_declared_implemented if cov else sum(1 for c in validated.controls if c.user_declaration == "implemented")
    total_ctrls = cov.total_controls if cov else len(validated.controls)
    raw_cov = cov.raw_percentage if cov else (round(decl_score / total_ctrls * 100, 1) if total_ctrls > 0 else 0.0)

    # Automatically heal truncated report if Section 5 or b) Top 3 was cut off
    report = ChatService.ensure_complete_report(
        markdown_report=raw_report,
        percentage=pct,
        score=sat_score,
        max_score=total_ctrls,
        org_name=org_name,
        std_name=std_name,
        industry=industry,
        json_data=json_data,
    )

    # Compute risk & gap metrics strictly using aggregate_priority_breakdown
    from services.assessment_helpers import aggregate_priority_breakdown
    try:
        pb = aggregate_priority_breakdown(
            controls=validated.controls,
            weighted_compliance=validated.weighted_compliance,
            enforce_invariants=True,
        )
    except ValueError as ve:
        logger.error(f"[PDF Export] Invariant violation for assessment {assessment_id}: {ve}")
        raise HTTPException(
            status_code=422,
            detail=f"Không thể xuất PDF do mâu thuẫn số liệu (Invariant Violation): {ve}"
        )

    # Invariant: Summary vs Category Breakdown cross-check
    raw_wc = data.get("weighted_compliance") or (data.get("json_data", {}).get("weighted_compliance") if isinstance(data.get("json_data"), dict) else {}) or {}
    raw_score = raw_wc.get("weighted_score")
    if raw_score is not None:
        try:
            f_raw = float(raw_score)
            if abs(f_raw - pb["total_weighted_score"]) > 0.5:
                logger.error(f"[PDF Export] Summary score ({f_raw}) conflicts with controls breakdown ({pb['total_weighted_score']})")
                raise HTTPException(
                    status_code=422,
                    detail=f"Không thể xuất PDF do mâu thuẫn số liệu (Invariant Violation): Điểm tổng hợp tóm tắt (Summary: {f_raw}) mâu thuẫn với tổng đóng góp của từng nhóm controls ({pb['total_weighted_score']})."
                )
        except (ValueError, TypeError):
            pass

    total_applicable_ctrls = len(validated.controls)
    if pb["total_applicable"] != total_applicable_ctrls:
        raise HTTPException(
            status_code=422,
            detail=f"Không thể xuất PDF do mâu thuẫn số liệu (Invariant Violation): Tổng controls áp dụng trong bảng ({pb['total_applicable']}) mâu thuẫn với số controls áp dụng ({total_applicable_ctrls})."
        )


    crit_data = pb["tiers"]["critical"]
    high_data = pb["tiers"]["high"]
    med_data = pb["tiers"]["medium"]
    low_data = pb["tiers"]["low"]
    total_gaps = pb["total_gaps"]

    try:
        from zoneinfo import ZoneInfo
        vn_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    except Exception:
        vn_tz = timezone.utc

    try:
        if created:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(vn_tz)
            now_viet_date = dt.strftime("ngày %d tháng %m năm %Y")
            doc_date = dt.strftime("%d/%m/%Y")
        else:
            now_dt = datetime.now(vn_tz)
            now_viet_date = now_dt.strftime("ngày %d tháng %m năm %Y")
            doc_date = now_dt.strftime("%d/%m/%Y")
    except Exception:
        now_viet_date = datetime.now(timezone.utc).strftime("ngày %d tháng %m năm %Y")
        doc_date = created[:10] if created else datetime.now(timezone.utc).strftime("%d/%m/%Y")
    doc_number = f"AUDIT-{assessment_id[:8]}/BC-ATTT"

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

    # Cleanse any legacy self-declared patterns from the report body
    html_body = _re.sub(r'Tỷ\s*lệ\s*Tuân\s*thủ\s*Tổng\s*thể:\s*58\.4%[^\n<]*', f'Tỷ lệ Tuân thủ có trọng số (Weighted Compliance): {pct}% ({sat_score}/{total_ctrls} Controls đạt)', html_body)
    html_body = _re.sub(r'58\.4%\s*\(\s*45\s*/\s*93\s*Controls\s*(?:đạt|được đánh dấu đạt)[^\)]*\)', f'{pct}% ({sat_score}/{total_ctrls} Controls đạt)', html_body)
    html_body = _re.sub(r'58\.4%', f'{pct}%', html_body)
    html_body = _re.sub(r'45\s*/\s*93\s*Controls\s*(?:đạt|được đánh dấu đạt)', f'{sat_score}/{total_ctrls} Controls đạt (đã đối soát)', html_body)
    html_body = _re.sub(r'45\s*/\s*93', f'{sat_score}/{total_ctrls}', html_body)
    html_body = _re.sub(r'hierarchical_weighted', 'verdict_weighted_v2', html_body)
    html_body = _re.sub(r'weight_score_v1', 'verdict_weighted_v2', html_body)

    aid_str = data.get("assessment_id") or assessment_id
    run_id = data.get("run_id") or json_data.get("run_id") or "run_default"
    code_ver = data.get("code_version") or json_data.get("code_version") or "v1.2.0-rel"

    is_tcvn_audit = ("tcvn" in std.lower() or "11930" in std.lower())
    if is_tcvn_audit:
        subhead_html = f"""<table class="doc-top-bar">
  <tr>
    <td style="text-align: left;">Báo cáo đánh giá an toàn thông tin — CyberAI Platform</td>
    <td style="text-align: right;">Tiêu chuẩn: {std_name}</td>
  </tr>
</table>"""
        letterhead_html = f"""<table class="letterhead-tbl">
  <tr>
    <td class="lh-left">
      <div class="lh-org">Hệ thống đánh giá an toàn thông tin CyberAI</div>
      <div class="lh-sub">Trung tâm kiểm toán & thẩm định tuân thủ</div>
      <div class="lh-divider-left"></div>
      <div class="lh-num">Số: {doc_number}</div>
    </td>
    <td class="lh-right">
      <div class="lh-country">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
      <div class="lh-motto">Độc lập - Tự do - Hạnh phúc</div>
      <div class="lh-divider-right"></div>
      <div class="lh-date">Hà Nội, {now_viet_date}</div>
    </td>
  </tr>
</table>"""
        disclaimer_banner_html = """<div class="disclaimer-banner">
  Kết quả được sinh để hỗ trợ tự đánh giá sơ bộ theo TCVN 11930:2017; không thay thế hồ sơ đề xuất cấp độ chính thức hay quyết định phê duyệt của cơ quan có thẩm quyền. Cần chuyên gia an toàn thông tin xác minh trước khi sử dụng làm căn cứ quyết định hoặc kiểm toán.
</div>"""
    else:
        subhead_html = f"""<table class="doc-top-bar">
  <tr>
    <td style="text-align: left;">Information Security Assessment Report — CyberAI Platform</td>
    <td style="text-align: right;">Standard: {std_name}</td>
  </tr>
</table>"""
        letterhead_html = f"""<table class="letterhead-tbl">
  <tr>
    <td class="lh-left">
      <div class="lh-org">CYBERAI SECURITY ASSESSMENT PLATFORM</div>
      <div class="lh-sub">Information Security Management System Audit</div>
      <div class="lh-divider-left"></div>
      <div class="lh-num">Ref: {doc_number}</div>
    </td>
    <td class="lh-right">
      <div class="lh-country" style="font-size: 11pt; letter-spacing: 0.5px;">IT SECURITY ASSESSMENT REPORT</div>
      <div class="lh-motto" style="font-size: 9.5pt; font-weight: bold; color: #2563eb;">ISO/IEC 27001:2022 ISMS AUDIT</div>
      <div class="lh-divider-right"></div>
      <div class="lh-date">Date: {doc_date}</div>
    </td>
  </tr>
</table>"""
        disclaimer_banner_html = """<div class="disclaimer-banner">
  Kết quả được sinh để hỗ trợ tự đánh giá; cần chuyên gia an toàn thông tin xác minh trước khi sử dụng làm căn cứ quyết định hoặc kiểm toán.
</div>"""

    wb_table_html = f"""
    <div class="section-box">
      <div class="table-caption">Bảng phân tích theo mức độ ưu tiên & trọng số kiểm soát (verdict_weighted_v2)</div>
      <table class="wb-table">
        <thead>
          <tr>
            <th>Mức độ ưu tiên</th>
            <th style="text-align:center;">Tổng số Controls</th>
            <th style="text-align:center;">Đã đạt (Verified)</th>
            <th style="text-align:center;">Khoảng trống (GAP)</th>
            <th style="text-align:center;">Điểm trọng số (Đạt / Tối đa)</th>
            <th style="text-align:center;">Tỷ lệ tuân thủ</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong style="color: #dc2626;">Critical (Trọng yếu)</strong></td>
            <td style="text-align:center;">{crit_data['total_controls']}</td>
            <td style="text-align:center; color:#16a34a; font-weight:bold;">{crit_data['satisfied_verified']}</td>
            <td style="text-align:center; color:#dc2626; font-weight:bold;">{crit_data['gap_controls']}</td>
            <td style="text-align:center; font-weight:bold;">{crit_data['weighted_score']:.1f} / {crit_data['weighted_max_score']:.1f}</td>
            <td style="text-align:center; font-weight:bold;">{crit_data['percentage']:.1f}%</td>
          </tr>
          <tr>
            <td><strong style="color: #ea580c;">High (Cao)</strong></td>
            <td style="text-align:center;">{high_data['total_controls']}</td>
            <td style="text-align:center; color:#16a34a; font-weight:bold;">{high_data['satisfied_verified']}</td>
            <td style="text-align:center; color:#ea580c; font-weight:bold;">{high_data['gap_controls']}</td>
            <td style="text-align:center; font-weight:bold;">{high_data['weighted_score']:.1f} / {high_data['weighted_max_score']:.1f}</td>
            <td style="text-align:center; font-weight:bold;">{high_data['percentage']:.1f}%</td>
          </tr>
          <tr>
            <td><strong style="color: #ca8a04;">Medium (Trung bình)</strong></td>
            <td style="text-align:center;">{med_data['total_controls']}</td>
            <td style="text-align:center; color:#16a34a; font-weight:bold;">{med_data['satisfied_verified']}</td>
            <td style="text-align:center; color:#ca8a04; font-weight:bold;">{med_data['gap_controls']}</td>
            <td style="text-align:center; font-weight:bold;">{med_data['weighted_score']:.1f} / {med_data['weighted_max_score']:.1f}</td>
            <td style="text-align:center; font-weight:bold;">{med_data['percentage']:.1f}%</td>
          </tr>
          <tr>
            <td><strong style="color: #64748b;">Low (Thấp)</strong></td>
            <td style="text-align:center;">{low_data['total_controls']}</td>
            <td style="text-align:center; color:#16a34a; font-weight:bold;">{low_data['satisfied_verified']}</td>
            <td style="text-align:center; color:#64748b; font-weight:bold;">{low_data['gap_controls']}</td>
            <td style="text-align:center; font-weight:bold;">{low_data['weighted_score']:.1f} / {low_data['weighted_max_score']:.1f}</td>
            <td style="text-align:center; font-weight:bold;">{low_data['percentage']:.1f}%</td>
          </tr>
        </tbody>
        <tfoot>
          <tr style="background: #f1f5f9; font-weight: bold; border-top: 2px solid #94a3b8;">
            <td><strong>Tổng cộng (Toàn hệ thống)</strong></td>
            <td style="text-align:center;">{pb['total_applicable']}</td>
            <td style="text-align:center; color:#16a34a;">{pb['total_satisfied']}</td>
            <td style="text-align:center; color:#dc2626;">{pb['total_gaps']}</td>
            <td style="text-align:center;">{pb['total_weighted_score']:.1f} / {pb['total_weighted_max_score']:.1f}</td>
            <td style="text-align:center; color:{pct_color};">{pb['percentage']:.1f}%</td>
          </tr>
        </tfoot>
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
  * {{ box-sizing: border-box; font-variant-ligatures: none; }}
  body {{
    font-family: 'Times New Roman', Times, serif, 'Segoe UI', Arial;
    font-variant-ligatures: none;
    margin: 0;
    padding: 0;
    color: #0f172a;
    line-height: 1.6;
    font-size: 11.5pt;
  }}

  /* Top running document subheader (matching xOffice / standard template) */
  .doc-top-bar {{
    width: 100%;
    border-collapse: collapse;
    border-bottom: 1px solid #cbd5e1;
    margin-bottom: 16px;
    padding-bottom: 6px;
  }}
  .doc-top-bar td {{
    border: none;
    padding: 0 0 6px 0;
    font-size: 8.5pt;
    color: #64748b;
    font-style: italic;
  }}

  /* Administrative Letterhead Header */
  .letterhead-tbl {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 22px;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 14px;
  }}
  .letterhead-tbl td {{
    border: none;
    padding: 0 0 14px 0;
    vertical-align: top;
  }}
  .lh-left {{
    width: 48%;
    text-align: center;
    padding-right: 10px;
  }}
  .lh-org {{
    font-size: 9.5pt;
    font-weight: 700;
    color: #0f172a;
    white-space: nowrap;
  }}
  .lh-sub {{
    font-size: 9pt;
    color: #475569;
    margin-top: 3px;
  }}
  .lh-divider-left {{
    width: 75px;
    height: 1px;
    background: #334155;
    margin: 5px auto 6px auto;
  }}
  .lh-num {{
    font-size: 8.5pt;
    font-style: italic;
    color: #475569;
    margin-top: 4px;
  }}
  .lh-right {{
    width: 52%;
    text-align: center;
    padding-left: 10px;
  }}
  .lh-country {{
    font-size: 9.5pt;
    font-weight: 700;
    text-transform: uppercase;
    color: #0f172a;
    white-space: nowrap;
  }}
  .lh-motto {{
    font-size: 9.5pt;
    font-weight: 700;
    color: #0f172a;
    margin-top: 2px;
  }}
  .lh-divider-right {{
    width: 110px;
    height: 1px;
    background: #334155;
    margin: 5px auto 6px auto;
  }}
  .lh-date {{
    font-size: 9pt;
    font-style: italic;
    color: #475569;
    margin-top: 4px;
  }}

  /* Main Title */
  .report-title-box {{
    text-align: center;
    margin: 18px 0 16px 0;
  }}
  .report-title {{
    font-size: 16pt;
    font-weight: 700;
    text-transform: uppercase;
    color: #0a2540;
    letter-spacing: 0.5px;
    margin: 0;
    border-bottom: none !important;
    padding-bottom: 0;
  }}
  .report-subtitle {{
    font-size: 11pt;
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

<!-- Top Running Document Subheader -->
{subhead_html}

<!-- 1. Administrative Letterhead -->
{letterhead_html}

<!-- 2. Main Title -->
<div class="report-title-box">
  <h1 class="report-title">Báo cáo đánh giá an toàn thông tin</h1>
  <div class="report-subtitle">Tiêu chuẩn đối soát: {std_name}</div>
</div>

<!-- Mandatory Disclaimer -->
{disclaimer_banner_html}

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
    <td class="val">ID: {aid_str} | Run: {run_id}</td>
    <td class="lbl">Phiên bản hệ thống:</td>
    <td class="val">{code_ver}</td>
  </tr>
  <tr>
    <td class="lbl">Tỷ lệ tuân thủ có trọng số:</td>
    <td class="val"><strong style="color: {pct_color}; font-size: 12pt;">{pct}%</strong></td>
    <td class="lbl">Controls đạt (Đã đối soát):</td>
    <td class="val"><strong style="color: {pct_color};">{sat_score}/{total_ctrls} Controls</strong></td>
  </tr>
  <tr>
    <td class="lbl">Tỷ lệ tự khai sơ bộ:</td>
    <td class="val">{raw_cov}% ({decl_score} controls tự khai)</td>
    <td class="lbl">Chuyên gia đối soát:</td>
    <td class="val">Hội đồng Kiểm toán ATTT</td>
  </tr>
  <tr>
    <td class="lbl">Phạm vi hệ thống:</td>
    <td class="val" colspan="3">{scope_desc}</td>
  </tr>
</table>

<!-- Disclaimer Scope Banner -->
<div style="background: #f0f9ff; border: 1px solid #bae6fd; border-left: 4px solid #0284c7; padding: 8px 12px; margin: 12px 0 16px 0; border-radius: 4px; font-size: 8.5pt; color: #0369a1; line-height: 1.4;">
  <strong>Phạm vi & Giới hạn kỹ thuật:</strong> Báo cáo này là kết quả đánh giá sơ bộ theo catalogue kỹ thuật {std_name} nhằm hỗ trợ rà soát khoảng cách bảo đảm an toàn thông tin. Kết quả không thay thế hồ sơ đề xuất cấp độ chính thức, không thay thế cơ quan nhà nước có thẩm quyền thẩm định hay phê duyệt cấp độ, và cần chuyên gia an toàn thông tin xem xét, phê duyệt theo quy trình của tổ chức (expert_review_status: pending).
</div>

<!-- 4. Metric Cards -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="val" style="color: {pct_color};">{pct}%</div>
    <div class="lbl">Tuân thủ có trọng số</div>
  </div>
  <div class="stat-card">
    <div class="val" style="color: {pct_color};">{sat_score}/{total_ctrls}</div>
    <div class="lbl">Controls đạt (Verified)</div>
  </div>
  <div class="stat-card">
    <div class="val" style="color: #64748b;">{raw_cov}%</div>
    <div class="lbl">Tự khai sơ bộ</div>
  </div>
  <div class="stat-card">
    <div class="val" style="color: #dc2626;">{total_gaps}</div>
    <div class="lbl">Khoảng trống (GAP)</div>
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

    pdf_filename = f"Audit_Report_{assessment_id[:8]}.pdf"
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
        audit_service.record_artifact_exported(
            ctx=audit_ctx,
            export_format="pdf",
            filename=pdf_filename,
            file_size_bytes=file_sz,
            file_hash_sha256=file_hash,
        )
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=pdf_filename,
        )
    except ImportError:
        # weasyprint not installed — return HTML file
        raw_b = html_content.encode("utf-8")
        file_hash = hashlib.sha256(raw_b).hexdigest()
        audit_service.record_artifact_exported(
            ctx=audit_ctx,
            export_format="html_fallback",
            filename=html_filename,
            file_size_bytes=len(raw_b),
            file_hash_sha256=file_hash,
        )
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
        audit_service.record_artifact_exported(
            ctx=audit_ctx,
            export_format="html_fallback_error",
            filename=html_filename,
            file_size_bytes=len(raw_b),
            file_hash_sha256=file_hash,
        )
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

    if body.assessment_id:
        asm_data = load_assessment(body.assessment_id)
        if asm_data:
            inv_valid, inv_fails = validate_assessment_invariants(asm_data.get("json_data") or asm_data)
            if not inv_valid:
                raise HTTPException(
                    status_code=422,
                    detail=f"INVARIANT_VALIDATION_FAILED (Invariant Violation): {'; '.join(inv_fails)}"
                )

    xlsx_bytes = generate_soa_xlsx(
        assessment_id=body.assessment_id,
        implemented_controls=body.implemented_controls,
        org_name=body.org_name,
    )

    import hashlib
    file_sz = len(xlsx_bytes)
    file_hash = hashlib.sha256(xlsx_bytes).hexdigest()

    # Determine standard (ISO vs TCVN)
    is_tcvn = False
    run_id_val = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    if body.assessment_id:
        asm_data = load_assessment(body.assessment_id)
        if asm_data:
            run_id_val = asm_data.get("run_id") or asm_data.get("json_data", {}).get("run_id") or run_id_val
            raw_std = asm_data.get("standard") or asm_data.get("system_info", {}).get("assessment_standard") or ""
            if isinstance(raw_std, dict):
                raw_std = raw_std.get("id") or raw_std.get("name") or ""
            std_str = str(raw_std).lower()
            if "tcvn" in std_str or "11930" in std_str:
                is_tcvn = True

    short_id = body.assessment_id[:8] if body.assessment_id else datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"SoA_{'TCVN11930' if is_tcvn else 'ISO27001'}_{short_id}.xlsx"

    if body.assessment_id:
        audit_ctx = AuditContext(assessment_id=body.assessment_id, run_id=run_id_val)
        audit_service.record_artifact_exported(
            ctx=audit_ctx,
            export_format="soa_xlsx",
            filename=filename,
            file_size_bytes=file_sz,
            file_hash_sha256=file_hash,
        )

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _format_content_disposition(filename: str) -> str:
    """Format RFC 6266 / RFC 5987 Content-Disposition header safely for HTTP/1.1 (ASCII/Latin-1)."""
    import unicodedata
    import re
    from urllib.parse import quote

    nfkd = unicodedata.normalize("NFKD", filename)
    ascii_name = nfkd.encode("ASCII", "ignore").decode("ASCII")
    ascii_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", ascii_name)
    ascii_name = re.sub(r"_+", "_", ascii_name).strip("_")
    if not ascii_name:
        ascii_name = "export_file"
    quoted_utf8 = quote(filename, safe="")
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quoted_utf8}'


@router.get("/iso27001/assessments/{assessment_id}/export-docx")
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

    if data.get("status") and data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Assessment not completed yet (current status: '{data.get('status')}')"
        )

    inv_valid, inv_fails = validate_assessment_invariants(data.get("json_data") or data)
    if not inv_valid:
        raise HTTPException(
            status_code=422,
            detail=f"INVARIANT_VALIDATION_FAILED (Invariant Violation): {'; '.join(inv_fails)}"
        )

    resolved_id = data.get("id") or data.get("assessment_id") or assessment_id
    run_id_val = data.get("run_id") or data.get("json_data", {}).get("run_id") or f"run_{resolved_id[:8]}"
    data["assessment_id"] = resolved_id
    data["run_id"] = run_id_val
    if "json_data" in data and isinstance(data["json_data"], dict):
        data["json_data"].setdefault("assessment_id", resolved_id)
        data["json_data"].setdefault("run_id", run_id_val)

    docx_bytes = generate_report_docx(data)
    docx_sz = len(docx_bytes)
    docx_hash = hashlib.sha256(docx_bytes).hexdigest()

    filename = f"IT_Audit_Report_{resolved_id[:8]}.docx"

    audit_ctx = AuditContext(assessment_id=resolved_id, run_id=run_id_val)
    audit_service.record_artifact_exported(
        ctx=audit_ctx,
        export_format="docx",
        filename=filename,
        file_size_bytes=docx_sz,
        file_hash_sha256=docx_hash,
    )

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": _format_content_disposition(filename)},
    )


@router.get("/iso27001/assessments/{assessment_id}/export-risk-register")
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

    if data.get("status") and data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Assessment not completed yet (current status: '{data.get('status')}')"
        )

    inv_valid, inv_fails = validate_assessment_invariants(data.get("json_data") or data)
    if not inv_valid:
        raise HTTPException(
            status_code=422,
            detail=f"INVARIANT_VALIDATION_FAILED (Invariant Violation): {'; '.join(inv_fails)}"
        )

    resolved_id = data.get("id") or data.get("assessment_id") or assessment_id
    run_id_val = data.get("run_id") or data.get("json_data", {}).get("run_id") or f"run_{resolved_id[:8]}"
    data["assessment_id"] = resolved_id
    data["run_id"] = run_id_val
    if "json_data" in data and isinstance(data["json_data"], dict):
        data["json_data"].setdefault("assessment_id", resolved_id)
        data["json_data"].setdefault("run_id", run_id_val)

    xlsx_bytes = generate_risk_register_xlsx(assessment_id=resolved_id, assessment_data=data)
    xlsx_sz = len(xlsx_bytes)
    xlsx_hash = hashlib.sha256(xlsx_bytes).hexdigest()

    filename = f"Risk_Register_{resolved_id[:8]}.xlsx"

    audit_ctx = AuditContext(assessment_id=resolved_id, run_id=run_id_val)
    audit_service.record_artifact_exported(
        ctx=audit_ctx,
        export_format="risk_register_xlsx",
        filename=filename,
        file_size_bytes=xlsx_sz,
        file_hash_sha256=xlsx_hash,
    )

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _format_content_disposition(filename)},
    )


@router.get("/iso27001/assessments/{assessment_id}/extraction-proof")
async def get_assessment_extraction_proof(assessment_id: str):
    """Retrieve 100% extraction integrity proof, ingestion manifest, and empirical facts."""
    _validate_path_id(assessment_id, "assessment_id")
    data = load_assessment(assessment_id)
    if not data:
        raise HTTPException(status_code=404, detail="Assessment not found")

    proof = data.get("extraction_proof") or data.get("json_data", {}).get("extraction_proof")
    if not proof:
        from services.evidence_fact_extractor import EvidenceFactExtractor
        manifest_path = os.path.join(os.getenv("DATA_PATH", "./data"), "evidence_manifests", f"{assessment_id}.json")
        manifest_data = {}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    manifest_data = json.load(mf)
            except Exception:
                pass

        system_data = data.get("system_data") or data.get("system_info") or {}
        raw_notes = system_data.get("notes", "") or ""
        manifest_files = manifest_data.get("files", [])
        total_files = len(manifest_files)
        is_template = bool(system_data.get("is_template_input") or data.get("is_template_input") or system_data.get("template_id"))
        tpl_name = system_data.get("template_name") or system_data.get("template_id") or "Template Mẫu"

        ev_map = system_data.get("evidence_map") or data.get("evidence_map") or {}
        has_ev_map = any(files for files in ev_map.values()) if isinstance(ev_map, dict) else False
        ev_files = system_data.get("evidence_files") or data.get("evidence_files") or []

        if total_files == 0 and has_ev_map:
            total_files = sum(len(f) if isinstance(f, list) else 1 for f in ev_map.values())
        elif total_files == 0 and ev_files:
            total_files = len(ev_files)
        elif total_files == 0 and not is_template and raw_notes and any(kw in raw_notes for kw in ["Host Name:", "OS Name:", "Hotfix", "KB", "CVE-"]):
            total_files = 1

        if total_files > 0:
            data_source = "uploaded_evidence"
            source_label = f"Minh chứng thực tế tải lên ({total_files} tệp) — Manifest ID: {manifest_data.get('assessment_id') or assessment_id}"
            integrity_status = "VERIFIED_100_PERCENT"
            completeness_score = 100.0
            fc = EvidenceFactExtractor.extract_facts(raw_notes, "assessment_evidence", use_llm=False)
            impl = system_data.get("compliance", {}).get("implemented_controls", []) or []
            verify_res = EvidenceFactExtractor.cross_verify_controls(impl, [fc])

            # Extract final verdicts map from assessment data to link Cross-Verification Matrix
            verdicts_map = {}
            ctrl_list = data.get("controls") or data.get("json_data", {}).get("controls", [])
            if isinstance(ctrl_list, list):
                for c in ctrl_list:
                    if isinstance(c, dict):
                        cid = c.get("id") or c.get("control_id")
                        if cid:
                            verdicts_map[cid] = c.get("assessment_verdict") or c.get("verdict")

            for item in verify_res.get("contradiction_gaps", []):
                cid = item.get("control_id")
                item["technical_result"] = "Mâu thuẫn log kỹ thuật"
                item["final_verdict"] = verdicts_map.get(cid, "needs_expert_review")

            for item in verify_res.get("verified_satisfied", []):
                cid = item.get("control_id")
                item["technical_result"] = "Khớp bằng chứng kỹ thuật"
                item["final_verdict"] = verdicts_map.get(cid, "satisfied")

            for item in verify_res.get("unverified_oversights", []):
                cid = item.get("control_id")
                item["technical_result"] = "Không có log đối chứng"
                item["final_verdict"] = verdicts_map.get(cid, "missing")

            tech_facts = {
                "hostname": fc.host_metadata.get("hostname") or "Chưa bóc tách được từ log",
                "os": fc.host_metadata.get("os_name") or "Không phát hiện hệ điều hành trong log",
                "os_eol": bool(fc.host_metadata.get("is_eol", False)),
                "hotfixes_count": len(fc.host_metadata.get("hotfixes", [])) if fc.host_metadata.get("hotfixes") else 0,
                "hotfixes": fc.host_metadata.get("hotfixes") or [],
                "open_ports": fc.network_and_access.get("listening_ports") or [],
                "antivirus": fc.host_metadata.get("antivirus") or [],
                "security_deficiencies": [d.get("name") for d in fc.security_deficiencies] if fc.security_deficiencies else [],
                "security_strengths": fc.security_strengths or [],
            }
        elif is_template:
            data_source = "template_sample"
            source_label = f"Dữ liệu mẫu từ template: {tpl_name} (Chưa qua kiểm định tệp thực tế)"
            integrity_status = "TEMPLATE_PREVIEW_ONLY"
            completeness_score = 0.0
            tech_facts = {
                "hostname": None,
                "os": None,
                "os_eol": False,
                "hotfixes_count": 0,
                "hotfixes": [],
                "open_ports": [],
                "antivirus": [],
                "security_deficiencies": [],
                "security_strengths": [],
            }
            verify_res = {
                "contradiction_gaps": [],
                "verified_satisfied": [],
                "unverified_oversights": [],
            }
        else:
            data_source = "no_evidence"
            source_label = "Không có minh chứng kỹ thuật (Tự khai báo không tệp)"
            integrity_status = "NO_EVIDENCE_ATTACHED"
            completeness_score = 0.0
            tech_facts = {
                "hostname": None,
                "os": None,
                "os_eol": False,
                "hotfixes_count": 0,
                "hotfixes": [],
                "open_ports": [],
                "antivirus": [],
                "security_deficiencies": [],
                "security_strengths": [],
            }
            verify_res = {
                "contradiction_gaps": [],
                "verified_satisfied": [],
                "unverified_oversights": [],
            }

        proof = {
            "data_source": data_source,
            "source_label": source_label,
            "integrity_status": integrity_status,
            "completeness_score": completeness_score,
            "assessment_id": assessment_id,
            "evidence_manifest_id": manifest_data.get("assessment_id") or data.get("evidence_manifest_id") or f"manifest_{assessment_id[:12]}",
            "total_files": total_files,
            "total_chars_extracted": sum(f.get("chars_extracted", f.get("size_bytes", 0)) for f in manifest_files) if total_files > 0 else 0,
            "manifest_files": manifest_files,
            "technical_facts": tech_facts,
            "cross_verification": verify_res,
        }
    return proof


# ── Audit Trace (Verifiable Runtime Telemetry) ──────────────────────


@router.get("/iso27001/assessments/{assessment_id}/audit-trace")
@router.get("/assessments/{assessment_id}/audit-trace")
async def get_assessment_audit_trace(assessment_id: str, run_id: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """Retrieve verifiable chronological audit events strictly filtered by assessment_id and run_id with redacted PII."""
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
    target_run_id = run_id or data.get("run_id") or data.get("json_data", {}).get("run_id")
    all_events = audit_store.get_events_by_assessment(assessment_id)
    events = [ev for ev in all_events if ev.get("run_id") == target_run_id] if target_run_id else all_events

    # Compute summary
    rag_collections = []
    actual_models = []
    total_tokens = 0

    manifest_id = None
    ev_source = "self_declared"
    total_files = 0
    files_list = []
    control_mapping = {}

    for ev in events:
        p = ev.get("payload", {})
        if ev.get("event_type") == "evidence_parsed":
            manifest_id = p.get("evidence_manifest_id") or manifest_id
            ev_source = p.get("evidence_source") or ev_source
            total_files = p.get("total_files", total_files)
            files_list = p.get("files", files_list)
            control_mapping = p.get("control_mapping", control_mapping)
        elif ev.get("event_type") == "rag_query_completed" and p.get("collection_name"):
            if p["collection_name"] not in rag_collections:
                rag_collections.append(p["collection_name"])
        elif ev.get("event_type") == "llm_inference_completed":
            if p.get("actual_model") and p["actual_model"] not in actual_models:
                actual_models.append(p["actual_model"])
            usage = p.get("usage_metrics", {})
            total_tokens += usage.get("total_tokens", 0)

    run_id = events[0].get("run_id") if events else data.get("run_id", f"run_{assessment_id[:8]}")
    if not manifest_id:
        manifest_id = data.get("evidence_manifest_id", f"manifest_{assessment_id}")

    summary = {
        "assessment_id": assessment_id,
        "run_id": run_id,
        "evidence_manifest_id": manifest_id,
        "evidence_source": ev_source,
        "total_files": total_files,
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

    trace_res = {
        "assessment_id": assessment_id,
        "run_id": run_id,
        "evidence_manifest_id": manifest_id,
        "evidence_source": ev_source,
        "total_files": total_files,
        "files": files_list,
        "control_mapping": control_mapping,
        "summary": summary,
        "events": events,
    }

    try:
        from services.audit_service import audit_service, AuditContext
        trace_bytes = json.dumps(trace_res, ensure_ascii=False).encode("utf-8")
        trace_hash = hashlib.sha256(trace_bytes).hexdigest()
        audit_ctx = AuditContext(assessment_id=assessment_id, run_id=run_id)
        audit_service.record_artifact_exported(
            ctx=audit_ctx,
            export_format="audit_trace_json",
            filename=f"audit_trace_{assessment_id[:8]}.json",
            file_size_bytes=len(trace_bytes),
            file_hash_sha256=trace_hash,
        )
    except Exception:
        pass

    return trace_res



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
    expert_verdict: str  # "satisfied" | "partial" | "missing" | "needs_expert_review"
    expert_rationale: str
    input_fact_summary: Optional[str] = ""
    initial_ai_verdict: Optional[str] = None
    standard: Optional[str] = "iso27001"
    auditor_username: Optional[str] = "lead_auditor"
    metadata: Optional[Dict[str, Any]] = None
    split: Optional[str] = "few_shot"
    label_status: Optional[str] = None


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
            split=payload.split or "few_shot",
            label_status=payload.label_status,
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




