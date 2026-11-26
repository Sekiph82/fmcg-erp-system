"""Ad platform sync and drafts (M44.S01.T002–T005), on top of `ads_adapters`.

- sync(account, since, until): pulls the platform's daily campaign report and upserts it (re-sync replaces a day,
  so the same window twice gives the same numbers). Auth / permission errors mark the account; rate limits keep the
  data and report the retry time.
- Drafts: idempotency key, budget guardrail (ADS_MAX_DAILY_BUDGET in account currency), second-editor approval,
  validation (platform validate-only where documented, otherwise local rules). Legacy drafts are never published.
- M48 campaign trees (end of file): the provider mutation path with ledger, approvals and fail-closed LIVE gate.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.crm import AdAccount, AdCampaignDay, AdDraft
from app.services.ads_adapters import ADAPTERS, AdsError

MAX_SYNC_DAYS = 90


async def sync(db: AsyncSession, acct: AdAccount, since: date, until: date) -> dict:
    if until < since or (until - since).days > MAX_SYNC_DAYS:
        raise AdsError("VALIDATION", f"Sync window must be 1–{MAX_SYNC_DAYS + 1} days.")
    try:
        rows = await ADAPTERS[acct.provider].report(acct.external_id, since, until)
    except AdsError as e:
        if e.kind in ("AUTH", "PERMISSION"):
            acct.status = "AUTH_FAILED" if e.kind == "AUTH" else "NO_ACCESS"
        acct.last_error = str(e)[:500]
        raise
    for r in rows:
        vals = dict(campaign_name=r.campaign_name[:300], impressions=r.impressions, clicks=r.clicks,
                    spend=r.spend, conversions=r.conversions)
        await db.execute(insert(AdCampaignDay).values(account_id=acct.id, campaign_id=r.campaign_id[:40], day=r.day,
                                                      **vals)
                         .on_conflict_do_update(constraint="uq_ads_campaign_day", set_=vals))
    acct.status, acct.last_error, acct.last_sync_at = "ACTIVE", None, datetime.now(timezone.utc)
    return {"rows": len(rows), "since": since.isoformat(), "until": until.isoformat()}


async def performance(db: AsyncSession, days: int) -> list[dict]:
    since = date.today() - timedelta(days=days)
    q = (select(AdAccount.provider, AdAccount.name, AdAccount.currency, AdCampaignDay.campaign_id,
                func.max(AdCampaignDay.campaign_name), func.sum(AdCampaignDay.impressions), func.sum(AdCampaignDay.clicks),
                func.sum(AdCampaignDay.spend), func.sum(AdCampaignDay.conversions))
         .join(AdAccount, AdAccount.id == AdCampaignDay.account_id).where(AdCampaignDay.day >= since)
         .group_by(AdAccount.provider, AdAccount.name, AdAccount.currency, AdCampaignDay.campaign_id)
         .order_by(func.sum(AdCampaignDay.spend).desc()))
    out = []
    for prov, acct, cur, cid, name, imp, clk, spend, conv in (await db.execute(q)).all():
        imp, clk, spend, conv = int(imp or 0), int(clk or 0), Decimal(spend or 0), Decimal(conv or 0)
        out.append({"provider": prov, "account": acct, "currency": cur, "campaign_id": cid, "campaign": name,
                    "impressions": imp, "clicks": clk, "spend": float(round(spend, 2)), "conversions": float(conv),
                    "ctr": round(clk / imp, 4) if imp else None, "cpc": float(round(spend / clk, 2)) if clk else None,
                    "cost_per_conversion": float(round(spend / conv, 2)) if conv else None})
    return out


def check_guardrail(budget: Decimal) -> None:
    if budget <= 0:
        raise AdsError("VALIDATION", "Daily budget must be positive.")
    if budget > Decimal(str(settings.ADS_MAX_DAILY_BUDGET)):
        raise AdsError("VALIDATION", f"Daily budget above the guardrail ({settings.ADS_MAX_DAILY_BUDGET} in account "
                                     "currency). Raise ADS_MAX_DAILY_BUDGET only with owner approval.")


async def validate_draft(db: AsyncSession, draft: AdDraft) -> dict:
    acct = await db.get(AdAccount, draft.account_id)
    check_guardrail(Decimal(draft.daily_budget))
    if draft.end_date and draft.start_date and draft.end_date < draft.start_date:
        raise AdsError("VALIDATION", "End date is before start date.")
    res = await ADAPTERS[acct.provider].validate(acct.external_id, {"name": draft.name, "objective": draft.objective,
                                                                    "daily_budget": str(draft.daily_budget)}, acct.currency)
    draft.validation = {**res, "at": datetime.now(timezone.utc).isoformat()}
    return draft.validation


# ── M48.S01.T001–T004 campaign trees: approvals, ledger, fail-closed LIVE/SIMULATED ──────────────────────────
# Mode is decided per call, fail-closed:
#   LIVE      only if PROVIDER_EGRESS=live AND ADS_LIVE_MUTATIONS AND an admin activated the account AND the
#             provider credentials are configured. Approval (second person, bound to version + hash) is always needed.
#   SIMULATED otherwise. With PROVIDER_EGRESS=local and credentials set, the real adapter runs against the local
#             simulator ("http"); else nothing is sent and ids are synthetic SIM-… ("offline").
# A tree keeps the mode it was created in: a simulated tree is never pushed live, a live one never simulated.
# Every object is created paused (Meta/Google PAUSED, LinkedIn DRAFT, TikTok DISABLE); resuming is its own approval.

import calendar
import hashlib
import json
import uuid
from contextlib import asynccontextmanager

from sqlalchemy import text

from app.core.provider_http import EgressBlocked, egress_mode
from app.models.m48_ads import AdAccountControl, AdApproval, AdCampaignNode, AdMutation
from app.services.ads_adapters import (BUDGET_LEVEL, BUILDERS, budget_problems, LEVEL_LABEL, LEVELS, STATUS_LEVELS, check_spec,
                                       find_created, send)

COMMITTED = ("PENDING_APPROVAL", "APPROVED", "SUBMITTING", "PARTIAL", "UNKNOWN", "PAUSED", "ACTIVE", "RESUME_SENT")
ACTIVE_WORDS, PAUSED_WORDS = {"ACTIVE", "ENABLED", "ENABLE"}, {"PAUSED", "DISABLE", "DRAFT"}


class Refused(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def audit(db: AsyncSession, user, event: str, target_id, details: dict) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None), event_type=event, module="ads",
                    target_type="ads_campaign", target_id=str(target_id) if target_id else None, details=details))


def live_flag() -> bool:
    """ADS_LIVE_MUTATIONS (bool, default False): settings field, or the environment until the field exists."""
    from app.services.ads_adapters import _setting
    return str(_setting("ADS_LIVE_MUTATIONS")).strip().lower() in ("1", "true", "yes", "on")


def gate(acct: AdAccount, ctrl) -> dict:
    """LIVE only when every switch is on; reasons say exactly which one is off."""
    reasons = []
    mode = egress_mode()
    if mode != "live":
        reasons.append(f"PROVIDER_EGRESS is {mode}, not live.")
    if not live_flag():
        reasons.append("ADS_LIVE_MUTATIONS is off.")
    if not (ctrl and ctrl.activated):
        reasons.append("An admin has not activated this ad account for live changes.")
    configured = ADAPTERS[acct.provider].configured()
    if not configured:
        reasons.append(f"{acct.provider} credentials are not configured.")
    live = not reasons
    return {"mode": "LIVE" if live else "SIMULATED", "reasons": reasons,
            "transport": "http" if live or (mode == "local" and configured) else "offline"}


def tag(n: AdCampaignNode) -> str:
    return f"povu-{n.id.hex[:10]}"


def provider_name(n: AdCampaignNode) -> str:
    """Names sent to the provider carry a unique tag so an UNKNOWN create can be found again by read-back."""
    return f"{n.name[:180]} ({tag(n)})"


async def control(db: AsyncSession, acct: AdAccount):
    return await db.get(AdAccountControl, acct.id)


def require_member(user, ctrl) -> None:
    """Credential-scoped access: only the account's listed members (or a superuser) act on its campaigns."""
    if getattr(user, "is_superuser", False):
        return
    if not ctrl or user.username not in (ctrl.members or []):
        raise Refused(403, "You are not a member of this ad account.")


async def nodes_of(db: AsyncSession, root: AdCampaignNode) -> list[AdCampaignNode]:
    kids = (await db.execute(select(AdCampaignNode).where(AdCampaignNode.root_id == root.id)
                             .order_by(AdCampaignNode.position))).scalars().all()
    return [root, *kids]


def payload_hash(acct: AdAccount, root: AdCampaignNode, nodes: list[AdCampaignNode]) -> str:
    doc = {"account": str(acct.id), "provider": acct.provider, "currency": acct.currency, "objective": root.objective,
           "budget": str(Decimal(root.daily_budget).quantize(Decimal("0.01"))), "version": root.budget_version,
           "spec": root.spec, "nodes": [[n.level, n.name] for n in nodes]}
    return hashlib.sha256(json.dumps(doc, sort_keys=True, default=str).encode()).hexdigest()


def ctx(acct: AdAccount, root: AdCampaignNode, nodes: list[AdCampaignNode], n: AdCampaignNode) -> dict:
    return {"account": acct.external_id, "name": provider_name(n), "tag": tag(n), "objective": root.objective,
            "budget": Decimal(root.daily_budget).quantize(Decimal("0.01")), "currency": acct.currency,
            "spec": root.spec or {}, "ids": {x.level: x.provider_id for x in nodes if x.provider_id}}


async def check_caps(db: AsyncSession, acct: AdAccount, ctrl, root: AdCampaignNode, budget: Decimal) -> None:
    check_guardrail(Decimal(budget))
    if not ctrl or ctrl.daily_cap is None or ctrl.monthly_cap is None:
        raise Refused(409, "An admin must set this account's daily and monthly spend caps first.")
    others = (await db.execute(select(func.coalesce(func.sum(AdCampaignNode.daily_budget), 0)).where(
        AdCampaignNode.account_id == acct.id, AdCampaignNode.root_id.is_(None), AdCampaignNode.id != root.id,
        AdCampaignNode.status.in_(COMMITTED)))).scalar_one()
    total = Decimal(others) + Decimal(budget)
    if total > Decimal(ctrl.daily_cap):
        raise Refused(409, f"Daily budgets on this account would total {total} {acct.currency}, above the daily cap "
                           f"{ctrl.daily_cap}.")
    today = date.today()
    month = total * calendar.monthrange(today.year, today.month)[1]
    if month > Decimal(ctrl.monthly_cap):
        raise Refused(409, f"At most {month} {acct.currency} this month, above the monthly cap {ctrl.monthly_cap}.")


async def create_tree(db: AsyncSession, acct: AdAccount, user, name: str, objective: str, budget: Decimal,
                      spec: dict, key: str) -> AdCampaignNode:
    problems = check_spec(acct.provider, objective, spec, Decimal(budget), acct.currency)
    if problems:
        raise Refused(422, " ".join(problems))
    check_guardrail(Decimal(budget))
    root = AdCampaignNode(account_id=acct.id, level=LEVELS[acct.provider][0], position=0, idempotency_key=key, name=name,
                          objective=objective, spec=spec, daily_budget=budget, created_by=user.username)
    db.add(root)
    await db.flush()
    parent = root
    for i, lv in enumerate(LEVELS[acct.provider][1:], start=1):
        parent = AdCampaignNode(id=uuid.uuid4(), account_id=acct.id, root_id=root.id, parent_id=parent.id, level=lv,
                                position=i, objective=objective, name=f"{name[:160]} – {LEVEL_LABEL[acct.provider][lv]}",
                                created_by=user.username)
        db.add(parent)
    audit(db, user, "ads.campaign.created", root.id, {"provider": acct.provider, "budget": str(budget)})
    return root


async def _supersede(db: AsyncSession, root: AdCampaignNode, actions) -> None:
    for a in (await db.execute(select(AdApproval).where(AdApproval.root_id == root.id, AdApproval.action.in_(actions),
                                                         AdApproval.status.in_(("PENDING", "APPROVED"))))).scalars():
        a.status = "SUPERSEDED"


async def edit_tree(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, user, name, spec) -> None:
    nodes = await nodes_of(db, root)
    if any(n.provider_id for n in nodes):
        raise Refused(409, "Already on the provider: only the budget can be changed here (new version, re-approval).")
    spec = spec if spec is not None else root.spec
    problems = check_spec(acct.provider, root.objective, spec, Decimal(root.daily_budget), acct.currency)
    if problems:
        raise Refused(422, " ".join(problems))
    if name:
        root.name = name
        for n in nodes[1:]:
            n.name = f"{name[:160]} – {LEVEL_LABEL[acct.provider][n.level]}"
    root.spec, root.status = spec, "DRAFT"
    await _supersede(db, root, ("SUBMIT",))
    audit(db, user, "ads.campaign.edited", root.id, {})


async def edit_budget(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, ctrl, user, budget: Decimal) -> None:
    """A budget change is a new version; any approval for the old version stops counting."""
    check_guardrail(Decimal(budget))
    low = budget_problems(acct.provider, Decimal(budget), acct.currency)
    if low:
        raise Refused(422, " ".join(low))
    created = root.provider_id is not None
    old = root.daily_budget
    root.daily_budget, root.budget_version = budget, root.budget_version + 1
    if not created:
        root.status = "DRAFT"
    await _supersede(db, root, ("SUBMIT", "BUDGET", "RESUME"))
    audit(db, user, "ads.campaign.budget_version", root.id, {"from": str(old), "to": str(budget), "version": root.budget_version})


async def request_approval(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, ctrl, user, action: str) -> AdApproval:
    nodes = await nodes_of(db, root)
    created = all(n.provider_id for n in nodes)
    if action == "SUBMIT" and created:
        raise Refused(409, "Already created on the provider.")
    problems = check_spec(acct.provider, root.objective, root.spec or {}, Decimal(root.daily_budget), acct.currency)
    if problems:      # never approve what the provider will refuse (M48.S01.T020)
        raise Refused(422, "Not valid, fix before approval: " + " ".join(problems))
    if action == "BUDGET" and (not created or root.budget_pushed >= root.budget_version):
        raise Refused(409, "No new budget version to send.")
    if action == "RESUME" and (not created or root.status == "ACTIVE"):
        raise Refused(409, "Only a created, paused campaign can be resumed.")
    await check_caps(db, acct, ctrl, root, Decimal(root.daily_budget))
    await _supersede(db, root, (action,))
    ap = AdApproval(root_id=root.id, action=action, budget_version=root.budget_version, daily_budget=root.daily_budget,
                    payload_hash=payload_hash(acct, root, nodes), requested_by=user.username)
    db.add(ap)
    if action == "SUBMIT":
        root.status = "PENDING_APPROVAL"
    audit(db, user, "ads.approval.requested", root.id, {"action": action, "version": root.budget_version})
    return ap


async def decide(db: AsyncSession, ap: AdApproval, root: AdCampaignNode, acct: AdAccount, ctrl, user, ok: bool) -> None:
    if ap.status != "PENDING":
        raise Refused(409, "Nothing waiting for approval.")
    if user.username in (ap.requested_by, root.created_by):
        raise Refused(403, "A second person must approve (not the requester or the author).")
    nodes = await nodes_of(db, root)
    if ap.budget_version != root.budget_version or ap.payload_hash != payload_hash(acct, root, nodes):
        ap.status = "SUPERSEDED"
        raise Refused(409, "The campaign changed after this request: approval refused for a stale version.")
    if ok:
        await check_caps(db, acct, ctrl, root, Decimal(root.daily_budget))
    ap.status, ap.decided_by, ap.decided_at = ("APPROVED" if ok else "REJECTED"), user.username, datetime.now(timezone.utc)
    if ap.action == "SUBMIT":
        root.status = "APPROVED" if ok else "REJECTED"
    audit(db, user, "ads.approval.decided", root.id, {"action": ap.action, "ok": ok, "version": ap.budget_version,
                                                      "hash": ap.payload_hash})


async def _approved(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, nodes, action: str) -> AdApproval:
    ap = (await db.execute(select(AdApproval).where(AdApproval.root_id == root.id, AdApproval.action == action,
                                                     AdApproval.status == "APPROVED")
                           .order_by(AdApproval.created_at.desc()))).scalars().first()
    if ap is None:
        raise Refused(409, f"No approved {action.lower()} request for this campaign.")
    h = payload_hash(acct, root, nodes)
    if ap.budget_version != root.budget_version or ap.payload_hash != h:
        raise Refused(409, f"Approval was for budget version {ap.budget_version}; the campaign is now version "
                           f"{root.budget_version} or its content changed. Request approval again.")
    return ap


CLAIM_GRACE = timedelta(minutes=2)   # a PENDING ledger row younger than this may still be in flight


def _tree_transport(nodes, g: dict, root: Optional[AdCampaignNode] = None) -> str:
    """A LIVE tree always talks to the real provider (http): it is never simulated, even when live changes are
    gated off — then the call is either refused up front or blocked by the egress guard, never faked."""
    if root is not None and root.mode == "LIVE":
        return "http"
    return "offline" if any((n.provider_id or "").startswith("SIM-") for n in nodes) else g["transport"]


@asynccontextmanager
async def root_lock(db: AsyncSession, root: AdCampaignNode):
    """Serialise submit / pause / resume / reconcile on one campaign tree. A PostgreSQL session advisory lock on a
    dedicated connection, so it survives the ledger's intermediate commits (a FOR UPDATE row lock would not)."""
    key = int.from_bytes(root.id.bytes[:8], "big", signed=True)
    bind = db.bind
    if bind is None:
        from app.db.session import engine as bind
    async with bind.connect() as conn:
        got = (await conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key})).scalar()
        await conn.commit()
        if not got:
            raise Refused(409, "Another change to this campaign is in progress; try again shortly.")
        try:
            yield
        finally:
            try:
                await conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
                await conn.commit()
            except BaseException:
                # never return a connection that may still hold the session lock to the pool (review N2)
                await conn.invalidate()
                raise


def _check_mode(root: AdCampaignNode, nodes, g: dict) -> None:
    if not any(n.provider_id for n in nodes):
        return
    if root.mode == "LIVE" and g["mode"] != "LIVE":
        raise Refused(409, "This campaign is live on the provider but live changes are switched off: "
                           + " ".join(g["reasons"]))
    if root.mode == "SIMULATED" and g["mode"] == "LIVE":
        raise Refused(409, "This campaign was created in simulation; create a new campaign for live use.")


async def _mutate(db: AsyncSession, acct: AdAccount, n: AdCampaignNode, op: str, key: str, req, intent: str,
                  mode: str, transport: str, user, parse=None) -> Optional[str]:
    """Ledger-guarded provider mutation. Claim (commit) → call → record. Never re-sends an UNKNOWN outcome."""
    body = {**req.log(), "intent": intent}
    h = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    row = (await db.execute(select(AdMutation).where(AdMutation.idempotency_key == key))).scalar_one_or_none()
    if row is not None:
        if row.request_hash != h:
            raise Refused(409, "This operation was already attempted with a different request.")
        if row.state == "SUCCEEDED":
            return row.provider_id
        if row.state in ("PENDING", "UNKNOWN"):
            raise Refused(409, "The previous attempt has an unknown outcome: reconcile first (never re-sent blindly).")
        row.state, row.attempts, row.error = "PENDING", row.attempts + 1, None      # FAILED: provider refused it
    else:
        row = AdMutation(account_id=acct.id, node_id=n.id, operation=op, idempotency_key=key, request_hash=h, mode=mode,
                         state="PENDING", request=body, created_by=user.username)
        db.add(row)
    await db.commit()                                     # the claim is durable before anything leaves
    if transport == "offline":
        pid, resp = n.provider_id or f"SIM-{n.level}-{n.id.hex[:12]}", {"simulated": True, "sent": False}
    else:
        try:
            out, headers = await send(ADAPTERS[acct.provider], req, safe=False)
        except (AdsError, EgressBlocked) as e:
            unknown = isinstance(e, AdsError) and e.kind == "UNKNOWN"
            row.state, row.error = ("UNKNOWN" if unknown else "FAILED"), str(e)[:500]
            n.last_error = row.error
            await db.commit()
            raise e if isinstance(e, AdsError) else AdsError("PROVIDER", str(e))
        try:
            pid = parse(out, headers) if parse else n.provider_id
        except AdsError as e:                              # 2xx without the id: may exist → reconcile
            row.state = "FAILED" if e.kind == "VALIDATION" else "UNKNOWN"
            row.error, row.response = str(e)[:500], out
            await db.commit()
            if row.state == "UNKNOWN":
                e.kind = "UNKNOWN"
            raise
        resp = out
    row.state, row.provider_id, row.response = "SUCCEEDED", pid, resp
    n.last_error = None
    await db.commit()
    return pid


async def readback(db: AsyncSession, acct: AdAccount, root: AdCampaignNode, nodes) -> dict:
    """Status read-back of every created object (safe reads, retried). Returns {level: parse_read result}."""
    g = gate(acct, await control(db, acct))
    out: dict = {}
    if _tree_transport(nodes, g, root) == "offline":
        for n in nodes:
            if n.provider_id:
                n.provider_status = f"SIMULATED {'ACTIVE' if root.status == 'ACTIVE' else 'PAUSED'}"
        return out
    b = BUILDERS[acct.provider]
    for n in nodes:
        if not n.provider_id:
            continue
        try:
            body, _ = await send(ADAPTERS[acct.provider], b.read(n.level, n.provider_id, ctx(acct, root, nodes, n)), safe=True)
            info = b.parse_read(n.level, body, ctx(acct, root, nodes, n))
            n.provider_status, n.last_read_at = (str(info.get("status") or "")[:60] or None), datetime.now(timezone.utc)
            out[n.level] = info
        except (AdsError, EgressBlocked) as e:
            n.last_error = str(e)[:500]
    return out


def _confirmed_active(provider: str, info: dict) -> bool:
    top = info.get("CAMPAIGN") or {}
    return str(top.get("configured") or "").upper() in ACTIVE_WORDS


async def submit(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, user) -> dict:
    """Create the approved tree (paused) or push an approved new budget version."""
    async with root_lock(db, root):
        await db.refresh(root)
        return await _submit(db, root, acct, user)


async def _submit(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, user) -> dict:
    ctrl = await control(db, acct)
    require_member(user, ctrl)
    nodes = await nodes_of(db, root)
    g = gate(acct, ctrl)
    _check_mode(root, nodes, g)
    b = BUILDERS[acct.provider]
    if not all(n.provider_id for n in nodes):
        ap = await _approved(db, root, acct, nodes, "SUBMIT")
        await check_caps(db, acct, ctrl, root, Decimal(root.daily_budget))
        if not any(n.provider_id for n in nodes):
            root.mode = g["mode"]
        transport = _tree_transport(nodes, g, root)
        root.status = "SUBMITTING"
        audit(db, user, "ads.campaign.submitted", root.id, {"mode": root.mode, "transport": transport,
                                                            "version": root.budget_version})
        await db.commit()
        for n in nodes:
            if n.provider_id:
                continue
            x = ctx(acct, root, nodes, n)
            try:
                pid = await _mutate(db, acct, n, "CREATE", f"{n.id}:CREATE", b.create(n.level, x), "CREATE PAUSED",
                                    root.mode, transport, user, parse=lambda body, h, lv=n.level: b.parse_create(lv, body, h))
            except (AdsError, Refused) as e:
                kind = getattr(e, "kind", "")
                root.status = "UNKNOWN" if kind == "UNKNOWN" else ("PARTIAL" if any(m.provider_id for m in nodes) else "FAILED")
                root.last_error = str(e)[:500]
                await db.commit()
                raise
            n.provider_id, n.status, n.mode = pid, "CREATED", root.mode
            await db.commit()
        ap.status, root.status, root.budget_pushed, root.last_error = "USED", "PAUSED", root.budget_version, None
    elif root.budget_pushed < root.budget_version:
        ap = await _approved(db, root, acct, nodes, "BUDGET")
        await check_caps(db, acct, ctrl, root, Decimal(root.daily_budget))
        n = next(m for m in nodes if m.level == BUDGET_LEVEL[acct.provider])
        await db.commit()
        await _mutate(db, acct, n, "BUDGET", f"{n.id}:BUDGET:v{root.budget_version}", b.budget(n.provider_id, ctx(acct, root, nodes, n)),
                      f"BUDGET v{root.budget_version}", root.mode, _tree_transport(nodes, g, root), user)
        ap.status, root.budget_pushed = "USED", root.budget_version
        audit(db, user, "ads.campaign.budget_pushed", root.id, {"version": root.budget_version})
    else:
        raise Refused(409, "Nothing to submit: the tree is created and the budget is current.")
    await readback(db, acct, root, nodes)
    await db.commit()
    return {"mode": root.mode, "status": root.status}


async def set_status(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, user, active: bool) -> dict:
    """Pause: top object only (fastest stop, no approval). Resume: every object, children first, needs a RESUME approval.
    Pausing a LIVE tree is allowed even when live changes are gated off (it only reduces spend), but only as a real
    provider call: without live egress and credentials it is refused, never recorded as done."""
    async with root_lock(db, root):
        await db.refresh(root)
        return await _set_status(db, root, acct, user, active)


async def _set_status(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, user, active: bool) -> dict:
    ctrl = await control(db, acct)
    require_member(user, ctrl)
    nodes = await nodes_of(db, root)
    if not all(n.provider_id for n in nodes):
        raise Refused(409, "The campaign is not fully created on the provider yet.")
    g = gate(acct, ctrl)
    if root.mode == "LIVE" and g["mode"] != "LIVE":
        if active:
            raise Refused(409, "Live changes are switched off: " + " ".join(g["reasons"]))
        if egress_mode() != "live" or not ADAPTERS[acct.provider].configured():
            raise Refused(409, "Cannot pause this live campaign from here: the provider is unreachable ("
                               + " ".join(r for r in g["reasons"] if "EGRESS" in r or "credentials" in r)
                               + "). Nothing was sent — pause it in the platform's own ads manager now.")
    if root.mode == "SIMULATED" and g["mode"] == "LIVE":
        raise Refused(409, "This campaign was created in simulation; create a new campaign for live use.")
    ap = None
    if active:
        ap = await _approved(db, root, acct, nodes, "RESUME")
        await check_caps(db, acct, ctrl, root, Decimal(root.daily_budget))
    b = BUILDERS[acct.provider]
    targets = [n for n in nodes if n.level in STATUS_LEVELS]
    targets = list(reversed(targets)) if active else targets[:1]
    root.op_seq += 1
    audit(db, user, "ads.campaign.resumed" if active else "ads.campaign.paused", root.id, {"mode": root.mode})
    await db.commit()
    for n in targets:
        await _mutate(db, acct, n, "STATUS", f"{n.id}:STATUS:{root.op_seq}", b.status(n.level, n.provider_id, active,
                      ctx(acct, root, nodes, n)), "ACTIVE" if active else "PAUSED", root.mode,
                      _tree_transport(nodes, g, root), user)
    if ap:
        ap.status = "USED"
    if _tree_transport(nodes, g, root) == "offline":
        root.status = "ACTIVE" if active else "PAUSED"
        await readback(db, acct, root, nodes)
    else:
        info = await readback(db, acct, root, nodes)
        root.status = ("ACTIVE" if _confirmed_active(acct.provider, info) else "RESUME_SENT") if active else "PAUSED"
    await db.commit()
    return {"mode": root.mode, "status": root.status}


async def reconcile(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, user) -> dict:
    """Resolve UNKNOWN / stale PENDING ledger rows by read-back, then refresh every object's provider status.
    A PENDING row younger than CLAIM_GRACE may still be in flight and is left alone (no false FAILED)."""
    async with root_lock(db, root):
        await db.refresh(root)
        return await _reconcile(db, root, acct, user)


async def _reconcile(db: AsyncSession, root: AdCampaignNode, acct: AdAccount, user) -> dict:
    ctrl = await control(db, acct)
    require_member(user, ctrl)
    nodes = await nodes_of(db, root)
    by_id = {n.id: n for n in nodes}
    g = gate(acct, ctrl)
    b = BUILDERS[acct.provider]
    cutoff = datetime.now(timezone.utc) - CLAIM_GRACE
    rows = (await db.execute(select(AdMutation).where(
        AdMutation.node_id.in_(list(by_id)),
        (AdMutation.state == "UNKNOWN") | ((AdMutation.state == "PENDING") & (AdMutation.updated_at < cutoff)))
        .order_by(AdMutation.created_at))).scalars().all()
    in_flight = (await db.execute(select(func.count()).select_from(AdMutation).where(
        AdMutation.node_id.in_(list(by_id)), AdMutation.state == "PENDING", AdMutation.updated_at >= cutoff))).scalar_one()
    resolved = []
    for row in rows:
        n = by_id[row.node_id]
        x = ctx(acct, root, nodes, n)
        if row.operation == "CREATE":
            pid = None if _tree_transport(nodes, g, root) == "offline" else await find_created(acct.provider, n.level, x)
            if pid:
                row.state, row.provider_id = "SUCCEEDED", pid
                n.provider_id, n.status, n.mode = pid, "CREATED", root.mode
            else:
                row.state, row.error = "FAILED", "Not found on read-back: nothing was created, safe to submit again."
        else:
            body, _ = await send(ADAPTERS[acct.provider], b.read(n.level, n.provider_id, x), safe=True)
            info = b.parse_read(n.level, body, x)
            if row.operation == "STATUS":
                want = ACTIVE_WORDS if (row.request or {}).get("intent") == "ACTIVE" else PAUSED_WORDS
                ok = str(info.get("configured") or "").upper() in want
            else:
                ok = info.get("budget_ok") is True
                if ok and root.budget_pushed < root.budget_version:
                    root.budget_pushed = root.budget_version
                    ap = (await db.execute(select(AdApproval).where(AdApproval.root_id == root.id, AdApproval.action == "BUDGET",
                                                                     AdApproval.status == "APPROVED"))).scalars().first()
                    if ap:
                        ap.status = "USED"
            row.state = "SUCCEEDED" if ok else "FAILED"
            row.error = None if ok else "Read-back shows the change was not applied; safe to try again."
        resolved.append({"operation": row.operation, "level": n.level, "state": row.state})
    info = await readback(db, acct, root, nodes)
    if all(n.provider_id for n in nodes):
        if root.status in ("SUBMITTING", "UNKNOWN", "PARTIAL", "FAILED"):
            root.budget_pushed = max(root.budget_pushed, root.budget_version)
            ap = (await db.execute(select(AdApproval).where(AdApproval.root_id == root.id, AdApproval.action == "SUBMIT",
                                                             AdApproval.status == "APPROVED"))).scalars().first()
            if ap:
                ap.status = "USED"
        if info:
            root.status = "ACTIVE" if _confirmed_active(acct.provider, info) else "PAUSED"
        elif root.status not in ("ACTIVE",):
            root.status = "PAUSED"
    elif any(n.provider_id for n in nodes):
        root.status = "PARTIAL"
    elif root.status in ("SUBMITTING", "UNKNOWN") and not in_flight:
        root.status = "FAILED"
    audit(db, user, "ads.campaign.reconciled", root.id, {"resolved": resolved, "in_flight": in_flight})
    await db.commit()
    return {"resolved": resolved, "status": root.status, "in_flight": in_flight}


async def validate_tree(db: AsyncSession, root: AdCampaignNode, acct: AdAccount) -> dict:
    """Local documented-limit checks; plus the provider's own validate-only where one exists (Meta
    execution_options=validate_only on the campaign, Google googleAds:mutate validateOnly over the whole tree).
    LinkedIn and TikTok document none → local only. Validate-only never creates anything."""
    nodes = await nodes_of(db, root)
    problems = check_spec(acct.provider, root.objective, root.spec or {}, Decimal(root.daily_budget), acct.currency)
    try:
        check_guardrail(Decimal(root.daily_budget))
    except AdsError as e:
        problems.append(str(e))
    checked = False
    a = ADAPTERS[acct.provider]
    if not problems and acct.provider in ("meta", "google") and a.configured() and egress_mode() != "off":
        b = BUILDERS[acct.provider]
        x = ctx(acct, root, nodes, root)
        req = (b.create("CAMPAIGN", x, validate_only=True) if acct.provider == "meta"
               else b.validate_tree(x, {n.level: provider_name(n) for n in nodes}))
        try:
            await send(a, req, safe=True)
            checked = True
        except AdsError as e:
            checked = e.kind == "VALIDATION"
            problems.append(str(e))
        except EgressBlocked as e:
            problems.append(f"Provider check skipped: {e}")
    root.validation = {"ok": not problems, "provider_checked": checked, "problems": problems,
                       "at": datetime.now(timezone.utc).isoformat()}
    return root.validation
