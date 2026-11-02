from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from resident_core import catalog
from resident_core.models import Scope, SourceKind
from resident_ingest.healthkit import normalize_sample
from resident_server import audit, repository
from resident_server.auth import Principal, require
from resident_server.db import get_session
from resident_server.schemas import (
    AuditEventOut,
    HealthKitBatch,
    IngestResult,
    MetricSummary,
    ObservationOut,
)

router = APIRouter(prefix="/api")
Session = Annotated[AsyncSession, Depends(get_session)]
Ingester = Annotated[Principal, Depends(require(Scope.INGEST))]
Reader = Annotated[Principal, Depends(require(Scope.READ))]
Admin = Annotated[Principal, Depends(require(Scope.ADMIN))]


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ingest/healthkit", tags=["ingest"], response_model=IngestResult)
async def ingest_healthkit(
    batch: HealthKitBatch, session: Session, principal: Ingester
) -> IngestResult:
    normalized = [normalize_sample(**s.model_dump()) for s in batch.samples]
    known = [o for o in normalized if o is not None]
    stored = await repository.upsert_observations(session, SourceKind.HEALTHKIT, known)
    await audit.record(
        session, principal, "api.ingest_healthkit", {"received": len(batch.samples)}, stored
    )
    return IngestResult(
        received=len(batch.samples), stored=stored, skipped_unknown=len(normalized) - len(known)
    )


@router.get("/metrics", tags=["observations"], response_model=list[MetricSummary])
async def list_metrics(session: Session, principal: Reader) -> list[MetricSummary]:
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
    await audit.record(session, principal, "api.list_metrics", result_count=len(summaries))
    return summaries


@router.get(
    "/metrics/{metric}/observations", tags=["observations"], response_model=list[ObservationOut]
)
async def get_observations(
    metric: str,
    session: Session,
    principal: Reader,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 500,
) -> list[ObservationOut]:
    limit = min(limit, 5000)
    rows = await repository.query_observations(session, metric, since, until, limit)
    await audit.record(
        session,
        principal,
        "api.get_observations",
        {"metric": metric, "since": since, "until": until, "limit": limit},
        len(rows),
    )
    return [ObservationOut.model_validate(r) for r in rows]


@router.get("/audit", tags=["system"], response_model=list[AuditEventOut])
async def get_audit_log(
    session: Session, principal: Admin, limit: int = 200
) -> list[AuditEventOut]:
    """Recent accesses to health data. Reading the log is itself not audited."""
    return [AuditEventOut.model_validate(e) for e in await audit.recent(session, min(limit, 1000))]
