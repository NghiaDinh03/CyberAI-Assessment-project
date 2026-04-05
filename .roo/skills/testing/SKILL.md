---
name: testing
description: Guide test creation, structure, and coverage for the CyberAI platform's Python backend and Next.js frontend.
---

Use this skill for writing tests, configuring test frameworks, mocking strategies, coverage targets, and CI test validation.

Primary intent:
- Ensure reliable test coverage across backend services, routes, and frontend components.
- Standardize test patterns so tests are fast, deterministic, and maintainable.

Reference direction:
- Backend test directory: `backend/tests/`
- Existing tests: `backend/tests/test_chat_service.py`, `backend/tests/test_iso27001_routes.py`, `backend/tests/test_rag_service.py`
- Backend services under test: `backend/services/`
- Backend routes under test: `backend/api/routes/`
- Frontend source: `frontend-next/src/`
- CI pipeline: `.github/workflows/ci.yml`

## Backend testing (Python)

Framework: pytest + pytest-asyncio + httpx (for async FastAPI testing).

Test location: `backend/tests/`

Patterns:
- Use `TestClient` from httpx for API route tests, direct function calls for service tests.
- Async tests: use `@pytest.mark.asyncio` decorator.
- Fixtures: create `conftest.py` with shared fixtures (`mock_vector_store`, `mock_session_store`, `mock_cloud_service`).

Mocking strategies:
- Mock external services: LocalAI (httpx responses), Ollama (httpx responses), Cloud API (httpx responses).
- Mock ChromaDB: in-memory client for vector store tests.
- Mock file system: use `tmp_path` fixture for session/assessment file tests.
- Mock DuckDuckGo: patch `duckduckgo_search.DDGS`.
- Never make real HTTP calls in unit tests.

Test structure:
- Unit tests: `tests/test_{service_name}.py` — one file per service.
- Route tests: `tests/test_{route_name}_routes.py` — one file per route module.
- Integration tests: `tests/integration/` — test service interactions.

Coverage targets:
- Services: 80%+ (critical path: `chat_service`, `cloud_llm_service`, `assessment_helpers`).
- Routes: 70%+ (all endpoints should have at least happy-path tests).
- Overall: 75%+.

Run command: `cd backend && pytest tests/ -v --tb=short`

## Frontend testing (Next.js)

Currently no test framework configured.

Recommended stack: Jest + React Testing Library.

Setup:
- Install: `npm install -D jest @testing-library/react @testing-library/jest-dom jest-environment-jsdom`.
- Config: `jest.config.js` with `nextJest()` from `next/jest`.
- Test location: `frontend-next/src/__tests__/` or colocated `ComponentName.test.js`.

Test pattern:
- Component unit tests: render, assert DOM output, simulate user events.
- API integration mocks: mock `fetch` for `/api/` calls.
- Theme tests: verify dark/light mode toggle via ThemeProvider.

## Rules

- Every new endpoint must have at least one test.
- Mock all external HTTP calls (never hit real LocalAI/Ollama/Cloud in tests).
- Use descriptive test names: `test_chat_returns_rag_context_when_security_intent`.
- Test error paths: invalid input, service unavailable, rate limited.
- CI runs: `pytest tests/ -v --tb=short` (must pass for merge).
- Do not skip tests without a tracking issue.
- Keep test files focused — one test file per service or route module.

Code quality policy:
- No verbose comments in test files.
- No banner decorations.
- Only comment non-obvious test setup or mock rationale.
