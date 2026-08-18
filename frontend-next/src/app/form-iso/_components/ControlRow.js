'use client'

import { useEffect, useRef, useState } from 'react'
import styles from './ControlRow.module.css'
import { useTranslation } from '@/components/LanguageProvider'

/**
 * Compact one-line row representing a single control inside the center list.
 *
 * Props:
 *  - control: { id, label, weight? }
 *  - state: { implemented: boolean }
 *  - onToggleImplemented(controlId)
 *  - onOpenDrawer(controlId)
 *  - evidenceCount: number
 *  - verdict?: 'satisfied' | 'partial' | 'missing' | 'not_applicable' | undefined
 */
export default function ControlRow({
    control,
    state,
    onToggleImplemented,
    onOpenDrawer,
    evidenceCount = 0,
    verdict,
}) {
    const { t } = useTranslation()
    const implemented = !!state?.implemented

    // Step 5: mandatory-evidence gate (uniform: ≥1 evidence file required)
    const [showHint, setShowHint] = useState(false)
    const hintTimerRef = useRef(null)

    useEffect(() => () => {
        if (hintTimerRef.current) clearTimeout(hintTimerRef.current)
    }, [])

    const handleToggle = () => {
        // Allow un-checking at any time; block check-on when no evidence
        if (!implemented && evidenceCount < 1) {
            setShowHint(true)
            if (hintTimerRef.current) clearTimeout(hintTimerRef.current)
            hintTimerRef.current = setTimeout(() => setShowHint(false), 4000)
            return
        }
        setShowHint(false)
        onToggleImplemented?.(control.id)
    }

    const verdictKey = verdict || 'neutral'
    const verdictLabel = t(`assessment.verdict.${verdictKey}`)

    return (
        <div
            className={`${styles.row} ${implemented ? styles.rowOn : ''}`}
            data-control-id={control.id}
        >
            <label className={styles.toggle}>
                <input
                    type="checkbox"
                    checked={implemented}
                    onChange={handleToggle}
                    aria-label={t('assessment.markImplemented')}
                />
            </label>

            <div className={styles.body}>
                <div className={styles.idRow}>
                    <span className={styles.id}>{control.id}</span>
                    {control.weight && (
                        <span className={`${styles.weight} ${styles[`w_${control.weight}`] || ''}`}>
                            {control.weight}
                        </span>
                    )}
                </div>
                <div className={styles.label}>{control.label}</div>
            </div>

            <div className={styles.meta}>
                <span
                    className={styles.evidence}
                    title={`${evidenceCount} ${t('assessment.filesUploaded')}`}
                >
                    📎 {evidenceCount}
                </span>
                <span
                    className={`${styles.verdict} ${styles[`v_${verdictKey}`] || ''}`}
                    title={verdictLabel}
                >
                    {verdictLabel}
                </span>
                <button
                    type="button"
                    className={styles.expand}
                    onClick={() => onOpenDrawer?.(control.id)}
                    aria-label={t('formIso.expandControl')}
                    title={t('formIso.expandControl')}
                >
                    ›
                </button>
            </div>
            {showHint && (
                <div className={styles.gateHint} role="status" aria-live="polite">
                    {t('formIso.evidenceRequiredHint')}
                </div>
            )}
        </div>
    )
}
