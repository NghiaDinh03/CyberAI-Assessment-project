'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import styles from './page.module.css'

const CATEGORIES = [
    { id: 'cybersecurity', name: 'An Ninh Mạng', icon: '🛡️' },
    { id: 'stocks_international', name: 'Cổ Phiếu Quốc Tế', icon: '📈' },
    { id: 'stocks_vietnam', name: 'Chứng Khoán VN', icon: '💹' },
]

export default function NewsPage() {
    const [activeTab, setActiveTab] = useState('cybersecurity')
    const [articles, setArticles] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [lastUpdate, setLastUpdate] = useState('')
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState(null)
    const [searching, setSearching] = useState(false)
    const [aiStatus, setAiStatus] = useState('Đang rảnh')
    const searchTimerRef = useRef(null)

    // Voice & Summary states
    const [audioData, setAudioData] = useState({}) // { [url]: { status: 'loading'|'ready'|'playing'|'error', audioUrl: '', text: '' } }
    const audioRef = useRef(null)
    const [expandedArticles, setExpandedArticles] = useState({})
    const [isPlayAll, setIsPlayAll] = useState(false)
    const playStateRef = useRef({ isPlayAll: false, currentUrl: null, articles: [] })
    const forcePlayRef = useRef(null)

    const playNext = useCallback(() => {
        const state = playStateRef.current
        if (!state.isPlayAll || !state.currentUrl) return
        const idx = state.articles.findIndex(a => a.url === state.currentUrl)
        if (idx >= 0) {
            let nextArt = null
            for (let i = idx + 1; i < state.articles.length; i++) {
                if (state.articles[i].audio_cached || state.articles[i].summary_text) {
                    nextArt = state.articles[i]
                    break
                }
            }
            if (nextArt) {
                if (forcePlayRef.current) forcePlayRef.current(nextArt)
            } else {
                setIsPlayAll(false)
            }
        }
    }, [])

    useEffect(() => {
        audioRef.current = new Audio()
        audioRef.current.onended = () => {
            setAudioData(prev => {
                const next = { ...prev }
                for (let k in next) {
                    if (next[k].status === 'playing') next[k].status = 'ready'
                }
                return next
            })
            playNext()
        }
    }, [playNext])

    const togglePlay = async (e, article, forcePlay = false) => {
        if (e) e.preventDefault()
        const data = audioData[article.url]

        if (data?.status === 'playing' && !forcePlay) {
            audioRef.current.pause()
            setAudioData(prev => ({ ...prev, [article.url]: { ...prev[article.url], status: 'ready' } }))
            playStateRef.current.currentUrl = null
            return
        }

        playStateRef.current.currentUrl = article.url

        if (data?.status === 'ready' || article.audio_cached) {
            // Check if we need to fetch the audio url (if cached but not in audioData)
            let finalUrl = data?.audioUrl
            let finalText = data?.text || article.summary_text

            if (!finalUrl && article.audio_cached) {
                try {
                    setAudioData(prev => ({ ...prev, [article.url]: { status: 'loading' } }))
                    const res = await fetch('/api/news/summarize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: article.url, lang: article.lang, title: article.title_vi || article.title })
                    })
                    const result = await res.json()
                    finalUrl = result.audio_url
                    finalText = result.summary_vi
                } catch (err) {
                    setAudioData(prev => ({ ...prev, [article.url]: { status: 'error' } }))
                    return
                }
            }

            setAudioData(prev => {
                const next = { ...prev }
                for (let k in next) { if (next[k]?.status === 'playing') next[k].status = 'ready' }
                next[article.url] = { status: 'playing', audioUrl: finalUrl, text: finalText }
                return next
            })
            if (!audioRef.current.src.includes(finalUrl)) {
                audioRef.current.src = finalUrl
            }
            audioRef.current.play()
            return
        }

        setAudioData(prev => ({ ...prev, [article.url]: { status: 'loading' } }))
        try {
            const res = await fetch('/api/news/summarize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: article.url, lang: article.lang, title: article.title_vi || article.title })
            })
            const result = await res.json()
            if (result.error) throw new Error(result.error)

            setAudioData(prev => {
                const next = { ...prev }
                for (let k in next) { if (next[k]?.status === 'playing') next[k].status = 'ready' }
                next[article.url] = { status: 'playing', audioUrl: result.audio_url, text: result.summary_vi }
                return next
            })

            audioRef.current.src = result.audio_url
            audioRef.current.play()
        } catch (err) {
            alert("Lỗi tải âm thanh: " + err.message)
            setAudioData(prev => ({ ...prev, [article.url]: { status: 'error' } }))
        }
    }

    useEffect(() => {
        forcePlayRef.current = (article) => togglePlay(null, article, true)
    }, [togglePlay])

    const fetchNews = useCallback(async (category, isBackground = false) => {
        if (!isBackground) setLoading(true)
        if (!isBackground) setError('')
        try {
            const res = await fetch(`/api/news?category=${category}&limit=20`)
            const data = await res.json()
            if (data.error) {
                setError(data.error)
                setArticles([])
            } else {
                setArticles(data.articles || [])
                setLastUpdate(data.cached_at || '')
            }
        } catch {
            setError('Không thể tải tin tức')
            setArticles([])
        } finally {
            setLoading(false)
        }
    }, [])

    const searchNews = useCallback(async (query) => {
        if (!query.trim()) {
            setSearchResults(null)
            return
        }
        setSearching(true)
        try {
            const res = await fetch(`/api/news/search?q=${encodeURIComponent(query)}&limit=20`)
            const data = await res.json()
            setSearchResults(data)
        } catch {
            setSearchResults({ articles: [], count: 0 })
        } finally {
            setSearching(false)
        }
    }, [])

    useEffect(() => {
        fetchNews(activeTab)
    }, [activeTab, fetchNews])

    const displayArticles = searchResults ? searchResults.articles : articles
    const isSearchMode = searchResults !== null

    const articlesRef = useRef(articles)
    useEffect(() => {
        articlesRef.current = displayArticles
        playStateRef.current.articles = displayArticles
        playStateRef.current.isPlayAll = isPlayAll
    }, [displayArticles, isPlayAll])

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const res = await fetch('/api/news/ai-status')
                const data = await res.json()
                setAiStatus(data.status || 'Đang rảnh')
            } catch (err) {
                console.error("AI status error:", err)
            }
        }, 2000)
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        let tick = 0;
        const interval = setInterval(() => {
            tick += 5;
            const hasPending = articlesRef.current.some(a => (a.lang === 'en' && !a.title_vi) || !a.audio_cached)

            if (hasPending || tick >= 300) {
                fetchNews(activeTab, true)
                if (tick >= 300) tick = 0;
            }
        }, 5000)
        return () => clearInterval(interval)
    }, [activeTab, fetchNews])

    const handleSearchInput = (e) => {
        const val = e.target.value
        setSearchQuery(val)
        if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
        if (!val.trim()) {
            setSearchResults(null)
            return
        }
        searchTimerRef.current = setTimeout(() => searchNews(val), 500)
    }

    const clearSearch = () => {
        setSearchQuery('')
        setSearchResults(null)
    }

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.headerLeft}>
                    <h1 className={styles.title}>Tin tức</h1>
                    <span className={styles.subtitle}>Tổng hợp tin tức thị trường, chứng khoán và an ninh mạng giúp AI phân tích</span>
                </div>
                <div className={styles.headerRight}>
                    {aiStatus !== 'Đang rảnh' && (
                        <div className={styles.aiMonitor}>
                            <span className={styles.pulse}></span>
                            <span className={styles.statusText}>🤖 {aiStatus}</span>
                        </div>
                    )}
                </div>
            </div>

            <div className={styles.searchWrap}>
                <div className={styles.searchBox}>
                    <span className={styles.searchIcon}>🔍</span>
                    <input
                        className={styles.searchInput}
                        type="text"
                        placeholder="Tìm kiếm tin tức..."
                        value={searchQuery}
                        onChange={handleSearchInput}
                    />
                    {searchQuery && (
                        <button className={styles.searchClear} onClick={clearSearch}>✕</button>
                    )}
                </div>
                {searching && <span className={styles.searchStatus}>Đang tìm...</span>}
                {isSearchMode && !searching && (
                    <span className={styles.searchStatus}>
                        {searchResults.count} kết quả cho &ldquo;{searchQuery}&rdquo;
                    </span>
                )}
            </div>

            {!isSearchMode && (
                <div className={styles.tabsContainer}>
                    <div className={styles.tabs}>
                        {CATEGORIES.map(cat => (
                            <button
                                key={cat.id}
                                className={`${styles.tab} ${activeTab === cat.id ? styles.tabActive : ''}`}
                                onClick={() => setActiveTab(cat.id)}
                            >
                                <span className={styles.tabIcon}>{cat.icon}</span>
                                <span className={styles.tabName}>{cat.name}</span>
                            </button>
                        ))}
                    </div>

                    <button
                        className={styles.playAllBtn}
                        onClick={() => {
                            if (isPlayAll) {
                                setIsPlayAll(false)
                                audioRef.current.pause()
                                setAudioData(prev => {
                                    const next = { ...prev }
                                    for (let k in next) { if (next[k]?.status === 'playing') next[k].status = 'ready' }
                                    return next
                                })
                            } else {
                                setIsPlayAll(true)
                                const firstPlayable = displayArticles.find(a => a.audio_cached)
                                if (firstPlayable) forcePlayRef.current(firstPlayable)
                            }
                        }}
                    >
                        {isPlayAll ? '⏹️ Dừng phát' : '▶️ Phát tất cả'}
                    </button>
                </div>
            )}

            <div className={styles.content}>
                {(loading && !isSearchMode) ? (
                    <div className={styles.loadingWrap}>
                        <div className={styles.spinner} />
                        <p>Đang tải tin tức...</p>
                    </div>
                ) : error && !isSearchMode ? (
                    <div className={styles.errorWrap}>
                        <p>⚠️ {error}</p>
                        <button className={styles.retryBtn} onClick={() => fetchNews(activeTab)}>Thử lại</button>
                    </div>
                ) : displayArticles.length === 0 ? (
                    <div className={styles.emptyWrap}>
                        <p>{isSearchMode ? 'Không tìm thấy kết quả' : 'Không có tin tức nào'}</p>
                    </div>
                ) : (
                    <div className={styles.list}>
                        {displayArticles.map((article, i) => (
                            <a
                                key={i}
                                href={article.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={styles.card}
                            >
                                <div className={styles.cardBody}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '4px' }}>
                                        <h3 className={styles.cardTitle} style={{ margin: 0 }}>{article.title}</h3>
                                        {article.audio_cached ? (
                                            <button
                                                onClick={(e) => togglePlay(e, article)}
                                                style={{ background: audioData[article.url]?.status === 'playing' ? '#10b981' : 'transparent', color: audioData[article.url]?.status === 'playing' ? '#fff' : '#3b82f6', border: '1px solid', borderColor: audioData[article.url]?.status === 'playing' ? '#10b981' : '#3b82f6', borderRadius: '4px', padding: '2px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', fontWeight: 'bold' }}
                                                title={audioData[article.url]?.status === 'playing' ? 'Dừng đọc' : 'Nghe Tóm Tắt AI'}
                                            >
                                                {audioData[article.url]?.status === 'loading' ? '⏳ Đang tải' : audioData[article.url]?.status === 'playing' ? '⏸️ Đang phát' : '▶️ Nghe'}
                                            </button>
                                        ) : (
                                            <span style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px', border: '1px dashed #64748b', padding: '2px 8px', borderRadius: '4px' }}>
                                                ⏳ Đang tạo Audio
                                            </span>
                                        )}
                                    </div>
                                    {article.title_vi && (
                                        <p className={styles.cardTitleVi}>{article.title_vi}</p>
                                    )}
                                    <div className={styles.cardMeta}>
                                        <span className={styles.cardSource}>{article.icon} {article.source}</span>
                                        {article.date && <span className={styles.cardDate}>{article.date}</span>}
                                        {article.tag && (
                                            <span className={styles.cardCategory} style={{ backgroundColor: '#10b981', color: '#fff', marginLeft: '6px' }}>
                                                🏷️ {article.tag}
                                            </span>
                                        )}
                                        {isSearchMode && article.category && (
                                            <span className={styles.cardCategory}>
                                                {CATEGORIES.find(c => c.id === article.category)?.name || article.category}
                                            </span>
                                        )}
                                    </div>
                                    {article.description && (
                                        <p className={styles.cardDesc}>{article.description}</p>
                                    )}
                                    {(audioData[article.url]?.text || article.summary_text) && (
                                        <div style={{ marginTop: '5px' }}>
                                            <button
                                                className={styles.expandBtn}
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    setExpandedArticles(prev => ({ ...prev, [article.url]: !prev[article.url] }));
                                                }}
                                            >
                                                {expandedArticles[article.url] ? '▲ Thu gọn tóm tắt' : '▼ Xem nội dung tóm tắt'}
                                            </button>

                                            {expandedArticles[article.url] && (
                                                <div style={{ marginTop: '8px', padding: '10px', background: '#1e293b', borderRadius: '6px', fontSize: '13px', color: '#cbd5e1', borderLeft: '3px solid #3b82f6', lineHeight: '1.5' }}>
                                                    🎙️ <b>AI tóm tắt:</b> {audioData[article.url]?.text || article.summary_text}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                                <div className={styles.cardRight}>
                                    <span className={styles.cardLang}>
                                        {article.lang === 'vi' ? '🇻🇳' : '🌐'}
                                    </span>
                                    <span className={styles.cardLink}>→</span>
                                </div>
                            </a>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
