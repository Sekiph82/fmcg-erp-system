"""Ad platforms (M44.S01.T002–T005, M48.S01.T001–T004). Prefix /api/v1/ads.

Reporting, account list, legacy drafts (never published). M48 campaign builder: provider campaign trees created
paused through the mutation ledger, second-person approval (marketing.approve) bound to budget version + payload hash,
per-account caps and members (admin), fail-closed LIVE/SIMULATED gate (see ads_service.gate)."""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.core.config import settings
from app.core.provider_http import EgressBlocked, egress_mode
from app.models.crm import AdAccount, AdDraft
from app.models.m48_ads import AdAccountControl, AdApproval, AdCampaignNode, AdMutation
from app.services import ads_service as svc
from app.services.ads_adapters import ADAPTERS, LEVEL_LABEL, LEVELS, OBJECTIVES, AdsError

READ = ("marketing.view", "marketing.edit", "crm.view_all", "crm.edit_all")
WRITE = ("marketing.edit", "crm.edit_all")
APPROVE = ("marketing.approve",)
router = APIRouter(dependencies=[Depends(require_any_permission(READ))])
PROVIDER = Field(pattern=r"^(meta|google|linkedin|tiktok)$")
HTTP = {"NOT_CONFIGURED": 503, "AUTH": 502, "PERMISSION": 502, "RATE_LIMIT": 429, "VALIDATION": 422, "VERSION": 502,
        "PROVIDER": 502, "UNKNOWN": 504}


def _w(u) -> None:
    if not (u.is_superuser or has_any_permission(u, WRITE)):
        raise HTTPException(403, "Marketing editors only.")


def _fail(e: Exception):
    if isinstance(e, EgressBlocked):
        raise HTTPException(503, str(e)) from None
    headers = {"Retry-After": str(e.retry_after)} if getattr(e, "retry_after", None) else None
    raise HTTPException(HTTP.get(e.kind, 502), {"kind": e.kind, "detail": str(e)}, headers=headers) from None


def _acct(a: AdAccount) -> dict:
    return {"id": str(a.id), "provider": a.provider, "external_id": a.external_id, "name": a.name, "currency": a.currency,
            "time_zone": a.time_zone, "status": a.status, "last_error": a.last_error,
            "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None}


def _draft(d: AdDraft) -> dict:
    return {"id": str(d.id), "account_id": str(d.account_id), "name": d.name, "objective": d.objective,
            "daily_budget": float(d.daily_budget), "start_date": d.start_date.isoformat() if d.start_date else None,
            "end_date": d.end_date.isoformat() if d.end_date else None, "status": d.status,
            "requested_by": d.requested_by, "approved_by": d.approved_by, "validation": d.validation, "created_by": d.created_by}


@router.get("/providers")
async def providers():
    """live_publishing: the global switches allow LIVE mutations (each account still needs admin activation)."""
    flag, egress = svc.live_flag(), egress_mode()
    return [{"provider": p, "configured": a.configured(), "validate_only": a.supports_validate_only,
             "live_publishing": flag and egress == "live" and a.configured(), "egress": egress, "live_flag": flag,
             "objectives": list(OBJECTIVES[p]), "levels": [{"level": lv, "label": LEVEL_LABEL[p][lv]} for lv in LEVELS[p]],
             "write_tier_ok": p != "linkedin" or settings.LINKEDIN_ADS_ACCESS_TIER == "standard"}
            for p, a in ADAPTERS.items()]


@router.get("/providers/{provider}/accounts")
async def discover(provider: str):
    if provider not in ADAPTERS:
        raise HTTPException(404, "Unknown provider")
    try:
        return await ADAPTERS[provider].accounts()
    except (AdsError, EgressBlocked) as e:
        _fail(e)


class AccountIn(BaseModel):
    provider: str = PROVIDER
    external_id: str = Field(min_length=1, max_length=40, pattern=r"^[0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    time_zone: Optional[str] = Field(None, max_length=64)


@router.get("/accounts")
async def accounts(db: AsyncSession = Depends(get_db)):
    return [_acct(a) for a in (await db.execute(select(AdAccount).order_by(AdAccount.provider, AdAccount.name))).scalars()]


@router.post("/accounts", status_code=201)
async def add_account(body: AccountIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    a = AdAccount(**body.model_dump())
    db.add(a)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(409, "This account is already added.") from None
    return _acct(a)


@router.post("/accounts/{aid}/sync")
async def sync(aid: uuid.UUID, days: int = Query(7, ge=1, le=90), db: AsyncSession = Depends(get_db),
               current_user=Depends(get_current_user)):
    _w(current_user)
    a = await db.get(AdAccount, aid)
    if a is None:
        raise HTTPException(404, "Account not found")
    until = date.today() - timedelta(days=1)
    try:
        res = await svc.sync(db, a, until - timedelta(days=days - 1), until)
    except (AdsError, EgressBlocked) as e:
        await db.commit()                     # keep the account status / error
        _fail(e)
    await db.commit()
    return res


@router.get("/performance")
async def performance(days: int = Query(30, ge=1, le=400), db: AsyncSession = Depends(get_db)):
    return await svc.performance(db, days)


class DraftIn(BaseModel):
    account_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z_]+$")
    daily_budget: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@router.get("/drafts")
async def drafts(db: AsyncSession = Depends(get_db)):
    return [_draft(d) for d in (await db.execute(select(AdDraft).order_by(AdDraft.created_at.desc()))).scalars()]


@router.post("/drafts", status_code=201)
async def create_draft(body: DraftIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    old = (await db.execute(select(AdDraft).where(AdDraft.idempotency_key == body.idempotency_key))).scalar_one_or_none()
    if old is not None:
        return _draft(old)                    # same key → same draft, never a duplicate
    if await db.get(AdAccount, body.account_id) is None:
        raise HTTPException(404, "Account not found")
    try:
        svc.check_guardrail(body.daily_budget)
    except AdsError as e:
        _fail(e)
    d = AdDraft(**body.model_dump(), created_by=current_user.username)
    db.add(d)
    try:
        await db.commit()
    except IntegrityError:                    # a parallel request with the same key won the race
        await db.rollback()
        return _draft((await db.execute(select(AdDraft).where(AdDraft.idempotency_key == body.idempotency_key))).scalar_one())
    return _draft(d)


@router.post("/drafts/{did}/{action}")
async def draft_action(did: uuid.UUID, action: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    d = await db.get(AdDraft, did)
    if d is None:
        raise HTTPException(404, "Draft not found")
    if action == "request":
        if d.status not in ("DRAFT", "REJECTED"):
            raise HTTPException(409, "Already sent for approval.")
        d.status, d.requested_by, d.approved_by = "PENDING", current_user.username, None
    elif action in ("approve", "reject"):
        if d.status != "PENDING":
            raise HTTPException(409, "Nothing waiting for approval.")
        if current_user.username in (d.requested_by, d.created_by):
            raise HTTPException(403, "A second editor must approve.")
        d.status, d.approved_by = ("APPROVED" if action == "approve" else "REJECTED"), current_user.username
    elif action == "validate":
        try:
            await svc.validate_draft(db, d)
        except (AdsError, EgressBlocked) as e:
            _fail(e)
    elif action == "publish":
        raise HTTPException(403, "Legacy drafts are never published. Build the campaign in the campaign builder "
                                 "(/api/v1/ads/campaigns): approval, paused creation and fail-closed live activation.")
    else:
        raise HTTPException(404, "Unknown action")
    await db.commit()
    return _draft(d)


# ── M48.S01.T001–T004 campaign builder ───────────────────────────────────────

SPEC_KEYS = {"meta": {"page_id", "link", "message", "headline", "country", "start_date"},
             "google": {"final_url", "headlines", "descriptions", "cpc_bid", "start_date"},
             "linkedin": {"share_urn", "geo_urn", "unit_cost", "start_date"},
             "tiktok": {"location_ids", "video_id", "identity_id", "ad_text", "landing_page_url", "start_date"}}


def _admin(u) -> None:
    if not u.is_superuser:
        raise HTTPException(403, "Admins only.")


def _refused(e: Exception):
    if isinstance(e, svc.Refused):
        raise HTTPException(e.status, str(e)) from None
    _fail(e)


def _clean_spec(provider: str, spec: dict) -> dict:
    """Whitelisted keys, bounded sizes; semantic checks are in ads_adapters.check_spec."""
    bad = set(spec) - SPEC_KEYS[provider]
    if bad:
        raise HTTPException(422, f"Unsupported fields for {provider}: {', '.join(sorted(bad))}")
    out = {}
    for k, v in spec.items():
        if isinstance(v, list):
            if len(v) > 15 or any(not isinstance(i, (str, int)) or len(str(i)) > 100 for i in v):
                raise HTTPException(422, f"{k}: at most 15 short values.")
            out[k] = [str(i).strip() for i in v]
        elif isinstance(v, (str, int, float)) and len(str(v)) <= 1000:
            out[k] = str(v).strip()
        else:
            raise HTTPException(422, f"{k}: invalid value.")
    if out.get("start_date"):
        try:
            date.fromisoformat(out["start_date"])
        except ValueError:
            raise HTTPException(422, "start_date must be YYYY-MM-DD.") from None
    return out


async def _root(db: AsyncSession, rid: uuid.UUID, user, write: bool = True):
    if write:
        _w(user)
    root = await db.get(AdCampaignNode, rid)
    if root is None or root.root_id is not None:
        raise HTTPException(404, "Campaign not found")
    acct = await db.get(AdAccount, root.account_id)
    try:
        svc.require_member(user, await svc.control(db, acct))
    except svc.Refused as e:
        _refused(e)
    return root, acct


def _actions(root, nodes, aps, muts, g, user, ctrl) -> dict:
    """Each button: None when allowed, otherwise the reason it is disabled."""
    created, any_created = all(n.provider_id for n in nodes), any(n.provider_id for n in nodes)
    editor = user.is_superuser or has_any_permission(user, WRITE)
    approver = user.is_superuser or has_any_permission(user, APPROVE)
    member = user.is_superuser or (ctrl is not None and user.username in (ctrl.members or []))
    pend = [a for a in aps if a.status == "PENDING"]
    ok = {a.action for a in aps if a.status == "APPROVED"}
    unknown = any(m.state in ("UNKNOWN", "PENDING") for m in muts)
    if not member:
        why = "You are not a member of this ad account."
        return {k: why for k in ("validate", "edit", "request_submit", "approve", "submit", "pause", "request_resume",
                                 "resume", "edit_budget", "request_budget", "reconcile")}
    no_edit = None if editor else "Needs marketing.edit."
    caps = None if (ctrl and ctrl.daily_cap is not None and ctrl.monthly_cap is not None) else \
        "An admin must set daily and monthly caps first."
    a = {"validate": no_edit, "edit": no_edit or ("Already on the provider: change the budget instead." if any_created else None),
         "edit_budget": no_edit}
    a["request_submit"] = no_edit or caps or ("Already on the provider." if created else
                                              "Waiting for approval." if any(p.action == "SUBMIT" for p in pend) else
                                              "Already approved." if "SUBMIT" in ok else None)
    if not pend:
        a["approve"] = "Nothing waiting for approval."
    elif not approver:
        a["approve"] = "Needs marketing.approve."
    elif all(user.username in (p.requested_by, root.created_by) for p in pend):
        a["approve"] = "A second person must approve (not the requester or the author)."
    else:
        a["approve"] = None
    if unknown:
        a["submit"] = "An earlier call has an unknown outcome: reconcile first."
    elif not created:
        a["submit"] = no_edit or (None if "SUBMIT" in ok else "Needs an approved submit request.")
    elif root.budget_pushed < root.budget_version:
        a["submit"] = no_edit or (None if "BUDGET" in ok else f"Budget version {root.budget_version} needs approval.")
    else:
        a["submit"] = "Nothing to submit: created and budget is current."
    a["request_budget"] = no_edit or caps or (None if created and root.budget_pushed < root.budget_version and not any(
        p.action == "BUDGET" for p in pend) and "BUDGET" not in ok else "No new budget version waiting to be requested.")
    paused = root.status in ("PAUSED",)
    a["pause"] = no_edit or (None if created and root.status in ("ACTIVE", "RESUME_SENT") else "Only a running campaign can be paused.")
    a["request_resume"] = no_edit or caps or (None if created and paused and "RESUME" not in ok and not any(
        p.action == "RESUME" for p in pend) else "Only a created, paused campaign without a resume request.")
    a["resume"] = no_edit or ("Reconcile first." if unknown else None if created and paused and "RESUME" in ok
                              else "Needs an approved resume request.")
    a["reconcile"] = no_edit or (None if any_created or unknown else "Nothing on the provider yet.")
    if g["mode"] == "LIVE" and root.mode == "SIMULATED" and any_created:
        for k in ("submit", "resume", "pause"):
            a[k] = a[k] or "Created in simulation: start a new campaign for live use."
    return a


async def _tree_out(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, user) -> dict:
    nodes = await svc.nodes_of(db, root)
    ctrl = await svc.control(db, acct)
    g = svc.gate(acct, ctrl)
    aps = (await db.execute(select(AdApproval).where(AdApproval.root_id == root.id).order_by(AdApproval.created_at))).scalars().all()
    muts = (await db.execute(select(AdMutation).where(AdMutation.node_id.in_([n.id for n in nodes]))
                             .order_by(AdMutation.created_at))).scalars().all()
    any_created = any(n.provider_id for n in nodes)
    return {"id": str(root.id), "account_id": str(acct.id), "provider": acct.provider, "currency": acct.currency,
            "name": root.name, "objective": root.objective, "spec": root.spec, "daily_budget": float(root.daily_budget),
            "budget_version": root.budget_version, "budget_pushed": root.budget_pushed, "status": root.status,
            "mode": root.mode if any_created else g["mode"], "transport": svc._tree_transport(nodes, g, root),
            "live_blockers": g["reasons"], "validation": root.validation, "last_error": root.last_error,
            "created_by": root.created_by,
            "nodes": [{"id": str(n.id), "level": n.level, "label": LEVEL_LABEL[acct.provider][n.level], "name": n.name,
                       "provider_name": svc.provider_name(n), "provider_id": n.provider_id,
                       "provider_status": n.provider_status, "status": n.status, "last_error": n.last_error,
                       "last_read_at": n.last_read_at.isoformat() if n.last_read_at else None} for n in nodes],
            "approvals": [{"id": str(a.id), "action": a.action, "budget_version": a.budget_version,
                           "daily_budget": float(a.daily_budget), "hash": a.payload_hash[:12], "status": a.status,
                           "requested_by": a.requested_by, "decided_by": a.decided_by} for a in aps],
            "pending_unknown": sum(m.state in ("UNKNOWN", "PENDING") for m in muts),
            "actions": _actions(root, nodes, aps, muts, g, user, ctrl)}


class ControlIn(BaseModel):
    daily_cap: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    monthly_cap: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    members: list[str] = Field(default_factory=list, max_length=200)


def _ctrl(c: Optional[AdAccountControl], acct: AdAccount) -> dict:
    g = svc.gate(acct, c)
    return {"account_id": str(acct.id), "activated": bool(c and c.activated), "activated_by": c.activated_by if c else None,
            "daily_cap": float(c.daily_cap) if c and c.daily_cap is not None else None,
            "monthly_cap": float(c.monthly_cap) if c and c.monthly_cap is not None else None,
            "members": list(c.members or []) if c else [], "mode": g["mode"], "transport": g["transport"],
            "live_blockers": g["reasons"]}


async def _account_or_404(db: AsyncSession, aid: uuid.UUID) -> AdAccount:
    a = await db.get(AdAccount, aid)
    if a is None:
        raise HTTPException(404, "Account not found")
    return a


@router.get("/accounts/{aid}/controls")
async def get_controls(aid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    a = await _account_or_404(db, aid)
    return _ctrl(await svc.control(db, a), a)


@router.put("/accounts/{aid}/controls")
async def put_controls(aid: uuid.UUID, body: ControlIn, db: AsyncSession = Depends(get_db),
                       current_user=Depends(get_current_user)):
    _admin(current_user)
    a = await _account_or_404(db, aid)
    if body.monthly_cap < body.daily_cap:
        raise HTTPException(422, "The monthly cap cannot be below the daily cap.")
    c = await svc.control(db, a) or AdAccountControl(account_id=a.id, activated=False)
    c.daily_cap, c.monthly_cap = body.daily_cap, body.monthly_cap
    c.members = sorted({m.strip() for m in body.members if m.strip()})[:200]
    db.add(c)
    svc.audit(db, current_user, "ads.account.controls", None, {"account": str(a.id), "daily_cap": str(body.daily_cap),
                                                                 "monthly_cap": str(body.monthly_cap), "members": c.members})
    await db.commit()
    return _ctrl(c, a)


class ActivationIn(BaseModel):
    active: bool


@router.post("/accounts/{aid}/activation")
async def activation(aid: uuid.UUID, body: ActivationIn, db: AsyncSession = Depends(get_db),
                     current_user=Depends(get_current_user)):
    """Admin switch for LIVE mutations on one account. Live still needs PROVIDER_EGRESS=live, ADS_LIVE_MUTATIONS and
    credentials; every change still needs a second-person approval."""
    _admin(current_user)
    from datetime import datetime, timezone
    a = await _account_or_404(db, aid)
    c = await svc.control(db, a) or AdAccountControl(account_id=a.id, members=[])
    c.activated = body.active
    c.activated_by, c.activated_at = current_user.username, datetime.now(timezone.utc)
    db.add(c)
    svc.audit(db, current_user, "ads.account.activation", None, {"account": str(a.id), "active": body.active})
    await db.commit()
    return _ctrl(c, a)


@router.get("/campaigns")
async def campaigns(account_id: Optional[uuid.UUID] = None, db: AsyncSession = Depends(get_db),
                    current_user=Depends(get_current_user)):
    q = select(AdCampaignNode).where(AdCampaignNode.root_id.is_(None)).order_by(AdCampaignNode.created_at.desc()).limit(200)
    if account_id:
        q = q.where(AdCampaignNode.account_id == account_id)
    out = []
    for root in (await db.execute(q)).scalars().all():
        acct = await db.get(AdAccount, root.account_id)
        try:
            svc.require_member(current_user, await svc.control(db, acct))   # only the accounts this user may act on
        except svc.Refused:
            continue
        out.append(await _tree_out(db, root, acct, current_user))
    return out


class CampaignIn(BaseModel):
    account_id: uuid.UUID
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    name: str = Field(min_length=1, max_length=150)
    objective: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z_]+$")
    daily_budget: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    spec: dict = Field(default_factory=dict)


@router.post("/campaigns", status_code=201)
async def create_campaign(body: CampaignIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _w(current_user)
    old = (await db.execute(select(AdCampaignNode).where(AdCampaignNode.idempotency_key == body.idempotency_key))).scalar_one_or_none()
    acct = await _account_or_404(db, body.account_id)
    try:
        svc.require_member(current_user, await svc.control(db, acct))     # cross-account requests refused here
        if old is not None:
            if old.account_id != acct.id:
                raise svc.Refused(409, "This idempotency key belongs to another campaign.")
            return await _tree_out(db, old, acct, current_user)
        root = await svc.create_tree(db, acct, current_user, body.name, body.objective, body.daily_budget,
                                     _clean_spec(acct.provider, body.spec), body.idempotency_key)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        root = (await db.execute(select(AdCampaignNode).where(AdCampaignNode.idempotency_key == body.idempotency_key))).scalar_one()
    except (svc.Refused, AdsError) as e:
        _refused(e)
    return await _tree_out(db, root, acct, current_user)


class CampaignEdit(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    spec: Optional[dict] = None


@router.patch("/campaigns/{rid}")
async def edit_campaign(rid: uuid.UUID, body: CampaignEdit, db: AsyncSession = Depends(get_db),
                        current_user=Depends(get_current_user)):
    root, acct = await _root(db, rid, current_user)
    try:
        await svc.edit_tree(db, root, acct, current_user, body.name,
                            _clean_spec(acct.provider, body.spec) if body.spec is not None else None)
    except (svc.Refused, AdsError) as e:
        _refused(e)
    await db.commit()
    return await _tree_out(db, root, acct, current_user)


class BudgetIn(BaseModel):
    daily_budget: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


@router.post("/campaigns/{rid}/budget")
async def edit_budget(rid: uuid.UUID, body: BudgetIn, db: AsyncSession = Depends(get_db),
                      current_user=Depends(get_current_user)):
    root, acct = await _root(db, rid, current_user)
    try:
        await svc.edit_budget(db, root, acct, await svc.control(db, acct), current_user, body.daily_budget)
    except (svc.Refused, AdsError) as e:
        _refused(e)
    await db.commit()
    return await _tree_out(db, root, acct, current_user)


class ApprovalIn(BaseModel):
    action: str = Field(pattern=r"^(SUBMIT|BUDGET|RESUME)$")


@router.post("/campaigns/{rid}/approvals", status_code=201)
async def request_approval(rid: uuid.UUID, body: ApprovalIn, db: AsyncSession = Depends(get_db),
                           current_user=Depends(get_current_user)):
    root, acct = await _root(db, rid, current_user)
    try:
        await svc.request_approval(db, root, acct, await svc.control(db, acct), current_user, body.action)
    except (svc.Refused, AdsError) as e:
        _refused(e)
    await db.commit()
    return await _tree_out(db, root, acct, current_user)


class DecideIn(BaseModel):
    ok: bool


@router.post("/approvals/{apid}/decide")
async def decide(apid: uuid.UUID, body: DecideIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if not (current_user.is_superuser or has_any_permission(current_user, APPROVE)):
        raise HTTPException(403, "Approvers only (marketing.approve).")
    ap = await db.get(AdApproval, apid)
    if ap is None:
        raise HTTPException(404, "Approval not found")
    root, acct = await _root(db, ap.root_id, current_user, write=False)
    try:
        await svc.decide(db, ap, root, acct, await svc.control(db, acct), current_user, body.ok)
    except (svc.Refused, AdsError) as e:
        await db.commit()                    # keep a stale request marked SUPERSEDED
        _refused(e)
    await db.commit()
    return await _tree_out(db, root, acct, current_user)


@router.post("/campaigns/{rid}/validate")
async def validate_campaign(rid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    root, acct = await _root(db, rid, current_user)
    await svc.validate_tree(db, root, acct)
    await db.commit()
    return await _tree_out(db, root, acct, current_user)


@router.post("/campaigns/{rid}/{action}")
async def campaign_action(rid: uuid.UUID, action: str, db: AsyncSession = Depends(get_db),
                          current_user=Depends(get_current_user)):
    root, acct = await _root(db, rid, current_user)
    fn = {"submit": lambda: svc.submit(db, root, acct, current_user),
          "pause": lambda: svc.set_status(db, root, acct, current_user, False),
          "resume": lambda: svc.set_status(db, root, acct, current_user, True),
          "reconcile": lambda: svc.reconcile(db, root, acct, current_user)}.get(action)
    if fn is None:
        raise HTTPException(404, "Unknown action")
    try:
        await fn()
    except (svc.Refused, AdsError, EgressBlocked) as e:
        await db.commit()
        _refused(e)
    return await _tree_out(db, root, acct, current_user)


@router.get("/campaigns/{rid}/mutations")
async def mutations(rid: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    root, acct = await _root(db, rid, current_user, write=False)
    ids = [n.id for n in await svc.nodes_of(db, root)]
    rows = (await db.execute(select(AdMutation).where(AdMutation.node_id.in_(ids)).order_by(AdMutation.created_at))).scalars()
    return [{"id": str(m.id), "node_id": str(m.node_id), "operation": m.operation, "key": m.idempotency_key,
             "mode": m.mode, "state": m.state, "provider_id": m.provider_id, "attempts": m.attempts, "error": m.error,
             "request": m.request, "response": m.response, "created_by": m.created_by,
             "created_at": m.created_at.isoformat() if m.created_at else None} for m in rows]
