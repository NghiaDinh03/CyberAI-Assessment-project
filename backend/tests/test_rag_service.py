"""Unit tests for services.rag_service — confidence threshold filtering.

Tests cover:
- RAG_CONFIDENCE_THRESHOLD constant value (Phase 3 requirement: 0.35)
- _filter_by_confidence() internal logic
- retrieve_context() and retrieve_with_sources() public API behaviour
- RAG_QUERIES Prometheus counter increments (hit/miss labels)

All external dependencies (VectorStore, CloudLLMService, Prometheus counters)
are fully mocked so tests run without Docker, ChromaDB, or network access.
"""

import pytest
from unittest.mock import MagicMock, patch, call


# ── Module-level import (avoids partial import issues) ────────────────────────
import services.rag_service as rag_module
from services.rag_service import RAGService, RAG_CONFIDENCE_THRESHOLD, _filter_by_confidence


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_doc(score: float, text: str = "sample text", file: str = "test.md") -> dict:
    """Helper: build a mock ChromaDB result dict."""
    return {"score": score, "text": text, "file": file, "doc_title": "Test Doc", "source": file}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Threshold constant
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGConfidenceThresholdConstant:
    def test_threshold_value_is_0_35(self):
        """Phase 3 requirement: confidence threshold must be exactly 0.35."""
        assert RAG_CONFIDENCE_THRESHOLD == 0.35

    def test_threshold_is_float(self):
        """Threshold must be a float (not int) for comparison with float scores."""
        assert isinstance(RAG_CONFIDENCE_THRESHOLD, float)

    def test_threshold_is_positive(self):
        assert RAG_CONFIDENCE_THRESHOLD > 0.0

    def test_threshold_is_below_one(self):
        assert RAG_CONFIDENCE_THRESHOLD < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. _filter_by_confidence() unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFilterByConfidence:
    def test_empty_list_returns_empty(self):
        assert _filter_by_confidence([]) == []

    def test_all_above_threshold_pass(self):
        docs = [_make_doc(0.5), _make_doc(0.8), _make_doc(1.0)]
        result = _filter_by_confidence(docs)
        assert len(result) == 3

    def test_all_below_threshold_filtered_out(self):
        docs = [_make_doc(0.1), _make_doc(0.2), _make_doc(0.34)]
        result = _filter_by_confidence(docs)
        assert result == []

    def test_exact_threshold_passes(self):
        """A score equal to the threshold must NOT be filtered out (>=, not >)."""
        docs = [_make_doc(0.35)]
        result = _filter_by_confidence(docs)
        assert len(result) == 1

    def test_just_below_threshold_filtered(self):
        """A score just below 0.35 must be filtered out."""
        docs = [_make_doc(0.3499)]
        result = _filter_by_confidence(docs)
        assert result == []

    def test_mixed_results_partial_filter(self):
        """Only chunks with score >= 0.35 survive."""
        docs = [
            _make_doc(0.10, text="low1"),
            _make_doc(0.35, text="borderline"),
            _make_doc(0.50, text="good1"),
            _make_doc(0.20, text="low2"),
            _make_doc(0.90, text="excellent"),
        ]
        result = _filter_by_confidence(docs)
        texts = [d["text"] for d in result]
        assert "borderline" in texts
        assert "good1" in texts
        assert "excellent" in texts
        assert "low1" not in texts
        assert "low2" not in texts

    def test_missing_score_key_treated_as_zero(self):
        """Docs without a 'score' key default to 0 and are filtered out."""
        docs = [{"text": "no score", "file": "x.md"}]
        result = _filter_by_confidence(docs)
        assert result == []

    def test_preserves_all_doc_fields(self):
        """Surviving docs must be the original dict objects, not copies."""
        doc = _make_doc(0.9, text="keep me")
        result = _filter_by_confidence([doc])
        assert result[0] is doc


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Prometheus RAG_QUERIES counter integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGQueriesCounter:
    def test_hit_label_incremented_when_results_pass(self):
        """When at least one chunk passes the threshold, 'hit' counter increments."""
        mock_counter = MagicMock()
        mock_labels = MagicMock()
        mock_counter.labels.return_value = mock_labels

        with patch.dict("sys.modules", {"api.routes.metrics": MagicMock(RAG_QUERIES=mock_counter)}):
            docs = [_make_doc(0.9)]
            _filter_by_confidence(docs)

        mock_counter.labels.assert_called_once_with(result="hit")
        mock_labels.inc.assert_called_once()

    def test_miss_label_incremented_when_all_filtered(self):
        """When all chunks are below threshold, 'miss' counter increments."""
        mock_counter = MagicMock()
        mock_labels = MagicMock()
        mock_counter.labels.return_value = mock_labels

        with patch.dict("sys.modules", {"api.routes.metrics": MagicMock(RAG_QUERIES=mock_counter)}):
            docs = [_make_doc(0.1), _make_doc(0.2)]
            _filter_by_confidence(docs)

        mock_counter.labels.assert_called_once_with(result="miss")
        mock_labels.inc.assert_called_once()

    def test_miss_label_incremented_for_empty_input(self):
        """Empty results list → 'miss' (no confident results)."""
        mock_counter = MagicMock()
        mock_labels = MagicMock()
        mock_counter.labels.return_value = mock_labels

        with patch.dict("sys.modules", {"api.routes.metrics": MagicMock(RAG_QUERIES=mock_counter)}):
            _filter_by_confidence([])

        mock_counter.labels.assert_called_once_with(result="miss")

    def test_counter_import_failure_does_not_raise(self):
        """If prometheus_client is unavailable, _filter_by_confidence must not crash."""
        with patch.dict("sys.modules", {"api.routes.metrics": None}):
            # Should silently swallow the import error
            result = _filter_by_confidence([_make_doc(0.9)])
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RAGService.retrieve_context()
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGServiceRetrieveContext:
    @patch("services.rag_service.VectorStore")
    def test_returns_empty_string_when_no_results(self, MockVS):
        MockVS.return_value.multi_query_search.return_value = []
        svc = RAGService()
        assert svc.retrieve_context("anything") == ""

    @patch("services.rag_service.VectorStore")
    def test_returns_empty_string_when_all_below_threshold(self, MockVS):
        MockVS.return_value.multi_query_search.return_value = [
            _make_doc(0.1, "low confidence text")
        ]
        svc = RAGService()
        assert svc.retrieve_context("anything") == ""

    @patch("services.rag_service.VectorStore")
    def test_returns_joined_text_for_confident_results(self, MockVS):
        MockVS.return_value.multi_query_search.return_value = [
            _make_doc(0.8, "first chunk"),
            _make_doc(0.9, "second chunk"),
        ]
        svc = RAGService()
        result = svc.retrieve_context("ISO 27001 access control")
        assert "first chunk" in result
        assert "second chunk" in result

    @patch("services.rag_service.VectorStore")
    def test_filters_mixed_results(self, MockVS):
        MockVS.return_value.multi_query_search.return_value = [
            _make_doc(0.9, "keep this"),
            _make_doc(0.1, "drop this"),
        ]
        svc = RAGService()
        result = svc.retrieve_context("query")
        assert "keep this" in result
        assert "drop this" not in result


# ═══════════════════════════════════════════════════════════════════════════════
# 5. RAGService.retrieve_with_sources()
# ═══════════════════════════════════════════════════════════════════════════════

class TestRAGServiceRetrieveWithSources:
    @patch("services.rag_service.VectorStore")
    def test_empty_results_return_empty_context_and_sources(self, MockVS):
        MockVS.return_value.multi_query_search.return_value = []
        svc = RAGService()
        result = svc.retrieve_with_sources("query")
        assert result["context"] == ""
        assert result["sources"] == []

    @patch("services.rag_service.VectorStore")
    def test_all_low_confidence_returns_empty(self, MockVS):
        MockVS.return_value.multi_query_search.return_value = [
            _make_doc(0.05, "irrelevant")
        ]
        svc = RAGService()
        result = svc.retrieve_with_sources("query")
        assert result["context"] == ""
        assert result["sources"] == []

    @patch("services.rag_service.VectorStore")
    def test_confident_results_have_sources(self, MockVS):
        MockVS.return_value.multi_query_search.return_value = [
            _make_doc(0.75, "relevant text", file="iso27001_annex_a.md"),
        ]
        svc = RAGService()
        result = svc.retrieve_with_sources("access control")
        assert result["context"] != ""
        assert len(result["sources"]) == 1
        assert result["sources"][0]["file"] == "iso27001_annex_a.md"

    @patch("services.rag_service.VectorStore")
    def test_duplicate_sources_deduplicated(self, MockVS):
        """Multiple chunks from the same file should produce only one source entry."""
        MockVS.return_value.multi_query_search.return_value = [
            _make_doc(0.8, "chunk 1", file="same_file.md"),
            _make_doc(0.9, "chunk 2", file="same_file.md"),
        ]
        svc = RAGService()
        result = svc.retrieve_with_sources("query")
        assert len(result["sources"]) == 1
