"""Dataset Generator — Auto-create fine-tuning dataset for SecurityLM from:
1. Completed assessments → Phase 1 training pairs (primary source)
2. Synthetic assessment pairs (Cloud AI generated)

Note: news-based dataset generation has been removed.
The news aggregator is now a separate project.
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

DATASET_DIR = os.path.join(os.getenv("DATA_PATH", "./data"), "knowledge_base")
ASSESSMENTS_DIR = os.path.join(os.getenv("DATA_PATH", "./data"), "assessments")
OUTPUT_JSONL = os.path.join(DATASET_DIR, "finetune_iso27001.jsonl")

ISO_CONTROLS_FLAT = [
    "A.5.1","A.5.2","A.5.3","A.5.4","A.5.5","A.5.6","A.5.7","A.5.8","A.5.9","A.5.10",
    "A.5.11","A.5.12","A.5.13","A.5.14","A.5.15","A.5.16","A.5.17","A.5.18","A.5.19","A.5.20",
    "A.5.21","A.5.22","A.5.23","A.5.24","A.5.25","A.5.26","A.5.27","A.5.28","A.5.29","A.5.30",
    "A.5.31","A.5.32","A.5.33","A.5.34","A.5.35","A.5.36","A.5.37",
    "A.6.1","A.6.2","A.6.3","A.6.4","A.6.5","A.6.6","A.6.7","A.6.8",
    "A.7.1","A.7.2","A.7.3","A.7.4","A.7.5","A.7.6","A.7.7","A.7.8","A.7.9","A.7.10",
    "A.7.11","A.7.12","A.7.13","A.7.14",
    "A.8.1","A.8.2","A.8.3","A.8.4","A.8.5","A.8.6","A.8.7","A.8.8","A.8.9","A.8.10",
    "A.8.11","A.8.12","A.8.13","A.8.14","A.8.15","A.8.16","A.8.17","A.8.18","A.8.19","A.8.20",
    "A.8.21","A.8.22","A.8.23","A.8.24","A.8.25","A.8.26","A.8.27","A.8.28","A.8.29","A.8.30",
    "A.8.31","A.8.32","A.8.33","A.8.34",
    "NW.01","NW.02","NW.03","NW.04","NW.05","NW.06","NW.07","NW.08",
    "SV.01","SV.02","SV.03","SV.04","SV.05","SV.06","SV.07","SV.08",
    "APP.01","APP.02","APP.03","APP.04","APP.05","APP.06","APP.07",
    "DAT.01","DAT.02","DAT.03","DAT.04","DAT.05","DAT.06",
    "MNG.01","MNG.02","MNG.03","MNG.04","MNG.05",
]


def _cloud_generate(prompt: str, max_tokens: int = 1000) -> Optional[str]:
    try:
        from services.cloud_llm_service import CloudLLMService
        result = CloudLLMService.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=max_tokens,
            task_type="iso_analysis",
        )
        return result.get("content", "").strip()
    except Exception as e:
        logger.error(f"[DatasetGen] Cloud AI failed: {e}")
        return None


def generate_from_assessments() -> List[Dict]:
    """Convert completed assessments → Phase 1 training pairs."""
    pairs = []
    if not os.path.exists(ASSESSMENTS_DIR):
        return pairs

    for fname in os.listdir(ASSESSMENTS_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(ASSESSMENTS_DIR, fname), "r", encoding="utf-8") as f:
                assessment = json.load(f)
        except Exception:
            continue

        if assessment.get("status") != "completed":
            continue

        result = assessment.get("result", {})
        raw_report = result.get("report", "")
        if not raw_report or len(raw_report) < 500:
            continue

        sys_info = assessment.get("system_info", {})
        standard = sys_info.get("assessment_standard", "iso27001")
        org = sys_info.get("organization", {})
        infra = sys_info.get("infrastructure", {})
        compliance = sys_info.get("compliance", {})
        implemented = compliance.get("implemented_controls", [])

        sys_summary = (
            f"Tổ chức: {org.get('name','')} | Ngành: {org.get('industry','')} | "
            f"Nhân sự: {org.get('employees',0)} | IT: {org.get('it_staff',0)}\n"
            f"Firewall: {infra.get('firewalls','')[:60]}\n"
            f"AV/EDR: {infra.get('antivirus','')[:50]}\n"
            f"SIEM: {infra.get('siem','')[:40]}\n"
            f"VPN: {infra.get('vpn','')}\n"
        )

        from services.controls_catalog import BUILTIN_CONTROLS
        categories = BUILTIN_CONTROLS.get(standard, BUILTIN_CONTROLS.get("iso27001", []))

        for cat in categories:
            cat_name = cat.get("category", "")
            cat_controls = cat.get("controls", [])
            missing = [c for c in cat_controls if c["id"] not in implemented]
            if not missing:
                continue

            missing_str = "\n".join(
                f"❌{c['id']}[{c.get('weight','m').upper()[0]}]{c.get('label','')[:40]}"
                for c in missing[:15]
            )
            present_ids = [c["id"] for c in cat_controls if c["id"] in implemented]

            gen_prompt = (
                f"ISO Auditor — {standard} | {cat_name} | Đánh giá GAP\n"
                f"HỆ THỐNG:{sys_summary}\n"
                f"ĐÃ ĐẠT:{', '.join(present_ids[:12])}\n"
                f"CHƯA ĐẠT:\n{missing_str}\n\n"
                f"Trả về JSON array với GAP analysis chính xác (chỉ JSON):\n"
                f'[{{"id":"XX","severity":"critical|high|medium|low","likelihood":1-5,"impact":1-5,"risk":1-25,"gap":"...","recommendation":"..."}}]'
            )
            ideal_output = _cloud_generate(gen_prompt, max_tokens=800)
            if not ideal_output:
                continue

            import re
            match = re.search(r'\[.*?\]', ideal_output, re.DOTALL)
            if not match:
                continue
            try:
                parsed = json.loads(match.group())
                if not isinstance(parsed, list):
                    continue
                pairs.append({
                    "type": "assessment_pair",
                    "assessment_id": assessment.get("id", "")[:8],
                    "category": cat_name,
                    "instruction": f"Phân tích GAP controls nhóm {cat_name} cho hệ thống sau:",
                    "input": f"{sys_summary}\nĐÃ ĐẠT:{', '.join(present_ids[:12])}\nCHƯA ĐẠT:\n{missing_str}",
                    "output": json.dumps(parsed, ensure_ascii=False),
                })
                logger.info(f"[DatasetGen] Assessment pair: {cat_name} ({len(parsed)} gaps)")
            except Exception:
                continue

    return pairs


def generate_synthetic_pairs(count: int = 20) -> List[Dict]:
    """Generate synthetic assessment scenarios using Cloud AI."""
    scenarios = [
        ("Startup SaaS 30 người, AWS, không có SIEM, antivirus cơ bản", "iso27001", "A.8 Công nghệ"),
        ("Bệnh viện 500 nhân viên, hệ thống HIS không mã hóa, Wi-Fi chung", "tcvn11930", "2. Bảo đảm ATTT Máy chủ"),
        ("Ngân hàng 2000 nhân viên, Palo Alto HA, CrowdStrike, Splunk SIEM", "iso27001", "A.5 Tổ chức"),
        ("Cơ quan nhà nước, FortiGate, BKAV, không có quy trình ứng cứu", "tcvn11930", "5. Quản lý Vận hành"),
        ("Công ty thương mại điện tử, 50 server, Kaspersky, không có WAF", "iso27001", "A.8 Công nghệ"),
    ]
    pairs = []
    for scenario, standard, category in scenarios[:count]:
        prompt = (
            f"Tạo một ví dụ đánh giá ISO {standard} thực tế:\n"
            f"Tổ chức: {scenario}\n"
            f"Category: {category}\n\n"
            f"Tạo ra:\n"
            f"1. Mô tả hệ thống ngắn (system_input)\n"
            f"2. Danh sách controls CHƯA ĐẠT trong category này\n"
            f"3. JSON GAP analysis chuẩn\n\n"
            f"Output JSON:\n"
            f'{{"system_input":"...","missing_controls":["XX","YY"],'
            f'"gap_analysis":[{{"id":"XX","severity":"...","likelihood":3,"impact":4,"risk":12,"gap":"...","recommendation":"..."}}]}}'
        )
        content = _cloud_generate(prompt, max_tokens=1000)
        if not content:
            continue
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            continue
        try:
            data = json.loads(match.group())
            sys_input = data.get("system_input", "")
            gap_analysis = data.get("gap_analysis", [])
            if not sys_input or not gap_analysis:
                continue
            pairs.append({
                "type": "synthetic",
                "scenario": scenario,
                "instruction": f"Phân tích GAP controls nhóm {category} cho hệ thống sau:",
                "input": sys_input,
                "output": json.dumps(gap_analysis, ensure_ascii=False),
            })
            logger.info(f"[DatasetGen] Synthetic pair: {scenario[:40]}")
        except Exception:
            continue
    return pairs


def export_to_jsonl(all_pairs: List[Dict], output_path: str = OUTPUT_JSONL) -> int:
    """Export all pairs to Alpaca-format JSONL for fine-tuning."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in all_pairs:
            alpaca = {
                "instruction": pair.get("instruction", ""),
                "input": pair.get("input", ""),
                "output": pair.get("output", ""),
            }
            f.write(json.dumps(alpaca, ensure_ascii=False) + "\n")
            count += 1
    logger.info(f"[DatasetGen] Exported {count} pairs to {output_path}")
    return count


def run_full_pipeline(synthetic_count: int = 10) -> Dict:
    """Run full dataset generation pipeline.

    Sources:
    - Completed assessments in /data/assessments/
    - Synthetic Cloud AI generated scenarios
    """
    results = {"assessments": 0, "synthetic": 0, "total": 0, "output": OUTPUT_JSONL}
    all_pairs = []

    logger.info("[DatasetGen] === Starting full pipeline ===")

    assessment_pairs = generate_from_assessments()
    results["assessments"] = len(assessment_pairs)
    all_pairs.extend(assessment_pairs)
    logger.info(f"[DatasetGen] Assessment pairs: {len(assessment_pairs)}")

    synthetic_pairs = generate_synthetic_pairs(count=synthetic_count)
    results["synthetic"] = len(synthetic_pairs)
    all_pairs.extend(synthetic_pairs)
    logger.info(f"[DatasetGen] Synthetic pairs: {len(synthetic_pairs)}")

    total = export_to_jsonl(all_pairs)
    results["total"] = total

    meta_path = os.path.join(DATASET_DIR, "finetune_metadata.json")
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_pairs": total,
        "breakdown": results,
        "format": "alpaca_jsonl",
        "target_model": "meta-llama/Llama-3-8B-Instruct",
        "fine_tune_method": "QLoRA 4-bit (lora_r=16)",
        "output_file": OUTPUT_JSONL,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info(f"[DatasetGen] === Pipeline complete: {total} total pairs ===")
    return results
