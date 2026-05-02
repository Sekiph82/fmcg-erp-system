"""
Security headers middleware.

Adds OWASP-recommended HTTP response headers to every response:
  - Strict-Transport-Security (HSTS)
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Referrer-Policy
  - Content-Security-Policy (relaxed for API — no HTML served)
  - Permissions-Policy
  - Cache-Control for sensitive endpoints
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Endpoints whose responses must never be cached
_NO_CACHE_PREFIXES = ("/api/v1/auth", "/api/v1/users", "/api/v1/roles", "/api/v1/ai")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # ── Standard security headers ──────────────────────────────────────────
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        # HSTS — only meaningful behind TLS; safe to send always
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # CSP — API only, no HTML; keep it tight
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )

        # ── Cache control for auth/sensitive endpoints ─────────────────────────
        path = request.url.path
        if any(path.startswith(p) for p in _NO_CACHE_PREFIXES):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response
