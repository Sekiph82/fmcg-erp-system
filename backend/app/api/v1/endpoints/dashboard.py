"""
Dashboard Summary Endpoint
Aggregates KPIs from all modules for the executive mobile dashboard.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, cast, Date as SADate, text

from app.core.deps import get_current_user, get_db

router = APIRouter()


# ── Response Schemas ──────────────────────────────────────────────────────────

class TrendPoint(BaseModel):
    date: str       # "YYYY-MM-DD"
    value: float


class ProductionSummary(BaseModel):
    active_orders: int
    today_planned_qty: float
    today_actual_qty: float
    completion_rate: float          # 0-100%
    machines_down: int
    open_breakdowns: int
    trend_7d: List[TrendPoint]      # last 7 days actual production qty


class LowStockItem(BaseModel):
    id: str
    name: str
    item_type: str                  # "product" | "material"
    quantity_on_hand: float
    reorder_point: float
    uom: str


class InventorySummary(BaseModel):
    total_stock_value: float        # sum(qty_on_hand * standard_cost)
    total_sku_count: int
    critical_low_stock_count: int
    low_stock_items: List[LowStockItem]


class SalesSummary(BaseModel):
    today_invoices_amount: float
    today_orders_count: int
    pending_payments_amount: float  # ISSUED + PARTIALLY_PAID
    overdue_invoices_count: int
    pending_shipments_count: int
    trend_7d: List[TrendPoint]      # last 7 days invoice totals


class MpesaTransactionRow(BaseModel):
    id: str
    phone_number: str
    amount: float
    status: str
    reference: Optional[str]
    created_at: str


class MpesaSummary(BaseModel):
    today_collected: float          # completed M-Pesa transactions today
    pending_count: int
    failed_today: int
    total_today: int
    success_rate: float             # 0-100%
    last_10: List[MpesaTransactionRow]


class LogisticsSummary(BaseModel):
    in_transit: int
    arrived_port: int
    customs_hold: int
    delayed_count: int              # ETA passed, not yet delivered
    arrivals_this_week: int


class AlertItem(BaseModel):
    id: str
    severity: str                   # "low" | "medium" | "critical"
    module: str
    message: str
    timestamp: str
    action_url: str


class DashboardSummary(BaseModel):
    generated_at: str
    production: ProductionSummary
    inventory: InventorySummary
    sales: SalesSummary
    mpesa: MpesaSummary
    logistics: LogisticsSummary
    alerts: List[AlertItem]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _today() -> date:
    return datetime.now(timezone.utc).date()


def _float(val) -> float:
    if val is None:
        return 0.0
    return float(val)


# ── Main Endpoint ─────────────────────────────────────────────────────────────

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = _today()
    seven_days_ago = today - timedelta(days=6)
    week_end = today + timedelta(days=7)
    alerts: List[AlertItem] = []

    # ── PRODUCTION ────────────────────────────────────────────────────────────
    from app.models.production import (
        ProductionOrder, ProductionOrderStatus,
    )
    from app.models.maintenance import Asset, AssetStatus, BreakdownRecord, BreakdownStatus

    # Active production orders (RELEASED + IN_PROGRESS)
    active_result = await db.execute(
        select(func.count(ProductionOrder.id)).where(
            ProductionOrder.status.in_([
                ProductionOrderStatus.RELEASED,
                ProductionOrderStatus.IN_PROGRESS,
            ])
        )
    )
    active_orders = active_result.scalar_one() or 0

    # Today planned vs actual qty (orders scheduled to start today or in progress)
    today_prod_result = await db.execute(
        select(
            func.coalesce(func.sum(ProductionOrder.planned_quantity), 0),
            func.coalesce(func.sum(ProductionOrder.actual_quantity), 0),
        ).where(
            and_(
                ProductionOrder.status.in_([
                    ProductionOrderStatus.IN_PROGRESS,
                    ProductionOrderStatus.COMPLETED,
                    ProductionOrderStatus.RELEASED,
                ]),
                func.cast(ProductionOrder.scheduled_start, SADate) == today,
            )
        )
    )
    row = today_prod_result.one()
    today_planned = _float(row[0])
    today_actual = _float(row[1])
    completion_rate = (today_actual / today_planned * 100) if today_planned > 0 else 0.0

    # Production 7-day trend (actual qty by scheduled_start date)
    prod_trend_result = await db.execute(
        select(
            func.cast(ProductionOrder.scheduled_start, SADate).label("day"),
            func.coalesce(func.sum(ProductionOrder.actual_quantity), 0).label("qty"),
        )
        .where(
            and_(
                ProductionOrder.status == ProductionOrderStatus.COMPLETED,
                func.cast(ProductionOrder.scheduled_start, SADate) >= seven_days_ago,
                func.cast(ProductionOrder.scheduled_start, SADate) <= today,
            )
        )
        .group_by(text("day"))
        .order_by(text("day"))
    )
    prod_trend_map: dict[str, float] = {
        str(r.day): _float(r.qty) for r in prod_trend_result
    }
    prod_trend_7d = [
        TrendPoint(
            date=str(seven_days_ago + timedelta(days=i)),
            value=prod_trend_map.get(str(seven_days_ago + timedelta(days=i)), 0.0),
        )
        for i in range(7)
    ]

    # Machines down (assets under maintenance)
    machines_result = await db.execute(
        select(func.count(Asset.id)).where(
            Asset.status == AssetStatus.UNDER_MAINTENANCE
        )
    )
    machines_down = machines_result.scalar_one() or 0

    # Open breakdowns
    breakdowns_result = await db.execute(
        select(func.count(BreakdownRecord.id)).where(
            BreakdownRecord.status.in_([BreakdownStatus.OPEN, BreakdownStatus.IN_REPAIR])
        )
    )
    open_breakdowns = breakdowns_result.scalar_one() or 0

    # Production delay alert
    delayed_orders_result = await db.execute(
        select(func.count(ProductionOrder.id)).where(
            and_(
                ProductionOrder.status == ProductionOrderStatus.IN_PROGRESS,
                func.cast(ProductionOrder.scheduled_end, SADate) < today,
            )
        )
    )
    delayed_orders = delayed_orders_result.scalar_one() or 0
    if delayed_orders > 0:
        alerts.append(AlertItem(
            id="prod-delay",
            severity="medium",
            module="production",
            message=f"{delayed_orders} production order(s) past scheduled end date",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_url="/dashboard/production/orders",
        ))

    if machines_down > 0:
        alerts.append(AlertItem(
            id="machines-down",
            severity="critical" if machines_down >= 3 else "medium",
            module="maintenance",
            message=f"{machines_down} machine(s) currently under maintenance",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_url="/dashboard/maintenance/assets",
        ))

    production = ProductionSummary(
        active_orders=active_orders,
        today_planned_qty=today_planned,
        today_actual_qty=today_actual,
        completion_rate=round(completion_rate, 1),
        machines_down=machines_down,
        open_breakdowns=open_breakdowns,
        trend_7d=prod_trend_7d,
    )

    # ── INVENTORY ─────────────────────────────────────────────────────────────
    from app.models.inventory import Stock
    from app.models.master import Product, Material

    # Product stocks: join to get reorder_point and standard_cost
    prod_stock_result = await db.execute(
        select(
            Stock.product_id,
            Product.name,
            Product.uom,
            Product.reorder_point,
            Product.standard_cost,
            func.coalesce(func.sum(Stock.quantity_on_hand), 0).label("qty"),
        )
        .join(Product, Stock.product_id == Product.id)
        .where(Stock.product_id.isnot(None))
        .group_by(Stock.product_id, Product.name, Product.uom, Product.reorder_point, Product.standard_cost)
    )
    prod_stock_rows = prod_stock_result.all()

    # Material stocks
    mat_stock_result = await db.execute(
        select(
            Stock.material_id,
            Material.name,
            Material.uom,
            Material.reorder_point,
            Material.standard_cost,
            func.coalesce(func.sum(Stock.quantity_on_hand), 0).label("qty"),
        )
        .join(Material, Stock.material_id == Material.id)
        .where(Stock.material_id.isnot(None))
        .group_by(Stock.material_id, Material.name, Material.uom, Material.reorder_point, Material.standard_cost)
    )
    mat_stock_rows = mat_stock_result.all()

    total_stock_value = 0.0
    sku_count = len(prod_stock_rows) + len(mat_stock_rows)
    low_stock_items: List[LowStockItem] = []

    for r in prod_stock_rows:
        qty = _float(r.qty)
        cost = _float(r.standard_cost) if r.standard_cost else 0.0
        total_stock_value += qty * cost
        if qty <= _float(r.reorder_point):
            low_stock_items.append(LowStockItem(
                id=str(r.product_id),
                name=r.name,
                item_type="product",
                quantity_on_hand=qty,
                reorder_point=_float(r.reorder_point),
                uom=str(r.uom.value) if hasattr(r.uom, "value") else str(r.uom),
            ))

    for r in mat_stock_rows:
        qty = _float(r.qty)
        cost = _float(r.standard_cost) if r.standard_cost else 0.0
        total_stock_value += qty * cost
        if qty <= _float(r.reorder_point):
            low_stock_items.append(LowStockItem(
                id=str(r.material_id),
                name=r.name,
                item_type="material",
                quantity_on_hand=qty,
                reorder_point=_float(r.reorder_point),
                uom=str(r.uom.value) if hasattr(r.uom, "value") else str(r.uom),
            ))

    critical_low = len(low_stock_items)
    if critical_low > 0:
        alerts.append(AlertItem(
            id="low-stock",
            severity="critical" if critical_low >= 5 else "medium",
            module="inventory",
            message=f"{critical_low} item(s) at or below reorder point",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_url="/dashboard/inventory",
        ))

    inventory = InventorySummary(
        total_stock_value=round(total_stock_value, 2),
        total_sku_count=sku_count,
        critical_low_stock_count=critical_low,
        low_stock_items=low_stock_items[:10],  # cap at 10 for response size
    )

    # ── SALES ─────────────────────────────────────────────────────────────────
    from app.models.sales import Invoice, InvoiceStatus, SalesOrder, SOStatus, Shipment, ShipmentStatus

    # Today's invoices total (invoices created today with non-draft status)
    today_inv_result = await db.execute(
        select(
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.total_amount), 0),
        ).where(
            and_(
                Invoice.invoice_date == today,
                Invoice.status.notin_([InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED]),
            )
        )
    )
    inv_row = today_inv_result.one()
    today_inv_count = inv_row[0] or 0
    today_inv_amount = _float(inv_row[1])

    # Today's confirmed sales orders count
    today_so_result = await db.execute(
        select(func.count(SalesOrder.id)).where(
            and_(
                SalesOrder.order_date == today,
                SalesOrder.status.notin_([SOStatus.CANCELLED, SOStatus.DRAFT]),
            )
        )
    )
    today_orders_count = today_so_result.scalar_one() or 0

    # Pending payments (ISSUED + PARTIALLY_PAID invoices)
    pending_pay_result = await db.execute(
        select(
            func.count(Invoice.id),
            func.coalesce(
                func.sum(Invoice.total_amount - Invoice.paid_amount), 0
            ),
        ).where(
            Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID])
        )
    )
    pay_row = pending_pay_result.one()
    pending_payments_amount = _float(pay_row[1])

    # Overdue invoices
    overdue_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.status == InvoiceStatus.OVERDUE
        )
    )
    overdue_count = overdue_result.scalar_one() or 0

    if overdue_count > 0:
        alerts.append(AlertItem(
            id="overdue-invoices",
            severity="critical" if overdue_count >= 5 else "medium",
            module="sales",
            message=f"{overdue_count} overdue invoice(s) awaiting payment",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_url="/dashboard/sales/invoices",
        ))

    # Pending shipments
    pending_ship_result = await db.execute(
        select(func.count(Shipment.id)).where(
            Shipment.status.in_([ShipmentStatus.PENDING, ShipmentStatus.PICKING, ShipmentStatus.PACKED])
        )
    )
    pending_shipments = pending_ship_result.scalar_one() or 0

    # Sales 7-day trend
    sales_trend_result = await db.execute(
        select(
            Invoice.invoice_date.label("day"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("amount"),
        )
        .where(
            and_(
                Invoice.invoice_date >= seven_days_ago,
                Invoice.invoice_date <= today,
                Invoice.status.notin_([InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED]),
            )
        )
        .group_by(Invoice.invoice_date)
        .order_by(Invoice.invoice_date)
    )
    sales_trend_map: dict[str, float] = {
        str(r.day): _float(r.amount) for r in sales_trend_result
    }
    sales_trend_7d = [
        TrendPoint(
            date=str(seven_days_ago + timedelta(days=i)),
            value=sales_trend_map.get(str(seven_days_ago + timedelta(days=i)), 0.0),
        )
        for i in range(7)
    ]

    sales = SalesSummary(
        today_invoices_amount=round(today_inv_amount, 2),
        today_orders_count=today_orders_count,
        pending_payments_amount=round(pending_payments_amount, 2),
        overdue_invoices_count=overdue_count,
        pending_shipments_count=pending_shipments,
        trend_7d=sales_trend_7d,
    )

    # ── MPESA ─────────────────────────────────────────────────────────────────
    from app.models.sales import MpesaTransaction, MpesaTxStatus

    # All M-Pesa transactions today
    mpesa_today_result = await db.execute(
        select(
            MpesaTransaction.status,
            func.count(MpesaTransaction.id),
            func.coalesce(func.sum(MpesaTransaction.amount), 0),
        )
        .where(
            func.cast(MpesaTransaction.created_at, SADate) == today
        )
        .group_by(MpesaTransaction.status)
    )
    mpesa_today_rows = mpesa_today_result.all()

    today_collected = 0.0
    pending_mpesa = 0
    failed_today = 0
    total_today = 0

    for r in mpesa_today_rows:
        count = r[1]
        amount = _float(r[2])
        total_today += count
        if r[0] == MpesaTxStatus.COMPLETED:
            today_collected += amount
        elif r[0] == MpesaTxStatus.PENDING:
            pending_mpesa += count
        elif r[0] == MpesaTxStatus.FAILED:
            failed_today += count

    success_rate = (
        ((total_today - failed_today) / total_today * 100)
        if total_today > 0 else 100.0
    )

    # Last 10 M-Pesa transactions
    last10_result = await db.execute(
        select(MpesaTransaction)
        .order_by(MpesaTransaction.created_at.desc())
        .limit(10)
    )
    last10 = last10_result.scalars().all()

    if failed_today > 0:
        alerts.append(AlertItem(
            id="mpesa-failed",
            severity="medium",
            module="finance",
            message=f"{failed_today} failed M-Pesa transaction(s) today",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_url="/dashboard/finance/mpesa",
        ))

    mpesa = MpesaSummary(
        today_collected=round(today_collected, 2),
        pending_count=pending_mpesa,
        failed_today=failed_today,
        total_today=total_today,
        success_rate=round(success_rate, 1),
        last_10=[
            MpesaTransactionRow(
                id=str(t.id),
                phone_number=t.phone_number,
                amount=_float(t.amount),
                status=t.status.value,
                reference=t.mpesa_reference,
                created_at=t.created_at.isoformat() if t.created_at else "",
            )
            for t in last10
        ],
    )

    # ── LOGISTICS ─────────────────────────────────────────────────────────────
    from app.models.logistics import InternationalShipment, IntlShipmentStatus

    logistics_result = await db.execute(
        select(
            InternationalShipment.status,
            func.count(InternationalShipment.id),
        )
        .where(
            InternationalShipment.status.notin_([
                IntlShipmentStatus.DELIVERED,
                IntlShipmentStatus.CANCELLED,
            ])
        )
        .group_by(InternationalShipment.status)
    )
    logistics_rows = {r[0]: r[1] for r in logistics_result}

    in_transit = logistics_rows.get(IntlShipmentStatus.IN_TRANSIT, 0)
    arrived_port = (
        logistics_rows.get(IntlShipmentStatus.ARRIVED_PORT, 0) +
        logistics_rows.get(IntlShipmentStatus.CUSTOMS_CLEARED, 0) +
        logistics_rows.get(IntlShipmentStatus.OUT_FOR_DELIVERY, 0)
    )
    customs_hold = logistics_rows.get(IntlShipmentStatus.CUSTOMS_HOLD, 0)

    # Delayed: ETA passed, not yet delivered
    delayed_result = await db.execute(
        select(func.count(InternationalShipment.id)).where(
            and_(
                InternationalShipment.eta < today,
                InternationalShipment.ata.is_(None),
                InternationalShipment.status.notin_([
                    IntlShipmentStatus.DELIVERED,
                    IntlShipmentStatus.CANCELLED,
                ])
            )
        )
    )
    delayed_logistics = delayed_result.scalar_one() or 0

    # Arrivals this week
    arrivals_result = await db.execute(
        select(func.count(InternationalShipment.id)).where(
            and_(
                InternationalShipment.eta >= today,
                InternationalShipment.eta <= week_end,
                InternationalShipment.status.notin_([
                    IntlShipmentStatus.DELIVERED,
                    IntlShipmentStatus.CANCELLED,
                ])
            )
        )
    )
    arrivals_this_week = arrivals_result.scalar_one() or 0

    if customs_hold > 0:
        alerts.append(AlertItem(
            id="customs-hold",
            severity="critical",
            module="logistics",
            message=f"{customs_hold} shipment(s) on customs hold",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_url="/dashboard/logistics/shipments",
        ))

    if delayed_logistics > 0:
        alerts.append(AlertItem(
            id="shipment-delay",
            severity="medium",
            module="logistics",
            message=f"{delayed_logistics} shipment(s) past ETA — not yet arrived",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_url="/dashboard/logistics/shipments",
        ))

    logistics = LogisticsSummary(
        in_transit=in_transit,
        arrived_port=arrived_port,
        customs_hold=customs_hold,
        delayed_count=delayed_logistics,
        arrivals_this_week=arrivals_this_week,
    )

    # ── QC REJECTION ALERT ────────────────────────────────────────────────────
    from app.models.quality import QCInspection, QCStatus

    qc_fail_result = await db.execute(
        select(func.count(QCInspection.id)).where(
            and_(
                QCInspection.status == QCStatus.FAILED,
                func.cast(QCInspection.created_at, SADate) == today,
            )
        )
    )
    qc_fails_today = qc_fail_result.scalar_one() or 0
    if qc_fails_today >= 3:
        alerts.append(AlertItem(
            id="qc-rejection",
            severity="critical" if qc_fails_today >= 5 else "medium",
            module="quality",
            message=f"{qc_fails_today} QC rejection(s) recorded today",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_url="/dashboard/quality",
        ))

    # Sort alerts: critical first
    severity_order = {"critical": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

    return DashboardSummary(
        generated_at=datetime.now(timezone.utc).isoformat(),
        production=production,
        inventory=inventory,
        sales=sales,
        mpesa=mpesa,
        logistics=logistics,
        alerts=alerts,
    )
