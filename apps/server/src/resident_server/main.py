from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from resident_server.api import router
from resident_server.config import get_settings
from resident_server.mcp_server import mcp


def create_app() -> FastAPI:
    # Each call builds a fresh MCP app; its session manager can only be started once.
    mcp_app = mcp.streamable_http_app(streamable_http_path="/")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Starlette doesn't run a mounted app's lifespan, so start the MCP session manager here.
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="Resident", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.mount("/mcp", mcp_app)
    return app


app = create_app()
