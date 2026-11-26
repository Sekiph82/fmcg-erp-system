"""Unified advertising lifecycle (M49.S01.T006) on top of the M48 adapters, ledger, approvals and caps.

Adds what the M48 builder lacked: a cross-account tree, a wizard description, edits after creation (documented updatable
fields only) through the same mutation ledger with a second-person approval bound to the exact change, schedule
read-back with reconciliation, and per-node reporting from the existing performance sync.

Updatable fields, per official docs (checked 2026-11-26):
 Meta  https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group (POST /<id> name),
       .../reference/ad-campaign (ad set start_time / end_time), ad creative: only name (and status, adlabels) after create.
 Google https://developers.google.com/google-ads/api/reference/rpc/v22/Campaign (name, start_date_time, end_date_time with
       updateMask; "yyyy-MM-dd HH:mm:ss" in the account time zone; the old start_date / end_date no longer exist).
 LinkedIn https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns
       (PARTIAL_UPDATE; runSchedule.start is immutable, runSchedule.end is not).
 TikTok https://business-api.tiktok.com/portal/docs (v1.3 /campaign/update/, /adgroup/update/). UNVERIFIED: the ad group
       schedule fields on update (the capability matrix could not read that page); flagged in the UI.
Nothing else is offered for editing (budget keeps its own versioned approval, status its pause / resume approval).
"""
from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.provider_http import EgressBlocked
from app.models.crm import AdAccount, AdCampaignDay
from app.models.m48_ads import AdCampaignNode, AdMutation
from app.models.m49_audiences import AdNodeEdit
from app.services import ads_adapters as ads
from app.services import ads_service as svc
from app.services.ads_adapters import ADAPTERS, BUILDERS, AdsError, Req, send
from app.services.ads_service import Refused

NAME, START, END = "name", "start_date", "end_date"
EDITABLE: dict[str, dict[str, set]] = {
    "meta": {"CAMPAIGN": {NAME}, "ADSET": {NAME, START, END}, "CREATIVE": {NAME}, "AD": {NAME}},
    "google": {"BUDGET": {NAME}, "CAMPAIGN": {NAME, START, END}, "ADSET": {NAME}, "AD": set()},
    "linkedin": {"CAMPAIGN": {NAME, END}, "ADSET": {NAME, END}, "AD": set()},
    "tiktok": {"CAMPAIGN": {NAME}, "ADSET": {NAME, START, END}, "AD": set()}}
UNVERIFIED = {("tiktok", "ADSET", START), ("tiktok", "ADSET", END)}
NOT_EDITABLE = {"linkedin": "LinkedIn runSchedule.start is immutable (only the end date can change).",
                "google": "Responsive search ads carry no name and cannot be edited in place.",
                "tiktok": "TikTok ad (creative) edits are not offered: the ad update body is UNVERIFIED."}
# provider campaign level whose id the existing performance sync reports on
REPORT_LEVEL = {"meta": "CAMPAIGN", "google": "CAMPAIGN", "linkedin": "ADSET", "tiktok": "CAMPAIGN"}
WIZARD_NOT_OFFERED = {
    "meta": "Sales, Leads, App and Engagement objectives need a pixel, catalog, lead form or app: not offered.",
    "google": "YouTube video campaigns cannot be created through the API; Performance Max / Demand Gen need asset groups: not offered.",
    "linkedin": "Lead-gen, video and carousel formats need uploaded assets or forms: not offered.",
    "tiktok": "Sales, App and Lead objectives need pixels or apps (legacy manual flow ends 2027-01-01): not offered."}
FIELDS = {
    "meta": [("page_id", "Facebook Page id", "text", True, "digits only"), ("link", "Link", "url", True, "https://povu-demo.test/allclean"),
             ("message", "Ad text", "text", True, ""), ("headline", "Headline", "text", False, ""),
             ("country", "Country", "text", True, "2 letters, e.g. KE")],
    "google": [("final_url", "Final URL", "url", True, "https"), ("headlines", "Headlines", "list", True, "3-15, each at most 30 characters"),
               ("descriptions", "Descriptions", "list", True, "2-4, each at most 90 characters"), ("cpc_bid", "Max CPC bid", "number", True, "")],
    "linkedin": [("share_urn", "Post URN", "text", True, "urn:li:share:..."), ("geo_urn", "Location URN", "text", True, "urn:li:geo:..."),
                 ("unit_cost", "Bid (unit cost)", "number", True, "")],
    "tiktok": [("location_ids", "Location ids", "list", True, "digits"), ("video_id", "Uploaded video id", "text", True, "asset prerequisite"),
               ("identity_id", "Identity id", "text", True, "asset prerequisite"), ("ad_text", "Ad text", "text", True, "at most 100 characters"),
               ("landing_page_url", "Landing page", "url", True, "https")]}


def wizard() -> list[dict]:
    out = []
    for p in ADAPTERS:
        out.append({"provider": p, "objectives": list(ads.OBJECTIVES[p]),
                    "levels": [{"level": lv, "label": ads.LEVEL_LABEL[p][lv]} for lv in ads.LEVELS[p]],
                    "fields": [{"key": k, "label": l, "kind": t, "required": r, "hint": h} for k, l, t, r, h in FIELDS[p]],
                    "not_offered": WIZARD_NOT_OFFERED[p], "budget_note": ads.budget_note(p, "USD" if p == "linkedin" else "KES"),
                    "editable": {lv: sorted(f) for lv, f in EDITABLE[p].items()}, "editable_note": NOT_EDITABLE.get(p)})
    return out


# ── provider requests ───────────────────────────────────────────────────────

def _d(v: str) -> date:
    try:
        return date.fromisoformat(v)
    except (TypeError, ValueError):
        raise Refused(422, f"'{v}' is not a date (YYYY-MM-DD).") from None


def _ms_end(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000) + 999


def _off(day: str, tz: Optional[str]) -> str:
    """ISO offset of the ad account's own time zone on that day (so the stored date reads back the same); UTC ('Z') when
    the account has no stored zone."""
    try:
        o = datetime.fromisoformat(day + "T12:00:00").replace(tzinfo=ZoneInfo(tz)).strftime("%z") if tz else ""
    except (ValueError, KeyError, ZoneInfoNotFoundError):
        o = ""
    return o or "Z"


def edit_req(provider: str, level: str, pid: str, fields: dict, node: AdCampaignNode, x: dict, li_start: Optional[int] = None) -> Req:
    name = f"{fields[NAME][:180]} ({svc.tag(node)})" if NAME in fields else None     # the tag keeps reconcile-by-name working
    st, en = fields.get(START), fields.get(END)
    if provider == "meta":
        data = {k: v for k, v in {"name": name, "start_time": f"{st}T00:00:00{_off(st, x.get('tz'))}" if st else None,
                                  "end_time": f"{en}T23:59:59{_off(en, x.get('tz'))}" if en else None}.items() if v}
        return Req("POST", ADAPTERS["meta"]._url(pid), data=data)
    if provider == "google":
        b = BUILDERS["google"]
        res = {"resourceName": pid, **{k: v for k, v in {"name": name, "startDateTime": f"{st} 00:00:00" if st else None,
                                                         "endDateTime": f"{en} 23:59:59" if en else None}.items() if v}}
        return Req("POST", ads.ADAPTERS["google"]._url(f"customers/{b._cid(x)}/{b.SVC[level]}:mutate"), json={"operations": [
            {"update": res, "updateMask": ",".join(k for k in res if k != "resourceName")}], "partialFailure": True})
    if provider == "linkedin":
        s = {k: v for k, v in {"name": name}.items() if v}
        if en:
            s["runSchedule"] = {"start": li_start, "end": _ms_end(_d(en))}      # start is immutable: sent back unchanged
        return Req("POST", BUILDERS["linkedin"]._path(level, pid, x), headers=BUILDERS["linkedin"].PATCH, json={"patch": {"$set": s}})
    b = BUILDERS["tiktok"]
    kind = b.KIND[level]
    body = {"advertiser_id": x["account"], f"{kind}_id": pid}
    if name:
        body[f"{kind}_name"] = name
    if st or en:
        body.update({"schedule_type": "SCHEDULE_START_END", "schedule_start_time": f"{st} 00:00:00", "schedule_end_time": f"{en} 23:59:59"})
    return Req("POST", b._url(f"{kind}/update/"), json=body)


def read_req(provider: str, level: str, pid: str, x: dict) -> Req:
    if provider == "meta":
        f = "id,name" if level == "CREATIVE" else "id,name,status,effective_status" + (",start_time,end_time" if level == "ADSET" else "")
        return Req("GET", ADAPTERS["meta"]._url(pid), params={"fields": f})
    if provider == "google":
        b = BUILDERS["google"]
        r = b.GAQL[level]
        extra = f", {r}.start_date_time, {r}.end_date_time" if level == "CAMPAIGN" else ""
        return b._search(x, f"SELECT {r}.resource_name, {r}.name{extra} FROM {r} WHERE {r}.resource_name = '{pid}'")
    return BUILDERS[provider].read(level, pid, x)


def _day_ms(ms) -> Optional[str]:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).date().isoformat() if ms else None


def observed(provider: str, level: str, body: dict) -> dict:
    """Name and schedule dates as the provider reports them (YYYY-MM-DD or None)."""
    if provider == "meta":
        return {NAME: body.get("name"), START: (body.get("start_time") or "")[:10] or None, END: (body.get("end_time") or "")[:10] or None}
    if provider == "google":
        row = ((body.get("results") or [{}])[0]).get(BUILDERS["google"].KEY[level]) or {}
        return {NAME: row.get("name"), START: (row.get("startDateTime") or "")[:10] or None, END: (row.get("endDateTime") or "")[:10] or None}
    if provider == "linkedin":
        rs = body.get("runSchedule") or {}
        return {NAME: body.get("name"), START: _day_ms(rs.get("start")), END: _day_ms(rs.get("end"))}
    row = (body.get("list") or [{}])[0]
    return {NAME: row.get("adgroup_name") or row.get("campaign_name") or row.get("ad_name"),
            START: (row.get("schedule_start_time") or "")[:10] or None, END: (row.get("schedule_end_time") or "")[:10] or None}


def compare(want: dict, seen: dict, node: AdCampaignNode) -> list[str]:
    diffs = []
    for k, v in want.items():
        exp = f"{v[:180]} ({svc.tag(node)})" if k == NAME else v
        if seen.get(k) != exp:
            diffs.append(f"{k}: wanted {exp}, provider reports {seen.get(k)}")
    return diffs


# ── flows ───────────────────────────────────────────────────────────────────

def _hash(node: AdCampaignNode, fields: dict) -> str:
    return hashlib.sha256(json.dumps({"node": str(node.id), "fields": fields}, sort_keys=True).encode()).hexdigest()


async def request_edit(db: AsyncSession, node: AdCampaignNode, root: AdCampaignNode, acct: AdAccount, user, fields: dict) -> AdNodeEdit:
    svc.require_member(user, await svc.control(db, acct))
    allowed = EDITABLE[acct.provider][node.level]
    clean = {k: str(v).strip() for k, v in (fields or {}).items() if v not in (None, "")}
    if not clean:
        raise Refused(422, "Nothing to change.")
    bad = set(clean) - allowed
    if bad:
        raise Refused(422, f"{', '.join(sorted(bad))} cannot be edited on a {ads.LEVEL_LABEL[acct.provider][node.level]} after creation "
                           f"(documented updatable fields: {', '.join(sorted(allowed)) or 'none'}). {NOT_EDITABLE.get(acct.provider, '')}")
    if not node.provider_id:
        raise Refused(409, "Not on the provider yet: edit the draft in the campaign builder instead.")
    if NAME in clean and not 1 <= len(clean[NAME]) <= 150:
        raise Refused(422, "Name must be 1-150 characters.")
    for k in (START, END):
        if k in clean:
            _d(clean[k])
    if START in clean and END in clean and _d(clean[END]) < _d(clean[START]):
        raise Refused(422, "End date is before start date.")
    if acct.provider == "tiktok" and node.level == "ADSET" and (START in clean) != (END in clean):
        raise Refused(422, "TikTok ad group schedule needs both a start and an end date.")
    for old in (await db.execute(select(AdNodeEdit).where(AdNodeEdit.node_id == node.id, AdNodeEdit.status.in_(("PENDING_APPROVAL", "APPROVED"))))).scalars():
        old.status = "SUPERSEDED"
    e = AdNodeEdit(root_id=root.id, node_id=node.id, fields=clean, payload_hash=_hash(node, clean), requested_by=user.username)
    db.add(e)
    await db.flush()
    svc.audit(db, user, "ads.edit.requested", root.id, {"node": str(node.id), "fields": clean})
    return e


async def decide_edit(db: AsyncSession, e: AdNodeEdit, node: AdCampaignNode, root: AdCampaignNode, acct: AdAccount, user, ok: bool) -> None:
    if e.status != "PENDING_APPROVAL":
        raise Refused(409, "Nothing waiting for approval.")
    if user.username in (e.requested_by, root.created_by):
        raise Refused(403, "A second person must approve (not the requester or the author).")
    svc.require_member(user, await svc.control(db, acct))
    if e.payload_hash != _hash(node, e.fields):
        e.status = "SUPERSEDED"
        raise Refused(409, "The change no longer matches what was requested.")
    e.status, e.decided_by, e.decided_at = ("APPROVED" if ok else "REJECTED"), user.username, datetime.now(timezone.utc)
    svc.audit(db, user, "ads.edit.decided", root.id, {"edit": str(e.id), "ok": ok})


async def _read(db, acct, root, nodes, node) -> dict:
    x = svc.ctx(acct, root, nodes, node)
    body, _ = await send(ADAPTERS[acct.provider], read_req(acct.provider, node.level, node.provider_id, x), safe=True)
    return observed(acct.provider, node.level, body)


async def apply_edit(db: AsyncSession, e: AdNodeEdit, node: AdCampaignNode, root: AdCampaignNode, acct: AdAccount, user) -> dict:
    async with svc.root_lock(db, root):
        await db.refresh(root)
        return await _apply(db, e, node, root, acct, user)


async def _apply(db, e: AdNodeEdit, node, root, acct, user) -> dict:
    ctrl = await svc.control(db, acct)
    svc.require_member(user, ctrl)
    nodes = await svc.nodes_of(db, root)
    g = svc.gate(acct, ctrl)
    svc._check_mode(root, nodes, g)
    if e.status not in ("APPROVED", "FAILED"):
        raise Refused(409, "No approved edit." if e.status != "UNKNOWN" else "The previous attempt has an unknown outcome: reconcile first.")
    if e.payload_hash != _hash(node, e.fields):
        raise Refused(409, "The change no longer matches the approval.")
    transport = svc._tree_transport(nodes, g, root)
    x = {**svc.ctx(acct, root, nodes, node), "tz": acct.time_zone}
    li_start = None
    try:
        if acct.provider == "linkedin" and END in e.fields and transport != "offline":
            li_start = ((await send(ADAPTERS["linkedin"], BUILDERS["linkedin"].read(node.level, node.provider_id, x), safe=True))[0]
                        .get("runSchedule") or {}).get("start")
            if not li_start:
                raise AdsError("VALIDATION", "LinkedIn did not report runSchedule.start, which an end-date change must send back.")
        req = edit_req(acct.provider, node.level, node.provider_id, e.fields, node, x, li_start)
        e.mode, e.attempts = root.mode, e.attempts + 1
        await db.commit()
        await svc._mutate(db, acct, node, "EDIT", f"{e.id}:EDIT", req, "EDIT " + ",".join(sorted(e.fields)), root.mode, transport, user)
    except (AdsError, EgressBlocked, Refused) as ex:
        if not isinstance(ex, Refused):
            e.status = "UNKNOWN" if getattr(ex, "kind", "") == "UNKNOWN" else "FAILED"
        e.last_error = str(ex)[:500]
        await db.commit()
        raise
    if NAME in e.fields:
        node.name = e.fields[NAME]
        if node.level == root.level and node.id == root.id:
            root.name = e.fields[NAME]
    e.applied_at = datetime.now(timezone.utc)
    if transport == "offline":
        e.status, e.read_back = "SIMULATED", {"simulated": True, "note": "Nothing was sent; no read-back exists."}
    else:
        await _confirm(db, e, node, root, acct, nodes)
    svc.audit(db, user, "ads.edit.applied", root.id, {"edit": str(e.id), "mode": root.mode, "status": e.status})
    await db.commit()
    return {"status": e.status, "read_back": e.read_back}


async def _confirm(db, e: AdNodeEdit, node, root, acct, nodes) -> None:
    """Status read-back: APPLIED only when the provider reports exactly what was asked, else UNCONFIRMED."""
    try:
        seen = await _read(db, acct, root, nodes, node)
    except (AdsError, EgressBlocked) as ex:
        e.status, e.read_back = "UNCONFIRMED", {"error": str(ex)[:300]}
        return
    diffs = compare(e.fields, seen, node)
    e.status, e.read_back = ("UNCONFIRMED" if diffs else "APPLIED"), {"observed": seen, "diffs": diffs,
                                                                     "at": datetime.now(timezone.utc).isoformat()}
    node.last_read_at = datetime.now(timezone.utc)


async def reconcile_edit(db: AsyncSession, e: AdNodeEdit, node: AdCampaignNode, root: AdCampaignNode, acct: AdAccount, user) -> dict:
    """UNKNOWN / UNCONFIRMED edit: read the object back. Matches → SUCCEEDED; otherwise FAILED and safe to apply again."""
    async with svc.root_lock(db, root):
        await db.refresh(root)
        svc.require_member(user, await svc.control(db, acct))
        if e.status not in ("UNKNOWN", "UNCONFIRMED", "FAILED"):
            raise Refused(409, "Nothing to reconcile.")
        nodes = await svc.nodes_of(db, root)
        if svc._tree_transport(nodes, svc.gate(acct, await svc.control(db, acct)), root) == "offline":
            raise Refused(409, "Simulation sent nothing: there is nothing to reconcile.")
        row = (await db.execute(select(AdMutation).where(AdMutation.idempotency_key == f"{e.id}:EDIT"))).scalar_one_or_none()
        await _confirm(db, e, node, root, acct, nodes)
        ok = e.status == "APPLIED"
        if row is not None and row.state in ("UNKNOWN", "PENDING", "FAILED"):
            row.state, row.error = ("SUCCEEDED" if ok else "FAILED"), None if ok else "Read-back shows the change was not applied; safe to try again."
        if ok:
            if NAME in e.fields:
                node.name = e.fields[NAME]
            e.applied_at = datetime.now(timezone.utc)
        else:
            e.status = "FAILED"
        svc.audit(db, user, "ads.edit.reconciled", root.id, {"edit": str(e.id), "applied": ok})
        await db.commit()
        return {"status": e.status, "read_back": e.read_back}


async def readback_node(db: AsyncSession, node: AdCampaignNode, root: AdCampaignNode, acct: AdAccount, user) -> dict:
    """Live read of one object (name, schedule, status). Offline simulation answers honestly that nothing exists."""
    ctrl = await svc.control(db, acct)
    svc.require_member(user, ctrl)
    nodes = await svc.nodes_of(db, root)
    if not node.provider_id:
        raise Refused(409, "Not on the provider yet.")
    if svc._tree_transport(nodes, svc.gate(acct, ctrl), root) == "offline":
        return {"simulated": True, "note": "Offline simulation: nothing was sent, so there is nothing to read back."}
    try:
        seen = await _read(db, acct, root, nodes, node)
    except (AdsError, EgressBlocked) as ex:
        node.last_error = str(ex)[:500]
        await db.commit()
        raise
    node.last_read_at = datetime.now(timezone.utc)
    await db.commit()
    return {"observed": seen, "at": node.last_read_at.isoformat()}


# ── reporting per node (existing performance sync) ──────────────────────────

def _tail(pid: Optional[str]) -> Optional[str]:
    return pid.replace(":", "/").rsplit("/", 1)[-1] if pid else None


async def node_reports(db: AsyncSession, acct: AdAccount, root: AdCampaignNode, nodes: list, days: int) -> dict:
    """Metrics only where the performance sync really reports (campaign level; LinkedIn: its 'campaign'). Other nodes say so."""
    from datetime import timedelta
    out = {}
    rn = next((n for n in nodes if n.level == REPORT_LEVEL[acct.provider]), None)
    for n in nodes:
        if rn is None or n.id != rn.id:
            out[str(n.id)] = {"available": False, "reason": "The performance sync reports at campaign level only."}
        elif not n.provider_id:
            out[str(n.id)] = {"available": False, "reason": "Not on the provider yet."}
        else:
            r = (await db.execute(select(func.coalesce(func.sum(AdCampaignDay.impressions), 0), func.coalesce(func.sum(AdCampaignDay.clicks), 0),
                                         func.coalesce(func.sum(AdCampaignDay.spend), 0), func.coalesce(func.sum(AdCampaignDay.conversions), 0),
                                         func.count(), func.max(AdCampaignDay.day)).where(
                AdCampaignDay.account_id == acct.id, AdCampaignDay.campaign_id == _tail(n.provider_id)[:40],
                AdCampaignDay.day >= date.today() - timedelta(days=days)))).one()
            imp, clk, spend, conv, rows, last = int(r[0]), int(r[1]), Decimal(r[2]), Decimal(r[3]), r[4], r[5]
            out[str(n.id)] = {"available": True, "rows": rows, "impressions": imp, "clicks": clk, "spend": float(spend),
                              "conversions": float(conv), "ctr": round(clk / imp, 4) if imp else None,
                              "cpc": float(round(spend / clk, 2)) if clk else None, "last_day": last.isoformat() if last else None,
                              "last_sync_at": acct.last_sync_at.isoformat() if acct.last_sync_at else None,
                              "note": None if rows else "No synced rows yet: run 'Sync reporting' on the account."}
    return out
