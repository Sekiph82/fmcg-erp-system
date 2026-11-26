"""Shared API for the Outlook and Gmail CRM add-ins (M45.S01.T012, M50.S01.T011). Prefix /api/v1/public/crm-addin.

Auth (M50): sign-in with the ERP's OAuth authorization-code + PKCE flow (addin_auth_service): POST /auth/authorize (signed-in
staff user approves), POST /auth/token (code + verifier -> 15-minute access token + rotating refresh token), /auth/refresh,
/auth/revoke, GET/DELETE /sessions. Requests carry Authorization: Bearer <access token> and X-Addin-Host: gmail|outlook; the host
and (for Outlook) the Origin must match the grant. A personal access token with the crm.addin scope still works (legacy).
The add-in runs as that user: contact visibility and edit rights are the same as in the CRM screens.
Public (token-checked, not session-checked): /auth/token, /auth/refresh, /auth/revoke and the data routes below.
- GET  /lookup?email=        contact, linked deals and recent activities for the open e-mail's sender
- POST /log-email            store the open e-mail (subject + first 2000 characters) as an EMAIL activity on a deal
- POST /note | /task         note or follow-up task on a deal
- GET  /templates            active e-mail templates to insert into a reply
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

import re

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.crm import CRMActivity, CRMActivityType, CRMContact, CRMContactAssociation, CRMRecord
from app.services import crm_contact_service as cs
from app.models.m50_data_sso import AddinGrant
from app.services import addin_auth_service as aas
from app.services import pat_service as pats

router = APIRouter()


def _auth(scope: str):
    async def dep(request: Request, authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
        raw = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
        if raw.startswith("povua_"):
            return await aas.authenticate(db, raw, scope, request.headers.get("x-addin-host"), request.headers.get("origin"))
        return await pats.authenticate(db, authorization, "crm.addin")           # legacy personal access token
    return dep


auth = _auth("addin.read")                     # lookup, templates, thread
write_auth = _auth("addin.write")              # log e-mail, notes, tasks
_TAG = re.compile(r"<[^>]*>")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MSGID = re.compile(r"^[A-Za-z0-9._%+@=/\-]{1,300}$")


def clean(text: str, limit: int) -> str:
    """Mail content is untrusted: no markup, no control characters, bounded. (The ERP UI also renders it as text only.)"""
    return _CTRL.sub("", _TAG.sub("", text or "")).strip()[:limit]
EDIT = ("crm.edit", "crm.edit_all", "crm.edit_own_scope", "crm.edit_own_region")


async def _contact(db, user, email: str) -> Optional[CRMContact]:
    from app.api.v1.endpoints.crm_contacts import _visible
    e = cs.norm_email(email)
    return (await db.execute(_visible(select(CRMContact).where(CRMContact.email == e), user))).scalar_one_or_none()


async def _record(db, user, rid: uuid.UUID) -> CRMRecord:
    rec = await db.get(CRMRecord, rid)
    all_ = user.is_superuser or has_any_permission(user, ("crm.view_all", "crm.edit_all"))
    if rec is None or not (all_ or rec.assigned_rep_id == str(user.id)):
        raise HTTPException(404, "Deal not found")
    return rec


@router.get("/lookup")
async def lookup(email: str = Query(..., min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$"), db: AsyncSession = Depends(get_db), ctx=Depends(auth)):
    user, _ = ctx
    c = await _contact(db, user, str(email))
    if c is None:
        return {"found": False, "email": str(email)}
    rec_ids = list((await db.execute(select(CRMContactAssociation.object_id).where(
        CRMContactAssociation.contact_id == c.id, CRMContactAssociation.object_type == "crm_record"))).scalars())
    all_ = user.is_superuser or has_any_permission(user, ("crm.view_all", "crm.edit_all"))
    recs = [r for r in (await db.execute(select(CRMRecord).where(CRMRecord.id.in_(rec_ids or [uuid.uuid4()])))).scalars()
            if all_ or r.assigned_rep_id == str(user.id)]
    rec_ids = [r.id for r in recs]
    acts = list((await db.execute(select(CRMActivity).where(CRMActivity.crm_record_id.in_(rec_ids or [uuid.uuid4()]))
                                  .order_by(CRMActivity.activity_datetime.desc().nullslast()).limit(5))).scalars())
    await db.commit()
    return {"found": True, "contact": {"id": str(c.id), "name": c.full_name, "job_title": c.job_title, "phone": c.phone,
                                       "lifecycle_stage": c.lifecycle_stage},
            "deals": [{"id": str(r.id), "company": r.company_name, "status": getattr(r.status, "value", r.status),
                       "link": f"/dashboard/crm/records/{r.id}"} for r in recs],
            "recent": [{"type": a.activity_type.value, "subject": a.subject,
                        "at": a.activity_datetime.isoformat() if a.activity_datetime else None} for a in acts]}


class LogIn(BaseModel):
    crm_record_id: uuid.UUID
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field("", max_length=20000)
    direction: Literal["IN", "OUT"] = "IN"
    message_id: Optional[str] = Field(None, max_length=300)   # without <> (the input sanitizer strips tags)
    thread_id: Optional[str] = Field(None, max_length=200)    # Outlook conversationId / Gmail threadId


class NoteIn(BaseModel):
    crm_record_id: uuid.UUID
    text: str = Field(min_length=1, max_length=5000)
    due: Optional[datetime] = None


async def _add(db, user, rec: CRMRecord, kind: CRMActivityType, subject: str, notes: str, due=None,
               outcome: Optional[str] = None) -> dict:
    if not has_any_permission(user, EDIT):
        raise HTTPException(403, "You may not change CRM records.")
    # M48.S01.T023 (audit F5): writes use the pipeline's *edit* scope for this deal, not the view scope
    from app.services.commercial_access_service import ensure_commercial_action_allowed
    ensure_commercial_action_allowed(user, rec, "edit", "crm")
    a = CRMActivity(crm_record_id=rec.id, activity_type=kind, subject=subject[:300], notes=notes,
                    activity_datetime=datetime.utcnow(), due_datetime=due.replace(tzinfo=None) if due else None,
                    created_by=user.username[:50], assigned_to=str(user.id), outcome_code=outcome)
    db.add(a)
    pats.audit(db, user, "CRM_ADDIN_" + kind.value, "crm_record", str(rec.id), {"subject": subject[:100]})
    await db.commit()
    return {"activity_id": str(a.id)}


@router.post("/log-email", status_code=201)
async def log_email(body: LogIn, db: AsyncSession = Depends(get_db), ctx=Depends(write_auth)):
    user, _ = ctx
    if body.message_id and not _MSGID.match(body.message_id):
        raise HTTPException(422, "message_id contains characters that are not allowed.")
    if body.thread_id and not _MSGID.match(body.thread_id):
        raise HTTPException(422, "thread_id contains characters that are not allowed.")
    body.subject, body.body = clean(body.subject, 300) or "(no subject)", clean(body.body, 2000)
    if body.thread_id:
        body.body = f"Thread: {body.thread_id}\n{body.body}"
    rec = await _record(db, user, body.crm_record_id)
    if body.message_id and (await db.execute(select(CRMActivity.id).where(
            CRMActivity.crm_record_id == rec.id, CRMActivity.outcome_code == f"msg:{body.message_id}"[:100]))).first():
        return {"duplicate": True}
    return await _add(db, user, rec, CRMActivityType.EMAIL, ("Received: " if body.direction == "IN" else "Sent: ") + body.subject,
                      body.body[:2000], outcome=f"msg:{body.message_id}"[:100] if body.message_id else None)


@router.post("/note", status_code=201)
async def note(body: NoteIn, db: AsyncSession = Depends(get_db), ctx=Depends(write_auth)):
    user, _ = ctx
    text = clean(body.text, 5000)
    if not text:
        raise HTTPException(422, "The note is empty.")
    return await _add(db, user, await _record(db, user, body.crm_record_id), CRMActivityType.NOTE, text[:80], text)


@router.post("/task", status_code=201)
async def task(body: NoteIn, db: AsyncSession = Depends(get_db), ctx=Depends(write_auth)):
    user, _ = ctx
    text = clean(body.text, 5000)
    if not text:
        raise HTTPException(422, "The task is empty.")
    return await _add(db, user, await _record(db, user, body.crm_record_id), CRMActivityType.TASK, text[:80], text, body.due)


@router.get("/templates")
async def templates(db: AsyncSession = Depends(get_db), ctx=Depends(auth)):
    from app.models.email_integration import EmailTemplate
    await db.commit()
    return [{"id": str(t.id), "name": t.name, "subject": t.subject_template, "body": t.body_template}
            for t in (await db.execute(select(EmailTemplate).where(EmailTemplate.is_active.is_(True))
                                       .order_by(EmailTemplate.name).limit(100))).scalars()]


@router.get("/thread")
async def thread(thread_id: str = Query(..., min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._%+@=/\-]+$"),
                 db: AsyncSession = Depends(get_db), ctx=Depends(auth)):
    """Activities already logged for this mail thread, on deals the user may see."""
    user, _ = ctx
    all_ = user.is_superuser or has_any_permission(user, ("crm.view_all", "crm.edit_all"))
    q = select(CRMActivity, CRMRecord).join(CRMRecord, CRMRecord.id == CRMActivity.crm_record_id).where(
        CRMActivity.notes.like(f"Thread: {thread_id}\n%")).order_by(CRMActivity.activity_datetime.desc().nullslast()).limit(20)
    rows = [(a, r) for a, r in (await db.execute(q)).all() if all_ or r.assigned_rep_id == str(user.id)]
    await db.commit()
    return [{"type": a.activity_type.value, "subject": a.subject, "deal": r.company_name, "deal_id": str(r.id),
             "at": a.activity_datetime.isoformat() if a.activity_datetime else None} for a, r in rows]


@router.get("/whoami")
async def whoami(ctx=Depends(auth)):
    user, g = ctx
    return {"name": user.full_name, "host": getattr(g, "host", None), "scopes": getattr(g, "scopes", ["crm.addin"])}


# ── sign-in (M50.S01.T011) ─────────────────────────────────────────────────────────────────────────────────────

class AuthorizeIn(BaseModel):
    host: Literal["gmail", "outlook"]
    code_challenge: str = Field(min_length=43, max_length=43)
    origin: str = Field(min_length=1, max_length=200)
    scopes: list[str] = Field(default_factory=list)


@router.post("/auth/authorize")
async def authorize(body: AuthorizeIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Staff session (not an add-in token) approves the add-in: returns the one-time code. Prompted by the consent page."""
    out = await aas.authorize(db, current_user, body.host, body.code_challenge, body.origin, body.scopes)
    pats.audit(db, current_user, "CRM_ADDIN_AUTHORIZED", "crm_addin", body.host, {"origin": body.origin, "scopes": out["scopes"]})
    await db.commit()
    return out


class TokenIn(BaseModel):
    code: str = Field(min_length=20, max_length=200)
    code_verifier: str = Field(min_length=43, max_length=128)
    host: Literal["gmail", "outlook"]


@router.post("/auth/token")
async def token(body: TokenIn, db: AsyncSession = Depends(get_db)):
    out = await aas.exchange(db, body.code, body.code_verifier, body.host)
    await db.commit()
    return out


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=200)


@router.post("/auth/refresh")
async def refresh(body: RefreshIn, db: AsyncSession = Depends(get_db)):
    out = await aas.refresh(db, body.refresh_token)
    await db.commit()
    return out


@router.post("/auth/revoke")
async def revoke(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    """The add-in's own sign-out: revokes the grant of the presented access token (idempotent)."""
    raw = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    g = (await db.execute(select(AddinGrant).where(AddinGrant.access_hash == aas.h(raw)))).scalar_one_or_none() if raw else None
    if g is not None:
        await aas.revoke(db, g, "addin_signout")
        await db.commit()
    return {"revoked": g is not None}


def _grant(g: AddinGrant) -> dict:
    return {"id": str(g.id), "host": g.host, "origin": g.origin, "scopes": g.scopes, "created_at": g.created_at.isoformat(),
            "last_used_at": g.last_used_at.isoformat() if g.last_used_at else None, "signed_in": g.access_hash is not None,
            "revoked_at": g.revoked_at.isoformat() if g.revoked_at else None}


@router.get("/sessions")
async def sessions(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    rows = (await db.execute(select(AddinGrant).where(AddinGrant.user_id == current_user.id, AddinGrant.revoked_at.is_(None),
                                                      AddinGrant.access_hash.is_not(None)).order_by(AddinGrant.created_at.desc()).limit(50))).scalars()
    return [_grant(g) for g in rows]


@router.delete("/sessions/{gid}")
async def revoke_session(gid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """The user revokes one of their add-in sessions (a superuser may revoke anyone's, e.g. when someone leaves)."""
    g = await db.get(AddinGrant, gid)
    if g is None or (g.user_id != current_user.id and not current_user.is_superuser):
        raise HTTPException(404, "Session not found")
    await aas.revoke(db, g, "user_revoked" if g.user_id == current_user.id else "admin_revoked")
    pats.audit(db, current_user, "CRM_ADDIN_REVOKED", "crm_addin", str(gid), {"host": g.host})
    await db.commit()
    return _grant(g)
