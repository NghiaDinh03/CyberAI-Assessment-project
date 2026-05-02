'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SystemStats from '@/components/SystemStats'
import Link from 'next/link'
import styles from './page.module.css'
import { useToast } from '@/components/Toast'
import { useTranslation } from '@/components/LanguageProvider'
import { SkeletonCard, SkeletonTable } from '@/components/Skeleton'
import { BarChart2, BookOpen, FlaskConical, Trash2, RefreshCw } from 'lucide-react'

function SvgGauge({ percent, size = 96, color = 'var(--accent-blue)' }) {
    const r = (size - 12) / 2
    const circ = 2 * Math.PI * r
    const dash = (Math.min(Math.max(percent, 0), 100) / 100) * circ
    return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="6" />
            <circle
                cx={size / 2} cy={size / 2} r={r}
                fill="none" stroke={color} strokeWidth="6"
                strokeDasharray={`${dash} ${circ}`}
                strokeLinecap="round"
                style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
        </svg>
    )
}

const WEIGHT_COLOR_STD = { critical: '#f87171', high: '#fbbf24', medium: '#4f8ef7', low: '#7d8fa3' }
const WEIGHT_LABEL_STD = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' }

// ── ISO 27001:2022 Annex A domains with control IDs ────────────────────────
const ANNEX_A_DOMAINS = [
    { id: 'A.5',  label: 'Org. Controls',     controls: ['A.5.1','A.5.2','A.5.3','A.5.4','A.5.5','A.5.6','A.5.7','A.5.8','A.5.9','A.5.10','A.5.11','A.5.12','A.5.13','A.5.14','A.5.15','A.5.16','A.5.17','A.5.18','A.5.19','A.5.20','A.5.21','A.5.22','A.5.23','A.5.24','A.5.25','A.5.26','A.5.27','A.5.28','A.5.29','A.5.30','A.5.31','A.5.32','A.5.33','A.5.34','A.5.35','A.5.36','A.5.37'] },
    { id: 'A.6',  label: 'People Controls',   controls: ['A.6.1','A.6.2','A.6.3','A.6.4','A.6.5','A.6.6','A.6.7','A.6.8'] },
    { id: 'A.7',  label: 'Physical Controls', controls: ['A.7.1','A.7.2','A.7.3','A.7.4','A.7.5','A.7.6','A.7.7','A.7.8','A.7.9','A.7.10','A.7.11','A.7.12','A.7.13','A.7.14'] },
    { id: 'A.8',  label: 'Tech. Controls',    controls: ['A.8.1','A.8.2','A.8.3','A.8.4','A.8.5','A.8.6','A.8.7','A.8.8','A.8.9','A.8.10','A.8.11','A.8.12','A.8.13','A.8.14','A.8.15','A.8.16','A.8.17','A.8.18','A.8.19','A.8.20','A.8.21','A.8.22','A.8.23','A.8.24','A.8.25','A.8.26','A.8.27','A.8.28','A.8.29','A.8.30','A.8.31','A.8.32','A.8.33','A.8.34'] },
]

function ComplianceHeatmap({ assessments, t, locale }) {
    // Guard: ensure assessments is always an array before calling .filter
    const list = Array.isArray(assessments) ? assessments : []
    if (list.length === 0) return null

    // Use the most recent completed assessment with control data
    const recent = list
        .filter(a => a.status === 'completed' && a.system_info?.compliance?.implemented_controls?.length > 0)
        .slice(0, 1)[0]

    const implemented = new Set(recent?.system_info?.compliance?.implemented_controls || [])
    const hasData = implemented.size > 0

    return (
        <div>
            <div className={styles.heatmapLegend}>
                {[
                    { color: '#34d399', label: t('analytics.heatmapCompliant') },
                    { color: '#fbbf24', label: t('analytics.heatmapPartial') },
                    { color: '#f87171', label: t('analytics.heatmapGap') },
                    { color: 'var(--bg-muted)', label: t('analytics.heatmapNotAssessed') },
                ].map(l => (
                    <span key={l.label} className={styles.heatmapLegendItem}>
                        <span className={styles.heatmapLegendDot} style={{ background: l.color }} />
                        {l.label}
                    </span>
                ))}
                {recent && (
                    <span className={styles.heatmapLegendOrg}>
                        {recent.org_name} · {new Date(recent.created_at).toLocaleDateString(locale === 'vi' ? 'vi-VN' : 'en-US')}
                    </span>
                )}
            </div>
            <div className={styles.heatmapGrid}>
                {ANNEX_A_DOMAINS.map(domain => {
                    const total = domain.controls.length
                    const done = hasData ? domain.controls.filter(c => implemented.has(c)).length : 0
                    const pct = hasData ? Math.round((done / total) * 100) : null
                    const cellColor = pct == null ? 'var(--bg-muted)' :
                        pct >= 80 ? 'rgba(52,211,153,0.22)' :
                        pct >= 50 ? 'rgba(251,191,36,0.22)' :
                                    'rgba(248,113,113,0.22)'
                    const borderColor = pct == null ? 'var(--border)' :
                        pct >= 80 ? 'rgba(52,211,153,0.4)' :
                        pct >= 50 ? 'rgba(251,191,36,0.4)' :
                                    'rgba(248,113,113,0.4)'
                    const textColor = pct == null ? 'var(--text-dim)' :
                        pct >= 80 ? '#34d399' :
                        pct >= 50 ? '#fbbf24' :
                                    '#f87171'
                    return (
                        <div
                            key={domain.id}
                            className={styles.heatmapCell}
                            style={{ background: cellColor, borderColor }}
                            title={pct != null ? `${domain.id} ${domain.label}: ${done}/${total} controls (${pct}%)` : `${domain.id} ${domain.label}: not assessed`}
                        >
                            <span className={styles.heatmapCellId}>{domain.id}</span>
                            <span className={styles.heatmapCellLabel}>{domain.label}</span>
                            <span className={styles.heatmapCellPct} style={{ color: textColor }}>
                                {pct != null ? `${pct}%` : '—'}
                            </span>
                            <span className={styles.heatmapCellSub}>
                                {pct != null ? `${done}/${total}` : `${total} ctrl`}
                            </span>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

export default function AnalyticsPage() {
    const { t, locale } = useTranslation()
    const { showToast } = useToast()
    const [activeMainTab, setActiveMainTab] = useState('dashboard')
    const [benchmarkCases, setBenchmarkCases] = useState(null)
    const [benchmarkRunning, setBenchmarkRunning] = useState(false)
    const [benchmarkResult, setBenchmarkResult] = useState(null)
    const [benchmarkMode, setBenchmarkMode] = useState('hybrid')
    const [benchmarkCompare, setBenchmarkCompare] = useState(false)
    const [services, setServices] = useState(null)
    const [aiStatus, setAiStatus] = useState(null)
    const [assessments, setAssessments] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedAssessment, setSelectedAssessment] = useState(null)
    const [modalLoading, setModalLoading] = useState(false)
    const [deleteWarning, setDeleteWarning] = useState(null)
    const [dontAskAgain, setDontAskAgain] = useState(false)
    const [chromaStats, setChromaStats] = useState(null)
    const [reindexing, setReindexing] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState(null)
    const [searching, setSearching] = useState(false)
    const [showFiles, setShowFiles] = useState(false)
    const [standards, setStandards] = useState({ builtin: [], custom: [] })
    const [stdLoading, setStdLoading] = useState(false)
    const [stdUploading, setStdUploading] = useState(false)
    const [stdUploadResult, setStdUploadResult] = useState(null)
    const [stdDragOver, setStdDragOver] = useState(false)
    const [selectedStandard, setSelectedStandard] = useState(null)
    const [stdDetailLoading, setStdDetailLoading] = useState(false)
    const [showSchemaGuide, setShowSchemaGuide] = useState(false)
    const router = useRouter()

    const fetchStandards = useCallback(async () => {
        try {
            setStdLoading(true)
            const res = await fetch('/api/standards')
            if (res.ok) {
                const data = await res.json()
                setStandards({ builtin: data.builtin || [], custom: data.custom || [] })
            }
        } catch (e) { console.error('Failed to fetch standards:', e) }
        finally { setStdLoading(false) }
    }, [])

    const handleStdUpload = async (file) => {
        if (!file) return
        setStdUploading(true)
        setStdUploadResult(null)
        const formData = new FormData()
        formData.append('file', file)
        try {
            const res = await fetch('/api/standards/upload', { method: 'POST', body: formData })
            const data = await res.json()
            if (res.ok && data.status === 'success') {
                setStdUploadResult({ success: true, data })
                fetchStandards()
            } else {
                setStdUploadResult({ success: false, errors: data.errors || [data.detail || 'Upload failed'] })
            }
        } catch (e) { setStdUploadResult({ success: false, errors: [`Network error: ${e.message}`] }) }
        finally { setStdUploading(false) }
    }

    const handleStdDelete = async (standardId) => {
        if (!confirm(`Confirm delete standard "${standardId}"?`)) return
        try {
            const res = await fetch(`/api/standards/${standardId}`, { method: 'DELETE' })
            if (res.ok) { fetchStandards(); if (selectedStandard?.id === standardId) setSelectedStandard(null) }
        } catch (e) { console.error('Delete failed:', e) }
    }

    const handleStdReindex = async (standardId) => {
        try {
            const res = await fetch(`/api/standards/${standardId}/index`, { method: 'POST' })
            const data = await res.json()
            if (data.status === 'ok') {
                showToast(`Indexed ${data.chunks_indexed} chunks`, 'success')
            } else {
                showToast(data.message || 'Indexing failed', 'error')
            }
        } catch (e) { showToast(e.message, 'error') }
    }

    const handleStdDetail = async (standardId) => {
        setStdDetailLoading(true)
        try {
            const res = await fetch(`/api/standards/${standardId}`)
            if (res.ok) { const data = await res.json(); setSelectedStandard(data) }
        } catch (e) { console.error(e) }
        finally { setStdDetailLoading(false) }
    }

    const downloadSample = async () => {
        try {
            const res = await fetch('/api/standards/sample')
            const data = await res.json()
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a'); a.href = url; a.download = 'sample_standard.json'; a.click()
            URL.revokeObjectURL(url)
        } catch (e) { console.error(e) }
    }

    useEffect(() => {
        if (activeMainTab === 'standards' && standards.builtin.length === 0) {
            fetchStandards()
        }
    }, [activeMainTab, fetchStandards, standards.builtin.length])

    const openDetail = async (id) => {
        setModalLoading(true)
        setSelectedAssessment({ id, loading: true })
        try {
            const res = await fetch(`/api/iso27001/assessments/${id}`)
            if (res.ok) {
                setSelectedAssessment(await res.json())
            } else {
                setSelectedAssessment({ id, error: 'Data not found' })
            }
        } catch {
            setSelectedAssessment({ id, error: 'Failed to load details' })
        } finally {
            setModalLoading(false)
        }
    }

    const handleReuse = () => {
        if (selectedAssessment && selectedAssessment.system_info) {
            localStorage.setItem('reuse_iso_form', JSON.stringify(selectedAssessment.system_info))
            router.push('/form-iso')
        }
    }

    const checkDeleteWarning = (id, e) => {
        e.stopPropagation()
        const suppressUntil = localStorage.getItem('skip_delete_warning_iso')
        if (suppressUntil && Date.now() < parseInt(suppressUntil)) {
            executeDelete(id)
        } else {
            setDeleteWarning(id)
        }
    }

    const executeDelete = async (id) => {
        try {
            const res = await fetch(`/api/iso27001/assessments/${id}`, { method: 'DELETE' })
            if (res.ok) {
                setAssessments(prev => prev.filter(a => a.id !== id))
                if (selectedAssessment?.id === id) setSelectedAssessment(null)
            }
        } catch (e) {
            console.error('Delete error:', e)
        } finally {
            setDeleteWarning(null)
        }
    }

    const confirmDelete = () => {
        if (dontAskAgain) {
            localStorage.setItem('skip_delete_warning_iso', Date.now() + 24 * 60 * 60 * 1000)
        }
        executeDelete(deleteWarning)
    }

    useEffect(() => {
        async function fetchData() {
            try {
                const res = await fetch('/api/health')
                const backendReady = res.ok
                let localaiReady = false
                try {
                    const sysRes = await fetch('/api/system/stats')
                    if (sysRes.ok) localaiReady = true
                } catch { }
                try {
                    const aiRes = await fetch('/api/system/ai-status')
                    if (aiRes.ok) setAiStatus(await aiRes.json())
                } catch { }
                try {
                    const assessRes = await fetch('/api/iso27001/assessments?page_size=50')
                    if (assessRes.ok) {
                        const assessData = await assessRes.json()
                        setAssessments(Array.isArray(assessData)
                            ? assessData
                            : Array.isArray(assessData?.items)
                                ? assessData.items
                                : [])
                    }
                } catch { }
                try {
                    const chromaRes = await fetch('/api/iso27001/chromadb/stats')
                    if (chromaRes.ok) setChromaStats(await chromaRes.json())
                } catch { }
                setServices({
                    backend: { status: backendReady ? 'Running' : 'Offline', ready: backendReady },
                    localai: { status: localaiReady ? 'Ready' : 'Offline', ready: localaiReady },
                    models: []
                })
            } catch {
                setServices({
                    backend: { status: 'Offline', ready: false },
                    localai: { status: 'Offline', ready: false },
                    models: []
                })
            } finally {
                setLoading(false)
            }
        }
        fetchData()
        // Poll every 60s instead of 15s — analytics page hits 4 endpoints per cycle,
        // backend has 30s health cache, so faster polling was pure waste.
        const interval = setInterval(fetchData, 60000)
        return () => clearInterval(interval)
    }, [])

    const getPctColor = (pct) => pct == null ? '' :
        pct >= 80 ? 'var(--accent-green)' :
        pct >= 50 ? 'var(--accent-blue)' :
        pct >= 25 ? 'var(--accent-amber)' :
        'var(--accent-red)'

    const ollamaStatus = aiStatus?.ollama?.status === 'healthy'
    const gemmaInfo = aiStatus?.ollama?.gemma3n_e4b
    const gemmaSize = gemmaInfo?.size ? `${(gemmaInfo.size / (1024 ** 3)).toFixed(1)} GB` : '—'

    // Models default to "Ready" when LocalAI engine is available (files on disk)
    const localaiUp = services?.localai?.ready
    const ollamaReady = ollamaStatus || (aiStatus && !aiStatus.ollama?.status?.startsWith?.('unreachable'))

    const SERVICE_ROWS = [
        { name: 'FastAPI Backend', detail: 'Core API Service · Port 8000', ready: services?.backend?.ready, status: services?.backend?.status },
        { name: 'LocalAI Engine', detail: 'Model Server · Port 8080 · CPU Mode', ready: localaiUp, status: services?.localai?.status },
        { name: 'ChromaDB', detail: 'Vector Database · RAG · cosine similarity', ready: services?.backend?.ready, status: services?.backend?.status },
        { name: 'Llama 3.1 8B', detail: 'LLM General · Q4_K_M · 4.9 GB', ready: localaiUp, status: localaiUp ? 'Ready' : undefined, loading: !services },
        { name: 'SecurityLLM 7B', detail: 'LLM ISO Assessor · Q4_K_M · 4.4 GB', ready: localaiUp, status: localaiUp ? 'Ready' : undefined, loading: !services },
        { name: 'Ollama Engine', detail: `Gemma 3n E4B · ${gemmaSize} · Port 11434`, ready: ollamaReady, status: ollamaReady ? 'Running' : (aiStatus ? 'Offline' : undefined), loading: !aiStatus },
    ]

    return (
        <div className="page-container">
            <div className={styles.header}>
                <h1 className={styles.title}>{t('analytics.pageTitle')}</h1>
                <p className={styles.subtitle}>{t('analytics.pageSubtitle')}</p>
            </div>

            <div className={styles.mainTabNav}>
                <button
                    className={`${styles.mainTab} ${activeMainTab === 'dashboard' ? styles.mainTabActive : ''}`}
                    onClick={() => setActiveMainTab('dashboard')}
                >
                    <BarChart2 size={14} style={{ marginRight: '5px', verticalAlign: 'middle' }} />{t('analytics.tabDashboard')}
                </button>
                <button
                    className={`${styles.mainTab} ${activeMainTab === 'standards' ? styles.mainTabActive : ''}`}
                    onClick={() => setActiveMainTab('standards')}
                >
                    <BookOpen size={14} style={{ marginRight: '5px', verticalAlign: 'middle' }} />{t('analytics.tabStandards')}
                </button>
                <button
                    className={`${styles.mainTab} ${activeMainTab === 'benchmark' ? styles.mainTabActive : ''}`}
                    onClick={async () => {
                        setActiveMainTab('benchmark')
                        if (!benchmarkCases) {
                            const res = await fetch('/api/benchmark/test-cases')
                            if (res.ok) setBenchmarkCases(await res.json())
                        }
                    }}
                >
                    <FlaskConical size={14} style={{ marginRight: '5px', verticalAlign: 'middle' }} />{t('analytics.tabBenchmark')}
                </button>
                <span className={styles.mainTabSpacer} />
                <Link href="/form-iso" className={styles.mainTabLink}>{t('analytics.backToAssessment')}</Link>
            </div>

            {activeMainTab === 'standards' && (
                <div>
                    <div className={styles.stdSection}>
                        <div className={styles.stdSectionHeader}>
                            <h2 className={styles.stdSectionTitle}>{t('analytics.uploadNewStandard')}</h2>
                            <div className={styles.stdHeaderActions}>
                                <button className={styles.stdBtnOutline} onClick={downloadSample}>{t('analytics.downloadSampleJson')}</button>
                                <button className={styles.stdBtnOutline} onClick={() => setShowSchemaGuide(!showSchemaGuide)}>
                                    {showSchemaGuide ? t('analytics.closeGuide') : t('analytics.formatGuide')}
                                </button>
                            </div>
                        </div>

                        {showSchemaGuide && (
                            <div className={styles.stdSchemaBox}>
                                <pre className={styles.stdSchemaCode}>{`{
  "id": "my_standard_id",
  "name": "Standard Name",
  "version": "1.0",
  "description": "Description",
  "controls": [
    {
      "category": "1. Group Name",
      "controls": [
        { "id": "CTL.01", "label": "Control name", "weight": "critical" }
      ]
    }
  ]
}`}</pre>
                                <div className={styles.stdWeightNote}>
                                    <strong>Weights:</strong>
                                    {[['critical', '#f87171', '4pts'], ['high', '#fbbf24', '3pts'], ['medium', '#4f8ef7', '2pts'], ['low', '#7d8fa3', '1pt']].map(([w, c, p]) => (
                                        <span key={w} style={{ borderColor: c, color: c, border: `1px solid ${c}`, borderRadius: '4px', padding: '1px 7px', fontSize: '0.72rem', fontWeight: 700 }}>{w} = {p}</span>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div
                            className={`${styles.stdDropZone} ${stdDragOver ? styles.stdDropZoneActive : ''} ${stdUploading ? styles.stdDropZoneUploading : ''}`}
                            onDragOver={(e) => { e.preventDefault(); setStdDragOver(true) }}
                            onDragLeave={() => setStdDragOver(false)}
                            onDrop={(e) => { e.preventDefault(); setStdDragOver(false); const f = e.dataTransfer?.files?.[0]; if (f) handleStdUpload(f) }}
                        >
                            {stdUploading ? (
                                <div className={styles.stdDropContent}>
                                    <span className={styles.stdDropSpinner} />
                                    <p>{t('analytics.uploadingProcessing')}</p>
                                </div>
                            ) : (
                                <div className={styles.stdDropContent}>
                                    <p className={styles.stdDropText}>{t('analytics.dropFileHere')}</p>
                                    <label className={styles.stdBtnPrimary}>
                                        {t('analytics.selectFile')}
                                        <input type="file" accept=".json,.yaml,.yml" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleStdUpload(f) }} hidden />
                                    </label>
                                    <p className={styles.stdDropHint}>{t('analytics.fileTypes')}</p>
                                </div>
                            )}
                        </div>

                        {stdUploadResult && (
                            <div className={`${styles.stdResultBox} ${stdUploadResult.success ? styles.stdResultSuccess : styles.stdResultError}`}>
                                <div className={styles.stdResultHeader}>{stdUploadResult.success ? t('analytics.uploadSuccessful') : t('analytics.uploadFailed')}</div>
                                {stdUploadResult.success && stdUploadResult.data?.standard && (
                                    <div className={styles.stdResultMeta}>
                                        <span>ID: <strong>{stdUploadResult.data.standard.id}</strong></span>
                                        <span>{stdUploadResult.data.standard.total_controls} controls</span>
                                        {stdUploadResult.data.chromadb_index?.chunks_indexed && <span>ChromaDB: {stdUploadResult.data.chromadb_index.chunks_indexed} chunks</span>}
                                    </div>
                                )}
                                {stdUploadResult.errors?.length > 0 && (
                                    <ul className={styles.stdResultErrors}>
                                        {stdUploadResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                                    </ul>
                                )}
                            </div>
                        )}
                    </div>

                    <div className={styles.stdSection}>
                        <div className={styles.stdSectionHeader}>
                            <h2 className={styles.stdSectionTitle}><BookOpen size={15} style={{ marginRight: '6px', verticalAlign: 'middle' }} />{t('analytics.standardsLibrary')}</h2>
                            <button className={styles.stdBtnOutline} onClick={fetchStandards} disabled={stdLoading}><RefreshCw size={13} style={{ marginRight: '4px', verticalAlign: 'middle' }} />{t('common.refresh')}</button>
                        </div>

                        {stdLoading ? (
                            <SkeletonTable rows={5} cols={3} />
                        ) : (
                            <>
                                <p className={styles.stdGroupLabel}>{t('analytics.builtInStandards')}</p>
                                <div className={styles.stdGrid}>
                                    {standards.builtin.map(std => (
                                        <div key={std.id} className={styles.stdCard}>
                                            <div className={styles.stdCardHead}>
                                                <span className={styles.stdCardBadge}>Built-in</span>
                                                <span className={styles.stdCardVersion}>{std.version}</span>
                                            </div>
                                            <h4 className={styles.stdCardName}>{std.name}</h4>
                                            <p className={styles.stdCardDesc}>{std.description}</p>
                                            <div className={styles.stdCardStats}>
                                                <span>{std.total_controls} controls</span>
                                                <span>{std.categories} categories</span>
                                            </div>
                                            <div className={styles.stdCardActions}>
                                                <Link href="/form-iso" className={styles.stdBtnSmall}>{t('analytics.useInAssessment')}</Link>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                <p className={styles.stdGroupLabel} style={{ marginTop: '1.25rem' }}>{t('analytics.customStandards')}</p>
                                {standards.custom.length === 0 ? (
                                    <div className={styles.stdEmpty}>
                                        <p>{t('analytics.noCustomStandards')}</p>
                                        <p className={styles.stdEmptyHint}>{t('analytics.noCustomStandardsHint')}</p>
                                    </div>
                                ) : (
                                    <div className={styles.stdGrid}>
                                        {standards.custom.map(std => (
                                            <div key={std.id} className={`${styles.stdCard} ${styles.stdCardCustom}`}>
                                                <div className={styles.stdCardHead}>
                                                    <span className={`${styles.stdCardBadge} ${styles.stdCardBadgeCustom}`}>Custom</span>
                                                    <span className={styles.stdCardVersion}>{std.version}</span>
                                                </div>
                                                <h4 className={styles.stdCardName}>{std.name}</h4>
                                                <p className={styles.stdCardDesc}>{std.description || 'No description'}</p>
                                                <div className={styles.stdCardStats}>
                                                    <span>{std.total_controls} controls</span>
                                                    <span>Max: {std.max_weighted_score}pts</span>
                                                </div>
                                                {std.weight_breakdown && (
                                                    <div className={styles.stdWeightTags}>
                                                        {Object.entries(std.weight_breakdown).map(([w, cnt]) => cnt > 0 && (
                                                            <span key={w} className={styles.stdWeightTag} style={{ borderColor: WEIGHT_COLOR_STD[w], color: WEIGHT_COLOR_STD[w] }}>
                                                                {WEIGHT_LABEL_STD[w]}: {cnt}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}
                                                <div className={styles.stdCardActions}>
                                                    <button className={styles.stdBtnSmall} onClick={() => handleStdDetail(std.id)}>{t('analytics.detail')}</button>
                                                    <button className={styles.stdBtnSmall} onClick={() => handleStdReindex(std.id)}><RefreshCw size={11} style={{ marginRight: '3px', verticalAlign: 'middle' }} />{t('analytics.reindexBtn')}</button>
                                                    <button className={`${styles.stdBtnSmall} ${styles.stdBtnDanger}`} onClick={() => handleStdDelete(std.id)}><Trash2 size={11} style={{ marginRight: '3px', verticalAlign: 'middle' }} />{t('common.delete')}</button>
                                                </div>
                                                <div className={styles.stdCardDate}>
                                                    {std.created_at ? new Date(std.created_at).toLocaleDateString(locale === 'vi' ? 'vi-VN' : 'en-US') : '—'}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        )}
                    </div>

                    {selectedStandard && selectedStandard.controls && (
                        <>
                            <div className={styles.modalOverlay} onClick={() => setSelectedStandard(null)} />
                            <div className={styles.stdDetailPanel}>
                                <div className={styles.modalHeader}>
                                    <div>
                                        <h3 className={styles.modalTitle}>{selectedStandard.name}</h3>
                                        <p className={styles.modalSubtitle}>{selectedStandard.id} · v{selectedStandard.version} · {selectedStandard.total_controls} controls</p>
                                    </div>
                                    <button className={styles.closeBtn} onClick={() => setSelectedStandard(null)}>✕</button>
                                </div>
                                <div className={styles.modalBody} style={{ overflowY: 'auto', flex: 1 }}>
                                    {stdDetailLoading ? <div className={styles.loading}>Loading...</div> : (
                                        selectedStandard.controls.map((cat, ci) => (
                                            <div key={ci} className={styles.stdDetailCat}>
                                                <h4 className={styles.stdDetailCatTitle}>
                                                    {cat.category}
                                                    <span className={styles.stdDetailCatCount}>{cat.controls.length} controls</span>
                                                </h4>
                                                {cat.controls.map(ctrl => (
                                                    <div key={ctrl.id} className={styles.stdDetailCtrl}>
                                                        <span className={styles.stdDetailCtrlId}>{ctrl.id}</span>
                                                        <span className={styles.stdDetailCtrlLabel}>{ctrl.label}</span>
                                                        <span className={styles.stdDetailCtrlWeight} style={{ borderColor: WEIGHT_COLOR_STD[ctrl.weight], color: WEIGHT_COLOR_STD[ctrl.weight] }}>{ctrl.weight}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        ))
                                    )}
                                </div>
                                <div className={styles.modalFooter}>
                                    <Link href="/form-iso" className={styles.btnPrimary}>{t('analytics.useInAssessment')}</Link>
                                    <button className={styles.btnSecondary} onClick={() => setSelectedStandard(null)}>{t('common.close')}</button>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            )}

            {activeMainTab === 'dashboard' && (
                <div>
                    <section className={styles.section}>
                        <p className="section-title">{t('analytics.systemResources')}</p>
                        <SystemStats />
                    </section>

                    <section className={styles.section}>
                        <p className="section-title">{t('analytics.serviceStatus')}</p>
                        {loading ? (
                            <div className="grid-2">
                                {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
                            </div>
                        ) : (
                            <div className="grid-2">
                                {SERVICE_ROWS.map((svc, i) => (
                                    <div key={i} className={styles.serviceCard}>
                                        <div className={styles.serviceHeader}>
                                            <div>
                                                <div className={styles.serviceName}>{svc.name}</div>
                                                <div className={styles.serviceDetail}>{svc.detail}</div>
                                            </div>
                                            <span className={`status-badge ${svc.ready ? 'status-online' : svc.loading ? 'status-loading' : 'status-offline'}`}>
                                                {svc.status}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className={styles.section}>
                        <p className="section-title">{t('analytics.assessmentHistory')}</p>
                        <div className={styles.tableContainer}>
                            <table className={styles.table}>
                                <thead>
                                    <tr>
                                        <th>{t('analytics.thTime')}</th>
                                        <th>{t('analytics.thOrganization')}</th>
                                        <th>{t('analytics.thCompliance')}</th>
                                        <th>{t('analytics.thStatus')}</th>
                                        <th>{t('analytics.thId')}</th>
                                        <th style={{ textAlign: 'right' }}>{t('analytics.thActions')}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {assessments.length > 0 ? assessments.map(a => {
                                        const pct = a.compliance_percent ?? null
                                        const pctColor = getPctColor(pct)
                                        return (
                                            <tr key={a.id} onClick={() => openDetail(a.id)} className={styles.tableRowRef}>
                                                <td>{new Date(a.created_at).toLocaleString(locale === 'vi' ? 'vi-VN' : 'en-US')}</td>
                                                <td><strong>{a.org_name}</strong></td>
                                                <td>
                                                    {pct != null ? (
                                                        <span className={styles.pctBadge} style={{ color: pctColor, borderColor: pctColor }}>{pct}%</span>
                                                    ) : (
                                                        <span className={styles.pctEmpty}>—</span>
                                                    )}
                                                </td>
                                                <td>
                                                    <span className={`status-badge ${a.status === 'completed' ? 'status-online' : a.status === 'processing' ? 'status-loading' : 'status-offline'}`}>
                                                        {a.status.toUpperCase()}
                                                    </span>
                                                </td>
                                                <td><code className={styles.codeId}>{a.id.split('-')[0]}</code></td>
                                                <td style={{ textAlign: 'right' }}>
                                                    <button className={styles.deleteBtn} onClick={(e) => checkDeleteWarning(a.id, e)} title="Delete assessment">
                                                        <Trash2 size={13} />
                                                    </button>
                                                </td>
                                            </tr>
                                        )
                                    }) : (
                                        <tr>
                                            <td colSpan="6" className={styles.tableEmpty}>
                                                <div className={styles.emptyState}>
                                                    <span className={styles.emptyStateIcon}>📋</span>
                                                    <p className={styles.emptyStateText}>{t('analytics.noAssessments')}</p>
                                                    <p className={styles.emptyStateHint}>{t('analytics.noAssessmentsHint')}</p>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <section className={styles.section}>
                        <p className="section-title">{t('analytics.complianceHeatmap')}</p>
                        <ComplianceHeatmap assessments={assessments} t={t} locale={locale} />
                    </section>

                    <section className={styles.section}>
                        <p className="section-title">{t('analytics.chromadbTitle')}</p>
                        <div className={styles.chromaPanel}>
                            <div className={styles.chromaHeader}>
                                <div className={styles.chromaHeaderLeft}>
                                    <div className={styles.chromaGrid}>
                                        {[
                                            { val: chromaStats?.total_chunks ?? '--', label: t('analytics.chunks') },
                                            { val: chromaStats?.total_files ?? '--', label: t('analytics.files') },
                                            { val: chromaStats?.metric ?? '--', label: t('analytics.metric') },
                                        ].map(s => (
                                            <div key={s.label} className={styles.chromaStat}>
                                                <span className={styles.chromaStatValue}>{s.val}</span>
                                                <span className={styles.chromaStatLabel}>{s.label}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className={styles.chromaHeaderRight}>
                                    <div className={styles.searchBox}>
                                        <input
                                            type="text"
                                            placeholder={t('analytics.searchDocuments')}
                                            value={searchQuery}
                                            onChange={e => setSearchQuery(e.target.value)}
                                            className={styles.searchInput}
                                            onKeyDown={async (e) => {
                                                if (e.key === 'Enter' && searchQuery.trim()) {
                                                    setSearching(true)
                                                    try {
                                                        const res = await fetch('/api/iso27001/chromadb/search', {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({ query: searchQuery, top_k: 3 })
                                                        })
                                                        if (res.ok) setSearchResults(await res.json())
                                                    } catch { } finally { setSearching(false) }
                                                }
                                            }}
                                        />
                                        <button
                                            className={styles.btnSearch}
                                            disabled={searching || !searchQuery.trim()}
                                            onClick={async () => {
                                                if (!searchQuery.trim()) return
                                                setSearching(true)
                                                try {
                                                    const res = await fetch('/api/iso27001/chromadb/search', {
                                                        method: 'POST',
                                                        headers: { 'Content-Type': 'application/json' },
                                                        body: JSON.stringify({ query: searchQuery, top_k: 3 })
                                                    })
                                                    if (res.ok) setSearchResults(await res.json())
                                                } catch { } finally { setSearching(false) }
                                            }}
                                        >{searching ? '...' : t('common.search')}</button>
                                    </div>
                                    {searchResults?.results?.length > 0 && (
                                        <div className={styles.searchResultsPanel}>
                                            {searchResults.results.map((r, i) => (
                                                <div key={i} className={styles.searchResultItem}>
                                                    <div className={styles.searchResultHeader}>
                                                        <span className={styles.searchResultSource}>{r.source}</span>
                                                        <span className={styles.searchResultScore}>{(r.score * 100).toFixed(0)}%</span>
                                                    </div>
                                                    <p className={styles.searchResultText}>{r.text?.substring(0, 200)}...</p>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    <div className={styles.chromaStatusRow}>
                                        <span className={`${styles.chromaStatusDot} ${chromaStats?.status === 'ok' ? styles.dotOk : styles.dotErr}`} />
                                        <span className={styles.chromaStatusText}>{chromaStats?.status === 'ok' ? t('analytics.databaseReady') : t('analytics.checking')}</span>
                                        <button
                                            className={styles.btnReindex}
                                            disabled={reindexing}
                                            onClick={async () => {
                                                setReindexing(true)
                                                try {
                                                    const res = await fetch('/api/iso27001/reindex', { method: 'POST' })
                                                    if (res.ok) {
                                                        const data = await res.json()
                                                        showToast(`Reindex successful: ${data.files} files → ${data.chunks} chunks`, 'success')
                                                        const r2 = await fetch('/api/iso27001/chromadb/stats')
                                                        if (r2.ok) setChromaStats(await r2.json())
                                                    }
                                                } catch (e) {
                                                    showToast('Error: ' + e.message, 'error')
                                                } finally { setReindexing(false) }
                                            }}
                                        >{reindexing ? t('analytics.reindexing') : <><RefreshCw size={13} style={{ marginRight: '4px', verticalAlign: 'middle' }} />{t('analytics.reindex')}</>}</button>
                                    </div>
                                </div>
                            </div>

                            {chromaStats?.files?.length > 0 && (
                                <div className={styles.chromaFiles}>
                                    <div className={styles.fileToggle} onClick={() => setShowFiles(!showFiles)}>
                                        <span>{showFiles ? '▼' : '▶'} {t('analytics.documents')} ({chromaStats.files.length} {t('analytics.files').toLowerCase()})</span>
                                        <span className={styles.fileTotalSize}>
                                            {(chromaStats.files.reduce((s, f) => s + f.size_bytes, 0) / 1024).toFixed(1)} KB
                                        </span>
                                    </div>
                                    {showFiles && (
                                        <div className={styles.fileList}>
                                            {chromaStats.files.map((f, i) => (
                                                <div key={i} className={styles.fileItem}>
                                                    <span className={styles.fileName}>{f.name}</span>
                                                    <span className={styles.fileSize}>{(f.size_bytes / 1024).toFixed(1)} KB</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </section>

                    {selectedAssessment && (
                        <div className={styles.modalOverlay} onClick={() => setSelectedAssessment(null)}>
                            <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
                                <div className={styles.modalHeader}>
                                    <div>
                                        <h3 className={styles.modalTitle}>{t('analytics.assessmentDetail')}</h3>
                                        <p className={styles.modalSubtitle}>
                                            ID: <code className={styles.codeId}>{selectedAssessment.id?.split('-')[0]}</code>
                                            {selectedAssessment.created_at && <> · {new Date(selectedAssessment.created_at).toLocaleString(locale === 'vi' ? 'vi-VN' : 'en-US')}</>}
                                        </p>
                                    </div>
                                    <button className={styles.closeBtn} onClick={() => setSelectedAssessment(null)}>✕</button>
                                </div>
                                <div className={styles.modalBody}>
                                    {modalLoading || selectedAssessment.loading ? (
                                        <div className={styles.loading}>
                                        <div className={styles.loadingSpinner} />
                                        <span>{t('analytics.loadingReport')}</span>
                                        </div>
                                    ) : selectedAssessment.error ? (
                                        <div className={styles.statusError}>{selectedAssessment.error}</div>
                                    ) : (
                                        <>
                                            {(() => {
                                                const pct = selectedAssessment.compliance_percent ?? null
                                                const org = selectedAssessment.system_info?.organization
                                                const infra = selectedAssessment.system_info?.infrastructure
                                                const comp = selectedAssessment.system_info?.compliance
                                                const stdId = selectedAssessment.standard
                                                const stdName = stdId === 'tcvn11930' ? 'TCVN 11930:2017' : 'ISO 27001:2022'
                                                const gaugeColor = getPctColor(pct) || 'var(--accent-blue)'
                                                const badgeClass = pct == null ? styles.modalBadgeNeutral :
                                                    pct >= 80 ? styles.modalBadgeFull :
                                                    pct >= 50 ? styles.modalBadgeMostly :
                                                    pct >= 25 ? styles.modalBadgePartial :
                                                    styles.modalBadgeLow
                                                const badgeLabel = pct == null ? t('analytics.modalProcessing') :
                                                    pct >= 80 ? t('analytics.modalCompliant') :
                                                    pct >= 50 ? t('analytics.modalMostlyCompliant') :
                                                    pct >= 25 ? t('analytics.modalPartiallyCompliant') :
                                                    t('analytics.modalNonCompliant')
                                                return (
                                                    <div className={styles.modalScoreHero}>
                                                        <div className={styles.modalGaugeWrap}>
                                                            {pct != null ? (
                                                                <>
                                                                    <SvgGauge percent={pct} size={96} color={gaugeColor} />
                                                                    <div className={styles.modalGaugeOverlay}>
                                                                        <span className={styles.modalGaugePct} style={{ color: gaugeColor }}>{pct}%</span>
                                                                        <span className={styles.modalGaugeLabel}>{t('analytics.complianceLabel')}</span>
                                                                    </div>
                                                                </>
                                                            ) : (
                                                                <div className={styles.modalGaugePlaceholder}>—</div>
                                                            )}
                                                        </div>
                                                        <div className={styles.modalScoreInfo}>
                                                            <div className={styles.modalOrgName}>{org?.name || t('analytics.organizationLabel')}</div>
                                                            <div className={styles.modalStdName}>{stdName}</div>
                                                            <span className={`${styles.modalBadge} ${badgeClass}`}>{badgeLabel}</span>
                                                            <div className={styles.modalMetaRow}>
                                                                {org?.employees ? <span>{t('assessment.preSubmitEmployees', { count: org.employees })}</span> : null}
                                                                {infra?.servers ? <span>{t('assessment.preSubmitServers', { count: infra.servers })}</span> : null}
                                                                {comp?.iso_status ? <span>{comp.iso_status}</span> : null}
                                                            </div>
                                                        </div>
                                                    </div>
                                                )
                                            })()}

                                            <div className={styles.modalActionBar}>
                                                <button className={styles.modalActionBtn} onClick={() => {
                                                    const text = selectedAssessment.result?.report || ''
                                                    navigator.clipboard?.writeText(text).catch(() => { })
                                                }}>{t('analytics.copyReportBtn')}</button>
                                                <button className={styles.modalActionBtn} onClick={() => {
                                                    const pct = selectedAssessment.compliance_percent ?? null
                                                    const orgName = selectedAssessment.system_info?.organization?.name || 'Organization'
                                                    const stdId = selectedAssessment.standard
                                                    const stdName = stdId === 'tcvn11930' ? 'TCVN 11930:2017' : 'ISO 27001:2022'
                                                    const gaugeColor = getPctColor(pct) || '#4f8ef7'
                                                    const reportHtml = `<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8">
<title>Assessment Report - ${orgName}</title>
<style>
  body{font-family:'Segoe UI',Arial,sans-serif;max-width:860px;margin:40px auto;padding:0 24px;color:#1e293b;line-height:1.7;font-size:14px}
  h1{font-size:20px;font-weight:800;border-bottom:2px solid #3b82f6;padding-bottom:8px}
  h2{font-size:15px;font-weight:700;color:#3b82f6;margin-top:24px;border-left:3px solid #3b82f6;padding-left:8px}
  h3{font-size:14px;font-weight:600;color:#475569;margin-top:16px}
  .hero{display:flex;align-items:center;gap:20px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;margin:16px 0}
  .pct{font-size:36px;font-weight:900;color:${gaugeColor};min-width:90px;text-align:center}
  .meta strong{display:block;font-size:16px}.meta span{color:#64748b;font-size:13px}
  table{width:100%;border-collapse:collapse;margin:8px 0}th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #e2e8f0;font-size:13px}th{background:#f1f5f9;font-weight:600}
  ul{padding-left:20px}li{margin-bottom:4px}strong{color:#1e293b}
  blockquote{border-left:3px solid #3b82f6;margin:8px 0;padding:6px 12px;background:#eff6ff;border-radius:0 8px 8px 0;color:#475569}
  hr{border:none;border-top:1px solid #e2e8f0;margin:16px 0}code{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:4px;padding:1px 6px;font-size:12px}
  @media print{.no-print{display:none!important}}
</style></head><body>
<div class="no-print" style="background:#eff6ff;border:1px solid #3b82f6;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:13px;color:#1d4ed8;">
  <strong>Save as PDF:</strong> press Ctrl+P → select "Save as PDF".
  <button onclick="window.print()" style="float:right;padding:6px 14px;background:#3b82f6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;">Print / Save PDF</button>
</div>
<div class="hero">
  <div class="pct">${pct != null ? pct + '%' : '—'}</div>
  <div class="meta"><strong>${orgName}</strong><span>${stdName}</span></div>
</div>
<pre style="white-space:pre-wrap;font-family:inherit;font-size:13px;line-height:1.7;margin:0">${(selectedAssessment.result?.report || 'No report available.').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</pre>
</body></html>`
                                                    const w = window.open('', '_blank')
                                                    if (w) { w.document.write(reportHtml); w.document.close() }
                                                }}>{t('analytics.exportPdf')}</button>
                                                <button className={styles.modalActionBtnSecondary} onClick={handleReuse}>{t('analytics.reuseForm')}</button>
                                            </div>

                                            {selectedAssessment.status === 'failed' && (
                                                <div className={styles.failedNote}>
                                                    {t('analytics.failedNote')}
                                                </div>
                                            )}
                                            <div className={styles.md}>
                                                <ReactMarkdown
                                                    remarkPlugins={[remarkGfm]}
                                                >
                                                    {selectedAssessment.result?.report || '*No detailed report for this assessment.*'}
                                                </ReactMarkdown>
                                            </div>
                                        </>
                                    )}
                                </div>
                                <div className={styles.modalFooter}>
                                    <button className={styles.btnSecondary} onClick={() => setSelectedAssessment(null)}>{t('common.close')}</button>
                                    <button className={styles.btnPrimary} onClick={handleReuse}>{t('analytics.reuseThisForm')}</button>
                                </div>
                            </div>
                        </div>
                    )}

                    {deleteWarning && (
                        <div className={styles.modalOverlay} onClick={() => setDeleteWarning(null)}>
                            <div className={`${styles.modalContent} ${styles.modalSmall}`} onClick={e => e.stopPropagation()}>
                                <div className={styles.modalHeader}>
                                    <h3 className={`${styles.modalTitle} ${styles.modalTitleDanger}`}>{t('analytics.confirmDelete')}</h3>
                                    <button className={styles.closeBtn} onClick={() => setDeleteWarning(null)}>✕</button>
                                </div>
                                <div className={styles.modalBody}>
                                    <p className={styles.deleteWarningText}>
                                        {t('analytics.deleteWarning')}
                                    </p>
                                    <label className={styles.checkboxLabel}>
                                        <input
                                            type="checkbox"
                                            checked={dontAskAgain}
                                            onChange={(e) => setDontAskAgain(e.target.checked)}
                                        />
                                        <span>{t('analytics.dontAskAgain')}</span>
                                    </label>
                                </div>
                                <div className={styles.modalFooter}>
                                    <button className={styles.btnSecondary} onClick={() => setDeleteWarning(null)}>{t('common.cancel')}</button>
                                    <button className={styles.btnDanger} onClick={confirmDelete}>{t('analytics.deletePermanently')}</button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {activeMainTab === 'benchmark' && (
                <div className={styles.benchmarkWrap}>
                    <div className={styles.benchmarkHeader}>
                        <div>
                            <h2 className={styles.sectionTitle}>{t('analytics.benchmarkTitle')}</h2>
                            <p className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('analytics.benchmarkDesc') }} />
                        </div>
                    </div>

                    <div className={styles.benchmarkGuideRow}>
                        {[
                            { label: 'Complete sections', max: 5, desc: '5 required sections' },
                            { label: 'Risk coverage', max: 3, desc: 'Accurate control IDs' },
                            { label: 'Severity format', max: 3, desc: 'Risk Register format' },
                            { label: 'Executive Summary', max: 2, desc: 'Metrics + Next Steps' },
                            { label: 'Action Plan', max: 2, desc: 'Specific timeline' },
                        ].map(g => (
                            <div key={g.label} className={styles.benchmarkGuideCard}>
                                <span className={styles.benchmarkGuideLabel}>{g.label}</span>
                                <span className={styles.benchmarkGuideMax}>{g.max} pts</span>
                                <span className={styles.benchmarkGuideDesc}>{g.desc}</span>
                            </div>
                        ))}
                    </div>

                    <div className={styles.benchmarkControls}>
                        <div className={styles.benchmarkModeRow}>
                            <label className={styles.benchmarkModeLabel}>{t('analytics.benchmarkRunMode')}</label>
                            {[
                                { id: 'local', label: 'Local Only', desc: 'SecurityLM 7B' },
                                { id: 'hybrid', label: 'Hybrid', desc: 'SecurityLM + Cloud' },
                                { id: 'cloud', label: 'Cloud', desc: 'OpenClaude' },
                            ].map(m => (
                                <button
                                    key={m.id}
                                    className={`${styles.benchmarkModeBtn} ${benchmarkMode === m.id ? styles.benchmarkModeBtnActive : ''}`}
                                    onClick={() => setBenchmarkMode(m.id)}
                                    disabled={benchmarkRunning}
                                >
                                    {m.label}
                                    <span className={styles.benchmarkModeSub}>{m.desc}</span>
                                </button>
                            ))}
                        </div>
                        <label className={styles.benchmarkCompareLabel}>
                            <input
                                type="checkbox"
                                checked={benchmarkCompare}
                                onChange={e => setBenchmarkCompare(e.target.checked)}
                                disabled={benchmarkRunning}
                            />
                            <span>{t('analytics.benchmarkCompare')}</span>
                        </label>
                        <button
                            className={styles.benchmarkRunBtn}
                            disabled={benchmarkRunning || !benchmarkCases}
                            onClick={async () => {
                                setBenchmarkRunning(true)
                                setBenchmarkResult(null)
                                try {
                                    const body = {
                                        model_mode: benchmarkMode,
                                        compare_modes: benchmarkCompare ? ['local', 'cloud'] : [benchmarkMode]
                                    }
                                    const res = await fetch('/api/benchmark/run', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify(body)
                                    })
                                    if (res.ok) setBenchmarkResult(await res.json())
                                } catch (e) { console.error(e) }
                                finally { setBenchmarkRunning(false) }
                            }}
                        >
                            {benchmarkRunning ? t('analytics.benchmarkRunning') : t('analytics.benchmarkRun', { count: benchmarkCases?.total_cases || '?' })}
                        </button>
                    </div>

                    {benchmarkCases && (
                        <div className={styles.benchmarkCaseList}>
                            <h4 className={styles.benchmarkSectionTitle}>{t('analytics.benchmarkTestCases')} ({benchmarkCases.total_cases})</h4>
                            {benchmarkCases.test_cases?.map(tc => (
                                <div key={tc.id} className={styles.benchmarkCaseItem}>
                                    <span className={styles.benchmarkCaseId}>{tc.id}</span>
                                    <span className={styles.benchmarkCaseName}>{tc.name}</span>
                                    <span className={`${styles.benchmarkCatBadge} ${styles[`bcat_${tc.category}`]}`}>{tc.category}</span>
                                    <span className={styles.benchmarkCaseMeta}>{tc.implemented_controls_count} controls</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {benchmarkResult && (
                        <div className={styles.benchmarkResults}>
                            <h4 className={styles.benchmarkSectionTitle}>{t('analytics.benchmarkResults')}</h4>
                            <div className={styles.benchmarkSummary}>
                                {Object.entries(benchmarkResult.summary?.per_mode_avg_score || {}).map(([mode, score]) => (
                                    <div key={mode} className={styles.benchmarkSummaryCard}>
                                        <span className={styles.benchmarkSummaryMode}>{mode}</span>
                                        <span className={`${styles.benchmarkSummaryScore} ${
                                            score >= 85 ? styles.scoreGradeA :
                                            score >= 70 ? styles.scoreGradeB :
                                            score >= 55 ? styles.scoreGradeC : styles.scoreGradeD
                                        }`}>{score}%</span>
                                        <span className={styles.benchmarkSummaryGrade}>
                                            {score >= 85 ? 'Grade A' : score >= 70 ? 'Grade B' : score >= 55 ? 'Grade C' : 'Grade D'}
                                        </span>
                                    </div>
                                ))}
                            </div>
                            {benchmarkResult.results?.map(r => (
                                <div key={r.id} className={styles.benchmarkResultItem}>
                                    <div className={styles.benchmarkResultHeader}>
                                        <strong>{r.id}</strong> — {r.name}
                                    </div>
                                    <div className={styles.benchmarkResultModes}>
                                        {Object.entries(r.modes || {}).map(([mode, data]) => (
                                            <div key={mode} className={styles.benchmarkResultMode}>
                                                <span className={styles.benchmarkResultModeLabel}>{mode}</span>
                                                {data.status === 'ok' ? (
                                                    <>
                                                        <span className={`${styles.benchmarkResultScore} ${
                                                            data.quality_score?.percentage >= 85 ? styles.scoreGradeA :
                                                            data.quality_score?.percentage >= 70 ? styles.scoreGradeB :
                                                            data.quality_score?.percentage >= 55 ? styles.scoreGradeC : styles.scoreGradeD
                                                        }`}>{data.quality_score?.percentage}% ({data.quality_score?.grade})</span>
                                                        <span className={styles.benchmarkResultTime}>{data.elapsed_seconds}s</span>
                                                        <span className={styles.benchmarkResultLen}>{data.report_length} chars</span>
                                                    </>
                                                ) : (
                                                    <span className={styles.benchmarkResultError}>{data.error?.slice(0, 80)}</span>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    <div className={styles.benchmarkAuditNote}>
                        <h4>{t('analytics.benchmarkVsAudit')}</h4>
                        <div className={styles.benchmarkAuditGrid}>
                            <div className={styles.benchmarkAuditCol}>
                                <div className={styles.benchmarkAuditColTitle}>{t('analytics.benchmarkToolTitle')}</div>
                                <ul>
                                    <li>{t('analytics.benchmarkToolPoint1')}</li>
                                    <li>{t('analytics.benchmarkToolPoint2')}</li>
                                    <li>{t('analytics.benchmarkToolPoint3')}</li>
                                    <li>{t('analytics.benchmarkToolPoint4')}</li>
                                    <li>{t('analytics.benchmarkToolPoint5')}</li>
                                </ul>
                            </div>
                            <div className={styles.benchmarkAuditCol}>
                                <div className={styles.benchmarkAuditColTitle}>{t('analytics.benchmarkAuditTitle')}</div>
                                <ul>
                                    <li>{t('analytics.benchmarkAuditPoint1')}</li>
                                    <li>{t('analytics.benchmarkAuditPoint2')}</li>
                                    <li>{t('analytics.benchmarkAuditPoint3')}</li>
                                    <li>{t('analytics.benchmarkAuditPoint4')}</li>
                                    <li>{t('analytics.benchmarkAuditPoint5')}</li>
                                </ul>
                            </div>
                        </div>
                        <p className={styles.benchmarkAuditNote2} dangerouslySetInnerHTML={{ __html: t('analytics.benchmarkConclusion') }} />
                    </div>
                </div>
            )}
        </div>
    )
}
