'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import styles from './page.module.css'
import { ASSESSMENT_STANDARDS, calcWeightedScore, calcCategoryBreakdown, WEIGHT_SCORE, mergeCustomStandard } from '../../data/standards'
import { useControlDescriptions, useAssessmentTemplates } from '../../data'
import StepProgress from '@/components/StepProgress'
import { useTranslation } from '@/components/LanguageProvider'
import { Shield, ChevronRight, ChevronLeft } from 'lucide-react'
import ControlRow from './_components/ControlRow'
import DetailDrawer from './_components/DetailDrawer'
import EvidencePreviewModal from './_components/EvidencePreviewModal'

const POLL_INTERVAL = 8000
const ASSESSMENT_MODE_KEY = 'cyberai.assessmentMode'
const ASSESSMENT_MODE_EVENT = 'cyberai:assessment-mode-change'
const readStoredAssessmentMode = () => {
    if (typeof window === 'undefined') return 'hybrid'
    try {
        const v = window.localStorage.getItem(ASSESSMENT_MODE_KEY)
        return v === 'cloud' || v === 'local' || v === 'hybrid' ? v : 'hybrid'
    } catch (_) { return 'hybrid' }
}

// Map standard id → display label for all supported standards
const STANDARD_LABEL_MAP = {
    iso27001:  'ISO 27001:2022',
    tcvn11930: 'TCVN 11930:2017',
    nd13:      'Nghị định 13/2023',
    nist_csf:  'NIST CSF 2.0',
    pci_dss:   'PCI DSS 4.0',
    hipaa:     'HIPAA Security Rule',
    gdpr:      'GDPR',
    soc2:      'SOC 2',
}
const getStdLabel = (stdId) => STANDARD_LABEL_MAP[stdId] || stdId || 'ISO 27001:2022'

// WEIGHT_LABEL is resolved dynamically via t() in render
const WEIGHT_COLOR = { critical: 'var(--accent-red)', high: 'var(--accent-amber,#f59e0b)', medium: 'var(--accent-blue)', low: 'var(--text-dim)' }

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}

function SvgGauge({ percent, size = 110, color = 'var(--accent-blue)' }) {
    const r = (size - 14) / 2
    const circ = 2 * Math.PI * r
    const dash = (Math.min(Math.max(percent, 0), 100) / 100) * circ
    return (
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }} role="img" aria-label={`${percent}% compliance score`}>
            <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="7" />
            <circle
                cx={size / 2} cy={size / 2} r={r}
                fill="none" stroke={color} strokeWidth="7"
                strokeDasharray={`${dash} ${circ}`}
                strokeLinecap="round"
                style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
        </svg>
    )
}

const FORM_DRAFT_KEY = 'iso_form_draft_v2'

const EMPTY_FORM = {
    assessment_standard: 'iso27001',
    org_name: '', org_size: '', industry: '',
    employees: 0, it_staff: 0,
    servers: 0, firewalls: '', vpn: false,
    cloud_provider: '', antivirus: '', backup_solution: '',
    siem: '', network_diagram: '',
    implemented_controls: [],
    incidents_12m: 0, iso_status: '', notes: '',
    model_mode: 'hybrid',
    assessment_scope: 'full',
    scope_description: ''
}

export default function FormISOPage() {
    const router = useRouter()
    const { t, locale } = useTranslation()
    const CONTROL_DESCRIPTIONS = useControlDescriptions()
    const ASSESSMENT_TEMPLATES = useAssessmentTemplates()
    const [step, setStep] = useState(1)
    const [form, setForm] = useState(EMPTY_FORM)
    // result: { id, status, report, model_used, json_data, progress, compliance_percent, standard, org_name, error }
    const [result, setResult] = useState(null)
    const [loading, setLoading] = useState(false)
    const [activeTab, setActiveTab] = useState('form')
    const [assessmentHistory, setAssessmentHistory] = useState([])
    const [expandedCategory, setExpandedCategory] = useState(null)
    const [activeTooltip, setActiveTooltip] = useState(null)
    const [customDescriptions, setCustomDescriptions] = useState({})
    const [availableStandards, setAvailableStandards] = useState(ASSESSMENT_STANDARDS)
    const [standardsLoading, setStandardsLoading] = useState(false)
    const [evidenceMap, setEvidenceMap] = useState({})
    const [evidenceUploading, setEvidenceUploading] = useState(null)
    const [evidencePreviews, setEvidencePreviews] = useState({})
    const [previewLoading, setPreviewLoading] = useState(null)
    const [isDragging, setIsDragging] = useState(false)
    const [deletingId, setDeletingId] = useState(null)

    // ── Drawer state (Step 4 refactor) ─────────────────────────────────────
    const [drawerControlId, setDrawerControlId] = useState(null)
    const [controlNotes, setControlNotes] = useState({})
    const drawerReturnFocusRef = useRef(null)

    // ── Step 5: evidence preview modal ─────────────────────────────────────
    const [previewFile, setPreviewFile] = useState(null)
    const previewReturnFocusRef = useRef(null)

    const [tplFilter, setTplFilter] = useState('all')
    const [showTplInfo, setShowTplInfo] = useState(false)

    // Stable ref for polling — avoids stale closure bugs
    const pollingRef = useRef(null)
    const pollingIdRef = useRef(null)

    const uploadEvidence = async (controlId, files) => {
        if (!files || files.length === 0) return
        setEvidenceUploading(controlId)
        const fileList = Array.from(files)
        for (const file of fileList) {
            if (file.size > 10 * 1024 * 1024) {
                alert('File too large. Maximum size is 10MB.')
                setEvidenceUploading(null)
                return
            }
            const formData = new FormData()
            formData.append('file', file)
            try {
                const res = await fetch(`/api/iso27001/evidence/${controlId}`, { method: 'POST', body: formData })
                if (res.ok) {
                    const data = await res.json()
                    setEvidenceMap(prev => ({
                        ...prev,
                        [controlId]: [...(prev[controlId] || []), { filename: data.filename, size_bytes: data.size_bytes }]
                    }))
                }
            } catch (e) { console.error('Evidence upload failed:', e) }
        }
        setEvidenceUploading(null)
    }

    const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true) }
    const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false) }
    const handleDrop = (controlId) => (e) => {
        e.preventDefault(); e.stopPropagation(); setIsDragging(false)
        const files = e.dataTransfer?.files
        if (files?.length > 0) uploadEvidence(controlId, files)
    }

    const fetchPreview = async (controlId, filename) => {
        const key = `${controlId}__${filename}`
        if (evidencePreviews[key]) return // already fetched
        setPreviewLoading(key)
        try {
            const res = await fetch(`/api/iso27001/evidence/${controlId}/${filename}/preview`)
            if (res.ok) {
                const data = await res.json()
                setEvidencePreviews(prev => ({ ...prev, [key]: data }))
            }
        } catch (_) {}
        setPreviewLoading(null)
    }

    const fetchEvidenceForControl = async (controlId) => {
        try {
            const res = await fetch(`/api/iso27001/evidence/${controlId}`)
            if (res.ok) {
                const data = await res.json()
                if (data.files?.length > 0) {
                    setEvidenceMap(prev => ({ ...prev, [controlId]: data.files }))
                }
            }
        } catch (_) {}
    }

    const deleteEvidence = async (controlId, filename) => {
        try {
            await fetch(`/api/iso27001/evidence/${controlId}/${filename}`, { method: 'DELETE' })
            setEvidenceMap(prev => ({
                ...prev,
                [controlId]: (prev[controlId] || []).filter(f => f.filename !== filename)
            }))
        } catch (e) { console.error('Evidence delete failed:', e) }
    }

    useEffect(() => {
        try {
            localStorage.setItem(FORM_DRAFT_KEY, JSON.stringify(form))
        } catch (_) {}
    }, [form])

    useEffect(() => {
        const fetchCustomStandards = async () => {
            try {
                setStandardsLoading(true)
                const res = await fetch('/api/standards')
                if (!res.ok) return
                const data = await res.json()
                if (data.custom && data.custom.length > 0) {
                    for (const std of data.custom) {
                        try {
                            const detailRes = await fetch(`/api/standards/${std.id}`)
                            if (detailRes.ok) {
                                const detail = await detailRes.json()
                                if (detail.controls) {
                                    mergeCustomStandard(detail)
                                    if (detail.controlDescriptions) {
                                        setCustomDescriptions(prev => ({ ...prev, ...detail.controlDescriptions }))
                                    }
                                }
                            }
                        } catch (e) {
                            console.warn(`Failed to load custom standard ${std.id}:`, e)
                        }
                    }
                    setAvailableStandards([...ASSESSMENT_STANDARDS])
                }
            } catch (e) {
                console.warn('Failed to fetch custom standards:', e)
            } finally {
                setStandardsLoading(false)
            }
        }
        fetchCustomStandards()
    }, [])

    const allDescriptions = useMemo(() => {
        return { ...CONTROL_DESCRIPTIONS, ...customDescriptions }
    }, [CONTROL_DESCRIPTIONS, customDescriptions])

    const currentStandard = useMemo(() => {
        return availableStandards.find(s => s.id === form.assessment_standard) || availableStandards[0]
    }, [form.assessment_standard, availableStandards])

    const totalControls = useMemo(() => {
        return currentStandard.controls.reduce((acc, cat) => acc + cat.controls.length, 0)
    }, [currentStandard])

    const weightedScore = useMemo(() => {
        return calcWeightedScore(form.implemented_controls, currentStandard.controls)
    }, [form.implemented_controls, currentStandard.controls])

    const categoryBreakdown = useMemo(() => {
        return calcCategoryBreakdown(form.implemented_controls, currentStandard.controls)
    }, [form.implemented_controls, currentStandard.controls])

    // Result-aware breakdown: uses server-stored controls when viewing history
    const resultCategoryBreakdown = useMemo(() => {
        if (!result?.implemented_controls || result.implemented_controls.length === 0) return null
        const stdId = result.standard || form.assessment_standard
        const std = availableStandards.find(s => s.id === stdId) || currentStandard
        return calcCategoryBreakdown(result.implemented_controls, std.controls)
    }, [result?.implemented_controls, result?.standard, form.assessment_standard, availableStandards, currentStandard])

    const compliancePercent = weightedScore.percent

    const applyTemplateData = (parsed, keepModelMode = false, currentModelMode = 'hybrid') => {
        return {
            assessment_standard: parsed.assessment_standard || 'iso27001',
            org_name: parsed.organization?.name || '',
            org_size: parsed.organization?.size || '',
            industry: parsed.organization?.industry || '',
            employees: parsed.organization?.employees || 0,
            it_staff: parsed.organization?.it_staff || 0,
            servers: parsed.infrastructure?.servers || 0,
            firewalls: parsed.infrastructure?.firewalls || '',
            vpn: parsed.infrastructure?.vpn === 'Có' || parsed.infrastructure?.vpn === true,
            cloud_provider: parsed.infrastructure?.cloud || '',
            antivirus: parsed.infrastructure?.antivirus || '',
            backup_solution: parsed.infrastructure?.backup || '',
            siem: parsed.infrastructure?.siem || '',
            network_diagram: parsed.infrastructure?.network_diagram || '',
            implemented_controls: parsed.compliance?.implemented_controls || [],
            incidents_12m: parsed.compliance?.incidents_12m || 0,
            iso_status: parsed.compliance?.iso_status || '',
            notes: parsed.notes || '',
            model_mode: keepModelMode ? currentModelMode : 'hybrid',
            assessment_scope: parsed.assessment_scope || 'full',
            scope_description: parsed.scope_description || ''
        }
    }

    useEffect(() => {
        const reuseData = localStorage.getItem('reuse_iso_form')
        if (reuseData) {
            try {
                const parsed = JSON.parse(reuseData)
                if (parsed.organization) {
                    setForm(applyTemplateData(parsed))
                    setStep(1)
                    setActiveTab('form')
                }
                localStorage.removeItem('reuse_iso_form')
                fetchHistory()
                return
            } catch (e) {
                console.error('Failed to parse reuse data:', e)
                localStorage.removeItem('reuse_iso_form')
            }
        }

        const draft = localStorage.getItem(FORM_DRAFT_KEY)
        if (draft) {
            try {
                const parsed = JSON.parse(draft)
                if (parsed.org_name) {
                    setForm(prev => ({ ...prev, ...parsed }))
                }
            } catch (_) {}
        }

        fetchHistory()
    }, []) // eslint-disable-line react-hooks/exhaustive-deps

    // Step 6: sync model_mode from Settings-page preference (localStorage + event)
    useEffect(() => {
        const initial = readStoredAssessmentMode()
        setForm(prev => (prev.model_mode === initial ? prev : { ...prev, model_mode: initial }))
        const onChange = (e) => {
            const mode = e?.detail
            if (mode === 'cloud' || mode === 'local' || mode === 'hybrid') {
                setForm(prev => ({ ...prev, model_mode: mode }))
            }
        }
        window.addEventListener(ASSESSMENT_MODE_EVENT, onChange)
        return () => window.removeEventListener(ASSESSMENT_MODE_EVENT, onChange)
    }, [])

    // ── fetchHistory: handles paginated envelope {items,...} OR flat array ─────
    const fetchHistory = useCallback(async () => {
        try {
            // ?page_size=50 fetches last 50 entries; backend also supports ?flat=true
            const res = await fetch('/api/iso27001/assessments?page_size=50')
            if (!res.ok) return
            const payload = await res.json()
            // Backend returns { items: [...], total, ... } OR plain array (flat=true)
            const rawList = Array.isArray(payload) ? payload : (payload.items || [])
            const mapped = rawList.map(h => ({
                id: h.id,
                date: h.created_at
                    ? new Date(h.created_at).toLocaleDateString('vi-VN') + ' ' +
                      new Date(h.created_at).toLocaleTimeString('vi-VN')
                    : '—',
                org: h.org_name || 'Không rõ',
                standard: getStdLabel(h.standard),
                status: h.status || 'unknown',
                compliance_percent: h.compliance_percent ?? null,
            }))
            setAssessmentHistory(mapped)
        } catch (_) {
            // Fallback to localStorage if API is unreachable
            try {
                const saved = localStorage.getItem('assessment_history')
                if (saved) setAssessmentHistory(JSON.parse(saved))
            } catch (__) {}
        }
    }, [])

    // ── Stable polling engine — ref-based to avoid stale closures ──────────────
    const stopPolling = useCallback(() => {
        if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
        }
        pollingIdRef.current = null
    }, [])

    const startPolling = useCallback((id) => {
        stopPolling()
        pollingIdRef.current = id

        const poll = async () => {
            const targetId = pollingIdRef.current
            if (!targetId) return
            try {
                const res = await fetch(`/api/iso27001/assessments/${targetId}`)
                if (!res.ok) return
                const data = await res.json()

                if (data.status === 'completed' || data.status === 'failed') {
                    stopPolling()
                    setResult({
                        id: data.id,
                        status: data.status,
                        report: data.result?.report || data.error || 'Lỗi không xác định.',
                        model_used: data.result?.model_used,
                        json_data: data.result?.json_data || null,
                        // BUG 5 FIX: use server-stored compliance_percent, not form-derived
                        compliance_percent: data.compliance_percent ?? null,
                        standard: data.standard || data.system_info?.assessment_standard,
                        org_name: data.system_info?.organization?.name || '',
                        // Persist implemented_controls from server for category breakdown
                        implemented_controls: data.system_info?.compliance?.implemented_controls || [],
                        progress: null,
                    })
                    setActiveTab('result')
                    fetchHistory()
                } else if (data.status === 'processing' || data.status === 'pending') {
                    setResult(prev =>
                        prev?.id === targetId
                            ? { ...prev, status: data.status, progress: data.progress || prev.progress }
                            : prev
                    )
                }
            } catch (e) {
                console.warn('[Poll] Error fetching assessment status:', e)
            }
        }

        // Poll immediately once, then on interval
        poll()
        pollingRef.current = setInterval(poll, POLL_INTERVAL)
    }, [stopPolling, fetchHistory]) // eslint-disable-line react-hooks/exhaustive-deps

    // Clean up polling on unmount
    useEffect(() => () => stopPolling(), [stopPolling])

    // Start/stop polling when result.id or result.status changes
    useEffect(() => {
        if (result?.id && (result.status === 'processing' || result.status === 'pending')) {
            startPolling(result.id)
        } else {
            stopPolling()
        }
    }, [result?.id, result?.status]) // eslint-disable-line react-hooks/exhaustive-deps

    // Refresh history when switching to history tab; also poll history if items are processing
    useEffect(() => {
        if (activeTab === 'history') fetchHistory()
    }, [activeTab, fetchHistory])

    useEffect(() => {
        if (activeTab !== 'history') return
        const hasProcessing = assessmentHistory.some(
            h => h.status === 'processing' || h.status === 'pending'
        )
        if (!hasProcessing) return
        const timer = setInterval(fetchHistory, POLL_INTERVAL)
        return () => clearInterval(timer)
    }, [activeTab, assessmentHistory, fetchHistory])

    const set = (key, val) => setForm(p => ({ ...p, [key]: val }))

    const clearDraft = () => {
        try { localStorage.removeItem(FORM_DRAFT_KEY) } catch (_) {}
    }

    const handleStandardChange = (newStandardId) => {
        setForm(prev => ({
            ...prev,
            assessment_standard: newStandardId,
            implemented_controls: []
        }))
        setExpandedCategory(null)
    }

    const toggleControl = (controlId) => {
        setForm(prev => {
            const current = prev.implemented_controls
            const updated = current.includes(controlId)
                ? current.filter(id => id !== controlId)
                : [...current, controlId]
            return { ...prev, implemented_controls: updated }
        })
    }

    const toggleCategoryAll = (catControls, isAllSelected) => {
        const catControlIds = catControls.map(c => c.id)
        setForm(prev => {
            let updated = [...prev.implemented_controls]
            if (isAllSelected) {
                updated = updated.filter(id => !catControlIds.includes(id))
            } else {
                catControlIds.forEach(id => {
                    if (!updated.includes(id)) updated.push(id)
                })
            }
            return { ...prev, implemented_controls: updated }
        })
    }

    const nextStep = () => {
        if (step < 4) {
            setStep(step + 1)
            window.scrollTo({ top: 0, behavior: 'smooth' })
        }
    }

    const prevStep = () => {
        if (step > 1) {
            setStep(step - 1)
            window.scrollTo({ top: 0, behavior: 'smooth' })
        }
    }

    const buildEvidenceSummary = () => {
        const entries = Object.entries(evidenceMap).filter(([_, files]) => files && files.length > 0)
        if (entries.length === 0) return ''
        let summary = '\n\nBẰNG CHỨNG ĐÃ CUNG CẤP CHO CÁC CONTROLS:\n'
        entries.forEach(([controlId, files]) => {
            const fileNames = files.map(f => f.filename).join(', ')
            summary += `  ${controlId}: [${files.length} file] — ${fileNames}\n`
        })
        summary += '\nLưu ý: Các controls có bằng chứng đính kèm cho thấy tổ chức đã có tài liệu/minh chứng triển khai thực tế.\n'
        return summary
    }

    const submit = async () => {
        setLoading(true)
        setResult(null)
        stopPolling()
        try {
            const evidenceSummary = buildEvidenceSummary()
            const scopeNote = form.assessment_scope !== 'full'
                ? `\n\nPHẠM VI ĐÁNH GIÁ: ${form.assessment_scope === 'by_department' ? 'Theo phòng ban' : 'Theo hệ thống cụ thể'}${form.scope_description ? ` — ${form.scope_description}` : ''}`
                : ''
            const submissionForm = {
                ...form,
                notes: [form.notes || '', scopeNote, evidenceSummary].join('').trim(),
                evidence_map: Object.fromEntries(
                    Object.entries(evidenceMap)
                        .filter(([_, files]) => files && files.length > 0)
                        .map(([ctrlId, files]) => [ctrlId, files.map(f => f.filename)])
                )
            }
            const res = await fetch('/api/iso27001/assess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(submissionForm)
            })
            const data = await res.json()
            if (data.status === 'accepted') {
                clearDraft()
                // Seed result with all info available at submit time
                setResult({
                    id: data.id,
                    status: 'processing',
                    report: '',
                    progress: { message: 'Hệ thống đã tiếp nhận yêu cầu, đang khởi động...', percent: 0 },
                    compliance_percent: null,
                    standard: form.assessment_standard,
                    org_name: form.org_name,
                })
                setActiveTab('result')
                fetchHistory()
                // Start stable ref-based polling immediately
                startPolling(data.id)
            } else {
                setResult({ error: true, report: data.error || 'Server error' })
                setActiveTab('result')
            }
        } catch {
            setResult({ error: true, report: 'Lỗi kết nối server.' })
        } finally {
            setLoading(false)
        }
    }

    // BUG 4 FIX: loadAssessmentById — fetches any completed/running assessment by id
    // Completely independent of current result state to avoid stale closures
    const loadAssessmentById = useCallback(async (id) => {
        if (!id) return
        try {
            const res = await fetch(`/api/iso27001/assessments/${id}`)
            if (!res.ok) return
            const data = await res.json()
            if (data.status === 'completed' || data.status === 'failed') {
                setResult({
                    id: data.id,
                    status: data.status,
                    report: data.result?.report || data.error || '',
                    model_used: data.result?.model_used,
                    json_data: data.result?.json_data || null,
                    // BUG 5 FIX: use server-stored compliance_percent, not form-derived
                    compliance_percent: data.compliance_percent ?? null,
                    standard: data.standard || data.system_info?.assessment_standard,
                    org_name: data.system_info?.organization?.name || '',
                    // Persist implemented_controls from server for category breakdown
                    implemented_controls: data.system_info?.compliance?.implemented_controls || [],
                    progress: null,
                })
                setActiveTab('result')
            } else if (data.status === 'processing' || data.status === 'pending') {
                setResult({
                    id: data.id,
                    status: data.status,
                    report: '',
                    progress: data.progress || { message: 'Đang xử lý...', percent: 0 },
                    compliance_percent: data.compliance_percent ?? null,
                    standard: data.standard || data.system_info?.assessment_standard,
                    org_name: data.system_info?.organization?.name || '',
                })
                setActiveTab('result')
                startPolling(id)
            }
        } catch (e) {
            console.error('[loadAssessmentById] Error:', e)
        }
    }, [startPolling]) // eslint-disable-line react-hooks/exhaustive-deps

    // deleteAssessment — called from history tab with inline confirmation
    const deleteAssessment = useCallback(async (id) => {
        if (!id) return
        setDeletingId(id)
        try {
            const res = await fetch(`/api/iso27001/assessments/${id}`, { method: 'DELETE' })
            if (res.ok) {
                setAssessmentHistory(prev => prev.filter(h => h.id !== id))
                // Clear result panel if viewing deleted assessment
                setResult(prev => prev?.id === id ? null : prev)
            }
        } catch (e) {
            console.error('[deleteAssessment] Error:', e)
        } finally {
            setDeletingId(null)
        }
    }, [])

    const renderStepContent = () => {
        switch (step) {
            case 1:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>
                            {t('assessment.step1Title')}
                        </h2>
                        <div className={styles.grid}>
                            <div className={styles.fieldFull}>
                                <label className={styles.highlightLabel}>
                                    {t('assessment.standardLabel')} <span className={styles.required}>*</span>
                                </label>
                                <select
                                    className={styles.standardSelect}
                                    value={form.assessment_standard}
                                    onChange={e => handleStandardChange(e.target.value)}
                                >
                                    {availableStandards.map(s => (
                                        <option key={s.id} value={s.id}>{s.name}{s.source === 'custom' ? ' (custom)' : ''}</option>
                                    ))}
                                    {standardsLoading && <option disabled>Loading standards...</option>}
                                </select>
                                <small className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('assessment.standardHelp') }} />
                            </div>

                            <div className={styles.field}>
                                <label>{t('assessment.orgName')} <span className={styles.required}>*</span></label>
                                <input value={form.org_name} onChange={e => set('org_name', e.target.value)} placeholder={t('assessment.orgNamePlaceholder')} />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.orgSize')}</label>
                                <select value={form.org_size} onChange={e => set('org_size', e.target.value)}>
                                    <option value="">{t('assessment.orgSizeSelect')}</option>
                                    <option value="small">{t('assessment.orgSizeSmall')}</option>
                                    <option value="medium">{t('assessment.orgSizeMedium')}</option>
                                    <option value="large">{t('assessment.orgSizeLarge')}</option>
                                </select>
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.industry')}</label>
                                <input value={form.industry} onChange={e => set('industry', e.target.value)} placeholder={t('assessment.industryPlaceholder')} />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.complianceStatus')}</label>
                                <select value={form.iso_status} onChange={e => set('iso_status', e.target.value)}>
                                    <option value="">{t('assessment.complianceStatusSelect')}</option>
                                    <option value="Chưa triển khai">{t('assessment.complianceNotStarted')}</option>
                                    <option value="Đang triển khai">{t('assessment.complianceInProgress')}</option>
                                    <option value="Đã chứng nhận">{t('assessment.complianceCertified')}</option>
                                </select>
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.totalEmployees')}</label>
                                <input type="number" value={form.employees || ''} onChange={e => set('employees', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.itStaff')}</label>
                                <input type="number" value={form.it_staff || ''} onChange={e => set('it_staff', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>

                            <div className={styles.fieldFull}>
                                <div className={styles.scopeSection}>
                                    <div className={styles.labelWithInfo}>
                                        <label className={styles.highlightLabel}>{t('assessment.scopeTitle')}</label>
                                        <button
                                            type="button"
                                            className={`${styles.infoIcon} ${activeTooltip === 'scope_guide' ? styles.infoIconActive : ''}`}
                                            onClick={() => setActiveTooltip(activeTooltip === 'scope_guide' ? null : 'scope_guide')}
                                            title={t('assessment.scopeGuideTooltipTitle')}
                                        >ⓘ</button>
                                    </div>
                                    <p className={styles.helperText}>
                                        {t('assessment.scopeHelp')}
                                    </p>
                                    <div className={styles.scopeOptions}>
                                        {[
                                            { value: 'full', icon: '🏢', label: t('assessment.scopeFull'), desc: t('assessment.scopeFullDesc') },
                                            { value: 'by_department', icon: '👥', label: t('assessment.scopeDepartment'), desc: t('assessment.scopeDepartmentDesc') },
                                            { value: 'by_system', icon: '🖥️', label: t('assessment.scopeSystem'), desc: t('assessment.scopeSystemDesc') }
                                        ].map(opt => (
                                            <label
                                                key={opt.value}
                                                className={`${styles.scopeOption} ${form.assessment_scope === opt.value ? styles.scopeOptionActive : ''}`}
                                            >
                                                <input
                                                    type="radio"
                                                    name="assessment_scope"
                                                    value={opt.value}
                                                    checked={form.assessment_scope === opt.value}
                                                    onChange={() => set('assessment_scope', opt.value)}
                                                    hidden
                                                />
                                                <span className={styles.scopeOptionIcon}>{opt.icon}</span>
                                                <div className={styles.scopeOptionText}>
                                                    <strong>{opt.label}</strong>
                                                    <span>{opt.desc}</span>
                                                </div>
                                                {form.assessment_scope === opt.value && (
                                                    <span className={styles.scopeCheckMark}>✓</span>
                                                )}
                                            </label>
                                        ))}
                                    </div>
                                    {form.assessment_scope !== 'full' && (
                                        <div className={styles.scopeDescWrap}>
                                            <div className={styles.labelWithInfo}>
                                                <label>
                                                    {form.assessment_scope === 'by_department'
                                                        ? t('assessment.scopeDeptLabel')
                                                        : t('assessment.scopeSysLabel')}
                                                    <span className={styles.required}> *</span>
                                                </label>
                                            </div>
                                            <input
                                                className={styles.scopeDescInput}
                                                value={form.scope_description}
                                                onChange={e => set('scope_description', e.target.value)}
                                                placeholder={form.assessment_scope === 'by_department'
                                                    ? t('assessment.scopeDeptPlaceholder')
                                                    : t('assessment.scopeSysPlaceholder')}
                                            />
                                            <p className={styles.helperText} style={{ marginBottom: 0 }}>
                                                {form.assessment_scope === 'by_department'
                                                    ? t('assessment.scopeDeptHelp')
                                                    : t('assessment.scopeSysHelp')}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )
            case 2:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>
                            {t('assessment.step2Title')}
                        </h2>
                        <div className={styles.grid}>
                            <div className={styles.field}>
                                <label>{t('assessment.serversLabel')}</label>
                                <input type="number" value={form.servers || ''} onChange={e => set('servers', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.firewallLabel')}</label>
                                <textarea className={styles.autoTextarea} value={form.firewalls} onChange={e => set('firewalls', e.target.value)} placeholder={t('assessment.firewallPlaceholder')} rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.cloudLabel')}</label>
                                <textarea className={styles.autoTextarea} value={form.cloud_provider} onChange={e => set('cloud_provider', e.target.value)} placeholder={t('assessment.cloudPlaceholder')} rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.antivirusLabel')}</label>
                                <textarea className={styles.autoTextarea} value={form.antivirus} onChange={e => set('antivirus', e.target.value)} placeholder={t('assessment.antivirusPlaceholder')} rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.backupLabel')}</label>
                                <textarea className={styles.autoTextarea} value={form.backup_solution} onChange={e => set('backup_solution', e.target.value)} placeholder={t('assessment.backupPlaceholder')} rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.siemLabel')}</label>
                                <textarea className={styles.autoTextarea} value={form.siem} onChange={e => set('siem', e.target.value)} placeholder={t('assessment.siemPlaceholder')} rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>{t('assessment.incidentsLabel')}</label>
                                <input type="number" value={form.incidents_12m || ''} onChange={e => set('incidents_12m', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.fieldCheckbox}>
                                <label className={styles.checkLabel}>
                                    <input type="checkbox" checked={form.vpn} onChange={e => set('vpn', e.target.checked)} />
                                    <span>{t('assessment.vpnLabel')}</span>
                                </label>
                            </div>
                        </div>
                    </div>
                )
            case 3:
                return (
                    <div className={styles.stepContent}>
                        <div className={styles.controlHeader}>
                            <div>
                                <h2 className={styles.sectionTitle}>
                                    {t('assessment.controlsTitle')}
                                </h2>
                                <p className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('assessment.controlsStandard', { name: currentStandard.name }) }} />
                            </div>
                            <div className={styles.counterBadge}>
                                <span className={styles.countNum}>{form.implemented_controls.length}</span> / {totalControls} {t('assessment.passed')}
                            </div>
                        </div>

                        <div className={styles.complianceBar}>
                            <div className={styles.complianceTrack}>
                                <div
                                    className={styles.complianceFill}
                                    style={{ width: `${compliancePercent}%` }}
                                />
                            </div>
                            <span className={styles.complianceLabel}>{t('assessment.controlsCompliancePct', { percent: compliancePercent })}</span>
                        </div>

                        <p className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('assessment.controlsHelp') }} />

                        <div className={styles.accordionContainer}>
                            {currentStandard.controls.map((category, catIdx) => {
                                const isExpanded = expandedCategory === catIdx
                                const catControlIds = category.controls.map(c => c.id)
                                const selectedInCat = form.implemented_controls.filter(id => catControlIds.includes(id)).length
                                const isAllSelected = selectedInCat === category.controls.length

                                return (
                                    <div key={catIdx} className={`${styles.accordionItem} ${isExpanded ? styles.expanded : ''}`}>
                                        <div
                                            className={styles.accordionHeader}
                                            onClick={() => setExpandedCategory(isExpanded ? null : catIdx)}
                                        >
                                            <div className={styles.accTitle}>
                                                <span className={styles.accIcon}>{isExpanded ? '📂' : '📁'}</span>
                                                {category.category}
                                            </div>
                                            <div className={styles.accMeta}>
                                                <span className={`${styles.accCount} ${selectedInCat === category.controls.length ? styles.accCountFull : ''}`}>
                                                    {selectedInCat}/{category.controls.length}
                                                </span>
                                                <span className={styles.accArrow}>{isExpanded ? '▲' : '▼'}</span>
                                            </div>
                                        </div>

                                        {isExpanded && (
                                            <div className={styles.accordionBody}>
                                                <div className={styles.selectAllBox}>
                                                    <label className={styles.checkLabel}>
                                                        <input
                                                            type="checkbox"
                                                            checked={isAllSelected}
                                                            onChange={() => toggleCategoryAll(category.controls, isAllSelected)}
                                                        />
                                                        <strong>{t('assessment.selectAllGroup')}</strong>
                                                    </label>
                                                </div>
                                                <div className={styles.controlGrid}>
                                                    {category.controls.map(ctrl => {
                                                        const implemented = form.implemented_controls.includes(ctrl.id)
                                                        const evCount = (evidenceMap[ctrl.id] || []).length
                                                        return (
                                                            <ControlRow
                                                                key={ctrl.id}
                                                                control={ctrl}
                                                                state={{ implemented }}
                                                                onToggleImplemented={toggleControl}
                                                                onOpenDrawer={(id) => {
                                                                    drawerReturnFocusRef.current =
                                                                        document.activeElement instanceof HTMLElement
                                                                            ? document.activeElement
                                                                            : null
                                                                    setDrawerControlId(id)
                                                                    fetchEvidenceForControl(id)
                                                                }}
                                                                evidenceCount={evCount}
                                                                verdict={undefined}
                                                            />
                                                        )
                                                    })}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                )
            case 4:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>
                            {t('assessment.step4Title')}
                        </h2>
                        <p className={styles.helperText}>{t('assessment.step4Desc')}</p>

                        <div className={styles.fieldFull}>
                            <div className={styles.labelWithInfo}>
                                <label>{t('assessment.networkTopology')}</label>
                                <button
                                    type="button"
                                    className={`${styles.infoIcon} ${activeTooltip === 'topology_guide' ? styles.infoIconActive : ''}`}
                                    onClick={() => setActiveTooltip(activeTooltip === 'topology_guide' ? null : 'topology_guide')}
                                    title={t('assessment.topologyGuideTooltipTitle')}
                                >ⓘ</button>
                            </div>
                            <textarea
                                className={styles.textarea}
                                value={form.network_diagram}
                                onChange={e => set('network_diagram', e.target.value)}
                                placeholder={t('assessment.networkTopologyPlaceholder')}
                                rows={6}
                            />
                        </div>

                        <div className={styles.fieldFull}>
                            <div className={styles.labelWithInfo}>
                                <label>{t('assessment.additionalNotes')}</label>
                                <button
                                    type="button"
                                    className={`${styles.infoIcon} ${activeTooltip === 'notes_guide' ? styles.infoIconActive : ''}`}
                                    onClick={() => setActiveTooltip(activeTooltip === 'notes_guide' ? null : 'notes_guide')}
                                    title={t('assessment.notesGuideTooltipTitle')}
                                >ⓘ</button>
                            </div>
                            <textarea
                                className={styles.textarea}
                                value={form.notes}
                                onChange={e => set('notes', e.target.value)}
                                placeholder={t('assessment.notesPlaceholder')}
                                rows={3}
                            />
                        </div>

                        <div className={styles.modelSelectorWrap}>
                            <div className={styles.modelSelectorHeader}>
                                <h4 className={styles.modelSelectorTitle}>{t('assessment.aiMode')}</h4>
                                <button
                                    type="button"
                                    className={`${styles.infoIcon} ${activeTooltip === 'model_info' ? styles.infoIconActive : ''}`}
                                    onClick={() => setActiveTooltip(activeTooltip === 'model_info' ? null : 'model_info')}
                                    title={t('assessment.aiModeDetailTitle')}
                                >ⓘ</button>
                            </div>
                            <div className={styles.modelCompactRow}>
                                {[
                                    { id: 'local', icon: '🔒', label: t('assessment.aiModeLocal'), badge: t('assessment.aiModeLocalBadge'), badgeColor: styles.modelBadgeSafe },
                                    { id: 'hybrid', icon: '⚡', label: t('assessment.aiModeHybrid'), badge: t('assessment.aiModeHybridBadge'), badgeColor: styles.modelBadgeDefault },
                                    { id: 'cloud', icon: '☁️', label: t('assessment.aiModeCloud'), badge: t('assessment.aiModeCloudBadge'), badgeColor: styles.modelBadgeCloud }
                                ].map(opt => (
                                    <button
                                        key={opt.id}
                                        type="button"
                                        className={`${styles.modelCompactBtn} ${form.model_mode === opt.id ? styles.modelCompactActive : ''}`}
                                        onClick={() => set('model_mode', opt.id)}
                                    >
                                        <span className={styles.modelCompactIcon}>{opt.icon}</span>
                                        <span className={styles.modelCompactLabel}>{opt.label}</span>
                                        {form.model_mode === opt.id && (
                                            <span className={`${styles.modelCompactBadge} ${opt.badgeColor}`}>{opt.badge}</span>
                                        )}
                                    </button>
                                ))}
                            </div>

                        </div>

                        <div className={styles.summaryBox}>
                            <h4>{t('assessment.preSubmitCheck')}</h4>
                            <ul>
                                <li>{t('assessment.preSubmitStandard')}: <strong>{currentStandard.name}</strong></li>
                                <li>{t('assessment.preSubmitOrg')}: <strong>{form.org_name || t('assessment.preSubmitOrgEmpty')}</strong></li>
                                <li>{t('assessment.preSubmitSize')}: <strong>{t('assessment.preSubmitEmployees', { count: form.employees })}</strong> ({t('assessment.preSubmitServers', { count: form.servers })})</li>
                                <li>{t('assessment.preSubmitScope')}: <strong>
                                    {form.assessment_scope === 'full' ? t('assessment.preSubmitScopeFull') :
                                     form.assessment_scope === 'by_department' ? `${t('assessment.preSubmitScopeDept')}${form.scope_description ? ` — ${form.scope_description}` : ''}` :
                                     `${t('assessment.preSubmitScopeSystem')}${form.scope_description ? ` — ${form.scope_description}` : ''}`}
                                </strong></li>
                                <li>{t('assessment.preSubmitCompliance')}: <strong>{t('assessment.preSubmitControls', { implemented: form.implemented_controls.length, total: totalControls })}</strong> ({compliancePercent}%)</li>
                                <li>{t('assessment.preSubmitAiMode')}: <strong>
                                    {form.model_mode === 'local' ? t('assessment.preSubmitAiLocal') :
                                     form.model_mode === 'cloud' ? t('assessment.preSubmitAiCloud') :
                                     t('assessment.preSubmitAiHybrid')}
                                </strong></li>
                            </ul>
                        </div>
                    </div>
                )
            default:
                return null
        }
    }

    const filteredTemplates = useMemo(() => {
        if (tplFilter === 'all') return ASSESSMENT_TEMPLATES
        return ASSESSMENT_TEMPLATES.filter(t => t.standard === tplFilter)
    }, [tplFilter, ASSESSMENT_TEMPLATES])

    const selectTemplate = (tpl) => {
        const newForm = applyTemplateData(tpl.data, false, form.model_mode)
        setForm(newForm)
        setExpandedCategory(null)
        setActiveTab('form')
        setStep(1)
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    const getTemplateControlCount = (template) => {
        const std = availableStandards.find(s => s.id === template.standard)
        if (!std) return { implemented: 0, total: 0 }
        const total = std.controls.reduce((acc, cat) => acc + cat.controls.length, 0)
        const implemented = template.data.compliance?.implemented_controls?.length || 0
        return { implemented, total }
    }

    const STEP_TITLES = [
        t('assessment.step1Title'),
        t('assessment.step2Title'),
        t('assessment.step3Title'),
        t('assessment.step4Title'),
    ]

    const WEIGHT_LABEL = {
        critical: t('assessment.weightCritical'),
        high: t('assessment.weightHigh'),
        medium: t('assessment.weightMedium'),
        low: t('assessment.weightLow'),
    }

    return (
        <div className="page-container">
            <div className={styles.compactHeader}>
                <div className={styles.headerRow}>
                    <h1 className={styles.title}>{t('assessment.pageTitle')}</h1>
                    <p className={styles.subtitle}>{t('assessment.pageSubtitle')}</p>
                </div>

                <div className={styles.tabs}>
                    <button className={`${styles.tab} ${activeTab === 'form' ? styles.tabActive : ''}`} onClick={() => setActiveTab('form')}>
                        {t('assessment.tabForm')}
                    </button>
                    <button className={`${styles.tab} ${activeTab === 'result' ? styles.tabActive : ''}`} onClick={() => setActiveTab('result')} disabled={!result}>
                        {t('assessment.tabResult')} {result && !result.error ? '✓' : ''}
                    </button>
                    <button className={`${styles.tab} ${activeTab === 'history' ? styles.tabActive : ''}`} onClick={() => setActiveTab('history')}>
                        {t('assessment.tabHistory')}
                    </button>
                    <button className={`${styles.tab} ${activeTab === 'templates' ? styles.tabActive : ''}`} onClick={() => setActiveTab('templates')}>
                        {t('assessment.tabTemplates')}
                    </button>
                </div>

                {activeTab === 'form' && (
                    <div className={styles.inlineSteps}>
                        {STEP_TITLES.map((label, i) => {
                            const idx = i + 1
                            const done = idx < step
                            const active = idx === step
                            return (
                                <button
                                    key={i}
                                    type="button"
                                    className={`${styles.inlineStep} ${done ? styles.inlineStepDone : ''} ${active ? styles.inlineStepActive : ''}`}
                                    onClick={() => { if (done || active) setStep(idx) }}
                                    disabled={!done && !active}
                                >
                                    <span className={styles.inlineStepNum}>{done ? '✓' : idx}</span>
                                    <span className={styles.inlineStepLabel}>{label}</span>
                                </button>
                            )
                        })}
                    </div>
                )}
            </div>

            {activeTab === 'form' && (
                <div className={styles.formWrap}>
                    {form.org_name && (
                        <div className={styles.draftBanner}>
                            <span className={styles.draftBannerDot} />
                            <span>{t('assessment.draftSaved')}</span>
                            <button
                                type="button"
                                className={styles.draftClearBtn}
                                onClick={() => { clearDraft(); setForm(EMPTY_FORM); setStep(1) }}
                                title={t('assessment.draftClearTitle')}
                            >{t('assessment.draftClear')}</button>
                        </div>
                    )}

                    <div className={styles.stepBanner}>
                        <span className={styles.stepBannerCount}>{t('assessment.stepOf', { current: step, total: 4 })}</span>
                        <span className={styles.stepBannerSep}>—</span>
                        <span className={styles.stepBannerTitle}>
                            {STEP_TITLES[step - 1]}
                        </span>
                    </div>

                    <div className={styles.stepContainer}>
                        {renderStepContent()}
                    </div>

                    <div className={styles.stepActions}>
                        <button className={styles.btnSecondary} onClick={prevStep} disabled={step === 1 || loading}>
                            <ChevronLeft size={15} style={{ verticalAlign: 'middle' }} /> {t('assessment.backBtn')}
                        </button>

                        {step < 4 ? (
                            <button className={styles.btnPrimary} onClick={nextStep} disabled={step === 1 && !form.org_name}>
                                {t('assessment.nextBtn')} <ChevronRight size={15} style={{ verticalAlign: 'middle' }} />
                            </button>
                        ) : (
                            <button className={styles.btnSubmit} onClick={submit} disabled={loading || !form.org_name}>
                                {loading ? (
                                    <><span className={styles.spinner} /> {t('assessment.submitting')}</>
                                ) : (
                                    <><Shield size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />{t('assessment.submitBtn')}</>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            )}

            {activeTab === 'result' && result && (
                <div className={styles.resultWrap}>
                    {result.status === 'failed' || result.error ? (
                        <div className={styles.errorBox}>
                            <h3>{t('assessment.errorTitle')}</h3>
                            <p className={styles.errorDetail}>{result.report || t('assessment.errorTimeout')}</p>
                            {(result.report || '').includes('could not load model') || (result.report || '').includes('rpc error') ? (
                                <div className={styles.errorGuidance}>
                                    <strong>🔧 {t('assessment.errorCause')}:</strong> {t('assessment.errorModelLoad')}
                                    <br /><strong>{t('assessment.errorFix')}:</strong> <span dangerouslySetInnerHTML={{ __html: t('assessment.errorModelLoadFix') }} />
                                </div>
                            ) : (result.report || '').includes('Busy') || (result.report || '').includes('Tạm dừng') ? (
                                <div className={styles.errorGuidance}>
                                    <strong>⏳ {t('assessment.errorCause')}:</strong> {t('assessment.errorBusy')}
                                    <br /><strong>{t('assessment.errorFix')}:</strong> <span dangerouslySetInnerHTML={{ __html: t('assessment.errorBusyFix') }} />
                                </div>
                            ) : null}
                            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', flexWrap: 'wrap' }}>
                               <button className={styles.btnSecondary} onClick={() => setActiveTab('form')}>
                                   {t('assessment.backToEdit')}
                               </button>
                               <button className={styles.btnPrimary} onClick={() => {
                                   set('model_mode', 'hybrid')
                                   setActiveTab('form')
                                   setStep(4)
                               }}>
                                   {t('assessment.switchHybrid')}
                               </button>
                            </div>
                        </div>
                    ) : (result.status === 'processing' || result.status === 'pending') ? (
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
                            {/* BUG 2 FIX: progress bar driven by server polling data */}
                            <div className={styles.processingProgressWrap}>
                                <div className={styles.processingProgressBar}>
                                    <div
                                        className={styles.processingProgressFill}
                                        style={{ width: `${result.progress?.percent || 0}%` }}
                                    />
                                </div>
                                <span className={styles.processingProgressMsg}>
                                    {result.progress?.message || (result.status === 'pending' ? t('assessment.processingPending') : t('assessment.processingStarting'))}
                                    <span className={styles.processingProgressPct}> {result.progress?.percent || 0}%</span>
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
                            {/* BUG 2 FIX: step indicators driven by progress.percent, not hardcoded */}
                            <div className={styles.processingSteps}>
                                {(() => {
                                    const pct = result.progress?.percent || 0
                                    // Phase thresholds: RAG done at ≥5%, P1 active 5-80%, P1 done ≥80%, P2 active >80%
                                    const ragDone  = pct >= 5
                                    const p1Active = pct >= 5  && pct < 80
                                    const p1Done   = pct >= 80
                                    const p2Active = pct >= 80 && pct < 100
                                    return (<>
                                        <div className={styles.procStep}>
                                            <span className={styles.procStepNum} style={ragDone ? { background: 'var(--accent-green)', color: '#fff' } : {}}>
                                                {ragDone ? '✓' : '1'}
                                            </span>
                                            <div className={styles.procStepText}>
                                                <span className={styles.procStepLabel}>{t('assessment.ragLookup')}</span>
                                                <span className={styles.procStepDesc}>ChromaDB — {getStdLabel(result.standard || form.assessment_standard).split('(')[0].trim()}</span>
                                            </div>
                                        </div>
                                        <div className={styles.procStep} style={!ragDone ? { opacity: 0.4 } : {}}>
                                            <span className={`${styles.procStepNum} ${p1Active ? styles.procStepNumAnim : ''}`}
                                                style={p1Done ? { background: 'var(--accent-green)', color: '#fff' } : {}}>
                                                {p1Done ? '✓' : '2'}
                                            </span>
                                            <div className={styles.procStepText}>
                                                <span className={styles.procStepLabel}>
                                                    Phase 1 — {form.model_mode === 'cloud' ? 'OpenClaude' : 'SecurityLM'}
                                                </span>
                                                <span className={styles.procStepDesc}>{t('assessment.gapAnalysis')}</span>
                                            </div>
                                        </div>
                                        <div className={styles.procStep} style={!p1Done ? { opacity: 0.4 } : {}}>
                                            <span className={`${styles.procStepNum} ${p2Active ? styles.procStepNumAnim : ''}`}>3</span>
                                            <div className={styles.procStepText}>
                                                <span className={styles.procStepLabel}>
                                                    Phase 2 — {form.model_mode === 'local' ? 'Meta-Llama 8B' : 'OpenClaude'}
                                                </span>
                                                <span className={styles.procStepDesc}>{t('assessment.reportFormat')}</span>
                                            </div>
                                        </div>
                                    </>)
                                })()}
                            </div>
                            <div className={styles.pollingInfo} style={{ justifyContent: 'center', marginTop: '0.75rem' }}>
                                <span className={styles.pollingDot} />
                                <span>{t('assessment.autoCheckEvery', { seconds: POLL_INTERVAL/1000 })} · ID: <code style={{fontSize:'0.72rem',opacity:0.7}}>{result.id?.slice(0,8)}</code></span>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* BUG 5 FIX: use server-stored result.compliance_percent, fall back to form-derived */}
                            {(() => {
                                const displayPct = result.compliance_percent != null
                                    ? parseFloat(result.compliance_percent)
                                    : parseFloat(compliancePercent)
                                const displayPctStr = displayPct.toFixed(1)
                                // Use result.json_data counts if available (loaded from server), else form counts
                                const implCount = result.json_data?.compliance?.implemented_count ?? form.implemented_controls.length
                                const missingCount = result.json_data?.compliance?.missing_count ?? (totalControls - form.implemented_controls.length)
                                const totalCount = (implCount + missingCount) || totalControls
                                const displayOrg = result.org_name || form.org_name || t('assessment.processingOrg')
                                const displayStd = getStdLabel(result.standard || form.assessment_standard)
                                return (
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
                                            <span className={`${styles.scoreNum} ${
                                                displayPct >= 80 ? styles.scoreNumFull :
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
                                    <div className={`${styles.complianceBadge} ${
                                        displayPct >= 80 ? styles.badgeFull :
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
                                    {result.model_used && (
                                        <div className={styles.modelChips}>
                                            <span className={styles.modelChip}>🤖 {result.model_used.phase1?.split(':')[1] || 'AI'}</span>
                                            <span className={styles.modelChip}>📝 Semantic RAG</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                                )
                            })()}

                            <div className={styles.breakdownPanel}>
                                <h4 className={styles.breakdownTitle}>{t('assessment.categoryBreakdown')}</h4>
                                <div className={styles.breakdownGrid}>
                                    {(resultCategoryBreakdown || categoryBreakdown).map((cat, idx) => (
                                        <div key={idx} className={styles.breakdownItem}>
                                            <div className={styles.breakdownItemHeader}>
                                                <span className={styles.breakdownCatName}>{cat.category}</span>
                                                <span className={`${styles.breakdownPct} ${
                                                    cat.weightPercent >= 80 ? styles.scoreNumFull :
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

                                        <div className={styles.jsonDashCard}>
                                            <div className={styles.jsonDashCardTitle}>{t('assessment.complianceByWeight')}</div>
                                            {['critical','high','medium','low'].map(w => {
                                                const bd = result.json_data.weight_breakdown?.[w]
                                                if (!bd || bd.total === 0) return null
                                                const colors = { critical: 'var(--accent-red)', high: 'var(--accent-amber,#f59e0b)', medium: 'var(--accent-blue)', low: 'var(--text-dim)' }
                                                return (
                                                    <div key={w} className={styles.wbRow}>
                                                        <span className={styles.wbLabel} style={{ color: colors[w] }}>{w}</span>
                                                        <div className={styles.wbTrack}>
                                                            <div className={styles.wbFill} style={{ width: `${bd.percent}%`, background: colors[w] }} />
                                                        </div>
                                                        <span className={styles.wbPct}>{bd.percent}%</span>
                                                        <span className={styles.wbCounts}>{bd.implemented}/{bd.total}</span>
                                                    </div>
                                                )
                                            })}
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
                                                    a.download = `assessment_${result.id?.slice(0,8) || 'data'}.json`
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
                                <button className={styles.reportActionBtn} onClick={() => {
                                    navigator.clipboard?.writeText(result.report || '')
                                    .catch(() => {})
                                }}>
                                    {t('assessment.copyReport')}
                                </button>
                                <button className={styles.reportActionBtn} onClick={() => {
                                    // BUG 5 FIX: use server-stored compliance_percent from result
                                    const pdfPct = result.compliance_percent != null
                                        ? parseFloat(result.compliance_percent)
                                        : parseFloat(compliancePercent)
                                    const pdfPctStr = pdfPct.toFixed(1)
                                    const pdfOrg = result.org_name || form.org_name || t('assessment.processingOrg')
                                    const pdfStd = getStdLabel(result.standard || form.assessment_standard)
                                    const pdfPctColor = pdfPct >= 80 ? '#10b981' : pdfPct >= 50 ? '#3b82f6' : pdfPct >= 25 ? '#f59e0b' : '#ef4444'
                                    const implCount = result.json_data?.compliance?.implemented_count ?? form.implemented_controls.length
                                    const totalCount = (result.json_data?.compliance?.implemented_count ?? 0) +
                                                       (result.json_data?.compliance?.missing_count ?? 0) || totalControls
                                    const reportHtml = `<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Báo cáo Đánh giá - ${pdfOrg}</title>
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; max-width: 860px; margin: 40px auto; padding: 0 24px; color: #1e293b; line-height: 1.7; font-size: 14px; }
  h1 { font-size: 22px; font-weight: 800; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; margin-bottom: 4px; }
  h2 { font-size: 16px; font-weight: 700; color: #3b82f6; margin-top: 24px; border-left: 3px solid #3b82f6; padding-left: 8px; }
  h3 { font-size: 14px; font-weight: 600; color: #475569; margin-top: 16px; }
  .hero { display: flex; align-items: center; gap: 20px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 20px; margin: 16px 0; }
  .pct { font-size: 36px; font-weight: 900; color: ${pdfPctColor}; min-width: 90px; text-align: center; }
  .meta { flex: 1; }
  .meta strong { display: block; font-size: 16px; }
  .meta span { color: #64748b; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; margin: 8px 0; }
  th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 13px; }
  th { background: #f1f5f9; font-weight: 600; color: #475569; }
  ul, ol { padding-left: 20px; }
  li { margin-bottom: 4px; }
  strong { color: #1e293b; }
  blockquote { border-left: 3px solid #3b82f6; margin: 8px 0; padding: 6px 12px; background: #eff6ff; border-radius: 0 8px 8px 0; color: #475569; }
  hr { border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }
  code { background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 4px; padding: 1px 6px; font-size: 12px; }
  @media print { body { margin: 20px; } .no-print { display: none !important; } }
</style>
</head>
<body>
<div class="no-print" style="background:#eff6ff;border:1px solid #3b82f6;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:13px;color:#1d4ed8;">
  💡 <strong>Để lưu PDF:</strong> nhấn <kbd>Ctrl+P</kbd> (hoặc <kbd>⌘+P</kbd> trên Mac) → chọn <em>"Lưu thành PDF"</em> → <em>Lưu</em>.
  <button onclick="window.print()" style="float:right;padding:6px 14px;background:#3b82f6;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">🖨️ In / Lưu PDF</button>
</div>
<div class="hero">
  <div class="pct">${pdfPctStr}%</div>
  <div class="meta">
    <strong>${pdfOrg}</strong>
    <span>${pdfStd} &nbsp;·&nbsp; ${implCount}/${totalCount} Controls đạt</span>
  </div>
</div>
${escHtml(result.report || '')}
</body></html>`
                                    const w = window.open('', '_blank')
                                    if (w) { w.document.write(reportHtml); w.document.close() }
                                }}>
                                    {t('assessment.viewExportPdf')}
                                </button>
                                {result.id && (
                                    <button className={styles.reportActionBtn} onClick={async () => {
                                        try {
                                            const res = await fetch(`/api/iso27001/assessments/${result.id}/export-pdf`, { method: 'POST' })
                                            if (res.ok) {
                                                const blob = await res.blob()
                                                const url = URL.createObjectURL(blob)
                                                const a = document.createElement('a')
                                                a.href = url
                                                a.download = res.headers.get('content-disposition')?.split('filename=')[1] || `report_${result.id.slice(0,8)}.pdf`
                                                a.click()
                                                URL.revokeObjectURL(url)
                                            }
                                        } catch (e) { console.error('PDF export failed:', e) }
                                    }}>
                                        {t('assessment.downloadPdfServer')}
                                    </button>
                                )}
                                <button className={styles.reportActionBtn} onClick={() => window.print()}>
                                    {t('assessment.printReport')}
                                </button>
                                <button className={styles.reportActionBtnSecondary} onClick={() => setActiveTab('form')}>
                                    {t('assessment.newAssessment')}
                                </button>
                                <div className={styles.reEvalGroup}>
                                    <span className={styles.reEvalLabel}>{t('assessment.reAssess')}</span>
                                    {[
                                        { id: 'local', icon: '🔒', label: 'Local' },
                                        { id: 'hybrid', icon: '⚡', label: 'Hybrid' },
                                        { id: 'cloud', icon: '☁️', label: 'Cloud' },
                                    ].map(opt => (
                                        <button
                                            key={opt.id}
                                            className={styles.reEvalBtn}
                                            disabled={loading}
                                            onClick={() => {
                                                set('model_mode', opt.id)
                                                setTimeout(() => submit(), 100)
                                            }}
                                            title={t('assessment.reAssessWithMode', { mode: opt.label })}
                                        >
                                            {opt.icon} {opt.label}
                                        </button>
                                    ))}
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
                    )}
                </div>
            )}

            {activeTab === 'history' && (
                <div className={styles.historyWrap}>
                    <div className={styles.historyHeader}>
                        <h2 className={styles.sectionTitle}>{t('assessment.historyTitle')}</h2>
                        <button className={styles.refreshBtn} onClick={fetchHistory}>{t('assessment.historyRefresh')}</button>
                    </div>
                    <p className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('assessment.historyNote', { count: assessmentHistory.length }) }} />

                    {assessmentHistory.length === 0 ? (
                        <div className={styles.emptyHistory}>
                            {t('assessment.historyEmpty')}<br />
                            <small style={{ opacity: 0.5 }}>{t('assessment.historyEmptyHint')}</small>
                        </div>
                    ) : (
                        <div className={styles.historyList}>
                            {assessmentHistory.map((hist) => (
                                // BUG 6 FIX: hist.standard already uses getStdLabel() from fetchHistory
                                <div key={hist.id || hist.date} className={styles.historyItem}>
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
                                        {hist.compliance_percent != null ? (
                                            <>
                                                <span className={`${styles.histPercentNum} ${
                                                    hist.compliance_percent >= 80 ? styles.scoreNumFull :
                                                    hist.compliance_percent >= 50 ? styles.scoreNumMostly :
                                                    hist.compliance_percent >= 25 ? styles.scoreNumPartial :
                                                    styles.scoreNumLow
                                                }`}>{hist.compliance_percent}%</span>
                                                <span className={styles.histPercentLabel}>{t('assessment.historyCompliance')}</span>
                                            </>
                                        ) : (
                                            <span className={styles.histPercentLabel} style={{ fontSize: '0.7rem', opacity: 0.4 }}>—</span>
                                        )}
                                    </div>
                                    <div className={styles.histAction}>
                                        <span className={`${styles.statusBadge} ${styles[`status_${hist.status}`]}`}>
                                            {hist.status === 'completed' ? t('assessment.historyCompleted') :
                                             hist.status === 'failed'    ? t('assessment.historyFailed') :
                                             hist.status === 'processing'? t('assessment.historyProcessing') : t('assessment.historyPending')}
                                        </span>
                                        {/* BUG 4 FIX: use loadAssessmentById — fully independent of stale result state */}
                                        {hist.status === 'completed' && hist.id && (
                                            <button className={styles.btnSmall}
                                                onClick={() => loadAssessmentById(hist.id)}>
                                                {t('assessment.historyView')}
                                            </button>
                                        )}
                                        {(hist.status === 'processing' || hist.status === 'pending') && hist.id && (
                                            <button className={styles.btnSmall}
                                                onClick={() => loadAssessmentById(hist.id)}>
                                                {t('assessment.historyTrack')}
                                            </button>
                                        )}
                                        {hist.status === 'failed' && (
                                            <button className={styles.btnSmall}
                                                style={{ color: 'var(--accent-amber,#f59e0b)' }}
                                                onClick={() => { setActiveTab('form'); setStep(4) }}>
                                                {t('assessment.historyRetry')}
                                            </button>
                                        )}
                                        {/* Enhancement 9: delete with inline confirm */}
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
            )}

            {activeTab === 'templates' && (
                <div className={styles.templatesWrap}>
                    <div className={styles.tplHeaderRow}>
                        <div>
                            <h2 className={styles.sectionTitle}>
                                {t('assessment.templatesTitle')}
                            </h2>
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
                        >{t('common.all')} ({ASSESSMENT_TEMPLATES.length})</button>
                        {ASSESSMENT_STANDARDS.map(std => {
                            const count = ASSESSMENT_TEMPLATES.filter(t => t.standard === std.id).length
                            if (count === 0) return null
                            return (
                                <button
                                    key={std.id}
                                    className={`${styles.tplFilterBtn} ${tplFilter === std.id ? styles.tplFilterActive : ''}`}
                                    onClick={() => setTplFilter(std.id)}
                                >{std.id === 'iso27001' ? 'ISO 27001' : 'TCVN 11930'} ({count})</button>
                            )
                        })}
                    </div>

                    <div className={styles.tplGrid}>
                        {filteredTemplates.map(tpl => {
                            const { implemented, total } = getTemplateControlCount(tpl)
                            const percent = total > 0 ? ((implemented / total) * 100).toFixed(0) : 0
                            return (
                                <div key={tpl.id} className={styles.tplCard}>
                                    <div className={styles.tplCardHeader}>
                                        <div>
                                            <h3 className={styles.tplCardTitle}>{tpl.name}</h3>
                                            <span className={`${styles.tplStdBadge} ${tpl.standard === 'iso27001' ? styles.tplStdIso : styles.tplStdTcvn}`}>
                                                {tpl.standard === 'iso27001' ? 'ISO 27001' : 'TCVN 11930'}
                                            </span>
                                        </div>
                                        <span className={styles.tplIndustryTag}>{tpl.data.organization.industry}</span>
                                    </div>
                                    <div className={styles.tplCardBody}>
                                        <p className={styles.tplCardDesc}>{tpl.description}</p>
                                        <div className={styles.tplStatsRow}>
                                            <div className={styles.tplStatBox}>
                                                <span className={styles.tplStatNum}>{tpl.data.organization.employees}</span>
                                                <span className={styles.tplStatLabel}>{t('assessment.employees')}</span>
                                            </div>
                                            <div className={styles.tplStatBox}>
                                                <span className={styles.tplStatNum}>{tpl.data.infrastructure.servers}</span>
                                                <span className={styles.tplStatLabel}>{t('assessment.servers')}</span>
                                            </div>
                                            <div className={styles.tplStatBox}>
                                                <span className={styles.tplStatNum}>{tpl.data.organization.it_staff}</span>
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

                    <div className={styles.tplNavRow}>
                        <button className={styles.btnSecondary} onClick={() => setActiveTab('form')}>{t('assessment.formInput')}</button>
                        <Link href="/analytics" className={styles.btnPrimary}>{t('assessment.analyticsStandards')}</Link>
                    </div>
                </div>
            )}
            {activeTooltip && (() => {
                const ctrlId = activeTooltip
                if (['scope_guide', 'topology_guide', 'notes_guide', 'model_info'].includes(ctrlId)) return null
                const desc = allDescriptions[ctrlId]
                const allControls = currentStandard.controls.flatMap(c => c.controls)
                const ctrlObj = allControls.find(c => c.id === ctrlId)
                if (!ctrlObj) return null
                const isImplemented = form.implemented_controls.includes(ctrlId)
                const weightLabel = ctrlObj?.weight ? WEIGHT_LABEL[ctrlObj.weight] : null
                const weightColor = ctrlObj?.weight ? WEIGHT_COLOR[ctrlObj.weight] : null
                const ctrlEvidence = evidenceMap[ctrlId] || []
                return (
                    <>
                        <div className={styles.panelOverlay} onClick={() => setActiveTooltip(null)} />
                        <div className={styles.detailPanel}>
                            <div className={styles.panelHeader}>
                                <div className={styles.panelHeaderInfo}>
                                    <div className={styles.panelHeaderTop}>
                                        <span className={`${styles.panelBadge} ${isImplemented ? styles.panelBadgeActive : ''}`}>
                                            {isImplemented ? t('assessment.controlImplemented') : t('assessment.controlNotImplemented')}
                                        </span>
                                        {weightLabel && (
                                            <span className={styles.panelWeightBadge} style={{ color: weightColor, borderColor: weightColor }}>
                                                {weightLabel}
                                            </span>
                                        )}
                                    </div>
                                    <h3 className={styles.panelTitle}>{ctrlId}</h3>
                                    <p className={styles.panelSubtitle}>{ctrlObj?.label || ''}</p>
                                </div>
                                <button className={styles.panelClose} onClick={() => setActiveTooltip(null)}>✕</button>
                            </div>
                            <div className={styles.panelBody}>
                                {desc ? (
                                    <>
                                        <div className={styles.panelSection}>
                                            <div className={styles.panelSectionTitle}>
                                                {t('assessment.standardRequirement')}
                                            </div>
                                            <p className={styles.panelText}>{desc.requirement}</p>
                                        </div>
                                        <div className={styles.panelDivider} />

                                        <div className={styles.panelSection}>
                                            <div className={styles.panelSectionTitle}>
                                                {t('assessment.assessmentCriteria')}
                                            </div>
                                            <p className={styles.panelText}>{desc.criteria}</p>
                                        </div>
                                        <div className={styles.panelDivider} />

                                        <div className={styles.panelSection}>
                                            <div className={styles.panelSectionTitle}>
                                                {t('assessment.implementationGuide')}
                                            </div>
                                            <p className={styles.panelHint}>{desc.hint ||
                                                (isImplemented
                                                    ? t('assessment.implementedHint')
                                                    : t('assessment.notImplementedHint'))
                                            }</p>
                                        </div>
                                        <div className={styles.panelDivider} />

                                        {desc.evidence && desc.evidence.length > 0 && (
                                            <div className={styles.panelSection}>
                                                <div className={styles.panelSectionTitle}>
                                                    {t('assessment.requiredEvidence')}
                                                    <span className={styles.required} aria-hidden="true"> *</span>
                                                    <span className={styles.panelEvidenceCount}>{desc.evidence.length} {t('assessment.documentTypes')}</span>
                                                </div>
                                                <ul className={styles.panelEvidenceList}>
                                                    {desc.evidence.map((ev, i) => (
                                                        <li key={i} className={styles.panelEvidenceItem}>
                                                            <span className={styles.panelEvidenceDot} />
                                                            {ev}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <div className={styles.panelSection}>
                                        <p className={styles.panelHint}>
                                           {t('assessment.noControlDetail')}
                                       </p>
                                    </div>
                                )}

                                <div className={styles.panelDivider} />
                                <div className={styles.panelSection}>
                                    <div className={styles.panelSectionTitle}>
                                        {t('assessment.uploadEvidence')}
                                        {ctrlEvidence.length > 0 && (
                                            <span className={styles.panelEvidenceCount}>{ctrlEvidence.length} {t('assessment.filesUploaded')}</span>
                                        )}
                                    </div>
                                    <p className={styles.evidenceHelpText}>
                                        {t('assessment.evidenceHelpText', { controlId: ctrlId })}
                                    </p>
                                    <div
                                        className={`${styles.dropZone} ${isDragging ? styles.dropZoneActive : ''}`}
                                        onDragOver={handleDragOver}
                                        onDragLeave={handleDragLeave}
                                        onDrop={handleDrop(ctrlId)}
                                    >
                                        <div className={styles.dropZoneInner}>
                                            {evidenceUploading === ctrlId ? (
                                                <><span className={styles.spinner} /> {t('assessment.uploading')}</>
                                            ) : (
                                                <>
                                                    <span className={styles.dropZoneIcon}>📂</span>
                                                    <span className={styles.dropZoneText}>{t('assessment.dragDropFiles')}</span>
                                                    <span className={styles.dropZoneOr}>{t('assessment.or')}</span>
                                                    <label className={styles.panelUploadBtn}>
                                                        📎 {t('assessment.selectFiles')}
                                                        <input
                                                            type="file"
                                                            multiple
                                                            accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xlsx,.csv,.txt,.log,.conf,.xml,.json"
                                                            onChange={(e) => {
                                                                const files = e.target.files
                                                                if (files?.length > 0) uploadEvidence(ctrlId, files)
                                                                e.target.value = ''
                                                            }}
                                                            hidden
                                                            disabled={evidenceUploading === ctrlId}
                                                        />
                                                    </label>
                                                </>
                                            )}
                                        </div>
                                        <span className={styles.evidenceFormats}>.pdf .png .jpg .doc .xlsx .csv .txt .log .conf .xml .json</span>
                                    </div>
                                    {ctrlEvidence.length > 0 && (
                                        <div className={styles.evidenceFileList}>
                                            {ctrlEvidence.map((ef, eIdx) => {
                                                const previewKey = `${ctrlId}__${ef.filename}`
                                                const preview = evidencePreviews[previewKey]
                                                const isPreviewOpen = !!preview
                                                return (
                                                    <div key={eIdx} className={styles.evidenceFileWrap}>
                                                        <div className={styles.evidenceFile}>
                                                            <span className={styles.evidenceFileName}>📄 {ef.filename}</span>
                                                            <span className={styles.evidenceFileSize}>
                                                                {ef.size_bytes > 1024*1024
                                                                    ? `${(ef.size_bytes/1024/1024).toFixed(1)}MB`
                                                                    : `${Math.round(ef.size_bytes/1024)}KB`
                                                                }
                                                            </span>
                                                            <button
                                                                className={styles.evidencePreviewBtn}
                                                                onClick={() => fetchPreview(ctrlId, ef.filename)}
                                                                title={t('assessment.viewContent')}
                                                                disabled={previewLoading === previewKey}
                                                            >
                                                                {previewLoading === previewKey ? '⏳' : isPreviewOpen ? '👁️' : '👁️'}
                                                            </button>
                                                            <button
                                                                className={styles.evidenceDeleteBtn}
                                                                onClick={() => deleteEvidence(ctrlId, ef.filename)}
                                                                title={t('assessment.deleteFile')}
                                                            >✕</button>
                                                        </div>
                                                        {isPreviewOpen && (
                                                            <div className={styles.evidencePreview}>
                                                                {preview.content_type === 'image' ? (
                                                                    <div className={styles.evidencePreviewImage}>
                                                                        <a href={preview.download_url} target="_blank" rel="noopener noreferrer">
                                                                            🖼️ {t('assessment.viewOriginal')} ({Math.round(preview.size_bytes/1024)}KB)
                                                                        </a>
                                                                        <p className={styles.evidencePreviewNote}>{preview.content}</p>
                                                                    </div>
                                                                ) : (
                                                                    <pre className={styles.evidencePreviewCode}>{preview.content}</pre>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div className={styles.panelFooter}>
                                <button
                                    className={`${styles.panelToggleBtn} ${isImplemented ? styles.panelToggleBtnRemove : ''}`}
                                    onClick={() => { toggleControl(ctrlId); setActiveTooltip(null) }}
                                >
                                    {isImplemented ? t('assessment.unmarkImplemented') : t('assessment.markImplemented')}
                                </button>
                            </div>
                        </div>
                    </>
                )
            })()}
            {/* ── Right-side guide tooltip panel ── */}
            {['scope_guide', 'topology_guide', 'notes_guide', 'model_info'].includes(activeTooltip) && (
                <div className={styles.tooltipPanel}>
                    <div className={styles.tooltipPanelHeader}>
                        <strong>
                            {activeTooltip === 'scope_guide' && t('assessment.scopeGuideTitle')}
                            {activeTooltip === 'topology_guide' && t('assessment.topologyGuideTitle')}
                            {activeTooltip === 'notes_guide' && t('assessment.notesGuideTitle')}
                            {activeTooltip === 'model_info' && t('assessment.aiModeFlowTitle')}
                        </strong>
                        <button type="button" className={styles.tooltipPanelClose} onClick={() => setActiveTooltip(null)} aria-label="Close">✕</button>
                    </div>
                    <div className={styles.tooltipPanelBody}>
                        {activeTooltip === 'scope_guide' && (
                            <>
                                <div className={styles.tooltipSection}>
                                    <span className={styles.tooltipTag}>🏢 {t('assessment.scopeFull')}</span>
                                    <ul className={styles.tooltipList}>
                                        <li>{t('assessment.scopeFullTip1')}</li>
                                        <li>{t('assessment.scopeFullTip2')}</li>
                                        <li>{t('assessment.scopeFullTip3')}</li>
                                    </ul>
                                </div>
                                <div className={styles.tooltipSection}>
                                    <span className={styles.tooltipTag}>👥 {t('assessment.scopeDepartment')}</span>
                                    <ul className={styles.tooltipList}>
                                        <li>{t('assessment.scopeDeptTip1')}</li>
                                        <li>{t('assessment.scopeDeptTip2')}</li>
                                        <li>{t('assessment.scopeDeptTip3')}</li>
                                    </ul>
                                </div>
                                <div className={styles.tooltipSection}>
                                    <span className={styles.tooltipTag}>🖥️ {t('assessment.scopeSystem')}</span>
                                    <ul className={styles.tooltipList}>
                                        <li>{t('assessment.scopeSysTip1')}</li>
                                        <li>{t('assessment.scopeSysTip2')}</li>
                                        <li>{t('assessment.scopeSysTip3')}</li>
                                    </ul>
                                </div>
                            </>
                        )}
                        {activeTooltip === 'topology_guide' && (
                            <>
                                <p className={styles.tooltipNote}>{t('assessment.topologyGuideNote')}</p>
                                <div className={styles.tooltipSection}>
                                    <span className={styles.tooltipTag}>{t('assessment.topologyNetworkTag')}</span>
                                    <ul className={styles.tooltipList}>
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologyNetwork1') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologyNetwork2') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologyNetwork3') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologyNetwork4') }} />
                                    </ul>
                                </div>
                                <div className={styles.tooltipSection}>
                                    <span className={styles.tooltipTag}>{t('assessment.topologyServerTag')}</span>
                                    <ul className={styles.tooltipList}>
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologyServer1') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologyServer2') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologyServer3') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologyServer4') }} />
                                    </ul>
                                </div>
                                <div className={styles.tooltipSection}>
                                    <span className={styles.tooltipTag}>{t('assessment.topologySecurityTag')}</span>
                                    <ul className={styles.tooltipList}>
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologySecurity1') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologySecurity2') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologySecurity3') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologySecurity4') }} />
                                        <li dangerouslySetInnerHTML={{ __html: t('assessment.topologySecurity5') }} />
                                    </ul>
                                </div>
                                <div className={styles.tooltipSection}>
                                    <span className={styles.tooltipTag}>{t('assessment.topologyExampleTag')}</span>
                                    <p className={styles.tooltipExample}>{t('assessment.topologyExample')}</p>
                                </div>
                            </>
                        )}
                        {activeTooltip === 'notes_guide' && (
                            <div className={styles.tooltipSection}>
                                <ul className={styles.tooltipList}>
                                    <li dangerouslySetInnerHTML={{ __html: t('assessment.notesGuide1') }} />
                                    <li>{t('assessment.notesGuide2')}</li>
                                    <li dangerouslySetInnerHTML={{ __html: t('assessment.notesGuide3') }} />
                                    <li>{t('assessment.notesGuide4')}</li>
                                    <li>{t('assessment.notesGuide5')}</li>
                                </ul>
                            </div>
                        )}
                        {activeTooltip === 'model_info' && (
                            <div className={styles.modelDetailBody}>
                                <div className={styles.modelDetailItem}>
                                    <div className={styles.modelDetailHead}>
                                        <span>🔒</span> <strong>Local Only</strong> <span className={styles.modelDetailTag}>SecurityLM</span>
                                    </div>
                                    <div className={styles.modelDetailFlow}>
                                        <span className={styles.flowStep}>📋 Form Data</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={`${styles.flowStep} ${styles.flowLocal}`}>🖥️ SecurityLM (Local)</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={`${styles.flowStep} ${styles.flowLocal}`}>🖥️ SecurityLM (Local)</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={styles.flowStep}>📄 Report</span>
                                    </div>
                                    <p className={styles.modelDetailDesc} dangerouslySetInnerHTML={{ __html: t('assessment.aiModeLocalDesc') }} />
                                </div>
                                <div className={styles.modelDetailDivider} />
                                <div className={styles.modelDetailItem}>
                                    <div className={styles.modelDetailHead}>
                                        <span>⚡</span> <strong>Hybrid</strong> <span className={styles.modelDetailTag}>SecurityLM → OpenClaude</span>
                                    </div>
                                    <div className={styles.modelDetailFlow}>
                                        <span className={styles.flowStep}>📋 Form Data</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={`${styles.flowStep} ${styles.flowLocal}`}>🖥️ SecurityLM (Local)</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={styles.flowStep}>📊 Raw GAP ({t('assessment.aiModeAnonymized')})</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={`${styles.flowStep} ${styles.flowCloud}`}>☁️ OpenClaude</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={styles.flowStep}>📄 Report</span>
                                    </div>
                                    <p className={styles.modelDetailDesc} dangerouslySetInnerHTML={{ __html: t('assessment.aiModeHybridDesc') }} />
                                </div>
                                <div className={styles.modelDetailDivider} />
                                <div className={styles.modelDetailItem}>
                                    <div className={styles.modelDetailHead}>
                                        <span>☁️</span> <strong>Cloud Only</strong> <span className={styles.modelDetailTag}>OpenClaude</span>
                                    </div>
                                    <div className={styles.modelDetailFlow}>
                                        <span className={styles.flowStep}>📋 Form Data</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={`${styles.flowStep} ${styles.flowCloud}`}>☁️ OpenClaude (Phase 1)</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={`${styles.flowStep} ${styles.flowCloud}`}>☁️ OpenClaude (Phase 2)</span>
                                        <span className={styles.flowArrow}>→</span>
                                        <span className={styles.flowStep}>📄 Report</span>
                                    </div>
                                    <p className={styles.modelDetailDesc} dangerouslySetInnerHTML={{ __html: t('assessment.aiModeCloudDesc') }} />
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ── Step 4: Overlay DetailDrawer ─────────────────────────────── */}
            {(() => {
                const allControls = currentStandard.controls.flatMap(c => c.controls)
                const ctrl = allControls.find(c => c.id === drawerControlId) || null
                const desc = drawerControlId ? allDescriptions[drawerControlId] : null
                const files = drawerControlId ? (evidenceMap[drawerControlId] || []) : []
                const implemented = drawerControlId
                    ? form.implemented_controls.includes(drawerControlId)
                    : false
                const state = ctrl ? {
                    implemented,
                    description: desc,
                    evidenceFiles: files,
                    notes: controlNotes[drawerControlId] || '',
                    // Step 5 AI verdict fields (not yet populated)
                    evidence_verdict: undefined,
                    missing_items: undefined,
                    confidence: undefined,
                    ai_notes: undefined,
                } : null
                return (
                    <DetailDrawer
                        open={!!ctrl}
                        control={ctrl}
                        state={state}
                        onClose={() => setDrawerControlId(null)}
                        onToggleImplemented={(id) => toggleControl(id)}
                        onUploadFiles={(id, filelist) => uploadEvidence(id, filelist)}
                        onDeleteFile={(id, filename) => deleteEvidence(id, filename)}
                        onChangeNotes={(id, text) => setControlNotes(prev => ({ ...prev, [id]: text }))}
                        onExpandFile={(file) => {
                            previewReturnFocusRef.current =
                                document.activeElement instanceof HTMLElement
                                    ? document.activeElement
                                    : null
                            setPreviewFile({ ...file, control_id: drawerControlId })
                        }}
                        returnFocusRef={drawerReturnFocusRef}
                    />
                )
            })()}

            {/* ── Step 5: Evidence preview modal ─────────────────────────── */}
            <EvidencePreviewModal
                open={!!previewFile}
                file={previewFile}
                onClose={() => setPreviewFile(null)}
                returnFocusRef={previewReturnFocusRef}
            />
        </div>
    )
}
