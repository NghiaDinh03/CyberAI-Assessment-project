# OWASP Top 10 2021 — Web Application Security Risks

## Tổng quan

OWASP Top 10 là danh sách 10 rủi ro bảo mật ứng dụng web nghiêm trọng nhất, được cập nhật định kỳ bởi Open Web Application Security Project.

- **Tên đầy đủ**: OWASP Top 10 Web Application Security Risks 2021
- **Tổ chức**: Open Web Application Security Project (OWASP)
- **Cập nhật**: 2021 (phiên bản mới nhất)
- **Áp dụng**: Tất cả ứng dụng web, API, mobile backend
- **Controls liên quan ISO 27001**: A.8.25, A.8.26, A.8.27, A.8.28, A.8.29

## 10 Rủi ro Bảo mật Hàng đầu

### A01:2021 — Broken Access Control (Kiểm soát Truy cập Bị phá vỡ)
- Mô tả: Người dùng có thể hành động ngoài quyền hạn của họ (truy cập dữ liệu người dùng khác, chức năng admin).
- Ví dụ: IDOR (Insecure Direct Object Reference), leo thang đặc quyền, CORS misconfiguration.
- Biện pháp: Implement access control server-side, deny by default, log và alert failures.
- Controls liên quan ISO 27001: A.5.15, A.5.18, A.8.3

### A02:2021 — Cryptographic Failures (Lỗi Mã hóa)
- Mô tả: Dữ liệu nhạy cảm không được bảo vệ đúng cách khi lưu trữ và truyền tải.
- Ví dụ: Dữ liệu thẻ tín dụng không mã hóa, mật khẩu MD5/SHA1, HTTP thay vì HTTPS.
- Biện pháp: TLS 1.2+, mã hóa AES-256 at rest, bcrypt/Argon2 cho mật khẩu, no sensitive data in URL.
- Controls liên quan ISO 27001: A.8.24, A.5.14

### A03:2021 — Injection (Tấn công Injection)
- Mô tả: Dữ liệu không tin cậy được gửi đến interpreter như SQL, OS, LDAP, NoSQL.
- Ví dụ: SQL Injection, NoSQL Injection, OS Command Injection, LDAP Injection.
- Biện pháp: Parameterized queries, stored procedures, input validation, escaping, WAF.
- Controls liên quan ISO 27001: A.8.25, A.8.26

### A04:2021 — Insecure Design (Thiết kế Không an toàn)
- Mô tả: Thiếu hoặc yếu trong thiết kế và kiến trúc bảo mật.
- Ví dụ: Không có threat modeling, không có rate limiting, business logic flaws.
- Biện pháp: Secure design patterns, threat modeling, use secure components, reference architectures.
- Controls liên quan ISO 27001: A.8.27, A.5.8

### A05:2021 — Security Misconfiguration (Cấu hình Bảo mật Sai)
- Mô tả: Cấu hình mặc định không an toàn, cấu hình không đầy đủ, lỗi tạm thời.
- Ví dụ: Default credentials, XML external entities, unnecessary features enabled, verbose error messages.
- Biện pháp: Hardening, remove unnecessary features, patch management, automated configuration review.
- Controls liên quan ISO 27001: A.8.9, A.8.8

### A06:2021 — Vulnerable and Outdated Components (Thành phần Lỗi thời)
- Mô tả: Sử dụng thư viện, framework, OS có lỗ hổng đã biết.
- Ví dụ: Log4Shell (Log4j), Struts vulnerabilities, outdated npm packages.
- Biện pháp: Inventory components, check NVD/CVE, SCA tools (Dependabot, Snyk), patch promptly.
- Controls liên quan ISO 27001: A.8.8, A.8.19

### A07:2021 — Identification and Authentication Failures
- Mô tả: Yếu kém trong xác thực, quản lý session, credential management.
- Ví dụ: Brute force không giới hạn, session fixation, mật khẩu yếu, không có MFA.
- Biện pháp: MFA, strong password policy, brute force protection, session timeout, HTTPS-only cookies.
- Controls liên quan ISO 27001: A.5.17, A.8.5

### A08:2021 — Software and Data Integrity Failures
- Mô tả: Code và cơ sở hạ tầng không được bảo vệ chống sửa đổi trái phép.
- Ví dụ: Deserialization không an toàn, CI/CD pipeline không được bảo mật, auto-update không có chữ ký.
- Biện pháp: Ký số, verify integrity, secure CI/CD pipeline, code review.
- Controls liên quan ISO 27001: A.8.25, A.8.32

### A09:2021 — Security Logging and Monitoring Failures
- Mô tả: Thiếu logging, monitoring, alerting cho các sự kiện bảo mật.
- Ví dụ: Login failures không được log, cảnh báo không đến SOC, log không được bảo vệ.
- Biện pháp: Log tất cả authentication, high-value transactions, SIEM integration, alert on suspicious activity.
- Controls liên quan ISO 27001: A.8.15, A.8.16

### A10:2021 — Server-Side Request Forgery (SSRF)
- Mô tả: Ứng dụng fetch URL do user cung cấp mà không validate đúng cách.
- Ví dụ: Truy cập metadata cloud (169.254.169.254), nội mạng, services nội bộ.
- Biện pháp: Whitelist domains, block private IPs, network segmentation, authentication cho internal services.
- Controls liên quan ISO 27001: A.8.22, A.8.20

## OWASP ASVS — Application Security Verification Standard

### Level 1 — Tự xác minh cơ bản
- Tất cả ứng dụng nên đạt mức này.
- Kiểm tra: Input validation, output encoding, auth basics, session management, error handling.

### Level 2 — Xác minh tiêu chuẩn
- Ứng dụng chứa dữ liệu nhạy cảm.
- Kiểm tra: Tất cả Level 1 + cryptography, API security, config management.

### Level 3 — Xác minh nâng cao
- Ứng dụng quan trọng cao (tài chính, y tế, quốc phòng).
- Kiểm tra: Tất cả Level 2 + secure design review, penetration testing toàn diện.

## Checklist Kiểm tra Bảo mật Ứng dụng

### Input Validation
- [ ] Tất cả input từ user được validate server-side
- [ ] Parameterized queries cho tất cả database queries
- [ ] File upload được kiểm tra type, size, content

### Authentication & Session
- [ ] MFA được triển khai
- [ ] Session token ngẫu nhiên, đủ dài (≥ 128 bits)
- [ ] Session invalidation khi logout
- [ ] HTTPS-only session cookies (Secure, HttpOnly, SameSite)

### Authorization
- [ ] Kiểm tra quyền server-side cho mọi request
- [ ] Principle of least privilege
- [ ] Không dựa vào client-side checks

### Cryptography
- [ ] TLS 1.2+ cho tất cả kết nối
- [ ] Dữ liệu nhạy cảm mã hóa at rest (AES-256)
- [ ] Mật khẩu hash với bcrypt/Argon2 (không MD5/SHA1)
