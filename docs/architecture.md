# Kiến trúc Hệ thống (Architecture)

## Sơ đồ Tổng quan Mạng (Network & Containers)

Hệ thống RAG & AI Aggregator sử dụng kiến trúc Containerized với Docker Compose, phân chia thành 3 node chính kết nối qua `phobert-network` (bridge network nội bộ chống rò rỉ):

1. **Frontend Container (`phobert-frontend`)**: Chạy Next.js 15, build tĩnh và phục vụ SSR (Server-Side Rendering). Nó đảm nhận Client-side cache, UI UX, và không bao giờ kết nối trực tiếp với DB hay Third-party AI.
2. **Backend Container (`phobert-backend`)**: Bộ não điều khiển trung tâm viết bằng FastAPI Python. Quản lý toàn bộ Logic, Rate Limiting, Load Balancing, và giữ kết nối tới các dịch vụ AI.
3. **LocalAI Container (`phobert-localai`)**: Chạy độc lập như một GPU/CPU Server cục bộ, mô phỏng chuẩn API OpenAI để chạy các mô hình mã nguồn mở (`Llama 3.1 GGUF`, `SecurityLLM GGUF`). Nó được giữ rỗng và tự động nạp (hot-load) các model từ ổ cứng khi có request đầu tiên.

## Cơ Chế Phối hợp AI (AI Orchestration)

Điểm nổi bật của kiến trúc là khả năng điều phối đa tầng mô hình (Multi-layered Model Execution):
- **Phân loại tác vụ nhẹ:** Dùng `VinAI Translate` (HuggingFace Transformers 135M) chạy nền ngầm trực tiếp trên tiến trình Backend Python, không gọi API, tiết kiệm chi phí cho các task như dịch title News.
- **Phân loại tác vụ bảo mật lớn:** Dùng `SecurityLLM` (7B parameters) phân tích độc lập điểm yếu của doanh nghiệp.
- **Tổng hợp News (Độ trễ thấp):** Sử dụng Cloud APIs (`Gemini 2.5 Flash`, `OpenRouter`) để có độ phản hồi (Latency) xuất sắc nhất, thay vì cố gắng lấy mô hình Local ôm đồm tất cả tác vụ chậm chạp.
- **Failover / Hoạt động ngoại tuyến (Offline Resiliency):** Tính sẵn sàng cao. Một vòng lặp Try/Catch sẽ bảo vệ quá trình News Summarization. Trình tự ưu tiên: `Gemini APIs` -> `OpenRouter APIs` -> `LocalAI`. Đảm bảo App không bao giờ chết khi bị chặn Internet.

## Cơ Chế Bộ Nhớ RAG (Retrieval-Augmented Generation)

- Thay vì nhồi nhét tài liệu dài vào Context Window 8,000 token giới hạn của mô hình, tài liệu sẽ bị `RecursiveCharacterTextSplitter` chặt thành từng khối nhỏ (Chunks).
- ChromaDB với module `all-MiniLM-L6-v2` sẽ biến các khối đó thành số (Vector Embeddings) lưu vào ổ cứng (chính là folder `/data/vector_store`).
- Khi người dùng hỏi: Câu hỏi -> Vector -> Tìm 3 khối văn bản gần giống nhất trong ChromaDB -> Gắn vào Prompt 📝 -> Đưa cho `Llama 3.1` đọc hiểu và trả lời. Cực kì chính xác và "ảo giác" (Hallucination) thấp.
