"""Smoke test: the FastAPI app builds and /v1/health responds without a DB."""

from __future__ import annotations

from fastapi.testclient import TestClient

from jumlaos.main import app


def test_health() -> None:
    client = TestClient(app)
    r = client.get("/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_openapi_schema() -> None:
    client = TestClient(app)
    r = client.get("/v1/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    # core + mali + whatsapp endpoints are mounted
    paths = set(schema["paths"].keys())
    assert "/v1/auth/otp/request" in paths
    assert "/v1/debtors" in paths
    assert "/v1/invoices" in paths
    assert "/v1/webhook/whatsapp" in paths


def test_requires_auth() -> None:
    client = TestClient(app)
    r = client.get("/v1/debtors")
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["code"] == "unauthorized"


def test_cors_headers() -> None:
    client = TestClient(app)
    r = client.options(
        "/v1/debtors",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert "access-control-allow-origin" in {k.lower() for k in r.headers}
