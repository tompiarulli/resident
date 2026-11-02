from __future__ import annotations

import secrets
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from resident_core import catalog
from resident_core.models import SourceKind
from resident_ingest.healthkit import normalize_sample
from resident_server import repository
from resident_server.config import get_settings
from resident_server.db import get_session
from resident_server.schemas import (
    HealthKitBatch,
    IngestResult,
    MetricSummary,
    ObservationOut,
)

router = APIRouter(prefix="/api")
Session = Annotated[AsyncSession, Depends(get_session)]


def require_device(authorization: Annotated[str | None, Header()] = None) -> None:
    token = get_settings().device_token
    if not token or not secrets.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device token")


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/ingest/healthkit",
    tags=["ingest"],
    dependencies=[Depends(require_device)],
    response_model=IngestResult,
)
async def ingest_healthkit(batch: HealthKitBatch, session: Session) -> IngestResult:
    normalized = [normalize_sample(**s.model_dump()) for s in batch.samples]
    known = [o for o in normalized if o is not None]
    stored = await repository.upsert_observations(session, SourceKind.HEALTHKIT, known)
    return IngestResult(
        received=len(batch.samples), stored=stored, skipped_unknown=len(normalized) - len(known)
    )


@router.get("/metrics", tags=["observations"], response_model=list[MetricSummary])
async def list_metrics(session: Session) -> list[MetricSummary]:
    summaries = []
    for key, count, latest in await repository.list_metrics(session):
        metric = catalog.get(key)
        summaries.append(
            MetricSummary(
                metric=key,
                name=metric.name if metric else None,
                unit=metric.unit if metric else None,
                count=count,
                latest_at=latest,
            )
        )
    return summaries


@router.get(
    "/metrics/{metric}/observations", tags=["observations"], response_model=list[ObservationOut]
)
async def get_observations(
    metric: str,
    session: Session,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 500,
) -> list[ObservationOut]:
    rows = await repository.query_observations(session, metric, since, until, min(limit, 5000))
    return [ObservationOut.model_validate(r) for r in rows]
