"""Comprehensive Audit Test Suite for Weighted Compliance (10-5-3-1 Scheme).

Validates all 20 mandatory requirements from Section 10:
1. No controls achieved -> Weighted Compliance = 0.0%
2. Self-declared implemented without evidence -> Raw coverage increases, Weighted compliance = 0.0%
3. Self-declared implemented + file attached but no AI verdict -> needs_expert_review, Weighted compliance = 0.0%
4. Self-declared implemented but AI verdict missing -> 0 pts
5. Not self-declared but AI verdict satisfied -> full weight
6. partial -> 50% weight
7. All controls satisfied -> 100.0%
8. Duplicate control IDs not double-counted
9. Non-existent control IDs don't affect score
10. All 5 authoritative verdicts participate in denominator (no controls excluded)
11. ISO 27001 weighted_max_score = 495.0
12. TCVN 11930 weighted_max_score = 271.0
13. weighted_compliance.percentage == round(weighted_score / weighted_max_score * 100, 1)
14. compliance.percentage, API response, persisted assessment and export agree
15. All verdicts not_evidenced/missing -> Weighted Compliance = 0.0%
16. Critical satisfied -> 10.0 pts
17. High satisfied -> 5.0 pts
18. Medium satisfied -> 3.0 pts
19. Low satisfied -> 1.0 pt
20. Critical partial -> 5.0 pts
"""

import pytest
from services.controls_catalog import (
    WEIGHT_SCORE,
    VERDICT_FACTOR,
    calc_weighted_compliance,
    calc_compliance,
    calc_tcvn_compliance,
    get_flat_controls,
    ISO_27001_CATEGORIES,
    TCVN_11930_CATEGORIES,
)
from services.chat_service import ChatService


def test_req11_iso_max_score_is_495():
    """Req 11: ISO 27001 has 93 controls and weighted_max_score = 495.0."""
    iso_controls = get_flat_controls("iso27001")
    assert len(iso_controls) == 93
    max_score = sum(WEIGHT_SCORE.get(c.get("weight", "medium"), 3.0) for c in iso_controls)
    assert max_score == 495.0

    res = calc_compliance(implemented=[c["id"] for c in iso_controls], standard="iso27001")
    assert res["weighted_compliance"]["weighted_max_score"] == 495.0


def test_req12_tcvn_max_score_is_271():
    """Req 12: TCVN 11930 has 34 controls and weighted_max_score = 271.0."""
    tcvn_controls = get_flat_controls("tcvn11930")
    assert len(tcvn_controls) == 34
    max_score = sum(WEIGHT_SCORE.get(c.get("weight", "medium"), 3.0) for c in tcvn_controls)
    assert max_score == 271.0

    res = calc_tcvn_compliance(implemented=[c["id"] for c in tcvn_controls])
    assert res["weighted_compliance"]["weighted_max_score"] == 271.0


def test_req16_17_18_19_20_per_weight_points():
    """Req 16, 17, 18, 19, 20: Individual weight contributions."""
    assert WEIGHT_SCORE["critical"] == 10.0
    assert WEIGHT_SCORE["high"] == 5.0
    assert WEIGHT_SCORE["medium"] == 3.0
    assert WEIGHT_SCORE["low"] == 1.0

    # Req 16: One Critical satisfied contributes 10.0
    res_crit = calc_weighted_compliance([{"id": "C1", "weight": "critical", "assessment_verdict": "satisfied"}])
    assert res_crit["weighted_score"] == 10.0
    assert res_crit["weighted_max_score"] == 10.0
    assert res_crit["percentage"] == 100.0

    # Req 17: One High satisfied contributes 5.0
    res_high = calc_weighted_compliance([{"id": "H1", "weight": "high", "assessment_verdict": "satisfied"}])
    assert res_high["weighted_score"] == 5.0
    assert res_high["weighted_max_score"] == 5.0
    assert res_high["percentage"] == 100.0

    # Req 18: One Medium satisfied contributes 3.0
    res_med = calc_weighted_compliance([{"id": "M1", "weight": "medium", "assessment_verdict": "satisfied"}])
    assert res_med["weighted_score"] == 3.0
    assert res_med["weighted_max_score"] == 3.0
    assert res_med["percentage"] == 100.0

    # Req 19: One Low satisfied contributes 1.0
    res_low = calc_weighted_compliance([{"id": "L1", "weight": "low", "assessment_verdict": "satisfied"}])
    assert res_low["weighted_score"] == 1.0
    assert res_low["weighted_max_score"] == 1.0
    assert res_low["percentage"] == 100.0

    # Req 20: One Critical partial contributes 5.0 (50% of 10.0)
    res_crit_part = calc_weighted_compliance([{"id": "C1", "weight": "critical", "assessment_verdict": "partial"}])
    assert res_crit_part["weighted_score"] == 5.0
    assert res_crit_part["weighted_max_score"] == 10.0
    assert res_crit_part["percentage"] == 50.0


def test_req1_and_req15_zero_controls_achieved():
    """Req 1 & 15: When no controls achieved or all not_evidenced/missing -> Weighted Compliance = 0.0%."""
    iso_controls = get_flat_controls("iso27001")
    controls_out = [
        {"id": c["id"], "weight": c.get("weight", "medium"), "assessment_verdict": "missing"}
        for c in iso_controls
    ]
    res = calc_weighted_compliance(controls_out)
    assert res["weighted_score"] == 0.0
    assert res["weighted_max_score"] == 495.0
    assert res["percentage"] == 0.0

    # Mixed not_evidenced and missing
    controls_out_mixed = [
        {"id": c["id"], "weight": c.get("weight", "medium"), "assessment_verdict": "not_evidenced" if i % 2 == 0 else "missing"}
        for i, c in enumerate(iso_controls)
    ]
    res_mixed = calc_weighted_compliance(controls_out_mixed)
    assert res_mixed["weighted_score"] == 0.0
    assert res_mixed["percentage"] == 0.0


def test_req2_self_declared_without_evidence_does_not_increase_weighted_compliance():
    """Req 2: Self-declared Implemented without evidence -> Raw coverage increases, Weighted Compliance = 0.0%."""
    iso_controls = get_flat_controls("iso27001")
    implemented_sample = [c["id"] for c in iso_controls[:20]]

    # Process through ChatService._build_structured_json with NO evidence and NO AI verdicts
    json_data = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=21.5,
        score=20,
        max_score=93,
        implemented=implemented_sample,
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001",
        standard="iso27001",
        today="2026-09-20",
        effective_mode="local",
        control_verdicts=[],  # No AI verdicts
        all_controls_flat=iso_controls,
        evidence_map={},      # No files attached
    )

    # Raw coverage reflects self-declaration
    assert json_data["control_coverage"]["self_declared_implemented"] == 20
    assert json_data["control_coverage"]["raw_percentage"] == round(20 / 93 * 100, 1)

    # Weighted compliance must be strictly 0.0% because verdicts are not_evidenced
    assert json_data["weighted_compliance"]["weighted_score"] == 0.0
    assert json_data["weighted_compliance"]["percentage"] == 0.0
    assert json_data["compliance"]["percentage"] == 0.0


def test_req3_self_declared_with_file_without_ai_verdict_needs_expert_review_zero_score():
    """Req 3: Self-declared Implemented + file attached without AI verdict -> needs_expert_review, 0 score."""
    iso_controls = get_flat_controls("iso27001")
    cid = iso_controls[0]["id"]  # Critical control A.5.1

    json_data = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=1.0,
        score=1,
        max_score=93,
        implemented=[cid],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001",
        standard="iso27001",
        today="2026-09-20",
        effective_mode="local",
        control_verdicts=[],  # No AI verdict yet
        all_controls_flat=iso_controls,
        evidence_map={cid: ["policy.pdf"]},  # File attached
    )

    ctrl_item = next(c for c in json_data["controls"] if c["control_id"] == cid)
    assert ctrl_item["assessment_verdict"] == "needs_expert_review"
    assert ctrl_item["evidence_status"] == "direct_attachment"

    # Weighted compliance must be 0.0 because needs_expert_review gets 0 factor
    assert json_data["weighted_compliance"]["weighted_score"] == 0.0
    assert json_data["weighted_compliance"]["percentage"] == 0.0


def test_req4_self_declared_implemented_but_ai_verdict_missing_gets_zero():
    """Req 4: Self-declared Implemented but AI verdict is missing -> 0 points."""
    iso_controls = get_flat_controls("iso27001")
    cid = "A.5.1"  # Critical (10 pts)

    json_data = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=1.0,
        score=1,
        max_score=93,
        implemented=[cid],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001",
        standard="iso27001",
        today="2026-09-20",
        effective_mode="local",
        control_verdicts=[{"control_id": cid, "evidence_verdict": "missing", "confidence": 0.9}],
        all_controls_flat=iso_controls,
        evidence_map={cid: ["invalid.pdf"]},
    )

    ctrl_item = next(c for c in json_data["controls"] if c["control_id"] == cid)
    assert ctrl_item["assessment_verdict"] in ("missing", "needs_expert_review")
    assert json_data["weighted_compliance"]["weighted_score"] == 0.0
    assert json_data["weighted_compliance"]["percentage"] == 0.0


def test_req5_not_self_declared_but_ai_verdict_satisfied_gets_full_weight():
    """Req 5: NOT self-declared but AI verdict is satisfied -> receives full weight."""
    iso_controls = get_flat_controls("iso27001")
    cid = "A.5.1"  # Critical (10 pts)

    json_data = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=0.0,
        score=0,
        max_score=93,
        implemented=[],  # User did NOT tick A.5.1
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001",
        standard="iso27001",
        today="2026-09-20",
        effective_mode="local",
        control_verdicts=[{
            "control_id": cid,
            "evidence_verdict": "satisfied",
            "confidence": 0.95,
            "citations": [{"file_name": "A51_policy.pdf"}],
        }],
        all_controls_flat=iso_controls,
        evidence_map={cid: ["A51_policy.pdf"]},
    )

    ctrl_item = next(c for c in json_data["controls"] if c["control_id"] == cid)
    assert ctrl_item["assessment_verdict"] == "satisfied"
    assert ctrl_item["user_declaration"] == "not_implemented"
    assert json_data["weighted_compliance"]["weighted_score"] == 10.0
    assert json_data["weighted_compliance"]["percentage"] == round(10.0 / 495.0 * 100, 1)


def test_req6_partial_verdict_receives_half_weight():
    """Req 6: partial verdict receives 50% weight."""
    controls = [
        {"control_id": "C1", "weight": "critical", "assessment_verdict": "partial"},  # 10 * 0.5 = 5.0
        {"control_id": "H1", "weight": "high", "assessment_verdict": "partial"},      # 5 * 0.5 = 2.5
        {"control_id": "M1", "weight": "medium", "assessment_verdict": "satisfied"},  # 3 * 1.0 = 3.0
    ]
    res = calc_weighted_compliance(controls)
    assert res["weighted_score"] == 10.5
    assert res["weighted_max_score"] == 18.0
    assert res["percentage"] == round(10.5 / 18.0 * 100, 1)


def test_req7_all_controls_satisfied_is_100_percent():
    """Req 7: All controls satisfied -> 100.0%."""
    iso_controls = get_flat_controls("iso27001")
    all_verdicts = [
        {
            "control_id": c["id"],
            "evidence_verdict": "satisfied",
            "confidence": 1.0,
            "citations": [{"file_name": f"{c['id']}_evidence.pdf"}],
        }
        for c in iso_controls
    ]
    ev_map = {c["id"]: [f"{c['id']}_evidence.pdf"] for c in iso_controls}

    json_data = ChatService._build_structured_json(
        raw_analysis="Full compliance",
        percentage=100.0,
        score=93,
        max_score=93,
        implemented=[c["id"] for c in iso_controls],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="Perfect Org",
        industry="Defense",
        org_size="enterprise",
        employees=1000,
        std_name="ISO 27001",
        standard="iso27001",
        today="2026-09-20",
        effective_mode="local",
        control_verdicts=all_verdicts,
        all_controls_flat=iso_controls,
        evidence_map=ev_map,
    )

    assert json_data["weighted_compliance"]["weighted_score"] == 495.0
    assert json_data["weighted_compliance"]["weighted_max_score"] == 495.0
    assert json_data["weighted_compliance"]["percentage"] == 100.0
    assert json_data["compliance"]["percentage"] == 100.0


def test_req8_and_req9_duplicate_and_invalid_ids():
    """Req 8 & 9: Duplicate IDs and non-existent IDs."""
    bloated_ids = ["A.5.1", "A.5.1", "A.5.1", "INVALID_123", "NONEXISTENT_XYZ", "A.5.2"]
    res = calc_compliance(bloated_ids, "iso27001")
    # Only A.5.1 and A.5.2 are valid, counted exactly once
    assert res["score"] == 2
    assert res["control_coverage"]["self_declared_implemented"] == 2
    # Both are critical (10 + 10 = 20 pts)
    assert res["achieved_weighted"] == 20.0
    assert res["max_weighted"] == 495.0


def test_req10_all_standard_verdicts_participate_in_denominator():
    """Req 10: All 5 authoritative verdicts participate in denominator (no controls excluded)."""
    controls = [
        {"control_id": "C1", "weight": "critical", "assessment_verdict": "satisfied"},            # 10 / 10
        {"control_id": "H1", "weight": "high", "assessment_verdict": "not_evidenced"},             # 0 / 5
        {"control_id": "M1", "weight": "medium", "assessment_verdict": "missing"},                 # 0 / 3
        {"control_id": "L1", "weight": "low", "assessment_verdict": "needs_expert_review"},       # 0 / 1
    ]
    res = calc_weighted_compliance(controls)
    # Denominator: 10 + 5 + 3 + 1 = 19.0, numerator: 10.0
    assert res["weighted_max_score"] == 19.0
    assert res["weighted_score"] == 10.0
    assert res["percentage"] == round(10.0 / 19.0 * 100, 1)


def test_req13_math_consistency():
    """Req 13: weighted_compliance.percentage == round(weighted_score / weighted_max_score * 100, 1)."""
    controls = [
        {"control_id": "C1", "weight": "critical", "assessment_verdict": "satisfied"},
        {"control_id": "H1", "weight": "high", "assessment_verdict": "partial"},
        {"control_id": "M1", "weight": "medium", "assessment_verdict": "missing"},
        {"control_id": "L1", "weight": "low", "assessment_verdict": "satisfied"},
    ]
    res = calc_weighted_compliance(controls)
    # C1 (10) + H1 (2.5) + M1 (0) + L1 (1) = 13.5
    # Max: 10 + 5 + 3 + 1 = 19.0
    expected = round((13.5 / 19.0 * 100), 1)
    assert res["percentage"] == expected


def test_req14_compliance_and_weighted_compliance_agree():
    """Req 14: compliance.percentage and weighted_compliance.percentage are unified."""
    iso_controls = get_flat_controls("iso27001")
    verdicts = [
        {"control_id": "A.5.1", "evidence_verdict": "satisfied", "confidence": 0.95},
        {"control_id": "A.5.2", "evidence_verdict": "satisfied", "confidence": 0.95},
    ]
    json_data = ChatService._build_structured_json(
        raw_analysis="Test",
        percentage=50.0,
        score=2,
        max_score=93,
        implemented=["A.5.1", "A.5.2"],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=10,
        std_name="ISO 27001",
        standard="iso27001",
        today="2026-09-20",
        effective_mode="local",
        control_verdicts=verdicts,
        all_controls_flat=iso_controls,
        evidence_map={},
    )

    w_pct = json_data["weighted_compliance"]["percentage"]
    c_pct = json_data["compliance"]["percentage"]
    assert w_pct == c_pct
    assert json_data["weighted_compliance"]["algorithm"] == "verdict_weighted_v2"
    assert json_data["weighted_compliance"]["weight_scheme"] == "critical_10_high_5_medium_3_low_1"


def test_req21_weighted_coverage_vs_compliance_isolation():
    """Verify weighted_coverage reflects self-declaration (e.g. 58.4%) while weighted_compliance reflects verdicts (0.0%)."""
    iso_controls = get_flat_controls("iso27001")
    # Take first 45 controls as implemented
    impl_45 = [c["id"] for c in iso_controls[:45]]

    # 1. Test preliminary calc_compliance
    from services.controls_catalog import calc_compliance
    prelim = calc_compliance(impl_45, "iso27001")
    assert "weighted_coverage" in prelim
    assert prelim["weighted_coverage"]["score"] > 0
    assert prelim["weighted_coverage"]["max_score"] == 495.0

    # 2. Test _build_structured_json with 0 verified controls
    json_data = ChatService._build_structured_json(
        raw_analysis="Test",
        percentage=0.0,
        score=45,
        max_score=93,
        implemented=impl_45,
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=10,
        std_name="ISO 27001",
        standard="iso27001",
        today="2026-09-20",
        effective_mode="local",
        control_verdicts=[],  # No verdicts
        all_controls_flat=iso_controls,
        evidence_map={},
    )

    assert "weighted_coverage" in json_data
    # weighted_coverage is positive based on 45 self-declared controls
    assert json_data["weighted_coverage"]["score"] > 0
    assert json_data["weighted_coverage"]["max_score"] == 495.0
    # But weighted_compliance MUST be 0.0 because verdicts are not_evidenced
    assert json_data["weighted_compliance"]["weighted_score"] == 0.0
    assert json_data["weighted_compliance"]["percentage"] == 0.0


def test_req22_45_self_declared_0_satisfied_unified_validation():
    """Req 22: Mandated Case 45 self-declared, 0 satisfied -> Raw=48.4%, Prelim=58.4%, Weighted=0.0%, Satisfied=0/93."""
    import os
    import json
    from schemas.assessment_schema import UnifiedAssessmentResult

    data_path = os.getenv("DATA_PATH", "./data")
    bee_path = os.path.join(data_path, "assessments", "bee45c5c-3c2b-4791-8abd-2ad516a69eb1.json")
    if not os.path.exists(bee_path):
        alt = os.path.join(data_path, "assessments", "asm_zero_verified_2026.json")
        if os.path.exists(alt):
            bee_path = alt
    assert os.path.exists(bee_path), f"File {bee_path} must exist"

    with open(bee_path, "r", encoding="utf-8") as f:
        raw_dict = json.load(f)

    validated = UnifiedAssessmentResult.model_validate(raw_dict)

    # Invariant checks
    assert validated.control_coverage.self_declared_implemented == 45
    assert validated.control_coverage.evidence_supported_implemented == 0
    assert validated.control_coverage.total_applicable_controls == 93
    assert validated.control_coverage.raw_percentage == 48.4

    # Preliminary weighted coverage is separated
    assert validated.weighted_coverage["score"] in (246.0, 289.0)
    assert validated.weighted_coverage["max_score"] == 495.0
    assert validated.weighted_coverage["percentage"] in (49.7, 58.4)

    # Official weighted compliance MUST be strictly 0.0% and algorithm verdict_weighted_v2
    assert validated.weighted_compliance.weighted_score == 0.0
    assert validated.weighted_compliance.weighted_max_score == 495.0
    assert validated.weighted_compliance.percentage == 0.0
    assert validated.weighted_compliance.algorithm == "verdict_weighted_v2"
    assert validated.weighted_compliance.weight_scheme == "critical_10_high_5_medium_3_low_1"

    # Invariant: sum of contributions equals weighted_compliance.weighted_score
    contrib_sum = sum(c.weighted_score_contribution for c in validated.controls)
    assert round(contrib_sum, 1) == validated.weighted_compliance.weighted_score == 0.0


def test_req23_test_pack_69_4_calculation():
    """Req 23: Test pack calculation: A.5.1 sat Crit=10, A.5.3 part High=2.5, A.5.5 miss Med=0 -> 12.5 / 18 = 69.4%."""
    from schemas.assessment_schema import UnifiedAssessmentResult

    controls_data = [
        {
            "control_id": "A.5.1",
            "weight": "critical",
            "assessment_verdict": "satisfied",
            "conflict_detected": False
        },
        {
            "control_id": "A.5.3",
            "weight": "high",
            "assessment_verdict": "partial",
            "conflict_detected": False
        },
        {
            "control_id": "A.5.5",
            "weight": "medium",
            "assessment_verdict": "missing",
            "conflict_detected": False
        }
    ]

    raw_dict = {
        "assessment_id": "test-pack-01",
        "run_id": "run_test_pack_01",
        "status": "completed",
        "standard": "iso27001",
        "controls": controls_data
    }

    validated = UnifiedAssessmentResult.model_validate(raw_dict)

    # Max = 18.0.
    # Score: A.5.1 (10 * 1.0 = 10), A.5.3 (5 * 0.5 = 2.5), A.5.5 (3 * 0.0 = 0) -> Score = 12.5.
    # Percentage: 12.5 / 18.0 * 100% = 69.444...% -> 69.4%
    assert validated.weighted_compliance.weighted_score == 12.5
    assert validated.weighted_compliance.weighted_max_score == 18.0
    assert validated.weighted_compliance.percentage == 69.4
    assert validated.weighted_compliance.algorithm == "verdict_weighted_v2"
    assert validated.weighted_compliance.weight_scheme == "critical_10_high_5_medium_3_low_1"

    # Invariant: sum of contributions equals weighted_compliance.weighted_score
    contrib_sum = sum(c.weighted_score_contribution for c in validated.controls)
    assert round(contrib_sum, 1) == validated.weighted_compliance.weighted_score == 12.5


def test_req24_conflict_detected_forces_zero_contribution():
    """Req 24: conflict_detected=True or needs_expert_review forces contribution to 0."""
    from schemas.assessment_schema import UnifiedAssessmentResult

    controls_data = [
        {
            "control_id": "A.5.1",
            "weight": "critical",
            "assessment_verdict": "satisfied",
            "conflict_detected": True  # Conflict flag overrides verdict factor
        },
        {
            "control_id": "A.5.2",
            "weight": "high",
            "assessment_verdict": "needs_expert_review",
            "conflict_detected": False
        }
    ]

    raw_dict = {
        "assessment_id": "conflict-test",
        "run_id": "run_conflict_01",
        "status": "completed",
        "standard": "iso27001",
        "controls": controls_data
    }

    validated = UnifiedAssessmentResult.model_validate(raw_dict)
    c1 = next(c for c in validated.controls if c.control_id == "A.5.1")
    assert c1.verdict_factor == 0.0
    assert c1.weighted_score_contribution == 0.0

    c2 = next(c for c in validated.controls if c.control_id == "A.5.2")
    assert c2.verdict_factor == 0.0
    assert c2.weighted_score_contribution == 0.0

    assert validated.weighted_compliance.weighted_score == 0.0
    assert validated.weighted_compliance.percentage == 0.0


def test_req25_risk_register_4x4_matrix_scores_max_16():
    """Req 25: Risk Register uses 4x4 matrix with scores between 1 and 16, no score 20."""
    from services.risk_scoring import calculate_risk_score, classify_risk_severity, is_valid_risk_score
    from services.risk_register_exporter import generate_risk_register_xlsx
    import openpyxl

    # Test all 4x4 combinations
    for l in range(1, 5):
        for i in range(1, 5):
            score = calculate_risk_score(l, i)
            assert 1 <= score <= 16
            assert is_valid_risk_score(score)
            sev = classify_risk_severity(score)
            assert sev in ("critical", "high", "medium", "low")

    # Ensure invalid legacy score 20 is caught / capped in exporter
    test_assessment = {
        "assessment_id": "risk-test-01",
        "run_id": "run_risk_01",
        "status": "completed",
        "standard": "iso27001",
        "top_gaps": [
            {"id": "A.8.1", "gap": "Test Gap", "severity": "critical", "likelihood": 5, "impact": 4, "risk_score": 20}
        ],
        "controls": []
    }

    xlsx_bytes = generate_risk_register_xlsx(assessment_data=test_assessment)
    import io
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    # Row 4 is first data row; Column 9 is Risk Score (L×I)
    score_val = ws.cell(row=4, column=9).value
    assert score_val is not None
    assert int(score_val) <= 16, f"Risk score must not exceed 16, got {score_val}"
    assert int(score_val) != 20, "Legacy score 20 must not appear in Risk Register"


