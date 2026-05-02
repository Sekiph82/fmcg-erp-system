"""
Input sanitization middleware.

Strips dangerous patterns from incoming request bodies before they reach route handlers.
Works on JSON bodies. Does NOT block requests — sanitizes in place.

Protections:
  - HTML/script tag stripping (XSS)
  - Null byte removal
  - Oversized string truncation (per-field 10 KB limit)
  - Control character stripping

Note: SQL injection is prevented at the ORM layer (SQLAlchemy parameterized queries).
This middleware adds defense-in-depth at the HTTP layer.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger(__name__)

# Endpoints that serve raw binary/files — skip sanitization
_SKIP_PATHS = {"/api/v1/bulk-import", "/api/v1/gs1", "/api/v1/documents"}

_FIELD_MAX_CHARS = 10_000          # max chars per string field
_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]{0,200}>")   # strip any HTML tag (bounded to avoid ReDoS)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")  # control chars (keep \t\n\r)


def _sanitize_value(v: Any) -> Any:
    if isinstance(v, str):
        v = v.replace("\x00", "")           # null bytes
        v = _SCRIPT_RE.sub("", v)           # <script> blocks
        v = _TAG_RE.sub("", v)              # remaining HTML tags
        v = _CONTROL_RE.sub("", v)          # control characters
        if len(v) > _FIELD_MAX_CHARS:
            log.warning("Input truncated: original length=%d", len(v))
            v = v[:_FIELD_MAX_CHARS]
        return v
    if isinstance(v, dict):
        return {k: _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(item) for item in v]
    return v


class InputSanitizerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Only sanitize JSON bodies on mutating methods
        if request.method in ("POST", "PUT", "PATCH") and "application/json" in (
            request.headers.get("content-type", "")
        ):
            path = request.url.path
            if not any(path.startswith(skip) for skip in _SKIP_PATHS):
                try:
                    raw = await request.body()
                    if raw:
                        parsed = json.loads(raw)
                        sanitized = _sanitize_value(parsed)
                        sanitized_bytes = json.dumps(sanitized).encode()
                        # Re-inject sanitized body
                        async def receive():
                            return {"type": "http.request", "body": sanitized_bytes, "more_body": False}
                        request._receive = receive
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass  # let FastAPI's validation handle malformed JSON

        return await call_next(request)
