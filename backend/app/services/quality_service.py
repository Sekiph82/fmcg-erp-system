"""
Quality Control business logic service.

Key operations:
  - auto_evaluate:   evaluates all test results against specs, sets is_passed
  - make_decision:   ACCEPT / REJECT / CONDITIONAL_RELEASE / REWORK
                     Rejection optionally calls quarantine on linked stock.
  - generate_coa:    builds a COA-ready report structure.
  - create_qc_for_grn:   convenience creator called after GRN posting.
  - create_qc_for_order: convenience creator for production order FG batch.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import (
    QCInspection, QCTestResult, QCParameter,
    QCType, QCStatus, QCDecision, ParameterType,
)
from app.models.inventory import Stock, Lot, StockMovement, MovementType, StockType
from app.schemas.quality import COAReport, COATestLine


# ── Guards ────────────────────────────────────────────────────────────────────

def _assert_status(insp: QCInspection, *allowed: QCStatus) -> None:
    if insp.status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Inspection is {insp.status}; allowed: {[s.value for s in allowed]}",
        )


# ── Auto-evaluate ─────────────────────────────────────────────────────────────

def auto_evaluate_result(tr: QCTestResult) -> bool:
    """Determine is_passed based on value vs spec limits. Returns computed pass value."""
    if tr.parameter_type == ParameterType.NUMERIC:
        if tr.numeric_value is None:
            return False
        v = tr.numeric_value
        if tr.min_spec is not None and v < tr.min_spec:
            return False
        if tr.max_spec is not None and v > tr.max_spec:
            return False
        return True
    elif tr.parameter_type == ParameterType.TEXT:
        if tr.expected_text and tr.text_value:
            return tr.text_value.strip().lower() == tr.expected_text.strip().lower()
        return tr.is_passed if tr.is_passed is not None else True
    elif tr.parameter_type == ParameterType.BOOLEAN:
        # expected_text holds "true"/"false" if there's a required value
        if tr.expected_text:
            expected = tr.expected_text.strip().lower() == "true"
            return tr.boolean_value == expected
        return tr.is_passed if tr.is_passed is not None else True
    else:  # PASS_FAIL: caller must explicitly set is_passed
        return tr.is_passed if tr.is_passed is not None else False


def _compute_inspection_outcome(insp: QCInspection) -> tuple[bool, bool]:
    """Returns (all_passed, any_critical_fail)."""
    if not insp.test_results:
        return True, False
    all_passed = all(tr.is_passed for tr in insp.test_results)
    any_critical_fail = any(
        tr.is_critical and not tr.is_passed
        for tr in insp.test_results
        if tr.is_passed is not None
    )
    return all_passed, any_critical_fail


# ── Decision ─────────────────────────────────────────────────────────────────

async def make_decision(
    db: AsyncSession,
    insp: QCInspection,
    decision: QCDecision,
    decided_by_id: uuid.UUID,
    decision_notes: Optional[str],
    rework_candidate: bool,
    apply_quarantine: bool,
) -> QCInspection:
    _assert_status(insp, QCStatus.PENDING, QCStatus.IN_PROGRESS)

    insp.decision = decision
    insp.decided_by_id = decided_by_id
    insp.decided_at = datetime.now(timezone.utc)
    insp.decision_notes = decision_notes
    insp.rework_candidate = rework_candidate

    if decision == QCDecision.ACCEPT:
        insp.status = QCStatus.PASSED
    elif decision == QCDecision.REJECT:
        insp.status = QCStatus.FAILED
    elif decision == QCDecision.CONDITIONAL_RELEASE:
        insp.status = QCStatus.CONDITIONAL_RELEASE
    elif decision == QCDecision.REWORK:
        insp.status = QCStatus.FAILED
        insp.rework_candidate = True

    # Apply quarantine if requested (REJECT or CONDITIONAL with block)
    if apply_quarantine and insp.lot_id and insp.warehouse_id:
        await _quarantine_lot_stock(
            db,
            lot_id=insp.lot_id,
            warehouse_id=insp.warehouse_id,
            material_id=insp.material_id,
            product_id=insp.product_id,
            reason=f"QC {decision.value}: {insp.inspection_no}",
            user_id=decided_by_id,
        )
        insp.quarantine_applied = True

    await db.flush()
    return insp


async def _quarantine_lot_stock(
    db: AsyncSession,
    lot_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    material_id: Optional[uuid.UUID],
    product_id: Optional[uuid.UUID],
    reason: str,
    user_id: uuid.UUID,
) -> None:
    """Direct quarantine without going through the schema layer."""
    filters = [
        Stock.warehouse_id == warehouse_id,
        Stock.lot_id == lot_id,
        Stock.is_blocked == False,  # noqa: E712
    ]
    if material_id:
        filters.append(Stock.material_id == material_id)
    elif product_id:
        filters.append(Stock.product_id == product_id)

    result = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
    rows = list(result.scalars().all())
    if not rows:
        return  # No unblocked stock to quarantine — not an error

    for s in rows:
        s.is_blocked = True
        s.quantity_reserved = s.quantity_on_hand
        s.quantity_available = Decimal("0")

    now = datetime.now(timezone.utc)
    stock_type = StockType.MATERIAL if material_id else StockType.PRODUCT
    mv = StockMovement(
        reference_number=f"QC-QUAR-{now.strftime('%Y%m%d%H%M%S')}",
        movement_type=MovementType.ADJUSTMENT,
        stock_type=stock_type,
        movement_date=now.date(),
        material_id=material_id,
        product_id=product_id,
        lot_id=lot_id,
        source_warehouse_id=warehouse_id,
        quantity=Decimal("0"),
        notes=f"QC QUARANTINE: {reason}",
        created_by_id=user_id,
    )
    db.add(mv)
    await db.flush()


async def release_qc_quarantine(
    db: AsyncSession,
    insp: QCInspection,
    user_id: uuid.UUID,
    notes: Optional[str] = None,
) -> None:
    """Release quarantine on a previously quarantined inspection lot."""
    if not insp.quarantine_applied or not insp.lot_id or not insp.warehouse_id:
        raise HTTPException(422, "No quarantine to release on this inspection")

    filters = [
        Stock.warehouse_id == insp.warehouse_id,
        Stock.lot_id == insp.lot_id,
        Stock.is_blocked == True,  # noqa: E712
    ]
    result = await db.execute(select(Stock).where(and_(*filters)).with_for_update())
    rows = list(result.scalars().all())
    for s in rows:
        s.is_blocked = False
        s.quantity_reserved = Decimal("0")
        s.quantity_available = s.quantity_on_hand

    now = datetime.now(timezone.utc)
    stock_type = StockType.MATERIAL if insp.material_id else StockType.PRODUCT
    mv = StockMovement(
        reference_number=f"QC-REL-{now.strftime('%Y%m%d%H%M%S')}",
        movement_type=MovementType.ADJUSTMENT,
        stock_type=stock_type,
        movement_date=now.date(),
        material_id=insp.material_id,
        product_id=insp.product_id,
        lot_id=insp.lot_id,
        destination_warehouse_id=insp.warehouse_id,
        quantity=Decimal("0"),
        notes=f"QC RELEASE: {insp.inspection_no}. {notes or ''}".strip(),
        created_by_id=user_id,
    )
    db.add(mv)
    insp.quarantine_applied = False
    await db.flush()


# ── COA Generation ────────────────────────────────────────────────────────────

def generate_coa(insp: QCInspection) -> COAReport:
    all_passed, any_critical = _compute_inspection_outcome(insp)

    if insp.decision == QCDecision.ACCEPT:
        overall = "PASS"
    elif insp.decision in (QCDecision.REJECT, QCDecision.REWORK):
        overall = "FAIL"
    elif insp.decision == QCDecision.CONDITIONAL_RELEASE:
        overall = "CONDITIONAL"
    else:
        overall = "PENDING"

    lines = []
    for tr in (insp.test_results or []):
        if tr.numeric_value is not None:
            display = f"{tr.numeric_value} {tr.unit or ''}".strip()
        elif tr.text_value is not None:
            display = tr.text_value
        elif tr.boolean_value is not None:
            display = "Yes" if tr.boolean_value else "No"
        else:
            display = "—"

        if tr.min_spec is not None and tr.max_spec is not None:
            spec = f"{tr.min_spec} – {tr.max_spec} {tr.unit or ''}".strip()
        elif tr.min_spec is not None:
            spec = f"≥ {tr.min_spec} {tr.unit or ''}".strip()
        elif tr.max_spec is not None:
            spec = f"≤ {tr.max_spec} {tr.unit or ''}".strip()
        elif tr.expected_text:
            spec = tr.expected_text
        else:
            spec = None

        lines.append(COATestLine(
            parameter_name=tr.parameter_name,
            unit=tr.unit,
            spec_range=spec,
            result_value=display,
            is_passed=tr.is_passed,
            is_critical=tr.is_critical,
        ))

    return COAReport(
        inspection_no=insp.inspection_no,
        qc_type=insp.qc_type.value,
        inspection_date=insp.inspection_date,
        lot_number=insp.lot_number,
        batch_no=insp.batch_no,
        product_name=insp.product.name if insp.product else None,
        product_sku=insp.product.sku if insp.product else None,
        material_name=insp.material.name if insp.material else None,
        supplier_name=insp.supplier.name if insp.supplier else None,
        inspector_name=insp.inspector.full_name if insp.inspector else None,
        decision=insp.decision.value if insp.decision else None,
        decision_notes=insp.decision_notes,
        decided_at=insp.decided_at,
        overall_result=overall,
        test_lines=lines,
    )


# ── Convenience creators ──────────────────────────────────────────────────────

async def create_qc_for_grn_line(
    db: AsyncSession,
    grn_id: uuid.UUID,
    grn_line_id: uuid.UUID,
    material_id: Optional[uuid.UUID],
    supplier_id: Optional[uuid.UUID],
    warehouse_id: Optional[uuid.UUID],
    lot_number: Optional[str],
    inspection_no: str,
    inspector_id: uuid.UUID,
) -> QCInspection:
    insp = QCInspection(
        inspection_no=inspection_no,
        qc_type=QCType.INCOMING,
        status=QCStatus.PENDING,
        grn_id=grn_id,
        grn_line_id=grn_line_id,
        material_id=material_id,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        lot_number=lot_number,
        inspection_date=date.today(),
        inspector_id=inspector_id,
    )
    db.add(insp)
    await db.flush()
    return insp


async def create_qc_for_order(
    db: AsyncSession,
    production_order_id: uuid.UUID,
    product_id: Optional[uuid.UUID],
    warehouse_id: Optional[uuid.UUID],
    lot_number: Optional[str],
    batch_no: Optional[str],
    inspection_no: str,
    inspector_id: uuid.UUID,
    qc_type: QCType = QCType.IN_PROCESS,
) -> QCInspection:
    insp = QCInspection(
        inspection_no=inspection_no,
        qc_type=qc_type,
        status=QCStatus.PENDING,
        production_order_id=production_order_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        lot_number=lot_number,
        batch_no=batch_no,
        inspection_date=date.today(),
        inspector_id=inspector_id,
    )
    db.add(insp)
    await db.flush()
    return insp


# ── Stats ─────────────────────────────────────────────────────────────────────

async def get_rejection_summary(
    db: AsyncSession,
) -> List[dict]:
    """Aggregated rejection stats by material/product + supplier."""
    result = await db.execute(
        select(QCInspection).options()
        .where(QCInspection.decision.isnot(None))
        .order_by(QCInspection.material_id, QCInspection.product_id, QCInspection.supplier_id)
    )
    inspections = list(result.scalars().all())

    # Group by (material_id, product_id, supplier_id)
    groups: dict = {}
    for insp in inspections:
        key = (str(insp.material_id), str(insp.product_id), str(insp.supplier_id))
        if key not in groups:
            groups[key] = {
                "material_id": insp.material_id,
                "product_id": insp.product_id,
                "supplier_id": insp.supplier_id,
                "total": 0,
                "rejected": 0,
                "last_rejection": None,
            }
        groups[key]["total"] += 1
        if insp.decision == QCDecision.REJECT:
            groups[key]["rejected"] += 1
            d = insp.inspection_date
            if groups[key]["last_rejection"] is None or d > groups[key]["last_rejection"]:
                groups[key]["last_rejection"] = d

    return list(groups.values())
