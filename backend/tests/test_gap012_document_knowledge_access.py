from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import APIRouter

from app.core.module_registry import (
    ENDPOINT_ROUTE_DEFINITIONS,
    MODULE_DEFINITIONS,
    register_module_routes,
    registry_permission_codes,
)
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS
from app.services.document_access_service import build_document_access_hint, can_modify_document
from app.services.esignature_service import build_signature_access_hint, can_sign_request, request_is_expired
from app.services.knowledge_base_service import can_modify_article, can_view_article


class Permission(SimpleNamespace):
    is_active = True


class Role(SimpleNamespace):
    is_active = True


def make_user(user_id: str = "user-1", permissions: tuple[str, ...] = (), superuser: bool = False):
    role = Role(
        permissions=[Permission(code=code) for code in permissions],
        access_scopes=[],
    )
    return SimpleNamespace(
        id=user_id,
        is_superuser=superuser,
        roles=[role],
        access_scopes=[],
    )


def test_document_lifecycle_separates_view_and_mutation():
    viewer = make_user(permissions=("documents.view",))
    editor = make_user(permissions=("documents.view", "documents.edit"))
    approver = make_user(permissions=("documents.view", "documents.approve"))
    draft = SimpleNamespace(status="DRAFT", file_locked=False, legal_hold=False)
    approved = SimpleNamespace(status="APPROVED", file_locked=True, legal_hold=False)

    assert build_document_access_hint(viewer, draft)["view_only"] is True
    assert can_modify_document(editor, draft, "edit") is True
    assert can_modify_document(editor, approved, "edit") is False
    assert can_modify_document(approver, draft, "approve") is True
    assert can_modify_document(approver, approved, "archive") is True


def test_knowledge_base_publish_requires_dedicated_permission():
    viewer = make_user(permissions=("knowledge_base.view",))
    editor = make_user(permissions=("knowledge_base.view", "knowledge_base.edit"))
    publisher = make_user(permissions=("knowledge_base.view", "knowledge_base.publish"))
    draft = SimpleNamespace(status="DRAFT", author_id="author-1")
    published = SimpleNamespace(status="PUBLISHED", author_id="author-1")

    assert can_view_article(viewer, published) is True
    assert can_modify_article(editor, draft, "publish") is False
    assert can_modify_article(publisher, draft, "publish") is True
    assert can_modify_article(publisher, published, "publish") is False


def test_esign_signing_requires_pending_signer_and_non_expired_request():
    signer = make_user("signer-1", permissions=("esign.sign",))
    other = make_user("other-1", permissions=("esign.sign",))
    pending_record = SimpleNamespace(signer_id="signer-1", status="PENDING")
    request = SimpleNamespace(
        status="PENDING",
        requester_id="requester-1",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        signature_records=[pending_record],
    )
    expired = SimpleNamespace(
        status="PENDING",
        requester_id="requester-1",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        signature_records=[pending_record],
    )

    assert request_is_expired(request) is False
    assert can_sign_request(signer, request) is True
    assert can_sign_request(other, request) is False
    assert can_sign_request(signer, expired) is False
    assert build_signature_access_hint(signer, request)["can_sign"] is True


def test_document_knowledge_esign_permissions_are_registry_and_seed_owned():
    required = {
        "documents.view",
        "documents.create",
        "documents.edit",
        "documents.approve",
        "documents.archive",
        "documents.export",
        "knowledge_base.view",
        "knowledge_base.create",
        "knowledge_base.edit",
        "knowledge_base.publish",
        "knowledge_base.delete",
        "knowledge_base.admin",
        "esign.view",
        "esign.request",
        "esign.sign",
        "esign.cancel",
        "esign.admin",
    }
    modules = {module.key for module in MODULE_DEFINITIONS}
    seed_codes = {f"{module}.{action}" for module, action, *_ in PERMISSIONS}

    assert {"documents", "knowledge_base", "esign"} <= modules
    assert not any(route.key in {"documents", "knowledge_base", "esign"} for route in ENDPOINT_ROUTE_DEFINITIONS)
    assert required <= registry_permission_codes()
    assert required <= seed_codes
    assert {"knowledge_base.view", "esign.view"} <= set(ROLE_DEFINITIONS["admin"]["permissions"])


def test_document_knowledge_esign_routes_register_from_module_registry():
    router = APIRouter()
    diagnostics = register_module_routes(router, environment="development")
    paths = {route.path for route in router.routes}

    assert not [item for item in diagnostics if item.get("status") == "error"]
    assert any(path.startswith("/documents") for path in paths)
    assert any(path.startswith("/kb") for path in paths)
    assert any(path.startswith("/esign") for path in paths)
