'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslation } from '@/components/LanguageProvider'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import styles from './page.module.css'
import { Globe, Check, BookOpen, Shield, ChevronRight, ChevronLeft, FileText, Server, Database, BarChart2, Brain, FlaskConical, Building2, ClipboardList, HardDrive, FileCode, Layers, X, Maximize2, Minimize2, ArrowUp } from 'lucide-react'

const LANGUAGES = [
    { code: 'en', labelKey: 'settings.langEnglish', subKey: 'settings.langEnglishSub' },
    { code: 'vi', labelKey: 'settings.langVietnamese', subKey: 'settings.langVietnameseSub' },
]

const ASSESSMENT_MODE_KEY = 'cyberai.assessmentMode'
const ASSESSMENT_MODE_EVENT = 'cyberai:assessment-mode-change'
const ASSESSMENT_MODES = [
    { id: 'cloud', labelKey: 'settings.assessmentMode.cloud.label', descKey: 'settings.assessmentMode.cloud.desc' },
    { id: 'local', labelKey: 'settings.assessmentMode.local.label', descKey: 'settings.assessmentMode.local.desc' },
    { id: 'hybrid', labelKey: 'settings.assessmentMode.hybrid.label', descKey: 'settings.assessmentMode.hybrid.desc' },
]

const readStoredAssessmentMode = () => {
    if (typeof window === 'undefined') return 'hybrid'
    try {
        const v = window.localStorage.getItem(ASSESSMENT_MODE_KEY)
        return v === 'cloud' || v === 'local' || v === 'hybrid' ? v : 'hybrid'
    } catch (_) { return 'hybrid' }
}

const DOCS_LIST = [
    { id: 'architecture', icon: Layers, titleKey: 'docs.architectureTitle', descKey: 'docs.architectureDesc', fileEn: 'architecture.md', fileVi: 'architecture.md' },
    { id: 'api', icon: FileCode, titleKey: 'docs.apiTitle', descKey: 'docs.apiDesc', fileEn: 'api.md', fileVi: 'api.md' },
    { id: 'deployment', icon: Server, titleKey: 'docs.deploymentTitle', descKey: 'docs.deploymentDesc', fileEn: 'deployment.md', fileVi: 'deployment.md' },
    { id: 'chatbot_rag', icon: Brain, titleKey: 'docs.chatbotRagTitle', descKey: 'docs.chatbotRagDesc', fileEn: 'chatbot_rag.md', fileVi: 'chatbot_rag.md' },
    { id: 'chromadb', icon: Database, titleKey: 'docs.chromadbTitle', descKey: 'docs.chromadbDesc', fileEn: 'chromadb_guide.md', fileVi: 'chromadb_guide.md' },
    { id: 'algorithms', icon: BarChart2, titleKey: 'docs.algorithmsTitle', descKey: 'docs.algorithmsDesc', fileEn: 'algorithms.md', fileVi: 'algorithms.md' },
    { id: 'analytics', icon: BarChart2, titleKey: 'docs.analyticsTitle', descKey: 'docs.analyticsDesc', fileEn: 'analytics_monitoring.md', fileVi: 'analytics_monitoring.md' },
    { id: 'benchmark', icon: FlaskConical, titleKey: 'docs.benchmarkTitle', descKey: 'docs.benchmarkDesc', fileEn: 'benchmark.md', fileVi: 'benchmark.md' },
    { id: 'case_studies', icon: Building2, titleKey: 'docs.caseStudiesTitle', descKey: 'docs.caseStudiesDesc', fileEn: 'case_studies.md', fileVi: 'case_studies.md' },
    { id: 'iso_form', icon: ClipboardList, titleKey: 'docs.isoFormTitle', descKey: 'docs.isoFormDesc', fileEn: 'iso_assessment_form.md', fileVi: 'iso_assessment_form.md' },
    { id: 'backup', icon: HardDrive, titleKey: 'docs.backupTitle', descKey: 'docs.backupDesc', fileEn: 'backup_strategy.md', fileVi: null },
    { id: 'markdown_rag', icon: FileText, titleKey: 'docs.markdownRagTitle', descKey: 'docs.markdownRagDesc', fileEn: 'markdown_rag_standard.md', fileVi: null },
    { id: 'multi_standard', icon: Shield, titleKey: 'docs.multiStandardTitle', descKey: 'docs.multiStandardDesc', fileEn: 'multi_standard_assessment_plan_v2.md', fileVi: null },
]

export default function SettingsPage() {
    const router = useRouter()
    const { locale, setLocale, t } = useTranslation()
    const [saved, setSaved] = useState(false)
    const [assessmentMode, setAssessmentMode] = useState('hybrid')
    const [modeSaved, setModeSaved] = useState(false)
    const [docContent, setDocContent] = useState(null)
    const [docTitle, setDocTitle] = useState('')
    const [docLoading, setDocLoading] = useState(false)
    const [docLang, setDocLang] = useState('en')
    const [expanded, setExpanded] = useState(false)
    const [showScrollTop, setShowScrollTop] = useState(false)
    const bodyRef = useRef(null)

    const handleSelect = (code) => {
        setLocale(code)
        setSaved(true)
        const timer = setTimeout(() => setSaved(false), 2000)
        return () => clearTimeout(timer)
    }

    useEffect(() => {
        setAssessmentMode(readStoredAssessmentMode())
    }, [])

    const handleSelectMode = (mode) => {
        setAssessmentMode(mode)
        try { window.localStorage.setItem(ASSESSMENT_MODE_KEY, mode) } catch (_) {}
        try { window.dispatchEvent(new CustomEvent(ASSESSMENT_MODE_EVENT, { detail: mode })) } catch (_) {}
        setModeSaved(true)
        setTimeout(() => setModeSaved(false), 2000)
    }

    const openDoc = useCallback(async (doc) => {
        const file = locale === 'vi' && doc.fileVi ? doc.fileVi : doc.fileEn
        const dir = locale === 'vi' && doc.fileVi ? 'vi' : 'en'
        const url = `/api/docs/${dir}/${file}`
        setDocTitle(t(doc.titleKey))
        setDocLang(dir)
        setDocLoading(true)
        setDocContent(null)
        setExpanded(false)
        try {
            const res = await fetch(url)
            if (res.ok) {
                const text = await res.text()
                setDocContent(text)
            } else {
                setDocContent(`> ⚠️ Failed to load document (HTTP ${res.status})`)
            }
        } catch (e) {
            setDocContent(`> ⚠️ Network error: ${e.message}`)
        } finally {
            setDocLoading(false)
        }
    }, [locale, t])

    const closeDoc = useCallback(() => {
        setDocContent(null)
        setDocTitle('')
        setDocLoading(false)
        setExpanded(false)
    }, [])

    const handleBodyScroll = useCallback(() => {
        if (bodyRef.current) {
            setShowScrollTop(bodyRef.current.scrollTop > 300)
        }
    }, [])

    const scrollToTop = useCallback(() => {
        bodyRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
    }, [])

    useEffect(() => {
        const handleEsc = (e) => {
            if (e.key === 'Escape') closeDoc()
        }
        if (docContent !== null || docLoading) {
            document.addEventListener('keydown', handleEsc)
            document.body.style.overflow = 'hidden'
        }
        return () => {
            document.removeEventListener('keydown', handleEsc)
            document.body.style.overflow = ''
        }
    }, [docContent, docLoading, closeDoc])

    const isOpen = docContent !== null || docLoading

    return (
        <div className="page-container">
            <div className={styles.header}>
                <h1 className={styles.title}>{t('settings.title')}</h1>
                <p className={styles.subtitle}>{t('settings.subtitle')}</p>
            </div>

            {/* Language Section */}
            <div className={styles.section}>
                <h2 className={styles.sectionTitle}>
                    <Globe size={16} />
                    {t('settings.languageTitle')}
                </h2>
                <div className={styles.card}>
                    <div className={styles.languageOptions}>
                        {LANGUAGES.map(lang => (
                            <button
                                key={lang.code}
                                className={`${styles.languageOption} ${locale === lang.code ? styles.languageOptionActive : ''}`}
                                onClick={() => handleSelect(lang.code)}
                                aria-pressed={locale === lang.code}
                            >
                                <span className={`${styles.radioCircle} ${locale === lang.code ? styles.radioCircleActive : ''}`}>
                                    <span className={`${styles.radioDot} ${locale === lang.code ? styles.radioDotActive : ''}`} />
                                </span>
                                <span className={styles.langInfo}>
                                    <span className={styles.langLabel}>{t(lang.labelKey)}</span>
                                    <span className={styles.langSub}>{t(lang.subKey)}</span>
                                </span>
                            </button>
                        ))}
                    </div>
                    {saved && (
                        <div className={styles.savedIndicator}>
                            <Check size={14} />
                            {t('settings.languageSaved')}
                        </div>
                    )}
                    <p className={styles.note}>
                        {t('settings.languageNote')}
                    </p>
                </div>
            </div>

            {/* Assessment Mode Section */}
            <div className={styles.section} style={{ animationDelay: '0.04s' }}>
                <h2 className={styles.sectionTitle}>
                    <Brain size={16} />
                    {t('settings.assessmentMode.title')}
                </h2>
                <div className={styles.card}>
                    <p className={styles.note} style={{ marginTop: 0 }}>
                        {t('settings.assessmentMode.description')}
                    </p>
                    <div className={styles.languageOptions}>
                        {ASSESSMENT_MODES.map(opt => (
                            <button
                                key={opt.id}
                                className={`${styles.languageOption} ${assessmentMode === opt.id ? styles.languageOptionActive : ''}`}
                                onClick={() => handleSelectMode(opt.id)}
                                aria-pressed={assessmentMode === opt.id}
                            >
                                <span className={`${styles.radioCircle} ${assessmentMode === opt.id ? styles.radioCircleActive : ''}`}>
                                    <span className={`${styles.radioDot} ${assessmentMode === opt.id ? styles.radioDotActive : ''}`} />
                                </span>
                                <span className={styles.langInfo}>
                                    <span className={styles.langLabel}>{t(opt.labelKey)}</span>
                                    <span className={styles.langSub}>{t(opt.descKey)}</span>
                                </span>
                            </button>
                        ))}
                    </div>
                    {modeSaved && (
                        <div className={styles.savedIndicator}>
                            <Check size={14} />
                            {t('settings.assessmentMode.saved')}
                        </div>
                    )}
                </div>
            </div>

            {/* User Guides Section */}
            <div className={styles.section} style={{ animationDelay: '0.08s' }}>
                <h2 className={styles.sectionTitle}>
                    <BookOpen size={16} />
                    {t('settings.userGuides')}
                </h2>
                <div className={styles.guideGrid}>
                    <button
                        className={styles.guideCard}
                        onClick={() => router.push('/settings/guide')}
                        aria-label={t('settings.guideAssessmentTitle')}
                    >
                        <div className={styles.guideCardIcon}>
                            <Shield size={22} />
                        </div>
                        <div className={styles.guideCardBody}>
                            <div className={styles.guideCardTop}>
                                <h3 className={styles.guideCardTitle}>{t('settings.guideAssessmentTitle')}</h3>
                                <span className={styles.guideCardBadge}>{t('settings.guideAssessmentBadge')}</span>
                            </div>
                            <p className={styles.guideCardDesc}>{t('settings.guideAssessmentDesc')}</p>
                        </div>
                        <ChevronRight size={18} className={styles.guideCardArrow} />
                    </button>
                    <button
                        className={styles.guideCard}
                        onClick={() => router.push('/settings/prompts/chat')}
                        aria-label={t('settings.promptsChatTitle')}
                    >
                        <div className={styles.guideCardIcon}>
                            <Brain size={22} />
                        </div>
                        <div className={styles.guideCardBody}>
                            <div className={styles.guideCardTop}>
                                <h3 className={styles.guideCardTitle}>{t('settings.promptsChatTitle')}</h3>
                                <span className={styles.guideCardBadge}>{t('settings.promptsChatBadge')}</span>
                            </div>
                            <p className={styles.guideCardDesc}>{t('settings.promptsChatDesc')}</p>
                        </div>
                        <ChevronRight size={18} className={styles.guideCardArrow} />
                    </button>
                    <button
                        className={styles.guideCard}
                        onClick={() => router.push('/settings/prompts/assessment')}
                        aria-label={t('settings.promptsAssessmentTitle')}
                    >
                        <div className={styles.guideCardIcon}>
                            <ClipboardList size={22} />
                        </div>
                        <div className={styles.guideCardBody}>
                            <div className={styles.guideCardTop}>
                                <h3 className={styles.guideCardTitle}>{t('settings.promptsAssessmentTitle')}</h3>
                                <span className={styles.guideCardBadge}>{t('settings.promptsAssessmentBadge')}</span>
                            </div>
                            <p className={styles.guideCardDesc}>{t('settings.promptsAssessmentDesc')}</p>
                        </div>
                        <ChevronRight size={18} className={styles.guideCardArrow} />
                    </button>
                </div>
            </div>

            {/* Documentation Library Section */}
            <div className={styles.section} style={{ animationDelay: '0.16s' }}>
                <h2 className={styles.sectionTitle}>
                    <FileText size={16} />
                    {t('docs.sectionTitle')}
                </h2>
                <div className={styles.docsGrid}>
                    {DOCS_LIST.map(doc => {
                        const Icon = doc.icon
                        const hasViDoc = doc.fileVi !== null
                        const showingVi = locale === 'vi' && hasViDoc
                        return (
                            <button
                                key={doc.id}
                                className={styles.docCard}
                                onClick={() => openDoc(doc)}
                                aria-label={t(doc.titleKey)}
                            >
                                <div className={styles.docCardIcon}>
                                    <Icon size={18} />
                                </div>
                                <div className={styles.docCardBody}>
                                    <h3 className={styles.docCardTitle}>{t(doc.titleKey)}</h3>
                                    <p className={styles.docCardDesc}>{t(doc.descKey)}</p>
                                </div>
                                <div className={styles.docCardMeta}>
                                    <span className={`${styles.docLangBadge} ${showingVi ? styles.docLangVi : styles.docLangEn}`}>
                                        {showingVi ? 'VI' : 'EN'}
                                    </span>
                                    <ChevronRight size={14} className={styles.docCardArrow} />
                                </div>
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Document Viewer - Full Screen Overlay */}
            {isOpen && (
                <>
                    <div className={styles.docOverlay} onClick={closeDoc} />
                    <div className={`${styles.docViewer} ${expanded ? styles.docViewerExpanded : ''}`}>
                        <div className={styles.docViewerHeader}>
                            <div className={styles.docViewerHeaderLeft}>
                                <button className={styles.docViewerBack} onClick={closeDoc} aria-label="Close">
                                    <ChevronLeft size={16} />
                                </button>
                                <div className={styles.docViewerTitleGroup}>
                                    <h3 className={styles.docViewerTitle}>{docTitle}</h3>
                                    <span className={`${styles.docViewerLangBadge} ${docLang === 'vi' ? styles.docLangVi : styles.docLangEn}`}>
                                        {docLang.toUpperCase()}
                                    </span>
                                </div>
                            </div>
                            <div className={styles.docViewerHeaderRight}>
                                <button
                                    className={styles.docViewerBtn}
                                    onClick={() => setExpanded(e => !e)}
                                    aria-label={expanded ? 'Minimize' : 'Maximize'}
                                >
                                    {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                                </button>
                                <button className={styles.docViewerClose} onClick={closeDoc} aria-label="Close">
                                    <X size={16} />
                                </button>
                            </div>
                        </div>
                        <div
                            className={`${styles.docViewerBody} ${expanded ? styles.docBodyExpanded : ''}`}
                            ref={bodyRef}
                            onScroll={handleBodyScroll}
                        >
                            {docLoading ? (
                                <div className={styles.docViewerLoading}>
                                    <div className={styles.loadingSpinner} />
                                    <span>{t('common.loading')}</span>
                                </div>
                            ) : (
                                <div className={`${styles.docViewerContent} ${expanded ? styles.docContentExpanded : ''}`}>
                                    <MarkdownRenderer content={docContent || ''} />
                                </div>
                            )}
                        </div>
                        {showScrollTop && !docLoading && (
                            <button className={styles.scrollTopBtn} onClick={scrollToTop} aria-label="Scroll to top">
                                <ArrowUp size={15} />
                            </button>
                        )}
                    </div>
                </>
            )}
        </div>
    )
}
