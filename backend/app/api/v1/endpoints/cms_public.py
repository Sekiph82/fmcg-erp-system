"""M46 Content hub — public API (no staff login). Prefix /api/v1/public/cms. Allow-listed in PUBLIC_ROUTES.

- Only live versions of PUBLISHED pages are served; drafts/reviews/archived answer 404.
- Members-only pages and media need the portal realm cookie of an account on the access list (401/403 otherwise).
- Personalized answers are Cache-Control: private, no-store; anonymous answers are public for 60 s.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.cms import CmsCta, CmsMedia, CmsPage, CmsPageVersion, CmsRedirect, CmsSite
from app.services import cms_media_service as media
from app.services import cms_personalize as pz
from app.services import cms_service as cms

router = APIRouter()


async def _site(db: AsyncSession, key: str) -> CmsSite:
    s = await cms.site_by_key(db, key[:40])
    if s is None:
        raise HTTPException(404, "Site not found")
    return s


def _site_public(s: CmsSite) -> dict:
    return {"key": s.key, "name": s.name, "theme": cms.validate_theme(s.theme or {}), "nav": s.nav or [], "locales": s.locales,
            "default_locale": s.default_locale}


def _clean(path: str) -> str:
    p = "/" + "/".join(x for x in (path or "/").split("?")[0].split("/") if x and x not in (".", ".."))
    return p[:400]


@router.get("/site/{key}/page")
async def page(key: str, request: Request, response: Response, path: str = Query("/", max_length=400), locale: Optional[str] = None,
               visitor: Optional[str] = Query(None, max_length=100), db: AsyncSession = Depends(get_db)):
    s = await _site(db, key)
    path = _clean(path)
    loc = locale if locale in (s.locales or []) else s.default_locale
    r = (await db.execute(select(CmsRedirect).where(CmsRedirect.site_id == s.id, CmsRedirect.from_path == path))).scalar_one_or_none()
    if r is not None:
        r.hits += 1
        await db.commit()
        return {"redirect": r.to_path, "code": r.code}
    p, row = await cms.find_live(db, s, path, loc)
    if p is None:
        raise HTTPException(404, "Page not found")
    if p.access == "MEMBERS":
        await media.member_check(db, p.access_list_id, await media.optional_portal_user(request, db))
    v = await db.get(CmsPageVersion, p.live_version_id)
    blocks = v.content.get("blocks", [])
    if row is not None:
        blocks = cms._fill_row(blocks, row)
    who = await pz.visitor(db, visitor, p.locale)
    blocks = pz.personalize(blocks, who)
    blocks, picked = await pz.choose(db, p, blocks, who)
    blocks = await cms.expand(db, s, blocks)
    keys = [b["cta"]["key"] for b in blocks if b.get("cta")]
    if keys:
        await db.execute(update(CmsCta).where(CmsCta.site_id == s.id, CmsCta.key.in_(keys)).values(views=CmsCta.views + 1))
    await db.commit()
    personal = who.personalized or p.access == "MEMBERS" or bool(picked and who.vh)   # per-visitor variant: never shared-cached
    response.headers["Cache-Control"] = "private, no-store" if personal else "public, max-age=60"
    base = cms.base_url(s)
    title = (row.values or {}).get("name") if row is not None else None
    seo = dict(v.content.get("seo") or {})
    if p.access == "MEMBERS":
        seo["noindex"] = True
    return {"site": _site_public(s),
            "page": {"id": str(p.id), "title": title or v.title, "kind": p.kind, "locale": p.locale, "path": path, "author": p.author,
                     "category": p.category, "tags": p.tags or [], "published_at": v.published_at.isoformat(), "version": v.version,
                     "members_only": p.access == "MEMBERS"},
            "blocks": blocks, "seo": seo, "alternates": await cms.alternates(db, s, p), "json_ld": cms.json_ld(s, p, v, blocks, base, row),
            "experiments": picked, "personalized": who.personalized, "canonical": seo.get("canonical") or f"{base}/{p.locale}{'' if path == '/' else path}"}


@router.get("/site/{key}/blog")
async def blog(key: str, locale: Optional[str] = None, category: Optional[str] = Query(None, max_length=80), db: AsyncSession = Depends(get_db)):
    s = await _site(db, key)
    loc = locale if locale in (s.locales or []) else s.default_locale
    q = select(CmsPage, CmsPageVersion).join(CmsPageVersion, CmsPageVersion.id == CmsPage.live_version_id).where(
        CmsPage.site_id == s.id, CmsPage.kind == "POST", CmsPage.status == "PUBLISHED", CmsPage.locale == loc, CmsPage.access == "PUBLIC")
    if category:
        q = q.where(CmsPage.category == category)
    rows = (await db.execute(q.order_by(CmsPageVersion.published_at.desc()).limit(100))).all()
    return {"site": _site_public(s), "posts": [{"title": v.title, "path": p.path, "author": p.author, "category": p.category, "tags": p.tags or [],
            "published_at": v.published_at.isoformat(), "description": (v.content.get("seo") or {}).get("meta_description")} for p, v in rows]}


@router.get("/site/{key}/sitemap.xml")
async def sitemap(key: str, db: AsyncSession = Depends(get_db)):
    return Response(await cms.sitemap(db, await _site(db, key)), media_type="application/xml")


@router.get("/site/{key}/robots.txt")
async def robots(key: str, db: AsyncSession = Depends(get_db)):
    return PlainTextResponse(await cms.robots(db, await _site(db, key)))


class ConvertIn(BaseModel):
    path: str = Field(max_length=400)
    locale: Optional[str] = None
    experiment: str = Field(max_length=40)
    visitor: str = Field(min_length=8, max_length=100)


@router.post("/site/{key}/convert", status_code=202)
async def convert(key: str, b: ConvertIn, db: AsyncSession = Depends(get_db)):
    s = await _site(db, key)
    p, _ = await cms.find_live(db, s, _clean(b.path), b.locale if b.locale in (s.locales or []) else s.default_locale)
    ok = bool(p) and await pz.convert(db, p, b.experiment, b.visitor)
    await db.commit()
    return {"recorded": ok}


@router.post("/site/{key}/cta/{cta_key}/click", status_code=202)
async def cta_click(key: str, cta_key: str, db: AsyncSession = Depends(get_db)):
    s = await _site(db, key)
    await db.execute(update(CmsCta).where(CmsCta.site_id == s.id, CmsCta.key == cta_key[:40]).values(clicks=CmsCta.clicks + 1))
    await db.commit()
    return {"ok": True}


# ── media ─────────────────────────────────────────────────────────────────────

async def _media(db: AsyncSession, media_id: uuid.UUID, request: Request):
    m = await db.get(CmsMedia, media_id)
    if m is None:
        raise HTTPException(404, "Not found")
    user = await media.optional_portal_user(request, db)
    if not m.public:
        await media.member_check(db, m.access_list_id, user)
    return m, user


@router.get("/media/{media_id}")
async def media_meta(media_id: uuid.UUID, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    m, _ = await _media(db, media_id, request)
    response.headers["Cache-Control"] = "public, max-age=60" if m.public else "private, no-store"
    return {"id": str(m.id), "kind": m.kind, "title": m.title, "mime": m.mime, "captions": sorted((m.captions or {}).keys()), "podcast": m.podcast}


@router.get("/media/{media_id}/file")
async def media_file(media_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    m, _ = await _media(db, media_id, request)
    return FileResponse(media.file_path(m), media_type=m.mime,
                        headers={"Cache-Control": "public, max-age=300" if m.public else "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/media/{media_id}/captions/{locale}")
async def media_captions(media_id: uuid.UUID, locale: str, request: Request, db: AsyncSession = Depends(get_db)):
    m, _ = await _media(db, media_id, request)
    vtt = (m.captions or {}).get(locale[:5])
    if vtt is None:
        raise HTTPException(404, "No captions in this language")
    return PlainTextResponse(vtt, media_type="text/vtt", headers={"X-Content-Type-Options": "nosniff"})


class ViewIn(BaseModel):
    seconds: int = Field(0, ge=0, le=86400)
    visitor: str = Field("anonymous", max_length=100)


@router.post("/media/{media_id}/view", status_code=202)
async def media_view(media_id: uuid.UUID, b: ViewIn, request: Request, db: AsyncSession = Depends(get_db)):
    m, user = await _media(db, media_id, request)
    new = await media.record_view(db, m, user, b.visitor, b.seconds)
    await db.commit()
    return {"recorded": new}


@router.get("/podcast/{show}.xml")
async def podcast_feed(show: str, db: AsyncSession = Depends(get_db)):
    """RSS for a public podcast (public episodes only)."""
    from html import escape
    from app.core.config import settings
    eps = (await db.execute(select(CmsMedia).where(CmsMedia.podcast == show[:120], CmsMedia.public.is_(True), CmsMedia.kind == "AUDIO")
                            .order_by(CmsMedia.created_at.desc()).limit(200))).scalars().all()
    if not eps:
        raise HTTPException(404, "No public episodes")
    api = settings.PUBLIC_API_URL.rstrip("/")
    items = "".join(f"<item><title>{escape(e.title)}</title><guid isPermaLink=\"false\">{e.id}</guid>"
                    f"<pubDate>{e.created_at.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>"
                    f"<enclosure url=\"{escape(api)}/api/v1/public/cms/media/{e.id}/file\" length=\"{e.size}\" type=\"{e.mime}\"/></item>" for e in eps)
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{escape(show)}</title>{items}</channel></rss>',
                    media_type="application/rss+xml")
