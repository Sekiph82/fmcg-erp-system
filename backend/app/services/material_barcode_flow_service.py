"""M37.S04 — barcode-driven raw-material flow: resolve any material barcode, dispense
(weigh + warehouse issue + label) a prepared lot for a work order, and consume it on the
shop floor by scanning. Every scan, accepted or rejected, is written to the work-order
activity log with server time, device time, session, machine and line context.

No new tables: the dispense ↔ work-order link and the scan log live in `WOActivityLog`
(`MATERIAL_DISPENSED`, `MATERIAL_SCAN`), next to the existing `MATERIAL_CONSUMPTION` event.
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import BarcodeLabel
from app.models.inventory import Lot
from app.models.master import Material, Product
from app.models.material_flow import PreparedLot, QualityStatus
from app.models.production_execution import ExecOrderMaterial
from app.models.shop_floor import WOActivityLog
from app.services import gs1_service
from app.services import production_execution_service as exec_svc
from app.services import shop_floor_service as sf_svc


class ScanRejected(ValueError):
    """A scan was refused; the rejection itself has already been logged and committed."""


# ── Resolution ────────────────────────────────────────────────────────────────

def _lot_info(lot: Optional[Lot]) -> dict[str, Any]:
    if lot is None:
        return {}
    expired = bool(lot.expiry_date and lot.expiry_date < date.today())
    return {
        "lot_id": str(lot.id),
        "lot_number": lot.lot_number,
        "batch_number": lot.batch_number,
        "expiry_date": lot.expiry_date.isoformat() if lot.expiry_date else None,
        "is_quarantine": bool(lot.is_quarantine),
        "is_expired": expired,
        "supplier_id": str(lot.supplier_id) if lot.supplier_id else None,
    }


async def _material_info(db: AsyncSession, material_id: Optional[uuid.UUID]) -> dict[str, Any]:
    if material_id is None:
        return {}
    material = await db.get(Material, material_id)
    if material is None:
        return {"material_id": str(material_id)}
    uom = material.uom.value if hasattr(material.uom, "value") else str(material.uom)
    return {"material_id": str(material.id), "material_code": material.code,
            "material_name": material.name, "uom": uom}


def _gs1_weight(parsed: dict[str, str]) -> Optional[Decimal]:
    for n in range(6):
        raw = parsed.get(f"310{n}")
        if raw and raw.isdigit():
            return Decimal(raw) / (Decimal(10) ** n)
    return None


def _looks_gs1(code: str) -> bool:
    return code.startswith("(") or code.startswith("]C1") or "\x1d" in code or bool(re.fullmatch(r"(01|02)\d{14}.*", code))


async def resolve_code(
    db: AsyncSession, code: str, *, material_ids: Optional[set[uuid.UUID]] = None,
) -> Optional[dict[str, Any]]:
    """Return everything the system knows about a scanned code, or None.

    Order: prepared-lot label → registered barcode label → GS1 → lot number → material code →
    product barcode/SKU. `material_ids` narrows an ambiguous lot number to the caller's materials.
    """
    code = (code or "").strip()
    if not code:
        return None

    prepared = (await db.execute(select(PreparedLot).where(PreparedLot.prepared_lot_no == code))).scalar_one_or_none()
    if prepared is not None:
        lot = await db.get(Lot, prepared.source_lot_id) if prepared.source_lot_id else None
        return {
            "code": code, "type": "PREPARED_LOT",
            "prepared_lot_id": str(prepared.id), "prepared_lot_no": prepared.prepared_lot_no,
            "quantity": str(prepared.actual_quantity) if prepared.actual_quantity is not None else None,
            "target_quantity": str(prepared.target_quantity), "prepared_uom": prepared.uom,
            "consumed": prepared.consumed, "quality_status": prepared.quality_status.value,
            "over_weigh": prepared.over_weigh, "under_weigh": prepared.under_weigh,
            "weighed_at": prepared.weighed_at.isoformat() if prepared.weighed_at else None,
            **await _material_info(db, prepared.material_id), **_lot_info(lot),
        }

    label = (await db.execute(select(BarcodeLabel).where(BarcodeLabel.barcode_value == code))).scalar_one_or_none()
    if label is not None:
        if label.entity_type == "LOT":
            lot = await db.get(Lot, label.entity_id)
            return {"code": code, "type": "LOT", **await _material_info(db, lot.material_id if lot else None), **_lot_info(lot)}
        if label.entity_type == "MATERIAL":
            return {"code": code, "type": "MATERIAL", **await _material_info(db, label.entity_id)}
        return {"code": code, "type": label.entity_type, "entity_id": str(label.entity_id), "entity_name": label.entity_name}

    if _looks_gs1(code):
        parsed = gs1_service.parse_gs1_string(code.removeprefix("]C1"))
        lot_no = parsed.get("10")
        result: dict[str, Any] = {"code": code, "type": "GS1", "gs1": parsed, "gtin": parsed.get("01")}
        weight = _gs1_weight(parsed)
        if weight is not None:
            result["quantity"] = str(weight)
        if lot_no:
            found = await _resolve_lot_number(db, lot_no, material_ids)
            if found is not None:
                result.update(await _material_info(db, found.material_id))
                result.update(_lot_info(found))
            else:
                result["lot_number"] = lot_no
        return result

    lot = await _resolve_lot_number(db, code, material_ids)
    if lot is not None:
        return {"code": code, "type": "LOT", **await _material_info(db, lot.material_id), **_lot_info(lot)}

    material = (await db.execute(select(Material).where(Material.code == code))).scalar_one_or_none()
    if material is not None:
        return {"code": code, "type": "MATERIAL", **await _material_info(db, material.id)}

    product = (await db.execute(select(Product).where((Product.barcode == code) | (Product.sku == code)))).scalars().first()
    if product is not None:
        return {"code": code, "type": "PRODUCT", "product_id": str(product.id), "product_name": product.name, "sku": product.sku}
    return None


async def _resolve_lot_number(
    db: AsyncSession, lot_number: str, material_ids: Optional[set[uuid.UUID]],
) -> Optional[Lot]:
    q = select(Lot).where(Lot.lot_number == lot_number, Lot.material_id.is_not(None))
    lots = list((await db.execute(q)).scalars().all())
    if material_ids:
        lots = [lot for lot in lots if lot.material_id in material_ids]
    return lots[0] if len(lots) == 1 else None


# ── Dispensing (warehouse → work order) ───────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


async def dispense_prepared_lot(
    db: AsyncSession,
    *,
    exec_material_id: uuid.UUID,
    source_lot_code: str,
    actual_quantity: Decimal,
    tolerance_pct: Optional[Decimal],
    actor_user_id: uuid.UUID,
    target_quantity: Optional[Decimal] = None,
) -> PreparedLot:
    """Weigh a quantity of a source lot for one work-order material line, issue it to the
    order and return the prepared lot whose label the operator will scan."""
    if not actual_quantity.is_finite() or actual_quantity <= 0:
        raise ValueError("Weighed quantity must be greater than zero")
    material_line = await db.get(ExecOrderMaterial, exec_material_id)
    if material_line is None:
        raise ValueError("Work-order material line not found")
    if material_line.item_type != "MATERIAL" or material_line.item_id is None:
        raise ValueError("Only raw-material lines can be dispensed")
    if material_line.work_order_id is None:
        raise ValueError("Assign this material line to an operation before dispensing")

    # narrow ambiguous lot numbers to this material; fall back so a wrong-material scan says what it is
    resolved = (await resolve_code(db, source_lot_code, material_ids={material_line.item_id})
                or await resolve_code(db, source_lot_code))
    if resolved and resolved["type"] == "PREPARED_LOT":
        raise ValueError("Scan the warehouse source lot, not a prepared-lot label")
    if not resolved or not resolved.get("lot_id"):
        raise ValueError("Scan or enter a known source lot for this material")
    if resolved.get("material_id") != str(material_line.item_id):
        raise ValueError(f"Lot {resolved.get('lot_number')} is {resolved.get('material_name') or 'another material'}, not {material_line.item_name}")
    if resolved["is_quarantine"]:
        raise ValueError(f"Lot {resolved['lot_number']} is in quarantine")
    if resolved["is_expired"]:
        raise ValueError(f"Lot {resolved['lot_number']} expired on {resolved['expiry_date']}")

    # Tolerance applies to the requested bag/batch weight; a line may be dispensed in several bags.
    target = target_quantity if target_quantity is not None else actual_quantity
    prepared = PreparedLot(
        prepared_lot_no=f"PL-{_now():%y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        source_lot_id=uuid.UUID(resolved["lot_id"]),
        material_id=material_line.item_id,
        target_quantity=target,
        actual_quantity=actual_quantity,
        uom=material_line.uom,
        tolerance_pct=tolerance_pct,
        weighed_at=_now(),
        operator_id=actor_user_id,
        quality_status=QualityStatus.RELEASED,
    )
    if tolerance_pct is not None:
        tol = target * tolerance_pct / Decimal("100")
        prepared.over_weigh = actual_quantity > target + tol
        prepared.under_weigh = actual_quantity < target - tol
        if prepared.over_weigh or prepared.under_weigh:
            # never label an out-of-tolerance weighing; the floor would refuse it anyway
            raise ValueError(f"Weighed {actual_quantity} is outside {tolerance_pct}% of target {target}; re-weigh before issuing")
    db.add(prepared)
    await db.flush()
    await sf_svc._log_event(
        db, material_line.work_order_id, material_line.production_order_id, "MATERIAL_DISPENSED",
        actor_user_id=actor_user_id,
        extra_data={
            "prepared_lot_id": str(prepared.id), "prepared_lot_no": prepared.prepared_lot_no,
            "material_line_id": str(material_line.id), "material_id": str(material_line.item_id),
            "item_name": material_line.item_name, "lot_no": resolved["lot_number"],
            "qty": str(actual_quantity), "uom": material_line.uom,
            "over_weigh": prepared.over_weigh, "under_weigh": prepared.under_weigh,
        },
    )
    # Warehouse issue to the order (commits the prepared lot and dispense event with it).
    await exec_svc.issue_material(
        db, material_line.production_order_id, material_line.id, actual_quantity, resolved["lot_number"],
    )
    await db.refresh(prepared)
    return prepared


def prepared_lot_label(prepared: PreparedLot, info: dict[str, Any]) -> dict[str, Any]:
    """Printable label: Code 128 + QR of the prepared-lot number, plus human-readable fields."""
    return {
        "prepared_lot_no": prepared.prepared_lot_no,
        "code128_svg_b64": gs1_service._generate_barcode_b64(prepared.prepared_lot_no, "CODE128"),
        "qr_png_b64": gs1_service._generate_qr_b64(prepared.prepared_lot_no),
        "material_name": info.get("material_name"), "material_code": info.get("material_code"),
        "lot_number": info.get("lot_number"), "expiry_date": info.get("expiry_date"),
        "quantity": str(prepared.actual_quantity), "uom": prepared.uom,
        "weighed_at": prepared.weighed_at.isoformat() if prepared.weighed_at else None,
    }


# ── Scan to consume (shop floor) ──────────────────────────────────────────────

async def scan_consume(
    db: AsyncSession,
    wo_id: uuid.UUID,
    *,
    session_id: uuid.UUID,
    code: str,
    qty: Optional[Decimal],
    client_scanned_at: Optional[datetime],
    actor_user_id: uuid.UUID,
    idempotency_key: str,
    request_fingerprint: str,
) -> tuple[ExecOrderMaterial, dict[str, Any]]:
    """Resolve the scanned code against this work order's materials and record consumption."""
    replay = await sf_svc._find_idempotent_execution_event(db, wo_id, actor_user_id, idempotency_key, request_fingerprint)
    if replay is not None:
        material = await db.get(ExecOrderMaterial, uuid.UUID((replay.extra_data or {})["material_id"]))
        return material, {"replayed": True}

    _, work_order = await sf_svc._lock_wo_context(db, wo_id)
    po_id = work_order.production_order_id  # ORM objects expire on rollback; keep plain ids
    lines = list((await db.execute(
        select(ExecOrderMaterial).where(
            ExecOrderMaterial.production_order_id == work_order.production_order_id,
            ExecOrderMaterial.work_order_id == work_order.id,
        )
    )).scalars().all())
    resolved = (await resolve_code(db, code, material_ids={m.item_id for m in lines if m.item_id})
                or await resolve_code(db, code))
    log: dict[str, Any] = {
        "code": code, "client_scanned_at": client_scanned_at.isoformat() if client_scanned_at else None,
        "resolved_type": resolved.get("type") if resolved else None,
        "material_id": resolved.get("material_id") if resolved else None,
        "lot_no": resolved.get("lot_number") if resolved else None,
        "prepared_lot_no": resolved.get("prepared_lot_no") if resolved else None,
    }

    async def reject(reason: str) -> ScanRejected:
        await db.rollback()
        await sf_svc._log_event(db, wo_id, po_id, "MATERIAL_SCAN", session_id=session_id,
                                actor_user_id=actor_user_id, reason_code="REJECTED", remarks=reason,
                                extra_data={**log, "result": "REJECTED"})
        await db.commit()
        return ScanRejected(reason)

    if resolved is None:
        raise await reject("Unknown barcode: not a prepared lot, lot, GS1 or material label")
    line = next((m for m in lines if resolved.get("material_id") and str(m.item_id) == resolved["material_id"]), None)
    if line is None:
        raise await reject(f"{resolved.get('material_name') or resolved.get('type')} is not in this operation's recipe")
    if resolved.get("is_quarantine"):
        raise await reject(f"Lot {resolved.get('lot_number')} is in quarantine")
    if resolved.get("is_expired"):
        raise await reject(f"Lot {resolved.get('lot_number')} expired on {resolved.get('expiry_date')}")

    prepared: Optional[PreparedLot] = None
    if resolved["type"] == "PREPARED_LOT":
        dispensed = (await db.execute(
            select(WOActivityLog.id).where(
                WOActivityLog.work_order_id == wo_id,
                WOActivityLog.event_type == "MATERIAL_DISPENSED",
                WOActivityLog.extra_data["prepared_lot_id"].astext == resolved["prepared_lot_id"],
            )
        )).first()
        if dispensed is None:
            raise await reject(f"Prepared lot {resolved['prepared_lot_no']} was dispensed for a different work order")
        prepared = (await db.execute(
            select(PreparedLot).where(PreparedLot.id == uuid.UUID(resolved["prepared_lot_id"])).with_for_update()
        )).scalar_one()
        if prepared.consumed:
            raise await reject(f"Prepared lot {prepared.prepared_lot_no} was already consumed")
        if prepared.quality_status != QualityStatus.RELEASED:
            raise await reject(f"Prepared lot {prepared.prepared_lot_no} is {prepared.quality_status.value}")
        if prepared.over_weigh or prepared.under_weigh:
            raise await reject(f"Prepared lot {prepared.prepared_lot_no} is outside weighing tolerance")
        qty = prepared.actual_quantity  # label quantity is authoritative; typed qty is ignored
    elif qty is None and resolved.get("quantity"):
        try:
            qty = Decimal(resolved["quantity"])
        except InvalidOperation:
            qty = None
    if qty is None:
        raise await reject("Enter the quantity for this material")

    lot_no = resolved.get("lot_number")
    if lot_no and lot_no not in (line.lot_numbers or []):
        raise await reject(f"Lot {lot_no} was not issued to this work order")
    if prepared is not None:
        prepared.consumed = True
    await sf_svc._log_event(db, wo_id, po_id, "MATERIAL_SCAN", session_id=session_id,
                            actor_user_id=actor_user_id, reason_code="ACCEPTED",
                            extra_data={**log, "result": "ACCEPTED", "material_line_id": str(line.id), "qty": str(qty)})
    try:
        material = await sf_svc.consume_work_order_material(
            db, wo_id, line.id, qty, session_id=session_id, lot_no=lot_no,
            actor_user_id=actor_user_id, idempotency_key=idempotency_key, request_fingerprint=request_fingerprint,
        )
    except sf_svc.IdempotencyConflictError:
        await db.rollback()
        raise
    except ValueError as exc:
        raise await reject(str(exc))
    return material, resolved
