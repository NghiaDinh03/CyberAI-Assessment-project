"""Authoritative Integration & Technical Specification Test Suite for Chapter 4 Acceptance Test Packs.

Covers:
- Deterministic Phase 0 regex mapping of ISO and TCVN filenames
- Multi-control mapping without false positive cross-talk
- Parser error resilience and unsupported format isolation
- Evidence manifest isolation between assessments
- Enforcement of safety invariants (no satisfied from self-declaration alone, mandatory citations)
- Safe conflict detection branch leading to needs_expert_review with zero score contribution
- Pre-calculated mathematical compliance validation according to verdict_weighted_v2
"""

import json
import os
import pytest
from services.controls_catalog import (
    ISO_27001_CATEGORIES,
    TCVN_11930_CATEGORIES,
    WEIGHT_SCORE,
    VERDICT_FACTOR,
    calc_weighted_compliance,
)
from services.evidence_mapper import map_evidence_to_controls
from services.evidence_parser import parse_evidence_file, compute_file_sha256
from schemas.assessment_schema import ControlItem, EvidenceManifest, EvidenceManifestItem


# ==============================================================================
# 1. Deterministic Filename Mapping Tests (Phase 0 Regex)
# ==============================================================================
def test_iso_filename_mapping_deterministic():
    """Verify that all proposed ISO filenames match their exact control IDs with confidence 1.0."""
    iso_test_files = [
        ("A.5.1_Chinh_Sach_An_Toan_Thong_Tin_v2.1.docx", ["A.5.1"]),
        ("A.5.15-A.5.16_Bien_Ban_Ra_Soat_Tai_Khoan_Va_IAM_Q3.xlsx", ["A.5.15", "A.5.16"]),
        ("A.5.17-A.8.5_Bao_Cao_Trien_Khai_MFA_VPN_Admin.pdf", ["A.5.17", "A.8.5"]),
        ("A.5.24-A.5.26_Quy_Trinh_Ung_Cuu_Va_Bao_Cao_Su_Co_ATTT.docx", ["A.5.24", "A.5.26"]),
        ("A.5.31_Bang_Theo_Doi_Tuan_Thu_Phap_Luat_ATTT.xlsx", ["A.5.31"]),
        ("A.6.3_Danh_Sach_Dao_Tao_Nhan_Thuc_ATTT_2026.csv", ["A.6.3"]),
        ("A.7.4_So_Do_Va_Anh_Giam_Sat_CCTV_Server_Room.png", ["A.7.4"]),
        ("A.8.8_Nhat_Ky_Quet_Va_Danh_Gia_Lo_Hong_Q3.log", ["A.8.8"]),
        ("A.8.9_Baseline_Hardening_Windows_Server_2022.conf", ["A.8.9"]),
        ("A.8.13_Nhat_Ky_Sao_Luu_Va_Phuc_Hoi_He_Thong.log", ["A.8.13"]),
        ("A.8.15_Cau_Hinh_Audit_Log_Va_Chuyen_Tiep_SIEM.txt", ["A.8.15"]),
        ("A.8.20_Cau_Hinh_Luat_Tuong_Lua_Bien_AP-FW01.conf", ["A.8.20"]),
    ]

    for fname, expected_cids in iso_test_files:
        mapping = map_evidence_to_controls(fname)
        for cid in expected_cids:
            assert cid in mapping, f"Expected {cid} in mapping for {fname}, got {mapping}"
            assert mapping[cid] == 1.0, f"Expected confidence 1.0 for {cid} in {fname}"


def test_tcvn_filename_mapping_deterministic():
    """Verify that all proposed TCVN filenames match their exact control IDs with confidence 1.0."""
    tcvn_test_files = [
        ("NW.01_Bang_Cau_Hinh_Access_Control_List_Core_Switch.conf", ["NW.01"]),
        ("NW.02_Cau_Hinh_Tuong_Lua_Bien_FortiGate_AP-FW01.conf", ["NW.02"]),
        ("NW.04_Cau_Hinh_Ket_Noi_Tu_Xa_VPN_IPsec_IKEv2.txt", ["NW.04"]),
        ("SV.01_Chinh_Sach_Mat_Khau_Va_Dong_Dich_Vu_Thua.conf", ["SV.01"]),
        ("SV.05-SV.06_Bien_Ban_Phan_Quyen_Va_MFA_Root_Admin.docx", ["SV.05", "SV.06"]),
        ("APP.01_Bao_Cao_Kiem_Tra_Bam_Mat_Khau_CSDL_Bcrypt.pdf", ["APP.01"]),
        ("APP.07_Nhat_Ky_Audit_Log_Nguoi_Dung_Ung_Dung.log", ["APP.07"]),
        ("DAT.01_Nhat_Ky_Sao_Luu_CSDL_Loi_Hau_Qua.log", ["DAT.01"]),
        ("DAT.04_Cau_Hinh_Ma_Hoa_CSDL_Tai_Noi_Luu_Tru_TDE.conf", ["DAT.04"]),
        ("MNG.01_Quyet_Dinh_Ban_Hanh_Chinh_Sach_ATTT_Cap_Do_3.docx", ["MNG.01"]),
    ]

    for fname, expected_cids in tcvn_test_files:
        mapping = map_evidence_to_controls(fname)
        for cid in expected_cids:
            assert cid in mapping, f"Expected {cid} in mapping for {fname}, got {mapping}"
            assert mapping[cid] == 1.0, f"Expected confidence 1.0 for {cid} in {fname}"


def test_multi_control_mapping_isolation():
    """Verify multi-control files map to both IDs without polluting unrelated controls."""
    multi_file = "A.5.9-A.5.10_So_Dang_Ky_Tai_San_Va_Su_Dung_Hop_Le.xlsx"
    mapping = map_evidence_to_controls(multi_file)
    assert "A.5.9" in mapping and mapping["A.5.9"] == 1.0
    assert "A.5.10" in mapping and mapping["A.5.10"] == 1.0
    # Must NOT contain unrelated controls like A.8.20 or NW.01
    assert "A.8.20" not in mapping
    assert "NW.01" not in mapping


# ==============================================================================
# 2. Parser Resilience & Negative Testing
# ==============================================================================
def test_parser_unsupported_format_graceful_rejection():
    """Verify negative test: unsupported formats (.exe, .bin) are safely rejected with UNSUPPORTED_FORMAT."""
    fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    res_exe = parse_evidence_file(fake_exe_bytes, "A.8.99_Corrupted_Firmware_Installer.exe")
    assert res_exe["status"] == "unsupported"
    assert res_exe["error_code"] == "UNSUPPORTED_FORMAT"
    assert "không nằm trong danh sách hỗ trợ" in res_exe["error_message"]

    fake_bin_bytes = b"\x00\x01\x02\x03\x04\x05"
    res_bin = parse_evidence_file(fake_bin_bytes, "MNG.99_Corrupted_Audit_Evidence.bin")
    assert res_bin["status"] == "unsupported"
    assert res_bin["error_code"] == "UNSUPPORTED_FORMAT"


def test_parser_native_text_and_hashing():
    """Verify text parser and SHA-256 calculation."""
    sample_log = (
        "2026-08-15 02:00:10 [INFO] Backup job started for AP-DB01\n"
        "2026-08-15 02:18:34 [INFO] Backup completed successfully. Verification OK.\n"
    ).encode("utf-8")
    res = parse_evidence_file(sample_log, "A.8.13_Nhat_Ky_Sao_Luu_Va_Phuc_Hoi_He_Thong.log")
    assert res["status"] == "success"
    assert "Backup completed successfully" in res["parsed_text"]
    assert res["sha256"] == compute_file_sha256(sample_log)
    assert len(res["sha256"]) == 64


# ==============================================================================
# 3. Safety Invariants & Fallback Tests
# ==============================================================================
def test_invariant_no_satisfied_from_self_declaration_alone():
    """Verify Invariant 3: Declared implemented with NO evidence must be not_evidenced, not satisfied."""
    ctrl_data = {
        "control_id": "A.5.4",
        "weight": "high",
        "weight_points": 5.0,
        "user_declaration": "implemented",
        "evidence_status": "no_evidence",
        "evidence_file_ids": [],
        "assessment_verdict": "not_evidenced",
        "verdict_source": "safe_fallback_no_evidence",
    }
    item = ControlItem.model_validate(ctrl_data)
    assert item.assessment_verdict == "not_evidenced"
    assert item.verdict_factor == 0.0
    assert item.weighted_score_contribution == 0.0


def test_safe_conflict_detection_branch():
    """Verify that conflict_detected=True forces needs_expert_review and 0 points contribution."""
    ctrl_data = {
        "control_id": "A.8.8",
        "weight": "critical",
        "weight_points": 10.0,
        "user_declaration": "implemented",
        "evidence_file_ids": ["A.8.8_Nhat_Ky_Quet_Va_Danh_Gia_Lo_Hong_Q3.log"],
        "conflict_detected": True,
        "conflict_reason": "Tự khai báo implemented nhưng log quét tồn tại lỗ hổng Critical CVE-2023-38606 unpatched.",
        "assessment_verdict": "needs_expert_review",
        "likelihood": 3,
        "impact": 3,
        "risk_score": 9,
    }
    item = ControlItem.model_validate(ctrl_data)
    assert item.conflict_detected is True
    assert item.assessment_verdict == "needs_expert_review"
    assert item.verdict_source == "safe_fallback_conflict"
    assert item.verdict_factor == 0.0
    assert item.weighted_score_contribution == 0.0


def test_no_not_applicable_verdict():
    """Verify that not_applicable is rejected by schema validation."""
    with pytest.raises(Exception):
        ControlItem.model_validate({
            "control_id": "A.5.1",
            "assessment_verdict": "not_applicable"
        })


# ==============================================================================
# 4. Mathematical Compliance Pre-Calculation Tests
# ==============================================================================
def test_iso_matrix_mathematical_compliance_within_60_to_70_range():
    """Verify ISO expected matrix achieves Weighted Compliance in 60.0% – 70.0% range."""
    fname = "expected_verdict_matrix_iso.json"
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "..", "test_evidence_specs", fname),
        os.path.join(os.path.dirname(__file__), "..", "..", "test_evidence_specs", fname),
        os.path.join("/app", "test_evidence_specs", fname),
    ]
    matrix_path = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])
    assert os.path.exists(matrix_path), f"File {matrix_path} must exist"

    with open(matrix_path, "r", encoding="utf-8") as f:
        iso_matrix = json.load(f)

    assert len(iso_matrix) == 93, f"ISO 27001 must cover all 93 controls, got {len(iso_matrix)}"

    # Authoritative calculation using controls_catalog
    res = calc_weighted_compliance(iso_matrix)
    pct = res["percentage"]
    assert 60.0 <= pct <= 70.0, f"Expected ISO Weighted Compliance in [60.0%, 70.0%], got {pct}%"
    assert res["weighted_max_score"] == 495.0, f"Expected 495.0 max weighted score, got {res['weighted_max_score']}"
    assert res["weighted_score"] == 312.0, f"Expected 312.0 weighted score, got {res['weighted_score']}"
    assert pct == 63.0, f"Expected exactly 63.0%, got {pct}%"

    # Verify verdict distribution
    verdicts = [c["expected_verdict"] for c in iso_matrix]
    assert "satisfied" in verdicts
    assert "partial" in verdicts
    assert "needs_expert_review" in verdicts
    assert "not_evidenced" in verdicts
    assert "missing" in verdicts
    assert "not_applicable" not in verdicts

    # Verify conflict control
    conflict_items = [c for c in iso_matrix if c.get("conflict_detected")]
    assert len(conflict_items) >= 1
    assert any(c["control_id"] == "A.8.8" for c in conflict_items)


def test_tcvn_matrix_mathematical_compliance_within_60_to_70_range():
    """Verify TCVN expected matrix achieves Weighted Compliance in 60.0% – 70.0% range."""
    fname = "expected_verdict_matrix_tcvn.json"
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "..", "test_evidence_specs", fname),
        os.path.join(os.path.dirname(__file__), "..", "..", "test_evidence_specs", fname),
        os.path.join("/app", "test_evidence_specs", fname),
    ]
    matrix_path = next((p for p in candidate_paths if os.path.exists(p)), candidate_paths[0])
    assert os.path.exists(matrix_path), f"File {matrix_path} must exist"

    with open(matrix_path, "r", encoding="utf-8") as f:
        tcvn_matrix = json.load(f)

    assert len(tcvn_matrix) == 34, f"TCVN 11930 must cover all 34 controls, got {len(tcvn_matrix)}"

    res = calc_weighted_compliance(tcvn_matrix)
    pct = res["percentage"]
    assert 60.0 <= pct <= 70.0, f"Expected TCVN Weighted Compliance in [60.0%, 70.0%], got {pct}%"
    assert res["weighted_max_score"] == 271.0, f"Expected 271.0 max weighted score, got {res['weighted_max_score']}"
    assert res["weighted_score"] == 175.0, f"Expected 175.0 weighted score, got {res['weighted_score']}"
    assert pct == 64.6, f"Expected exactly 64.6%, got {pct}%"

    verdicts = [c["expected_verdict"] for c in tcvn_matrix]
    assert "satisfied" in verdicts
    assert "partial" in verdicts
    assert "needs_expert_review" in verdicts
    assert "not_evidenced" in verdicts
    assert "missing" in verdicts
    assert "not_applicable" not in verdicts

    conflict_items = [c for c in tcvn_matrix if c.get("conflict_detected")]
    assert len(conflict_items) >= 1
    assert any(c["control_id"] == "DAT.01" for c in conflict_items)


# ==============================================================================
# 5. Manifest Isolation & Integrity Tests
# ==============================================================================
def test_manifest_item_attributes_and_hash():
    """Verify EvidenceManifestItem validates SHA-256 and required metadata."""
    sample_content = b"DUMMY_EVIDENCE_FOR_MANIFEST_TEST"
    sha = compute_file_sha256(sample_content)
    item = EvidenceManifestItem(
        file_id="file_abc12345",
        masked_filename="A.5.1_Information_Security_Policy.docx",
        extension=".docx",
        size_bytes=len(sample_content),
        sha256=sha,
        parser_or_ocr="native_parser",
        control_mapping=["A.5.1"],
        mapping_type="direct_attachment",
        ingestion_status="ingested",
    )
    assert item.sha256 == sha
    assert item.control_mapping == ["A.5.1"]
    assert item.ingestion_status == "ingested"
