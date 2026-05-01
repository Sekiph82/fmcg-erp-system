"""
Secondary Sales / Distributor Sell-Through Service.
Handles data ingestion, validation, sell-through analytics, and AI insights.
"""
from __future__ import annotations

from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Optional, List
import json
import uuid

from fastapi import HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.secondary_sales import (
    SecondarySalesHeader, SecondarySalesLine, DistributorInventorySnapshot,
    RetailerMaster, SecondarySalesStatus, UploadSource,
)
from app.models.distribution import Distributor
from app.models.master import Product
from app.schemas.secondary_sales import (
    SecondarySalesUpload, SecondarySalesRead, SecondarySalesDetail,
    SecondarySalesLineRead, SellThroughRow, DistributorPerformanceRow,
    ProductSellThroughRow, AIInsightResult,
)
from app.crud import secondary_sales as crud


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _gen_ref() -> str:
    return f"SS-{_now().strftime('%Y%m%d%H%M%S')}"


# ── Upload & Validation ───────────────────────────────────────────────────────

async def upload_secondary_sales(
    db: AsyncSession,
    data: SecondarySalesUpload,
    user_id: uuid.UUID,
) -> SecondarySalesHeader:
    # Verify distributor exists
    dist_r = await db.execute(select(Distributor).where(Distributor.id == data.distributor_id))
    distributor = dist_r.scalar_one_or_none()
    if not distributor:
        raise HTTPException(404, "Distributor not found")

    # Build header
    header = SecondarySalesHeader(
        reference_no=_gen_ref(),
        distributor_id=data.distributor_id,
        period_from=data.period_from,
        period_to=data.period_to,
        upload_source=data.upload_source,
        upload_date=_now(),
        uploaded_by=user_id,
        notes=data.notes,
        status=SecondarySalesStatus.PENDING,
        total_lines=len(data.lines),
        total_value=Decimal("0"),
    )
    await crud.create_header(db, header)

    total_value = Decimal("0")
    validation_errors = []

    for idx, line_in in enumerate(data.lines):
        product_id = line_in.product_id
        retailer_id = line_in.retailer_id
        is_valid = True
        validation_note = None

        # Resolve product by SKU if no id
        if not product_id and line_in.product_sku:
            p_r = await db.execute(select(Product).where(Product.sku == line_in.product_sku))
            p = p_r.scalar_one_or_none()
            if p:
                product_id = p.id
            else:
                is_valid = False
                validation_note = f"SKU '{line_in.product_sku}' not found"
                validation_errors.append(f"Line {idx + 1}: {validation_note}")

        # Resolve retailer by name if no id
        if not retailer_id and line_in.retailer_name:
            retailer = await crud.get_or_create_retailer_by_name(
                db, line_in.retailer_name, data.distributor_id
            )
            retailer_id = retailer.id

        # Compute total_value if missing
        line_total = line_in.total_value
        if line_total is None and line_in.unit_price:
            line_total = line_in.quantity_sold * line_in.unit_price

        sales_line = SecondarySalesLine(
            header_id=header.id,
            retailer_id=retailer_id,
            retailer_name=line_in.retailer_name,
            product_id=product_id,
            product_sku=line_in.product_sku,
            quantity_sold=line_in.quantity_sold,
            unit_price=line_in.unit_price,
            total_value=line_total,
            sale_date=line_in.sale_date,
            is_valid=is_valid,
            validation_note=validation_note,
        )
        db.add(sales_line)
        if line_total:
            total_value += line_total

    header.total_value = total_value
    if validation_errors:
        header.validation_errors = json.dumps(validation_errors)
        header.status = SecondarySalesStatus.VALIDATED
    else:
        header.status = SecondarySalesStatus.VALIDATED

    await db.flush()
    await db.refresh(header)
    return header


async def process_header(
    db: AsyncSession, header: SecondarySalesHeader
) -> SecondarySalesHeader:
    if header.status != SecondarySalesStatus.VALIDATED:
        raise HTTPException(422, "Only VALIDATED records can be processed")
    header.status = SecondarySalesStatus.PROCESSED
    await db.flush()
    await db.refresh(header)
    return header


async def reject_header(
    db: AsyncSession, header: SecondarySalesHeader, reason: str
) -> SecondarySalesHeader:
    header.status = SecondarySalesStatus.REJECTED
    header.notes = (header.notes or "") + f"\nREJECTED: {reason}"
    await db.flush()
    await db.refresh(header)
    return header


# ── Sell-Through Analysis ─────────────────────────────────────────────────────

async def get_sell_through_report(
    db: AsyncSession,
    distributor_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[SellThroughRow]:
    # Aggregate secondary sales by distributor + product
    q = (
        select(
            SecondarySalesHeader.distributor_id,
            SecondarySalesLine.product_id,
            func.sum(SecondarySalesLine.quantity_sold).label("sell_out_qty"),
            func.sum(SecondarySalesLine.total_value).label("sell_out_value"),
        )
        .join(SecondarySalesLine, SecondarySalesHeader.id == SecondarySalesLine.header_id)
        .where(
            SecondarySalesHeader.status == SecondarySalesStatus.PROCESSED,
            SecondarySalesLine.is_valid == True,  # noqa: E712
            SecondarySalesLine.product_id.isnot(None),
        )
        .group_by(SecondarySalesHeader.distributor_id, SecondarySalesLine.product_id)
    )
    if distributor_id:
        q = q.where(SecondarySalesHeader.distributor_id == distributor_id)
    if date_from:
        q = q.where(SecondarySalesHeader.period_from >= date_from)
    if date_to:
        q = q.where(SecondarySalesHeader.period_to <= date_to)

    result = await db.execute(q)
    rows = result.all()

    # Bulk load distributors and products
    dist_ids = {r.distributor_id for r in rows}
    prod_ids = {r.product_id for r in rows}

    distributors: dict = {}
    if dist_ids:
        dr = await db.execute(select(Distributor).where(Distributor.id.in_(dist_ids)))
        for d in dr.scalars():
            distributors[d.id] = d

    products: dict = {}
    if prod_ids:
        pr = await db.execute(select(Product).where(Product.id.in_(prod_ids)))
        for p in pr.scalars():
            products[p.id] = p

    # Fetch latest inventory snapshots for days-of-stock
    snapshots: dict = {}
    if dist_ids and prod_ids:
        snap_q = await db.execute(
            select(DistributorInventorySnapshot)
            .where(
                DistributorInventorySnapshot.distributor_id.in_(dist_ids),
                DistributorInventorySnapshot.product_id.in_(prod_ids),
            )
            .order_by(DistributorInventorySnapshot.snapshot_date.desc())
        )
        for s in snap_q.scalars():
            key = (s.distributor_id, s.product_id)
            if key not in snapshots:
                snapshots[key] = s

    out = []
    for row in rows:
        dist = distributors.get(row.distributor_id)
        prod = products.get(row.product_id)
        if not dist or not prod:
            continue

        sell_out = Decimal(str(row.sell_out_qty or 0))
        snap = snapshots.get((row.distributor_id, row.product_id))
        stock_qty = snap.stock_qty if snap else None

        # Sell-through rate: sell_out / (sell_out + stock) if stock known
        if stock_qty is not None and (sell_out + stock_qty) > 0:
            rate = (sell_out / (sell_out + stock_qty)) * 100
        else:
            rate = Decimal("0")

        if rate >= 80:
            status = "FAST_MOVING"
        elif rate >= 40:
            status = "NORMAL"
        elif rate > 0:
            status = "SLOW_MOVING"
        else:
            status = "NO_DATA"

        # Days of stock = stock_qty / avg daily sell-out
        days = None
        if stock_qty and sell_out > 0:
            # Assume 30-day period
            avg_daily = sell_out / 30
            days = stock_qty / avg_daily if avg_daily > 0 else None

        out.append(SellThroughRow(
            distributor_id=row.distributor_id,
            distributor_name=dist.name,
            product_sku=prod.sku,
            product_name=prod.name,
            sell_in_qty=Decimal("0"),  # primary sales not yet linked here
            sell_out_qty=sell_out,
            sell_through_rate=rate.quantize(Decimal("0.01")),
            stock_at_distributor=stock_qty,
            days_of_stock=Decimal(str(round(float(days), 1))) if days else None,
            status=status,
        ))

    return out


async def get_distributor_performance(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[DistributorPerformanceRow]:
    q = (
        select(
            SecondarySalesHeader.distributor_id,
            func.sum(SecondarySalesLine.total_value).label("total_value"),
            func.sum(SecondarySalesLine.quantity_sold).label("total_qty"),
            func.count(SecondarySalesLine.id).label("line_count"),
            func.min(SecondarySalesHeader.period_from).label("period_from"),
            func.max(SecondarySalesHeader.period_to).label("period_to"),
        )
        .join(SecondarySalesLine, SecondarySalesHeader.id == SecondarySalesLine.header_id)
        .where(
            SecondarySalesHeader.status == SecondarySalesStatus.PROCESSED,
            SecondarySalesLine.is_valid == True,  # noqa: E712
        )
        .group_by(SecondarySalesHeader.distributor_id)
        .order_by(func.sum(SecondarySalesLine.total_value).desc())
    )
    if date_from:
        q = q.where(SecondarySalesHeader.period_from >= date_from)
    if date_to:
        q = q.where(SecondarySalesHeader.period_to <= date_to)

    result = await db.execute(q)
    rows = result.all()

    dist_ids = {r.distributor_id for r in rows}
    distributors: dict = {}
    if dist_ids:
        dr = await db.execute(select(Distributor).where(Distributor.id.in_(dist_ids)))
        for d in dr.scalars():
            distributors[d.id] = d

    out = []
    for row in rows:
        dist = distributors.get(row.distributor_id)
        out.append(DistributorPerformanceRow(
            distributor_id=row.distributor_id,
            distributor_name=dist.name if dist else str(row.distributor_id),
            total_sell_out_value=Decimal(str(row.total_value or 0)),
            total_sell_out_qty=Decimal(str(row.total_qty or 0)),
            line_count=row.line_count or 0,
            period=f"{row.period_from} – {row.period_to}" if row.period_from else "—",
        ))
    return out


async def get_product_performance(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[ProductSellThroughRow]:
    q = (
        select(
            SecondarySalesLine.product_id,
            func.sum(SecondarySalesLine.quantity_sold).label("total_qty"),
            func.sum(SecondarySalesLine.total_value).label("total_value"),
            func.count(SecondarySalesHeader.distributor_id.distinct()).label("dist_count"),
        )
        .join(SecondarySalesHeader, SecondarySalesHeader.id == SecondarySalesLine.header_id)
        .where(
            SecondarySalesHeader.status == SecondarySalesStatus.PROCESSED,
            SecondarySalesLine.is_valid == True,  # noqa: E712
            SecondarySalesLine.product_id.isnot(None),
        )
        .group_by(SecondarySalesLine.product_id)
        .order_by(func.sum(SecondarySalesLine.quantity_sold).desc())
    )
    if date_from:
        q = q.where(SecondarySalesHeader.period_from >= date_from)
    if date_to:
        q = q.where(SecondarySalesHeader.period_to <= date_to)

    result = await db.execute(q)
    rows = result.all()

    prod_ids = {r.product_id for r in rows if r.product_id}
    products: dict = {}
    if prod_ids:
        pr = await db.execute(select(Product).where(Product.id.in_(prod_ids)))
        for p in pr.scalars():
            products[p.id] = p

    out = []
    for row in rows:
        prod = products.get(row.product_id)
        if not prod:
            continue
        out.append(ProductSellThroughRow(
            product_id=row.product_id,
            product_sku=prod.sku,
            product_name=prod.name,
            total_qty_sold=Decimal(str(row.total_qty or 0)),
            total_value=Decimal(str(row.total_value or 0)),
            distributor_count=row.dist_count or 0,
        ))
    return out


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def ai_demand_signal(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> AIInsightResult:
    products = await get_product_performance(db, date_from, date_to)
    insights = []
    details = []

    if not products:
        insights.append("No secondary sales data processed yet. Upload sell-out data to enable demand signal analysis.")
        return AIInsightResult(
            agent="Demand Signal Analyzer",
            insights=insights,
            generated_at=_now().isoformat(),
        )

    top = products[:3]
    for p in top:
        insights.append(
            f"HIGH VELOCITY: '{p.product_name}' ({p.product_sku}) sold {float(p.total_qty_sold):.0f} units across {p.distributor_count} distributors — strong market pull signal."
        )
        details.append({
            "product_sku": p.product_sku,
            "product_name": p.product_name,
            "total_qty": float(p.total_qty_sold),
            "distributor_coverage": p.distributor_count,
            "signal": "HIGH_DEMAND",
        })

    if len(products) > 3:
        bottom = products[-min(3, len(products) - 3):]
        for p in bottom:
            if float(p.total_qty_sold) < float(products[0].total_qty_sold) * 0.2:
                insights.append(
                    f"WEAK SIGNAL: '{p.product_name}' ({p.product_sku}) low sell-out ({float(p.total_qty_sold):.0f} units). Consider promotional support."
                )

    if not details:
        insights.append("Demand signals within normal range. Continue monitoring.")

    return AIInsightResult(
        agent="Demand Signal Analyzer",
        insights=insights,
        details=details,
        generated_at=_now().isoformat(),
    )


async def ai_distributor_risk(
    db: AsyncSession,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> AIInsightResult:
    sell_through = await get_sell_through_report(db, date_from=date_from, date_to=date_to)
    insights = []
    details = []

    slow_movers = [r for r in sell_through if r.status == "SLOW_MOVING"]
    high_stock = [r for r in sell_through if r.days_of_stock and float(r.days_of_stock) > 60]

    if slow_movers:
        for r in slow_movers[:5]:
            insights.append(
                f"LOW SELL-THROUGH: {r.distributor_name} — '{r.product_name}' at {float(r.sell_through_rate):.1f}% sell-through. Risk of overstock."
            )
            details.append({
                "distributor": r.distributor_name,
                "product": r.product_name,
                "sell_through_rate": float(r.sell_through_rate),
                "risk": "SLOW_MOVING",
            })

    if high_stock:
        for r in high_stock[:5]:
            insights.append(
                f"OVERSTOCK RISK: {r.distributor_name} — '{r.product_name}' has {float(r.days_of_stock):.0f} days of stock. Review replenishment or run promotion."
            )
            details.append({
                "distributor": r.distributor_name,
                "product": r.product_name,
                "days_of_stock": float(r.days_of_stock),
                "risk": "OVERSTOCK",
            })

    if not insights:
        insights.append("No significant distributor risk signals detected. Sell-through rates are healthy.")

    return AIInsightResult(
        agent="Distributor Risk Detector",
        insights=insights,
        details=details,
        generated_at=_now().isoformat(),
    )


async def ai_promotion_impact(
    db: AsyncSession,
    promo_start: Optional[date] = None,
    promo_end: Optional[date] = None,
) -> AIInsightResult:
    insights = []
    details = []

    if not promo_start or not promo_end:
        insights.append("No promotion period specified. Provide promo_start and promo_end to compare before/after sell-through.")
        return AIInsightResult(
            agent="Promotion Impact Analyzer",
            insights=insights,
            generated_at=_now().isoformat(),
        )

    # During promo
    during = await get_product_performance(db, date_from=promo_start, date_to=promo_end)

    # Before promo (same duration before)
    delta = promo_end - promo_start
    before_end = promo_start - timedelta(days=1)
    before_start = before_end - delta
    before = await get_product_performance(db, date_from=before_start, date_to=before_end)

    before_map = {p.product_sku: p for p in before}

    for d_row in during:
        b_row = before_map.get(d_row.product_sku)
        if b_row and float(b_row.total_qty_sold) > 0:
            uplift = (float(d_row.total_qty_sold) - float(b_row.total_qty_sold)) / float(b_row.total_qty_sold) * 100
            if uplift > 20:
                insights.append(f"EFFECTIVE: '{d_row.product_name}' — {uplift:.1f}% uplift during promotion vs prior period.")
                details.append({"product": d_row.product_name, "uplift_pct": round(uplift, 1), "result": "EFFECTIVE"})
            elif uplift < -5:
                insights.append(f"INEFFECTIVE: '{d_row.product_name}' — {abs(uplift):.1f}% decline during promotion. Review execution.")
                details.append({"product": d_row.product_name, "uplift_pct": round(uplift, 1), "result": "INEFFECTIVE"})

    if not insights:
        insights.append("Insufficient comparison data for promotion period. Process more historical secondary sales data.")

    return AIInsightResult(
        agent="Promotion Impact Analyzer",
        insights=insights,
        details=details,
        generated_at=_now().isoformat(),
    )
