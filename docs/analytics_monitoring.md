# Quản trị & Giám sát Hệ thống (Analytics UI)

Nhằm cung cấp cái nhìn trực quan và Real-time (thời gian thực) cho toàn bộ cấu hình lõi của dự án trí tuệ nhân tạo, trang **Analytics** đóng vai trò là Dashboard tổng huy động quản trị.

## 1. Monitor Các Service Hoạt động (Trạng thái Dịch vụ)

Giao diện sẽ liên tục (Mỗi 5 giây) Pinging tới Backend thông qua Endpoint: `GET /api/system/stats`. Trả về trạng thái màu Xanh/Đỏ/Vàng cảnh báo cho các Core API:
- **FastAPI Backend:** Server xử lý giao tiếp chính. (Port 8000)
- **LocalAI Engine:** AI Server chạy bằng C++ cho GGUF. (Port 8080)
- **ChromaDB**: Kho lưu trữ Vector Embeddings cục bộ.
- **Llama 3.1 8B**: Load vào RAM, phục vụ RAG và Chat. (Dành cho General/Summary).
- **SecurityLLM 7B**: Mô hình soi lỗi bảo mật hệ thống. (ISO Assessor).
- **VinAI Translate Model**: Giao thức NLP siêu nhẹ (135M parameters) phục vụ Dịch tin.

## 2. Thống kê Sinh Cache (Audio & Translation)
Do tính năng **Feed Tin Tức** tự động Cào bài báo -> Dịch tiếng việt -> Lưu Audio MP3 ngầm nên Cảnh báo tràn đĩa cứng là bài toán ưu tiên.
Khu vực này giải quyết bằng Data biểu đồ (Lấy từ Endpoint: `GET /api/system/cache-stats`):
- **CACHE TRANSLATIONS (TEXT):** Số lượng tiêu đề lưu JSON.
- **CACHE SUMMARIES (AUDIO):** Tổng MP3 đã lưu trong hệ thống thời điểm hiện tại.
- **TỔNG DUNG LƯỢNG STORAGE:** Hiển thị Megabytes File rác hệ thống (Data sẽ tự động được dọn dẹp sau **7 ngày** kể từ khi tạo theo thiết lập trong Backend, tránh tràn ổ đĩa).

## 3. Kho Tài liệu AI (ChromaDB Vector Hub)

Một hộp Panel cho riêng DB này (Do nó khá đặc thù).
- Xem số liệu Tổng tài liệu (Files) và số Đoạn Văn (Chunks) đã chẻ nhỏ. Cung thủ với Khoảng cách thuật toán Cosine (Metric).
- **Nạp Lại (Reindex Button)**: Nhấn `🔄 Nạp lại` -> Hệ thống sẽ vứt bỏ DB cũ, tìm lại folder `data/iso_documents/`, mã hóa file Markdown thành Vector rồi nạp vào CSDL lại. Rất thích hợp khi bạn vừa thả thêm nội quy Công ty vào!
- **Tìm kiếm Thử nghiệm**: Gõ trực tiếp Test search, ví dụ: "Phòng chống ransomware". ChromaDB sẽ nhả ra 3 thẻ Card gợi ý chứa dòng text trong tài liệu.

## 4. Quản lý Lịch sử Đánh giá (ISO History)

Cung cấp danh sách Table (Bảng) ghi nhận những lần điền Form "Khảo sát và Phân tích ISO" do Backend lưu.

- Hiển thị Cột Cấp độ rủi ro (Nghiêm Trọng, Trung Bình...).
- Cho phép Bấm xem chi tiết (Mở lại report AI cũ).
- **Tính năng Xoá Lịch sử [🗑️]:** Khi click Xoá, popup Xóa sẽ văng ra. Sẽ có Option "*Không hỏi lại cảnh báo này trong vòng 24 giờ*" - Được lưu vào **localStorage** của trình duyệt. 
- Tính năng này rất tối ưu hóa UI/UX dành cho Admin quản trị thường xuyên phải xóa test dữ liệu rác.
