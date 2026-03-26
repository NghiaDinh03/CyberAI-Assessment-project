# NIST SP 800-53 Rev 5 — Security and Privacy Controls

## Tổng quan

NIST Special Publication 800-53 Revision 5 là catalog kiểm soát bảo mật và riêng tư toàn diện nhất cho hệ thống thông tin liên bang Hoa Kỳ, được áp dụng rộng rãi trong doanh nghiệp toàn cầu.

- **Tên đầy đủ**: Security and Privacy Controls for Information Systems and Organizations
- **Phiên bản**: Revision 5 (2020)
- **Tổ chức**: NIST, USA
- **Mối quan hệ với ISO 27001**: NIST 800-53 chi tiết hơn, có thể dùng để triển khai ISO 27001

## 20 Control Families (Nhóm kiểm soát)

### AC — Access Control (Kiểm soát truy cập)
- Yêu cầu: Quản lý quyền truy cập theo nguyên tắc tối thiểu đặc quyền, phân tách nhiệm vụ.
- Tiêu chí: Có chính sách AC, quản lý tài khoản, phân quyền dựa trên vai trò (RBAC), kiểm soát từ xa.
- Mức độ ưu tiên: HIGH

### AU — Audit and Accountability (Kiểm toán và Trách nhiệm)
- Yêu cầu: Ghi nhật ký đầy đủ, bảo vệ log, phân tích và xem xét log định kỳ.
- Tiêu chí: Audit events được định nghĩa, log được bảo vệ khỏi sửa đổi, xem xét log theo lịch.
- Mức độ ưu tiên: HIGH

### AT — Awareness and Training (Nhận thức và Đào tạo)
- Yêu cầu: Chương trình đào tạo nhận thức bảo mật cho tất cả người dùng.
- Tiêu chí: Đào tạo định kỳ (ít nhất hàng năm), đào tạo theo vai trò, ghi nhận hoàn thành.
- Mức độ ưu tiên: HIGH

### CA — Assessment, Authorization, Monitoring
- Yêu cầu: Đánh giá kiểm soát bảo mật định kỳ, ủy quyền vận hành hệ thống.
- Tiêu chí: Đánh giá rủi ro định kỳ, kế hoạch bảo mật, giám sát liên tục.
- Mức độ ưu tiên: HIGH

### CM — Configuration Management (Quản lý cấu hình)
- Yêu cầu: Duy trì baseline cấu hình, kiểm soát thay đổi, tối giản hóa chức năng.
- Tiêu chí: Danh sách phần mềm được phê duyệt, CMDB, change management process.
- Mức độ ưu tiên: HIGH

### CP — Contingency Planning (Kế hoạch dự phòng)
- Yêu cầu: Kế hoạch dự phòng cho hệ thống, backup, phục hồi sau thảm họa.
- Tiêu chí: BCP/DRP được tài liệu hóa và kiểm tra, RPO/RTO được xác định.
- Mức độ ưu tiên: HIGH

### IA — Identification and Authentication
- Yêu cầu: Xác định và xác thực người dùng, thiết bị, quy trình.
- Tiêu chí: MFA cho tài khoản đặc quyền, chính sách mật khẩu mạnh, quản lý định danh tập trung.
- Mức độ ưu tiên: HIGH

### IR — Incident Response (Ứng phó sự cố)
- Yêu cầu: Kế hoạch ứng phó sự cố, đội ứng phó, diễn tập định kỳ.
- Tiêu chí: IRP được phê duyệt, đội CSIRT, diễn tập tabletop hàng năm, báo cáo sự cố.
- Mức độ ưu tiên: HIGH

### MA — Maintenance (Bảo trì)
- Yêu cầu: Kiểm soát bảo trì hệ thống, kiểm soát thiết bị bảo trì, nhân viên bảo trì.
- Tiêu chí: Lịch bảo trì định kỳ, kiểm soát truy cập bảo trì từ xa.
- Mức độ ưu tiên: MEDIUM

### MP — Media Protection (Bảo vệ phương tiện)
- Yêu cầu: Bảo vệ, kiểm soát, tiêu hủy phương tiện lưu trữ.
- Tiêu chí: Mã hóa phương tiện di động, quy trình tiêu hủy an toàn, kiểm soát truy cập.
- Mức độ ưu tiên: MEDIUM

### PE — Physical and Environmental Protection
- Yêu cầu: Bảo vệ vật lý cho cơ sở và hệ thống CNTT.
- Tiêu chí: Kiểm soát ra vào, giám sát CCTV, bảo vệ điện lực, kiểm soát nhiệt độ/độ ẩm.
- Mức độ ưu tiên: HIGH

### PL — Planning (Lập kế hoạch)
- Yêu cầu: Kế hoạch bảo mật hệ thống, quy tắc ứng xử, kế hoạch riêng tư.
- Tiêu chí: SSP được cập nhật, quy tắc ứng xử người dùng được ký kết.
- Mức độ ưu tiên: MEDIUM

### PS — Personnel Security (Bảo mật nhân sự)
- Yêu cầu: Kiểm tra lý lịch, điều khoản tuyển dụng, kết thúc việc làm an toàn.
- Tiêu chí: Background check trước khi tuyển dụng, NDA, quy trình offboarding.
- Mức độ ưu tiên: HIGH

### RA — Risk Assessment (Đánh giá rủi ro)
- Yêu cầu: Đánh giá rủi ro định kỳ, scan lỗ hổng, xác định mối đe dọa.
- Tiêu chí: Risk assessment hàng năm, vulnerability scanning định kỳ, threat modeling.
- Mức độ ưu tiên: HIGH

### SA — System and Services Acquisition
- Yêu cầu: Tích hợp bảo mật vào vòng đời phát triển, quản lý chuỗi cung ứng.
- Tiêu chí: SDLC security requirements, mã nguồn được review, quản lý nhà cung cấp.
- Mức độ ưu tiên: HIGH

### SC — System and Communications Protection
- Yêu cầu: Phân tách mạng, bảo vệ ranh giới, mã hóa truyền thông.
- Tiêu chí: Phân tách mạng, DMZ, mã hóa TLS/IPSec, kiểm soát luồng thông tin.
- Mức độ ưu tiên: HIGH

### SI — System and Information Integrity
- Yêu cầu: Bảo vệ chống mã độc, quản lý lỗ hổng, giám sát hệ thống.
- Tiêu chí: Anti-malware/EDR triển khai, patch management, IDS/IPS hoạt động.
- Mức độ ưu tiên: HIGH

## Mức độ Tác động (Impact Level)
- **LOW**: Hệ thống ít quan trọng, tổn thất hạn chế.
- **MODERATE**: Hệ thống quan trọng, tổn thất nghiêm trọng nếu bị xâm phạm.
- **HIGH**: Hệ thống quan trọng, tổn thất thảm khốc nếu bị xâm phạm.
