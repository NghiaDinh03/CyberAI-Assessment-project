"""Unit tests for the Risk Register module (Phase 2).

Tests exercise the service layer directly and the HTTP routes via
FastAPI TestClient. Each test gets an isolated temp directory so
there is no cross-contamination.
"""

from __future__ import annotations

import pathlib
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


# ── fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def data_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(data_path):
    from api.routes.risks import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def _sample_payload(**overrides) -> dict:
    base = {
        "asset_ref": "ERP Server",
        "threat": "Ransomware attack",
        "vulnerability": "Unpatched OS",
        "likelihood": 4,
        "impact": 5,
        "treatment": "mitigate",
        "residual_score": 8,
        "owner": "CISO",
        "review_date": "2026-06-01",
        "linked_controls": ["A.5.1", "A.8.3"],
    }
    base.update(overrides)
    return base


# ── service-level tests ─────────────────────────────────────────────

class TestRiskRegisterService:

    def test_create_and_get(self, data_path):
        from api.schemas.risk import RiskCreate
        from services import risk_register_service as svc

        payload = RiskCreate(**_sample_payload())
        risk = svc.create(payload)

        assert risk.id
        assert risk.inherent_score == 4 * 5  # likelihood × impact
        assert risk.asset_ref == "ERP Server"
        assert risk.linked_controls == ["A.5.1", "A.8.3"]

        loaded = svc.get(risk.id)
        assert loaded is not None
        assert loaded.id == risk.id

    def test_list_all(self, data_path):
        from api.schemas.risk import RiskCreate
        from services import risk_register_service as svc

        svc.create(RiskCreate(**_sample_payload(asset_ref="Server A")))
        svc.create(RiskCreate(**_sample_payload(asset_ref="Server B")))

        risks = svc.list_all()
        assert len(risks) == 2
        # newest first
        assert risks[0].asset_ref == "Server B"

    def test_update_recalculates_inherent(self, data_path):
        from api.schemas.risk import RiskCreate, RiskUpdate
        from services import risk_register_service as svc

        risk = svc.create(RiskCreate(**_sample_payload(likelihood=3, impact=3)))
        assert risk.inherent_score == 9

        updated = svc.update(risk.id, RiskUpdate(likelihood=5))
        assert updated is not None
        assert updated.likelihood == 5
        assert updated.impact == 3  # unchanged
        assert updated.inherent_score == 15  # 5 × 3

    def test_update_nonexistent_returns_none(self, data_path):
        from api.schemas.risk import RiskUpdate
        from services import risk_register_service as svc

        result = svc.update("nonexistent-id", RiskUpdate(owner="Nobody"))
        assert result is None

    def test_delete(self, data_path):
        from api.schemas.risk import RiskCreate
        from services import risk_register_service as svc

        risk = svc.create(RiskCreate(**_sample_payload()))
        assert svc.delete(risk.id) is True
        assert svc.get(risk.id) is None
        assert svc.delete(risk.id) is False

    def test_linked_controls_deduplication(self, data_path):
        from api.schemas.risk import RiskCreate
        from services import risk_register_service as svc

        risk = svc.create(RiskCreate(**_sample_payload(
            linked_controls=["A.5.1", "A.5.1", "A.8.3", "A.8.3"]
        )))
        assert risk.linked_controls == ["A.5.1", "A.8.3"]


# ── route-level tests ───────────────────────────────────────────────

class TestRiskRoutes:

    def test_create_risk(self, client):
        resp = client.post("/api/risks", json=_sample_payload())
        assert resp.status_code == 201
        body = resp.json()
        assert body["inherent_score"] == 20
        assert body["id"]

    def test_list_risks(self, client):
        client.post("/api/risks", json=_sample_payload(asset_ref="A"))
        client.post("/api/risks", json=_sample_payload(asset_ref="B"))

        resp = client.get("/api/risks")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["risks"]) == 2

    def test_get_risk(self, client):
        create_resp = client.post("/api/risks", json=_sample_payload())
        risk_id = create_resp.json()["id"]

        resp = client.get(f"/api/risks/{risk_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == risk_id

    def test_get_risk_404(self, client):
        resp = client.get("/api/risks/nonexistent")
        assert resp.status_code == 404

    def test_patch_risk(self, client):
        create_resp = client.post("/api/risks", json=_sample_payload())
        risk_id = create_resp.json()["id"]

        resp = client.patch(f"/api/risks/{risk_id}", json={"owner": "CTO"})
        assert resp.status_code == 200
        assert resp.json()["owner"] == "CTO"

    def test_delete_risk(self, client):
        create_resp = client.post("/api/risks", json=_sample_payload())
        risk_id = create_resp.json()["id"]

        resp = client.delete(f"/api/risks/{risk_id}")
        assert resp.status_code == 204

        resp = client.get(f"/api/risks/{risk_id}")
        assert resp.status_code == 404

    def test_heatmap(self, client):
        client.post("/api/risks", json=_sample_payload(likelihood=4, impact=5))
        client.post("/api/risks", json=_sample_payload(likelihood=2, impact=3))

        resp = client.get("/api/risks/heatmap")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["matrix"][3][4] == 1  # likelihood=4, impact=5
        assert body["matrix"][1][2] == 1  # likelihood=2, impact=3

    def test_create_risk_validation(self, client):
        # likelihood out of range
        resp = client.post("/api/risks", json=_sample_payload(likelihood=6))
        assert resp.status_code == 422

        # missing required field
        payload = _sample_payload()
        del payload["threat"]
        resp = client.post("/api/risks", json=payload)
        assert resp.status_code == 422
