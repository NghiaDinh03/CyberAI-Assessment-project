"""ISO 27001:2022 and TCVN 11930:2017 control catalogs — authoritative server-side data."""

ISO_27001_CATEGORIES = [
    {"category": "A.5 Tổ chức", "controls": [
        {"id": "A.5.1", "label": "Chính sách an toàn thông tin", "weight": "critical"},
        {"id": "A.5.2", "label": "Vai trò và trách nhiệm ATTT", "weight": "critical"},
        {"id": "A.5.3", "label": "Phân tách nhiệm vụ", "weight": "high"},
        {"id": "A.5.4", "label": "Trách nhiệm của ban quản lý", "weight": "high"},
        {"id": "A.5.5", "label": "Liên lạc với cơ quan chức năng", "weight": "medium"},
        {"id": "A.5.6", "label": "Liên lạc với nhóm chuyên gia", "weight": "low"},
        {"id": "A.5.7", "label": "Threat Intelligence", "weight": "medium"},
        {"id": "A.5.8", "label": "ATTT trong quản lý dự án", "weight": "medium"},
        {"id": "A.5.9", "label": "Kiểm kê tài sản thông tin", "weight": "high"},
        {"id": "A.5.10", "label": "Sử dụng tài sản thông tin hợp lệ", "weight": "medium"},
        {"id": "A.5.11", "label": "Hoàn trả tài sản", "weight": "low"},
        {"id": "A.5.12", "label": "Phân loại thông tin", "weight": "high"},
        {"id": "A.5.13", "label": "Ghi nhãn thông tin", "weight": "medium"},
        {"id": "A.5.14", "label": "Truyền tải thông tin", "weight": "high"},
        {"id": "A.5.15", "label": "Kiểm soát truy cập", "weight": "critical"},
        {"id": "A.5.16", "label": "Quản lý danh tính (IAM)", "weight": "critical"},
        {"id": "A.5.17", "label": "Xác thực (MFA/Mật khẩu mạnh)", "weight": "critical"},
        {"id": "A.5.18", "label": "Quyền truy cập", "weight": "critical"},
        {"id": "A.5.19", "label": "ATTT trong quan hệ nhà cung cấp", "weight": "high"},
        {"id": "A.5.20", "label": "Xử lý ATTT trong hợp đồng nhà cung cấp", "weight": "high"},
        {"id": "A.5.21", "label": "Quản lý ATTT chuỗi cung ứng ICT", "weight": "medium"},
        {"id": "A.5.22", "label": "Giám sát dịch vụ nhà cung cấp", "weight": "medium"},
        {"id": "A.5.23", "label": "ATTT khi sử dụng dịch vụ đám mây", "weight": "high"},
        {"id": "A.5.24", "label": "Lập kế hoạch quản lý sự cố ATTT", "weight": "critical"},
        {"id": "A.5.25", "label": "Đánh giá sự kiện ATTT", "weight": "high"},
        {"id": "A.5.26", "label": "Phản ứng sự cố ATTT", "weight": "critical"},
        {"id": "A.5.27", "label": "Rút kinh nghiệm từ sự cố ATTT", "weight": "high"},
        {"id": "A.5.28", "label": "Thu thập bằng chứng (Forensic)", "weight": "medium"},
        {"id": "A.5.29", "label": "ATTT trong giai đoạn gián đoạn (BCP)", "weight": "high"},
        {"id": "A.5.30", "label": "Sẵn sàng ICT cho kinh doanh liên tục (DR)", "weight": "high"},
        {"id": "A.5.31", "label": "Tuân thủ yêu cầu pháp lý", "weight": "critical"},
        {"id": "A.5.32", "label": "Bảo vệ quyền sở hữu trí tuệ", "weight": "medium"},
        {"id": "A.5.33", "label": "Bảo vệ hồ sơ", "weight": "medium"},
        {"id": "A.5.34", "label": "Bảo vệ thông tin cá nhân (PII)", "weight": "critical"},
        {"id": "A.5.35", "label": "Đánh giá độc lập ATTT", "weight": "high"},
        {"id": "A.5.36", "label": "Tuân thủ chính sách và tiêu chuẩn ATTT", "weight": "high"},
        {"id": "A.5.37", "label": "Tài liệu hóa quy trình vận hành", "weight": "medium"},
    ]},
    {"category": "A.6 Con người", "controls": [
        {"id": "A.6.1", "label": "Sàng lọc nhân sự (Background check)", "weight": "high"},
        {"id": "A.6.2", "label": "Điều khoản tuyển dụng (NDA)", "weight": "medium"},
        {"id": "A.6.3", "label": "Nhận thức, đào tạo ATTT", "weight": "critical"},
        {"id": "A.6.4", "label": "Quy trình kỷ luật vi phạm ATTT", "weight": "medium"},
        {"id": "A.6.5", "label": "Trách nhiệm sau chia tay (Offboarding)", "weight": "high"},
        {"id": "A.6.6", "label": "Thỏa thuận không tiết lộ (NDA)", "weight": "high"},
        {"id": "A.6.7", "label": "Làm việc từ xa (Remote work / BYOD)", "weight": "high"},
        {"id": "A.6.8", "label": "Báo cáo sự kiện ATTT", "weight": "high"},
    ]},
    {"category": "A.7 Vật lý", "controls": [
        {"id": "A.7.1", "label": "Vành đai an ninh vật lý", "weight": "high"},
        {"id": "A.7.2", "label": "Kiểm soát vào ra vật lý", "weight": "high"},
        {"id": "A.7.3", "label": "Bảo vệ văn phòng, phòng ban", "weight": "medium"},
        {"id": "A.7.4", "label": "Giám sát an ninh vật lý (CCTV)", "weight": "medium"},
        {"id": "A.7.5", "label": "Bảo vệ trước thiên tai", "weight": "medium"},
        {"id": "A.7.6", "label": "Làm việc trong khu vực an toàn", "weight": "medium"},
        {"id": "A.7.7", "label": "Bàn làm việc sạch, màn hình sạch", "weight": "low"},
        {"id": "A.7.8", "label": "Bố trí và bảo vệ máy chủ/thiết bị", "weight": "high"},
        {"id": "A.7.9", "label": "An ninh tài sản ngoài khuôn viên", "weight": "medium"},
        {"id": "A.7.10", "label": "Quản lý phương tiện lưu trữ", "weight": "high"},
        {"id": "A.7.11", "label": "Dịch vụ hỗ trợ (UPS/Điện/Net)", "weight": "medium"},
        {"id": "A.7.12", "label": "An ninh cáp mạng", "weight": "medium"},
        {"id": "A.7.13", "label": "Bảo trì thiết bị", "weight": "low"},
        {"id": "A.7.14", "label": "Hủy/Tái chế thiết bị an toàn", "weight": "high"},
    ]},
    {"category": "A.8 Công nghệ", "controls": [
        {"id": "A.8.1", "label": "Bảo vệ thiết bị đầu cuối (Endpoint Security)", "weight": "critical"},
        {"id": "A.8.2", "label": "Quản lý quyền truy cập đặc quyền (PAM)", "weight": "critical"},
        {"id": "A.8.3", "label": "Hạn chế truy cập thông tin", "weight": "high"},
        {"id": "A.8.4", "label": "Kiểm soát truy cập mã nguồn", "weight": "high"},
        {"id": "A.8.5", "label": "Xác thực an toàn (MFA)", "weight": "critical"},
        {"id": "A.8.6", "label": "Quản lý công suất (Capacity Planning)", "weight": "medium"},
        {"id": "A.8.7", "label": "Bảo vệ chống mã độc (Anti-Malware/EDR)", "weight": "critical"},
        {"id": "A.8.8", "label": "Quản lý lỗ hổng kỹ thuật (Vulnerability)", "weight": "critical"},
        {"id": "A.8.9", "label": "Quản lý cấu hình (Hardening)", "weight": "critical"},
        {"id": "A.8.10", "label": "Xóa thông tin an toàn", "weight": "medium"},
        {"id": "A.8.11", "label": "Che giấu dữ liệu (Data Masking)", "weight": "medium"},
        {"id": "A.8.12", "label": "Ngăn chặn rò rỉ dữ liệu (DLP)", "weight": "high"},
        {"id": "A.8.13", "label": "Sao lưu thông tin (Backup)", "weight": "critical"},
        {"id": "A.8.14", "label": "Dự phòng thiết bị xử lý thông tin (HA)", "weight": "high"},
        {"id": "A.8.15", "label": "Ghi nhật ký (Logging/SIEM)", "weight": "critical"},
        {"id": "A.8.16", "label": "Hoạt động giám sát (Monitoring/SOC)", "weight": "critical"},
        {"id": "A.8.17", "label": "Đồng bộ đồng hồ (NTP)", "weight": "low"},
        {"id": "A.8.18", "label": "Sử dụng chương trình tiện ích đặc quyền", "weight": "medium"},
        {"id": "A.8.19", "label": "Quản lý cài đặt phần mềm", "weight": "medium"},
        {"id": "A.8.20", "label": "An ninh mạng (Firewall)", "weight": "critical"},
        {"id": "A.8.21", "label": "An ninh dịch vụ mạng", "weight": "high"},
        {"id": "A.8.22", "label": "Phân tách mạng (VLAN/DMZ)", "weight": "high"},
        {"id": "A.8.23", "label": "Lọc web (Web Filtering)", "weight": "medium"},
        {"id": "A.8.24", "label": "Sử dụng mã hóa (Cryptography)", "weight": "critical"},
        {"id": "A.8.25", "label": "Vòng đời phát triển an toàn (SDLC/DevSecOps)", "weight": "high"},
        {"id": "A.8.26", "label": "Yêu cầu bảo mật ứng dụng", "weight": "high"},
        {"id": "A.8.27", "label": "Kiến trúc hệ thống an toàn", "weight": "high"},
        {"id": "A.8.28", "label": "Lập trình an toàn (Secure Coding)", "weight": "medium"},
        {"id": "A.8.29", "label": "Kiểm thử bảo mật (Pentest/SAST/DAST)", "weight": "high"},
        {"id": "A.8.30", "label": "Giám sát phát triển thuê ngoài", "weight": "medium"},
        {"id": "A.8.31", "label": "Phân tách môi trường Dev/Test/Prod", "weight": "high"},
        {"id": "A.8.32", "label": "Quản lý thay đổi (Change Management)", "weight": "high"},
        {"id": "A.8.33", "label": "Bảo vệ thông tin kiểm thử", "weight": "medium"},
        {"id": "A.8.34", "label": "Bảo vệ hệ thống trong quá trình kiểm toán", "weight": "medium"},
    ]},
]

TCVN_11930_CATEGORIES = [
    {"category": "1. Bảo đảm ATTT Mạng", "controls": [
        {"id": "NW.01", "label": "Kiểm soát truy cập vùng mạng (ACL)", "weight": "critical"},
        {"id": "NW.02", "label": "Tường lửa (Firewall) bảo vệ vùng biên", "weight": "critical"},
        {"id": "NW.03", "label": "Hệ thống phát hiện/ngăn chặn xâm nhập (IDS/IPS)", "weight": "critical"},
        {"id": "NW.04", "label": "Mã hóa đường truyền truy cập từ xa (VPN)", "weight": "high"},
        {"id": "NW.05", "label": "Phân tách vùng mạng công cộng và nội bộ (DMZ)", "weight": "critical"},
        {"id": "NW.06", "label": "Lọc địa chỉ MAC (Port Security)", "weight": "medium"},
        {"id": "NW.07", "label": "Quản lý truy cập mạng NAC", "weight": "high"},
        {"id": "NW.08", "label": "Đường truyền vật lý dự phòng khác tuyến", "weight": "high"},
    ]},
    {"category": "2. Bảo đảm ATTT Máy chủ", "controls": [
        {"id": "SV.01", "label": "Mật khẩu phức tạp & Đóng dịch vụ không cần thiết", "weight": "critical"},
        {"id": "SV.02", "label": "Phần mềm chống mã độc (Antivirus)", "weight": "critical"},
        {"id": "SV.03", "label": "Hệ thống chống xâm nhập máy chủ (EDR/XDR)", "weight": "critical"},
        {"id": "SV.04", "label": "Giám sát tính toàn vẹn tệp tin (FIM)", "weight": "high"},
        {"id": "SV.05", "label": "Quản lý truy cập đặc quyền (PAM)", "weight": "critical"},
        {"id": "SV.06", "label": "Xác thực đa yếu tố (MFA) cho root/admin", "weight": "critical"},
        {"id": "SV.07", "label": "Cập nhật bản vá định kỳ (Patch Management)", "weight": "critical"},
        {"id": "SV.08", "label": "Thiết lập cấu hình an toàn (Hardening / CIS)", "weight": "critical"},
    ]},
    {"category": "3. Bảo đảm ATTT Ứng dụng", "controls": [
        {"id": "APP.01", "label": "Mã hóa mật khẩu CSDL (Bcrypt, SHA-256)", "weight": "critical"},
        {"id": "APP.02", "label": "Kết nối an toàn HTTPS/TLS 1.2+", "weight": "critical"},
        {"id": "APP.03", "label": "Kiểm soát đầu vào người dùng (Chống SQLi, XSS)", "weight": "critical"},
        {"id": "APP.04", "label": "Giới hạn thời gian phiên làm việc (Session Timeout)", "weight": "high"},
        {"id": "APP.05", "label": "Ngăn chặn tấn công Web (WAF)", "weight": "high"},
        {"id": "APP.06", "label": "Đánh giá an toàn mã nguồn (SAST/DAST)", "weight": "high"},
        {"id": "APP.07", "label": "Lưu nhật ký truy cập tự động (Audit Log)", "weight": "critical"},
    ]},
    {"category": "4. Bảo đảm ATTT Dữ liệu", "controls": [
        {"id": "DAT.01", "label": "Sao lưu định kỳ dữ liệu quan trọng", "weight": "critical"},
        {"id": "DAT.02", "label": "Phân quyền truy cập theo Need-to-know", "weight": "critical"},
        {"id": "DAT.03", "label": "Hệ thống sao lưu dự phòng tự động 3-2-1", "weight": "high"},
        {"id": "DAT.04", "label": "Mã hóa dữ liệu nhạy cảm tại nơi lưu trữ (TDE)", "weight": "critical"},
        {"id": "DAT.05", "label": "Hệ thống phòng chống thất thoát dữ liệu (DLP)", "weight": "high"},
        {"id": "DAT.06", "label": "Quy trình xóa máy móc/tái chế đảm bảo dữ liệu bị hủy", "weight": "medium"},
    ]},
    {"category": "5. Quản lý Vận hành & Chính sách", "controls": [
        {"id": "MNG.01", "label": "Ban hành chính sách ATTT được Lãnh đạo phê duyệt", "weight": "critical"},
        {"id": "MNG.02", "label": "Có cán bộ chuyên trách an toàn thông tin", "weight": "critical"},
        {"id": "MNG.03", "label": "Hệ thống giám sát sự cố tập trung (SIEM / SOC)", "weight": "critical"},
        {"id": "MNG.04", "label": "Quy trình ứng cứu sự cố và diễn tập ATTT hàng năm", "weight": "high"},
        {"id": "MNG.05", "label": "Kiểm tra đánh giá rủi ro định kỳ (Pentest)", "weight": "high"},
    ]},
]

BUILTIN_CONTROLS = {
    "iso27001": ISO_27001_CATEGORIES,
    "tcvn11930": TCVN_11930_CATEGORIES,
}

WEIGHT_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def get_categories(standard: str, custom_std: dict = None) -> list:
    if custom_std:
        return custom_std.get("controls", [])
    return BUILTIN_CONTROLS.get(standard, ISO_27001_CATEGORIES)


def get_flat_controls(standard: str, custom_std: dict = None) -> list:
    cats = get_categories(standard, custom_std)
    return [ctrl for cat in cats for ctrl in cat.get("controls", [])]


def calc_compliance(implemented: list, standard: str, custom_std: dict = None) -> dict:
    flat = get_flat_controls(standard, custom_std)
    if not flat:
        total = 93 if standard != "tcvn11930" else 34
        return {"score": len(implemented), "max_score": total,
                "percentage": round(len(implemented) / total * 100, 1) if total else 0}
    weight_map = {c["id"]: WEIGHT_SCORE.get(c.get("weight", "medium"), 1) for c in flat}
    max_w = sum(weight_map.values())
    achieved_w = sum(weight_map.get(cid, 0) for cid in implemented)
    pct = round(achieved_w / max_w * 100, 1) if max_w > 0 else 0
    return {
        "score": len(implemented),
        "max_score": len(flat),
        "max_weighted": max_w,
        "achieved_weighted": achieved_w,
        "percentage": pct,
    }


def build_weight_breakdown(implemented: list, all_controls: list) -> tuple:
    breakdown = {w: {"total": 0, "implemented": 0} for w in WEIGHT_SCORE}
    missing_by_weight = {w: [] for w in WEIGHT_SCORE}
    for ctrl in all_controls:
        w = ctrl.get("weight", "medium")
        if w not in breakdown:
            continue
        breakdown[w]["total"] += 1
        if ctrl["id"] in implemented:
            breakdown[w]["implemented"] += 1
        else:
            missing_by_weight[w].append(f"{ctrl['id']} ({ctrl.get('label', '')})")
    return breakdown, missing_by_weight
