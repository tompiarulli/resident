"""Authentication: scoped device tokens and trusted Tailscale identities.

Devices (the iOS app, agents, MCP clients) send ``Authorization: Bearer rsd_...``. People using
the dashboard are identified by the ``Tailscale-User-Login`` header that ``tailscale serve``
adds, but only when their login is in ``RESIDENT_TRUSTED_TAILSCALE_LOGINS``. See
docs/SECURITY.md for why that header can be trusted.
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from resident_core.models import Device, Scope
from resident_server.config import get_settings
from resident_server.db import get_session

TOKEN_PREFIX = "rsd_"
TAILSCALE_LOGIN_HEADER = "tailscale-user-login"
# Avoid a database write on every request just to bump last_used_at.
LAST_USED_RESOLUTION = timedelta(minutes=1)


@dataclass(frozen=True)
class Principal:
    """Who is making a request and what they may do."""

    name: str
    scopes: frozenset[Scope]

    def has(self, scope: Scope) -> bool:
        return scope in self.scopes


@dataclass(frozen=True)
class NewToken:
    token: str
    prefix: str
    hash: str


def generate_token() -> NewToken:
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return NewToken(token=token, prefix=token[:12], hash=hash_token(token))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def authenticate(session: AsyncSession, headers: Mapping[str, str]) -> Principal | None:
    """Resolve request headers to a principal, or None if unauthenticated."""
    authorization = headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.startswith(TOKEN_PREFIX):
        return await _authenticate_token(session, token)

    login = headers.get(TAILSCALE_LOGIN_HEADER)
    if login and login in get_settings().trusted_tailscale_logins:
        # The person who owns this instance: full access through the dashboard.
        return Principal(name=f"user:{login}", scopes=frozenset(Scope))
    return None


async def _authenticate_token(session: AsyncSession, token: str) -> Principal | None:
    device = await session.scalar(
        select(Device).where(Device.token_hash == hash_token(token), Device.revoked_at.is_(None))
    )
    if device is None:
        return None
    await session.execute(
        update(Device)
        .where(
            Device.id == device.id,
            or_(
                Device.last_used_at.is_(None),
                Device.last_used_at < func.now() - LAST_USED_RESOLUTION,
            ),
        )
        .values(last_used_at=func.now())
    )
    await session.commit()
    return Principal(name=device.name, scopes=frozenset(Scope(s) for s in device.scopes))


def require(scope: Scope) -> Callable[..., Coroutine[Any, Any, Principal]]:
    """FastAPI dependency that requires an authenticated principal with ``scope``."""

    async def dependency(
        request: Request, session: Annotated[AsyncSession, Depends(get_session)]
    ) -> Principal:
        principal = await authenticate(session, request.headers)
        if principal is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not principal.has(scope):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires the {scope} scope")
        return principal

    return dependency
