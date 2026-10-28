"""ASGI upload security checks for the bulk-import HTTP routes."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import bulk_import
from app.services.import_engine import ImportMode, ImportResult


class _FakeDatabase:
    async def commit(self) -> None:
        return None


class _FakeUser:
    id = uuid4()
    username = "synthetic-upload-test"
    roles: list = []


def _import_app(monkeypatch) -> FastAPI:
    app = FastAPI()
    app.include_router(bulk_import.router, prefix="/api/v1/bulk-import")
    app.dependency_overrides[bulk_import.get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[bulk_import.get_db] = lambda: _FakeDatabase()
    monkeypatch.setattr(bulk_import, "_get_adapter", lambda _module: object())

    async def allow_import(_perm_module, _action, _user, _db):
        return None

    monkeypatch.setattr(bulk_import, "_assert_perm", allow_import)

    async def successful_import(**kwargs):
        return ImportResult(
            total_rows=1,
            valid_rows=1,
            failed_rows=0,
            imported=kwargs["mode"] != ImportMode.VALIDATE_ONLY,
            import_mode=kwargs["mode"],
            module="products",
        )

    monkeypatch.setattr(bulk_import.import_engine, "run", successful_import)
    return app


@pytest.mark.parametrize(
    ("route", "form"),
    [
        ("validate", {}),
        ("import", {"mode": ImportMode.IMPORT_VALID_ONLY.value}),
    ],
)
@pytest.mark.asyncio
async def test_bulk_import_routes_reject_disallowed_mime(route, form, monkeypatch):
    app = _import_app(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/bulk-import/products/{route}",
            data=form,
            files={"file": ("payload.exe", b"MZ", "application/x-msdownload")},
        )
    assert response.status_code == 415, response.text


@pytest.mark.parametrize(
    ("route", "form"),
    [
        ("validate", {}),
        ("import", {"mode": ImportMode.IMPORT_VALID_ONLY.value}),
    ],
)
@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"sku,name\nA,Example\n", None),
        (b"MZ\x00\x90\x00binary", "text/csv"),
        (b"\xff\xfe\x00\x00binary", "text/plain"),
    ],
)
@pytest.mark.asyncio
async def test_bulk_import_routes_reject_missing_mime_and_binary_text(
    route, form, content, content_type, monkeypatch
):
    app = _import_app(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/bulk-import/products/{route}",
            data=form,
            files={"file": ("payload.csv", content, content_type)},
        )
    assert response.status_code == 415, response.text


@pytest.mark.parametrize(
    ("route", "form"),
    [
        ("validate", {}),
        ("import", {"mode": ImportMode.IMPORT_VALID_ONLY.value}),
    ],
)
@pytest.mark.asyncio
async def test_bulk_import_routes_enforce_size_limit(route, form, monkeypatch):
    monkeypatch.setattr(bulk_import, "MAX_BYTES_IMPORT", 8)
    app = _import_app(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/bulk-import/products/{route}",
            data=form,
            files={"file": ("oversized.csv", b"x" * 9, "text/csv")},
        )
    assert response.status_code == 413, response.text


@pytest.mark.parametrize(
    ("route", "form"),
    [
        ("validate", {}),
        ("import", {"mode": ImportMode.IMPORT_VALID_ONLY.value}),
    ],
)
@pytest.mark.asyncio
async def test_bulk_import_routes_pass_sanitized_name_to_engine(route, form, monkeypatch):
    captured = {}

    async def capture_import(**kwargs):
        captured.update(kwargs)
        return ImportResult(
            total_rows=1,
            valid_rows=1,
            failed_rows=0,
            imported=False,
            import_mode=kwargs["mode"],
            module="products",
        )

    app = _import_app(monkeypatch)
    monkeypatch.setattr(bulk_import.import_engine, "run", capture_import)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/bulk-import/products/{route}",
            data=form,
            files={"file": (r"..\uploads\unsafe.csv", b"sku,name\nA,Example\n", "text/csv")},
        )
    assert response.status_code == 200, response.text
    assert captured["file_name"] == "unsafe.csv"
