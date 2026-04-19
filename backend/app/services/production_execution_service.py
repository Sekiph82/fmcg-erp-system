"""
Production Execution Service — core lifecycle + work order generation + genealogy.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production_execution import (
    ProdExecOrder, ExecWorkOrder, ExecOrderMaterial,
    BatchGenealogy, ExecSplitMergeLog,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _next_order_no(db: AsyncSession) -> str:
    year = datetime.now(timezone.utc).year
    result = await db.execute(
        select(func.count()).select_from(ProdExecOrder)
        .where(ProdExecOrder.order_no.like(f"PO-{year}-%"))
    )
    seq = (result.scalar() or 0) + 1
    return f"PO-{year}-{seq:05d}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


LIFECYCLE_FLOW = {
    "DRAFT":       "PLANNED",
    "PLANNED":     "RELEASED",
    "RELEASED":    "IN_PROGRESS",
    "IN_PROGRESS": "COMPLETED",
    "COMPLETED":   "CLOSED",
}


async def _load_order(db: AsyncSession, order_id: uuid.UUID) -> ProdExecOrder:
    result = await db.execute(
        select(ProdExecOrder)
        .where(ProdExecOrder.id == order_id)
        .options(
            selectinload(ProdExecOrder.work_orders),
            selectinload(ProdExecOrder.materials),
            selectinload(ProdExecOrder.genealogy_links),
            selectinload(ProdExecOrder.ai_recs),
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError(f"Production order {order_id} not found")
    return order


# ── Work order generation from routing ────────────────────────────────────────

async def _generate_work_orders(db: AsyncSession, order: ProdExecOrder) -> None:
    if not order.routing_id:
        return

    from app.models.production_advanced import RoutingStep
    steps_result = await db.execute(
        select(RoutingStep)
        .where(RoutingStep.routing_id == order.routing_id)
        .order_by(RoutingStep.step_number)
    )
    steps = steps_result.scalars().all()
    if not steps:
        return

    prev_wo_id: Optional[uuid.UUID] = None
    for step in steps:
        wo = ExecWorkOrder(
            production_order_id=order.id,
            operation_code=None,
            step_sequence=step.step_number,
            step_name=step.operation,
            work_center_id=step.work_center_id,
            planned_qty=order.planned_qty,
            setup_time_planned=Decimal(str(step.setup_time_minutes or 0)),
            run_time_planned=Decimal(str(step.standard_time_minutes or 0)),
            cleanup_time_planned=Decimal("0"),
            dependency_work_order_id=prev_wo_id,
            qc_required_flag=False,
            status="READY" if prev_wo_id is None else "PENDING",
        )
        db.add(wo)
        await db.flush()
        prev_wo_id = wo.id


async def _populate_materials_from_bom(db: AsyncSession, order: ProdExecOrder) -> None:
    if not order.bom_id:
        return

    from app.models.bom import AdvancedBOMLine
    lines_result = await db.execute(
        select(AdvancedBOMLine)
        .where(AdvancedBOMLine.bom_id == order.bom_id)
        .order_by(AdvancedBOMLine.line_no)
    )
    lines = lines_result.scalars().all()

    scale_factor = float(order.planned_qty) / 1  # assume base_qty=1 for now; will use BOM base_qty

    # Fetch BOM base_qty for proper scaling
    from app.models.bom import AdvancedBOM
    bom_result = await db.execute(select(AdvancedBOM).where(AdvancedBOM.id == order.bom_id))
    bom = bom_result.scalar_one_or_none()
    if bom and bom.base_qty and float(bom.base_qty) > 0:
        scale_factor = float(order.planned_qty) / float(bom.base_qty)

    for line in lines:
        qty = Decimal(str(float(line.required_qty) * scale_factor))
        mat = ExecOrderMaterial(
            production_order_id=order.id,
            item_type=line.item_type,
            item_id=line.item_id,
            item_name=line.item_name,
            item_code=line.item_code,
            required_qty=qty,
            uom=line.required_uom,
            status="RESERVED",
            unit_cost=line.unit_cost,
            extended_cost=Decimal(str(float(line.unit_cost or 0) * float(qty))) if line.unit_cost else None,
        )
        db.add(mat)

    # Set planned material cost
    if lines:
        total_mat_cost = sum(
            float(line.unit_cost or 0) * float(line.required_qty or 0) * scale_factor
            for line in lines
        )
        order.planned_material_cost = Decimal(str(total_mat_cost))


# ── CRUD ────────────────────────────────────────────────────────────────────────

async def create_order(db: AsyncSession, data: dict, user_id: uuid.UUID) -> ProdExecOrder:
    order_no = await _next_order_no(db)
    batch_no = data.get("batch_no") or f"BATCH-{order_no}"

    order = ProdExecOrder(
        order_no=order_no,
        batch_no=batch_no,
        created_by=user_id,
        **{k: v for k, v in data.items() if k not in {"batch_no"}},
    )
    order.batch_no = batch_no
    db.add(order)
    await db.flush()

    # Generate work orders from routing
    await _generate_work_orders(db, order)

    # Populate materials from BOM
    await _populate_materials_from_bom(db, order)

    await db.commit()
    return await _load_order(db, order.id)


async def list_orders(
    db: AsyncSession,
    status: Optional[str] = None,
    product_id: Optional[uuid.UUID] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[ProdExecOrder]:
    q = select(ProdExecOrder).order_by(ProdExecOrder.created_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(ProdExecOrder.status == status)
    if product_id:
        q = q.where(ProdExecOrder.product_id == product_id)
    result = await db.execute(q)
    return result.scalars().all()


async def get_order(db: AsyncSession, order_id: uuid.UUID) -> ProdExecOrder:
    return await _load_order(db, order_id)


async def update_order(db: AsyncSession, order_id: uuid.UUID, data: dict) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    if order.status not in {"DRAFT", "PLANNED"}:
        raise ValueError("Only DRAFT or PLANNED orders can be edited")
    for k, v in data.items():
        setattr(order, k, v)
    await db.commit()
    return await _load_order(db, order_id)


# ── Lifecycle ──────────────────────────────────────────────────────────────────

async def advance_order(db: AsyncSession, order_id: uuid.UUID) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    next_status = LIFECYCLE_FLOW.get(order.status)
    if not next_status:
        raise ValueError(f"Cannot advance order in status {order.status}")
    order.status = next_status
    if next_status == "IN_PROGRESS" and not order.actual_start:
        order.actual_start = _now()
    if next_status == "COMPLETED" and not order.actual_end:
        order.actual_end = _now()
        await _accumulate_costs(db, order)
    await db.commit()
    return await _load_order(db, order_id)


async def release_order(db: AsyncSession, order_id: uuid.UUID) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    if order.status not in {"DRAFT", "PLANNED"}:
        raise ValueError("Order must be DRAFT or PLANNED to release")
    order.status = "RELEASED"
    await db.commit()
    return await _load_order(db, order_id)


async def start_order(db: AsyncSession, order_id: uuid.UUID) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    if order.status != "RELEASED":
        raise ValueError("Order must be RELEASED to start")
    order.status = "IN_PROGRESS"
    order.actual_start = _now()
    await db.commit()
    return await _load_order(db, order_id)


async def pause_order(db: AsyncSession, order_id: uuid.UUID) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    if order.status != "IN_PROGRESS":
        raise ValueError("Order must be IN_PROGRESS to pause")
    order.status = "PAUSED"
    await db.commit()
    return await _load_order(db, order_id)


async def complete_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    completed_qty: Decimal,
    scrap_qty: Decimal = Decimal("0"),
    remarks: Optional[str] = None,
) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    if order.status not in {"IN_PROGRESS", "PAUSED"}:
        raise ValueError("Order must be IN_PROGRESS or PAUSED to complete")
    order.completed_qty = completed_qty
    order.scrap_qty = scrap_qty
    order.status = "COMPLETED"
    order.actual_end = _now()
    if remarks:
        order.remarks = remarks
    await _accumulate_costs(db, order)
    await db.commit()
    return await _load_order(db, order_id)


async def close_order(db: AsyncSession, order_id: uuid.UUID) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    if order.status != "COMPLETED":
        raise ValueError("Order must be COMPLETED to close")
    order.status = "CLOSED"
    await db.commit()
    return await _load_order(db, order_id)


async def cancel_order(db: AsyncSession, order_id: uuid.UUID) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    if order.status == "CLOSED":
        raise ValueError("Closed orders cannot be cancelled")
    order.status = "CANCELLED"
    await db.commit()
    return await _load_order(db, order_id)


async def _accumulate_costs(db: AsyncSession, order: ProdExecOrder) -> None:
    """Sum up material costs from issued materials, time costs from work orders."""
    mats_result = await db.execute(
        select(ExecOrderMaterial).where(ExecOrderMaterial.production_order_id == order.id)
    )
    mats = mats_result.scalars().all()
    actual_mat_cost = sum(
        float(m.unit_cost or 0) * float(m.consumed_qty or m.issued_qty or 0)
        for m in mats
    )

    wos_result = await db.execute(
        select(ExecWorkOrder).where(ExecWorkOrder.production_order_id == order.id)
    )
    wos = wos_result.scalars().all()
    total_run_min = sum(
        float(wo.run_time_actual or wo.run_time_planned or 0)
        for wo in wos
    )
    LABOR_COST_PER_MIN = 2.5  # KES per minute — configurable
    actual_labor = total_run_min * LABOR_COST_PER_MIN

    order.actual_material_cost = Decimal(str(round(actual_mat_cost, 2)))
    order.actual_labor_cost = Decimal(str(round(actual_labor, 2)))
    order.total_actual_cost = Decimal(str(round(actual_mat_cost + actual_labor + float(order.overhead_cost or 0), 2)))
    if order.completed_qty and float(order.completed_qty) > 0:
        order.cost_per_uom = Decimal(str(round(float(order.total_actual_cost) / float(order.completed_qty), 4)))


# ── Split / Merge ──────────────────────────────────────────────────────────────

async def split_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    split_qtys: List[Decimal],
    reason: Optional[str],
    user_id: uuid.UUID,
) -> List[ProdExecOrder]:
    order = await _load_order(db, order_id)
    if order.status not in {"DRAFT", "PLANNED", "RELEASED"}:
        raise ValueError("Only DRAFT/PLANNED/RELEASED orders can be split")

    total = sum(float(q) for q in split_qtys)
    if abs(total - float(order.planned_qty)) > 0.001:
        raise ValueError(f"Split quantities {total} must sum to {order.planned_qty}")

    child_ids = []
    child_order_no_list = []
    for qty in split_qtys:
        child_no = await _next_order_no(db)
        child_batch = f"BATCH-{child_no}"
        child = ProdExecOrder(
            order_no=child_no,
            batch_no=child_batch,
            product_id=order.product_id,
            product_name=order.product_name,
            bom_id=order.bom_id,
            bom_code=order.bom_code,
            routing_id=order.routing_id,
            planned_qty=qty,
            uom=order.uom,
            source_type=order.source_type,
            priority=order.priority,
            planned_start=order.planned_start,
            planned_end=order.planned_end,
            parent_order_id=order.id,
            is_split=True,
            status="PLANNED",
            created_by=user_id,
        )
        db.add(child)
        await db.flush()
        await _generate_work_orders(db, child)
        child_ids.append(child.id)
        child_order_no_list.append(str(child.id))

    # Log the split
    log = ExecSplitMergeLog(
        operation_type="SPLIT",
        source_order_id=order.id,
        result_order_ids=[str(cid) for cid in child_ids],
        source_qty=order.planned_qty,
        result_qtys=[float(q) for q in split_qtys],
        reason=reason,
        performed_by=user_id,
    )
    db.add(log)
    order.status = "CANCELLED"
    await db.commit()

    results = []
    for cid in child_ids:
        results.append(await _load_order(db, cid))
    return results


async def merge_orders(
    db: AsyncSession,
    order_ids: List[uuid.UUID],
    reason: Optional[str],
    user_id: uuid.UUID,
) -> ProdExecOrder:
    orders = []
    for oid in order_ids:
        o = await _load_order(db, oid)
        if o.status not in {"DRAFT", "PLANNED", "RELEASED"}:
            raise ValueError(f"Order {o.order_no} cannot be merged (status={o.status})")
        orders.append(o)

    if len({o.product_id for o in orders}) > 1:
        raise ValueError("Cannot merge orders for different products")

    total_qty = sum(float(o.planned_qty) for o in orders)
    new_no = await _next_order_no(db)
    merged = ProdExecOrder(
        order_no=new_no,
        batch_no=f"BATCH-{new_no}",
        product_id=orders[0].product_id,
        product_name=orders[0].product_name,
        bom_id=orders[0].bom_id,
        bom_code=orders[0].bom_code,
        routing_id=orders[0].routing_id,
        planned_qty=Decimal(str(total_qty)),
        uom=orders[0].uom,
        source_type="MANUAL",
        priority=min(o.priority for o in orders),
        status="PLANNED",
        created_by=user_id,
    )
    db.add(merged)
    await db.flush()
    await _generate_work_orders(db, merged)

    log = ExecSplitMergeLog(
        operation_type="MERGE",
        source_order_id=orders[0].id,
        result_order_ids=[str(merged.id)],
        source_qty=Decimal(str(total_qty)),
        result_qtys=[total_qty],
        reason=reason,
        performed_by=user_id,
    )
    db.add(log)

    for o in orders:
        o.status = "CANCELLED"

    await db.commit()
    return await _load_order(db, merged.id)


# ── Rework ─────────────────────────────────────────────────────────────────────

async def create_rework_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    qty: Decimal,
    reason: str,
    user_id: uuid.UUID,
) -> ProdExecOrder:
    order = await _load_order(db, order_id)
    new_no = await _next_order_no(db)
    rework = ProdExecOrder(
        order_no=new_no,
        batch_no=f"REWORK-{new_no}",
        product_id=order.product_id,
        product_name=order.product_name,
        bom_id=order.bom_id,
        bom_code=order.bom_code,
        routing_id=order.routing_id,
        planned_qty=qty,
        uom=order.uom,
        source_type="MANUAL",
        priority=1,
        parent_order_id=order.id,
        is_rework=True,
        rework_reason=reason,
        status="PLANNED",
        created_by=user_id,
    )
    db.add(rework)
    await db.flush()
    await _generate_work_orders(db, rework)
    order.rework_qty = (order.rework_qty or Decimal("0")) + qty
    await db.commit()
    return await _load_order(db, rework.id)


# ── Genealogy ──────────────────────────────────────────────────────────────────

async def _build_genealogy_node(
    db: AsyncSession,
    order: ProdExecOrder,
    depth: int = 0,
    visited: Optional[set] = None,
) -> dict:
    if visited is None:
        visited = set()
    if str(order.id) in visited or depth > 10:
        return {}
    visited.add(str(order.id))

    links_result = await db.execute(
        select(BatchGenealogy).where(BatchGenealogy.production_order_id == order.id)
    )
    links = links_result.scalars().all()

    children_result = await db.execute(
        select(ProdExecOrder)
        .where(ProdExecOrder.parent_order_id == order.id)
        .options(selectinload(ProdExecOrder.genealogy_links))
    )
    children = children_result.scalars().all()

    child_nodes = []
    for child in children:
        child_node = await _build_genealogy_node(db, child, depth + 1, visited)
        if child_node:
            child_nodes.append(child_node)

    return {
        "order_id": str(order.id),
        "order_no": order.order_no,
        "batch_no": order.batch_no,
        "product_name": order.product_name,
        "planned_qty": float(order.planned_qty),
        "completed_qty": float(order.completed_qty or 0),
        "status": order.status,
        "is_rework": order.is_rework,
        "is_split": order.is_split,
        "input_lots": [
            {"lot": g.input_lot_no, "item": g.input_item_name, "qty": float(g.input_qty or 0), "uom": g.input_uom}
            for g in links if g.input_lot_no
        ],
        "output_lots": [
            {"lot": g.output_lot_no, "item": g.output_item_name, "qty": float(g.output_qty or 0), "uom": g.output_uom}
            for g in links if g.output_lot_no
        ],
        "children": child_nodes,
    }


async def get_genealogy(db: AsyncSession, order_id: uuid.UUID) -> dict:
    order = await _load_order(db, order_id)
    root_node = await _build_genealogy_node(db, order)

    all_input_lots: List[str] = []
    all_output_lots: List[str] = []

    def _collect_lots(node: dict) -> None:
        for lot in node.get("input_lots", []):
            if lot.get("lot"):
                all_input_lots.append(lot["lot"])
        for lot in node.get("output_lots", []):
            if lot.get("lot"):
                all_output_lots.append(lot["lot"])
        for child in node.get("children", []):
            _collect_lots(child)

    _collect_lots(root_node)

    def _depth(node: dict) -> int:
        if not node.get("children"):
            return 0
        return 1 + max(_depth(c) for c in node["children"])

    return {
        "root": root_node,
        "all_input_lots": list(set(all_input_lots)),
        "all_output_lots": list(set(all_output_lots)),
        "depth": _depth(root_node),
    }


# ── Work Orders ────────────────────────────────────────────────────────────────

async def add_work_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    data: dict,
) -> ExecWorkOrder:
    wo = ExecWorkOrder(production_order_id=order_id, **data, status="PENDING")
    db.add(wo)
    await db.commit()
    await db.refresh(wo)
    return wo


async def start_work_order(db: AsyncSession, wo_id: uuid.UUID) -> ExecWorkOrder:
    result = await db.execute(select(ExecWorkOrder).where(ExecWorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise ValueError("Work order not found")
    if wo.status not in {"READY", "PENDING"}:
        raise ValueError(f"Cannot start work order in status {wo.status}")
    wo.status = "IN_PROGRESS"
    wo.started_at = _now()
    await db.commit()
    await db.refresh(wo)
    return wo


async def complete_work_order(
    db: AsyncSession,
    wo_id: uuid.UUID,
    completed_qty: Decimal,
    scrap_qty: Decimal,
    rework_qty: Decimal,
    setup_time_actual: Optional[Decimal],
    run_time_actual: Optional[Decimal],
    cleanup_time_actual: Optional[Decimal],
    scrap_category: Optional[str],
    scrap_reason: Optional[str],
    qc_passed: Optional[bool],
    notes: Optional[str],
) -> ExecWorkOrder:
    result = await db.execute(select(ExecWorkOrder).where(ExecWorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise ValueError("Work order not found")
    wo.status = "COMPLETED"
    wo.completed_qty = completed_qty
    wo.scrap_qty = scrap_qty
    wo.rework_qty = rework_qty
    wo.setup_time_actual = setup_time_actual
    wo.run_time_actual = run_time_actual
    wo.cleanup_time_actual = cleanup_time_actual
    wo.scrap_category = scrap_category
    wo.scrap_reason = scrap_reason
    wo.qc_passed = qc_passed
    wo.notes = notes
    wo.completed_at = _now()

    # Unblock next work order in chain
    next_result = await db.execute(
        select(ExecWorkOrder)
        .where(ExecWorkOrder.dependency_work_order_id == wo_id)
        .where(ExecWorkOrder.status == "PENDING")
    )
    next_wos = next_result.scalars().all()
    for nwo in next_wos:
        nwo.status = "READY"

    await db.commit()
    await db.refresh(wo)
    return wo


async def update_work_order(db: AsyncSession, wo_id: uuid.UUID, data: dict) -> ExecWorkOrder:
    result = await db.execute(select(ExecWorkOrder).where(ExecWorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise ValueError("Work order not found")
    for k, v in data.items():
        setattr(wo, k, v)
    await db.commit()
    await db.refresh(wo)
    return wo


async def list_work_orders(
    db: AsyncSession,
    status: Optional[str] = None,
    work_center_id: Optional[uuid.UUID] = None,
    limit: int = 200,
) -> List[ExecWorkOrder]:
    q = select(ExecWorkOrder).order_by(ExecWorkOrder.created_at.desc()).limit(limit)
    if status:
        q = q.where(ExecWorkOrder.status == status)
    if work_center_id:
        q = q.where(ExecWorkOrder.work_center_id == work_center_id)
    result = await db.execute(q)
    return result.scalars().all()


# ── Materials ──────────────────────────────────────────────────────────────────

async def add_material(
    db: AsyncSession, order_id: uuid.UUID, data: dict,
) -> ExecOrderMaterial:
    mat = ExecOrderMaterial(production_order_id=order_id, **data, status="RESERVED")
    db.add(mat)
    await db.commit()
    await db.refresh(mat)
    return mat


async def issue_material(
    db: AsyncSession,
    order_id: uuid.UUID,
    material_id: uuid.UUID,
    qty: Decimal,
    lot_no: Optional[str],
) -> ExecOrderMaterial:
    result = await db.execute(
        select(ExecOrderMaterial)
        .where(ExecOrderMaterial.id == material_id, ExecOrderMaterial.production_order_id == order_id)
    )
    mat = result.scalar_one_or_none()
    if not mat:
        raise ValueError("Material not found on this order")
    mat.issued_qty = (mat.issued_qty or Decimal("0")) + qty
    mat.status = "ISSUED"
    if lot_no:
        lots = list(mat.lot_numbers or [])
        lots.append(lot_no)
        mat.lot_numbers = lots
    await db.commit()
    await db.refresh(mat)
    return mat


async def return_material(
    db: AsyncSession,
    order_id: uuid.UUID,
    material_id: uuid.UUID,
    qty: Decimal,
) -> ExecOrderMaterial:
    result = await db.execute(
        select(ExecOrderMaterial)
        .where(ExecOrderMaterial.id == material_id, ExecOrderMaterial.production_order_id == order_id)
    )
    mat = result.scalar_one_or_none()
    if not mat:
        raise ValueError("Material not found")
    mat.returned_qty = (mat.returned_qty or Decimal("0")) + qty
    mat.status = "RETURNED"
    await db.commit()
    await db.refresh(mat)
    return mat


# ── Genealogy records ──────────────────────────────────────────────────────────

async def add_genealogy_link(
    db: AsyncSession, order_id: uuid.UUID, data: dict,
) -> BatchGenealogy:
    link = BatchGenealogy(production_order_id=order_id, **data)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


# ── Dashboard ──────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> dict:
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total = (await db.execute(select(func.count()).select_from(ProdExecOrder))).scalar() or 0

    by_status_result = await db.execute(
        select(ProdExecOrder.status, func.count())
        .group_by(ProdExecOrder.status)
    )
    by_status = dict(by_status_result.all())

    completed_today = (await db.execute(
        select(func.count()).select_from(ProdExecOrder)
        .where(ProdExecOrder.actual_end >= today_start)
        .where(ProdExecOrder.status == "COMPLETED")
    )).scalar() or 0

    delayed = (await db.execute(
        select(func.count()).select_from(ProdExecOrder)
        .where(ProdExecOrder.planned_end < now)
        .where(ProdExecOrder.status.in_(["RELEASED", "IN_PROGRESS", "PAUSED"]))
    )).scalar() or 0

    total_wo = (await db.execute(select(func.count()).select_from(ExecWorkOrder))).scalar() or 0
    pending_wo = (await db.execute(
        select(func.count()).select_from(ExecWorkOrder).where(ExecWorkOrder.status == "PENDING")
    )).scalar() or 0
    active_wo = (await db.execute(
        select(func.count()).select_from(ExecWorkOrder).where(ExecWorkOrder.status == "IN_PROGRESS")
    )).scalar() or 0

    total_scrap = (await db.execute(select(func.sum(ProdExecOrder.scrap_qty)))).scalar() or 0

    pending_ai = (await db.execute(
        select(func.count()).select_from(
            __import__("app.models.production_execution", fromlist=["ExecAIRec"]).ExecAIRec
        ).where(
            __import__("app.models.production_execution", fromlist=["ExecAIRec"]).ExecAIRec.status == "PENDING"
        )
    )).scalar() or 0

    recent_result = await db.execute(
        select(ProdExecOrder).order_by(ProdExecOrder.created_at.desc()).limit(10)
    )
    recent = recent_result.scalars().all()

    return {
        "total_orders": total,
        "draft_orders": by_status.get("DRAFT", 0),
        "released_orders": by_status.get("RELEASED", 0),
        "in_progress_orders": by_status.get("IN_PROGRESS", 0),
        "completed_today": completed_today,
        "delayed_orders": delayed,
        "total_work_orders": total_wo,
        "pending_work_orders": pending_wo,
        "active_work_orders": active_wo,
        "total_scrap_qty": float(total_scrap),
        "pending_ai_recs": pending_ai,
        "by_status": by_status,
        "recent_orders": recent,
    }
