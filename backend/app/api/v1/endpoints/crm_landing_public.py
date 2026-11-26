"""Public landing pages (no login): GET shows the visitor's variant and records one view; POST submits the lead
form and records one conversion for that variant. The visitor id is a random id kept by the browser."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.crm import CRMLeadForm
from app.services import crm_landing_service as lp
from app.services import crm_lead_capture_service as capture

router = APIRouter()
VISITOR = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$")


class ConvertIn(BaseModel):
    visitor: str = VISITOR
    lead: capture.LeadSubmission


async def _resolve(db: AsyncSession, slug: str, visitor: str):
    page = await lp.page_by_slug(db, slug)
    if page is None:
        raise HTTPException(404, "Page not found")
    try:
        variant = lp.assign(page.id, visitor, await lp.variants(db, page.id))
    except ValueError:
        raise HTTPException(404, "Page not found")
    return page, variant


@router.get("/{slug}")
async def show(slug: str, request: Request, visitor: str = Query(..., min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$"),
               db: AsyncSession = Depends(get_db)):
    page, v = await _resolve(db, slug, visitor)
    v = await lp.seen_variant(db, page, visitor) or v          # a returning visitor keeps the variant first shown
    await lp.record(db, page, v, visitor, "VIEW", request.client.host if request.client else None)
    await db.commit()
    form = await db.get(CRMLeadForm, page.lead_form_id)
    return {"slug": page.slug, "variant": v.key, "headline": v.headline, "body": v.body, "cta_label": v.cta_label,
            "consent_text": form.consent_text, "require_consent": form.require_consent}


@router.post("/{slug}/convert", status_code=202)
async def convert(slug: str, body: ConvertIn, request: Request, db: AsyncSession = Depends(get_db)):
    page, _ = await _resolve(db, slug, body.visitor)
    v = await lp.seen_variant(db, page, body.visitor)   # credited to the variant actually shown; no view → not counted
    form = await db.get(CRMLeadForm, page.lead_form_id)
    if form is None or not form.active_flag:
        raise HTTPException(404, "Page not found")
    key = v.key if v else "-"
    lead = body.lead.model_copy(update={"landing_page": f"lp:{page.slug}:{key}", "utm_content": body.lead.utm_content or f"variant-{key}"})
    try:
        sub = await capture.submit(db, form, lead, request.client.host if request.client else None)
    except capture.RateLimited:
        raise HTTPException(429, "Too many submissions; please try again later.")
    except capture.ConsentRequired:
        raise HTTPException(422, "Please accept the consent statement to send the form.")
    except capture.MissingField as e:   # M48.S01.T023 (audit F9): a required field left empty is the visitor's error
        raise HTTPException(422, str(e))
    if v is not None and getattr(sub, "status", None) == "ACCEPTED":   # new, real leads only (not spam or repeats)
        await lp.record(db, page, v, body.visitor, "CONVERT")
    await db.commit()
    return {"status": "received", "message": form.success_message or "Thank you — we will be in touch."}
