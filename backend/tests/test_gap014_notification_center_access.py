from __future__ import annotations

from fastapi import APIRouter

from app.core.module_registry import (
    ENDPOINT_ROUTE_DEFINITIONS,
    MODULE_DEFINITIONS,
    register_module_routes,
    registry_permission_codes,
)
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS

REQUIRED_PERMISSION_CODES = {
    "notifications.view",
    "notifications.manage",
    "notifications.send",
    "notifications.configure",
    "notifications.report",
    "notifications.admin",
}


# ── Registry / seed contract ───────────────────────────────────────────────────

def test_notifications_module_in_module_definitions_not_endpoint_routes():
    module_keys = {m.key for m in MODULE_DEFINITIONS}
    route_keys = {r.key for r in ENDPOINT_ROUTE_DEFINITIONS}

    assert "notifications" in module_keys, "notifications must be in MODULE_DEFINITIONS"
    assert "notifications" not in route_keys, "notifications must not be in ENDPOINT_ROUTE_DEFINITIONS"


def test_all_six_notification_permission_codes_in_registry():
    codes = registry_permission_codes()
    missing = REQUIRED_PERMISSION_CODES - codes
    assert not missing, f"registry missing: {missing}"


def test_all_six_notification_permission_codes_in_seed():
    seed_codes = {f"{module}.{action}" for module, action, *_ in PERMISSIONS}
    missing = REQUIRED_PERMISSION_CODES - seed_codes
    assert not missing, f"seed missing: {missing}"


def test_admin_role_has_all_notification_permissions():
    admin_perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    missing = REQUIRED_PERMISSION_CODES - admin_perms
    assert not missing, f"admin role missing: {missing}"


def test_admin_role_has_at_minimum_view_manage_admin():
    admin_perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    assert {"notifications.view", "notifications.manage", "notifications.admin"} <= admin_perms


# ── Route registration ─────────────────────────────────────────────────────────

def test_notification_routes_register_from_module_registry():
    router = APIRouter()
    diagnostics = register_module_routes(router, environment="development")
    paths = {route.path for route in router.routes}

    errors = [d for d in diagnostics if d.get("status") == "error"]
    assert not errors, f"module route errors: {errors}"
    assert any("/notifications" in p for p in paths), \
        f"no notification paths registered. paths={sorted(paths)[:10]}"


# ── Module definition properties ──────────────────────────────────────────────

def test_notifications_module_has_correct_permission_actions():
    nc_module = next((m for m in MODULE_DEFINITIONS if m.key == "notifications"), None)
    assert nc_module is not None, "notifications module not found"
    actions = set(nc_module.permission_actions)
    assert actions == {"view", "manage", "send", "configure", "report", "admin"}


def test_notifications_module_not_marked_critical():
    nc_module = next((m for m in MODULE_DEFINITIONS if m.key == "notifications"), None)
    assert nc_module is not None
    assert nc_module.critical is False


def test_notifications_module_route_prefix():
    nc_module = next((m for m in MODULE_DEFINITIONS if m.key == "notifications"), None)
    assert nc_module is not None
    assert nc_module.route_prefix == "/notifications"
