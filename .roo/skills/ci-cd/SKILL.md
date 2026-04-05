---
name: ci-cd
description: Keep the chatbot project safe to change by automating lint, type-check, tests, build validation, Docker checks, and deployment gates with simple, fast, low-noise workflows.
---

Use this skill for GitHub Actions, pipeline automation, test/build validation, release checks, container validation, and deployment safety.

Primary intent:
- Catch breakages before merge via automated CI on every push/PR to main and develop.
- Keep workflows simple enough to debug quickly with isolated job stages.

Reference direction:
- Pipeline definition: `.github/workflows/ci.yml`
- Backend lint/test config: `backend/requirements.txt`, `backend/tests/`
- Frontend build: `frontend-next/package.json`
- Compose files: `docker-compose.yml` (dev), `docker-compose.prod.yml` (prod)
- Model configs: `models/llm/*.yaml`

Current pipeline (ubuntu-latest, all jobs):
- `backend-lint`: `ruff check . --select E,W,F --ignore E501,W503`
- `backend-test`: `pytest tests/ -v --tb=short` (pytest-asyncio, httpx)
- `frontend-build`: `npm ci && npm run build` (Node 20)
- `docker-validate`: `docker compose config --quiet` for both dev and prod compose files
- `model-yaml-validate`: validate `models/llm/*.yaml` — required keys: name, backend, parameters.model

Triggers:
- push to main, develop
- pull_request to main, develop

Required checks:
- Install dependencies deterministically (`pip install -r requirements.txt`, `npm ci`).
- Run ruff lint first — fail fast on syntax/import errors.
- Run pytest with `-v --tb=short` for actionable output.
- Run `npm run build` to catch frontend compilation errors.
- Run `docker compose config --quiet` against both compose files.
- Validate model YAML files have required keys before merge.

Known gaps:
- No security scanning (SAST/DAST/dependency audit).
- No test coverage reporting (e.g., pytest-cov, coverage threshold).
- No integration tests (API-level tests against running containers).
- No deployment automation (CD stage missing).

Workflow rules:
- Keep jobs readable and low-noise.
- Reuse commands from package.json or requirements.txt — no duplicated shell logic in YAML.
- Cache pip and npm dependencies only when it measurably improves runtime.
- Separate frontend, backend, docker, and model-config checks into distinct jobs.
- Keep logs actionable and short.

Change rules:
- Do not introduce CD until CI is stable and all gaps above are addressed.
- Start with CI basics: lint, test, build, validate.
- Add security scanning as the next incremental step.
- Prefer incremental improvements over pipeline rewrites.

Debug strategy:
- Each failed job points to one layer: backend-lint, backend-test, frontend-build, docker-validate, or model-yaml-validate.
- Do not mix unrelated checks in one step.
- Surface missing env variables clearly (especially `JWT_SECRET`, `CORS_ORIGINS`).
- Keep command output concise so errors are easy to spot.

Code quality policy:
- No verbose comments in workflow files.
- No banner comments or tutorial comments.
- Only comment non-obvious workflow constraints or security-sensitive behavior.
