from __future__ import annotations

from fastapi import APIRouter

from app.core.module_registry import (
    ENDPOINT_ROUTE_DEFINITIONS,
    MODULE_DEFINITIONS,
    register_module_routes,
    registry_permission_codes,
)
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS
from app.services.report_builder_service import (
    DATA_SOURCES,
    _apply_filter_python,
    _validate_field,
)

REQUIRED_PERMISSION_CODES = {
    "reports.view",
    "reports.create",
    "reports.edit",
    "reports.run",
    "reports.export",
    "reports.admin",
}


# ── Registry / seed contract ───────────────────────────────────────────────────

def test_reports_module_in_module_definitions_not_endpoint_routes():
    module_keys = {m.key for m in MODULE_DEFINITIONS}
    route_keys = {r.key for r in ENDPOINT_ROUTE_DEFINITIONS}

    assert "reports" in module_keys, "reports must be in MODULE_DEFINITIONS"
    assert "report_builder" not in route_keys, "report_builder must not remain in ENDPOINT_ROUTE_DEFINITIONS"
    assert "reports" not in route_keys, "reports must not be in ENDPOINT_ROUTE_DEFINITIONS"


def test_all_six_report_permission_codes_in_registry():
    codes = registry_permission_codes()
    missing = REQUIRED_PERMISSION_CODES - codes
    assert not missing, f"registry missing: {missing}"


def test_all_six_report_permission_codes_in_seed():
    seed_codes = {f"{module}.{action}" for module, action, *_ in PERMISSIONS}
    missing = REQUIRED_PERMISSION_CODES - seed_codes
    assert not missing, f"seed missing: {missing}"


def test_admin_role_has_all_report_permissions():
    admin_perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    missing = REQUIRED_PERMISSION_CODES - admin_perms
    assert not missing, f"admin role missing: {missing}"


def test_admin_role_has_at_minimum_view_run_admin():
    admin_perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    assert {"reports.view", "reports.run", "reports.admin"} <= admin_perms


# ── Route registration ─────────────────────────────────────────────────────────

def test_report_builder_routes_register_from_module_registry():
    router = APIRouter()
    diagnostics = register_module_routes(router, environment="development")
    paths = {route.path for route in router.routes}

    errors = [d for d in diagnostics if d.get("status") == "error"]
    assert not errors, f"module route errors: {errors}"
    assert any("/reports" in p or "/report" in p for p in paths), \
        f"no report-builder paths registered. paths={sorted(paths)[:10]}"


# ── Data source validation ─────────────────────────────────────────────────────

def test_validate_field_known_source_and_field():
    assert _validate_field("sales_orders", "order_no") is True
    assert _validate_field("sales_orders", "total_amount") is True
    assert _validate_field("customers", "customer_name") is True
    assert _validate_field("products", "unit_price") is True
    assert _validate_field("stock", "quantity") is True


def test_validate_field_unknown_source_returns_false():
    assert _validate_field("nonexistent_source", "any_field") is False


def test_validate_field_unknown_field_returns_false():
    assert _validate_field("sales_orders", "__injected") is False
    assert _validate_field("customers", "password") is False


def test_data_sources_catalog_has_required_keys():
    required_sources = {"sales_orders", "customers", "products", "stock", "invoices"}
    assert required_sources <= set(DATA_SOURCES.keys())


def test_data_sources_each_have_table_and_fields():
    for key, ds in DATA_SOURCES.items():
        assert "table" in ds, f"{key} missing 'table'"
        assert "fields" in ds, f"{key} missing 'fields'"
        assert len(ds["fields"]) > 0, f"{key} has no fields"


# ── Python-level filter helper ─────────────────────────────────────────────────

def _rows():
    return [
        {"status": "CONFIRMED", "total_amount": "500"},
        {"status": "DRAFT", "total_amount": "200"},
        {"status": "CONFIRMED", "total_amount": "1500"},
    ]


def test_apply_filter_eq():
    result = _apply_filter_python(_rows(), "status", "eq", "CONFIRMED")
    assert len(result) == 2
    assert all(r["status"] == "CONFIRMED" for r in result)


def test_apply_filter_neq():
    result = _apply_filter_python(_rows(), "status", "neq", "DRAFT")
    assert len(result) == 2


def test_apply_filter_gt():
    result = _apply_filter_python(_rows(), "total_amount", "gt", "400")
    assert len(result) == 2


def test_apply_filter_lt():
    result = _apply_filter_python(_rows(), "total_amount", "lt", "300")
    assert len(result) == 1


def test_apply_filter_between():
    result = _apply_filter_python(_rows(), "total_amount", "between", "100", "600")
    assert len(result) == 2


def test_apply_filter_like():
    result = _apply_filter_python(_rows(), "status", "like", "CONF")
    assert len(result) == 2


def test_apply_filter_in():
    result = _apply_filter_python(_rows(), "status", "in", "DRAFT,CANCELLED")
    assert len(result) == 1


def test_apply_filter_is_null():
    rows = [{"status": None}, {"status": "X"}]
    result = _apply_filter_python(rows, "status", "is_null", "")
    assert len(result) == 1


def test_apply_filter_is_not_null():
    rows = [{"status": None}, {"status": "X"}]
    result = _apply_filter_python(rows, "status", "is_not_null", "")
    assert len(result) == 1
