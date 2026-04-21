// Module-level streaming store.
//
// Purpose: keep SSE fetch loop + accumulated tokens ALIVE across React
// unmount/remount (e.g. when user navigates to another tab in the navbar and
// back). The store lives outside React so the fetch reader, abort controller,
// and in-flight assistant bubble survive remounts. Components subscribe via
// a listener and re-render on every mutation.
//
// No external deps. SSR-safe: all browser APIs are gated.

const SESSIONS_KEY = 'phobert_chat_sessions'
const PENDING_KEY = 'phobert_pending_chat'

const initialState = {
    sessionId: null,
    pendingMsgId: null,
    messages: [],          // full conversation incl. in-flight assistant bubble
    streaming: false,
    statusText: '',
    streamBuffer: '',
    startTs: 0,
    isLocal: false,
    selectedModel: '',
    finalData: null,
    error: null,
}

let state = { ...initialState }
const listeners = new Set()

// Internals kept out of the public snapshot (non-serializable / mutable refs).
let controller = null
let lastPersistTs = 0
let onFinalizeCb = null
let tRef = null

function notify() {
    // Shallow-clone so subscribers can reference-compare.
    const snap = { ...state }
    listeners.forEach(l => {
        try { l(snap) } catch {}
    })
}

function setState(patch) {
    state = { ...state, ...patch }
    notify()
}

export function getState() {
    return state
}

export function subscribe(listener) {
    listeners.add(listener)
    return () => listeners.delete(listener)
}

function now() {
    return new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function lsSet(key, val) {
    if (typeof window === 'undefined') return
    try { localStorage.setItem(key, JSON.stringify(val)) } catch {}
}

function lsDel(key) {
    if (typeof window === 'undefined') return
    try { localStorage.removeItem(key) } catch {}
}

function directSaveSession(sessionId, messages) {
    if (typeof window === 'undefined') return
    try {
        const sessions = JSON.parse(localStorage.getItem(SESSIONS_KEY) || '[]')
        const title = messages[0]?.content?.slice(0, 50) || 'New chat'
        const entry = { id: sessionId, title, time: new Date().toLocaleString('vi-VN'), messages, count: messages.length }
        const idx = sessions.findIndex(x => x.id === sessionId)
        if (idx >= 0) sessions[idx] = entry
        else sessions.unshift(entry)
        localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
    } catch {}
}

function persistPending(force = false) {
    const t0 = Date.now()
    if (!force && t0 - lastPersistTs < 400) return
    lastPersistTs = t0
    const { sessionId, messages } = state
    if (!sessionId) return
    const userMsg = messages.find(m => m.role === 'user')
    lsSet(PENDING_KEY, {
        sessionId,
        userMessage: userMsg?.content || '',
        currentMessages: messages,
        done: false,
    })
}

function translate(key, params) {
    if (typeof tRef === 'function') {
        const v = tRef(key, params)
        if (v && v !== key) return v
    }
    return ''
}

// Append token text to the in-flight assistant bubble.
function appendToken(token) {
    const { pendingMsgId } = state
    if (!pendingMsgId) return
    const buf = state.streamBuffer + token
    const messages = state.messages.map(m =>
        m._id === pendingMsgId ? { ...m, content: m.content + token } : m
    )
    state = { ...state, streamBuffer: buf, messages }
    notify()
    persistPending(false)
}

function updateStatus(text) {
    if (!text) return
    setState({ statusText: text })
}

function buildParseLine() {
    return function parseLine(line) {
        if (line.startsWith(': ')) {
            // heartbeat
            if (state.isLocal) {
                const elapsed = Math.round((Date.now() - state.startTs) / 1000)
                const txt = translate('chatbot.localProcessing', { elapsed })
                if (txt) updateStatus(txt)
            }
            return
        }
        if (!line.startsWith('data: ')) return
        try {
            const event = JSON.parse(line.slice(6))
            if (event.step === 'done' || event.step === 'error') {
                setState({ finalData: event.data })
            } else if (event.step === 'token' && event.token) {
                appendToken(event.token)
            } else {
                if (event.i18n_key) {
                    const translated = translate(`chatbot.${event.i18n_key}`, event.i18n_params || {})
                    const next = translated || event.message
                    if (next) updateStatus(next)
                } else if (event.message) {
                    updateStatus(event.message)
                }
            }
        } catch {}
    }
}

async function runStream(res, userText) {
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const parseLine = buildParseLine()

    while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) parseLine(line)
    }
    if (buffer.trim()) parseLine(buffer.trim())
}

function finalize({ aborted = false, err = null } = {}) {
    const { finalData, pendingMsgId, sessionId, selectedModel, streamBuffer, startTs } = state
    const elapsedSec = Math.round((Date.now() - startTs) / 1000)

    let finalMessages = state.messages
    if (pendingMsgId) {
        const pending = state.messages.find(m => m._id === pendingMsgId)
        const streamed = (pending?.content || streamBuffer || '').trim()

        if (err) {
            const content = err.message || 'Error'
            const errProvider = selectedModel.includes(':')
                ? 'ollama'
                : (selectedModel.endsWith('.gguf') ? 'local' : 'cloud')
            const finalContent = streamed ? `${streamed}\n\n_${content}_` : content
            const errorMsg = {
                role: 'assistant',
                content: finalContent,
                time: now(),
                elapsedSec,
                model: selectedModel,
                requestedModel: selectedModel,
                provider: errProvider,
                isError: true,
            }
            finalMessages = state.messages.map(m => m._id === pendingMsgId ? errorMsg : m)
        } else if (finalData) {
            const isError = !!finalData.error
            const finalResp = (finalData.response || '').trim()
            // Token-wins-over-finalData.response preservation (from round 2):
            // prefer already-streamed text when backend's final response is
            // empty or shorter than what we've already rendered.
            let botContent
            if (isError) {
                const errText = finalResp || translate('chatbot.modelUnavailable') || 'Model unavailable'
                botContent = streamed ? `${streamed}\n\n_${errText}_` : errText
            } else {
                botContent = finalResp.length >= streamed.length
                    ? (finalResp || translate('chatbot.noResponse') || streamed || '')
                    : (streamed || finalResp || '')
            }
            const botMsg = {
                role: 'assistant',
                content: botContent,
                time: now(),
                elapsedSec,
                model: isError ? selectedModel : finalData.model,
                requestedModel: selectedModel,
                provider: finalData.provider,
                searchUsed: finalData.search_used,
                ragUsed: finalData.rag_used,
                webSources: finalData.web_sources,
                sources: finalData.sources,
                isError,
            }
            finalMessages = state.messages.map(m => m._id === pendingMsgId ? botMsg : m)
        } else {
            // Stream ended with no done/error event — use accumulated tokens.
            const content = streamed || translate('chatbot.noResponseFromModel') || 'No response'
            const botMsg = {
                role: 'assistant',
                content,
                time: now(),
                elapsedSec,
                model: selectedModel,
                requestedModel: selectedModel,
                provider: 'unknown',
                isError: !streamed,
            }
            finalMessages = state.messages.map(m => m._id === pendingMsgId ? botMsg : m)
        }
    }

    // Persist to sessions and clear PENDING_KEY.
    if (sessionId && finalMessages.length > 0) {
        directSaveSession(sessionId, finalMessages)
    }
    lsDel(PENDING_KEY)

    state = {
        ...state,
        messages: finalMessages,
        streaming: false,
        statusText: '',
        pendingMsgId: null,
        error: err ? (err.message || 'error') : null,
    }
    notify()

    // Invoke caller finalize callback AFTER state commit so consumer can
    // merge into its local sessions/msgs if desired.
    const cb = onFinalizeCb
    onFinalizeCb = null
    controller = null
    if (typeof cb === 'function') {
        try { cb(finalMessages, state.finalData) } catch {}
    }
}

export async function startStream({
    sessionId,
    messages,       // includes the newly-added user message (no assistant yet)
    userText,
    selectedModel,
    isLocal,
    t,
    locale,         // reserved for future use
    onFinalize,
}) {
    if (state.streaming) {
        throw new Error('Stream already in progress')
    }

    tRef = t
    onFinalizeCb = onFinalize || null

    const pendingMsgId = `pending-${Date.now()}`
    const streamingMsg = { role: 'assistant', content: '', time: now(), _streaming: true, _id: pendingMsgId }
    const initialMessages = [...messages, streamingMsg]

    state = {
        ...initialState,
        sessionId,
        pendingMsgId,
        messages: initialMessages,
        streaming: true,
        statusText: (typeof t === 'function' ? t('chatbot.processing') : '') || 'Processing…',
        streamBuffer: '',
        startTs: Date.now(),
        isLocal: !!isLocal,
        selectedModel,
        finalData: null,
        error: null,
    }
    notify()
    persistPending(true)

    controller = new AbortController()
    const timeoutId = setTimeout(() => {
        try { controller?.abort() } catch {}
    }, 1800000)

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userText,
                session_id: sessionId,
                model: selectedModel,
                prefer_cloud: !isLocal,
            }),
            signal: controller.signal,
        })
        clearTimeout(timeoutId)

        const contentType = res.headers.get('content-type') || ''
        if (!res.ok) {
            if (contentType.includes('text/event-stream')) {
                const txt = await res.text().catch(() => '')
                const match = txt.match(/data:\s*(\{.*\})/)
                if (match) {
                    try {
                        const evt = JSON.parse(match[1])
                        throw new Error(evt?.data?.response || evt?.response || `HTTP ${res.status}`)
                    } catch (e) {
                        if (e.message !== `HTTP ${res.status}`) throw e
                    }
                }
                throw new Error(`HTTP ${res.status}`)
            }
            const errData = await res.json().catch(() => null)
            throw new Error(errData?.detail || errData?.response || `HTTP ${res.status}`)
        }

        if (contentType.includes('text/event-stream')) {
            await runStream(res, userText)
            finalize({})
        } else {
            // Non-SSE JSON fallback.
            const data = await res.json()
            const isError = !!data.error
            const botMsg = {
                role: 'assistant',
                content: isError
                    ? (data.response || translate('chatbot.modelUnavailable') || 'Model unavailable')
                    : (data.response || translate('chatbot.noResponse') || ''),
                time: now(),
                model: isError ? selectedModel : data.model,
                requestedModel: selectedModel,
                provider: data.provider,
                searchUsed: data.search_used,
                ragUsed: data.rag_used,
                webSources: data.web_sources,
                sources: data.sources,
                isError,
            }
            const finalMessages = state.messages.map(m => m._id === pendingMsgId ? botMsg : m)
            if (sessionId) directSaveSession(sessionId, finalMessages)
            lsDel(PENDING_KEY)
            state = {
                ...state,
                messages: finalMessages,
                streaming: false,
                statusText: '',
                pendingMsgId: null,
                finalData: data,
            }
            notify()
            const cb = onFinalizeCb
            onFinalizeCb = null
            controller = null
            if (typeof cb === 'function') {
                try { cb(finalMessages, data) } catch {}
            }
        }
    } catch (err) {
        clearTimeout(timeoutId)
        const aborted = err?.name === 'AbortError'
        let message
        if (aborted) {
            message = translate('chatbot.timeoutError') || 'Request aborted'
        } else if (err?.message?.includes('network') || err?.message?.includes('fetch')) {
            message = translate('chatbot.networkError') || 'Network error'
        } else {
            message = translate('chatbot.errorPrefix', { message: err?.message || 'unknown' })
                || (err?.message || 'Error')
        }
        finalize({ aborted, err: new Error(message) })
    }
}

export function abortStream() {
    try { controller?.abort() } catch {}
}

export function clearStream() {
    state = { ...initialState }
    notify()
}
