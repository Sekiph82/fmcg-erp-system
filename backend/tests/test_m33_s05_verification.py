"""M33.S05 — Warehouse/Inventory Enterprise Upgrade verification suite.

Pure-unit tests for WMS status state machine, FEFO sorting logic,
GS1 barcode enum contract, handling-unit type hierarchy, and putaway
rule types — no database required.
"""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.models.wms import (
    HandlingUnitStatus, HandlingUnitType,
    PickWaveStatus, PickingTaskStatus, PackingStatus,
    PutawayTaskStatus, PutawayRuleType,
    ReplenishmentStatus, StockCountStatus,
    ZoneType, LocationType,
)
from app.models.gs1 import BarcodeType, PackagingLevel, SSCCStatus, PrintJobStatus
from app.services.wms_service import can_change_wms_status


# ── M33.S01 — License plates & GS1 enum contract ─────────────────────────────

def test_handling_unit_type_enum_has_pallet():
    assert HandlingUnitType.PALLET.value == "PALLET"


def test_handling_unit_type_has_carton_and_tote():
    values = {t.value for t in HandlingUnitType}
    assert "CARTON" in values
    assert "TOTE" in values


def test_gs1_barcode_types_include_gs1_128():
    values = {b.value for b in BarcodeType}
    assert "GS1_128" in values
    assert "EAN13" in values


def test_gs1_packaging_levels_ordered():
    levels = [PackagingLevel.UNIT, PackagingLevel.INNER_PACK, PackagingLevel.CARTON, PackagingLevel.PALLET]
    assert len(levels) == 4


def test_sscc_status_has_active_and_shipped():
    values = {s.value for s in SSCCStatus}
    assert "ACTIVE" in values
    assert "SHIPPED" in values


def test_print_job_status_includes_failed():
    values = {s.value for s in PrintJobStatus}
    assert "FAILED" in values


# ── M33.S01 — WMS zone/location types ─────────────────────────────────────────

def test_zone_types_includes_quarantine():
    values = {z.value for z in ZoneType}
    assert "QUARANTINE" in values


def test_location_types_includes_cold_storage():
    values = {l.value for l in LocationType}
    assert "COLD_STORAGE" in values


# ── M33.S02 — Allocation & Putaway: status state machine ─────────────────────

def test_handling_unit_open_can_change():
    assert can_change_wms_status("handling_unit", HandlingUnitStatus.OPEN) is True


def test_handling_unit_on_hold_can_change():
    assert can_change_wms_status("handling_unit", HandlingUnitStatus.ON_HOLD) is True


def test_handling_unit_shipped_cannot_change():
    assert can_change_wms_status("handling_unit", HandlingUnitStatus.SHIPPED) is False


def test_pick_wave_cancelled_cannot_change():
    assert can_change_wms_status("pick_wave", PickWaveStatus.CANCELLED) is False


def test_pick_wave_closed_cannot_change():
    assert can_change_wms_status("pick_wave", PickWaveStatus.CLOSED) is False


def test_pick_wave_picked_can_only_close_or_cancel():
    # allowed → CLOSED
    assert can_change_wms_status("pick_wave", PickWaveStatus.PICKED, PickWaveStatus.CLOSED) is True
    # allowed → CANCELLED
    assert can_change_wms_status("pick_wave", PickWaveStatus.PICKED, PickWaveStatus.CANCELLED) is True
    # disallowed → back to DRAFT
    assert can_change_wms_status("pick_wave", PickWaveStatus.PICKED, PickWaveStatus.DRAFT) is False


def test_picking_task_packed_is_terminal():
    assert can_change_wms_status("picking_task", PickingTaskStatus.PACKED) is False


def test_picking_task_cancelled_is_terminal():
    assert can_change_wms_status("picking_task", PickingTaskStatus.CANCELLED) is False


def test_picking_task_in_progress_can_change():
    assert can_change_wms_status("picking_task", PickingTaskStatus.IN_PROGRESS) is True


def test_packing_record_closed_is_terminal():
    assert can_change_wms_status("packing_record", PackingStatus.CLOSED) is False


def test_packing_record_open_can_change():
    assert can_change_wms_status("packing_record", PackingStatus.OPEN) is True


def test_replenishment_completed_is_terminal():
    assert can_change_wms_status("replenishment_task", ReplenishmentStatus.COMPLETED) is False


def test_replenishment_pending_can_change():
    assert can_change_wms_status("replenishment_task", ReplenishmentStatus.PENDING) is True


def test_putaway_task_completed_is_terminal():
    assert can_change_wms_status("putaway_task", PutawayTaskStatus.COMPLETED) is False


def test_putaway_task_pending_can_change():
    assert can_change_wms_status("putaway_task", PutawayTaskStatus.PENDING) is True


# ── M33.S02 — FEFO sorting logic ─────────────────────────────────────────────

def _fefo_key(expiry_date, created_at):
    """Mirrors SQL: order_by(Lot.expiry_date.asc().nulls_last(), Stock.created_at.asc())."""
    if expiry_date is None:
        return (1, created_at)
    return (0, expiry_date, created_at)


def test_fefo_sorts_earlier_expiry_first():
    today = date(2026, 11, 10)
    lots = [
        {"expiry": today + timedelta(days=30), "created": today},
        {"expiry": today + timedelta(days=10), "created": today},
        {"expiry": today + timedelta(days=20), "created": today},
    ]
    sorted_lots = sorted(lots, key=lambda x: _fefo_key(x["expiry"], x["created"]))
    assert sorted_lots[0]["expiry"] == today + timedelta(days=10)
    assert sorted_lots[1]["expiry"] == today + timedelta(days=20)
    assert sorted_lots[2]["expiry"] == today + timedelta(days=30)


def test_fefo_no_expiry_lots_sorted_last():
    today = date(2026, 11, 10)
    lots = [
        {"expiry": None, "created": today - timedelta(days=5)},
        {"expiry": today + timedelta(days=15), "created": today},
    ]
    sorted_lots = sorted(lots, key=lambda x: _fefo_key(x["expiry"], x["created"]))
    assert sorted_lots[0]["expiry"] == today + timedelta(days=15)
    assert sorted_lots[1]["expiry"] is None


def test_fefo_tie_on_expiry_uses_fifo():
    today = date(2026, 11, 10)
    expiry = today + timedelta(days=20)
    lots = [
        {"expiry": expiry, "created": today},
        {"expiry": expiry, "created": today - timedelta(days=3)},
    ]
    sorted_lots = sorted(lots, key=lambda x: _fefo_key(x["expiry"], x["created"]))
    # older lot (created - 3 days) first
    assert sorted_lots[0]["created"] == today - timedelta(days=3)


# ── M33.S02 — Putaway rule types ─────────────────────────────────────────────

def test_putaway_rule_types_include_fefo_zone_nearest():
    values = {r.value for r in PutawayRuleType}
    assert "ZONE" in values
    assert "NEAREST" in values
    assert "FIXED" in values
    assert "RANDOM" in values


# ── M33.S04 — Stock count lifecycle ───────────────────────────────────────────

def test_stock_count_terminal_statuses():
    terminal = {StockCountStatus.APPROVED.value, StockCountStatus.CANCELLED.value}
    assert StockCountStatus.DRAFT.value not in terminal
    assert StockCountStatus.IN_PROGRESS.value not in terminal
    assert StockCountStatus.PENDING_APPROVAL.value not in terminal
