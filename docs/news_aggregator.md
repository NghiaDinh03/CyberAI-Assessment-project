# AI News Aggregator & Text-To-Speech (TTS)

Trong kỷ nguyên an ninh thông tin, việc tiếp thu kịp thời các tin tức chứng khoán, giá dầu, hoặc mã độc Zero-Day mới là cực kỳ quan trọng. Trang **Tin tức** được thiết kế như một quy trình Background (tự động hóa ngầm) để loại bỏ 100% rào cản ngoại ngữ.

## 1. Sơ đồ các luồng chạy của Hệ thống

### Luồng 1 (Fetch Data): Thu thập RSS định kỳ
- Mỗi 2 tiếng, Timer ở Background Python sẽ kích hoạt (Hoặc người dùng Auto-refresh trên UI).
- Script tự động quét 3 thẻ tin tức:
  - *"An Ninh Mạng"* (The Hacker News, BleepingComputer...).
  - *"Cổ Phiếu Quốc Tế"* (CNBC, Yahoo Finance).
  - *"Chứng Khoán VN"*.
- Lấy về 20-30 Header Tin (Tiêu đề, Mô tả ngắn, Link gốc).

### Luồng 2 (AI Auto-Translate):
- Vì báo nước ngoài (Title EN) là Tiếng Anh, ngay tức thì tiến trình ngầm sẽ quăng đống Title này vào **Mô hình VinAI Translate** (135 triệu tham số).
- Model này được load ngầm trên HuggingFace (hoạt động hoàn toàn Offline trong local). Nó có khả năng dịch song ngữ EN->VI xuất sắc.
- Sau vài giây, UI của người dùng đột nhiên biến đổi toàn bộ đầu báo Quốc tế hiển thị sang dạng Tiếng Việt trực quan. File kết quả dịch lưu Cache tại `data/translations/<hash>.json`.

### Luồng 3 (AI Tagging):
- Đồng thời với việc dịch, Title dịch được nạp vào Llama 3.1 nội bộ.
- Prompt cực ngắn: *"Gán 1-2 từ khóa tiêu điểm. Không giải thích thêm"*.
- Llama dán nhãn thông minh (vd: "Pháp lý", "Ransomware", "Cổ tức"). Những Tags này xuất hiện bên dưới thẻ tin tức gốc.

---

## 2. Luồng Audio Text-To-Speech (AI Tóm tắt báo)

Trọng tâm của tính năng (Button [Play Audio 🔊 Nghe]):

1. Khi click Nghe (hoặc khi background chạy), thư viện `newspaper3k` sẽ vào link báo gốc cào toàn diện bài.
2. Xóa sạch HTML, rác, định hình Text (giới hạn độ dài).
3. **Cơ Chế 3-Tier Fallback Summarization**: Hệ thống ném bài báo này vào kiến trúc 3 Tầng AI để tóm tắt chuẩn báo chí:
   - **Tầng 1 (Gemini 2.5 Flash)**: Gọi API mảng xoay vòng. Tốc độ ánh sáng. Nếu lỗi/429 khóa key 60s, thử tiếp.
   - **Tầng 2 (OpenRouter)**: Nếu toàn bộ Gemini tịt, tự động dùng OpenRouter xoay vòng.
   - **Tầng 3 (LocalAI)**: Tại máy ảo, dùng Llama xử lý nếu rớt mạng hoàn toàn.
4. Bơm dòng văn bản tóm tắt (Summary text) vừa sinh ra vào thư viện chuyên dụng **Microsoft Edge-TTS**.
5. Sinh ra File mp3, lưu định tuyến tại `data/summaries/audio/{hash}.mp3` bằng cách băm chuỗi nội dung MD5.  
6. Trạng thái nút chuyển thành `🔊 Nghe` màu xanh -> Có hiệu lực vĩnh viễn lưu đệm trên thanh Lịch sử bên cạnh.

## 3. Storage & Cleanup (Vòng đời 7 ngày)
- Để không bị nổ ổ cứng do File Mp3 (Voice), chu kỳ dọn rác của hệ thống không xóa báo trong 2 giờ nữa. Hệ thống thiết lập **Lưu giữ Lịch sử Tin tức trong 7 NGÀY**.
- Tính năng Panel Lịch Sử: Cho phép người dùng lục lại toàn bộ tin bài cũ của tuần vừa rồi để đọc tóm tắt hoặc ấn "Nghe lại" Audio Mp3 với độ trễ phản hồi bằng 0 giây (Hit Cache Object).
- Các Text/Audio Cache quá 7 Ngày sẽ bị hệ thống âm thầm Delete vĩnh viễn không thương tiếc nhằm giải phóng RAM và SSD Disk. Hệ thống bảo đảm luôn duy trì mức Storage an toàn vô hạn.
