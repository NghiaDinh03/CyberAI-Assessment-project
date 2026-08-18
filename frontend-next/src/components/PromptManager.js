'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslation } from '@/components/LanguageProvider'
import { ArrowLeft, RotateCcw, Save, CheckCircle2, AlertTriangle, Info } from 'lucide-react'
import styles from './PromptManager.module.css'

/**
 * Prompt editor page shared between chat & assessment groups.
 * @param {Object} props
 * @param {'chat'|'assessment'} props.group
 * @param {string} props.titleKey  - i18n key for page title
 * @param {string} props.descKey   - i18n key for page description
 */
export default function PromptManager({ group, titleKey, descKey }) {
    const router = useRouter()
    const { t } = useTranslation()
    const [items, setItems] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [activeKey, setActiveKey] = useState(null)
    const [draft, setDraft] = useState('')
    const [saving, setSaving] = useState(false)
    const [flash, setFlash] = useState(null)

    const load = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`/api/prompts?group=${group}`)
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            const body = await res.json()
            setItems(body.items || [])
            if (body.items?.length && !activeKey) {
                setActiveKey(body.items[0].key)
                setDraft(body.items[0].current)
            }
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }, [group, activeKey])

    useEffect(() => { load() }, [load])

    const active = items.find((i) => i.key === activeKey)
    const isDirty = active && draft !== active.current

    const selectItem = (item) => {
        if (isDirty && !confirm(t('prompts.unsavedConfirm'))) return
        setActiveKey(item.key)
        setDraft(item.current)
        setFlash(null)
    }

    const doSave = async () => {
        if (!active) return
        // Client-side placeholder validation
        const missing = (active.required_placeholders || []).filter((ph) => !draft.includes(ph))
        if (missing.length) {
            setFlash({ type: 'error', text: `${t('prompts.missingPlaceholders')}: ${missing.join(', ')}` })
            return
        }
        setSaving(true)
        setFlash(null)
        try {
            const res = await fetch(`/api/prompts/${encodeURIComponent(active.key)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: draft }),
            })
            if (!res.ok) {
                const err = await res.json().catch(() => ({}))
                throw new Error(err.detail || `HTTP ${res.status}`)
            }
            setFlash({ type: 'success', text: t('prompts.saved') })
            await load()
        } catch (e) {
            setFlash({ type: 'error', text: e.message })
        } finally {
            setSaving(false)
        }
    }

    const doReset = async () => {
        if (!active) return
        if (!confirm(t('prompts.resetConfirm'))) return
        setSaving(true)
        setFlash(null)
        try {
            const res = await fetch(`/api/prompts/${encodeURIComponent(active.key)}/reset`, { method: 'POST' })
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            setFlash({ type: 'success', text: t('prompts.resetDone') })
            await load()
            const fresh = (await (await fetch(`/api/prompts/${encodeURIComponent(active.key)}`)).json())
            setDraft(fresh.current)
        } catch (e) {
            setFlash({ type: 'error', text: e.message })
        } finally {
            setSaving(false)
        }
    }

    return (
        <main className={styles.wrap}>
            <header className={styles.header}>
                <button onClick={() => router.push('/settings')} className={styles.back} aria-label={t('common.back')}>
                    <ArrowLeft size={16} /> {t('common.back')}
                </button>
                <div>
                    <h1 className={styles.title}>{t(titleKey)}</h1>
                    <p className={styles.desc}>{t(descKey)}</p>
                </div>
            </header>

            {error && <div className={styles.errorBox}><AlertTriangle size={14} /> {error}</div>}
            {loading && <div className={styles.loading}>{t('common.loading')}…</div>}

            {!loading && !error && (
                <div className={styles.layout}>
                    <aside className={styles.list} aria-label={t('prompts.listLabel')}>
                        {items.map((it) => (
                            <button
                                key={it.key}
                                className={`${styles.listItem} ${it.key === activeKey ? styles.listItemActive : ''}`}
                                onClick={() => selectItem(it)}
                            >
                                <span className={styles.listTitle}>{it.title}</span>
                                <span className={styles.listMeta}>
                                    {it.is_overridden ? (
                                        <span className={styles.badgeOverride}>{t('prompts.overridden')}</span>
                                    ) : (
                                        <span className={styles.badgeDefault}>{t('prompts.default')}</span>
                                    )}
                                    <span className={styles.listLen}>{it.length} chars</span>
                                </span>
                            </button>
                        ))}
                    </aside>

                    <section className={styles.editor}>
                        {!active && <div className={styles.empty}>{t('prompts.pickOne')}</div>}
                        {active && (
                            <>
                                <div className={styles.editorHead}>
                                    <div>
                                        <h2 className={styles.editorTitle}>{active.title}</h2>
                                        <p className={styles.editorDesc}>{active.description}</p>
                                        {(active.required_placeholders || []).length > 0 && (
                                            <p className={styles.placeholderHint}>
                                                <Info size={12} /> {t('prompts.requiredPlaceholders')}:{' '}
                                                {active.required_placeholders.map((ph) => (
                                                    <code key={ph} className={styles.ph}>{ph}</code>
                                                ))}
                                            </p>
                                        )}
                                    </div>
                                    <div className={styles.actions}>
                                        <button
                                            onClick={doReset}
                                            disabled={saving || !active.is_overridden}
                                            className={styles.btnSecondary}
                                            title={t('prompts.resetTitle')}
                                        >
                                            <RotateCcw size={14} /> {t('prompts.reset')}
                                        </button>
                                        <button
                                            onClick={doSave}
                                            disabled={saving || !isDirty}
                                            className={styles.btnPrimary}
                                        >
                                            <Save size={14} /> {saving ? t('prompts.saving') : t('prompts.save')}
                                        </button>
                                    </div>
                                </div>

                                {flash && (
                                    <div className={`${styles.flash} ${flash.type === 'error' ? styles.flashError : styles.flashOk}`}>
                                        {flash.type === 'error' ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
                                        {flash.text}
                                    </div>
                                )}

                                <textarea
                                    className={styles.textarea}
                                    value={draft}
                                    onChange={(e) => setDraft(e.target.value)}
                                    spellCheck={false}
                                    aria-label={t('prompts.editorLabel')}
                                />
                                <div className={styles.footer}>
                                    <span className={styles.counter}>{draft.length} / 20000</span>
                                    {isDirty && <span className={styles.dirty}>{t('prompts.unsaved')}</span>}
                                </div>
                            </>
                        )}
                    </section>
                </div>
            )}
        </main>
    )
}
