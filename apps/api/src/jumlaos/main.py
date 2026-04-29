"""FastAPI app factory.

Mounts per-module routers under `/v1` and wires global middleware.
Everything under `/v1` requires auth except `/v1/auth/*`, `/v1/health`,
`/v1/livez`, `/v1/readyz`, and signed webhooks.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from jumlaos import __version__
from jumlaos.config import Settings, get_settings
from jumlaos.core.errors import register_exception_handlers
from jumlaos.core.idempotency import idempotency_middleware
from jumlaos.core.rate_limit import (
    cache_json_body_middleware,
    limiter,
    rate_limit_exceeded_handler,
)
from jumlaos.core.routes import auth as auth_routes
from jumlaos.core.routes import health as health_routes
from jumlaos.core.routes import me as me_routes
from jumlaos.core.routes import memberships as memberships_routes
from jumlaos.logging import configure_logging, get_logger
from jumlaos.mali.routes import router as mali_router
from jumlaos.talab.routes import router as talab_router
from jumlaos.whatsapp.routes import router as whatsapp_router

# Webhook prefixes that bypass CSRF Origin/Referer enforcement.
# These routes are HMAC-authenticated and called by external systems
# (Meta, payment providers) that do not send a browser Origin/Referer.
WEBHOOK_PATH_PREFIXES = ("/v1/webhook/",)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.env,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.05 if settings.is_prod else 0.0,
            send_default_pii=False,
        )
    get_logger().info("jumlaos.startup", env=settings.env, version=__version__)
    yield
    get_logger().info("jumlaos.shutdown")


def _register_middleware(app: FastAPI, settings: Settings) -> None:
    @app.middleware("http")
    async def secure_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/v1/auth/"):
            response.headers["Cache-Control"] = "no-store"
        elif request.url.path.startswith("/v1/") and request.url.path not in (
            "/v1/livez",
            "/v1/readyz",
            "/v1/health",
        ):
            # Quick win: never cache authenticated API responses.
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.middleware("http")
    async def body_size_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        # F25: enforce a hard cap on request bodies to defend against memory DoS.
        is_webhook = any(request.url.path.startswith(p) for p in WEBHOOK_PATH_PREFIXES)
        limit = settings.max_webhook_bytes if is_webhook else settings.max_request_bytes
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > limit:
                    return ORJSONResponse(
                        status_code=413, content={"error": {"code": "request_too_large"}}
                    )
            except ValueError:
                return ORJSONResponse(
                    status_code=400, content={"error": {"code": "bad_content_length"}}
                )
        return await call_next(request)

    @app.middleware("http")
    async def csrf_and_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        # F09: webhooks are HMAC-authenticated and exempt from Origin/Referer checks.
        is_webhook = any(request.url.path.startswith(p) for p in WEBHOOK_PATH_PREFIXES)
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and not is_webhook:
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            origin_ok = origin is not None and origin in settings.cors_origins
            referer_ok = referer is not None and any(
                referer.startswith(o) for o in settings.cors_origins
            )
            # Default-deny: a mutating request must present a recognised Origin
            # OR Referer regardless of cookie presence. This protects both
            # cookie-authenticated and bearer-authenticated callers from CSRF.
            if not (origin_ok or referer_ok):
                return ORJSONResponse(
                    status_code=403,
                    content={"error": {"code": "csrf_missing_or_invalid_origin"}},
                )

        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = request_id
        return response

    # F02: per-route idempotency for mutating requests with `Idempotency-Key`.
    app.middleware("http")(idempotency_middleware)

    # F10/F20: pre-read OTP request bodies so the slowapi phone-keyed limiter
    # has a phone number to hash on.
    app.middleware("http")(cache_json_body_middleware)


def _mount_routers(app: FastAPI) -> None:
    app.include_router(health_routes.router, prefix="/v1")
    app.include_router(auth_routes.router, prefix="/v1/auth", tags=["auth"])
    app.include_router(me_routes.router, prefix="/v1", tags=["me"])
    app.include_router(memberships_routes.router, prefix="/v1/memberships", tags=["memberships"])
    app.include_router(mali_router, prefix="/v1", tags=["mali"])
    app.include_router(talab_router, prefix="/v1", tags=["talab"])
    app.include_router(whatsapp_router, prefix="/v1", tags=["whatsapp"])


def create_app() -> FastAPI:
    settings = get_settings()

    # F17: do not expose Swagger UI in prod.
    docs_url = None if settings.is_prod else "/v1/docs"

    app = FastAPI(
        title="JumlaOS API",
        version=__version__,
        default_response_class=ORJSONResponse,
        docs_url=docs_url,
        redoc_url=None,
        openapi_url="/v1/openapi.json" if not settings.is_prod else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",
            "Idempotency-Key",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    _register_middleware(app, settings)

    # F10: global rate limiter shared by every route.
    app.state.limiter = limiter
    from slowapi.errors import RateLimitExceeded

    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    register_exception_handlers(app)
    _mount_routers(app)

    return app


app = create_app()
