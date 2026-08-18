# Access Control Matrix
## Document Control

| Field | Value |
|-------|-------|
| **Document ID** | ISMS-ACM-001 |
| **Version** | 2.1 |
| **Classification** | Confidential |
| **Owner** | IT Security Manager |
| **Last updated** | 2025-03-10 |

---

## 1. Purpose

This Access Control Matrix defines the authorization levels for all critical information systems. It implements controls **A.5.15** (Access Control), **A.5.16** (Identity Management), **A.5.17** (Authentication), and **A.5.18** (Access Rights) of ISO/IEC 27001:2022 Annex A.

## 2. System Access Matrix

### 2.1 ERP System (SAP S/4HANA)

| Role | Module | Access Level | MFA Required | Approval |
|------|--------|-------------|--------------|----------|
| Finance Manager | FI/CO | Read/Write | Yes | CFO |
| HR Manager | HCM | Read/Write | Yes | CHRO |
| IT Admin | BASIS | Full Admin | Yes + Hardware Token | CIO + CISO |
| Auditor | All | Read Only | Yes | CISO |
| General Staff | Self-Service | Read Only | Yes | Line Manager |

### 2.2 Cloud Infrastructure (AWS)

| Role | Service Scope | IAM Policy | MFA Required |
|------|--------------|------------|--------------|
| Cloud Architect | All services | PowerUserAccess | Yes + YubiKey |
| DevOps Engineer | ECS, RDS, S3, CloudWatch | Custom-DevOps | Yes |
| Developer | CodeCommit, ECR, CloudWatch Logs | Custom-Dev-ReadOnly | Yes |
| Security Analyst | GuardDuty, SecurityHub, CloudTrail | SecurityAudit | Yes + YubiKey |
| Billing Admin | Billing, Cost Explorer | Billing | Yes |

### 2.3 Network Infrastructure

| Role | Device Access | Protocol | Authentication |
|------|--------------|----------|---------------|
| Network Admin | All switches/routers/firewalls | SSH + HTTPS | RADIUS + MFA |
| SOC Analyst | SIEM, IDS/IPS (read-only) | HTTPS | LDAP + MFA |
| Help Desk | Switch port management only | HTTPS | LDAP |

## 3. Privileged Access Management (PAM)

- All privileged accounts are managed through **CyberArk PAM**
- Session recording enabled for all admin sessions
- Privileged credentials rotated every **90 days** (automated)
- Break-glass accounts sealed; usage triggers immediate alert to SOC
- Quarterly access review conducted by CISO office

## 4. Access Review Schedule

| Review Type | Frequency | Reviewer | Last Completed |
|-------------|-----------|----------|----------------|
| User access recertification | Quarterly | Department Heads | 2025-03-01 |
| Privileged access review | Monthly | CISO | 2025-03-15 |
| Service account audit | Semi-annually | IT Security | 2025-01-20 |
| Third-party access review | Quarterly | Vendor Management | 2025-02-28 |

## 5. Account Lifecycle

1. **Provisioning**: HR triggers account creation via ServiceNow → auto-provisioned via AD + SCIM
2. **Modification**: Change request → manager approval → IT Security review → implemented within 4 hours
3. **Deprovisioning**: Offboarding ticket → all access revoked within **2 hours** of termination notice
4. **Dormant accounts**: Disabled after 30 days of inactivity; deleted after 90 days

---

*This is a sample evidence document for demonstration purposes.*
