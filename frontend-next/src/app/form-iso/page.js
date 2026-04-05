'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import styles from './page.module.css'
import { ASSESSMENT_STANDARDS, calcWeightedScore, calcCategoryBreakdown, WEIGHT_SCORE, mergeCustomStandard } from '../../data/standards'
import { CONTROL_DESCRIPTIONS } from '../../data/controlDescriptions'
import { ASSESSMENT_TEMPLATES } from '../../data/templates'
import StepProgress from '@/components/StepProgress'
import { Shield, ChevronRight, ChevronLeft } from 'lucide-react'

const POLL_INTERVAL = 8000

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

const WEIGHT_LABEL = { critical: 'Tối quan trọng', high: 'Quan trọng', medium: 'Trung bình', low: 'Thấp' }
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
    }, [customDescriptions])

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
                            Thông tin Tổ chức & Tiêu chuẩn
                        </h2>
                        <div className={styles.grid}>
                            <div className={styles.fieldFull}>
                                <label className={styles.highlightLabel}>
                                    Tiêu chuẩn đánh giá <span className={styles.required}>*</span>
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
                                <small className={styles.helperText}>
                                    Tiêu chuẩn được chọn sẽ quyết định <strong>bộ câu hỏi Checklists</strong> ở Bước 3.
                                </small>
                            </div>

                            <div className={styles.field}>
                                <label>Tên tổ chức / Doanh nghiệp <span className={styles.required}>*</span></label>
                                <input value={form.org_name} onChange={e => set('org_name', e.target.value)} placeholder="VD: Công ty Điện toán ABC" />
                            </div>
                            <div className={styles.field}>
                                <label>Quy mô doanh nghiệp</label>
                                <select value={form.org_size} onChange={e => set('org_size', e.target.value)}>
                                    <option value="">Chọn quy mô</option>
                                    <option value="small">Nhỏ (Dưới 50 NV)</option>
                                    <option value="medium">Trung bình (50-200 NV)</option>
                                    <option value="large">Lớn (Trên 200 NV)</option>
                                </select>
                            </div>
                            <div className={styles.field}>
                                <label>Lĩnh vực / Ngành nghề</label>
                                <input value={form.industry} onChange={e => set('industry', e.target.value)} placeholder="VD: Tài chính, Y tế, Bán lẻ..." />
                            </div>
                            <div className={styles.field}>
                                <label>Trạng thái tuân thủ hiện tại</label>
                                <select value={form.iso_status} onChange={e => set('iso_status', e.target.value)}>
                                    <option value="">Chọn trạng thái</option>
                                    <option value="Chưa triển khai">Chưa có gì, đang tìm hiểu</option>
                                    <option value="Đang triển khai">Đang xây dựng chính sách</option>
                                    <option value="Đã chứng nhận">Đã đạt chứng nhận (Tái đánh giá)</option>
                                </select>
                            </div>
                            <div className={styles.field}>
                                <label>Tổng số nhân viên</label>
                                <input type="number" value={form.employees || ''} onChange={e => set('employees', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.field}>
                                <label>Số nhân sự IT / Bảo mật</label>
                                <input type="number" value={form.it_staff || ''} onChange={e => set('it_staff', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>

                            <div className={styles.fieldFull}>
                                <div className={styles.scopeSection}>
                                    <div className={styles.labelWithInfo}>
                                        <label className={styles.highlightLabel}>Phạm vi đánh giá (Scope)</label>
                                        <div className={styles.infoWrap}>
                                            <button
                                                type="button"
                                                className={`${styles.infoIcon} ${activeTooltip === 'scope_guide' ? styles.infoIconActive : ''}`}
                                                onClick={() => setActiveTooltip(activeTooltip === 'scope_guide' ? null : 'scope_guide')}
                                                title="Hướng dẫn chọn phạm vi"
                                            >ⓘ</button>
                                            {activeTooltip === 'scope_guide' && (
                                                <div className={styles.tooltip}>
                                                    <div className={styles.tooltipHeader}>
                                                        <strong>🎯 Hướng dẫn chọn phạm vi đánh giá</strong>
                                                        <button type="button" className={styles.tooltipClose} onClick={() => setActiveTooltip(null)}>✕</button>
                                                    </div>
                                                    <div className={styles.tooltipBody}>
                                                        <div className={styles.tooltipSection}>
                                                            <span className={styles.tooltipTag}>🏢 Toàn bộ tổ chức</span>
                                                            <ul className={styles.tooltipList}>
                                                                <li>Phù hợp khi lần đầu đánh giá hoặc chuẩn bị chứng nhận ISO</li>
                                                                <li>Bao gồm tất cả phòng ban, hệ thống, quy trình trong tổ chức</li>
                                                                <li>AI sẽ đánh giá tổng thể và đưa ra khuyến nghị ưu tiên toàn công ty</li>
                                                            </ul>
                                                        </div>
                                                        <div className={styles.tooltipSection}>
                                                            <span className={styles.tooltipTag}>👥 Theo phòng ban</span>
                                                            <ul className={styles.tooltipList}>
                                                                <li>Phù hợp khi đánh giá nội bộ từng bộ phận riêng lẻ</li>
                                                                <li>VD: Chỉ đánh giá Phòng IT + Phòng Kế toán</li>
                                                                <li>Liệt kê tên phòng ban cách nhau bởi dấu phẩy</li>
                                                            </ul>
                                                        </div>
                                                        <div className={styles.tooltipSection}>
                                                            <span className={styles.tooltipTag}>🖥️ Theo hệ thống</span>
                                                            <ul className={styles.tooltipList}>
                                                                <li>Phù hợp khi đánh giá một ứng dụng / hệ thống cụ thể</li>
                                                                <li>VD: Core Banking, ERP SAP, Portal khách hàng</li>
                                                                <li>AI sẽ tập trung phân tích rủi ro cho hệ thống đó</li>
                                                            </ul>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    <p className={styles.helperText}>
                                        Xác định phạm vi hệ thống / bộ phận nào được đưa vào đánh giá lần này.
                                    </p>
                                    <div className={styles.scopeOptions}>
                                        {[
                                            { value: 'full', icon: '🏢', label: 'Toàn bộ tổ chức', desc: 'Tất cả hệ thống, phòng ban, quy trình' },
                                            { value: 'by_department', icon: '👥', label: 'Theo phòng ban', desc: 'Một hoặc vài phòng ban cụ thể' },
                                            { value: 'by_system', icon: '🖥️', label: 'Theo hệ thống', desc: 'Một hệ thống / ứng dụng nhất định' }
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
                                                        ? 'Phòng ban được đánh giá'
                                                        : 'Hệ thống / ứng dụng được đánh giá'}
                                                    <span className={styles.required}> *</span>
                                                </label>
                                            </div>
                                            <input
                                                className={styles.scopeDescInput}
                                                value={form.scope_description}
                                                onChange={e => set('scope_description', e.target.value)}
                                                placeholder={form.assessment_scope === 'by_department'
                                                    ? 'VD: Phòng IT, Phòng Kế toán, Phòng Kinh doanh'
                                                    : 'VD: Hệ thống ERP SAP, Portal khách hàng, Core Banking'}
                                            />
                                            <p className={styles.helperText} style={{ marginBottom: 0 }}>
                                                {form.assessment_scope === 'by_department'
                                                    ? 'Liệt kê tên phòng ban, cách nhau bởi dấu phẩy. AI sẽ tập trung đánh giá các bộ phận này.'
                                                    : 'Mô tả ngắn gọn tên và chức năng hệ thống. AI sẽ phân tích rủi ro tập trung cho hệ thống đó.'}
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
                            Hạ tầng & Kỹ thuật mạng
                        </h2>
                        <div className={styles.grid}>
                            <div className={styles.field}>
                                <label>Số lượng máy chủ (Physical & VM)</label>
                                <input type="number" value={form.servers || ''} onChange={e => set('servers', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.field}>
                                <label>Tường lửa (Firewall)</label>
                                <textarea className={styles.autoTextarea} value={form.firewalls} onChange={e => set('firewalls', e.target.value)} placeholder="VD: FortiGate 100F, Palo Alto..." rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>Dịch vụ đám mây (Cloud)</label>
                                <textarea className={styles.autoTextarea} value={form.cloud_provider} onChange={e => set('cloud_provider', e.target.value)} placeholder="VD: AWS, Azure, Google Cloud..." rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>Giải pháp chống mã độc (AV/EDR)</label>
                                <textarea className={styles.autoTextarea} value={form.antivirus} onChange={e => set('antivirus', e.target.value)} placeholder="VD: CrowdStrike, Kaspersky..." rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>Công nghệ sao lưu (Backup)</label>
                                <textarea className={styles.autoTextarea} value={form.backup_solution} onChange={e => set('backup_solution', e.target.value)} placeholder="VD: Veeam Backup, NAS Synology..." rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>Hệ thống ghi nhật ký (SIEM/Log)</label>
                                <textarea className={styles.autoTextarea} value={form.siem} onChange={e => set('siem', e.target.value)} placeholder="VD: Wazuh, Splunk, ElasticSearch..." rows={2} />
                            </div>
                            <div className={styles.field}>
                                <label>Sự cố an ninh mạng (12 tháng qua)</label>
                                <input type="number" value={form.incidents_12m || ''} onChange={e => set('incidents_12m', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.fieldCheckbox}>
                                <label className={styles.checkLabel}>
                                    <input type="checkbox" checked={form.vpn} onChange={e => set('vpn', e.target.checked)} />
                                    <span>Hệ thống có cấu hình VPN cho nhân viên từ xa</span>
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
                                    Biện pháp kiểm soát (Controls)
                                </h2>
                                <p className={styles.helperText}>Tiêu chuẩn: <strong>{currentStandard.name}</strong></p>
                            </div>
                            <div className={styles.counterBadge}>
                                <span className={styles.countNum}>{form.implemented_controls.length}</span> / {totalControls} Đạt
                            </div>
                        </div>

                        <div className={styles.complianceBar}>
                            <div className={styles.complianceTrack}>
                                <div
                                    className={styles.complianceFill}
                                    style={{ width: `${compliancePercent}%` }}
                                />
                            </div>
                            <span className={styles.complianceLabel}>{compliancePercent}% tuân thủ</span>
                        </div>

                        <p className={styles.helperText}>Đánh dấu (✓) vào các biện pháp mà tổ chức <strong>đã triển khai thực tế</strong>:</p>

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
                                                        <strong>Chọn tất cả thuộc nhóm này</strong>
                                                    </label>
                                                </div>
                                                <div className={styles.controlGrid}>
                                                    {category.controls.map(ctrl => {
                                                        const desc = allDescriptions[ctrl.id]
                                                        const w = ctrl.weight || 'medium'
                                                        return (
                                                            <div key={ctrl.id} className={`${styles.controlItem} ${form.implemented_controls.includes(ctrl.id) ? styles.controlActive : ''}`}>
                                                                <label className={styles.controlLabel}>
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={form.implemented_controls.includes(ctrl.id)}
                                                                        onChange={() => toggleControl(ctrl.id)}
                                                                    />
                                                                    <div className={styles.ctrlText}>
                                                                        <div className={styles.ctrlTopRow}>
                                                                            <span className={styles.ctrlId}>{ctrl.id}</span>
                                                                            <span
                                                                                className={styles.weightBadge}
                                                                                style={{ borderColor: WEIGHT_COLOR[w], color: WEIGHT_COLOR[w] }}
                                                                                title={`Mức độ quan trọng: ${WEIGHT_LABEL[w]} (${WEIGHT_SCORE[w]} điểm)`}
                                                                            >{w}</span>
                                                                        </div>
                                                                        <span className={styles.ctrlLabel}>{ctrl.label}</span>
                                                                    </div>
                                                                </label>
                                                                <button
                                                                    type="button"
                                                                    className={`${styles.infoIcon} ${activeTooltip === ctrl.id ? styles.infoIconActive : ''}`}
                                                                    onClick={(e) => { e.stopPropagation(); const newId = activeTooltip === ctrl.id ? null : ctrl.id; setActiveTooltip(newId); if (newId) fetchEvidenceForControl(newId) }}
                                                                    title="Chi tiết & upload bằng chứng"
                                                                >ⓘ</button>
                                                            </div>
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
                            Mô tả hệ thống & Tổng kết
                        </h2>
                        <p className={styles.helperText}>Diễn giải kiến trúc mạng hoặc đặc thù hệ thống để AI đưa ra đánh giá chính xác nhất:</p>

                        <div className={styles.fieldFull}>
                            <div className={styles.labelWithInfo}>
                                <label>Mô tả kiến trúc mạng / Topology</label>
                                <div className={styles.infoWrap}>
                                    <button
                                        type="button"
                                        className={styles.infoIcon}
                                        onClick={() => setActiveTooltip(activeTooltip === 'topology_guide' ? null : 'topology_guide')}
                                        title="Hướng dẫn mô tả hệ thống"
                                    >ⓘ</button>
                                    {activeTooltip === 'topology_guide' && (
                                        <div className={`${styles.tooltip} ${styles.tooltipWide}`}>
                                            <div className={styles.tooltipHeader}>
                                                <strong>💡 Hướng dẫn mô tả hệ thống</strong>
                                                <button type="button" className={styles.tooltipClose} onClick={() => setActiveTooltip(null)}>✕</button>
                                            </div>
                                            <div className={styles.tooltipBody}>
                                                <p className={styles.tooltipNote}>Chưa hỗ trợ đọc ảnh/file. Vui lòng <strong>mô tả bằng văn bản</strong> theo gợi ý:</p>
                                                <div className={styles.tooltipSection}>
                                                    <span className={styles.tooltipTag}>🌐 Network Architecture (Kiến trúc mạng)</span>
                                                    <ul className={styles.tooltipList}>
                                                        <li>Số lượng <strong>VLAN</strong> (Virtual LAN) và mục đích: Server, User, Guest, Management</li>
                                                        <li><strong>DMZ Zone</strong> (Vùng mạng biên): có không, chứa Web Server, Mail Gateway, DNS</li>
                                                        <li><strong>Firewall</strong> (Tường lửa): model, vị trí biên mạng / giữa các security zone</li>
                                                        <li>Internet uplink: số <strong>ISP</strong>, có <strong>BGP failover</strong> / load balancing không</li>
                                                    </ul>
                                                </div>
                                                <div className={styles.tooltipSection}>
                                                    <span className={styles.tooltipTag}>🖥️ Server Infrastructure (Hạ tầng máy chủ)</span>
                                                    <ul className={styles.tooltipList}>
                                                        <li>Máy chủ vật lý (Physical) vs <strong>VM</strong> (Virtual Machine) — nền tảng: VMware / Hyper-V / KVM</li>
                                                        <li>OS: Windows Server / Linux / cả hai</li>
                                                        <li>Dịch vụ: <strong>AD</strong> (Active Directory), DNS, DHCP, Web, Database, Mail</li>
                                                        <li><strong>HA</strong> (High Availability) / Clustering / Load Balancer nếu có</li>
                                                    </ul>
                                                </div>
                                                <div className={styles.tooltipSection}>
                                                    <span className={styles.tooltipTag}>🔒 Security Stack (Giải pháp bảo mật)</span>
                                                    <ul className={styles.tooltipList}>
                                                        <li><strong>EDR/XDR</strong> (Endpoint Detection & Response): tên sản phẩm, phạm vi triển khai</li>
                                                        <li><strong>SIEM</strong> (Security Information & Event Management): giải pháp, lưu log bao lâu</li>
                                                        <li><strong>VPN</strong> (Virtual Private Network): IPSec / SSL, ai được dùng</li>
                                                        <li><strong>Backup</strong> (Sao lưu): giải pháp, tần suất, offsite / cloud</li>
                                                        <li><strong>WAF</strong> (Web Application Firewall), <strong>IDS/IPS</strong>, <strong>DLP</strong> (Data Loss Prevention) nếu có</li>
                                                    </ul>
                                                </div>
                                                <div className={styles.tooltipSection}>
                                                    <span className={styles.tooltipTag}>📝 Ví dụ mẫu</span>
                                                    <p className={styles.tooltipExample}>"Mạng chia 5 VLAN: Server (10), User (20), Guest (99), Management (1), DMZ Zone (50). Firewall FortiGate 200F tại biên, block all inbound mặc định. DMZ chứa Web Server Nginx + Mail Gateway. Core Banking trên 2 server Dell R750 HA Cluster, kết nối qua Cisco Catalyst 9300. VPN SSL cho 200 nhân viên remote. Wazuh SIEM thu log toàn bộ server, lưu 12 tháng."</p>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <textarea
                                className={styles.textarea}
                                value={form.network_diagram}
                                onChange={e => set('network_diagram', e.target.value)}
                                placeholder={"Ví dụ:\n- Mạng chia 3 VLAN: Server (10), User (20), WiFi Khách (99)\n- Traffic ra vào đều qua Firewall FortiGate.\n- Server nội bộ không public ra ngoài.\n- Cổng SSH đóng, chỉ truy cập qua VPN nội bộ."}
                                rows={6}
                            />
                        </div>

                        <div className={styles.fieldFull}>
                            <div className={styles.labelWithInfo}>
                                <label>Ghi chú bổ sung (Tùy chọn)</label>
                                <div className={styles.infoWrap}>
                                    <button
                                        type="button"
                                        className={styles.infoIcon}
                                        onClick={() => setActiveTooltip(activeTooltip === 'notes_guide' ? null : 'notes_guide')}
                                        title="Gợi ý ghi chú"
                                    >ⓘ</button>
                                    {activeTooltip === 'notes_guide' && (
                                        <div className={styles.tooltip}>
                                            <div className={styles.tooltipHeader}>
                                                <strong>💡 Gợi ý nội dung ghi chú</strong>
                                                <button type="button" className={styles.tooltipClose} onClick={() => setActiveTooltip(null)}>✕</button>
                                            </div>
                                            <div className={styles.tooltipBody}>
                                                <div className={styles.tooltipSection}>
                                                    <ul className={styles.tooltipList}>
                                                        <li>Sự cố gần đây: <strong>Phishing</strong> (lừa đảo qua email), <strong>Ransomware</strong> (mã độc tống tiền), <strong>Data Leak</strong> (rò rỉ dữ liệu)</li>
                                                        <li>Known vulnerabilities (Lỗ hổng đã biết) nhưng chưa vá</li>
                                                        <li>Compliance yêu cầu đặc thù: <strong>PCI-DSS</strong> (thanh toán thẻ), <strong>HIPAA</strong> (y tế), <strong>SOC 2</strong></li>
                                                        <li>Kế hoạch nâng cấp hạ tầng (Roadmap) sắp tới</li>
                                                        <li>Security budget (Ngân sách ATTT) dự kiến năm nay</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <textarea
                                className={styles.textarea}
                                value={form.notes}
                                onChange={e => set('notes', e.target.value)}
                                placeholder="Bất kỳ thông tin về điểm yếu, rủi ro nào bạn đang lo ngại..."
                                rows={3}
                            />
                        </div>

                        <div className={styles.modelSelectorWrap}>
                            <div className={styles.modelSelectorHeader}>
                                <h4 className={styles.modelSelectorTitle}>Chế độ AI</h4>
                                <button
                                    type="button"
                                    className={styles.infoIcon}
                                    onClick={() => setActiveTooltip(activeTooltip === 'model_info' ? null : 'model_info')}
                                    title="Xem chi tiết luồng xử lý dữ liệu"
                                >ⓘ</button>
                            </div>
                            <div className={styles.modelCompactRow}>
                                {[
                                    { id: 'local', icon: '🔒', label: 'Local Only', badge: 'Bảo mật', badgeColor: styles.modelBadgeSafe },
                                    { id: 'hybrid', icon: '⚡', label: 'Hybrid', badge: 'Khuyên dùng', badgeColor: styles.modelBadgeDefault },
                                    { id: 'cloud', icon: '☁️', label: 'Cloud', badge: 'Chất lượng cao', badgeColor: styles.modelBadgeCloud }
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

                            {activeTooltip === 'model_info' && (
                                <div className={styles.modelDetailPanel}>
                                    <div className={styles.tooltipHeader}>
                                        <strong>🔐 Luồng xử lý dữ liệu theo chế độ AI</strong>
                                        <button type="button" className={styles.tooltipClose} onClick={() => setActiveTooltip(null)}>✕</button>
                                    </div>
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
                                            <p className={styles.modelDetailDesc}>
                                                <strong>Dữ liệu không rời server.</strong> Phase 1 + Phase 2 đều xử lý trên máy cục bộ.
                                                Phù hợp: air-gap, dữ liệu mật, quân sự. Nhược điểm: chậm hơn, báo cáo cơ bản.
                                            </p>
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
                                                <span className={styles.flowStep}>📊 Raw GAP (ẩn danh)</span>
                                                <span className={styles.flowArrow}>→</span>
                                                <span className={`${styles.flowStep} ${styles.flowCloud}`}>☁️ OpenClaude</span>
                                                <span className={styles.flowArrow}>→</span>
                                                <span className={styles.flowStep}>📄 Report</span>
                                            </div>
                                            <p className={styles.modelDetailDesc}>
                                                <strong>Dữ liệu hạ tầng chỉ xử lý local.</strong> Phase 1 phân tích bảo mật cục bộ → kết quả GAP (không chứa IP, config) gửi lên cloud để format báo cáo chuyên nghiệp. Cân bằng bảo mật & chất lượng.
                                            </p>
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
                                            <p className={styles.modelDetailDesc}>
                                                <strong>⚠️ Toàn bộ dữ liệu gửi cloud.</strong> Bao gồm: thông tin hạ tầng, firewall, server, SIEM. Báo cáo chi tiết nhất, tốc độ nhanh. Chỉ dùng khi dữ liệu không nhạy cảm.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className={styles.summaryBox}>
                            <h4>Kiểm tra trước khi đánh giá</h4>
                            <ul>
                                <li>Tiêu chuẩn: <strong>{currentStandard.name}</strong></li>
                                <li>Tổ chức: <strong>{form.org_name || 'Chưa nhập'}</strong></li>
                                <li>Quy mô: <strong>{form.employees} nhân sự</strong> ({form.servers} máy chủ)</li>
                                <li>Phạm vi đánh giá: <strong>
                                    {form.assessment_scope === 'full' ? '🏢 Toàn bộ tổ chức' :
                                     form.assessment_scope === 'by_department' ? `👥 Theo phòng ban${form.scope_description ? ` — ${form.scope_description}` : ''}` :
                                     `🖥️ Theo hệ thống${form.scope_description ? ` — ${form.scope_description}` : ''}`}
                                </strong></li>
                                <li>Mức tuân thủ sơ bộ: <strong>{form.implemented_controls.length}/{totalControls} Controls</strong> ({compliancePercent}%)</li>
                                <li>Chế độ AI: <strong>
                                    {form.model_mode === 'local' ? '🔒 LocalAI Only (SecurityLM)' :
                                     form.model_mode === 'cloud' ? '☁️ Cloud Only (OpenClaude)' :
                                     '⚡ Hybrid (SecurityLM + OpenClaude)'}
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
    }, [tplFilter])

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

    return (
        <div className="page-container">
            <div className={styles.header}>
                <h1 className={styles.title}>Đánh giá An toàn Thông tin</h1>
                <p className={styles.subtitle}>
                    AI Auditor · ISO 27001 · TCVN 11930 · Phân tích GAP & Risk Register tự động
                </p>
            </div>

            <div className={styles.tabs}>
                <button className={`${styles.tab} ${activeTab === 'form' ? styles.tabActive : ''}`} onClick={() => setActiveTab('form')}>
                    Nhập liệu
                </button>
                <button className={`${styles.tab} ${activeTab === 'result' ? styles.tabActive : ''}`} onClick={() => setActiveTab('result')} disabled={!result}>
                    Kết quả {result && !result.error ? '✓' : ''}
                </button>
                <button className={`${styles.tab} ${activeTab === 'history' ? styles.tabActive : ''}`} onClick={() => setActiveTab('history')}>
                    Lịch sử
                </button>
                <button className={`${styles.tab} ${activeTab === 'templates' ? styles.tabActive : ''}`} onClick={() => setActiveTab('templates')}>
                    Mẫu
                </button>
            </div>

            {activeTab === 'form' && (
                <div className={styles.formWrap}>
                    <StepProgress currentStep={step} />
                    {form.org_name && (
                        <div className={styles.draftBanner}>
                            <span className={styles.draftBannerDot} />
                            <span>Draft tự động lưu</span>
                            <button
                                type="button"
                                className={styles.draftClearBtn}
                                onClick={() => { clearDraft(); setForm(EMPTY_FORM); setStep(1) }}
                                title="Xóa draft và bắt đầu lại"
                            >✕ Xóa</button>
                        </div>
                    )}

                    <div className={styles.stepper}>
                        {[1, 2, 3, 4].map((s, idx) => (
                            <div key={s} className={styles.stepGroup}>
                                <div className={`${styles.stepIndicator} ${step === s ? styles.stepCurrent : step > s ? styles.stepCompleted : ''}`}>
                                    <div className={styles.stepCircle}>{step > s ? '✓' : s}</div>
                                    <div className={styles.stepLabel}>
                                        {s === 1 ? 'Tổ chức' : s === 2 ? 'Hạ tầng' : s === 3 ? 'Controls' : 'Mô tả'}
                                    </div>
                                </div>
                                {idx < 3 && <div className={`${styles.stepLine} ${step > s ? styles.stepLineActive : ''}`} />}
                            </div>
                        ))}
                    </div>

                    <div className={styles.stepBanner}>
                        <span className={styles.stepBannerCount}>Bước {step} / 4</span>
                        <span className={styles.stepBannerSep}>—</span>
                        <span className={styles.stepBannerTitle}>
                            {step === 1 ? 'Thông tin Tổ chức & Tiêu chuẩn' :
                             step === 2 ? 'Hạ tầng & Kỹ thuật mạng' :
                             step === 3 ? 'Biện pháp kiểm soát (Controls)' :
                             'Mô tả hệ thống & Tổng kết'}
                        </span>
                    </div>

                    <div className={styles.progressBar}>
                        <div className={styles.progressFill} style={{ width: `${((step - 1) / 3) * 100}%` }} />
                    </div>

                    <div className={styles.stepContainer}>
                        {renderStepContent()}
                    </div>

                    <div className={styles.stepActions}>
                        <button className={styles.btnSecondary} onClick={prevStep} disabled={step === 1 || loading}>
                            <ChevronLeft size={15} style={{ verticalAlign: 'middle' }} /> Quay lại
                        </button>

                        {step < 4 ? (
                            <button className={styles.btnPrimary} onClick={nextStep} disabled={step === 1 && !form.org_name}>
                                Tiếp theo <ChevronRight size={15} style={{ verticalAlign: 'middle' }} />
                            </button>
                        ) : (
                            <button className={styles.btnSubmit} onClick={submit} disabled={loading || !form.org_name}>
                                {loading ? (
                                    <><span className={styles.spinner} /> Đang xử lý ...</>
                                ) : (
                                    <><Shield size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} />Bắt đầu Đánh giá</>
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
                            <h3>Đã có lỗi xảy ra</h3>
                            <p className={styles.errorDetail}>{result.report || 'Timeout hoặc lỗi phân tích.'}</p>
                            {(result.report || '').includes('could not load model') || (result.report || '').includes('rpc error') ? (
                                <div className={styles.errorGuidance}>
                                    <strong>🔧 Nguyên nhân:</strong> LocalAI không load được model (thiếu RAM hoặc model file chưa tải).
                                    <br /><strong>Giải pháp ngay:</strong> Chuyển sang chế độ <strong>Hybrid</strong> hoặc <strong>Cloud</strong> ở Bước 4 → đánh giá lại.
                                </div>
                            ) : (result.report || '').includes('Busy') || (result.report || '').includes('Tạm dừng') ? (
                                <div className={styles.errorGuidance}>
                                    <strong>⏳ Nguyên nhân:</strong> AI đang bận xử lý tác vụ khác (tóm tắt tin tức).
                                    <br /><strong>Giải pháp:</strong> Chờ 1-2 phút rồi thử lại, hoặc chuyển sang chế độ <strong>Hybrid/Cloud</strong>.
                                </div>
                            ) : null}
                            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', flexWrap: 'wrap' }}>
                                <button className={styles.btnSecondary} onClick={() => setActiveTab('form')}>
                                    ← Quay lại chỉnh sửa
                                </button>
                                <button className={styles.btnPrimary} onClick={() => {
                                    set('model_mode', 'hybrid')
                                    setActiveTab('form')
                                    setStep(4)
                                }}>
                                    ⚡ Chuyển sang Hybrid & thử lại
                                </button>
                            </div>
                        </div>
                    ) : (result.status === 'processing' || result.status === 'pending') ? (
                        <div className={styles.processingCard}>
                            <div className={styles.processingSpinner}>
                                <div className={styles.spinnerRing} />
                                <span className={styles.spinnerIcon}>🤖</span>
                            </div>
                            <h3 className={styles.processingTitle}>AI đang phân tích hệ thống...</h3>
                            <div className={styles.processingTabAway}>
                                <span>💡</span>
                                <span>
                                    <strong>Bạn có thể chuyển sang tab khác</strong> — hệ thống xử lý nền,
                                    tự động cập nhật khi xong. Quay lại tab <strong>Lịch sử</strong> để xem kết quả.
                                </span>
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
                                    {result.progress?.message || (result.status === 'pending' ? 'Đang xếp hàng...' : 'Đang khởi động...')}
                                    <span className={styles.processingProgressPct}> {result.progress?.percent || 0}%</span>
                                </span>
                            </div>
                            <p className={styles.processingDesc}>
                                Tổ chức: <strong>{result.org_name || form.org_name || '—'}</strong> ·{' '}
                                {getStdLabel(result.standard || form.assessment_standard)} ·{' '}
                                {form.model_mode === 'local'
                                    ? 'Local AI — thường mất 2–5 phút.'
                                    : form.model_mode === 'hybrid'
                                    ? 'Hybrid — thường mất 1–3 phút.'
                                    : 'Cloud AI — thường mất 30–60 giây.'}
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
                                                <span className={styles.procStepLabel}>RAG Lookup</span>
                                                <span className={styles.procStepDesc}>ChromaDB — {getStdLabel(result.standard || form.assessment_standard).split('(')[0].trim()}</span>
                                            </div>
                                        </div>
                                        <div className={styles.procStep} style={!ragDone ? { opacity: 0.4 } : {}}>
                                            <span className={`${styles.procStepNum} ${p1Active ? styles.procStepNumAnim : ''}`}
                                                style={p1Done ? { background: 'var(--accent-green)', color: '#fff' } : {}}>
                                                {p1Done ? '✓' : '2'}
                                            </span>
                                            <div className={styles.procStepText}>
                                                <span className={styles.procStepLabel}>Phase 1 — SecurityLM</span>
                                                <span className={styles.procStepDesc}>Phân tích GAP theo từng category controls</span>
                                            </div>
                                        </div>
                                        <div className={styles.procStep} style={!p1Done ? { opacity: 0.4 } : {}}>
                                            <span className={`${styles.procStepNum} ${p2Active ? styles.procStepNumAnim : ''}`}>3</span>
                                            <div className={styles.procStepText}>
                                                <span className={styles.procStepLabel}>Phase 2 — {form.model_mode === 'local' ? 'Meta-Llama 8B' : 'OpenClaude'}</span>
                                                <span className={styles.procStepDesc}>Định dạng báo cáo Markdown + Risk Register</span>
                                            </div>
                                        </div>
                                    </>)
                                })()}
                            </div>
                            <div className={styles.pollingInfo} style={{ justifyContent: 'center', marginTop: '0.75rem' }}>
                                <span className={styles.pollingDot} />
                                <span>Tự động kiểm tra mỗi {POLL_INTERVAL/1000} giây · ID: <code style={{fontSize:'0.72rem',opacity:0.7}}>{result.id?.slice(0,8)}</code></span>
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
                                const displayOrg = result.org_name || form.org_name || 'Tổ chức'
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
                                            <span className={styles.scoreUnit}>Tuân thủ</span>
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
                                        {displayPct >= 80 ? '✅ Tuân thủ cao' :
                                         displayPct >= 50 ? '🟡 Tuân thủ một phần' :
                                         displayPct >= 25 ? '🟠 Tuân thủ thấp' :
                                         '🔴 Không tuân thủ'}
                                    </div>
                                    <div className={styles.scoreStats}>
                                        <div className={styles.scoreStat}>
                                            <span className={styles.scoreStatNum}>{implCount}</span>
                                            <span className={styles.scoreStatLabel}>Controls đạt</span>
                                        </div>
                                        <div className={styles.scoreStatDivider} />
                                        <div className={styles.scoreStat}>
                                            <span className={styles.scoreStatNum}>{missingCount}</span>
                                            <span className={styles.scoreStatLabel}>Còn thiếu</span>
                                        </div>
                                        <div className={styles.scoreStatDivider} />
                                        <div className={styles.scoreStat}>
                                            <span className={styles.scoreStatNum}>{totalCount}</span>
                                            <span className={styles.scoreStatLabel}>Tổng controls</span>
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
                                <h4 className={styles.breakdownTitle}>Phân tích theo Category (Weighted)</h4>
                                <div className={styles.breakdownGrid}>
                                    {categoryBreakdown.map((cat, idx) => (
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
                                                <span>{cat.implemented}/{cat.total} controls</span>
                                                <span>{cat.weightScore}/{cat.maxWeightScore} điểm</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {result.json_data && (
                                <div className={styles.jsonDashboard}>
                                    <h4 className={styles.jsonDashTitle}>Dashboard Đánh giá (Structured Data)</h4>
                                    <div className={styles.jsonDashGrid}>
                                        <div className={styles.jsonDashCard}>
                                            <div className={styles.jsonDashCardTitle}>Phân loại Rủi ro</div>
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
                                            <div className={styles.jsonDashCardTitle}>Tuân thủ theo Trọng số</div>
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
                                                <div className={styles.jsonDashCardTitle}>Controls Thiếu Ưu tiên Cao</div>
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
                                            <div className={styles.jsonDashCardTitle}>Export Dữ liệu</div>
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
                                            >📥 Tải JSON</button>
                                            <p className={styles.jsonExportNote}>
                                                Dữ liệu có cấu trúc: compliance %, risk counts, weight breakdown, top gaps.
                                                Dùng để tích hợp dashboard/BI ngoài.
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
                                    Copy report
                                </button>
                                <button className={styles.reportActionBtn} onClick={() => {
                                    // BUG 5 FIX: use server-stored compliance_percent from result
                                    const pdfPct = result.compliance_percent != null
                                        ? parseFloat(result.compliance_percent)
                                        : parseFloat(compliancePercent)
                                    const pdfPctStr = pdfPct.toFixed(1)
                                    const pdfOrg = result.org_name || form.org_name || 'Tổ chức'
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
                                    📄 Xem / Xuất PDF
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
                                        📥 Tải PDF (Server)
                                    </button>
                                )}
                                <button className={styles.reportActionBtn} onClick={() => window.print()}>
                                    🖨️ In báo cáo
                                </button>
                                <button className={styles.reportActionBtnSecondary} onClick={() => setActiveTab('form')}>
                                    ← Đánh giá mới
                                </button>
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
                        <h2 className={styles.sectionTitle}>Lịch sử Báo cáo</h2>
                        <button className={styles.refreshBtn} onClick={fetchHistory}>🔄 Làm mới</button>
                    </div>
                    <p className={styles.helperText}>
                        Hệ thống RAG xử lý ngầm. Báo cáo được lưu trên máy chủ · Tổng: <strong>{assessmentHistory.length}</strong> đánh giá
                    </p>

                    {assessmentHistory.length === 0 ? (
                        <div className={styles.emptyHistory}>
                            Chưa có lịch sử đánh giá nào.<br />
                            <small style={{ opacity: 0.5 }}>Hãy hoàn thành đánh giá đầu tiên từ tab Nhập liệu.</small>
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
                                            Tiêu chuẩn: <strong>{hist.standard}</strong>
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
                                                <span className={styles.histPercentLabel}>tuân thủ</span>
                                            </>
                                        ) : (
                                            <span className={styles.histPercentLabel} style={{ fontSize: '0.7rem', opacity: 0.4 }}>—</span>
                                        )}
                                    </div>
                                    <div className={styles.histAction}>
                                        <span className={`${styles.statusBadge} ${styles[`status_${hist.status}`]}`}>
                                            {hist.status === 'completed' ? '✅ Hoàn thành' :
                                             hist.status === 'failed'    ? '❌ Thất bại' :
                                             hist.status === 'processing'? '⏳ Xử lý...' : '🔄 Chờ'}
                                        </span>
                                        {/* BUG 4 FIX: use loadAssessmentById — fully independent of stale result state */}
                                        {hist.status === 'completed' && hist.id && (
                                            <button className={styles.btnSmall}
                                                onClick={() => loadAssessmentById(hist.id)}>
                                                Xem →
                                            </button>
                                        )}
                                        {(hist.status === 'processing' || hist.status === 'pending') && hist.id && (
                                            <button className={styles.btnSmall}
                                                onClick={() => loadAssessmentById(hist.id)}>
                                                Theo dõi →
                                            </button>
                                        )}
                                        {hist.status === 'failed' && (
                                            <button className={styles.btnSmall}
                                                style={{ color: 'var(--accent-amber,#f59e0b)' }}
                                                onClick={() => { setActiveTab('form'); setStep(4) }}>
                                                Thử lại
                                            </button>
                                        )}
                                        {/* Enhancement 9: delete with inline confirm */}
                                        {hist.id && (
                                            <button
                                                className={styles.btnSmall}
                                                style={{ color: 'var(--accent-red)', opacity: deletingId === hist.id ? 0.5 : 1 }}
                                                disabled={deletingId === hist.id}
                                                onClick={() => {
                                                    if (window.confirm(`Xóa đánh giá của "${hist.org}" (${hist.date})?\nThao tác này không thể hoàn tác.`)) {
                                                        deleteAssessment(hist.id)
                                                    }
                                                }}
                                                title="Xóa đánh giá này"
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
                                Kho Mẫu Hệ thống Thực tế
                            </h2>
                            <p className={styles.helperText}>Dữ liệu kiến trúc mạng, quản lý truy cập và mức tuân thủ của các tổ chức thực tế.</p>
                        </div>
                        <button
                            type="button"
                            className={`${styles.infoIcon} ${styles.tplInfoBtn} ${showTplInfo ? styles.infoIconActive : ''}`}
                            onClick={() => setShowTplInfo(!showTplInfo)}
                            title="Hướng dẫn sử dụng"
                        >ℹ</button>
                    </div>

                    {showTplInfo && (
                        <div className={styles.tplInfoPanel}>
                            <div className={styles.tooltipHeader}>
                                <strong>💡 Kho Mẫu là gì?</strong>
                                <button type="button" className={styles.tooltipClose} onClick={() => setShowTplInfo(false)}>✕</button>
                            </div>
                            <div className={styles.tooltipBody}>
                                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>
                                    Đây là bộ dữ liệu mẫu từ các tổ chức thực tế (ngân hàng, bệnh viện, startup, cơ quan nhà nước...) đã được cấu hình sẵn thông tin hạ tầng và controls tuân thủ.
                                    <br /><br />
                                    <strong>Cách sử dụng:</strong> Chọn một mẫu → Hệ thống tự điền form → Bạn có thể chỉnh sửa thêm → Bấm "Đánh giá" để AI phân tích.
                                    <br /><br />
                                    Phù hợp cho: Demo, đào tạo, benchmark, so sánh mức tuân thủ giữa các loại tổ chức.
                                </p>
                            </div>
                        </div>
                    )}

                    <div className={styles.tplFilterBar}>
                        <button
                            className={`${styles.tplFilterBtn} ${tplFilter === 'all' ? styles.tplFilterActive : ''}`}
                            onClick={() => setTplFilter('all')}
                        >Tất cả ({ASSESSMENT_TEMPLATES.length})</button>
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
                                                <span className={styles.tplStatLabel}>Nhân sự</span>
                                            </div>
                                            <div className={styles.tplStatBox}>
                                                <span className={styles.tplStatNum}>{tpl.data.infrastructure.servers}</span>
                                                <span className={styles.tplStatLabel}>Máy chủ</span>
                                            </div>
                                            <div className={styles.tplStatBox}>
                                                <span className={styles.tplStatNum}>{tpl.data.organization.it_staff}</span>
                                                <span className={styles.tplStatLabel}>IT/Bảo mật</span>
                                            </div>
                                        </div>
                                        <div className={styles.tplComplianceSection}>
                                            <div className={styles.tplComplianceHeader}>
                                                <span className={styles.tplComplianceTitle}>Mức tuân thủ</span>
                                                <span className={styles.tplComplianceValue}>{implemented}/{total} ({percent}%)</span>
                                            </div>
                                            <div className={styles.tplComplianceTrack}>
                                                <div className={styles.tplComplianceFill} style={{ width: `${percent}%` }} />
                                            </div>
                                        </div>
                                    </div>
                                    <div className={styles.tplCardFooter}>
                                        <button className={styles.tplUseBtn} onClick={() => selectTemplate(tpl)}>
                                            Phân tích hệ thống này →
                                        </button>
                                    </div>
                                </div>
                            )
                        })}
                    </div>

                    <div className={styles.tplNavRow}>
                        <button className={styles.btnSecondary} onClick={() => setActiveTab('form')}>← Nhập liệu</button>
                        <Link href="/analytics" className={styles.btnPrimary}>Analytics & Standards →</Link>
                    </div>
                </div>
            )}
            {activeTooltip && (() => {
                const ctrlId = activeTooltip
                if (['topology_guide', 'notes_guide', 'model_info'].includes(ctrlId)) return null
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
                                            {isImplemented ? '✅ Đã triển khai' : '⚠️ Chưa triển khai'}
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
                                                Yêu cầu tiêu chuẩn
                                            </div>
                                            <p className={styles.panelText}>{desc.requirement}</p>
                                        </div>
                                        <div className={styles.panelDivider} />

                                        <div className={styles.panelSection}>
                                            <div className={styles.panelSectionTitle}>
                                                Tiêu chí đánh giá
                                            </div>
                                            <p className={styles.panelText}>{desc.criteria}</p>
                                        </div>
                                        <div className={styles.panelDivider} />

                                        <div className={styles.panelSection}>
                                            <div className={styles.panelSectionTitle}>
                                                Hướng dẫn triển khai
                                            </div>
                                            <p className={styles.panelHint}>{desc.hint ||
                                                (isImplemented
                                                    ? 'Biện pháp này đã được đánh dấu triển khai. Đảm bảo tài liệu bằng chứng được cập nhật và lưu trữ đúng nơi.'
                                                    : 'Biện pháp chưa triển khai. Tham khảo tiêu chí đánh giá và danh sách bằng chứng yêu cầu để lên kế hoạch thực hiện.')
                                            }</p>
                                        </div>
                                        <div className={styles.panelDivider} />

                                        {desc.evidence && desc.evidence.length > 0 && (
                                            <div className={styles.panelSection}>
                                                <div className={styles.panelSectionTitle}>
                                                    Bằng chứng yêu cầu
                                                    <span className={styles.panelEvidenceCount}>{desc.evidence.length} loại tài liệu</span>
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
                                            Chưa có thông tin chi tiết cho control này. Bạn có thể đính kèm bằng chứng triển khai bên dưới.
                                        </p>
                                    </div>
                                )}

                                <div className={styles.panelDivider} />
                                <div className={styles.panelSection}>
                                    <div className={styles.panelSectionTitle}>
                                        Upload bằng chứng triển khai
                                        {ctrlEvidence.length > 0 && (
                                            <span className={styles.panelEvidenceCount}>{ctrlEvidence.length} file đã tải</span>
                                        )}
                                    </div>
                                    <p className={styles.evidenceHelpText}>
                                        Đính kèm file minh chứng (PDF, ảnh, config, log...) cho <strong>{ctrlId}</strong>.
                                        Hỗ trợ kéo-thả nhiều file cùng lúc. Nội dung file sẽ được AI phân tích khi gửi đánh giá.
                                    </p>
                                    <div
                                        className={`${styles.dropZone} ${isDragging ? styles.dropZoneActive : ''}`}
                                        onDragOver={handleDragOver}
                                        onDragLeave={handleDragLeave}
                                        onDrop={handleDrop(ctrlId)}
                                    >
                                        <div className={styles.dropZoneInner}>
                                            {evidenceUploading === ctrlId ? (
                                                <><span className={styles.spinner} /> Đang tải lên...</>
                                            ) : (
                                                <>
                                                    <span className={styles.dropZoneIcon}>📂</span>
                                                    <span className={styles.dropZoneText}>Kéo & thả file vào đây</span>
                                                    <span className={styles.dropZoneOr}>hoặc</span>
                                                    <label className={styles.panelUploadBtn}>
                                                        📎 Chọn file đính kèm
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
                                                                title="Xem nội dung"
                                                                disabled={previewLoading === previewKey}
                                                            >
                                                                {previewLoading === previewKey ? '⏳' : isPreviewOpen ? '👁️' : '👁️'}
                                                            </button>
                                                            <button
                                                                className={styles.evidenceDeleteBtn}
                                                                onClick={() => deleteEvidence(ctrlId, ef.filename)}
                                                                title="Xóa file"
                                                            >✕</button>
                                                        </div>
                                                        {isPreviewOpen && (
                                                            <div className={styles.evidencePreview}>
                                                                {preview.content_type === 'image' ? (
                                                                    <div className={styles.evidencePreviewImage}>
                                                                        <a href={preview.download_url} target="_blank" rel="noopener noreferrer">
                                                                            🖼️ Xem ảnh gốc ({Math.round(preview.size_bytes/1024)}KB)
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
                                    {isImplemented ? '✖ Bỏ đánh dấu triển khai' : '✔ Đánh dấu đã triển khai'}
                                </button>
                            </div>
                        </div>
                    </>
                )
            })()}
        </div>
    )
}
