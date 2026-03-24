# Tin Tức Tổng Hợp — Phân Tích Kỹ Thuật

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-News_Aggregator-blue?style=flat-square)](news_aggregator.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Tin_tức_tổng_hợp-red?style=flat-square)](news_aggregator_vi.md)

</div>

---

## Mục Lục

1. [Tổng Quan](#1-tổng-quan)
2. [Sơ Đồ Pipeline Đầy Đủ](#2-sơ-đồ-pipeline-đầy-đủ)
3. [Nguồn RSS](#3-nguồn-rss)
4. [Cào Bài Báo — Chuỗi 3 Chiến Lược](#4-cào-bài-báo--chuỗi-3-chiến-lược)
5. [Dịch & Biên Tập AI — Open Claude](#5-dịch--biên-tập-ai--open-claude)
6. [Text-to-Speech — Edge-TTS](#6-text-to-speech--edge-tts)
7. [Kiến Trúc Cache](#7-kiến-trúc-cache)
8. [Hàng Đợi Worker Nền](#8-hàng-đợi-worker-nền)
9. [Cache Dịch Thuật](#9-cache-dịch-thuật)
10. [Frontend — Trang Tin Tức](#10-frontend--trang-tin-tức)

---

## 1. Tổng Quan

Module Tin Tức Tổng Hợp:

1. **Lấy** bài báo từ 9 feed RSS trong 3 danh mục
2. **Dịch** tiêu đề bài tiếng Anh sang tiếng Việt (theo lô, có cache)
3. **Theo yêu cầu** (người dùng nhấn play): cào nội dung đầy đủ, dịch/biên tập bằng AI, tạo audio
4. **Cache** mọi thứ — không gọi AI trùng lặp cho cùng một URL

| Tầng | Công nghệ |
|------|----------|
| Phân tích RSS | Python `xml.etree.ElementTree` + `requests` |
| Cào web | `requests+BeautifulSoup4` → `trafilatura` → `newspaper3k` |
| Dịch AI | Open Claude (gemini-2.5-pro) → LocalAI dự phòng |
| Text-to-Speech | Microsoft Edge TTS (`edge-tts`, giọng: `vi-VN-HoaiMyNeural`) |
| Định dạng audio | MP3, lưu tại `/data/summaries/audio/` |
| Cache tóm tắt | File JSON tại `/data/summaries/{hash}.json` |

---

## 2. Sơ Đồ Pipeline Đầy Đủ

```
Người dùng mở trang /news
          │
          ▼
GET /api/news?category=cybersecurity
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  NewsService.get_news(category, limit=15)                       │
│                                                                  │
│  1. Kiểm tra cache in-memory (CACHE_TTL = 15 phút)              │
│     → HIT: trả về dữ liệu cache ngay                            │
│     → MISS: tiếp tục                                            │
│                                                                  │
│  2. _parse_rss() × 3 nguồn                                      │
│     → Lấy mỗi feed RSS (HTTP GET)                               │
│     → Parse XML: title, url, date, description                   │
│     → Sắp xếp theo ngày mới nhất, cắt theo limit               │
│                                                                  │
│  3. Cho mỗi bài báo:                                             │
│     → SummaryService._get_cache(url)                             │
│       → audio_cached = true/false/error                         │
│                                                                  │
│  4. _apply_translations(articles, category)                      │
│     → Load title_vi từ JSON cache dịch                          │
│                                                                  │
│  5. _update_history(articles)                                    │
│     → Lưu vào /data/articles_history.json                       │
│                                                                  │
│  6. Đưa bài chưa dịch → _translation_queue                      │
│  7. Đưa bài chưa tóm tắt → _llama_queue                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ trả về danh sách bài
                               ▼
                    Người dùng thấy thẻ bài báo
                    (hiển thị badge audio_cached)
                               │
                    Người dùng nhấn ▶ Play
                               │
                               ▼
POST /api/news/summarize { url, lang, title }
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  SummaryService.process_article(url)   [khóa theo URL]          │
│                                                                  │
│  Bước 1 — Cào nội dung bài báo                                  │
│    Lần 1: requests + BeautifulSoup4                             │
│    Lần 2: trafilatura                                           │
│    Lần 3: newspaper3k                                           │
│    Cắt tại 30.000 ký tự                                         │
│                                                                  │
│  Bước 2 — Open Claude: dịch/biên tập sang tiếng Việt            │
│    task_type = "news_translate" → gemini-2.5-pro                │
│    temperature = 0.1, max_tokens = 32000                        │
│    Xóa artifact AI (* # <|eot_id|> tiền tố "assistant")         │
│    Xóa ghi chú/từ chối trách nhiệm cuối                        │
│                                                                  │
│  Bước 3 — Edge-TTS: tạo audio MP3                               │
│    Giọng: vi-VN-HoaiMyNeural                                    │
│    Lưu vào: /data/summaries/audio/{url_hash}.mp3                │
│                                                                  │
│  Cache JSON: /data/summaries/{url_hash}.json                    │
│    { audio_url, summary_vi, title_vi, url, hash }               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
              { audio_url, summary_vi, title_vi }
                               │
                    Frontend phát audio MP3
```

---

## 3. Nguồn RSS

```python
RSS_SOURCES = {
    "cybersecurity": [
        { "name": "The Hacker News",  "url": "https://feeds.feedburner.com/TheHackersNews", "lang": "en" },
        { "name": "Dark Reading",     "url": "https://www.darkreading.com/rss.xml",          "lang": "en" },
        { "name": "SecurityWeek",     "url": "https://www.securityweek.com/feed/",            "lang": "en" },
    ],
    "stocks_international": [
        { "name": "CNBC Markets",     "url": "https://search.cnbc.com/rs/search/...",         "lang": "en" },
        { "name": "MarketWatch",      "url": "https://feeds.marketwatch.com/...",             "lang": "en" },
        { "name": "Yahoo Finance",    "url": "https://finance.yahoo.com/news/rssindex",       "lang": "en" },
    ],
    "stocks_vietnam": [
        { "name": "Znews Kinh doanh", "url": "https://znews.vn/rss/kinh-doanh-tai-chinh.rss","lang": "vi" },
        { "name": "VnExpress KD",     "url": "https://vnexpress.net/rss/kinh-doanh.rss",     "lang": "vi" },
        { "name": "VnEconomy",        "url": "https://vneconomy.vn/chung-khoan.rss",         "lang": "vi" },
    ],
}
```

**TTL Cache:** `CACHE_TTL = 15` phút (dict `_cache` in-memory)

---

## 4. Cào Bài Báo — Chuỗi 3 Chiến Lược

File: [`backend/services/summary_service.py`](../backend/services/summary_service.py)

### Chiến Lược 1 — requests + BeautifulSoup4

```python
def _scrape_with_requests_bs4(url):
    resp = requests.get(url, headers=_get_random_headers(), timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    # Loại bỏ nhiễu: nav, aside, footer, script, style, quảng cáo
    for tag in soup(["nav","aside","footer","script","style","form","button"]):
        tag.decompose()
    # Trích xuất đoạn văn ≥ 40 ký tự
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")
                  if len(p.get_text(strip=True)) >= 40]
    return "\n\n".join(paragraphs)
```

### Chiến Lược 2 — trafilatura

```python
def _scrape_with_trafilatura(url):
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False)
```

### Chiến Lược 3 — newspaper3k

```python
def _scrape_with_newspaper(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.text
```

### Dự Phòng Khi Bị Chặn / Nội Dung Không Đủ

Nếu tất cả chiến lược thất bại hoặc < 300 ký tự:

```python
if title:
    text = f"{title}\n\n{text or ''}"
    # Dùng title + text một phần (≥ 100 ký tự để tiếp tục)
```

Nếu domain chặn bot (HTTP 401/403/429):

```json
{
  "error": "❌ Trang thehackernews.com chặn truy cập bot. Sẽ tự động thử lại sau.",
  "retryable": true
}
```

---

## 5. Dịch & Biên Tập AI — Open Claude

### Định Tuyến Task

```python
CloudLLMService.chat_completion(
    messages=[system_prompt, user_prompt],
    temperature=0.1,
    max_tokens=32000,
    task_type="news_translate"    # → gemini-2.5-pro
)
```

### System Prompt

**Bài tiếng Anh (`lang="en"`) — Dịch đầy đủ:**

```
Bạn là biên dịch viên báo chí chuyên nghiệp.
Nhiệm vụ duy nhất: dịch TOÀN BỘ nội dung bài báo sang Tiếng Việt.
KHÔNG giải thích, KHÔNG bình luận, KHÔNG thêm nội dung ngoài bài báo.
```

**Bài tiếng Việt (`lang="vi"`) — Biên tập lại:**

```
Bạn là biên tập viên báo chí chuyên nghiệp.
Nhiệm vụ duy nhất: biên tập lại bài báo Tiếng Việt thành bài hoàn chỉnh, chuẩn phát thanh.
```

### Yêu Cầu Dịch Thuật (user prompt)

1. Dòng đầu tiên = tiêu đề tiếng Việt
2. Giữ nguyên 100%: tên người, tổ chức, số liệu, ngày tháng, CVE IDs, IPs, tên phần mềm
3. KHÔNG rút gọn — dịch đầy đủ từng đoạn
4. Bỏ qua: menu điều hướng, quảng cáo, nút bấm, footer, link đăng ký
5. Văn phong phát thanh chuyên nghiệp (phù hợp đọc radio)
6. Chỉ văn bản thuần — không `*`, `#`, `[]`, `()`, `**`
7. Chỉ trả về bản dịch — không ghi chú hay giải thích

### Dọn Dẹp Artifact AI

Sau mỗi phản hồi AI:

```python
summary_vi = summary_vi.replace("*", "").replace("#", "").replace('"', "")
summary_vi = summary_vi.replace("<|eot_id|>", "").replace("<|end_header_id|>", "")
if summary_vi.lower().startswith("assistant"):
    summary_vi = summary_vi[len("assistant"):].strip()

# Xóa từ chối trách nhiệm AI ở cuối:
for pattern in [r"\(Đoạn văn tiếp theo.*$", r"\(Lưu ý:.*$",
                r"---.*$", r"Lưu ý:.*$", r"Note:.*$"]:
    summary_vi = re.sub(pattern, "", summary_vi, flags=re.DOTALL).strip()
```

### Chuỗi Dự Phòng 2 Tầng

```
Open Claude (gemini-2.5-pro)  → chính
        │ thất bại (timeout / 5xx / không có API key)
        ▼
LocalAI (LOCAL_AI_MODEL)       → dự phòng
```

Không có OpenRouter.

---

## 6. Text-to-Speech — Edge-TTS

### Giọng Đọc

```python
voice = "vi-VN-HoaiMyNeural"   # Nữ, tiếng Việt, Microsoft Neural TTS
```

### Tạo Audio

```python
import edge_tts, asyncio

text_to_read = SummaryService._fix_pronunciation(summary_vi)
communicate = edge_tts.Communicate(text_to_read, "vi-VN-HoaiMyNeural")
asyncio.run(communicate.save(audio_path))
# Lưu vào: /data/summaries/audio/{url_hash}.mp3
```

### Phát Âm Chuẩn

```python
def _fix_pronunciation(text):
    # Thay thế viết tắt bằng dạng đọc đầy đủ
    # Ví dụ: "CVE" → "C V E", "API" → "A P I"
    # Chuẩn hóa định dạng số cho giọng đọc tự nhiên
    ...
```

### Phục Vụ Audio

```
GET /api/news/audio/{filename}
→ StreamingResponse(open(audio_path, "rb"), media_type="audio/mpeg")
```

---

## 7. Kiến Trúc Cache

### Cache Tóm Tắt (JSON theo URL)

```
/data/summaries/{md5(url)}.json
```

```json
{
  "url": "https://thehackernews.com/...",
  "hash": "a7c3e259...",
  "audio_url": "/api/news/audio/a7c3e259.mp3",
  "summary_vi": "Tóm tắt bài báo bằng tiếng Việt...",
  "title_vi": "Tiêu đề tiếng Việt",
  "retryable": false
}
```

### Cache Audio (MP3)

```
/data/summaries/audio/{md5(url)}.mp3
```

### Cache Tin Tức In-Memory

```python
_cache: Dict[str, Dict] = {}
CACHE_TTL = 15  # phút

_cache[f"{category}_{limit}"] = {
    "data": result,
    "timestamp": time.time()
}
```

### Xử Lý Cache Miss

| Tình huống | Giá trị `audio_cached` | Hiển thị UI |
|------------|------------------------|------------|
| Chưa xử lý | `False` | ▶ Play (sẽ kích hoạt xử lý) |
| Đã xử lý xong | `True` | ▶ Play (audio tức thì) |
| Lỗi đã cache | `"error"` | ⚠ Hiển thị badge lỗi |

---

## 8. Hàng Đợi Worker Nền

Hai daemon thread chạy liên tục sau request đầu tiên:

### Worker Dịch Thuật

```python
_translation_queue = queue.Queue()

def _translation_worker():
    while True:
        task = _translation_queue.get()
        # Dịch hàng loạt tất cả tiêu đề tiếng Anh bằng Open Claude
        # Lưu vào /data/translations/{category}.json
```

### Worker Xử Lý LLM

```python
_llama_queue = queue.Queue()

def _llama_worker():
    while True:
        task = _llama_queue.get()
        articles = [a for a in task["articles"] if not a.get("audio_cached")]
        for article in articles:
            set_ai_status(f"Đang dịch bài: {article['title'][:60]}...")
            SummaryService.process_article(article["url"], article["lang"], article["title"])
        set_ai_status("Đang rảnh")
```

### API Trạng Thái AI

```
GET /api/news/ai-status
→ { "status": "Đang dịch bài: Critical Zero-Day in..." }
→ { "status": "Đang rảnh" }
```

Frontend poll endpoint này mỗi 5 giây để hiển thị chỉ báo đang xử lý theo thời gian thực.

---

## 9. Cache Dịch Thuật

File: [`backend/services/translation_service.py`](../backend/services/translation_service.py)

```
/data/translations/{category}.json
{
  "Critical Zero-Day in OpenSSL": "Lỗ hổng Zero-Day nghiêm trọng trong OpenSSL",
  "Ransomware Attack on US Hospital": "Tấn công ransomware vào bệnh viện Mỹ"
}
```

Bản dịch tiêu đề được cache vĩnh viễn để tránh dịch lại cùng tiêu đề qua nhiều lần làm mới.

### Worker Auto-Translation

Worker nền riêng biệt tự động dịch tất cả danh mục mỗi 30 phút:

```python
def _auto_translate_worker():
    while True:
        for cat in ("cybersecurity", "stocks_vietnam", "stocks_international"):
            news = NewsService.get_news(cat, limit=15)
            NewsService._bg_translate(news["articles"], cat)
        time.sleep(1800)   # 30 phút
```

---

## 10. Frontend — Trang Tin Tức

File: [`frontend-next/src/app/news/page.js`](../frontend-next/src/app/news/page.js)

### Danh Mục

```js
const CATEGORIES = [
  { id: "cybersecurity",         label: "🔐 An ninh mạng" },
  { id: "stocks_vietnam",        label: "📈 Chứng khoán VN" },
  { id: "stocks_international",  label: "💹 Thị trường toàn cầu" },
]
```

### `togglePlay` — Pipeline Audio

Hàm frontend cốt lõi điều khiển luồng summarize → TTS → phát:

```js
const togglePlay = async (e, article, forcePlay = false) => {
  // Đang phát → tạm dừng
  if (playingUrl === article.url && !forcePlay) {
    audioRef.current?.pause()
    setPlayingUrl(null)
    return
  }

  // Đã cache → phát ngay
  if (article.audio_cached === true) {
    const hash = article.url_hash
    audioRef.current.src = `/api/news/audio/${hash}.mp3`
    audioRef.current.play()
    setPlayingUrl(article.url)
    return
  }

  // Chưa cache → gọi backend
  setLoadingUrl(article.url)
  const res = await fetch('/api/news/summarize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: article.url, lang: article.lang, title: article.title })
  })

  if (!res.ok) {
    const errText = await res.text().catch(() => `HTTP ${res.status}`)
    throw new Error(errText || `Server error ${res.status}`)
  }

  const result = await res.json()
  if (result.error) throw new Error(result.error)

  audioRef.current.src = result.audio_url
  audioRef.current.play()
  setPlayingUrl(article.url)
}
```

### Quản Lý State

| State | Kiểu | Mục đích |
|-------|------|---------|
| `articles` | array | Bài báo danh mục hiện tại |
| `playingUrl` | string\|null | URL bài đang phát |
| `loadingUrl` | string\|null | URL bài đang xử lý |
| `categoryCache` | object | Cache bài theo danh mục (tránh load lại khi chuyển tab) |
| `history` | array | Lịch sử xử lý đầy đủ từ `/api/news/history` |
| `searchQuery` | string | Bộ lọc tìm kiếm trực tiếp |

### Panel Lịch Sử

Hiển thị tất cả bài đã xử lý từ `/data/articles_history.json` trong thanh bên. Mỗi mục hiển thị:
- Tiêu đề tiếng Việt (nếu có)
- Badge tình trạng audio
- Toggle hiện/ẩn văn bản tóm tắt tiếng Việt
