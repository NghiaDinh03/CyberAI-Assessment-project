export const CONTROL_DESCRIPTIONS_EN = {
    // === ISO 27001:2022 — Annex A Controls ===

    // A.5 Organizational Controls
    "A.5.1": {
        requirement: "Establish, approve, and communicate an information security policy aligned with organizational objectives.",
        criteria: "Information security policy approved by senior leadership, communicated to all staff, reviewed periodically."
    },
    "A.5.2": {
        requirement: "Clearly assign roles and responsibilities for information security.",
        criteria: "RACI matrix exists for security roles: CISO, system administrators, end users."
    },
    "A.5.3": {
        requirement: "Conflicting duties and areas of responsibility must be segregated.",
        criteria: "No single individual controls an entire critical transaction. Approver differs from executor."
    },
    "A.5.4": {
        requirement: "Management requires staff and contractors to comply with information security policies.",
        criteria: "Written acknowledgment, security awareness training for managers."
    },
    "A.5.5": {
        requirement: "Establish and maintain contact with relevant authorities and functions.",
        criteria: "Contact list for police, CERT, telecommunications regulators maintained."
    },
    "A.5.6": {
        requirement: "Maintain contact with special interest groups and security forums.",
        criteria: "Active membership in security communities, monitoring of security advisories."
    },
    "A.5.7": {
        requirement: "Collect and analyze information about information security threats.",
        criteria: "Process for ingesting and processing Threat Intelligence feeds."
    },
    "A.5.8": {
        requirement: "Integrate information security into project management.",
        criteria: "Each project has security risk assessment and security requirements from design phase."
    },
    "A.5.9": {
        requirement: "Establish and maintain an inventory of information assets (with owners).",
        criteria: "Asset inventory maintained and classified: hardware, software, data, people."
    },
    "A.5.10": {
        requirement: "Rules for acceptable use of information assets must be defined and documented.",
        criteria: "Acceptable Use Policy in place and acknowledged."
    },
    "A.5.11": {
        requirement: "Staff and external parties must return assets upon contract termination.",
        criteria: "Offboarding procedure includes IT asset return checklist."
    },
    "A.5.12": {
        requirement: "Information must be classified by value, legal requirements, and sensitivity.",
        criteria: "3-4 classification levels: Public, Internal, Confidential, Top Secret."
    },
    "A.5.13": {
        requirement: "Information must be labeled in accordance with the classification scheme.",
        criteria: "Documents have classification watermark/header; emails are tagged with confidentiality level."
    },
    "A.5.14": {
        requirement: "Rules and procedures for transferring information across all media types.",
        criteria: "Encrypted email for sensitive data, VPN for transit, USB restrictions."
    },
    "A.5.15": {
        requirement: "Establish and implement physical and logical access control policies.",
        criteria: "Need-to-know and Least Privilege principles applied."
    },
    "A.5.16": {
        requirement: "Manage the full identity lifecycle.",
        criteria: "Identity & Access Management (IAM) system with unique account per person."
    },
    "A.5.17": {
        requirement: "Use authentication technologies appropriate to sensitivity level.",
        criteria: "MFA for critical systems; strong password policy (12+ characters)."
    },
    "A.5.18": {
        requirement: "Provision, review, modify, and revoke access rights according to policy.",
        criteria: "Periodic access review (at least every 6 months); immediate revocation on departure."
    },
    "A.5.19": {
        requirement: "Identify and implement controls to manage supplier-related risks.",
        criteria: "Security clauses in supplier contracts; supplier risk assessments."
    },
    "A.5.20": {
        requirement: "Information security requirements included in supplier agreements.",
        criteria: "NDAs, security SLAs, audit rights."
    },
    "A.5.21": {
        requirement: "Manage information security risks in the ICT supply chain.",
        criteria: "Software supplier security assessments; third-party code review."
    },
    "A.5.22": {
        requirement: "Monitor, review, evaluate, and manage changes in supplier services.",
        criteria: "Periodic supplier reports; reassessment when changes occur."
    },
    "A.5.23": {
        requirement: "Establish information security management process for cloud services.",
        criteria: "Cloud Security Policy, CSP assessment, cloud data encryption."
    },
    "A.5.24": {
        requirement: "Plan and prepare for information security incident management.",
        criteria: "Incident Response Plan, CSIRT/SOC team, annual incident drills."
    },
    "A.5.25": {
        requirement: "Assess security events and decide whether they are incidents.",
        criteria: "Event classification process and severity scoring."
    },
    "A.5.26": {
        requirement: "Respond to incidents according to established procedures.",
        criteria: "Escalation procedures, response time SLAs, incident logging."
    },
    "A.5.27": {
        requirement: "Knowledge from incidents is used to improve preventive controls.",
        criteria: "Post-incident reviews; updates to preventive measures."
    },
    "A.5.28": {
        requirement: "Establish procedures for collecting and preserving digital evidence.",
        criteria: "Chain of custody, log preservation, forensic readiness."
    },
    "A.5.29": {
        requirement: "Maintain information security during business disruption.",
        criteria: "Business Continuity Plan (BCP) includes security requirements."
    },
    "A.5.30": {
        requirement: "Ensure ICT readiness for business continuity.",
        criteria: "DR Plan, defined RTO/RPO, tested backups, failover procedures."
    },
    "A.5.31": {
        requirement: "Identify and comply with applicable legal requirements for information security.",
        criteria: "List of applicable laws/regulations: Vietnam Cybersecurity Law, PDPA, GDPR if applicable."
    },
    "A.5.32": {
        requirement: "Protect intellectual property rights.",
        criteria: "Software license management; copyright compliance checks."
    },
    "A.5.33": {
        requirement: "Protect records from loss, destruction, and falsification.",
        criteria: "Records retention policy, retention periods, encryption."
    },
    "A.5.34": {
        requirement: "Comply with privacy regulations and PII protection requirements.",
        criteria: "DPIA, data processing consent, DPO if required."
    },
    "A.5.35": {
        requirement: "Independent reviews of information security at planned intervals.",
        criteria: "Annual internal audits, independent pentests, assessment reports."
    },
    "A.5.36": {
        requirement: "Periodic review of compliance with information security policies.",
        criteria: "Quarterly compliance checks, violation reporting."
    },
    "A.5.37": {
        requirement: "Document operating procedures.",
        criteria: "SOPs for IT operations, change management, backups."
    },

    // A.6 People Controls
    "A.6.1": {
        requirement: "Background checks on personnel before hiring.",
        criteria: "Background check, education verification, criminal record check."
    },
    "A.6.2": {
        requirement: "Employment contracts include information security responsibilities.",
        criteria: "NDA and confidentiality clauses in contracts."
    },
    "A.6.3": {
        requirement: "All personnel receive appropriate information security training.",
        criteria: "Annual training program, phishing simulations, awareness assessments."
    },
    "A.6.4": {
        requirement: "Disciplinary process for violations of information security policies.",
        criteria: "Clear, fair, and communicated disciplinary process."
    },
    "A.6.5": {
        requirement: "Information security responsibilities remain valid after contract termination.",
        criteria: "NDA remains in effect; account revocation within 24h."
    },
    "A.6.6": {
        requirement: "Confidentiality agreements with staff and external parties.",
        criteria: "Signed NDAs, periodically reviewed."
    },
    "A.6.7": {
        requirement: "Security measures for remote working.",
        criteria: "Mandatory VPN, BYOD policy, device encryption."
    },
    "A.6.8": {
        requirement: "Information security event reporting mechanism for staff.",
        criteria: "Clear reporting channels: hotline, email, ticketing system."
    },

    // A.7 Physical Controls
    "A.7.1": {
        requirement: "Define security perimeters protecting areas containing sensitive information.",
        criteria: "Walls, locked doors, fencing for data center and server rooms."
    },
    "A.7.2": {
        requirement: "Physical access control to secure areas.",
        criteria: "Smart card/biometric, entry/exit logs, visitor escort."
    },
    "A.7.3": {
        requirement: "Design and apply physical protection for offices.",
        criteria: "Lockable cabinets, clean desk policy, surveillance cameras."
    },
    "A.7.4": {
        requirement: "Continuous monitoring of sensitive areas.",
        criteria: "24/7 CCTV, retention at least 30 days, real-time monitoring."
    },
    "A.7.5": {
        requirement: "Protection against natural disasters, fire, flood, power loss.",
        criteria: "UPS, backup generators, automatic fire suppression, climate control."
    },
    "A.7.6": {
        requirement: "Working procedures in secure areas.",
        criteria: "Recording devices prohibited, staff supervision, restricted access numbers."
    },
    "A.7.7": {
        requirement: "Clean desk and clear screen policy.",
        criteria: "Auto screen lock after 5 minutes, lockable cabinets for documents."
    },
    "A.7.8": {
        requirement: "Place equipment in safe locations protected from risk.",
        criteria: "Lockable server racks, tidy cabling, equipment labels."
    },
    "A.7.9": {
        requirement: "Protect off-premise assets.",
        criteria: "Laptop disk encryption, device tracking, insurance."
    },
    "A.7.10": {
        requirement: "Lifecycle management of storage media.",
        criteria: "USB/portable drive encryption; secure disposal (degaussing/shredding)."
    },
    "A.7.11": {
        requirement: "Protect equipment from power loss and utility failures.",
        criteria: "Backup power, redundant internet links."
    },
    "A.7.12": {
        requirement: "Protect power and network cabling.",
        criteria: "Cables in conduits, cable labels, fiber optics for backbone."
    },
    "A.7.13": {
        requirement: "Properly maintain equipment to ensure availability.",
        criteria: "Maintenance schedule, maintenance records, authorized personnel."
    },
    "A.7.14": {
        requirement: "Securely erase data before disposal/reuse of equipment.",
        criteria: "Data wiping procedure (DoD 5220.22-M or NIST 800-88)."
    },

    // A.8 Technological Controls
    "A.8.1": {
        requirement: "Protect information on user endpoints.",
        criteria: "Antivirus/EDR, disk encryption (BitLocker), GPO policy."
    },
    "A.8.2": {
        requirement: "Restrict and manage privileged access rights.",
        criteria: "PAM (Privileged Access Management), separate admin accounts, logging."
    },
    "A.8.3": {
        requirement: "Restrict access based on the access control policy.",
        criteria: "RBAC/ABAC, permissions based on Least Privilege."
    },
    "A.8.4": {
        requirement: "Control read/write access to source code.",
        criteria: "Git access control, code review, branch protection."
    },
    "A.8.5": {
        requirement: "Implement secure authentication mechanisms.",
        criteria: "HTTPS, certificate management, OAuth2/SAML."
    },
    "A.8.6": {
        requirement: "Monitor and manage resource capacity.",
        criteria: "Monitoring (CPU, RAM, Disk), capacity planning, alerting."
    },
    "A.8.7": {
        requirement: "Implement detection, prevention, and recovery from malware.",
        criteria: "Antivirus/EDR on all endpoints, email gateway filtering, sandbox."
    },
    "A.8.8": {
        requirement: "Identify, evaluate, and treat technical vulnerabilities.",
        criteria: "Periodic vulnerability scanning (Nessus/OpenVAS), patch management."
    },
    "A.8.9": {
        requirement: "Establish, document, implement, and monitor configurations.",
        criteria: "Baseline configuration, hardening guides (CIS Benchmarks)."
    },
    "A.8.10": {
        requirement: "Erase information when no longer needed.",
        criteria: "Data retention policy, secure deletion procedures."
    },
    "A.8.11": {
        requirement: "Mask data per access control policy.",
        criteria: "Data masking in test/dev environments, tokenization."
    },
    "A.8.12": {
        requirement: "Apply data leakage prevention measures.",
        criteria: "Endpoint and network DLP, monitoring of email/USB/cloud upload."
    },
    "A.8.13": {
        requirement: "Backup data, software, and system configurations per policy.",
        criteria: "3-2-1 backup (3 copies, 2 media, 1 offsite), quarterly restore tests."
    },
    "A.8.14": {
        requirement: "Information processing equipment must have redundancy for availability.",
        criteria: "High Availability (HA) for critical systems, failover cluster."
    },
    "A.8.15": {
        requirement: "Log and monitor activities, exceptions, errors, and security events.",
        criteria: "Centralized logging (SIEM), 12-month log retention, tamper-proof."
    },
    "A.8.16": {
        requirement: "Monitor networks, systems, and applications for anomalies.",
        criteria: "SOC/NOC, alert rules, incident correlation."
    },
    "A.8.17": {
        requirement: "Synchronize system clocks with a standard time source.",
        criteria: "Internal NTP server, all devices synchronized."
    },
    "A.8.18": {
        requirement: "Restrict and control use of privileged utility programs.",
        criteria: "Application whitelisting, logging admin tools usage."
    },
    "A.8.19": {
        requirement: "Software installation control procedures.",
        criteria: "Approved software list, admin rights control."
    },
    "A.8.20": {
        requirement: "Protect, manage, and control networks to safeguard information.",
        criteria: "Firewall, network segmentation, VLAN, ACL."
    },
    "A.8.21": {
        requirement: "Identify, implement, and monitor security mechanisms for network services.",
        criteria: "ISP SLAs, redundant connectivity, IDS/IPS."
    },
    "A.8.22": {
        requirement: "Segregate networks by service group, user, system.",
        criteria: "DMZ for public servers, separate VLANs for server/user/management/guest."
    },
    "A.8.23": {
        requirement: "Manage web access to reduce risk.",
        criteria: "Web filtering proxy, blocking dangerous categories."
    },
    "A.8.24": {
        requirement: "Use cryptography correctly including key management.",
        criteria: "TLS 1.2+ in transit, AES-256 at rest, certificate management."
    },
    "A.8.25": {
        requirement: "Establish secure development rules for software/systems.",
        criteria: "Security-integrated SDLC (SAST/DAST), code review, penetration testing."
    },
    "A.8.26": {
        requirement: "Identify and approve security requirements when developing/acquiring applications.",
        criteria: "Security requirements in user stories, threat modeling."
    },
    "A.8.27": {
        requirement: "Establish secure system architecture principles.",
        criteria: "Defense in depth, Zero Trust architecture principles."
    },
    "A.8.28": {
        requirement: "Apply secure coding principles.",
        criteria: "OWASP Top 10, input validation, parameterized queries."
    },
    "A.8.29": {
        requirement: "Conduct security testing during development.",
        criteria: "Security unit tests, SAST/DAST, pre-go-live pentest."
    },
    "A.8.30": {
        requirement: "Monitor outsourced software development activities.",
        criteria: "Code audit, NDA, security checks of received products."
    },
    "A.8.31": {
        requirement: "Separate dev/test/production environments.",
        criteria: "Distinct environments, no real data used in test."
    },
    "A.8.32": {
        requirement: "Change control for systems/applications.",
        criteria: "Change management process, CAB review, rollback plan."
    },
    "A.8.33": {
        requirement: "Protect data used for testing.",
        criteria: "Test data masking, no real PII used."
    },
    "A.8.34": {
        requirement: "Plan audits to minimize disruption.",
        criteria: "Audit schedule, read-only auditor access, audit activity monitoring."
    },

    // === TCVN 11930:2017 Controls ===

    // Network Security
    "NW.01": {
        requirement: "Control access between network zones using ACLs.",
        criteria: "Network devices have clear ACL configuration, default passwords changed, access logging."
    },
    "NW.02": {
        requirement: "Deploy firewalls protecting the network perimeter.",
        criteria: "Firewall at perimeter, rule set reviewed periodically, default-deny policy."
    },
    "NW.03": {
        requirement: "Deploy intrusion detection/prevention systems (IDS/IPS).",
        criteria: "IDS/IPS active, signatures updated, alert handling procedure in place."
    },
    "NW.04": {
        requirement: "Encrypt remote access traffic via VPN.",
        criteria: "VPN for all remote connections, AES-256 encryption, certificate-based authentication."
    },
    "NW.05": {
        requirement: "Separate public (DMZ) and internal network zones.",
        criteria: "Dedicated DMZ for Web/Mail servers, firewall between DMZ and LAN."
    },
    "NW.06": {
        requirement: "MAC address filtering (Port Security) on switches.",
        criteria: "Port security enabled, MAC limits per port, alerts for unauthorized devices."
    },
    "NW.07": {
        requirement: "Network Access Control (NAC) management.",
        criteria: "NAC checks compliance before allowing connection; quarantines violating devices."
    },
    "NW.08": {
        requirement: "Redundant physical network paths (for systems Level 4, 5).",
        criteria: "Dual ISP, physically diverse cable paths, automatic failover."
    },

    // Server Security
    "SV.01": {
        requirement: "Set complex passwords and disable unnecessary services.",
        criteria: "12+ character passwords with special chars + numbers, SSH root disabled, redundant ports closed."
    },
    "SV.02": {
        requirement: "Install antivirus software on servers.",
        criteria: "Antivirus active, automatic signature updates, real-time scanning."
    },
    "SV.03": {
        requirement: "Deploy host intrusion prevention systems (EDR/XDR).",
        criteria: "EDR on all servers, threat detection, auto-response rules."
    },
    "SV.04": {
        requirement: "File Integrity Monitoring (FIM).",
        criteria: "FIM active on critical system files, real-time alerts on changes."
    },
    "SV.05": {
        requirement: "Privileged Access Management (PAM) on servers.",
        criteria: "Separate admin accounts, session recording, just-in-time access."
    },
    "SV.06": {
        requirement: "Multi-Factor Authentication (MFA) for root/admin.",
        criteria: "MFA required for SSH/RDP admin, OTP or hardware key."
    },
    "SV.07": {
        requirement: "Periodic security patch management.",
        criteria: "Critical patches within 72h, others within 30 days, tested before applying."
    },
    "SV.08": {
        requirement: "Secure configuration (Hardening per CIS Benchmark).",
        criteria: "CIS Benchmark score > 80%, redundant services disabled, audit policy in place."
    },

    // Application Security
    "APP.01": {
        requirement: "Encrypt passwords in databases using safe algorithms.",
        criteria: "Bcrypt/Argon2 for passwords, no MD5/SHA1, unique salt per record."
    },
    "APP.02": {
        requirement: "Secure connections via HTTPS/TLS 1.2 or higher.",
        criteria: "TLS 1.2+, valid certificate, HSTS enabled, TLS 1.0/1.1 disabled."
    },
    "APP.03": {
        requirement: "Validate user input (prevent SQLi, XSS).",
        criteria: "Input validation, parameterized queries, output encoding, CSP header."
    },
    "APP.04": {
        requirement: "Limit session lifetime (Session Timeout).",
        criteria: "Session timeout 15-30 minutes, secure/httponly cookie flags."
    },
    "APP.05": {
        requirement: "Prevent web attacks via WAF (Web Application Firewall).",
        criteria: "WAF active, OWASP CRS ruleset, custom application rules."
    },
    "APP.06": {
        requirement: "Source code security assessment (SAST/DAST) before production.",
        criteria: "SAST in CI/CD pipeline, DAST before each release, all Critical issues fixed."
    },
    "APP.07": {
        requirement: "Automatic access logging (Audit Log).",
        criteria: "Log all data changes (Insert/Update/Delete), who/when/what, tamper-proof."
    },

    // Data Security
    "DAT.01": {
        requirement: "Periodic backup of critical data.",
        criteria: "Daily backup, weekly full backup, quarterly restore tests."
    },
    "DAT.02": {
        requirement: "Need-to-know access permissions (least privilege).",
        criteria: "RBAC, periodic permission review, audit trail for sensitive data access."
    },
    "DAT.03": {
        requirement: "Automated 3-2-1 backup system.",
        criteria: "3 copies, 2 different media, 1 offsite/cloud, defined RPO/RTO."
    },
    "DAT.04": {
        requirement: "Encrypt sensitive data at rest (Encryption at Rest).",
        criteria: "TDE for databases, BitLocker/LUKS for disks, key management policy."
    },
    "DAT.05": {
        requirement: "Deploy Data Loss Prevention (DLP) systems.",
        criteria: "Endpoint + network DLP, monitoring USB/email/cloud upload, alert & block."
    },
    "DAT.06": {
        requirement: "Equipment disposal/recycling procedures ensure physical data destruction.",
        criteria: "Data wiping (NIST 800-88), HDD degaussing, SSD shredding."
    },

    // Management
    "MNG.01": {
        requirement: "Issue an information security policy approved by senior management.",
        criteria: "Written security policy, executive-level approval, organization-wide communication."
    },
    "MNG.02": {
        requirement: "Designated information security personnel.",
        criteria: "Independent security function or dedicated officer, reporting directly to leadership."
    },
    "MNG.03": {
        requirement: "Centralized monitoring and incident alerting (SIEM/SOC).",
        criteria: "SIEM running 24/7, correlation rules, alert escalation, monthly reports."
    },
    "MNG.04": {
        requirement: "Incident response procedures and annual security drills.",
        criteria: "Incident Response Plan, at least 1 drill per year, results reported."
    },
    "MNG.05": {
        requirement: "Periodic third-party risk assessments (Pentest).",
        criteria: "Annual pentest by independent provider, fix timeline tracked, retest."
    }
}
