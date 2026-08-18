# Dataset Schema — SecurityLM Fine-tuning (CyberAI Assessment)
# Cập nhật: 27/03/2026

## Mục tiêu

Fine-tune SecurityLM (hoặc Llama-3-8B-Instruct) để phân tích ISO 27001 GAP chính xác hơn.

**Vấn đề hiện tại:** SecurityLM 7B general model → JSON malformed, hallucinate control IDs, severity sai
**Giải pháp:** Fine-tune với dataset ISO assessment domain-specific

---

## Nguồn dữ liệu training (3 nguồn)

### Nguồn 1: Synthetic assessment pairs (Cloud AI generated)
- Input: Mô tả hạ tầng hệ thống (org, servers, firewall, SIEM...) + controls đã tick
- Output: JSON GAP analysis chuẩn per category
- Tạo bằng: Gemini/GPT-4 với prompt engineering
- Số lượng: Target 500-1000 pairs

### Nguồn 2: Existing completed assessments
- `/data/assessments/*.json` — những assessment đã chạy cloud có kết quả tốt
- Extract: system_data → Phase 1 raw_analysis (cloud version) làm ground truth
- Số lượng: N assessments × 4 categories = N×4 training pairs

### Nguồn 3: News cybersecurity → Control mapping (tính năng MỚI)
- Tin tức an ninh mạng (CVE, breach, attack) → extract threat type → map sang ISO controls
- Ví dụ: "Ransomware attack via unpatched server" → A.8.8 (Vulnerability mgmt), A.8.7 (Anti-malware)
- Tạo domain knowledge về mối liên hệ threat↔control

---

## JSONL Format (Alpaca-style instruction tuning)

```jsonl
{"instruction": "Phân tích GAP controls nhóm A.8 Công nghệ cho hệ thống sau:", "input": "Tổ chức: Công ty ABC | Ngành: Tài chính | Nhân sự: 200 | IT: 8\nFirewall: FortiGate 200F\nAV/EDR: Kaspersky không có EDR\nSIEM: Không có\nCloud: Không\nVPN: Có\nChưa đạt: A.8.7[C]Bảo vệ chống mã độc(Anti-Malware/EDR)\nA.8.8[C]Quản lý lỗ hổng kỹ thuật(Vulnerability)\nA.8.15[C]Ghi nhật ký(Logging/SIEM)\nA.8.16[C]Hoạt động giám sát(Monitoring/SOC)", "output": "[{\"id\":\"A.8.7\",\"severity\":\"critical\",\"likelihood\":4,\"impact\":5,\"risk\":20,\"gap\":\"Kaspersky không có EDR, không phát hiện được mã độc nâng cao (APT, fileless malware)\",\"recommendation\":\"Nâng cấp lên EDR (CrowdStrike/SentinelOne) trong 30 ngày, deploy toàn bộ endpoint\"},{\"id\":\"A.8.8\",\"severity\":\"critical\",\"likelihood\":4,\"impact\":4,\"risk\":16,\"gap\":\"Không có quy trình vulnerability scanning và patch management định kỳ\",\"recommendation\":\"Triển khai Tenable/OpenVAS scan hàng tuần, patch critical ≤ 7 ngày\"},{\"id\":\"A.8.15\",\"severity\":\"critical\",\"likelihood\":5,\"impact\":4,\"risk\":20,\"gap\":\"Không có SIEM, không phát hiện được tấn công brute-force, lateral movement\",\"recommendation\":\"Deploy Wazuh SIEM (miễn phí) trong 2 tuần, thu log từ tất cả server và firewall\"},{\"id\":\"A.8.16\",\"severity\":\"critical\",\"likelihood\":5,\"impact\":5,\"risk\":25,\"gap\":\"Không có SOC/NOC, tấn công có thể diễn ra hàng tuần mà không ai biết\",\"recommendation\":\"Thuê dịch vụ SOC managed service hoặc thuê thêm 1 security analyst\"}]"}
```

---

## Pipeline tự động hóa

### Step 1: Thu thập raw articles từ news history
```python
# Đọc /data/articles_history.json
# Lọc: category='cybersecurity', có summary_text, lang='en'
# Output: list[{title, url, summary_text, source}]
```

### Step 2: Cloud AI extract threat → control mapping
```
Prompt: "Từ bài báo an ninh mạng sau, xác định:
1. Loại tấn công/lỗ hổng (attack_type)
2. Các control ISO 27001 có thể ngăn chặn/phát hiện (control_ids: list)
3. Lý do mapping (reason: string)

Bài báo: {article_text}

Output JSON:
{\"attack_type\": \"...\", \"controls\": [{\"id\": \"A.X.Y\", \"role\": \"prevent|detect|respond\", \"reason\": \"...\"}]}"
```

### Step 3: Convert assessment history → training pairs
```python
# Đọc /data/assessments/*.json (chỉ status='completed', result có content)
# Per category: extract system_data chunk + cloud Phase 1 output
# Format thành Alpaca JSONL
```

### Step 4: Fine-tune với Axolotl/LLaMA-Factory
```yaml
# axolotl config
base_model: meta-llama/Llama-3-8B-Instruct
datasets:
  - path: data/knowledge_base/finetune_iso27001.jsonl
    type: alpaca
adapter: lora
lora_r: 16
lora_target_modules: [q_proj, v_proj, k_proj, o_proj]
learning_rate: 2e-4
num_epochs: 3
```

---

## Model so sánh cho fine-tuning

| Model base | Fine-tune method | RAM cần | Kết quả mong đợi |
|------------|-----------------|---------|------------------|
| Llama-3-8B-Instruct | LoRA r=16 | 16GB GPU | Best — cùng base với SecurityLM |
| Llama-3-8B-Instruct | QLoRA 4-bit | 8GB GPU | OK — chạy được trên consumer GPU |
| SecurityLM-7B (GGUF) | ❌ Không fine-tune được | - | GGUF không có weights gốc |

**Kết luận:** Target Llama-3-8B-Instruct với QLoRA 4-bit → có thể chạy trên RTX 3080 (10GB)

---

## Dataset target size

| Loại | Số pairs | Ước tính thời gian tạo |
|------|---------|----------------------|
| Synthetic assessment | 500 pairs | ~2h (batch Cloud AI) |
| From existing assessments | N×4 (N = số assessments đã chạy) | ~30 phút |
| News → control mapping | 200 pairs | ~1h (từ 7 ngày news history) |
| **Tổng** | **~750+ pairs** | **~3.5h** |

Với 750 pairs, fine-tuning LoRA 3 epochs = ~2h trên RTX 3080.

---

## Ví dụ mapping News → Controls

### Bài báo: "Microsoft Exchange zero-day exploited by Chinese APT group"
```json
{
  "attack_type": "Zero-day exploit, APT, email server compromise",
  "controls": [
    {"id": "A.8.8", "role": "prevent", "reason": "Vulnerability management - patch zero-day kịp thời"},
    {"id": "A.8.7", "role": "detect", "reason": "EDR phát hiện malicious payload sau khai thác"},
    {"id": "A.8.15", "role": "detect", "reason": "SIEM log Exchange access patterns bất thường"},
    {"id": "A.5.7", "role": "prevent", "reason": "Threat intelligence - nhận cảnh báo APT sớm"},
    {"id": "A.5.26", "role": "respond", "reason": "Incident response khi phát hiện APT"}
  ]
}
```

### Bài báo: "Ransomware encrypts hospital records via unpatched VPN"
```json
{
  "attack_type": "Ransomware, VPN vulnerability, lateral movement",
  "controls": [
    {"id": "A.8.8", "role": "prevent", "reason": "Patch VPN vulnerability ngay khi có CVE"},
    {"id": "A.8.13", "role": "recover", "reason": "Backup tốt = khôi phục sau ransomware không cần trả tiền"},
    {"id": "NW.04", "role": "prevent", "reason": "TCVN: VPN mã hóa và xác thực mạnh"},
    {"id": "A.5.29", "role": "recover", "reason": "BCP để duy trì hoạt động bệnh viện khi bị tấn công"},
    {"id": "A.8.22", "role": "prevent", "reason": "Network segmentation ngăn ransomware lây lan"}
  ]
}
```
