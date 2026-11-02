from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from resident_core.models import Scope
from resident_server.api import router
from resident_server.config import get_settings
from resident_server.mcp_server import RequireScope, mcp


def create_app() -> FastAPI:
    settings = get_settings()
    # Each call builds a fresh MCP app; its session manager can only be started once.
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/",
        # Rejects requests whose Host header isn't listed (DNS rebinding protection).
        transport_security=TransportSecuritySettings(allowed_hosts=settings.allowed_hosts),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Starlette doesn't run a mounted app's lifespan, so start the MCP session manager here.
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="Resident", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.mount("/mcp", RequireScope(mcp_app, Scope.READ))
    return app


app = create_app()
