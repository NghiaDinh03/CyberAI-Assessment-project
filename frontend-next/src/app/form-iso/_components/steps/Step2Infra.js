'use client'

import styles from './steps.module.css'
import { useTranslation } from '@/components/LanguageProvider'

export default function Step2Infra({ form, set }) {
    const { t } = useTranslation()

    return (
        <div className={styles.stepContent}>
            <h2 className={styles.sectionTitle}>{t('assessment.step2Title')}</h2>
            <p className={styles.helperText}>{t('assessment.step2Desc') || 'Khai báo thông số máy chủ, hệ thống phòng thủ, bảo mật và sao lưu'}</p>
            <div className={styles.grid}>
                <div className={styles.field}>
                    <label>{t('assessment.serversLabel')}</label>
                    <input
                        type="number"
                        value={form.servers || ''}
                        onChange={e => set('servers', parseInt(e.target.value) || 0)}
                        placeholder="0"
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.firewallLabel')}</label>
                    <textarea
                        className={styles.autoTextarea}
                        value={form.firewalls}
                        onChange={e => set('firewalls', e.target.value)}
                        placeholder={t('assessment.firewallPlaceholder')}
                        rows={2}
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.cloudLabel')}</label>
                    <textarea
                        className={styles.autoTextarea}
                        value={form.cloud_provider}
                        onChange={e => set('cloud_provider', e.target.value)}
                        placeholder={t('assessment.cloudPlaceholder')}
                        rows={2}
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.antivirusLabel')}</label>
                    <textarea
                        className={styles.autoTextarea}
                        value={form.antivirus}
                        onChange={e => set('antivirus', e.target.value)}
                        placeholder={t('assessment.antivirusPlaceholder')}
                        rows={2}
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.backupLabel')}</label>
                    <textarea
                        className={styles.autoTextarea}
                        value={form.backup_solution}
                        onChange={e => set('backup_solution', e.target.value)}
                        placeholder={t('assessment.backupPlaceholder')}
                        rows={2}
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.siemLabel')}</label>
                    <textarea
                        className={styles.autoTextarea}
                        value={form.siem}
                        onChange={e => set('siem', e.target.value)}
                        placeholder={t('assessment.siemPlaceholder')}
                        rows={2}
                    />
                </div>
                <div className={styles.field}>
                    <label>{t('assessment.incidentsLabel')}</label>
                    <input
                        type="number"
                        value={form.incidents_12m || ''}
                        onChange={e => set('incidents_12m', parseInt(e.target.value) || 0)}
                        placeholder="0"
                    />
                </div>
                <div className={styles.fieldCheckbox}>
                    <label className={styles.checkLabel}>
                        <input
                            type="checkbox"
                            checked={form.vpn}
                            onChange={e => set('vpn', e.target.checked)}
                        />
                        <span>{t('assessment.vpnLabel')}</span>
                    </label>
                </div>
            </div>
        </div>
    )
}
