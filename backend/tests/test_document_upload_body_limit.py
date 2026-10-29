from __future__ import annotations

import uuid

import pytest

from app.core.config import settings
from app.core.document_upload_limit import DocumentUploadBodyLimitMiddleware


def _scope(path: str, method: str = "POST", headers=()):
    return {"type": "http", "method": method, "path": path, "headers": list(headers)}


@pytest.mark.asyncio
async def test_document_upload_content_length_is_rejected_before_multipart_parser(monkeypatch):
    monkeypatch.setattr(settings, "DOCUMENT_MAX_UPLOAD_BYTES", 8)
    entered_app = False

    async def downstream(scope, receive, send):
        nonlocal entered_app
        entered_app = True

    events = []
    async def send(message):
        events.append(message)

    async def receive():
        pytest.fail("An oversized Content-Length must be rejected without reading or parsing the body")

    middleware = DocumentUploadBodyLimitMiddleware(downstream)
    await middleware(
        _scope(
            f"/api/v1/documents/{uuid.uuid4()}/file",
            headers=[(b"content-length", str(8 + 1024 * 1024 + 1).encode("ascii"))],
        ),
        receive,
        send,
    )

    assert not entered_app
    assert events[0]["status"] == 413


@pytest.mark.asyncio
async def test_chunked_document_upload_is_bounded_before_parser_can_spool_more(monkeypatch):
    monkeypatch.setattr(settings, "DOCUMENT_MAX_UPLOAD_BYTES", 8)
    body = b"x" * (8 + 1024 * 1024 + 1)
    entered_parser = False

    async def downstream(scope, receive, send):
        nonlocal entered_parser
        entered_parser = True
        await receive()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    events = []
    async def send(message):
        events.append(message)

    middleware = DocumentUploadBodyLimitMiddleware(downstream)
    await middleware(_scope(f"/api/v1/documents/{uuid.uuid4()}/file"), receive, send)

    assert entered_parser
    assert events[0]["status"] == 413
    assert b"configured upload limit" in events[1]["body"]


@pytest.mark.asyncio
async def test_limit_does_not_intercept_other_requests(monkeypatch):
    monkeypatch.setattr(settings, "DOCUMENT_MAX_UPLOAD_BYTES", 8)
    entered_app = False

    async def downstream(scope, receive, send):
        nonlocal entered_app
        entered_app = True

    async def receive():
        return {"type": "http.request", "body": b"x" * 100, "more_body": False}

    async def send(_message):
        pass

    middleware = DocumentUploadBodyLimitMiddleware(downstream)
    await middleware(_scope("/api/v1/documents", headers=[(b"content-length", b"99999999")]), receive, send)

    assert entered_app
