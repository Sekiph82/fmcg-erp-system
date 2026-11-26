"""M50.S01.T001-T004 AI prospecting workspace API. Prefix /api/v1/prospecting-agent.
View: crm.view; run agent / propose outreach / research: crm.edit; settings, import, apply, withdraw: crm.edit_all.
No unauthenticated routes."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.m50_prospecting import (M50AgentRun, M50Candidate, M50EnrichmentProposal, M50Icp, M50IntentAlert,
                                        M50IntentEvent, M50ProviderSetting, M50ResearchDoc)
from app.services import m50_enrichment_service as enr
from app.services import m50_intent_service as intent
from app.services import m50_prospecting_service as agent
from app.services import m50_research_service as rs
from app.services import pat_service as pats

router = APIRouter(dependencies=[Depends(require_any_permission(("crm.view", "crm.view_all", "crm.edit_all")))])
KINDS = ("SEARCH", "ENRICHMENT", "INTENT")


def _can(u, *perms):
    if not (u.is_superuser or has_any_permission(u, perms)):
        raise HTTPException(403, f"Needs {' or '.join(perms)}.")


def _wrap(e: Exception):
    raise HTTPException(getattr(e, "status", 400), str(e))


@router.get("/state")
async def state(db: AsyncSession = Depends(get_db)):
    from app.services.ai_provider import MockProvider, get_ai_provider
    p = get_ai_provider()
    out = {"search": await rs.search_state(db), "enrichment": await enr.status(db), "intent": await intent.status(db),
           "llm": {"mode": "DETERMINISTIC" if isinstance(p, MockProvider) else "LLM", "provider": type(p).__name__}}
    await db.commit()
    return out


class SettingIn(BaseModel):
    provider: Optional[str] = Field(None, max_length=30)
    enabled: bool
    licensed: bool
    license_note: Optional[str] = Field(None, max_length=500)
    retention_days: int = Field(30, ge=1, le=365)
    config: dict = Field(default_factory=dict)


@router.put("/settings/{kind}")
async def put_setting(kind: str, body: SettingIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    kind = kind.upper()
    if kind not in KINDS:
        raise HTTPException(404, "Unknown setting")
    if body.enabled and body.licensed and not (body.license_note or "").strip():
        raise HTTPException(422, "Record the licence / consent basis before enabling.")
    if kind == "ENRICHMENT" and body.provider and body.provider not in enr.PROVIDERS:
        raise HTTPException(422, "Unknown enrichment provider.")
    row = await rs.get_setting(db, kind)
    row.provider, row.enabled, row.licensed = body.provider or row.provider, body.enabled, body.licensed
    row.license_note, row.retention_days, row.config, row.updated_by = body.license_note, body.retention_days, body.config, current_user.username
    pats.audit(db, current_user, "M50_SETTING_CHANGED", "m50_provider_setting", kind,
               {"enabled": body.enabled, "licensed": body.licensed, "provider": row.provider, "retention_days": body.retention_days})
    await db.commit()
    return {"ok": True}


# ── T001 agent ───────────────────────────────────────────────────────────────

class IcpIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    city: Optional[str] = None
    region: Optional[str] = None
    channel: Optional[str] = None
    segment: Optional[str] = None
    size_bands: Optional[list[str]] = None
    keywords: Optional[list[str]] = Field(None, max_length=10)
    competitors: list[str] = Field(default_factory=list, max_length=20)
    use_search: bool = False


@router.post("/icps", status_code=201)
async def create_icp(body: IcpIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit", "crm.edit_all")
    crit = body.model_dump(exclude_none=True, exclude={"name", "competitors", "use_search"})
    if not crit:
        raise HTTPException(422, "Give at least one targeting criterion.")
    icp = M50Icp(name=body.name, criteria=crit, competitors=body.competitors, use_search=body.use_search, created_by=current_user.username)
    db.add(icp)
    pats.audit(db, current_user, "M50_ICP_CREATED", "m50_icp", body.name, {"criteria": crit})
    await db.commit()
    return {"id": str(icp.id)}


@router.get("/icps")
async def list_icps(db: AsyncSession = Depends(get_db)):
    return [{"id": str(i.id), "name": i.name, "criteria": i.criteria, "competitors": i.competitors, "use_search": i.use_search}
            for i in (await db.execute(select(M50Icp).where(M50Icp.archived.is_(False)).order_by(M50Icp.created_at.desc()))).scalars()]


class RunIn(BaseModel):
    icp_id: uuid.UUID
    discovery_queries: list[str] = Field(default_factory=list, max_length=3)


@router.post("/runs", status_code=201)
async def create_run(body: RunIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit", "crm.edit_all")
    icp = await db.get(M50Icp, body.icp_id)
    if icp is None:
        raise HTTPException(404, "ICP not found")
    try:
        r = await agent.run(db, current_user.username, criteria=icp.criteria, competitors=icp.competitors, use_search=icp.use_search,
                            discovery_queries=[q[:200] for q in body.discovery_queries], icp_id=icp.id)
    except agent.AgentError as e:
        _wrap(e)
    pats.audit(db, current_user, "M50_AGENT_RUN", "m50_agent_run", str(r.id), {"icp": icp.name, "mode": r.llm_mode, "search": r.search_state})
    await db.commit()
    return await _run_view(db, r.id)


async def _run_view(db: AsyncSession, rid: uuid.UUID) -> dict:
    r = await db.get(M50AgentRun, rid)
    if r is None:
        raise HTTPException(404, "Run not found")
    cs = (await db.execute(select(M50Candidate).where(M50Candidate.run_id == rid).order_by(M50Candidate.score.desc(), M50Candidate.company_name))).scalars()
    return {"id": str(r.id), "llm_mode": r.llm_mode, "llm_model": r.llm_model, "search_state": r.search_state, "steps": r.steps,
            "criteria": r.criteria, "created_at": r.created_at.isoformat(), "candidates": [agent.cand_view(c) for c in cs]}


@router.get("/runs")
async def list_runs(db: AsyncSession = Depends(get_db)):
    return [{"id": str(r.id), "llm_mode": r.llm_mode, "search_state": r.search_state, "created_at": r.created_at.isoformat(), "criteria": r.criteria}
            for r in (await db.execute(select(M50AgentRun).order_by(M50AgentRun.created_at.desc()).limit(30))).scalars()]


@router.get("/runs/{rid}")
async def get_run(rid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _run_view(db, rid)


class DraftIn(BaseModel):
    subject: Optional[str] = Field(None, max_length=300)
    body: Optional[str] = Field(None, max_length=10000)


@router.post("/candidates/{cid}/draft")
async def candidate_draft(cid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        return await agent.draft_for(db, cid, current_user)
    except agent.AgentError as e:
        _wrap(e)


@router.post("/candidates/{cid}/outreach", status_code=201)
async def candidate_outreach(cid: uuid.UUID, body: DraftIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Never sends: creates an approval request that a different person decides; the outbox applies suppression."""
    _can(current_user, "crm.edit", "crm.edit_all")
    try:
        out = await agent.propose_outreach(db, cid, current_user, body.subject, body.body)
    except agent.AgentError as e:
        _wrap(e)
    await db.commit()
    return out


@router.post("/candidates/{cid}/dismiss")
async def candidate_dismiss(cid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit", "crm.edit_all")
    c = await db.get(M50Candidate, cid)
    if c is None or c.status != "RANKED":
        raise HTTPException(404, "Candidate not found")
    c.status = "DISMISSED"
    pats.audit(db, current_user, "M50_CANDIDATE_DISMISSED", "m50_candidate", str(cid), {})
    await db.commit()
    return {"ok": True}


# ── T002 research ────────────────────────────────────────────────────────────

class SearchIn(BaseModel):
    q: str = Field(min_length=1, max_length=400)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    lang: Optional[str] = Field(None, max_length=10)
    page: int = Field(0, ge=0, le=9)


@router.post("/research/search")
async def research_search(body: SearchIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit", "crm.edit_all")
    try:
        rec = await rs.search(db, body.q, current_user.username, country=body.country, lang=body.lang, page=body.page)
    except rs.ResearchError as e:
        await db.commit()                 # keep the failed-query record
        _wrap(e)
    pats.audit(db, current_user, "M50_RESEARCH_SEARCH", "m50_research_query", str(rec.id), {"q": body.q[:100], "page": body.page})
    await db.commit()
    return {"query_id": str(rec.id), "provider": rec.provider, "page": rec.page, "more_available": rec.more_available,
            "results": rec.results, "expires_at": rec.expires_at.isoformat()}


class FetchIn(BaseModel):
    url: str = Field(min_length=8, max_length=1000)
    query_id: Optional[uuid.UUID] = None


def _doc(d: M50ResearchDoc) -> dict:
    return {"id": str(d.id), "url": d.url, "final_url": d.final_url, "status": d.status, "reason": d.reason, "title": d.title,
            "facts": d.facts, "retrieved_at": d.retrieved_at.isoformat(), "expires_at": d.expires_at.isoformat()}


@router.post("/research/fetch", status_code=201)
async def research_fetch(body: FetchIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit", "crm.edit_all")
    try:
        d = await rs.fetch_and_store(db, body.url, current_user.username, body.query_id)
    except rs.ResearchError as e:
        _wrap(e)
    pats.audit(db, current_user, "M50_RESEARCH_FETCH", "m50_research_doc", str(d.id), {"status": d.status, "reason": d.reason})
    await db.commit()
    return _doc(d)


@router.get("/research/docs")
async def research_docs(db: AsyncSession = Depends(get_db)):
    return [_doc(d) for d in (await db.execute(select(M50ResearchDoc).order_by(M50ResearchDoc.retrieved_at.desc()).limit(50))).scalars()]


class ReconcileIn(BaseModel):
    doc_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)


@router.post("/research/reconcile")
async def research_reconcile(body: ReconcileIn, db: AsyncSession = Depends(get_db)):
    docs = (await db.execute(select(M50ResearchDoc).where(M50ResearchDoc.id.in_(body.doc_ids)))).scalars().all()
    return {"fields": rs.reconcile(list(docs))}


@router.delete("/research/expired")
async def research_purge(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    n = await rs.purge_expired(db)
    pats.audit(db, current_user, "M50_RESEARCH_PURGED", "m50_research", None, {"deleted": n})
    await db.commit()
    return {"deleted": n}


# ── T003 enrichment ──────────────────────────────────────────────────────────

async def _enr_list(db: AsyncSession, cid: uuid.UUID) -> list[dict]:
    from app.models.sales import Customer
    c = await db.get(Customer, cid)
    if c is None:
        raise HTTPException(404, "Customer not found")
    cur = {k: getattr(c, k) for k in enr.APPLY_COLUMNS}
    ps = (await db.execute(select(M50EnrichmentProposal).where(M50EnrichmentProposal.customer_id == cid)
                           .order_by(M50EnrichmentProposal.retrieved_at.desc()))).scalars()
    return [enr.view(p, cur) for p in ps]


@router.post("/enrichment/customers/{cid}/preview")
async def enrich_preview(cid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit", "crm.edit_all")
    try:
        new = await enr.preview(db, cid, current_user.username)
    except enr.EnrichError as e:
        _wrap(e)
    pats.audit(db, current_user, "M50_ENRICHMENT_PREVIEW", "customer", str(cid), {"new_proposals": len(new)})
    await db.commit()
    return {"new": len(new), "proposals": await _enr_list(db, cid)}


@router.get("/enrichment/customers/{cid}")
async def enrich_list(cid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _enr_list(db, cid)


class ApplyIn(BaseModel):
    overwrite: bool = False


@router.post("/enrichment/{pid}/apply")
async def enrich_apply(pid: uuid.UUID, body: ApplyIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    try:
        out = await enr.apply(db, pid, current_user, body.overwrite)
    except enr.EnrichError as e:
        _wrap(e)
    await db.commit()
    return out


@router.post("/enrichment/{pid}/reject")
async def enrich_reject(pid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    try:
        await enr.reject(db, pid, current_user)
    except enr.EnrichError as e:
        _wrap(e)
    await db.commit()
    return {"ok": True}


@router.post("/enrichment/{pid}/revoke")
async def enrich_revoke(pid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    try:
        out = await enr.revoke(db, pid, current_user)
    except enr.EnrichError as e:
        _wrap(e)
    await db.commit()
    return out


@router.delete("/enrichment/customers/{cid}")
async def enrich_purge(cid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    n = await enr.purge(db, customer_id=cid)
    pats.audit(db, current_user, "M50_ENRICHMENT_PURGED", "customer", str(cid), {"deleted": n})
    await db.commit()
    return {"deleted": n}


# ── T004 buyer intent ────────────────────────────────────────────────────────

class ImportIn(BaseModel):
    feed: str = Field(min_length=1, max_length=100)
    consent_basis: str = Field(min_length=3, max_length=300)
    events: list[dict] = Field(min_length=1, max_length=5000)
    mapping: Optional[dict[str, str]] = None


@router.post("/intent/import", status_code=201)
async def intent_import(body: ImportIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    try:
        out = await intent.import_events(db, feed=body.feed, events=body.events, mapping=body.mapping,
                                         consent_basis=body.consent_basis, user=current_user.username)
    except intent.IntentError as e:
        _wrap(e)
    pats.audit(db, current_user, "M50_INTENT_IMPORT", "intent_feed", body.feed, out)
    await db.commit()
    return out


@router.get("/intent/events")
async def intent_events(db: AsyncSession = Depends(get_db)):
    return [{"id": str(e.id), "feed": e.feed, "company_name": e.company_name, "domain": e.domain, "topic": e.topic, "strength": e.strength,
             "observed_at": e.observed_at.isoformat(), "expires_at": e.expires_at.isoformat(), "status": e.status,
             "customer_id": str(e.customer_id) if e.customer_id else None, "match": e.match_method, "match_confidence": e.match_confidence}
            for e in (await db.execute(select(M50IntentEvent).order_by(M50IntentEvent.observed_at.desc()).limit(100))).scalars()]


@router.get("/intent/customers/{cid}")
async def intent_customer(cid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Both scores side by side; they are never added together."""
    return await intent.first_party_and_third_party(db, cid)


@router.get("/intent/alerts")
async def intent_alerts(db: AsyncSession = Depends(get_db)):
    from app.models.sales import Customer
    rows = (await db.execute(select(M50IntentAlert, Customer.name).join(Customer, Customer.id == M50IntentAlert.customer_id)
                             .order_by(M50IntentAlert.created_at.desc()).limit(50))).all()
    return [{"id": str(a.id), "customer_id": str(a.customer_id), "customer": n, "score": a.score, "reasons": a.reasons,
             "created_at": a.created_at.isoformat(), "acknowledged_by": a.acknowledged_by} for a, n in rows]


@router.post("/intent/alerts/{aid}/ack")
async def intent_ack(aid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit", "crm.edit_all")
    from datetime import datetime, timezone
    a = await db.get(M50IntentAlert, aid)
    if a is None:
        raise HTTPException(404, "Alert not found")
    a.acknowledged_by, a.acknowledged_at = current_user.username, datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True}


class WithdrawIn(BaseModel):
    feed: Optional[str] = None
    domain: Optional[str] = None
    company_name: Optional[str] = None


@router.post("/intent/withdraw")
async def intent_withdraw(body: WithdrawIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    try:
        out = await intent.withdraw(db, feed=body.feed, domain=body.domain, company_name=body.company_name, user=current_user)
    except intent.IntentError as e:
        _wrap(e)
    await db.commit()
    return out


@router.delete("/intent/expired")
async def intent_purge(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _can(current_user, "crm.edit_all")
    n = await intent.purge_expired(db)
    pats.audit(db, current_user, "M50_INTENT_PURGED", "intent_feed", None, {"deleted": n})
    await db.commit()
    return {"deleted": n}
