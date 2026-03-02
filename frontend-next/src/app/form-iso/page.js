'use client'

import { useState } from 'react'
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
    const [activeTab, setActiveTab] = useState('form')

    const set = (key, val) => setForm(p => ({ ...p, [key]: val }))
    const togglePolicy = (p) => {
        setForm(prev => ({
            ...prev,
            existing_policies: prev.existing_policies.includes(p)
                ? prev.existing_policies.filter(x => x !== p)
                : [...prev.existing_policies, p]
        }))
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
            setResult(data)
            setActiveTab('result')
        } catch {
            setResult({ error: true, report: 'Lỗi kết nối server.' })
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="page-container">
            <div className={styles.header}>
                <h1 className={styles.title}>📋 Đánh giá ISO 27001:2022</h1>
                <p className={styles.subtitle}>AI phân tích hệ thống theo Annex A</p>
            </div>

            <div className={styles.tabs}>
                <button className={`${styles.tab} ${activeTab === 'form' ? styles.tabActive : ''}`} onClick={() => setActiveTab('form')}>
                    📝 Nhập thông tin
                </button>
                <button className={`${styles.tab} ${activeTab === 'result' ? styles.tabActive : ''}`} onClick={() => setActiveTab('result')} disabled={!result}>
                    📊 Kết quả đánh giá
                </button>
            </div>

            {activeTab === 'form' && (
                <div className={styles.formWrap}>
                    <section className={styles.section}>
                        <h2 className={styles.sectionTitle}>🏢 Thông tin tổ chức</h2>
                        <div className={styles.grid}>
                            <div className={styles.field}>
                                <label>Tên tổ chức</label>
                                <input value={form.org_name} onChange={e => set('org_name', e.target.value)} placeholder="VD: Công ty ABC" />
                            </div>
                            <div className={styles.field}>
                                <label>Quy mô</label>
                                <select value={form.org_size} onChange={e => set('org_size', e.target.value)}>
                                    <option value="">Chọn quy mô</option>
                                    <option value="small">Nhỏ (dưới 50 NV)</option>
                                    <option value="medium">Trung bình (50-200 NV)</option>
                                    <option value="large">Lớn (trên 200 NV)</option>
                                </select>
                            </div>
                            <div className={styles.field}>
                                <label>Ngành nghề</label>
                                <input value={form.industry} onChange={e => set('industry', e.target.value)} placeholder="VD: Tài chính, CNTT, Y tế..." />
                            </div>
                            <div className={styles.field}>
                                <label>Số nhân viên</label>
                                <input type="number" value={form.employees || ''} onChange={e => set('employees', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.field}>
                                <label>Nhân viên IT</label>
                                <input type="number" value={form.it_staff || ''} onChange={e => set('it_staff', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.field}>
                                <label>Trạng thái ISO</label>
                                <select value={form.iso_status} onChange={e => set('iso_status', e.target.value)}>
                                    <option value="">Chọn trạng thái</option>
                                    <option value="Chưa triển khai">Chưa triển khai</option>
                                    <option value="Đang triển khai">Đang triển khai</option>
                                    <option value="Đã chứng nhận">Đã chứng nhận</option>
                                </select>
                            </div>
                        </div>
                    </section>

                    <section className={styles.section}>
                        <h2 className={styles.sectionTitle}>🖥️ Hạ tầng IT</h2>
                        <div className={styles.grid}>
                            <div className={styles.field}>
                                <label>Số lượng server</label>
                                <input type="number" value={form.servers || ''} onChange={e => set('servers', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                            <div className={styles.field}>
                                <label>Firewall</label>
                                <input value={form.firewalls} onChange={e => set('firewalls', e.target.value)} placeholder="VD: FortiGate 100F" />
                            </div>
                            <div className={styles.field}>
                                <label>Cloud Provider</label>
                                <input value={form.cloud_provider} onChange={e => set('cloud_provider', e.target.value)} placeholder="VD: AWS, Azure, GCP..." />
                            </div>
                            <div className={styles.field}>
                                <label>Antivirus / EDR</label>
                                <input value={form.antivirus} onChange={e => set('antivirus', e.target.value)} placeholder="VD: CrowdStrike, Kaspersky..." />
                            </div>
                            <div className={styles.field}>
                                <label>Backup</label>
                                <input value={form.backup_solution} onChange={e => set('backup_solution', e.target.value)} placeholder="VD: Veeam, NAS Synology..." />
                            </div>
                            <div className={styles.field}>
                                <label>SIEM / Log</label>
                                <input value={form.siem} onChange={e => set('siem', e.target.value)} placeholder="VD: Wazuh, Splunk, ELK..." />
                            </div>
                            <div className={styles.fieldFull}>
                                <label className={styles.checkLabel}>
                                    <input type="checkbox" checked={form.vpn} onChange={e => set('vpn', e.target.checked)} />
                                    Có VPN cho truy cập từ xa
                                </label>
                            </div>
                            <div className={styles.fieldFull}>
                                <label>Sự cố ATTT (12 tháng qua)</label>
                                <input type="number" value={form.incidents_12m || ''} onChange={e => set('incidents_12m', parseInt(e.target.value) || 0)} placeholder="0" />
                            </div>
                        </div>
                    </section>

                    <section className={styles.section}>
                        <h2 className={styles.sectionTitle}>📜 Chính sách hiện có</h2>
                        <div className={styles.policyGrid}>
                            {POLICY_OPTIONS.map(p => (
                                <label key={p} className={`${styles.policyItem} ${form.existing_policies.includes(p) ? styles.policyActive : ''}`}>
                                    <input type="checkbox" checked={form.existing_policies.includes(p)} onChange={() => togglePolicy(p)} />
                                    <span>{p}</span>
                                </label>
                            ))}
                        </div>
                    </section>

                    <section className={styles.section}>
                        <h2 className={styles.sectionTitle}>📐 Mô tả hệ thống / Sơ đồ mạng</h2>
                        <textarea
                            className={styles.textarea}
                            value={form.network_diagram}
                            onChange={e => set('network_diagram', e.target.value)}
                            placeholder={"Mô tả kiến trúc mạng, topology, VLAN, DMZ...\nVD:\n- Internet → FortiGate 100F → Core Switch Cisco 9300\n- VLAN 10: Server (AD, File, DB)\n- VLAN 20: User (100 workstations)\n- VLAN 99: Guest WiFi (isolated)\n- Backup: NAS Synology → Cloud S3"}
                            rows={6}
                        />
                    </section>

                    <section className={styles.section}>
                        <h2 className={styles.sectionTitle}>📝 Ghi chú thêm</h2>
                        <textarea
                            className={styles.textarea}
                            value={form.notes}
                            onChange={e => set('notes', e.target.value)}
                            placeholder="Thông tin bổ sung, yêu cầu đặc biệt..."
                            rows={3}
                        />
                    </section>

                    <button className={styles.submitBtn} onClick={submit} disabled={loading || !form.org_name}>
                        {loading ? (
                            <><span className={styles.spinner} /> Đang phân tích (2-5 phút)...</>
                        ) : (
                            '🤖 Đánh giá bằng AI'
                        )}
                    </button>
                </div>
            )}

            {activeTab === 'result' && result && (
                <div className={styles.resultWrap}>
                    {result.error ? (
                        <div className={styles.errorBox}>{result.report}</div>
                    ) : (
                        <>
                            <div className={styles.reportSection}>
                                <h2 className={styles.sectionTitle}>📊 Báo cáo tổng hợp</h2>
                                <div className={styles.md}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {result.report || 'Đang tạo báo cáo...'}
                                    </ReactMarkdown>
                                </div>
                            </div>

                            {result.model_used && (
                                <div className={styles.modelInfo}>
                                    <span>Phân tích: {result.model_used.analysis}</span>
                                    <span>Tổng hợp: {result.model_used.summary}</span>
                                </div>
                            )}

                            {result.details && result.details.length > 0 && (
                                <div className={styles.reportSection}>
                                    <h2 className={styles.sectionTitle}>🔍 Chi tiết theo nhóm</h2>
                                    {result.details.map((d, i) => (
                                        <details key={i} className={styles.detailGroup}>
                                            <summary className={styles.detailSummary}>
                                                {d.category === 'organization' && '🏢 Kiểm soát tổ chức (A.5)'}
                                                {d.category === 'people' && '👥 Kiểm soát con người (A.6)'}
                                                {d.category === 'physical' && '🏗️ Kiểm soát vật lý (A.7)'}
                                                {d.category === 'technology' && '💻 Kiểm soát công nghệ (A.8)'}
                                            </summary>
                                            <div className={styles.md}>
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                    {d.analysis}
                                                </ReactMarkdown>
                                            </div>
                                        </details>
                                    ))}
                                </div>
                            )}

                            <button className={styles.backBtn} onClick={() => setActiveTab('form')}>
                                ← Quay lại chỉnh sửa
                            </button>
                        </>
                    )}
                </div>
            )}
        </div>
    )
}
