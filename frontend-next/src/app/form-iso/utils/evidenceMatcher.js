/**
 * Intelligent Real-time Evidence Matcher
 * Maps infrastructure inputs and uploaded log data to specific ISO 27001 & TCVN 11930 controls.
 */

export function deriveInputEvidenceMap(form, evidenceMap = {}) {
    const insights = {}

    // Helper to register an insight
    const addInsight = (controlIds, source, text) => {
        controlIds.forEach(id => {
            if (!insights[id]) insights[id] = []
            insights[id].push({ source, text })
        })
    }

    // 1. Firewall & Network Security
    if (form.firewalls && form.firewalls.trim()) {
        const fw = form.firewalls.trim()
        addInsight(['NW.02', 'A.8.20', 'NW.01', 'A.8.22'], 'Hạ tầng / Firewall', `Thiết bị tường lửa ghi nhận: ${fw}`)
    }

    // 2. Antivirus & EDR / Malware Protection
    if (form.antivirus && form.antivirus.trim()) {
        const av = form.antivirus.trim()
        addInsight(['SV.02', 'A.8.7', 'SV.03', 'APP.03'], 'Hạ tầng / Antivirus', `Giải pháp bảo vệ Endpoint/Antivirus: ${av}`)
    }

    // 3. Backup & Recovery Solution
    if (form.backup_solution && form.backup_solution.trim()) {
        const bk = form.backup_solution.trim()
        addInsight(['DAT.01', 'A.8.13', 'A.8.14', 'QL.08'], 'Hạ tầng / Sao lưu', `Giải pháp sao lưu & phục hồi dữ liệu: ${bk}`)
    }

    // 4. SIEM & Centralized Log Management
    if (form.siem && form.siem.trim()) {
        const siem = form.siem.trim()
        addInsight(['SV.08', 'A.8.15', 'SV.09', 'A.8.16'], 'Hạ tầng / SIEM', `Hệ thống giám sát & quản lý log tập trung: ${siem}`)
    }

    // 5. Cloud Infrastructure & Segmentation
    if (form.cloud_provider && form.cloud_provider.trim()) {
        const cp = form.cloud_provider.trim()
        addInsight(['NW.04', 'NW.05', 'A.8.21', 'A.8.23'], 'Hạ tầng / Cloud', `Môi trường điện toán đám mây: ${cp}`)
    }

    // 6. VPN & Remote Access
    if (form.vpn) {
        addInsight(['NW.03', 'A.8.20', 'AC.03', 'A.8.5'], 'Hạ tầng / VPN', 'Kênh truyền kết nối từ xa bảo mật qua VPN')
    }

    // 7. Scope & Dedicated Departments/Systems
    if (form.assessment_scope && form.assessment_scope !== 'full' && form.scope_description) {
        addInsight(['QL.01', 'A.5.1'], 'Phạm vi đánh giá', `Phạm vi áp dụng: ${form.scope_description}`)
    }

    // 8. Uploaded Evidence Files
    Object.entries(evidenceMap).forEach(([ctrlId, files]) => {
        if (files && files.length > 0) {
            const names = files.map(f => f.filename).join(', ')
            addInsight([ctrlId], 'Tệp bằng chứng', `${files.length} tệp đính kèm (${names})`)
        }
    })

    return insights
}
