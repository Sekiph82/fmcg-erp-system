from __future__ import annotations
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.supplier_portal import (
    SPAccountCreate, SPAccountUpdate, SPAccountOut,
    SPUserInvite, SPUserOut,
    SPPermissionProfileOut,
    SPActivityLogOut,
    SPDocumentCreate, SPDocumentReview, SPDocumentOut,
    SPPOAcknowledge, SPPOResponseOut,
    SPETAPropose, SPETAReview, SPETALogOut,
    SPLoginRequest, SPLoginResponse, SPPasswordReset,
    SPAIRecAck, SPAIRecommendationOut,
    SPDashboard,
)
import app.services.supplier_portal_service as svc

router = APIRouter()


# ── Auth ───────────────────────────────────────────────────────────────────────

@router.post("/auth/login")
async def login(payload: SPLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    result = await svc.login(db, payload, ip=ip)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials or inactive account")
    await db.commit()
    return result


@router.post("/auth/reset-password")
async def reset_password(payload: SPPasswordReset, db: AsyncSession = Depends(get_db)):
    ok = await svc.reset_password(db, payload.email, payload.new_password)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()
    return {"detail": "Password updated"}


# ── Account CRUD ───────────────────────────────────────────────────────────────

@router.post("/accounts", response_model=SPAccountOut)
async def create_account(payload: SPAccountCreate, db: AsyncSession = Depends(get_db)):
    acct = await svc.create_account(db, payload)
    await db.commit()
    await db.refresh(acct)
    return acct


@router.get("/accounts", response_model=List[SPAccountOut])
async def list_accounts(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_accounts(db, status=status)


@router.get("/accounts/{account_id}", response_model=SPAccountOut)
async def get_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    return acct


@router.put("/accounts/{account_id}", response_model=SPAccountOut)
async def update_account(account_id: uuid.UUID, payload: SPAccountUpdate, db: AsyncSession = Depends(get_db)):
    acct = await svc.update_account(db, account_id, payload)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.commit()
    await db.refresh(acct)
    return acct


# ── User Management ────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/users", response_model=List[SPUserOut])
async def list_users(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await svc.list_users(db, account_id)


@router.post("/accounts/{account_id}/users/invite", response_model=SPUserOut)
async def invite_user(
    account_id: uuid.UUID,
    payload: SPUserInvite,
    invited_by: str = Query("internal"),
    db: AsyncSession = Depends(get_db),
):
    user = await svc.invite_user(db, account_id, payload, invited_by)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/deactivate", response_model=SPUserOut)
async def deactivate_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await svc.deactivate_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()
    return user


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/dashboard")
async def get_dashboard(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    result = await svc.get_dashboard(db, acct)
    await db.commit()
    return result


# ── Purchase Orders ────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/purchase-orders")
async def list_pos(
    account_id: uuid.UUID,
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    return await svc.list_supplier_pos(db, acct, status=status, limit=limit)


@router.get("/accounts/{account_id}/purchase-orders/{po_id}")
async def get_po(account_id: uuid.UUID, po_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    detail = await svc.get_po_detail(db, acct, po_id)
    if not detail:
        raise HTTPException(status_code=404, detail="PO not found")
    await db.commit()
    return detail


# ── PO Acknowledgment ──────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/purchase-orders/{po_id}/acknowledge", response_model=SPPOResponseOut)
async def acknowledge_po(
    account_id: uuid.UUID,
    po_id: uuid.UUID,
    payload: SPPOAcknowledge,
    user_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        resp = await svc.acknowledge_po(db, acct, po_id, payload, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(resp)
    return resp


# ── ETA Management ─────────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/propose-eta", response_model=SPETALogOut)
async def propose_eta(
    account_id: uuid.UUID,
    payload: SPETAPropose,
    user_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    eta = await svc.propose_eta(db, acct, payload, user_id=user_id)
    await db.commit()
    await db.refresh(eta)
    return eta


@router.get("/accounts/{account_id}/eta-history")
async def list_eta_history(
    account_id: uuid.UUID,
    po_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_eta_history(db, account_id, po_id)


@router.post("/eta/{eta_id}/review", response_model=SPETALogOut)
async def review_eta(eta_id: uuid.UUID, payload: SPETAReview, db: AsyncSession = Depends(get_db)):
    eta = await svc.review_eta(db, eta_id, payload)
    if not eta:
        raise HTTPException(status_code=404, detail="ETA log not found")
    await db.commit()
    await db.refresh(eta)
    return eta


# ── Document Upload ────────────────────────────────────────────────────────────

@router.post("/accounts/{account_id}/documents", response_model=SPDocumentOut)
async def upload_document(
    account_id: uuid.UUID,
    payload: SPDocumentCreate,
    user_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    doc = await svc.upload_document(db, acct, payload, user_id=user_id)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/accounts/{account_id}/documents", response_model=List[SPDocumentOut])
async def list_documents(
    account_id: uuid.UUID,
    upload_type: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_documents(db, account_id, upload_type=upload_type, review_status=review_status)


@router.post("/documents/{doc_id}/review", response_model=SPDocumentOut)
async def review_document(doc_id: uuid.UUID, payload: SPDocumentReview, db: AsyncSession = Depends(get_db)):
    doc = await svc.review_document(db, doc_id, payload)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/documents/expiring")
async def expiring_documents(days: int = Query(30, le=365), db: AsyncSession = Depends(get_db)):
    return await svc.list_expiring_docs(db, days=days)


# ── Payment Status ─────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/payment-status")
async def get_payment_status(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    return await svc.get_payment_status(db, acct)


# ── Activity Log ───────────────────────────────────────────────────────────────

@router.get("/accounts/{account_id}/activity", response_model=List[SPActivityLogOut])
async def list_activity(
    account_id: uuid.UUID,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_activity(db, account_id, limit=limit)


# ── AI Agents ──────────────────────────────────────────────────────────────────

@router.post("/ai/run")
async def run_ai(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_ai_agents(db)
    await db.commit()
    return {"generated": len(recs)}


@router.get("/ai/recommendations", response_model=List[SPAIRecommendationOut])
async def list_ai_recs(
    account_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, account_id=account_id)


@router.post("/ai/recommendations/{rec_id}/ack", response_model=SPAIRecommendationOut)
async def ack_rec(rec_id: uuid.UUID, payload: SPAIRecAck, db: AsyncSession = Depends(get_db)):
    rec = await svc.ack_ai_rec(db, rec_id, payload)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    await db.commit()
    await db.refresh(rec)
    return rec


# ── Reports ────────────────────────────────────────────────────────────────────

@router.get("/reports/po-acknowledgment-time")
async def report_ack_time(db: AsyncSession = Depends(get_db)):
    return await svc.report_po_acknowledgment_time(db)


@router.get("/reports/eta-revisions")
async def report_eta(db: AsyncSession = Depends(get_db)):
    return await svc.report_eta_revisions(db)


@router.get("/reports/adoption")
async def report_adoption(db: AsyncSession = Depends(get_db)):
    return await svc.report_adoption(db)


@router.get("/reports/not-responding")
async def report_not_responding(db: AsyncSession = Depends(get_db)):
    return await svc.report_not_responding_suppliers(db)
