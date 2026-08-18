"""RAM guard — disable the heavy 27B local model path when host RAM is too low.

Rule: if total system RAM (GB) < ``settings.LOCAL_RAM_GUARD_GB``, the heavy
local path (e.g. ``gemma3:27b``) is disabled and callers must fall back to a
mid-size local model.

Fail-open policy: if RAM cannot be determined on this platform, we log a
warning and return False so we do NOT regress behavior.
"""

from __future__ import annotations

import logging

from core.config import settings

_BYTES_PER_GB = 1024 ** 3


def _total_ram_gb() -> float | None:
    """Return total system RAM in GB, or ``None`` if it cannot be determined."""
    # Preferred path — psutil (already a pinned dep in backend/requirements.txt).
    try:
        import psutil  # type: ignore
        return float(psutil.virtual_memory().total) / _BYTES_PER_GB
    except Exception:
        pass

    # Linux fallback — /proc/meminfo
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return (kb * 1024) / _BYTES_PER_GB
    except Exception:
        pass

    # Windows fallback — GlobalMemoryStatusEx via ctypes
    try:
        import ctypes

        class _MEMSTAT(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = _MEMSTAT()
        stat.dwLength = ctypes.sizeof(_MEMSTAT)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return float(stat.ullTotalPhys) / _BYTES_PER_GB
    except Exception:
        pass

    return None


def should_disable_heavy_local_model() -> bool:
    """Return True when the heavy (27B) local model path must be disabled.

    Fail-open: returns False when total RAM cannot be determined.
    """
    total_gb = _total_ram_gb()
    if total_gb is None:
        return False
    return total_gb < float(settings.LOCAL_RAM_GUARD_GB)


def log_ram_guard_status(logger: logging.Logger) -> None:
    """Log a one-line RAM-guard status message at startup."""
    threshold = float(settings.LOCAL_RAM_GUARD_GB)
    total_gb = _total_ram_gb()
    if total_gb is None:
        logger.warning(
            "RAM guard: unable to determine system RAM; heavy-local path left ENABLED "
            "(fail-open). threshold=%.1fGB",
            threshold,
        )
        return
    if total_gb < threshold:
        logger.warning(
            "RAM guard: host RAM %.1fGB < threshold %.1fGB — heavy local model "
            "(e.g. gemma3:27b) DISABLED; falling back to mid-size local model.",
            total_gb,
            threshold,
        )
    else:
        logger.info(
            "RAM guard: host RAM %.1fGB ≥ threshold %.1fGB — heavy local path enabled.",
            total_gb,
            threshold,
        )


# Cached at import so routers can consult without re-reading memory each call.
HEAVY_LOCAL_DISABLED: bool = should_disable_heavy_local_model()
