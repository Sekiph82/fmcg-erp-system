"""Public website lead forms (no login). Allow-listed in module_registry.PUBLIC_ROUTES."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.crm import CRMLeadForm
from app.services import crm_lead_capture_service as capture

router = APIRouter()


async def _active_form(db: AsyncSession, slug: str) -> CRMLeadForm:
    if len(slug) > 80:
        raise HTTPException(404, "Form not found")
    form = (await db.execute(select(CRMLeadForm).where(CRMLeadForm.slug == slug))).scalar_one_or_none()
    if form is None or not form.active_flag:
        raise HTTPException(404, "Form not found")
    return form


@router.get("/{slug}")
async def get_public_form(slug: str, db: AsyncSession = Depends(get_db)):
    form = await _active_form(db, slug)
    return {"slug": form.slug, "title": form.title, "intro": form.intro, "consent_text": form.consent_text,
            "require_consent": form.require_consent}


@router.post("/{slug}/submit", status_code=202)
async def submit_public_form(slug: str, body: capture.LeadSubmission, request: Request,
                             db: AsyncSession = Depends(get_db)):
    """Same 202 answer for new, repeat and trapped submissions, so the form reveals nothing about existing leads.
    The per-IP limit uses the connection address: behind a reverse proxy run the API with
    FORWARDED_ALLOW_IPS set to that proxy only, so X-Forwarded-For is trusted from it and nobody else."""
    form = await _active_form(db, slug)
    try:
        await capture.submit(db, form, body, request.client.host if request.client else None)
    except capture.RateLimited:
        raise HTTPException(429, "Too many submissions; please try again later.")
    except capture.ConsentRequired:
        raise HTTPException(422, "Please accept the consent statement to send the form.")
    except capture.MissingField as e:
        raise HTTPException(422, str(e))
    return {"status": "received", "message": form.success_message or "Thank you — we will be in touch."}


class KnownIn(BaseModel):
    visitor: str = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9-]+$")


KNOWN_LIMIT = (30, 600.0)            # lookups per client address per 10 minutes
_known_hits: dict[str, list[float]] = {}


def _known_limit(request: Request) -> None:
    """ponytail: per-process memory window (like cms_public._limit); with several workers each keeps its own window."""
    import time
    key = capture.ip_hash(request.client.host if request.client else "unknown") or "unknown"
    now = time.monotonic()
    recent = [t for t in _known_hits.get(key, []) if t > now - KNOWN_LIMIT[1]]
    if len(recent) >= KNOWN_LIMIT[0]:
        raise HTTPException(429, "Too many requests; please try again later.")
    recent.append(now)
    _known_hits[key] = recent
    if len(_known_hits) > 50_000:            # keep memory bounded
        _known_hits.clear()


@router.post("/{slug}/known")
async def known_fields(slug: str, body: KnownIn, request: Request, db: AsyncSession = Depends(get_db)):
    """M47.S01.T010 form shortening: the names of the fields this form may leave out for this visitor (only names,
    never the stored values). The visitor id travels in the body, not the URL. Rate-limited per client address."""
    _known_limit(request)
    form = await _active_form(db, slug)
    return {"omit": await capture.omitted(db, form, body.visitor)}
