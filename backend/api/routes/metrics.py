"""Prometheus metrics endpoint for CyberAI Assessment Platform.

Exposes standard Prometheus text format at GET /metrics.
This route is mounted at prefix="" (root) so the endpoint is reachable
at /metrics — not /api/metrics — for standard Prometheus scraper compatibility.

Usage in main.py:
    from api.routes.metrics import router as metrics_router
    app.include_router(metrics_router, prefix="")
"""

import logging

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

REQUEST_COUNT = Counter(
    "cyberai_requests_total",
    "Total HTTP requests processed by the CyberAI API",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "cyberai_request_duration_seconds",
    "HTTP request processing duration in seconds",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_SESSIONS = Gauge(
    "cyberai_active_sessions",
    "Number of active chat sessions currently tracked in the session store",
)

RAG_QUERIES = Counter(
    "cyberai_rag_queries_total",
    "Total RAG vector-store queries, labelled by result",
    ["result"],  # label values: "hit" | "miss"
)

ASSESSMENTS_TOTAL = Gauge(
    "cyberai_assessments_total",
    "Total number of assessment records persisted on disk",
)


@router.get(
    "/metrics",
    response_class=Response,
    include_in_schema=False,
    summary="Prometheus metrics scrape endpoint",
)
async def metrics() -> Response:
    """Return all registered Prometheus metrics in text exposition format.

    Prometheus should be configured to scrape this endpoint:

    .. code-block:: yaml

        scrape_configs:
          - job_name: cyberai
            static_configs:
              - targets: ['backend:8000']
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
