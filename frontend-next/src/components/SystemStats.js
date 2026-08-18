'use client'

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from './LanguageProvider'
import styles from './SystemStats.module.css'

const CACHE_KEY = 'system_stats_cache'

function getCachedStats() {
    if (typeof window === 'undefined') return null
    try {
        const cached = sessionStorage.getItem(CACHE_KEY)
        if (cached) return JSON.parse(cached)
    } catch { }
    return null
}

function setCachedStats(data) {
    if (typeof window === 'undefined') return
    try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify(data))
    } catch { }
}

export default function SystemStats() {
    const { t } = useTranslation()
    const [stats, setStats] = useState(null)
    const [loading, setLoading] = useState(true)
    const [refreshing, setRefreshing] = useState(false)
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
        const cached = getCachedStats()
        if (cached) {
            setStats(cached)
            setLoading(false)
        }
    }, [])

    const fetchStats = useCallback(async (isBackground = false) => {
        if (isBackground) setRefreshing(true)
        try {
            const res = await fetch('/api/system/stats')
            if (res.ok) {
                const data = await res.json()
                setStats(data)
                setCachedStats(data)
            }
        } catch (err) {
            console.error('System stats fetch failed:', err)
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }, [])

    useEffect(() => {
        if (!stats) {
            fetchStats(false)
        } else {
            fetchStats(true)
        }
        const interval = setInterval(() => fetchStats(true), 15000)
        return () => clearInterval(interval)
    }, [fetchStats])

    const formatBytes = (bytes) => {
        if (!bytes) return '0'
        const gb = bytes / (1024 ** 3)
        return gb.toFixed(1)
    }

    const formatUptime = (seconds) => {
        if (!seconds) return '0d'
        const days = Math.floor(seconds / 86400)
        const hours = Math.floor((seconds % 86400) / 3600)
        return days > 0 ? `${days}d ${hours}h` : `${hours}h`
    }

    if (!mounted || (loading && !stats)) {
        return (
            <div className={styles.wrapper}>
                <div className={styles.grid}>
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className={styles.card}>
                            <div className={styles.skeleton} />
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    if (!stats) {
        return (
            <div className={styles.wrapper}>
                <div className={styles.errorCard}>
                    <p>{t('systemStats.unableToConnect')}</p>
                </div>
            </div>
        )
    }

    const getColor = (percent, thresholds = [50, 80]) => {
        if (percent > thresholds[1]) return 'var(--accent-red)'
        if (percent > thresholds[0]) return 'var(--accent-amber)'
        return 'var(--accent-green)'
    }

    const items = [
        {
            label: t('systemStats.cpu'),
            abbr: 'proc',
            value: `${stats.cpu.percent}%`,
            detail: stats.cpu.name,
            sub: `${stats.cpu.cores} ${t('systemStats.cores')}`,
            color: getColor(stats.cpu.percent),
            percent: stats.cpu.percent
        },
        {
            label: t('systemStats.ram'),
            abbr: 'mem',
            value: formatBytes(stats.memory.used),
            unit: 'GB',
            detail: `${stats.memory.percent}% ${t('systemStats.used')}`,
            sub: `${t('systemStats.total')}: ${formatBytes(stats.memory.total)} GB`,
            color: getColor(stats.memory.percent, [60, 85]),
            percent: stats.memory.percent
        },
        {
            label: t('systemStats.disk'),
            abbr: 'stor',
            value: formatBytes(stats.disk.used),
            unit: 'GB',
            detail: `${stats.disk.percent}% ${t('systemStats.used')}`,
            sub: `${t('systemStats.total')}: ${formatBytes(stats.disk.total)} GB`,
            color: getColor(stats.disk.percent, [70, 90]),
            percent: stats.disk.percent
        },
        {
            label: t('systemStats.uptime'),
            abbr: 'sys',
            value: formatUptime(stats.uptime_seconds),
            detail: stats.platform,
            sub: t('systemStats.operatingSystem'),
            color: 'var(--accent-green)',
            percent: 100
        }
    ]

    return (
        <div className={styles.wrapper}>
            {refreshing && <div className={styles.refreshDot} title="Refreshing..." />}
            <div className={styles.grid}>
                {items.map((item, i) => (
                    <div key={i} className={styles.card}>
                        <div className={styles.header}>
                            <span className={styles.label}>{item.label}</span>
                            <span className={styles.abbr}>{item.abbr}</span>
                        </div>
                        <div className={styles.value} style={{ color: item.color }}>
                            {item.value}
                            {item.unit && <span className={styles.unit}>{item.unit}</span>}
                        </div>
                        <div className={styles.progressBar}>
                            <div
                                className={styles.progressFill}
                                style={{ width: `${Math.min(item.percent, 100)}%`, background: item.color }}
                            />
                        </div>
                        <div className={styles.detail} title={item.detail}>{item.detail}</div>
                        <div className={styles.sub}>{item.sub}</div>
                    </div>
                ))}
            </div>
        </div>
    )
}
