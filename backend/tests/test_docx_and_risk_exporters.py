"""Tests for DOCX and Risk Register Exporters."""

import pytest
from services.report_docx_generator import generate_report_docx
from services.risk_register_exporter import generate_risk_register_xlsx


def test_generate_report_docx():
    sample_data = {
        "standard": "iso27001",
        "created_at": "2026-09-05T08:00:00Z",
        "compliance_percent": 74.5,
        "system_info": {
            "organization": {"name": "Tập đoàn Điện lực Việt Nam (EVN)", "industry": "Năng lượng"},
            "assessment_standard": "iso27001"
        },
        "json_data": {
            "compliance": {"percentage": 74.5},
            "weight_breakdown": {
                "critical": {"total": 20, "implemented": 15, "percent": 75.0},
                "high": {"total": 30, "implemented": 22, "percent": 73.3},
                "medium": {"total": 30, "implemented": 20, "percent": 66.7},
                "low": {"total": 13, "implemented": 12, "percent": 92.3},
            },
            "risk_register": [
                {
                    "control_id": "A.8.8",
                    "label": "Quản lý lỗ hổng kỹ thuật",
                    "gap": "Phát hiện hệ điều hành Windows Server 2008 R2 EOL và Hotfix N/A",
                    "severity": "critical",
                    "likelihood": 5,
                    "impact": 5,
                    "risk_score": 25,
                    "recommendation": "Nâng cấp OS lên Windows Server 2022 và cô lập phân vùng."
                }
            ]
        }
    }

    docx_bytes = generate_report_docx(sample_data)
    assert docx_bytes is not None
    assert len(docx_bytes) > 2000
    # Check PK zip header for docx
    assert docx_bytes[:2] == b"PK"


def test_generate_risk_register_xlsx():
    sample_data = {
        "standard": "ISO 27001:2022",
        "system_info": {"organization": {"name": "EVN Enterprise Infrastructure"}},
        "json_data": {
            "risk_register": [
                {
                    "control_id": "A.8.20",
                    "label": "Bảo mật mạng",
                    "category": "A.8 Công nghệ",
                    "gap": "Chưa kích hoạt IPS trên đường truyền kết nối trạm",
                    "severity": "high",
                    "likelihood": 4,
                    "impact": 4,
                    "risk_score": 16,
                    "recommendation": "Kích hoạt IPS profile và cập nhật signature hàng ngày."
                }
            ]
        }
    }

    xlsx_bytes = generate_risk_register_xlsx(assessment_data=sample_data)
    assert xlsx_bytes is not None
    assert len(xlsx_bytes) > 1000
    # Check PK zip header for xlsx
    assert xlsx_bytes[:2] == b"PK"


def test_api_export_endpoints(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    import api.routes.iso27001 as iso_mod

    # Setup dummy assessment
    test_id = "test_audit_001"
    sample_data = {
        "id": test_id,
        "standard": "iso27001",
        "created_at": "2026-09-05T08:00:00Z",
        "compliance_percent": 85.0,
        "system_info": {
            "organization": {"name": "Test Enterprise"},
            "assessment_standard": "iso27001"
        },
        "json_data": {
            "compliance": {"percentage": 85.0},
            "risk_register": [
                {"control_id": "A.5.1", "severity": "low", "likelihood": 2, "impact": 2, "risk_score": 4}
            ]
        }
    }

    monkeypatch.setattr(iso_mod, "load_assessment", lambda aid: sample_data if aid == test_id else None)

    client = TestClient(app)

    # Test DOCX endpoint
    resp_docx = client.post(f"/api/iso27001/assessments/{test_id}/export-docx")
    assert resp_docx.status_code == 200
    assert resp_docx.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert resp_docx.content[:2] == b"PK"

    # Test Risk Register endpoint
    resp_risk = client.post(f"/api/iso27001/assessments/{test_id}/export-risk-register")
    assert resp_risk.status_code == 200
    assert resp_risk.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert resp_risk.content[:2] == b"PK"

    # Test PDF endpoint with weasyprint & healed report
    sample_data_completed = dict(sample_data)
    sample_data_completed["status"] = "completed"
    sample_data_completed["result"] = {
        "report": (
            "## 1. ĐÁNH GIÁ TỔNG QUAN\nTuân thủ: 85%\n\n"
            "## 5. EXECUTIVE SUMMARY\n"
            "a) Metrics Overview\n"
            "- Tỷ lệ Tuân thủ: 85%\n\n"
            "### b) Top 3 R"
        ),
        "json_data": sample_data["json_data"],
        "compliance_percent": 85.0
    }
    monkeypatch.setattr(iso_mod, "load_assessment", lambda aid: sample_data_completed if aid == test_id else None)

    resp_pdf = client.post(f"/api/iso27001/assessments/{test_id}/export-pdf")
    assert resp_pdf.status_code == 200
    # Returns PDF or fallback HTML
    assert resp_pdf.headers["content-type"] in ["application/pdf", "text/html; charset=utf-8"]
    if resp_pdf.headers["content-type"] == "application/pdf":
        assert resp_pdf.content[:4] == b"%PDF"


def test_chat_service_ensure_complete_report_heals_truncated():
    from services.chat_service import ChatService

    # Case 1: Truncated at '### b) Top 3 R'
    truncated_input = (
        "## 1. ĐÁNH GIÁ TỔNG QUAN\n"
        "Nội dung tổng quan...\n\n"
        "## 5. EXECUTIVE SUMMARY (TÓM TẮT CHO BAN LÃNH ĐẠO)\n"
        "a) Metrics Overview\n"
        "- Tỷ lệ Tuân thủ: 55.6%\n\n"
        "### b) Top 3 R"
    )

    healed = ChatService.ensure_complete_report(
        markdown_report=truncated_input,
        percentage=55.6,
        score=47,
        max_score=93,
        org_name="Công ty TNHH MTV Nhiệt điện Thủ Đức",
        std_name="ISO 27001:2022"
    )

    assert "### b) Top 3 R" not in healed.split("\n\n")[-1]
    assert "Top 3 Rủi ro trọng yếu" in healed
    assert "VND" in healed
    assert "Next Steps" in healed or "Lộ trình triển khai" in healed
    assert "30 ngày" in healed

    # Case 2: Complete report should not be damaged
    complete_input = (
        "## 1. ĐÁNH GIÁ TỔNG QUAN\n"
        "Nội dung...\n\n"
        "## 5. EXECUTIVE SUMMARY\n"
        "### b) Top 3 rủi ro:\n"
        "1. Rủi ro 1 rất dài và chi tiết có đầy đủ thông tin bảo mật và phân tích kỹ thuật hơn 150 ký tự để không bị coi là bị cắt ngắn giữa chừng khi kiểm tra.\n"
        "### c) Next Steps:\n"
        "1. Kế hoạch 30 ngày chi tiết."
    )
    res_complete = ChatService.ensure_complete_report(markdown_report=complete_input)
    assert res_complete == complete_input

