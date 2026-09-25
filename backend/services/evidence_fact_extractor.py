"""Evidence Fact Extractor (Agent 1) — Dynamic LLM-Powered Security Fact Extraction Engine.

Transforms ANY unstructured raw evidence (PowerShell/Bash logs, system configs, firewall rules,
VA/pentest reports, administrative policies, audit minutes) into structured SecurityFactCards
for Agent 2 (Compliance Auditor).
Uses Qwen2.5-Coder (or Gemma 4 / Local LLM) for deep semantic comprehension with a robust
deterministic fallback engine.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Standard EOL reference patterns for deterministic validation
EOL_OS_PATTERNS = [
    (r"Windows\s+Server\s+2008(?:\s+R2)?", "Windows Server 2008 (End-of-Life: Jan 2020)"),
    (r"Windows\s+Server\s+2003(?:\s+R2)?", "Windows Server 2003 (End-of-Life: Jul 2015)"),
    (r"Windows\s+Server\s+2012(?:\s+R2)?", "Windows Server 2012 (End-of-Life: Oct 2023)"),
    (r"Windows\s+XP", "Windows XP (End-of-Life: Apr 2014)"),
    (r"Windows\s+7", "Windows 7 (End-of-Life: Jan 2020)"),
    (r"CentOS\s+(?:release\s+)?(?:6|7|8(?!\s+Stream))", "CentOS Linux EOL"),
    (r"Ubuntu\s+(?:14\.04|16\.04|18\.04)", "Ubuntu LTS End-of-Standard-Support"),
    (r"Red\s+Hat\s+Enterprise\s+Linux(?:\s+Server)?\s+release\s+(?:5|6|7\.[0-8])", "RHEL Legacy Version"),
]

EOL_SOFTWARE_PATTERNS = [
    (r"SQL\s+Server\s+(?:2000|2005|2008|2008\s+R2|2012)", "Microsoft SQL Server EOL", "critical", ["A.8.8", "SV.07", "SV.08"]),
    (r"Office\s+2003", "Microsoft Office 2003 EOL", "high", ["A.8.8"]),
    (r"Office\s+2007", "Microsoft Office 2007 EOL", "high", ["A.8.8"]),
    (r"WinPcap\s+4\.", "WinPcap (Unmaintained, replaced by Npcap)", "medium", ["A.8.8"]),
    (r"Apache/(?:1\.|2\.[0-3]\.)", "Apache HTTP Server Outdated", "high", ["A.8.8", "APP.01"]),
    (r"PHP/(?:5\.|7\.[0-3])", "PHP EOL Runtime", "critical", ["A.8.8", "APP.01"]),
    (r"OpenSSL\s+(?:0\.9|1\.0\.[0-1])", "OpenSSL Outdated/Vulnerable", "critical", ["A.8.24", "APP.02"]),
    (r"Tomcat/(?:6|7|8\.[0-4])", "Apache Tomcat Outdated", "high", ["A.8.8"]),
]


class SecurityFactCard:
    """Standardized Structured Security Fact Card produced by Agent 1."""

    def __init__(
        self,
        filename: str,
        category: str = "general_evidence",
        summary: str = "",
        host_metadata: Optional[Dict[str, Any]] = None,
        security_strengths: Optional[List[str]] = None,
        security_deficiencies: Optional[List[Dict[str, Any]]] = None,
        software_inventory: Optional[List[Dict[str, Any]]] = None,
        governance_facts: Optional[Dict[str, Any]] = None,
        network_and_access: Optional[Dict[str, Any]] = None,
        compliance_readiness: Optional[Dict[str, Any]] = None,
        relevant_controls: Optional[List[str]] = None,
        raw_citations: Optional[List[str]] = None,
    ):
        self.filename = filename
        self.category = category
        self.summary = summary
        self.host_metadata = host_metadata or {}
        self.security_strengths = security_strengths or []
        self.security_deficiencies = security_deficiencies or []
        self.software_inventory = software_inventory or []
        self.governance_facts = governance_facts or {}
        self.network_and_access = network_and_access or {}
        self.compliance_readiness = compliance_readiness or {"satisfied_controls": [], "failing_controls": []}
        self.relevant_controls = relevant_controls or []
        self.raw_citations = raw_citations or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "category": self.category,
            "summary": self.summary,
            "host_metadata": self.host_metadata,
            "security_strengths": self.security_strengths,
            "security_deficiencies": self.security_deficiencies,
            "software_inventory": self.software_inventory,
            "governance_facts": self.governance_facts,
            "network_and_access": self.network_and_access,
            "compliance_readiness": self.compliance_readiness,
            "relevant_controls": self.relevant_controls,
            "raw_citations": self.raw_citations,
        }

    def to_compact_summary(self) -> str:
        """Format into an informative, token-efficient summary for Agent 2 (Auditor)."""
        lines = [f"📄 File: {self.filename} ({self.category})"]
        if self.summary:
            lines.append(f"  📝 Tóm tắt: {self.summary[:180]}")

        if self.host_metadata:
            hm = self.host_metadata
            os_info = hm.get("os_name", "")
            eol_tag = " ⚠️[EOL OS]" if hm.get("is_eol") else ""
            ip_str = ", ".join(hm.get("ip_addresses", []))
            lines.append(f"  • Máy chủ: {hm.get('hostname', 'N/A')} | IP: {ip_str or 'N/A'} | HĐH: {os_info}{eol_tag}")

        if self.security_strengths:
            lines.append("  ✅ Điểm mạnh / Minh chứng đạt (Căn cứ tích xanh):")
            for s in self.security_strengths[:15]:
                lines.append(f"    + {s[:160]}")

        if self.security_deficiencies:
            lines.append("  ⚠️ Rủi ro / Điểm thiếu sót (Căn cứ đánh giá thiếu/khắc phục):")
            for d in self.security_deficiencies[:25]:
                sev = d.get("risk_level", "medium").upper()
                name = d.get("name", "")
                snippet = d.get("evidence_snippet", "")
                lines.append(f"    - [{sev}] {name}: {snippet[:160]}")

        if self.software_inventory:
            inv_names = [f"{it.get('name', '')} {it.get('version', '')}".strip() for it in self.software_inventory[:12]]
            lines.append(f"  📦 Phần mềm & Dịch vụ ({len(self.software_inventory)} mục): {', '.join(inv_names)}")

        if self.governance_facts:
            gf = self.governance_facts
            title = gf.get('title') or gf.get('document_title') or 'Văn bản quy chế'
            lines.append(f"  📋 Chính sách/Quy chế: {title} (Ban hành: {gf.get('issue_date', 'N/A')}, Duyệt: {gf.get('approved_by', 'N/A')})")

        sat = self.compliance_readiness.get("satisfied_controls", [])
        fail = self.compliance_readiness.get("failing_controls", [])
        if sat or fail:
            sat_ids = [c.get("control_id") if isinstance(c, dict) else str(c) for c in sat[:25]]
            fail_ids = [c.get("control_id") if isinstance(c, dict) else str(c) for c in fail[:25]]
            lines.append(f"  🎯 Đánh giá sơ bộ: [Đạt/Tích xanh]: {', '.join(sat_ids) or 'Chưa rõ'} | [Có rủi ro]: {', '.join(fail_ids) or 'Không'}")

        return "\n".join(lines)


class EvidenceFactExtractor:
    """Agent 1 — Autonomous Dynamic Security Fact Extraction Engine.
    
    Reads any uploaded evidence files and dynamically synthesizes actionable compliance facts.
    """

    @classmethod
    def extract_facts(
        cls,
        raw_text: str,
        filename: str,
        use_llm: bool = True,
        preferred_model: Optional[str] = None
    ) -> SecurityFactCard:
        """Extract structured security facts using LLM (Qwen2.5-Coder / Gemma 4) with deterministic fallback."""
        if not raw_text or not raw_text.strip():
            return SecurityFactCard(filename=filename, category="empty")

        clean_text = raw_text.strip()

        # 1. Try Dynamic AI Agent Extraction via Local/Cloud LLM
        if use_llm:
            try:
                card = cls._extract_facts_via_llm(clean_text, filename, preferred_model)
                if card is not None:
                    return card
            except Exception as e:
                logger.debug(f"[Agent 1 FactExtractor] LLM dynamic extraction fallback due to: {e}")

        # 2. High-precision Deterministic & Heuristic Fallback
        return cls._extract_facts_deterministic(clean_text, filename)

    @classmethod
    def _extract_facts_via_llm(
        cls,
        raw_text: str,
        filename: str,
        preferred_model: Optional[str] = None
    ) -> Optional[SecurityFactCard]:
        """Invoke Agent 1 (Qwen2.5-Coder:7b / Gemma 4 / Local LLM) to dynamically structure the evidence."""
        from services.cloud_llm_service import CloudLLMService

        # Truncate to reasonable context if gigantic log (> 16000 chars)
        text_snippet = raw_text[:16000] if len(raw_text) > 16000 else raw_text

        system_prompt = (
            "Bạn là CyberAI Evidence Extractor (Agent 1 - Kỹ sư Phân tích Bằng chứng & Tuân thủ ATTT).\n"
            "Nhiệm vụ: Phân tích sâu tệp tài liệu bằng chứng do người dùng upload (log máy chủ, PowerShell/Bash, "
            "cấu hình mạng, firewall, báo cáo quét pentest/VA, chính sách/quy chế ATTT, biên bản kiểm toán...).\n"
            "Mục tiêu: Đưa ra thông tin chính xác giúp Agent 2 (Auditor) biết bằng chứng này CÓ ĐỦ ĐIỀU KIỆN TÍCH XANH "
            "(đạt tiêu chuẩn) hay CÓ RỦI RO / THIẾU SÓT (chưa đạt tiêu chuẩn).\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "- Trả về DUY NHẤT 1 khối JSON hợp lệ theo đúng cấu trúc bên dưới, không kèm giải thích bên ngoài:\n"
            "{\n"
            '  "summary": "Tóm tắt ngắn gọn nội dung tài liệu và phạm vi kỹ thuật",\n'
            '  "category": "host_configuration | vulnerability_assessment | policy_governance | network_firewall | general_evidence",\n'
            '  "host_metadata": {\n'
            '    "hostname": "...",\n'
            '    "os_name": "...",\n'
            '    "os_version": "...",\n'
            '    "is_eol": false,\n'
            '    "ip_addresses": ["..."],\n'
            '    "domain": "..."\n'
            "  },\n"
            '  "security_strengths": [\n'
            '    "Điểm mạnh hoặc minh chứng đã làm tốt chứng minh việc tuân thủ để tích xanh (ví dụ: Firewall đang bật, đã áp dụng MFA, có chính sách ban hành hợp lệ...)"\n'
            "  ],\n"
            '  "security_deficiencies": [\n'
            "    {\n"
            '      "type": "unsupported_legacy_os | unsupported_legacy_software | missing_security_patches | vulnerability_scan_findings | insecure_protocol | other",\n'
            '      "name": "Tên rủi ro/lỗ hổng",\n'
            '      "risk_level": "critical | high | medium | low",\n'
            '      "evidence_snippet": "Trích dẫn nguyên văn dòng/đoạn trong tài liệu",\n'
            '      "control_ids": ["A.8.8", "SV.07"]\n'
            "    }\n"
            "  ],\n"
            '  "software_inventory": [\n'
            '    {"name": "...", "version": "..."}\n'
            "  ],\n"
            '  "governance_facts": {\n'
            '    "title": "...",\n'
            '    "issue_date": "...",\n'
            '    "version": "...",\n'
            '    "approved_by": "...",\n'
            '    "scope": "..."\n'
            "  },\n"
            '  "network_and_access": {\n'
            '    "firewall_status": "...",\n'
            '    "admin_accounts": ["..."]\n'
            "  },\n"
            '  "compliance_readiness": {\n'
            '    "satisfied_controls": [\n'
            '      {"control_id": "A.5.1", "reason": "Có chính sách ban hành đầy đủ", "confidence": "high"}\n'
            "    ],\n"
            '    "failing_controls": [\n'
            '      {"control_id": "A.8.8", "reason": "Hệ thống chạy phần mềm hết hạn hỗ trợ", "severity": "critical"}\n'
            "    ]\n"
            "  },\n"
            '  "relevant_controls": ["A.8.8", "A.5.1"],\n'
            '  "raw_citations": ["Trích dẫn các dòng nguyên văn quan trọng nhất"]\n'
            "}"
        )

        user_prompt = f"TÊN TỆP BẰNG CHỨNG: {filename}\n\nNỘI DUNG TỆP BẰNG CHỨNG THỰC TẾ:\n```\n{text_snippet}\n```"

        target_model = preferred_model or os.getenv("EXTRACTOR_MODEL_NAME", "qwen2.5-coder:7b")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        res = CloudLLMService.chat_completion(
            messages=messages,
            temperature=0.1,
            local_model=target_model,
        )

        raw_content = res.get("content", "").strip()
        if not raw_content:
            return None

        # Clean markdown wrappers if any
        clean_json_str = raw_content
        if "```json" in clean_json_str:
            clean_json_str = clean_json_str.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in clean_json_str:
            clean_json_str = clean_json_str.split("```", 1)[1].split("```", 1)[0].strip()

        data = json.loads(clean_json_str)

        # Merge with deterministic signals to guarantee 0% hallucination on known EOL/CVEs
        det_card = cls._extract_facts_deterministic(raw_text, filename)

        host_meta = data.get("host_metadata") or det_card.host_metadata
        if det_card.host_metadata.get("is_eol"):
            host_meta["is_eol"] = True
            host_meta["eol_description"] = det_card.host_metadata.get("eol_description")

        deficiencies = data.get("security_deficiencies") or []
        # Ensure deterministic critical defects are included if model missed them
        for det_d in det_card.security_deficiencies:
            if not any(det_d["name"] in d.get("name", "") for d in deficiencies):
                deficiencies.append(det_d)

        strengths = data.get("security_strengths") or det_card.security_strengths
        gov_facts = data.get("governance_facts") or det_card.governance_facts
        controls = list(dict.fromkeys(data.get("relevant_controls", []) + det_card.relevant_controls))

        return SecurityFactCard(
            filename=filename,
            category=data.get("category") or det_card.category,
            summary=data.get("summary") or f"Bằng chứng '{filename}' đã được phân tích bởi Agent 1.",
            host_metadata=host_meta,
            security_strengths=strengths,
            security_deficiencies=deficiencies,
            software_inventory=data.get("software_inventory") or det_card.software_inventory,
            governance_facts=gov_facts,
            network_and_access=data.get("network_and_access") or det_card.network_and_access,
            compliance_readiness=data.get("compliance_readiness") or det_card.compliance_readiness,
            relevant_controls=controls,
            raw_citations=data.get("raw_citations") or det_card.raw_citations,
        )

    @classmethod
    def _extract_facts_deterministic(cls, text: str, filename: str) -> SecurityFactCard:
        """High-precision deterministic extraction for immediate response and fallback."""
        category = cls._detect_evidence_type(filename, text)
        host_meta = cls._extract_host_metadata(text, filename)
        deficiencies = cls._extract_deficiencies(text, host_meta)
        strengths = cls._extract_strengths(text, host_meta)
        software_inv = cls._extract_software_inventory(text)
        governance = cls._extract_governance_facts(text, filename)
        net_access = cls._extract_network_and_access(text)
        citations = cls._extract_citations(text)
        controls = cls._map_controls(filename, text, host_meta, deficiencies, governance, strengths)
        compliance_readiness = cls._build_compliance_readiness(strengths, deficiencies, governance)

        summary = f"Bằng chứng dạng {category} ghi nhận "
        if host_meta.get("hostname"):
            summary += f"máy chủ {host_meta.get('hostname')} "
        if deficiencies:
            summary += f"với {len(deficiencies)} rủi ro kỹ thuật cần khắc phục."
        elif strengths:
            summary += f"với các biện pháp kiểm soát đã triển khai thực tế."
        else:
            summary += f"phục vụ đối soát các biện pháp an toàn thông tin."

        return SecurityFactCard(
            filename=filename,
            category=category,
            summary=summary,
            host_metadata=host_meta,
            security_strengths=strengths,
            security_deficiencies=deficiencies,
            software_inventory=software_inv,
            governance_facts=governance,
            network_and_access=net_access,
            compliance_readiness=compliance_readiness,
            relevant_controls=controls,
            raw_citations=citations,
        )

    @classmethod
    def _detect_evidence_type(cls, filename: str, text: str) -> str:
        fname = filename.lower()
        if any(w in fname for w in ["chinh_sach", "policy", "quy_che", "quy_dinh", "so_tay", "bcp", "drp"]):
            return "policy_governance"
        if any(w in fname for w in ["va", "pentest", "vulnerability", "nessus", "openvas", "report"]):
            return "vulnerability_assessment"
        if any(w in fname for w in ["firewall", "netsh", "iptables", "switch", "router", "acl"]):
            return "network_firewall"
        if any(w in fname for w in ["systeminfo", "server", "host", "config", "powershell", "log", ".txt"]):
            return "host_configuration"
        if "Host Name:" in text or "OS Name:" in text or "PS C:\\" in text:
            return "host_configuration"
        if "CVE-" in text or "Lỗ hổng" in text or "CVSS" in text:
            return "vulnerability_assessment"
        return "general_evidence"

    @classmethod
    def _extract_host_metadata(cls, text: str, filename: str = "") -> Dict[str, Any]:
        meta: Dict[str, Any] = {}

        # Hostname
        m_host = re.search(r"Host\s+Name:\s*([^\r\n]+)", text, re.IGNORECASE)
        if m_host:
            meta["hostname"] = m_host.group(1).strip()

        # OS Name
        m_os = re.search(r"OS\s+Name:\s*([^\r\n]+)", text, re.IGNORECASE)
        if m_os:
            os_name = m_os.group(1).strip().replace("Microsoftr", "Microsoft").replace("Serverr", "Server")
            meta["os_name"] = os_name

            for pattern, eol_desc in EOL_OS_PATTERNS:
                if re.search(pattern, os_name, re.IGNORECASE):
                    meta["is_eol"] = True
                    meta["eol_description"] = eol_desc
                    break

        # OS Version
        m_ver = re.search(r"OS\s+Version:\s*([^\r\n]+)", text, re.IGNORECASE)
        if m_ver:
            meta["os_version"] = m_ver.group(1).strip()

        # Domain
        m_dom = re.search(r"Domain:\s*([^\r\n]+)", text, re.IGNORECASE)
        if m_dom:
            meta["domain"] = m_dom.group(1).strip()

        # IP Addresses
        ips = re.findall(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b", text)
        fn_ips = re.findall(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b", filename)
        all_ips = fn_ips + [ip for ip in ips if ip not in fn_ips]
        if all_ips:
            meta["ip_addresses"] = list(dict.fromkeys(all_ips))

        # Hotfixes count & list
        kbs = re.findall(r"\bKB\d{6,8}\b", text, re.IGNORECASE)
        if kbs:
            meta["hotfixes"] = list(dict.fromkeys(kbs))
            meta["hotfix_count"] = len(meta["hotfixes"])
        elif re.search(r"Hotfix\(s\):\s*N/A", text, re.IGNORECASE):
            meta["hotfixes"] = []
            meta["hotfix_count"] = 0

        # Antivirus detection
        lower_txt = text.lower()
        if "trend micro" in lower_txt or "apex one" in lower_txt:
            meta["antivirus"] = "Trend Micro Apex One"
        elif "windows defender" in lower_txt or "windefend" in lower_txt:
            meta["antivirus"] = "Windows Defender"
        elif "crowdstrike" in lower_txt or "falcon" in lower_txt:
            meta["antivirus"] = "CrowdStrike Falcon"
        elif "wazuh" in lower_txt:
            meta["antivirus"] = "Wazuh EDR"
        elif "sentinelone" in lower_txt:
            meta["antivirus"] = "SentinelOne"

        # Listening / Open Ports
        ports = re.findall(r":(\d{2,5})\b", text)
        well_known = {"21", "22", "23", "25", "80", "110", "135", "139", "443", "445", "1433", "1521", "3306", "3389", "5432", "8080", "8443"}
        detected_ports = [p for p in set(ports) if p in well_known]
        if detected_ports:
            meta["listening_ports"] = sorted(detected_ports, key=int)

        return meta

    @classmethod
    def _extract_strengths(cls, text: str, host_meta: Dict[str, Any]) -> List[str]:
        strengths: List[str] = []
        lower_txt = text.lower()

        if "firewall set rule" in lower_txt or "advfirewall" in lower_txt:
            if "enable=yes" in lower_txt or "state on" in lower_txt:
                strengths.append("Tường lửa máy chủ (Host Firewall) đã được kích hoạt và cấu hình quy tắc.")

        if "mfa" in lower_txt or "xác thực đa yếu tố" in lower_txt or "2fa" in lower_txt:
            strengths.append("Có bằng chứng áp dụng cơ chế xác thực đa yếu tố (MFA) cho tài khoản truy cập.")

        has_backup_fail = bool(re.search(r"\b(?:\[FATAL\]|FATAL|disk full|corrupted|crc error|job aborted|backup failed|dump failed|could not write output)\b", lower_txt))
        if ("sao lưu" in lower_txt or "backup" in lower_txt) and not has_backup_fail:
            strengths.append("Có quy định hoặc lịch trình thực hiện sao lưu dữ liệu hệ thống định kỳ.")

        if "người phê duyệt" in lower_txt or "approved by" in lower_txt or "ban hành" in lower_txt:
            strengths.append("Tài liệu chính sách/quy chế đã được ký duyệt và ban hành chính thức.")

        if "https://" in lower_txt or "tls 1.2" in lower_txt or "tls 1.3" in lower_txt:
            strengths.append("Áp dụng giao thức truyền thông an toàn mã hóa SSL/TLS.")

        if host_meta.get("antivirus") or re.search(r"\b(?:antivirus|endpoint protection|chống mã độc|managed/protected|pattern virus|bảo vệ mã độc)\b", lower_txt):
            av_name = host_meta.get('antivirus') or "Antivirus / Endpoint Protection"
            strengths.append(f"Hệ thống máy chủ đã trang bị giải pháp bảo vệ mã độc: {av_name}.")

        return strengths

    @classmethod
    def _extract_deficiencies(cls, text: str, host_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        deficiencies: List[Dict[str, Any]] = []

        # 0. Backup failure & corruption
        if re.search(r"\b(?:\[FATAL\]|FATAL|disk full|corrupted|crc error|job aborted|backup failed|dump failed|could not write output)\b", text, re.IGNORECASE) and re.search(r"\b(?:backup|sao\s*lưu|pg_dump|mysqldump|archive)\b", text, re.IGNORECASE):
            deficiencies.append({
                "type": "backup_failure",
                "name": "Lỗi sao lưu nghiêm trọng (Hỏng tệp sao lưu / Tràn đĩa / Tiến trình bị hủy)",
                "risk_level": "critical",
                "evidence_snippet": "Ghi nhận lỗi nghiêm trọng trong nhật ký sao lưu (FATAL / Disk full / Corrupted / Aborted)",
                "control_ids": ["A.8.13", "DAT.01"],
            })

        # 1. OS EOL
        if host_meta.get("is_eol"):
            deficiencies.append({
                "type": "unsupported_legacy_os",
                "name": f"Hệ điều hành hết hạn hỗ trợ ({host_meta.get('os_name')})",
                "risk_level": "critical",
                "evidence_snippet": host_meta.get("eol_description", "End of Life"),
                "control_ids": ["A.8.8", "SV.07", "SV.08"],
            })

        # 2. Hotfix missing / N/A
        if re.search(r"Hotfix\(s\):\s*N/A", text, re.IGNORECASE) or re.search(r"Get-Hotfix\s*:\s*The term 'Get-Hotfix' is not recognized", text, re.IGNORECASE):
            deficiencies.append({
                "type": "missing_security_patches",
                "name": "Hệ thống chưa áp dụng bản vá bảo mật (Hotfixes: N/A)",
                "risk_level": "critical",
                "evidence_snippet": "Hotfix(s): N/A / Không thể xác minh lịch sử cập nhật",
                "control_ids": ["A.8.8", "SV.07"],
            })

        # 3. EOL Software installed
        for pattern, desc, sev, ctrl_ids in EOL_SOFTWARE_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 60)
                snippet = text[start:end].replace("\n", " ").strip()
                deficiencies.append({
                    "type": "unsupported_legacy_software",
                    "name": f"Phần mềm hết hạn hỗ trợ ({desc})",
                    "risk_level": sev,
                    "evidence_snippet": snippet[:100],
                    "control_ids": ctrl_ids,
                })

        # 4. CVEs
        cves = re.findall(r"\bCVE-\d{4}-\d{4,7}\b", text)
        if cves:
            unique_cves = list(dict.fromkeys(cves))
            is_critical = len(unique_cves) >= 3 or bool(re.search(r"\b(?:critical|cvss\s*(?:10(?:\.0)?|9\.[0-9]))\b", text, re.IGNORECASE))
            deficiencies.append({
                "type": "vulnerability_scan_findings",
                "name": f"Phát hiện {len(unique_cves)} mã lỗ hổng CVE trong báo cáo quét",
                "risk_level": "critical" if is_critical else "high",
                "evidence_snippet": f"CVEs: {', '.join(unique_cves[:6])}",
                "control_ids": ["A.8.8", "MNG.05"],
            })

        # 5. Insecure protocols & Open weak ports
        insecure_m = re.search(r"\b(?:telnet|ftp|smbv1|http://|ssl\s+2\.0|ssl\s+3\.0)\b", text, re.IGNORECASE)
        if insecure_m:
            lines_with_m = [l.lower() for l in text.splitlines() if insecure_m.group(0).lower() in l.lower()]
            is_disabled = any(
                any(k in l for k in ("disable", "stop", "deny", "drop", "block", "remove", "cấm", "vô hiệu hóa", "tắt"))
                for l in lines_with_m
            )
            if not is_disabled:
                deficiencies.append({
                    "type": "insecure_protocol",
                    "name": "Sử dụng giao thức truyền thông không mã hóa hoặc lỗi thời",
                    "risk_level": "high",
                    "evidence_snippet": "Phát hiện giao thức không an toàn trong cấu hình mạng",
                    "control_ids": ["A.8.20", "A.8.24", "APP.02", "NW.01", "NW.02", "SV.01"],
                })

        # 6. SWEET32 / CVE-2016-2183 / Weak 3DES ciphers
        if re.search(r"\b(?:cve-2016-2183|sweet32|3des|triple-des|des-cbc3)\b", text, re.IGNORECASE):
            deficiencies.append({
                "type": "weak_cryptography",
                "name": "Lỗ hổng SWEET32 (CVE-2016-2183) trên thuật toán 3DES 64-bit",
                "risk_level": "high",
                "evidence_snippet": "Giao thức SSL/TLS cho phép sử dụng mã hóa 3DES khối 64-bit dễ bị tấn công birthday",
                "control_ids": ["A.8.24", "APP.02", "SV.08"],
            })

        # 7. Missing specific critical hotfix KB5070247
        if re.search(r"\bKB5070247\b", text, re.IGNORECASE) and re.search(r"\b(?:missing|thiếu|chưa cài|failed)\b", text, re.IGNORECASE):
            deficiencies.append({
                "type": "missing_security_patches",
                "name": "Thiếu bản vá bảo mật khẩn cấp Hotfix KB5070247",
                "risk_level": "critical",
                "evidence_snippet": "Bản vá KB5070247 chưa được cài đặt trên hệ điều hành máy chủ",
                "control_ids": ["A.8.8", "SV.07"],
            })

        # 8. RDP without NLA
        if re.search(r"\b(?:user authentication.*optional|nla disabled|securitylayer.*0)\b", text, re.IGNORECASE):
            deficiencies.append({
                "type": "insecure_remote_access",
                "name": "Dịch vụ Remote Desktop (RDP) không bắt buộc xác thực cấp độ mạng (NLA)",
                "risk_level": "high",
                "evidence_snippet": "RDP cấu hình cho phép kết nối không cần NLA",
                "control_ids": ["A.8.2", "A.8.5", "SV.01", "SV.06"],
            })

        return deficiencies

    @classmethod
    def _extract_software_inventory(cls, text: str) -> List[Dict[str, Any]]:
        inventory: List[Dict[str, Any]] = []
        lines = text.splitlines()
        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("DisplayName") or line_str.startswith("-----------"):
                continue
            if any(key in line_str.lower() for key in ["sql server", "visual c++", "winpcap", "apache", "nginx", "mysql", "php", "office"]):
                parts = re.split(r"\s{2,}", line_str)
                name = parts[0] if parts else line_str
                ver = parts[1] if len(parts) > 1 else ""
                inventory.append({"name": name[:60], "version": ver[:30]})
        return inventory[:20]

    @classmethod
    def _extract_governance_facts(cls, text: str, filename: str) -> Dict[str, Any]:
        fname_lower = (filename or "").lower()
        is_raw_log = any(fname_lower.endswith(ext) for ext in [".txt", ".log", ".csv", ".json", ".xml"])
        has_policy_filename = any(w in fname_lower for w in ["chinh_sach", "policy_attt", "quy_che", "quy_dinh", "so_tay", "bcp", "drp", "bien_ban", "quyet_dinh"])
        
        # Raw log files should not be treated as governance policies unless specifically named as such
        if is_raw_log and not has_policy_filename:
            return {}

        text_preview = (text or "")[:2000].lower()
        is_gov_doc = has_policy_filename or any(w in text_preview for w in ["quy chế", "quy định", "chính sách an toàn", "người phê duyệt", "ban hành"])
        if not is_gov_doc:
            return {}

        facts: Dict[str, Any] = {}
        m_date = re.search(r"\b(?:ngày\s*(?:ban\s*hành|ký)?[:\s]*)(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})\b", text, re.IGNORECASE)
        if m_date:
            facts["issue_date"] = m_date.group(1)

        m_ver = re.search(r"\b(?:phiên\s*bản|version|v)\s*[:\.]?\s*(\d+\.\d+(?:\.\d+)?)\b", text, re.IGNORECASE)
        if m_ver:
            facts["version"] = m_ver.group(1)

        m_app = re.search(r"(?:người\s*phê\s*duyệt|người\s*ký|approved\s*by)\s*[:\.]?\s*([^\r\n,]+)", text, re.IGNORECASE)
        if m_app:
            facts["approved_by"] = m_app.group(1).strip()

        if "toàn bộ cán bộ" in text.lower() or "tất cả nhân viên" in text.lower() or "tổ chức" in text.lower():
            facts["scope"] = "Toàn bộ tổ chức"

        if facts or "policy" in filename.lower() or "chinh_sach" in filename.lower():
            facts["title"] = filename.replace(".docx", "").replace(".pdf", "").replace("_", " ")

        return facts

    @classmethod
    def _extract_network_and_access(cls, text: str) -> Dict[str, Any]:
        net: Dict[str, Any] = {}
        if "netsh advfirewall" in text.lower() or "firewall" in text.lower():
            if "enable=yes" in text.lower() or "state on" in text.lower():
                net["firewall_status"] = "Đã bật (Active)"
            elif "enable=no" in text.lower() or "state off" in text.lower():
                net["firewall_status"] = "Đã tắt (Disabled - Nguy hiểm)"

        admins = re.findall(r"\b(?:Administrator|root|admin_[a-zA-Z0-9]+)\b", text, re.IGNORECASE)
        if admins:
            net["admin_accounts"] = list(dict.fromkeys(admins))

        return net

    @classmethod
    def _extract_citations(cls, text: str) -> List[str]:
        citations = []
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for line in lines:
            if any(k in line.lower() for k in ["windows server 2008", "sql server 2005", "hotfix(s): n/a", "cve-", "advfirewall"]):
                citations.append(line[:140])
                if len(citations) >= 5:
                    break
        return citations

    @classmethod
    def _build_compliance_readiness(
        cls,
        strengths: List[str],
        deficiencies: List[Dict[str, Any]],
        governance: Dict[str, Any]
    ) -> Dict[str, Any]:
        satisfied = []
        failing = []

        if governance.get("approved_by") or governance.get("title"):
            satisfied.append({
                "control_id": "A.5.1",
                "reason": f"Có chính sách ATTT ({governance.get('title', 'Quy chế')}) ban hành hợp lệ.",
                "confidence": "high"
            })
            satisfied.append({
                "control_id": "A.5.2",
                "reason": "Quy chế quy định rõ vai trò và trách nhiệm ATTT.",
                "confidence": "high"
            })

        for s in strengths:
            if "tường lửa" in s.lower():
                satisfied.append({"control_id": "A.8.20", "reason": "Host Firewall kích hoạt.", "confidence": "high"})
                satisfied.append({"control_id": "NW.02", "reason": "Tường lửa bảo vệ vùng biên kích hoạt.", "confidence": "high"})
            if "mfa" in s.lower():
                satisfied.append({"control_id": "A.8.5", "reason": "Áp dụng xác thực đa yếu tố.", "confidence": "high"})
            if "sao lưu" in s.lower():
                satisfied.append({"control_id": "A.8.13", "reason": "Có chính sách sao lưu định kỳ.", "confidence": "high"})
                satisfied.append({"control_id": "DAT.01", "reason": "Có chính sách sao lưu định kỳ.", "confidence": "high"})
            if "mã độc" in s.lower() or "antivirus" in s.lower():
                satisfied.append({"control_id": "A.8.7", "reason": "Áp dụng giải pháp chống mã độc.", "confidence": "high"})
                satisfied.append({"control_id": "SV.02", "reason": "Áp dụng giải pháp chống mã độc.", "confidence": "high"})

        for d in deficiencies:
            for cid in d.get("control_ids", []):
                failing.append({
                    "control_id": cid,
                    "reason": d.get("name"),
                    "severity": d.get("risk_level", "medium")
                })

        return {"satisfied_controls": satisfied, "failing_controls": failing}

    @classmethod
    def _map_controls(
        cls,
        filename: str,
        text: str,
        host_meta: Dict[str, Any],
        deficiencies: List[Dict[str, Any]],
        governance: Dict[str, Any],
        strengths: List[str]
    ) -> List[str]:
        controls = set()

        for d in deficiencies:
            for c in d.get("control_ids", []):
                controls.add(c)

        if governance and governance.get("title") and any(k in str(governance.get("title")).lower() for k in ["policy", "chinh_sach", "quy_che", "quy_dinh"]):
            controls.add("A.5.1")
            controls.add("A.5.2")

        if host_meta.get("os_name") or host_meta.get("hostname"):
            controls.add("A.5.9")
            controls.add("A.8.8")
            controls.add("A.8.9")
            controls.add("SV.07")
            controls.add("SV.08")

        for s in strengths:
            if "tường lửa" in s.lower():
                controls.add("A.8.20")
                controls.add("NW.02")
            if "mfa" in s.lower():
                controls.add("A.8.5")
            if "sao lưu" in s.lower():
                controls.add("A.8.13")
                controls.add("DAT.01")
            if "mã độc" in s.lower() or "antivirus" in s.lower():
                controls.add("A.8.7")
                controls.add("SV.02")

        from services.evidence_mapper import map_evidence_to_controls
        mapped = map_evidence_to_controls(filename, text[:32000])
        for cid in mapped.keys():
            controls.add(cid)

        return sorted(list(controls))

    @classmethod
    def cross_verify_controls(
        cls,
        self_attested_controls: List[str],
        fact_cards: List[SecurityFactCard],
        standard: str = "iso27001",
    ) -> Dict[str, Any]:
        """Cross-verify self-attested controls against empirical evidence across all files.

        Rule 1 (Contradiction): User marked control as implemented, but evidence demonstrates a critical/high defect.
        Rule 2 (Unverified Attestation): User marked control as implemented, but NO evidence across all files supports it.
        Rule 3 (Verified Satisfied): User marked control as implemented, and positive evidence confirms it.
        """
        attested_set = set(self_attested_controls or [])
        verified_satisfied = []
        contradiction_gaps = []
        unverified_oversights = []

        evidence_positive_controls = set()
        evidence_failing_map: Dict[str, List[Tuple[Dict[str, Any], str]]] = {}

        for fc in fact_cards:
            fname = fc.filename
            for sat in fc.compliance_readiness.get("satisfied_controls", []):
                cid = sat.get("control_id") if isinstance(sat, dict) else str(sat)
                if cid:
                    evidence_positive_controls.add(cid)
            if fc.security_strengths:
                for cid in fc.relevant_controls:
                    evidence_positive_controls.add(cid)

            for d in fc.security_deficiencies:
                for cid in d.get("control_ids", []):
                    if cid not in evidence_failing_map:
                        evidence_failing_map[cid] = []
                    evidence_failing_map[cid].append((d, fname))

        for cid in attested_set:
            if cid in evidence_failing_map:
                defects = evidence_failing_map[cid]
                d, fname = defects[0]
                contradiction_gaps.append({
                    "control_id": cid,
                    "defect_name": d.get("name", "Lỗ hổng bảo mật"),
                    "risk_level": d.get("risk_level", "critical"),
                    "filename": fname,
                    "evidence_snippet": d.get("evidence_snippet", ""),
                    "citation": f"[🏷️ Nguồn: Mâu thuẫn với log {fname}]",
                    "verdict": "Không Đạt",
                    "reason": f"Tự khai báo đạt nhưng bằng chứng thực tế ({fname}) ghi nhận: {d.get('name')}",
                })
            elif cid in evidence_positive_controls:
                verified_satisfied.append({
                    "control_id": cid,
                    "status": "verified",
                    "verdict": "Đạt",
                    "citation": "[🏷️ Nguồn: Bằng chứng kỹ thuật đối soát khớp]",
                })
            else:
                unverified_oversights.append({
                    "control_id": cid,
                    "status": "unverified",
                    "verdict": "Không Đạt",
                    "citation": "[🏷️ Nguồn: Tự khai báo - Không có log đối chứng]",
                    "reason": "Người dùng tự tích chọn đạt nhưng không tìm thấy cấu hình hoặc log đối chứng trong hồ sơ bằng chứng.",
                })

        logger.info(
            f"[EvidenceAudit] Cross-verification completed: "
            f"attested={len(attested_set)}, verified={len(verified_satisfied)}, "
            f"contradictions={len(contradiction_gaps)}, unverified={len(unverified_oversights)}"
        )

        return {
            "total_attested": len(attested_set),
            "verified_count": len(verified_satisfied),
            "contradiction_count": len(contradiction_gaps),
            "unverified_count": len(unverified_oversights),
            "verified_satisfied": verified_satisfied,
            "contradiction_gaps": contradiction_gaps,
            "unverified_oversights": unverified_oversights,
        }

    @classmethod
    def format_for_auditor(
        cls,
        fact_cards: List[SecurityFactCard],
        self_attested_controls: Optional[List[str]] = None
    ) -> str:
        """Combine multiple Fact Cards into a consolidated structured context for Agent 2."""
        if not fact_cards:
            return ""

        sections = [
            "\n═════════════════════════════════════════════════════════════════════",
            "📊 SECURITY FACT CARDS (AGENT 1 TRÍCH XUẤT ĐỘNG TỪ BẰNG CHỨNG THỰC TẾ)",
            "═════════════════════════════════════════════════════════════════════"
        ]

        for fc in fact_cards:
            sections.append(fc.to_compact_summary())
            sections.append("─────────────────────────────────────────────────────────────────")

        if self_attested_controls:
            verify_res = cls.cross_verify_controls(self_attested_controls, fact_cards)
            sections.append("\n🔍 KẾT QUẢ ĐỐI SOÁT CHÉO TỰ KHAI BÁO VÀ BẰNG CHỨNG THỰC TẾ (CROSS-VERIFICATION):")

            if verify_res["contradiction_gaps"]:
                sections.append("  ⚠️ MÂU THUẪN NGHIÊM TRỌNG (Tự khai báo ĐẠT nhưng LOG THỰC TẾ CÓ LỖ HỔNG / THIẾU SÓT):")
                sections.append("     => BẮT BUỘC AGENT 2 ĐÁNH GIÁ LÀ 'KHÔNG ĐẠT', TUYỆT ĐỐI KHÔNG ĐÁNH GIÁ 'ĐẠT' HOẶC 'ĐẠT MỘT PHẦN'!")
                for cg in verify_res["contradiction_gaps"]:
                    sections.append(f"     - [{cg['control_id']}] {cg['defect_name']} ({cg['citation']}) -> {cg['reason']}")

            if verify_res["unverified_oversights"]:
                sections.append("  🏷️ CHƯA ĐƯỢC XÁC THỰC (Tự khai báo ĐẠT nhưng KHÔNG CÓ LOG/FILE MINH CHỨNG):")
                sections.append("     => BẮT BUỘC AGENT 2 ĐÁNH GIÁ LÀ 'KHÔNG ĐẠT' DO THIẾU BẰNG CHỨNG XÁC THỰC (GẮN TAG [🏷️ Nguồn: Tự khai báo - Không có log đối chứng]).")
                for uo in verify_res["unverified_oversights"][:15]:
                    sections.append(f"     - [{uo['control_id']}] {uo['citation']}")

            if verify_res["verified_satisfied"]:
                sat_ids = [s["control_id"] for s in verify_res["verified_satisfied"][:20]]
                sections.append(f"  ✅ ĐÃ XÁC THỰC KHỚP BẰNG CHỨNG ({len(verify_res['verified_satisfied'])} controls): {', '.join(sat_ids)}")

            sections.append("─────────────────────────────────────────────────────────────────")

        sections.append("LƯU Ý QUAN TRỌNG CHO AGENT 2 (LEAD AUDITOR):")
        sections.append("1. Hãy căn cứ vào 'Điểm mạnh / Minh chứng đạt' để TÍCH XANH (SATISFIED) nếu bằng chứng đầy đủ.")
        sections.append("2. Hãy căn cứ vào 'Rủi ro / Điểm thiếu sót' để TÍCH ĐỎ/VÀNG (MISSING/PARTIAL) và nêu rõ GAP.")
        sections.append("3. Đối với các control tự khai báo nhưng mâu thuẫn với log hoặc thiếu log, tuân thủ đúng quy tắc đối soát chéo ở trên.")
        sections.append("4. Luôn đính kèm trích dẫn nguyên văn (Audit Citation) để minh bạch kết quả kiểm toán.")
        return "\n".join(sections)
