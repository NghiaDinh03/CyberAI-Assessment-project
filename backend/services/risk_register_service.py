"""Risk Register CRUD service — JSON file storage (Phase 2).

Storage layout mirrors ``data/sessions/`` pattern from
:class:`repositories.session_store.SessionStore`:

    DATA_PATH/risks/{risk_id}.json

Each file is a self-contained :class:`api.schemas.risk.Risk` record.
Thread-safety is handled via a module-level lock (single-process deploy).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from api.schemas.risk import Risk, RiskCreate, RiskUpdate

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _risks_dir() -> Path:
    """Resolve the risks directory from DATA_PATH (read at call time)."""
    base = os.getenv("DATA_PATH", "./data")
    d = Path(base) / "risks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _risk_path(risk_id: str) -> Path:
    safe = "".join(c for c in risk_id if c.isalnum() or c in "-_")
    return _risks_dir() / f"{safe}.json"


def create(payload: RiskCreate) -> Risk:
    """Persist a new risk and return the full record."""
    now = datetime.now(timezone.utc)
    risk_id = str(uuid.uuid4())

    risk = Risk(
        id=risk_id,
        asset_ref=payload.asset_ref,
        threat=payload.threat,
        vulnerability=payload.vulnerability,
        likelihood=payload.likelihood,
        impact=payload.impact,
        inherent_score=payload.likelihood * payload.impact,
        treatment=payload.treatment,
        residual_score=payload.residual_score,
        owner=payload.owner,
        review_date=payload.review_date,
        linked_controls=payload.linked_controls,
        created_at=now,
        updated_at=now,
    )

    with _lock:
        path = _risk_path(risk_id)
        path.write_text(risk.model_dump_json(indent=2), encoding="utf-8")

    logger.info("risk created id=%s asset=%s", risk_id, payload.asset_ref)
    return risk


def get(risk_id: str) -> Optional[Risk]:
    """Load a single risk by id, or None if not found."""
    path = _risk_path(risk_id)
    if not path.is_file():
        return None
    try:
        return Risk.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("corrupt risk file %s", path)
        return None


def list_all() -> List[Risk]:
    """Return every risk, sorted by created_at descending."""
    risks: List[Risk] = []
    d = _risks_dir()
    if not d.exists():
        return risks
    for f in d.iterdir():
        if f.suffix != ".json":
            continue
        try:
            risks.append(Risk.model_validate_json(f.read_text(encoding="utf-8")))
        except Exception:
            logger.warning("skipping corrupt risk file %s", f)
    risks.sort(key=lambda r: r.created_at, reverse=True)
    return risks


def update(risk_id: str, patch: RiskUpdate) -> Optional[Risk]:
    """Merge *patch* into the existing risk. Returns None if not found."""
    with _lock:
        existing = get(risk_id)
        if existing is None:
            return None

        data = existing.model_dump()
        updates = patch.model_dump(exclude_unset=True)
        data.update(updates)

        # Recalculate inherent_score whenever likelihood or impact changes.
        data["inherent_score"] = data["likelihood"] * data["impact"]
        data["updated_at"] = datetime.now(timezone.utc)

        risk = Risk.model_validate(data)
        path = _risk_path(risk_id)
        path.write_text(risk.model_dump_json(indent=2), encoding="utf-8")

    logger.info("risk updated id=%s", risk_id)
    return risk


def delete(risk_id: str) -> bool:
    """Delete a risk by id. Returns True if it existed."""
    with _lock:
        path = _risk_path(risk_id)
        if not path.is_file():
            return False
        path.unlink()
    logger.info("risk deleted id=%s", risk_id)
    return True
