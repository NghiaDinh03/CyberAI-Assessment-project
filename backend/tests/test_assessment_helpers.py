"""Unit tests for services.assessment_helpers — Step 7 coverage.

Covers:
- normalize_verdict: verdict coercion, confidence clamp, missing_items coercion, trimming.
- build_evidence_block: optional evidence_summary prepended as a delimited section.
- validate_chunk_output: backward compat + normalized verdict merge.
- summarize_evidence: happy path + exception path (returns "") + max_tokens forwarding.

All external model calls are mocked; no network, no Ollama / Cloud dependency.
"""

import os
import sys
import logging
import pytest

# Ensure backend/ is importable regardless of invocation cwd.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import assessment_helpers as ah
from services.assessment_helpers import (
    EVIDENCE_VERDICTS,
    normalize_verdict,
    build_evidence_block,
    validate_chunk_output,
    summarize_evidence,
)


# ---------------------------------------------------------------------------
# normalize_verdict
# ---------------------------------------------------------------------------
class TestNormalizeVerdict:
    def test_valid_satisfied_unchanged_shape(self):
        out = normalize_verdict({
            "control_id": "A.5.1",
            "evidence_verdict": "satisfied",
            "missing_items": ["doc-review"],
            "confidence": 0.8,
        })
        assert out["control_id"] == "A.5.1"
        assert out["evidence_verdict"] == "satisfied"
        assert out["missing_items"] == ["doc-review"]
        assert out["confidence"] == pytest.approx(0.8)
        # Stable keys match the TypedDict contract.
        assert set(out.keys()) == {
            "control_id", "evidence_verdict", "missing_items", "confidence",
        }

    def test_unknown_verdict_coerced_to_missing(self):
        out = normalize_verdict({
            "control_id": "A.5.2",
            "evidence_verdict": "definitely-yes",
            "confidence": 0.5,
        })
        assert out["evidence_verdict"] == "missing"
        assert out["missing_items"] == []

    def test_empty_verdict_string_coerced_to_missing(self):
        out = normalize_verdict({"control_id": "X", "evidence_verdict": ""})
        assert out["evidence_verdict"] == "missing"

    def test_verdict_case_insensitive(self):
        out = normalize_verdict({"evidence_verdict": "SATISFIED"})
        assert out["evidence_verdict"] == "satisfied"

    def test_confidence_clamped_low(self):
        out = normalize_verdict({"evidence_verdict": "partial", "confidence": -2.5})
        assert out["confidence"] == 0.0

    def test_confidence_clamped_high(self):
        out = normalize_verdict({"evidence_verdict": "partial", "confidence": 9.9})
        assert out["confidence"] == 1.0

    def test_confidence_non_numeric_becomes_zero(self):
        out = normalize_verdict({"evidence_verdict": "partial", "confidence": "n/a"})
        assert out["confidence"] == 0.0

    def test_confidence_none_becomes_zero(self):
        out = normalize_verdict({"evidence_verdict": "partial", "confidence": None})
        assert out["confidence"] == 0.0

    def test_missing_items_none_becomes_empty_list(self):
        out = normalize_verdict({"evidence_verdict": "missing", "missing_items": None})
        assert out["missing_items"] == []

    def test_missing_items_non_list_wrapped(self):
        out = normalize_verdict({"evidence_verdict": "missing", "missing_items": "lone-string"})
        assert out["missing_items"] == ["lone-string"]

    def test_missing_items_strings_trimmed_and_nones_dropped(self):
        out = normalize_verdict({
            "evidence_verdict": "partial",
            "missing_items": ["  foo  ", None, "", "bar"],
        })
        assert out["missing_items"] == ["foo", "bar"]

    def test_control_id_trimmed(self):
        out = normalize_verdict({"control_id": "  A.5.3  ", "evidence_verdict": "satisfied"})
        assert out["control_id"] == "A.5.3"

    def test_non_dict_input_returns_defaults(self):
        out = normalize_verdict(None)  # type: ignore[arg-type]
        assert out["evidence_verdict"] == "missing"
        assert out["missing_items"] == []
        assert out["confidence"] == 0.0
        assert out["control_id"] == ""

    def test_all_verdict_values_pass_through(self):
        for v in EVIDENCE_VERDICTS:
            out = normalize_verdict({"evidence_verdict": v})
            assert out["evidence_verdict"] == v


# ---------------------------------------------------------------------------
# build_evidence_block
# ---------------------------------------------------------------------------
class TestBuildEvidenceBlock:
    def test_empty_inputs_returns_empty_string(self):
        assert build_evidence_block("") == ""
        assert build_evidence_block("", None) == ""
        assert build_evidence_block("", "") == ""

    def test_evidence_only_no_summary_key_substring(self):
        out = build_evidence_block("sample evidence body")
        # Do not snapshot full output — just ensure the raw evidence text is embedded.
        assert "sample evidence body" in out
        assert "EVIDENCE SUMMARY" not in out

    def test_evidence_summary_prepended_with_delimiter(self):
        summary = "• key A\n• key B"
        body = "raw evidence payload here"
        out = build_evidence_block(body, evidence_summary=summary)
        assert "EVIDENCE SUMMARY" in out
        assert "• key A" in out and "• key B" in out
        # Summary must appear before the raw evidence block.
        assert out.index("EVIDENCE SUMMARY") < out.index("raw evidence payload here")

    def test_summary_only_no_raw_evidence(self):
        out = build_evidence_block("", evidence_summary="• solo bullet")
        assert "EVIDENCE SUMMARY" in out
        assert "• solo bullet" in out

    def test_whitespace_only_summary_ignored(self):
        out = build_evidence_block("raw", evidence_summary="   \n\t  ")
        assert "EVIDENCE SUMMARY" not in out
        assert "raw" in out


# ---------------------------------------------------------------------------
# validate_chunk_output
# ---------------------------------------------------------------------------
class TestValidateChunkOutput:
    def test_backward_compat_no_verdict_fields(self):
        content = (
            '[{"id": "A.5.1", "severity": "high", "likelihood": 3, '
            '"impact": 4, "risk": 12, "gap": "missing doc", "recommendation": "write doc"}]'
        )
        out = validate_chunk_output(content, "Cat")
        assert out is not None and len(out) == 1
        item = out[0]
        assert item["id"] == "A.5.1"
        assert item["severity"] == "high"
        # Verdict keys must NOT be injected when absent.
        for k in ("evidence_verdict", "missing_items", "confidence"):
            assert k not in item

    def test_verdict_fields_normalized_and_merged(self):
        content = (
            '[{"id": "A.5.1", "severity": "high", "likelihood": 3, '
            '"impact": 4, "risk": 12, "gap": "g", "recommendation": "r", '
            '"evidence_verdict": "GARBAGE", "missing_items": "single", '
            '"confidence": 2.5}]'
        )
        out = validate_chunk_output(content, "Cat")
        assert out is not None and len(out) == 1
        item = out[0]
        assert item["evidence_verdict"] == "missing"  # unknown → missing
        assert item["missing_items"] == ["single"]    # non-list wrapped
        assert item["confidence"] == 1.0              # clamped to [0,1]
        # control_id defaults to id when absent.
        assert item["control_id"] == "A.5.1"

    def test_empty_list_is_valid(self):
        assert validate_chunk_output("[]", "Cat") == []

    def test_no_json_returns_none(self):
        assert validate_chunk_output("no json here", "Cat") is None


# ---------------------------------------------------------------------------
# summarize_evidence
# ---------------------------------------------------------------------------
class _FakeModelRouter:
    def __init__(self, security_model="sec-lm-tiny"):
        self._security_model = security_model
        self.calls = 0

    def get_security_model(self):
        self.calls += 1
        return self._security_model


def _install_fake_cloud_service(monkeypatch, fn):
    """Install a fake ``services.cloud_llm_service`` module in sys.modules.

    The real module imports ``httpx`` at import time which may not be
    available in minimal test environments. ``summarize_evidence`` does a
    lazy ``from services.cloud_llm_service import CloudLLMService`` inside
    the function body, so we can shadow the whole module before it runs.
    """
    import types
    fake_mod = types.ModuleType("services.cloud_llm_service")

    class _FakeCloudLLMService:
        @staticmethod
        def chat_completion(**kwargs):
            return fn(**kwargs)

    fake_mod.CloudLLMService = _FakeCloudLLMService
    monkeypatch.setitem(sys.modules, "services.cloud_llm_service", fake_mod)
    return fake_mod


class TestSummarizeEvidence:
    def test_empty_text_returns_empty_string(self):
        assert summarize_evidence("") == ""
        assert summarize_evidence("   \n\t ") == ""

    def test_happy_path_returns_content_and_uses_security_model(self, monkeypatch):
        router = _FakeModelRouter(security_model="sec-xyz")
        captured = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return {"content": "- Controls: A.5.1\n- Artifact: policy.pdf"}

        _install_fake_cloud_service(monkeypatch, fake)

        out = summarize_evidence("raw evidence", model_router=router)
        assert "Controls: A.5.1" in out
        assert router.calls == 1
        assert captured.get("local_model") == "sec-xyz"
        assert captured.get("task_type") == "iso_local"
        assert captured.get("prefer_cloud") is False

    def test_max_tokens_forwarded(self, monkeypatch):
        router = _FakeModelRouter()
        captured = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return {"content": "ok"}

        _install_fake_cloud_service(monkeypatch, fake)
        summarize_evidence("raw", max_tokens=64, model_router=router)
        assert captured.get("max_tokens") == 64

    def test_max_tokens_floor_32(self, monkeypatch):
        router = _FakeModelRouter()
        captured = {}

        def fake(**kwargs):
            captured.update(kwargs)
            return {"content": "ok"}

        _install_fake_cloud_service(monkeypatch, fake)
        summarize_evidence("raw", max_tokens=1, model_router=router)
        assert captured.get("max_tokens") == 32

    def test_failure_returns_empty_and_logs_warning(self, monkeypatch, caplog):
        router = _FakeModelRouter()

        def boom(**kwargs):
            raise RuntimeError("upstream down")

        _install_fake_cloud_service(monkeypatch, boom)

        with caplog.at_level(logging.WARNING, logger=ah.logger.name):
            out = summarize_evidence("raw evidence", model_router=router)

        assert out == ""
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("summarize_evidence" in r.getMessage() for r in warnings)

    def test_empty_content_field_returns_empty_string(self, monkeypatch):
        router = _FakeModelRouter()
        _install_fake_cloud_service(monkeypatch, lambda **kw: {"content": ""})
        assert summarize_evidence("raw", model_router=router) == ""
