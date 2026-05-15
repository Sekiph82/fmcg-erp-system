from __future__ import annotations

from app.core.module_registry import MODULE_DEFINITIONS, registry_permission_codes


NAV_PERMISSION_KEYS = {
    # keys used in nav-config.tsx that must exist in registry_permission_codes()
    # only includes keys from modules promoted to MODULE_DEFINITIONS
    "reports.view",
    "reports.create",
    "reports.admin",
    "notifications.view",
    "notifications.manage",
    "notifications.configure",
    "notifications.report",
    "knowledge_base.view",
    "esign.view",
    "documents.view",
    "users.view",
    "roles.view",
    "inventory.view",
    # audit.view and wms.view are from ENDPOINT_ROUTE_DEFINITIONS modules (not MODULE_DEFINITIONS)
    # so they are not in registry_permission_codes() — checked in seed separately
}


def test_all_nav_permission_keys_exist_in_registry():
    codes = registry_permission_codes()
    missing = NAV_PERMISSION_KEYS - codes
    assert not missing, f"nav uses permission codes not in registry: {missing}"


def test_module_definitions_have_sidebar_groups():
    for module in MODULE_DEFINITIONS:
        assert module.sidebar_group, f"module '{module.key}' has no sidebar_group"


def test_module_definitions_have_route_prefixes():
    for module in MODULE_DEFINITIONS:
        assert module.route_prefix.startswith("/"), \
            f"module '{module.key}' route_prefix missing leading slash"


def test_no_duplicate_module_keys():
    keys = [m.key for m in MODULE_DEFINITIONS]
    assert len(keys) == len(set(keys)), f"duplicate module keys: {[k for k in keys if keys.count(k) > 1]}"


def test_no_duplicate_route_prefixes():
    prefixes = [m.route_prefix for m in MODULE_DEFINITIONS]
    assert len(prefixes) == len(set(prefixes)), \
        f"duplicate route prefixes: {[p for p in prefixes if prefixes.count(p) > 1]}"
