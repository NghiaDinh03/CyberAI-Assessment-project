# Incident Response Plan
## Document Control

| Field | Value |
|-------|-------|
| **Document ID** | ISMS-IRP-001 |
| **Version** | 3.0 |
| **Classification** | Confidential |
| **Owner** | CISO / Incident Response Team Lead |
| **Last updated** | 2025-02-10 |

---

## 1. Purpose

This Incident Response Plan (IRP) establishes procedures for detecting, responding to, and recovering from information security incidents. It implements controls **A.5.24** (Incident Management Planning), **A.5.25** (Assessment of Security Events), **A.5.26** (Response to Incidents), **A.5.27** (Learning from Incidents), and **A.5.28** (Evidence Collection) of ISO/IEC 27001:2022.

## 2. Incident Classification

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| **P1 — Critical** | Data breach, ransomware, system-wide outage | 15 minutes | CISO + CEO + Legal |
| **P2 — High** | Targeted attack, partial service disruption | 1 hour | CISO + IT Director |
| **P3 — Medium** | Malware on single endpoint, policy violation | 4 hours | IT Security Manager |
| **P4 — Low** | Phishing attempt (blocked), minor policy deviation | 24 hours | SOC Team Lead |

## 3. Incident Response Team (IRT)

| Role | Primary | Backup | Contact |
|------|---------|--------|---------|
| IRT Lead | CISO | Deputy CISO | ext. 1001 |
| Technical Lead | Sr. Security Engineer | SOC Lead | ext. 1002 |
| Communications | PR Director | Marketing VP | ext. 1003 |
| Legal Counsel | General Counsel | External firm | ext. 1004 |
| HR Representative | HR Director | HR Manager | ext. 1005 |
| IT Operations | IT Director | Sr. SysAdmin | ext. 1006 |

## 4. Response Phases

### Phase 1: Detection & Triage (0–15 min)

1. SOC receives alert from SIEM / EDR / user report
2. SOC analyst validates alert (true positive vs. false positive)
3. Classify severity (P1–P4) using criteria in Section 2
4. Create incident ticket in ServiceNow (INC-YYYY-NNNN)
5. Notify IRT Lead if P1 or P2

### Phase 2: Containment (15 min – 4 hours)

**Short-term containment:**
- Isolate affected systems from network (EDR network quarantine)
- Block malicious IPs/domains at firewall
- Disable compromised accounts
- Preserve volatile evidence (memory dumps, running processes)

**Long-term containment:**
- Apply emergency patches
- Redirect traffic to clean systems
- Implement additional monitoring on affected segments

### Phase 3: Eradication (4–48 hours)

- Remove malware/backdoors from all affected systems
- Reset all potentially compromised credentials
- Patch exploited vulnerabilities
- Verify removal with full system scan

### Phase 4: Recovery (1–5 days)

- Restore systems from verified clean backups
- Gradually reconnect to production network
- Monitor for re-infection indicators (30-day watch period)
- Validate system integrity before full service restoration

### Phase 5: Post-Incident Review (within 5 business days)

- Conduct post-mortem meeting with all IRT members
- Document timeline, root cause, and lessons learned
- Update detection rules and response procedures
- File regulatory notifications if required (GDPR: 72 hours)

## 5. Evidence Collection (A.5.28)

### 5.1 Digital Forensics Procedures

| Evidence Type | Collection Method | Storage | Chain of Custody |
|--------------|-------------------|---------|-----------------|
| Memory dumps | WinPMEM / LiME | Encrypted USB → Evidence vault | Hash + timestamp + collector |
| Disk images | FTK Imager (write-blocked) | Evidence server (encrypted) | Hash + timestamp + collector |
| Network captures | tcpdump / Wireshark | SIEM archive | Automated |
| Log files | SIEM export (tamper-proof) | Log archive (WORM) | Automated |
| Email evidence | eDiscovery hold (M365) | Compliance center | Legal hold notice |

### 5.2 Chain of Custody Form

All physical and digital evidence must be logged with:
- Evidence ID, description, and classification
- Date/time of collection
- Collector name and role
- Hash values (SHA-256) at time of collection
- Storage location and access log
- Transfer records (if moved between custodians)

## 6. Communication Plan

| Audience | Channel | Timing | Responsible |
|----------|---------|--------|-------------|
| IRT members | Secure Teams channel + phone | Immediate | IRT Lead |
| Executive team | Email + briefing | Within 1 hour (P1/P2) | CISO |
| All employees | Intranet notice | Within 24 hours (if needed) | Communications |
| Customers | Email + website notice | Per regulatory requirement | Legal + Communications |
| Regulators | Formal notification | Within 72 hours (GDPR) | Legal Counsel |
| Media | Press statement | Only if public disclosure required | PR Director |

## 7. Testing & Exercises

| Exercise Type | Frequency | Last Conducted | Next Scheduled |
|--------------|-----------|----------------|----------------|
| Tabletop exercise | Quarterly | 2025-01-25 | 2025-04-25 |
| Technical drill (red team) | Semi-annually | 2024-11-15 | 2025-05-15 |
| Full simulation | Annually | 2024-09-20 | 2025-09-20 |
| Communication test | Quarterly | 2025-02-10 | 2025-05-10 |

## 8. Metrics

| KPI | Target | Actual (2025 Q1) | Status |
|-----|--------|-------------------|--------|
| Mean time to detect (MTTD) | < 30 min | 22 min | ✅ |
| Mean time to respond (MTTR) | < 4 hours | 2.5 hours | ✅ |
| Incidents per quarter | < 10 | 7 | ✅ |
| Post-mortem completion rate | 100% | 100% | ✅ |
| False positive rate | < 15% | 11% | ✅ |

---

*This is a sample evidence document for demonstration purposes.*
