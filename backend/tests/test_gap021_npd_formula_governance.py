"""GAP-021: NPD / formula governance focused contract tests."""
from __future__ import annotations

from pathlib import Path

from app.core.module_registry import (
    ENDPOINT_ROUTE_DEFINITIONS,
    MODULE_DEFINITIONS,
    registry_permission_codes,
)
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ACTIONS = {
    "npd": {"view", "create", "edit", "approve", "advance", "pilot", "export"},
    "bom": {"view", "create", "edit", "delete", "approve", "release", "archive", "cost", "ai", "export"},
    "recipe": {"view", "create", "edit", "delete", "approve", "obsolete", "export"},
}
REQUIRED_CODES = {
    f"{module}.{action}"
    for module, actions in REQUIRED_ACTIONS.items()
    for action in actions
}


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_npd_bom_recipe_are_module_owned_not_loose_routes():
    modules = {module.key: module for module in MODULE_DEFINITIONS}
    endpoint_imports = {route.import_path for route in ENDPOINT_ROUTE_DEFINITIONS}

    assert {"npd", "bom", "recipe"} <= set(modules)
    assert modules["npd"].route_prefix == "/npd-workflow"
    assert modules["bom"].route_prefix == "/bom"
    assert modules["recipe"].route_prefix == "/recipes"
    assert "app.api.v1.endpoints.npd_workflow" not in endpoint_imports
    assert "app.api.v1.endpoints.bom" not in endpoint_imports
    assert "app.api.v1.endpoints.recipes" not in endpoint_imports


def test_registry_permission_codes_include_required_governance_actions():
    missing = REQUIRED_CODES - registry_permission_codes()
    assert not missing, f"registry missing {missing}"


def test_seed_permission_tuples_include_required_governance_actions():
    seed_codes = {f"{module}.{action}" for module, action, *_ in PERMISSIONS}
    missing = REQUIRED_CODES - seed_codes
    assert not missing, f"seed missing {missing}"


def test_admin_role_has_full_npd_bom_recipe_permissions():
    admin_perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    missing = REQUIRED_CODES - admin_perms
    assert not missing, f"admin role missing {missing}"


def test_operational_roles_do_not_receive_destructive_formula_permissions():
    unsafe = {"bom.delete", "recipe.delete", "bom.ai"}

    for role_name in ("production_manager", "quality_manager", "factory_manager", "read_only_auditor"):
        perms = set(ROLE_DEFINITIONS[role_name]["permissions"])
        assert not (unsafe & perms), f"{role_name} has unsafe grants: {unsafe & perms}"


def test_quality_manager_has_approval_visibility_but_not_mutation_overreach():
    perms = set(ROLE_DEFINITIONS["quality_manager"]["permissions"])

    assert {"npd.view", "npd.approve", "bom.view", "bom.approve", "bom.release", "recipe.view", "recipe.approve"} <= perms
    assert "npd.advance" not in perms
    assert "npd.pilot" not in perms
    assert "bom.create" not in perms
    assert "recipe.create" not in perms


def test_frontend_navigation_uses_dedicated_permissions():
    nav = _source("../frontend/src/components/nav-config.tsx")

    assert '{ label: "Recipes / BOM", href: "/dashboard/recipes",         permission: "recipe.view" }' in nav
    assert 'label: "New Product Development"' in nav
    assert '{ label: "NPD Projects",    href: "/dashboard/npd",   permission: "npd.view" }' in nav
    assert '{ label: "BOM Master",          href: "/dashboard/bom",            permission: "bom.view" }' in nav
    assert '{ label: "Conversion Profiles", href: "/dashboard/bom/conversion", permission: "bom.view" }' in nav
    assert "New Product Development" in nav
    assert "BOM Master" in nav


def test_frontend_pages_use_page_and_action_guards():
    frontend_expectations = {
        "../frontend/src/app/dashboard/npd/page.tsx": [
            'RequirePermission permission="npd.view"',
            'PermissionGuard permission="npd.create"',
        ],
        "../frontend/src/app/dashboard/npd/[id]/page.tsx": [
            'RequirePermission permission="npd.view"',
            'PermissionGuard permission="npd.advance"',
            'PermissionGuard permission="npd.approve"',
            'PermissionGuard permission="npd.pilot"',
        ],
        "../frontend/src/app/dashboard/bom/page.tsx": [
            'RequirePermission permission="bom.view"',
            'PermissionGuard permission="bom.create"',
        ],
        "../frontend/src/app/dashboard/bom/[id]/page.tsx": [
            'RequirePermission permission="bom.view"',
            'PermissionGuard permission="bom.ai"',
            'PermissionGuard permission="bom.archive"',
        ],
        "../frontend/src/app/dashboard/recipes/page.tsx": [
            'RequirePermission permission="recipe.view"',
            'PermissionGuard permission="recipe.create"',
            'PermissionGuard permission="recipe.delete"',
        ],
        "../frontend/src/app/dashboard/recipes/[id]/page.tsx": [
            'RequirePermission permission="recipe.view"',
            'PermissionGuard permission="recipe.approve"',
            'PermissionGuard permission="recipe.obsolete"',
        ],
    }

    for relative_path, expected_snippets in frontend_expectations.items():
        source = _source(relative_path)
        for snippet in expected_snippets:
            assert snippet in source, f"{relative_path} missing {snippet}"


def test_endpoint_modules_import_cleanly():
    import app.api.v1.endpoints.bom as bom_endpoint
    import app.api.v1.endpoints.npd_workflow as npd_endpoint
    import app.api.v1.endpoints.recipes as recipes_endpoint

    assert bom_endpoint.router is not None
    assert npd_endpoint.router is not None
    assert recipes_endpoint.router is not None


def test_endpoints_use_dedicated_permission_dependencies():
    endpoint_expectations = {
        "app/api/v1/endpoints/npd_workflow.py": [
            'require_permission("npd", "view")',
            'require_permission("npd", "create")',
            'require_permission("npd", "edit")',
            'require_permission("npd", "approve")',
            'require_permission("npd", "advance")',
            'require_permission("npd", "pilot")',
        ],
        "app/api/v1/endpoints/bom.py": [
            'require_permission("bom", "view")',
            'require_permission("bom", "create")',
            'require_permission("bom", "edit")',
            'require_permission("bom", "delete")',
            'require_permission("bom", "archive")',
            'require_permission("bom", "cost")',
            'require_permission("bom", "ai")',
            'f"bom.{action}"',
        ],
        "app/api/v1/endpoints/recipes.py": [
            'require_permission("recipe", "view")',
            'require_permission("recipe", "create")',
            'require_permission("recipe", "edit")',
            'require_permission("recipe", "delete")',
            'require_permission("recipe", "approve")',
            'require_permission("recipe", "obsolete")',
        ],
    }

    for relative_path, expected_snippets in endpoint_expectations.items():
        source = _source(relative_path)
        for snippet in expected_snippets:
            assert snippet in source, f"{relative_path} missing {snippet}"
        assert "production.view" not in source


def test_reconciliation_migration_owns_expected_tables_and_merges_heads():
    migration = _source("alembic/versions/20260516_0010_npd_formula_governance_reconciliation.py")

    assert 'revision = "20260516_0010"' in migration
    assert 'down_revision = ("20260515_0040", "20260515_0060")' in migration
    for table_name in (
        "npd_projects",
        "npd_stage_gates",
        "npd_pilot_batches",
        "recipes",
        "recipe_items",
        "process_parameters",
        "advanced_boms",
        "advanced_bom_lines",
        "bom_ai_recs",
    ):
        assert table_name in migration
