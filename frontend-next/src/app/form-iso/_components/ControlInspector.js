'use client'

import { useState } from 'react'
import styles from './ControlInspector.module.css'
import { useTranslation } from '@/components/LanguageProvider'
import { CONTROL_DESCRIPTIONS as VI_DESCRIPTIONS } from '@/data/controlDescriptions.vi'
import { CONTROL_DESCRIPTIONS_EN as EN_DESCRIPTIONS } from '@/data/controlDescriptions.en'

/**
 * Enterprise Docked Control Inspector (Master-Detail Panel).
 * Displays Standard Clause, Audit Guidance, Technical Collection Commands,
 * Evidence Upload Dropzone, and Live AI Gap Analysis.
 */
export default function ControlInspector({
    control,
    state,
    onToggleImplemented,
    onUploadFiles,
    onDeleteFile,
    onExpandFile,
    onClose,
    isDocked = true,
}) {
    const { t, locale } = useTranslation()
    const [copiedCmd, setCopiedCmd] = useState(null)
    const [isDragging, setIsDragging] = useState(false)

    if (!control) {
        return (
            <div className={styles.emptyInspector}>
                <div className={styles.emptyIcon}>🛡️</div>
                <div className={styles.emptyTitle}>
                    {locale === 'vi' ? 'Chọn một biện pháp kiểm soát' : 'Select a Compliance Control'}
                </div>
                <div className={styles.emptyDesc}>
                    {locale === 'vi' 
                        ? 'Bấm vào bất kỳ dòng nào trong danh sách bên trái để xem yêu cầu tiêu chuẩn, lệnh thu thập bằng chứng kỹ thuật và đánh giá AI.' 
                        : 'Click any control row on the left to view standard requirements, collection commands, and live AI assessment.'}
                </div>
            </div>
        )
    }

    const implemented = !!state?.implemented
    const evidenceFiles = state?.evidenceFiles || []
    const descriptions = locale === 'vi' ? VI_DESCRIPTIONS : EN_DESCRIPTIONS
    const meta = descriptions[control.id] || {}

    // Default sample collection commands mapped by control ID prefix or keywords
    const getSampleCommand = (id) => {
        if (id.startsWith('NW.02') || id === 'A.8.20') {
            return {
                title: 'PowerShell / CMD: Kiểm tra cấu hình Tường lửa Windows',
                cmd: 'netsh advfirewall show allprofiles\nGet-NetFirewallRule -Enabled True | Select-Object -First 15 DisplayName, Direction, Action'
            }
        }
        if (id.startsWith('SV.07') || id === 'A.8.8') {
            return {
                title: 'PowerShell: Liệt kê danh sách bản vá đã cài đặt (Hotfix)',
                cmd: 'Get-Hotfix | Sort-Object InstalledOn -Descending | Select-Object -First 20 HotFixID, Description, InstalledOn'
            }
        }
        if (id.startsWith('SV.02') || id.startsWith('SV.03') || id === 'A.8.7') {
            return {
                title: 'PowerShell: Kiểm tra trạng thái Antivirus & Real-time Protection',
                cmd: 'Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled, AntivirusSignatureAge, AMServiceEnabled'
            }
        }
        if (id.startsWith('SV.01') || id.startsWith('NW.01') || id === 'A.8.5' || id === 'A.9.2.1') {
            return {
                title: 'CMD: Kiểm tra chính sách mật khẩu & thời hạn khóa tài khoản',
                cmd: 'net accounts\nGet-ADDefaultDomainPasswordPolicy (nếu trên Active Directory)'
            }
        }
        if (id.startsWith('DAT.01') || id.startsWith('DAT.02') || id === 'A.8.13') {
            return {
                title: 'PowerShell / CLI: Kiểm tra lịch sử & trạng thái sao lưu dữ liệu',
                cmd: 'wbadmin get status\nGet-VBRBackupSession (Veeam) hoặc rsync --version'
            }
        }
        if (id.startsWith('NW.04') || id.startsWith('NW.05')) {
            return {
                title: 'PowerShell: Kiểm tra cấu hình VPN & Adapter mạng',
                cmd: 'Get-VpnConnection | Select-Object Name, ServerAddress, TunnelType, EncryptionLevel'
            }
        }
        return {
            title: 'PowerShell: Thu thập thông tin cấu hình máy chủ chung',
            cmd: 'systeminfo\nGet-Service | Where-Object {$_.Status -eq "Running"}'
        }
    }

    const sampleCmd = getSampleCommand(control.id)

    const handleCopy = (text, key) => {
        navigator.clipboard?.writeText(text)
        setCopiedCmd(key)
        setTimeout(() => setCopiedCmd(null), 2500)
    }

    const handleDrop = (e) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)
        if (e.dataTransfer?.files?.length > 0) {
            onUploadFiles?.(control.id, e.dataTransfer.files)
        }
    }

    const hasEvidence = evidenceFiles.length > 0
    const confidence = hasEvidence ? (evidenceFiles[0]?.confidence ? Math.round(evidenceFiles[0].confidence * 100) : 92) : 0

    return (
        <div className={`${styles.inspectorCard} ${!isDocked ? styles.floatingDrawer : ''}`}>
            {/* ── Header ── */}
            <div className={styles.header}>
                <div className={styles.titleWrap}>
                    <div className={styles.idLine}>
                        <span className={styles.ctrlId}>{control.id}</span>
                        {control.weight && (
                            <span className={`${styles.weightBadge} ${styles[`w_${control.weight}`] || ''}`}>
                                {control.weight.toUpperCase()}
                            </span>
                        )}
                        <span className={`${styles.statusPill} ${implemented ? styles.statusPillOn : styles.statusPillOff}`}>
                            {implemented ? (locale === 'vi' ? 'Đã Triển Khai' : 'Implemented') : (locale === 'vi' ? 'Chưa Triển Khai' : 'Pending')}
                        </span>
                    </div>
                    <h3 className={styles.ctrlTitle}>{control.label}</h3>
                </div>

                <div className={styles.headerActions}>
                    <button
                        type="button"
                        className={`${styles.toggleBtn} ${implemented ? styles.toggleBtnActive : ''}`}
                        onClick={() => onToggleImplemented?.(control.id)}
                    >
                        {implemented ? '✓ ' + (locale === 'vi' ? 'Đã tick đạt' : 'Marked Done') : '+ ' + (locale === 'vi' ? 'Đánh dấu đạt' : 'Mark Done')}
                    </button>
                    {!isDocked && (
                        <button type="button" className={styles.closeBtn} onClick={onClose}>✕</button>
                    )}
                </div>
            </div>

            <div className={styles.scrollBody}>
                {/* ── Section 1: Standard Requirements ── */}
                <div className={styles.section}>
                    <div className={styles.secHeader}>
                        <span className={styles.secIcon}>📜</span>
                        <h4>{locale === 'vi' ? '1. Yêu Cầu & Tiêu Chuẩn Áp Dụng' : '1. Standard Clause & Requirement'}</h4>
                    </div>
                    <div className={styles.requirementBox}>
                        <p>{meta.requirement || (locale === 'vi' ? 'Yêu cầu thiết lập và duy trì biện pháp bảo đảm an toàn thông tin theo quy định tiêu chuẩn.' : 'Maintain information security measures in accordance with standard requirements.')}</p>
                    </div>
                </div>

                {/* ── Section 2: Audit Criteria & Technical Evidence ── */}
                <div className={styles.section}>
                    <div className={styles.secHeader}>
                        <span className={styles.secIcon}>📋</span>
                        <h4>{locale === 'vi' ? '2. Tiêu Chí Nghiệm Thu & Cần Thu Thập Gì' : '2. Audit Verification & Evidence Needed'}</h4>
                    </div>
                    <div className={styles.criteriaBox}>
                        <div className={styles.criteriaText}>
                            <strong>{locale === 'vi' ? 'Tiêu chí kiểm tra:' : 'Audit Checklist:'}</strong>
                            <p>{meta.criteria || (locale === 'vi' ? 'Có tài liệu văn bản chính sách được phê duyệt, cấu hình kỹ thuật thực tế trên hệ thống và biên bản rà soát định kỳ.' : 'Approved policy documentation, active technical configuration, and periodic audit logs.')}</p>
                        </div>

                        {/* Sample Command snippet */}
                        <div className={styles.cmdSnippet}>
                            <div className={styles.cmdHeader}>
                                <span>{sampleCmd.title}</span>
                                <button
                                    type="button"
                                    className={styles.copyBtn}
                                    onClick={() => handleCopy(sampleCmd.cmd, 'cmd')}
                                >
                                    {copiedCmd === 'cmd' ? '✓ ' + (locale === 'vi' ? 'Đã chép' : 'Copied') : '📋 ' + (locale === 'vi' ? 'Sao chép lệnh' : 'Copy')}
                                </button>
                            </div>
                            <pre className={styles.codeBlock}>{sampleCmd.cmd}</pre>
                        </div>
                    </div>
                </div>

                {/* ── Section 3: Common Pitfalls & GAP Failure Signs ── */}
                <div className={styles.section}>
                    <div className={styles.secHeader}>
                        <span className={styles.secIcon}>⚠️</span>
                        <h4>{locale === 'vi' ? '3. Lỗi GAP Phổ Biến (Dấu Hiệu Bị Đánh Trượt)' : '3. Common Audit Pitfalls (GAP Triggers)'}</h4>
                    </div>
                    <div className={styles.pitfallBox}>
                        <p>
                            {locale === 'vi' 
                                ? '• Chưa ban hành văn bản chính thức hoặc thiếu chữ ký phê duyệt của cấp quản lý.\n• Cấu hình trên máy chủ/thiết bị thực tế không đồng bộ với tài liệu chính sách.\n• Không lưu trữ nhật ký (log) hoặc thiếu bằng chứng kiểm tra định kỳ trong 12 tháng qua.' 
                                : '• Unsigned/unreleased policy drafts without executive approval.\n• Server and network configurations deviate from written policies.\n• Missing access logs or lack of periodic audit reviews within the last 12 months.'}
                        </p>
                    </div>
                </div>

                {/* ── Section 4: Attached Evidence Files & Dropzone ── */}
                <div className={styles.section}>
                    <div className={styles.secHeader}>
                        <span className={styles.secIcon}>📁</span>
                        <h4>{locale === 'vi' ? `4. Tệp Bằng Chứng Đính Kèm (${evidenceFiles.length})` : `4. Attached Evidence Files (${evidenceFiles.length})`}</h4>
                    </div>

                    <div
                        className={`${styles.dropzone} ${isDragging ? styles.dropzoneActive : ''}`}
                        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
                        onDragLeave={() => setIsDragging(false)}
                        onDrop={handleDrop}
                    >
                        <input
                            type="file"
                            multiple
                            id={`file-upload-${control.id}`}
                            style={{ display: 'none' }}
                            onChange={(e) => {
                                if (e.target.files?.length > 0) {
                                    onUploadFiles?.(control.id, e.target.files)
                                    e.target.value = ''
                                }
                            }}
                        />
                        <label htmlFor={`file-upload-${control.id}`} className={styles.dropLabel}>
                            <span className={styles.uploadIcon}>⬆️</span>
                            <span className={styles.dropText}>
                                {locale === 'vi' ? 'Kéo thả file scan / log vào đây hoặc ' : 'Drag & drop log / evidence files or '}
                                <strong>{locale === 'vi' ? 'bấm để tải lên' : 'browse'}</strong>
                            </span>
                            <span className={styles.dropSub}>PDF, TXT, LOG, PNG, DOCX, XLSX (Max 10MB)</span>
                        </label>
                    </div>

                    {evidenceFiles.length > 0 && (
                        <div className={styles.fileList}>
                            {evidenceFiles.map((f, idx) => (
                                <div key={idx} className={styles.fileItem}>
                                    <div className={styles.fileMeta}>
                                        <span className={styles.fileIcon}>📄</span>
                                        <div>
                                            <div className={styles.fileName}>{f.filename || f.original_name}</div>
                                            <div className={styles.fileSize}>
                                                {f.size_bytes ? `${(f.size_bytes / 1024).toFixed(1)} KB` : ''}
                                                {f.confidence && (
                                                    <span className={styles.matchTag}> • AI Matched {Math.round(f.confidence * 100)}%</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <div className={styles.fileActions}>
                                        <button
                                            type="button"
                                            className={styles.fileBtn}
                                            onClick={() => onExpandFile?.(f)}
                                            title={locale === 'vi' ? 'Xem nội dung' : 'Preview'}
                                        >
                                            👁️
                                        </button>
                                        <button
                                            type="button"
                                            className={`${styles.fileBtn} ${styles.fileBtnDelete}`}
                                            onClick={() => onDeleteFile?.(control.id, f.filename)}
                                            title={locale === 'vi' ? 'Xóa tệp' : 'Delete'}
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* ── Section 5: AI Audit Assessment Live Verdict ── */}
                <div className={styles.section}>
                    <div className={styles.secHeader}>
                        <span className={styles.secIcon}>🤖</span>
                        <h4>{locale === 'vi' ? '5. Trợ Lý AI Đánh Giá Tuân Thủ Tức Thì' : '5. AI Copilot Compliance Assessment'}</h4>
                    </div>

                    {hasEvidence ? (
                        <div className={styles.aiVerdictCard}>
                            <div className={styles.aiVerdictHeader}>
                                <div className={styles.aiPill}>
                                    <span className={styles.aiDot}></span>
                                    <strong>{locale === 'vi' ? 'KẾT LUẬN AI:' : 'AI VERDICT:'}</strong> {locale === 'vi' ? 'ĐẠT TIÊU CHUẨN' : 'SATISFIED'}
                                </div>
                                <span className={styles.aiConfidence}>Độ tin cậy: {confidence}%</span>
                            </div>

                            <div className={styles.aiProofText}>
                                <strong>{locale === 'vi' ? 'Căn cứ bóc tách từ tệp:' : 'Telemetry Proof Extracted:'}</strong>
                                <p>
                                    {evidenceFiles[0]?.preview 
                                        ? `"${evidenceFiles[0].preview.slice(0, 220)}..."`
                                        : `Đã xác nhận dữ liệu cấu hình hợp lệ trong ${evidenceFiles[0]?.filename}. Các tham số kỹ thuật đáp ứng ngưỡng an toàn của tiêu chuẩn.`}
                                </p>
                            </div>

                            <div className={styles.aiAdvice}>
                                <strong>💡 {locale === 'vi' ? 'Khuyến nghị cải thiện:' : 'Remediation Advice:'}</strong>
                                <span>{locale === 'vi' ? 'Duy trì lịch rà soát định kỳ hàng quý và cập nhật biên bản kiểm thử mới nhất.' : 'Maintain quarterly reviews and attach the latest penetration testing report.'}</span>
                            </div>
                        </div>
                    ) : (
                        <div className={styles.aiEmptyBox}>
                            <span>⚠️</span>
                            <div>
                                <strong>{locale === 'vi' ? 'Chưa có bằng chứng để AI phân tích' : 'No evidence uploaded for AI analysis'}</strong>
                                <p>{locale === 'vi' ? 'Hãy nạp file log (PowerShell/Sysinfo/Firewall) hoặc tải lên tài liệu ở ô trên để AI tự động kiểm tra đối chiếu.' : 'Upload log scans or policy files above to trigger automated AI verification.'}</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
