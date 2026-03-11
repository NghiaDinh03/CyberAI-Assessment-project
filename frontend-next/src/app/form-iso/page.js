'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Link from 'next/link'
import styles from './page.module.css'
import { ASSESSMENT_STANDARDS } from '../../data/standards'
import { CONTROL_DESCRIPTIONS } from '../../data/controlDescriptions'

const POLL_INTERVAL = 10000

export default function FormISOPage() {
    const [step, setStep] = useState(1)
    const [form, setForm] = useState({
        assessment_standard: 'iso27001',
        org_name: '', org_size: '', industry: '',
        employees: 0, it_staff: 0,
        servers: 0, firewalls: '', vpn: false,
        cloud_provider: '', antivirus: '', backup_solution: '',
        siem: '', network_diagram: '',
        implemented_controls: [],
        incidents_12m: 0, iso_status: '', notes: ''
    })
    const [result, setResult] = useState(null)
    const [loading, setLoading] = useState(false)
    const [activeTab, setActiveTab] = useState('form')
    const [assessmentHistory, setAssessmentHistory] = useState([])
    const [expandedCategory, setExpandedCategory] = useState(null)
    const [activeTooltip, setActiveTooltip] = useState(null)

    const currentStandard = useMemo(() => {
        return ASSESSMENT_STANDARDS.find(s => s.id === form.assessment_standard) || ASSESSMENT_STANDARDS[0]
    }, [form.assessment_standard])

    const totalControls = useMemo(() => {
        return currentStandard.controls.reduce((acc, cat) => acc + cat.controls.length, 0)
    }, [currentStandard])

    const compliancePercent = useMemo(() => {
        if (totalControls === 0) return 0
        return ((form.implemented_controls.length / totalControls) * 100).toFixed(1)
    }, [form.implemented_controls.length, totalControls])

    // Load template data from localStorage & fetch server history
    useEffect(() => {
        const reuseData = localStorage.getItem('reuse_iso_form')
        if (reuseData) {
            try {
                const parsed = JSON.parse(reuseData)
                if (parsed.organization) {
                    setForm({
                        assessment_standard: parsed.assessment_standard || 'iso27001',
                        org_name: parsed.organization.name || '',
                        org_size: parsed.organization.size || '',
                        industry: parsed.organization.industry || '',
                        employees: parsed.organization.employees || 0,
                        it_staff: parsed.organization.it_staff || 0,
                        servers: parsed.infrastructure?.servers || 0,
                        firewalls: parsed.infrastructure?.firewalls || '',
                        vpn: parsed.infrastructure?.vpn === 'Có',
                        cloud_provider: parsed.infrastructure?.cloud || '',
                        antivirus: parsed.infrastructure?.antivirus || '',
                        backup_solution: parsed.infrastructure?.backup || '',
                        siem: parsed.infrastructure?.siem || '',
                        network_diagram: parsed.infrastructure?.network_diagram || '',
                        implemented_controls: parsed.compliance?.implemented_controls || [],
                        incidents_12m: parsed.compliance?.incidents_12m || 0,
                        iso_status: parsed.compliance?.iso_status || '',
                        notes: parsed.notes || ''
                    })
                }
                localStorage.removeItem('reuse_iso_form')
            } catch (e) {
                console.error('Failed to parse reuse data:', e)
            }
        }

        fetchHistory()
    }, [])

    const fetchHistory = async () => {
        try {
            const res = await fetch('/api/iso27001/assessments')
            if (res.ok) {
                const serverHistory = await res.json()
                const mapped = serverHistory.map(h => ({
                    id: h.id,
                    date: new Date(h.created_at).toLocaleDateString('vi-VN') + ' ' + new Date(h.created_at).toLocaleTimeString('vi-VN'),
                    org: h.org_name,
                    standard: h.standard === 'tcvn11930' ? 'TCVN 11930:2017' : 'ISO 27001:2022',
                    status: h.status
                }))
                setAssessmentHistory(mapped)
            }
        } catch (e) {
            // Fallback to localStorage
            const saved = localStorage.getItem('assessment_history')
            if (saved) {
                try { setAssessmentHistory(JSON.parse(saved)) } catch (_) { }
            }
        }
    }

    // Auto-poll when result is processing
    useEffect(() => {
        if (!result || result.status !== 'processing') return
        const timer = setInterval(() => refreshStatus(), POLL_INTERVAL)
        return () => clearInterval(timer)
    }, [result])

    const set = (key, val) => setForm(p => ({ ...p, [key]: val }))

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

    const submit = async () => {
        setLoading(true)
        setResult(null)
        try {
            const res = await fetch('/api/iso27001/assess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form)
            })
            const data = await res.json()
            if (data.status === 'accepted') {
                setResult({
                    id: data.id,
                    status: 'processing',
                    report: 'Hệ thống đã tiếp nhận yêu cầu. Model RAG đang phân tích dữ liệu.\n\nBạn có thể sang tab khác, sau đó quay lại tab **Lịch sử** để xem báo cáo khi hoàn thành.'
                })
                setActiveTab('result')
                fetchHistory()
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

    const refreshStatus = useCallback(async (idToRefresh = null) => {
        const targetId = idToRefresh || (result && result.id)
        if (!targetId) return

        try {
            const res = await fetch(`/api/iso27001/assessments/${targetId}`)
            const data = await res.json()
            if (data.status === 'completed' || data.status === 'failed') {
                setResult({
                    id: data.id,
                    status: data.status,
                    report: data.result?.report || data.error,
                    model_used: data.result?.model_used
                })
                setActiveTab('result')
                fetchHistory()
            }
        } catch (e) {
            console.error('Failed to refresh status:', e)
        }
    }, [result])

    const renderStepContent = () => {
        switch (step) {
            case 1:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>
                            <span className={styles.sectionIcon}>🏢</span>
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
                                    {ASSESSMENT_STANDARDS.map(s => (
                                        <option key={s.id} value={s.id}>{s.name}</option>
                                    ))}
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
                        </div>
                    </div>
                )
            case 2:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>
                            <span className={styles.sectionIcon}>🖥️</span>
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
                                    <span className={styles.sectionIcon}>🛡️</span>
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
                                                        const desc = CONTROL_DESCRIPTIONS[ctrl.id]
                                                        return (
                                                            <div key={ctrl.id} className={`${styles.controlItem} ${form.implemented_controls.includes(ctrl.id) ? styles.controlActive : ''}`}>
                                                                <label className={styles.controlLabel}>
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={form.implemented_controls.includes(ctrl.id)}
                                                                        onChange={() => toggleControl(ctrl.id)}
                                                                    />
                                                                    <div className={styles.ctrlText}>
                                                                        <span className={styles.ctrlId}>{ctrl.id}</span>
                                                                        <span className={styles.ctrlLabel}>{ctrl.label}</span>
                                                                    </div>
                                                                </label>
                                                                {desc && (
                                                                    <button
                                                                        type="button"
                                                                        className={`${styles.infoIcon} ${activeTooltip === ctrl.id ? styles.infoIconActive : ''}`}
                                                                        onClick={(e) => { e.stopPropagation(); setActiveTooltip(activeTooltip === ctrl.id ? null : ctrl.id) }}
                                                                        title="Xem chi tiết"
                                                                    >ⓘ</button>
                                                                )}
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
                            <span className={styles.sectionIcon}>📐</span>
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
                                                <p className={styles.tooltipNote}>Hệ thống hiện chưa hỗ trợ đọc dữ liệu từ hình ảnh / file đính kèm. Vui lòng <strong>mô tả bằng văn bản</strong> theo gợi ý sau:</p>
                                                <div className={styles.tooltipSection}>
                                                    <span className={styles.tooltipTag}>🌐 Kiến trúc mạng</span>
                                                    <ul className={styles.tooltipList}>
                                                        <li>Số lượng VLAN và mục đích (Server, User, Guest, Management)</li>
                                                        <li>Vùng DMZ: có hay không, chứa những dịch vụ gì (Web, Mail, DNS)</li>
                                                        <li>Firewall model và vị trí (biên, giữa các zone)</li>
                                                        <li>Kết nối Internet: bao nhiêu ISP, có load balancing không</li>
                                                    </ul>
                                                </div>
                                                <div className={styles.tooltipSection}>
                                                    <span className={styles.tooltipTag}>🖥️ Hệ thống máy chủ</span>
                                                    <ul className={styles.tooltipList}>
                                                        <li>Máy chủ vật lý vs VM (số lượng, nền tảng ảo hóa)</li>
                                                        <li>Hệ điều hành: Windows Server / Linux / cả hai</li>
                                                        <li>Dịch vụ chạy: AD, DNS, DHCP, Web, Database, Mail</li>
                                                        <li>Cơ chế High Availability / Clustering nếu có</li>
                                                    </ul>
                                                </div>
                                                <div className={styles.tooltipSection}>
                                                    <span className={styles.tooltipTag}>🔒 Giải pháp bảo mật</span>
                                                    <ul className={styles.tooltipList}>
                                                        <li>EDR/Antivirus: tên sản phẩm, phạm vi triển khai</li>
                                                        <li>SIEM/Log: giải pháp nào, lưu trữ bao lâu</li>
                                                        <li>VPN: loại nào (IPSec/SSL), ai được dùng</li>
                                                        <li>Backup: giải pháp, tần suất, có offsite không</li>
                                                        <li>WAF, IDS/IPS, DLP nếu có</li>
                                                    </ul>
                                                </div>
                                                <div className={styles.tooltipSection}>
                                                    <span className={styles.tooltipTag}>📝 Ví dụ mẫu</span>
                                                    <p className={styles.tooltipExample}>"Mạng chia 5 VLAN: Server (10), User (20), Guest (99), Management (1), DMZ (50). Firewall FortiGate 200F đặt tại biên, chặn mặc định tất cả inbound. DMZ chứa Web Server (Nginx) và Mail Gateway. Core Banking chạy trên 2 server Dell R750 cluster HA, kết nối qua switch Cisco 9300. VPN SSL cho 200 nhân viên remote. Wazuh SIEM thu log từ tất cả server, lưu 12 tháng."</p>
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
                                                        <li>Sự cố an ninh gần đây (phishing, ransomware, data leak)</li>
                                                        <li>Điểm yếu đã biết nhưng chưa khắc phục</li>
                                                        <li>Yêu cầu tuân thủ đặc thù ngành (PCI-DSS, HIPAA)</li>
                                                        <li>Kế hoạch nâng cấp hạ tầng sắp tới</li>
                                                        <li>Ngân sách dự kiến cho ATTT</li>
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

                        <div className={styles.summaryBox}>
                            <h4>Kiểm tra trước khi đánh giá</h4>
                            <ul>
                                <li>Tiêu chuẩn: <strong>{currentStandard.name}</strong></li>
                                <li>Tổ chức: <strong>{form.org_name || 'Chưa nhập'}</strong></li>
                                <li>Quy mô: <strong>{form.employees} nhân sự</strong> ({form.servers} máy chủ)</li>
                                <li>Mức tuân thủ sơ bộ: <strong>{form.implemented_controls.length}/{totalControls} Controls</strong> ({compliancePercent}%)</li>
                            </ul>
                        </div>
                    </div>
                )
            default:
                return null
        }
    }

    return (
        <div className="page-container">
            <div className={styles.header}>
                <h1 className={styles.title}>Form Đánh giá Đa Tiêu chuẩn</h1>
                <p className={styles.subtitle}>
                    AI Cyber Auditor — Chấm điểm dựa trên khung kiểm soát tiêu chuẩn chính thức.<br />
                    Chưa có dữ liệu? Thử <Link href="/templates" className={styles.templateLink}>Kho Mẫu Thực tế</Link> để trải nghiệm.
                </p>
            </div>

            <div className={styles.tabs}>
                <button className={`${styles.tab} ${activeTab === 'form' ? styles.tabActive : ''}`} onClick={() => setActiveTab('form')}>
                    📝 Nhập liệu
                </button>
                <button className={`${styles.tab} ${activeTab === 'result' ? styles.tabActive : ''}`} onClick={() => setActiveTab('result')} disabled={!result}>
                    📊 Kết quả
                </button>
                <button className={`${styles.tab} ${activeTab === 'history' ? styles.tabActive : ''}`} onClick={() => setActiveTab('history')}>
                    🕒 Lịch sử
                </button>
            </div>

            {activeTab === 'form' && (
                <div className={styles.formWrap}>
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

                    <div className={styles.progressBar}>
                        <div className={styles.progressFill} style={{ width: `${((step - 1) / 3) * 100}%` }} />
                    </div>

                    <div className={styles.stepContainer}>
                        {renderStepContent()}
                    </div>

                    <div className={styles.stepActions}>
                        <button className={styles.btnSecondary} onClick={prevStep} disabled={step === 1 || loading}>
                            ← Quay lại
                        </button>

                        {step < 4 ? (
                            <button className={styles.btnPrimary} onClick={nextStep} disabled={step === 1 && !form.org_name}>
                                Tiếp theo →
                            </button>
                        ) : (
                            <button className={styles.btnSubmit} onClick={submit} disabled={loading || !form.org_name}>
                                {loading ? (
                                    <><span className={styles.spinner} /> Đang xử lý ...</>
                                ) : (
                                    '🤖 Bắt đầu Đánh giá'
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
                            <p>{result.report || 'Timeout hoặc lỗi phân tích.'}</p>
                            <button className={styles.btnSecondary} onClick={() => setActiveTab('form')} style={{ marginTop: '1rem' }}>
                                Sửa thông tin & thử lại
                            </button>
                        </div>
                    ) : (
                        <>
                            <div className={styles.reportSection}>
                                <div className={styles.resultHeader}>
                                    <h2 className={styles.sectionTitle}>
                                        {result.status === 'processing' ? '⏳ AI đang phân tích...' : '📊 Báo cáo AI Auditor'}
                                    </h2>
                                    {result.status === 'processing' && (
                                        <div className={styles.pollingInfo}>
                                            <span className={styles.pollingDot} />
                                            <span>Tự động cập nhật</span>
                                        </div>
                                    )}
                                </div>
                                <div className={styles.md}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {result.report || 'Model đang xử lý dữ liệu, vui lòng chờ 1-2 phút...'}
                                    </ReactMarkdown>
                                </div>
                            </div>

                            {result.model_used && (
                                <div className={styles.modelInfo}>
                                    <div className={styles.modelTag}>🧠 Model: <strong>{result.model_used.analysis_and_summary}</strong></div>
                                    <div className={styles.modelTag}>🚀 Strategy: <strong>Semantic RAG Assessment</strong></div>
                                </div>
                            )}

                            <div className={styles.actionsCenter}>
                                <button className={styles.btnSecondary} onClick={() => setActiveTab('form')}>
                                    ← Tạo đánh giá mới
                                </button>
                            </div>
                        </>
                    )}
                </div>
            )}

            {activeTab === 'history' && (
                <div className={styles.historyWrap}>
                    <div className={styles.historyHeader}>
                        <h2 className={styles.sectionTitle}>🕒 Lịch sử Báo cáo</h2>
                        <button className={styles.refreshBtn} onClick={fetchHistory}>🔄 Làm mới</button>
                    </div>
                    <p className={styles.helperText}>Hệ thống RAG xử lý ngầm. Báo cáo được lưu theo Thread ID trên máy chủ.</p>

                    {assessmentHistory.length === 0 ? (
                        <div className={styles.emptyHistory}>Chưa có lịch sử đánh giá nào.</div>
                    ) : (
                        <div className={styles.historyList}>
                            {assessmentHistory.map((hist, idx) => (
                                <div key={idx} className={styles.historyItem}>
                                    <div className={styles.histInfo}>
                                        <div className={styles.histTitle}>
                                            {hist.org}
                                            <span className={styles.histDate}>{hist.date}</span>
                                        </div>
                                        <div className={styles.histStd}>Tiêu chuẩn: <strong>{hist.standard}</strong></div>
                                    </div>
                                    <div className={styles.histAction}>
                                        <span className={`${styles.statusBadge} ${styles[`status_${hist.status}`]}`}>
                                            {hist.status === 'completed' ? '✅ Hoàn thành' :
                                                hist.status === 'failed' ? '❌ Thất bại' :
                                                    hist.status === 'processing' ? '⏳ Đang xử lý' : '🔄 Chờ xử lý'}
                                        </span>
                                        {hist.status === 'completed' && (
                                            <button className={styles.btnSmall} onClick={() => refreshStatus(hist.id)}>Xem →</button>
                                        )}
                                        {hist.status === 'processing' && (
                                            <button className={styles.btnSmall} onClick={() => refreshStatus(hist.id)}>Kiểm tra</button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
            {activeTooltip && CONTROL_DESCRIPTIONS[activeTooltip] && (() => {
                const desc = CONTROL_DESCRIPTIONS[activeTooltip]
                const ctrlId = activeTooltip
                const allControls = currentStandard.controls.flatMap(c => c.controls)
                const ctrlObj = allControls.find(c => c.id === ctrlId)
                const isImplemented = form.implemented_controls.includes(ctrlId)
                return (
                    <>
                        <div className={styles.panelOverlay} onClick={() => setActiveTooltip(null)} />
                        <div className={styles.detailPanel}>
                            <div className={styles.panelHeader}>
                                <div>
                                    <span className={`${styles.panelBadge} ${isImplemented ? styles.panelBadgeActive : ''}`}>
                                        {isImplemented ? '✅ Đã triển khai' : '⚠️ Chưa triển khai'}
                                    </span>
                                    <h3 className={styles.panelTitle}>{ctrlId}</h3>
                                    <p className={styles.panelSubtitle}>{ctrlObj?.label || ''}</p>
                                </div>
                                <button className={styles.panelClose} onClick={() => setActiveTooltip(null)}>✕</button>
                            </div>
                            <div className={styles.panelBody}>
                                <div className={styles.panelSection}>
                                    <div className={styles.panelSectionTitle}>
                                        <span>📋</span> Yêu cầu tiêu chuẩn
                                    </div>
                                    <p className={styles.panelText}>{desc.requirement}</p>
                                </div>
                                <div className={styles.panelDivider} />
                                <div className={styles.panelSection}>
                                    <div className={styles.panelSectionTitle}>
                                        <span>✅</span> Tiêu chí đánh giá
                                    </div>
                                    <p className={styles.panelText}>{desc.criteria}</p>
                                </div>
                                <div className={styles.panelDivider} />
                                <div className={styles.panelSection}>
                                    <div className={styles.panelSectionTitle}>
                                        <span>💡</span> Hướng dẫn
                                    </div>
                                    <p className={styles.panelHint}>
                                        {isImplemented
                                            ? 'Tổ chức đã đánh dấu biện pháp này là "triển khai". Hãy đảm bảo có đầy đủ bằng chứng và tài liệu chứng minh.'
                                            : 'Biện pháp này chưa được triển khai. Xem xét các tiêu chí đánh giá ở trên để lên kế hoạch thực hiện.'}
                                    </p>
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
