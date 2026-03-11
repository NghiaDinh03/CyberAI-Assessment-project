export const ISO_27001_CONTROLS = [
    {
        category: "A.5 Tổ chức",
        controls: [
            { id: "A.5.1", label: "Chính sách an toàn thông tin" },
            { id: "A.5.2", label: "Vai trò và trách nhiệm ATTT" },
            { id: "A.5.3", label: "Phân tách nhiệm vụ" },
            { id: "A.5.4", label: "Trách nhiệm của ban quản lý" },
            { id: "A.5.5", label: "Liên lạc với cơ quan chức năng" },
            { id: "A.5.6", label: "Liên lạc với nhóm chuyên gia" },
            { id: "A.5.7", label: "Tình báo mối đe dọa (Threat Intelligence)" },
            { id: "A.5.8", label: "ATTT trong quản lý dự án" },
            { id: "A.5.9", label: "Kiểm kê tài sản thông tin" },
            { id: "A.5.10", label: "Sử dụng tài sản thông tin hợp lệ (AUP)" },
            { id: "A.5.11", label: "Hoàn trả tài sản" },
            { id: "A.5.12", label: "Phân loại thông tin" },
            { id: "A.5.13", label: "Ghi nhãn thông tin" },
            { id: "A.5.14", label: "Truyền tải thông tin" },
            { id: "A.5.15", label: "Kiểm soát truy cập" },
            { id: "A.5.16", label: "Quản lý danh tính (IAM)" },
            { id: "A.5.17", label: "Xác thực (MFA/Mật khẩu mạnh)" },
            { id: "A.5.18", label: "Quyền truy cập" },
            { id: "A.5.19", label: "ATTT trong quan hệ nhà cung cấp" },
            { id: "A.5.20", label: "Xử lý ATTT trong hợp đồng nhà cung cấp" },
            { id: "A.5.21", label: "Quản lý ATTT chuỗi cung ứng ICT" },
            { id: "A.5.22", label: "Giám sát dịch vụ nhà cung cấp" },
            { id: "A.5.23", label: "ATTT khi sử dụng dịch vụ đám mây" },
            { id: "A.5.24", label: "Lập kế hoạch quản lý sự cố ATTT" },
            { id: "A.5.25", label: "Đánh giá sự kiện ATTT" },
            { id: "A.5.26", label: "Phản ứng sự cố ATTT" },
            { id: "A.5.27", label: "Rút kinh nghiệm từ sự cố ATTT" },
            { id: "A.5.28", label: "Thu thập bằng chứng (Forensic)" },
            { id: "A.5.29", label: "ATTT trong giai đoạn gián đoạn (BCP)" },
            { id: "A.5.30", label: "Sẵn sàng ICT cho kinh doanh liên tục (DR)" },
            { id: "A.5.31", label: "Tuân thủ yêu cầu pháp lý" },
            { id: "A.5.32", label: "Bảo vệ quyền sở hữu trí tuệ" },
            { id: "A.5.33", label: "Bảo vệ hồ sơ" },
            { id: "A.5.34", label: "Bảo vệ thông tin cá nhân (PII)" },
            { id: "A.5.35", label: "Đánh giá độc lập ATTT" },
            { id: "A.5.36", label: "Tuân thủ chính sách và tiêu chuẩn ATTT" },
            { id: "A.5.37", label: "Tài liệu hóa quy trình vận hành" }
        ]
    },
    {
        category: "A.6 Con người",
        controls: [
            { id: "A.6.1", label: "Sàng lọc nhân sự (Background check)" },
            { id: "A.6.2", label: "Điều khoản tuyển dụng (NDA)" },
            { id: "A.6.3", label: "Nhận thức, đào tạo ATTT" },
            { id: "A.6.4", label: "Quy trình kỷ luật vi phạm ATTT" },
            { id: "A.6.5", label: "Trách nhiệm sau chia tay (Offboarding)" },
            { id: "A.6.6", label: "Thỏa thuận không tiết lộ (NDA)" },
            { id: "A.6.7", label: "Làm việc từ xa (Remote work / BYOD)" },
            { id: "A.6.8", label: "Báo cáo sự kiện ATTT" }
        ]
    },
    {
        category: "A.7 Vật lý",
        controls: [
            { id: "A.7.1", label: "Vành đai an ninh vật lý" },
            { id: "A.7.2", label: "Kiểm soát vào ra vật lý" },
            { id: "A.7.3", label: "Bảo vệ văn phòng, phòng ban" },
            { id: "A.7.4", label: "Giám sát an ninh vật lý (CCTV)" },
            { id: "A.7.5", label: "Bảo vệ trước thiên tai" },
            { id: "A.7.6", label: "Làm việc trong khu vực an toàn" },
            { id: "A.7.7", label: "Bàn làm việc sạch, màn hình sạch" },
            { id: "A.7.8", label: "Bố trí và bảo vệ máy chủ/thiết bị" },
            { id: "A.7.9", label: "An ninh tài sản ngoài khuôn viên" },
            { id: "A.7.10", label: "Quản lý phương tiện lưu trữ" },
            { id: "A.7.11", label: "Dịch vụ hỗ trợ (UPS/Điện/Net)" },
            { id: "A.7.12", label: "An ninh cáp mạng" },
            { id: "A.7.13", label: "Bảo trì thiết bị" },
            { id: "A.7.14", label: "Hủy/Tái chế thiết bị an toàn" }
        ]
    },
    {
        category: "A.8 Công nghệ",
        controls: [
            { id: "A.8.1", label: "Bảo vệ thiết bị đầu cuối (Endpoint Security)" },
            { id: "A.8.2", label: "Quản lý quyền truy cập đặc quyền (PAM)" },
            { id: "A.8.3", label: "Hạn chế truy cập thông tin" },
            { id: "A.8.4", label: "Kiểm soát truy cập mã nguồn" },
            { id: "A.8.5", label: "Xác thực an toàn (MFA)" },
            { id: "A.8.6", label: "Quản lý công suất (Capacity Planning)" },
            { id: "A.8.7", label: "Bảo vệ chống mã độc (Anti-Malware/EDR)" },
            { id: "A.8.8", label: "Quản lý lỗ hổng kỹ thuật (Vulnerability)" },
            { id: "A.8.9", label: "Quản lý cấu hình (Hardening)" },
            { id: "A.8.10", label: "Xóa thông tin an toàn" },
            { id: "A.8.11", label: "Che giấu dữ liệu (Data Masking)" },
            { id: "A.8.12", label: "Ngăn chặn rò rỉ dữ liệu (DLP)" },
            { id: "A.8.13", label: "Sao lưu thông tin (Backup)" },
            { id: "A.8.14", label: "Dự phòng thiết bị xử lý thông tin (HA)" },
            { id: "A.8.15", label: "Ghi nhật ký (Logging/SIEM)" },
            { id: "A.8.16", label: "Hoạt động giám sát (Monitoring/SOC)" },
            { id: "A.8.17", label: "Đồng bộ đồng hồ (NTP)" },
            { id: "A.8.18", label: "Sử dụng chương trình tiện ích đặc quyền" },
            { id: "A.8.19", label: "Quản lý cài đặt phần mềm" },
            { id: "A.8.20", label: "An ninh mạng (Firewall)" },
            { id: "A.8.21", label: "An ninh dịch vụ mạng" },
            { id: "A.8.22", label: "Phân tách mạng (VLAN/DMZ)" },
            { id: "A.8.23", label: "Lọc web (Web Filtering)" },
            { id: "A.8.24", label: "Sử dụng mã hóa (Cryptography)" },
            { id: "A.8.25", label: "Vòng đời phát triển an toàn (SDLC/DevSecOps)" },
            { id: "A.8.26", label: "Yêu cầu bảo mật ứng dụng" },
            { id: "A.8.27", label: "Kiến trúc hệ thống an toàn" },
            { id: "A.8.28", label: "Lập trình an toàn (Secure Coding)" },
            { id: "A.8.29", label: "Kiểm thử bảo mật (Pentest/SAST/DAST)" },
            { id: "A.8.30", label: "Giám sát phát triển thuê ngoài" },
            { id: "A.8.31", label: "Phân tách môi trường Dev/Test/Prod" },
            { id: "A.8.32", label: "Quản lý thay đổi (Change Management)" },
            { id: "A.8.33", label: "Bảo vệ thông tin kiểm thử" },
            { id: "A.8.34", label: "Bảo vệ hệ thống trong quá trình kiểm toán" }
        ]
    }
];

export const TCVN_11930_CONTROLS = [
    {
        category: "1. Bảo đảm ATTT Mạng",
        controls: [
            { id: "NW.01", label: "Kiểm soát truy cập vùng mạng (Access Control List)" },
            { id: "NW.02", label: "Tường lửa (Firewall) bảo vệ vùng biên" },
            { id: "NW.03", label: "Hệ thống phát hiện/ngăn chặn xâm nhập (IDS/IPS)" },
            { id: "NW.04", label: "Mã hóa đường truyền truy cập từ xa (VPN)" },
            { id: "NW.05", label: "Phân tách vùng mạng công cộng và nội bộ (DMZ)" },
            { id: "NW.06", label: "Lọc địa chỉ MAC (Port Security)" },
            { id: "NW.07", label: "Quản lý truy cập mạng NAC" },
            { id: "NW.08", label: "Đường truyền vật lý dự phòng khác tuyến (Cho cấp độ 4, 5)" }
        ]
    },
    {
        category: "2. Bảo đảm ATTT Máy chủ",
        controls: [
            { id: "SV.01", label: "Mật khẩu phức tạp & Đóng các dịch vụ không cần thiết" },
            { id: "SV.02", label: "Phần mềm chống mã độc (Antivirus)" },
            { id: "SV.03", label: "Hệ thống chống xâm nhập máy chủ (EDR/XDR)" },
            { id: "SV.04", label: "Giám sát tính toàn vẹn tệp tin (FIM)" },
            { id: "SV.05", label: "Quản lý truy cập đặc quyền (PAM)" },
            { id: "SV.06", label: "Xác thực đa yếu tố (MFA) đối với quyền root/admin" },
            { id: "SV.07", label: "Cập nhật bản vá định kỳ (Patch Management)" },
            { id: "SV.08", label: "Thiết lập cấu hình an toàn (Hardening / CIS Benchmark)" }
        ]
    },
    {
        category: "3. Bảo đảm ATTT Ứng dụng",
        controls: [
            { id: "APP.01", label: "Mã hóa mật khẩu CSDL (Bcrypt, SHA-256)" },
            { id: "APP.02", label: "Kết nối an toàn HTTPS/TLS 1.2+" },
            { id: "APP.03", label: "Kiểm soát đầu vào người dùng (Chống SQLi, XSS)" },
            { id: "APP.04", label: "Giới hạn thời gian phiên làm việc (Session Timeout)" },
            { id: "APP.05", label: "Ngăn chặn tấn công Web (Trang bị WAF)" },
            { id: "APP.06", label: "Đánh giá an toàn mã nguồn (SAST/DAST) trước khi lên production" },
            { id: "APP.07", label: "Lưu nhật ký truy cập tự động (Audit Log)" }
        ]
    },
    {
        category: "4. Bảo đảm ATTT Dữ liệu",
        controls: [
            { id: "DAT.01", label: "Sao lưu định kỳ dữ liệu quan trọng" },
            { id: "DAT.02", label: "Phân quyền truy cập theo Need-to-know (Quyền tối thiểu)" },
            { id: "DAT.03", label: "Hệ thống sao lưu dự phòng tự động 3-2-1" },
            { id: "DAT.04", label: "Mã hóa dữ liệu nhạy cảm tại nơi lưu trữ (TDE)" },
            { id: "DAT.05", label: "Hệ thống phòng chống thất thoát dữ liệu (DLP)" },
            { id: "DAT.06", label: "Quy trình xóa máy móc/tái chế đảm bảo dữ liệu bị hủy vật lý" }
        ]
    },
    {
        category: "5. Quản lý Vận hành & Chính sách",
        controls: [
            { id: "MNG.01", label: "Ban hành chính sách ATTT và được Lãnh đạo cấp cao phê duyệt" },
            { id: "MNG.02", label: "Có cán bộ chuyên trách an toàn thông tin" },
            { id: "MNG.03", label: "Hệ thống giám sát và cảnh báo sự cố tập trung (SIEM / SOC)" },
            { id: "MNG.04", label: "Có quy trình ứng cứu sự cố và diễn tập ATTT hàng năm" },
            { id: "MNG.05", label: "Kiểm tra đánh giá rủi ro định kỳ với bên thứ 3 (Pentest)" }
        ]
    }
];

export const ASSESSMENT_STANDARDS = [
    { id: "iso27001", name: "ISO 27001:2022 (93 Biện pháp kiểm soát)", controls: ISO_27001_CONTROLS },
    { id: "tcvn11930", name: "TCVN 11930:2017 (34 Yêu cầu kỹ thuật/quản lý)", controls: TCVN_11930_CONTROLS }
];
