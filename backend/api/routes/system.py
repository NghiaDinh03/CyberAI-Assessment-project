import platform
import time
import os
from fastapi import APIRouter

router = APIRouter()

def read_proc_file(path: str) -> str:
    try:
        with open(path, "r") as f:
            return f.read()
    except:
        return ""

def get_cpu_info():
    cpu_name = "Unknown CPU"
    cores = os.cpu_count() or 0

    proc_info = read_proc_file("/host/proc/cpuinfo")
    if proc_info:
        for line in proc_info.split("\n"):
            if "model name" in line:
                cpu_name = line.split(":")[1].strip()
                break

    return {"name": cpu_name, "cores": cores}

def get_cpu_percent():
    stat1 = read_proc_file("/host/proc/stat")
    if not stat1:
        return 0.0

    def parse_cpu(content):
        line = content.split("\n")[0]
        parts = line.split()
        idle = int(parts[4])
        total = sum(int(p) for p in parts[1:])
        return idle, total

    idle1, total1 = parse_cpu(stat1)
    time.sleep(0.3)
    stat2 = read_proc_file("/host/proc/stat")
    idle2, total2 = parse_cpu(stat2)

    idle_delta = idle2 - idle1
    total_delta = total2 - total1

    if total_delta == 0:
        return 0.0

    return round((1.0 - idle_delta / total_delta) * 100, 1)

def get_memory_info():
    meminfo = read_proc_file("/host/proc/meminfo")
    if not meminfo:
        return {"used": 0, "total": 0, "percent": 0}

    mem = {}
    for line in meminfo.split("\n"):
        parts = line.split(":")
        if len(parts) == 2:
            key = parts[0].strip()
            val = int(parts[1].strip().split()[0]) * 1024
            mem[key] = val

    total = mem.get("MemTotal", 0)
    available = mem.get("MemAvailable", 0)
    used = total - available

    return {
        "used": used,
        "total": total,
        "percent": round((used / total) * 100, 1) if total > 0 else 0
    }

def get_disk_info():
    try:
        stat = os.statvfs("/")
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bfree * stat.f_frsize
        used = total - free
        return {
            "used": used,
            "total": total,
            "percent": round((used / total) * 100, 1) if total > 0 else 0
        }
    except:
        return {"used": 0, "total": 0, "percent": 0}

def get_uptime():
    uptime_str = read_proc_file("/host/proc/uptime")
    if uptime_str:
        return float(uptime_str.split()[0])
    return 0.0

from services.cloud_llm_service import CloudLLMService
from services.model_guard import ModelGuard
from core.config import settings


@router.get("/system/stats")
def system_stats():
    cpu_info = get_cpu_info()
    cpu_percent = get_cpu_percent()
    memory = get_memory_info()
    disk = get_disk_info()
    uptime = get_uptime()

    return {
        "cpu": {
            "name": cpu_info["name"],
            "cores": cpu_info["cores"],
            "percent": cpu_percent
        },
        "memory": {
            "used": memory["used"],
            "total": memory["total"],
            "percent": memory["percent"]
        },
        "disk": {
            "used": disk["used"],
            "total": disk["total"],
            "percent": disk["percent"]
        },
        "uptime_seconds": uptime,
        "platform": platform.system()
    }

def get_dir_size(path: str):
    total_size = 0
    total_files = 0
    if os.path.exists(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
                    total_files += 1
    return total_size, total_files

@router.get("/system/cache-stats")
def cache_stats():
    sessions_size, sessions_files = get_dir_size("/data/sessions")
    exports_size, exports_files = get_dir_size("/data/exports")

    return {
        "sessions": {
            "size_bytes": sessions_size,
            "files": sessions_files
        },
        "exports": {
            "size_bytes": exports_size,
            "files": exports_files
        },
        "total_size_bytes": sessions_size + exports_size,
        "total_files": sessions_files + exports_files
    }


@router.get("/system/ai-status")
def ai_status():
    health = CloudLLMService.health_check()
    models_ready = ModelGuard.is_ready()
    cloud_ready = bool(settings.cloud_api_key_list)

    if settings.LOCAL_ONLY_MODE:
        mode_label = "local-only"
    elif settings.PREFER_LOCAL:
        mode_label = "local-first"
    else:
        mode_label = "cloud-first"

    return {
        "local_only_mode": settings.LOCAL_ONLY_MODE,
        "prefer_local": settings.PREFER_LOCAL,
        "mode_label": mode_label,
        "models_ready": models_ready,
        "cloud_keys": cloud_ready,
        "model_guard": ModelGuard.status(),
        "localai": health.get("localai", {}),
        "open_claude": health.get("open_claude", {}),
    }
