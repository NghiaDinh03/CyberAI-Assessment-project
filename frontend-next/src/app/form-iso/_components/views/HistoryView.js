'use client'

import styles from './views.module.css'
import { useTranslation } from '@/components/LanguageProvider'

export default function HistoryView({
    assessmentHistory,
    fetchHistory,
    loadAssessmentById,
    deleteAssessment,
    deletingId,
    setActiveTab,
    setStep,
    onStartNewAssessment,
}) {
    const { t } = useTranslation()

    return (
        <div className={styles.historyWrap}>
            <div className={styles.historyHeader}>
                <h2 className={styles.sectionTitle}>{t('assessment.historyTitle')}</h2>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className={styles.refreshBtn} onClick={fetchHistory}>
                        {t('assessment.historyRefresh')}
                    </button>
                    {onStartNewAssessment && (
                        <button
                            className={styles.refreshBtn}
                            style={{ background: 'rgba(16, 185, 129, 0.15)', borderColor: 'rgba(16, 185, 129, 0.4)', color: '#34d399' }}
                            onClick={onStartNewAssessment}
                        >
                            ✨ {t('assessment.tabForm')}
                        </button>
                    )}
                </div>
            </div>
            <p className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('assessment.historyNote', { count: assessmentHistory.length }) }} />

            {assessmentHistory.length === 0 ? (
                <div className={styles.emptyHistory}>
                    {t('assessment.historyEmpty')}<br />
                    <small style={{ opacity: 0.5 }}>{t('assessment.historyEmptyHint')}</small>
                </div>
            ) : (
                <div className={styles.historyList}>
                    {assessmentHistory.map((hist, index) => (
                        <div key={hist.id ? `${hist.id}-${index}` : index} className={styles.historyItem}>
                            <div className={styles.histInfo}>
                                <div className={styles.histTitle}>
                                    {hist.org}
                                    <span className={styles.histDate}>{hist.date}</span>
                                </div>
                                <div className={styles.histStd}>
                                    {t('assessment.historyStandard')}: <strong>{hist.standard}</strong>
                                    {hist.id && (
                                        <span style={{ marginLeft: '0.5rem', opacity: 0.4, fontSize: '0.68rem', fontFamily: 'monospace' }}>
                                            #{hist.id.slice(0, 8)}
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div className={styles.histPercent}>
                                {(() => {
                                    const pct = hist.weighted_compliance?.percentage ?? (hist.compliance_percent != null ? parseFloat(hist.compliance_percent) : null)
                                    return pct != null ? (
                                        <>
                                            <span className={`${styles.histPercentNum} ${pct >= 80 ? styles.scoreNumFull :
                                                    pct >= 50 ? styles.scoreNumMostly :
                                                        pct >= 25 ? styles.scoreNumPartial :
                                                            styles.scoreNumLow
                                                }`}>{pct}%</span>
                                            <span className={styles.histPercentLabel}>{t('assessment.historyCompliance')}</span>
                                        </>
                                    ) : (
                                        <span className={styles.histPercentLabel} style={{ fontSize: '0.7rem', opacity: 0.4 }}>—</span>
                                    )
                                })()}
                            </div>

                            <div className={styles.histAction}>
                                <span className={`${styles.statusBadge} ${styles[`status_${hist.status}`]}`}>
                                    {hist.status === 'completed' ? t('assessment.historyCompleted') :
                                        hist.status === 'failed' ? t('assessment.historyFailed') :
                                            hist.status === 'processing' ? t('assessment.historyProcessing') : t('assessment.historyPending')}
                                </span>

                                {hist.status === 'completed' && hist.id && (
                                    <button
                                        className={styles.btnSmall}
                                        onClick={() => loadAssessmentById(hist.id)}
                                    >
                                        {t('assessment.historyView')}
                                    </button>
                                )}

                                {(hist.status === 'processing' || hist.status === 'pending') && hist.id && (
                                    <button
                                        className={styles.btnSmall}
                                        onClick={() => loadAssessmentById(hist.id)}
                                    >
                                        {t('assessment.historyTrack')}
                                    </button>
                                )}

                                {hist.status === 'failed' && (
                                    <button
                                        className={styles.btnSmall}
                                        style={{ color: 'var(--accent-amber,#f59e0b)' }}
                                        onClick={() => {
                                            setActiveTab('form')
                                            setStep(4)
                                        }}
                                    >
                                        {t('assessment.historyRetry')}
                                    </button>
                                )}

                                {hist.id && (
                                    <button
                                        className={styles.btnSmall}
                                        style={{ color: 'var(--accent-red)', opacity: deletingId === hist.id ? 0.5 : 1 }}
                                        disabled={deletingId === hist.id}
                                        onClick={() => {
                                            if (window.confirm(t('assessment.historyDeleteConfirm', { org: hist.org, date: hist.date }))) {
                                                deleteAssessment(hist.id)
                                            }
                                        }}
                                        title={t('assessment.deleteAssessment')}
                                    >
                                        {deletingId === hist.id ? '⏳' : '🗑️'}
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
