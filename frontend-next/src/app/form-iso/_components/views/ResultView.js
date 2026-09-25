'use client'

import { useState, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './views.module.css'
import SvgGauge from '../ui/SvgGauge'
import { useTranslation } from '@/components/LanguageProvider'
import {
    calcWeightedCoverage,
    calcWeightedScore,
    calcCategoryBreakdown,
    calcCategoryComplianceBreakdown,
    normalizeAssessmentMetrics,
    isValidNumber,
    WEIGHT_SCORE
} from '../../../../data/standards'
import OfficeEditorModal from '@/components/OfficeEditorModal'
import EvidenceExtractionProofModal from '@/components/EvidenceExtractionProofModal'
import { useToast } from '@/components/Toast'

const POLL_INTERVAL = 8000

function formatModelLabel(rawModel) {
    if (!rawModel) return 'Ollama · qwen2.5-coder:7b'
    let rawStr = ''
    if (typeof rawModel === 'string') {
        rawStr = rawModel
    } else if (typeof rawModel === 'object') {
        rawStr = rawModel.model || rawModel.phase1 || rawModel.name || ''
    }
    let cleaned = rawStr.replace(/\\:/g, ':').replace(/\\\//g, '/').trim()
    if (!cleaned) return 'Ollama · qwen2.5-coder:7b'
    if (cleaned.toLowerCase().includes('qwen2.5-coder')) {
        return 'Ollama · qwen2.5-coder:7b'
    }
    if (cleaned.toLowerCase().includes('gemma')) {
        return 'Ollama · gemma4:latest'
    }
    if (cleaned.toLowerCase().includes('claude')) {
        return 'Anthropic · Claude 3.5 Sonnet'
    }
    if (cleaned.startsWith('ollama/')) {
        return `Ollama · ${cleaned.replace('ollama/', '')}`
    }
    if (cleaned.startsWith('ollama:')) {
        return `Ollama · ${cleaned.replace('ollama:', '')}`
    }
    return cleaned
}

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
    onStartNewAssessment,
}) {
    const { t, locale } = useTranslation()
    let toastNotifier = null
    try {
        toastNotifier = useToast()
    } catch (e) {
        // Fallback gracefully if mounted outside ToastProvider
    }
    const showToast = (msg, type = 'info') => {
        if (toastNotifier?.showToast) {
            toastNotifier.showToast(msg, type)
        }
    }

    const [auditTrace, setAuditTrace] = useState(null)
    const [showTraceModal, setShowTraceModal] = useState(false)
    const [loadingTrace, setLoadingTrace] = useState(false)
    const [showProofModal, setShowProofModal] = useState(false)
    const [showOfficeModal, setShowOfficeModal] = useState(false)
    const [officeFileType, setOfficeFileType] = useState('docx')
    const [exportingType, setExportingType] = useState(null)
    const [showExportMenu, setShowExportMenu] = useState(false)
    const [exportError, setExportError] = useState(null)

    const rawStd = result?.standard || form?.assessment_standard || 'iso27001'
    const activeStandardId = (typeof rawStd === 'object' && rawStd !== null) ? (rawStd.id || 'iso27001') : rawStd
    const activeStandard = availableStandards?.find(s => s.id === activeStandardId) || currentStandard
    const metrics = normalizeAssessmentMetrics(result, activeStandard?.controls || [])

    // Ensure activeReport resolves and consistently reflects Weighted Compliance (Must be top-level hook!)
    const rawReport = result?.report || result?.result?.report || result?.json_data?.report || ''
    const activeReport = useMemo(() => {
        if (!rawReport) return ''
        let rep = rawReport
        const wCompPct = isValidNumber(metrics?.weightedCompliance?.percentage)
            ? `${metrics.weightedCompliance.percentage.toFixed(1)}%`
            : null

        if (wCompPct) {
            rep = rep.replace(/\|\s*[\*\-]+\s*(?:\*\*)?/g, '| **')
            if (locale === 'vi') {
                rep = rep.replace(/(\|\s*\*\*(?:Tỷ\s*lệ|Mức)?\s*tuân\s*thủ\s*có\s*trọng\s*số[^\*\|]*\*\*\s*\|\s*)(?:\*\*)?[0-9\.]+%(?:\*\*)?/gi, `$1**${wCompPct}**`)
                rep = rep.replace(/(^|\n)([ \t]*[\*\-]\s*(?:\*\*)?(?:Mức|Tỷ\s*lệ)\s*tuân\s*thủ\s*có\s*trọng\s*số:?(?:\*\*)?:?\s*)(?:[0-9\.]+%|\*\*[0-9\.]+%\*\*)/gi, `$1- **Tuân thủ có trọng số:** ${wCompPct}`)
                rep = rep.replace(/(^|\n)([ \t]*[\*\-]\s*(?:\*\*)?Compliance\s*Score[^\:]*:?(?:\*\*)?:?\s*)(?:\*\*)?[0-9\.]+%(?:\*\*)?/gi, `$1- **Tuân thủ có trọng số:** ${wCompPct}`)
                rep = rep.replace(/(?<!\| )(?<!\|\s)(?:Mức\s*tuân\s*thủ|Tuân\s*thủ\s*có\s*trọng\s*số)\s*[0-9\.]+%(\s*cho\s*thấy)/gi, `Tuân thủ có trọng số ${wCompPct}$1`)
                rep = rep.replace(/(^|\n)([ \t]*[\*\-]\s*\*\*Tỷ\s*lệ\s*Tuân\s*thủ\s*có\s*trọng\s*số\s*(?:\(Weighted\s*Compliance\))?:\*\*\s*)[0-9\.]+%?/gi, `$1- **Tuân thủ có trọng số:** ${wCompPct}`)
                rep = rep.replace(/Weighted\s*Coverage\s*\((?:Kỳ\s*vọng|Expected)\)/gi, 'Tuân thủ kỳ vọng')
                rep = rep.replace(/\(Weighted\s*Compliance\)/gi, '')
            } else {
                rep = rep.replace(/(\|\s*\*\*(?:(?:Tỷ\s*lệ|Mức)?\s*tuân\s*thủ\s*có\s*trọng\s*số|Weighted\s*Compliance)[^\*\|]*\*\*\s*\|\s*)(?:\*\*)?[0-9\.]+%(?:\*\*)?/gi, `| **Weighted Compliance** | **${wCompPct}**`)
                rep = rep.replace(/(^|\n)([ \t]*[\*\-]\s*(?:\*\*)?(?:Mức|Tỷ\s*lệ)?\s*(?:tuân\s*thủ\s*có\s*trọng\s*số|Weighted\s*Compliance):?(?:\*\*)?:?\s*)(?:[0-9\.]+%|\*\*[0-9\.]+%\*\*)/gi, `$1- **Weighted Compliance:** ${wCompPct}`)
                rep = rep.replace(/(^|\n)([ \t]*[\*\-]\s*(?:\*\*)?Compliance\s*Score[^\:]*:?(?:\*\*)?:?\s*)(?:\*\*)?[0-9\.]+%(?:\*\*)?/gi, `$1- **Weighted Compliance:** ${wCompPct}`)
                rep = rep.replace(/(?<!\| )(?<!\|\s)(?:Mức\s*tuân\s*thủ|Weighted\s*Compliance)\s*[0-9\.]+%(\s*cho\s*thấy)/gi, `Weighted Compliance ${wCompPct}$1`)
                rep = rep.replace(/(^|\n)([ \t]*[\*\-]\s*\*\*(?:Tỷ\s*lệ\s*Tuân\s*thủ\s*có\s*trọng\s*số|Weighted\s*Compliance)\s*(?:\(Weighted\s*Compliance\))?:\*\*\s*)[0-9\.]+%?/gi, `$1- **Weighted Compliance:** ${wCompPct}`)
                rep = rep.replace(/Weighted\s*Coverage\s*\((?:Kỳ\s*vọng|Expected)\)/gi, 'Expected Compliance')
                rep = rep.replace(/Tuân\s*thủ\s*kỳ\s*vọng/gi, 'Expected Compliance')
                rep = rep.replace(/Tuân\s*thủ\s*có\s*trọng\s*số/gi, 'Weighted Compliance')
                rep = rep.replace(/Mức\s*tuân\s*thủ\s*có\s*trọng\s*số/gi, 'Weighted Compliance')
            }
        }
        return rep
    }, [rawReport, metrics?.weightedCompliance?.percentage, locale])

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

    const getFilenameFromHeader = (header, fallbackName) => {
        if (!header) return fallbackName
        const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i)
        if (utf8Match && utf8Match[1]) {
            try {
                return decodeURIComponent(utf8Match[1].replace(/['"]/g, ''))
            } catch (e) {}
        }
        const match = header.match(/filename="?([^";]+)"?/i)
        if (match && match[1]) {
            return match[1].trim()
        }
        return fallbackName
    }

    const executeExport = async (type, endpoint, fallbackFilename) => {
        const aid = result?.id || result?.assessment_id
        if (!aid) {
            const err = 'Không xác định được mã đánh giá (assessment_id)'
            setExportError(err)
            showToast(err, 'error')
            return
        }
        setExportingType(type)
        setExportError(null)
        try {
            const res = await fetch(endpoint, { method: 'POST' })
            if (res.ok) {
                const blob = await res.blob()
                const cd = res.headers.get('content-disposition')
                const filename = getFilenameFromHeader(cd, fallbackFilename)
                downloadBlob(blob, filename)
                showToast(`Đã tải thành công: ${filename}`, 'success')
            } else {
                let detail = `Lỗi tải file (HTTP ${res.status})`
                try {
                    const errJson = await res.json()
                    detail = errJson.detail || errJson.error || detail
                } catch (e) {
                    const text = await res.text()
                    if (text) detail = text.slice(0, 150)
                }
                setExportError(detail)
                showToast(detail, 'error')
                console.error(`Export ${type} failed:`, detail)
            }
        } catch (err) {
            const msg = `Lỗi kết nối khi tải file: ${err.message || err}`
            setExportError(msg)
            showToast(msg, 'error')
            console.error(`Export ${type} error:`, err)
        } finally {
            setExportingType(null)
        }
    }

    const handleExportDocx = () => {
        const aid = result?.id || result?.assessment_id || ''
        executeExport('docx', `/api/iso27001/assessments/${aid}/export-docx`, `IT_Audit_Report_${aid.slice(0, 8)}.docx`)
    }

    const handleExportRiskRegister = () => {
        const aid = result?.id || result?.assessment_id || ''
        executeExport('risk', `/api/iso27001/assessments/${aid}/export-risk-register`, `Risk_Register_${aid.slice(0, 8)}.xlsx`)
    }

    const handleExportPdf = () => {
        const aid = result?.id || result?.assessment_id || ''
        executeExport('pdf', `/api/iso27001/assessments/${aid}/export-pdf`, `Audit_Report_${aid.slice(0, 8)}.pdf`)
    }

    const handleExportSoA = async () => {
        const aid = result?.id || result?.assessment_id || ''
        if (!aid) {
            const err = 'Không xác định được mã đánh giá'
            setExportError(err)
            showToast(err, 'error')
            return
        }
        setExportingType('soa')
        setExportError(null)
        try {
            const res = await fetch('/api/iso27001/soa/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ assessment_id: aid, org_name: form?.org_name || '' })
            })
            if (res.ok) {
                const blob = await res.blob()
                const cd = res.headers.get('content-disposition')
                const isTcvn = String(result?.standard?.id || result?.standard_id || form?.standard || '').toLowerCase().includes('tcvn') || String(result?.standard?.name || result?.standard_name || '').includes('11930')
                const defaultSoa = isTcvn ? `SoA_TCVN11930_${aid.slice(0, 8)}.xlsx` : `SoA_ISO27001_${aid.slice(0, 8)}.xlsx`
                const filename = getFilenameFromHeader(cd, defaultSoa)
                downloadBlob(blob, filename)
                showToast(`Đã tải thành công: ${filename}`, 'success')
            } else {
                let detail = `Lỗi tải SoA (HTTP ${res.status})`
                try {
                    const errJson = await res.json()
                    detail = errJson.detail || errJson.error || detail
                } catch (e) {
                    const text = await res.text()
                    if (text) detail = text.slice(0, 150)
                }
                setExportError(detail)
                showToast(detail, 'error')
                console.error('Export SoA failed:', detail)
            }
        } catch (err) {
            const msg = `Lỗi kết nối khi tải SoA: ${err.message || err}`
            setExportError(msg)
            showToast(msg, 'error')
            console.error('Export SoA error:', err)
        } finally {
            setExportingType(null)
        }
    }

    const handleExportAuditTrace = async () => {
        const aid = result?.id || result?.assessment_id || ''
        if (!aid) return
        setExportingType('trace')
        setExportError(null)
        try {
            if (auditTrace && !auditTrace.error) {
                const blob = new Blob([JSON.stringify(auditTrace, null, 2)], { type: 'application/json' })
                downloadBlob(blob, `audit_trace_${aid.slice(0, 8) || 'trace'}.json`)
                showToast(`Đã tải thành công: audit_trace_${aid.slice(0, 8) || 'trace'}.json`, 'success')
            } else {
                const res = await fetch(`/api/iso27001/assessments/${aid}/audit-trace`)
                if (res.ok) {
                    const data = await res.json()
                    setAuditTrace(data)
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                    downloadBlob(blob, `audit_trace_${aid.slice(0, 8) || 'trace'}.json`)
                    showToast(`Đã tải thành công: audit_trace_${aid.slice(0, 8) || 'trace'}.json`, 'success')
                } else {
                    const detail = `Lỗi tải Audit Trace (HTTP ${res.status})`
                    setExportError(detail)
                    showToast(detail, 'error')
                }
            }
        } catch (err) {
            const msg = `Lỗi kết nối khi tải Audit Trace: ${err.message || err}`
            setExportError(msg)
            showToast(msg, 'error')
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

                {/* Real-time Provisional Scope & Coverage Display */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
                    gap: '0.85rem',
                    margin: '1.25rem 0',
                    width: '100%'
                }}>
                    {/* 1. Provisional Weighted Coverage with Circular Gauge */}
                    <div style={{
                        background: 'rgba(59, 130, 246, 0.08)',
                        border: '1px solid rgba(59, 130, 246, 0.25)',
                        borderRadius: '12px',
                        padding: '0.85rem 1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.85rem'
                    }}>
                        <SvgGauge
                            percent={metrics.weightedCoverage.percentage}
                            size={64}
                            color="var(--accent-blue)"
                        />
                        <div>
                            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--accent-blue)', fontWeight: 700 }}>
                                {locale === 'vi' ? 'ĐỘ PHỦ CÓ TRỌNG SỐ (TẠM TÍNH)' : 'WEIGHTED COVERAGE (PROVISIONAL)'}
                            </div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.1rem' }}>
                                {metrics.weightedCoverage.score} / {metrics.weightedCoverage.maxScore} — {metrics.weightedCoverage.percentage.toFixed(1)}%
                            </div>
                        </div>
                    </div>

                    {/* 2. Raw Coverage */}
                    <div style={{
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '12px',
                        padding: '0.85rem 1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center'
                    }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {locale === 'vi' ? 'Phạm vi thô' : 'Raw Coverage'}
                        </div>
                        <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                            {metrics.rawCoverage.implemented}/{metrics.rawCoverage.total} — {metrics.rawCoverage.percentage.toFixed(1)}%
                        </div>
                    </div>

                    {/* 3. Weighted Compliance */}
                    <div style={{
                        background: 'rgba(245, 158, 11, 0.06)',
                        border: '1px solid rgba(245, 158, 11, 0.25)',
                        borderRadius: '12px',
                        padding: '0.85rem 1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center'
                    }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--accent-amber, #f59e0b)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {locale === 'vi' ? 'Tuân thủ có trọng số' : 'Weighted Compliance'}
                        </div>
                        <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent-amber, #f59e0b)', marginTop: '0.2rem' }}>
                            ⏳ {locale === 'vi' ? 'Đang thẩm định...' : 'Under Assessment...'}
                        </div>
                    </div>
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
    const activeImplList = (result.implemented_controls && result.implemented_controls.length > 0)
        ? result.implemented_controls
        : (result.json_data?.compliance?.implemented_controls && result.json_data.compliance.implemented_controls.length > 0)
            ? result.json_data.compliance.implemented_controls
            : form?.implemented_controls || []

    // Authoritative display percentage strictly from weightedCompliance
    // Zero (0.0) is a valid score and must NEVER fallback to weightedCoverage
    const displayPct = isValidNumber(metrics.weightedCompliance?.percentage)
        ? Number(metrics.weightedCompliance.percentage)
        : null

    const displayPctStr = displayPct !== null ? `${displayPct.toFixed(1)}%` : (locale === 'vi' ? 'Đang thẩm định...' : 'Under Assessment...')

    const displayOrg = result.org_name || form?.org_name || t('assessment.processingOrg')
    const displayStd = getStdLabel(activeStandardId)

    const modelName = formatModelLabel(result.model_used)

    // Category analysis for preliminary weighted coverage (sums to 289/495)
    const categoryBreakdown = calcCategoryBreakdown(activeImplList, activeStandard?.controls || [])

    // Optional verified category compliance breakdown from AI verdicts
    const controlsList = result.json_data?.controls || result.result?.json_data?.controls || result.controls || []
    const hasControlsVerdicts = Array.isArray(controlsList) && controlsList.some(c => c.assessment_verdict || c.evidence_verdict)
    const categoryCompliance = hasControlsVerdicts
        ? calcCategoryComplianceBreakdown(controlsList, activeStandard?.controls || [])
        : []


    return (
        <>
            {metrics.isLegacy && (
                <div className={styles.legacyWarningBanner}>
                    <span>⚠️</span>
                    <span>{locale === 'vi' ? 'Kết quả legacy – chưa đối soát theo verdict_weighted_v2' : 'Legacy result – not verified under verdict_weighted_v2'}</span>
                </div>
            )}

            {(form?.template_id || result?.template_id || result?.json_data?.template_id || result?.metadata?.template_id) && (
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px 16px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    border: '1px solid var(--accent-amber, #f59e0b)',
                    color: '#d97706',
                    fontSize: '0.875rem',
                    marginBottom: '1rem',
                    fontWeight: 500
                }}>
                    <span style={{ fontSize: '1.1rem' }}>📋</span>
                    <span>
                        <strong>{locale === 'vi' ? 'Dữ liệu mẫu từ template' : 'Sample Data from Template'}</strong>
                        {form?.template_name || result?.template_name ? ` (${form?.template_name || result?.template_name})` : ''}
                        {' — '}
                        {locale === 'vi' 
                            ? 'Dữ liệu mẫu từ template, không được coi là evidence (minh chứng kỹ thuật).'
                            : 'Sample data from template, not considered technical evidence.'}
                    </span>
                </div>
            )}

            <div className={styles.scoreHero}>
                <div className={styles.scoreHeroLeft}>
                    <div className={styles.svgGaugeWrap}>
                        <SvgGauge
                            percent={displayPct !== null ? displayPct : 0}
                            size={120}
                            color={
                                displayPct === null ? 'var(--accent-amber,#f59e0b)' :
                                displayPct >= 80 ? 'var(--accent-green)' :
                                displayPct >= 50 ? 'var(--accent-blue)' :
                                displayPct >= 25 ? 'var(--accent-amber,#f59e0b)' :
                                'var(--accent-red)'
                            }
                        />
                        <div className={styles.svgGaugeOverlay}>
                            <span className={`${styles.scoreNum} ${
                                displayPct === null ? styles.scoreNumPartial :
                                displayPct >= 80 ? styles.scoreNumFull :
                                displayPct >= 50 ? styles.scoreNumMostly :
                                displayPct >= 25 ? styles.scoreNumPartial :
                                styles.scoreNumLow
                            }`}>{displayPctStr}</span>
                            <span className={styles.scoreUnit}>
                                {metrics.isLegacy ? (locale === 'vi' ? 'Điểm cũ' : 'Legacy Score') : 'Weighted Compliance'}
                            </span>
                        </div>
                    </div>
                </div>

                <div className={styles.scoreHeroRight}>
                    <div className={styles.scoreOrg}>{displayOrg}</div>
                    <div className={styles.scoreStd}>{displayStd}</div>
                    <div className={`${styles.complianceBadge} ${
                        metrics.statusBadgeType === 'pending' ? styles.badgePendingReview :
                        displayPct === null ? styles.badgePartial :
                        displayPct >= 80 ? styles.badgeFull :
                        displayPct >= 50 ? styles.badgeMostly :
                        displayPct >= 25 ? styles.badgePartial :
                        styles.badgeLow
                    }`}>
                        {metrics.statusBadge || (locale === 'vi' ? 'Đang thẩm định...' : 'Under Assessment...')}
                    </div>
                    <div className={styles.scoreStats}>
                        {/* 1. Weighted Compliance */}
                        <div className={styles.scoreStat}>
                            <span className={styles.scoreStatNum}>
                                {metrics.weightedCompliance.score !== null ? `${metrics.weightedCompliance.score} / ${metrics.weightedCompliance.maxScore} ${locale === 'vi' ? 'điểm' : 'pts'} · ${metrics.weightedCompliance.percentage.toFixed(1)}%` : (metrics.isLegacy ? (locale === 'vi' ? 'Chưa đối soát' : 'Not verified') : '0.0%')}
                            </span>
                            <span className={styles.scoreStatLabel}>
                                {locale === 'vi' ? 'Tuân thủ có trọng số' : 'Weighted Compliance'}
                            </span>
                        </div>
                        <div className={styles.scoreStatDivider} />

                        {/* 2. Tuân thủ kỳ vọng / Expected Compliance */}
                        <div className={styles.scoreStat} title={locale === 'vi' ? `Tuân thủ kỳ vọng: ${metrics.weightedCoverage.score} / ${metrics.weightedCoverage.maxScore} điểm (${metrics.weightedCoverage.percentage.toFixed(1)}%) dựa trên các biện pháp tự khai triển khai.` : `Expected Compliance: ${metrics.weightedCoverage.score} / ${metrics.weightedCoverage.maxScore} pts (${metrics.weightedCoverage.percentage.toFixed(1)}%) based on self-declared implemented controls.`}>
                            <span className={styles.scoreStatNum}>
                                {typeof metrics.weightedCoverage?.percentage === 'number' && !isNaN(metrics.weightedCoverage.percentage)
                                    ? `${metrics.weightedCoverage.percentage.toFixed(1)}%`
                                    : '0.0%'}
                            </span>
                            <span className={styles.scoreStatLabel}>
                                {locale === 'vi' ? 'Tuân thủ kỳ vọng' : 'Expected Compliance'}
                            </span>
                        </div>
                        <div className={styles.scoreStatDivider} />

                        {/* 3. Evidence-verified satisfied controls */}
                        <div className={styles.scoreStat} title={locale === 'vi' ? 'Chỉ gồm verdict satisfied; dùng để tính điểm.' : 'Counts only final satisfied verdicts with evidence citation.'}>
                            <span className={styles.scoreStatNum}>{metrics.satisfiedCount} / {metrics.rawCoverage.total} {locale === 'vi' ? 'biện pháp' : 'controls'}</span>
                            <span className={styles.scoreStatLabel}>
                                {locale === 'vi' ? 'Đạt theo minh chứng' : 'Evidence-verified satisfied controls'}
                            </span>
                        </div>
                        <div className={styles.scoreStatDivider} />

                        {/* 4. Self-declared implemented */}
                        <div className={styles.scoreStat} title={locale === 'vi' ? 'Không được dùng để tính Tuân thủ có trọng số.' : 'Self-declared only; not used to calculate Weighted Compliance.'}>
                            <span className={styles.scoreStatNum}>{metrics.rawCoverage.implemented} / {metrics.rawCoverage.total} {locale === 'vi' ? 'biện pháp' : 'controls'}</span>
                            <span className={styles.scoreStatLabel}>
                                {locale === 'vi' ? 'Triển khai tự khai' : 'Self-declared Implemented'}
                            </span>
                        </div>
                        <div className={styles.scoreStatDivider} />

                        {/* 5. Pending Expert Review */}
                        <div className={styles.scoreStat} title={locale === 'vi' ? 'Các kiểm soát có mâu thuẫn hoặc cần chuyên gia thẩm định trực tiếp; nhận hệ số 0.0.' : 'Controls with conflicts or requiring manual auditor review; factor 0.0.'}>
                            <span className={styles.scoreStatNum} style={{ color: (metrics.needsReviewCount > 0 ? 'var(--accent-amber, #f59e0b)' : 'inherit') }}>
                                {metrics.needsReviewCount || 0} {locale === 'vi' ? 'biện pháp' : 'controls'}
                            </span>
                            <span className={styles.scoreStatLabel}>
                                {locale === 'vi' ? 'Đang chờ chuyên gia rà soát' : 'Pending Expert Review'}
                            </span>
                        </div>
                    </div>
                    <div className={styles.modelChips}>
                        <span className={styles.modelChip}>🤖 {modelName}</span>
                        <span className={styles.modelChip} title="Thang điểm chuẩn: Critical=10, High=5, Medium=3, Low=1">⚖️ Critical=10 · High=5 · Medium=3 · Low=1</span>
                    </div>
                </div>
            </div>

            <div className={styles.breakdownPanel}>
                <h4 className={styles.breakdownTitle}>
                    📋 {locale === 'vi' ? 'Độ phủ tự khai sơ bộ theo danh mục' : 'Raw Coverage by Category'}
                </h4>
                <div className={styles.breakdownGrid}>
                    {categoryBreakdown.map((cat, idx) => (
                        <div key={idx} className={styles.breakdownItem}>
                            <div className={styles.breakdownItemHeader}>
                                <span className={styles.breakdownCatName}>{cat.category}</span>
                                <span className={`${styles.breakdownPct} ${cat.percent >= 80 ? styles.scoreNumFull :
                                        cat.percent >= 50 ? styles.scoreNumMostly :
                                            cat.percent >= 25 ? styles.scoreNumPartial :
                                                styles.scoreNumLow
                                    }`}>{cat.percent}%</span>
                            </div>
                            <div className={styles.breakdownBarTrack}>
                                <div
                                    className={styles.breakdownBarFill}
                                    style={{
                                        width: `${cat.percent}%`,
                                        background: cat.percent >= 80 ? 'var(--accent-green)' :
                                            cat.percent >= 50 ? 'var(--accent-blue)' :
                                                cat.percent >= 25 ? 'var(--accent-amber,#f59e0b)' :
                                                    'var(--accent-red)'
                                    }}
                                />
                            </div>
                            <div className={styles.breakdownMeta}>
                                <span>{cat.implemented}/{cat.total} {t('assessment.controls')}</span>
                                <span>({cat.percent}%)</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {hasControlsVerdicts && categoryCompliance.length > 0 && (
                <div className={styles.breakdownPanel} style={{ marginTop: '1.25rem' }}>
                    <h4 className={styles.breakdownTitle}>
                        🛡️ {locale === 'vi' ? 'Thẩm định kiểm toán theo danh mục' : 'Verified Compliance by Category'}
                    </h4>
                    <div className={styles.breakdownGrid}>
                        {categoryCompliance.map((cat, idx) => (
                            <div key={idx} className={styles.breakdownItem}>
                                <div className={styles.breakdownItemHeader}>
                                    <span className={styles.breakdownCatName}>{cat.category}</span>
                                    <span className={`${styles.breakdownPct} ${cat.percent >= 80 ? styles.scoreNumFull :
                                            cat.percent >= 50 ? styles.scoreNumMostly :
                                                cat.percent >= 25 ? styles.scoreNumPartial :
                                                    styles.scoreNumLow
                                        }`}>{cat.percent}%</span>
                                </div>
                                <div className={styles.breakdownBarTrack}>
                                    <div
                                        className={styles.breakdownBarFill}
                                        style={{
                                            width: `${cat.percent}%`,
                                            background: cat.percent >= 80 ? 'var(--accent-green)' :
                                                cat.percent >= 50 ? 'var(--accent-blue)' :
                                                    cat.percent >= 25 ? 'var(--accent-amber,#f59e0b)' :
                                                        'var(--accent-red)'
                                        }}
                                    />
                                </div>
                                <div className={styles.breakdownMeta}>
                                    <span>{cat.satisfied}/{cat.total} {locale === 'vi' ? 'đạt kiểm toán' : 'satisfied'}</span>
                                    <span>{cat.achieved}/{cat.maxScore} {t('assessment.points')}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

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

            {/* Detailed Controls Table Panel */}
            {(() => {
                const controlsList = result.controls || result.json_data?.controls || []
                const WEIGHT_MAP = { critical: 10, high: 5, medium: 3, low: 1, 10: 10, 5: 5, 3: 3, 1: 1 }
                const getWeightPoints = (w) => {
                    if (typeof w === 'number') return w
                    if (!w) return 3
                    return WEIGHT_MAP[String(w).toLowerCase()] || 3
                }
                const getWeightLevel = (w) => {
                    if (typeof w === 'number') {
                        return w >= 10 ? 'critical' : w >= 5 ? 'high' : w >= 3 ? 'medium' : 'low'
                    }
                    return String(w || 'medium').toLowerCase()
                }
                const getVerdictFactor = (verdict) => {
                    const v = String(verdict || 'missing').toLowerCase()
                    if (v === 'satisfied') return 1.0
                    if (v === 'partial' || v === 'partially_satisfied') return 0.5
                    return 0.0
                }

                return (
                    <div className={styles.controlTablePanel}>
                        <div className={styles.controlTableTitle}>
                            <span>📋 {locale === 'vi' ? 'Bảng đối soát kiểm soát chi tiết' : 'Detailed Control Assessment Table'}</span>
                            <span className={styles.controlTableSubtitle} title="Thang điểm chuẩn: Critical=10, High=5, Medium=3, Low=1">
                                ⚖️ Critical = 10 · High = 5 · Medium = 3 · Low = 1
                            </span>
                        </div>

                        {controlsList.length === 0 ? (
                            <div className={styles.noDetailsNotice}>
                                ℹ️ {locale === 'vi' ? 'Không có dữ liệu chi tiết kiểm soát (Historical Assessment)' : 'No detailed control data available (Historical Assessment)'}
                            </div>
                        ) : (
                            <div className={styles.controlTableScroll}>
                                <table className={styles.controlTable}>
                                    <thead>
                                        <tr>
                                            <th style={{ width: '90px' }}>Control ID</th>
                                            <th style={{ minWidth: '180px' }}>{locale === 'vi' ? 'Tên kiểm soát' : 'Control Name'}</th>
                                            <th style={{ width: '85px', textAlign: 'center' }}>{locale === 'vi' ? 'Trọng số' : 'Weight'}</th>
                                            <th style={{ width: '120px', textAlign: 'center' }}>Verdict</th>
                                            <th style={{ width: '70px', textAlign: 'center' }}>{locale === 'vi' ? 'Hệ số' : 'Factor'}</th>
                                            <th style={{ width: '90px', textAlign: 'center' }}>{locale === 'vi' ? 'Điểm đóng góp' : 'Contribution'}</th>
                                            <th style={{ width: '130px', textAlign: 'center' }}>{locale === 'vi' ? 'Nguồn kết luận' : 'Verdict Source'}</th>
                                            <th style={{ minWidth: '220px' }}>{locale === 'vi' ? 'Lý do & Minh chứng' : 'Rationale & Citations'}</th>
                                            <th style={{ width: '130px' }}>{locale === 'vi' ? 'Đối soát chuyên gia' : 'Expert Review'}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {controlsList.map((ctrl, cIdx) => {
                                            const cid = ctrl.control_id || ctrl.id || `C-${cIdx}`
                                            const label = ctrl.label || cid
                                            const rawW = ctrl.weight_points ?? ctrl.weight
                                            const wPoints = getWeightPoints(rawW)
                                            const wLevel = getWeightLevel(ctrl.weight_level || rawW)
                                            const verdict = String(ctrl.assessment_verdict || ctrl.verdict || 'missing').toLowerCase()
                                            const isConflict = Boolean(ctrl.conflict_detected || verdict === 'needs_expert_review')
                                            const rawFactor = ctrl.verdict_factor !== undefined ? Number(ctrl.verdict_factor) : getVerdictFactor(verdict)
                                            const factor = isConflict ? 0.0 : rawFactor
                                            const contrib = (isConflict || verdict === 'not_evidenced' || verdict === 'missing')
                                                ? 0.0
                                                : (ctrl.weighted_score_contribution !== undefined
                                                    ? Number(ctrl.weighted_score_contribution)
                                                    : Math.round(wPoints * factor * 10) / 10)

                                            const src = ctrl.verdict_source || (isConflict ? 'safe_fallback_conflict' : (verdict === 'needs_expert_review' ? 'safe_fallback_no_evidence' : 'rule_based'))
                                            const isLlm = src === 'llm'
                                            const isConflictSrc = src === 'safe_fallback_conflict'
                                            const isNoEvSrc = src === 'safe_fallback_no_evidence'
                                            const isInvalidSrc = src === 'safe_fallback_invalid_verdict'

                                            return (
                                                <tr key={cid}>
                                                    <td className={styles.ctrlIdCell}>{cid}</td>
                                                    <td style={{ maxWidth: '240px', wordBreak: 'break-word' }}>{label}</td>
                                                    <td style={{ textAlign: 'center' }}>
                                                        <span
                                                            className={`${styles.ctrlWeightBadge} ${
                                                                wLevel === 'critical' ? styles.weightCrit :
                                                                wLevel === 'high' ? styles.weightHigh :
                                                                wLevel === 'medium' ? styles.weightMed : styles.weightLow
                                                            }`}
                                                            title={`Trọng số: ${wLevel.toUpperCase()} = ${wPoints} điểm (Thang 10-5-3-1)`}
                                                        >
                                                            {wLevel} ({wPoints}đ)
                                                        </span>
                                                    </td>
                                                    <td style={{ textAlign: 'center' }}>
                                                        <span className={`${styles.verdictBadge} ${
                                                            verdict === 'satisfied' ? styles.verdictSatisfied :
                                                            (verdict === 'partial' || verdict === 'partially_satisfied') ? styles.verdictPartial :
                                                            verdict === 'needs_expert_review' ? styles.verdictReview :
                                                            verdict === 'not_evidenced' ? styles.verdictNotEvidenced : styles.verdictMissing
                                                        }`}>
                                                            {verdict === 'satisfied' ? '✓ Satisfied' :
                                                             verdict === 'partial' ? '½ Partial' :
                                                             verdict === 'needs_expert_review' ? '⚠️ Review' :
                                                             verdict === 'not_evidenced' ? '○ Not Evidenced' : '✕ Missing'}
                                                        </span>
                                                    </td>
                                                    <td style={{ textAlign: 'center', fontWeight: 600 }}>
                                                        {`${Math.round(factor * 100)}%`}
                                                    </td>
                                                    <td style={{ textAlign: 'center', fontWeight: 700, color: contrib > 0 ? 'var(--accent-green, #34d399)' : 'var(--text-secondary)' }}>
                                                        {contrib.toFixed(1)} pts
                                                    </td>
                                                    <td style={{ textAlign: 'center' }}>
                                                        {(() => {
                                                            const srcLower = String(src || '').toLowerCase()
                                                            let vLabel = 'LLM'
                                                            let vTitle = 'LLM: verdict do suy luận mô hình tạo ra.'
                                                            let vBg = 'rgba(59, 130, 246, 0.15)'
                                                            let vColor = 'var(--accent-blue, #60a5fa)'
                                                            let vBorder = 'rgba(59, 130, 246, 0.3)'

                                                            if (isConflict || isConflictSrc || srcLower.includes('conflict')) {
                                                                vLabel = 'Fallback Conflict'
                                                                vTitle = ctrl.conflict_reason || ctrl.fallback_reason || 'Fallback Conflict: tự khai mâu thuẫn với minh chứng, verdict bị khóa về needs_expert_review.'
                                                                vBg = 'rgba(239, 68, 68, 0.15)'
                                                                vColor = 'var(--accent-red, #f87171)'
                                                                vBorder = 'rgba(239, 68, 68, 0.3)'
                                                            } else if (isNoEvSrc || srcLower.includes('fallback') || srcLower.includes('no_evidence') || verdict === 'not_evidenced' || verdict === 'needs_expert_review') {
                                                                vLabel = 'Fallback No-Ev'
                                                                vTitle = ctrl.fallback_reason || 'Fallback No-Ev: không có minh chứng đủ để suy luận, verdict do quy tắc fallback.'
                                                                vBg = 'rgba(245, 158, 11, 0.15)'
                                                                vColor = 'var(--accent-amber, #fbbf24)'
                                                                vBorder = 'rgba(245, 158, 11, 0.3)'
                                                            } else if (isLlm) {
                                                                vLabel = 'LLM'
                                                                vTitle = 'LLM: verdict do suy luận mô hình tạo ra.'
                                                            }

                                                            return (
                                                                <span
                                                                    style={{
                                                                        display: 'inline-block',
                                                                        fontSize: '0.72rem',
                                                                        padding: '2px 6px',
                                                                        borderRadius: '4px',
                                                                        fontWeight: 600,
                                                                        fontFamily: 'monospace',
                                                                        background: vBg,
                                                                        color: vColor,
                                                                        border: `1px solid ${vBorder}`,
                                                                        cursor: 'help'
                                                                    }}
                                                                    title={vTitle}
                                                                >
                                                                    {vLabel}
                                                                </span>
                                                            )
                                                        })()}
                                                    </td>
                                                    <td style={{ fontSize: '0.8rem', maxWidth: '280px', wordBreak: 'break-word' }}>
                                                        {ctrl.verdict_rationale || ctrl.rationale || ctrl.gap ? (
                                                            <div style={{ color: 'var(--text-primary)', marginBottom: '4px' }}>
                                                                {ctrl.verdict_rationale || ctrl.rationale || ctrl.gap}
                                                            </div>
                                                        ) : null}
                                                        {ctrl.fallback_reason ? (
                                                            <div style={{ fontSize: '0.72rem', color: '#f59e0b', fontStyle: 'italic', marginBottom: '4px' }}>
                                                                ℹ️ {ctrl.fallback_reason}
                                                            </div>
                                                        ) : null}
                                                        {Array.isArray(ctrl.evidence_citations) && ctrl.evidence_citations.length > 0 && (
                                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '2px' }}>
                                                                {ctrl.evidence_citations.map((cit, ci) => {
                                                                    const fn = typeof cit === 'string' ? cit : (cit.file_name || cit.evidence_id || JSON.stringify(cit))
                                                                    return (
                                                                        <span key={ci} style={{
                                                                            fontSize: '0.7rem',
                                                                            padding: '1px 5px',
                                                                            borderRadius: '3px',
                                                                            background: 'rgba(16, 185, 129, 0.12)',
                                                                            color: 'var(--accent-green, #34d399)',
                                                                            border: '1px solid rgba(16, 185, 129, 0.25)',
                                                                            whiteSpace: 'nowrap',
                                                                            maxWidth: '200px',
                                                                            overflow: 'hidden',
                                                                            textOverflow: 'ellipsis'
                                                                        }} title={fn}>
                                                                            📎 {fn}
                                                                        </span>
                                                                    )
                                                                })}
                                                            </div>
                                                        )}
                                                    </td>
                                                    <td>
                                                        {isConflict ? (
                                                            <span className={styles.conflictAlertBadge} title={ctrl.conflict_reason || ctrl.fallback_reason || 'Cần chuyên gia ATTT thẩm định trực tiếp'}>
                                                                ⚠️ {locale === 'vi' ? 'Cần đối soát' : 'Needs Review'}
                                                            </span>
                                                        ) : verdict === 'satisfied' ? (
                                                            <span style={{ color: 'var(--accent-green, #34d399)', fontSize: '0.75rem', fontWeight: 600 }}>✓ {locale === 'vi' ? 'Đã đối soát' : 'Verified'}</span>
                                                        ) : verdict === 'not_evidenced' ? (
                                                            <span style={{ color: 'var(--text-dim, #64748b)', fontSize: '0.75rem' }}>○ {locale === 'vi' ? 'Chưa có minh chứng' : 'Not Evidenced'}</span>
                                                        ) : verdict === 'missing' ? (
                                                            <span style={{ color: 'var(--text-dim, #64748b)', fontSize: '0.75rem' }}>✕ {locale === 'vi' ? 'Thiếu kiểm soát' : 'Missing'}</span>
                                                        ) : (
                                                            <span style={{ color: 'var(--text-dim, #64748b)', fontSize: '0.75rem' }}>—</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )
            })()}

            {/* Enterprise Consolidated Action Toolbar */}
            <div className={styles.miniActionBar}>
                <div className={styles.miniActionBarTop}>
                    <div className={styles.miniBarTitle}>
                        <span>{locale === 'vi' ? 'Bộ xuất báo cáo & kiểm toán' : 'Report & Audit Export Suite'}</span>
                        <span className={styles.miniBarSubtitle}>{locale === 'vi' ? 'Khổ A4 · Times New Roman · ISO 27001 / TCVN 11930' : 'A4 Size · Times New Roman · ISO 27001 / TCVN 11930'}</span>
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
                                title={locale === 'vi' ? "Mở trình soạn thảo văn bản A4 với form ô khuyết" : "Open A4 document editor with fill-in form"}
                            >
                                {locale === 'vi' ? '📄 Văn bản' : '📄 Document'}
                            </button>
                            <span className={styles.capsuleDivider}>|</span>
                            <button
                                className={styles.capsuleBtn}
                                onClick={() => {
                                    setOfficeFileType('xlsx')
                                    setShowOfficeModal(true)
                                }}
                                title={locale === 'vi' ? "Mở bảng tính ma trận rủi ro L × I" : "Open L × I Risk Matrix spreadsheet"}
                            >
                                {locale === 'vi' ? '📊 Sổ rủi ro' : '📊 Risk Register'}
                            </button>
                        </div>

                        {/* 2. Unified Export Dropdown */}
                        <div className={styles.exportDropdownWrap}>
                            <button
                                className={`${styles.exportDropdownTrigger} ${showExportMenu ? styles.exportTriggerActive : ''}`}
                                onClick={() => setShowExportMenu(prev => !prev)}
                                title={locale === 'vi' ? "Tải báo cáo với các định dạng tiêu chuẩn" : "Download reports in standard formats"}
                            >
                                <span>{locale === 'vi' ? '📥 Tải báo cáo' : '📥 Download Report'}</span>
                                <span className={styles.dropdownArrow}>{showExportMenu ? '▲' : '▼'}</span>
                            </button>

                            {showExportMenu && (
                                <div className={styles.exportMenuDropdown}>
                                    <div className={styles.exportMenuHeader}>{locale === 'vi' ? 'Chọn định dạng tải về:' : 'Select download format:'}</div>
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
                                            <div className={styles.itemTitle}>{locale === 'vi' ? 'Báo cáo Word (.docx)' : 'Word Report (.docx)'}</div>
                                            <div className={styles.itemDesc}>{locale === 'vi' ? 'Cấu trúc 5 phần A4 chuẩn CISO' : '5-part A4 structure CISO standard'}</div>
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
                                            <div className={styles.itemTitle}>{locale === 'vi' ? 'Bảng SoA (.xlsx)' : 'SoA Sheet (.xlsx)'}</div>
                                            <div className={styles.itemDesc}>{locale === 'vi' ? 'Tuyên bố áp dụng kiểm soát' : 'Statement of Applicability'}</div>
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
                                            <div className={styles.itemTitle}>{locale === 'vi' ? 'Sổ đăng ký rủi ro (.xlsx)' : 'Risk Register (.xlsx)'}</div>
                                            <div className={styles.itemDesc}>{locale === 'vi' ? 'Ma trận định lượng L × I' : 'L × I Quantitative Matrix'}</div>
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
                                            <div className={styles.itemTitle}>{locale === 'vi' ? 'Bản in báo cáo (.pdf)' : 'Printable Report (.pdf)'}</div>
                                            <div className={styles.itemDesc}>{locale === 'vi' ? 'Đóng dấu điện tử và in ấn' : 'Digitally stamped & print-ready'}</div>
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
                                            showToast(locale === 'vi' ? 'Đã tải thành công file JSON đánh giá' : 'Assessment JSON downloaded successfully', 'success')
                                        }}
                                    >
                                        <span className={styles.itemIcon}>💾</span>
                                        <div className={styles.itemContent}>
                                            <div className={styles.itemTitle}>{locale === 'vi' ? 'Dữ liệu thô (.json)' : 'Raw Data (.json)'}</div>
                                            <div className={styles.itemDesc}>{locale === 'vi' ? 'Trích xuất toàn bộ cấu trúc API' : 'Full API data structure export'}</div>
                                        </div>
                                        <span className={styles.formatPillJson}>JSON</span>
                                    </button>

                                    <button
                                        className={styles.exportMenuItem}
                                        onClick={() => {
                                            handleExportAuditTrace()
                                            setShowExportMenu(false)
                                        }}
                                        disabled={exportingType === 'trace'}
                                    >
                                        <span className={styles.itemIcon}>🛡️</span>
                                        <div className={styles.itemContent}>
                                            <div className={styles.itemTitle}>Audit Trace (.json)</div>
                                            <div className={styles.itemDesc}>{locale === 'vi' ? 'Nhật ký kiểm chứng SQLite & Runtime' : 'SQLite & Runtime audit trail log'}</div>
                                        </div>
                                        <span className={styles.formatPillTrace}>TRACE</span>
                                    </button>

                                    {exportError && (
                                        <div className={styles.exportErrorBanner} role="alert">
                                            <span>⚠️ {exportError}</span>
                                            <button className={styles.exportErrorClose} onClick={(e) => { e.stopPropagation(); setExportError(null); }}>✕</button>
                                        </div>
                                    )}
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
                                title={locale === 'vi' ? "Xem chu trình tư duy và đối soát bằng chứng của AI" : "View AI thought process and evidence validation"}
                            >
                                {locale === 'vi' ? '🔍 Luồng kiểm chứng (Audit Trace)' : '🔍 Audit Trace'}
                            </button>

                            <button
                                className={styles.miniActionBtnHighlight}
                                onClick={() => setShowProofModal(true)}
                                style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.18), rgba(6, 78, 59, 0.35))', borderColor: 'rgba(52, 211, 153, 0.4)', color: '#34d399' }}
                                title={locale === 'vi' ? "Chứng minh mô hình và script bóc tách chính xác 100% dữ liệu đầu vào (SHA-256, Fact Cards, Hotfixes, Đối soát chéo)" : "Cryptographic proof of 100% accurate data extraction"}
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
                                {locale === 'vi' ? '📋 Sao chép' : '📋 Copy'}
                            </button>

                            <button
                                className={styles.miniActionBtnSecondary}
                                onClick={() => {
                                    if (onStartNewAssessment) onStartNewAssessment()
                                    else {
                                        setActiveTab('form')
                                        setStep(1)
                                    }
                                }}
                            >
                                ← {locale === 'vi' ? 'Đánh giá mới' : 'New Assessment'}
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
                        {activeReport}
                    </ReactMarkdown>
                </div>
            </div>

            {/* xOffice Interactive Web Editor Modal */}
            <OfficeEditorModal
                isOpen={showOfficeModal}
                onClose={() => setShowOfficeModal(false)}
                fileType={officeFileType}
                assessmentId={result.id}
                initialReport={activeReport}
                jsonData={result.json_data || result.result?.json_data || {}}
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
