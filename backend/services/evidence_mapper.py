"""Evidence-to-control mapper — matches uploaded evidence files to ISO/TCVN controls.

Uses filename patterns and content keyword matching to automatically associate
evidence documents with relevant control IDs. This enables the assessment
pipeline to inject the right evidence into each control group's prompt.

Usage::

    from services.evidence_mapper import map_evidence_to_controls
    mapping = map_evidence_to_controls(filename, text_preview)
    # Returns: {"A.5.1": 0.9, "A.5.2": 0.7, ...}  (control_id -> relevance score)
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Filename pattern -> list of (control_id, confidence)
_FILENAME_RULES: List[tuple] = [
    # Policies
    ("policy", [("A.5.1", 0.9), ("A.5.2", 0.7)]),
    ("chinh_sach", [("A.5.1", 0.9), ("A.5.2", 0.7)]),
    ("chính_sách", [("A.5.1", 0.9), ("A.5.2", 0.7)]),
    ("policy_security", [("A.5.1", 0.95)]),

    # Access control
    ("access", [("A.5.15", 0.8), ("A.5.16", 0.7)]),
    ("truy_cap", [("A.5.15", 0.8), ("A.5.16", 0.7)]),
    ("phan_quyen", [("A.5.15", 0.8), ("A.5.18", 0.7)]),
    ("iam", [("A.5.16", 0.9)]),
    ("mfa", [("A.5.17", 0.9), ("A.8.5", 0.9)]),
    ("xác_thực", [("A.5.17", 0.9)]),

    # Firewall / Network
    ("firewall", [("A.8.20", 0.9), ("NW.02", 0.9)]),
    ("tuong_lua", [("A.8.20", 0.9), ("NW.02", 0.9)]),
    ("tường_lửa", [("A.8.20", 0.9), ("NW.02", 0.9)]),
    ("network", [("A.8.20", 0.6), ("A.8.21", 0.6), ("A.8.22", 0.6)]),
    ("mang", [("A.8.20", 0.6), ("NW.01", 0.6)]),
    ("vpn", [("NW.04", 0.9)]),
    ("vlan", [("A.8.22", 0.8), ("NW.05", 0.8)]),
    ("dmz", [("A.8.22", 0.8), ("NW.05", 0.9)]),

    # Backup / Recovery
    ("backup", [("A.8.13", 0.9), ("DAT.01", 0.9)]),
    ("sao_luu", [("A.8.13", 0.9), ("DAT.01", 0.9)]),
    ("sao_lưu", [("A.8.13", 0.9), ("DAT.01", 0.9)]),
    ("recovery", [("A.8.13", 0.7), ("A.8.14", 0.7)]),
    ("phuc_hoi", [("A.8.13", 0.7), ("A.8.14", 0.7)]),
    ("drp", [("A.5.30", 0.9)]),
    ("bcp", [("A.5.29", 0.9)]),

    # Training
    ("training", [("A.6.3", 0.9)]),
    ("dao_tao", [("A.6.3", 0.9)]),
    ("đào_tạo", [("A.6.3", 0.9)]),
    ("awareness", [("A.6.3", 0.8)]),
    ("nhan_thuc", [("A.6.3", 0.8)]),

    # Encryption
    ("encrypt", [("A.8.24", 0.9), ("DAT.04", 0.9)]),
    ("ma_hoa", [("A.8.24", 0.9), ("DAT.04", 0.9)]),
    ("mã_hóa", [("A.8.24", 0.9), ("DAT.04", 0.9)]),
    ("tls", [("APP.02", 0.9)]),
    ("ssl", [("APP.02", 0.9)]),

    # Vulnerability / Patch
    ("vulnerability", [("A.8.8", 0.9)]),
    ("lo_hong", [("A.8.8", 0.9)]),
    ("lỗ_hổng", [("A.8.8", 0.9)]),
    ("patch", [("SV.07", 0.9)]),
    ("ban_va", [("SV.07", 0.9)]),
    ("bản_vá", [("SV.07", 0.9)]),
    ("pentest", [("A.8.29", 0.9), ("MNG.05", 0.9)]),

    # Logging / SIEM / Monitoring
    ("logging", [("A.8.15", 0.9), ("MNG.03", 0.8)]),
    ("audit_log", [("A.8.15", 0.9), ("APP.07", 0.9)]),
    ("siem", [("A.8.15", 0.9), ("A.8.16", 0.8), ("MNG.03", 0.9)]),
    ("soc", [("A.8.16", 0.9), ("MNG.03", 0.9)]),
    ("monitoring", [("A.8.16", 0.9)]),
    ("giam_sat", [("A.8.16", 0.8)]),

    # Incident
    ("incident", [("A.5.24", 0.8), ("A.5.25", 0.8), ("A.5.26", 0.8)]),
    ("su_co", [("A.5.24", 0.8), ("A.5.25", 0.8), ("A.5.26", 0.8)]),
    ("sự_cố", [("A.5.24", 0.8), ("A.5.25", 0.8), ("A.5.26", 0.8)]),
    ("incident_response", [("A.5.26", 0.9), ("MNG.04", 0.9)]),

    # Endpoint / Antivirus
    ("antivirus", [("A.8.7", 0.9), ("SV.02", 0.9)]),
    ("edr", [("A.8.7", 0.9), ("SV.03", 0.9)]),
    ("endpoint", [("A.8.1", 0.8)]),

    # Physical security
    ("physical", [("A.7.1", 0.7), ("A.7.2", 0.7)]),
    ("vat_ly", [("A.7.1", 0.7), ("A.7.2", 0.7)]),
    ("vật_lý", [("A.7.1", 0.7), ("A.7.2", 0.7)]),
    ("cctv", [("A.7.4", 0.9)]),

    # Asset management
    ("asset", [("A.5.9", 0.8), ("A.5.10", 0.7)]),
    ("tai_san", [("A.5.9", 0.8)]),
    ("cmdb", [("A.5.9", 0.9)]),

    # Compliance / Legal
    ("compliance", [("A.5.31", 0.7), ("A.5.35", 0.7)]),
    ("tuân_thủ", [("A.5.31", 0.7)]),
    ("legal", [("A.5.31", 0.8)]),
    ("phap_ly", [("A.5.31", 0.8)]),

    # DLP
    ("dlp", [("A.8.12", 0.9), ("DAT.05", 0.9)]),

    # Hardening / Configuration
    ("hardening", [("A.8.9", 0.9), ("SV.08", 0.9)]),
    ("cis", [("A.8.9", 0.8), ("SV.08", 0.8)]),
    ("configuration", [("A.8.9", 0.7)]),

    # Change management
    ("change_management", [("A.8.32", 0.9)]),
    ("quan_ly_thay_doi", [("A.8.32", 0.9)]),

    # NDA / Supplier
    ("nda", [("A.5.20", 0.8), ("A.6.6", 0.8)]),
    ("supplier", [("A.5.19", 0.8), ("A.5.20", 0.8)]),
    ("nha_cung_cap", [("A.5.19", 0.8), ("A.5.20", 0.8)]),
    ("cloud_security", [("A.5.23", 0.9)]),
]

# Content keywords -> control IDs (checked against first 500 chars of content)
_CONTENT_KEYWORDS: Dict[str, List[tuple]] = {
    "chính sách": [("A.5.1", 0.7)],
    "policy": [("A.5.1", 0.6)],
    "phân quyền": [("A.5.15", 0.7), ("A.5.18", 0.6)],
    "truy cập": [("A.5.15", 0.6)],
    "firewall": [("A.8.20", 0.7)],
    "tường lửa": [("A.8.20", 0.7)],
    "sao lưu": [("A.8.13", 0.7)],
    "backup": [("A.8.13", 0.7)],
    "mã hóa": [("A.8.24", 0.7)],
    "encryption": [("A.8.24", 0.7)],
    "đào tạo": [("A.6.3", 0.7)],
    "training": [("A.6.3", 0.6)],
    "sự cố": [("A.5.24", 0.6), ("A.5.26", 0.6)],
    "incident": [("A.5.24", 0.6)],
    "lỗ hổng": [("A.8.8", 0.7)],
    "vulnerability": [("A.8.8", 0.7)],
    "nhật ký": [("A.8.15", 0.7)],
    "logging": [("A.8.15", 0.7)],
    "siem": [("A.8.15", 0.7), ("MNG.03", 0.7)],
    "xác thực": [("A.5.17", 0.7), ("A.8.5", 0.7)],
    "mật khẩu": [("SV.01", 0.7)],
    "password": [("SV.01", 0.6)],
    "bản vá": [("SV.07", 0.7)],
    "patch": [("SV.07", 0.7)],
    "chống mã độc": [("A.8.7", 0.7), ("SV.02", 0.7)],
    "antivirus": [("A.8.7", 0.7)],
    "giám sát": [("A.8.16", 0.6)],
    "monitoring": [("A.8.16", 0.6)],
}


def map_evidence_to_controls(
    filename: str,
    content_preview: str = "",
    *,
    max_controls: int = 10,
    min_confidence: float = 0.5,
) -> Dict[str, float]:
    """Map an evidence file to relevant control IDs.

    Args:
        filename: Original filename (used for pattern matching).
        content_preview: First ~500 chars of extracted text (used for keyword matching).
        max_controls: Maximum number of controls to return.
        min_confidence: Minimum confidence threshold.

    Returns:
        Dict mapping control_id -> confidence score (0.0 to 1.0).
        Sorted by confidence descending, limited to *max_controls* entries.
    """
    scores: Dict[str, float] = {}
    fname_lower = os.path.basename(filename or "").lower().replace(" ", "_")

    # Phase 1: Filename pattern matching
    for pattern, control_list in _FILENAME_RULES:
        if pattern in fname_lower:
            for ctrl_id, conf in control_list:
                scores[ctrl_id] = max(scores.get(ctrl_id, 0.0), conf)

    # Phase 2: Content keyword matching (first 500 chars)
    if content_preview:
        preview_lower = content_preview[:500].lower()
        for keyword, control_list in _CONTENT_KEYWORDS.items():
            if keyword in preview_lower:
                for ctrl_id, conf in control_list:
                    # Content match gets slightly lower confidence than filename match
                    adjusted_conf = conf * 0.9
                    scores[ctrl_id] = max(scores.get(ctrl_id, 0.0), adjusted_conf)

    # Filter by min_confidence and sort
    filtered = {k: v for k, v in scores.items() if v >= min_confidence}
    sorted_items = sorted(filtered.items(), key=lambda x: -x[1])[:max_controls]

    result = dict(sorted_items)
    if result:
        logger.info(
            "[EvidenceMapper] '%s' -> %d controls: %s",
            filename, len(result), list(result.keys())[:5],
        )
    return result


def score_evidence_quality(
    filename: str,
    content_text: str,
    file_age_days: Optional[int] = None,
) -> dict:
    """Score the quality of an evidence file for a given control.

    Returns dict with:
        completeness: 0.0-1.0 (how much useful content)
        freshness: 0.0-1.0 (how recent)
        relevance: 0.0-1.0 (placeholder — caller provides control context)
        overall: weighted average
    """
    # Completeness: based on text length
    text_len = len(content_text or "")
    if text_len > 2000:
        completeness = 1.0
    elif text_len > 500:
        completeness = 0.7
    elif text_len > 100:
        completeness = 0.4
    else:
        completeness = 0.1

    # Freshness: based on file age
    if file_age_days is None:
        freshness = 0.7  # unknown age — neutral
    elif file_age_days <= 90:
        freshness = 1.0
    elif file_age_days <= 180:
        freshness = 0.8
    elif file_age_days <= 365:
        freshness = 0.5
    else:
        freshness = 0.2  # > 1 year = outdated

    # Relevance: placeholder (will be filled by caller based on control match)
    relevance = 0.5

    overall = round(completeness * 0.4 + freshness * 0.3 + relevance * 0.3, 2)

    return {
        "completeness": round(completeness, 2),
        "freshness": round(freshness, 2),
        "relevance": round(relevance, 2),
        "overall": overall,
    }
