---
name: overall-workspace
description: Maintain a consistent full-stack workspace for the chatbot project by enforcing clear boundaries between frontend, backend, model, security, and CI/CD, with minimal file churn and production-safe incremental changes.
---

Use this skill when a task spans multiple layers or risks causing project-wide inconsistency.

Core intent:
- Keep the project easy to extend.
- Keep Claude focused on the smallest correct set of files.
- Prevent overlapping logic across frontend, backend, and model layers.

Required structure:
- Frontend owns rendering, user interaction, local view state, and UX polish.
- Backend owns validation, API contracts, auth, orchestration, and safe error handling.
- Model layer owns LocalAI provider logic, model config, timeout/retry/fallback, and response parsing.
- Security owns trust boundaries, secrets, auth hardening, logging hygiene, and safety checks.
- CI/CD owns lint, test, build, and release validation.

Rules:
- Make the smallest useful change.
- Do not move files unless there is a structural reason.
- Do not create a new abstraction without removing real duplication or coupling.
- Prefer extension over rewrite.
- Keep code self-explanatory.
- No verbose comments.
- Only comment non-obvious tradeoffs or edge-case constraints.

Primary outcomes:
- New features are easy to add.
- Failures are easier to localize.
- Claude uses less context because each task stays in the right layer.