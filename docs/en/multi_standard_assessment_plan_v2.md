# Kế hoạch Nâng cấp Nền tảng Đánh giá ATTT Đa Tiêu Chuẩn (Phiên bản 2.0)

Căn cứ theo các góp ý chuyên sâu, Kế hoạch triển khai Form đánh giá (Assessment Platform) sẽ được quy hoạch lại một cách chặt chẽ, tối ưu luồng AI và đảm bảo tính chính xác của các bộ quản lý tiêu chuẩn (Compliance Frameworks).

## 1. Cơ chế Quản lý Đa Tiêu chuẩn (Multi-Standard Assessment)
Giai đoạn này hệ thống **chỉ tập trung triển khai 2 tiêu chuẩn chính tả thực**:
- **ISO 27001:2022:** Chấm điểm dựa trên tỷ lệ đáp ứng 93 Controls (Biện pháp kiểm soát).
- **TCVN 11930:2017:** Yêu cầu cơ bản về bảo đảm an toàn hệ thống thông tin theo cấp độ. (Chấm điểm theo yêu cầu đáp ứng của 5 Cấp độ, KHÔNG chấm theo % controls như ISO).

👉 **Nhiệm vụ Deep Research:** 
- Tạm dừng việc lấy JSON tĩnh đơn giản. Hệ thống sẽ cần Deep Research lại tài liệu `TCVN 11930:2017` để mapping chính xác điều kiện của 5 Cấp độ (Level 1 -> 5) vào Database, phục vụ cho cơ chế chấm điểm đúng luật Việt Nam. (Đã hoàn thành và lưu vào `data/iso_documents/tcvn_11930_2017.md`)
- Bộ Data mẫu của TCVN 11930 và ISO 27001 sẽ được tách biệt rõ ràng.

## 2. Quản lý Mẫu Báo Cáo (Templates Library)
- **Không dùng chế độ "Điền nhanh ảo":** Tính năng `Auto-fill` sẽ bị loại bỏ.
- **Tính năng Template Monitor:** Sẽ có một khu vực (hoặc Page Monitor riêng) ở bên ngoài cho phép người dùng lướt xem các Mẫu (Profiles) hệ thống thực tế (VD: Ngân hàng, Bệnh viện, Core SaaS). Đảm bảo Data mẫu là chuẩn và chính xác, phù hợp với kiến trúc ngoài thực tế.
- Khi người dùng ấn **"Sử dụng mẫu này"**, hệ thống sẽ nạp (load) Data Profile đó vào đúng Form của Tiêu chuẩn tương ứng. Mỗi tiêu chuẩn sẽ có Format Data khác biệt hoàn toàn.

## 3. Kiến trúc Đánh giá thông minh (Multi-LLM Pipeline)
Thay vì bắt một Model làm tất cả dẫn đến chất lượng giảm sút, luồng xử lý Report (Báo cáo đánh giá) sẽ được chia làm 2 pha:

- **Pha 1 (Phân tích chuyên sâu - Security LLM):** Model chuyên về Security (VD: `SecurityLLM 7B` hoặc model RAG bảo mật) sẽ nhận dữ liệu Form và tài liệu RAG. Nhiệm vụ của nó là "bắt bệnh", chấm điểm, tìm ra các lỗ hổng (GAP Analysis) so với đúng tiêu chuẩn được chọn.
- **Pha 2 (Định dạng & Thiết kế Báo cáo - Llama 3.1):** Model AI Llama (General Model) sẽ cầm kết quả thô của Pha 1 để xào nấu lại theo một Format giao diện (Markdown) vô cùng đẹp mắt, chuẩn mực và dễ hiểu cho người dùng cuối. 
- *Mở rộng:* Ưu tiên chất lượng Đánh giá Hệ thống (Assessment). Phần đề xuất nâng cao có thể kết nối với 1 API bên thứ 3 để Gen thêm (nếu cần).

## 4. UI/UX: Quản lý Luồng Async (Thread ID & History)
- Khắc phục tình trạng treo Tab bắt người dùng chờ đợi Model AI xử lý.
- Khi nhấn nút "Bắt đầu Đánh giá", hệ thống Backend sẽ sinh ra **Thread ID (Job ID)**, thực thi ngầm ở Background Task. 
- Frontend hiển thị 1 Tab `Kết quả Đánh giá (History)`. Người dùng hoàn toàn có thể sang Tab khác đọc tin tức, sau đó quay lại trang History để xem báo cáo khi nó hoàn thành dựa trên ID kết quả.
