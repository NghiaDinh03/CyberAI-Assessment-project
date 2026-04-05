---
name: model-localai-runtime
description: Manage LocalAI-based model execution through centralized configuration, provider isolation, explicit fallback behavior, and safe support for multiple local models such as Gemma-family models when compatibility is verified.
---

Use this skill for LocalAI integration, model configuration, model switching, fallback strategy, streaming logic, retry policy, and inference debugging.

LocalAI assumptions:
- LocalAI is the serving layer.
- The app may use OpenAI-compatible request formats.
- Model capabilities depend on backend compatibility and model config.

Rules:
- Keep model URLs, names, and options centralized.
- Separate prompt formatting from provider transport logic.
- Separate provider transport logic from response parsing.
- Keep timeout, retry, and fallback behavior explicit.
- Support one default model and optional fallback model.
- Allow Gemma-family integration only if support is verified in the current stack.
- Do not fake model support.
- No verbose comments.

Primary outcomes:
- Switching or adding models becomes low-risk.
- Model debugging stays local to the provider layer.
- Claude does not waste context touching unrelated backend or UI files.