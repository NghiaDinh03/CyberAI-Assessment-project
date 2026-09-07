"""Test Suite for Multi-Agent Assessment Pipeline & Audit Feedback Loop.

Validates:
1. Agent 1 (EvidenceFactExtractor) dynamic extraction using LLM & fallback on real evidence files.
2. Extraction of both security strengths (tích xanh) and security deficiencies (tích đỏ/vàng).
3. AuditFeedbackStore SQLite database operations and few-shot exemplar prompt formatting.
4. Integration with build_chunk_prompt and Agent 2 prompt injection.
5. Full evidence parsing pipeline without 1000-char truncation.
"""

import json
import os
import tempfile
from unittest.mock import patch
import pytest
from pathlib import Path

from services.evidence_fact_extractor import EvidenceFactExtractor, SecurityFactCard
from repositories.feedback_store import AuditFeedbackStore
from services.evidence_parser import parse_evidence_file
from services.assessment_helpers import build_chunk_prompt


# Locate sample evidence
TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
REPO_ROOT = TESTS_DIR.parent.parent
EXAMPLE_EVIDENCE_DIR = REPO_ROOT / ".AI_CONTEXT" / "Example_envident"


def _get_sample_log_content() -> str:
    """Helper to find sample log file either from fixtures or .AI_CONTEXT."""
    fixture_file = FIXTURES_DIR / "evn_sample_10_140_0_103.txt"
    if fixture_file.exists():
        return fixture_file.read_text(encoding="utf-8", errors="replace")
    
    evn_file = EXAMPLE_EVIDENCE_DIR / "EVN" / "4.Q2_2026_LẦN4" / "001.INFO" / "10.140.0.103.txt"
    if evn_file.exists():
        return evn_file.read_text(encoding="utf-8", errors="replace")
        
    raise FileNotFoundError("Could not locate evn sample evidence file in fixtures or .AI_CONTEXT")


class TestAgent1FactExtraction:
    """Test Agent 1 (Qwen2.5-Coder / EvidenceFactExtractor) dynamic & deterministic analysis."""

    def test_extract_facts_from_real_evn_server_log(self):
        """Test extraction against real 10.140.0.103.txt from EVN dataset."""
        raw_content = _get_sample_log_content()
        fact_card = EvidenceFactExtractor.extract_facts(raw_content, "10.140.0.103.txt", use_llm=False)

        assert isinstance(fact_card, SecurityFactCard)
        assert fact_card.category == "host_configuration"

        # 1. Verify Host Metadata
        meta = fact_card.host_metadata
        assert meta.get("hostname") == "DIM"
        assert "Windows Server 2008" in meta.get("os_name", "")
        assert meta.get("is_eol") is True
        assert "10.140.0.103" in meta.get("ip_addresses", [])

        # 2. Verify Security Deficiencies (Căn cứ tích đỏ/vàng)
        deficiencies = fact_card.security_deficiencies
        assert len(deficiencies) >= 2

        deficiency_names = [d["name"].lower() for d in deficiencies]
        assert any("hết hạn" in name or "eol" in name for name in deficiency_names)
        assert any("sql server" in name for name in deficiency_names)
        assert any("hotfix" in name or "bản vá" in name for name in deficiency_names)

        # 3. Verify Security Strengths (Căn cứ tích xanh)
        strengths = fact_card.security_strengths
        assert len(strengths) >= 1
        assert any("tường lửa" in s.lower() or "firewall" in s.lower() for s in strengths)

        # 4. Verify Compliance Readiness
        readiness = fact_card.compliance_readiness
        assert len(readiness.get("failing_controls", [])) >= 1

        # 5. Verify Compact Summary output
        summary = fact_card.to_compact_summary()
        assert "DIM" in summary
        assert "[CRITICAL]" in summary or "[HIGH]" in summary
        assert "Windows Server 2008" in summary

    def test_extract_facts_from_policy_document(self):
        """Test extraction against administrative policy text (Tích xanh A.5.1)."""
        policy_text = """
        CÔNG TY CỔ PHẦN CÔNG NGHỆ CYBERAI
        QUY CHẾ AN TOÀN THÔNG TIN VÀ QUẢN LÝ TRUY CẬP
        Số: 12/2025/QC-ATTT
        Ngày ban hành: 15/08/2025
        Người phê duyệt: Giám đốc Điều hành - Nguyễn Văn A
        Phiên bản: 2.1
        Phạm vi áp dụng: Toàn bộ cán bộ nhân viên và đối tác.
        Điều 5: Bắt buộc kích hoạt xác thực đa yếu tố (MFA) cho toàn bộ tài khoản quản trị.
        Điều 8: Sao lưu dữ liệu định kỳ mỗi 24 giờ, kiểm tra khôi phục mỗi quý.
        """
        fact_card = EvidenceFactExtractor.extract_facts(policy_text, "Quy_Che_ATTT_v2.1.docx", use_llm=False)
        assert fact_card.category == "policy_governance"
        assert fact_card.governance_facts.get("issue_date") == "15/08/2025"
        assert fact_card.governance_facts.get("version") == "2.1"
        assert "Nguyễn Văn A" in fact_card.governance_facts.get("approved_by", "")
        
        # Verify satisfied controls (Tích xanh)
        sat_controls = [c["control_id"] for c in fact_card.compliance_readiness.get("satisfied_controls", [])]
        assert "A.5.1" in sat_controls

    def test_extract_facts_from_va_scan_report(self):
        """Test extraction against Vulnerability Assessment report snippet."""
        va_text = """
        BÁO CÁO ĐÁNH GIÁ LỖ HỔNG BẢO MẬT (VULNERABILITY ASSESSMENT)
        Hệ thống: Cổng dịch vụ công
        Phát hiện các lỗ hổng nghiêm trọng:
        1. CVE-2021-44228 (Log4Shell) - CVSS 10.0 Critical trên máy chủ 10.140.0.11
        2. CVE-2023-38606 (Kernel Privilege Escalation) - CVSS 8.8 High
        3. CVE-2024-21413 (Microsoft Outlook RCE) - CVSS 9.8 Critical
        """
        fact_card = EvidenceFactExtractor.extract_facts(va_text, "Bao_Cao_VA_Dot4.pdf", use_llm=False)
        assert fact_card.category == "vulnerability_assessment"
        assert len(fact_card.security_deficiencies) >= 1
        va_def = fact_card.security_deficiencies[0]
        assert "CVE-2021-44228" in va_def["evidence_snippet"]
        assert va_def["risk_level"] == "critical"

    def test_dynamic_llm_agent_fact_extraction(self):
        """Test Agent 1 dynamic LLM invocation and JSON reasoning synthesis."""
        mock_llm_response = {
            "summary": "Tệp cấu hình NGINX và SSL cho cổng thông tin điện tử.",
            "category": "host_configuration",
            "host_metadata": {
                "hostname": "portal-web-01",
                "os_name": "Ubuntu 22.04 LTS",
                "os_version": "22.04",
                "is_eol": False,
                "ip_addresses": ["10.10.20.5"],
                "domain": "portal.gov.vn"
            },
            "security_strengths": [
                "Bật giao thức TLS 1.3 và HSTS",
                "Cấu hình Content Security Policy (CSP) chặt chẽ"
            ],
            "security_deficiencies": [
                {
                    "type": "insecure_protocol",
                    "name": "Vẫn chấp nhận TLS 1.0 trên cổng 8443",
                    "risk_level": "medium",
                    "evidence_snippet": "ssl_protocols TLSv1 TLSv1.2 TLSv1.3;",
                    "control_ids": ["A.8.24"]
                }
            ],
            "governance_facts": {},
            "software_inventory": [{"name": "nginx", "version": "1.24.0"}],
            "network_and_access": {"firewall_status": "Active"},
            "compliance_readiness": {
                "satisfied_controls": [{"control_id": "A.8.20", "reason": "Có TLS 1.3", "confidence": "high"}],
                "failing_controls": [{"control_id": "A.8.24", "reason": "Bật TLS 1.0", "severity": "medium"}]
            },
            "relevant_controls": ["A.8.20", "A.8.24"],
            "raw_citations": ["ssl_protocols TLSv1 TLSv1.2 TLSv1.3;"]
        }

        with patch("services.cloud_llm_service.CloudLLMService.chat_completion") as mock_chat:
            mock_chat.return_value = {
                "status": "success",
                "model": "qwen2.5-coder:7b",
                "content": f"```json\n{json.dumps(mock_llm_response, ensure_ascii=False)}\n```"
            }

            raw_nginx = "server { listen 443 ssl; ssl_protocols TLSv1 TLSv1.2 TLSv1.3; }"
            card = EvidenceFactExtractor.extract_facts(raw_nginx, "nginx_ssl.conf", use_llm=True)

            assert card.category == "host_configuration"
            assert "NGINX" in card.summary
            assert len(card.security_strengths) >= 2
            assert len(card.security_deficiencies) >= 1
            assert "A.8.24" in card.relevant_controls
            assert "portal-web-01" in card.host_metadata.get("hostname")


class TestAuditFeedbackStore:
    """Test SQLite Feedback Store and In-Context Few-Shot Exemplars."""

    def test_feedback_store_crud_and_few_shot(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        try:
            store = AuditFeedbackStore(db_path=db_path)

            # 1. Save Golden Case
            fid1 = store.save_feedback(
                control_id="A.8.8",
                expert_verdict="missing",
                expert_rationale="Máy chủ chạy OS EOL Windows 2008 và thiếu Hotfixes, bắt buộc đánh giá Missing theo chuẩn ISO.",
                input_fact_summary="Host DIM (10.140.0.103): Windows 2008 EOL + SQL 2005 EOL",
                initial_ai_verdict="partial",
                standard="iso27001",
                auditor_username="auditor_lead",
            )
            assert fid1.startswith("fb-")

            fid2 = store.save_feedback(
                control_id="A.5.1",
                expert_verdict="satisfied",
                expert_rationale="Chính sách ATTT đã ban hành v2.1 có phê duyệt của Ban Giám đốc.",
                input_fact_summary="Quy chế ATTT v2.1 ngày 15/08/2025",
                standard="iso27001",
            )
            assert fid2.startswith("fb-")

            # 2. Query feedback by control
            feedbacks_a88 = store.get_feedback_by_control("A.8.8", standard="iso27001")
            assert len(feedbacks_a88) == 1
            assert feedbacks_a88[0]["expert_verdict"] == "missing"
            assert "Windows 2008" in feedbacks_a88[0]["expert_rationale"]

            # 3. Format Few-Shot Prompt for Agent 2
            few_shot_prompt = store.format_few_shot_prompt(["A.8.8", "A.5.1"], standard="iso27001")
            assert "HỌC TĂNG CƯỜNG TỪ LỊCH SỬ KIỂM TOÁN VIÊN" in few_shot_prompt
            assert "A.8.8" in few_shot_prompt
            assert "MISSING" in few_shot_prompt
            assert "A.5.1" in few_shot_prompt

            # 4. List all
            all_fb = store.get_all_feedback()
            assert len(all_fb) == 2

            # 5. Delete feedback
            deleted = store.delete_feedback(fid1)
            assert deleted is True
            assert len(store.get_feedback_by_control("A.8.8")) == 0

        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


class TestMultiAgentIntegration:
    """Test end-to-end integration of Fact Cards & Feedback into Chunk Prompts."""

    def test_build_chunk_prompt_with_fact_cards_and_exemplars(self):
        cat_controls = [
            {"id": "A.8.8", "label": "Quản lý lỗ hổng kỹ thuật", "weight": "critical"},
            {"id": "A.8.9", "label": "Quản lý cấu hình", "weight": "high"},
        ]
        implemented = []

        fact_card = SecurityFactCard(
            filename="10.140.0.103.txt",
            category="host_configuration",
            summary="Log cấu hình máy chủ DIM phát hiện rủi ro EOL",
            host_metadata={"hostname": "DIM", "os_name": "Windows Server 2008", "is_eol": True},
            security_strengths=["Đã bật Firewall"],
            security_deficiencies=[{"name": "SQL Server 2005 EOL", "risk_level": "critical", "evidence_snippet": "SQL Server 2005 installed"}],
        )
        fact_cards_text = EvidenceFactExtractor.format_for_auditor([fact_card])
        feedback_text = "• Control A.8.8: Kết luận chuẩn: MISSING (Do OS và Database EOL)"

        prompt = build_chunk_prompt(
            cat_name="A.8 Công nghệ",
            cat_controls=cat_controls,
            implemented=implemented,
            pct=0.0,
            sc=0,
            mx=2,
            sys_summary="Hệ thống máy chủ nội bộ",
            std_name="ISO 27001:2022",
            fact_cards_text=fact_cards_text,
            feedback_exemplars_text=feedback_text,
        )

        assert "SECURITY FACT CARDS" in prompt
        assert "DIM" in prompt
        assert "Windows Server 2008" in prompt
        assert "SQL Server 2005 EOL" in prompt
        assert "MISSING" in prompt
        assert "A.8.8" in prompt

    def test_parse_evidence_file_includes_fact_card(self):
        sample_log = b"""
        Host Name:                 SRV-PROD-01
        OS Name:                   Microsoft Windows Server 2012 R2
        Product ID:                12345
        Hotfix(s):                 N/A
        """
        res = parse_evidence_file(sample_log, "srv_prod_01.txt")
        assert res["status"] == "success"
        assert "fact_card" in res
        assert "fact_summary" in res
        assert res["fact_card"]["host_metadata"]["hostname"] == "SRV-PROD-01"
        assert res["fact_card"]["host_metadata"]["is_eol"] is True
        assert len(res["fact_card"]["security_deficiencies"]) >= 1
