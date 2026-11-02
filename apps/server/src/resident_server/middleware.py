"""ASGI middleware and error handling that protect the server and keep data out of logs."""

from __future__ import annotations

import contextlib
import json
import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("resident")


class BodyTooLarge(Exception):
    pass


class BodySizeLimit:
    """Reject request bodies over ``max_bytes`` with 413, whether or not Content-Length is set."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(send)
            return

        received = 0
        started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except BodyTooLarge:
            if not started:
                await self._reject(send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps({"detail": f"Request body exceeds {self.max_bytes} bytes"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected errors without their message.

    Exception messages can contain health data (a database error echoing a row, a validation
    error echoing a value), so only the type and stack frames are logged.
    """
    frames = "".join(traceback.format_tb(exc.__traceback__))
    logger.error(
        "Unhandled %s on %s %s\n%s", type(exc).__name__, request.method, request.url.path, frames
    )
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


class SuppressReraisedErrors:
    """Outermost wrapper that stops errors from being logged a second time with their message.

    Starlette re-raises unhandled exceptions after the 500 handler runs so the server can log
    them, and uvicorn's log would include the exception message. ``handle_unexpected_error``
    has already logged a scrubbed version, so swallow the re-raise for HTTP requests.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        with contextlib.suppress(Exception):
            await self.app(scope, receive, send)
