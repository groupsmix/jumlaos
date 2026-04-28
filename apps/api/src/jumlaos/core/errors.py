"""Centralised exception handlers. Consistent error envelope."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse

from jumlaos.logging import get_logger

log = get_logger(__name__)


class DomainError(Exception):
    """Base class for domain-level errors (business rule violations)."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class NotFound(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class Forbidden(DomainError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class Unauthorized(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class Conflict(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class RateLimited(DomainError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"


def _envelope(*, code: str, message: str, details: object | None = None) -> dict[str, object]:
    body: dict[str, object] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details  # type: ignore[index]
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Unauthorized)
    async def unauthorized_handler(request: Request, exc: Unauthorized) -> ORJSONResponse:
        log.warning(
            "auth_failure",
            reason=exc.message,
            path=request.url.path,
            method=request.method,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return ORJSONResponse(
            _envelope(code=exc.code, message=exc.message),
            status_code=exc.status_code,
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> ORJSONResponse:
        return ORJSONResponse(
            _envelope(code=exc.code, message=exc.message),
            status_code=exc.status_code,
        )

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException) -> ORJSONResponse:
        return ORJSONResponse(
            _envelope(
                code=f"http_{exc.status_code}",
                message=str(exc.detail) if exc.detail else "error",
            ),
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> ORJSONResponse:
        return ORJSONResponse(
            _envelope(
                code="validation_error",
                message="Request validation failed",
                details=exc.errors(),
            ),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> ORJSONResponse:
        log.exception("unhandled_exception", exc_type=type(exc).__name__)
        return ORJSONResponse(
            _envelope(code="internal_error", message="Internal server error"),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
