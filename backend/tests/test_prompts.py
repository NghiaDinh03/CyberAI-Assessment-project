"""Tests for the prompt registry & override store."""
import json
import os
from pathlib import Path

import pytest

from prompts import defaults
from prompts.store import PromptStore


@pytest.fixture
def store(tmp_path: Path) -> PromptStore:
    return PromptStore(path=tmp_path / "prompts_overrides.json")


def test_defaults_are_returned_when_no_overrides(store: PromptStore):
    for key, meta in defaults.REGISTRY.items():
        assert store.get(key) == meta["default"], f"Default mismatch for {key}"


def test_two_groups_chat_and_assessment_only():
    groups = {meta["group"] for meta in defaults.REGISTRY.values()}
    assert groups == {"chat", "assessment"}


def test_set_and_get_override(store: PromptStore):
    new_text = "Bạn là trợ lý mới."
    store.set("chat.local_default", new_text)
    assert store.get("chat.local_default") == new_text
    # Other prompts unaffected
    assert store.get("chat.general") == defaults.REGISTRY["chat.general"]["default"]


def test_set_rejects_unknown_key(store: PromptStore):
    with pytest.raises(KeyError):
        store.set("nope.unknown", "x")


def test_set_rejects_too_long(store: PromptStore):
    with pytest.raises(ValueError):
        store.set("chat.local_default", "x" * 25_000)


def test_set_requires_placeholders(store: PromptStore):
    # report_system requires {std_name},{pct},{sc},{mx}
    with pytest.raises(ValueError, match="placeholder"):
        store.set("assessment.report_system", "no placeholders here")


def test_reset_removes_override(store: PromptStore):
    store.set("chat.general", "Override text")
    res = store.reset("chat.general")
    assert res["was_overridden"] is True
    assert store.get("chat.general") == defaults.REGISTRY["chat.general"]["default"]


def test_list_marks_overridden(store: PromptStore):
    store.set("chat.rag", defaults.REGISTRY["chat.rag"]["default"] + "\nEXTRA")
    listed = {item["key"]: item for item in store.list()}
    assert listed["chat.rag"]["is_overridden"] is True
    assert listed["chat.general"]["is_overridden"] is False


def test_chat_and_assessment_prompts_are_independent(store: PromptStore):
    store.set("assessment.report_system",
              "Bạn là chuyên gia {std_name}. {pct}% ({sc}/{mx}) — custom.")
    # chat prompts must remain default
    for key in [k for k, m in defaults.REGISTRY.items() if m["group"] == "chat"]:
        assert store.get(key) == defaults.REGISTRY[key]["default"], (
            f"Chat prompt {key} leaked through assessment override"
        )


def test_chunk_template_and_report_system_format_correctly():
    """Defaults must be valid format strings with documented placeholders."""
    chunk = defaults.ASSESSMENT_CHUNK_TEMPLATE.format_map({
        "std_name": "ISO 27001:2022",
        "cat_name": "A.5",
        "pct": 50,
        "sc": 5,
        "mx": 10,
        "sys_summary": "x",
        "rag_section": "",
        "present_str": "A.5.1",
        "missing_str": "A.5.2",
        "few_shot": "EX",
    })
    assert "A.5" in chunk and "A.5.1" in chunk

    report = defaults.ASSESSMENT_REPORT_SYSTEM.format_map({
        "std_name": "ISO 27001:2022", "pct": 50, "sc": 5, "mx": 10,
    })
    assert "ISO 27001:2022" in report and "50%" in report
