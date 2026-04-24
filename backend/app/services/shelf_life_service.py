"""
FEFO + Shelf-Life Control Service
Enforces FEFO picking, tracks expiry, validates issues/shipments,
manages retest workflow, and runs 3 AI agents.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shelf_life import (
    ItemShelfLifeConfig, PickingStrategyConfig, CustomerShelfLifeRule,
    LotShelfLifeProfile, RetestRequest, BulkHoldRecord, ShelfLifeAlert,
    DispositionSuggestion, FEFOAuditLog, SLAIRecommendation,
    ShelfLifeStatus, PickingStrategy, ExpiryBlockPolicy, NearExpiryPolicy,
    ShelfLifeCategory, RetestStatus, DispositionAction, DispositionStatus,
    AlertType, AlertSeverity, SLAIAgentType, SLAIRecStatus, FEFOContext,
    StrategyScope,
)
from app.models.inventory import Lot, Stock
from app.models.master import Product, Material, Warehouse
from app.schemas.shelf_life import (
    ItemShelfLifeConfigCreate, ItemShelfLifeConfigUpdate,
    PickingStrategyConfigCreate, CustomerShelfLifeRuleCreate,
    LotShelfLifeProfileUpdate, FEFORankRequest, FEFORankResponse,
    FEFOLotCandidate, FEFOValidateIssueRequest, FEFOValidateIssueResponse,
    FEFOValidateShipmentRequest, FEFOValidateShipmentResponse,
    FEFOAuditLogCreate, RetestRequestCreate, RetestResultCreate,
    BulkHoldCreate, DispositionApproveRequest, SLAIRecReviewRequest,
    ShelfLifeDashboard, ShelfLifeKPIs, FEFOComplianceReport,
    FEFOComplianceRow,
)


# ─────────────────────────────────────────────────────────────────────────────
# Item Config
# ─────────────────────────────────────────────────────────────────────────────

async def create_item_config(db: AsyncSession, data: ItemShelfLifeConfigCreate) -> ItemShelfLifeConfig:
    cfg = ItemShelfLifeConfig(**data.model_dump())
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def update_item_config(db: AsyncSession, config_id: uuid.UUID, data: ItemShelfLifeConfigUpdate) -> ItemShelfLifeConfig:
    cfg = await db.get(ItemShelfLifeConfig, config_id)
    if not cfg:
        raise ValueError("ItemShelfLifeConfig not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cfg, k, v)
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def get_item_config(db: AsyncSession, product_id: Optional[uuid.UUID] = None,
                          material_id: Optional[uuid.UUID] = None) -> Optional[ItemShelfLifeConfig]:
    q = select(ItemShelfLifeConfig)
    if product_id:
        q = q.where(ItemShelfLifeConfig.product_id == product_id)
    elif material_id:
        q = q.where(ItemShelfLifeConfig.material_id == material_id)
    else:
        return None
    result = await db.execute(q)
    return result.scalars().first()


async def list_item_configs(db: AsyncSession) -> List[ItemShelfLifeConfig]:
    result = await db.execute(select(ItemShelfLifeConfig).order_by(ItemShelfLifeConfig.created_at.desc()))
    return list(result.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Picking Strategy Config
# ─────────────────────────────────────────────────────────────────────────────

async def create_picking_strategy(db: AsyncSession, data: PickingStrategyConfigCreate,
                                   changed_by_id: Optional[uuid.UUID] = None) -> PickingStrategyConfig:
    cfg = PickingStrategyConfig(**data.model_dump(), changed_by_id=changed_by_id)
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def list_picking_strategies(db: AsyncSession) -> List[PickingStrategyConfig]:
    result = await db.execute(select(PickingStrategyConfig).order_by(PickingStrategyConfig.created_at.desc()))
    return list(result.scalars().all())


async def resolve_picking_strategy(db: AsyncSession, product_id: Optional[uuid.UUID] = None,
                                    material_id: Optional[uuid.UUID] = None,
                                    warehouse_id: Optional[uuid.UUID] = None) -> PickingStrategy:
    """Resolve picking strategy using hierarchy: item+wh > item > wh > system."""
    if product_id and warehouse_id:
        r = await db.execute(
            select(PickingStrategyConfig).where(
                PickingStrategyConfig.product_id == product_id,
                PickingStrategyConfig.warehouse_id == warehouse_id,
                PickingStrategyConfig.is_active == True,
                PickingStrategyConfig.scope == StrategyScope.item_warehouse,
            )
        )
        cfg = r.scalars().first()
        if cfg:
            return cfg.strategy

    if product_id:
        r = await db.execute(
            select(PickingStrategyConfig).where(
                PickingStrategyConfig.product_id == product_id,
                PickingStrategyConfig.is_active == True,
                PickingStrategyConfig.scope == StrategyScope.item_default,
            )
        )
        cfg = r.scalars().first()
        if cfg:
            return cfg.strategy

    if warehouse_id:
        r = await db.execute(
            select(PickingStrategyConfig).where(
                PickingStrategyConfig.warehouse_id == warehouse_id,
                PickingStrategyConfig.is_active == True,
                PickingStrategyConfig.scope == StrategyScope.warehouse_default,
            )
        )
        cfg = r.scalars().first()
        if cfg:
            return cfg.strategy

    # Fall back to item config default
    if product_id:
        ic = await get_item_config(db, product_id=product_id)
        if ic:
            return ic.picking_strategy_default
    if material_id:
        ic = await get_item_config(db, material_id=material_id)
        if ic:
            return ic.picking_strategy_default

    return PickingStrategy.fefo


# ─────────────────────────────────────────────────────────────────────────────
# Customer Shelf-Life Rules
# ─────────────────────────────────────────────────────────────────────────────

async def create_customer_rule(db: AsyncSession, data: CustomerShelfLifeRuleCreate) -> CustomerShelfLifeRule:
    rule = CustomerShelfLifeRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def list_customer_rules(db: AsyncSession) -> List[CustomerShelfLifeRule]:
    result = await db.execute(select(CustomerShelfLifeRule).order_by(CustomerShelfLifeRule.created_at.desc()))
    return list(result.scalars().all())


async def get_customer_rule(db: AsyncSession, customer_id: uuid.UUID,
                             product_id: Optional[uuid.UUID] = None) -> Optional[CustomerShelfLifeRule]:
    """Find most specific applicable rule for customer + product."""
    q = select(CustomerShelfLifeRule).where(
        CustomerShelfLifeRule.is_active == True,
        CustomerShelfLifeRule.customer_id == customer_id,
    )
    if product_id:
        q = q.where(CustomerShelfLifeRule.product_id == product_id)
    r = await db.execute(q)
    return r.scalars().first()


# ─────────────────────────────────────────────────────────────────────────────
# Lot Shelf-Life Profile CRUD & Recalculation
# ─────────────────────────────────────────────────────────────────────────────

async def get_or_create_lot_profile(db: AsyncSession, lot_id: uuid.UUID) -> LotShelfLifeProfile:
    r = await db.execute(select(LotShelfLifeProfile).where(LotShelfLifeProfile.lot_id == lot_id))
    profile = r.scalars().first()
    if not profile:
        lot = await db.get(Lot, lot_id)
        if not lot:
            raise ValueError("Lot not found")
        profile = LotShelfLifeProfile(
            lot_id=lot_id,
            manufacturing_date=lot.manufacture_date,
            expiry_date=lot.expiry_date,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def update_lot_profile(db: AsyncSession, lot_id: uuid.UUID,
                              data: LotShelfLifeProfileUpdate) -> LotShelfLifeProfile:
    profile = await get_or_create_lot_profile(db, lot_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(profile, k, v)
    await db.commit()
    await db.refresh(profile)
    return profile


async def recalculate_lot_status(db: AsyncSession, lot_id: uuid.UUID,
                                  near_expiry_days: int = 30) -> LotShelfLifeProfile:
    """Recalculate and persist shelf-life status for a single lot."""
    profile = await get_or_create_lot_profile(db, lot_id)
    today = date.today()
    now   = datetime.utcnow()

    remaining: Optional[int] = None
    if profile.expiry_date:
        remaining = (profile.expiry_date - today).days
        profile.remaining_shelf_life_days = remaining

    if profile.manufacturing_date:
        profile.age_since_production_days = (today - profile.manufacturing_date).days

    if profile.qc_release_date:
        profile.age_since_release_days = (today - profile.qc_release_date).days

    if profile.manufacturing_date and profile.expiry_date:
        total = (profile.expiry_date - profile.manufacturing_date).days
        profile.original_shelf_life_days = total
        if total > 0 and remaining is not None:
            profile.pct_remaining = Decimal(str(round(remaining / total * 100, 2)))

    # Determine status
    old_status = profile.shelf_life_status
    if profile.expiry_date is None:
        profile.shelf_life_status = ShelfLifeStatus.not_applicable
    elif remaining is not None and remaining < 0:
        profile.expired_flag = True
        profile.near_expiry_flag = False
        profile.blocked_for_issue_flag = True
        profile.blocked_for_shipment_flag = True
        profile.blocked_for_consumption_flag = True
        profile.shelf_life_status = ShelfLifeStatus.expired
    elif remaining is not None and remaining <= near_expiry_days:
        profile.near_expiry_flag = True
        profile.expired_flag = False
        profile.shelf_life_status = ShelfLifeStatus.near_expiry
    elif profile.retest_date and profile.retest_date <= today and profile.shelf_life_status not in (
        ShelfLifeStatus.retested_released,
    ):
        profile.shelf_life_status = ShelfLifeStatus.pending_retest
    elif profile.blocked_for_issue_flag:
        profile.shelf_life_status = ShelfLifeStatus.blocked
    else:
        profile.near_expiry_flag = False
        profile.expired_flag = False
        if profile.shelf_life_status not in (ShelfLifeStatus.qc_hold, ShelfLifeStatus.quarantine,
                                              ShelfLifeStatus.retested_released, ShelfLifeStatus.customer_restricted):
            profile.shelf_life_status = ShelfLifeStatus.active

    if profile.shelf_life_status != old_status:
        profile.status_changed_at = now

    profile.last_recalc_at = now
    await db.commit()
    await db.refresh(profile)
    return profile


async def batch_recalculate_statuses(db: AsyncSession) -> int:
    """Recalculate shelf-life status for all lots with profiles. Returns count updated."""
    r = await db.execute(select(LotShelfLifeProfile.lot_id))
    lot_ids = [row[0] for row in r.all()]
    count = 0
    for lid in lot_ids:
        await recalculate_lot_status(db, lid)
        count += 1
    return count


async def list_near_expiry(db: AsyncSession, days: int = 30,
                            warehouse_id: Optional[uuid.UUID] = None) -> List[LotShelfLifeProfile]:
    q = select(LotShelfLifeProfile).where(
        LotShelfLifeProfile.remaining_shelf_life_days >= 0,
        LotShelfLifeProfile.remaining_shelf_life_days <= days,
        LotShelfLifeProfile.expired_flag == False,
    ).order_by(asc(LotShelfLifeProfile.remaining_shelf_life_days))
    result = await db.execute(q)
    return list(result.scalars().all())


async def list_expired(db: AsyncSession, warehouse_id: Optional[uuid.UUID] = None) -> List[LotShelfLifeProfile]:
    q = select(LotShelfLifeProfile).where(
        LotShelfLifeProfile.expired_flag == True
    ).order_by(asc(LotShelfLifeProfile.expiry_date))
    result = await db.execute(q)
    return list(result.scalars().all())


async def list_all_lot_profiles(db: AsyncSession, status: Optional[ShelfLifeStatus] = None,
                                 limit: int = 200, offset: int = 0) -> List[LotShelfLifeProfile]:
    q = select(LotShelfLifeProfile).order_by(asc(LotShelfLifeProfile.remaining_shelf_life_days))
    if status:
        q = q.where(LotShelfLifeProfile.shelf_life_status == status)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# FEFO Ranking Engine
# ─────────────────────────────────────────────────────────────────────────────

async def rank_lots_fefo(db: AsyncSession, req: FEFORankRequest) -> FEFORankResponse:
    """Core FEFO ranking engine: returns ordered eligible lot candidates."""
    policy_violations: List[str] = []

    # Resolve picking strategy
    strategy = await resolve_picking_strategy(
        db,
        product_id=req.product_id,
        material_id=req.material_id,
        warehouse_id=req.warehouse_id,
    )

    # Get item config for policy checks
    item_cfg = None
    if req.product_id:
        item_cfg = await get_item_config(db, product_id=req.product_id)
    elif req.material_id:
        item_cfg = await get_item_config(db, material_id=req.material_id)

    near_expiry_days = item_cfg.near_expiry_threshold_days if item_cfg else 30

    # Get all stocks for this item in this warehouse
    q = select(Stock).where(Stock.quantity_available > 0)
    if req.product_id:
        q = q.where(Stock.product_id == req.product_id)
    if req.material_id:
        q = q.where(Stock.material_id == req.material_id)
    if req.warehouse_id:
        q = q.where(Stock.warehouse_id == req.warehouse_id)
    q = q.where(Stock.is_blocked == False)

    stocks_result = await db.execute(q)
    stocks = list(stocks_result.scalars().all())

    candidates: List[FEFOLotCandidate] = []
    excluded: List[FEFOLotCandidate] = []

    today = date.today()

    for stock in stocks:
        if not stock.lot_id:
            continue
        if req.exclude_lot_ids and stock.lot_id in req.exclude_lot_ids:
            continue

        lot = await db.get(Lot, stock.lot_id)
        if not lot:
            continue

        profile_r = await db.execute(
            select(LotShelfLifeProfile).where(LotShelfLifeProfile.lot_id == stock.lot_id)
        )
        profile = profile_r.scalars().first()

        remaining = None
        pct = None
        expiry = lot.expiry_date
        if expiry:
            remaining = (expiry - today).days
            if profile and profile.original_shelf_life_days:
                pct = Decimal(str(round(remaining / profile.original_shelf_life_days * 100, 2)))

        exclusion_reason: Optional[str] = None

        # Block expired
        if remaining is not None and remaining < 0:
            exclusion_reason = f"Expired {abs(remaining)} days ago"

        # Block QC hold / quarantine
        if profile and profile.shelf_life_status in (ShelfLifeStatus.qc_hold, ShelfLifeStatus.quarantine,
                                                      ShelfLifeStatus.blocked):
            exclusion_reason = f"Lot blocked: {profile.shelf_life_status.value}"

        # Block if explicitly blocked for issue/consumption
        if profile and (profile.blocked_for_issue_flag or profile.blocked_for_consumption_flag):
            exclusion_reason = exclusion_reason or "Blocked for issue/consumption"

        # Minimum remaining shelf life check
        if item_cfg and item_cfg.min_remaining_days_issue and remaining is not None:
            if remaining < item_cfg.min_remaining_days_issue:
                exclusion_reason = exclusion_reason or f"Below min remaining ({remaining}d < {item_cfg.min_remaining_days_issue}d)"

        # Customer minimum remaining shelf life
        if req.customer_id and req.product_id and remaining is not None:
            cust_rule = await get_customer_rule(db, req.customer_id, req.product_id)
            if cust_rule and cust_rule.min_remaining_days and remaining < cust_rule.min_remaining_days:
                exclusion_reason = exclusion_reason or (
                    f"Customer requires {cust_rule.min_remaining_days}d remaining, only {remaining}d left"
                )

        shelf_status = profile.shelf_life_status if profile else ShelfLifeStatus.active

        c = FEFOLotCandidate(
            lot_id=stock.lot_id,
            lot_number=lot.lot_number,
            expiry_date=expiry,
            remaining_days=remaining,
            pct_remaining=pct,
            quantity_available=stock.quantity_available,
            shelf_life_status=shelf_status,
            rank=0,
            is_recommended=exclusion_reason is None,
            exclusion_reason=exclusion_reason,
        )

        if exclusion_reason:
            excluded.append(c)
        else:
            candidates.append(c)

    # Sort eligible candidates by strategy
    if strategy in (PickingStrategy.fefo, PickingStrategy.hybrid):
        candidates.sort(key=lambda c: (c.expiry_date or date.max))
    elif strategy == PickingStrategy.fifo:
        # Sort by lot creation date — approximate by lot_id UUID or use manufacturing date
        candidates.sort(key=lambda c: c.expiry_date or date.max)
    elif strategy == PickingStrategy.lifo:
        candidates.sort(key=lambda c: c.expiry_date or date.min, reverse=True)

    # Assign ranks
    for i, c in enumerate(candidates):
        c.rank = i + 1
    for i, c in enumerate(excluded):
        c.rank = len(candidates) + i + 1

    recommended_lot = candidates[0].lot_id if candidates else None
    all_candidates = candidates + excluded

    return FEFORankResponse(
        candidates=all_candidates,
        recommended_lot_id=recommended_lot,
        strategy_used=strategy,
        policy_violations=policy_violations,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Validation Engine
# ─────────────────────────────────────────────────────────────────────────────

async def validate_issue(db: AsyncSession, req: FEFOValidateIssueRequest) -> FEFOValidateIssueResponse:
    warnings: List[str] = []
    errors:   List[str] = []
    requires_approval = False

    lot = await db.get(Lot, req.lot_id)
    if not lot:
        return FEFOValidateIssueResponse(
            allowed=False, requires_approval=False,
            warnings=[], errors=["Lot not found"], lot_status=None, remaining_days=None,
        )

    profile_r = await db.execute(select(LotShelfLifeProfile).where(LotShelfLifeProfile.lot_id == req.lot_id))
    profile = profile_r.scalars().first()

    remaining = None
    if lot.expiry_date:
        remaining = (lot.expiry_date - date.today()).days

    # Load item config
    item_cfg = None
    if req.product_id:
        item_cfg = await get_item_config(db, product_id=req.product_id)
    elif req.material_id:
        item_cfg = await get_item_config(db, material_id=req.material_id)

    # Expired check
    if remaining is not None and remaining < 0:
        block_policy = item_cfg.expiry_block_policy if item_cfg else ExpiryBlockPolicy.block
        if block_policy == ExpiryBlockPolicy.block:
            errors.append(f"Lot expired {abs(remaining)} days ago. Issue blocked by policy.")
        elif block_policy == ExpiryBlockPolicy.warn:
            warnings.append(f"Lot expired {abs(remaining)} days ago. Proceed with caution.")
        elif block_policy == ExpiryBlockPolicy.allow_with_approval:
            warnings.append(f"Lot expired {abs(remaining)} days ago. Approval required.")
            requires_approval = True

    # QC/quarantine block
    if profile and profile.shelf_life_status in (ShelfLifeStatus.qc_hold, ShelfLifeStatus.quarantine):
        errors.append(f"Lot is on {profile.shelf_life_status.value}. Issue blocked.")

    if profile and profile.blocked_for_issue_flag and (remaining is None or remaining >= 0):
        errors.append(f"Lot is explicitly blocked for issue. Reason: {profile.hold_reason or 'no reason given'}")

    # Near expiry check
    near_expiry_days = item_cfg.near_expiry_threshold_days if item_cfg else 30
    issue_policy = item_cfg.near_expiry_issue_policy if item_cfg else NearExpiryPolicy.warn
    if remaining is not None and 0 <= remaining <= near_expiry_days:
        if issue_policy == NearExpiryPolicy.warn:
            warnings.append(f"Lot expires in {remaining} days (near-expiry threshold: {near_expiry_days}d).")
        elif issue_policy == NearExpiryPolicy.require_approval:
            warnings.append(f"Near-expiry lot ({remaining}d remaining). Supervisor approval required.")
            requires_approval = True
        elif issue_policy == NearExpiryPolicy.block_external:
            warnings.append(f"Near-expiry lot ({remaining}d remaining). Only internal use allowed.")

    # Minimum remaining shelf life check
    if item_cfg and item_cfg.min_remaining_days_issue and remaining is not None:
        if remaining < item_cfg.min_remaining_days_issue and remaining >= 0:
            errors.append(
                f"Remaining shelf life ({remaining}d) below minimum required for issue ({item_cfg.min_remaining_days_issue}d)."
            )

    status = profile.shelf_life_status if profile else ShelfLifeStatus.active
    allowed = len(errors) == 0

    return FEFOValidateIssueResponse(
        allowed=allowed,
        requires_approval=requires_approval,
        warnings=warnings,
        errors=errors,
        lot_status=status,
        remaining_days=remaining,
    )


async def validate_shipment(db: AsyncSession, req: FEFOValidateShipmentRequest) -> FEFOValidateShipmentResponse:
    warnings: List[str] = []
    errors:   List[str] = []
    requires_approval = False

    lot = await db.get(Lot, req.lot_id)
    if not lot:
        return FEFOValidateShipmentResponse(
            allowed=False, requires_approval=False,
            warnings=[], errors=["Lot not found"],
            remaining_days=None, pct_remaining=None, customer_min_days=None,
        )

    profile_r = await db.execute(select(LotShelfLifeProfile).where(LotShelfLifeProfile.lot_id == req.lot_id))
    profile = profile_r.scalars().first()

    remaining = None
    pct = None
    if lot.expiry_date:
        remaining = (lot.expiry_date - date.today()).days
        if profile and profile.original_shelf_life_days:
            pct = Decimal(str(round(remaining / profile.original_shelf_life_days * 100, 2)))

    item_cfg = None
    if req.product_id:
        item_cfg = await get_item_config(db, product_id=req.product_id)

    # Expired block
    if remaining is not None and remaining < 0:
        errors.append(f"Lot expired {abs(remaining)} days ago. Shipment of expired FG is blocked.")

    # Blocked for shipment
    if profile and profile.blocked_for_shipment_flag:
        errors.append(f"Lot is explicitly blocked for shipment. Reason: {profile.hold_reason or 'no reason'}")

    # Min remaining for shipment
    if item_cfg and item_cfg.min_remaining_days_ship and remaining is not None and remaining >= 0:
        if remaining < item_cfg.min_remaining_days_ship:
            errors.append(
                f"Remaining shelf life ({remaining}d) below minimum for shipment ({item_cfg.min_remaining_days_ship}d)."
            )

    # Customer-specific rule
    customer_min = None
    if req.customer_id and req.product_id and remaining is not None:
        cust_rule = await get_customer_rule(db, req.customer_id, req.product_id)
        if cust_rule:
            customer_min = cust_rule.min_remaining_days
            if customer_min and remaining < customer_min:
                if cust_rule.block_policy == ExpiryBlockPolicy.block:
                    errors.append(
                        f"Customer requires {customer_min}d remaining. Only {remaining}d left. Shipment blocked."
                    )
                elif cust_rule.block_policy == ExpiryBlockPolicy.warn:
                    warnings.append(
                        f"Customer prefers {customer_min}d remaining. Only {remaining}d left."
                    )
                elif cust_rule.block_policy == ExpiryBlockPolicy.allow_with_approval:
                    warnings.append(
                        f"Customer minimum not met ({remaining}d < {customer_min}d). Approval required."
                    )
                    requires_approval = True

    allowed = len(errors) == 0
    return FEFOValidateShipmentResponse(
        allowed=allowed,
        requires_approval=requires_approval,
        warnings=warnings,
        errors=errors,
        remaining_days=remaining,
        pct_remaining=pct,
        customer_min_days=customer_min,
    )


# ─────────────────────────────────────────────────────────────────────────────
# FEFO Audit Log
# ─────────────────────────────────────────────────────────────────────────────

async def log_fefo_audit(db: AsyncSession, data: FEFOAuditLogCreate) -> FEFOAuditLog:
    entry = FEFOAuditLog(**data.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_fefo_audit(db: AsyncSession, warehouse_id: Optional[uuid.UUID] = None,
                           context: Optional[FEFOContext] = None,
                           limit: int = 200) -> List[FEFOAuditLog]:
    q = select(FEFOAuditLog).order_by(desc(FEFOAuditLog.created_at)).limit(limit)
    if warehouse_id:
        q = q.where(FEFOAuditLog.warehouse_id == warehouse_id)
    if context:
        q = q.where(FEFOAuditLog.context == context)
    r = await db.execute(q)
    return list(r.scalars().all())


async def get_fefo_compliance_report(db: AsyncSession, date_from: Optional[date] = None,
                                      date_to: Optional[date] = None) -> FEFOComplianceReport:
    q = select(
        FEFOAuditLog.warehouse_id,
        func.count(FEFOAuditLog.id).label("total"),
        func.sum(func.cast(FEFOAuditLog.is_fefo_compliant, db.bind.dialect.name == "postgresql" and "integer" or "integer")).label("compliant"),
    ).group_by(FEFOAuditLog.warehouse_id)

    if date_from:
        q = q.where(FEFOAuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.where(FEFOAuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))

    result = await db.execute(q)
    rows_raw = result.all()

    rows: List[FEFOComplianceRow] = []
    total_picks = 0
    total_compliant = 0

    for row in rows_raw:
        total = row.total or 0
        compliant = int(row.compliant or 0)
        non_compliant = total - compliant
        pct = Decimal(str(round(compliant / total * 100, 1))) if total > 0 else Decimal("0")
        rows.append(FEFOComplianceRow(
            warehouse_id=row.warehouse_id,
            warehouse_name=None,
            total_picks=total,
            compliant_picks=compliant,
            non_compliant_picks=non_compliant,
            compliance_pct=pct,
            override_count=non_compliant,
        ))
        total_picks += total
        total_compliant += compliant

    overall_pct = Decimal(str(round(total_compliant / total_picks * 100, 1))) if total_picks > 0 else Decimal("100")

    return FEFOComplianceReport(
        period_from=date_from,
        period_to=date_to,
        overall_compliance_pct=overall_pct,
        rows=rows,
        top_overriders=[],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Retest
# ─────────────────────────────────────────────────────────────────────────────

def _gen_retest_number() -> str:
    import random
    return f"RTT-{date.today().strftime('%Y%m%d')}-{random.randint(1000,9999)}"


async def create_retest_request(db: AsyncSession, data: RetestRequestCreate) -> RetestRequest:
    req = RetestRequest(
        lot_id=data.lot_id,
        request_number=_gen_retest_number(),
        status=RetestStatus.requested,
        reason=data.reason,
        requested_by_id=data.requested_by_id,
        requested_at=datetime.utcnow(),
        assigned_to_id=data.assigned_to_id,
        scheduled_date=data.scheduled_date,
    )
    db.add(req)

    # Update lot profile status to pending_retest
    profile = await get_or_create_lot_profile(db, data.lot_id)
    profile.shelf_life_status = ShelfLifeStatus.pending_retest
    profile.status_changed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(req)
    return req


async def record_retest_result(db: AsyncSession, request_id: uuid.UUID,
                                data: RetestResultCreate) -> RetestRequest:
    req = await db.get(RetestRequest, request_id)
    if not req:
        raise ValueError("RetestRequest not found")

    req.result_passed    = data.result_passed
    req.result_notes     = data.result_notes
    req.result_by_id     = data.result_by_id
    req.result_at        = datetime.utcnow()
    req.new_expiry_date  = data.new_expiry_date
    req.new_retest_date  = data.new_retest_date
    req.new_release_date = data.new_release_date
    req.status           = RetestStatus.passed if data.result_passed else RetestStatus.failed

    # Update lot profile
    profile = await get_or_create_lot_profile(db, req.lot_id)
    if data.result_passed:
        profile.shelf_life_status       = ShelfLifeStatus.retested_released
        profile.blocked_for_issue_flag  = False
        profile.blocked_for_consumption_flag = False
        if data.new_expiry_date:
            profile.expiry_date = data.new_expiry_date
        if data.new_retest_date:
            profile.retest_date = data.new_retest_date
        if data.new_release_date:
            profile.qc_release_date = data.new_release_date
    else:
        profile.shelf_life_status       = ShelfLifeStatus.blocked
        profile.blocked_for_issue_flag  = True
        profile.blocked_for_shipment_flag = True
        profile.blocked_for_consumption_flag = True
        profile.hold_reason = "Retest failed"

    profile.status_changed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(req)
    return req


async def list_retest_queue(db: AsyncSession) -> List[RetestRequest]:
    r = await db.execute(
        select(RetestRequest)
        .where(RetestRequest.status.in_([RetestStatus.pending, RetestStatus.requested, RetestStatus.in_progress]))
        .order_by(asc(RetestRequest.scheduled_date))
    )
    return list(r.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Bulk Hold
# ─────────────────────────────────────────────────────────────────────────────

async def create_bulk_hold(db: AsyncSession, data: BulkHoldCreate) -> BulkHoldRecord:
    expiry_time = data.creation_time + timedelta(hours=float(data.max_hold_hours))
    record = BulkHoldRecord(
        lot_id=data.lot_id,
        material_id=data.material_id,
        warehouse_id=data.warehouse_id,
        location_ref=data.location_ref,
        creation_time=data.creation_time,
        max_hold_hours=data.max_hold_hours,
        expiry_time=expiry_time,
        notes=data.notes,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def refresh_bulk_hold_statuses(db: AsyncSession) -> int:
    """Update is_expired and is_near_limit for all bulk hold records."""
    now = datetime.utcnow()
    r = await db.execute(select(BulkHoldRecord).where(BulkHoldRecord.is_expired == False))
    records = list(r.scalars().all())
    count = 0
    for rec in records:
        hours_used = (now - rec.creation_time).total_seconds() / 3600
        rec.hours_used    = Decimal(str(round(hours_used, 2)))
        pct = hours_used / float(rec.max_hold_hours) * 100 if rec.max_hold_hours else 0
        rec.pct_hold_used = Decimal(str(round(pct, 2)))

        if now >= rec.expiry_time:
            rec.is_expired = True
            rec.is_blocked = True
            rec.is_near_limit = False
        elif pct >= 80:
            rec.is_near_limit = True
        count += 1
    await db.commit()
    return count


async def list_bulk_holds(db: AsyncSession, active_only: bool = True) -> List[BulkHoldRecord]:
    q = select(BulkHoldRecord).order_by(asc(BulkHoldRecord.expiry_time))
    if active_only:
        q = q.where(BulkHoldRecord.is_expired == False)
    r = await db.execute(q)
    return list(r.scalars().all())


# ─────────────────────────────────────────────────────────────────────────────
# Alerts
# ─────────────────────────────────────────────────────────────────────────────

async def generate_alerts(db: AsyncSession) -> int:
    """Generate/refresh shelf-life alerts. Returns count of new alerts created."""
    today = date.today()
    count = 0

    # Near expiry
    near_profiles = await list_near_expiry(db, days=30)
    for p in near_profiles:
        existing = await db.execute(
            select(ShelfLifeAlert).where(
                ShelfLifeAlert.lot_id == p.lot_id,
                ShelfLifeAlert.alert_type == AlertType.near_expiry,
                ShelfLifeAlert.is_resolved == False,
            )
        )
        if not existing.scalars().first():
            alert = ShelfLifeAlert(
                alert_type=AlertType.near_expiry,
                severity=AlertSeverity.warning if (p.remaining_shelf_life_days or 0) > 7 else AlertSeverity.critical,
                lot_id=p.lot_id,
                title=f"Near-Expiry Lot: {p.remaining_shelf_life_days}d remaining",
                message=f"Lot expires in {p.remaining_shelf_life_days} days. Prioritize consumption or shipment.",
                days_remaining=p.remaining_shelf_life_days,
            )
            db.add(alert)
            count += 1

    # Expired
    expired = await list_expired(db)
    for p in expired:
        existing = await db.execute(
            select(ShelfLifeAlert).where(
                ShelfLifeAlert.lot_id == p.lot_id,
                ShelfLifeAlert.alert_type == AlertType.expired,
                ShelfLifeAlert.is_resolved == False,
            )
        )
        if not existing.scalars().first():
            alert = ShelfLifeAlert(
                alert_type=AlertType.expired,
                severity=AlertSeverity.critical,
                lot_id=p.lot_id,
                title="Expired Lot in Active Stock",
                message=f"Lot expired {abs(p.remaining_shelf_life_days or 0)} days ago. Immediate disposition required.",
                days_remaining=p.remaining_shelf_life_days,
            )
            db.add(alert)
            count += 1

    # Bulk hold at risk
    holds = await list_bulk_holds(db, active_only=True)
    for h in holds:
        if h.is_near_limit or h.is_expired:
            existing = await db.execute(
                select(ShelfLifeAlert).where(
                    ShelfLifeAlert.alert_type == AlertType.bulk_age_limit,
                    ShelfLifeAlert.is_resolved == False,
                    ShelfLifeAlert.lot_id == h.lot_id,
                )
            )
            if not existing.scalars().first():
                sev = AlertSeverity.critical if h.is_expired else AlertSeverity.warning
                alert = ShelfLifeAlert(
                    alert_type=AlertType.bulk_age_limit,
                    severity=sev,
                    lot_id=h.lot_id,
                    material_id=h.material_id,
                    warehouse_id=h.warehouse_id,
                    title="Bulk/Intermediate Age Limit Approaching",
                    message=f"Hold record is at {h.pct_hold_used}% of max hold time ({h.max_hold_hours}h).",
                )
                db.add(alert)
                count += 1

    # Retest overdue
    overdue_r = await db.execute(
        select(LotShelfLifeProfile).where(
            LotShelfLifeProfile.retest_date <= today,
            LotShelfLifeProfile.shelf_life_status.in_([
                ShelfLifeStatus.active, ShelfLifeStatus.near_expiry,
            ])
        )
    )
    for p in overdue_r.scalars().all():
        existing = await db.execute(
            select(ShelfLifeAlert).where(
                ShelfLifeAlert.lot_id == p.lot_id,
                ShelfLifeAlert.alert_type == AlertType.unretested_lot,
                ShelfLifeAlert.is_resolved == False,
            )
        )
        if not existing.scalars().first():
            alert = ShelfLifeAlert(
                alert_type=AlertType.unretested_lot,
                severity=AlertSeverity.warning,
                lot_id=p.lot_id,
                title="Retest Date Passed – Lot Pending Retest",
                message="Lot retest date has passed without a retest request being raised.",
            )
            db.add(alert)
            count += 1

    await db.commit()
    return count


async def list_alerts(db: AsyncSession, resolved: bool = False,
                       severity: Optional[AlertSeverity] = None,
                       limit: int = 100) -> List[ShelfLifeAlert]:
    q = select(ShelfLifeAlert).where(ShelfLifeAlert.is_resolved == resolved).order_by(
        desc(ShelfLifeAlert.created_at)
    ).limit(limit)
    if severity:
        q = q.where(ShelfLifeAlert.severity == severity)
    r = await db.execute(q)
    return list(r.scalars().all())


async def resolve_alert(db: AsyncSession, alert_id: uuid.UUID) -> ShelfLifeAlert:
    alert = await db.get(ShelfLifeAlert, alert_id)
    if not alert:
        raise ValueError("Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(alert)
    return alert


# ─────────────────────────────────────────────────────────────────────────────
# Disposition Suggestions
# ─────────────────────────────────────────────────────────────────────────────

async def generate_disposition_suggestions(db: AsyncSession) -> int:
    """Auto-generate disposition suggestions for at-risk lots."""
    count = 0
    today = date.today()

    # Expired lots → scrap/rework/quarantine
    expired = await list_expired(db)
    for p in expired:
        existing = await db.execute(
            select(DispositionSuggestion).where(
                DispositionSuggestion.lot_id == p.lot_id,
                DispositionSuggestion.status == DispositionStatus.suggested,
            )
        )
        if not existing.scalars().first():
            d = DispositionSuggestion(
                lot_id=p.lot_id,
                action=DispositionAction.scrap,
                status=DispositionStatus.suggested,
                reason=f"Lot expired {abs(p.remaining_shelf_life_days or 0)} days ago.",
                urgency_score=100,
                days_until_expiry=p.remaining_shelf_life_days,
            )
            db.add(d)
            count += 1

    # Near-expiry with no demand → use urgently / clearance
    near = await list_near_expiry(db, days=14)
    for p in near:
        existing = await db.execute(
            select(DispositionSuggestion).where(
                DispositionSuggestion.lot_id == p.lot_id,
                DispositionSuggestion.status == DispositionStatus.suggested,
            )
        )
        if not existing.scalars().first():
            d = DispositionSuggestion(
                lot_id=p.lot_id,
                action=DispositionAction.use_urgently,
                status=DispositionStatus.suggested,
                reason=f"Lot expires in {p.remaining_shelf_life_days} days. Urgent production consumption recommended.",
                urgency_score=90,
                days_until_expiry=p.remaining_shelf_life_days,
            )
            db.add(d)
            count += 1

    # Pending retest overdue → retest action
    pending_r = await db.execute(
        select(LotShelfLifeProfile).where(
            LotShelfLifeProfile.shelf_life_status == ShelfLifeStatus.pending_retest
        )
    )
    for p in pending_r.scalars().all():
        existing = await db.execute(
            select(DispositionSuggestion).where(
                DispositionSuggestion.lot_id == p.lot_id,
                DispositionSuggestion.status == DispositionStatus.suggested,
                DispositionSuggestion.action == DispositionAction.retest,
            )
        )
        if not existing.scalars().first():
            d = DispositionSuggestion(
                lot_id=p.lot_id,
                action=DispositionAction.retest,
                status=DispositionStatus.suggested,
                reason="Lot is in pending_retest status with no active retest request.",
                urgency_score=70,
                days_until_expiry=p.remaining_shelf_life_days,
            )
            db.add(d)
            count += 1

    await db.commit()
    return count


async def list_disposition_suggestions(db: AsyncSession,
                                        status: Optional[DispositionStatus] = None) -> List[DispositionSuggestion]:
    q = select(DispositionSuggestion).order_by(desc(DispositionSuggestion.urgency_score))
    if status:
        q = q.where(DispositionSuggestion.status == status)
    r = await db.execute(q)
    return list(r.scalars().all())


async def approve_disposition(db: AsyncSession, suggestion_id: uuid.UUID,
                               data: DispositionApproveRequest) -> DispositionSuggestion:
    sugg = await db.get(DispositionSuggestion, suggestion_id)
    if not sugg:
        raise ValueError("DispositionSuggestion not found")
    sugg.status          = DispositionStatus.approved
    sugg.approved_by_id  = data.approved_by_id
    sugg.approved_at     = datetime.utcnow()
    sugg.execution_notes = data.execution_notes
    await db.commit()
    await db.refresh(sugg)
    return sugg


# ─────────────────────────────────────────────────────────────────────────────
# AI Agents
# ─────────────────────────────────────────────────────────────────────────────

async def _run_expiry_risk_predictor(db: AsyncSession) -> List[SLAIRecommendation]:
    """Agent 1: Predict lots likely to expire before use."""
    recs: List[SLAIRecommendation] = []

    # Lots near expiry (< 30 days) in significant quantities
    r = await db.execute(
        select(LotShelfLifeProfile).where(
            LotShelfLifeProfile.remaining_shelf_life_days <= 30,
            LotShelfLifeProfile.remaining_shelf_life_days >= 0,
            LotShelfLifeProfile.expired_flag == False,
        ).order_by(asc(LotShelfLifeProfile.remaining_shelf_life_days)).limit(10)
    )
    profiles = list(r.scalars().all())

    for p in profiles:
        rec = SLAIRecommendation(
            agent_type=SLAIAgentType.expiry_risk_predictor,
            status=SLAIRecStatus.pending,
            lot_id=p.lot_id,
            title=f"High Expiry Risk: {p.remaining_shelf_life_days}d remaining",
            explanation=(
                f"Lot has only {p.remaining_shelf_life_days} days of shelf life remaining. "
                f"Current status: {p.shelf_life_status.value}. "
                f"Shelf life is {p.pct_remaining or 0}% of original."
            ),
            recommendation=(
                "Prioritize this lot for immediate production consumption or shipment. "
                "If demand is insufficient, initiate disposition process to avoid write-off."
            ),
            confidence_score=Decimal("0.85"),
        )
        recs.append(rec)

    return recs


async def _run_allocation_optimizer(db: AsyncSession) -> List[SLAIRecommendation]:
    """Agent 2: Suggest best lot allocation across orders and channels."""
    recs: List[SLAIRecommendation] = []

    # Identify near-expiry lots that could be routed to domestic vs export
    r = await db.execute(
        select(LotShelfLifeProfile).where(
            LotShelfLifeProfile.remaining_shelf_life_days.between(14, 45),
            LotShelfLifeProfile.expired_flag == False,
        ).order_by(asc(LotShelfLifeProfile.remaining_shelf_life_days)).limit(5)
    )
    profiles = list(r.scalars().all())

    for p in profiles:
        rec = SLAIRecommendation(
            agent_type=SLAIAgentType.allocation_optimizer,
            status=SLAIRecStatus.pending,
            lot_id=p.lot_id,
            title=f"Allocation Optimization: Lot with {p.remaining_shelf_life_days}d remaining",
            explanation=(
                f"Lot shelf life ({p.remaining_shelf_life_days}d remaining) may not meet export customer "
                f"minimum shelf-life requirements. Domestic channels typically accept shorter shelf life."
            ),
            recommendation=(
                "Route this lot to domestic customers or internal production. "
                "Reserve lots with more remaining shelf life for export orders requiring 70%+ shelf life."
            ),
            confidence_score=Decimal("0.78"),
        )
        recs.append(rec)

    return recs


async def _run_compliance_monitor(db: AsyncSession) -> List[SLAIRecommendation]:
    """Agent 3: Detect FEFO override patterns and policy conflicts."""
    recs: List[SLAIRecommendation] = []

    # Check for repeated non-FEFO picks in the last 7 days
    cutoff = datetime.utcnow() - timedelta(days=7)
    r = await db.execute(
        select(
            FEFOAuditLog.warehouse_id,
            func.count(FEFOAuditLog.id).label("total"),
        ).where(
            FEFOAuditLog.is_fefo_compliant == False,
            FEFOAuditLog.created_at >= cutoff,
        ).group_by(FEFOAuditLog.warehouse_id).having(func.count(FEFOAuditLog.id) >= 3)
    )
    rows = r.all()

    for row in rows:
        rec = SLAIRecommendation(
            agent_type=SLAIAgentType.compliance_monitor,
            status=SLAIRecStatus.pending,
            warehouse_id=row.warehouse_id,
            title=f"FEFO Compliance Alert: {row.total} non-FEFO picks in 7 days",
            explanation=(
                f"Warehouse has {row.total} non-FEFO picks in the last 7 days. "
                f"This pattern may indicate training gaps, system bypass, or operational friction with FEFO enforcement."
            ),
            recommendation=(
                "Review non-FEFO override reasons for this warehouse. "
                "Consider targeted training or investigate if FEFO strategy config is causing operational issues."
            ),
            confidence_score=Decimal("0.90"),
        )
        recs.append(rec)

    return recs


async def run_all_ai_agents(db: AsyncSession) -> List[SLAIRecommendation]:
    """Run all 3 AI agents and persist new recommendations."""
    all_recs: List[SLAIRecommendation] = []

    for runner in [_run_expiry_risk_predictor, _run_allocation_optimizer, _run_compliance_monitor]:
        recs = await runner(db)
        for rec in recs:
            db.add(rec)
            all_recs.append(rec)

    await db.commit()
    return all_recs


async def list_ai_recommendations(db: AsyncSession, status: Optional[SLAIRecStatus] = None,
                                   agent_type: Optional[SLAIAgentType] = None,
                                   limit: int = 50) -> List[SLAIRecommendation]:
    q = select(SLAIRecommendation).order_by(desc(SLAIRecommendation.created_at)).limit(limit)
    if status:
        q = q.where(SLAIRecommendation.status == status)
    if agent_type:
        q = q.where(SLAIRecommendation.agent_type == agent_type)
    r = await db.execute(q)
    return list(r.scalars().all())


async def review_ai_recommendation(db: AsyncSession, rec_id: uuid.UUID,
                                    data: SLAIRecReviewRequest) -> SLAIRecommendation:
    rec = await db.get(SLAIRecommendation, rec_id)
    if not rec:
        raise ValueError("SLAIRecommendation not found")
    rec.status        = data.status
    rec.reviewed_by_id= data.reviewed_by_id
    rec.reviewed_at   = datetime.utcnow()
    rec.review_note   = data.review_note
    await db.commit()
    await db.refresh(rec)
    return rec


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession) -> ShelfLifeDashboard:
    from app.schemas.shelf_life import (
        LotShelfLifeProfileOut, ShelfLifeAlertOut,
        DispositionSuggestionOut, SLAIRecommendationOut, ShelfLifeKPIs,
    )

    # KPIs
    total_r = await db.execute(select(func.count(LotShelfLifeProfile.id)))
    total = total_r.scalar() or 0

    active_r = await db.execute(select(func.count(LotShelfLifeProfile.id)).where(
        LotShelfLifeProfile.shelf_life_status == ShelfLifeStatus.active))
    active = active_r.scalar() or 0

    near_r = await db.execute(select(func.count(LotShelfLifeProfile.id)).where(
        LotShelfLifeProfile.shelf_life_status == ShelfLifeStatus.near_expiry))
    near = near_r.scalar() or 0

    exp_r = await db.execute(select(func.count(LotShelfLifeProfile.id)).where(
        LotShelfLifeProfile.expired_flag == True))
    exp = exp_r.scalar() or 0

    blk_r = await db.execute(select(func.count(LotShelfLifeProfile.id)).where(
        LotShelfLifeProfile.shelf_life_status == ShelfLifeStatus.blocked))
    blk = blk_r.scalar() or 0

    prt_r = await db.execute(select(func.count(LotShelfLifeProfile.id)).where(
        LotShelfLifeProfile.shelf_life_status == ShelfLifeStatus.pending_retest))
    prt = prt_r.scalar() or 0

    alert_r = await db.execute(select(func.count(ShelfLifeAlert.id)).where(
        ShelfLifeAlert.is_resolved == False))
    open_alerts = alert_r.scalar() or 0

    disp_r = await db.execute(select(func.count(DispositionSuggestion.id)).where(
        DispositionSuggestion.status == DispositionStatus.suggested))
    pending_disp = disp_r.scalar() or 0

    # Compliance
    total_picks_r = await db.execute(select(func.count(FEFOAuditLog.id)))
    total_picks = total_picks_r.scalar() or 0
    comp_picks_r  = await db.execute(
        select(func.count(FEFOAuditLog.id)).where(FEFOAuditLog.is_fefo_compliant == True)
    )
    comp_picks = comp_picks_r.scalar() or 0
    compliance_pct = Decimal(str(round(comp_picks / total_picks * 100, 1))) if total_picks > 0 else None

    kpis = ShelfLifeKPIs(
        total_lots_tracked=total,
        active_lots=active,
        near_expiry_lots=near,
        expired_lots=exp,
        blocked_lots=blk,
        pending_retest_lots=prt,
        near_expiry_value_kes=Decimal("0"),
        expired_value_kes=Decimal("0"),
        fefo_compliance_pct=compliance_pct,
        open_alerts=open_alerts,
        pending_dispositions=pending_disp,
    )

    near_profiles   = await list_near_expiry(db, days=14)
    expired_profiles= await list_expired(db)
    alerts          = await list_alerts(db, resolved=False, limit=10)
    dispositions    = await list_disposition_suggestions(db, status=DispositionStatus.suggested)
    ai_recs         = await list_ai_recommendations(db, status=SLAIRecStatus.pending, limit=5)

    bulk_holds      = await list_bulk_holds(db, active_only=True)
    bulk_at_risk    = sum(1 for h in bulk_holds if h.is_near_limit or h.is_expired)

    retest_queue    = await list_retest_queue(db)
    retest_overdue  = len(retest_queue)

    return ShelfLifeDashboard(
        kpis=kpis,
        critical_alerts=[ShelfLifeAlertOut.model_validate(a) for a in alerts],
        near_expiry_lots=[LotShelfLifeProfileOut.model_validate(p) for p in near_profiles[:10]],
        expired_lots=[LotShelfLifeProfileOut.model_validate(p) for p in expired_profiles[:10]],
        pending_dispositions=[DispositionSuggestionOut.model_validate(d) for d in dispositions[:5]],
        pending_ai_recs=[SLAIRecommendationOut.model_validate(r) for r in ai_recs],
        retest_overdue=retest_overdue,
        bulk_hold_at_risk=bulk_at_risk,
    )
