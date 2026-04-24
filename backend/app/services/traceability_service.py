"""
Lot Traceability Service — forward/backward trace, genealogy graph, search.
"""
from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Set

from sqlalchemy import select, func, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.traceability import (
    TraceEvent, TraceEventLine, LotGenealogyLink,
    TraceEventType, TraceItemStage, GenealogyRelType,
)
from app.models.inventory import Lot, Stock
from app.schemas.traceability import (
    TraceEventCreate, TraceEventOut, TraceEventLineOut,
    GenealogyLinkCreate, GenealogyLinkOut,
    GenealogyTree, GenealogyNode,
    TraceabilitySearchRequest, TraceabilitySearchResult,
    ForwardTraceResult, BackwardTraceResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# Trace Event CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def create_trace_event(db: AsyncSession, data: TraceEventCreate) -> TraceEvent:
    lines_data = data.lines
    event = TraceEvent(**{k: v for k, v in data.model_dump().items() if k != "lines"})
    db.add(event)
    await db.flush()

    for l in lines_data:
        line = TraceEventLine(event_id=event.id, **l.model_dump())
        db.add(line)

        # Auto-create genealogy link if source_lot → child_lot
        if l.source_lot_id and l.child_lot_id:
            rel = _infer_rel_type(data.trace_event_type)
            link = LotGenealogyLink(
                parent_lot_id=l.source_lot_id,
                child_lot_id=l.child_lot_id,
                relationship_type=rel,
                source_document_type=data.source_document_type,
                source_document_id=data.source_document_id,
                production_order_id=data.production_order_id,
                quantity_linked=l.quantity,
                uom=l.uom,
                parent_stage=l.source_stage,
                child_stage=l.dest_stage,
            )
            db.add(link)

    await db.commit()
    await db.refresh(event)
    return event


def _infer_rel_type(event_type: TraceEventType) -> GenealogyRelType:
    mapping = {
        TraceEventType.transformation: GenealogyRelType.intermediate_from,
        TraceEventType.packaging:      GenealogyRelType.packed_from,
        TraceEventType.rework:         GenealogyRelType.reworked_from,
        TraceEventType.consumption:    GenealogyRelType.bulk_from,
        TraceEventType.receipt:        GenealogyRelType.received_from,
    }
    return mapping.get(event_type, GenealogyRelType.prepared_from)


async def list_trace_events(db: AsyncSession, lot_id: Optional[uuid.UUID] = None,
                             event_type: Optional[TraceEventType] = None,
                             limit: int = 200) -> List[TraceEvent]:
    q = select(TraceEvent).order_by(desc(TraceEvent.event_datetime)).limit(limit)
    if event_type:
        q = q.where(TraceEvent.trace_event_type == event_type)
    if lot_id:
        # Get events that have a line mentioning this lot
        subq = (
            select(TraceEventLine.event_id)
            .where(
                (TraceEventLine.source_lot_id == lot_id) |
                (TraceEventLine.child_lot_id  == lot_id)
            )
        )
        q = q.where(TraceEvent.id.in_(subq))
    r = await db.execute(q)
    return list(r.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Genealogy Link CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def create_genealogy_link(db: AsyncSession, data: GenealogyLinkCreate) -> LotGenealogyLink:
    link = LotGenealogyLink(**data.model_dump())
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def list_genealogy_links(db: AsyncSession, lot_id: uuid.UUID,
                                direction: str = "both") -> List[LotGenealogyLink]:
    conditions = []
    if direction in ("both", "forward"):
        conditions.append(LotGenealogyLink.parent_lot_id == lot_id)
    if direction in ("both", "backward"):
        conditions.append(LotGenealogyLink.child_lot_id == lot_id)

    from sqlalchemy import or_
    q = select(LotGenealogyLink).where(or_(*conditions)) if conditions else select(LotGenealogyLink)
    r = await db.execute(q)
    return list(r.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Forward Traceability
# ─────────────────────────────────────────────────────────────────────────────

async def forward_trace(db: AsyncSession, root_lot_id: uuid.UUID,
                         max_depth: int = 10) -> ForwardTraceResult:
    """
    Forward trace: given a lot, find all descendent lots (what it became),
    all shipments, and all customers that received it.
    """
    visited: Set[uuid.UUID] = set()
    queue: deque[tuple[uuid.UUID, int]] = deque([(root_lot_id, 0)])
    affected_lots: List[Dict[str, Any]] = []
    affected_shipments: List[Dict[str, Any]] = []
    customer_ids: Set[uuid.UUID] = set()

    qty_in_stock = Decimal("0")
    qty_shipped  = Decimal("0")
    qty_returned = Decimal("0")
    qty_scrapped = Decimal("0")
    qty_quarantined = Decimal("0")
    qty_reworked    = Decimal("0")

    while queue:
        lot_id, depth = queue.popleft()
        if lot_id in visited or depth > max_depth:
            continue
        visited.add(lot_id)

        lot = await db.get(Lot, lot_id)
        if not lot:
            continue

        # Stock status for this lot
        stock_r = await db.execute(select(Stock).where(Stock.lot_id == lot_id))
        stocks = list(stock_r.scalars().all())
        for s in stocks:
            qty_in_stock += s.quantity_available

        # Event lines referencing this lot as source
        lines_r = await db.execute(
            select(TraceEventLine).where(TraceEventLine.source_lot_id == lot_id)
        )
        lines = list(lines_r.scalars().all())

        for line in lines:
            event = await db.get(TraceEvent, line.event_id)
            if event:
                if event.trace_event_type == TraceEventType.shipment:
                    qty_shipped += line.quantity
                    if line.linked_customer_id:
                        customer_ids.add(line.linked_customer_id)
                    affected_shipments.append({
                        "event_id": str(event.id),
                        "shipment_ref": line.linked_shipment_id,
                        "customer_id": str(line.linked_customer_id) if line.linked_customer_id else None,
                        "lot_id": str(lot_id),
                        "quantity": float(line.quantity),
                        "event_date": event.event_datetime.isoformat() if event.event_datetime else None,
                    })
                elif event.trace_event_type == TraceEventType.scrap:
                    qty_scrapped += line.quantity
                elif event.trace_event_type == TraceEventType.quarantine:
                    qty_quarantined += line.quantity
                elif event.trace_event_type == TraceEventType.rework:
                    qty_reworked += line.quantity
                elif event.trace_event_type == TraceEventType.return_event:
                    qty_returned += line.quantity

        # Child lots
        children_r = await db.execute(
            select(LotGenealogyLink).where(LotGenealogyLink.parent_lot_id == lot_id)
        )
        for link in children_r.scalars().all():
            affected_lots.append({
                "lot_id": str(link.child_lot_id),
                "rel_type": link.relationship_type.value,
                "quantity": float(link.quantity_linked or 0),
                "child_stage": link.child_stage.value if link.child_stage else None,
            })
            if link.child_lot_id not in visited:
                queue.append((link.child_lot_id, depth + 1))

    affected_customers: List[Dict[str, Any]] = []
    for cid in customer_ids:
        affected_customers.append({"customer_id": str(cid)})

    total = qty_in_stock + qty_shipped + qty_returned + qty_scrapped + qty_quarantined + qty_reworked

    return ForwardTraceResult(
        root_lot_id=root_lot_id,
        affected_lots=affected_lots,
        affected_shipments=affected_shipments,
        affected_customers=affected_customers,
        qty_in_stock=qty_in_stock,
        qty_shipped=qty_shipped,
        qty_returned=qty_returned,
        qty_scrapped=qty_scrapped,
        qty_quarantined=qty_quarantined,
        qty_reworked=qty_reworked,
        total_affected_qty=total,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Backward Traceability
# ─────────────────────────────────────────────────────────────────────────────

async def backward_trace(db: AsyncSession, root_lot_id: uuid.UUID,
                          max_depth: int = 10) -> BackwardTraceResult:
    """
    Backward trace: given a lot, find all ancestor lots (where it came from),
    production orders, suppliers, GRNs.
    """
    visited: Set[uuid.UUID] = set()
    queue: deque[tuple[uuid.UUID, int]] = deque([(root_lot_id, 0)])
    source_lots: List[Dict[str, Any]] = []
    prod_order_ids: Set[uuid.UUID] = set()
    supplier_ids: Set[uuid.UUID] = set()
    grns: List[Dict[str, Any]] = []
    max_depth_found = 0

    while queue:
        lot_id, depth = queue.popleft()
        if lot_id in visited or depth > max_depth:
            continue
        visited.add(lot_id)
        max_depth_found = max(max_depth_found, depth)

        lot = await db.get(Lot, lot_id)
        if lot and lot.supplier_id:
            supplier_ids.add(lot.supplier_id)

        # Parent lots
        parents_r = await db.execute(
            select(LotGenealogyLink).where(LotGenealogyLink.child_lot_id == lot_id)
        )
        for link in parents_r.scalars().all():
            source_lots.append({
                "lot_id": str(link.parent_lot_id),
                "rel_type": link.relationship_type.value,
                "quantity": float(link.quantity_linked or 0),
                "parent_stage": link.parent_stage.value if link.parent_stage else None,
            })
            if link.production_order_id:
                prod_order_ids.add(link.production_order_id)
            if link.parent_lot_id not in visited:
                queue.append((link.parent_lot_id, depth + 1))

        # Receipt events for this lot
        receipt_lines_r = await db.execute(
            select(TraceEventLine).where(TraceEventLine.child_lot_id == lot_id)
        )
        for line in receipt_lines_r.scalars().all():
            event = await db.get(TraceEvent, line.event_id)
            if event and event.trace_event_type == TraceEventType.receipt:
                if line.linked_grn_id:
                    grns.append({
                        "grn_id": str(line.linked_grn_id),
                        "supplier_id": str(line.linked_supplier_id) if line.linked_supplier_id else None,
                        "lot_id": str(lot_id),
                        "quantity": float(line.quantity),
                    })
                    if line.linked_supplier_id:
                        supplier_ids.add(line.linked_supplier_id)

    return BackwardTraceResult(
        root_lot_id=root_lot_id,
        source_lots=source_lots,
        production_orders=[{"id": str(pid)} for pid in prod_order_ids],
        suppliers=[{"id": str(sid)} for sid in supplier_ids],
        grns=grns,
        qc_events=[],
        genealogy_depth=max_depth_found,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Genealogy Tree
# ─────────────────────────────────────────────────────────────────────────────

async def get_genealogy_tree(db: AsyncSession, root_lot_id: uuid.UUID,
                              direction: str = "both",
                              max_depth: int = 6) -> GenealogyTree:
    """Build a graph-ready tree structure for visualization."""
    nodes: Dict[str, Dict] = {}
    edges: List[Dict[str, Any]] = []
    visited: Set[str] = set()
    stage_summary: Dict[str, int] = {}

    async def _collect_forward(lot_id: uuid.UUID, depth: int) -> None:
        key = str(lot_id)
        if key in visited or depth > max_depth:
            return
        visited.add(key)

        lot = await db.get(Lot, lot_id)
        lot_num = lot.lot_number if lot else key[:8]
        if key not in nodes:
            nodes[key] = {"lot_id": str(lot_id), "lot_number": lot_num,
                          "stage": None, "quantity": None}

        links_r = await db.execute(
            select(LotGenealogyLink).where(LotGenealogyLink.parent_lot_id == lot_id)
        )
        for link in links_r.scalars().all():
            child_key = str(link.child_lot_id)
            child_lot  = await db.get(Lot, link.child_lot_id)
            child_num  = child_lot.lot_number if child_lot else child_key[:8]
            stage_val  = link.child_stage.value if link.child_stage else None

            if child_key not in nodes:
                nodes[child_key] = {"lot_id": child_key, "lot_number": child_num,
                                     "stage": stage_val, "quantity": float(link.quantity_linked or 0)}
            if stage_val:
                stage_summary[stage_val] = stage_summary.get(stage_val, 0) + 1

            edges.append({
                "source": key,
                "target": child_key,
                "rel_type": link.relationship_type.value,
                "qty": float(link.quantity_linked or 0),
            })
            await _collect_forward(link.child_lot_id, depth + 1)

    async def _collect_backward(lot_id: uuid.UUID, depth: int) -> None:
        key = str(lot_id)
        if key in visited or depth > max_depth:
            return
        visited.add(key)

        lot = await db.get(Lot, lot_id)
        lot_num = lot.lot_number if lot else key[:8]
        if key not in nodes:
            nodes[key] = {"lot_id": str(lot_id), "lot_number": lot_num,
                          "stage": None, "quantity": None}

        links_r = await db.execute(
            select(LotGenealogyLink).where(LotGenealogyLink.child_lot_id == lot_id)
        )
        for link in links_r.scalars().all():
            parent_key = str(link.parent_lot_id)
            parent_lot  = await db.get(Lot, link.parent_lot_id)
            parent_num  = parent_lot.lot_number if parent_lot else parent_key[:8]
            stage_val   = link.parent_stage.value if link.parent_stage else None

            if parent_key not in nodes:
                nodes[parent_key] = {"lot_id": parent_key, "lot_number": parent_num,
                                      "stage": stage_val, "quantity": float(link.quantity_linked or 0)}
            if stage_val:
                stage_summary[stage_val] = stage_summary.get(stage_val, 0) + 1

            edges.append({
                "source": parent_key,
                "target": key,
                "rel_type": link.relationship_type.value,
                "qty": float(link.quantity_linked or 0),
            })
            await _collect_backward(link.parent_lot_id, depth + 1)

    root_lot = await db.get(Lot, root_lot_id)
    root_num = root_lot.lot_number if root_lot else str(root_lot_id)[:8]
    nodes[str(root_lot_id)] = {"lot_id": str(root_lot_id), "lot_number": root_num,
                                "stage": None, "quantity": None}

    if direction in ("forward", "both"):
        await _collect_forward(root_lot_id, 0)
    if direction in ("backward", "both"):
        visited_bak = visited.copy()
        visited = set()
        await _collect_backward(root_lot_id, 0)
        visited = visited | visited_bak

    node_list = [
        GenealogyNode(
            lot_id=uuid.UUID(n["lot_id"]),
            lot_number=n["lot_number"],
            stage=n.get("stage"),
            quantity=n.get("quantity"),
            rel_type=None,
        )
        for n in nodes.values()
    ]

    return GenealogyTree(
        root_lot_id=root_lot_id,
        root_lot_number=root_num,
        direction=direction,
        depth=max_depth,
        nodes=node_list,
        edges=edges,
        lot_count=len(nodes),
        stage_summary=stage_summary,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Traceability Search
# ─────────────────────────────────────────────────────────────────────────────

async def search_traceability(db: AsyncSession,
                               req: TraceabilitySearchRequest) -> List[TraceabilitySearchResult]:
    q = select(Lot)
    if req.lot_number:
        q = q.where(Lot.lot_number.ilike(f"%{req.lot_number}%"))
    if req.batch_number:
        q = q.where(Lot.batch_number.ilike(f"%{req.batch_number}%"))
    if req.product_id:
        q = q.where(Lot.product_id == req.product_id)
    if req.material_id:
        q = q.where(Lot.material_id == req.material_id)
    if req.supplier_id:
        q = q.where(Lot.supplier_id == req.supplier_id)

    lots_r = await db.execute(q.limit(50))
    lots = list(lots_r.scalars().all())

    results: List[TraceabilitySearchResult] = []
    for lot in lots:
        events = await list_trace_events(db, lot_id=lot.id, limit=20)
        link_r = await db.execute(
            select(func.count(LotGenealogyLink.id)).where(
                (LotGenealogyLink.parent_lot_id == lot.id) |
                (LotGenealogyLink.child_lot_id  == lot.id)
            )
        )
        link_count = link_r.scalar() or 0

        results.append(TraceabilitySearchResult(
            lot_id=lot.id,
            lot_number=lot.lot_number,
            batch_number=lot.batch_number,
            item_name=None,
            stage=None,
            events=[TraceEventOut(
                id=e.id,
                trace_event_type=e.trace_event_type,
                event_datetime=e.event_datetime,
                reference_number=e.reference_number,
                source_document_type=e.source_document_type,
                source_document_id=e.source_document_id,
                production_order_id=e.production_order_id,
                warehouse_id=e.warehouse_id,
                performed_by_id=e.performed_by_id,
                recall_id=e.recall_id,
                notes=e.notes,
                lines=[],
                created_at=e.created_at,
            ) for e in events],
            genealogy_link_count=link_count,
            has_recall=False,
        ))

    return results
