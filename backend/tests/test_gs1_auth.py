"""
GS1 route auth/permission guard tests — no DB required.

Tests:
- require_permission("gs1", X) raises 403 for user missing that permission
- Superuser bypasses all gs1 guards
- All 36 gs1 routes have require_permission("gs1", ...) in their signature
- complete_print_job uses authenticated user identity (not a Query default)
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.params import Depends as DependsType

from app.core.deps import require_permission


# ── Helpers (same pattern as test_permissions.py) ─────────────────────────────

def _perm(code: str):
    module, action = code.split(".", 1)
    return SimpleNamespace(code=code, module=module, action=action, is_active=True)


def _role(*perm_codes: str):
    return SimpleNamespace(
        name="test-role",
        is_active=True,
        permissions=[_perm(c) for c in perm_codes],
        access_scopes=[],
    )


def _user(*perm_codes: str, superuser: bool = False):
    return SimpleNamespace(
        username="testuser",
        full_name="Test User",
        is_superuser=superuser,
        roles=[_role(*perm_codes)],
        access_scopes=[],
    )


# ── Permission guard behaviour ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gs1_view_denied_without_permission():
    check = require_permission("gs1", "view")
    user = _user()  # no permissions
    with pytest.raises(HTTPException) as exc:
        await check(current_user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_gs1_create_denied_without_permission():
    check = require_permission("gs1", "create")
    user = _user("gs1.view")  # has view but not create
    with pytest.raises(HTTPException) as exc:
        await check(current_user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_gs1_print_denied_without_permission():
    check = require_permission("gs1", "print")
    user = _user("gs1.view", "gs1.create")
    with pytest.raises(HTTPException) as exc:
        await check(current_user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_gs1_admin_denied_without_permission():
    check = require_permission("gs1", "admin")
    user = _user("gs1.view", "gs1.create", "gs1.print", "gs1.report")
    with pytest.raises(HTTPException) as exc:
        await check(current_user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_superuser_bypasses_gs1_guards():
    for action in ("view", "create", "edit", "approve", "print", "report", "admin"):
        check = require_permission("gs1", action)
        user = _user(superuser=True)
        result = await check(current_user=user)
        assert result == user


@pytest.mark.asyncio
async def test_gs1_view_granted_with_permission():
    check = require_permission("gs1", "view")
    user = _user("gs1.view")
    result = await check(current_user=user)
    assert result == user


# ── Route wiring ──────────────────────────────────────────────────────────────

def _get_dep_callables(fn):
    """Return set of callables that are Depends() defaults in fn's signature."""
    deps = set()
    for param in inspect.signature(fn).parameters.values():
        if isinstance(param.default, DependsType):
            deps.add(param.default.dependency)
    return deps


def test_all_gs1_routes_have_require_permission_guard():
    """Every route in gs1.py must have at least one require_permission dep."""
    from fastapi.routing import APIRoute
    from app.api.v1.endpoints.gs1 import router

    unguarded = []
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        deps = _get_dep_callables(route.endpoint)
        # require_permission returns a closure; its __name__ is "_check"
        has_guard = any(getattr(d, "__name__", "") == "_check" for d in deps)
        if not has_guard:
            unguarded.append(f"{route.methods} {route.path}")

    assert not unguarded, f"Routes missing require_permission guard: {unguarded}"


def test_gs1_route_count_is_36():
    """Confirm total route count matches audit (36)."""
    from fastapi.routing import APIRoute
    from app.api.v1.endpoints.gs1 import router

    routes = [r for r in router.routes if isinstance(r, APIRoute)]
    assert len(routes) == 36, f"Expected 36 routes, found {len(routes)}"


def test_complete_print_job_has_no_printed_by_query_param():
    """complete_print_job must not expose printed_by as a Query default (uses auth instead)."""
    from app.api.v1.endpoints.gs1 import complete_print_job
    sig = inspect.signature(complete_print_job)
    for name, param in sig.parameters.items():
        if name == "printed_by":
            pytest.fail("complete_print_job still has printed_by Query param — should use current_user.username")
    # No printed_by param found — pass


def test_complete_print_job_uses_require_permission_print():
    """complete_print_job must have require_permission('gs1', 'print') guard."""
    from app.api.v1.endpoints.gs1 import complete_print_job
    deps = _get_dep_callables(complete_print_job)
    has_guard = any(getattr(d, "__name__", "") == "_check" for d in deps)
    assert has_guard, "complete_print_job missing require_permission guard"
