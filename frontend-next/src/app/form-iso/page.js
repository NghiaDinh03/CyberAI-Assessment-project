'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import styles from './page.module.css'
import { calcWeightedScore, mergeCustomStandard } from '../../data/standards'
import { useControlDescriptions, useAssessmentStandards } from '../../data'
import StepProgress from '@/components/StepProgress'
import { useTranslation } from '@/components/LanguageProvider'
import { Shield, ChevronRight, ChevronLeft, ArrowDown } from 'lucide-react'

import Step1Org from './_components/steps/Step1Org'
import Step2Infra from './_components/steps/Step2Infra'
import Step3Controls from './_components/steps/Step3Controls'
import Step4Review from './_components/steps/Step4Review'
import ResultView from './_components/views/ResultView'
import HistoryView from './_components/views/HistoryView'
import TemplatesView from './_components/views/TemplatesView'
import DetailDrawer from './_components/controls/DetailDrawer'
import EvidencePreviewModal from './_components/controls/EvidencePreviewModal'

const POLL_INTERVAL = 8000
const FORM_DRAFT_KEY = 'form-iso-draft'

const STANDARD_LABEL_MAP = {
    iso27001: 'ISO 27001:2022',
    tcvn11930: 'TCVN 11930:2017',
    nd13: 'Nghị định 13/2023',
    nist_csf: 'NIST CSF 2.0',
    pci_dss: 'PCI DSS 4.0',
    hipaa: 'HIPAA Security Rule',
    gdpr: 'GDPR',
    soc2: 'SOC 2',
}
const getStdLabel = (stdId) => STANDARD_LABEL_MAP[stdId] || stdId || 'ISO 27001:2022'

const EMPTY_FORM = {
    org_name: '',
    org_size: 'medium',
    industry: '',
    iso_status: 'planning',
    servers: 1,
    cloud_provider: '',
    firewalls: '',
    antivirus: '',
    backup_solution: '',
    siem: '',
    incidents_12m: 0,
    vpn: false,
    assessment_standard: 'iso27001',
    implemented_controls: [],
    notes: '',
    assessment_scope: 'full',
    scope_description: '',
    model_mode: 'local'
}

export default function FormISOPage() {
    const router = useRouter()
    const { t, locale } = useTranslation()
    const CONTROL_DESCRIPTIONS = useControlDescriptions()
    const availableStandards = useAssessmentStandards()

    const [dynamicTemplates, setDynamicTemplates] = useState([])
    const [templatesLoading, setTemplatesLoading] = useState(false)
    const [step, setStep] = useState(1)
    const [form, setForm] = useState(EMPTY_FORM)
    const [result, setResult] = useState(null)
    const [loading, setLoading] = useState(false)
    const [activeTab, setActiveTab] = useState('form')
    const [assessmentHistory, setAssessmentHistory] = useState([])
    const [expandedCategory, setExpandedCategory] = useState(null)
    const [activeTooltip, setActiveTooltip] = useState(null)
    const [customDescriptions, setCustomDescriptions] = useState({})
    const [standardsLoading, setStandardsLoading] = useState(false)
    const [evidenceMap, setEvidenceMap] = useState({})
    const [evidenceUploading, setEvidenceUploading] = useState(null)
    const [evidencePreviews, setEvidencePreviews] = useState({})
    const [previewLoading, setPreviewLoading] = useState(null)
    const [deletingId, setDeletingId] = useState(null)

    const [drawerControlId, setDrawerControlId] = useState(null)
    const [controlNotes, setControlNotes] = useState({})
    const drawerReturnFocusRef = useRef(null)

    const [previewFile, setPreviewFile] = useState(null)
    const previewReturnFocusRef = useRef(null)

    const [tplFilter, setTplFilter] = useState('all')
    const [showTplInfo, setShowTplInfo] = useState(false)

    const [controlSearch, setControlSearch] = useState('')
    const [filterTag, setFilterTag] = useState('all')
    const [expandAllCategories, setExpandAllCategories] = useState(false)
    const [selectedAiModel, setSelectedAiModel] = useState('gemma4:latest')
    const [showScrollBottom, setShowScrollBottom] = useState(false)

    const [batchUploading, setBatchUploading] = useState(false)
    const [batchResultMsg, setBatchResultMsg] = useState(null)
    const [detectedHosts, setDetectedHosts] = useState([])
    const batchFileInputRef = useRef(null)

    const pollingRef = useRef(null)
    const pollingIdRef = useRef(null)

    const STEP_TITLES = [
        t('assessment.step1Title'),
        t('assessment.step2Title'),
        t('assessment.step3Title'),
        t('assessment.step4Title')
    ]

    useEffect(() => {
        if (activeTab !== 'result') {
            setShowScrollBottom(false)
            return
        }
        const handleScroll = () => {
            const distanceToBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY
            setShowScrollBottom(distanceToBottom > 250)
        }
        window.addEventListener('scroll', handleScroll, { passive: true })
        return () => window.removeEventListener('scroll', handleScroll)
    }, [activeTab])

    const fetchTemplates = useCallback(async () => {
        try {
            setTemplatesLoading(true)
            const res = await fetch('/api/templates')
            if (res.ok) {
                const data = await res.json()
                if (data.templates && Array.isArray(data.templates)) {
                    setDynamicTemplates(data.templates)
                }
            }
        } catch (e) {
            console.warn('Failed to fetch templates:', e)
        } finally {
            setTemplatesLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchTemplates()
    }, [fetchTemplates])

    const selectTemplate = useCallback((tpl) => {
        if (!tpl) return
        const d = tpl.data || {}
        const std = tpl.standard || d.assessment_standard || 'iso27001'
        const orgInfo = d.organization || {}
        const infraInfo = d.infrastructure || {}
        const complianceInfo = d.compliance || {}

        setForm({
            assessment_standard: std,
            org_name: d.org_name || orgInfo.name || tpl.name || '',
            org_size: d.org_size || orgInfo.size || 'medium',
            industry: d.industry || orgInfo.industry || tpl.industry || '',
            iso_status: d.iso_status || orgInfo.iso_status || 'Đang triển khai',
            employees: d.employees || orgInfo.employees || 0,
            it_staff: d.it_staff || orgInfo.it_staff || 0,
            servers: d.servers || infraInfo.servers || 0,
            firewalls: d.firewalls || infraInfo.firewalls || '',
            cloud_provider: d.cloud_provider || infraInfo.cloud || '',
            antivirus: d.antivirus || infraInfo.antivirus || '',
            backup_solution: d.backup_solution || infraInfo.backup || '',
            siem: d.siem || infraInfo.siem || '',
            vpn: d.vpn !== undefined ? d.vpn : (infraInfo.vpn !== undefined ? infraInfo.vpn : false),
            incidents_12m: d.incidents_12m || infraInfo.incidents_12m || 0,
            network_diagram: d.network_diagram || infraInfo.network_topology || '',
            notes: d.notes || '',
            assessment_scope: d.assessment_scope || 'full',
            scope_description: d.scope_description || '',
            model_mode: 'local',
            implemented_controls: d.implemented_controls || complianceInfo.implemented_controls || []
        })

        if (d.evidence_map && typeof d.evidence_map === 'object') {
            setEvidenceMap(d.evidence_map)
        }

        setActiveTab('form')
        setStep(1)
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }, [])

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
            } catch (e) {
                console.error('Evidence upload failed:', e)
            }
        }
        setEvidenceUploading(null)
    }

    const fetchPreview = async (controlId, filename) => {
        const key = `${controlId}__${filename}`
        if (evidencePreviews[key]) return
        setPreviewLoading(key)
        try {
            const res = await fetch(`/api/iso27001/evidence/${controlId}/${filename}/preview`)
            if (res.ok) {
                const data = await res.json()
                setEvidencePreviews(prev => ({ ...prev, [key]: data }))
            }
        } catch (_) { }
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
        } catch (_) { }
    }

    const handleBatchEvidenceUpload = async (files) => {
        if (!files || files.length === 0) return
        setBatchUploading(true)
        setBatchResultMsg(null)
        const formData = new FormData()
        Array.from(files).forEach(f => formData.append('files', f))

        try {
            const savedToken = typeof window !== 'undefined' ? localStorage.getItem('cyberai_auth_token') : null
            const headers = {}
            if (savedToken) {
                headers['Authorization'] = `Bearer ${savedToken}`
            }

            const res = await fetch('/api/iso27001/evidence/batch-ingest', {
                method: 'POST',
                headers,
                body: formData
            })

            const data = await res.json().catch(() => ({}))

            if (res.ok && data.status === 'success') {
                const mapped = data.mapped_controls || {}
                const suggestedControls = data.suggested_implemented_controls || []
                const hosts = data.detected_hosts || []

                setForm(prev => {
                    const mergedControls = Array.from(new Set([...prev.implemented_controls, ...suggestedControls]))
                    const newServersCount = hosts.length > 0 ? Math.max(prev.servers, hosts.length) : prev.servers
                    return {
                        ...prev,
                        implemented_controls: mergedControls,
                        servers: newServersCount
                    }
                })

                setEvidenceMap(prev => {
                    const next = { ...prev }
                    Object.entries(mapped).forEach(([ctrlId, fileList]) => {
                        const existing = next[ctrlId] || []
                        const newFiles = fileList.map(f => ({
                            filename: f.filename,
                            size_bytes: f.size_bytes,
                            confidence: f.confidence
                        }))
                        next[ctrlId] = [...existing, ...newFiles]
                    })
                    return next
                })

                if (hosts.length > 0) {
                    setDetectedHosts(hosts)
                }

                setBatchResultMsg({
                    type: 'success',
                    text: locale === 'vi'
                        ? `🎉 Tự động bóc tách thành công ${data.summary?.processed_successfully || files.length} tệp! Đã nhận diện ${hosts.length} máy chủ và tự động tick ${suggestedControls.length} biện pháp kiểm soát phù hợp.`
                        : `🎉 Successfully parsed ${data.summary?.processed_successfully || files.length} files! Detected ${hosts.length} hosts and auto-checked ${suggestedControls.length} matching controls.`
                })
            } else {
                let errMsg = (locale === 'vi' ? 'Lỗi khi xử lý hàng loạt tệp bằng chứng.' : 'Error processing batch evidence files.')
                if (typeof data.detail === 'string') errMsg = data.detail
                else if (typeof data.message === 'string') errMsg = data.message
                setBatchResultMsg({ type: 'error', text: errMsg })
            }
        } catch (err) {
            console.error('Batch ingest error:', err)
            setBatchResultMsg({
                type: 'error',
                text: locale === 'vi' ? 'Không thể kết nối đến máy chủ để bóc tách tệp.' : 'Could not connect to server for batch processing.'
            })
        } finally {
            setBatchUploading(false)
        }
    }

    const deleteEvidence = async (controlId, filename) => {
        try {
            await fetch(`/api/iso27001/evidence/${controlId}/${filename}`, { method: 'DELETE' })
            setEvidenceMap(prev => ({
                ...prev,
                [controlId]: (prev[controlId] || []).filter(f => f.filename !== filename)
            }))
        } catch (e) {
            console.error('Evidence delete failed:', e)
        }
    }

    useEffect(() => {
        try {
            localStorage.setItem(FORM_DRAFT_KEY, JSON.stringify(form))
        } catch (_) { }
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
        return availableStandards?.find(s => s.id === form.assessment_standard) || availableStandards?.[0] || { id: 'iso27001', name: 'ISO 27001:2022', controls: [] }
    }, [form.assessment_standard, availableStandards])

    const totalControls = useMemo(() => {
        return currentStandard?.controls?.reduce((acc, cat) => acc + (cat?.controls?.length || 0), 0) || 0
    }, [currentStandard])

    const weightedScore = useMemo(() => {
        return calcWeightedScore(form.implemented_controls, currentStandard?.controls || [])
    }, [form.implemented_controls, currentStandard])

    const compliancePercent = weightedScore.percent

    const allControls = useMemo(() => {
        return (currentStandard?.controls || []).flatMap(c => c.controls || [])
    }, [currentStandard])

    const riskStats = useMemo(() => {
        const stats = {
            critical: { total: 0, done: 0 },
            high: { total: 0, done: 0 },
            medium: { total: 0, done: 0 },
            low: { total: 0, done: 0 },
            missingEvidence: 0,
            implementedTotal: form.implemented_controls.length
        }

        allControls.forEach(ctrl => {
            const w = ctrl.weight || 'medium'
            if (stats[w]) stats[w].total += 1
            const isDone = form.implemented_controls.includes(ctrl.id)
            if (isDone && stats[w]) stats[w].done += 1
            const evCount = (evidenceMap[ctrl.id] || []).length
            if (evCount === 0) stats.missingEvidence += 1
        })

        return stats
    }, [allControls, form.implemented_controls, evidenceMap])

    const applyTemplateData = (parsed) => {
        const isNested = Boolean(parsed.organization || parsed.infrastructure || parsed.compliance)
        return {
            assessment_standard: parsed.assessment_standard || parsed.standard || 'iso27001',
            org_name: isNested ? (parsed.organization?.name || '') : (parsed.org_name || ''),
            org_size: isNested ? (parsed.organization?.size || 'medium') : (parsed.org_size || 'medium'),
            industry: isNested ? (parsed.organization?.industry || '') : (parsed.industry || ''),
            employees: isNested ? (parsed.organization?.employees || 0) : (parsed.employees || 0),
            it_staff: isNested ? (parsed.organization?.it_staff || 0) : (parsed.it_staff || 0),
            servers: isNested ? (parsed.infrastructure?.servers || 0) : (parsed.servers || 0),
            firewalls: isNested ? (parsed.infrastructure?.firewalls || '') : (parsed.firewalls || ''),
            vpn: isNested ? (parsed.infrastructure?.vpn || false) : (parsed.vpn || false),
            cloud_provider: isNested ? (parsed.infrastructure?.cloud_provider || '') : (parsed.cloud_provider || ''),
            antivirus: isNested ? (parsed.infrastructure?.antivirus || '') : (parsed.antivirus || ''),
            backup_solution: isNested ? (parsed.infrastructure?.backup_solution || '') : (parsed.backup_solution || ''),
            siem: isNested ? (parsed.infrastructure?.siem || '') : (parsed.siem || ''),
            incidents_12m: isNested ? (parsed.infrastructure?.incidents_12m || 0) : (parsed.incidents_12m || 0),
            iso_status: isNested ? (parsed.compliance?.iso_status || 'Chưa triển khai') : (parsed.iso_status || 'Chưa triển khai'),
            implemented_controls: isNested ? (parsed.compliance?.implemented_controls || []) : (parsed.implemented_controls || []),
            notes: parsed.notes || '',
            assessment_scope: parsed.assessment_scope || 'full',
            scope_description: parsed.scope_description || '',
            model_mode: 'local'
        }
    }

    useEffect(() => {
        const reuseData = localStorage.getItem('reuse_iso_form')
        if (reuseData) {
            try {
                const parsed = JSON.parse(reuseData)
                setForm(applyTemplateData(parsed))
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
            } catch (_) { }
        }

        fetchHistory()
    }, [])

    const fetchHistory = useCallback(async () => {
        try {
            const res = await fetch('/api/iso27001/assessments?page_size=50')
            if (!res.ok) return
            const payload = await res.json()
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
            try {
                const saved = localStorage.getItem('assessment_history')
                if (saved) setAssessmentHistory(JSON.parse(saved))
            } catch (__) { }
        }
    }, [])

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
                        compliance_percent: data.compliance_percent ?? null,
                        standard: data.standard || data.system_info?.assessment_standard,
                        org_name: data.system_info?.organization?.name || '',
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

        poll()
        pollingRef.current = setInterval(poll, POLL_INTERVAL)
    }, [stopPolling, fetchHistory])

    useEffect(() => () => stopPolling(), [stopPolling])

    useEffect(() => {
        if (result?.id && (result.status === 'processing' || result.status === 'pending')) {
            startPolling(result.id)
        } else {
            stopPolling()
        }
    }, [result?.id, result?.status])

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
        try { localStorage.removeItem(FORM_DRAFT_KEY) } catch (_) { }
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
                model_mode: 'local',
                selected_model: selectedAiModel || 'gemma4:latest',
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
                    compliance_percent: data.compliance_percent ?? null,
                    standard: data.standard || data.system_info?.assessment_standard,
                    org_name: data.system_info?.organization?.name || '',
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
    }, [startPolling])

    const deleteAssessment = useCallback(async (id) => {
        if (!id) return
        setDeletingId(id)
        try {
            const res = await fetch(`/api/iso27001/assessments/${id}`, { method: 'DELETE' })
            if (res.ok) {
                setAssessmentHistory(prev => prev.filter(h => h.id !== id))
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
                    <Step1Org
                        form={form}
                        set={set}
                        handleStandardChange={handleStandardChange}
                        availableStandards={availableStandards}
                        standardsLoading={standardsLoading}
                        activeTooltip={activeTooltip}
                        setActiveTooltip={setActiveTooltip}
                    />
                )
            case 2:
                return (
                    <Step2Infra
                        form={form}
                        set={set}
                    />
                )
            case 3:
                return (
                    <Step3Controls
                        form={form}
                        currentStandard={currentStandard}
                        totalControls={totalControls}
                        compliancePercent={compliancePercent}
                        riskStats={riskStats}
                        allControls={allControls}
                        batchFileInputRef={batchFileInputRef}
                        batchUploading={batchUploading}
                        handleBatchEvidenceUpload={handleBatchEvidenceUpload}
                        batchResultMsg={batchResultMsg}
                        detectedHosts={detectedHosts}
                        controlSearch={controlSearch}
                        setControlSearch={setControlSearch}
                        filterTag={filterTag}
                        setFilterTag={setFilterTag}
                        expandAllCategories={expandAllCategories}
                        setExpandAllCategories={setExpandAllCategories}
                        expandedCategory={expandedCategory}
                        setExpandedCategory={setExpandedCategory}
                        toggleCategoryAll={toggleCategoryAll}
                        toggleControl={toggleControl}
                        drawerReturnFocusRef={drawerReturnFocusRef}
                        setDrawerControlId={setDrawerControlId}
                        fetchEvidenceForControl={fetchEvidenceForControl}
                        evidenceMap={evidenceMap}
                    />
                )
            case 4:
                return (
                    <Step4Review
                        form={form}
                        set={set}
                        currentStandard={currentStandard}
                        totalControls={totalControls}
                        compliancePercent={compliancePercent}
                        activeTooltip={activeTooltip}
                        setActiveTooltip={setActiveTooltip}
                    />
                )
            default:
                return null
        }
    }

    return (
        <div className={styles.page}>
            <header className={styles.header}>
                <div className={styles.headerLeft}>
                    <h1 className={styles.title}>{t('assessment.pageTitle')}</h1>
                    <p className={styles.subtitle}>{t('assessment.pageSubtitle')}</p>
                </div>
                <div className={styles.headerActions}>
                    <button
                        className={`${styles.tabBtn} ${activeTab === 'templates' ? styles.activeTab : ''}`}
                        onClick={() => setActiveTab('templates')}
                    >
                        📚 {t('assessment.tabTemplates')}
                    </button>
                    <button
                        className={`${styles.tabBtn} ${activeTab === 'form' ? styles.activeTab : ''}`}
                        onClick={() => setActiveTab('form')}
                    >
                        📝 {t('assessment.tabForm')}
                    </button>
                    {result && (
                        <button
                            className={`${styles.tabBtn} ${activeTab === 'result' ? styles.activeTab : ''}`}
                            onClick={() => setActiveTab('result')}
                        >
                            📊 {t('assessment.tabResult')}
                            {(result.status === 'processing' || result.status === 'pending') && (
                                <span className={styles.tabBadge}>...</span>
                            )}
                        </button>
                    )}
                    <button
                        className={`${styles.tabBtn} ${activeTab === 'history' ? styles.activeTab : ''}`}
                        onClick={() => { setActiveTab('history'); fetchHistory() }}
                    >
                        📋 {t('assessment.tabHistory')}
                        {assessmentHistory.length > 0 && (
                            <span className={styles.tabBadge}>{assessmentHistory.length}</span>
                        )}
                    </button>
                </div>
            </header>

            {activeTab === 'form' && (
                <div className={styles.formContainer}>
                    <StepProgress
                        steps={STEP_TITLES}
                        currentStep={step}
                        onStepClick={(i) => setStep(i)}
                    />

                    {step === 1 && (
                        <div className={styles.templatePromoBanner}>
                            <div className={styles.templatePromoContent}>
                                <span className={styles.templatePromoIcon}>⚡</span>
                                <div>
                                    <strong>{t('assessment.quickTemplate')}</strong>
                                    <span>{t('assessment.quickTemplateDesc')}</span>
                                </div>
                            </div>
                            <button
                                type="button"
                                className={styles.templatePromoBtn}
                                onClick={() => setActiveTab('templates')}
                            >
                                {t('assessment.viewTemplates')}
                            </button>
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

            {activeTab === 'result' && (
                <div className={styles.resultContainer}>
                    <ResultView
                        result={result}
                        form={form}
                        availableStandards={availableStandards}
                        currentStandard={currentStandard}
                        getStdLabel={getStdLabel}
                        set={set}
                        setActiveTab={setActiveTab}
                        setStep={setStep}
                        loading={loading}
                        submit={submit}
                        setSelectedAiModel={setSelectedAiModel}
                    />
                </div>
            )}

            {activeTab === 'history' && (
                <HistoryView
                    assessmentHistory={assessmentHistory}
                    fetchHistory={fetchHistory}
                    loadAssessmentById={loadAssessmentById}
                    deleteAssessment={deleteAssessment}
                    deletingId={deletingId}
                    setActiveTab={setActiveTab}
                    setStep={setStep}
                />
            )}

            {activeTab === 'templates' && (
                <TemplatesView
                    dynamicTemplates={dynamicTemplates}
                    templatesLoading={templatesLoading}
                    tplFilter={tplFilter}
                    setTplFilter={setTplFilter}
                    showTplInfo={showTplInfo}
                    setShowTplInfo={setShowTplInfo}
                    getStdLabel={getStdLabel}
                    selectTemplate={selectTemplate}
                    setActiveTab={setActiveTab}
                />
            )}

            {/* Control Detail Drawer */}
            <DetailDrawer
                open={Boolean(drawerControlId)}
                control={(() => {
                    if (!drawerControlId) return null
                    for (const cat of currentStandard?.controls || []) {
                        const found = (cat?.controls || []).find(c => c.id === drawerControlId)
                        if (found) return found
                    }
                    return { id: drawerControlId, label: drawerControlId, weight: 'medium' }
                })()}
                state={{
                    implemented: form.implemented_controls.includes(drawerControlId),
                    evidenceFiles: evidenceMap[drawerControlId] || [],
                    notes: controlNotes[drawerControlId] || '',
                    description: allDescriptions[drawerControlId] || {}
                }}
                onClose={() => {
                    setDrawerControlId(null)
                    drawerReturnFocusRef.current?.focus?.()
                }}
                onToggleImplemented={toggleControl}
                onUploadFiles={uploadEvidence}
                onDeleteFile={deleteEvidence}
                onChangeNotes={(ctrlId, note) => setControlNotes(prev => ({ ...prev, [ctrlId]: note }))}
                onExpandFile={(ctrlId, fn) => {
                    setPreviewFile({ controlId: ctrlId, filename: fn })
                    fetchPreview(ctrlId, fn)
                }}
                returnFocusRef={drawerReturnFocusRef}
                standard={form.assessment_standard}
                selectedModel={selectedAiModel}
            />

            {/* Evidence Preview Modal */}
            <EvidencePreviewModal
                isOpen={Boolean(previewFile)}
                previewFile={previewFile}
                previewData={previewFile ? evidencePreviews[`${previewFile.controlId}__${previewFile.filename}`] : null}
                isLoading={Boolean(previewLoading)}
                onClose={() => {
                    setPreviewFile(null)
                    previewReturnFocusRef.current?.focus?.()
                }}
            />

            {showScrollBottom && (
                <button
                    type="button"
                    className={styles.fabScrollBottom}
                    onClick={() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })}
                    title={locale === 'vi' ? 'Cuộn xuống cuối trang' : 'Scroll to bottom'}
                    aria-label="Scroll to bottom"
                >
                    <ArrowDown size={18} />
                </button>
            )}
        </div>
    )
}
