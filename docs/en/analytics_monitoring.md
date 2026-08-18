# Analytics & Monitoring — Technical Deep Dive

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-Analytics-blue?style=flat-square)](analytics_monitoring.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Phân_tích-red?style=flat-square)](analytics_monitoring_vi.md)

</div>

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Stats — Real-Time Monitoring](#2-system-stats--real-time-monitoring)
3. [CPU Calculation Detail](#3-cpu-calculation-detail)
4. [Memory & Disk Stats](#4-memory--disk-stats)
5. [Cache Stats](#5-cache-stats)
6. [AI Health Check](#6-ai-health-check)
7. [Assessment History Dashboard](#7-assessment-history-dashboard)
8. [ChromaDB Explorer](#8-chromadb-explorer)
9. [Frontend — Analytics Page](#9-frontend--analytics-page)
10. [Frontend — SystemStats Widget](#10-frontend--systemstats-widget)

---

## 1. Overview

The Analytics & Monitoring module provides:

| Feature | Source |
|---------|--------|
| Real-time CPU / RAM / Disk / Uptime | `/host/proc/` (host OS filesystem) |
| Cache size stats | `/data/` directory sizes |
| AI model health check | Open Claude + LocalAI ping |
| ISO assessment history | `/data/assessments/*.json` |
| ChromaDB semantic explorer | ChromaDB `iso_documents` collection |

---

## 2. System Stats — Real-Time Monitoring

File: [`backend/api/routes/system.py`](../backend/api/routes/system.py)

### Architecture

The backend container mounts the **host's `/proc` filesystem** read-only:

```yaml
# docker-compose.yml
volumes:
  - /proc:/host/proc:ro
```

All system stats are read directly from `/host/proc/*` — this reports **host machine** stats, not container-isolated stats.

```python
def read_proc_file(path: str) -> str:
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return ""
```

### Endpoint

```
GET /api/system/stats
```

**Response:**

```json
{
  "cpu": {
    "percent": 23.5,
    "model": "Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz",
    "cores": 8
  },
  "memory": {
    "total": 16777216000,
    "used":  8234567000,
    "free":  8542649000,
    "percent": 49.1
  },
  "disk": {
    "total": 512110190592,
    "used":  189234561024,
    "free":  322875629568,
    "percent": 36.9
  },
  "uptime": 432000
}
```

---

## 3. CPU Calculation Detail

File: [`backend/api/routes/system.py`](../backend/api/routes/system.py) — `get_cpu_percent()`

### Method: Two-snapshot delta from `/host/proc/stat`

```python
def get_cpu_percent():
    def parse_cpu(content):
        line = [l for l in content.split("\n") if l.startswith("cpu ")][0]
        values = list(map(int, line.split()[1:]))
        total = sum(values)
        idle  = values[3]           # 4th field = idle jiffies
        return total, idle

    stat1 = read_proc_file("/host/proc/stat")
    time.sleep(0.1)                 # 100ms snapshot interval
    stat2 = read_proc_file("/host/proc/stat")

    total1, idle1 = parse_cpu(stat1)
    total2, idle2 = parse_cpu(stat2)

    delta_total = total2 - total1
    delta_idle  = idle2  - idle1

    if delta_total == 0:
        return 0.0
    return round((1 - delta_idle / delta_total) * 100, 1)
```

### CPU Model

Read from `/host/proc/cpuinfo`:

```python
def get_cpu_info():
    content = read_proc_file("/host/proc/cpuinfo")
    for line in content.split("\n"):
        if "model name" in line:
            return line.split(":")[1].strip()   # e.g. "Intel(R) Core(TM) i7..."
    return platform.processor()
```

---

## 4. Memory & Disk Stats

### Memory — `/host/proc/meminfo`

```python
def get_memory_info():
    content = read_proc_file("/host/proc/meminfo")
    data = {}
    for line in content.strip().split("\n"):
        key, val = line.split(":")[0].strip(), line.split(":")[1].strip()
        data[key] = int(val.replace(" kB", "")) * 1024  # kB → bytes

    total = data.get("MemTotal", 0)
    free  = data.get("MemAvailable", 0)
    used  = total - free
    return {
        "total": total,
        "used":  used,
        "free":  free,
        "percent": round(used / total * 100, 1) if total else 0
    }
```

### Disk — Python `shutil`

```python
def get_disk_info():
    usage = shutil.disk_usage("/")
    return {
        "total":   usage.total,
        "used":    usage.used,
        "free":    usage.free,
        "percent": round(usage.used / usage.total * 100, 1)
    }
```

### Uptime — `/proc/uptime`

```python
def get_uptime():
    content = read_proc_file("/proc/uptime")
    return int(float(content.split()[0]))   # seconds
```

> **Note:** Uptime reads from `/proc/uptime` (container namespace), not `/host/proc/uptime`.

---

## 5. Cache Stats

```
GET /api/system/cache-stats
```

**Response:**

```json
{
  "summaries": {
    "count": 54,
    "size_bytes": 2340000
  },
  "audio": {
    "count": 54,
    "size_bytes": 98000000
  },
  "sessions": {
    "count": 12,
    "size_bytes": 45000
  },
  "assessments": {
    "count": 3,
    "size_bytes": 12000
  }
}
```

**Implementation:**

```python
def get_dir_size(path: str) -> int:
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
    return total

@router.get("/system/cache-stats")
def cache_stats():
    return {
        "summaries":   { "count": len(os.listdir(SUMMARIES_DIR)),
                         "size_bytes": get_dir_size(SUMMARIES_DIR) },
        "audio":       { "count": len(os.listdir(AUDIO_DIR)),
                         "size_bytes": get_dir_size(AUDIO_DIR) },
        "sessions":    { "count": len(os.listdir(SESSIONS_DIR)),
                         "size_bytes": get_dir_size(SESSIONS_DIR) },
        "assessments": { "count": len(os.listdir(ASSESSMENTS_DIR)),
                         "size_bytes": get_dir_size(ASSESSMENTS_DIR) },
    }
```

---

## 6. AI Health Check

File: [`backend/services/cloud_llm_service.py`](../backend/services/cloud_llm_service.py) — `health_check()`

```python
@classmethod
def health_check(cls) -> Dict[str, Any]:
    status = {
        "open_claude": { "status": "unknown", "latency_ms": None },
        "localai":     { "status": "unknown", "latency_ms": None },
    }

    # Test Open Claude
    try:
        t0 = time.time()
        cls._call_open_claude([{"role":"user","content":"ping"}], max_tokens=5)
        status["open_claude"] = {
            "status": "ok",
            "latency_ms": round((time.time()-t0)*1000)
        }
    except Exception as e:
        status["open_claude"] = {"status": "error", "error": str(e)}

    # Test LocalAI
    try:
        t0 = time.time()
        cls._call_localai(LOCAL_AI_MODEL, [{"role":"user","content":"ping"}], max_tokens=5)
        status["localai"] = {
            "status": "ok",
            "latency_ms": round((time.time()-t0)*1000)
        }
    except Exception as e:
        status["localai"] = {"status": "error", "error": str(e)}

    return status
```

**Sample response:**

```json
{
  "open_claude": { "status": "ok",    "latency_ms": 342 },
  "localai":     { "status": "error", "error": "Connection refused" }
}
```

The analytics dashboard shows these as colored status indicators (green/red).

---

## 7. Assessment History Dashboard

File: [`frontend-next/src/app/analytics/page.js`](../frontend-next/src/app/analytics/page.js)

### Data Loading

```js
useEffect(() => {
  async function fetchData() {
    // Load assessment history
    const histRes = await fetch('/api/iso27001/assessments')
    const histData = await histRes.json()
    setHistory(histData)

    // Load AI service health
    const svcRes = await fetch('/api/system/stats')
    const svcData = await svcRes.json()
    setServices({ cpu: svcData.cpu, memory: svcData.memory, ... })
  }
  fetchData()
}, [])
```

### Assessment List

Displays all assessments from `/data/assessments/` as cards:

```
┌──────────────────────────────────────────────────────┐
│  ACME Corp (Finance)                    ✅ done       │
│  Standard: ISO 27001:2022               Mar 24, 2025  │
│  Controls: A.5.1, A.9.1, A.9.2                       │
│  [View Detail] [Reuse] [Delete]                      │
└──────────────────────────────────────────────────────┘
```

### Delete with Confirmation

```js
const checkDeleteWarning = (id, e) => {
  e.stopPropagation()
  setDeleteWarning(id)      // show confirmation dialog
}

const executeDelete = async (id) => {
  await fetch(`/api/iso27001/assessments/${id}`, { method: 'DELETE' })
  setHistory(prev => prev.filter(h => h.id !== id))
  setDeleteWarning(null)
}
```

---

## 8. ChromaDB Explorer

The analytics page includes a semantic search interface for the ISO knowledge base.

### Search UI

```
┌──────────────────────────────────────────────┐
│  Search ISO Knowledge Base                   │
│  [access control policy            ] [Search]│
└──────────────────────────────────────────────┘
```

### API Call

```js
const res = await fetch('/api/iso27001/chromadb/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: searchQuery, top_k: 5 })
})
const data = await res.json()
```

### Results Display

Each result shows:

```
Distance: 0.12  |  Source: iso27001_annex_a.md
────────────────────────────────────────────────
[Context: # ISO 27001 > ## Annex A > ### A.9]
A.9.1.1 Access control policy — An access control
policy shall be established, documented...
```

### Collection Stats Display

```
ChromaDB Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Collection:    iso_documents
Documents:     312 chunks
Persist dir:   /data/vector_store
Distance:      cosine
```

---

## 9. Frontend — Analytics Page

File: [`frontend-next/src/app/analytics/page.js`](../frontend-next/src/app/analytics/page.js)

### Page Sections

```
┌─────────────────────────────────────────────────────────┐
│  System Resources                                       │
│  [CPU: 23%] [RAM: 49%] [Disk: 37%] [Uptime: 5d 2h]    │
├─────────────────────────────────────────────────────────┤
│  AI Services                                            │
│  [Open Claude: ✅ 342ms] [LocalAI: ❌ offline]          │
├─────────────────────────────────────────────────────────┤
│  Assessment History          [3 assessments]            │
│  ┌────────────────────────────────────────────────────┐ │
│  │ ACME Corp — ISO 27001:2022 — done — Mar 24         │ │
│  │ Test Corp — TCVN 14423    — done — Mar 23         │ │
│  └────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  ISO Knowledge Base Search                              │
│  [query input] [Search]                                 │
│  Results: 5 semantic matches shown                      │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Frontend — SystemStats Widget

File: [`frontend-next/src/components/SystemStats.js`](../frontend-next/src/components/SystemStats.js)

A reusable widget that can be embedded in any page. Caches stats for 10 seconds to avoid excessive polling.

### Cache Logic

```js
function getCachedStats() {
  try {
    const s = sessionStorage.getItem("sys_stats")
    if (!s) return null
    const { data, ts } = JSON.parse(s)
    if (Date.now() - ts < 10000) return data    // 10s cache
    return null
  } catch { return null }
}
```

### Metric Items

```js
const items = [
  { label: "CPU",    value: `${stats.cpu?.percent}%`,   color: getColor(stats.cpu?.percent) },
  { label: "RAM",    value: `${stats.memory?.percent}%`,color: getColor(stats.memory?.percent) },
  { label: "Disk",   value: `${stats.disk?.percent}%`,  color: getColor(stats.disk?.percent) },
  { label: "Uptime", value: formatUptime(stats.uptime),  color: "var(--accent-blue)" },
]
```

### Color Thresholds

```js
const getColor = (percent, thresholds = [50, 80]) => {
  if (percent < thresholds[0]) return "var(--accent-green)"   // healthy
  if (percent < thresholds[1]) return "var(--accent-yellow)"  // warning
  return "var(--accent-red)"                                   // critical
}
```

### Formatting Helpers

```js
const formatBytes = (bytes) => {
  if (bytes > 1e9) return `${(bytes/1e9).toFixed(1)} GB`
  if (bytes > 1e6) return `${(bytes/1e6).toFixed(1)} MB`
  return `${(bytes/1e3).toFixed(0)} KB`
}

const formatUptime = (seconds) => {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}
```
