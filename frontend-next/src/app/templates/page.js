'use client'

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import styles from './page.module.css'
import { ASSESSMENT_TEMPLATES } from '../../data/templates'
import { ASSESSMENT_STANDARDS } from '../../data/standards'

export default function TemplatesMonitorPage() {
    const router = useRouter()
    const [filter, setFilter] = useState('all')

    const filteredTemplates = useMemo(() => {
        if (filter === 'all') return ASSESSMENT_TEMPLATES
        return ASSESSMENT_TEMPLATES.filter(t => t.standard === filter)
    }, [filter])

    const getStandardInfo = (standardId) => {
        const std = ASSESSMENT_STANDARDS.find(s => s.id === standardId)
        return std || { name: standardId, controls: [] }
    }

    const getControlCount = (template) => {
        const std = getStandardInfo(template.standard)
        const total = std.controls.reduce((acc, cat) => acc + cat.controls.length, 0)
        const implemented = template.data.compliance?.implemented_controls?.length || 0
        return { implemented, total }
    }

    const selectTemplate = (tpl) => {
        localStorage.setItem('reuse_iso_form', JSON.stringify(tpl.data))
        router.push('/form-iso')
    }

    return (
        <div className="page-container">
            <div className={styles.header}>
                <h1 className={styles.title}>Kho Mẫu Hệ thống Thực tế</h1>
                <p className={styles.subtitle}>
                    Dữ liệu kiến trúc mạng, quản lý truy cập và mức tuân thủ của các tổ chức thực tế.
                    Sử dụng để trải nghiệm hệ thống RAG Auditor.
                </p>
                <div className={styles.headerActions}>
                    <Link href="/form-iso" className={styles.backBtn}>← Trang Đánh giá</Link>
                </div>
            </div>

            <div className={styles.filterBar}>
                <button
                    className={`${styles.filterBtn} ${filter === 'all' ? styles.filterActive : ''}`}
                    onClick={() => setFilter('all')}
                >
                    Tất cả ({ASSESSMENT_TEMPLATES.length})
                </button>
                {ASSESSMENT_STANDARDS.map(std => {
                    const count = ASSESSMENT_TEMPLATES.filter(t => t.standard === std.id).length
                    return (
                        <button
                            key={std.id}
                            className={`${styles.filterBtn} ${filter === std.id ? styles.filterActive : ''}`}
                            onClick={() => setFilter(std.id)}
                        >
                            {std.id === 'iso27001' ? 'ISO 27001' : 'TCVN 11930'} ({count})
                        </button>
                    )
                })}
            </div>

            <div className={styles.templateGrid}>
                {filteredTemplates.map(tpl => {
                    const { implemented, total } = getControlCount(tpl)
                    const percent = total > 0 ? ((implemented / total) * 100).toFixed(0) : 0

                    return (
                        <div key={tpl.id} className={styles.templateCard}>
                            <div className={styles.cardHeader}>
                                <div>
                                    <h3 className={styles.cardTitle}>{tpl.name}</h3>
                                    <span className={`${styles.stdBadge} ${tpl.standard === 'iso27001' ? styles.stdIso : styles.stdTcvn}`}>
                                        {tpl.standard === 'iso27001' ? 'ISO 27001' : 'TCVN 11930'}
                                    </span>
                                </div>
                                <span className={styles.industryTag}>{tpl.data.organization.industry}</span>
                            </div>

                            <div className={styles.cardBody}>
                                <p className={styles.cardDesc}>{tpl.description}</p>

                                <div className={styles.statsRow}>
                                    <div className={styles.statBox}>
                                        <span className={styles.statNum}>{tpl.data.organization.employees}</span>
                                        <span className={styles.statLabel}>Nhân sự</span>
                                    </div>
                                    <div className={styles.statBox}>
                                        <span className={styles.statNum}>{tpl.data.infrastructure.servers}</span>
                                        <span className={styles.statLabel}>Máy chủ</span>
                                    </div>
                                    <div className={styles.statBox}>
                                        <span className={styles.statNum}>{tpl.data.organization.it_staff}</span>
                                        <span className={styles.statLabel}>IT/Bảo mật</span>
                                    </div>
                                </div>

                                <div className={styles.metaGrid}>
                                    <div className={styles.metaItem}>
                                        <span className={styles.metaLabel}>☁️ Cloud</span>
                                        <span className={styles.metaValue}>{tpl.data.infrastructure.cloud?.split(',')[0]?.split('(')[0]?.trim() || 'Không'}</span>
                                    </div>
                                    <div className={styles.metaItem}>
                                        <span className={styles.metaLabel}>🛡️ Firewall</span>
                                        <span className={styles.metaValue}>{tpl.data.infrastructure.firewalls?.split(',')[0]?.trim() || 'Không có'}</span>
                                    </div>
                                    <div className={styles.metaItem}>
                                        <span className={styles.metaLabel}>📊 SIEM</span>
                                        <span className={styles.metaValue}>{tpl.data.infrastructure.siem?.split(',')[0]?.split('+')[0]?.trim() || 'Không có'}</span>
                                    </div>
                                    <div className={styles.metaItem}>
                                        <span className={styles.metaLabel}>🔒 VPN</span>
                                        <span className={styles.metaValue}>{tpl.data.infrastructure.vpn}</span>
                                    </div>
                                </div>

                                <div className={styles.complianceSection}>
                                    <div className={styles.complianceHeader}>
                                        <span className={styles.complianceTitle}>Mức tuân thủ</span>
                                        <span className={styles.complianceValue}>{implemented}/{total} ({percent}%)</span>
                                    </div>
                                    <div className={styles.complianceTrack}>
                                        <div className={styles.complianceFill} style={{ width: `${percent}%` }} />
                                    </div>
                                </div>
                            </div>

                            <div className={styles.cardFooter}>
                                <button className={styles.useBtn} onClick={() => selectTemplate(tpl)}>
                                    Phân tích hệ thống này →
                                </button>
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
