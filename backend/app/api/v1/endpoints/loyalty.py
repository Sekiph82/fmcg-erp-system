"""Customer Loyalty Program endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db
from app.models.loyalty import LoyaltyTier, CustomerLoyaltyAccount, LoyaltyTransaction

router = APIRouter()


# ── Tiers ──────────────────────────────────────────────────────────────────────

@router.get("/tiers", response_model=list)
async def list_tiers(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    r = await db.execute(
        select(LoyaltyTier).where(LoyaltyTier.is_active == True)
        .order_by(LoyaltyTier.display_order)
    )
    tiers = list(r.scalars())
    result = []
    for t in tiers:
        count_r = await db.execute(
            select(func.count()).select_from(CustomerLoyaltyAccount)
            .where(CustomerLoyaltyAccount.tier_id == t.id, CustomerLoyaltyAccount.is_active == True)
        )
        result.append({
            "id": str(t.id),
            "tier_code": t.tier_code,
            "tier_name": t.tier_name,
            "min_lifetime_points": t.min_lifetime_points,
            "points_per_100_spend": float(t.points_per_100_spend),
            "discount_pct": float(t.discount_pct),
            "perks": t.perks or [],
            "color": t.color,
            "member_count": count_r.scalar_one(),
        })
    return result


@router.post("/tiers", status_code=201)
async def create_tier(body: dict, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from decimal import Decimal
    tier = LoyaltyTier(
        tier_code=body["tier_code"],
        tier_name=body["tier_name"],
        min_lifetime_points=int(body.get("min_lifetime_points", 0)),
        points_per_100_spend=Decimal(str(body.get("points_per_100_spend", 1))),
        discount_pct=Decimal(str(body.get("discount_pct", 0))),
        perks=body.get("perks", []),
        color=body.get("color", "#6b7280"),
        display_order=body.get("display_order", 0),
    )
    db.add(tier)
    await db.commit()
    await db.refresh(tier)
    return {"id": str(tier.id), "tier_code": tier.tier_code}


@router.patch("/tiers/{tier_id}")
async def update_tier(tier_id: uuid.UUID, body: dict,
                      db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from decimal import Decimal
    r = await db.execute(select(LoyaltyTier).where(LoyaltyTier.id == tier_id))
    tier = r.scalar_one_or_none()
    if not tier:
        raise HTTPException(404, "Tier not found")
    for k in ["tier_name", "min_lifetime_points", "perks", "color", "display_order", "is_active"]:
        if k in body:
            setattr(tier, k, body[k])
    if "discount_pct" in body:
        tier.discount_pct = Decimal(str(body["discount_pct"]))
    if "points_per_100_spend" in body:
        tier.points_per_100_spend = Decimal(str(body["points_per_100_spend"]))
    await db.commit()
    return {"id": str(tier.id)}


# ── Accounts ───────────────────────────────────────────────────────────────────

@router.get("/accounts", response_model=list)
async def list_accounts(
    tier_id: Optional[uuid.UUID] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(CustomerLoyaltyAccount).options(
        selectinload(CustomerLoyaltyAccount.customer),
        selectinload(CustomerLoyaltyAccount.tier),
    ).where(CustomerLoyaltyAccount.is_active == True)
    if tier_id:
        q = q.where(CustomerLoyaltyAccount.tier_id == tier_id)
    r = await db.execute(q.order_by(CustomerLoyaltyAccount.total_points.desc()).limit(limit))
    accounts = list(r.scalars())
    return [
        {
            "id": str(a.id),
            "customer_id": str(a.customer_id),
            "customer_name": a.customer.name if a.customer else None,
            "customer_code": a.customer.code if a.customer else None,
            "tier_id": str(a.tier_id) if a.tier_id else None,
            "tier_name": a.tier.tier_name if a.tier else "Untiered",
            "tier_color": a.tier.color if a.tier else "#6b7280",
            "total_points": a.total_points,
            "lifetime_points": a.lifetime_points,
            "enrolled_at": a.enrolled_at.isoformat() if a.enrolled_at else None,
            "last_activity_at": a.last_activity_at.isoformat() if a.last_activity_at else None,
        }
        for a in accounts
    ]


@router.get("/accounts/{customer_id}", response_model=dict)
async def get_account(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    r = await db.execute(
        select(CustomerLoyaltyAccount).options(
            selectinload(CustomerLoyaltyAccount.customer),
            selectinload(CustomerLoyaltyAccount.tier),
            selectinload(CustomerLoyaltyAccount.transactions).selectinload(LoyaltyTransaction.created_by),
        ).where(CustomerLoyaltyAccount.customer_id == customer_id)
    )
    a = r.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Loyalty account not found for this customer")
    return {
        "id": str(a.id),
        "customer_id": str(a.customer_id),
        "customer_name": a.customer.name if a.customer else None,
        "tier_name": a.tier.tier_name if a.tier else "Untiered",
        "tier_color": a.tier.color if a.tier else "#6b7280",
        "discount_pct": float(a.tier.discount_pct) if a.tier else 0,
        "total_points": a.total_points,
        "lifetime_points": a.lifetime_points,
        "enrolled_at": a.enrolled_at.isoformat() if a.enrolled_at else None,
        "last_activity_at": a.last_activity_at.isoformat() if a.last_activity_at else None,
        "transactions": [
            {
                "id": str(t.id),
                "transaction_type": t.transaction_type,
                "points_delta": t.points_delta,
                "description": t.description,
                "balance_after": t.balance_after,
                "reference_type": t.reference_type,
                "reference_id": t.reference_id,
                "created_by_name": t.created_by.full_name if t.created_by else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in (a.transactions or [])[:50]
        ],
    }


@router.post("/accounts/enroll", status_code=201)
async def enroll_customer(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    customer_id = uuid.UUID(body["customer_id"])
    existing = await db.execute(
        select(CustomerLoyaltyAccount).where(CustomerLoyaltyAccount.customer_id == customer_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Customer already enrolled in loyalty program")
    tier_id = None
    r = await db.execute(
        select(LoyaltyTier).where(LoyaltyTier.min_lifetime_points == 0, LoyaltyTier.is_active == True)
        .order_by(LoyaltyTier.display_order)
    )
    base_tier = r.scalars().first()
    if base_tier:
        tier_id = base_tier.id
    account = CustomerLoyaltyAccount(
        customer_id=customer_id,
        tier_id=tier_id,
        total_points=body.get("initial_points", 0),
        lifetime_points=body.get("initial_points", 0),
        enrolled_at=datetime.utcnow(),
    )
    db.add(account)
    await db.flush()
    if account.total_points > 0:
        txn = LoyaltyTransaction(
            account_id=account.id,
            transaction_type="BONUS",
            points_delta=account.total_points,
            description="Welcome bonus",
            balance_after=account.total_points,
            created_by_id=current_user.id,
        )
        db.add(txn)
    await db.commit()
    return {"id": str(account.id), "customer_id": str(account.customer_id)}


# ── Transactions (earn / redeem) ───────────────────────────────────────────────

@router.post("/accounts/{customer_id}/earn")
async def earn_points(
    customer_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(
        select(CustomerLoyaltyAccount).options(selectinload(CustomerLoyaltyAccount.tier))
        .where(CustomerLoyaltyAccount.customer_id == customer_id)
    )
    account = r.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Loyalty account not found")

    points = int(body.get("points", 0))
    if points <= 0 and not body.get("spend_amount"):
        raise HTTPException(422, "Provide points or spend_amount")

    if body.get("spend_amount") and not points:
        rate = float(account.tier.points_per_100_spend) if account.tier else 1.0
        points = int(float(body["spend_amount"]) / 100 * rate)

    account.total_points += points
    account.lifetime_points += points
    account.last_activity_at = datetime.utcnow()

    txn = LoyaltyTransaction(
        account_id=account.id,
        transaction_type="EARN",
        points_delta=points,
        description=body.get("description", f"Points earned"),
        reference_type=body.get("reference_type"),
        reference_id=body.get("reference_id"),
        balance_after=account.total_points,
        created_by_id=current_user.id,
    )
    db.add(txn)

    # Auto-upgrade tier based on lifetime points
    tiers_r = await db.execute(
        select(LoyaltyTier).where(LoyaltyTier.is_active == True)
        .order_by(LoyaltyTier.min_lifetime_points.desc())
    )
    for tier in tiers_r.scalars():
        if account.lifetime_points >= tier.min_lifetime_points:
            account.tier_id = tier.id
            break

    await db.commit()
    return {
        "points_earned": points,
        "total_points": account.total_points,
        "lifetime_points": account.lifetime_points,
    }


@router.post("/accounts/{customer_id}/redeem")
async def redeem_points(
    customer_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await db.execute(
        select(CustomerLoyaltyAccount)
        .where(CustomerLoyaltyAccount.customer_id == customer_id)
    )
    account = r.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "Loyalty account not found")
    points = int(body.get("points", 0))
    if points <= 0:
        raise HTTPException(422, "Points must be positive")
    if account.total_points < points:
        raise HTTPException(422, f"Insufficient points. Balance: {account.total_points}")
    account.total_points -= points
    account.last_activity_at = datetime.utcnow()
    txn = LoyaltyTransaction(
        account_id=account.id,
        transaction_type="REDEEM",
        points_delta=-points,
        description=body.get("description", "Points redeemed"),
        reference_type=body.get("reference_type"),
        reference_id=body.get("reference_id"),
        balance_after=account.total_points,
        created_by_id=current_user.id,
    )
    db.add(txn)
    await db.commit()
    return {
        "points_redeemed": points,
        "total_points": account.total_points,
    }


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/stats")
async def loyalty_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    total_r = await db.execute(
        select(func.count()).select_from(CustomerLoyaltyAccount).where(CustomerLoyaltyAccount.is_active == True)
    )
    points_r = await db.execute(
        select(func.sum(CustomerLoyaltyAccount.total_points))
        .where(CustomerLoyaltyAccount.is_active == True)
    )
    txn_r = await db.execute(select(func.count()).select_from(LoyaltyTransaction))
    top_r = await db.execute(
        select(CustomerLoyaltyAccount).options(
            selectinload(CustomerLoyaltyAccount.customer),
            selectinload(CustomerLoyaltyAccount.tier),
        ).where(CustomerLoyaltyAccount.is_active == True)
        .order_by(CustomerLoyaltyAccount.total_points.desc()).limit(5)
    )
    top = list(top_r.scalars())
    return {
        "total_members": total_r.scalar_one(),
        "total_points_outstanding": int(points_r.scalar_one() or 0),
        "total_transactions": txn_r.scalar_one(),
        "top_members": [
            {
                "customer_name": a.customer.name if a.customer else None,
                "tier_name": a.tier.tier_name if a.tier else "Untiered",
                "total_points": a.total_points,
            }
            for a in top
        ],
    }
