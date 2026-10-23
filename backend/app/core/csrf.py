"""Origin validation for browser-initiated state-changing requests."""
from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class CSRFOriginMiddleware(BaseHTTPMiddleware):
    """Reject unsafe browser requests whose Origin/Referer is not trusted.

    Non-browser API clients that omit both headers remain compatible. Browsers
    send Origin on state-changing fetches and form posts; Referer is a fallback
    for clients that omit Origin.
    """

    def __init__(self, app, allowed_origins: list[str]):
        super().__init__(app)
        self.allowed_origins = frozenset(allowed_origins)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            if origin is None and referer:
                parsed = urlsplit(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "null"
            if origin is not None and origin not in self.allowed_origins:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-site state-changing request blocked"},
                )
        return await call_next(request)
