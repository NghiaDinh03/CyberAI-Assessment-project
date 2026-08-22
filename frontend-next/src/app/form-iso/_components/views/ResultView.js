'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './views.module.css'
import SvgGauge from '../ui/SvgGauge'
import { useTranslation } from '@/components/LanguageProvider'
import { calcWeightedScore, calcCategoryBreakdown } from '../../../../data/standards'

const POLL_INTERVAL = 8000

export default function ResultView({
    result,
    form,
    availableStandards,
    currentStandard,
    getStdLabel,
    set,
    setActiveTab,
    setStep,
    loading,
    submit,
    setSelectedAiModel,
}) {
    const { t, locale } = useTranslation()

    if (!result) return null

    // 1. Error state (Rate limit or API error)
    if (result.error && (result.error.includes('RESOURCE_EXHAUSTED') || result.error.includes('Rate limit') || result.error.includes('429'))) {
        return (
            <div className={styles.rateLimitCard}>
                <div className={styles.rateLimitIcon}>⚠️</div>
                <div className={styles.rateLimitContent}>
                    <h3>{t('assessment.cloudRateLimitTitle')}</h3>
                    <p>{t('assessment.cloudRateLimitDesc')}</p>
                    <button
                        className={styles.btnPrimary}
                        onClick={() => {
                            set('model_mode', 'local')
                            setActiveTab('form')
                            setStep(4)
                        }}
                    >
                        {locale === 'vi' ? 'Chuyển sang Local Gemma 4 (Offline)' : 'Switch to Local Gemma 4'}
                    </button>
                </div>
            </div>
        )
    }

    // 2. Processing / Pending state
    if (result.status === 'processing' || result.status === 'pending') {
        const pct = result.progress?.percent || 0
        const ragDone = pct >= 5
        const p1Active = pct >= 5 && pct < 85
        const p1Done = pct >= 85
        const p2Active = pct >= 85 && pct < 100

        return (
            <div className={styles.processingCard}>
                <div className={styles.processingSpinner}>
                    <div className={styles.spinnerRing} />
                    <span className={styles.spinnerIcon}>🤖</span>
                </div>
                <h3 className={styles.processingTitle}>{t('assessment.processingTitle')}</h3>
                <div className={styles.processingTabAway}>
                    <span>💡</span>
                    <span dangerouslySetInnerHTML={{ __html: t('assessment.processingTabAway') }} />
                </div>

                <div className={styles.processingProgressWrap}>
                    <div className={styles.processingProgressBar}>
                        <div
                            className={styles.processingProgressFill}
                            style={{ width: `${pct}%` }}
                        />
                    </div>
                    <span className={styles.processingProgressMsg}>
                        {result.progress?.message || (result.status === 'pending' ? t('assessment.processingPending') : t('assessment.processingStarting'))}
                        <span className={styles.processingProgressPct}> {pct}%</span>
                    </span>
                </div>

                <p className={styles.processingDesc}>
                    {t('assessment.processingOrg')}: <strong>{result.org_name || form.org_name || '—'}</strong> ·{' '}
                    {getStdLabel(result.standard || form.assessment_standard)} ·{' '}
                    {form.model_mode === 'local'
                        ? t('assessment.processingLocalTime')
                        : form.model_mode === 'hybrid'
                            ? t('assessment.processingHybridTime')
                            : t('assessment.processingCloudTime')}
                </p>

                {/* 3-Step Live Processing Stepper */}
                <div className={styles.processingSteps}>
                    <div className={styles.procStep}>
                        <span className={styles.procStepNum} style={ragDone ? { background: 'var(--accent-green)', color: '#fff' } : {}}>
                            {ragDone ? '✓' : '1'}
                        </span>
                        <div className={styles.procStepText}>
                            <span className={styles.procStepLabel}>
                                {locale === 'vi' ? 'Bước 1: Bóc tách & Tra cứu Tiêu chuẩn' : 'Step 1: RAG Standard Retrieval'}
                            </span>
                            <span className={styles.procStepDesc}>
                                ChromaDB — {getStdLabel(result.standard || form.assessment_standard).split('(')[0].trim()}
                            </span>
                        </div>
                    </div>

                    <div className={styles.procStep} style={!ragDone ? { opacity: 0.4 } : {}}>
                        <span
                            className={`${styles.procStepNum} ${p1Active ? styles.procStepNumAnim : ''}`}
                            style={p1Done ? { background: 'var(--accent-green)', color: '#fff' } : {}}
                        >
                            {p1Done ? '✓' : '2'}
                        </span>
                        <div className={styles.procStepText}>
                            <span className={styles.procStepLabel}>
                                {locale === 'vi' ? 'Bước 2: Phân tích GAP Controls (Gemma 4)' : 'Step 2: GAP Controls Analysis (Gemma 4)'}
                            </span>
                            <span className={styles.procStepDesc}>{t('assessment.gapAnalysis')}</span>
                        </div>
                    </div>

                    <div className={styles.procStep} style={!p1Done ? { opacity: 0.4 } : {}}>
                        <span className={`${styles.procStepNum} ${p2Active ? styles.procStepNumAnim : ''}`}>
                            {pct === 100 ? '✓' : '3'}
                        </span>
                        <div className={styles.procStepText}>
                            <span className={styles.procStepLabel}>
                                {locale === 'vi' ? 'Bước 3: Tổng hợp Báo cáo IT Audit (Gemma 4)' : 'Step 3: IT Audit Report Synthesis (Gemma 4)'}
                            </span>
                            <span className={styles.procStepDesc}>{t('assessment.reportFormat')}</span>
                        </div>
                    </div>
                </div>

                {/* Live Assessment Activity Terminal */}
                <div className={styles.liveConsoleBox}>
                    <div className={styles.liveConsoleHeader}>
                        <div className={styles.liveConsoleTitle}>
                            <span className={styles.liveConsoleDot} />
                            <span>{locale === 'vi' ? 'Live Progress Stream (Nhật Ký Thẩm Định)' : 'Live Assessment Progress Stream'}</span>
                        </div>
                        <span className={styles.liveConsoleModel}>Engine: Gemma 4 (100% Offline)</span>
                    </div>
                    <div className={styles.liveConsoleBody}>
                        <div className={styles.liveConsoleLine}>
                            <span className={styles.liveConsoleTime}>[System]</span>
                            <span className={styles.liveConsoleText}>⚡ Khởi tạo tiến trình đánh giá ngầm (Task ID: {result.id?.slice(0, 8)})</span>
                        </div>
                        <div className={styles.liveConsoleLine}>
                            <span className={styles.liveConsoleTime}>[RAG]</span>
                            <span className={styles.liveConsoleText}>🔍 Nạp tri thức tiêu chuẩn {getStdLabel(result.standard || form.assessment_standard)} & đối chiếu hồ sơ</span>
                        </div>
                        {result.progress?.message && (
                            <div className={`${styles.liveConsoleLine} ${styles.liveConsoleLineActive}`}>
                                <span className={styles.liveConsoleTime}>[Live]</span>
                                <span className={styles.liveConsoleText}>⏳ {result.progress.message} ({pct}%)</span>
                            </div>
                        )}
                    </div>
                </div>

                <div className={styles.pollingInfo} style={{ justifyContent: 'center', marginTop: '0.75rem' }}>
                    <span className={styles.pollingDot} />
                    <span>{t('assessment.autoCheckEvery', { seconds: POLL_INTERVAL / 1000 })} · ID: <code style={{ fontSize: '0.72rem', opacity: 0.7 }}>{result.id?.slice(0, 8)}</code></span>
                </div>
            </div>
        )
    }

    // 3. Completed Result View
    const activeStandardId = result.standard || form.assessment_standard || 'iso27001'
    const activeStandard = availableStandards?.find(s => s.id === activeStandardId) || currentStandard
    const activeTotalControls = activeStandard?.controls?.reduce((acc, cat) => acc + (cat?.controls?.length || 0), 0) || (activeStandardId === 'tcvn11930' ? 34 : 93)

    const activeImplList = (result.implemented_controls && result.implemented_controls.length > 0)
        ? result.implemented_controls
        : (result.json_data?.compliance?.implemented_controls && result.json_data.compliance.implemented_controls.length > 0)
            ? result.json_data.compliance.implemented_controls
            : form.implemented_controls

    const implCount = activeImplList.length
    const totalCount = activeTotalControls
    const missingCount = Math.max(0, totalCount - implCount)

    const calculatedScore = calcWeightedScore(activeImplList, activeStandard?.controls || [])
    const serverPct = result.compliance_percent != null ? parseFloat(result.compliance_percent) : null
    const displayPct = (serverPct != null && !isNaN(serverPct) && serverPct > 0)
        ? serverPct
        : calculatedScore.percent
    const displayPctStr = displayPct.toFixed(1)

    const displayOrg = result.org_name || form.org_name || t('assessment.processingOrg')
    const displayStd = getStdLabel(activeStandardId)

    const rawModel = result.model_used
    let modelName = 'Gemma 4 (100% Local AI)'
    if (typeof rawModel === 'string') {
        if (rawModel.includes('gemma')) modelName = 'Gemma 4 (Local Offline)'
        else if (rawModel.includes('claude')) modelName = 'Claude 3.5 Sonnet'
        else modelName = rawModel
    } else if (rawModel && typeof rawModel === 'object') {
        const p1 = rawModel.phase1 || rawModel.model || ''
        if (p1.includes('gemma')) modelName = 'Gemma 4 (Local Offline)'
        else if (p1.includes('claude')) modelName = 'Claude 3.5 Sonnet'
        else if (p1) modelName = p1
    }

    const categoryBreakdown = calcCategoryBreakdown(activeImplList, activeStandard?.controls || [])

    return (
        <>
            <div className={styles.scoreHero}>
                <div className={styles.scoreHeroLeft}>
                    <div className={styles.svgGaugeWrap}>
                        <SvgGauge
                            percent={displayPct}
                            size={120}
                            color={
                                displayPct >= 80 ? 'var(--accent-green)' :
                                    displayPct >= 50 ? 'var(--accent-blue)' :
                                        displayPct >= 25 ? 'var(--accent-amber,#f59e0b)' :
                                            'var(--accent-red)'
                            }
                        />
                        <div className={styles.svgGaugeOverlay}>
                            <span className={`${styles.scoreNum} ${displayPct >= 80 ? styles.scoreNumFull :
                                    displayPct >= 50 ? styles.scoreNumMostly :
                                        displayPct >= 25 ? styles.scoreNumPartial :
                                            styles.scoreNumLow
                                }`}>{displayPctStr}%</span>
                            <span className={styles.scoreUnit}>{t('assessment.complianceLabel')}</span>
                        </div>
                    </div>
                </div>

                <div className={styles.scoreHeroRight}>
                    <div className={styles.scoreOrg}>{displayOrg}</div>
                    <div className={styles.scoreStd}>{displayStd}</div>
                    <div className={`${styles.complianceBadge} ${displayPct >= 80 ? styles.badgeFull :
                            displayPct >= 50 ? styles.badgeMostly :
                                displayPct >= 25 ? styles.badgePartial :
                                    styles.badgeLow
                        }`}>
                        {displayPct >= 80 ? t('assessment.complianceHigh') :
                            displayPct >= 50 ? t('assessment.compliancePartial') :
                                displayPct >= 25 ? t('assessment.complianceLow') :
                                    t('assessment.complianceNone')}
                    </div>
                    <div className={styles.scoreStats}>
                        <div className={styles.scoreStat}>
                            <span className={styles.scoreStatNum}>{implCount}</span>
                            <span className={styles.scoreStatLabel}>{t('assessment.controlsPassed')}</span>
                        </div>
                        <div className={styles.scoreStatDivider} />
                        <div className={styles.scoreStat}>
                            <span className={styles.scoreStatNum}>{missingCount}</span>
                            <span className={styles.scoreStatLabel}>{t('assessment.controlsMissing')}</span>
                        </div>
                        <div className={styles.scoreStatDivider} />
                        <div className={styles.scoreStat}>
                            <span className={styles.scoreStatNum}>{totalCount}</span>
                            <span className={styles.scoreStatLabel}>{t('assessment.controlsTotal')}</span>
                        </div>
                    </div>
                    <div className={styles.modelChips}>
                        <span className={styles.modelChip}>🤖 {modelName}</span>
                        <span className={styles.modelChip}>📝 ChromaDB RAG</span>
                    </div>
                </div>
            </div>

            <div className={styles.breakdownPanel}>
                <h4 className={styles.breakdownTitle}>{t('assessment.categoryBreakdown')}</h4>
                <div className={styles.breakdownGrid}>
                    {categoryBreakdown.map((cat, idx) => (
                        <div key={idx} className={styles.breakdownItem}>
                            <div className={styles.breakdownItemHeader}>
                                <span className={styles.breakdownCatName}>{cat.category}</span>
                                <span className={`${styles.breakdownPct} ${cat.weightPercent >= 80 ? styles.scoreNumFull :
                                        cat.weightPercent >= 50 ? styles.scoreNumMostly :
                                            cat.weightPercent >= 25 ? styles.scoreNumPartial :
                                                styles.scoreNumLow
                                    }`}>{cat.weightPercent}%</span>
                            </div>
                            <div className={styles.breakdownBarTrack}>
                                <div
                                    className={styles.breakdownBarFill}
                                    style={{
                                        width: `${cat.weightPercent}%`,
                                        background: cat.weightPercent >= 80 ? 'var(--accent-green)' :
                                            cat.weightPercent >= 50 ? 'var(--accent-blue)' :
                                                cat.weightPercent >= 25 ? 'var(--accent-amber,#f59e0b)' :
                                                    'var(--accent-red)'
                                    }}
                                />
                            </div>
                            <div className={styles.breakdownMeta}>
                                <span>{cat.implemented}/{cat.total} {t('assessment.controls')}</span>
                                <span>{cat.weightScore}/{cat.maxWeightScore} {t('assessment.points')}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {result.json_data && (
                <div className={styles.jsonDashboard}>
                    <h4 className={styles.jsonDashTitle}>{t('assessment.dashboardTitle')}</h4>
                    <div className={styles.jsonDashGrid}>
                        <div className={styles.jsonDashCard}>
                            <div className={styles.jsonDashCardTitle}>{t('assessment.riskClassification')}</div>
                            <div className={styles.riskSummaryRow}>
                                {[
                                    { key: 'critical_gaps', label: 'Critical', color: 'var(--accent-red)' },
                                    { key: 'high_gaps', label: 'High', color: 'var(--accent-amber,#f59e0b)' },
                                    { key: 'medium_gaps', label: 'Medium', color: 'var(--accent-blue)' },
                                    { key: 'low_gaps', label: 'Low', color: 'var(--text-dim)' },
                                ].map(({ key, label, color }) => (
                                    <div key={key} className={styles.riskStat}>
                                        <span className={styles.riskStatNum} style={{ color }}>{result.json_data.risk_summary?.[key] ?? 0}</span>
                                        <span className={styles.riskStatLabel}>{label}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {result.json_data.top_gaps?.length > 0 && (
                            <div className={`${styles.jsonDashCard} ${styles.jsonDashCardWide}`}>
                                <div className={styles.jsonDashCardTitle}>{t('assessment.highPriorityGaps')}</div>
                                <div className={styles.topGapsList}>
                                    {result.json_data.top_gaps.slice(0, 8).map((gap, i) => (
                                        <div key={i} className={styles.topGapItem}>
                                            <span className={styles.topGapSev} style={{
                                                color: gap.severity === 'critical' ? 'var(--accent-red)' :
                                                    gap.severity === 'high' ? 'var(--accent-amber,#f59e0b)' :
                                                        'var(--accent-blue)'
                                            }}>●</span>
                                            <span className={styles.topGapId}>{gap.id}</span>
                                            <span className={styles.topGapLabel}>{gap.label}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className={`${styles.jsonDashCard} ${styles.jsonDashExport}`}>
                            <div className={styles.jsonDashCardTitle}>{t('assessment.exportData')}</div>
                            <button
                                className={styles.jsonExportBtn}
                                onClick={() => {
                                    const blob = new Blob([JSON.stringify(result.json_data, null, 2)], { type: 'application/json' })
                                    const url = URL.createObjectURL(blob)
                                    const a = document.createElement('a')
                                    a.href = url
                                    a.download = `assessment_${result.id?.slice(0, 8) || 'data'}.json`
                                    a.click()
                                    URL.revokeObjectURL(url)
                                }}
                            >{t('assessment.downloadJson')}</button>
                            <p className={styles.jsonExportNote}>
                                {t('assessment.exportNote')}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            <div className={styles.reportActions}>
                <button
                    className={styles.reportActionBtn}
                    onClick={() => {
                        navigator.clipboard?.writeText(result.report || '').catch(() => { })
                    }}
                >
                    {t('assessment.copyReport')}
                </button>
                <button className={styles.reportActionBtn} onClick={() => window.print()}>
                    {t('assessment.printReport')}
                </button>
                <button className={styles.reportActionBtnSecondary} onClick={() => setActiveTab('form')}>
                    {t('assessment.newAssessment')}
                </button>
                <div className={styles.reEvalGroup}>
                    <button
                        className={styles.reEvalBtn}
                        disabled={loading}
                        onClick={() => {
                            setSelectedAiModel('gemma4:latest')
                            set('model_mode', 'local')
                            setTimeout(() => submit(), 100)
                        }}
                        title={locale === 'vi' ? 'Đánh giá lại bằng mô hình Gemma 4 (Local GPU)' : 'Re-assess with Gemma 4 (Local GPU)'}
                    >
                        ⚡ {locale === 'vi' ? 'Đánh giá lại (Gemma 4 GPU)' : 'Re-assess (Gemma 4 GPU)'}
                    </button>
                </div>
            </div>

            <div className={styles.reportSection}>
                <div className={styles.md}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {result.report || ''}
                    </ReactMarkdown>
                </div>
            </div>
        </>
    )
}
