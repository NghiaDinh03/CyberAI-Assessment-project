'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import SystemStats from '@/components/SystemStats'
import styles from './page.module.css'
import { MessageSquare, Shield, LayoutTemplate, BarChart2, BookOpen, Database, Cpu, Clock } from 'lucide-react'

const FEATURES = [
    {
        title: 'AI Chat',
        desc: 'Trợ lý AI tra cứu ISO 27001 và TCVN 11930 với streaming response',
        tag: 'Streaming',
        color: '#4f8ef7',
        href: '/chatbot',
        icon: MessageSquare
    },
    {
        title: 'Security Assessment',
        desc: 'Form đánh giá đa tiêu chuẩn với RAG Auditor và Multi-LLM Fallback',
        tag: 'Multi-LLM',
        color: '#8b6cf7',
        href: '/form-iso',
        icon: Shield
    },
    {
        title: 'Template Library',
        desc: 'Templates hệ thống mạng thực tế để trải nghiệm và thử nghiệm đánh giá',
        tag: 'Templates',
        color: '#34d399',
        href: '/templates',
        icon: LayoutTemplate
    },
    {
        title: 'Analytics',
        desc: 'Giám sát hiệu năng, lịch sử đánh giá và trạng thái dịch vụ real-time',
        tag: 'Real-time',
        color: '#22d3ee',
        href: '/analytics',
        icon: BarChart2
    },
]

export default function HomePage() {
    const [stats, setStats] = useState(null)
    const [statsLoading, setStatsLoading] = useState(true)

    useEffect(() => {
        async function fetchStats() {
            try {
                const [healthRes, assessRes] = await Promise.allSettled([
                    fetch('/api/health'),
                    fetch('/api/iso27001/assessments?page=1&per_page=1')
                ])
                const health = healthRes.status === 'fulfilled' && healthRes.value.ok
                    ? await healthRes.value.json() : null
                const assessData = assessRes.status === 'fulfilled' && assessRes.value.ok
                    ? await assessRes.value.json() : null

                const total = assessData?.total ?? (Array.isArray(assessData) ? assessData.length : 0)
                const lastDate = Array.isArray(assessData) && assessData[0]?.created_at
                    ? new Date(assessData[0].created_at).toLocaleDateString('vi-VN')
                    : assessData?.assessments?.[0]?.created_at
                        ? new Date(assessData.assessments[0].created_at).toLocaleDateString('vi-VN')
                        : '—'

                setStats({
                    assessments: total,
                    chunks: health?.chromadb?.total_chunks ?? health?.chunks ?? '—',
                    models: health?.models?.length ?? health?.active_models ?? '—',
                    lastDate,
                })
            } catch {
                setStats({ assessments: '—', chunks: '—', models: '—', lastDate: '—' })
            } finally {
                setStatsLoading(false)
            }
        }
        fetchStats()
    }, [])

    const STAT_ITEMS = [
        { key: 'assessments', label: 'Total Assessments', icon: MessageSquare },
        { key: 'chunks', label: 'ChromaDB Chunks', icon: Database },
        { key: 'models', label: 'Active Models', icon: Cpu },
        { key: 'lastDate', label: 'Last Assessment', icon: Clock },
    ]

    return (
        <div className="page-container">
            <div className={styles.hero}>
                <div className={styles.heroLabel}>Platform v2.0 — Cloud LLM + RAG Pipeline</div>
                <h1 className={styles.heroTitle}>CyberAI Assessment</h1>
                <p className={styles.heroSub}>
                    Nền tảng AI đánh giá tuân thủ <strong>ISO 27001:2022</strong> và <strong>TCVN 11930:2017</strong>.
                    Tích hợp <strong>Multi-LLM Fallback</strong> và <strong>Semantic RAG Search</strong>.
                </p>
            </div>

            <div className={styles.statsRow}>
                {STAT_ITEMS.map(s => (
                    <div key={s.key} className={styles.statCard}>
                        <div className={styles.statIcon}><s.icon size={22} /></div>
                        <div>
                            <div className={styles.statValue}>
                                {statsLoading ? <span className="shimmer" style={{ display: 'inline-block', width: 40, height: 18, borderRadius: 4 }} /> : stats?.[s.key] ?? '—'}
                            </div>
                            <div className={styles.statLabel}>{s.label}</div>
                        </div>
                    </div>
                ))}
            </div>

            <section>
                <p className="section-title">⚡ System Resources</p>
                <SystemStats />
            </section>

            <section className={styles.modulesSection}>
                <p className="section-title">🧩 Modules</p>
                <div className={styles.features}>
                    {FEATURES.map((f, i) => (
                        <Link key={i} href={f.href} className={styles.card} aria-label={`${f.title} — ${f.desc}`}>
                            <div className={styles.cardAccent} style={{ background: f.color }} />
                            <div className={styles.cardBody}>
                                <div className={styles.cardTop}>
                                    <f.icon size={16} style={{ color: f.color, flexShrink: 0 }} />
                                    <h3>{f.title}</h3>
                                    <span className={styles.tag} style={{ color: f.color, borderColor: `${f.color}30`, background: `${f.color}0d` }}>{f.tag}</span>
                                </div>
                                <p>{f.desc}</p>
                            </div>
                            <span className={styles.arrow}>→</span>
                        </Link>
                    ))}
                </div>
            </section>

            <footer className={styles.footer}>
                CyberAI Assessment Platform · FastAPI · Next.js · Open Claude · © 2026
            </footer>
        </div>
    )
}
