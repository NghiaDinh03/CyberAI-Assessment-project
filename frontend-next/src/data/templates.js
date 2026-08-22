/**
 * Dynamic Assessment Templates Module
 * Templates are stored and served dynamically via SQLite Database (GET /api/templates).
 * This module provides standard definitions and fallback data.
 */

export const BUILTIN_TEMPLATES = [
    {
        id: 'tpl_evn_tpc',
        name: 'Công ty TNHH MTV Nhiệt điện Thủ Đức - EVN TPC (Hạ tầng Năng lượng & TCVN 11930 / ISO 27001)',
        standard: 'tcvn11930',
        industry: 'Năng lượng & Điện lực (Critical Infrastructure)',
        description: 'Hệ thống thông tin quản lý sản xuất và văn phòng điều hành của Nhiệt điện Thủ Đức (EVN TPC / EVNGENCO 3). Đánh giá an toàn thông tin theo cấp độ bảo vệ TCVN 11930:2017 Cấp độ 3 và ISO 27001:2022, phát hiện 53 lỗ hổng bảo mật thực tế (EOL OS Windows Server 2008/2016, SQL Server cũ, SWEET32, phân vùng IT/OT).',
        is_builtin: true,
        data: {
            assessment_standard: 'tcvn11930',
            org_name: 'Công ty TNHH MTV Nhiệt điện Thủ Đức (EVN TPC)',
            org_size: 'medium',
            industry: 'Năng lượng & Tiện ích công cộng (Critical Energy Infrastructure)',
            compliance_status: 'partially_compliant',
            employees: 320,
            servers: 9,
            firewalls: 2,
            vpn: true,
            cloud_provider: 'None (On-Premises Hyper-V & Physical Dell PowerEdge)',
            antivirus: 'Trend Micro Apex One + Windows Defender',
            backup_solution: 'Veeam Backup & Replication (Offline tape + NAS backup hàng tuần)',
            siem: 'Splunk Enterprise (Tập trung log từ DC01, Firewall, Switch)',
            incidents_12m: 2,
            it_staff: 5,
            assessment_scope: 'full',
            scope_description: 'Toàn bộ hạ tầng mạng LAN/DMZ, 09 máy chủ vật lý & ảo hóa điều hành (EOFFICE-DB, DC01, Web Portal, Mail Server, Máy chủ ứng dụng quản lý kỹ thuật) thuộc dải mạng 10.140.0.0/24, domain thuducpp.evn.vn.',
            network_diagram: 'Mô hình mạng 2 lớp: Vùng biên tiếp giáp Internet bảo vệ bởi Firewall thế hệ mới (NGFW), kết nối VPN bảo mật về EVN Tập đoàn. Vùng mạng nội bộ (10.140.0.0/24) bao gồm 9 máy chủ: DC01 (Active Directory), EOFFICE-DB (Windows Server 2016 / MS SQL Server 2016), Web Server (Windows Server 2008 EOL), Mail Gateway. Phân tách mạng IT điều hành và OT/SCADA thông qua Firewall công nghiệp.',
            notes: 'Hồ sơ đánh giá lỗ hổng thực tế Đợt 4/2026 ghi nhận 53 lỗ hổng tồn tại: 18 lỗ hổng Nghiêm trọng (CVSS 9.0-10.0 do thiếu bản vá bảo mật Hotfix KB5070247, HĐH Windows Server 2008 EOL, MS SQL Server 2016 build 13.2 cũ), 14 lỗ hổng Cao (SWEET32 CVE-2016-2183 trên giao thức SSL 3DES, RDP không bắt buộc NLA), và các cấu hình SMBv1 chưa vô hiệu hóa. Cần lập Action Plan chuyển dịch và vá lỗi theo Nghị định 85/2016/NĐ-CP và TCVN 11930:2017.',
            implemented_controls: [
                'A.5.1', 'A.5.2', 'A.5.3', 'A.5.4', 'A.5.15', 'A.5.16', 'A.5.17', 'A.5.18', 'A.5.24', 'A.5.25', 'A.5.26',
                'A.6.1', 'A.6.2', 'A.6.3', 'A.6.4', 'A.6.5',
                'A.7.1', 'A.7.2', 'A.7.3', 'A.7.4', 'A.7.7', 'A.7.8', 'A.7.9', 'A.7.10',
                'A.8.1', 'A.8.2', 'A.8.3', 'A.8.4', 'A.8.7', 'A.8.9', 'A.8.10', 'A.8.12', 'A.8.13', 'A.8.14', 'A.8.15',
                'A.8.16', 'A.8.17', 'A.8.18', 'A.8.19', 'A.8.20', 'A.8.21', 'A.8.22', 'A.8.23', 'A.8.24', 'A.8.25'
            ]
        }
    },
    {
        id: 'tpl_momo_fintech',
        name: 'Ví Điện Tử MoMo (Fintech PCI DSS v4.0 & ISO 27001:2022)',
        standard: 'pci_dss',
        industry: 'Fintech & Trung gian thanh toán',
        description: 'Mô hình ví điện tử với 30 triệu người dùng, kiến trúc Zero Trust trên AWS, phân vùng PCI Zone cô lập, AWS CloudHSM FIPS 140-2 Level 3, mã hóa toàn diện dữ liệu thẻ PAN/CVV.',
        is_builtin: true,
        data: {
            assessment_standard: 'pci_dss',
            org_name: 'Công ty Cổ phần Dịch vụ Di động Trực tuyến (M_Service / MoMo)',
            org_size: 'enterprise',
            industry: 'Công nghệ Tài chính (Fintech & Payment Gateway)',
            compliance_status: 'compliant',
            employees: 2500,
            servers: 450,
            firewalls: 12,
            vpn: true,
            cloud_provider: 'AWS (Multi-AZ Multi-Region)',
            antivirus: 'CrowdStrike Falcon EDR + GuardDuty',
            backup_solution: 'AWS Backup tự động đa vùng địa lý, mã hóa KMS CMK với RPO < 5 phút, RTO < 15 phút',
            siem: 'Datadog Security Monitoring + AWS OpenSearch SIEM (24/7 SOC)',
            incidents_12m: 0,
            it_staff: 180,
            assessment_scope: 'full',
            scope_description: 'Toàn bộ môi trường Cardholder Data Environment (CDE), ứng dụng di động iOS/Android, hệ sinh thái thanh toán mã QR, hệ thống Core Payment và hạ tầng dữ liệu trên AWS.',
            network_diagram: 'Kiến trúc Zero Trust trên AWS. Phân vùng PCI Payment Zone cách ly hoàn toàn qua mTLS API Gateway; Quản trị truy cập đặc quyền PAM qua CyberArk. Dữ liệu thẻ lưu trữ được mã hóa phần cứng bằng AWS CloudHSM (FIPS 140-2 Level 3). CI/CD pipeline tích hợp Snyk SAST, Trivy Container scanning và HashiCorp Vault.',
            notes: 'Hệ thống ví điện tử thanh toán hàng đầu Việt Nam. Tuân thủ nghiêm ngặt PCI DSS v4.0 cấp độ cao nhất (Service Provider Level 1) và Nghị định 13/2023 về Bảo vệ Dữ liệu Cá nhân. Hệ thống AI phát hiện gian lận giao dịch theo thời gian thực (real-time sub-200ms).',
            implemented_controls: [
                'A.5.1', 'A.5.2', 'A.5.3', 'A.5.4', 'A.5.5', 'A.5.6', 'A.5.7', 'A.5.8', 'A.5.9', 'A.5.10',
                'A.5.11', 'A.5.12', 'A.5.13', 'A.5.14', 'A.5.15', 'A.5.16', 'A.5.17', 'A.5.18', 'A.5.19', 'A.5.20',
                'A.6.1', 'A.6.2', 'A.6.3', 'A.6.4', 'A.6.5', 'A.6.6', 'A.6.7', 'A.6.8',
                'A.7.1', 'A.7.2', 'A.7.3', 'A.7.4', 'A.7.5', 'A.7.6', 'A.7.7', 'A.7.8', 'A.7.9', 'A.7.10',
                'A.8.1', 'A.8.2', 'A.8.3', 'A.8.4', 'A.8.5', 'A.8.6', 'A.8.7', 'A.8.8', 'A.8.9', 'A.8.10',
                'A.8.20', 'A.8.21', 'A.8.22', 'A.8.23', 'A.8.24', 'A.8.25', 'A.8.26', 'A.8.27', 'A.8.28'
            ]
        }
    },
    {
        id: 'tpl_tiki_ecommerce',
        name: 'Sàn Thương Mại Điện Tử Tiki (E-Commerce & Nghị định 13/2023)',
        standard: 'nd13',
        industry: 'Thương mại Điện tử & Logistics',
        description: 'Nền tảng thương mại điện tử quy mô lớn trên GCP GKE, hệ thống quản lý kho TikiNOW, bảo vệ dữ liệu cá nhân khách hàng PII theo Nghị định 13/2023/NĐ-CP.',
        is_builtin: true,
        data: {
            assessment_standard: 'nd13',
            org_name: 'Công ty Cổ phần Ti Ki (Tiki Corporation)',
            org_size: 'enterprise',
            industry: 'Thương mại điện tử & Chuỗi cung ứng (E-Commerce Marketplace)',
            compliance_status: 'partially_compliant',
            employees: 1800,
            servers: 320,
            firewalls: 8,
            vpn: true,
            cloud_provider: 'Google Cloud Platform (GCP)',
            antivirus: 'SentinelOne Singularity + Google Cloud Security Command Center',
            backup_solution: 'Google Cloud Storage Multi-Regional với chính sách Retention Lock 3 năm',
            siem: 'Google Chronicle SIEM tích hợp Elasticsearch log cluster',
            incidents_12m: 1,
            it_staff: 120,
            assessment_scope: 'full',
            scope_description: 'Hạ tầng Website tiki.vn, ứng dụng di động Tiki App, nền tảng vi dịch vụ trên Google Kubernetes Engine (GKE), hệ thống quản lý kho vận TikiNOW Smart Logistics.',
            network_diagram: 'Kiến trúc Microservices trên GCP GKE (Google Kubernetes Engine) trải rộng 3 Availability Zones. Sử dụng Cloudflare Enterprise bảo vệ DDoS/WAF Layer 7. Dữ liệu nhạy cảm PII được ẩn danh hóa và bảo vệ nghiêm ngặt.',
            notes: 'Hệ thống phục vụ hàng triệu đơn hàng mỗi tháng. Định kỳ tổ chức Pentest Red-Team và duy trì Bug Bounty.',
            implemented_controls: [
                'A.5.1', 'A.5.2', 'A.5.3', 'A.5.4', 'A.5.7', 'A.5.8', 'A.5.9', 'A.5.10', 'A.5.12',
                'A.6.1', 'A.6.2', 'A.6.3', 'A.6.4', 'A.6.5', 'A.6.6',
                'A.7.1', 'A.7.2', 'A.7.3', 'A.7.4', 'A.7.8', 'A.7.9', 'A.7.10',
                'A.8.1', 'A.8.2', 'A.8.3', 'A.8.4', 'A.8.7', 'A.8.8', 'A.8.9', 'A.8.20', 'A.8.21'
            ]
        }
    },
    {
        id: 'tpl_basevn_saas',
        name: 'Base.vn Enterprise Platform (B2B SaaS SOC 2 Type II & ISO 27001)',
        standard: 'soc2',
        industry: 'B2B Enterprise SaaS',
        description: 'Nền tảng quản trị doanh nghiệp đa khách hàng (Multi-tenant B2B SaaS) với Row-Level Security, Teleport Zero-Trust Bastion, quy trình DevSecOps nghiêm ngặt.',
        is_builtin: true,
        data: {
            assessment_standard: 'soc2',
            org_name: 'Công ty Cổ phần Base Enterprise (Base.vn)',
            org_size: 'medium',
            industry: 'Nền tảng Công nghệ Doanh nghiệp B2B SaaS',
            compliance_status: 'compliant',
            employees: 450,
            servers: 85,
            firewalls: 4,
            vpn: true,
            cloud_provider: 'AWS (Singapore Region)',
            antivirus: 'Wazuh EDR + AWS Inspector',
            backup_solution: 'AWS RDS Automated Snapshot + S3 Glacier Vault Lock (RPO < 15m, RTO < 1h)',
            siem: 'Wazuh SIEM tích hợp OpenSearch Dashboard',
            incidents_12m: 0,
            it_staff: 35,
            assessment_scope: 'full',
            scope_description: 'Toàn bộ hệ sinh thái phần mềm quản trị doanh nghiệp Base.vn (Base Work+, Base Info+, Base HRM+, Base Finance+).',
            network_diagram: 'Mô hình Multi-tenant SaaS với Row-Level Security (RLS) cách ly logic hoàn toàn. 3-tier AWS VPC. Quản trị SSH qua Teleport Zero-trust Bastion. CI/CD tích hợp SonarQube, Snyk và Trivy.',
            notes: 'Phục vụ hơn 8,000 khách hàng doanh nghiệp. Đạt chứng chỉ SOC 2 Type II và SLA 99.9%.',
            implemented_controls: [
                'A.5.1', 'A.5.2', 'A.5.3', 'A.5.4', 'A.5.5', 'A.5.7', 'A.5.8', 'A.5.9', 'A.5.10',
                'A.6.1', 'A.6.2', 'A.6.3', 'A.6.4', 'A.6.5', 'A.6.6', 'A.6.7',
                'A.7.1', 'A.7.2', 'A.7.3', 'A.7.4', 'A.7.6', 'A.7.7', 'A.7.8', 'A.7.9', 'A.7.10',
                'A.8.1', 'A.8.2', 'A.8.3', 'A.8.4', 'A.8.5', 'A.8.7', 'A.8.8', 'A.8.9', 'A.8.20', 'A.8.24'
            ]
        }
    }
]

export function getAssessmentTemplates(locale = 'vi') {
    return BUILTIN_TEMPLATES
}

export const ASSESSMENT_TEMPLATES = BUILTIN_TEMPLATES
