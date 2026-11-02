"""MCP server exposing health data to AI agents.

Mounted into the FastAPI app at /mcp (streamable HTTP) behind ``RequireScope``, so every MCP
request needs a token with the ``read`` scope. Tools read through the same repository layer as
the REST API.
"""

from __future__ import annotations

import json
from datetime import datetime

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from starlette.types import ASGIApp, Receive, Scope, Send

from resident_core import catalog
from resident_core.models import Scope as TokenScope
from resident_server import audit, repository
from resident_server.auth import Principal, authenticate
from resident_server.db import get_sessionmaker

mcp = MCPServer(
    "Resident",
    instructions=(
        "Personal health data for a single person: Apple Watch metrics, lab results and "
        "documents. Call list_metrics first to see what data exists. Values are in the "
        "canonical unit reported for each metric. This is decision support, not diagnosis."
    ),
)


class RequireScope:
    """ASGI middleware: authenticate every HTTP request and require a token scope.

    The authenticated principal is stored on the request state so tools can attribute
    audit events to it.
    """

    def __init__(self, app: ASGIApp, scope: TokenScope) -> None:
        self.app = app
        self.required = scope

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        async with get_sessionmaker()() as session:
            principal = await authenticate(session, headers)
        if principal is None:
            await _reject(send, 401, "Authentication required")
            return
        if not principal.has(self.required):
            await _reject(send, 403, f"Requires the {self.required} scope")
            return
        scope.setdefault("state", {})["principal"] = principal
        await self.app(scope, receive, send)


async def _reject(send: Send, status: int, message: str) -> None:
    body = json.dumps({"detail": message}).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    if status == 401:
        headers.append((b"www-authenticate", b"Bearer"))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def principal_of(ctx: Context) -> Principal:
    """The principal ``RequireScope`` authenticated for the current request."""
    request = ctx.request_context.request
    principal = getattr(request.state, "principal", None) if request else None
    if principal is None:
        raise PermissionError("Unauthenticated MCP request")
    return principal


@mcp.tool()
async def list_metrics(ctx: Context) -> list[dict]:
    """List every metric with stored data, its unit, sample count and most recent date."""
    principal = principal_of(ctx)
    async with get_sessionmaker()() as session:
        rows = await repository.list_metrics(session)
        await audit.record(session, principal, "mcp.list_metrics", result_count=len(rows))
    result = []
    for key, count, latest in rows:
        metric = catalog.get(key)
        result.append(
            {
                "metric": key,
                "name": metric.name if metric else key,
                "unit": metric.unit if metric else None,
                "count": count,
                "latest": latest.isoformat(),
            }
        )
    return result


@mcp.tool()
async def query_observations(
    ctx: Context,
    metric: str,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 200,
) -> list[dict]:
    """Return observations for one metric, newest first, optionally bounded by date."""
    principal = principal_of(ctx)
    limit = min(limit, 2000)
    async with get_sessionmaker()() as session:
        rows = await repository.query_observations(session, metric, since, until, limit)
        await audit.record(
            session,
            principal,
            "mcp.query_observations",
            {"metric": metric, "since": since, "until": until, "limit": limit},
            len(rows),
        )
    return [
        {
            "value": r.value,
            "value_text": r.value_text,
            "unit": r.unit,
            "start": r.start_at.isoformat(),
            "end": r.end_at.isoformat() if r.end_at else None,
        }
        for r in rows
    ]
