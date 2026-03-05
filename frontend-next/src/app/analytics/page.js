'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SystemStats from '@/components/SystemStats'
import styles from './page.module.css'

export default function AnalyticsPage() {
    const [services, setServices] = useState(null)
    const [assessments, setAssessments] = useState([])
    const [loading, setLoading] = useState(true)
    const [selectedAssessment, setSelectedAssessment] = useState(null)
    const [modalLoading, setModalLoading] = useState(false)
    const [deleteWarning, setDeleteWarning] = useState(null)
    const [dontAskAgain, setDontAskAgain] = useState(false)
    const [chromaStats, setChromaStats] = useState(null)
    const [reindexing, setReindexing] = useState(false)
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState(null)
    const [searching, setSearching] = useState(false)
    const [showFiles, setShowFiles] = useState(false)
    const router = useRouter()

    const openDetail = async (id) => {
        setModalLoading(true)
        setSelectedAssessment({ id, loading: true })
        try {
            const res = await fetch(`/api/iso27001/assessments/${id}`)
            if (res.ok) {
                const data = await res.json()
                setSelectedAssessment(data)
            } else {
                setSelectedAssessment({ id, error: 'Không tìm thấy dữ liệu' })
            }
        } catch {
            setSelectedAssessment({ id, error: 'Lỗi tải chi tiết' })
        } finally {
            setModalLoading(false)
        }
    }

    const handleReuse = () => {
        if (selectedAssessment && selectedAssessment.system_info) {
            localStorage.setItem('reuse_iso_form', JSON.stringify(selectedAssessment.system_info))
            router.push('/form-iso')
        }
    }

    const checkDeleteWarning = (id, e) => {
        e.stopPropagation() // Ngăn click nhầm vào mở row detail
        const suppressUntil = localStorage.getItem('skip_delete_warning_iso')
        if (suppressUntil && Date.now() < parseInt(suppressUntil)) {
            executeDelete(id)
        } else {
            setDeleteWarning(id)
        }
    }

    const executeDelete = async (id) => {
        try {
            const res = await fetch(`/api/iso27001/assessments/${id}`, { method: 'DELETE' })
            if (res.ok) {
                setAssessments(prev => prev.filter(a => a.id !== id))
                if (selectedAssessment?.id === id) setSelectedAssessment(null)
            }
        } catch (e) {
            console.error('Lỗi khi xóa:', e)
        } finally {
            setDeleteWarning(null)
        }
    }

    const confirmDelete = () => {
        if (dontAskAgain) {
            // Lấy thời gian hiện tại + 24 giờ (ms)
            const twentyFourHours = 24 * 60 * 60 * 1000
            localStorage.setItem('skip_delete_warning_iso', Date.now() + twentyFourHours)
        }
        executeDelete(deleteWarning)
    }

    useEffect(() => {
        async function fetchData() {
            try {
                const res = await fetch('/api/health')
                const backendReady = res.ok

                let localaiReady = false
                let models = []
                try {
                    const sysRes = await fetch('/api/system/stats')
                    if (sysRes.ok) localaiReady = true
                } catch { }

                try {
                    const assessRes = await fetch('/api/iso27001/assessments')
                    if (assessRes.ok) {
                        setAssessments(await assessRes.json())
                    }
                } catch { }

                try {
                    const chromaRes = await fetch('/api/iso27001/chromadb/stats')
                    if (chromaRes.ok) {
                        setChromaStats(await chromaRes.json())
                    }
                } catch { }

                setServices({
                    backend: { status: backendReady ? 'Running' : 'Offline', ready: backendReady },
                    localai: { status: localaiReady ? 'Ready' : 'Offline', ready: localaiReady },
                    models
                })
            } catch {
                setServices({
                    backend: { status: 'Offline', ready: false },
                    localai: { status: 'Offline', ready: false },
                    models: []
                })
            } finally {
                setLoading(false)
            }
        }
        fetchData()
        const interval = setInterval(fetchData, 15000)
        return () => clearInterval(interval)
    }, [])

    return (
        <div className="page-container">
            <div className={styles.header}>
                <h1 className={styles.title}>📊 Analytics Dashboard</h1>
                <p className={styles.subtitle}>Giám sát hiệu năng hệ thống và trạng thái dịch vụ real-time</p>
            </div>

            <section style={{ marginBottom: '2.5rem' }}>
                <h2 className="section-title">⚡ Tài nguyên Hệ thống</h2>
                <SystemStats />
            </section>

            <section style={{ marginBottom: '2.5rem' }}>
                <h2 className="section-title">🤖 Trạng thái Dịch vụ</h2>
                {loading ? (
                    <div className={styles.loading}>Đang tải...</div>
                ) : (
                    <div className="grid-2">
                        <div className={styles.serviceCard}>
                            <div className={styles.serviceHeader}>
                                <div>
                                    <div className={styles.serviceName}>
                                        {services?.backend?.ready ? '✅' : '⏳'} FastAPI Backend
                                    </div>
                                    <div className={styles.serviceDetail}>
                                        Core API Service • Port: <strong style={{ color: 'var(--accent-blue)' }}>8000</strong> • v1.0.0
                                    </div>
                                </div>
                                <span className={`status-badge ${services?.backend?.ready ? 'status-online' : 'status-offline'}`}>
                                    {services?.backend?.status}
                                </span>
                            </div>
                        </div>

                        <div className={styles.serviceCard}>
                            <div className={styles.serviceHeader}>
                                <div>
                                    <div className={styles.serviceName}>
                                        {services?.localai?.ready ? '🔥' : '⏳'} LocalAI Engine
                                    </div>
                                    <div className={styles.serviceDetail}>
                                        Model Server • Port: <strong style={{ color: 'var(--accent-blue)' }}>8080</strong> • CPU Mode
                                    </div>
                                </div>
                                <span className={`status-badge ${services?.localai?.ready ? 'status-online' : 'status-offline'}`}>
                                    {services?.localai?.status}
                                </span>
                            </div>
                        </div>

                        <div className={styles.serviceCard}>
                            <div className={styles.serviceHeader}>
                                <div>
                                    <div className={styles.serviceName}>
                                        {services?.backend?.ready ? '🗄️' : '⏳'} ChromaDB
                                    </div>
                                    <div className={styles.serviceDetail}>
                                        Vector Database • RAG ISO 27001 • <strong style={{ color: 'var(--accent-green)' }}>cosine</strong> space
                                    </div>
                                </div>
                                <span className={`status-badge ${services?.backend?.ready ? 'status-online' : 'status-offline'}`}>
                                    {services?.backend?.status}
                                </span>
                            </div>
                        </div>

                        <div className={styles.serviceCard}>
                            <div className={styles.serviceHeader}>
                                <div>
                                    <div className={styles.serviceName}>🧠 PhoBERT Model</div>
                                    <div className={styles.serviceDetail}>
                                        Vietnamese NLP • Parameters: <strong style={{ color: 'var(--accent-green)' }}>135M</strong>
                                    </div>
                                </div>
                                <span className="status-badge status-online">Active</span>
                            </div>
                        </div>

                        <div className={styles.serviceCard}>
                            <div className={styles.serviceHeader}>
                                <div>
                                    <div className={styles.serviceName}>⚡ Llama 3.1 8B</div>
                                    <div className={styles.serviceDetail}>
                                        LLM (General/Summary) • Quant: <strong style={{ color: 'var(--accent-amber)' }}>Q4_K_M</strong> • 4.9GB
                                    </div>
                                </div>
                                <span className={`status-badge ${services?.localai?.ready ? 'status-online' : 'status-loading'}`}>
                                    {services?.localai?.ready ? 'Ready' : 'Loading'}
                                </span>
                            </div>
                        </div>

                        <div className={styles.serviceCard}>
                            <div className={styles.serviceHeader}>
                                <div>
                                    <div className={styles.serviceName}>🛡️ SecurityLLM 7B</div>
                                    <div className={styles.serviceDetail}>
                                        LLM (ISO Assessor) • Quant: <strong style={{ color: 'var(--accent-amber)' }}>Q4_K_M</strong> • 4.4GB
                                    </div>
                                </div>
                                <span className={`status-badge ${services?.localai?.ready ? 'status-online' : 'status-loading'}`}>
                                    {services?.localai?.ready ? 'Ready' : 'Loading'}
                                </span>
                            </div>
                        </div>
                    </div>
                )}
            </section>

            <section style={{ marginBottom: '2.5rem' }}>
                <h2 className="section-title">🕒 Lịch sử Đánh giá ISO 27001</h2>
                <div className={styles.tableContainer}>
                    <table className={styles.table}>
                        <thead>
                            <tr>
                                <th>Thời gian</th>
                                <th>Tổ chức</th>
                                <th>Trạng thái</th>
                                <th>ID Giao dịch</th>
                                <th style={{ textAlign: 'right' }}>Thao tác</th>
                            </tr>
                        </thead>
                        <tbody>
                            {assessments.length > 0 ? assessments.map(a => (
                                <tr key={a.id} onClick={() => openDetail(a.id)} className={styles.tableRowRef}>
                                    <td>{new Date(a.created_at).toLocaleString('vi-VN')}</td>
                                    <td><strong>{a.org_name}</strong></td>
                                    <td>
                                        <span className={`status-badge ${a.status === 'completed' ? 'status-online' : a.status === 'processing' ? 'status-loading' : 'status-offline'}`}>
                                            {a.status.toUpperCase()}
                                        </span>
                                    </td>
                                    <td><code className={styles.codeId}>{a.id.split('-')[0]}</code></td>
                                    <td style={{ textAlign: 'right' }}>
                                        <button
                                            className={styles.deleteBtn}
                                            onClick={(e) => checkDeleteWarning(a.id, e)}
                                            title="Xóa đánh giá này"
                                        >
                                            🗑️
                                        </button>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="5" style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>Chưa có yêu cầu đánh giá nào.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            <section style={{ marginBottom: '2.5rem' }}>
                <h2 className="section-title">📈 Cấu hình Hệ thống</h2>
                <div className="grid-3">
                    <div className={styles.configCard}>
                        <div className={styles.configLabel}>Context Size</div>
                        <div className={styles.configValue}>8192</div>
                        <div className={styles.configUnit}>tokens</div>
                    </div>
                    <div className={styles.configCard}>
                        <div className={styles.configLabel}>Max Tokens</div>
                        <div className={styles.configValue}>Unlimited</div>
                        <div className={styles.configUnit}>không giới hạn</div>
                    </div>
                    <div className={styles.configCard}>
                        <div className={styles.configLabel}>Threads</div>
                        <div className={styles.configValue}>8</div>
                        <div className={styles.configUnit}>CPU threads</div>
                    </div>
                </div>
            </section>

            <section>
                <h2 className="section-title">🗄️ Kho Tài liệu AI — ChromaDB</h2>
                <div className={styles.chromaPanel}>
                    <div className={styles.chromaHeader}>
                        <div className={styles.chromaHeaderLeft}>
                            <div className={styles.chromaGrid}>
                                <div className={styles.chromaStat}>
                                    <span className={styles.chromaStatIcon}>🧩</span>
                                    <div>
                                        <span className={styles.chromaStatValue}>{chromaStats?.total_chunks ?? '--'}</span>
                                        <span className={styles.chromaStatLabel}>Chunks</span>
                                    </div>
                                </div>
                                <div className={styles.chromaStat}>
                                    <span className={styles.chromaStatIcon}>📄</span>
                                    <div>
                                        <span className={styles.chromaStatValue}>{chromaStats?.total_files ?? '--'}</span>
                                        <span className={styles.chromaStatLabel}>Files</span>
                                    </div>
                                </div>
                                <div className={styles.chromaStat}>
                                    <span className={styles.chromaStatIcon}>🎯</span>
                                    <div>
                                        <span className={styles.chromaStatValue} style={{ fontSize: '1rem', textTransform: 'uppercase' }}>{chromaStats?.metric ?? '--'}</span>
                                        <span className={styles.chromaStatLabel}>Metric</span>
                                    </div>
                                </div>
                            </div>
                            <div className={styles.chromaStatusRow}>
                                <span className={`${styles.chromaStatusDot} ${chromaStats?.status === 'ok' ? styles.dotOk : styles.dotErr}`} />
                                <span className={styles.chromaStatusText}>{chromaStats?.status === 'ok' ? 'Database sẵn sàng' : 'Đang kiểm tra...'}</span>
                                <button
                                    className={styles.btnReindex}
                                    disabled={reindexing}
                                    onClick={async () => {
                                        setReindexing(true)
                                        try {
                                            const res = await fetch('/api/iso27001/reindex', { method: 'POST' })
                                            if (res.ok) {
                                                const data = await res.json()
                                                alert(`Nạp lại thành công! ${data.files} files → ${data.chunks} chunks`)
                                                const r2 = await fetch('/api/iso27001/chromadb/stats')
                                                if (r2.ok) setChromaStats(await r2.json())
                                            }
                                        } catch (e) {
                                            alert('Lỗi: ' + e.message)
                                        } finally { setReindexing(false) }
                                    }}
                                >
                                    {reindexing ? '⏳ Đang nạp...' : '🔄 Nạp lại'}
                                </button>
                            </div>
                        </div>

                        <div className={styles.chromaHeaderRight}>
                            <div className={styles.searchBox}>
                                <input
                                    type="text"
                                    placeholder="Thử tìm kiếm tài liệu..."
                                    value={searchQuery}
                                    onChange={e => setSearchQuery(e.target.value)}
                                    className={styles.searchInput}
                                    onKeyDown={async (e) => {
                                        if (e.key === 'Enter' && searchQuery.trim()) {
                                            setSearching(true)
                                            try {
                                                const res = await fetch('/api/iso27001/chromadb/search', {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({ query: searchQuery, top_k: 3 })
                                                })
                                                if (res.ok) setSearchResults(await res.json())
                                            } catch { } finally { setSearching(false) }
                                        }
                                    }}
                                />
                                <button
                                    className={styles.btnSearch}
                                    disabled={searching || !searchQuery.trim()}
                                    onClick={async () => {
                                        if (!searchQuery.trim()) return
                                        setSearching(true)
                                        try {
                                            const res = await fetch('/api/iso27001/chromadb/search', {
                                                method: 'POST',
                                                headers: { 'Content-Type': 'application/json' },
                                                body: JSON.stringify({ query: searchQuery, top_k: 3 })
                                            })
                                            if (res.ok) setSearchResults(await res.json())
                                        } catch { } finally { setSearching(false) }
                                    }}
                                >{searching ? '⏳' : '🔍'}</button>
                            </div>
                            {searchResults?.results?.length > 0 && (
                                <div className={styles.searchResultsPanel}>
                                    {searchResults.results.map((r, i) => (
                                        <div key={i} className={styles.searchResultItem}>
                                            <div className={styles.searchResultHeader}>
                                                <span className={styles.searchResultSource}>{r.source}</span>
                                                <span className={styles.searchResultScore}>{(r.score * 100).toFixed(0)}%</span>
                                            </div>
                                            <p className={styles.searchResultText}>{r.text?.substring(0, 200)}...</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {chromaStats?.files?.length > 0 && (
                        <div className={styles.chromaFiles}>
                            <div className={styles.fileToggle} onClick={() => setShowFiles(!showFiles)}>
                                <span>{showFiles ? '▼' : '▶'} Danh sách tài liệu ({chromaStats.files.length} files)</span>
                                <span className={styles.fileTotalSize}>
                                    {(chromaStats.files.reduce((s, f) => s + f.size_bytes, 0) / 1024).toFixed(1)} KB
                                </span>
                            </div>
                            {showFiles && (
                                <div className={styles.fileList}>
                                    {chromaStats.files.map((f, i) => (
                                        <div key={i} className={styles.fileItem}>
                                            <span className={styles.fileName}>{f.name}</span>
                                            <span className={styles.fileSize}>{(f.size_bytes / 1024).toFixed(1)} KB</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </section>

            {selectedAssessment && (
                <div className={styles.modalOverlay} onClick={() => setSelectedAssessment(null)}>
                    <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
                        <div className={styles.modalHeader}>
                            <h3 className={styles.modalTitle}>Chi tiết Đánh giá: <code className={styles.codeId}>{selectedAssessment.id?.split('-')[0]}</code></h3>
                            <button className={styles.closeBtn} onClick={() => setSelectedAssessment(null)}>✕</button>
                        </div>
                        <div className={styles.modalBody}>
                            {modalLoading || selectedAssessment.loading ? (
                                <div className={styles.loading}>Đang tải chi tiết...</div>
                            ) : selectedAssessment.error ? (
                                <div className={styles.statusError}>{selectedAssessment.error}</div>
                            ) : (
                                <>
                                    <div className={styles.systemSummary}>
                                        <p><strong>🏢 Tổ chức:</strong> {selectedAssessment.system_info?.organization?.name}
                                            &nbsp;({selectedAssessment.system_info?.organization?.employees} NV, {selectedAssessment.system_info?.infrastructure?.servers} Servers)</p>
                                        <p><strong>Trạng thái trước đây:</strong> {selectedAssessment.system_info?.compliance?.iso_status}</p>
                                    </div>
                                    <div className={styles.md}>
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {selectedAssessment.result?.report || 'Chưa có báo cáo chi tiết'}
                                        </ReactMarkdown>
                                    </div>
                                </>
                            )}
                            {selectedAssessment.status === 'failed' && (
                                <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', borderLeft: '3px solid var(--accent-red)', borderRadius: '4px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                    <strong>💡 Lưu ý:</strong> Đây là bản nháp lịch sử đã bị lỗi từ hệ thống cũ. Hãy click <b>&quot;Tái sử dụng Form này&quot;</b> để tự động nhập lại thông tin và chạy đánh giá trên hệ thống mới đã được tối ưu.
                                </div>
                            )}
                        </div>
                        <div className={styles.modalFooter}>
                            <button className={styles.btnSecondary} onClick={() => setSelectedAssessment(null)}>Đóng</button>
                            <button className={styles.btnPrimary} onClick={handleReuse}>♻️ Tái sử dụng Form này</button>
                        </div>
                    </div>
                </div>
            )}

            {deleteWarning && (
                <div className={styles.modalOverlay} onClick={() => setDeleteWarning(null)}>
                    <div className={`${styles.modalContent} ${styles.modalSmall}`} onClick={e => e.stopPropagation()}>
                        <div className={styles.modalHeader}>
                            <h3 className={styles.modalTitle} style={{ color: 'var(--accent-red)' }}>⚠️ Xác nhận Xóa</h3>
                            <button className={styles.closeBtn} onClick={() => setDeleteWarning(null)}>✕</button>
                        </div>
                        <div className={styles.modalBody} style={{ paddingBottom: '0.5rem' }}>
                            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', lineHeight: '1.5' }}>
                                Bạn có chắc chắn muốn xóa vĩnh viễn báo cáo đánh giá này không? Hành động này không thể hoàn tác.
                            </p>
                            <label className={styles.checkboxLabel}>
                                <input
                                    type="checkbox"
                                    checked={dontAskAgain}
                                    onChange={(e) => setDontAskAgain(e.target.checked)}
                                />
                                <span>Không hiển thị lại thông báo này trong 24 giờ tới</span>
                            </label>
                        </div>
                        <div className={styles.modalFooter}>
                            <button className={styles.btnSecondary} onClick={() => setDeleteWarning(null)}>Hủy bỏ</button>
                            <button className={styles.btnDanger} onClick={confirmDelete}>Xóa vĩnh viễn</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
