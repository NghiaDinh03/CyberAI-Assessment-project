'use client'

import { useState, useCallback } from 'react'
import { useTranslation } from '@/components/LanguageProvider'
import { SAMPLE_EVIDENCE, EVIDENCE_CATEGORIES, getSampleEvidenceByCategory } from '@/data/sampleEvidence'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import styles from './EvidenceLibrary.module.css'
import { Eye, Download, FileText, Image, File, X } from 'lucide-react'

/**
 * Evidence Library — displays sample evidence documents grouped by
 * ISO 27001 Annex A category. Each card has a preview icon that opens
 * a modal showing the document content inline.
 */
export default function EvidenceLibrary() {
    const { t } = useTranslation()
    const [activeCategory, setActiveCategory] = useState('all')
    const [previewFile, setPreviewFile] = useState(null)
    const [previewContent, setPreviewContent] = useState('')
    const [previewLoading, setPreviewLoading] = useState(false)

    const filteredEvidence = activeCategory === 'all'
        ? SAMPLE_EVIDENCE.filter(e => e.category !== 'generic')
        : getSampleEvidenceByCategory(activeCategory)

    const openPreview = useCallback(async (file) => {
        setPreviewFile(file)
        setPreviewContent('')
        setPreviewLoading(true)

        // For markdown files, fetch content and render inline
        if (file.mime === 'text/markdown' || file.filename.endsWith('.md')) {
            try {
                const res = await fetch(file.path)
                if (res.ok) {
                    const text = await res.text()
                    setPreviewContent(text)
                }
            } catch {
                setPreviewContent('*Preview unavailable*')
            }
        }
        setPreviewLoading(false)
    }, [])

    const closePreview = useCallback(() => {
        setPreviewFile(null)
        setPreviewContent('')
    }, [])

    const getFileIcon = (file) => {
        if (file.kind === 'image') return <Image size={16} />
        if (file.mime === 'application/pdf') return <FileText size={16} />
        return <File size={16} />
    }

    return (
        <section className={styles.library}>
            <div className={styles.header}>
                <h2 className={styles.title}>
                    📋 {t('evidenceLibrary.title')}
                </h2>
                <p className={styles.subtitle}>
                    {t('evidenceLibrary.subtitle')}
                </p>
            </div>

            {/* Category filter tabs */}
            <div className={styles.tabs}>
                <button
                    className={`${styles.tab} ${activeCategory === 'all' ? styles.tabActive : ''}`}
                    onClick={() => setActiveCategory('all')}
                >
                    {t('evidenceLibrary.allCategories')} ({SAMPLE_EVIDENCE.filter(e => e.category !== 'generic').length})
                </button>
                {EVIDENCE_CATEGORIES.map(cat => {
                    const count = getSampleEvidenceByCategory(cat.id).length
                    return (
                        <button
                            key={cat.id}
                            className={`${styles.tab} ${activeCategory === cat.id ? styles.tabActive : ''}`}
                            onClick={() => setActiveCategory(cat.id)}
                        >
                            {cat.icon} {cat.id} ({count})
                        </button>
                    )
                })}
            </div>

            {/* Evidence cards grid */}
            <div className={styles.grid}>
                {filteredEvidence.map(file => (
                    <div key={file.id} className={styles.card}>
                        <div className={styles.cardIcon}>
                            {getFileIcon(file)}
                        </div>
                        <div className={styles.cardBody}>
                            <h3 className={styles.cardTitle}>
                                {t(file.labelKey) || file.fallbackLabel}
                            </h3>
                            <p className={styles.cardDesc}>
                                {t(file.descriptionKey) || file.fallbackDescription}
                            </p>
                            {file.controls.length > 0 && (
                                <div className={styles.controlTags}>
                                    {file.controls.map(c => (
                                        <span key={c} className={styles.controlTag}>{c}</span>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className={styles.cardActions}>
                            <button
                                type="button"
                                className={styles.previewBtn}
                                onClick={() => openPreview(file)}
                                title={t('evidenceLibrary.preview')}
                                aria-label={`${t('evidenceLibrary.preview')} ${file.fallbackLabel}`}
                            >
                                <Eye size={15} />
                            </button>
                            <a
                                href={file.path}
                                download={file.filename}
                                className={styles.downloadBtn}
                                title={t('evidenceLibrary.download')}
                                aria-label={`${t('evidenceLibrary.download')} ${file.filename}`}
                            >
                                <Download size={15} />
                            </a>
                        </div>
                    </div>
                ))}
            </div>

            {filteredEvidence.length === 0 && (
                <p className={styles.empty}>{t('evidenceLibrary.noEvidence')}</p>
            )}

            {/* Mandatory evidence notice */}
            <div className={styles.notice}>
                <strong>⚠️ {t('evidenceLibrary.mandatoryTitle')}</strong>
                <p>{t('evidenceLibrary.mandatoryDesc')}</p>
            </div>

            {/* Preview modal */}
            {previewFile && (
                <>
                    <div className={styles.backdrop} onClick={closePreview} aria-hidden="true" />
                    <div
                        className={styles.modal}
                        role="dialog"
                        aria-modal="true"
                        aria-label={previewFile.fallbackLabel}
                    >
                        <header className={styles.modalHeader}>
                            <div className={styles.modalTitleWrap}>
                                <span className={styles.modalLabel}>{t('evidenceLibrary.preview')}</span>
                                <h3 className={styles.modalTitle}>{previewFile.fallbackLabel}</h3>
                            </div>
                            <div className={styles.modalActions}>
                                <a
                                    href={previewFile.path}
                                    download={previewFile.filename}
                                    className={styles.modalDownload}
                                    title={t('evidenceLibrary.download')}
                                >
                                    <Download size={16} />
                                </a>
                                <button
                                    type="button"
                                    className={styles.modalClose}
                                    onClick={closePreview}
                                    aria-label="Close"
                                >
                                    <X size={18} />
                                </button>
                            </div>
                        </header>
                        <div className={styles.modalBody}>
                            {previewLoading ? (
                                <p className={styles.loading}>Loading…</p>
                            ) : previewContent ? (
                                <div className={styles.markdownWrap}>
                                    <MarkdownRenderer content={previewContent} />
                                </div>
                            ) : previewFile.kind === 'image' ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img src={previewFile.path} alt={previewFile.fallbackLabel} className={styles.previewImage} />
                            ) : previewFile.mime === 'application/pdf' ? (
                                <iframe src={previewFile.path} title={previewFile.fallbackLabel} className={styles.previewIframe} />
                            ) : (
                                <div className={styles.fallback}>
                                    <p>{t('evidenceLibrary.previewUnavailable')}</p>
                                    <a href={previewFile.path} download={previewFile.filename}>
                                        {t('evidenceLibrary.download')}
                                    </a>
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </section>
    )
}
