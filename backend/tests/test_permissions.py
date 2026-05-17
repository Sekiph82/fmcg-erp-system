"""Permission enforcement unit tests — no DB required."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.access_control import has_permission, has_any_permission, forbidden_detail
from app.core.deps import require_permission


# ── Helpers ────────────────────────────────────────────────────────────────────

def _perm(code: str):
    module, action = code.split(".", 1)
    return SimpleNamespace(code=code, module=module, action=action, is_active=True)


def _role(name: str, *perm_codes: str, active: bool = True):
    return SimpleNamespace(
        name=name,
        is_active=active,
        permissions=[_perm(c) for c in perm_codes],
        access_scopes=[],
    )


def _user(*perm_codes: str, superuser: bool = False):
    return SimpleNamespace(
        is_superuser=superuser,
        roles=[_role("test-role", *perm_codes)],
        access_scopes=[],
    )


# ── has_permission ─────────────────────────────────────────────────────────────

def test_superuser_has_all_permissions():
    u = _user(superuser=True)
    assert has_permission(u, "inventory.delete") is True
    assert has_permission(u, "finance.post") is True


def test_user_with_exact_permission_is_granted():
    u = _user("inventory.view", "sales.create")
    assert has_permission(u, "inventory.view") is True
    assert has_permission(u, "sales.create") is True


def test_user_without_permission_is_denied():
    u = _user("inventory.view")
    assert has_permission(u, "inventory.delete") is False
    assert has_permission(u, "finance.post") is False


def test_no_roles_user_is_denied():
    u = SimpleNamespace(is_superuser=False, roles=[], access_scopes=[])
    assert has_permission(u, "inventory.view") is False


def test_inactive_role_permissions_not_granted():
    u = SimpleNamespace(
        is_superuser=False,
        roles=[_role("inactive-role", "inventory.view", active=False)],
        access_scopes=[],
    )
    assert has_permission(u, "inventory.view") is False


def test_has_any_permission_true_when_one_matches():
    u = _user("inventory.view", "sales.create")
    assert has_any_permission(u, ["finance.post", "sales.create"]) is True


def test_has_any_permission_false_when_none_match():
    u = _user("inventory.view")
    assert has_any_permission(u, ["finance.post", "sales.create"]) is False


# ── forbidden_detail ───────────────────────────────────────────────────────────

def test_forbidden_detail_contains_reason():
    detail = forbidden_detail("Permission 'inventory.delete' required")
    assert "inventory.delete" in str(detail)


# ── require_permission dependency ─────────────────────────────────────────────
#
# require_permission() returns an inner async _check(current_user=Depends(...))
# function. Calling it directly with current_user=<user> bypasses FastAPI DI,
# letting us unit-test the permission logic without a real DB or test client.

def test_require_permission_grants_user_with_permission():
    check = require_permission("inventory", "view")
    u = _user("inventory.view")
    result = asyncio.run(check(current_user=u))
    assert result is u


def test_require_permission_raises_403_when_user_lacks_permission():
    check = require_permission("inventory", "delete")
    u = _user("inventory.view")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(check(current_user=u))
    assert exc_info.value.status_code == 403


def test_require_permission_grants_superuser_any_permission():
    check = require_permission("finance", "post")
    u = _user(superuser=True)
    result = asyncio.run(check(current_user=u))
    assert result is u


def test_require_permission_403_detail_names_the_permission():
    check = require_permission("sales", "approve")
    u = _user("inventory.view")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(check(current_user=u))
    assert "sales.approve" in str(exc_info.value.detail)
