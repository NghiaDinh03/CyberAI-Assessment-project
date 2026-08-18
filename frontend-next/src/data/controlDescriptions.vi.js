export const CONTROL_DESCRIPTIONS = {
    // === ISO 27001:2022 — Annex A Controls ===

    // A.5 Organizational Controls
    "A.5.1": {
        requirement: "Xây dựng, phê duyệt và truyền đạt chính sách ATTT phù hợp với mục tiêu tổ chức.",
        criteria: "Có chính sách ATTT được lãnh đạo cấp cao phê duyệt, truyền đạt toàn bộ nhân viên, xem xét định kỳ."
    },
    "A.5.2": {
        requirement: "Phân công rõ ràng vai trò, trách nhiệm về ATTT.",
        criteria: "Có ma trận RACI cho các vai trò ATTT: CISO, quản trị viên hệ thống, người dùng cuối."
    },
    "A.5.3": {
        requirement: "Các nhiệm vụ xung đột và vùng trách nhiệm phải được phân tách.",
        criteria: "Không có một cá nhân nào kiểm soát toàn bộ giao dịch quan trọng. Người phê duyệt khác người thực hiện."
    },
    "A.5.4": {
        requirement: "Ban quản lý yêu cầu nhân viên và nhà thầu tuân thủ chính sách ATTT.",
        criteria: "Có cam kết bằng văn bản, đào tạo nhận thức ATTT cho quản lý."
    },
    "A.5.5": {
        requirement: "Thiết lập và duy trì liên lạc với cơ quan quản lý, chức năng liên quan.",
        criteria: "Có danh sách liên hệ cơ quan công an, CERT, cơ quan quản lý viễn thông."
    },
    "A.5.6": {
        requirement: "Thiết lập liên lạc với các nhóm chuyên gia, diễn đàn ATTT.",
        criteria: "Tham gia cộng đồng ATTT, theo dõi cảnh báo an ninh mạng."
    },
    "A.5.7": {
        requirement: "Thu thập và phân tích thông tin về các mối đe dọa ATTT.",
        criteria: "Có quy trình tiếp nhận và xử lý Threat Intelligence feeds."
    },
    "A.5.8": {
        requirement: "Tích hợp ATTT vào quản lý dự án.",
        criteria: "Mỗi dự án có đánh giá rủi ro ATTT, yêu cầu bảo mật từ giai đoạn thiết kế."
    },
    "A.5.9": {
        requirement: "Lập và duy trì danh mục tài sản thông tin (bao gồm người chịu trách nhiệm).",
        criteria: "Có danh mục tài sản được cập nhật, phân loại: phần cứng, phần mềm, dữ liệu, con người."
    },
    "A.5.10": {
        requirement: "Quy tắc sử dụng tài sản thông tin phải được xác định và tài liệu hóa.",
        criteria: "Có chính sách sử dụng chấp nhận được (Acceptable Use Policy)."
    },
    "A.5.11": {
        requirement: "Nhân viên và bên ngoài phải hoàn trả tài sản khi chấm dứt hợp đồng.",
        criteria: "Quy trình offboarding bao gồm kiểm tra hoàn trả tài sản IT."
    },
    "A.5.12": {
        requirement: "Thông tin phải được phân loại theo giá trị, yêu cầu pháp lý, mức độ nhạy cảm.",
        criteria: "Có 3-4 mức phân loại: Công khai, Nội bộ, Bí mật, Tối mật."
    },
    "A.5.13": {
        requirement: "Thông tin phải được ghi nhãn phù hợp với sơ đồ phân loại.",
        criteria: "Tài liệu có watermark/header phân loại, email có nhãn mức độ bảo mật."
    },
    "A.5.14": {
        requirement: "Quy tắc, thủ tục truyền tải thông tin cho mọi loại phương tiện.",
        criteria: "Mã hóa email nhạy cảm, VPN cho truyền dữ liệu, hạn chế USB."
    },
    "A.5.15": {
        requirement: "Thiết lập và triển khai chính sách kiểm soát truy cập vật lý và logic.",
        criteria: "Nguyên tắc Need-to-know và Least Privilege được áp dụng."
    },
    "A.5.16": {
        requirement: "Quản lý vòng đời đầy đủ của danh tính.",
        criteria: "Hệ thống IAM (Identity & Access Management), tài khoản duy nhất cho mỗi người."
    },
    "A.5.17": {
        requirement: "Sử dụng công nghệ xác thực phù hợp với mức độ nhạy cảm.",
        criteria: "MFA cho hệ thống quan trọng, chính sách mật khẩu mạnh (12+ ký tự)."
    },
    "A.5.18": {
        requirement: "Cung cấp, xem xét, sửa đổi và thu hồi quyền truy cập theo chính sách.",
        criteria: "Review quyền định kỳ (tối thiểu 6 tháng/lần), thu hồi ngay khi nghỉ việc."
    },
    "A.5.19": {
        requirement: "Xác định và triển khai biện pháp quản lý rủi ro từ nhà cung cấp.",
        criteria: "Điều khoản ATTT trong hợp đồng, đánh giá rủi ro nhà cung cấp."
    },
    "A.5.20": {
        requirement: "Các yêu cầu ATTT được đưa vào thỏa thuận với nhà cung cấp.",
        criteria: "NDA, SLA bảo mật, quyền kiểm toán."
    },
    "A.5.21": {
        requirement: "Quản lý rủi ro ATTT liên quan đến chuỗi cung ứng sản phẩm/dịch vụ ICT.",
        criteria: "Đánh giá bảo mật nhà cung cấp phần mềm, kiểm tra mã nguồn bên thứ ba."
    },
    "A.5.22": {
        requirement: "Giám sát, xem xét, đánh giá và quản lý thay đổi dịch vụ nhà cung cấp.",
        criteria: "Báo cáo định kỳ từ nhà cung cấp, đánh giá lại khi có thay đổi."
    },
    "A.5.23": {
        requirement: "Thiết lập quy trình quản lý ATTT khi sử dụng dịch vụ đám mây.",
        criteria: "Chính sách Cloud Security, đánh giá CSP, mã hóa dữ liệu trên cloud."
    },
    "A.5.24": {
        requirement: "Lập kế hoạch và chuẩn bị cho việc quản lý sự cố ATTT.",
        criteria: "Có Incident Response Plan, đội CSIRT/SOC, diễn tập sự cố hàng năm."
    },
    "A.5.25": {
        requirement: "Đánh giá sự kiện ATTT và quyết định có phải là sự cố không.",
        criteria: "Quy trình phân loại sự kiện, thang đo mức độ nghiêm trọng."
    },
    "A.5.26": {
        requirement: "Phản ứng sự cố theo quy trình đã thiết lập.",
        criteria: "Quy trình escalation, thời gian phản ứng (SLA), ghi chép sự cố."
    },
    "A.5.27": {
        requirement: "Kiến thức từ sự cố được sử dụng để cải tiến biện pháp phòng ngừa.",
        criteria: "Post-incident review, cập nhật biện pháp phòng ngừa."
    },
    "A.5.28": {
        requirement: "Thiết lập quy trình thu thập, bảo quản bằng chứng số.",
        criteria: "Chain of custody, log preservation, forensic readiness."
    },
    "A.5.29": {
        requirement: "Duy trì ATTT trong tình huống gián đoạn hoạt động.",
        criteria: "BCP (Business Continuity Plan) bao gồm yêu cầu ATTT."
    },
    "A.5.30": {
        requirement: "Đảm bảo sẵn sàng ICT để duy trì hoạt động kinh doanh.",
        criteria: "DR Plan, RTO/RPO xác định, backup tested, failover procedures."
    },
    "A.5.31": {
        requirement: "Xác định và tuân thủ các yêu cầu pháp lý liên quan đến ATTT.",
        criteria: "Danh mục luật/quy định áp dụng: Luật An ninh mạng VN, PDPA, GDPR nếu có."
    },
    "A.5.32": {
        requirement: "Bảo vệ quyền sở hữu trí tuệ.",
        criteria: "Quản lý license phần mềm, kiểm tra bản quyền."
    },
    "A.5.33": {
        requirement: "Bảo vệ hồ sơ khỏi mất mát, hủy hoại, giả mạo.",
        criteria: "Chính sách lưu trữ hồ sơ, thời gian lưu giữ, mã hóa."
    },
    "A.5.34": {
        requirement: "Tuân thủ quy định về quyền riêng tư và bảo vệ PII.",
        criteria: "DPIA (Data Protection Impact Assessment), đồng ý xử lý dữ liệu, DPO nếu cần."
    },
    "A.5.35": {
        requirement: "Đánh giá độc lập ATTT theo khoảng thời gian đã lên kế hoạch.",
        criteria: "Audit nội bộ hàng năm, pentest độc lập, báo cáo đánh giá."
    },
    "A.5.36": {
        requirement: "Xem xét định kỳ việc tuân thủ chính sách ATTT.",
        criteria: "Kiểm tra tuân thủ hàng quý, báo cáo vi phạm."
    },
    "A.5.37": {
        requirement: "Tài liệu hóa các quy trình vận hành.",
        criteria: "SOP cho vận hành IT, quản lý thay đổi, backup."
    },

    // A.6 People Controls
    "A.6.1": {
        requirement: "Kiểm tra lý lịch nhân viên trước khi tuyển dụng.",
        criteria: "Background check, xác minh bằng cấp, kiểm tra tiền án."
    },
    "A.6.2": {
        requirement: "Hợp đồng lao động bao gồm trách nhiệm ATTT.",
        criteria: "NDA, điều khoản bảo mật trong hợp đồng."
    },
    "A.6.3": {
        requirement: "Tất cả nhân viên được đào tạo ATTT phù hợp.",
        criteria: "Chương trình đào tạo hàng năm, phishing simulation, kiểm tra nhận thức."
    },
    "A.6.4": {
        requirement: "Quy trình kỷ luật cho vi phạm chính sách ATTT.",
        criteria: "Có quy trình rõ ràng, công bằng, được truyền đạt."
    },
    "A.6.5": {
        requirement: "Trách nhiệm ATTT vẫn có hiệu lực sau khi chấm dứt hợp đồng.",
        criteria: "NDA còn hiệu lực, thu hồi tài khoản trong 24h."
    },
    "A.6.6": {
        requirement: "Thỏa thuận bảo mật với nhân viên và bên ngoài.",
        criteria: "NDA được ký, xem xét định kỳ."
    },
    "A.6.7": {
        requirement: "Biện pháp bảo mật khi làm việc từ xa.",
        criteria: "VPN bắt buộc, chính sách BYOD, mã hóa thiết bị."
    },
    "A.6.8": {
        requirement: "Cơ chế báo cáo sự kiện ATTT cho nhân viên.",
        criteria: "Kênh báo cáo rõ ràng: hotline, email, ticketing system."
    },

    // A.7 Physical Controls
    "A.7.1": {
        requirement: "Xác định vành đai bảo vệ các khu vực chứa thông tin nhạy cảm.",
        criteria: "Tường, cửa khóa, hàng rào cho data center và server room."
    },
    "A.7.2": {
        requirement: "Kiểm soát truy cập vật lý vào các khu vực an toàn.",
        criteria: "Thẻ từ/biometric, log ra vào, escort cho khách."
    },
    "A.7.3": {
        requirement: "Thiết kế và áp dụng biện pháp bảo vệ vật lý cho văn phòng.",
        criteria: "Khóa tủ tài liệu, clean desk policy, camera giám sát."
    },
    "A.7.4": {
        requirement: "Giám sát liên tục các khu vực nhạy cảm.",
        criteria: "CCTV 24/7, lưu trữ ít nhất 30 ngày, giám sát thời gian thực."
    },
    "A.7.5": {
        requirement: "Biện pháp chống thiên tai, cháy, lũ, mất điện.",
        criteria: "UPS, máy phát điện, hệ thống chữa cháy tự động, kiểm soát nhiệt độ."
    },
    "A.7.6": {
        requirement: "Quy tắc làm việc trong khu vực an toàn.",
        criteria: "Cấm thiết bị ghi hình, giám sát nhân viên, hạn chế số người vào."
    },
    "A.7.7": {
        requirement: "Chính sách bàn sạch và màn hình khóa.",
        criteria: "Tự động khóa màn hình sau 5 phút, tủ có khóa cho tài liệu."
    },
    "A.7.8": {
        requirement: "Đặt thiết bị ở vị trí an toàn, bảo vệ khỏi rủi ro.",
        criteria: "Server rack có khóa, cáp gọn gàng, nhãn thiết bị."
    },
    "A.7.9": {
        requirement: "Bảo vệ tài sản khi mang ra ngoài khuôn viên.",
        criteria: "Mã hóa ổ cứng laptop, tracking thiết bị, bảo hiểm."
    },
    "A.7.10": {
        requirement: "Quản lý phương tiện lưu trữ theo vòng đời.",
        criteria: "Mã hóa USB/ổ cứng di động, hủy an toàn (degaussing/shredding)."
    },
    "A.7.11": {
        requirement: "Bảo vệ thiết bị khỏi mất điện và sự cố tiện ích.",
        criteria: "Nguồn điện dự phòng, đường internet backup."
    },
    "A.7.12": {
        requirement: "Bảo vệ cáp nguồn và cáp mạng.",
        criteria: "Cáp trong ống luồn, nhãn cáp, fiber optic cho backbone."
    },
    "A.7.13": {
        requirement: "Bảo trì thiết bị đúng cách để đảm bảo tính khả dụng.",
        criteria: "Lịch bảo trì, ghi chép bảo trì, nhân viên được ủy quyền."
    },
    "A.7.14": {
        requirement: "Xóa sạch dữ liệu trước khi xử lý/tái sử dụng thiết bị.",
        criteria: "Quy trình data wiping (DoD 5220.22-M hoặc NIST 800-88)."
    },

    // A.8 Technological Controls
    "A.8.1": {
        requirement: "Bảo vệ thông tin trên thiết bị đầu cuối người dùng.",
        criteria: "Antivirus/EDR, mã hóa ổ đĩa (BitLocker), policy GPO."
    },
    "A.8.2": {
        requirement: "Hạn chế và quản lý quyền truy cập đặc quyền.",
        criteria: "PAM (Privileged Access Management), tài khoản admin riêng biệt, logging."
    },
    "A.8.3": {
        requirement: "Hạn chế truy cập dựa trên chính sách kiểm soát truy cập.",
        criteria: "RBAC/ABAC, phân quyền theo nguyên tắc Least Privilege."
    },
    "A.8.4": {
        requirement: "Kiểm soát truy cập đọc/ghi mã nguồn.",
        criteria: "Git access control, code review, branch protection."
    },
    "A.8.5": {
        requirement: "Triển khai cơ chế xác thực an toàn.",
        criteria: "HTTPS, certificate management, OAuth2/SAML."
    },
    "A.8.6": {
        requirement: "Giám sát và quản lý công suất tài nguyên.",
        criteria: "Monitoring (CPU, RAM, Disk), capacity planning, alerting."
    },
    "A.8.7": {
        requirement: "Triển khai biện pháp phát hiện, ngăn chặn và phục hồi từ mã độc.",
        criteria: "Antivirus/EDR trên tất cả endpoint, email gateway filtering, sandbox."
    },
    "A.8.8": {
        requirement: "Xác định, đánh giá và xử lý lỗ hổng kỹ thuật.",
        criteria: "Vulnerability scanning định kỳ (Nessus/OpenVAS), patch management."
    },
    "A.8.9": {
        requirement: "Thiết lập, tài liệu hóa, triển khai, giám sát cấu hình.",
        criteria: "Baseline configuration, hardening guides (CIS Benchmarks)."
    },
    "A.8.10": {
        requirement: "Xóa thông tin khi không còn cần thiết.",
        criteria: "Data retention policy, secure deletion procedures."
    },
    "A.8.11": {
        requirement: "Che giấu dữ liệu theo chính sách kiểm soát truy cập.",
        criteria: "Data masking trong môi trường test/dev, tokenization."
    },
    "A.8.12": {
        requirement: "Áp dụng biện pháp ngăn chặn rò rỉ dữ liệu.",
        criteria: "DLP endpoint và network, giám sát email/USB/cloud upload."
    },
    "A.8.13": {
        requirement: "Sao lưu dữ liệu, phần mềm, cấu hình hệ thống theo chính sách.",
        criteria: "Backup 3-2-1 (3 bản, 2 media, 1 offsite), test restore hàng quý."
    },
    "A.8.14": {
        requirement: "Thiết bị xử lý thông tin phải có dự phòng để đáp ứng tính khả dụng.",
        criteria: "HA (High Availability) cho hệ thống critical, failover cluster."
    },
    "A.8.15": {
        requirement: "Ghi và giám sát log hoạt động, ngoại lệ, lỗi, sự kiện ATTT.",
        criteria: "Centralized logging (SIEM), log retention 12 tháng, tamper-proof."
    },
    "A.8.16": {
        requirement: "Giám sát mạng, hệ thống, ứng dụng để phát hiện bất thường.",
        criteria: "SOC/NOC, alert rules, incident correlation."
    },
    "A.8.17": {
        requirement: "Đồng bộ đồng hồ hệ thống với nguồn thời gian chuẩn.",
        criteria: "NTP server nội bộ, tất cả thiết bị sync."
    },
    "A.8.18": {
        requirement: "Hạn chế và kiểm soát sử dụng chương trình tiện ích đặc quyền.",
        criteria: "Application whitelisting, logging admin tools usage."
    },
    "A.8.19": {
        requirement: "Quy trình kiểm soát cài đặt phần mềm.",
        criteria: "Danh sách phần mềm được phê duyệt, kiểm soát admin rights."
    },
    "A.8.20": {
        requirement: "Bảo vệ, quản lý và kiểm soát mạng để bảo vệ thông tin.",
        criteria: "Firewall, network segmentation, VLAN, ACL."
    },
    "A.8.21": {
        requirement: "Xác định, triển khai và giám sát cơ chế an ninh cho dịch vụ mạng.",
        criteria: "SLA với ISP, redundant connectivity, IDS/IPS."
    },
    "A.8.22": {
        requirement: "Phân tách mạng theo nhóm dịch vụ, người dùng, hệ thống.",
        criteria: "DMZ cho server public, VLAN riêng cho server/user/management/guest."
    },
    "A.8.23": {
        requirement: "Quản lý truy cập web để giảm thiểu rủi ro.",
        criteria: "Web filtering proxy, chặn danh mục nguy hiểm."
    },
    "A.8.24": {
        requirement: "Sử dụng mã hóa đúng cách bao gồm quản lý khóa.",
        criteria: "TLS 1.2+ cho transit, AES-256 cho at-rest, certificate management."
    },
    "A.8.25": {
        requirement: "Thiết lập quy tắc phát triển phần mềm/hệ thống an toàn.",
        criteria: "SDLC tích hợp bảo mật (SAST/DAST), code review, penetration testing."
    },
    "A.8.26": {
        requirement: "Xác định và phê duyệt yêu cầu ATTT khi phát triển/mua ứng dụng.",
        criteria: "Security requirements trong user stories, threat modeling."
    },
    "A.8.27": {
        requirement: "Thiết lập nguyên tắc kiến trúc hệ thống an toàn.",
        criteria: "Defense in depth, Zero Trust architecture principles."
    },
    "A.8.28": {
        requirement: "Áp dụng nguyên tắc lập trình an toàn.",
        criteria: "OWASP Top 10, input validation, parameterized queries."
    },
    "A.8.29": {
        requirement: "Thực hiện kiểm thử bảo mật trong quá trình phát triển.",
        criteria: "Unit test bảo mật, SAST/DAST, pentest trước go-live."
    },
    "A.8.30": {
        requirement: "Giám sát hoạt động phát triển phần mềm thuê ngoài.",
        criteria: "Code audit, NDA, kiểm tra bảo mật sản phẩm nhận."
    },
    "A.8.31": {
        requirement: "Phân tách các môi trường dev/test/production.",
        criteria: "Môi trường riêng biệt, không dùng dữ liệu thật cho test."
    },
    "A.8.32": {
        requirement: "Kiểm soát thay đổi đối với hệ thống/ứng dụng.",
        criteria: "Change management process, CAB review, rollback plan."
    },
    "A.8.33": {
        requirement: "Bảo vệ dữ liệu dùng cho kiểm thử.",
        criteria: "Data masking cho test data, không dùng PII thật."
    },
    "A.8.34": {
        requirement: "Lập kế hoạch kiểm toán để giảm thiểu gián đoạn.",
        criteria: "Audit schedule, read-only access cho auditor, giám sát hoạt động audit."
    },

    // === TCVN 11930:2017 Controls ===

    // Network Security
    "NW.01": {
        requirement: "Kiểm soát truy cập giữa các mạng/vùng mạng bằng ACL.",
        criteria: "Thiết bị mạng có cấu hình ACL rõ ràng, đổi mật khẩu mặc định, log truy cập."
    },
    "NW.02": {
        requirement: "Trang bị tường lửa (Firewall) bảo vệ vùng biên mạng.",
        criteria: "Firewall đặt tại biên mạng, rule set được rà soát định kỳ, block traffic mặc định."
    },
    "NW.03": {
        requirement: "Triển khai hệ thống phát hiện/ngăn chặn xâm nhập (IDS/IPS).",
        criteria: "IDS/IPS hoạt động, signature cập nhật, có quy trình xử lý cảnh báo."
    },
    "NW.04": {
        requirement: "Mã hóa đường truyền khi truy cập từ xa bằng VPN.",
        criteria: "VPN cho mọi kết nối từ xa, mã hóa AES-256, xác thực chứng chỉ số."
    },
    "NW.05": {
        requirement: "Phân tách vùng mạng công cộng (DMZ) và nội bộ.",
        criteria: "DMZ riêng biệt cho Web/Mail server, Firewall giữa DMZ và LAN."
    },
    "NW.06": {
        requirement: "Lọc địa chỉ MAC (Port Security) trên switch.",
        criteria: "Port security enabled, giới hạn MAC/port, log cảnh báo thiết bị lạ."
    },
    "NW.07": {
        requirement: "Quản lý truy cập mạng NAC (Network Access Control).",
        criteria: "NAC kiểm tra compliance trước khi cho phép kết nối, cách ly thiết bị vi phạm."
    },
    "NW.08": {
        requirement: "Đường truyền vật lý dự phòng khác tuyến (cho HTTT cấp độ 4, 5).",
        criteria: "Dual ISP, đường cáp vật lý khác tuyến, tự động failover."
    },

    // Server Security
    "SV.01": {
        requirement: "Thiết lập mật khẩu phức tạp và đóng các dịch vụ không cần thiết.",
        criteria: "Mật khẩu 12+ ký tự, đặc biệt + số, disable SSH root, đóng port thừa."
    },
    "SV.02": {
        requirement: "Cài đặt phần mềm chống mã độc (Antivirus) trên máy chủ.",
        criteria: "Antivirus active, cập nhật signature tự động, quét real-time."
    },
    "SV.03": {
        requirement: "Triển khai hệ thống chống xâm nhập máy chủ (EDR/XDR).",
        criteria: "EDR trên tất cả server, threat detection, auto-response rules."
    },
    "SV.04": {
        requirement: "Giám sát tính toàn vẹn tệp tin (File Integrity Monitoring).",
        criteria: "FIM hoạt động trên file hệ thống quan trọng, cảnh báo real-time khi thay đổi."
    },
    "SV.05": {
        requirement: "Quản lý truy cập đặc quyền trên máy chủ (PAM).",
        criteria: "Tài khoản admin riêng biệt, session recording, just-in-time access."
    },
    "SV.06": {
        requirement: "Xác thực đa yếu tố (MFA) đối với quyền root/admin.",
        criteria: "MFA bắt buộc cho SSH/RDP admin, OTP hoặc hardware key."
    },
    "SV.07": {
        requirement: "Cập nhật bản vá bảo mật định kỳ (Patch Management).",
        criteria: "Bản vá critical trong 72h, thường trong 30 ngày, test trước khi apply."
    },
    "SV.08": {
        requirement: "Thiết lập cấu hình an toàn (Hardening theo CIS Benchmark).",
        criteria: "CIS Benchmark score > 80%, disable service thừa, audit policy."
    },

    // Application Security
    "APP.01": {
        requirement: "Mã hóa mật khẩu trong CSDL bằng thuật toán an toàn.",
        criteria: "Bcrypt/Argon2 cho mật khẩu, không dùng MD5/SHA1, salt unique."
    },
    "APP.02": {
        requirement: "Kết nối an toàn qua HTTPS/TLS 1.2 trở lên.",
        criteria: "TLS 1.2+, certificate hợp lệ, HSTS enabled, disable TLS 1.0/1.1."
    },
    "APP.03": {
        requirement: "Kiểm soát đầu vào người dùng (chống SQLi, XSS).",
        criteria: "Input validation, parameterized queries, output encoding, CSP header."
    },
    "APP.04": {
        requirement: "Giới hạn thời gian phiên làm việc (Session Timeout).",
        criteria: "Session timeout 15-30 phút, secure/httponly cookie flags."
    },
    "APP.05": {
        requirement: "Ngăn chặn tấn công Web bằng WAF (Web Application Firewall).",
        criteria: "WAF active, OWASP CRS ruleset, custom rules cho ứng dụng."
    },
    "APP.06": {
        requirement: "Đánh giá an toàn mã nguồn (SAST/DAST) trước production.",
        criteria: "SAST trong CI/CD pipeline, DAST trước mỗi release, fix tất cả Critical."
    },
    "APP.07": {
        requirement: "Lưu nhật ký truy cập tự động (Audit Log).",
        criteria: "Log mọi thay đổi dữ liệu (Insert/Update/Delete), who/when/what, tamper-proof."
    },

    // Data Security
    "DAT.01": {
        requirement: "Sao lưu định kỳ dữ liệu quan trọng.",
        criteria: "Backup hàng ngày, full backup hàng tuần, test restore hàng quý."
    },
    "DAT.02": {
        requirement: "Phân quyền truy cập theo nguyên tắc Need-to-know (quyền tối thiểu).",
        criteria: "RBAC, review quyền định kỳ, audit trail cho truy cập dữ liệu nhạy cảm."
    },
    "DAT.03": {
        requirement: "Hệ thống sao lưu dự phòng tự động theo mô hình 3-2-1.",
        criteria: "3 bản sao, 2 media khác nhau, 1 offsite/cloud, RPO/RTO xác định."
    },
    "DAT.04": {
        requirement: "Mã hóa dữ liệu nhạy cảm tại nơi lưu trữ (Encryption at Rest).",
        criteria: "TDE cho database, BitLocker/LUKS cho disk, key management policy."
    },
    "DAT.05": {
        requirement: "Triển khai hệ thống phòng chống thất thoát dữ liệu (DLP).",
        criteria: "DLP endpoint + network, giám sát USB/email/cloud upload, alert & block."
    },
    "DAT.06": {
        requirement: "Quy trình xóa/tái chế thiết bị đảm bảo dữ liệu bị hủy vật lý.",
        criteria: "Data wiping (NIST 800-88), degaussing cho HDD, shredding cho SSD."
    },

    // Management
    "MNG.01": {
        requirement: "Ban hành chính sách ATTT được lãnh đạo cấp cao phê duyệt.",
        criteria: "Chính sách ATTT bằng văn bản, phê duyệt cấp Giám đốc, truyền đạt toàn tổ chức."
    },
    "MNG.02": {
        requirement: "Có cán bộ chuyên trách an toàn thông tin.",
        criteria: "Bộ phận ATTT độc lập hoặc cán bộ chuyên trách, báo cáo trực tiếp lãnh đạo."
    },
    "MNG.03": {
        requirement: "Hệ thống giám sát và cảnh báo sự cố tập trung (SIEM/SOC).",
        criteria: "SIEM hoạt động 24/7, correlation rules, alert escalation, report hàng tháng."
    },
    "MNG.04": {
        requirement: "Có quy trình ứng cứu sự cố và diễn tập ATTT hàng năm.",
        criteria: "Incident Response Plan, diễn tập ít nhất 1 lần/năm, báo cáo kết quả."
    },
    "MNG.05": {
        requirement: "Kiểm tra đánh giá rủi ro định kỳ với bên thứ 3 (Pentest).",
        criteria: "Pentest hàng năm bởi đơn vị độc lập, báo cáo fix timeline, retest."
    }
}
