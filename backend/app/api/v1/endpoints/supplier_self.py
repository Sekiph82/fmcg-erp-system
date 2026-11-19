"""Supplier self-service portal (M38.S05.T001).

Signed in with the supplier realm cookie (``app.core.external_auth``), never a staff session. Everything is scoped to
the signed-in user's supplier: only released purchase orders (approved/ordered/received) are visible; acknowledging,
proposing delivery dates and uploading documents are limited by the user's portal role.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import external_auth as ext
from app.db.session import get_db
from app.models.supplier_portal import SPActivityType, SPDocUploadType, SPUser, SPUserRole
from app.schemas.supplier_portal import SPDocumentCreate, SPETAPropose, SPPOAcknowledge
from app.services import supplier_portal_service as svc

public = APIRouter()
router = APIRouter()

RESPOND_ROLES = {SPUserRole.OWNER, SPUserRole.SALES, SPUserRole.LOGISTICS}
UPLOAD_ROLES = {SPUserRole.OWNER, SPUserRole.SALES, SPUserRole.LOGISTICS, SPUserRole.FINANCE, SPUserRole.QUALITY}
PAYMENT_ROLES = {SPUserRole.OWNER, SPUserRole.FINANCE}


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class ActivateIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class PasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class AckIn(BaseModel):
    response_status: str = Field(pattern=r"^(ACCEPTED|ACCEPTED_REVISED_ETA|PARTIALLY_ACCEPTED|REJECTED)$")
    supplier_comment: Optional[str] = Field(default=None, max_length=2000)
    rejection_reason: Optional[str] = Field(default=None, max_length=2000)
    proposed_eta: Optional[date] = None


class EtaIn(BaseModel):
    proposed_date: date
    supplier_reason: str = Field(min_length=3, max_length=2000)


def _me(user: SPUser, supplier_name: Optional[str]) -> dict:
    a = user.account
    return {"id": str(user.id), "full_name": user.full_name, "email": user.email, "role": user.role_type.value,
            "supplier_name": supplier_name, "can_respond": user.role_type in RESPOND_ROLES,
            "can_upload": user.role_type in UPLOAD_ROLES,
            "can_view_payment": bool(a.can_view_payment) and user.role_type in PAYMENT_ROLES,
            "can_view_prices": bool(a.can_view_prices)}


async def _supplier_name(db: AsyncSession, user: SPUser) -> Optional[str]:
    from app.models.master import Supplier

    s = await db.get(Supplier, user.account.supplier_id)
    return s.name if s else None


def _require(user: SPUser, roles: set, what: str):
    if user.role_type not in roles:
        raise HTTPException(403, f"Your portal role cannot {what}.")


# ── sign-in ───────────────────────────────────────────────────────────────────

@public.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from app.models.supplier_portal import SPAccount, SPAccountStatus

    key = await ext.login_guard("supplier", body.email)
    user = (await db.execute(select(SPUser).where(func.lower(SPUser.email) == body.email.strip().lower()))).scalar_one_or_none()
    account = await db.get(SPAccount, user.account_id) if user else None
    usable = (user is not None and user.is_active and account is not None
              and account.portal_status == SPAccountStatus.ACTIVE and user.password_hash)
    if not usable or not await ext.password_login(db, response, "supplier", user, body.password, key):
        if not usable:
            ext.dummy_password_check(body.password)
            await ext.record_login_failure(key)
        raise HTTPException(401, "E-mail or password is incorrect, or the account is not active.")
    user.last_login_at = datetime.now(timezone.utc)
    await svc._log(db, account.id, SPActivityType.LOGIN, user_id=user.id,
                   ip=request.client.host if request.client else None)
    await db.commit()
    user.account = account
    return _me(user, await _supplier_name(db, user))


@public.post("/auth/activate")
async def activate(body: ActivateIn, db: AsyncSession = Depends(get_db)):
    user = await svc.activate_with_token(db, body.token, body.new_password)
    if not user:
        raise HTTPException(400, "This link is invalid or has expired. Ask your buyer for a new one.")
    await db.commit()
    return {"detail": "Password set. You can sign in now.", "email": user.email}


@public.post("/auth/logout")
async def logout(request: Request, response: Response):
    await ext.sign_out(request, response, "supplier")
    return {"detail": "Signed out"}


# ── signed-in ─────────────────────────────────────────────────────────────────

@router.get("/me")
async def me(user: SPUser = Depends(ext.get_supplier_user), db: AsyncSession = Depends(get_db)):
    return _me(user, await _supplier_name(db, user))


@router.post("/password")
async def change_password(body: PasswordIn, response: Response, user: SPUser = Depends(ext.get_supplier_user),
                          db: AsyncSession = Depends(get_db)):
    from app.core.security import hash_password

    if not ext.check_password(body.current_password, user.password_hash)[0]:
        raise HTTPException(400, "Current password is incorrect.")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    ext.issue(response, "supplier", user.id, user.password_hash)
    return {"detail": "Password changed"}


@router.get("/purchase-orders")
async def purchase_orders(user: SPUser = Depends(ext.get_supplier_user), db: AsyncSession = Depends(get_db)):
    return await svc.list_supplier_pos(db, user.account, limit=200)


@router.get("/purchase-orders/{po_id}")
async def purchase_order(po_id: uuid.UUID, user: SPUser = Depends(ext.get_supplier_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import selectinload

    from app.models.master import Material, Product
    from app.models.procurement import PurchaseOrder

    detail = await svc.get_po_detail(db, user.account, po_id)
    if not detail:
        raise HTTPException(404, "Purchase order not found")
    po = (await db.execute(select(PurchaseOrder).options(selectinload(PurchaseOrder.lines))
                           .where(PurchaseOrder.id == po_id))).scalar_one()
    names = {}
    for l in po.lines:
        item = await db.get(Material, l.material_id) if l.material_id else await db.get(Product, l.product_id) if l.product_id else None
        names[l.id] = getattr(item, "name", None) or l.description or "Item"
    prices = user.account.can_view_prices
    resp, etas, docs = detail["response"], detail["eta_history"], detail["documents"]
    await db.commit()  # activity log (viewed)
    return {
        "id": str(po.id), "po_number": po.po_no, "po_date": str(po.order_date), "status": po.status.value,
        "currency": po.currency, "required_date": str(po.expected_delivery_date), "payment_terms": po.payment_terms,
        "total_amount": float(svc.po_total(po)) if prices else None,
        "lines": [{"line_no": l.line_no, "item": names[l.id], "quantity": float(l.ordered_quantity), "unit": l.unit,
                   "unit_price": float(l.unit_price) if prices else None} for l in po.lines],
        "acknowledgment": {"status": resp.response_status.value, "comment": resp.supplier_comment,
                           "proposed_eta": str(resp.proposed_eta) if resp.proposed_eta else None,
                           "responded_at": resp.responded_at.isoformat()} if resp else None,
        "eta_history": [{"revision_no": e.revision_no, "proposed_date": str(e.proposed_date), "status": e.eta_status.value,
                         "reason": e.supplier_reason, "buyer_notes": e.buyer_notes} for e in etas],
        "documents": [{"id": str(d.id), "type": d.upload_type.value, "file_name": d.file_name,
                       "review_status": d.review_status.value} for d in docs],
    }


@router.post("/purchase-orders/{po_id}/acknowledge")
async def acknowledge(po_id: uuid.UUID, body: AckIn, user: SPUser = Depends(ext.get_supplier_user),
                      db: AsyncSession = Depends(get_db)):
    _require(user, RESPOND_ROLES, "respond to purchase orders")
    if body.response_status == "REJECTED" and not body.rejection_reason:
        raise HTTPException(422, "Please give a reason for rejecting the order.")
    if body.response_status == "ACCEPTED_REVISED_ETA" and not body.proposed_eta:
        raise HTTPException(422, "Please give the delivery date you can meet.")
    try:
        resp = await svc.acknowledge_po(db, user.account, po_id, SPPOAcknowledge(**body.model_dump()), user_id=user.id)
    except ValueError:
        raise HTTPException(404, "Purchase order not found")
    await db.commit()
    return {"status": resp.response_status.value}


@router.post("/purchase-orders/{po_id}/eta")
async def propose_eta(po_id: uuid.UUID, body: EtaIn, user: SPUser = Depends(ext.get_supplier_user),
                      db: AsyncSession = Depends(get_db)):
    _require(user, RESPOND_ROLES, "propose delivery dates")
    detail = await svc.get_po_detail(db, user.account, po_id)  # only this supplier's released POs
    if not detail:
        raise HTTPException(404, "Purchase order not found")
    if body.proposed_date < date.today():
        raise HTTPException(422, "The proposed date cannot be in the past.")
    eta = await svc.propose_eta(db, user.account, SPETAPropose(po_id=po_id, proposed_date=body.proposed_date,
                                                                 supplier_reason=body.supplier_reason,
                                                                 original_date=detail["po"].expected_delivery_date),
                                user_id=user.id)
    await db.commit()
    return {"revision_no": eta.revision_no, "status": eta.eta_status.value}


@router.get("/documents")
async def documents(user: SPUser = Depends(ext.get_supplier_user), db: AsyncSession = Depends(get_db)):
    rows = await svc.list_documents(db, user.account.id)
    return [{"id": str(d.id), "type": d.upload_type.value, "file_name": d.file_name,
             "linked_po_id": str(d.linked_po_id) if d.linked_po_id else None, "review_status": d.review_status.value,
             "expiry_date": str(d.expiry_date) if d.expiry_date else None,
             "uploaded_at": d.uploaded_at.isoformat()} for d in rows]


@router.post("/documents", status_code=201)
async def upload(upload_type: SPDocUploadType = Form(...), linked_po_id: Optional[uuid.UUID] = Form(None),
                 expiry_date: Optional[date] = Form(None), notes: Optional[str] = Form(None, max_length=1000),
                 file: UploadFile = File(...), user: SPUser = Depends(ext.get_supplier_user),
                 db: AsyncSession = Depends(get_db)):
    from app.services.document_storage_service import get_document_storage

    _require(user, UPLOAD_ROLES, "upload documents")
    if linked_po_id and not await svc.get_po_detail(db, user.account, linked_po_id):
        raise HTTPException(422, "The purchase order is not one of yours.")
    stored = await get_document_storage().store_upload(file)  # opaque key, type/size/content checked
    doc = await svc.upload_document(db, user.account, SPDocumentCreate(
        upload_type=upload_type, linked_po_id=linked_po_id, file_name=stored.file_name, file_path=stored.storage_key,
        file_size_kb=max(1, stored.file_size_bytes // 1024), expiry_date=expiry_date, notes=notes), user_id=user.id)
    await db.commit()
    return {"id": str(doc.id), "file_name": doc.file_name, "review_status": doc.review_status.value}


@router.get("/payments")
async def payments(user: SPUser = Depends(ext.get_supplier_user), db: AsyncSession = Depends(get_db)):
    if not (user.account.can_view_payment and user.role_type in PAYMENT_ROLES):
        raise HTTPException(403, "Payment status is not available for your account or role.")
    return await svc.get_payment_status(db, user.account)
