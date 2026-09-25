# CyberAI Assessment Platform — Hướng Dẫn Đánh Giá Định Lượng RAG & LLM Verdict

Tài liệu kỹ thuật hướng dẫn phương pháp, kiến trúc, công thức toán học và quy trình vận hành hệ thống đánh giá định lượng chất lượng RAG Retrieval và LLM Assessment Verdict dựa trên nhãn chuyên gia độc lập.

---

## 1. Kiến Trúc Mô-đun Đánh Giá (`backend/evaluation/`)

Mô-đun được thiết kế hoàn toàn cô lập, chạy offline trên runtime local (không phụ thuộc cloud LLM/cloud embedding), tuân thủ nghiêm ngặt nguyên tắc **chống rò rỉ dữ liệu (Anti-Leakage)** và **khử nhạy cảm thông tin (Desensitization)**.

```text
backend/evaluation/
├── schemas.py       # Pydantic models: RagEvalRecord, VerdictEvalRecord, Metrics, Artefact
├── normalizer.py    # Chuẩn hóa phán quyết, cô lập nhãn legacy (non_compliant)
├── metrics.py       # Tính toán toán học Recall@k, MRR@k, Accuracy, Macro-F1, Confusion Matrix
├── dataset.py       # Nạp dataset từ SQLite / JSON fixture, băm SHA-256 fingerprint
├── evaluator.py     # Điều phối đánh giá RAG (ChromaDB BGE-M3) và Verdict
├── run.py           # CLI entrypoint tái lập: python -m evaluation.run
└── fixtures/        # Bộ fixture đánh giá mẫu (RAG & Verdict)
```

---

## 2. Định Nghĩa Toán Học Của Các Metric

### A. RAG Retrieval Metrics

Cho tập $N_{valid}$ queries hợp lệ (có ít nhất một `relevant_chunk_id` được chuyên gia gán nhãn):

1. **Recall@k**:
   $$\text{Recall@k} = \frac{1}{N_{valid}} \sum_{i=1}^{N_{valid}} \mathbb{I}\left( \text{Top-k}(q_i) \cap \mathcal{R}_i \neq \emptyset \right)$$
   *Ý nghĩa:* Tỷ lệ các truy vấn có ít nhất một chunk liên quan nằm trong top-$k$ kết quả truy hồi.

2. **MRR@k (Mean Reciprocal Rank)**:
   $$\text{MRR@k} = \frac{1}{N_{valid}} \sum_{i=1}^{N_{valid}} \text{RR}_k(q_i)$$
   Trong đó:
   $$\text{RR}_k(q_i) = \begin{cases} \frac{1}{\text{rank}_i^*} & \text{nếu có chunk thuộc } \mathcal{R}_i \text{ tại vị trí } \text{rank}_i^* \le k \\ 0 & \text{nếu không có chunk liên quan nào trong top-}k \end{cases}$$
   *Lưu ý:* Nếu một query có nhiều relevant chunks trong top-$k$, chỉ lấy vị trí đầu tiên ($\text{rank}_i^*$) có thứ hạng cao nhất.

3. **Xử lý query thiếu nhãn:**
   - Các query có `relevant_chunk_ids = []` bị loại hoàn toàn khỏi $N_{valid}$ và thống kê riêng tại `unlabeled_or_empty_queries`.
   - Tuyệt đối không tính mù quáng vào mẫu số để tránh làm sai lệch metric.

### B. LLM Verdict Metrics

Dựa trên 5 lớp phán quyết chính thức:
`satisfied`, `partial`, `not_evidenced`, `missing`, `needs_expert_review`.

1. **Exact-match Accuracy**:
   $$\text{Accuracy} = \frac{1}{M_{valid}} \sum_{j=1}^{M_{valid}} \mathbb{I}\left( y_j = \hat{y}_j \right)$$

2. **Per-class Precision, Recall, F1**:
   $$\text{Precision}_c = \frac{TP_c}{TP_c + FP_c}, \quad \text{Recall}_c = \frac{TP_c}{TP_c + FN_c}, \quad F1_c = \frac{2 \cdot \text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c}$$

3. **Macro-F1**:
   $$\text{Macro-F1} = \frac{1}{|C_{support}|} \sum_{c \in C_{support}} F1_c$$
   *Quy tắc chuẩn:* Nếu dataset rỗng hoặc chỉ có 1 lớp duy nhất ($|C_{support}| \le 1$), metric Macro-F1 được gán là `None / Undefined` vì không mang tính đại diện thống kê.

4. **Confusion Matrix**:
   Ma trận kích thước $C \times C$ ghi nhận số lần chuyển đổi giữa lớp thực tế (Ground Truth) và lớp dự đoán (Prediction).

---

## 3. Quy Tắc Chuẩn Hóa Nhãn & Xử Lý Legacy Data

- **5 nhãn chuẩn hóa chính thức:**
  - `satisfied`: Đạt yêu cầu (Có minh chứng đầy đủ).
  - `partial`: Đạt một phần (Minh chứng chưa trọn vẹn).
  - `not_evidenced`: Chưa có minh chứng (Đơn vị chưa cung cấp).
  - `missing`: Thiếu biện pháp kiểm soát.
  - `needs_expert_review`: Cần chuyên gia trực tiếp thẩm định.

- **Dữ liệu legacy:**
  - `compliant` $\rightarrow$ Ánh xạ an toàn sang `satisfied`.
  - `partial` $\rightarrow$ Giữ nguyên `partial`.
  - `non_compliant` $\rightarrow$ **TUYỆT ĐỐI KHÔNG tự động map sang `missing` hay `not_evidenced`**. Record legacy mang nhãn này được hệ thống tự động gán trạng thái `label_status = 'needs_label_review'` và loại khỏi tập đánh giá tự động cho đến khi kiểm toán viên rà soát lại.

---

## 4. Cơ Chế Chống Rò Rỉ Dữ Liệu (Anti-Leakage Invariants)

Hệ thống phân chia ranh giới vật lý và logic:
- `split = 'few_shot'`: Chỉ dùng để nhúng làm ví dụ In-Context Learning trong prompt của Agent 2.
- `split = 'test'`: Tập kiểm thử độc lập, **KHÔNG BAO GIỜ** được truy vấn bởi hàm `get_few_shot_exemplars()`.
- Migration SQLite trên bảng `audit_feedback_exemplars` tự động thêm 2 cột `split` và `label_status` với tính chất idempotent và tạo index riêng `idx_feedback_split`.

---

## 5. Khử Nhạy Cảm Thông Tin Trong Artefact Đánh Giá

Các file kết quả tại `data/evaluations/eval_<timestamp>_<mode>.json` cam kết:
- **KHÔNG lưu:** Prompt thô của hệ thống, nội dung minh chứng chi tiết của doanh nghiệp, địa chỉ IP/mật khẩu/PII.
- **CHỈ lưu:** `case_id`, `input_ref` (dưới dạng mã băm SHA-256 `hash:<hex>`), `query_preview` (giới hạn 50 ký tự), các giá trị metric, định nghĩa metric, và hash fingerprint của dataset.

---

## 6. Hướng Dẫn Vận Hành CLI

### Chạy Đánh Giá RAG
```bash
python -m evaluation.run --standard iso27001 --split test --mode rag --top-k 5
```

### Chạy Đánh Giá LLM Verdict
```bash
python -m evaluation.run --standard iso27001 --split test --mode verdict
```

### Chạy Toàn Bộ (RAG + Verdict)
```bash
python -m evaluation.run --standard iso27001 --split test --mode all
```

### Chạy Trên Docker Container Hiện Hành
```bash
docker exec cyberai-backend python -m evaluation.run --standard iso27001 --split test --mode all
```

---

## 7. Quy Trình Gán Nhãn & Duyệt Test Case Bởi Chuyên Gia

1. **Trên Giao Diện (Auditor Feedback Drawer):**
   - Mở màn hình đánh giá ISO/TCVN, bấm vào biểu tượng **⚖️ Kho Tri Thức Kiểm Toán**.
   - Chuyển sang tab **➕ Thêm Phán Quyết Mẫu Mới**.
   - Chọn mã Control (ví dụ: `A.5.1`).
   - Chọn Phán Quyết Chuyên Gia (`satisfied`, `partial`, `not_evidenced`, `missing`, `needs_expert_review`).
   - Tại mục **Mục Đích Sử Dụng (Dataset Split)**:
     - Chọn `🧠 Few-shot Exemplar` nếu muốn AI học cách đối soát tương tự.
     - Chọn `🎯 Test Evaluation Set` nếu muốn đưa vào tập đánh giá định lượng độc lập.
   - Nhập lý do phán quyết và bấm **💾 Lưu Vào Kho Tri Thức**.

2. **Duyệt Lại Nhãn Legacy:**
   - Trong danh sách Golden Cases, các trường hợp mang nhãn cũ chưa chuẩn hóa sẽ hiển thị nhãn cảnh báo đỏ `⚠️ Cần rà soát nhãn`. Chuyên gia có thể xóa hoặc cập nhật lại phán quyết chuẩn.
