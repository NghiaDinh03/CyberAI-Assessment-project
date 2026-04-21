# Technology Security Controls — Configuration Baseline
## Document Control

| Field | Value |
|-------|-------|
| **Document ID** | ISMS-TECH-001 |
| **Version** | 2.3 |
| **Classification** | Confidential |
| **Owner** | IT Security Manager |
| **Last updated** | 2025-03-05 |

---

## 1. Purpose

This document defines the technology security baseline and evidence of implementation for controls **A.8.1–A.8.34** of ISO/IEC 27001:2022 Annex A, covering endpoint security, network protection, secure development, and data protection.

## 2. Endpoint Security (A.8.1–A.8.4)

### 2.1 Device Inventory

| Device Type | Count | OS | Management | Encryption |
|-------------|-------|-----|------------|------------|
| Workstations | 280 | Windows 11 Enterprise | Intune MDM | BitLocker (TPM+PIN) |
| Laptops | 150 | Windows 11 / macOS 14 | Intune / Jamf | BitLocker / FileVault |
| Servers (on-prem) | 45 | Ubuntu 22.04 LTS / RHEL 9 | Ansible + Puppet | LUKS |
| Servers (cloud) | 120 | Amazon Linux 2023 | Terraform + SSM | EBS encryption (AES-256) |
| Mobile devices | 95 | iOS 17 / Android 14 | Intune MAM | Device encryption |

### 2.2 Endpoint Protection

- **EDR**: CrowdStrike Falcon (all endpoints + servers)
- **Patch management**: WSUS + Intune (Windows), Jamf (macOS), Ansible (Linux)
- **Patch SLA**: Critical — 72 hours; High — 7 days; Medium — 30 days
- **Compliance rate** (March 2025): 97.2% patched within SLA

## 3. Network Security (A.8.20–A.8.22)

### 3.1 Network Segmentation

```
┌─────────────────────────────────────────────────┐
│                    INTERNET                       │
│                       │                           │
│              ┌────────┴────────┐                  │
│              │   Cloudflare    │                  │
│              │   WAF + DDoS   │                  │
│              └────────┬────────┘                  │
│                       │                           │
│              ┌────────┴────────┐                  │
│              │  DMZ (VLAN 10)  │                  │
│              │  Nginx RP, API  │                  │
│              └────────┬────────┘                  │
│                       │                           │
│         ┌─────────────┼─────────────┐            │
│         │             │             │            │
│  ┌──────┴──────┐ ┌────┴────┐ ┌─────┴─────┐     │
│  │ App Zone    │ │ DB Zone │ │ Mgmt Zone │     │
│  │ (VLAN 20)  │ │(VLAN 30)│ │ (VLAN 40) │     │
│  │ K8s, APIs  │ │ RDS,    │ │ SIEM,     │     │
│  │            │ │ Redis   │ │ Ansible   │     │
│  └────────────┘ └─────────┘ └───────────┘     │
└─────────────────────────────────────────────────┘
```

### 3.2 Firewall Rules Summary

| Source | Destination | Port | Protocol | Action |
|--------|------------|------|----------|--------|
| Internet | DMZ | 443 | HTTPS | Allow |
| DMZ | App Zone | 8080 | HTTP | Allow |
| App Zone | DB Zone | 5432, 6379 | TCP | Allow |
| Mgmt Zone | All Zones | 22 | SSH | Allow (with PAM) |
| All | Internet | * | * | Deny (except allowlisted) |

### 3.3 IDS/IPS

- **Suricata IDS** on all VLAN boundaries
- Rules updated daily from ET Pro + custom rules
- Alerts forwarded to Splunk SIEM
- Monthly tuning review to reduce false positives

## 4. Cryptography (A.8.24)

| Use Case | Algorithm | Key Length | Key Management |
|----------|-----------|------------|----------------|
| Data at rest | AES-256-GCM | 256-bit | AWS KMS / HashiCorp Vault |
| Data in transit | TLS 1.3 | ECDHE P-256 | Let's Encrypt (auto-renew) |
| Database encryption | AES-256-CBC | 256-bit | RDS managed keys |
| Email encryption | S/MIME | RSA-2048 | Internal CA |
| Code signing | RSA-SHA256 | 4096-bit | HashiCorp Vault |
| Backup encryption | AES-256 | 256-bit | Veeam managed + offline key |

## 5. Secure Development (A.8.25–A.8.29)

### 5.1 SDLC Security Gates

| Phase | Security Activity | Tool | Gate Criteria |
|-------|------------------|------|---------------|
| Design | Threat modeling | STRIDE / Microsoft TMT | All high risks mitigated |
| Code | SAST scan | SonarQube + Semgrep | 0 critical, 0 high |
| Build | Dependency scan | Snyk + Trivy | 0 critical CVEs |
| Test | DAST scan | OWASP ZAP | 0 critical findings |
| Deploy | Container scan | Trivy | Base image < 30 days old |
| Production | Penetration test | Annual (third-party) | All critical findings fixed |

### 5.2 Vulnerability Management

- **Scan frequency**: Weekly (internal), Monthly (external)
- **Remediation SLA**: Critical — 48h, High — 7 days, Medium — 30 days
- **Open vulnerabilities** (March 2025): 0 critical, 2 high (in remediation), 14 medium

## 6. Logging & Monitoring (A.8.15–A.8.16)

| Log Source | Destination | Retention | Alert Rules |
|-----------|-------------|-----------|-------------|
| Firewall logs | Splunk | 1 year | Blocked traffic anomalies |
| Server auth logs | Splunk | 1 year | Failed login > 5/min |
| Application logs | ELK Stack | 6 months | Error rate > 1% |
| Cloud audit trail | CloudTrail → S3 | 2 years | Root account usage |
| Database audit | RDS audit logs | 1 year | Schema changes, bulk exports |
| Endpoint EDR | CrowdStrike cloud | 1 year | Malware, lateral movement |

## 7. Backup & Recovery (A.8.13–A.8.14)

| System | RPO | RTO | Backup Method | Last Test |
|--------|-----|-----|---------------|-----------|
| Production DB | 1 hour | 4 hours | RDS automated + cross-region | 2025-02-15 |
| File servers | 4 hours | 8 hours | Veeam incremental | 2025-03-01 |
| Email (M365) | 24 hours | 4 hours | Veeam for M365 | 2025-01-20 |
| Source code | Real-time | 1 hour | Git (3 remotes) | N/A (continuous) |

---

*This is a sample evidence document for demonstration purposes.*
