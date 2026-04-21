'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslation } from '@/components/LanguageProvider'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import styles from './page.module.css'
import { useAssessmentTemplates } from '../../data'
import { ASSESSMENT_STANDARDS } from '../../data/standards'
import { SAMPLE_EVIDENCE } from '../../data/sampleEvidence'
import { Filter, Zap, ExternalLink, Info, Eye, Download, FileText, X, Upload } from 'lucide-react'
import EvidenceLibrary from '@/components/EvidenceLibrary'
import {
    uploadTemplateEvidence,
    getTemplateEvidence,
    getTemplateEvidenceRawUrl,
    getTemplateEvidenceTextUrl,
} from '@/lib/api'

/**
 * Compute matching sample evidence for a template based on its implemented_controls.
 * Returns unique evidence entries that map to at least one of the template's controls.
 */
function getEvidenceForTemplate(template) {
    const controls = template.data?.compliance?.implemented_controls || []
    if (controls.length === 0) return []

    const matched = new Map()
    for (const ev of SAMPLE_EVIDENCE) {
        if (ev.category === 'generic') continue
        for (const ctrl of ev.controls) {
            if (controls.includes(ctrl) && !matched.has(ev.id)) {
                matched.set(ev.id, ev)
                break
            }
        }
    }
    return Array.from(matched.values())
}

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export default function TemplatesMonitorPage() {
    const { t } = useTranslation()
    const router = useRouter()
    const [filter, setFilter] = useState('all')
    const ASSESSMENT_TEMPLATES = useAssessmentTemplates()

    /* ── Uploaded evidence state ── */
    const [uploadedMap, setUploadedMap] = useState({})
    const [uploadingMap, setUploadingMap] = useState({})
    const [uploadError, setUploadError] = useState({})
    const fileInputRefs = useRef({})

    useEffect(() => {
        let cancelled = false
        async function fetchAll() {
            for (const tpl of ASSESSMENT_TEMPLATES) {
                try {
                    const data = await getTemplateEvidence(tpl.id)
                    if (!cancelled) {
                        setUploadedMap(prev => ({ ...prev, [tpl.id]: data.evidence || [] }))
                    }
                } catch { /* backend may be offline — ignore */ }
            }
        }
        if (ASSESSMENT_TEMPLATES.length > 0) fetchAll()
        return () => { cancelled = true }
    }, [ASSESSMENT_TEMPLATES])

    const handleUpload = useCallback(async (templateId, file) => {
        setUploadingMap(prev => ({ ...prev, [templateId]: true }))
        setUploadError(prev => ({ ...prev, [templateId]: null }))
        try {
            await uploadTemplateEvidence(templateId, file)
            const data = await getTemplateEvidence(templateId)
            setUploadedMap(prev => ({ ...prev, [templateId]: data.evidence || [] }))
        } catch {
            setUploadError(prev => ({ ...prev, [templateId]: true }))
        } finally {
            setUploadingMap(prev => ({ ...prev, [templateId]: false }))
        }
    }, [])

    const handleFileSelect = useCallback((templateId, e) => {
        const file = e.target.files?.[0]
        if (file) handleUpload(templateId, file)
        e.target.value = ''
    }, [handleUpload])

    const handleDrop = useCallback((templateId, e) => {
        e.preventDefault()
        const file = e.dataTransfer?.files?.[0]
        if (file) handleUpload(templateId, file)
    }, [handleUpload])

    /* ── Evidence preview modal state ── */
    const [previewFile, setPreviewFile] = useState(null)
    const [previewContent, setPreviewContent] = useState('')
    const [previewLoading, setPreviewLoading] = useState(false)

    const openPreview = useCallback(async (file) => {
        setPreviewFile(file)
        setPreviewContent('')
        setPreviewLoading(true)

        if (file._uploaded) {
            const mime = file.mime_type || ''
            if (mime.startsWith('text/') || file.filename?.endsWith('.md') || file.filename?.endsWith('.txt')) {
                try {
                    const res = await fetch(getTemplateEvidenceTextUrl(file._templateId, file.doc_id))
                    if (res.ok) setPreviewContent(await res.text())
                } catch { setPreviewContent('*Preview unavailable*') }
            }
        } else {
            if (file.mime === 'text/markdown' || file.filename?.endsWith('.md')) {
                try {
                    const res = await fetch(file.path)
                    if (res.ok) setPreviewContent(await res.text())
                } catch { setPreviewContent('*Preview unavailable*') }
            }
        }
        setPreviewLoading(false)
    }, [])

    const closePreview = useCallback(() => {
        setPreviewFile(null)
        setPreviewContent('')
    }, [])

    const filteredTemplates = useMemo(() => {
        if (filter === 'all') return ASSESSMENT_TEMPLATES
        return ASSESSMENT_TEMPLATES.filter(t => t.standard === filter)
    }, [filter, ASSESSMENT_TEMPLATES])

    const getControlCount = (template) => {
        const std = ASSESSMENT_STANDARDS.find(s => s.id === template.standard)
        const total = std ? std.controls.reduce((acc, cat) => acc + cat.controls.length, 0) : 0
        const implemented = template.data.compliance?.implemented_controls?.length || 0
        return { implemented, total }
    }

    const selectTemplate = (tpl) => {
        localStorage.setItem('reuse_iso_form', JSON.stringify(tpl.data))
        router.push('/form-iso')
    }

    return (
        <div className="page-container">
            <div className={styles.header}>
                <div className={styles.headerMeta}>
                    <Link href="/form-iso" className={styles.backBtn}>{t('templates.backToAssessment')}</Link>
                </div>
                <h1 className={styles.title}>{t('templates.pageTitle')}</h1>
                <p className={styles.subtitle}>
                    {t('templates.pageSubtitle')}
                </p>
            </div>

            <div className={styles.filterBar}>
                <Filter size={14} style={{ color: 'var(--text-dim)', alignSelf: 'center' }} />
                <button
                    className={`${styles.filterBtn} ${filter === 'all' ? styles.filterActive : ''}`}
                    onClick={() => setFilter('all')}
                >
                    All ({ASSESSMENT_TEMPLATES.length})
                </button>
                {ASSESSMENT_STANDARDS.map(std => {
                    const count = ASSESSMENT_TEMPLATES.filter(t => t.standard === std.id).length
                    if (count === 0) return null
                    return (
                        <button
                            key={std.id}
                            className={`${styles.filterBtn} ${filter === std.id ? styles.filterActive : ''}`}
                            onClick={() => setFilter(std.id)}
                        >
                            {std.id === 'iso27001' ? 'ISO 27001' : 'TCVN 11930'} ({count})
                        </button>
                    )
                })}
            </div>

            <div className={styles.templateGrid}>
                {filteredTemplates.map(tpl => {
                    const { implemented, total } = getControlCount(tpl)
                    const percent = total > 0 ? Math.round((implemented / total) * 100) : 0
                    const tplEvidence = getEvidenceForTemplate(tpl)

                    return (
                        <div key={tpl.id} className={styles.templateCard}>
                            <div className={styles.cardHeader}>
                                <div className={styles.cardTitleRow}>
                                    <h3 className={styles.cardTitle}>{tpl.name}</h3>
                                    <span className={`${styles.stdBadge} ${tpl.standard === 'iso27001' ? styles.stdIso : styles.stdTcvn}`}>
                                        {tpl.standard === 'iso27001' ? 'ISO 27001' : 'TCVN 11930'}
                                    </span>
                                </div>
                                <span className={styles.industryTag}>{tpl.data.organization.industry}</span>
                            </div>

                            <div className={styles.cardBody}>
                                <p className={styles.cardDesc}>{tpl.description}</p>

                                {tpl.source && (
                                    <div className={styles.sourceRow}>
                                        <Info size={11} className={styles.sourceIcon} />
                                        <span className={styles.sourceText}>
                                            {tpl.sourceUrl ? (
                                                <a
                                                    href={tpl.sourceUrl}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className={styles.sourceLink}
                                                >
                                                    {tpl.source}
                                                    <ExternalLink size={10} style={{ marginLeft: '4px', verticalAlign: 'middle' }} />
                                                </a>
                                            ) : tpl.source}
                                        </span>
                                    </div>
                                )}

                                <div className={styles.statsRow}>
                                    {[
                                        { num: tpl.data.organization.employees?.toLocaleString(), label: t('templates.employees') },
                                        { num: tpl.data.infrastructure.servers?.toLocaleString(), label: t('templates.servers') },
                                        { num: tpl.data.organization.it_staff?.toLocaleString(), label: t('templates.itSec') },
                                    ].map(s => (
                                        <div key={s.label} className={styles.statBox}>
                                            <span className={styles.statNum}>{s.num}</span>
                                            <span className={styles.statLabel}>{s.label}</span>
                                        </div>
                                    ))}
                                </div>

                                <div className={styles.metaGrid}>
                                    {[
                                        { label: 'Cloud', value: tpl.data.infrastructure.cloud?.split(',')[0]?.split('(')[0]?.trim() || 'None' },
                                        { label: 'Firewall', value: tpl.data.infrastructure.firewalls?.split(',')[0]?.trim() || 'None' },
                                        { label: 'SIEM', value: tpl.data.infrastructure.siem?.split(',')[0]?.split('+')[0]?.trim() || 'None' },
                                        { label: 'Status', value: tpl.data.compliance.iso_status?.split('(')[0]?.trim() || '—' },
                                    ].map(m => (
                                        <div key={m.label} className={styles.metaItem}>
                                            <span className={styles.metaLabel}>{m.label}</span>
                                            <span className={styles.metaValue}>{m.value}</span>
                                        </div>
                                    ))}
                                </div>

                                <div className={styles.complianceSection}>
                                    <div className={styles.complianceHeader}>
                                        <span className={styles.complianceTitle}>{t('templates.compliance')}</span>
                                        <span className={styles.complianceValue}>{implemented}/{total} — {percent}%</span>
                                    </div>
                                    <div className={styles.complianceTrack}>
                                        <div className={styles.complianceFill} style={{
                                            width: `${percent}%`,
                                            background: percent >= 80 ? 'var(--accent-green)'
                                                      : percent >= 50 ? 'var(--accent-blue)'
                                                      : percent >= 25 ? 'var(--accent-amber, #f59e0b)'
                                                      : 'var(--accent-red, #ef4444)'
                                        }} />
                                    </div>
                                </div>

                                {/* Sample evidence — matched to this template's controls */}
                                {tplEvidence.length > 0 && (
                                    <div className={styles.evidenceSection}>
                                        <div className={styles.evidenceHeader}>
                                            <span className={styles.evidenceTitle}>📋 {t('templates.evidence')}</span>
                                            <span className={styles.evidenceCount}>{tplEvidence.length} {t('templates.evidenceFiles')}</span>
                                        </div>
                                        <div className={styles.evidenceList}>
                                            {tplEvidence.map(ev => (
                                                <div key={ev.id} className={styles.evidenceItem}>
                                                    <FileText size={13} className={styles.evidenceIcon} />
                                                    <span className={styles.evidenceName} title={t(ev.descriptionKey) || ev.fallbackDescription}>
                                                        {t(ev.labelKey) || ev.fallbackLabel}
                                                    </span>
                                                    <button
                                                        type="button"
                                                        className={styles.evidencePreviewBtn}
                                                        onClick={(e) => { e.stopPropagation(); openPreview(ev) }}
                                                        title={t('evidenceLibrary.preview')}
                                                        aria-label={`${t('evidenceLibrary.preview')} ${ev.fallbackLabel}`}
                                                    >
                                                        <Eye size={13} />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Uploaded evidence section */}
                                <div className={styles.evidenceSection}>
                                    <div className={styles.evidenceHeader}>
                                        <span className={styles.evidenceTitle}>📎 {t('templates.uploadedEvidence')}</span>
                                        <span className={styles.evidenceCount}>
                                            {(uploadedMap[tpl.id] || []).length} {t('templates.evidenceFiles')}
                                        </span>
                                    </div>

                                    {/* Upload drop zone */}
                                    <div
                                        className={styles.uploadZone}
                                        onDragOver={(e) => e.preventDefault()}
                                        onDrop={(e) => handleDrop(tpl.id, e)}
                                        onClick={() => fileInputRefs.current[tpl.id]?.click()}
                                        role="button"
                                        tabIndex={0}
                                        aria-label={t('templates.uploadEvidence')}
                                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRefs.current[tpl.id]?.click() }}
                                    >
                                        <Upload size={14} className={styles.uploadIcon} />
                                        <span className={styles.uploadText}>
                                            {uploadingMap[tpl.id] ? t('templates.uploading') : t('templates.uploadEvidenceHint')}
                                        </span>
                                        <input
                                            ref={el => { fileInputRefs.current[tpl.id] = el }}
                                            type="file"
                                            className={styles.uploadInput}
                                            onChange={(e) => handleFileSelect(tpl.id, e)}
                                            aria-hidden="true"
                                            tabIndex={-1}
                                        />
                                    </div>

                                    {uploadError[tpl.id] && (
                                        <p className={styles.uploadErrorMsg}>{t('templates.uploadError')}</p>
                                    )}

                                    {/* Uploaded evidence list */}
                                    {(uploadedMap[tpl.id] || []).length > 0 ? (
                                        <div className={styles.evidenceList}>
                                            {(uploadedMap[tpl.id] || []).map(ev => (
                                                <div key={ev.doc_id} className={styles.evidenceItem}>
                                                    <FileText size={13} className={styles.evidenceIcon} />
                                                    <span className={styles.evidenceName} title={ev.filename}>
                                                        {ev.filename}
                                                    </span>
                                                    <span className={styles.evidenceSize}>
                                                        {formatFileSize(ev.size_bytes)}
                                                    </span>
                                                    <button
                                                        type="button"
                                                        className={styles.evidencePreviewBtn}
                                                        onClick={(e) => {
                                                            e.stopPropagation()
                                                            openPreview({ ...ev, _uploaded: true, _templateId: tpl.id })
                                                        }}
                                                        title={t('evidenceLibrary.preview')}
                                                        aria-label={`${t('evidenceLibrary.preview')} ${ev.filename}`}
                                                    >
                                                        <Eye size={13} />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className={styles.noEvidence}>{t('templates.noUploadedEvidence')}</p>
                                    )}
                                </div>
                            </div>

                            <div className={styles.cardFooter}>
                                <button className={styles.useBtn} onClick={() => selectTemplate(tpl)} aria-label={`${t('templates.analyzeSystem')} ${tpl.name}`}>
                                    <Zap size={13} style={{ marginRight: '5px', verticalAlign: 'middle' }} />
                                    {t('templates.analyzeSystem')}
                                </button>
                            </div>
                        </div>
                    )
                })}
                {filteredTemplates.length === 0 && (
                    <div className={styles.emptyState}>
                        <p>{t('templates.noTemplates')}</p>
                    </div>
                )}
            </div>

            <EvidenceLibrary />

            {/* Evidence preview modal — shared across all template cards */}
            {previewFile && (() => {
                const isUploaded = !!previewFile._uploaded
                const displayName = isUploaded ? previewFile.filename : (previewFile.fallbackLabel || previewFile.filename)
                const rawUrl = isUploaded
                    ? getTemplateEvidenceRawUrl(previewFile._templateId, previewFile.doc_id)
                    : previewFile.path
                const mime = isUploaded ? (previewFile.mime_type || '') : (previewFile.mime || '')
                const isImage = isUploaded
                    ? mime.startsWith('image/')
                    : previewFile.kind === 'image'
                const isPdf = mime === 'application/pdf'

                return (
                    <>
                        <div className={styles.previewBackdrop} onClick={closePreview} aria-hidden="true" />
                        <div className={styles.previewModal} role="dialog" aria-modal="true" aria-label={displayName}>
                            <header className={styles.previewHeader}>
                                <div>
                                    <span className={styles.previewLabel}>{t('evidenceLibrary.preview')}</span>
                                    <h3 className={styles.previewTitle}>{displayName}</h3>
                                </div>
                                <div className={styles.previewActions}>
                                    <a href={rawUrl} download={previewFile.filename || displayName} className={styles.previewDownload} title={t('templates.downloadFile')}>
                                        <Download size={16} />
                                    </a>
                                    <button type="button" className={styles.previewClose} onClick={closePreview} aria-label="Close">
                                        <X size={18} />
                                    </button>
                                </div>
                            </header>
                            <div className={styles.previewBody}>
                                {previewLoading ? (
                                    <p style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '2rem' }}>Loading…</p>
                                ) : previewContent ? (
                                    <div className={styles.previewMarkdown}>
                                        <MarkdownRenderer content={previewContent} />
                                    </div>
                                ) : isImage ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={rawUrl} alt={displayName} style={{ maxWidth: '100%', borderRadius: '8px' }} />
                                ) : isPdf ? (
                                    <iframe src={rawUrl} title={displayName} style={{ width: '100%', height: '70vh', border: 'none' }} />
                                ) : (
                                    <div style={{ textAlign: 'center', padding: '2rem' }}>
                                        <p style={{ color: 'var(--text-dim)', marginBottom: '1rem' }}>{t('templates.previewUnavailable')}</p>
                                        <a href={rawUrl} download={previewFile.filename || displayName} className={styles.downloadLink}>
                                            <Download size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                                            {t('templates.downloadFile')}
                                        </a>
                                    </div>
                                )}
                            </div>
                        </div>
                    </>
                )
            })()}
        </div>
    )
}
