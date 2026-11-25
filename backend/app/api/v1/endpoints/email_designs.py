"""Visual e-mail designs (M44.S01.T001). Prefix /api/v1/email-designs.

Marketing/CRM editors write drafts; publishing freezes a version (edits create a new version, campaigns keep the
version they used). Preview renders desktop/mobile-ready HTML with sample or real values; test-send goes through the
normal consent-aware outbox to the signed-in user's own address.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.crm import EmailDesign
from app.services import email_design_service as eds

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
WRITE = ("marketing.edit", "marketing.create", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])
SAMPLE = {"contact_name": "Asha Buyer", "company_name": "POVU Synthetic Outlet", "first_name": "Asha"}


class DesignIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    preheader: Optional[str] = Field(None, max_length=200)
    document: dict[str, Any]


def _out(d: EmailDesign, warnings: Optional[list] = None) -> dict:
    return {"id": str(d.id), "family_id": str(d.family_id), "version": d.version, "name": d.name, "preheader": d.preheader,
            "document": d.document, "status": d.status, "warnings": warnings or []}


def _need_write(u) -> None:
    if not (u.is_superuser or has_any_permission(u, WRITE)):
        raise HTTPException(403, "Marketing editors only.")


def _clean(body: DesignIn) -> tuple[dict, list[str]]:
    try:
        return eds.validate(body.document)
    except (eds.DesignError, ValueError, TypeError) as e:
        raise HTTPException(422, str(e)) from None


@router.get("")
async def list_designs(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(EmailDesign).order_by(EmailDesign.name, EmailDesign.version.desc()))).scalars()
    return [_out(d) for d in rows]


@router.post("", status_code=201)
async def create_design(body: DesignIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_write(current_user)
    doc, warnings = _clean(body)
    d = EmailDesign(family_id=uuid.uuid4(), version=1, name=body.name, preheader=body.preheader, document=doc,
                    status="DRAFT", created_by_id=current_user.id)
    db.add(d)
    await db.commit()
    return _out(d, warnings)


@router.put("/{design_id}")
async def update_design(design_id: uuid.UUID, body: DesignIn, db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    _need_write(current_user)
    d = await db.get(EmailDesign, design_id)
    if d is None:
        raise HTTPException(404, "Design not found")
    if d.status != "DRAFT":
        raise HTTPException(409, "Published designs are frozen; create a new version.")
    d.document, warnings = _clean(body)
    d.name, d.preheader = body.name, body.preheader
    await db.commit()
    return _out(d, warnings)


@router.post("/{design_id}/publish")
async def publish(design_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_write(current_user)
    d = await db.get(EmailDesign, design_id)
    if d is None or d.status != "DRAFT":
        raise HTTPException(409, "Only a draft can be published.")
    for old in (await db.execute(select(EmailDesign).where(EmailDesign.family_id == d.family_id,
                                                           EmailDesign.status == "PUBLISHED"))).scalars():
        old.status = "RETIRED"
    await db.flush()
    d.status = "PUBLISHED"
    await db.commit()
    return _out(d)


@router.post("/{design_id}/new-version", status_code=201)
async def new_version(design_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need_write(current_user)
    d = await db.get(EmailDesign, design_id)
    if d is None:
        raise HTTPException(404, "Design not found")
    top = (await db.execute(select(func.max(EmailDesign.version)).where(EmailDesign.family_id == d.family_id))).scalar_one()
    n = EmailDesign(family_id=d.family_id, version=top + 1, name=d.name, preheader=d.preheader, document=d.document,
                    status="DRAFT", created_by_id=current_user.id)
    db.add(n)
    await db.commit()
    return _out(n)


@router.post("/preview", response_class=HTMLResponse)
async def preview(body: DesignIn):
    """Render an unsaved document with sample values (the editor's live preview)."""
    doc, _ = _clean(body)
    return HTMLResponse(eds.render_html(doc, SAMPLE, body.preheader or ""),
                        headers={"Content-Security-Policy": "default-src 'none'; img-src https: data:; style-src 'unsafe-inline'"})


class SingleSendIn(BaseModel):
    to_email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    subject: str = Field(min_length=1, max_length=300, pattern=r"^[^\r\n]+$")
    values: dict[str, str] = Field(default_factory=dict)
    track_engagement: bool = False


@router.post("/{design_id}/send")
async def single_send(design_id: uuid.UUID, body: SingleSendIn, db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user)):
    """M44.S01.T012 single-send API: one published design to one contact, as marketing mail — marketing consent,
    suppression and the frequency cap apply exactly as for campaigns."""
    _need_write(current_user)
    from app.services import crm_outbound_service as outbound
    d = await db.get(EmailDesign, design_id)
    if d is None or d.status != "PUBLISHED":
        raise HTTPException(422, "Only a published design can be sent.")
    vals = {k: str(v)[:200] for k, v in body.values.items() if k in ("contact_name", "company_name", "first_name", "lifecycle", "channel")}
    msg = await outbound.queue(db, to_email=body.to_email, subject=body.subject, body=eds.render_text(d.document, vals),
                               body_html=eds.render_html(d.document, vals, d.preheader or ""), purpose="CAMPAIGN",
                               dedupe_key=f"single:{d.id}:{uuid.uuid4()}", created_by=current_user.username,
                               track=body.track_engagement)
    await db.commit()
    return {"id": str(msg.id), "status": msg.status, "reason": msg.status_reason}


@router.post("/{design_id}/test-send")
async def test_send(design_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Queue the design to the signed-in user's own address through the normal outbox (consent rules apply)."""
    _need_write(current_user)
    from app.services import crm_outbound_service as outbound
    d = await db.get(EmailDesign, design_id)
    if d is None:
        raise HTTPException(404, "Design not found")
    vals = {**SAMPLE, "contact_name": current_user.full_name, "first_name": current_user.full_name.split(" ")[0]}
    msg = await outbound.queue(db, to_email=current_user.email, subject=f"[Test] {d.name} v{d.version}",
                               body=eds.render_text(d.document, vals), body_html=eds.render_html(d.document, vals, d.preheader or ""),
                               purpose="MANUAL", dedupe_key=f"design-test:{d.id}:{uuid.uuid4()}", created_by=current_user.username)
    await db.commit()
    return {"status": msg.status, "reason": msg.status_reason, "to": current_user.email}
