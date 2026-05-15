from types import SimpleNamespace
from pathlib import Path
import inspect

import pytest

from app.api.v1.endpoints import wms as wms_api
from app.models.wms import (
    HandlingUnitStatus,
    PackingStatus,
    PickWaveStatus,
    PickingTaskStatus,
    PutawayTaskStatus,
    ReplenishmentStatus,
)
from app.services.wms_service import (
    build_wms_access_hint,
    can_change_wms_status,
    ensure_wms_action_allowed,
)


def permission(code: str):
    return SimpleNamespace(code=code, is_active=True)


def access_scope(scope_id: str, **flags):
    defaults = {
        "scope_type": "warehouse",
        "scope_id": scope_id,
        "scope_name": scope_id,
        "is_active": True,
        "can_view": True,
        "can_create": False,
        "can_edit": False,
        "can_delete": False,
        "can_approve": False,
        "can_post": False,
        "can_release": False,
        "can_cancel": False,
        "can_export": False,
        "can_import": False,
        "can_transfer": False,
        "can_adjust": False,
        "can_receive": False,
        "can_dispatch": False,
    }
    defaults.update(flags)
    return SimpleNamespace(**defaults)


def role(permissions, scopes):
    return SimpleNamespace(
        is_active=True,
        permissions=[permission(code) for code in permissions],
        access_scopes=scopes,
    )


def user(permissions, scopes):
    return SimpleNamespace(
        is_superuser=False,
        roles=[role(permissions, scopes)],
        access_scopes=[],
    )


def test_wms_access_hint_separates_broad_view_from_scoped_mutation():
    warehouse_manager = user(
        [
            "inventory.view_all",
            "inventory.edit_own_scope",
            "inventory.adjust_own_scope",
            "inventory.receive_own_scope",
            "inventory.dispatch_own_scope",
            "inventory.transfer_own_scope",
        ],
        [
            access_scope(
                "nairobi",
                can_edit=True,
                can_adjust=True,
                can_receive=True,
                can_dispatch=True,
                can_transfer=True,
            )
        ],
    )

    nairobi = build_wms_access_hint(warehouse_manager, "nairobi")
    mombasa = build_wms_access_hint(warehouse_manager, "mombasa")

    assert nairobi.can_view is True
    assert nairobi.can_edit is True
    assert nairobi.can_putaway is True
    assert nairobi.can_pick is True
    assert mombasa.can_view is True
    assert mombasa.can_edit is False
    assert mombasa.can_pick is False


def test_wms_action_guard_returns_clear_forbidden_for_out_of_scope_mutation():
    warehouse_manager = user(
        ["inventory.view_all", "inventory.edit_own_scope"],
        [access_scope("nairobi", can_edit=True)],
    )

    with pytest.raises(Exception) as exc:
        ensure_wms_action_allowed(warehouse_manager, "mombasa", "edit")

    assert getattr(exc.value, "status_code", None) == 403
    assert exc.value.detail["error"] == "forbidden"
    assert "cannot modify" in exc.value.detail["detail"]


def test_wms_status_lock_rules_block_completed_or_closed_work():
    assert can_change_wms_status("handling_unit", HandlingUnitStatus.OPEN) is True
    assert can_change_wms_status("handling_unit", HandlingUnitStatus.SHIPPED) is False
    assert can_change_wms_status("pick_wave", PickWaveStatus.PICKED, PickWaveStatus.CLOSED) is True
    assert can_change_wms_status("pick_wave", PickWaveStatus.PICKED, PickWaveStatus.IN_PROGRESS) is False
    assert can_change_wms_status("picking_task", PickingTaskStatus.PACKED) is False
    assert can_change_wms_status("packing_record", PackingStatus.CLOSED) is False
    assert can_change_wms_status("replenishment_task", ReplenishmentStatus.COMPLETED) is False
    assert can_change_wms_status("putaway_task", PutawayTaskStatus.CANCELLED) is False


def test_seed_role_exposes_wms_nav_but_keeps_mutation_scoped():
    from app.db.seed import ROLE_DEFINITIONS

    permissions = set(ROLE_DEFINITIONS["warehouse_manager"]["permissions"])

    assert "wms.view" in permissions
    assert "warehouses.view_all" in permissions
    assert "inventory.view_all" in permissions
    assert "inventory.receive_own_scope" in permissions
    assert "inventory.dispatch_own_scope" in permissions
    assert "inventory.transfer_own_scope" in permissions
    assert "inventory.adjust_own_scope" in permissions
    assert "inventory.edit_all" not in permissions


def test_wms_api_exposes_depth_endpoints_with_scoped_guards():
    source = inspect.getsource(wms_api)

    for path in {
        '"/handling-units"',
        '"/handling-units/{handling_unit_id}"',
        '"/pick-waves"',
        '"/pick-waves/{wave_id}"',
    }:
        assert path in source

    assert "ensure_wms_action_allowed" in source
    assert "build_wms_access_hint" in source
    assert "can_change_wms_status" in source


def test_wms_frontend_contract_exposes_handling_units_waves_and_access_hints():
    repo_root = Path(__file__).resolve().parents[2]
    client_source = (repo_root / "frontend/src/lib/wms.ts").read_text(encoding="utf-8")
    page_source = (repo_root / "frontend/src/app/dashboard/wms/page.tsx").read_text(encoding="utf-8")

    for token in {
        "WMSAccessHint",
        "HandlingUnit",
        "PickWave",
        "listHandlingUnits",
        "listPickWaves",
    }:
        assert token in client_source

    assert "handlingUnits" in page_source
    assert "pickWaves" in page_source
    assert "AccessBadge" in page_source
    assert "View Only" in page_source
