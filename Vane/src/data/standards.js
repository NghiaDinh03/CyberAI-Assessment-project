// Mức độ quan trọng: critical=4, high=3, medium=2, low=1
// Điểm tối đa = tổng tất cả weight; điểm đạt = tổng weight của controls đã tick

export const ISO_27001_CONTROLS = [
    {
        category: "A.5 Tổ chức",
        controls: [
            { id: "A.5.1",  label: "Chính sách an toàn thông tin",               weight: "critical" },
            { id: "A.5.2",  label: "Vai trò và trách nhiệm ATTT",                weight: "critical" },
            { id: "A.5.3",  label: "Phân tách nhiệm vụ",                         weight: "high" },
            { id: "A.5.4",  label: "Trách nhiệm của ban quản lý",                weight: "high" },
            { id: "A.5.5",  label: "Liên lạc với cơ quan chức năng",             weight: "medium" },
            { id: "A.5.6",  label: "Liên lạc với nhóm chuyên gia",               weight: "low" },
            { id: "A.5.7",  label: "Tình báo mối đe dọa (Threat Intelligence)",  weight: "medium" },
            { id: "A.5.8",  label: "ATTT trong quản lý dự án",                   weight: "medium" },
            { id: "A.5.9",  label: "Kiểm kê tài sản thông tin",                  weight: "high" },
            { id: "A.5.10", label: "Sử dụng tài sản thông tin hợp lệ (AUP)",     weight: "medium" },
            { id: "A.5.11", label: "Hoàn trả tài sản",                           weight: "low" },
            { id: "A.5.12", label: "Phân loại thông tin",                        weight: "high" },
            { id: "A.5.13", label: "Ghi nhãn thông tin",                         weight: "medium" },
            { id: "A.5.14", label: "Truyền tải thông tin",                       weight: "high" },
            { id: "A.5.15", label: "Kiểm soát truy cập",                         weight: "critical" },
            { id: "A.5.16", label: "Quản lý danh tính (IAM)",                    weight: "critical" },
            { id: "A.5.17", label: "Xác thực (MFA/Mật khẩu mạnh)",              weight: "critical" },
            { id: "A.5.18", label: "Quyền truy cập",                             weight: "critical" },
            { id: "A.5.19", label: "ATTT trong quan hệ nhà cung cấp",            weight: "high" },
            { id: "A.5.20", label: "Xử lý ATTT trong hợp đồng nhà cung cấp",    weight: "high" },
            { id: "A.5.21", label: "Quản lý ATTT chuỗi cung ứng ICT",           weight: "medium" },
            { id: "A.5.22", label: "Giám sát dịch vụ nhà cung cấp",             weight: "medium" },
            { id: "A.5.23", label: "ATTT khi sử dụng dịch vụ đám mây",          weight: "high" },
            { id: "A.5.24", label: "Lập kế hoạch quản lý sự cố ATTT",           weight: "critical" },
            { id: "A.5.25", label: "Đánh giá sự kiện ATTT",                     weight: "high" },
            { id: "A.5.26", label: "Phản ứng sự cố ATTT",                       weight: "critical" },
            { id: "A.5.27", label: "Rút kinh nghiệm từ sự cố ATTT",             weight: "high" },
            { id: "A.5.28", label: "Thu thập bằng chứng (Forensic)",             weight: "medium" },
            { id: "A.5.29", label: "ATTT trong giai đoạn gián đoạn (BCP)",       weight: "high" },
            { id: "A.5.30", label: "Sẵn sàng ICT cho kinh doanh liên tục (DR)",  weight: "high" },
            { id: "A.5.31", label: "Tuân thủ yêu cầu pháp lý",                  weight: "critical" },
            { id: "A.5.32", label: "Bảo vệ quyền sở hữu trí tuệ",              weight: "medium" },
            { id: "A.5.33", label: "Bảo vệ hồ sơ",                              weight: "medium" },
            { id: "A.5.34", label: "Bảo vệ thông tin cá nhân (PII)",             weight: "critical" },
            { id: "A.5.35", label: "Đánh giá độc lập ATTT",                     weight: "high" },
            { id: "A.5.36", label: "Tuân thủ chính sách và tiêu chuẩn ATTT",    weight: "high" },
            { id: "A.5.37", label: "Tài liệu hóa quy trình vận hành",           weight: "medium" }
        ]
    },
    {
        category: "A.6 Con người",
        controls: [
            { id: "A.6.1", label: "Sàng lọc nhân sự (Background check)",        weight: "high" },
            { id: "A.6.2", label: "Điều khoản tuyển dụng (NDA)",                weight: "medium" },
            { id: "A.6.3", label: "Nhận thức, đào tạo ATTT",                    weight: "critical" },
            { id: "A.6.4", label: "Quy trình kỷ luật vi phạm ATTT",             weight: "medium" },
            { id: "A.6.5", label: "Trách nhiệm sau chia tay (Offboarding)",      weight: "high" },
            { id: "A.6.6", label: "Thỏa thuận không tiết lộ (NDA)",             weight: "high" },
            { id: "A.6.7", label: "Làm việc từ xa (Remote work / BYOD)",         weight: "high" },
            { id: "A.6.8", label: "Báo cáo sự kiện ATTT",                       weight: "high" }
        ]
    },
    {
        category: "A.7 Vật lý",
        controls: [
            { id: "A.7.1",  label: "Vành đai an ninh vật lý",                   weight: "high" },
            { id: "A.7.2",  label: "Kiểm soát vào ra vật lý",                   weight: "high" },
            { id: "A.7.3",  label: "Bảo vệ văn phòng, phòng ban",               weight: "medium" },
            { id: "A.7.4",  label: "Giám sát an ninh vật lý (CCTV)",            weight: "medium" },
            { id: "A.7.5",  label: "Bảo vệ trước thiên tai",                    weight: "medium" },
            { id: "A.7.6",  label: "Làm việc trong khu vực an toàn",            weight: "medium" },
            { id: "A.7.7",  label: "Bàn làm việc sạch, màn hình sạch",          weight: "low" },
            { id: "A.7.8",  label: "Bố trí và bảo vệ máy chủ/thiết bị",         weight: "high" },
            { id: "A.7.9",  label: "An ninh tài sản ngoài khuôn viên",           weight: "medium" },
            { id: "A.7.10", label: "Quản lý phương tiện lưu trữ",               weight: "high" },
            { id: "A.7.11", label: "Dịch vụ hỗ trợ (UPS/Điện/Net)",             weight: "medium" },
            { id: "A.7.12", label: "An ninh cáp mạng",                          weight: "medium" },
            { id: "A.7.13", label: "Bảo trì thiết bị",                          weight: "low" },
            { id: "A.7.14", label: "Hủy/Tái chế thiết bị an toàn",             weight: "high" }
        ]
    },
    {
        category: "A.8 Công nghệ",
        controls: [
            { id: "A.8.1",  label: "Bảo vệ thiết bị đầu cuối (Endpoint Security)", weight: "critical" },
            { id: "A.8.2",  label: "Quản lý quyền truy cập đặc quyền (PAM)",        weight: "critical" },
            { id: "A.8.3",  label: "Hạn chế truy cập thông tin",                    weight: "high" },
            { id: "A.8.4",  label: "Kiểm soát truy cập mã nguồn",                   weight: "high" },
            { id: "A.8.5",  label: "Xác thực an toàn (MFA)",                        weight: "critical" },
            { id: "A.8.6",  label: "Quản lý công suất (Capacity Planning)",          weight: "medium" },
            { id: "A.8.7",  label: "Bảo vệ chống mã độc (Anti-Malware/EDR)",        weight: "critical" },
            { id: "A.8.8",  label: "Quản lý lỗ hổng kỹ thuật (Vulnerability)",      weight: "critical" },
            { id: "A.8.9",  label: "Quản lý cấu hình (Hardening)",                  weight: "critical" },
            { id: "A.8.10", label: "Xóa thông tin an toàn",                         weight: "medium" },
            { id: "A.8.11", label: "Che giấu dữ liệu (Data Masking)",               weight: "medium" },
            { id: "A.8.12", label: "Ngăn chặn rò rỉ dữ liệu (DLP)",                weight: "high" },
            { id: "A.8.13", label: "Sao lưu thông tin (Backup)",                    weight: "critical" },
            { id: "A.8.14", label: "Dự phòng thiết bị xử lý thông tin (HA)",        weight: "high" },
            { id: "A.8.15", label: "Ghi nhật ký (Logging/SIEM)",                    weight: "critical" },
            { id: "A.8.16", label: "Hoạt động giám sát (Monitoring/SOC)",           weight: "critical" },
            { id: "A.8.17", label: "Đồng bộ đồng hồ (NTP)",                        weight: "low" },
            { id: "A.8.18", label: "Sử dụng chương trình tiện ích đặc quyền",       weight: "medium" },
            { id: "A.8.19", label: "Quản lý cài đặt phần mềm",                     weight: "medium" },
            { id: "A.8.20", label: "An ninh mạng (Firewall)",                       weight: "critical" },
            { id: "A.8.21", label: "An ninh dịch vụ mạng",                         weight: "high" },
            { id: "A.8.22", label: "Phân tách mạng (VLAN/DMZ)",                    weight: "high" },
            { id: "A.8.23", label: "Lọc web (Web Filtering)",                      weight: "medium" },
            { id: "A.8.24", label: "Sử dụng mã hóa (Cryptography)",                weight: "critical" },
            { id: "A.8.25", label: "Vòng đời phát triển an toàn (SDLC/DevSecOps)", weight: "high" },
            { id: "A.8.26", label: "Yêu cầu bảo mật ứng dụng",                    weight: "high" },
            { id: "A.8.27", label: "Kiến trúc hệ thống an toàn",                   weight: "high" },
            { id: "A.8.28", label: "Lập trình an toàn (Secure Coding)",             weight: "medium" },
            { id: "A.8.29", label: "Kiểm thử bảo mật (Pentest/SAST/DAST)",         weight: "high" },
            { id: "A.8.30", label: "Giám sát phát triển thuê ngoài",               weight: "medium" },
            { id: "A.8.31", label: "Phân tách môi trường Dev/Test/Prod",            weight: "high" },
            { id: "A.8.32", label: "Quản lý thay đổi (Change Management)",          weight: "high" },
            { id: "A.8.33", label: "Bảo vệ thông tin kiểm thử",                    weight: "medium" },
            { id: "A.8.34", label: "Bảo vệ hệ thống trong quá trình kiểm toán",    weight: "medium" }
        ]
    }
];

export const TCVN_11930_CONTROLS = [
    {
        category: "1. Bảo đảm ATTT Mạng",
        controls: [
            { id: "NW.01", label: "Kiểm soát truy cập vùng mạng (Access Control List)", weight: "critical" },
            { id: "NW.02", label: "Tường lửa (Firewall) bảo vệ vùng biên",               weight: "critical" },
            { id: "NW.03", label: "Hệ thống phát hiện/ngăn chặn xâm nhập (IDS/IPS)",     weight: "critical" },
            { id: "NW.04", label: "Mã hóa đường truyền truy cập từ xa (VPN)",            weight: "high" },
            { id: "NW.05", label: "Phân tách vùng mạng công cộng và nội bộ (DMZ)",       weight: "critical" },
            { id: "NW.06", label: "Lọc địa chỉ MAC (Port Security)",                     weight: "medium" },
            { id: "NW.07", label: "Quản lý truy cập mạng NAC",                           weight: "high" },
            { id: "NW.08", label: "Đường truyền vật lý dự phòng khác tuyến (Cấp 4, 5)", weight: "high" }
        ]
    },
    {
        category: "2. Bảo đảm ATTT Máy chủ",
        controls: [
            { id: "SV.01", label: "Mật khẩu phức tạp & Đóng dịch vụ không cần thiết",  weight: "critical" },
            { id: "SV.02", label: "Phần mềm chống mã độc (Antivirus)",                  weight: "critical" },
            { id: "SV.03", label: "Hệ thống chống xâm nhập máy chủ (EDR/XDR)",         weight: "critical" },
            { id: "SV.04", label: "Giám sát tính toàn vẹn tệp tin (FIM)",               weight: "high" },
            { id: "SV.05", label: "Quản lý truy cập đặc quyền (PAM)",                   weight: "critical" },
            { id: "SV.06", label: "Xác thực đa yếu tố (MFA) cho root/admin",           weight: "critical" },
            { id: "SV.07", label: "Cập nhật bản vá định kỳ (Patch Management)",         weight: "critical" },
            { id: "SV.08", label: "Thiết lập cấu hình an toàn (Hardening / CIS)",       weight: "critical" }
        ]
    },
    {
        category: "3. Bảo đảm ATTT Ứng dụng",
        controls: [
            { id: "APP.01", label: "Mã hóa mật khẩu CSDL (Bcrypt, SHA-256)",              weight: "critical" },
            { id: "APP.02", label: "Kết nối an toàn HTTPS/TLS 1.2+",                      weight: "critical" },
            { id: "APP.03", label: "Kiểm soát đầu vào người dùng (Chống SQLi, XSS)",      weight: "critical" },
            { id: "APP.04", label: "Giới hạn thời gian phiên làm việc (Session Timeout)", weight: "high" },
            { id: "APP.05", label: "Ngăn chặn tấn công Web (WAF)",                        weight: "high" },
            { id: "APP.06", label: "Đánh giá an toàn mã nguồn (SAST/DAST)",              weight: "high" },
            { id: "APP.07", label: "Lưu nhật ký truy cập tự động (Audit Log)",            weight: "critical" }
        ]
    },
    {
        category: "4. Bảo đảm ATTT Dữ liệu",
        controls: [
            { id: "DAT.01", label: "Sao lưu định kỳ dữ liệu quan trọng",                        weight: "critical" },
            { id: "DAT.02", label: "Phân quyền truy cập theo Need-to-know (Quyền tối thiểu)",    weight: "critical" },
            { id: "DAT.03", label: "Hệ thống sao lưu dự phòng tự động 3-2-1",                   weight: "high" },
            { id: "DAT.04", label: "Mã hóa dữ liệu nhạy cảm tại nơi lưu trữ (TDE)",            weight: "critical" },
            { id: "DAT.05", label: "Hệ thống phòng chống thất thoát dữ liệu (DLP)",             weight: "high" },
            { id: "DAT.06", label: "Quy trình xóa máy móc/tái chế đảm bảo dữ liệu bị hủy",    weight: "medium" }
        ]
    },
    {
        category: "5. Quản lý Vận hành & Chính sách",
        controls: [
            { id: "MNG.01", label: "Ban hành chính sách ATTT được Lãnh đạo phê duyệt",  weight: "critical" },
            { id: "MNG.02", label: "Có cán bộ chuyên trách an toàn thông tin",           weight: "critical" },
            { id: "MNG.03", label: "Hệ thống giám sát sự cố tập trung (SIEM / SOC)",    weight: "critical" },
            { id: "MNG.04", label: "Quy trình ứng cứu sự cố và diễn tập ATTT hàng năm", weight: "high" },
            { id: "MNG.05", label: "Kiểm tra đánh giá rủi ro định kỳ (Pentest)",        weight: "high" }
        ]
    }
];

// Bảng điểm trọng số: critical=4, high=3, medium=2, low=1
export const WEIGHT_SCORE = { critical: 4, high: 3, medium: 2, low: 1 };

// Tính điểm có trọng số từ danh sách controls đã tick
export function calcWeightedScore(implementedIds, allControls) {
    const allFlat = allControls.flatMap(cat => cat.controls)
    const weightMap = {}
    allFlat.forEach(c => { weightMap[c.id] = WEIGHT_SCORE[c.weight] || 1 })
    const maxScore = allFlat.reduce((s, c) => s + (WEIGHT_SCORE[c.weight] || 1), 0)
    const achieved  = implementedIds.reduce((s, id) => s + (weightMap[id] || 0), 0)
    return {
        achieved,
        maxScore,
        percent: maxScore > 0 ? parseFloat(((achieved / maxScore) * 100).toFixed(1)) : 0
    }
}

// Built-in standards (always available)
export const BUILTIN_STANDARDS = [
    { id: "iso27001",  name: "ISO 27001:2022 (93 Biện pháp kiểm soát)",       controls: ISO_27001_CONTROLS, source: "builtin" },
    { id: "tcvn11930", name: "TCVN 11930:2017 (34 Yêu cầu kỹ thuật/quản lý)", controls: TCVN_11930_CONTROLS, source: "builtin" }
];

// ASSESSMENT_STANDARDS is mutable — starts with built-ins, custom standards are merged at runtime
export const ASSESSMENT_STANDARDS = [...BUILTIN_STANDARDS];

/**
 * Merge a custom standard (loaded from backend) into the ASSESSMENT_STANDARDS array.
 * If a standard with the same id already exists, it replaces it.
 * @param {Object} std - { id, name, controls: [{category, controls: [{id, label, weight}]}] }
 */
export function mergeCustomStandard(std) {
    if (!std || !std.id || !std.controls) return
    const existingIdx = ASSESSMENT_STANDARDS.findIndex(s => s.id === std.id)
    const entry = {
        id: std.id,
        name: std.name || std.id,
        controls: std.controls,
        source: "custom",
        version: std.version || "",
        description: std.description || "",
        controlDescriptions: std.controlDescriptions || {},
    }
    if (existingIdx >= 0) {
        ASSESSMENT_STANDARDS[existingIdx] = entry
    } else {
        ASSESSMENT_STANDARDS.push(entry)
    }
}

/**
 * Remove a custom standard from the ASSESSMENT_STANDARDS array.
 * Cannot remove built-in standards.
 */
export function removeCustomStandard(standardId) {
    const idx = ASSESSMENT_STANDARDS.findIndex(s => s.id === standardId)
    if (idx >= 0 && ASSESSMENT_STANDARDS[idx].source === "custom") {
        ASSESSMENT_STANDARDS.splice(idx, 1)
        return true
    }
    return false
}

/**
 * Calculate per-category scoring breakdown.
 * Returns array of { category, total, implemented, percent, weightScore, maxWeightScore, weightPercent }
 */
export function calcCategoryBreakdown(implementedIds, allControls) {
    return allControls.map(cat => {
        const catControls = cat.controls
        const total = catControls.length
        const implemented = catControls.filter(c => implementedIds.includes(c.id)).length
        const maxWeightScore = catControls.reduce((s, c) => s + (WEIGHT_SCORE[c.weight] || 1), 0)
        const weightScore = catControls
            .filter(c => implementedIds.includes(c.id))
            .reduce((s, c) => s + (WEIGHT_SCORE[c.weight] || 1), 0)
        return {
            category: cat.category,
            total,
            implemented,
            percent: total > 0 ? parseFloat(((implemented / total) * 100).toFixed(1)) : 0,
            weightScore,
            maxWeightScore,
            weightPercent: maxWeightScore > 0 ? parseFloat(((weightScore / maxWeightScore) * 100).toFixed(1)) : 0,
        }
    })
}
