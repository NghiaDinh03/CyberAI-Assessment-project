'use client'

import Link from 'next/link'
import styles from './views.module.css'
import { useTranslation } from '@/components/LanguageProvider'

export default function TemplatesView({
    dynamicTemplates,
    templatesLoading,
    tplFilter,
    setTplFilter,
    showTplInfo,
    setShowTplInfo,
    getStdLabel,
    selectTemplate,
    setActiveTab,
}) {
    const { t } = useTranslation()

    const filteredTemplates = dynamicTemplates?.filter(tpl => {
        if (tplFilter === 'all') return true
        return tpl.standard === tplFilter
    }) || []

    const getTemplateControlCount = (tpl) => {
        const implemented = tpl.data?.implemented_controls?.length || 0
        const total = tpl.standard === 'tcvn11930' ? 34 : 93
        return { implemented, total }
    }

    return (
        <div className={styles.templatesWrap}>
            <div className={styles.tplHeaderRow}>
                <div>
                    <h2 className={styles.sectionTitle}>{t('assessment.templatesTitle')}</h2>
                    <p className={styles.helperText}>{t('assessment.templatesDesc')}</p>
                </div>
                <button
                    type="button"
                    className={`${styles.infoIcon} ${styles.tplInfoBtn} ${showTplInfo ? styles.infoIconActive : ''}`}
                    onClick={() => setShowTplInfo(!showTplInfo)}
                    title={t('assessment.templatesUsageGuide')}
                >ℹ</button>
            </div>

            {showTplInfo && (
                <div className={styles.tplInfoPanel}>
                    <div className={styles.tooltipHeader}>
                        <strong>{t('assessment.templatesGuideTitle')}</strong>
                        <button type="button" className={styles.tooltipClose} onClick={() => setShowTplInfo(false)}>✕</button>
                    </div>
                    <div className={styles.tooltipBody}>
                        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>
                            {t('assessment.templatesGuideDesc')}
                            <br /><br />
                            <span dangerouslySetInnerHTML={{ __html: t('assessment.templatesGuideUsage') }} />
                            <br /><br />
                            {t('assessment.templatesGuideFor')}
                        </p>
                    </div>
                </div>
            )}

            <div className={styles.tplFilterBar}>
                <button
                    className={`${styles.tplFilterBtn} ${tplFilter === 'all' ? styles.tplFilterActive : ''}`}
                    onClick={() => setTplFilter('all')}
                >
                    {t('common.all')} ({dynamicTemplates?.length || 0})
                </button>
                {['tcvn11930', 'iso27001', 'pci_dss', 'soc2', 'nd13'].map(stdId => {
                    const count = dynamicTemplates?.filter(t => t.standard === stdId).length || 0
                    if (count === 0) return null
                    return (
                        <button
                            key={stdId}
                            className={`${styles.tplFilterBtn} ${tplFilter === stdId ? styles.tplFilterActive : ''}`}
                            onClick={() => setTplFilter(stdId)}
                        >
                            {getStdLabel(stdId)} ({count})
                        </button>
                    )
                })}
            </div>

            {templatesLoading ? (
                <div style={{ textAlign: 'center', padding: '2.5rem', color: '#94a3b8' }}>
                    <span className={styles.spinner} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                    <span>Đang tải danh sách mẫu thẩm định từ cơ sở dữ liệu...</span>
                </div>
            ) : (
                <div className={styles.tplGrid}>
                    {filteredTemplates.map(tpl => {
                        const { implemented, total } = getTemplateControlCount(tpl)
                        const percent = total > 0 ? ((implemented / total) * 100).toFixed(0) : 0
                        const employees = tpl.data?.employees || tpl.data?.organization?.employees || 0
                        const servers = tpl.data?.servers || tpl.data?.infrastructure?.servers || 0
                        const itStaff = tpl.data?.it_staff || tpl.data?.organization?.it_staff || 0
                        const industry = tpl.industry || tpl.data?.industry || tpl.data?.organization?.industry || 'Tiêu chuẩn bảo mật'

                        return (
                            <div key={tpl.id} className={styles.tplCard}>
                                <div className={styles.tplCardHeader}>
                                    <div>
                                        <h3 className={styles.tplCardTitle}>{tpl.name}</h3>
                                        <span className={`${styles.tplStdBadge} ${tpl.standard === 'iso27001' ? styles.tplStdIso : styles.tplStdTcvn}`}>
                                            {getStdLabel(tpl.standard)}
                                        </span>
                                    </div>
                                    <span className={styles.tplIndustryTag}>{industry}</span>
                                </div>
                                <div className={styles.tplCardBody}>
                                    <p className={styles.tplCardDesc}>{tpl.description}</p>
                                    <div className={styles.tplStatsRow}>
                                        <div className={styles.tplStatBox}>
                                            <span className={styles.tplStatNum}>{employees}</span>
                                            <span className={styles.tplStatLabel}>{t('assessment.employees')}</span>
                                        </div>
                                        <div className={styles.tplStatBox}>
                                            <span className={styles.tplStatNum}>{servers}</span>
                                            <span className={styles.tplStatLabel}>{t('assessment.servers')}</span>
                                        </div>
                                        <div className={styles.tplStatBox}>
                                            <span className={styles.tplStatNum}>{itStaff}</span>
                                            <span className={styles.tplStatLabel}>{t('assessment.itSecurity')}</span>
                                        </div>
                                    </div>
                                    <div className={styles.tplComplianceSection}>
                                        <div className={styles.tplComplianceHeader}>
                                            <span className={styles.tplComplianceTitle}>{t('assessment.complianceLevel')}</span>
                                            <span className={styles.tplComplianceValue}>{implemented}/{total} ({percent}%)</span>
                                        </div>
                                        <div className={styles.tplComplianceTrack}>
                                            <div className={styles.tplComplianceFill} style={{ width: `${percent}%` }} />
                                        </div>
                                    </div>
                                </div>
                                <div className={styles.tplCardFooter}>
                                    <button className={styles.tplUseBtn} onClick={() => selectTemplate(tpl)}>
                                        {t('assessment.analyzeSystem')}
                                    </button>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            <div className={styles.tplNavRow}>
                <button className={styles.btnSecondary} onClick={() => setActiveTab('form')}>
                    {t('assessment.formInput')}
                </button>
                <Link href="/analytics" className={styles.btnPrimary}>
                    {t('assessment.analyticsStandards')}
                </Link>
            </div>
        </div>
    )
}
