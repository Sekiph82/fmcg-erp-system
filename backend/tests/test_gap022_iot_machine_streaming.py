"""GAP-022: True IoT / Machine Streaming focused contract tests."""
from __future__ import annotations

from pathlib import Path

from app.core.module_registry import (
    MODULE_DEFINITIONS,
    ENDPOINT_ROUTE_DEFINITIONS,
    registry_permission_codes,
)
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ACTIONS = {"view", "ingest", "configure", "acknowledge", "export", "admin"}
REQUIRED_CODES = {f"iot.{a}" for a in REQUIRED_ACTIONS}


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


# ── Module registry ───────────────────────────────────────────────────────────

def test_iot_is_module_definition():
    """iot must be promoted to ModuleDefinition."""
    keys = {m.key for m in MODULE_DEFINITIONS}
    assert "iot" in keys, "iot not found in MODULE_DEFINITIONS"


def test_iot_not_endpoint_route_definition():
    """iot must NOT remain in ENDPOINT_ROUTE_DEFINITIONS after promotion."""
    keys = {e.key for e in ENDPOINT_ROUTE_DEFINITIONS}
    assert "iot" not in keys, "iot still in ENDPOINT_ROUTE_DEFINITIONS (not yet promoted)"


def test_iot_module_permission_actions():
    """iot ModuleDefinition must declare all required permission actions."""
    mod = next((m for m in MODULE_DEFINITIONS if m.key == "iot"), None)
    assert mod is not None, "iot module not found"
    declared = set(mod.permission_actions)
    missing = REQUIRED_ACTIONS - declared
    assert not missing, f"iot module missing permission_actions: {missing}"


# ── Permission seeds ──────────────────────────────────────────────────────────

def test_iot_permission_tuples_exist():
    """All required iot.* permission tuples must be in seed PERMISSIONS."""
    seeded = {f"{p[0]}.{p[1]}" for p in PERMISSIONS}
    missing = REQUIRED_CODES - seeded
    assert not missing, f"Missing IoT permission tuples in seed: {missing}"


def test_iot_registry_permission_codes():
    """registry_permission_codes must include all iot.* codes."""
    all_codes = registry_permission_codes()
    missing = REQUIRED_CODES - all_codes
    assert not missing, f"registry_permission_codes missing: {missing}"


# ── Role grants ───────────────────────────────────────────────────────────────

def test_admin_has_full_iot_permissions():
    """admin role must have all iot.* permissions."""
    perms = set(ROLE_DEFINITIONS["admin"]["permissions"])
    missing = REQUIRED_CODES - perms
    assert not missing, f"admin role missing IoT permissions: {missing}"


def test_cto_has_iot_core_permissions():
    """cto must have iot.view, configure, acknowledge, export, admin."""
    perms = set(ROLE_DEFINITIONS["cto"]["permissions"])
    required = {"iot.view", "iot.configure", "iot.acknowledge", "iot.export", "iot.admin"}
    missing = required - perms
    assert not missing, f"cto role missing IoT permissions: {missing}"


def test_factory_manager_has_iot_view():
    """factory_manager must have iot.view and iot.acknowledge."""
    perms = set(ROLE_DEFINITIONS["factory_manager"]["permissions"])
    assert "iot.view" in perms, "factory_manager missing iot.view"
    assert "iot.acknowledge" in perms, "factory_manager missing iot.acknowledge"


def test_maintenance_technician_has_iot_view():
    """maintenance_technician must have iot.view."""
    perms = set(ROLE_DEFINITIONS["maintenance_technician"]["permissions"])
    assert "iot.view" in perms, "maintenance_technician missing iot.view"


def test_owner_role_is_wildcard():
    """owner role has wildcard permissions — IoT auto-included."""
    assert ROLE_DEFINITIONS["owner"]["permissions"] == "*"


# ── Endpoint source permission guards ─────────────────────────────────────────

def test_iot_endpoint_uses_require_permission():
    """iot.py endpoint must import and use require_permission."""
    src = _source("app/api/v1/endpoints/iot.py")
    assert "require_permission" in src, "iot endpoint does not use require_permission"
    assert 'require_permission("iot"' in src, "iot endpoint does not call require_permission with 'iot' module"


def test_iot_ingest_requires_ingest_permission():
    """POST /ingest must be protected with iot.ingest."""
    src = _source("app/api/v1/endpoints/iot.py")
    assert 'require_permission("iot", "ingest")' in src


def test_iot_dashboard_requires_view_permission():
    """GET /dashboard must be protected with iot.view."""
    src = _source("app/api/v1/endpoints/iot.py")
    assert 'require_permission("iot", "view")' in src


def test_iot_threshold_create_requires_configure_permission():
    """POST /thresholds must be protected with iot.configure."""
    src = _source("app/api/v1/endpoints/iot.py")
    assert 'require_permission("iot", "configure")' in src


def test_iot_alert_acknowledge_requires_acknowledge_permission():
    """POST /alerts/{id}/acknowledge must be protected with iot.acknowledge."""
    src = _source("app/api/v1/endpoints/iot.py")
    assert 'require_permission("iot", "acknowledge")' in src


# ── Frontend guards ───────────────────────────────────────────────────────────

def test_iot_page_uses_require_permission_guard():
    """frontend IoT page must use RequirePermission with iot.view."""
    src = _source("../frontend/src/app/dashboard/iot/page.tsx")
    assert "RequirePermission" in src, "IoT page missing RequirePermission guard"
    assert 'permission="iot.view"' in src, "IoT page guard not set to iot.view"


def test_iot_nav_guard_is_iot_view():
    """nav-config IoT entry must use iot.view (not utility_management.view)."""
    src = _source("../frontend/src/components/nav-config.tsx")
    assert 'href: "/dashboard/iot"' in src or 'href="/dashboard/iot"' in src or '"/dashboard/iot"' in src
    # Guard must be iot.view, not the old utility_management.view
    import re
    iot_nav_line = next((l for l in src.splitlines() if "/dashboard/iot" in l), "")
    assert "iot.view" in iot_nav_line, f"IoT nav entry does not use iot.view: {iot_nav_line!r}"


# ── Migration ownership ───────────────────────────────────────────────────────

def test_iot_migration_exists():
    """GAP-022C migration file must exist."""
    migration_dir = ROOT / "alembic" / "versions"
    iot_migrations = list(migration_dir.glob("*iot_machine_streaming*"))
    assert iot_migrations, "No IoT machine streaming migration file found"


def test_iot_migration_creates_devices_table():
    """GAP-022C migration must create iot_devices table."""
    migration_dir = ROOT / "alembic" / "versions"
    iot_migrations = list(migration_dir.glob("*iot_machine_streaming*"))
    assert iot_migrations
    src = iot_migrations[0].read_text(encoding="utf-8")
    assert "iot_devices" in src, "Migration does not create iot_devices"
    assert "iot_channels" in src, "Migration does not create iot_channels"
    assert "machine_events" in src, "Migration does not create machine_events"


# ── ORM model imports ─────────────────────────────────────────────────────────

def test_iot_models_import():
    """All IoT ORM model classes must be importable."""
    from app.models.iot import (
        IoTDevice, IoTChannel, IoTIngestMessage,
        SensorDataPoint, MachineStateEvent,
        IoTAlertThreshold, IoTAlert,
        MachineState, AlertSeverity, AlertStatus,
        IoTDeviceProtocol, IoTDeviceType, IoTDeviceStatus,
        IoTChannelValueType, IoTAggregationMethod, IoTIngestStatus,
    )
    assert IoTDevice.__tablename__ == "iot_devices"
    assert IoTChannel.__tablename__ == "iot_channels"
    assert IoTIngestMessage.__tablename__ == "iot_ingest_messages"
    assert SensorDataPoint.__tablename__ == "iot_sensor_data"
    assert MachineStateEvent.__tablename__ == "iot_machine_states"
    assert IoTAlertThreshold.__tablename__ == "iot_alert_thresholds"
    assert IoTAlert.__tablename__ == "iot_alerts"


def test_machine_event_model_import():
    """MachineEvent must be importable from integrations."""
    from app.models.integrations import MachineEvent
    assert MachineEvent.__tablename__ == "machine_events"


def test_iot_endpoint_import():
    """iot endpoint module must be importable."""
    import app.api.v1.endpoints.iot  # noqa: F401
