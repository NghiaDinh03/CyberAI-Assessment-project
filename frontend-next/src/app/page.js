'use client'

import Link from 'next/link'
import SystemStats from '@/components/SystemStats'
import styles from './page.module.css'

const FEATURES = [
    {
        title: 'AI Chat',
        desc: 'Trợ lý AI tra cứu ISO 27001 và TCVN 11930 với streaming response',
        tag: 'Streaming',
        color: '#4f8ef7',
        href: '/chatbot'
    },
    {
        title: 'Security Assessment',
        desc: 'Form đánh giá đa tiêu chuẩn với RAG Auditor và Multi-LLM Fallback',
        tag: 'Multi-LLM',
        color: '#8b6cf7',
        href: '/form-iso'
    },
    {
        title: 'Template Library',
        desc: 'Templates hệ thống mạng thực tế để trải nghiệm và thử nghiệm đánh giá',
        tag: 'Templates',
        color: '#34d399',
        href: '/templates'
    },
    {
        title: 'Analytics',
        desc: 'Giám sát hiệu năng, lịch sử đánh giá và trạng thái dịch vụ real-time',
        tag: 'Real-time',
        color: '#22d3ee',
        href: '/analytics'
    },
]

export default function HomePage() {
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

            <section>
                <p className="section-title">⚡ System Resources</p>
                <SystemStats />
            </section>

            <section style={{ marginTop: '2.5rem' }}>
                <p className="section-title">🧩 Modules</p>
                <div className={styles.features}>
                    {FEATURES.map((f, i) => (
                        <Link key={i} href={f.href} className={styles.card}>
                            <div className={styles.cardAccent} style={{ background: f.color }} />
                            <div className={styles.cardBody}>
                                <div className={styles.cardTop}>
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
