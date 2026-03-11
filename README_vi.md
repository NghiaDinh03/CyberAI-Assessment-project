# PhoBERT AI Platform — Hệ thống RAG, Đánh giá ISO 27001 & Tóm tắt Tin Tức Đa Tầng

Nền tảng AI on-premise kết hợp đánh giá tuân thủ **ISO 27001:2022**, Tra cứu thông tin (RAG), và Tổng hợp Tin tức Tự động. Hệ thống được triển khai bằng Docker Compose, thiết kế đặc biệt với kiến trúc Fallback đa điểm để đảm bảo tính sẵn sàng (High Availability) lớn nhất.

---

## 🏗️ Kiến trúc Công nghệ & Các Thành phần Chính

Dự án này sử dụng mô hình Client-Server với sự hỗ trợ của đa dạng AI Models, được phân bổ vào các container trong Docker.

### 1. 🖥️ Frontend (Next.js 15)
- **Giao diện người dùng (UI):** Thiết kế dạng Single Page Application (SPA) siêu tốc, không cần tải lại trang. Các Module được chia thành các Tab chức năng (Analytics, Chat, Form ISO, Tin tức).
- **Client-Side Caching:** Tích hợp bộ nhớ đệm (cache) phía client (React state/ref) cho ứng dụng Tin tức, giúp lưu trữ tạm thời các tab (An ninh mạng, Chứng khoán...) giảm tải băng thông và độ trễ khi chuyển qua lại.
- **Audio Control:** Giao diện điều khiển audio hiện đại, cho phép nghe ngay tin tức tóm tắt trên từng bài báo hoặc thông qua Panel Lịch sử (có logic tắt chéo chống âm thanh đè lên nhau).

### 2. ⚙️ Backend (FastAPI - Python)
Hệ thống API thần tốc đáp ứng mọi request từ Frontend thông qua kiến trúc đa luồng và bảo mật:
- **`chat_service.py`**: Quản lý trò chuyện, gọi LocalAI và kết nối CSDL Vector.
- **`model_router.py`**: Điều phối công việc giữa 2 model LocalAI: `SecurityLLM` (soi lỗi) và `Llama 3.1` (viết báo cáo).
- **`summary_service.py`**: Trái tim của hệ thống tóm tắt tin tức. Tích hợp cơ chế **Fallback 3 Tầng & Round-Robin**:
  1. **Google Gemini Flash (2.5)**: Xoay vòng mảng nhiều API Keys. Nếu dính Rate Limit (429), chặn key đó trong 60s và chuyển sang key kế tiếp.
  2. **OpenRouter**: Nếu toàn bộ mảng Gemini Keys bị lỗi, tự chuyển sang pool các OpenRouter API keys (cũng xoay vòng với Cooldown).
  3. **LocalAI (On-premise)**: Nếu mất mạng hoặc tất cả Cloud API đều sập/hết quota, tự động dùng AI Local để tóm tắt làm phương án cuối cùng.
- **`news_service.py`**: Quản lý việc kéo RSS từ các nguồn lớn (The Hacker News, Dark Reading, MarketWatch...). Tích hợp cơ sở dữ liệu `articles_history.json` dọn dẹp (cleanup) vòng đời tuổi thọ 7 ngày.
- **`translation_service.py`**: Dùng Model `VinAI Translate` (135M parameters) dịch tiêu đề trực tiếp bằng CPU không cần API ngoài.

### 3. 💾 Data & Logic Lưu trữ (Folder `data/`)
Đây là bộ não lưu trữ persistent (bền vững) được mount vào Docker:
- **`data/iso_documents/`**: Thư mục bạn vứt file `.md` vào, và ChromaDB sẽ đọc nó để tạo Knowledge Base cho bot ISO.
- **`data/vector_store/`**: Chứa CSDL SQLite Vector của ChromaDB.
- **`data/summaries/`**: Nơi lưu Cache JSON cho chữ và đặc biệt là folder `data/summaries/audio/`.
  - **Cơ chế Audio Caching:** Url của bài báo được băm thành **MD5 Hash**. Hệ thống dùng Edge-TTS chuyển văn bản thành giọng nói tiếng Việt và lưu thành file tĩnh bằng `hash.mp3`. Các url đã có Audio sẽ không bao giờ phải gọi TTS lại lần thứ 2, giúp lướt nhanh cho người sau. Cùng với text history, nó bị xóa sau 7 ngày để giải phóng RAM/Ổ cứng.
- **`data/assessments/`**: Lưu lịch sử báo cáo ISO được sinh ra.

---

## 📑 Các Tính năng Chia theo Giao diện (Tabs)

### 🏠 Trang chủ (Dashboard)
- Đồng hồ 4 Múi giờ Thế giới trực tiếp.
- Các nút dẫn hướng nhanh giới thiệu tính năng hệ thống.

### 💬 AI Chat (ISO RAG)
👉 **[Xem chi tiết Hướng dẫn Cơ chế Hoạt động RAG](./docs/chatbot_rag.md)**
👉 *Dành cho việc train data: [Tiêu chuẩn Format Markdown RAG & PICO](./docs/markdown_rag_standard.md)*
- Ứng dụng Retrieval-Augmented Generation (RAG). Người dùng chat, hệ thống trích xuất vector từ `vector_store` kết hợp với prompt gửi vào LocalAI Llama 3.1 để trả lời chính xác thông tin nội bộ.

### 📊 Analytics (Monitor)
👉 **[Xem chi tiết Hướng dẫn Quản trị và Analytics](./docs/analytics_monitoring.md)**
- Dashboard tối thượng theo dõi sức khỏe phần cứng (CPU, RAM).
- Theo dõi các Container và trạng thái Model AI rảnh hay đang bận.
- Quản lý kho ChromaDB (Clear, Reload), Lịch sử hệ thống.
👉 *Tham khảo thêm: [Hướng dẫn nạp dữ liệu ChromaDB](./docs/chromadb_guide.md)*

### 📝 Form ISO
👉 **[Xem chi tiết Luồng Data Form Đánh giá ISO](./docs/iso_assessment_form.md)**
- Khảo sát nhanh 20+ câu hỏi về hạ tầng Mạng doanh nghiệp.
- Sinh báo cáo Action Plan bằng AI Llama 3.1 & SecurityLLM.

### 📰 Tin tức (AI News Aggregator)
👉 **[Xem chi tiết Cơ chế Crawl Tin & Sinh Audio TTS Nội bộ](./docs/news_aggregator.md)**
- 3 Chuyên mục tin tức chính. Bài đăng được fetch liên tục.
- Hiển thị bài viết, ấn **🔊 Nghe** hệ thống sẽ tóm tắt -> sinh MP3 -> và phát (Phát từ Cache nếu nghe lần 2).
- **Panel Lịch Sử 7 Ngày Sidebar:** Hiển thị bài báo cũ của tuần, cho phép người dùng click Nghe lại Audio tĩnh đã được tạo trong lịch sử mà không tốn token.

---

## 📚 Hệ thống Tài liệu Kỹ thuật (Docs)
Dự án đi kèm bộ tài liệu phân tích kỹ thuật rất sâu, nằm trong thư mục `docs/`. Bạn có thể đọc chúng để hiểu rõ hơn cách hệ thống hoạt động:
- 📖 **[Kiến trúc Tổng thể (Architecture)](./docs/architecture.md):** Giải thích mô hình Client-Server và luồng dữ liệu.
- 📖 **[Tài liệu API Dữ liệu (API References)](./docs/api.md):** Danh sách các Endpoint API Backend đang hỗ trợ.
- 📖 **[Hướng dẫn Triển khai (Deployment)](./docs/deployment.md):** Các bước để triển khai lên server thật bằng Docker.
- 📖 **[Hướng dẫn Nạp ChromaDB (ChromaDB Guide)](./docs/chromadb_guide.md):** Cơ chế Embed file `.md` thành vector nội bộ.
- 📖 **[Tiêu chuẩn Format Markdown RAG & PICO](./docs/markdown_rag_standard.md):** Định dạng file `.md` chuẩn nhất để giúp Llama 3 hiểu và truy xuất chính xác thông tin.

---

## 🤖 Hệ thống Mô hình AI (Trí tuệ Nhân tạo)

1. **Llama 3.1 Instruct (8B)** `[LocalAI]`: "Bộ não não đa năng" viết lách, gán nhãn, tóm tắt fallback.
2. **SecurityLLM (7B)** `[LocalAI]`: Chuyên gia bảo mật dò lỗi mạng nội bộ.
3. **Gemini 2.5 Flash / OpenRouter** `[Cloud API]`: "Lính đánh thuê" tóm tắt tốc độ cao, hỗ trợ đa thread.
4. **VinAI Translate (135M)** `[HuggingFace Transformers]`: Biên dịch viên tiếng Việt 100% On-server.
5. **all-MiniLM-L6-v2** `[ChromaDB]`: Phân mảnh text thành Vector toán học.
6. **Edge-TTS** `[Microsoft Service]`: Text-to-Speech tự nhiên, mượt mà.

---

## 🚀 Cài đặt và Khởi chạy

Kiến trúc chuẩn bị vô cùng đơn giản, tất cả được đóng gói qua `docker-compose`. Mọi vấn đề về DNS hoặc Network Docker đã được tuỳ biến dọn dẹp.

1. **Clone project và thiết lập biến môi trường**
   ```bash
   git clone https://github.com/NghiaDinh03/phobert-chatbot-project.git
   cd phobert-chatbot-project
   cp .env.example .env
   ```
   > ⚠️ **Lưu ý:** Hãy mở file `.env` lên và điền nhiều API Keys vào `GEMINI_API_KEYS` và `OPENROUTER_API_KEYS` theo định dạng `key1,key2,key3`. Hệ thống sẽ tự dùng Round-Robin để cân bằng tải!

2. **Chạy Project bằng 1 lệnh**
   ```bash
   docker-compose up --build -d
   ```
   *Lệnh này sẽ tự kéo các image, tải GGUF model vào `/models`, nạp thư viện và chạy 3 container `phobert-frontend`, `phobert-backend`, `phobert-localai`.*

3. **Truy cập:** Mở trình duyệt và vào **http://localhost:3000**

---
*Dự án tập trung vào trải nghiệm Người dùng cuối (End-User) cao cấp, an toàn dữ liệu, chống tràn bộ nhớ, và Backup lỗi hệ thống nhiều tầng vững chắc.*
