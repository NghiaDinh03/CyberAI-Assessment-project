'use client'

import { useMemo } from 'react'
import styles from './steps.module.css'
import { useTranslation } from '@/components/LanguageProvider'
import ControlRow from '../controls/ControlRow'
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
}) {
    const { t, locale } = useTranslation()

    // Real-time input & file evidence matching
    const inputEvidenceMap = useMemo(() => {
        return deriveInputEvidenceMap(form, evidenceMap)
    }, [form, evidenceMap])

    // Controls that belong to the currently active standard only
    const validImplemented = useMemo(() => {
        const standardControlIds = new Set(allControls.map(c => c.id))
        return form.implemented_controls.filter(id => standardControlIds.has(id))
    }, [form.implemented_controls, allControls])

    return (
        <div className={styles.stepContent}>
            <div className={styles.controlHeader}>
                <div>
                    <h2 className={styles.sectionTitle}>{t('assessment.controlsTitle')}</h2>
                    <p className={styles.helperText} dangerouslySetInnerHTML={{ __html: t('assessment.controlsStandard', { name: currentStandard.name }) }} />
                </div>
                <div className={styles.counterBadge}>
                    <span className={styles.countNum}>{validImplemented.length}</span> / {totalControls} {t('assessment.passed')}
                </div>
            </div>

            <div className={styles.complianceBar}>
                <div className={styles.complianceTrack}>
                    <div
                        className={styles.complianceFill}
                        style={{ width: `${compliancePercent}%` }}
                    />
                </div>
                <span className={styles.complianceLabel}>{t('assessment.controlsCompliancePct', { percent: compliancePercent })}</span>
            </div>

            <div className={styles.riskBadgeRow}>
                <div className={`${styles.riskBadge} ${styles.riskBadgeCrit}`}>
                    <span className={styles.riskDot} />
                    <strong>Critical:</strong> {riskStats.critical.done}/{riskStats.critical.total} {locale === 'vi' ? 'Đạt' : 'Passed'}
                </div>
                <div className={`${styles.riskBadge} ${styles.riskBadgeHigh}`}>
                    <span className={styles.riskDot} />
                    <strong>High:</strong> {riskStats.high.done}/{riskStats.high.total} {locale === 'vi' ? 'Đạt' : 'Passed'}
                </div>
                <div className={`${styles.riskBadge} ${styles.riskBadgeMed}`}>
                    <span className={styles.riskDot} />
                    <strong>Medium:</strong> {riskStats.medium.done}/{riskStats.medium.total} {locale === 'vi' ? 'Đạt' : 'Passed'}
                </div>
                <div className={`${styles.riskBadge} ${styles.riskBadgeEvidence}`}>
                    <span>📎</span>
                    <strong>{locale === 'vi' ? 'Chưa có tệp:' : 'No Files:'}</strong> {riskStats.missingEvidence}
                </div>
            </div>

            <div className={styles.batchIngestCard}>
                <div className={styles.batchIngestHeader}>
                    <div className={styles.batchIngestTitle}>
                        <span className={styles.batchIcon}>⚡</span>
                        <div>
                            <div className={styles.batchMainTitle}>
                                {locale === 'vi' ? 'Nạp Hàng Loạt Log & Tệp Bằng Chứng' : 'Batch Evidence & Scan Log Ingestion'}
                            </div>
                            <div className={styles.batchSub}>
                                {locale === 'vi'
                                    ? 'Tự động bóc tách log máy chủ (systeminfo, Hotfix KB, Firewall...) & tự động tick chọn Controls phù hợp'
                                    : 'Auto-parse server scan logs & auto-populate compliance controls with mapped evidence'}
                            </div>
                        </div>
                    </div>
                    <button
                        type="button"
                        className={styles.batchBtn}
                        onClick={() => batchFileInputRef.current?.click()}
                        disabled={batchUploading}
                    >
                        {batchUploading ? (
                            <>⏳ {locale === 'vi' ? 'Đang phân tích...' : 'Analyzing...'}</>
                        ) : (
                            <>📁 {locale === 'vi' ? 'Chọn nhiều tệp log/bằng chứng' : 'Upload Batch Files'}</>
                        )}
                    </button>
                    <input
                        type="file"
                        multiple
                        ref={batchFileInputRef}
                        style={{ display: 'none' }}
                        onChange={(e) => {
                            if (e.target.files?.length > 0) {
                                handleBatchEvidenceUpload(e.target.files)
                                e.target.value = ''
                            }
                        }}
                    />
                </div>

                {batchResultMsg && (
                    <div className={`${styles.batchAlert} ${batchResultMsg.type === 'success' ? styles.batchAlertSuccess : styles.batchAlertError}`}>
                        {batchResultMsg.text}
                    </div>
                )}

                {detectedHosts.length > 0 && (
                    <div className={styles.detectedHostsRow}>
                        <span className={styles.detectedLabel}>🖥️ {locale === 'vi' ? 'Máy chủ phát hiện được:' : 'Detected Hosts:'}</span>
                        <div className={styles.hostBadges}>
                            {detectedHosts.map((h, i) => (
                                <span key={i} className={styles.hostBadge} title={h.os || ''}>
                                    <strong>{h.hostname || h.ip}</strong> {h.ip && h.hostname ? `(${h.ip})` : ''}
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
        </div>
    )
}
