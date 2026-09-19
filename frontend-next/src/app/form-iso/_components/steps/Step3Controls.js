'use client'

import { useMemo, useRef, useState } from 'react'
import styles from './steps.module.css'
import { useTranslation } from '@/components/LanguageProvider'
import ControlRow from '../controls/ControlRow'
import UploadedFilesModal from '../controls/UploadedFilesModal'
import { deriveInputEvidenceMap } from '../../utils/evidenceMatcher'

export default function Step3Controls({
    form,
    currentStandard,
    totalControls,
    compliancePercent,
    riskStats,
    allControls,
    batchFileInputRef,
    batchUploading,
    handleBatchEvidenceUpload,
    batchResultMsg,
    detectedHosts,
    onRemoveDetectedHost,
    uploadedFilesList = [],
    onDeleteUploadedFile,
    controlSearch,
    setControlSearch,
    filterTag,
    setFilterTag,
    expandAllCategories,
    setExpandAllCategories,
    expandedCategory,
    setExpandedCategory,
    toggleCategoryAll,
    toggleControl,
    drawerReturnFocusRef,
    setDrawerControlId,
    fetchEvidenceForControl,
    evidenceMap,
    onOpenFeedbackDrawer,
}) {
    const { t, locale } = useTranslation()
    const batchFolderInputRef = useRef(null)
    const [isDragging, setIsDragging] = useState(false)
    const [showUploadedFilesModal, setShowUploadedFilesModal] = useState(false)

    // Handle Drag & Drop with folder traversal
    const handleDragOver = (e) => {
        e.preventDefault()
        e.stopPropagation()
        if (!isDragging) setIsDragging(true)
    }

    const handleDragLeave = (e) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)
    }

    const handleDrop = async (e) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)
        if (batchUploading) return

        const dt = e.dataTransfer
        if (!dt) return

        const items = dt.items
        if (!items || items.length === 0) {
            if (dt.files && dt.files.length > 0) {
                handleBatchEvidenceUpload(Array.from(dt.files))
            }
            return
        }

        const collectedFiles = []
        const traverseEntry = async (entry) => {
            if (entry.isFile) {
                const file = await new Promise((resolve) => entry.file(resolve))
                collectedFiles.push(file)
            } else if (entry.isDirectory) {
                const reader = entry.createReader()
                let entries = []
                let batch
                do {
                    batch = await new Promise((resolve) => reader.readEntries(resolve))
                    entries = entries.concat(batch)
                } while (batch && batch.length > 0)
                for (const child of entries) {
                    await traverseEntry(child)
                }
            }
        }

        const promises = []
        for (let i = 0; i < items.length; i++) {
            const entry = items[i].webkitGetAsEntry ? items[i].webkitGetAsEntry() : null
            if (entry) {
                promises.push(traverseEntry(entry))
            } else if (items[i].kind === 'file') {
                const f = items[i].getAsFile()
                if (f) collectedFiles.push(f)
            }
        }

        await Promise.all(promises)
        if (collectedFiles.length > 0) {
            handleBatchEvidenceUpload(collectedFiles)
        }
    }

    // Real-time input & file evidence matching
    const inputEvidenceMap = useMemo(() => {
        return deriveInputEvidenceMap(form, evidenceMap)
    }, [form, evidenceMap])

    // Controls that belong to the currently active standard only
    const validImplemented = useMemo(() => {
        const standardControlIds = new Set(allControls.map(c => c.id))
        return form.implemented_controls.filter(id => standardControlIds.has(id))
    }, [form.implemented_controls, allControls])

    // Controls with actual uploaded evidence
    const controlsWithEvidenceCount = useMemo(() => {
        return Object.keys(evidenceMap || {}).filter(k => evidenceMap[k] && evidenceMap[k].length > 0).length
    }, [evidenceMap])

    const missingEvidenceCount = Math.max(0, validImplemented.length - controlsWithEvidenceCount)

    return (
        <div className={styles.stepContent}>
            <div className={styles.controlHeader}>
                <div>
                    <h2 className={styles.sectionTitle}>{t('assessment.controlsTitle')}</h2>
                    <p className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('assessment.controlsStandard', { name: currentStandard.name }) }} />
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <div className={styles.counterBadge} title={locale === 'vi' ? 'Số biện pháp kiểm soát doanh nghiệp tự chọn áp dụng' : 'Controls selected by organization'}>
                        <span className={styles.countNum}>{validImplemented.length}</span> / {totalControls} {locale === 'vi' ? 'Khai báo' : 'Declared'}
                    </div>
                    <div className={styles.counterBadge} style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)' }} title={locale === 'vi' ? 'Số biện pháp đã nạp tệp bằng chứng đối chiếu' : 'Controls with attached evidence'}>
                        📎 <strong>{controlsWithEvidenceCount}</strong> / {totalControls} {locale === 'vi' ? 'Có tệp' : 'Files'}
                    </div>
                </div>
            </div>

            <div className={styles.complianceBar}>
                <div className={styles.complianceTrack}>
                    <div
                        className={styles.complianceFill}
                        style={{ width: `${compliancePercent}%` }}
                    />
                </div>
                <span className={styles.complianceLabel}>
                    {locale === 'vi'
                        ? `Tự khai báo: ${validImplemented.length}/${totalControls} controls (${compliancePercent}%) · Có minh chứng: ${controlsWithEvidenceCount}/${totalControls}`
                        : `Declared: ${validImplemented.length}/${totalControls} controls (${compliancePercent}%) · With Evidence: ${controlsWithEvidenceCount}/${totalControls}`}
                </span>
            </div>

            <div className={styles.riskBadgeRow}>
                <div className={`${styles.riskBadge} ${styles.riskBadgeCrit}`}>
                    <span className={styles.riskDot} />
                    <strong>Critical:</strong> {riskStats.critical.done}/{riskStats.critical.total} {locale === 'vi' ? 'Khai báo' : 'Selected'}
                </div>
                <div className={`${styles.riskBadge} ${styles.riskBadgeHigh}`}>
                    <span className={styles.riskDot} />
                    <strong>High:</strong> {riskStats.high.done}/{riskStats.high.total} {locale === 'vi' ? 'Khai báo' : 'Selected'}
                </div>
                <div className={`${styles.riskBadge} ${styles.riskBadgeMed}`}>
                    <span className={styles.riskDot} />
                    <strong>Medium:</strong> {riskStats.medium.done}/{riskStats.medium.total} {locale === 'vi' ? 'Khai báo' : 'Selected'}
                </div>
                <div className={`${styles.riskBadge}`} style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    <span>📎</span>
                    <strong>{locale === 'vi' ? 'Đã có tệp:' : 'With Files:'}</strong> {controlsWithEvidenceCount}
                </div>
                <div className={`${styles.riskBadge} ${styles.riskBadgeEvidence}`}>
                    <span>⚠️</span>
                    <strong>{locale === 'vi' ? 'Chưa có tệp:' : 'No Files:'}</strong> {missingEvidenceCount}
                </div>
            </div>

            <div
                className={`${styles.batchIngestCard} ${isDragging ? styles.batchDropActive : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
            >
                <div className={styles.batchIngestHeader}>
                    <div className={styles.batchIngestTitle}>
                        <div style={{ width: 36, height: 36, borderRadius: '8px', background: 'rgba(59, 130, 246, 0.15)', border: '1px solid rgba(59, 130, 246, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#60a5fa', flexShrink: 0 }}>
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="17 8 12 3 7 8" />
                                <line x1="12" y1="3" x2="12" y2="15" />
                            </svg>
                        </div>
                        <div>
                            <div className={styles.batchMainTitle}>
                                {locale === 'vi' ? 'Nạp Hàng Loạt Log & Thư Mục Bằng Chứng' : 'Batch Evidence & Folder Ingestion'}
                            </div>
                            <div className={styles.batchSub}>
                                {locale === 'vi'
                                    ? 'Hỗ trợ chọn tệp lẻ hoặc nạp cả thư mục (kèm tính năng kéo thả). Hệ thống tự bóc tách và đối chiếu tiêu chí phù hợp.'
                                    : 'Upload multiple files or entire folder (drag & drop supported). System auto-parses and maps to compliance controls.'}
                            </div>
                            <span className={styles.batchDropHint}>
                                {locale === 'vi'
                                    ? '💡 Mẹo: Bạn có thể kéo thả trực tiếp cả thư mục từ máy tính vào khung này.'
                                    : '💡 Tip: You can drag & drop an entire folder directly from your desktop into this card.'}
                            </span>
                        </div>
                    </div>

                    <div className={styles.batchButtonGroup}>
                        <button
                            type="button"
                            className={styles.batchBtn}
                            onClick={() => batchFileInputRef.current?.click()}
                            disabled={batchUploading}
                            title={locale === 'vi' ? 'Chọn nhiều tệp lẻ từ hộp thoại tệp' : 'Upload individual files'}
                        >
                            {batchUploading ? (
                                <>{locale === 'vi' ? 'Đang phân tích...' : 'Analyzing...'}</>
                            ) : (
                                <>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                        <polyline points="14 2 14 8 20 8" />
                                    </svg>
                                    {locale === 'vi' ? 'Chọn tệp lẻ' : 'Select Files'}
                                </>
                            )}
                        </button>

                        <button
                            type="button"
                            className={styles.batchBtnFolder}
                            onClick={() => batchFolderInputRef.current?.click()}
                            disabled={batchUploading}
                            title={locale === 'vi' ? 'Tải lên toàn bộ thư mục mà không cần Ctrl+A' : 'Upload entire folder directly'}
                        >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                            </svg>
                            {locale === 'vi' ? 'Chọn cả thư mục (Folder)' : 'Upload Folder'}
                        </button>

                        <button
                            type="button"
                            className={styles.batchBtnReview}
                            onClick={() => setShowUploadedFilesModal(true)}
                            title={locale === 'vi' ? 'Xem danh mục tệp đã nạp, nội dung bóc tách thô và xóa tệp rác' : 'Review uploaded files, view raw text and delete noise'}
                        >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                <polyline points="14 2 14 8 20 8" />
                                <line x1="16" y1="13" x2="8" y2="13" />
                                <line x1="16" y1="17" x2="8" y2="17" />
                            </svg>
                            {locale === 'vi'
                                ? `Quản lý tệp (${uploadedFilesList.length})`
                                : `Manage Files (${uploadedFilesList.length})`}
                        </button>
                    </div>

                    {/* Hidden individual files input */}
                    <input
                        type="file"
                        multiple
                        ref={batchFileInputRef}
                        style={{ display: 'none' }}
                        onChange={(e) => {
                            if (e.target.files && e.target.files.length > 0) {
                                const selectedFiles = Array.from(e.target.files)
                                e.target.value = ''
                                handleBatchEvidenceUpload(selectedFiles)
                            }
                        }}
                    />

                    {/* Hidden folder input with webkitdirectory */}
                    <input
                        type="file"
                        webkitdirectory=""
                        directory=""
                        multiple
                        ref={batchFolderInputRef}
                        style={{ display: 'none' }}
                        onChange={(e) => {
                            if (e.target.files && e.target.files.length > 0) {
                                const selectedFiles = Array.from(e.target.files)
                                e.target.value = ''
                                handleBatchEvidenceUpload(selectedFiles)
                            }
                        }}
                    />
                </div>

                {batchResultMsg && (
                    <div className={`${styles.batchAlert} ${
                        batchResultMsg.type === 'success'
                            ? styles.batchAlertSuccess
                            : batchResultMsg.type === 'warning'
                            ? styles.batchAlertWarning
                            : styles.batchAlertError
                    }`}>
                        <div className={styles.batchAlertContent}>
                            <span className={styles.batchAlertIcon}>
                                {batchResultMsg.type === 'success' ? '✓' : batchResultMsg.type === 'warning' ? '⚠️' : '✕'}
                            </span>
                            <span className={styles.batchAlertText}>{batchResultMsg.text}</span>
                            {uploadedFilesList.length > 0 && (
                                <button
                                    type="button"
                                    className={styles.batchAlertActionBtn}
                                    onClick={() => setShowUploadedFilesModal(true)}
                                >
                                    {locale === 'vi' ? 'Xem danh mục tệp →' : 'Review files →'}
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {detectedHosts.length > 0 && (
                    <div className={styles.detectedHostsRow}>
                        <span className={styles.detectedLabel}>
                            {locale === 'vi' ? 'Máy chủ phát hiện được:' : 'Detected Hosts:'}
                        </span>
                        <div className={styles.hostBadges}>
                            {detectedHosts.map((h, i) => (
                                <span key={i} className={styles.hostBadge} title={h.os || ''}>
                                    <strong>{h.hostname || h.ip}</strong> {h.ip && h.hostname && h.hostname !== h.ip ? `(${h.ip})` : ''}
                                    {onRemoveDetectedHost && (
                                        <button
                                            type="button"
                                            className={styles.hostRemoveBtn}
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                onRemoveDetectedHost(h)
                                            }}
                                            title={locale === 'vi' ? 'Gỡ máy chủ này' : 'Remove host'}
                                        >✕</button>
                                    )}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            <div className={styles.controlToolbar}>
                <div className={styles.searchWrap}>
                    <span className={styles.searchIcon}>🔍</span>
                    <input
                        type="text"
                        className={styles.searchInput}
                        placeholder={locale === 'vi' ? 'Tìm kiếm theo mã, tên biện pháp (firewall, backup, hotfix, mật khẩu)...' : 'Search controls by ID, name, keyword...'}
                        value={controlSearch}
                        onChange={(e) => setControlSearch(e.target.value)}
                    />
                    {controlSearch && (
                        <button
                            type="button"
                            className={styles.clearSearchBtn}
                            onClick={() => setControlSearch('')}
                        >✕</button>
                    )}
                </div>

                <div className={styles.filterChips}>
                    <button
                        type="button"
                        className={`${styles.filterChip} ${filterTag === 'all' ? styles.filterChipActive : ''}`}
                        onClick={() => setFilterTag('all')}
                    >
                        {locale === 'vi' ? 'Tất cả' : 'All'} ({allControls.length})
                    </button>
                    <button
                        type="button"
                        className={`${styles.filterChip} ${filterTag === 'critical' ? styles.filterChipActiveCrit : ''}`}
                        onClick={() => setFilterTag('critical')}
                    >
                        🔴 Critical ({riskStats.critical.total})
                    </button>
                    <button
                        type="button"
                        className={`${styles.filterChip} ${filterTag === 'high' ? styles.filterChipActiveHigh : ''}`}
                        onClick={() => setFilterTag('high')}
                    >
                        🟠 High ({riskStats.high.total})
                    </button>
                    <button
                        type="button"
                        className={`${styles.filterChip} ${filterTag === 'no_evidence' ? styles.filterChipActiveEv : ''}`}
                        onClick={() => setFilterTag('no_evidence')}
                    >
                        📎 {locale === 'vi' ? 'Chưa có tệp' : 'No Files'} ({riskStats.missingEvidence})
                    </button>
                    <button
                        type="button"
                        className={`${styles.filterChip} ${filterTag === 'implemented' ? styles.filterChipActiveDone : ''}`}
                        onClick={() => setFilterTag('implemented')}
                    >
                        ✅ {locale === 'vi' ? 'Đã tick' : 'Checked'} ({validImplemented.length})
                    </button>
                </div>
            </div>

            <div className={styles.categoryActionRow}>
                <button
                    type="button"
                    className={styles.expandAllBtn}
                    onClick={() => setExpandAllCategories(prev => !prev)}
                >
                    {expandAllCategories
                        ? (locale === 'vi' ? '▲ Thu gọn tất cả nhóm' : '▲ Collapse All Groups')
                        : (locale === 'vi' ? '▼ Mở rộng tất cả nhóm Controls' : '▼ Expand All Control Groups')}
                </button>
                <button
                    type="button"
                    className={styles.expandAllBtn}
                    style={{ background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}
                    onClick={() => onOpenFeedbackDrawer?.()}
                    title={locale === 'vi' ? 'Quản lý kho tri thức kiểm toán & phán quyết mẫu của chuyên gia' : 'Manage Auditor Feedback & Golden Cases'}
                >
                    ⚖️ {locale === 'vi' ? 'Kho Tri Thức Kiểm Toán' : 'Auditor Knowledge Base'}
                </button>
            </div>

            <p className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('assessment.controlsHelp') }} />

            <div className={styles.accordionContainer}>
                {currentStandard.controls.map((category, catIdx) => {
                    const catControlIds = category.controls.map(c => c.id)
                    const selectedInCat = form.implemented_controls.filter(id => catControlIds.includes(id)).length
                    const isAllSelected = selectedInCat === category.controls.length

                    const filteredControls = category.controls.filter(ctrl => {
                        if (controlSearch.trim()) {
                            const q = controlSearch.toLowerCase().trim()
                            const idMatch = ctrl.id.toLowerCase().includes(q)
                            const labelMatch = (ctrl.label || '').toLowerCase().includes(q)
                            const catMatch = (category.category || '').toLowerCase().includes(q)
                            if (!idMatch && !labelMatch && !catMatch) return false
                        }
                        if (filterTag === 'critical' && ctrl.weight !== 'critical') return false
                        if (filterTag === 'high' && ctrl.weight !== 'high') return false
                        if (filterTag === 'no_evidence') {
                            const evCount = (evidenceMap[ctrl.id] || []).length
                            if (evCount > 0) return false
                        }
                        if (filterTag === 'implemented') {
                            if (!form.implemented_controls.includes(ctrl.id)) return false
                        }
                        return true
                    })

                    if (filteredControls.length === 0 && (controlSearch.trim() || filterTag !== 'all')) {
                        return null
                    }

                    const isAutoExpanded = (controlSearch.trim() || filterTag !== 'all') && filteredControls.length > 0
                    const isExpanded = expandAllCategories || isAutoExpanded || expandedCategory === catIdx

                    return (
                        <div key={catIdx} className={`${styles.accordionItem} ${isExpanded ? styles.expanded : ''}`}>
                            <div
                                className={styles.accordionHeader}
                                onClick={() => setExpandedCategory(isExpanded && !isAutoExpanded ? null : catIdx)}
                            >
                                <div className={styles.accTitle}>
                                    <span className={styles.accIcon}>{isExpanded ? '📂' : '📁'}</span>
                                    {category.category}
                                </div>
                                <div className={styles.accMeta}>
                                    <span className={`${styles.accCount} ${selectedInCat === category.controls.length ? styles.accCountFull : ''}`}>
                                        {selectedInCat}/{category.controls.length}
                                    </span>
                                    <span className={styles.accArrow}>{isExpanded ? '▲' : '▼'}</span>
                                </div>
                            </div>

                            {isExpanded && (
                                <div className={styles.accordionBody}>
                                    <div className={styles.selectAllBox}>
                                        <label className={styles.checkLabel}>
                                            <input
                                                type="checkbox"
                                                checked={isAllSelected}
                                                onChange={() => toggleCategoryAll(category.controls, isAllSelected)}
                                            />
                                            <strong>{t('assessment.selectAllGroup')}</strong>
                                        </label>
                                    </div>
                                    <div className={styles.controlList}>
                                        {filteredControls.map(ctrl => {
                                            const implemented = form.implemented_controls.includes(ctrl.id)
                                            const evCount = (evidenceMap[ctrl.id] || []).length
                                            const insights = inputEvidenceMap[ctrl.id] || []
                                            return (
                                                <ControlRow
                                                    key={ctrl.id}
                                                    control={ctrl}
                                                    state={{ implemented }}
                                                    onToggleImplemented={toggleControl}
                                                    onOpenDrawer={(id) => {
                                                        drawerReturnFocusRef.current =
                                                            document.activeElement instanceof HTMLElement
                                                                ? document.activeElement
                                                                : null
                                                        setDrawerControlId(id)
                                                        fetchEvidenceForControl(id)
                                                    }}
                                                    evidenceCount={evCount}
                                                    evidenceInsights={insights}
                                                    verdict={undefined}
                                                />
                                            )
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>

            <UploadedFilesModal
                isOpen={showUploadedFilesModal}
                onClose={() => setShowUploadedFilesModal(false)}
                files={uploadedFilesList}
                onDeleteFile={onDeleteUploadedFile}
                locale={locale}
            />
        </div>
    )
}
