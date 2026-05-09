from __future__ import annotations
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.portal import (
    PortalAccountCreate, PortalAccountRead, PortalAccountUpdate,
    PortalUserInvite, PortalUserRead,
    PortalLoginRequest, PortalLoginResponse,
    PortalPasswordSetRequest,
    PortalClaimCreate, PortalClaimRead, PortalClaimReview,
    PortalDraftOrderCreate, PortalDraftOrderRead, PortalDraftOrderReview,
    PortalActivityRead,
    PortalAIRecRead, PortalAIRecAck,
)
import app.services.portal_service as svc

router = APIRouter()


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/auth/login", response_model=PortalLoginResponse)
async def portal_login(data: PortalLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await svc.login(db, data.email, data.password)
    if not result:
        raise HTTPException(401, "Invalid credentials or account inactive")
    return result


@router.post("/auth/activate")
async def activate_portal_user(data: PortalPasswordSetRequest, db: AsyncSession = Depends(get_db)):
    user = await svc.activate_user_with_password(db, data.token, data.new_password)
    if not user:
        raise HTTPException(400, "Invalid or expired invitation token")
    return {"message": "Account activated successfully", "email": user.email}


# ── Portal Accounts (internal admin) ─────────────────────────────────────────

@router.get("/accounts", response_model=List[PortalAccountRead])
async def list_accounts(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_accounts(db, status=status, skip=skip, limit=limit)


@router.post("/accounts", response_model=PortalAccountRead, status_code=201)
async def create_account(data: PortalAccountCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_account(db, data)


@router.get("/accounts/{account_id}", response_model=PortalAccountRead)
async def get_account(account_id: str, db: AsyncSession = Depends(get_db)):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return acc


@router.patch("/accounts/{account_id}", response_model=PortalAccountRead)
async def update_account(account_id: str, data: PortalAccountUpdate, db: AsyncSession = Depends(get_db)):
    acc = await svc.update_account(db, account_id, data)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return acc


@router.post("/accounts/{account_id}/activate", response_model=PortalAccountRead)
async def activate_account(account_id: str, db: AsyncSession = Depends(get_db)):
    acc = await svc.activate_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return acc


@router.post("/accounts/{account_id}/suspend", response_model=PortalAccountRead)
async def suspend_account(account_id: str, db: AsyncSession = Depends(get_db)):
    acc = await svc.suspend_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return acc


# ── Portal Users ──────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/users", response_model=List[PortalUserRead])
async def list_users(account_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.get_users(db, account_id)


@router.post("/accounts/{account_id}/users/invite", response_model=PortalUserRead, status_code=201)
async def invite_user(account_id: str, data: PortalUserInvite, db: AsyncSession = Depends(get_db)):
    return await svc.invite_user(db, account_id, data)


@router.post("/users/{user_id}/deactivate", response_model=PortalUserRead)
async def deactivate_user(user_id: str, db: AsyncSession = Depends(get_db)):
    user = await svc.deactivate_user(db, user_id)
    if not user:
        raise HTTPException(404, "Portal user not found")
    return user


# ── Portal Self-Service (scoped to account) ───────────────────────────────────

@router.get("/accounts/{account_id}/dashboard")
async def portal_dashboard(account_id: str, db: AsyncSession = Depends(get_db)):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return await svc.get_portal_dashboard(db, acc)


@router.get("/accounts/{account_id}/orders")
async def portal_orders(
    account_id: str,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return await svc.get_portal_orders(db, acc, status=status, skip=skip, limit=limit)


@router.get("/accounts/{account_id}/orders/{order_id}")
async def portal_order_detail(account_id: str, order_id: str, db: AsyncSession = Depends(get_db)):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    order = await svc.get_portal_order_detail(db, acc, order_id)
    if not order:
        raise HTTPException(404, "Order not found or not accessible")
    return order


@router.get("/accounts/{account_id}/shipments")
async def portal_shipments(
    account_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return await svc.get_portal_shipments(db, acc, skip=skip, limit=limit)


@router.get("/accounts/{account_id}/invoices")
async def portal_invoices(
    account_id: str,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return await svc.get_portal_invoices(db, acc, status=status, skip=skip, limit=limit)


@router.get("/accounts/{account_id}/payments")
async def portal_payments(
    account_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return await svc.get_portal_payments(db, acc, skip=skip, limit=limit)


@router.get("/accounts/{account_id}/statement")
async def portal_statement(
    account_id: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    return await svc.get_portal_statement(db, acc, from_date=from_date, to_date=to_date)


# ── Claims ─────────────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/claims", response_model=List[PortalClaimRead])
async def list_claims(account_id: str, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_claims(db, account_id, status=status)


@router.post("/accounts/{account_id}/claims", response_model=PortalClaimRead, status_code=201)
async def submit_claim(
    account_id: str,
    data: PortalClaimCreate,
    submitted_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_claim(db, account_id, submitted_by or "portal_user", data)


@router.patch("/claims/{claim_id}/review", response_model=PortalClaimRead)
async def review_claim(claim_id: str, data: PortalClaimReview, db: AsyncSession = Depends(get_db)):
    claim = await svc.review_claim(db, claim_id, data)
    if not claim:
        raise HTTPException(404, "Claim not found")
    return claim


# ── Draft Orders ──────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/draft-orders", response_model=List[PortalDraftOrderRead])
async def list_draft_orders(account_id: str, status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.get_draft_orders(db, account_id, status=status)


@router.post("/accounts/{account_id}/draft-orders", response_model=PortalDraftOrderRead, status_code=201)
async def create_draft_order(
    account_id: str,
    data: PortalDraftOrderCreate,
    submitted_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_draft_order(db, account_id, submitted_by or "portal_user", data)


@router.post("/accounts/{account_id}/draft-orders/{draft_id}/submit", response_model=PortalDraftOrderRead)
async def submit_draft_order(account_id: str, draft_id: str, db: AsyncSession = Depends(get_db)):
    draft = await svc.submit_draft_order(db, draft_id)
    if not draft:
        raise HTTPException(404, "Draft order not found")
    return draft


@router.patch("/draft-orders/{draft_id}/review", response_model=PortalDraftOrderRead)
async def review_draft_order(draft_id: str, data: PortalDraftOrderReview, db: AsyncSession = Depends(get_db)):
    draft = await svc.review_draft_order(db, draft_id, data)
    if not draft:
        raise HTTPException(404, "Draft order not found")
    return draft


@router.post("/accounts/{account_id}/reorder/{source_order_id}", response_model=PortalDraftOrderRead)
async def reorder(
    account_id: str,
    source_order_id: str,
    submitted_by: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")
    draft = await svc.reorder_from_order(db, acc, submitted_by or "portal_user", source_order_id)
    if not draft:
        raise HTTPException(404, "Source order not found or not accessible")
    return draft


# ── Activity Logs ─────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/activity", response_model=List[PortalActivityRead])
async def get_activity_logs(account_id: str, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await svc.get_activity_logs(db, account_id=account_id, limit=limit)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/adoption")
async def adoption_report(db: AsyncSession = Depends(get_db)):
    return await svc.portal_adoption_report(db)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.post("/ai/run-support-assistant")
async def run_support_assistant(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_support_assistant(db)
    return {"generated": len(recs), "message": f"Support Assistant generated {len(recs)} recommendations"}


@router.post("/ai/run-friction-monitor")
async def run_friction_monitor(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_friction_monitor(db)
    return {"generated": len(recs), "message": f"Friction Monitor generated {len(recs)} recommendations"}


@router.post("/ai/run-commercial-opportunity")
async def run_commercial_opportunity(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_commercial_opportunity(db)
    return {"generated": len(recs), "message": f"Commercial Opportunity agent generated {len(recs)} recommendations"}


@router.get("/ai/recommendations", response_model=List[PortalAIRecRead])
async def get_ai_recommendations(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_ai_recommendations(db, agent_type=agent_type, status=status)


@router.patch("/ai/recommendations/{rec_id}", response_model=PortalAIRecRead)
async def ack_recommendation(rec_id: str, data: PortalAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_recommendation(db, rec_id, data)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec


# ── Order Tracking (confirmed ERP sales orders for portal account) ─────────────

@router.get("/accounts/{account_id}/sales-orders")
async def portal_sales_orders(
    account_id: str,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return confirmed ERP sales orders linked to the portal account's customer."""
    from sqlalchemy import select
    from app.models.portal import PortalAccount
    from app.models.sales import SalesOrder, SOStatus

    acc = await svc.get_account(db, account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")

    if not acc.linked_customer_id:
        return []

    result = await db.execute(
        select(SalesOrder)
        .where(
            SalesOrder.customer_id.cast(str) == str(acc.linked_customer_id)
        )
        .order_by(SalesOrder.created_at.desc())
        .limit(limit)
    )
    orders = result.scalars().all()
    return [
        {
            "id": str(o.id),
            "order_no": o.order_no,
            "order_date": str(o.order_date) if o.order_date else None,
            "status": o.status,
            "payment_status": o.payment_status,
            "total_amount": float(o.total_amount) if hasattr(o, "total_amount") and o.total_amount else None,
            "currency": getattr(o, "currency", "KES"),
            "requested_delivery_date": str(o.requested_delivery_date) if o.requested_delivery_date else None,
            "created_at": o.created_at.isoformat() if o.created_at else "",
        }
        for o in orders
    ]


# ── Sell-Through Upload (distributor portal) ──────────────────────────────────

from pydantic import BaseModel as _BaseModel

class SellThroughUploadIn(_BaseModel):
    account_id: str
    period_start: str
    period_end: str
    total_units_sold: int
    total_value: Optional[float] = None
    notes: Optional[str] = None
    upload_reference: Optional[str] = None


@router.post("/sell-through-upload", status_code=201)
async def submit_sell_through(
    payload: SellThroughUploadIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Distributor self-service sell-through data submission.
    Creates a portal sell-through upload record for internal review.
    """
    from app.models.portal import PortalAccount, PortalSellThroughUpload
    from datetime import date
    import uuid as _uuid2

    acc = await svc.get_account(db, payload.account_id)
    if not acc:
        raise HTTPException(404, "Portal account not found")

    upload = PortalSellThroughUpload(
        portal_account_id=acc.id,
        period_start=date.fromisoformat(payload.period_start),
        period_end=date.fromisoformat(payload.period_end),
        total_units_sold=payload.total_units_sold,
        total_value=payload.total_value,
        notes=payload.notes,
        upload_reference=payload.upload_reference,
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)
    return {
        "upload_id": str(upload.id),
        "status": "PENDING",
        "period": f"{payload.period_start} to {payload.period_end}",
        "message": "Sell-through data received. Pending review.",
    }
