"""Risk Scoring Service — Authoritative Single Source of Truth for Risk Heatmap (4×4).

Enforces the official Risk Heatmap specification:
- Likelihood: 1–4
- Impact: 1–4
- Risk Score = Likelihood × Impact
- Risk Score Min: 1
- Risk Score Max: 16
"""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

RISK_AXIS_MIN = 1
RISK_AXIS_MAX = 4
RISK_SCORE_MIN = 1
RISK_SCORE_MAX = 16

RiskSeverity = Literal["critical", "high", "medium", "low"]


def calculate_risk_score(likelihood: int, impact: int) -> int:
    """Calculate risk score as Likelihood × Impact on the official 4×4 matrix.

    Raises:
        ValueError: If likelihood or impact is outside the valid range [1, 4].
    """
    if not isinstance(likelihood, int) or not (RISK_AXIS_MIN <= likelihood <= RISK_AXIS_MAX):
        raise ValueError("Likelihood must be between 1 and 4")
    if not isinstance(impact, int) or not (RISK_AXIS_MIN <= impact <= RISK_AXIS_MAX):
        raise ValueError("Impact must be between 1 and 4")
    return likelihood * impact


def classify_risk_severity(score: int) -> RiskSeverity:
    """Classify risk score (1-16) into standardized severity levels:
    - Critical (12–16): e.g. 3×4=12, 4×3=12, 4×4=16
    - High (8–11): e.g. 2×4=8, 3×3=9
    - Medium (4–7): e.g. 1×4=4, 2×2=4, 2×3=6
    - Low (1–3): e.g. 1×1=1, 1×2=2, 1×3=3
    """
    if not isinstance(score, (int, float)) or not (RISK_SCORE_MIN <= score <= RISK_SCORE_MAX):
        logger.warning("Score %s is outside 4x4 matrix range [1, 16]", score)
    if score >= 12:
        return "critical"
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def is_valid_risk_axis(val: int) -> bool:
    """Check if value is within [1, 4]."""
    return isinstance(val, int) and (RISK_AXIS_MIN <= val <= RISK_AXIS_MAX)


def is_valid_risk_score(val: int) -> bool:
    """Check if value is within [1, 16]."""
    return isinstance(val, int) and (RISK_SCORE_MIN <= val <= RISK_SCORE_MAX)
