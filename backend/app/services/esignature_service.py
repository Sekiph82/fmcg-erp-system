"""Electronic-signature access and workflow helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.access_control import can_modify_record, can_view_record, forbidden_detail, has_permission, permission_code


def _status_value(record: Any, default: str = "PENDING") -> str:
    value = getattr(record, "status", default)
    return str(getattr(value, "value", value)).upper()


def _user_id(user: Any) -> str:
    return str(getattr(user, "id", ""))


def _record_signer_id(record: Any) -> str:
    return str(getattr(record, "signer_id", ""))


def request_is_pending(request: Any) -> bool:
    return _status_value(request) == "PENDING"


def request_is_expired(request: Any, now: datetime | None = None) -> bool:
    expires_at = getattr(request, "expires_at", None)
    if expires_at is None:
        return False
    current_time = now or datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        current_time = current_time.replace(tzinfo=None)
    return expires_at <= current_time


def user_is_requester(user: Any, request: Any) -> bool:
    return str(getattr(request, "requester_id", "")) == _user_id(user)


def user_is_signer(user: Any, request: Any) -> bool:
    return any(_record_signer_id(record) == _user_id(user) for record in getattr(request, "signature_records", []) or [])


def pending_signature_record_for_user(user: Any, request: Any) -> Any | None:
    for record in getattr(request, "signature_records", []) or []:
        if _record_signer_id(record) == _user_id(user) and _status_value(record) == "PENDING":
            return record
    return None


def can_view_signature_request(user: Any, request: Any) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    if has_permission(user, permission_code("esign", "admin")) or has_permission(user, permission_code("esign", "view")):
        return True
    if user_is_requester(user, request) or user_is_signer(user, request):
        return True
    return can_view_record(user, "esign", request)


def can_create_signature_request(user: Any, request_scope: Any | None = None) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    if has_permission(user, permission_code("esign", "request")):
        return True
    if request_scope is not None:
        return can_modify_record(user, "esign", "request", request_scope)
    return False


def can_sign_request(user: Any, request: Any, now: datetime | None = None) -> bool:
    if not request_is_pending(request):
        return False
    if request_is_expired(request, now):
        return False
    if pending_signature_record_for_user(user, request) is None:
        return False
    return getattr(user, "is_superuser", False) or has_permission(user, permission_code("esign", "sign")) or user_is_signer(user, request)


def can_cancel_signature_request(user: Any, request: Any) -> bool:
    if not request_is_pending(request):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if has_permission(user, permission_code("esign", "admin")):
        return True
    return user_is_requester(user, request) and has_permission(user, permission_code("esign", "cancel"))


def build_signature_access_hint(user: Any, request: Any) -> dict[str, Any]:
    can_view = can_view_signature_request(user, request)
    actions = {
        "can_sign": can_sign_request(user, request),
        "can_decline": can_sign_request(user, request),
        "can_cancel": can_cancel_signature_request(user, request),
        "can_admin": getattr(user, "is_superuser", False) or has_permission(user, permission_code("esign", "admin")),
    }
    reason = None
    if can_view and not any(actions.values()):
        reason = "You can view this signature request but cannot act on it in this status or scope."
    return {
        "can_view": can_view,
        "view_only": can_view and not any(actions.values()),
        "reason": reason,
        **actions,
    }


def ensure_signature_action_allowed(user: Any, request: Any, action: str) -> dict[str, Any]:
    if action == "view":
        allowed = can_view_signature_request(user, request)
    elif action in {"sign", "decline"}:
        allowed = can_sign_request(user, request)
    elif action == "cancel":
        allowed = can_cancel_signature_request(user, request)
    else:
        allowed = can_modify_record(user, "esign", action, request)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=forbidden_detail("You can view this signature request only if your role in the workflow allows it."),
        )
    return build_signature_access_hint(user, request)
