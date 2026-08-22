'use client'

import styles from './steps.module.css'
import { useTranslation } from '@/components/LanguageProvider'

export default function Step1Org({
    form,
    set,
    handleStandardChange,
    availableStandards,
    standardsLoading,
    activeTooltip,
    setActiveTooltip,
}) {
    const { t } = useTranslation()

    return (
        <div className={styles.stepContent}>
            <h2 className={styles.sectionTitle}>{t('assessment.step1Title')}</h2>
            <p className={styles.helperText}>{t('assessment.standardHelp')}</p>
            <div className={styles.grid}>
                <div className={styles.fieldFull}>
                    <label className={styles.highlightLabel}>
                        {t('assessment.standardLabel')} <span className={styles.required}>*</span>
                    </label>
                    <select
                        className={styles.standardSelect}
                        value={form.assessment_standard}
                        onChange={e => handleStandardChange(e.target.value)}
                    >
                        {availableStandards.map(s => (
                            <option key={s.id} value={s.id}>
                                {s.name}{s.source === 'custom' ? ' (custom)' : ''}
                            </option>
                        ))}
                        {standardsLoading && <option disabled>Loading standards...</option>}
                    </select>
                </div>

                <div className={styles.field}>
                    <label>{t('assessment.orgName')} <span className={styles.required}>*</span></label>
                    <input
                        value={form.org_name}
                        onChange={e => set('org_name', e.target.value)}
                        placeholder={t('assessment.orgNamePlaceholder')}
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.orgSize')}</label>
                    <select value={form.org_size} onChange={e => set('org_size', e.target.value)}>
                        <option value="">{t('assessment.orgSizeSelect')}</option>
                        <option value="small">{t('assessment.orgSizeSmall')}</option>
                        <option value="medium">{t('assessment.orgSizeMedium')}</option>
                        <option value="large">{t('assessment.orgSizeLarge')}</option>
                    </select>
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.industry')}</label>
                    <input
                        value={form.industry}
                        onChange={e => set('industry', e.target.value)}
                        placeholder={t('assessment.industryPlaceholder')}
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.complianceStatus')}</label>
                    <select value={form.iso_status} onChange={e => set('iso_status', e.target.value)}>
                        <option value="">{t('assessment.complianceStatusSelect')}</option>
                        <option value="Chưa triển khai">{t('assessment.complianceNotStarted')}</option>
                        <option value="Đang triển khai">{t('assessment.complianceInProgress')}</option>
                        <option value="Đã chứng nhận">{t('assessment.complianceCertified')}</option>
                    </select>
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.totalEmployees')}</label>
                    <input
                        type="number"
                        value={form.employees || ''}
                        onChange={e => set('employees', parseInt(e.target.value) || 0)}
                        placeholder="0"
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.itStaff')}</label>
                    <input
                        type="number"
                        value={form.it_staff || ''}
                        onChange={e => set('it_staff', parseInt(e.target.value) || 0)}
                        placeholder="0"
                    />
                </div>

                <div className={styles.fieldFull}>
                    <div className={styles.scopeSection}>
                        <div className={styles.labelWithInfo}>
                            <label className={styles.highlightLabel}>{t('assessment.scopeTitle')}</label>
                            <button
                                type="button"
                                className={`${styles.infoIcon} ${activeTooltip === 'scope_guide' ? styles.infoIconActive : ''}`}
                                onClick={() => setActiveTooltip(activeTooltip === 'scope_guide' ? null : 'scope_guide')}
                                title={t('assessment.scopeGuideTooltipTitle')}
                            >ⓘ</button>
                        </div>
                        <p className={styles.helperText} style={{ marginBottom: 0 }}>{t('assessment.scopeHelp')}</p>
                        <div className={styles.scopeOptions}>
                            {[
                                { value: 'full', icon: '🏢', label: t('assessment.scopeFull'), desc: t('assessment.scopeFullDesc') },
                                { value: 'by_department', icon: '👥', label: t('assessment.scopeDepartment'), desc: t('assessment.scopeDepartmentDesc') },
                                { value: 'by_system', icon: '🖥️', label: t('assessment.scopeSystem'), desc: t('assessment.scopeSystemDesc') }
                            ].map(opt => (
                                <label
                                    key={opt.value}
                                    className={`${styles.scopeOption} ${form.assessment_scope === opt.value ? styles.scopeOptionActive : ''}`}
                                >
                                    <input
                                        type="radio"
                                        name="assessment_scope"
                                        value={opt.value}
                                        checked={form.assessment_scope === opt.value}
                                        onChange={() => set('assessment_scope', opt.value)}
                                        hidden
                                    />
                                    <span className={styles.scopeOptionIcon}>{opt.icon}</span>
                                    <div className={styles.scopeOptionText}>
                                        <strong>{opt.label}</strong>
                                        <span>{opt.desc}</span>
                                    </div>
                                    {form.assessment_scope === opt.value && (
                                        <span className={styles.scopeCheckMark}>✓</span>
                                    )}
                                </label>
                            ))}
                        </div>
                        {form.assessment_scope !== 'full' && (
                            <div className={styles.scopeDescWrap}>
                                <div className={styles.labelWithInfo}>
                                    <label>
                                        {form.assessment_scope === 'by_department'
                                            ? t('assessment.scopeDeptLabel')
                                            : t('assessment.scopeSysLabel')}
                                        <span className={styles.required}> *</span>
                                    </label>
                                </div>
                                <input
                                    className={styles.scopeDescInput}
                                    value={form.scope_description}
                                    onChange={e => set('scope_description', e.target.value)}
                                    placeholder={form.assessment_scope === 'by_department'
                                        ? t('assessment.scopeDeptPlaceholder')
                                        : t('assessment.scopeSysPlaceholder')}
                                />
                                <p className={styles.helperText} style={{ marginBottom: 0 }}>
                                    {form.assessment_scope === 'by_department'
                                        ? t('assessment.scopeDeptHelp')
                                        : t('assessment.scopeSysHelp')}
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
