'use client'

import { useEffect, useRef, useState } from 'react'
import styles from './DetailDrawer.module.css'
import EvidenceThumb from './EvidenceThumb'
import { useTranslation } from '@/components/LanguageProvider'

/**
 * Overlay drawer showing control details. Does NOT reflow the grid below.
 *
 * Props:
 *  - open: boolean
 *  - control: { id, label } | null
 *  - state: {
 *      implemented, description, evidenceFiles, notes,
 *      evidence_verdict?, missing_items?, confidence?, ai_notes?
 *    }
 *  - onClose()
 *  - onToggleImplemented(controlId)
 *  - onUploadFiles(controlId, FileList | File[])
 *  - onDeleteFile(controlId, filename)
 *  - onChangeNotes(controlId, text)
 *  - onExpandFile(file)   // Step 5: full modal preview
 *  - returnFocusRef?: ref to element that triggered the drawer (to restore focus)
 */
const COMMAND_MAP = {
    'NW.02': 'netsh advfirewall show allprofiles\nGet-NetFirewallRule -Enabled True | Select DisplayName, Direction, Action',
    'A.8.20': 'netsh advfirewall show allprofiles\nGet-NetFirewallRule -Enabled True | Select DisplayName, Direction, Action',
    'SV.07': 'Get-Hotfix | Sort-Object InstalledOn -Descending | Select-Object -First 10',
    'A.8.8': 'Get-Hotfix | Sort-Object InstalledOn -Descending | Select-Object -First 10',
    'SV.02': 'Get-MpComputerStatus | Select-Object AMServiceEnabled, AntispywareSignatureVersion, RealTimeProtectionEnabled',
    'A.8.7': 'Get-MpComputerStatus | Select-Object AMServiceEnabled, AntispywareSignatureVersion, RealTimeProtectionEnabled',
    'SV.01': 'net accounts\nGet-ADDefaultDomainPasswordPolicy',
    'A.8.5': 'net accounts\nGet-ADDefaultDomainPasswordPolicy',
    'DAT.01': 'wbadmin get status\nwbadmin get versions',
    'A.8.13': 'wbadmin get status\nwbadmin get versions',
    'AC.01': 'Get-LocalGroupMember -Group "Administrators"',
    'A.5.15': 'Get-LocalGroupMember -Group "Administrators"',
}

const PITFALL_MAP = {
    'NW.02': 'Mở port nhạy cảm (3389/RDP, 445/SMB, 22/SSH) trực tiếp ra Internet mà không qua VPN/Bastion Host.',
    'A.8.20': 'Mở port nhạy cảm (3389/RDP, 445/SMB, 22/SSH) trực tiếp ra Internet mà không qua VPN/Bastion Host.',
    'SV.07': 'Hơn 60 ngày chưa cập nhật bản vá bảo mật hàng tháng (Windows Cumulative Update / Linux yum update).',
    'A.8.8': 'Hơn 60 ngày chưa cập nhật bản vá bảo mật hàng tháng (Windows Cumulative Update / Linux yum update).',
    'SV.02': 'Tắt Real-Time Protection hoặc Antivirus Signature hết hạn quá 7 ngày.',
    'A.8.7': 'Tắt Real-Time Protection hoặc Antivirus Signature hết hạn quá 7 ngày.',
    'SV.01': 'Cho phép mật khẩu đơn giản dưới 8 ký tự, không khóa tài khoản khi nhập sai quá 5 lần.',
    'A.8.5': 'Cho phép mật khẩu đơn giản dưới 8 ký tự, không khóa tài khoản khi nhập sai quá 5 lần.',
    'DAT.01': 'Chưa kiểm thử khôi phục dữ liệu định kỳ (Restore Drill) hoặc lưu bản backup cùng trên cùng 1 ổ đĩa sản xuất.',
    'A.8.13': 'Chưa kiểm thử khôi phục dữ liệu định kỳ (Restore Drill) hoặc lưu bản backup cùng trên cùng 1 ổ đĩa sản xuất.',
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
}) {
    const { t, locale } = useTranslation()
    const [tab, setTab] = useState('criteria')
    const [showGateHint, setShowGateHint] = useState(false)
    const [copiedCmd, setCopiedCmd] = useState(false)
    const panelRef = useRef(null)
    const gateTimerRef = useRef(null)

    // Reset to criteria tab when control changes
    useEffect(() => {
        if (open) setTab('criteria')
    }, [open, control?.id])

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
    const verdict = state?.evidence_verdict
    const missingItems = state?.missing_items || []
    const confidence = state?.confidence
    const aiNotes = state?.ai_notes || ''

    const sampleCommand = COMMAND_MAP[control.id] || `auditpol /get /category:* \nGet-Service | Where-Object {$_.Status -eq "Running"}`
    const pitfall = PITFALL_MAP[control.id] || (locale === 'vi' 
        ? 'Chưa ban hành văn bản chính thức, thiếu chữ ký phê duyệt của cấp quản lý, hoặc cấu hình trên máy chủ không đồng bộ với chính sách.' 
        : 'Missing executive approval, unreleased policy drafts, or server configurations inconsistent with stated policy.')

    const copyCommand = () => {
        navigator.clipboard.writeText(sampleCommand)
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
                            {verdict && (
                                <span className={`${styles.chip} ${styles[`v_${verdict}`] || ''}`}>
                                    {t(`assessment.verdict.${verdict}`)}
                                </span>
                            )}
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
                        { id: 'criteria', label: locale === 'vi' ? 'Tiêu chí & Hướng dẫn' : 'Criteria & Guidance' },
                        { id: 'evidence', label: `${locale === 'vi' ? 'Bằng chứng' : 'Evidence'} (${evidenceFiles.length})` },
                        { id: 'ai', label: 'AI Copilot' }
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

                                    {/* 2. Assessment Criteria & Audit Verification */}
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{locale === 'vi' ? 'TIÊU CHÍ ĐÁNH GIÁ & NGHIỆM THU' : 'ASSESSMENT CRITERIA'}</div>
                                        <p className={styles.text}>{desc.criteria}</p>
                                    </div>

                                    {/* 3. Sample Technical Commands for Audit Ingestion */}
                                    <div className={styles.block}>
                                        <div className={styles.blockLabelRow}>
                                            <div className={styles.blockLabel}>{locale === 'vi' ? 'LỆNH KỸ THUẬT THU THẬP BẰNG CHỨNG' : 'TECHNICAL SCAN COMMANDS'}</div>
                                            <button type="button" className={styles.copyCmdBtn} onClick={copyCommand}>
                                                {copiedCmd ? '✓ Đã sao chép' : '📋 Sao chép lệnh'}
                                            </button>
                                        </div>
                                        <pre className={styles.codeBlock}><code>{sampleCommand}</code></pre>
                                    </div>

                                    {/* 4. Common Pitfalls / GAP Triggers */}
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{locale === 'vi' ? '⚠️ LỖI GAP THƯỜNG GẶP (DỄ BỊ ĐÁNH TRƯỢT)' : '⚠️ COMMON AUDIT PITFALLS'}</div>
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
                                                    ? 'Biện pháp này đã được đánh dấu triển khai. Hãy đảm bảo tài liệu bằng chứng được cập nhật và lưu trữ đúng nơi.'
                                                    : 'Cần rà soát chính sách, cấu hình máy chủ hoặc tài liệu liên quan trước khi đánh dấu đạt.')}
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
                            {/* STEP-5-PLACEHOLDER: mandatory-evidence gate will highlight this zone when empty */}
                            <div
                                className={styles.drop}
                                onDrop={handleDrop}
                                onDragOver={handleDragOver}
                            >
                                <span className={styles.dropIcon} aria-hidden="true">📂</span>
                                <span className={styles.dropText}>{t('assessment.dragDropFiles')}</span>
                                <label className={styles.uploadBtn}>
                                    📎 {t('assessment.selectFiles')}
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
                                <p className={styles.empty}>{t('formIso.evidenceEmpty')}</p>
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
                            {verdict || confidence != null || missingItems.length > 0 || aiNotes ? (
                                <>
                                    {verdict && (
                                        <div className={styles.block}>
                                            <div className={styles.blockLabel}>{t('formIso.aiVerdict')}</div>
                                            <span className={`${styles.chip} ${styles[`v_${verdict}`] || ''}`}>
                                                {t(`assessment.verdict.${verdict}`)}
                                            </span>
                                        </div>
                                    )}
                                    {confidence != null && (
                                        <div className={styles.block}>
                                            <div className={styles.blockLabel}>{t('formIso.aiConfidence')}</div>
                                            <p className={styles.text}>
                                                {typeof confidence === 'number'
                                                    ? `${Math.round(confidence * 100)}%`
                                                    : String(confidence)}
                                            </p>
                                        </div>
                                    )}
                                    {missingItems.length > 0 && (
                                        <div className={styles.block}>
                                            <div className={styles.blockLabel}>{t('formIso.aiMissing')}</div>
                                            <ul className={styles.evList}>
                                                {missingItems.map((m, i) => <li key={i}>{m}</li>)}
                                            </ul>
                                        </div>
                                    )}
                                    {aiNotes && (
                                        <div className={styles.block}>
                                            <div className={styles.blockLabel}>{t('formIso.aiNotes')}</div>
                                            <p className={styles.text}>{aiNotes}</p>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <p className={styles.empty}>{t('formIso.aiEmpty')}</p>
                            )}
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
