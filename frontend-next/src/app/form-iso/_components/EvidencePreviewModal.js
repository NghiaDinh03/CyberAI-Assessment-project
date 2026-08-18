'use client'

import { useEffect, useRef, useState } from 'react'
import styles from './EvidencePreviewModal.module.css'
import { useTranslation } from '@/components/LanguageProvider'
import { getEvidenceDownloadUrl, getEvidencePreviewUrl } from '@/lib/api'

const IMAGE_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']
const TEXT_EXTS = ['md', 'txt', 'json', 'csv', 'log', 'conf', 'xml', 'yml', 'yaml']

function classify(file) {
    const name = file?.filename || ''
    const ext = (name.split('.').pop() || '').toLowerCase()
    const mime = (file?.mime || '').toLowerCase()
    if (mime.startsWith('image/') || IMAGE_EXTS.includes(ext)) return 'image'
    if (mime === 'application/pdf' || ext === 'pdf') return 'pdf'
    if (mime.startsWith('text/') || TEXT_EXTS.includes(ext)) return 'text'
    return 'other'
}

/**
 * Modal preview of a single evidence file (image / PDF / text / fallback).
 * Source URLs come from /api/iso27001/evidence/{control_id}/{filename}[/preview].
 */
export default function EvidencePreviewModal({ open, file, onClose, returnFocusRef }) {
    const { t } = useTranslation()
    const panelRef = useRef(null)
    const [textContent, setTextContent] = useState('')
    const [loading, setLoading] = useState(false)
    const [errored, setErrored] = useState(false)

    const kind = file ? classify(file) : 'other'
    const controlId = file?.control_id || file?.controlId
    const filename = file?.filename
    const downloadUrl = controlId && filename ? getEvidenceDownloadUrl(controlId, filename) : ''
    const previewUrl = controlId && filename ? getEvidencePreviewUrl(controlId, filename) : ''

    // Focus panel on open; restore focus on close
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

    // Esc closes
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

    // Fetch text content via preview endpoint when applicable
    useEffect(() => {
        let cancelled = false
        setTextContent('')
        setErrored(false)
        if (!open || kind !== 'text' || !previewUrl) return
        setLoading(true)
        fetch(previewUrl)
            .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
            .then(data => { if (!cancelled) setTextContent(data?.content || '') })
            .catch(() => { if (!cancelled) setErrored(true) })
            .finally(() => { if (!cancelled) setLoading(false) })
        return () => { cancelled = true }
    }, [open, kind, previewUrl])

    if (!open || !file) return null

    const titleId = 'evidence-preview-title'

    return (
        <>
            <div className={styles.backdrop} onClick={onClose} aria-hidden="true" />
            <div
                ref={panelRef}
                className={styles.panel}
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                tabIndex={-1}
            >
                <header className={styles.header}>
                    <div className={styles.titleWrap}>
                        <span className={styles.label}>{t('formIso.previewTitle')}</span>
                        <h3 id={titleId} className={styles.title} title={filename}>
                            {filename}
                        </h3>
                    </div>
                    <button
                        type="button"
                        className={styles.close}
                        onClick={onClose}
                        aria-label={t('formIso.previewClose')}
                    >✕</button>
                </header>

                <div className={styles.body}>
                    {kind === 'image' && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={downloadUrl} alt={filename} className={styles.image} />
                    )}
                    {kind === 'pdf' && (
                        <iframe
                            src={downloadUrl}
                            title={filename}
                            className={styles.iframe}
                        />
                    )}
                    {kind === 'text' && (
                        loading ? (
                            <p className={styles.note}>…</p>
                        ) : errored ? (
                            <div className={styles.fallback}>
                                <p>{t('formIso.previewUnavailable')}</p>
                                <a href={downloadUrl} target="_blank" rel="noopener noreferrer" className={styles.dlLink}>
                                    {t('formIso.previewDownload')}
                                </a>
                            </div>
                        ) : (
                            <pre className={styles.text}>{textContent}</pre>
                        )
                    )}
                    {kind === 'other' && (
                        <div className={styles.fallback}>
                            <p>{t('formIso.previewUnavailable')}</p>
                            <a href={downloadUrl} target="_blank" rel="noopener noreferrer" className={styles.dlLink}>
                                {t('formIso.previewDownload')}
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </>
    )
}
