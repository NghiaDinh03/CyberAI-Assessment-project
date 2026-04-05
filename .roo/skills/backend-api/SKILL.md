---
name: backend-api-orchestrator
description: Keep the chatbot backend clean and scalable with thin API handlers, explicit validation, stable response contracts, and orchestration logic separated from LocalAI provider details.
---

Use this skill for routes, controllers, schemas, API services, auth flow, request normalization, and chat orchestration.

Pattern to follow:
- Thin route/controller
- Validation near input boundary
- Service layer for orchestration
- Provider integration hidden behind model service
- Stable response contract for frontend

Rules:
- Do not hardcode model-specific logic in routes.
- Normalize chat request and response shapes.
- Keep streaming and blocking paths explicit.
- Make backend errors predictable for the UI.
- Keep controller code small and readable.
- No verbose comments.

Primary outcomes:
- New endpoints are easy to add.
- Frontend integration stays stable.
- Debugging backend issues does not require opening model-provider code unless necessary.