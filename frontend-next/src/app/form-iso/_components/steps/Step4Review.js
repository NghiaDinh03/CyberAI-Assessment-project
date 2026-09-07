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
                    {/* Model 2: Gemma 4 - Primary Reasoning Auditor */}
                    <div className={`${styles.modelOptionCard} ${styles.modelOptionCardActive}`}>
                        <div className={styles.modelOptionTop}>
                            <div className={styles.modelNameGroup}>
                                <span className={styles.modelMainIcon}>⚡</span>
                                <div>
                                    <div className={styles.modelOptionName}>Gemma 4 (Reasoning Auditor)</div>
                                    <span className={styles.modelSubBadge}>
                                        {locale === 'vi' ? 'Model 2: Thẩm định Tuân thủ ISO 27001' : 'Model 2: ISO 27001 Compliance Auditor'}
                                    </span>
                                </div>
                            </div>
                            <span className={styles.modelBadgeActive}>
                                {locale === 'vi' ? 'Chính & Thẩm Định' : 'Primary Auditor'}
                            </span>
                        </div>
                        <p className={styles.modelOptionDesc}>
                            {locale === 'vi'
                                ? 'Tiếp nhận Fact Cards từ Model 1 để đối soát chuyên sâu với 93 controls ISO 27001, sinh báo cáo IT Audit, SoA và Risk Register.'
                                : 'Evaluates Fact Cards against 93 ISO 27001 controls and produces quantitative compliance reports.'}
                        </p>
                        <div className={styles.modelHwBadges}>
                            <span className={styles.modelOptionHw}>Local GPU (AMD Radeon 860M)</span>
                            <span className={styles.modelOptionHw}>Ollama Local</span>
                            <span className={styles.modelOptionHwSafe}>🔒 100% On-Premise</span>
                        </div>
                    </div>

                    {/* Model 1: Qwen2.5-Coder - Evidence Extractor */}
                    <div className={`${styles.modelOptionCard} ${styles.modelOptionCardActive}`}>
                        <div className={styles.modelOptionTop}>
                            <div className={styles.modelNameGroup}>
                                <span className={styles.modelMainIcon}>🔬</span>
                                <div>
                                    <div className={styles.modelOptionName}>Qwen2.5-Coder:7b (Evidence Extractor)</div>
                                    <span className={styles.modelSubBadge}>
                                        {locale === 'vi' ? 'Model 1: Trích xuất Dữ liệu Kỹ thuật' : 'Model 1: Technical Fact Extractor'}
                                    </span>
                                </div>
                            </div>
                            <span className={styles.modelBadgeActive} style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
                                {locale === 'vi' ? 'Trích Xuất Bằng Chứng' : 'Data Extractor'}
                            </span>
                        </div>
                        <p className={styles.modelOptionDesc}>
                            {locale === 'vi'
                                ? 'Tự động bóc tách file lớn 50 trang (.docx/.pdf), phân tích Heading/Bảng biểu, log hệ thống thành Security Fact Cards chuẩn hóa.'
                                : 'Parses large 50-page reports, logs and system configs into structured Security Fact Cards.'}
                        </p>
                        <div className={styles.modelHwBadges}>
                            <span className={styles.modelOptionHw}>Tự Động Bóc Tách</span>
                            <span className={styles.modelOptionHw}>Zero Data Leakage</span>
                        </div>
                    </div>

                    {/* Model 3: BGE-M3 - Vector RAG Engine */}
                    <div className={`${styles.modelOptionCard} ${styles.modelOptionCardActive}`}>
                        <div className={styles.modelOptionTop}>
                            <div className={styles.modelNameGroup}>
                                <span className={styles.modelMainIcon}>📚</span>
                                <div>
                                    <div className={styles.modelOptionName}>BGE-M3 / Semantic Vector Engine</div>
                                    <span className={styles.modelSubBadge}>
                                        {locale === 'vi' ? 'Model 3: RAG Embedding & Indexing' : 'Model 3: RAG Vector Indexing'}
                                    </span>
                                </div>
                            </div>
                            <span className={styles.modelBadgeActive} style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', borderColor: 'rgba(168, 85, 247, 0.3)' }}>
                                {locale === 'vi' ? 'RAG Tri Thức Chuẩn' : 'RAG Knowledge'}
                            </span>
                        </div>
                        <p className={styles.modelOptionDesc}>
                            {locale === 'vi'
                                ? 'Truy vấn ngữ nghĩa vector điều khoản tiêu chuẩn ISO 27001:2022, TCVN 11930 & Nghị định 13 với ngữ cảnh 8,192 tokens.'
                                : 'Multilingual semantic indexing across ISO 27001:2022 and Vietnamese cybersecurity legal frameworks.'}
                        </p>
                        <div className={styles.modelHwBadges}>
                            <span className={styles.modelOptionHw}>ChromaDB Local</span>
                            <span className={styles.modelOptionHw}>Multilingual 8K Context</span>
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
