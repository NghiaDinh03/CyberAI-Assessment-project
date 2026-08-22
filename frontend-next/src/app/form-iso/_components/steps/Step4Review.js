'use client'

import styles from './steps.module.css'
import { useTranslation } from '@/components/LanguageProvider'

export default function Step4Review({
    form,
    set,
    currentStandard,
    totalControls,
    compliancePercent,
    activeTooltip,
    setActiveTooltip,
}) {
    const { t, locale } = useTranslation()

    return (
        <div className={styles.stepContent}>
            <h2 className={styles.sectionTitle}>{t('assessment.step4Title')}</h2>
            <p className={styles.helperText}>{t('assessment.step4Desc')}</p>

            <div className={styles.fieldFull}>
                <div className={styles.labelWithInfo}>
                    <label>{t('assessment.networkTopology')}</label>
                    <button
                        type="button"
                        className={`${styles.infoIcon} ${activeTooltip === 'topology_guide' ? styles.infoIconActive : ''}`}
                        onClick={() => setActiveTooltip(activeTooltip === 'topology_guide' ? null : 'topology_guide')}
                        title={t('assessment.topologyGuideTooltipTitle')}
                    >ⓘ</button>
                </div>
                <textarea
                    className={styles.textarea}
                    value={form.network_diagram}
                    onChange={e => set('network_diagram', e.target.value)}
                    placeholder={t('assessment.networkTopologyPlaceholder')}
                    rows={3}
                />
            </div>

            <div className={styles.fieldFull}>
                <div className={styles.labelWithInfo}>
                    <label>{t('assessment.additionalNotes')}</label>
                    <button
                        type="button"
                        className={`${styles.infoIcon} ${activeTooltip === 'notes_guide' ? styles.infoIconActive : ''}`}
                        onClick={() => setActiveTooltip(activeTooltip === 'notes_guide' ? null : 'notes_guide')}
                        title={t('assessment.notesGuideTooltipTitle')}
                    >ⓘ</button>
                </div>
                <textarea
                    className={styles.textarea}
                    value={form.notes}
                    onChange={e => set('notes', e.target.value)}
                    placeholder={t('assessment.notesPlaceholder')}
                    rows={2}
                />
            </div>

            <div className={styles.modelSelectorWrap}>
                <div className={styles.modelSelectorHeader}>
                    <h4 className={styles.modelSelectorTitle}>
                        {locale === 'vi' ? 'Lựa Chọn Engine AI Thẩm Định (AI Model Engine)' : 'Assessment AI Model Engine'}
                    </h4>
                    <span className={styles.modelEngineActiveStatus}>🟢 Local Engine Online</span>
                </div>
                <div className={styles.modelGridSelector}>
                    {/* Option 1: Local Gemma 4 - Active */}
                    <div className={`${styles.modelOptionCard} ${styles.modelOptionCardActive}`}>
                        <div className={styles.modelOptionTop}>
                            <div className={styles.modelNameGroup}>
                                <span className={styles.modelMainIcon}>⚡</span>
                                <div>
                                    <div className={styles.modelOptionName}>Gemma 4 (Local Offline AI)</div>
                                    <span className={styles.modelSubBadge}>
                                        {locale === 'vi' ? 'Chạy ngoại tuyến qua Ollama' : 'Offline inference via Ollama'}
                                    </span>
                                </div>
                            </div>
                            <span className={styles.modelBadgeActive}>
                                {locale === 'vi' ? 'Mặc định & Khuyên dùng' : 'Active & Recommended'}
                            </span>
                        </div>
                        <p className={styles.modelOptionDesc}>
                            {locale === 'vi'
                                ? 'Mô hình AI nội bộ xử lý tốc độ cao, phân tích toàn bộ 93 controls & trích xuất báo cáo IT Audit 100% ngoại tuyến, bảo mật tuyệt đối.'
                                : 'High-speed offline inference analyzing 93 controls with zero external data transfer.'}
                        </p>
                        <div className={styles.modelHwBadges}>
                            <span className={styles.modelOptionHw}>Context: 8,192 Tokens</span>
                            <span className={styles.modelOptionHw}>100% Offline</span>
                            <span className={styles.modelOptionHwSafe}>🔒 Zero Data Leakage</span>
                        </div>
                    </div>

                    {/* Option 2: Cloud Claude 3.5 Sonnet - In Development */}
                    <div className={`${styles.modelOptionCard} ${styles.modelOptionCardDisabled}`}>
                        <div className={styles.modelOptionTop}>
                            <div className={styles.modelNameGroup}>
                                <span className={styles.modelMainIcon} style={{ opacity: 0.5 }}>☁️</span>
                                <div>
                                    <div className={styles.modelOptionName} style={{ opacity: 0.6 }}>Claude 3.5 Sonnet (Cloud AI)</div>
                                    <span className={styles.modelSubBadge}>Anthropic / Open Claude</span>
                                </div>
                            </div>
                            <span className={styles.modelBadgeDev}>
                                🔒 {locale === 'vi' ? 'Tính năng đang phát triển' : 'In Development'}
                            </span>
                        </div>
                        <p className={styles.modelOptionDesc} style={{ opacity: 0.5 }}>
                            {locale === 'vi'
                                ? 'Xử lý đám mây hiệu năng cao với ngữ cảnh mở rộng cho báo cáo đa tiêu chuẩn quốc tế.'
                                : 'High performance cloud inference with massive context for international multi-standard audits.'}
                        </p>
                        <div className={styles.modelHwBadges} style={{ opacity: 0.5 }}>
                            <span className={styles.modelOptionHw}>Cloud API</span>
                            <span className={styles.modelOptionHw}>200K Context</span>
                        </div>
                    </div>

                    {/* Option 3: Hybrid Engine - In Development */}
                    <div className={`${styles.modelOptionCard} ${styles.modelOptionCardDisabled}`}>
                        <div className={styles.modelOptionTop}>
                            <div className={styles.modelNameGroup}>
                                <span className={styles.modelMainIcon} style={{ opacity: 0.5 }}>🔄</span>
                                <div>
                                    <div className={styles.modelOptionName} style={{ opacity: 0.6 }}>Hybrid Multi-Phase Engine</div>
                                    <span className={styles.modelSubBadge}>Local AI + Cloud Synthesis</span>
                                </div>
                            </div>
                            <span className={styles.modelBadgeDev}>
                                🔒 {locale === 'vi' ? 'Tính năng đang phát triển' : 'In Development'}
                            </span>
                        </div>
                        <p className={styles.modelOptionDesc} style={{ opacity: 0.5 }}>
                            {locale === 'vi'
                                ? 'Kết hợp phân tích bóc tách PII tại máy nội bộ và tổng hợp báo cáo chuyên sâu qua Cloud.'
                                : 'Combines local PII-safe parsing with cloud-based comprehensive executive reporting.'}
                        </p>
                        <div className={styles.modelHwBadges} style={{ opacity: 0.5 }}>
                            <span className={styles.modelOptionHw}>Multi-Stage</span>
                            <span className={styles.modelOptionHw}>PII Redaction</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className={styles.summaryBox}>
                <h4>{t('assessment.preSubmitCheck')}</h4>
                <ul>
                    <li>{t('assessment.preSubmitStandard')}: <strong>{currentStandard.name}</strong></li>
                    <li>{t('assessment.preSubmitOrg')}: <strong>{form.org_name || t('assessment.preSubmitOrgEmpty')}</strong></li>
                    <li>{t('assessment.preSubmitSize')}: <strong>{t('assessment.preSubmitEmployees', { count: form.employees })}</strong> ({t('assessment.preSubmitServers', { count: form.servers })})</li>
                    <li>{t('assessment.preSubmitScope')}: <strong>
                        {form.assessment_scope === 'full' ? t('assessment.preSubmitScopeFull') :
                            form.assessment_scope === 'by_department' ? `${t('assessment.preSubmitScopeDept')}${form.scope_description ? ` — ${form.scope_description}` : ''}` :
                                `${t('assessment.preSubmitScopeSystem')}${form.scope_description ? ` — ${form.scope_description}` : ''}`}
                    </strong></li>
                    <li>{t('assessment.preSubmitCompliance')}: <strong>{t('assessment.preSubmitControls', { implemented: form.implemented_controls.length, total: totalControls })}</strong> ({compliancePercent}%)</li>
                    <li>{t('assessment.preSubmitAiMode')}: <strong>⚡ 100% Local GPU (gemma4:latest)</strong></li>
                </ul>
            </div>
        </div>
    )
}
