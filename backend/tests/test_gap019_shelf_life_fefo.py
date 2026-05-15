"""GAP-019: Shelf-Life / FEFO / Expiry Control — focused tests."""
from __future__ import annotations


# ── Registry / module contract ────────────────────────────────────────────────

def test_shelf_life_in_module_definitions():
    from app.core.module_registry import MODULE_DEFINITIONS
    keys = [m.key for m in MODULE_DEFINITIONS]
    assert "shelf_life" in keys, "shelf_life not in MODULE_DEFINITIONS"


def test_shelf_life_not_in_endpoint_route_definitions():
    from app.core.module_registry import ENDPOINT_ROUTE_DEFINITIONS
    keys = [e.key for e in ENDPOINT_ROUTE_DEFINITIONS]
    assert "shelf_life" not in keys, "shelf_life still in ENDPOINT_ROUTE_DEFINITIONS"


def test_shelf_life_permission_actions():
    from app.core.module_registry import MODULE_DEFINITIONS
    m = next(m for m in MODULE_DEFINITIONS if m.key == "shelf_life")
    required = {"view", "create", "edit", "approve", "hold", "dispose", "report"}
    assert required.issubset(set(m.permission_actions)), (
        f"shelf_life missing actions: {required - set(m.permission_actions)}"
    )


def test_shelf_life_permission_codes_in_registry():
    from app.core.module_registry import registry_permission_codes
    codes = registry_permission_codes()
    for action in ("view", "create", "edit", "approve", "hold", "dispose", "report"):
        assert f"shelf_life.{action}" in codes, f"shelf_life.{action} missing from registry"


def test_shelf_life_is_critical():
    from app.core.module_registry import MODULE_DEFINITIONS
    m = next(m for m in MODULE_DEFINITIONS if m.key == "shelf_life")
    assert m.critical is True, "shelf_life module should be critical"


# ── ORM model contract ────────────────────────────────────────────────────────

def test_lot_shelf_life_profile_model_exists():
    from app.models.shelf_life import LotShelfLifeProfile
    cols = {c.key for c in LotShelfLifeProfile.__table__.columns}
    assert "expiry_date" in cols, "LotShelfLifeProfile missing expiry_date"


def test_item_shelf_life_config_model_exists():
    from app.models.shelf_life import ItemShelfLifeConfig
    cols = {c.key for c in ItemShelfLifeConfig.__table__.columns}
    assert "min_remaining_life_pct" in cols or "shelf_life_days" in cols, (
        "ItemShelfLifeConfig missing shelf life threshold column"
    )


def test_bulk_hold_record_model_exists():
    from app.models.shelf_life import BulkHoldRecord
    cols = {c.key for c in BulkHoldRecord.__table__.columns}
    assert len(cols) > 0, "BulkHoldRecord has no columns"


def test_customer_shelf_life_rule_model_exists():
    from app.models.shelf_life import CustomerShelfLifeRule
    cols = {c.key for c in CustomerShelfLifeRule.__table__.columns}
    assert len(cols) > 0, "CustomerShelfLifeRule has no columns"


# ── Service contract ──────────────────────────────────────────────────────────

def test_shelf_life_service_has_fefo_functions():
    import app.services.shelf_life_service as svc
    assert hasattr(svc, "rank_lots_fefo"), "shelf_life_service missing rank_lots_fefo"
    assert hasattr(svc, "validate_issue"), "shelf_life_service missing validate_issue"
    assert hasattr(svc, "create_bulk_hold"), "shelf_life_service missing create_bulk_hold"
    assert hasattr(svc, "get_fefo_compliance_report"), "shelf_life_service missing get_fefo_compliance_report"
