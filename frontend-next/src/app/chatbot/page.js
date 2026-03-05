'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styles from './page.module.css'

const SUGGESTIONS = [
    { icon: '📋', text: 'ISO 27001 là gì?' },
    { icon: '🔍', text: 'TCVN 14423 quy định gì?' },
    { icon: '💡', text: 'Làm sao triển khai ISMS?' },
    { icon: '✅', text: 'Cách đánh giá rủi ro ATTT' },
    { icon: '🌐', text: 'Tin tức bảo mật mới nhất' },
    { icon: '🛡️', text: 'Xu hướng an ninh mạng 2026' }
]

const SESSIONS_KEY = 'phobert_chat_sessions'
const ACTIVE_KEY = 'phobert_active_session'
const PENDING_KEY = 'phobert_pending_chat'

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
        const entry = {
            id: sessionId,
            title,
            time: new Date().toLocaleString('vi-VN'),
            messages,
            count: messages.length
        }
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
    const mountedRef = useRef(true)
    const endRef = useRef(null)
    const inputRef = useRef(null)

    useEffect(() => {
        mountedRef.current = true

        const saved = lsGet(SESSIONS_KEY, [])
        const id = lsGet(ACTIVE_KEY, null)

        const pending = lsGet(PENDING_KEY, null)
        if (pending && pending.done) {
            directSaveSession(pending.sessionId, pending.finalMessages)
            lsDel(PENDING_KEY)

            const refreshed = lsGet(SESSIONS_KEY, [])
            setSessions(refreshed)

            if (id === pending.sessionId || !id) {
                setActiveId(pending.sessionId)
                setMsgs(pending.finalMessages)
                lsSet(ACTIVE_KEY, pending.sessionId)
            } else {
                setSessions(refreshed)
                if (id) {
                    const s = refreshed.find(x => x.id === id)
                    if (s) { setActiveId(id); setMsgs(s.messages || []) }
                }
            }
        } else if (pending && !pending.done) {
            setSessions(saved)
            setActiveId(pending.sessionId)
            setMsgs(pending.currentMessages || [])
            setSending(true)

            const controller = new AbortController()
            const timeoutId = setTimeout(() => controller.abort(), 600000)

            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: pending.userMessage, session_id: pending.sessionId }),
                signal: controller.signal
            })
                .then(r => r.json())
                .then(data => {
                    const content = data.error ? `Lỗi: ${data.error}` : (data.response || 'Không có phản hồi.')
                    const botMsg = { role: 'assistant', content, time: now() }
                    const final = [...(pending.currentMessages || []), botMsg]

                    directSaveSession(pending.sessionId, final)
                    lsDel(PENDING_KEY)

                    if (mountedRef.current) {
                        setMsgs(final)
                        setSessions(lsGet(SESSIONS_KEY, []))
                        setSending(false)
                    }
                })
                .catch((err) => {
                    const isTimeout = err?.name === 'AbortError'
                    const errContent = isTimeout
                        ? 'Request timeout (5 phút). Model đang quá tải, thử lại sau.'
                        : 'Đang chờ model phản hồi... Quay lại sau để xem kết quả.'
                    const botMsg = { role: 'assistant', content: errContent, time: now() }
                    const final = [...(pending.currentMessages || []), botMsg]
                    directSaveSession(pending.sessionId, final)
                    lsDel(PENDING_KEY)
                    if (mountedRef.current) {
                        setMsgs(final)
                        setSessions(lsGet(SESSIONS_KEY, []))
                        setSending(false)
                    }
                })
                .finally(() => clearTimeout(timeoutId))
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
    useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

    const updateSessions = useCallback((messages, id) => {
        setSessions(prev => {
            const entry = {
                id,
                title: messages[0]?.content?.slice(0, 50) || 'Chat mới',
                time: new Date().toLocaleString('vi-VN'),
                messages,
                count: messages.length
            }
            const i = prev.findIndex(x => x.id === id)
            if (i >= 0) { const u = [...prev]; u[i] = entry; return u }
            return [entry, ...prev]
        })
    }, [])

    const send = async (text) => {
        if (!text.trim() || sending) return
        const id = activeId || uid()
        if (!activeId) setActiveId(id)

        const userMsg = { role: 'user', content: text.trim(), time: now() }
        const next = [...msgs, userMsg]
        setMsgs(next)
        setInput('')
        setSending(true)
        updateSessions(next, id)

        lsSet(PENDING_KEY, {
            sessionId: id,
            userMessage: text.trim(),
            currentMessages: next,
            done: false
        })

        setStatusText('Đang xử lý...')

        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 600000)

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text.trim(), session_id: id }),
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
                            } else if (event.message && mountedRef.current) {
                                setStatusText(event.message)
                            }
                        } catch { }
                    }
                }

                if (finalData) {
                    const botMsg = {
                        role: 'assistant',
                        content: finalData.error
                            ? (finalData.response || 'Model đang không khả dụng.')
                            : (finalData.response || 'Không có phản hồi.'),
                        time: now(),
                        searchUsed: finalData.search_used,
                        ragUsed: finalData.rag_used,
                        webSources: finalData.web_sources
                    }
                    const final = [...next, botMsg]
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
                    content: data.error ? (data.response || 'Model đang không khả dụng.') : (data.response || 'Không có phản hồi.'),
                    time: now(),
                    searchUsed: data.search_used,
                    ragUsed: data.rag_used,
                    webSources: data.web_sources
                }
                const final = [...next, botMsg]
                directSaveSession(id, final)
                if (mountedRef.current) {
                    setMsgs(final)
                    updateSessions(final, id)
                    lsDel(PENDING_KEY)
                }
            }

        } catch (err) {
            clearTimeout(timeoutId)
            if (mountedRef.current) {
                const isAbort = err?.name === 'AbortError'
                const errContent = isAbort
                    ? 'Request timeout (5 phút). Model đang quá tải.'
                    : `Lỗi kết nối: ${err.message}`
                const errMsg = { role: 'assistant', content: errContent, time: now() }
                const final = [...next, errMsg]
                directSaveSession(id, final)
                setMsgs(final)
                updateSessions(final, id)
                lsDel(PENDING_KEY)
            }
        } finally {
            if (mountedRef.current) {
                setSending(false)
                setStatusText('')
            }
        }
    }

    const newChat = () => {
        setActiveId(null)
        setMsgs([])
        setSidebar(false)
        setTimeout(() => inputRef.current?.focus(), 100)
    }

    const openSession = (s) => {
        setActiveId(s.id)
        setMsgs(s.messages || [])
        setSidebar(false)
    }

    const removeSession = (e, id) => {
        e.stopPropagation()
        setSessions(prev => prev.filter(x => x.id !== id))
        if (activeId === id) { setActiveId(null); setMsgs([]) }
    }

    return (
        <div className={styles.layout}>
            {sidebar && <div className={styles.overlay} onClick={() => setSidebar(false)} />}

            <aside className={`${styles.sidebar} ${sidebar ? styles.sidebarOpen : ''}`}>
                <div className={styles.sidebarHeader}>
                    <h3>Lịch sử</h3>
                    <button className={styles.sidebarClose} onClick={() => setSidebar(false)}>✕</button>
                </div>
                <button className={styles.newBtn} onClick={newChat}>＋ Chat mới</button>
                <div className={styles.sessionList}>
                    {sessions.length === 0 && <p className={styles.empty}>Chưa có cuộc hội thoại nào</p>}
                    {sessions.map(s => (
                        <div key={s.id} className={`${styles.sessionItem} ${s.id === activeId ? styles.sessionActive : ''}`} onClick={() => openSession(s)}>
                            <div className={styles.sessionInfo}>
                                <div className={styles.sessionTitle}>{s.title}</div>
                                <div className={styles.sessionMeta}>{s.count} tin · {s.time}</div>
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
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h18M3 6h18M3 18h18" /></svg>
                        </button>
                        <div>
                            <h1 className={styles.pageTitle}>AI Chat</h1>
                            <p className={styles.pageSub}>Trợ lý ISO 27001 · TCVN 14423</p>
                        </div>
                    </div>
                    <div className={styles.topRight}>
                        <button className={styles.topBtn} onClick={newChat}>＋ Mới</button>
                        <button className={styles.topBtn} onClick={() => setSidebar(true)}>📚 {sessions.length}</button>
                    </div>
                </div>

                <div className={styles.chatArea}>
                    {msgs.length === 0 && !sending ? (
                        <div className={styles.welcome}>
                            <div className={styles.welcomeIcon}>💬</div>
                            <h2 className={styles.welcomeTitle}>Xin chào!</h2>
                            <p className={styles.welcomeSub}>Trợ lý AI hỗ trợ ISO 27001, TCVN 14423 và tìm kiếm thông tin bảo mật</p>
                            <div className={styles.chips}>
                                {SUGGESTIONS.map((s, i) => (
                                    <button key={i} className={styles.chip} onClick={() => send(s.text)}>
                                        <span>{s.icon}</span> {s.text}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className={styles.msgList}>
                            {msgs.map((m, i) => (
                                <div key={i} className={`${styles.msg} ${m.role === 'user' ? styles.msgUser : styles.msgBot}`}>
                                    {m.role === 'assistant' && <div className={styles.avatar}>🤖</div>}
                                    <div className={`${styles.bubble} ${m.role === 'user' ? styles.bubbleUser : styles.bubbleBot}`}>
                                        {m.role === 'assistant' ? (
                                            <div className={styles.md}><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown></div>
                                        ) : m.content}
                                        {m.searchUsed && <span className={styles.badge}>🌐 Web Search</span>}
                                        {m.ragUsed && <span className={styles.badge}>📚 RAG</span>}
                                        <span className={styles.time}>{m.time}</span>
                                    </div>
                                    {m.role === 'user' && <div className={styles.avatarUser}>👤</div>}
                                </div>
                            ))}
                            {sending && (
                                <div className={styles.typingWrap}>
                                    <div className={styles.typingDots}><span /><span /><span /></div>
                                    {statusText && <span className={styles.statusText}>{statusText}</span>}
                                </div>
                            )}
                            <div ref={endRef} />
                        </div>
                    )}
                </div>

                <form className={styles.inputBar} onSubmit={e => { e.preventDefault(); send(input) }}>
                    <input
                        ref={inputRef}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        placeholder="Nhập câu hỏi..."
                        disabled={sending}
                        autoFocus
                    />
                    <button type="submit" disabled={!input.trim() || sending}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                    </button>
                </form>
            </div>
        </div>
    )
}
