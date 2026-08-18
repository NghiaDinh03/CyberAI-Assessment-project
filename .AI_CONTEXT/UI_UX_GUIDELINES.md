# UI_UX_GUIDELINES.md — Hướng Dẫn Thiết Kế Giao Diện Trí Tuệ Nhân Tạo (Conversational AI)

> **Áp dụng cho:** Toàn bộ giao diện Chatbot, Form Đánh Giá, Dashboard và Components của CyberAI Platform.  
> **Tiêu chuẩn tham chiếu:** Dify Product UX, Claude, ChatGPT, Vercel AI SDK.

---

## 1. Nguyên Tắc Cốt Lõi (Core Principles)

| Nguyên tắc | Mô tả chi tiết |
|------------|----------------|
| **Centered Reading Rhythm** | Luồng hội thoại luôn được giới hạn `max-width: 768px – 840px` và căn giữa màn hình (`margin: 0 auto`). Không bao giờ để tin nhắn tràn ra 2 mép màn hình rộng 1920px gây mỏi mắt. |
| **Bubble Geometry & Proportions** | Bong bóng chat phải co giãn linh hoạt theo lượng văn bản (`width: fit-content; max-width: 75%`). Không nhồi nhét actions hay metadata cố định làm méo mó chiều cao bong bóng. |
| **External Floating Actions** | Các nút thao tác (Copy, Edit, Retry, Like/Dislike) phải nằm **bên ngoài** bong bóng tin nhắn, hiển thị dạng floating toolbar tinh tế khi hover hoặc focus. |
| **Human-Friendly Error Recovery** | Không bao giờ để lộ mã lỗi kỹ thuật JSON thô (`HTTP 404...`) cho người dùng cuối. Thay vào đó, cung cấp Thẻ Báo Lỗi có phân loại kèm các nút hành động cứu nguy tức thì (Retry, Đổi model). |
| **Clear Model & System State** | Luôn hiển thị trạng thái sẵn sàng của Model (Ready, Pulling progress %, Offline) và cung cấp gợi ý chuyển đổi linh hoạt giữa Local và Cloud. |

---

## 2. Quy Chuẩn Bong Bóng Tin Nhắn (Chat Bubbles)

### 2.1 Tin Nhắn Người Dùng (User Bubble)
- **Vị trí:** Căn lề phải (`justify-content: flex-end`).
- **Màu sắc & Nền:** Gradient xanh đậm hiện đại `linear-gradient(135deg, #2563eb, #1d4ed8)` hoặc dark subtle surface có viền tinh tế.
- **Bo góc:** `border-radius: 18px 18px 4px 18px` (mềm mại, góc nhọn chỉ nhẹ ở phía người nói).
- **Typography:** Font rõ ràng, `font-size: 0.9rem`, `line-height: 1.55`.
- **Timestamp & Metadata:** Hiển thị chữ nhỏ ở góc dưới ngoài hoặc góc dưới trong bong bóng không chiếm thêm khối block.
- **Thao tác (Edit/Copy):** Floating bar nằm bên trái bubble của User khi hover (`opacity: 0` -> `opacity: 1`), không làm xô lệch layout.

### 2.2 Tin Nhắn Trợ Lý AI (Assistant Bubble)
- **Vị trí:** Căn lề trái (`justify-content: flex-start`).
- **Màu sắc & Nền:** Card surface tối màu `#121826` với viền mờ `1px solid rgba(255, 255, 255, 0.08)`.
- **Avatar:** Nằm ở bên trái, căn thẳng hàng với đỉnh đầu tin nhắn (`align-items: flex-start`).
- **Markdown & Code Blocks:** Code blocks có header riêng (tên ngôn ngữ + nút Copy code), bảng dữ liệu có scroll ngang khi tràn màn hình.

---

## 3. Xử Lý Lỗi & Trạng Thái Phục Hồi (Error States & Recovery)

Khi xảy ra lỗi (mô hình chưa tải xong, mất kết nối, timeout):
```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Không thể kết nối với mô hình gemma4:latest (Ollama)    │
│ Mô hình đang được tải về hoặc dịch vụ cục bộ chưa sẵn sàng. │
│                                                             │
│ [ 🔄 Thử lại ]   [ ⚡ Chuyển sang Cloud (DeepSeek / Gemini) ] │
│                                                             │
│ ▸ Chi tiết kỹ thuật (Nhấn để xem log JSON)                 │
└─────────────────────────────────────────────────────────────┘
```
- **Màu nền:** Đỏ cảnh báo dịu mắt `rgba(239, 68, 68, 0.08)` với viền `rgba(239, 68, 68, 0.25)`.
- **Hành động tức thì:** Cung cấp ít nhất 1 nút khắc phục trực tiếp (Retry hoặc Chuyển Model).
- **Chi tiết kỹ thuật:** Thu gọn trong `<details>` để không gây rối mắt nhưng vẫn phục vụ được mục đích gỡ lỗi của kỹ thuật viên.

---

## 4. Thanh Nhập Liệu & Bộ Chọn Model (Input Composer)

- **Input Area:** Textarea tự động co giãn (`auto-resize`), bo góc 16px, viền sáng nhẹ khi focus (`border-color: #3b82f6`).
- **Model Selector:** Tích hợp gọn gàng ở góc trái của khung input hoặc thanh công cụ phía trên input với indicator rõ ràng (🟢 Ready / 🟡 Pulling / 🔴 Offline).
- **Nút Gửi (Send Button):** Tương phản cao, chuyển đổi trạng thái khi đang gõ (`active`) hoặc khi AI đang stream câu trả lời (`stop`).
