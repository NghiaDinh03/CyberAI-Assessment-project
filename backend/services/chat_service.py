"""Chat Service — Conversation routing with session memory and Cloud-first strategy."""

import re
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Generator, List

from core.config import settings
from services.cloud_llm_service import CloudLLMService
from services.model_router import route_model
from services.web_search import WebSearch
from repositories.vector_store import VectorStore
from repositories.session_store import SessionStore

logger = logging.getLogger(__name__)

SPECIAL_TOKENS = re.compile(
    r'<\|eot_id\|>|<\|start_header_id\|>|<\|end_header_id\|>|'
    r'<\|begin_of_text\|>|<\|end_of_text\|>|<\|finetune_right_pad_id\|>|'
    r'<\|reserved_special_token_\d+\|>'
)


class ChatService:
    _vector_store = None
    _session_store = None
    _vs_lock = threading.Lock()
    _ss_lock = threading.Lock()

    @classmethod
    def get_vector_store(cls):
        if cls._vector_store is None:
            with cls._vs_lock:
                if cls._vector_store is None:
                    cls._vector_store = VectorStore()
        return cls._vector_store

    @classmethod
    def get_session_store(cls) -> SessionStore:
        if cls._session_store is None:
            with cls._ss_lock:
                if cls._session_store is None:
                    cls._session_store = SessionStore()
        return cls._session_store

    @staticmethod
    def clean_response(text: str) -> str:
        return SPECIAL_TOKENS.sub('', text).strip()

    @staticmethod
    def _build_messages(message: str, routing: dict, context: str = "",
                        search_context: str = "", history: List[Dict[str, str]] = None) -> list:
        use_rag = routing["use_rag"]
        use_search = routing.get("use_search", False)

        if use_rag and context:
            system_prompt = (
                "Bạn là chuyên gia đánh giá ISO 27001:2022 và an toàn thông tin. "
                "Trả lời chính xác dựa trên tài liệu chuẩn được cung cấp. "
                "Không bịa thêm thông tin ngoài tài liệu. "
                "Nếu không tìm thấy thông tin, hãy nói rõ. "
                "Trả lời bằng tiếng Việt, rõ ràng và có cấu trúc."
            )
            user_content = f"Tài liệu tham chiếu:\n{context}\n\nCâu hỏi: {message}"
        elif use_search and search_context:
            system_prompt = (
                "Bạn là trợ lý AI thông minh có khả năng phân tích thông tin từ internet. "
                "Dưới đây là kết quả tìm kiếm web. Hãy tổng hợp và trả lời chính xác dựa trên những nguồn này. "
                "Trích dẫn nguồn URL khi cần. Trả lời bằng tiếng Việt."
            )
            user_content = f"Kết quả tìm kiếm:\n{search_context}\n\nCâu hỏi: {message}"
        else:
            system_prompt = (
                "Bạn là trợ lý AI thông minh, chuyên gia về an ninh mạng và công nghệ thông tin. "
                "Trả lời bằng tiếng Việt, rõ ràng, chính xác và có cấu trúc."
            )
            user_content = message

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_content})
        return messages

    @staticmethod
    def generate_response(message: str, session_id: str = "default") -> Dict[str, Any]:
        try:
            routing = route_model(message)
            model_name = routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                vs = ChatService.get_vector_store()
                results = vs.search(message, top_k=5)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]

            if use_search:
                search_results = WebSearch.search(message, max_results=5)
                if search_results:
                    search_context = WebSearch.format_context(search_results)
                    web_sources = [{"title": r["title"], "url": r["url"]} for r in search_results]

            ss = ChatService.get_session_store()
            history = ss.get_context_messages(session_id, max_messages=10)
            messages = ChatService._build_messages(message, routing, context, search_context, history)

            result = CloudLLMService.chat_completion(messages=messages, temperature=0.7, local_model=model_name)
            response_text = ChatService.clean_response(result["content"]) if result.get("content") else ""

            ss.add_message(session_id, "user", message)
            if response_text:
                ss.add_message(session_id, "assistant", response_text)

            return {
                "response": response_text or "Model không trả về response. Vui lòng thử lại.",
                "model": result.get("model", model_name),
                "provider": result.get("provider", "unknown"),
                "route": routing["route"],
                "session_id": session_id,
                "rag_used": use_rag,
                "search_used": use_search,
                "sources": list(set(sources)) if sources else [],
                "web_sources": web_sources,
                "tokens": {
                    "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": result.get("usage", {}).get("total_tokens", 0),
                },
            }
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "response": f"Lỗi: {str(e)}", "model": settings.MODEL_NAME,
                "provider": "error", "session_id": session_id, "error": True,
            }

    @staticmethod
    def generate_response_stream(message: str, session_id: str = "default") -> Generator:
        try:
            # Check if AI is busy
            try:
                from services.news_service import get_ai_status
                ai_status = get_ai_status()
                if "Đang rảnh" not in ai_status:
                    yield {
                        "step": "done",
                        "data": {
                            "response": f"⚠️ Hệ thống AI hiện đang bận ({ai_status}). Vui lòng chờ rồi thử lại!",
                            "model": settings.MODEL_NAME, "provider": "blocked",
                            "route": "blocked_by_queue", "session_id": session_id,
                            "rag_used": False, "search_used": False,
                            "sources": [], "web_sources": [],
                            "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        },
                    }
                    return
            except ImportError:
                pass

            yield {"step": "routing", "message": "Đang phân tích câu hỏi..."}

            routing = route_model(message)
            model_name = routing["model"]
            use_rag = routing["use_rag"]
            use_search = routing.get("use_search", False)

            context, search_context = "", ""
            sources, web_sources = [], []

            if use_rag:
                yield {"step": "rag", "message": "📚 Đang tra cứu tài liệu nội bộ..."}
                vs = ChatService.get_vector_store()
                results = vs.search(message, top_k=5)
                if results:
                    context = "\n\n---\n\n".join([r["text"] for r in results])
                    sources = [r.get("source", "") for r in results]

            if use_search:
                yield {"step": "searching", "message": "🔍 Đang tìm kiếm trên internet..."}
                search_results = WebSearch.search(message, max_results=5)
                if search_results:
                    search_context = WebSearch.format_context(search_results)
                    web_sources = [{"title": r["title"], "url": r["url"]} for r in search_results]
                    yield {"step": "search_done", "message": f"✅ Tìm thấy {len(search_results)} kết quả, đang phân tích..."}

            yield {"step": "thinking", "message": f"🤖 Đang tạo câu trả lời ({settings.CLOUD_MODEL_NAME})..."}

            ss = ChatService.get_session_store()
            history = ss.get_context_messages(session_id, max_messages=10)
            messages = ChatService._build_messages(message, routing, context, search_context, history)

            result = CloudLLMService.chat_completion(messages=messages, temperature=0.7, local_model=model_name)
            response_text = ChatService.clean_response(result["content"]) if result.get("content") else ""

            ss.add_message(session_id, "user", message)
            if response_text:
                ss.add_message(session_id, "assistant", response_text)

            yield {
                "step": "done",
                "data": {
                    "response": response_text or "Model không trả về response.",
                    "model": result.get("model", model_name),
                    "provider": result.get("provider", "unknown"),
                    "route": routing["route"],
                    "session_id": session_id,
                    "rag_used": use_rag, "search_used": use_search,
                    "sources": list(set(sources)) if sources else [],
                    "web_sources": web_sources,
                    "tokens": {
                        "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                        "total_tokens": result.get("usage", {}).get("total_tokens", 0),
                    },
                },
            }
        except Exception as e:
            logger.error(f"Stream chat error: {e}")
            yield {
                "step": "error",
                "data": {"response": f"Lỗi: {str(e)}", "model": settings.MODEL_NAME,
                         "session_id": session_id, "error": True},
            }

    @staticmethod
    def clear_conversation(session_id: str) -> Dict[str, Any]:
        ss = ChatService.get_session_store()
        ss.clear_history(session_id)
        return {"status": "ok", "message": "Đã xóa ngữ cảnh hội thoại", "session_id": session_id}

    @staticmethod
    def assess_system(system_data: Dict[str, Any], model_mode: str = "hybrid") -> Dict[str, Any]:
        from services.controls_catalog import get_categories, get_flat_controls, calc_compliance, build_weight_breakdown, BUILTIN_CONTROLS
        from services.assessment_helpers import (
            build_chunk_prompt, validate_chunk_output, gap_items_to_markdown,
            build_full_prompt, build_weight_breakdown_txt, compress_for_phase2, build_sys_summary
        )

        effective_mode = model_mode or system_data.get("model_mode", "hybrid")
        vs = ChatService.get_vector_store()
        standard = system_data.get("assessment_standard", "iso27001")

        if standard == "tcvn11930":
            search_query = "TCVN 11930 hệ thống thông tin cấp độ bảo đảm an toàn"
        elif standard == "nd13":
            search_query = "Nghị định 13 bảo vệ dữ liệu cá nhân"
        else:
            search_query = "A.5 Tổ chức, A.6 Nhân sự, A.7 Vật lý, A.8 Công nghệ"

        custom_std = None
        try:
            from services.standard_service import load_standard
            custom_std = load_standard(standard)
        except Exception:
            pass

        if custom_std:
            std_name = custom_std.get("name", standard)
            search_query = f"{std_name} compliance security controls"
            for cat in custom_std.get("controls", []):
                search_query += f", {cat.get('category', '')}"
        else:
            std_name = "ISO 27001:2022" if standard != "tcvn11930" else "TCVN 11930:2017 (Yêu cầu kỹ thuật theo 5 cấp độ)"

        context_results = vs.search(search_query, top_k=6)
        context = "\n---\n".join([r["text"] for r in context_results])

        implemented = system_data.get("compliance", {}).get("implemented_controls", [])
        compliance = calc_compliance(implemented, standard, custom_std)
        score = compliance["score"]
        max_score = compliance["max_score"]
        percentage = compliance["percentage"]

        # Load control catalog from controls_catalog module (ISO 27001, TCVN 11930, or custom)
        builtin_std_categories = get_categories(standard, custom_std)
        all_controls_flat = get_flat_controls(standard, custom_std)
        weight_breakdown, missing_controls_by_weight = build_weight_breakdown(implemented, all_controls_flat)
        weight_breakdown_txt = build_weight_breakdown_txt(weight_breakdown, missing_controls_by_weight)
        sys_summary_short = build_sys_summary(system_data)

        system_info_txt = (
            f"Tiêu chuẩn đánh giá: {std_name}\n"
            f"Mức độ tuân thủ: {score}/{max_score} Controls đạt yêu cầu ({percentage}%).\n"
            f"Các Controls đã đạt: {', '.join(implemented)}\n"
            f"{weight_breakdown_txt}\n"
            f"\nCHI TIẾT HẠ TẦNG HỆ THỐNG:\n{sys_summary_short}"
        )


        # ── Health check LocalAI before local mode ──────────────────────────
        local_available = False
        if effective_mode in ("local", "hybrid"):
            local_available = CloudLLMService.localai_health_check(
                model=settings.SECURITY_MODEL_NAME, timeout=15
            )
            if not local_available:
                logger.warning(
                    f"[Assessment] LocalAI health check FAILED (model={settings.SECURITY_MODEL_NAME}) — "
                    f"auto-upgrade mode: local→hybrid, hybrid→cloud"
                )
                if effective_mode == "local":
                    if settings.cloud_api_key_list:
                        effective_mode = "hybrid"
                        logger.warning("[Assessment] local→hybrid fallback")
                    else:
                        raise Exception(
                            "LocalAI không khởi động được và không có Cloud API key. "
                            "Kiểm tra RAM và model GGUF trong LocalAI container."
                        )
                elif effective_mode == "hybrid":
                    effective_mode = "cloud"
                    logger.warning("[Assessment] hybrid→cloud fallback (LocalAI unavailable)")

        # ── Xác định task_type + model_name cho từng Phase ──────────────────
        # Phase 1: SecurityLM — phân tích GAP kỹ thuật (domain-specific)
        # Phase 2: Meta-Llama — format báo cáo (general language model)
        if effective_mode == "local":
            p1_task_type = "iso_local"
            p1_model = settings.SECURITY_MODEL_NAME
            p2_task_type = "iso_local"
            p2_model = settings.MODEL_NAME  # Meta-Llama cho report formatting
            logger.info(f"[Assessment] local — P1={p1_model}, P2={p2_model}")
        elif effective_mode == "cloud":
            p1_task_type = "iso_analysis"
            p1_model = None  # resolved by CloudLLMService
            p2_task_type = "iso_analysis"
            p2_model = None
            logger.info("[Assessment] cloud — both phases OpenClaude")
        else:  # hybrid
            p1_task_type = "iso_local"
            p1_model = settings.SECURITY_MODEL_NAME
            p2_task_type = "iso_analysis"
            p2_model = None  # OpenClaude for report
            logger.info(f"[Assessment] hybrid — P1={p1_model} (LocalAI), P2=OpenClaude")

        try:
            raw_analysis = ""
            result_p1 = None

            if p1_task_type == "iso_local" and all_controls_flat:
                std_categories = builtin_std_categories or [{"category": "Tất cả Controls", "controls": all_controls_flat}]

                all_gap_items = []  # accumulated structured gap items
                logger.info(f"[Assessment] Chunked mode: {len(std_categories)} categories")

                for cat_idx, category in enumerate(std_categories):
                    cat_name = category.get("category", f"Category {cat_idx+1}")
                    cat_controls = category.get("controls", [])
                    missing_in_cat = [c for c in cat_controls if c["id"] not in implemented]

                    if not missing_in_cat:
                        logger.info(f"[Assessment] '{cat_name}' — all implemented, skip")
                        continue

                    # RAG: get category-specific context from ChromaDB
                    cat_rag_query = f"{cat_name} {std_name} controls requirements"
                    try:
                        cat_rag = vs.search(cat_rag_query, top_k=2)
                        cat_rag_ctx = "\n---\n".join(r["text"][:300] for r in cat_rag)
                    except Exception:
                        cat_rag_ctx = ""

                    chunk_prompt = build_chunk_prompt(
                        cat_name, cat_controls, implemented,
                        percentage, score, max_score,
                        sys_summary_short, std_name, cat_rag_ctx
                    )
                    chunk_messages = [{"role": "user", "content": chunk_prompt}]

                    chunk_gap_items = None
                    for attempt in range(3):
                        try:
                            chunk_result = CloudLLMService.chat_completion(
                                messages=chunk_messages,
                                temperature=0.2,
                                local_model=p1_model or settings.SECURITY_MODEL_NAME,
                                task_type=p1_task_type
                            )
                            if result_p1 is None:
                                result_p1 = chunk_result
                            chunk_content = chunk_result.get("content", "").strip()
                            chunk_gap_items = validate_chunk_output(chunk_content, cat_name)
                            if chunk_gap_items is not None:
                                logger.info(f"[Assessment] Chunk '{cat_name}' attempt {attempt+1}: {len(chunk_gap_items)} gaps")
                                break
                            logger.warning(f"[Assessment] Chunk '{cat_name}' invalid JSON attempt {attempt+1}")
                        except Exception as chunk_err:
                            logger.warning(f"[Assessment] Chunk '{cat_name}' attempt {attempt+1}: {chunk_err}")

                    if chunk_gap_items:
                        all_gap_items.extend(chunk_gap_items)

                raw_analysis = gap_items_to_markdown(all_gap_items)
                logger.info(f"[Assessment] All chunks complete — {len(all_gap_items)} total gaps, raw: {len(raw_analysis)} chars")

            else:
                security_prompt, user_msg = build_full_prompt(std_name, percentage, score, max_score, system_info_txt, context)
                messages_p1 = [
                    {"role": "system", "content": security_prompt},
                    {"role": "user", "content": user_msg},
                ]
                result_p1 = CloudLLMService.chat_completion(
                    messages=messages_p1,
                    temperature=0.3,
                    local_model=p1_model or settings.SECURITY_MODEL_NAME,
                    task_type=p1_task_type
                )
                raw_analysis = result_p1.get("content", "")

            raw_analysis_p2 = compress_for_phase2(raw_analysis)

            # Phase 2: Format report with Risk Register + Structured JSON output
            today = datetime.now(timezone.utc).strftime("%d/%m/%Y")
            org_name = system_data.get("organization", {}).get("name", "Tổ chức")
            industry = system_data.get("organization", {}).get("industry", "")
            org_size = system_data.get("organization", {}).get("size", "")
            employees = system_data.get("organization", {}).get("employees", 0)
            mode_label = {
                "local": f"LocalAI: SecurityLM (Phase 1) + Meta-Llama (Phase 2)",
                "cloud": "Cloud only (OpenClaude)",
                "hybrid": f"Hybrid: SecurityLM local (Phase 1) + OpenClaude (Phase 2)"
            }

            weight_summary = f"\n\nDữ liệu trọng số:\n{weight_breakdown_txt}" if weight_breakdown_txt else ""

            formatting_prompt = (
                f"Bạn là chuyên gia trình bày Báo cáo Đánh giá An toàn Thông tin chuyên nghiệp.\n"
                f"Trình bày báo cáo bằng Markdown tiếng Việt, CẤU TRÚC BẮT BUỘC:\n\n"
                f"## 1. ĐÁNH GIÁ TỔNG QUAN\n"
                f"Tuân thủ: {percentage}% — {score}/{max_score} Controls đạt\n"
                f"Bảng phân bổ: Critical/High/Medium/Low đạt bao nhiêu %\n\n"
                f"## 2. RISK REGISTER\n"
                f"| # | Control | GAP | Severity | L | I | Risk | Khuyến nghị | Timeline |\n"
                f"|---|---------|-----|----------|---|---|------|-------------|----------|\n"
                f"Severity: 🔴 Critical 🟠 High 🟡 Medium ⚪ Low | Risk=L×I giảm dần\n\n"
                f"## 3. GAP ANALYSIS\n"
                f"Phân nhóm theo severity, Critical trước.\n\n"
                f"## 4. ACTION PLAN\n"
                f"Ngắn hạn (0-30 ngày) | Trung hạn (1-3 tháng) | Dài hạn (3-12 tháng)\n\n"
                f"## 5. EXECUTIVE SUMMARY\n"
                f"a) Metrics: compliance%, controls đạt/thiếu, risk breakdown\n"
                f"b) Top 3 rủi ro + ngân sách khắc phục ước tính (VND)\n"
                f"c) Next Steps: 3 hành động ưu tiên trong 30 ngày\n\n"
                f"Tổ chức: {org_name} | Ngành: {industry} | Tiêu chuẩn: {std_name} | {today}\n\n"
                f"--- DỮ LIỆU ĐẦU VÀO ---\n{raw_analysis_p2}{weight_summary}"
            )
            result_p2 = CloudLLMService.chat_completion(
                messages=[{"role": "user", "content": formatting_prompt}],
                temperature=0.5,
                local_model=p2_model or settings.MODEL_NAME,
                task_type=p2_task_type
            )
            markdown_report = result_p2.get("content", "")

            json_data = ChatService._build_structured_json(
                raw_analysis=raw_analysis,
                percentage=percentage,
                score=score,
                max_score=max_score,
                implemented=implemented,
                weight_breakdown=weight_breakdown,
                missing_controls_by_weight=missing_controls_by_weight,
                org_name=org_name,
                industry=industry,
                org_size=org_size,
                employees=employees,
                std_name=std_name,
                standard=standard,
                today=today,
                effective_mode=effective_mode,
            )

            return {
                "report": markdown_report,
                "json_data": json_data,
                "details": [],
                "model_mode": effective_mode,
                "model_used": {
                    "phase1": f"{result_p1.get('provider') if result_p1 else 'localai'}:{result_p1.get('model') if result_p1 else settings.SECURITY_MODEL_NAME}",
                    "phase2": f"{result_p2.get('provider')}:{result_p2.get('model')}",
                },
            }
        except Exception as e:
            logger.error(f"Assessment error: {e}")
            return {"report": f"Lỗi tạo báo cáo: {str(e)}", "details": [], "error": True}

    @staticmethod
    def _build_structured_json(
        raw_analysis: str,
        percentage: float,
        score: int,
        max_score: int,
        implemented: list,
        weight_breakdown: dict,
        missing_controls_by_weight: dict,
        org_name: str,
        industry: str,
        org_size: str,
        employees: int,
        std_name: str,
        standard: str,
        today: str,
        effective_mode: str,
    ) -> dict:
        """
        Build structured JSON output for dashboard consumption.
        Parses GAP severity counts from raw Phase 1 analysis and packages
        all scoring data into a clean, frontend-parseable dict.
        """
        import re

        # ── Count severity from raw_analysis ─────────────────────────────
        critical_count = len(re.findall(r'🔴|Critical|critical', raw_analysis))
        high_count = len(re.findall(r'🟠|High(?!est)', raw_analysis))
        medium_count = len(re.findall(r'🟡|Medium|medium', raw_analysis))
        low_count = len(re.findall(r'⚪|Low(?!est)', raw_analysis))

        # Clamp to plausible range (avoid duplicate mentions inflating counts)
        total_gap_mentions = critical_count + high_count + medium_count + low_count
        if total_gap_mentions > 200:
            # Normalise: divide by ~3 to account for repeated mentions
            critical_count = max(0, critical_count // 3)
            high_count = max(0, high_count // 3)
            medium_count = max(0, medium_count // 3)
            low_count = max(0, low_count // 3)

        # ── Weight breakdown from controls ────────────────────────────────
        wb = weight_breakdown or {}
        missing = missing_controls_by_weight or {}

        def wb_pct(w):
            bd = wb.get(w, {})
            total = bd.get("total", 0)
            impl = bd.get("implemented", 0)
            return round((impl / total * 100), 1) if total > 0 else 0.0

        # ── Compliance tier ───────────────────────────────────────────────
        if percentage >= 80:
            tier = "high"
            tier_label = "Tuân thủ cao"
        elif percentage >= 50:
            tier = "medium"
            tier_label = "Tuân thủ một phần"
        elif percentage >= 25:
            tier = "low"
            tier_label = "Tuân thủ thấp"
        else:
            tier = "critical"
            tier_label = "Không tuân thủ"

        # ── Build top missing controls list ──────────────────────────────
        top_gaps = []
        for sev in ["critical", "high", "medium"]:
            for ctrl_str in (missing.get(sev, []))[:5]:
                parts = ctrl_str.split(" (", 1)
                ctrl_id = parts[0].strip()
                ctrl_label = parts[1].rstrip(")") if len(parts) > 1 else ""
                top_gaps.append({"id": ctrl_id, "label": ctrl_label, "severity": sev})
            if len(top_gaps) >= 10:
                break

        return {
            "assessment_date": today,
            "standard": standard,
            "standard_name": std_name,
            "ai_mode": effective_mode,
            "organization": {
                "name": org_name,
                "industry": industry,
                "size": org_size,
                "employees": employees,
            },
            "compliance": {
                "score": score,
                "max_score": max_score,
                "percentage": percentage,
                "tier": tier,
                "tier_label": tier_label,
                "implemented_count": len(implemented),
                "missing_count": max_score - score,
            },
            "weight_breakdown": {
                "critical": {
                    "total": wb.get("critical", {}).get("total", 0),
                    "implemented": wb.get("critical", {}).get("implemented", 0),
                    "percent": wb_pct("critical"),
                },
                "high": {
                    "total": wb.get("high", {}).get("total", 0),
                    "implemented": wb.get("high", {}).get("implemented", 0),
                    "percent": wb_pct("high"),
                },
                "medium": {
                    "total": wb.get("medium", {}).get("total", 0),
                    "implemented": wb.get("medium", {}).get("implemented", 0),
                    "percent": wb_pct("medium"),
                },
                "low": {
                    "total": wb.get("low", {}).get("total", 0),
                    "implemented": wb.get("low", {}).get("implemented", 0),
                    "percent": wb_pct("low"),
                },
            },
            "risk_summary": {
                "critical_gaps": critical_count,
                "high_gaps": high_count,
                "medium_gaps": medium_count,
                "low_gaps": low_count,
                "total_gaps": critical_count + high_count + medium_count + low_count,
            },
            "top_gaps": top_gaps,
            "implemented_controls": implemented,
        }

    @staticmethod
    def health_check() -> Dict[str, Any]:
        return CloudLLMService.health_check()
