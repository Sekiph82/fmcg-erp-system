"""
Utility Integration Service — cross-module orchestration.

Wires Utility Management to Production, Inventory, Maintenance, Quality, Finance.
Each function is self-contained: read existing data → create/link records → commit.
Callers must wrap calls in db.begin() if needed.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.utility_management import (
    UtilityBill, UtilityCostAllocation, UtilityAlarmEvent,
    TreatmentChemicalRecord, SoftWaterRecord, WastewaterRecord, BoilerSteamRecord,
    UtilityTransaction, MachineConsumptionRecord,
    BillStatus, SourceMethod,
)
from app.models.finance import (
    JournalEntry, JournalLine, ProductionCostEntry, CostType,
)
from app.models.inventory import StockMovement, Lot, MovementType, StockType
from app.models.maintenance import (
    PMWorkOrder, BreakdownRecord, PMPlan, Asset,
    PMStatus, PMFrequency, BreakdownSeverity, BreakdownStatus,
)
from app.models.quality import QCInspection
from app.models.production import ProductionOrder
from app.models.production_advanced import BatchLot, WorkOrder

logger = logging.getLogger(__name__)

_D = lambda v: Decimal(str(v)) if v is not None else Decimal("0")


# ── Function 1: post_bill_to_finance ──────────────────────────────────────────

async def post_bill_to_finance(
    db: AsyncSession,
    *,
    bill_id: UUID,
    debit_account_id: UUID,   # expense account (e.g. Utilities Expense)
    credit_account_id: UUID,  # payable account
    posted_by_id: Optional[UUID] = None,
) -> dict:
    """
    Create a balanced JournalEntry (debit expense / credit payable) for a
    utility bill and link the entry back to the bill.

    Raises ValueError if the bill is not found or already has a journal entry.
    """
    result = await db.execute(select(UtilityBill).where(UtilityBill.id == bill_id))
    bill = result.scalar_one_or_none()
    if bill is None:
        raise ValueError(f"UtilityBill {bill_id} not found")
    if bill.journal_entry_id is not None:
        raise ValueError(
            f"UtilityBill {bill_id} is already linked to journal entry {bill.journal_entry_id}"
        )

    entry_date = bill.invoice_date or date.today()
    entry_no = f"JE-UTIL-{bill.bill_no}"

    journal_entry = JournalEntry(
        id=uuid.uuid4(),
        entry_no=entry_no,
        entry_date=entry_date,
        description=f"Utility bill {bill.bill_no}",
        source_module="utility_billing",
        source_id=bill.id,
        source_ref=bill.bill_no,
        is_posted=True,
        posted_by_id=posted_by_id,
        posted_at=datetime.now(timezone.utc),
        created_by_id=posted_by_id,
        notes=f"Auto-posted from utility bill {bill.bill_no}",
    )
    db.add(journal_entry)

    debit_line = JournalLine(
        id=uuid.uuid4(),
        entry_id=journal_entry.id,
        account_id=debit_account_id,
        description=f"Utility expense — {bill.bill_no}",
        debit=bill.total_amount,
        credit=Decimal("0"),
        currency=bill.currency_code or "USD",
    )
    credit_line = JournalLine(
        id=uuid.uuid4(),
        entry_id=journal_entry.id,
        account_id=credit_account_id,
        description=f"Utility payable — {bill.bill_no}",
        debit=Decimal("0"),
        credit=bill.total_amount,
        currency=bill.currency_code or "USD",
    )
    db.add(debit_line)
    db.add(credit_line)

    await db.flush()

    bill.journal_entry_id = journal_entry.id
    db.add(bill)
    await db.flush()

    logger.info("Posted bill %s to GL as %s (amount=%s)", bill.bill_no, entry_no, bill.total_amount)
    return {
        "bill_id": bill.id,
        "journal_entry_id": journal_entry.id,
        "entry_no": entry_no,
        "amount": _D(bill.total_amount),
    }


# ── Function 2: post_allocations_to_production_costs ─────────────────────────

async def post_allocations_to_production_costs(
    db: AsyncSession,
    *,
    bill_id: UUID,
    posted_by_id: Optional[UUID] = None,
) -> dict:
    """
    For each approved UtilityCostAllocation tied to this bill that has a
    production_order_id but no production_cost_entry_id yet, create a
    ProductionCostEntry (cost_type=UTILITY) and link it back.

    Returns a summary dict with entries_created count and total cost posted.
    """
    # Load the bill for billing_period_from fallback
    bill_res = await db.execute(select(UtilityBill).where(UtilityBill.id == bill_id))
    bill = bill_res.scalar_one_or_none()
    if bill is None:
        raise ValueError(f"UtilityBill {bill_id} not found")

    alloc_res = await db.execute(
        select(UtilityCostAllocation).where(
            and_(
                UtilityCostAllocation.bill_id == bill_id,
                UtilityCostAllocation.is_approved == True,
                UtilityCostAllocation.production_order_id.isnot(None),
                UtilityCostAllocation.production_cost_entry_id.is_(None),
            )
        )
    )
    allocations = alloc_res.scalars().all()

    entries_created = 0
    total_cost_posted = Decimal("0")

    for allocation in allocations:
        # Determine period_ym
        if allocation.period_start is not None:
            period_ym = allocation.period_start.strftime("%Y-%m")
        elif bill.billing_period_from is not None:
            period_ym = bill.billing_period_from.strftime("%Y-%m")
        else:
            period_ym = date.today().strftime("%Y-%m")

        # Resolve product_id: prefer allocation's own, else from production order
        product_id = allocation.product_id
        if product_id is None and allocation.production_order_id is not None:
            po_res = await db.execute(
                select(ProductionOrder).where(
                    ProductionOrder.id == allocation.production_order_id
                )
            )
            po = po_res.scalar_one_or_none()
            if po is not None:
                product_id = po.product_id

        cost_entry = ProductionCostEntry(
            id=uuid.uuid4(),
            production_order_id=allocation.production_order_id,
            product_id=product_id,
            cost_type=CostType.UTILITY,
            amount=allocation.allocated_cost,
            period_ym=period_ym,
            notes=f"Utility cost allocation {allocation.allocation_no} from bill {bill.bill_no}",
            created_by_id=posted_by_id,
        )
        db.add(cost_entry)
        await db.flush()

        allocation.production_cost_entry_id = cost_entry.id
        db.add(allocation)

        entries_created += 1
        total_cost_posted += _D(allocation.allocated_cost)

    await db.flush()
    logger.info(
        "Posted %d allocations for bill %s — total %s",
        entries_created, bill_id, total_cost_posted,
    )
    return {
        "bill_id": bill_id,
        "entries_created": entries_created,
        "total_cost_posted": total_cost_posted,
    }


# ── Function 3: sync_chemical_to_inventory ───────────────────────────────────

async def sync_chemical_to_inventory(
    db: AsyncSession,
    *,
    record_id: UUID,
    warehouse_id: UUID,
    posted_by_id: Optional[UUID] = None,
) -> dict:
    """
    Create a StockMovement (ISSUE) for a TreatmentChemicalRecord dosing event
    and mark the record as inventory_synced.

    Raises ValueError if already synced or no material_id.
    """
    rec_res = await db.execute(
        select(TreatmentChemicalRecord).where(TreatmentChemicalRecord.id == record_id)
    )
    record = rec_res.scalar_one_or_none()
    if record is None:
        raise ValueError(f"TreatmentChemicalRecord {record_id} not found")
    if record.inventory_synced:
        raise ValueError(f"TreatmentChemicalRecord {record_id} is already inventory-synced")
    if record.material_id is None:
        raise ValueError(
            f"TreatmentChemicalRecord {record_id} has no material_id — cannot create stock movement"
        )

    quantity = record.consumed_qty if record.consumed_qty is not None else record.quantity_dosed
    if quantity is None:
        quantity = Decimal("0")

    unit_cost = record.unit_cost or Decimal("0")
    total_cost = _D(unit_cost) * _D(quantity)

    movement_date = record.date if record.date is not None else record.record_datetime.date()
    movement_ref = f"CHEM-{record.record_no}"

    movement = StockMovement(
        id=uuid.uuid4(),
        reference_number=movement_ref,
        movement_type=MovementType.ISSUE,
        stock_type=StockType.MATERIAL,
        movement_date=movement_date,
        material_id=record.material_id,
        lot_id=record.inventory_lot_id,
        source_warehouse_id=warehouse_id,
        quantity=_D(quantity),
        unit_cost=_D(unit_cost) if record.unit_cost is not None else None,
        total_cost=total_cost if total_cost > 0 else None,
        notes=f"Chemical dosing — {record.chemical_name} — record {record.record_no}",
        created_by_id=posted_by_id,
    )
    db.add(movement)
    await db.flush()

    record.inventory_movement_id = movement.id
    record.inventory_synced = True
    db.add(record)
    await db.flush()

    logger.info(
        "Synced chemical record %s → stock movement %s (qty=%s)",
        record_id, movement.id, quantity,
    )
    return {
        "record_id": record_id,
        "movement_id": movement.id,
        "movement_reference": movement_ref,
        "quantity_issued": _D(quantity),
    }


# ── Function 4: create_maintenance_action_from_alarm ─────────────────────────

_ALARM_SEVERITY_MAP = {
    "CRITICAL": BreakdownSeverity.CRITICAL,
    "ALERT":    BreakdownSeverity.HIGH,
    "WARNING":  BreakdownSeverity.MEDIUM,
    "INFO":     BreakdownSeverity.LOW,
}


async def create_maintenance_action_from_alarm(
    db: AsyncSession,
    *,
    event_id: UUID,
    action_type: str,   # "PM_WORK_ORDER" or "BREAKDOWN"
    description: str,
    scheduled_date: Optional[date] = None,
    plan_id: Optional[UUID] = None,
    assigned_to_id: Optional[UUID] = None,
    posted_by_id: Optional[UUID] = None,
) -> dict:
    """
    Create a PM work order or breakdown record from a utility alarm event and
    link it back to the event.

    Raises ValueError if the event is not found, or if action_type==BREAKDOWN
    and the linked utility asset has no maintenance_asset_id.
    """
    event_res = await db.execute(
        select(UtilityAlarmEvent).where(UtilityAlarmEvent.id == event_id)
    )
    event = event_res.scalar_one_or_none()
    if event is None:
        raise ValueError(f"UtilityAlarmEvent {event_id} not found")

    # Load linked UtilityAsset to get maintenance_asset_id
    from app.models.utility_management import UtilityAsset
    utility_asset = None
    maintenance_asset = None
    if event.asset_id is not None:
        ua_res = await db.execute(
            select(UtilityAsset).where(UtilityAsset.id == event.asset_id)
        )
        utility_asset = ua_res.scalar_one_or_none()
        if utility_asset is not None and utility_asset.maintenance_asset_id is not None:
            asset_res = await db.execute(
                select(Asset).where(Asset.id == utility_asset.maintenance_asset_id)
            )
            maintenance_asset = asset_res.scalar_one_or_none()

    if action_type == "PM_WORK_ORDER":
        # Resolve plan_id — load provided plan, or create a minimal one
        resolved_plan_id = plan_id
        if resolved_plan_id is None and maintenance_asset is not None:
            # Create a minimal PM plan on the fly
            new_plan = PMPlan(
                id=uuid.uuid4(),
                asset_id=maintenance_asset.id,
                name=f"Alarm-triggered PM — {event.event_no}",
                description=description,
                frequency=PMFrequency.MONTHLY,
                is_active=True,
            )
            db.add(new_plan)
            await db.flush()
            resolved_plan_id = new_plan.id

        if resolved_plan_id is None:
            raise ValueError(
                f"Cannot create PM work order: no plan_id provided and no maintenance asset "
                f"is linked to alarm event {event_id}"
            )

        wo = PMWorkOrder(
            id=uuid.uuid4(),
            wo_no=f"WO-ALM-{event.event_no}",
            plan_id=resolved_plan_id,
            scheduled_date=scheduled_date or date.today(),
            status=PMStatus.PENDING,
            technician=str(assigned_to_id) if assigned_to_id else None,
            checklist_notes=f"Created from alarm {event.event_no}: {description}",
        )
        db.add(wo)
        await db.flush()

        event.maintenance_work_order_id = wo.id
        db.add(event)
        await db.flush()

        logger.info("Created PM work order %s from alarm %s", wo.wo_no, event.event_no)
        return {
            "type": "PM_WORK_ORDER",
            "alarm_event_id": event_id,
            "work_order_id": wo.id,
            "wo_no": wo.wo_no,
        }

    elif action_type == "BREAKDOWN":
        if maintenance_asset is None:
            raise ValueError(
                f"Cannot create breakdown record: alarm event {event_id} has no linked "
                f"utility asset with a maintenance_asset_id"
            )

        severity = _ALARM_SEVERITY_MAP.get(
            str(event.severity.value) if event.severity else "WARNING",
            BreakdownSeverity.MEDIUM,
        )

        br = BreakdownRecord(
            id=uuid.uuid4(),
            breakdown_no=f"BR-ALM-{event.event_no}",
            asset_id=maintenance_asset.id,
            start_time=event.triggered_at or datetime.now(timezone.utc),
            reason=description,
            severity=severity,
            status=BreakdownStatus.OPEN,
            corrective_action=None,
            reported_by_id=posted_by_id,
        )
        db.add(br)
        await db.flush()

        event.breakdown_record_id = br.id
        db.add(event)
        await db.flush()

        logger.info("Created breakdown record %s from alarm %s", br.breakdown_no, event.event_no)
        return {
            "type": "BREAKDOWN",
            "alarm_event_id": event_id,
            "breakdown_id": br.id,
            "breakdown_no": br.breakdown_no,
        }

    else:
        raise ValueError(
            f"Unknown action_type '{action_type}'. Must be 'PM_WORK_ORDER' or 'BREAKDOWN'."
        )


# ── Function 5: get_production_utility_summary ───────────────────────────────

async def get_production_utility_summary(
    db: AsyncSession,
    *,
    production_order_id: UUID,
) -> dict:
    """
    Aggregate utility consumption and cost for a production order across
    UtilityTransaction and MachineConsumptionRecord, returning a per-utility-type
    breakdown and total cost.
    """
    po_res = await db.execute(
        select(ProductionOrder).where(ProductionOrder.id == production_order_id)
    )
    po = po_res.scalar_one_or_none()
    if po is None:
        raise ValueError(f"ProductionOrder {production_order_id} not found")

    # Aggregate from UtilityTransaction
    tx_rows = await db.execute(
        select(
            UtilityTransaction.utility_type,
            func.sum(UtilityTransaction.quantity).label("total_qty"),
            func.sum(UtilityTransaction.total_cost).label("total_cost"),
            func.max(UtilityTransaction.unit_of_measure).label("uom"),
        )
        .where(UtilityTransaction.production_order_id == production_order_id)
        .group_by(UtilityTransaction.utility_type)
    )
    tx_data: dict[str, dict] = {}
    for row in tx_rows:
        key = str(row.utility_type.value) if row.utility_type else "OTHER"
        tx_data[key] = {
            "utility_type": key,
            "quantity": _D(row.total_qty),
            "unit": row.uom,
            "cost": _D(row.total_cost),
        }

    # Aggregate from MachineConsumptionRecord (more granular — takes priority)
    mcr_rows = await db.execute(
        select(
            MachineConsumptionRecord.utility_type,
            func.sum(MachineConsumptionRecord.actual_consumption).label("total_qty"),
            func.sum(MachineConsumptionRecord.total_cost).label("total_cost"),
            func.max(MachineConsumptionRecord.actual_unit).label("uom"),
        )
        .where(MachineConsumptionRecord.production_order_id == production_order_id)
        .group_by(MachineConsumptionRecord.utility_type)
    )
    mcr_data: dict[str, dict] = {}
    for row in mcr_rows:
        key = str(row.utility_type.value) if row.utility_type else "OTHER"
        mcr_data[key] = {
            "utility_type": key,
            "quantity": _D(row.total_qty),
            "unit": row.uom,
            "cost": _D(row.total_cost),
        }

    # Merge: MCR takes priority where available
    merged: dict[str, dict] = {**tx_data, **mcr_data}

    total_utility_cost = sum(v["cost"] for v in merged.values())
    by_type = list(merged.values())

    return {
        "production_order_id": po.id,
        "order_no": po.order_no,
        "total_utility_cost": total_utility_cost,
        "by_type": by_type,
    }


# ── Function 6: get_maintenance_status_for_utility_asset ─────────────────────

async def get_maintenance_status_for_utility_asset(
    db: AsyncSession,
    *,
    utility_asset_id: UUID,
) -> dict:
    """
    Return PM plan status and open breakdowns for the maintenance asset linked
    to a utility asset.  Returns {"linked": False, ...} when no link exists.
    """
    from app.models.utility_management import UtilityAsset

    ua_res = await db.execute(
        select(UtilityAsset).where(UtilityAsset.id == utility_asset_id)
    )
    utility_asset = ua_res.scalar_one_or_none()
    if utility_asset is None or utility_asset.maintenance_asset_id is None:
        return {"linked": False, "utility_asset_id": str(utility_asset_id)}

    asset_res = await db.execute(
        select(Asset)
        .options(selectinload(Asset.pm_plans))
        .where(Asset.id == utility_asset.maintenance_asset_id)
    )
    asset = asset_res.scalar_one_or_none()
    if asset is None:
        return {"linked": False, "utility_asset_id": str(utility_asset_id)}

    today = date.today()

    # Overdue plans
    overdue_plans = [
        p for p in asset.pm_plans
        if p.next_due_date is not None
        and p.next_due_date < today
        and p.is_active
    ]

    # Recent breakdowns (last 3)
    bd_res = await db.execute(
        select(BreakdownRecord)
        .where(BreakdownRecord.asset_id == asset.id)
        .order_by(BreakdownRecord.created_at.desc())
        .limit(3)
    )
    recent_breakdowns = bd_res.scalars().all()

    # Open breakdowns
    open_breakdowns = [
        b for b in recent_breakdowns
        if b.status != BreakdownStatus.RESOLVED
    ]

    # All open (may be more than 3)
    open_bd_res = await db.execute(
        select(func.count()).select_from(BreakdownRecord).where(
            and_(
                BreakdownRecord.asset_id == asset.id,
                BreakdownRecord.status != BreakdownStatus.RESOLVED,
            )
        )
    )
    open_breakdown_count = open_bd_res.scalar_one() or 0

    # Next PM due
    future_plans = [
        p for p in asset.pm_plans
        if p.next_due_date is not None and p.is_active
    ]
    next_pm_due: Optional[date] = (
        min(p.next_due_date for p in future_plans) if future_plans else None
    )

    return {
        "linked": True,
        "utility_asset_id": utility_asset_id,
        "maintenance_asset_id": asset.id,
        "asset_name": asset.name,
        "asset_status": str(asset.status.value) if asset.status else None,
        "overdue_pm_count": len(overdue_plans),
        "open_breakdown_count": open_breakdown_count,
        "next_pm_due": next_pm_due,
        "pm_plans": [
            {
                "id": p.id,
                "name": p.name,
                "next_due_date": p.next_due_date,
                "status": None,  # PMPlan has no direct status field; derived from next_due_date
            }
            for p in asset.pm_plans
        ],
        "recent_breakdowns": [
            {
                "id": b.id,
                "breakdown_no": b.breakdown_no,
                "severity": str(b.severity.value) if b.severity else "MEDIUM",
                "status": str(b.status.value) if b.status else "OPEN",
            }
            for b in recent_breakdowns
        ],
    }


# ── Function 7: get_quality_inspections_for_utility ──────────────────────────

async def get_quality_inspections_for_utility(
    db: AsyncSession,
    *,
    utility_asset_id: UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[dict]:
    """
    Return QCInspections linked (via qc_inspection_id) to SoftWaterRecord,
    WastewaterRecord, or BoilerSteamRecord records belonging to a utility asset.

    Optionally filtered by inspection_date range.
    """
    # Collect qc_inspection_ids from the three record types for this asset
    qc_ids: set[UUID] = set()

    for model_cls in (SoftWaterRecord, WastewaterRecord, BoilerSteamRecord):
        res = await db.execute(
            select(model_cls.qc_inspection_id).where(  # type: ignore[attr-defined]
                and_(
                    model_cls.asset_id == utility_asset_id,  # type: ignore[attr-defined]
                    model_cls.qc_inspection_id.isnot(None),  # type: ignore[attr-defined]
                )
            )
        )
        for (qc_id,) in res:
            if qc_id is not None:
                qc_ids.add(qc_id)

    if not qc_ids:
        return []

    # Load QCInspections by those IDs with optional date filter
    filters = [QCInspection.id.in_(list(qc_ids))]
    if date_from is not None:
        filters.append(QCInspection.inspection_date >= date_from)
    if date_to is not None:
        filters.append(QCInspection.inspection_date <= date_to)

    insp_res = await db.execute(
        select(QCInspection)
        .where(and_(*filters))
        .order_by(QCInspection.inspection_date.desc())
    )
    inspections = insp_res.scalars().all()

    return [
        {
            "inspection_id": insp.id,
            "inspection_no": insp.inspection_no,
            "qc_type": str(insp.qc_type.value) if insp.qc_type else None,
            "status": str(insp.status.value) if insp.status else None,
            "decision": str(insp.decision.value) if insp.decision else None,
            "inspection_date": insp.inspection_date,
            "lot_number": insp.lot_number,
            "batch_no": insp.batch_no,
        }
        for insp in inspections
    ]
