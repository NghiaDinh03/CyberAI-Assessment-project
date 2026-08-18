# Andrej Karpathy Guidelines — Áp dụng cho CyberAI

> **Nguồn:** https://github.com/forrestchang/andrej-karpathy-skills  
> **Ngày tạo:** 2026-05-06  
> **Mục đích:** Hướng dẫn coding cho AI agents (Roo/Cline/Claude) khi làm việc với codebase CyberAI

---

## Nội dung CLAUDE.md gốc

### 1. Think Before Coding — Nghĩ trước khi code

- **Nêu rõ giả định.** Nếu không chắc → hỏi.
- Nếu có nhiều cách hiểu → trình bày tất cả, không chọn im lặng.
- Nếu có cách đơn giản hơn → nói. Đẩy lại khi cần thiết.
- Nếu không rõ → dừng lại. Nói rõ cái gì confusing. Hỏi.

### 2. Simplicity First — Đơn giản trước

- Không code thêm feature ngoài yêu cầu.
- Không tạo abstraction cho code chỉ dùng 1 lần.
- Không thêm "flexibility" / "configurability" nếu không được yêu cầu.
- Không xử lý lỗi cho kịch bản không thể xảy ra.
- Nếu viết 200 dòng mà có thể viết 50 dòng → viết lại.

**Tự hỏi:** "Senior engineer có nói code này quá phức tạp không?" → Nếu có → đơn giản hóa.

### 3. Surgical Changes — Thay đổi phẫu thuật

Khi sửa code có sẵn:
- Không "cải thiện" code/comment/formatting liền kề.
- Không refactor code chưa hỏng.
- Theo style hiện tại, dù bạn sẽ làm khác.
- Nếu thấy dead code không liên quan → mention, không xóa.

Khi thay đổi tạo orphan:
- Xóa import/variable/function mà THAY ĐỔI CỦA BẠN tạo ra unused.
- Không xóa dead code có sẵn nếu không được yêu cầu.

**Test:** Mỗi dòng thay đổi phải trace trực tiếp về yêu cầu của user.

### 4. Goal-Driven Execution — Thực thi theo mục tiêu

Chuyển task thành mục tiêu có thể verify:
- "Thêm validation" → "Viết test cho input không hợp lệ, rồi làm cho pass"
- "Fix bug" → "Viết test tái tạo bug, rồi làm cho pass"
- "Refactor X" → "Đảm bảo test pass trước và sau"

Với multi-step task, nêu plan ngắn:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

---

## Áp dụng cho CyberAI Assessment Project

### Quy tắc cụ thể

| Quy tắc | Áp dụng cho CyberAI |
|---------|---------------------|
| **Simplicity First** | Không thêm model mới nếu gemma4 đã đủ. Không thêm feature nếu chưa có yêu cầu rõ ràng. |
| **Surgical Changes** | Khi sửa `chat_service.py` → chỉ sửa `assess_system()`, không đụng `stream_chat()`. |
| **No speculative code** | Không viết code cho "tương lai có thể cần". Chỉ code cái user yêu cầu. |
| **Verify after each step** | Mỗi task trong roadmap phải có acceptance criteria cụ thể. |
| **Match existing style** | Code Python theo style hiện tại (type hints, logging, docstrings). Frontend theo React patterns hiện có. |

### Checklist cho mỗi PR

- [ ] Có đơn giản hơn được không?
- [ ] Có feature nào thêm ngoài yêu cầu không?
- [ ] Có thay đổi code liền kề không liên quan không?
- [ ] Có test cho thay đổi mới không?
- [ ] Mỗi dòng thay đổi trace về yêu cầu nào?

---

## Cách sử dụng repo này

### Bước 1: Copy vào project

```bash
# Copy CLAUDE.md vào root của project
cp CLAUDE.md /path/to/CyberAI-Assessment-project/CLAUDE.md
```

### Bước 2: Merge với .clinerules hiện tại

File `.clinerules` hiện tại đã có RTK rule. Thêm Karpathy guidelines:

```markdown
# Thêm vào cuối .clinerules

## Karpathy Guidelines
- Simplicity first: không code thêm feature ngoài yêu cầu
- Surgical changes: chỉ sửa code liên quan trực tiếp
- Verify: mỗi task phải có acceptance criteria
- No speculative code: không viết code cho "tương lai"
```

### Bước 3: Roo/Cline tự động đọc

Khi Roo/Cline đọc `CLAUDE.md` + `.clinerules`, nó sẽ:
1. Nghĩ trước khi code (không assume)
2. Viết code đơn giản nhất có thể
3. Chỉ thay đổi code liên quan
4. Verify sau mỗi bước
