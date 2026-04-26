from __future__ import annotations
import uuid
import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier_portal import (
    SPAccount, SPUser, SPPermissionProfile, SPActivityLog, SPDocument,
    SPPOResponse, SPETALog, SPAIRecommendation,
    SPAccountStatus, SPUserRole, SPActivityType, SPPOResponseStatus,
    SPETAStatus, SPDocUploadType, SPDocReviewStatus,
    SPAIAgentType, SPAIRecStatus,
)
from app.models.procurement import PurchaseOrder, GoodsReceipt
from app.models.finance import PurchaseInvoice, PurchaseInvoiceStatus
from app.schemas.supplier_portal import (
    SPAccountCreate, SPAccountUpdate,
    SPUserInvite,
    SPDocumentCreate, SPDocumentReview,
    SPPOAcknowledge,
    SPETAPropose, SPETAReview,
    SPAIRecAck,
    SPLoginRequest,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _verify_pw(pw: str, hashed: str) -> bool:
    return hashlib.sha256(pw.encode()).hexdigest() == hashed


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _log(
    db: AsyncSession,
    account_id: uuid.UUID,
    activity_type: SPActivityType,
    user_id: Optional[uuid.UUID] = None,
    ref_type: Optional[str] = None,
    ref_id: Optional[str] = None,
    notes: Optional[str] = None,
    ip: Optional[str] = None,
) -> None:
    db.add(SPActivityLog(
        account_id=account_id,
        user_id=user_id,
        activity_type=activity_type,
        reference_type=ref_type,
        reference_id=ref_id,
        activity_datetime=_now(),
        ip_or_session=ip,
        notes=notes,
    ))


# ── Account CRUD ──────────────────────────────────────────────────────────────

async def create_account(db: AsyncSession, payload: SPAccountCreate) -> SPAccount:
    acct = SPAccount(**payload.model_dump())
    db.add(acct)
    await db.flush()
    await db.refresh(acct)
    return acct


async def get_account(db: AsyncSession, account_id: uuid.UUID) -> Optional[SPAccount]:
    return (await db.execute(select(SPAccount).where(SPAccount.id == account_id))).scalar_one_or_none()


async def get_account_by_supplier(db: AsyncSession, supplier_id: uuid.UUID) -> Optional[SPAccount]:
    return (await db.execute(
        select(SPAccount).where(SPAccount.supplier_id == supplier_id)
    )).scalar_one_or_none()


async def list_accounts(db: AsyncSession, status: Optional[str] = None) -> List[SPAccount]:
    q = select(SPAccount)
    if status:
        q = q.where(SPAccount.portal_status == status)
    return list((await db.execute(q.order_by(SPAccount.created_at.desc()))).scalars())


async def update_account(db: AsyncSession, account_id: uuid.UUID, payload: SPAccountUpdate) -> Optional[SPAccount]:
    acct = await get_account(db, account_id)
    if not acct:
        return None
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(acct, k, v)
    await db.flush()
    await db.refresh(acct)
    return acct


# ── User Management ───────────────────────────────────────────────────────────

async def invite_user(db: AsyncSession, account_id: uuid.UUID, payload: SPUserInvite, invited_by: str) -> SPUser:
    temp_pw = secrets.token_urlsafe(12)
    user = SPUser(
        account_id=account_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        role_type=payload.role_type,
        password_hash=_hash_pw(temp_pw),
        login_identifier=payload.email,
        invited_by=invited_by,
        notes=payload.notes,
    )
    db.add(user)
    await db.flush()
    await _log(db, account_id, SPActivityType.INVITE_USER, notes=f"Invited {payload.email}")
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[SPUser]:
    user = (await db.execute(select(SPUser).where(SPUser.id == user_id))).scalar_one_or_none()
    if not user:
        return None
    user.is_active = False
    await db.flush()
    await _log(db, user.account_id, SPActivityType.DEACTIVATE_USER, notes=f"Deactivated {user.email}")
    return user


async def list_users(db: AsyncSession, account_id: uuid.UUID) -> List[SPUser]:
    rows = await db.execute(select(SPUser).where(SPUser.account_id == account_id).order_by(SPUser.created_at))
    return list(rows.scalars())


async def reset_password(db: AsyncSession, email: str, new_pw: str) -> bool:
    user = (await db.execute(select(SPUser).where(SPUser.email == email, SPUser.is_active == True))).scalar_one_or_none()
    if not user:
        return False
    user.password_hash = _hash_pw(new_pw)
    await db.flush()
    return True


# ── Authentication ────────────────────────────────────────────────────────────

async def login(db: AsyncSession, payload: SPLoginRequest, ip: Optional[str] = None) -> Optional[dict]:
    user = (await db.execute(
        select(SPUser).where(SPUser.email == payload.email, SPUser.is_active == True)
    )).scalar_one_or_none()
    if not user or not _verify_pw(payload.password, user.password_hash or ""):
        return None
    user.last_login_at = _now()
    await db.flush()
    await _log(db, user.account_id, SPActivityType.LOGIN, user_id=user.id, ip=ip)
    token = secrets.token_urlsafe(32)
    return {
        "token": token,
        "user_id": str(user.id),
        "account_id": str(user.account_id),
        "full_name": user.full_name,
        "role_type": user.role_type,
    }


# ── Purchase Orders (scoped to supplier) ──────────────────────────────────────

async def list_supplier_pos(
    db: AsyncSession,
    account: SPAccount,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    q = (
        select(PurchaseOrder)
        .where(PurchaseOrder.supplier_id == account.supplier_id)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(limit)
    )
    if status:
        q = q.where(PurchaseOrder.status == status)
    pos = list((await db.execute(q)).scalars())
    result = []
    for po in pos:
        resp = (await db.execute(
            select(SPPOResponse).where(
                SPPOResponse.account_id == account.id,
                SPPOResponse.po_id == po.id,
            )
        )).scalar_one_or_none()
        result.append({
            "po_id": str(po.id),
            "po_number": getattr(po, "po_number", str(po.id)[:8]),
            "po_date": str(po.created_at.date()) if po.created_at else None,
            "status": po.status,
            "total_amount": float(po.total_amount) if po.total_amount else None,
            "currency": getattr(po, "currency", "KES"),
            "required_date": str(po.required_date) if getattr(po, "required_date", None) else None,
            "acknowledgment_status": resp.response_status if resp else "PENDING_RESPONSE",
        })
    return result


async def get_po_detail(
    db: AsyncSession,
    account: SPAccount,
    po_id: uuid.UUID,
) -> Optional[dict]:
    po = (await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id,
            PurchaseOrder.supplier_id == account.supplier_id,
        )
    )).scalar_one_or_none()
    if not po:
        return None
    await _log(db, account.id, SPActivityType.VIEW_PO, ref_type="PurchaseOrder", ref_id=str(po_id))
    resp = (await db.execute(
        select(SPPOResponse).where(
            SPPOResponse.account_id == account.id,
            SPPOResponse.po_id == po.id,
        )
    )).scalar_one_or_none()
    eta_logs = list((await db.execute(
        select(SPETALog)
        .where(SPETALog.account_id == account.id, SPETALog.po_id == po.id)
        .order_by(SPETALog.revision_no.desc())
    )).scalars())
    docs = list((await db.execute(
        select(SPDocument).where(
            SPDocument.account_id == account.id,
            SPDocument.linked_po_id == po.id,
        )
    )).scalars())
    return {
        "po": po,
        "response": resp,
        "eta_history": eta_logs,
        "documents": docs,
    }


# ── PO Acknowledgment ─────────────────────────────────────────────────────────

async def acknowledge_po(
    db: AsyncSession,
    account: SPAccount,
    po_id: uuid.UUID,
    payload: SPPOAcknowledge,
    user_id: Optional[uuid.UUID] = None,
) -> SPPOResponse:
    po = (await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id,
            PurchaseOrder.supplier_id == account.supplier_id,
        )
    )).scalar_one_or_none()
    if not po:
        raise ValueError("PO not found or not belonging to your supplier account")

    existing = (await db.execute(
        select(SPPOResponse).where(
            SPPOResponse.account_id == account.id,
            SPPOResponse.po_id == po_id,
        )
    )).scalar_one_or_none()

    if existing:
        existing.response_status = payload.response_status
        existing.supplier_comment = payload.supplier_comment
        existing.rejection_reason = payload.rejection_reason
        existing.proposed_eta = payload.proposed_eta
        existing.accepted_qty_json = payload.accepted_qty_json
        existing.responded_at = _now()
        existing.responded_by_user = user_id
        resp = existing
    else:
        resp = SPPOResponse(
            account_id=account.id,
            po_id=po_id,
            responded_by_user=user_id,
            response_status=payload.response_status,
            supplier_comment=payload.supplier_comment,
            rejection_reason=payload.rejection_reason,
            proposed_eta=payload.proposed_eta,
            accepted_qty_json=payload.accepted_qty_json,
            responded_at=_now(),
        )
        db.add(resp)

    await db.flush()
    await _log(
        db, account.id, SPActivityType.ACKNOWLEDGE_PO,
        user_id=user_id, ref_type="PurchaseOrder", ref_id=str(po_id),
        notes=payload.response_status,
    )
    await db.refresh(resp)
    return resp


# ── ETA Management ────────────────────────────────────────────────────────────

async def propose_eta(
    db: AsyncSession,
    account: SPAccount,
    payload: SPETAPropose,
    user_id: Optional[uuid.UUID] = None,
) -> SPETALog:
    count = (await db.execute(
        select(func.count(SPETALog.id)).where(
            SPETALog.account_id == account.id,
            SPETALog.po_id == payload.po_id,
        )
    )).scalar() or 0
    eta = SPETALog(
        account_id=account.id,
        po_id=payload.po_id,
        proposed_by=user_id,
        original_date=payload.original_date,
        proposed_date=payload.proposed_date,
        eta_status=SPETAStatus.REVISED,
        revision_no=count + 1,
        supplier_reason=payload.supplier_reason,
    )
    db.add(eta)
    await db.flush()
    await _log(
        db, account.id, SPActivityType.PROPOSE_ETA,
        user_id=user_id, ref_type="PurchaseOrder", ref_id=str(payload.po_id),
        notes=f"Proposed {payload.proposed_date}",
    )
    await db.refresh(eta)
    return eta


async def review_eta(db: AsyncSession, eta_id: uuid.UUID, payload: SPETAReview) -> Optional[SPETALog]:
    eta = (await db.execute(select(SPETALog).where(SPETALog.id == eta_id))).scalar_one_or_none()
    if not eta:
        return None
    eta.eta_status = payload.eta_status
    eta.buyer_notes = payload.buyer_notes
    eta.reviewed_by = payload.reviewed_by
    eta.reviewed_at = _now()
    await db.flush()
    await db.refresh(eta)
    return eta


async def list_eta_history(db: AsyncSession, account_id: uuid.UUID, po_id: uuid.UUID) -> List[SPETALog]:
    rows = await db.execute(
        select(SPETALog)
        .where(SPETALog.account_id == account_id, SPETALog.po_id == po_id)
        .order_by(SPETALog.revision_no.desc())
    )
    return list(rows.scalars())


# ── Document Upload ───────────────────────────────────────────────────────────

async def upload_document(
    db: AsyncSession,
    account: SPAccount,
    payload: SPDocumentCreate,
    user_id: Optional[uuid.UUID] = None,
) -> SPDocument:
    doc = SPDocument(
        account_id=account.id,
        supplier_id=account.supplier_id,
        upload_type=payload.upload_type,
        linked_po_id=payload.linked_po_id,
        linked_grn_id=payload.linked_grn_id,
        linked_invoice_id=payload.linked_invoice_id,
        file_name=payload.file_name,
        file_path=payload.file_path,
        file_size_kb=payload.file_size_kb,
        uploaded_by_user_id=user_id,
        uploaded_at=_now(),
        expiry_date=payload.expiry_date,
        notes=payload.notes,
    )
    db.add(doc)
    await db.flush()
    await _log(
        db, account.id, SPActivityType.UPLOAD_DOC,
        user_id=user_id, ref_type=payload.upload_type, ref_id=payload.file_name,
    )
    await db.refresh(doc)
    return doc


async def review_document(db: AsyncSession, doc_id: uuid.UUID, payload: SPDocumentReview) -> Optional[SPDocument]:
    doc = (await db.execute(select(SPDocument).where(SPDocument.id == doc_id))).scalar_one_or_none()
    if not doc:
        return None
    doc.review_status = payload.review_status
    doc.reviewed_by = payload.reviewed_by
    doc.reviewed_at = _now()
    doc.notes = payload.notes or doc.notes
    await db.flush()
    await db.refresh(doc)
    return doc


async def list_documents(
    db: AsyncSession,
    account_id: uuid.UUID,
    upload_type: Optional[str] = None,
    review_status: Optional[str] = None,
) -> List[SPDocument]:
    q = select(SPDocument).where(SPDocument.account_id == account_id)
    if upload_type:
        q = q.where(SPDocument.upload_type == upload_type)
    if review_status:
        q = q.where(SPDocument.review_status == review_status)
    return list((await db.execute(q.order_by(SPDocument.uploaded_at.desc()))).scalars())


async def list_expiring_docs(db: AsyncSession, days: int = 30) -> List[SPDocument]:
    cutoff = date.today() + timedelta(days=days)
    rows = await db.execute(
        select(SPDocument)
        .where(
            SPDocument.expiry_date != None,
            SPDocument.expiry_date <= cutoff,
            SPDocument.review_status == SPDocReviewStatus.ACCEPTED,
        )
        .order_by(SPDocument.expiry_date)
    )
    return list(rows.scalars())


# ── Payment Status ────────────────────────────────────────────────────────────

async def get_payment_status(db: AsyncSession, account: SPAccount) -> List[dict]:
    if not account.can_view_payment:
        return []
    rows = await db.execute(
        select(PurchaseInvoice)
        .where(PurchaseInvoice.supplier_id == account.supplier_id)
        .order_by(PurchaseInvoice.created_at.desc())
        .limit(100)
    )
    invoices = list(rows.scalars())
    result = []
    for inv in invoices:
        result.append({
            "invoice_id": str(inv.id),
            "invoice_number": getattr(inv, "invoice_number", str(inv.id)[:8]),
            "invoice_date": str(inv.invoice_date) if getattr(inv, "invoice_date", None) else None,
            "total_amount": float(inv.total_amount) if getattr(inv, "total_amount", None) else None,
            "currency": getattr(inv, "currency", "KES"),
            "status": inv.status if inv.status else "SUBMITTED",
            "due_date": str(inv.due_date) if getattr(inv, "due_date", None) else None,
        })
    return result


# ── Activity Log ──────────────────────────────────────────────────────────────

async def list_activity(
    db: AsyncSession,
    account_id: uuid.UUID,
    limit: int = 100,
) -> List[SPActivityLog]:
    rows = await db.execute(
        select(SPActivityLog)
        .where(SPActivityLog.account_id == account_id)
        .order_by(SPActivityLog.activity_datetime.desc())
        .limit(limit)
    )
    return list(rows.scalars())


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def get_dashboard(db: AsyncSession, account: SPAccount) -> dict:
    from app.models.master import Supplier
    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == account.supplier_id)
    )).scalar_one_or_none()

    open_pos = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.supplier_id == account.supplier_id,
        )
    )).scalar() or 0

    pending_ack = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.supplier_id == account.supplier_id,
        )
    )).scalar() or 0

    cutoff_30 = _now() - timedelta(days=30)
    docs_30 = (await db.execute(
        select(func.count(SPDocument.id)).where(
            SPDocument.account_id == account.id,
            SPDocument.uploaded_at >= cutoff_30,
        )
    )).scalar() or 0

    inv_docs_30 = (await db.execute(
        select(func.count(SPDocument.id)).where(
            SPDocument.account_id == account.id,
            SPDocument.upload_type == SPDocUploadType.INVOICE,
            SPDocument.uploaded_at >= cutoff_30,
        )
    )).scalar() or 0

    expiring = (await db.execute(
        select(func.count(SPDocument.id)).where(
            SPDocument.account_id == account.id,
            SPDocument.expiry_date != None,
            SPDocument.expiry_date <= date.today() + timedelta(days=30),
        )
    )).scalar() or 0

    recent = list((await db.execute(
        select(SPActivityLog)
        .where(SPActivityLog.account_id == account.id)
        .order_by(SPActivityLog.activity_datetime.desc())
        .limit(5)
    )).scalars())

    ai_alerts = list((await db.execute(
        select(SPAIRecommendation)
        .where(
            or_(SPAIRecommendation.account_id == account.id, SPAIRecommendation.account_id == None),
            SPAIRecommendation.status == SPAIRecStatus.PENDING,
        )
        .order_by(SPAIRecommendation.created_at.desc())
        .limit(5)
    )).scalars())

    return {
        "account_id": str(account.id),
        "supplier_name": supplier.name if supplier else "Unknown",
        "open_pos": open_pos,
        "pending_acknowledgment": pending_ack,
        "uploaded_invoices_30d": inv_docs_30,
        "uploaded_docs_30d": docs_30,
        "expiring_certs": expiring,
        "recent_activity": recent,
        "ai_alerts": ai_alerts,
    }


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[SPAIRecommendation]:
    recs: List[SPAIRecommendation] = []

    # Agent 1: Collaboration Monitor — suppliers with no PO acknowledgment > 3 days
    accounts = await list_accounts(db, status=SPAccountStatus.ACTIVE)
    for acct in accounts:
        three_days_ago = _now() - timedelta(days=3)
        recent_pos = list((await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.supplier_id == acct.supplier_id,
                PurchaseOrder.created_at >= three_days_ago - timedelta(days=30),
            ).limit(5)
        )).scalars())
        for po in recent_pos:
            resp = (await db.execute(
                select(SPPOResponse).where(
                    SPPOResponse.account_id == acct.id,
                    SPPOResponse.po_id == po.id,
                )
            )).scalar_one_or_none()
            if not resp and po.created_at and (po.created_at.replace(tzinfo=timezone.utc) < three_days_ago):
                r = SPAIRecommendation(
                    account_id=acct.id,
                    agent_type=SPAIAgentType.COLLABORATION_MONITOR,
                    status=SPAIRecStatus.PENDING,
                    title="PO Acknowledgment Overdue",
                    body=f"PO has not been acknowledged by supplier within 3 days. Follow up required.",
                    severity="WARNING",
                    reference_type="PurchaseOrder",
                    reference_id=str(po.id),
                )
                db.add(r)
                recs.append(r)

    # Agent 2: Friction Assistant — suppliers with low portal activity
    for acct in accounts:
        last_30 = (await db.execute(
            select(func.count(SPActivityLog.id)).where(
                SPActivityLog.account_id == acct.id,
                SPActivityLog.activity_datetime >= _now() - timedelta(days=30),
            )
        )).scalar() or 0
        if last_30 < 3:
            r = SPAIRecommendation(
                account_id=acct.id,
                agent_type=SPAIAgentType.FRICTION_ASSISTANT,
                status=SPAIRecStatus.PENDING,
                title="Low Supplier Portal Adoption",
                body=f"This supplier has had only {last_30} portal interactions in 30 days. Consider onboarding outreach.",
                severity="INFO",
                reference_type="SPAccount",
                reference_id=str(acct.id),
            )
            db.add(r)
            recs.append(r)

    # Agent 3: Risk Signal — expiring compliance docs
    expiring = await list_expiring_docs(db, days=14)
    seen_accounts: set = set()
    for doc in expiring:
        if doc.account_id not in seen_accounts:
            seen_accounts.add(doc.account_id)
            r = SPAIRecommendation(
                account_id=doc.account_id,
                agent_type=SPAIAgentType.RISK_SIGNAL,
                status=SPAIRecStatus.PENDING,
                title="Compliance Document Expiring Soon",
                body=f"Document '{doc.file_name}' ({doc.upload_type}) expires on {doc.expiry_date}. Request renewal immediately.",
                severity="CRITICAL",
                reference_type="SPDocument",
                reference_id=str(doc.id),
            )
            db.add(r)
            recs.append(r)

    await db.flush()
    return recs


async def ack_ai_rec(db: AsyncSession, rec_id: uuid.UUID, payload: SPAIRecAck) -> Optional[SPAIRecommendation]:
    rec = (await db.execute(select(SPAIRecommendation).where(SPAIRecommendation.id == rec_id))).scalar_one_or_none()
    if not rec:
        return None
    rec.status = payload.status
    rec.actioned_by = payload.actioned_by
    rec.actioned_at = _now()
    await db.flush()
    await db.refresh(rec)
    return rec


async def list_ai_recs(db: AsyncSession, account_id: Optional[uuid.UUID] = None) -> List[SPAIRecommendation]:
    q = select(SPAIRecommendation)
    if account_id:
        q = q.where(or_(SPAIRecommendation.account_id == account_id, SPAIRecommendation.account_id == None))
    return list((await db.execute(q.order_by(SPAIRecommendation.created_at.desc()).limit(200))).scalars())


# ── Reports ───────────────────────────────────────────────────────────────────

async def report_po_acknowledgment_time(db: AsyncSession) -> List[dict]:
    responses = list((await db.execute(
        select(SPPOResponse).where(SPPOResponse.responded_at != None)
    )).scalars())
    result = []
    for r in responses:
        po = (await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == r.po_id)
        )).scalar_one_or_none()
        if po and po.created_at and r.responded_at:
            delta = r.responded_at.replace(tzinfo=timezone.utc) - po.created_at.replace(tzinfo=timezone.utc)
            result.append({
                "po_id": str(r.po_id),
                "account_id": str(r.account_id),
                "response_status": r.response_status,
                "response_time_hours": round(delta.total_seconds() / 3600, 1),
            })
    return result


async def report_eta_revisions(db: AsyncSession) -> List[dict]:
    rows = await db.execute(
        select(SPETALog).order_by(SPETALog.created_at.desc()).limit(500)
    )
    return [
        {
            "po_id": str(e.po_id),
            "account_id": str(e.account_id),
            "revision_no": e.revision_no,
            "proposed_date": str(e.proposed_date),
            "eta_status": e.eta_status,
        }
        for e in rows.scalars()
    ]


async def report_adoption(db: AsyncSession) -> List[dict]:
    accounts = await list_accounts(db)
    result = []
    for acct in accounts:
        logins = (await db.execute(
            select(func.count(SPActivityLog.id)).where(
                SPActivityLog.account_id == acct.id,
                SPActivityLog.activity_type == SPActivityType.LOGIN,
            )
        )).scalar() or 0
        doc_uploads = (await db.execute(
            select(func.count(SPDocument.id)).where(SPDocument.account_id == acct.id)
        )).scalar() or 0
        users_count = (await db.execute(
            select(func.count(SPUser.id)).where(SPUser.account_id == acct.id)
        )).scalar() or 0
        result.append({
            "account_id": str(acct.id),
            "portal_status": acct.portal_status,
            "total_logins": logins,
            "document_uploads": doc_uploads,
            "active_users": users_count,
        })
    return result


async def report_not_responding_suppliers(db: AsyncSession) -> List[dict]:
    accounts = await list_accounts(db, status=SPAccountStatus.ACTIVE)
    result = []
    for acct in accounts:
        pending = list((await db.execute(
            select(PurchaseOrder).where(
                PurchaseOrder.supplier_id == acct.supplier_id,
            ).limit(10)
        )).scalars())
        unresponded = 0
        for po in pending:
            resp = (await db.execute(
                select(SPPOResponse).where(
                    SPPOResponse.account_id == acct.id,
                    SPPOResponse.po_id == po.id,
                )
            )).scalar_one_or_none()
            if not resp:
                unresponded += 1
        if unresponded > 0:
            result.append({
                "account_id": str(acct.id),
                "supplier_id": str(acct.supplier_id),
                "unresponded_pos": unresponded,
            })
    return result
