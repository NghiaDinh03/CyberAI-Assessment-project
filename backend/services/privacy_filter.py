"""Privacy filter — strips PII from evidence text before sending to cloud APIs.

Patterns are tailored for Vietnamese organizations (phone numbers, ID cards,
emails, internal IPs, API keys, hostnames).  The filter is applied:
- **Always** before cloud API calls (mandatory).
- **Optionally** before local model calls (configurable).

Usage::

    from services.privacy_filter import filter_pii
    safe_text = filter_pii(raw_text, mode="cloud")
"""

from __future__ import annotations

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Each pattern: (compiled_regex, replacement_label)
_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Vietnamese phone numbers: 0[3-9]XXXXXXXX
    (re.compile(r'\b0[3-9]\d{8}\b'), '[SĐT]'),
    # International format: +84[3-9]XXXXXXXX
    (re.compile(r'\+84[3-9]\d{8}\b'), '[SĐT]'),

    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),

    # Vietnamese ID (CCCD/CMND): 9 or 12 digits
    (re.compile(r'\b\d{9}\b'), '[CMND]'),
    (re.compile(r'\b\d{12}\b'), '[CCCD]'),

    # Internal/private IP addresses (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
    (re.compile(r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '[IP]'),
    (re.compile(r'\b172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b'), '[IP]'),
    (re.compile(r'\b192\.168\.\d{1,3}\.\d{1,3}\b'), '[IP]'),

    # API keys / tokens (common patterns: sk-, ghp_, gsk_, AKIA, Bearer)
    (re.compile(r'\b(sk-[A-Za-z0-9]{20,})\b'), '[BI_MAT]'),
    (re.compile(r'\b(ghp_[A-Za-z0-9]{36})\b'), '[BI_MAT]'),
    (re.compile(r'\b(gsk_[A-Za-z0-9]{20,})\b'), '[BI_MAT]'),
    (re.compile(r'\b(AKIA[A-Z0-9]{16})\b'), '[BI_MAT]'),
    (re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}'), '[BI_MAT]'),

    # Generic long hex tokens (32+ chars, likely secrets/hashes used as tokens)
    (re.compile(r'\b[A-Fa-f0-9]{32,}\b'), '[HASH]'),

    # Internal hostnames: *.local, *.corp, *.internal, *.lan
    (re.compile(r'\b[\w-]+\.(local|corp|internal|lan)\b'), '[TEN_MAY]'),

    # Passwords in config: password=, passwd=, pwd=, secret=
    (re.compile(r'(password|passwd|pwd|secret)\s*[=:]\s*\S+', re.IGNORECASE), r'\1=[BI_MAT]'),
]

# Lighter set for local model — only strip the most sensitive items.
_LIGHT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r'\b0[3-9]\d{8}\b'), '[SĐT]'),
    (re.compile(r'\+84[3-9]\d{8}\b'), '[SĐT]'),
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
    (re.compile(r'\b\d{12}\b'), '[CCCD]'),
    (re.compile(r'\b(sk-[A-Za-z0-9]{20,})\b'), '[BI_MAT]'),
    (re.compile(r'\b(ghp_[A-Za-z0-9]{36})\b'), '[BI_MAT]'),
    (re.compile(r'(password|passwd|pwd|secret)\s*[=:]\s*\S+', re.IGNORECASE), r'\1=[BI_MAT]'),
]


def filter_pii(text: str, *, mode: str = "cloud") -> str:
    """Strip PII from *text*.

    Args:
        text: Raw evidence text.
        mode: ``"cloud"`` (full filter, mandatory for cloud APIs) or
              ``"local"`` (light filter, only phone/email/ID/secrets).

    Returns:
        Cleaned text with PII replaced by ``[PLACEHOLDER]`` labels.
    """
    if not text or not text.strip():
        return text

    patterns = _PATTERNS if mode == "cloud" else _LIGHT_PATTERNS
    result = text
    stripped_count = 0

    for regex, replacement in patterns:
        new_result = regex.sub(replacement, result)
        if new_result != result:
            stripped_count += result.count('[') - new_result.count('[') + len(regex.findall(result))
            result = new_result

    if stripped_count > 0:
        logger.info("[PrivacyFilter] Stripped %d PII items (mode=%s)", stripped_count, mode)

    return result


def sanitize_indirect_injection(text: str) -> str:
    """Loại bỏ các chỉ thị tấn công Indirect Prompt Injection ra khỏi log thô/minh chứng."""
    if not text or not text.strip():
        return text
    
    # Danh sách các từ khóa/cụm từ độc hại nhạy cảm
    injection_patterns = [
        (re.compile(r'ignore\s+(all\s+)?previous\s+instructions', re.IGNORECASE), '[ATTT_BO_QUA]'),
        (re.compile(r'ignore\s+(all\s+)?previous\s+directives', re.IGNORECASE), '[ATTT_BO_QUA]'),
        (re.compile(r'override\s+system\s+settings', re.IGNORECASE), '[ATTT_BO_QUA]'),
        (re.compile(r'developer\s+mode', re.IGNORECASE), '[ATTT_BO_QUA]'),
        (re.compile(r'you\s+must\s+now', re.IGNORECASE), '[ATTT_BO_QUA]'),
        (re.compile(r'\b(system|user|assistant|developer)\s*:\s*', re.IGNORECASE), r'[\1_role]: '),
    ]
    
    result = text
    cleaned_count = 0
    for regex, replacement in injection_patterns:
        new_result = regex.sub(replacement, result)
        if new_result != result:
            cleaned_count += len(regex.findall(result))
            result = new_result
            
    if cleaned_count > 0:
        logger.info(f"[IndirectGuard] Loc bo {cleaned_count} chi thi prompt injection gian tiep.")
        
    return result


def count_pii(text: str) -> dict:
    """Count PII items by category for reporting. Returns dict of {category: count}."""
    if not text:
        return {}

    counts = {}
    category_names = [
        "SĐT", "EMAIL", "CMND/CCCD", "IP nội bộ",
        "API key/token", "Hostname nội bộ", "Password"
    ]

    # Phone
    phones = len(re.findall(r'\b0[3-9]\d{8}\b', text)) + len(re.findall(r'\b\+84[3-9]\d{8}\b', text))
    if phones:
        counts["SĐT"] = phones

    emails = len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
    if emails:
        counts["EMAIL"] = emails

    ids_9 = len(re.findall(r'\b\d{9}\b', text))
    ids_12 = len(re.findall(r'\b\d{12}\b', text))
    if ids_9 + ids_12:
        counts["CMND/CCCD"] = ids_9 + ids_12

    ips = (
        len(re.findall(r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text))
        + len(re.findall(r'\b172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b', text))
        + len(re.findall(r'\b192\.168\.\d{1,3}\.\d{1,3}\b', text))
    )
    if ips:
        counts["IP nội bộ"] = ips

    return counts
