"""GAP-018: GS1 / Label Printing / Packaging Compliance — focused tests."""
from __future__ import annotations


# ── Registry / module contract ────────────────────────────────────────────────

def test_gs1_in_module_definitions():
    from app.core.module_registry import MODULE_DEFINITIONS
    keys = [m.key for m in MODULE_DEFINITIONS]
    assert "gs1" in keys, "gs1 not in MODULE_DEFINITIONS"


def test_gs1_not_in_endpoint_route_definitions():
    from app.core.module_registry import ENDPOINT_ROUTE_DEFINITIONS
    keys = [e.key for e in ENDPOINT_ROUTE_DEFINITIONS]
    assert "gs1" not in keys, "gs1 still in ENDPOINT_ROUTE_DEFINITIONS (should be MODULE_DEFINITIONS)"


def test_gs1_permission_actions():
    from app.core.module_registry import MODULE_DEFINITIONS
    m = next(m for m in MODULE_DEFINITIONS if m.key == "gs1")
    required = {"view", "create", "edit", "approve", "print", "report", "admin"}
    assert required.issubset(set(m.permission_actions)), (
        f"gs1 missing actions: {required - set(m.permission_actions)}"
    )


def test_gs1_permission_codes_in_registry():
    from app.core.module_registry import registry_permission_codes
    codes = registry_permission_codes()
    for action in ("view", "create", "edit", "approve", "print", "report", "admin"):
        assert f"gs1.{action}" in codes, f"gs1.{action} missing from registry"


def test_gs1_not_critical():
    from app.core.module_registry import MODULE_DEFINITIONS
    m = next(m for m in MODULE_DEFINITIONS if m.key == "gs1")
    assert m.critical is False, "gs1 module should not be critical"


# ── ORM model contract ────────────────────────────────────────────────────────

def test_product_gs1_config_has_sku_code():
    from app.models.gs1 import ProductGS1Config
    cols = {c.key for c in ProductGS1Config.__table__.columns}
    assert "product_sku_code" in cols, "ProductGS1Config missing product_sku_code column"


def test_product_gs1_config_has_weight_volume():
    from app.models.gs1 import ProductGS1Config
    cols = {c.key for c in ProductGS1Config.__table__.columns}
    assert "net_weight_g" in cols, "ProductGS1Config missing net_weight_g column"
    assert "net_volume_ml" in cols, "ProductGS1Config missing net_volume_ml column"


# ── Schema contract ───────────────────────────────────────────────────────────

def test_gs1_product_config_create_has_new_fields():
    from app.schemas.gs1 import ProductGS1ConfigCreate
    for field in ("product_sku_code", "net_weight_g", "net_volume_ml"):
        assert field in ProductGS1ConfigCreate.model_fields, f"ProductGS1ConfigCreate missing {field}"


def test_gs1_product_config_out_has_new_fields():
    from app.schemas.gs1 import ProductGS1ConfigOut
    for field in ("product_sku_code", "net_weight_g", "net_volume_ml"):
        assert field in ProductGS1ConfigOut.model_fields, f"ProductGS1ConfigOut missing {field}"


# ── Migration head ────────────────────────────────────────────────────────────

def test_alembic_head_is_gs1_migration():
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        capture_output=True, text=True,
        cwd=__file__[:__file__.index("tests")],
    )
    assert "20260516_0060" in result.stdout, (
        f"Alembic head should be 20260516_0060; got: {result.stdout.strip()}"
    )
