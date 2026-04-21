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
    const { t } = useTranslation()
    const [tab, setTab] = useState('criteria')
    const [showGateHint, setShowGateHint] = useState(false)
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
                                    ? t('assessment.controlImplemented')
                                    : t('assessment.controlNotImplemented')}
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
                    {['criteria', 'evidence', 'ai'].map(id => (
                        <button
                            key={id}
                            type="button"
                            role="tab"
                            aria-selected={tab === id}
                            className={`${styles.tab} ${tab === id ? styles.tabActive : ''}`}
                            onClick={() => setTab(id)}
                        >
                            {t(`formIso.tab.${id}`)}
                        </button>
                    ))}
                </nav>

                <div className={styles.body}>
                    {tab === 'criteria' && (
                        <div className={styles.section}>
                            {desc ? (
                                <>
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{t('assessment.standardRequirement')}</div>
                                        <p className={styles.text}>{desc.requirement}</p>
                                    </div>
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{t('assessment.assessmentCriteria')}</div>
                                        <p className={styles.text}>{desc.criteria}</p>
                                    </div>
                                    <div className={styles.block}>
                                        <div className={styles.blockLabel}>{t('assessment.implementationGuide')}</div>
                                        <p className={styles.hint}>
                                            {desc.hint ||
                                                (implemented
                                                    ? t('assessment.implementedHint')
                                                    : t('assessment.notImplementedHint'))}
                                        </p>
                                    </div>
                                    {desc.evidence?.length > 0 && (
                                        <div className={styles.block}>
                                            <div className={styles.blockLabel}>
                                                {t('assessment.requiredEvidence')}
                                                <span className={styles.required} aria-hidden="true"> *</span>
                                                <span className={styles.countPill}>{desc.evidence.length} {t('assessment.documentTypes')}</span>
                                            </div>
                                            <ul className={styles.evList}>
                                                {desc.evidence.map((ev, i) => (
                                                    <li key={i}>{ev}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
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
