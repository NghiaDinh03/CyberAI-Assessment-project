# Hướng dẫn thiết kế và đánh giá hạ tầng mạng theo ISO 27001

## Kiến trúc mạng chuẩn (Reference Architecture)

### Sơ đồ phân zone mạng
```
Internet
    │
    ├── ISP Primary (Fiber)
    ├── ISP Secondary (Backup)
    │
┌───┴───┐
│ Firewall │ (Next-Gen Firewall - FortiGate/Palo Alto)
│  (HA)   │
└───┬───┘
    │
    ├── DMZ Zone
    │   ├── Web Server (reverse proxy)
    │   ├── Mail Gateway
    │   ├── DNS Public
    │   └── VPN Gateway
    │
    ├── Server Zone (VLAN 10)
    │   ├── Application Server
    │   ├── Database Server
    │   ├── File Server
    │   ├── AD/LDAP Server
    │   └── Backup Server
    │
    ├── User Zone (VLAN 20)
    │   ├── Workstations
    │   ├── VoIP Phones
    │   └── Printers
    │
    ├── Management Zone (VLAN 30)
    │   ├── SIEM/Log Server
    │   ├── Monitoring (Zabbix/Nagios)
    │   ├── Patch Management
    │   └── Network Management
    │
    ├── Guest Zone (VLAN 99)
    │   └── Guest WiFi (isolated)
    │
    └── IoT Zone (VLAN 50)
        ├── CCTV Cameras
        ├── Access Control System
        └── Environmental Sensors
```

## Danh mục thiết bị theo vị trí đặt

### Core (Phòng Server / Data Center)
| Thiết bị | Vị trí đặt | Yêu cầu môi trường |
|---|---|---|
| Firewall | Rack chính, U1-U2 | Nhiệt độ 18-27°C, UPS |
| Core Switch | Rack chính, U3-U5 | Nguồn dự phòng |
| Server Rack | Server room | Sàn nâng, chống tĩnh điện |
| UPS | Phòng điện kỹ thuật | Thông gió |
| NAS/Backup | Rack phụ | Nhiệt độ ổn định |

### Distribution (Tầng/Khu vực)
| Thiết bị | Vị trí đặt | Yêu cầu |
|---|---|---|
| Distribution Switch | Tủ mạng tầng | Khóa tủ, thông gió |
| Access Point | Trần nhà, cách 15-20m | PoE, coverage planning |
| IP Camera | Góc hành lang, cửa ra vào | PoE, outdoor nếu ngoài trời |

### Access (Người dùng cuối)
| Thiết bị | Vị trí đặt | Yêu cầu |
|---|---|---|
| Access Switch | Tủ mạng tầng | 24/48 port PoE+ |
| Patch Panel | Tủ mạng | Cat6a, label rõ ràng |
| Wall Jack | Mỗi bàn làm việc | 2 port (data + voice) |

## Checklist đánh giá hạ tầng mạng

### 1. An ninh mạng biên (Perimeter Security)
- [ ] Firewall next-gen với IPS/IDS
- [ ] Dual ISP với failover
- [ ] VPN site-to-site (nếu có chi nhánh)
- [ ] VPN remote access cho nhân viên
- [ ] Web Application Firewall (WAF) cho web public
- [ ] DDoS protection

### 2. Phân tách mạng (Network Segmentation)
- [ ] VLAN riêng cho Server, User, Management, Guest
- [ ] DMZ cho dịch vụ public
- [ ] ACL giữa các VLAN
- [ ] IoT trên VLAN riêng biệt
- [ ] Guest WiFi cách ly hoàn toàn

### 3. Kiểm soát truy cập mạng (Network Access Control)
- [ ] 802.1X authentication
- [ ] MAC address filtering (phụ trợ)
- [ ] NAC solution (ISE, PacketFence)
- [ ] Port security trên switch
- [ ] Disable unused ports

### 4. Giám sát và logging
- [ ] NetFlow/sFlow collection
- [ ] SNMP monitoring (v3)
- [ ] Syslog centralized
- [ ] SIEM integration
- [ ] Bandwidth monitoring

### 5. Mã hóa và xác thực
- [ ] TLS 1.2+ cho tất cả dịch vụ web
- [ ] SSH thay Telnet
- [ ] RADIUS/TACACS+ cho quản trị thiết bị mạng
- [ ] Certificate management
- [ ] IPSec cho site-to-site VPN

### 6. Sao lưu và dự phòng
- [ ] Config backup tự động cho thiết bị mạng
- [ ] HA cho firewall và core switch
- [ ] Spanning Tree Protocol (RSTP/MSTP)
- [ ] Link aggregation cho uplinks
- [ ] Documented recovery procedures

### 7. Quản lý thiết bị
- [ ] Firmware cập nhật
- [ ] Default password đã đổi
- [ ] Hardening theo CIS Benchmark
- [ ] Change management cho cấu hình
- [ ] Inventory cập nhật

## Bảng tham chiếu: Thiết bị ↔ Điều khoản Annex A

| Điều khoản | Thiết bị/Giải pháp liên quan |
|---|---|
| A.7.1 Vành đai vật lý | Access control system, camera CCTV |
| A.7.2 Kiểm soát vào ra | Card reader, biometric scanner |
| A.7.4 Giám sát vật lý | IP camera, NVR, motion sensor |
| A.7.5 Mối đe dọa môi trường | UPS, generator, fire suppression, HVAC |
| A.8.1 Thiết bị đầu cuối | EDR, MDM, disk encryption |
| A.8.7 Chống mã độc | Antivirus, email gateway, sandbox |
| A.8.8 Quản lý lỗ hổng | Vulnerability scanner (Nessus/OpenVAS) |
| A.8.12 Chống rò rỉ dữ liệu | DLP solution |
| A.8.13 Sao lưu | NAS, tape library, cloud backup |
| A.8.14 Dự phòng | HA cluster, load balancer |
| A.8.15 Ghi log | SIEM (Wazuh/Splunk/ELK) |
| A.8.16 Giám sát | IDS/IPS, SIEM, monitoring tool |
| A.8.20 An ninh mạng | Firewall, WAF, network segmentation |
| A.8.21 Dịch vụ mạng | ISP redundancy, SD-WAN |
| A.8.22 Phân tách mạng | VLAN, micro-segmentation |
| A.8.23 Lọc web | Web proxy, DNS filtering |
| A.8.24 Mã hóa | HSM, certificate management, TLS |
