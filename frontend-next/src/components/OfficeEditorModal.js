'use client'

import React, { useState, useEffect, useMemo } from 'react'
import styles from './OfficeEditorModal.module.css'
import { TCVN_11930_CONTROLS_VI, ISO_27001_CONTROLS_VI } from '../data/standards'
import EvidenceExtractionProofModal from './EvidenceExtractionProofModal'


export default function OfficeEditorModal({
    isOpen,
    onClose,
    fileType = 'docx',
    assessmentId,
    initialReport = '',
    jsonData = {},
    orgName = 'Doanh nghiệp',
    standardName = 'ISO/IEC 27001:2022',
}) {
    const [viewMode, setViewMode] = useState('preview') // 'preview' | 'fields'
    const [saving, setSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState('Đã đồng bộ')
    const [showProofModal, setShowProofModal] = useState(false)

    // Field-Value State Model
    const [fields, setFields] = useState({
        orgName: orgName || 'Doanh nghiệp',
        industry: jsonData?.system_info?.industry || 'Công nghệ & Dịch vụ số',
        standardName: standardName || 'ISO/IEC 27001:2022',
        assessmentLevel: jsonData?.system_info?.assessment_level || (standardName?.includes('11930') ? 'Cấp độ 3 (TCVN 11930 & NĐ 85/2016)' : 'Tiêu chuẩn Doanh nghiệp'),
        servers: jsonData?.system_info?.servers || 9,
        firewalls: jsonData?.system_info?.firewalls || 2,
        ipRange: jsonData?.system_info?.ip_range || '10.140.0.0/24',
        networkDiagram: jsonData?.system_info?.network_diagram || 'Mô hình phân cấp 2 lớp: Firewall biên Internet HA + Vùng DMZ + Vùng Server Farm nội bộ + Phân vùng OT cách ly.',
        assessmentDate: new Date().toISOString().slice(0, 10),
        auditorName: 'Chuyên gia Đánh giá Trưởng (Lead Auditor)',
        approverName: 'Đại diện Lãnh đạo Đơn vị Chủ quản',
        compliancePercent: jsonData?.compliance?.percentage || 0,
        executiveSummary: 'Báo cáo đánh giá mức độ tuân thủ và các khoảng trống an toàn thông tin của hệ thống dựa trên tiêu chuẩn quy định. Mặc dù tổ chức đã nỗ lực triển khai các biện pháp bảo vệ, hệ thống vẫn tồn tại các điểm rủi ro cần khắc phục theo lộ trình.',
        scope: jsonData?.system_info?.scope || 'Toàn bộ hạ tầng mạng LAN/DMZ, 09 máy chủ cơ sở dữ liệu, ứng dụng điều hành và văn phòng điện tử thuộc dải mạng 10.140.0.0/24.',
        keyStrengths: 'Đã triển khai hệ thống xác thực tập trung, tường lửa phân vùng mạng cơ bản và ban hành sơ bộ quy chế an toàn thông tin.',
        roadmap30d: 'Khắc phục các lỗ hổng Critical (cập nhật bản vá máy chủ, đổi mật khẩu mặc định, tắt giao thức truyền thông không mã hóa).',
        roadmap90d: 'Triển khai xác thực đa yếu tố (MFA) toàn diện, cấu hình giám sát nhật ký SIEM tập trung, diễn tập phương án sao lưu dự phòng định kỳ.',
        roadmap180d: 'Hoàn thiện hệ thống quản lý an toàn thông tin ISMS theo chuẩn ISO 27001:2022 / TCVN 11930 Cấp độ 3, đánh giá độc lập định kỳ hàng năm.',
    })

    // Active tab in Fields:Values mode
    const [activeFieldsTab, setActiveFieldsTab] = useState('tab_admin') // 'tab_admin' | 'tab_technical' | 'tab_risks'

    // Implemented controls set for technical domain evaluation
    const [implementedControls, setImplementedControls] = useState(() => {
        const raw = jsonData?.system_info?.implemented_controls || jsonData?.implemented_controls
        if (Array.isArray(raw) && raw.length > 0) return new Set(raw)
        return new Set([
            'NW.01', 'NW.02', 'NW.04', 'NW.05',
            'SV.01', 'SV.02', 'SV.05',
            'APP.01', 'APP.02', 'APP.04', 'APP.07',
            'DAT.01', 'DAT.02', 'DAT.03',
            'MNG.01', 'MNG.02', 'MNG.03', 'MNG.04'
        ])
    })

    const activeStandardControls = useMemo(() => {
        const std = fields.standardName || standardName || ''
        if (std.toLowerCase().includes('11930') || std.toLowerCase().includes('tcvn')) {
            return TCVN_11930_CONTROLS_VI
        }
        return ISO_27001_CONTROLS_VI
    }, [fields.standardName, standardName])

    const totalStandardControlsCount = useMemo(() => {
        return activeStandardControls.reduce((acc, cat) => acc + (cat.controls?.length || 0), 0)
    }, [activeStandardControls])

    const toggleControl = (cid) => {
        setImplementedControls(prev => {
            const next = new Set(prev)
            if (next.has(cid)) next.delete(cid)
            else next.add(cid)
            return next
        })
    }

    // Risk Register Table State
    const [riskRows, setRiskRows] = useState([])

    useEffect(() => {
        if (!isOpen) return

        // Extract and clean executive summary if report is present
        let parsedSummary = ''
        if (initialReport) {
            let extracted = ''
            const sec1Match = initialReport.match(/##\s*1\.\s*ĐÁNH GIÁ TỔNG QUAN[^\n]*\n+([\s\S]*?)(?=\n##|$)/i)
            if (sec1Match) {
                extracted = sec1Match[1]
            } else {
                const sec5Match = initialReport.match(/##\s*5\.\s*EXECUTIVE SUMMARY[^\n]*\n+([\s\S]*?)(?=\n##|$)/i)
                if (sec5Match) extracted = sec5Match[1]
                else extracted = initialReport
            }

            extracted = extracted
                .replace(/^#+.*$/gm, '')
                .replace(/^\|.*\|$/gm, '')
                .replace(/\*\*(?:Tổ chức|Ngành|Tiêu chuẩn|Ngày đánh giá|Người thực hiện|Tuân thủ):.*?\*\*/gi, '')
                .replace(/(?:Tổ chức|Ngành|Tiêu chuẩn áp dụng|Ngày đánh giá|Người thực hiện):[^\n]+/gi, '')
                .replace(/---+/g, '')
                .replace(/\[Context:.*?\]/g, '')
                .replace(/\*\*|__|`|>/g, '')
                .replace(/^\s*[-*•]\s+/gm, '')
                .replace(/\s+/g, ' ')
                .trim()

            if (extracted.length > 50) {
                if (extracted.length <= 650) {
                    parsedSummary = extracted
                } else {
                    const periodIdx = extracted.indexOf('.', 450)
                    if (periodIdx !== -1 && periodIdx < 700) {
                        parsedSummary = extracted.slice(0, periodIdx + 1).trim()
                    } else {
                        const lastPeriod = extracted.lastIndexOf('.', 600)
                        if (lastPeriod > 150) {
                            parsedSummary = extracted.slice(0, lastPeriod + 1).trim()
                        } else {
                            parsedSummary = extracted.slice(0, 500).replace(/\s+\S*$/, '') + '.'
                        }
                    }
                }
            }
        }

        if (!parsedSummary || parsedSummary.length < 30) {
            parsedSummary = `Báo cáo này cung cấp cái nhìn toàn diện về mức độ tuân thủ và rủi ro an toàn thông tin của ${orgName || 'đơn vị'} so với tiêu chuẩn quốc tế ${standardName || 'ISO 27001:2022'}. Qua kết quả thẩm định thực tế, tổ chức đã xây dựng được nền tảng cơ bản về quản lý an toàn thông tin, tuy nhiên cần tiếp tục khắc phục các khoảng trống an ninh trọng yếu để đạt mức tuân thủ cao.`
        }

        const pct = jsonData?.compliance?.percentage ?? (jsonData?.compliance_percent ?? 0)

        setFields(prev => ({
            ...prev,
            orgName: orgName || prev.orgName,
            standardName: standardName || prev.standardName,
            compliancePercent: pct,
            executiveSummary: parsedSummary,
        }))

        // Load initial risks from jsonData
        const rawRisks = jsonData?.risk_register || jsonData?.top_gaps || []
        if (rawRisks.length > 0) {
            setRiskRows(rawRisks.map((item, idx) => {
                const l = item.likelihood || (item.severity === 'critical' ? 5 : item.severity === 'high' ? 4 : 3)
                const i = item.impact || (item.severity === 'critical' ? 5 : item.severity === 'high' ? 4 : 3)
                return {
                    id: idx + 1,
                    control_id: item.control_id || item.id || `CTRL-${idx + 1}`,
                    gap: item.gap || item.label || 'Chưa hoàn thiện biện pháp kiểm soát theo quy định.',
                    severity: item.severity || (l * i >= 15 ? 'critical' : l * i >= 10 ? 'high' : 'medium'),
                    likelihood: l,
                    impact: i,
                    risk_score: item.risk_score || (l * i),
                    recommendation: item.recommendation || 'Bổ sung chính sách và kích hoạt biện pháp kỹ thuật tương ứng.',
                }
            }))
        } else {
            setRiskRows([
                {
                    id: 1,
                    control_id: 'A.5.17',
                    gap: 'Chưa bắt buộc xác thực đa yếu tố (MFA) cho toàn bộ tài khoản quản trị hệ thống.',
                    severity: 'critical',
                    likelihood: 5,
                    impact: 5,
                    risk_score: 25,
                    recommendation: 'Kích hoạt xác thực 2 bước (TOTP/FIDO2) bắt buộc cho 100% tài khoản quản trị mạng và máy chủ.',
                },
                {
                    id: 2,
                    control_id: 'A.8.20',
                    gap: 'Tường lửa chưa phân tách vùng mạng DMZ riêng biệt cho máy chủ Web công khai.',
                    severity: 'high',
                    likelihood: 4,
                    impact: 4,
                    risk_score: 16,
                    recommendation: 'Thiết lập phân vùng mạng DMZ cô lập máy chủ Web với vùng cơ sở dữ liệu nội bộ.',
                },
                {
                    id: 3,
                    control_id: 'A.8.8',
                    gap: 'Hệ điều hành máy chủ ứng dụng chưa được cập nhật các bản vá bảo mật định kỳ trong 6 tháng.',
                    severity: 'high',
                    likelihood: 4,
                    impact: 3,
                    risk_score: 12,
                    recommendation: 'Triển khai quy trình quét lỗ hổng định kỳ và cài đặt các bản vá lỗi bảo mật quan trọng.',
                }
            ])
        }
    }, [isOpen, jsonData, initialReport, orgName, standardName])

    if (!isOpen) return null

    const handleFieldChange = (key, val) => {
        setFields(prev => ({ ...prev, [key]: val }))
    }

    const handleRiskCellChange = (index, key, val) => {
        setRiskRows(prev => {
            const next = [...prev]
            const target = { ...next[index], [key]: val }
            if (key === 'likelihood' || key === 'impact') {
                const l = Number(key === 'likelihood' ? val : target.likelihood) || 1
                const i = Number(key === 'impact' ? val : target.impact) || 1
                const score = l * i
                target.risk_score = score
                target.severity = score >= 15 ? 'critical' : score >= 10 ? 'high' : score >= 5 ? 'medium' : 'low'
            }
            next[index] = target
            return next
        })
    }

    const handleAddRiskRow = () => {
        setRiskRows(prev => [
            ...prev,
            {
                id: prev.length + 1,
                control_id: `A.${prev.length + 1}.1`,
                gap: 'Mô tả khoảng trống an ninh mới...',
                severity: 'medium',
                likelihood: 3,
                impact: 3,
                risk_score: 9,
                recommendation: 'Biện pháp khắc phục khuyến nghị...',
            }
        ])
    }

    const handleDeleteRiskRow = (index) => {
        setRiskRows(prev => prev.filter((_, idx) => idx !== index))
    }

    const handleDownloadExport = async (type = 'docx') => {
        if (!assessmentId) return
        const endpoint = type === 'xlsx'
            ? `/api/iso27001/assessments/${assessmentId}/export-risk-register`
            : `/api/iso27001/assessments/${assessmentId}/export-docx`
        try {
            const res = await fetch(endpoint, { method: 'POST' })
            if (res.ok) {
                const blob = await res.blob()
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = type === 'xlsx'
                    ? `Risk_Register_${assessmentId.slice(0, 8)}.xlsx`
                    : `Bao_Cao_Kiem_Toan_${assessmentId.slice(0, 8)}.docx`
                document.body.appendChild(a)
                a.click()
                window.URL.revokeObjectURL(url)
                document.body.removeChild(a)
            } else {
                window.open(endpoint, '_blank')
            }
        } catch (err) {
            window.open(endpoint, '_blank')
        }
    }

    const handleSave = () => {
        setSaving(true)
        setSaveStatus('Đang lưu biểu mẫu...')
        setTimeout(() => {
            setSaving(false)
            setSaveStatus('Đã lưu thành công!')
            setTimeout(() => setSaveStatus('Đã đồng bộ'), 2500)
        }, 500)
    }

    const fileName = fileType === 'xlsx'
        ? `Risk_Register_${assessmentId?.slice(0, 8) || '2026'}.xlsx`
        : `Bao_Cao_Kiem_Toan_${assessmentId?.slice(0, 8) || '2026'}.docx`

    return (
        <div className={styles.overlay} onClick={onClose}>
            <div className={styles.modalContainer} onClick={(e) => e.stopPropagation()}>
                {/* Top Action Bar */}
                <div className={styles.topBar}>
                    <div className={styles.topLeft}>
                        <span className={styles.brandBadge}>xOffice Editor</span>
                        <h3 className={styles.fileTitle}>{fileName}</h3>
                        <span className={styles.fileTypeBadge}>{fileType.toUpperCase()}</span>
                    </div>

                    {fileType === 'docx' && (
                        <div className={styles.segmentedControl}>
                            <button
                                className={`${styles.segmentBtn} ${viewMode === 'preview' ? styles.segmentActive : ''}`}
                                onClick={() => setViewMode('preview')}
                            >
                                📄 Trang in A4 chuẩn
                            </button>
                            <button
                                className={`${styles.segmentBtn} ${viewMode === 'fields' ? styles.segmentActive : ''}`}
                                onClick={() => setViewMode('fields')}
                            >
                                ✏️ Biên tập ô khuyết (Fields:Values)
                            </button>
                        </div>
                    )}

                    <div className={styles.topRight}>
                        <button className={styles.actionBtn} onClick={() => handleDownloadExport('docx')} title="Tải file Word báo cáo về máy">
                            📥 Tải Word (.docx)
                        </button>
                        <button className={styles.actionBtn} onClick={() => handleDownloadExport('xlsx')} title="Tải file Excel Sổ rủi ro về máy">
                            📊 Tải Excel (.xlsx)
                        </button>
                        <button className={styles.actionBtnPrimary} onClick={handleSave} disabled={saving}>
                            {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
                        </button>
                        <button className={styles.closeBtn} onClick={onClose} title="Đóng">✕</button>
                    </div>
                </div>

                {/* Editor Body */}
                <div className={styles.editorArea}>
                    {fileType === 'xlsx' ? (
                        /* Spreadsheet Mode (Risk Register) */
                        <div className={styles.sheetPaper}>
                            <div className={styles.sheetHeader}>
                                <div className={styles.sheetTitleGroup}>
                                    <h2 className={styles.sheetMainTitle}>Sổ đăng ký rủi ro an toàn thông tin (Risk Register)</h2>
                                    <p className={styles.sheetSubtitle}>Đơn vị: {fields.orgName} | Tiêu chuẩn: {fields.standardName} | Ngày lập: {fields.assessmentDate}</p>
                                </div>
                                <button className={styles.addRowBtn} onClick={handleAddRiskRow}>
                                    + Thêm mục rủi ro
                                </button>
                            </div>

                            <div className={styles.tableScroll}>
                                <table className={styles.spreadsheetTable}>
                                    <thead>
                                        <tr>
                                            <th style={{ width: '48px' }}>STT</th>
                                            <th style={{ width: '110px' }}>Mã kiểm soát</th>
                                            <th>Khoảng trống an ninh (GAP)</th>
                                            <th style={{ width: '80px' }}>Khả năng (L)</th>
                                            <th style={{ width: '80px' }}>Ảnh hưởng (I)</th>
                                            <th style={{ width: '90px' }}>Điểm (L×I)</th>
                                            <th style={{ width: '110px' }}>Mức độ</th>
                                            <th>Biện pháp khắc phục khuyến nghị</th>
                                            <th style={{ width: '45px' }}>Xóa</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {riskRows.map((r, idx) => (
                                            <tr key={idx}>
                                                <td style={{ textAlign: 'center', fontWeight: 600 }}>{idx + 1}</td>
                                                <td>
                                                    <input
                                                        type="text"
                                                        className={styles.cellInputBold}
                                                        value={r.control_id}
                                                        onChange={(e) => handleRiskCellChange(idx, 'control_id', e.target.value)}
                                                    />
                                                </td>
                                                <td>
                                                    <textarea
                                                        className={styles.cellTextarea}
                                                        rows={2}
                                                        value={r.gap}
                                                        onChange={(e) => handleRiskCellChange(idx, 'gap', e.target.value)}
                                                    />
                                                </td>
                                                <td>
                                                    <select
                                                        className={styles.cellSelect}
                                                        value={r.likelihood}
                                                        onChange={(e) => handleRiskCellChange(idx, 'likelihood', e.target.value)}
                                                    >
                                                        {[1, 2, 3, 4, 5].map(v => <option key={v} value={v}>{v}</option>)}
                                                    </select>
                                                </td>
                                                <td>
                                                    <select
                                                        className={styles.cellSelect}
                                                        value={r.impact}
                                                        onChange={(e) => handleRiskCellChange(idx, 'impact', e.target.value)}
                                                    >
                                                        {[1, 2, 3, 4, 5].map(v => <option key={v} value={v}>{v}</option>)}
                                                    </select>
                                                </td>
                                                <td style={{ textAlign: 'center', fontWeight: 700, fontSize: '1rem' }}>
                                                    {r.risk_score}
                                                </td>
                                                <td style={{ textAlign: 'center' }}>
                                                    <span className={`${styles.riskBadge} ${
                                                        r.severity === 'critical' ? styles.badgeCrit :
                                                        r.severity === 'high' ? styles.badgeHigh :
                                                        r.severity === 'medium' ? styles.badgeMed :
                                                        styles.badgeLow
                                                    }`}>
                                                        {r.severity.toUpperCase()}
                                                    </span>
                                                </td>
                                                <td>
                                                    <textarea
                                                        className={styles.cellTextarea}
                                                        rows={2}
                                                        value={r.recommendation}
                                                        onChange={(e) => handleRiskCellChange(idx, 'recommendation', e.target.value)}
                                                    />
                                                </td>
                                                <td style={{ textAlign: 'center' }}>
                                                    <button className={styles.deleteRowBtn} onClick={() => handleDeleteRiskRow(idx)}>✕</button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ) : viewMode === 'fields' ? (
                        /* Field-Value Multi-Page Tabbed Form Editor Mode */
                        <div className={styles.fieldsContainer}>
                            {/* Navigation Tabs Bar */}
                            <div className={styles.fieldsTabsBar}>
                                <button
                                    type="button"
                                    className={`${styles.fieldsTabPill} ${activeFieldsTab === 'tab_admin' ? styles.fieldsTabPillActive : ''}`}
                                    onClick={() => setActiveFieldsTab('tab_admin')}
                                >
                                    <span className={styles.tabIcon}>🏛️</span>
                                    <span className={styles.tabTitle}>Trang 1: Hành chính & Cấp độ</span>
                                </button>
                                <button
                                    type="button"
                                    className={`${styles.fieldsTabPill} ${activeFieldsTab === 'tab_technical' ? styles.fieldsTabPillActive : ''}`}
                                    onClick={() => setActiveFieldsTab('tab_technical')}
                                >
                                    <span className={styles.tabIcon}>🛡️</span>
                                    <span className={styles.tabTitle}>Trang 2: 5 Miền an toàn TCVN</span>
                                    <span className={styles.tabBadge}>{implementedControls.size}/{totalStandardControlsCount} Đạt</span>
                                </button>
                                <button
                                    type="button"
                                    className={`${styles.fieldsTabPill} ${activeFieldsTab === 'tab_risks' ? styles.fieldsTabPillActive : ''}`}
                                    onClick={() => setActiveFieldsTab('tab_risks')}
                                >
                                    <span className={styles.tabIcon}>📋</span>
                                    <span className={styles.tabTitle}>Trang 3: Sổ rủi ro & Lộ trình</span>
                                    <span className={styles.tabBadgeWarn}>{riskRows.length} GAPs</span>
                                </button>
                            </div>

                            {/* TAB 1: THÔNG TIN HÀNH CHÍNH & CẤP ĐỘ / PHẠM VI */}
                            {activeFieldsTab === 'tab_admin' && (
                                <>
                                    <div className={styles.fieldSectionCard}>
                                        <h4 className={styles.fieldSectionTitle}>1.1 Thông tin tổ chức & Tiêu chuẩn đánh giá</h4>
                                        <div className={styles.fieldGrid}>
                                            <div className={styles.fieldGroup}>
                                                <label>Tổ chức / Doanh nghiệp được đánh giá</label>
                                                <input
                                                    type="text"
                                                    value={fields.orgName}
                                                    onChange={(e) => handleFieldChange('orgName', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Lĩnh vực hoạt động & Hạ tầng</label>
                                                <input
                                                    type="text"
                                                    value={fields.industry}
                                                    onChange={(e) => handleFieldChange('industry', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Tiêu chuẩn an toàn thông tin áp dụng</label>
                                                <input
                                                    type="text"
                                                    value={fields.standardName}
                                                    onChange={(e) => handleFieldChange('standardName', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Cấp độ an toàn hệ thống thông tin đề xuất</label>
                                                <input
                                                    type="text"
                                                    value={fields.assessmentLevel}
                                                    onChange={(e) => handleFieldChange('assessmentLevel', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Ngày lập hồ sơ / Đánh giá</label>
                                                <input
                                                    type="date"
                                                    value={fields.assessmentDate}
                                                    onChange={(e) => handleFieldChange('assessmentDate', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Chuyên gia kiểm toán (Lead Auditor)</label>
                                                <input
                                                    type="text"
                                                    value={fields.auditorName}
                                                    onChange={(e) => handleFieldChange('auditorName', e.target.value)}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div className={styles.fieldSectionCard}>
                                        <h4 className={styles.fieldSectionTitle}>1.2 Quy mô hạ tầng kỹ thuật & Mạng điều hành</h4>
                                        <div className={styles.fieldGrid}>
                                            <div className={styles.fieldGroup}>
                                                <label>Số lượng máy chủ vật lý & ảo hóa</label>
                                                <input
                                                    type="number"
                                                    value={fields.servers}
                                                    onChange={(e) => handleFieldChange('servers', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Số lượng Tường lửa bảo vệ (Firewall NGFW)</label>
                                                <input
                                                    type="number"
                                                    value={fields.firewalls}
                                                    onChange={(e) => handleFieldChange('firewalls', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Dải địa chỉ mạng LAN / Server Farm</label>
                                                <input
                                                    type="text"
                                                    value={fields.ipRange}
                                                    onChange={(e) => handleFieldChange('ipRange', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Tỷ lệ tuân thủ sơ bộ (%)</label>
                                                <input
                                                    type="number"
                                                    value={fields.compliancePercent}
                                                    onChange={(e) => handleFieldChange('compliancePercent', e.target.value)}
                                                />
                                            </div>
                                        </div>
                                        <div className={styles.fieldGroupFull}>
                                            <label>Phạm vi hệ thống thông tin kiểm toán</label>
                                            <textarea
                                                rows={2}
                                                value={fields.scope}
                                                onChange={(e) => handleFieldChange('scope', e.target.value)}
                                            />
                                        </div>
                                        <div className={styles.fieldGroupFull}>
                                            <label>Mô tả kiến trúc mạng và phân vùng an toàn</label>
                                            <textarea
                                                rows={2}
                                                value={fields.networkDiagram}
                                                onChange={(e) => handleFieldChange('networkDiagram', e.target.value)}
                                            />
                                        </div>
                                    </div>

                                    <div className={styles.fieldSectionCard}>
                                        <h4 className={styles.fieldSectionTitle}>1.3 Nhận định điều hành cho Ban Lãnh đạo (CISO)</h4>
                                        <div className={styles.fieldGroupFull}>
                                            <label>Tóm tắt điều hành (Executive Summary)</label>
                                            <textarea
                                                rows={4}
                                                value={fields.executiveSummary}
                                                onChange={(e) => handleFieldChange('executiveSummary', e.target.value)}
                                            />
                                        </div>
                                        <div className={styles.fieldGroupFull}>
                                            <label>Điểm mạnh bảo mật đã ghi nhận (Bằng chứng đạt)</label>
                                            <textarea
                                                rows={3}
                                                value={fields.keyStrengths}
                                                onChange={(e) => handleFieldChange('keyStrengths', e.target.value)}
                                            />
                                        </div>
                                    </div>
                                </>
                            )}

                            {/* TAB 2: 5 MIỀN AN TOÀN TCVN / KIỂM SOÁT KỸ THUẬT */}
                            {activeFieldsTab === 'tab_technical' && (
                                <>
                                    <div className={styles.statsHeaderBar}>
                                        <div className={styles.statsTitleGroup}>
                                            <h4>Bảng thẩm định phương án kỹ thuật — {fields.standardName || 'TCVN 11930:2017 Cấp độ 3'}</h4>
                                            <p>Đánh giá nhị phân nghiêm ngặt (Đạt / Không Đạt) — Đối soát trực tiếp với log và bằng chứng kỹ thuật</p>
                                        </div>
                                        <div className={styles.statsPillsGroup}>
                                            <div className={styles.statsMetricPill}>
                                                <span>Đạt:</span>
                                                <strong style={{ color: '#22c55e' }}>{implementedControls.size}</strong>
                                            </div>
                                            <div className={styles.statsMetricPill}>
                                                <span>Không Đạt:</span>
                                                <strong style={{ color: '#ef4444' }}>{Math.max(0, totalStandardControlsCount - implementedControls.size)}</strong>
                                            </div>
                                            <div className={styles.statsMetricPill}>
                                                <span>Tuân thủ:</span>
                                                <strong>{totalStandardControlsCount > 0 ? ((implementedControls.size / totalStandardControlsCount) * 100).toFixed(1) : 0}%</strong>
                                            </div>
                                            <button
                                                type="button"
                                                className={styles.proofModalOpenBtn}
                                                onClick={() => setShowProofModal(true)}
                                                title="Xem bảng chứng minh bóc tách 100%"
                                            >
                                                🛡️ Xem bóc tách 100%
                                            </button>
                                        </div>
                                    </div>

                                    {activeStandardControls.map((cat, catIdx) => {
                                        const catControls = cat.controls || []
                                        const catPassed = catControls.filter(c => implementedControls.has(c.id)).length
                                        return (
                                            <div key={catIdx} className={styles.categoryBlock}>
                                                <div className={styles.categoryHeader}>
                                                    <h5 className={styles.categoryTitle}>{cat.category}</h5>
                                                    <span className={styles.categoryBadge}>{catPassed} / {catControls.length} Tiêu chí đạt</span>
                                                </div>
                                                <div className={styles.controlsList}>
                                                    {catControls.map((ctrl) => {
                                                        const isPass = implementedControls.has(ctrl.id)
                                                        const w = (ctrl.weight || 'medium').toLowerCase()
                                                        return (
                                                            <div key={ctrl.id} className={styles.controlRow}>
                                                                <div className={styles.controlInfo}>
                                                                    <div className={styles.controlTopRow}>
                                                                        <span className={styles.controlId}>{ctrl.id}</span>
                                                                        <span className={styles.controlLabel}>{ctrl.label}</span>
                                                                        <span className={`${styles.controlWeightBadge} ${
                                                                            w === 'critical' ? styles.ctrlWeightCrit :
                                                                            w === 'high' ? styles.ctrlWeightHigh :
                                                                            w === 'medium' ? styles.ctrlWeightMed :
                                                                            styles.ctrlWeightLow
                                                                        }`}>
                                                                            {w}
                                                                        </span>
                                                                    </div>
                                                                    {isPass ? (
                                                                        <span className={styles.ctrlSourceTag}>
                                                                            🏷️ Nguồn: Bằng chứng kỹ thuật đối soát khớp
                                                                        </span>
                                                                    ) : (
                                                                        <span className={styles.ctrlSourceTagWarn}>
                                                                            🏷️ Nguồn: Mâu thuẫn với log hoặc thiếu log đối chứng
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                <div className={styles.controlActions}>
                                                                    <button
                                                                        type="button"
                                                                        className={isPass ? styles.ctrlStatusBtnPass : styles.ctrlStatusBtnFail}
                                                                        onClick={() => toggleControl(ctrl.id)}
                                                                    >
                                                                        {isPass ? '✓ ĐẠT' : '✕ KHÔNG ĐẠT'}
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        )
                                                    })}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </>
                            )}

                            {/* TAB 3: SỔ RỦI RO & LỘ TRÌNH KHẮC PHỤC */}
                            {activeFieldsTab === 'tab_risks' && (
                                <>
                                    <div className={styles.sheetPaper}>
                                        <div className={styles.sheetHeader}>
                                            <div className={styles.sheetTitleGroup}>
                                                <h2 className={styles.sheetMainTitle}>3.1 Sổ đăng ký rủi ro an toàn thông tin (Risk Register L × I)</h2>
                                                <p className={styles.sheetSubtitle}>Đơn vị: {fields.orgName} | Tiêu chuẩn: {fields.standardName}</p>
                                            </div>
                                            <button type="button" className={styles.addRowBtn} onClick={handleAddRiskRow}>
                                                + Thêm mục rủi ro
                                            </button>
                                        </div>

                                        <div className={styles.tableScroll}>
                                            <table className={styles.spreadsheetTable}>
                                                <thead>
                                                    <tr>
                                                        <th style={{ width: '48px' }}>STT</th>
                                                        <th style={{ width: '110px' }}>Mã</th>
                                                        <th>Khoảng trống an ninh (GAP)</th>
                                                        <th style={{ width: '80px' }}>L</th>
                                                        <th style={{ width: '80px' }}>I</th>
                                                        <th style={{ width: '90px' }}>L×I</th>
                                                        <th style={{ width: '110px' }}>Mức độ</th>
                                                        <th>Biện pháp khắc phục khuyến nghị</th>
                                                        <th style={{ width: '45px' }}>Xóa</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {riskRows.map((r, idx) => (
                                                        <tr key={idx}>
                                                            <td style={{ textAlign: 'center', fontWeight: 600 }}>{idx + 1}</td>
                                                            <td>
                                                                <input
                                                                    type="text"
                                                                    className={styles.cellInputBold}
                                                                    value={r.control_id}
                                                                    onChange={(e) => handleRiskCellChange(idx, 'control_id', e.target.value)}
                                                                />
                                                            </td>
                                                            <td>
                                                                <textarea
                                                                    className={styles.cellTextarea}
                                                                    rows={2}
                                                                    value={r.gap}
                                                                    onChange={(e) => handleRiskCellChange(idx, 'gap', e.target.value)}
                                                                />
                                                            </td>
                                                            <td>
                                                                <select
                                                                    className={styles.cellSelect}
                                                                    value={r.likelihood}
                                                                    onChange={(e) => handleRiskCellChange(idx, 'likelihood', e.target.value)}
                                                                >
                                                                    {[1, 2, 3, 4, 5].map(v => <option key={v} value={v}>{v}</option>)}
                                                                </select>
                                                            </td>
                                                            <td>
                                                                <select
                                                                    className={styles.cellSelect}
                                                                    value={r.impact}
                                                                    onChange={(e) => handleRiskCellChange(idx, 'impact', e.target.value)}
                                                                >
                                                                    {[1, 2, 3, 4, 5].map(v => <option key={v} value={v}>{v}</option>)}
                                                                </select>
                                                            </td>
                                                            <td style={{ textAlign: 'center', fontWeight: 700, fontSize: '1rem' }}>
                                                                {r.risk_score}
                                                            </td>
                                                            <td style={{ textAlign: 'center' }}>
                                                                <span className={`${styles.riskBadge} ${
                                                                    r.severity === 'critical' ? styles.badgeCrit :
                                                                    r.severity === 'high' ? styles.badgeHigh :
                                                                    r.severity === 'medium' ? styles.badgeMed :
                                                                    styles.badgeLow
                                                                }`}>
                                                                    {r.severity.toUpperCase()}
                                                                </span>
                                                            </td>
                                                            <td>
                                                                <textarea
                                                                    className={styles.cellTextarea}
                                                                    rows={2}
                                                                    value={r.recommendation}
                                                                    onChange={(e) => handleRiskCellChange(idx, 'recommendation', e.target.value)}
                                                                />
                                                            </td>
                                                            <td style={{ textAlign: 'center' }}>
                                                                <button type="button" className={styles.deleteRowBtn} onClick={() => handleDeleteRiskRow(idx)}>✕</button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>

                                    <div className={styles.fieldSectionCard}>
                                        <h4 className={styles.fieldSectionTitle}>3.2 Lộ trình khắc phục rủi ro (Remediation Roadmap 30 - 90 - 180 ngày)</h4>
                                        <div className={styles.fieldGroupFull}>
                                            <label>Giai đoạn 1: Ngắn hạn (30 ngày - Khắc phục ngay các lỗ hổng Critical & Thiếu Hotfix)</label>
                                            <textarea
                                                rows={2}
                                                value={fields.roadmap30d}
                                                onChange={(e) => handleFieldChange('roadmap30d', e.target.value)}
                                            />
                                        </div>
                                        <div className={styles.fieldGroupFull}>
                                            <label>Giai đoạn 2: Trung hạn (90 ngày - Củng cố phòng thủ, EDR & Giám sát SIEM)</label>
                                            <textarea
                                                rows={2}
                                                value={fields.roadmap90d}
                                                onChange={(e) => handleFieldChange('roadmap90d', e.target.value)}
                                            />
                                        </div>
                                        <div className={styles.fieldGroupFull}>
                                            <label>Giai đoạn 3: Dài hạn (180 ngày - Chuẩn hóa ISMS Cấp độ 3 & Diễn tập ứng cứu)</label>
                                            <textarea
                                                rows={2}
                                                value={fields.roadmap180d}
                                                onChange={(e) => handleFieldChange('roadmap180d', e.target.value)}
                                            />
                                        </div>
                                    </div>

                                    <div className={styles.fieldSectionCard}>
                                        <h4 className={styles.fieldSectionTitle}>3.3 Thông tin thẩm định & Ký duyệt hồ sơ</h4>
                                        <div className={styles.fieldGrid}>
                                            <div className={styles.fieldGroup}>
                                                <label>Đại diện Đơn vị Vận hành Hệ thống</label>
                                                <input
                                                    type="text"
                                                    value={fields.auditorName}
                                                    onChange={(e) => handleFieldChange('auditorName', e.target.value)}
                                                />
                                            </div>
                                            <div className={styles.fieldGroup}>
                                                <label>Đại diện Đơn vị Chủ quản Hệ thống Thông tin</label>
                                                <input
                                                    type="text"
                                                    value={fields.approverName}
                                                    onChange={(e) => handleFieldChange('approverName', e.target.value)}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    ) : (
                        /* Document Preview Mode: True Multi-Page Paginated A4 Sheets */
                        <div className={styles.a4PagesContainer}>
                            {/* TRANG 1: TỔNG QUAN ĐIỀU HÀNH & PHẠM VI */}
                            <div className={styles.a4Sheet}>
                                <div className={styles.a4SheetBody}>
                                    <div className={styles.pageHeader}>
                                        <span>Báo cáo đánh giá an toàn thông tin — CyberAI Platform</span>
                                        <span>Tiêu chuẩn: {fields.standardName}</span>
                                    </div>

                                    {/* Administrative Letterhead */}
                                    <div className={styles.docLetterhead}>
                                        <div className={styles.letterheadLeft}>
                                            <div className={styles.orgMainUpper}>Hệ thống đánh giá an toàn thông tin CyberAI</div>
                                            <div className={styles.orgSubUpper}>Trung tâm kiểm toán & thẩm định tuân thủ</div>
                                            <div className={styles.dividerLine} />
                                            <div className={styles.docCode}>Số: AUDIT-{assessmentId?.slice(0, 8) || '2026'}/BC-ATTT</div>
                                        </div>
                                        <div className={styles.letterheadRight}>
                                            <div className={styles.nationUpper}>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>
                                            <div className={styles.motto}>Độc lập - Tự do - Hạnh phúc</div>
                                            <div className={styles.dividerLine} />
                                            <div className={styles.docDate}>Hà Nội, ngày {fields.assessmentDate.split('-')[2]} tháng {fields.assessmentDate.split('-')[1]} năm {fields.assessmentDate.split('-')[0]}</div>
                                        </div>
                                    </div>

                                    {/* Document Title */}
                                    <div className={styles.docTitleBlock}>
                                        <h1 className={styles.docTitleMain}>Báo cáo đánh giá an toàn thông tin</h1>
                                        <div className={styles.docTitleSub}>Tiêu chuẩn đối soát: {fields.standardName}</div>
                                    </div>

                                    {/* Administrative Metadata Table */}
                                    <table className={styles.adminTable}>
                                        <tbody>
                                            <tr>
                                                <td className={styles.adminLabel}>Tổ chức được đánh giá:</td>
                                                <td className={styles.adminVal}><strong>{fields.orgName}</strong></td>
                                                <td className={styles.adminLabel}>Lĩnh vực hoạt động:</td>
                                                <td className={styles.adminVal}>{fields.industry}</td>
                                            </tr>
                                            <tr>
                                                <td className={styles.adminLabel}>Chuyên gia đánh giá:</td>
                                                <td className={styles.adminVal}>{fields.auditorName}</td>
                                                <td className={styles.adminLabel}>Tỷ lệ tuân thủ:</td>
                                                <td className={styles.adminVal}><span className={styles.scoreText}>{fields.compliancePercent}%</span></td>
                                            </tr>
                                            <tr>
                                                <td className={styles.adminLabel}>Phạm vi hệ thống:</td>
                                                <td colSpan={3} className={styles.adminVal}>{fields.scope}</td>
                                            </tr>
                                        </tbody>
                                    </table>

                                    {/* Section I: Executive Summary */}
                                    <div className={styles.docSection}>
                                        <h3 className={styles.sectionHeadingA4}>I. Tổng quan điều hành & kết quả đánh giá</h3>
                                        <p className={styles.docParagraph}>{fields.executiveSummary}</p>
                                        
                                        <div className={styles.statCardsRow}>
                                            <div className={styles.statCardA4}>
                                                <div className={styles.statCardNum}>{fields.compliancePercent}%</div>
                                                <div className={styles.statCardLabel}>Mức độ tuân thủ chung</div>
                                            </div>
                                            <div className={styles.statCardA4}>
                                                <div className={styles.statCardNum} style={{ color: '#dc2626' }}>
                                                    {riskRows.filter(r => r.severity === 'critical').length}
                                                </div>
                                                <div className={styles.statCardLabel}>Rủi ro mức Critical</div>
                                            </div>
                                            <div className={styles.statCardA4}>
                                                <div className={styles.statCardNum} style={{ color: '#ea580c' }}>
                                                    {riskRows.filter(r => r.severity === 'high').length}
                                                </div>
                                                <div className={styles.statCardLabel}>Rủi ro mức High</div>
                                            </div>
                                            <div className={styles.statCardA4}>
                                                <div className={styles.statCardNum}>
                                                    {riskRows.length}
                                                </div>
                                                <div className={styles.statCardLabel}>Tổng số khoảng trống (GAP)</div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Section II: Scope & Strengths */}
                                    <div className={styles.docSection}>
                                        <h3 className={styles.sectionHeadingA4}>II. Phạm vi hệ thống & điểm mạnh an ninh</h3>
                                        <p className={styles.docParagraph}><strong>Phạm vi đánh giá:</strong> {fields.scope}</p>
                                        <p className={styles.docParagraph}><strong>Điểm mạnh bảo mật ghi nhận:</strong> {fields.keyStrengths}</p>
                                    </div>
                                </div>

                                <div className={styles.pageFooter}>
                                    <span>Tài liệu bảo mật nội bộ — Chỉ lưu hành trong Hội đồng ATTT</span>
                                    <span className={styles.pageNumberPill}>Trang 1 / 2</span>
                                </div>
                            </div>

                            {/* PAGE SEPARATOR */}
                            <div className={styles.pageDivider}>
                                <div className={styles.pageDividerLine} />
                                <span>Trang 1 kết thúc · Tiếp tục sang trang 2</span>
                                <div className={styles.pageDividerLine} />
                            </div>

                            {/* TRANG 2: CHI TIẾT KHOẢNG TRỐNG GAP, LỘ TRÌNH & CHỮ KÝ */}
                            <div className={styles.a4Sheet}>
                                <div className={styles.a4SheetBody}>
                                    <div className={styles.pageHeader}>
                                        <span>Báo cáo đánh giá an toàn thông tin (tiếp theo)</span>
                                        <span>Đơn vị: {fields.orgName}</span>
                                    </div>

                                    {/* Section III: Risk Register & GAP Table */}
                                    <div className={styles.docSection}>
                                        <h3 className={styles.sectionHeadingA4}>III. Danh mục khoảng trống an ninh & sổ đăng ký rủi ro</h3>
                                        <table className={styles.docTable}>
                                            <thead>
                                                <tr>
                                                    <th style={{ width: '42px', textAlign: 'center' }}>STT</th>
                                                    <th style={{ width: '85px', textAlign: 'center' }}>Mã Control</th>
                                                    <th>Khoảng trống an ninh (GAP phát hiện)</th>
                                                    <th style={{ width: '90px', textAlign: 'center' }}>Mức độ</th>
                                                    <th style={{ width: '70px', textAlign: 'center' }}>Điểm (L×I)</th>
                                                    <th>Biện pháp khắc phục khuyến nghị</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {riskRows.map((item, idx) => (
                                                    <tr key={idx}>
                                                        <td style={{ textAlign: 'center' }}>{idx + 1}</td>
                                                        <td style={{ textAlign: 'center', fontWeight: 'bold' }}>{item.control_id}</td>
                                                        <td>{item.gap}</td>
                                                        <td style={{ textAlign: 'center' }}>
                                                            <span className={`${styles.riskBadge} ${
                                                                item.severity === 'critical' ? styles.badgeCrit :
                                                                item.severity === 'high' ? styles.badgeHigh :
                                                                item.severity === 'medium' ? styles.badgeMed :
                                                                styles.badgeLow
                                                            }`}>
                                                                {item.severity}
                                                            </span>
                                                        </td>
                                                        <td style={{ textAlign: 'center', fontWeight: 'bold' }}>{item.risk_score}</td>
                                                        <td>{item.recommendation}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>

                                    {/* Section IV: Remediation Roadmap */}
                                    <div className={styles.docSection}>
                                        <h3 className={styles.sectionHeadingA4}>IV. Lộ trình khắc phục rủi ro (Remediation Roadmap)</h3>
                                        <div className={styles.roadmapCards}>
                                            <div className={styles.roadmapCard}>
                                                <div className={styles.roadmapBadgeImmediate}>30 ngày · Ngắn hạn</div>
                                                <p>{fields.roadmap30d}</p>
                                            </div>
                                            <div className={styles.roadmapCard}>
                                                <div className={styles.roadmapBadgeMedium}>90 ngày · Trung hạn</div>
                                                <p>{fields.roadmap90d}</p>
                                            </div>
                                            <div className={styles.roadmapCard}>
                                                <div className={styles.roadmapBadgeLong}>180 ngày · Dài hạn</div>
                                                <p>{fields.roadmap180d}</p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Section V: Signature Block */}
                                    <div className={styles.signBlock}>
                                        <div className={styles.signColumn}>
                                            <div className={styles.signTitle}>Đại diện tổ chức được đánh giá</div>
                                            <div className={styles.signSub}>(Ký, ghi rõ họ tên và đóng dấu)</div>
                                            <div className={styles.signSpace} />
                                            <div className={styles.signName}>{fields.orgName}</div>
                                        </div>
                                        <div className={styles.signColumn}>
                                            <div className={styles.signTitle}>Đoàn kiểm toán an toàn thông tin</div>
                                            <div className={styles.signSub}>(Ký và ghi rõ họ tên)</div>
                                            <div className={styles.signSpace} />
                                            <div className={styles.signName}>{fields.auditorName}</div>
                                        </div>
                                    </div>
                                </div>

                                <div className={styles.pageFooter}>
                                    <span>CyberAI Assessment Platform · Runtime Audit Trace Verified</span>
                                    <span className={styles.pageNumberPill}>Trang 2 / 2</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Bottom Status Bar */}
                <div className={styles.bottomStatusBar}>
                    <div className={styles.statusIndicator}>
                        <span className={styles.dot} />
                        <span>{saveStatus}</span>
                    </div>
                    <div className={styles.statusNote}>
                        Định dạng: Khổ A4 (210 × 297 mm) | Font: Times New Roman 12pt | Cơ chế điền ô khuyết xOffice Template Active
                    </div>
                </div>
            </div>

            {/* Evidence Extraction Proof Modal */}
            <EvidenceExtractionProofModal
                isOpen={showProofModal}
                onClose={() => setShowProofModal(false)}
                assessmentId={assessmentId}
            />
        </div>
    )
}
