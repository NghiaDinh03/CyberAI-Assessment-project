# GAP Analysis Patterns — Mẫu Phân tích Khoảng cách An toàn Thông tin

## Tổng quan

Tài liệu này cung cấp các mẫu phân tích GAP phổ biến, tiêu chí đánh giá rủi ro và khuyến nghị chuẩn cho các loại tổ chức khác nhau.

## Phương pháp GAP Analysis

### Định nghĩa GAP
GAP = Khoảng cách giữa trạng thái hiện tại và yêu cầu tiêu chuẩn.

### Phân loại GAP theo Severity

#### 🔴 Critical (Tối quan trọng) — Risk Score ≥ 16
- Định nghĩa: Lỗ hổng có thể dẫn đến vi phạm dữ liệu nghiêm trọng, gián đoạn dịch vụ quan trọng, hoặc vi phạm pháp luật.
- Ví dụ: Không có MFA cho admin, không backup dữ liệu quan trọng, không có firewall, mật khẩu mặc định.
- Timeline khắc phục: Ngay lập tức (0-7 ngày).
- Controls ISO 27001 thường gặp: A.5.17, A.8.5, A.8.13, A.8.20, A.5.24.

#### 🟠 High (Quan trọng) — Risk Score 9-15
- Định nghĩa: Lỗ hổng có thể bị khai thác và gây hại đáng kể.
- Ví dụ: Patch management yếu, không có IDS/IPS, log không đầy đủ, VPN không được mã hóa đúng.
- Timeline khắc phục: 1-4 tuần.
- Controls ISO 27001 thường gặp: A.8.8, A.8.15, A.8.16, A.8.24.

#### 🟡 Medium (Trung bình) — Risk Score 4-8
- Định nghĩa: Lỗ hổng có thể bị khai thác nhưng yêu cầu điều kiện đặc biệt.
- Ví dụ: Chính sách mật khẩu yếu, thiếu tài liệu hóa quy trình, chưa có đào tạo nhận thức.
- Timeline khắc phục: 1-3 tháng.

#### ⚪ Low (Thấp) — Risk Score 1-3
- Định nghĩa: Lỗ hổng ít khả năng bị khai thác hoặc tác động hạn chế.
- Ví dụ: Thiếu một số tài liệu, quy trình chưa được cập nhật, nhãn phân loại thông tin không đầy đủ.
- Timeline khắc phục: 3-12 tháng.

## GAP Phổ biến theo Loại Tổ chức

### Ngân hàng và Tài chính

#### GAP thường gặp
- Thiếu kiểm tra xâm nhập định kỳ (Pentest/Red Team) — Severity: High
- Chưa triển khai Zero Trust Architecture — Severity: High
- Phân tách môi trường Development/Production chưa đầy đủ — Severity: Medium
- Chưa có quy trình Security Champion trong SDLC — Severity: Medium

#### Yêu cầu đặc thù ngành
- PCI DSS compliance cho xử lý thẻ thanh toán
- SWIFT Customer Security Programme (CSP) cho giao dịch liên ngân hàng
- Thông tư 09/2020/TT-NHNN về an toàn hệ thống thông tin

### Y tế và Bệnh viện

#### GAP thường gặp
- CSDL bệnh nhân không mã hóa — Severity: Critical
- Thiết bị y tế kết nối mạng không được bảo vệ (IoMT) — Severity: Critical
- Không có quy trình xử lý sự cố lộ lọt dữ liệu bệnh nhân — Severity: High
- Wi-Fi dùng chung nhân viên và khách — Severity: High

#### Yêu cầu đặc thù ngành
- Thông tư 46/2018/TT-BYT về hồ sơ bệnh án điện tử
- Nghị định 13/2023 về bảo vệ dữ liệu cá nhân (đặc biệt dữ liệu sức khỏe)

### Startup và SaaS

#### GAP thường gặp
- Thiếu tài liệu hóa quy trình IT — Severity: Medium
- Chưa có chính sách BYOD/Remote Work chính thức — Severity: Medium
- Container security chưa được hardening — Severity: High
- Secrets management (API keys, passwords) không an toàn — Severity: Critical

#### Yêu cầu đặc thù ngành
- SOC 2 Type II cho B2B SaaS
- ISO 27001 cho khách hàng doanh nghiệp lớn

### Cơ quan Nhà nước

#### GAP thường gặp
- Thiếu SIEM/SOC tập trung — Severity: Critical (theo Thông tư 13/2022)
- Chưa đánh giá và phân loại cấp độ HTTT — Severity: High
- Phần mềm hết hạn hỗ trợ (Windows XP, Office 2010) — Severity: Critical
- Chưa có kế hoạch ứng cứu sự cố chính thức — Severity: High

## Risk Scoring Matrix

### Likelihood Scale (L)
| Score | Mô tả |
|---|---|
| 1 | Rất khó xảy ra — Không có history, đòi hỏi kỹ năng cao |
| 2 | Khó xảy ra — Cần điều kiện đặc biệt |
| 3 | Có thể xảy ra — Đã có precedent trong ngành |
| 4 | Khả năng cao — Đã xảy ra với tổ chức tương tự |
| 5 | Rất dễ xảy ra — Đang bị exploit active |

### Impact Scale (I)
| Score | Mô tả |
|---|---|
| 1 | Tối thiểu — Gián đoạn ngắn, không mất dữ liệu |
| 2 | Thấp — Gián đoạn nhỏ, dữ liệu ít nhạy cảm |
| 3 | Trung bình — Gián đoạn đáng kể, dữ liệu nhạy cảm |
| 4 | Cao — Vi phạm dữ liệu lớn, gián đoạn lâu |
| 5 | Nghiêm trọng — Gián đoạn dịch vụ quan trọng, vi phạm pháp lý |

### Risk Score = Likelihood × Impact
- 1-3: Low ⚪
- 4-8: Medium 🟡
- 9-15: High 🟠
- 16-25: Critical 🔴

## Action Plan Template

### Ngắn hạn (0-30 ngày) — Critical và High
1. Khắc phục ngay các lỗ hổng Critical
2. Triển khai biện pháp tạm thời cho High
3. Thu thập bằng chứng triển khai

### Trung hạn (1-3 tháng) — High và Medium
1. Hoàn thiện các biện pháp High
2. Lập kế hoạch và bắt đầu Medium
3. Đào tạo nhân sự về các thay đổi

### Dài hạn (3-12 tháng) — Medium và Low
1. Hoàn thiện Medium
2. Triển khai Low
3. Đánh giá lại và cập nhật Risk Register
4. Chuẩn bị cho chứng nhận (nếu cần)
