# Checklist Đánh giá Toàn diện Hệ thống CNTT theo ISO 27001 và Pháp luật Việt Nam

## Hướng dẫn sử dụng
Tài liệu này cung cấp danh mục kiểm tra toàn diện để đánh giá mức độ an toàn của hệ thống CNTT. Áp dụng cho tất cả quy mô doanh nghiệp tại Việt Nam, phù hợp cho việc đánh giá trước khi lấy chứng nhận ISO 27001:2022 hoặc tuân thủ TCVN 11930:2017.

## 1. Đánh giá Hạ tầng Phần cứng

### Server và Trung tâm dữ liệu
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| Phòng server | Có kiểm soát nhiệt độ 18-27°C, độ ẩm 40-60% | A.7.5, A.7.8 |
| Hệ thống chữa cháy | FM-200 hoặc Novec cho phòng server | A.7.5 |
| UPS | Dự phòng tối thiểu 30 phút tải đầy | A.7.11 |
| Máy phát điện | Tự động chuyển đổi (ATS) khi mất điện lưới | A.7.11 |
| Kiểm soát ra vào | Thẻ từ hoặc vân tay, ghi log ra vào | A.7.1, A.7.2 |
| Camera giám sát | CCTV 24/7, lưu trữ tối thiểu 30 ngày | A.7.4 |
| Server rack | Có khóa, cable management, nhãn rõ ràng | A.7.8 |
| Nguồn điện dự phòng | PDU kép cho thiết bị quan trọng | A.7.11 |

### Thiết bị mạng
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| Firewall | Next-Gen Firewall với IPS/IDS, HA pair | A.8.20 |
| Switch L3 | Core switch có dự phòng, VLAN configuration | A.8.22 |
| Access Point | WiFi WPA3-Enterprise, RADIUS authentication | A.8.20 |
| VPN Gateway | IPSec/SSL VPN cho remote access | A.6.7 |
| Load Balancer | HA cho web services critical | A.8.14 |
| IDS/IPS | Phát hiện và ngăn chặn xâm nhập real-time | A.8.16 |

### Thiết bị lưu trữ
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| NAS/SAN | RAID 5/6, dual controller | A.8.13 |
| Tape backup | Offsite storage, ghi nhãn, mã hóa | A.8.13 |
| Cloud backup | Mã hóa AES-256, region tại Việt Nam | A.8.13, Luật ANM |

## 2. Đánh giá Phần mềm và Ứng dụng

### Hệ điều hành
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| Bản vá bảo mật | Cập nhật trong vòng 30 ngày (critical) | A.8.8 |
| Hardening | Theo CIS Benchmark, tắt dịch vụ không cần thiết | A.8.9 |
| Antivirus/EDR | Cài đặt và cập nhật trên tất cả endpoint | A.8.7 |
| Disk encryption | BitLocker hoặc FileVault cho laptop | A.8.1 |
| Firewall OS | Bật firewall local, chỉ mở port cần thiết | A.8.20 |

### Ứng dụng Web
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| HTTPS | TLS 1.2+ cho tất cả traffic | A.8.24 |
| WAF | Web Application Firewall cho ứng dụng public | A.8.20 |
| Input validation | Chống SQL injection, XSS, CSRF | A.8.28 |
| Session management | Timeout, secure cookie, HTTPS only | A.8.5 |
| Pentest | Kiểm thử bảo mật trước go-live | A.8.29 |

### Cơ sở dữ liệu
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| Mã hóa dữ liệu | TDE hoặc column-level encryption cho dữ liệu nhạy cảm | A.8.24 |
| Backup | Tự động hàng ngày, kiểm tra restore hàng quý | A.8.13 |
| Kiểm soát truy cập | Tài khoản riêng cho mỗi ứng dụng, least privilege | A.8.3 |
| Audit log | Ghi log truy cập và thay đổi dữ liệu | A.8.15 |
| Data masking | Che dữ liệu nhạy cảm trong môi trường test | A.8.11 |

## 3. Đánh giá Chính sách và Quy trình

### Quản trị ATTT
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| Chính sách ATTT | Được lãnh đạo phê duyệt, truyền đạt toàn bộ | A.5.1 |
| Vai trò ATTT | Có CISO/người phụ trách, ma trận RACI | A.5.2 |
| Đánh giá rủi ro | Thực hiện tối thiểu 1 lần/năm | TCVN 11930 |
| Audit nội bộ | Kiểm toán ATTT hàng năm | A.5.35 |
| Quản lý thay đổi | Quy trình CAB, rollback plan | A.8.32 |

### Quản lý sự cố
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| Incident Response Plan | Có kế hoạch ứng cứu sự cố chi tiết | A.5.24 |
| Đội CSIRT/SOC | Có đội ứng cứu, phân công rõ ràng | A.5.24 |
| Diễn tập sự cố | Ít nhất 1 lần/năm | A.5.24 |
| Thông báo sự cố | Trong 72 giờ cho cơ quan chức năng | NĐ 13/2023 |
| Post-incident review | Rút kinh nghiệm sau mỗi sự cố | A.5.27 |

### Quản lý nhân sự
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| Background check | Kiểm tra lý lịch trước tuyển dụng | A.6.1 |
| NDA | Ký cam kết bảo mật | A.6.6 |
| Đào tạo ATTT | Hàng năm cho toàn bộ nhân viên | A.6.3 |
| Offboarding | Thu hồi tài khoản trong 24h khi nghỉ việc | A.6.5 |
| Phishing test | Mô phỏng tấn công phishing định kỳ | A.6.3 |

## 4. Đánh giá Bảo vệ Dữ liệu Cá nhân (NĐ 13/2023)

### Tuân thủ pháp luật BVDLCN
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| Thông báo xử lý | Thông báo cho chủ thể trước khi xử lý DLCN | NĐ 13 Đ.14 |
| Đồng ý xử lý | Có biểu mẫu đồng ý rõ ràng, cụ thể | NĐ 13 Đ.11 |
| DPIA | Đánh giá tác động với dữ liệu nhạy cảm | NĐ 13 Đ.24 |
| Người phụ trách | Có bộ phận/cá nhân phụ trách BVDLCN | NĐ 13 Đ.28 |
| Lưu trữ dữ liệu | Tại Việt Nam (nếu áp dụng) | Luật ANM Đ.26 |
| Quyền chủ thể | Cơ chế cho chủ thể truy cập/xóa/chỉnh sửa dữ liệu | NĐ 13 Đ.9 |

## 5. Đánh giá Kinh doanh Liên tục

### BCP và DR
| Hạng mục | Tiêu chí đánh giá | Tham chiếu |
|---|---|---|
| BCP | Có kế hoạch kinh doanh liên tục | A.5.29, A.5.30 |
| DR Plan | Có kế hoạch khôi phục sau thảm họa | A.5.30 |
| RTO/RPO | Được xác định cho từng hệ thống | A.5.30 |
| DR site | Có site dự phòng (tối thiểu cloud backup) | A.5.30 |
| Diễn tập DR | Ít nhất 1 lần/năm, ghi nhận kết quả | A.5.30 |
| Backup test | Kiểm tra khôi phục backup hàng quý | A.8.13 |

## 6. Bảng tổng hợp Điểm đánh giá

### Công thức tính điểm theo nhóm
```
Điểm nhóm (%) = (Số mục đạt / Tổng số mục áp dụng) × 100
```

### Điểm tổng thể
```
Điểm tổng = (Hạ tầng × 25%) + (Phần mềm × 25%) + (Chính sách × 20%) + (BVDLCN × 15%) + (BCP/DR × 15%)
```

### Mức đánh giá
| Điểm | Mức | Nhận xét |
|---|---|---|
| 90-100% | Xuất sắc | Sẵn sàng chứng nhận ISO 27001 |
| 75-89% | Tốt | Cần hoàn thiện một số điểm nhỏ |
| 60-74% | Trung bình | Cần kế hoạch cải thiện 3-6 tháng |
| 40-59% | Yếu | Cần đầu tư đáng kể, tư vấn chuyên gia |
| Dưới 40% | Rất yếu | Cần xây dựng lại từ đầu |
