from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from resident_server.middleware import (
    BodySizeLimit,
    SuppressReraisedErrors,
    handle_unexpected_error,
)


def make_client(max_bytes: int) -> TestClient:
    app = FastAPI()

    @app.post("/echo")
    async def echo(request: Request) -> dict[str, int]:
        return {"size": len(await request.body())}

    app.add_middleware(BodySizeLimit, max_bytes=max_bytes)
    return TestClient(app)


def test_allows_body_under_limit():
    response = make_client(100).post("/echo", content=b"x" * 100)
    assert response.json() == {"size": 100}


def test_rejects_declared_oversized_body():
    assert make_client(100).post("/echo", content=b"x" * 101).status_code == 413


def test_rejects_streamed_oversized_body_without_content_length():
    def chunks():
        for _ in range(5):
            yield b"x" * 50

    assert make_client(100).post("/echo", content=chunks()).status_code == 413


def test_unexpected_errors_are_logged_without_their_message(caplog):
    app = FastAPI()
    app.add_exception_handler(Exception, handle_unexpected_error)

    # Built at runtime so it can only appear in logs via the exception message, not via the
    # source lines included in stack frames.
    secret = "-".join(["resting", "hr", "fifty", "two"])

    @app.get("/boom")
    async def boom() -> None:
        raise ValueError(secret)

    client = TestClient(SuppressReraisedErrors(app), raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    assert "ValueError" in caplog.text
    assert secret not in caplog.text
