"""Document management access and lifecycle helpers."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.core.access_control import can_modify_record, can_view_record, forbidden_detail, has_permission, permission_code


DOCUMENT_ACTION_STATUSES: dict[str, set[str]] = {
    "edit": {"DRAFT"},
    "approve": {"DRAFT"},
    "archive": {"APPROVED", "OBSOLETE"},
    "obsolete": {"APPROVED"},
    "new_version": {"APPROVED", "OBSOLETE"},
    "delete": set(),
    "export": {"DRAFT", "APPROVED", "OBSOLETE", "ARCHIVED"},
}


def document_status(record: Any) -> str | None:
    value = getattr(record, "status", None)
    if value is None:
        return None
    return str(getattr(value, "value", value)).upper()


def document_is_locked(record: Any) -> bool:
    return bool(getattr(record, "file_locked", False)) or bool(getattr(record, "legal_hold", False))


def can_change_document_status(record: Any, action: str) -> bool:
    allowed_statuses = DOCUMENT_ACTION_STATUSES.get(action)
    if allowed_statuses is None:
        return True
    if not allowed_statuses:
        return False
    return document_status(record) in allowed_statuses


def can_view_document(user: Any, document: Any) -> bool:
    return can_view_record(user, "documents", document)


def can_modify_document(user: Any, document: Any, action: str) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    if action in {"edit", "delete"} and document_is_locked(document):
        return False
    if not can_change_document_status(document, action):
        return False
    if has_permission(user, permission_code("documents", action)):
        return True
    if action in {"archive", "obsolete"} and has_permission(user, permission_code("documents", "approve")):
        return True
    return can_modify_record(user, "documents", action, document)


def build_document_access_hint(user: Any, document: Any) -> dict[str, Any]:
    can_view = can_view_document(user, document)
    actions = {
        "can_edit": can_modify_document(user, document, "edit"),
        "can_approve": can_modify_document(user, document, "approve"),
        "can_archive": can_modify_document(user, document, "archive"),
        "can_obsolete": can_modify_document(user, document, "obsolete"),
        "can_new_version": can_modify_document(user, document, "new_version"),
        "can_export": can_modify_document(user, document, "export"),
        "can_delete": can_modify_document(user, document, "delete"),
    }
    mutation_allowed = any(actions.values())
    reason = None
    if can_view and not mutation_allowed:
        reason = "You can view this document but cannot modify it in this scope or lifecycle status."
    return {
        "can_view": can_view,
        "view_only": can_view and not mutation_allowed,
        "reason": reason,
        **actions,
    }


def ensure_document_action_allowed(user: Any, document: Any, action: str) -> dict[str, Any]:
    allowed = can_view_document(user, document) if action == "view" else can_modify_document(user, document, action)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=forbidden_detail("You can view this document only if your permissions and scopes allow it."),
        )
    return build_document_access_hint(user, document)
