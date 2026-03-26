# Hướng dẫn Mô tả Hạ tầng Mạng — Chuẩn Format cho RAG và AI Assessment

## Mục đích

Tài liệu này hướng dẫn cách mô tả hạ tầng mạng và hệ thống CNTT theo format chuẩn để AI Auditor (SecurityLM) có thể phân tích chính xác và đưa ra đánh giá đầy đủ.

## ⚠️ Quy tắc Mô tả Hạ tầng

### Nguyên tắc cơ bản
1. **Cụ thể** — Ghi tên sản phẩm, phiên bản, cấu hình thực tế (không mơ hồ).
2. **Đầy đủ** — Mô tả tất cả thành phần quan trọng (firewall, SIEM, backup, AV/EDR).
3. **Có cấu trúc** — Sử dụng các nhóm: Network / Server / Security / Access.
4. **Bilingual** — Dùng thuật ngữ tiếng Anh + giải thích tiếng Việt khi cần.

## Format Chuẩn Mô tả Network Topology

### Template Mô tả Kiến trúc Mạng

```
NETWORK ARCHITECTURE:
- Internet Connection (Kết nối Internet): [số ISP], [loại kết nối], [băng thông]
- Firewall (Tường lửa): [Model], [vị trí], [HA hay không]
- DMZ Zone (Vùng mạng biên): [có/không], [dịch vụ trong DMZ]
- VLAN Segmentation: [số VLAN], [mục đích từng VLAN]
- Core Switch (Switch lõi): [Model]
- Wi-Fi: [SSID phân tách SSID nội bộ và khách không]

SERVER INFRASTRUCTURE:
- Physical Servers (Máy chủ vật lý): [số lượng], [model]
- Virtualization Platform (Nền tảng ảo hóa): [VMware/Hyper-V/KVM/None]
- Virtual Machines (Máy chủ ảo): [số lượng ước tính]
- OS Distribution: [Windows Server X%], [Linux X%]
- Key Services: [AD, DNS, DHCP, Web, DB, Mail...]

SECURITY STACK (Giải pháp bảo mật):
- Firewall/WAF: [tên sản phẩm và phạm vi]
- EDR/Antivirus: [tên sản phẩm, số endpoint bảo phủ]
- SIEM/Log: [tên sản phẩm, lưu trữ bao lâu]
- IDS/IPS: [có/không, tích hợp firewall hay riêng]
- DLP: [có/không, giải pháp]
- PAM (Quản lý truy cập đặc quyền): [có/không]
- NAC (Kiểm soát truy cập mạng): [có/không]

REMOTE ACCESS (Truy cập từ xa):
- VPN: [loại IPSec/SSL, sản phẩm, số user remote]
- MFA: [có/không, phương thức]
- Zero Trust/ZTNA: [có/không]

BACKUP (Sao lưu):
- Solution: [tên giải pháp]
- Frequency: [tần suất backup]
- Retention: [thời gian lưu giữ]
- Offsite/Cloud: [có/không]
- Last DR Test: [lần cuối kiểm tra phục hồi]

CLOUD (Đám mây):
- Provider: [AWS/Azure/GCP/Private/None]
- Services: [liệt kê dịch vụ]
- Data stored in cloud: [loại dữ liệu]
```

## Ví dụ Mô tả Tốt vs Không Tốt

### ❌ Không đủ thông tin (AI không phân tích được)
```
Hệ thống có firewall và antivirus. Backup hàng ngày.
Có dùng cloud một chút. VPN cho nhân viên.
```

### ✅ Mô tả đầy đủ (AI phân tích chính xác)
```
NETWORK: 3 ISP (VNPT 1Gbps primary, Viettel 500Mbps failover, FPT 200Mbps
backup). Firewall FortiGate 200F HA pair tại biên, FortiGate 100F cho
internal segmentation. DMZ Zone (VLAN 50) chứa Web Server Nginx, Mail
Gateway Postfix, DNS Public. 8 VLAN: Server(10), User(20-29 theo phòng),
Guest(99), VoIP(50), Printer(60), Management(1), DMZ(50). Core switch
Cisco Nexus 9300, Access switch Cisco Catalyst 9200. Wi-Fi phân tách SSID
Corp và Guest với captive portal.

SERVER: 25 physical servers (Dell PowerEdge R750, HPE DL380 Gen10).
VMware vSphere 8.0 với 180 VMs. OS: Windows Server 2019 (60%), RHEL 8 (40%).
Key services: AD DS (3 DCs), Exchange 2019, SQL Server 2019 (cluster),
Oracle DB 19c, Web (IIS + Apache), SFTP.

SECURITY: Fortinet FortiEDR trên 500 endpoints + 25 servers. Wazuh SIEM
4.x (3-node cluster), log retention 12 tháng. FortiGate IPS inline mode.
Symantec DLP email gateway. CyberArk PAM cho 15 admin accounts. Cisco
ISE NAC cho tất cả thiết bị kết nối mạng.

REMOTE: FortiClient SSL VPN cho 200 nhân viên WFH. MFA với FortiToken
(hardware token) bắt buộc cho tất cả remote access. Không có ZTNA.

BACKUP: Veeam Backup & Replication v12. Full backup hàng tuần, incremental
hàng ngày. Retention 30 ngày hot (NAS Synology 48TB), 1 năm offsite
(AWS S3 Glacier). DR test hàng quý, lần cuối 15/02/2026: RTO 4h, RPO 2h.

CLOUD: AWS cho Web Application (EKS), Azure cho Office 365 và AD sync.
Dữ liệu khách hàng không lưu trên cloud public.
```

## Thuật ngữ Kỹ thuật Cần Biết

### Network Terms (Thuật ngữ Mạng)
| Thuật ngữ | Viết tắt | Tiếng Việt |
|---|---|---|
| Virtual LAN | VLAN | Mạng LAN ảo — phân tách logic |
| Demilitarized Zone | DMZ | Vùng mạng biên — chứa dịch vụ public |
| Network Access Control | NAC | Kiểm soát truy cập mạng |
| Border Gateway Protocol | BGP | Giao thức định tuyến liên ISP |
| Software-Defined WAN | SD-WAN | Mạng WAN định nghĩa bởi phần mềm |

### Security Terms (Thuật ngữ Bảo mật)
| Thuật ngữ | Viết tắt | Tiếng Việt |
|---|---|---|
| Endpoint Detection Response | EDR | Phát hiện và phản ứng trên endpoint |
| Security Information Event Management | SIEM | Quản lý sự kiện và thông tin bảo mật |
| Intrusion Detection/Prevention System | IDS/IPS | Hệ thống phát hiện/ngăn chặn xâm nhập |
| Data Loss Prevention | DLP | Ngăn chặn rò rỉ dữ liệu |
| Privileged Access Management | PAM | Quản lý truy cập đặc quyền |
| Web Application Firewall | WAF | Tường lửa ứng dụng web |
| Security Operations Center | SOC | Trung tâm vận hành bảo mật |
| Zero Trust Network Access | ZTNA | Truy cập mạng không tin tưởng mặc định |

### Backup Terms (Thuật ngữ Sao lưu)
| Thuật ngữ | Tiếng Việt |
|---|---|
| Recovery Time Objective (RTO) | Thời gian phục hồi tối đa cho phép |
| Recovery Point Objective (RPO) | Lượng dữ liệu tối đa có thể mất |
| Hot backup | Backup đang trực tuyến, phục hồi nhanh |
| Cold backup / Offsite | Backup offline hoặc tại nơi khác |
| 3-2-1 Rule | 3 bản sao, 2 loại media, 1 offsite |

## Checklist Thông tin Bắt buộc cho AI Assessment

### ✅ Thông tin TỐI THIỂU cần cung cấp:
- [ ] Số lượng nhân viên và IT/bảo mật staff
- [ ] Loại và model Firewall (biên)
- [ ] Có DMZ không và chứa gì
- [ ] Antivirus/EDR tên gì, phủ bao nhiêu %
- [ ] Có SIEM/Log tập trung không
- [ ] Backup: giải pháp và có offsite không
- [ ] VPN cho remote: loại gì, có MFA không
- [ ] Số sự cố bảo mật trong 12 tháng qua

### ✅ Thông tin NÂNG CAO giúp AI phân tích sâu hơn:
- [ ] Kiến trúc chi tiết (số VLAN, DMZ services)
- [ ] Phiên bản phần mềm và hệ điều hành
- [ ] Kết quả pentest gần nhất
- [ ] Quy trình incident response hiện tại
- [ ] Compliance yêu cầu đặc thù ngành
- [ ] Kế hoạch DR (RTO/RPO targets)
