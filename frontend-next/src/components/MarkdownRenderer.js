'use client'

import { useMemo, useEffect, useRef, useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import styles from './MarkdownRenderer.module.css'
import { Copy, Check, ExternalLink, GitBranch, Download, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false)
    const handleCopy = useCallback(() => {
        navigator.clipboard.writeText(text).then(() => {
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        })
    }, [text])
    return (
        <button className={styles.copyBtn} onClick={handleCopy} aria-label="Copy code">
            {copied ? <Check size={13} /> : <Copy size={13} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
    )
}

/* ── Global Mermaid render queue to avoid parallel render() conflicts ── */
let _mermaidQueue = Promise.resolve()
let _mermaidCounter = 0

function MermaidBlock({ content }) {
    const ref = useRef(null)
    const wrapRef = useRef(null)
    const [error, setError] = useState(null)
    const [rendered, setRendered] = useState(false)
    const [zoom, setZoom] = useState(1)
    const [isPanning, setIsPanning] = useState(false)
    const panStart = useRef({ x: 0, y: 0, scrollLeft: 0, scrollTop: 0 })
    const idRef = useRef(`mmd_${Date.now()}_${++_mermaidCounter}`)

    /* Normalize SVG after render: set viewBox for responsive scaling */
    const normalizeSvg = useCallback((container) => {
        const svg = container?.querySelector('svg')
        if (!svg) return
        const w = svg.getAttribute('width') || svg.style.width
        const h = svg.getAttribute('height') || svg.style.height
        const numW = parseFloat(w) || svg.getBBox?.()?.width || 800
        const numH = parseFloat(h) || svg.getBBox?.()?.height || 400
        if (!svg.getAttribute('viewBox')) {
            svg.setAttribute('viewBox', `0 0 ${numW} ${numH}`)
        }
        svg.removeAttribute('width')
        svg.removeAttribute('height')
        svg.removeAttribute('style')
    }, [])

    /* Drag-to-pan: mousedown/mousemove/mouseup on the wrapper */
    const handleMouseDown = useCallback((e) => {
        const wrap = wrapRef.current
        if (!wrap) return
        setIsPanning(true)
        panStart.current = {
            x: e.clientX,
            y: e.clientY,
            scrollLeft: wrap.scrollLeft,
            scrollTop: wrap.scrollTop,
        }
    }, [])

    const handleMouseMove = useCallback((e) => {
        if (!isPanning) return
        const wrap = wrapRef.current
        if (!wrap) return
        e.preventDefault()
        const dx = e.clientX - panStart.current.x
        const dy = e.clientY - panStart.current.y
        wrap.scrollLeft = panStart.current.scrollLeft - dx
        wrap.scrollTop = panStart.current.scrollTop - dy
    }, [isPanning])

    const handleMouseUp = useCallback(() => {
        setIsPanning(false)
    }, [])

    /* Mouse-wheel zoom on diagram */
    useEffect(() => {
        const wrap = wrapRef.current
        if (!wrap || !rendered) return
        const handleWheel = (e) => {
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault()
                setZoom(z => Math.min(3, Math.max(0.3, z + (e.deltaY > 0 ? -0.1 : 0.1))))
            }
        }
        wrap.addEventListener('wheel', handleWheel, { passive: false })
        return () => wrap.removeEventListener('wheel', handleWheel)
    }, [rendered])

    useEffect(() => {
        let cancelled = false
        const renderTimeout = setTimeout(() => {
            if (!cancelled && !rendered && !error) {
                setError('Diagram render timed out')
            }
        }, 15000)

        async function doRender() {
            if (typeof window === 'undefined') return
            try {
                const mermaid = (await import('mermaid')).default
                const isDark = document.documentElement.getAttribute('data-theme') !== 'light'
                mermaid.initialize({
                    startOnLoad: false,
                    theme: isDark ? 'dark' : 'default',
                    securityLevel: 'loose',
                    fontFamily: 'Inter, system-ui, sans-serif',
                    suppressErrorRendering: true,
                    themeVariables: isDark ? {
                        primaryColor: '#2563eb',
                        primaryTextColor: '#e2e8f0',
                        primaryBorderColor: '#3b82f6',
                        lineColor: '#64748b',
                        secondaryColor: '#1e293b',
                        tertiaryColor: '#0f172a',
                        background: '#0f172a',
                        mainBkg: '#1e293b',
                        secondBkg: '#334155',
                        nodeBorder: '#475569',
                        clusterBkg: '#1e293b',
                        clusterBorder: '#475569',
                        titleColor: '#f1f5f9',
                        edgeLabelBackground: '#1e293b',
                        nodeTextColor: '#e2e8f0',
                        actorTextColor: '#e2e8f0',
                        actorBkg: '#1e293b',
                        actorBorder: '#475569',
                        actorLineColor: '#64748b',
                        signalColor: '#94a3b8',
                        signalTextColor: '#e2e8f0',
                        labelBoxBkgColor: '#1e293b',
                        labelBoxBorderColor: '#475569',
                        labelTextColor: '#e2e8f0',
                        loopTextColor: '#e2e8f0',
                        noteBkgColor: '#1e3a5f',
                        noteTextColor: '#e2e8f0',
                        noteBorderColor: '#3b82f6',
                        sectionBkgColor: '#1e293b',
                        sectionBkgColor2: '#0f172a',
                        altSectionBkgColor: '#1e293b',
                        taskBkgColor: '#2563eb',
                        taskTextColor: '#fff',
                        activeTaskBkgColor: '#3b82f6',
                    } : {},
                })

                const staleEl = document.getElementById(idRef.current)
                if (staleEl) staleEl.remove()

                const { svg } = await mermaid.render(idRef.current, content)
                if (!cancelled && ref.current) {
                    ref.current.innerHTML = svg
                    normalizeSvg(ref.current)
                    setRendered(true)
                }
            } catch (e) {
                try { document.getElementById(idRef.current)?.remove() } catch (_) {}
                if (!cancelled) setError(e.message || 'Mermaid render failed')
            }
        }

        _mermaidQueue = _mermaidQueue.then(doRender, doRender)

        return () => {
            cancelled = true
            clearTimeout(renderTimeout)
        }
    }, [content, rendered, error, normalizeSvg])

    const handleZoomIn = useCallback(() => setZoom(z => Math.min(3, z + 0.25)), [])
    const handleZoomOut = useCallback(() => setZoom(z => Math.max(0.3, z - 0.25)), [])
    const handleZoomReset = useCallback(() => setZoom(1), [])

    /* Export diagram as PNG */
    const handleExport = useCallback(() => {
        const svg = ref.current?.querySelector('svg')
        if (!svg) return
        
        // Dùng cloneNode để không ảnh hưởng trang web
        const clonedSvg = svg.cloneNode(true)
        if (!clonedSvg.getAttribute('xmlns')) {
            clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
        }
        
        // Trích xuất kích thước từ viewBox
        const viewBoxStr = clonedSvg.getAttribute('viewBox')
        let w = 800, h = 400
        if (viewBoxStr) {
            const parts = viewBoxStr.split(/[\s,]+/)
            if (parts.length >= 4) {
                w = parseFloat(parts[2])
                h = parseFloat(parts[3])
            }
        }
        
        // Nhân 5 lần độ phân giải (scale = 5) để nét
        const exportScale = 5
        clonedSvg.setAttribute('width', (w * exportScale) + 'px')
        clonedSvg.setAttribute('height', (h * exportScale) + 'px')
        
        // Lấy tên theo title trong đồ thị hoặc tên mặc định
        const titleMatch = content.match(/title\s+(.+)/i)
        const customName = titleMatch ? titleMatch[1].trim().replace(/[^a-zA-Z0-9]/g, '_').toLowerCase() : 'mermaid_model'
        
        const svgData = new XMLSerializer().serializeToString(clonedSvg)
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')
        const img = new Image()
        img.crossOrigin = 'anonymous'
        
        const url = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)))
        
        img.onload = () => {
            canvas.width = w * exportScale
            canvas.height = h * exportScale
            
            ctx.fillStyle = '#0f172a' // Background dark mode
            ctx.fillRect(0, 0, canvas.width, canvas.height)
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
            try {
                const pngUrl = canvas.toDataURL('image/png', 1.0)
                const a = document.createElement('a')
                a.href = pngUrl
                a.download = `CyberAI_${customName}_${Date.now()}.png`
                a.click()
            } catch (err) {
                console.error('Export failed due to tainted canvas:', err)
                alert('Không thể xuất ảnh (Tainted Canvas). Vui lòng thử trình duyệt khác hoặc copy nội dung Memaid.')
            }
        }
        img.src = url
    }, [content])

    if (error) {
        return (
            <div className={styles.mermaidBlock}>
                <div className={styles.mermaidHeader}>
                    <GitBranch size={14} />
                    <span>Diagram (Mermaid)</span>
                </div>
                <pre className={styles.mermaidPre}>{content}</pre>
            </div>
        )
    }

    return (
        <div className={styles.mermaidBlock}>
            <div className={styles.mermaidHeader}>
                <GitBranch size={14} />
                <span>Diagram</span>
                {rendered && (
                    <div className={styles.mermaidToolbar}>
                        <button onClick={handleZoomOut} className={styles.mermaidToolBtn} aria-label="Zoom out" title="Thu nhỏ">
                            <ZoomOut size={13} />
                        </button>
                        <span className={styles.mermaidZoomLabel} onClick={handleZoomReset} title="Reset zoom">
                            {Math.round(zoom * 100)}%
                        </span>
                        <button onClick={handleZoomIn} className={styles.mermaidToolBtn} aria-label="Zoom in" title="Phóng to">
                            <ZoomIn size={13} />
                        </button>
                        <div className={styles.mermaidToolDivider} />
                        <button onClick={handleZoomReset} className={styles.mermaidToolBtn} aria-label="Reset" title="Reset zoom">
                            <RotateCcw size={12} />
                        </button>
                        <button onClick={handleExport} className={styles.mermaidToolBtn} aria-label="Download PNG" title="Tải xuống PNG">
                            <Download size={13} />
                        </button>
                    </div>
                )}
            </div>
            <div
                ref={wrapRef}
                className={`${styles.mermaidSvgWrap} ${isPanning ? styles.mermaidPanning : ''}`}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
            >
                <div
                    ref={ref}
                    className={styles.mermaidSvg}
                    style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
                />
            </div>
            {!rendered && <div className={styles.mermaidLoading}>Rendering diagram…</div>}
        </div>
    )
}

const customTheme = {
    ...oneDark,
    'pre[class*="language-"]': {
        ...oneDark['pre[class*="language-"]'],
        background: 'var(--pre-bg, #080c14)',
        margin: 0,
        padding: '1rem 1.15rem',
        borderRadius: 0,
        fontSize: '0.8rem',
        lineHeight: 1.7,
    },
    'code[class*="language-"]': {
        ...oneDark['code[class*="language-"]'],
        background: 'none',
        fontSize: '0.8rem',
        lineHeight: 1.7,
    },
}

export default function MarkdownRenderer({ content }) {
    const components = useMemo(() => ({
        h1: ({ children, ...props }) => (
            <h1 className={styles.h1} {...props}>
                {children}
            </h1>
        ),
        h2: ({ children, ...props }) => (
            <h2 className={styles.h2} {...props}>
                {children}
            </h2>
        ),
        h3: ({ children, ...props }) => (
            <h3 className={styles.h3} {...props}>
                {children}
            </h3>
        ),
        h4: ({ children, ...props }) => (
            <h4 className={styles.h4} {...props}>
                {children}
            </h4>
        ),
        h5: ({ children, ...props }) => (
            <h5 className={styles.h5} {...props}>
                {children}
            </h5>
        ),
        p: ({ children, node, ...props }) => {
            const hasBlockChild = node?.children?.some(c =>
                c.tagName === 'img' || c.tagName === 'div'
            )
            if (hasBlockChild) return <div className={styles.pBlock} {...props}>{children}</div>
            return <p className={styles.p} {...props}>{children}</p>
        },
        a: ({ href, children, ...props }) => {
            const isExternal = href?.startsWith('http')
            const isBadge = children?.[0]?.type === 'img' || (typeof children?.[0] === 'object' && children?.[0]?.props?.src)
            if (isBadge) {
                return (
                    <a href={href} className={styles.badgeLink} target="_blank" rel="noopener noreferrer" {...props}>
                        {children}
                    </a>
                )
            }
            return (
                <a
                    href={href}
                    className={styles.link}
                    {...(isExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                    {...props}
                >
                    {children}
                    {isExternal && <ExternalLink size={11} className={styles.linkIcon} />}
                </a>
            )
        },
        img: ({ src, alt, ...props }) => {
            if (src?.includes('shields.io') || src?.includes('badge')) {
                return <img src={src} alt={alt || ''} className={styles.badge} loading="lazy" {...props} />
            }
            return (
                <figure className={styles.figure}>
                    <img src={src} alt={alt || ''} className={styles.img} loading="lazy" {...props} />
                    {alt && <figcaption className={styles.figcaption}>{alt}</figcaption>}
                </figure>
            )
        },
        code: ({ className, children, node, inline, ...props }) => {
            const match = /language-(\w+)/.exec(className || '')
            const lang = match?.[1]
            const codeStr = String(children).replace(/\n$/, '')

            if (lang === 'mermaid') {
                return <MermaidBlock content={codeStr} />
            }

            if (!inline && (lang || codeStr.includes('\n'))) {
                return (
                    <div className={styles.codeBlock}>
                        <div className={styles.codeHeader}>
                            <span className={styles.codeLang}>{lang || 'text'}</span>
                            <CopyButton text={codeStr} />
                        </div>
                        <SyntaxHighlighter
                            style={customTheme}
                            language={lang || 'text'}
                            PreTag="div"
                            showLineNumbers={codeStr.split('\n').length > 5}
                            lineNumberStyle={{ color: 'var(--text-dim, #5e7189)', fontSize: '0.72rem', minWidth: '2em' }}
                            wrapLines
                            {...props}
                        >
                            {codeStr}
                        </SyntaxHighlighter>
                    </div>
                )
            }

            return <code className={styles.inlineCode} {...props}>{children}</code>
        },
        pre: ({ children }) => {
            return <>{children}</>
        },
        table: ({ children, ...props }) => (
            <div className={styles.tableWrapper}>
                <table className={styles.table} {...props}>{children}</table>
            </div>
        ),
        thead: ({ children, ...props }) => (
            <thead className={styles.thead} {...props}>{children}</thead>
        ),
        th: ({ children, ...props }) => (
            <th className={styles.th} {...props}>{children}</th>
        ),
        td: ({ children, ...props }) => (
            <td className={styles.td} {...props}>{children}</td>
        ),
        tr: ({ children, ...props }) => (
            <tr className={styles.tr} {...props}>{children}</tr>
        ),
        blockquote: ({ children, ...props }) => (
            <blockquote className={styles.blockquote} {...props}>{children}</blockquote>
        ),
        ul: ({ children, ...props }) => (
            <ul className={styles.ul} {...props}>{children}</ul>
        ),
        ol: ({ children, ...props }) => (
            <ol className={styles.ol} {...props}>{children}</ol>
        ),
        li: ({ children, ...props }) => (
            <li className={styles.li} {...props}>{children}</li>
        ),
        hr: () => <hr className={styles.hr} />,
        strong: ({ children, ...props }) => (
            <strong className={styles.strong} {...props}>{children}</strong>
        ),
        em: ({ children, ...props }) => (
            <em className={styles.em} {...props}>{children}</em>
        ),
        del: ({ children, ...props }) => (
            <del className={styles.del} {...props}>{children}</del>
        ),
        input: ({ checked, ...props }) => (
            <span className={`${styles.checkbox} ${checked ? styles.checkboxChecked : ''}`}>
                {checked ? '✓' : ''}
            </span>
        ),
        div: ({ className, children, ...props }) => {
            if (className || props.align) {
                return (
                    <div
                        className={`${styles.htmlDiv} ${props.align === 'center' ? styles.center : ''}`}
                        {...props}
                    >
                        {children}
                    </div>
                )
            }
            return <div {...props}>{children}</div>
        },
    }), [])

    if (!content) return null

    return (
        <div className={styles.markdown}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={components}
            >
                {content}
            </ReactMarkdown>
        </div>
    )
}
