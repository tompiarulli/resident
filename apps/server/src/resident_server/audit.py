"""Audit log of access to health data.

Call ``record`` from every route or tool that reads or writes observations. ``target`` describes
what was asked for (metric, date range, limit), never the values returned.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resident_core.models import AuditEvent
from resident_server.auth import Principal


async def record(
    session: AsyncSession,
    principal: Principal,
    action: str,
    target: dict[str, Any] | None = None,
    result_count: int | None = None,
) -> None:
    clean = {k: _jsonable(v) for k, v in (target or {}).items() if v is not None}
    session.add(
        AuditEvent(
            actor=principal.name, action=action, target=clean or None, result_count=result_count
        )
    )
    await session.commit()


async def recent(session: AsyncSession, limit: int = 200) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.at.desc()).limit(limit)
    return list((await session.scalars(stmt)).all())


def _jsonable(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value
