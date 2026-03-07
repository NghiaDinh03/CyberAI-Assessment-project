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

    // History & Reprocess States
    const [showHistory, setShowHistory] = useState(false)
    const [historyData, setHistoryData] = useState([])
    const [historyTab, setHistoryTab] = useState('all')
    const [historyLoading, setHistoryLoading] = useState(false)
    const [reprocessing, setReprocessing] = useState({}) // { [url]: boolean }

    const fetchHistory = useCallback(async (cat = 'all') => {
        setHistoryLoading(true)
        try {
            const res = await fetch(`/api/news/history?category=${cat}`)
            if (res.ok) {
                const data = await res.json()
                setHistoryData(data)
            } else {
                setHistoryData([])
            }
        } catch (err) {
            console.warn('History fetch failure:', err)
            setHistoryData([])
        } finally {
            setHistoryLoading(false)
        }
    }, [])

    useEffect(() => {
        if (showHistory) fetchHistory(historyTab)
    }, [showHistory, historyTab, fetchHistory])

    const handleReprocess = async (e, article) => {
        e.preventDefault()
        e.stopPropagation()
        if (!confirm('Dịch và tóm tắt lại bài báo này từ đầu?')) return

        setReprocessing(p => ({ ...p, [article.url]: true }))
        try {
            const res = await fetch('/api/news/reprocess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: article.url })
            })
            if (res.ok) {
                alert('Đã đưa bài báo vào hàng đợi. Vui lòng đợi trong giây lát...')
                setAudioData(prev => {
                    const next = { ...prev }
                    delete next[article.url]
                    return next
                })
                fetchNews(activeTab)
            } else {
                const data = await res.json()
                alert(data.error || 'Lỗi hệ thống')
            }
        } catch (err) {
            alert('Không thể kết nối máy chủ')
        } finally {
            setReprocessing(p => ({ ...p, [article.url]: false }))
        }
    }

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
                    if (!res.ok) throw new Error('Summarize unstable')
                    const result = await res.json()
                    finalUrl = result.audio_url
                    finalText = result.summary_vi
                } catch (err) {
                    console.error("Audio cache fetch error:", err)
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
            if (!res.ok) {
                const text = await res.text()
                throw new Error(text || 'Server error')
            }
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
            console.error("Audio error:", err)
            setAudioData(prev => ({ ...prev, [article.url]: { status: 'error' } }))
        }
    }

    useEffect(() => {
        forcePlayRef.current = (article) => togglePlay(null, article, true)
    }, [togglePlay])

    const [categoryCache, setCategoryCache] = useState({}) // { [cat]: { articles, cached_at } }
    const fetchNews = useCallback(async (category, isBackground = false) => {
        if (!isBackground) {
            if (categoryCache[category]) {
                setArticles(categoryCache[category].articles)
                setLastUpdate(categoryCache[category].cached_at)
                setLoading(false) // Show cached data immediately
            } else {
                setLoading(true)
            }
            setError('')
        }

        try {
            const res = await fetch(`/api/news?category=${category}&limit=20`)
            if (!res.ok) throw new Error('API unstable')
            const contentType = res.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error("Not JSON response");
            }
            const data = await res.json()
            if (data.error) {
                if (!isBackground) {
                    setError(data.error)
                    setArticles([])
                }
            } else {
                const newArticles = data.articles || []
                setArticles(newArticles)
                setLastUpdate(data.cached_at || '')
                setCategoryCache(prev => ({
                    ...prev,
                    [category]: { articles: newArticles, cached_at: data.cached_at }
                }))
            }
        } catch (err) {
            console.warn('Silent news update failure:', err)
            if (!isBackground && !categoryCache[category]) setError('Không thể tải tin tức lúc này')
        } finally {
            setLoading(false)
        }
    }, [categoryCache])

    const searchNews = useCallback(async (query) => {
        if (!query.trim()) {
            setSearchResults(null)
            return
        }
        setSearching(true)
        try {
            const res = await fetch(`/api/news/search?q=${encodeURIComponent(query)}&limit=20`)
            if (!res.ok) throw new Error('Search failed')
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
    }, [activeTab]) // Removed fetchNews from deps to avoid loop with categoryCache

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
                if (res.ok) {
                    const contentType = res.headers.get("content-type");
                    if (contentType && contentType.includes("application/json")) {
                        const data = await res.json()
                        setAiStatus(data.status || 'Đang rảnh')
                    }
                } else {
                    setAiStatus('Kết nối...')
                }
            } catch { 
                setAiStatus('Mất kết nối')
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
                    <button className={styles.refreshBtn} onClick={() => setShowHistory(true)} style={{ marginRight: '10px' }}>
                        🕒 Lịch sử 7 ngày
                    </button>
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
                            <div
                                key={i}
                                className={styles.card}
                            >
                                <button 
                                    className={styles.reprocessBtnCorner} 
                                    onClick={(e) => handleReprocess(e, article)}
                                    disabled={reprocessing[article.url]}
                                    title="Dịch lại bài báo này"
                                >
                                    {reprocessing[article.url] ? '⏳' : '🔄'}
                                </button>
                                <div className={styles.cardBody}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '4px' }}>
                                        <a
                                            href={article.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className={styles.cardTitle}
                                            style={{ margin: 0, textDecoration: 'none', color: 'inherit' }}
                                        >
                                            {article.title} 🔗
                                        </a>
                                        {article.audio_cached && article.audio_cached !== 'error' ? (
                                            <button
                                                onClick={(e) => togglePlay(e, article)}
                                                style={{ background: audioData[article.url]?.status === 'playing' ? '#10b981' : 'transparent', color: audioData[article.url]?.status === 'playing' ? '#fff' : '#3b82f6', border: '1px solid', borderColor: audioData[article.url]?.status === 'playing' ? '#10b981' : '#3b82f6', borderRadius: '4px', padding: '2px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', fontWeight: 'bold' }}
                                                title={audioData[article.url]?.status === 'playing' ? 'Dừng đọc' : 'Nghe Tóm Tắt AI'}
                                            >
                                                {audioData[article.url]?.status === 'loading' ? '⏳ Đang tải' : audioData[article.url]?.status === 'playing' ? '⏸️ Đang phát' : '▶️ Nghe'}
                                            </button>
                                        ) : !article.audio_cached ? (
                                            <span style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px', border: '1px dashed #64748b', padding: '2px 8px', borderRadius: '4px' }}>
                                                ⏳ Đang tạo Audio
                                            </span>
                                        ) : null}
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
                                    {(audioData[article.url]?.text || article.summary_text || article.audio_cached === 'error') && (
                                        <div style={{ marginTop: '5px' }}>
                                            <button
                                                className={styles.expandBtn}
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    setExpandedArticles(prev => ({ ...prev, [article.url]: !prev[article.url] }));
                                                }}
                                            >
                                                {expandedArticles[article.url] ? '▲ Thu gọn tóm tắt' : '▼ Xem nội dung tóm tắt' + (article.audio_cached === 'error' ? ' (Có lỗi)' : '')}
                                            </button>

                                            {expandedArticles[article.url] && (
                                                <div style={{ 
                                                    marginTop: '8px', 
                                                    padding: '10px', 
                                                    background: '#1e293b', 
                                                    borderRadius: '6px', 
                                                    fontSize: '13px', 
                                                    color: article.audio_cached === 'error' ? '#fca5a5' : '#cbd5e1', 
                                                    borderLeft: article.audio_cached === 'error' ? '3px solid #ef4444' : '3px solid #3b82f6', 
                                                    lineHeight: '1.5' 
                                                }}>
                                                    {article.audio_cached === 'error' ? (
                                                        <>⚠️ <b>Lỗi AI:</b> {article.summary_text || 'Hệ thống AI đang quá tải, vui lòng thử lại sau giây lát.'}</>
                                                    ) : (
                                                        <>🎙️ <b>AI tóm tắt:</b> {audioData[article.url]?.text || article.summary_text}</>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                                <a
                                    href={article.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className={styles.cardRight}
                                    style={{ textDecoration: 'none' }}
                                >
                                    <span className={styles.cardLang}>
                                        {article.lang === 'vi' ? '🇻🇳' : '🌐'}
                                    </span>
                                    <span className={styles.cardLink}>→</span>
                                </a>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {showHistory && <div className={styles.historyOverlay} onClick={() => setShowHistory(false)} />}
            <div className={`${styles.historySidebar} ${showHistory ? styles.open : ''}`}>
                <div className={styles.historyHeader}>
                    <h2>Lịch sử tin tức</h2>
                    <button className={styles.historyClose} onClick={() => setShowHistory(false)}>✕</button>
                </div>
                <div className={styles.historyTabs}>
                    <button className={`${styles.htab} ${historyTab === 'all' ? styles.active : ''}`} onClick={() => setHistoryTab('all')}>Tất cả</button>
                    {CATEGORIES.map(c => (
                        <button key={c.id} className={`${styles.htab} ${historyTab === c.id ? styles.active : ''}`} onClick={() => setHistoryTab(c.id)}>{c.name}</button>
                    ))}
                </div>
                <div className={styles.historyContent}>
                    {historyLoading ? (
                        <div style={{ textAlign: 'center', padding: '20px', color: '#64748b', fontSize: '13px' }}>Đang tải lịch sử...</div>
                    ) : historyData.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '20px', color: '#64748b', fontSize: '13px' }}>Không có lịch sử 7 ngày qua</div>
                    ) : (
                        historyData.map((hItem, idx) => (
                            <div key={idx} className={styles.historyItem}>
                                <a href={hItem.url} target="_blank" rel="noopener noreferrer" className={styles.historyItemTitle}>
                                    {hItem.title_vi || hItem.title}
                                </a>
                                {hItem.title_vi && hItem.title_vi !== hItem.title && (
                                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px', fontStyle: 'italic' }}>
                                        Gốc: {hItem.title}
                                    </div>
                                )}
                                <div className={styles.historyItemMeta}>
                                    <span>{new Date(hItem.added_at).toLocaleString('vi-VN')}</span>
                                    <span>
                                        {hItem.audio_cached === true ? '✅ Có Audio' : (hItem.audio_cached === 'error' ? '❌ Lỗi' : '⏳ Chờ')}
                                    </span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}
