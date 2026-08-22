"""Persistent Template Store — SQLite database for Assessment Templates & Industry Presets."""

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_PATH", "/data")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
DB_PATH = os.path.join(TEMPLATES_DIR, "templates.db")


# Built-in Default Templates (including real EVN TPC Assessment data)
BUILTIN_TEMPLATES = [
    {
        "id": "tpl_evn_tpc",
        "name": "Công ty TNHH MTV Nhiệt điện Thủ Đức - EVN TPC (Hạ tầng Năng lượng & TCVN 11930 / ISO 27001)",
        "standard": "tcvn11930",
        "industry": "Năng lượng & Điện lực (Critical Infrastructure)",
        "description": "Hệ thống thông tin quản lý sản xuất và văn phòng điều hành của Nhiệt điện Thủ Đức (EVN TPC / EVNGENCO 3). Đánh giá an toàn thông tin theo cấp độ bảo vệ TCVN 11930:2017 Cấp độ 3 và ISO 27001:2022, phát hiện 53 lỗ hổng bảo mật thực tế (EOL OS Windows Server 2008/2016, SQL Server cũ, SWEET32, phân vùng IT/OT).",
        "is_builtin": 1,
        "data": {
            "assessment_standard": "tcvn11930",
            "org_name": "Công ty TNHH MTV Nhiệt điện Thủ Đức (EVN TPC)",
            "org_size": "medium",
            "industry": "Năng lượng & Tiện ích công cộng (Critical Energy Infrastructure)",
            "compliance_status": "partially_compliant",
            "employees": 320,
            "servers": 9,
            "firewalls": 2,
            "vpn": True,
            "cloud_provider": "None (On-Premises Hyper-V & Physical Dell PowerEdge)",
            "antivirus": "Trend Micro Apex One + Windows Defender",
            "backup_solution": "Veeam Backup & Replication (Offline tape + NAS backup hàng tuần)",
            "siem": "Splunk Enterprise (Tập trung log từ DC01, Firewall, Switch)",
            "incidents_12m": 2,
            "it_staff": 5,
            "assessment_scope": "full",
            "scope_description": "Toàn bộ hạ tầng mạng LAN/DMZ, 09 máy chủ vật lý & ảo hóa điều hành (EOFFICE-DB, DC01, Web Portal, Mail Server, Máy chủ ứng dụng quản lý kỹ thuật) thuộc dải mạng 10.140.0.0/24, domain thuducpp.evn.vn.",
            "network_diagram": "Mô hình mạng 2 lớp: Vùng biên tiếp giáp Internet bảo vệ bởi Firewall thế hệ mới (NGFW), kết nối VPN bảo mật về EVN Tập đoàn. Vùng mạng nội bộ (10.140.0.0/24) bao gồm 9 máy chủ: DC01 (Active Directory), EOFFICE-DB (Windows Server 2016 / MS SQL Server 2016), Web Server (Windows Server 2008 EOL), Mail Gateway. Phân tách mạng IT điều hành và OT/SCADA thông qua Firewall công nghiệp.",
            "notes": "Hồ sơ đánh giá lỗ hổng thực tế Đợt 4/2026 ghi nhận 53 lỗ hổng tồn tại: 18 lỗ hổng Nghiêm trọng (CVSS 9.0-10.0 do thiếu bản vá bảo mật Hotfix KB5070247, HĐH Windows Server 2008 EOL, MS SQL Server 2016 build 13.2 cũ), 14 lỗ hổng Cao (SWEET32 CVE-2016-2183 trên giao thức SSL 3DES, RDP không bắt buộc NLA), và các cấu hình SMBv1 chưa vô hiệu hóa. Cần lập Action Plan chuyển dịch và vá lỗi theo Nghị định 85/2016/NĐ-CP và TCVN 11930:2017.",
            "implemented_controls": [
                "A.5.1", "A.5.2", "A.5.3", "A.5.4", "A.5.15", "A.5.16", "A.5.17", "A.5.18", "A.5.24", "A.5.25", "A.5.26",
                "A.6.1", "A.6.2", "A.6.3", "A.6.4", "A.6.5",
                "A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.7", "A.7.8", "A.7.9", "A.7.10",
                "A.8.1", "A.8.2", "A.8.3", "A.8.4", "A.8.7", "A.8.9", "A.8.10", "A.8.12", "A.8.13", "A.8.14", "A.8.15",
                "A.8.16", "A.8.17", "A.8.18", "A.8.19", "A.8.20", "A.8.21", "A.8.22", "A.8.23", "A.8.24", "A.8.25"
            ]
        }
    },
    {
        "id": "tpl_momo_fintech",
        "name": "Ví Điện Tử MoMo (Fintech PCI DSS v4.0 & ISO 27001:2022)",
        "standard": "pci_dss",
        "industry": "Fintech & Trung gian thanh toán",
        "description": "Mô hình ví điện tử với 30 triệu người dùng, kiến trúc Zero Trust trên AWS, phân vùng PCI Zone cô lập, AWS CloudHSM FIPS 140-2 Level 3, mã hóa toàn diện dữ liệu thẻ PAN/CVV.",
        "is_builtin": 1,
        "data": {
            "assessment_standard": "pci_dss",
            "org_name": "Công ty Cổ phần Dịch vụ Di động Trực tuyến (M_Service / MoMo)",
            "org_size": "enterprise",
            "industry": "Công nghệ Tài chính (Fintech & Payment Gateway)",
            "compliance_status": "compliant",
            "employees": 2500,
            "servers": 450,
            "firewalls": 12,
            "vpn": True,
            "cloud_provider": "AWS (Multi-AZ Multi-Region)",
            "antivirus": "CrowdStrike Falcon EDR + GuardDuty",
            "backup_solution": "AWS Backup tự động đa vùng địa lý, mã hóa KMS CMK với RPO < 5 phút, RTO < 15 phút",
            "siem": "Datadog Security Monitoring + AWS OpenSearch SIEM (24/7 SOC)",
            "incidents_12m": 0,
            "it_staff": 180,
            "assessment_scope": "full",
            "scope_description": "Toàn bộ môi trường Cardholder Data Environment (CDE), ứng dụng di động iOS/Android, hệ sinh thái thanh toán mã QR, hệ thống Core Payment và hạ tầng dữ liệu trên AWS.",
            "network_diagram": "Kiến trúc Zero Trust trên AWS. Phân vùng PCI Payment Zone cách ly hoàn toàn qua mTLS API Gateway; Quản trị truy cập đặc quyền PAM qua CyberArk. Dữ liệu thẻ lưu trữ được mã hóa phần cứng bằng AWS CloudHSM (FIPS 140-2 Level 3). CI/CD pipeline tích hợp Snyk SAST, Trivy Container scanning và HashiCorp Vault.",
            "notes": "Hệ thống ví điện tử thanh toán hàng đầu Việt Nam. Tuân thủ nghiêm ngặt PCI DSS v4.0 cấp độ cao nhất (Service Provider Level 1) và Nghị định 13/2023 về Bảo vệ Dữ liệu Cá nhân. Hệ thống AI phát hiện gian lận giao dịch theo thời gian thực (real-time sub-200ms).",
            "implemented_controls": [
                "A.5.1", "A.5.2", "A.5.3", "A.5.4", "A.5.5", "A.5.6", "A.5.7", "A.5.8", "A.5.9", "A.5.10",
                "A.5.11", "A.5.12", "A.5.13", "A.5.14", "A.5.15", "A.5.16", "A.5.17", "A.5.18", "A.5.19", "A.5.20",
                "A.5.21", "A.5.22", "A.5.23", "A.5.24", "A.5.25", "A.5.26", "A.5.27", "A.5.28", "A.5.29", "A.5.30",
                "A.6.1", "A.6.2", "A.6.3", "A.6.4", "A.6.5", "A.6.6", "A.6.7", "A.6.8",
                "A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.5", "A.7.6", "A.7.7", "A.7.8", "A.7.9", "A.7.10", "A.7.11", "A.7.12", "A.7.13", "A.7.14",
                "A.8.1", "A.8.2", "A.8.3", "A.8.4", "A.8.5", "A.8.6", "A.8.7", "A.8.8", "A.8.9", "A.8.10",
                "A.8.11", "A.8.12", "A.8.13", "A.8.14", "A.8.15", "A.8.16", "A.8.17", "A.8.18", "A.8.19", "A.8.20",
                "A.8.21", "A.8.22", "A.8.23", "A.8.24", "A.8.25", "A.8.26", "A.8.27", "A.8.28", "A.8.29", "A.8.30", "A.8.31"
            ]
        }
    },
    {
        "id": "tpl_tiki_ecommerce",
        "name": "Sàn Thương Mại Điện Tử Tiki (E-Commerce & Nghị định 13/2023)",
        "standard": "nd13",
        "industry": "Thương mại Điện tử & Logistics",
        "description": "Nền tảng thương mại điện tử quy mô lớn trên GCP GKE, hệ thống quản lý kho TikiNOW, bảo vệ dữ liệu cá nhân khách hàng PII theo Nghị định 13/2023/NĐ-CP và kiểm soát chống rò rỉ dữ liệu.",
        "is_builtin": 1,
        "data": {
            "assessment_standard": "nd13",
            "org_name": "Công ty Cổ phần Ti Ki (Tiki Corporation)",
            "org_size": "enterprise",
            "industry": "Thương mại điện tử & Chuỗi cung ứng (E-Commerce Marketplace)",
            "compliance_status": "partially_compliant",
            "employees": 1800,
            "servers": 320,
            "firewalls": 8,
            "vpn": True,
            "cloud_provider": "Google Cloud Platform (GCP)",
            "antivirus": "SentinelOne Singularity + Google Cloud Security Command Center",
            "backup_solution": "Google Cloud Storage Multi-Regional với chính sách Retention Lock 3 năm",
            "siem": "Google Chronicle SIEM tích hợp Elasticsearch log cluster",
            "incidents_12m": 1,
            "it_staff": 120,
            "assessment_scope": "full",
            "scope_description": "Hạ tầng Website tiki.vn, ứng dụng di động Tiki App, nền tảng vi dịch vụ trên Google Kubernetes Engine (GKE), hệ thống quản lý kho vận TikiNOW Smart Logistics.",
            "network_diagram": "Kiến trúc Microservices trên GCP GKE (Google Kubernetes Engine) trải rộng 3 Availability Zones. Sử dụng Cloudflare Enterprise bảo vệ DDoS/WAF Layer 7. Dữ liệu nhạy cảm của người dùng (PII: Tên, SĐT, Địa chỉ, Thói quen mua sắm) được ẩn danh hóa và phân vùng bảo vệ riêng biệt tuân thủ Nghị định 13/2023/NĐ-CP.",
            "notes": "Hệ thống phục vụ hàng triệu đơn hàng mỗi tháng. Định kỳ tổ chức diễn tập Pentest Red-Team và duy trì chương trình Bug Bounty công khai. Cần hoàn thiện cơ chế Consent Management và thỏa thuận chuyển giao dữ liệu ra nước ngoài.",
            "implemented_controls": [
                "A.5.1", "A.5.2", "A.5.3", "A.5.4", "A.5.7", "A.5.8", "A.5.9", "A.5.10", "A.5.12", "A.5.14", "A.5.15", "A.5.16", "A.5.17", "A.5.18",
                "A.6.1", "A.6.2", "A.6.3", "A.6.4", "A.6.5", "A.6.6",
                "A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.8", "A.7.9", "A.7.10", "A.7.14",
                "A.8.1", "A.8.2", "A.8.3", "A.8.4", "A.8.7", "A.8.8", "A.8.9", "A.8.11", "A.8.12", "A.8.13", "A.8.15", "A.8.16", "A.8.19", "A.8.20", "A.8.21", "A.8.24", "A.8.25", "A.8.28"
            ]
        }
    },
    {
        "id": "tpl_basevn_saas",
        "name": "Base.vn Enterprise Platform (B2B SaaS SOC 2 Type II & ISO 27001)",
        "standard": "soc2",
        "industry": "B2B Enterprise SaaS",
        "description": "Nền tảng quản trị doanh nghiệp đa khách hàng (Multi-tenant B2B SaaS) với Row-Level Security, Teleport Zero-Trust Bastion, quy trình DevSecOps nghiêm ngặt bảo vệ dữ liệu khách hàng doanh nghiệp.",
        "is_builtin": 1,
        "data": {
            "assessment_standard": "soc2",
            "org_name": "Công ty Cổ phần Base Enterprise (Base.vn)",
            "org_size": "medium",
            "industry": "Nền tảng Công nghệ Doanh nghiệp B2B SaaS",
            "compliance_status": "compliant",
            "employees": 450,
            "servers": 85,
            "firewalls": 4,
            "vpn": True,
            "cloud_provider": "AWS (Singapore Region)",
            "antivirus": "Wazuh EDR + AWS Inspector",
            "backup_solution": "AWS RDS Automated Snapshot + S3 Glacier Vault Lock (RPO < 15m, RTO < 1h)",
            "siem": "Wazuh SIEM tích hợp OpenSearch Dashboard",
            "incidents_12m": 0,
            "it_staff": 35,
            "assessment_scope": "full",
            "scope_description": "Toàn bộ hệ sinh thái phần mềm quản trị doanh nghiệp Base.vn (Base Work+, Base Info+, Base HRM+, Base Finance+).",
            "network_diagram": "Mô hình Multi-tenant SaaS với cơ chế Row-Level Security (RLS) cách ly logic hoàn toàn giữa các khách hàng doanh nghiệp. 3-tier AWS VPC (Public ALB, Private EKS Cluster, Isolated RDS Multi-AZ). Quản trị SSH hạ tầng qua Teleport Zero-trust Bastion. CI/CD tích hợp SonarQube SAST, Snyk Dependency Check và Trivy Container Scan.",
            "notes": "Nhà cung cấp nền tảng SaaS phục vụ hơn 8,000 khách hàng doanh nghiệp tại Việt Nam và Đông Nam Á. Đã vượt qua kiểm định độc lập SOC 2 Type II và cam kết SLA dịch vụ đạt 99.9% uptime. Yêu cầu mã hóa dữ liệu At-Rest bằng AES-256 và In-Transit bằng TLS 1.3.",
            "implemented_controls": [
                "A.5.1", "A.5.2", "A.5.3", "A.5.4", "A.5.5", "A.5.7", "A.5.8", "A.5.9", "A.5.10", "A.5.12", "A.5.15", "A.5.16", "A.5.17", "A.5.18", "A.5.20", "A.5.24", "A.5.25", "A.5.26", "A.5.28",
                "A.6.1", "A.6.2", "A.6.3", "A.6.4", "A.6.5", "A.6.6", "A.6.7",
                "A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.6", "A.7.7", "A.7.8", "A.7.9", "A.7.10", "A.7.11", "A.7.14",
                "A.8.1", "A.8.2", "A.8.3", "A.8.4", "A.8.5", "A.8.7", "A.8.8", "A.8.9", "A.8.11", "A.8.12", "A.8.13", "A.8.14", "A.8.15", "A.8.16", "A.8.17", "A.8.18", "A.8.19", "A.8.20", "A.8.21", "A.8.22", "A.8.23", "A.8.24", "A.8.25", "A.8.26", "A.8.27", "A.8.28", "A.8.29", "A.8.30", "A.8.31"
            ]
        }
    }
]


class TemplateStore:
    _lock = threading.Lock()

    def __init__(self):
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS assessment_templates (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        standard TEXT NOT NULL,
                        industry TEXT NOT NULL,
                        description TEXT NOT NULL,
                        data TEXT NOT NULL,
                        is_builtin INTEGER NOT NULL DEFAULT 0,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_templates_standard
                    ON assessment_templates(standard)
                """)
                conn.commit()
                self._seed_builtin_templates(conn)
            except Exception as e:
                logger.error(f"Failed to initialize Template SQLite database: {e}")
            finally:
                conn.close()

    def _seed_builtin_templates(self, conn: sqlite3.Connection):
        """Seed or update built-in templates from BUILTIN_TEMPLATES."""
        try:
            cursor = conn.cursor()
            now = time.time()
            for tpl in BUILTIN_TEMPLATES:
                cursor.execute("""
                    INSERT INTO assessment_templates (id, name, standard, industry, description, data, is_builtin, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        standard=excluded.standard,
                        industry=excluded.industry,
                        description=excluded.description,
                        data=excluded.data,
                        updated_at=excluded.updated_at
                """, (
                    tpl["id"],
                    tpl["name"],
                    tpl["standard"],
                    tpl["industry"],
                    tpl["description"],
                    json.dumps(tpl["data"], ensure_ascii=False),
                    tpl["is_builtin"],
                    now,
                    now,
                ))
            conn.commit()
            logger.info(f"Seeded {len(BUILTIN_TEMPLATES)} built-in assessment templates.")
        except Exception as e:
            logger.error(f"Failed to seed built-in templates: {e}")

    def list_templates(self, standard: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all assessment templates, optionally filtered by standard."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                if standard and standard != "all":
                    cursor.execute("""
                        SELECT id, name, standard, industry, description, data, is_builtin, created_at, updated_at
                        FROM assessment_templates
                        WHERE standard = ?
                        ORDER BY is_builtin DESC, created_at ASC
                    """, (standard,))
                else:
                    cursor.execute("""
                        SELECT id, name, standard, industry, description, data, is_builtin, created_at, updated_at
                        FROM assessment_templates
                        ORDER BY is_builtin DESC, created_at ASC
                    """)
                
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append({
                        "id": row["id"],
                        "name": row["name"],
                        "standard": row["standard"],
                        "industry": row["industry"],
                        "description": row["description"],
                        "data": json.loads(row["data"]),
                        "is_builtin": bool(row["is_builtin"]),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    })
                return results
            finally:
                conn.close()

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a single assessment template by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, standard, industry, description, data, is_builtin, created_at, updated_at
                    FROM assessment_templates
                    WHERE id = ?
                """, (template_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "standard": row["standard"],
                    "industry": row["industry"],
                    "description": row["description"],
                    "data": json.loads(row["data"]),
                    "is_builtin": bool(row["is_builtin"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            finally:
                conn.close()

    def save_template(self, template_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a custom template."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                now = time.time()
                template_id = template_dict.get("id") or f"custom_{int(now)}"
                name = template_dict["name"]
                standard = template_dict.get("standard", "iso27001")
                industry = template_dict.get("industry", "Khác")
                description = template_dict.get("description", "")
                data_json = json.dumps(template_dict.get("data", {}), ensure_ascii=False)
                is_builtin = 1 if template_dict.get("is_builtin") else 0

                cursor.execute("""
                    INSERT INTO assessment_templates (id, name, standard, industry, description, data, is_builtin, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        standard=excluded.standard,
                        industry=excluded.industry,
                        description=excluded.description,
                        data=excluded.data,
                        updated_at=excluded.updated_at
                """, (
                    template_id, name, standard, industry, description, data_json, is_builtin, now, now
                ))
                conn.commit()
                return self.get_template(template_id)
            finally:
                conn.close()

    def delete_template(self, template_id: str) -> bool:
        """Delete a custom template by ID. Cannot delete built-in templates."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT is_builtin FROM assessment_templates WHERE id = ?", (template_id,))
                row = cursor.fetchone()
                if not row or row["is_builtin"] == 1:
                    return False
                cursor.execute("DELETE FROM assessment_templates WHERE id = ?", (template_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()


# Singleton
template_store = TemplateStore()
