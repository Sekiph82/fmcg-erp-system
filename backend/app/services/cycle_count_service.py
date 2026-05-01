"""Cycle Counting service — plans, tasks, entries, adjustments, ABC, AI."""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cycle_count import (
    ABCClass, ABCClassification, AdjustmentStatus, CountAdjustment,
    CountEntry, CycleCountPlan, CycleCountTask,
    PlanStatus, PlanType, TaskStatus,
)
from app.models.inventory import MovementType, Stock, StockMovement, StockType
from app.schemas.cycle_count import (
    AdjustmentApprove, AdjustmentReject, CountEntryCreate,
    PlanCreate, PlanUpdate, TaskCreate, TaskUpdate,
)

# ABC thresholds (cumulative % of stock value)
ABC_A_THRESHOLD = 70.0   # top 70% of value → A
ABC_B_THRESHOLD = 90.0   # 70–90% → B; rest → C

ABC_FREQUENCY = {ABCClass.A: 7, ABCClass.B: 30, ABCClass.C: 90}


# ── Sequence helpers ──────────────────────────────────────────────────────────

async def _next_plan_code(db: AsyncSession) -> str:
    r = await db.execute(select(func.count()).select_from(CycleCountPlan))
    n = (r.scalar_one() or 0) + 1
    return f"CCP-{n:05d}"


async def _next_task_no(db: AsyncSession) -> str:
    r = await db.execute(select(func.count()).select_from(CycleCountTask))
    n = (r.scalar_one() or 0) + 1
    return f"CCT-{n:06d}"


async def _next_movement_ref(db: AsyncSession) -> str:
    r = await db.execute(select(func.count()).select_from(StockMovement))
    n = (r.scalar_one() or 0) + 1
    return f"ADJ-CC-{n:06d}"


# ── Plan CRUD ─────────────────────────────────────────────────────────────────

async def list_plans(
    db: AsyncSession,
    warehouse_id: Optional[UUID] = None,
    status: Optional[PlanStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[CycleCountPlan]:
    q = select(CycleCountPlan).order_by(desc(CycleCountPlan.created_at))
    if warehouse_id:
        q = q.where(CycleCountPlan.warehouse_id == warehouse_id)
    if status:
        q = q.where(CycleCountPlan.status == status)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_plan(db: AsyncSession, plan_id: UUID) -> Optional[CycleCountPlan]:
    result = await db.execute(select(CycleCountPlan).where(CycleCountPlan.id == plan_id))
    return result.scalar_one_or_none()


async def create_plan(
    db: AsyncSession, data: PlanCreate, user_id: Optional[UUID] = None
) -> CycleCountPlan:
    plan_code = data.plan_code or await _next_plan_code(db)
    plan = CycleCountPlan(**data.model_dump(exclude={"plan_code"}), plan_code=plan_code, created_by_id=user_id)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def update_plan(
    db: AsyncSession, plan_id: UUID, data: PlanUpdate
) -> Optional[CycleCountPlan]:
    plan = await get_plan(db, plan_id)
    if not plan:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, val)
    await db.commit()
    await db.refresh(plan)
    return plan


# ── Task generation ───────────────────────────────────────────────────────────

async def generate_tasks(
    db: AsyncSession,
    plan: CycleCountPlan,
    target_date: date,
) -> List[CycleCountTask]:
    """Auto-generate counting tasks from a plan."""
    tasks: List[CycleCountTask] = []

    if plan.plan_type in (PlanType.ABC, PlanType.FREQUENCY):
        # Pull ABC classifications for warehouse
        abc_filter = list(plan.abc_classes.upper()) if plan.abc_classes else ["A", "B", "C"]
        result = await db.execute(
            select(ABCClassification).where(
                and_(
                    ABCClassification.warehouse_id == plan.warehouse_id,
                    ABCClassification.abc_class.in_(abc_filter),
                )
            )
        )
        classifications = list(result.scalars().all())

        for cls in classifications:
            task = CycleCountTask(
                task_no=await _next_task_no(db),
                plan_id=plan.id,
                warehouse_id=plan.warehouse_id,
                product_id=cls.product_id,
                material_id=cls.material_id,
                abc_class=cls.abc_class,
                scheduled_date=target_date,
                status=TaskStatus.PENDING,
            )
            db.add(task)
            tasks.append(task)

    elif plan.plan_type == PlanType.RANDOM:
        # Random sample: pick items with stock at this warehouse
        result = await db.execute(
            select(Stock).where(
                and_(
                    Stock.warehouse_id == plan.warehouse_id,
                    Stock.quantity_on_hand > 0,
                )
            ).order_by(func.random()).limit(20)
        )
        stocks = list(result.scalars().all())
        for s in stocks:
            task = CycleCountTask(
                task_no=await _next_task_no(db),
                plan_id=plan.id,
                warehouse_id=plan.warehouse_id,
                product_id=s.product_id,
                material_id=s.material_id,
                location_id=s.location_id,
                scheduled_date=target_date,
                status=TaskStatus.PENDING,
            )
            db.add(task)
            tasks.append(task)

    await db.flush()
    return tasks


# ── Task CRUD ─────────────────────────────────────────────────────────────────

async def list_tasks(
    db: AsyncSession,
    plan_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    status: Optional[TaskStatus] = None,
    assigned_to_id: Optional[UUID] = None,
    scheduled_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[CycleCountTask]:
    q = select(CycleCountTask).order_by(CycleCountTask.scheduled_date, CycleCountTask.task_no)
    if plan_id:
        q = q.where(CycleCountTask.plan_id == plan_id)
    if warehouse_id:
        q = q.where(CycleCountTask.warehouse_id == warehouse_id)
    if status:
        q = q.where(CycleCountTask.status == status)
    if assigned_to_id:
        q = q.where(CycleCountTask.assigned_to_id == assigned_to_id)
    if scheduled_date:
        q = q.where(CycleCountTask.scheduled_date == scheduled_date)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: UUID) -> Optional[CycleCountTask]:
    result = await db.execute(select(CycleCountTask).where(CycleCountTask.id == task_id))
    return result.scalar_one_or_none()


async def create_task(db: AsyncSession, data: TaskCreate) -> CycleCountTask:
    task = CycleCountTask(task_no=await _next_task_no(db), **data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(db: AsyncSession, task_id: UUID, data: TaskUpdate) -> Optional[CycleCountTask]:
    task = await get_task(db, task_id)
    if not task:
        return None
    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(task, field, val)
    if data.status == TaskStatus.COMPLETED and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return task


# ── Count entries ─────────────────────────────────────────────────────────────

async def _get_system_qty(
    db: AsyncSession,
    warehouse_id: UUID,
    product_id: Optional[UUID],
    material_id: Optional[UUID],
    lot_id: Optional[UUID],
    location_id: Optional[UUID],
) -> Decimal:
    """Look up current on-hand qty from Stock table."""
    q = select(func.sum(Stock.quantity_on_hand)).where(
        Stock.warehouse_id == warehouse_id
    )
    if product_id:
        q = q.where(Stock.product_id == product_id)
    if material_id:
        q = q.where(Stock.material_id == material_id)
    if lot_id:
        q = q.where(Stock.lot_id == lot_id)
    if location_id:
        q = q.where(Stock.location_id == location_id)
    result = await db.execute(q)
    return Decimal(str(result.scalar_one() or 0))


async def create_count_entry(
    db: AsyncSession,
    data: CountEntryCreate,
    user_id: Optional[UUID],
    tolerance_pct: Decimal = Decimal("2.0"),
    auto_approve: bool = True,
) -> CountEntry:
    task = await get_task(db, data.task_id)
    if not task:
        raise ValueError("Task not found")

    system_qty = await _get_system_qty(
        db,
        warehouse_id=task.warehouse_id,
        product_id=data.product_id or task.product_id,
        material_id=data.material_id or task.material_id,
        lot_id=data.lot_id,
        location_id=data.location_id or task.location_id,
    )

    variance_qty = data.counted_qty - system_qty
    variance_pct = (abs(variance_qty) / system_qty * 100) if system_qty != 0 else Decimal("100")
    variance_value = variance_qty * data.unit_cost if data.unit_cost else None
    within_tolerance = abs(variance_pct) <= tolerance_pct

    entry = CountEntry(
        task_id=data.task_id,
        product_id=data.product_id or task.product_id,
        material_id=data.material_id or task.material_id,
        lot_id=data.lot_id,
        location_id=data.location_id or task.location_id,
        system_qty=system_qty,
        counted_qty=data.counted_qty,
        variance_qty=variance_qty,
        variance_pct=variance_pct,
        unit_cost=data.unit_cost,
        variance_value=variance_value,
        unit=data.unit,
        within_tolerance=within_tolerance,
        root_cause=data.root_cause,
        counted_by_id=user_id,
        counted_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()

    # Create adjustment record
    adj_status = AdjustmentStatus.APPROVED if (within_tolerance and auto_approve) else AdjustmentStatus.PENDING
    adjustment = CountAdjustment(
        entry_id=entry.id,
        status=adj_status,
        adjustment_qty=variance_qty,
        adjustment_value=variance_value,
        notes="Auto-approved within tolerance" if adj_status == AdjustmentStatus.APPROVED else None,
    )
    if adj_status == AdjustmentStatus.APPROVED:
        adjustment.approved_at = datetime.now(timezone.utc)
    db.add(adjustment)

    # Mark task in_progress
    if task.status == TaskStatus.PENDING:
        task.status = TaskStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(entry)

    # Post adjustment immediately if auto-approved
    if adj_status == AdjustmentStatus.APPROVED and variance_qty != 0:
        await _post_stock_adjustment(db, entry, adjustment)

    return entry


async def list_entries(
    db: AsyncSession,
    task_id: Optional[UUID] = None,
    within_tolerance: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[CountEntry]:
    q = select(CountEntry).order_by(desc(CountEntry.counted_at))
    if task_id:
        q = q.where(CountEntry.task_id == task_id)
    if within_tolerance is not None:
        q = q.where(CountEntry.within_tolerance == within_tolerance)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


# ── Variance approval / rejection ─────────────────────────────────────────────

async def approve_adjustments(
    db: AsyncSession,
    data: AdjustmentApprove,
    approver_id: UUID,
) -> int:
    count = 0
    for entry_id in data.entry_ids:
        entry_r = await db.execute(select(CountEntry).where(CountEntry.id == entry_id))
        entry = entry_r.scalar_one_or_none()
        if not entry or not entry.adjustment:
            continue
        adj = entry.adjustment
        if adj.status != AdjustmentStatus.PENDING:
            continue
        adj.status = AdjustmentStatus.APPROVED
        adj.approved_by_id = approver_id
        adj.approved_at = datetime.now(timezone.utc)
        adj.notes = data.notes
        await db.flush()
        if entry.variance_qty != 0:
            await _post_stock_adjustment(db, entry, adj)
        count += 1
    await db.commit()
    return count


async def reject_adjustments(
    db: AsyncSession,
    data: AdjustmentReject,
    reviewer_id: UUID,
) -> int:
    count = 0
    for entry_id in data.entry_ids:
        entry_r = await db.execute(select(CountEntry).where(CountEntry.id == entry_id))
        entry = entry_r.scalar_one_or_none()
        if not entry or not entry.adjustment:
            continue
        adj = entry.adjustment
        if adj.status != AdjustmentStatus.PENDING:
            continue
        adj.status = AdjustmentStatus.REJECTED
        adj.approved_by_id = reviewer_id
        adj.approved_at = datetime.now(timezone.utc)
        adj.rejection_reason = data.rejection_reason
        count += 1
    await db.commit()
    return count


# ── Stock adjustment posting ──────────────────────────────────────────────────

async def _post_stock_adjustment(
    db: AsyncSession,
    entry: CountEntry,
    adjustment: CountAdjustment,
) -> None:
    """Write adjustment to Stock and create StockMovement ledger entry."""
    if adjustment.posted_flag:
        return

    ref = await _next_movement_ref(db)

    # Determine stock_type
    stock_type = StockType.PRODUCT if entry.product_id else StockType.MATERIAL

    # Update Stock record
    q = select(Stock).where(
        and_(
            Stock.product_id == entry.product_id if entry.product_id else Stock.material_id == entry.material_id,
        )
    )
    if entry.location_id:
        q = q.where(Stock.location_id == entry.location_id)
    if entry.lot_id:
        q = q.where(Stock.lot_id == entry.lot_id)

    stock_r = await db.execute(q)
    stock = stock_r.scalar_one_or_none()
    if stock:
        stock.quantity_on_hand = stock.quantity_on_hand + adjustment.adjustment_qty
        stock.quantity_available = stock.quantity_available + adjustment.adjustment_qty

    # Create StockMovement
    movement = StockMovement(
        reference_number=ref,
        movement_type=MovementType.ADJUSTMENT,
        stock_type=stock_type,
        movement_date=date.today(),
        product_id=entry.product_id,
        material_id=entry.material_id,
        lot_id=entry.lot_id,
        source_warehouse_id=None,
        destination_warehouse_id=None,
        quantity=adjustment.adjustment_qty,
        unit_cost=entry.unit_cost,
        total_cost=adjustment.adjustment_value,
        notes=f"Cycle count adjustment — task entry {entry.id}",
    )
    db.add(movement)

    adjustment.posted_flag = True
    adjustment.stock_movement_ref = ref
    adjustment.status = AdjustmentStatus.POSTED
    await db.flush()


# ── Adjustment queries ────────────────────────────────────────────────────────

async def list_adjustments(
    db: AsyncSession,
    status: Optional[AdjustmentStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[CountAdjustment]:
    q = select(CountAdjustment).order_by(desc(CountAdjustment.created_at))
    if status:
        q = q.where(CountAdjustment.status == status)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


# ── ABC Classification ────────────────────────────────────────────────────────

async def run_abc_classification(db: AsyncSession, warehouse_id: UUID) -> int:
    """Compute ABC classification for all stocked items in warehouse."""
    # Get all stocks with value
    result = await db.execute(
        select(Stock).where(
            and_(Stock.warehouse_id == warehouse_id, Stock.quantity_on_hand > 0)
        )
    )
    stocks = list(result.scalars().all())

    # Compute stock value — use product/material cost or quantity as proxy
    items: List[Dict[str, Any]] = []
    for s in stocks:
        items.append({
            "product_id": s.product_id,
            "material_id": s.material_id,
            "value": float(s.quantity_on_hand),  # proxy: quantity (cost would need join)
        })

    if not items:
        return 0

    total_value = sum(i["value"] for i in items)
    items.sort(key=lambda x: x["value"], reverse=True)

    today = date.today()
    cumulative = 0.0
    count = 0

    for item in items:
        cumulative += item["value"]
        pct = (cumulative / total_value * 100) if total_value > 0 else 0
        abc = ABCClass.A if pct <= ABC_A_THRESHOLD else (ABCClass.B if pct <= ABC_B_THRESHOLD else ABCClass.C)

        # Upsert
        existing_r = await db.execute(
            select(ABCClassification).where(
                and_(
                    ABCClassification.warehouse_id == warehouse_id,
                    ABCClassification.product_id == item["product_id"],
                    ABCClassification.material_id == item["material_id"],
                )
            )
        )
        existing = existing_r.scalar_one_or_none()
        if existing:
            existing.abc_class = abc
            existing.stock_value = Decimal(str(item["value"]))
            existing.classification_date = today
            existing.count_frequency_days = ABC_FREQUENCY[abc]
        else:
            db.add(ABCClassification(
                warehouse_id=warehouse_id,
                product_id=item["product_id"],
                material_id=item["material_id"],
                abc_class=abc,
                stock_value=Decimal(str(item["value"])),
                classification_date=today,
                count_frequency_days=ABC_FREQUENCY[abc],
            ))
        count += 1

    await db.commit()
    return count


async def list_abc_classifications(
    db: AsyncSession,
    warehouse_id: Optional[UUID] = None,
    abc_class: Optional[ABCClass] = None,
    skip: int = 0,
    limit: int = 200,
) -> List[ABCClassification]:
    q = select(ABCClassification).order_by(desc(ABCClassification.stock_value))
    if warehouse_id:
        q = q.where(ABCClassification.warehouse_id == warehouse_id)
    if abc_class:
        q = q.where(ABCClassification.abc_class == abc_class)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> Dict[str, Any]:
    today = date.today()
    t7d = today - timedelta(days=7)

    total_plans_r = await db.execute(select(func.count()).select_from(CycleCountPlan))
    total_plans = total_plans_r.scalar_one()

    active_plans_r = await db.execute(
        select(func.count()).where(CycleCountPlan.status == PlanStatus.ACTIVE)
    )
    active_plans = active_plans_r.scalar_one()

    tasks_today_r = await db.execute(
        select(func.count()).where(CycleCountTask.scheduled_date == today)
    )
    tasks_today = tasks_today_r.scalar_one()

    tasks_overdue_r = await db.execute(
        select(func.count()).where(
            and_(
                CycleCountTask.scheduled_date < today,
                CycleCountTask.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            )
        )
    )
    tasks_overdue = tasks_overdue_r.scalar_one()

    tasks_pending_r = await db.execute(
        select(func.count()).where(CycleCountTask.status == TaskStatus.PENDING)
    )
    tasks_pending = tasks_pending_r.scalar_one()

    tasks_done_today_r = await db.execute(
        select(func.count()).where(
            and_(
                CycleCountTask.status == TaskStatus.COMPLETED,
                CycleCountTask.scheduled_date == today,
            )
        )
    )
    tasks_done_today = tasks_done_today_r.scalar_one()

    # Accuracy: entries within tolerance / total entries in last 7d
    total_entries_r = await db.execute(
        select(func.count()).where(CountEntry.counted_at >= datetime.combine(t7d, datetime.min.time()))
    )
    total_entries = total_entries_r.scalar_one() or 1

    accurate_entries_r = await db.execute(
        select(func.count()).where(
            and_(
                CountEntry.within_tolerance == True,  # noqa: E712
                CountEntry.counted_at >= datetime.combine(t7d, datetime.min.time()),
            )
        )
    )
    accurate_entries = accurate_entries_r.scalar_one()
    accuracy_pct = round(accurate_entries / total_entries * 100, 2)

    open_variances_r = await db.execute(
        select(func.count()).where(
            and_(CountEntry.within_tolerance == False)  # noqa: E712
        )
    )
    open_variances = open_variances_r.scalar_one()

    pending_adj_r = await db.execute(
        select(func.count()).where(CountAdjustment.status == AdjustmentStatus.PENDING)
    )
    pending_adj = pending_adj_r.scalar_one()

    recent_var_r = await db.execute(
        select(CountEntry)
        .where(CountEntry.within_tolerance == False)  # noqa: E712
        .order_by(desc(CountEntry.counted_at))
        .limit(5)
    )
    recent_variances = [
        {
            "id": str(e.id),
            "variance_qty": float(e.variance_qty),
            "variance_pct": float(e.variance_pct or 0),
            "variance_value": float(e.variance_value or 0),
            "counted_at": str(e.counted_at),
        }
        for e in recent_var_r.scalars().all()
    ]

    return {
        "total_plans": total_plans,
        "active_plans": active_plans,
        "tasks_today": tasks_today,
        "tasks_overdue": tasks_overdue,
        "tasks_pending": tasks_pending,
        "tasks_completed_today": tasks_done_today,
        "accuracy_pct_7d": accuracy_pct,
        "open_variances": open_variances,
        "pending_adjustments": pending_adj,
        "recent_variances": recent_variances,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

async def accuracy_report(db: AsyncSession, days: int = 30) -> Dict[str, Any]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    total_r = await db.execute(select(func.count()).where(CountEntry.counted_at >= since))
    total = total_r.scalar_one() or 1
    accurate_r = await db.execute(
        select(func.count()).where(
            and_(CountEntry.within_tolerance == True, CountEntry.counted_at >= since)  # noqa: E712
        )
    )
    accurate = accurate_r.scalar_one()

    variance_r = await db.execute(
        select(func.sum(func.abs(CountEntry.variance_value))).where(
            and_(CountEntry.counted_at >= since, CountEntry.variance_value.isnot(None))
        )
    )
    total_variance_value = float(variance_r.scalar_one() or 0)

    return {
        "period_days": days,
        "total_entries": total,
        "accurate_entries": accurate,
        "accuracy_pct": round(accurate / total * 100, 2),
        "total_variance_value": total_variance_value,
        "inaccurate_entries": total - accurate,
    }


async def variance_report(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(CountEntry)
        .where(
            and_(
                CountEntry.within_tolerance == False,  # noqa: E712
                CountEntry.counted_at >= since,
            )
        )
        .order_by(desc(CountEntry.variance_value))
        .limit(100)
    )
    return [
        {
            "id": str(e.id),
            "product_id": str(e.product_id) if e.product_id else None,
            "material_id": str(e.material_id) if e.material_id else None,
            "system_qty": float(e.system_qty),
            "counted_qty": float(e.counted_qty),
            "variance_qty": float(e.variance_qty),
            "variance_pct": float(e.variance_pct or 0),
            "variance_value": float(e.variance_value or 0),
            "root_cause": e.root_cause,
            "counted_at": str(e.counted_at),
        }
        for e in result.scalars().all()
    ]


async def completion_report(db: AsyncSession, days: int = 30) -> Dict[str, Any]:
    since = date.today() - timedelta(days=days)
    total_r = await db.execute(
        select(func.count()).where(CycleCountTask.scheduled_date >= since)
    )
    total = total_r.scalar_one() or 1

    by_status_r = await db.execute(
        select(CycleCountTask.status, func.count())
        .where(CycleCountTask.scheduled_date >= since)
        .group_by(CycleCountTask.status)
    )
    by_status = {str(r[0].value): r[1] for r in by_status_r.all()}

    completed = by_status.get("completed", 0) + by_status.get("approved", 0)
    return {
        "period_days": days,
        "total_tasks": total,
        "by_status": by_status,
        "completion_pct": round(completed / total * 100, 2),
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def ai_variance_analyzer(db: AsyncSession) -> Dict[str, Any]:
    """AI Agent 1: Detect items with recurring discrepancies."""
    since = datetime.now(timezone.utc) - timedelta(days=90)
    result = await db.execute(
        select(
            CountEntry.product_id,
            CountEntry.material_id,
            func.count().label("total_counts"),
            func.sum(
                func.cast(CountEntry.within_tolerance == False, type_=None)  # noqa: E712
            ).label("variance_count"),
            func.avg(func.abs(CountEntry.variance_pct)).label("avg_variance_pct"),
        )
        .where(CountEntry.counted_at >= since)
        .group_by(CountEntry.product_id, CountEntry.material_id)
        .having(func.count() >= 2)
        .order_by(desc("variance_count"))
        .limit(20)
    )

    flagged = []
    for r in result.all():
        if r[3] and r[3] > 1:
            flagged.append({
                "product_id": str(r[0]) if r[0] else None,
                "material_id": str(r[1]) if r[1] else None,
                "total_counts": r[2],
                "variance_count": r[3],
                "avg_variance_pct": round(float(r[4] or 0), 2),
                "recommendation": "Investigate root cause — physical security, handling, or system data issue",
                "priority": "HIGH" if r[3] >= 3 else "MEDIUM",
            })

    return {
        "agent": "Variance Analyzer",
        "analysis_period_days": 90,
        "recurring_discrepancy_items": flagged,
        "summary": f"{len(flagged)} item(s) show recurring count discrepancies.",
    }


async def ai_count_optimizer(db: AsyncSession) -> Dict[str, Any]:
    """AI Agent 2: Suggest optimal counting frequency based on variance history."""
    since = datetime.now(timezone.utc) - timedelta(days=90)

    # Items counted less often than their ABC class recommends
    abc_result = await db.execute(
        select(ABCClassification).order_by(ABCClassification.abc_class)
    )
    classifications = list(abc_result.scalars().all())

    recommendations = []
    for cls in classifications:
        # Count how many times this item was counted in last 90d
        count_r = await db.execute(
            select(func.count()).where(
                and_(
                    CountEntry.product_id == cls.product_id if cls.product_id else CountEntry.material_id == cls.material_id,
                    CountEntry.counted_at >= since,
                )
            )
        )
        actual_counts = count_r.scalar_one()
        expected_counts = 90 // (cls.count_frequency_days or 90)

        if actual_counts < expected_counts:
            recommendations.append({
                "product_id": str(cls.product_id) if cls.product_id else None,
                "material_id": str(cls.material_id) if cls.material_id else None,
                "abc_class": cls.abc_class.value,
                "expected_counts_90d": expected_counts,
                "actual_counts_90d": actual_counts,
                "recommended_frequency_days": cls.count_frequency_days,
                "suggestion": f"Class {cls.abc_class.value} item should be counted every {cls.count_frequency_days}d — currently undercounted",
            })

    return {
        "agent": "Count Optimizer",
        "analysis_period_days": 90,
        "undercounted_items": recommendations[:20],
        "total_undercounted": len(recommendations),
        "note": "Recommendations do not auto-schedule counts — review and action manually.",
    }
