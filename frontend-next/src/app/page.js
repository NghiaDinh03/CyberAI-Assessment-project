'use client'

import Link from 'next/link'
import SystemStats from '@/components/SystemStats'
import styles from './page.module.css'

const FEATURES = [
    { icon: '💬', title: 'AI Chat', desc: 'Trợ lý AI tra cứu ISO 27001 và TCVN 11930', tag: 'Streaming', color: '#6366F1', href: '/chatbot' },
    { icon: '📋', title: 'Đánh giá ATTT', desc: 'Form đánh giá đa tiêu chuẩn với RAG Auditor', tag: 'Multi-LLM', color: '#A78BFA', href: '/form-iso' },
    { icon: '📂', title: 'Kho Mẫu Thực tế', desc: 'Templates hệ thống mạng thực tế để trải nghiệm', tag: 'Templates', color: '#34D399', href: '/templates' },
    { icon: '📊', title: 'Analytics', desc: 'Giám sát hiệu năng và trạng thái dịch vụ', tag: 'Real-time', color: '#22D3EE', href: '/analytics' },
    { icon: '📰', title: 'Tin tức ATTT', desc: 'Tổng hợp tin tức an toàn thông tin & TTS', tag: 'AI Summary', color: '#FBBF24', href: '/news' },
]

export default function HomePage() {
    return (
        <div className="page-container">
            <div className={styles.hero}>
                <div className={styles.heroLabel}>✦ Platform v2.0 — Cloud LLM + RAG Pipeline</div>
                <h1 className={styles.heroTitle}>CyberAI Assessment</h1>
                <p className={styles.heroSub}>
                    Nền tảng AI đánh giá tuân thủ <strong>ISO 27001:2022</strong> và <strong>TCVN 11930:2017</strong>.
                    Tích hợp <strong>Multi-LLM Fallback</strong> + <strong>Semantic RAG Search</strong>.
                </p>
            </div>

            <section>
                <h2 className="section-title">Tài nguyên hệ thống</h2>
                <SystemStats />
            </section>

            <section style={{ marginTop: '2.5rem' }}>
                <h2 className="section-title">Chức năng</h2>
                <div className={styles.features}>
                    {FEATURES.map((f, i) => (
                        <Link key={i} href={f.href} className={styles.card}>
                            <div className={styles.cardIcon}>{f.icon}</div>
                            <div className={styles.cardBody}>
                                <h3>{f.title}</h3>
                                <p>{f.desc}</p>
                                <span className={styles.tag} style={{ color: f.color, borderColor: `${f.color}22`, background: `${f.color}0A` }}>{f.tag}</span>
                            </div>
                            <span className={styles.arrow}>→</span>
                        </Link>
                    ))}
                </div>
            </section>

            <footer className={styles.footer}>
                CyberAI Assessment Platform · FastAPI · Next.js · LocalAI · © 2026
            </footer>
        </div>
    )
}
