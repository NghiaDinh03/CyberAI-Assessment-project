# Hướng dẫn Cơ chế Hoạt động của AI Chat & RAG

Tính năng **AI Chatbot** của PhoBERT AI Platform không chỉ là một công cụ trò chuyện đơn thuần mà là một hệ thống **RAG (Retrieval-Augmented Generation)** tiên tiến, được thiết kế chuyên biệt cho lĩnh vực An toàn Thông tin (ATTT) và Tuân thủ ISO 27001.

## 1. Cơ chế Hoạt động RAG

Khi người dùng đặt câu hỏi, hệ thống sẽ trải qua các bước sau để sinh ra câu trả lời chính xác và đáng tin cậy:

### Bước 1: User Input (Câu hỏi của bạn)
Người dùng nhập câu hỏi trên UI (ví dụ: *"Yêu cầu về kiểm soát truy cập vật lý trong ISO 27001 là gì?"*). Frontend chuyển tiếp câu hỏi tới Backend thông qua REST API (`/api/chat`).

### Bước 2: Embedding (Mã hóa Vector)
Thay vì ném thẳng câu hỏi vào Llama 3.1 (điều này có thể dẫn đến hiện tượng 'ảo giác' - hallucination), câu hỏi trước tiên được đưa vào hàm Embedding. Mô hình `all-MiniLM-L6-v2` sẽ biến đổi câu hỏi (dạng Text) thành một Vector không gian nhiều chiều.

### Bước 3: Retrieval (Tra cứu ChromaDB)
Hệ thống lấy Vector câu hỏi, đem mang đi đối chiếu với hàng ngàn Vector (chunks) của các tài liệu rải rác trong **ChromaDB**. 
Bằng cách tính toán **Cosine Similarity**, ChromaDB sẽ lọc ra được 3 đoạn văn bản (chunks) từ các file ISO/Luật gốc có nội dung "gần nghĩa nhất" với câu hỏi.

### Bước 4: Augmented Generation (Bơm context cho LLM)
Backend sẽ nhồi nhét 3 đoạn văn bản chuẩn gốc vừa tìm được (Context) cùng với Câu hỏi ban đầu (Prompt) làm đầu vào cho LLM **Llama 3.1 8B**. 

### Bước 5: Output Sinh văn bản (Inference)
LLM Llama 3.1 dưới sự ép buộc của Prompt: *"Dựa vào các bối cảnh RAG được cung cấp, hãy trả lời câu hỏi..."*, tiến hành sinh văn bản giải thích logic, đúng luật và có kèm trích dẫn (ví dụ: *"Theo Phụ lục A.11 của ISO..."*). Sau đó, nó sẽ được stream từng chữ về giao diện người dùng.

---

## 2. Kiến trúc và Models

*   **ChromaDB**: Local Vector Database lưu trữ Embedding của các file Markdown (`data/iso_documents`).
*   **Embedding Model**: Sử dụng thuật toán mã nguồn mở (all-MiniLM-L6-v2), độ trễ cực thấp để embedding dữ liệu.
*   **Llama 3.1 (8B instruct)**: AI trung tâm đảm đương vai trò tổng hợp, suy ngẫm và phát biểu lại bằng Tiếng Việt.

---

## 3. Cách sử dụng tính năng Chatbot RAG hiệu quả
*   **Được**: Hỏi chi tiết về các điều khoản luật, hoặc cách thực hành TCVN, ISO 27001. Hệ thống sẽ bám rất sát vào RAG.
*   **Được**: Hỏi về tình trạng bảo mật, yêu cầu tư vấn hệ thống.
*   **Không Nên**: Bắt Chatbot làm thơ, giải toán, hoặc các việc ngoài chuyên môn. Dù có thể làm được, nhưng Prompts thiết kế đang ưu tiên độ khắt khe cho báo cáo ATTT.
*   **Để tăng độ chính xác**: Hãy nạp thêm nhiều file Markdown chứa Quy định nội bộ riêng của Tổ chức bạn vào ChromaDB. Xem thêm: [Hướng dẫn ChromaDB](./chromadb_guide.md).
