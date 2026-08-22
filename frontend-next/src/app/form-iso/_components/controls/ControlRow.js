'use client'

import { useEffect, useRef, useState } from 'react'
import styles from './ControlRow.module.css'
import { useTranslation } from '@/components/LanguageProvider'
import { useControlDescriptions } from '@/data'

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

    const descriptions = useControlDescriptions()
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
                    className={`${styles.guideBtn} ${evidenceCount > 0 ? styles.guideBtnHasFiles : ''}`}
                    onClick={() => onOpenDrawer?.(control.id)}
                    title={locale === 'vi' ? 'Xem hướng dẫn, tiêu chí và tệp bằng chứng' : 'View criteria and evidence'}
                >
                    {locale === 'vi' ? 'Hướng dẫn' : 'Guide'} {evidenceCount > 0 ? `(${evidenceCount})` : ''}
                </button>

                {verdict && (
                    <span className={`${styles.verdict} ${styles[`v_${verdict}`] || ''}`}>
                        {t(`assessment.verdict.${verdict}`)}
                    </span>
                )}
            </div>

            {showHint && (
                <div className={styles.gateHint} role="status" aria-live="polite" onClick={(e) => e.stopPropagation()}>
                    {t('formIso.evidenceRequiredHint')}
                </div>
            )}
        </div>
    )
}




