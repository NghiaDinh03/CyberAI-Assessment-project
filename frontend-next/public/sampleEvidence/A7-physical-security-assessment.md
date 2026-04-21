# Physical Security Assessment Report
## Document Control

| Field | Value |
|-------|-------|
| **Document ID** | ISMS-PHY-001 |
| **Version** | 1.4 |
| **Classification** | Confidential |
| **Owner** | Facilities Manager & CISO |
| **Last updated** | 2025-01-30 |

---

## 1. Purpose

This report documents the physical security controls in place at all organizational facilities, implementing controls **A.7.1–A.7.14** of ISO/IEC 27001:2022 Annex A.

## 2. Facility Overview

| Facility | Type | Classification | Staff |
|----------|------|---------------|-------|
| HQ Building (Floor 5–8) | Office + Data Center | Restricted Zone | 250 |
| Branch Office A | Office | Internal Zone | 45 |
| DR Site | Data Center | Restricted Zone | 5 (on-site) |

## 3. Physical Access Controls (A.7.1–A.7.2)

### 3.1 Security Perimeters

| Zone | Access Method | Monitoring | Log Retention |
|------|-------------|------------|---------------|
| Building Entrance | Badge + PIN | CCTV 24/7 | 90 days |
| Office Floors | Badge | CCTV | 90 days |
| Server Room | Badge + Biometric + PIN | CCTV + Motion | 180 days |
| Network Closets | Key Lock + Badge | CCTV | 90 days |
| Executive Suite | Badge + Biometric | CCTV | 90 days |

### 3.2 Visitor Management

- All visitors must register at reception with government-issued ID
- Visitor badges issued with photo, date, and host name
- Escorts required for all restricted zones
- Visitor log reviewed weekly by Facilities Manager
- Visitor badges automatically expire at end of business day

## 4. CCTV Surveillance (A.7.4)

| Location | Cameras | Resolution | Storage | Monitored |
|----------|---------|------------|---------|-----------|
| Building perimeter | 12 | 4K | 90 days NVR | 24/7 SOC |
| Lobby & corridors | 8 | 1080p | 90 days NVR | 24/7 SOC |
| Server room | 4 | 4K | 180 days NVR | 24/7 SOC + motion alerts |
| Parking garage | 6 | 1080p | 30 days NVR | Business hours |

**Total cameras**: 30 | **NVR capacity**: 120TB | **Backup**: Cloud archive (encrypted)

## 5. Environmental Controls (A.7.5)

### 5.1 Data Center Environment

| Control | Specification | Redundancy | Last Test |
|---------|--------------|------------|-----------|
| HVAC | Precision cooling, 20–22°C | N+1 | 2025-01-15 |
| Fire suppression | FM-200 gas + VESDA early detection | Dual zone | 2024-12-20 |
| UPS | 30 kVA, 15 min runtime | N+1 | 2025-01-10 |
| Generator | 200 kW diesel, 48h fuel | Single | 2024-11-30 |
| Water detection | Under-floor sensors | — | 2025-01-15 |
| Temperature monitoring | IoT sensors, alerts at 25°C | — | Continuous |

### 5.2 Natural Disaster Preparedness

- Seismic zone assessment: Low risk (Zone 1)
- Flood risk: Building elevated 2m above 100-year flood level
- Lightning protection: Faraday cage + surge protectors on all power feeds
- Emergency evacuation drills: Conducted quarterly (last: 2025-02-15)

## 6. Clean Desk & Clear Screen (A.7.7)

- Policy enforced via random spot checks (monthly)
- Automatic screen lock after 5 minutes of inactivity (GPO enforced)
- Shredders available on every floor
- Last audit: 2025-02-28 — **94% compliance** (6 minor findings, all remediated)

## 7. Equipment Security (A.7.8–A.7.14)

- All laptops encrypted with BitLocker (TPM + PIN)
- USB ports disabled via endpoint policy (exceptions require CISO approval)
- Equipment disposal via certified ITAD vendor (certificates retained 5 years)
- Cabling: Structured cabling in locked conduits; fiber for inter-floor links

---

*This is a sample evidence document for demonstration purposes.*
