"""Smoke test for log-analysis helpers — runs without FastAPI deps.

Not a pytest test; invoked directly with `python backend/tests/_smoke_log_helpers.py`.
Validates _is_log_analysis / _flatten_log_to_fields / _normalize_log_output logic.
"""
import json
import re
from typing import Any, List

# ── Mirrors of helpers under test (copy-paste, NOT importing ChatService to skip fastapi) ──

_LOG_JSON_KEY_HINTS = (
    '"rule"', '"agent"', '"manager"', '"decoder"',
    '"event_src"', '"behavior_type"', '"behavior_category"',
    '"srcip"', '"dstip"', '"src_port"', '"dst_port"',
    '"action":"allow"', '"action":"deny"', '"action":"block"',
    '"http_method"', '"status_code"', '"user_agent"', '"request_uri"',
    '"syscall"', '"auid"', '"ses"', '"exe"',
    '"EventID"', '"EventCode"', '"Computer"', '"Channel"',
    '"full_log"', '"@timestamp"', '"_source"',
)


def is_log_analysis(message: str) -> bool:
    if not message:
        return False
    msg_lower = message.lower()
    log_keywords = (
        "phân tích log", "analyze log", "event id", "eventid",
        "sự kiện", "windows event", "syslog", "security log",
        "audit log", "process creation", "logon", "logoff",
        "firewall log", "access log", "error log", "phân tích sự kiện",
        "raw log", "alert", "siem log", "edr log",
    )
    if any(kw in msg_lower for kw in log_keywords):
        return True
    stripped = message.lstrip()
    if stripped.startswith(('{', '[')):
        for hint in _LOG_JSON_KEY_HINTS:
            if hint in message:
                return True
    log_patterns = (
        r"Event\s*ID[:\s]*\d+",
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        r"\bsrc(?:ip|_ip)?\s*=\s*\d+\.\d+\.\d+\.\d+",
        r"\b(?:GET|POST|PUT|DELETE|PATCH)\s+/\S+\s+HTTP/\d",
    )
    for pattern in log_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return True
    return False


_SKIP = frozenset({"_index", "_id", "_version", "_score", "_type",
                   "fields", "highlight", "sort", "location", "input"})


def flatten_log(message: str) -> str:
    if not message:
        return message
    stripped = message.strip()
    if not stripped.startswith(('{', '[')):
        return message
    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return message
    if isinstance(data, list):
        if not data:
            return message
        data = data[0]
    if not isinstance(data, dict):
        return message
    if isinstance(data.get("_source"), dict):
        data = data["_source"]

    lines: List[str] = []
    seen: set = set()

    def _emit(key: str, value: Any) -> None:
        if value is None or value == "":
            return
        sval = str(value).strip()
        if not sval or sval in {"-", "N/A", "null"}:
            return
        sig = (key, sval[:80])
        if sig in seen:
            return
        seen.add(sig)
        if len(sval) > 400:
            sval = sval[:400] + "…"
        lines.append(f"{key}: {sval}")

    def _walk(obj, prefix=""):
        if len(lines) >= 40:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in _SKIP:
                    continue
                key = f"{prefix}.{k}" if prefix else str(k)
                _walk(v, key)
        elif isinstance(obj, list):
            if obj and all(not isinstance(x, (dict, list)) for x in obj):
                _emit(prefix, ", ".join(str(x) for x in obj))
            else:
                for i, item in enumerate(obj[:3]):
                    _walk(item, f"{prefix}[{i}]")
        else:
            _emit(prefix, obj)

    _walk(data)
    if len(lines) < 3:
        return message
    return "Log đã chuẩn hoá (field: value) — phân tích theo format bắt buộc:\n" + "\n".join(lines[:40])


_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_HRULE = re.compile(
    r"^\s{0,3}[-_*=~\u2014\u2015\u2500\u2501\u2550\u25AC\u23AF\u2E3B\u2580\u25A0\u25FC\u2022]{3,}\s*$",
    re.MULTILINE,
)
_INLINE_DIV = re.compile(r"[\u2014\u2015\u2500\u2501\u2550\u25AC\u23AF\u2E3B]{3,}")
_LEADING_EMOJI = re.compile(
    r"^\s*[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2B00-\u2BFF]+\s*",
    re.MULTILINE,
)
_BULLET = re.compile(r"^\s{0,3}[-*+•]\s+(?=[A-Za-zÀ-ỹ])", re.MULTILINE)
_BOLD_LABEL = re.compile(r"^\s*\*\*([^*\n:]{1,60})\*\*\s*:", re.MULTILINE)

_VN_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    re.IGNORECASE,
)


def is_vietnamese(text: str) -> bool:
    return bool(_VN_RE.search(text or ""))


_MARKERS = ("Nhận định:", "Mức độ:", "Technique:", "Tactic:",
            "Log cần kiểm tra:", "Truy vấn gợi ý:", "IOCs:")


def session_in_log_mode(history):
    if not history:
        return False
    for msg in reversed(history):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "") or ""
        hits = sum(1 for m in _MARKERS if m in content)
        return hits >= 2
    return False


def normalize(text: str) -> str:
    if not text:
        return text
    out = _HEADING.sub("", text)
    out = _HRULE.sub("", out)
    out = _INLINE_DIV.sub("", out)
    out = _LEADING_EMOJI.sub("", out)
    out = _BULLET.sub("", out)
    out = _BOLD_LABEL.sub(r"\1:", out)
    out = re.sub(r"\*\*([^*\n]{1,120})\*\*", r"\1", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


# ── Test cases ──

# 1. NCS EDR log from the user's screenshot (abridged).
EDR_JSON = '''{
  "_index": "edr-alerts-4.x",
  "_source": {
    "agent": {"ip": "192.168.2.47", "name": "HOST01", "id": "1198"},
    "data": {
      "subject": {"process": {"name": "DismHost.exe", "path": "C:\\\\Temp\\\\"}},
      "behavior_severity": "high",
      "behavior_type": "DLL side-loading detected",
      "action": "load",
      "event_src": {"host": "MAYSCAN", "category": "process"},
      "time": "2026-04-20T16:31:35.085Z",
      "object": {"process": {"name": "CbsProvider.dll", "extension": "dll"}}
    },
    "rule": {"level": 5, "description": "DLL side-loading", "id": "99999"}
  }
}'''


def test_detect_edr_json():
    assert is_log_analysis(EDR_JSON), "EDR JSON must be detected as log"
    print("✓ detect EDR JSON")


def test_detect_firewall_kv():
    msg = "Apr 20 16:31:35 fw1 kernel: srcip=10.0.0.5 dstip=8.8.8.8 proto=UDP"
    assert is_log_analysis(msg)
    print("✓ detect firewall key=value")


def test_detect_nginx_access():
    msg = '192.168.1.1 - - [20/Apr/2026:16:31:35 +0700] "GET /admin HTTP/1.1" 401 234'
    assert is_log_analysis(msg)
    print("✓ detect nginx access")


def test_detect_plain_question():
    assert not is_log_analysis("Làm sao để cấu hình ISO 27001?")
    print("✓ skip non-log question")


def test_flatten_edr():
    out = flatten_log(EDR_JSON)
    assert "agent.ip: 192.168.2.47" in out, out
    assert "data.behavior_severity: high" in out, out
    assert "rule.description: DLL side-loading" in out, out
    assert "_index" not in out, "_index must be skipped"
    print("✓ flatten EDR JSON")


def test_flatten_non_json_passthrough():
    msg = "EventID: 4688\nHost: PC01"
    assert flatten_log(msg) == msg
    print("✓ flatten non-JSON passthrough")


def test_flatten_invalid_json_passthrough():
    msg = "{this is not json}"
    assert flatten_log(msg) == msg
    print("✓ flatten invalid JSON passthrough")


def test_normalize_strips_headings():
    bad = "## Technical Data Extraction\n### Observed Activity:\n- **Source Process**: foo"
    out = normalize(bad)
    assert "##" not in out
    assert "###" not in out
    assert not out.startswith("-")
    print("✓ normalize strips headings + bullets")


def test_normalize_strips_hrule():
    bad = "Event ID: 4688\n---\nNhận định: High"
    out = normalize(bad)
    assert "---" not in out
    print("✓ normalize strips horizontal rule")


def test_normalize_strips_unicode_hrule():
    bad = "Event ID: 4688\n━━━━━━━━━━━━━\nNhận định: High\n─────────\n═══════"
    out = normalize(bad)
    assert "━" not in out
    assert "─" not in out
    assert "═" not in out
    print("✓ normalize strips unicode hrule (━ ─ ═)")


def test_normalize_strips_leading_emoji():
    bad = "🚨 BÁO CÁO PHÂN TÍCH SỰ CỐ AN NINH MẠNG\nEvent ID: 4688"
    out = normalize(bad)
    assert "🚨" not in out
    assert out.startswith("BÁO CÁO"), out
    print("✓ normalize strips leading emoji")


def test_normalize_strips_inline_bold():
    bad = "Nhận định: **True Positive** cao"
    out = normalize(bad)
    assert "**" not in out
    assert "True Positive" in out
    print("✓ normalize strips inline **bold**")


def test_normalize_converts_bold_label():
    bad = "**Source Process**: powershell.exe"
    out = normalize(bad)
    assert out == "Source Process: powershell.exe", out
    print("✓ normalize converts bold label")


def test_is_vietnamese_true():
    assert is_vietnamese("Phân tích log này xem log này đang làm gì")
    print("✓ VN detected")


def test_is_vietnamese_false():
    assert not is_vietnamese("Analyze this log please")
    print("✓ EN not flagged as VN")


def test_session_sticky_log_mode():
    history = [
        {"role": "user", "content": "Phân tích log EDR"},
        {"role": "assistant", "content": "Event ID: 4688\nNhận định: True Positive\nMức độ: High"},
    ]
    assert session_in_log_mode(history)
    print("✓ session sticky log mode detected")


def test_session_not_log_mode():
    history = [
        {"role": "user", "content": "Xin chào"},
        {"role": "assistant", "content": "Chào bạn! Tôi có thể giúp gì?"},
    ]
    assert not session_in_log_mode(history)
    print("✓ session non-log mode correctly skipped")


if __name__ == "__main__":
    test_detect_edr_json()
    test_detect_firewall_kv()
    test_detect_nginx_access()
    test_detect_plain_question()
    test_flatten_edr()
    test_flatten_non_json_passthrough()
    test_flatten_invalid_json_passthrough()
    test_normalize_strips_headings()
    test_normalize_strips_hrule()
    test_normalize_strips_unicode_hrule()
    test_normalize_strips_leading_emoji()
    test_normalize_strips_inline_bold()
    test_normalize_converts_bold_label()
    test_is_vietnamese_true()
    test_is_vietnamese_false()
    test_session_sticky_log_mode()
    test_session_not_log_mode()
    print("\nAll smoke checks passed.")
