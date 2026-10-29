"""Bound document multipart bodies before Starlette spools uploaded files."""
from __future__ import annotations

import uuid
from typing import Any, Awaitable, Callable

from app.core.config import settings


_MULTIPART_OVERHEAD_BYTES = 1024 * 1024


def _is_document_upload(scope: dict[str, Any]) -> bool:
    if scope.get("type") != "http" or scope.get("method", "").upper() != "POST":
        return False
    parts = [part for part in scope.get("path", "").split("/") if part]
    return any(
        parts[index] == "documents"
        and parts[index + 2] == "file"
        and _is_uuid(parts[index + 1])
        for index in range(max(0, len(parts) - 2))
    )


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


class _UploadBodyTooLarge(Exception):
    pass


class DocumentUploadBodyLimitMiddleware:
    """Reject oversized document bodies before multipart parsing/spooling."""

    def __init__(self, app: Callable[..., Awaitable[None]]):
        self.app = app

    async def __call__(self, scope, receive, send):
        if not _is_document_upload(scope):
            await self.app(scope, receive, send)
            return

        max_body_bytes = settings.DOCUMENT_MAX_UPLOAD_BYTES + _MULTIPART_OVERHEAD_BYTES
        content_length = next(
            (value for key, value in scope.get("headers", []) if key.lower() == b"content-length"),
            None,
        )
        if content_length is not None:
            try:
                if int(content_length) > max_body_bytes:
                    await _send_too_large(send)
                    return
            except ValueError:
                # Invalid Content-Length is left to the HTTP server/parser; the
                # actual body counter below still enforces the maximum.
                pass

        received_bytes = 0

        async def bounded_receive():
            nonlocal received_bytes
            message = await receive()
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > max_body_bytes:
                    raise _UploadBodyTooLarge
            return message

        response_started = False

        async def track_response(message):
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, bounded_receive, track_response)
        except _UploadBodyTooLarge:
            if not response_started:
                await _send_too_large(send)


async def _send_too_large(send):
    body = b'{"detail":"The document request exceeds the configured upload limit"}'
    await send({
        "type": "http.response.start",
        "status": 413,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ],
    })
    await send({"type": "http.response.body", "body": body})
