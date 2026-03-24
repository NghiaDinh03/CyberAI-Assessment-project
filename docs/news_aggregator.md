# News Aggregator — Technical Deep Dive

<div align="center">

[![🇬🇧 English](https://img.shields.io/badge/English-News_Aggregator-blue?style=flat-square)](news_aggregator.md)
[![🇻🇳 Tiếng Việt](https://img.shields.io/badge/Tiếng_Việt-Tin_tức_tổng_hợp-red?style=flat-square)](news_aggregator_vi.md)

</div>

---

## Table of Contents

1. [Overview](#1-overview)
2. [Full Pipeline Flow](#2-full-pipeline-flow)
3. [RSS Sources](#3-rss-sources)
4. [Article Scraping — 3-Strategy Chain](#4-article-scraping--3-strategy-chain)
5. [AI Translation & Rewrite — Open Claude](#5-ai-translation--rewrite--open-claude)
6. [Text-to-Speech — Edge-TTS](#6-text-to-speech--edge-tts)
7. [Caching Architecture](#7-caching-architecture)
8. [Background Worker Queues](#8-background-worker-queues)
9. [Translation Cache](#9-translation-cache)
10. [Frontend — News Page](#10-frontend--news-page)

---

## 1. Overview

The News Aggregator module:

1. **Fetches** articles from 9 RSS feeds across 3 categories
2. **Translates** English article titles to Vietnamese (batch, cached)
3. **On demand** (user clicks play): scrapes full content, translates/rewrites with AI, generates audio
4. **Caches** everything — no duplicate AI calls for the same URL

| Layer | Technology |
|-------|-----------|
| RSS parsing | Python `xml.etree.ElementTree` + `requests` |
| Web scraping | `requests+BeautifulSoup4` → `trafilatura` → `newspaper3k` |
| AI translation | Open Claude (gemini-2.5-pro) → LocalAI fallback |
| Text-to-Speech | Microsoft Edge TTS (`edge-tts`, voice: `vi-VN-HoaiMyNeural`) |
| Audio format | MP3, stored at `/data/summaries/audio/` |
| Summary cache | JSON files at `/data/summaries/{hash}.json` |

---

## 2. Full Pipeline Flow

```
User opens /news page
        │
        ▼
GET /api/news?category=cybersecurity
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│  NewsService.get_news(category, limit=15)                    │
│                                                              │
│  1. Check in-memory cache (CACHE_TTL = 15 min)              │
│     → HIT: return cached data immediately                    │
│     → MISS: continue                                         │
│                                                              │
│  2. _parse_rss() × 3 sources                                │
│     → Fetch each RSS feed (HTTP GET)                         │
│     → Parse XML: title, url, date, description               │
│     → Sort by date desc, trim to limit                       │
│                                                              │
│  3. For each article:                                        │
│     → SummaryService._get_cache(url)                         │
│       → audio_cached = true/false/error                     │
│                                                              │
│  4. _apply_translations(articles, category)                  │
│     → Load title_vi from translation JSON cache              │
│                                                              │
│  5. _update_history(articles)                                │
│     → Persist to /data/articles_history.json                │
│                                                              │
│  6. Enqueue untranslated articles → _translation_queue       │
│  7. Enqueue un-summarized articles → _llama_queue            │
└──────────────────────────────┬───────────────────────────────┘
                               │ return articles list
                               ▼
                    User sees article cards
                    (audio_cached badge shown)
                               │
                    User clicks ▶ Play button
                               │
                               ▼
POST /api/news/summarize { url, lang, title }
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  SummaryService.process_article(url)   [per-URL lock]        │
│                                                              │
│  Step 1 — Scrape article content                             │
│    Attempt 1: requests + BeautifulSoup4                      │
│    Attempt 2: trafilatura                                    │
│    Attempt 3: newspaper3k                                    │
│    Truncate at 30,000 chars                                  │
│                                                              │
│  Step 2 — Open Claude: translate/rewrite to Vietnamese       │
│    task_type = "news_translate" → gemini-2.5-pro             │
│    temperature = 0.1, max_tokens = 32000                     │
│    Strip AI artifacts (* # <|eot_id|> "assistant" prefix)    │
│    Strip trailing notes/disclaimers                          │
│                                                              │
│  Step 3 — Edge-TTS: generate MP3 audio                      │
│    Voice: vi-VN-HoaiMyNeural                                 │
│    Save to: /data/summaries/audio/{url_hash}.mp3             │
│                                                              │
│  Cache JSON: /data/summaries/{url_hash}.json                 │
│    { audio_url, summary_vi, title_vi, url, hash }           │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
              { audio_url, summary_vi, title_vi }
                               │
                    Frontend plays MP3 audio
```

---

## 3. RSS Sources

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

**Cache TTL:** `CACHE_TTL = 15` minutes (in-memory `_cache` dict)

---

## 4. Article Scraping — 3-Strategy Chain

File: [`backend/services/summary_service.py`](../backend/services/summary_service.py)

### Strategy 1 — requests + BeautifulSoup4

```python
def _scrape_with_requests_bs4(url):
    resp = requests.get(url, headers=_get_random_headers(), timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    # Remove noise: nav, aside, footer, script, style, ads
    for tag in soup(["nav","aside","footer","script","style","form","button"]):
        tag.decompose()
    # Extract paragraphs ≥ 40 chars
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")
                  if len(p.get_text(strip=True)) >= 40]
    return "\n\n".join(paragraphs)
```

### Strategy 2 — trafilatura

```python
def _scrape_with_trafilatura(url):
    downloaded = trafilatura.fetch_url(url)
    return trafilatura.extract(downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False)
```

### Strategy 3 — newspaper3k

```python
def _scrape_with_newspaper(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.text
```

### Fallback on Block / Insufficient Content

If all strategies fail or return < 300 chars:

```python
if title:
    text = f"{title}\n\n{text or ''}"
    # Use title + partial text as minimal content (≥ 100 chars to continue)
```

If domain blocks bots (HTTP 401/403/429):

```json
{
  "error": "❌ Trang thehackernews.com chặn truy cập bot. Sẽ tự động thử lại sau.",
  "retryable": true
}
```

---

## 5. AI Translation & Rewrite — Open Claude

### Task Routing

```python
CloudLLMService.chat_completion(
    messages=[system_prompt, user_prompt],
    temperature=0.1,
    max_tokens=32000,
    task_type="news_translate"    # → gemini-2.5-pro
)
```

### System Prompts

**For English articles (`lang="en"`) — Full translation:**

```
Bạn là biên dịch viên báo chí chuyên nghiệp.
Nhiệm vụ duy nhất: dịch TOÀN BỘ nội dung bài báo sang Tiếng Việt.
KHÔNG giải thích, KHÔNG bình luận, KHÔNG thêm nội dung ngoài bài báo.
```

**For Vietnamese articles (`lang="vi"`) — Editorial rewrite:**

```
Bạn là biên tập viên báo chí chuyên nghiệp.
Nhiệm vụ duy nhất: biên tập lại bài báo Tiếng Việt thành bài hoàn chỉnh, chuẩn phát thanh.
```

### Translation Requirements (user prompt)

1. First line = Vietnamese headline
2. Preserve 100%: names, organizations, numbers, dates, CVE IDs, IPs, software names
3. Do NOT summarize — translate every paragraph in full
4. Skip: navigation menus, ads, buttons, footers, subscribe links
5. Broadcast-quality writing style (suitable for radio reading)
6. Plain text only — no `*`, `#`, `[]`, `()`, `**`
7. Return translation only — no notes or explanations

### AI Artifact Cleanup

After every AI response:

```python
summary_vi = summary_vi.replace("*", "").replace("#", "").replace('"', "")
summary_vi = summary_vi.replace("<|eot_id|>", "").replace("<|end_header_id|>", "")
if summary_vi.lower().startswith("assistant"):
    summary_vi = summary_vi[len("assistant"):].strip()

# Remove trailing AI disclaimers:
for pattern in [r"\(Đoạn văn tiếp theo.*$", r"\(Lưu ý:.*$",
                r"---.*$", r"Lưu ý:.*$", r"Note:.*$"]:
    summary_vi = re.sub(pattern, "", summary_vi, flags=re.DOTALL).strip()
```

### 2-Tier Fallback

```
Open Claude (gemini-2.5-pro)  → primary
        │ fail (timeout / 5xx / no API key)
        ▼
LocalAI (LOCAL_AI_MODEL)       → fallback
```

No OpenRouter involved.

---

## 6. Text-to-Speech — Edge-TTS

### Voice

```python
voice = "vi-VN-HoaiMyNeural"   # Female Vietnamese, Microsoft Neural TTS
```

### Generation

```python
import edge_tts, asyncio

text_to_read = SummaryService._fix_pronunciation(summary_vi)
communicate = edge_tts.Communicate(text_to_read, "vi-VN-HoaiMyNeural")
asyncio.run(communicate.save(audio_path))
# Saves to: /data/summaries/audio/{url_hash}.mp3
```

### Pronunciation Fix

```python
def _fix_pronunciation(text):
    # Replace abbreviations with full spoken forms
    # e.g., "CVE" → "C V E", "API" → "A P I"
    # Normalizes number formats for natural speech
    ...
```

### Audio Serving

```
GET /api/news/audio/{filename}
→ StreamingResponse(open(audio_path, "rb"), media_type="audio/mpeg")
```

---

## 7. Caching Architecture

### Summary Cache (JSON per URL)

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

### Audio Cache (MP3)

```
/data/summaries/audio/{md5(url)}.mp3
```

### In-Memory News Cache

```python
_cache: Dict[str, Dict] = {}
CACHE_TTL = 15  # minutes

_cache[f"{category}_{limit}"] = {
    "data": result,
    "timestamp": time.time()
}
```

### Cache Miss Handling

| Scenario | `audio_cached` value | UI display |
|----------|----------------------|-----------|
| Not processed yet | `False` | ▶ Play (will trigger processing) |
| Processing done | `True` | ▶ Play (instant audio) |
| Error cached | `"error"` | ⚠ Error badge shown |

---

## 8. Background Worker Queues

Two daemon threads run continuously after first request:

### Translation Worker

```python
_translation_queue = queue.Queue()

def _translation_worker():
    while True:
        task = _translation_queue.get()
        # Batch-translate all English titles using Open Claude
        # Save to /data/translations/{category}.json
```

### LLM Processing Worker

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

### AI Status API

```
GET /api/news/ai-status
→ { "status": "Đang dịch bài: Critical Zero-Day in..." }
→ { "status": "Đang rảnh" }
```

The frontend polls this endpoint every 5 seconds to show a live processing indicator.

---

## 9. Translation Cache

File: [`backend/services/translation_service.py`](../backend/services/translation_service.py)

```
/data/translations/{category}.json
{
  "Critical Zero-Day in OpenSSL": "Lỗ hổng Zero-Day nghiêm trọng trong OpenSSL",
  "Ransomware Attack on US Hospital": "Tấn công ransomware vào bệnh viện Mỹ"
}
```

Title translations are cached permanently to avoid re-translating the same headlines across multiple refreshes.

### Auto-Translation Worker

A separate background worker auto-translates all categories every 30 minutes:

```python
def _auto_translate_worker():
    while True:
        for cat in ("cybersecurity", "stocks_vietnam", "stocks_international"):
            news = NewsService.get_news(cat, limit=15)
            NewsService._bg_translate(news["articles"], cat)
        time.sleep(1800)   # 30 minutes
```

---

## 10. Frontend — News Page

File: [`frontend-next/src/app/news/page.js`](../frontend-next/src/app/news/page.js)

### Categories

```js
const CATEGORIES = [
  { id: "cybersecurity",         label: "🔐 Cybersecurity" },
  { id: "stocks_vietnam",        label: "📈 VN Stocks" },
  { id: "stocks_international",  label: "💹 Global Markets" },
]
```

### `togglePlay` — Audio Pipeline

The core frontend function that drives the summarize → TTS → play flow:

```js
const togglePlay = async (e, article, forcePlay = false) => {
  // If already playing → pause
  if (playingUrl === article.url && !forcePlay) {
    audioRef.current?.pause()
    setPlayingUrl(null)
    return
  }

  // If audio cached → play immediately
  if (article.audio_cached === true) {
    const hash = article.url_hash
    audioRef.current.src = `/api/news/audio/${hash}.mp3`
    audioRef.current.play()
    setPlayingUrl(article.url)
    return
  }

  // Not cached → call backend
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

### State Management

| State | Type | Purpose |
|-------|------|---------|
| `articles` | array | Current category articles |
| `playingUrl` | string\|null | URL of currently playing article |
| `loadingUrl` | string\|null | URL of article being processed |
| `categoryCache` | object | Per-category article cache (avoids refetch on tab switch) |
| `history` | array | Full processing history from `/api/news/history` |
| `searchQuery` | string | Live search filter |

### History Panel

Displays all processed articles from `/data/articles_history.json` in a sidebar. Each entry shows:
- Vietnamese title (if available)
- Audio availability badge
- Toggle to show/hide Vietnamese summary text
