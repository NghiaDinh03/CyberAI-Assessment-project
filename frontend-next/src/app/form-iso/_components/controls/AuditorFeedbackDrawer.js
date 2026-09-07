'use client'

import { useState, useEffect, useCallback } from 'react'
import styles from './AuditorFeedbackDrawer.module.css'
import { useTranslation } from '@/components/LanguageProvider'

export default function AuditorFeedbackDrawer({
    isOpen,
    onClose,
    activeStandard = 'iso27001',
    initialControlId = '',
}) {
    const { locale } = useTranslation()
    const [activeTab, setActiveTab] = useState('list')
    const [loading, setLoading] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [feedbackList, setFeedbackList] = useState([])
    const [filterCtrl, setFilterCtrl] = useState('')

    // Form states for adding a new Golden Case
    const [controlId, setControlId] = useState(initialControlId || '')
    const [expertVerdict, setExpertVerdict] = useState('compliant')
    const [expertRationale, setExpertRationale] = useState('')
    const [inputFactSummary, setInputFactSummary] = useState('')
    const [errorMsg, setErrorMsg] = useState('')
    const [successMsg, setSuccessMsg] = useState('')

    useEffect(() => {
        if (initialControlId) {
            setControlId(initialControlId)
            setFilterCtrl(initialControlId)
        }
    }, [initialControlId])

    const fetchFeedbacks = useCallback(async () => {
        setLoading(true)
        try {
            const url = filterCtrl.trim()
                ? `/api/iso27001/feedback/${encodeURIComponent(filterCtrl.trim())}?standard=${activeStandard}`
                : `/api/iso27001/feedback?standard=${activeStandard}`
            const res = await fetch(url)
            if (res.ok) {
                const data = await res.json()
                setFeedbackList(data.feedbacks || [])
            }
        } catch (err) {
            console.error('[AuditorFeedback] Load error:', err)
        } finally {
            setLoading(false)
        }
    }, [filterCtrl, activeStandard])

    useEffect(() => {
        if (isOpen) {
            fetchFeedbacks()
            setErrorMsg('')
            setSuccessMsg('')
        }
    }, [isOpen, fetchFeedbacks])

    const handleSubmitNewCase = async (e) => {
        e.preventDefault()
        if (!controlId.trim() || !expertRationale.trim()) {
            setErrorMsg(locale === 'vi' ? 'Vui lòng nhập Mã Biện Pháp và Lý Do Phán Quyết.' : 'Please provide Control ID and Expert Rationale.')
            return
        }

        setSubmitting(true)
        setErrorMsg('')
        setSuccessMsg('')

        try {
            const payload = {
                control_id: controlId.trim().toUpperCase(),
                expert_verdict: expertVerdict,
                expert_rationale: expertRationale.trim(),
                input_fact_summary: inputFactSummary.trim(),
                standard: activeStandard,
                auditor_username: 'lead_auditor',
            }

            const res = await fetch('/api/iso27001/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })

            if (!res.ok) {
                const errData = await res.json()
                throw new Error(errData.detail || 'Lưu thất bại')
            }

            setSuccessMsg(locale === 'vi' ? 'Đã lưu phán quyết mẫu vào Kho Tri Thức thành công!' : 'Saved Golden Case successfully!')
            setExpertRationale('')
            setInputFactSummary('')
            fetchFeedbacks()
            setTimeout(() => {
                setActiveTab('list')
                setSuccessMsg('')
            }, 1200)
        } catch (err) {
            setErrorMsg(err.message || 'Error saving feedback')
        } finally {
            setSubmitting(false)
        }
    }

    const handleDeleteCase = async (id) => {
        if (!confirm(locale === 'vi' ? 'Xác nhận xóa phán quyết kiểm toán mẫu này?' : 'Delete this Golden Case?')) return
        try {
            const res = await fetch(`/api/iso27001/feedback/${encodeURIComponent(id)}`, { method: 'DELETE' })
            if (res.ok) {
                setFeedbackList(prev => prev.filter(item => item.id !== id))
            }
        } catch (err) {
            console.error('[AuditorFeedback] Delete error:', err)
        }
    }

    if (!isOpen) return null

    return (
        <div className={styles.backdrop} onClick={onClose}>
            <div className={styles.drawer} onClick={(e) => e.stopPropagation()}>
                <div className={styles.header}>
                    <div className={styles.titleGroup}>
                        <span className={styles.icon}>⚖️</span>
                        <div>
                            <h3 className={styles.title}>
                                {locale === 'vi' ? 'Kho Tri Thức Kiểm Toán (Golden Cases)' : 'Auditor Few-Shot Knowledge'}
                            </h3>
                            <p className={styles.subtitle}>
                                {locale === 'vi'
                                    ? 'Lưu trữ các mẫu phán quyết chuẩn của Lead Auditor để AI học tập và đối soát chính xác'
                                    : 'Exemplar audit verdicts stored for dynamic few-shot in-context learning'}
                            </p>
                        </div>
                    </div>
                    <button type="button" className={styles.closeBtn} onClick={onClose}>✕</button>
                </div>

                <div className={styles.tabRow}>
                    <button
                        type="button"
                        className={`${styles.tabBtn} ${activeTab === 'list' ? styles.tabBtnActive : ''}`}
                        onClick={() => setActiveTab('list')}
                    >
                        📚 {locale === 'vi' ? `Danh Sách Phán Quyết (${feedbackList.length})` : `Golden Cases (${feedbackList.length})`}
                    </button>
                    <button
                        type="button"
                        className={`${styles.tabBtn} ${activeTab === 'add' ? styles.tabBtnActive : ''}`}
                        onClick={() => setActiveTab('add')}
                    >
                        ➕ {locale === 'vi' ? 'Thêm Phán Quyết Mẫu Mới' : 'Add Golden Case'}
                    </button>
                </div>

                <div className={styles.body}>
                    {activeTab === 'add' ? (
                        <form className={styles.formCard} onSubmit={handleSubmitNewCase}>
                            {errorMsg && <div style={{ color: '#f87171', fontSize: '0.85rem' }}>⚠️ {errorMsg}</div>}
                            {successMsg && <div style={{ color: '#34d399', fontSize: '0.85rem' }}>✅ {successMsg}</div>}

                            <div className={styles.formGroup}>
                                <label className={styles.label}>{locale === 'vi' ? 'Mã Biện Pháp (Control ID):' : 'Control ID:'}</label>
                                <input
                                    type="text"
                                    className={styles.input}
                                    placeholder="Ví dụ: A.8.8 hoặc A.5.1"
                                    value={controlId}
                                    onChange={(e) => setControlId(e.target.value)}
                                    required
                                />
                            </div>

                            <div className={styles.formGroup}>
                                <label className={styles.label}>{locale === 'vi' ? 'Phán Quyết Của Chuyên Gia (Verdict):' : 'Expert Verdict:'}</label>
                                <select
                                    className={styles.select}
                                    value={expertVerdict}
                                    onChange={(e) => setExpertVerdict(e.target.value)}
                                >
                                    <option value="compliant">🟢 COMPLIANT — Đạt yêu cầu (Tích xanh)</option>
                                    <option value="non_compliant">🔴 NON_COMPLIANT — Chưa đạt / Rủi ro (Tích đỏ)</option>
                                    <option value="partial">🟡 PARTIAL — Đạt một phần / Cần khắc phục (Vàng)</option>
                                </select>
                            </div>

                            <div className={styles.formGroup}>
                                <label className={styles.label}>{locale === 'vi' ? 'Lý Do Phán Quyết (Expert Rationale):' : 'Auditor Rationale:'}</label>
                                <textarea
                                    className={styles.textarea}
                                    placeholder={locale === 'vi' ? 'Nêu rõ căn cứ tiêu chuẩn và lý do đưa ra kết luận này...' : 'Detailed audit justification...'}
                                    value={expertRationale}
                                    onChange={(e) => setExpertRationale(e.target.value)}
                                    rows={3}
                                    required
                                />
                            </div>

                            <div className={styles.formGroup}>
                                <label className={styles.label}>{locale === 'vi' ? 'Bối Cảnh Bằng Chứng Mẫu (Evidence Fact Summary - Tùy chọn):' : 'Evidence Fact Context:'}</label>
                                <textarea
                                    className={styles.textarea}
                                    placeholder={locale === 'vi' ? 'Mô tả tóm tắt tình trạng máy chủ hoặc minh chứng...' : 'Observed evidence facts...'}
                                    value={inputFactSummary}
                                    onChange={(e) => setInputFactSummary(e.target.value)}
                                    rows={2}
                                />
                            </div>

                            <button type="submit" className={styles.submitBtn} disabled={submitting}>
                                {submitting ? '⏳ Đang lưu...' : '💾 Lưu Vào Kho Tri Thức'}
                            </button>
                        </form>
                    ) : (
                        <>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                <input
                                    type="text"
                                    className={styles.input}
                                    placeholder={locale === 'vi' ? 'Lọc theo mã control (vd: A.8.8)...' : 'Filter by control ID...'}
                                    value={filterCtrl}
                                    onChange={(e) => setFilterCtrl(e.target.value)}
                                />
                                {filterCtrl && (
                                    <button
                                        type="button"
                                        style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                                        onClick={() => setFilterCtrl('')}
                                    >✕</button>
                                )}
                            </div>

                            {loading ? (
                                <div className={styles.emptyBox}>⏳ Đang tải kho tri thức kiểm toán...</div>
                            ) : feedbackList.length === 0 ? (
                                <div className={styles.emptyBox}>
                                    Chưa có phán quyết mẫu nào được ghi nhận. Bấm vào tab <strong>➕ Thêm Phán Quyết Mẫu</strong> để tạo mẫu đầu tiên.
                                </div>
                            ) : (
                                <div className={styles.cardList}>
                                    {feedbackList.map((item) => {
                                        const verdict = (item.expert_verdict || '').toLowerCase()
                                        const verdictClass = verdict === 'compliant'
                                            ? styles.verdictPass
                                            : verdict === 'non_compliant'
                                                ? styles.verdictFail
                                                : styles.verdictPartial

                                        return (
                                            <div key={item.id} className={styles.caseCard}>
                                                <div className={styles.cardHeader}>
                                                    <span className={styles.controlBadge}>{item.control_id}</span>
                                                    <span className={`${styles.verdictBadge} ${verdictClass}`}>
                                                        {item.expert_verdict}
                                                    </span>
                                                </div>
                                                <p className={styles.rationale}>{item.expert_rationale}</p>
                                                {item.input_fact_summary && (
                                                    <div className={styles.factSnippet}>
                                                        Minh chứng: {item.input_fact_summary}
                                                    </div>
                                                )}
                                                <div className={styles.cardFooter}>
                                                    <span>Auditor: {item.auditor_username || 'Lead Auditor'} · {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}</span>
                                                    <button
                                                        type="button"
                                                        className={styles.deleteBtn}
                                                        onClick={() => handleDeleteCase(item.id)}
                                                    >
                                                        🗑️ Xóa
                                                    </button>
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}
