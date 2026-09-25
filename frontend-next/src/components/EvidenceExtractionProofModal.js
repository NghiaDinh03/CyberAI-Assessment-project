'use client'

import React, { useState, useEffect } from 'react'
import styles from './EvidenceExtractionProofModal.module.css'

function renderFinalVerdictBadge(finalVerdict, styles) {
    const v = (finalVerdict || '').toLowerCase()
    if (v === 'satisfied') {
        return <span className={styles.verdictPass}>✓ ĐẠT</span>
    }
    if (v === 'partial') {
        return <span style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: '1px solid rgba(234, 179, 8, 0.35)', fontSize: '0.72rem', fontWeight: 700, padding: '2px 7px', borderRadius: '4px' }}>~ BÁN PHẦN</span>
    }
    if (v === 'needs_expert_review') {
        return <span style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(251, 146, 60, 0.15)', color: '#fb923c', border: '1px solid rgba(251, 146, 60, 0.35)', fontSize: '0.72rem', fontWeight: 700, padding: '2px 7px', borderRadius: '4px' }}>🟠 CHỜ RÀ SOÁT</span>
    }
    if (v === 'missing') {
        return <span className={styles.verdictFail}>✕ THIẾU</span>
    }
    if (v === 'not_evidenced') {
        return <span className={styles.verdictFail}>✕ CHƯA BẰNG CHỨNG</span>
    }
    return <span className={styles.verdictFail}>✕ {finalVerdict || 'CHƯA ĐẠT'}</span>
}

function renderTechnicalResultBadge(techResult) {
    if (techResult === 'Khớp bằng chứng kỹ thuật') {
        return <span style={{ color: '#38bdf8', fontSize: '0.78rem', fontWeight: 600 }}>🔍 Khớp bằng chứng</span>
    }
    if (techResult === 'Mâu thuẫn log kỹ thuật') {
        return <span style={{ color: '#f87171', fontSize: '0.78rem', fontWeight: 600 }}>⚠️ Mâu thuẫn log</span>
    }
    return <span style={{ color: '#94a3b8', fontSize: '0.78rem', fontStyle: 'italic' }}>Chưa có log đối chứng</span>
}

export default function EvidenceExtractionProofModal({ isOpen, onClose, assessmentId, initialData }) {
    const [activeTab, setActiveTab] = useState('facts')
    const [proofData, setProofData] = useState(initialData || null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (!isOpen) return
        if (initialData) {
            setProofData(initialData)
            return
        }
        if (assessmentId) {
            setLoading(true)
            fetch(`/api/iso27001/assessments/${assessmentId}/extraction-proof`)
                .then(res => res.json())
                .then(data => {
                    if (data && !data.error) {
                        setProofData(data)
                    }
                })
                .catch(err => console.error('Error loading extraction proof:', err))
                .finally(() => setLoading(false))
        }
    }, [isOpen, assessmentId, initialData])

    if (!isOpen) return null

    const dataSource = proofData?.data_source || (proofData?.manifest_files && proofData.manifest_files.length > 0 ? 'uploaded_evidence' : (proofData?.template_name || proofData?.template_id ? 'template_sample' : 'no_evidence'))
    const isTemplatePreview = dataSource === 'template_sample'
    const isNoEvidence = dataSource === 'no_evidence'
    const isUploaded = dataSource === 'uploaded_evidence'

    const facts = proofData?.technical_facts || {}
    const manifestFiles = proofData?.manifest_files || []
    const crossVerify = proofData?.cross_verification || {
        contradiction_gaps: [],
        verified_satisfied: [],
        unverified_oversights: []
    }

    const hasFacts = Boolean(
        facts.hostname ||
        (facts.hotfixes && facts.hotfixes.length > 0) ||
        (facts.open_ports && facts.open_ports.length > 0) ||
        (facts.antivirus && facts.antivirus.length > 0) ||
        (facts.security_deficiencies && facts.security_deficiencies.length > 0) ||
        (facts.security_strengths && facts.security_strengths.length > 0)
    )

    const hasCrossVerify = Boolean(
        (crossVerify.contradiction_gaps && crossVerify.contradiction_gaps.length > 0) ||
        (crossVerify.verified_satisfied && crossVerify.verified_satisfied.length > 0) ||
        (crossVerify.unverified_oversights && crossVerify.unverified_oversights.length > 0)
    )

    return (
        <div className={styles.overlay} onClick={onClose}>
            <div className={styles.modalContainer} onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className={styles.modalHeader}>
                    <div className={styles.headerLeft}>
                        <div className={styles.shieldIconBadge}>
                            {isUploaded ? '🛡️' : isTemplatePreview ? '📋' : '⚠️'}
                        </div>
                        <div className={styles.headerTextGroup}>
                            <h3>
                                Chứng minh Bóc tách Minh chứng Kỹ thuật
                                {isUploaded && (
                                    <span className={styles.integrityBadge}>
                                        ✓ Toàn vẹn 100.0% ({manifestFiles.length} tệp)
                                    </span>
                                )}
                                {isTemplatePreview && (
                                    <span style={{ background: 'rgba(234, 179, 8, 0.15)', border: '1px solid rgba(234, 179, 8, 0.4)', color: '#fde047', fontSize: '0.72rem', padding: '3px 8px', borderRadius: '6px', fontWeight: 600 }}>
                                        Dữ liệu mẫu từ template ({proofData?.template_name || proofData?.template_id || 'Mẫu'})
                                    </span>
                                )}
                                {isNoEvidence && (
                                    <span style={{ background: 'rgba(148, 163, 184, 0.15)', border: '1px solid rgba(148, 163, 184, 0.3)', color: '#cbd5e1', fontSize: '0.72rem', padding: '3px 8px', borderRadius: '6px', fontWeight: 600 }}>
                                        Tự khai báo không tệp (0 tệp minh chứng)
                                    </span>
                                )}
                            </h3>
                            <p>
                                {isUploaded
                                    ? `Đối soát minh chứng thực tế: Manifest ID [${proofData?.evidence_manifest_id || assessmentId}] — SHA-256 Checksum & Fact Cards`
                                    : isTemplatePreview
                                    ? 'Cấu hình tham khảo từ template — Không phải minh chứng tải lên thực tế để chấm điểm'
                                    : 'Lượt đánh giá này hoàn toàn dựa trên thông tin tự kê khai, chưa đính kèm tệp kỹ thuật đối chứng'}
                            </p>
                        </div>
                    </div>
                    <button className={styles.closeBtn} onClick={onClose}>✕</button>
                </div>

                {/* Notice Banner */}
                {isTemplatePreview && (
                    <div style={{ background: 'rgba(234, 179, 8, 0.1)', borderBottom: '1px solid rgba(234, 179, 8, 0.25)', padding: '0.6rem 1.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.82rem', color: '#fef08a' }}>
                        <span>⚠️</span>
                        <span>
                            <strong>Lưu ý quan trọng:</strong> Hệ thống đang hiển thị hồ sơ mẫu từ template <em>"{proofData?.template_name || proofData?.template_id || 'Mẫu'}"</em>. Minh chứng mẫu không được coi là bằng chứng hợp lệ cho assessment thực trừ khi bạn tải lên tệp đối soát kỹ thuật.
                        </span>
                    </div>
                )}
                {isNoEvidence && (
                    <div style={{ background: 'rgba(100, 116, 139, 0.12)', borderBottom: '1px solid rgba(100, 116, 139, 0.25)', padding: '0.6rem 1.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.82rem', color: '#cbd5e1' }}>
                        <span>ℹ️</span>
                        <span>
                            <strong>Không có tệp đối chứng:</strong> Lượt đánh giá này không mang tệp minh chứng kỹ thuật (evidence_status=no_evidence). Tất cả điểm số dựa trên tự khai báo.
                        </span>
                    </div>
                )}

                {/* Metrics Grid */}
                <div className={styles.metricsGrid}>
                    <div className={styles.metricCard}>
                        <span className={styles.metricLabel}>Tỷ lệ bóc tách dữ liệu</span>
                        <div className={styles.metricValue}>
                            {isUploaded ? '100.0%' : '0.0%'}{' '}
                            <span className={styles.metricSub}>{isUploaded ? 'Toàn vẹn' : isTemplatePreview ? 'Xem mẫu' : 'Không có tệp'}</span>
                        </div>
                    </div>
                    <div className={styles.metricCard}>
                        <span className={styles.metricLabel}>Số tệp / Ký tự bóc tách</span>
                        <div className={styles.metricValue}>
                            {manifestFiles.length} Tệp{' '}
                            <span className={styles.metricSub}>
                                ({(proofData?.total_chars_extracted || 0).toLocaleString()} ký tự)
                            </span>
                        </div>
                    </div>
                    <div className={styles.metricCard}>
                        <span className={styles.metricLabel}>Bản vá Hotfixes bóc tách</span>
                        <div className={styles.metricValue}>
                            {facts.hotfixes_count || facts.hotfixes?.length || 0} Bản vá{' '}
                            <span className={styles.metricSub}>KB</span>
                        </div>
                    </div>
                    <div className={styles.metricCard}>
                        <span className={styles.metricLabel}>Lỗ hổng & Điểm yếu bảo mật</span>
                        <div className={styles.metricValue} style={{ color: (facts.security_deficiencies?.length || 0) > 0 ? '#f87171' : '#94a3b8' }}>
                            {facts.security_deficiencies?.length || 0} Lỗ hổng{' '}
                            <span className={styles.metricSub}>Phát hiện</span>
                        </div>
                    </div>
                </div>

                {/* Tabs Nav */}
                <div className={styles.tabsNav}>
                    <button
                        className={`${styles.tabBtn} ${activeTab === 'facts' ? styles.tabBtnActive : ''}`}
                        onClick={() => setActiveTab('facts')}
                    >
                        🔍 Dữ liệu kỹ thuật trích xuất (Technical Facts)
                    </button>
                    <button
                        className={`${styles.tabBtn} ${activeTab === 'manifest' ? styles.tabBtnActive : ''}`}
                        onClick={() => setActiveTab('manifest')}
                    >
                        📁 Hồ sơ nạp bằng chứng & SHA-256 (Ingestion Manifest)
                    </button>
                    <button
                        className={`${styles.tabBtn} ${activeTab === 'matrix' ? styles.tabBtnActive : ''}`}
                        onClick={() => setActiveTab('matrix')}
                    >
                        ⚖️ Ma trận đối soát chéo (Cross-Verification Matrix)
                    </button>
                </div>

                {/* Content */}
                <div className={styles.tabContent}>
                    {activeTab === 'facts' && (
                        <div className={styles.factsSection}>
                            {!hasFacts ? (
                                <div style={{ padding: '3.5rem 1.5rem', textAlign: 'center', color: '#94a3b8' }}>
                                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📂</div>
                                    <h4 style={{ color: '#e2e8f0', margin: '0 0 0.5rem 0', fontSize: '1.1rem' }}>
                                        {isTemplatePreview ? 'Dữ liệu mẫu từ Template — Chưa nạp tệp kỹ thuật' : 'Không có dữ liệu trích xuất kỹ thuật'}
                                    </h4>
                                    <p style={{ maxWidth: '540px', margin: '0 auto', fontSize: '0.875rem', lineHeight: 1.6, color: '#94a3b8' }}>
                                        {isTemplatePreview
                                            ? 'Hồ sơ đang ở chế độ xem mẫu cấu hình. Để bóc tách thông tin máy chủ, bản vá và cổng dịch vụ thực tế, vui lòng nạp tệp scan/log vào form đánh giá.'
                                            : 'Lượt đánh giá này không có tệp minh chứng kỹ thuật đính kèm (0 tệp / 0 bytes). Phán quyết được chấm dựa trên trạng thái tự khai báo.'}
                                    </p>
                                </div>
                            ) : (
                                <>
                                    {/* Host & OS */}
                                    {(facts.hostname || facts.os) && (
                                        <div className={styles.factBlock}>
                                            <h5 className={styles.factBlockTitle}>🖥️ Thông tin máy chủ & Hệ điều hành (Empirical OS Telemetry)</h5>
                                            <div className={styles.factPropsGrid}>
                                                {facts.hostname && (
                                                    <div className={styles.factPropItem}>
                                                        <span className={styles.factPropLabel}>Tên máy chủ (Hostname)</span>
                                                        <span className={styles.factPropValue}>{facts.hostname}</span>
                                                    </div>
                                                )}
                                                {facts.os && (
                                                    <div className={styles.factPropItem}>
                                                        <span className={styles.factPropLabel}>Hệ điều hành & Phiên bản</span>
                                                        <span className={styles.factPropValue}>
                                                            {facts.os}
                                                            {facts.os_eol && <span className={styles.pillItemWarn} style={{ marginLeft: '8px' }}>⚠️ End-of-Life (EOL)</span>}
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* Hotfixes */}
                                    {facts.hotfixes && facts.hotfixes.length > 0 && (
                                        <div className={styles.factBlock}>
                                            <h5 className={styles.factBlockTitle}>
                                                📦 Danh sách Bản vá đã cài đặt (Hotfixes Inventory — {facts.hotfixes.length} Bản vá)
                                            </h5>
                                            <div className={styles.pillsList}>
                                                {facts.hotfixes.map((kb, idx) => (
                                                    <span key={idx} className={styles.pillItem}>✓ {kb}</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Ports & Antivirus */}
                                    {((facts.open_ports && facts.open_ports.length > 0) || (facts.antivirus && facts.antivirus.length > 0)) && (
                                        <div className={styles.factBlock}>
                                            <h5 className={styles.factBlockTitle}>🌐 Cổng dịch vụ mạng & Phần mềm bảo vệ (Network & EDR)</h5>
                                            <div className={styles.factPropsGrid}>
                                                {facts.open_ports && facts.open_ports.length > 0 && (
                                                    <div className={styles.factPropItem}>
                                                        <span className={styles.factPropLabel}>Cổng dịch vụ đang lắng nghe (Open Ports)</span>
                                                        <div className={styles.pillsList}>
                                                            {facts.open_ports.map((p, idx) => (
                                                                <span key={idx} className={styles.pillItem}>{p}</span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                                {facts.antivirus && facts.antivirus.length > 0 && (
                                                    <div className={styles.factPropItem}>
                                                        <span className={styles.factPropLabel}>Phần mềm phòng chống mã độc (Antivirus / EDR)</span>
                                                        <div className={styles.pillsList}>
                                                            {facts.antivirus.map((av, idx) => (
                                                                <span key={idx} className={styles.pillItem}>🛡️ {av}</span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* Deficiencies */}
                                    {facts.security_deficiencies && facts.security_deficiencies.length > 0 && (
                                        <div className={styles.factBlock}>
                                            <h5 className={styles.factBlockTitle}>⚠️ Lỗ hổng phát hiện từ bằng chứng thực tế</h5>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                {facts.security_deficiencies.map((d, idx) => (
                                                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.82rem', color: '#fda4af' }}>
                                                        <span>🔴</span>
                                                        <span>{typeof d === 'string' ? d : d.name || 'Lỗ hổng bảo mật'}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    )}

                    {activeTab === 'manifest' && (
                        <div>
                            {manifestFiles.length === 0 ? (
                                <div style={{ padding: '3.5rem 1.5rem', textAlign: 'center', color: '#94a3b8' }}>
                                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📭</div>
                                    <h4 style={{ color: '#e2e8f0', margin: '0 0 0.5rem 0' }}>Hồ sơ nạp bằng chứng (Evidence Manifest) trống</h4>
                                    <p style={{ fontSize: '0.875rem', color: '#94a3b8', maxWidth: '480px', margin: '0 auto' }}>
                                        Chưa có tệp minh chứng kỹ thuật nào được nạp hoặc liên kết với lượt đánh giá này.
                                    </p>
                                </div>
                            ) : (
                                <table className={styles.dataTable}>
                                    <thead>
                                        <tr>
                                            <th style={{ width: '40px' }}>#</th>
                                            <th style={{ width: '130px' }}>Nguồn dữ liệu</th>
                                            <th>Tên tệp bằng chứng</th>
                                            <th style={{ width: '100px' }}>Evidence ID</th>
                                            <th style={{ width: '80px' }}>Kích thước</th>
                                            <th style={{ width: '100px' }}>Ký tự trích xuất</th>
                                            <th style={{ width: '120px' }}>Biện pháp liên kết</th>
                                            <th style={{ width: '120px' }}>Trạng thái OCR / Parse</th>
                                            <th style={{ width: '120px' }}>Trạng thái Ingest</th>
                                            <th>Mã băm SHA-256 (Toàn vẹn)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {manifestFiles.map((f, idx) => (
                                            <tr key={idx}>
                                                <td style={{ textAlign: 'center', color: '#64748b' }}>{idx + 1}</td>
                                                <td>
                                                    {isUploaded ? (
                                                        <span style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', padding: '2px 6px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600 }}>
                                                            Uploaded Evidence
                                                        </span>
                                                    ) : isTemplatePreview ? (
                                                        <span style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#fde047', padding: '2px 6px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600 }}>
                                                            Template Preview
                                                        </span>
                                                    ) : (
                                                        <span style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#cbd5e1', padding: '2px 6px', borderRadius: '4px', fontSize: '0.72rem', fontWeight: 600 }}>
                                                            Assessment Manifest
                                                        </span>
                                                    )}
                                                </td>
                                                <td style={{ fontWeight: 600 }}>📄 {f.masked_filename || f.filename}</td>
                                                <td style={{ color: '#94a3b8', fontSize: '0.78rem', fontFamily: 'monospace' }}>
                                                    {f.file_id || f.id || '—'}
                                                </td>
                                                <td>{((f.size_bytes || 0) / 1024).toFixed(1)} KB</td>
                                                <td style={{ color: '#38bdf8' }}>{(f.chars_extracted || f.char_count || 0).toLocaleString()} ký tự</td>
                                                <td>
                                                    {(f.control_mapping || f.mapped_controls || []).length > 0 ? (
                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                                            {(f.control_mapping || f.mapped_controls).map((c, cIdx) => (
                                                                <span key={cIdx} className={styles.tagVerified} style={{ fontSize: '0.72rem', padding: '2px 6px' }}>
                                                                    {c}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <span style={{ color: '#64748b', fontSize: '0.78rem' }}>Chưa gán</span>
                                                    )}
                                                </td>
                                                <td>
                                                    <span className={styles.tagVerified}>✓ {f.parser_or_ocr || f.status || 'native_parser'}</span>
                                                </td>
                                                <td>
                                                    {f.ingestion_status === 'excluded' ? (
                                                        <span style={{ color: '#f87171', fontSize: '0.74rem' }}>
                                                            Loại trừ: {f.exclusion_reason || 'Không hợp lệ'}
                                                        </span>
                                                    ) : (
                                                        <span style={{ color: '#4ade80', fontSize: '0.74rem', fontWeight: 600 }}>
                                                            Đã nạp (Ingested)
                                                        </span>
                                                    )}
                                                </td>
                                                <td>
                                                    <span className={styles.hashCell} title={f.sha256}>
                                                        {f.sha256 || '—'}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    )}

                    {activeTab === 'matrix' && (
                        <div>
                            {!hasCrossVerify ? (
                                <div style={{ padding: '3.5rem 1.5rem', textAlign: 'center', color: '#94a3b8' }}>
                                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚖️</div>
                                    <h4 style={{ color: '#e2e8f0', margin: '0 0 0.5rem 0' }}>Không có dữ liệu đối soát chéo</h4>
                                    <p style={{ fontSize: '0.875rem', color: '#94a3b8', maxWidth: '480px', margin: '0 auto' }}>
                                        Ma trận đối soát chéo tự động kích hoạt khi có tệp log hoặc cấu hình kiểm chứng để so sánh với bản tự khai báo.
                                    </p>
                                </div>
                            ) : (
                                <table className={styles.dataTable}>
                                    <thead>
                                        <tr>
                                            <th style={{ width: '85px' }}>Tiêu chí</th>
                                            <th style={{ width: '110px' }}>Tự khai báo</th>
                                            <th>Trích đoạn log đối chiếu kỹ thuật</th>
                                            <th style={{ width: '150px' }}>Kết quả đối soát kỹ thuật</th>
                                            <th style={{ width: '130px' }}>Verdict cuối</th>
                                            <th>Thẻ dẫn chứng minh bạch</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {/* Contradictions */}
                                        {crossVerify.contradiction_gaps?.map((c, idx) => (
                                            <tr key={`cg_${idx}`}>
                                                <td style={{ fontWeight: 700, color: '#f87171' }}>{c.control_id}</td>
                                                <td><span style={{ color: '#22c55e' }}>Đã triển khai</span></td>
                                                <td>
                                                    <div className={styles.snippetBox} title={c.evidence_snippet}>
                                                        {c.evidence_snippet || c.defect_name}
                                                    </div>
                                                </td>
                                                <td>
                                                    {renderTechnicalResultBadge(c.technical_result || 'Mâu thuẫn log kỹ thuật')}
                                                </td>
                                                <td>
                                                    {renderFinalVerdictBadge(c.final_verdict || 'needs_expert_review', styles)}
                                                </td>
                                                <td>
                                                    <span className={styles.tagContradiction}>{c.citation}</span>
                                                </td>
                                            </tr>
                                        ))}

                                        {/* Verified */}
                                        {crossVerify.verified_satisfied?.map((c, idx) => (
                                            <tr key={`vs_${idx}`}>
                                                <td style={{ fontWeight: 700, color: '#4ade80' }}>{c.control_id}</td>
                                                <td><span style={{ color: '#22c55e' }}>Đã triển khai</span></td>
                                                <td>
                                                    <div className={styles.snippetBox} title={c.evidence_snippet}>
                                                        {c.evidence_snippet || c.label || 'Khớp cấu hình & log'}
                                                    </div>
                                                </td>
                                                <td>
                                                    {renderTechnicalResultBadge(c.technical_result || 'Khớp bằng chứng kỹ thuật')}
                                                </td>
                                                <td>
                                                    {renderFinalVerdictBadge(c.final_verdict || 'satisfied', styles)}
                                                </td>
                                                <td>
                                                    <span className={styles.tagVerified}>{c.citation}</span>
                                                </td>
                                            </tr>
                                        ))}

                                        {/* Unverified */}
                                        {crossVerify.unverified_oversights?.map((c, idx) => (
                                            <tr key={`uo_${idx}`}>
                                                <td style={{ fontWeight: 700, color: '#94a3b8' }}>{c.control_id}</td>
                                                <td><span style={{ color: '#22c55e' }}>Đã triển khai</span></td>
                                                <td style={{ color: '#64748b', fontStyle: 'italic' }}>
                                                    Không tìm thấy log hoặc tài liệu đính kèm
                                                </td>
                                                <td>
                                                    {renderTechnicalResultBadge(c.technical_result || 'Không có log đối chứng')}
                                                </td>
                                                <td>
                                                    {renderFinalVerdictBadge(c.final_verdict || 'missing', styles)}
                                                </td>
                                                <td>
                                                    <span className={styles.tagUnverified}>{c.citation}</span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
