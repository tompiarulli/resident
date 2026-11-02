from fastapi.testclient import TestClient

from resident_server.main import create_app


def test_health():
    with TestClient(create_app()) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_ingest_requires_device_token():
    with TestClient(create_app()) as client:
        response = client.post("/api/ingest/healthkit", json={"samples": []})
    assert response.status_code == 401
