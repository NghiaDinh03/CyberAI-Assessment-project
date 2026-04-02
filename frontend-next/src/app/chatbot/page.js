'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './page.module.css'

const MAX_INPUT = 2000
const WARN_THRESHOLD = 1800

const CLOUD_MODELS = [
    { id: 'gemini-3-flash-preview', label: 'Gemini 3 Flash', provider: 'google', badge: 'Fast' },
    { id: 'gemini-3-pro-preview', label: 'Gemini 3 Pro', provider: 'google', badge: '' },
    { id: 'gpt-5', label: 'GPT-5', provider: 'openai', badge: 'Pro' },
    { id: 'gpt-5-mini', label: 'GPT-5 Mini', provider: 'openai', badge: 'Fast' },
    { id: 'gpt-5.2', label: 'GPT-5.2', provider: 'openai', badge: '' },
    { id: 'gpt-5.2-codex', label: 'GPT-5.2 Codex', provider: 'openai', badge: 'Code' },
    { id: 'gpt-5.4', label: 'GPT-5.4', provider: 'openai', badge: 'Fast' },
    { id: 'claude-opus-4.5', label: 'Claude Opus 4.5', provider: 'anthropic', badge: 'Pro' },
    { id: 'claude-opus-4.6', label: 'Claude Opus 4.6', provider: 'anthropic', badge: 'New' },
    { id: 'claude-sonnet-4', label: 'Claude Sonnet 4', provider: 'anthropic', badge: 'Fast' },
    { id: 'gpt-4.1', label: 'GPT-4.1', provider: 'openai', badge: '' },
    { id: 'gpt-4.1-mini', label: 'GPT-4.1 Mini', provider: 'openai', badge: 'Fast' },
    { id: 'localai', label: 'LocalAI (On-prem)', provider: 'local', badge: 'Local' },
]

const PROVIDER_COLORS = {
    openai: '#10a37f',
    google: '#4285f4',
    anthropic: '#d97706',
    local: '#8b5cf6',
}

const SUGGESTIONS = [
    { text: 'ISO 27001:2022 có gì mới so với 2013?' },
    { text: 'TCVN 11930 yêu cầu kỹ thuật gì?' },
    { text: 'Cách triển khai ISMS cho doanh nghiệp nhỏ' },
    { text: 'Các lỗ hổng bảo mật nguy hiểm nhất 2026' },
    { text: 'Tin tức an ninh mạng mới nhất' },
    { text: 'Tác giả của CyberAI là ai?' },
]

const SESSIONS_KEY = 'phobert_chat_sessions'
const ACTIVE_KEY = 'phobert_active_session'
const PENDING_KEY = 'phobert_pending_chat'
const MODEL_KEY = 'phobert_selected_model'

function uid() { return `s_${Date.now()}_${Math.random().toString(36).slice(2, 6)}` }
function now() { return new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false }) }

function lsGet(key, fallback) {
    if (typeof window === 'undefined') return fallback
    try { return JSON.parse(localStorage.getItem(key)) || fallback } catch { return fallback }
}

function lsSet(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)) } catch { }
}

function lsDel(key) {
    try { localStorage.removeItem(key) } catch { }
}

function directSaveSession(sessionId, messages) {
    try {
        const sessions = JSON.parse(localStorage.getItem(SESSIONS_KEY) || '[]')
        const title = messages[0]?.content?.slice(0, 50) || 'Chat mới'
        const entry = { id: sessionId, title, time: new Date().toLocaleString('vi-VN'), messages, count: messages.length }
        const idx = sessions.findIndex(x => x.id === sessionId)
        if (idx >= 0) sessions[idx] = entry
        else sessions.unshift(entry)
        localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
    } catch { }
}

export default function ChatbotPage() {
    const [sessions, setSessions] = useState([])
    const [activeId, setActiveId] = useState(null)
    const [msgs, setMsgs] = useState([])
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const [statusText, setStatusText] = useState('')
    const [sidebar, setSidebar] = useState(false)
    const [ready, setReady] = useState(false)
    const [selectedModel, setSelectedModel] = useState('gemini-3-flash-preview')
    const [modelDropdown, setModelDropdown] = useState(false)
    const [focusedModelIdx, setFocusedModelIdx] = useState(-1)
    const [aiStatus, setAiStatus] = useState(null)
    const [copiedMsgId, setCopiedMsgId] = useState(null)
    const isSubmitting = useRef(false)
    const mountedRef = useRef(true)
    const endRef = useRef(null)
    const inputRef = useRef(null)
    const modelBtnRef = useRef(null)
    const dropdownRef = useRef(null)

    useEffect(() => {
        let cancelled = false
        const fetchStatus = async () => {
            try {
                const res = await fetch('/api/system/ai-status')
                if (!res.ok || cancelled) return
                const data = await res.json()
                const missing = Object.entries(data?.model_guard || {}).filter(([, s]) => s !== 'present')
                const modeLabel = { 'local-only': 'Local-only', 'local-first': 'Local-first' }[data?.mode_label] || 'Cloud-first'
                let badgeTone = 'badgeHybrid'
                if (modeLabel !== 'Cloud-first') badgeTone = 'badgeLocal'
                if (missing.length > 0 || data?.localai?.status?.startsWith('unreachable')) badgeTone = 'badgeWarn'
                if (!cancelled) setAiStatus({ mode: modeLabel, badgeTone, missing, details: data })
            } catch { }
        }
        fetchStatus()
        const timer = setInterval(fetchStatus, 15000)
        return () => { cancelled = true; clearInterval(timer) }
    }, [])

    useEffect(() => {
        mountedRef.current = true
        const saved = lsGet(SESSIONS_KEY, [])
        const id = lsGet(ACTIVE_KEY, null)
        const savedModel = lsGet(MODEL_KEY, 'gemini-3-flash-preview')
        const validIds = CLOUD_MODELS.map(m => m.id)
        const resolvedModel = validIds.includes(savedModel) ? savedModel : 'gemini-3-flash-preview'
        setSelectedModel(resolvedModel)

        const pending = lsGet(PENDING_KEY, null)
        if (pending?.done) {
            directSaveSession(pending.sessionId, pending.finalMessages)
            lsDel(PENDING_KEY)
            const refreshed = lsGet(SESSIONS_KEY, [])
            setSessions(refreshed)
            if (id === pending.sessionId || !id) {
                setActiveId(pending.sessionId)
                setMsgs(pending.finalMessages)
                lsSet(ACTIVE_KEY, pending.sessionId)
            }
        } else if (pending && !pending.done) {
            setSessions(saved)
            setActiveId(pending.sessionId)
            setMsgs(pending.currentMessages || [])
            setSending(true)
            isSubmitting.current = true
            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), 600000)
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: pending.userMessage, session_id: pending.sessionId, model: savedModel, prefer_cloud: savedModel !== 'localai' }),
                signal: controller.signal
            })
                .then(r => r.json())
                .then(data => {
                    const content = data.error ? `Lỗi: ${data.response || data.error}` : (data.response || 'Không có phản hồi.')
                    const final = [...(pending.currentMessages || []), { role: 'assistant', content, time: now() }]
                    directSaveSession(pending.sessionId, final)
                    lsDel(PENDING_KEY)
                    if (mountedRef.current) { setMsgs(final); setSessions(lsGet(SESSIONS_KEY, [])); setSending(false) }
                })
                .catch(() => {
                    const final = [...(pending.currentMessages || []), { role: 'assistant', content: 'Đang chờ model phản hồi...', time: now() }]
                    directSaveSession(pending.sessionId, final)
                    lsDel(PENDING_KEY)
                    if (mountedRef.current) { setMsgs(final); setSessions(lsGet(SESSIONS_KEY, [])); setSending(false) }
                })
                .finally(() => {
                    clearTimeout(timeoutId)
                    isSubmitting.current = false
                })
        } else {
            setSessions(saved)
            if (id) {
                const s = saved.find(x => x.id === id)
                if (s) { setActiveId(id); setMsgs(s.messages || []) }
            }
        }
        setReady(true)
        return () => { mountedRef.current = false }
    }, [])

    useEffect(() => { if (ready) lsSet(SESSIONS_KEY, sessions) }, [sessions, ready])
    useEffect(() => { if (ready) lsSet(ACTIVE_KEY, activeId) }, [activeId, ready])
    // Improvement 5: scroll to bottom whenever message content changes (catches typewriter growth)
    useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

    const handleModelChange = (modelId) => {
        setSelectedModel(modelId)
        lsSet(MODEL_KEY, modelId)
        setModelDropdown(false)
        setFocusedModelIdx(-1)
        modelBtnRef.current?.focus()
    }

    const openDropdown = () => {
        const idx = CLOUD_MODELS.findIndex(m => m.id === selectedModel)
        setFocusedModelIdx(idx >= 0 ? idx : 0)
        setModelDropdown(true)
    }

    const handleModelKeyDown = (e) => {
        if (!modelDropdown) {
            if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
                e.preventDefault()
                openDropdown()
            }
            return
        }
        if (e.key === 'ArrowDown') {
            e.preventDefault()
            setFocusedModelIdx(prev => (prev + 1) % CLOUD_MODELS.length)
        } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setFocusedModelIdx(prev => (prev - 1 + CLOUD_MODELS.length) % CLOUD_MODELS.length)
        } else if (e.key === 'Enter') {
            e.preventDefault()
            if (focusedModelIdx >= 0) handleModelChange(CLOUD_MODELS[focusedModelIdx].id)
        } else if (e.key === 'Escape' || e.key === 'Tab') {
            e.preventDefault()
            setModelDropdown(false)
            setFocusedModelIdx(-1)
            modelBtnRef.current?.focus()
        }
    }

    const copyMessage = useCallback((msgId, text) => {
        navigator.clipboard.writeText(text).then(() => {
            setCopiedMsgId(msgId)
            setTimeout(() => setCopiedMsgId(null), 2000)
        }).catch(() => {})
    }, [])

    const updateSessions = useCallback((messages, id) => {
        setSessions(prev => {
            const entry = { id, title: messages[0]?.content?.slice(0, 50) || 'Chat mới', time: new Date().toLocaleString('vi-VN'), messages, count: messages.length }
            const i = prev.findIndex(x => x.id === id)
            if (i >= 0) { const u = [...prev]; u[i] = entry; return u }
            return [entry, ...prev]
        })
    }, [])

    const send = async (text) => {
        if (!text.trim()) return

        // Improvement 3: guard against double-submit race condition
        if (isSubmitting.current) return
        isSubmitting.current = true

        const id = activeId || uid()
        if (!activeId) setActiveId(id)
        const userMsg = { role: 'user', content: text.trim(), time: now() }
        const next = [...msgs, userMsg]
        setMsgs(next)
        setInput('')
        setSending(true)
        updateSessions(next, id)
        const isLocalAI = selectedModel === 'localai'
        lsSet(PENDING_KEY, { sessionId: id, userMessage: text.trim(), currentMessages: next, done: false })
        setStatusText('Đang xử lý...')
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 600000)
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text.trim(), session_id: id, model: isLocalAI ? '' : selectedModel, prefer_cloud: !isLocalAI }),
                signal: controller.signal
            })
            clearTimeout(timeoutId)
            if (!res.ok) {
                const errData = await res.json().catch(() => null)
                throw new Error(errData?.detail || errData?.response || `HTTP ${res.status}`)
            }
            const contentType = res.headers.get('content-type') || ''
            if (contentType.includes('text/event-stream')) {
                const reader = res.body.getReader()
                const decoder = new TextDecoder()
                let buffer = ''
                let finalData = null

                // Improvement 5: add a streaming placeholder message for typewriter effect
                const pendingMsgId = `pending-${Date.now()}`
                const streamingMsg = {
                    role: 'assistant',
                    content: '',
                    time: now(),
                    _streaming: true,
                    _id: pendingMsgId,
                }
                if (mountedRef.current) {
                    setMsgs(prev => [...prev, streamingMsg])
                }

                while (true) {
                    const { done, value } = await reader.read()
                    if (done) break
                    buffer += decoder.decode(value, { stream: true })
                    const lines = buffer.split('\n')
                    buffer = lines.pop() || ''
                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue
                        try {
                            const event = JSON.parse(line.slice(6))
                            if (event.step === 'done' || event.step === 'error') {
                                finalData = event.data
                            } else if (event.step === 'token' && event.token && mountedRef.current) {
                                // Improvement 5: append each token incrementally (typewriter)
                                setMsgs(prev => prev.map(m =>
                                    m._id === pendingMsgId
                                        ? { ...m, content: m.content + event.token }
                                        : m
                                ))
                            } else if (event.message && mountedRef.current) {
                                setStatusText(event.message)
                            }
                        } catch { }
                    }
                }

                if (finalData) {
                    const botContent = finalData.error
                        ? (finalData.response || 'Model không khả dụng.')
                        : (finalData.response || 'Không có phản hồi.')
                    const botMsg = {
                        role: 'assistant',
                        content: botContent,
                        time: now(),
                        model: finalData.model,
                        requestedModel: isLocalAI ? 'localai' : selectedModel,
                        provider: finalData.provider,
                        searchUsed: finalData.search_used,
                        ragUsed: finalData.rag_used,
                        webSources: finalData.web_sources,
                        sources: finalData.sources,
                        // _streaming and _id intentionally absent — finalised message
                    }
                    // Replace the streaming placeholder with the complete finalised message
                    const final = [
                        ...next,
                        botMsg,
                    ]
                    directSaveSession(id, final)
                    if (mountedRef.current) {
                        setMsgs(final)
                        updateSessions(final, id)
                        lsDel(PENDING_KEY)
                    }
                } else {
                    throw new Error('Stream ended without response')
                }
            } else {
                const data = await res.json()
                const botMsg = {
                    role: 'assistant',
                    content: data.error ? (data.response || 'Model không khả dụng.') : (data.response || 'Không có phản hồi.'),
                    time: now(),
                    model: data.model,
                    requestedModel: isLocalAI ? 'localai' : selectedModel,
                    provider: data.provider,
                    searchUsed: data.search_used,
                    ragUsed: data.rag_used,
                    webSources: data.web_sources,
                    sources: data.sources,
                }
                const final = [...next, botMsg]
                directSaveSession(id, final)
                if (mountedRef.current) { setMsgs(final); updateSessions(final, id); lsDel(PENDING_KEY) }
            }
        } catch (err) {
            clearTimeout(timeoutId)
            if (mountedRef.current) {
                const content = err?.name === 'AbortError'
                    ? 'Request timeout (5 phút). Model đang quá tải.'
                    : `Lỗi kết nối: ${err.message}`
                // Remove any in-flight streaming placeholder before appending error
                const final = [...next, { role: 'assistant', content, time: now() }]
                directSaveSession(id, final)
                setMsgs(final)
                updateSessions(final, id)
                lsDel(PENDING_KEY)
            }
        } finally {
            // Improvement 3: always reset the submission guard in finally
            isSubmitting.current = false
            if (mountedRef.current) { setSending(false); setStatusText('') }
        }
    }

    const newChat = () => { setActiveId(null); setMsgs([]); setSidebar(false); setTimeout(() => inputRef.current?.focus(), 100) }
    const openSession = (s) => { setActiveId(s.id); setMsgs(s.messages || []); setSidebar(false) }
    const removeSession = (e, id) => { e.stopPropagation(); setSessions(prev => prev.filter(x => x.id !== id)); if (activeId === id) { setActiveId(null); setMsgs([]) } }
    const clearAllSessions = () => {
        setSessions([])
        setActiveId(null)
        setMsgs([])
        lsDel(SESSIONS_KEY)
        lsDel(ACTIVE_KEY)
    }

    const activeModelInfo = CLOUD_MODELS.find(m => m.id === selectedModel) || CLOUD_MODELS[0]

    return (
        <div className={styles.layout} onClick={() => modelDropdown && setModelDropdown(false)}>
            {sidebar && <div className={styles.overlay} onClick={() => setSidebar(false)} />}

            <aside className={`${styles.sidebar} ${sidebar ? styles.sidebarOpen : ''}`}>
                <div className={styles.sidebarHeader}>
                    <h3>History</h3>
                    <div style={{ display: 'flex', gap: 4 }}>
                        {sessions.length > 0 && (
                            <button
                                className={styles.sidebarClose}
                                onClick={clearAllSessions}
                                title="Clear all history"
                                style={{ fontSize: '0.7rem', padding: '4px 8px', borderRadius: 6, background: 'rgba(248,113,113,0.09)', color: 'var(--accent-red)', border: '1px solid rgba(248,113,113,0.2)' }}
                            >
                                Clear all
                            </button>
                        )}
                        <button className={styles.sidebarClose} onClick={() => setSidebar(false)}>✕</button>
                    </div>
                </div>
                <button className={styles.newBtn} onClick={newChat}>New Chat</button>
                <div className={styles.sessionList}>
                    {sessions.length === 0 && <p className={styles.empty}>No conversations yet</p>}
                    {sessions.map(s => (
                        <div
                            key={s.id}
                            className={`${styles.sessionItem} ${s.id === activeId ? styles.sessionActive : ''}`}
                            onClick={() => openSession(s)}
                        >
                            <div className={styles.sessionInfo}>
                                <div className={styles.sessionTitle}>{s.title}</div>
                                <div className={styles.sessionMeta}>{s.count} msgs · {s.time}</div>
                            </div>
                            <button className={styles.sessionDel} onClick={e => removeSession(e, s.id)}>✕</button>
                        </div>
                    ))}
                </div>
            </aside>

            <div className={styles.main}>
                <div className={styles.topBar}>
                    <div className={styles.topLeft}>
                        <button className={styles.menuBtn} onClick={() => setSidebar(true)}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h18M3 6h18M3 18h18" /></svg>
                        </button>
                        <div>
                            <h1 className={styles.pageTitle}>CyberAI Assistant</h1>
                            <p className={styles.pageSub}>ISO 27001 · TCVN 11930 · RAG ChromaDB · Web Search</p>
                            {aiStatus && (
                                <div className={styles.aiBadgeRow}>
                                    <span className={`${styles.aiBadge} ${styles[aiStatus.badgeTone || 'badgeHybrid']}`}>
                                        {aiStatus.mode}
                                    </span>
                                    {aiStatus.missing?.length > 0 && (
                                        <span className={styles.aiBadgeNote}>LocalAI: missing GGUF model</span>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                    <div className={styles.topRight}>
                        <button className={styles.topBtn} onClick={newChat}>New</button>
                        <button className={styles.topBtn} onClick={() => setSidebar(true)}>History ({sessions.length})</button>
                    </div>
                </div>

                <div className={styles.chatArea}>
                    {msgs.length === 0 && !sending ? (
                        <div className={styles.welcome}>
                            <div className={styles.welcomeHeading}>
                                <div className={styles.emptyIcon}>💬</div>
                                <h2 className={styles.welcomeTitle}>Bắt đầu cuộc trò chuyện</h2>
                                <p className={styles.welcomeSub}>Hỏi bất kỳ câu hỏi nào về ISO 27001, bảo mật thông tin, hoặc compliance.</p>
                            </div>
                            <div className={styles.chips}>
                                {[
                                    'Kiểm soát truy cập là gì?',
                                    'Giải thích Annex A',
                                    'ISO 27001 vs SOC 2',
                                    ...SUGGESTIONS.slice(0, 3).map(s => s.text)
                                ].map((text, i) => (
                                    <button key={i} className={styles.chip} onClick={() => setInput(text)}>
                                        {text}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className={styles.msgList}>
                            {msgs.map((m, i) => {
                                const msgKey = m._id || i
                                return (
                                <div key={msgKey} className={`${styles.msg} ${m.role === 'user' ? styles.msgUser : styles.msgBot}`}>
                                    {m.role === 'assistant' && <div className={styles.avatar}>AI</div>}
                                    <div className={`${styles.bubble} ${m.role === 'user' ? styles.bubbleUser : styles.bubbleBot}`}>
                                        {m.role === 'assistant' ? (
                                            <div className={`${styles.md} ${m._streaming ? styles.streamingCursor : ''}`}>
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || ' '}</ReactMarkdown>
                                            </div>
                                        ) : m.content}
                                        {m.role === 'assistant' && !m._streaming && (
                                            <button
                                                className={styles.copyBtn}
                                                onClick={() => copyMessage(msgKey, m.content)}
                                                title="Copy message"
                                                aria-label="Copy message to clipboard"
                                            >
                                                {copiedMsgId === msgKey ? '✓ Copied!' : '📋 Copy'}
                                            </button>
                                        )}
                                        {!m._streaming && (
                                            <div className={styles.msgMeta}>
                                                {m.ragUsed && <span className={styles.badge}>RAG</span>}
                                                {m.searchUsed && <span className={styles.badge}>Web</span>}
                                                {m.model && (
                                                    <span className={styles.badge} title={m.requestedModel && m.requestedModel !== m.model ? `Requested: ${m.requestedModel} → Fallback: ${m.model}` : m.model}>
                                                        {m.model}{m.requestedModel && m.requestedModel !== m.model ? ' ↩' : ''}
                                                    </span>
                                                )}
                                                <span className={styles.time}>{m.time}</span>
                                            </div>
                                        )}
                                        {!m._streaming && m.ragUsed && m.sources?.length > 0 && (
                                            <div className={styles.sourcesList}>
                                                {m.sources.slice(0, 4).map((src, idx) => (
                                                    <a key={idx} href={src.startsWith('http') ? src : '#'} target="_blank" rel="noreferrer" className={styles.sourceItem}>
                                                        {src}
                                                    </a>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    {m.role === 'user' && <div className={styles.avatarUser}>You</div>}
                                </div>
                                )
                            })}
                            {sending && !msgs.some(m => m._streaming) && (
                                <div className={styles.typingWrap}>
                                    <div className={styles.typingDots}><span /><span /><span /></div>
                                    {statusText && <span className={styles.statusText}>{statusText}</span>}
                                </div>
                            )}
                            {sending && statusText && msgs.some(m => m._streaming) && (
                                <div className={styles.typingWrap}>
                                    <span className={styles.statusText}>{statusText}</span>
                                </div>
                            )}
                            <div ref={endRef} />
                        </div>
                    )}
                </div>

                <div className={styles.inputFooter}>
                    <div className={styles.inputToolbar} onClick={e => e.stopPropagation()}>
                        <div className={styles.modelPicker}>
                            <button
                                ref={modelBtnRef}
                                type="button"
                                className={styles.modelBtn}
                                onClick={() => modelDropdown ? (setModelDropdown(false), setFocusedModelIdx(-1)) : openDropdown()}
                                onKeyDown={handleModelKeyDown}
                                style={{ '--provider-color': PROVIDER_COLORS[activeModelInfo.provider] }}
                                aria-haspopup="listbox"
                                aria-expanded={modelDropdown}
                                aria-label={`Selected model: ${activeModelInfo.label}`}
                            >
                                <span className={styles.modelDot} style={{ background: PROVIDER_COLORS[activeModelInfo.provider] }} />
                                <span className={styles.modelBtnLabel}>{activeModelInfo.label}</span>
                                <span className={styles.modelChevron}>{modelDropdown ? '▴' : '▾'}</span>
                            </button>
                            {modelDropdown && (
                                <div
                                    ref={dropdownRef}
                                    className={styles.modelDropdown}
                                    role="listbox"
                                    aria-label="Select AI Model"
                                    aria-activedescendant={focusedModelIdx >= 0 ? `model-opt-${CLOUD_MODELS[focusedModelIdx].id}` : undefined}
                                    onKeyDown={handleModelKeyDown}
                                >
                                    <div className={styles.modelDropdownTitle}>Select AI Model</div>
                                    {CLOUD_MODELS.map((m, idx) => (
                                        <button
                                            key={m.id}
                                            id={`model-opt-${m.id}`}
                                            type="button"
                                            role="option"
                                            aria-selected={selectedModel === m.id}
                                            className={`${styles.modelOption} ${selectedModel === m.id ? styles.modelOptionActive : ''} ${focusedModelIdx === idx ? styles.modelOptionFocused : ''}`}
                                            onClick={() => handleModelChange(m.id)}
                                            onMouseEnter={() => setFocusedModelIdx(idx)}
                                        >
                                            <span className={styles.modelDot} style={{ background: PROVIDER_COLORS[m.provider] }} />
                                            <span className={styles.modelOptionName}>{m.label}</span>
                                            {m.badge && <span className={styles.modelBadge}>{m.badge}</span>}
                                            <span className={styles.modelProviderTag} style={{ color: PROVIDER_COLORS[m.provider] }}>{m.provider}</span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                        <span className={styles.inputHint}>Enter to send · Shift+Enter for newline</span>
                    </div>
                    <form className={styles.inputBar} onSubmit={e => { e.preventDefault(); send(input) }}>
                        <div className={styles.inputWrap}>
                            <input
                                ref={inputRef}
                                value={input}
                                onChange={e => setInput(e.target.value.slice(0, MAX_INPUT))}
                                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input) } }}
                                placeholder="Ask about ISO 27001, TCVN, cybersecurity..."
                                disabled={sending}
                                maxLength={MAX_INPUT}
                                autoFocus
                            />
                            <span className={`${styles.charCounter} ${input.length >= WARN_THRESHOLD ? styles.charCounterWarn : ''}`}>
                                {input.length}/{MAX_INPUT}
                            </span>
                        </div>
                        <button type="submit" disabled={!input.trim() || sending}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}
