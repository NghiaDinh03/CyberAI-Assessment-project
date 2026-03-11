# Tài liệu Hệ thống API (API References)

Đây là danh sách các Endpoint chính của Backend `FastAPI`, phục vụ cho Next.js Frontend.

## 1. API Tin tức (News API) - `api/routes/news.py`
- `GET /api/news`: Lấy danh sách tin tức mới nhất từ RSS Feeds (The Hacker News, Dark Reading, MarketWatch). Tự động chạy dịch ngầm tiêu đề nếu là báo tiếng Anh.
- `GET /api/news/history?category=...`: Trả về lịch sử các bài báo đã được tóm tắt trong 7 ngày qua, kèm theo Hash để frontend load Audio.
- `POST /api/news/summarize`: Nhận một `url` bài báo. Cào nội dung (newspaper3k) -> AI tóm tắt (Gemini/OpenRouter/LocalAI) -> Sinh audio (Edge-TTS) -> Lưu vào Cache `articles_history.json`. Trả về `audio_url` và `summary_text`.
- `GET /api/news/audio/{audio_hash}.mp3`: Endpoint tĩnh trả về file MP3 định dạng dòng âm thanh (stream) cho thẻ `<audio>` của trình duyệt.
- `DELETE /api/news/history`: Xoá dữ liệu một bài báo cụ thể trong Lịch Sử.
- `POST /api/news/reprocess`: Bắt ép (force) hệ thống cào và dịch lại bài báo từ đầu, bỏ qua cache cũ.

## 2. API Chatbot RAG - `api/routes/chat.py`
- `POST /api/chat/message`: Gửi câu hỏi của người dùng. Backend nhúng (embed) câu hỏi -> Query ChromaDB tìm context ISO -> Tạo prompt -> Gọi mô hình `Llama 3.1` qua điểm cuối của LocalAI (`http://localai:8080/v1/chat/completions`) dạng Stream.
- `GET /api/chat/history`: Lấy lịch sử đoạn chat.
- `POST /api/chat/clear`: Xoá cuộc hội thoại RAG.

## 3. API Form Đánh giá ISO - `api/routes/iso27001.py`
- `POST /api/iso27001/submit`: Gửi mảng các câu trả lời khảo sát. Hệ thống sử dụng mô hình `SecurityLLM` báo cáo rủi ro mạng, sau đó `Llama 3.1` lập Action Plan bằng tiếng Việt.
- `GET /api/iso27001/history`: Xem lại lịch sử các form đánh giá đã hoàn thành.

## 4. API Quản lý Hệ thống - `api/routes/system.py`
- `GET /api/system/status`: Trả về trạng thái các module phần cứng (CPU, RAM).
- `GET /api/system/ai-status`: Trả về trạng thái của các mô hình AI (Rảnh / Đang xử lý form / Đang tổng hợp tin tức).
- `POST /api/system/chromadb/clear`: Reset CSDL vector kiến thức RAG.
- `POST /api/system/chromadb/reload`: Tự động nạp lại toàn bộ file `.md` trong thư mục `/data/iso_documents/` vào ChromaDB.
- `GET /api/system/cache-size`: Trả về dung lượng (Megabytes) của ổ đĩa đang được dùng bởi các file Audio và JSON cache.
