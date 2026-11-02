"""Integration tests for the guarantees in docs/SECURITY.md."""

from __future__ import annotations

import json

import pytest

from resident_core.models import Scope
from resident_server import config

SAMPLE = {
    "uuid": "S1",
    "type": "HKQuantityTypeIdentifierRestingHeartRate",
    "value": 52,
    "unit": "count/min",
    "start": "2026-10-30T00:00:00Z",
    "end": "2026-10-30T23:59:00Z",
    "source_name": "Apple Watch",
}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_reads_require_authentication(client):
    assert client.get("/api/metrics").status_code == 401
    assert client.get("/api/metrics", headers=auth("rsd_not-a-real-token")).status_code == 401


def test_ingest_token_can_write_but_not_read(client, make_token):
    _, token = make_token(Scope.INGEST)

    response = client.post("/api/ingest/healthkit", json={"samples": [SAMPLE]}, headers=auth(token))
    assert response.status_code == 200
    assert client.get("/api/metrics", headers=auth(token)).status_code == 403


def test_read_token_can_read_but_not_write(client, make_token):
    _, token = make_token(Scope.READ)

    assert client.get("/api/metrics", headers=auth(token)).status_code == 200
    response = client.post("/api/ingest/healthkit", json={"samples": [SAMPLE]}, headers=auth(token))
    assert response.status_code == 403


def test_revoked_token_is_rejected(client, make_token, revoke):
    name, token = make_token(Scope.READ)
    assert client.get("/api/metrics", headers=auth(token)).status_code == 200

    revoke(name)
    assert client.get("/api/metrics", headers=auth(token)).status_code == 401


def test_audit_log_is_admin_only(client, make_token):
    _, reader = make_token(Scope.READ)
    _, admin = make_token(Scope.ADMIN)

    assert client.get("/api/audit", headers=auth(reader)).status_code == 403
    assert client.get("/api/audit", headers=auth(admin)).status_code == 200


def test_reads_are_audited_without_values(client, make_token, audit_events):
    _, writer = make_token(Scope.INGEST)
    reader_name, reader = make_token(Scope.READ)
    client.post("/api/ingest/healthkit", json={"samples": [SAMPLE]}, headers=auth(writer))

    response = client.get(
        "/api/metrics/resting_heart_rate/observations",
        params={"since": "2026-10-01T00:00:00Z"},
        headers=auth(reader),
    )
    assert response.json()[0]["value"] == 52

    [event] = audit_events(reader_name)
    assert event.action == "api.get_observations"
    assert event.target["metric"] == "resting_heart_rate"
    assert event.result_count == 1
    assert "52" not in json.dumps(event.target)


def test_mcp_requires_read_scope(client, make_token):
    _, ingest = make_token(Scope.INGEST)
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

    assert client.post("/mcp/", json=request).status_code == 401
    assert client.post("/mcp/", json=request, headers=auth(ingest)).status_code == 403


@pytest.fixture
def trust_login(monkeypatch):
    def trust(login: str) -> None:
        monkeypatch.setenv("RESIDENT_TRUSTED_TAILSCALE_LOGINS", login)
        config.get_settings.cache_clear()

    yield trust
    config.get_settings.cache_clear()


def test_tailscale_identity_only_when_allowlisted(client, trust_login):
    header = {"Tailscale-User-Login": "me@github"}
    assert client.get("/api/metrics", headers=header).status_code == 401

    trust_login("me@github")
    assert client.get("/api/metrics", headers=header).status_code == 200
    assert (
        client.get("/api/metrics", headers={"Tailscale-User-Login": "else@github"}).status_code
        == 401
    )
