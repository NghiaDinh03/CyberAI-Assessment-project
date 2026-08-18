# Tiêu chí chấm điểm đánh giá tuân thủ ISO 27001:2022

## Thang điểm đánh giá

### Mức tuân thủ (Compliance Level)

| Mức | Điểm | Mô tả |
|---|---|---|
| **Tuân thủ đầy đủ** | 3 | Biện pháp kiểm soát được triển khai hoàn chỉnh, có tài liệu đầy đủ, được giám sát và cải tiến liên tục |
| **Tuân thủ một phần** | 2 | Biện pháp đã triển khai nhưng còn thiếu sót hoặc chưa đầy đủ tài liệu |
| **Không tuân thủ** | 1 | Biện pháp chưa được triển khai hoặc triển khai không hiệu quả |
| **Không áp dụng** | 0 | Biện pháp không áp dụng cho tổ chức (cần có lý do hợp lệ) |

## Công thức tính điểm

### Điểm tổng thể
```
Điểm tuân thủ (%) = (Tổng điểm thực tế / Tổng điểm tối đa áp dụng) × 100
```

### Phân loại kết quả

| Điểm (%) | Xếp hạng | Đánh giá | Hành động |
|---|---|---|---|
| 90-100 | **A - Xuất sắc** | Sẵn sàng chứng nhận | Duy trì và cải tiến |
| 75-89 | **B - Tốt** | Gần đạt chuẩn | Khắc phục điểm yếu còn lại |
| 60-74 | **C - Trung bình** | Cần cải thiện đáng kể | Lập kế hoạch khắc phục 6 tháng |
| 40-59 | **D - Yếu** | Nhiều lỗ hổng | Cần đầu tư và hỗ trợ chuyên gia |
| 0-39 | **F - Rất yếu** | Chưa sẵn sàng | Bắt đầu từ đầu, gap analysis toàn diện |

## Trọng số theo nhóm kiểm soát

| Nhóm | Trọng số | Lý do |
|---|---|---|
| A.5 Kiểm soát tổ chức | 30% | Nền tảng cho toàn bộ ISMS |
| A.6 Kiểm soát con người | 15% | Yếu tố con người quan trọng |
| A.7 Kiểm soát vật lý | 15% | Bảo vệ tài sản vật lý |
| A.8 Kiểm soát công nghệ | 40% | Bảo vệ hệ thống CNTT |

## Tiêu chí đánh giá chi tiết

### Kiểm tra tài liệu (Documentation)
- Chính sách có được phê duyệt bởi lãnh đạo?
- Quy trình có phiên bản và ngày hiệu lực?
- Hướng dẫn có rõ ràng và cập nhật?
- Biểu mẫu/template có sẵn sàng?

### Kiểm tra triển khai (Implementation)
- Biện pháp có được triển khai trên thực tế?
- Nhân viên có nhận thức và tuân thủ?
- Công cụ kỹ thuật có hoạt động đúng?
- Log/bằng chứng có ghi lại đầy đủ?

### Kiểm tra hiệu quả (Effectiveness)
- Sự cố ATTT có giảm so với kỳ trước?
- Thời gian phản ứng sự cố có đạt SLA?
- Kết quả pentest/vulnerability scan?
- Kết quả phishing simulation?

### Kiểm tra cải tiến (Improvement)
- Có hành động khắc phục từ lần audit trước?
- Có bài học kinh nghiệm từ sự cố?
- KPI ATTT được theo dõi và cải thiện?
- Management review được thực hiện định kỳ?

## Mẫu khuyến nghị theo kết quả

### Khi phát hiện Non-Compliant
1. Mô tả phát hiện (Finding)
2. Tham chiếu điều khoản (Reference)
3. Rủi ro liên quan (Risk)
4. Khuyến nghị khắc phục (Recommendation)
5. Mức độ ưu tiên (Priority): Cao/Trung bình/Thấp
6. Thời hạn khắc phục (Timeline)

### Khi đạt Compliant
1. Ghi nhận điểm mạnh
2. Đề xuất cải tiến thêm (nếu có)
3. Lưu ý duy trì
