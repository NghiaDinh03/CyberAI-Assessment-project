'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './views.module.css'
import SvgGauge from '../ui/SvgGauge'
import { useTranslation } from '@/components/LanguageProvider'
import { calcWeightedScore, calcCategoryBreakdown } from '../../../../data/standards'
import OfficeEditorModal from '@/components/OfficeEditorModal'
import EvidenceExtractionProofModal from '@/components/EvidenceExtractionProofModal'

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
    const [auditTrace, setAuditTrace] = useState(null)
    const [showTraceModal, setShowTraceModal] = useState(false)
    const [loadingTrace, setLoadingTrace] = useState(false)
    const [showProofModal, setShowProofModal] = useState(false)
    const [showOfficeModal, setShowOfficeModal] = useState(false)
    const [officeFileType, setOfficeFileType] = useState('docx')
    const [exportingType, setExportingType] = useState(null)
    const [showExportMenu, setShowExportMenu] = useState(false)

    const downloadBlob = (blob, filename) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const handleExportDocx = async () => {
        if (!result.id) return
        setExportingType('docx')
        try {
            const res = await fetch(`/api/iso27001/assessments/${result.id}/export-docx`, { method: 'POST' })
            if (res.ok) {
                const blob = await res.blob()
                downloadBlob(blob, `IT_Audit_Report_${result.id.slice(0, 8)}.docx`)
            }
        } catch (err) {
            console.error('Export DOCX error:', err)
        } finally {
            setExportingType(null)
        }
    }

    const handleExportSoA = async () => {
        if (!result.id) return
        setExportingType('soa')
        try {
            const res = await fetch('/api/iso27001/soa/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ assessment_id: result.id, org_name: form?.org_name || '' })
            })
            if (res.ok) {
                const blob = await res.blob()
                downloadBlob(blob, `SoA_ISO27001_${result.id.slice(0, 8)}.xlsx`)
            }
        } catch (err) {
            console.error('Export SoA error:', err)
        } finally {
            setExportingType(null)
        }
    }

    const handleExportRiskRegister = async () => {
        if (!result.id) return
        setExportingType('risk')
        try {
            const res = await fetch(`/api/iso27001/assessments/${result.id}/export-risk-register`, { method: 'POST' })
            if (res.ok) {
                const blob = await res.blob()
                downloadBlob(blob, `Risk_Register_${result.id.slice(0, 8)}.xlsx`)
            }
        } catch (err) {
            console.error('Export Risk Register error:', err)
        } finally {
            setExportingType(null)
        }
    }

    const handleExportPdf = async () => {
        if (!result.id) return
        setExportingType('pdf')
        try {
            const res = await fetch(`/api/iso27001/assessments/${result.id}/export-pdf`, { method: 'POST' })
            if (res.ok) {
                const blob = await res.blob()
                downloadBlob(blob, `Audit_Report_${result.id.slice(0, 8)}.pdf`)
            }
        } catch (err) {
            console.error('Export PDF error:', err)
        } finally {
            setExportingType(null)
        }
    }

    if (!result) return null

    // 1. Error state (Rate limit or API error)
    if (result.error || result.status === 'failed') {
        const errorStr = typeof result.error === 'string'
            ? result.error
            : (result.report || result.error?.message || result.error?.detail || (result.status === 'failed' && result.report) || 'Đã xảy ra lỗi khi thực hiện đánh giá.')

        const isRateLimit = errorStr.includes('RESOURCE_EXHAUSTED') ||
                            errorStr.includes('Rate limit') ||
                            errorStr.includes('429')

        const isOllamaUnreachable = errorStr.toLowerCase().includes('ollama') ||
                                    errorStr.toLowerCase().includes('connection error') ||
                                    errorStr.toLowerCase().includes('unreachable') ||
                                    errorStr.toLowerCase().includes('lỗi kết nối server')

        if (isRateLimit) {
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

        const errorCode = result.error_code || (result.status === 'failed' ? 'ASSESSMENT_PIPELINE_ERROR' : null)

        return (
            <div className={styles.rateLimitCard}>
                <div className={styles.rateLimitIcon}>⚠️</div>
                <div className={styles.rateLimitContent} style={{ width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                        <h3 style={{ margin: 0 }}>{locale === 'vi' ? 'Lỗi khi thực hiện đánh giá' : 'Assessment Error'}</h3>
                        {errorCode && (
                            <span style={{
                                background: 'rgba(239, 68, 68, 0.2)',
                                border: '1px solid rgba(239, 68, 68, 0.4)',
                                color: '#fca5a5',
                                padding: '0.15rem 0.5rem',
                                borderRadius: '4px',
                                fontSize: '0.75rem',
                                fontFamily: 'monospace',
                                fontWeight: 'bold'
                            }}>
                                {errorCode}
                            </span>
                        )}
                    </div>
                    <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '8px', padding: '0.85rem 1rem', marginTop: '0.75rem' }}>
                        <p style={{ whiteSpace: 'pre-wrap', color: '#fca5a5', fontSize: '0.88rem', margin: 0 }}>{errorStr}</p>
                    </div>
                    {isOllamaUnreachable && (
                        <p style={{ marginTop: '0.75rem', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                            {locale === 'vi'
                                ? '💡 Gợi ý: Hãy đảm bảo dịch vụ Ollama đang chạy (`ollama serve` hoặc mở app Ollama) và đã tải mô hình tương ứng (ví dụ `ollama pull gemma4:latest`), hoặc kiểm tra kết nối API backend.'
                                : '💡 Tip: Ensure Ollama is running (`ollama serve`) and model is pulled, or check backend connection.'}
                        </p>
                    )}
                    <div style={{ marginTop: '1.25rem', display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                        <button
                            className={styles.btnPrimary}
                            onClick={() => {
                                if (submit) submit()
                                else {
                                    setActiveTab('form')
                                    setStep(4)
                                }
                            }}
                        >
                            🔄 {locale === 'vi' ? 'Thử lại' : 'Retry'}
                        </button>
                        <button
                            className={styles.btnSecondary}
                            onClick={() => {
                                setActiveTab('form')
                                setStep(3)
                            }}
                        >
                            📎 {locale === 'vi' ? 'Quay lại chỉnh minh chứng' : 'Edit Evidence & Controls'}
                        </button>
                        {result.id && (
                            <button
                                className={styles.btnSecondary}
                                onClick={async () => {
                                    setLoadingTrace(true)
                                    try {
                                        const res = await fetch(`/api/iso27001/assessments/${result.id}/audit-trace`)
                                        if (res.ok) {
                                            const data = await res.json()
                                            setAuditTrace(data)
                                            setShowTraceModal(true)
                                        }
                                    } catch (err) {
                                        console.error('Audit trace fetch error:', err)
                                    } finally {
                                        setLoadingTrace(false)
                                    }
                                }}
                            >
                                🛡️ {loadingTrace ? '...' : (locale === 'vi' ? 'Xem Audit Trace lỗi' : 'View Audit Trace')}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        )
    }

    // 2. Processing / Pending state
    if (result.status === 'processing' || result.status === 'pending') {
        const pct = result.progress?.percent || 0
        const a1Active = pct < 15
        const a1Done = pct >= 15
        const a2Active = pct >= 15 && pct < 30
        const a2Done = pct >= 30
        const a3Active = pct >= 30 && pct < 85
        const a3Done = pct >= 85
        const a4Active = pct >= 85 && pct < 100
        const a4Done = pct === 100

        const activeStandardClean = getStdLabel(result.standard || form.assessment_standard).split('(')[0].trim()

        return (
            <div className={styles.processingCard}>
                <div className={styles.processingSpinner}>
                    <div className={styles.spinnerRing} />
                    <span className={styles.spinnerIcon}>🤖</span>
                </div>
                <h3 className={styles.processingTitle}>
                    {locale === 'vi' ? 'Hệ thống Đa Tác tử đang phân tích an toàn...' : t('assessment.processingTitle')}
                </h3>
                <div className={styles.processingTabAway}>
                    <span>💡</span>
                    <span>
                        {locale === 'vi'
                            ? 'Bạn có thể chuyển sang tab khác — hệ thống xử lý nền và tự động cập nhật khi xong.'
                            : 'You can switch to another tab — the system processes in the background and auto-updates.'}
                    </span>
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

                <div className={styles.processingDescWrap}>
                    <span className={styles.processingMetaBadge}>
                        🏢 {t('assessment.processingOrg')}: <strong>{result.org_name || form.org_name || '—'}</strong>
                    </span>
                    <span className={styles.processingMetaBadge}>
                        📜 {getStdLabel(result.standard || form.assessment_standard)}
                    </span>
                </div>

                {/* 4-Agent Architecture Pipeline Stepper */}
                <div className={styles.agentStepperWrap}>
                    <div className={styles.agentStepperHeader}>
                        <span className={styles.agentPipelineTitle}>
                            <span>⚡</span>
                            <span>{locale === 'vi' ? 'Tiến trình điều phối Đa Tác tử' : 'Multi-Agent Orchestration Pipeline'}</span>
                        </span>
                        <span className={styles.agentModePill}>
                            100% Local GPU
                        </span>
                    </div>

                    <div className={styles.agentGrid}>
                        {/* Agent 1 */}
                        <div key="card-agent-1" className={`${styles.agentCard} ${a1Active ? styles.agentCardActive : ''} ${a1Done ? styles.agentCardDone : ''}`}>
                            <div className={styles.agentCardTop}>
                                <span
                                    className={`${styles.agentStepNum} ${a1Active ? styles.agentStepNumActive : ''}`}
                                    style={a1Done ? { background: 'var(--accent-green)', color: '#fff' } : {}}
                                >
                                    {a1Done ? '✓' : '1'}
                                </span>
                                <div className={styles.agentBadges}>
                                    <span className={styles.agentRoleBadge}>RAG Retrieval</span>
                                    <span className={styles.agentModelBadge}>bge-m3 · 1024D</span>
                                </div>
                            </div>
                            <div className={styles.agentCardContent}>
                                <h4 className={styles.agentStepTitle}>
                                    {locale === 'vi' ? 'Tác tử 1: Truy xuất tri thức tiêu chuẩn' : 'Agent 1: Standard Knowledge Retrieval'}
                                </h4>
                                <p className={styles.agentStepDesc}>
                                    {locale === 'vi'
                                        ? `ChromaDB Cosine · Nạp điều khoản ${activeStandardClean}`
                                        : `ChromaDB Cosine · Load ${activeStandardClean} controls`}
                                </p>
                            </div>
                        </div>

                        {/* Agent 2 */}
                        <div
                            key="card-agent-2"
                            className={`${styles.agentCard} ${a2Active ? styles.agentCardActive : ''} ${a2Done ? styles.agentCardDone : ''}`}
                            style={!a1Done ? { opacity: 0.5 } : {}}
                        >
                            <div className={styles.agentCardTop}>
                                <span
                                    className={`${styles.agentStepNum} ${a2Active ? styles.agentStepNumActive : ''}`}
                                    style={a2Done ? { background: 'var(--accent-green)', color: '#fff' } : {}}
                                >
                                    {a2Done ? '✓' : '2'}
                                </span>
                                <div className={styles.agentBadges}>
                                    <span className={styles.agentRoleBadge}>Fact Extractor</span>
                                    <span className={styles.agentModelBadge}>qwen2.5-coder:7b</span>
                                </div>
                            </div>
                            <div className={styles.agentCardContent}>
                                <h4 className={styles.agentStepTitle}>
                                    {locale === 'vi' ? 'Tác tử 2: Bóc tách minh chứng kỹ thuật' : 'Agent 2: Technical Fact Extraction'}
                                </h4>
                                <p className={styles.agentStepDesc}>
                                    {locale === 'vi'
                                        ? 'Bóc tách logs, tệp cấu hình, sơ đồ mạng & lập Fact Cards'
                                        : 'Parse logs, server configs, network topology & extract Fact Cards'}
                                </p>
                            </div>
                        </div>

                        {/* Agent 3 */}
                        <div
                            key="card-agent-3"
                            className={`${styles.agentCard} ${a3Active ? styles.agentCardActive : ''} ${a3Done ? styles.agentCardDone : ''}`}
                            style={!a2Done ? { opacity: 0.5 } : {}}
                        >
                            <div className={styles.agentCardTop}>
                                <span
                                    className={`${styles.agentStepNum} ${a3Active ? styles.agentStepNumActive : ''}`}
                                    style={a3Done ? { background: 'var(--accent-green)', color: '#fff' } : {}}
                                >
                                    {a3Done ? '✓' : '3'}
                                </span>
                                <div className={styles.agentBadges}>
                                    <span className={styles.agentRoleBadge}>Compliance Auditor</span>
                                    <span className={styles.agentModelBadge}>gemma4:latest</span>
                                </div>
                            </div>
                            <div className={styles.agentCardContent}>
                                <h4 className={styles.agentStepTitle}>
                                    {locale === 'vi' ? 'Tác tử 3: Thẩm định tuân thủ & GAP' : 'Agent 3: Compliance GAP Reasoning'}
                                </h4>
                                <p className={styles.agentStepDesc}>
                                    {locale === 'vi'
                                        ? 'Đối soát nhóm kiểm soát, tính ma trận rủi ro L × I (93/34 Controls)'
                                        : 'GAP controls analysis & L × I risk scoring matrix (93/34 Controls)'}
                                </p>
                            </div>
                        </div>

                        {/* Agent 4 */}
                        <div
                            key="card-agent-4"
                            className={`${styles.agentCard} ${a4Active ? styles.agentCardActive : ''} ${a4Done ? styles.agentCardDone : ''}`}
                            style={!a3Done ? { opacity: 0.5 } : {}}
                        >
                            <div className={styles.agentCardTop}>
                                <span
                                    className={`${styles.agentStepNum} ${a4Active ? styles.agentStepNumActive : ''}`}
                                    style={a4Done ? { background: 'var(--accent-green)', color: '#fff' } : {}}
                                >
                                    {a4Done ? '✓' : '4'}
                                </span>
                                <div className={styles.agentBadges}>
                                    <span className={styles.agentRoleBadge}>Artifact Synthesizer</span>
                                    <span className={styles.agentModelBadge}>gemma4 + Exporters</span>
                                </div>
                            </div>
                            <div className={styles.agentCardContent}>
                                <h4 className={styles.agentStepTitle}>
                                    {locale === 'vi' ? 'Tác tử 4: Tổng hợp báo cáo IT Audit A4' : 'Agent 4: IT Audit Report Synthesis'}
                                </h4>
                                <p className={styles.agentStepDesc}>
                                    {locale === 'vi'
                                        ? 'Bản thảo A4 Executive Summary, Sổ rủi ro Excel & xOffice'
                                        : 'A4 Executive Summary, Risk Register Excel & xOffice'}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Live Assessment Activity Terminal */}
                <div className={styles.liveConsoleBox}>
                    <div className={styles.liveConsoleHeader}>
                        <div className={styles.liveConsoleTitle}>
                            <span className={styles.liveConsoleDot} />
                            <span>
                                {locale === 'vi'
                                    ? 'Nhật ký điều phối Đa Tác tử thời gian thực (Live Stream)'
                                    : 'Multi-Agent Real-time Orchestration Stream'}
                            </span>
                        </div>
                        <span className={styles.liveConsoleModel}>
                            bge-m3 ➔ qwen2.5-coder ➔ gemma4
                        </span>
                    </div>
                    <div className={styles.liveConsoleBody}>
                        <div key="line-sys" className={styles.liveConsoleLine}>
                            <span className={styles.liveTagSystem}>[Hệ thống]</span>
                            <span className={styles.liveConsoleText}>⚡ Khởi tạo tiến trình đánh giá ngầm (Task ID: {result.id?.slice(0, 8)})</span>
                        </div>
                        <div key="line-rag" className={styles.liveConsoleLine}>
                            <span className={styles.liveTagAgent1}>[Tác tử 1 · bge-m3]</span>
                            <span className={styles.liveConsoleText}>🔍 Nạp tri thức tiêu chuẩn {getStdLabel(result.standard || form.assessment_standard)} & đối chiếu hồ sơ</span>
                        </div>
                        {pct >= 15 && (
                            <div key="line-agent2" className={styles.liveConsoleLine}>
                                <span className={styles.liveTagAgent2}>[Tác tử 2 · Qwen2.5]</span>
                                <span className={styles.liveConsoleText}>📑 Bóc tách log máy chủ, cấu hình an toàn & trích xuất Security Fact Cards</span>
                            </div>
                        )}
                        {pct >= 30 && (
                            <div key="line-agent3" className={styles.liveConsoleLine}>
                                <span className={styles.liveTagAgent3}>[Tác tử 3 · Gemma 4]</span>
                                <span className={styles.liveConsoleText}>⚖️ Thẩm định đối soát khoảng trống GAP Controls & chấm điểm rủi ro L × I</span>
                            </div>
                        )}
                        {pct >= 85 && (
                            <div key="line-agent4" className={styles.liveConsoleLine}>
                                <span className={styles.liveTagAgent4}>[Tác tử 4 · Tổng hợp]</span>
                                <span className={styles.liveConsoleText}>📄 Định dạng bản thảo kiểm toán A4, lập Sổ rủi ro (Risk Register) & xOffice</span>
                            </div>
                        )}
                        {result.progress?.message && (
                            <div key="line-stream" className={`${styles.liveConsoleLine} ${styles.liveConsoleLineActive}`}>
                                <span className={styles.liveTagStream}>[Live Stream]</span>
                                <span className={styles.liveConsoleText}>⏳ {result.progress.message} ({pct}%)</span>
                            </div>
                        )}
                    </div>
                </div>

                <div className={styles.pollingInfo} style={{ justifyContent: 'center', marginTop: '0.75rem' }}>
                    <span className={styles.pollingDot} />
                    <span>{t('assessment.autoCheckEvery', { seconds: POLL_INTERVAL / 1000 })}</span>
                    {result.id && (
                        <span style={{ opacity: 0.7, fontSize: '0.72rem' }}> · ID: {result.id.slice(0, 8)}</span>
                    )}
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

                    </div>
                </div>
            )}

            {/* Enterprise Consolidated Action Toolbar */}
            <div className={styles.miniActionBar}>
                <div className={styles.miniActionBarTop}>
                    <div className={styles.miniBarTitle}>
                        <span>Bộ xuất báo cáo & kiểm toán</span>
                        <span className={styles.miniBarSubtitle}>Khổ A4 · Times New Roman · ISO 27001 / TCVN 11930</span>
                    </div>

                    <div className={styles.consolidatedControls}>
                        {/* 1. Merged xOffice Studio Capsule */}
                        <div className={styles.xOfficeStudioCapsule}>
                            <span className={styles.capsuleLabel}>✏️ xOffice:</span>
                            <button
                                className={styles.capsuleBtn}
                                onClick={() => {
                                    setOfficeFileType('docx')
                                    setShowOfficeModal(true)
                                }}
                                title="Mở trình soạn thảo văn bản A4 với form ô khuyết"
                            >
                                📄 Văn bản
                            </button>
                            <span className={styles.capsuleDivider}>|</span>
                            <button
                                className={styles.capsuleBtn}
                                onClick={() => {
                                    setOfficeFileType('xlsx')
                                    setShowOfficeModal(true)
                                }}
                                title="Mở bảng tính ma trận rủi ro L × I"
                            >
                                📊 Sổ rủi ro
                            </button>
                        </div>

                        {/* 2. Unified Export Dropdown */}
                        <div className={styles.exportDropdownWrap}>
                            <button
                                className={`${styles.exportDropdownTrigger} ${showExportMenu ? styles.exportTriggerActive : ''}`}
                                onClick={() => setShowExportMenu(prev => !prev)}
                                title="Tải báo cáo với các định dạng tiêu chuẩn"
                            >
                                <span>📥 Tải báo cáo</span>
                                <span className={styles.dropdownArrow}>{showExportMenu ? '▲' : '▼'}</span>
                            </button>

                            {showExportMenu && (
                                <div className={styles.exportMenuDropdown}>
                                    <div className={styles.exportMenuHeader}>Chọn định dạng tải về:</div>
                                    <button
                                        className={styles.exportMenuItem}
                                        onClick={() => {
                                            handleExportDocx()
                                            setShowExportMenu(false)
                                        }}
                                        disabled={exportingType === 'docx'}
                                    >
                                        <span className={styles.itemIcon}>📄</span>
                                        <div className={styles.itemContent}>
                                            <div className={styles.itemTitle}>Báo cáo Word (.docx)</div>
                                            <div className={styles.itemDesc}>Cấu trúc 5 phần A4 chuẩn CISO</div>
                                        </div>
                                        <span className={styles.formatPillDocx}>DOCX</span>
                                    </button>

                                    <button
                                        className={styles.exportMenuItem}
                                        onClick={() => {
                                            handleExportSoA()
                                            setShowExportMenu(false)
                                        }}
                                        disabled={exportingType === 'soa'}
                                    >
                                        <span className={styles.itemIcon}>📊</span>
                                        <div className={styles.itemContent}>
                                            <div className={styles.itemTitle}>Bảng SoA (.xlsx)</div>
                                            <div className={styles.itemDesc}>Tuyên bố áp dụng kiểm soát</div>
                                        </div>
                                        <span className={styles.formatPillXlsx}>XLSX</span>
                                    </button>

                                    <button
                                        className={styles.exportMenuItem}
                                        onClick={() => {
                                            handleExportRiskRegister()
                                            setShowExportMenu(false)
                                        }}
                                        disabled={exportingType === 'risk'}
                                    >
                                        <span className={styles.itemIcon}>⚠️</span>
                                        <div className={styles.itemContent}>
                                            <div className={styles.itemTitle}>Sổ đăng ký rủi ro (.xlsx)</div>
                                            <div className={styles.itemDesc}>Ma trận định lượng L × I</div>
                                        </div>
                                        <span className={styles.formatPillRisk}>XLSX</span>
                                    </button>

                                    <button
                                        className={styles.exportMenuItem}
                                        onClick={() => {
                                            handleExportPdf()
                                            setShowExportMenu(false)
                                        }}
                                        disabled={exportingType === 'pdf'}
                                    >
                                        <span className={styles.itemIcon}>📑</span>
                                        <div className={styles.itemContent}>
                                            <div className={styles.itemTitle}>Bản in báo cáo (.pdf)</div>
                                            <div className={styles.itemDesc}>Đóng dấu điện tử và in ấn</div>
                                        </div>
                                        <span className={styles.formatPillPdf}>PDF</span>
                                    </button>

                                    <button
                                        className={styles.exportMenuItem}
                                        onClick={() => {
                                            const blob = new Blob([JSON.stringify(result.json_data || result, null, 2)], { type: 'application/json' })
                                            const url = URL.createObjectURL(blob)
                                            const a = document.createElement('a')
                                            a.href = url
                                            a.download = `assessment_${result.id?.slice(0, 8) || 'data'}.json`
                                            a.click()
                                            URL.revokeObjectURL(url)
                                            setShowExportMenu(false)
                                        }}
                                    >
                                        <span className={styles.itemIcon}>💾</span>
                                        <div className={styles.itemContent}>
                                            <div className={styles.itemTitle}>Dữ liệu thô (.json)</div>
                                            <div className={styles.itemDesc}>Trích xuất toàn bộ cấu trúc API</div>
                                        </div>
                                        <span className={styles.formatPillJson}>JSON</span>
                                    </button>
                                </div>
                            )}
                        </div>

                        {/* 3. Streamlined Actions */}
                        <div className={styles.streamlinedActions}>
                            <button
                                className={styles.miniActionBtnHighlight}
                                onClick={async () => {
                                    if (!result.id) return
                                    setLoadingTrace(true)
                                    setShowTraceModal(true)
                                    try {
                                        const res = await fetch(`/api/iso27001/assessments/${result.id}/audit-trace`)
                                        if (res.ok) {
                                            const traceData = await res.json()
                                            setAuditTrace(traceData)
                                        } else {
                                            setAuditTrace({ error: 'Không thể tải audit trace' })
                                        }
                                    } catch (err) {
                                        setAuditTrace({ error: String(err) })
                                    } finally {
                                        setLoadingTrace(false)
                                    }
                                }}
                                title="Xem chu trình tư duy và đối soát bằng chứng của AI"
                            >
                                🔍 Luồng kiểm chứng (Audit Trace)
                            </button>

                            <button
                                className={styles.miniActionBtnHighlight}
                                onClick={() => setShowProofModal(true)}
                                style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.18), rgba(6, 78, 59, 0.35))', borderColor: 'rgba(52, 211, 153, 0.4)', color: '#34d399' }}
                                title="Chứng minh mô hình và script bóc tách chính xác 100% dữ liệu đầu vào (SHA-256, Fact Cards, Hotfixes, Đối soát chéo)"
                            >
                                🛡️ {locale === 'vi' ? 'Bằng chứng bóc tách 100%' : '100% Extraction Proof'}
                            </button>

                            <button
                                className={styles.miniActionBtn}
                                onClick={() => {
                                    navigator.clipboard?.writeText(result.report || '').catch(() => { })
                                }}
                                title={t('assessment.copyReport')}
                            >
                                📋 Sao chép
                            </button>

                            <button className={styles.miniActionBtnSecondary} onClick={() => setActiveTab('form')}>
                                ← Đánh giá mới
                            </button>

                            <button
                                className={styles.reEvalBtnMini}
                                disabled={loading}
                                onClick={() => {
                                    setSelectedAiModel('gemma4:latest')
                                    set('model_mode', 'local')
                                    setTimeout(() => submit(), 100)
                                }}
                                title={locale === 'vi' ? 'Đánh giá lại bằng mô hình Gemma 4 (Local GPU)' : 'Re-assess with Gemma 4 (Local GPU)'}
                            >
                                ⚡ {locale === 'vi' ? 'Đánh giá lại' : 'Re-assess'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Audit Trace Modal */}
            {showTraceModal && (
                <div className={styles.modalOverlay} onClick={() => setShowTraceModal(false)}>
                    <div className={styles.modalContent} onClick={(e) => e.stopPropagation()} style={{ maxWidth: '820px', maxHeight: '85vh', overflowY: 'auto' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
                            <h3 style={{ margin: 0, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                🛡️ {locale === 'vi' ? 'Runtime Audit Trace (Kiểm Chứng Tác Vụ AI)' : 'Runtime Audit Trace Verification'}
                            </h3>
                            <button onClick={() => setShowTraceModal(false)} style={{ background: 'transparent', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>✕</button>
                        </div>

                        {loadingTrace ? (
                            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                                ⏳ {locale === 'vi' ? 'Đang tải dữ liệu kiểm chứng SQLite...' : 'Loading verifiable SQLite trace...'}
                            </div>
                        ) : auditTrace?.error ? (
                            <div style={{ color: 'var(--accent-red)', padding: '1rem' }}>⚠️ {auditTrace.error}</div>
                        ) : auditTrace ? (
                            <div>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem', background: 'var(--bg-secondary)', padding: '0.85rem', borderRadius: '8px' }}>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Actual Model</div>
                                        <div style={{ fontWeight: 600, color: 'var(--accent-blue)' }}>{auditTrace.summary?.actual_models_used?.join(', ') || 'gemma4:latest'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>RAG Collections</div>
                                        <div style={{ fontWeight: 600 }}>{auditTrace.summary?.rag_collections_queried?.join(', ') || 'iso27001'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Total Audit Events</div>
                                        <div style={{ fontWeight: 600, color: 'var(--accent-green)' }}>{auditTrace.summary?.total_audit_events || auditTrace.events?.length || 0} events</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Code Version</div>
                                        <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{auditTrace.summary?.code_version || 'v1.2.0-rel'}</div>
                                    </div>
                                </div>

                                <h4 style={{ margin: '1rem 0 0.5rem 0', fontSize: '0.95rem' }}>
                                    {locale === 'vi' ? 'Các sự kiện Runtime theo thời gian (Append-Only):' : 'Chronological Runtime Events (Append-Only):'}
                                </h4>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '350px', overflowY: 'auto' }}>
                                    {auditTrace.events?.map((ev, idx) => (
                                        <div key={idx} style={{ border: '1px solid var(--border)', borderRadius: '6px', padding: '0.65rem', background: 'var(--card-bg)' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem' }}>
                                                <strong style={{ color: 'var(--accent-blue)' }}>{ev.event_type}</strong>
                                                <span style={{ color: 'var(--text-secondary)', fontSize: '0.72rem' }}>{ev.created_at}</span>
                                            </div>
                                            <pre style={{ margin: 0, fontSize: '0.72rem', background: 'var(--bg-secondary)', padding: '0.5rem', borderRadius: '4px', overflowX: 'auto' }}>
                                                {JSON.stringify(ev.payload, null, 2)}
                                            </pre>
                                        </div>
                                    ))}
                                </div>

                                <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                        🔒 Dữ liệu đã được khử PII & Redacted SHA-256 an toàn.
                                    </span>
                                    <button
                                        className={styles.btnPrimary}
                                        onClick={() => {
                                            const blob = new Blob([JSON.stringify(auditTrace, null, 2)], { type: 'application/json' })
                                            const url = URL.createObjectURL(blob)
                                            const a = document.createElement('a')
                                            a.href = url
                                            a.download = `audit_trace_${result.id?.slice(0, 8) || 'trace'}.json`
                                            a.click()
                                            URL.revokeObjectURL(url)
                                        }}
                                    >
                                        📥 {locale === 'vi' ? 'Tải File Audit Trace JSON' : 'Download Audit Trace JSON'}
                                    </button>
                                </div>
                            </div>
                        ) : null}
                    </div>
                </div>
            )}

            <div className={styles.reportSection}>
                <div className={styles.md}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {result.report || ''}
                    </ReactMarkdown>
                </div>
            </div>

            {/* xOffice Interactive Web Editor Modal */}
            <OfficeEditorModal
                isOpen={showOfficeModal}
                onClose={() => setShowOfficeModal(false)}
                fileType={officeFileType}
                assessmentId={result.id}
                initialReport={result.report || ''}
                jsonData={result.json_data || {}}
                orgName={form?.org_name || 'Doanh nghiệp'}
                standardName={getStdLabel(form?.assessment_standard)}
            />

            {/* 100% Evidence Extraction Proof Modal */}
            <EvidenceExtractionProofModal
                isOpen={showProofModal}
                onClose={() => setShowProofModal(false)}
                assessmentId={result.id}
            />
        </>
    )
}
