export const ASSESSMENT_TEMPLATES = [
    {
        id: "tpl_bank_advanced",
        name: "🏦 Ngân hàng Top-tier (ISO 27001 đạt 95%)",
        description: "Ngân hàng thương mại quốc doanh hạng Tier-1 đã đạt chứng nhận ISO 27001, hạ tầng bảo mật doanh nghiệp toàn diện với SOC 24/7 và Zero Trust Architecture.",
        standard: "iso27001",
        data: {
            assessment_standard: "iso27001",
            organization: {
                name: "Ngân hàng TMCP Quốc tế VietGlobal",
                size: "large",
                industry: "Tài chính - Ngân hàng",
                employees: 5000,
                it_staff: 120
            },
            infrastructure: {
                servers: 800,
                firewalls: "Palo Alto PA-5260 HA Pair (biên), Palo Alto PA-3260 (giữa zones), FortiWeb 3000E WAF, Cisco Firepower 4115 (IPS)",
                vpn: "Có",
                cloud: "AWS (Web/Mobile Banking), Azure (DR site), Private Cloud VMware vSphere 8.0 (Core Banking)",
                antivirus: "CrowdStrike Falcon XDR (toàn bộ endpoint + server), SentinelOne Singularity (mobile)",
                backup: "Veeam Backup & Replication v12, HPE StoreOnce, AWS S3 Glacier (offsite 3-2-1), tape library LTO-9",
                siem: "Splunk Enterprise Security 8.0 + Splunk SOAR, IBM QRadar (DR site)",
                network_diagram: "Kiến trúc Zero Trust 7 Zones: (1) Internet Zone → Palo Alto PA-5260 HA → (2) DMZ Zone chứa Reverse Proxy Nginx, WAF FortiWeb, Mail Gateway Barracuda → (3) Application Zone chứa Web/API servers cluster (20 nodes), Load Balancer F5 BIG-IP → (4) Core Banking Zone hoàn toàn cách ly, 12 server IBM Power10 chạy AS/400, chỉ truy cập qua Bastion Host + PAM CyberArk → (5) Database Zone gồm Oracle RAC 19c cluster (4 node), PostgreSQL HA, Redis Sentinel → (6) Management Zone chứa SIEM Splunk, NMS SolarWinds, PAM CyberArk, Ansible Tower → (7) DR Zone tại Azure (active-passive). Switch Core: Cisco Nexus 9500 stack, Access: Cisco Catalyst 9300. VLAN: Server (10), User (20-29 theo phòng ban), Guest (99), VoIP (50), Printer (60), Management (1). Dual ISP (VNPT Leased-line 1Gbps + Viettel MPLS 500Mbps) với BGP failover. VPN SSL GlobalProtect cho 2000 nhân viên remote. NAC Cisco ISE kiểm soát thiết bị kết nối. Micro-segmentation qua VMware NSX-T. NTP server nội bộ sync GPS."
            },
            compliance: {
                implemented_controls: [
                    "A.5.1", "A.5.2", "A.5.3", "A.5.4", "A.5.5", "A.5.6", "A.5.7", "A.5.8", "A.5.9", "A.5.10",
                    "A.5.11", "A.5.12", "A.5.13", "A.5.14", "A.5.15", "A.5.16", "A.5.17", "A.5.18", "A.5.19", "A.5.20",
                    "A.5.21", "A.5.22", "A.5.23", "A.5.24", "A.5.25", "A.5.26", "A.5.27", "A.5.28", "A.5.29", "A.5.30",
                    "A.5.31", "A.5.32", "A.5.33", "A.5.34", "A.5.35", "A.5.36", "A.5.37",
                    "A.6.1", "A.6.2", "A.6.3", "A.6.4", "A.6.5", "A.6.6", "A.6.7", "A.6.8",
                    "A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.5", "A.7.6", "A.7.7", "A.7.8", "A.7.9", "A.7.10",
                    "A.7.11", "A.7.12", "A.7.13", "A.7.14",
                    "A.8.1", "A.8.2", "A.8.3", "A.8.4", "A.8.5", "A.8.6", "A.8.7", "A.8.8", "A.8.9", "A.8.10",
                    "A.8.11", "A.8.12", "A.8.13", "A.8.14", "A.8.15", "A.8.16", "A.8.17", "A.8.18", "A.8.19", "A.8.20",
                    "A.8.21", "A.8.22", "A.8.23", "A.8.24", "A.8.25", "A.8.26", "A.8.27", "A.8.28", "A.8.29",
                    "A.8.31", "A.8.32", "A.8.33", "A.8.34"
                ],
                incidents_12m: 2,
                iso_status: "Đã chứng nhận"
            },
            notes: "Đã đạt chứng nhận ISO 27001:2022 từ BSI. SOC L2/L3 hoạt động 24/7 với 15 analyst. Diễn tập Red Team/Blue Team hàng quý. PCI-DSS Level 1 compliant. Đang triển khai SASE (Zscaler). 2 sự cố phishing trong 12 tháng qua đều được SOC phát hiện và xử lý trong 15 phút."
        }
    },
    {
        id: "tpl_enterprise",
        name: "🏢 Tập đoàn Công nghệ lớn (ISO 97%)",
        description: "Tập đoàn công nghệ quy mô 3000+ nhân sự đã đạt ISO 27001, triển khai DevSecOps toàn diện, hạ tầng hybrid cloud với DR site.",
        standard: "iso27001",
        data: {
            assessment_standard: "iso27001",
            organization: {
                name: "Tập đoàn Công nghệ An Phát Holdings",
                size: "large",
                industry: "Công nghệ thông tin - Viễn thông",
                employees: 3200,
                it_staff: 180
            },
            infrastructure: {
                servers: 1200,
                firewalls: "Fortinet FortiGate 600F HA (HQ), Palo Alto PA-450 (chi nhánh x8), Cloudflare Enterprise WAF, Cisco Firepower 2130 IPS",
                vpn: "Có",
                cloud: "Multi-cloud: AWS (production), Azure (DR + Office 365), GCP (AI/ML workloads). On-premise VMware vSAN 8.0 cho hệ thống legacy.",
                antivirus: "Microsoft Defender for Endpoint P2 (endpoint), CrowdStrike Falcon (server), Proofpoint Email Security",
                backup: "Veeam v12 + Wasabi S3 offsite, Azure Backup (SaaS), Commvault cho Oracle DB, RPO 1h / RTO 4h",
                siem: "Microsoft Sentinel (primary) + Wazuh (on-prem legacy), SOAR: Cortex XSOAR",
                network_diagram: "Hybrid Architecture 6 Zones: (1) Edge/Internet → Cloudflare CDN + WAF → FortiGate 600F HA → (2) Public DMZ: Nginx reverse proxy cluster (4 nodes), API Gateway Kong, Mail relay Postfix → (3) Application Zone: Kubernetes cluster 40 worker nodes (AWS EKS + on-prem Rancher), microservices architecture → (4) Data Zone: PostgreSQL Patroni HA (3 nodes), MongoDB ReplicaSet, Redis Cluster, Elasticsearch 8.x cluster (5 nodes) → (5) Internal Zone: Active Directory 2022 (3 DC), SCCM, WSUS, Print server, File server DFS → (6) Management: Sentinel SIEM, Ansible AWX, Terraform Cloud, Vault (HashiCorp), Grafana + Prometheus monitoring. Switch: Aruba CX 8360 core, Aruba CX 6300 access. Wireless: Aruba AP-635 (Wi-Fi 6E) managed by Aruba Central. SD-WAN Fortinet kết nối 8 chi nhánh. VPN: GlobalProtect SSL (nhân viên), IPSec site-to-site (chi nhánh). NAC: Aruba ClearPass. DNS: Infoblox DDI. NTP: Meinberg GPS receiver."
            },
            compliance: {
                implemented_controls: [
                    "A.5.1", "A.5.2", "A.5.3", "A.5.4", "A.5.5", "A.5.6", "A.5.7", "A.5.8", "A.5.9", "A.5.10",
                    "A.5.11", "A.5.12", "A.5.13", "A.5.14", "A.5.15", "A.5.16", "A.5.17", "A.5.18", "A.5.19", "A.5.20",
                    "A.5.21", "A.5.22", "A.5.23", "A.5.24", "A.5.25", "A.5.26", "A.5.27", "A.5.28", "A.5.29", "A.5.30",
                    "A.5.31", "A.5.32", "A.5.33", "A.5.34", "A.5.35", "A.5.36", "A.5.37",
                    "A.6.1", "A.6.2", "A.6.3", "A.6.4", "A.6.5", "A.6.6", "A.6.7", "A.6.8",
                    "A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.5", "A.7.6", "A.7.7", "A.7.8", "A.7.9", "A.7.10",
                    "A.7.11", "A.7.12", "A.7.13", "A.7.14",
                    "A.8.1", "A.8.2", "A.8.3", "A.8.4", "A.8.5", "A.8.6", "A.8.7", "A.8.8", "A.8.9", "A.8.10",
                    "A.8.11", "A.8.12", "A.8.13", "A.8.14", "A.8.15", "A.8.16", "A.8.17", "A.8.18", "A.8.19", "A.8.20",
                    "A.8.21", "A.8.22", "A.8.23", "A.8.24", "A.8.25", "A.8.26", "A.8.27", "A.8.28", "A.8.29", "A.8.30",
                    "A.8.31", "A.8.32", "A.8.33", "A.8.34"
                ],
                incidents_12m: 1,
                iso_status: "Đã chứng nhận"
            },
            notes: "ISO 27001:2022 certified (TÜV Rheinland). DevSecOps pipeline: GitLab CI → SonarQube SAST → Trivy container scan → OWASP ZAP DAST → ArgoCD deploy. Pentest hàng quý bởi CyberSecurity Vietnam. Bug bounty program trên HackerOne. DPO chuyên trách. Đào tạo Security Awareness hàng quý qua KnowBe4."
        }
    },
    {
        id: "tpl_bank",
        name: "🏦 Ngân hàng Đang triển khai (30%)",
        description: "Ngân hàng thương mại cổ phần đang triển khai ISO 27001, hạ tầng Core Banking riêng biệt, đã có EDR và SIEM nhưng chưa đầy đủ.",
        standard: "iso27001",
        data: {
            assessment_standard: "iso27001",
            organization: {
                name: "Ngân hàng Thương mại Cổ phần AlphaBank",
                size: "large",
                industry: "Tài chính - Ngân hàng",
                employees: 1500,
                it_staff: 45
            },
            infrastructure: {
                servers: 250,
                firewalls: "Palo Alto PA-5250 HA, FortiWeb WAF",
                vpn: "Có",
                cloud: "AWS (cho Web Public) & Private Cloud nội bộ",
                antivirus: "CrowdStrike Falcon EDR",
                backup: "Veeam Backup & Replication, Tape offsite",
                siem: "Splunk Enterprise Security",
                network_diagram: "Mạng chia 5 Zones: Internet → PA-5250 → DMZ (Web/API/Mail) → Core Banking Zone (IBM AS/400, cách ly hoàn toàn) → Database Zone (Oracle RAC) → Management Zone (SIEM, PAM). Switch Cisco Catalyst 9300. VPN SSL cho 500 nhân viên. Bastion Host + CyberArk PAM cho quản trị server."
            },
            compliance: {
                implemented_controls: [
                    "A.5.1", "A.5.2", "A.5.3", "A.5.9", "A.5.15", "A.5.16", "A.5.17", "A.5.30",
                    "A.6.1", "A.6.3", "A.6.6",
                    "A.7.1", "A.7.2", "A.7.4", "A.7.5", "A.7.11",
                    "A.8.1", "A.8.2", "A.8.5", "A.8.7", "A.8.12", "A.8.13", "A.8.14", "A.8.15", "A.8.16", "A.8.20", "A.8.22", "A.8.24"
                ],
                incidents_12m: 1,
                iso_status: "Đang triển khai"
            },
            notes: "Vừa bị 1 đợt Phishing tương đối lớn vào tháng trước, 3 nhân sự click nhầm link nhưng EDR đã block được payload. Đang trong quá trình hoàn thiện tài liệu để xin chứng nhận ISO 27001."
        }
    },
    {
        id: "tpl_hospital",
        name: "🏥 Bệnh viện / Y tế (15%)",
        description: "Bệnh viện đa khoa lớn sử dụng hệ thống HIS nội bộ, hạ tầng CNTT cơ bản, chưa có quy trình bảo mật bài bản.",
        standard: "tcvn11930",
        data: {
            assessment_standard: "tcvn11930",
            organization: {
                name: "Bệnh viện Đa khoa Trung tâm Y Tế Mới",
                size: "large",
                industry: "Y tế - Khám chữa bệnh",
                employees: 500,
                it_staff: 5
            },
            infrastructure: {
                servers: 15,
                firewalls: "FortiGate 100F",
                vpn: "Không",
                cloud: "Không sử dụng",
                antivirus: "Kaspersky Endpoint Security",
                backup: "NAS Synology backup hàng ngày",
                siem: "Không có",
                network_diagram: "Mạng đơn giản 2 VLAN: Khu Hành chính (VLAN 10) và Khu Khám Bệnh (VLAN 20). FortiGate 100F đặt tại biên. Switch HP 1920 không managed. Phần mềm HIS chạy trên 2 server Dell PowerEdge T440 (Windows Server 2019 + SQL Server 2017). Không có DMZ. Wi-Fi dùng chung cho nhân viên và khách."
            },
            compliance: {
                implemented_controls: [
                    "NW.01", "NW.02",
                    "SV.01", "SV.02",
                    "DAT.01"
                ],
                incidents_12m: 3,
                iso_status: "Chưa triển khai"
            },
            notes: "CSDL bệnh nhân (Hồ sơ bệnh án điện tử) lưu trữ không mã hóa trên SQL Server. Chưa có quy trình xử lý sự cố lộ lọt dữ liệu. 3 lần bị ransomware cảnh báo trong năm qua nhưng Kaspersky đã chặn."
        }
    },
    {
        id: "tpl_startup",
        name: "🚀 Startup SaaS (29%)",
        description: "Startup công nghệ 100% Cloud, hạ tầng Kubernetes trên AWS, tốc độ phát triển nhanh nhưng thiếu tài liệu hóa quy trình.",
        standard: "tcvn11930",
        data: {
            assessment_standard: "tcvn11930",
            organization: {
                name: "Công ty Cổ phần TechCloud VN",
                size: "small",
                industry: "Phần mềm dịch vụ (SaaS)",
                employees: 30,
                it_staff: 15
            },
            infrastructure: {
                servers: 50,
                firewalls: "AWS Security Groups, Cloudflare WAF",
                vpn: "Có",
                cloud: "100% AWS (EKS, RDS, S3, CloudFront, Lambda)",
                antivirus: "Bitdefender GravityZone",
                backup: "AWS RDS Automated Backup, S3 Versioning",
                siem: "AWS CloudTrail + CloudWatch Logs",
                network_diagram: "100% Cloud (không có Data Center vật lý). AWS VPC chia 3 subnet: Public (ALB + CloudFront), Private (EKS worker nodes, 12 pods), Isolated (RDS PostgreSQL Multi-AZ). Kubernetes trên EKS 1.28. CI/CD: GitHub Actions → SonarQube → ECR → ArgoCD. Dev truy cập qua VPN WireGuard. IAM phân quyền strict by tag. WAF Cloudflare chặn OWASP Top 10."
            },
            compliance: {
                implemented_controls: [
                    "NW.01", "NW.02", "NW.04",
                    "SV.01", "SV.02", "SV.07",
                    "APP.02", "APP.03",
                    "DAT.01", "DAT.02"
                ],
                incidents_12m: 0,
                iso_status: "Chưa triển khai"
            },
            notes: "Tốc độ code rất nhanh nhưng chưa có chính sách tài liệu hóa. Cần rà soát theo TCVN 11930 để chuẩn bị xin giấy phép đăng ký cung cấp dịch vụ viễn thông tại VN."
        }
    },
    {
        id: "tpl_gov",
        name: "🏛️ Cơ quan Nhà nước Cấp độ 3 (53%)",
        description: "Hệ thống thông tin cấp Sở/Ngành phục vụ dịch vụ công mức 3-4, yêu cầu tuân thủ cấp độ 3 theo TCVN 11930:2017.",
        standard: "tcvn11930",
        data: {
            assessment_standard: "tcvn11930",
            organization: {
                name: "Sở Thông tin và Truyền thông tỉnh XYZ",
                size: "medium",
                industry: "Hành chính công",
                employees: 200,
                it_staff: 8
            },
            infrastructure: {
                servers: 30,
                firewalls: "FortiGate 200F, Sangfor WAF",
                vpn: "Có",
                cloud: "Trung tâm Dữ liệu tỉnh (Private Cloud OpenStack)",
                antivirus: "BKAV Endpoint",
                backup: "Veeam Backup, NAS Synology 8-bay RAID 6",
                siem: "Wazuh SIEM 4.x (3 nodes)",
                network_diagram: "Mạng 3 VLAN: Nội bộ (VLAN 10 - 80 PC), DMZ (VLAN 50 - Cổng TTĐT, Dịch vụ công, Mail), Quản trị (VLAN 1 - SIEM, AD, Backup). FortiGate 200F đặt biên + Sangfor WAF bảo vệ Cổng TTĐT. Switch HP Aruba 2930F. Server: 4 HPE DL380 Gen10 chạy Active Directory, Exchange, SQL Server, App server DVCTT. Kết nối LGSP qua Leased-line VNPT 100Mbps. Wazuh SIEM thu log từ 30 server."
            },
            compliance: {
                implemented_controls: [
                    "NW.01", "NW.02", "NW.03", "NW.04", "NW.05",
                    "SV.01", "SV.02", "SV.07", "SV.08",
                    "APP.01", "APP.02", "APP.03", "APP.07",
                    "DAT.01", "DAT.02",
                    "MNG.01", "MNG.02", "MNG.03"
                ],
                incidents_12m: 2,
                iso_status: "Đang triển khai"
            },
            notes: "Cung cấp dịch vụ công trực tuyến mức 3-4 cho 1.2 triệu dân. 2 lần bị DDoS nhắm vào Cổng TTĐT nhưng WAF đã chặn. Chưa có quy trình ứng cứu sự cố chính thức. Cần hoàn thiện diễn tập ATTT hàng năm theo yêu cầu Bộ TT&TT."
        }
    }
];

