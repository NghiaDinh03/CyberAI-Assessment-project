'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import SystemStats from '@/components/SystemStats'
import { useTranslation } from '@/components/LanguageProvider'
import styles from './page.module.css'
import { MessageSquare, Shield, LayoutTemplate, BarChart2, BookOpen, Database, Cpu, Clock } from 'lucide-react'

export default function HomePage() {
    const { t, locale } = useTranslation()
    const [stats, setStats] = useState(null)
    const [statsLoading, setStatsLoading] = useState(true)

    const FEATURES = [
        {
            title: t('home.featureChat'),
            desc: t('home.featureChatDesc'),
            tag: t('home.featureChatTag'),
            color: '#4f8ef7',
            href: '/chatbot',
            icon: MessageSquare
        },
        {
            title: t('home.featureAssessment'),
            desc: t('home.featureAssessmentDesc'),
            tag: t('home.featureAssessmentTag'),
            color: '#8b6cf7',
            href: '/form-iso',
            icon: Shield
        },
        {
            title: t('home.featureTemplates'),
            desc: t('home.featureTemplatesDesc'),
            tag: t('home.featureTemplatesTag'),
            color: '#34d399',
            href: '/templates',
            icon: LayoutTemplate
        },
        {
            title: t('home.featureAnalytics'),
            desc: t('home.featureAnalyticsDesc'),
            tag: t('home.featureAnalyticsTag'),
            color: '#22d3ee',
            href: '/analytics',
            icon: BarChart2
        },
    ]

    useEffect(() => {
        async function fetchStats() {
            const dateFmt = locale === 'vi' ? 'vi-VN' : 'en-US'
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
                    ? new Date(assessData[0].created_at).toLocaleDateString(dateFmt)
                    : assessData?.assessments?.[0]?.created_at
                        ? new Date(assessData.assessments[0].created_at).toLocaleDateString(dateFmt)
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
    }, [locale])

    const STAT_ITEMS = [
        { key: 'assessments', label: t('home.totalAssessments'), icon: MessageSquare },
        { key: 'chunks', label: t('home.chromadbChunks'), icon: Database },
        { key: 'models', label: t('home.activeModels'), icon: Cpu },
        { key: 'lastDate', label: t('home.lastAssessment'), icon: Clock },
    ]

    return (
        <div className="page-container">
            <div className={styles.hero}>
                <div className={styles.heroLabel}>{t('home.platformVersion')}</div>
                <h1 className={styles.heroTitle}>{t('home.heroTitle')}</h1>
                <p className={styles.heroSub} dangerouslySetInnerHTML={{ __html: t('home.heroSub') }} />
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
                <p className="section-title">{t('home.systemResources')}</p>
                <SystemStats />
            </section>

            <section className={styles.modulesSection}>
                <p className="section-title">{t('home.modules')}</p>
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
                {t('home.footer')}
            </footer>
        </div>
    )
}
