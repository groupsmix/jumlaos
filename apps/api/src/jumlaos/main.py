"""FastAPI app factory.

Mounts per-module routers under `/v1` and wires global middleware.
Everything under `/v1` requires auth except `/v1/auth/*`, `/v1/health`,
`/v1/ready`, and signed webhooks.
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
from jumlaos.config import get_settings
from jumlaos.core.errors import register_exception_handlers
from jumlaos.core.routes import auth as auth_routes
from jumlaos.core.routes import health as health_routes
from jumlaos.core.routes import me as me_routes
from jumlaos.core.routes import memberships as memberships_routes
from jumlaos.logging import configure_logging, get_logger
from jumlaos.mali.routes import router as mali_router
from jumlaos.talab.routes import router as talab_router
from jumlaos.whatsapp.routes import router as whatsapp_router


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


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="JumlaOS API",
        version=__version__,
        default_response_class=ORJSONResponse,
        docs_url="/v1/docs",
        redoc_url=None,
        openapi_url="/v1/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = request_id
        return response

    register_exception_handlers(app)

    # Mount routers
    app.include_router(health_routes.router, prefix="/v1")
    app.include_router(auth_routes.router, prefix="/v1/auth", tags=["auth"])
    app.include_router(me_routes.router, prefix="/v1", tags=["me"])
    app.include_router(memberships_routes.router, prefix="/v1/memberships", tags=["memberships"])
    app.include_router(mali_router, prefix="/v1", tags=["mali"])
    app.include_router(talab_router, prefix="/v1", tags=["talab"])
    app.include_router(whatsapp_router, prefix="/v1", tags=["whatsapp"])

    return app


app = create_app()
