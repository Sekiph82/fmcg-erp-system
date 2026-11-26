"""M47.S01.T002 lead → customer: a won (or converted) CRM record gets a real Customer so orders, invoices and
attribution follow the lead. Links an existing customer of the same company by e-mail (or a single exact name
match) before creating one. Caller commits."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm import CRMRecord
from app.models.sales import Customer


async def _match(db: AsyncSession, rec: CRMRecord) -> Optional[Customer]:
    same_company = Customer.company_id == rec.company_id if rec.company_id else Customer.company_id.is_(None)
    if rec.contact_email:
        hit = (await db.execute(select(Customer).where(
            func.lower(Customer.email) == rec.contact_email.lower(), same_company, Customer.is_active.is_(True))
            .order_by(Customer.created_at).limit(1))).scalars().first()
        if hit:
            return hit
    named = (await db.execute(select(Customer).where(
        func.lower(Customer.name) == rec.company_name.strip().lower(), same_company, Customer.is_active.is_(True))
        .limit(2))).scalars().all()
    return named[0] if len(named) == 1 else None      # several shops with one name: never guess


async def _code(db: AsyncSession, rec: CRMRecord) -> str:
    base = f"C-{rec.opportunity_code or rec.lead_code or uuid.uuid4().hex[:10].upper()}"[:40]
    code = base
    while (await db.execute(select(Customer.id).where(Customer.code == code))).first():
        code = f"{base}-{uuid.uuid4().hex[:4].upper()}"
    return code


async def ensure_customer(db: AsyncSession, rec: CRMRecord, user: Any = None) -> tuple[Customer, bool]:
    """Return (customer, created). Sets rec.assigned_customer_id."""
    from app.models.audit_log import AuditLog

    if rec.assigned_customer_id:
        cust = await db.get(Customer, rec.assigned_customer_id)
        if cust is not None:
            return cust, False
    cust, created = await _match(db, rec), False
    if cust is None:
        cust = Customer(code=await _code(db, rec), name=rec.company_name.strip(), contact_person=rec.contact_person_name,
                        email=rec.contact_email, phone=rec.contact_phone, currency=rec.currency or "KES",
                        company_id=rec.company_id, branch_id=rec.branch_id, sales_region_id=rec.sales_region_id,
                        sales_team_id=rec.sales_team_id, notes=f"Created from CRM {rec.opportunity_code or rec.lead_code}")
        db.add(cust)
        await db.flush()
        created = True
    rec.assigned_customer_id = cust.id
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None),
                    event_type="crm.customer_created" if created else "crm.customer_linked", module="crm",
                    target_type="crm_record", target_id=str(rec.id),
                    details={"customer_id": str(cust.id), "customer_code": cust.code}))
    return cust, created
