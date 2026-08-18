# PCI DSS 4.0 — Payment Card Industry Data Security Standard

## Tổng quan

PCI DSS là tiêu chuẩn bảo mật dữ liệu cho ngành thanh toán thẻ, bắt buộc cho mọi tổ chức xử lý, lưu trữ hoặc truyền dữ liệu thẻ thanh toán.

- **Tên đầy đủ**: Payment Card Industry Data Security Standard Version 4.0
- **Phát hành**: 2022 (hiệu lực đầy đủ từ 2025)
- **Tổ chức**: PCI Security Standards Council
- **Áp dụng**: Merchant, service provider xử lý dữ liệu Cardholder Data (CHD)

## 12 Requirements chính

### Requirement 1: Cài đặt và duy trì kiểm soát an ninh mạng
- Yêu cầu: Cấu hình firewall/router để bảo vệ môi trường dữ liệu thẻ (CDE).
- Tiêu chí: Network diagram cập nhật, rule firewall được review 6 tháng/lần, DMZ cho public-facing services.
- Controls liên quan ISO 27001: A.8.20, A.8.22

### Requirement 2: Áp dụng cấu hình an toàn cho tất cả thành phần hệ thống
- Yêu cầu: Thay đổi mật khẩu mặc định của vendor, loại bỏ chức năng không cần thiết.
- Tiêu chí: CIS benchmarks hoặc vendor hardening guides được áp dụng, inventory đầy đủ.
- Controls liên quan ISO 27001: A.8.9, A.8.19

### Requirement 3: Bảo vệ dữ liệu thẻ được lưu trữ
- Yêu cầu: Tối thiểu hóa lưu trữ CHD, mã hóa PAN, không lưu sensitive authentication data.
- Tiêu chí: Không lưu CVV/CVC sau khi xác thực, PAN được masked hoặc mã hóa (AES-256).
- Controls liên quan ISO 27001: A.8.24, A.5.34

### Requirement 4: Bảo vệ dữ liệu thẻ khi truyền qua mạng công cộng
- Yêu cầu: Mã hóa mạnh (TLS 1.2+) cho truyền CHD qua internet.
- Tiêu chí: TLS 1.2 hoặc 1.3, không dùng SSL/TLS cũ, certificate hợp lệ.
- Controls liên quan ISO 27001: A.8.24, A.5.14

### Requirement 5: Bảo vệ chống phần mềm độc hại
- Yêu cầu: Anti-malware trên tất cả systems, cập nhật định kỳ.
- Tiêu chí: AV/EDR triển khai, auto-update, không thể tắt bởi user thông thường.
- Controls liên quan ISO 27001: A.8.7

### Requirement 6: Phát triển và bảo trì hệ thống và phần mềm an toàn
- Yêu cầu: Secure SDLC, patch management, bảo vệ ứng dụng web.
- Tiêu chí: Patch critical trong 1 tháng, WAF cho public web apps, SAST/DAST trong SDLC.
- Controls liên quan ISO 27001: A.8.25, A.8.29, A.8.8

### Requirement 7: Hạn chế truy cập vào dữ liệu thẻ theo business need
- Yêu cầu: Least privilege — chỉ cấp quyền cần thiết, xem xét quyền định kỳ.
- Tiêu chí: Role-based access control, access review hàng quý, tài liệu hóa quyền truy cập.
- Controls liên quan ISO 27001: A.5.15, A.5.18

### Requirement 8: Xác định người dùng và xác thực truy cập hệ thống
- Yêu cầu: MFA cho tất cả truy cập vào CDE, quản lý mật khẩu mạnh.
- Tiêu chí: MFA bắt buộc, mật khẩu ≥ 12 ký tự, thay đổi mật khẩu khi có nguy cơ.
- Controls liên quan ISO 27001: A.5.17, A.8.5

### Requirement 9: Hạn chế truy cập vật lý vào dữ liệu thẻ
- Yêu cầu: Kiểm soát ra vào khu vực lưu trữ CHD, quản lý visitors, bảo vệ thiết bị.
- Tiêu chí: Thẻ từ/PIN kiểm soát vào khu vực nhạy cảm, log ra vào, camera CCTV.
- Controls liên quan ISO 27001: A.7.2, A.7.4

### Requirement 10: Log và giám sát tất cả truy cập vào tài nguyên mạng và CHD
- Yêu cầu: Audit log đầy đủ, đồng bộ thời gian, review log hàng ngày.
- Tiêu chí: Log tất cả admin actions, login failures, truy cập CHD; lưu ≥ 12 tháng.
- Controls liên quan ISO 27001: A.8.15, A.8.16

### Requirement 11: Kiểm tra bảo mật hệ thống và mạng định kỳ
- Yêu cầu: Vulnerability scan hàng quý, penetration test hàng năm, IDS/IPS.
- Tiêu chí: ASV scan hàng quý, pentest nội bộ hàng năm, IDS/IPS với signature cập nhật.
- Controls liên quan ISO 27001: A.8.8, A.8.29

### Requirement 12: Hỗ trợ bảo mật thông tin với chính sách và chương trình tổ chức
- Yêu cầu: Chính sách bảo mật, chương trình nhận thức, quản lý sự cố, quản lý nhà cung cấp.
- Tiêu chí: Chính sách cập nhật hàng năm, đào tạo nhận thức, IRP được kiểm tra.
- Controls liên quan ISO 27001: A.5.1, A.5.24, A.5.19

## Các mức độ Tuân thủ PCI DSS

| Level | Mô tả | Yêu cầu |
|---|---|---|
| Level 1 | > 6 triệu transactions/năm | Báo cáo hàng năm bởi QSA, ASV scan hàng quý |
| Level 2 | 1-6 triệu transactions/năm | Self-Assessment Questionnaire, ASV scan |
| Level 3 | 20,000-1 triệu e-commerce | SAQ, ASV scan |
| Level 4 | < 20,000 e-commerce | SAQ, có thể không cần ASV |
