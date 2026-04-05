# Phân Tích & Giám Sát — Phân Tích Kỹ Thuật

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-Analytics-blue?style=flat-square)](analytics_monitoring.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Phân_tích-red?style=flat-square)](analytics_monitoring_vi.md)

</div>

---

## Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Thống Kê Hệ Thống — Giám Sát Thời Gian Thực](#2-thống-kê-hệ-thống--giám-sát-thời-gian-thực)
3. [Chi Tiết Tính CPU](#3-chi-tiết-tính-cpu)
4. [Thống Kê Bộ Nhớ & Đĩa](#4-thống-kê-bộ-nhớ--đĩa)
5. [Thống Kê Cache](#5-thống-kê-cache)
6. [Kiểm Tra Sức Khỏe AI](#6-kiểm-tra-sức-khỏe-ai)
7. [Dashboard Lịch Sử Đánh Giá](#7-dashboard-lịch-sử-đánh-giá)
8. [ChromaDB Explorer](#8-chromadb-explorer)
9. [Frontend — Trang Analytics](#9-frontend--trang-analytics)
10. [Frontend — Widget SystemStats](#10-frontend--widget-systemstats)

---

## 1. Tổng Quan

Module Phân Tích & Giám Sát cung cấp:

| Tính năng | Nguồn |
|---------|------|
| CPU / RAM / Disk / Uptime thời gian thực | `/host/proc/` (filesystem host OS) |
| Thống kê kích thước cache | Kích thước thư mục `/data/` |
| Kiểm tra sức khỏe model AI | Open Claude + LocalAI ping |
| Lịch sử đánh giá ISO | `/data/assessments/*.json` |
| ChromaDB semantic explorer | ChromaDB collection `iso_documents` |

---

## 2. Thống Kê Hệ Thống — Giám Sát Thời Gian Thực

File: [`backend/api/routes/system.py`](../backend/api/routes/system.py)

### Kiến Trúc

Container backend mount **filesystem `/proc` của host** ở chế độ chỉ đọc:

```yaml
# docker-compose.yml
volumes:
  - /proc:/host/proc:ro
```

Mọi thống kê hệ thống được đọc trực tiếp từ `/host/proc/*` — báo cáo thống kê **máy host**, không phải container-isolated.

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

**Phản hồi:**

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

## 3. Chi Tiết Tính CPU

File: [`backend/api/routes/system.py`](../backend/api/routes/system.py) — `get_cpu_percent()`

### Phương Pháp: Delta 2 snapshot từ `/host/proc/stat`

```python
def get_cpu_percent():
    def parse_cpu(content):
        line = [l for l in content.split("\n") if l.startswith("cpu ")][0]
        values = list(map(int, line.split()[1:]))
        total = sum(values)
        idle  = values[3]           # Trường thứ 4 = idle jiffies
        return total, idle

    stat1 = read_proc_file("/host/proc/stat")
    time.sleep(0.1)                 # Khoảng thời gian snapshot 100ms
    stat2 = read_proc_file("/host/proc/stat")

    total1, idle1 = parse_cpu(stat1)
    total2, idle2 = parse_cpu(stat2)

    delta_total = total2 - total1
    delta_idle  = idle2  - idle1

    if delta_total == 0:
        return 0.0
    return round((1 - delta_idle / delta_total) * 100, 1)
```

### Model CPU

Đọc từ `/host/proc/cpuinfo`:

```python
def get_cpu_info():
    content = read_proc_file("/host/proc/cpuinfo")
    for line in content.split("\n"):
        if "model name" in line:
            return line.split(":")[1].strip()
    return platform.processor()
```

---

## 4. Thống Kê Bộ Nhớ & Đĩa

### Bộ Nhớ — `/host/proc/meminfo`

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

### Đĩa — Python `shutil`

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
    return int(float(content.split()[0]))   # giây
```

> **Lưu ý:** Uptime đọc từ `/proc/uptime` (namespace container), không phải `/host/proc/uptime`.

---

## 5. Thống Kê Cache

```
GET /api/system/cache-stats
```

**Phản hồi:**

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

**Triển khai:**

```python
def get_dir_size(path: str) -> int:
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
    return total
```

---

## 6. Kiểm Tra Sức Khỏe AI

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

**Phản hồi mẫu:**

```json
{
  "open_claude": { "status": "ok",    "latency_ms": 342 },
  "localai":     { "status": "error", "error": "Connection refused" }
}
```

Dashboard analytics hiển thị các chỉ báo màu sắc (xanh/đỏ).

---

## 7. Dashboard Lịch Sử Đánh Giá

File: [`frontend-next/src/app/analytics/page.js`](../frontend-next/src/app/analytics/page.js)

### Load Dữ Liệu

```js
useEffect(() => {
  async function fetchData() {
    // Load lịch sử đánh giá
    const histRes = await fetch('/api/iso27001/assessments')
    const histData = await histRes.json()
    setHistory(histData)

    // Load sức khỏe dịch vụ AI
    const svcRes = await fetch('/api/system/stats')
    const svcData = await svcRes.json()
    setServices({ cpu: svcData.cpu, memory: svcData.memory, ... })
  }
  fetchData()
}, [])
```

### Danh Sách Đánh Giá

Hiển thị tất cả đánh giá từ `/data/assessments/` dưới dạng thẻ:

```
┌──────────────────────────────────────────────────────────┐
│  ACME Corp (Tài chính)                     ✅ done        │
│  Tiêu chuẩn: ISO 27001:2022               24/03/2025     │
│  Controls: A.5.1, A.9.1, A.9.2                          │
│  [Xem chi tiết] [Tái sử dụng] [Xóa]                    │
└──────────────────────────────────────────────────────────┘
```

### Xóa Có Xác Nhận

```js
const checkDeleteWarning = (id, e) => {
  e.stopPropagation()
  setDeleteWarning(id)      // hiện dialog xác nhận
}

const executeDelete = async (id) => {
  await fetch(`/api/iso27001/assessments/${id}`, { method: 'DELETE' })
  setHistory(prev => prev.filter(h => h.id !== id))
  setDeleteWarning(null)
}
```

---

## 8. ChromaDB Explorer

Trang analytics bao gồm giao diện tìm kiếm ngữ nghĩa cho cơ sở kiến thức ISO.

### UI Tìm Kiếm

```
┌──────────────────────────────────────────────┐
│  Tìm kiếm Cơ Sở Kiến Thức ISO               │
│  [chính sách kiểm soát truy cập    ] [Tìm]  │
└──────────────────────────────────────────────┘
```

### Gọi API

```js
const res = await fetch('/api/iso27001/chromadb/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: searchQuery, top_k: 5 })
})
const data = await res.json()
```

### Hiển Thị Kết Quả

Mỗi kết quả hiển thị:

```
Khoảng cách: 0.12  |  Nguồn: iso27001_annex_a.md
──────────────────────────────────────────────────────
[Context: # ISO 27001 > ## Annex A > ### A.9]
A.9.1.1 Chính sách kiểm soát truy cập — Cần thiết lập
chính sách kiểm soát truy cập, được lập tài liệu...
```

### Hiển Thị Thống Kê Collection

```
Trạng Thái ChromaDB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Collection:    iso_documents
Tài liệu:      312 chunks
Thư mục lưu:  /data/vector_store
Metric:        cosine
```

---

## 9. Frontend — Trang Analytics

File: [`frontend-next/src/app/analytics/page.js`](../frontend-next/src/app/analytics/page.js)

### Các Phần Trang

```
┌──────────────────────────────────────────────────────────┐
│  Tài Nguyên Hệ Thống                                     │
│  [CPU: 23%] [RAM: 49%] [Disk: 37%] [Uptime: 5n 2h]      │
├──────────────────────────────────────────────────────────┤
│  Dịch Vụ AI                                              │
│  [Open Claude: ✅ 342ms] [LocalAI: ❌ offline]            │
├──────────────────────────────────────────────────────────┤
│  Lịch Sử Đánh Giá              [3 đánh giá]              │
│  ┌──────────────────────────────────────────────────┐    │
│  │ ACME Corp — ISO 27001:2022 — done — 24/03        │    │
│  │ Test Corp — TCVN 14423    — done — 23/03         │    │
│  └──────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────┤
│  Tìm Kiếm Cơ Sở Kiến Thức ISO                           │
│  [ô nhập query] [Tìm]                                    │
│  Kết quả: 5 kết quả ngữ nghĩa                            │
└──────────────────────────────────────────────────────────┘
```

---

## 10. Frontend — Widget SystemStats

File: [`frontend-next/src/components/SystemStats.js`](../frontend-next/src/components/SystemStats.js)

Widget có thể tái sử dụng nhúng vào bất kỳ trang nào. Cache thống kê 10 giây để tránh polling quá mức.

### Logic Cache

```js
function getCachedStats() {
  try {
    const s = sessionStorage.getItem("sys_stats")
    if (!s) return null
    const { data, ts } = JSON.parse(s)
    if (Date.now() - ts < 10000) return data    // cache 10s
    return null
  } catch { return null }
}
```

### Các Chỉ Số

```js
const items = [
  { label: "CPU",     value: `${stats.cpu?.percent}%`,    color: getColor(stats.cpu?.percent) },
  { label: "RAM",     value: `${stats.memory?.percent}%`, color: getColor(stats.memory?.percent) },
  { label: "Disk",    value: `${stats.disk?.percent}%`,   color: getColor(stats.disk?.percent) },
  { label: "Uptime",  value: formatUptime(stats.uptime),   color: "var(--accent-blue)" },
]
```

### Ngưỡng Màu Sắc

```js
const getColor = (percent, thresholds = [50, 80]) => {
  if (percent < thresholds[0]) return "var(--accent-green)"   // bình thường
  if (percent < thresholds[1]) return "var(--accent-yellow)"  // cảnh báo
  return "var(--accent-red)"                                   // nghiêm trọng
}
```

### Hàm Định Dạng

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
  if (d > 0) return `${d}n ${h}g`
  if (h > 0) return `${h}g ${m}p`
  return `${m}p`
}
```
