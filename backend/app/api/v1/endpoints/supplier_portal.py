from __future__ import annotations
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission
from app.core.config import settings
from app.core.deps import get_current_user

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

async def _staff_access(request: Request, current_user=Depends(get_current_user)):
    """Staff administration of the supplier portal: reading needs procurement.view, changes procurement.edit.
    (Suppliers themselves use /supplier-self with their own sign-in.)"""
    needed = "procurement.view" if request.method == "GET" else "procurement.edit"
    if not has_permission(current_user, needed):
        raise HTTPException(403, f"Missing permission {needed}")
    return current_user


router = APIRouter(dependencies=[Depends(_staff_access)])


async def _manage_access(current_user=Depends(get_current_user)):
    if not has_permission(current_user, "partner_portal.manage_access"):
        raise HTTPException(403, "Missing permission partner_portal.manage_access")
    return current_user


def _with_link(user, token: str) -> dict:
    out = SPUserOut.model_validate(user).model_dump(mode="json")
    out["activation_link"] = f"{settings.PUBLIC_APP_URL.rstrip('/')}/supplier/activate?token={token}"
    return out


@router.post("/users/{user_id}/password-link")
async def password_link(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), staff=Depends(_manage_access)):
    """New one-time set-password link for an active supplier user (invitation resend / forgotten password)."""
    from app.models.supplier_portal import SPActivityType, SPUser

    user = await db.get(SPUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(409, "This user is deactivated; invite a new user instead.")
    token = svc.new_invitation(user)
    await svc._log(db, user.account_id, SPActivityType.INVITE_USER, notes=f"Set-password link for {user.email} issued by {staff.username}")
    await db.commit()
    await db.refresh(user)
    return _with_link(user, token)


@router.get("/documents/{doc_id}/file")
async def download_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from app.models.supplier_portal import SPDocument
    from app.services.document_storage_service import get_document_storage

    doc = await db.get(SPDocument, doc_id)
    if doc is None or not doc.file_path or "/" in doc.file_path:
        raise HTTPException(status_code=404, detail="Document file not found")
    if doc.scan_status != "CLEAN":  # unscanned/infected files stay quarantined
        raise HTTPException(status_code=409, detail=f"File not released: malware scan status {doc.scan_status}")
    path = get_document_storage().path_for(doc.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")
    return FileResponse(path, filename=doc.file_name)


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


@router.post("/accounts/{account_id}/users/invite")
async def invite_user(
    account_id: uuid.UUID,
    payload: SPUserInvite,
    db: AsyncSession = Depends(get_db),
    staff=Depends(_manage_access),
):
    from sqlalchemy import func, select

    from app.models.supplier_portal import SPUser

    if await svc.get_account(db, account_id) is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if (await db.execute(select(SPUser.id).where(func.lower(SPUser.email) == payload.email.strip().lower()))).first():
        raise HTTPException(409, "A supplier portal user with this e-mail already exists.")
    user = await svc.invite_user(db, account_id, payload, staff.username)
    token = user.raw_invitation_token
    await db.commit()
    await db.refresh(user)
    return _with_link(user, token)


@router.post("/users/{user_id}/deactivate", response_model=SPUserOut, dependencies=[Depends(_manage_access)])
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
    db: AsyncSession = Depends(get_db),
):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        resp = await svc.acknowledge_po(db, acct, po_id, payload, user_id=None)
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
    db: AsyncSession = Depends(get_db),
):
    acct = await svc.get_account(db, account_id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    from sqlalchemy import select as _select

    from app.models.procurement import PurchaseOrder

    await db.execute(_select(PurchaseOrder.id).where(PurchaseOrder.id == payload.po_id).with_for_update())  # revision numbers
    if not await svc.get_po_detail(db, acct, payload.po_id):
        raise HTTPException(status_code=404, detail="Purchase order not found for this supplier")
    eta = await svc.propose_eta(db, acct, payload, user_id=None)
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

@router.get("/accounts/{account_id}/documents", response_model=List[SPDocumentOut])
async def list_documents(
    account_id: uuid.UUID,
    upload_type: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_documents(db, account_id, upload_type=upload_type, review_status=review_status)


@router.post("/documents/{doc_id}/review", response_model=SPDocumentOut)
async def review_document(doc_id: uuid.UUID, payload: SPDocumentReview, db: AsyncSession = Depends(get_db),
                          staff=Depends(_staff_access)):
    payload.reviewed_by = staff.full_name or staff.username   # recorded under the signed-in reviewer, not typed text
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
