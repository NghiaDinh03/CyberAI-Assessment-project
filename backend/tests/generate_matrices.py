"""Utility script to generate authoritative JSON matrices for ISO 27001 and TCVN 11930 test packs."""

import json
import os
from services.controls_catalog import (
    ISO_27001_CATEGORIES,
    TCVN_11930_CATEGORIES,
    WEIGHT_SCORE,
    calc_weighted_compliance,
)

# ==============================================================================
# 1. ISO 27001:2022 Expected Matrix Generation
# ==============================================================================
iso_all = []
for cat in ISO_27001_CATEGORIES:
    cat_name = cat["category"]
    for c in cat["controls"]:
        iso_all.append({"id": c["id"], "label": c["label"], "weight": c["weight"], "category": cat_name})

satisfied_iso = {
    "A.5.1": ("EV-ISO-01", "QĐ số QĐ-01/2026/QĐ-AP ban hành Chính sách ATTT toàn diện"),
    "A.5.2": ("EV-ISO-02", "QĐ số 05/QĐ-AP phân công CISO và Trưởng nhóm IT"),
    "A.5.3": ("EV-ISO-02", "QĐ số 05/QĐ-AP Điều 4: Cấm tuyệt đối Dev truy cập Production AP-DB01"),
    "A.5.9": ("EV-ISO-03", "Sổ kiểm kê 45 tài sản phần cứng và CSDL tại AP-DC01"),
    "A.5.10": ("EV-ISO-03", "Quy định sử dụng tài sản CNTT hợp lệ có chữ ký nhân sự"),
    "A.5.12": ("EV-ISO-03", "Phân loại thông tin 4 cấp độ: Công khai, Nội bộ, Mật, Tối mật"),
    "A.5.15": ("EV-ISO-04", "Biên bản rà soát định kỳ 250 tài khoản Active Directory Q3/2026"),
    "A.5.16": ("EV-ISO-04", "Thu hồi và vô hiệu hóa 14 tài khoản nhân viên thôi việc"),
    "A.5.17": ("EV-ISO-05", "Bắt buộc xác thực TOTP/MFA trên cổng VPN 10.140.0.5"),
    "A.5.18": ("EV-ISO-04", "Phân quyền thư mục và dịch vụ theo ma trận chức danh"),
    "A.5.24": ("EV-ISO-07", "Quy trình ứng cứu sự cố ATTT QTr-CSIRT-01 phân loại mức độ"),
    "A.5.26": ("EV-ISO-07", "Quy trình xử lý sự cố trong vòng 30 phút cho mức Critical"),
    "A.5.31": ("EV-ISO-09", "Sổ theo dõi tuân thủ Nghị định 13/2023/NĐ-CP và Luật ATTTM"),
    "A.6.1": ("EV-ISO-10", "Quy trình thẩm tra lý lịch nhân sự kỹ thuật trước tuyển dụng"),
    "A.6.2": ("EV-ISO-10", "Cam kết bảo mật thông tin NDA 100% nhân sự ký khi nhận việc"),
    "A.6.3": ("EV-ISO-11", "Danh sách 242/250 nhân viên hoàn thành khóa đào tạo ATTT 2026"),
    "A.6.5": ("EV-ISO-04", "Quy trình bàn giao trách nhiệm và thu hồi tài sản khi nghỉ việc"),
    "A.6.6": ("EV-ISO-10", "Thỏa thuận bảo mật thông tin có hiệu lực 2 năm sau thôi việc"),
    "A.7.1": ("EV-ISO-13", "Vành đai an ninh vật lý tầng 3 phòng máy chủ AP-DC01"),
    "A.7.2": ("EV-ISO-13", "Kiểm soát vào ra hai lớp: Thẻ từ kết hợp sinh trắc học vân tay"),
    "A.7.4": ("EV-ISO-14", "CCTV giám sát 24/7 phòng máy chủ, lưu trữ hình ảnh 90 ngày (OCR)"),
    "A.7.7": ("EV-ISO-15", "Quy định bàn làm việc sạch và màn hình sạch có biên bản kiểm tra"),
    "A.7.8": ("EV-ISO-15", "Thiết bị lắp trong tủ rack có luồng khí nóng lạnh và tiếp địa"),
    "A.7.10": ("EV-ISO-03", "Quản lý phương tiện lưu trữ dự phòng trong két chống cháy"),
    "A.7.11": ("EV-ISO-16", "Hệ thống UPS 80kVA 2N và máy phát điện chuyển ATS trong 12ms"),
    "A.8.1": ("EV-ISO-17", "180/180 máy trạm được bảo vệ bởi EDR Agent và Windows Update"),
    "A.8.2": ("EV-ISO-18", "Quản lý 3 tài khoản Domain Admins qua két sắt số PAM CyberArk/Vault"),
    "A.8.4": ("EV-ISO-02", "Kiểm soát truy cập mã nguồn GitLab qua 2FA và phân quyền nhánh"),
    "A.8.5": ("EV-ISO-05", "Xác thực đa yếu tố MFA cho toàn bộ truy cập SSH/RDP máy chủ DC"),
    "A.8.7": ("EV-ISO-19", "Microsoft Defender for Endpoint bảo vệ thời gian thực cho máy chủ"),
    "A.8.9": ("EV-ISO-21", "Baseline Hardening áp dụng CIS Benchmark Level 2 qua GPO"),
    "A.8.13": ("EV-ISO-22", "Veeam Backup sao lưu CSDL hàng ngày và kiểm thử khôi phục thành công"),
    "A.8.14": ("EV-ISO-16", "Hạ tầng máy chủ ảo hóa VMware vSphere cấu hình HA dự phòng N+1"),
    "A.8.15": ("EV-ISO-23", "rsyslog và WEF chuyển tiếp toàn bộ nhật ký về máy chủ SIEM 10.140.1.30"),
    "A.8.20": ("EV-ISO-25", "Tường lửa FortiGate AP-FW01 chặn toàn bộ kết nối trái phép vào DB"),
    "A.8.22": ("EV-ISO-26", "Phân tách VLAN Quản trị, VLAN Ứng dụng, VLAN DB và DMZ (OCR)"),
    "A.8.24": ("EV-ISO-27", "Nginx kích hoạt TLS 1.3 và cipher ECDHE-ECDSA-AES256-GCM"),
    "A.8.31": ("EV-ISO-02", "Phân tách độc lập môi trường Development, Staging và Production"),
}

partial_iso = {
    "A.5.19": ("EV-ISO-06", "Hợp đồng có điều khoản bảo mật nhưng thiếu kiểm toán bên thứ 3 định kỳ"),
    "A.5.20": ("EV-ISO-06", "Thiếu cam kết bảo mật chi tiết đối với nhà cung cấp dịch vụ hạ tầng phụ"),
    "A.5.29": ("EV-ISO-08", "Kế hoạch BCP có RTO/RPO nhưng chưa tổ chức diễn tập thực tế năm 2026"),
    "A.5.30": ("EV-ISO-08", "Hạ tầng DR sẵn sàng nhưng hoãn đợt chuyển đổi tải thực tế"),
    "A.5.36": ("EV-ISO-01", "Rà soát chính sách nội bộ nhưng chưa đối chiếu toàn diện chuẩn ISO mới"),
    "A.6.7": ("EV-ISO-12", "Chính sách BYOD ban hành nhưng chưa trang bị phần mềm MDM quản lý"),
    "A.6.8": ("EV-ISO-07", "Nhân viên có kênh báo cáo sự cố nhưng thiếu cổng tiếp nhận tự động 24/7"),
    "A.7.3": ("EV-ISO-13", "Phòng ban có khóa cửa nhưng thiếu cảm biến báo động đột nhập ban đêm"),
    "A.7.14": ("EV-ISO-03", "Biên bản hủy ổ cứng định kỳ nhưng thiếu chứng thư tiêu hủy của đơn vị chuyên nghiệp"),
    "A.8.3": ("EV-ISO-04", "Phân quyền thư mục có chia sẻ nhưng thiếu gắn nhãn tự động DLP"),
    "A.8.12": ("EV-ISO-04", "DLP được triển khai trên email nhưng chưa áp dụng cho cổng USB máy trạm"),
    "A.8.16": ("EV-ISO-24", "SOC giám sát an ninh trong giờ hành chính, ngoài giờ dùng alert tự động"),
    "A.8.21": ("EV-ISO-25", "Dịch vụ mạng có quản lý nhưng chưa kiểm toán lưu lượng định kỳ"),
    "A.8.25": ("EV-ISO-02", "Quy trình DevSecOps có rà soát nhưng chưa tích hợp quét SAST tự động vào CI/CD"),
    "A.8.32": ("EV-ISO-28", "Quy trình thay đổi CAB hoạt động nhưng thiếu kế hoạch rollback bắt buộc"),
}

conflict_iso = {
    "A.8.8": ("EV-ISO-20", "Log Nessus cho thấy CVE-2023-38606 CVSS 9.8 chưa vá trên AP-SRV-APP01 mâu thuẫn với tự khai")
}

not_evidenced_iso = {
    "A.5.4": "Trách nhiệm của ban quản lý",
    "A.5.7": "Threat Intelligence",
    "A.5.14": "Truyền tải thông tin",
    "A.5.25": "Đánh giá sự kiện ATTT",
    "A.5.34": "Bảo vệ thông tin cá nhân PII",
    "A.6.4": "Quy trình kỷ luật vi phạm ATTT",
    "A.7.5": "Bảo vệ trước thiên tai",
    "A.7.6": "Làm việc trong khu vực an toàn",
    "A.7.9": "An ninh tài sản ngoài khuôn viên",
    "A.7.12": "An ninh cáp mạng",
    "A.8.6": "Quản lý công suất",
    "A.8.10": "Xóa thông tin an toàn",
    "A.8.11": "Che giấu dữ liệu",
    "A.8.23": "Lọc web",
    "A.8.29": "Kiểm thử bảo mật Pentest",
}

iso_matrix = []
for c in iso_all:
    cid = c["id"]
    w_name = c["weight"].lower()
    w_pts = WEIGHT_SCORE[w_name]

    if cid in satisfied_iso:
        ev_id, anchor = satisfied_iso[cid]
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "implemented",
            "expected_verdict": "satisfied",
            "expected_verdict_factor": 1.0,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "satisfied",
            "verdict": "satisfied",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 1.0,
            "weighted_score_contribution": round(w_pts * 1.0, 1),
            "evidence_ids": [ev_id],
            "expected_citation_anchor": anchor,
            "conflict_detected": False,
            "expected_source": "llm",
            "reason": "Minh chứng kỹ thuật và chính sách đầy đủ, hợp lệ, có trích dẫn xác thực."
        }
    elif cid in partial_iso:
        ev_id, anchor = partial_iso[cid]
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "implemented",
            "expected_verdict": "partial",
            "expected_verdict_factor": 0.5,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "partial",
            "verdict": "partial",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 0.5,
            "weighted_score_contribution": round(w_pts * 0.5, 1),
            "evidence_ids": [ev_id],
            "expected_citation_anchor": anchor,
            "conflict_detected": False,
            "expected_source": "llm",
            "reason": "Biện pháp đã triển khai trên thực tế nhưng còn thiếu sót nhỏ cần khắc phục."
        }
    elif cid in conflict_iso:
        ev_id, anchor = conflict_iso[cid]
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "implemented",
            "expected_verdict": "needs_expert_review",
            "expected_verdict_factor": 0.0,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "needs_expert_review",
            "verdict": "needs_expert_review",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 0.0,
            "weighted_score_contribution": 0.0,
            "evidence_ids": [ev_id],
            "expected_citation_anchor": anchor,
            "conflict_detected": True,
            "expected_source": "safe_fallback_conflict",
            "reason": "Phát hiện mâu thuẫn: Tự khai báo đã triển khai nhưng log quét thực tế tồn tại lỗ hổng nghiêm trọng chưa vá."
        }
    elif cid in not_evidenced_iso:
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "implemented",
            "expected_verdict": "not_evidenced",
            "expected_verdict_factor": 0.0,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "not_evidenced",
            "verdict": "not_evidenced",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 0.0,
            "weighted_score_contribution": 0.0,
            "evidence_ids": [],
            "expected_citation_anchor": None,
            "conflict_detected": False,
            "expected_source": "safe_fallback_no_evidence",
            "reason": "Có tự khai báo triển khai nhưng không đính kèm tệp bằng chứng trong Manifest; hệ thống ép về 0 điểm."
        }
    else:
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "not_implemented",
            "expected_verdict": "missing",
            "expected_verdict_factor": 0.0,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "missing",
            "verdict": "missing",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 0.0,
            "weighted_score_contribution": 0.0,
            "evidence_ids": [],
            "expected_citation_anchor": None,
            "conflict_detected": False,
            "expected_source": "rule_based",
            "reason": "Doanh nghiệp chưa triển khai kiểm soát này và không cung cấp tài liệu minh chứng."
        }
    iso_matrix.append(entry)

iso_comp = calc_weighted_compliance(iso_matrix)
print("=== ISO 27001 Calculation ===")
print(f"Weighted Score: {iso_comp['weighted_score']} / {iso_comp['weighted_max_score']} = {iso_comp['percentage']}%")

with open("/app/expected_iso.json", "w", encoding="utf-8") as f:
    json.dump(iso_matrix, f, ensure_ascii=False, indent=2)


# ==============================================================================
# 2. TCVN 11930:2017 Expected Matrix Generation
# ==============================================================================
tcvn_all = []
for cat in TCVN_11930_CATEGORIES:
    cat_name = cat["category"]
    for c in cat["controls"]:
        tcvn_all.append({"id": c["id"], "label": c["label"], "weight": c["weight"], "category": cat_name})

satisfied_tcvn = {
    "NW.01": ("EV-TCVN-01", "ACL 101 switch lõi deny ip văn phòng vào dải Server DC"),
    "NW.02": ("EV-TCVN-02", "AP-FW01 FortiGate chặn toàn bộ traffic ngoài luồng, mở duy nhất 443 DMZ"),
    "NW.04": ("EV-TCVN-04", "VPN IPsec IKEv2 mã hóa AES-256-GCM cho truy cập từ xa"),
    "NW.05": ("EV-TCVN-05", "Sơ đồ topo DMZ 2 lớp firewall cách ly Web và CSDL (OCR)"),
    "SV.01": ("EV-TCVN-06", "Mật khẩu tối thiểu 12 ký tự, tắt toàn bộ telnet, rsh, ftp"),
    "SV.02": ("EV-TCVN-07", "Trend Micro Deep Security bảo vệ thời gian thực cho 12 máy chủ"),
    "SV.05": ("EV-TCVN-09", "Khóa đăng nhập root trực tiếp SSH, quản lý tài khoản qua PAM"),
    "SV.06": ("EV-TCVN-09", "Bắt buộc xác thực khóa SSH Ed25519 kết hợp OTP Google Authenticator"),
    "SV.08": ("EV-TCVN-10", "Áp dụng CIS Benchmark Level 2 cho Linux đạt 94.2% tiêu chí"),
    "APP.01": ("EV-TCVN-11", "Mật khẩu người dùng băm bằng bcrypt cost factor 12 trong CSDL"),
    "APP.02": ("EV-TCVN-12", "Chứng chỉ HTTPS Qualys SSL Labs đạt điểm A+, hỗ trợ TLS 1.3"),
    "APP.07": ("EV-TCVN-15", "Ứng dụng ghi nhận audit log JSON chi tiết các hành vi xác thực"),
    "DAT.02": ("EV-TCVN-17", "Ma trận phân quyền CSDL theo Need-to-know, cấm quyền DBA cho web app"),
    "DAT.04": ("EV-TCVN-19", "Mã hóa phân vùng CSDL LUKS AES-512 quản lý qua HashiCorp Vault"),
    "MNG.01": ("EV-TCVN-20", "Quyết định số 10/QĐ-AP ban hành Quy chế ATTT Cấp độ 3"),
    "MNG.02": ("EV-TCVN-21", "QĐ số 12/QĐ-AP thành lập Ban ATTT chuyên trách độc lập"),
}

partial_tcvn = {
    "NW.03": ("EV-TCVN-03", "Suricata IPS hoạt động ở chế độ Detect cảnh báo, chưa bật inline drop"),
    "SV.04": ("EV-TCVN-08", "Wazuh FIM giám sát /etc nhưng chưa giám sát thư mục mã nguồn /var/www"),
    "APP.03": ("EV-TCVN-13", "Dùng ORM chống SQLi nhưng frontend thiếu HTTP Header CSP chống XSS"),
    "APP.04": ("EV-TCVN-14", "Timeout 15 phút nhưng thiếu kiểm soát đăng nhập đồng thời từ 2 IP"),
    "DAT.03": ("EV-TCVN-18", "Đã có bản sao lưu NAS + S3 Immutable nhưng thiếu sao lưu offline Tape"),
    "MNG.04": ("EV-TCVN-22", "Kịch bản diễn tập Ransomware đã duyệt nhưng chưa diễn tập thực chiến"),
}

conflict_tcvn = {
    "DAT.01": ("EV-TCVN-16", "Nhật ký pg_dump báo lỗi Disk full / CRC error mâu thuẫn với tự khai báo")
}

not_evidenced_tcvn = {
    "NW.07": "Quản lý truy cập mạng NAC",
    "SV.03": "Hệ thống chống xâm nhập máy chủ EDR/XDR",
    "APP.05": "Ngăn chặn tấn công Web WAF",
    "DAT.05": "Phòng chống thất thoát dữ liệu DLP",
    "MNG.03": "Hệ thống giám sát sự cố tập trung SIEM/SOC",
}

tcvn_matrix = []
for c in tcvn_all:
    cid = c["id"]
    w_name = c["weight"].lower()
    w_pts = WEIGHT_SCORE[w_name]

    if cid in satisfied_tcvn:
        ev_id, anchor = satisfied_tcvn[cid]
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "implemented",
            "expected_verdict": "satisfied",
            "expected_verdict_factor": 1.0,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "satisfied",
            "verdict": "satisfied",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 1.0,
            "weighted_score_contribution": round(w_pts * 1.0, 1),
            "evidence_ids": [ev_id],
            "expected_citation_anchor": anchor,
            "conflict_detected": False,
            "expected_source": "llm",
            "reason": "Minh chứng kỹ thuật và cấu hình đầy đủ, hợp lệ, có trích dẫn xác thực."
        }
    elif cid in partial_tcvn:
        ev_id, anchor = partial_tcvn[cid]
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "implemented",
            "expected_verdict": "partial",
            "expected_verdict_factor": 0.5,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "partial",
            "verdict": "partial",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 0.5,
            "weighted_score_contribution": round(w_pts * 0.5, 1),
            "evidence_ids": [ev_id],
            "expected_citation_anchor": anchor,
            "conflict_detected": False,
            "expected_source": "llm",
            "reason": "Biện pháp kỹ thuật đã triển khai một phần nhưng còn tồn tại thiếu sót nhỏ."
        }
    elif cid in conflict_tcvn:
        ev_id, anchor = conflict_tcvn[cid]
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "implemented",
            "expected_verdict": "needs_expert_review",
            "expected_verdict_factor": 0.0,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "needs_expert_review",
            "verdict": "needs_expert_review",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 0.0,
            "weighted_score_contribution": 0.0,
            "evidence_ids": [ev_id],
            "expected_citation_anchor": anchor,
            "conflict_detected": True,
            "expected_source": "safe_fallback_conflict",
            "reason": "Phát hiện mâu thuẫn: Tự khai báo đã sao lưu nhưng log hệ thống ghi nhận phiên sao lưu bị lỗi CRC."
        }
    elif cid in not_evidenced_tcvn:
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "implemented",
            "expected_verdict": "not_evidenced",
            "expected_verdict_factor": 0.0,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "not_evidenced",
            "verdict": "not_evidenced",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 0.0,
            "weighted_score_contribution": 0.0,
            "evidence_ids": [],
            "expected_citation_anchor": None,
            "conflict_detected": False,
            "expected_source": "safe_fallback_no_evidence",
            "reason": "Có tự khai báo đạt nhưng không cung cấp minh chứng kỹ thuật trong Manifest."
        }
    else:
        entry = {
            "control_id": cid,
            "label": c["label"],
            "category": c["category"],
            "declaration_status": "not_implemented",
            "expected_verdict": "missing",
            "expected_verdict_factor": 0.0,
            "expected_weight": w_name,
            "expected_weight_points": w_pts,
            "assessment_verdict": "missing",
            "verdict": "missing",
            "weight": w_name,
            "weight_points": w_pts,
            "verdict_factor": 0.0,
            "weighted_score_contribution": 0.0,
            "evidence_ids": [],
            "expected_citation_anchor": None,
            "conflict_detected": False,
            "expected_source": "rule_based",
            "reason": "Chưa triển khai và không có hồ sơ minh chứng kỹ thuật."
        }
    tcvn_matrix.append(entry)

tcvn_comp = calc_weighted_compliance(tcvn_matrix)
print("=== TCVN 11930 Calculation ===")
print(f"Weighted Score: {tcvn_comp['weighted_score']} / {tcvn_comp['weighted_max_score']} = {tcvn_comp['percentage']}%")

with open("/app/expected_tcvn.json", "w", encoding="utf-8") as f:
    json.dump(tcvn_matrix, f, ensure_ascii=False, indent=2)

print("Matrices generation completed successfully.")
