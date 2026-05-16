"""GAP-025: Multi-Company / Multi-Branch / Franchise Scaling contract tests."""
from __future__ import annotations

from pathlib import Path

from app.core.module_registry import MODULE_DEFINITIONS, registry_permission_codes
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ACTIONS = {"view", "create", "edit", "delete", "export", "manage"}
REQUIRED_CODES = {f"company.{a}" for a in REQUIRED_ACTIONS}


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _frontend_src(relative_path: str) -> str:
    frontend_root = ROOT.parent / "frontend"
    return (frontend_root / relative_path).read_text(encoding="utf-8")


# ── Module registry ───────────────────────────────────────────────────────────

def test_company_is_module_definition():
    keys = {m.key for m in MODULE_DEFINITIONS}
    assert "company" in keys, "company not promoted to ModuleDefinition"


def test_company_not_in_endpoint_route_definitions():
    from app.core.module_registry import ENDPOINT_ROUTE_DEFINITIONS
    keys = {r.key for r in ENDPOINT_ROUTE_DEFINITIONS}
    assert "company" not in keys, "company still in ENDPOINT_ROUTE_DEFINITIONS"


def test_company_module_permission_actions():
    mod = next((m for m in MODULE_DEFINITIONS if m.key == "company"), None)
    assert mod is not None
    declared = set(mod.permission_actions)
    missing = REQUIRED_ACTIONS - declared
    assert not missing, f"company module missing permission_actions: {missing}"


# ── Permission seeds ──────────────────────────────────────────────────────────

def test_company_permission_tuples_exist():
    seeded = {f"{p[0]}.{p[1]}" for p in PERMISSIONS}
    missing = REQUIRED_CODES - seeded
    assert not missing, f"Missing company permission tuples in seed: {missing}"


def test_company_registry_permission_codes():
    all_codes = registry_permission_codes()
    missing = REQUIRED_CODES - all_codes
    assert not missing, f"registry_permission_codes missing: {missing}"


# ── Role grants ───────────────────────────────────────────────────────────────

def test_admin_has_full_company_permissions():
    perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    missing = REQUIRED_CODES - perms
    assert not missing, f"admin missing company permissions: {missing}"


def test_company_admin_has_manage():
    perms = set(ROLE_DEFINITIONS["company_admin"]["permissions"])
    required = {"company.view", "company.edit", "company.manage"}
    missing = required - perms
    assert not missing, f"company_admin missing: {missing}"


def test_ceo_has_company_view_export():
    perms = set(ROLE_DEFINITIONS["ceo"]["permissions"])
    required = {"company.view", "company.export"}
    missing = required - perms
    assert not missing, f"ceo missing: {missing}"


def test_coo_has_company_view():
    perms = set(ROLE_DEFINITIONS["coo"]["permissions"])
    assert "company.view" in perms, "coo missing company.view"


def test_cto_has_company_view():
    perms = set(ROLE_DEFINITIONS["cto"]["permissions"])
    assert "company.view" in perms, "cto missing company.view"


# ── Endpoint source guards ────────────────────────────────────────────────────

def test_company_endpoints_use_require_permission():
    src = _source("app/api/v1/endpoints/company.py")
    assert "require_permission" in src
    assert "admin" not in src or 'require_permission("admin"' not in src, \
        "company.py still uses require_permission('admin', ...) instead of company.*"


def test_company_endpoints_no_bare_get_current_user_in_route():
    src = _source("app/api/v1/endpoints/company.py")
    assert 'Depends(get_current_user)' not in src, \
        "company.py still has bare Depends(get_current_user) in route signatures"


def test_company_endpoints_view_guard_present():
    src = _source("app/api/v1/endpoints/company.py")
    assert 'require_permission("company", "view")' in src


def test_company_endpoints_manage_guard_present():
    src = _source("app/api/v1/endpoints/company.py")
    assert 'require_permission("company", "manage")' in src


def test_company_endpoints_edit_guard_present():
    src = _source("app/api/v1/endpoints/company.py")
    assert 'require_permission("company", "edit")' in src


def test_company_endpoints_ownership_check_present():
    src = _source("app/api/v1/endpoints/company.py")
    assert "_check_company_access" in src


# ── ORM model imports ─────────────────────────────────────────────────────────

def test_company_orm_models_importable():
    from app.models.company import Company, Branch, UserCompanyAccess, CompanyUserRole
    assert Company.__tablename__ == "companies"
    assert Branch.__tablename__ == "branches"
    assert UserCompanyAccess.__tablename__ == "user_company_access"


def test_warehouse_has_company_id():
    from app.models.master import Warehouse
    assert hasattr(Warehouse, "company_id"), "Warehouse missing company_id"
    assert hasattr(Warehouse, "branch_id"), "Warehouse missing branch_id"


def test_warehouse_schema_has_company_id():
    from app.schemas.master import WarehouseBase
    import inspect
    fields = WarehouseBase.model_fields
    assert "company_id" in fields, "WarehouseBase missing company_id"
    assert "branch_id" in fields, "WarehouseBase missing branch_id"


# ── Migration file ────────────────────────────────────────────────────────────

def test_warehouse_reconciliation_migration_exists():
    migrations = list((ROOT / "alembic" / "versions").glob("*warehouse*reconciliation*"))
    assert migrations, "No warehouse reconciliation migration found"


def test_warehouse_migration_adds_company_id():
    src = _source("alembic/versions/20260516_0050_multi_company_warehouse_reconciliation.py")
    assert "company_id" in src
    assert "branch_id" in src
    assert "warehouses" in src


# ── Frontend guards ───────────────────────────────────────────────────────────

def test_companies_page_has_require_permission():
    src = _frontend_src("src/app/dashboard/companies/page.tsx")
    assert "RequirePermission" in src
    assert "company.view" in src
