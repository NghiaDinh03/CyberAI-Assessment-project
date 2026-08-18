# HIPAA Security Rule — Health Insurance Portability and Accountability Act

## Tổng quan

HIPAA Security Rule quy định các tiêu chuẩn bảo mật cho thông tin y tế điện tử (ePHI) tại Hoa Kỳ. Áp dụng cho Covered Entities và Business Associates.

- **Tên đầy đủ**: HIPAA Security Rule (45 CFR Part 164)
- **Phát hành**: Hiệu lực 2005, cập nhật HITECH 2009
- **Tổ chức**: U.S. Department of Health and Human Services (HHS)
- **Áp dụng**: Bệnh viện, phòng khám, bảo hiểm y tế, nhà cung cấp dịch vụ y tế, business associates
- **Phạt vi phạm**: $100 - $50,000 per violation, tối đa $1.9M/năm/category

## 3 Loại Biện pháp Bảo vệ

### Administrative Safeguards (Biện pháp Hành chính)

#### Security Management Process (§164.308(a)(1))
- Yêu cầu: Chính sách và quy trình ngăn chặn, phát hiện, kiểm soát vi phạm bảo mật ePHI.
- Tiêu chí: Risk analysis, risk management, sanction policy, information system activity review.
- Controls liên quan ISO 27001: A.5.1, A.5.36

#### Assigned Security Responsibility (§164.308(a)(2))
- Yêu cầu: Phân công cá nhân chịu trách nhiệm phát triển và triển khai security policies.
- Tiêu chí: Designated Security Official, job description, accountability.
- Controls liên quan ISO 27001: A.5.2

#### Workforce Security (§164.308(a)(3))
- Yêu cầu: Đảm bảo nhân viên có quyền truy cập phù hợp và ngăn chặn truy cập trái phép.
- Tiêu chí: Authorization procedures, workforce clearance, termination procedures.
- Controls liên quan ISO 27001: A.6.1, A.6.5, A.5.16

#### Information Access Management (§164.308(a)(4))
- Yêu cầu: Quy trình ủy quyền truy cập ePHI.
- Tiêu chí: Isolating healthcare clearinghouse functions, access authorization, modification procedures.
- Controls liên quan ISO 27001: A.5.15, A.5.18

#### Security Awareness and Training (§164.308(a)(5))
- Yêu cầu: Chương trình đào tạo bảo mật cho tất cả workforce.
- Tiêu chí: Security reminders, protection from malicious software, log-in monitoring, password management.
- Controls liên quan ISO 27001: A.6.3

#### Security Incident Procedures (§164.308(a)(6))
- Yêu cầu: Chính sách ứng phó và báo cáo sự cố bảo mật.
- Tiêu chí: Response and reporting procedures, incident documentation.
- Controls liên quan ISO 27001: A.5.24, A.5.26

#### Contingency Plan (§164.308(a)(7))
- Yêu cầu: Kế hoạch ứng phó khi hệ thống khẩn cấp ảnh hưởng đến ePHI.
- Tiêu chí: Data backup plan, disaster recovery plan, emergency mode operation, testing, applications criticality analysis.
- Controls liên quan ISO 27001: A.5.29, A.5.30, A.8.13

### Physical Safeguards (Biện pháp Vật lý)

#### Facility Access Controls (§164.310(a))
- Yêu cầu: Kiểm soát truy cập vật lý vào cơ sở có hệ thống thông tin ePHI.
- Tiêu chí: Contingency operations, facility security plan, access control and validation, maintenance records.
- Controls liên quan ISO 27001: A.7.1, A.7.2, A.7.6

#### Workstation Use and Security (§164.310(b)(c))
- Yêu cầu: Chính sách sử dụng workstation hợp lý, bảo vệ vật lý workstation.
- Tiêu chí: Workstation use policies, physical access restrictions to workstations.
- Controls liên quan ISO 27001: A.7.7

#### Device and Media Controls (§164.310(d))
- Yêu cầu: Kiểm soát phần cứng và phương tiện điện tử chứa ePHI.
- Tiêu chí: Disposal procedures, media re-use, accountability, data backup and storage.
- Controls liên quan ISO 27001: A.7.10, A.7.14, A.8.10

### Technical Safeguards (Biện pháp Kỹ thuật)

#### Access Control (§164.312(a))
- Yêu cầu: Kiểm soát truy cập kỹ thuật cho người được ủy quyền vào hệ thống ePHI.
- Tiêu chí: Unique user identification, emergency access, automatic logoff, encryption and decryption.
- Controls liên quan ISO 27001: A.5.16, A.8.5, A.8.24

#### Audit Controls (§164.312(b))
- Yêu cầu: Ghi lại và kiểm tra hoạt động trên hệ thống thông tin có ePHI.
- Tiêu chí: Hardware, software, and procedural mechanisms cho audit trail.
- Controls liên quan ISO 27001: A.8.15, A.8.16

#### Integrity (§164.312(c))
- Yêu cầu: Bảo vệ ePHI khỏi bị sửa đổi hoặc tiêu hủy không đúng.
- Tiêu chí: Electronic mechanism to corroborate ePHI has not been improperly altered or destroyed.
- Controls liên quan ISO 27001: A.8.24

#### Transmission Security (§164.312(e))
- Yêu cầu: Bảo vệ ePHI khi truyền qua mạng điện tử.
- Tiêu chí: Encryption, integrity controls.
- Controls liên quan ISO 27001: A.8.24, A.5.14

## Breach Notification Rule

### Định nghĩa Vi phạm
- Vi phạm = acquisition, access, use, disclosure của ePHI không được phép.
- Phải thông báo cho affected individuals trong 60 ngày.
- Vi phạm > 500 cá nhân: phải thông báo HHS và phương tiện truyền thông địa phương.

## So sánh HIPAA với ISO 27001

| Tiêu chí | HIPAA | ISO 27001 |
|---|---|---|
| Phạm vi | ePHI — Thông tin y tế điện tử | Tất cả thông tin tổ chức |
| Tính bắt buộc | Luật liên bang Mỹ | Tự nguyện (hoặc theo hợp đồng) |
| Chứng nhận | Không có chứng chỉ chính thức | Chứng nhận ISO bởi CB |
| Risk Analysis | Bắt buộc | Bắt buộc |
