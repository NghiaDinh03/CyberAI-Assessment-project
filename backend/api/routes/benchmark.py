"""Benchmark & Model Comparison API — validate AI Auditor output quality against known test cases."""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()

BENCHMARK_FILE = os.path.join(
    os.getenv("DATA_PATH", "./data"), "knowledge_base", "benchmark_iso27001.json"
)


def load_benchmark() -> Dict:
    if os.path.exists(BENCHMARK_FILE):
        with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"test_cases": []}


def score_report(report: str, expected: Dict) -> Dict:
    """Score an AI-generated report against expected output criteria."""
    score = {"total": 0, "max": 0, "details": {}}

    # 1. Section completeness (5 points)
    required_sections = expected.get("report_sections_required", [])
    section_score = sum(1 for s in required_sections if s.lower() in report.lower())
    score["details"]["section_completeness"] = {
        "score": section_score,
        "max": len(required_sections),
        "found": [s for s in required_sections if s.lower() in report.lower()],
        "missing": [s for s in required_sections if s.lower() not in report.lower()]
    }
    score["total"] += section_score
    score["max"] += len(required_sections)

    # 2. Required risk IDs mentioned (critical GAPs should appear)
    top_risks = expected.get("top_risks_should_include", [])
    if top_risks:
        found_risks = sum(1 for r in top_risks if r in report)
        risk_score = round((found_risks / len(top_risks)) * 3, 1)
        score["details"]["critical_risk_coverage"] = {
            "score": risk_score,
            "max": 3.0,
            "expected_risks": top_risks,
            "found": found_risks,
            "coverage_pct": round(found_risks / len(top_risks) * 100, 1)
        }
        score["total"] += risk_score
        score["max"] += 3

    # 3. Severity emoji present (quality indicator)
    has_risk_register = "RISK REGISTER" in report.upper()
    sev_score = 0
    if "🔴" in report:
        sev_score += 1
    if "🟠" in report:
        sev_score += 1
    if "🟡" in report or "⚪" in report:
        sev_score += 1
    score["details"]["severity_formatting"] = {
        "score": sev_score,
        "max": 3,
        "has_risk_register": has_risk_register
    }
    score["total"] += sev_score
    score["max"] += 3

    # 4. Executive summary quality
    exec_present = "EXECUTIVE SUMMARY" in report.upper() or "TÓM TẮT ĐIỀU HÀNH" in report.upper()
    exec_has_metrics = any(kw in report for kw in ["Controls", "tuân thủ", "%", "VND", "ngân sách"])
    exec_score = (1 if exec_present else 0) + (1 if exec_has_metrics else 0)
    score["details"]["executive_summary"] = {
        "score": exec_score,
        "max": 2,
        "present": exec_present,
        "has_metrics": exec_has_metrics
    }
    score["total"] += exec_score
    score["max"] += 2

    # 5. Action plan specificity
    has_timeline = any(kw in report for kw in ["30 ngày", "0-30", "1-3 tháng", "3-12"])
    action_score = 2 if ("ACTION PLAN" in report.upper() or "KHUYẾN NGHỊ" in report.upper()) and has_timeline else 1 if "ACTION PLAN" in report.upper() or "KHUYẾN NGHỊ" in report.upper() else 0
    score["details"]["action_plan"] = {
        "score": action_score,
        "max": 2,
        "has_timeline": has_timeline
    }
    score["total"] += action_score
    score["max"] += 2

    score["percentage"] = round(score["total"] / score["max"] * 100, 1) if score["max"] > 0 else 0
    score["grade"] = "A" if score["percentage"] >= 85 else "B" if score["percentage"] >= 70 else "C" if score["percentage"] >= 55 else "D"
    return score


class BenchmarkRunRequest(BaseModel):
    test_case_id: Optional[str] = None  # None = run all
    model_mode: str = "hybrid"  # "local", "hybrid", "cloud"
    compare_modes: Optional[List[str]] = None  # e.g. ["local", "cloud"] for comparison


@router.get("/benchmark/test-cases")
async def list_test_cases():
    """List all benchmark test cases."""
    bm = load_benchmark()
    return {
        "version": bm.get("version", "1.0"),
        "standard": bm.get("standard"),
        "total_cases": len(bm.get("test_cases", [])),
        "test_cases": [
            {
                "id": tc["id"],
                "name": tc["name"],
                "category": tc["category"],
                "standard": tc.get("standard", "iso27001"),
                "implemented_controls_count": len(tc["input"]["implemented_controls"])
            }
            for tc in bm.get("test_cases", [])
        ],
        "evaluation_metrics": bm.get("evaluation_metrics", {}),
        "model_comparison": bm.get("model_comparison", {})
    }


@router.post("/benchmark/run")
async def run_benchmark(request: BenchmarkRunRequest, background_tasks: BackgroundTasks):
    """Run benchmark test(s) against the AI Auditor and score results."""
    from services.chat_service import ChatService

    bm = load_benchmark()
    test_cases = bm.get("test_cases", [])

    if request.test_case_id:
        test_cases = [tc for tc in test_cases if tc["id"] == request.test_case_id]
        if not test_cases:
            return {"error": f"Test case '{request.test_case_id}' not found"}

    modes_to_run = request.compare_modes or [request.model_mode]
    results = []

    for tc in test_cases:
        tc_results = {"id": tc["id"], "name": tc["name"], "category": tc["category"], "modes": {}}

        system_data = {
            "assessment_standard": tc.get("standard", "iso27001"),
            "organization": {
                "name": tc["input"]["org_name"],
                "industry": tc["input"]["industry"],
                "employees": tc["input"]["employees"],
                "it_staff": tc["input"]["it_staff"],
                "size": "large" if tc["input"]["employees"] > 200 else "medium" if tc["input"]["employees"] > 50 else "small"
            },
            "infrastructure": {
                "servers": tc["input"]["servers"],
                "firewalls": tc["input"]["firewalls"],
                "vpn": "Có" if tc["input"]["vpn"] else "Không",
                "cloud": tc["input"]["cloud"],
                "antivirus": tc["input"]["antivirus"],
                "backup": tc["input"]["backup"],
                "siem": tc["input"]["siem"],
                "network_diagram": tc["input"]["network_diagram"]
            },
            "compliance": {
                "implemented_controls": tc["input"]["implemented_controls"],
                "incidents_12m": tc["input"]["incidents_12m"],
                "iso_status": tc["input"]["iso_status"]
            },
            "notes": ""
        }

        for mode in modes_to_run:
            logger.info(f"[Benchmark] Running {tc['id']} with mode={mode}")
            start_time = time.time()
            try:
                result = ChatService.assess_system(system_data, model_mode=mode)
                elapsed = round(time.time() - start_time, 1)
                report = result.get("report", "")
                quality_score = score_report(report, tc.get("expected_output", {}))
                tc_results["modes"][mode] = {
                    "status": "ok",
                    "elapsed_seconds": elapsed,
                    "model_used": result.get("model_used", {}),
                    "quality_score": quality_score,
                    "report_length": len(report),
                    "report_preview": report[:500] if report else ""
                }
            except Exception as e:
                elapsed = round(time.time() - start_time, 1)
                tc_results["modes"][mode] = {
                    "status": "error",
                    "elapsed_seconds": elapsed,
                    "error": str(e)[:200]
                }

        results.append(tc_results)

    # Summary
    summary = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "test_cases_run": len(results),
        "modes_compared": modes_to_run,
        "per_mode_avg_score": {}
    }
    for mode in modes_to_run:
        scores = [
            r["modes"][mode]["quality_score"]["percentage"]
            for r in results
            if mode in r["modes"] and r["modes"][mode]["status"] == "ok"
        ]
        if scores:
            summary["per_mode_avg_score"][mode] = round(sum(scores) / len(scores), 1)

    return {"summary": summary, "results": results}


@router.get("/benchmark/scoring-guide")
async def scoring_guide():
    """Return scoring criteria documentation."""
    return {
        "scoring_criteria": {
            "section_completeness": {
                "max_points": 5,
                "description": "Báo cáo có đủ 5 section: ĐÁNH GIÁ TỔNG QUAN, RISK REGISTER, GAP ANALYSIS, ACTION PLAN, EXECUTIVE SUMMARY"
            },
            "critical_risk_coverage": {
                "max_points": 3,
                "description": "Các control ID rủi ro cao nhất phải được đề cập trong báo cáo"
            },
            "severity_formatting": {
                "max_points": 3,
                "description": "Sử dụng emoji severity (🔴🟠🟡⚪) và có Risk Register table"
            },
            "executive_summary": {
                "max_points": 2,
                "description": "Có Executive Summary với metrics (%, Controls, ngân sách)"
            },
            "action_plan": {
                "max_points": 2,
                "description": "Có Action Plan với timeline cụ thể (0-30 ngày, 1-3 tháng, 3-12 tháng)"
            }
        },
        "grade_scale": {
            "A": "85-100% — Báo cáo xuất sắc, đầy đủ thông tin",
            "B": "70-84% — Báo cáo tốt, thiếu một số chi tiết nhỏ",
            "C": "55-69% — Báo cáo trung bình, thiếu một số section quan trọng",
            "D": "<55% — Báo cáo yếu, thiếu nhiều thông tin cần thiết"
        },
        "tool_vs_real_audit": {
            "this_tool": "Công cụ hỗ trợ tự đánh giá (Self-Assessment Tool) — IT staff tự khai báo controls → AI phân tích GAP → báo cáo sơ bộ trong vài phút",
            "real_it_audit": "Kiểm toán CNTT thực tế — Auditor bên thứ ba đến tổ chức → phỏng vấn, kiểm tra bằng chứng, xem log → báo cáo formal sau vài tuần",
            "key_difference": "Tool này KHÔNG thể thay thế IT Audit chính thức, nhưng giúp tổ chức chuẩn bị trước và hiểu rõ khoảng cách tuân thủ",
            "data_privacy": "Chế độ Local Only: dữ liệu hạ tầng không rời khỏi server — phù hợp tổ chức có yêu cầu bảo mật cao"
        }
    }
