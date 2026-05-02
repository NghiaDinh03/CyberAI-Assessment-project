'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useTranslation } from '@/components/LanguageProvider'
import styles from './page.module.css'
import {
    ArrowLeft, Shield, Landmark, Server, CheckSquare, FileText,
    ChevronDown, ChevronUp, Zap, Lock, Cloud, BookOpen,
    AlertTriangle, TrendingUp, Download, History, LayoutTemplate,
    Upload, Eye, Trash2, RotateCcw, Layers
} from 'lucide-react'

const TOC_KEYS = [
    { id: 'overview', labelKey: 'guide.toc1', icon: BookOpen },
    { id: 'workflow', labelKey: 'guide.toc2', icon: Layers },
    { id: 'step1', labelKey: 'guide.toc3', icon: Landmark },
    { id: 'step2', labelKey: 'guide.toc4', icon: Server },
    { id: 'step3', labelKey: 'guide.toc5', icon: CheckSquare },
    { id: 'step4', labelKey: 'guide.toc6', icon: FileText },
    { id: 'ai-modes', labelKey: 'guide.toc7', icon: Zap },
    { id: 'results', labelKey: 'guide.toc8', icon: TrendingUp },
    { id: 'history', labelKey: 'guide.toc9', icon: History },
    { id: 'evidence', labelKey: 'guide.toc10', icon: Upload },
    { id: 'export', labelKey: 'guide.toc11', icon: Download },
    { id: 'scoring', labelKey: 'guide.toc12', icon: Shield },
    { id: 'faq', labelKey: 'guide.toc13', icon: AlertTriangle },
]

function Collapse({ title, children, defaultOpen = false }) {
    const [open, setOpen] = useState(defaultOpen)
    return (
        <div className={`${styles.collapse} ${open ? styles.collapseOpen : ''}`}>
            <button
                type="button"
                className={styles.collapseHeader}
                onClick={() => setOpen(!open)}
                aria-expanded={open}
            >
                <span className={styles.collapseTitle}>{title}</span>
                {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {open && <div className={styles.collapseBody}>{children}</div>}
        </div>
    )
}

export default function AssessmentGuidePage() {
    const { t } = useTranslation()
    const scrollTo = (id) => {
        const el = document.getElementById(id)
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }

    return (
        <div className="page-container">
            <div className={styles.header}>
                <Link href="/settings" className={styles.backLink}>
                    <ArrowLeft size={16} />
                    <span>{t('guide.backToSettings')}</span>
                </Link>
                <div className={styles.headerContent}>
                    <div className={styles.headerIcon}>
                        <Shield size={24} />
                    </div>
                    <div>
                        <h1 className={styles.title}>{t('guide.pageTitle')}</h1>
                        <p className={styles.subtitle}>
                            {t('guide.pageSubtitle')}
                        </p>
                    </div>
                </div>
            </div>

            <div className={styles.layout}>
                {/* Table of Contents sidebar */}
                <nav className={styles.toc} aria-label={t('guide.tocTitle')}>
                    <h3 className={styles.tocTitle}>{t('guide.tocTitle')}</h3>
                    {TOC_KEYS.map(item => {
                        const Icon = item.icon
                        return (
                            <button
                                key={item.id}
                                className={styles.tocItem}
                                onClick={() => scrollTo(item.id)}
                            >
                                <Icon size={14} />
                                <span>{t(item.labelKey)}</span>
                            </button>
                        )
                    })}
                </nav>

                {/* Main content */}
                <div className={styles.content}>

                    {/* ─── 1. Overview ──────────────────────────────────────────────── */}
                    <section id="overview" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <BookOpen size={18} />
                            {t('guide.sec1Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec1Desc') }} />
                            <div className={styles.highlightBox}>
                                <strong>{t('guide.sec1Purpose')}</strong>
                                <ul className={styles.bulletList}>
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec1Bullet1') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec1Bullet2') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec1Bullet3') }} />
                                    <li>{t('guide.sec1Bullet4')}</li>
                                </ul>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec1SubSupported')}</h4>
                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec1ThStandard')}</th>
                                            <th>{t('guide.sec1ThScope')}</th>
                                            <th>{t('guide.sec1ThControls')}</th>
                                            <th>{t('guide.sec1ThSuitableFor')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>ISO 27001:2022</strong></td>
                                            <td>{t('guide.sec1Iso27001Scope')}</td>
                                            <td>{t('guide.sec1Iso27001Controls')}</td>
                                            <td>{t('guide.sec1Iso27001Suitable')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>TCVN 11930:2017</strong></td>
                                            <td>{t('guide.sec1TcvnScope')}</td>
                                            <td>{t('guide.sec1TcvnControls')}</td>
                                            <td>{t('guide.sec1TcvnSuitable')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>NIST CSF 2.0</strong></td>
                                            <td>{t('guide.sec1NistScope')}</td>
                                            <td>{t('guide.sec1NistControls')}</td>
                                            <td>{t('guide.sec1NistSuitable')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>PCI DSS 4.0</strong></td>
                                            <td>{t('guide.sec1PciScope')}</td>
                                            <td>{t('guide.sec1PciControls')}</td>
                                            <td>{t('guide.sec1PciSuitable')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>HIPAA</strong></td>
                                            <td>{t('guide.sec1HipaaScope')}</td>
                                            <td>{t('guide.sec1HipaaControls')}</td>
                                            <td>{t('guide.sec1HipaaSuitable')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>GDPR</strong></td>
                                            <td>{t('guide.sec1GdprScope')}</td>
                                            <td>{t('guide.sec1GdprControls')}</td>
                                            <td>{t('guide.sec1GdprSuitable')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>SOC 2</strong></td>
                                            <td>{t('guide.sec1Soc2Scope')}</td>
                                            <td>{t('guide.sec1Soc2Controls')}</td>
                                            <td>{t('guide.sec1Soc2Suitable')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>

                    {/* ─── 2. Workflow ──────────────────────────────────────────────── */}
                    <section id="workflow" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <Layers size={18} />
                            {t('guide.sec2Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec2Desc') }} />
                            <div className={styles.stepsFlow}>
                                <div className={styles.stepFlowItem}>
                                    <div className={styles.stepFlowNum}>1</div>
                                    <div className={styles.stepFlowContent}>
                                        <strong>{t('guide.sec2Step1Title')}</strong>
                                        <span>{t('guide.sec2Step1Desc')}</span>
                                    </div>
                                </div>
                                <div className={styles.stepFlowArrow}>→</div>
                                <div className={styles.stepFlowItem}>
                                    <div className={`${styles.stepFlowNum} ${styles.stepFlowNum2}`}>2</div>
                                    <div className={styles.stepFlowContent}>
                                        <strong>{t('guide.sec2Step2Title')}</strong>
                                        <span>{t('guide.sec2Step2Desc')}</span>
                                    </div>
                                </div>
                                <div className={styles.stepFlowArrow}>→</div>
                                <div className={styles.stepFlowItem}>
                                    <div className={`${styles.stepFlowNum} ${styles.stepFlowNum3}`}>3</div>
                                    <div className={styles.stepFlowContent}>
                                        <strong>{t('guide.sec2Step3Title')}</strong>
                                        <span>{t('guide.sec2Step3Desc')}</span>
                                    </div>
                                </div>
                                <div className={styles.stepFlowArrow}>→</div>
                                <div className={styles.stepFlowItem}>
                                    <div className={`${styles.stepFlowNum} ${styles.stepFlowNum4}`}>4</div>
                                    <div className={styles.stepFlowContent}>
                                        <strong>{t('guide.sec2Step4Title')}</strong>
                                        <span>{t('guide.sec2Step4Desc')}</span>
                                    </div>
                                </div>
                            </div>
                            <div className={styles.tipBox}>
                                <strong>{t('guide.sec2Tip')}</strong>{' '}
                                <span dangerouslySetInnerHTML={{ __html: t('guide.sec2TipText') }} />
                            </div>
                        </div>
                    </section>

                    {/* ─── 3. Step 1 ───────────────────────────────────────────────── */}
                    <section id="step1" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <Landmark size={18} />
                            {t('guide.sec3Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph}>
                                {t('guide.sec3Desc')}
                            </p>

                            <h4 className={styles.subHeading}>{t('guide.sec3SubFields')}</h4>
                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec3ThField')}</th>
                                            <th>{t('guide.sec3ThRequired')}</th>
                                            <th>{t('guide.sec3ThDescription')}</th>
                                            <th>{t('guide.sec3ThExample')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>{t('guide.sec3FieldStandard')}</strong></td>
                                            <td><span className={styles.required}>{t('guide.sec3FieldStandardReq')}</span></td>
                                            <td>{t('guide.sec3FieldStandardDesc')}</td>
                                            <td>ISO 27001:2022</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec3FieldOrgName')}</strong></td>
                                            <td><span className={styles.required}>{t('guide.sec3FieldOrgNameReq')}</span></td>
                                            <td>{t('guide.sec3FieldOrgNameDesc')}</td>
                                            <td>{t('guide.sec3FieldOrgNameEx')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec3FieldSize')}</strong></td>
                                            <td>{t('guide.sec3FieldSizeReq')}</td>
                                            <td>{t('guide.sec3FieldSizeDesc')}</td>
                                            <td>{t('guide.sec3FieldSizeEx')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec3FieldIndustry')}</strong></td>
                                            <td>{t('guide.sec3FieldIndustryReq')}</td>
                                            <td>{t('guide.sec3FieldIndustryDesc')}</td>
                                            <td>{t('guide.sec3FieldIndustryEx')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec3FieldCompliance')}</strong></td>
                                            <td>{t('guide.sec3FieldComplianceReq')}</td>
                                            <td>{t('guide.sec3FieldComplianceDesc')}</td>
                                            <td>{t('guide.sec3FieldComplianceEx')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec3FieldEmployees')}</strong></td>
                                            <td>{t('guide.sec3FieldEmployeesReq')}</td>
                                            <td>{t('guide.sec3FieldEmployeesDesc')}</td>
                                            <td>120</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec3FieldItSec')}</strong></td>
                                            <td>{t('guide.sec3FieldItSecReq')}</td>
                                            <td>{t('guide.sec3FieldItSecDesc')}</td>
                                            <td>8</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec3SubScope')}</h4>
                            <p className={styles.paragraph}>
                                {t('guide.sec3ScopeDesc')}
                            </p>
                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec3ThScopeType')}</th>
                                            <th>{t('guide.sec3ThScopeWhen')}</th>
                                            <th>{t('guide.sec3ThExample')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>{t('guide.sec3ScopeFullLabel')}</strong></td>
                                            <td>{t('guide.sec3ScopeFullWhen')}</td>
                                            <td>{t('guide.sec3ScopeFullEx')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec3ScopeDeptLabel')}</strong></td>
                                            <td>{t('guide.sec3ScopeDeptWhen')}</td>
                                            <td>{t('guide.sec3ScopeDeptEx')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec3ScopeSysLabel')}</strong></td>
                                            <td>{t('guide.sec3ScopeSysWhen')}</td>
                                            <td>{t('guide.sec3ScopeSysEx')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <div className={styles.exampleBox}>
                                <strong>{t('guide.sec3ExampleTitle')}</strong>
                                <ol className={styles.orderedList}>
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec3ExampleStep1') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec3ExampleStep2') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec3ExampleStep3') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec3ExampleStep4') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec3ExampleStep5') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec3ExampleStep6') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec3ExampleStep7') }} />
                                </ol>
                            </div>
                        </div>
                    </section>

                    {/* ─── 4. Step 2 ───────────────────────────────────────────────── */}
                    <section id="step2" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <Server size={18} />
                            {t('guide.sec4Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph}>
                                {t('guide.sec4Desc')}
                            </p>

                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec4ThField')}</th>
                                            <th>{t('guide.sec4ThDescription')}</th>
                                            <th>{t('guide.sec4ThRealExample')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>{t('guide.sec4FieldServers')}</strong></td>
                                            <td>{t('guide.sec4FieldServersDesc')}</td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec4FieldServersEx') }} />
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec4FieldFirewall')}</strong></td>
                                            <td>{t('guide.sec4FieldFirewallDesc')}</td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec4FieldFirewallEx') }} />
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec4FieldCloud')}</strong></td>
                                            <td>{t('guide.sec4FieldCloudDesc')}</td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec4FieldCloudEx') }} />
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec4FieldAvEdr')}</strong></td>
                                            <td>{t('guide.sec4FieldAvEdrDesc')}</td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec4FieldAvEdrEx') }} />
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec4FieldBackup')}</strong></td>
                                            <td>{t('guide.sec4FieldBackupDesc')}</td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec4FieldBackupEx') }} />
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec4FieldSiem')}</strong></td>
                                            <td>{t('guide.sec4FieldSiemDesc')}</td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec4FieldSiemEx') }} />
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec4FieldIncidents')}</strong></td>
                                            <td>{t('guide.sec4FieldIncidentsDesc')}</td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec4FieldIncidentsEx') }} />
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec4FieldVpn')}</strong></td>
                                            <td>{t('guide.sec4FieldVpnDesc')}</td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec4FieldVpnEx') }} />
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <div className={styles.tipBox}>
                                <strong>{t('guide.sec4Tip')}</strong>{' '}
                                <span dangerouslySetInnerHTML={{ __html: t('guide.sec4TipText') }} />
                            </div>
                        </div>
                    </section>

                    {/* ─── 5. Step 3 ───────────────────────────────────────────────── */}
                    <section id="step3" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <CheckSquare size={18} />
                            {t('guide.sec5Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec5Desc') }} />

                            <h4 className={styles.subHeading}>{t('guide.sec5SubStructure')}</h4>
                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec5ThGroup')}</th>
                                            <th>{t('guide.sec5ThCount')}</th>
                                            <th>{t('guide.sec5ThMainContent')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec5GroupOrg') }} />
                                            <td>{t('guide.sec5GroupOrgCount')}</td>
                                            <td>{t('guide.sec5GroupOrgContent')}</td>
                                        </tr>
                                        <tr>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec5GroupPeople') }} />
                                            <td>{t('guide.sec5GroupPeopleCount')}</td>
                                            <td>{t('guide.sec5GroupPeopleContent')}</td>
                                        </tr>
                                        <tr>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec5GroupPhysical') }} />
                                            <td>{t('guide.sec5GroupPhysicalCount')}</td>
                                            <td>{t('guide.sec5GroupPhysicalContent')}</td>
                                        </tr>
                                        <tr>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec5GroupTech') }} />
                                            <td>{t('guide.sec5GroupTechCount')}</td>
                                            <td>{t('guide.sec5GroupTechContent')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec5SubWeight')}</h4>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec5WeightDesc') }} />
                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec5ThWeight')}</th>
                                            <th>{t('guide.sec5ThPoints')}</th>
                                            <th>{t('guide.sec5ThMeaning')}</th>
                                            <th>{t('guide.sec5ThExampleControl')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><span className={styles.weightCritical}>critical</span></td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec5CriticalPoints') }} />
                                            <td>{t('guide.sec5CriticalMeaning')}</td>
                                            <td>{t('guide.sec5CriticalExample')}</td>
                                        </tr>
                                        <tr>
                                            <td><span className={styles.weightHigh}>high</span></td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec5HighPoints') }} />
                                            <td>{t('guide.sec5HighMeaning')}</td>
                                            <td>{t('guide.sec5HighExample')}</td>
                                        </tr>
                                        <tr>
                                            <td><span className={styles.weightMedium}>medium</span></td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec5MediumPoints') }} />
                                            <td>{t('guide.sec5MediumMeaning')}</td>
                                            <td>{t('guide.sec5MediumExample')}</td>
                                        </tr>
                                        <tr>
                                            <td><span className={styles.weightLow}>low</span></td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec5LowPoints') }} />
                                            <td>{t('guide.sec5LowMeaning')}</td>
                                            <td>{t('guide.sec5LowExample')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <div className={styles.exampleBox}>
                                <strong>{t('guide.sec5ExampleTitle')}</strong>
                                <ol className={styles.orderedList}>
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec5ExampleStep1') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec5ExampleStep2') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec5ExampleStep3') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec5ExampleStep4') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec5ExampleStep5') }} />
                                </ol>
                            </div>

                            <div className={styles.warningBox}>
                                <strong>{t('guide.sec5Warning')}</strong>{' '}
                                <span dangerouslySetInnerHTML={{ __html: t('guide.sec5WarningText') }} />
                            </div>
                        </div>
                    </section>

                    {/* ─── 6. Step 4 ───────────────────────────────────────────────── */}
                    <section id="step4" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <FileText size={18} />
                            {t('guide.sec6Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph}>
                                {t('guide.sec6Desc')}
                            </p>

                            <h4 className={styles.subHeading}>{t('guide.sec6SubTopology')}</h4>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec6TopologyDesc') }} />

                            <div className={styles.exampleBox}>
                                <strong>{t('guide.sec6TopologyExample')}</strong>
                                <div className={styles.codeBlock}>
                                    {`Mạng chia 5 VLAN:
- VLAN 10 (Server): 20 VM trên VMware ESXi 7.0
- VLAN 20 (User): 150 workstation Windows 11
- VLAN 30 (WiFi Guest): isolated, không access internal
- VLAN 50 (DMZ): Web Server Nginx, Mail Gateway
- VLAN 1 (Management): Switch Cisco Catalyst 9300

Firewall: FortiGate 200F tại biên mạng, block all inbound mặc định.
Zone-based policy: DMZ ↔ Internal chỉ cho phép port 443, 3306.
Internet: 2 ISP (VNPT + Viettel), BGP failover.

Core Banking chạy trên 2 Dell R750 HA Cluster (Active-Passive).
Database: Oracle 19c RAC, TDE enabled.
Backup: Veeam Backup hàng ngày, offsite NAS Synology mỗi tuần.

VPN: FortiClient SSL cho 200 nhân viên remote.
SIEM: Wazuh thu log toàn bộ server + firewall, lưu 12 tháng.
EDR: CrowdStrike Falcon trên 100% endpoint.`}
                                </div>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec6SubNotes')}</h4>
                            <div className={styles.bulletList}>
                                <li dangerouslySetInnerHTML={{ __html: t('guide.sec6NotesBullet1') }} />
                                <li dangerouslySetInnerHTML={{ __html: t('guide.sec6NotesBullet2') }} />
                                <li dangerouslySetInnerHTML={{ __html: t('guide.sec6NotesBullet3') }} />
                                <li dangerouslySetInnerHTML={{ __html: t('guide.sec6NotesBullet4') }} />
                                <li>{t('guide.sec6NotesBullet5')}</li>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec6SubSummary')}</h4>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec6SummaryDesc') }} />
                            <div className={styles.summaryPreview}>
                                <div className={styles.summaryItem}><span>{t('guide.sec6SummaryStandard')}</span> <strong>ISO 27001:2022</strong></div>
                                <div className={styles.summaryItem}><span>{t('guide.sec6SummaryOrg')}</span> <strong>{t('guide.sec6SummaryOrgValue')}</strong></div>
                                <div className={styles.summaryItem}><span>{t('guide.sec6SummarySize')}</span> <strong>{t('guide.sec6SummarySizeValue')}</strong></div>
                                <div className={styles.summaryItem}><span>{t('guide.sec6SummaryScope')}</span> <strong>{t('guide.sec6SummaryScopeValue')}</strong></div>
                                <div className={styles.summaryItem}><span>{t('guide.sec6SummaryCompliance')}</span> <strong>{t('guide.sec6SummaryComplianceValue')}</strong></div>
                                <div className={styles.summaryItem}><span>{t('guide.sec6SummaryAiMode')}</span> <strong>{t('guide.sec6SummaryAiModeValue')}</strong></div>
                            </div>
                        </div>
                    </section>

                    {/* ─── 7. AI Modes ──────────────────────────────────────────────── */}
                    <section id="ai-modes" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <Zap size={18} />
                            {t('guide.sec7Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec7Desc') }} />

                            <div className={styles.aiModeGrid}>
                                <div className={`${styles.aiModeCard} ${styles.aiModeLocal}`}>
                                    <div className={styles.aiModeHeader}>
                                        <Lock size={20} />
                                        <h4>Local Only</h4>
                                        <span className={styles.aiModeBadge}>{t('guide.sec7LocalBadge')}</span>
                                    </div>
                                    <div className={styles.aiModeFlow}>
                                        <span>📋 Form</span> → <span className={styles.flowLocal}>🖥️ SecurityLM</span> → <span className={styles.flowLocal}>🖥️ SecurityLM</span> → <span>📄 Report</span>
                                    </div>
                                    <ul className={styles.aiModeDetails}>
                                        <li><strong>{t('guide.sec7LocalData')}</strong> {t('guide.sec7LocalDataDesc')}</li>
                                        <li><strong>{t('guide.sec7LocalPhase')}</strong> {t('guide.sec7LocalPhaseDesc')}</li>
                                        <li><strong>{t('guide.sec7LocalTime')}</strong> {t('guide.sec7LocalTimeDesc')}</li>
                                        <li><strong>{t('guide.sec7LocalFit')}</strong> {t('guide.sec7LocalFitDesc')}</li>
                                        <li><strong>{t('guide.sec7LocalCon')}</strong> {t('guide.sec7LocalConDesc')}</li>
                                    </ul>
                                </div>

                                <div className={`${styles.aiModeCard} ${styles.aiModeHybrid}`}>
                                    <div className={styles.aiModeHeader}>
                                        <Zap size={20} />
                                        <h4>Hybrid</h4>
                                        <span className={`${styles.aiModeBadge} ${styles.aiModeBadgeRecommend}`}>{t('guide.sec7HybridBadge')}</span>
                                    </div>
                                    <div className={styles.aiModeFlow}>
                                        <span>📋 Form</span> → <span className={styles.flowLocal}>🖥️ SecurityLM</span> → <span>📊 GAP</span> → <span className={styles.flowCloud}>☁️ OpenClaude</span> → <span>📄 Report</span>
                                    </div>
                                    <ul className={styles.aiModeDetails}>
                                        <li><strong>{t('guide.sec7HybridData')}</strong> {t('guide.sec7HybridDataDesc')}</li>
                                        <li><strong>{t('guide.sec7HybridPhase1')}</strong> {t('guide.sec7HybridPhase1Desc')}</li>
                                        <li><strong>{t('guide.sec7HybridPhase2')}</strong> {t('guide.sec7HybridPhase2Desc')}</li>
                                        <li><strong>{t('guide.sec7HybridTime')}</strong> {t('guide.sec7HybridTimeDesc')}</li>
                                        <li><strong>{t('guide.sec7HybridFit')}</strong> {t('guide.sec7HybridFitDesc')}</li>
                                    </ul>
                                </div>

                                <div className={`${styles.aiModeCard} ${styles.aiModeCloud}`}>
                                    <div className={styles.aiModeHeader}>
                                        <Cloud size={20} />
                                        <h4>Cloud Only</h4>
                                        <span className={styles.aiModeBadge}>{t('guide.sec7CloudBadge')}</span>
                                    </div>
                                    <div className={styles.aiModeFlow}>
                                        <span>📋 Form</span> → <span className={styles.flowCloud}>☁️ OpenClaude P1</span> → <span className={styles.flowCloud}>☁️ OpenClaude P2</span> → <span>📄 Report</span>
                                    </div>
                                    <ul className={styles.aiModeDetails}>
                                        <li><strong>{t('guide.sec7CloudData')}</strong> {t('guide.sec7CloudDataDesc')}</li>
                                        <li><strong>{t('guide.sec7CloudPhase')}</strong> {t('guide.sec7CloudPhaseDesc')}</li>
                                        <li><strong>{t('guide.sec7CloudTime')}</strong> {t('guide.sec7CloudTimeDesc')}</li>
                                        <li><strong>{t('guide.sec7CloudFit')}</strong> {t('guide.sec7CloudFitDesc')}</li>
                                        <li><strong>{t('guide.sec7CloudPro')}</strong> {t('guide.sec7CloudProDesc')}</li>
                                    </ul>
                                </div>
                            </div>

                            <div className={styles.warningBox}>
                                <strong>{t('guide.sec7SecurityWarning')}</strong>{' '}
                                <span dangerouslySetInnerHTML={{ __html: t('guide.sec7SecurityWarningText') }} />
                            </div>
                        </div>
                    </section>

                    {/* ─── 8. Results ───────────────────────────────────────────────── */}
                    <section id="results" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <TrendingUp size={18} />
                            {t('guide.sec8Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec8Desc') }} />

                            <h4 className={styles.subHeading}>{t('guide.sec8Sub1')}</h4>
                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec8ThComponent')}</th>
                                            <th>{t('guide.sec8ThDescription')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>{t('guide.sec8GaugeLabel')}</strong></td>
                                            <td>{t('guide.sec8GaugeDesc')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec8BadgeLabel')}</strong></td>
                                            <td>{t('guide.sec8BadgeDesc')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec8ControlsLabel')}</strong></td>
                                            <td dangerouslySetInnerHTML={{ __html: t('guide.sec8ControlsDesc') }} />
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec8ModelChipsLabel')}</strong></td>
                                            <td>{t('guide.sec8ModelChipsDesc')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec8Sub2')}</h4>
                            <p className={styles.paragraph}>
                                {t('guide.sec8CategoryDesc')}
                            </p>
                            <div className={styles.bulletList}>
                                <li>{t('guide.sec8CategoryBullet1')}</li>
                                <li>{t('guide.sec8CategoryBullet2')}</li>
                                <li>{t('guide.sec8CategoryBullet3')}</li>
                                <li>{t('guide.sec8CategoryBullet4')}</li>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec8Sub3')}</h4>
                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec8ThSection')}</th>
                                            <th>{t('guide.sec8ThContent')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>{t('guide.sec8DashRisk')}</strong></td>
                                            <td>{t('guide.sec8DashRiskDesc')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec8DashWeight')}</strong></td>
                                            <td>{t('guide.sec8DashWeightDesc')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec8DashGaps')}</strong></td>
                                            <td>{t('guide.sec8DashGapsDesc')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec8Sub4')}</h4>
                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec8ThCompliance')}</th>
                                            <th>{t('guide.sec8ThLevel')}</th>
                                            <th>{t('guide.sec8ThImplication')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><span className={styles.scoreGreen}>≥ 80%</span></td>
                                            <td>{t('guide.sec8Level1')}</td>
                                            <td>{t('guide.sec8Level1Desc')}</td>
                                        </tr>
                                        <tr>
                                            <td><span className={styles.scoreBlue}>50% – 79%</span></td>
                                            <td>{t('guide.sec8Level2')}</td>
                                            <td>{t('guide.sec8Level2Desc')}</td>
                                        </tr>
                                        <tr>
                                            <td><span className={styles.scoreAmber}>25% – 49%</span></td>
                                            <td>{t('guide.sec8Level3')}</td>
                                            <td>{t('guide.sec8Level3Desc')}</td>
                                        </tr>
                                        <tr>
                                            <td><span className={styles.scoreRed}>&lt; 25%</span></td>
                                            <td>{t('guide.sec8Level4')}</td>
                                            <td>{t('guide.sec8Level4Desc')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>

                    {/* ─── 9. History & Templates ──────────────────────────────────── */}
                    <section id="history" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <History size={18} />
                            {t('guide.sec9Title')}
                        </h2>
                        <div className={styles.card}>
                            <h4 className={styles.subHeading}>{t('guide.sec9SubHistory')}</h4>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec9HistoryDesc') }} />
                            <div className={styles.bulletList}>
                                <li>{t('guide.sec9HistoryBullet1')}</li>
                                <li>{t('guide.sec9HistoryBullet2')}</li>
                                <li>{t('guide.sec9HistoryBullet3')}</li>
                                <li>{t('guide.sec9HistoryBullet4')}</li>
                            </div>

                            <div className={styles.exampleBox}>
                                <strong>{t('guide.sec9HistoryActionsTitle')}</strong>
                                <ul className={styles.bulletList}>
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec9HistoryAction1') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec9HistoryAction2') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec9HistoryAction3') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec9HistoryAction4') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec9HistoryAction5') }} />
                                </ul>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec9SubTemplates')}</h4>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec9TemplatesDesc') }} />

                            <div className={styles.exampleBox}>
                                <strong>{t('guide.sec9TemplatesTitle')}</strong>
                                <ol className={styles.orderedList}>
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec9TemplateStep1') }} />
                                    <li>{t('guide.sec9TemplateStep2')}</li>
                                    <li>{t('guide.sec9TemplateStep3')}</li>
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec9TemplateStep4') }} />
                                    <li>{t('guide.sec9TemplateStep5')}</li>
                                </ol>
                            </div>
                        </div>
                    </section>

                    {/* ─── 10. Evidence ─────────────────────────────────────────────── */}
                    <section id="evidence" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <Upload size={18} />
                            {t('guide.sec10Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec10Desc') }} />

                            <h4 className={styles.subHeading}>{t('guide.sec10SubHow')}</h4>
                            <ol className={styles.orderedList}>
                                <li dangerouslySetInnerHTML={{ __html: t('guide.sec10HowStep1') }} />
                                <li dangerouslySetInnerHTML={{ __html: t('guide.sec10HowStep2') }} />
                                <li dangerouslySetInnerHTML={{ __html: t('guide.sec10HowStep3') }} />
                                <li dangerouslySetInnerHTML={{ __html: t('guide.sec10HowStep4') }} />
                            </ol>

                            <h4 className={styles.subHeading}>{t('guide.sec10SubFormats')}</h4>
                            <div className={styles.fileFormats}>
                                <span className={styles.formatBadge}>.pdf</span>
                                <span className={styles.formatBadge}>.png</span>
                                <span className={styles.formatBadge}>.jpg</span>
                                <span className={styles.formatBadge}>.doc/.docx</span>
                                <span className={styles.formatBadge}>.xlsx</span>
                                <span className={styles.formatBadge}>.csv</span>
                                <span className={styles.formatBadge}>.txt</span>
                                <span className={styles.formatBadge}>.log</span>
                                <span className={styles.formatBadge}>.conf</span>
                                <span className={styles.formatBadge}>.xml</span>
                                <span className={styles.formatBadge}>.json</span>
                            </div>

                            <div className={styles.exampleBox}>
                                <strong>{t('guide.sec10EvidenceTitle')}</strong>
                                <div className={styles.tableWrap}>
                                    <table className={styles.table}>
                                        <thead>
                                            <tr>
                                                <th>{t('guide.sec10ThControl')}</th>
                                                <th>{t('guide.sec10ThEvidence')}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td dangerouslySetInnerHTML={{ __html: t('guide.sec10Ev1Control') }} />
                                                <td>{t('guide.sec10Ev1Desc')}</td>
                                            </tr>
                                            <tr>
                                                <td dangerouslySetInnerHTML={{ __html: t('guide.sec10Ev2Control') }} />
                                                <td>{t('guide.sec10Ev2Desc')}</td>
                                            </tr>
                                            <tr>
                                                <td dangerouslySetInnerHTML={{ __html: t('guide.sec10Ev3Control') }} />
                                                <td>{t('guide.sec10Ev3Desc')}</td>
                                            </tr>
                                            <tr>
                                                <td dangerouslySetInnerHTML={{ __html: t('guide.sec10Ev4Control') }} />
                                                <td>{t('guide.sec10Ev4Desc')}</td>
                                            </tr>
                                            <tr>
                                                <td dangerouslySetInnerHTML={{ __html: t('guide.sec10Ev5Control') }} />
                                                <td>{t('guide.sec10Ev5Desc')}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            <div className={styles.tipBox}>
                                <strong>{t('guide.sec10Tip')}</strong>{' '}
                                <span dangerouslySetInnerHTML={{ __html: t('guide.sec10TipText') }} />
                            </div>
                        </div>
                    </section>

                    {/* ─── 11. Export ───────────────────────────────────────────────── */}
                    <section id="export" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <Download size={18} />
                            {t('guide.sec11Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph}>
                                {t('guide.sec11Desc')}
                            </p>

                            <div className={styles.tableWrap}>
                                <table className={styles.table}>
                                    <thead>
                                        <tr>
                                            <th>{t('guide.sec11ThAction')}</th>
                                            <th>{t('guide.sec11ThDescription')}</th>
                                            <th>{t('guide.sec11ThUseWhen')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>{t('guide.sec11CopyReport')}</strong></td>
                                            <td>{t('guide.sec11CopyReportDesc')}</td>
                                            <td>{t('guide.sec11CopyReportWhen')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec11ViewPdf')}</strong></td>
                                            <td>{t('guide.sec11ViewPdfDesc')}</td>
                                            <td>{t('guide.sec11ViewPdfWhen')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec11DownloadPdf')}</strong></td>
                                            <td>{t('guide.sec11DownloadPdfDesc')}</td>
                                            <td>{t('guide.sec11DownloadPdfWhen')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec11Print')}</strong></td>
                                            <td>{t('guide.sec11PrintDesc')}</td>
                                            <td>{t('guide.sec11PrintWhen')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec11DownloadJson')}</strong></td>
                                            <td>{t('guide.sec11DownloadJsonDesc')}</td>
                                            <td>{t('guide.sec11DownloadJsonWhen')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec11NewAssessment')}</strong></td>
                                            <td>{t('guide.sec11NewAssessmentDesc')}</td>
                                            <td>{t('guide.sec11NewAssessmentWhen')}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>{t('guide.sec11Reassess')}</strong></td>
                                            <td>{t('guide.sec11ReassessDesc')}</td>
                                            <td>{t('guide.sec11ReassessWhen')}</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </section>

                    {/* ─── 12. Scoring ──────────────────────────────────────────────── */}
                    <section id="scoring" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <Shield size={18} />
                            {t('guide.sec12Title')}
                        </h2>
                        <div className={styles.card}>
                            <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec12Desc') }} />

                            <div className={styles.formulaBox}>
                                <h4>{t('guide.sec12FormulaTitle')}</h4>
                                <div className={styles.formula}>
                                    <code>{t('guide.sec12Formula')}</code>
                                </div>
                                <p>{t('guide.sec12FormulaNote')}</p>
                            </div>

                            <h4 className={styles.subHeading}>{t('guide.sec12SubExample')}</h4>
                            <div className={styles.exampleBox}>
                                <strong>{t('guide.sec12ExampleTitle')}</strong>
                                <div className={styles.tableWrap}>
                                    <table className={styles.table}>
                                        <thead>
                                            <tr>
                                                <th>{t('guide.sec12ThWeight')}</th>
                                                <th>{t('guide.sec12ThTotalControls')}</th>
                                                <th>{t('guide.sec12ThChecked')}</th>
                                                <th>{t('guide.sec12ThScoreAchieved')}</th>
                                                <th>{t('guide.sec12ThMaxScore')}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td><span className={styles.weightCritical}>critical</span></td>
                                                <td>22</td>
                                                <td>18</td>
                                                <td>18 × 4 = <strong>72</strong></td>
                                                <td>22 × 4 = 88</td>
                                            </tr>
                                            <tr>
                                                <td><span className={styles.weightHigh}>high</span></td>
                                                <td>30</td>
                                                <td>22</td>
                                                <td>22 × 3 = <strong>66</strong></td>
                                                <td>30 × 3 = 90</td>
                                            </tr>
                                            <tr>
                                                <td><span className={styles.weightMedium}>medium</span></td>
                                                <td>25</td>
                                                <td>16</td>
                                                <td>16 × 2 = <strong>32</strong></td>
                                                <td>25 × 2 = 50</td>
                                            </tr>
                                            <tr>
                                                <td><span className={styles.weightLow}>low</span></td>
                                                <td>16</td>
                                                <td>6</td>
                                                <td>6 × 1 = <strong>6</strong></td>
                                                <td>16 × 1 = 16</td>
                                            </tr>
                                            <tr className={styles.totalRow}>
                                                <td><strong>{t('guide.sec12Total')}</strong></td>
                                                <td><strong>93</strong></td>
                                                <td><strong>62</strong></td>
                                                <td><strong>176</strong></td>
                                                <td><strong>244</strong></td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                <p className={styles.paragraph} style={{ marginTop: '0.75rem' }} dangerouslySetInnerHTML={{ __html: t('guide.sec12Result') }} />
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec12Explanation') }} />
                            </div>
                        </div>
                    </section>

                    {/* ─── 13. FAQ ──────────────────────────────────────────────────── */}
                    <section id="faq" className={styles.section}>
                        <h2 className={styles.sectionTitle}>
                            <AlertTriangle size={18} />
                            {t('guide.sec13Title')}
                        </h2>
                        <div className={styles.card}>
                            <Collapse title={t('guide.sec13Q1')}>
                                <p className={styles.paragraph}>
                                    {t('guide.sec13Q1Intro')}
                                </p>
                                <ul className={styles.bulletList}>
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec13Q1Cloud') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec13Q1Hybrid') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec13Q1Local') }} />
                                </ul>
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q1Note') }} />
                            </Collapse>

                            <Collapse title={t('guide.sec13Q2')}>
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q2Cause') }} />
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q2Fix') }} />
                            </Collapse>

                            <Collapse title={t('guide.sec13Q3')}>
                                <p className={styles.paragraph}>
                                    <span dangerouslySetInnerHTML={{ __html: t('guide.sec13Q3Count') }} />
                                    <br />
                                    <span dangerouslySetInnerHTML={{ __html: t('guide.sec13Q3Weighted') }} />
                                </p>
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q3Note') }} />
                            </Collapse>

                            <Collapse title={t('guide.sec13Q4')}>
                                <p className={styles.paragraph}>
                                    <span dangerouslySetInnerHTML={{ __html: t('guide.sec13Q4Draft') }} />
                                    <br />
                                    <span dangerouslySetInnerHTML={{ __html: t('guide.sec13Q4Results') }} />
                                </p>
                            </Collapse>

                            <Collapse title={t('guide.sec13Q5')}>
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q5Answer') }} />
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q5Note') }} />
                            </Collapse>

                            <Collapse title={t('guide.sec13Q6')}>
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q6Answer') }} />
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q6Note') }} />
                            </Collapse>

                            <Collapse title={t('guide.sec13Q7')}>
                                <p className={styles.paragraph}>
                                    {t('guide.sec13Q7Intro')}
                                </p>
                                <ol className={styles.orderedList}>
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec13Q7Step1') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec13Q7Step2') }} />
                                    <li dangerouslySetInnerHTML={{ __html: t('guide.sec13Q7Step3') }} />
                                </ol>
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q7Alt') }} />
                            </Collapse>

                            <Collapse title={t('guide.sec13Q8')}>
                                <p className={styles.paragraph} dangerouslySetInnerHTML={{ __html: t('guide.sec13Q8Answer') }} />
                            </Collapse>
                        </div>
                    </section>

                    {/* ─── CTA ──────────────────────────────────────────────────────── */}
                    <div className={styles.ctaSection}>
                        <div className={styles.ctaCard}>
                            <h3>{t('guide.readyToStart')}</h3>
                            <p>{t('guide.readyToStartDesc')}</p>
                            <div className={styles.ctaActions}>
                                <Link href="/form-iso" className={styles.ctaPrimary}>
                                    <Shield size={16} />
                                    {t('guide.startAssessment')}
                                </Link>
                                <Link href="/settings" className={styles.ctaSecondary}>
                                    ← {t('guide.backToSettings')}
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
