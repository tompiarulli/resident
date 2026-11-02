"""MCP server exposing health data to Claude and local LLM clients.

Mounted into the FastAPI app at /mcp (streamable HTTP). Tools read through the same repository
layer as the REST API.
"""

from __future__ import annotations

from datetime import datetime

from mcp.server import MCPServer

from resident_core import catalog
from resident_server import repository
from resident_server.db import get_sessionmaker

mcp = MCPServer(
    "Resident",
    instructions=(
        "Personal health data for a single person: Apple Watch metrics, lab results and "
        "documents. Call list_metrics first to see what data exists. Values are in the "
        "canonical unit reported for each metric. This is decision support, not diagnosis."
    ),
)


@mcp.tool()
async def list_metrics() -> list[dict]:
    """List every metric with stored data, its unit, sample count and most recent date."""
    async with get_sessionmaker()() as session:
        rows = await repository.list_metrics(session)
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
    metric: str, since: datetime | None = None, until: datetime | None = None, limit: int = 200
) -> list[dict]:
    """Return observations for one metric, newest first, optionally bounded by date."""
    async with get_sessionmaker()() as session:
        rows = await repository.query_observations(session, metric, since, until, min(limit, 2000))
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
