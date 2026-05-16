"""GAP-023: ML-Based Predictive Maintenance focused contract tests."""
from __future__ import annotations

from pathlib import Path

from app.core.module_registry import (
    MODULE_DEFINITIONS,
    registry_permission_codes,
)
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ACTIONS = {"view", "create", "edit", "delete", "predict", "review_prediction", "export"}
REQUIRED_CODES = {f"maintenance.{a}" for a in REQUIRED_ACTIONS}


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


# ── Module registry ───────────────────────────────────────────────────────────

def test_maintenance_is_module_definition():
    keys = {m.key for m in MODULE_DEFINITIONS}
    assert "maintenance" in keys


def test_maintenance_module_permission_actions():
    """maintenance must declare predict, review_prediction, export (not just DEFAULT_ACTIONS)."""
    mod = next((m for m in MODULE_DEFINITIONS if m.key == "maintenance"), None)
    assert mod is not None
    declared = set(mod.permission_actions)
    missing = REQUIRED_ACTIONS - declared
    assert not missing, f"maintenance module missing permission_actions: {missing}"
    for action in ("predict", "review_prediction", "export"):
        assert action in declared, f"maintenance missing action: {action}"


# ── Permission seeds ──────────────────────────────────────────────────────────

def test_maintenance_permission_tuples_exist():
    seeded = {f"{p[0]}.{p[1]}" for p in PERMISSIONS}
    missing = REQUIRED_CODES - seeded
    assert not missing, f"Missing maintenance permission tuples in seed: {missing}"


def test_maintenance_predict_permission_seeded():
    seeded = {f"{p[0]}.{p[1]}" for p in PERMISSIONS}
    assert "maintenance.predict" in seeded
    assert "maintenance.review_prediction" in seeded
    assert "maintenance.export" in seeded


def test_maintenance_registry_permission_codes():
    all_codes = registry_permission_codes()
    missing = REQUIRED_CODES - all_codes
    assert not missing, f"registry_permission_codes missing: {missing}"


# ── Role grants ───────────────────────────────────────────────────────────────

def test_admin_has_full_maintenance_permissions():
    perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    missing = {"maintenance.view", "maintenance.create", "maintenance.edit",
               "maintenance.delete", "maintenance.predict",
               "maintenance.review_prediction", "maintenance.export"} - perms
    assert not missing, f"admin role missing maintenance permissions: {missing}"


def test_coo_has_maintenance_predict_review_export():
    perms = set(ROLE_DEFINITIONS["coo"]["permissions"])
    required = {"maintenance.view", "maintenance.predict",
                "maintenance.review_prediction", "maintenance.export"}
    missing = required - perms
    assert not missing, f"coo role missing maintenance permissions: {missing}"


def test_cto_has_maintenance_export():
    perms = set(ROLE_DEFINITIONS["cto"]["permissions"])
    assert "maintenance.export" in perms, "cto missing maintenance.export"


def test_factory_manager_has_maintenance_predict_review():
    perms = set(ROLE_DEFINITIONS["factory_manager"]["permissions"])
    required = {"maintenance.predict", "maintenance.review_prediction"}
    missing = required - perms
    assert not missing, f"factory_manager missing: {missing}"


def test_maintenance_technician_has_core_permissions():
    perms = set(ROLE_DEFINITIONS["maintenance_technician"]["permissions"])
    required = {"maintenance.view", "maintenance.create", "maintenance.edit"}
    missing = required - perms
    assert not missing, f"maintenance_technician missing: {missing}"


def test_production_manager_has_maintenance_view_export():
    perms = set(ROLE_DEFINITIONS["production_manager"]["permissions"])
    required = {"maintenance.view", "maintenance.export"}
    missing = required - perms
    assert not missing, f"production_manager missing: {missing}"


# ── Endpoint source guards ────────────────────────────────────────────────────

def test_maintenance_endpoints_use_require_permission():
    src = _source("app/api/v1/endpoints/maintenance.py")
    assert "require_permission" in src
    assert "get_current_user" not in src, "maintenance.py still uses bare get_current_user"


def test_maintenance_endpoints_predict_permission_guard():
    src = _source("app/api/v1/endpoints/maintenance.py")
    assert 'require_permission("maintenance", "predict")' in src


def test_maintenance_endpoints_review_prediction_permission_guard():
    src = _source("app/api/v1/endpoints/maintenance.py")
    assert 'require_permission("maintenance", "review_prediction")' in src


def test_maintenance_endpoints_export_permission_guard():
    src = _source("app/api/v1/endpoints/maintenance.py")
    assert 'require_permission("maintenance", "export")' in src


# ── Frontend guards ───────────────────────────────────────────────────────────

def _frontend_src(relative_path: str) -> str:
    frontend_root = ROOT.parent / "frontend"
    return (frontend_root / relative_path).read_text(encoding="utf-8")


def test_maintenance_dashboard_page_guard():
    src = _frontend_src("src/app/dashboard/maintenance/page.tsx")
    assert "RequirePermission" in src
    assert "maintenance.view" in src


def test_maintenance_assets_page_guard():
    src = _frontend_src("src/app/dashboard/maintenance/assets/page.tsx")
    assert "RequirePermission" in src
    assert "maintenance.view" in src


def test_maintenance_breakdowns_page_guard():
    src = _frontend_src("src/app/dashboard/maintenance/breakdowns/page.tsx")
    assert "RequirePermission" in src
    assert "maintenance.view" in src


def test_maintenance_plans_page_guard():
    src = _frontend_src("src/app/dashboard/maintenance/plans/page.tsx")
    assert "RequirePermission" in src
    assert "maintenance.view" in src


def test_maintenance_spares_page_guard():
    src = _frontend_src("src/app/dashboard/maintenance/spares/page.tsx")
    assert "RequirePermission" in src
    assert "maintenance.view" in src


def test_maintenance_reports_page_guard():
    src = _frontend_src("src/app/dashboard/maintenance/reports/page.tsx")
    assert "RequirePermission" in src
    assert "maintenance.export" in src


def test_maintenance_predictive_page_guard():
    src = _frontend_src("src/app/dashboard/maintenance/predictive/page.tsx")
    assert "RequirePermission" in src
    assert "maintenance.view" in src
    assert "PermissionGuard" in src
    assert "maintenance.predict" in src
    assert "maintenance.review_prediction" in src


# ── Migration file ────────────────────────────────────────────────────────────

def test_maintenance_reconciliation_migration_exists():
    migrations = list((ROOT / "alembic" / "versions").glob("*maintenance*reconciliation*"))
    assert migrations, "No maintenance reconciliation migration found"


def test_maintenance_migration_creates_expected_tables():
    src = _source("alembic/versions/20260516_0030_maintenance_predictive_reconciliation.py")
    for table in ("assets", "pm_plans", "pm_work_orders", "breakdown_records",
                  "spare_parts", "spare_part_usages", "maintenance_predictions"):
        assert table in src, f"Migration missing table: {table}"


# ── ORM model imports ─────────────────────────────────────────────────────────

def test_maintenance_orm_models_importable():
    from app.models.maintenance import (
        Asset, PMPlan, PMWorkOrder, BreakdownRecord,
        SparePart, SparePartUsage, MaintenancePrediction,
        AssetStatus, PMFrequency, PMStatus, BreakdownSeverity,
        BreakdownStatus, MaintenancePredictionRisk, MaintenancePredictionStatus,
    )
    assert Asset.__tablename__ == "assets"
    assert PMPlan.__tablename__ == "pm_plans"
    assert PMWorkOrder.__tablename__ == "pm_work_orders"
    assert BreakdownRecord.__tablename__ == "breakdown_records"
    assert SparePart.__tablename__ == "spare_parts"
    assert SparePartUsage.__tablename__ == "spare_part_usages"
    assert MaintenancePrediction.__tablename__ == "maintenance_predictions"


def test_maintenance_endpoint_module_importable():
    import app.api.v1.endpoints.maintenance as m
    assert hasattr(m, "router")
