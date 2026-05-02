"""
Global exception handlers — ensure no stack traces or internal details
are ever leaked to API consumers.

Register in main.py via:
    from app.core.exception_handlers import register_handlers
    register_handlers(app)
"""
from __future__ import annotations

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


def register_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Return structured error — never expose internal paths or stack traces."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": _status_label(exc.status_code),
                "detail": exc.detail,
                "path": request.url.path,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Return readable validation errors without internal model details."""
        errors = []
        for err in exc.errors():
            field = " → ".join(str(p) for p in err.get("loc", []))
            errors.append({"field": field, "message": err.get("msg", "invalid value")})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "detail": "Request validation failed.",
                "fields": errors,
                "path": request.url.path,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all: log full traceback internally, return generic 500."""
        log.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred. Please try again later.",
                "path": request.url.path,
            },
        )


def _status_label(code: int) -> str:
    labels = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "unprocessable_entity",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
        503: "service_unavailable",
    }
    return labels.get(code, f"http_error_{code}")
