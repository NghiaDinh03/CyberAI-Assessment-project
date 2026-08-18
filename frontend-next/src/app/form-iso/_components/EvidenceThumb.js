'use client'

import styles from './EvidenceThumb.module.css'
import { useTranslation } from '@/components/LanguageProvider'

/**
 * Small thumbnail for one evidence file.
 *
 * Props:
 *  - file: { filename, size_bytes, mime?, previewUrl? }
 *  - onExpand(file)  // Step 5 will wire full modal preview
 */
export default function EvidenceThumb({ file, onExpand }) {
    const { t } = useTranslation()
    if (!file) return null

    const name = file.filename || ''
    const ext = (name.split('.').pop() || '').toLowerCase()
    const mime = file.mime || ''
    const isImage = mime.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)
    const isPdf = mime === 'application/pdf' || ext === 'pdf'

    const sizeLabel = file.size_bytes
        ? file.size_bytes > 1024 * 1024
            ? `${(file.size_bytes / 1024 / 1024).toFixed(1)}MB`
            : `${Math.round(file.size_bytes / 1024)}KB`
        : ''

    return (
        <div className={styles.thumb}>
            <div className={styles.preview}>
                {isImage && file.previewUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={file.previewUrl} alt={name} className={styles.img} />
                ) : isImage ? (
                    <span className={styles.icon} aria-hidden="true">🖼️</span>
                ) : isPdf ? (
                    <span className={styles.icon} aria-hidden="true">📕</span>
                ) : (
                    <span className={styles.icon} aria-hidden="true">📄</span>
                )}
            </div>
            <div className={styles.info}>
                <span className={styles.name} title={name}>{name}</span>
                {sizeLabel && <span className={styles.size}>{sizeLabel}</span>}
            </div>
            {/* STEP-5-PLACEHOLDER: expand-modal preview wired via onExpand */}
            <button
                type="button"
                className={styles.expand}
                onClick={() => onExpand?.(file)}
                title={t('formIso.thumbExpand')}
                aria-label={t('formIso.thumbExpand')}
            >
                ⤢
            </button>
        </div>
    )
}
