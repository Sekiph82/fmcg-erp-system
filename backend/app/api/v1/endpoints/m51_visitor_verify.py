"""M51.S01.T009 staff side of visitor verification. Prefix /api/v1/visitor-verification (marketing.edit | crm.edit_all).

  POST /revoke {email}  revoke an address everywhere    POST /purge  delete old challenges
  GET  /outbox          LOCAL outbox (link + code of unused challenges, so a tester can read them; deleted on use/expiry)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import require_any_permission
from app.core.deps import get_current_user, get_db as _staff_db
from app.models.audit_log import AuditLog
from app.models.m51_seo import M51VisitorMailOutbox
from app.services import m51_visitor_verify_service as vv

router = APIRouter(dependencies=[Depends(require_any_permission(("marketing.edit", "crm.edit_all")))])


class AddressIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


@router.post("/revoke")
async def staff_revoke(b: AddressIn, db: AsyncSession = Depends(_staff_db), user=Depends(get_current_user)):
    n = await vv.revoke_address(db, b.email)
    db.add(AuditLog(actor_id=user.id, event_type="VISITOR_VERIFICATION_REVOKED", module="marketing",
                    target_type="web_identity", target_id=None, target_name="address revoked", details={"identities": n}))
    await db.commit()
    return {"revoked_identities": n}


@router.post("/purge")
async def staff_purge(db: AsyncSession = Depends(_staff_db)):
    n = await vv.purge_expired(db)
    await db.commit()
    return {"deleted": n}


@router.get("/outbox")
async def outbox(db: AsyncSession = Depends(_staff_db)):
    rows = (await db.execute(select(M51VisitorMailOutbox).order_by(M51VisitorMailOutbox.created_at.desc()).limit(20))).scalars()
    return [{"to": r.to_email, "subject": r.subject, "body": r.body, "channel": r.channel, "at": r.created_at.isoformat()} for r in rows]

