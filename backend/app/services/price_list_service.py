from __future__ import annotations
import uuid
import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_list import (
    PLHeader, PLLine, PLTier, PLAssignment, PLDiscountRule,
    PLApproval, PLChangeHistory, PLAIRecommendation,
    PLType, PLStatus, PLDiscountType, PLApprovalAction,
    PLDiscountScope, PLChangeType, PLAIAgentType, PLAIRecStatus,
)
from app.models.sales import Customer
from app.models.master import Product
from app.models.finance import ProductCost
from app.schemas.price_list import (
    PLHeaderCreate, PLHeaderUpdate,
    PLLineCreate, PLLineUpdate,
    PLTierCreate,
    PLAssignmentCreate,
    PLDiscountRuleCreate,
    PLApprovalSubmit, PLApprovalReview,
    PriceResolveRequest,
    MarginCheckRequest,
    PLBulkImportRequest, PLBulkImportResult,
    PLAIRecAck,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return date.today()


def _log_change(
    db: AsyncSession,
    header_id: uuid.UUID,
    change_type: PLChangeType,
    changed_by: str,
    line_id: Optional[uuid.UUID] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    notes: Optional[str] = None,
) -> PLChangeHistory:
    h = PLChangeHistory(
        header_id=header_id,
        line_id=line_id,
        change_type=change_type,
        changed_by=changed_by,
        changed_at=_now(),
        old_value_json=old_value,
        new_value_json=new_value,
        notes=notes,
    )
    db.add(h)
    return h


# ── Header CRUD ───────────────────────────────────────────────────────────────

async def create_header(db: AsyncSession, payload: PLHeaderCreate) -> PLHeader:
    hdr = PLHeader(**payload.model_dump())
    db.add(hdr)
    await db.flush()
    _log_change(db, hdr.id, PLChangeType.STATUS_CHANGE, payload.created_by or "system",
                new_value={"status": PLStatus.DRAFT})
    await db.refresh(hdr)
    return hdr


async def list_headers(
    db: AsyncSession,
    status: Optional[str] = None,
    pl_type: Optional[str] = None,
    active_only: bool = False,
) -> List[PLHeader]:
    q = select(PLHeader)
    if status:
        q = q.where(PLHeader.status == status)
    if pl_type:
        q = q.where(PLHeader.pl_type == pl_type)
    if active_only:
        today = _today()
        q = q.where(
            PLHeader.status == PLStatus.ACTIVE,
            PLHeader.valid_from <= today,
            or_(PLHeader.valid_to == None, PLHeader.valid_to >= today),
        )
    return list((await db.execute(q.order_by(PLHeader.priority_rank, PLHeader.created_at.desc()))).scalars())


async def get_header(db: AsyncSession, header_id: uuid.UUID) -> Optional[PLHeader]:
    return (await db.execute(select(PLHeader).where(PLHeader.id == header_id))).scalar_one_or_none()


async def update_header(db: AsyncSession, header_id: uuid.UUID, payload: PLHeaderUpdate, updated_by: str = "system") -> Optional[PLHeader]:
    hdr = await get_header(db, header_id)
    if not hdr or hdr.status in (PLStatus.ACTIVE, PLStatus.APPROVED, PLStatus.ARCHIVED):
        return None
    old = {k: str(getattr(hdr, k)) for k in payload.model_dump(exclude_none=True)}
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(hdr, k, v)
    _log_change(db, header_id, PLChangeType.PRICE_CHANGE, updated_by, old_value=old, new_value=payload.model_dump(exclude_none=True))
    await db.flush()
    await db.refresh(hdr)
    return hdr


async def submit_for_approval(db: AsyncSession, header_id: uuid.UUID, payload: PLApprovalSubmit) -> Optional[PLHeader]:
    hdr = await get_header(db, header_id)
    if not hdr or hdr.status != PLStatus.DRAFT:
        return None
    hdr.status = PLStatus.UNDER_REVIEW
    approval = PLApproval(
        header_id=header_id,
        action=PLApprovalAction.SUBMITTED,
        submitted_by=payload.submitted_by,
        notes=payload.notes,
    )
    db.add(approval)
    _log_change(db, header_id, PLChangeType.APPROVAL, payload.submitted_by, new_value={"status": PLStatus.UNDER_REVIEW})
    await db.flush()
    await db.refresh(hdr)
    return hdr


async def review_approval(db: AsyncSession, header_id: uuid.UUID, payload: PLApprovalReview) -> Optional[PLHeader]:
    hdr = await get_header(db, header_id)
    if not hdr:
        return None
    if payload.action == PLApprovalAction.APPROVED:
        hdr.status = PLStatus.APPROVED
        hdr.approved_by = payload.reviewed_by
        hdr.approved_at = _now()
    elif payload.action == PLApprovalAction.REJECTED:
        hdr.status = PLStatus.DRAFT
    approval = PLApproval(
        header_id=header_id,
        action=payload.action,
        submitted_by=hdr.created_by or "unknown",
        reviewed_by=payload.reviewed_by,
        reviewed_at=_now(),
        notes=payload.notes,
    )
    db.add(approval)
    _log_change(db, header_id, PLChangeType.APPROVAL, payload.reviewed_by, new_value={"action": payload.action})
    await db.flush()
    await db.refresh(hdr)
    return hdr


async def activate_header(db: AsyncSession, header_id: uuid.UUID, activated_by: str = "system") -> Optional[PLHeader]:
    hdr = await get_header(db, header_id)
    if not hdr or hdr.status not in (PLStatus.APPROVED, PLStatus.DRAFT):
        return None
    hdr.status = PLStatus.ACTIVE
    _log_change(db, header_id, PLChangeType.STATUS_CHANGE, activated_by, new_value={"status": PLStatus.ACTIVE})
    await db.flush()
    await db.refresh(hdr)
    return hdr


async def archive_header(db: AsyncSession, header_id: uuid.UUID, archived_by: str = "system") -> Optional[PLHeader]:
    hdr = await get_header(db, header_id)
    if not hdr:
        return None
    hdr.status = PLStatus.ARCHIVED
    _log_change(db, header_id, PLChangeType.STATUS_CHANGE, archived_by, new_value={"status": PLStatus.ARCHIVED})
    await db.flush()
    await db.refresh(hdr)
    return hdr


# ── Lines ─────────────────────────────────────────────────────────────────────

async def add_line(db: AsyncSession, header_id: uuid.UUID, payload: PLLineCreate, added_by: str = "system") -> PLLine:
    hdr = await get_header(db, header_id)
    if hdr and hdr.status == PLStatus.ACTIVE:
        raise ValueError("Cannot add lines to an active price list. Clone and create a new version.")
    line = PLLine(header_id=header_id, **payload.model_dump())
    db.add(line)
    await db.flush()
    _log_change(db, header_id, PLChangeType.PRICE_CHANGE, added_by,
                line_id=line.id,
                new_value={"product_id": str(payload.product_id), "base_price": str(payload.base_price)})
    await db.refresh(line)
    return line


async def update_line(db: AsyncSession, line_id: uuid.UUID, payload: PLLineUpdate, updated_by: str = "system") -> Optional[PLLine]:
    line = (await db.execute(select(PLLine).where(PLLine.id == line_id))).scalar_one_or_none()
    if not line:
        return None
    old = {k: str(getattr(line, k)) for k in payload.model_dump(exclude_none=True)}
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(line, k, v)
    _log_change(db, line.header_id, PLChangeType.PRICE_CHANGE, updated_by,
                line_id=line.id, old_value=old, new_value=payload.model_dump(exclude_none=True))
    await db.flush()
    await db.refresh(line)
    return line


async def list_lines(db: AsyncSession, header_id: uuid.UUID) -> List[PLLine]:
    rows = await db.execute(
        select(PLLine).where(PLLine.header_id == header_id, PLLine.active_flag == True)
        .order_by(PLLine.created_at)
    )
    return list(rows.scalars())


# ── Tiers ─────────────────────────────────────────────────────────────────────

async def add_tier(db: AsyncSession, line_id: uuid.UUID, payload: PLTierCreate) -> PLTier:
    tier = PLTier(line_id=line_id, **payload.model_dump())
    db.add(tier)
    await db.flush()
    await db.refresh(tier)
    return tier


async def list_tiers(db: AsyncSession, line_id: uuid.UUID) -> List[PLTier]:
    rows = await db.execute(
        select(PLTier).where(PLTier.line_id == line_id, PLTier.active_flag == True)
        .order_by(PLTier.min_qty)
    )
    return list(rows.scalars())


# ── Assignments ───────────────────────────────────────────────────────────────

async def add_assignment(db: AsyncSession, header_id: uuid.UUID, payload: PLAssignmentCreate) -> PLAssignment:
    asn = PLAssignment(header_id=header_id, **payload.model_dump())
    db.add(asn)
    await db.flush()
    await db.refresh(asn)
    return asn


async def list_assignments(db: AsyncSession, header_id: uuid.UUID) -> List[PLAssignment]:
    rows = await db.execute(
        select(PLAssignment).where(PLAssignment.header_id == header_id, PLAssignment.active_flag == True)
    )
    return list(rows.scalars())


async def list_assignments_for_customer(db: AsyncSession, customer_id: uuid.UUID) -> List[PLAssignment]:
    today = _today()
    rows = await db.execute(
        select(PLAssignment).where(
            PLAssignment.customer_id == customer_id,
            PLAssignment.active_flag == True,
            PLAssignment.valid_from <= today,
            or_(PLAssignment.valid_to == None, PLAssignment.valid_to >= today),
        ).order_by(PLAssignment.priority_rank)
    )
    return list(rows.scalars())


# ── Discount Rules ────────────────────────────────────────────────────────────

async def create_discount_rule(db: AsyncSession, payload: PLDiscountRuleCreate) -> PLDiscountRule:
    rule = PLDiscountRule(**payload.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return rule


async def list_discount_rules(db: AsyncSession, active_only: bool = True) -> List[PLDiscountRule]:
    q = select(PLDiscountRule)
    if active_only:
        q = q.where(PLDiscountRule.active_flag == True)
    return list((await db.execute(q.order_by(PLDiscountRule.rule_code))).scalars())


# ── Approval Queue ────────────────────────────────────────────────────────────

async def list_pending_approvals(db: AsyncSession) -> List[PLHeader]:
    rows = await db.execute(
        select(PLHeader).where(PLHeader.status == PLStatus.UNDER_REVIEW)
        .order_by(PLHeader.created_at)
    )
    return list(rows.scalars())


async def list_approval_history(db: AsyncSession, header_id: uuid.UUID) -> List[PLApproval]:
    rows = await db.execute(
        select(PLApproval).where(PLApproval.header_id == header_id).order_by(PLApproval.created_at)
    )
    return list(rows.scalars())


# ── Price Resolution Engine ───────────────────────────────────────────────────

async def resolve_price(db: AsyncSession, req: PriceResolveRequest) -> dict:
    today = req.as_of_date or _today()
    resolution_path: List[str] = []

    def _active_headers_q():
        return and_(
            PLHeader.status == PLStatus.ACTIVE,
            PLHeader.valid_from <= today,
            or_(PLHeader.valid_to == None, PLHeader.valid_to >= today),
        )

    def _active_line_q(header_id):
        return and_(
            PLLine.header_id == header_id,
            PLLine.product_id == req.product_id,
            PLLine.active_flag == True,
            or_(PLLine.valid_from == None, PLLine.valid_from <= today),
            or_(PLLine.valid_to == None, PLLine.valid_to >= today),
        )

    async def _find_line(header: PLHeader) -> Optional[PLLine]:
        return (await db.execute(select(PLLine).where(_active_line_q(header.id)))).scalar_one_or_none()

    async def _apply_tier(line: PLLine, qty: Decimal) -> tuple[Decimal, bool]:
        tiers = list((await db.execute(
            select(PLTier).where(
                PLTier.line_id == line.id,
                PLTier.active_flag == True,
                PLTier.min_qty <= qty,
            ).order_by(PLTier.min_qty.desc()).limit(1)
        )).scalars())
        if not tiers:
            return line.base_price, False
        tier = tiers[0]
        if tier.unit_price:
            return tier.unit_price, True
        if tier.discount_pct:
            return line.base_price * (1 - tier.discount_pct / 100), True
        if tier.fixed_discount_amount:
            return max(line.base_price - tier.fixed_discount_amount, Decimal("0")), True
        return line.base_price, False

    found_price: Optional[Decimal] = None
    found_pl: Optional[PLHeader] = None
    found_line: Optional[PLLine] = None
    tier_applied = False

    # 1. Customer-specific
    if req.customer_id:
        resolution_path.append("Checking customer-specific price list")
        rows = await db.execute(
            select(PLHeader).where(
                _active_headers_q(),
                PLHeader.pl_type == PLType.CUSTOMER_SPECIFIC,
                PLHeader.customer_id == req.customer_id,
            ).order_by(PLHeader.priority_rank).limit(5)
        )
        for hdr in rows.scalars():
            line = await _find_line(hdr)
            if line:
                price, tiered = await _apply_tier(line, req.quantity)
                found_price = price
                found_pl = hdr
                found_line = line
                tier_applied = tiered
                resolution_path.append(f"Found in customer-specific list: {hdr.price_list_code}")
                break

    # 2. Assignment-based lookup (distributor / channel / region / segment)
    if not found_price:
        resolution_path.append("Checking assignments")
        asn_q = select(PLAssignment).where(
            PLAssignment.active_flag == True,
            PLAssignment.valid_from <= today,
            or_(PLAssignment.valid_to == None, PLAssignment.valid_to >= today),
        )
        filters = []
        if req.customer_id:
            filters.append(PLAssignment.customer_id == req.customer_id)
        if req.distributor_id:
            filters.append(PLAssignment.distributor_id == req.distributor_id)
        if req.channel:
            filters.append(PLAssignment.channel == req.channel)
        if req.region:
            filters.append(PLAssignment.region == req.region)
        if filters:
            asn_q = asn_q.where(or_(*filters))
            assignments = list((await db.execute(asn_q.order_by(PLAssignment.priority_rank).limit(10))).scalars())
            for asn in assignments:
                hdr = await get_header(db, asn.header_id)
                if hdr and hdr.status == PLStatus.ACTIVE:
                    line = await _find_line(hdr)
                    if line:
                        price, tiered = await _apply_tier(line, req.quantity)
                        found_price = price
                        found_pl = hdr
                        found_line = line
                        tier_applied = tiered
                        resolution_path.append(f"Found via assignment: {hdr.price_list_code}")
                        break

    # 3. Promo price
    if not found_price:
        resolution_path.append("Checking promotional price lists")
        rows = await db.execute(
            select(PLHeader).where(
                _active_headers_q(),
                PLHeader.pl_type == PLType.PROMO,
            ).order_by(PLHeader.priority_rank).limit(5)
        )
        for hdr in rows.scalars():
            line = await _find_line(hdr)
            if line:
                price, tiered = await _apply_tier(line, req.quantity)
                found_price = price
                found_pl = hdr
                found_line = line
                tier_applied = tiered
                resolution_path.append(f"Found in promo list: {hdr.price_list_code}")
                break

    # 4. Channel / region list
    if not found_price and (req.channel or req.region):
        resolution_path.append("Checking channel/region price lists")
        chan_cond = PLHeader.channel == req.channel if req.channel else None
        reg_cond = PLHeader.region == req.region if req.region else None
        cond = or_(*[c for c in [chan_cond, reg_cond] if c is not None])
        rows = await db.execute(
            select(PLHeader).where(_active_headers_q(), cond).order_by(PLHeader.priority_rank).limit(5)
        )
        for hdr in rows.scalars():
            line = await _find_line(hdr)
            if line:
                price, tiered = await _apply_tier(line, req.quantity)
                found_price = price
                found_pl = hdr
                found_line = line
                tier_applied = tiered
                resolution_path.append(f"Found in channel/region list: {hdr.price_list_code}")
                break

    # 5. Default / Standard list
    if not found_price:
        resolution_path.append("Falling back to default price list")
        rows = await db.execute(
            select(PLHeader).where(
                _active_headers_q(),
                or_(PLHeader.default_flag == True, PLHeader.pl_type == PLType.STANDARD),
            ).order_by(PLHeader.priority_rank).limit(3)
        )
        for hdr in rows.scalars():
            line = await _find_line(hdr)
            if line:
                price, tiered = await _apply_tier(line, req.quantity)
                found_price = price
                found_pl = hdr
                found_line = line
                tier_applied = tiered
                resolution_path.append(f"Found in standard list: {hdr.price_list_code}")
                break

    if not found_price:
        resolution_path.append("No price found — using zero")
        found_price = Decimal("0")

    # Margin check
    margin_pct = None
    margin_warning = False
    cost = (await db.execute(
        select(ProductCost).where(ProductCost.product_id == req.product_id)
        .order_by(ProductCost.period_ym.desc()).limit(1)
    )).scalar_one_or_none()
    if cost and found_price and float(found_price) > 0:
        cost_price = Decimal(str(cost.unit_cost))
        if cost_price > 0:
            margin_pct = (found_price - cost_price) / found_price * 100
            min_margin = Decimal(str(found_pl.minimum_margin_pct or 0)) if found_pl and found_pl.minimum_margin_pct else Decimal("20")
            if margin_pct < min_margin:
                margin_warning = True
                resolution_path.append(f"MARGIN WARNING: {float(margin_pct):.1f}% < {float(min_margin):.1f}% minimum")

    return {
        "product_id": str(req.product_id),
        "quantity": req.quantity,
        "uom": req.uom,
        "unit_price": found_line.base_price if found_line else Decimal("0"),
        "currency": req.currency or (found_line.currency if found_line else "KES"),
        "source_price_list": found_pl.price_list_name if found_pl else None,
        "source_pl_id": str(found_pl.id) if found_pl else None,
        "source_pl_type": found_pl.pl_type if found_pl else None,
        "tier_applied": tier_applied,
        "discount_applied": None,
        "effective_price": found_price,
        "minimum_price": found_line.minimum_price if found_line else None,
        "margin_warning": margin_warning,
        "margin_pct": margin_pct,
        "resolution_path": resolution_path,
    }


# ── Margin Check ──────────────────────────────────────────────────────────────

async def check_margin(db: AsyncSession, req: MarginCheckRequest) -> dict:
    cost = (await db.execute(
        select(ProductCost).where(ProductCost.product_id == req.product_id)
        .order_by(ProductCost.period_ym.desc()).limit(1)
    )).scalar_one_or_none()

    if not cost:
        return {
            "product_id": str(req.product_id),
            "proposed_price": req.proposed_price,
            "cost_price": None,
            "margin_pct": None,
            "margin_status": "NO_COST_DATA",
            "blocked": False,
            "requires_approval": False,
            "message": "No cost data available. Price accepted without margin check.",
        }

    cost_price = Decimal(str(cost.unit_cost))
    if req.proposed_price <= 0:
        return {
            "product_id": str(req.product_id),
            "proposed_price": req.proposed_price,
            "cost_price": cost_price,
            "margin_pct": Decimal("-100"),
            "margin_status": "BELOW_COST",
            "blocked": True,
            "requires_approval": True,
            "message": "Price is at or below zero. Blocked.",
        }

    margin_pct = (req.proposed_price - cost_price) / req.proposed_price * 100

    if req.proposed_price < cost_price:
        return {
            "product_id": str(req.product_id),
            "proposed_price": req.proposed_price,
            "cost_price": cost_price,
            "margin_pct": round(margin_pct, 2),
            "margin_status": "BELOW_COST",
            "blocked": True,
            "requires_approval": True,
            "message": f"Price {req.proposed_price} is below cost {cost_price}. Executive approval required.",
        }
    elif margin_pct < 10:
        return {
            "product_id": str(req.product_id),
            "proposed_price": req.proposed_price,
            "cost_price": cost_price,
            "margin_pct": round(margin_pct, 2),
            "margin_status": "BELOW_MINIMUM",
            "blocked": False,
            "requires_approval": True,
            "message": f"Margin {float(margin_pct):.1f}% is below 10% minimum. Approval required.",
        }
    elif margin_pct < 20:
        return {
            "product_id": str(req.product_id),
            "proposed_price": req.proposed_price,
            "cost_price": cost_price,
            "margin_pct": round(margin_pct, 2),
            "margin_status": "WARNING",
            "blocked": False,
            "requires_approval": False,
            "message": f"Margin {float(margin_pct):.1f}% is below 20% target. Review recommended.",
        }
    return {
        "product_id": str(req.product_id),
        "proposed_price": req.proposed_price,
        "cost_price": cost_price,
        "margin_pct": round(margin_pct, 2),
        "margin_status": "OK",
        "blocked": False,
        "requires_approval": False,
        "message": f"Margin {float(margin_pct):.1f}% is acceptable.",
    }


# ── Bulk Import ───────────────────────────────────────────────────────────────

async def bulk_import(db: AsyncSession, req: PLBulkImportRequest) -> PLBulkImportResult:
    hdr = await get_header(db, req.header_id)
    if not hdr:
        return PLBulkImportResult(imported=0, skipped=0, errors=["Price list header not found"])

    imported = 0
    skipped = 0
    errors: List[str] = []

    for i, row in enumerate(req.rows, 1):
        product = (await db.execute(
            select(Product).where(Product.sku == row.product_code)
        )).scalar_one_or_none()
        if not product:
            errors.append(f"Row {i}: product code '{row.product_code}' not found")
            skipped += 1
            continue

        existing = (await db.execute(
            select(PLLine).where(
                PLLine.header_id == req.header_id,
                PLLine.product_id == product.id,
                PLLine.uom == row.uom,
            )
        )).scalar_one_or_none()

        if existing:
            existing.base_price = row.base_price
            existing.currency = row.currency
            if row.minimum_price:
                existing.minimum_price = row.minimum_price
            if row.valid_from:
                existing.valid_from = row.valid_from
            if row.valid_to:
                existing.valid_to = row.valid_to
        else:
            line = PLLine(
                header_id=req.header_id,
                product_id=product.id,
                uom=row.uom,
                base_price=row.base_price,
                minimum_price=row.minimum_price,
                currency=row.currency,
                valid_from=row.valid_from,
                valid_to=row.valid_to,
                notes=row.notes,
            )
            db.add(line)

        imported += 1

    _log_change(db, req.header_id, PLChangeType.PRICE_CHANGE, req.imported_by,
                new_value={"bulk_import_rows": imported})
    await db.flush()
    return PLBulkImportResult(imported=imported, skipped=skipped, errors=errors)


def generate_template_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["product_code", "uom", "base_price", "currency", "minimum_price", "valid_from", "valid_to", "notes"])
    writer.writerow(["SKU-001", "KG", "150.00", "KES", "120.00", "2026-01-01", "", "Sample line"])
    return output.getvalue()


# ── Change History ────────────────────────────────────────────────────────────

async def list_change_history(db: AsyncSession, header_id: uuid.UUID) -> List[PLChangeHistory]:
    rows = await db.execute(
        select(PLChangeHistory).where(PLChangeHistory.header_id == header_id)
        .order_by(PLChangeHistory.changed_at.desc())
    )
    return list(rows.scalars())


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_dashboard(db: AsyncSession) -> dict:
    today = _today()
    active = (await db.execute(select(func.count(PLHeader.id)).where(PLHeader.status == PLStatus.ACTIVE))).scalar() or 0
    draft = (await db.execute(select(func.count(PLHeader.id)).where(PLHeader.status == PLStatus.DRAFT))).scalar() or 0
    pending = (await db.execute(select(func.count(PLHeader.id)).where(PLHeader.status == PLStatus.UNDER_REVIEW))).scalar() or 0
    expired = (await db.execute(select(func.count(PLHeader.id)).where(
        PLHeader.valid_to != None, PLHeader.valid_to < today, PLHeader.status == PLStatus.ACTIVE
    ))).scalar() or 0
    total_lines = (await db.execute(select(func.count(PLLine.id)).where(PLLine.active_flag == True))).scalar() or 0
    return {
        "active_price_lists": active,
        "draft_price_lists": draft,
        "pending_approval": pending,
        "expired_active_lists": expired,
        "total_active_lines": total_lines,
    }


async def report_expiring_soon(db: AsyncSession, days: int = 30) -> List[PLHeader]:
    from datetime import timedelta
    cutoff = _today() + timedelta(days=days)
    rows = await db.execute(
        select(PLHeader).where(
            PLHeader.valid_to != None,
            PLHeader.valid_to <= cutoff,
            PLHeader.valid_to >= _today(),
            PLHeader.status == PLStatus.ACTIVE,
        ).order_by(PLHeader.valid_to)
    )
    return list(rows.scalars())


async def report_below_margin(db: AsyncSession) -> List[dict]:
    lines = list((await db.execute(
        select(PLLine).where(PLLine.active_flag == True)
    )).scalars())
    results = []
    for line in lines:
        cost = (await db.execute(
            select(ProductCost).where(ProductCost.product_id == line.product_id)
            .order_by(ProductCost.period_ym.desc()).limit(1)
        )).scalar_one_or_none()
        if cost and line.base_price:
            cost_price = Decimal(str(cost.unit_cost))
            if cost_price > 0 and line.base_price > 0:
                margin_pct = (line.base_price - cost_price) / line.base_price * 100
                if margin_pct < 10:
                    results.append({
                        "line_id": str(line.id),
                        "header_id": str(line.header_id),
                        "product_id": str(line.product_id),
                        "base_price": float(line.base_price),
                        "cost_price": float(cost_price),
                        "margin_pct": round(float(margin_pct), 1),
                    })
    return results


async def report_version_compare(db: AsyncSession, header_id_a: uuid.UUID, header_id_b: uuid.UUID) -> dict:
    lines_a = {str(l.product_id): l for l in await list_lines(db, header_id_a)}
    lines_b = {str(l.product_id): l for l in await list_lines(db, header_id_b)}
    all_pids = set(lines_a.keys()) | set(lines_b.keys())
    diffs = []
    for pid in all_pids:
        la = lines_a.get(pid)
        lb = lines_b.get(pid)
        price_a = float(la.base_price) if la else None
        price_b = float(lb.base_price) if lb else None
        diffs.append({
            "product_id": pid,
            "price_a": price_a,
            "price_b": price_b,
            "delta": round((price_b or 0) - (price_a or 0), 4) if price_a is not None and price_b is not None else None,
            "delta_pct": round(((price_b - price_a) / price_a * 100), 2) if price_a and price_b else None,
            "status": "added" if not la else ("removed" if not lb else ("changed" if price_a != price_b else "same")),
        })
    return {"header_a": str(header_id_a), "header_b": str(header_id_b), "diff_lines": diffs}


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[PLAIRecommendation]:
    recs: List[PLAIRecommendation] = []
    today = _today()

    # Agent 1: Pricing Risk Monitor — expired active lists
    expired_hdrs = list((await db.execute(
        select(PLHeader).where(
            PLHeader.valid_to != None,
            PLHeader.valid_to < today,
            PLHeader.status == PLStatus.ACTIVE,
        )
    )).scalars())
    for hdr in expired_hdrs:
        r = PLAIRecommendation(
            header_id=hdr.id,
            agent_type=PLAIAgentType.PRICING_RISK_MONITOR,
            status=PLAIRecStatus.PENDING,
            title="Expired Price List Still Active",
            body=f"Price list '{hdr.price_list_name}' ({hdr.price_list_code}) expired on {hdr.valid_to} but is still active. Archive immediately or extend validity.",
            severity="CRITICAL",
            reference_type="PLHeader",
            reference_id=str(hdr.id),
        )
        db.add(r)
        recs.append(r)

    # Agent 1b: below-margin lines
    below_margin = await report_below_margin(db)
    seen_headers: set = set()
    for row in below_margin[:20]:
        hid = row["header_id"]
        if hid not in seen_headers:
            seen_headers.add(hid)
            r = PLAIRecommendation(
                header_id=uuid.UUID(hid),
                agent_type=PLAIAgentType.PRICING_RISK_MONITOR,
                status=PLAIRecStatus.PENDING,
                title="Price Line Below Minimum Margin",
                body=f"Price list {hid[:8]} has lines with margin below 10%. Affected product: {row['product_id'][:8]}, margin: {row['margin_pct']}%. Review and adjust.",
                severity="WARNING",
                reference_type="PLLine",
                reference_id=row["line_id"],
            )
            db.add(r)
            recs.append(r)

    # Agent 2: Price Optimization — multiple overlapping active lists of same type
    type_counts = await db.execute(
        select(PLHeader.pl_type, func.count(PLHeader.id).label("cnt"))
        .where(PLHeader.status == PLStatus.ACTIVE)
        .group_by(PLHeader.pl_type)
        .having(func.count(PLHeader.id) > 3)
    )
    for row in type_counts:
        r = PLAIRecommendation(
            agent_type=PLAIAgentType.PRICE_OPTIMIZATION,
            status=PLAIRecStatus.PENDING,
            title=f"Too Many Active {row.pl_type} Price Lists",
            body=f"There are {row.cnt} active '{row.pl_type}' price lists. Consider consolidating to simplify resolution hierarchy and reduce conflicts.",
            severity="INFO",
            reference_type="PLType",
            reference_id=row.pl_type,
        )
        db.add(r)
        recs.append(r)

    # Agent 3: Discount Abuse — price lists with no minimum_price guard
    unguarded = list((await db.execute(
        select(PLHeader).where(
            PLHeader.status == PLStatus.ACTIVE,
            PLHeader.minimum_margin_pct == None,
            PLHeader.pl_type == PLType.CUSTOMER_SPECIFIC,
        ).limit(10)
    )).scalars())
    for hdr in unguarded:
        r = PLAIRecommendation(
            header_id=hdr.id,
            agent_type=PLAIAgentType.DISCOUNT_ABUSE_DETECTOR,
            status=PLAIRecStatus.PENDING,
            title="Customer Price List Has No Margin Guard",
            body=f"Customer-specific price list '{hdr.price_list_name}' has no minimum margin set. This allows unlimited discounting. Set a minimum_margin_pct to protect profitability.",
            severity="WARNING",
            reference_type="PLHeader",
            reference_id=str(hdr.id),
        )
        db.add(r)
        recs.append(r)

    await db.flush()
    return recs


async def list_ai_recs(db: AsyncSession, header_id: Optional[uuid.UUID] = None) -> List[PLAIRecommendation]:
    q = select(PLAIRecommendation)
    if header_id:
        q = q.where(PLAIRecommendation.header_id == header_id)
    return list((await db.execute(q.order_by(PLAIRecommendation.created_at.desc()).limit(200))).scalars())


async def ack_ai_rec(db: AsyncSession, rec_id: uuid.UUID, payload: PLAIRecAck) -> Optional[PLAIRecommendation]:
    rec = (await db.execute(select(PLAIRecommendation).where(PLAIRecommendation.id == rec_id))).scalar_one_or_none()
    if not rec:
        return None
    rec.status = payload.status
    rec.actioned_by = payload.actioned_by
    rec.actioned_at = _now()
    await db.flush()
    await db.refresh(rec)
    return rec
