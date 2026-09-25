"""Unit tests for WebSearch upgrades and reference formatting normalization."""

import pytest
from services.web_search import WebSearch
from services.chat_service import ChatService


def test_sanitize_query_strips_vietnamese_conversational_fillers():
    raw_query = "Tin tức an ninh mạng hôm nay có gì mới và hot hit ?"
    cleaned = WebSearch._sanitize_query(raw_query)
    assert "hot hit" not in cleaned.lower()
    assert "hôm nay có gì mới" not in cleaned.lower()
    assert "an ninh mạng" in cleaned.lower()


def test_sanitize_query_preserves_concise_queries():
    raw_query = "ISO 27001 Annex A controls"
    cleaned = WebSearch._sanitize_query(raw_query)
    assert cleaned == "ISO 27001 Annex A controls"


def test_normalize_references_layout_splits_consecutive_citations():
    raw_line = "[1] ISO 27001 - https://tcert.vn [4] Tiêu chuẩn ISO 27001 là gì - https://gglobal.vn"
    normalized = ChatService._normalize_references_layout(raw_line)
    lines = [l.strip() for l in normalized.splitlines() if l.strip()]
    assert len(lines) == 2
    assert lines[0].startswith("- [1]")
    assert lines[1].startswith("- [4]")
    assert "https://tcert.vn" in lines[0]
    assert "https://gglobal.vn" in lines[1]


def test_normalize_references_layout_preserves_standard_markdown():
    text = "Đây là câu trả lời bình thường.\n\n- Gạch đầu dòng 1\n- Gạch đầu dòng 2"
    normalized = ChatService._normalize_references_layout(text)
    assert normalized == text


def test_format_context_numbers_results():
    sample_results = [
        {"title": "Báo An Ninh", "url": "https://baomoi.com", "snippet": "Tóm tắt tin tức an ninh..."},
        {"title": "Bộ Công An", "url": "https://bocongan.gov.vn", "snippet": "Cảnh báo lừa đảo..."}
    ]
    ctx = WebSearch.format_context(sample_results)
    assert "[1] Báo An Ninh" in ctx
    assert "[2] Bộ Công An" in ctx
    assert "https://baomoi.com" in ctx
    assert "https://bocongan.gov.vn" in ctx


def test_strip_trailing_references_removes_duplicate_llm_section():
    raw_response = (
        "Đây là nội dung phân tích an ninh mạng chi tiết [1].\n\n"
        "| Nguồn tham khảo / References\n"
        "[1] Thời Sự - https://thanhnien.vn [4] Trend Micro - https://thanhnien.vn/trend"
    )
    cleaned = ChatService._strip_trailing_references(raw_response)
    assert "Đây là nội dung phân tích an ninh mạng chi tiết [1]." in cleaned
    assert "Nguồn tham khảo" not in cleaned
    assert "thanhnien.vn" not in cleaned


def test_strip_trailing_references_removes_markdown_heading_section():
    raw_response = (
        "Khuyến nghị áp dụng xác thực 2 bước MFA [1].\n\n"
        "## Nguồn tham khảo\n"
        "- [1] Hướng dẫn MFA (https://antoanthongtin.gov.vn)\n"
        "- [2] Cảnh báo lừa đảo (https://bocongan.gov.vn)"
    )
    cleaned = ChatService._strip_trailing_references(raw_response)
    assert cleaned == "Khuyến nghị áp dụng xác thực 2 bước MFA [1]."


def test_wikipedia_fallback_skips_news_query():
    """Wikipedia is an encyclopedia, NOT news. Must return [] for news queries."""
    res = WebSearch._search_wikipedia_fallback("tin tức an ninh mạng hôm nay")
    assert res == []


def test_wikipedia_fallback_filters_irrelevant_namesakes(monkeypatch):
    """Irrelevant results like Nguyễn An Ninh, Quảng Ninh must be filtered out for security queries."""
    fake_data = {
        "query": {
            "search": [
                {"title": "Nguyễn An Ninh", "pageid": 111, "snippet": "Nguyễn An Ninh là một nhà hoạt động cách mạng..."},
                {"title": "Quảng Ninh", "pageid": 222, "snippet": "Quảng Ninh là một tỉnh ven biển..."},
                {"title": "Luật An ninh mạng Việt Nam", "pageid": 333, "snippet": "Luật An ninh mạng quy định về bảo vệ an toàn thông tin..."}
            ]
        }
    }
    class MockResp:
        status_code = 200
        def json(self):
            return fake_data

    class MockClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, *args, **kwargs): return MockResp()

    monkeypatch.setattr("httpx.Client", MockClient)
    res = WebSearch._search_wikipedia_fallback("an ninh mạng")
    assert len(res) == 1
    assert res[0]["title"] == "Wikipedia: Luật An ninh mạng Việt Nam"


def test_chat_stream_respects_explicit_use_search_false(monkeypatch):
    """When use_search=False, web search is never triggered even if message contains news keywords."""
    stream_events = list(ChatService.generate_response_stream(
        message="tin tức an ninh mạng hôm nay?",
        session_id="test_web_search_off",
        use_search=False
    ))
    # Ensure no 'searching' or 'search_done' step
    step_names = [e.get("step") for e in stream_events]
    assert "searching" not in step_names
    assert "search_done" not in step_names

    # Ensure done event has search_used=False, web_sources=[]
    done_ev = next((e for e in stream_events if e.get("step") == "done"), None)
    if done_ev:
        assert done_ev["data"]["search_used"] is False
        assert done_ev["data"]["web_sources"] == []


