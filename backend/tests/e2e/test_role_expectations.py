from __future__ import annotations

from app.db.seed import DEFAULT_ROLE_ACCESS_SCOPES, ROLE_DEFINITIONS


def role_permissions(role_name: str) -> set[str]:
    return set(ROLE_DEFINITIONS[role_name]["permissions"])


def test_warehouse_manager_role_supports_broad_view_and_scoped_mutation():
    permissions = role_permissions("warehouse_manager")

    assert "inventory.view_all" in permissions
    assert "warehouses.view_all" in permissions
    assert "inventory.edit_own_scope" in permissions
    assert "inventory.adjust_own_scope" in permissions
    assert "inventory.receive_own_scope" in permissions
    assert "inventory.dispatch_own_scope" in permissions
    assert "inventory.adjust_all" not in permissions
    assert "inventory.edit_all" not in permissions


def test_operational_e2e_roles_do_not_receive_global_scopes_by_default():
    operational_roles = {
        "warehouse_manager",
        "production_manager",
        "quality_manager",
        "procurement_manager",
        "regional_sales_manager",
        "scoped_finance_manager",
        "read_only_auditor",
    }

    assert operational_roles.isdisjoint(DEFAULT_ROLE_ACCESS_SCOPES)
    assert {"owner", "admin"}.issubset(DEFAULT_ROLE_ACCESS_SCOPES)


def test_read_only_auditor_role_has_no_mutation_permissions():
    permissions = role_permissions("read_only_auditor")
    mutation_fragments = (
        ".create",
        ".edit",
        ".delete",
        ".approve",
        ".post",
        ".release",
        ".adjust",
        ".dispatch",
        ".receive",
    )

    assert "auditor.export" in permissions
    assert any(permission.endswith(".view_own_scope") for permission in permissions)
    assert not any(fragment in permission for permission in permissions for fragment in mutation_fragments)
