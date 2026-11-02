"""Creating, listing and revoking device tokens."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from resident_core.models import Device, Scope
from resident_server.auth import generate_token


class DeviceError(Exception):
    pass


async def create_device(session: AsyncSession, name: str, scopes: Iterable[Scope]) -> str:
    """Create a device and return its token. The token is only ever shown here."""
    scopes = sorted(set(scopes))
    if not scopes:
        raise DeviceError("A device needs at least one scope")
    if await session.scalar(select(Device.id).where(Device.name == name)):
        raise DeviceError(f"A device named {name!r} already exists")
    new = generate_token()
    session.add(
        Device(name=name, token_hash=new.hash, token_prefix=new.prefix, scopes=list(scopes))
    )
    await session.commit()
    return new.token


async def list_devices(session: AsyncSession) -> list[Device]:
    return list((await session.scalars(select(Device).order_by(Device.created_at))).all())


async def revoke_device(session: AsyncSession, name: str) -> None:
    result = await session.execute(
        update(Device)
        .where(Device.name == name, Device.revoked_at.is_(None))
        .values(revoked_at=func.now())
    )
    if result.rowcount == 0:
        raise DeviceError(f"No active device named {name!r}")
    await session.commit()
