'use client'

import { useEffect, useRef, useState } from 'react'
import styles from './ControlRow.module.css'
import { useTranslation } from '@/components/LanguageProvider'
import { CONTROL_DESCRIPTIONS as VI_DESCRIPTIONS } from '@/data/controlDescriptions.vi'
import { CONTROL_DESCRIPTIONS_EN as EN_DESCRIPTIONS } from '@/data/controlDescriptions.en'

/**
 * Full-width enterprise control row.
 * Displays full unabbreviated control name, weight tag, requirement snippet, evidence action button, and audit guide.
 */
export default function ControlRow({
    control,
    state,
    onToggleImplemented,
    onOpenDrawer,
    evidenceCount = 0,
    verdict,
}) {
    const { t, locale } = useTranslation()
    const implemented = !!state?.implemented

    const [showHint, setShowHint] = useState(false)
    const [showAuditGuide, setShowAuditGuide] = useState(false)
    const hintTimerRef = useRef(null)
    const popoverRef = useRef(null)
    const infoBtnRef = useRef(null)

    useEffect(() => () => {
        if (hintTimerRef.current) clearTimeout(hintTimerRef.current)
    }, [])

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (
                popoverRef.current && 
                !popoverRef.current.contains(e.target) &&
                infoBtnRef.current && 
                !infoBtnRef.current.contains(e.target)
            ) {
                setShowAuditGuide(false)
            }
        }
        if (showAuditGuide) {
            document.addEventListener('mousedown', handleClickOutside)
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [showAuditGuide])

    const handleToggle = (e) => {
        e.stopPropagation()
        if (!implemented && evidenceCount < 1) {
            setShowHint(true)
            if (hintTimerRef.current) clearTimeout(hintTimerRef.current)
            hintTimerRef.current = setTimeout(() => setShowHint(false), 4000)
            return
        }
        setShowHint(false)
        onToggleImplemented?.(control.id)
    }

    const descriptions = locale === 'vi' ? VI_DESCRIPTIONS : EN_DESCRIPTIONS
    const meta = descriptions[control.id] || {}

    return (
        <div
            className={`${styles.row} ${implemented ? styles.rowOn : ''}`}
            data-control-id={control.id}
            onClick={() => onOpenDrawer?.(control.id)}
        >
            <div className={styles.toggleWrap} onClick={(e) => e.stopPropagation()}>
                <input
                    type="checkbox"
                    checked={implemented}
                    onChange={handleToggle}
                    aria-label={t('assessment.markImplemented')}
                    className={styles.checkbox}
                />
            </div>

            <div className={styles.body}>
                <div className={styles.headerLine}>
                    <span className={styles.id}>{control.id}</span>
                    {control.weight && (
                        <span className={`${styles.weight} ${styles[`w_${control.weight}`] || ''}`}>
                            {control.weight}
                        </span>
                    )}
                    <span className={styles.label}>{control.label}</span>
                </div>
                {meta.requirement && (
                    <div className={styles.requirementSnippet}>
                        {meta.requirement}
                    </div>
                )}
            </div>

            <div className={styles.actions} onClick={(e) => e.stopPropagation()}>
                <button
                    type="button"
                    className={`${styles.evidenceBtn} ${evidenceCount > 0 ? styles.evidenceBtnActive : ''}`}
                    onClick={() => onOpenDrawer?.(control.id)}
                    title={locale === 'vi' ? 'Quản lý tệp bằng chứng' : 'Manage evidence files'}
                >
                    📎 {evidenceCount > 0 ? `${evidenceCount} ${locale === 'vi' ? 'tệp' : 'files'}` : (locale === 'vi' ? 'Đính kèm' : 'Attach')}
                </button>

                <button
                    type="button"
                    ref={infoBtnRef}
                    className={`${styles.infoBtn} ${showAuditGuide ? styles.infoBtnActive : ''}`}
                    onClick={() => setShowAuditGuide(!showAuditGuide)}
                    title={locale === 'vi' ? 'Xem hướng dẫn kiểm toán & lỗi thường gặp' : 'View audit guidance & pitfalls'}
                >
                    ⓘ {locale === 'vi' ? 'Hướng dẫn' : 'Guide'}
                </button>

                {verdict && (
                    <span className={`${styles.verdict} ${styles[`v_${verdict}`] || ''}`}>
                        {t(`assessment.verdict.${verdict}`)}
                    </span>
                )}
            </div>

            {/* Smart Audit Guide Popover */}
            {showAuditGuide && (
                <div 
                    className={styles.guidePopover} 
                    ref={popoverRef}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className={styles.popoverArrow} />
                    <div className={styles.guideHeader}>
                        <div className={styles.guideTitle}>
                            <span>🛡️ {control.id}</span> — {control.label}
                        </div>
                        <button
                            type="button"
                            className={styles.closeBtn}
                            onClick={() => setShowAuditGuide(false)}
                        >
                            ✕
                        </button>
                    </div>

                    <div className={styles.guideSection}>
                        <div className={styles.secTitle}>🎯 {locale === 'vi' ? 'Mục tiêu Yêu cầu' : 'Core Requirement'}</div>
                        <div className={styles.secContent}>
                            {meta.requirement || (locale === 'vi' ? 'Chưa có mô tả chi tiết cho biện pháp kiểm soát này.' : 'No detailed description available.')}
                        </div>
                    </div>

                    <div className={styles.guideSection}>
                        <div className={styles.secTitle}>📋 {locale === 'vi' ? 'Bằng chứng cần cung cấp' : 'Recommended Evidence'}</div>
                        <div className={styles.secContent}>
                            {meta.criteria || (locale === 'vi' ? 'Tải lên tài liệu chính sách, ảnh chụp cấu hình hệ thống hoặc scan log kỹ thuật tương ứng.' : 'Upload policy documents, configuration screenshots, or server scan logs.')}
                        </div>
                    </div>

                    <div className={styles.guideSection}>
                        <div className={styles.secTitle}>⚠️ {locale === 'vi' ? 'Dấu hiệu lỗi GAP phổ biến' : 'Common Audit Pitfalls'}</div>
                        <div className={styles.secContentMuted}>
                            {locale === 'vi' 
                                ? 'Chưa ban hành văn bản chính thức, thiếu chữ ký phê duyệt của cấp quản lý, hoặc cấu hình trên máy chủ không đồng bộ với chính sách.' 
                                : 'Missing executive approval, unreleased policy drafts, or server configurations inconsistent with stated policy.'}
                        </div>
                    </div>
                </div>
            )}

            {showHint && (
                <div className={styles.gateHint} role="status" aria-live="polite" onClick={(e) => e.stopPropagation()}>
                    {t('formIso.evidenceRequiredHint')}
                </div>
            )}
        </div>
    )
}


