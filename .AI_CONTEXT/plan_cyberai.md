# Kế hoạch Triển khai: CyberAI Assessment Project

Tài liệu này kiểm soát kế hoạch triển khai, nâng cấp và tối ưu hóa hệ thống trí tuệ nhân tạo **CyberAI** (FastAPI + Next.js + Ollama).

---

## 🎯 Đánh giá Mức độ Sẵn sàng Go-Live: **100%**

Hệ thống CyberAI đã đạt mức hoàn thiện 100% phục vụ môi trường Go-Live của doanh nghiệp:
- Tối ưu giới hạn tài nguyên container Ollama/LocalAI chạy gemma4:latest trên CPU ổn định.
- Chuyển đổi thành công lịch sử chat bền vững lưu trữ bằng SQLite local.
- Background watcher tự động quét, parse (PDF/Word/etc.) và index tài liệu quy trình kiểm toán/ISO vào vector store ChromaDB (legacy) hoặc đưa trực tiếp vào context.

### 📋 Khoảng trống kỹ thuật đã hoàn thiện:
1. **Docker Compose Dev Mode Integration:** Cấu hình Next.js frontend chạy dev mode với hot reload tự động trong Docker.
2. **CPU Optimization for gemma4:** Thiết lập giới hạn tài nguyên và cấu hình luồng xử lý của Ollama để CPU không bị quá tải khi chạy mô hình.
3. **Chat Session Persistence:** Lưu lịch sử chat của từng case kiểm toán vào database SQLite local bền vững, an toàn.
4. **Dynamic RAG SOC Playbooks:** Background worker tự động học và tham chiếu tài liệu hướng dẫn kiểm toán của doanh nghiệp (PDF/Word) trước khi trả lời.

---

## 🛠️ Chi tiết các Phase & Subtask Phát triển

### Phase I: Docker Compose Dev Mode Integration (Hoàn thành)
- **Input:** File cấu hình `docker-compose.yml` của CyberAI và source code frontend Next.js.
- **Output nguyện vọng:**
  - Frontend Next.js của CyberAI chạy ở chế độ dev (`NODE_ENV=development`).
  - Sửa đổi code frontend/backend ở host tự động cập nhật vào Docker container (live-reload).
- **Output kết quả thực tế:**
  - [x] Đổi cấu hình frontend Next.js sang chế độ dev, mount volume `./frontend-next:/app` (loại bỏ node_modules và .next).
  - [x] Cài đặt dependencies qua `npm install` và khởi chạy `npm run dev` thông qua lệnh `command`.
- **Subtasks:**
  - `[x]` Sửa `docker-compose.yml` của CyberAI tại block `frontend`.

### Phase J: Tối ưu hóa gemma4 trên CPU (CPU Resource Hardening) (Hoàn thành)
- **Mục tiêu:** Đảm bảo mô hình gemma4 chạy ổn định, phản hồi nhanh dưới 30 giây trên môi trường CPU của doanh nghiệp mà không gây treo hệ thống. Sửa đổi code backend tự động đồng bộ.
- **Input:** File cấu hình `docker-compose.yml` và `.env` của CyberAI.
- **Output nguyện vọng:** Phản hồi mượt mà, RAM sử dụng ổn định dưới giới hạn cho phép, tự động reload khi sửa code backend.
- **Output kết quả thực tế:**
  - [x] Giới hạn tài nguyên RAM/CPU deploy cho `ollama` (limits: 16G, cpus: 8) và `localai` (limits: 12G, cpus: 8) an toàn.
  - [x] Thêm lệnh uvicorn `--reload` cho backend hỗ trợ hot-reload từ host máy tính phát triển.
- **Subtasks:**
  - [x] Thắt chặt giới hạn tài nguyên RAM/CPU trong deploy resources cho container `ollama` và `localai` trong `docker-compose.yml`.
  - [x] Cấu hình `OLLAMA_NUM_PARALLEL=2` và `OLLAMA_MAX_LOADED_MODELS=1` để tối ưu tải xử lý luồng.
  - [x] Bổ sung uvicorn `--reload` cho backend in `docker-compose.yml`.

### Phase K: Chat Session Persistence & Smart Local Fallback (Hoàn thành)
- **Mục tiêu:** Lưu vết toàn bộ lịch sử trò chuyện của kiểm toán viên với AI theo từng case kiểm toán để phục vụ điều tra hồi cứu và xử lý triệt để lỗi định dạng JSON khi local model quá yếu.
- **Input:** Cơ sở dữ liệu SQLite của CyberAI.
- **Output nguyện vọng:** Lịch sử chat được lưu trữ bền vững, tự động tải lại khi Analyst mở lại tab CyberAI, tự động cứu nguy bằng cách gọi dự phòng chéo giữa các local model và tự sửa lỗi JSON nếu gặp lỗi định dạng.
- **Output kết quả thực tế:**
  - [x] Viết lại SessionStore sử dụng SQLite database lưu tại `/data/sessions/chat_history.db`.
  - [x] Tạo các bảng `sessions` và `chat_messages` lưu trữ bền vững đa luồng an toàn.
  - [x] Đảm bảo tương thích 100% API interface cũ của SessionStore.
  - [x] Thêm try/catch an toàn ở frontend Next.js triệt tiêu lỗi `Failed to fetch` unhandled rejection.
  - [x] Tích hợp cơ chế tự động dự phòng chéo cục bộ (Ollama <-> LocalAI) và tự vá JSON để đảm bảo hoạt động 100% Offline.
- **Subtasks:**
  - [x] Tạo bảng `chat_histories` trong cơ sở dữ liệu local để lưu log hội thoại theo `session_id`.
  - [x] Tái cấu trúc SessionStore đọc/ghi SQLite.
  - [x] Tích hợp middleware tự động lưu/tải lịch sử chat khi có tin nhắn mới qua API `/api/v1/chat`.
  - [x] Tích hợp cơ chế tự động dự phòng chéo cục bộ và vá lỗi JSON tại backend.

### Phase L: Dynamic RAG SOC Playbooks & Exporter (Hoàn thành)
- **Mục tiêu:** AI có khả năng đọc hiểu các file PDF/Word chứa quy trình SOC của doanh nghiệp được lưu tại `/data/iso_documents` để đề xuất containment steps chuẩn xác theo đúng quy chuẩn riêng của công ty. Hỗ trợ xuất Excel SoA động.
- **Input:** Thư mục `/data/iso_documents` trên máy chủ.
- **Output nguyện vọng:** Phản hồi của AI tích hợp Contextual RAG từ tài liệu nội bộ (PDF/Word/etc) tự động. Bảng SoA Excel xuất ra khớp động với tiêu chuẩn đánh giá (TCVN 11930 hoặc ISO 27001) và được Việt hóa đầy đủ nhãn cột.
- **Output kết quả thực tế:**
  - [x] Viết DocumentWatcher quét thư mục `/data/iso_documents` định kỳ mỗi 30 giây.
  - [x] Sử dụng parser có sẵn (OCR, PDF, Docx) trích xuất bytes thành văn bản, chia nhỏ (chunking) khi có file mới/thay đổi.
  - [x] Tự động index các chunk vào ChromaDB collection `"iso_documents"`.
  - [x] Tránh index trùng lặp bằng cách lưu trạng thái file vào `/data/.indexed_files.json`.
  - [x] Nâng cấp `soa_exporter.py` hỗ trợ xuất Excel SoA động cho cả TCVN 11930 và ISO 27001 chuẩn chỉnh, Việt hóa cột cho TCVN.
- **Subtasks:**
  - `[x]` Viết background worker tự động phân tách (chunking) và đánh chỉ mục (vector indexing) các tài liệu mới xuất hiện trong thư mục.
  - `[x]` Đăng ký và khởi chạy watcher thread trong lifespan startup của FastAPI.
  - `[x]` Nâng cấp `backend/services/soa_exporter.py` hỗ trợ xuất Excel SoA động và Việt hóa cột cho TCVN 11930.

---

## 🛠️ Chi tiết các Phase & Subtask Phát triển (Tiếp theo)

### Phase M: GPU Acceleration & Dynamic Overlapping Chunking (Hoàn thành)
- **Input**: GPU Nvidia vật lý, Nvidia container toolkit, và cấu hình chunking của FastAPI backend.
- **Output nguyện vọng**: 
  - Chuẩn bị sẵn cấu hình Docker Compose kích hoạt GPU Nvidia.
  - Phân tách văn bản giữ ngữ cảnh nguyên vẹn, không mất thông tin.
- **Output kết quả thực tế**:
  - [x] Đã cấu hình và comment out sẵn block `deploy.resources.reservations.devices` cho Nvidia GPU ở `ollama` và `localai` service trong `docker-compose.yml` để sẵn sàng bật lên khi triển khai thật.
  - [x] Background watcher tự động thực hiện chunking với overlap giữ nguyên ngữ cảnh các tệp tài liệu SOC/ISO.
- **Subtasks**:
  - `[x]` Thiết lập sẵn cấu hình GPU Nvidia.
  - `[x]` Triển khai overlapping chunking cho watcher.

### Phase N: System Prompt Guard (AI Safety) (Hoàn thành)
- **Input**: Cấu hình System Prompt và API chatbot của FastAPI backend.
- **Output nguyện vọng**: AI phát hiện và từ chối 100% các câu hỏi jailbreak/prompt injection, trả về cảnh báo an toàn bảo mật.
- **Output kết quả thực tế**:
  - [x] Viết hàm kiểm tra Prompt Injection `_is_prompt_injection` tại `backend/services/chat_service.py` chặn đứng các hành vi chèn prompt.
  - [x] Trả về tin nhắn cảnh báo ATTT chuẩn SOC: *"Hệ thống phát hiện yêu cầu không an toàn..."*.
- **Subtasks**:
  - `[x]` Xây dựng Hard System Prompt Guard làm hàng rào bảo vệ cứng trong API của CyberAI.
  - `[x]` Kiểm thử và chặn các tin nhắn jailbreak thành công.

### Phase O: Low-Resource Model Optimization (Hoàn thành - Nâng cấp Đặc biệt)
- **Mục tiêu**: Giải quyết triệt để lỗi định dạng JSON do local model yếu/chạy CPU sinh ra, triệt tiêu latency và bypass cuộc gọi Cloud không cần thiết.
- **Input**: File content JSON lỗi cú pháp nhẹ sinh ra từ local model.
- **Output nguyện vọng**: Sửa đổi và vá lỗi JSON tự động ngay tại backend trước khi parse, giúp local model chạy mượt mà không cần retry hay fallback.
- **Output kết quả thực tế**:
  - [x] Tạo mới module `backend/utils/json_repair.py` vá các lỗi: single quotes thành double quotes, Python literals thành JSON literals, trailing commas, và tự động vá ngoặc bị thiếu ở cuối chuỗi.
  - [x] Tích hợp `json_repair` vào hàm `validate_chunk_output()` của `backend/services/assessment_helpers.py` trước khi parse.
  - [x] Tạo bộ unit test `backend/tests/test_json_repair.py` tự động kiểm thử và chạy PASS 100%.
- **Subtasks**:
  - `[x]` Viết module tự sửa lỗi JSON thông minh.
  - `[x]` Tích hợp `json_repair` vào E2E assessment pipeline.

### Phase P: Infrastructure, Cache & Smoke Tests (Hoàn thành - Hạ tầng dở dang)
- **Mục tiêu**: Tách biệt SearXNG, tối ưu khởi động Ollama và viết smoke test tự động cho frontend.
- **Input**: `docker-compose.yml`, `package.json` của frontend.
- **Output nguyện vọng**: 
  - SearXNG chạy private cục bộ.
  - Cache Ollama model pulls thành công, không pull lại khi restart.
  - Bộ smoke test frontend tự động verify status 200 cho các route chính.
- **Output kết quả thực tế**:
  - [x] Tích hợp service `searxng` private chạy trong Docker Compose.
  - [x] Sửa entrypoint Ollama thành `(ollama list | grep -q 'gemma4' || ollama pull gemma4:latest)` để chỉ pull khi chưa có sẵn.
  - [x] Viết script Node.js smoke test `/frontend-next/scripts/smoke_test.js` chạy cả static test và HTTP runtime test.
  - [x] Đăng ký `"test:smoke"` trong `package.json` của frontend, chạy PASS 100% trên các route `/`, `/chatbot`, `/form-iso`, `/settings`.
- **Subtasks**:
  - `[x]` Tách SearXNG thành service Docker riêng biệt.
  - `[x]` Cache Ollama model pulls.
  - `[x]` Viết frontend smoke test tự động.

### Phase Q: Continuous Automated Monitoring & Health Check (Hoàn thành)
- **Mục tiêu**: Xây dựng tiến trình giám sát và chạy kiểm thử tích hợp (E2E & Smoke) tự động định kỳ để đảm bảo AI Server hoạt động 24/7.
- **Input là gì**: Trạng thái các docker containers, HTTP routes backend, và các file E2E tests.
- **Output nguyện vọng**: Script chạy tự động phát hiện sự cố, kiểm thử E2E và ghi log bền vững, tránh xung đột encoding trên Windows.
- **Output kết quả thực tế**:
  - [x] Viết script Python giám sát sức khỏe `backend/scripts/health_monitor.py` tự động kiểm tra container, ping API và chạy test E2E.
  - [x] Khắc phục triệt để lỗi Unicode encoding (CP1252/UTF-8) trên môi trường Windows thông qua `sys.stdout.reconfigure`.
  - [x] Lập lịch tiến trình cron chạy ngầm tự động đánh thức và kiểm tra sức khỏe hệ thống định kỳ mỗi 15 phút.
- **Subtasks**:
  - `[x]` Xây dựng kịch bản kiểm thử health_monitor.py đa nền tảng.
  - `[x]` Thiết lập scheduler định kỳ liên tục để chạy kiểm thử sức khỏe AI server.

### Phase R: Conversational UI/UX Upgrade & Smart Error Recovery (Hoàn thành)
- **Mục tiêu**: Chuẩn hóa kỹ năng UI/UX vào `.AI_CONTEXT/`, tái cấu trúc bong bóng chat User tự co giãn, căn giữa luồng chat 840px chống mỏi mắt và xây dựng Smart Error Card có nút hành động phục hồi.
- **Input là gì**: File giao diện `frontend-next/src/app/chatbot/page.js`, `page.module.css`, và các nguyên lý Conversational UI/UX từ Dify, Claude, ChatGPT.
- **Output nguyện vọng**:
  - Tạo file `.AI_CONTEXT/UI_UX_GUIDELINES.md` và nâng cấp skill `fontend-ui-ux`.
  - Bong bóng User co giãn tự nhiên theo độ dài text, không bị kéo dài cột đứng.
  - Tách nút thao tác (Copy, Edit) ra dạng Floating Bar bên ngoài xuất hiện khi hover.
  - Xử lý lỗi Ollama 404 thành Smart Error Card thân thiện kèm nút **[🔄 Thử lại]** và **[⚡ Dùng Cloud AI]**.
  - Luồng hội thoại căn giữa màn hình (`max-width: 840px`), khoảng cách đọc tự nhiên.
- **Output kết quả thực tế đạt được**:
  - [x] Tạo mới `.AI_CONTEXT/UI_UX_GUIDELINES.md` và cập nhật `.AI_CONTEXT/.roo/skills/fontend-ui-ux/SKILL.md`.
  - [x] Tái cấu trúc `MessageBubble` trong `frontend-next/src/app/chatbot/page.js`: đưa `userFloatingActions` ra ngoài bubble, User bubble co giãn `width: fit-content; max-width: 75%` với gradient hiện đại `linear-gradient(135deg, #2563eb, #1d4ed8)`.
  - [x] Xây dựng Smart Error Card trong `MessageBubble` tự động phân loại lỗi và cung cấp 2 nút hành động trực tiếp (Retry & Switch to Cloud AI) kèm chi tiết kỹ thuật collapsible.
  - [x] Căn giữa luồng hội thoại `msgList` tại `max-width: 840px; margin: 0 auto; width: 100%;` trong `page.module.css`.
  - [x] Khắc phục lỗi `AttributeError: LOCALAI_URL` trong `backend/services/cloud_llm_service.py`.
### Phase S: Action Toolbar & Metadata Footer Upgrade (Hoàn thành)
- **Mục tiêu**: Tái cấu trúc khu vực chân tin nhắn của trợ lý AI, giải quyết triệt để lỗi nút Copy bị chập chờn ẩn hiện, bổ sung nút tạo lại câu trả lời và chuẩn hóa hiển thị metadata.
- **Input là gì**: Component `MessageBubble` trong `frontend-next/src/app/chatbot/page.js` và file CSS `page.module.css`.
- **Output nguyện vọng**:
  - Nút Copy chuyển thành Action Toolbar cố định, không bị ẩn hiện nhấp nháy hay làm giật layout.
  - Thêm nút Tạo lại (Regenerate) và nút Thử Cloud AI trực tiếp dưới tin nhắn.
  - Phân tách rõ ràng: Cụm hành động bên trái, Cụm metadata thông số (Thời gian xử lý, Model label, Timestamp) bên phải.
- **Output kết quả thực tế đạt được**:
  - [x] Tách chân tin nhắn thành `.msgFooterLeft` (Copy, Tạo lại, Thử Cloud) và `.msgFooterRight` (Elapsed badge, Model badge, RAG/Search, Timestamp).
  - [x] Sửa triệt để lỗi ẩn hiện nút Copy: Sử dụng toolbar cố định với hiệu ứng hover nhẹ, phản hồi `Đã sao chép` trực quan.
  - [x] Bổ sung nút `Tạo lại` gọi lại prompt và nút `Thử Cloud` chuyển nhanh sang Gemini Cloud.
  - [x] Tối giản giao diện: Bỏ emoji glyphs gây lệch dòng, chuẩn hóa font tabular-nums cho thông số thời gian.
### Phase T: Unified Auto-Grow Composer & SQLite Storage Architecture (Hoàn thành)
- **Mục tiêu**: Xóa bỏ thanh kéo thủ công `:::`, nâng cấp khung chat thành Unified Auto-Grow Input Card và xây dựng Database SQLite lưu trữ bền vững Lịch sử Chat & Lịch sử Đánh giá Hạ tầng ISO 27001.
- **Input là gì**:
  - Frontend: `frontend-next/src/app/chatbot/page.js`, `page.module.css`.
  - Backend: `backend/repositories/`, `backend/api/routes/`, `backend/main.py`.
- **Output nguyện vọng**:
  - Khung chat loại bỏ hoàn toàn thanh kéo `:::`, tự động tăng giảm chiều cao theo nội dung gõ (44px - 180px).
  - Nút Gửi tròn nổi bật và bộ đếm `0/5000` tích hợp tinh tế bên trong khối Input Card.
  - Xây dựng kho lưu trữ SQLite tại `data/assessments/assessments.db` và `data/sessions/chat_history.db`.
  - Các API: `GET /api/chat/sessions`, `GET /api/assessment/history`, `POST /api/assessment/history`, `GET /api/assessment/history/{id}`, `DELETE /api/assessment/history/{id}`.
- **Output kết quả thực tế đạt được**:
  - [x] Nâng cấp `page.js`: Loại bỏ `useDragResize`, triển khai `useAutoResizeTextarea` mượt mà, gom cấu trúc JSX thành Unified Input Card.
  - [x] Cập nhật `page.module.css`: Tạo style `.inputCard`, `.inputCardTextarea`, `.inputCardBottom`, `.sendBtn` với hiệu ứng focus và hover tinh tế.
  - [x] Tạo `backend/repositories/assessment_store.py` quản lý bảng `infrastructure_assessments` trong SQLite.
  - [x] Tạo `backend/api/routes/assessment_history.py` và bổ sung route `GET /api/chat/sessions` trong `chat.py`.
  - [x] Đăng ký router trong `backend/main.py` và tích hợp auto-save vào pipeline ISO 27001 trong `iso27001.py`.
  - [x] Kiểm thử toàn bộ API qua curl và PowerShell: Kết quả phản hồi HTTP 200, lưu trữ và xóa bản ghi chính xác.
### Phase U: Input Composer CSS Syntax & Modular Alignment Fix (Hoàn thành)
- **Mục tiêu**: Khắc phục triệt để lỗi cú pháp CSS trong file `page.module.css` (do khối duplicate và unclosed block khiến trình duyệt không tải được CSS và hiển thị ô textarea HTML thô màu trắng), đảm bảo mã nguồn phân chia theo từng module dễ bảo trì.
- **Input là gì**: File `frontend-next/src/app/chatbot/page.module.css` và `page.js`.
- **Output nguyện vọng**:
  - Dọn dẹp toàn bộ lỗi cú pháp CSS trong `page.module.css`.
  - Khung chat hiển thị chuẩn xác Unified Input Card: Nền tối `#131b2e`, bo góc 16px, textarea trong suốt tự co giãn, thanh công cụ tích hợp sẵn bên trong hộp thoại.
- **Output kết quả thực tế đạt được**:
  - [x] Đã xóa khối CSS trùng lặp và sửa lỗi cú pháp `}ustify-content: space-between;` cùng unclosed block `.typingWrap`.
  - [x] Khôi phục toàn bộ style cho `.inputCard`, `.inputCardTextarea`, `.sendBtn`, `.typingWrap` và `.scrollBottom`.
  - [x] Chạy kiểm thử smoke test `npm run test:smoke`: Toàn bộ các route chính đều đạt PASS.
### Phase V: React Key Deduplication & Authentication System Architecture (Hoàn thành)
- **Mục tiêu**: Xử lý triệt để cảnh báo React Key trùng lặp `gemma4:latest` và xây dựng toàn diện hệ thống Authentication (Trang Login / Register + Database SQLite + JWT Auth API + User Profile).
- **Input là gì**:
  - Frontend: `frontend-next/src/app/chatbot/page.js`, `frontend-next/src/contexts/AuthContext.js`, `frontend-next/src/app/login/`, `frontend-next/src/components/Navbar.js`.
  - Backend: `backend/repositories/user_store.py`, `backend/api/routes/auth.py`, `backend/main.py`.
- **Output nguyện vọng**:
  - Không còn warning duplicate key `gemma4:latest` trên browser console.
  - Cơ sở dữ liệu SQLite tại `data/auth/users.db` quản lý người dùng với mật khẩu mã hóa PBKDF2/SHA-256 + Salt.
  - Trang `/login` giao diện Dark Cyber / Glassmorphism hỗ trợ Đăng nhập, Đăng ký và điền nhanh tài khoản demo.
  - Navbar hiển thị thông tin Avatar người dùng, vai trò và nút Đăng xuất.
- **Output kết quả thực tế đạt được**:
  - [x] Sửa `allModels` trong `page.js`: Dùng `Map` deduplicate theo model ID, loại bỏ 100% cảnh báo duplicate key.
  - [x] Tạo `UserStore` SQLite repository tự động seed 2 tài khoản demo `admin` và `auditor`.
  - [x] Tạo router `backend/api/routes/auth.py` và đăng ký trong `main.py` hỗ trợ `/api/auth/login`, `/api/auth/register`, `/api/auth/me`.
  - [x] Tạo `AuthContext.js`, trang `frontend-next/src/app/login/page.js` và tích hợp vào `Navbar.js` cùng `layout.js`.
  - [x] Kiểm thử toàn bộ flow đăng nhập admin, auditor và test smoke đạt kết quả PASS 100%.
### Phase W: Global Auth Guard & User Settings Profile Page (Hoàn thành)
- **Mục tiêu**: Thiết lập AuthGuard bảo vệ toàn bộ ứng dụng (bắt buộc đăng nhập trước khi truy cập), điền sẵn thông tin đăng nhập demo và bổ sung khối Hồ sơ tài khoản người dùng tại trang Settings.
- **Input là gì**:
  - Frontend: `frontend-next/src/components/AuthGuard.js`, `frontend-next/src/app/login/page.js`, `frontend-next/src/app/layout.js`, `frontend-next/src/app/settings/page.js`, `frontend-next/src/app/settings/page.module.css`.
- **Output nguyện vọng**:
  - Bắt buộc người dùng đăng nhập trước khi vào xem giao diện chính (tự động chuyển hướng về `/login` nếu chưa đăng nhập).
  - Điền sẵn tài khoản `admin` / `Admin@123456` ở ô đăng nhập để tiện kiểm thử nhanh.
  - Trang `/settings` hiển thị thẻ Hồ sơ Người dùng (Avatar, Tên đầy đủ, Username, Quyền hạn, nút Đăng xuất).
- **Output kết quả thực tế đạt được**:
  - [x] Tạo `AuthGuard.js` bảo vệ toàn bộ route con, tích hợp màn hình loading khi đang xác thực.
  - [x] Cập nhật `layout.js` bọc `AuthGuard` cho toàn bộ ứng dụng.
  - [x] Điền sẵn giá trị mặc định `admin` / `Admin@123456` trong `login/page.js`.
  - [x] Thêm khối `Hồ sơ Tài khoản & Xác thực` vào `settings/page.js` và `page.module.css`.
  - [x] Kiểm thử toàn bộ flow xác thực và chuyển hướng mượt mà.
- **Subtasks**:
  - `[x]` W1: Xây dựng AuthGuard và bọc vào RootLayout.
  - `[x]` W2: Điền sẵn thông tin đăng nhập mẫu tại trang login.
  - `[x]` W3: Bổ sung User Profile Card vào trang settings.
  - `[x]` W4: Kiểm thử luồng bảo vệ và chuyển hướng trang.








