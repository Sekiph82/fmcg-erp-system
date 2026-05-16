"""GAP-020: Consumer Complaint and Recall Linkage focused contract tests."""
from __future__ import annotations

from pathlib import Path

from app.core.module_registry import (
    ENDPOINT_ROUTE_DEFINITIONS,
    MODULE_DEFINITIONS,
    registry_permission_codes,
)
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS


REQUIRED_ACTIONS = {
    "view",
    "create",
    "edit",
    "delete",
    "approve",
    "close",
    "link_recall",
    "export",
}
REQUIRED_CODES = {f"consumer_complaints.{action}" for action in REQUIRED_ACTIONS}
ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_consumer_complaints_is_module_owned_not_loose_route():
    module_keys = {m.key for m in MODULE_DEFINITIONS}
    route_keys = {r.key for r in ENDPOINT_ROUTE_DEFINITIONS}

    assert "consumer_complaints" in module_keys
    assert "consumer_complaints" not in route_keys


def test_consumer_complaints_registry_permission_codes_exist():
    codes = registry_permission_codes()
    missing = REQUIRED_CODES - codes
    assert not missing, f"registry missing {missing}"


def test_consumer_complaints_seed_permission_tuples_exist():
    seed_codes = {f"{module}.{action}" for module, action, *_ in PERMISSIONS}
    missing = REQUIRED_CODES - seed_codes
    assert not missing, f"seed missing {missing}"


def test_admin_role_has_full_consumer_complaint_permissions():
    admin_perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    missing = REQUIRED_CODES - admin_perms
    assert not missing, f"admin role missing {missing}"


def test_quality_manager_has_recall_linkage_but_not_delete():
    quality_manager_perms = set(ROLE_DEFINITIONS["quality_manager"]["permissions"])
    expected = {
        "consumer_complaints.view",
        "consumer_complaints.create",
        "consumer_complaints.edit",
        "consumer_complaints.approve",
        "consumer_complaints.close",
        "consumer_complaints.link_recall",
        "consumer_complaints.export",
    }
    assert expected <= quality_manager_perms
    assert "consumer_complaints.delete" not in quality_manager_perms


def test_non_recall_operational_roles_do_not_get_unsafe_permissions():
    for role_name in ("quality_officer", "sales_manager", "regional_sales_manager", "read_only_auditor"):
        perms = set(ROLE_DEFINITIONS[role_name]["permissions"])
        assert "consumer_complaints.delete" not in perms
        assert "consumer_complaints.link_recall" not in perms


def test_consumer_complaints_nav_uses_dedicated_permission():
    nav = _source("../frontend/src/components/nav-config.tsx")
    complaint_lines = [line for line in nav.splitlines() if "Consumer Complaints" in line]

    assert complaint_lines, "Consumer Complaints nav item not found"
    assert all('permission: "quality.view"' not in line for line in complaint_lines)
    assert any('permission: "consumer_complaints.view"' in line for line in complaint_lines)


def test_frontend_page_uses_page_and_action_guards():
    page = _source("../frontend/src/app/dashboard/quality/consumer-complaints/page.tsx")

    assert 'RequirePermission permission="consumer_complaints.view"' in page
    assert 'PermissionGuard permission="consumer_complaints.create"' in page
    assert 'PermissionGuard permission="consumer_complaints.edit"' in page


def test_endpoint_imports_cleanly():
    import app.api.v1.endpoints.consumer_complaints as endpoint

    assert endpoint.router is not None


def test_endpoint_uses_dedicated_action_permissions():
    endpoint = _source("app/api/v1/endpoints/consumer_complaints.py")

    for action in ("view", "create", "edit", "close", "link_recall"):
        assert f'"{action}"' in endpoint
    assert 'MODULE_KEY = "consumer_complaints"' in endpoint
    assert "quality.view" not in endpoint
