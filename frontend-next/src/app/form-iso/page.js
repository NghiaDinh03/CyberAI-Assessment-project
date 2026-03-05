'use client'

import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './page.module.css'

const POLICY_OPTIONS = [
    'Chính sách ATTT tổng thể',
    'Kiểm soát truy cập',
    'Quản lý mật khẩu',
    'Backup và khôi phục',
    'Quản lý sự cố',
    'BYOD / Thiết bị di động',
    'Phân loại thông tin',
    'Mã hóa dữ liệu',
    'Đào tạo nhận thức ATTT',
    'Quản lý nhà cung cấp',
    'Kinh doanh liên tục (BCP)',
    'Clean desk policy'
]

export default function FormISOPage() {
    const [step, setStep] = useState(1)
    const [form, setForm] = useState({
        org_name: '', org_size: '', industry: '',
        employees: 0, it_staff: 0,
        servers: 0, firewalls: '', vpn: false,
        cloud_provider: '', antivirus: '', backup_solution: '',
        siem: '', network_diagram: '',
        existing_policies: [],
        incidents_12m: 0, iso_status: '', notes: ''
    })
    const [result, setResult] = useState(null)
    const [loading, setLoading] = useState(false)
    const [activeTab, setActiveTab] = useState('form') // 'form' or 'result'

    useEffect(() => {
        const reuseData = localStorage.getItem('reuse_iso_form')
        if (reuseData) {
            try {
                const parsed = JSON.parse(reuseData)
                if (parsed.organization) {
                    setForm({
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
                        existing_policies: parsed.compliance?.existing_policies || [],
                        incidents_12m: parsed.compliance?.incidents_12m || 0,
                        iso_status: parsed.compliance?.iso_status || '',
                        notes: parsed.notes || ''
                    })
                }
                localStorage.removeItem('reuse_iso_form')
            } catch (e) {
                console.error('Lỗi khi nạp lại dữ liệu form:', e)
            }
        }
    }, [])

    const set = (key, val) => setForm(p => ({ ...p, [key]: val }))
    const togglePolicy = (p) => {
        setForm(prev => ({
            ...prev,
            existing_policies: prev.existing_policies.includes(p)
                ? prev.existing_policies.filter(x => x !== p)
                : [...prev.existing_policies, p]
        }))
    }

    const nextStep = () => {
        if (step < 4) setStep(step + 1)
    }

    const prevStep = () => {
        if (step > 1) setStep(step - 1)
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
                    report: 'Hệ thống đã tiếp nhận yêu cầu. Model đang phân tích (có thể mất 1-2 phút). Vui lòng bấm "Làm mới trạng thái" để xem tiến độ.'
                })
                setActiveTab('result')
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

    const refreshStatus = async () => {
        if (!result || !result.id) return;
        try {
            const res = await fetch(`/api/iso27001/assessments/${result.id}`)
            const data = await res.json()
            if (data.status === 'completed' || data.status === 'failed') {
                setResult({
                    id: data.id,
                    status: data.status,
                    report: data.result?.report || data.error,
                    model_used: data.result?.model_used
                })
            }
        } catch (e) {
            console.error('Lỗi khi tải kết quả:', e)
        }
    }

    const renderStepContent = () => {
        switch (step) {
            case 1:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>🏢 Bước 1: Thông tin Tổ chức</h2>
                        <div className={styles.grid}>
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
                                <label>Trạng thái tuân thủ ISO hiện tại</label>
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
                                <label>Số lượng nhân sự IT / Bảo mật</label>
                                <input type="number" value={form.it_staff || ''} onChange={e => set('it_staff', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                        </div>
                    </div>
                )
            case 2:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>🖥️ Bước 2: Hạ tầng & Kỹ thuật mạng</h2>
                        <div className={styles.grid}>
                            <div className={styles.field}>
                                <label>Số lượng máy chủ (Physical & VM)</label>
                                <input type="number" value={form.servers || ''} onChange={e => set('servers', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.field}>
                                <label>Tường lửa (Firewall)</label>
                                <input value={form.firewalls} onChange={e => set('firewalls', e.target.value)} placeholder="VD: FortiGate 100F, Palo Alto..." />
                            </div>
                            <div className={styles.field}>
                                <label>Dịch vụ Đám mây (Cloud)</label>
                                <input value={form.cloud_provider} onChange={e => set('cloud_provider', e.target.value)} placeholder="VD: AWS, Azure, Google Cloud..." />
                            </div>
                            <div className={styles.field}>
                                <label>Giải pháp Chống mã độc (AV/EDR)</label>
                                <input value={form.antivirus} onChange={e => set('antivirus', e.target.value)} placeholder="VD: CrowdStrike, Kaspersky, SentinelOne..." />
                            </div>
                            <div className={styles.field}>
                                <label>Công nghệ Sao lưu (Backup)</label>
                                <input value={form.backup_solution} onChange={e => set('backup_solution', e.target.value)} placeholder="VD: Veeam Backup, NAS Synology..." />
                            </div>
                            <div className={styles.field}>
                                <label>Hệ thống Ghi nhật ký (SIEM/Log)</label>
                                <input value={form.siem} onChange={e => set('siem', e.target.value)} placeholder="VD: Wazuh, Splunk, ElasticSearch..." />
                            </div>
                            <div className={styles.field}>
                                <label>Sự cố An ninh mạng (12 tháng qua)</label>
                                <input type="number" value={form.incidents_12m || ''} onChange={e => set('incidents_12m', parseInt(e.target.value) || 0)} placeholder="Số lần bị tấn công/rò rỉ..." />
                            </div>
                            <div className={styles.fieldCheckbox}>
                                <label className={styles.checkLabel}>
                                    <input type="checkbox" checked={form.vpn} onChange={e => set('vpn', e.target.checked)} />
                                    <span>Hệ thống có cấu hình VPN cho nhân viên làm việc từ xa</span>
                                </label>
                            </div>
                        </div>
                    </div>
                )
            case 3:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>📜 Bước 3: Đánh giá Chính sách hiện có</h2>
                        <p className={styles.helperText}>Chọn những quy tắc/chính sách mà tổ chức của bạn <strong>đã ban hành bằng văn bản</strong> và thực thi:</p>
                        <div className={styles.policyGrid}>
                            {POLICY_OPTIONS.map(p => (
                                <label key={p} className={`${styles.policyItem} ${form.existing_policies.includes(p) ? styles.policyActive : ''}`}>
                                    <input type="checkbox" checked={form.existing_policies.includes(p)} onChange={() => togglePolicy(p)} />
                                    <span>{p}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                )
            case 4:
                return (
                    <div className={styles.stepContent}>
                        <h2 className={styles.sectionTitle}>📐 Bước 4: Mô tả hệ thống & Tổng kết</h2>
                        <p className={styles.helperText}>Diễn giải kiến trúc mạng hoặc đặc thù hệ thống bằng lời thay vì hình ảnh (AI hiện chỉ đọc Text):</p>

                        <div className={styles.fieldFull}>
                            <label>Mô tả kiến trúc mạng / Topology</label>
                            <textarea
                                className={styles.textarea}
                                value={form.network_diagram}
                                onChange={e => set('network_diagram', e.target.value)}
                                placeholder="Ví dụ:&#10;- Mạng chia làm 3 VLAN: Server (10), User (20), WiFi Khách (99)&#10;- Tất cả traffic ra vào đều qua Firewall FortiGate.&#10;- Server nội bộ (AD, File Server) không public ra ngoài...&#10;- Cổng SSH đóng, chỉ truy cập qua VPN nội bộ."
                                rows={6}
                            />
                        </div>

                        <div className={styles.fieldFull}>
                            <label>Ghi chú bổ sung (Tùy chọn)</label>
                            <textarea
                                className={styles.textarea}
                                value={form.notes}
                                onChange={e => set('notes', e.target.value)}
                                placeholder="Bất kỳ thông tin điểm yếu, rủi ro nào bạn đang lo ngại..."
                                rows={3}
                            />
                        </div>

                        <div className={styles.summaryBox}>
                            <h4>Kiểm tra trước khi nộp:</h4>
                            <ul>
                                <li>Tổ chức: <strong>{form.org_name || 'Chưa nhập'}</strong></li>
                                <li>Quy mô: <strong>{form.employees} nhân sự</strong> ({form.servers} máy chủ)</li>
                                <li>Chính sách: <strong>{form.existing_policies.length}/12</strong> mục đã áp dụng</li>
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
                <h1 className={styles.title}>📋 Đánh giá ISO 27001:2022</h1>
                <p className={styles.subtitle}>AI Security Auditor - Phân tích dựa trên tiêu chuẩn cốt lõi (Annex A)</p>
            </div>

            <div className={styles.tabs}>
                <button className={`${styles.tab} ${activeTab === 'form' ? styles.tabActive : ''}`} onClick={() => setActiveTab('form')}>
                    📝 Nhập liệu hệ thống
                </button>
                <button className={`${styles.tab} ${activeTab === 'result' ? styles.tabActive : ''}`} onClick={() => setActiveTab('result')} disabled={!result}>
                    📊 Kết quả Assessor
                </button>
            </div>

            {activeTab === 'form' && (
                <div className={styles.formWrap}>
                    {/* Stepper Header */}
                    <div className={styles.stepper}>
                        {[1, 2, 3, 4].map(s => (
                            <div key={s} className={`${styles.stepIndicator} ${step === s ? styles.stepCurrent : step > s ? styles.stepCompleted : ''}`}>
                                <div className={styles.stepCircle}>{step > s ? '✓' : s}</div>
                                <div className={styles.stepLabel}>
                                    {s === 1 ? 'Tổ chức' : s === 2 ? 'Hạ tầng' : s === 3 ? 'Chính sách' : 'Mô tả'}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Progress Bar */}
                    <div className={styles.progressBar}>
                        <div className={styles.progressFill} style={{ width: `${((step - 1) / 3) * 100}%` }}></div>
                    </div>

                    {/* Step Content */}
                    <div className={styles.stepContainer}>
                        {renderStepContent()}
                    </div>

                    {/* Navigation Buttons */}
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
                            <p>{result.report || 'Timeout hoặc lỗi AI model. Yêu cầu kiểm tra phần cứng CPU.'}</p>
                            <button className={styles.btnSecondary} onClick={() => setActiveTab('form')} style={{ marginTop: '1rem' }}>
                                Làm lại / Sửa thông tin
                            </button>
                        </div>
                    ) : (
                        <>
                            <div className={styles.reportSection}>
                                <div className={styles.resultHeader}>
                                    <h2 className={styles.sectionTitle}>
                                        {result.status === 'processing' ? '⏳ Đang lập báo cáo...' : '📊 Báo cáo AI Auditor'}
                                    </h2>
                                    {result.status === 'processing' && (
                                        <button className={styles.refreshBtn} onClick={refreshStatus}>
                                            🔄 Làm mới kết quả
                                        </button>
                                    )}
                                </div>
                                <div className={styles.md}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {result.report || 'Model đang phân tích, bạn vui lòng chờ từ 1-2 phút tùy tốc độ CPU...'}
                                    </ReactMarkdown>
                                </div>
                            </div>

                            {result.model_used && (
                                <div className={styles.modelInfo}>
                                    <div className={styles.modelTag}>🧠 Model Inference: <strong>{result.model_used.analysis_and_summary}</strong></div>
                                    <div className={styles.modelTag}>🚀 Strategy: <strong>Direct Context RAG</strong></div>
                                </div>
                            )}

                            <div className={styles.actionsCenter}>
                                <button className={styles.btnSecondary} onClick={() => setActiveTab('form')}>
                                    ← Chỉnh sửa hệ thống
                                </button>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    )
}
