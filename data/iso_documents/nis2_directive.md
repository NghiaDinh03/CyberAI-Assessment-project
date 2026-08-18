# NIS2 Directive — Network and Information Systems Security

## Tổng quan

NIS2 (Network and Information Security Directive 2) là chỉ thị an ninh mạng mới nhất của EU, thay thế NIS Directive 2016, có hiệu lực từ tháng 10/2024.

- **Tên đầy đủ**: Directive (EU) 2022/2555 on measures for a high common level of cybersecurity across the Union
- **Phát hành**: 2022, hiệu lực từ 17/10/2024
- **Tổ chức**: Liên minh Châu Âu
- **Phạt vi phạm**: Essential entities: €10M hoặc 2% doanh thu; Important entities: €7M hoặc 1.4% doanh thu
- **Ảnh hưởng Việt Nam**: Công ty xuất khẩu sang EU hoặc có hoạt động tại EU cần tuân thủ

## Phân loại Tổ chức

### Essential Entities (Tổ chức Thiết yếu)
Bao gồm: Năng lượng, giao thông, ngân hàng, cơ sở hạ tầng tài chính, y tế, nước uống, hạ tầng kỹ thuật số, dịch vụ ICT, không gian.

### Important Entities (Tổ chức Quan trọng)
Bao gồm: Bưu chính, quản lý chất thải, sản xuất, hóa chất, thực phẩm, nhà cung cấp kỹ thuật số.

## 10 Biện pháp Bảo mật Bắt buộc (Article 21)

### 1. Risk Analysis và Security Policy
- Yêu cầu: Chính sách quản lý rủi ro an ninh thông tin và mạng.
- Tiêu chí: Risk assessment hàng năm, security policies được ban quản lý phê duyệt.
- Controls liên quan ISO 27001: A.5.1, A.6.1.1

### 2. Incident Handling
- Yêu cầu: Ngăn chặn, phát hiện, phân tích và phục hồi sau sự cố.
- Tiêu chí: IRP tài liệu hóa, CSIRT, báo cáo trong 24h (early warning), 72h (notification), 1 tháng (final report).
- Controls liên quan ISO 27001: A.5.24, A.5.26, A.5.27

### 3. Business Continuity
- Yêu cầu: Backup management, disaster recovery, crisis management.
- Tiêu chí: BCP/DRP được kiểm tra hàng năm, RPO/RTO được định nghĩa, backup được bảo vệ.
- Controls liên quan ISO 27001: A.5.29, A.5.30, A.8.13

### 4. Supply Chain Security
- Yêu cầu: An ninh trong quan hệ với nhà cung cấp và đối tác chuỗi cung ứng.
- Tiêu chí: Vendor risk assessment, contractual requirements, monitoring nhà cung cấp.
- Controls liên quan ISO 27001: A.5.19, A.5.20, A.5.21, A.5.22

### 5. Security in Network and Information Systems
- Yêu cầu: Bảo mật trong acquisition, development, maintenance hệ thống.
- Tiêu chí: Secure SDLC, vulnerability management, patch management.
- Controls liên quan ISO 27001: A.8.25-A.8.29

### 6. Policies and Procedures for Effectiveness Assessment
- Yêu cầu: Chính sách đánh giá hiệu quả của các biện pháp quản lý rủi ro an ninh mạng.
- Tiêu chí: KPIs bảo mật, audit nội bộ, penetration testing.
- Controls liên quan ISO 27001: A.5.35, A.5.36

### 7. Basic Cyber Hygiene and Cybersecurity Training
- Yêu cầu: Thực hành vệ sinh an ninh mạng cơ bản và đào tạo nhận thức.
- Tiêu chí: Patch management, password hygiene, MFA, đào tạo định kỳ.
- Controls liên quan ISO 27001: A.6.3, A.8.8

### 8. Cryptography and Encryption
- Yêu cầu: Chính sách và thực hành sử dụng mã hóa và quản lý khóa.
- Tiêu chí: Encryption policy, key management procedures, TLS enforcement.
- Controls liên quan ISO 27001: A.8.24

### 9. Human Resources Security và Access Control
- Yêu cầu: Kiểm soát truy cập vật lý và logic, quản lý tài sản.
- Tiêu chí: Access control policy, privileged access management, MFA, background checks.
- Controls liên quan ISO 27001: A.5.15-A.5.18, A.8.2, A.8.5, A.6.1

### 10. Multi-Factor Authentication
- Yêu cầu: Xác thực đa yếu tố hoặc xác thực liên tục, truyền thông bảo mật.
- Tiêu chí: MFA cho tất cả truy cập từ xa và admin, end-to-end encryption cho communications.
- Controls liên quan ISO 27001: A.8.5, A.5.17

## Báo cáo Sự cố NIS2

### Timeline Báo cáo
| Thời hạn | Nội dung |
|---|---|
| 24 giờ | Early warning: loại sự cố, cross-border impact |
| 72 giờ | Notification đầy đủ: severity, initial assessment, indicators |
| 1 tháng | Final report: root cause, mitigations, cross-border impact |

### Tiêu chí Sự cố Đáng kể
- Gây ra disruption nghiêm trọng hoặc thiệt hại tài chính cho tổ chức
- Ảnh hưởng đến người dùng/tổ chức khác

## So sánh NIS vs NIS2

| Tiêu chí | NIS (2016) | NIS2 (2022) |
|---|---|---|
| Phạm vi | Operators of Essential Services + DSPs | Mở rộng đáng kể (medium-large enterprises) |
| Phạt | Không thống nhất | Harmonized max penalties |
| Supply chain | Không yêu cầu | Bắt buộc |
| Incident reporting | 72h | 24h early warning + 72h notification |
| Management accountability | Hạn chế | Ban quản lý chịu trách nhiệm trực tiếp |
