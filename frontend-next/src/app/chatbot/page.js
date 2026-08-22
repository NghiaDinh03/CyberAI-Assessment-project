'use client'

export const dynamic = 'force-dynamic'

import { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
    Send, Copy, Plus, Trash2, ChevronDown, Bot, User, Loader2, ArrowDown, Check, Download, X, Pencil,
    AlertTriangle, RefreshCw, Zap, Sparkles, RotateCcw
} from 'lucide-react'
import { useTranslation } from '@/components/LanguageProvider'
import { useAuth } from '@/contexts/AuthContext'
import styles from './page.module.css'
import * as streamStore from './streamStore'
import { useStreamStore } from './useStreamStore'

const MAX_INPUT_LOCAL = 5000
const MAX_INPUT_CLOUD = 15000
const WARN_OFFSET = 200

const CLOUD_MODELS = [
    { id: 'gemma4:latest',           label: 'Gemma 4 (Local)',          provider: 'ollama',    badge: 'Primary · Local' },
    { id: 'gemini-2.0-flash-free',   label: 'Gemini 2.0 Flash (Free)', provider: 'google',    badge: 'Cloud Fallback' },
]

// Ollama models populated dynamically from backend catalog
const OLLAMA_ID_MAP = {}

const LOCAL_MODEL_IDS = new Set(
    CLOUD_MODELS.filter(m => m.provider === 'local' || m.provider === 'ollama').map(m => m.id)
)

// Map raw model IDs to friendly labels for display
const MODEL_LABEL_MAP = Object.fromEntries(CLOUD_MODELS.map(m => [m.id, m.label]))
function getModelLabel(modelId) {
    if (!modelId) return ''
    return MODEL_LABEL_MAP[modelId] || modelId.replace(/-Q\d.*\.gguf$/i, '').replace(/-/g, ' ')
}

const PROVIDER_COLORS = {
    openai: '#10a37f',
    google: '#4285f4',
    anthropic: '#d97706',
    local: '#8b5cf6',
    ollama: '#ff6b35',
}

const PROVIDER_LABEL = {
    openai: 'OpenAI',
    google: 'Google',
    anthropic: 'Anthropic',
    local: 'LocalAI',
    ollama: 'Ollama',
}

const SESSIONS_KEY = 'cyberai_chat_sessions'
const ACTIVE_KEY = 'cyberai_active_session'
const PENDING_KEY = 'cyberai_pending_chat'
const MODEL_KEY = 'cyberai_selected_model'

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
        const title = messages[0]?.content?.slice(0, 50) || 'New chat'
        const entry = { id: sessionId, title, time: new Date().toLocaleString('vi-VN'), messages, count: messages.length }
        const idx = sessions.findIndex(x => x.id === sessionId)
        if (idx >= 0) sessions[idx] = entry
        else sessions.unshift(entry)
        localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
    } catch { }
}

function decodeHexByteTokens(str) {
    if (!str || typeof str !== 'string') return str || ''
    return str.replace(/(?:<0x[0-9A-Fa-f]{2}>)+/g, (match) => {
        const hexes = match.match(/<0x([0-9A-Fa-f]{2})>/g)
        if (!hexes) return ''
        try {
            const bytes = new Uint8Array(hexes.map(h => parseInt(h.replace(/<0x|>/g, ''), 16)))
            return new TextDecoder('utf-8').decode(bytes)
        } catch {
            return ''
        }
    }).replace(/<0x[0-9A-Fa-f]{2}>/g, '')
}

function normalizeMathAndArrows(str) {
    if (!str || typeof str !== 'string') return str || ''
    return str
        // LaTeX Arrows & Implications
        .replace(/\$(?:\\rightarrow|\\to|\\longrightarrow)\$/gi, '→')
        .replace(/\\(?:rightarrow|to|longrightarrow)\b/gi, '→')
        .replace(/\$(?:\\leftarrow|\\gets|\\longleftarrow)\$/gi, '←')
        .replace(/\\(?:leftarrow|gets|longleftarrow)\b/gi, '←')
        .replace(/\$(?:\\Rightarrow|\\implies|\\Longrightarrow)\$/gi, '⇒')
        .replace(/\\(?:Rightarrow|implies|Longrightarrow)\b/gi, '⇒')
        .replace(/\$(?:\\Leftarrow|\\Longleftarrow)\$/gi, '⇐')
        .replace(/\\(?:Leftarrow|Longleftarrow)\b/gi, '⇐')
        .replace(/\$(?:\\Leftrightarrow|\\iff|\\Longleftrightarrow)\$/gi, '⇔')
        .replace(/\\(?:Leftrightarrow|iff|Longleftrightarrow)\b/gi, '⇔')
        .replace(/\$(?:\\leftrightarrow)\$/gi, '↔')
        .replace(/\\(?:leftrightarrow)\b/gi, '↔')
        // LaTeX Math comparisons & operators
        .replace(/\$(?:\\approx|\\approxeq)\$/gi, '≈')
        .replace(/\\(?:approx|approxeq)\b/gi, '≈')
        .replace(/\$(?:\\neq|\\ne)\$/gi, '≠')
        .replace(/\\(?:neq|ne)\b/gi, '≠')
        .replace(/\$(?:\\le|\\leq)\$/gi, '≤')
        .replace(/\\(?:le|leq)\b/gi, '≤')
        .replace(/\$(?:\\ge|\\geq)\$/gi, '≥')
        .replace(/\\(?:ge|geq)\b/gi, '≥')
        .replace(/\$(?:\\pm)\$/gi, '±')
        .replace(/\\(?:pm)\b/gi, '±')
        .replace(/\$(?:\\times)\$/gi, '×')
        .replace(/\\(?:times)\b/gi, '×')
        .replace(/\$(?:\\div)\$/gi, '÷')
        .replace(/\\(?:div)\b/gi, '÷')
        .replace(/\$(?:\\cdot)\$/gi, '·')
        .replace(/\\(?:cdot)\b/gi, '·')
        .replace(/\$(?:\\bullet)\$/gi, '•')
        .replace(/\\(?:bullet)\b/gi, '•')
        .replace(/\$(?:\\dots|\\cdots|\\ldots)\$/gi, '...')
        .replace(/\\(?:dots|cdots|ldots)\b/gi, '...')
        .replace(/\$(?:\\infty)\$/gi, '∞')
        .replace(/\\(?:infty)\b/gi, '∞')
        .replace(/\$(?:\\checkmark)\$/gi, '✓')
        .replace(/\\(?:checkmark)\b/gi, '✓')
        .replace(/\$(?:\\sim)\$/gi, '~')
        // Strip stray inline $ wrapping text/arrow chains like `$Reconnaissance → Initial Access$`
        .replace(/\$([^\$\n]+)\$/g, '$1')
        // TL;DR normalization
        .replace(/\b(?:TL;DR|TLDR)\s*[:\-]\s*/gi, '**Tóm lại:** ')
}

function cleanAndFormatMarkdown(text) {
    if (!text || typeof text !== 'string') return text || ''
    
    // First pass: decode hex bytes and normalize LaTeX math/arrows
    let cleaned = normalizeMathAndArrows(decodeHexByteTokens(text))

    // If text is SOC log, format into structured report without emoji clutter
    const hasLogMarkers = cleaned.includes('Nhận định:')
        || cleaned.includes('Event ID:')
        || cleaned.includes('Process Name:')
        || cleaned.includes('Command Line:')
        || (cleaned.includes('Technique:') && cleaned.includes('Mức độ:'))
        || (cleaned.includes('MD5:') && cleaned.includes('SHA256:'))
        || cleaned.includes('Khuyến nghị:')

    if (!hasLogMarkers || cleaned.includes('### Thông tin sự kiện')) {
        return cleaned
    }

    const lines = cleaned.split('\n')
    const formatted = []
    let hasEventHeader = false
    let hasVerdictHeader = false
    let hasMitreHeader = false
    let hasRecHeader = false

    for (let rawLine of lines) {
        let line = rawLine.trim()
        if (!line) continue
        if (line.startsWith('###')) {
            formatted.push(`\n${line}`)
            continue
        }
        const lower = line.toLowerCase()
        if (!hasEventHeader && (
            lower.startsWith('event id:') || lower.startsWith('timestamp:') || lower.startsWith('host:') ||
            lower.startsWith('user:') || lower.startsWith('process name:') || lower.startsWith('source:') ||
            lower.startsWith('command line:') || lower.startsWith('md5:') || lower.startsWith('sha256:')
        )) {
            formatted.push('### Thông tin sự kiện')
            hasEventHeader = true
        } else if (!hasVerdictHeader && lower.startsWith('nhận định:')) {
            formatted.push('\n### Nhận định & Đánh giá')
            hasVerdictHeader = true
        } else if (!hasMitreHeader && (lower.startsWith('technique:') || lower.startsWith('tactic:') || lower.startsWith('mitre:'))) {
            formatted.push('\n### Kỹ thuật tấn công (MITRE ATT&CK)')
            hasMitreHeader = true
        } else if (!hasRecHeader && (lower.startsWith('khuyến nghị:') || lower.startsWith('log cần kiểm tra:'))) {
            formatted.push('\n### Khuyến nghị xử lý')
            hasRecHeader = true
        }

        const match = line.match(/^([A-Za-z0-9À-ỹ\s\(\)\/_\-]+?):\s*(.+)$/)
        if (match && !line.startsWith('- **') && !line.startsWith('###')) {
            const label = match[1].trim()
            const val = match[2].trim()
            formatted.push(`- **${label}**: ${val}`)
        } else {
            formatted.push(line)
        }
    }
    return formatted.join('\n')
}

const MessageBubble = memo(function MessageBubble({
    m,
    index,
    msgKey,
    isLastStreaming,
    statusText,
    copiedMsgId,
    onCopy,
    onSaveEdit,
    onRegenerate,
    onSwitchModel,
    onNewChat,
    prevUserPrompt,
    t
}) {
    const isBot = m.role === 'assistant'
    const isStreaming = !!m._streaming
    const isCopied = copiedMsgId === msgKey
    const content = typeof m.content === 'string' ? m.content : (m.content ? JSON.stringify(m.content) : '')
    const displayContent = useMemo(() => {
        return isBot ? cleanAndFormatMarkdown(content) : content
    }, [isBot, content])
    const charCount = content.length
    const modelKey = m.model || m.requestedModel || ''
    const providerColor = m.provider && PROVIDER_COLORS[m.provider]
        ? PROVIDER_COLORS[m.provider]
        : (modelKey.includes('gemma') || modelKey.endsWith('.gguf') ? PROVIDER_COLORS.ollama : PROVIDER_COLORS.openai)

    const [isEditing, setIsEditing] = useState(false)
    const [editText, setEditText] = useState(content)
    const editTextareaRef = useRef(null)

    useEffect(() => {
        setEditText(content)
    }, [content])

    useEffect(() => {
        if (isEditing && editTextareaRef.current) {
            editTextareaRef.current.focus()
            const len = editTextareaRef.current.value.length
            editTextareaRef.current.setSelectionRange(len, len)
        }
    }, [isEditing])

    const handleSaveEdit = () => {
        if (!editText.trim()) return
        setIsEditing(false)
        onSaveEdit?.(index, editText.trim())
    }

    const handleCancelEdit = () => {
        setEditText(content)
        setIsEditing(false)
    }

    const isContextOverflow = content.includes('đạt giới hạn bộ nhớ ngữ cảnh')
        || content.includes('vượt quá dung lượng ngữ cảnh')
        || content.includes('CONTEXT_LENGTH_EXCEEDED')
        || !!m.isContextOverflow

    const isExplicitError = !isContextOverflow && (!!m.isError || (isBot && (content.startsWith('Error:') || content.includes('[Ollama] HTTP') || content.includes('inference failed:') || content.startsWith('Hệ thống không thể') || content.startsWith('Mô hình cục bộ không thể') || content === 'No response.' || content === 'Không nhận được phản hồi từ mô hình. Vui lòng thử lại.')))
    const isOllama404 = isExplicitError && (content.includes('404') || content.includes('not found') || content.includes('gemma4:latest'))

    if (!isBot) {
        return (
            <div className={`${styles.msg} ${styles.msgUser}`}>
                {!isEditing && (
                    <div className={styles.userFloatingActions}>
                        <button
                            type="button"
                            className={styles.userActionBtn}
                            onClick={() => setIsEditing(true)}
                            title={t ? t('chatbot.editAndResend') : 'Chỉnh sửa & gửi lại'}
                            aria-label="Edit message"
                        >
                            <Pencil size={12} />
                        </button>
                        <button
                            type="button"
                            className={`${styles.userActionBtn} ${isCopied ? styles.userActionBtnActive : ''}`}
                            onClick={() => onCopy(msgKey, content)}
                            title={isCopied ? 'Đã sao chép!' : 'Sao chép'}
                            aria-label="Copy message"
                        >
                            {isCopied ? <Check size={12} /> : <Copy size={12} />}
                        </button>
                        <span className={styles.userTimeOutside}>{m.time}</span>
                    </div>
                )}
                <div className={`${styles.bubble} ${styles.bubbleUser} ${isEditing ? styles.bubbleUserEditing : ''}`}>
                    {isEditing ? (
                        <div className={styles.userEditContainer}>
                            <textarea
                                ref={editTextareaRef}
                                className={styles.userEditTextarea}
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault()
                                        handleSaveEdit()
                                    } else if (e.key === 'Escape') {
                                        e.preventDefault()
                                        handleCancelEdit()
                                    }
                                }}
                                rows={Math.min(8, Math.max(2, editText.split('\n').length))}
                                placeholder="Chỉnh sửa câu hỏi..."
                            />
                            <div className={styles.userEditActions}>
                                <button
                                    type="button"
                                    className={styles.userEditCancelBtn}
                                    onClick={handleCancelEdit}
                                >
                                    Hủy
                                </button>
                                <button
                                    type="button"
                                    className={styles.userEditSaveBtn}
                                    onClick={handleSaveEdit}
                                    disabled={!editText.trim()}
                                >
                                    <Send size={12} />
                                    <span>Lưu & Gửi lại</span>
                                </button>
                            </div>
                        </div>
                    ) : (
                        content
                    )}
                </div>
                <div className={styles.avatarUser}>
                    <User size={14} />
                </div>
            </div>
        )
    }

    return (
        <div className={`${styles.msg} ${styles.msgBot}`}>
            <div className={styles.avatar}>
                {isStreaming
                    ? <Loader2 size={14} className={styles.spinIcon} />
                    : (isContextOverflow
                        ? <AlertCircle size={14} color="#fbbf24" />
                        : (isExplicitError ? <AlertTriangle size={14} color="#fca5a5" /> : <Bot size={14} />))}
            </div>

            <div className={`${styles.bubble} ${styles.bubbleBot} ${isContextOverflow ? styles.bubbleContextWarning : (isExplicitError ? styles.bubbleError : '')}`}>
                {isContextOverflow ? (
                    <div className={styles.contextWarningCard}>
                        <div className={styles.contextWarningHeader}>
                            <AlertCircle size={16} />
                            <span>Ngữ cảnh hội thoại đã đầy</span>
                        </div>
                        <p className={styles.contextWarningDesc}>
                            Đoạn hội thoại hiện tại chứa nhiều câu hỏi và dữ liệu log lớn đã đạt giới hạn bộ nhớ ngữ cảnh của mô hình AI cục bộ. Để AI phân tích chính xác và đạt hiệu suất cao nhất, bạn vui lòng mở một phiên chat mới hoặc chuyển sang Cloud AI.
                        </p>
                        <div className={styles.contextWarningActions}>
                            <button
                                type="button"
                                className={styles.contextNewChatBtn}
                                onClick={() => onNewChat?.()}
                            >
                                <Plus size={13} /> Mở phiên chat mới
                            </button>
                            <button
                                type="button"
                                className={styles.errorCloudBtn}
                                onClick={() => onSwitchModel?.(index, 'gemini-2.0-flash-free')}
                            >
                                <Zap size={13} /> Thử Cloud AI (1M context)
                            </button>
                        </div>
                    </div>
                ) : isExplicitError ? (
                    <div className={styles.errorCard}>
                        <div className={styles.errorHeader}>
                            <AlertTriangle size={16} />
                            <span>{isOllama404 ? 'Mô hình AI cục bộ chưa sẵn sàng' : 'Lỗi xử lý yêu cầu AI'}</span>
                        </div>
                        <p className={styles.errorDesc}>
                            {isOllama404
                                ? 'Mô hình gemma4:latest cục bộ đang được tải về (hoặc chưa khởi động xong). Bạn có thể thử lại sau giây lát hoặc chuyển sang mô hình Cloud AI để tiếp tục ngay lập tức.'
                                : 'Hệ thống không thể hoàn tất câu trả lời do gián đoạn kết nối hoặc timeout. Bạn có thể thử lại hoặc chọn mô hình khác.'}
                        </p>
                        <div className={styles.errorActions}>
                            <button
                                type="button"
                                className={styles.errorRetryBtn}
                                onClick={() => onRegenerate?.(index)}
                            >
                                <RefreshCw size={13} /> Thử lại
                            </button>
                            <button
                                type="button"
                                className={styles.errorCloudBtn}
                                onClick={() => onSwitchModel?.(index, 'gemini-2.0-flash-free')}
                            >
                                <Zap size={13} /> Dùng Cloud AI (Miễn phí)
                            </button>
                        </div>
                        <details className={styles.errorDetails}>
                            <summary>Chi tiết kỹ thuật (Raw Log)</summary>
                            <pre>{content}</pre>
                        </details>
                    </div>
                ) : (
                    <>
                        {m.thinking && (
                            <details
                                className={styles.thinkingBlock}
                                open={isStreaming && !content}
                            >
                                <summary className={styles.thinkingSummary}>
                                    <Sparkles size={13} className={styles.thinkingSparkle} />
                                    <span>
                                        {isStreaming && !content
                                            ? (statusText || 'Đang suy nghĩ...')
                                            : `Quá trình suy nghĩ (${m.thinkingElapsed ? `${m.thinkingElapsed}s` : 'hoàn tất'})`}
                                    </span>
                                    {isStreaming && !content && <Loader2 size={12} className={styles.spinIcon} />}
                                </summary>
                                <div className={styles.thinkingContent}>
                                    <pre className={styles.thinkingText}>{m.thinking}</pre>
                                    {isStreaming && !content && <span className={styles.blinkCursor}>|</span>}
                                </div>
                            </details>
                        )}

                        {isStreaming && content === '' && !m.thinking ? (
                            <div className={styles.streamPendingBox}>
                                <div className={styles.streamStatusHeader}>
                                    <span className={styles.streamStatusPulse} />
                                    <span className={styles.streamStatusLabel}>{statusText || (typeof t === 'function' ? t('chatbot.processing') : 'Đang xử lý...')}</span>
                                </div>
                                <div className={styles.skeletonWrap}>
                                    <div className={`${styles.skeletonLine} ${styles.skeletonLong}`} />
                                    <div className={`${styles.skeletonLine} ${styles.skeletonMed}`} />
                                    <div className={`${styles.skeletonLine} ${styles.skeletonShort}`} />
                                </div>
                            </div>
                        ) : (
                            content ? (
                                <div className={styles.md}>
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent || ' '}</ReactMarkdown>
                                    {isLastStreaming && <span className={styles.blinkCursor}>|</span>}
                                </div>
                            ) : null
                        )}

                        {isStreaming && (charCount > 0 || (m.thinking && m.thinking.length > 0)) && (
                            <div className={styles.streamMeta}>
                                <span className={styles.streamDot} />
                                <span>{charCount > 0 ? `${charCount} chars · streaming…` : 'thinking…'}</span>
                            </div>
                        )}

                        {!isStreaming && (
                            <div className={styles.msgFooter}>
                                <div className={styles.msgFooterLeft}>
                                    <button
                                        type="button"
                                        className={`${styles.actionBtn} ${isCopied ? styles.actionBtnCopied : ''}`}
                                        onClick={() => onCopy(msgKey, displayContent)}
                                        title="Sao chép toàn bộ câu trả lời"
                                        aria-label="Copy response"
                                    >
                                        {isCopied ? <Check size={12} className={styles.actionIcon} /> : <Copy size={12} className={styles.actionIcon} />}
                                        <span>{isCopied ? 'Đã sao chép' : 'Sao chép'}</span>
                                    </button>
                                    {prevUserPrompt && (
                                        <button
                                            type="button"
                                            className={styles.actionBtn}
                                            onClick={() => onRegenerate?.(index)}
                                            title="Tạo lại câu trả lời với cùng câu hỏi"
                                            aria-label="Regenerate response"
                                        >
                                            <RotateCcw size={12} className={styles.actionIcon} />
                                            <span>Tạo lại</span>
                                        </button>
                                    )}
                                    {prevUserPrompt && (modelKey.includes('gemma') || modelKey.includes(':') || modelKey.endsWith('.gguf')) && (
                                        <button
                                            type="button"
                                            className={`${styles.actionBtn} ${styles.actionBtnCloud}`}
                                            onClick={() => onSwitchModel?.(index, 'gemini-2.0-flash-free')}
                                            title="Chạy thử câu hỏi này bằng Cloud AI (Nhanh & Miễn phí)"
                                            aria-label="Try with Cloud AI"
                                        >
                                            <Zap size={12} className={styles.actionIcon} />
                                            <span>Thử Cloud</span>
                                        </button>
                                    )}
                                </div>

                                <div className={styles.msgFooterRight}>
                                    {typeof m.elapsedSec === 'number' && m.elapsedSec >= 0 && (
                                        <span className={styles.elapsedBadge} title={`Thời gian xử lý: ${m.elapsedSec}s`}>
                                            {m.elapsedSec}s
                                        </span>
                                    )}
                                    {modelKey && (
                                        <span
                                            className={styles.modelBadge}
                                            style={{ '--badge-accent': providerColor }}
                                            title={m.requestedModel && m.model && m.requestedModel !== m.model
                                                ? `${getModelLabel(m.requestedModel)} → ${getModelLabel(m.model)}`
                                                : modelKey}
                                        >
                                            <span className={styles.modelProviderDot} style={{ background: providerColor }} />
                                            {getModelLabel(modelKey)}
                                            {m.requestedModel && m.model && m.requestedModel !== m.model ? ' (fallback)' : ''}
                                        </span>
                                    )}
                                    {m.ragUsed && <span className={styles.badge} title="Trả lời có sử dụng tài liệu RAG nội bộ">RAG</span>}
                                    {m.searchUsed && <span className={styles.badge} title="Trả lời có sử dụng kết quả tìm kiếm web">Web Search</span>}
                                    <span className={styles.time}>{m.time}</span>
                                </div>
                            </div>
                        )}

                        {!isStreaming && m.ragUsed && m.sources?.length > 0 && (
                            <div className={styles.sourcesList}>
                                {m.sources.slice(0, 4).map((src, idx) => (
                                    <a key={idx} href={src.startsWith('http') ? src : '#'} target="_blank" rel="noreferrer" className={styles.sourceItem}>
                                        {src}
                                    </a>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    )
})

function isOllamaModelAvailable(modelId, ollamaAvailable) {
    if (!ollamaAvailable || ollamaAvailable.length === 0) return null
    const mapped = OLLAMA_ID_MAP[modelId]
    if (!mapped) return null
    if (ollamaAvailable.includes(mapped)) return true
    const prefix = mapped.split(':')[0] + ':'
    if (ollamaAvailable.some(a => a.startsWith(prefix))) return true
    return false
}

const ModelDropdown = memo(function ModelDropdown({
    selectedModel, modelDropdown, focusedModelIdx,
    onToggle, onSelect, onKeyDown, modelBtnRef, dropdownRef,
    models, pullingModels, onPull, onDelete
}) {
    const activeModelInfo = models.find(m => m.id === selectedModel) || models[0]
    return (
        <div className={styles.modelPicker}>
            <button
                ref={modelBtnRef}
                type="button"
                className={styles.modelBtn}
                onClick={onToggle}
                onKeyDown={onKeyDown}
                style={{ '--provider-color': PROVIDER_COLORS[activeModelInfo?.provider] }}
                aria-haspopup="listbox"
                aria-expanded={modelDropdown}
                aria-label={`Selected model: ${activeModelInfo?.label}`}
            >
                <span className={styles.modelDot} style={{ background: PROVIDER_COLORS[activeModelInfo?.provider] }} />
                <span className={styles.modelBtnLabel}>{activeModelInfo?.label || selectedModel}</span>
                <ChevronDown size={14} className={`${styles.modelChevron} ${modelDropdown ? styles.modelChevronOpen : ''}`} />
            </button>
            {modelDropdown && (
                <div
                    ref={dropdownRef}
                    className={styles.modelDropdown}
                    role="listbox"
                    aria-label="Select AI Model"
                    aria-activedescendant={focusedModelIdx >= 0 && models[focusedModelIdx] ? `model-opt-${models[focusedModelIdx].id}` : undefined}
                    onKeyDown={onKeyDown}
                >
                    <div className={styles.modelDropdownTitle}>Select AI Model</div>
                    {models.map((m, idx) => {
                        const prevProvider = idx > 0 ? models[idx - 1].provider : null
                        const showOllamaDivider = m.provider === 'ollama' && prevProvider !== 'ollama'
                        const showLocalDivider  = m.provider === 'local'  && prevProvider !== 'local'
                        const isInstalled = m.provider === 'ollama' ? m.installed !== false : true
                        const pulling = pullingModels?.[m.id]
                        const isPulling = !!pulling
                        return (
                            <div key={m.id}>
                                {showOllamaDivider && (
                                    <div className={styles.modelDropdownDivider} style={{ color: PROVIDER_COLORS.ollama }}>
                                        <span>🦙 Ollama Models · 100% Local</span>
                                    </div>
                                )}
                                {showLocalDivider && (
                                    <div className={styles.modelDropdownDivider}>
                                        <span>🖥️ LocalAI (Llama · SecurityLLM)</span>
                                    </div>
                                )}
                                <div
                                    id={`model-opt-${m.id}`}
                                    role="option"
                                    aria-selected={selectedModel === m.id}
                                    className={`${styles.modelOption} ${selectedModel === m.id ? styles.modelOptionActive : ''} ${focusedModelIdx === idx ? styles.modelOptionFocused : ''}`}
                                    style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}
                                >
                                    <button
                                        type="button"
                                        style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'inherit', font: 'inherit', textAlign: 'left' }}
                                        onClick={() => isInstalled ? onSelect(m.id) : null}
                                        title={!isInstalled ? 'Not installed — click download to pull' : ''}
                                    >
                                        <span className={styles.modelDot} style={{
                                            background: !isInstalled ? '#6b7280' : PROVIDER_COLORS[m.provider]
                                        }} />
                                        <span className={styles.modelOptionName} style={!isInstalled ? { opacity: 0.55 } : undefined}>
                                            {m.label}
                                        </span>
                                        {m.provider === 'ollama' && isInstalled && (
                                            <span className={styles.modelBadge} style={{ background: '#059669', color: '#fff', fontSize: '0.6rem' }}>✓ Ready</span>
                                        )}
                                        {m.provider === 'ollama' && !isInstalled && !isPulling && (
                                            <span className={styles.modelBadge} style={{ background: '#6b7280', color: '#fff', fontSize: '0.6rem' }}>Not Installed</span>
                                        )}
                                        {isPulling && (
                                            <span className={styles.modelBadge} style={{ background: '#2563eb', color: '#fff', fontSize: '0.6rem' }}>
                                                <Loader2 size={10} style={{ animation: 'spin 1s linear infinite', marginRight: 3 }} />
                                                {pulling.progress || 0}%
                                            </span>
                                        )}
                                        {m.badge && <span className={styles.modelBadge} style={{ fontSize: '0.6rem' }}>{m.badge}</span>}
                                        <span className={styles.modelProviderTag} style={{ color: PROVIDER_COLORS[m.provider] }}>
                                            {PROVIDER_LABEL[m.provider] || m.provider}
                                        </span>
                                    </button>
                                    {m.provider === 'ollama' && !isInstalled && !isPulling && onPull && (
                                        <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); onPull(m.id) }}
                                            title={`Download ${m.label}`}
                                            style={{ background: 'rgba(37,99,235,0.12)', border: '1px solid rgba(37,99,235,0.3)', borderRadius: 6, padding: '3px 7px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3, color: '#2563eb', fontSize: '0.65rem', whiteSpace: 'nowrap' }}
                                        >
                                            <Download size={11} /> Pull
                                        </button>
                                    )}
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
})

const SessionList = memo(function SessionList({ sessions, activeId, onOpen, onRemove, onNew, onClose, onClearAll, t }) {
    const [search, setSearch] = useState('')

    const filtered = useMemo(() => {
        if (!search.trim()) return sessions
        const q = search.toLowerCase()
        return sessions.filter(s =>
            s.title?.toLowerCase().includes(q) ||
            s.messages?.some(m => m.content?.toLowerCase().includes(q))
        )
    }, [sessions, search])

    return (
        <>
            <div className={styles.sidebarHeader}>
                <h3>{t('chatbot.history')}</h3>
                <div style={{ display: 'flex', gap: 4 }}>
                    {sessions.length > 0 && (
                        <button
                            className={styles.sidebarClose}
                            onClick={onClearAll}
                            title={t('chatbot.clearAll')}
                            style={{ fontSize: '0.7rem', padding: '4px 8px', borderRadius: 6, background: 'rgba(248,113,113,0.09)', color: 'var(--accent-red)', border: '1px solid rgba(248,113,113,0.2)' }}
                        >
                            {t('chatbot.clearAll')}
                        </button>
                    )}
                    <button className={styles.sidebarClose} onClick={onClose}>✕</button>
                </div>
            </div>
            <button className={styles.newBtn} onClick={onNew}>
                <Plus size={13} style={{ marginRight: 4 }} />{t('chatbot.newChatFull')}
            </button>
            {sessions.length > 0 && (
                <div style={{ padding: '0 0.75rem 0.4rem' }}>
                    <input
                        className={styles.sessionSearch}
                        type="search"
                        placeholder={t('chatbot.searchHistory')}
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        aria-label={t('chatbot.searchHistory')}
                    />
                </div>
            )}
            <div className={styles.sessionList}>
                {filtered.length === 0 && (
                    <p className={styles.empty}>{sessions.length === 0 ? t('chatbot.noConversations') : t('chatbot.noMatches')}</p>
                )}
                {filtered.map(s => (
                    <div
                        key={s.id}
                        className={`${styles.sessionItem} ${s.id === activeId ? styles.sessionActive : ''}`}
                        onClick={() => onOpen(s)}
                    >
                        <div className={styles.sessionInfo}>
                            <div className={styles.sessionTitle}>{s.title}</div>
                            <div className={styles.sessionMeta}>{s.count} {t('chatbot.msgs')} · {s.time}</div>
                        </div>
                        <button className={styles.sessionDel} onClick={e => onRemove(e, s.id)} aria-label={t('chatbot.deleteSession')}>
                            <Trash2 size={12} />
                        </button>
                    </div>
                ))}
            </div>
        </>
    )
})

const MIN_TEXTAREA_H = 44
const MAX_TEXTAREA_H = 180

function useAutoResizeTextarea(ref, value) {
    useEffect(() => {
        const el = ref.current
        if (!el) return
        el.style.height = 'auto'
        const scrollH = el.scrollHeight
        const newH = Math.max(MIN_TEXTAREA_H, Math.min(scrollH, MAX_TEXTAREA_H))
        el.style.height = `${newH}px`
        el.style.overflowY = scrollH > MAX_TEXTAREA_H ? 'auto' : 'hidden'
    }, [ref, value])
}

export default function ChatbotPage() {
    const { t, locale } = useTranslation()
    const { user, token } = useAuth()
    const [sessions, setSessions] = useState([])
    const [activeId, setActiveId] = useState(null)
    const [localMsgs, setLocalMsgs] = useState([])
    const [input, setInput] = useState('')
    const [sidebar, setSidebar] = useState(false)
    const [ready, setReady] = useState(false)
    const [selectedModel, setSelectedModel] = useState('gemini-3-flash-preview')
    const [modelDropdown, setModelDropdown] = useState(false)
    const [focusedModelIdx, setFocusedModelIdx] = useState(-1)
    const [aiStatus, setAiStatus] = useState(null)
    const [copiedMsgId, setCopiedMsgId] = useState(null)
    const [showScrollBtn, setShowScrollBtn] = useState(false)
    const isSubmitting = useRef(false)
    const mountedRef = useRef(true)
    const endRef = useRef(null)

    // Subscribe to module-level streaming store so this component re-renders
    // when the store emits updates. The store survives remounts (e.g. navbar
    // tab switches) so an ongoing stream continues to paint tokens into the
    // bubble even after the previous page component was unmounted.
    const stream = useStreamStore()

    // Derived state: when a stream is active for the current session, the
    // store's messages are the source of truth (they include the in-flight
    // assistant bubble and latest tokens). Otherwise fall back to local
    // session messages loaded from localStorage.
    const isStreamingActive = stream.streaming && (!activeId || stream.sessionId === activeId || !stream.sessionId)
    const msgs = isStreamingActive ? stream.messages : localMsgs
    const sending = isStreamingActive
    const statusText = isStreamingActive ? stream.statusText : ''
    const inputRef = useRef(null)
    const chatAreaRef = useRef(null)
    const modelBtnRef = useRef(null)
    const dropdownRef = useRef(null)
    const prevMsgLenRef = useRef(0)

    useEffect(() => {
        if (stream.streaming && stream.sessionId && (!activeId || activeId !== stream.sessionId)) {
            setActiveId(stream.sessionId)
        }
    }, [stream.streaming, stream.sessionId, activeId])

    const [ollamaAvailable, setOllamaAvailable] = useState([])
    const [ollamaCatalog, setOllamaCatalog] = useState([])
    const [pullingModels, setPullingModels] = useState({})

    useAutoResizeTextarea(inputRef, input)

    useEffect(() => {
        const area = chatAreaRef.current
        if (!area) return
        const handleScroll = () => {
            const distanceFromBottom = area.scrollHeight - area.scrollTop - area.clientHeight
            setShowScrollBtn(distanceFromBottom > 120)
        }
        area.addEventListener('scroll', handleScroll, { passive: true })
        return () => area.removeEventListener('scroll', handleScroll)
    }, [])

    const scrollToBottom = useCallback(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [])

    useEffect(() => {
        let cancelled = false
        const fetchStatus = async () => {
            try {
                const res = await fetch('/api/system/ai-status')
                if (!res.ok || cancelled) return
                const data = await res.json()
                const missing = Object.entries(data?.model_guard || {}).filter(([, s]) => s !== 'present')
                if (!cancelled) {
                    // Step 3: dropped misleading mode badge — keep raw status for any
                    // future UI that needs it (ollama list still consumed below).
                    setAiStatus({ missing, details: data })
                    if (Array.isArray(data?.ollama_models)) {
                        setOllamaAvailable(data.ollama_models)
                    }
                }
            } catch { }
        }
        fetchStatus()
        const timer = setInterval(fetchStatus, 60000)
        return () => { cancelled = true; clearInterval(timer) }
    }, [])

    // Fetch Ollama catalog (installed + available models)
    const fetchOllamaCatalog = useCallback(async () => {
        try {
            const res = await fetch('/api/ollama/models')
            if (!res.ok) return
            const data = await res.json()
            if (Array.isArray(data?.models)) {
                setOllamaCatalog(data.models)
                setOllamaAvailable(data.installed || [])
            }
        } catch { }
    }, [])

    useEffect(() => {
        fetchOllamaCatalog()
        const t = setInterval(fetchOllamaCatalog, 30000)
        return () => clearInterval(t)
    }, [fetchOllamaCatalog])

    const handlePullModel = useCallback(async (modelId) => {
        setPullingModels(prev => ({ ...prev, [modelId]: { status: 'pulling', progress: 0 } }))
        try {
            await fetch('/api/ollama/pull', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: modelId }),
            })
            // Poll progress
            const poll = setInterval(async () => {
                try {
                    const res = await fetch(`/api/ollama/pull/status?model=${encodeURIComponent(modelId)}`)
                    const data = await res.json()
                    const st = data?.status
                    if (st?.status === 'done' || st?.status === 'error') {
                        clearInterval(poll)
                        setPullingModels(prev => { const n = { ...prev }; delete n[modelId]; return n })
                        fetchOllamaCatalog()
                    } else if (st?.status === 'pulling') {
                        setPullingModels(prev => ({ ...prev, [modelId]: st }))
                    }
                } catch { clearInterval(poll) }
            }, 2000)
        } catch {
            setPullingModels(prev => { const n = { ...prev }; delete n[modelId]; return n })
        }
    }, [fetchOllamaCatalog])

    const handleDeleteModel = useCallback(async (modelId) => {
        try {
            await fetch(`/api/ollama/models/${encodeURIComponent(modelId)}`, { method: 'DELETE' })
            fetchOllamaCatalog()
        } catch { }
    }, [fetchOllamaCatalog])

    const allModels = useMemo(() => {
        const staticOllama = CLOUD_MODELS.filter(m => m.provider === 'ollama')
        const cloud = CLOUD_MODELS.filter(m => m.provider !== 'local' && m.provider !== 'ollama')
        const local = CLOUD_MODELS.filter(m => m.provider === 'local')
        const dynamicOllama = ollamaCatalog
            .filter(m => m.installed === true)
            .map(m => ({
                id: m.id,
                label: `${m.name} ${m.params || ''}`.trim(),
                provider: 'ollama',
                badge: `${m.params || 'Local'} · ${m.size || ''}`.trim(),
                installed: m.installed,
                pull_status: m.pull_status,
            }))

        // Deduplicate uniquely by model ID
        const modelMap = new Map()
        for (const m of [...staticOllama, ...dynamicOllama, ...cloud, ...local]) {
            if (!modelMap.has(m.id)) {
                modelMap.set(m.id, m)
            }
        }
        return Array.from(modelMap.values())
    }, [ollamaCatalog])

    const maxInput = useMemo(() => {
        const model = allModels.find(m => m.id === selectedModel)
        return (model?.provider === 'local' || model?.provider === 'ollama') ? MAX_INPUT_LOCAL : MAX_INPUT_CLOUD
    }, [selectedModel, allModels])
    const warnThreshold = maxInput - WARN_OFFSET

    useEffect(() => {
        mountedRef.current = true
        const saved = lsGet(SESSIONS_KEY, [])
        const id = lsGet(ACTIVE_KEY, null)
        const savedModel = lsGet(MODEL_KEY, 'gemma4:latest')
        const validIds = new Set(CLOUD_MODELS.map(m => m.id))
        const resolvedModel = (savedModel && (validIds.has(savedModel) || savedModel.includes(':') || savedModel.endsWith('.gguf')))
            ? savedModel
            : 'gemma4:latest'
        setSelectedModel(resolvedModel)

        // If the store is already streaming (e.g. user navigated away via
        // navbar and came back), just adopt its session id so the derived
        // state branch picks up live messages. Otherwise process PENDING_KEY
        // for the hard-reload resume path.
        const storeSnap = streamStore.getState()
        if (storeSnap.streaming && storeSnap.sessionId) {
            setSessions(saved)
            setActiveId(storeSnap.sessionId)
            // Preserve already-persisted session messages as a fallback;
            // the derived `msgs` will come from the store while streaming.
            const s = saved.find(x => x.id === storeSnap.sessionId)
            if (s) setLocalMsgs(s.messages || [])
            setReady(true)
            return () => { mountedRef.current = false }
        }

        const pending = lsGet(PENDING_KEY, null)
        if (pending?.done) {
            directSaveSession(pending.sessionId, pending.finalMessages)
            lsDel(PENDING_KEY)
            const refreshed = lsGet(SESSIONS_KEY, [])
            setSessions(refreshed)
            if (id === pending.sessionId || !id) {
                setActiveId(pending.sessionId)
                setLocalMsgs(pending.finalMessages)
                lsSet(ACTIVE_KEY, pending.sessionId)
            }
        } else if (pending && !pending.done) {
            // Hard-reload resume path: the previous page process died while a
            // stream was in flight (page fully reloaded, not just a React
            // remount from tab switch — those are handled by the store above).
            // Finalize any in-flight assistant bubble with an "interrupted"
            // note so the user keeps the partial answer.
            const restored = Array.isArray(pending.currentMessages) ? pending.currentMessages : []
            const finalized = restored.map(m => {
                if (!m?._streaming) return m
                const txt = (m.content || '').trim()
                return {
                    ...m,
                    _streaming: false,
                    _id: undefined,
                    content: txt
                        ? `${txt}\n\n_${t('chatbot.streamInterrupted') || 'Stream interrupted — please resend if the answer is incomplete.'}_`
                        : (t('chatbot.streamInterrupted') || 'Stream interrupted — please resend if the answer is incomplete.'),
                    isError: !txt,
                }
            })
            setActiveId(pending.sessionId)
            setLocalMsgs(finalized)
            lsSet(ACTIVE_KEY, pending.sessionId)
            if (finalized.length > 0) {
                directSaveSession(pending.sessionId, finalized)
            }
            setSessions(lsGet(SESSIONS_KEY, []))
            lsDel(PENDING_KEY)
            isSubmitting.current = false
        } else {
            setSessions(saved)
            if (id) {
                const s = saved.find(x => x.id === id)
                if (s) { setActiveId(id); setLocalMsgs(s.messages || []) }
            }
        }
        setReady(true)
        return () => { mountedRef.current = false }
    }, [])

    // Fetch user sessions from backend SQLite database on mount / login
    useEffect(() => {
        if (!ready) return
        let cancelled = false
        const fetchBackendSessions = async () => {
            try {
                const headers = {}
                if (token) headers['Authorization'] = `Bearer ${token}`
                const res = await fetch('/api/chat/sessions', { headers })
                if (!res.ok || cancelled) return
                const data = await res.json()
                if (Array.isArray(data.sessions) && data.sessions.length > 0 && !cancelled) {
                    setSessions(prev => {
                        const localMap = new Map(prev.map(s => [s.id || s.session_id, s]))
                        const merged = data.sessions.map(s => {
                            const sId = s.id || s.session_id
                            const local = localMap.get(sId)
                            return {
                                ...s,
                                id: sId,
                                messages: (local?.messages && local.messages.length > 0) ? local.messages : (s.messages || [])
                            }
                        })
                        const backendIds = new Set(data.sessions.map(s => s.id || s.session_id))
                        for (const [id, s] of localMap.entries()) {
                            if (!backendIds.has(id)) {
                                merged.push(s)
                            }
                        }
                        return merged
                    })
                }
            } catch (e) {
                console.warn('[chatbot] failed to load backend sessions:', e)
            }
        }
        fetchBackendSessions()
        return () => { cancelled = true }
    }, [ready, token, user])

    useEffect(() => { if (ready) lsSet(SESSIONS_KEY, sessions) }, [sessions, ready])
    useEffect(() => { if (ready) lsSet(ACTIVE_KEY, activeId) }, [activeId, ready])

    useEffect(() => {
        if (msgs.length > prevMsgLenRef.current) {
            endRef.current?.scrollIntoView({ behavior: 'smooth' })
        }
        prevMsgLenRef.current = msgs.length
    }, [msgs.length])

    const handleModelChange = useCallback((modelId) => {
        setSelectedModel(modelId)
        lsSet(MODEL_KEY, modelId)
        setModelDropdown(false)
        setFocusedModelIdx(-1)
        modelBtnRef.current?.focus()
    }, [])

    const openDropdown = useCallback(() => {
        const idx = allModels.findIndex(m => m.id === selectedModel)
        setFocusedModelIdx(idx >= 0 ? idx : 0)
        setModelDropdown(true)
    }, [selectedModel, allModels])

    const handleModelKeyDown = useCallback((e) => {
        if (!modelDropdown) {
            if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
                e.preventDefault()
                openDropdown()
            }
            return
        }
        if (e.key === 'ArrowDown') {
            e.preventDefault()
            setFocusedModelIdx(prev => (prev + 1) % allModels.length)
        } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setFocusedModelIdx(prev => (prev - 1 + allModels.length) % allModels.length)
        } else if (e.key === 'Enter') {
            e.preventDefault()
            if (focusedModelIdx >= 0 && allModels[focusedModelIdx]) handleModelChange(allModels[focusedModelIdx].id)
        } else if (e.key === 'Escape' || e.key === 'Tab') {
            e.preventDefault()
            setModelDropdown(false)
            setFocusedModelIdx(-1)
            modelBtnRef.current?.focus()
        }
    }, [modelDropdown, focusedModelIdx, handleModelChange, openDropdown, allModels])

    const copyMessage = useCallback((id, text) => {
        const fallbackCopy = () => {
            try {
                const ta = document.createElement('textarea')
                ta.value = typeof text === 'string' ? text : JSON.stringify(text)
                ta.style.position = 'fixed'
                ta.style.opacity = '0'
                document.body.appendChild(ta)
                ta.select()
                document.execCommand('copy')
                document.body.removeChild(ta)
                setCopiedMsgId(id)
                setTimeout(() => setCopiedMsgId(null), 2000)
            } catch { }
        }
        if (navigator.clipboard?.writeText) {
            navigator.clipboard.writeText(typeof text === 'string' ? text : JSON.stringify(text)).then(() => {
                setCopiedMsgId(id)
                setTimeout(() => setCopiedMsgId(null), 2000)
            }).catch(fallbackCopy)
        } else {
            fallbackCopy()
        }
    }, [])

    const updateSessions = useCallback((messages, id) => {
        const dateFmt = locale === 'vi' ? 'vi-VN' : 'en-US'
        const title = messages[0]?.content?.slice(0, 50) || t('chatbot.newChatFull')
        const entry = { id, session_id: id, title, time: new Date().toLocaleString(dateFmt), messages, count: messages.length }
        setSessions(prev => {
            const i = prev.findIndex(x => (x.id || x.session_id) === id)
            if (i >= 0) { const u = [...prev]; u[i] = entry; return u }
            return [entry, ...prev]
        })
        // Persist to backend SQLite database
        try {
            const headers = { 'Content-Type': 'application/json' }
            if (token) headers['Authorization'] = `Bearer ${token}`
            fetch('/api/chat/sessions', {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    session_id: id,
                    title,
                    messages,
                    user_id: user?.id
                })
            }).catch(() => {})
        } catch {}
    }, [locale, t, token, user])

    const handleSaveEdit = useCallback(async (msgIdx, newText) => {
        if (!newText || !newText.trim()) return
        if (isSubmitting.current || streamStore.getState().streaming) return
        isSubmitting.current = true

        const id = activeId || uid()
        if (!activeId) setActiveId(id)

        // Truncate conversation to replace this turn and clear downstream history
        const truncated = localMsgs.slice(0, msgIdx)
        const updatedUserMsg = { role: 'user', content: newText.trim(), time: now() }
        const next = [...truncated, updatedUserMsg]
        setLocalMsgs(next)
        updateSessions(next, id)

        const isLocal = LOCAL_MODEL_IDS.has(selectedModel)
            || selectedModel.includes(':')
            || selectedModel.endsWith('.gguf')

        try {
            await streamStore.startStream({
                sessionId: id,
                messages: next,
                userText: newText.trim(),
                selectedModel,
                isLocal,
                t,
                locale,
                token,
                userId: user?.id,
                onFinalize: (finalMessages) => {
                    if (!mountedRef.current) return
                    setLocalMsgs(finalMessages)
                    updateSessions(finalMessages, id)
                },
            })
        } catch {
        } finally {
            isSubmitting.current = false
        }
    }, [activeId, selectedModel, updateSessions, localMsgs, t, locale, token, user])

    const handleRegenerate = useCallback(async (botIdx) => {
        if (isSubmitting.current || streamStore.getState().streaming) return
        isSubmitting.current = true

        const id = activeId || uid()
        if (!activeId) setActiveId(id)

        // Find the user prompt for this bot reply (at botIdx - 1)
        const userMsg = botIdx > 0 && localMsgs[botIdx - 1]?.role === 'user'
            ? localMsgs[botIdx - 1]
            : localMsgs.find(m => m.role === 'user')

        const userText = userMsg?.content || ''
        if (!userText) {
            isSubmitting.current = false
            return
        }

        // Truncate messages so this bot response and subsequent turns are removed
        const next = localMsgs.slice(0, botIdx)
        setLocalMsgs(next)
        updateSessions(next, id)

        const isLocal = LOCAL_MODEL_IDS.has(selectedModel)
            || selectedModel.includes(':')
            || selectedModel.endsWith('.gguf')

        try {
            await streamStore.startStream({
                sessionId: id,
                messages: next,
                userText: userText.trim(),
                selectedModel,
                isLocal,
                t,
                locale,
                token,
                userId: user?.id,
                onFinalize: (finalMessages) => {
                    if (!mountedRef.current) return
                    setLocalMsgs(finalMessages)
                    updateSessions(finalMessages, id)
                },
            })
        } catch {
        } finally {
            isSubmitting.current = false
        }
    }, [activeId, selectedModel, updateSessions, localMsgs, t, locale, token, user])

    const handleSwitchModelAndRegenerate = useCallback(async (botIdx, modelId) => {
        handleModelChange(modelId)
        if (isSubmitting.current || streamStore.getState().streaming) return
        isSubmitting.current = true

        const id = activeId || uid()
        if (!activeId) setActiveId(id)

        const userMsg = botIdx > 0 && localMsgs[botIdx - 1]?.role === 'user'
            ? localMsgs[botIdx - 1]
            : localMsgs.find(m => m.role === 'user')

        const userText = userMsg?.content || ''
        if (!userText) {
            isSubmitting.current = false
            return
        }

        const next = localMsgs.slice(0, botIdx)
        setLocalMsgs(next)
        updateSessions(next, id)

        const isLocal = LOCAL_MODEL_IDS.has(modelId)
            || modelId.includes(':')
            || modelId.endsWith('.gguf')

        try {
            await streamStore.startStream({
                sessionId: id,
                messages: next,
                userText: userText.trim(),
                selectedModel: modelId,
                isLocal,
                t,
                locale,
                token,
                userId: user?.id,
                onFinalize: (finalMessages) => {
                    if (!mountedRef.current) return
                    setLocalMsgs(finalMessages)
                    updateSessions(finalMessages, id)
                },
            })
        } catch {
        } finally {
            isSubmitting.current = false
        }
    }, [activeId, handleModelChange, updateSessions, localMsgs, t, locale, token, user])

    const send = useCallback(async (text) => {
        if (!text.trim()) return
        if (isSubmitting.current) return
        if (streamStore.getState().streaming) return
        isSubmitting.current = true

        const id = activeId || uid()
        if (!activeId) setActiveId(id)
        const userMsg = { role: 'user', content: text.trim(), time: now() }
        const next = [...localMsgs, userMsg]
        // Commit user message into local session state + sessions list
        // immediately. The assistant bubble + streaming lives in the store.
        setLocalMsgs(next)
        setInput('')
        updateSessions(next, id)

        // gemma4:latest etc. are loaded dynamically into models state, not in
        // static CLOUD_MODELS, so LOCAL_MODEL_IDS misses them. Treat any id with
        // ':' (Ollama tag) or '.gguf' (LocalAI) as local — bypass cloud routing.
        const isLocal = LOCAL_MODEL_IDS.has(selectedModel)
            || selectedModel.includes(':')
            || selectedModel.endsWith('.gguf')

        try {
            await streamStore.startStream({
                sessionId: id,
                messages: next,
                userText: text.trim(),
                selectedModel,
                isLocal,
                t,
                locale,
                token,
                userId: user?.id,
                onFinalize: (finalMessages) => {
                    if (!mountedRef.current) return
                    // Persist the finalized conversation into the component's
                    // local view + sessions list. The store already called
                    // directSaveSession and cleared PENDING_KEY.
                    setLocalMsgs(finalMessages)
                    updateSessions(finalMessages, id)
                },
            })
        } catch {
            // startStream rejects only when another stream is already running,
            // which we guarded against above. Swallow defensively.
        } finally {
            isSubmitting.current = false
        }
    }, [activeId, selectedModel, updateSessions, localMsgs, t, locale, token, user])

    const newChat = useCallback(() => {
        setActiveId(null); setLocalMsgs([]); setSidebar(false)
        setTimeout(() => inputRef.current?.focus(), 100)
    }, [])

    const openSession = useCallback(async (s) => {
        const sId = s.id || s.session_id
        setActiveId(sId)
        setSidebar(false)
        if (s.messages && s.messages.length > 0) {
            setLocalMsgs(s.messages)
        } else {
            // Fetch messages from backend SQLite database
            try {
                const headers = {}
                if (token) headers['Authorization'] = `Bearer ${token}`
                const res = await fetch(`/api/chat/sessions/${sId}`, { headers })
                if (res.ok) {
                    const data = await res.json()
                    const msgs = data.messages || []
                    setLocalMsgs(msgs)
                    setSessions(prev => prev.map(item => (item.id === sId || item.session_id === sId) ? { ...item, messages: msgs } : item))
                }
            } catch {}
        }
    }, [token])

    const removeSession = useCallback(async (e, id) => {
        e.stopPropagation()
        setSessions(prev => prev.filter(x => (x.id || x.session_id) !== id))
        if (activeId === id) { setActiveId(null); setLocalMsgs([]) }
        try {
            const headers = {}
            if (token) headers['Authorization'] = `Bearer ${token}`
            await fetch(`/api/chat/sessions/${id}`, { method: 'DELETE', headers })
        } catch {}
    }, [activeId, token])

    const clearAllSessions = useCallback(async () => {
        const currentSessions = [...sessions]
        setSessions([]); setActiveId(null); setLocalMsgs([])
        lsDel(SESSIONS_KEY); lsDel(ACTIVE_KEY); lsDel(PENDING_KEY)
        for (const s of currentSessions) {
            const sId = s.id || s.session_id
            if (sId) {
                try {
                    const headers = {}
                    if (token) headers['Authorization'] = `Bearer ${token}`
                    await fetch(`/api/chat/sessions/${sId}`, { method: 'DELETE', headers })
                } catch {}
            }
        }
    }, [sessions, token])

    const lastStreamingIdx = useMemo(() => {
        for (let i = msgs.length - 1; i >= 0; i--) {
            if (msgs[i]._streaming) return i
        }
        return -1
    }, [msgs])

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            send(input)
        }
    }, [input, send])

    return (
        <div className={styles.layout} onClick={() => modelDropdown && setModelDropdown(false)}>
            {sidebar && <div className={styles.overlay} onClick={() => setSidebar(false)} />}

            <aside className={`${styles.sidebar} ${sidebar ? styles.sidebarOpen : ''}`}>
                <SessionList
                    sessions={sessions}
                    activeId={activeId}
                    onOpen={openSession}
                    onRemove={removeSession}
                    onNew={newChat}
                    onClose={() => setSidebar(false)}
                    onClearAll={clearAllSessions}
                    t={t}
                />
            </aside>

            <div className={styles.main}>
                <div className={styles.topBar}>
                    <div className={styles.topLeft}>
                        <button className={styles.menuBtn} onClick={() => setSidebar(true)} title={t('chatbot.chatHistory')} aria-label={t('chatbot.chatHistory')}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h18M3 6h18M3 18h18" /></svg>
                        </button>
                        <h1 className={styles.pageTitle}>{t('chatbot.pageTitle')}</h1>
                        {/* Removed misleading "LOCAL-FIRST"/"Cloud-first" mode badge (Step 3).
                            The actual routing depends on per-request task_type, not a global flag. */}
                    </div>
                    <div className={styles.topRight}>
                        <button className={styles.topBtn} onClick={newChat} title={t('chatbot.newChatFull')} aria-label={t('chatbot.newChatFull')}>
                            <Plus size={14} />
                            <span className={styles.topBtnLabel}>{t('chatbot.newChat')}</span>
                        </button>
                        <button className={styles.topBtn} onClick={() => setSidebar(true)} title={t('chatbot.chatHistory')} aria-label={t('chatbot.chatHistory')}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8v4l3 2" /><circle cx="12" cy="12" r="9" /></svg>
                            <span className={styles.topBtnLabel}>{t('chatbot.history')}</span>
                            {sessions.length > 0 && <span className={styles.topBtnCount}>{sessions.length}</span>}
                        </button>
                    </div>
                </div>

                <div className={styles.chatArea} ref={chatAreaRef}>
                    {msgs.length === 0 && !sending ? (
                        <div className={styles.welcome}>
                            <div className={styles.welcomeHeading}>
                                <div className={styles.emptyIcon}><Bot size={28} /></div>
                                <h2 className={styles.welcomeTitle}>{t('chatbot.startConversation')}</h2>
                                <p className={styles.welcomeSub}>{t('chatbot.startConversationSub')}</p>
                            </div>
                            <div className={styles.chips}>
                                {[t('chatbot.suggestedPrompt1'), t('chatbot.suggestedPrompt2'), t('chatbot.suggestedPrompt3')].map((text, i) => (
                                    <button key={i} className={styles.chip} onClick={() => setInput(text)} aria-label={text}>
                                        {text}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className={styles.msgList}>
                            {msgs.map((m, i) => {
                                const msgKey = m._id || i
                                const prevUserPrompt = i > 0 && msgs[i - 1]?.role === 'user' ? msgs[i - 1]?.content : null
                                return (
                                    <MessageBubble
                                        key={msgKey}
                                        m={m}
                                        index={i}
                                        msgKey={msgKey}
                                        isLastStreaming={i === lastStreamingIdx}
                                        statusText={statusText}
                                        copiedMsgId={copiedMsgId}
                                        onCopy={copyMessage}
                                        onSaveEdit={handleSaveEdit}
                                        onRegenerate={handleRegenerate}
                                        onSwitchModel={handleSwitchModelAndRegenerate}
                                        onNewChat={newChat}
                                        prevUserPrompt={prevUserPrompt}
                                        t={t}
                                    />
                                )
                            })}
                            {sending && !msgs.some(m => m._streaming) && (
                                <div className={styles.typingWrap}>
                                    <div className={styles.typingDots}><span /><span /><span /></div>
                                    {statusText && <span className={styles.statusText}>{statusText}</span>}
                                </div>
                            )}
                            <div ref={endRef} />
                        </div>
                    )}
                </div>

                {showScrollBtn && (
                    <button
                        type="button"
                        className={styles.scrollBottom}
                        onClick={scrollToBottom}
                        title="Cuộn xuống tin nhắn mới nhất"
                        aria-label="Scroll to bottom"
                    >
                        <ArrowDown size={14} />
                        <span>Cuộn xuống</span>
                    </button>
                )}

                <div className={styles.inputFooter}>
                    <form className={styles.inputCard} onSubmit={e => { e.preventDefault(); send(input) }}>
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={e => setInput(e.target.value.slice(0, maxInput))}
                            onKeyDown={handleKeyDown}
                            placeholder={t('chatbot.inputPlaceholder')}
                            disabled={sending}
                            maxLength={maxInput}
                            rows={1}
                            autoFocus
                            className={styles.inputCardTextarea}
                        />
                        <div className={styles.inputCardBottom}>
                            <div className={styles.inputCardLeft} onClick={e => e.stopPropagation()}>
                                <ModelDropdown
                                    selectedModel={selectedModel}
                                    modelDropdown={modelDropdown}
                                    focusedModelIdx={focusedModelIdx}
                                    onToggle={() => modelDropdown ? (setModelDropdown(false), setFocusedModelIdx(-1)) : openDropdown()}
                                    onSelect={handleModelChange}
                                    onKeyDown={handleModelKeyDown}
                                    modelBtnRef={modelBtnRef}
                                    dropdownRef={dropdownRef}
                                    models={allModels}
                                    pullingModels={pullingModels}
                                    onPull={handlePullModel}
                                    onDelete={handleDeleteModel}
                                />
                            </div>
                            <div className={styles.inputCardRight}>
                                <span className={`${styles.charCounter} ${input.length >= warnThreshold ? styles.charCounterWarn : ''}`}>
                                    {input.length}/{maxInput}
                                </span>
                                <button
                                    type="submit"
                                    className={styles.sendBtn}
                                    disabled={!input.trim() || sending}
                                    title="Gửi câu hỏi (Enter)"
                                    aria-label="Send message"
                                >
                                    {sending
                                        ? <Loader2 size={15} className={styles.spinIcon} />
                                        : <Send size={14} />}
                                </button>
                            </div>
                        </div>
                    </form>
                    <div className={styles.inputFooterHint}>
                        <span>{t('chatbot.enterToSend') || 'Enter để gửi · Shift+Enter xuống dòng'}</span>
                    </div>
                </div>
            </div>
        </div>
    )
}
