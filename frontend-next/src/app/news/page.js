'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import styles from './page.module.css'

const CATEGORIES = [
    { id: 'cybersecurity', name: 'An Ninh Mạng', icon: '🛡️' },
    { id: 'stocks_international', name: 'Cổ Phiếu Quốc Tế', icon: '📈' },
    { id: 'stocks_vietnam', name: 'Chứng Khoán VN', icon: '🇻🇳' },
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
    const searchTimerRef = useRef(null)

    const fetchNews = useCallback(async (category) => {
        setLoading(true)
        setError('')
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

    useEffect(() => {
        const interval = setInterval(() => fetchNews(activeTab), 300000)
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

    const displayArticles = searchResults ? searchResults.articles : articles
    const isSearchMode = searchResults !== null

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.headerLeft}>
                    <h1 className={styles.title}>Tin tức</h1>
                    <span className={styles.subtitle}>Cập nhật realtime từ các nguồn uy tín</span>
                </div>
                <div className={styles.headerRight}>
                    {lastUpdate && <span className={styles.lastUpdate}>{lastUpdate}</span>}
                    <button className={styles.refreshBtn} onClick={() => fetchNews(activeTab)} disabled={loading}>
                        {loading ? '⏳' : '🔄'}
                    </button>
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
                                    <h3 className={styles.cardTitle}>{article.title}</h3>
                                    {article.title_vi && (
                                        <p className={styles.cardTitleVi}>{article.title_vi}</p>
                                    )}
                                    <div className={styles.cardMeta}>
                                        <span className={styles.cardSource}>{article.icon} {article.source}</span>
                                        {article.date && <span className={styles.cardDate}>{article.date}</span>}
                                        {isSearchMode && article.category && (
                                            <span className={styles.cardCategory}>
                                                {CATEGORIES.find(c => c.id === article.category)?.name || article.category}
                                            </span>
                                        )}
                                    </div>
                                    {article.description && (
                                        <p className={styles.cardDesc}>{article.description}</p>
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
