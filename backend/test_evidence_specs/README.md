# CyberAI Assessment Platform — Đặc Tả Bộ Minh Chứng Kiểm Thử Doanh Nghiệp (Test Packs Spec v1)

> **DỮ LIỆU KIỂM THỬ MÔ PHỎNG — không dùng cho mục đích kiểm toán/chứng nhận**
> *SIMULATED TEST DATA — FOR TESTING AND AUDIT VALIDATION PURPOSES ONLY*

Tài liệu này xác lập quy cách thiết kế, cấu trúc ma trận, ánh xạ kiểm soát và bộ tiêu chuẩn nghiệm thu cho 02 bộ dữ liệu minh chứng kỹ thuật phục vụ nghiệm thu Chương 4 của nền tảng **CyberAI Assessment Platform**:
1. `ISO27001_Enterprise_TestPack_v1` (Đánh giá theo ISO/IEC 27001:2022)
2. `TCVN11930_Enterprise_TestPack_v1` (Đánh giá theo TCVN 11930:2017 - Cấp độ 3)

---

## 1. Thông Tin Doanh Nghiệp Giả Lập Thống Nhất

Nhằm đảm bảo tính thực tế, tính nhất quán ngữ cảnh kỹ thuật (contextual cohesion) và không gây mâu thuẫn vô ý giữa các văn bản, toàn bộ tệp minh chứng được xây dựng dựa trên một tổ chức giả định:

- **Tên tổ chức**: Công ty TNHH MTV Hạ tầng Năng lượng An Phú (An Phu Energy Infrastructure Co., Ltd.)
- **Tên viết tắt**: AN PHU ENERGY INFRA
- **Mã định danh hệ thống thông tin**: `AP-ENERGY-PORTAL-LV3` (Cổng Thông tin Quản lý Năng lượng & Điều độ Tải)
- **Quy mô**: Doanh nghiệp năng lượng hạng trung (250 cán bộ nhân viên, 12 nhân sự IT & An toàn thông tin).
- **Môi trường & Hạ tầng máy chủ**:
  - `AP-DC01`: Trung tâm dữ liệu chính (Phòng máy chủ DC Tier 3, Tòa nhà An Phú, Quận 7, TP. Hồ Chí Minh).
  - `AP-DC-AD01` (IP nội bộ: `10.140.1.10`): Máy chủ Domain Controller (Windows Server 2022 Datacenter).
  - `AP-SRV-APP01` (IP nội bộ: `10.140.1.15`): Máy chủ ứng dụng Cổng Điều độ Năng lượng (Ubuntu 22.04 LTS).
  - `AP-DB01` (IP nội bộ: `10.140.1.20`): Máy chủ cơ sở dữ liệu giao dịch SCADA/Billing (PostgreSQL 15 / Red Hat Enterprise Linux 8.8).
  - `AP-FW01` (IP mạng biên: `10.140.0.1`): Cặp tường lửa biên HA FortiGate / Cisco ASA.
  - `AP-WAF01` (IP DMZ: `10.140.2.5`): Tường lửa ứng dụng web.
  - `AP-VPN01` (IP Gateway: `10.140.0.5`): Cổng xác thực VPN SSL/IPsec có MFA.

---

## 2. Giới Hạn Sử Dụng Dữ Liệu & Ràng Buộc An Toàn (Safety Invariants)

1. **Tính chất dữ liệu**: Toàn bộ tài liệu, chính sách, biên bản, nhật ký (log), sơ đồ và ảnh chụp trong các gói test pack là **dữ liệu mô phỏng kỹ thuật (synthetic test data)**. Tuyệt đối không giả mạo chứng chỉ, không sao chép nguyên trạng hồ sơ mật của bất kỳ tổ chức có thật nào.
2. **Quy tắc Header/Footer bắt buộc**: Mọi tệp tài liệu văn bản (`.docx`, `.pdf`), bảng tính (`.xlsx`, `.csv`), và hình ảnh OCR (`.png`) đều chứa dòng ghi chú:
   `DỮ LIỆU KIỂM THỬ MÔ PHỎNG — không dùng cho mục đích kiểm toán/chứng nhận`
3. **Ẩn danh hóa tuyệt đối**: Không chứa thông tin định danh cá nhân thật (PII), chữ ký scan thật, con dấu pháp lý thật, địa chỉ IP public thực tế đang hoạt động, tài khoản ngân hàng hoặc khóa bí mật (private key) thật. Mọi địa chỉ IP đều nằm trong dải IP nội bộ RFC 1918 (`10.140.x.x`, `192.168.x.x`).
4. **Tính nhất quán thời gian và nhân sự**:
   - Mốc thời gian đánh giá: Năm 2026 (Quý 3/2026).
   - Người phê duyệt chính sách: Ông Trần Nam Anh (Chủ tịch kiêm Tổng Giám đốc).
   - Trưởng bộ phận ATTT / CISO: Ông Lê Hoàng Long.
   - Trưởng nhóm Kỹ thuật Hệ thống: Bà Vũ Hải Yến.
   - Mọi số hiệu văn bản (ví dụ: `QĐ-01/2026/QĐ-AP`, `QTr-ATTT-03/AP`) đều tuân theo chuẩn lưu trữ văn thư duy nhất.

---

## 3. Phân Tách Tuyệt Đối Giữa ISO 27001 và TCVN 11930

Nền tảng CyberAI Assessment Platform áp dụng cơ chế cô lập dữ liệu nghiêm ngặt giữa các tiêu chuẩn:

| Tiêu chí | `ISO27001_Enterprise_TestPack_v1` | `TCVN11930_Enterprise_TestPack_v1` |
|---|---|---|
| **Mã tiêu chuẩn (`assessment_standard`)** | `iso27001` | `tcvn11930` |
| **Hệ thống Control Catalog** | 93 Controls (4 nhóm: A.5, A.6, A.7, A.8) | 34 Controls (5 nhóm: Mạng, Máy chủ, Ứng dụng, Dữ liệu, Vận hành) |
| **Tổng điểm trọng số tối đa ($W_{max}$)** | **495.0 điểm** | **271.0 điểm** |
| **Điểm trọng số đạt dự kiến ($W_{achieved}$)** | **312.0 điểm** | **175.0 điểm** |
| **Tỷ lệ Weighted Compliance dự kiến** | **63.0%** (nằm trong dải 60% – 70%) | **64.6%** (nằm trong dải 60% – 70%) |
| **Evidence Manifest Scoping** | `manifest_iso27001_pack_v1` | `manifest_tcvn11930_pack_v1` |
| **Quy tắc kiểm soát chéo** | Backend từ chối tiếp nhận evidence manifest khác `assessment_id` (HTTP 409 Conflict). Tệp TCVN trong assessment ISO sẽ bị đánh dấu `ingestion_status: excluded`. | Tương tự, assessment TCVN sở hữu manifest độc lập, không tái sử dụng hash hoặc file của ISO. |

---

## 4. Công Thức Tính Điểm Chuẩn Hiện Hành (`verdict_weighted_v2`)

Hệ thống tính điểm tuân thủ có trọng số dựa trên thuật toán `verdict_weighted_v2` trong mã nguồn [controls_catalog.py](file:///d:/VSC/CyberAI-Assessment-project/backend/services/controls_catalog.py#L188-L238):

$$\text{Weighted Compliance} = \frac{\sum (w_i \times f_i)}{\sum w_i} \times 100\%$$

Trong đó:
- **Trọng số ($w_i$)** được định nghĩa cố định theo catalog:
  - `Critical`: $10.0$ điểm
  - `High`: $5.0$ điểm
  - `Medium`: $3.0$ điểm
  - `Low`: $1.0$ điểm
- **Hệ số phán quyết ($f_i$)** dựa trên kết quả thẩm định minh chứng:
  - `satisfied` (Đạt đầy đủ minh chứng hợp lệ & có trích dẫn): $f = 1.0$ ($100\%$ điểm)
  - `partial` (Đạt một phần, còn tồn tại thiếu sót nhỏ): $f = 0.5$ ($50\%$ điểm)
  - `needs_expert_review` (Mâu thuẫn hoặc cần chuyên gia rà soát): $f = 0.0$ ($0\%$ điểm)
  - `not_evidenced` (Có tự khai nhưng không có minh chứng trong manifest): $f = 0.0$ ($0\%$ điểm)
  - `missing` (Chưa triển khai, không có minh chứng): $f = 0.0$ ($0\%$ điểm)
  - **Lưu ý**: Phán quyết `not_applicable` bị loại bỏ hoàn toàn khỏi hệ thống đánh giá theo thiết kế kiến trúc chuẩn.

---

## 5. Quy Trình Vận Hành & Khởi Chạy (End-to-End Run)

### Bước 1: Khởi tạo Assessment ID
Gửi yêu cầu khởi tạo phiên đánh giá độc lập:
```bash
# Khởi tạo phiên đánh giá ISO 27001
curl -s -X POST "http://localhost:8000/api/iso27001/assessments/init" \
  -H "Content-Type: application/json" \
  -d '{"standard": "iso27001", "org_name": "Công ty TNHH MTV Hạ tầng Năng lượng An Phú"}'

# Response mẫu: {"assessment_id": "iso-ap-2026-001", "standard": "iso27001"}
```

### Bước 2: Nạp tệp bằng chứng (Batch Ingest)
Nạp toàn bộ gói minh chứng vào phân vùng lưu trữ của `assessment_id`:
```bash
curl -s -X POST "http://localhost:8000/api/iso27001/evidence/batch-ingest?assessment_id=iso-ap-2026-001" \
  -F "files=@./test_evidence_specs/iso_files/A.5.1_Chinh_Sach_An_Toan_Thong_Tin_v2.1.docx" \
  -F "files=@./test_evidence_specs/iso_files/A.8.8_Nhat_Ky_Quet_Va_Danh_Gia_Lo_Hong_Q3.log" \
  ...
```

### Bước 3: Kích hoạt Thẩm định Đa tác tử (Start Assessment)
Gửi payload đánh giá chứa thông tin hệ thống, tự khai báo và mapping:
```bash
curl -s -X POST "http://localhost:8000/api/iso27001/assess" \
  -H "Content-Type: application/json" \
  -d @./test_evidence_specs/assessment_payload_iso.example.json
```

### Bước 4: Giám sát tiến độ qua Server-Sent Events (SSE)
```bash
curl -N "http://localhost:8000/api/iso27001/assessments/iso-ap-2026-001/stream"
```

### Bước 5: Trích xuất hồ sơ nghiệm thu Chương 4
```bash
# Lấy kết quả thẩm định chuẩn hóa (Unified Assessment JSON)
curl -s "http://localhost:8000/api/iso27001/assessments/iso-ap-2026-001" -o audit_result_iso.json

# Lấy Evidence Manifest minh bạch có mã băm SHA-256
curl -s "http://localhost:8000/api/iso27001/assessments/iso-ap-2026-001/manifest" -o evidence_manifest_iso.json

# Lấy vết kiểm toán bất biến (Audit Trace Timeline)
curl -s "http://localhost:8000/api/iso27001/assessments/iso-ap-2026-001/audit-trace" -o audit_trace_iso.json
```
