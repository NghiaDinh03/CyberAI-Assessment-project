'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import styles from './page.module.css'

function FormatGuidePanel({ onClose }) {
    const [tab, setTab] = useState('json')
    return (
        <div className={styles.formatGuideOverlay} onClick={onClose}>
            <div className={styles.formatGuidePanel} onClick={e => e.stopPropagation()}>
                <div className={styles.formatGuideHeader}>
                    <div>
                        <h3 className={styles.formatGuideTitle}>Standard Format Guide</h3>
                        <p className={styles.formatGuideSubtitle}>
                            Both built-in standards (ISO 27001, TCVN 11930) share this schema.
                            Custom uploaded files must follow this format.
                        </p>
                    </div>
                    <button className={styles.formatGuideClose} onClick={onClose}>✕</button>
                </div>

                <div className={styles.formatGuideTabs}>
                    {[
                        { id: 'json', label: 'JSON' },
                        { id: 'yaml', label: 'YAML' },
                        { id: 'builtin', label: 'Built-in examples' },
                        { id: 'chromadb', label: 'vs ChromaDB' },
                    ].map(t => (
                        <button
                            key={t.id}
                            className={`${styles.formatGuideTab} ${tab === t.id ? styles.formatGuideTabActive : ''}`}
                            onClick={() => setTab(t.id)}
                        >{t.label}</button>
                    ))}
                </div>

                <div className={styles.formatGuideBody}>
                    {tab === 'json' && (
                        <>
                            <p className={styles.formatGuideNote}>
                                Full JSON format — supports <strong>nested controls by category</strong> and optional <strong>controlDescriptions</strong>.
                            </p>
                            <pre className={styles.formatGuideCode}>{`{
  "id": "my_standard",
  "name": "Standard Name",
  "version": "1.0",
  "description": "Description...",

  "controls": [
    {
      "category": "1. Group Name",
      "controls": [
        {
          "id": "CTL.01",
          "label": "Short name",
          "weight": "critical"
        },
        {
          "id": "CTL.02",
          "label": "Another control",
          "weight": "high"
        }
      ]
    }
  ],

  "controlDescriptions": {
    "CTL.01": {
      "requirement": "Standard requirement...",
      "criteria": "Evaluation criteria...",
      "hint": "Implementation hint...",
      "evidence": [
        "Policy document ABC",
        "Log file XYZ"
      ]
    }
  }
}`}</pre>
                            <div className={styles.formatGuideWeights}>
                                <strong>Weight scores:</strong>
                                {[['critical', '#f87171', '4pts'], ['high', '#fbbf24', '3pts'], ['medium', '#4f8ef7', '2pts'], ['low', '#7d8fa3', '1pt']].map(([w, c, p]) => (
                                    <span key={w} style={{ borderColor: c, color: c, border: `1px solid ${c}`, borderRadius: '4px', padding: '2px 8px', fontSize: '0.72rem', fontWeight: 700 }}>{w} = {p}</span>
                                ))}
                            </div>
                        </>
                    )}
                    {tab === 'yaml' && (
                        <>
                            <p className={styles.formatGuideNote}>YAML format — equivalent to JSON, more concise syntax.</p>
                            <pre className={styles.formatGuideCode}>{`id: my_standard
name: "Standard Name"
version: "1.0"
description: "Description"

controls:
  - category: "1. Group Name"
    controls:
      - id: CTL.01
        label: "Control short name"
        weight: critical
      - id: CTL.02
        label: "Another control"
        weight: high

controlDescriptions:
  CTL.01:
    requirement: "Standard requirement..."
    criteria: "Evaluation criteria..."
    hint: "Implementation hint..."
    evidence:
      - "Policy document"
      - "Evidence log file"`}</pre>
                        </>
                    )}
                    {tab === 'builtin' && (
                        <>
                            <p className={styles.formatGuideNote}>
                                Both built-in standards use the <strong>same schema</strong> as custom uploads.
                                The only difference: built-in standards are hardcoded in <code>src/data/standards.js</code> and cannot be deleted.
                            </p>
                            <pre className={styles.formatGuideCode}>{`// ISO 27001:2022 — first 2 controls
{
  "id": "iso27001",
  "name": "ISO 27001:2022 (93 Controls)",
  "controls": [
    {
      "category": "A.5 Organizational",
      "controls": [
        { "id": "A.5.1", "label": "Information security policies", "weight": "critical" },
        { "id": "A.5.2", "label": "ISMS roles and responsibilities", "weight": "critical" }
      ]
    }
  ]
}

// TCVN 11930:2017 — same schema, different IDs
{
  "id": "tcvn11930",
  "name": "TCVN 11930:2017 (34 Requirements)",
  "controls": [
    { "category": "1. Network Security", "controls": [ /* NW.01–NW.08 */ ] },
    { "category": "2. Server Security", "controls": [ /* SV.01–SV.08 */ ] }
  ]
}`}</pre>
                            <p className={styles.formatGuideNote} style={{ marginTop: '0.75rem' }}>
                                Want to see the full schema? Click <strong>Download sample JSON</strong> — the downloaded file will have all required and optional fields.
                            </p>
                        </>
                    )}
                    {tab === 'chromadb' && (
                        <>
                            <p className={styles.formatGuideNote}>
                                <strong>ChromaDB does not use your JSON file directly.</strong>
                                The backend automatically transforms it when you upload.
                            </p>
                            <div className={styles.formatGuideCompare}>
                                <div className={styles.formatGuideCompareCol}>
                                    <div className={styles.formatGuideCompareHead}>Your upload file (JSON/YAML)</div>
                                    <pre className={styles.formatGuideCode} style={{ margin: 0, borderRadius: '0 0 8px 8px' }}>{`{
  "id": "my_standard",
  "controls": [
    {
      "category": "1. Group A",
      "controls": [
        {
          "id": "CTL.01",
          "label": "Control name",
          "weight": "critical"
        }
      ]
    }
  ]
}`}</pre>
                                </div>
                                <div className={styles.formatGuideCompareArrow}>→ backend transform →</div>
                                <div className={styles.formatGuideCompareCol}>
                                    <div className={styles.formatGuideCompareHead}>ChromaDB document chunk</div>
                                    <pre className={styles.formatGuideCode} style={{ margin: 0, borderRadius: '0 0 8px 8px' }}>{`{
  "id": "my_standard__CTL_01",
  "document": "CTL.01 — Control name
    Category: 1. Group A
    Weight: critical
    Standard: my_standard",
  "metadata": {
    "source": "my_standard",
    "control_id": "CTL.01",
    "category": "1. Group A",
    "weight": "critical"
  }
}`}</pre>
                                </div>
                            </div>
                            <p className={styles.formatGuideNote} style={{ marginTop: '0.75rem' }}>
                                Each control becomes <strong>1 separate chunk</strong> in ChromaDB.
                                The AI Auditor queries ChromaDB during assessment to find relevant standard requirements.
                                After uploading, click <strong>Re-index</strong> on the standard card to update ChromaDB if needed.
                            </p>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

export default function StandardsPage() {
    const [standards, setStandards] = useState({ builtin: [], custom: [] })
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const [uploadResult, setUploadResult] = useState(null)
    const [validateResult, setValidateResult] = useState(null)
    const [dragOver, setDragOver] = useState(false)
    const [selectedStandard, setSelectedStandard] = useState(null)
    const [detailLoading, setDetailLoading] = useState(false)
    const [showFormatGuide, setShowFormatGuide] = useState(false)

    const fetchStandards = useCallback(async () => {
        try {
            setLoading(true)
            const res = await fetch('/api/standards')
            if (res.ok) {
                const data = await res.json()
                setStandards({ builtin: data.builtin || [], custom: data.custom || [] })
            }
        } catch (e) {
            console.error('Failed to fetch standards:', e)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { fetchStandards() }, [fetchStandards])

    const handleUpload = async (file) => {
        if (!file) return
        setUploading(true)
        setUploadResult(null)
        setValidateResult(null)
        const formData = new FormData()
        formData.append('file', file)
        try {
            const res = await fetch('/api/standards/upload', { method: 'POST', body: formData })
            const data = await res.json()
            if (res.ok && data.status === 'success') {
                setUploadResult({ success: true, data })
                fetchStandards()
            } else {
                setUploadResult({ success: false, errors: data.errors || [data.detail || data.message || 'Upload failed'] })
            }
        } catch (e) {
            setUploadResult({ success: false, errors: [`Network error: ${e.message}`] })
        } finally {
            setUploading(false)
        }
    }

    const handleValidate = async (file) => {
        if (!file) return
        setValidateResult(null)
        const formData = new FormData()
        formData.append('file', file)
        try {
            const res = await fetch('/api/standards/validate', { method: 'POST', body: formData })
            const data = await res.json()
            setValidateResult(data)
        } catch (e) {
            setValidateResult({ valid: false, errors: [`Network error: ${e.message}`] })
        }
    }

    const handleDelete = async (standardId) => {
        if (!confirm(`Confirm delete standard "${standardId}"? This action cannot be undone.`)) return
        try {
            const res = await fetch(`/api/standards/${standardId}`, { method: 'DELETE' })
            if (res.ok) {
                fetchStandards()
                if (selectedStandard?.id === standardId) setSelectedStandard(null)
            }
        } catch (e) {
            console.error('Delete failed:', e)
        }
    }

    const handleReindex = async (standardId) => {
        try {
            const res = await fetch(`/api/standards/${standardId}/index`, { method: 'POST' })
            const data = await res.json()
            alert(data.status === 'ok'
                ? `Indexed ${data.chunks_indexed} chunks for "${standardId}"`
                : data.message || 'Indexing failed'
            )
        } catch (e) {
            alert(`Error: ${e.message}`)
        }
    }

    const handleViewDetail = async (standardId) => {
        setDetailLoading(true)
        try {
            const res = await fetch(`/api/standards/${standardId}`)
            if (res.ok) {
                const data = await res.json()
                setSelectedStandard(data)
            }
        } catch (e) {
            console.error('Failed to load standard detail:', e)
        } finally {
            setDetailLoading(false)
        }
    }

    const downloadSample = async () => {
        try {
            const res = await fetch('/api/standards/sample')
            const data = await res.json()
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'sample_standard.json'
            a.click()
            URL.revokeObjectURL(url)
        } catch (e) {
            console.error('Download failed:', e)
        }
    }

    const onDrop = (e) => {
        e.preventDefault()
        setDragOver(false)
        const file = e.dataTransfer?.files?.[0]
        if (file) handleUpload(file)
    }

    const onFileSelect = (e) => {
        const file = e.target.files?.[0]
        if (file) handleUpload(file)
    }

    const onValidateSelect = (e) => {
        const file = e.target.files?.[0]
        if (file) handleValidate(file)
    }

    const WEIGHT_COLOR = { critical: '#f87171', high: '#fbbf24', medium: '#4f8ef7', low: '#7d8fa3' }
    const WEIGHT_LABEL = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' }

    return (
        <div className="page-container">
            <div className={styles.header}>
                <h1 className={styles.title}>Standards Management</h1>
                <p className={styles.subtitle}>
                    Upload custom standards (JSON/YAML) → Backend parses + ChromaDB indexes → Assessment form auto-renders.
                </p>
                <Link href="/form-iso" className={styles.backLink}>← Back to Assessment</Link>
            </div>

            {showFormatGuide && <FormatGuidePanel onClose={() => setShowFormatGuide(false)} />}

            <div className={styles.section}>
                <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>Upload New Standard</h2>
                    <div className={styles.sectionActions}>
                        <button className={styles.btnOutline} onClick={downloadSample}>
                            Download sample JSON
                        </button>
                        <label className={styles.btnOutline}>
                            Validate file
                            <input type="file" accept=".json,.yaml,.yml" onChange={onValidateSelect} hidden />
                        </label>
                        <button className={styles.btnOutline} onClick={() => setShowFormatGuide(true)}>
                            Format guide
                        </button>
                    </div>
                </div>

                <div
                    className={`${styles.dropZone} ${dragOver ? styles.dropZoneActive : ''} ${uploading ? styles.dropZoneUploading : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={onDrop}
                >
                    {uploading ? (
                        <div className={styles.dropContent}>
                            <span className={styles.dropSpinner} />
                            <p>Uploading and processing...</p>
                        </div>
                    ) : (
                        <div className={styles.dropContent}>
                            <p className={styles.dropText}>Drop JSON / YAML file here</p>
                            <p className={styles.dropHint}>or</p>
                            <label className={styles.btnPrimary}>
                                Select file
                                <input type="file" accept=".json,.yaml,.yml" onChange={onFileSelect} hidden />
                            </label>
                            <p className={styles.dropMeta}>.json, .yaml, .yml · Max 2MB</p>
                        </div>
                    )}
                </div>

                {validateResult && (
                    <div className={`${styles.resultBox} ${validateResult.valid ? styles.resultSuccess : styles.resultError}`}>
                        <div className={styles.resultHeader}>
                            {validateResult.valid ? 'File is valid' : 'File is invalid'}
                        </div>
                        {validateResult.preview && (
                            <div className={styles.resultMeta}>
                                <span>ID: <strong>{validateResult.preview.id}</strong></span>
                                <span>Name: <strong>{validateResult.preview.name}</strong></span>
                                <span>Controls: <strong>{validateResult.preview.total_controls}</strong></span>
                                <span>Categories: <strong>{validateResult.preview.categories}</strong></span>
                            </div>
                        )}
                        {validateResult.errors?.length > 0 && (
                            <ul className={styles.errorList}>
                                {validateResult.errors.map((err, i) => <li key={i}>{err}</li>)}
                            </ul>
                        )}
                    </div>
                )}

                {uploadResult && (
                    <div className={`${styles.resultBox} ${uploadResult.success ? styles.resultSuccess : styles.resultError}`}>
                        <div className={styles.resultHeader}>
                            {uploadResult.success ? 'Upload successful' : 'Upload failed'}
                        </div>
                        {uploadResult.success && uploadResult.data?.standard && (
                            <div className={styles.resultMeta}>
                                <span>ID: <strong>{uploadResult.data.standard.id}</strong></span>
                                <span>Name: <strong>{uploadResult.data.standard.name}</strong></span>
                                <span>Controls: <strong>{uploadResult.data.standard.total_controls}</strong></span>
                                <span>Max Score: <strong>{uploadResult.data.standard.max_weighted_score}</strong></span>
                                {uploadResult.data.chromadb_index?.chunks_indexed && (
                                    <span>ChromaDB: <strong>{uploadResult.data.chromadb_index.chunks_indexed} chunks indexed</strong></span>
                                )}
                            </div>
                        )}
                        {uploadResult.errors?.length > 0 && (
                            <ul className={styles.errorList}>
                                {uploadResult.errors.map((err, i) => <li key={i}>{err}</li>)}
                            </ul>
                        )}
                        {!uploadResult.success && (
                            <p className={styles.resultHint}>
                                Download <button className={styles.linkBtn} onClick={downloadSample}>sample JSON</button> to see the correct format.
                            </p>
                        )}
                    </div>
                )}
            </div>

            <div className={styles.section}>
                <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>Standards Library</h2>
                    <button className={styles.btnOutline} onClick={fetchStandards} disabled={loading}>
                        Refresh
                    </button>
                </div>

                {loading ? (
                    <div className={styles.loadingBox}>Loading...</div>
                ) : (
                    <>
                        <div className={styles.groupTitleRow}>
                            <h3 className={styles.groupTitle}>Built-in Standards</h3>
                            <button className={styles.infoIconBtn} onClick={() => setShowFormatGuide(true)}>
                                View schema
                            </button>
                        </div>
                        <div className={styles.standardGrid}>
                            {standards.builtin.map(std => (
                                <div key={std.id} className={styles.standardCard}>
                                    <div className={styles.cardHeader}>
                                        <span className={styles.cardBadge}>Built-in</span>
                                        <span className={styles.cardVersion}>{std.version}</span>
                                    </div>
                                    <h4 className={styles.cardName}>{std.name}</h4>
                                    <p className={styles.cardDesc}>{std.description}</p>
                                    <div className={styles.cardStats}>
                                        <span>{std.total_controls} controls</span>
                                        <span>{std.categories} categories</span>
                                    </div>
                                    <div className={styles.cardActions}>
                                        <Link href="/form-iso" className={styles.btnSmall}>Use in Assessment</Link>
                                        <button className={styles.btnSmall} onClick={() => setShowFormatGuide(true)}>Schema</button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <h3 className={styles.groupTitle} style={{ marginTop: '1.25rem' }}>Custom Standards (Uploaded)</h3>
                        {standards.custom.length === 0 ? (
                            <div className={styles.emptyBox}>
                                <p>No custom standards yet.</p>
                                <p className={styles.emptyHint}>Upload a JSON/YAML file above to add a new standard.</p>
                            </div>
                        ) : (
                            <div className={styles.standardGrid}>
                                {standards.custom.map(std => (
                                    <div key={std.id} className={`${styles.standardCard} ${styles.standardCardCustom}`}>
                                        <div className={styles.cardHeader}>
                                            <span className={`${styles.cardBadge} ${styles.cardBadgeCustom}`}>Custom</span>
                                            <span className={styles.cardVersion}>{std.version}</span>
                                        </div>
                                        <h4 className={styles.cardName}>{std.name}</h4>
                                        <p className={styles.cardDesc}>{std.description || 'No description'}</p>
                                        <div className={styles.cardStats}>
                                            <span>{std.total_controls} controls</span>
                                            <span>{std.categories} categories</span>
                                            <span>Max: {std.max_weighted_score}pts</span>
                                        </div>
                                        {std.weight_breakdown && Object.keys(std.weight_breakdown).length > 0 && (
                                            <div className={styles.weightBreakdown}>
                                                {Object.entries(std.weight_breakdown).map(([w, count]) => count > 0 && (
                                                    <span key={w} className={styles.weightTag} style={{ borderColor: WEIGHT_COLOR[w], color: WEIGHT_COLOR[w] }}>
                                                        {WEIGHT_LABEL[w]}: {count}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                        <div className={styles.cardActions}>
                                            <button className={styles.btnSmall} onClick={() => handleViewDetail(std.id)}>Detail</button>
                                            <button className={styles.btnSmall} onClick={() => handleReindex(std.id)}>Re-index</button>
                                            <button className={`${styles.btnSmall} ${styles.btnDanger}`} onClick={() => handleDelete(std.id)}>Delete</button>
                                        </div>
                                        <div className={styles.cardMeta}>
                                            <span>{std.created_at ? new Date(std.created_at).toLocaleDateString('vi-VN') : '—'}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </div>

            {selectedStandard && selectedStandard.controls && (
                <>
                    <div className={styles.panelOverlay} onClick={() => setSelectedStandard(null)} />
                    <div className={styles.detailPanel}>
                        <div className={styles.panelHeader}>
                            <div>
                                <h3 className={styles.panelTitle}>{selectedStandard.name}</h3>
                                <p className={styles.panelSubtitle}>
                                    {selectedStandard.id} · v{selectedStandard.version} · {selectedStandard.total_controls} controls
                                </p>
                            </div>
                            <button className={styles.panelClose} onClick={() => setSelectedStandard(null)}>✕</button>
                        </div>
                        <div className={styles.panelBody}>
                            {detailLoading ? (
                                <div className={styles.loadingBox}>Loading details...</div>
                            ) : (
                                selectedStandard.controls.map((cat, catIdx) => (
                                    <div key={catIdx} className={styles.detailCategory}>
                                        <h4 className={styles.detailCatTitle}>
                                            {cat.category}
                                            <span className={styles.detailCatCount}>{cat.controls.length} controls</span>
                                        </h4>
                                        <div className={styles.detailControlList}>
                                            {cat.controls.map(ctrl => (
                                                <div key={ctrl.id} className={styles.detailControl}>
                                                    <span className={styles.detailCtrlId}>{ctrl.id}</span>
                                                    <span className={styles.detailCtrlLabel}>{ctrl.label}</span>
                                                    <span
                                                        className={styles.detailWeightBadge}
                                                        style={{ borderColor: WEIGHT_COLOR[ctrl.weight], color: WEIGHT_COLOR[ctrl.weight] }}
                                                    >
                                                        {ctrl.weight}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                        <div className={styles.panelFooter}>
                            <Link href="/form-iso" className={styles.btnPrimary}>Use in Assessment Form</Link>
                        </div>
                    </div>
                </>
            )}

            <div className={styles.section}>
                <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>Quick Format Reference</h2>
                    <button className={styles.btnOutline} onClick={() => setShowFormatGuide(true)}>
                        Full guide (JSON / YAML / ChromaDB)
                    </button>
                </div>
                <div className={styles.schemaBox}>
                    <div className={styles.schemaSyncNote}>
                        <span className={styles.schemaSyncBadge}>Synced</span>
                        Both built-in standards (<strong>ISO 27001</strong> and <strong>TCVN 11930</strong>) use the
                        <strong> same JSON schema</strong> as custom uploads. Only the <code>id</code> and
                        category/control ID structure differ.
                    </div>
                    <pre className={styles.schemaCode}>{`{
  "id": "my_standard_id",
  "name": "Standard Name",
  "version": "1.0",
  "description": "Short description",
  "controls": [
    {
      "category": "1. Group Name",
      "controls": [
        {
          "id": "CTL.01",
          "label": "Short name",
          "weight": "critical"
        }
      ]
    }
  ],
  "controlDescriptions": {
    "CTL.01": {
      "requirement": "Standard requirement",
      "criteria": "Evaluation criteria",
      "hint": "Implementation hint",
      "evidence": ["Evidence 1", "Evidence 2"]
    }
  }
}`}</pre>
                    <div className={styles.schemaNote}>
                        <p><strong>Weight scores:</strong></p>
                        <div className={styles.weightBreakdown}>
                            <span className={styles.weightTag} style={{ borderColor: '#f87171', color: '#f87171' }}>critical = 4pts</span>
                            <span className={styles.weightTag} style={{ borderColor: '#fbbf24', color: '#fbbf24' }}>high = 3pts</span>
                            <span className={styles.weightTag} style={{ borderColor: '#4f8ef7', color: '#4f8ef7' }}>medium = 2pts</span>
                            <span className={styles.weightTag} style={{ borderColor: '#7d8fa3', color: '#7d8fa3' }}>low = 1pt</span>
                        </div>
                        <p className={styles.schemaHintText}>
                            Supports <strong>JSON and YAML</strong>. Max 500 controls. After uploading,
                            the backend automatically converts each control into a document chunk and indexes it into <strong>ChromaDB</strong>
                            so the AI Auditor can query it during assessment.
                            {' '}<button className={styles.linkBtn} onClick={() => setShowFormatGuide(true)}>
                                See how ChromaDB storage differs from the upload file →
                            </button>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
