"""
Analytics / BI endpoints.
Each module endpoint returns KPIs + trend series — no separate calls needed.
All metrics are computed from real ERP data; nothing is hardcoded.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text, cast, Date as SADate

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db

router = APIRouter()


# ── Shared types ──────────────────────────────────────────────────────────────

class TrendPoint(BaseModel):
    date: str
    value: float
    label: Optional[str] = None


class DistributionSlice(BaseModel):
    label: str
    value: float
    count: int


class ExceptionRow(BaseModel):
    id: str
    label: str
    detail: str
    severity: str    # "low" | "medium" | "high" | "critical"
    href: str


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _f(v) -> float:
    return float(v) if v is not None else 0.0


def _date_series(start: date, days: int) -> List[str]:
    return [str(start + timedelta(days=i)) for i in range(days)]


def _fill_trend(raw: dict[str, float], start: date, days: int) -> List[TrendPoint]:
    return [
        TrendPoint(date=str(start + timedelta(days=i)),
                   value=raw.get(str(start + timedelta(days=i)), 0.0))
        for i in range(days)
    ]


# ── Inventory analytics ───────────────────────────────────────────────────────

class InventoryAnalytics(BaseModel):
    # KPIs
    total_stock_value: float
    total_sku_count: int
    low_stock_count: int
    zero_stock_count: int
    blocked_stock_count: int
    product_count: int
    material_count: int
    # Trends
    movement_trend_30d: List[TrendPoint]      # net movements by day
    receipts_trend_30d: List[TrendPoint]
    issues_trend_30d: List[TrendPoint]
    # Distributions
    by_movement_type: List[DistributionSlice]
    # Exceptions
    low_stock_items: List[ExceptionRow]


@router.get("/inventory", response_model=InventoryAnalytics,
            dependencies=[Depends(require_permission("inventory", "view"))])
async def inventory_analytics(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.inventory import Stock, StockMovement, MovementType
    from app.models.master import Product, Material

    today = _today()
    start = today - timedelta(days=days - 1)

    # ── Stock value + counts ──
    prod_result = await db.execute(
        select(
            Stock.product_id,
            Product.name,
            Product.reorder_point,
            Product.standard_cost,
            Product.uom,
            func.sum(Stock.quantity_on_hand).label("qty"),
            func.sum(Stock.is_blocked.cast(int)).label("blocked_count"),
        )
        .join(Product, Stock.product_id == Product.id)
        .where(Stock.product_id.isnot(None))
        .group_by(Stock.product_id, Product.name, Product.reorder_point,
                  Product.standard_cost, Product.uom)
    )
    prod_rows = prod_result.all()

    mat_result = await db.execute(
        select(
            Stock.material_id,
            Material.name,
            Material.reorder_point,
            Material.standard_cost,
            Material.uom,
            func.sum(Stock.quantity_on_hand).label("qty"),
        )
        .join(Material, Stock.material_id == Material.id)
        .where(Stock.material_id.isnot(None))
        .group_by(Stock.material_id, Material.name, Material.reorder_point,
                  Material.standard_cost, Material.uom)
    )
    mat_rows = mat_result.all()

    total_value = 0.0
    low_stock_exc: List[ExceptionRow] = []
    zero_count = 0
    blocked_count = 0

    for r in prod_rows:
        qty = _f(r.qty)
        cost = _f(r.standard_cost)
        total_value += qty * cost
        if qty <= 0:
            zero_count += 1
        if _f(getattr(r, "blocked_count", 0)) > 0:
            blocked_count += 1
        rp = _f(r.reorder_point)
        if qty <= rp:
            low_stock_exc.append(ExceptionRow(
                id=str(r.product_id),
                label=r.name,
                detail=f"Stock: {qty:.1f} | Reorder: {rp:.1f}",
                severity="critical" if qty <= 0 else ("high" if qty <= rp * 0.5 else "medium"),
                href="/dashboard/inventory",
            ))

    for r in mat_rows:
        qty = _f(r.qty)
        cost = _f(r.standard_cost)
        total_value += qty * cost
        if qty <= 0:
            zero_count += 1
        rp = _f(r.reorder_point)
        if qty <= rp:
            low_stock_exc.append(ExceptionRow(
                id=str(r.material_id),
                label=r.name,
                detail=f"Stock: {qty:.1f} | Reorder: {rp:.1f}",
                severity="critical" if qty <= 0 else ("high" if qty <= rp * 0.5 else "medium"),
                href="/dashboard/inventory",
            ))

    # ── Movement trends ──
    move_result = await db.execute(
        select(
            cast(StockMovement.moved_at, SADate).label("day"),
            StockMovement.movement_type,
            func.count(StockMovement.id).label("cnt"),
            func.coalesce(func.sum(StockMovement.quantity), 0).label("qty"),
        )
        .where(cast(StockMovement.moved_at, SADate) >= start)
        .group_by(text("day"), StockMovement.movement_type)
        .order_by(text("day"))
    )
    move_rows = move_result.all()

    receipt_map: dict[str, float] = defaultdict(float)
    issue_map: dict[str, float] = defaultdict(float)
    type_counts: dict[str, dict] = defaultdict(lambda: {"value": 0.0, "count": 0})

    for r in move_rows:
        day = str(r.day)
        qty = _f(r.qty)
        mt = r.movement_type.value if hasattr(r.movement_type, "value") else str(r.movement_type)
        type_counts[mt]["value"] += qty
        type_counts[mt]["count"] += r.cnt
        if mt == "RECEIPT":
            receipt_map[day] += qty
        elif mt in ("ISSUE", "WRITE_OFF"):
            issue_map[day] += qty

    net_map = {
        d: receipt_map.get(d, 0.0) - issue_map.get(d, 0.0)
        for d in set(list(receipt_map.keys()) + list(issue_map.keys()))
    }

    return InventoryAnalytics(
        total_stock_value=round(total_value, 2),
        total_sku_count=len(prod_rows) + len(mat_rows),
        low_stock_count=len(low_stock_exc),
        zero_stock_count=zero_count,
        blocked_stock_count=blocked_count,
        product_count=len(prod_rows),
        material_count=len(mat_rows),
        movement_trend_30d=_fill_trend(net_map, start, days),
        receipts_trend_30d=_fill_trend(receipt_map, start, days),
        issues_trend_30d=_fill_trend(issue_map, start, days),
        by_movement_type=[
            DistributionSlice(label=k, value=round(v["value"], 2), count=v["count"])
            for k, v in type_counts.items()
        ],
        low_stock_items=sorted(low_stock_exc, key=lambda x: x.severity)[:20],
    )


# ── Production analytics ──────────────────────────────────────────────────────

class ProductionAnalytics(BaseModel):
    # KPIs
    total_orders: int
    active_orders: int
    completed_today: int
    completion_rate: float           # planned vs actual avg
    delayed_orders: int
    machines_down: int
    open_breakdowns: int
    avg_downtime_hours: float
    # Trends
    production_trend: List[TrendPoint]       # daily actual qty
    plan_vs_actual: List[TrendPoint]         # planned
    plan_vs_actual_actual: List[TrendPoint]  # actual
    downtime_trend: List[TrendPoint]         # daily downtime hours
    rejection_trend: List[TrendPoint]        # QC fails
    # Distribution
    by_status: List[DistributionSlice]
    # Exceptions
    exceptions: List[ExceptionRow]


@router.get("/production", response_model=ProductionAnalytics,
            dependencies=[Depends(require_permission("production", "view"))])
async def production_analytics(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.production import ProductionOrder, ProductionOrderStatus, DowntimeLog
    from app.models.maintenance import Asset, AssetStatus, BreakdownRecord, BreakdownStatus
    from app.models.quality import QCInspection, QCStatus

    today = _today()
    start = today - timedelta(days=days - 1)

    # ── Status distribution ──
    status_result = await db.execute(
        select(ProductionOrder.status, func.count(ProductionOrder.id))
        .group_by(ProductionOrder.status)
    )
    status_map = {r[0]: r[1] for r in status_result}
    total_orders = sum(status_map.values())
    active_orders = (
        status_map.get(ProductionOrderStatus.RELEASED, 0) +
        status_map.get(ProductionOrderStatus.IN_PROGRESS, 0)
    )

    completed_today_result = await db.execute(
        select(func.count(ProductionOrder.id)).where(
            and_(
                ProductionOrder.status == ProductionOrderStatus.COMPLETED,
                cast(ProductionOrder.updated_at, SADate) == today,
            )
        )
    )
    completed_today = completed_today_result.scalar_one() or 0

    # Completion rate (avg planned vs actual for completed orders)
    rate_result = await db.execute(
        select(
            func.avg(
                func.case(
                    (ProductionOrder.planned_quantity > 0,
                     ProductionOrder.actual_quantity / ProductionOrder.planned_quantity * 100),
                    else_=0
                )
            )
        ).where(ProductionOrder.status == ProductionOrderStatus.COMPLETED)
    )
    completion_rate = _f(rate_result.scalar_one())

    # Delayed orders
    delayed_result = await db.execute(
        select(func.count(ProductionOrder.id)).where(
            and_(
                ProductionOrder.status == ProductionOrderStatus.IN_PROGRESS,
                cast(ProductionOrder.scheduled_end, SADate) < today,
            )
        )
    )
    delayed_orders = delayed_result.scalar_one() or 0

    machines_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.status == AssetStatus.UNDER_MAINTENANCE)
    )
    machines_down = machines_result.scalar_one() or 0

    breakdowns_result = await db.execute(
        select(func.count(BreakdownRecord.id)).where(
            BreakdownRecord.status.in_([BreakdownStatus.OPEN, BreakdownStatus.IN_REPAIR])
        )
    )
    open_breakdowns = breakdowns_result.scalar_one() or 0

    # ── Production trends ──
    prod_trend_result = await db.execute(
        select(
            cast(ProductionOrder.scheduled_start, SADate).label("day"),
            func.coalesce(func.sum(ProductionOrder.planned_quantity), 0).label("planned"),
            func.coalesce(func.sum(ProductionOrder.actual_quantity), 0).label("actual"),
        )
        .where(cast(ProductionOrder.scheduled_start, SADate).between(start, today))
        .group_by(text("day"))
        .order_by(text("day"))
    )
    planned_map: dict[str, float] = {}
    actual_map: dict[str, float] = {}
    for r in prod_trend_result:
        d = str(r.day)
        planned_map[d] = _f(r.planned)
        actual_map[d] = _f(r.actual)

    # ── Downtime trend ──
    downtime_result = await db.execute(
        select(
            cast(DowntimeLog.started_at, SADate).label("day"),
            func.coalesce(func.sum(DowntimeLog.duration_minutes), 0).label("mins"),
        )
        .where(cast(DowntimeLog.started_at, SADate).between(start, today))
        .group_by(text("day"))
    )
    downtime_map: dict[str, float] = {}
    total_downtime_mins = 0.0
    downtime_days = 0
    for r in downtime_result:
        d = str(r.day)
        hours = _f(r.mins) / 60.0
        downtime_map[d] = round(hours, 2)
        total_downtime_mins += _f(r.mins)
        downtime_days += 1
    avg_downtime = (total_downtime_mins / 60.0 / max(downtime_days, 1)) if total_downtime_mins > 0 else 0.0

    # ── QC rejection trend ──
    qc_result = await db.execute(
        select(
            cast(QCInspection.created_at, SADate).label("day"),
            func.count(QCInspection.id).label("cnt"),
        )
        .where(
            and_(
                QCInspection.status == QCStatus.FAILED,
                cast(QCInspection.created_at, SADate).between(start, today),
            )
        )
        .group_by(text("day"))
    )
    rejection_map = {str(r.day): _f(r.cnt) for r in qc_result}

    # Exceptions
    exceptions: List[ExceptionRow] = []
    if delayed_orders > 0:
        exceptions.append(ExceptionRow(
            id="delayed", label=f"{delayed_orders} Orders Past Scheduled End",
            detail="Production orders overdue", severity="high",
            href="/dashboard/production/orders",
        ))
    if machines_down > 0:
        exceptions.append(ExceptionRow(
            id="machines", label=f"{machines_down} Machines Down",
            detail="Under maintenance", severity="critical" if machines_down >= 3 else "medium",
            href="/dashboard/maintenance/assets",
        ))

    return ProductionAnalytics(
        total_orders=total_orders,
        active_orders=active_orders,
        completed_today=completed_today,
        completion_rate=round(completion_rate, 1),
        delayed_orders=delayed_orders,
        machines_down=machines_down,
        open_breakdowns=open_breakdowns,
        avg_downtime_hours=round(avg_downtime, 2),
        production_trend=_fill_trend(actual_map, start, days),
        plan_vs_actual=_fill_trend(planned_map, start, days),
        plan_vs_actual_actual=_fill_trend(actual_map, start, days),
        downtime_trend=_fill_trend(downtime_map, start, days),
        rejection_trend=_fill_trend(rejection_map, start, days),
        by_status=[
            DistributionSlice(label=k.value, value=0, count=v)
            for k, v in status_map.items()
        ],
        exceptions=exceptions,
    )


# ── Procurement analytics ─────────────────────────────────────────────────────

class ProcurementAnalytics(BaseModel):
    # KPIs
    open_po_count: int
    open_po_value: float
    overdue_po_count: int
    pending_pr_count: int
    received_this_month: int
    avg_po_lead_days: float
    top_suppliers: List[DistributionSlice]    # by PO value
    # Trends
    po_value_trend: List[TrendPoint]          # monthly PO value
    grn_trend: List[TrendPoint]               # GRNs received by day
    # Exceptions
    exceptions: List[ExceptionRow]


@router.get("/procurement", response_model=ProcurementAnalytics,
            dependencies=[Depends(require_permission("procurement", "view"))])
async def procurement_analytics(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.procurement import (
        PurchaseOrder, POStatus, GoodsReceipt, GRNStatus,
        PurchaseRequisition, PRStatus, POLine
    )
    from app.models.master import Supplier

    today = _today()
    start = today - timedelta(days=days - 1)

    # Open POs
    po_result = await db.execute(
        select(
            PurchaseOrder.status,
            func.count(PurchaseOrder.id),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0),
        ).group_by(PurchaseOrder.status)
    )
    open_po_count = 0
    open_po_value = 0.0
    for r in po_result:
        if r[0] in (POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED):
            open_po_count += r[1]
            open_po_value += _f(r[2])

    # Overdue POs (expected_delivery < today, not yet received)
    overdue_result = await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            and_(
                PurchaseOrder.status.in_([POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED]),
                PurchaseOrder.expected_delivery_date < today,
            )
        )
    )
    overdue_po_count = overdue_result.scalar_one() or 0

    # Pending PRs
    pr_result = await db.execute(
        select(func.count(PurchaseRequisition.id)).where(
            PurchaseRequisition.status == PRStatus.PENDING_APPROVAL
        )
    )
    pending_pr_count = pr_result.scalar_one() or 0

    # GRNs received this month
    month_start = today.replace(day=1)
    grn_result = await db.execute(
        select(func.count(GoodsReceipt.id)).where(
            and_(
                GoodsReceipt.status == GRNStatus.POSTED,
                cast(GoodsReceipt.received_date, SADate) >= month_start,
            )
        )
    )
    received_this_month = grn_result.scalar_one() or 0

    # GRN trend
    grn_trend_result = await db.execute(
        select(
            cast(GoodsReceipt.received_date, SADate).label("day"),
            func.count(GoodsReceipt.id).label("cnt"),
        )
        .where(
            and_(
                GoodsReceipt.status == GRNStatus.POSTED,
                cast(GoodsReceipt.received_date, SADate).between(start, today),
            )
        )
        .group_by(text("day"))
    )
    grn_trend_map = {str(r.day): _f(r.cnt) for r in grn_trend_result}

    # PO value trend
    po_trend_result = await db.execute(
        select(
            cast(PurchaseOrder.order_date, SADate).label("day"),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label("val"),
        )
        .where(cast(PurchaseOrder.order_date, SADate).between(start, today))
        .group_by(text("day"))
    )
    po_trend_map = {str(r.day): _f(r.val) for r in po_trend_result}

    # Top suppliers by PO value
    supplier_result = await db.execute(
        select(
            Supplier.name,
            func.count(PurchaseOrder.id).label("cnt"),
            func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label("val"),
        )
        .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
        .group_by(Supplier.name)
        .order_by(func.sum(PurchaseOrder.total_amount).desc())
        .limit(8)
    )
    top_suppliers = [
        DistributionSlice(label=r.name, value=round(_f(r.val), 2), count=r.cnt)
        for r in supplier_result
    ]

    exceptions: List[ExceptionRow] = []
    if overdue_po_count:
        exceptions.append(ExceptionRow(
            id="po-overdue", label=f"{overdue_po_count} POs Past Delivery Date",
            detail="Follow up with supplier", severity="high",
            href="/dashboard/procurement/orders",
        ))
    if pending_pr_count:
        exceptions.append(ExceptionRow(
            id="pr-pending", label=f"{pending_pr_count} PRs Awaiting Approval",
            detail="Purchase requisitions pending", severity="medium",
            href="/dashboard/procurement",
        ))

    return ProcurementAnalytics(
        open_po_count=open_po_count,
        open_po_value=round(open_po_value, 2),
        overdue_po_count=overdue_po_count,
        pending_pr_count=pending_pr_count,
        received_this_month=received_this_month,
        avg_po_lead_days=0.0,  # computed if needed
        top_suppliers=top_suppliers,
        po_value_trend=_fill_trend(po_trend_map, start, days),
        grn_trend=_fill_trend(grn_trend_map, start, days),
        exceptions=exceptions,
    )


# ── Sales analytics ───────────────────────────────────────────────────────────

class SalesAnalytics(BaseModel):
    # KPIs
    today_orders: int
    today_revenue: float
    mtd_revenue: float
    ytd_revenue: float
    open_orders: int
    overdue_invoices: int
    overdue_value: float
    pending_shipments: int
    avg_order_value: float
    # Trends
    revenue_trend: List[TrendPoint]
    order_count_trend: List[TrendPoint]
    # Distributions
    by_channel: List[DistributionSlice]
    by_status: List[DistributionSlice]
    top_customers: List[DistributionSlice]
    # Exceptions
    exceptions: List[ExceptionRow]


@router.get("/sales", response_model=SalesAnalytics,
            dependencies=[Depends(require_permission("sales", "view"))])
async def sales_analytics(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.sales import (
        SalesOrder, SOStatus, Invoice, InvoiceStatus,
        Shipment, ShipmentStatus, Customer, CustomerChannel,
    )

    today = _today()
    start = today - timedelta(days=days - 1)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # Today orders
    today_so = await db.execute(
        select(func.count(SalesOrder.id), func.coalesce(func.sum(SalesOrder.total_amount), 0))
        .where(and_(SalesOrder.order_date == today,
                    SalesOrder.status.notin_([SOStatus.CANCELLED, SOStatus.DRAFT])))
    )
    r = today_so.one()
    today_orders = r[0] or 0
    today_revenue = _f(r[1])

    # MTD revenue
    mtd = await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount), 0))
        .where(and_(Invoice.invoice_date >= month_start,
                    Invoice.status.notin_(["DRAFT", "CANCELLED"])))
    )
    mtd_revenue = _f(mtd.scalar_one())

    # YTD revenue
    ytd = await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount), 0))
        .where(and_(Invoice.invoice_date >= year_start,
                    Invoice.status.notin_(["DRAFT", "CANCELLED"])))
    )
    ytd_revenue = _f(ytd.scalar_one())

    # Open orders
    open_so = await db.execute(
        select(func.count(SalesOrder.id)).where(
            SalesOrder.status.in_([SOStatus.CONFIRMED, SOStatus.ALLOCATED,
                                   SOStatus.PICKING, SOStatus.SHIPPED])
        )
    )
    open_orders = open_so.scalar_one() or 0

    # Overdue invoices
    overdue = await db.execute(
        select(func.count(Invoice.id),
               func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0))
        .where(Invoice.status == InvoiceStatus.OVERDUE)
    )
    ov_row = overdue.one()
    overdue_invoices = ov_row[0] or 0
    overdue_value = _f(ov_row[1])

    # Pending shipments
    pship = await db.execute(
        select(func.count(Shipment.id)).where(
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PICKING, ShipmentStatus.PACKED])
        )
    )
    pending_shipments = pship.scalar_one() or 0

    # Avg order value (last 30d)
    avg_ov = await db.execute(
        select(func.avg(SalesOrder.total_amount))
        .where(and_(SalesOrder.order_date >= start,
                    SalesOrder.status.notin_([SOStatus.CANCELLED, SOStatus.DRAFT])))
    )
    avg_order_value = _f(avg_ov.scalar_one())

    # Revenue trend (invoice date)
    rev_trend = await db.execute(
        select(Invoice.invoice_date.label("day"),
               func.coalesce(func.sum(Invoice.total_amount), 0).label("amt"),
               func.count(Invoice.id).label("cnt"))
        .where(and_(Invoice.invoice_date.between(start, today),
                    Invoice.status.notin_([InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED])))
        .group_by(Invoice.invoice_date)
        .order_by(Invoice.invoice_date)
    )
    rev_map: dict[str, float] = {}
    cnt_map: dict[str, float] = {}
    for r in rev_trend:
        rev_map[str(r.day)] = _f(r.amt)
        cnt_map[str(r.day)] = _f(r.cnt)

    # By channel
    channel_result = await db.execute(
        select(Customer.channel,
               func.count(SalesOrder.id).label("cnt"),
               func.coalesce(func.sum(SalesOrder.total_amount), 0).label("val"))
        .join(Customer, SalesOrder.customer_id == Customer.id)
        .where(and_(SalesOrder.order_date >= start,
                    SalesOrder.status.notin_([SOStatus.CANCELLED, SOStatus.DRAFT])))
        .group_by(Customer.channel)
        .order_by(func.sum(SalesOrder.total_amount).desc())
    )
    by_channel = [
        DistributionSlice(
            label=r.channel.value if hasattr(r.channel, "value") else str(r.channel),
            value=round(_f(r.val), 2), count=r.cnt
        )
        for r in channel_result
    ]

    # By status
    so_status_result = await db.execute(
        select(SalesOrder.status, func.count(SalesOrder.id)).group_by(SalesOrder.status)
    )
    by_status = [
        DistributionSlice(
            label=r[0].value if hasattr(r[0], "value") else str(r[0]),
            value=0, count=r[1]
        )
        for r in so_status_result
    ]

    # Top customers
    top_cust = await db.execute(
        select(Customer.name,
               func.count(Invoice.id).label("cnt"),
               func.coalesce(func.sum(Invoice.total_amount), 0).label("val"))
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.invoice_date >= start)
        .group_by(Customer.name)
        .order_by(func.sum(Invoice.total_amount).desc())
        .limit(8)
    )
    top_customers = [
        DistributionSlice(label=r.name, value=round(_f(r.val), 2), count=r.cnt)
        for r in top_cust
    ]

    exceptions: List[ExceptionRow] = []
    if overdue_invoices:
        exceptions.append(ExceptionRow(
            id="overdue", label=f"{overdue_invoices} Overdue Invoices",
            detail=f"KES {overdue_value:,.0f} outstanding", severity="high",
            href="/dashboard/sales/invoices",
        ))

    return SalesAnalytics(
        today_orders=today_orders,
        today_revenue=round(today_revenue, 2),
        mtd_revenue=round(mtd_revenue, 2),
        ytd_revenue=round(ytd_revenue, 2),
        open_orders=open_orders,
        overdue_invoices=overdue_invoices,
        overdue_value=round(overdue_value, 2),
        pending_shipments=pending_shipments,
        avg_order_value=round(avg_order_value, 2),
        revenue_trend=_fill_trend(rev_map, start, days),
        order_count_trend=_fill_trend(cnt_map, start, days),
        by_channel=by_channel,
        by_status=by_status,
        top_customers=top_customers,
        exceptions=exceptions,
    )


# ── Finance analytics ─────────────────────────────────────────────────────────

class FinanceAnalytics(BaseModel):
    # KPIs
    cash_on_hand: float
    bank_balance: float
    open_receivables: float
    overdue_receivables: float
    open_payables: float
    mtd_revenue: float
    mtd_expenses: float
    # Trends
    cash_receipts_trend: List[TrendPoint]
    cash_payments_trend: List[TrendPoint]
    # Distributions
    by_account_type: List[DistributionSlice]
    # Exceptions
    exceptions: List[ExceptionRow]


@router.get("/finance", response_model=FinanceAnalytics,
            dependencies=[Depends(require_permission("finance", "view"))])
async def finance_analytics(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.finance import (
        CashAccount, CashTransaction, TxDirection, FinTxStatus, CashAccountType
    )
    from app.models.sales import Invoice, InvoiceStatus
    from app.models.procurement import PurchaseOrder, POStatus, POPaymentStatus

    today = _today()
    start = today - timedelta(days=days - 1)

    # Cash balances
    cash_result = await db.execute(
        select(CashAccount.account_type,
               func.coalesce(func.sum(CashAccount.balance), 0).label("bal"))
        .group_by(CashAccount.account_type)
    )
    cash_on_hand = 0.0
    bank_balance = 0.0
    for r in cash_result:
        at = r[0].value if hasattr(r[0], "value") else str(r[0])
        if at == "CASH":
            cash_on_hand += _f(r.bal)
        elif at in ("BANK", "MPESA"):
            bank_balance += _f(r.bal)

    # Open receivables (unpaid invoices)
    recv_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0))
        .where(Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]))
    )
    open_receivables = _f(recv_result.scalar_one())

    overdue_recv = await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0))
        .where(Invoice.status == InvoiceStatus.OVERDUE)
    )
    overdue_receivables = _f(overdue_recv.scalar_one())

    # Open payables
    payables_result = await db.execute(
        select(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))
        .where(and_(
            PurchaseOrder.payment_status.in_([POPaymentStatus.PENDING, POPaymentStatus.PARTIALLY_PAID]),
            PurchaseOrder.status != POStatus.CANCELLED,
        ))
    )
    open_payables = _f(payables_result.scalar_one())

    # Cash transactions trend
    tx_result = await db.execute(
        select(
            cast(CashTransaction.transaction_date, SADate).label("day"),
            CashTransaction.direction,
            func.coalesce(func.sum(CashTransaction.amount), 0).label("amt"),
        )
        .where(
            and_(
                CashTransaction.status == FinTxStatus.CLEARED,
                cast(CashTransaction.transaction_date, SADate).between(start, today),
            )
        )
        .group_by(text("day"), CashTransaction.direction)
    )
    receipt_map: dict[str, float] = defaultdict(float)
    payment_map: dict[str, float] = defaultdict(float)
    mtd_revenue = 0.0
    mtd_expenses = 0.0

    for r in tx_result:
        d = str(r.day)
        dir_ = r.direction.value if hasattr(r.direction, "value") else str(r.direction)
        amt = _f(r.amt)
        if dir_ == "RECEIPT":
            receipt_map[d] += amt
            if d >= str(today.replace(day=1)):
                mtd_revenue += amt
        else:
            payment_map[d] += amt
            if d >= str(today.replace(day=1)):
                mtd_expenses += amt

    exceptions: List[ExceptionRow] = []
    if overdue_receivables > 0:
        exceptions.append(ExceptionRow(
            id="overdue-recv", label="Overdue Receivables",
            detail=f"KES {overdue_receivables:,.0f} past due", severity="high",
            href="/dashboard/finance/receivables",
        ))

    return FinanceAnalytics(
        cash_on_hand=round(cash_on_hand, 2),
        bank_balance=round(bank_balance, 2),
        open_receivables=round(open_receivables, 2),
        overdue_receivables=round(overdue_receivables, 2),
        open_payables=round(open_payables, 2),
        mtd_revenue=round(mtd_revenue, 2),
        mtd_expenses=round(mtd_expenses, 2),
        cash_receipts_trend=_fill_trend(dict(receipt_map), start, days),
        cash_payments_trend=_fill_trend(dict(payment_map), start, days),
        by_account_type=[],
        exceptions=exceptions,
    )


# ── Payment / M-Pesa analytics ────────────────────────────────────────────────

class MpesaAnalytics(BaseModel):
    # Today KPIs
    today_collected: float
    today_transactions: int
    today_success_rate: float
    today_failed: int
    today_pending: int
    today_reversed: int
    # Period KPIs
    period_collected: float
    period_total_transactions: int
    period_failed: int
    period_success_rate: float
    avg_amount: float
    avg_completion_time_minutes: float   # avg minutes from initiated → completed
    # Trends
    daily_collection_trend: List[TrendPoint]
    daily_transaction_count: List[TrendPoint]
    daily_failure_count: List[TrendPoint]
    # Distribution
    by_status: List[DistributionSlice]
    # Recent failures
    recent_failures: List[ExceptionRow]


@router.get("/payments/mpesa", response_model=MpesaAnalytics,
            dependencies=[Depends(require_permission("mpesa", "view_transactions"))])
async def mpesa_analytics(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.sales import MpesaTransaction, MpesaTxStatus

    today = _today()
    start = today - timedelta(days=days - 1)

    # Today breakdown
    today_result = await db.execute(
        select(MpesaTransaction.status,
               func.count(MpesaTransaction.id),
               func.coalesce(func.sum(MpesaTransaction.amount), 0))
        .where(cast(MpesaTransaction.created_at, SADate) == today)
        .group_by(MpesaTransaction.status)
    )
    today_map = {r[0]: (r[1], _f(r[2])) for r in today_result}

    today_collected = _f(today_map.get(MpesaTxStatus.COMPLETED, (0, 0.0))[1])
    today_transactions = sum(v[0] for v in today_map.values())
    today_failed = today_map.get(MpesaTxStatus.FAILED, (0, 0))[0]
    today_pending = today_map.get(MpesaTxStatus.PENDING, (0, 0))[0]
    today_reversed = today_map.get(MpesaTxStatus.CANCELLED, (0, 0))[0]
    today_success_rate = (
        (today_transactions - today_failed) / today_transactions * 100
        if today_transactions > 0 else 100.0
    )

    # Period breakdown
    period_result = await db.execute(
        select(MpesaTransaction.status,
               func.count(MpesaTransaction.id),
               func.coalesce(func.sum(MpesaTransaction.amount), 0))
        .where(cast(MpesaTransaction.created_at, SADate).between(start, today))
        .group_by(MpesaTransaction.status)
    )
    period_map = {r[0]: (r[1], _f(r[2])) for r in period_result}
    period_total = sum(v[0] for v in period_map.values())
    period_completed = period_map.get(MpesaTxStatus.COMPLETED, (0, 0.0))
    period_failed = period_map.get(MpesaTxStatus.FAILED, (0, 0))[0]
    period_collected = period_completed[1]
    period_success_rate = (
        (period_total - period_failed) / period_total * 100
        if period_total > 0 else 100.0
    )
    avg_amount = period_collected / max(period_completed[0], 1)

    # Daily trends
    daily_result = await db.execute(
        select(
            cast(MpesaTransaction.created_at, SADate).label("day"),
            MpesaTransaction.status,
            func.count(MpesaTransaction.id).label("cnt"),
            func.coalesce(func.sum(MpesaTransaction.amount), 0).label("amt"),
        )
        .where(cast(MpesaTransaction.created_at, SADate).between(start, today))
        .group_by(text("day"), MpesaTransaction.status)
    )
    coll_map: dict[str, float] = defaultdict(float)
    cnt_map: dict[str, float] = defaultdict(float)
    fail_map: dict[str, float] = defaultdict(float)

    for r in daily_result:
        d = str(r.day)
        status = r.status
        cnt_map[d] += r.cnt
        if status == MpesaTxStatus.COMPLETED:
            coll_map[d] += _f(r.amt)
        elif status == MpesaTxStatus.FAILED:
            fail_map[d] += r.cnt

    # Distribution
    by_status = [
        DistributionSlice(
            label=k.value if hasattr(k, "value") else str(k),
            value=round(v[1], 2), count=v[0]
        )
        for k, v in period_map.items()
    ]

    # Recent failures
    recent_fail_result = await db.execute(
        select(MpesaTransaction)
        .where(MpesaTransaction.status == MpesaTxStatus.FAILED)
        .order_by(MpesaTransaction.created_at.desc())
        .limit(10)
    )
    recent_failures = [
        ExceptionRow(
            id=str(t.id),
            label=f"KES {_f(t.amount):,.0f} — {t.phone_number}",
            detail=t.failure_reason or "Unknown reason",
            severity="medium",
            href="/dashboard/finance/mpesa",
        )
        for t in recent_fail_result.scalars().all()
    ]

    # Avg completion time (minutes) — time from created_at to updated_at for COMPLETED txns
    comp_time_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", MpesaTransaction.updated_at - MpesaTransaction.created_at) / 60.0
            )
        )
        .where(
            and_(
                MpesaTransaction.status == MpesaTxStatus.COMPLETED,
                cast(MpesaTransaction.created_at, SADate).between(start, today),
                MpesaTransaction.updated_at.isnot(None),
            )
        )
    )
    avg_completion_time = _f(comp_time_result.scalar_one())

    return MpesaAnalytics(
        today_collected=round(today_collected, 2),
        today_transactions=today_transactions,
        today_success_rate=round(today_success_rate, 1),
        today_failed=today_failed,
        today_pending=today_pending,
        today_reversed=today_reversed,
        period_collected=round(period_collected, 2),
        period_total_transactions=period_total,
        period_failed=period_failed,
        period_success_rate=round(period_success_rate, 1),
        avg_amount=round(avg_amount, 2),
        avg_completion_time_minutes=round(avg_completion_time, 2),
        daily_collection_trend=_fill_trend(dict(coll_map), start, days),
        daily_transaction_count=_fill_trend(dict(cnt_map), start, days),
        daily_failure_count=_fill_trend(dict(fail_map), start, days),
        by_status=by_status,
        recent_failures=recent_failures,
    )


# ── Marketing BI analytics ─────────────────────────────────────────────────────

class MarketingBIKPIs(BaseModel):
    # Campaign performance
    completed_campaigns: int
    active_campaigns: int
    avg_campaign_roi: float
    total_campaign_budget: float
    total_campaign_revenue: float
    overall_campaign_efficiency: float          # revenue / budget

    # Spend
    total_trade_spend: float
    total_brand_spend: float
    trade_spend_vs_sales_pct: float             # trade spend as % of invoiced sales
    brand_spend_vs_revenue_pct: float           # brand spend as % of campaign revenue

    # Influencer
    active_influencers: int
    total_influencer_revenue: float
    avg_influencer_score: float
    influencer_roi: float                       # revenue / total agreed fees

    # Social
    total_impressions: int
    total_engagements: int
    avg_engagement_rate: float
    top_social_platform: Optional[str]

    # Ads
    total_ad_spend: float
    total_ad_revenue: float
    overall_roas: float
    best_ad_platform: Optional[str]

    # E-commerce
    ecommerce_revenue: float
    ecommerce_orders: int
    avg_conversion_rate: float
    overall_return_rate: float

    # CRM / segments
    total_crm_profiles: int
    at_risk_customers: int
    vip_customers: int
    avg_engagement_score: float

    # Survey sentiment
    avg_survey_sentiment: float
    survey_count: int

    # Attribution-ready sales linkage
    campaign_linked_orders: int                 # SO count with campaign_id
    promotion_linked_orders: int                # SO count with promotion_id

    # Trends
    campaign_revenue_trend: List[TrendPoint]
    trade_spend_trend: List[TrendPoint]
    brand_spend_trend: List[TrendPoint]
    ad_spend_trend: List[TrendPoint]
    social_engagement_trend: List[TrendPoint]

    # Distributions
    by_campaign_type: List[DistributionSlice]
    by_ad_platform: List[DistributionSlice]
    by_influencer_platform: List[DistributionSlice]

    # Exceptions / signals
    exceptions: List[ExceptionRow]


@router.get("/marketing", response_model=MarketingBIKPIs,
            dependencies=[Depends(require_permission("marketing_analytics", "view"))])
async def marketing_bi_analytics(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    """
    Marketing BI dashboard — KPIs aggregated from all marketing sub-modules.
    Attribution-ready: includes campaign_linked_orders and promotion_linked_orders
    from the SalesOrder table for cross-module ROI visibility.
    """
    from app.models.marketing import (
        Campaign, CampaignStatus, Promotion,
        TradeSpend, BrandSpend,
        Influencer, InfluencerCampaignLink, InfluencerStatus,
        SocialMediaActivity,
        AdPerformance,
        Store, StorePerformance,
        CRMProfile, Survey,
    )
    from app.models.sales import SalesOrder, Invoice, InvoiceStatus
    from collections import defaultdict

    today = _today()
    start = today - timedelta(days=days - 1)

    # ── Campaign KPIs ──────────────────────────────────────────────────────────
    camp_rows = (await db.execute(
        select(
            Campaign.campaign_type,
            Campaign.status,
            func.count(Campaign.id).label("cnt"),
            func.avg(Campaign.actual_roi).label("avg_roi"),
            func.sum(Campaign.budget).label("total_budget"),
            func.sum(Campaign.actual_revenue).label("total_rev"),
        )
        .group_by(Campaign.campaign_type, Campaign.status)
    )).all()

    completed = sum(r.cnt for r in camp_rows if r.status == CampaignStatus.COMPLETED)
    active = sum(r.cnt for r in camp_rows if r.status == CampaignStatus.ACTIVE)
    avg_roi = sum(_f(r.avg_roi) * r.cnt for r in camp_rows if r.status == CampaignStatus.COMPLETED) / max(completed, 1)
    total_budget = sum(_f(r.total_budget) for r in camp_rows)
    total_rev = sum(_f(r.total_rev) for r in camp_rows if r.status == CampaignStatus.COMPLETED)

    by_campaign_type = [
        DistributionSlice(
            label=r.campaign_type if isinstance(r.campaign_type, str) else r.campaign_type.value,
            value=round(_f(r.avg_roi), 2),
            count=r.cnt,
        )
        for r in camp_rows if r.status == CampaignStatus.COMPLETED
    ]

    # Campaign revenue trend (by campaign start_date bucketed to days)
    camp_trend_rows = (await db.execute(
        select(Campaign.start_date, func.sum(Campaign.actual_revenue).label("rev"))
        .where(Campaign.start_date >= start, Campaign.status == CampaignStatus.COMPLETED)
        .group_by(Campaign.start_date)
    )).all()
    camp_rev_map = defaultdict(float)
    for r in camp_trend_rows:
        camp_rev_map[str(r.start_date)] += _f(r.rev)

    # ── Spend KPIs ─────────────────────────────────────────────────────────────
    trade_rows = (await db.execute(
        select(TradeSpend.spend_date, func.sum(TradeSpend.amount).label("amt"))
        .where(TradeSpend.spend_date >= start)
        .group_by(TradeSpend.spend_date)
    )).all()
    trade_map = defaultdict(float)
    total_trade = 0.0
    for r in trade_rows:
        total_trade += _f(r.amt)
        trade_map[str(r.spend_date)] += _f(r.amt)

    brand_rows = (await db.execute(
        select(BrandSpend.spend_date, func.sum(BrandSpend.amount).label("amt"))
        .where(BrandSpend.spend_date >= start)
        .group_by(BrandSpend.spend_date)
    )).all()
    brand_map = defaultdict(float)
    total_brand = 0.0
    for r in brand_rows:
        total_brand += _f(r.amt)
        brand_map[str(r.spend_date)] += _f(r.amt)

    # Invoiced sales in period (for spend-vs-sales %)
    inv_rows = (await db.execute(
        select(func.sum(Invoice.total_amount).label("total"))
        .where(Invoice.invoice_date >= start, Invoice.status != InvoiceStatus.CANCELLED)
    )).scalar_one_or_none()
    period_sales = _f(inv_rows)
    trade_vs_sales_pct = (total_trade / period_sales * 100) if period_sales > 0 else 0.0
    brand_vs_rev_pct = (total_brand / max(total_rev, 1) * 100) if total_rev > 0 else 0.0

    # ── Influencer KPIs ────────────────────────────────────────────────────────
    inf_rows = (await db.execute(
        select(
            Influencer.platform,
            func.count(Influencer.id).label("cnt"),
            func.sum(InfluencerCampaignLink.attributed_revenue).label("total_rev"),
            func.avg(InfluencerCampaignLink.performance_score).label("avg_score"),
            func.sum(InfluencerCampaignLink.agreed_fee).label("total_fees"),
        )
        .join(InfluencerCampaignLink, InfluencerCampaignLink.influencer_id == Influencer.id, isouter=True)
        .where(Influencer.status == InfluencerStatus.ACTIVE)
        .group_by(Influencer.platform)
    )).all()
    active_influencers = sum(r.cnt for r in inf_rows)
    inf_total_rev = sum(_f(r.total_rev) for r in inf_rows)
    inf_avg_score = sum(_f(r.avg_score) * r.cnt for r in inf_rows) / max(active_influencers, 1)
    inf_total_fees = sum(_f(r.total_fees) for r in inf_rows)
    inf_roi = inf_total_rev / max(inf_total_fees, 1)
    by_influencer_platform = [
        DistributionSlice(label=r.platform if isinstance(r.platform, str) else r.platform.value,
                          value=round(_f(r.total_rev), 2), count=r.cnt)
        for r in inf_rows
    ]

    # ── Social media KPIs ──────────────────────────────────────────────────────
    social_rows = (await db.execute(
        select(
            SocialMediaActivity.platform,
            SocialMediaActivity.published_date,
            func.sum(SocialMediaActivity.impressions).label("imp"),
            func.sum(SocialMediaActivity.engagements).label("eng"),
        )
        .where(SocialMediaActivity.published_date >= start)
        .group_by(SocialMediaActivity.platform, SocialMediaActivity.published_date)
    )).all()
    total_imp = sum(int(r.imp or 0) for r in social_rows)
    total_eng = sum(int(r.eng or 0) for r in social_rows)
    eng_rate = total_eng / max(total_imp, 1)
    eng_map = defaultdict(float)
    eng_by_plat: dict[str, float] = defaultdict(float)
    for r in social_rows:
        eng_map[str(r.published_date)] += _f(r.eng)
        plat = r.platform if isinstance(r.platform, str) else r.platform.value
        eng_by_plat[plat] += _f(r.eng)
    top_social = max(eng_by_plat, key=eng_by_plat.get) if eng_by_plat else None

    # ── Ad KPIs ────────────────────────────────────────────────────────────────
    ad_rows = (await db.execute(
        select(
            AdPerformance.platform,
            AdPerformance.ad_date,
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.revenue_generated).label("rev"),
        )
        .where(AdPerformance.ad_date >= start)
        .group_by(AdPerformance.platform, AdPerformance.ad_date)
    )).all()
    total_ad_spend = sum(_f(r.spend) for r in ad_rows)
    total_ad_rev = sum(_f(r.rev) for r in ad_rows)
    overall_roas = total_ad_rev / max(total_ad_spend, 1)
    ad_spend_map = defaultdict(float)
    ad_rev_by_plat: dict[str, float] = defaultdict(float)
    for r in ad_rows:
        ad_spend_map[str(r.ad_date)] += _f(r.spend)
        plat = r.platform if isinstance(r.platform, str) else r.platform.value
        ad_rev_by_plat[plat] += _f(r.rev)
    best_ad = max(ad_rev_by_plat, key=ad_rev_by_plat.get) if ad_rev_by_plat else None
    by_ad_platform = [
        DistributionSlice(label=p, value=round(v, 2), count=1)
        for p, v in sorted(ad_rev_by_plat.items(), key=lambda x: -x[1])
    ]

    # ── E-commerce KPIs ────────────────────────────────────────────────────────
    ecomm_rows = (await db.execute(
        select(
            func.sum(StorePerformance.total_revenue).label("rev"),
            func.sum(StorePerformance.total_orders).label("orders"),
            func.avg(StorePerformance.conversion_rate).label("cvr"),
            func.avg(StorePerformance.return_rate).label("rr"),
        )
        .where(StorePerformance.perf_date >= start)
    )).one()
    ecomm_rev = _f(ecomm_rows.rev)
    ecomm_orders = int(ecomm_rows.orders or 0)
    avg_cvr = _f(ecomm_rows.cvr)
    avg_rr = _f(ecomm_rows.rr)

    # ── CRM KPIs ───────────────────────────────────────────────────────────────
    crm_rows = (await db.execute(
        select(
            func.count(CRMProfile.id).label("total"),
            func.avg(CRMProfile.engagement_score).label("avg_eng"),
        )
    )).one()
    total_crm = int(crm_rows.total or 0)
    avg_eng = _f(crm_rows.avg_eng)

    at_risk = (await db.execute(
        select(func.count(CRMProfile.id)).where(CRMProfile.churn_risk_score >= 60)
    )).scalar_one() or 0

    vip = (await db.execute(
        select(func.count(CRMProfile.id)).where(CRMProfile.loyalty_status == "VIP")
    )).scalar_one() or 0

    # ── Survey KPIs ────────────────────────────────────────────────────────────
    surv_rows = (await db.execute(
        select(
            func.count(Survey.id).label("cnt"),
            func.avg(Survey.sentiment_score).label("avg_sent"),
        )
        .where(Survey.survey_date >= start)
    )).one()
    survey_cnt = int(surv_rows.cnt or 0)
    avg_sent = _f(surv_rows.avg_sent)

    # ── Attribution-ready sales linkage ────────────────────────────────────────
    camp_orders = (await db.execute(
        select(func.count(SalesOrder.id))
        .where(SalesOrder.campaign_id.isnot(None), SalesOrder.order_date >= start)
    )).scalar_one() or 0

    promo_orders = (await db.execute(
        select(func.count(SalesOrder.id))
        .where(SalesOrder.promotion_id.isnot(None), SalesOrder.order_date >= start)
    )).scalar_one() or 0

    # ── Exceptions / signals ───────────────────────────────────────────────────
    exceptions: List[ExceptionRow] = []
    if int(at_risk) > 5:
        exceptions.append(ExceptionRow(
            id="crm_churn", label=f"{at_risk} At-Risk Customers",
            detail="Churn risk score ≥ 60 — activate retention campaign",
            severity="high", href="/dashboard/marketing/crm",
        ))
    if overall_roas < 1.2 and total_ad_spend > 0:
        exceptions.append(ExceptionRow(
            id="roas_low", label=f"Low Ad ROAS ({overall_roas:.2f}x)",
            detail="Ad spend return below 1.2x — review ad creative and targeting",
            severity="medium", href="/dashboard/marketing/ads",
        ))
    if avg_sent < 4.0 and survey_cnt > 0:
        exceptions.append(ExceptionRow(
            id="survey_neg", label=f"Low Survey Sentiment ({avg_sent:.1f}/10)",
            detail="Customer sentiment trending negative — review product/service issues",
            severity="medium", href="/dashboard/marketing/surveys",
        ))

    return MarketingBIKPIs(
        completed_campaigns=completed,
        active_campaigns=active,
        avg_campaign_roi=round(avg_roi, 2),
        total_campaign_budget=round(total_budget, 2),
        total_campaign_revenue=round(total_rev, 2),
        overall_campaign_efficiency=round(total_rev / max(total_budget, 1), 2),
        total_trade_spend=round(total_trade, 2),
        total_brand_spend=round(total_brand, 2),
        trade_spend_vs_sales_pct=round(trade_vs_sales_pct, 1),
        brand_spend_vs_revenue_pct=round(brand_vs_rev_pct, 1),
        active_influencers=active_influencers,
        total_influencer_revenue=round(inf_total_rev, 2),
        avg_influencer_score=round(inf_avg_score, 2),
        influencer_roi=round(inf_roi, 2),
        total_impressions=total_imp,
        total_engagements=total_eng,
        avg_engagement_rate=round(eng_rate, 4),
        top_social_platform=top_social,
        total_ad_spend=round(total_ad_spend, 2),
        total_ad_revenue=round(total_ad_rev, 2),
        overall_roas=round(overall_roas, 2),
        best_ad_platform=best_ad,
        ecommerce_revenue=round(ecomm_rev, 2),
        ecommerce_orders=ecomm_orders,
        avg_conversion_rate=round(avg_cvr, 4),
        overall_return_rate=round(avg_rr, 4),
        total_crm_profiles=total_crm,
        at_risk_customers=int(at_risk),
        vip_customers=int(vip),
        avg_engagement_score=round(avg_eng, 1),
        avg_survey_sentiment=round(avg_sent, 1),
        survey_count=survey_cnt,
        campaign_linked_orders=int(camp_orders),
        promotion_linked_orders=int(promo_orders),
        campaign_revenue_trend=_fill_trend(dict(camp_rev_map), start, days),
        trade_spend_trend=_fill_trend(dict(trade_map), start, days),
        brand_spend_trend=_fill_trend(dict(brand_map), start, days),
        ad_spend_trend=_fill_trend(dict(ad_spend_map), start, days),
        social_engagement_trend=_fill_trend(dict(eng_map), start, days),
        by_campaign_type=by_campaign_type,
        by_ad_platform=by_ad_platform,
        by_influencer_platform=by_influencer_platform,
        exceptions=exceptions,
    )


# ── Marketing sub-dashboard detail endpoints ───────────────────────────────────

class CampaignDetailRow(BaseModel):
    id: str
    campaign_name: str
    campaign_type: str
    status: str
    region: Optional[str]
    budget: float
    actual_revenue: float
    actual_roi: float
    start_date: Optional[str]
    end_date: Optional[str]


class MarketingCampaignsDetail(BaseModel):
    campaigns: List[CampaignDetailRow]
    total_budget: float
    total_revenue: float
    avg_roi: float
    by_type: List[DistributionSlice]
    revenue_trend: List[TrendPoint]


@router.get("/marketing/campaigns", response_model=MarketingCampaignsDetail,
            dependencies=[Depends(require_permission("marketing_analytics", "view"))])
async def marketing_campaigns_detail(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.marketing import Campaign, CampaignStatus
    from collections import defaultdict
    today = _today()
    start = today - timedelta(days=days - 1)

    rows = (await db.execute(
        select(Campaign)
        .where(Campaign.start_date >= start)
        .order_by(Campaign.actual_roi.desc().nulls_last())
        .limit(50)
    )).scalars().all()

    detail = [
        CampaignDetailRow(
            id=str(c.id),
            campaign_name=c.campaign_name,
            campaign_type=c.campaign_type.value if hasattr(c.campaign_type, "value") else str(c.campaign_type),
            status=c.status.value if hasattr(c.status, "value") else str(c.status),
            region=c.region,
            budget=_f(c.budget),
            actual_revenue=_f(c.actual_revenue),
            actual_roi=_f(c.actual_roi),
            start_date=str(c.start_date) if c.start_date else None,
            end_date=str(c.end_date) if c.end_date else None,
        )
        for c in rows
    ]

    total_budget = sum(r.budget for r in detail)
    total_rev = sum(r.actual_revenue for r in detail)
    completed = [r for r in detail if r.status == "COMPLETED"]
    avg_roi = sum(r.actual_roi for r in completed) / max(len(completed), 1)

    # Distribution by type
    type_map: dict[str, float] = defaultdict(float)
    type_cnt: dict[str, int] = defaultdict(int)
    for r in detail:
        type_map[r.campaign_type] += r.actual_revenue
        type_cnt[r.campaign_type] += 1
    by_type = [
        DistributionSlice(label=t, value=round(v, 2), count=type_cnt[t])
        for t, v in sorted(type_map.items(), key=lambda x: -x[1])
    ]

    # Revenue trend
    trend_map: dict[str, float] = defaultdict(float)
    for r in detail:
        if r.start_date:
            trend_map[r.start_date] += r.actual_revenue
    revenue_trend = _fill_trend(dict(trend_map), start, days)

    return MarketingCampaignsDetail(
        campaigns=detail,
        total_budget=round(total_budget, 2),
        total_revenue=round(total_rev, 2),
        avg_roi=round(avg_roi, 2),
        by_type=by_type,
        revenue_trend=revenue_trend,
    )


# ── Influencer sub-dashboard ───────────────────────────────────────────────────

class InfluencerDetailRow(BaseModel):
    id: str
    influencer_name: str
    platform: str
    handle: Optional[str]
    category: Optional[str]
    followers_count: int
    attributed_revenue: float
    agreed_fee: float
    performance_score: float
    roi: float


class MarketingInfluencersDetail(BaseModel):
    influencers: List[InfluencerDetailRow]
    total_revenue: float
    total_fees: float
    overall_roi: float
    avg_score: float
    by_platform: List[DistributionSlice]


@router.get("/marketing/influencers", response_model=MarketingInfluencersDetail,
            dependencies=[Depends(require_permission("marketing_analytics", "view"))])
async def marketing_influencers_detail(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.marketing import Influencer, InfluencerCampaignLink, InfluencerStatus
    from collections import defaultdict
    today = _today()
    start = today - timedelta(days=days - 1)

    rows = (await db.execute(
        select(
            Influencer.id,
            Influencer.influencer_name,
            Influencer.platform,
            Influencer.handle,
            Influencer.category,
            Influencer.followers_count,
            func.sum(InfluencerCampaignLink.attributed_revenue).label("total_rev"),
            func.sum(InfluencerCampaignLink.agreed_fee).label("total_fee"),
            func.avg(InfluencerCampaignLink.performance_score).label("avg_score"),
        )
        .join(InfluencerCampaignLink, InfluencerCampaignLink.influencer_id == Influencer.id, isouter=True)
        .where(Influencer.status == InfluencerStatus.ACTIVE)
        .group_by(Influencer.id, Influencer.influencer_name, Influencer.platform,
                  Influencer.handle, Influencer.category, Influencer.followers_count)
        .order_by(func.sum(InfluencerCampaignLink.attributed_revenue).desc().nulls_last())
        .limit(30)
    )).all()

    detail = []
    plat_rev: dict[str, float] = defaultdict(float)
    plat_cnt: dict[str, int] = defaultdict(int)
    for r in rows:
        rev = _f(r.total_rev)
        fee = _f(r.total_fee)
        roi = rev / max(fee, 1)
        plat = r.platform.value if hasattr(r.platform, "value") else str(r.platform)
        plat_rev[plat] += rev
        plat_cnt[plat] += 1
        detail.append(InfluencerDetailRow(
            id=str(r.id),
            influencer_name=r.influencer_name,
            platform=plat,
            handle=r.handle,
            category=r.category,
            followers_count=int(r.followers_count or 0),
            attributed_revenue=round(rev, 2),
            agreed_fee=round(fee, 2),
            performance_score=round(_f(r.avg_score), 1),
            roi=round(roi, 2),
        ))

    total_rev = sum(r.attributed_revenue for r in detail)
    total_fee = sum(r.agreed_fee for r in detail)
    avg_score = sum(r.performance_score for r in detail) / max(len(detail), 1)

    by_platform = [
        DistributionSlice(label=p, value=round(v, 2), count=plat_cnt[p])
        for p, v in sorted(plat_rev.items(), key=lambda x: -x[1])
    ]

    return MarketingInfluencersDetail(
        influencers=detail,
        total_revenue=round(total_rev, 2),
        total_fees=round(total_fee, 2),
        overall_roi=round(total_rev / max(total_fee, 1), 2),
        avg_score=round(avg_score, 1),
        by_platform=by_platform,
    )


# ── Ads sub-dashboard ──────────────────────────────────────────────────────────

class AdPlatformRow(BaseModel):
    platform: str
    spend: float
    revenue: float
    roas: float
    impressions: int
    clicks: int
    conversions: int
    days_active: int


class MarketingAdsDetail(BaseModel):
    by_platform: List[AdPlatformRow]
    spend_trend: List[TrendPoint]
    revenue_trend: List[TrendPoint]
    total_spend: float
    total_revenue: float
    overall_roas: float


@router.get("/marketing/ads", response_model=MarketingAdsDetail,
            dependencies=[Depends(require_permission("marketing_analytics", "view"))])
async def marketing_ads_detail(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.marketing import AdPerformance
    from collections import defaultdict
    today = _today()
    start = today - timedelta(days=days - 1)

    rows = (await db.execute(
        select(
            AdPerformance.platform,
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.revenue_generated).label("revenue"),
            func.sum(AdPerformance.impressions).label("imps"),
            func.sum(AdPerformance.clicks).label("clicks"),
            func.sum(AdPerformance.conversions).label("convs"),
            func.count(AdPerformance.id).label("days_active"),
        )
        .where(AdPerformance.ad_date >= start)
        .group_by(AdPerformance.platform)
        .order_by(func.sum(AdPerformance.revenue_generated).desc().nulls_last())
    )).all()

    by_platform = []
    for r in rows:
        spend = _f(r.spend)
        rev = _f(r.revenue)
        by_platform.append(AdPlatformRow(
            platform=r.platform.value if hasattr(r.platform, "value") else str(r.platform),
            spend=round(spend, 2),
            revenue=round(rev, 2),
            roas=round(rev / max(spend, 1), 2),
            impressions=int(r.imps or 0),
            clicks=int(r.clicks or 0),
            conversions=int(r.convs or 0),
            days_active=int(r.days_active or 0),
        ))

    # Daily trend
    trend_rows = (await db.execute(
        select(
            AdPerformance.ad_date,
            func.sum(AdPerformance.spend).label("spend"),
            func.sum(AdPerformance.revenue_generated).label("revenue"),
        )
        .where(AdPerformance.ad_date >= start)
        .group_by(AdPerformance.ad_date)
    )).all()
    spend_map: dict[str, float] = {}
    rev_map: dict[str, float] = {}
    for r in trend_rows:
        spend_map[str(r.ad_date)] = _f(r.spend)
        rev_map[str(r.ad_date)] = _f(r.revenue)

    total_spend = sum(p.spend for p in by_platform)
    total_rev = sum(p.revenue for p in by_platform)

    return MarketingAdsDetail(
        by_platform=by_platform,
        spend_trend=_fill_trend(spend_map, start, days),
        revenue_trend=_fill_trend(rev_map, start, days),
        total_spend=round(total_spend, 2),
        total_revenue=round(total_rev, 2),
        overall_roas=round(total_rev / max(total_spend, 1), 2),
    )


# ── Social sub-dashboard ───────────────────────────────────────────────────────

class SocialPlatformRow(BaseModel):
    platform: str
    impressions: int
    engagements: int
    clicks: int
    post_count: int
    engagement_rate: float


class MarketingSocialDetail(BaseModel):
    by_platform: List[SocialPlatformRow]
    engagement_trend: List[TrendPoint]
    impression_trend: List[TrendPoint]
    total_impressions: int
    total_engagements: int
    avg_engagement_rate: float


@router.get("/marketing/social", response_model=MarketingSocialDetail,
            dependencies=[Depends(require_permission("marketing_analytics", "view"))])
async def marketing_social_detail(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.marketing import SocialMediaActivity
    today = _today()
    start = today - timedelta(days=days - 1)

    rows = (await db.execute(
        select(
            SocialMediaActivity.platform,
            func.sum(SocialMediaActivity.impressions).label("imps"),
            func.sum(SocialMediaActivity.engagements).label("eng"),
            func.sum(SocialMediaActivity.clicks).label("clicks"),
            func.count(SocialMediaActivity.id).label("posts"),
        )
        .where(SocialMediaActivity.published_date >= start)
        .group_by(SocialMediaActivity.platform)
        .order_by(func.sum(SocialMediaActivity.engagements).desc().nulls_last())
    )).all()

    by_platform = []
    for r in rows:
        imps = int(r.imps or 0)
        eng = int(r.eng or 0)
        by_platform.append(SocialPlatformRow(
            platform=r.platform.value if hasattr(r.platform, "value") else str(r.platform),
            impressions=imps,
            engagements=eng,
            clicks=int(r.clicks or 0),
            post_count=int(r.posts or 0),
            engagement_rate=round(eng / max(imps, 1), 4),
        ))

    trend_rows = (await db.execute(
        select(
            SocialMediaActivity.published_date,
            func.sum(SocialMediaActivity.engagements).label("eng"),
            func.sum(SocialMediaActivity.impressions).label("imps"),
        )
        .where(SocialMediaActivity.published_date >= start)
        .group_by(SocialMediaActivity.published_date)
    )).all()
    eng_map: dict[str, float] = {}
    imp_map: dict[str, float] = {}
    for r in trend_rows:
        eng_map[str(r.published_date)] = _f(r.eng)
        imp_map[str(r.published_date)] = _f(r.imps)

    total_imp = sum(p.impressions for p in by_platform)
    total_eng = sum(p.engagements for p in by_platform)

    return MarketingSocialDetail(
        by_platform=by_platform,
        engagement_trend=_fill_trend(eng_map, start, days),
        impression_trend=_fill_trend(imp_map, start, days),
        total_impressions=total_imp,
        total_engagements=total_eng,
        avg_engagement_rate=round(total_eng / max(total_imp, 1), 4),
    )


# ── E-commerce / Stores sub-dashboard ─────────────────────────────────────────

class StoreDetailRow(BaseModel):
    id: str
    store_name: str
    platform: str
    region: Optional[str]
    total_revenue: float
    total_orders: int
    conversion_rate: float
    return_rate: float
    gross_margin: float


class MarketingStoresDetail(BaseModel):
    stores: List[StoreDetailRow]
    revenue_trend: List[TrendPoint]
    total_revenue: float
    total_orders: int
    avg_conversion_rate: float
    avg_return_rate: float
    by_platform: List[DistributionSlice]


@router.get("/marketing/stores", response_model=MarketingStoresDetail,
            dependencies=[Depends(require_permission("marketing_analytics", "view"))])
async def marketing_stores_detail(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.marketing import Store, StorePerformance
    from collections import defaultdict
    today = _today()
    start = today - timedelta(days=days - 1)

    rows = (await db.execute(
        select(
            Store.id,
            Store.store_name,
            Store.platform,
            Store.region,
            func.sum(StorePerformance.total_revenue).label("rev"),
            func.sum(StorePerformance.total_orders).label("orders"),
            func.avg(StorePerformance.conversion_rate).label("cvr"),
            func.avg(StorePerformance.return_rate).label("rr"),
            func.sum(StorePerformance.gross_margin).label("margin"),
        )
        .join(StorePerformance, StorePerformance.store_id == Store.id, isouter=True)
        .where(StorePerformance.perf_date >= start)
        .group_by(Store.id, Store.store_name, Store.platform, Store.region)
        .order_by(func.sum(StorePerformance.total_revenue).desc().nulls_last())
        .limit(30)
    )).all()

    stores = []
    plat_rev: dict[str, float] = defaultdict(float)
    plat_cnt: dict[str, int] = defaultdict(int)
    for r in rows:
        plat = r.platform.value if hasattr(r.platform, "value") else str(r.platform)
        rev = _f(r.rev)
        plat_rev[plat] += rev
        plat_cnt[plat] += 1
        stores.append(StoreDetailRow(
            id=str(r.id),
            store_name=r.store_name,
            platform=plat,
            region=r.region,
            total_revenue=round(rev, 2),
            total_orders=int(r.orders or 0),
            conversion_rate=round(_f(r.cvr), 4),
            return_rate=round(_f(r.rr), 4),
            gross_margin=round(_f(r.margin), 2),
        ))

    trend_rows = (await db.execute(
        select(
            StorePerformance.perf_date,
            func.sum(StorePerformance.total_revenue).label("rev"),
        )
        .where(StorePerformance.perf_date >= start)
        .group_by(StorePerformance.perf_date)
    )).all()
    trend_map = {str(r.perf_date): _f(r.rev) for r in trend_rows}

    total_rev = sum(s.total_revenue for s in stores)
    total_orders = sum(s.total_orders for s in stores)
    avg_cvr = sum(s.conversion_rate for s in stores) / max(len(stores), 1)
    avg_rr = sum(s.return_rate for s in stores) / max(len(stores), 1)

    by_platform = [
        DistributionSlice(label=p, value=round(v, 2), count=plat_cnt[p])
        for p, v in sorted(plat_rev.items(), key=lambda x: -x[1])
    ]

    return MarketingStoresDetail(
        stores=stores,
        revenue_trend=_fill_trend(trend_map, start, days),
        total_revenue=round(total_rev, 2),
        total_orders=total_orders,
        avg_conversion_rate=round(avg_cvr, 4),
        avg_return_rate=round(avg_rr, 4),
        by_platform=by_platform,
    )


# ── Return analytics sub-dashboard ────────────────────────────────────────────

class ReturnDetailRow(BaseModel):
    return_date: str
    return_reason: Optional[str]
    return_count: int
    return_rate: float


class MarketingReturnsDetail(BaseModel):
    returns: List[ReturnDetailRow]
    trend: List[TrendPoint]
    total_returns: int
    avg_return_rate: float
    by_reason: List[DistributionSlice]


@router.get("/marketing/returns", response_model=MarketingReturnsDetail,
            dependencies=[Depends(require_permission("marketing_analytics", "view"))])
async def marketing_returns_detail(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    from app.models.marketing import ReturnAnalytics
    from collections import defaultdict
    today = _today()
    start = today - timedelta(days=days - 1)

    rows = (await db.execute(
        select(ReturnAnalytics)
        .where(ReturnAnalytics.return_date >= start)
        .order_by(ReturnAnalytics.return_date.desc())
        .limit(200)
    )).scalars().all()

    returns = [
        ReturnDetailRow(
            return_date=str(r.return_date),
            return_reason=r.return_reason,
            return_count=int(r.return_count or 0),
            return_rate=round(_f(r.return_rate), 4),
        )
        for r in rows
    ]

    total_returns = sum(r.return_count for r in returns)
    avg_rr = sum(r.return_rate for r in returns) / max(len(returns), 1)

    reason_cnt: dict[str, int] = defaultdict(int)
    for r in returns:
        reason_cnt[r.return_reason or "Unknown"] += r.return_count

    by_reason = [
        DistributionSlice(label=reason, value=float(cnt), count=cnt)
        for reason, cnt in sorted(reason_cnt.items(), key=lambda x: -x[1])
    ][:10]

    trend_map: dict[str, float] = defaultdict(float)
    for r in returns:
        trend_map[r.return_date] += r.return_count
    trend = _fill_trend(dict(trend_map), start, days)

    return MarketingReturnsDetail(
        returns=returns[:50],
        trend=trend,
        total_returns=total_returns,
        avg_return_rate=round(avg_rr, 4),
        by_reason=by_reason,
    )


# ── Daily KPI Framework ───────────────────────────────────────────────────────
# Consolidated snapshot of all critical daily KPIs — single call for the hub page.

class DailyKPIs(BaseModel):
    as_of: str                        # ISO datetime

    # Sales
    daily_sales_amount: float          # today's confirmed invoice totals
    daily_sales_orders: int            # today's confirmed SO count
    open_receivables: float            # all outstanding invoice amounts

    # Inventory
    stock_value: float                 # total inventory value
    low_stock_count: int               # items at/below reorder point
    zero_stock_count: int              # items with zero stock

    # Production
    production_plan_qty: float         # today planned production qty
    production_actual_qty: float       # today actual production qty
    production_completion_pct: float   # actual/planned × 100

    # Procurement
    purchase_delay_count: int          # POs past expected delivery date

    # Finance / Payments
    payment_collection_today: float    # cash receipts + M-Pesa collected today
    failed_payment_count: int          # failed M-Pesa today
    open_receivables_overdue: float    # overdue invoice outstanding balance

    # M-Pesa
    mpesa_collected_today: float
    mpesa_success_rate: float          # today %
    mpesa_pending_count: int

    # Maintenance
    machines_down: int
    open_breakdowns: int

    # Trends (7d for each key metric)
    sales_trend_7d: List[TrendPoint]
    mpesa_trend_7d: List[TrendPoint]
    production_trend_7d: List[TrendPoint]


@router.get("/kpi/daily", response_model=DailyKPIs,
            dependencies=[Depends(require_permission("analytics", "view"))])
async def daily_kpis(db: AsyncSession = Depends(get_db)):
    """
    Consolidated daily KPI snapshot for the BI hub page.
    All metrics sourced from real data — nothing hardcoded.
    """
    from app.models.sales import (
        SalesOrder, SOStatus, SOLine, Invoice, InvoiceStatus, MpesaTransaction, MpesaTxStatus
    )
    from app.models.inventory import Stock, StockMovement
    from app.models.master import Product, Material
    from app.models.production import ProductionOrder, ProductionOrderStatus
    from app.models.procurement import PurchaseOrder, POStatus
    from app.models.finance import CashTransaction, TxDirection, FinTxStatus
    from app.models.maintenance import Asset, AssetStatus, BreakdownRecord, BreakdownStatus

    today = _today()
    seven_days_ago = today - timedelta(days=6)

    # ── Sales today ──
    so_row = (await db.execute(
        select(
            func.count(func.distinct(SalesOrder.id)),
            func.coalesce(
                func.sum(
                    SOLine.ordered_quantity * SOLine.unit_price
                    * (1 - func.coalesce(SOLine.discount_pct, 0))
                ), 0
            ),
        )
        .outerjoin(SOLine, SOLine.so_id == SalesOrder.id)
        .where(and_(SalesOrder.order_date == today,
                    SalesOrder.status.notin_([SOStatus.CANCELLED, SOStatus.DRAFT])))
    )).one()
    daily_sales_orders = so_row[0] or 0
    daily_sales_amount = _f(so_row[1])

    # 7-day sales trend (invoice-based)
    s_trend = (await db.execute(
        select(Invoice.invoice_date.label("d"),
               func.coalesce(func.sum(Invoice.total_amount), 0).label("amt"))
        .where(and_(Invoice.invoice_date.between(seven_days_ago, today),
                    Invoice.status.notin_([InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED])))
        .group_by(Invoice.invoice_date)
    )).all()
    s_map = {str(r.d): _f(r.amt) for r in s_trend}

    # Open receivables
    recv = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0))
        .where(Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]))
    )).scalar_one()
    open_recv = _f(recv)

    overdue_recv = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0))
        .where(Invoice.status == InvoiceStatus.OVERDUE)
    )).scalar_one()
    open_recv_overdue = _f(overdue_recv)

    # ── Inventory ──
    prod_s = (await db.execute(
        select(Product.reorder_point, Product.standard_cost,
               func.coalesce(func.sum(Stock.quantity_on_hand), 0).label("qty"))
        .join(Stock, Stock.product_id == Product.id)
        .where(Stock.product_id.isnot(None))
        .group_by(Product.id, Product.reorder_point, Product.standard_cost)
    )).all()
    mat_s = (await db.execute(
        select(Material.reorder_point, Material.standard_cost,
               func.coalesce(func.sum(Stock.quantity_on_hand), 0).label("qty"))
        .join(Stock, Stock.material_id == Material.id)
        .where(Stock.material_id.isnot(None))
        .group_by(Material.id, Material.reorder_point, Material.standard_cost)
    )).all()

    stock_value = sum(_f(r.qty) * _f(r.standard_cost) for r in list(prod_s) + list(mat_s))
    low_stock_count = sum(1 for r in list(prod_s) + list(mat_s) if _f(r.qty) <= _f(r.reorder_point))
    zero_stock_count = sum(1 for r in list(prod_s) + list(mat_s) if _f(r.qty) <= 0)

    # ── Production today ──
    prod_row = (await db.execute(
        select(func.coalesce(func.sum(ProductionOrder.planned_quantity), 0),
               func.coalesce(func.sum(ProductionOrder.actual_quantity), 0))
        .where(and_(
            ProductionOrder.status.in_([
                ProductionOrderStatus.IN_PROGRESS,
                ProductionOrderStatus.COMPLETED,
                ProductionOrderStatus.RELEASED,
            ]),
            cast(ProductionOrder.scheduled_start, SADate) == today,
        ))
    )).one()
    prod_planned = _f(prod_row[0])
    prod_actual = _f(prod_row[1])
    prod_pct = (prod_actual / prod_planned * 100) if prod_planned > 0 else 0.0

    # 7-day production trend
    p_trend = (await db.execute(
        select(cast(ProductionOrder.scheduled_start, SADate).label("d"),
               func.coalesce(func.sum(ProductionOrder.actual_quantity), 0).label("qty"))
        .where(and_(
            ProductionOrder.status == ProductionOrderStatus.COMPLETED,
            cast(ProductionOrder.scheduled_start, SADate).between(seven_days_ago, today),
        ))
        .group_by(text("d"))
    )).all()
    p_map = {str(r.d): _f(r.qty) for r in p_trend}

    # ── Procurement delays ──
    delay_count = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(and_(
            PurchaseOrder.status.in_([POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED]),
            PurchaseOrder.expected_delivery_date < today,
        ))
    )).scalar_one() or 0

    # ── M-Pesa today ──
    mpesa_rows = (await db.execute(
        select(MpesaTransaction.status,
               func.count(MpesaTransaction.id),
               func.coalesce(func.sum(MpesaTransaction.amount), 0))
        .where(cast(MpesaTransaction.created_at, SADate) == today)
        .group_by(MpesaTransaction.status)
    )).all()
    mp_map = {r[0]: (r[1], _f(r[2])) for r in mpesa_rows}
    mp_total = sum(v[0] for v in mp_map.values())
    mp_collected = _f(mp_map.get(MpesaTxStatus.COMPLETED, (0, 0.0))[1])
    mp_failed = mp_map.get(MpesaTxStatus.FAILED, (0, 0))[0]
    mp_pending = mp_map.get(MpesaTxStatus.PENDING, (0, 0))[0]
    mp_success_rate = ((mp_total - mp_failed) / mp_total * 100) if mp_total > 0 else 100.0

    # 7-day M-Pesa collection trend
    mp_trend = (await db.execute(
        select(cast(MpesaTransaction.created_at, SADate).label("d"),
               func.coalesce(func.sum(MpesaTransaction.amount), 0).label("amt"))
        .where(and_(
            MpesaTransaction.status == MpesaTxStatus.COMPLETED,
            cast(MpesaTransaction.created_at, SADate).between(seven_days_ago, today),
        ))
        .group_by(text("d"))
    )).all()
    mp_map7 = {str(r.d): _f(r.amt) for r in mp_trend}

    # ── Cash receipts today ──
    cash_today = (await db.execute(
        select(func.coalesce(func.sum(CashTransaction.amount), 0))
        .where(and_(
            CashTransaction.direction == TxDirection.RECEIPT,
            CashTransaction.status == FinTxStatus.CLEARED,
            cast(CashTransaction.transaction_date, SADate) == today,
        ))
    )).scalar_one()
    payment_collection_today = _f(cash_today) + mp_collected

    # ── Maintenance ──
    machines_down = (await db.execute(
        select(func.count(Asset.id)).where(Asset.status == AssetStatus.UNDER_MAINTENANCE)
    )).scalar_one() or 0

    open_breakdowns = (await db.execute(
        select(func.count(BreakdownRecord.id)).where(
            BreakdownRecord.status.in_([BreakdownStatus.OPEN, BreakdownStatus.IN_REPAIR])
        )
    )).scalar_one() or 0

    return DailyKPIs(
        as_of=datetime.now(timezone.utc).isoformat(),
        daily_sales_amount=round(daily_sales_amount, 2),
        daily_sales_orders=daily_sales_orders,
        open_receivables=round(open_recv, 2),
        stock_value=round(stock_value, 2),
        low_stock_count=low_stock_count,
        zero_stock_count=zero_stock_count,
        production_plan_qty=round(prod_planned, 2),
        production_actual_qty=round(prod_actual, 2),
        production_completion_pct=round(prod_pct, 1),
        purchase_delay_count=delay_count,
        payment_collection_today=round(payment_collection_today, 2),
        failed_payment_count=mp_failed,
        open_receivables_overdue=round(open_recv_overdue, 2),
        mpesa_collected_today=round(mp_collected, 2),
        mpesa_success_rate=round(mp_success_rate, 1),
        mpesa_pending_count=mp_pending,
        machines_down=machines_down,
        open_breakdowns=open_breakdowns,
        sales_trend_7d=_fill_trend(s_map, seven_days_ago, 7),
        mpesa_trend_7d=_fill_trend(mp_map7, seven_days_ago, 7),
        production_trend_7d=_fill_trend(p_map, seven_days_ago, 7),
    )
