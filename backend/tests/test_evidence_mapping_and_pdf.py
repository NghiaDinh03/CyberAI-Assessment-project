"""Integration and regression tests for evidence mapping and PDF exporter (Goals 1 & 2).

Test 1: Upload 3 evidence files for A.5.1, A.5.3, A.5.5.
        Verify backend receives mapping, attaches evidence correctly,
        and computes test pack:
        A.5.1=satisfied (10.0), A.5.3=partial (2.5), A.5.5=missing (0.0).
        Total = 12.5 / 18.0 = 69.4%.

Test 2: Regression test scanning PDF text in zero-verified assessment.
        Assert PDF does NOT contain 58.4%, 45/93, hierarchical_weighted, weight_score_v1.
        Assert PDF contains 0.0%, 0/93, verdict_weighted_v2.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import sys
import uuid
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long!")
os.environ.setdefault("DEBUG", "true")

BACKEND = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.routes.iso27001 import router, process_assessment_bg, save_assessment, load_assessment, export_pdf
from schemas.assessment_schema import UnifiedAssessmentResult, ControlItem, ControlCoverage, WeightedCompliance
from services.controls_catalog import calc_weighted_compliance


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    # Update route dirs to temp path
    from api.routes import iso27001
    iso27001.DATA_DIR = str(tmp_path)
    iso27001.ASSESSMENTS_DIR = str(tmp_path / "assessments")
    iso27001.EVIDENCE_DIR = str(tmp_path / "evidence")
    iso27001.EXPORTS_DIR = str(tmp_path / "exports")
    os.makedirs(iso27001.ASSESSMENTS_DIR, exist_ok=True)
    os.makedirs(iso27001.EVIDENCE_DIR, exist_ok=True)
    os.makedirs(iso27001.EXPORTS_DIR, exist_ok=True)

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_evidence_upload_mapping_and_test_pack_integration(client, tmp_path):
    """Test 1:
    - Upload 4 files mapped to A.5.1, A.5.3, A.5.5, A.5.6.
    - Verify backend saves files in appropriate control dirs and returns filenames.
    - Submit assessment with evidence_map and control_verdicts.
    - Verify backend reads evidence_map, sets evidence_status='direct_attachment',
      and calculates test pack score:
      A.5.1 sat (10.0), A.5.3 part (2.5), A.5.5 miss (0.0), A.5.6 NA (excluded) -> 12.5 / 18.0 = 69.4%.
    """
    # 1. Upload 3 files
    f1_content = b"Chinh sach an toan thong tin toan dien. Verdict: satisfied."
    f2_content = b"Quy che phan tach nhiem vu dang hoan thien. Verdict: partial."
    f3_content = b"Chua lien lac co quan chuc nang. Verdict: missing."

    resp1 = client.post("/api/iso27001/evidence/A.5.1", files={"file": ("a51_chinh_sach_attt.txt", f1_content, "text/plain")})
    assert resp1.status_code == 200, resp1.text
    fn1 = resp1.json()["filename"]

    resp2 = client.post("/api/iso27001/evidence/A.5.3", files={"file": ("a53_phan_tach_nhiem_vu.txt", f2_content, "text/plain")})
    assert resp2.status_code == 200, resp2.text
    fn2 = resp2.json()["filename"]

    resp3 = client.post("/api/iso27001/evidence/A.5.5", files={"file": ("a55_co_quan_chuc_nang.txt", f3_content, "text/plain")})
    assert resp3.status_code == 200, resp3.text
    fn3 = resp3.json()["filename"]

    # Verify physical file existence in control dirs
    evidence_dir = tmp_path / "evidence"
    assert (evidence_dir / "A_5_1" / fn1).exists()
    assert (evidence_dir / "A_5_3" / fn2).exists()
    assert (evidence_dir / "A_5_5" / fn3).exists()

    # 2. Submit assessment with evidence_map
    payload = {
        "assessment_standard": "iso27001",
        "org_name": "Tổ chức Đánh giá Tích hợp",
        "implemented_controls": ["A.5.1", "A.5.3"],
        "evidence_map": {
            "A.5.1": [fn1],
            "A.5.3": [fn2],
            "A.5.5": [fn3],
        },
        "control_verdicts": [
            {"control_id": "A.5.1", "evidence_verdict": "satisfied"},
            {"control_id": "A.5.3", "evidence_verdict": "partial"},
            {"control_id": "A.5.5", "evidence_verdict": "missing"},
        ]
    }

    from unittest.mock import patch
    with patch("services.chat_service.CloudLLMService._call_ollama", return_value={"content": "[]", "model": "mock", "provider": "ollama"}), \
         patch("services.cloud_llm_service.CloudLLMService._call_ollama", return_value={"content": "[]", "model": "mock", "provider": "ollama"}), \
         patch("repositories.vector_store.VectorStore.search", return_value=[]):
        assess_resp = client.post("/api/iso27001/assess", json=payload)

    assert assess_resp.status_code == 200, assess_resp.text
    aid = assess_resp.json()["id"]

    # 4. Verify assessment results
    record = load_assessment(aid)
    assert record is not None
    assert record["status"] == "completed"

    json_data = record["json_data"]
    controls = json_data["controls"]
    c_map = {c["control_id"]: c for c in controls}

    # Verify all 4 controls have direct_attachment and their respective files
    assert c_map["A.5.1"]["evidence_status"] == "direct_attachment"
    assert fn1 in c_map["A.5.1"]["evidence_file_ids"]
    assert c_map["A.5.1"]["assessment_verdict"] == "satisfied"

    assert c_map["A.5.3"]["evidence_status"] == "direct_attachment"
    assert fn2 in c_map["A.5.3"]["evidence_file_ids"]
    assert c_map["A.5.3"]["assessment_verdict"] == "partial"

    assert c_map["A.5.5"]["evidence_status"] == "direct_attachment"
    assert fn3 in c_map["A.5.5"]["evidence_file_ids"]
    # Verify test pack calculation strictly:
    test_pack_controls = [c_map["A.5.1"], c_map["A.5.3"], c_map["A.5.5"]]
    scoring = calc_weighted_compliance(test_pack_controls)

    # A.5.1 (Critical = 10.0 * 1.0 = 10.0)
    # A.5.3 (High = 5.0 * 0.5 = 2.5)
    # A.5.5 (Medium = 3.0 * 0.0 = 0.0)
    # Total = 12.5 / 18.0 = 69.444...% -> 69.4%
    assert scoring["weighted_score"] == 12.5
    assert scoring["weighted_max_score"] == 18.0
    assert scoring["percentage"] == 69.4


def test_pdf_exporter_regression_zero_verified(client, tmp_path):
    """Test 2:
    - Build zero-verified assessment: 45 self-declared, 0 satisfied, 0.0% weighted compliance.
    - Include simulated markdown report with legacy patterns:
      '58.4%', '45/93 Controls đạt', 'hierarchical_weighted', 'weight_score_v1'.
    - Generate PDF via export_pdf.
    - Extract text with pypdf and assert:
      * NO '58.4%'
      * NO '45/93'
      * NO 'hierarchical_weighted'
      * NO 'weight_score_v1'
      * HAS '0.0%'
      * HAS '0/93'
      * HAS 'verdict_weighted_v2'
    """
    import pypdf

    aid = f"test-zero-verified-{uuid.uuid4().hex[:8]}"

    # 45 self-declared controls, 0 verified satisfied
    from services.controls_catalog import get_flat_controls
    flat_iso = get_flat_controls("iso27001")
    controls = []
    for i, c in enumerate(flat_iso):
        cid = c["id"]
        is_decl = (i < 45)
        controls.append({
            "control_id": cid,
            "label": c.get("label", f"Control {cid}"),
            "weight": c.get("weight", "medium"),
            "user_declaration": "implemented" if is_decl else "not_implemented",
            "assessment_verdict": "not_evidenced" if is_decl else "missing",
            "score": 0,
            "weighted_score_contribution": 0.0,
            "gap": "Chưa có bằng chứng" if is_decl else "Chưa triển khai",
            "recommendation": "Bổ sung minh chứng",
            "severity": "high" if is_decl else "critical",
            "likelihood": 3 if is_decl else 4,
            "impact": 3 if is_decl else 4,
            "risk_score": 9 if is_decl else 16,
        })

    legacy_markdown_report = (
        "# BÁO CÁO ĐÁNH GIÁ AN TOÀN THÔNG TIN\n\n"
        "## 1. ĐÁNH GIÁ TỔNG QUAN\n"
        "- Mức tuân thủ: 58.4% (45/93 Controls được đánh dấu đạt)\n"
        "- Thuật toán chấm điểm: hierarchical_weighted và weight_score_v1\n\n"
        "## 5. EXECUTIVE SUMMARY\n"
        "- **Tỷ lệ Tuân thủ Tổng thể:** 58.4% (45/93 Controls đạt).\n"
    )

    assessment_data = {
        "id": aid,
        "assessment_id": aid,
        "run_id": f"run_{aid[:8]}",
        "code_version": "v1.2.0-rel",
        "status": "completed",
        "created_at": "2026-09-21T00:00:00Z",
        "org_name": "Doanh nghiệp Zero-Verified",
        "compliance_percent": 0.0,
        "system_info": {
            "org_name": "Doanh nghiệp Zero-Verified",
            "assessment_standard": "iso27001",
        },
        "result": {
            "report": legacy_markdown_report,
            "percentage": 0.0,
        },
        "json_data": {
            "assessment_id": aid,
            "run_id": f"run_{aid[:8]}",
            "code_version": "v1.2.0-rel",
            "status": "completed",
            "standard": "iso27001",
            "organization": {
                "name": "Doanh nghiệp Zero-Verified",
                "industry": "Tài chính",
            },
            "weighted_compliance": {
                "weighted_score": 0.0,
                "weighted_max_score": 495.0,
                "percentage": 0.0,
                "algorithm": "verdict_weighted_v2",
                "weight_scheme": "critical_10_high_5_medium_3_low_1",
            },
            "control_coverage": {
                "self_declared_implemented": 45,
                "evidence_supported_implemented": 0,
                "not_evidenced_or_missing": 93,
                "total_controls": 93,
                "raw_percentage": 48.4,
            },
            "controls": controls,
        },
        "weighted_compliance": {
            "weighted_score": 0.0,
            "weighted_max_score": 495.0,
            "percentage": 0.0,
        },
        "control_coverage": {
            "self_declared_implemented": 45,
            "evidence_supported_implemented": 0,
            "not_evidenced_or_missing": 93,
            "total_controls": 93,
            "raw_percentage": 48.4,
        }
    }

    save_assessment(aid, assessment_data)

    # Call PDF export endpoint
    export_resp = client.post(f"/api/iso27001/assessments/{aid}/export-pdf")
    assert export_resp.status_code == 200, export_resp.text
    assert export_resp.headers["content-type"] == "application/pdf"
    pdf_bytes = export_resp.content
    assert len(pdf_bytes) > 1000

    # Parse PDF text
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    all_text = ""
    for page in reader.pages:
        all_text += page.extract_text() or ""

    # Assertions on sanitized PDF text
    assert "58.4%" not in all_text, f"Found legacy '58.4%' in PDF text: {all_text[:500]}"
    assert "45/93" not in all_text, f"Found legacy '45/93' in PDF text: {all_text[:500]}"
    assert "hierarchical_weighted" not in all_text, f"Found legacy 'hierarchical_weighted' in PDF text"
    assert "weight_score_v1" not in all_text, f"Found legacy 'weight_score_v1' in PDF text"

    # Assert validated UnifiedAssessmentResult invariants are present
    assert "0.0%" in all_text, "Expected '0.0%' in PDF text"
    assert "0/93" in all_text, "Expected '0/93' in PDF text"
    assert "verdict_weighted_v2" in all_text, "Expected 'verdict_weighted_v2' in PDF text"


def test_e2e_batch_upload_manifest_and_verdict_pipeline(client, tmp_path):
    """Test 3 (P0 Synchronous Flow):
    upload -> map control -> Evidence Manifest -> start assessment -> backend receives evidence -> verdict output.
    
    Requirements:
    - A.5.1_satisfied_policy.txt maps to A.5.1
    - A.5.3_partial_segregation_of_duties.txt maps to A.5.3
    - A.5.5_missing_authority_contact.txt maps to A.5.5
    - Test FAILS if evidence count > 0 but assessment result has all evidence_status=no_evidence
    - Audit Trace contains evidence_manifest_id, total_files=3, SHA-256 hashes, control IDs mapped
    - Score: A.5.1=satisfied (10), A.5.3=partial (2.5), A.5.5=missing (0)
             12.5 / 18.0 = 69.4%.
    """
    # 1. Batch upload 3 test pack files
    f1 = ("files", ("A.5.1_satisfied_policy.txt", b"Chinh sach an toan thong tin phe duyet. Verdict: satisfied.", "text/plain"))
    f2 = ("files", ("A.5.3_partial_segregation_of_duties.txt", b"Phan tach nhiem vu ap dung 50%. Verdict: partial.", "text/plain"))
    f3 = ("files", ("A.5.5_missing_authority_contact.txt", b"Chua thiet lap kenh lien lac co quan chuc nang. Verdict: missing.", "text/plain"))

    batch_resp = client.post("/api/iso27001/evidence/batch-ingest", files=[f1, f2, f3])
    assert batch_resp.status_code == 200, batch_resp.text
    batch_data = batch_resp.json()

    assert batch_data["status"] == "success"
    manifest_id = batch_data.get("manifest_id") or batch_data.get("evidence_manifest_id")
    assert manifest_id is not None
    assert manifest_id.startswith("manifest_")

    mapped = batch_data.get("mapped_controls", {})
    assert "A.5.1" in mapped, f"A.5.1 not in mapped controls: {mapped.keys()}"
    assert "A.5.3" in mapped, f"A.5.3 not in mapped controls: {mapped.keys()}"
    assert "A.5.5" in mapped, f"A.5.5 not in mapped controls: {mapped.keys()}"

    # Verify SHA-256 is present for all 3 files
    files_list = batch_data.get("files", [])
    assert len(files_list) == 3
    for f in files_list:
        assert len(f.get("sha256", "")) == 64, f"File {f.get('filename')} missing valid SHA-256"

    # Build evidence map for assessment submission
    ev_map = {
        cid: [item["filename"] for item in flist]
        for cid, flist in mapped.items()
    }

    # 2. Start Assessment with Evidence Manifest and evidence_map
    assess_payload = {
        "assessment_standard": "iso27001",
        "org_name": "Doanh nghiệp Kiểm thử Đồng bộ",
        "implemented_controls": ["A.5.1", "A.5.3"],
        "evidence_manifest_id": manifest_id,
        "evidence_files": files_list,
        "evidence_map": ev_map,
        "control_verdicts": [
            {"control_id": "A.5.1", "evidence_verdict": "satisfied"},
            {"control_id": "A.5.3", "evidence_verdict": "partial"},
            {"control_id": "A.5.5", "evidence_verdict": "missing"},
        ]
    }

    from unittest.mock import patch
    with patch("services.chat_service.CloudLLMService._call_ollama", return_value={"content": "[]", "model": "mock", "provider": "ollama"}), \
         patch("services.cloud_llm_service.CloudLLMService._call_ollama", return_value={"content": "[]", "model": "mock", "provider": "ollama"}), \
         patch("repositories.vector_store.VectorStore.search", return_value=[]):
        assess_resp = client.post("/api/iso27001/assess", json=assess_payload)

    assert assess_resp.status_code == 200, assess_resp.text
    assess_data = assess_resp.json()
    assert assess_data["status"] == "accepted"
    aid = assess_data["id"]
    assert assess_data["evidence_manifest_id"] == manifest_id
    assert assess_data["mapped_controls_count"] == 3
    assert len(assess_data.get("evidence_map", {})) == 3

    # 3. Load completed assessment and check verdicts
    record = load_assessment(aid)
    assert record is not None
    assert record["status"] == "completed"

    json_data = record["json_data"]
    controls = json_data["controls"]
    c_map = {c["control_id"]: c for c in controls}

    # P0 Regression Check: MUST FAIL if evidence count > 0 but all evidence_status=no_evidence
    target_controls = [c_map["A.5.1"], c_map["A.5.3"], c_map["A.5.5"]]
    all_no_evidence = all(c.get("evidence_status") == "no_evidence" for c in target_controls)
    assert not all_no_evidence, "P0 REGRESSION FAILURE: All controls marked as 'no_evidence' despite 3 uploaded files!"

    for cid in ("A.5.1", "A.5.3", "A.5.5"):
        assert c_map[cid]["evidence_status"] == "direct_attachment", f"{cid} evidence_status is not direct_attachment"
        assert len(c_map[cid]["evidence_file_ids"]) > 0

    assert c_map["A.5.1"]["assessment_verdict"] == "satisfied"
    assert c_map["A.5.3"]["assessment_verdict"] == "partial"
    assert c_map["A.5.5"]["assessment_verdict"] == "missing"

    target_controls = [c_map["A.5.1"], c_map["A.5.3"], c_map["A.5.5"]]
    scoring = calc_weighted_compliance(target_controls)
    assert scoring["weighted_score"] == 12.5, f"Expected 12.5, got {scoring['weighted_score']}"
    assert scoring["weighted_max_score"] == 18.0, f"Expected 18.0, got {scoring['weighted_max_score']}"
    assert scoring["percentage"] == 69.4, f"Expected 69.4%, got {scoring['percentage']}%"

    # 4. Check Audit Trace
    trace_resp = client.get(f"/api/iso27001/assessments/{aid}/audit-trace")
    assert trace_resp.status_code == 200, trace_resp.text
    trace_data = trace_resp.json()
    events = trace_data.get("events", [])
    ev_parsed_event = next((e for e in events if e.get("event_type") == "evidence_parsed"), None)
    assert ev_parsed_event is not None, "Audit trace missing 'evidence_parsed' event"

    payload = ev_parsed_event.get("payload", {})
    assert payload.get("evidence_manifest_id") == manifest_id
    assert payload.get("total_files") == 3
    file_hashes = payload.get("file_hashes", {})
    assert len(file_hashes) == 3
    for fname, fhash in file_hashes.items():
        assert len(fhash) == 64

    ctrl_mapping = payload.get("control_mapping", {})
    for cid in ("A.5.1", "A.5.3", "A.5.5"):
        assert cid in ctrl_mapping

    # 5. Check Extraction Proof endpoint
    proof_resp = client.get(f"/api/iso27001/assessments/{aid}/extraction-proof")
    assert proof_resp.status_code == 200, proof_resp.text
    proof = proof_resp.json()
    assert proof["data_source"] == "uploaded_evidence"
    assert proof["total_files"] == 3
    assert len(proof["manifest_files"]) == 3
    assert proof["integrity_status"] == "VERIFIED_100_PERCENT"


def test_template_vs_uploaded_evidence_separation(client, tmp_path):
    """Test 4: Verify template preview data is strictly separated from uploaded evidence.
    When a template is selected without user uploaded files, data_source is 'template_sample'
    and NO fake EVN server telemetry is presented.
    """
    aid = f"test-tpl-{uuid.uuid4().hex[:8]}"
    assessment_data = {
        "id": aid,
        "assessment_id": aid,
        "status": "completed",
        "created_at": "2026-09-21T00:00:00Z",
        "template_id": "tpl_financial_iso27001",
        "template_name": "Mẫu Ngân hàng & Tài chính",
        "is_template_input": False,
        "system_data": {
            "template_id": "tpl_financial_iso27001",
            "template_name": "Mẫu Ngân hàng & Tài chính",
            "is_template_input": False,
            "evidence_map": {},
            "compliance": {"implemented_controls": ["A.5.1"]}
        },
        "json_data": {
            "assessment_id": aid,
            "status": "completed",
            "standard": "iso27001",
            "controls": []
        }
    }
    save_assessment(aid, assessment_data)

    proof_resp = client.get(f"/api/iso27001/assessments/{aid}/extraction-proof")
    assert proof_resp.status_code == 200, proof_resp.text
    proof = proof_resp.json()

    assert proof["data_source"] == "template_sample"
    assert "Mẫu Ngân hàng & Tài chính" in proof["source_label"]
    assert proof["total_files"] == 0
    assert proof["manifest_files"] == []
    assert proof["completeness_score"] == 0.0

    facts = proof["technical_facts"]
    assert facts["hostname"] is None
    assert facts["os"] is None
    assert facts["hotfixes_count"] == 0
    assert len(facts["security_deficiencies"]) == 0
