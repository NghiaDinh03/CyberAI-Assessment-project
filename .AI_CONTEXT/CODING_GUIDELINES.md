# CODING_GUIDELINES.md — Coding Rules & Self-Debate Protocol

> **Cập nhật:** 2026-05-07
> **Áp dụng cho:** Tất cả AI coding agents (Roo/Cline/Claude) khi làm việc với codebase CyberAI
> **QUY TẮC VÀNG:** Khi muốn thêm/sửa/xóa gì → PHẢI tự tranh luận + hỏi ý kiến user TRƯỚC khi thực hiện.

---

## 0. Three Integrated Solutions (BẮT BUỘC)

### 0.1 Caveman Protocol (Token Compression)
- All responses use Caveman terse style: bullet points, no filler, 100% technical accuracy
- Slash commands: `/caveman` (default), `/caveman lite`, `/caveman ultra`, `/caveman-commit`, `/caveman-review`, `/caveman-compress`
- Strip polite filler, omit obvious context, keep precision

### 0.2 Karpathy Guidelines
| Rule | Description |
|------|-------------|
| Think Before Coding | State assumptions, don't pick silently, push back when needed |
| Simplicity First | Minimum code, no speculative features, no over-engineering |
| Surgical Changes | Touch only what's needed, match existing style |
| Goal-Driven Execution | Define success criteria, verify after each step |

### 0.3 RTK (Rust Token Killer)
- Always prefix shell commands with `rtk`: `rtk docker compose ps`, `rtk pytest backend/tests/`
- Meta: `rtk gain`, `rtk gain --history`, `rtk discover`, `rtk proxy <cmd>`

---

## 1. Quy Trình Tự Tranh Luận (Self-Debate)

Trước MỌI thay đổi code, AI PHẢI trả lời 5 câu hỏi:

```
┌─────────────────────────────────────────────────────────────┐
│  5 CÂU HỎI BẮT BUỘC TRƯỚC KHI CODE                        │
│                                                             │
│  1. CÓ ĐƠN GIẢN HƠN ĐƯỢC KHÔNG?                           │
│     → Nếu viết 200 dòng mà 50 dòng được → viết lại        │
│                                                             │
│  2. CÓ FEATURE NÀO THÊM NGOÀI YÊU CẦU KHÔNG?              │
│     → Nếu có → cắt bỏ. Không speculative code.             │
│                                                             │
│  3. CÓ THAY ĐỔI CODE LIỀN KỀ KHÔNG LIÊN QUAN KHÔNG?       │
│     → Nếu có → revert. Chỉ sửa code liên quan trực tiếp.  │
│                                                             │
│  4. CÓ LÀM HỎNG CODE HIỆN TẠI KHÔNG?                      │
│     → Nếu không chắc → hỏi user. Không assume.             │
│                                                             │
│  5. CÓ CÁCH NÀO AN TOÀN HƠN KHÔNG?                        │
│     → Git commit trước → sửa → test → nếu fail → revert   │
└─────────────────────────────────────────────────────────────┘
```

### Ví dụ tự tranh luận

```
YÊU CẦU: "Thêm DeepSeek provider vào cloud_llm_service.py"

TỰ TRANH LUẬN:
Q1: Đơn giản hơn? → Có, chỉ cần thêm 1 function mới, không refactor code cũ.
Q2: Feature ngoài yêu cầu? → Không. Chỉ thêm DeepSeek.
Q3: Thay đổi code liền kề? → Không được sửa FALLBACK_CHAIN cũ, chỉ thêm DeepSeek vào.
Q4: Làm hỏng code hiện tại? → Không, vì thêm function mới, không sửa function cũ.
Q5: Cách an toàn hơn? → Git commit trước, thêm function mới, test, nếu fail → revert.

KẾT LUẬN: Thực hiện. Nhưng CHỈ thêm function mới, KHÔNG sửa function có sẵn.
```

---

## 2. Quy Tắc Simplicity First

| Quy tắc | Mô tả | Ví dụ đúng | Ví dụ sai |
|---------|-------|------------|-----------|
| Không thêm feature ngoài yêu cầu | Chỉ code cái user yêu cầu | User hỏi "thêm DeepSeek" → chỉ thêm DeepSeek | Thêm DeepSeek + refactor toàn bộ model router |
| Không tạo abstraction cho 1 lần dùng | Nếu chỉ dùng 1 chỗ → viết trực tiếp | `if model == "deepseek": call_deepseek()` | Tạo `AbstractCloudProvider` interface |
| Không thêm flexibility nếu không yêu cầu | Không tạo config cho "tương lai" | Hardcode timeout=30s | Tạo `TIMEOUT_CONFIG` với 10 options |
| Không xử lý lỗi cho kịch bản không thể xảy ra | Chỉ xử lý lỗi thực tế | `try/except ConnectionError` | `try/except AlienInvasion` |

---

## 3. Quy Tắc Surgical Changes

### Khi sửa file có sẵn:

```
✅ ĐƯỢC PHÉP:
├── Thêm function mới vào file
├── Sửa function mà user yêu cầu sửa
├── Thêm import cần thiết cho function mới
└── Xóa import mà THAY ĐỔI CỦA BẠT tạo ra unused

❌ KHÔNG ĐƯỢC PHÉP:
├── Sửa function liền kề không liên quan
├── Refactor code chưa hỏng
├── Đổi style/formatting code cũ
├── Thêm comment "giải thích" cho code cũ
└── Xóa dead code có sẵn (nếu không được yêu cầu)
```

### Test: Mỗi dòng thay đổi phải trace về yêu cầu nào?

```
User: "Thêm DeepSeek provider"

Dòng thay đổi hợp lệ:
├── +def call_deepseek(messages, temperature): ...     → trace: "thêm DeepSeek"
├── +from services.deepseek import DeepSeekClient      → trace: "thêm DeepSeek"
└── +TASK_MODEL_MAP["deepseek"] = "deepseek-v4-flash"  → trace: "thêm DeepSeek"

Dòng thay đổi KHÔNG hợp lệ:
├── ~def call_google_genai(...): # refactored          → KHÔNG được yêu cầu
├── ~FALLBACK_CHAIN = [...] # reordered                → KHÔNG được yêu cầu
└── -# Old comment removed                              → KHÔNG được yêu cầu
```

---

## 4. Quy Tắc Goal-Driven Execution

Mỗi task phải có acceptance criteria cụ thể:

```
❌ WEAK: "Thêm DeepSeek provider"
   → Không rõ thế nào là "hoàn thành"

✅ STRONG: "Thêm DeepSeek provider"
   → Acceptance criteria:
   1. Function call_deepseek() hoạt động → verify: unit test pass
   2. FALLBACK_CHAIN chứa deepseek → verify: assert "deepseek" in FALLBACK_CHAIN
   3. Không sửa function hiện có → verify: git diff chỉ show thêm, không show sửa
   4. Không phá code hiện tại → verify: pytest pass
```

---

## 5. Quy Tắc Bảo Vệ Code

### Trước khi sửa code:

```bash
# 1. Commit trạng thái hiện tại
git add -A
git commit -m "checkpoint: before [mô tả thay đổi]"

# 2. Thực hiện thay đổi
# ...

# 3. Test
pytest backend/tests/

# 4. Nếu fail → revert
git checkout -- <file>

# 5. Nếu pass → commit
git add -A
git commit -m "feat: [mô tả thay đổi]"
```

### Quy tắc git:

| Quy tắc | Mô tả |
|---------|-------|
| Commit trước khi sửa | Luôn có checkpoint để revert |
| Không force push | Không dùng `git push --force` |
| Không xóa branch | Không dùng `git branch -D` |
| Không rebase interactive | Không dùng `git rebase -i` |
| Message rõ ràng | `feat:`, `fix:`, `refactor:`, `docs:` |

---

## 6. Quy Tắc Hỏi Ý Kiến User

### Khi nào PHẢI hỏi:

| Tình huống | Hành động |
|-----------|-----------|
| Có nhiều cách implement | Trình bày pros/cons → hỏi user chọn |
| Không chắc yêu cầu | Hỏi lại cho rõ |
| Thay đổi ảnh hưởng nhiều file | Liệt kê files → hỏi user confirm |
| Muốn refactor code cũ | Hỏi user có muốn không |
| Phát hiện bug unrelated | Mention nhưng KHÔNG tự sửa |
| Muốn thêm feature ngoài yêu cầu | Hỏi user có muốn không |

### Khi nào KHÔNG cần hỏi:

| Tình huống | Hành động |
|-----------|-----------|
| Thêm function mới, không ảnh hưởng code cũ | Thực hiện luôn |
| Sửa bug rõ ràng (typo, syntax error) | Thực hiện luôn |
| Thêm test cho code đã viết | Thực hiện luôn |
| Update docs | Thực hiện luôn |

---

## 7. Quy Tắc An Toàn

### KHÔNG BAO GIỜ:

| Quy tắc | Lý do |
|---------|-------|
| Không xóa file trong `.AI_CONTEXT/` | MEMORY.md là append-only |
| Không sửa `.env` | Chứa secrets |
| Không sửa `docker-compose.yml` mà không hỏi | Ảnh hưởng infrastructure |
| Không sửa `database schema` mà không hỏi | Ảnh hưởng data |
| Không push code mà không test | Có thể phá production |
| Không dùng `rm -rf` | Có thể xóa nhầm |
| Không sửa file config production | Ảnh hưởng hệ thống đang chạy |

### LUÔN LUÔN:

| Quy tắc | Lý do |
|---------|-------|
| Luôn commit trước khi sửa | Có checkpoint để revert |
| Luôn test sau khi sửa | Đảm bảo không phá code |
| Luôn đọc file trước khi sửa | Hiểu context hiện tại |
| Luôn dùng relative paths | Tránh lỗi path trên OS khác nhau |
| Luôn update STRUCTURE.md khi thêm file mới | Giữ cấu trúc project chính xác |

---

## 8. Quy Tắc cho .AI_CONTEXT/

| File | Quy tắc |
|------|---------|
| `MEMORY.md` | **CHỈ GHI THÊM, KHÔNG XÓA.** Sửa thông tin cũ → ghi dòng mới, giữ dòng cũ. |
| `STRUCTURE.md` | **LUÔN UPDATE** khi thêm/sửa/xóa file trong project. |
| `CODING_GUIDELINES.md` | File này. Có thể sửa nhưng phải hỏi user. |
| `core_features_plan.md` | Plan chính. Sửa khi có feedback mới. |
| `feedback_update.md` | Phản hồi. Ghi thêm khi có feedback mới. |
| `karpathy_guidelines.md` | Tham khảo. Không sửa. |
| `subtask.md` | Subtasks. Update status khi hoàn thành. |

---

## 9. Checklist cho mỗi lần coding

```
TRƯỚC KHI CODE:
□ Đọc file cần sửa (read_file)
□ Đọc MEMORY.md (để nhớ context)
□ Đọc CODING_GUIDELINES.md (để nhớ quy tắc)
□ Tự tranh luận 5 câu hỏi
□ Git commit checkpoint

TRONG KHI CODE:
□ Chỉ thêm/sửa code liên quan trực tiếp
□ Không refactor code liền kề
□ Không thêm feature ngoài yêu cầu
□ Dùng style hiện tại (không đổi formatting)

SAU KHI CODE:
□ Test (pytest / manual)
□ Nếu fail → git checkout revert
□ Nếu pass → git commit
□ Update STRUCTURE.md nếu thêm file mới
□ Update MEMORY.md nếu có quyết định mới
```
