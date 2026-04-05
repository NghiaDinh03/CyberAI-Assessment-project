# context.md — Đề xuất Cải thiện cho Đồ án Tốt nghiệp

> Tài liệu này tổng hợp các đề xuất cải thiện dựa trên phản hồi của thầy Tô Nguyễn Nhật Quang (16/03/2026), phân tích lý do cần thiết, vấn đề hiện tại, và giải pháp cụ thể cho từng điểm.

---

## Mục lục

- [1. Giảm bớt phần lý thuyết, đưa thuật toán liên quan](#1-giảm-bớt-phần-lý-thuyết-đưa-thuật-toán-liên-quan)
- [2. Phần AI chưa sâu — So sánh mô hình](#2-phần-ai-chưa-sâu--so-sánh-mô-hình)
- [3. Chưa có dataset chuẩn](#3-chưa-có-dataset-chuẩn)
- [4. Production architecture, User testing, Real enterprise data](#4-production-architecture-user-testing-real-enterprise-data)

---

## 1. Giảm bớt phần lý thuyết, đưa thuật toán liên quan

### Vấn đề hiện tại

Phần lý thuyết trong báo cáo quá dài, trình bày nhiều khái niệm chung (định nghĩa ISO 27001, lịch sử ISMS, tổng quan AI) mà chưa gắn kết trực tiếp với hệ thống đã xây dựng. Thiếu mô tả thuật toán cụ thể mà hệ thống sử dụng.

### Tại sao cần thiết

Đồ án tốt nghiệp cần thể hiện năng lực kỹ thuật — thuật toán và quyết định thiết kế quan trọng hơn lý thuyết nền. Giám khảo đánh giá cao khi sinh viên **chứng minh hiểu sâu** qua việc mô tả chính xác thuật toán đã triển khai.

### Giải pháp đề xuất

**A. Thay thế lý thuyết chung bằng mô tả thuật toán cụ thể của hệ thống:**

| Thuật toán | File nguồn | Mô tả kỹ thuật cần bổ sung |
|-----------|-----------|---------------------------|
| Header-aware Chunking | `backend/repositories/vector_store.py` dòng 30–77 | Thuật toán phân đoạn văn bản nhận biết cấu trúc tiêu đề markdown (#, ##, ###), giữ ngữ cảnh phân cấp khi chunk. Chunk size = 600 chars, overlap = 150 chars, natural break detection tránh cắt giữa bảng/danh sách. |
| Multi-query Expansion | `backend/repositories/vector_store.py` dòng 158–175 | Mở rộng truy vấn tự động: thêm tiền tố `tiêu chuẩn` cho truy vấn chứa "iso"/"tcvn", thay thế từ đồng nghĩa (`đánh giá` → `kiểm toán`). Tìm kiếm union + loại bỏ trùng lặp bằng `(source, chunk_index)`. |
| Hybrid Intent Classification | `backend/services/model_router.py` dòng 146–214 | 2 tầng: (1) Semantic — ChromaDB cosine similarity trên 60+ intent templates, (2) Keyword fallback — regex pattern matching 80+ từ khóa ISO + search. Threshold-based routing đến security/general/search model. |
| Weighted Compliance Scoring | `backend/services/assessment_helpers.py` dòng 10, 168–184 | Trọng số: critical=4, high=3, medium=2, low=1. Công thức: `Score = Σ(w_i × implemented_i) / Σ(w_i) × 100%`. Risk scoring: `R = L × I` (thang 1–5). |
| Severity Normalization | `backend/services/assessment_helpers.py` dòng 137–165 | Thuật toán chuẩn hóa phân bố severity khi mô hình 7B đánh >70% critical. Sắp xếp theo risk score giảm dần, áp phân bố: 25% critical, 25% high, 30% medium, 20% low. |
| Anti-hallucination Filter | `backend/services/assessment_helpers.py` dòng 67–110 | Xác thực output JSON từ SecurityLLM: kiểm tra control ID có trong catalog đã biết, clamp giá trị (likelihood 1–5, impact 1–5, risk 1–25), cắt văn bản ≤200 ký tự/trường. |
| API Key Round-robin + Cooldown | `backend/services/cloud_llm_service.py` dòng 39–52 | Xoay vòng key với cooldown 30s khi gặp 429. Fallback chain 5 mô hình × N keys = tối đa 5N lần thử. |

**B. Mô tả toán học ngắn gọn cho báo cáo:**

```
Cosine Similarity: sim(q, d) = (q · d) / (||q|| × ||d||)
  → ChromaDB lưu distance = 1 - sim, hệ thống chuyển: score = 1 - distance
  → Ngưỡng tin cậy: score ≥ 0.35 (tương đương distance ≤ 0.65)

Weighted Compliance:
  W = Σ(w_i × c_i) / Σ(w_i) × 100%
  Trong đó: w_i ∈ {4, 3, 2, 1} (critical/high/medium/low)
            c_i ∈ {0, 1} (chưa triển khai / đã triển khai)

Risk Score:
  R = L × I, L ∈ [1,5], I ∈ [1,5], R ∈ [1,25]
```

**Ước tính công việc:** 2–3 ngày viết lại chương lý thuyết.

---

## 2. Phần AI chưa sâu — So sánh mô hình

### Vấn đề hiện tại

Báo cáo chưa có phần so sánh hiệu năng các mô hình AI (LocalAI vs Ollama vs Cloud), chưa đo lường chất lượng output, chưa giải thích tại sao chọn mô hình cụ thể cho từng tác vụ.

### Tại sao cần thiết

Đồ án sử dụng 6+ mô hình nhưng không có dữ liệu thực nghiệm chứng minh lựa chọn mô hình là hợp lý. Giám khảo sẽ hỏi: *"Tại sao dùng SecurityLLM cho GAP mà không dùng Llama? Tại sao 8B mà không phải 12B?"*

### Giải pháp đề xuất

**A. Benchmark so sánh mô hình (có thể triển khai ngay):**

Hệ thống đã có endpoint `GET /benchmark`. Cần chạy benchmark thực tế và ghi nhận kết quả:

| Thí nghiệm | Mô hình | Metric đo |
|------------|---------|-----------|
| GAP Analysis quality | SecurityLLM 7B vs Llama 8B vs gemini-3-flash | Precision/Recall trên 20 test cases ISO 27001 |
| Response latency | LocalAI vs Ollama vs Cloud | P50, P95, P99 latency (từ Prometheus histogram) |
| Token throughput | LocalAI (6 threads) vs Ollama | tokens/second trên cùng prompt |
| JSON format compliance | SecurityLLM 7B | % output parse được JSON hợp lệ (hiện đã log) |
| Severity accuracy | SecurityLLM 7B | % severity đúng vs expert annotation |
| RAG retrieval quality | ChromaDB cosine | Precision@5, Recall@5 trên 30 câu hỏi ISO |

**B. Bảng so sánh mẫu (điền sau khi chạy benchmark):**

```markdown
| Metric                  | SecurityLLM 7B | Llama 3.1 8B | Gemma 3n E4B | gemini-3-flash |
|-------------------------|---------------|-------------|-------------|---------------|
| GAP JSON parse rate     | __%           | __%         | __%         | __%           |
| Avg response time       | __s           | __s         | __s         | __s           |
| Severity accuracy       | __%           | __%         | __%         | __%           |
| RAM usage (peak)        | __ GB         | __ GB       | __ GB       | N/A           |
| Tokens/second           | __            | __          | __          | __            |
| Cost per 1K tokens      | $0 (local)    | $0 (local)  | $0 (local)  | $__           |
```

**C. Script benchmark cần xây dựng:**

File: `scripts/benchmark_models.py`
- Input: 20–30 cặp (prompt, expected_output) từ `data/knowledge_base/sample_training_pairs.jsonl`
- Chạy qua từng model endpoint
- Đo: latency, token count, JSON validity, severity match
- Output: bảng kết quả markdown + JSON

**Ước tính công việc:** 3–5 ngày (viết script benchmark + chạy + phân tích kết quả + viết báo cáo).

---

## 3. Chưa có dataset chuẩn

### Vấn đề hiện tại

Hệ thống không có dataset chuẩn hóa để đánh giá chất lượng. File `data/knowledge_base/sample_training_pairs.jsonl` chỉ là mẫu nhỏ, chưa đủ để làm benchmark nghiêm túc. Không có ground truth cho GAP analysis output.

### Tại sao cần thiết

Không có dataset = không thể đánh giá khách quan chất lượng AI. Giám khảo kỹ thuật sẽ yêu cầu: *"Làm sao biết hệ thống đánh giá đúng? Accuracy bao nhiêu?"*

### Giải pháp đề xuất

**A. Xây dựng CyberAI Evaluation Dataset (ưu tiên cao):**

| Tập dữ liệu | Kích thước | Nội dung | Nguồn |
|-------------|-----------|---------|-------|
| RAG QA Pairs | 100 cặp | Câu hỏi ISO/TCVN + câu trả lời kỳ vọng + tài liệu nguồn | Tự tạo từ 21 tài liệu |
| GAP Analysis Ground Truth | 30 cases | Hệ thống giả lập (controls implemented) + expert-annotated gaps | Tham khảo ISO auditor |
| Intent Classification | 200 câu | Message + expected intent (security/general/search) | Tự tạo + crowd-source |
| Prompt Injection | 50 câu | Injection attempts + expected block/pass | OWASP LLM Top 10 |

**B. Cấu trúc dataset đề xuất:**

```
data/evaluation/
├── rag_qa_pairs.jsonl          # {"question": "...", "answer": "...", "sources": [...]}
├── gap_analysis_cases.jsonl    # {"system_info": {...}, "controls": [...], "expected_gaps": [...]}
├── intent_classification.jsonl # {"message": "...", "expected_intent": "security"}
├── prompt_injection.jsonl      # {"message": "...", "should_block": true}
└── README.md                   # Dataset documentation
```

**C. Quy trình đánh giá:**

```
1. Chạy RAG QA → tính BLEU/ROUGE hoặc cosine similarity với câu trả lời kỳ vọng
2. Chạy GAP Analysis → so sánh severity + control IDs với ground truth
3. Chạy Intent Classification → tính accuracy, F1-score
4. Chạy Prompt Injection → tính True Positive Rate, False Positive Rate
```

**D. Tool hỗ trợ tạo dataset:**

Hệ thống đã có `backend/services/dataset_generator.py` — có thể mở rộng để:
- Sinh QA pairs tự động từ 21 tài liệu markdown
- Tạo GAP analysis test cases từ `data/knowledge_base/controls.json`
- Xuất định dạng JSONL chuẩn

**Ước tính công việc:** 5–7 ngày (tạo dataset 100+ entries + viết evaluation script + chạy + phân tích).

---

## 4. Production architecture, User testing, Real enterprise data

### Vấn đề hiện tại

Hệ thống chạy ở chế độ phát triển (`docker-compose.yml`). Chưa có:
- Triển khai production thực tế với monitoring end-to-end
- User testing với người dùng thực (IT auditor, security officer)
- Dữ liệu doanh nghiệp thực (chỉ dùng dữ liệu giả lập)

### Tại sao cần thiết

Đồ án đạt điểm cao hơn khi chứng minh hệ thống **hoạt động thực tế**, không chỉ ở môi trường lab. User testing cho thấy tính ứng dụng thực tiễn.

### Giải pháp đề xuất

**A. Production Architecture (có thể triển khai — 2–3 ngày):**

Đã có sẵn `docker-compose.prod.yml` và `nginx/nginx.conf`. Cần:

| Hạng mục | Trạng thái | Cần làm |
|---------|-----------|---------|
| Docker Compose production | ✅ Có | Kiểm tra lại, test trên VPS |
| Nginx reverse proxy + TLS | ✅ Có file cấu hình | Triển khai với Let's Encrypt |
| Prometheus metrics | ✅ Có endpoint | Thêm `prometheus.yml` + Grafana dashboard |
| Health checks | ✅ Có cho 4 services | Đã cấu hình trong docker-compose |
| Resource limits | ✅ Có | Backend 6GB, LocalAI 12GB, Ollama 12GB |
| Backup strategy | ✅ Có `scripts/backup.sh` | Test restore procedure |
| **Chưa có:** Grafana dashboard | ❌ | Tạo dashboard JSON import cho 5 metrics |
| **Chưa có:** Alert rules | ❌ | Thêm Alertmanager rules (CPU >80%, RAM >90%) |
| **Chưa có:** CI/CD pipeline | ❌ | GitHub Actions: lint + test + build + deploy |

**B. User Testing (cần 5–7 ngày):**

| Bước | Nội dung | Deliverable |
|------|---------|-------------|
| 1 | Tuyển 5–10 người thử (IT staff, auditor, sinh viên ATTT) | Danh sách testers |
| 2 | Tạo kịch bản test: 3 scenarios (chat, assessment, standard upload) | Test script document |
| 3 | Deploy lên VPS, cấp URL public | Production URL |
| 4 | Thu thập feedback: SUS (System Usability Scale) questionnaire | SUS score (target ≥ 68) |
| 5 | Đo metrics thực: response time, error rate, completion rate | Performance report |
| 6 | Phân tích + viết chương User Testing trong báo cáo | 5–8 trang |

**Kịch bản test mẫu:**
```
Scenario 1: "Bạn là IT Manager của công ty 100 nhân viên. Hãy sử dụng chatbot 
để hỏi về yêu cầu ISO 27001 cho kiểm soát truy cập."

Scenario 2: "Hãy thực hiện đánh giá ISO 27001 cho hệ thống của công ty bạn 
(50 servers, có firewall, chưa có SIEM). Chọn controls đã triển khai và xem báo cáo."

Scenario 3: "Tải lên một tiêu chuẩn bảo mật tùy chỉnh (file JSON mẫu được cung cấp) 
và kiểm tra nó xuất hiện trong danh sách tiêu chuẩn."
```

**C. Real Enterprise Data (hạn chế — giải pháp thay thế):**

Dữ liệu doanh nghiệp thực nhạy cảm, khó thu thập cho đồ án. Giải pháp thay thế:

| Phương án | Khả thi | Mô tả |
|----------|---------|-------|
| Dữ liệu ẩn danh từ công ty thực | Trung bình | Liên hệ công ty IT, xin dữ liệu đã ẩn danh |
| Dữ liệu giả lập chất lượng cao | Cao | Tạo 5 company profiles chi tiết + assessment results |
| Case study công khai | Cao | Dùng breach reports công khai (VN-CERT, NIST NVD) |
| Lab environment simulation | Cao | Dựng hệ thống lab (10 VMs, AD, firewall) → đánh giá thực |

**Ước tính tổng:** 10–15 ngày cho cả 3 hạng mục (A + B + C).

---

## Tóm tắt Ưu tiên

| # | Đề xuất | Độ khó | Thời gian | Tác động đến điểm |
|---|---------|--------|-----------|-------------------|
| 1 | Viết lại chương lý thuyết → thuật toán | Thấp | 2–3 ngày | ⭐⭐⭐⭐ Cao |
| 2 | Benchmark so sánh mô hình | Trung bình | 3–5 ngày | ⭐⭐⭐⭐⭐ Rất cao |
| 3 | Xây dựng evaluation dataset | Trung bình | 5–7 ngày | ⭐⭐⭐⭐⭐ Rất cao |
| 4a | Production deployment + Grafana | Thấp | 2–3 ngày | ⭐⭐⭐ Trung bình |
| 4b | User testing (5+ người) | Trung bình | 5–7 ngày | ⭐⭐⭐⭐⭐ Rất cao |
| 4c | Enterprise data / case study | Cao | 3–5 ngày | ⭐⭐⭐ Trung bình |

**Khuyến nghị thứ tự thực hiện:** 1 → 2 → 3 → 4b → 4a → 4c
