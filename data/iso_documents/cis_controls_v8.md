# CIS Controls v8 — Center for Internet Security

## Tổng quan

CIS Controls là bộ kiểm soát bảo mật thực tiễn được phát triển bởi cộng đồng chuyên gia toàn cầu, tập trung vào các biện pháp hiệu quả nhất để ngăn chặn các cuộc tấn công mạng phổ biến.

- **Tên đầy đủ**: CIS Critical Security Controls Version 8
- **Phiên bản**: v8 (2021)
- **Tổ chức**: Center for Internet Security (CIS)
- **Áp dụng**: Mọi tổ chức, theo Implementation Groups (IG1/IG2/IG3)

## 18 CIS Controls

### CIS Control 1 — Kiểm kê và Kiểm soát Tài sản Doanh nghiệp
- Yêu cầu: Quản lý tích cực tất cả thiết bị phần cứng trong mạng.
- Tiêu chí: CMDB/asset inventory đầy đủ, scanning định kỳ, unauthorized device detection.
- IG: IG1 (cơ bản)
- Controls liên quan ISO 27001: A.5.9

### CIS Control 2 — Kiểm kê và Kiểm soát Tài sản Phần mềm
- Yêu cầu: Chỉ cho phép phần mềm được ủy quyền chạy trên thiết bị.
- Tiêu chí: Software whitelist, unauthorized software detection, license management.
- IG: IG1
- Controls liên quan ISO 27001: A.5.9, A.8.19

### CIS Control 3 — Bảo vệ Dữ liệu
- Yêu cầu: Phân loại, xử lý và bảo vệ dữ liệu theo mức độ nhạy cảm.
- Tiêu chí: Phân loại dữ liệu, mã hóa lưu trữ và truyền, DLP, data retention.
- IG: IG1
- Controls liên quan ISO 27001: A.5.12, A.8.24, A.8.12

### CIS Control 4 — Cấu hình An toàn Tài sản và Phần mềm
- Yêu cầu: Thiết lập và duy trì cấu hình bảo mật cho thiết bị và phần mềm.
- Tiêu chí: Hardening standards (CIS Benchmarks), automated configuration management.
- IG: IG1
- Controls liên quan ISO 27001: A.8.9

### CIS Control 5 — Quản lý Tài khoản
- Yêu cầu: Sử dụng các quy trình và công cụ để phân công và quản lý tài khoản.
- Tiêu chí: Account inventory, service account management, inactive account removal.
- IG: IG1
- Controls liên quan ISO 27001: A.5.16

### CIS Control 6 — Quản lý Kiểm soát Truy cập
- Yêu cầu: Tạo, gán, quản lý và thu hồi thông tin xác thực và đặc quyền.
- Tiêu chí: MFA, RBAC, privileged account management, password manager.
- IG: IG1
- Controls liên quan ISO 27001: A.5.15, A.5.17, A.8.2, A.8.5

### CIS Control 7 — Quản lý Lỗ hổng Liên tục
- Yêu cầu: Phát triển kế hoạch quản lý lỗ hổng liên tục.
- Tiêu chí: Vulnerability scan hàng tuần, patch theo CVSS score, tracking remediation.
- IG: IG1
- Controls liên quan ISO 27001: A.8.8

### CIS Control 8 — Quản lý Nhật ký Kiểm toán
- Yêu cầu: Thu thập, cảnh báo, xem xét và lưu giữ audit logs.
- Tiêu chí: Log từ tất cả systems, SIEM, retention ≥ 90 ngày hot, 1 năm tổng.
- IG: IG1
- Controls liên quan ISO 27001: A.8.15, A.8.17

### CIS Control 9 — Bảo vệ Email và Trình duyệt Web
- Yêu cầu: Cải thiện bảo vệ chống mối đe dọa qua email và web.
- Tiêu chí: Email filtering (anti-spam, anti-phishing), web filtering, DNS filtering.
- IG: IG1
- Controls liên quan ISO 27001: A.8.23

### CIS Control 10 — Phòng thủ Chống Phần mềm Độc hại
- Yêu cầu: Ngăn ngừa hoặc kiểm soát cài đặt, lây lan, thực thi mã độc.
- Tiêu chí: Anti-malware/EDR, application whitelisting, USB control, macro control.
- IG: IG1
- Controls liên quan ISO 27001: A.8.7

### CIS Control 11 — Phục hồi Dữ liệu
- Yêu cầu: Thực hành và kiểm tra quy trình backup/restore.
- Tiêu chí: Backup tự động, kiểm tra restore định kỳ, offline/offsite backup, encryption.
- IG: IG1
- Controls liên quan ISO 27001: A.8.13

### CIS Control 12 — Quản lý Cơ sở hạ tầng Mạng
- Yêu cầu: Thiết lập, triển khai, quản lý và giám sát cơ sở hạ tầng mạng.
- Tiêu chí: Network diagram, VLAN segmentation, firewall rules review, network monitoring.
- IG: IG2
- Controls liên quan ISO 27001: A.8.20, A.8.21, A.8.22

### CIS Control 13 — Giám sát và Phòng thủ Mạng
- Yêu cầu: Giám sát lưu lượng mạng, phát hiện và ngăn chặn tấn công.
- Tiêu chí: IDS/IPS, network traffic analysis (NTA), DNS logging, honeypots.
- IG: IG2
- Controls liên quan ISO 27001: A.8.16

### CIS Control 14 — Nhận thức và Đào tạo Kỹ năng Bảo mật
- Yêu cầu: Thiết lập và duy trì chương trình nhận thức bảo mật.
- Tiêu chí: Đào tạo định kỳ, phishing simulation, role-based security training.
- IG: IG1
- Controls liên quan ISO 27001: A.6.3

### CIS Control 15 — Quản lý Nhà cung cấp Dịch vụ
- Yêu cầu: Quy trình để đánh giá nhà cung cấp dịch vụ xử lý dữ liệu nhạy cảm.
- Tiêu chí: Vendor assessment, contract requirements, monitoring, offboarding.
- IG: IG2
- Controls liên quan ISO 27001: A.5.19, A.5.20, A.5.22

### CIS Control 16 — Bảo mật Ứng dụng
- Yêu cầu: Quản lý vòng đời bảo mật ứng dụng phát triển nội bộ và mua.
- Tiêu chí: SAST/DAST, code review, OWASP Top 10 mitigation, WAF.
- IG: IG2
- Controls liên quan ISO 27001: A.8.25, A.8.26, A.8.29

### CIS Control 17 — Quản lý Ứng phó Sự cố
- Yêu cầu: Thiết lập chương trình quản lý sự cố để chuẩn bị, phát hiện, phân tích.
- Tiêu chí: IRP, CSIRT, tabletop exercises, post-incident review.
- IG: IG1
- Controls liên quan ISO 27001: A.5.24, A.5.25, A.5.26, A.5.27

### CIS Control 18 — Kiểm tra Xâm nhập
- Yêu cầu: Kiểm tra hiệu quả và khả năng phục hồi của tổ chức thông qua pentest.
- Tiêu chí: Pentest nội bộ và bên ngoài hàng năm, bug bounty, red team exercises.
- IG: IG2
- Controls liên quan ISO 27001: A.8.29

## Implementation Groups

| Group | Tổ chức | Controls áp dụng |
|---|---|---|
| IG1 | Nhỏ, ít IT staff, dữ liệu ít nhạy cảm | Controls cơ bản (56 safeguards) |
| IG2 | Trung bình, có IT team, dữ liệu nhạy cảm | IG1 + thêm controls kỹ thuật |
| IG3 | Lớn, có security team, dữ liệu rất nhạy cảm | Tất cả 153 safeguards |
