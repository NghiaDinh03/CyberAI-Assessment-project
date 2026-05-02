export const ASSESSMENT_TEMPLATES_EN = [
    {
        id: "tpl_vietcombank",
        name: "🏦 Vietcombank — ISO 27001 (BSI Certified)",
        description: "Vietnam's largest bank by market capitalization. Achieved ISO 27001:2013 certification from BSI in 2018 for core banking, internet banking, mobile banking, and card payment systems. IT security team grew from ~30 to ~80 staff during implementation. Reduced security incidents by reported 40% in first year post-certification.",
        standard: "iso27001",
        source: "Vietcombank Investor Relations — Annual Reports; BSI Vietnam",
        sourceUrl: "https://www.vietcombank.com.vn/en/investor-relations",
        data: {
            assessment_standard: "iso27001",
            organization: {
                name: "Joint Stock Commercial Bank for Foreign Trade of Vietnam (Vietcombank)",
                size: "large",
                industry: "Finance - Banking",
                employees: 22000,
                it_staff: 80
            },
            infrastructure: {
                servers: 600,
                firewalls: "Palo Alto PA-5260 HA Pair, FortiWeb WAF, Cisco Firepower IPS",
                vpn: "Yes",
                cloud: "AWS (Web/Mobile Banking), Private Cloud VMware vSphere (Core Banking)",
                antivirus: "CrowdStrike Falcon XDR (endpoints + servers)",
                backup: "Veeam Backup & Replication, HPE StoreOnce, offsite tape LTO-9 (3-2-1 strategy)",
                siem: "Splunk Enterprise Security, IBM QRadar (DR)",
                network_diagram: "Zero Trust architecture across 600+ offices nationwide. Core Banking runs on IBM mainframe isolated behind Bastion Host + CyberArk PAM. DMZ with Nginx reverse proxy, FortiWeb WAF, Barracuda Mail Gateway. Database zone: Oracle RAC cluster, PostgreSQL HA. Management zone: Splunk SIEM, SolarWinds NMS. DR site (active-passive). Dual ISP with BGP failover. PCI DSS Level 1 compliant network segmentation for card operations."
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
                iso_status: "ISO 27001:2013 certified (BSI, 2018)"
            },
            notes: "Vietnam's largest commercial bank by market capitalization. ISO 27001:2013 certified by BSI in 2018. PCI DSS Level 1 compliant. Migrating to ISO 27001:2022 (deadline 10/2025). Reported 40% reduction in security incidents after first year of certification.",
            assessment_scope: "full",
            scope_description: ""
        }
    },
    {
        id: "tpl_fpt",
        name: "🏢 FPT Corporation — ISO 27001 Pioneer (2012)",
        description: "Vietnam's largest technology company and among the first Vietnamese organizations to achieve ISO 27001 (2012). Multiple subsidiaries certified: FPT Software (ISO 27001 + CMMI Level 5 + SOC 2 Type II), FPT Telecom (all 9 data centers), FPT Cloud (CSA STAR). 60,000+ employees across 30+ countries.",
        standard: "iso27001",
        source: "FPT Corporation Investor Relations; BSI certification database",
        sourceUrl: "https://fpt.com.vn/en/ir",
        data: {
            assessment_standard: "iso27001",
            organization: {
                name: "FPT Corporation",
                size: "large",
                industry: "Information Technology - Telecommunications",
                employees: 60000,
                it_staff: 800
            },
            infrastructure: {
                servers: 5000,
                firewalls: "Fortinet FortiGate HA clusters (HQ + branches), Palo Alto (data centers), Cloudflare Enterprise WAF",
                vpn: "Yes",
                cloud: "Multi-cloud: AWS (production), Azure (enterprise services), GCP (AI/ML workloads), FPT Cloud (proprietary). 9 data centers nationwide.",
                antivirus: "Microsoft Defender for Endpoint P2, CrowdStrike Falcon (servers), Proofpoint Email Security",
                backup: "Veeam v12, Commvault (Oracle DB), Azure Backup (SaaS), RPO 1h / RTO 4h",
                siem: "Microsoft Sentinel (primary), Splunk (FPT Telecom), SOAR: Cortex XSOAR",
                network_diagram: "Global delivery architecture spanning 30+ countries. Each data center (9 total) follows N+1 redundancy with Tier III Uptime certification. Kubernetes on AWS EKS + on-premise Rancher for microservices. FPT Software offices connected via SD-WAN. Zero Trust with Azure AD conditional access. DevSecOps pipeline: GitLab CI → SonarQube SAST → Trivy container scan → OWASP ZAP DAST → ArgoCD."
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
                iso_status: "ISO 27001:2013 certified (BSI/TÜV SÜD, 2012)"
            },
            notes: "Vietnam's largest technology company. ISO 27001 since 2012 — one of the earliest Vietnamese enterprises. FPT Software: ISO 27001 + CMMI Level 5 + SOC 2 Type II. FPT Telecom: ISO 27001 for all 9 data centers. FPT Cloud: CSA STAR. Major outsourcing contracts: Airbus, Deutsche Bank.",
            assessment_scope: "full",
            scope_description: ""
        }
    },
    {
        id: "tpl_techcombank",
        name: "🏦 Techcombank — ISO 27001 + SOC 2 (TÜV Rheinland)",
        description: "Vietnam's most digitally aggressive bank, investing over $500M in technology transformation (2018–2023). ISO 27001:2013 certified by TÜV Rheinland in 2019. Achieved SOC 2 Type II in parallel. Enabled Open API banking under SBV Circular 16/2020.",
        standard: "iso27001",
        source: "Techcombank Investor Relations; TÜV Rheinland Vietnam",
        sourceUrl: "https://www.techcombank.com.vn/en/investor-relations",
        data: {
            assessment_standard: "iso27001",
            organization: {
                name: "Vietnam Technological and Commercial Joint Stock Bank (Techcombank)",
                size: "large",
                industry: "Finance - Banking",
                employees: 12000,
                it_staff: 200
            },
            infrastructure: {
                servers: 500,
                firewalls: "Palo Alto PA-5250 HA, FortiWeb 3000E WAF, Cisco Firepower 4115 IPS",
                vpn: "Yes",
                cloud: "Hybrid cloud: AWS (digital banking platform), Azure (office workloads), Private Cloud (Core Banking T24 Temenos)",
                antivirus: "CrowdStrike Falcon XDR (all endpoints), SentinelOne (mobile)",
                backup: "Veeam Backup v12, AWS S3 Glacier offsite, tape library LTO-9",
                siem: "Splunk Enterprise Security 8.0 + Splunk SOAR",
                network_diagram: "Hybrid architecture: Core Banking (Temenos T24) on-premise with dedicated DMZ. Digital banking platform (Techcombank Mobile 5.0) on AWS. Open API Gateway for fintech partners. 24/7 SOC. Network: 300+ branches connected via MPLS. Zero Trust for remote access. PCI DSS Level 1 for card operations."
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
                    "A.8.21", "A.8.22", "A.8.23", "A.8.24", "A.8.25", "A.8.26", "A.8.27", "A.8.28",
                    "A.8.31", "A.8.32", "A.8.33", "A.8.34"
                ],
                incidents_12m: 1,
                iso_status: "ISO 27001:2013 certified (TÜV Rheinland, 2019)"
            },
            notes: "Vietnam's most digitally transformed bank. Invested >$500M in technology transformation (2018–2023, partnership with McKinsey). ISO 27001 from TÜV Rheinland 2019. SOC 2 Type II achieved in parallel. Powers Techcombank Mobile 5.0 and Open API Banking (SBV Circular 16/2020).",
            assessment_scope: "full",
            scope_description: ""
        }
    },
    {
        id: "tpl_viettel",
        name: "📡 Viettel Group — ISO 27001 + TCVN 11930 Level 4",
        description: "Vietnam's largest telecom and military-owned enterprise. Dual ISO 27001 (BSI) + TCVN 11930 Level 4 compliance. Operates 100M+ subscribers, Viettel Cyber Security (VCS) — Vietnam's leading MSSP, and Viettel IDC (Tier III Uptime + ISO 27001). Active in 11 international markets.",
        standard: "iso27001",
        source: "Viettel Group; Uptime Institute Tier Certification List",
        sourceUrl: "https://viettel.com.vn/en",
        data: {
            assessment_standard: "iso27001",
            organization: {
                name: "Viettel Group (Military Industry-Telecommunications Group)",
                size: "large",
                industry: "Telecommunications - Defense - Cybersecurity",
                employees: 45000,
                it_staff: 500
            },
            infrastructure: {
                servers: 8000,
                firewalls: "Multi-vendor: Palo Alto (core), Fortinet (branches), custom military-grade firewalls (critical infrastructure)",
                vpn: "Yes",
                cloud: "Viettel Cloud (proprietary, 3 data centers), AWS (international operations). Viettel IDC — Tier III Uptime Institute certified.",
                antivirus: "Custom Viettel Threat Intelligence platform, CrowdStrike (endpoints)",
                backup: "Geo-redundant backup across 3 DCs, tape offsite, RPO 30min / RTO 2h for critical systems",
                siem: "Custom Viettel SOC platform + Splunk Enterprise, national-scale threat monitoring",
                network_diagram: "Telecom-grade infrastructure: 100M+ subscribers across Vietnam + 11 international markets. Core network: MPLS backbone connecting 63 provinces. Viettel IDC: Tier III certified, 3 data centers (Hanoi, HCMC, Da Nang). Viettel Cyber Security (VCS) operates SOC monitoring government agencies and enterprises. Network security: DDoS mitigation, DNS filtering, BGP security. Military-grade physical security for critical nodes."
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
                incidents_12m: 0,
                iso_status: "ISO 27001:2013 certified (BSI) + TCVN 11930 Level 4"
            },
            notes: "Military-owned enterprise running commercial telecommunications. Viettel Cyber Security (VCS) is Vietnam's leading MSSP, providing SOC monitoring for government agencies and enterprises. Viettel IDC achieves Tier III Uptime + ISO 27001. In-house Viettel Threat Intelligence platform. Dual compliance: military + commercial.",
            assessment_scope: "full",
            scope_description: ""
        }
    },
    {
        id: "tpl_vinmec",
        name: "🏥 Vinmec Hospital — JCI Accredited Healthcare",
        description: "Vietnam's leading private hospital chain (Vingroup). JCI accredited with ISO 27001-aligned security for Hospital Information System (HIS) and Electronic Medical Records (EMR). Subject to Decree 13/2023 for patient data as sensitive personal data.",
        standard: "tcvn11930",
        source: "Vinmec International Hospital; JCI Accreditation Database",
        sourceUrl: "https://www.vinmec.com/en/",
        data: {
            assessment_standard: "tcvn11930",
            organization: {
                name: "Vinmec International General Hospital (Vingroup)",
                size: "large",
                industry: "Healthcare - International Hospital",
                employees: 3000,
                it_staff: 25
            },
            infrastructure: {
                servers: 80,
                firewalls: "FortiGate 200F HA, Cloudflare WAF",
                vpn: "Yes",
                cloud: "AWS (telemedicine platform), Private Cloud (HIS, EMR on-premise)",
                antivirus: "Kaspersky Endpoint Security for Business Advanced",
                backup: "Veeam Backup, NAS Synology HA (patient data), AWS S3 offsite",
                siem: "Wazuh SIEM 4.x",
                network_diagram: "Hospital network: 3 VLANs — Medical Devices (VLAN 10, IoMT isolated), Clinical Systems (VLAN 20, HIS/EMR/PACS), Administrative (VLAN 30). FortiGate 200F at perimeter. HIS runs on 4-server cluster Dell PowerEdge R750 (Windows Server 2022 + SQL Server 2019). PACS storage: NetApp FAS. Telemedicine via AWS. Wi-Fi separated: staff (WPA3-Enterprise) vs guest (captive portal). Badge access + CCTV across entire server room."
            },
            compliance: {
                implemented_controls: [
                    "NW.01", "NW.02", "NW.03", "NW.04",
                    "SV.01", "SV.02", "SV.07",
                    "APP.01", "APP.02", "APP.03",
                    "DAT.01", "DAT.02",
                    "MNG.01", "MNG.02"
                ],
                incidents_12m: 1,
                iso_status: "JCI Accredited, TCVN 11930 in progress"
            },
            notes: "Vietnam's leading private hospital (Vingroup subsidiary). JCI accredited (international healthcare quality standard). Deploying AI-assisted diagnostics with security controls. Electronic Medical Records (EMR) classified as sensitive personal data under Decree 13/2023/ND-CP. IoMT (Internet of Medical Things) isolated on dedicated VLAN.",
            assessment_scope: "by_system",
            scope_description: "HIS (Hospital Information System), EMR (Electronic Medical Records), Telemedicine platform, IoMT network"
        }
    },
    {
        id: "tpl_danang",
        name: "🏛️ Da Nang City — Smart City TCVN 11930 Level 3",
        description: "Da Nang City — Vietnam's #1 ranked ICT city (2019–2023). Da Nang Data Center achieved ISO 27001. TCVN 11930 Level 3 compliance for e-government services. Centralized SOC for all city systems. Recognized by ITU as ASEAN smart city security reference model.",
        standard: "tcvn11930",
        source: "Da Nang City Government Portal; Vietnam ICT Index (MIC)",
        sourceUrl: "https://danang.gov.vn/",
        data: {
            assessment_standard: "tcvn11930",
            organization: {
                name: "Da Nang City Department of Information and Communications (DIC)",
                size: "medium",
                industry: "Public Administration - Smart City",
                employees: 300,
                it_staff: 35
            },
            infrastructure: {
                servers: 120,
                firewalls: "FortiGate 600F HA, Sangfor WAF, Palo Alto (smart city edge)",
                vpn: "Yes",
                cloud: "Private Cloud OpenStack (Da Nang Data Center, ISO 27001 certified), VNPT Government Cloud (backup)",
                antivirus: "BKAV Endpoint + CrowdStrike (servers)",
                backup: "Veeam Backup, NAS QNAP RAID 6, offsite at VNPT DC (3-2-1 strategy)",
                siem: "Centralized SOC: Wazuh SIEM + Viettel Threat Intelligence feeds, 24/7 monitoring",
                network_diagram: "Smart city architecture: Da Nang Data Center (ISO 27001 certified) as hub. 4 network zones: (1) Public Services (Government Portal, Online Public Services levels 3-4, One-stop portal) → Sangfor WAF, (2) IoT Zone (smart traffic, environmental sensors, CCTV — isolated VLAN), (3) Internal Government (AD 2022, Exchange, file server, 30+ agency applications), (4) SOC/Management (centralized monitoring for all city systems). Leased-line VNPT 1Gbps + Viettel 500Mbps backup. Connected to national LGSP. Regular security drills with MIC."
            },
            compliance: {
                implemented_controls: [
                    "NW.01", "NW.02", "NW.03", "NW.04", "NW.05", "NW.06",
                    "SV.01", "SV.02", "SV.03", "SV.07", "SV.08",
                    "APP.01", "APP.02", "APP.03", "APP.04", "APP.07",
                    "DAT.01", "DAT.02", "DAT.03",
                    "MNG.01", "MNG.02", "MNG.03", "MNG.04", "MNG.05"
                ],
                incidents_12m: 2,
                iso_status: "TCVN 11930 Level 3 (Da Nang DC ISO 27001 certified)"
            },
            notes: "Ranked #1 Vietnam ICT Index for 5 consecutive years 2019–2023 (MIC). Data Center achieved ISO 27001. ITU recognized as ASEAN smart city security reference model. Centralized SOC monitors entire city systems. 2 DDoS incidents targeting the Government Portal successfully blocked by WAF. Online public services levels 3-4 serving 1.2M residents.",
            assessment_scope: "by_system",
            scope_description: "Government Portal, Online Public Services, Da Nang Data Center, IoT Smart City infrastructure"
        }
    }
];
