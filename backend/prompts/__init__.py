"""System prompt registry — separates Chat AI prompts from Assessment prompts.

Provides defaults plus a JSON-backed override store so admins can edit prompts
from the Settings UI without redeploy. Each consumer (chat_service,
assessment_helpers) calls :func:`get_prompt` with a stable key.
"""
from .store import PromptStore, get_prompt, list_prompts, set_prompt, reset_prompt
from . import defaults

__all__ = [
    "PromptStore",
    "defaults",
    "get_prompt",
    "list_prompts",
    "set_prompt",
    "reset_prompt",
]
