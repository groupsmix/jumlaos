"""Smoke test: the FastAPI app builds and /v1/health responds without a DB."""

from __future__ import annotations

from fastapi.testclient import TestClient

from jumlaos.main import app


def test_health() -> None:
    client = TestClient(app)
    r = client.get("/v1/livez")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "alive"


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


def test_idempotency_header_in_cors() -> None:
    """F02 smoke test: Idempotency-Key is an allowed CORS header."""
    client = TestClient(app)
    r = client.options(
        "/v1/debtors",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Idempotency-Key",
        },
    )
    assert r.status_code == 200
    allowed = r.headers.get("access-control-allow-headers", "").lower()
    assert "idempotency-key" in allowed


def test_body_size_limit() -> None:
    """F25 smoke test: oversized request bodies are rejected with 413."""
    client = TestClient(app)
    r = client.post(
        "/v1/debtors",
        headers={
            "Origin": "http://localhost:3000",
            "Content-Length": str(256 * 1024 + 1),
        },
        content="x",  # Content-Length header is what matters
    )
    assert r.status_code == 413


def test_cache_control_on_api_responses() -> None:
    """Quick win: all /v1/* responses (except health) have Cache-Control: no-store."""
    client = TestClient(app)
    r = client.get("/v1/debtors")
    assert r.headers.get("cache-control") == "no-store"


def test_secure_headers_present() -> None:
    """Verify security headers are set on all responses."""
    client = TestClient(app)
    r = client.get("/v1/livez")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy") == "no-referrer"
    assert "max-age=" in (r.headers.get("strict-transport-security") or "")
