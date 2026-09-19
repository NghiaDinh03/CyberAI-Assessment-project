/**
 * Intelligent Real-time Evidence Matcher
 * Maps infrastructure inputs and uploaded log data to specific ISO 27001 & TCVN 11930 controls.
 */

const normalizeString = (val) => {
    if (val === null || val === undefined) return ''
    if (typeof val === 'string') return val.trim()
    if (typeof val === 'number') return val !== 0 ? String(val) : ''
    if (Array.isArray(val)) return val.map(v => typeof v === 'string' ? v.trim() : String(v)).filter(Boolean).join(', ')
    return String(val).trim()
}

export function deriveInputEvidenceMap(form = {}, evidenceMap = {}) {
    if (!form) return {}
    const insights = {}

    // Helper to register an insight
    const addInsight = (controlIds, source, text, extra = {}) => {
        controlIds.forEach(id => {
            if (!insights[id]) insights[id] = []
            insights[id].push({ source, text, ...extra })
        })
    }

    // 1. Firewall & Network Security
    const fw = normalizeString(form.firewalls)
    if (fw) {
        addInsight(['NW.02', 'A.8.20', 'NW.01', 'A.8.22'], 'Hạ tầng / Firewall', `Thiết bị tường lửa: ${fw}`, { type: 'infra' })
    }

    // 2. Antivirus & EDR / Malware Protection
    const av = normalizeString(form.antivirus)
    if (av) {
        addInsight(['SV.02', 'A.8.7', 'SV.03', 'APP.03'], 'Hạ tầng / Antivirus', `Giải pháp bảo vệ Endpoint: ${av}`, { type: 'infra' })
    }

    // 3. Backup & Recovery Solution
    const bk = normalizeString(form.backup_solution)
    if (bk) {
        addInsight(['DAT.01', 'A.8.13', 'A.8.14', 'QL.08'], 'Hạ tầng / Sao lưu', `Giải pháp sao lưu dữ liệu: ${bk}`, { type: 'infra' })
    }

    // 4. SIEM & Centralized Log Management
    const siem = normalizeString(form.siem)
    if (siem) {
        addInsight(['SV.08', 'A.8.15', 'SV.09', 'A.8.16'], 'Hạ tầng / SIEM', `Hệ thống giám sát SIEM: ${siem}`, { type: 'infra' })
    }

    // 5. Cloud Infrastructure & Segmentation
    const cp = normalizeString(form.cloud_provider)
    if (cp) {
        addInsight(['NW.04', 'NW.05', 'A.8.21', 'A.8.23'], 'Hạ tầng / Cloud', `Môi trường Cloud: ${cp}`, { type: 'infra' })
    }

    // 6. VPN & Remote Access
    if (form.vpn) {
        addInsight(['NW.03', 'A.8.20', 'AC.03', 'A.8.5'], 'Hạ tầng / VPN', 'Kênh truyền kết nối từ xa VPN', { type: 'infra' })
    }

    // 7. Scope & Dedicated Departments/Systems
    const scopeDesc = normalizeString(form.scope_description)
    if (form.assessment_scope && form.assessment_scope !== 'full' && scopeDesc) {
        addInsight(['QL.01', 'A.5.1'], 'Phạm vi đánh giá', `Phạm vi: ${scopeDesc}`, { type: 'infra' })
    }

    // 8. Uploaded Evidence Files
    if (evidenceMap && typeof evidenceMap === 'object') {
        Object.entries(evidenceMap).forEach(([ctrlId, files]) => {
            if (files && Array.isArray(files) && files.length > 0) {
                const cleanNames = files.map(f => {
                    const raw = f?.filename || f?.name || 'file'
                    return raw.replace(/^\d{8}_\d{6}_/, '')
                })
                
                let textDesc = ''
                if (cleanNames.length === 1) {
                    textDesc = cleanNames[0]
                } else if (cleanNames.length === 2) {
                    textDesc = `${cleanNames[0]}, ${cleanNames[1]}`
                } else {
                    textDesc = `${cleanNames[0]}, ${cleanNames[1]} (+${cleanNames.length - 2} tệp)`
                }

                addInsight([ctrlId], 'Tệp bằng chứng', textDesc, {
                    type: 'evidence_file',
                    count: cleanNames.length,
                    fullList: cleanNames.join(', ')
                })
            }
        })
    }

    return insights
}
