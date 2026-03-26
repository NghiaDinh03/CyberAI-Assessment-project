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
        """
        Đánh giá hệ thống với 3 chế độ model:
          - "hybrid"  (mặc định): Phase1=SecurityLM(LocalAI) + Phase2=OpenClaude (RAG)
          - "local"  : Cả hai Phase dùng LocalAI — bảo mật tối đa, dữ liệu không rời server
          - "cloud"  : Cả hai Phase dùng OpenClaude — chất lượng cao nhất
        model_mode có thể được truyền qua system_data["model_mode"] hoặc tham số trực tiếp.
        """
        # Ưu tiên giá trị trực tiếp; fallback sang system_data nếu có
        effective_mode = model_mode or system_data.get("model_mode", "hybrid")

        vs = ChatService.get_vector_store()

        standard = system_data.get("assessment_standard", "iso27001")
        search_query = "A.5 Tổ chức, A.6 Nhân sự, A.7 Vật lý, A.8 Công nghệ"
        if standard == "tcvn11930":
            search_query = "TCVN 11930 hệ thống thông tin cấp độ bảo đảm an toàn"
        elif standard == "nd13":
            search_query = "Nghị định 13 bảo vệ dữ liệu cá nhân"

        # Try to load custom standard for dynamic metadata
        custom_std = None
        try:
            from services.standard_service import load_standard, WEIGHT_SCORE as WS
            custom_std = load_standard(standard)
        except Exception:
            pass

        if custom_std:
            # Custom standard — dynamic search query and scoring
            std_name = custom_std.get("name", standard)
            search_query = f"{std_name} compliance security controls"
            all_ctrls = []
            for cat in custom_std.get("controls", []):
                all_ctrls.extend(cat.get("controls", []))
                # Add category names to search query for better RAG retrieval
                search_query += f", {cat.get('category', '')}"
        else:
            std_name = "ISO 27001:2022" if standard != "tcvn11930" else "TCVN 11930:2017 (Yêu cầu kỹ thuật theo 5 cấp độ)"

        context_results = vs.search(search_query, top_k=6)
        context = "\n---\n".join([r["text"] for r in context_results])

        implemented = system_data.get("compliance", {}).get("implemented_controls", [])
        score = len(implemented)
        max_score = 93
        percentage = 0

        if custom_std:
            max_score = len(all_ctrls) if all_ctrls else 1
            # Use weighted scoring for custom standards
            weight_map = {c["id"]: WS.get(c.get("weight", "medium"), 1) for c in all_ctrls}
            max_weighted = sum(weight_map.values())
            achieved_weighted = sum(weight_map.get(cid, 0) for cid in implemented)
            percentage = round((achieved_weighted / max_weighted) * 100, 1) if max_weighted > 0 else 0
        elif standard == "tcvn11930":
            max_score = 34
            percentage = round((score / max_score) * 100, 1)
        else:
            percentage = round((score / max_score) * 100, 1)

        # ── Build weight breakdown for AI prompt ────────────────────────
        weight_labels = {"critical": "Tối quan trọng", "high": "Quan trọng", "medium": "Trung bình", "low": "Thấp"}
        weight_scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        # Collect all controls with weights for breakdown
        all_controls_flat = []
        if custom_std:
            for cat in custom_std.get("controls", []):
                for ctrl in cat.get("controls", []):
                    all_controls_flat.append(ctrl)
        else:
            # Built-in standards — build from implemented list & known totals
            # We don't have weight data server-side for built-in, so use simple breakdown
            pass

        # Calculate weight breakdown
        weight_breakdown = {"critical": {"total": 0, "implemented": 0}, "high": {"total": 0, "implemented": 0},
                           "medium": {"total": 0, "implemented": 0}, "low": {"total": 0, "implemented": 0}}
        missing_controls_by_weight = {"critical": [], "high": [], "medium": [], "low": []}

        if all_controls_flat:
            for ctrl in all_controls_flat:
                w = ctrl.get("weight", "medium")
                weight_breakdown[w]["total"] += 1
                if ctrl["id"] in implemented:
                    weight_breakdown[w]["implemented"] += 1
                else:
                    missing_controls_by_weight[w].append(f"{ctrl['id']} ({ctrl.get('label', '')})")

        weight_breakdown_txt = ""
        if all_controls_flat:
            weight_breakdown_txt = "\n\nPHÂN BỔ TRỌNG SỐ CONTROLS:\n"
            for w in ["critical", "high", "medium", "low"]:
                bd = weight_breakdown[w]
                if bd["total"] > 0:
                    pct = round((bd["implemented"] / bd["total"]) * 100, 1)
                    weight_breakdown_txt += (
                        f"- {weight_labels[w]} ({weight_scores[w]} điểm): "
                        f"{bd['implemented']}/{bd['total']} đạt ({pct}%)\n"
                    )

            # List missing critical & high controls for AI focus
            critical_missing = missing_controls_by_weight["critical"]
            high_missing = missing_controls_by_weight["high"]
            if critical_missing:
                weight_breakdown_txt += f"\n⚠️ CONTROLS TỐI QUAN TRỌNG CHƯA ĐẠT ({len(critical_missing)}):\n"
                for m in critical_missing[:15]:
                    weight_breakdown_txt += f"  🔴 {m}\n"
            if high_missing:
                weight_breakdown_txt += f"\n⚠️ CONTROLS QUAN TRỌNG CHƯA ĐẠT ({len(high_missing)}):\n"
                for m in high_missing[:15]:
                    weight_breakdown_txt += f"  🟠 {m}\n"

        system_info_txt = f"Tiêu chuẩn đánh giá: {std_name}\n"
        system_info_txt += f"Mức độ tuân thủ: {score}/{max_score} Controls đạt yêu cầu ({percentage}%).\n"
        system_info_txt += f"Các Controls đã đạt: {', '.join(implemented)}\n"
        system_info_txt += weight_breakdown_txt
        system_info_txt += "\nCHI TIẾT HẠ TẦNG HỆ THỐNG:\n"

        for key, value in system_data.items():
            if key in ["compliance", "assessment_standard", "implemented_controls", "model_mode"]:
                continue
            if isinstance(value, dict):
                for k, v in value.items():
                    system_info_txt += f"- {k}: {v}\n"
            elif isinstance(value, list):
                system_info_txt += f"- {key}: {', '.join(str(v) for v in value)}\n"
            else:
                system_info_txt += f"- {key}: {value}\n"

        # ── Health check LocalAI trước khi dùng local mode ─────────────────
        # Nếu model fail load (OOM/RPC), tự động chuyển sang hybrid (Phase2=cloud) hoặc cloud
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

        # ── Phase 1: Chunked per-category analysis for LocalAI ─────────────

        def _build_category_chunk_prompt(cat_name: str, cat_controls: list, impl: list,
                                          pct: float, sc: int, mx: int,
                                          sys_summary: str, rag_ctx: str = "") -> str:
            missing = [c for c in cat_controls if c["id"] not in impl]
            present = [c for c in cat_controls if c["id"] in impl]
            missing_str = "\n".join(
                f"  ❌ {c['id']} [{c.get('weight','medium').upper()}] {c.get('label','')}"
                for c in missing[:20]
            )
            present_str = ", ".join(c["id"] for c in present[:15])
            rag_section = f"\nTÀI LIỆU THAM CHIẾU {std_name}:\n{rag_ctx[:600]}\n" if rag_ctx else ""
            return (
                f"Auditor {std_name} — Category: {cat_name}\n"
                f"Tuân thủ tổng: {pct}% ({sc}/{mx})\n"
                f"{rag_section}\n"
                f"CONTROLS ĐÃ ĐẠT: {present_str or 'Không có'}\n"
                f"CONTROLS CHƯA ĐẠT:\n{missing_str or 'Tất cả đã đạt'}\n\n"
                f"THÔNG TIN HỆ THỐNG:\n{sys_summary[:700]}\n\n"
                f"NHIỆM VỤ: Với mỗi control CHƯA ĐẠT trong nhóm '{cat_name}', "
                f"trả về JSON array (chỉ JSON, không text thêm):\n"
                f'[{{"id":"CTL.XX","severity":"critical|high|medium|low",'
                f'"likelihood":1-5,"impact":1-5,"risk":1-25,'
                f'"gap":"mô tả GAP ngắn","recommendation":"1 câu khuyến nghị"}}]\n'
                f"Nếu tất cả đã đạt, trả về: []"
            )

        def _validate_chunk_output(content: str, cat_name: str) -> list:
            """Parse and validate JSON output from SecurityLM chunk."""
            import json, re as _re
            content = content.strip()
            # Extract JSON array — handle model wrapping in ```json ... ```
            match = _re.search(r'\[.*?\]', content, _re.DOTALL)
            if not match:
                return None  # invalid, needs retry
            try:
                data = json.loads(match.group())
                if not isinstance(data, list):
                    return None
                validated = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    ctrl_id = item.get("id", "")
                    if not ctrl_id:
                        continue
                    validated.append({
                        "id": ctrl_id,
                        "category": cat_name,
                        "severity": item.get("severity", "medium"),
                        "likelihood": max(1, min(5, int(item.get("likelihood", 3)))),
                        "impact": max(1, min(5, int(item.get("impact", 3)))),
                        "risk": max(1, min(25, int(item.get("risk", 9)))),
                        "gap": str(item.get("gap", ""))[:200],
                        "recommendation": str(item.get("recommendation", ""))[:200],
                    })
                return validated
            except Exception:
                return None

        def _chunk_results_to_markdown(all_gap_items: list) -> str:
            """Convert structured JSON gap items to markdown for Phase 2."""
            if not all_gap_items:
                return "✅ Không phát hiện GAP đáng kể nào.\n"
            sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_items = sorted(all_gap_items, key=lambda x: (sev_order.get(x["severity"], 2), -x["risk"]))
            lines = [
                "## RISK REGISTER\n",
                "| # | Control | Category | GAP | Severity | L | I | Risk | Khuyến nghị |",
                "|---|---------|----------|-----|----------|---|---|------|-------------|",
            ]
            sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
            for i, item in enumerate(sorted_items, 1):
                sev = item["severity"]
                lines.append(
                    f"| {i} | {item['id']} | {item['category'][:20]} | {item['gap'][:60]} "
                    f"| {sev_emoji.get(sev,'')} {sev} | {item['likelihood']} | {item['impact']} "
                    f"| {item['risk']} | {item['recommendation'][:60]} |"
                )
            counts = {s: sum(1 for x in all_gap_items if x["severity"] == s) for s in sev_order}
            lines.append(f"\n## TÓM TẮT: 🔴 Critical={counts['critical']} 🟠 High={counts['high']} "
                         f"🟡 Medium={counts['medium']} ⚪ Low={counts['low']}")
            return "\n".join(lines)

        def _build_single_full_prompt(pct: float, sc: int, mx: int, sys_info: str, ctx: str) -> tuple:
            sp = (
                f"Bạn là chuyên gia Auditor về {std_name}. Tuân thủ: {pct}% ({sc}/{mx} Controls).\n\n"
                f"NHIỆM VỤ:\n"
                f"1. Phân loại GAP theo rủi ro: 🔴 Critical, 🟠 High, 🟡 Medium, ⚪ Low\n"
                f"2. Đánh giá Likelihood + Impact cho mỗi GAP\n"
                f"3. Risk Score = L × I; sắp xếp giảm dần\n"
                f"4. RISK REGISTER dạng bảng: Control | GAP | Severity | L | I | Risk | Khuyến nghị\n\n"
                f"## DANH SÁCH PHÁT HIỆN\n[GAP với severity]\n\n"
                f"## RISK REGISTER\n"
                f"| Control | GAP | Severity | L | I | Risk | Khuyến nghị |\n"
                f"|---------|-----|----------|---|---|------|-------------|\n[data]\n\n"
                f"## TÓM TẮT RỦI RO\n[Tổng: Critical/High/Medium/Low]"
            )
            um = f"Tài liệu {std_name}:\n{ctx}\n\nBiên bản khảo sát:\n{sys_info}"
            return sp, um

        # Build concise system summary for chunks (avoid repeating 3000 chars 4 times)
        sys_summary_short = (
            f"Tổ chức: {system_data.get('organization', {}).get('name', '')} | "
            f"Ngành: {system_data.get('organization', {}).get('industry', '')} | "
            f"Nhân sự: {system_data.get('organization', {}).get('employees', 0)} | "
            f"IT: {system_data.get('organization', {}).get('it_staff', 0)}\n"
            f"Firewall: {system_data.get('infrastructure', {}).get('firewalls', '')[:80]}\n"
            f"AV/EDR: {system_data.get('infrastructure', {}).get('antivirus', '')[:60]}\n"
            f"SIEM: {system_data.get('infrastructure', {}).get('siem', '')[:60]}\n"
            f"Cloud: {system_data.get('infrastructure', {}).get('cloud', '')[:60]}\n"
            f"Backup: {system_data.get('infrastructure', {}).get('backup', '')[:60]}\n"
            f"VPN: {system_data.get('infrastructure', {}).get('vpn', '')}\n"
            f"Sự cố 12T: {system_data.get('compliance', {}).get('incidents_12m', 0)}\n"
            f"Ghi chú: {(system_data.get('notes') or '')[:300]}"
        )

        try:
            raw_analysis = ""
            result_p1 = None

            if p1_task_type == "iso_local" and all_controls_flat:
                # ── Chunked mode: SecurityLM per-category, JSON output, RAG, retry, validate ─
                std_categories = (custom_std.get("controls", []) if custom_std else [])
                if not std_categories:
                    std_categories = [{"category": "Tất cả Controls", "controls": all_controls_flat}]

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

                    chunk_prompt = _build_category_chunk_prompt(
                        cat_name, cat_controls, implemented,
                        percentage, score, max_score,
                        sys_summary_short, cat_rag_ctx
                    )
                    chunk_messages = [{"role": "user", "content": chunk_prompt}]

                    # Retry × 2 with validation
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
                            chunk_gap_items = _validate_chunk_output(chunk_content, cat_name)
                            if chunk_gap_items is not None:
                                logger.info(f"[Assessment] Chunk '{cat_name}' OK attempt {attempt+1}: {len(chunk_gap_items)} gaps")
                                break
                            logger.warning(f"[Assessment] Chunk '{cat_name}' invalid JSON attempt {attempt+1}, retrying")
                        except Exception as chunk_err:
                            logger.warning(f"[Assessment] Chunk '{cat_name}' error attempt {attempt+1}: {chunk_err}")
                            if attempt == 2:
                                logger.error(f"[Assessment] Chunk '{cat_name}' failed all attempts")

                    if chunk_gap_items:
                        all_gap_items.extend(chunk_gap_items)

                raw_analysis = _chunk_results_to_markdown(all_gap_items)
                logger.info(f"[Assessment] All chunks complete — {len(all_gap_items)} total gaps, raw: {len(raw_analysis)} chars")

            else:
                # ── Single full prompt mode: Cloud or no controls flat list ─
                security_prompt, user_msg = _build_single_full_prompt(
                    percentage, score, max_score, system_info_txt, context
                )
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

            # Phase 2: Compress raw_analysis if too large for Llama 8B context window
            MAX_P2_INPUT = 2500  # chars — Llama 8B safe limit ~3000 tokens
            if len(raw_analysis) > MAX_P2_INPUT:
                # Keep Risk Register table rows + summary, drop verbose narrative
                import re as _re2
                lines = raw_analysis.split("\n")
                table_lines = [l for l in lines if l.startswith("|") or l.startswith("##") or "Critical" in l or "High" in l or "TÓM TẮT" in l]
                compressed = "\n".join(table_lines)
                if len(compressed) < 200:
                    compressed = raw_analysis[:MAX_P2_INPUT] + "\n...[truncated for context window]"
                raw_analysis_p2 = compressed[:MAX_P2_INPUT]
                logger.info(f"[Assessment] P2 input compressed: {len(raw_analysis)} → {len(raw_analysis_p2)} chars")
            else:
                raw_analysis_p2 = raw_analysis

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
