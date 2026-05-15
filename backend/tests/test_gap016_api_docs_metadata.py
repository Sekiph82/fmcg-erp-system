from __future__ import annotations

from app.main import app


def _schema():
    return app.openapi()


def test_openapi_has_title():
    info = _schema().get("info", {})
    assert info.get("title"), "OpenAPI schema missing title"


def test_openapi_has_version():
    info = _schema().get("info", {})
    assert info.get("version"), "OpenAPI schema missing version"


def test_openapi_has_description():
    info = _schema().get("info", {})
    desc = info.get("description", "")
    assert desc, "OpenAPI schema missing description"
    assert "Authentication" in desc, "description should mention Authentication"
    assert "Permissions" in desc, "description should mention Permissions"


def test_openapi_has_contact():
    info = _schema().get("info", {})
    contact = info.get("contact", {})
    assert contact, "OpenAPI schema missing contact"
    assert contact.get("email"), "OpenAPI contact missing email"


def test_openapi_has_license_info():
    info = _schema().get("info", {})
    assert info.get("license"), "OpenAPI schema missing license_info"


def test_module_manifest_route_has_summary():
    paths = _schema().get("paths", {})
    manifest = paths.get("/api/v1/modules/manifest", {})
    get_op = manifest.get("get", {})
    assert get_op.get("summary"), "GET /modules/manifest missing summary"
