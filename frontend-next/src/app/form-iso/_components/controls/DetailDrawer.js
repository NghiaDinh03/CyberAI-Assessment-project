'use client'

import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './DetailDrawer.module.css'
import EvidenceThumb from './EvidenceThumb'
import { useTranslation } from '@/components/LanguageProvider'

/**
 * Overlay drawer showing control details. Does NOT reflow the grid below.
 */
const TECHNICAL_COMMANDS = {
    // Firewall & Network
    'A.8.20': 'netsh advfirewall show allprofiles\nGet-NetFirewallRule -Enabled True | Select-Object DisplayName, Direction, Action',
    'NW.02': 'netsh advfirewall show allprofiles\nGet-NetFirewallRule -Enabled True | Select-Object DisplayName, Direction, Action',
    'A.8.22': 'route print\nGet-NetIPConfiguration',
    'NW.01': 'route print\nGet-NetIPConfiguration',
    'A.8.24': 'manage-bde -status\nGet-TlsCipherSuite | Select-Object -First 5',
    'NW.04': 'manage-bde -status\nGet-TlsCipherSuite | Select-Object -First 5',

    // Patch & Vulnerability Management
    'A.8.8': 'Get-Hotfix | Sort-Object InstalledOn -Descending | Select-Object -First 10',
    'SV.07': 'Get-Hotfix | Sort-Object InstalledOn -Descending | Select-Object -First 10',
    'SV.06': 'wmic qfe list brief /format:table',

    // Antivirus & Malware Protection
    'A.8.7': 'Get-MpComputerStatus | Select-Object AMServiceEnabled, AntispywareSignatureVersion, RealTimeProtectionEnabled',
    'SV.02': 'Get-MpComputerStatus | Select-Object AMServiceEnabled, AntispywareSignatureVersion, RealTimeProtectionEnabled',

    // Passwords, Authentication & Access Rights
    'A.8.5': 'net accounts\nGet-ADDefaultDomainPasswordPolicy',
    'SV.01': 'net accounts\nGet-ADDefaultDomainPasswordPolicy',
    'A.8.2': 'Get-LocalGroupMember -Group "Administrators" | Select-Object Name, PrincipalSource',
    'AC.01': 'Get-LocalGroupMember -Group "Administrators" | Select-Object Name, PrincipalSource',

    // Backup & Recovery
    'A.8.13': 'wbadmin get status\nwbadmin get versions',
    'DAT.01': 'wbadmin get status\nwbadmin get versions',

    // Logging & Monitoring
    'A.8.15': 'wevtutil gl Security\nauditpol /get /category:*',
    'SV.08': 'wevtutil gl Security\nauditpol /get /category:*',
    'A.8.16': 'Get-EventLog -LogName System -Newest 10 -EntryType Error,Warning',
    'SV.09': 'Get-EventLog -LogName System -Newest 10 -EntryType Error,Warning',

    // Configuration & Endpoint
    'A.8.9': 'systeminfo | Select-String "OS Name", "OS Version", "System Type"',
    'SV.04': 'systeminfo | Select-String "OS Name", "OS Version", "System Type"',
    'A.8.1': 'Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
    'SV.03': 'Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',
}

const getPitfallText = (id, locale) => {
    if (id.startsWith('A.5') || id.startsWith('QL')) {
        return locale === 'vi'
            ? 'Văn bản chính sách chưa có chữ ký phê duyệt chính thức của lãnh đạo, ban hành dưới dạng dự thảo, hoặc quá 12 tháng chưa được rà soát cập nhật định kỳ.'
            : 'Policy draft unapproved by management, missing signature, or not reviewed within the last 12 months.'
    }
    if (id.startsWith('A.6') || id.startsWith('NS')) {
        return locale === 'vi'
            ? 'Nhân viên mới chưa ký cam kết bảo mật thông tin (NDA) trước khi cấp quyền truy cập, hoặc chưa hoàn thành khóa đào tạo nhận thức an toàn thông tin hàng năm.'
            : 'New employees missing signed NDA before access grant, or annual security awareness training records missing.'
    }
    if (id.startsWith('A.7') || id.startsWith('VL')) {
        return locale === 'vi'
            ? 'Không có camera hoặc nhật ký ghi nhận người ra vào phòng máy chủ / Data Center; thiết bị PCCC hoặc nguồn điện dự phòng UPS không được kiểm tra định kỳ.'
            : 'No access log or CCTV for server room; fire suppression and UPS power untested periodically.'
    }
    if (id.includes('8.20') || id.includes('NW.02')) {
        return locale === 'vi'
            ? 'Mở cổng dịch vụ quản trị (3389/RDP, 22/SSH, 445/SMB) trực tiếp ra ngoài Internet mà không qua kênh truyền mã hóa VPN.'
            : 'Sensitive ports (3389/RDP, 22/SSH, 445) exposed directly to public internet without VPN.'
    }
    if (id.includes('8.8') || id.includes('SV.07')) {
        return locale === 'vi'
            ? 'Máy chủ còn tồn tại bản vá bảo mật chậm cập nhật quá 30-60 ngày kể từ khi nhà cung cấp phát hành (Cumulative Update).'
            : 'Security patches overdue by more than 30-60 days from vendor release.'
    }
    if (id.includes('8.7') || id.includes('SV.02')) {
        return locale === 'vi'
            ? 'Phần mềm diệt virus bị tắt tính năng quét thời gian thực (Real-time Protection) hoặc cơ sở dữ liệu mẫu nhận diện virus quá 7 ngày chưa cập nhật.'
            : 'Real-time antivirus protection disabled or signatures outdated by more than 7 days.'
    }
    if (id.includes('8.13') || id.includes('DAT.01')) {
        return locale === 'vi'
            ? 'Lưu trữ bản sao lưu (Backup) trên cùng ổ đĩa chứa dữ liệu sản xuất, hoặc chưa từng thực hiện diễn tập khôi phục (Restore Drill) để kiểm tra tính toàn vẹn.'
            : 'Backups stored on the same production disk, or disaster recovery restore drill never tested.'
    }
    return locale === 'vi'
        ? 'Thiếu bằng chứng xác thực (ảnh chụp cấu hình, văn bản phê duyệt hoặc log hệ thống) để chứng minh biện pháp đã được triển khai hiệu quả.'
        : 'Lack of tangible verification proof (configuration export, approval document, or system log).'
}

export default function DetailDrawer({
    open,
    control,
    state,
    onClose,
    onToggleImplemented,
    onUploadFiles,
    onDeleteFile,
    onChangeNotes,
    onExpandFile,
    returnFocusRef,
    standard = 'iso27001',
    selectedModel = 'gemma4:latest',
}) {
    const { t, locale } = useTranslation()
    const [tab, setTab] = useState('criteria')
    const [showGateHint, setShowGateHint] = useState(false)
    const [copiedCmd, setCopiedCmd] = useState(false)
    const panelRef = useRef(null)
    const gateTimerRef = useRef(null)

    // AI Control Assistant states
    const [aiMode, setAiMode] = useState('verify_evidence')
    const [aiLoading, setAiLoading] = useState(false)
    const [aiResponse, setAiResponse] = useState(null)
    const [customQuery, setCustomQuery] = useState('')
    const [copiedAi, setCopiedAi] = useState(false)

    // Reset states when control changes
    useEffect(() => {
        if (open) {
            setTab('criteria')
            setAiResponse(null)
            setCustomQuery('')
        }
    }, [open, control?.id])

    const handleRunAiAssist = async (chosenMode, overrideQuery) => {
        const m = chosenMode || aiMode
        setAiLoading(true)
        setAiMode(m)
        const q = overrideQuery !== undefined ? overrideQuery : customQuery
        try {
            const desc = state?.description
            const evidenceFiles = state?.evidenceFiles || []
            const res = await fetch(`/api/iso27001/controls/${control.id}/ai-assist`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    standard: standard || 'iso27001',
                    control_id: control.id,
                    control_label: control.label,
                    requirement: desc?.requirement || '',
                    criteria: desc?.criteria || '',
                    mode: m,
                    query: q,
                    evidence_filenames: evidenceFiles.map(f => f.filename),
                    notes: state?.notes || '',
                    model: selectedModel || 'gemma4:latest'
                })
            })
            const data = await res.json()
            if (data.status === 'success') {
                setAiResponse(data.response)
            } else {
                setAiResponse(`❌ **Lỗi:** ${data.error || 'Không thể kết nối mô hình AI.'}`)
            }
        } catch (err) {
            setAiResponse(`❌ **Lỗi kết nối máy chủ:** ${err.message}`)
        } finally {
            setAiLoading(false)
        }
    }

    const copyAiResponse = () => {
        if (!aiResponse) return
        navigator.clipboard.writeText(aiResponse)
        setCopiedAi(true)
        setTimeout(() => setCopiedAi(false), 2000)
    }

    // Focus panel on open; restore focus to the opener on close
    useEffect(() => {
        if (!open) return
        const node = panelRef.current
        if (node) node.focus()
        return () => {
            const el = returnFocusRef?.current
            if (el && typeof el.focus === 'function') {
                try { el.focus() } catch (_) {}
            }
        }
    }, [open, returnFocusRef])

    // Esc to close
    useEffect(() => {
        if (!open) return
        const handler = (e) => {
            if (e.key === 'Escape') {
                e.stopPropagation()
                onClose?.()
            }
        }
        window.addEventListener('keydown', handler)
        return () => window.removeEventListener('keydown', handler)
    }, [open, onClose])

    useEffect(() => () => {
        if (gateTimerRef.current) clearTimeout(gateTimerRef.current)
    }, [])

    // Reset hint when control or open state changes
    useEffect(() => { setShowGateHint(false) }, [open, control?.id])

    if (!open || !control) return null

    const desc = state?.description
    const evidenceFiles = state?.evidenceFiles || []
    const implemented = !!state?.implemented

    const isTechnical = (
        control.id.startsWith('A.8') ||
        control.id.startsWith('NW') ||
        control.id.startsWith('SV') ||
        control.id.startsWith('DAT') ||
        control.id.startsWith('APP') ||
        control.id.startsWith('AC')
    )
    const isPolicy = control.id.startsWith('A.5') || control.id.startsWith('QL')
    const isHR = control.id.startsWith('A.6') || control.id.startsWith('NS')
    const isPhysical = control.id.startsWith('A.7') || control.id.startsWith('VL')

    const technicalCmd = TECHNICAL_COMMANDS[control.id] || (isTechnical ? `auditpol /get /category:*\nGet-Service | Where-Object {$_.Status -eq "Running"}` : null)
    const pitfall = getPitfallText(control.id, locale)

    const copyCommand = () => {
        if (!technicalCmd) return
        navigator.clipboard.writeText(technicalCmd)
        setCopiedCmd(true)
        setTimeout(() => setCopiedCmd(false), 2000)
    }

    const handleDrop = (e) => {
        e.preventDefault()
        e.stopPropagation()
        const files = e.dataTransfer?.files
        if (files?.length > 0 && onUploadFiles) onUploadFiles(control.id, files)
    }
    const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation() }

    const headingId = `drawer-heading-${control.id}`

    return (
        <>
            <div className={styles.backdrop} onClick={onClose} aria-hidden="true" />
            <aside
                ref={panelRef}
                className={styles.drawer}
                role="dialog"
                aria-modal="true"
                aria-labelledby={headingId}
                tabIndex={-1}
            >
                <header className={styles.header}>
                    <div className={styles.headerMain}>
                        <div className={styles.headerTop}>
                            <span className={`${styles.chip} ${implemented ? styles.chipOn : styles.chipOff}`}>
                                {implemented
                                    ? (locale === 'vi' ? '✓ ĐÃ TRIỂN KHAI' : '✓ IMPLEMENTED')
                                    : (locale === 'vi' ? 'CHƯA TRIỂN KHAI' : 'NOT IMPLEMENTED')}
                            </span>
                        </div>
                        <h2 id={headingId} className={styles.title}>
                            {control.id}
                        </h2>
                        <p className={styles.subtitle}>{control.label}</p>
                    </div>
                    <button
                        type="button"
                        className={styles.close}
                        onClick={onClose}
                        aria-label={t('common.close')}
                    >✕</button>
                </header>

                <nav className={styles.tabs} role="tablist" aria-label={t('formIso.drawerTabs')}>
                    {[
                        { id: 'criteria', label: t('formIso.tab.criteria') },
                        { id: 'evidence', label: `${t('formIso.tab.evidence')} (${evidenceFiles.length})` },
                        { id: 'ai', label: `🤖 CyberAI (${locale === 'vi' ? 'Trợ lý' : 'Assistant'})` }
                    ].map(tObj => (
                        <button
                            key={tObj.id}
                            type="button"
                            role="tab"
                            aria-selected={tab === tObj.id}
                            className={`${styles.tab} ${tab === tObj.id ? styles.tabActive : ''}`}
                            onClick={() => setTab(tObj.id)}
                        >
                            {tObj.label}
                        </button>
                    ))}
                </nav>

                <div className={styles.body}>
                    {tab === 'criteria' && (
                        <div className={styles.section}>
                            {desc ? (
                                <>
                                    {/* 1. Standard Requirement */}
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{locale === 'vi' ? 'YÊU CẦU TIÊU CHUẨN' : 'STANDARD REQUIREMENT'}</div>
                                        <p className={styles.text}>{desc.requirement}</p>
                                    </div>

                                    {/* 2. Assessment Criteria */}
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{locale === 'vi' ? 'TIÊU CHÍ ĐÁNH GIÁ & NGHIỆM THU' : 'ASSESSMENT CRITERIA'}</div>
                                        <p className={styles.text}>{desc.criteria}</p>
                                    </div>

                                    {/* 3. Technical Commands OR Non-technical Guidance Notice */}
                                    {isTechnical && technicalCmd ? (
                                        <div className={styles.block}>
                                            <div className={styles.blockLabelRow}>
                                                <div className={styles.blockLabel}>{locale === 'vi' ? 'LỆNH KỸ THUẬT THU THẬP BẰNG CHỨNG' : 'TECHNICAL SCAN COMMANDS'}</div>
                                                <button type="button" className={styles.copyCmdBtn} onClick={copyCommand}>
                                                    {copiedCmd ? (locale === 'vi' ? '✓ Đã sao chép' : '✓ Copied') : (locale === 'vi' ? 'Sao chép lệnh' : 'Copy Script')}
                                                </button>
                                            </div>
                                            <pre className={styles.codeBlock}><code>{technicalCmd}</code></pre>
                                        </div>
                                    ) : (
                                        <div className={styles.block}>
                                            <div className={styles.blockLabel}>{locale === 'vi' ? 'HÌNH THỨC THU THẬP BẰNG CHỨNG' : 'EVIDENCE COLLECTION TYPE'}</div>
                                            <div className={styles.nonTechNotice}>
                                                {isPolicy && (locale === 'vi' 
                                                    ? 'Biện pháp Quản lý & Quy định: Không áp dụng lệnh máy chủ. Bằng chứng cần thu thập là văn bản quy định, quy chế ISMS có chữ ký phê duyệt của ban lãnh đạo hoặc biên bản họp rà soát định kỳ.'
                                                    : 'Management & Governance Control: No server command applicable. Provide signed policy documents, ISMS charter, or review meeting minutes.')}
                                                {isHR && (locale === 'vi' 
                                                    ? 'Biện pháp Nhân sự: Không áp dụng lệnh máy chủ. Bằng chứng cần thu thập là cam kết bảo mật thông tin (NDA) có chữ ký, hồ sơ đào tạo nhận thức an toàn thông tin, hoặc biên bản bàn giao khi thôi việc.'
                                                    : 'Human Resources Control: No server command applicable. Provide signed NDA agreements, security awareness training logs, or exit checklists.')}
                                                {isPhysical && (locale === 'vi' 
                                                    ? 'Biện pháp Vật lý & Môi trường: Không áp dụng lệnh máy chủ. Bằng chứng cần thu thập là sơ đồ phòng máy chủ, biên bản kiểm tra PCCC/UPS định kỳ hoặc trích xuất nhật ký quẹt thẻ cửa từ/camera giám sát.'
                                                    : 'Physical Security Control: No server command applicable. Provide data center layout diagrams, fire suppression test logs, or badge access logs.')}
                                                {!isPolicy && !isHR && !isPhysical && (locale === 'vi'
                                                    ? 'Biện pháp Quản lý/Vận hành: Thu thập tài liệu quy trình, biên bản họp hoặc ảnh chụp màn hình minh chứng thực tế.'
                                                    : 'Operational Control: Provide procedural documents, meeting notes, or verified configuration screenshots.')}
                                            </div>
                                        </div>
                                    )}

                                    {/* 4. Common Pitfalls / GAP Triggers */}
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{locale === 'vi' ? 'LỖI GAP THƯỜNG GẶP (DỄ BỊ ĐÁNH TRƯỢT)' : 'COMMON AUDIT PITFALLS'}</div>
                                        <div className={styles.pitfallBox}>
                                            {pitfall}
                                        </div>
                                    </div>

                                    {/* 5. Required Evidence Types */}
                                    {desc.evidence?.length > 0 && (
                                        <div className={styles.block}>
                                            <div className={styles.blockLabel}>
                                                {locale === 'vi' ? 'TÀI LIỆU BẰNG CHỨNG CẦN THU THẬP' : 'REQUIRED EVIDENCE DOCUMENTS'}
                                                <span className={styles.countPill}>{desc.evidence.length} {locale === 'vi' ? 'loại tệp' : 'types'}</span>
                                            </div>
                                            <ul className={styles.evList}>
                                                {desc.evidence.map((ev, i) => (
                                                    <li key={i}>{ev}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* 6. Implementation Guide */}
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{locale === 'vi' ? 'HƯỚNG DẪN TRIỂN KHAI' : 'IMPLEMENTATION GUIDE'}</div>
                                        <p className={styles.hint}>
                                            {desc.hint ||
                                                (implemented
                                                    ? (locale === 'vi' ? 'Biện pháp này đã được đánh dấu triển khai. Hãy đảm bảo tài liệu bằng chứng được cập nhật và lưu trữ đúng nơi.' : 'Control marked as implemented.')
                                                    : (locale === 'vi' ? 'Cần rà soát chính sách, cấu hình máy chủ hoặc tài liệu liên quan trước khi đánh dấu đạt.' : 'Review policies and system settings before marking completed.'))}
                                        </p>
                                    </div>
                                </>
                            ) : (
                                <p className={styles.hint}>{t('assessment.noControlDetail')}</p>
                            )}
                        </div>
                    )}

                    {tab === 'evidence' && (
                        <div className={styles.section}>
                            <div
                                className={styles.drop}
                                onDrop={handleDrop}
                                onDragOver={handleDragOver}
                            >
                                <span className={styles.dropText}>{locale === 'vi' ? 'Kéo thả tệp bằng chứng vào đây hoặc bấm' : 'Drag & drop evidence files here or'}</span>
                                <label className={styles.uploadBtn}>
                                    {locale === 'vi' ? 'Chọn tệp từ máy tính' : 'Browse Files'}
                                    <input
                                        type="file"
                                        multiple
                                        accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xlsx,.csv,.txt,.log,.conf,.xml,.json"
                                        hidden
                                        onChange={(e) => {
                                             const files = e.target.files
                                             if (files?.length > 0 && onUploadFiles) onUploadFiles(control.id, files)
                                             e.target.value = ''
                                        }}
                                    />
                                </label>
                            </div>

                            {evidenceFiles.length > 0 ? (
                                <div className={styles.fileList}>
                                    {evidenceFiles.map((f, i) => (
                                        <div key={i} className={styles.fileRow}>
                                            <EvidenceThumb file={f} onExpand={onExpandFile} />
                                            <button
                                                type="button"
                                                className={styles.removeBtn}
                                                onClick={() => onDeleteFile?.(control.id, f.filename)}
                                                aria-label={t('assessment.deleteFile')}
                                                title={t('assessment.deleteFile')}
                                            >✕</button>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className={styles.empty}>{locale === 'vi' ? 'Chưa có tệp bằng chứng nào được tải lên cho biện pháp này.' : 'No evidence files uploaded for this control yet.'}</p>
                            )}

                            <div className={styles.block}>
                                <div className={styles.blockLabel}>{t('formIso.notesLabel')}</div>
                                <textarea
                                    className={styles.notes}
                                    value={state?.notes || ''}
                                    onChange={(e) => onChangeNotes?.(control.id, e.target.value)}
                                    placeholder={t('formIso.notesPlaceholder')}
                                    rows={3}
                                />
                            </div>
                        </div>
                    )}

                    {tab === 'ai' && (
                        <div className={styles.section}>
                            <div className={styles.aiActionCard}>
                                <div className={styles.aiActionHeader}>
                                    <span className={styles.aiModelBadge}>
                                        ⚡ {selectedModel}
                                    </span>
                                    <span className={styles.aiTitleTag}>
                                        {locale === 'vi' ? 'Trợ Lý Thẩm Định CyberAI' : 'CyberAI Assessment Assistant'}
                                    </span>
                                </div>
                                <p className={styles.aiSubText}>
                                    {locale === 'vi'
                                        ? 'Sử dụng mô hình AI an toàn nội bộ để thẩm định tệp bằng chứng thực tế, sinh kịch bản triển khai SOP hoặc giải đáp các thắc mắc chuyên sâu cho biện pháp này.'
                                        : 'Leverage offline AI model to verify uploaded evidence files, generate implementation SOP, or answer technical inquiries.'}
                                </p>

                                <div className={styles.aiButtonGrid}>
                                    <button
                                        type="button"
                                        className={`${styles.aiQuickBtn} ${aiMode === 'verify_evidence' ? styles.aiQuickBtnActive : ''}`}
                                        onClick={() => handleRunAiAssist('verify_evidence')}
                                        disabled={aiLoading}
                                    >
                                        <span>🔍</span>
                                        <div>
                                            <strong>{locale === 'vi' ? 'Thẩm Định Bằng Chứng' : 'Verify Evidence'}</strong>
                                            <small>{evidenceFiles.length} {locale === 'vi' ? 'tệp đính kèm' : 'files attached'}</small>
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        className={`${styles.aiQuickBtn} ${aiMode === 'generate_sop' ? styles.aiQuickBtnActive : ''}`}
                                        onClick={() => handleRunAiAssist('generate_sop')}
                                        disabled={aiLoading}
                                    >
                                        <span>💡</span>
                                        <div>
                                            <strong>{locale === 'vi' ? 'Sinh Quy Trình & Lệnh Mẫu' : 'Generate SOP & Scripts'}</strong>
                                            <small>{locale === 'vi' ? 'SOP chuẩn & PowerShell' : 'Policy SOP & Scripts'}</small>
                                        </div>
                                    </button>
                                </div>

                                <div className={styles.aiQueryBox}>
                                    <div className={styles.aiQueryInputRow}>
                                        <input
                                            type="text"
                                            className={styles.aiQueryInput}
                                            placeholder={locale === 'vi' ? 'Đặt câu hỏi cụ thể cho Model (VD: Làm sao vượt qua audit mục này?)...' : 'Ask specific question to AI model...'}
                                            value={customQuery}
                                            onChange={(e) => setCustomQuery(e.target.value)}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter' && customQuery.trim()) {
                                                    handleRunAiAssist('custom_query', customQuery)
                                                }
                                            }}
                                            disabled={aiLoading}
                                        />
                                        <button
                                            type="button"
                                            className={styles.aiQuerySendBtn}
                                            onClick={() => handleRunAiAssist('custom_query', customQuery)}
                                            disabled={aiLoading || !customQuery.trim()}
                                        >
                                            {aiLoading ? '...' : 'Gửi'}
                                        </button>
                                    </div>
                                </div>

                                {aiLoading && (
                                    <div className={styles.aiLoadingWrap}>
                                        <div className={styles.aiLoadingSpinner} />
                                        <span>{locale === 'vi' ? 'Mô hình AI đang phân tích dữ liệu chuyên sâu...' : 'AI model is analyzing...'}</span>
                                    </div>
                                )}

                                {aiResponse && !aiLoading && (
                                    <div className={styles.aiResultCard}>
                                        <div className={styles.aiResultHeader}>
                                            <div className={styles.aiResultHeaderLeft}>
                                                <span className={styles.aiResultDot} />
                                                <strong>{locale === 'vi' ? 'Kết Quả Phân Tích Chuyên Sâu' : 'AI Analysis Result'}</strong>
                                            </div>
                                            <button
                                                type="button"
                                                className={styles.aiCopyBtn}
                                                onClick={copyAiResponse}
                                                title={locale === 'vi' ? 'Sao chép kết quả' : 'Copy result'}
                                            >
                                                {copiedAi ? (locale === 'vi' ? '✓ Đã chép' : '✓ Copied') : (locale === 'vi' ? 'Sao chép' : 'Copy')}
                                            </button>
                                        </div>
                                        <div className={styles.aiMarkdownContent}>
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {aiResponse}
                                            </ReactMarkdown>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <footer className={styles.footer}>
                    <div className={styles.footerInner}>
                        <button
                            type="button"
                            className={`${styles.toggleBtn} ${implemented ? styles.toggleBtnRemove : ''}`}
                            onClick={() => {
                                // Step 5 gate: block check-on when no evidence; allow uncheck always
                                if (!implemented && evidenceFiles.length < 1) {
                                    setShowGateHint(true)
                                    if (gateTimerRef.current) clearTimeout(gateTimerRef.current)
                                    gateTimerRef.current = setTimeout(() => setShowGateHint(false), 4000)
                                    return
                                }
                                setShowGateHint(false)
                                onToggleImplemented?.(control.id)
                            }}
                        >
                            {implemented
                                ? t('assessment.unmarkImplemented')
                                : t('assessment.markImplemented')}
                        </button>
                        {showGateHint && (
                            <div className={styles.gateHint} role="status" aria-live="polite">
                                {t('formIso.evidenceRequiredHint')}
                            </div>
                        )}
                    </div>
                </footer>
            </aside>
        </>
    )
}
