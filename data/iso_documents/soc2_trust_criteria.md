# SOC 2 Type II — Service Organization Control

## Tổng quan

SOC 2 là tiêu chuẩn kiểm toán do AICPA (American Institute of Certified Public Accountants) phát triển cho các tổ chức dịch vụ công nghệ lưu trữ dữ liệu khách hàng trên đám mây.

- **Tên đầy đủ**: System and Organization Controls 2
- **Tổ chức**: AICPA (American Institute of Certified Public Accountants)
- **Loại**: Type I — kiểm tra thiết kế controls tại thời điểm; Type II — kiểm tra hiệu quả hoạt động trong kỳ (6-12 tháng)
- **Áp dụng**: SaaS, cloud service providers, data centers, MSPs

## 5 Trust Service Criteria (TSC)

### CC — Common Criteria (Bắt buộc)
Bao gồm 9 nhóm kiểm soát chung:

#### CC1 — Control Environment (Môi trường kiểm soát)
- Yêu cầu: Cam kết với integrity và ethical values, board oversight, tổ chức và authority.
- Tiêu chí: Code of conduct, governance structure, competency standards.

#### CC2 — Communication and Information
- Yêu cầu: Thông tin liên lạc nội bộ và bên ngoài về security policies.
- Tiêu chí: Security awareness training, customer communication, incident notification.

#### CC3 — Risk Assessment
- Yêu cầu: Quy trình đánh giá rủi ro, xác định gian lận, thay đổi ảnh hưởng.
- Tiêu chí: Risk assessment process, risk register, fraud risk assessment.

#### CC4 — Monitoring Activities
- Yêu cầu: Đánh giá và truyền đạt kết quả giám sát.
- Tiêu chí: Internal audit function, remediation tracking, external assessments.

#### CC5 — Control Activities
- Yêu cầu: Lựa chọn, phát triển và triển khai controls.
- Tiêu chí: Control policies, segregation of duties, automated controls.

#### CC6 — Logical and Physical Access Controls
- Yêu cầu: Hạn chế và quản lý truy cập logic và vật lý.
- Tiêu chí: Authentication (MFA), authorization (RBAC), access reviews, physical security.
- Controls liên quan ISO 27001: A.5.15-A.5.18, A.7.1-A.7.2, A.8.2, A.8.5

#### CC7 — System Operations
- Yêu cầu: Phát hiện và giám sát mối đe dọa, ứng phó sự cố.
- Tiêu chí: SIEM/IDS, vulnerability management, incident response, change management.
- Controls liên quan ISO 27001: A.8.8, A.8.15, A.8.16, A.5.24-A.5.27

#### CC8 — Change Management
- Yêu cầu: Kiểm soát thay đổi cơ sở hạ tầng và phần mềm.
- Tiêu chí: Change control process, testing environments, rollback procedures, approvals.
- Controls liên quan ISO 27001: A.8.32

#### CC9 — Risk Mitigation
- Yêu cầu: Quản lý rủi ro bên thứ ba, bảo hiểm.
- Tiêu chí: Vendor risk assessment, contract reviews, business continuity.
- Controls liên quan ISO 27001: A.5.19-A.5.22, A.5.29

### A — Availability (Tính sẵn sàng) — Tùy chọn
- Yêu cầu: Hệ thống hoạt động đáp ứng SLA cam kết.
- Tiêu chí: Uptime monitoring, disaster recovery, capacity planning, incident response SLA.
- Controls liên quan ISO 27001: A.8.14, A.5.30

### C — Confidentiality (Bảo mật) — Tùy chọn
- Yêu cầu: Thông tin được đánh dấu là bí mật được bảo vệ đúng cách.
- Tiêu chí: Data classification, encryption at rest and in transit, data disposal.
- Controls liên quan ISO 27001: A.5.12, A.8.24, A.8.10

### I — Processing Integrity (Tính toàn vẹn xử lý) — Tùy chọn
- Yêu cầu: Xử lý hệ thống hoàn chỉnh, hợp lệ, chính xác, kịp thời.
- Tiêu chí: Input validation, processing controls, error handling, output reconciliation.
- Controls liên quan ISO 27001: A.8.25, A.8.26

### P — Privacy (Riêng tư) — Tùy chọn
- Yêu cầu: Thu thập, sử dụng, lưu giữ, tiết lộ thông tin cá nhân theo GDPR/CCPA.
- Tiêu chí: Privacy notice, consent management, data subject rights, retention policy.
- Controls liên quan ISO 27001: A.5.34, A.5.33

## So sánh SOC 2 với ISO 27001

| Tiêu chí | SOC 2 | ISO 27001 |
|---|---|---|
| Mục đích | Kiểm toán báo cáo cho khách hàng | Chứng nhận ISMS |
| Kiểm toán viên | CPA/AICPA | CB được accredit |
| Phạm vi | Dịch vụ cụ thể | Toàn tổ chức hoặc scope định nghĩa |
| Thời gian | Type II: 6-12 tháng | 3 năm (tái chứng nhận hàng năm) |
| Phổ biến | Mỹ, SaaS/Cloud | Toàn cầu |
