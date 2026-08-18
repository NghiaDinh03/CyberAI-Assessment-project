# Tiêu chuẩn Format Markdown Tối ưu cho Hệ thống RAG

Để mô hình Llama 3.1 và Hệ thống RAG (Retrieval-Augmented Generation) hiểu sâu và trích xuất đúng nội dung nhất, các file `.md` nạp vào thư mục `data/iso_documents/` cần tuân thủ cấu trúc phân mảnh (Chunking).

---

## 1. Cơ chế Chunking hiện tại của PhoBERT (Header-Aware Splitting)

Mặc định, module `vector_store.py` của dự án đang sử dụng cơ chế **Header-Aware Chunking** cấp độ 2.
Mỗi khi gặp thẻ H2 (`##`), hệ thống sẽ ghi nhớ tiêu đề này. Khi nội dung quá dài bị cắt ra (Chunk size mặc định = 500 ký tự), hệ thống sẽ **tự động gắn lại Header** đó vào đầu đoạn văn bản bị cắt.

**👉 Lợi ích:** Mô hình LLM luôn biết đoạn văn bản nhỏ bé nó đang đọc thuộc về chuyên mục/tiêu đề nào, chống mất bối cảnh (Context Loss).

## 2. Format File .md Tiêu chuẩn Khuyến nghị

Hãy cấu trúc nội dung từ Tổng quan đến Chi tiết, và bắt buộc dùng thẻ `##` (Header 2) để định hình các đoạn thông tin lớn. Thẻ `#` (Header 1) chỉ dùng cho tên toàn bộ file.

```markdown
# Tiêu chuẩn ISO 27001:2022 - Điều khoản 5 và 6

(Phần giới thiệu chung không cần mảng lớn, mô hình sẽ gom chung)
Đây là tài liệu trình bày các nguyên tắc cơ bản...

## 5.1 Hệ thống Cấu trúc Lãnh đạo
Lãnh đạo cao nhất phải chứng minh cam kết đối với ISMS bằng cách:
- Đảm bảo các chính sách an toàn thông tin được thiết lập.
- Thúc đẩy cải tiến liên tục.
(Chỗ này dài đến mấy hệ thống cũng tự cắt và luôn nhớ mác "5.1 Hệ thống Cấu trúc Lãnh đạo")

## 6.1 Hành động giải quyết rủi ro
Khi lập kế hoạch ISMS, tổ chức phải xác định rủi ro và cơ hội.
- Đánh giá rủi ro...
- Lên phương án giải quyết...

## 6.2 Mục tiêu An toàn thông tin
Tổ chức phải thiết lập mục tiêu an toàn thông tin tại các cấp độ khác nhau.
Các mục tiêu này phải đo lường được và nhất quán với chính sách.
```

---

## 3. Giải pháp PicoLM & Ứng dụng PICO Format trong RAG

### 3.1. Giải pháp PicoLM là gì?
**PicoLM** là một framework mã nguồn mở được thiết kế tối giản nhằm hỗ trợ huấn luyện (training) và phân tích các mô hình ngôn ngữ quy mô nhỏ (như 1M đến 1B tham số). Điểm đáng giá của PicoLM nằm ở khâu tiền xử lý dữ liệu: Hệ thống thiết lập tiêu chuẩn chia nhỏ và đóng gói kho dữ liệu đầu vào thành các đoạn (chunks) có kích thước cố định là **2049 tokens** rành mạch. Việc chuẩn hóa kích thước token này giúp mô hình hấp thu dữ liệu với Performance (hiệu suất) và sự ổn định cao nhất, tránh nhiễu ngữ cảnh.

Tuy nhiên, khi làm việc với kỹ thuật RAG (sinh văn bản theo câu truy vấn), khái niệm này thường được kết hợp với một kỹ thuật đỉnh cao khác trong Y tế/Bảo mật có tên là **PICO Chunking Format** để tách mảng văn bản thành các Vector tối ưu.

### 3.2. Phương pháp Chunk và Convert Vector kết hợp PICO Format như thế nào là hợp lý?
Việc chỉ cắt văn bản thô theo số lượng ký tự hay token cố định (như 2049 tokens) dễ làm LLM mất đi mạch văn giữa chừng (Context Fragmentation).
Bởi vậy, chuẩn hợp lý và tiên tiến nhất khi convert Vector là **chia Chunk Semantic (Theo ngữ nghĩa PICO: Problem - Intervention - Comparison - Outcome)** kết hợp với kĩ thuật Header-Aware.

**Luồng Convert Vector (Embedding) chuẩn mực:**

1. **Khâu định dạng Metadata (Document Level):** Trong file `.md`, bạn viết rõ các thẻ ranh giới `## [PROBLEM]`, `## [INTERVENTION]`.
2. **Khâu Chunking (Cắt khúc dữ liệu):** Hàm `chunk_text()` trước khi đưa dữ liệu vào ChromaDB sẽ không cắt mù quáng theo số chữ. Thay vào đó, nó nhận diện kí tự `##` làm ranh giới phân tách mảng. Nếu đoạn văn bị quá dài, hệ thống sẽ chèn lại cái thẻ `## [INTERVENTION]` đấy vào phần văn bản bị ngắt đứt.
3. **Khâu Embedding (Convert Vector):** Khi đoạn text này được biến đổi thành dạng CSDL Vector thông qua model `all-MiniLM-L6-v2`, bộ não toán học của Model sẽ gán mức độ tương đồng cực đại (Cosine Similarity) giữa câu hỏi như *"Cách ly network như thế nào"* với nguyên một cụm Vector dày đặc ý nghĩa thuộc nhóm `[INTERVENTION]`.

**Mẫu ví dụ cấu trúc tài liệu PICO RAG cực kì hiệu quả:**

```markdown
# Báo cáo Sự cố Ransomware LockBit (Q3/2026)

## [PROBLEM] Phát hiện sự cố
Vào lúc 2AM, hệ thống SIEM cảnh báo bị mã hóa file bất thường do LockBit 3.0.

## [INTERVENTION] Hành động khắc phục
Đội SOC ngắt mạng 3 server DB, chặn Inbound IP lạ. Chuyển hướng lưu lượng truy cập sang Server Backup ở Site B.

## [COMPARISON] So sánh phạm vi
Rủi ro nhỏ hơn đợt tấn công Wannacry năm 2017 nhờ có Zone tách biệt trên hệ thống. Rủi ro rò rỉ ở cấp độ 2.

## [OUTCOME] Kết quả cuối cùng
Khôi phục 100% data từ Data Backup nguyên vẹn. Lỗ hổng gốc là do lộ port RDP 3389 ra thẻ mạng WAN.
```

**Tổng kết:** Bằng phương thức này, thay vì RAG tự động "xới tung" một đại dương file `.md` dạng thô, thì việc chuẩn bị cấu trúc PICO sẽ giúp thuật toán tìm Vector ánh xạ thẳng tỷ lệ 100% vào Chunk có gắn tag `## [INTERVENTION]`. Từ đó, Llama 3.1 sẽ lấy đúng bối cảnh dọn dẹp để trả lời người dùng mà không bao giờ bị chém gió (Hallucination) sang đoạn khác.

---

## 4. Ghi chú triển khai thực tế trong repo

> Các con số sau đây khớp trực tiếp với code trong
> [`backend/repositories/vector_store.py`](../../backend/repositories/vector_store.py):

| Tham số | Giá trị thực | Vị trí |
|---|---|---|
| `chunk_size` mặc định | **600 ký tự** (không phải 500 như văn bản gốc bên trên) | `vector_store.py:28` |
| `overlap` mặc định | **150 ký tự** | `vector_store.py:28` |
| Cơ chế header-aware | gán lại header H2 gần nhất vào đầu chunk | `vector_store.py:28-75` |
| Domain collection | ví dụ `iso_documents`, hoặc `custom_<std_id>` | `vector_store.py:20-26` |
| Multi-query search | `multi_query_search()` expand query thành nhiều biến thể | `vector_store.py:156-173` |

Ngưỡng confidence để chấp nhận chunk (trước khi đưa vào prompt) = **0.35**
— xem `RAG_CONFIDENCE_THRESHOLD` trong
[`backend/services/rag_service.py:18-42`](../../backend/services/rag_service.py).
