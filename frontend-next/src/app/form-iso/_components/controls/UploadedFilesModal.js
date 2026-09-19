'use client'

import React, { useState, useMemo } from 'react'
import styles from './UploadedFilesModal.module.css'

export default function UploadedFilesModal({
    isOpen,
    onClose,
    files = [],
    onDeleteFile,
    locale = 'vi'
}) {
    const [searchTerm, setSearchTerm] = useState('')
    const [previewFile, setPreviewFile] = useState(null)
    const [previewData, setPreviewData] = useState(null)
    const [previewLoading, setPreviewLoading] = useState(false)
    const [copied, setCopied] = useState(false)
    const [deletingName, setDeletingName] = useState(null)

    const filteredFiles = useMemo(() => {
        if (!searchTerm.trim()) return files
        const q = searchTerm.toLowerCase()
        return files.filter(f =>
            (f.clean_name || f.filename || '').toLowerCase().includes(q) ||
            (f.original_name || '').toLowerCase().includes(q) ||
            (f.mapped_controls || []).some(c => c.toLowerCase().includes(q))
        )
    }, [files, searchTerm])

    const totalChars = useMemo(() => {
        return files.reduce((acc, f) => acc + (f.char_count || 0), 0)
    }, [files])

    const totalMapped = useMemo(() => {
        const set = new Set()
        files.forEach(f => {
            (f.mapped_controls || []).forEach(c => set.add(c))
        })
        return set.size
    }, [files])

    if (!isOpen) return null

    const handleOpenPreview = async (file) => {
        setPreviewFile(file)
        setPreviewLoading(true)
        setPreviewData(null)
        setCopied(false)

        try {
            const targetName = encodeURIComponent(file.filename || file.clean_name || '')
            const res = await fetch(`/api/iso27001/evidence/file-content?filename=${targetName}`)
            if (res.ok) {
                const data = await res.json()
                setPreviewData(data)
            } else {
                // Fallback to locally cached preview text
                setPreviewData({
                    filename: file.clean_name || file.filename,
                    full_text: file.preview || file.fact_summary || (locale === 'vi' ? '(Không có bản xem trước văn bản)' : '(No text preview available)'),
                    sha256: file.sha256 || 'N/A',
                    char_count: file.char_count || 0,
                    size_bytes: file.size_bytes || 0
                })
            }
        } catch (e) {
            console.error('Preview fetch error:', e)
            setPreviewData({
                filename: file.clean_name || file.filename,
                full_text: file.preview || (locale === 'vi' ? 'Lỗi kết nối tải nội dung xem trước' : 'Error fetching preview'),
                sha256: file.sha256 || 'N/A',
                char_count: file.char_count || 0,
                size_bytes: file.size_bytes || 0
            })
        } finally {
            setPreviewLoading(false)
        }
    }

    const handleCopy = (text) => {
        if (!text) return
        navigator.clipboard.writeText(text).then(() => {
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        })
    }

    const handleDelete = async (file) => {
        const displayName = file.clean_name || file.filename
        const confirmMsg = locale === 'vi'
            ? `Bạn có chắc chắn muốn xóa tệp "${displayName}" không?\nTệp sẽ được gỡ bỏ khỏi hệ thống và loại trừ khỏi mọi phép đối soát kiểm toán.`
            : `Are you sure you want to delete "${displayName}"?\nThis will remove it from all mapped controls and eliminate audit noise.`

        if (window.confirm(confirmMsg)) {
            setDeletingName(file.filename || file.clean_name)
            try {
                if (onDeleteFile) {
                    await onDeleteFile(file)
                }
            } finally {
                setDeletingName(null)
            }
        }
    }

    const getFormatBadge = (name = '') => {
        const ext = name.split('.').pop()?.toLowerCase()
        switch (ext) {
            case 'docx':
            case 'doc':
                return <div className={`${styles.formatBadge} ${styles.formatDocx}`}>DOCX</div>
            case 'pdf':
                return <div className={`${styles.formatBadge} ${styles.formatPdf}`}>PDF</div>
            case 'xlsx':
            case 'xls':
            case 'csv':
                return <div className={`${styles.formatBadge} ${styles.formatXlsx}`}>XLSX</div>
            case 'log':
            case 'conf':
            case 'txt':
                return <div className={`${styles.formatBadge} ${styles.formatLog}`}>LOG</div>
            default:
                return <div className={`${styles.formatBadge} ${styles.formatDefault}`}>{ext?.slice(0, 4) || 'FILE'}</div>
        }
    }

    const formatSize = (bytes = 0) => {
        if (bytes === 0) return '0 B'
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    return (
        <div className={styles.backdrop} onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className={styles.modal} role="dialog" aria-modal="true">
                {/* Header */}
                <div className={styles.header}>
                    <div className={styles.headerInfo}>
                        <div className={styles.titleRow}>
                            <div className={styles.titleIcon}>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                    <polyline points="14 2 14 8 20 8" />
                                    <line x1="16" y1="13" x2="8" y2="13" />
                                    <line x1="16" y1="17" x2="8" y2="17" />
                                    <polyline points="10 9 9 9 8 9" />
                                </svg>
                            </div>
                            <h3 className={styles.title}>
                                {locale === 'vi' ? 'Danh Mục Bằng Chứng & Tệp Đã Nạp' : 'Staged Evidence Files & Review'}
                            </h3>
                        </div>
                        <p className={styles.subtitle}>
                            {locale === 'vi'
                                ? `Lưu trữ tích lũy đa đợt (${files.length} tệp) · Tự động ánh xạ ${totalMapped} biện pháp · Xem văn bản bóc tách thô và loại bỏ tệp rác (noise)`
                                : `Cumulative ingest across batches (${files.length} files) · Auto-mapped to ${totalMapped} controls · Review raw text and prune noise`}
                        </p>
                    </div>
                    <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close">✕</button>
                </div>

                {/* Toolbar */}
                <div className={styles.toolbar}>
                    <div className={styles.searchWrap}>
                        <span className={styles.searchIcon}>🔍</span>
                        <input
                            type="text"
                            className={styles.searchInput}
                            placeholder={locale === 'vi' ? 'Tìm theo tên tệp, thư mục, mã biện pháp (A.8.8)...' : 'Search by filename, subfolder, control ID...'}
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div className={styles.statsBar}>
                        <span className={`${styles.statBadge} ${styles.statBadgePrimary}`}>
                            {locale === 'vi' ? 'Tổng ký tự trích xuất:' : 'Total Extracted Chars:'} <strong>{totalChars.toLocaleString()}</strong>
                        </span>
                        <span className={`${styles.statBadge} ${styles.statBadgeSuccess}`}>
                            {locale === 'vi' ? 'Đã map:' : 'Mapped:'} <strong>{totalMapped} controls</strong>
                        </span>
                    </div>
                </div>

                {/* Body */}
                <div className={styles.body}>
                    {filteredFiles.length === 0 ? (
                        <div className={styles.emptyState}>
                            <span className={styles.emptyIcon}>📂</span>
                            <div className={styles.emptyText}>
                                {files.length === 0
                                    ? (locale === 'vi' ? 'Chưa có tệp bằng chứng nào được tải lên.' : 'No evidence files uploaded yet.')
                                    : (locale === 'vi' ? 'Không tìm thấy tệp nào phù hợp với từ khóa.' : 'No matching files found.')}
                            </div>
                        </div>
                    ) : (
                        filteredFiles.map((file, idx) => {
                            const displayName = file.clean_name || file.filename
                            const hasSubfolder = file.original_name && file.original_name !== displayName
                            const mappedList = file.mapped_controls || []
                            const isDeleting = deletingName === (file.filename || file.clean_name)

                            return (
                                <div key={idx} className={styles.fileCard} style={{ opacity: isDeleting ? 0.4 : 1 }}>
                                    <div className={styles.fileMain}>
                                        {getFormatBadge(displayName)}
                                        <div className={styles.fileDetails}>
                                            <div className={styles.fileNameRow}>
                                                <span className={styles.fileName}>{displayName}</span>
                                                {hasSubfolder && (
                                                    <span className={styles.originalPath} title={file.original_name}>
                                                        📁 {file.original_name}
                                                    </span>
                                                )}
                                            </div>

                                            <div className={styles.fileMetaRow}>
                                                <span className={styles.metaItem}>
                                                    📦 {formatSize(file.size_bytes)}
                                                </span>
                                                <span className={styles.metaItem}>
                                                    🔤 {file.char_count?.toLocaleString() || 0} {locale === 'vi' ? 'ký tự' : 'chars'}
                                                </span>
                                                {file.sha256 && (
                                                    <span className={styles.metaItem} title={`SHA-256: ${file.sha256}`}>
                                                        🔒 {file.sha256.slice(0, 10)}...
                                                    </span>
                                                )}
                                            </div>

                                            <div className={styles.mappedControlsRow}>
                                                {mappedList.length > 0 ? (
                                                    mappedList.map((ctrl, cIdx) => (
                                                        <span key={cIdx} className={styles.mappedPill}>
                                                            ✓ {ctrl}
                                                        </span>
                                                    ))
                                                ) : (
                                                    <span className={styles.unassignedPill}>
                                                        ⚠️ {locale === 'vi' ? 'Chưa gán biện pháp (_unassigned)' : 'Unassigned'}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className={styles.fileActions}>
                                        <button
                                            type="button"
                                            className={styles.viewBtn}
                                            onClick={() => handleOpenPreview(file)}
                                            title={locale === 'vi' ? 'Xem toàn bộ văn bản thô bóc tách được' : 'View raw extracted text'}
                                        >
                                            👁️ {locale === 'vi' ? 'Xem thô' : 'Raw View'}
                                        </button>

                                        <button
                                            type="button"
                                            className={styles.deleteBtn}
                                            onClick={() => handleDelete(file)}
                                            disabled={isDeleting}
                                            title={locale === 'vi' ? 'Xóa tệp khỏi hệ thống để lọc sạch dữ liệu rác (noise)' : 'Delete file and eliminate audit noise'}
                                        >
                                            🗑️ {locale === 'vi' ? 'Xóa' : 'Delete'}
                                        </button>
                                    </div>
                                </div>
                            )
                        })
                    )}
                </div>

                {/* Footer */}
                <div className={styles.footer}>
                    <span className={styles.footerNote}>
                        {locale === 'vi'
                            ? '💡 Mẹo: Bạn có thể tiếp tục nạp thêm thư mục/tệp mới mà không lo bị ghi đè các lần nạp trước.'
                            : '💡 Tip: You can upload more folders/files anytime; previous uploads remain safely preserved.'}
                    </span>
                    <button type="button" className={styles.closeModalBtn} onClick={onClose}>
                        {locale === 'vi' ? 'Đóng cửa sổ' : 'Close'}
                    </button>
                </div>
            </div>

            {/* Nested Raw Text Preview Modal */}
            {previewFile && (
                <div className={styles.previewBackdrop} onClick={(e) => e.target === e.currentTarget && setPreviewFile(null)}>
                    <div className={styles.previewModal}>
                        <div className={styles.previewHeader}>
                            <h4 className={styles.previewTitle}>
                                📄 {previewFile.clean_name || previewFile.filename}
                            </h4>
                            <button
                                type="button"
                                className={styles.closeBtn}
                                onClick={() => setPreviewFile(null)}
                            >✕</button>
                        </div>

                        <div className={styles.previewMetaBar}>
                            <span>Dung lượng: <strong>{formatSize(previewData?.size_bytes || previewFile.size_bytes)}</strong></span>
                            <span>Ký tự: <strong>{(previewData?.char_count || previewFile.char_count || 0).toLocaleString()}</strong></span>
                            {previewData?.sha256 && (
                                <span className={styles.shaBadge} title="SHA-256 Hash Digest">
                                    SHA256: {previewData.sha256}
                                </span>
                            )}
                            <button
                                type="button"
                                className={`${styles.viewBtn} ${styles.copyBtn}`}
                                onClick={() => handleCopy(previewData?.full_text)}
                            >
                                {copied ? (locale === 'vi' ? '✓ Đã sao chép' : '✓ Copied') : (locale === 'vi' ? '📋 Sao chép text' : '📋 Copy text')}
                            </button>
                        </div>

                        <div className={styles.previewContentWrap}>
                            {previewLoading ? (
                                <div className={styles.previewLoading}>
                                    {locale === 'vi' ? 'Đang tải nội dung văn bản bóc tách thô...' : 'Loading raw text preview...'}
                                </div>
                            ) : (
                                <pre className={styles.rawStreamView}>
                                    {previewData?.full_text || (locale === 'vi' ? '(Tệp không chứa văn bản thô hoặc đang xử lý)' : '(No text extracted)')}
                                </pre>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
