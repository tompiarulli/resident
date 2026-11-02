"""Database access shared by the REST API and the MCP server."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from resident_core.models import Observation, Source, SourceKind
from resident_ingest import NormalizedObservation


async def get_or_create_source(session: AsyncSession, kind: SourceKind, name: str) -> Source:
    stmt = (
        insert(Source)
        .values(kind=kind, name=name)
        .on_conflict_do_update(index_elements=["kind", "name"], set_={"name": name})
        .returning(Source)
    )
    return (await session.execute(stmt)).scalar_one()


async def upsert_observations(
    session: AsyncSession, kind: SourceKind, observations: Iterable[NormalizedObservation]
) -> int:
    """Insert observations, skipping ones already stored (same source + external id)."""
    sources: dict[str, Source] = {}
    rows = []
    for obs in observations:
        if obs.source_name not in sources:
            sources[obs.source_name] = await get_or_create_source(session, kind, obs.source_name)
        rows.append(
            obs.model_dump(exclude={"source_name"}) | {"source_id": sources[obs.source_name].id}
        )
    if not rows:
        return 0
    stmt = (
        insert(Observation)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["source_id", "external_id", "start_at"])
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0


async def list_metrics(session: AsyncSession) -> list[tuple[str, int, datetime]]:
    stmt = (
        select(Observation.metric, func.count(), func.max(Observation.start_at))
        .group_by(Observation.metric)
        .order_by(Observation.metric)
    )
    return [tuple(row) for row in await session.execute(stmt)]


async def query_observations(
    session: AsyncSession,
    metric: str,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 500,
) -> list[Observation]:
    stmt = select(Observation).where(Observation.metric == metric)
    if since:
        stmt = stmt.where(Observation.start_at >= since)
    if until:
        stmt = stmt.where(Observation.start_at < until)
    stmt = stmt.order_by(Observation.start_at.desc()).limit(limit)
    return list((await session.scalars(stmt)).all())
