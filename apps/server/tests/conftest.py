"""Fixtures for tests that need a real database.

They create a throwaway ``resident_test`` database on the dev Postgres (``just db``) and skip
when it isn't running. Override the admin connection with RESIDENT_TEST_ADMIN_DSN.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from resident_core.models import AuditEvent, Scope
from resident_server import config, db, devices
from resident_server.main import create_app

SERVER_DIR = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.environ.get(
    "RESIDENT_TEST_ADMIN_DSN", "postgresql://resident:resident@localhost:5432/resident"
)
TEST_DB = "resident_test"


def _reset_caches() -> None:
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    async def recreate() -> None:
        conn = await asyncpg.connect(ADMIN_DSN, timeout=3)
        try:
            await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
            await conn.execute(f"CREATE DATABASE {TEST_DB}")
        finally:
            await conn.close()

    try:
        asyncio.run(recreate())
    except (OSError, asyncpg.PostgresError) as error:
        pytest.skip(f"Postgres not available for integration tests ({error})")

    url = ADMIN_DSN.replace("postgresql://", "postgresql+asyncpg://").rsplit("/", 1)[0]
    url = f"{url}/{TEST_DB}"
    os.environ["RESIDENT_DATABASE_URL"] = url
    _reset_caches()

    alembic_config = Config(str(SERVER_DIR / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(SERVER_DIR / "migrations"))
    command.upgrade(alembic_config, "head")
    yield url


@pytest.fixture
def client(database_url: str) -> Iterator[TestClient]:
    # Engines are tied to an event loop and each TestClient runs its own, so start fresh.
    _reset_caches()
    with TestClient(create_app()) as test_client:
        yield test_client
    _reset_caches()


def _run(database_url: str, work):
    async def go():
        engine = create_async_engine(database_url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine)() as session:
                return await work(session)
        finally:
            await engine.dispose()

    return asyncio.run(go())


@pytest.fixture
def make_token(database_url: str):
    """Create a device with the given scopes and return ``(name, token)``."""

    def make(*scopes: Scope) -> tuple[str, str]:
        name = f"test-{uuid.uuid4().hex[:8]}"
        token = _run(database_url, lambda s: devices.create_device(s, name, scopes))
        return name, token

    return make


@pytest.fixture
def revoke(database_url: str):
    return lambda name: _run(database_url, lambda s: devices.revoke_device(s, name))


@pytest.fixture
def audit_events(database_url: str):
    """Return audit events recorded for one actor, oldest first."""

    def fetch(actor: str) -> list[AuditEvent]:
        async def work(session):
            stmt = select(AuditEvent).where(AuditEvent.actor == actor).order_by(AuditEvent.id)
            return list((await session.scalars(stmt)).all())

        return _run(database_url, work)

    return fetch
