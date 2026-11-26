"""M51.S01.T003/T004/T005 staff endpoints. Prefix /api/v1/seo-pro.

  GET  /gsc/state  /gsc/connect-url?write=  /gsc/sites  /gsc/snapshots  /gsc/sitemaps  /gsc/sitemaps/status
  POST /gsc/analytics  /gsc/inspect  /gsc/submissions (request)  /gsc/submissions/{id}/decide (second person)
  GET/POST/DELETE /sites           crawl allow-list           POST /crawl, GET /crawls, /crawls/{id}, /crawls/compare
  POST /vitals/lab  /vitals/field  POST /competitor/compare   POST/GET /keywords, GET /keywords/coverage/{crawl}
  GET/POST /aeo/sets, GET /aeo/sets/{id}/state, POST /aeo/sets/{id}/run, GET /aeo/sets/{id}/trend, /aeo/runs/{id}
Read = marketing.view|edit, crm.view_all|edit_all; change/run = marketing.edit, crm.edit_all. Every mutation is audited.
"""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.audit_log import AuditLog
from app.models.m51_seo import (M51AeoAnswer, M51AeoPromptSet, M51AeoRun, M51GscSnapshot, M51GscSubmission, M51Keyword,
                                M51SeoCrawl, M51SeoIssue, M51SeoPage, M51SeoSite)
from app.services import m51_aeo_service as aeo
from app.services import m51_gsc_service as gsc
from app.services import m51_seo_crawler as crawler
from app.services import oauth_service as oauth

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
WRITE = ("marketing.edit", "crm.edit_all")
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])


def _writer(user=Depends(get_current_user)):
    if not has_any_permission(user, WRITE):
        raise HTTPException(403, "Marketing edit permission is required.")
    return user


def _audit(db, user, event: str, target: str, name: str, details: Optional[dict] = None):
    db.add(AuditLog(actor_id=user.id, event_type=event, module="marketing", target_type=target, target_id=None,
                    target_name=name[:200], details=details or {}))


def _err(e):
    return HTTPException(getattr(e, "status", 400), {"code": getattr(e, "code", "error"), "message": str(e)})


# ── T003 Google Search Console ──────────────────────────────────────────────────────────────────

@router.get("/gsc/state")
async def gsc_state(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return await gsc.state(db, user.id)


@router.get("/gsc/connect-url")
async def gsc_connect(write: bool = False, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    try:
        url = await oauth.start(db, user.id, "google", "searchconsole_edit" if write else "searchconsole")
    except oauth.OAuthError as e:
        raise HTTPException(e.status_code, {"code": e.code, "message": str(e)}) from None
    await db.commit()
    return {"authorize_url": url, "scope": "webmasters" if write else "webmasters.readonly"}


async def _conn(db, user, write=False):
    c = await gsc.connection(db, user.id, write=write)
    if c is None:
        raise HTTPException(409, {"code": "not_configured", "message": "NOT_CONFIGURED: connect a Google account for Search Console first."})
    return c


@router.get("/gsc/sites")
async def gsc_sites(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        return await gsc.list_sites(db, await _conn(db, user))
    except gsc.GscError as e:
        raise _err(e) from None


class AnalyticsIn(BaseModel):
    site_url: str = Field(max_length=300)
    start_date: str
    end_date: str
    dimensions: list[str] = Field(default_factory=lambda: ["query"], max_length=5)
    filters: list[dict] = Field(default_factory=list, max_length=10)
    row_limit: int = Field(1000, ge=1, le=25000)
    start_row: int = Field(0, ge=0)
    data_state: Literal["final", "all"] = "final"
    search_type: str = "web"
    paginate: bool = False


@router.post("/gsc/analytics")
async def gsc_analytics(b: AnalyticsIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        body = gsc.build_query(b.start_date, b.end_date, b.dimensions, b.filters, b.row_limit, b.start_row, b.data_state, b.search_type)
        out = await gsc.analytics(db, await _conn(db, user), user.username, b.site_url, body, b.paginate)
    except gsc.GscError as e:
        await db.rollback()
        raise _err(e) from None
    await db.commit()
    return out


@router.get("/gsc/snapshots")
async def gsc_snapshots(limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(M51GscSnapshot).order_by(M51GscSnapshot.fetched_at.desc()).limit(limit))).scalars()
    return [{"id": str(r.id), "site_url": r.site_url, "rows": r.row_count, "source": r.source, "data_state": r.data_state,
             "fetched_at": r.fetched_at.isoformat(), "params": r.params} for r in rows]


@router.get("/gsc/sitemaps")
async def gsc_sitemaps(site_url: str = Query(..., max_length=300), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        return await gsc.sitemaps(db, await _conn(db, user), site_url)
    except gsc.GscError as e:
        raise _err(e) from None


@router.get("/gsc/sitemaps/status")
async def gsc_sitemap_status(site_url: str = Query(..., max_length=300), feedpath: str = Query(..., max_length=1000),
                             db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        return await gsc.sitemap_status(db, await _conn(db, user), site_url, feedpath)
    except gsc.GscError as e:
        raise _err(e) from None


class InspectIn(BaseModel):
    site_url: str = Field(max_length=300)
    url: str = Field(max_length=1000)
    language: str = Field("en-US", max_length=12)


@router.post("/gsc/inspect")
async def gsc_inspect(b: InspectIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        return await gsc.inspect_url(db, await _conn(db, user), b.site_url, b.url, b.language)
    except gsc.GscError as e:
        raise _err(e) from None


class SubmissionIn(BaseModel):
    site_url: str = Field(max_length=300)
    feedpath: str = Field(max_length=1000)


def _sub(r: M51GscSubmission) -> dict:
    return {"id": str(r.id), "site_url": r.site_url, "feedpath": r.feedpath, "status": r.status, "requested_by": r.requested_by,
            "decided_by": r.decided_by, "result": r.result, "source": r.source}


@router.post("/gsc/submissions", status_code=201)
async def request_submission(b: SubmissionIn, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    try:
        row = await gsc.request_submission(db, user.username, b.site_url, b.feedpath)
    except gsc.GscError as e:
        raise _err(e) from None
    _audit(db, user, "SEO_SITEMAP_SUBMISSION_REQUESTED", "m51_gsc_submission", b.feedpath)
    await db.commit()
    return _sub(row)


@router.get("/gsc/submissions")
async def list_submissions(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(M51GscSubmission).order_by(M51GscSubmission.created_at.desc()).limit(50))).scalars()
    return [_sub(r) for r in rows]


class DecideIn(BaseModel):
    approve: bool


@router.post("/gsc/submissions/{sid}/decide")
async def decide_submission(sid: uuid.UUID, b: DecideIn, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    row = await db.get(M51GscSubmission, sid)
    if row is None:
        raise HTTPException(404, "Submission not found")
    try:
        if user.username == row.requested_by:
            raise gsc.GscError(403, "A second person must approve a sitemap submission.", "two_person")
        conn = await _conn(db, user, write=True) if b.approve else None
        await gsc.decide_submission(db, row, user.username, b.approve, conn)
    except gsc.GscError as e:
        raise _err(e) from None
    _audit(db, user, "SEO_SITEMAP_SUBMISSION_" + row.status, "m51_gsc_submission", row.feedpath, {"site": row.site_url})
    await db.commit()
    return _sub(row)


# ── T004 allow-list, crawl, vitals, keywords, competitor ────────────────────────────────────────

class SiteIn(BaseModel):
    origin: str = Field(max_length=300)
    kind: Literal["OWN", "AUTHORIZED_SOURCE"] = "OWN"
    note: Optional[str] = Field(None, max_length=500)
    confirm_authorized: bool = False


@router.get("/sites")
async def list_sites(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(M51SeoSite).order_by(M51SeoSite.origin))).scalars()
    return [{"id": str(r.id), "origin": r.origin, "kind": r.kind, "note": r.note} for r in rows]


@router.post("/sites", status_code=201)
async def add_site(b: SiteIn, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    if not b.confirm_authorized:
        raise HTTPException(422, "Confirm that you own this site or are authorised to audit it.")
    try:
        row = await crawler.add_site(db, b.origin, b.kind, b.note or "", user.username)
    except crawler.CrawlError as e:
        raise _err(e) from None
    _audit(db, user, "SEO_SITE_AUTHORIZED", "m51_seo_site", row.origin, {"kind": row.kind})
    await db.commit()
    return {"id": str(row.id), "origin": row.origin, "kind": row.kind}


@router.delete("/sites/{sid}", status_code=204)
async def remove_site(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    row = await db.get(M51SeoSite, sid)
    if row is None:
        raise HTTPException(404, "Not found")
    _audit(db, user, "SEO_SITE_REMOVED", "m51_seo_site", row.origin)
    await db.delete(row)
    await db.commit()


class CrawlIn(BaseModel):
    origin: str = Field(max_length=300)
    max_pages: Optional[int] = Field(None, ge=1, le=200)


@router.post("/crawl", status_code=201)
async def start_crawl(b: CrawlIn, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    try:
        run = await crawler.crawl(db, b.origin, user.username, b.max_pages)
    except crawler.CrawlError as e:
        raise _err(e) from None
    _audit(db, user, "SEO_CRAWL_RUN", "m51_seo_crawl", run.origin, {"status": run.status})
    await db.commit()
    return _crawl(run)


def _crawl(r: M51SeoCrawl) -> dict:
    return {"id": str(r.id), "origin": r.origin, "status": r.status, "summary": r.summary, "error": r.error,
            "created_at": r.created_at.isoformat() if r.created_at else None}


@router.get("/crawls")
async def list_crawls(origin: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(M51SeoCrawl).order_by(M51SeoCrawl.created_at.desc()).limit(30)
    if origin:
        q = q.where(M51SeoCrawl.origin == origin)
    return [_crawl(r) for r in (await db.execute(q)).scalars()]


@router.get("/crawls/compare")
async def compare_crawls(a: uuid.UUID, b: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ca, cb = await db.get(M51SeoCrawl, a), await db.get(M51SeoCrawl, b)
    if not ca or not cb or ca.origin != cb.origin:
        raise HTTPException(422, "Compare two crawls of the same site.")
    ia = (await db.execute(select(M51SeoIssue).where(M51SeoIssue.crawl_id == a))).scalars().all()
    ib = (await db.execute(select(M51SeoIssue).where(M51SeoIssue.crawl_id == b))).scalars().all()
    return {"before": _crawl(ca), "after": _crawl(cb), **crawler.compare(ia, ib)}


@router.get("/crawls/{cid}")
async def get_crawl(cid: uuid.UUID, severity: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    run = await db.get(M51SeoCrawl, cid)
    if run is None:
        raise HTTPException(404, "Crawl not found")
    q = select(M51SeoIssue).where(M51SeoIssue.crawl_id == cid).order_by(M51SeoIssue.severity, M51SeoIssue.code).limit(1000)
    if severity:
        q = q.where(M51SeoIssue.severity == severity.upper())
    issues = (await db.execute(q)).scalars().all()
    pages = (await db.execute(select(M51SeoPage).where(M51SeoPage.crawl_id == cid).limit(300))).scalars().all()
    return {**_crawl(run), "issues": [{"url": i.url, "code": i.code, "severity": i.severity, "detail": i.detail} for i in issues],
            "pages": [{"url": p.url, "status": p.status, "title": p.data.get("title"), "words": p.data.get("words")} for p in pages]}


class VitalsIn(BaseModel):
    url: str = Field(max_length=1000)
    form_factor: Optional[str] = None
    page: bool = False


@router.post("/vitals/lab")
async def lab_vitals(b: VitalsIn, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    try:
        return await crawler.lab_vitals(db, b.url)
    except (crawler.CrawlError, crawler.FetchBlocked) as e:
        raise _err(e) from None


@router.post("/vitals/field")
async def field_vitals(b: VitalsIn, db: AsyncSession = Depends(get_db)):
    try:
        return await crawler.field_vitals(db, b.url, b.form_factor, b.page)
    except crawler.CrawlError as e:
        raise _err(e) from None


class CompetitorIn(BaseModel):
    own_url: str = Field(max_length=1000)
    competitor_text: Optional[str] = Field(None, max_length=200_000)
    competitor_url: Optional[str] = Field(None, max_length=1000)


@router.post("/competitor/compare")
async def competitor_compare(b: CompetitorIn, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    try:
        return await crawler.compare_content(db, b.own_url, b.competitor_text, b.competitor_url)
    except crawler.CrawlError as e:
        raise _err(e) from None


class KeywordImportIn(BaseModel):
    csv_text: str = Field(max_length=1_000_000)
    source: str = Field(max_length=60)


@router.get("/keywords/providers")
async def keyword_providers():
    return [{"id": "csv", "state": "OK", "columns": list(crawler.KEYWORD_COLUMNS), "required": ["keyword"]},
            {"id": "paid_api", "state": "UNVERIFIED", "reason": "No keyword-data provider API was verified against its documentation; not wired."}]


@router.post("/keywords/import", status_code=201)
async def import_keywords(b: KeywordImportIn, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    try:
        out = await crawler.import_keywords(db, b.csv_text, b.source, user.username)
    except crawler.CrawlError as e:
        raise _err(e) from None
    _audit(db, user, "SEO_KEYWORDS_IMPORTED", "m51_keyword", b.source, {"imported": out["imported"]})
    await db.commit()
    return out


@router.get("/keywords")
async def list_keywords(q: Optional[str] = Query(None, max_length=100), limit: int = Query(100, ge=1, le=500),
                        db: AsyncSession = Depends(get_db)):
    st = select(M51Keyword).order_by(M51Keyword.volume.desc().nullslast()).limit(limit)
    if q:
        st = st.where(M51Keyword.keyword.contains(q.lower()))
    return [{"keyword": k.keyword, "locale": k.locale, "volume": k.volume, "difficulty": k.difficulty, "cpc": k.cpc,
             "intent": k.intent, "source": k.source} for k in (await db.execute(st)).scalars()]


@router.get("/keywords/coverage/{crawl_id}")
async def keyword_coverage(crawl_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await crawler.keyword_coverage(db, crawl_id)


# ── T005 AEO ────────────────────────────────────────────────────────────────────────────────────

class SetIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    locale: Literal["en", "sw", "tr"]
    prompts: list[str] = Field(max_length=20)
    brand_terms: list[str] = Field(max_length=10)
    brand_domains: list[str] = Field(default_factory=list, max_length=10)
    competitor_terms: list[str] = Field(default_factory=list, max_length=20)
    provider: Literal["", "ai_provider", "simulator"] = ""
    samples_per_prompt: int = Field(3, ge=1, le=10)
    max_calls_per_run: int = Field(30, ge=1, le=100)
    consent_confirmed: bool = False


def _set(s: M51AeoPromptSet) -> dict:
    return {"id": str(s.id), "name": s.name, "locale": s.locale, "prompts": s.prompts, "brand_terms": s.brand_terms,
            "brand_domains": s.brand_domains, "competitor_terms": s.competitor_terms, "provider": s.provider or None,
            "samples_per_prompt": s.samples_per_prompt, "max_calls_per_run": s.max_calls_per_run,
            "consent_confirmed": s.consent_confirmed}


@router.get("/aeo/sets")
async def aeo_sets(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(M51AeoPromptSet).where(M51AeoPromptSet.archived.is_(False)).order_by(M51AeoPromptSet.created_at))).scalars()
    return [_set(s) for s in rows]


@router.post("/aeo/sets", status_code=201)
async def aeo_create(b: SetIn, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    try:
        s = await aeo.create_set(db, user.username, b.model_dump())
    except aeo.AeoError as e:
        raise _err(e) from None
    _audit(db, user, "AEO_PROMPT_SET_CREATED", "m51_aeo_set", s.name, {"locale": s.locale, "provider": s.provider})
    await db.commit()
    return _set(s)


async def _get_set(db, sid) -> M51AeoPromptSet:
    s = await db.get(M51AeoPromptSet, sid)
    if s is None or s.archived:
        raise HTTPException(404, "Prompt set not found")
    return s


@router.get("/aeo/sets/{sid}/state")
async def aeo_state(sid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    st = await aeo.state(db, await _get_set(db, sid))
    return {**st, "readiness_note": "Page readiness (structure) is the CMS AEO audit; it is not measured visibility."}


@router.post("/aeo/sets/{sid}/run", status_code=201)
async def aeo_run(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(_writer)):
    s = await _get_set(db, sid)
    try:
        r = await aeo.run(db, s, user.username)
    except aeo.AeoError as e:
        raise _err(e) from None
    _audit(db, user, "AEO_RUN", "m51_aeo_run", s.name, {"calls": r.calls, "source": r.source, "status": r.status})
    await db.commit()
    return _run(r)


def _run(r: M51AeoRun) -> dict:
    return {"id": str(r.id), "set_id": str(r.set_id), "provider": r.provider, "model": r.model, "model_version": r.model_version,
            "source": r.source, "status": r.status, "calls": r.calls, "summary": r.summary, "error": r.error,
            "at": r.created_at.isoformat()}


@router.get("/aeo/sets/{sid}/trend")
async def aeo_trend(sid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_set(db, sid)
    return await aeo.trend(db, sid)


@router.get("/aeo/sets/{sid}/runs")
async def aeo_runs(sid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(M51AeoRun).where(M51AeoRun.set_id == sid).order_by(M51AeoRun.created_at.desc()).limit(30))).scalars()
    return [_run(r) for r in rows]


@router.get("/aeo/runs/{rid}")
async def aeo_run_detail(rid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    r = await db.get(M51AeoRun, rid)
    if r is None:
        raise HTTPException(404, "Run not found")
    ans = (await db.execute(select(M51AeoAnswer).where(M51AeoAnswer.run_id == rid).order_by(M51AeoAnswer.prompt, M51AeoAnswer.sample))).scalars()
    return {**_run(r), "answers": [{"prompt": a.prompt, "sample": a.sample, "brand": a.brand, "brand_cited": a.brand_cited,
                                    "competitors": a.competitors, "citations": a.citations, "answer": a.answer} for a in ans]}
