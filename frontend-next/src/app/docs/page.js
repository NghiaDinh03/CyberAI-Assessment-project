'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import styles from './page.module.css'
import {
    BookOpen, Code2, ExternalLink, Search, Shield, Zap, Terminal,
    Layers, Copy, Check, Server, FileText, CheckCircle2, Lock, Cpu
} from 'lucide-react'
import { useTranslation } from '@/components/LanguageProvider'

const BACKEND_PUBLIC_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const METHOD_COLORS = {
    GET: { bg: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa', border: 'rgba(59, 130, 246, 0.4)' },
    POST: { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: 'rgba(16, 185, 129, 0.4)' },
    PUT: { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.4)' },
    DELETE: { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.4)' },
    PATCH: { bg: 'rgba(168, 85, 247, 0.15)', text: '#c084fc', border: 'rgba(168, 85, 247, 0.4)' },
}

export default function SwaggerDocsPage() {
    const { t, locale } = useTranslation()
    const [spec, setSpec] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [activeTab, setActiveTab] = useState('catalog') // 'catalog' | 'swagger' | 'guide'
    const [searchQuery, setSearchQuery] = useState('')
    const [selectedTag, setSelectedTag] = useState('all')
    const [selectedMethod, setSelectedMethod] = useState('all')
    const [copiedPath, setCopiedPath] = useState(null)

    useEffect(() => {
        async function fetchSpec() {
            try {
                setLoading(true)
                const res = await fetch('/api/openapi')
                if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load OpenAPI schema`)
                const data = await res.json()
                setSpec(data)
            } catch (err) {
                setError(err.message)
            } finally {
                setLoading(false)
            }
        }
        fetchSpec()
    }, [])

    // Parse endpoints from OpenAPI paths
    const endpoints = useMemo(() => {
        if (!spec || !spec.paths) return []
        const list = []
        for (const [path, methods] of Object.entries(spec.paths)) {
            for (const [method, details] of Object.entries(methods)) {
                if (['get', 'post', 'put', 'delete', 'patch'].includes(method.toLowerCase())) {
                    list.push({
                        path,
                        method: method.toUpperCase(),
                        summary: details.summary || details.description || path,
                        description: details.description || '',
                        tags: details.tags || ['Default'],
                        parameters: details.parameters || [],
                        requestBody: details.requestBody,
                        responses: details.responses || {},
                        operationId: details.operationId || `${method}_${path}`,
                    })
                }
            }
        }
        return list
    }, [spec])

    // Distinct tags
    const allTags = useMemo(() => {
        const set = new Set()
        endpoints.forEach(e => e.tags.forEach(t => set.add(t)))
        return Array.from(set).sort()
    }, [endpoints])

    // Filtered endpoints
    const filteredEndpoints = useMemo(() => {
        return endpoints.filter(ep => {
            if (selectedTag !== 'all' && !ep.tags.includes(selectedTag)) return false
            if (selectedMethod !== 'all' && ep.method !== selectedMethod) return false
            if (searchQuery.trim()) {
                const q = searchQuery.toLowerCase()
                const matchPath = ep.path.toLowerCase().includes(q)
                const matchSummary = ep.summary.toLowerCase().includes(q)
                const matchTag = ep.tags.some(t => t.toLowerCase().includes(q))
                if (!matchPath && !matchSummary && !matchTag) return false
            }
            return true
        })
    }, [endpoints, selectedTag, selectedMethod, searchQuery])

    const copyToClipboard = (text, key) => {
        navigator.clipboard.writeText(text)
        setCopiedPath(key)
        setTimeout(() => setCopiedPath(null), 2000)
    }

    return (
        <div className="page-container">
            {/* ── Header ── */}
            <div className={styles.header}>
                <div className={styles.headerLeft}>
                    <div className={styles.badgeRow}>
                        <span className={styles.apiBadge}>FastAPI OpenAPI 3.1</span>
                        <span className={styles.liveBadge}>🟢 Service Online</span>
                    </div>
                    <h1 className={styles.title}>
                        <Code2 size={26} className={styles.titleIcon} />
                        {locale === 'vi' ? 'Tài Liệu Swagger & OpenAPI Hub' : 'Swagger & OpenAPI Documentation'}
                    </h1>
                    <p className={styles.subtitle}>
                        {locale === 'vi'
                            ? 'Trung tâm tài liệu tương tác và kiểm thử toàn bộ REST API của hệ thống CyberAI (Chatbot, Thẩm định ISO 27001, Document Parsing, AI Models, Templates).'
                            : 'Interactive API explorer and live documentation for all CyberAI backend services.'}
                    </p>
                </div>

                <div className={styles.headerActions}>
                    <a
                        href={`${BACKEND_PUBLIC_URL}/docs`}
                        target="_blank"
                        rel="noreferrer"
                        className={styles.actionBtnPrimary}
                    >
                        <ExternalLink size={15} />
                        {locale === 'vi' ? 'Mở Swagger UI Gốc' : 'Open Native Swagger'}
                    </a>
                    <a
                        href={`${BACKEND_PUBLIC_URL}/redoc`}
                        target="_blank"
                        rel="noreferrer"
                        className={styles.actionBtnSecondary}
                    >
                        <FileText size={15} />
                        ReDoc View
                    </a>
                </div>
            </div>

            {/* ── Stats Strip ── */}
            <div className={styles.statsStrip}>
                <div className={styles.statCard}>
                    <span className={styles.statLabel}>Tổng số API Endpoints</span>
                    <span className={styles.statVal}>{endpoints.length || '—'}</span>
                </div>
                <div className={styles.statCard}>
                    <span className={styles.statLabel}>Nhóm Tính Năng (Modules)</span>
                    <span className={styles.statVal}>{allTags.length || '—'}</span>
                </div>
                <div className={styles.statCard}>
                    <span className={styles.statLabel}>Local AI Engine</span>
                    <span className={styles.statVal}>Ollama Gemma 4</span>
                </div>
                <div className={styles.statCard}>
                    <span className={styles.statLabel}>Chuẩn Xác Thực</span>
                    <span className={styles.statVal}>JWT Bearer + RBAC</span>
                </div>
            </div>

            {/* ── View Switcher Tabs ── */}
            <div className={styles.tabsBar}>
                <button
                    className={`${styles.tabBtn} ${activeTab === 'catalog' ? styles.tabBtnActive : ''}`}
                    onClick={() => setActiveTab('catalog')}
                >
                    <Layers size={16} />
                    {locale === 'vi' ? 'Danh Mục Endpoint Chi Tiết' : 'Endpoints Catalog'}
                </button>
                <button
                    className={`${styles.tabBtn} ${activeTab === 'swagger' ? styles.tabBtnActive : ''}`}
                    onClick={() => setActiveTab('swagger')}
                >
                    <Terminal size={16} />
                    {locale === 'vi' ? 'Giao Diện Swagger UI Trực Tiếp' : 'Embedded Swagger UI'}
                </button>
                <button
                    className={`${styles.tabBtn} ${activeTab === 'guide' ? styles.tabBtnActive : ''}`}
                    onClick={() => setActiveTab('guide')}
                >
                    <BookOpen size={16} />
                    {locale === 'vi' ? 'Hướng Dẫn Tích Hợp & Auth' : 'Integration & Auth Guide'}
                </button>
            </div>

            {/* ── TAB 1: Endpoints Catalog ── */}
            {activeTab === 'catalog' && (
                <div className={styles.catalogWrap}>
                    {/* Search & Filters */}
                    <div className={styles.filterRow}>
                        <div className={styles.searchBox}>
                            <Search size={16} className={styles.searchIcon} />
                            <input
                                type="text"
                                placeholder={locale === 'vi' ? 'Tìm kiếm theo đường dẫn path, tag hoặc mô tả tóm tắt...' : 'Search by path, tag, or summary...'}
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                className={styles.searchInput}
                            />
                            {searchQuery && (
                                <button className={styles.searchClear} onClick={() => setSearchQuery('')}>✕</button>
                            )}
                        </div>

                        <div className={styles.filterGroup}>
                            <select
                                value={selectedTag}
                                onChange={e => setSelectedTag(e.target.value)}
                                className={styles.selectFilter}
                            >
                                <option value="all">{locale === 'vi' ? 'Tất cả nhóm Tag' : 'All Tags'} ({allTags.length})</option>
                                {allTags.map(tag => (
                                    <option key={tag} value={tag}>{tag}</option>
                                ))}
                            </select>

                            <select
                                value={selectedMethod}
                                onChange={e => setSelectedMethod(e.target.value)}
                                className={styles.selectFilter}
                            >
                                <option value="all">{locale === 'vi' ? 'Tất cả Method' : 'All Methods'}</option>
                                <option value="GET">GET</option>
                                <option value="POST">POST</option>
                                <option value="PUT">PUT</option>
                                <option value="DELETE">DELETE</option>
                            </select>
                        </div>
                    </div>

                    {/* Results Counter */}
                    <div className={styles.resultsMeta}>
                        <span>Hiển thị <strong>{filteredEndpoints.length}</strong> / {endpoints.length} endpoints</span>
                    </div>

                    {/* Endpoints List */}
                    {loading ? (
                        <div className={styles.loadingBox}>
                            <span className={styles.spinner} />
                            <span>Đang tải danh sách đặc tả OpenAPI từ Backend...</span>
                        </div>
                    ) : filteredEndpoints.length === 0 ? (
                        <div className={styles.emptyBox}>
                            <span>Không tìm thấy endpoint phù hợp với bộ lọc.</span>
                        </div>
                    ) : (
                        <div className={styles.endpointList}>
                            {filteredEndpoints.map((ep, idx) => {
                                const methodStyle = METHOD_COLORS[ep.method] || METHOD_COLORS.GET
                                const itemKey = `${ep.method}_${ep.path}_${idx}`
                                const isCopied = copiedPath === itemKey

                                return (
                                    <div key={itemKey} className={styles.endpointCard}>
                                        <div className={styles.endpointHeader}>
                                            <div className={styles.endpointLeft}>
                                                <span
                                                    className={styles.methodBadge}
                                                    style={{
                                                        backgroundColor: methodStyle.bg,
                                                        color: methodStyle.text,
                                                        borderColor: methodStyle.border
                                                    }}
                                                >
                                                    {ep.method}
                                                </span>
                                                <code className={styles.pathCode}>{ep.path}</code>
                                                <button
                                                    type="button"
                                                    className={styles.copyBtn}
                                                    onClick={() => copyToClipboard(`curl -X ${ep.method} "${BACKEND_PUBLIC_URL}${ep.path}"`, itemKey)}
                                                    title="Copy cURL command"
                                                >
                                                    {isCopied ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
                                                </button>
                                            </div>

                                            <div className={styles.tagChips}>
                                                {Array.from(new Set(ep.tags || [])).map((t, tIdx) => (
                                                    <span key={`${t}-${tIdx}`} className={styles.tagChip}>{t}</span>
                                                ))}
                                            </div>
                                        </div>

                                        <p className={styles.endpointSummary}>{ep.summary}</p>

                                        {/* Parameter Pills */}
                                        {ep.parameters && ep.parameters.length > 0 && (
                                            <div className={styles.paramSection}>
                                                <span className={styles.paramLabel}>Tham số (Parameters):</span>
                                                <div className={styles.paramList}>
                                                    {ep.parameters.map((p, pIdx) => (
                                                        <span key={pIdx} className={styles.paramPill}>
                                                            <code>{p.name}</code>
                                                            <small>({p.in}{p.required ? ' *' : ''})</small>
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            )}

            {/* ── TAB 2: Embedded Swagger UI ── */}
            {activeTab === 'swagger' && (
                <div className={styles.iframeContainer}>
                    <iframe
                        src={`${BACKEND_PUBLIC_URL}/docs`}
                        className={styles.swaggerIframe}
                        title="FastAPI Swagger UI"
                    />
                </div>
            )}

            {/* ── TAB 3: Integration & Auth Guide ── */}
            {activeTab === 'guide' && (
                <div className={styles.guideWrap}>
                    <div className={styles.guideCard}>
                        <h3>🔒 1. Cơ Chế Xác Thực & Phân Quyền (Authentication)</h3>
                        <p>
                            Toàn bộ API yêu cầu xác thực sử dụng tiêu chuẩn <strong>JWT Bearer Token</strong>. Sau khi đăng nhập qua endpoint <code>POST /api/auth/login</code>, gửi token trong header của mọi request:
                        </p>
                        <pre className={styles.codeBlock}>
                            {`Authorization: Bearer <your_jwt_access_token>`}
                        </pre>
                    </div>

                    <div className={styles.guideCard}>
                        <h3>⚡ 2. Gọi Thẩm Định Tự Động (Assessment API)</h3>
                        <p>
                            Gửi yêu cầu đánh giá an toàn thông tin theo tiêu chuẩn ISO 27001 / TCVN 11930 qua endpoint nền:
                        </p>
                        <pre className={styles.codeBlock}>
                            {`POST /api/iso27001/assess
Content-Type: application/json

{
  "org_name": "Công ty Nhiệt điện Thủ Đức - EVN TPC",
  "assessment_standard": "tcvn11930",
  "model_mode": "local",
  "selected_model": "gemma4:latest",
  "employees": 320,
  "servers": 9,
  "implemented_controls": ["A.5.1", "A.8.20", "A.8.24"]
}`}
                        </pre>
                    </div>

                    <div className={styles.guideCard}>
                        <h3>📂 3. Định Dạng Upload Hồ Sơ Bằng Chứng (Evidence Ingestion)</h3>
                        <p>
                            Hệ thống tự động bóc tách và phân tích các định dạng:
                        </p>
                        <div className={styles.formatGrid}>
                            <div className={styles.formatItem}>
                                <strong>Word (.docx)</strong>
                                <span>Báo cáo kiểm thử, Báo cáo rà quét lỗ hổng IT Audit</span>
                            </div>
                            <div className={styles.formatItem}>
                                <strong>Log & Shell (.txt, .log, .ps1, .sh)</strong>
                                <span>Output lệnh systeminfo, Get-Hotfix, Nmap, Firewall logs</span>
                            </div>
                            <div className={styles.formatItem}>
                                <strong>Excel / CSV (.xlsx, .csv)</strong>
                                <span>Danh mục tài sản CNTT, Bảng tổng hợp CVE CVSS</span>
                            </div>
                            <div className={styles.formatItem}>
                                <strong>PDF & Config (.pdf, .json, .yaml, .conf)</strong>
                                <span>Chính sách an toàn thông tin, File cấu hình máy chủ</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
